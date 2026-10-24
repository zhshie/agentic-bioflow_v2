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
import copy
import csv
import io
import math
import os
import re
import shlex

from abf_platform import compute_envs

from . import rules

SITE_KEYS = ("modules", "siteConfigVars", "sitePipelines")
REMOTE = {"kind": "remote"}
BUNDLE_VERSION = 1
RUN_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}\Z")
SESSION_ID = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")      # a Nextflow session id is a UUID; it is put in a script, so nothing else gets in
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
COMPOSED = "abf-composed"      # the owner part of the pipeline name of a composed pipeline; nf-core launches may not use it
COMPOSED_NO_RESUME = ("自訂組合的 run 目前不能續跑或原樣重跑；請回到組合頁，用同一個版本重新送出（會再問一次確認）(a run of a composed pipeline cannot be "
                      "resumed or relaunched yet; send the same version again from the pipeline page, which asks for a new yes)")
PROJECT_KEY = re.compile(r"^(main\.nf|nextflow\.config|modules\.json|modules/nf-core/[a-z0-9_]+(/[a-z0-9_]+)*/"
                         r"(main\.nf|templates/[A-Za-z0-9_.-]+|resources/[A-Za-z0-9_.-]+))\Z")
PROJECT_MAX_FILE = 200000          # characters of one file of a composed project
PROJECT_MAX_BYTES = 2 * 1024 * 1024
PROJECT_MAX_FILES = 2000
GCB_NO_RESUME = "Google Batch 的 run 還不能續跑或原樣重跑（尚未支援）(a Google Batch run cannot be resumed or relaunched yet)"


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


def _check_project(project):
    """The files of a composed pipeline's project: {relative path: text}. Only the shapes the platform makes are accepted, so that every
    key is a safe path below the run's `pipeline/` folder. Raises BundleError naming the file."""
    f = "project"
    if not isinstance(project, dict) or not project:
        raise BundleError("%s: 必須是 相對路徑到文字 的對照 (a mapping of relative path to text)" % f)
    if len(project) > PROJECT_MAX_FILES:
        raise BundleError("%s: 檔案數 %d 超過上限 %d (more than %d files)" % (f, len(project), PROJECT_MAX_FILES, PROJECT_MAX_FILES))
    total = 0
    for key in sorted(project, key=str):
        label = "%s 檔 %r" % (f, key if isinstance(key, str) else str(key)[:60])
        if (not isinstance(key, str) or not PROJECT_KEY.match(key) or len(key) > 300
                or any(part in (".", "..") for part in key.split("/"))):
            raise BundleError("%s: 不是組合專案允許的檔案路徑 (not a path a composed project may have)" % label)
        _check_text(label, project[key], limit=PROJECT_MAX_FILE)
        total += len(project[key].encode("utf-8"))
    if total > PROJECT_MAX_BYTES:
        raise BundleError("%s: 全部檔案共 %d 位元組，超過上限 %d (the files are larger than %d bytes together)"
                          % (f, total, PROJECT_MAX_BYTES, PROJECT_MAX_BYTES))
    for need in ("main.nf", "nextflow.config"):
        if need not in project:
            raise BundleError("%s 檔 %r: 缺少這個檔案 (the project has no %s)" % (f, need, need))


def _composed_source(pipeline, revision, composed):
    """The pipeline_source of a composed launch (the checks first). `composed` is {"pipeline_id", "version", "project"}."""
    if pipeline.split("/")[0] != COMPOSED:
        raise BundleError("pipeline: 組合管線的名稱必須是 %s/名稱 (a composed pipeline is named %s/name)" % (COMPOSED, COMPOSED))
    if (not isinstance(composed, dict) or set(composed) != {"pipeline_id", "version", "project"}
            or any(isinstance(composed[k], bool) or not isinstance(composed[k], int) or composed[k] < 1 for k in ("pipeline_id", "version"))):
        raise BundleError("composed: 必須有 pipeline_id、version（1 以上的整數）與 project (pipeline_id, version and project)")
    if revision != "0.%d.0" % composed["version"]:
        raise BundleError("revision: 組合管線的版本必須是 0.%d.0 (the revision of version %d is 0.%d.0)"
                          % (composed["version"], composed["version"], composed["version"]))
    _check_project(composed["project"])
    return {"kind": "composed", "pipeline_id": composed["pipeline_id"], "version": composed["version"],
            "project_sha256": hashlib.sha256(common.canonical_json(composed["project"])).hexdigest()}


# ---- the compute environment ---------------------------------------------------------------------------------

def snapshot_ce(view):
    """What a launch needs of a compute environment (the shape compute_envs.get gives), as plain JSON."""
    c = view.get("config") or {}
    env = [{"name": e.get("name"), "value": e.get("value", ""), "head": bool(e.get("head", True)),
            "compute": bool(e.get("compute", False))} for e in (c.get("environment") or [])]
    if view.get("platform") == GCB:
        return {"name": view.get("name"), "platform": GCB, "project": c.get("project"), "location": c.get("location"),
                "workDir": c.get("workDir"), "spot": bool(c.get("spot")), "bootDiskSize": c.get("bootDiskSize"),
                "bootDiskImage": c.get("bootDiskImage"), "serviceAccountEmail": c.get("serviceAccountEmail"),
                "network": c.get("network"), "subnetwork": c.get("subnetwork"), "usePrivateAddress": bool(c.get("usePrivateAddress")),
                "labels": dict(c.get("labels") or {}), "maxvCpus": c.get("maxvCpus"), "environment": env,
                "nextflowConfig": c.get("nextflowConfig") or "", "preRunScript": c.get("preRunScript") or "",
                "postRunScript": c.get("postRunScript") or ""}
    return {"name": view.get("name"), "platform": view.get("platform"), "workDir": c.get("workDir"),
            "launchDir": c.get("launchDir"), "headQueue": c.get("headQueue"), "computeQueue": c.get("computeQueue"),
            "readRoots": list(c.get("readRoots") or []), "headJobOptions": c.get("headJobOptions") or "",
            "environment": env, "nextflowConfig": c.get("nextflowConfig") or "",
            "preRunScript": c.get("preRunScript") or "", "postRunScript": c.get("postRunScript") or "",
            "modules": list(c.get("modules") or []), "siteConfigVars": list(c.get("siteConfigVars") or []),
            "sitePipelines": [dict(p) if isinstance(p, dict) else p for p in (c.get("sitePipelines") or [])]}


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
    site = {k: ce.get(k) if ce.get(k) is not None else [] for k in SITE_KEYS}
    try:
        compute_envs._check_site_keys(site)      # the one set of rules for the three keys, the platform's own
    except compute_envs.CEError as e:
        raise BundleError("環境: %s (the compute environment's modules, siteConfigVars or sitePipelines are not acceptable)" % e)
    return work, queue, config, env, site


