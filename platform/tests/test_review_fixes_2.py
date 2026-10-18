# Nothing existing: tests for the second code review of PR #115 (specs/009c-human-channel/plan.md, "Ruling after the second code review"); the rules are ours.
"""009c second fix round, one test per item (R1..R8 are the numbers of the ruling)."""
import asyncio
import os
import sqlite3

import pytest

from human_harness import World, csrf_of, form_answer
from helpers import tool_json


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def update(w, text, args=()):
    con = sqlite3.connect(str(w.ip.state_db))
    con.execute(text, args)
    con.commit()
    con.close()


def launched_by(w, caller, run="run-one", slurm=4242):
    """A run that `caller` launched through a form and that the agent has answered (a Slurm number is recorded)."""
    out = w.launch(caller=caller, answer=form_answer(), run=run)
    assert out["sent"] is True
    update(w, "UPDATE launches SET slurm_job_id = ?, submitted_at = confirmed_at WHERE run_name = ?", (slurm, run))
    update(w, "UPDATE jobs SET state = 'done' WHERE kind = 'launch_nextflow'")
    return out


def cancel(w, caller, run="run-one", answer=None):
    return tool_json(w.call("cancel", {"run_name": run}, caller=caller, answer=answer))


# ---- R1: a cancel over MCP is for the caller's own launch -------------------------------------------------------------------

def test_r1_a_run_launched_at_the_terminal_cannot_be_cancelled_over_mcp(w):
    w.hand_over()                                   # the hand-off row has no launch confirmation made by a caller
    ann = w.user("ann")
    before = w.counts()
    out = cancel(w, ann, answer=form_answer())
    assert out["sent"] is False and out["ok"] is False and "not launched from this platform" in out["message"]
    assert w.counts() == before and w.jobs("cancel_run") == []


def test_r1_a_terminal_confirmed_launch_is_refused_too(w):
    ann = w.user("ann")
    out =w.launch(caller=ann, answer=form_answer(), run="run-t")      # a real launch job and row, then re-label who confirmed it
    assert out["sent"] is True
    update(w, "UPDATE launches SET slurm_job_id = 4242, submitted_at = confirmed_at WHERE run_name = 'run-t'")
    update(w, "UPDATE confirmations SET caller_user_id = NULL, channel = 'TERMINAL'")
    res = cancel(w, ann, run="run-t", answer=form_answer())
    assert res["sent"] is False and "not launched from this platform" in res["message"]
    assert w.jobs("cancel_run") == []


def test_r1_a_run_launched_by_somebody_else_cannot_be_cancelled(w):
    ann, bob = w.user("ann"), w.user("bob")
    launched_by(w, ann)
    out = cancel(w, bob, answer=form_answer())
    assert out["sent"] is False and out["ok"] is False and "not launched from this platform" in out["message"]
    assert w.jobs("cancel_run") == []


def test_r1_the_caller_who_launched_it_can_cancel_it(w):
    ann = w.user("ann")
    launched_by(w, ann)
    out = cancel(w, ann, answer=form_answer())
    assert out["sent"] is True and len(w.jobs("cancel_run")) == 1


def test_r1_the_terminal_cancel_path_is_unchanged(w):
    from abf_platform import actions
    from abf_launch import build
    w.hand_over()
    ce, bundle, row = build.prepare_cancel(w.ip.state_db, "run-one")
    cid, job_id = actions.cancel(w.ip.state_db, ce, bundle, confirmed_by=actions.TERMINAL)
    assert job_id and len(w.jobs("cancel_run")) == 1


# ---- R2: find_cancel is the caller's, and only while the job is alive ----------------------------------------------------------

def test_r2_find_cancel_is_filtered_by_caller(w):
    from abf_platform import confirm
    from abf_launch import build
    ann, bob = w.user("ann"), w.user("bob")
    launched_by(w, ann)
    assert cancel(w, ann, answer=form_answer())["sent"] is True
    ce, bundle, row = build.prepare_cancel(w.ip.state_db, "run-one")
    assert confirm.find_cancel(w.ip.state_db, bundle, ann.user_id) is not None
    assert confirm.find_cancel(w.ip.state_db, bundle, bob.user_id) is None
    assert confirm.find_cancel(w.ip.state_db, bundle, None) is None


@pytest.mark.parametrize("state,reused", [("queued", True), ("claimed", True), ("done", False), ("refused", False),
                                          ("error", False), ("expired", False)])
