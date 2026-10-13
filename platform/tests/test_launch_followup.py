# Nothing existing: tests of the 007b follow-up (a refused launch shown as refused, a refused name used again, the launches table upgraded); the rows and the rules are ours.
"""Follow-up 1 of feature 007b: F1 (what `launches` says of a launch without a Slurm number) and F2 (run names).

Everything runs on private folders under tmp and a fake clock or a pseudo-terminal; nothing here reads or writes the
acceptance setup that may be running on this machine, and no test uses a fixed port.
"""
import json
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from helpers import all_files_digest
from launch_harness import LaunchData, Pty, cli_argv, QUESTION_CANCEL, QUESTION_LAUNCH
from station_harness import Inproc
from test_launch_platform import (STATE_WORDS, bundle, create_body, setup, sql, tokens_rows, _queue_launch)
from test_station_platform import bearer, poll, state_db

REFUSAL = "預檢未通過，沒有建立任何東西：connect（No open connection to the site…"
UNKNOWN = "未送出：代理沒有回報 Slurm 工作編號（結果不明時請查國網上的專屬資料夾與 nf-%s）"
OLD_LAUNCHES = ("CREATE TABLE launches (id INTEGER PRIMARY KEY AUTOINCREMENT, run_name TEXT NOT NULL UNIQUE, slurm_job_id INTEGER, "
                "run_folder TEXT NOT NULL, ce TEXT NOT NULL, agent TEXT NOT NULL, confirmed_at REAL NOT NULL, submitted_at REAL, "
                "cancel_requested_at REAL)")
OLD_COLUMNS = "id, run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, cancel_requested_at"
FOLDER = "/data/w1/runs/%s"


# ---- helpers: rows written the way the platform writes them ------------------------------------------------------

def add_launch(db, run, slurm=None, state="refused", message=REFUSAL, left=None, deadline="future", late=None, no_job=False,
               cancel_at=None, link=True, folder=None, agent="a1"):
    """One launches row and (unless no_job) the launch job behind it. Returns (launch id, job id)."""
    now = time.time()
    folder = folder or FOLDER % run
    con = sqlite3.connect(str(db))
    try:
        job_id = None
        if not no_job:
            cid = secrets.token_hex(16)
            con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, used_at) VALUES (?, 'x', 'launch', ?, ?)",
                        (cid, now - 100, now - 50))
            result = None
            if state in ("done", "refused", "error"):
                result = {"ok": state == "done", "message": message}
                if left:
                    result["left_on_site"] = left
            dl = {"future": now + 3600, "past": now - 10}[deadline]
            cur = con.execute(
                "INSERT INTO jobs (agent, compute_env, kind, args_json, state, result_json, late_result_json, created_at, deadline_at, "
                "claimed_at, finished_at, confirmation_id) VALUES (?, 'lab-a', 'launch_nextflow', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (agent, json.dumps({"bundle": {"run_name": run, "run_folder": folder}, "confirmation_id": cid}), state,
                 json.dumps(result) if result else None, json.dumps(late) if late else None, now - 100, dl,
                 None if state == "queued" else now - 60, None if state in ("queued", "claimed") else now - 30, cid))
            job_id = cur.lastrowid
        cols = ["run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at", "cancel_requested_at"]
        vals = [run, slurm, folder, "lab-a", agent, now - 100, now - 90 if slurm else None, cancel_at]
        if link:
            cols.append("job_id")
            vals.append(job_id)
        cur = con.execute("INSERT INTO launches (%s) VALUES (%s)" % (", ".join(cols), ", ".join("?" * len(cols))), vals)
        con.commit()
        return cur.lastrowid, job_id
    finally:
        con.close()


