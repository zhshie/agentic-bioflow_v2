# Nothing existing: tests of spec 009c, the pending request, the form answer and the repeated call; the rules (who may say yes, what is shown, what is queued) are ours.
"""009c: a person's yes through an MCP form or the confirmation page. Test cases are named in the comments (TC-A01 ...),
see specs/009c-human-channel/test-case.md."""
import asyncio
import copy
import inspect
import json
import re
import sqlite3
import threading
import time
import types

import pytest

from helpers import Clock, free_port, mcp_call, mcp_http_call, pkg_env, start_cli, stop_proc, tool_json, tool_text, wait_port
from human_harness import PASSWORD, World, csrf_of, form_answer, pending_id_of
from launch_harness import QUESTION_LAUNCH, Pty, cli_argv
from test_launch_cli import parts
from test_launch_platform import bundle, make_confirmation, setup, sql
from test_station_platform import state_db

REFUSED = "no human confirmation channel"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def actions():
    from abf_platform import actions as a
    return a


def prefix_off(screen_lines):
    return "\n".join(ln[2:] if ln.startswith("| ") else ln for ln in screen_lines)


# ---- US1: a pending request is not a confirmation ----------------------------------------------------------------------

def test_tca01_the_summary_shows_pipeline_samples_place_and_every_file(w, tmp_path):
    # TC-A01
    ann = w.user("ann")
    w.sheet = w.data.samplesheet(tmp_path, rows=[("alpha", "/data/storage/rawdata/alpha.fastq.gz"),
                                                  ("beta", "/data/storage/rawdata/beta.fastq.gz")])
    out = w.launch(caller=ann)
    text = out["summary"]
    for needle in ("nf-core/ampliseq", "2.18.0", "lab-a", "agent-t", "/data/w1/runs/run-one", "alpha,", "beta,",
                   "== params.yaml ==", "== nextflow.config ==", "== head.sh =="):
        assert needle in text, needle
    assert "(略)" not in text and "omitted" not in text.lower()
    assert "== samplesheet.csv（2 列資料）==" in text


def test_tca02_a06_the_summary_and_the_bundle_are_the_ones_of_the_terminal(w, tmp_path):
    # TC-A02, TC-A06: the terminal shows the same text (but for the line prefix) and hashes the same bundle
    ann = w.user("ann")
    out = w.launch(caller=ann)
    pending = w.confirmations()[0]
    # 116: the terminal names the account and reads the very samplesheet the page's caller sent (its paths are in her folder)
    mine = w.in_area(ann, {"samplesheet": str(w.sheet)})["samplesheet"]
    p = Pty(cli_argv(*w.data.launch_args(tmp_path, extra=("--user", "ann", "--samplesheet", mine))), w.data.env())
    assert p.wait_for(QUESTION_LAUNCH, 30), p.text()
    lines, _ = parts(p.text(), QUESTION_LAUNCH)
    assert "\n".join(lines) == out["summary"]
    p.send("y\n")
    p.finish(60)
    terminal_row = [r for r in w.confirmations() if r["id"] != pending["id"]][0]
    # 116b: the page's bundle also carries `upload_paths` (the real paths of the caller's own files); without that record it is the terminal's bundle, byte for byte
    from abf_platform import common
    page_bundle = json.loads(pending["bundle_json"])
    assert "upload_paths" in page_bundle
    del page_bundle["upload_paths"]
    assert terminal_row["sha256"] == common.bundle_sha256(page_bundle)


def test_tca03_nothing_is_queued_while_nobody_has_said_yes(w):
    # TC-A03
    out = w.launch(caller=w.user("ann"))
    assert out["sent"] is False and out["ok"] is True and "還沒送出" in out["message"]
    assert w.counts() == (0, 1, 0)
    row = w.confirmations()[0]
    assert row["state"] == "pending" and row["kind"] == "launch" and row["id"] == out["id"]


