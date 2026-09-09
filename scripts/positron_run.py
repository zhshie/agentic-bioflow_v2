#!/usr/bin/env python3
"""Run a file, or a snippet, in the console Positron already has open.

    positron_run.py --check
    positron_run.py --lang r      --file analysis/figures.R
    positron_run.py --lang python --file analysis/figures.py
    positron_run.py --lang r      --code 'sessionInfo()'

The point is the *live* session: plots land in the Plots pane and objects stay
in the Variables pane, which is what a batch `Rscript`/`python` run cannot do.
Batch is still the right tool for reproducing figures; this is for the step
where someone wants to see them in the IDE they already have open.

Why this file exists at all - nothing off the shelf does it:

  - the Positron CLI has --goto and extension management, no way to run code;
  - `positron.runtime.executeCode` and the `workbench.action.executeCode.*`
    commands are real, but reachable only from inside an extension;
  - Kallichore's own client is Rust, lives in its repo for testing, and is not
    shipped with Positron (only kcserver is). There is no client on PyPI.

What *is* off the shelf is the protocol. Kallichore's README describes the
supported path as "connect to the session, send and receive Jupyter messages",
and jupyter_client is that protocol's own library - it does the ZMQ sockets,
the HMAC signing and the message framing here. All this file adds is the two
GET calls that find the session, because that part has no library.

The R kernel is the reason those two calls are needed. positron-python writes
a full Jupyter connection file to disk, so a client can just read it. ark
writes only a registration stub - transport, key, and a registration port, no
channel ports - so the obvious read-the-file trick appears to be Python-only.
The ports are not secret, only absent: the supervisor hands them out at
GET /sessions/{id}/connection_info, for R exactly as for Python.

    supervisor connection file          ->  transport + bearer token
    GET /sessions                       ->  which session, is it free
    GET /sessions/{id}/connection_info  ->  the five ZMQ ports + HMAC key
    jupyter_client                      ->  execute_request

SECURITY - read before editing the reporting code. GET /sessions returns each
kernel's full `initial_env`, which on a developer's machine holds real
credentials; the first run of this against a live Positron surfaced a GitHub
PAT and several API keys. CLAUDE.md's rule is that credentials are never
printed. So nothing here prints a raw API response: every session is narrowed
to SESSION_FIELDS the moment it is parsed, and the bearer token and HMAC key
are never rendered. tests/positron_run_test.sh feeds in a fixture containing a
fake token and fails if it appears in the output.

This attaches to a session that already exists and never creates one. A tool
that quietly spawns a console in someone's IDE is a surprise; "open an R
console" is a one-click thing to be asked for.
"""
import argparse
import glob
import json
import os
import socket
import stat
import sys
import tempfile
import time

# Everything from a /sessions response that may leave this process. The point
# is the omission: `initial_env` and `argv` carry credentials and are dropped
# here, once, rather than at each print site where one would eventually be
# forgotten.
SESSION_FIELDS = (
    "session_id", "language", "display_name",
    "status", "working_directory", "execution_queue",
)

# Positron names these by the kernel's language, and the spelling is the
# kernel's, not ours.
LANGUAGES = {"r": "R", "python": "Python"}


# --------------------------------------------------------------------------
# Talking to the supervisor
#
# One HTTP client over three transports, because Kallichore picks a different
# one per platform: a named pipe on Windows, a Unix domain socket on macOS and
# Linux, and TCP when it is told to. Only the bytes underneath differ - the
# request is the same HTTP either way.
# --------------------------------------------------------------------------
class _PipeSock:
    r"""A named pipe with a socket's manners.

    Windows named pipes open as ordinary files; wrapping them here means
    _http_get does not need to care which transport it got.

    Open it with the OS's own path. Git Bash rewrites anything shaped like
    \\.\pipe\... into a POSIX path on the way to open(), and the failure is a
    FileNotFoundError naming a pipe that is plainly there - so run this under
    native python.exe, not under an MSYS shell.
    """

    def __init__(self, path):
        self._f = open(path, "r+b", buffering=0)

    def sendall(self, data):
        self._f.write(data)

    def recv(self, n):
        return self._f.read(n)

    def close(self):
        try:
            self._f.close()
        except OSError:
            pass


