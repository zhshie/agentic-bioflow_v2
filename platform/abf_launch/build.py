# Nothing existing: the part of a launch or a cancel that comes before any question (read the choices, build the bundle, make the screen); both the terminal commands and the MCP tools need the same bytes, and no library builds this bundle.
"""What `abf-platform launch` and `cancel` do before they ask anybody, as functions (feature 007b, moved here by spec 009c).

The terminal commands (abf_launch.cli) and the MCP tools `launch` and `cancel` (through abf_platform.actions) both call these, so
the bundle that is hashed, the screen that is shown and every refusal are the same whoever asks. This module asks nothing and
writes nothing: it reads the samplesheet and the params, the platform's tables (read-only) and calls abf_station.launch.render_bundle().
A choice that cannot be made into a launch raises Refusal, whose text is said to the person as it is.
"""
import copy
import csv
import io
import json
import os
import re
import time
from pathlib import Path

from abf_platform import agents, compute_envs, jobs, status, store
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


def prepare_launch(state, *, ce=None, pipeline, revision, run_name, samplesheet=None, params_file=None, param_items=None, params=None,
                   path_columns=None, check_name=True, samplesheet_raw=None, owner=None, area=None, samplesheet_rows=None):
    """(environment name, bundle) for these choices, or Refusal. Nothing is shown, asked or written.

    owner (a user id, 116): the environment is chosen among, and must be, that user's own; None is the local terminal without an
    account. area (the real path of the caller's own upload folder): a path cell of the samplesheet that lies in the upload area must lie inside
    it (anywhere else it only has to lie in the environment's own roots, as a path in params), on top of those roots; None keeps the old roots (the terminal and stdio).

    param_items are `name=value` strings as typed on a command line (the value is read as a number or true/false when it looks
    like one); params is a mapping that already has its types (the MCP tool). Both are put over the params file.
    check_name=False leaves the run-name check to the caller (the MCP tool looks for a yes that already exists first).
    samplesheet_raw (bytes) is the samplesheet already read; then `samplesheet` is not opened again. samplesheet_rows (a list of rows) is
    one that was read and checked before, a resume or a relaunch taking the rows of the first launch; then nothing is opened either."""
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
        if samplesheet_rows is not None:
            rows = copy.deepcopy(samplesheet_rows)
        else:
            rows = parse_samplesheet(samplesheet_raw) if samplesheet_raw is not None else read_samplesheet(samplesheet)
        merged = read_params_file(params_file) if params_file else {}
        for item in param_items or []:
            key, eq, value = item.partition("=")
            if not eq:
                raise bundle_mod.BundleError("--param: %r 不是 名稱=值 (name=value)" % item[:40])
            merged[key] = infer(value)
        merged.update(params or {})
        inputs = bundle_mod.inputs_from_environment(view, view["agent"], facts, run_name=run_name, pipeline=pipeline, revision=revision,
                                                    samplesheet=rows, params=merged, path_columns=path_columns)
        bundle = bundle_mod.render_bundle(**inputs)
    except bundle_mod.BundleError as e:
        raise Refusal(str(e))
    if area is not None:
        bundle["upload_paths"] = _confine(state, bundle, area, inputs["roots"])
    if check_name:
        try:
            jobs.check_run_name(state, bundle["run_name"])    # a name that cannot be used is refused before anything is shown
        except jobs.JobRefused as e:
            raise Refusal(str(e))
    return ce_name, bundle


def area_refusal(area):
    return Refusal("samplesheet 裡的每個路徑都必須在你自己的上傳資料夾裡：%s (every path in the samplesheet must lie inside your own uploads folder)" % area)


SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


def params_area_refusal(name, area):
    return Refusal("params %s: 路徑必須在你自己的上傳資料夾裡：%s (a path in params must lie inside your own uploads folder)" % (name, area))


def _below(real, area):
    return real == area or real.startswith(area + os.sep)


OWNER_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _param_path(value, area, roots):
    """The path to judge for a params value, else None. A value is a path when it starts with / or ~, is . or .. or has a . or ..
    component, starts with ./ or ../, names an existing file or folder under the caller's folder or a read root, or contains / and is
    neither a scheme address (https://...) nor an owner/name identifier such as nf-core/rnaseq (116b ruling)."""
    if not value:
        return None
    if value.startswith("/") or value.startswith("~"):
        return value
    if any(part in (".", "..") for part in value.split("/")):
        return value
    if SCHEME.match(value) and not value.lower().startswith("file:"):
        return None
    for root in [area] + [r for r in roots if isinstance(r, str)]:
        if os.path.exists(os.path.join(root, value)):
            return os.path.join(root, value)
    if "/" in value and not OWNER_NAME.match(value):
        return value
    return None