def test_tca04_a11_a_pending_or_void_row_cannot_queue_a_job(tmp_path):
    # TC-A04, TC-A11
    from abf_platform import jobs
    plat, tok, clock = setup(tmp_path)
    db = state_db(plat)
    b = bundle()
    ids = {}
    for state in ("pending", "void", "confirmed"):
        cid = make_confirmation(db, "launch", b)
        con = sqlite3.connect(str(db))
        con.execute("UPDATE confirmations SET state = ? WHERE id = ?", (state, cid))
        con.commit()
        con.close()
        ids[state] = cid
    for state in ("pending", "void"):
        with pytest.raises(jobs.JobRefused):
            jobs.enqueue_launch(db, "lab-a", b, confirmation_id=ids[state], clock=clock)
    assert sql(plat, "SELECT COUNT(*) FROM jobs WHERE kind = 'launch_nextflow'") == [(0,)]
    assert jobs.enqueue_launch(db, "lab-a", b, confirmation_id=ids["confirmed"], clock=clock)
    # the old checks are all still there: wrong kind, another content, a spent row
    other = make_confirmation(db, "cancel", b)
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_launch(db, "lab-a", b, confirmation_id=other, clock=clock)


def test_tca05_a_cancel_is_a_pending_request_too_and_the_tool_says_destructive(w):
    # TC-A05
    ann = w.user("ann")
    w.hand_over(by=ann)
    tools, outs = w.mcp([("cancel", {"run_name": "run-one"})], caller=ann)
    out = tool_json(outs[0])
    assert out["sent"] is False and "還沒送出" in out["message"] and "Slurm" in out["summary"]
    assert w.jobs() == [] and w.confirmations()[0]["kind"] == "cancel" and w.confirmations()[0]["state"] == "pending"
    cancel = [t for t in tools if t.name == "cancel"][0]
    assert cancel.annotations.read_only_hint is False and cancel.annotations.destructive_hint is True


def test_tca07_a_launch_that_cannot_be_built_leaves_no_request(w, tmp_path):
    # TC-A07
    ann = w.user("ann")
    rc, out = w.ip.create_slurm("lab-b", agent="agent-nofacts", head_job_options="-A X -c 4", nextflow_config="x = 1\n")
    assert rc == 0, out
    from test_station_envs import make_available
    make_available(w.ip, "lab-b", agent="agent-nofacts")
    w.hand_over("taken-name")
    cases = [dict(ce_name="no-such-env"), dict(ce_name="lab-b"), dict(run="taken-name"),
             dict(samplesheet=str(tmp_path / "missing.csv"))]
    for over in cases:
        out = w.launch(caller=ann, **over)
        assert out["ok"] is False and out["sent"] is False and out["message"], over
    assert w.confirmations() == [] and w.jobs() == []


def test_tca15_control_characters_are_refused_before_anything_is_made(w, tmp_path):
    # TC-A15
    sheet = w.data.samplesheet(tmp_path, rows=[("s01", "/data/storage/rawdata/\x1b[2Js01.fastq.gz")], name="bad.csv")
    out = w.launch(caller=w.user("ann"), samplesheet=str(sheet))
    assert out["ok"] is False and w.confirmations() == []
    # a control character in a param is not refused by the bundle (as at the terminal, TC-006): it is shown spelled out, never raw
    out = w.launch(caller=w.user("bob"), params={"primer": "A\x07G\x1b[2J"})
    if out["ok"] is False:
        assert w.confirmations() == []
    else:
        assert "\x07" not in out["summary"] and "\x1b" not in out["summary"] and "\\x07" in out["summary"]
        assert "\x07" not in w.confirmations()[0]["screen_text"]