def _pipeline_source(site, pipeline, revision):
    """Where this (pipeline, revision) is started from: the site's own copy if the environment lists it (the first entry wins), else the remote."""
    for p in site["sitePipelines"]:
        if p["pipeline"] == pipeline and p["revision"] == revision:
            return {"kind": "site-module", "module": p["module"], "home": p["home"]}
    return dict(REMOTE)


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
    if reach not in (None, "local", "none") and facts.get("way_back") == "direct":  # the compute nodes reach the platform's public address
        url = common.public_url(facts.get("platform_public_url"))
        if not url:
            raise BundleError("進度回報: 進度回報需要 https 公開網址或 loopback（本機測試用）；請把設定檔的 platform_public_url 改成 https 網址 "
                              "(progress reporting needs an https public address or loopback)")
        return {"mode": "direct", "endpoint": url}
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


def _head_script(run_name, run_folder, pipeline, revision, queue, options, account, env, tower, resume_session=None, site=None,
                 source=None):
    q = shlex.quote
    site = site or {"modules": [], "siteConfigVars": []}
    source = source or REMOTE
    local = source["kind"] == "site-module"
    composed = source["kind"] == "composed"
    lines = ["#!/bin/bash",
             "#SBATCH -D %s" % run_folder,
             "#SBATCH -J nf-%s" % run_name,
             "#SBATCH --no-requeue",
             "#SBATCH -p %s" % queue]
    lines += ["#SBATCH %s" % o for o in options]
    lines.append("umask 077")
    loads = list(site["modules"]) + ([source["module"]] if local else [])
    lines += ["module load %s || exit 1" % q(m) for m in loads]      # a module that will not load stops the job; it never falls back to the remote
    lines += ["cd %s || exit 1" % q(run_folder), "export SLURM_ACCOUNT=%s" % q(account)]
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
    resume = "" if resume_session is None else " -resume %s" % q(resume_session)      # 009e: the one thing a resume adds to the last line
    # the site's own config files first, ours (nextflow.config, ending in OVERWRITE_BLOCK) last so that our overrides win
    site_c = "".join(' -c "$%s"' % v for v in site["siteConfigVars"])
    if composed:      # the project the bundle carries, written below the run's own folder; its config is read before ours, which stays last
        lines.append("exec nextflow run %s -name %s -params-file params.yaml%s -c %s -c nextflow.config -with-tower %s"
                     % (q(run_folder + "/pipeline/main.nf"), q(run_name), site_c, q(run_folder + "/pipeline/nextflow.config"), endpoint))
        return "\n".join(lines) + "\n"
    target = '"$%s"' % source["home"] if local else "%s -r %s" % (q(pipeline), q(revision))
    lines.append("exec nextflow run %s%s -name %s -params-file params.yaml%s -c nextflow.config -with-tower %s"
                 % (target, resume, q(run_name), site_c, endpoint))
    return "\n".join(lines) + "\n"


def render_bundle(*, ce, agent, facts, roots, run_name, pipeline, revision, samplesheet, params, path_columns=None, composed=None):
    """The launch bundle: everything that is shown, hashed, written and run. Raises BundleError, naming the field. `composed`
    ({"pipeline_id", "version", "project"}) makes it the launch of a composed pipeline: the bundle then carries the project and starts it
    from the run's own folder; with None the bundle is exactly what it always was."""
    if isinstance(ce, dict) and ce.get("platform") == GCB:      # a Google Batch environment has its own bundle, below
        if composed is not None:
            raise BundleError("環境: Google Batch 環境還不能送出自訂組合 (a composed pipeline cannot be sent to a Google Batch environment yet)")
        return render_gcb_bundle(ce=ce, agent=agent, facts=facts, roots=roots, run_name=run_name, pipeline=pipeline, revision=revision,
                                 samplesheet=samplesheet, params=params, path_columns=path_columns)
    if not isinstance(agent, str) or not agent:
        raise BundleError("agent: 這個環境沒有代理 (the environment has no agent)")
    facts = facts if isinstance(facts, dict) else {}
    if not isinstance(run_name, str) or not RUN_NAME.match(run_name):
        raise BundleError("run 名稱: %r 必須是小寫英文字母開頭，只含小寫字母、數字、_ 與 -，最長 64 字元 (run name)" % str(run_name)[:70])
    _check_pipeline(pipeline)
    _check_revision(revision)
    work, queue, config, env, site = _check_ce(ce)
    source = _pipeline_source(site, pipeline, revision) if composed is None else _composed_source(pipeline, revision, composed)
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
              "nextflowConfig": config, "preRunScript": "", "postRunScript": "",
              "modules": list(site["modules"]), "siteConfigVars": list(site["siteConfigVars"]),
              "sitePipelines": copy.deepcopy(site["sitePipelines"])}
    files = {
        "samplesheet.csv": _csv_text(sheet),
        "params.yaml": _params_yaml(user_params, run_folder),
        "nextflow.config": ((config if config.endswith("\n") else config + "\n") if config.strip()
                            else "// the compute environment carries no Nextflow config\n") + OVERWRITE_BLOCK,
        "head.sh": _head_script(run_name, run_folder, pipeline, revision, queue, options, account, env, tower, site=site,
                                source=source),
    }
    return {"version": BUNDLE_VERSION, "agent": agent, "ce": ce_out, "run_name": run_name, "run_folder": run_folder,
            "pipeline": pipeline, "revision": revision, "samplesheet": sheet, "params": user_params,
            "path_columns": sorted(set(path_columns or [])), "account": account, "tower": tower, "files": files,
            "pipeline_source": source, **({"project": composed["project"]} if composed is not None else {})}


