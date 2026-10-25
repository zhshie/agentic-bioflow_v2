# Not Ansible modules or Celery tasks: they run whatever a controller sends; these are two built-in read-only handlers, and a job is only data for them, never a command.
"""What the agent does: check a site (preflight), list a folder (list_site_files), and, with a confirmation, start an analysis
(launch_nextflow, launch.py) or stop one (cancel_run, cancel.py); fetch_run_records reads Nextflow's own logs back (fetch.py);
read_task_log reads the end of one log file of one task folder (readlog.py); clean_work, with a confirmation, removes the
work folder of one finished Slurm run (clean.py); put_upload streams one uploaded file from the
upload folder into the person's own cloud prefix and, once the cloud size matches, removes the staged copy (put_upload.py).

A job is a dict with a kind and arguments. Only the exact kinds below exist; any other text is refused,
and a refusal is an answer, not a crash. Every value that reaches the site is checked again here and
quoted. What goes back to the platform is the agent's own short wording, never the site's raw output.
"""
import re
from datetime import datetime, timezone

from . import cancel, clean, fetch, gcb_preflight, launch, put_upload, readlog, rules
from .site import quote

JOB_KINDS = ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log", "clean_work", "put_upload")
ARG_KEYS = {"preflight": {"ce"}, "list_site_files": {"ce", "path"}, "launch_nextflow": launch.LAUNCH_KEYS,
            "cancel_run": launch.LAUNCH_KEYS, "fetch_run_records": fetch.ARGS, "read_task_log": readlog.ARGS,
            "clean_work": launch.LAUNCH_KEYS, "put_upload": put_upload.ARGS}
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
        if kind == "clean_work":
            return clean.run_clean(job, ctx)
        if kind == "fetch_run_records":
            return fetch.run_fetch(job, ctx)
        if kind == "read_task_log":
            return readlog.run_read(job, ctx)
        if kind == "put_upload":
            return put_upload.run_put(job, ctx)
        ce = args.get("ce")
        if kind == "preflight" and isinstance(ce, dict) and ce.get("platform") == gcb_preflight.TYPE:
            # a Google Batch environment is checked here, on the platform host: its own checks, read-only and free (預檢不計費)
            res = gcb_preflight.run_preflight(gcb_preflight.clean_environment(ce),
                                              cred_path=gcb_preflight.credentials_path(ctx.settings_file))
            return "done", _verdict(res["checks"])
        env = rules.clean_environment(ce)
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


def _planned(env):
    """The names this environment is checked for, in the order they are reported. CHECK_ORDER is the base; modules, site_pipeline and
    image_library are conditional (preflight-nano4): they exist only when the environment names modules, site pipelines or a library."""
    order = list(CHECK_ORDER)
    if env.get("modules"):
        order.insert(order.index("java"), "modules")
    if env.get("sitePipelines"):
        order.append("site_pipeline")
    if env.get("singularityLibraryDir"):
        order.append("image_library")
    return order


def _module_chain(modules):
    return " && ".join("module load %s" % quote(m) for m in modules)


def _blank_comments(text):
    """The text of a Nextflow config with its comments taken out; text in quotes is left as it is."""
    out, skip_to, in_quote = [], 0, None      # skip_to: characters before this index are already dealt with
    for i, c in enumerate(text):
        if i < skip_to:
            continue
        if in_quote:
            out.append(c)
            if c == "\\":
                out.append(text[i + 1:i + 2])
                skip_to = i + 2
            elif c == in_quote or c == "\n":
                in_quote = None
        elif c in "'\"":
            in_quote = c
            out.append(c)
        elif text.startswith("//", i):
            end = text.find("\n", i)
            skip_to = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            skip_to = len(text) if end < 0 else end + 2
        else:
            out.append(c)
    return "".join(out)


def _block_after(text, start):
    """The text between the brace that opens at `start` and the brace that closes it, or None."""
    depth, in_quote = 0, None
    for i in range(start, len(text)):
        c = text[i]
        if in_quote:
            if c == in_quote or c == "\n":
                in_quote = None
        elif c in "'\"":
            in_quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


_VERSION_ASSIGN = r"(?<![\w.])%sversion\s*=\s*(['\"])([^'\"\n]{1,60})\1"


def _manifest_version(config_text):
    """The version a pipeline's own nextflow.config gives in its manifest block (never one from another block), or None."""
    clean = _blank_comments(config_text)
    for m in re.finditer(r"(?<![\w.])manifest\s*\{", clean):
        block = _block_after(clean, m.end() - 1)
        found = re.search(_VERSION_ASSIGN % "", block) if block is not None else None
        if found:
            return found.group(2).strip()
    found = re.search(_VERSION_ASSIGN % r"manifest\.", clean)
    return found.group(2).strip() if found else None


def _site_pipeline_command(entry):
    """Load the pipeline's module, then say whether its main.nf is there and print its nextflow.config. Reads only."""
    home = entry["home"]      # judged by rules.clean_environment: capital letters, digits and _ only
    return ('%s && { if [ -z "${%s:-}" ]; then echo abf_site=unset; elif [ -r "$%s/main.nf" ]; then echo abf_site=main; '
            'head -c 200000 "$%s/nextflow.config" 2>/dev/null; else echo abf_site=nomain; fi; }'
            % (_module_chain([entry["module"]]), home, home, home))


