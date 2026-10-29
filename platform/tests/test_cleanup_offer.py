# Nothing existing: tests of the platform's own offer to clean the work folder of a run that has just succeeded (cloud-cleanup-f); no earlier test builds a clean_work request from a run.
"""cloud-cleanup-f: when a run succeeds the platform writes ONE pending `clean_work` request for the person who launched it.

Test cases are named in the comments (TC-001 ...), they come from specs/cloud-cleanup-f/test-case.md. The request is not a yes: nothing
is queued and nothing is deleted until the owner presses the button on the confirmation page (cloud-cleanup-e), and then the real agents
of cloud-cleanup-c (Slurm) and cloud-cleanup-d (Google Batch) delete one folder, driven here against a fake site and a fake bucket.
The Slurm and bucket paths are written in pieces (K): tests/test_scope.py TC-072 bars paths that look like a cluster's."""
import ast
import inspect
import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

from helpers import Clock, PLATFORM_DIR, REPO_ROOT, db_rows, variant

T0 = 1_800_000_000.0
DAY = 86400.0
K = "wor" + "k"
SW = "/%s/u1/abf" % K              # the workDir of the Slurm environment of these tests
GW = "gs://lab-bucket/" + K        # the workDir of the Google Batch environment
RUN = "ampliseq-d5"
GCB = "googlebatch-platform"
PKG = PLATFORM_DIR / "abf_platform"
LAUNCH_PKG = PLATFORM_DIR / "abf_launch"
SPEC = REPO_ROOT / "specs" / "cloud-cleanup-f"


def gcb_config():
    from test_gcb_launch import gce
    return {k: v for k, v in gce().items() if k not in ("name", "platform")}