# ---- Google Cloud Batch: the head process runs on the platform host, the compute on Batch (gcb-launch) ----------------------

GCB = compute_envs.PLATFORM_HOST_TYPES[0]
GCB_RUNS = "_gcb_runs"
GCB_FILE_NAMES = ("samplesheet.csv", "params.yaml", "nextflow.config", "gcb.config", "head.sh")
GCB_CREDENTIALS_COMMENT = ("# credentials: the agent sets GOOGLE_APPLICATION_CREDENTIALS from its own key file; the path is not part of "
                           "this script")
GCB_FORBIDDEN_ENV = ("GOOGLE_APPLICATION_CREDENTIALS",)
GCB_WORK_CHARS = re.compile(r"^[A-Za-z0-9_./@+=:,-]+\Z")
GCB_VALUE_CHARS = re.compile(r"^[A-Za-z0-9_./@+=:,-]*\Z")
GCB_LOOPBACK_OPTS = "-Dhttp.nonProxyHosts="
NO_BUCKET_PATH = ("把檔案放進 bucket 是之後的功能（C-6 上傳）；現在請自己用 `gcloud storage" " cp` 把檔案放進 gs://%s/ 底下，再把這一格改成 "
                  "gs:// 路徑 (copying files into the bucket is a later feature; for now put them there with `gcloud storage" " cp`)")      # in two pieces: the source holds no upload command


def _gcb_text(field, value, pattern, limit):
    if not (isinstance(value, str) and 0 < len(value) <= limit and pattern.match(value)):
        raise BundleError("環境 %s: 值不合規則 (%s is not acceptable)" % (field, field))
    return value


def _check_gcb_ce(ce):
    """The settings of a Google Batch environment, each judged again with the platform's own patterns: they end up in a config file.
    Returns (the normalised ce, the bucket of workDir, the head environment [(name, value)])."""
    if not isinstance(ce, dict) or ce.get("platform") != GCB:
        raise BundleError("環境: 這不是 Google Batch 環境 (not a Google Batch environment)")
    out = {"name": ce.get("name"), "platform": GCB}
    out["project"] = _gcb_text("project", ce.get("project"), compute_envs._GCB_PROJECT, 30)
    if len(out["project"]) < 6:
        raise BundleError("環境 project: 值不合規則 (project is not acceptable)")
    out["location"] = _gcb_text("location", ce.get("location"), compute_envs._GCB_LOCATION, 40)
    work = ce.get("workDir")
    if not (isinstance(work, str) and work.startswith("gs://")):
        raise BundleError("環境 workDir: 必須是 gs:// 開頭的網址 (workDir must be a gs:// URL)")
    bucket, _, prefix = work[5:].partition("/")
    if not compute_envs._GCB_BUCKET.match(bucket):
        raise BundleError("環境 workDir: bucket 名稱不合規則 (the bucket name is not acceptable)")
    prefix = prefix.rstrip("/")
    if not prefix:
        raise BundleError("環境 workDir: gs://%s 沒有子目錄。Nextflow 規定 workDir 至少含一層子目錄，例如 gs://%s/work；請更新環境 "
                          "(Nextflow needs a workDir with at least one subdirectory)" % (bucket, bucket))
    if not GCB_WORK_CHARS.match(prefix) or any(part in ("", ".", "..") for part in prefix.split("/")) or len(prefix) > 900:
        raise BundleError("環境 workDir: 資料夾部分含不支援的字元或 .. (the folder part of workDir is not acceptable)")
    out["workDir"] = "gs://%s/%s" % (bucket, prefix)
    spot, private = ce.get("spot"), ce.get("usePrivateAddress")
    for key, v in (("spot", spot), ("usePrivateAddress", private)):
        if v is not None and not isinstance(v, bool):
            raise BundleError("環境 %s: 必須是 true 或 false (true or false)" % key)
    out["spot"], out["usePrivateAddress"] = bool(spot), bool(private)
    disk = ce.get("bootDiskSize")
    if disk is not None:
        m = compute_envs._GCB_DISK.match(disk) if isinstance(disk, str) else None
        if not m or not 1 <= int(m.group(1)) <= 2000:
            raise BundleError("環境 bootDiskSize: 必須是 1 到 2000 的整數加 GB，例如 50 GB (a whole number of GB)")
    out["bootDiskSize"] = disk
    for key, rx, limit in (("bootDiskImage", compute_envs._GCB_IMAGE, 200), ("serviceAccountEmail", compute_envs._GCB_SA_EMAIL, 200),
                           ("network", compute_envs._GCB_NET, 300), ("subnetwork", compute_envs._GCB_NET, 300)):
        v = ce.get(key)
        out[key] = None if v is None else _gcb_text(key, v, rx, limit)
    labels = ce.get("labels") or {}
    if not isinstance(labels, dict) or len(labels) > 64:
        raise BundleError("環境 labels: 必須是最多 64 組的文字對照 (labels are at most 64 text pairs)")
    for k, v in labels.items():
        if not (isinstance(k, str) and compute_envs._GCB_LABEL_KEY.match(k) and isinstance(v, str) and compute_envs._GCB_LABEL_VALUE.match(v)):
            raise BundleError("環境 labels: 有一組標籤的鍵或值不合規則 (a label is not acceptable)")
        if k == "abf-run":
            raise BundleError("環境 labels: abf-run 由送出自己設定，環境不能設 (abf-run is set by the launch itself)")
    out["labels"] = {k: labels[k] for k in sorted(labels)}
    cpus = ce.get("maxvCpus")
    if cpus is not None and (isinstance(cpus, bool) or not isinstance(cpus, int) or not 1 <= cpus <= 10000):
        raise BundleError("環境 maxvCpus: 必須是 1 到 10000 的整數 (a whole number from 1 to 10000)")
    out["maxvCpus"] = cpus
    if ((ce.get("preRunScript") or "").strip()) or ((ce.get("postRunScript") or "").strip()):
        raise BundleError("環境: %s" % NO_SCRIPTS)
    config = ce.get("nextflowConfig") or ""
    _check_text("nextflowConfig", config, allow_cr=True, limit=200000)
    out["nextflowConfig"] = config
    head_env = []
    for i, e in enumerate(ce.get("environment") or []):
        name, value = e.get("name"), e.get("value", "")
        if not isinstance(name, str) or not ENV_NAME.match(name):
            raise BundleError("environment[%d]: 變數名稱 %r 必須是英文字母、數字與底線，且不以數字開頭 (a shell variable name)"
                              % (i, str(name)[:40]))
        if not isinstance(value, str) or "\n" in value or "\r" in value or "\x00" in value or len(value) > 2000:
            raise BundleError("environment %s: 值不能含換行或 NUL，且不超過 2000 字元 (no newline or NUL in a value)" % name)
        if name in SET_BY_THE_SCRIPT or name in GCB_FORBIDDEN_ENV or name.upper().startswith("ABF_"):
            raise BundleError("environment %s: 這個變數由送出本身或代理設定，環境不能設 (set by the launch or the agent itself)" % name)
        if e.get("head", True):
            head_env.append((name, value))
    out["environment"] = [dict(e) for e in (ce.get("environment") or [])]
    out["preRunScript"], out["postRunScript"] = "", ""
    return out, bucket, head_env


