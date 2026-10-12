# Not Seqera's launcher script, nf-core's `tower launch` or a shell template in a Makefile: they build a head job script for Seqera's own service; this one turns a compute environment and a user's choices into the five files of one Nextflow head job on Slurm, and it is the only file that holds the template.
"""The launch bundle and the launch itself (feature 007b).

`render_bundle()` is a pure function: from a compute environment, the facts the agent reported, and the user's choices
it builds the bundle, which holds the four files that will be written on the site (`samplesheet.csv`, `params.yaml`,
`nextflow.config`, `head.sh`) and everything they were made from. The terminal command shows these files and hashes
the bundle; the agent builds the bundle again from the same inputs with its *own* facts and refuses the job unless the
result is identical to what was confirmed. The script text shown and the script text written are therefore one text.

This module is the one place that holds the head script template and the words that submit a job
(tests/no_second_run_state_test.sh lists it in LAUNCH_ALLOW; its test is
platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused).

Nothing here names a cluster, a partition, a login node or a port: they come from the compute environment (its
queue, options, environment variables and Nextflow config) and from the deployment's settings (the account, the
storage root), through the facts the agent reports in hello.
"""
import csv
import io
import math
import re
import shlex

from . import rules

BUNDLE_VERSION = 1
RUN_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
REVISION = re.compile(r"^(v?[0-9]+(\.[0-9]+){1,3}|[0-9a-f]{40})$")
PIPELINE_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PARAM_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")
ACCOUNT = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
QUEUE = re.compile(r"^[A-Za-z0-9_.-]+$")
TIME = re.compile(r"^([0-9]{1,3}-)?[0-9]{1,2}:[0-9]{2}:[0-9]{2}$")
URL = re.compile(r"^https?://[A-Za-z0-9.:\[\]-]+(/[A-Za-z0-9._~/-]*)?$")
DEFAULT_PATH_COLUMN = re.compile(r"^(fastq|fq|bam|cram|reads|file|path|reference)([_-]?[0-9]+)?$|_(file|path)$", re.I)
MAX_VALUE = 100000
SET_BY_THE_SCRIPT = ("TOWER_ACCESS_TOKEN", "NXF_LOG_FILE")
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F, 0x061C}
FILE_NAMES = ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh")
NO_SCRIPTS = "不支援：這一片不執行事前／事後腳本"


class BundleError(Exception):
    """A choice that cannot be made into a launch; the text names the field and says why."""


def _bad_char(text, allow_cr=False):
    for ch in text:
        o = ord(ch)
        if o == 0 or o == 0x1B or o in BIDI or (ch == "\r" and not allow_cr):
            return ch
    return None


def _check_text(field, value, allow_cr=False, limit=MAX_VALUE):
    if not isinstance(value, str):
        raise BundleError("%s: 必須是文字 (must be text)" % field)
    if len(value) > limit:
        raise BundleError("%s: 超過 %d 個字元 (longer than %d characters)" % (field, limit, limit))
    ch = _bad_char(value, allow_cr)
    if ch is not None:
        raise BundleError("%s: 含有不能誠實顯示的控制字元 %s（NUL、CR、ESC 與雙向控制字元一律拒絕）(contains a control character that "
                          "cannot be shown honestly)" % (field, "U+%04X" % ord(ch)))
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise BundleError("%s: 不是有效的文字 (not valid text)" % field)


# ---- the compute environment ---------------------------------------------------------------------------------

def snapshot_ce(view):
    """What a launch needs of a compute environment (the shape compute_envs.get gives), as plain JSON."""
    c = view.get("config") or {}
    env = [{"name": e.get("name"), "value": e.get("value", ""), "head": bool(e.get("head", True)),
            "compute": bool(e.get("compute", False))} for e in (c.get("environment") or [])]
    return {"name": view.get("name"), "platform": view.get("platform"), "workDir": c.get("workDir"),
            "launchDir": c.get("launchDir"), "headQueue": c.get("headQueue"), "computeQueue": c.get("computeQueue"),
            "readRoots": list(c.get("readRoots") or []), "headJobOptions": c.get("headJobOptions") or "",
            "environment": env, "nextflowConfig": c.get("nextflowConfig") or "",
            "preRunScript": c.get("preRunScript") or "", "postRunScript": c.get("postRunScript") or ""}