def test_tca08_exactly_eleven_tools_and_none_of_them_can_say_yes(w):
    # TC-A08. 009e: was exactly eight; resume and relaunch are added, asked like launch and cancel (their fields are checked below too)
    tools, _ = w.mcp([])
    names = sorted(t.name for t in tools)
    assert names == ["cancel", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation", "launch", "list_agents", "list_compute_envs", "list_pipelines", "list_runs",
                     "list_site_files", "list_used_pipelines", "my_usage", "read_run_file", "read_task_log", "relaunch", "resume", "run_outputs"]
    assert not [n for n in names if re.search(r"approve|confirm|passwd|login", n)]
    by = {t.name: t for t in tools}
    assert by["launch"].annotations.read_only_hint is False
    assert by["cancel"].annotations.read_only_hint is False and by["cancel"].annotations.destructive_hint is True
    for name in ("launch", "cancel", "resume", "relaunch"):
        props = set(by[name].input_schema.get("properties", {}))
        assert not (props & {"yes", "confirm", "confirmed", "approve", "approved", "送出", "ok", "agree", "force"}), props


def test_tca09_a16_the_pending_row_holds_the_whole_bundle_and_nothing_else_is_shown(w):
    # TC-A09, TC-A16
    from abf_platform import common
    from abf_launch import build
    ann = w.user("ann")
    t0 = time.time()
    out = w.launch(caller=ann)
    row = w.confirmations()[0]
    assert row["caller_user_id"] == ann.user_id and row["ce_name"] == "lab-a" and row["channel"] is None
    assert row["confirmed_at"] is None and row["used_at"] is None
    assert abs(row["expires_at"] - row["created_at"] - 600) < 0.001 and t0 - 5 < row["created_at"] < time.time() + 5
    b = json.loads(row["bundle_json"])
    assert common.bundle_sha256(b) == row["sha256"]
    assert prefix_off(build.launch_screen(b, "lab-a")) == out["summary"] == row["screen_text"]


def test_tca10_a_platform_db_of_009d_is_upgraded_in_place(tmp_path):
    # TC-A10
    from abf_platform import jobs, store
    plat, tok, clock = setup(tmp_path)
    db = state_db(plat)
    b = bundle()
    unused = make_confirmation(db, "launch", b)
    used = make_confirmation(db, "launch", bundle("run-two"), used=time.time())
    con = sqlite3.connect(str(db))
    con.execute("PRAGMA foreign_keys = OFF")
    con.executescript("""
        BEGIN;
        CREATE TABLE confirmations_old (id TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
            kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel')), created_at REAL NOT NULL, used_at REAL, caller_user_id INTEGER);
        INSERT INTO confirmations_old SELECT id, sha256, kind, created_at, used_at, caller_user_id FROM confirmations;
        DROP TABLE confirmations;
        ALTER TABLE confirmations_old RENAME TO confirmations;
        COMMIT;""")
    assert [r[1] for r in con.execute("PRAGMA table_info(confirmations)")] == [
        "id", "sha256", "kind", "created_at", "used_at", "caller_user_id"]
    con.close()
    store.connect_state(db).close()
    rows = {r[0]: r for r in sql(plat, "SELECT id, state, channel, confirmed_at FROM confirmations")}
    assert rows[unused][1] == "confirmed" and rows[unused][2] == "TERMINAL" and rows[unused][3] is not None
    assert rows[used][1] == "confirmed" and rows[used][2] == "TERMINAL"
    cols = {r[1] for r in sqlite3.connect(str(db)).execute("PRAGMA table_info(confirmations)")}
    assert {"state", "channel", "confirmed_at", "expires_at", "ce_name", "bundle_json", "screen_text", "void_reason"} <= cols
    assert jobs.enqueue_launch(db, "lab-a", b, confirmation_id=unused, clock=clock)


def _http_server(w):
    port = free_port()
    proc = start_cli(["mcp", "--http", "--port", str(port)], w.data.env(), w.tmp / "mcp.log")
    wait_port(port, proc=proc)
    return port, proc


def test_tca12_a13_over_http_a_call_needs_a_token_and_the_token_only_names_the_caller(w):
    # TC-A12, TC-A13
    import httpx
    from abf_platform import store
    ann = w.user("ann")
    pat = store.create_token(w.ip.tokens, kind="pat", user_id=ann.user_id)
    port, proc = _http_server(w)
    try:
        r = httpx.post("http://127.0.0.1:%d/mcp" % port, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "launch", "arguments": w.choices()}},
                       headers={"Accept": "application/json, text/event-stream"}, timeout=10)
        assert r.status_code == 401 and w.confirmations() == []
        _, outs = mcp_http_call("http://127.0.0.1:%d/mcp" % port, [("launch", w.in_area(ann, w.choices()))], token=pat)
    finally:
        stop_proc(proc)
    out = tool_json(outs[0])
    assert out["sent"] is False and w.jobs() == []
    row = w.confirmations()[0]
    assert row["caller_user_id"] == ann.user_id and row["state"] == "pending"


