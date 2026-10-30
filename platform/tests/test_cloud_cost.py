# Nothing existing: Seqera Platform only bills (no estimate or per-person cap inside the platform), Nextflow's trace reports machineType and priceModel but no price, and a Google billing budget alerts after the spend, so a check before a launch is ours.
"""cloud-cost (C-3): the price of a Google Batch run in US dollars, what was used this month, and the per-person monthly cap.
Test cases TC-001 ... TC-133 are named in the comments, see specs/cloud-cost/test-case.md (the verifier's list).
Everything here uses a made-up price list, made-up accounts and databases in tmp_path: no network, no program is started."""
import asyncio
import calendar
import json
import math
import re
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, Platform, pkg_env, run_cli

PKG = PLATFORM_DIR / "abf_platform"
GCB = "googlebatch-platform"
SRC = "https://example.test/price-page"
RATES = {"currency": "USD", "regions": {"us-central1": {
    "n2-standard-4": {"standard": 0.20, "spot": 0.06, "source": SRC, "read_on": "2026-10-24"},
    "e2-standard-2": {"standard": 0.10, "source": SRC, "read_on": "2026-10-25"}}}}
H = 3600000


def _cc():
    from abf_platform import cloud_cost
    return cloud_cost


def _task(**kw):
    t = {"name": "T", "status": "COMPLETED", "realtime_ms": 10 * H, "machine_type": "n2-standard-4", "price_model": "standard",
         "zone": "us-central1-a"}
    t.update(kw)
    return {k: v for k, v in t.items() if v is not Ellipsis}


def _usd(tasks, rates=RATES, **kw):
    return _cc().cost_of_tasks(tasks, rates, **kw)


def _rates_with(**changes):
    r = json.loads(json.dumps(RATES))
    r["regions"]["us-central1"]["n2-standard-4"].update(changes)
    return r


def _epoch(iso):
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


NOW = _epoch("2026-10-15T00:00:00Z")


# ---- US1: the rates and the price of one task ------------------------------------------------------------------------

def test_ten_hours_of_n2_standard_4_is_two_dollars():
    # TC-001, TC-002 (T1)
    out = _usd([_task()])
    assert out["usd"] == pytest.approx(2.00) and out["currency"] == "USD"
    assert _usd([_task(price_model="spot")])["usd"] == pytest.approx(0.60)


def test_price_model_is_not_case_sensitive():
    # TC-004
    assert _usd([_task(price_model="SPOT")])["usd"] == pytest.approx(0.60)
    assert _usd([_task(price_model="Standard")])["usd"] == pytest.approx(2.00)


def test_two_tasks_add_up():
    # TC-003 (T2)
    a = _task(name="A", realtime_ms=5400000)
    b = _task(name="B", machine_type="e2-standard-2", realtime_ms=7200000)
    assert _usd([a])["usd"] == pytest.approx(0.30)
    assert _usd([b])["usd"] == pytest.approx(0.20)
    assert _usd([a, b])["usd"] == pytest.approx(0.50)


def test_as_of_is_the_oldest_read_date_of_what_was_used():
    # TC-005
    both = _usd([_task(), _task(machine_type="e2-standard-2")])
    assert both["as_of"] == "2026-10-24"
    assert _usd([_task(machine_type="e2-standard-2")])["as_of"] == "2026-10-25"


@pytest.mark.parametrize("task, words", [
    ({"machine_type": "c9-fake-8"}, ["c9-fake-8"]),                      # TC-006
    ({"realtime_ms": ...}, ["realtime"]),                                # TC-007
    ({"price_model": ...}, ["price"]),                                   # TC-008
    ({"price_model": "weird"}, ["weird"]),                               # TC-009
    ({"zone": ...}, ["區域"]),                                            # TC-010
    ({"zone": "europe-west1-b"}, ["europe-west1"]),                      # TC-011
    ({"machine_type": "e2-standard-2", "price_model": "spot"}, ["e2-standard-2"]),   # TC-012: no spot price for it
    ({"machine_type": ..., "cpus": 4}, ["machine"]),                     # TC-013: never guessed from cpus
])
def test_anything_missing_makes_the_whole_run_unknown_with_a_reason(task, words):
    # TC-006 ... TC-013 (T3)
    good = _task(name="good")
    out = _usd([good, _task(name="bad", **task)])
    assert out["usd"] is None
    text = " ".join(out["unknown_reasons"])
    assert out["unknown_reasons"] and all(w in text or w.lower() in text.lower() for w in words), text


def test_one_bad_task_does_not_leave_a_partial_sum():
    # TC-006
    out = _usd([_task(), _task(machine_type="c9-fake-8")])
    assert out["usd"] is None and out["usd"] != 0


@pytest.mark.parametrize("change", [{"source": ...}, {"read_on": ...}, {"source": "http://x.test/p"}, {"read_on": "24/10/2026"}])
def test_a_rate_entry_without_a_source_or_a_read_date_is_not_used(change):
    # TC-014 ... TC-017 (T4)
    r = _rates_with()
    entry = r["regions"]["us-central1"]["n2-standard-4"]
    for k, v in change.items():
        if v is Ellipsis:
            del entry[k]
        else:
            entry[k] = v
    out = _usd([_task()], r)
    assert out["usd"] is None and "n2-standard-4" in " ".join(out["unknown_reasons"])