def read_roots(ce, storage_root):
    """The places a sample file may be: the work folder, the launch folder, the read roots, the deployment's storage root.
    The agent computes the same list from its own settings (rules.allowed_roots) and uses that one."""
    roots = [ce["workDir"]]
    if ce.get("launchDir"):
        roots.append(ce["launchDir"])
    roots += list(ce.get("readRoots") or [])
    if isinstance(storage_root, str) and rules.path_problem(storage_root) is None and rules.normalize(storage_root) != "/":
        roots.append(rules.normalize(storage_root))
    return roots


def inputs_from_environment(view, agent, facts, *, run_name, pipeline, revision, samplesheet, params, path_columns=None):
    """The arguments of render_bundle for a compute environment as the platform holds it and the facts of its agent."""
    ce = snapshot_ce(view)
    storage = (facts or {}).get("storage_root")
    return dict(ce=ce, agent=agent, facts=facts or {}, roots=read_roots(ce, storage), run_name=run_name, pipeline=pipeline,
                revision=revision, samplesheet=samplesheet, params=params, path_columns=path_columns)


def _check_ce(ce):
    if not isinstance(ce, dict) or ce.get("platform") != rules.SLURM:
        raise BundleError("環境: 尚未支援這種環境，只有 Slurm 能送出 (not supported: only a Slurm environment can launch)")
    try:
        work = rules.clean_root(ce.get("workDir"), "workDir")
        queue = rules.clean_queue(ce.get("headQueue"), "headQueue")
    except rules.Refusal as e:
        raise BundleError("環境: %s" % e)
    if ((ce.get("preRunScript") or "").strip()) or ((ce.get("postRunScript") or "").strip()):
        raise BundleError("環境: %s" % NO_SCRIPTS)
    config = ce.get("nextflowConfig") or ""
    _check_text("nextflowConfig", config, allow_cr=True, limit=200000)
    env = []
    for i, e in enumerate(ce.get("environment") or []):
        name, value = e.get("name"), e.get("value", "")
        if not isinstance(name, str) or not ENV_NAME.match(name):
            raise BundleError("environment[%d]: 變數名稱 %r 必須是英文字母、數字與底線，且不以數字開頭 (a shell variable name)"
                              % (i, str(name)[:40]))
        if not isinstance(value, str) or "\n" in value or "\r" in value or "\x00" in value or len(value) > 2000:
            raise BundleError("environment %s: 值不能含換行或 NUL，且不超過 2000 字元 (no newline or NUL in a value)" % name)
        if name in SET_BY_THE_SCRIPT:
            raise BundleError("environment %s: 這個變數由送出本身設定，環境不能設 (set by the launch itself)" % name)
        if e.get("head", True):
            env.append((name, value))
    return work, queue, config, env


_OPTION_SHAPES = [
    ("cpus", re.compile(r"^-c$"), True, re.compile(r"^[0-9]{1,4}$")),
    ("cpus", re.compile(r"^--cpus-per-task=([0-9]{1,4})$"), False, None),
    ("mem", re.compile(r"^--mem=([0-9]{1,7}[MG])$"), False, None),
    ("time", re.compile(r"^-t$"), True, TIME),
    ("time", re.compile(r"^--time=(.+)$"), False, TIME),
    ("account", re.compile(r"^-A$"), True, ACCOUNT),
    ("qos", re.compile(r"^--qos=([A-Za-z0-9_.-]+)$"), False, None),
]