def _gcb_quote(value):
    if not (isinstance(value, str) and GCB_VALUE_CHARS.match(value)):
        raise BundleError("設定檔: 值含不支援的字元 (a value of the config has a character that is not allowed)")
    return "'%s'" % value


def _gcb_config(ce, run_name, work_uri):
    """gcb.config: the settings of the compute environment, in the words Nextflow reads. It is read after nextflow.config (-c twice),
    so a line here cannot be overruled by the free text of the environment."""
    q = _gcb_quote
    lines = ["// written by the platform from the compute environment; read after nextflow.config, so these settings win",
             "process.executor = 'google-batch'", "workDir = %s" % q(work_uri), "google.project = %s" % q(ce["project"]),
             "google.location = %s" % q(ce["location"])]
    if ce["spot"]:
        lines.append("google.batch.spot = true")
    if ce["bootDiskSize"] is not None:
        lines.append("google.batch.bootDiskSize = %d.GB" % int(compute_envs._GCB_DISK.match(ce["bootDiskSize"]).group(1)))
    for key in ("bootDiskImage", "serviceAccountEmail", "network", "subnetwork"):
        if ce[key] is not None:
            lines.append("google.batch.%s = %s" % (key, q(ce[key])))
    if ce["usePrivateAddress"]:
        lines.append("google.batch.usePrivateAddress = true")
    pairs = [(k, v) for k, v in ce["labels"].items()] + [("abf-run", run_name[:63])]
    lines.append("process.resourceLabels = [%s]" % ", ".join("%s: %s" % (q(k), q(v)) for k, v in pairs))
    if ce["maxvCpus"] is not None:
        lines.append("process.resourceLimits = [cpus: %d]" % ce["maxvCpus"])      # one task at most; Nextflow has no total of vCPUs
    return "\n".join(lines) + "\n"


def _gcb_head_script(run_name, run_folder, pipeline, revision, env, tower):
    q = shlex.quote
    lines = ["#!/bin/bash", GCB_CREDENTIALS_COMMENT, "umask 077", "cd %s || exit 1" % q(run_folder)]
    loopback = (urlparse(tower["endpoint"]).hostname or "") in LOOPBACK
    had_opts = False
    for name, value in env:
        if name == "NXF_OPTS" and loopback:
            value = (value + " " if value else "") + GCB_LOOPBACK_OPTS      # the JVM does not send loopback through its proxy unless this is emptied
            had_opts = True
        lines.append("export %s=%s" % (name, q(value)))
    if loopback and not had_opts:
        lines.append("export NXF_OPTS=%s" % q(GCB_LOOPBACK_OPTS))
    lines.append('export TOWER_ACCESS_TOKEN="$(cat tower.token)"')
    lines.append("exec nextflow run %s -r %s -name %s -params-file params.yaml -c nextflow.config -c gcb.config -with-tower %s"
                 % (q(pipeline), q(revision), q(run_name), q(tower["endpoint"])))
    return "\n".join(lines) + "\n"


def _gcb_params_yaml(params, input_path, outdir):
    merged = dict(params)
    merged["input"] = input_path
    merged["outdir"] = outdir
    return "".join("%s: %s\n" % (k, _yaml_scalar(merged[k])) for k in sorted(merged))


def _check_gcb_samplesheet(rows, path_columns, bucket):
    """The samplesheet of a Google Batch run: every cell that is read as a path is gs://<the bucket of workDir>/<object>."""
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
    unknown = set(path_columns or []) - set(clean[0])
    if unknown:
        raise BundleError("%s: 沒有名為 %s 的欄 (no such column)" % (f, sorted(unknown)[0]))
    for r, c, cell in path_cells(clean, path_columns):
        where = "%s 第 %d 列第 %d 欄（%s）" % (f, r, c, clean[0][c - 1][:40])
        why = None
        if any(ord(ch) <= 0x20 or ord(ch) == 0x7F or ord(ch) in BIDI for ch in cell):
            why = "含空白、控制字元或雙向文字字元 (a space, control or bidirectional character)"
        else:
            m = re.match(r"^gs://([^/]+)/(.+)\Z", cell)
            if not m:
                why = "必須是 gs://%s/<物件路徑> (must be gs://%s/<object path>)" % (bucket, bucket)
            elif m.group(1) != bucket:
                why = "bucket 必須和環境 workDir 的 bucket（%s）相同 (must be in the bucket of workDir)" % bucket
            elif any(part in ("", ".", "..") for part in m.group(2).split("/")):
                why = "路徑裡不能有 .、.. 或空的一段 (no . or .. or empty part)"
        if why:
            raise BundleError("%s: %s。%s" % (where, why, NO_BUCKET_PATH % bucket))
    return clean


