# Nothing existing: glue for the 009e tests (a run folder as a first launch leaves it, a resume bundle for it, a failed run in the index and in the hand-off record); no library plays "a Nextflow run that failed on a cluster".
"""Helpers for the resume and relaunch tests (spec 009e)."""
import asyncio
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path

SESSION = "0b1c2d3e-4f50-4a6b-8c7d-9e0f1a2b3c4d"
OLD_TOKEN = "abf_" + secrets.token_hex(16)      # the token of the first launch, which is in tower.token until the resume replaces it; made at run time: a fixed value of this shape in a tracked file fails tests/credentials_stay_in_settings_test.sh
FILE_NAMES = ("samplesheet.csv", "params.yaml", "nextflow.config", "head.sh")


# ---- the site: a run folder as a first launch and a failed Nextflow leave it ----------------------------------------------------------

def make_folder(origin, session=SESSION, history=True, where=None):
    """Write the folder of the launch `origin` the way the agent wrote it, plus what Nextflow left in it."""
    f = Path(where or origin["run_folder"])
    f.mkdir(parents=True, mode=0o700)
    for name in FILE_NAMES:
        (f / name).write_bytes(origin["files"][name].encode("utf-8"))
        (f / name).chmod(0o600)
    (f / "tower.token").write_text(OLD_TOKEN)
    (f / "tower.token").chmod(0o600)
    if history:
        (f / ".nextflow").mkdir()
        (f / ".nextflow" / "history").write_text(
            "2026-10-18 10:00:00\t3m 2s\tcrazy_darwin\tERR\t3fa2b1c9d0\t%s\tnextflow run nf-core/ampliseq -r 2.18.0\n" % session)
    (f / "work" / "ab").mkdir(parents=True)
    (f / "work" / "ab" / "task.txt").write_text("a finished task that a resume may reuse")
    return f


def resume_bundle(site, fake, run="run-a", new="run-a-a2", attempt=2, session=SESSION, slurm=4242, **over):
    """(origin, resume bundle) for the first launch `run` of tests/test_station_launch.py's site."""
    from abf_station import launch
    from test_station_launch import bundle_for
    origin = bundle_for(site, fake, run=run, **over)
    return origin, launch.render_resume_bundle(origin=origin, run_name=new, attempt=attempt, session_id=session, of_run=run,
                                               of_slurm_job_id=slurm)


def relaunch_bundle(site, fake, run="run-a", new="run-a-a2", attempt=2, **over):
    """(origin, relaunch bundle): the same samples and parameters under a new name, with the record of what it is a relaunch of."""
    from test_station_launch import bundle_for
    origin = bundle_for(site, fake, run=run, **over)
    b = bundle_for(site, fake, run=new, **over)
    b["relaunch"] = {"of_run": run, "attempt": attempt, "of_sha256": "7" * 64}
    return origin, b


# ---- the platform: a first launch, finished and failed ------------------------------------------------------------------------------------

class FakePerson:
    """The person behind an MCP call. answer True: presses send; False: declines; None: the client cannot show a form."""

    def __init__(self, answer=True):
        self.answer = answer
        self.seen = []

    def can_ask(self):
        return self.answer is not None

    async def says_yes(self, text):
        self.seen.append(text)
        return (True, "") if self.answer else (False, "the person did not say yes (本人沒有按送出): decline")