def _parse_options(text, account):
    """headJobOptions as `#SBATCH` arguments: only -c, --cpus-per-task, --mem, -t/--time, -A and --qos, each once."""
    field = "headJobOptions"
    if not isinstance(text, str) or any(c in text for c in "\n\r\x00") or len(text) > 1000:
        raise BundleError("%s: 不能含換行或 NUL (no newline or NUL)" % field)
    toks = text.split()
    out, seen = [], {}
    it = iter(toks)
    for tok in it:
        for family, shape, takes_next, value_shape in _OPTION_SHAPES:
            m = shape.match(tok)
            if not m:
                continue
            if takes_next:
                nxt = next(it, None)
                if nxt is None or not value_shape.match(nxt):
                    raise BundleError("%s: %s 後面缺少合法的值 (%s needs a plain value)" % (field, tok, tok))
                value, shown = nxt, "%s %s" % (tok, nxt)
            else:
                value, shown = m.group(1), tok
                if value_shape is not None and not value_shape.match(value):
                    raise BundleError("%s: %s 的值不合法 (%s is not a plain value)" % (field, tok, tok))
                if family == "time" and not TIME.match(value):
                    raise BundleError("%s: %s 的時間格式不合法 (a time looks like D-HH:MM:SS)" % (field, tok))
            if family in seen:
                raise BundleError("%s: %s 重複出現 (given twice)" % (field, family))
            seen[family] = value
            out.append(shown)
            break
        else:
            raise BundleError("%s: 不允許的選項 %r（只允許 -c、--cpus-per-task、--mem、-t/--time、-A、--qos）(option not allowed)"
                              % (field, tok[:40]))
    if "account" in seen and seen["account"] != account:
        raise BundleError("帳號與環境選項不一致: 部署設定的帳號是 %s，環境的送出選項寫的是 %s。不猜哪一個才對，請改成一致 "
                          "(the account of the deployment and the account in headJobOptions disagree)" % (account, seen["account"]))
    if "account" not in seen:
        out.append("-A %s" % account)
    return out


# ---- the choices ---------------------------------------------------------------------------------------------

def _check_pipeline(pipeline):
    if not isinstance(pipeline, str) or pipeline.count("/") != 1:
        raise BundleError("pipeline: 必須是 擁有者/名稱，例如 nf-core/ampliseq (owner/name)")
    owner, name = pipeline.split("/")
    for part in (owner, name):
        if not PIPELINE_PART.match(part) or part in (".", ".."):
            raise BundleError("pipeline: %r 不是合法的管線名稱 (each part starts with a letter or digit)" % pipeline[:60])


def _check_revision(revision):
    if not isinstance(revision, str) or not REVISION.match(revision):
        raise BundleError("revision: %r 不是固定版本；只接受標籤（例如 2.18.0）或完整的 40 位 commit，不接受分支 "
                          "(a tag or a full commit, never a branch)" % str(revision)[:60])


def _check_samplesheet(rows, path_columns, roots):
    f = "samplesheet"
    if not isinstance(rows, list) or len(rows) < 2:
        raise BundleError("%s: 至少要有標題列和一列資料 (a header and at least one row)" % f)
    clean = []
    for r, row in enumerate(rows):
        if not isinstance(row, list) or not row:
            raise BundleError("%s 第 %d 列: 不是一列 (not a row)" % (f, r + 1))
        if len(row) != len(rows[0]):
            raise BundleError("%s 第 %d 列: 欄數 %d 與標題列的 %d 不同 (ragged row)" % (f, r + 1, len(row), len(rows[0])))
        for c, cell in enumerate(row):
            _check_text("%s 第 %d 列第 %d 欄" % (f, r + 1, c + 1), cell, limit=5000)
        clean.append(list(row))
    explicit = set(path_columns or [])
    unknown = explicit - set(clean[0])
    if unknown:
        raise BundleError("%s: 沒有名為 %s 的欄 (no such column)" % (f, sorted(unknown)[0]))
    path_cols = {i for i, h in enumerate(clean[0]) if h in explicit or DEFAULT_PATH_COLUMN.match(h)}
    for r, row in enumerate(clean[1:], 2):
        for c, cell in enumerate(row):
            if not (c in path_cols or cell.startswith("/")):
                continue
            if cell == "":
                continue
            where = "%s 第 %d 列第 %d 欄（%s）" % (f, r, c + 1, clean[0][c][:40])
            problem = rules.path_problem(cell)
            if problem:
                raise BundleError("%s: %s" % (where, rules.path_reason("路徑", problem)))
            if not rules.inside(rules.normalize(cell), roots):
                raise BundleError("%s: 路徑在允許讀取的範圍之外 (outside the allowed read roots)" % where)
    return clean


