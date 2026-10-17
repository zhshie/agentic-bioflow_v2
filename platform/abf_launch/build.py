# Nothing existing: the part of a launch or a cancel that comes before any question (read the choices, build the bundle, make the screen); both the terminal commands and the MCP tools need the same bytes, and no library builds this bundle.
"""What `abf-platform launch` and `cancel` do before they ask anybody, as functions (feature 007b, moved here by spec 009c).

The terminal commands (abf_launch.cli) and the MCP tools `launch` and `cancel` (through abf_platform.actions) both call these, so
the bundle that is hashed, the screen that is shown and every refusal are the same whoever asks. This module asks nothing and
writes nothing: it reads the samplesheet and the params, the platform's tables (read-only) and calls abf_station.launch.render_bundle().
A choice that cannot be made into a launch raises Refusal, whose text is said to the person as it is.
"""
import csv
import io
import json
import os
import re
import time
from pathlib import Path

from abf_platform import agents, compute_envs, jobs
from abf_station import launch as bundle_mod

from . import terminal


class Refusal(Exception):
    """A choice that cannot be made into a launch or a cancel; the text is the reason, in the person's words."""


# ---- reading what the person gave -------------------------------------------------------------------------------

def read_samplesheet(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise bundle_mod.BundleError("samplesheet: 讀不到 %s (%s)" % (path, e.__class__.__name__))
    return parse_samplesheet(raw)


def parse_samplesheet(raw):
    """The rows of a samplesheet given as bytes (the MCP tool reads the file once, after its own check, and passes the bytes on)."""
    if b"\x00" in raw:
        raise bundle_mod.BundleError("samplesheet: 含有 NUL 字元，一律拒絕 (contains a NUL character)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise bundle_mod.BundleError("samplesheet: 不是 UTF-8 文字 (not UTF-8 text)")
    try:
        rows = [r for r in csv.reader(io.StringIO(text, newline="")) if r]
    except csv.Error as e:
        raise bundle_mod.BundleError("samplesheet: 不是合法的 CSV (%s)" % e)
    return rows


def infer(text):
    if text in ("true", "false"):
        return text == "true"
    if re.fullmatch(r"-?[0-9]+", text) and len(text) < 16:
        return int(text)
    if re.fullmatch(r"-?[0-9]+\.[0-9]+", text) and len(text) < 20:
        return float(text)
    return text


def read_params_file(path):
    """A flat `name: value` file (YAML or the same in JSON). Nesting and lists are refused, not guessed at."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise bundle_mod.BundleError("params-file: 讀不到 %s (%s)" % (path, e.__class__.__name__))
    if str(path).endswith(".json"):
        try:
            data = json.loads(text)
        except ValueError:
            raise bundle_mod.BundleError("params-file: 不是合法的 JSON (not valid JSON)")
        if not isinstance(data, dict):
            raise bundle_mod.BundleError("params-file: 必須是名稱到值的對照 (a mapping)")
        return data
    out = {}
    for n, ln in enumerate(text.splitlines(), 1):
        s = ln.rstrip()
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]+(.*)$", s)
        if not m:
            raise bundle_mod.BundleError("params-file 第 %d 行: 只支援一行一個 `名稱: 值`；巢狀、清單與多行值不支援，"
                                         "請改用 --param (flat `name: value` lines only)" % n)
        v = m.group(2).strip()
        if v[:1] in ("'", '"'):
            q = v[0]
            end = v.find(q, 1)
            if end < 0 or v[end + 1:].strip() not in ("",) and not v[end + 1:].strip().startswith("#"):
                raise bundle_mod.BundleError("params-file 第 %d 行: 引號沒有成對 (unbalanced quote)" % n)
            val = v[1:end]
            if q == '"':
                try:
                    val = json.loads('"' + val + '"')
                except ValueError:
                    raise bundle_mod.BundleError("params-file 第 %d 行: 跳脫字元不合法 (bad escape)" % n)
            out[m.group(1)] = val
            continue
        v = re.sub(r"\s+#.*$", "", v)
        if v in ("", "|", ">", "[", "{") or v.startswith(("[", "{", "- ")):
            raise bundle_mod.BundleError("params-file 第 %d 行: 巢狀或清單不支援，請改用 --param (nested values are not supported)" % n)
        out[m.group(1)] = infer(v)
    return out


# ---- the checks that come before any question --------------------------------------------------------------------

def primary_environment(state, owner=None):
    """The environment a launch uses when none is named. With `owner` (a user id, 116) it is chosen among that user's own."""
    envs = [c for c in compute_envs.list_all(state, owner=owner)
            if c["platform"] == compute_envs.SUPPORTED and c["status"] == compute_envs.AVAILABLE]
    primary = [c for c in envs if c["primary"]]
    if primary:
        return primary[0]["name"]
    if len(envs) == 1:
        return envs[0]["name"]
    return None


def target_problem(state, ce_name, kind, owner=None):
    """The sentence that says why the environment cannot take this kind of job right now, or None. With `owner` (116) an environment
    or an agent of somebody else is 'not found'."""
    try:
        jobs.check_target(state, ce_name, kind, caller_user_id=owner)
    except jobs.JobRefused as e:
        return str(e)
    return None


def prepare_launch(state, *, ce=None, pipeline, revision, run_name, samplesheet, params_file=None, param_items=None, params=None,
                   path_columns=None, check_name=True, samplesheet_raw=None, owner=None, area=None):
    """(environment name, bundle) for these choices, or Refusal. Nothing is shown, asked or written.

    owner (a user id, 116): the environment is chosen among, and must be, that user's own; None is the local terminal without an
    account. area (the real path of the caller's own upload folder): every path cell of the samplesheet must lie inside it, on top of
    the environment's own roots; None keeps the old roots (the terminal and stdio).

    param_items are `name=value` strings as typed on a command line (the value is read as a number or true/false when it looks
    like one); params is a mapping that already has its types (the MCP tool). Both are put over the params file.
    check_name=False leaves the run-name check to the caller (the MCP tool looks for a yes that already exists first).
    samplesheet_raw (bytes) is the samplesheet already read; then `samplesheet` is not opened again."""
    ce_name = ce or primary_environment(state, owner)
    if not ce_name:
        raise Refusal("沒有指定環境（--ce），也找不到唯一可用的環境 (no --ce, and no single available environment)")
    problem = target_problem(state, ce_name, "launch_nextflow", owner)
    if problem:
        raise Refusal(problem)
    view = compute_envs.get(state, ce_name, owner)
    facts = agents.get_facts(state, view["agent"])
    if facts is None:
        raise Refusal("代理 %s 還沒有回報送出需要的資料；請確認代理是新版並已連線 (the agent has not reported its facts)" % view["agent"])
    try:
        rows = parse_samplesheet(samplesheet_raw) if samplesheet_raw is not None else read_samplesheet(samplesheet)
        merged = read_params_file(params_file) if params_file else {}
        for item in param_items or []:
            key, eq, value = item.partition("=")
            if not eq:
                raise bundle_mod.BundleError("--param: %r 不是 名稱=值 (name=value)" % item[:40])
            merged[key] = infer(value)
        merged.update(params or {})
        bundle = bundle_mod.render_bundle(**bundle_mod.inputs_from_environment(
            view, view["agent"], facts, run_name=run_name, pipeline=pipeline, revision=revision,
            samplesheet=rows, params=merged, path_columns=path_columns))
    except bundle_mod.BundleError as e:
        raise Refusal(str(e))
    if area is not None:
        _check_area(bundle, area)
    if check_name:
        try:
            jobs.check_run_name(state, bundle["run_name"])    # a name that cannot be used is refused before anything is shown
        except jobs.JobRefused as e:
            raise Refusal(str(e))
    return ce_name, bundle


def area_refusal(area):
    return Refusal("samplesheet 裡的每個路徑都必須在你自己的上傳資料夾裡：%s (every path in the samplesheet must lie inside your own uploads folder)" % area)


def _check_area(bundle, area):
    """Every path cell of the samplesheet, with its links followed, lies below `area` (the real path of the caller's own folder)."""
    for _, _, cell in bundle_mod.path_cells(bundle["samplesheet"], bundle["path_columns"]):
        real = os.path.realpath(cell)
        if not real.startswith(area + os.sep):
            raise area_refusal(area)


def prepare_cancel(state, run, owner=None):
    """(environment name, bundle, hand-off row) for a cancel of one run of this platform, or Refusal. With `owner` (116) only a run
    that user launched is there: another user's run is 'not launched from this platform' to them, as a missing one is."""
    con = _open(state)
    try:
        row = jobs.latest_launch(con, run) if con is not None else None
    finally:
        if con is not None:
            con.close()
    if row is not None and owner is not None and ("user_id" not in row.keys() or row["user_id"] != owner):
        row = None
    if row is None:
        raise Refusal("%s 不是平台自己送出的（hand-off 紀錄裡沒有它）(not launched from this platform)" % run)
    if row["slurm_job_id"] is None:
        raise Refusal("%s 沒有 Slurm 工作編號：它尚未送出，或結果不明；請先查國網上的 %s (no Slurm job number recorded)"
                      % (run, row["run_folder"]))
    view = compute_envs.get(state, row["ce"])
    if view is None:
        raise Refusal("環境 %s 找不到 (not found)" % row["ce"])
    if view["agent"] != row["agent"]:
        raise Refusal("%s 是經由代理 %s 送出的，環境 %s 現在的代理是 %s；不取消別的代理送出的工作 (a different agent)"
                      % (run, row["agent"], row["ce"], view["agent"]))
    problem = target_problem(state, row["ce"], "cancel_run", owner)
    if problem:
        raise Refusal(problem)
    bundle = {"version": 1, "run_name": row["run_name"], "slurm_job_id": row["slurm_job_id"], "run_folder": row["run_folder"],
              "agent": row["agent"], "ce": bundle_mod.snapshot_ce(view)}
    return row["ce"], bundle, row


def _open(state):
    from abf_platform import store
    return store.open_readonly(state)


# ---- the screens ----------------------------------------------------------------------------------------------------

def when(epoch):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))