def render_gcb_bundle(*, ce, agent, facts, roots, run_name, pipeline, revision, samplesheet, params, path_columns=None):
    """The launch bundle of a Google Batch environment: the same shape as render_bundle's, without an account, with five files.
    `roots` is accepted for the same call as render_bundle and not used: reads are gs:// paths of the bucket of workDir. Raises BundleError."""
    if not isinstance(agent, str) or not agent:
        raise BundleError("agent: 這個環境沒有代理 (the environment has no agent)")
    facts = facts if isinstance(facts, dict) else {}
    if not isinstance(run_name, str) or not RUN_NAME.match(run_name):
        raise BundleError("run 名稱: %r 必須是小寫英文字母開頭，只含小寫字母、數字、_ 與 -，最長 64 字元 (run name)" % str(run_name)[:70])
    _check_pipeline(pipeline)
    _check_revision(revision)
    ce_out, bucket, head_env = _check_gcb_ce(ce)
    storage = facts.get("storage_root")
    if not isinstance(storage, str) or rules.path_problem(storage) is not None or rules.normalize(storage) == "/":
        raise BundleError("storage_root 未設定: 代理主機上的專屬資料夾放在 storage_root 底下，請在部署設定檔（config/env.yaml）設定 "
                          "storage_root 再重試 (storage_root is not set in the deployment's settings)")
    if facts.get("reach") != "local":
        raise BundleError("環境: Google Batch 的主控程序跑在平台主機上，代理必須在本機（reach: local）；這個代理回報的連線方式是 %r "
                          "(the agent must be on the platform host)" % str(facts.get("reach"))[:20])
    tower = _tower(facts, run_name)
    sheet = _check_gcb_samplesheet(samplesheet, path_columns, bucket)
    user_params = _check_params(params)
    run_folder = "%s/%s/%s" % (rules.normalize(storage), GCB_RUNS, run_name)
    base = "%s/runs/%s" % (ce_out["workDir"], run_name)
    config = ce_out["nextflowConfig"]
    files = {
        "samplesheet.csv": _csv_text(sheet),
        "params.yaml": _gcb_params_yaml(user_params, run_folder + "/samplesheet.csv", base + "/results"),
        "nextflow.config": ((config if config.endswith("\n") else config + "\n") if config.strip()
                            else "// the compute environment carries no Nextflow config\n") + OVERWRITE_BLOCK,
        "gcb.config": _gcb_config(ce_out, run_name, base + "/work"),
        "head.sh": _gcb_head_script(run_name, run_folder, pipeline, revision, head_env, tower),
    }
    return {"version": BUNDLE_VERSION, "agent": agent, "ce": ce_out, "run_name": run_name, "run_folder": run_folder,
            "pipeline": pipeline, "revision": revision, "samplesheet": sheet, "params": user_params,
            "path_columns": sorted(set(path_columns or [])), "tower": tower, "files": files, "pipeline_source": dict(REMOTE)}


def render_resume(*, origin, run_name, attempt, session_id):
    """{ "head-<attempt>.sh": text }: the head script of a resume (spec 009e). `origin` is a launch bundle as render_bundle made it. The
    text is the first launch's head script but for the job name, the new -name and `-resume <session id>`; it runs in the same folder, so
    Nextflow finds its cache there. Raises BundleError, naming the field."""
    if not isinstance(run_name, str) or not RUN_NAME.match(run_name):
        raise BundleError("run 名稱: %r 不是合法的 run 名稱 (run name)" % str(run_name)[:70])
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 2 or attempt > 9999:
        raise BundleError("attempt: 必須是 2 以上的整數 (a whole number from 2)")
    if not isinstance(session_id, str) or not SESSION_ID.match(session_id):
        raise BundleError("session id: 必須是 Nextflow 的 session id（UUID）(a UUID)")
    try:
        ce, account, tower = origin["ce"], origin["account"], origin["tower"]
        pipeline, revision, run_folder = origin["pipeline"], origin["revision"], origin["run_folder"]
    except (KeyError, TypeError):
        raise BundleError("origin: 不是一份送出的內容包 (not a launch bundle)")
    if (origin.get("pipeline_source") or {}).get("kind") == "composed" or "project" in origin:
        raise BundleError(COMPOSED_NO_RESUME)
    _check_pipeline(pipeline)
    _check_revision(revision)
    work, queue, config, env, site = _check_ce(ce)
    source = _pipeline_source(site, pipeline, revision)
    if not isinstance(account, str) or not ACCOUNT.match(account):
        raise BundleError("帳號: 不是合法的帳號 (account)")
    if not isinstance(run_folder, str) or rules.path_problem(run_folder) or not rules.inside(rules.normalize(run_folder), [work + "/runs"]):
        raise BundleError("run_folder: 不在 %s/runs 之下 (not below the work folder's runs)" % work)
    if not isinstance(tower, dict) or tower.get("mode") not in ("forward", "direct"):
        raise BundleError("tower: 不是合法的連線方式 (not a way back to the platform)")
    options = _parse_options(ce.get("headJobOptions") or "", account)
    return {"head-%d.sh" % attempt: _head_script(run_name, run_folder, pipeline, revision, queue, options, account, env, tower,
                                                  resume_session=session_id, site=site, source=source)}