def to_live_shape(db):
    """Make launches the table the live platform.db has now: run_name UNIQUE, no job_id."""
    con = sqlite3.connect(str(db))
    rows = con.execute("SELECT %s FROM launches ORDER BY id" % OLD_COLUMNS).fetchall()
    seq = con.execute("SELECT seq FROM sqlite_sequence WHERE name = 'launches'").fetchone()
    con.execute("DROP TABLE launches")
    con.execute(OLD_LAUNCHES)
    con.executemany("INSERT INTO launches (%s) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)" % OLD_COLUMNS, rows)
    con.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'launches'", (max(seq[0] if seq else 0, 40),))
    con.commit()
    con.close()


def live_shaped(tmp_path, name="live"):
    """A platform.db like the live one: UNIQUE on run_name, a row of a launch the agent refused."""
    from abf_platform import store
    db = tmp_path / name / "platform.db"
    store.connect_state(db).close()
    add_launch(db, "ampliseq-mt-0920-rerun")
    to_live_shape(db)
    return db


def dump(db):
    con = sqlite3.connect(str(db))
    try:
        return list(con.iterdump())
    finally:
        con.close()


def table(db, name, order="id"):
    con = sqlite3.connect(str(db))
    try:
        return con.execute("SELECT * FROM %s ORDER BY %s" % (name, order)).fetchall()
    finally:
        con.close()


def sql_one(db, text, args=()):
    con = sqlite3.connect(str(db))
    try:
        return con.execute(text, args).fetchone()[0]
    finally:
        con.close()


@pytest.fixture
def env(tmp_path, monkeypatch):
    from abf_platform import store
    ip = Inproc(tmp_path / "ip", monkeypatch)
    store.connect_state(ip.state_db).close()
    return ip


def listing(ip):
    rc, out = ip.run("launches")
    assert rc == 0, out
    blocks, cur = {}, None
    for ln in out.split("\n"):
        if ln and not ln.startswith(" "):
            cur = ln.split()[0]
            blocks.setdefault(cur, []).append([ln])
        elif ln.strip() and cur:
            blocks[cur][-1].append(ln)
    return out, blocks


# ---- F1 ----------------------------------------------------------------------------------------------------------

def test_tcf1_01_a_launch_the_agent_refused_is_shown_as_refused_with_the_agents_words(env):
    # TC-F1-01
    add_launch(env.state_db, "run-a")
    out, blocks = listing(env)
    lines = blocks["run-a"][0]
    assert lines[1] == "  被代理拒絕：" + REFUSAL, lines
    assert "未送出：代理沒有回報 Slurm 工作編號" not in out and "結果不明" not in out
    assert not STATE_WORDS.search(out) and not re.search(r"失敗|已取消|跑完", out)
    # the platform claims nothing of its own: a message without those words shows without them
    add_launch(env.state_db, "run-b", message="連線過期了")
    out, blocks = listing(env)
    assert blocks["run-b"][0][1] == "  被代理拒絕：連線過期了"
    assert "沒有建立任何東西" not in "\n".join(blocks["run-b"][0]) and "國網上沒有" not in "\n".join(blocks["run-b"][0])


def test_tcf1_02_a_launch_still_with_the_agent_says_so_with_its_own_job_number(env):
    # TC-F1-02
    _, j1 = add_launch(env.state_db, "run-q", state="queued")
    _, j2 = add_launch(env.state_db, "run-c", state="claimed")
    out, blocks = listing(env)
    assert blocks["run-q"][0][1] == "  等代理處理中（工作 %d）" % j1
    assert blocks["run-c"][0][1] == "  等代理處理中（工作 %d）" % j2
    assert "結果不明" not in out and "被代理拒絕" not in out


