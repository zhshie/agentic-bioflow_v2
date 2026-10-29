# Not scp or rsync of a whole folder: those copy what they are told to; this reads one named regular file of one run, once, and says no to everything else.
"""The read_run_file job (results-files): read-only.

It hands the platform the bytes of ONE regular file in the results folder of one run, so that a person can download it from the web
without logging in to the site. The platform sends only the environment, the run name and a path that is relative to `results/`; the
folder of the run is put together here (<workDir>/runs/<run>/results, a resumed run uses the folder of its first run), so the platform
cannot name any other place.

Rules, all judged again here whatever the platform judged: the path is plain text of at most 512 characters, relative, with no empty
part and no part that starts with a dot (so no `..` and no hidden name) and no control character; the real path (links followed) must lie
inside the places this agent may read AND inside the real results folder of the run; it must be a regular file; it must not be larger
than 25 MB, and a larger one is never read (only its size is asked). The content goes out base64-encoded, whole, never cut. Every value
reaches the site quoted. A cloud environment has no results on the site host, so nothing is sent anywhere for it. Nothing is written,
created or run on the site besides the three reading commands below.
"""
import base64
import re

from . import launch, rules
from .site import quote

ARGS = {"ce", "run", "path"}
MAX_BYTES = 26214400            # 25 MB; the platform holds the same number, written separately
MAX_PATH = 512
NOT_ON_SITE = "此環境的結果檔不在站台主機上 (the results of this environment are not on the site host)"
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def path_problem(value):
    """None for a path that may be read: text, 1 to 512 characters, relative, every part non-empty and not starting with a dot, no control character."""
    if not isinstance(value, str) or not value:
        return "the path is missing"
    if len(value) > MAX_PATH:
        return "the path is longer than %d characters" % MAX_PATH
    if _CONTROL.search(value):
        return "the path contains a control character"
    if value.startswith("/"):
        return "the path must be relative to the results folder"
    for part in value.split("/"):
        if not part:
            return "the path has an empty part"
        if part.startswith("."):
            return "a part of the path starts with a dot (含 .. 或隱藏名稱)"
    return None


def _failure(code, text, **more):
    return "error", dict({"ok": False, "error": code, "message": text}, **more)


def _run_folder(site, work, run):
    """<work>/runs/<run>, or for a resume attempt (<root>-aN) whose own folder is not there, the folder of <root>."""
    first = "%s/runs/%s" % (work.rstrip("/"), run)
    m = launch.RESUME_NAME.match(run)
    if not m or not launch.RUN_NAME.match(m.group(1)):
        return first
    root = "%s/runs/%s" % (work.rstrip("/"), m.group(1))
    res = site.call(["find -P %s %s -maxdepth 0 -type d -printf %s" % (quote(first), quote(root), quote("%p\\0"))])
    seen = {x.decode("utf-8", errors="replace") for x in res.out.split(b"\0") if x}
    return first if first in seen or root not in seen else root


def run_read(job, ctx):
    from . import handlers          # the realpath and failure helpers of list_site_files; handlers imports this module
    args = job["args"]
    absent = sorted(ARGS - set(args))
    if absent:
        raise rules.Refusal("the job lacks an argument: %s" % absent[0])
    ce = args.get("ce")
    if isinstance(ce, dict) and ce.get("platform") != rules.SLURM:
        return _failure("not_on_site", NOT_ON_SITE)
    env = rules.clean_environment(ce)
    run, path = args.get("run"), args.get("path")
    if not isinstance(run, str) or not launch.RUN_NAME.match(run):
        raise rules.Refusal("the run name is not a run name of this platform (run 名稱不對)")
    problem = path_problem(path)
    if problem:
        raise rules.Refusal("%s (路徑不正確)" % problem)
    roots = rules.allowed_roots(env, ctx.settings_file)
    site = ctx.site
    folder = _run_folder(site, env["workDir"], run)
    results = folder + "/results"
    full = results + "/" + path
    resolved = handlers._real_path(site, full, [results] + list(roots))
    if resolved is None:      # fail closed: a path the site cannot resolve is never read
        raise rules.Refusal("the site could not say where the path leads, so it is not read (站台無法確認路徑的真實位置)")
    real, real_roots = resolved
    real_results, real_roots = real_roots[0], real_roots[1:]
    if not rules.inside(real, list(roots) + real_roots):
        raise rules.Refusal("the file lies outside the allowed read roots (在允許範圍之外)")
    if not rules.inside(real, [real_results]) or real == real_results:
        raise rules.Refusal("the path leads out of the results folder by a link (捷徑指向 results 資料夾之外)")
    target = quote(real)
    kind = site.call(["find -P %s -maxdepth 0 -printf %s" % (target, quote("%y\\t%s"))])
    said = kind.out.decode("utf-8", errors="replace").strip() if kind.rc == 0 else ""
    if kind.rc != 0 and (handlers.lost_connection(kind) or "No such file" not in kind.err):
        return handlers._failure("site_unreachable", handlers._site_down(site, kind))
    if not said:
        return _failure("not_found", "the file does not exist on the site (站台沒有此檔案)")
    letter, _, size_text = said.partition("\t")
    if letter != "f":
        return _failure("not_a_file", "the path is not a plain file (不是一般檔案)")
    try:
        size = int(size_text)
    except ValueError:
        return handlers._failure("site_unreachable", "the site gave no size for the file")
    if size > MAX_BYTES:
        return _failure("too_large", "the file is larger than %d bytes, so it is not read (超過網頁下載上限)" % MAX_BYTES, size=size, path=real)
    # one fixed command: find re-checks that it is still a regular file within the limit, and base64 prints it
    res = site.call(["find -P %s -maxdepth 0 -type f -size -%dc -exec base64 {} \\;" % (target, MAX_BYTES + 1)], timeout=60)
    if res.rc != 0:
        return handlers._failure("site_unreachable", handlers._site_down(site, res))
    b64 = re.sub(rb"\s+", b"", res.out).decode("ascii", errors="replace")
    try:
        got = len(base64.b64decode(b64, validate=True))
    except ValueError:
        got = -1
    if got != size:      # the file changed while it was read, or the answer is broken: nothing is sent
        return _failure("changed", "the file changed while it was read, so nothing was sent (讀取時檔案已改變)")
    return "done", {"ok": True, "status": "ok", "name": path.rsplit("/", 1)[-1], "size": size, "b64": b64}