def _confine(state, bundle, area, roots):
    """Every path of an HTTP caller's launch that lies in the upload area (the path cells of the samplesheet and the path-like values of
    params) is below `area`, the real path of the caller's own folder, with its links followed; the others follow the read roots. Returns
    the record that goes into the bundle (so that the approved hash covers it): the real path of each upload-area path, as of now.
    The agent resolves them again at job time and refuses a job whose paths moved (116b)."""
    rules = bundle_mod.rules
    entries = []
    root = store.uploads_root(state)
    uploads = os.path.realpath(str(root))
    spellings = {rules.normalize(os.path.abspath(str(root))), rules.normalize(uploads)}
    for r, c, cell in bundle_mod.path_cells(bundle["samplesheet"], bundle["path_columns"]):
        real = os.path.realpath(cell)
        lexical = rules.normalize(cell) if rules.path_problem(cell) is None else None
        if _below(real, uploads) or (lexical and rules.inside(lexical, spellings)):
            # the same judgement as a path in params: inside the upload area it must be a file of the caller's own folder (the folder
            # itself is not a file); a cell anywhere else only has to lie in the read roots, which was checked when the bundle was built
            if real == area or not _below(real, area) or not lexical:
                raise area_refusal(area)
            entries.append({"where": "samplesheet 第 %d 列第 %d 欄" % (r, c), "given": cell, "real": real})
    for name, value in bundle["params"].items():
        judged = _param_path(value, area, roots) if isinstance(value, str) else None
        if judged is None:
            continue
        outside = Refusal("params %s: 路徑在允許讀取的範圍之外 (outside the allowed read roots)" % name)
        if not os.path.isabs(judged):
            raise outside      # ~/x and x/y are not places a read root names
        real = os.path.realpath(judged)
        lexical = rules.normalize(judged) if rules.path_problem(judged) is None else None
        if _below(real, uploads) or (lexical and rules.inside(lexical, spellings)):
            if not _below(real, area):
                raise params_area_refusal(name, area)
            if not lexical:
                raise outside      # the agent writes and resolves only plain paths
            entries.append({"where": "params %s" % name, "given": judged, "real": real})
        elif not lexical or not rules.inside(lexical, roots):
            raise outside
    return {"area": area, "paths": entries}


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


# ---- resume and relaunch (spec 009e) --------------------------------------------------------------------------------

WORDS = {"resume": "續跑", "relaunch": "重跑"}
TOO_OLD = "太久了，這次送出的內容已經清掉，請當成新分析重新送出 (the content of that launch is cleared after 7 days; send it again as a new analysis)"
CHANGED = ("環境或設定在第一次送出之後變了（%s）。換環境就是新的分析，請用 launch 當成新分析重新送出 "
           "(the environment is not the one of the first launch; that is a new analysis, send it with launch)")


def attempt_name(root, attempt):
    """<root>-a<N>, the root cut so that the whole name is at most 64 characters. Given by the platform; nobody types it."""
    suffix = "-a%d" % attempt
    return root[:64 - len(suffix)] + suffix