def _connect(sup):
    transport = sup.get("transport")
    if transport == "named-pipe":
        return _PipeSock(sup["named_pipe"])
    if transport == "socket":
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(sup["socket_path"])
        return s
    port = sup.get("port")
    if not port:
        raise RuntimeError(f"supervisor has transport {transport!r} but no port")
    return socket.create_connection((sup.get("ip", "127.0.0.1"), int(port)), timeout=10)


def endpoint_label(sup):
    """How to describe this supervisor without revealing its token."""
    transport = sup.get("transport")
    if transport == "named-pipe":
        return f"named-pipe {sup.get('named_pipe')}"
    if transport == "socket":
        return f"socket {sup.get('socket_path')}"
    return f"tcp {sup.get('ip', '127.0.0.1')}:{sup.get('port')}"


def _dechunk(body):
    out, rest = b"", body
    while rest:
        line, _, rest = rest.partition(b"\r\n")
        try:
            size = int(line.split(b";")[0], 16)
        except ValueError:
            break
        if size == 0:
            break
        out += rest[:size]
        rest = rest[size + 2:]
    return out


def _parse_response(buf, path):
    """Split an HTTP/1.1 response into (status line, decoded body).

    Its own function so a test can reach it. The socket path around it cannot
    be exercised without standing up a supervisor, and this is the half where
    the mistakes live - see the header-case bug that measurement turned up.

    Headers are matched case-insensitively because kcserver sends them
    lowercase. Measured, not assumed: GET /sessions against a live supervisor
    answers `content-type`, `connection: close`, `content-length: 18630`. The
    first version of this looked for `Transfer-Encoding: chunked` capitalised
    the way the RFC writes it, which this server will never send - so the
    chunked branch could not fire and a chunked body would have reached
    json.loads with its chunk-size lines still in it.
    """
    head, sep, body = buf.partition(b"\r\n\r\n")
    if not sep:
        raise RuntimeError("supervisor closed the connection without replying")
    lines = head.split(b"\r\n")
    status = lines[0].decode("latin-1")
    headers = {}
    for line in lines[1:]:
        name, _, value = line.partition(b":")
        headers[name.strip().lower()] = value.strip()
    if headers.get(b"transfer-encoding", b"").lower() == b"chunked":
        body = _dechunk(body)
    else:
        # Trust Content-Length over "whatever arrived before EOF" when the
        # server states one; a keep-alive reply would otherwise trail the next
        # response into this one.
        try:
            body = body[:int(headers[b"content-length"])]
        except (KeyError, ValueError):
            pass
    if " 200" not in status:
        # Deliberately not echoing the body: an error response from /sessions
        # can still carry environment data.
        raise RuntimeError(f"supervisor said {status.strip()!r} for {path}")
    return json.loads(body.decode("utf-8"))


def _http_get(sup, path):
    """GET `path` from a supervisor. Returns parsed JSON, or raises."""
    fixture = os.environ.get("POSITRON_RUN_FIXTURE")
    if fixture:
        # The test seam. Kallichore speaks over a pipe or a socket that no test
        # should have to stand up, so tests supply the responses as files.
        # Keyed by server_pid, not just by path, so a test can give two
        # supervisors different sessions - which is the whole of the two-open-
        # windows case, and not reachable with one flat response table.
        name = path.strip("/").replace("/", "_") + ".json"
        canned = os.path.join(fixture, str(sup.get("server_pid")), name)
        if not os.path.exists(canned):
            raise RuntimeError(f"HTTP 404 for {path}")
        with open(canned, encoding="utf-8") as fh:
            return json.load(fh)

    conn = _connect(sup)
    try:
        conn.sendall(
            f"GET {path} HTTP/1.1\r\n"
            f"Host: localhost\r\n"
            f"Authorization: Bearer {sup['bearer_token']}\r\n"
            f"Accept: application/json\r\n"
            f"Connection: close\r\n\r\n".encode()
        )
        buf = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
    finally:
        conn.close()

    return _parse_response(buf, path)