def test_load_rates_gives_none_for_a_missing_file_or_an_array(tmp_path):
    # TC-018
    cc = _cc()
    assert cc.load_rates(tmp_path / "nope.json") is None
    (tmp_path / "arr.json").write_text("[1, 2]")
    assert cc.load_rates(tmp_path / "arr.json") is None
    (tmp_path / "ok.json").write_text(json.dumps(RATES))
    assert cc.load_rates(tmp_path / "ok.json")["currency"] == "USD"


def test_an_unreadable_rates_file_makes_cost_unknown():
    out = _cc().cost_of_tasks([_task()], None)
    assert out["usd"] is None and out["unknown_reasons"]


SHIPPED = PKG / "data" / "cloud_rates.json"


def _shipped_entries():
    data = json.loads(SHIPPED.read_text(encoding="utf-8"))
    return data, [(r, m, e) for r, ms in data["regions"].items() for m, e in ms.items()]


def test_the_shipped_rates_file_is_valid_and_empty():
    # TC-019, TC-020, TC-021, TC-022 (T5, 裁決四 10: real prices go to cloud-rates-fill)
    data, entries = _shipped_entries()
    assert data["currency"] == "USD" and "_about" in data
    assert _cc().load_rates(SHIPPED) is not None
    today = time.strftime("%Y-%m-%d")
    for region, machine, e in entries:           # TC-020: whatever entry exists must be sourced and sane
        where = "%s/%s" % (region, machine)
        assert str(e.get("source", "")).startswith("https://"), where
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("read_on", ""))), where
        assert e["read_on"] <= today, where
        for model in ("standard", "spot"):
            if model in e:
                v = e[model]
                assert isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0, where
        if "spot" in e and "standard" in e:
            assert e["spot"] < e["standard"], where
    assert entries == []                         # TC-021: nothing is priced in this task
    text = SHIPPED.read_text(encoding="utf-8")
    for word in ("TWD", "NT$", "exchange", "匯率"):
        assert word not in text


def test_empty_shipped_rates_make_every_estimate_unknown_with_the_reason():
    # TC-134
    cc = _cc()
    rates = cc.load_rates(SHIPPED)
    for model in ("standard", "spot"):
        out = cc.cost_of_tasks([_task(price_model=model, realtime_ms=H)], rates)
        assert out["usd"] is None and "尚未填入價目" in " ".join(out["unknown_reasons"])


# ---- US2: estimate and what was used this month ----------------------------------------------------------------------

class World:
    def __init__(self, tmp_path):
        from abf_platform import store
        self.store = store
        self.index, self.plat, self.tokens = tmp_path / "index.db", tmp_path / "platform.db", tmp_path / "tokens.db"
        store.init_index(self.index)
        store.init_state(self.plat)
        store.connect_tokens(self.tokens).close()
        self.n = 0
        self.alice = store.create_user(self.tokens, "alice", "lab")
        self.bob = store.create_user(self.tokens, "bob", "lab")

    def ce(self, name, platform=GCB, location=None):
        cfg = {"location": location} if location else {}
        con = self.store.connect_state(self.plat)
        with con:
            con.execute("INSERT OR IGNORE INTO compute_envs (name, platform, status, is_primary, config_json, created_at, updated_at) "
                        "VALUES (?, ?, 'ready', 0, ?, 1, 1)", (name, platform, json.dumps(cfg)))
        con.close()

    def run(self, name, user, pipeline="nf-core/x", ce="gcb1", tasks=None, status="succeeded", started="2026-09-10T04:00:00Z",
            platform=GCB, location=None, launches=None):
        """A run in the index with its task rows, and the hand-off record that says who sent it where. tasks are dicts (see _task)."""
        self.n += 1
        self.ce(ce, platform, location)
        con = self.store.connect_index(self.index)
        with con:
            con.execute("INSERT INTO runs (id, session_id, run_name, source, final_status, started_at, ended_at, last_message_at) "
                        "VALUES (?, 's', ?, 'live', ?, ?, ?, 3)", ("id-" + name, name, status, _epoch(started), _epoch(started) + 100))
            for i, t in enumerate(tasks if tasks is not None else [_task()]):
                con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue, machine_type, price_model, "
                            "cloud_zone) VALUES (?, ?, ?, ?, 1, ?, NULL, ?, ?, ?)",
                            ("id-" + name, "%d:1" % i, t.get("name", "T"), t.get("status", "COMPLETED"), t.get("realtime_ms"),
                             t.get("machine_type"), t.get("price_model"), t.get("zone")))
        con.close()
        con = self.store.connect_state(self.plat)
        with con:
            for k, (lce, lpipe) in enumerate(launches or [(ce, pipeline)]):
                at = 1000 * self.n + k
                con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?, '/f', ?, 'a1', ?, ?)",
                            (name, lce, at, user))
                con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state, confirmed_at, bundle_json) "
                            "VALUES (?, 'x', 'launch', ?, 'confirmed', ?, ?)",
                            ("c-%s-%d" % (name, k), at, at, json.dumps({"pipeline": lpipe})))
        con.close()

    def cost(self, name, rates=RATES):
        return _cc().run_tasks_cost(self.index, name, rates)

    def estimate(self, user, pipeline="nf-core/x", rates=RATES):
        return _cc().estimate_launch(self.index, self.plat, user, pipeline, rates)

    def used(self, user, month="2026-10", rates=RATES):
        return _cc().month_used(self.index, self.plat, user, month, rates)

    def cap(self, user, usd):
        self.store.set_cloud_cap(self.tokens, user, usd)

    def ask(self, user, pipeline="nf-core/x", ce="gcb1", rates=RATES, now=NOW):
        return _cc().cap_problem(self.plat, ce, {"pipeline": pipeline}, user, index_path=self.index, tokens_path=self.tokens,
                                 rates=rates, now=now)