def _check_params(params):
    if not isinstance(params, dict):
        raise BundleError("params: 必須是名稱到值的對照 (a mapping)")
    out = {}
    for name, value in params.items():
        if not isinstance(name, str) or not PARAM_NAME.match(name):
            raise BundleError("params: 參數名稱 %r 必須是英文字母、數字與底線，且不以數字開頭 (a plain name)" % str(name)[:40])
        if name == "outdir":
            raise BundleError("outdir: 固定為專屬資料夾下的 results，不能自訂 (outdir is always <run folder>/results)")
        if name == "input":
            raise BundleError("input: 由 --samplesheet 決定，不能自訂 (input comes from the samplesheet)")
        if isinstance(value, bool) or (isinstance(value, int) and not isinstance(value, bool)):
            out[name] = value
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise BundleError("params %s: 數字必須是有限的 (a finite number)" % name)
            out[name] = value
        elif isinstance(value, str):
            _check_text("params %s" % name, value)
            out[name] = value
        else:
            raise BundleError("params %s: 值必須是文字、數字或布林 (text, a number or a boolean)" % name)
    return out


def _tower(facts, run_name):
    reach = facts.get("reach")
    if reach not in (None, "local", "none"):  # the site is reached over a shared connection: the reverse forward is the way back
        if not facts.get("platform_local"):
            raise BundleError("反向通道: 這一片的反向通道要求平台與代理在同一台機器；這個代理連到的平台網址不是本機。請在同一台機器上"
                              "啟動平台與代理，並用 --platform http://127.0.0.1:<port> (the platform and the agent must be on the "
                              "same machine)")
        ff = facts.get("forward_file")
        if not isinstance(ff, str) or rules.path_problem(ff):
            raise BundleError("反向通道: 代理沒有回報合法的 forward 檔路徑 (the agent reported no usable forward file)")
        return {"mode": "forward", "forward_file": rules.normalize(ff)}
    if reach == "local":
        ep = facts.get("endpoint")
        if not isinstance(ep, str) or not URL.match(ep):
            raise BundleError("端點: 代理沒有回報合法的平台網址 (the agent reported no usable platform address)")
        return {"mode": "direct", "endpoint": ep.rstrip("/")}
    raise BundleError("環境: 代理回報的連線方式是 %r，這一片只支援在本機或透過共用連線到達的站台 (reach must be local or remote)" % str(reach)[:20])


# ---- the files -------------------------------------------------------------------------------------------------------

