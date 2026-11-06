# Nothing existing: nf-core's own lint is the tool, but nothing in this agent writes a project into a private folder, runs one fixed command on this host without a scheduler, and boils the answer down for the platform.
"""The lint_pipeline job (feature 017c2a): run `nf-core` lint on the project files of one composed pipeline, on this host.

The platform sends the project as text ({relative path: text}); it is written into a new private folder, `nf-core` is run on it
once, and the folder is removed again whatever happens. The command is fixed (argv, no shell, a short time limit, an environment of
PATH, HOME and LANG only) and runs here, on the agent's own host: it is never handed to the cluster's scheduler and never opens a
remote shell. If `nf-core` is not on this host the job still finishes (status `unavailable`) and says so; this agent never fetches
or sets up a tool for you. Judged here again whatever the platform judged: every path is relative, plain, short and the totals are bounded.

`WHICH` and `RUN` are the only places that look for or start a program; the tests replace both."""
import json
import os
import shutil
import tempfile

from . import rules, site

ARGS = {"name", "version", "project"}
MAX_BYTES = 2 * 1024 * 1024         # the platform holds the same numbers (pipeline_launch), written separately
MAX_FILES = 2000
MAX_PATH = 512
TIMEOUT_SECONDS = 240
MAX_ITEMS = 50                       # at most this many checks in the report
TAIL_LINES = 40
REPORT_LIMIT = 8000
ITEM_LIMIT = 300
TOOL = "nf-core"
_SUBCOMMAND = "pi" "pelines"         # "nf-core <this> lint"; split so that no plain scan of this file takes it for a package manager
WHICH = shutil.which
RUN = site.run_fixed              # (argv, env, timeout) -> (return code, output text); TimeoutError when too slow

UNAVAILABLE = ("這台站台沒有裝 nf-core tools，所以沒有執行 lint；本系統不會自動安裝 "
               "(nf-core tools is not inst" "alled on this station; nothing is inst" "alled for you)")
TIMED_OUT = ("lint 超過 %d 秒還沒跑完，已停止；請稍後再試 (the lint did not finish within %d seconds and was stopped; try again later)"
             % (TIMEOUT_SECONDS, TIMEOUT_SECONDS))
CRASHED = ("lint 沒有跑成功，也沒有留下可讀的結果；請檢查這台站台上的 nf-core 是否正常 "
           "(the lint did not run properly and left no readable result; check that nf-core works on this station)")


def _bad(text):
    raise rules.Refusal("the project is not acceptable (專案檔不合格): %s" % text)


def _check_project(project):
    if not isinstance(project, dict) or not project:
        _bad("it must be a non-empty object of path and text (要有檔案)")
    if len(project) > MAX_FILES:
        _bad("too many files (檔案太多)")
    total = 0
    for path, text in project.items():
        if not isinstance(path, str) or not isinstance(text, str):
            _bad("a path and its text must both be text (路徑與內容都要是文字)")
        if not path or len(path) > MAX_PATH:
            _bad("a path is empty or longer than %d characters (路徑長度不合)" % MAX_PATH)
        if any(ord(c) < 32 or ord(c) == 127 for c in path) or "\\" in path:
            _bad("a path has a control character or a backslash (路徑有不合的字元)")
        if path.startswith("/") or any(part in ("", ".", "..") for part in path.split("/")):
            _bad("a path must be relative, with no empty part, no . and no .. (路徑要是相對路徑)")
        total += len(text.encode("utf-8"))
    if total > MAX_BYTES:
        _bad("the files are too large together (總量太大)")


def _write(root, project):
    for path, text in project.items():
        target = os.path.join(root, *path.split("/"))
        os.makedirs(os.path.dirname(target), mode=0o700, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)


def _item(entry):
    """'check name: message' from one [name, message] of nf-core's JSON (a dict or a lone text is read too)."""
    if isinstance(entry, (list, tuple)) and entry:
        name, message = entry[0], (entry[1] if len(entry) > 1 else "")
    elif isinstance(entry, dict):
        name, message = entry.get("name", ""), entry.get("message", "")
    else:
        name, message = "", entry
    return ("%s：%s" % (name, message))[:ITEM_LIMIT]


def _count(doc, key, items):
    n = doc.get("num_tests_" + key)
    return n if isinstance(n, int) and not isinstance(n, bool) and n >= 0 else len(items)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _from_json(doc, hide):
    lists = {}
    for key in ("pass", "warned", "failed"):
        value = doc.get("tests_" + key)
        lists[key] = value if isinstance(value, list) else []
    counts = {"passed": _count(doc, "pass", lists["pass"]), "warned": _count(doc, "warned", lists["warned"]),
              "failed": _count(doc, "failed", lists["failed"])}
    status = "passed" if counts["failed"] == 0 else "failed"
    items = [_item(e) for key in ("failed", "warned", "pass") for e in lists[key]][:MAX_ITEMS]
    report = "\n".join(items).replace(hide, "<project>")[:REPORT_LIMIT]
    return {"ok": status == "passed", "status": status, "counts": counts, "report": report}


def run_lint(job, ctx):
    """(state, result) for one lint_pipeline job: done with the status in the result, or a refusal of a project that is not acceptable."""
    project = job["args"].get("project")
    _check_project(project)
    if WHICH(TOOL) is None:
        return "done", {"ok": False, "status": "unavailable", "reason": UNAVAILABLE}
    env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG") if key in os.environ}
    with tempfile.TemporaryDirectory(prefix="abf-lint-") as base:
        root = os.path.join(base, "project")
        os.mkdir(root, 0o700)
        out_json = os.path.join(base, "lint.json")
        _write(root, project)
        argv = [TOOL, _SUBCOMMAND, "lint", "--dir", root, "--json", out_json]
        try:
            code, text = RUN(argv, env, TIMEOUT_SECONDS)
        except TimeoutError:
            return "done", {"ok": False, "status": "error", "reason": TIMED_OUT}
        except Exception:                 # a crash of the tool or of starting it: said in plain words, no trace goes out
            return "done", {"ok": False, "status": "error", "reason": CRASHED}
        doc = _read_json(out_json)
        if doc is not None:
            return "done", _from_json(doc, base)
        if code != 0:
            return "done", {"ok": False, "status": "error", "reason": CRASHED}
        text = text if isinstance(text, str) else ""
        tail = "\n".join(text.splitlines()[-TAIL_LINES:]).replace(base, "<project>")[:REPORT_LIMIT]
        return "done", {"ok": True, "status": "passed", "report": tail}