@pytest.fixture
def w(tmp_path):
    return World(tmp_path)


def _hours(h, **kw):
    return [_task(realtime_ms=int(h * H), **kw)]


def test_estimate_is_the_cost_of_the_latest_successful_run_of_the_same_pipeline_of_this_user(w):
    # TC-024 ... TC-028 (T6)
    w.run("old", w.alice, tasks=_hours(17), started="2026-08-01T00:00:00Z")           # 3.40
    w.run("new", w.alice, tasks=_hours(12.5), started="2026-09-01T00:00:00Z")         # 2.50
    w.run("others", w.bob, tasks=_hours(1), started="2026-09-20T00:00:00Z")
    w.run("other-pipe", w.alice, pipeline="nf-core/y", tasks=_hours(2), started="2026-09-21T00:00:00Z")
    w.run("failed", w.alice, tasks=_hours(3), status="failed", started="2026-09-22T00:00:00Z")
    w.run("slurm", w.alice, ce="nano4", platform="slurm-platform", tasks=_hours(4), started="2026-09-23T00:00:00Z")
    est = w.estimate(w.alice)
    assert est["usd"] == pytest.approx(2.50) and "new" in est["basis"]
    assert w.estimate(w.bob)["usd"] == pytest.approx(0.20)
    assert w.estimate(w.alice, "nf-core/y")["usd"] == pytest.approx(0.40)


def test_estimate_pipeline_names_match_in_the_same_spelling_only_trivially_different(w):
    w.run("r", w.alice, pipeline="nf-core/x", tasks=_hours(5))
    assert w.estimate(w.alice, "nf-core/x")["usd"] == pytest.approx(1.00)
    assert w.estimate(w.alice, "NF-core/x/ ")["usd"] == pytest.approx(1.00)


def test_a_failed_retry_of_the_basis_run_is_counted(w):
    # TC-029
    w.run("r", w.alice, tasks=[_task(name="A", realtime_ms=5 * H), _task(name="A", status="FAILED", realtime_ms=5 * H)])
    assert w.estimate(w.alice)["usd"] == pytest.approx(2.00)


def test_estimate_skips_a_newer_run_it_cannot_price(w):
    # TC-030
    w.run("older", w.alice, tasks=_hours(5), started="2026-08-01T00:00:00Z")
    w.run("newer", w.alice, tasks=[_task(machine_type="c9-fake-8")], started="2026-09-01T00:00:00Z")
    est = w.estimate(w.alice)
    assert est["usd"] == pytest.approx(1.00) and "older" in est["basis"]


def test_no_history_means_unknown_estimate_not_a_guess(w):
    # TC-031, TC-032 (T7)
    w.run("slurm", w.alice, ce="nano4", platform="slurm-platform", tasks=_hours(4))
    est = w.estimate(w.alice)
    assert est["usd"] is None and est["basis"] is None
    assert "還沒有成功跑過" in " ".join(est["unknown_reasons"])
    # resourceLimits / maxvCpus never produce a number
    con = w.store.connect_state(w.plat)
    with con:
        con.execute("UPDATE compute_envs SET config_json = ? WHERE name = 'nano4'", (json.dumps({"maxvCpus": 64, "resourceLimits": {"cpus": 8}}),))
    con.close()
    assert w.estimate(w.alice)["usd"] is None


def test_an_old_index_without_the_machine_columns_is_unknown(tmp_path):
    # TC-033
    db = tmp_path / "old.db"
    con = sqlite3.connect(str(db))
    con.executescript("""CREATE TABLE runs (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, run_name TEXT NOT NULL, token_id INTEGER,
        source TEXT NOT NULL DEFAULT 'live', final_status TEXT, started_at INTEGER, ended_at INTEGER, last_message_at REAL NOT NULL,
        project_name TEXT, nextflow_version TEXT, exit_status INTEGER, params_json TEXT, failure_reason TEXT,
        n_succeeded INTEGER NOT NULL DEFAULT 0, n_cached INTEGER NOT NULL DEFAULT 0, n_failed INTEGER NOT NULL DEFAULT 0,
        n_aborted INTEGER NOT NULL DEFAULT 0, n_running INTEGER NOT NULL DEFAULT 0, n_pending INTEGER NOT NULL DEFAULT 0,
        n_submitted INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE task_usage (run_id TEXT NOT NULL, task_key TEXT NOT NULL, name TEXT NOT NULL, status TEXT, cpus INTEGER,
        realtime_ms INTEGER, queue TEXT, PRIMARY KEY (run_id, task_key));
        INSERT INTO runs (id, session_id, run_name, final_status, started_at, last_message_at) VALUES ('id-o', 's', 'o', 'succeeded', 1790000000, 3);
        INSERT INTO task_usage VALUES ('id-o', '1:1', 'A', 'COMPLETED', 1, 3600000, NULL);""")
    con.close()
    out = _cc().run_tasks_cost(db, "o", RATES)
    assert out["usd"] is None and "這個 run 的紀錄沒有保存機器型號" in " ".join(out["unknown_reasons"])
    con = sqlite3.connect(str(db))
    assert "machine_type" not in {r[1] for r in con.execute("PRAGMA table_info(task_usage)")}      # reading never changes the file
    con.close()