def _predecessor(state, run, verb, index_path, owner):
    """Everything a resume or a relaunch of `run` is made from, or Refusal (the words are said to the person as they are):
    (its row of the hand-off record, the first launch's bundle that made its folder, the hash that was confirmed for that bundle,
    its end as the run index says, the number of the new attempt, the name that began the analysis).

    The run must be a run of this platform that the caller may see, with a Slurm number, and its end must be a failure in Nextflow's own
    records (the index; a cancelled run is a failed run there). It must be the newest attempt of its analysis. Nothing of the state of a
    run is stored by the platform: it is read from the index each time."""
    word = WORDS[verb]
    con = _open(state)
    try:
        row = jobs.latest_launch(con, run) if con is not None else None
        if row is not None and owner is not None and jobs._col(row, "user_id") != owner:
            row = None
        if row is None:
            raise Refusal(jobs.RUN_NOT_FOUND % run)
        if jobs.run_forgotten(con, run):
            raise Refusal(jobs.FORGOTTEN)      # keep-submissions (F2): the owner deleted what it was sent with; there is nothing to go on from
        if row["slurm_job_id"] is None:
            raise Refusal("%s 沒有 Slurm 工作編號：它尚未送出，或結果不明；請先查國網上的 %s (no Slurm job number recorded)" % (run, row["run_folder"]))
        view = status.find_run(index_path, run)
        if view is None:
            raise Refusal("%s 還在跑，或還沒有回報任何事件，不能%s (still running or waiting)" % (run, word))
        if view["status"] == "succeeded":
            raise Refusal("%s 已成功，不需要%s (it succeeded)" % (run, word))
        if view["status"] != "failed":
            raise Refusal("%s 還在跑，或已失去聯絡（%s），無法確定它已結束，不能%s；等 Nextflow 的紀錄顯示失敗之後再試 (not ended)"
                          % (run, view["status"], word))
        now = time.time()
        standing = jobs.standing_attempts(con, run, now)
        mine = jobs._col(row, "attempt") or 1
        newer = sorted([(n, r["run_name"]) for r, n in standing if n > mine])
        if newer:
            raise Refusal("%s 已有較新的一次：%s（第 %d 次）；只能對最新的一次%s (a newer attempt exists: %s)"
                          % (run, newer[-1][1], newer[-1][0], word, newer[-1][1]))
        content = None
        for r in con.execute("SELECT * FROM launches WHERE run_folder = ? ORDER BY id DESC", (row["run_folder"],)).fetchall():
            if jobs._col(r, "attempt_kind") == "resume":
                continue
            kind, job = jobs.launch_job(con, r, now)
            if kind == "refused":
                continue
            content = jobs.launch_content(con, r, job)      # the confirmation first; the job's copy only for a row made before it kept the content
            break
        if content is None:
            raise Refusal(TOO_OLD)
        origin, sha = content
        return row, origin, sha, view, jobs.next_attempt(con, run, now), jobs.analysis_root(con, run)
    finally:
        if con is not None:
            con.close()


def _same_environment(state, row):
    """The name of the environment the predecessor went through, which must still be there with the agent that took it."""
    view = compute_envs.get(state, row["ce"])
    if view is None:
        raise Refusal("環境 %s 找不到 (not found)" % row["ce"])
    if view["agent"] != row["agent"]:
        raise Refusal("%s 是經由代理 %s 送出的，環境 %s 現在的代理是 %s；換代理就是新的分析，請用 launch 重新送出 (a different agent)"
                      % (row["run_name"], row["agent"], row["ce"], view["agent"]))
    return row["ce"]


def _name(state, root, attempt, owner):
    name = attempt_name(root, attempt)
    try:
        jobs.check_run_name(state, name, time.time, owner)
    except jobs.JobRefused as e:
        raise Refusal(str(e))
    return name


def prepare_resume(state, run, *, index_path, owner=None, area=None):
    """(environment name, bundle, the predecessor's row) for the resume of the failed run `run`, or Refusal. Nothing is shown, asked or
    written. The bundle has no samples and no parameters of its own: they are the first launch's bundle, kept verbatim, so that they cannot
    change. It is rebuilt from the platform's facts of today, as the agent will rebuild it, and must come out the same: a resume of
    another environment is a new analysis. owner and area are the 116 and 116b limits of a launch; with an area the real paths of the
    samples are looked at again and recorded in the bundle, and a link that now leads out of the caller's folder is refused here."""
    row, origin, _sha, view, attempt, root = _predecessor(state, run, "resume", index_path, owner)
    ce_name = _same_environment(state, row)
    session = view.get("session_id")
    if not isinstance(session, str) or not bundle_mod.SESSION_ID.match(session):
        raise Refusal("%s 的 Nextflow session id 看起來不對，不續跑 (the session id of the run is not a UUID)" % run)
    new_name = _name(state, root, attempt, owner)
    try:
        _, rebuilt = prepare_launch(state, ce=ce_name, pipeline=origin["pipeline"], revision=origin["revision"], run_name=origin["run_name"],
                                    params=origin["params"], path_columns=origin["path_columns"], check_name=False, owner=owner, area=area,
                                    samplesheet_rows=origin["samplesheet"])
    except (KeyError, TypeError):
        raise Refusal(TOO_OLD)
    upload = rebuilt.pop("upload_paths", None)
    if rebuilt != {k: v for k, v in origin.items() if k not in bundle_mod.RECORDS}:
        raise Refusal(CHANGED % "與第一次送出時各自重建的內容不一致")
    try:
        bundle = bundle_mod.render_resume_bundle(origin=rebuilt, run_name=new_name, attempt=attempt, session_id=session, of_run=run,
                                                 of_slurm_job_id=row["slurm_job_id"])
    except bundle_mod.BundleError as e:
        raise Refusal(str(e))
    bundle["resume"]["origin"] = copy.deepcopy(origin)      # the bundle as it was confirmed, with the records the platform added to it
    if upload is not None:
        bundle["upload_paths"] = upload
    return ce_name, bundle, row