def launch_screen(bundle, ce_name):
    ce = bundle["ce"]
    lines = [terminal.PREFIX + "== 送出確認：下面就是會被送出的全部內容 =="]
    for label, value in (("管線", bundle["pipeline"]), ("版本", bundle["revision"]), ("環境", ce_name),
                         ("代理", bundle["agent"]), ("run 名稱", bundle["run_name"]), ("專屬資料夾", bundle["run_folder"]),
                         ("計費帳號", bundle["account"]), ("主控佇列", ce["headQueue"]),
                         ("主控送出選項", ce["headJobOptions"] or "(無)")):
        lines.append(terminal.pair(label, value))
    rows = bundle["samplesheet"]
    lines.append(terminal.PREFIX + "== samplesheet.csv（%d 列資料）==" % (len(rows) - 1))
    for row in rows:
        buf = io.StringIO()
        csv.writer(buf, lineterminator="").writerow(row)
        lines.append(terminal.PREFIX + terminal.esc(buf.getvalue()))
    for name in ("params.yaml", "nextflow.config", "head.sh"):
        lines += terminal.block(name, bundle["files"][name])
    return lines


def cancel_screen(bundle, row):
    lines = [terminal.PREFIX + "== 取消確認：只會對下面這一個 Slurm 工作送出取消 =="]
    for label, value in (("run 名稱", bundle["run_name"]), ("Slurm 工作編號", bundle["slurm_job_id"]),
                         ("專屬資料夾", bundle["run_folder"]), ("代理", bundle["agent"])):
        lines.append(terminal.pair(label, value))
    if row["cancel_requested_at"] is not None:
        lines.append(terminal.pair("提醒", "這個 run 的取消請求已經在 %s 送出過一次" % when(row["cancel_requested_at"])))
    return lines


def as_text(lines):
    """A screen as plain text for a form or a page: the same lines, without the line prefix of the terminal."""
    return "\n".join(ln[len(terminal.PREFIX):] if ln.startswith(terminal.PREFIX) else ln for ln in lines)