def test_a_run_with_no_task_rows_is_unknown(w):
    w.run("r", w.alice, tasks=[])
    assert w.cost("r")["usd"] is None
    assert w.cost("no-such-run")["usd"] is None


def test_the_region_falls_back_to_the_location_of_the_environment(w):
    # TC-034, TC-035
    nozone = [_task(zone=...)]
    w.run("with-loc", w.alice, tasks=nozone, ce="gcb-loc", location="us-central1", started="2026-10-02T00:00:00Z")
    w.run("no-loc", w.alice, tasks=nozone, ce="gcb-noloc", started="2026-10-03T00:00:00Z")
    assert w.cost("with-loc")["usd"] is None          # the run alone cannot name its region; month_used and estimate_launch add the location
    used = w.used(w.alice)
    assert used["usd"] == pytest.approx(2.00) and used["unknown_runs"] == 1
    w.run("hist", w.alice, tasks=nozone, ce="gcb-loc", location="us-central1", started="2026-08-03T00:00:00Z", pipeline="nf-core/q")
    assert w.estimate(w.alice, "nf-core/q")["usd"] == pytest.approx(2.00)
    w.run("hist2", w.alice, tasks=nozone, ce="gcb-noloc", started="2026-08-03T00:00:00Z", pipeline="nf-core/r")
    est = w.estimate(w.alice, "nf-core/r")
    assert est["usd"] is None


def test_month_used_counts_only_this_user_this_month_and_cloud_runs(w):
    # TC-036 ... TC-039, TC-041 (T9)
    w.run("edge", w.alice, tasks=_hours(10), started="2026-09-30T16:30:00Z")       # 2026-10-01 00:30 in Taipei
    w.run("bobs", w.bob, tasks=_hours(10), started="2026-10-05T00:00:00Z")
    w.run("slurm", w.alice, ce="nano4", platform="slurm-platform", tasks=_hours(10), started="2026-10-06T00:00:00Z")
    assert w.used(w.alice, "2026-10")["usd"] == pytest.approx(2.00)
    assert w.used(w.alice, "2026-09")["usd"] == pytest.approx(0.0)
    w.run("fail", w.alice, tasks=[_task(status="FAILED", realtime_ms=5 * H)], status="failed", started="2026-10-07T00:00:00Z")
    assert w.used(w.alice, "2026-10")["usd"] == pytest.approx(3.00)


def test_a_run_sent_to_the_cloud_and_then_to_slurm_is_not_a_cloud_run(w):
    # TC-040
    w.run("moved", w.alice, tasks=_hours(10), started="2026-10-05T00:00:00Z", launches=[("gcb1", "nf-core/x"), ("nano4", "nf-core/x")])
    w.ce("nano4", "slurm-platform")
    assert w.used(w.alice)["usd"] == pytest.approx(0.0)


def test_one_run_that_cannot_be_priced_does_not_make_the_month_unknown(w):
    # TC-042
    w.run("ok", w.alice, tasks=_hours(15), started="2026-10-05T00:00:00Z")
    w.run("bad", w.alice, tasks=[_task(machine_type="c9-fake-8")], started="2026-10-06T00:00:00Z")
    used = w.used(w.alice)
    assert used["usd"] == pytest.approx(3.00) and used["unknown_runs"] == 1


# ---- US3: the cap ----------------------------------------------------------------------------------------------------

def _scene(w, user, used, estimate, cap=20.0, extra_unknown=False):
    """This month `used` dollars (one failed run, so it is never the basis) and an `estimate` from an earlier month's success."""
    w.run("used-%s" % w.n, user, tasks=_hours(used / 0.20), status="failed", started="2026-10-05T00:00:00Z")
    if estimate is not None:
        w.run("basis-%s" % w.n, user, tasks=_hours(estimate / 0.20), started="2026-09-05T00:00:00Z")
    if extra_unknown:
        w.run("unk-%s" % w.n, user, tasks=[_task(machine_type="c9-fake-8")], status="failed", started="2026-10-06T00:00:00Z")
    if cap is not None:
        w.cap(user, cap)


@pytest.mark.parametrize("used, est, cap, refused", [
    (14.50, 2.00, 20.0, False),     # TC-043
    (14.50, 6.00, 20.0, True),      # TC-044
    (14.50, 5.50, 20.0, False),     # TC-046
    (20.00, None, 20.0, True),      # TC-047
    (14.50, None, 20.0, False),     # TC-049
    (0.0, 1.0, 0.0, True),          # TC-050
])
def test_cap_check_numbers(w, used, est, cap, refused):
    # TC-043 ... TC-050 (T8)
    _scene(w, w.alice, used, est, cap)
    out = w.ask(w.alice)
    assert (out is not None) == refused, out