def test_tca14_over_stdio_without_a_form_the_launch_is_refused(w):
    # TC-A14
    _, outs = mcp_call(w.data.env(), [("launch", w.choices())])
    out = tool_json(outs[0])
    assert out["ok"] is False and "終端機" in out["message"] and "HTTP" in out["message"]
    assert w.confirmations() == [] and w.jobs() == []


# ---- US3: the form ------------------------------------------------------------------------------------------------------------

def test_tc01_c13_a_true_in_the_form_queues_exactly_one_launch(w):
    # TC-C01, TC-C13
    ann = w.user("ann")
    out = w.launch(caller=ann, answer=form_answer())
    assert out["sent"] is True and out["job_id"]
    assert len(w.jobs("launch_nextflow")) == 1 and w.jobs()[0]["id"] == out["job_id"]
    row = w.confirmations()[0]
    assert row["state"] == "confirmed" and row["channel"] == "ELICITED" and row["confirmed_at"] and row["caller_user_id"] == ann.user_id


def test_tcc13_over_stdio_a_form_still_works_and_records_no_caller(w):
    # TC-C13 (local stdio has no caller)
    out = w.launch(caller=None, answer=form_answer())
    assert out["sent"] is True
    assert w.confirmations()[0]["channel"] == "ELICITED" and w.confirmations()[0]["caller_user_id"] is None


def test_tcc06_the_form_carries_the_summary_and_one_boolean(w):
    # TC-C06
    seen = []
    out = w.launch(caller=w.user("ann"), answer=form_answer("decline", seen=seen))
    assert len(seen) == 1
    row = w.confirmations()[0]
    assert seen[0].message == row["screen_text"]
    props = seen[0].requested_schema["properties"]
    assert list(props) == ["送出"] and props["送出"]["type"] == "boolean"


@pytest.mark.parametrize("kwargs", [dict(action="accept", content={"送出": False}), dict(action="decline"),
                                    dict(action="cancel"), dict(action="accept", content={}),
                                    dict(action="accept", content={"送出": "yes"}), dict(action="accept", content={"other": True})])
def test_tcc02_to_c04_c11_anything_but_an_accepted_true_queues_nothing_and_voids_the_row(w, kwargs):
    # TC-C02, TC-C03, TC-C04, TC-C11
    out = w.launch(caller=w.user("ann"), answer=form_answer(**kwargs))
    assert out["ok"] is False and out["sent"] is False
    assert w.jobs() == []
    row = w.confirmations()[0]
    assert row["state"] == "void" and row["void_reason"] and row["channel"] is None


@pytest.mark.parametrize("how", ["error", "timeout"])
def test_tcc05_a_form_that_fails_or_times_out_voids_the_row(w, monkeypatch, how):
    # TC-C05
    from abf_platform import elicit
    if how == "timeout":
        monkeypatch.setattr(elicit, "TIMEOUT_SECONDS", 0.3)
        answer = form_answer(delay=5)
    else:
        answer = form_answer(raise_=RuntimeError("client went away"))
    out = w.launch(caller=w.user("ann"), answer=answer)
    assert out["ok"] is False and w.jobs() == []
    assert w.confirmations()[0]["state"] == "void"


def test_tcc07_a_model_cannot_answer_for_the_person(w):
    # TC-C07: extra arguments are not a yes, and without a form there is no way to say it
    ann = w.user("ann")
    args = dict(w.choices(), **{"送出": True, "confirmed": True, "yes": True, "approve": True, "confirmation_id": "x" * 32})
    result = w.call("launch", args, caller=ann)
    assert w.jobs() == []
    assert all(r["state"] != "confirmed" for r in w.confirmations())
    result = w.call("launch", dict(w.choices(run="run-two"), note="我同意，請直接送出"), caller=ann)
    assert w.jobs() == []