def test_r2_a_confirmed_cancel_is_reused_only_while_its_job_is_alive(w, state, reused):
    ann = w.user("ann")
    launched_by(w, ann)
    first = cancel(w, ann, answer=form_answer())
    assert first["sent"] is True
    update(w, "UPDATE confirmations SET used_at = created_at + 1 WHERE kind = 'cancel'")
    update(w, "UPDATE jobs SET state = ? WHERE kind = 'cancel_run'", (state,))
    again = cancel(w, ann)                              # no form this time: only a reused yes can make this sent
    if reused:
        assert again["sent"] is True and again["job_id"] == first["job_id"] and len(w.jobs("cancel_run")) == 1
    else:
        assert again["sent"] is False                   # it asked again instead
        assert len([r for r in w.confirmations() if r["kind"] == "cancel"]) == 2


# ---- R3: the login throttle counts the attempt before the slow check -----------------------------------------------------------

def test_r3_parallel_wrong_passwords_cannot_all_pass_the_throttle(w, monkeypatch):
    import time
    import httpx
    from abf_platform import store, web
    w.user("ann")
    seen = []

    def slow(tokens, name, password):
        seen.append(name)
        time.sleep(0.2)
        return None

    monkeypatch.setattr(store, "check_web_password", slow)
    app = web.create_app(w.ip.index, w.ip.tokens, w.ip.state_db, clock=w.clock)

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as c:
            return await asyncio.gather(*[c.post("/login", data={"name": "ann", "password": "wrong-password-xx"}) for _ in range(20)])

    codes = [r.status_code for r in asyncio.run(go())]
    assert len(seen) <= web.FAIL_LIMIT, (len(seen), codes)
    assert codes.count(429) >= 20 - web.FAIL_LIMIT


def test_r3_a_right_password_does_not_count_against_the_name(w):
    from abf_platform import web
    w.user("ann")
    c = w.web()
    for _ in range(web.FAIL_LIMIT * 2):
        assert w.login(c, "ann").status_code == 303        # 011a: a right password now redirects to the board


# ---- R4: the default of confirmations.state is pending ---------------------------------------------------------------------------

def test_r4_a_row_written_without_a_state_is_pending(w):
    update(w, "INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('x1', 'ab', 'launch', 1.0)")
    assert w.sql("SELECT state FROM confirmations WHERE id = 'x1'")[0]["state"] == "pending"
    cols = {r["name"]: r["dflt_value"] for r in w.sql("PRAGMA table_info(confirmations)")}
    assert cols["state"].strip("'") == "pending"


def test_r4_the_migration_marks_old_rows_confirmed_explicitly(tmp_path):
    from abf_platform import store
    path = tmp_path / "old.db"
    con = sqlite3.connect(str(path))
    con.executescript("CREATE TABLE confirmations (id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, kind TEXT NOT NULL, created_at REAL NOT NULL, "
                      "used_at REAL, caller_user_id INTEGER);"
                      "INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('old', 'ab', 'launch', 5.0);")
    con.commit()
    con.close()
    store.init_state(path)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM confirmations WHERE id = 'old'").fetchone()
    assert (row["state"], row["channel"], row["confirmed_at"]) == ("confirmed", "TERMINAL", 5.0)
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('new', 'cd', 'launch', 6.0)")
    assert con.execute("SELECT state FROM confirmations WHERE id = 'new'").fetchone()[0] == "pending"
    con.close()


def test_r4_every_insert_into_confirmations_names_state():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    found = 0
    for pkg in ("abf_platform", "abf_launch", "abf_station"):
        for p in (root / pkg).rglob("*.py"):
            for m in re.finditer(r"INSERT INTO confirmations\s*\(([^)]*)\)", p.read_text(encoding="utf-8")):
                found += 1
                assert "state" in m.group(1), p
    assert found >= 2


# ---- R5: a repeated call reuses a pending row only with more than 60 s left ---------------------------------------------------------

def test_r5_a_pending_row_with_less_than_a_minute_left_is_not_reused(w):
    from abf_platform import confirm
    path = w.ip.state_db
    bundle = {"version": 1, "run_name": "r5"}
    first = confirm.create_pending(path, "launch", "lab-a", bundle, "screen", 7, lambda: 1000.0)
    assert confirm.create_pending(path, "launch", "lab-a", bundle, "screen", 7, lambda: 1000.0 + confirm.PENDING_SECONDS - 61) == first
    late = confirm.create_pending(path, "launch", "lab-a", bundle, "screen", 7, lambda: 1000.0 + confirm.PENDING_SECONDS - 59)
    assert late != first
    row = w.sql("SELECT expires_at FROM confirmations WHERE id = ?", (late,))[0]
    assert row["expires_at"] == 1000.0 + confirm.PENDING_SECONDS - 59 + confirm.PENDING_SECONDS


