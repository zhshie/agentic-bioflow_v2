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
import os
import re
import shlex

from . import rules

BUNDLE_VERSION = 1
RUN_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}\Z")
REVISION = re.compile(r"^(v?[0-9]+(\.[0-9]+){1,3}|[0-9a-f]{40})\Z")
PIPELINE_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
PARAM_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}\Z")
ACCOUNT = re.compile(r"^[A-Za-z0-9_.-]{1,64}\Z")
QUEUE = re.compile(r"^[A-Za-z0-9_.-]+\Z")
TIME = re.compile(r"^([0-9]{1,3}-)?[0-9]{1,2}:[0-9]{2}:[0-9]{2}\Z")
URL = re.compile(r"^https?://[A-Za-z0-9.:\[\]-]+(/[A-Za-z0-9._~/-]*)?\Z")
DEFAULT_PATH_COLUMN = re.compile(r"^(fastq|fq|bam|cram|reads|file|path|reference)([_-]?[0-9]+)?\Z|_(file|path)\Z", re.I)
MAX_VALUE = 100000
SET_BY_THE_SCRIPT = ("TOWER_ACCESS_TOKEN", "NXF_LOG_FILE")
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F, 0x061C}
FILE_NAMES = ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh")
# Appended to every rendered nextflow.config, after the compute environment's own text (which stays first and unchanged).
# When a run is cancelled Nextflow runs its workflow-complete observers twice (Session.destroy() calls shutdown0() again,
# docs/PITFALLS.md 50); the second report/timeline write refuses an existing file and logs "Report file already exists".
# Only these two settings, they concern files of this one run. The block is part of the bundle that is shown and hashed.
OVERWRITE_BLOCK = (
    "\n"
    "// added by the platform: when a run is cancelled Nextflow writes its report and timeline twice;\n"
    "// without this the second write is refused and the log of the cancelled run holds an ERROR.\n"
    "report.overwrite = true\n"
    "timeline.overwrite = true\n"
)
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
    ("cpus", re.compile(r"^-c\Z"), True, re.compile(r"^[0-9]{1,4}\Z")),
    ("cpus", re.compile(r"^--cpus-per-task=([0-9]{1,4})\Z"), False, None),
    ("mem", re.compile(r"^--mem=([0-9]{1,7}[MG])\Z"), False, None),
    ("time", re.compile(r"^-t\Z"), True, TIME),
    ("time", re.compile(r"^--time=(.+)\Z"), False, TIME),
    ("account", re.compile(r"^-A\Z"), True, ACCOUNT),
    ("qos", re.compile(r"^--qos=([A-Za-z0-9_.-]+)\Z"), False, None),
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


def path_cells(rows, path_columns):
    """(row number, column number, cell) of every cell of a checked samplesheet that is read as a path: a cell of a path column
    (named, or one of the usual names) or any cell that starts with /. Empty cells are not paths. Numbers count from 1 and the header is row 1."""
    explicit = set(path_columns or [])
    path_cols = {i for i, h in enumerate(rows[0]) if h in explicit or DEFAULT_PATH_COLUMN.match(h)}
    return [(r, c + 1, cell) for r, row in enumerate(rows[1:], 2) for c, cell in enumerate(row)
            if cell != "" and (c in path_cols or cell.startswith("/"))]


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
    for r, c, cell in path_cells(clean, path_columns):
        where = "%s 第 %d 列第 %d 欄（%s）" % (f, r, c, clean[0][c - 1][:40])
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
        "nextflow.config": ((config if config.endswith("\n") else config + "\n") if config.strip()
                            else "// the compute environment carries no Nextflow config\n") + OVERWRITE_BLOCK,
        "head.sh": _head_script(run_name, run_folder, pipeline, revision, queue, options, account, env, tower),
    }
    return {"version": BUNDLE_VERSION, "agent": agent, "ce": ce_out, "run_name": run_name, "run_folder": run_folder,
            "pipeline": pipeline, "revision": revision, "samplesheet": sheet, "params": user_params,
            "path_columns": sorted(set(path_columns or [])), "account": account, "tower": tower, "files": files}


# ======================================================================================================================
# The launch itself: what the agent does with a confirmed job
# ======================================================================================================================

