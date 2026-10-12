# Nothing existing: glue that drives the real command line through a pseudo-terminal and builds the files and rows a launch needs; the standard library's pty module is the only help available and it has no "wait for the question, then answer" step.
"""Helpers for the launch tests (feature 007b): the confirmation terminal, and a data folder with an environment in it."""
import json
import os
import re
import select
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from helpers import PLATFORM_DIR, pkg_env

QUESTION_LAUNCH = "確定送出？(y/N)"
QUESTION_CANCEL = "確定取消？(y/N)"
ACCOUNT = "ACCT-TEST-7"


class Pty:
    """A command line run on a pseudo-terminal that is its controlling terminal; the whole screen is kept as bytes.

    Output processing is off (no CR is added to a line feed), so the bytes kept are the bytes the program wrote.
    """

    def __init__(self, argv, env, cwd=None, controlling=True, stdin_tty=True):
        import fcntl
        import pty
        import termios
        self.master, slave = pty.openpty()
        attrs = termios.tcgetattr(slave)
        attrs[1] &= ~termios.OPOST
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        self.buf = bytearray()
        self.lock = threading.Lock()

        def child():
            if controlling:
                os.setsid()
                fcntl.ioctl(0, termios.TIOCSCTTY, 1)

        self.proc = subprocess.Popen(argv, env=env, cwd=cwd, stdin=slave if stdin_tty else subprocess.DEVNULL,
                                     stdout=slave, stderr=slave, preexec_fn=child,
                                     start_new_session=not controlling)
        os.close(slave)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        while True:
            try:
                r, _, _ = select.select([self.master], [], [], 0.2)
            except (OSError, ValueError):
                return
            if not r:
                if self.proc.poll() is not None:
                    # drain what is left, then stop
                    try:
                        r, _, _ = select.select([self.master], [], [], 0.2)
                        if not r:
                            return
                    except (OSError, ValueError):
                        return
                else:
                    continue
            try:
                data = os.read(self.master, 65536)
            except OSError:
                return
            if not data:
                return
            with self.lock:
                self.buf += data

    def raw(self):
        with self.lock:
            return bytes(self.buf)

    def text(self):
        return self.raw().decode("utf-8", errors="replace")

    def wait_for(self, needle, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            if needle in self.text():
                return True
            if self.proc.poll() is not None and needle not in self.text():
                time.sleep(0.3)
                return needle in self.text()
            time.sleep(0.02)
        return False

    def send(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        os.write(self.master, data)

    def finish(self, timeout=60):
        """(exit code, whole screen text). Kills the program if it does not end by itself."""
        try:
            rc = self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            rc = self.proc.wait()
        self.reader.join(timeout=3)
        try:
            os.close(self.master)
        except OSError:
            pass
        return rc, self.text()

    def hangup(self):
        """Close the terminal under the program."""
        try:
            os.close(self.master)
        except OSError:
            pass


def cli_argv(*args):
    return [sys.executable, "-m", "abf_platform"] + [str(a) for a in args]


def screen_before_question(text, question):
    """The lines of the screen up to (not including) the line that asks the question."""
    idx = text.rindex(question)
    return text[:idx]


class LaunchData:
    """A platform data folder with one available Slurm environment and one online agent that reported its facts.

    The command line is run as a process on this folder (ABF_PLATFORM_DB); no platform process and no agent is started,
    the rows are written the way the platform and the agent write them.
    """

    WORK = "/data/w1"
    STORAGE = "/data/storage"

    def __init__(self, ip, facts=None, ce_name="lab-a", agent="agent-t", head_job_options="-A %s -c 4 --mem=26G -t 4-00:00:00" % ACCOUNT,
                 environment=None, nextflow_config="process.executor = 'slurm'\n", **ce_extra):
        from abf_platform import agents, store
        self.ip = ip
        self.ce_name = ce_name
        self.agent = agent
        self.facts = {"slurm_account": ACCOUNT, "reach": "local", "platform_local": True,
                      "endpoint": "http://127.0.0.1:8787", "forward_file": None, "storage_root": self.STORAGE}
        self.facts.update(facts or {})
        flags = dict(work_dir=self.WORK, launch_dir="/data/launch", head_queue="normal", compute_queue="dev",
                     agent=agent, nextflow_config=nextflow_config)
        if head_job_options is not None:
            flags["head_job_options"] = head_job_options
        env = environment if environment is not None else [
            "both:http_proxy=http://login.example:18080", "head:NXF_OPTS=-Dhttp.proxyHost=login.example -Dhttp.proxyPort=18080",
            "head:NXF_SINGULARITY_CACHEDIR=/data/storage/cache"]
        flags["env"] = env
        flags.update(ce_extra)
        rc, out = ip.create_slurm(ce_name, **flags)  # the agent is not online yet, so no first preflight is queued
        assert rc == 0, out
        self.make_available()

    def register(self, facts):
        from abf_platform import agents
        agents.register(self.ip.state_db, self.agent, "0.1.0", time.time, facts=facts)

    def make_available(self):
        from test_station_envs import make_available
        make_available(self.ip, self.ce_name, agent=self.agent)
        self.register(self.facts)

    def env(self, **extra):
        e = pkg_env(ABF_PLATFORM_DB=self.ip.index, ABF_AGENT_HEARTBEAT_SECONDS=3600, ABF_PLATFORM_DEADLINE_LAUNCH=3,
                    ABF_PLATFORM_DEADLINE_CANCEL=3, ABF_PLATFORM_LAUNCH_GRACE=0)
        e.update({k: str(v) for k, v in extra.items()})
        return e

    def samplesheet(self, tmp_path, rows=None, name="samples.csv", header=("sample", "fastq_1")):
        rows = rows if rows is not None else [("s%02d" % i, "%s/rawdata/s%02d.fastq.gz" % (self.STORAGE, i)) for i in range(1, 11)]
        import csv
        p = Path(tmp_path) / name
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            for row in rows:
                if any("\x00" in c for c in row):  # the csv module of Python 3.10 cannot write a NUL: write it by hand
                    f.write(",".join('"%s"' % c.replace('"', '""') for c in row) + "\n")
                else:
                    w.writerow(row)
        return p

    def launch_args(self, tmp_path, run="run-one", rows=None, params=("primer=AGRG", "pacbio=true", "depth=3"), pipeline="nf-core/ampliseq",
                    revision="2.18.0", extra=()):
        sheet = self.samplesheet(tmp_path, rows)
        args = ["launch", "--ce", self.ce_name, "--pipeline", pipeline, "--revision", revision, "--run-name", run,
                "--samplesheet", str(sheet)]
        for p in params:
            args += ["--param", p]
        return args + list(extra)

    # --- what the platform and the token file hold ----------------------------------------------------------
    def rows(self, table):
        import sqlite3
        if not self.ip.state_db.exists():
            return []
        con = sqlite3.connect(str(self.ip.state_db))
        try:
            where = " WHERE kind NOT IN ('preflight', 'list_site_files')" if table == "jobs" else ""  # the first preflight is setup
            return con.execute("SELECT * FROM " + table + where).fetchall()
        finally:
            con.close()

    def count(self, table):
        return len(self.rows(table))

    def run_tokens(self):
        import sqlite3
        if not self.ip.tokens.exists():
            return 0
        con = sqlite3.connect(str(self.ip.tokens))
        try:
            return con.execute("SELECT COUNT(*) FROM tokens WHERE kind = 'run'").fetchone()[0]
        finally:
            con.close()

    def nothing_changed_since(self, before):
        return (self.count("jobs"), self.count("confirmations"), self.count("launches"), self.run_tokens()) == before

    def snapshot(self):
        return (self.count("jobs"), self.count("confirmations"), self.count("launches"), self.run_tokens())


def prefix_lines(text):
    """Split a screen into lines; the last element is the unfinished line with the question."""
    return text.split("\n")