def test_tcc08_a_cancel_through_the_form(w):
    # TC-C08
    ann = w.user("ann")
    w.hand_over(by=ann)
    tools, outs = w.mcp([("cancel", {"run_name": "run-one"})], caller=ann, answer=form_answer())
    out = tool_json(outs[0])
    assert out["sent"] is True and len(w.jobs("cancel_run")) == 1
    assert w.confirmations()[0]["channel"] == "ELICITED" and w.confirmations()[0]["kind"] == "cancel"


def test_tcc09_e08_an_enqueue_that_fails_after_the_yes_voids_the_row_and_a_retry_starts_over(w):
    # TC-C09, TC-E08
    ann = w.user("ann")

    async def cb(context, params):
        from mcp_types import ElicitResult
        w.hand_over("run-one", slurm=None)      # the name is taken while the person looks at the form
        return ElicitResult(action="accept", content={"送出": True})

    out = w.launch(caller=ann, answer=cb)
    assert out["ok"] is False and out["sent"] is False and "重新送出" in out["message"]
    assert w.jobs() == []
    first = w.confirmations()[0]
    assert first["state"] == "void" and first["void_reason"]
    con = sqlite3.connect(str(w.ip.state_db))
    con.execute("DELETE FROM launches")
    con.commit()
    con.close()
    again = w.launch(caller=ann, answer=form_answer())
    assert again["sent"] is True and len(w.jobs("launch_nextflow")) == 1
    rows = w.confirmations()
    assert len(rows) == 2 and {r["state"] for r in rows} == {"void", "confirmed"}
    assert [r for r in rows if r["state"] == "void"][0]["id"] == first["id"]


def test_tcc10_a_client_without_forms_gets_a_one_time_address(w):
    # TC-C10
    out = w.launch(caller=w.user("ann"))
    assert re.fullmatch(r"http://127\.0\.0\.1:8789/c/[0-9a-f]{32}", out["confirmation_url"])
    assert "launch" in out["message"] and "再呼叫" in out["message"] and out["sent"] is False and w.jobs() == []


# ---- US5: once, and not for another content -----------------------------------------------------------------------------------

def _approve_on_the_page(w, ann_name, request_id, client=None):
    client = client or w.web()
    assert w.login(client, ann_name).status_code in (200, 303)
    page = client.get("/c/" + request_id)
    assert page.status_code == 200, page.text
    return client, client.post("/c/" + request_id, data={"csrf": csrf_of(page.text)})


def test_tce01_e02_the_repeated_call_after_the_page_returns_the_same_job(w):
    # TC-E01, TC-E02
    ann = w.user("ann")
    first = w.launch(caller=ann)
    _approve_on_the_page(w, "ann", first["id"])
    assert len(w.jobs("launch_nextflow")) == 1
    job_id = w.jobs()[0]["id"]
    for _ in range(2):
        again = w.launch(caller=ann)
        assert again["sent"] is True and again["job_id"] == job_id
    assert len(w.jobs("launch_nextflow")) == 1 and len(w.confirmations()) == 1


def test_tce03_waiting_is_not_a_job_and_the_same_request_is_reused(w):
    # TC-E03
    ann = w.user("ann")
    ids = {w.launch(caller=ann)["id"] for _ in range(3)}
    assert len(ids) == 1 and len(w.confirmations()) == 1 and w.jobs() == []
    assert w.launch(caller=ann)["sent"] is False