def test_the_refusal_says_the_numbers_and_what_to_do(w):
    # TC-044, TC-045, TC-053
    _scene(w, w.alice, 14.50, 6.00)
    text = w.ask(w.alice)
    for s in ("US$20.00", "US$14.50", "US$5.50", "US$6.00"):
        assert s in text
    assert "超過" in text and "管理者" in text and "下個月" in text
    assert not re.findall(r"US\$\d+(?!\.\d\d)\b", text) and not re.findall(r"\$\d+\.\d{3,}", text)


def test_a_used_up_month_is_refused_whatever_the_estimate(w):
    # TC-047, TC-048
    _scene(w, w.alice, 20.00, None)
    text = w.ask(w.alice)
    assert "US$20.00" in text and "US$0.00" in text and "不能再送出" in text


def test_no_cap_set_means_no_cloud_launch(w):
    # TC-051
    _scene(w, w.alice, 0.2, 1.0, cap=None)
    text = w.ask(w.alice)
    assert text and "cloud-cap" in text and "管理者" in text


def test_with_the_empty_shipped_rates_the_cap_still_works(w):
    # TC-136 (裁決四 10, 13)
    rates = _cc().load_rates(SHIPPED)
    _scene(w, w.alice, 0.2, 1.0, cap=5.0)
    assert w.ask(w.alice, rates=rates) is None
    w.cap(w.alice, 0)
    assert w.ask(w.alice, rates=rates)
    text = w.ask(w.bob, rates=rates)
    assert text and "cloud-cap" in text and "Traceback" not in text


def test_unpriced_runs_make_the_used_figure_a_floor(w):
    # TC-052
    _scene(w, w.alice, 14.50, 6.00, extra_unknown=True)
    text = w.ask(w.alice)
    assert "至少" in text and "1 個 run" in text


def test_the_estimate_comes_from_the_pipeline_the_bundle_names(w):
    # TC-056
    w.run("a-hist", w.alice, pipeline="pipe-a", tasks=_hours(10), started="2026-09-05T00:00:00Z")
    w.run("b-hist", w.alice, pipeline="pipe-b", tasks=_hours(45), started="2026-09-06T00:00:00Z")
    w.run("used", w.alice, tasks=_hours(70), status="failed", started="2026-10-05T00:00:00Z")
    w.cap(w.alice, 20)
    assert w.ask(w.alice, "pipe-a") is None
    assert w.ask(w.alice, "pipe-b") is not None


def test_a_slurm_launch_never_reads_the_rates_or_the_cap(w, monkeypatch):
    # TC-054, TC-055 (T12)
    from abf_platform import status
    cc = _cc()
    w.ce("nano4", "slurm-platform")
    w.ce("aws1", "awsbatch-platform")

    def boom(*a, **k):
        raise AssertionError("must not be called")
    for target, name in ((cc, "load_rates"), (w.store, "cloud_cap"), (w.store, "connect_tokens"), (w.store, "connect_index"),
                         (status, "_open_readonly")):
        monkeypatch.setattr(target, name, boom)
    assert w.ask(w.alice, ce="nano4", rates=None) is None
    assert w.ask(w.alice, ce="aws1", rates=None) is None
    assert w.ask(w.alice, ce="gone-env", rates=None) is None


def test_one_person_does_not_use_another_persons_cap(w):
    # TC-057, TC-058
    _scene(w, w.alice, 19.90, 1.0)
    w.run("bob-used", w.bob, tasks=_hours(1), status="failed", started="2026-10-05T00:00:00Z")
    w.run("bob-hist", w.bob, tasks=_hours(1), started="2026-09-05T00:00:00Z")
    w.cap(w.bob, 20)
    assert w.ask(w.alice) is not None
    assert w.ask(w.bob) is None
    con = sqlite3.connect(str(w.tokens))
    con.execute("DELETE FROM cloud_caps WHERE user_id = ?", (w.bob,))
    con.commit()
    con.close()
    assert "cloud-cap" in w.ask(w.bob)


def _counts(w):
    out = {}
    for path, tables in ((w.plat, ("jobs", "confirmations", "launches")), (w.index, ("task_usage", "runs")), (w.tokens, ("cloud_caps", "users"))):
        con = sqlite3.connect(str(path))
        for t in tables:
            out[t] = con.execute("SELECT * FROM %s ORDER BY 1" % t).fetchall()
        con.close()
    return out


def test_asking_changes_nothing(w):
    # TC-059, TC-097
    _scene(w, w.alice, 14.50, 6.00)
    w.run("running", w.alice, tasks=_hours(1), status="running", started="2026-10-08T00:00:00Z")
    before = _counts(w)
    assert w.ask(w.alice) is not None
    w.cap(w.alice, 30)
    mid = _counts(w)
    assert w.ask(w.alice) is None
    assert {k: v for k, v in mid.items() if k != "cloud_caps"} == {k: v for k, v in before.items() if k != "cloud_caps"}
    assert _counts(w) == mid
    assert not w.store.connect_state(w.plat).execute("SELECT 1 FROM jobs").fetchall()