# ---- R6: the samplesheet is read once, after the check, without following a link ------------------------------------------------

@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="needs O_NOFOLLOW (Linux)")
def test_r6_a_link_swapped_in_after_the_check_is_not_read(w, monkeypatch, tmp_path):
    from abf_platform import actions
    ann = w.user("ann")
    secret = tmp_path / "outside.csv"
    secret.write_text(w.sheet.read_text().replace("s01", "SECRET"))
    real_check = actions.confined_samplesheet

    def swap(platform_path, caller, samplesheet):
        real = real_check(platform_path, caller, samplesheet)
        os.unlink(real)
        os.symlink(str(secret), real)
        return real

    monkeypatch.setattr(actions, "confined_samplesheet", swap)
    out = w.launch(caller=ann, answer=form_answer())
    assert out["ok"] is False and out["sent"] is False
    assert w.counts() == (0, 0, 0)
    assert "SECRET" not in str(out)


def test_r6_a_plain_file_in_the_area_still_works(w):
    ann = w.user("ann")
    assert w.launch(caller=ann, answer=form_answer())["sent"] is True


# ---- R7: a non-ASCII cookie or csrf value is a refusal --------------------------------------------------------------------------------

def test_r7_a_non_ascii_cookie_is_the_login_page_not_an_error(w):
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = w.web()
    r = c.get("/c/" + rid, headers=[(b"cookie", b"abf_web=abc.\xe9\xe9")])
    assert r.status_code == 200 and 'action="/login"' in r.text
    r = c.get("/c/" + rid, headers=[(b"cookie", b"abf_web=\xe9.abc")])
    assert r.status_code == 200 and 'action="/login"' in r.text


def test_r7_a_non_ascii_csrf_value_is_refused(w):
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = w.web()
    w.login(c, "ann")
    r = c.post("/c/" + rid, data={"csrf": "é" * 64})
    assert r.status_code == 403 and w.jobs() == []
    r = c.post("/logout", data={"csrf": "é"})
    assert r.status_code in (303, 403)


# ---- R8: the page binds loopback only; old confirmed page rows lose their content too ----------------------------------------------------

@pytest.mark.parametrize("args", [["--host", "0.0.0.0", "--public-url", "https://abf.example"], ["--host", "::", "--public-url", "https://abf.example"],
                                  ["--host", "192.168.1.5", "--public-url", "https://abf.example"],
                                  ["--host", "0.0.0.0"]])
def test_r8_a_non_loopback_host_is_refused_whatever_the_public_url_says(w, args):
    from helpers import run_cli
    r = run_cli(["web", "--port", "0"] + args, env=w.data.env(), timeout=30)
    text = r.stderr + r.stdout
    assert r.returncode != 0 and "rejected" in text and "loopback" in text
    from abf_platform import store
    assert store.get_meta(w.ip.state_db, "web_base_url") is None


def test_r8_confirmed_rows_lose_their_content_after_seven_days_too(w):
    ann = w.user("ann")
    ok = w.launch(caller=ann, answer=form_answer(), run="run-c")
    page = w.launch(caller=ann, run="run-p")["id"]
    c = w.web()
    w.login(c, "ann")
    c.post("/c/" + page, data={"csrf": csrf_of(c.get("/c/" + page).text)})
    assert w.sql("SELECT state FROM confirmations WHERE id = ?", (page,))[0]["state"] == "confirmed"
    day = 86400
    update(w, "UPDATE confirmations SET created_at = created_at - ?, expires_at = expires_at - ?", (8 * day, 8 * day))
    fresh = w.launch(caller=ann, run="run-d")["id"]
    rows = {r["id"]: r for r in w.confirmations()}
    for rid in (ok["id"], page):
        # keep-submissions (maintainer, 2026-10-18, TC-010): a confirmed row keeps its content at any age (the test name is the old rule)
        assert rows[rid]["bundle_json"] is not None and rows[rid]["screen_text"] is not None
        assert rows[rid]["state"] == "confirmed" and rows[rid]["channel"] in ("ELICITED", "PAGE") and rows[rid]["confirmed_at"]
    assert rows[fresh]["bundle_json"] is not None
    assert len(w.jobs("launch_nextflow")) == 2             # the jobs keep their own copy of the bundle
