# Nothing existing: glue that builds a fake site, runs the real platform and the real agent as processes and plays a fake platform; no shared fixture library speaks this protocol.
"""Harness for the station-agent tests (feature 007): a fake site, real processes, a fake platform."""
import asyncio
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from helpers import (PLATFORM_DIR, REPO_ROOT, free_port, mcp_call, pkg_env, run_cli, start_cli,
                     stop_proc, tool_json, wait_port)

# Tools the site scripts need. The fake site's PATH holds only these (as links) and the fake scheduler
# programs, so "java is missing" or "sinfo is missing" is true on any machine, a laptop with Java included.
TOOLS = ["bash", "sh", "env", "find", "ls", "stat", "cat", "head", "tail", "tr", "sed", "awk", "grep", "sleep",
         "mktemp", "rm", "mkdir", "cp", "mv", "tar", "date", "uname", "dirname", "basename", "readlink", "timeout",
         "wc", "sort", "cut", "id", "printf", "true", "false", "touch", "chmod", "python3", "kill", "sha256sum",
         "xargs", "tee", "expr", "realpath", "gzip", "jq", "hostname", "uniq", "tput", "ps", "ln", "cmp"]
FAKE_TOOLS = ["sbatch", "squeue", "sinfo", "scancel", "srun", "qsub", "bsub", "java", "nextflow"]
CANARY_TOKEN = "CANARY_" "7d3f9a1c5b2e4f60"


