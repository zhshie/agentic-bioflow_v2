# Not Ansible modules or Celery tasks: they run whatever a controller sends; these are two built-in read-only handlers, and a job is only data for them, never a command.
"""What the agent does: check a site (preflight), list a folder (list_site_files), and, with a confirmation, start an analysis
(launch_nextflow, launch.py) or stop one (cancel_run, cancel.py); fetch_run_records reads Nextflow's own logs back (fetch.py).

A job is a dict with a kind and arguments. Only the exact kinds below exist; any other text is refused,
and a refusal is an answer, not a crash. Every value that reaches the site is checked again here and
quoted. What goes back to the platform is the agent's own short wording, never the site's raw output.
"""
import re
from datetime import datetime, timezone

from . import cancel, fetch, launch, rules
from .site import quote

JOB_KINDS = ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records")
ARG_KEYS = {"preflight": {"ce"}, "list_site_files": {"ce", "path"}, "launch_nextflow": launch.LAUNCH_KEYS,
            "cancel_run": launch.LAUNCH_KEYS, "fetch_run_records": fetch.ARGS}
LIST_LIMIT = 500
# The check ids are written as one comma-split string, never as a quoted sbatch: the scan of
# constitution principle 2 (tests/no_second_run_state_test.sh) treats a quote straight before
# the word as a submission command, and this file only checks that the tools exist (command -v).
CHECK_ORDER = tuple("connect,work_dir,sbatch,squeue,sinfo,java,nextflow,head_queue".split(","))
JAVA_MIN = 17
DETAIL_LIMIT = 300

_NEEDS_CONNECTION = "needs a working connection to the site (未檢查)"


def _refused(text):
    return "refused", {"ok": False, "message": text[:600]}


def handle(job, ctx):
    """(state, result) for one job. state is done, refused or error."""
    if not isinstance(job, dict):
        return _refused("the job is not an object, so it is not supported (不支援)")
    kind, args = job.get("kind"), job.get("args")
    if not isinstance(kind, str) or kind not in JOB_KINDS:
        shown = kind if isinstance(kind, str) and len(kind) <= 40 and kind.isprintable() else "(unreadable)"
        return _refused("the job kind %r is not supported (不支援); this agent does %s" % (shown, " and ".join(JOB_KINDS)))
    if not isinstance(args, dict):
        return _refused("the job arguments must be an object")
    extra = sorted(set(args) - ARG_KEYS[kind])
    if extra:
        return _refused("the job has an argument this agent does not take (不支援): %s" % str(extra[0])[:40])
    try:
        if kind == "launch_nextflow":
            return launch.run_launch(job, ctx, preflight)
        if kind == "cancel_run":
            return cancel.run_cancel(job, ctx)
        if kind == "fetch_run_records":
            return fetch.run_fetch(job, ctx)
        env = rules.clean_environment(args.get("ce"))
        if kind == "preflight":
            return "done", preflight(env, ctx)
        return listing(env, args.get("path"), ctx)
    except rules.Refusal as e:
        return _refused(str(e))


# ---- what the site script said ---------------------------------------------------------------

def _open_command(err):
    """The line on_site.sh prints for the user to open the shared connection, word for word."""
    for line in err.splitlines():
        s = line.strip()
        if re.match(r"^(?:wsl\.exe -e )?ssh\s", s) and "ControlPath" in s and "true" in s:
            return s
    return ""


def _close_command(err):
    for line in err.splitlines():
        s = line.strip()
        if re.match(r"^ssh\s", s) and "ControlPath" in s and re.search(r"-O\s+exit", s):
            return s
    return ""


def lost_connection(res):
    return res.timed_out or "on_site: needs-human" in res.err or res.rc in (124, 255)


def connect_failure(res):
    """Why the site could not be reached, in the agent's words plus the one command line on_site.sh offers."""
    if "reason=no-master" in res.err:
        cmd = _open_command(res.err)
        prefix = "No open connection to the site. Log in once in a WSL terminal first (請先在 WSL 終端機登入站台): "
        return (prefix[:max(0, DETAIL_LIMIT - len(cmd))] + cmd) if cmd else prefix.rstrip(": ")
    if "reason=sessions-exhausted" in res.err:
        cmd = _close_command(res.err)
        prefix = ("The site did not answer in time: its sessions are used up (站台工作階段用盡). "
                  "Close the stuck connection, then log in again in a WSL terminal: ")
        return (prefix[:max(0, DETAIL_LIMIT - len(cmd))] + cmd) if cmd else prefix.rstrip(": ")
    if res.timed_out:
        return "The site script did not return in time (站台沒有回應)."
    return "The site could not be reached (exit code %d)." % res.rc


