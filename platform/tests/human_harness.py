# Nothing existing: glue for the 009c tests (a data folder with an environment, users with web passwords, the MCP tools driven in process with a scripted form answer, the confirmation page in a test client); no library plays "a person who answers the form".
"""Helpers for the human-channel tests (spec 009c): who the caller is, how the person answers, what the page shows."""
import asyncio
import re
import sqlite3
import time

from helpers import Clock, tool_json
from launch_harness import LaunchData
from station_harness import Inproc

PASSWORD = "correct horse battery"


class World:
    """One platform data folder (an available environment, an agent with facts), plus users, MCP calls and the web page."""

    def __init__(self, tmp_path, monkeypatch):
        from abf_platform import store
        self.ip = Inproc(tmp_path / "ip", monkeypatch)
        self.uploads = store.uploads_root(self.ip.state_db)
        self.data = LaunchData(self.ip, read_root=[str(self.uploads)])       # 116: over HTTP a path cell must lie in the caller's folder, which the environment may read
        self.tmp = tmp_path
        self.monkeypatch = monkeypatch
        self.clock = Clock(time.time())
        self.sheet = self.data.samplesheet(tmp_path)
        self._setup_jobs, self._setup_confirmations = set(), set()     # made by hand_over(by=...): the launch a cancel needs, not the test's subject

    # ---- the people ---------------------------------------------------------------------------------------------
    def user(self, name, password=PASSWORD):
        from abf_platform import actions, store
        uid = store.create_user(self.ip.tokens, name, "lab-x")
        store.assign_orphans(self.ip.state_db, self.ip.tokens)     # 116: the first person to exist owns what the setup made (the migration does the same)
        if password is not None:
            store.set_web_password(self.ip.tokens, name, password)
        return actions.Caller(uid, name, "lab-x")

    # ---- what the AI asks for ------------------------------------------------------------------------------------
    def choices(self, run="run-one", **over):
        c = {"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "run_name": run, "samplesheet": str(self.sheet),
             "ce_name": "lab-a", "params": {"primer": "AGRG", "pacbio": True, "depth": 3}}
        c.update(over)
        return c

    def move_into_area(self, src, dest, area):
        """Copy a samplesheet to `dest`, each absolute path in it moved under `area` (116: over HTTP every path cell must lie in the
        caller's own folder). The cell keeps its whole old path below the folder, so two cells stay two cells."""
        import csv
        from pathlib import Path
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(src, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        with open(dest, "w", newline="", encoding="utf-8") as f:
            out = csv.writer(f, lineterminator="\n")
            for i, row in enumerate(rows):
                out.writerow(row if i == 0 else [str(area) + c if c.startswith("/") else c for c in row])
        return dest

    def env_for(self, caller):
        """The environment this caller launches on: `lab-a` for its owner (and for stdio), else an environment of their own, made
        on first use in the shape of lab-a with an agent of their own (116: nobody launches on somebody else's)."""
        from abf_platform import agents, compute_envs
        if caller is None or self.sql("SELECT owner_user_id FROM compute_envs WHERE name = 'lab-a'")[0][0] == caller.user_id:
            return "lab-a"
        name, agent = "lab-" + caller.name, "agent-" + caller.name
        if not self.sql("SELECT 1 FROM compute_envs WHERE name = ?", (name,)):
            base = compute_envs.get(self.ip.state_db, "lab-a")
            compute_envs.create(self.ip.state_db, {"name": name, "platform": base["platform"], "agent": agent,
                                                   "owner_user_id": caller.user_id, "config": base["config"]})
            con = sqlite3.connect(str(self.ip.state_db))
            with con:
                con.execute("UPDATE compute_envs SET status = 'available', checked_ok = 1 WHERE name = ?", (name,))
            con.close()
            agents.register(self.ip.state_db, agent, "0.1.0", time.time, facts=self.data.facts, owner_user_id=caller.user_id)
        return name

    def in_area(self, caller, args):
        """Over HTTP a samplesheet must be in the caller's own upload folder (review finding 2), and so must every path in it (116):
        put a copy of the given file there, and launch on an environment the caller owns (the first user owns lab-a)."""
        from pathlib import Path
        src = Path(args["samplesheet"])
        area = self.ip.state_db.parent / "uploads" / caller.name
        dest = area / src.name
        if src.is_file() and not dest.exists():
            self.move_into_area(src, dest, area)
        if args.get("ce_name") == "lab-a":
            args = dict(args, ce_name=self.env_for(caller))
        return dict(args, samplesheet=str(dest))

    def mcp(self, calls, caller=None, answer=None, raw=False):
        """Tool calls in process. `caller` is who the HTTP bearer check would have found (None: local stdio); `answer` is the
        form callback of the client (None: a client that cannot show forms). A launch from a caller reads the file from the caller's
        own upload folder, so the file is copied there first, unless raw=True (a test of the confinement itself)."""
        if caller is not None and not raw:
            calls = [(n, self.in_area(caller, a) if n == "launch" and isinstance(a.get("samplesheet"), str) else a) for n, a in calls]
        from mcp import Client
        from abf_platform import http_auth, mcp_server
        self.monkeypatch.setattr(http_auth, "current_caller", lambda: caller)

        async def go():
            kw = {"elicitation_callback": answer} if answer else {}
            kw["mode"] = "legacy"     # the handshake with a back channel, which is what a form needs (Claude Code connects this way)
            async with Client(mcp_server.build_server(self.ip.index), **kw) as c:
                tools = (await c.list_tools()).tools
                return tools, [await c.call_tool(n, a) for n, a in calls]

        return asyncio.run(go())

    def call(self, name, args, caller=None, answer=None):
        tools, outs = self.mcp([(name, args)], caller=caller, answer=answer)
        return outs[0]

    def launch(self, caller=None, answer=None, **over):
        return tool_json(self.call("launch", self.choices(**over), caller=caller, answer=answer))

    # ---- what the database holds ------------------------------------------------------------------------------------
    def sql(self, text, args=()):
        con = sqlite3.connect(str(self.ip.state_db))
        con.row_factory = sqlite3.Row
        try:
            return con.execute(text, args).fetchall()
        finally:
            con.close()

    def jobs(self, kind=None):
        rows = self.sql("SELECT * FROM jobs WHERE kind IN ('launch_nextflow', 'cancel_run')")
        return [r for r in rows if (kind is None or r["kind"] == kind) and r["id"] not in self._setup_jobs]

    def confirmations(self):
        return [r for r in self.sql("SELECT * FROM confirmations ORDER BY created_at, id") if r["id"] not in self._setup_confirmations]

    def counts(self):
        return (len(self.jobs()), len(self.confirmations()), len(self.sql("SELECT * FROM launches")))

    def hand_over(self, run="run-one", slurm=4242, by=None):
        """A launched run with a Slurm number. By default the terminal's kind of row (no launch job, nobody's confirmation); with
        `by` (a Caller) the run was launched by that user through a form, as a cancel over MCP now needs (second review, item 1)."""
        if by is None:
            from test_launch_cli import hand_over
            hand_over(self.data, run=run, slurm=slurm)
            return
        out = self.launch(caller=by, answer=form_answer(), run=run)
        assert out["sent"] is True, out
        self._setup_jobs.add(out["job_id"])
        self._setup_confirmations.add(out["id"])
        con = sqlite3.connect(str(self.ip.state_db))
        con.execute("UPDATE launches SET slurm_job_id = ?, submitted_at = confirmed_at WHERE run_name = ?", (slurm, run))
        con.execute("UPDATE jobs SET state = 'done' WHERE kind = 'launch_nextflow'")
        con.commit()
        con.close()

    # ---- the confirmation page ---------------------------------------------------------------------------------------
    def web(self, public_url=None, clock=None):
        from starlette.testclient import TestClient
        from abf_platform import web
        app = web.create_app(self.ip.index, self.ip.tokens, self.ip.state_db, clock=clock or self.clock, public_url=public_url)
        return TestClient(app, follow_redirects=False)

    def login(self, client, name, password=PASSWORD):
        return client.post("/login", data={"name": name, "password": password})


def form_answer(action="accept", content=None, seen=None, raise_=None, delay=None):
    """The callback of a client that shows forms: it answers as scripted and keeps what it was shown in `seen`."""
    from mcp_types import ElicitResult
    content = {"送出": True} if content is None and action == "accept" else content

    async def cb(context, params):
        if seen is not None:
            seen.append(params)
        if delay:
            await asyncio.sleep(delay)
        if raise_:
            raise raise_
        return ElicitResult(action=action, content=content)

    return cb


def csrf_of(html):
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    return m.group(1) if m else None


def pending_id_of(url):
    return re.search(r"/c/([0-9a-f]{32})", url).group(1)