def test_tcf1_03_a_result_that_is_really_unknown_keeps_the_old_sentence(env):
    # TC-F1-03
    add_launch(env.state_db, "run-a", state="expired")
    add_launch(env.state_db, "run-b", state="queued", deadline="past")
    add_launch(env.state_db, "run-c", state="claimed", deadline="past")
    add_launch(env.state_db, "run-d", no_job=True)
    add_launch(env.state_db, "run-e", state="error", message="sbatch 沒有成功（結束碼 1）…", left="/data/w1/runs/run-e 與其中的檔案")
    out, blocks = listing(env)
    for run in "abcde":
        name = "run-" + run
        text = "\n".join(blocks[name][0])
        assert UNKNOWN % name in text, text
        assert "等代理處理中" not in text and "被代理拒絕" not in text
    e = "\n".join(blocks["run-e"][0])
    assert "sbatch 沒有成功（結束碼 1）…" in e and "/data/w1/runs/run-e 與其中的檔案" in e


def test_tcf1_04_the_agents_message_and_the_folder_are_escaped(env):
    # TC-F1-04
    add_launch(env.state_db, "run-x", message="A\x1b[31mred\rback\x00nul\nnext", folder="/data/\x1b[2Jfolder")
    rc, out = env.run("launches")
    raw = out.encode("utf-8")
    assert b"\x1b" not in raw and b"\r" not in raw and b"\x00" not in raw
    assert "被代理拒絕：A\\x1b[31mred\\rback\\x00nul\\nnext" in out and "/data/\\x1b[2Jfolder" in out


def test_tcf1_05_a_launch_with_a_slurm_number_is_listed_exactly_as_before(env):
    # TC-F1-05: the golden text is what the code before this change printed for the three rows
    from abf_platform import store
    add_launch(env.state_db, "run-1", slurm=111, state="done", message="ok")
    add_launch(env.state_db, "run-2", slurm=222, state="done", message="ok")
    add_launch(env.state_db, "run-3", slurm=333, state="done", message="ok", cancel_at=1_800_000_500.0)
    con = sqlite3.connect(str(env.state_db))
    con.execute("UPDATE launches SET confirmed_at = 1800000000.0, submitted_at = 1800000010.0")
    con.commit()
    con.close()
    idx = store.default_index_path()
    store.init_index(idx)
    con = sqlite3.connect(str(idx))
    con.execute("INSERT INTO runs (id, session_id, run_name, last_message_at) VALUES ('wf-2', 's', 'run-2', 1)")
    con.commit()
    con.close()
    when = lambda t: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    c, s = when(1_800_000_000.0), when(1_800_000_010.0)
    golden = ("run-1  Slurm 111  /data/w1/runs/run-1  確認於 %s\n  已送出，尚未收到 Nextflow 事件（%s 送出）\n"
              "run-2  Slurm 222  /data/w1/runs/run-2  確認於 %s\n  已收到 Nextflow 的事件；請用 get_run 看（run id wf-2）\n"
              "run-3  Slurm 333  /data/w1/runs/run-3  確認於 %s\n  已送出，尚未收到 Nextflow 事件（%s 送出）\n"
              "  取消請求已於 %s 送出\n") % (c, s, c, c, s, when(1_800_000_500.0))
    rc, out = env.run("launches")
    assert out == golden


def test_tcf1_06_two_rows_of_one_name_each_show_their_own_job(env):
    # TC-F1-06
    add_launch(env.state_db, "run-t", message="message A")
    _, j2 = add_launch(env.state_db, "run-t", state="queued")
    out, blocks = listing(env)
    first, second = blocks["run-t"]
    assert first[1] == "  被代理拒絕：message A" and second[1] == "  等代理處理中（工作 %d）" % j2
    add_launch(env.state_db, "run-u", message="message A")
    add_launch(env.state_db, "run-u", message="message B")
    out, blocks = listing(env)
    assert [b[1] for b in blocks["run-u"]] == ["  被代理拒絕：message A", "  被代理拒絕：message B"]


def test_tcf1_07_the_row_of_the_live_database_is_filled_in_by_the_upgrade(tmp_path, monkeypatch):
    # TC-F1-07: the maintainer's real example, on a database of the live shape
    from abf_platform import store
    db = live_shaped(tmp_path)
    ip = Inproc(tmp_path / "ip2", monkeypatch)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(db.parent / "index.db"))
    store.connect_state(db).close()
    rc, out = ip.run("launches")
    assert rc == 0 and "  被代理拒絕：" + REFUSAL in out and "ampliseq-mt-0920-rerun" in out, out