def test_no_secret_or_path_in_the_refusal(w, tmp_path):
    # TC-060 (T17)
    texts = []
    _scene(w, w.alice, 14.50, 6.00, extra_unknown=True)
    texts.append(w.ask(w.alice))
    _scene(w, w.bob, 20.0, None, cap=None)
    texts.append(w.ask(w.bob))
    for t in texts:
        assert t
        for bad in ("Traceback", "SELECT", ".db", str(tmp_path), "abf_pat_", "token"):
            assert bad not in t
        assert not re.search(r"[A-Za-z]:[\\/]|/tmp|\\", t)


def test_the_words_of_the_refusals_have_no_other_currency(w):
    # TC-099
    _scene(w, w.alice, 14.50, 6.00)
    _scene(w, w.bob, 1.0, None, cap=None)
    for t in (w.ask(w.alice), w.ask(w.bob)):
        for word in ("NT$", "TWD", "新台幣", "匯率", "exchange rate"):
            assert word not in t


# ---- US4: only the administrator sets a cap --------------------------------------------------------------------------

def _env(tmp_path):
    return pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db")


def _cap_of(tmp_path, name):
    from abf_platform import store
    tokens = tmp_path / "data" / "tokens.db"
    uid = store.user_id_of(tokens, name)
    return None if uid is None else store.cloud_cap(tokens, uid)


def test_the_admin_commands_set_and_change_a_cap(tmp_path):
    # TC-061, TC-062, TC-063, TC-070, TC-071
    env = _env(tmp_path)
    assert run_cli(["user", "add", "alice", "--lab", "x", "--cloud-cap-usd", "20"], env=env).returncode == 0
    assert _cap_of(tmp_path, "alice") == 20.0
    assert run_cli(["user", "cloud-cap", "alice", "25"], env=env).returncode == 0
    assert _cap_of(tmp_path, "alice") == 25.0
    assert run_cli(["user", "add", "carol", "--lab", "x"], env=env).returncode == 0
    assert _cap_of(tmp_path, "carol") is None
    assert run_cli(["user", "cloud-cap", "alice", "1000000"], env=env).returncode == 0
    assert _cap_of(tmp_path, "alice") == 1000000.0
    assert run_cli(["user", "cloud-cap", "alice", "0"], env=env).returncode == 0
    assert _cap_of(tmp_path, "alice") == 0.0


@pytest.mark.parametrize("bad", ["-1", "abc", "nan", "inf", "1e9", "1000001", "-0.5", ""])
def test_a_bad_cap_is_refused_in_plain_words_and_nothing_changes(tmp_path, bad):
    # TC-064 ... TC-069, TC-072
    env = _env(tmp_path)
    run_cli(["user", "add", "alice", "--lab", "x", "--cloud-cap-usd", "20"], env=env)
    r = run_cli(["user", "cloud-cap", "alice", bad], env=env)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "1,000,000" in out and "0" in out
    for leak in ("Traceback", "SELECT", ".db", str(tmp_path)):
        assert leak not in out
    assert _cap_of(tmp_path, "alice") == 20.0


def test_a_bad_cap_at_user_add_creates_no_account(tmp_path):
    # TC-073
    env = _env(tmp_path)
    r = run_cli(["user", "add", "newbie", "--lab", "x", "--cloud-cap-usd", "abc"], env=env)
    assert r.returncode != 0
    assert _cap_of(tmp_path, "newbie") is None
    from abf_platform import store
    tokens = tmp_path / "data" / "tokens.db"
    assert not tokens.exists() or store.user_id_of(tokens, "newbie") is None


def test_cloud_cap_for_an_unknown_user_is_refused(tmp_path):
    r = run_cli(["user", "cloud-cap", "nobody", "5"], env=_env(tmp_path))
    assert r.returncode != 0 and "Traceback" not in r.stderr


DOOR = re.compile(r"cloud_cap|cloud-cap|cap_usd", re.I)


def test_no_user_door_to_the_cap(tmp_path):
    # TC-074, TC-075, TC-076, TC-077, TC-078 (T11 part 3 and 4)
    from abf_platform import actions, web
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    # tool count is pinned elsewhere (test_oauth_mcp etc.); here only: no tool is a door to the cap
    assert names and not [n for n in names if DOOR.search(n)]
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if DOOR.search(getattr(r, "path", ""))]
    assert not [n for n in dir(actions) if not n.startswith("_") and (DOOR.search(n) or "cloud" in n.lower())]
    # nothing but the store, the cost module and the administrator command line knows the cap
    allowed = {"store.py", "cloud_cost.py", "cli.py"}
    knows = [p.name for p in PKG.rglob("*.py") if p.name not in allowed and re.search(r"cloud_caps?\b|cap_usd|cloud-cap", p.read_text(encoding="utf-8"))]
    assert knows == []
    # a field with the cap's name changes nothing through the web
    from starlette.testclient import TestClient
    from abf_platform import store
    store.connect_tokens(tmp_path / "tokens.db").close()
    uid = store.create_user(tmp_path / "tokens.db", "mallory", "lab")
    store.set_cloud_cap(tmp_path / "tokens.db", uid, 777.77)
    client = TestClient(app, raise_server_exceptions=False)
    for path in ("/", "/settings", "/launch", "/act/launch", "/login"):
        for method in ("GET", "POST"):
            r = client.request(method, path, data={"cloud_cap_usd": "1", "cap_usd": "1"}, follow_redirects=False)
            assert "777.77" not in r.text
    assert store.cloud_cap(tmp_path / "tokens.db", uid) == 777.77