class Rig:
    """A World (one data folder with an available environment and an agent that reported its facts) plus the verbs of 009e:
    a first launch that is handed over and fails, and the actions asked the way the MCP tools and the terminal ask them."""

    def __init__(self, tmp_path, monkeypatch):
        from human_harness import World
        self.w = World(tmp_path, monkeypatch)
        self.state = self.w.ip.state_db
        self.index = self.w.ip.index
        self.n_slurm = 4000

    # ---- people ----------------------------------------------------------------------------------------------------------------------------
    def user(self, name):
        return self.w.user(name)

    # ---- a first launch ---------------------------------------------------------------------------------------------------------------------
    def first(self, run="run-one", caller=None, status="failed", session=SESSION, slurm=None, pipeline="nf-core/ampliseq", with_run=True,
              samplesheet=None, params=None, finish=True):
        """The terminal's first launch of `run`, handed over to Slurm, and its row in the run index with this end ("failed",
        "succeeded", None: still running). Returns the bundle."""
        from abf_launch import build
        from abf_platform import actions
        ce, bundle = build.prepare_launch(self.state, ce="lab-a", pipeline=pipeline, revision="2.18.0", run_name=run,
                                          samplesheet=str(samplesheet or self.w.sheet),
                                          params=params or {"primer": "AGRG", "pacbio": True, "depth": 3},
                                          owner=caller.user_id if caller else None)
        _, job_id = actions.launch(self.state, ce, bundle, confirmed_by=actions.TERMINAL, caller=caller)
        if finish:
            self.hand_over(job_id, run, slurm)
            if with_run:
                self.set_run(run, status, session)
        return bundle

    def hand_over(self, job_id, run, slurm=None):
        self.n_slurm += 1
        slurm = slurm or self.n_slurm
        con = sqlite3.connect(str(self.state))
        with con:
            con.execute("UPDATE jobs SET state = 'done', finished_at = ?, result_json = ? WHERE id = ?",
                        (time.time(), json.dumps({"ok": True, "slurm_job_id": slurm}), job_id))
            con.execute("UPDATE launches SET slurm_job_id = ?, submitted_at = confirmed_at WHERE job_id = ?", (slurm, job_id))
        con.close()
        return slurm

    def set_run(self, run, status, session=SESSION):
        """The row Nextflow's own events would make in the index: failed, succeeded, or None for one that is still reporting."""
        from abf_platform import store
        con = store.connect_index(self.index)
        try:
            with con:
                con.execute("DELETE FROM runs WHERE run_name = ?", (run,))
                con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                            "VALUES (?, ?, ?, 'live', ?, ?, ?, ?)",
                            ("id-" + run, session, run, status, time.time() - 100, time.time() - 50 if status else None, time.time()))
        finally:
            con.close()

    def fail_job(self, job_id, state="refused"):
        """The agent refused (or never took) this job: nothing was done on the site."""
        con = sqlite3.connect(str(self.state))
        with con:
            con.execute("UPDATE jobs SET state = ?, finished_at = ? WHERE id = ?", (state, time.time(), job_id))
        con.close()

    def age_requests(self, seconds=3600):
        """Make every request of a person's yes older than the ten minutes it is alive for."""
        con = sqlite3.connect(str(self.state))
        with con:
            con.execute("UPDATE confirmations SET expires_at = expires_at - ? WHERE expires_at IS NOT NULL", (seconds,))
        con.close()

    # ---- the actions, asked ----------------------------------------------------------------------------------------------------------------------
    def ask(self, verb, run, caller=None, person=None, remote=False):
        from abf_platform import actions
        fn = getattr(actions, "request_" + verb)
        return asyncio.run(fn(self.state, run_name=run, caller=caller, person=person, remote=remote, index_path=self.index))

    def resume(self, run, **kw):
        return self.ask("resume", run, **kw)

    def relaunch(self, run, **kw):
        return self.ask("relaunch", run, **kw)

    def prepare(self, verb, run, owner=None, area=None):
        from abf_launch import build
        return getattr(build, "prepare_" + verb)(self.state, run, index_path=self.index, owner=owner, area=area)

    def attempt(self, verb, run, caller=None, status="failed", session=SESSION):
        """Resume or relaunch `run` with a yes, hand the new job over to Slurm and give it this end in the index. Returns the answer."""
        out = self.ask(verb, run, caller=caller, person=FakePerson(True))
        assert out["sent"] is True, out
        row = self.row_of_job(out["job_id"])
        self.hand_over(out["job_id"], row["run_name"])
        self.set_run(row["run_name"], status, session)
        return out

    # ---- what the database holds ----------------------------------------------------------------------------------------------------------------
    def sql(self, text, args=()):
        con = sqlite3.connect(str(self.state))
        con.row_factory = sqlite3.Row
        try:
            return con.execute(text, args).fetchall()
        finally:
            con.close()

    def launches(self):
        return self.sql("SELECT * FROM launches ORDER BY id")

    def row_of_job(self, job_id):
        return self.sql("SELECT * FROM launches WHERE job_id = ?", (job_id,))[0]

    def jobs(self):
        return self.sql("SELECT * FROM jobs WHERE kind = 'launch_nextflow' ORDER BY id")

    def confirmations(self):
        return self.sql("SELECT * FROM confirmations ORDER BY created_at, id")

    def counts(self):
        return (len(self.jobs()), len(self.confirmations()), len(self.launches()))

    def bundle_of_job(self, job_id):
        return json.loads(self.sql("SELECT args_json FROM jobs WHERE id = ?", (job_id,))[0][0])["bundle"]