def prepare_relaunch(state, run, *, index_path, owner=None, area=None):
    """(environment name, bundle, the predecessor's row) for the relaunch of the failed run `run`: the first launch's pipeline, revision,
    samples and parameters under a new name and a new folder, as `prepare_launch` makes them, with one record more, `relaunch`: what it is a
    relaunch of, which attempt it is, and the hash that was confirmed for the launch that made the old folder."""
    row, origin, sha, _view, attempt, root = _predecessor(state, run, "relaunch", index_path, owner)
    ce_name = _same_environment(state, row)
    new_name = _name(state, root, attempt, owner)      # 116b: the check carries the caller, so another user's run is not told about
    try:
        _, bundle = prepare_launch(state, ce=ce_name, pipeline=origin["pipeline"], revision=origin["revision"], run_name=new_name,
                                   params=origin["params"], path_columns=origin["path_columns"], check_name=False, owner=owner, area=area,
                                   samplesheet_rows=origin["samplesheet"])
        same = all(bundle.get(k) == origin.get(k) for k in ("ce", "agent", "account", "tower", "pipeline", "revision", "samplesheet", "params",
                                                           "path_columns"))
    except (KeyError, TypeError):
        raise Refusal(TOO_OLD)
    if not same:
        raise Refusal(CHANGED % "環境、代理或連線方式不是第一次送出時的那一個")
    bundle["relaunch"] = {"of_run": run, "attempt": attempt, "of_sha256": sha}
    return ce_name, bundle, row


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


FORGET_WARNING = "刪除後無法復原；這個 run 之後不能再續跑或原樣重跑。紀錄（誰、何時送出）會保留。"


def forget_screen(run_name):
    """What the person is asked before the content of one run's submissions is deleted (keep-submissions)."""
    return [terminal.PREFIX + "== 刪除確認：只會刪除這個 run 送出時留下的內容（bundle 與畫面文字）==",
            terminal.pair("run 名稱", run_name),
            terminal.PREFIX + FORGET_WARNING]

def _attempt_lines(title, bundle, row, attempt, sentence, pipeline, revision, samples, script):
    lines = [terminal.PREFIX + title]
    for label, value in (("上一次的 run", row["run_name"]), ("這是第幾次", "第 %d 次" % attempt), ("上一次的 Slurm 工作編號", row["slurm_job_id"]),
                         ("新的 run 名稱", bundle["run_name"]), ("專屬資料夾", bundle["run_folder"]), ("管線", pipeline), ("版本", revision),
                         ("樣本數", samples), ("環境", row["ce"]), ("代理", bundle["agent"])):
        lines.append(terminal.pair(label, value))
    lines.append(terminal.PREFIX + sentence)
    last = [ln for ln in bundle["files"][script].split("\n") if ln][-1]       # the line that starts Nextflow, as the script has it
    lines.append(terminal.pair("指令（%s 的最後一行）" % script, last))
    return lines


def resume_screen(bundle, row):
    """What a person sees before saying yes to a resume: whose it is, which attempt, what stays as it is, and the exact line that runs."""
    r = bundle["resume"]
    o = r["origin"]
    script = next(iter(bundle["files"]))
    lines = _attempt_lines("== 續跑確認：同一個資料夾，Nextflow 接著上次做 ==", bundle, row, r["attempt"],
                           "這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變", o["pipeline"], o["revision"], len(o["samplesheet"]) - 1, script)
    lines.append(terminal.pair("接續的 session", r["session_id"]))
    lines += terminal.block(script, bundle["files"][script])
    return lines


def relaunch_screen(bundle, row):
    """What a person sees before saying yes to a relaunch: the same as a launch shows, with what it is a relaunch of in front."""
    lines = _attempt_lines("== 重跑確認：全新的資料夾，從頭開始 ==", bundle, row, bundle["relaunch"]["attempt"],
                           "這是原樣重跑：全新資料夾，樣本與參數不變", bundle["pipeline"], bundle["revision"], len(bundle["samplesheet"]) - 1, "head.sh")
    return lines + launch_screen(bundle, row["ce"])[1:]


def as_text(lines):
    """A screen as plain text for a form or a page: the same lines, without the line prefix of the terminal."""
    return "\n".join(ln[len(terminal.PREFIX):] if ln.startswith(terminal.PREFIX) else ln for ln in lines)
