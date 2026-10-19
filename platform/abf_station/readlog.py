# Not `tail -f` over ssh or a log shipper: this reads the end of one of three named files of one task folder, once, never follows a link, never writes on the site.
"""The read_task_log job (run-diag-tools): read-only.

It reads the last lines of `.command.err`, `.command.out` or `.command.log` in the work folder of one task (the folder
Nextflow reported for a failed task). The folder must lie inside the places this agent may read, as for list_site_files;
the file name is one of the three, never anything else; a link in place of the file is refused (find -P says what the
entry is, and the file is read only if it is still a regular file when it is read). At most 200 lines and 64 KB are
sent, the last ones, and a cut is said. Nothing is written, created or run on the site.
"""
from . import rules
from .site import quote

FILES = (".command.err", ".command.out", ".command.log")
ARGS = {"ce", "workdir", "file"}
MAX_LINES = 200
MAX_BYTES = 64 * 1024


def cap(data):
    """(bytes, cut): the end of `data` within MAX_LINES lines and MAX_BYTES bytes, and whether anything was dropped."""
    cut = False
    if len(data) > MAX_BYTES:
        data, cut = data[-MAX_BYTES:], True
    kept = data.splitlines(True)
    if len(kept) > MAX_LINES:
        data, cut = b"".join(kept[-MAX_LINES:]), True
    return data, cut


def run_read(job, ctx):
    from . import handlers          # the realpath and failure helpers of list_site_files; handlers imports this module
    args = job["args"]
    absent = sorted(ARGS - set(args))
    if absent:
        raise rules.Refusal("the job lacks an argument: %s" % absent[0])
    env = rules.clean_environment(args.get("ce"))
    workdir = rules.clean_path(args.get("workdir"), "workdir")
    name = args.get("file")
    if name not in FILES:
        raise rules.Refusal("file must be one of %s (只能讀這三個檔案)" % ", ".join(FILES))
    roots = rules.allowed_roots(env, ctx.settings_file)
    if not rules.inside(workdir, roots):
        raise rules.Refusal("the task folder is outside the allowed read roots (在允許範圍之外)")
    site = ctx.site
    resolved = handlers._real_path(site, workdir, roots)
    if resolved is None:      # fail closed: a folder the site cannot resolve is never read
        raise rules.Refusal("the site could not say where the task folder leads, so it is not read (站台無法確認路徑的真實位置)")
    real, real_roots = resolved
    if real != workdir and not rules.inside(real, list(roots) + real_roots):
        raise rules.Refusal("the task folder leads outside the allowed read roots by a link (捷徑指向允許範圍之外)")
    target = quote("%s/%s" % (real.rstrip("/"), name))
    kind = site.call(["find -P %s -maxdepth 0 -printf %%y" % target])
    said = kind.out.decode("utf-8", errors="replace").strip() if kind.rc == 0 else ""
    if kind.rc != 0 and (handlers.lost_connection(kind) or "No such file" not in kind.err):
        return handlers._failure("site_unreachable", handlers._site_down(site, kind))
    if not said:
        return handlers._failure("not_found", "file not found in the task folder")
    if said == "l":
        raise rules.Refusal("%s is a link, so it is not read (符號連結已拒絕)" % name)
    if said != "f":
        raise rules.Refusal("%s is not a plain file, so it is not read (不是一般檔案)" % name)
    res = site.call(["find -P %s -maxdepth 0 -type f -exec tail -n %d {} \\; | tail -c %d" % (target, MAX_LINES + 1, MAX_BYTES + 1)],
                    timeout=60)
    if res.rc != 0:
        return handlers._failure("site_unreachable", handlers._site_down(site, res))
    data, cut = cap(res.out)
    text = data.decode("utf-8", errors="replace")
    if cut:
        text = text.lstrip("�")        # the cut may have fallen inside a character
    count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    note = " (截斷 truncated: the end of the file)" if cut else ""
    return "done", {"ok": True, "file": name, "text": text, "lines": count, "truncated": cut,
                    "message": "read the end of %s: %d lines%s" % (name, count, note)}