def test_tcf1_08_listing_an_upgrade_pending_database_does_not_change_it_and_does_not_crash(tmp_path, monkeypatch):
    # TC-F1-08
    db = live_shaped(tmp_path)
    con = sqlite3.connect(str(db))
    con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('other', '/f', 'lab-a', 'a1', 1.0)")
    con.commit()
    con.close()
    ip = Inproc(tmp_path / "ip3", monkeypatch)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(db.parent / "index.db"))
    digest = all_files_digest(db)
    rc, out = ip.run("launches")
    assert rc == 0 and out.count("確認於") == 2 and "Traceback" not in out, out
    assert all_files_digest(db) == digest
    assert not re.search(r"^  $", out, re.M)


# ---- F2: the check of the name -----------------------------------------------------------------------------------

@pytest.fixture
def data(tmp_path, monkeypatch):
    return LaunchData(Inproc(tmp_path / "ipl", monkeypatch))


def refused_before_the_question(data, tmp_path, run="run-one"):
    before = data.snapshot()
    p = Pty(cli_argv(*data.launch_args(tmp_path, run=run)), data.env())
    rc, screen = p.finish(60)
    assert rc != 0, screen
    assert QUESTION_LAUNCH not in screen and "送出確認" not in screen and "samplesheet.csv" not in screen, screen
    assert data.snapshot() == before, "no job, no confirmation, no launches row, no token"
    return screen


def test_tcf2_02_a_submitted_name_cannot_be_used_again(data, tmp_path):
    # TC-F2-02
    add_launch(data.ip.state_db, "run-one", slurm=2231948, state="done", message="ok")
    screen = refused_before_the_question(data, tmp_path)
    assert "已送出過" in screen and "2231948" in screen


@pytest.mark.parametrize("state", ["queued", "claimed"])
def test_tcf2_03_a_name_still_waiting_for_the_agent_cannot_be_used_again(data, tmp_path, state):
    # TC-F2-03
    add_launch(data.ip.state_db, "run-one", state=state)
    screen = refused_before_the_question(data, tmp_path)
    assert "還在等代理" in screen


@pytest.mark.parametrize("how", ["expired", "error", "queued-past", "claimed-past", "no-job", "late-refusal"])
def test_tcf2_04_a_name_with_an_unknown_result_cannot_be_used_again(data, tmp_path, how):
    # TC-F2-04
    db = data.ip.state_db
    if how == "expired":
        add_launch(db, "run-one", state="expired")
    elif how == "error":
        add_launch(db, "run-one", state="error", message="sbatch 沒有成功（結束碼 1）…")
    elif how == "queued-past":
        add_launch(db, "run-one", state="queued", deadline="past")
    elif how == "claimed-past":
        add_launch(db, "run-one", state="claimed", deadline="past")
    elif how == "no-job":
        add_launch(db, "run-one", no_job=True)
    else:
        add_launch(db, "run-one", state="expired", late={"state": "refused", "result": {"ok": False, "message": "late no"}})
    screen = refused_before_the_question(data, tmp_path)
    assert "結果不明，請先查國網上的專屬資料夾與 nf-run-one" in screen


@pytest.mark.parametrize("second,allowed", [("submitted", False), ("unknown", False), ("refused", True)])
def test_tcf2_05_the_strictest_row_of_the_history_decides(data, tmp_path, second, allowed):
    # TC-F2-05
    db = data.ip.state_db
    add_launch(db, "run-one", message="first refusal")
    if second == "submitted":
        add_launch(db, "run-one", slurm=77, state="done", message="ok")
    elif second == "unknown":
        add_launch(db, "run-one", state="expired")
    else:
        add_launch(db, "run-one", message="second refusal")
    if not allowed:
        refused_before_the_question(data, tmp_path)
        return
    p = Pty(cli_argv(*data.launch_args(tmp_path, run="run-one")), data.env())
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    p.send("y\n")
    p.finish(60)
    rows = table(data.ip.state_db, "launches")
    assert len(rows) == 3 and [r[1] for r in rows] == ["run-one"] * 3