import base64
import io
import tarfile
import time
from urllib.parse import urlparse

from abf_platform import common

from .site import quote

LOOPBACK = ("127.0.0.1", "localhost", "::1")
MIN_REMAINING = 60.0                       # seconds of the job's deadline that must be left before sbatch (ABF_STATION_MIN_REMAINING)
LAUNCH_KEYS = {"bundle", "confirmation_id", "bundle_sha256"}
SUBMITTED = re.compile(r"Submitted batch job ([0-9]+)\s*$", re.M)


def own_facts(ctx):
    """What this agent says about itself in hello, from the deployment's settings; the same shape the platform stores."""
    sf = ctx.settings_file
    reach = rules.read_setting(sf, "reach") or "local"
    storage = rules.read_setting(sf, "storage_root")
    if not storage or rules.path_problem(storage) or rules.normalize(storage) == "/":
        storage = None
    else:
        storage = rules.normalize(storage)
    url = (ctx.platform_url or "").rstrip("/")
    forward_file = storage + "/_relay/forward_port" if storage and reach not in ("local", "none") else None
    return common.clean_facts({"slurm_account": rules.read_setting(sf, "slurm_account") or None, "reach": reach,
                               "platform_local": (urlparse(url).hostname or "") in LOOPBACK, "endpoint": url or None,
                               "forward_file": forward_file, "storage_root": storage})


def verify_confirmation(job, ctx, want):
    """The bundle of a confirmed job, or rules.Refusal: it carries a confirmation of the right kind that was made for exactly
    this content and has not been used by this agent before. Nothing is written or run before this has passed."""
    args = job.get("args")
    conf = job.get("confirmation")
    cid = args.get("confirmation_id") if isinstance(args, dict) else None
    if not isinstance(cid, str) or not cid:
        raise rules.Refusal("沒有確認憑證：送出與取消只在使用者於終端機答 y 之後才會執行 (no confirmation)")
    if not isinstance(conf, dict) or conf.get("id") != cid:
        raise rules.Refusal("平台沒有附上這個確認憑證的紀錄 (the platform sent no matching confirmation row)")
    if conf.get("kind") != want or conf.get("used_at") is not None:
        raise rules.Refusal("確認憑證的種類不符，或已用過 (wrong kind of confirmation, or used already)")
    bundle = args.get("bundle")
    if not isinstance(bundle, dict):
        raise rules.Refusal("沒有內容包 (no bundle)")
    sha = common.bundle_sha256(bundle)
    if not (isinstance(conf.get("sha256"), str) and conf["sha256"] == args.get("bundle_sha256") == sha):
        raise rules.Refusal("內容與確認時不符：代理執行的必須是使用者看到的那一份 (the content is not the content that was confirmed)")
    if cid in ctx.used_confirmations:
        raise rules.Refusal("這個確認憑證已經用過 (this confirmation was used already)")
    ctx.used_confirmations.add(cid)
    return bundle


def _left(ctx, job):
    """Seconds of the job's deadline that are left, by this agent's own clock."""
    remaining = job.get("remaining")
    if isinstance(remaining, bool) or not isinstance(remaining, (int, float)):
        remaining = 0.0
    return remaining - (time.monotonic() - ctx.job_started)


def _min_remaining():
    try:
        return float(os.environ.get("ABF_STATION_MIN_REMAINING", MIN_REMAINING))
    except ValueError:
        return MIN_REMAINING