def test_tce04_a_changed_content_gets_a_new_request_and_never_the_old_yes(w):
    # TC-E04. The same run name with another version is refused outright, because the first job holds the name (no job either way);
    # another name and another version is a new content and gets a new pending request. The old yes is used for neither.
    ann = w.user("ann")
    first = w.launch(caller=ann)
    _approve_on_the_page(w, "ann", first["id"])
    same_name = w.launch(caller=ann, revision="2.17.0")
    assert same_name["ok"] is False and same_name["sent"] is False and "已用過" in same_name["message"]
    assert len(w.jobs("launch_nextflow")) == 1 and len(w.confirmations()) == 1
    changed = w.launch(caller=ann, revision="2.17.0", run="run-two")
    assert changed["sent"] is False and changed["id"] != first["id"]
    assert len(w.jobs("launch_nextflow")) == 1 and len(w.confirmations()) == 2
    assert [r["state"] for r in w.confirmations() if r["id"] == changed["id"]] == ["pending"]


def test_tce05_another_person_cannot_use_my_yes(w):
    # TC-E05
    ann, bob = w.user("ann"), w.user("bob")
    mine = w.launch(caller=ann)
    theirs = w.launch(caller=bob)                       # only pending so far: bob has his own request
    assert theirs["sent"] is False and theirs["id"] != mine["id"]
    _approve_on_the_page(w, "ann", mine["id"])
    assert len(w.jobs("launch_nextflow")) == 1
    after = w.launch(caller=bob)                        # ann's job exists now: bob gets no job out of ann's yes
    assert after.get("job_id") != w.jobs()[0]["id"] and after["sent"] is False
    assert len(w.jobs("launch_nextflow")) == 1


def test_tce06_an_approved_request_older_than_ten_minutes_is_not_used_again(w):
    # TC-E06
    ann = w.user("ann")
    first = w.launch(caller=ann)
    _approve_on_the_page(w, "ann", first["id"])
    a = actions()
    b = json.loads(w.confirmations()[0]["bundle_json"])
    now = w.confirmations()[0]["created_at"]
    assert a.find_approved(w.ip.state_db, "launch", b, caller=ann, clock=lambda: now + 5)["job_id"] == w.jobs()[0]["id"]
    assert a.find_approved(w.ip.state_db, "launch", b, caller=ann, clock=lambda: now + 601) is None
    out = asyncio.run(a.request_launch(w.ip.state_db, caller=ann, clock=lambda: now + 601, **w.in_area(ann, w.choices())))
    assert out["sent"] is False and len(w.jobs("launch_nextflow")) == 1


def test_tce07_a_spent_confirmation_cannot_start_a_second_job(tmp_path):
    # TC-E07
    from abf_platform import jobs
    plat, tok, clock = setup(tmp_path)
    db = state_db(plat)
    b = bundle()
    cid = make_confirmation(db, "launch", b)
    jobs.enqueue_launch(db, "lab-a", b, confirmation_id=cid, clock=clock)
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_launch(db, "lab-a", b, confirmation_id=cid, clock=clock)
    spent = make_confirmation(db, "launch", b, used=time.time())
    with pytest.raises(jobs.JobRefused):
        jobs.enqueue_launch(db, "lab-a", b, confirmation_id=spent, clock=clock)
    assert sql(plat, "SELECT COUNT(*) FROM jobs WHERE kind = 'launch_nextflow'") == [(1,)]