def test_tcf0_05_a_reusable_name_still_needs_the_y_on_the_terminal(data, tmp_path):
    # TC-F0-05
    add_launch(data.ip.state_db, "run-one")
    before = data.snapshot()
    p = Pty(cli_argv(*data.launch_args(tmp_path, run="run-one")), data.env())
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    p.send("n\n")
    rc, screen = p.finish(60)
    assert rc != 0 and "未送出" in screen and data.snapshot() == before
    p = Pty(cli_argv(*data.launch_args(tmp_path, run="run-one")), data.env(), stdin_tty=False, controlling=False)
    rc, screen = p.finish(60)
    assert rc != 0 and data.snapshot() == before


# ---- F2: the table, the results, the readers ----------------------------------------------------------------------

def test_tcf2_06_a_number_and_a_cancel_time_are_written_to_their_own_row_only(tmp_path):
    # TC-F2-06
    from abf_platform import confirm
    plat, tok, clock = setup(tmp_path)
    b1, c1, j1 = _queue_launch(plat, clock)
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % j1, json={"state": "refused", "result": {"ok": False, "message": "no"}}, headers=bearer(tok))
    b2, c2, j2 = _queue_launch(plat, clock)
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % j2, json={"state": "done", "result": {"ok": True, "slurm_job_id": 99, "run_name": "run-one"}},
                     headers=bearer(tok))
    rows = sql(plat, "SELECT id, slurm_job_id, submitted_at, cancel_requested_at, job_id FROM launches ORDER BY id")
    assert len(rows) == 2
    assert rows[0][1:4] == (None, None, None) and rows[0][4] == j1
    assert rows[1][1] == 99 and rows[1][2] == clock() and rows[1][3] is None and rows[1][4] == j2
    clock.t += 5
    cancel = {"run_name": "run-one", "slurm_job_id": 99, "run_folder": b2["run_folder"], "agent": "a1", "ce": b2["ce"]}
    cc, cj = confirm.confirm_cancel(state_db(plat), "lab-a", cancel, clock=clock)
    poll(plat, tok)
    plat.client.post("/agent/result/%d" % cj, json={"state": "done", "result": {"ok": True, "slurm_job_id": 99}}, headers=bearer(tok))
    rows = sql(plat, "SELECT cancel_requested_at FROM launches ORDER BY id")
    assert rows == [(None,), (clock(),)]


def test_tcf2_06_a_late_answer_of_an_old_job_does_not_touch_the_new_row(tmp_path):
    # TC-F2-06: two rows of one name (made by hand: the old job expired); the old job's late answer belongs to the old row
    plat, tok, clock = setup(tmp_path)
    db = state_db(plat)
    _, old_job = add_launch(db, "run-one", state="claimed", deadline="past")
    con = sqlite3.connect(str(db))
    con.execute("UPDATE jobs SET deadline_at = ?, created_at = ? WHERE id = ?", (clock() - 10, clock() - 400, old_job))
    con.commit()
    con.close()
    _, new_job = add_launch(db, "run-one", state="queued")
    r = plat.client.post("/agent/result/%d" % old_job, json={"state": "done", "result": {"ok": True, "slurm_job_id": 55}},
                         headers=bearer(tok))
    assert r.json() == {"accepted": False, "late": True}
    rows = sql(plat, "SELECT slurm_job_id, job_id FROM launches ORDER BY id")
    assert rows == [(55, old_job), (None, new_job)]