# --------------------------------------------------------------------------
# Finding the session
# --------------------------------------------------------------------------
def supervisor_files():
    """Every supervisor connection file this machine has lying about.

    Positron writes one per window, so a second window means a second server
    with its own token; both are candidates until their sessions say which
    workspace they belong to.
    """
    named = os.environ.get("POSITRON_SUPERVISOR_CONNECTION_FILE")
    if named:
        return [named] if os.path.exists(named) else []
    where = os.environ.get("POSITRON_RUN_SUPERVISOR_DIR") or tempfile.gettempdir()
    return sorted(glob.glob(os.path.join(where, "kallichore-*.json")))


def _under(child, parent):
    """Is `child` inside `parent`, or the same place?

    Walks up from the child asking the filesystem, rather than comparing
    strings. Two paths that name one directory need not spell it the same
    way: macOS and Windows are case-insensitive, so a workspace typed as
    ~/desktop/proj and a session reporting ~/Desktop/Proj are the same place
    and a string compare says they are not - which reads to the caller as
    "no console is open" for a console that is open. os.path.samefile
    compares device and inode, which is the filesystem's own answer.

    String comparison stays as the fallback for a path that does not exist
    yet, where there is nothing to stat.
    """
    if not parent:
        return False
    child, parent = os.path.realpath(child), os.path.realpath(parent)
    try:
        seen = set()
        here = child
        while here not in seen:
            if os.path.samefile(here, parent):
                return True
            seen.add(here)
            here = os.path.dirname(here)
        return False
    except OSError:  # one of them is not on disk; fall back to the spelling
        try:
            parent = os.path.normcase(parent)
            return os.path.commonpath([os.path.normcase(child), parent]) == parent
        except ValueError:  # different drives on Windows
            return False


def find_sessions(language=None, workspace=None):
    """Sessions across every running supervisor, narrowed to SESSION_FIELDS.

    Returns a list of (supervisor, session) pairs. `workspace` keeps only
    sessions whose working directory contains it, which is what tells two
    Positron windows apart.
    """
    found = []
    for path in supervisor_files():
        try:
            with open(path, encoding="utf-8") as fh:
                sup = json.load(fh)
        except (OSError, ValueError):
            continue
        try:
            payload = _http_get(sup, "/sessions")
        except Exception:
            # A stale file from a Positron that has since quit. Not an error:
            # the next one may well be the live server.
            continue
        for raw in payload.get("sessions", []):
            session = {k: raw.get(k) for k in SESSION_FIELDS}
            if language and (session.get("language") or "").lower() != language.lower():
                continue
            if workspace and not _under(workspace, session.get("working_directory")):
                continue
            found.append((sup, session))
    # Longest working directory first: with nested workspaces open, the
    # innermost is the one the caller meant.
    found.sort(key=lambda pair: len(pair[1].get("working_directory") or ""), reverse=True)
    return found


def busy_reason(session):
    """Why this session cannot take work right now, or None."""
    status = session.get("status")
    queued = (session.get("execution_queue") or {}).get("length") or 0
    if status != "idle":
        return f"console is {status}"
    if queued:
        return f"{queued} statement(s) already queued"
    return None


# --------------------------------------------------------------------------
# Running the code
# --------------------------------------------------------------------------
def connection_file(sup, session_id):
    """Ask for the session's real channel ports; write them where jupyter_client looks.

    This is the step that makes R reachable. The file holds the HMAC key, so it
    is written private and removed by the caller.
    """
    info = _http_get(sup, f"/sessions/{session_id}/connection_info")
    fd, path = tempfile.mkstemp(prefix="positron_run-", suffix=".json")
    os.close(fd)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(info, fh)
    except BaseException:
        # Including KeyboardInterrupt: this file holds the session's HMAC key,
        # and the caller's cleanup only starts once this function has returned
        # a path. Anything that stops us before then has to remove it here.
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path


