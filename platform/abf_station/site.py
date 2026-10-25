# Not Fabric or Ansible: they open their own connections and run arbitrary tasks; this only calls the site script of this repository, which keeps the one shared connection.
"""The only module that starts another program.

Every command for the site goes through scripts/on_site.sh of the plugin this agent was installed with
(never found from the current folder), with the deployment's settings file named in LAB_SETTINGS_FILE.
The command is one string made of fixed words and quoted values; on_site.sh joins its arguments with
spaces, so each value is quoted with shlex.quote before it gets there.

Besides that script there are three other ways, all with a fixed argument list and no shell: run_fixed (waits for the answer),
start_detached (a head process in a session of its own) and start_fed (a program whose standard input the caller feeds, used to
stream one uploaded file into the copy command of gcloud; the bytes are handed on and never kept, logged or written anywhere here).
"""
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

DEFAULT_SITE_TIMEOUT = "20"   # seconds, ON_SITE_TIMEOUT of one call unless the environment already sets it


class SiteResult:
    def __init__(self, rc, out, err, timed_out=False):
        self.rc = rc
        self.out = out          # bytes
        self.err = err          # text
        self.timed_out = timed_out

    def text(self):
        return self.out.decode("utf-8", errors="replace") + self.err


def quote(value):
    return shlex.quote(str(value))


def host_os():
    """What `uname -s` says, or '' when it cannot be asked."""
    try:
        p = subprocess.run(["uname", "-s"], capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return ""
    return p.stdout.strip()


def default_plugin_root():
    """The plugin folder of this install: the copy a wheel carries, else the repository checkout this file sits in."""
    here = Path(__file__).parent
    if (here / "plugin" / "scripts" / "on_site.sh").is_file():
        return here / "plugin"
    return Path(__file__).resolve().parents[2]


def on_site_script(plugin_root):
    return Path(plugin_root) / "scripts" / "on_site.sh"


class Site:
    """Calls the site script for one deployment."""

    def __init__(self, plugin_root, settings_file, log=print):
        self.script = on_site_script(plugin_root)
        self.settings_file = str(settings_file)
        self.log = log

    def call(self, args, input=None, timeout=None):
        """Run `on_site.sh <args>`; args is a list of strings. Returns a SiteResult, never raises for a failing command.

        input (bytes) is handed to the command on its standard input and is never logged or put on a command line;
        timeout (seconds) replaces the default clock of this one call."""
        env = dict(os.environ)
        env["LAB_SETTINGS_FILE"] = self.settings_file
        if timeout is not None:
            env["ON_SITE_TIMEOUT"] = str(int(timeout))
        env.setdefault("ON_SITE_TIMEOUT", DEFAULT_SITE_TIMEOUT)
        try:
            site_limit = int(env["ON_SITE_TIMEOUT"])
        except ValueError:
            site_limit = int(DEFAULT_SITE_TIMEOUT)
        shown = " ".join(args)
        self.log("site: " + (shown if len(shown) <= 400 else shown[:400] + "..."))
        try:
            p = subprocess.run(["bash", str(self.script)] + list(args), capture_output=True, env=env,
                               input=input, stdin=None if input is not None else subprocess.DEVNULL,
                               timeout=(site_limit + 15) if site_limit > 0 else None)
        except subprocess.TimeoutExpired:
            return SiteResult(124, b"", "the site script did not return in time", timed_out=True)
        except OSError as e:
            return SiteResult(127, b"", "cannot start the site script: %s" % e.__class__.__name__)
        if "ON_SITE_DRY_RUN" in env:
            for line in p.stdout.decode("utf-8", errors="replace").splitlines():
                self.log("site-output: " + line)
        return SiteResult(p.returncode, p.stdout, p.stderr.decode("utf-8", errors="replace"))


def run_fixed(argv, env, timeout):
    """(return code, output text) of one program started with a fixed argument list and no shell: the one other way this package
    starts a program (the Google Batch preflight uses it for gcloud). TimeoutError when it does not return in `timeout` seconds."""
    try:
        p = subprocess.run(list(argv), env=env, timeout=timeout, shell=False, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise TimeoutError("did not return in %s seconds" % timeout)
    except OSError as e:
        return 127, "could not start %s (%s)" % (argv[0], e.__class__.__name__)
    out = (p.stderr or "") + (p.stdout or "")
    return p.returncode, out


def wait_for_exit(proc, seconds):
    """The exit code of a process started with start_detached when it ends within `seconds`, else None (it is still running)."""
    wait = getattr(proc, "wait", None)
    if seconds > 0 and callable(wait):
        try:
            return wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return None
    poll = getattr(proc, "poll", None)
    return poll() if callable(poll) else None


def start_detached(argv, env, cwd, out_path):
    """The Popen of one program started with a fixed argument list, no shell, in a session of its own, with the output of both streams
    appended to `out_path` (private, 0600; a link there is never followed). Returns at once. This is the one other way (next to
    run_fixed) this package starts a program: the head process of one analysis, which is the analysis itself and not a watcher over
    it. It lives in a session of its own so that a restart of this agent does not end it."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(out_path), flags, 0o600)
    try:
        return subprocess.Popen(list(argv), env=env, cwd=str(cwd), shell=False, stdin=subprocess.DEVNULL, stdout=fd,
                                stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    finally:
        os.close(fd)


class Fed:
    """One program started by start_fed: bytes go in through write, the answer comes back through wait. Nothing written here is kept,
    printed or logged. Its error output goes to an unnamed temporary file, not a pipe, so that a chatty program can never stall
    during the time we are still feeding its standard input."""

    def __init__(self, proc, err):
        self._proc = proc
        self._err = err

    def write(self, data):
        """Hand `data` to the program. BrokenPipeError and other OSError are raised as they are."""
        self._proc.stdin.write(data)

    def close_stdin(self):
        """Tell the program the input is over. Safe to call again; a pipe that is already broken is not an error here (wait says why)."""
        try:
            self._proc.stdin.close()
        except OSError:
            pass

    close_input = close_stdin

    def wait(self, timeout):
        """(return code, the first 2000 characters of the error output) once the program has ended; TimeoutError when it has not
        ended within `timeout` seconds (it is left running; the caller kills it)."""
        try:
            rc = self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TimeoutError("did not return in %s seconds" % timeout)
        text = ""
        try:
            self._err.seek(0)
            text = self._err.read(2000).decode("utf-8", errors="replace")
        except (OSError, ValueError):
            pass
        return rc, text[:2000]

    def kill(self):
        """End the program and collect it. Safe to call again; the temporary file is closed too."""
        try:
            if self._proc.poll() is None:
                self._proc.kill()
            self._proc.wait()
        except OSError:
            pass
        self.close_stdin()
        try:
            self._err.close()
        except OSError:
            pass


def start_fed(argv, env):
    """A Fed over one program started with a fixed argument list and no shell, with a pipe on its standard input. OSError when it
    cannot be started (the caller turns that into a plain sentence)."""
    err = tempfile.TemporaryFile()
    try:
        proc = subprocess.Popen(list(argv), env=env, shell=False, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err,
                                close_fds=True)
    except BaseException:
        err.close()
        raise
    return Fed(proc, err)