def test_tcf2_07_cancel_fetch_and_the_closing_report_find_the_newest_row(data, tmp_path, monkeypatch):
    # TC-F2-07 (a), (b), (c)
    import contextlib
    import io
    from abf_launch import cli
    from abf_platform import jobs
    db = data.ip.state_db
    add_launch(db, "run-one", folder="/data/w1/runs/OLD", agent=data.agent)
    _, jdone = add_launch(db, "run-one", slurm=99, state="done", message="ok", folder="/data/w1/runs/NEW", agent=data.agent)
    p = Pty(cli_argv("cancel", "run-one"), data.env())
    assert p.wait_for(QUESTION_CANCEL, 30), p.text()
    shown = p.text()
    assert "99" in shown and "/data/w1/runs/NEW" in shown and "OLD" not in shown
    p.send("y\n")
    p.finish(60)
    cancel_job = [r for r in data.rows("jobs") if r[3] == "cancel_run"][0]
    sent = json.loads(cancel_job[4])["bundle"]
    assert sent["slurm_job_id"] == 99 and sent["run_folder"] == "/data/w1/runs/NEW"
    jid = jobs.enqueue_fetch(db, "run-one")
    fetch = json.loads(sql_one(db, "SELECT args_json FROM jobs WHERE id = ?", (jid,)))
    assert fetch["run_folder"] == "/data/w1/runs/NEW"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli._report_launch(db, jdone, {"run_name": "run-one", "run_folder": "/data/w1/runs/NEW"})
    assert rc == 0 and "Slurm 工作編號 99" in buf.getvalue() and "/data/w1/runs/NEW" in buf.getvalue()


def test_tcf2_07_a_name_with_only_refused_rows_cannot_be_cancelled(data):
    # TC-F2-07
    add_launch(data.ip.state_db, "run-one")
    before = data.snapshot()
    p = Pty(cli_argv("cancel", "run-one"), data.env())
    rc, screen = p.finish(60)
    assert rc != 0 and "沒有 Slurm 工作編號" in screen and QUESTION_CANCEL not in screen and data.snapshot() == before


# ---- F2: the upgrade of the table ---------------------------------------------------------------------------------

def seeded_live(tmp_path):
    """A live-shaped database with several rows: submitted, cancel requested, refused, unknown; and a high sequence."""
    from abf_platform import store
    db = tmp_path / "multi" / "platform.db"
    store.connect_state(db).close()
    add_launch(db, "run-sub", slurm=11, state="done", message="ok")
    add_launch(db, "run-can", slurm=12, state="done", message="ok", cancel_at=1_800_000_123.0)
    add_launch(db, "run-ref")
    add_launch(db, "run-unk", state="expired")
    to_live_shape(db)
    return db


ORDER = {"meta": "rowid", "agents": "name"}


def test_tcf2_08_the_upgrade_keeps_every_row_and_the_sequence(tmp_path):
    # TC-F2-08
    from abf_platform import store
    db = seeded_live(tmp_path)
    before = {t: table(db, t, ORDER.get(t, "id")) for t in ("jobs", "confirmations", "agents", "compute_envs", "meta")}
    old = table(db, "launches")
    seq = sql_one(db, "SELECT seq FROM sqlite_sequence WHERE name = 'launches'")
    assert seq >= 40
    store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    cols = [r[1] for r in con.execute("PRAGMA table_info(launches)")]
    assert cols[:9] == ["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at",
                        "cancel_requested_at"] and "job_id" in cols
    new = con.execute("SELECT %s FROM launches ORDER BY id" % OLD_COLUMNS).fetchall()
    assert new == old
    for t, rows in before.items():
        assert table(db, t, ORDER.get(t, "id")) == rows, t
    # every old row got its own job
    links = dict(con.execute("SELECT run_name, job_id FROM launches"))
    assert all(links[r] is not None for r in links) and len(set(links.values())) == 4
    assert con.execute("SELECT seq FROM sqlite_sequence WHERE name = 'launches'").fetchone()[0] == seq
    cur = con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('run-sub', '/f', 'lab-a', 'a1', 1)")
    assert cur.lastrowid == seq + 1, "numbering goes on after the old maximum"
    con.rollback()
    con.close()
    digest = all_files_digest(db)
    store.connect_state(db).close()
    assert all_files_digest(db) == digest, "a second opening changes nothing"


