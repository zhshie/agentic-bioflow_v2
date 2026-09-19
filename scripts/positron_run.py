#!/bin/bash
# Not the Positron CLI: it has --goto and extension management, no way to run
# code in an already-open console (see "Why this file exists" below).
#
# Entered as a shell script so it can choose its own interpreter, because on
# both machines this tool has to run on, the name in a shebang lies.
#
#   Windows (where Positron is): `python3` is on PATH as an App Execution
#   Alias pointing at a Microsoft Store stub. `command -v` finds it; running it
#   exits 49 having printed nothing (PITFALLS 20c). A `#!/usr/bin/env python3`
#   line resolves to that stub, so the documented invocation dies silently.
#
#   This cluster: /usr/bin/python3 is RHEL's own reserved interpreter, mode 750
#   root:root - present, on PATH, and unrunnable (PITFALLS 16d).
#
# One rule covers both: pick an interpreter by RUNNING one, never by finding
# one. A stub that exits 49 and a binary that cannot be executed both fail the
# probe, and the next candidate gets its turn. Running it as
# `python positron_run.py` still works; the shell block is then just a string.
''''true
for candidate in python3 python py; do
    if "$candidate" -c 'import sys' >/dev/null 2>&1; then
        exec "$candidate" "$0" "$@"
    fi
done
echo "positron_run: no working Python interpreter found (tried python3, python, py)." >&2
echo "  On Windows, 'python3' may be the Microsoft Store alias - install Python or" >&2
echo "  use the interpreter Positron itself runs on." >&2
exit 2
'''

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