def _r_string(s):
    """One R double-quoted literal. Backslash first, or it eats the others."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def code_for(language, file=None, code=None, args=()):
    """The one statement to send.

    `args` is what makes a live run able to do what a batch run can. Neither
    language gives it for free: source() has no argument mechanism at all, and
    a live console's commandArgs(trailingOnly = TRUE) is empty - measured, not
    assumed - so a script's own --outdir and --results flags were reachable
    from `Rscript` and unreachable from here. That asymmetry is not academic:
    two scripts in analysis/ default to the same figures directory, and
    without a way to pass --outdir, running one live overwrites the other's
    output with no way to avoid it.
    """
    if code is not None:
        return code
    path = os.path.abspath(file).replace("\\", "/")

    if language.lower() != "r":
        # IPython's %run already passes anything after the path through to the
        # script as sys.argv, so there is nothing to emulate.
        run = " ".join(f'"{a}"' for a in args)
        return f'%run "{path}"' + (f" {run}" if run else "")

    # echo=TRUE so the console shows the run the way pressing Source does.
    src = f'source("{path}", echo = TRUE, max.deparse.length = Inf)'
    if not args:
        return src

    # R has no equivalent, so shadow commandArgs for exactly the duration of
    # the source() call. Defining it in the global environment is what makes
    # the script see it: R resolves the name up the environment chain and
    # reaches globalenv before base. on.exit puts the original back even if
    # the script stops with an error, so a failed run does not leave the
    # console with a rigged commandArgs for everything typed afterwards.
    listed = ", ".join(_r_string(a) for a in args)
    return (
        "local({\n"
        f"  .positron_run_args <- c({listed})\n"
        "  .had <- exists('commandArgs', envir = globalenv(), inherits = FALSE)\n"
        "  .old <- if (.had) get('commandArgs', envir = globalenv()) else NULL\n"
        "  assign('commandArgs', function(trailingOnly = FALSE)\n"
        "    if (trailingOnly) .positron_run_args\n"
        "    else c(base::commandArgs(FALSE), '--args', .positron_run_args),\n"
        "    envir = globalenv())\n"
        "  on.exit(if (.had) assign('commandArgs', .old, envir = globalenv())\n"
        "          else rm('commandArgs', envir = globalenv()), add = TRUE)\n"
        f"  {src}\n"
        "})"
    )


def error_text(content):
    """Render a Jupyter error payload as something worth printing.

    `traceback` is the field to prefer and the one that is often not there:
    measured against ark, `stop("deliberate failure")` sends an iopub error
    whose traceback is an empty list, so joining it printed a blank line and
    the reason for the failure was visible only inside the IDE. ename/evalue
    carry it in that case.
    """
    lines = [t for t in (content.get("traceback") or []) if t]
    if lines:
        return "\n".join(lines)
    named = ": ".join(x for x in (content.get("ename"), content.get("evalue")) if x)
    return named or "the console reported the run as failed"


def execute(conn_path, code, timeout):
    """Send one execute_request and relay the console's output back.

    No wait_for_ready() here: that is for a kernel you started yourself, and
    against a live console its handshake is noise. If the session answers
    kernel_info it is up.
    """
    from jupyter_client import BlockingKernelClient

    kc = BlockingKernelClient()
    kc.load_connection_file(conn_path)
    kc.start_channels()
    try:
        kc.kernel_info()
        try:
            kc.get_shell_msg(timeout=15)
        except Exception:
            print("positron_run: session did not answer kernel_info", file=sys.stderr)
            return 1

        msg_id = kc.execute(code)
        status = "ok"
        while True:
            try:
                msg = kc.get_iopub_msg(timeout=timeout)
            except Exception:
                print(f"positron_run: no output for {timeout}s, giving up waiting",
                      file=sys.stderr)
                return 1
            if msg["parent_header"].get("msg_id") != msg_id:
                continue  # the frontend's traffic, or another client's
            kind, content = msg["msg_type"], msg["content"]
            if kind == "stream":
                stream = sys.stderr if content.get("name") == "stderr" else sys.stdout
                stream.write(content.get("text", ""))
                stream.flush()
            elif kind == "error":
                status = "error"
                print(error_text(content), file=sys.stderr)
            elif kind == "execute_result":
                text = (content.get("data") or {}).get("text/plain")
                if text:
                    print(text)
            elif kind == "status" and content.get("execution_state") == "idle":
                break

        # iopub says what was printed; the shell channel's execute_reply says
        # whether it worked. Those are not the same question. A kernel that
        # reports a failure as text on stderr - which R does for some
        # conditions - produces no iopub `error` message at all, and trusting
        # iopub alone would exit 0 on a run that failed. "Did it actually
        # work" is the reason this tool exists, so ask the authoritative
        # channel and let it override.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                reply = kc.get_shell_msg(timeout=max(0.1, deadline - time.monotonic()))
            except Exception:
                break
            if reply["parent_header"].get("msg_id") != msg_id:
                continue
            if reply["content"].get("status") != "ok":
                if status != "error":
                    # iopub said nothing was wrong and the kernel says it was.
                    print(error_text(reply["content"]), file=sys.stderr)
                status = "error"
            break
        return 0 if status == "ok" else 1
    finally:
        kc.stop_channels()


# --------------------------------------------------------------------------
def report(pairs):
    if not pairs:
        print("no Positron sessions found")
        return
    for sup, session in pairs:
        blocked = busy_reason(session)
        print(f"{session['session_id']}  {session.get('display_name')}")
        print(f"    language   {session.get('language')}")
        print(f"    status     {session.get('status')}"
              + (f"  ({blocked})" if blocked else "  (free)"))
        print(f"    directory  {session.get('working_directory')}")
        print(f"    supervisor {endpoint_label(sup)}")


def open_console_guidance(language, workspace):
    """The one thing a person has to do that this tool will not do for them.

    Starting a console unasked puts a runtime in someone's IDE that they did
    not ask for, in a workspace they may not have meant; so this stops instead.
    Stopping is only acceptable if what to do next is unambiguous, which is
    why this is spelt out rather than left as "no session found".
    """
    name = LANGUAGES.get(language, language)
    return (
        f"positron_run: no {name} console is open"
        + (f" for {workspace}" if workspace else "") + ".\n"
        "\n"
        f"Nothing can run until one exists. To open it:\n"
        f"  1. Bring up the Positron window for {workspace or 'this project'}.\n"
        f"     Its working directory has to contain that path - a console in\n"
        f"     another project will not be used, on purpose.\n"
        f"  2. In the Console pane, open the session picker (the dropdown in\n"
        f"     its top-right) and choose {name}.\n"
        f"  3. Wait for the prompt, then run this command again.\n"
        "\n"
        "  positron_run.py --check                 what this can see right now\n"
        "  positron_run.py ... --wait 120          block here until you open one\n"
        "\n"
        "This attaches to a console you already have and will not start one\n"
        "for you: a runtime appearing unasked in your IDE, holding a workspace\n"
        "you did not pick, is a worse surprise than this message."
    )


def await_session(language, workspace, seconds, poll=2.0):
    """Block until a usable console appears, or the clock runs out.

    The alternative to a hard stop, for a caller that would rather hold the
    step open than be sent away and have to start over: the instructions stay
    on screen while someone acts on them, and the run continues by itself the
    moment the console is there.
    """
    deadline = time.monotonic() + seconds
    while True:
        pairs = find_sessions(language=LANGUAGES[language], workspace=workspace)
        free = [p for p in pairs if not busy_reason(p[1])]
        if free:
            print(f"positron_run: {free[0][1]['session_id']} is up - continuing.",
                  file=sys.stderr)
            return free
        left = deadline - time.monotonic()
        if left <= 0:
            return []
        print(f"positron_run: still waiting for a free {LANGUAGES[language]} console "
              f"({int(left)}s left) ...", file=sys.stderr)
        time.sleep(min(poll, left))


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="positron_run.py",
        description="Run a file or a snippet in a console Positron already has open.",
    )
    p.add_argument("--lang", choices=sorted(LANGUAGES), help="which console to use")
    p.add_argument("--file", help="script to source/run there")
    p.add_argument("--code", help="a snippet to run instead of a file")
    p.add_argument("--session-id", help="target one session explicitly")
    p.add_argument("--workspace", help="workspace root (default: the file's directory)")
    p.add_argument("--timeout", type=float, default=600,
                   help="seconds to wait for output before giving up (default 600)")
    p.add_argument("--check", action="store_true",
                   help="list the sessions this can see, and run nothing")
    p.add_argument("--dry-run", action="store_true",
                   help="say what would run, and where, without running it")
    p.add_argument("--wait", type=float, default=0, metavar="SECONDS",
                   help="instead of failing when no console is open, hold here "
                        "until one appears (must be last except for --args)")
    # REMAINDER so the script's own flags arrive intact: --args --outdir figs
    # would otherwise be eaten by this parser as unknown options.
    p.add_argument("--args", nargs=argparse.REMAINDER, default=[],
                   metavar="...", help="everything after this goes to the script "
                                       "(R: commandArgs; Python: sys.argv)")
    args = p.parse_args(argv)

    if args.check:
        report(find_sessions(language=LANGUAGES.get(args.lang) if args.lang else None))
        return 0

    if not args.lang:
        p.error("--lang is required unless --check")
    if bool(args.file) == bool(args.code):
        p.error("give exactly one of --file or --code")
    if args.args and not args.file:
        p.error("--args needs --file; a snippet given with --code is its own argument")
    if args.file and not os.path.exists(args.file):
        print(f"positron_run: no such file: {args.file}", file=sys.stderr)
        return 2

    if args.session_id:
        pairs = [pair for pair in find_sessions(language=LANGUAGES[args.lang])
                 if pair[1]["session_id"] == args.session_id]
        if not pairs:
            print(f"positron_run: no {LANGUAGES[args.lang]} session "
                  f"{args.session_id}", file=sys.stderr)
            return 2
    else:
        workspace = args.workspace or (os.path.dirname(os.path.abspath(args.file))
                                       if args.file else os.getcwd())
        pairs = find_sessions(language=LANGUAGES[args.lang], workspace=workspace)
        if not pairs:
            # Falling back to any window would run the code somewhere the
            # caller did not mean; say what was found instead.
            others = find_sessions(language=LANGUAGES[args.lang])
            if others:
                print(f"positron_run: found a {LANGUAGES[args.lang]} console, but not "
                      f"one holding {workspace}:", file=sys.stderr)
                for _, session in others:
                    print(f"    {session['session_id']} in "
                          f"{session.get('working_directory')}", file=sys.stderr)
                print("\nUse --workspace or --session-id to pick one.", file=sys.stderr)
                return 2
            print(open_console_guidance(args.lang, workspace), file=sys.stderr)
            if not args.wait:
                return 2
            print(f"\npositron_run: waiting up to {int(args.wait)}s for you to open "
                  f"it. Ctrl-C to stop.", file=sys.stderr)
            try:
                pairs = await_session(args.lang, workspace, args.wait)
            except KeyboardInterrupt:
                print("\npositron_run: gave up waiting.", file=sys.stderr)
                return 2
            if not pairs:
                print(f"positron_run: no {LANGUAGES[args.lang]} console appeared "
                      f"within {int(args.wait)}s. Nothing was run.", file=sys.stderr)
                return 2

    sup, session = pairs[0]
    blocked = busy_reason(session)
    if blocked:
        # Queuing behind whatever is running would execute this at a time
        # nobody chose, against state nobody predicted.
        print(f"positron_run: {session['session_id']} is not free - {blocked}.\n"
              "Wait for it to finish, or interrupt it in Positron.", file=sys.stderr)
        return 3

    code = code_for(args.lang, file=args.file, code=args.code, args=args.args)
    if args.dry_run or os.environ.get("POSITRON_RUN_DRY_RUN"):
        print(f"would run in {session['session_id']} "
              f"({session.get('display_name')}) via {endpoint_label(sup)}")
        print(f"  cwd  {session.get('working_directory')}")
        print(f"  code {code}")
        return 0

    try:
        conn_path = connection_file(sup, session["session_id"])
    except Exception as exc:
        # A traceback here would be both unhelpful and a hazard: the frames it
        # prints are the ones holding the bearer token and the HMAC key. Say
        # what failed by type, and nothing about what was in the response.
        print(f"positron_run: could not get connection info for "
              f"{session['session_id']} ({type(exc).__name__}). The console may "
              f"have closed since it was listed; try --check.", file=sys.stderr)
        return 2

    try:
        return execute(conn_path, code, args.timeout)
    finally:
        try:
            os.unlink(conn_path)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