def test_tcf2_09_a_failure_in_the_upgrade_puts_everything_back(tmp_path, monkeypatch):
    # TC-F2-09
    from abf_platform import store
    db = seeded_live(tmp_path)
    before = dump(db)

    def boom(step):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(store, "_migration_step", boom)
    with pytest.raises(RuntimeError):
        store.connect_state(db).close()
    assert dump(db) == before
    names = {r[0] for r in sqlite3.connect(str(db)).execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert not {n for n in names if n.endswith("_new")}
    monkeypatch.undo()
    store.connect_state(db).close()
    assert "job_id" in [r[1] for r in sqlite3.connect(str(db)).execute("PRAGMA table_info(launches)")]


def test_tcf2_10_a_new_database_and_an_upgraded_one_have_the_same_launches_table(tmp_path):
    # TC-F2-10
    from abf_platform import store
    fresh = tmp_path / "fresh" / "platform.db"
    store.connect_state(fresh).close()
    up = seeded_live(tmp_path)
    store.connect_state(up).close()
    shape = lambda p: [tuple(r) for r in sqlite3.connect(str(p)).execute("PRAGMA table_info(launches)")]
    assert shape(fresh) == shape(up)
    for p in (fresh, up):
        con = sqlite3.connect(str(p))
        for i in (1, 2):
            con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at) VALUES ('same', '/f', 'c', 'a', ?)", (i,))
        assert not [r for r in con.execute("PRAGMA index_list(launches)") if r[2] and
                    [i[2] for i in con.execute("PRAGMA index_info(%s)" % r[1])] == ["run_name"]]
        con.close()


def test_tcf2_11_two_confirmations_of_one_name_at_once_let_one_through(tmp_path):
    # TC-F2-11
    from abf_platform import confirm, jobs
    plat, tok, clock = setup(tmp_path)
    results = []
    gate = threading.Barrier(2)

    def go():
        gate.wait()
        try:
            confirm.confirm_launch(state_db(plat), "lab-a", bundle("run-one"), clock=clock)
            results.append("ok")
        except jobs.JobRefused:
            results.append("refused")

    ts = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["ok", "refused"], results
    assert len(sql(plat, "SELECT id FROM jobs WHERE kind = 'launch_nextflow' AND state = 'queued'")) == 1


def test_tcf2_13_a_name_used_again_leaves_one_valid_token_and_the_old_one_cannot_make_a_run(tmp_path):
    # TC-F2-13
    plat, tok, clock = setup(tmp_path)
    _queue_launch(plat, clock)
    first = poll(plat, tok).json()["job"]
    plat.client.post("/agent/result/%d" % first["id"], json={"state": "refused", "result": {"ok": False, "message": "no"}}, headers=bearer(tok))
    _queue_launch(plat, clock)
    second = poll(plat, tok).json()["job"]
    live = [r for r in tokens_rows(plat) if r[2] is None]
    assert len(live) == 1 and len(tokens_rows(plat)) == 2
    assert plat.send("POST", "/trace/create", create_body("run-one"), token=first["run_token"]).status_code == 401
    assert plat.send("POST", "/trace/create", create_body("run-one"), token=second["run_token"]).status_code == 200


# ---- out of scope -------------------------------------------------------------------------------------------------

def test_tcf0_03_the_new_tests_never_name_the_running_acceptance_setup_or_its_port():
    # TC-F0-03: the words are built from parts so that this file does not contain them
    folder, port = "abf-station" + "-test", "87" + "87"
    for p in Path(__file__).parent.glob("test_launch_followup*.py"):
        text = p.read_text(encoding="utf-8")
        assert folder not in text and port not in text, p.name