def write_exec(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


def snapshot(root):
    """Every entry under root (and root itself): kind, size, mtime_ns and, for files, the content hash."""
    root = Path(root)
    out = {}
    for p in [root] + sorted(root.rglob("*")):
        st = p.lstat()
        digest = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and not p.is_symlink() else None
        out[str(p.relative_to(root))] = (p.is_dir(), st.st_size if p.is_file() else 0, st.st_mtime_ns, digest)
    return out


def snapshot_file(path):
    """Content hash and modification time of one file; None when it is gone."""
    path = Path(path)
    if not path.exists():
        return None
    return (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)


class FakeSite:
    """A deployment root plus a site directory tree and fake scheduler programs that log every call."""

    def __init__(self, tmp, reach="local", ssh="ok", account=None, site_user=None, settings=(), destructive_log=False):
        self.tmp = Path(tmp)
        self.reach = reach
        self.destructive_log = destructive_log
        self.root = self.tmp / "deploy"
        self.config = self.root / "config"
        self.config.mkdir(parents=True)
        self.site = self.tmp / "site"
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.calls_log = self.tmp / "calls.log"
        self.calls_log.write_text("")
        self.work = self.site / "work"
        self.launch = self.site / "launch"
        self.storage = self.site / "storage"
        self.evil = self.site / "work-evil"
        for d in (self.work, self.launch, self.evil, self.storage / "rawdata", self.storage / "results",
                  self.storage / "analysis"):
            d.mkdir(parents=True)
        for name in ("rawdata", "results", "analysis"):
            (self.storage / name / "guard.txt").write_text("guard content of " + name + "\n")
        self.home = self.tmp / "home"
        self.cwd = self.tmp / "cwd"
        self.tmpdir = self.tmp / "tmpdir"
        for d in (self.home, self.cwd, self.tmpdir):
            d.mkdir()
        (self.home / ".ssh").mkdir()
        self.key = self.home / ".ssh" / "id_test"
        self.key.write_text("-----" "BEGIN OPENSSH PRIVATE KEY-----\nCANARYKEY_5c1e8b\n-----END OPENSSH PRIVATE KEY-----\n")
        self.key.chmod(0o600)
        st = self.key.stat()
        os.utime(self.key, (st.st_mtime - 5000, st.st_mtime - 4000))  # atime older than mtime: a read would move it
        self.key_atime = os.stat(self.key).st_atime_ns
        self.bin = self.tmp / "fakebin"
        self.bin_off = self.tmp / "fakebin-off"
        self.toolbin = self.tmp / "toolbin"
        self.bin_off.mkdir()
        self.toolbin.mkdir()
        for t in TOOLS:
            real = shutil.which(t)
            if real:
                (self.toolbin / t).symlink_to(real)
        self.softdir = self.tmp / "sitesoft"      # the site's own pipeline copies (preflight-nano4); outside the work and storage trees
        self.site_vars = {}      # home variable -> folder; handed to every command that runs on the site
        self.make_site_pipeline("NFCORE_AMPLISEQ_HOME", "2.18.0")      # what the SITE_CE of the launch tests names
        self.make_site_pipeline("NFCORE_RNASEQ_HOME", "3.14.0")
        self._fakes()
        self.ssh_bin = None
        self.control = self.tmp / "cm"
        lines = ["reach: " + reach, "storage_root: " + str(self.storage),
                 "agent_connection: CANARY_agent_connection_91ab", "tw_token_file: CANARY_tw_token_77cd"]
        if account:
            lines.append("slurm_account: " + account)
        if site_user:
            lines.append("site_user: " + site_user)
        lines += list(settings)
        if reach == "ssh":
            lines += ["site_host: tester@fake.example", "site_bridge: none", "ssh_control_path: " + str(self.control)]
            self.ssh_bin = self._fake_ssh(ssh)
        self.settings = self.config / "env.yaml"
        self.settings.write_text("\n".join(lines) + "\n")
        self.settings.chmod(0o600)
        self.guards = {n: snapshot_file(self.storage / n / "guard.txt") for n in ("rawdata", "results", "analysis")}

    # --- the fake programs --------------------------------------------------------
    def _fakes(self):
        log, st = str(self.calls_log), str(self.state)
        head = "#!/bin/bash\nprintf '%s\n' \"$(basename \"$0\") $*\" >> '" + log + "'\n"
        sbatch = head + (
            "case \"$1\" in --version|-V) echo 'slurm 23.02.7'; exit 0 ;; esac\n"
            "umask >> '@ST@/sbatch_umask'\n"  # the umask sbatch is called under: Slurm opens the job's output file with it
            "for last; do :; done\n"
            "mkdir -p '@ST@/scripts'; n=$(ls '@ST@/scripts' | wc -l)\n"
            "[ -f \"$last\" ] && cp \"$last\" \"@ST@/scripts/$((n + 1)).sh\"\n"
            "[ -f '@ST@/sbatch_sleep' ] && sleep \"$(cat '@ST@/sbatch_sleep')\"\n"
            "if [ -f '@ST@/sbatch_fail' ]; then cat '@ST@/sbatch_fail' >&2; exit 1; fi\n"
            "[ -f '@ST@/sbatch_garbage' ] && { echo 'Submitted batch job abc'; exit 0; }\n"
            "id=$(cat '@ST@/sbatch_id' 2>/dev/null || echo 4242)\n"
            "name=$(sed -n 's/^#SBATCH -J \\(.*\\)$/\\1/p' \"$last\" | head -1)\n"
            "dir=$(sed -n 's/^#SBATCH -D \\(.*\\)$/\\1/p' \"$last\" | head -1)\n"
            "echo \"$id|$name|$(cat '@ST@/site_user' 2>/dev/null || echo tester)|$dir\" >> '@ST@/jobs.tsv'\n"
            # like Slurm: slurm-<id>.out in the -D folder, opened with 666 & ~umask of the submitter. Only when the test
            # asks (state file sbatch_out): older tests list the files of the run folder and know five of them
            "[ -f '@ST@/sbatch_out' ] && [ -d \"$dir\" ] && : > \"$dir/slurm-$id.out\"\n"
            "echo \"Submitted batch job $id\"\n"
            "[ -f '@ST@/sbatch_exit' ] && exit \"$(cat '@ST@/sbatch_exit')\"\n"
            "exit 0\n")
        write_exec(self.bin / "sbatch", sbatch.replace("@ST@", st))
        squeue = head + (
            "[ -f '@ST@/squeue_fail' ] && exit 1\n"
            # -j <id>: that job. 009e: -n <name> (with no -j): the jobs of that name, which is how a resume asks "is the predecessor alive"
            "id=''; name=''; while [ $# -gt 0 ]; do case \"$1\" in -j) id=\"$2\"; shift ;; -n) name=\"$2\"; shift ;; esac; shift; done\n"
            "[ -f '@ST@/jobs.tsv' ] && awk -F'|' -v id=\"$id\" -v name=\"$name\" "
            "'(id != \"\" && $1 == id) || (id == \"\" && name != \"\" && $2 == name) {print $2 \"|\" $3 \"|\" $4}' '@ST@/jobs.tsv'\n"
            "exit 0\n")
        write_exec(self.bin / "squeue", squeue.replace("@ST@", st))
        curl = head + (
            "mode=direct; for a in \"$@\"; do [ \"$a\" = -x ] && mode=proxy; done\n"
            "how=$(cat \"@ST@/curl_$mode\" 2>/dev/null || echo ok)\n"
            "case \"$how\" in\n"
            "  ok) printf 'HTTP/1.1 401 Unauthorized\\r\\nX-ABF-Platform: %s\\r\\n\\r\\ncode=401\\n' \"$(cat '@ST@/instance_id')\"; exit 0 ;;\n"
            "  refused) echo 'curl: (7) Failed to connect' >&2; exit 7 ;;\n"
            "  silent) exit 28 ;;\n"
            "  e403) printf 'HTTP/1.1 403 Forbidden\\r\\n\\r\\ncode=403\\n'; exit 0 ;;\n"
            "  e502) printf 'HTTP/1.1 502 Bad Gateway\\r\\n\\r\\ncode=502\\n'; exit 0 ;;\n"
            "  other) printf 'HTTP/1.1 401 Unauthorized\\r\\n\\r\\ncode=401\\n'; exit 0 ;;\n"
            "  wrongid) printf 'HTTP/1.1 401 Unauthorized\\r\\nX-ABF-Platform: someone-else\\r\\n\\r\\ncode=401\\n'; exit 0 ;;\n"
            "esac\nexit 0\n")
        write_exec(self.bin / "curl", curl.replace("@ST@", st))
        if self.destructive_log:
            for n in ("rm", "rmdir", "mv", "tar"):
                real = shutil.which(n)
                write_exec(self.bin / n, ("#!/bin/bash\n[ -n \"$ABF_FAKE_SITE_SIDE\" ] && printf '%s\\n' \"" + n + " $*\" >> '@ST@/destructive.log'\n"
                                          "exec '" + str(real) + "' \"$@\"\n").replace("@ST@", st))
        sinfo = head + (
            "env > '@ST@/sinfo_env.txt'\n"
            "[ -f '@ST@/sinfo_sleep' ] && sleep \"$(cat '@ST@/sinfo_sleep')\"\n"
            "[ -f '@ST@/sinfo_noise' ] && { head -c 30000 /dev/zero | tr '\0' 'x'; echo; }\n"
            "if [ -f '@ST@/queues' ]; then cat '@ST@/queues'; else printf 'normal*\ndev\n'; fi\n")
        write_exec(self.bin / "sinfo", sinfo.replace("@ST@", st))
        write_exec(self.bin / "scancel", (head + (
            "[ -f '@ST@/scancel_keep' ] || { [ -f '@ST@/jobs.tsv' ] && grep -v \"^$1|\" '@ST@/jobs.tsv' > '@ST@/jobs.tmp'; "
            "[ -f '@ST@/jobs.tmp' ] && mv '@ST@/jobs.tmp' '@ST@/jobs.tsv'; }\nexit 0\n")).replace("@ST@", st))
        for n in ("srun", "qsub", "bsub"):
            write_exec(self.bin / n, head + "exit 0\n")
        write_exec(self.bin / "ssh", head + "exit 1\n")  # the ssh on PATH must never be called
        real_find = shutil.which("find")
        write_exec(self.bin / "find", ("#!/bin/bash\n[ -f '@ST@/find_sleep' ] && sleep \"$(cat '@ST@/find_sleep')\"\n"
                                       "exec '" + str(real_find) + "' \"$@\"\n").replace("@ST@", st))
        java = head + (
            "if [ -f '@ST@/java_dump_env' ]; then env >&2; echo 'java failed' >&2; exit 1; fi\n"
            "if [ -f '@ST@/java_text' ]; then cat '@ST@/java_text' >&2; else "
            "echo 'openjdk version \"17.0.9\" 2023-10-17' >&2; fi\n")
        write_exec(self.bin / "java", java.replace("@ST@", st))
        # `module load X`: every module is known unless state/modules.allow exists, and then only the modules listed there are (one per line)
        module = head + (
            "[ \"$1\" = load ] || exit 0\n"
            "[ -f '@ST@/modules.allow' ] || exit 0\n"
            "shift\n"
            "for m in \"$@\"; do grep -qxF -- \"$m\" '@ST@/modules.allow' || { echo \"Lmod has detected the following error: unknown module\" >&2; exit 1; }; done\n"
            "exit 0\n")
        write_exec(self.bin / "module", module.replace("@ST@", st))
        nf = head + (
            "if [ \"$1\" = run ]; then exit 0; fi\n"
            "if [ -f '@ST@/nextflow_text' ]; then cat '@ST@/nextflow_text'; else "
            "printf '      N E X T F L O W\n      version 24.10.5 build 5935\n'; fi\n")
        write_exec(self.bin / "nextflow", nf.replace("@ST@", st))

    def _fake_ssh(self, mode):
        """A stand-in for ssh. -O check answers by mode; any other call runs the last argument locally.

        state/ssh_drop_after holds a number: after that many working calls the connection is "gone".
        """
        st = str(self.state)
        text = (
            "#!/bin/bash\n"
            "last=\"${@: -1}\"\n"
            "printf '%s\\n' \"$*\" >> '@ST@/ssh.log'\n"
            "op=''; spec=''; prev=''; for a in \"$@\"; do [ \"$prev\" = -O ] && op=\"$a\"; [ \"$prev\" = -R ] && spec=\"$a\"; prev=\"$a\"; done\n"
            "case \"$op\" in\n"
            "  check)\n"
            "    [ -f '@ST@/ssh_down' ] && exit 255\n"
            "    [ \"$(cat '@ST@/ssh_mode')\" = nomaster ] && exit 255\n"
            "    echo \"Master running (pid=$(cat '@ST@/master_pid' 2>/dev/null || echo 4242))\" >&2; exit 0 ;;\n"
            "  forward)\n"
            "    [ -f '@ST@/fwd_fail' ] && { echo 'mux_client_forward: forwarding request failed' >&2; exit 255; }\n"
            "    p=$(echo \"$spec\" | awk -F: '{print $2}')\n"
            "    if [ \"$p\" = 0 ]; then n=$(cat '@ST@/fwd_next' 2>/dev/null || echo 41234); echo $((n + 1)) > '@ST@/fwd_next'; else n=\"$p\"; fi\n"
            "    echo \"$spec $n\" >> '@ST@/fwd_specs'; echo \"$n\" >> '@ST@/listening'; echo \"$n\"; exit 0 ;;\n"
            # like OpenSSH 8.9p1 (PITFALLS 2026-10-13): a cancel only matches the spec the forward was opened with; a
            # refusal is two lines on stderr and the exit code is still 0
            "  cancel)\n"
            "    [ -f '@ST@/cancel_error' ] && { echo 'Control socket connect: No such file or directory' >&2; exit 255; }\n"
            "    refuse() { echo 'mux_client_forward: forwarding request failed: port not forwarded' >&2; "
            "echo 'muxclient: master cancel forward request failed' >&2; exit 0; }\n"
            "    [ -f '@ST@/cancel_refuse_text' ] && { cat '@ST@/cancel_refuse_text' >&2; exit 0; }\n"
            "    [ -f '@ST@/cancel_refuse_once' ] && { rm -f '@ST@/cancel_refuse_once'; refuse; }\n"
            "    n=$(awk -v s=\"$spec\" '$1 == s {print $2; exit}' '@ST@/fwd_specs' 2>/dev/null)\n"
            "    [ -n \"$n\" ] || refuse\n"
            "    [ -f '@ST@/cancel_warning' ] && cat '@ST@/cancel_warning' >&2\n"
            "    grep -vx \"$n\" '@ST@/listening' > '@ST@/listening.tmp'; mv '@ST@/listening.tmp' '@ST@/listening'\n"
            "    awk -v s=\"$spec\" '$1 == s && !d {d = 1; next} {print}' '@ST@/fwd_specs' > '@ST@/fwd_specs.tmp'; mv '@ST@/fwd_specs.tmp' '@ST@/fwd_specs'\n"
            "    exit 0 ;;\n"
            "  exit) exit 0 ;;\n"
            "esac\n"
            "[ -f '@ST@/ssh_down' ] && { echo 'Connection closed by remote host' >&2; exit 255; }\n"
            "if [ \"$(cat '@ST@/ssh_mode')\" = hang ]; then sleep 60; exit 0; fi\n"
            "if [ -f '@ST@/ssh_drop_after' ]; then n=$(cat '@ST@/ssh_drop_after'); "
            "if [ \"$n\" -le 0 ]; then touch '@ST@/ssh_down'; echo 'Connection closed by remote host' >&2; exit 255; fi; "
            "echo $((n - 1)) > '@ST@/ssh_drop_after'; fi\n"
            "[ \"$last\" = true ] && exit 0\n"
            "export ABF_FAKE_SITE_SIDE=1\n"
            "exec bash -c \"$last\"\n").replace("@ST@", st)
        (self.state / "ssh_mode").write_text({"ok": "ok", "nomaster": "nomaster", "hang": "hang"}[mode])
        path = self.tmp / "fake-ssh"
        write_exec(path, text)
        return path

    def make_site_pipeline(self, var, version, config=None, main=True):
        """The site's copy of a pipeline under the home variable `var`: main.nf and a nextflow.config with `manifest { version }`."""
        d = self.softdir / var
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        if main:
            (d / "main.nf").write_text("// fake pipeline\n")
        (d / "nextflow.config").write_text(config if config is not None else "manifest {\n    name = 'x'\n    version = '%s'\n}\n" % version)
        self.site_vars[var] = str(d)
        return d

    def allow_modules(self, *names):
        self.set("modules.allow", "".join(n + "\n" for n in names))

    # --- changing the site -----------------------------------------------------------
    def set(self, name, text):
        (self.state / name).write_text(text)

    def clear(self, name):
        try:
            (self.state / name).unlink()
        except FileNotFoundError:
            pass

    def remove(self, tool):
        shutil.move(str(self.bin / tool), str(self.bin_off / tool))

    def restore(self, tool):
        shutil.move(str(self.bin_off / tool), str(self.bin / tool))

    # --- what the programs saw -----------------------------------------------------
    def calls(self):
        return [ln for ln in self.calls_log.read_text().splitlines() if ln.strip()]

    def dangerous(self):
        bad = []
        for ln in self.calls():
            parts = ln.split()
            prog, args = parts[0], parts[1:]
            if prog in ("sbatch", "srun", "qsub", "bsub") and args and args not in (["--version"], ["-V"]):
                bad.append(ln)
            elif prog in ("srun", "qsub", "bsub") and not args:
                bad.append(ln)
            elif prog == "nextflow" and args[:1] == ["run"]:
                bad.append(ln)
            elif prog == "scancel":
                bad.append(ln)
        return bad

    def scripts(self):
        """The head scripts sbatch was given, in order, as text."""
        d = self.state / "scripts"
        return [p.read_text() for p in sorted(d.glob("*.sh"), key=lambda p: int(p.stem))] if d.exists() else []

    def sbatch_umasks(self):
        """The umask of each sbatch call (the fake writes it before anything else), as octal text."""
        f = self.state / "sbatch_umask"
        return f.read_text().split() if f.exists() else []

    def destructive(self):
        f = self.state / "destructive.log"
        return f.read_text().splitlines() if f.exists() else []

    def listening(self):
        """The ports the fake sshd on the site listens on because of a reverse forward (the truth; ssh.log is not)."""
        f = self.state / "listening"
        return f.read_text().split() if f.exists() else []

    def ssh_calls(self):
        f = self.state / "ssh.log"
        return f.read_text().splitlines() if f.exists() else []

    def add_job(self, jid, name, user, folder):
        with open(self.state / "jobs.tsv", "a") as f:
            f.write("%s|%s|%s|%s\n" % (jid, name, user, folder))

    def slurm_jobs(self):
        f = self.state / "jobs.tsv"
        return f.read_text().splitlines() if f.exists() else []

    def guards_intact(self):
        return all(snapshot_file(self.storage / n / "guard.txt") == self.guards[n] for n in self.guards)

    # --- the agent's environment ------------------------------------------------------
    def agent_env(self, **extra):
        env = {"PATH": str(self.bin) + os.pathsep + str(self.toolbin), "HOME": str(self.home),
               "TMPDIR": str(self.tmpdir), "LANG": "C.UTF-8",
               "PYTHONPATH": str(PLATFORM_DIR), "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        env.update(self.site_vars)
        if self.ssh_bin:
            env["ON_SITE_SSH_BIN"] = str(self.ssh_bin)
        elif self.destructive_log:
            env["ABF_FAKE_SITE_SIDE"] = "1"
        env.update({k: str(v) for k, v in extra.items()})
        return env

    def ce_args(self, name="lab-a", agent=None, **over):
        """Command-line flags of `abf-platform ce create` for a Slurm environment on this site."""
        f = {"--name": name, "--platform": "slurm-platform", "--work-dir": str(self.work),
             "--launch-dir": str(self.launch), "--head-queue": "normal", "--compute-queue": "dev",
             "--host-name": "login.example", "--credentials": "site-login"}
        if agent:
            f["--agent"] = agent
        f.update(over)
        out = []
        for k, v in f.items():
            if v is not None:
                out += [k, str(v)]
        return out


# ---------------------------------------------------------------------------------------
# Running the real platform, the real agent, and MCP calls against them
# ---------------------------------------------------------------------------------------

class RealPlatform:
    """`abf-platform serve` as a process on a free loopback port, with its own data folder."""

    def __init__(self, tmp, env_extra=None, start=True):
        self.dir = Path(tmp) / "plat"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.data = self.dir / "data"
        self.index = self.data / "index.db"
        self.tokens = self.data / "tokens.db"
        self.state_db = self.data / "platform.db"
        self.env_extra = dict(env_extra or {})
        self.env = pkg_env(ABF_PLATFORM_DB=self.index, **self.env_extra)
        self.port = free_port()
        self.url = "http://127.0.0.1:%d" % self.port
        self.log = self.dir / "serve.log"
        self.proc = None
        if start:
            self.start()

    def start(self):
        self.proc = start_cli(["serve", "--port", str(self.port)], self.env, self.log)
        wait_port(self.port, proc=self.proc)

    def stop(self):
        if self.proc is not None:
            stop_proc(self.proc)
            self.proc = None

    def cli(self, args, **extra):
        env = dict(self.env)
        env.update({k: str(v) for k, v in extra.items()})
        return run_cli(list(args), env=env)

    def agent_token(self, name):
        r = self.cli(["agent-token", "new", name])
        assert r.returncode == 0, r.stdout + r.stderr
        return re.search(r"abf_[A-Za-z0-9_-]{20,}", r.stdout).group(0)

    def token_file(self, name, tmp, token=None):
        token = token or self.agent_token(name)
        path = Path(tmp) / ("token-" + name)
        path.write_text(token + "\n")
        path.chmod(0o600)
        return path, token

    def mcp(self, calls, **extra):
        env = dict(self.env)
        env.update({k: str(v) for k, v in extra.items()})
        return mcp_call(env, list(calls))

    def mcp_json(self, name, args=None, **extra):
        _, outs = self.mcp([(name, args or {})], **extra)
        return tool_json(outs[0])

    def db_rows(self, sql, args=()):
        import sqlite3
        if not self.state_db.exists():
            return []
        con = sqlite3.connect("file:%s?mode=ro" % self.state_db, uri=True)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()

    def create_ce(self, site, name="lab-a", agent=None, **over):
        return self.cli(["ce", "create"] + site.ce_args(name, agent, **over))

    def wait_ce(self, name, status, timeout=30):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            rows = self.db_rows("SELECT status, message FROM compute_envs WHERE name = ?", (name,))
            last = rows[0] if rows else None
            if last and last[0] == status:
                return last
            time.sleep(0.2)
        raise AssertionError("compute environment %s never became %s (last: %s)" % (name, status, last))

    def wait_agent_online(self, name, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            if self.db_rows("SELECT 1 FROM agents WHERE name = ?", (name,)):
                return
            time.sleep(0.1)
        raise AssertionError("agent %s never said hello" % name)

    def preflight(self, ce="lab-a"):
        return self.cli(["ce", "preflight", ce])

    def checks_of(self, text):
        """{check name: 'pass'|'fail'|'unchecked'} from the lines `ce preflight` prints: '<name>: <status> - <detail>'."""
        out = {}
        for ln in text.splitlines():
            m = re.match(r"^\s*([a-z_]+):\s+(pass|fail|unchecked)\b", ln)
            if m:
                out[m.group(1)] = m.group(2)
        return out


class AgentProc:
    """`python -m abf_station run ...` as a process; its output goes to a log file."""

    def __init__(self, url, token_file, site, name, tmp, extra_args=(), env_extra=None, env=None, cwd=None):
        self.name = name
        self.log_path = Path(tmp) / ("agent-%s.log" % name)
        self.cmd = [sys.executable, "-m", "abf_station", "run", "--platform", url, "--token-file", str(token_file),
                    "--deployment", str(site.root), "--name", name] + list(extra_args)
        e = env if env is not None else site.agent_env()
        e = dict(e)
        e.update({k: str(v) for k, v in (env_extra or {}).items()})
        self.log = open(self.log_path, "w")
        self.proc = subprocess.Popen(self.cmd, env=e, cwd=str(cwd or site.cwd), stdout=self.log,
                                     stderr=subprocess.STDOUT)

    def output(self):
        try:
            self.log.flush()
        except ValueError:  # already closed by stop(): the file still holds everything
            pass
        return self.log_path.read_text(errors="replace")

    def wait(self, timeout):
        return self.proc.wait(timeout=timeout)

    def alive(self):
        return self.proc.poll() is None

    def stop(self, sig=signal.SIGTERM, timeout=10):
        if self.proc.poll() is None:
            self.proc.send_signal(sig)
            try:
                self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.log.close()
        return self.proc.returncode


def start_agent(plat, site, name, tmp, **kw):
    """Issue a token for name, start the agent with it, wait until the platform has seen it."""
    tf, token = plat.token_file(name, tmp)
    agent = AgentProc(plat.url, tf, site, name, tmp, **kw)
    agent.token = token
    agent.token_file = tf
    plat.wait_agent_online(name)
    return agent


# ---------------------------------------------------------------------------------------
# A fake platform: speaks only the agent protocol, hands out whatever job the test wants
# ---------------------------------------------------------------------------------------

class FakePlatform:
    def __init__(self, always_status=None, poll_seconds=0.4):
        import uvicorn
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        self.always_status = always_status
        self.poll_seconds = poll_seconds
        self.requests = []
        self.results = {}
        self.pending = []
        self.next_id = 1
        self.hello_reply = {"heartbeat_seconds": 20, "poll_seconds": 1}
        self.lock = threading.Lock()

        async def body_of(request):
            raw = await request.body()
            try:
                return json.loads(raw) if raw else None
            except ValueError:
                return None

        async def hello(request):
            with self.lock:
                self.requests.append(("hello", await body_of(request), request.headers.get("authorization")))
            if self.always_status:
                return JSONResponse({"message": "no"}, status_code=self.always_status)
            return JSONResponse(self.hello_reply)

        async def poll(request):
            with self.lock:
                self.requests.append(("poll", await body_of(request), request.headers.get("authorization")))
            if self.always_status:
                return JSONResponse({"message": "no"}, status_code=self.always_status)
            end = time.time() + self.poll_seconds
            while time.time() < end:
                with self.lock:
                    if self.pending:
                        return JSONResponse({"job": self.pending.pop(0)})
                await asyncio.sleep(0.05)
            return JSONResponse({"job": None})

        async def result(request):
            body = await body_of(request)
            jid = request.path_params["jid"]
            with self.lock:
                self.requests.append(("result", body, request.headers.get("authorization")))
                self.results[jid] = body
            return JSONResponse({"accepted": True})

        app = Starlette(routes=[Route("/agent/hello", hello, methods=["POST"]),
                                Route("/agent/poll", poll, methods=["POST"]),
                                Route("/agent/result/{jid}", result, methods=["POST"])])
        self.port = free_port()
        self.url = "http://127.0.0.1:%d" % self.port
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        end = time.time() + 30
        while not self.server.started and time.time() < end:
            time.sleep(0.05)
        assert self.server.started

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=20)

    def count(self, kind=None):
        with self.lock:
            return len([r for r in self.requests if kind is None or r[0] == kind])

    def push(self, kind, args=None):
        """Queue a job exactly as given (kind and args are not checked); returns its id as a string."""
        with self.lock:
            jid = self.next_id
            self.next_id += 1
            self.pending.append({"id": jid, "kind": kind, "args": args if args is not None else {}})
        return str(jid)

    def push_raw(self, job):
        with self.lock:
            jid = self.next_id
            self.next_id += 1
            job = dict(job)
            job["id"] = jid
            self.pending.append(job)
        return str(jid)

    def wait_result(self, jid, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            with self.lock:
                if jid in self.results:
                    return self.results[jid]
            time.sleep(0.05)
        raise AssertionError("the agent never answered job %s" % jid)


def ce_snapshot(site, **over):
    """The environment part of a job's arguments, the way the platform sends it."""
    ce = {"name": "lab-a", "platform": "slurm-platform", "workDir": str(site.work), "launchDir": str(site.launch),
          "headQueue": "normal", "computeQueue": "dev", "readRoots": []}
    ce.update(over)
    return ce


# ---------------------------------------------------------------------------------------
# The command line and MCP tools, run inside the test process against private files
# ---------------------------------------------------------------------------------------

class Inproc:
    """`abf-platform ...` and the MCP tools in this process, on private files under tmp."""

    def __init__(self, tmp, monkeypatch):
        self.data = Path(tmp) / "data"
        self.index = self.data / "index.db"
        self.tokens = self.data / "tokens.db"
        self.state_db = self.data / "platform.db"
        for k in list(os.environ):
            if k.startswith("ABF_PLATFORM_"):
                monkeypatch.delenv(k)
        monkeypatch.setenv("ABF_PLATFORM_DB", str(self.index))
        self.monkeypatch = monkeypatch

    def run(self, *args):
        """(exit code, stdout + stderr) of one command line."""
        import contextlib
        import io
        from abf_platform import cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                rc = cli.main([str(a) for a in args])
            except SystemExit as e:
                rc = e.code if isinstance(e.code, int) else 1
        return (rc or 0), buf.getvalue()

    def create(self, name, platform="slurm-platform", work_dir="/data/work", **flags):
        argv = ["ce", "create", "--name", name, "--platform", platform]
        if work_dir is not None:
            argv.append("--work-dir=%s" % work_dir)
        for k, v in flags.items():
            flag = "--" + k.replace("_", "-")
            values = v if isinstance(v, (list, tuple)) else [v]
            for x in values:
                if x is not None:
                    argv.append("%s=%s" % (flag, x))  # the = form lets a value start with --
        return self.run(*argv)

    def create_slurm(self, name, **flags):
        flags.setdefault("launch_dir", "/data/launch")
        flags.setdefault("head_queue", "normal")
        return self.create(name, **flags)

    def show(self, name):
        rc, out = self.run("ce", "show", name)
        assert rc == 0, out
        return json.loads(out)

    def rows(self):
        import sqlite3
        if not self.state_db.exists():
            return {"compute_envs": [], "agents": [], "jobs": []}
        con = sqlite3.connect(str(self.state_db))
        try:
            return {t: con.execute("SELECT * FROM " + t).fetchall() for t in ("compute_envs", "agents", "jobs")}
        finally:
            con.close()

    def mcp(self, calls):
        return mcp_inproc(self.index, calls)

    def mcp_json(self, name, args=None):
        _, outs = self.mcp([(name, args or {})])
        return tool_json(outs[0])

    def all_bytes(self):
        from helpers import db_bytes
        return db_bytes(self.index, self.tokens, self.state_db)


def mcp_inproc(index, calls):
    """(tools, results) of MCP tool calls made against the server object in this process."""
    from mcp import Client
    from abf_platform import mcp_server

    async def go():
        async with Client(mcp_server.build_server(index)) as client:
            tools = (await client.list_tools()).tools
            outs = []
            for name, args in calls:
                outs.append(await client.call_tool(name, args))
            return tools, outs

    return asyncio.run(go())


def mcp_inproc_json(index, name, args=None):
    _, outs = mcp_inproc(index, [(name, args or {})])
    return tool_json(outs[0])