def _yaml_scalar(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    out = ['"']
    for ch in value:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif o < 0x20 or 0x7F <= o <= 0x9F or o in (0x2028, 0x2029, 0xFEFF):
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _params_yaml(params, run_folder):
    merged = dict(params)
    merged["input"] = run_folder + "/samplesheet.csv"
    merged["outdir"] = run_folder + "/results"
    return "".join("%s: %s\n" % (k, _yaml_scalar(merged[k])) for k in sorted(merged))


def _csv_text(rows):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def _head_script(run_name, run_folder, pipeline, revision, queue, options, account, env, tower):
    q = shlex.quote
    lines = ["#!/bin/bash",
             "#SBATCH -D %s" % run_folder,
             "#SBATCH -J nf-%s" % run_name,
             "#SBATCH --no-requeue",
             "#SBATCH -p %s" % queue]
    lines += ["#SBATCH %s" % o for o in options]
    lines += ["umask 077", "cd %s || exit 1" % q(run_folder), "export SLURM_ACCOUNT=%s" % q(account)]
    forward = tower["mode"] == "forward"
    had_opts = False
    for name, value in env:
        if name == "SLURM_ACCOUNT":
            if value != account:
                raise BundleError("帳號與環境選項不一致: 部署設定的帳號是 %s，環境變數 SLURM_ACCOUNT 寫的是 %s (the account of the "
                                  "deployment and SLURM_ACCOUNT of the environment disagree)" % (account, value))
            continue
        if name == "NXF_OPTS" and forward:
            # the JVM does not send loopback through its proxy unless nonProxyHosts is emptied, and the endpoint is loopback
            value = (value + " " if value else "") + "-Dhttp.nonProxyHosts="
            had_opts = True
        lines.append("export %s=%s" % (name, q(value)))
    if forward and not had_opts:
        lines.append("export NXF_OPTS=%s" % q("-Dhttp.nonProxyHosts="))
    if forward:
        ff = tower["forward_file"]
        lines += ["ABF_FORWARD_PORT=$(cat %s 2>/dev/null)" % q(ff),
                  'case "$ABF_FORWARD_PORT" in \'\'|*[!0-9]*) echo "abf: no usable reverse forward port in %s, so Nextflow '
                  'cannot report to the platform" >&2; exit 1 ;; esac' % ff]
        endpoint = '"http://127.0.0.1:${ABF_FORWARD_PORT}"'
    else:
        endpoint = q(tower["endpoint"])
    lines.append('export TOWER_ACCESS_TOKEN="$(cat tower.token)"')
    lines.append("exec nextflow run %s -r %s -name %s -params-file params.yaml -c nextflow.config -with-tower %s"
                 % (q(pipeline), q(revision), q(run_name), endpoint))
    return "\n".join(lines) + "\n"


def render_bundle(*, ce, agent, facts, roots, run_name, pipeline, revision, samplesheet, params, path_columns=None):
    """The launch bundle: everything that is shown, hashed, written and run. Raises BundleError, naming the field."""
    if not isinstance(agent, str) or not agent:
        raise BundleError("agent: 這個環境沒有代理 (the environment has no agent)")
    facts = facts if isinstance(facts, dict) else {}
    if not isinstance(run_name, str) or not RUN_NAME.match(run_name):
        raise BundleError("run 名稱: %r 必須是小寫英文字母開頭，只含小寫字母、數字、_ 與 -，最長 64 字元 (run name)" % str(run_name)[:70])
    _check_pipeline(pipeline)
    _check_revision(revision)
    work, queue, config, env = _check_ce(ce)
    account = facts.get("slurm_account")
    if not isinstance(account, str) or not account:
        raise BundleError("帳號未設定: 計費帳號沒有預設值，請在部署設定檔（config/env.yaml）設定 slurm_account 再重試 "
                          "(slurm_account is not set in the deployment's settings)")
    if not ACCOUNT.match(account):
        raise BundleError("帳號: 部署設定的 slurm_account 含不允許的字元 (the account has characters that are not allowed)")
    options = _parse_options(ce.get("headJobOptions") or "", account)
    tower = _tower(facts, run_name)
    sheet = _check_samplesheet(samplesheet, path_columns, roots)
    user_params = _check_params(params)
    run_folder = "%s/runs/%s" % (work, run_name)
    ce_out = {"name": ce.get("name"), "platform": ce.get("platform"), "workDir": work, "launchDir": ce.get("launchDir"),
              "headQueue": queue, "computeQueue": ce.get("computeQueue"), "readRoots": list(ce.get("readRoots") or []),
              "headJobOptions": ce.get("headJobOptions") or "", "environment": [dict(e) for e in (ce.get("environment") or [])],
              "nextflowConfig": config, "preRunScript": "", "postRunScript": ""}
    files = {
        "samplesheet.csv": _csv_text(sheet),
        "params.yaml": _params_yaml(user_params, run_folder),
        "nextflow.config": (config if config.endswith("\n") else config + "\n") if config.strip()
        else "// the compute environment carries no Nextflow config\n",
        "head.sh": _head_script(run_name, run_folder, pipeline, revision, queue, options, account, env, tower),
    }
    return {"version": BUNDLE_VERSION, "agent": agent, "ce": ce_out, "run_name": run_name, "run_folder": run_folder,
            "pipeline": pipeline, "revision": revision, "samplesheet": sheet, "params": user_params,
            "path_columns": sorted(set(path_columns or [])), "account": account, "tower": tower, "files": files}