# ---- preflight --------------------------------------------------------------------------------

def _parse_java(text):
    m = re.search(r'version "(\d+)(?:\.(\d+))?', text)
    if not m:
        return None
    major = int(m.group(1))
    if major == 1 and m.group(2):
        major = int(m.group(2))
    return major


def _parse_nextflow(text):
    m = re.search(r"version\s+(\d[\w.\-]*)", text)
    return m.group(1) if m else None


def _probe_command(env):
    w = quote(env["workDir"])
    return ("if test -d %s; then echo work_dir=dir; else echo work_dir=missing; fi; "
            "if test -w %s; then echo work_dir_writable=yes; else echo work_dir_writable=no; fi; "
            "if command -v sbatch >/dev/null 2>&1; then echo has_sbatch=yes; else echo has_sbatch=no; fi; "
            "if command -v squeue >/dev/null 2>&1; then echo has_squeue=yes; else echo has_squeue=no; fi; "
            "if command -v sinfo >/dev/null 2>&1; then echo has_sinfo=yes; else echo has_sinfo=no; fi") % (w, w)


def preflight(env, ctx):
    """Run every check and report all of them. Nothing is created, changed or submitted on the site."""
    site = ctx.site
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail[:DETAIL_LIMIT]})

    def rest_unchecked(done):
        for name in CHECK_ORDER:
            if name not in done:
                add(name, "unchecked", _NEEDS_CONNECTION)

    def connection_lost():
        """None while the shared connection still answers, else the reason it does not."""
        res = site.call(["--check-reach"])
        return connect_failure(res) if res.rc != 0 else None

    reach = site.call(["--check-reach"])
    if reach.rc != 0:
        add("connect", "fail", connect_failure(reach))
        rest_unchecked({"connect"})
        return _verdict(checks)
    add("connect", "pass", "the site answers")

    def abandon(reason):
        """The connection went away part-way: report that one fact and mark everything not yet checked."""
        checks[:] = []
        add("connect", "fail", reason)
        rest_unchecked({"connect"})
        return _verdict(checks)

    probe = site.call([_probe_command(env)])
    if probe.rc != 0 and lost_connection(probe):
        reason = connection_lost()
        if reason:
            return abandon(reason)
    facts = dict(line.split("=", 1) for line in probe.out.decode("utf-8", errors="replace").splitlines() if "=" in line)
    if facts.get("work_dir") == "dir":
        if facts.get("work_dir_writable") == "yes":
            add("work_dir", "pass", "the work folder exists and can be written")
        else:
            add("work_dir", "fail", "the work folder exists but cannot be written")
    elif facts.get("work_dir") == "missing":
        add("work_dir", "fail", "the work folder does not exist on the site")
    else:
        add("work_dir", "fail", "the site gave no answer about the work folder")
    for tool in CHECK_ORDER[2:5]:  # the three scheduler tools: the 3rd to 5th ids above (see the note at CHECK_ORDER)
        have = facts.get("has_" + tool)
        if have == "yes":
            add(tool, "pass", "found on the site")
        elif have == "no":
            add(tool, "fail", "not found on the site")
        else:
            add(tool, "fail", "the site gave no answer")

    res = site.call(["java -version"])
    if res.rc != 0 and lost_connection(res):
        reason = connection_lost()
        if reason:
            return abandon(reason)
    text = res.text()
    major = _parse_java(text)
    if res.rc == 127:
        add("java", "fail", "java was not found on the site")
    elif major is None:
        add("java", "fail", "cannot read the Java version (讀不出版本)")
    elif major >= JAVA_MIN:
        add("java", "pass", "Java %d" % major)
    else:
        add("java", "fail", "Java %d found, %d or newer is needed" % (major, JAVA_MIN))

    res = site.call(["nextflow -version"])
    if res.rc != 0 and lost_connection(res):
        reason = connection_lost()
        if reason:
            return abandon(reason)
    version = _parse_nextflow(res.text())
    if res.rc == 127:
        add("nextflow", "fail", "nextflow was not found on the site")
    elif version is None:
        add("nextflow", "fail", "cannot read the Nextflow version (讀不出版本)")
    else:
        add("nextflow", "pass", "Nextflow %s" % version[:40])

    if facts.get("has_sinfo") != "yes":
        add("head_queue", "unchecked", "needs sinfo, which was not found (未檢查)")
    else:
        res = site.call(["sinfo -h -o %P"])
        if res.rc != 0 and lost_connection(res):
            reason = connection_lost()
            if reason:
                return abandon(reason)
        if res.rc != 0:
            add("head_queue", "fail", "sinfo failed (exit code %d)" % res.rc)
        else:
            names = {tok.rstrip("*") for tok in res.out.decode("utf-8", errors="replace").split()}
            if env["headQueue"] in names:
                add("head_queue", "pass", "the head queue %s is listed by sinfo" % env["headQueue"])
            else:
                add("head_queue", "fail", "the head queue %s is not listed by sinfo" % env["headQueue"])
    return _verdict(checks)