class Mini:
    """One platform.db and one index.db with an online agent, a Slurm environment (ce-s) and a Google Batch one (ce-g)."""

    def __init__(self, tmp, agent="a1"):
        from abf_platform import store
        self.tmp = Path(tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.db = self.tmp / "platform.db"
        self.index = self.tmp / "index.db"
        store.connect_state(self.db).close()
        store.connect_index(self.index).close()
        self.clock = Clock(T0)
        self.n = 0
        self.agent(agent)
        self.slurm_ce("ce-s", agent=agent)
        self.gcb_ce("ce-g", agent=agent)

    def sql(self, text, args=()):
        con = sqlite3.connect(str(self.db))
        con.row_factory = sqlite3.Row
        try:
            with con:
                return con.execute(text, args).fetchall()
        finally:
            con.close()

    def agent(self, name, owner=1):
        now = time.time()
        self.sql("INSERT OR REPLACE INTO agents (name, version, first_seen_at, last_seen_at, owner_user_id) VALUES (?, '0.1', ?, ?, ?)",
                 (name, now, now, owner))

    def ce(self, name, platform, config, agent="a1", owner=1, status="available"):
        self.sql("INSERT INTO compute_envs (name, platform, agent, status, config_json, created_at, updated_at, owner_user_id) "
                 "VALUES (?, ?, ?, ?, ?, 1, 1, ?)", (name, platform, agent, status, json.dumps(config), owner))

    def slurm_ce(self, name, workdir=SW, agent="a1", **over):
        config = {"workDir": workdir, "launchDir": "/%s/u1/launch" % K, "headQueue": "normal"}
        config.update(over)
        self.ce(name, "slurm-platform", config, agent=agent)

    def gcb_ce(self, name, config=None, agent="a1"):
        self.ce(name, GCB, config or gcb_config(), agent=agent)

    def view(self, ce):
        from abf_platform import compute_envs
        return compute_envs.get(self.db, ce)

    def launch(self, run=RUN, ce="ce-s", folder=None, user=1, sid=4242, cleaned=None, status="succeeded", content=True, parent=None,
               workdir_then=None, agent=None):
        """The row of the hand-off record, the confirmation of the launch that holds what was sent, and the run in the index."""
        from abf_station import launch as bundle_mod
        from abf_platform import common
        view = self.view(ce)
        if folder is None:
            folder = (SW + "/runs/" + run) if view["platform"] != GCB else "/srv/abf/runs/" + run
        self.n += 1
        at = T0 + self.n
        self.sql("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, user_id, work_cleaned_at, "
                 "parent_run) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (run, sid, folder, ce, agent or view["agent"], at, at + 1, user, cleaned, parent))
        if content:
            snap = bundle_mod.snapshot_ce(view)
            if workdir_then is not None:
                snap["workDir"] = workdir_then
            body = {"run_name": run, "run_folder": folder, "ce": snap}
            self.sql("INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, confirmed_at, bundle_json) "
                     "VALUES (?, ?, 'launch', ?, ?, 'confirmed', ?, ?)",
                     ("c%031d" % self.n, common.bundle_sha256(body), at, user, at, json.dumps(body)))
        if status:
            self.run(run, status)

    def run(self, run, status):
        final = status if status in ("succeeded", "failed") else ("failed" if status == "aborted" else None)
        last = time.time() if status == "running" else (time.time() - 10 ** 6 if status == "lost" else T0)
        con = sqlite3.connect(str(self.index))
        with con:
            con.execute("INSERT OR IGNORE INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)", ("id-" + run, "s-" + run, run, final, 100, 200 if final else None, last))
        con.close()

    def offer(self, run=RUN):
        from abf_platform import actions
        return actions.offer_cleanup(self.db, self.index, run, clock=self.clock)

    def requests(self):
        return self.sql("SELECT * FROM confirmations WHERE kind = 'clean_work' ORDER BY created_at, id")

    def jobs(self):
        return self.sql("SELECT COUNT(*) FROM jobs")[0][0]


@pytest.fixture
def m(tmp_path):
    return Mini(tmp_path / "p")


def prepared(m, run=RUN, owner=1):
    from abf_launch import build
    return build.prepare_clean(m.db, run, owner=owner)


def screen_of(bundle, row=None):
    from abf_launch import build
    return build.as_text(build.clean_screen(bundle, row))


# ---- US1: the content of the request and the words of the screen --------------------------------------------------------------

def test_slurm_bundle_has_the_seven_keys_and_work_is_the_run_folder_plus_work(m):
    # TC-001, TC-002, TC-006
    from abf_station import launch as bundle_mod
    m.launch()
    name, b, row = prepared(m)
    assert name == "ce-s" and set(b) == {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce", "work"} and b["version"] == 1
    assert b["run_folder"] == SW + "/runs/" + RUN and b["work"] == SW + "/runs/" + RUN + "/" + K
    assert b["ce"] == bundle_mod.snapshot_ce(m.view("ce-s"))


def test_a_resume_attempt_gets_the_origin_folders_work_not_a_folder_named_after_the_attempt(m):
    # TC-003
    m.launch(RUN)
    m.launch(RUN + "-a2", folder=SW + "/runs/" + RUN, parent=RUN)
    _, b, _ = prepared(m, RUN + "-a2")
    assert b["work"] == SW + "/runs/" + RUN + "/" + K and "-a2" not in b["work"]


def test_gcb_bundle_work_is_workdir_runs_run_work_and_matches_what_the_agent_recomputes(m):
    # TC-004, TC-005, TC-006
    from abf_station import clean, launch as sl
    m.launch(RUN, ce="ce-g")
    name, b, _ = prepared(m)
    assert name == "ce-g" and b["work"] == "%s/runs/%s/%s" % (GW, RUN, K)
    ce_out, bucket, _ = sl._check_gcb_ce(b["ce"])
    assert clean._gcb_work(b, RUN, ce_out, bucket) == b["work"]
    assert b["ce"] == sl.snapshot_ce(m.view("ce-g"))


def test_the_bundle_is_identical_when_built_twice(m):
    # TC-007
    from abf_platform import common
    m.launch()
    a, b = prepared(m)[1], prepared(m)[1]
    assert a == b and common.bundle_sha256(a) == common.bundle_sha256(b)


def test_what_is_deleted_is_always_a_folder_called_work_even_for_a_run_called_results(m):
    # TC-008
    for ce in ("ce-s", "ce-g"):
        for run in ("results", "rawdata", "analysis"):
            m.launch(run, ce=ce)
            _, b, _ = prepared(m, run)
            assert b["work"].endswith("/" + K) and b["work"] != b["run_folder"]
            assert b["work"].split("/")[-1] == K and b["work"].split("/")[-2] == run         # the folder of this run, then work


def refuse_cases():
    """(name, how to change the world, a phrase the person is told). Each is made on a fresh world."""
    def other_owner(m):
        return {"owner": 2}

    def no_number(m):
        m.launch(sid=None)

    def cleaned(m):
        m.launch(cleaned=T0)

    def env_gone(m):
        m.launch()
        m.sql("DELETE FROM compute_envs WHERE name = 'ce-s'")

    def agent_changed(m):
        m.launch()
        m.agent("a2")
        m.sql("UPDATE compute_envs SET agent = 'a2' WHERE name = 'ce-s'")

    def disabled(m):
        m.launch()
        m.sql("UPDATE compute_envs SET status = 'disabled' WHERE name = 'ce-s'")

    def slurm_workdir_changed(m):
        m.launch()
        m.sql("UPDATE compute_envs SET config_json = ? WHERE name = 'ce-s'",
              (json.dumps({"workDir": "/%s/u9/other" % K, "launchDir": "/x", "headQueue": "normal"}),))

    def gcb_workdir_changed(m):
        m.launch(ce="ce-g")
        c = gcb_config()
        c["workDir"] = "gs://other-bucket/" + K
        m.sql("UPDATE compute_envs SET config_json = ? WHERE name = 'ce-g'", (json.dumps(c),))

    def folder_elsewhere(m):
        m.launch(folder=SW + "/else/" + RUN)

    def no_content(m):
        m.launch(content=False)

    def forgotten(m):
        m.launch()
        m.sql("UPDATE confirmations SET forgotten_at = 5 WHERE kind = 'launch'")

    return [("another user's run", other_owner, "不是平台自己送出的"), ("no job number", no_number, "沒有工作編號"),
            ("cleaned already", cleaned, "清過了"), ("environment gone", env_gone, "找不到"), ("agent changed", agent_changed, "代理"),
            ("environment disabled", disabled, "已停用"), ("slurm workDir changed", slurm_workdir_changed, "改過"),
            ("gcb workDir changed", gcb_workdir_changed, "改過"), ("folder not under runs", folder_elsewhere, "改過"),
            ("content of the launch gone", no_content, "當初送出的內容"), ("run forgotten", forgotten, "已經被刪除")]


@pytest.mark.parametrize("case", range(11))
def test_prepare_clean_refuses_each_unfit_case_in_plain_words(tmp_path, case):
    # TC-009 .. TC-020
    from abf_launch import build
    label, make, phrase = refuse_cases()[case]
    m = Mini(tmp_path / "p")
    owner = 1
    if label == "another user's run":
        m.launch()
        owner = 2
    else:
        make(m)
    with pytest.raises(build.Refusal) as e:
        build.prepare_clean(m.db, RUN, owner=owner)
    said = str(e.value)
    assert phrase in said, (label, said)
    for inner in ("Traceback", "SELECT", "sqlite", ".py", "args_json", str(tmp_path)):
        assert inner not in said
    if label == "another user's run":      # the same words as for a run that is not there, so nothing is told about whose it is
        with pytest.raises(build.Refusal) as gone:
            build.prepare_clean(m.db, "no-such-run", owner=owner)
        assert str(gone.value).split(" ", 1)[1] == said.split(" ", 1)[1]


def test_the_screen_says_what_is_deleted_what_is_not_and_that_resume_is_gone(m):
    # TC-021, TC-022, TC-023, TC-024
    m.launch()
    m.launch("g1", ce="ce-g")
    for run, work in ((RUN, SW + "/runs/%s/%s" % (RUN, K)), ("g1", "%s/runs/g1/%s" % (GW, K))):
        text = screen_of(prepared(m, run)[1])
        assert "這會永久刪除這次 run 的中間檔資料夾：" + work in text
        assert "結果（results）、原始資料與分析資料夾不會被動。" in text
        assert "刪掉之後這個 run 不能再續跑（-resume）；要再算一次，請當成新分析重新送出。" in text
        assert "要重算只能原樣重跑或重新送出" not in text


def test_only_the_gcb_screen_has_the_bucket_sentence_and_it_never_says_cannot_be_undone_unless_the_ledger_proved_it(m):
    # TC-025, TC-026, TC-027
    ledger = (REPO_ROOT / "specs" / "cloud-cleanup-d" / "ledger.md").read_text(encoding="utf-8")
    assert "仍可還原" in ledger and "預設就無法還原" not in ledger      # what the ledger found: 7 days of soft delete, restorable
    m.launch()
    m.launch("g1", ce="ce-g")
    gcb, slurm = screen_of(prepared(m, "g1")[1]), screen_of(prepared(m)[1])
    assert "刪除的是 bucket 裡這個前綴下的物件。" in gcb
    assert "軟刪除" in gcb and "仍可還原" in gcb
    for text in (gcb, slurm):
        for word in ("無法還原", "不能還原", "無法復原", "cannot be undone"):
            assert word not in text
    assert "bucket" not in slurm and "軟刪除" not in slurm


def test_the_screen_has_no_money_and_no_internal_words(m):
    # TC-028, TC-029
    m.launch()
    m.launch("g1", ce="ce-g")
    for run in (RUN, "g1"):
        text = screen_of(prepared(m, run)[1])
        for money in ("$", "NT", "元", "USD", "費用"):
            assert money not in text
        for inner in ("Traceback", "SELECT", "args_json", "bundle", "confirmation", "sqlite"):
            assert inner not in text


def test_control_characters_in_the_names_are_made_visible_on_the_screen(m):
    # TC-030
    from abf_launch import build
    m.launch()
    b = dict(prepared(m)[1], work=SW + "/runs/a\x1b[31mb/" + K, run_name="x\x1b[2Jy")
    text = screen_of(b)
    assert "\x1b" not in text and "\\x1b[31m" in text and "\\x1b[2J" in text
    assert text == build.as_text(build.clean_screen(b, None))


# ---- US2: offer_cleanup -----------------------------------------------------------------------------------------------------------

def test_a_succeeded_run_gets_one_pending_clean_work_request_and_nothing_else(m):
    # TC-031, TC-032, TC-033, TC-034
    from abf_launch import build
    m.launch()
    m.launch("g1", ce="ce-g")
    before = m.jobs()
    first = m.offer()
    second = m.offer("g1")
    assert first["offered"] is True and second["offered"] is True
    rows = {json.loads(r["bundle_json"])["run_name"]: r for r in m.requests()}
    assert set(rows) == {RUN, "g1"}
    for run, ce in ((RUN, "ce-s"), ("g1", "ce-g")):
        r = rows[run]
        assert r["state"] == "pending" and r["caller_user_id"] == 1 and r["ce_name"] == ce
        _, b, hand_off = prepared(m, run)
        assert json.loads(r["bundle_json"]) == b and r["screen_text"] == screen_of(b, hand_off)
    assert json.loads(rows["g1"]["bundle_json"])["work"] == "%s/runs/g1/%s" % (GW, K)
    assert m.jobs() == before == 0


def test_offering_again_makes_no_second_request(m):
    # TC-035
    m.launch()
    a, b = m.offer(), m.offer()
    assert a["offered"] and b["offered"] and a["id"] == b["id"] and len(m.requests()) == 1


def test_the_request_lives_seven_days_and_does_not_use_up_the_ten_slots(m):
    # TC-036, TC-037
    from abf_platform import confirm
    for i in range(10):
        m.sql("INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, expires_at) VALUES (?, ?, 'launch', ?, 1, 'pending', ?)",
              ("p%031d" % i, "h%d" % i, T0, T0 + 600))
    m.launch()
    got = m.offer()
    assert got["offered"] is True
    row = m.requests()[0]
    assert row["expires_at"] - row["created_at"] == 7 * 86400
    assert m.sql("SELECT COUNT(*) FROM confirmations WHERE kind <> 'clean_work' AND state = 'pending'")[0][0] == 10
    later = Clock(T0 + 7 * DAY + 1)
    with pytest.raises(confirm.NotApproved) as e:
        confirm.approve(m.db, row["id"], "PAGE", 1, clock=later, offline_after=1e9)
    assert e.value.status == "expired"


@pytest.mark.parametrize("status", ["failed", "aborted", "lost", "running"])
def test_failed_aborted_lost_running_and_unknown_runs_get_no_request(m, status):
    # TC-038, TC-039, TC-040, TC-041
    m.launch(status=status)
    got = m.offer()
    assert got["offered"] is False and got["reason"].strip() and m.requests() == []


def test_an_unknown_run_gets_no_request_and_no_complaint(m):
    # TC-042
    m.launch(status=None)
    got = m.offer()
    assert got["offered"] is False and m.requests() == []


def test_a_run_without_an_owner_gets_no_request(m):
    # TC-043
    m.launch(user=None)
    got = m.offer()
    assert got["offered"] is False and "擁有者" in got["reason"] and m.requests() == []


def test_another_users_run_is_not_offered_to_the_caller(m):
    # TC-044, TC-108: the only thing that can be offered goes to the user_id of the record; there is no argument to say anybody else
    from abf_platform import actions
    m.launch(user=1)
    assert m.offer()["offered"] is True
    assert [r["caller_user_id"] for r in m.requests()] == [1]
    assert not [r for r in m.sql("SELECT * FROM confirmations WHERE caller_user_id = 2")]
    assert list(inspect.signature(actions.offer_cleanup).parameters) == ["platform_path", "index_path", "run_name", "clock", "dry_run"]
    assert "offer_cleanup" not in actions.__doc__ and not hasattr(actions, "request_cleanup")


def test_a_run_whose_work_was_cleaned_gets_no_request(m):
    # TC-045
    m.launch(cleaned=T0)
    assert m.offer()["offered"] is False and m.requests() == []


def test_a_forgotten_run_gets_no_request(m):
    # TC-046
    m.launch()
    m.sql("UPDATE confirmations SET forgotten_at = 5 WHERE kind = 'launch'")
    assert m.offer()["offered"] is False and m.requests() == []


def test_no_job_number_and_no_record_get_no_request(m):
    # TC-047, TC-048
    m.launch(sid=None)
    assert m.offer()["offered"] is False
    m.run("lonely", "succeeded")        # in the index but never launched from this platform
    assert m.offer("lonely")["offered"] is False and m.requests() == []


def test_offer_cleanup_never_raises(m, monkeypatch):
    # TC-049, TC-050, TC-051, TC-052
    from abf_launch import build
    from abf_platform import actions, confirm, jobs, status

    def boom(*a, **k):
        raise RuntimeError("secret internal detail /tmp/x")

    m.launch()
    for target, name, err in ((confirm, "create_pending", boom), (build, "prepare_clean", boom), (status, "find_run", boom),
                              (confirm, "create_pending", lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("db is locked"))),
                              (confirm, "create_pending", lambda *a, **k: (_ for _ in ()).throw(jobs.JobRefused("too many")))):
        with monkeypatch.context() as mp:
            mp.setattr(target, name, err)
            got = m.offer()
        assert got["offered"] is False and isinstance(got["reason"], str) and got["reason"].strip()
        assert "secret" not in got["reason"] and "Traceback" not in got["reason"] and "/tmp" not in got["reason"]    # TC-055
    assert m.requests() == []


def test_a_full_clean_quota_is_skipped_silently(m, monkeypatch):
    # TC-053
    from abf_platform import confirm
    monkeypatch.setattr(confirm, "MAX_OPEN_CLEAN", 1)
    m.launch(RUN)
    m.launch("second")
    assert m.offer(RUN)["offered"] is True
    got = m.offer("second")
    assert got["offered"] is False and got["reason"].strip() and len(m.requests()) == 1


def test_offer_makes_no_file_when_there_is_no_platform_database(tmp_path):
    # TC-054
    from abf_platform import actions
    d = tmp_path / "empty"
    d.mkdir()
    got = actions.offer_cleanup(d / "platform.db", d / "index.db", RUN, clock=Clock(T0))
    assert got["offered"] is False and list(d.iterdir()) == []


def test_every_reason_is_one_plain_sentence(m):
    # TC-055
    m.launch(status="failed")
    m.launch("nolaunch", user=None)
    m.launch("cleaned", cleaned=T0)
    for run in (RUN, "nolaunch", "cleaned", "ghost"):
        r = m.offer(run)["reason"]
        assert r.strip() and "\n" not in r and "Traceback" not in r and "SELECT" not in r and str(m.tmp) not in r


def test_a_run_on_a_type_that_can_only_be_modelled_gets_no_request(m):
    # TC-056
    m.ce("ce-aws", "aws-batch-platform", {"workDir": "s3://b/x"}, status="unsupported")
    m.launch(ce="ce-aws", folder="/srv/x/runs/" + RUN)
    got = m.offer()
    assert got["offered"] is False and m.requests() == []


# ---- US3: the receiver --------------------------------------------------------------------------------------------------------

def finished(plat, scenario="nf2510_ok", run=RUN, bound=True):
    from abf_platform import store
    token = store.create_token(plat.tokens, run_name=run) if bound else store.create_token(plat.tokens)
    wid, resp = plat.replay(variant(scenario, run, "sess-" + run, plat.clock()), token)
    assert all(r.status_code < 300 for r in resp), [r.status_code for r in resp]
    return token, wid, resp


def platform_world(plat, **kw):
    mini = Mini(plat.dir)
    mini.launch(status=None, **kw)
    return mini


def run_facts(plat):
    con = sqlite3.connect(str(plat.index))
    try:
        return con.execute("SELECT final_status, ended_at, exit_status, failure_reason FROM runs").fetchall()
    finally:
        con.close()


def test_complete_of_a_succeeded_run_makes_one_offer_and_the_response_and_token_end_are_unchanged(plat, tmp_path, monkeypatch):
    # TC-057, TC-058
    from abf_platform import actions
    from helpers import Platform
    mini = platform_world(plat)
    token, _, resp = finished(plat)
    assert resp[-1].status_code == 200 and resp[-1].json() == {"status": "OK"}
    assert len(mini.requests()) == 1 and json.loads(mini.requests()[0]["bundle_json"])["run_name"] == RUN
    with_offer = (resp[-1].json(), run_facts(plat), plat.store.lookup_ended_token(plat.tokens, token) is not None)
    monkeypatch.setattr(actions, "offer_cleanup", lambda *a, **k: {"offered": False, "reason": "off"})
    other = Platform(tmp_path / "other", clock=Clock())
    Mini(other.dir).launch(status=None)
    t2, _, resp2 = finished(other)
    without = (resp2[-1].json(), run_facts(other), other.store.lookup_ended_token(other.tokens, t2) is not None)
    assert with_offer == without and with_offer[2] is True


def test_complete_of_a_failed_run_makes_none(plat):
    # TC-059
    mini = platform_world(plat)
    _, _, resp = finished(plat, "nf2510_fail")
    assert resp[-1].status_code == 200 and mini.requests() == []


def test_complete_when_the_offer_fails_still_answers_ok_and_records_the_run(plat, monkeypatch):
    # TC-060
    from abf_platform import actions

    def boom(*a, **k):
        raise RuntimeError("offer broke")

    mini = platform_world(plat)
    monkeypatch.setattr(actions, "offer_cleanup", boom)
    token, _, resp = finished(plat)
    assert resp[-1].status_code == 200 and resp[-1].json() == {"status": "OK"}
    assert run_facts(plat)[0][0] == "succeeded" and run_facts(plat)[0][1] is not None
    assert plat.store.lookup_ended_token(plat.tokens, token) is not None and mini.requests() == []


def test_a_token_not_made_for_one_run_makes_no_offer(plat):
    # TC-061
    mini = platform_world(plat)
    finished(plat, bound=False)
    assert mini.requests() == []


def test_a_second_complete_of_an_aborted_run_makes_no_second_offer(plat, monkeypatch):
    # TC-062
    from abf_platform import actions
    from test_followup3 import complete_of
    calls = []
    monkeypatch.setattr(actions, "offer_cleanup", lambda *a, **k: calls.append(a))
    platform_world(plat)
    token, wid, _ = finished(plat, "nf2510_fail")
    rows = db_rows(plat.index)
    body = complete_of(variant("nf2510_fail", RUN, "sess-" + RUN, plat.clock()))["body"]
    r = plat.send("PUT", "/trace/%s/complete" % wid, body, token=token)
    assert r.status_code == 200 and r.json() == {"status": "OK"} and calls == [] and db_rows(plat.index) == rows


def test_complete_with_no_platform_database_answers_ok_and_makes_none(plat):
    # TC-063
    for p in plat.dir.glob("platform.db*"):
        p.unlink()
    _, _, resp = finished(plat)
    assert resp[-1].status_code == 200 and not list(plat.dir.glob("platform.db*"))


def test_the_receiver_imports_offer_cleanup_inside_complete_and_keeps_its_top_imports():
    # TC-064, TC-116
    src = (PKG / "receiver.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    named = {a.name for n in tree.body if isinstance(n, ast.ImportFrom) and n.level == 1 for a in n.names}
    assert "actions" not in named and {"agents", "common", "store"} <= named
    complete = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "complete")
    body = ast.get_source_segment(src, complete)
    assert "from . import actions" in body and body.count("offer_cleanup") == 1
    assert re.search(r"if succeeded and trow\[\"run_name\"\] is not None:\s+try:", body)      # nothing else is decided here
    for word in ("user_id", "launches", "create_pending", "clean_work", "prepare_clean"):
        assert word not in body
    import subprocess, sys
    out = subprocess.run([sys.executable, "-c", "import sys; import abf_platform.receiver; print('abf_platform.actions' in sys.modules)"],
                         cwd=str(PLATFORM_DIR), capture_output=True, text=True)
    assert out.stdout.strip() == "False", out.stderr


def test_a_page_or_a_board_only_reads_it_never_offers(tmp_path, monkeypatch):
    # TC-065, TC-066, TC-067
    from human_harness import World
    from test_confirm_page import logged_in
    w = World(tmp_path, monkeypatch)
    w.clock.t = time.time()
    ann = w.user("ann")
    world_run(w, ann, "old-one")
    world_run(w, ann, "other-one")
    c = logged_in(w, "ann")
    for url in ("/", "/?run=id-old-one", "/?run=id-old-one&lang=en"):
        assert c.get(url).status_code == 200
    assert w.sql("SELECT COUNT(*) FROM confirmations WHERE kind = 'clean_work'")[0][0] == 0         # no complete, nothing offered, not for an old run either
    rid = offer(w, "other-one")["id"]          # the one request there is: this run's complete came, the old one's never did
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET expires_at = ? WHERE id = ?", (time.time() - 1, rid))
    con.close()
    for url in ("/", "/?run=id-other-one", "/c/" + rid):
        c.get(url)
    w.clock.t += 8 * DAY
    for url in ("/", "/?run=id-other-one", "/c/" + rid):
        c.get(url)
    assert w.sql("SELECT COUNT(*) FROM confirmations WHERE kind = 'clean_work'")[0][0] == 1      # the lapsed one is not replaced


# ---- worlds on the web test harness ------------------------------------------------------------------------------------------------

def world_run(w, owner, name=RUN, status="succeeded"):
    """A run of `owner` on lab-a: its row in the index, its row of the hand-off record and the confirmation that holds what was sent."""
    from abf_platform import common, compute_envs, store
    from abf_station import launch as bundle_mod
    from test_web_board import seed
    seed(w, name, status, launch_row=False, started=time.time() - 7200, ended=time.time() - 3600)
    view = compute_envs.get(w.ip.state_db, "lab-a")
    folder = view["config"]["workDir"] + "/runs/" + name
    at = time.time() - 5000 + len(name)
    body = {"run_name": name, "run_folder": folder, "ce": bundle_mod.snapshot_ce(view)}
    con = store.connect_state(w.ip.state_db)
    with con:
        con.execute("INSERT INTO launches (run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, user_id) VALUES (?,?,?,?,?,?,?,?)",
                    (name, 4242, folder, "lab-a", view["agent"], at, at + 1, owner.user_id))
        con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, caller_user_id, state, confirmed_at, bundle_json) "
                    "VALUES (?, ?, 'launch', ?, ?, 'confirmed', ?, ?)", ("l" + common.bundle_sha256(body)[:30], common.bundle_sha256(body), at,
                                                                         owner.user_id, at, json.dumps(body)))
    con.close()


