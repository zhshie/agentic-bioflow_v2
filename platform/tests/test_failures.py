# Nothing existing: tests of the failed-run summary (spec failure-seqera); they drive our own view builder, action layer and recorded runs.
"""A failed run as Seqera shows it: failed tasks, exit codes, the two actions. No cause is classified here.

Test cases are named in the comments (TC-001 ...), see specs/failure-seqera/test-case.md.
"""
import ast
import json
import re
import sqlite3
import time

from abf_platform import actions, failures, status, store
from helpers import Clock, Platform, PLATFORM_DIR, REPO_ROOT, all_files_digest, own_runs, variant

PKG = PLATFORM_DIR / "abf_platform"
TASK = {"name": "NFCORE_AMPLISEQ:AMPLISEQ:DADA2_DENOISING", "exit_code": 137, "error_message": "Killed", "workdir": "/site/ab/cdef"}


def mk(status_="failed", succeeded=3, cached=0, tasks=None, **extra):
    v = {"id": "r1", "name": "x", "status": status_, "tasks": {"succeeded": succeeded, "cached": cached, "failed": 1},
         "failed_tasks": [dict(TASK)] if tasks is None else tasks}
    v.update(extra)
    return v


def strings_of(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings_of(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from strings_of(v)


def keys_of(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from keys_of(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from keys_of(v)


# ---- the pure function -------------------------------------------------------------------------------------------------

def test_ff01_not_failed_is_none():
    # TC-001, TC-002
    assert failures.summarize(mk("running")) is None
    assert failures.summarize(mk("succeeded")) is None


def test_ff02_failed_tasks_are_carried_verbatim():
    # TC-003
    out = failures.summarize(mk())
    assert out["failed_tasks"] == [TASK]
    assert out["failed_tasks"][0]["exit_code"] == 137 and isinstance(out["failed_tasks"][0]["exit_code"], int)


def test_ff03_lost_is_unknown():
    # TC-010, TC-011, TC-017
    out = failures.summarize(mk("lost", succeeded=0))
    assert out["status_seqera"] == "unknown" and out["actions"] == ["relaunch"]
    assert failures.summarize(mk("failed"))["status_seqera"] == "failed"


def test_ff04_cancel_requested_is_cancelled():
    # TC-012, TC-013
    assert failures.summarize(mk(cancel_requested_at="2026-10-23T01:00:00.000+00:00"))["status_seqera"] == "cancelled"
    assert failures.summarize(mk("lost", cancel_requested_at="2026-10-23T01:00:00.000+00:00"))["status_seqera"] == "cancelled"


def test_ff05_resume_and_relaunch_when_tasks_completed():
    # TC-014, TC-016
    assert failures.summarize(mk(succeeded=3))["actions"] == ["resume", "relaunch"]
    assert failures.summarize(mk(succeeded=0, cached=2))["actions"] == ["resume", "relaunch"]


def test_ff06_relaunch_only_when_nothing_completed():
    # TC-015
    assert failures.summarize(mk(succeeded=0, cached=0))["actions"] == ["relaunch"]


FIVE = {"status_seqera", "failed_tasks", "failure_reason", "log", "actions"}


def test_ff07_shape_is_fixed():
    # TC-018, TC-019, TC-020, TC-006, TC-036, TC-037
    views = [mk(), mk("lost", succeeded=0), mk(succeeded=0, failure_reason="Process `X` terminated with an error exit status (137)")]
    banned = {"cause", "category", "class", "kind", "type", "reason_class", "evidence", "advice", "hint", "suggestion", "recommended", "default"}
    fixed = {"failed", "unknown", "cancelled", "resume", "relaunch"}
    for v in views:
        out = failures.summarize(v)
        assert set(out) == FIVE
        assert set(out["actions"]) <= {"resume", "relaunch"} and len(set(out["actions"])) == len(out["actions"])
        assert not banned & set(keys_of(out))
        own = set(strings_of(v))
        assert all(s in own or s in fixed for s in strings_of(out)), set(strings_of(out)) - own - fixed
    assert failures.summarize(views[2])["failure_reason"] == views[2]["failure_reason"]


def test_carry_edges():
    # TC-004, TC-005, TC-007, TC-008, TC-009, TC-034, TC-035
    many = [{"name": "P%d" % ((i * 7) % 13), "exit_code": (i * 31) % 5, "error_message": "m%d" % i} for i in range(60)]
    assert failures.summarize(mk(tasks=many))["failed_tasks"] == many
    assert failures.summarize(mk(tasks=[]))["failed_tasks"] == []
    v = mk()
    del v["failed_tasks"]
    assert failures.summarize(v)["failed_tasks"] == []
    out = failures.summarize(mk(tasks=[{"name": "A", "exit_code": 1, "error_message": "e"}]))
    assert out["failure_reason"] is None and out["log"] is None and "workdir" not in out["failed_tasks"][0]
    a = failures.summarize(mk(tasks=[dict(TASK, exit_code=137)]))
    b = failures.summarize(mk(tasks=[dict(TASK, exit_code=1, error_message="No space left on device")]))
    for k in ("status_seqera", "actions"):
        assert a[k] == b[k]
    assert set(a) == set(b)


# ---- through the action layer ------------------------------------------------------------------------------------------

class Rig:
    def __init__(self, tmp_path):
        self.clock = Clock()
        self.plat = Platform(tmp_path / "p", clock=self.clock)
        self.token = self.plat.new_token()
        self.state = store.default_platform_path(self.plat.index)
        self.n = 0

    def run(self, scenario, name, user=1, **kw):
        self.n += 1
        wid, _ = self.plat.replay(variant(scenario, name, "sess-" + name, self.clock() - 100 + self.n), self.token, **kw)
        own_runs(self.state, user, [name])
        return wid

    def failed(self, name, user=1, exit_code=137):
        wid = self.run("fail_run", name, user)
        con = sqlite3.connect(str(self.plat.index))
        with con:
            con.execute("UPDATE failed_tasks SET exit_code = ?, error_message = 'Killed', name = 'DADA2_DENOISING' WHERE run_id = ?", (exit_code, wid))
        con.close()
        return wid

    @property
    def me(self):
        return actions.Caller(1, "a", "lab")

    @property
    def other(self):
        return actions.Caller(2, "b", "lab")

    def get(self, wid, caller=None):
        return actions.get_run(self.plat.index, wid, caller=caller or self.me, platform_path=self.state)

    def runs(self, caller=None):
        return actions.list_runs(self.plat.index, caller=caller or self.me, platform_path=self.state)["runs"]


def test_ff08_get_run_and_list_runs_carry_failure(tmp_path):
    # TC-021, TC-022, TC-029, TC-030, TC-033
    r = Rig(tmp_path)
    wid = r.failed("run-a")
    got = r.get(wid)
    assert got["failure"]["failed_tasks"][0]["exit_code"] == 137 and got["failure"]["status_seqera"] == "failed"
    row = [x for x in r.runs() if x["id"] == wid][0]
    assert row["failure"]["failed_tasks"][0]["exit_code"] == 137
    seen = r.get(wid, r.other)
    assert seen["found"] is False and "failure" not in seen and seen["message"] == actions.RUN_NOT_FOUND_TEXT % wid
    text = json.dumps(seen) + json.dumps(r.runs(r.other))
    assert "DADA2" not in text and "137" not in text and r.runs(r.other) == []
    nf = r.get("nope")
    assert nf["found"] is False and nf["message"] == actions.RUN_NOT_FOUND_TEXT % "nope"


def test_list_rows_and_non_failed(tmp_path):
    # TC-023, TC-024, TC-025, TC-031, TC-041
    r = Rig(tmp_path)
    ok = r.run("ok_run", "run-ok")
    live = r.run("ok_run", "run-live", stop_before="complete")
    bad = r.failed("run-bad")
    rows = {x["id"]: x for x in r.runs()}
    assert rows[ok]["failure"] is None and rows[live]["failure"] is None and rows[bad]["failure"] is not None
    base = {x["id"]: x for x in status.list_runs(r.plat.index, status.now())}
    for i, row in rows.items():
        assert set(row) == set(base[i]) | {"failure"}
        assert {k: v for k, v in row.items() if k != "failure"} == base[i]
        assert "failure" not in base[i]
    assert r.get(live)["failure"] is None and r.get(ok)["failure"] is None
    plain = status.get_run(r.plat.index, bad, status.now())
    assert "failure" not in plain
    got = r.get(bad)
    assert {k: v for k, v in got.items() if k != "failure"} == plain


def test_lost_and_cancelled(tmp_path, monkeypatch):
    # TC-026, TC-027, TC-028
    from abf_platform import common
    r = Rig(tmp_path)
    lost = r.run("ok_run", "run-lost", stop_before="complete")
    bad = r.failed("run-bad")
    con = sqlite3.connect(str(r.state))
    with con:
        con.execute("UPDATE launches SET cancel_requested_at = ? WHERE run_name = 'run-bad'", (time.time(),))
    con.close()
    monkeypatch.setenv("ABF_PLATFORM_CLOCK_OFFSET", str(r.clock() + common.LOST_AFTER_SECONDS + 60 - time.time()))
    row = [x for x in r.runs() if x["id"] == lost][0]
    assert row["status"] == "lost" and row["failure"]["status_seqera"] == "unknown"
    assert row["failure"]["actions"] in (["relaunch"], ["resume", "relaunch"])
    assert r.get(lost)["failure"]["status_seqera"] == "unknown"
    g = r.get(bad)
    assert g["status"] == "failed" and g["failure"]["status_seqera"] == "cancelled" and g["cancel_requested_at"]
    row = [x for x in r.runs() if x["id"] == bad][0]
    assert row["status"] == "failed" and row["failure"]["status_seqera"] == "cancelled"


def test_old_index_without_new_columns(tmp_path):
    # TC-032
    r = Rig(tmp_path)
    wid = r.failed("run-old")
    con = sqlite3.connect(str(r.plat.index))
    with con:
        con.execute("ALTER TABLE failed_tasks DROP COLUMN workdir")
        con.execute("ALTER TABLE runs DROP COLUMN failure_reason")
    con.close()
    for out in (r.get(wid)["failure"], [x for x in r.runs() if x["id"] == wid][0]["failure"]):
        assert out["failure_reason"] is None
        assert out["failed_tasks"][0]["exit_code"] == 137 and out["failed_tasks"][0]["error_message"] == "Killed"


def test_read_only_and_no_secret(tmp_path):
    # TC-039, TC-047, TC-048
    r = Rig(tmp_path)
    wid = r.failed("run-a")

    def schema():
        out = {}
        for p in (r.plat.index, r.state):
            c = sqlite3.connect(str(p))
            out[str(p)] = c.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()
            c.close()
        return out
    before, sch = all_files_digest(r.plat.index, r.state), schema()
    text = ""
    for _ in range(3):
        text += json.dumps(r.get(wid)) + json.dumps(r.runs())
    assert all_files_digest(r.plat.index, r.state) == before and schema() == sch
    assert r.token not in text


# ---- what is not done --------------------------------------------------------------------------------------------------

def _imports(path):
    names = set()
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            names |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            names |= {n.module or ""} | {a.name for a in n.names}
    return names


def test_ff09_failures_is_read_only():
    # TC-038, TC-040, TC-042
    src = (PKG / "failures.py").read_text(encoding="utf-8")
    imp = _imports(PKG / "failures.py")
    assert not imp & {"jobs", "confirm", "receiver", "status", "actions", "mcp_server", "sqlite3", "socket", "subprocess", "urllib",
                      "http", "requests", "httpx", "os"}
    assert not any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "open" for n in ast.walk(ast.parse(src)))
    assert "read_task_log" not in src and ".command.err" not in src


def test_untouched_modules_do_not_know_failure():
    # TC-043
    for f in ("web.py", "web_board.py", "receiver.py", "status.py"):
        p = PKG / f
        if p.exists():
            s = p.read_text(encoding="utf-8")
            assert not re.search(r"import[^\n]*\bfailures\b|\bfailures\.summarize", s) and '"failure"' not in s, f


def test_docs_and_ledger():
    # TC-049, TC-050
    doc = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    sec = doc.split("Failed runs", 1)[1]
    sec = re.split(r"\n## ", sec, 1)[0]
    for w in ("status_seqera", "failed_tasks", "failure_reason", "unknown", "Resume", "Relaunch", "resume-edit-params"):
        assert w in sec, w
    assert not re.search(r"\btw |station|ssh", sec)
    led = (REPO_ROOT / "specs" / "failure-seqera" / "ledger.md").read_text(encoding="utf-8")
    assert "resume-edit-params" in led
