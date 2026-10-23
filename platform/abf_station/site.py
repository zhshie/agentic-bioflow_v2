# Not Fabric or Ansible: they open their own connections and run arbitrary tasks; this only calls the site script of this repository, which keeps the one shared connection.
"""The only module that starts another program.

Every command for the site goes through scripts/on_site.sh of the plugin this agent was installed with
(never found from the current folder), with the deployment's settings file named in LAB_SETTINGS_FILE.
The command is one string made of fixed words and quoted values; on_site.sh joins its arguments with
spaces, so each value is quoted with shlex.quote before it gets there.
"""
import os
import shlex
import subprocess
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