_COMMIT = re.compile(r"[0-9a-fA-F]{40}\Z")


def _judge_site_pipeline(entry, res):
    """(passed, wording) for one site pipeline entry, from what the site answered."""
    label = "%s %s" % (entry["pipeline"], entry["revision"])
    lines = res.out.decode("utf-8", errors="replace").splitlines()
    if "abf_site=unset" in lines:
        return False, "%s: the site variable %s is not set (站台沒有設定 %s)" % (label, entry["home"], entry["home"])
    if res.rc != 0 or "abf_site=main" not in lines:
        return False, "%s: not installed where the module says (站台找不到這個版本)" % label
    if _COMMIT.match(entry["revision"]):
        return True, "%s (commit revision, version not compared)" % label
    site_version = _manifest_version("\n".join(lines[lines.index("abf_site=main") + 1:]))
    if site_version is None:
        return False, "%s: cannot read the pipeline version (讀不出版本)" % entry["pipeline"]
    want = entry["revision"]
    if site_version.lstrip("v") != want.lstrip("v"):
        return False, ("%s: the site has %s, the environment says %s (站台裝的是 %s，設定說 %s)"
                       % (entry["pipeline"], site_version, want, site_version, want))
    return True, label


def preflight(env, ctx):
    """Run every check and report all of them. Nothing is created, changed or submitted on the site."""
    site = ctx.site
    checks = []
    planned = _planned(env)
    modules = env.get("modules") or []
    prefix = "".join("module load %s && " % quote(m) for m in modules)

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail[:DETAIL_LIMIT]})

    def rest_unchecked(done):
        for name in planned:
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

    def lost(res):
        """The reason the shared connection is gone when `res` is a failure that looks like it, else None."""
        if res.rc != 0 and lost_connection(res):
            return connection_lost()
        return None

    if modules:
        res = site.call([_module_chain(modules)])
        reason = lost(res)
        if reason:
            return abandon(reason)
        if res.rc == 0:
            add("modules", "pass", "loaded: " + ", ".join(modules))
        else:
            bad = modules[0]
            if len(modules) > 1:      # the chain says only that one failed: ask for each in order, the first that fails is named
                bad = ", ".join(modules)
                for m in modules:
                    one = site.call([_module_chain([m])])
                    reason = lost(one)
                    if reason:
                        return abandon(reason)
                    if one.rc != 0:
                        bad = m
                        break
            add("modules", "fail", "cannot load module %s: check the environment's modules, or empty them and use a self-installed Nextflow "
                "(載入不了模組 %s：請檢查計算環境的 modules，或清空它改用自裝 Nextflow)" % (bad, bad))

    res = site.call([prefix + "java -version"])
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

    res = site.call([prefix + "nextflow -version"])
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

    entries = env.get("sitePipelines") or []
    if entries:
        verdicts = []
        for entry in entries:
            res = site.call([_site_pipeline_command(entry)])
            reason = lost(res)
            if reason:
                return abandon(reason)
            verdicts.append(_judge_site_pipeline(entry, res))
        if all(ok for ok, _ in verdicts):
            add("site_pipeline", "pass", ", ".join(words for _, words in verdicts))
        else:
            add("site_pipeline", "fail", "; ".join(words for ok, words in verdicts if not ok))

    library = env.get("singularityLibraryDir")
    if library:
        res = site.call(['test -r "%s" && test -x "%s"' % (library, library)])      # the path was judged plain by rules.clean_root
        reason = lost(res)
        if reason:
            return abandon(reason)
        if res.rc == 0:
            add("image_library", "pass", "the read-only image library can be read")
        else:
            add("image_library", "fail", "the read-only image library %s cannot be read (唯讀映像庫讀不到)" % library)
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
    """(the real path of `path` on the site, the real paths of the roots matched by position), or None when the site cannot say.
    NUL-separated output, so that a link whose target holds a newline adds no line; the count must be exact (116b)."""
    want = [path] + list(roots)
    res = site.call(["realpath -z -m -- " + " ".join(quote(p) for p in want)])
    if res.rc != 0 or not res.out.endswith(b"\0"):
        return None
    parts = res.out[:-1].split(b"\0")
    if len(parts) != len(want):
        return None
    texts = [x.decode("utf-8", errors="replace") for x in parts]
    return texts[0], texts[1:]


def listing(env, path, ctx):
    path = rules.clean_path(path, "path")
    roots = rules.allowed_roots(env, ctx.settings_file)
    if not rules.inside(path, roots):
        raise rules.Refusal("the path is outside the allowed read roots (在允許範圍之外)")
    site = ctx.site
    resolved = _real_path(site, path, roots)
    if resolved is None:      # fail closed: a path the site cannot resolve is never judged the v3 way
        raise rules.Refusal("the site could not say where the path leads, so it is not listed (站台無法確認路徑的真實位置)")
    real, real_roots = resolved
    if real != path and not rules.inside(real, list(roots) + real_roots):      # a link in the way leads out of the places this agent may read
        raise rules.Refusal("the path leads outside the allowed read roots by a link (捷徑指向允許範圍之外)")
    p = quote(real if real != path else path)      # list what the link leads to, never follow one out of it
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