def render_resume_bundle(*, origin, run_name, attempt, session_id, of_run, of_slurm_job_id):
    """The bundle of a resume (spec 009e): the folder of `origin` and the one new file, head-<attempt>.sh. It has no samplesheet and no
    parameters of its own; they are the origin's, which is kept verbatim in `resume`, so they cannot change between the yes and the run."""
    files = render_resume(origin=origin, run_name=run_name, attempt=attempt, session_id=session_id)
    if not isinstance(of_run, str) or not RUN_NAME.match(of_run):
        raise BundleError("of_run: 不是合法的 run 名稱 (run name)")
    if isinstance(of_slurm_job_id, bool) or not isinstance(of_slurm_job_id, int) or of_slurm_job_id < 1:
        raise BundleError("of_slurm_job_id: 必須是 Slurm 工作編號 (a Slurm job number)")
    return {"version": BUNDLE_VERSION, "agent": origin["agent"], "ce": copy.deepcopy(origin["ce"]), "run_name": run_name,
            "run_folder": origin["run_folder"], "files": files,
            "resume": {"of_run": of_run, "of_slurm_job_id": of_slurm_job_id, "session_id": session_id, "attempt": attempt,
                       "origin": copy.deepcopy(origin)}}


# ======================================================================================================================
# The launch itself: what the agent does with a confirmed job
# ======================================================================================================================

import base64
import hashlib
import io
import tarfile
import time
from urllib.parse import urlparse

from abf_platform import common

from .site import quote

LOOPBACK = ("127.0.0.1", "localhost", "::1")
MIN_REMAINING = 60.0                       # seconds of the job's deadline that must be left before sbatch (ABF_STATION_MIN_REMAINING)
LAUNCH_KEYS = {"bundle", "confirmation_id", "bundle_sha256"}
RECORDS = ("upload_paths", "relaunch")      # keys of a launch bundle that the platform adds to what render_bundle makes
RESUME_KEYS = {"of_run", "of_slurm_job_id", "session_id", "attempt", "origin"}
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
    way_back = rules.read_setting(sf, "way_back")
    if way_back not in ("forward", "direct"):
        way_back = "forward" if reach not in ("local", "none") else None
    forward_file = storage + "/_relay/forward_port" if storage and reach not in ("local", "none") else None
    return common.clean_facts({"slurm_account": rules.read_setting(sf, "slurm_account") or None, "reach": reach,
                               "platform_local": (urlparse(url).hostname or "") in LOOPBACK, "endpoint": url or None,
                               "forward_file": forward_file, "storage_root": storage, "way_back": way_back,
                               "platform_public_url": rules.read_setting(sf, "platform_public_url") or None})


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
    if "resume" in bundle:
        return run_resume(job, ctx, preflight, bundle)
    if isinstance(bundle.get("ce"), dict) and bundle["ce"].get("platform") == GCB:
        from . import gcb_launch      # the Google Batch launch; it imports this module, so it is read here and not at the top
        return gcb_launch.run_launch(job, ctx, bundle)
    env = rules.clean_environment(bundle.get("ce"))
    if bundle.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個內容包是給另一個代理的 (the bundle is for another agent)")
    facts = own_facts(ctx)
    token = job.get("run_token")
    if not isinstance(token, str) or not token or len(token) > 200:
        raise rules.Refusal("平台沒有給這次執行的 token (no run token was sent)")
    source = bundle.get("pipeline_source")
    is_composed = isinstance(source, dict) and source.get("kind") == "composed"
    if is_composed != ("project" in bundle):
        raise rules.Refusal("組合管線的內容包必須同時有 project 與 composed 來源，兩者缺一不可 "
                            "(a composed bundle needs both its project and its composed source)")
    composed = {"pipeline_id": source.get("pipeline_id"), "version": source.get("version"), "project": bundle["project"]} if is_composed else None
    try:
        rebuilt = render_bundle(ce=bundle["ce"], agent=bundle["agent"], facts=facts, roots=rules.allowed_roots(env, ctx.settings_file),
                                run_name=bundle["run_name"], pipeline=bundle["pipeline"], revision=bundle["revision"],
                                samplesheet=bundle["samplesheet"], params=bundle["params"], path_columns=bundle["path_columns"],
                                composed=composed)
    except (BundleError, KeyError, TypeError) as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    if rebuilt != {k: v for k, v in bundle.items() if k not in RECORDS}:      # the records of the upload-area paths and of a relaunch are the platform's; the first is checked below
        why = "帳號與部署設定不符" if rebuilt.get("account") != bundle.get("account") else "內容與代理依自己的設定重新產生的不一致"
        raise rules.Refusal("%s：不送出 (the bundle is not what this agent builds from its own settings)" % why)
    _prechecks(job, ctx, preflight, env, bundle, bundle)
    site = ctx.site
    run, folder, work = bundle["run_name"], bundle["run_folder"], env["workDir"]

    res = site.call(["mkdir -p %s" % quote(work + "/runs")])
    if res.rc != 0:
        return "error", {"ok": False, "message": "站台上建不起 %s/runs（結束碼 %d）；沒有建立專屬資料夾 (nothing was made)" % (work, res.rc)}
    files = [(name, bundle["files"][name].encode("utf-8")) for name in FILE_NAMES] + [("tower.token", token.encode("utf-8"))]
    if composed is not None:      # the project goes below the run's own folder, in the same unpack: no shared folder, nothing skipped for an equal copy
        files += [("pipeline/" + rel, bundle["project"][rel].encode("utf-8")) for rel in sorted(bundle["project"])]
    res = site.call(["umask 077; mkdir %s && tar -x --no-same-owner -C %s" % (quote(folder), quote(folder))],
                    input=_tar(files), timeout=120)
    if res.rc != 0:
        if "File exists" in res.err:
            raise rules.Refusal("專屬資料夾 %s 已存在，不覆蓋；請換一個 run 名稱。沒有改動任何東西 (the run folder exists already)" % folder)
        left = "資料夾 %s 可能已建立，檔案可能不完整，尚未送出" % folder
        return "error", {"ok": False, "message": "寫入專屬資料夾時出錯（結束碼 %d）。%s" % (res.rc, left), "left_on_site": left}
    return _submit(job, ctx, folder, run, "head.sh", "資料夾 %s 與其中的檔案已寫好，尚未送出（工作期限剩下的時間不足）" % folder)