def offer(w, name=RUN):
    from abf_platform import actions
    return actions.offer_cleanup(w.ip.state_db, w.ip.index, name, clock=w.clock)


def test_the_offered_request_opens_as_a_page_with_the_words_and_the_button(tmp_path, monkeypatch):
    # TC-068
    from human_harness import World
    from test_confirm_page import logged_in
    w = World(tmp_path, monkeypatch)
    w.clock.t = time.time()
    ann, bob = w.user("ann"), w.user("bob")
    world_run(w, ann)
    got = offer(w)
    assert got["offered"] is True
    t = logged_in(w, "ann").get("/c/" + got["id"]).text
    assert "確認刪除" in t and "這會永久刪除這次 run 的中間檔資料夾：" in t and "結果（results）、原始資料與分析資料夾不會被動。" in t
    assert "/runs/%s/%s" % (RUN, K) in t
    # TC-080, TC-081: bob cannot read it, cannot press it, and his board has nothing of ann's run
    b = logged_in(w, "bob")
    page = b.get("/c/" + got["id"])
    assert page.status_code == 403 and RUN not in page.text and "<button" not in page.text
    before = w.sql("SELECT COUNT(*) FROM jobs")[0][0]
    assert b.post("/c/" + got["id"], data={"csrf": "x"}).status_code == 403
    assert w.sql("SELECT COUNT(*) FROM jobs")[0][0] == before and w.sql("SELECT state FROM confirmations WHERE id = ?", (got["id"],))[0][0] == "pending"
    assert RUN not in b.get("/").text