def test_the_cap_is_never_read_back_by_any_existing_door(tmp_path):
    # TC-077: the number is only in the store and the cost module
    from abf_platform import store
    tokens = tmp_path / "tokens.db"
    uid = store.create_user(tokens, "alice", "lab")
    store.set_cloud_cap(tokens, uid, 777.77)
    for p in PKG.rglob("*.py"):
        if p.name in ("store.py", "cloud_cost.py", "cli.py"):
            continue
        assert "cloud_caps" not in p.read_text(encoding="utf-8"), p.name


# ---- US5: the receiver and the migrations ----------------------------------------------------------------------------

def _send(plat, token, tasks, run="r1"):
    wid = plat.send("POST", "/trace/create", {"runName": run, "sessionId": "s-" + run, "projectName": "p"}, token=token).json()["workflowId"]
    r = plat.send("PUT", "/trace/%s/progress" % wid, {"progress": {}, "tasks": tasks}, token=token)
    assert r.status_code == 200, r.text
    return wid


def _usage(plat, wid):
    con = sqlite3.connect(str(plat.index))
    try:
        return con.execute("SELECT task_key, cpus, realtime_ms, queue, machine_type, price_model, cloud_zone FROM task_usage "
                           "WHERE run_id = ? ORDER BY task_key", (wid,)).fetchall()
    finally:
        con.close()


def _ev(i=1, **kw):
    d = {"taskId": i, "attempt": 1, "name": "A (%d)" % i, "status": "COMPLETED", "cpus": 4, "realtime": 1234, "queue": "q"}
    d.update(kw)
    return d


def test_receiver_keeps_machine_type_price_model_and_zone(tmp_path):
    # TC-080, TC-081, TC-082, TC-083, TC-084, TC-085, TC-086 (T15)
    plat = Platform(tmp_path)
    token = plat.new_token()
    wid = _send(plat, token, [
        _ev(1, machineType="n2-standard-4", priceModel="spot", cloudZone="us-central1-a"),
        _ev(2, machineType=None, priceModel=None, cloudZone=None),
        _ev(3, machineType=7, priceModel=["spot"], cloudZone={"a": 1}),
        _ev(4, machineType="m" * 100, priceModel="p" * 100, cloudZone="z" * 100),
        _ev(5),
    ])
    rows = {r[0]: r for r in _usage(plat, wid)}
    assert rows["1:1"] == ("1:1", 4, 1234, "q", "n2-standard-4", "spot", "us-central1-a")
    assert rows["2:1"][4:] == (None, None, None)
    assert rows["3:1"][4:] == (None, None, None)
    assert rows["4:1"][4:] == ("m" * 64, "p" * 64, "z" * 64)
    assert rows["5:1"][1:4] == (4, 1234, "q") and rows["5:1"][4:] == (None, None, None)


def test_the_task_usage_table_has_exactly_three_new_columns(tmp_path):
    # TC-087
    from abf_platform import store
    store.init_index(tmp_path / "i.db")
    con = sqlite3.connect(str(tmp_path / "i.db"))
    cols = [r[1] for r in con.execute("PRAGMA table_info(task_usage)")]
    con.close()
    assert cols == ["run_id", "task_key", "name", "status", "cpus", "realtime_ms", "queue", "machine_type", "price_model", "cloud_zone"]


def _old_index(path):
    con = sqlite3.connect(str(path))
    con.executescript("""CREATE TABLE task_usage (run_id TEXT NOT NULL, task_key TEXT NOT NULL, name TEXT NOT NULL, status TEXT,
        cpus INTEGER, realtime_ms INTEGER, queue TEXT, PRIMARY KEY (run_id, task_key));
        INSERT INTO task_usage VALUES ('r', '1:1', 'A', 'COMPLETED', 2, 99, 'qq');""")
    con.commit()
    con.close()


def test_an_older_database_gets_the_new_columns_and_the_new_table(tmp_path):
    # TC-088, TC-089, TC-091 (T16)
    from abf_platform import store
    _old_index(tmp_path / "i.db")
    store.init_index(tmp_path / "i.db")
    con = sqlite3.connect(str(tmp_path / "i.db"))
    assert {"machine_type", "price_model", "cloud_zone"} <= {r[1] for r in con.execute("PRAGMA table_info(task_usage)")}
    assert con.execute("SELECT run_id, task_key, name, status, cpus, realtime_ms, queue, machine_type, price_model, cloud_zone "
                       "FROM task_usage").fetchall() == [("r", "1:1", "A", "COMPLETED", 2, 99, "qq", None, None, None)]
    con.close()
    old = re.sub(r"CREATE TABLE IF NOT EXISTS cloud_caps \(.*?\);", "", store.TOKEN_SCHEMA, flags=re.S)
    assert "cloud_caps" not in old
    con = sqlite3.connect(str(tmp_path / "t.db"))
    con.executescript(old)
    con.close()
    store.connect_tokens(tmp_path / "t.db").close()
    con = sqlite3.connect(str(tmp_path / "t.db"))
    assert [r[1] for r in con.execute("PRAGMA table_info(cloud_caps)")] == ["user_id", "cap_usd", "set_at"]
    con.close()