def _tar(folder_files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for name, data in folder_files:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o600
            info.mtime = int(time.time())
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _curl(site, url, proxy=None):
    """(exit code, http code or None, X-ABF-Platform header or None) of one request made ON the login node. No token is sent."""
    cmd = "curl -sS -D - -o /dev/null -w %s --max-time 10 %s%s" % (quote("code=%{http_code}\\n"), ("-x %s " % quote(proxy)) if proxy else "",
                                                                    quote(url))
    res = site.call([cmd], timeout=40)
    text = res.out.decode("utf-8", errors="replace")
    code = re.search(r"code=([0-9]{3})", text)
    mark = re.search(r"(?im)^x-abf-platform:[ \t]*(\S+)", text)
    return res.rc, (code.group(1) if code else None), (mark.group(1) if mark else None)


def _channel(ctx, bundle):
    """Make sure the way back from the compute nodes to this platform is open, hop by hop, before anything is written on the site.

    The reverse forward is an option of the user's shared connection (scripts/on_site.sh --forward): one is made when none is
    recorded for this connection, and every launch after it uses the same one. Its port is also written on the site, where the
    relay reads it. Then two probes run on the login node, with no token: straight to the forward, and through the relay the way
    the head job will go. Each failure names the hop and the fix.
    """
    site = ctx.site
    ff = bundle["tower"]["forward_file"]
    proxy = next((e["value"] for e in bundle["ce"].get("environment", [])
                  if e.get("name") in ("http_proxy", "HTTP_PROXY") and e.get("head", True) and e.get("value")), None)
    if not proxy:
        raise rules.Refusal("環境沒有 http_proxy（relay 的位址），無法檢查計算節點回報的路；請先用 scripts/ce_apply.sh 補上，沒有建立任何東西 "
                            "(the compute environment has no http_proxy)")
    if not getattr(ctx, "instance_id", None):
        raise rules.Refusal("代理不知道這個平台的實例編號（平台太舊？），無法確認通道另一端是它 (the platform did not tell its instance id)")
    local = urlparse(ctx.platform_url).port or (443 if urlparse(ctx.platform_url).scheme == "https" else 80)
    found = site.call(["--check-forward"])
    port = None
    if found.rc == 0:
        port = found.out.decode("utf-8", errors="replace").strip().splitlines()[-1:] or [""]
        port = port[0] if port[0].isdigit() else None
    elif found.rc != 1:
        from .handlers import connect_failure
        raise rules.Refusal("不能確認反向通道：%s" % connect_failure(found))
    if port is None:
        made = site.call(["--forward", str(local)])
        if made.rc != 0:
            from .handlers import connect_failure
            why = connect_failure(made) if ("needs-human" in made.err or made.timed_out) else made.err.strip()[-300:]
            raise rules.Refusal("反向通道開不起來：%s（沒有建立任何東西）" % why)
        lines = made.out.decode("utf-8", errors="replace").strip().splitlines()
        port = lines[-1] if lines and lines[-1].isdigit() else None
        if port is None:
            raise rules.Refusal("反向通道開了，但讀不出站台選的 port (could not read the port the site chose)")
    fi = os.path.dirname(ff) + "/forward_instance"
    wrote = site.call(["mkdir -p %s && umask 077 && cat > %s && chmod 600 %s" % (quote(os.path.dirname(ff)), quote(ff), quote(ff))],
                      input=(port + "\n").encode("ascii"))
    if wrote.rc == 0:
        # the relay asks the port who answers and compares with this id before it passes a run token on
        wrote = site.call(["umask 077 && cat > %s && chmod 600 %s" % (quote(fi), quote(fi))], input=(ctx.instance_id + "\n").encode("ascii"))
    if wrote.rc != 0:
        raise rules.Refusal("沒辦法在站台上寫 relay 要讀的 port 檔 %s（結束碼 %d）(could not write the forward file on the site)" % (ff, wrote.rc))
    url = "http://127.0.0.1:%s/user-info" % port
    fix_tunnel = "反向通道沒開：登入節點連不到 127.0.0.1:%s。請確認平台在跑，再重試；仍不行就執行 `abf-station unforward` 後再試。" % port
    silent = "平台沒有回應：反向通道有開，但另一端的平台沒有回答。請檢查 abf-platform serve 是否在跑、port 是否對。"
    taken = "這個 port 上回答的不是這個平台（回應沒有帶這個平台的 X-ABF-Platform 編號）：有別的程式佔用。請 `abf-station unforward` 後重試。"
    rc, code, mark = _curl(site, url)
    if rc == 7:
        raise rules.Refusal(fix_tunnel)
    if rc != 0 or code is None or code in ("000", "502", "504"):
        raise rules.Refusal(silent)
    if code != "401" or mark != ctx.instance_id:
        raise rules.Refusal(taken)
    rc, code, mark = _curl(site, url, proxy)
    if rc == 7:
        raise rules.Refusal("relay 沒在跑（登入節點上連不到 %s）：請啟動 relay：`bash scripts/egress_ctl.sh start`（經 scripts/on_site.sh --script 在站台上執行）。" % proxy)
    if code == "403":
        raise rules.Refusal("relay 是舊版，還沒有放行反向通道：請重啟 relay：`bash scripts/egress_ctl.sh restart`（經 scripts/on_site.sh --script "
                            "在站台上執行）。")
    if rc != 0 or code is None or code in ("000", "502", "504"):
        raise rules.Refusal(silent + "（這次是經過 relay 的那一段沒通）")
    if code != "401" or mark != ctx.instance_id:
        raise rules.Refusal(taken)


def _check_upload_paths(record, ctx):
    """116b: the paths of an HTTP caller's launch that lay in the caller's upload folder were recorded with their real paths when the
    person said yes. Resolve each again now, on the site, and refuse the job when one leads somewhere else or outside the recorded
    folder: a link swapped after the yes. This only ever refuses; what the agent may read is still judged by rules.allowed_roots."""
    swapped = "上傳資料夾裡的路徑在你核可之後變了（捷徑被改指別處），不送出 (a path in your uploads folder leads somewhere else than when you approved)"
    try:
        area = record["area"]
        entries = [(e["given"], e["real"]) for e in record["paths"]]
        if not isinstance(area, str) or not all(isinstance(g, str) and isinstance(r, str) for g, r in entries):
            raise TypeError
    except (KeyError, TypeError):
        raise rules.Refusal("上傳路徑的記錄格式不對，不送出 (the record of the upload paths is malformed)")
    for given, real in entries:
        if rules.path_problem(given) or rules.path_problem(real) or rules.path_problem(area):
            raise rules.Refusal(swapped)
        if not rules.inside(rules.normalize(real), [rules.normalize(area)]):
            raise rules.Refusal("記錄的真實路徑不在擁有者的上傳資料夾裡，不送出 (a recorded path lies outside the owner's folder)")
    if not entries:
        return
    res = ctx.site.call(["realpath -z -m -- " + " ".join(quote(g) for g, _ in entries)])      # NUL-separated: a newline in a link target adds no line
    if res.rc != 0 or not res.out.endswith(b"\0"):
        raise rules.Refusal(swapped)
    now = [x.decode("utf-8", errors="replace") for x in res.out[:-1].split(b"\0")]
    if len(now) != len(entries) or now != [r for _, r in entries]:
        raise rules.Refusal(swapped)


def run_launch(job, ctx, preflight):
    """(state, result) of one launch_nextflow job. preflight(env, ctx) is handlers.preflight, passed in so that the checks of
    007 run first and unchanged."""
    bundle = verify_confirmation(job, ctx, "launch")
    env = rules.clean_environment(bundle.get("ce"))
    if bundle.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個內容包是給另一個代理的 (the bundle is for another agent)")
    facts = own_facts(ctx)
    token = job.get("run_token")
    if not isinstance(token, str) or not token or len(token) > 200:
        raise rules.Refusal("平台沒有給這次執行的 token (no run token was sent)")
    try:
        rebuilt = render_bundle(ce=bundle["ce"], agent=bundle["agent"], facts=facts, roots=rules.allowed_roots(env, ctx.settings_file),
                                run_name=bundle["run_name"], pipeline=bundle["pipeline"], revision=bundle["revision"],
                                samplesheet=bundle["samplesheet"], params=bundle["params"], path_columns=bundle["path_columns"])
    except (BundleError, KeyError, TypeError) as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    if rebuilt != {k: v for k, v in bundle.items() if k != "upload_paths"}:      # the record of the upload-area paths is the platform's; the agent checks it below
        why = "帳號與部署設定不符" if rebuilt.get("account") != bundle.get("account") else "內容與代理依自己的設定重新產生的不一致"
        raise rules.Refusal("%s：不送出 (the bundle is not what this agent builds from its own settings)" % why)
    if "upload_paths" in bundle:
        _check_upload_paths(bundle["upload_paths"], ctx)
    if _left(ctx, job) < _min_remaining():
        raise rules.Refusal("工作期限剩下的時間不足以安全送出 (too little of the deadline is left to submit safely)")
    site = ctx.site
    run, folder, work = bundle["run_name"], bundle["run_folder"], env["workDir"]

    verdict = preflight(env, ctx)
    failed = [c for c in verdict["checks"] if c["status"] != "pass"]
    if failed:
        raise rules.Refusal("預檢未通過，沒有建立任何東西：" + "；".join("%s（%s）" % (c["name"], c["detail"]) for c in failed))
    cache = next((e["value"] for e in bundle["ce"].get("environment", []) if e.get("name") == "NXF_SINGULARITY_CACHEDIR" and e.get("head", True)), None)
    if cache:
        if rules.path_problem(cache):
            raise rules.Refusal("NXF_SINGULARITY_CACHEDIR 不是合法的路徑 (not a plain path)")
        c = quote(cache)
        res = site.call(["if test -d %s; then test -w %s && echo cache=ok || echo cache=no; else d=$(dirname %s); "
                         "test -d \"$d\" && test -w \"$d\" && echo cache=ok || echo cache=no; fi" % (c, c, c)])
        if "cache=ok" not in res.out.decode("utf-8", errors="replace"):
            raise rules.Refusal("容器快取 NXF_SINGULARITY_CACHEDIR=%s 不可寫；請改成可寫的資料夾後再試，沒有建立任何東西 (the container cache "
                                "cannot be written)" % cache)
    if bundle["tower"]["mode"] == "forward":
        _channel(ctx, bundle)

    res = site.call(["mkdir -p %s" % quote(work + "/runs")])
    if res.rc != 0:
        return "error", {"ok": False, "message": "站台上建不起 %s/runs（結束碼 %d）；沒有建立專屬資料夾 (nothing was made)" % (work, res.rc)}
    files = [(name, bundle["files"][name].encode("utf-8")) for name in FILE_NAMES] + [("tower.token", token.encode("utf-8"))]
    res = site.call(["umask 077; mkdir %s && tar -x --no-same-owner -C %s" % (quote(folder), quote(folder))],
                    input=_tar(files), timeout=120)
    if res.rc != 0:
        if "File exists" in res.err:
            raise rules.Refusal("專屬資料夾 %s 已存在，不覆蓋；請換一個 run 名稱。沒有改動任何東西 (the run folder exists already)" % folder)
        left = "資料夾 %s 可能已建立，檔案可能不完整，尚未送出" % folder
        return "error", {"ok": False, "message": "寫入專屬資料夾時出錯（結束碼 %d）。%s" % (res.rc, left), "left_on_site": left}
    if _left(ctx, job) < _min_remaining():
        left = "資料夾 %s 與其中的檔案已寫好，尚未送出（工作期限剩下的時間不足）" % folder
        return "error", {"ok": False, "message": "不送出：" + left, "left_on_site": left}
    # Slurm opens the job's output file (slurm-<id>.out) with the umask of whoever submits; 077 keeps it 0600
    res = site.call(["umask 077; sbatch %s" % quote(folder + "/head.sh")], timeout=120)
    text = res.out.decode("utf-8", errors="replace")
    m = SUBMITTED.search(text)
    unknown = "可能已送出，請查專屬資料夾 %s 與 Slurm 工作 nf-%s" % (folder, run)
    if res.rc == 0 and m:
        n = int(m.group(1))
        return "done", {"ok": True, "slurm_job_id": n, "run_name": run, "run_folder": folder,
                        "message": "已送出：Slurm 工作編號 %d，run 名稱 %s，專屬資料夾 %s" % (n, run, folder)}
    if res.rc == 0 or m or res.timed_out or res.rc in (124, 255):
        return "error", {"ok": False, "message": "sbatch 的結果不明：%s" % unknown, "left_on_site": "資料夾 %s；%s" % (folder, unknown)}
    return "error", {"ok": False, "message": "sbatch 沒有成功（結束碼 %d）：%s。不重試。" % (res.rc, res.err.strip()[:200] or "沒有訊息"),
                     "left_on_site": "資料夾 %s 與其中的檔案（未送出，未刪除）" % folder}