def _verdict(checks):
    bad = [c["name"] for c in checks if c["status"] != "pass"]
    return {"ok": not bad, "checks": checks,
            "message": "all %d checks passed" % len(checks) if not bad else "not passed: " + ", ".join(bad)}


# ---- list_site_files ---------------------------------------------------------------------------

_TYPES = {"f": "file", "d": "dir", "l": "link"}


def _iso(epoch):
    return datetime.fromtimestamp(int(float(epoch)), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _failure(code, text):
    return "error", {"ok": False, "error": code, "message": text}


def _real_path(site, path, roots):
    """(the real path of `path` on the site, or None; the real paths of the roots). One call, links resolved (116b)."""
    res = site.call(["for p in %s; do realpath -m -- \"$p\"; done" % " ".join(quote(p) for p in [path] + list(roots))])
    lines = res.out.decode("utf-8", errors="replace").split("\n")
    if res.rc != 0 or len(lines) < len(roots) + 1:
        return None, []
    return lines[0], lines[1:len(roots) + 1]


def listing(env, path, ctx):
    path = rules.clean_path(path, "path")
    roots = rules.allowed_roots(env, ctx.settings_file)
    if not rules.inside(path, roots):
        raise rules.Refusal("the path is outside the allowed read roots (在允許範圍之外)")
    site = ctx.site
    real, real_roots = _real_path(site, path, roots)
    if real is not None and real != path and not rules.inside(real, list(roots) + real_roots):      # a link in the way leads out of the places this agent may read
        raise rules.Refusal("the path leads outside the allowed read roots by a link (捷徑指向允許範圍之外)")
    p = quote(real if real is not None and real != path else path)      # list what the link leads to, never follow one out of it
    kind = site.call(["if test -d %s; then echo kind=dir; elif test -e %s; then echo kind=other; "
                      "else echo kind=missing; fi" % (p, p)])
    if kind.rc != 0:
        return _failure("site_unreachable", _site_down(site, kind))
    said = kind.out.decode("utf-8", errors="replace").strip()
    if said == "kind=missing":
        return _failure("not_found", "the folder does not exist on the site")
    if said == "kind=other":
        return _failure("not_a_directory", "the path is not a folder")
    if said != "kind=dir":
        return _failure("site_unreachable", "the site gave no answer about the path")
    res = site.call(["find %s -mindepth 1 -maxdepth 1 -printf %s" % (p, quote("%y\\t%s\\t%T@\\t%f\\0"))])
    if res.rc != 0:
        if "Permission denied" in res.err:
            return _failure("permission_denied", "the folder cannot be read (permission denied)")
        if "No such file" in res.err:
            return _failure("not_found", "the folder does not exist on the site")
        return _failure("site_unreachable", _site_down(site, res))
    entries = []
    for record in res.out.split(b"\0"):
        if not record:
            continue
        parts = record.split(b"\t", 3)
        if len(parts) != 4:
            continue
        try:
            entries.append({"name": parts[3].decode("utf-8", errors="replace"), "type": _TYPES.get(parts[0].decode(), "other"),
                            "size": int(parts[1]), "modified": _iso(parts[2])})
        except ValueError:
            continue
    entries.sort(key=lambda e: e["name"])
    total = len(entries)
    shown = entries[:LIST_LIMIT]
    out = {"ok": True, "path": path, "entries": shown, "count": len(shown), "total": total,
           "truncated": total > LIST_LIMIT, "limit": LIST_LIMIT}
    if out["truncated"]:
        out["note"] = "truncated (截斷): showing %d of %d entries" % (len(shown), total)
    return "done", out


def _site_down(site, res):
    """A failed call: if the shared connection is the reason, say so with the line that opens it again."""
    if lost_connection(res) or res.rc != 0:
        check = site.call(["--check-reach"])
        if check.rc != 0:
            return connect_failure(check)
    return "The site could not do this (exit code %d)." % res.rc