def _prechecks(job, ctx, preflight, env, bundle, shape):
    """What a launch and a resume ask before they touch the site: the record of the upload paths (116b), the time left, the preflight of
    007, the container cache and the way back to the platform. `shape` is the bundle that holds the environment's variables and the way
    back (`tower`): the bundle itself for a launch, the origin as the agent rebuilt it for a resume."""
    if "upload_paths" in bundle:
        _check_upload_paths(bundle["upload_paths"], ctx)
    if _left(ctx, job) < _min_remaining():
        raise rules.Refusal("工作期限剩下的時間不足以安全送出 (too little of the deadline is left to submit safely)")
    site = ctx.site
    verdict = preflight(env, ctx)
    failed = [c for c in verdict["checks"] if c["status"] != "pass"]
    if failed:
        raise rules.Refusal("預檢未通過，沒有建立任何東西：" + "；".join("%s（%s）" % (c["name"], c["detail"]) for c in failed))
    cache = next((e["value"] for e in shape["ce"].get("environment", []) if e.get("name") == "NXF_SINGULARITY_CACHEDIR" and e.get("head", True)), None)
    if cache:
        if rules.path_problem(cache):
            raise rules.Refusal("NXF_SINGULARITY_CACHEDIR 不是合法的路徑 (not a plain path)")
        c = quote(cache)
        res = site.call(["if test -d %s; then test -w %s && echo cache=ok || echo cache=no; else d=$(dirname %s); "
                         "test -d \"$d\" && test -w \"$d\" && echo cache=ok || echo cache=no; fi" % (c, c, c)])
        if "cache=ok" not in res.out.decode("utf-8", errors="replace"):
            raise rules.Refusal("容器快取 NXF_SINGULARITY_CACHEDIR=%s 不可寫；請改成可寫的資料夾後再試，沒有建立任何東西 (the container cache "
                                "cannot be written)" % cache)
    if shape["tower"]["mode"] == "forward":
        _channel(ctx, shape)


def _submit(job, ctx, folder, run, script, written):
    """The last step of a launch and of a resume: the time left, then ONE sbatch of folder/script, and the answer in the same words."""
    site = ctx.site
    if _left(ctx, job) < _min_remaining():
        return "error", {"ok": False, "message": "不送出：" + written, "left_on_site": written}
    # Slurm opens the job's output file (slurm-<id>.out) with the umask of whoever submits; 077 keeps it 0600
    res = site.call(["umask 077; sbatch %s" % quote(folder + "/" + script)], timeout=120)
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


# ======================================================================================================================
# A resume (spec 009e): the same run folder, one new head script, one new token
# ======================================================================================================================

def _site_user(settings_file):
    from .cancel import site_user      # cancel.py imports this module, so it is read here and not at the top
    user = site_user(settings_file)
    if not user or not re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z", user):
        raise rules.Refusal("部署設定沒有 site_user，無法確認前一次已經結束，不續跑 (site_user is not set)")
    return user


def _probe(folder, of_run, user, script):
    """ONE question to the site about the folder of a resume. Every line of the answer is `key=value`; nothing is written or run."""
    f, s = quote(folder), quote(script)
    return ("f=%s; "
            'if [ -d "$f" ] && [ "$(realpath -- "$f")" = "$f" ]; then echo dir=ok; else echo dir=no; fi; '
            'if [ -e "$f"/%s ] || [ -L "$f"/%s ]; then echo head=exists; else echo head=free; fi; '
            'if [ -L "$f"/tower.token ]; then echo token=link; else echo token=ok; fi; '
            'echo session=$(cut -f6 "$f"/.nextflow/history 2>/dev/null | grep -m1 -E %s); '
            '(cd "$f" 2>/dev/null && sha256sum -- %s 2>/dev/null | sed %s); '
            'q=$(squeue -h -n %s -u %s 2>&1); echo squeue_rc=$?; echo alive=$(printf "%%s\\n" "$q" | grep -c .)'
            % (f, s, s, quote("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"), " ".join(FILE_NAMES), quote("s/^/sha=/"),
               quote("nf-" + of_run), quote(user)))


def _check_folder(folder, answer, resume, origin, script):
    """The refusal (rules.Refusal) when what the site says of the folder is not what was confirmed; None when it is."""
    def stop(why):
        return rules.Refusal("續跑的專屬資料夾 %s %s；沒有改動任何東西 (nothing was changed)" % (folder, why))

    values = {}
    for line in answer.splitlines():
        key, _, value = line.partition("=")
        values.setdefault(key, []).append(value)
    one = lambda key: (values.get(key) or [""])[0].strip()
    if one("dir") != "ok":
        return stop("不是一個一般的資料夾（不存在，或要經過捷徑才到得了）(not a plain folder: missing, or reached through a link)")
    if one("head") != "free":
        return stop("裡已經有 %s，不覆蓋 (%s exists already)" % (script, script))
    if one("token") != "ok":
        return stop("裡的 tower.token 是捷徑 (tower.token is a link)")
    if one("session").lower() != resume["session_id"].lower():
        return stop("的 .nextflow/history 裡第一個 session 不是 %s（是 %s）(the session of the folder is not the one confirmed)"
                    % (resume["session_id"], one("session") or "沒有"))
    seen = {}
    for entry in values.get("sha", []):
        digest, _, name = entry.partition("  ")
        seen[name.strip()] = digest.strip()
    for name in FILE_NAMES:
        if seen.get(name) != hashlib.sha256(origin["files"][name].encode("utf-8")).hexdigest():
            return stop("裡的 %s 和第一次送出時寫下的不一樣，或不見了 (%s is not what the first launch wrote)" % (name, name))
    if one("squeue_rc") != "0":
        return stop("無法確認前一次是否已經結束（查 Slurm 佇列失敗）(could not ask the queue)")
    if one("alive") != "0":
        return stop("的前一次（Slurm 工作 nf-%s）還在佇列裡，還活著 (the predecessor is still in the queue)" % resume["of_run"])
    return None