def test_tce09_two_posts_at_once_queue_one_job(w):
    # TC-E09
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c1, c2 = w.web(), w.web()
    # both clients share the app through the same database; each logs in on its own
    for c in (c1, c2):
        assert w.login(c, "ann").status_code in (200, 303)
    tokens = [csrf_of(c.get("/c/" + rid).text) for c in (c1, c2)]
    results = []

    def post(c, t):
        results.append(c.post("/c/" + rid, data={"csrf": t}))

    threads = [threading.Thread(target=post, args=(c, t)) for c, t in zip((c1, c2), tokens)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(w.jobs("launch_nextflow")) == 1
    assert all("已送出" in r.text for r in results), [r.text for r in results]


def test_tce10_find_approved_needs_the_same_person_hash_state_and_time(w):
    # TC-E10
    a = actions()
    ann, bob = w.user("ann"), w.user("bob")
    first = w.launch(caller=ann)
    _approve_on_the_page(w, "ann", first["id"])
    row = w.confirmations()[0]
    b = json.loads(row["bundle_json"])
    t = row["created_at"] + 1
    db = w.ip.state_db
    assert a.find_approved(db, "launch", b, caller=ann, clock=lambda: t)["id"] == row["id"]
    assert a.find_approved(db, "launch", b, caller=bob, clock=lambda: t) is None
    assert a.find_approved(db, "launch", b, caller=None, clock=lambda: t) is None
    assert a.find_approved(db, "cancel", b, caller=ann, clock=lambda: t) is None
    assert a.find_approved(db, "launch", dict(b, revision="x"), caller=ann, clock=lambda: t) is None
    assert a.find_approved(db, "launch", b, caller=ann, clock=lambda: row["created_at"] + 601) is None
    con = sqlite3.connect(str(db))
    con.execute("UPDATE confirmations SET used_at = ?", (t,))
    con.commit()
    con.close()
    assert a.find_approved(db, "launch", b, caller=ann, clock=lambda: t) is None
    con = sqlite3.connect(str(db))
    con.execute("UPDATE confirmations SET used_at = NULL, state = 'void'")
    con.commit()
    con.close()
    assert a.find_approved(db, "launch", b, caller=ann, clock=lambda: t) is None


def test_tce12_a_void_request_cannot_be_brought_back(w):
    # TC-E12
    a = actions()
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    a.void_request(w.ip.state_db, rid, "test")
    client = w.web()
    w.login(client, "ann")
    page = client.get("/c/" + rid)
    r = client.post("/c/" + rid, data={"csrf": csrf_of(page.text) or "x"})
    assert r.status_code >= 400 or "作廢" in r.text
    for channel in (a.PAGE, a.ELICITED):
        with pytest.raises(a.NotApproved) as e:
            a.approve(w.ip.state_db, rid, confirmed_by=channel, caller=ann)
        assert e.value.status == "void"
    assert w.jobs() == [] and w.confirmations()[0]["state"] == "void"


# ---- US6: the terminal path and the channels ------------------------------------------------------------------------------------

@pytest.mark.parametrize("make", [lambda a: "ELICITED", lambda a: "PAGE", lambda a: "TERMINAL", lambda a: True, lambda a: None,
                                  lambda a: copy.copy(a.ELICITED), lambda a: copy.deepcopy(a.PAGE), lambda a: object(),
                                  lambda a: types.SimpleNamespace(name="PAGE"), lambda a: str(a.PAGE), lambda a: type(a.PAGE)("x")])
def test_tcf07_only_the_three_singletons_pass(tmp_path, make):
    # TC-F07
    from abf_platform import jobs
    a = actions()
    plat, _, clock = setup(tmp_path)
    before = sql(plat, "SELECT COUNT(*) FROM confirmations")
    with pytest.raises(jobs.JobRefused, match=REFUSED):
        a.launch(state_db(plat), "lab-a", bundle("run-one"), confirmed_by=make(a), clock=clock)
    with pytest.raises((jobs.JobRefused, TypeError)):
        a.cancel(state_db(plat), "lab-a", {}, confirmed_by=make(a), clock=clock)
    assert sql(plat, "SELECT COUNT(*) FROM confirmations") == before


def test_tcf07_the_three_singletons_pass(tmp_path):
    # TC-F07
    a = actions()
    plat, _, clock = setup(tmp_path)
    for n, (name, ch) in enumerate((("TERMINAL", a.TERMINAL), ("ELICITED", a.ELICITED), ("PAGE", a.PAGE))):
        cid, jid = a.launch(state_db(plat), "lab-a", bundle("run-%d" % n), confirmed_by=ch, clock=clock)
        assert sql(plat, "SELECT channel, state FROM confirmations WHERE id = ?", (cid,)) == [(name, "confirmed")]


def test_tcf08_the_channels_are_three_different_objects_and_only_the_cli_uses_terminal():
    # TC-F08 (the scan of test_tcc04 does the same for launch, cancel and TERMINAL everywhere else)
    from abf_platform import actions as a
    from helpers import PLATFORM_DIR
    from test_actions_layer import action_refs, source_files
    assert len({id(a.TERMINAL), id(a.ELICITED), id(a.PAGE)}) == 3
    users = {rel for p, rel in source_files() if "TERMINAL" in " ".join(action_refs(p.read_text(encoding="utf-8"), rel))}
    assert users == {"abf_launch/cli.py", "abf_platform/actions/__init__.py"}, users
    web = (PLATFORM_DIR / "abf_platform" / "web.py").read_text(encoding="utf-8")
    assert "actions.PAGE" in web and "ELICITED" not in web and "TERMINAL" not in web
    mcp = (PLATFORM_DIR / "abf_platform" / "mcp_server.py").read_text(encoding="utf-8")
    assert not re.search(r"PAGE|ELICITED|TERMINAL", mcp)


def test_tcf09_the_signatures_of_launch_and_cancel_did_not_change():
    # TC-F09
    a = actions()
    for fn in (a.launch, a.cancel):
        params = inspect.signature(fn).parameters
        assert list(params) == ["state_path", "ce_name", "bundle", "confirmed_by", "clock", "deadline_seconds", "offline_after",
                                "caller"]
        assert params["confirmed_by"].kind is inspect.Parameter.KEYWORD_ONLY
        assert params["clock"].kind is inspect.Parameter.KEYWORD_ONLY


# ---- the shape of the tool bodies -------------------------------------------------------------------------------------------------

def test_tch06_without_any_client_rule_nothing_is_queued(w):
    # TC-H06: the gate is the platform, not a permission rule of the client
    for _ in range(3):
        w.launch(caller=w.user("u%d" % _))
    w.hand_over()
    w.call("cancel", {"run_name": "run-one"}, caller=w.user("zed"))
    assert w.jobs() == []


def test_tch09_nothing_reaches_the_queue_through_the_tools_without_a_person(w):
    # TC-H09 (a)
    ann = w.user("ann")
    w.hand_over()
    variants = [dict(), dict(revision="2.17.0"), dict(run="run-two"), dict(params={"depth": 9})]
    for over in variants:
        for caller in (ann, None):
            w.launch(caller=caller, **over)
            w.call("cancel", {"run_name": "run-one"}, caller=caller)
    assert w.jobs() == []


def test_tcf10_f11_the_ban_on_session_and_password_names_has_exactly_one_exception(tmp_path):
    # TC-F10, TC-F11: the exception is the exact triples; an extra column in any database still turns the scan red
    from helpers import Platform
    from test_station_envs import EXEMPT, banned_schema_words
    plat = Platform(tmp_path / "p")
    state = plat.dir / "platform.db"
    from abf_platform import store
    store.connect_state(state).close()
    store.connect_tokens(plat.tokens).close()
    store.connect_index(plat.index).close()
    dbs = {"index.db": plat.index, "tokens.db": plat.tokens, "platform.db": state}
    assert {"web_sessions"} <= {r[0] for r in sqlite3.connect(str(plat.tokens)).execute("SELECT name FROM sqlite_master")}
    assert EXEMPT == {("index.db", "runs", "session_id"), ("tokens.db", "users", "password_hash"),
                      ("tokens.db", "web_sessions", "id_hash"), ("tokens.db", "web_sessions", "user_id"),
                      ("tokens.db", "web_sessions", "created_at"), ("tokens.db", "web_sessions", "expires_at")}
    for name, path in dbs.items():
        assert banned_schema_words(path) == [], name
    cases = [("tokens.db", "users", "role"), ("platform.db", "agents", "cookie"), ("index.db", "runs", "session_id2"),
             ("tokens.db", "web_sessions", "session_token"), ("platform.db", "meta", "password_hash"),
             ("tokens.db", "tokens", "session_id")]
    for name, table, column in cases:
        con = sqlite3.connect(str(dbs[name]))
        con.execute("ALTER TABLE %s ADD COLUMN %s TEXT" % (table, column))
        con.commit()
        assert banned_schema_words(dbs[name]), (name, table, column)
        con.close()
