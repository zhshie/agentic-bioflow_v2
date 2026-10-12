# Not a systemd service or a Docker image: they hide what the agent checks at start; this command line checks its token file, its platform URL and its deployment first and says what it found.
"""abf-station run --platform URL --token-file FILE --deployment ROOT

Before it connects to anything the agent checks, in this order, and stops with one clear line when a
check fails: the shell it runs in, the platform URL, the token file (present, not empty, readable by
its owner only, and not on a Windows drive), and the deployment (its settings file and the site script).
"""
import argparse
import os
import re
import stat
import sys
import urllib.parse
from pathlib import Path

from . import __version__, agent, site

LOOPBACK = ("127.0.0.1", "localhost", "::1")
WINDOWS_MOUNTS = ("drvfs", "9p", "fuse.drvfs")
EXIT_REFUSED = 2


def say(text):
    print(text, flush=True)


def _unescape(field):
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def windows_problem():
    if sys.platform.startswith("win") or site.host_os().upper().startswith(("MINGW", "MSYS", "CYGWIN")):
        return ("abf-station needs bash and WSL: it runs on Linux, or inside WSL on Windows. The missing capability is "
                "WSL. Install it with `wsl --install`, then start abf-station from a WSL terminal.")
    return None


def url_problem(url):
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return "the platform URL %s is not an http or https address" % url
    if parts.scheme == "http" and parts.hostname not in LOOPBACK:
        return ("the platform URL %s is plain http to a machine that is not this one, and the token would travel "
                "in clear text (憑證不能走明文). Use HTTPS; only localhost and 127.0.0.1 may use http." % url)
    return None


def mount_type(path, mounts_file):
    """(filesystem type of the mount holding path, problem text). The mount table is read from /proc/mounts unless
    ABF_STATION_MOUNTS_FILE names another one; a table that cannot be read is a failure, never a skip."""
    try:
        with open(mounts_file, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return None, "cannot read the mount table %s, so I cannot check where the token file lives" % mounts_file
    want = [p for p in os.path.realpath(path).split("/") if p]
    best, best_len = None, -1
    for line in lines:
        fields = line.split()
        if len(fields) < 3:
            continue
        mp = [p for p in _unescape(fields[1]).split("/") if p]
        if want[:len(mp)] == mp and len(mp) > best_len:
            best, best_len = fields[2], len(mp)
    return best, None


def token_problem(path):
    p = Path(path)
    if not p.exists():
        return "the token file %s was not found" % path
    if not p.is_file():
        return "the token file %s is not a file" % path
    if not p.read_text(encoding="utf-8", errors="replace").strip():
        return "the token file %s is empty" % path
    mode = stat.S_IMODE(p.stat().st_mode)
    if mode & 0o077:
        return "the token file %s can be read by other users (mode %o); run `chmod 600 %s` and start again" % (path, mode, path)
    fstype, why = mount_type(path, os.environ.get("ABF_STATION_MOUNTS_FILE") or "/proc/mounts")
    if why:
        return why
    if fstype in WINDOWS_MOUNTS:
        return ("the token file %s is on a Windows drive (%s mount), where permission bits cannot be trusted "
                "(Windows 磁碟上的權限位元不可信). Move it into WSL's own home folder and run `chmod 600` on it." % (path, fstype))
    return None


def deployment_problem(root, plugin_root):
    settings = Path(root) / "config" / "env.yaml"
    if not Path(root).is_dir():
        return "the deployment folder %s does not exist (it should hold config/env.yaml, the settings file)" % root
    if not settings.is_file():
        return "the deployment folder %s has no settings file (config/env.yaml)" % root
    if not site.on_site_script(plugin_root).is_file():
        return "the site script %s was not found; give the plugin folder with --plugin-root" % site.on_site_script(plugin_root)
    return None


def cmd_run(args):
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else Path(__file__).resolve().parents[2]
    for problem in (windows_problem(), url_problem(args.platform), token_problem(args.token_file),
                    deployment_problem(args.deployment, plugin_root)):
        if problem:
            say("abf-station will not start: %s" % problem)
            return EXIT_REFUSED
    token = Path(args.token_file).read_text(encoding="utf-8").strip()
    settings = Path(args.deployment) / "config" / "env.yaml"
    return agent.run(args.platform, token, args.name, plugin_root, settings)


def cmd_unforward(args):
    """Cancel the reverse forward and remove its records on both sides. By hand only: nothing in the agent does it by itself."""
    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else Path(__file__).resolve().parents[2]
    problem = windows_problem() or deployment_problem(args.deployment, plugin_root)
    if problem:
        say("abf-station will not do this: %s" % problem)
        return EXIT_REFUSED
    settings = Path(args.deployment) / "config" / "env.yaml"
    from .site import Site, quote
    from . import rules
    site = Site(plugin_root, settings, log=lambda *_: None)
    res = site.call(["--unforward"])
    say(res.out.decode("utf-8", errors="replace").strip() or res.err.strip())
    storage = rules.read_setting(str(settings), "storage_root")
    if storage and not rules.path_problem(storage):
        target = rules.normalize(storage) + "/_relay/forward_port"
        gone = site.call(["rm -f -- %s %s" % (quote(target), quote(rules.normalize(storage) + "/_relay/forward_instance"))])
        say("the copy on the site (%s) is removed" % target if gone.rc == 0 else "could not remove the copy on the site: %s" % gone.err.strip()[:200])
    return 0 if res.rc == 0 else 1


def build_parser():
    p = argparse.ArgumentParser(prog="abf-station", description=__doc__.split("\n\n")[0])
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="connect to the platform and answer read-only jobs until stopped")
    r.add_argument("--platform", required=True, help="the platform URL, e.g. http://127.0.0.1:8787 (HTTPS unless local)")
    r.add_argument("--token-file", required=True, help="a file holding the agent token, mode 600, inside WSL's own home")
    r.add_argument("--deployment", required=True, help="the deployment root (the folder holding config/env.yaml)")
    r.add_argument("--name", help="the agent name the token was made for (default: what the token says)")
    r.add_argument("--plugin-root", help="the plugin folder holding scripts/on_site.sh (default: the one this install came from)")
    r.set_defaults(func=cmd_run)
    u = sub.add_parser("unforward", help="cancel the reverse forward of live progress and remove its records (nothing does this by itself)")
    u.add_argument("--deployment", required=True, help="the deployment root (the folder holding config/env.yaml)")
    u.add_argument("--plugin-root", help="the plugin folder holding scripts/on_site.sh (default: the one this install came from)")
    u.set_defaults(func=cmd_unforward)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)