def _as_current(bundle):
    """A bundle made before the site keys existed, read as the current shape: no modules, no site config, started from the remote."""
    out = dict(bundle)
    out["ce"] = dict(bundle.get("ce") or {})
    for k in SITE_KEYS:
        out["ce"].setdefault(k, [])
    out.setdefault("pipeline_source", dict(REMOTE))
    return out


def run_resume(job, ctx, preflight, bundle):
    """(state, result) of a confirmed resume: the bundle is judged exactly as a launch is (rebuilt from this agent's own facts), then the
    folder is looked at on the site in one question, and only if all of it agrees are head-N.sh and a new tower.token written into it
    (nothing else, nothing deleted) and ONE sbatch made."""
    resume = bundle.get("resume")
    origin_ce = (resume.get("origin") or {}).get("ce") if isinstance(resume, dict) and isinstance(resume.get("origin"), dict) else None
    if any(isinstance(ce, dict) and ce.get("platform") == GCB for ce in (bundle.get("ce"), origin_ce)):
        raise rules.Refusal(GCB_NO_RESUME)      # a Google Batch run cannot be resumed yet, whatever the platform sent
    if not isinstance(resume, dict) or set(resume) != RESUME_KEYS or not isinstance(resume.get("origin"), dict):
        raise rules.Refusal("續跑的內容包欄位不對 (the resume bundle has other fields than it should)")
    origin = resume["origin"]
    if (origin.get("pipeline_source") or {}).get("kind") == "composed" or "project" in origin:
        raise rules.Refusal(COMPOSED_NO_RESUME)
    env = rules.clean_environment(origin.get("ce"))
    if bundle.get("agent") != ctx.agent_name or origin.get("agent") != ctx.agent_name:
        raise rules.Refusal("這個內容包是給另一個代理的 (the bundle is for another agent)")
    token = job.get("run_token")
    if not isinstance(token, str) or not token or len(token) > 200:
        raise rules.Refusal("平台沒有給這次執行的 token (no run token was sent)")
    folder, work = bundle.get("run_folder"), env["workDir"]
    if (not isinstance(folder, str) or rules.path_problem(folder) or folder != origin.get("run_folder")
            or rules.normalize(folder) == work + "/runs" or not rules.inside(rules.normalize(folder), [work + "/runs"])):
        raise rules.Refusal("續跑的專屬資料夾必須就是第一次送出的那個，且在 %s/runs 之下 (the run folder is not the one of the first launch, "
                            "or not below the runs folder)" % work)
    try:
        rebuilt = render_bundle(ce=origin["ce"], agent=origin["agent"], facts=own_facts(ctx), roots=rules.allowed_roots(env, ctx.settings_file),
                                run_name=origin["run_name"], pipeline=origin["pipeline"], revision=origin["revision"],
                                samplesheet=origin["samplesheet"], params=origin["params"], path_columns=origin["path_columns"])
    except (BundleError, KeyError, TypeError) as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    if rebuilt != {k: v for k, v in _as_current(origin).items() if k not in RECORDS}:
        why = "帳號與部署設定不符" if rebuilt.get("account") != origin.get("account") else "內容與代理依自己的設定重新產生的不一致"
        raise rules.Refusal("%s：不續跑 (the origin is not what this agent builds from its own settings)" % why)
    try:
        expected = render_resume_bundle(origin=rebuilt, run_name=bundle.get("run_name"), attempt=resume["attempt"],
                                        session_id=resume["session_id"], of_run=resume["of_run"], of_slurm_job_id=resume["of_slurm_job_id"])
    except BundleError as e:
        raise rules.Refusal("內容不合規則：%s" % e)
    expected["resume"]["origin"] = origin      # the records the platform added to it (upload paths, relaunch) were taken out above; it is the same origin
    shown = {k: v for k, v in bundle.items() if k != "upload_paths"}
    shown["ce"] = _as_current(bundle)["ce"]
    if expected != shown:
        raise rules.Refusal("內容與代理依自己的設定重新產生的不一致：不續跑 (the bundle is not what this agent builds from its own settings)")
    script = "head-%d.sh" % resume["attempt"]
    run = bundle["run_name"]
    user = _site_user(ctx.settings_file)
    _prechecks(job, ctx, preflight, env, bundle, rebuilt)
    site = ctx.site
    res = site.call([_probe(folder, resume["of_run"], user, script)])
    if res.rc != 0:
        raise rules.Refusal("續跑的專屬資料夾 %s 查不了（結束碼 %d）；沒有改動任何東西 (the folder could not be looked at)" % (folder, res.rc))
    refusal = _check_folder(folder, res.out.decode("utf-8", errors="replace"), resume, origin, script)
    if refusal is not None:
        raise refusal
    files = [(script, bundle["files"][script].encode("utf-8")), ("tower.token", token.encode("utf-8"))]
    res = site.call(["umask 077; tar -x --no-same-owner -C %s" % quote(folder)], input=_tar(files), timeout=120)
    if res.rc != 0:
        left = "資料夾 %s 裡的 %s 與 tower.token 可能不完整，尚未送出" % (folder, script)
        return "error", {"ok": False, "message": "寫入專屬資料夾時出錯（結束碼 %d）。%s" % (res.rc, left), "left_on_site": left}
    return _submit(job, ctx, folder, run, script, "資料夾 %s 裡的 %s 與 tower.token 已寫好，尚未送出（工作期限剩下的時間不足）" % (folder, script))