THREE-TIER LADDER (GitHub issue #14) - everything above this paragraph
describes the *second* rung, not the first any more. kallichore 0.1.68, the
version bundled with current Positron on Windows, stopped writing
`kallichore-*.json` connection files at all: it hands connection info to
Positron's own main process over a one-shot handshake named pipe
(`\\\\.\\pipe\\kallichore-handshake-<id>`) that is consumed the moment Positron
reads it, and this process - or any process outside Positron itself - can
never see it (docs/PITFALLS.md's kallichore entry has the measured evidence:
the log line, and the connection file that never appears). Against that
version, everything below the ladder's first rung finds nothing, forever,
console alive or not - which is exactly the bug this rewrite fixes.

    1. bridge file    extensions/positron-bridge's own state file, read by
                       read_bridge() - if it is there and answers, run
                       through it (bridge_run()). Works against *any*
                       kallichore version, because it never touches
                       kallichore at all: positron.runtime.executeCode is
                       Positron's own API, called from inside an extension
                       this repo now ships (extensions/positron-bridge/).
    2. kallichore file  no bridge (or a stale one) -> fall back to the
                       supervisor_files()/survey() path this file always
                       had, for a Positron old enough to still write one.
    3. neither         distinguish *why*, because the advice differs: no
                       Positron running here at all: no Positron installed
                       here at all; or Positron is running a kallichore new
                       enough to need the bridge and the bridge is not
                       installed. See positron_presence() and
                       tier3_message(). Every one of the three still offers
                       the batch path (`Rscript`/`python`, figures written to
                       disk) as a real next step, not a dead end - RStudio,
                       VS Code and Jupyter have no rung above tier 3 at all
                       and always land here, which is why this is where that
                       offer lives once, rather than being copied into three
                       separate refusals.

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
import shutil
import socket
import stat
import subprocess
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


def _split_response(buf):
    """Split an HTTP/1.1 response into (status line, decoded body bytes).

    Its own function so both _parse_response (kallichore's GETs, which raise
    on anything but 200) and _bridge_post (the bridge's POST /run, which
    reports its own status/error in a 200 *and* a 400/401/403 body and must
    not have either one turned into an exception here) can share the framing
    logic without agreeing on what a non-200 status means.

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
        raise RuntimeError("connection closed without replying")
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
    return status, body


def _parse_response(buf, path):
    """Split an HTTP/1.1 response and return its JSON body, kallichore's way:
    anything but 200 raises. Its own function so a test can reach it - see
    _split_response for why the framing itself moved out of here.
    """
    status, body = _split_response(buf)
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
# The bridge extension - ladder rung 1
#
# extensions/positron-bridge writes one state file per Positron window, the
# same "one per window" shape supervisor_files() already has for kallichore,
# but with one important difference: there is nothing to glob. The bridge
# only ever runs inside the one window that installed it and only ever
# writes the one file for that window's own state directory, so there is at
# most one to read - no multi-window disambiguation, no workspace matching,
# because the extension only ever speaks for the window it is already in.
# --------------------------------------------------------------------------
def bridge_file_path():
    """Where extensions/positron-bridge writes its state file.

    Kept in lockstep by hand with stateFilePath() in
    extensions/positron-bridge/src/bridge-core.js - docs/PITFALLS.md names
    this pair as the one thing to change together if it ever has to move.

    POSITRON_RUN_BRIDGE_FILE overrides it for tests, the same seam
    POSITRON_SUPERVISOR_CONNECTION_FILE already is for the kallichore side.
    """
    named = os.environ.get("POSITRON_RUN_BRIDGE_FILE")
    if named:
        return named
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.environ.get("USERPROFILE", ""), "AppData", "Local")
    else:
        base = os.environ.get("XDG_STATE_HOME") or os.path.join(
            os.environ.get("HOME", ""), ".local", "state")
    return os.path.join(base, "agentic-bioflow", "positron-bridge.json")


def read_bridge():
    """The bridge file's contents, or None when absent/unreadable/incomplete.

    Presence is not liveness, the same way a kallichore connection file left
    behind by a Positron that has since quit is not either - bridge_probe()
    is what tells the two apart, by actually trying to connect.
    """
    path = bridge_file_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or "port" not in data or "token" not in data:
        return None
    return data


def _bridge_post(bridge, payload_obj, timeout):
    """POST /run to the bridge extension. Returns (status_code, parsed_json).

    Never raises on the *server* saying 400/401/403 - unlike _parse_response,
    a non-200 here is still a real, meaningful reply (extension.ts's own
    handleRequest() puts an {ok:false, error:...} body on every one of its
    rejections) and the caller decides what it means. What this does raise
    on is the connection itself failing - ConnectionRefusedError, a timeout -
    which is what a stale bridge file (extension deactivated, Positron quit,
    file never got cleaned up) looks like from here.
    """
    fixture = os.environ.get("POSITRON_RUN_BRIDGE_FIXTURE")
    if fixture:
        # Mirrors _http_get's own fixture seam: a real loopback HTTP round
        # trip through positron-bridge's own server is not something a test
        # of this file should have to stand up either. "refuse" is the one
        # canned shape that means "the connection itself failed", matching
        # what a stale file produces against a real socket.
        with open(fixture, encoding="utf-8") as fh:
            canned = json.load(fh)
        if canned.get("refuse"):
            raise ConnectionRefusedError("fixture: bridge did not answer")
        return canned.get("status", 200), canned.get("body")

    body = json.dumps(payload_obj).encode("utf-8")
    conn = socket.create_connection(("127.0.0.1", int(bridge["port"])), timeout=timeout)
    conn.settimeout(timeout)
    try:
        conn.sendall(
            f"POST /run HTTP/1.1\r\n"
            f"Host: 127.0.0.1\r\n"
            f"Authorization: Bearer {bridge['token']}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n".encode() + body
        )
        buf = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
    finally:
        conn.close()
    status_line, body = _split_response(buf)
    try:
        code = int(status_line.split()[1])
    except (IndexError, ValueError):
        code = 0
    try:
        parsed = json.loads(body.decode("utf-8")) if body else None
    except ValueError:
        parsed = None
    return code, parsed


def bridge_probe(bridge, timeout=5):
    """Does the bridge answer at all? True/False, never raises.

    Sent as a request the extension's own input validation rejects - an
    empty `lang` - so this proves the loopback connection, the token, and
    the request handler all work, without running a single line of anyone's
    code to find out: extension.ts's runOne() checks lang against its
    {"r", "python"} whitelist as the very last step, well after loopback and
    token, so an empty lang clears every earlier gate and is refused before
    positron.runtime.executeCode is ever called.
    """
    try:
        _bridge_post(bridge, {"lang": "", "code": "positron_run --check probe"}, timeout)
        return True
    except Exception:
        return False


def bridge_run(bridge, language, code, timeout):
    """Run `code` through the bridge. Returns the process exit code this
    tool should use - 0 ok, 1 the console reported failure or the bridge
    answered strangely. Never raises; a connection failure is the caller's
    to catch (see bridge_probe's docstring) and treat as a stale file.
    """
    status, parsed = _bridge_post(bridge, {"lang": language, "code": code}, timeout)
    if status != 200 or not isinstance(parsed, dict):
        print(f"positron_run: bridge answered unexpectedly (HTTP {status}). "
              "Try --check.", file=sys.stderr)
        return 1
    images = parsed.get("new_images") or []
    for image in images:
        print(f"positron_run: new image  {image}")
    if parsed.get("ok"):
        # Always one line on success. With no new image file this used to
        # print nothing at all, and an exit 0 with empty output read as
        # "did anything happen?" (2.15.0 Windows verification: the plot was
        # in Positron's Plots pane the whole time).
        print(f"positron_run: ok - ran in the Positron {LANGUAGES.get(language, language)} "
              f"console via the bridge; {len(images)} new image file(s)"
              + ("" if images else " (a plot shown only in the Plots pane is not a file)"))
        return 0
    print(parsed.get("error") or "the console reported the run as failed", file=sys.stderr)
    return 1


# --------------------------------------------------------------------------
# Telling "not open" from "not installed" - ladder rung 3's own distinction
#
# Both of these are inferred, not measured, in docs/CONDITIONS.md's own
# sense of the word (see that file's "Evidence levels"): a positive is
# fairly reliable, a negative only means none of the common spots had it.
# Getting this wrong costs nothing but which of two very similar sentences
# is printed - tier3_message() offers the same batch path regardless.
# --------------------------------------------------------------------------
def _process_running(name):
    """Best-effort: is a process named exactly `name` running right now?

    Exact name, not a substring of the full command line: this script's own
    argv is `.../positron_run.py ...`, which *contains* "positron" - a
    substring match (`pgrep -f`) against that pattern matches this process
    itself the instant it runs, which is a self-inflicted false positive,
    not evidence of anything. `pgrep -x` compares against the process name
    (argv[0]'s basename) instead, and this script's own name is
    python3/python/py, never positron.

    Never raises: no tasklist, no pgrep, a permissions error - every one of
    those is read as "cannot tell", which the caller treats the same as "not
    found" rather than blocking on an inconclusive probe.
    """
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {name}.exe", "/NH"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            return f"{name}.exe".lower() in out.stdout.lower()
        out = subprocess.run(
            ["pgrep", "-x", name], capture_output=True, text=True, timeout=5, check=False)
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _positron_installed():
    """Best-effort: does this machine have Positron anywhere obvious?"""
    if shutil.which("positron"):
        return True
    candidates = []
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        candidates.append(os.path.join(local, "Programs", "Positron", "Positron.exe"))
    elif sys.platform == "darwin":
        candidates.append("/Applications/Positron.app")
    else:
        candidates += ["/usr/share/positron", "/opt/positron", "/opt/Positron"]
    return any(os.path.exists(c) for c in candidates)


def positron_presence():
    """One of "running" / "installed" / "absent" - see this section's own
    header for how sure each is. Used only to choose which of tier3_message's
    three refusals to print when neither the bridge nor a kallichore file
    found anything at all.

    POSITRON_RUN_PRESENCE overrides it for tests: real process/install
    detection is exactly the kind of host-state probe tests/run_all.sh's own
    header says this suite must not depend on (it would otherwise pass or
    fail by whether the machine running the suite happens to have Positron
    installed, which has nothing to do with whether this file's logic is
    correct).
    """
    override = os.environ.get("POSITRON_RUN_PRESENCE")
    if override in ("running", "installed", "absent"):
        return override
    if _process_running("positron") or _process_running("Positron"):
        return "running"
    if _positron_installed():
        return "installed"
    return "absent"


BATCH_HINT = (
    "\nBatch still works here, and is a supported path, not a fallback of\n"
    "last resort: `Rscript <script>.R` / `python <script>.py`, with the\n"
    "figure written to analysis/figures/ for you to open by hand. RStudio,\n"
    "VS Code and Jupyter all take this same path - this tool cannot reach\n"
    "any of them at all, and docs/CONDITIONS.md says so plainly rather than\n"
    "leaving downstream.md step 5 a dead end for them."
)


def tier3_message(language, workspace, presence):
    """Ladder rung 3: neither the bridge nor a kallichore file found
    anything. Which of three sentences to lead with depends on `presence`
    (positron_presence()) - the advice is different for each, and only one
    of the three is actually about opening a console.
    """
    name = LANGUAGES.get(language) or "R or Python"
    where = os.environ.get("POSITRON_RUN_SUPERVISOR_DIR") or tempfile.gettempdir()
    bridge_at = bridge_file_path()
    if presence == "running":
        head = (
            "positron_run: Positron is running on this machine, but neither the bridge\n"
            f"  extension ({bridge_at}) nor the old kallichore connection-file contract\n"
            f"  (looked in {where} for kallichore-*.json) found anything to attach to.\n"
            "  This is very likely a kallichore version that only hands connection info\n"
            "  to Positron's own process over a one-shot handshake pipe - see\n"
            "  docs/PITFALLS.md's kallichore handshake-pipe entry - and the bridge\n"
            "  extension that works around it is not installed here.\n"
            "\n"
            "  Install it once, inside Positron:\n"
            "      positron --install-extension "
            "<repo>/extensions/positron-bridge/*.vsix\n"
            "  Then run this again; no need to reopen the console.\n"
        )
    elif presence == "installed":
        head = (
            "positron_run: Positron looks to be installed on this machine but not running\n"
            "  right now (no bridge file, no kallichore connection files, and no matching\n"
            "  process found - inferred, not certain).\n"
            "\n"
            f"  Start Positron, open {workspace or 'this project'}, bring up a {name} console,\n"
            "  and run this again.\n"
        )
    else:
        host = socket.gethostname()
        head = (
            f"positron_run: no Positron is running on this machine ({host}), and no install\n"
            "  was found either (checked PATH and the usual install locations - inferred,\n"
            f"  not certain). Looked in {where} for kallichore-*.json and at {bridge_at}\n"
            "  for a bridge file; found neither.\n"
            "\n"
            "  This reaches Positron over a local pipe, socket or loopback port, and\n"
            "  nothing else. If Positron is open on a different machine - your own\n"
            "  desktop, while this runs on a login node - there is no route to it from\n"
            "  here, and opening or installing one there will not change what this can see\n"
            "  (docs/DOWNSTREAM.md names that split). Either run this on the machine\n"
            "  Positron is on, or reach this machine from Positron's own Remote-SSH so\n"
            "  its console - and the bridge extension's state file - live here too.\n"
        )
    return head + BATCH_HINT


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


def survey(language=None, workspace=None):
    """What is on this machine, in enough detail to tell four states apart.

    `find_sessions` answers "which sessions" and throws the rest away, and
    that is one answer short. No supervisor file at all, a file left by a
    Positron that has quit, and a running Positron with no console open come
    back from it as the same empty list - and they need different advice.
    Positron writes one supervisor file per window, so the counts are what
    separate them: `supervisors` is how many files exist, `answered` how many
    of them replied.

    That distinction is the whole of the machine boundary. Every transport
    here is local-only, so an agent on a login node while Positron runs on
    someone's desktop sees zero files no matter how many consoles are open
    there, and "no console is open" is then a true sentence about the wrong
    machine.
    """
    files = supervisor_files()
    answered = 0
    found = []
    for path in files:
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
        answered += 1
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
    return {"supervisors": len(files), "answered": answered, "pairs": found}


def find_sessions(language=None, workspace=None):
    """Sessions across every running supervisor, narrowed to SESSION_FIELDS.

    Returns a list of (supervisor, session) pairs. `workspace` keeps only
    sessions whose working directory contains it, which is what tells two
    Positron windows apart.
    """
    return survey(language=language, workspace=workspace)["pairs"]


def jupyter_client_problem():
    """None if the ZMQ half of this can run, else what to tell the caller.

    Imported rather than looked up: a wheel built for another interpreter is
    findable and not importable, and importlib.util.find_spec would call that
    installed.

    Checked by --check, and again before the connection file is written,
    because of what used to happen without it. --check passed, a session was
    found, the file holding that session's HMAC key was written to disk, and
    only then did `from jupyter_client import ...` fail - with a raw traceback,
    out of a tool that weighs every other line it prints. commands/downstream.md
    tells a person to run --check first and stop if it reports trouble; a check
    that passes when the run cannot possibly work is not a check.
    """
    try:
        import jupyter_client  # noqa: F401
    except ImportError as exc:
        return (
            "positron_run: jupyter_client is not importable (%s).\n"
            "  It carries the Jupyter protocol this speaks to the console.\n"
            "  Install it for the interpreter that runs this file:\n"
            "      %s -m pip install jupyter_client" % (exc, sys.executable)
        )
    return None


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
def report(state, language=None, workspace=None):
    """--check: say what is here, and why nothing is when nothing is.

    Takes the whole survey rather than its pairs, because the empty case is
    the one worth being precise about - see survey().

    Only called once main() has already ruled out ladder rung 1 (no usable
    bridge) - so `state["supervisors"] == 0` here means rung 2 also found
    nothing, which is exactly what tier3_message() (rung 3) exists to
    explain. `language`/`workspace` are None for a plain `--check` with no
    `--lang`; tier3_message handles that.
    """
    pairs = state["pairs"]
    if not pairs:
        if state["supervisors"] == 0:
            print(tier3_message(language, workspace, positron_presence()))
        elif state["answered"] == 0:
            print("positron_run: %d supervisor file(s) here, none answered - "
                  "left behind by a\n  Positron that has since quit. Nothing "
                  "is running to attach to." % state["supervisors"])
        else:
            print("positron_run: Positron is running here (%d window(s)), with no "
                  "matching\n  console open in it." % state["answered"])
    for sup, session in pairs:
        blocked = busy_reason(session)
        print(f"{session['session_id']}  {session.get('display_name')}")
        print(f"    language   {session.get('language')}")
        print(f"    status     {session.get('status')}"
              + (f"  ({blocked})" if blocked else "  (free)"))
        print(f"    directory  {session.get('working_directory')}")
        print(f"    supervisor {endpoint_label(sup)}")


def report_dependency():
    """Printed by --check whether or not a session was found.

    A console that is open and a protocol library that is installed are two
    independent preconditions, and --check is where both are supposed to be
    visible before anyone acts.
    """
    problem = jupyter_client_problem()
    if problem:
        print()
        print(problem)
    return problem


def open_console_guidance(language, workspace, state=None):
    """The one thing a person has to do that this tool will not do for them.

    Starting a console unasked puts a runtime in someone's IDE that they did
    not ask for, in a workspace they may not have meant; so this stops instead.
    Stopping is only acceptable if what to do next is unambiguous, which is
    why this is spelt out rather than left as "no session found".

    Unambiguous also means naming the right cause. This used to open with "no
    R console is open" in every case, including the one where no Positron is
    running here at all - so an agent on a login node told the person to open
    a console that was already open on their desktop, and would keep telling
    them however many they opened. `state` is the survey that separates them.

    Only called once main() has already ruled out ladder rung 1 (see
    report()'s own docstring for the same point) - so `supervisors == 0`
    here hands off to tier3_message() (rung 3) rather than assuming, as this
    function used to, that "no kallichore file" only ever meant "Positron is
    not open".
    """
    name = LANGUAGES.get(language, language)
    supervisors = (state or {}).get("supervisors")
    answered = (state or {}).get("answered")
    if supervisors == 0:
        return tier3_message(language, workspace, positron_presence())
    if supervisors and not answered:
        head = ("positron_run: %d supervisor file(s) here, none answered - left by a "
                "Positron\n  that has since quit.\n" % supervisors)
        step1 = f"  1. Start Positron again and open {workspace or 'this project'}.\n"
    else:
        head = (f"positron_run: no {name} console is open"
                + (f" for {workspace}" if workspace else "") + ".\n"
                f"  Positron is running here; what is missing is the console.\n")
        step1 = (f"  1. Bring up the Positron window for {workspace or 'this project'}.\n"
                 f"     Its working directory has to contain that path - a console in\n"
                 f"     another project will not be used, on purpose.\n")
    return (
        head +
        "\n"
        f"Nothing can run until one exists. To open it:\n"
        + step1 +
        f"  2. In the Console pane, open the session picker (the dropdown in\n"
        f"     its top-right) and choose {name}.\n"
        f"  3. Wait for the prompt, then run this command again.\n"
        "\n"
        "  positron_run.py --check                 what this can see right now\n"
        "  positron_run.py ... --wait 120          block here until you open one\n"
        "\n"
        "This attaches to a console you already have and will not start one\n"
        "for you: a runtime appearing unasked in your IDE, holding a workspace\n"
        "you did not pick, is a worse surprise than this message.\n"
        # Every rung-3 message ends with the batch path, not only the one
        # tier3_message() builds: after Positron quit (stale supervisor files)
        # this used to stop at "start Positron again", a dead end for anyone
        # who did not want to (2.15.0 Windows verification).
        + BATCH_HINT
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

    # Ladder rung 1: the bridge extension. Tried before anything else,
    # because it works against any kallichore version - there is nothing to
    # "fall back from" if it answers. bridge_probe's own docstring explains
    # why probing it is safe to do even for a plain --check: it never
    # reaches positron.runtime.executeCode.
    bridge = read_bridge()
    if bridge is not None and not bridge_probe(bridge):
        print(f"positron_run: a bridge file is here ({bridge_file_path()}) but did not "
              "answer -\n  Positron may have quit since without cleaning it up. Falling "
              "back to the\n  older kallichore contract.\n", file=sys.stderr)
        bridge = None

    if args.check:
        if bridge is not None:
            print(f"bridge      127.0.0.1:{bridge.get('port')}  "
                  f"positron {bridge.get('positron_version', '?')}  pid {bridge.get('pid', '?')}")
            print("  Primary path: --lang/--file will run through this, whatever")
            print("  kallichore version Positron is carrying underneath.")
            return 0
        state = survey(language=LANGUAGES.get(args.lang) if args.lang else None)
        report(state, language=args.lang, workspace=args.workspace)
        problem = report_dependency()
        # An exit code, because downstream.md step 5 uses --check as a gate and
        # a gate that always returns 0 is prose. 2 is what the rest of this file
        # already means by "nothing here can run".
        return 0 if (state["pairs"] and not problem) else 2

    if not args.lang:
        p.error("--lang is required unless --check")
    if bool(args.file) == bool(args.code):
        p.error("give exactly one of --file or --code")
    if args.args and not args.file:
        p.error("--args needs --file; a snippet given with --code is its own argument")
    if args.file and not os.path.exists(args.file):
        print(f"positron_run: no such file: {args.file}", file=sys.stderr)
        return 2

    if bridge is not None:
        code = code_for(args.lang, file=args.file, code=args.code, args=args.args)
        if args.dry_run or os.environ.get("POSITRON_RUN_DRY_RUN"):
            print(f"would run via bridge 127.0.0.1:{bridge.get('port')} "
                  f"(positron {bridge.get('positron_version', '?')})")
            print(f"  code {code}")
            return 0
        return bridge_run(bridge, args.lang, code, args.timeout)

    # Ladder rung 2 (and, if this finds nothing either, rung 3 via
    # open_console_guidance/report above): the pre-existing kallichore
    # connection-file contract, unchanged from before the bridge existed.
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
        state = survey(language=LANGUAGES[args.lang], workspace=workspace)
        pairs = state["pairs"]
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
            print(open_console_guidance(args.lang, workspace, state), file=sys.stderr)
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

    problem = jupyter_client_problem()
    if problem:
        # Before connection_file, not after: that call writes the session's
        # HMAC key to a temporary file, and there is no reason to create it for
        # a run that cannot proceed.
        print(problem, file=sys.stderr)
        return 2

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