def test_two_processes_upgrading_at_once_do_not_fail(tmp_path):
    # TC-090
    from abf_platform import store
    _old_index(tmp_path / "i.db")
    barrier, errors = threading.Barrier(4), []

    def go():
        try:
            barrier.wait()
            store.init_index(tmp_path / "i.db")
        except Exception as e:      # noqa: BLE001
            errors.append(e)
    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errors == []


# ---- US6: what is not done -------------------------------------------------------------------------------------------

def _pkg_text():
    return {p.name: p.read_text(encoding="utf-8") for p in PKG.rglob("*.py")}


def test_nothing_stops_a_running_job_and_no_policy_channel_exists():
    # TC-093 ... TC-096 (T13)
    texts = _pkg_text()
    for name, text in texts.items():
        assert "watchdog" not in text.lower() and "POLICY" not in text, name
    kinds = re.search(r"CHECK \(kind IN \(('preflight'[^)]*)\)\)", (PKG / "store.py").read_text(encoding="utf-8")).group(1)
    assert [k.strip(" '") for k in kinds.split(",")] == ["preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records",
                                                         "read_task_log", "clean_work", "put_upload", "pipeline_files"]
    assert "kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel', 'clean_work'))" in (PKG / "store.py").read_text(encoding="utf-8")
    for word in ("enqueue_cancel", "cancel_run"):
        assert word not in texts["cloud_cost.py"]


def test_no_other_currency_in_the_source_or_the_rates():
    # TC-098
    for text in (_pkg_text()["cloud_cost.py"], SHIPPED.read_text(encoding="utf-8")):
        for word in ("NT$", "TWD", "新台幣", "匯率", "exchange rate"):
            assert word not in text


def test_the_scope_stays_small():
    # TC-101, TC-102 (T14)
    assert "google-cloud" not in (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    for name, text in _pkg_text().items():
        assert not re.search(r"^\s*(import|from)\s+(google|boto3)\b", text, re.M), name


# ---- US7: the documents ----------------------------------------------------------------------------------------------

DOC = REPO_ROOT / "docs" / "CLOUD.md"


def test_the_cloud_document_says_what_it_must():
    # TC-100, TC-107 ... TC-113, TC-120, TC-121 (T10, T18)
    text = DOC.read_text(encoding="utf-8")
    assert "NT$" not in text and not re.search(r"[0-9][0-9,.]*\s*(元|塊)?\s*台幣|台幣\s*[0-9]", text)
    assert "只含運算" in text and "約" in text
    assert "同一個 pipeline" in text and "最近一次成功" in text
    assert "user add" in text and "--cloud-cap-usd" in text and "user cloud-cap" in text
    assert "不會自動停止正在跑的雲端工作" in text and "只會擋下新的送出" in text
    assert "台幣" in text and "帳單預算" in text
    assert "cloud_rates.json" in text and "source" in text and "read_on" in text and "https://" in text and "YYYY-MM-DD" in text
    assert "太平洋時間" in text and "台北時間" in text
    assert "第一次" in text and "擋不住" in text
    for word in ("新台幣", "匯率", "exchange rate"):
        assert word not in text


def test_the_new_python_files_name_what_they_are_not_in_their_first_forty_lines():
    # TC-122
    for path in (PKG / "cloud_cost.py", Path(__file__)):
        lines = path.read_text(encoding="utf-8").splitlines()[:40]
        hit = [ln for ln in lines if ln.startswith("# Nothing existing:")]
        assert hit and len(hit[0].split(":", 1)[1].strip()) >= 15, path.name


def _shipped_rates_are_empty():
    return not json.loads(SHIPPED.read_text(encoding="utf-8"))["regions"]


def test_empty_rates_never_count_used_money_so_the_monthly_cap_cannot_fill(w):
    # cloud-cap-empty-rates-doc: TC-009, TC-010
    if not _shipped_rates_are_empty():
        pytest.skip("price list is filled; this pins the empty-list behaviour")
    rates = _cc().load_rates(SHIPPED)
    assert not rates.get("regions")
    w.run("used-a", w.alice, tasks=_hours(40), status="failed", started="2026-10-05T00:00:00Z")
    w.run("used-b", w.alice, tasks=_hours(40), status="failed", started="2026-10-06T00:00:00Z")
    w.cap(w.alice, 5.0)
    used = w.used(w.alice, rates=rates)
    assert used["usd"] == 0 and used["unknown_runs"] >= 1
    assert w.ask(w.alice, rates=rates) is None


def test_cloud_doc_does_not_claim_the_monthly_cap_works_while_the_price_list_is_empty():
    # cloud-cap-empty-rates-doc: TC-001 ... TC-004, TC-008
    if not _shipped_rates_are_empty():
        pytest.skip("price list is filled; these sentences are meant to be rewritten then")
    zh, en = "要等價目表填入後才會生效", "only takes effect once the price list is filled in"
    cloud = DOC.read_text(encoding="utf-8")
    for ln in cloud.splitlines():
        if "價目表" in ln and "空的" in ln and "已用滿" in ln:
            assert zh in ln, ln
    assert zh in cloud
    testing = (REPO_ROOT / "docs" / "TESTING.md").read_text(encoding="utf-8")
    for ln in testing.splitlines():
        if "empty price list" in ln and "used up" in ln:
            assert en in ln, ln
    assert en in testing
