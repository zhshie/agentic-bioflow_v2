# Nothing existing: glue for the 116 tests (two people on one platform, each with an environment and an agent of their own); no library plays "two lab members".
"""Helpers for the owner-binding tests (spec 116): alice owns what the setup made, bob owns an environment and an agent of his own."""
import csv
import json
import sqlite3
import time
from pathlib import Path

from helpers import tool_json
from human_harness import form_answer

SHARED = "/data/shared"


def sql_rows(db, text, args=()):
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        return con.execute(text, args).fetchall()
    finally:
        con.close()


def sql_exec(db, text, args=()):
    con = sqlite3.connect(str(db))
    try:
        with con:
            con.execute(text, args)
    finally:
        con.close()


class Duo:
    """The World of spec 009c with two users. alice is the first to exist, so she owns the environment `lab-a` and the agent `agent-t`
    that the setup made (what the migration does for a platform with one user); bob owns `b1` and `agent-b`, made on demand."""

    def __init__(self, w):
        from abf_platform import store
        self.w = w
        self.state = w.ip.state_db
        self.uploads = Path(store.uploads_root(self.state))
        self.a = w.user("alice")
        store.assign_orphans(self.state, w.ip.tokens)
        self.b = w.user("bob")
        rc, out = w.ip.run("ce", "update", "lab-a", "--read-root=%s" % self.uploads, "--read-root=%s" % SHARED)
        assert rc == 0, out
        self.sheet_n = 0

    # ---- bob's environment and agent -----------------------------------------------------------------------------------
    def bobs_environment(self, name="b1", agent="agent-b", owner=None, primary=False):
        from abf_platform import agents, compute_envs
        owner = self.b.user_id if owner is None else owner
        compute_envs.create(self.state, {"name": name, "platform": "slurm-platform", "agent": agent, "owner_user_id": owner,
                                         "config": {"workDir": "/data/w2", "launchDir": "/data/launch2", "headQueue": "normal",
                                                    "headJobOptions": "-A ACCT-TEST-7 -c 4",
                                                    "readRoots": [str(self.uploads), SHARED]}})
        sql_exec(self.state, "UPDATE compute_envs SET status = 'available', checked_ok = 1 WHERE name = ?", (name,))
        agents.register(self.state, agent, "0.1.0", time.time, facts=self.w.data.facts, owner_user_id=owner)
        if primary:
            compute_envs.set_primary(self.state, name)

    def an_environment_nobody_owns(self, name="e0", agent="agent-0"):
        from abf_platform import agents, compute_envs
        compute_envs.create(self.state, {"name": name, "platform": "slurm-platform", "agent": agent,
                                         "config": {"workDir": "/data/w3", "launchDir": "/data/launch3", "headQueue": "normal",
                                                    "headJobOptions": "-A ACCT-TEST-7 -c 4", "readRoots": [str(self.uploads)]}})
        sql_exec(self.state, "UPDATE compute_envs SET status = 'available', checked_ok = 1 WHERE name = ?", (name,))
        agents.register(self.state, agent, "0.1.0", time.time, facts=self.w.data.facts)

    # ---- files in a caller's own upload folder ---------------------------------------------------------------------------
    def area(self, caller):
        return self.uploads / caller.name

    def sheet(self, caller, cells=None, name=None):
        """A samplesheet file in the caller's upload folder. `cells` are the path cells; the default ones lie in that very folder."""
        self.sheet_n += 1
        area = self.area(caller)
        area.mkdir(parents=True, exist_ok=True)
        cells = cells if cells is not None else ["%s/rawdata/s%02d.fastq.gz" % (area, i) for i in (1, 2)]
        path = area / (name or "sheet%d.csv" % self.sheet_n)
        with open(path, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(("sample", "fastq_1"))
            for i, c in enumerate(cells, 1):
                wr.writerow(("s%02d" % i, c))
        return path

    # ---- what the AI asks for -------------------------------------------------------------------------------------------
    def launch(self, caller, run="run-one", answer=None, cells=None, ce_name="lab-a", sheet=None, raw_args=None, text=None, nosheet=False):
        """text: the CSV itself, sent as `samplesheet_text` and no file is made; nosheet: no `samplesheet` argument at all."""
        if text is not None or nosheet:
            args = self.w.choices(run=run, ce_name=ce_name)
            del args["samplesheet"]
            if text is not None:
                args["samplesheet_text"] = text
        else:
            sheet = sheet or self.sheet(caller, cells)
            args = self.w.choices(run=run, samplesheet=str(sheet), ce_name=ce_name)
        if ce_name is None:
            del args["ce_name"]
        args.update(raw_args or {})
        return tool_json(self._call("launch", args, caller, answer))

    def sent(self, caller, run="run-one", **kw):
        out = self.launch(caller, run=run, answer=form_answer(), **kw)
        assert out["sent"] is True, out
        return out

    def _call(self, name, args, caller, answer):
        _, outs = self.w.mcp([(name, args)], caller=caller, answer=answer, raw=True)
        return outs[0]

    def call(self, name, args=None, caller=None, answer=None):
        return tool_json(self._call(name, args or {}, caller, answer))

    # ---- runs ----------------------------------------------------------------------------------------------------------
    def add_run(self, name, user_id=None, launch_row=True):
        """A run in the index; its launches row names `user_id` (None: nobody). launch_row=False leaves the hand-off record without it."""
        from abf_platform import store
        con = store.connect_index(self.w.ip.index)
        try:
            with con:
                con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                            "VALUES (?, ?, ?, 'live', 'succeeded', 1, 2, 3)", ("id-" + name, "sess-" + name, name))
        finally:
            con.close()
        if launch_row:
            self.add_launch_row(name, user_id)
        return "id-" + name

    def add_launch_row(self, name, user_id):
        sql_exec(self.state, "INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?, ?, 'lab-a', 'agent-t', ?, ?)",
                 (name, "/data/w1/runs/" + name, time.time(), user_id))

    def run_names(self, caller):
        return sorted(r["name"] for r in self.call("list_runs", caller=caller)["runs"])