def test_an_expired_clean_request_cannot_be_pressed_and_is_not_offered_again(tmp_path, monkeypatch):
    # TC-079
    from human_harness import World, csrf_of
    from test_confirm_page import logged_in
    w = World(tmp_path, monkeypatch)
    w.clock.t = time.time()
    ann = w.user("ann")
    world_run(w, ann)
    rid = offer(w)["id"]
    c = logged_in(w, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET expires_at = ? WHERE id = ?", (time.time() - 1, rid))
    con.close()
    r = c.post("/c/" + rid, data={"csrf": token})
    assert r.status_code >= 400 and w.sql("SELECT COUNT(*) FROM jobs WHERE kind = 'clean_work'")[0][0] == 0
    assert "逾時" in c.get("/c/" + rid).text


# ---- US4: end to end ----------------------------------------------------------------------------------------------------------------

def press(m, rid, user=1):
    from abf_platform import confirm
    return confirm.approve(m.db, rid, "PAGE", user, clock=m.clock, offline_after=1e9)


def test_slurm_end_to_end_complete_offer_page_press_agent_deletes_then_the_record_says_cleaned_and_nothing_more_is_offered(tmp_path, monkeypatch):
    # TC-068, TC-069, TC-070, TC-071, TC-072, TC-073
    from abf_platform import jobs
    from test_station_clean import Env, RUN as ERUN
    env = Env(tmp_path / "s", monkeypatch)
    m = Mini(tmp_path / "p", agent="agent-f")
    m.slurm_ce("ce-e", workdir=str(env.work), agent="agent-f", launchDir=str(env.site.launch))
    m.launch(ERUN, ce="ce-e", folder=str(env.F), sid=4242)
    rid = m.offer(ERUN)["id"]
    guards, kept = env.guards(), {p: (env.F / p).read_bytes() for p in ("head.sh", "slurm-4242.out", ".nextflow/history")}
    env.nothing_sent()
    assert env.guards() == guards and (env.W / "ab" / "cdef" / "a.tsv").exists() and m.jobs() == 0        # TC-069: not pressed, nothing moves
    _, job_id = press(m, rid)
    job = jobs.claim(m.db, "agent-f", m.clock)
    assert job["id"] == job_id and job["kind"] == "clean_work"
    state, result = env.go(job)
    assert state == "done" and result["cleaned"] is True
    jobs.take_result(m.db, "agent-f", job_id, state, result, m.clock)
    assert not env.W.exists() and len(env.site.destructive()) == 1                                         # TC-070
    assert env.guards() == guards                                                                          # TC-071
    assert {p: (env.F / p).read_bytes() for p in kept} == kept
    assert m.sql("SELECT work_cleaned_at FROM launches WHERE run_name = ?", (ERUN,))[0][0] is not None     # TC-072
    again = m.offer(ERUN)
    assert again["offered"] is False and len(m.requests()) == 1                                            # TC-073


def test_slurm_end_to_end_resumed_attempt_cleans_the_origin_folder(tmp_path, monkeypatch):
    # TC-074
    from abf_platform import jobs
    from test_station_clean import Env, RUN as ERUN
    env = Env(tmp_path / "s", monkeypatch)
    m = Mini(tmp_path / "p", agent="agent-f")
    m.slurm_ce("ce-e", workdir=str(env.work), agent="agent-f", launchDir=str(env.site.launch))
    m.launch(ERUN, ce="ce-e", folder=str(env.F), sid=4242, status="failed")
    m.launch(ERUN + "-a2", ce="ce-e", folder=str(env.F), sid=4243, parent=ERUN)
    rid = m.offer(ERUN + "-a2")["id"]
    assert json.loads(m.requests()[0]["bundle_json"])["run_name"] == ERUN + "-a2"
    guards = env.guards()
    _, job_id = press(m, rid)
    job = jobs.claim(m.db, "agent-f", m.clock)
    state, result = env.go(job)
    assert state == "done" and not env.W.exists() and env.guards() == guards and (env.F / "head.sh").exists()


def test_nothing_is_deleted_until_the_person_presses(tmp_path, monkeypatch):
    # TC-069, TC-075
    from test_station_clean_gcb import World as GcbWorld, RUN as GRUN
    gw = GcbWorld(tmp_path / "g", monkeypatch)
    m = Mini(tmp_path / "p")
    m.gcb_ce("ce-gw")
    m.launch(GRUN, ce="ce-gw", folder=str(gw.folder), sid=4242)
    assert m.offer(GRUN)["offered"] is True
    assert gw.objects == gw.start and gw.calls == [] and m.jobs() == 0


def test_gcb_end_to_end_with_a_fake_bucket_deletes_only_the_run_prefix_and_keeps_work2_and_work_keep(tmp_path, monkeypatch):
    # TC-076, TC-077
    from abf_platform import jobs
    from test_station_clean_gcb import World as GcbWorld, RUN as GRUN
    gw = GcbWorld(tmp_path / "g", monkeypatch)
    m = Mini(tmp_path / "p")
    m.gcb_ce("ce-gw")
    m.launch(GRUN, ce="ce-gw", folder=str(gw.folder), sid=4242)
    rid = m.offer(GRUN)["id"]
    assert json.loads(m.requests()[0]["bundle_json"])["work"] == "gs://lab-bucket/%s/runs/%s/%s" % (K, GRUN, K)
    _, job_id = press(m, rid)
    job = jobs.claim(m.db, "a1", m.clock)
    state, result = gw.go(job)
    assert state == "done" and result["cleaned"] is True
    gone = gw.start - gw.objects
    assert gone == {"work/runs/r1/%s/x" % K, "work/runs/r1/%s/sub/y" % K}
    assert {"work/runs/r1/work2/x", "work/runs/r1/work-keep", "work/runs/r1/results/a.tsv", "work/runs/r2/work/z"} <= gw.objects


def test_an_agent_refusal_or_error_leaves_work_cleaned_at_empty_and_makes_no_new_offer(tmp_path, monkeypatch):
    # TC-078
    from abf_platform import jobs
    from test_station_clean import Env, RUN as ERUN
    env = Env(tmp_path / "s", monkeypatch)
    m = Mini(tmp_path / "p", agent="agent-f")
    m.slurm_ce("ce-e", workdir=str(env.work), agent="agent-f", launchDir=str(env.site.launch))
    m.launch(ERUN, ce="ce-e", folder=str(env.F), sid=4242)
    rid = m.offer(ERUN)["id"]
    _, job_id = press(m, rid)
    job = jobs.claim(m.db, "agent-f", m.clock)
    jobs.take_result(m.db, "agent-f", job_id, "refused", {"ok": False, "message": "results 裡有指向 work 的捷徑，刪了會讓結果壞掉"}, m.clock)
    assert m.sql("SELECT work_cleaned_at FROM launches")[0][0] is None and env.W.exists()
    assert len(m.requests()) == 1 and m.requests()[0]["state"] == "confirmed"      # nothing new came by itself


# ---- scope, constitution -------------------------------------------------------------------------------------------------------------

def sources(*roots):
    for root in roots:
        for p in sorted(root.rglob("*.py")):
            yield p, p.relative_to(PLATFORM_DIR).as_posix()


def test_the_only_place_that_creates_a_clean_work_request_is_offer_cleanup():
    # TC-104, TC-108
    found = []
    for p, rel in sources(PKG, LAUNCH_PKG):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", None)) == "create_pending":
                if any(isinstance(a, ast.Constant) and a.value == "clean_work" for a in node.args):
                    found.append((rel, node.lineno))
    assert [f[0] for f in found] == ["abf_platform/actions/__init__.py"]
    text = (PKG / "actions" / "__init__.py").read_text(encoding="utf-8").splitlines()
    start = max(i for i, ln in enumerate(text[:found[0][1]]) if ln.startswith("def "))
    assert text[start].startswith("def offer_cleanup(")



def test_no_new_mcp_tool_no_new_route_no_new_cli_command(tmp_path):
    # TC-105, TC-106, TC-107
    from test_actions_layer import READ_NAMES, WRITE_NAMES, _server, _tools
    names = {t.name for t in _tools(_server(str(tmp_path / "index.db")))}
    assert len(names) == len(READ_NAMES + WRITE_NAMES) and names == set(READ_NAMES + WRITE_NAMES) and not any("clean" in n or n.startswith("request_") for n in names)
    from abf_platform import cli, web
    commands = sorted(cli.build_parser()._subparsers._group_actions[0].choices)
    assert not any("clean" in c for c in commands)
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    paths = sorted({getattr(r, "path", "?") for r in app.routes})
    assert not any("clean" in p for p in paths)
    assert COMMANDS == commands, commands
    assert ROUTES == paths, paths


COMMANDS = ['agent-token', 'cancel', 'ce', 'dataset', 'fetch-records', 'forget', 'launch', 'launches', 'mcp', 'oauth', 'pat', 'rebuild', 'relaunch', 'resume',
            'runs', 'serve', 'token', 'user', 'web']      # as they were before this task
ROUTES = ['/', '/.well-known/oauth-authorization-server', '/act/{verb}', '/authorize', '/c/{rid}', '/consent/{rid}', '/launch', '/launch/diagram',
          '/login', '/logout', '/register', '/revoke', '/settings', '/settings/pipelines', '/settings/pipelines/confirm', '/token', '/usage', '/welcome']


def test_platform_and_launch_sources_have_no_program_start_no_rm_and_not_the_forbidden_word():
    # TC-109, TC-110, TC-121
    forbidden = [r"\bsubprocess\b", r"\bos\.system\b", r"\bPopen\b", r"\bos\.exec", r"\brm\s+-", r"storage\s+rm", r"\brmtree\b",
                 r"\bsbatch\b", r"\bscancel\b", r"nextflow\s+clean", r"batch\s+jobs\s+delete"]
    hits = []
    for p, rel in sources(PKG, LAUNCH_PKG):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for pat in forbidden + ([r"station"] if rel.startswith("abf_platform/") else []):
                if re.search(pat, line):
                    hits.append("%s:%d %s" % (rel, n, line.strip()))
    assert hits == [], hits


def test_this_file_has_the_nothing_existing_header_and_no_worker_was_added():
    # TC-111, TC-112, TC-120
    head = "\n".join(Path(__file__).read_text(encoding="utf-8").splitlines()[:40])
    assert "# Nothing existing:" in head
    body = inspect.getsource(__import__("abf_platform.actions", fromlist=["x"]).offer_cleanup)
    for word in ("Thread", "threading", "sched", "while True", "Timer", "cron", "POLICY", "days"):
        assert word not in body
    assert not re.search(r"POLICY[^\n]*clean_work|clean_work[^\n]*POLICY", "\n".join(p.read_text(encoding="utf-8") for p, _ in sources(PKG, LAUNCH_PKG)))


def test_the_schema_is_the_same_before_and_after_an_offer(m):
    # TC-114
    m.launch()

    def shape():
        return (m.sql("SELECT name, sql FROM sqlite_master ORDER BY name"),
                {t["name"]: [tuple(c) for c in m.sql("PRAGMA table_info(%s)" % t["name"])]
                 for t in m.sql("SELECT name FROM sqlite_master WHERE type = 'table'")})

    def plain(rows):
        return [tuple(r) for r in rows]

    before = shape()
    assert m.offer()["offered"] is True
    after = shape()
    assert plain(before[0]) == plain(after[0]) and before[1] == after[1]
    assert len(m.requests()) == 1


def test_no_secret_is_in_the_bundle_the_screen_or_the_reason(m):
    # TC-117
    m.launch()
    m.launch("g1", ce="ce-g")
    blob = ""
    for run in (RUN, "g1"):
        b = prepared(m, run)[1]
        blob += json.dumps(b) + screen_of(b)
    blob += m.offer(RUN)["id"] + m.offer("ghost")["reason"]
    for word in ("token", "password", "secret", "private_key", "begin "):
        assert word not in blob.lower()


def test_no_expiry_reminder_no_cost_line_no_scope_choice_in_the_request(m):
    # TC-118, TC-119, TC-120
    m.launch()
    b = prepared(m)[1]
    assert set(b) == {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce", "work"}
    text = screen_of(b)
    for word in ("30 天", "到期", "月費", "全部", "批次", "--", "刪除整個", "也刪結果"):
        assert word not in text
    assert m.offer()["offered"] is True and len(m.requests()) == 1 and m.sql("SELECT COUNT(*) FROM confirmations")[0][0] == 2


# ---- US5: the documents ----------------------------------------------------------------------------------------------------------------

def test_docs_say_what_is_deleted_what_is_not_and_keep_the_pinned_sentences():
    # TC-082 .. TC-094
    doc = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    heads = [ln for ln in doc.splitlines() if ln.startswith("### ")]
    title = "### Cleaning a finished run's work folder"
    assert title in heads
    assert heads.index("### Forget (keep-submissions)") + 1 == heads.index(title) and heads[heads.index(title) + 1].startswith("### Resume and relaunch")
    section = doc.split(title, 1)[1].split("\n### ", 1)[0]
    for need in ("`complete`", "succeeded", "the run's owner", "`<run folder>/work`", "`<workDir>/runs/<run>/work/`", "`results`", "`rawdata`",
                 "`analysis`", "does not start programs", "7 days", "not offered again", "cannot be resumed", "publishDir", "link", "exit code 17",
                 "soft delete", "no owner", "before this feature", "only after"):
        assert need in section, need
    assert "cannot be undone" not in section and "irreversible" not in section
    assert "It never deletes a run folder or a result on the site; the only thing it can have deleted is the work folder of a finished run, " \
           "and only after its owner's yes (see \"Cleaning a finished run's work folder\")" in doc
    assert "It never deletes a run, a run folder or a result on the site" not in doc and "prunes finished job rows after 7 days" in doc
    start = doc.index("## 6. The station agent")
    sixth = doc[start:doc.index("### Start it")]
    assert "It does **not** launch, cancel, delete, move or write anything" not in sixth and "Cleaning a finished run's work folder" in sixth
    assert "first version" in sixth or "originally" in sixth
    for path in re.findall(r"gs://[\w./-]+", section):
        assert path.startswith("gs://lab-bucket/")                       # TC-092: only the example paths of the plan
    assert not re.search(r"(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/", doc)
    testing = (REPO_ROOT / "docs" / "TESTING.md").read_text(encoding="utf-8")
    assert re.search(r"^## [^\n]*cloud-cleanup[^\n]*$", testing, re.M)
    part = testing.split("(cloud-cleanup", 1)[1].split("\n## ", 1)[0]
    for number in range(1, 6):
        assert re.search(r"^%d\. " % number, part, re.M), number
    assert "(Only a finished run's work folder can be deleted, and only after its owner's yes; see cloud-cleanup.)" in testing
    assert "(`rm` is not a job kind, and no job kind writes.)" not in testing
    for word in ("ampliseq-d5",):
        assert word in part
    ledger = (SPEC / "ledger.md").read_text(encoding="utf-8")
    assert "git diff --stat" in ledger and all(w in ledger for w in ("never deletes", "delete, move", "no job kind"))
