# Nothing existing: the cap and the estimate of cloud-cost are modules nobody calls yet; a launch check before anything is made, and a screen line that tells the truth, are ours to test.
"""cloud-cost-wire: the monthly cloud cap is looked at before a launch to Google Batch makes anything, and the launch screen has one line
that says what this launch is estimated to cost, or why that cannot be said. Test cases TC-001 ... TC-074 are named in the comments
(W, B, C, K numbers are those of specs/cloud-cost-wire/plan.md). Everything here uses a made-up price list and databases in tmp_path:
no network, no program is started."""
import asyncio
import inspect
import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

from helpers import REPO_ROOT
from test_cloud_cost import NOW, RATES, World, _hours, _task
from test_gcb_ce import create, ip, set_status  # noqa: F401
from test_gcb_launch import SHEET, box, sheet_file  # noqa: F401

TAIL = "平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。"
KNOWN = ("費用預估：約 US$%.2f（依你最近一次成功的同管線雲端 %s 的實際運算時間推算；只含虛擬機運算費用，不含磁碟與網路；價目讀於 %s）。"
         + TAIL)
UNKNOWN = "費用預估：無法預估（%s）。" + TAIL
NO_COST = UNKNOWN % "這個送出入口沒有算預估 (this way of sending does not work out an estimate)"
PIPE = "nf-core/rnaseq"
THIS_FILE = Path(__file__).resolve()
EMPTY_RATES = {"currency": "USD", "regions": {}}


def _build():
    from abf_launch import build
    return build


def _cost():
    from abf_platform import cloud_cost
    return cloud_cost


def _actions():
    from abf_platform import actions
    return actions


class Wire(World):
    """The World of test_cloud_cost on the databases of an in-process platform, plus Google Batch environments people may launch on."""

    def __init__(self, ip, box, monkeypatch):
        from abf_platform import store
        self.store, self.ip, self.box, self.mp, self.n = store, ip, box, monkeypatch, 0
        self.index, self.plat, self.tokens = ip.index, ip.state_db, ip.tokens
        store.init_index(self.index)
        store.init_state(self.plat)
        store.connect_tokens(self.tokens).close()
        self.alice = store.create_user(self.tokens, "alice", "lab")
        self.bob = store.create_user(self.tokens, "bob", "lab")
        monkeypatch.setattr("abf_platform.status.now", lambda: NOW)
        self.use_rates(RATES)

    def use_rates(self, rates):
        self.mp.setattr(_cost(), "load_rates", lambda *a, **k: rates)

    def caller(self, uid, name):
        return _actions().Caller(uid, name, "lab")

    def env(self, uid, name="gcb1", agent="a1"):
        """An available Google Batch environment of this user, with an agent of theirs that has said hello."""
        from abf_platform import agents
        agents.register(self.plat, agent, "0.1.0", time.time, facts=self.box.facts(), owner_user_id=uid)
        create(self.ip, name, agent=agent, owner_user_id=uid)
        set_status(self.ip, name, "available")
        return name

    def counts(self):
        con = sqlite3.connect(str(self.plat))
        try:
            return tuple(con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] for t in ("confirmations", "jobs", "launches"))
        finally:
            con.close()

    def launch(self, caller, ce="gcb1", run="run-w", **kw):
        kw.setdefault("samplesheet_text", "\n".join(",".join(r) for r in SHEET) + "\n")
        return asyncio.run(_actions().request_launch(self.plat, pipeline=PIPE, revision="3.14.0", run_name=run, ce_name=ce,
                                                     params={"genome": "GRCh38"}, caller=caller, **kw))

    def used(self, uid, hours, name="used"):
        """`hours` of cloud time this month on another pipeline, so that it is spend and not the basis of an estimate."""
        self.run(name, uid, pipeline="nf-core/other", tasks=_hours(hours), started="2026-10-05T00:00:00Z")

    def basis(self, uid, hours, name="basis", started="2026-09-10T00:00:00Z"):
        """The latest successful run of the launched pipeline, last month: the estimate is its cost."""
        self.run(name, uid, pipeline=PIPE, tasks=_hours(hours), started=started)


@pytest.fixture
def w(ip, box, monkeypatch):
    return Wire(ip, box, monkeypatch)


def line3(out):
    """The cost line of a summary (the third line)."""
    return out["summary"].split("\n")[2]


def never(*a, **k):
    raise AssertionError("this must not be called")


def plain(lines):
    return [ln[2:] if ln.startswith("| ") else ln for ln in lines]


# ---- US1: refused before anything is created -------------------------------------------------------------------------

def test_over_the_cap_is_refused_before_anything_is_created(w, monkeypatch):
    # TC-001, TC-002 (W1)
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    w.used(uid, 72.5)             # 14.50
    w.basis(uid, 30)              # 6.00
    monkeypatch.setattr(_actions(), "_ask", never)
    monkeypatch.setattr(_build(), "launch_screen", never)
    before = w.counts()
    out = w.launch(w.caller(uid, "alice"))
    assert out["ok"] is False and out["sent"] is False
    msg = out["message"]
    assert msg.startswith("未送出：")
    for needle in ("US$20.00", "US$14.50", "US$5.50", "US$6.00", "請找管理者調整上限"):
        assert needle in msg, needle
    assert w.counts() == before


def test_a_month_already_used_up_is_refused_whatever_the_estimate(w):
    # TC-003 (W2)
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    w.used(uid, 100)              # 20.00 = the cap; no basis run: the estimate cannot be worked out
    before = w.counts()
    out = w.launch(w.caller(uid, "alice"))
    assert out["ok"] is False and "不能再送出新的雲端分析" in out["message"]
    assert w.counts() == before


def test_a_person_with_no_cap_cannot_launch_to_the_cloud(w):
    # TC-004 (W3)
    uid = w.alice
    w.env(uid)
    before = w.counts()
    out = w.launch(w.caller(uid, "alice"))
    assert out["ok"] is False and out["sent"] is False and out["message"].startswith("未送出：") and "cloud-cap" in out["message"]
    assert w.counts() == before


def test_a_cap_of_zero_refuses(w):
    # TC-005 (W4)
    uid = w.alice
    w.env(uid)
    w.cap(uid, 0)
    before = w.counts()
    out = w.launch(w.caller(uid, "alice"))
    assert out["ok"] is False and out["sent"] is False and out["message"].startswith("未送出：")
    assert w.counts() == before


def test_exactly_at_the_cap_goes_on_to_the_screen(w):
    # TC-006 (W5)
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    w.used(uid, 72.5)             # 14.50
    w.basis(uid, 27.5)            # 5.50: together exactly 20.00
    before = w.counts()
    out = w.launch(w.caller(uid, "alice"))
    assert out["state"] == "pending" and out["confirmation_url"]
    assert w.counts()[0] == before[0] + 1
    assert "費用預估：約 US$5.50" in out["summary"]


def test_an_estimate_that_fits_shows_its_line_on_the_screen(w):
    # TC-019, TC-020, TC-033 (W6)
    from abf_platform import common
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    w.used(uid, 72.5)
    w.basis(uid, 10)              # 2.00
    out = w.launch(w.caller(uid, "alice"))
    assert out["state"] == "pending"
    assert line3(out) == KNOWN % (2.00, "run basis", "2026-10-24")
    for word in ("本月已用", "已用", "剩"):
        assert word not in out["summary"]
    con = sqlite3.connect(str(w.plat))
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM confirmations WHERE id = ?", (out["id"],)).fetchone()
    con.close()
    assert row["screen_text"] == out["summary"]
    assert row["sha256"] == common.bundle_sha256(json.loads(row["bundle_json"]))
    assert "費用預估" not in row["bundle_json"]


def test_an_estimate_that_cannot_be_worked_out_is_allowed_and_says_so(w):
    # TC-023, TC-024, TC-070 (W7)
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    out = w.launch(w.caller(uid, "alice"))                      # no history at all
    assert out["state"] == "pending"
    assert "無法預估" in line3(out) and "還沒有成功跑過" in line3(out) and "US$" not in line3(out)
    w.basis(uid, 10)                                           # a history, but a price list with nothing in it (as shipped)
    w.use_rates(EMPTY_RATES)
    out = w.launch(w.caller(uid, "alice"), run="run-w2")
    assert out["state"] == "pending"
    assert "無法預估" in line3(out) and "尚未填入價目" in line3(out)
    assert "還沒有成功跑過" not in line3(out) and "US$" not in line3(out)


def test_the_run_name_is_judged_before_the_cap(w):
    # TC-011 (W8)
    from abf_platform import jobs
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    w.used(uid, 100)
    w.run("taken", uid, pipeline="nf-core/other", tasks=_hours(1), started="2026-09-01T00:00:00Z")
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_run_name(w.plat, "taken", time.time, uid)
    out = w.launch(w.caller(uid, "alice"), run="taken")
    assert out["message"] == "未送出：%s" % e.value and "US$" not in out["message"]


def test_the_composed_pipeline_entry_is_checked_the_same_way(w):
    # TC-012, TC-014 (W10, W14): both entries end in _finish_launch (test_pipeline_launch.py:486), so it is called directly
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    w.used(uid, 100)
    _, bundle = _build().prepare_launch(w.plat, ce="gcb1", pipeline=PIPE, revision="3.14.0", run_name="run-c",
                                        samplesheet=str(sheet_file(w.box.tmp)), params={"genome": "GRCh38"}, owner=uid)
    before = w.counts()
    out = asyncio.run(_actions()._finish_launch(w.plat, "gcb1", bundle, w.caller(uid, "alice"), None, time.time, False))
    assert out["ok"] is False and out["message"].startswith("未送出：") and "不能再送出新的雲端分析" in out["message"]
    assert w.counts() == before
    problem = _cost().cap_problem(w.plat, "gcb1", bundle, uid, index_path=w.index, tokens_path=w.tokens, rates=RATES, now=NOW)
    assert out["message"] == "未送出：" + problem


def test_one_person_over_the_cap_does_not_block_another(w):
    # TC-007 (W12)
    w.env(w.alice)
    w.env(w.bob, "gcb2", "a2")
    w.cap(w.alice, 20.00)
    w.cap(w.bob, 20.00)
    w.used(w.alice, 100)
    assert w.launch(w.caller(w.alice, "alice"))["ok"] is False
    out = w.launch(w.caller(w.bob, "bob"), ce="gcb2", run="run-b")
    assert out["state"] == "pending"


def test_the_yes_that_already_exists_is_not_checked_again(w):
    # TC-038 (W13)
    from abf_platform import confirm
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    first = w.launch(w.caller(uid, "alice"))
    assert first["state"] == "pending"
    confirm.approve(w.plat, first["id"], "PAGE", uid, time.time)
    w.cap(uid, 0)
    second = w.launch(w.caller(uid, "alice"))
    assert second["ok"] is True and second["sent"] is True and second["state"] == "queued" and "未送出" not in second["message"]
    con = sqlite3.connect(str(w.plat))
    n = con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'launch_nextflow'").fetchone()[0]
    con.close()
    assert n == 1


def test_no_secret_path_or_sql_in_the_refusal(w, tmp_path):
    # TC-008 (W15)
    w.env(w.alice)
    w.used(w.alice, 100)
    w.run("bobs", w.bob, tasks=_hours(1))
    w.cap(w.alice, 20.00)
    one = w.launch(w.caller(w.alice, "alice"))["message"]
    con = sqlite3.connect(str(w.tokens))
    with con:
        con.execute("DELETE FROM cloud_caps WHERE user_id = ?", (w.alice,))
    con.close()
    two = w.launch(w.caller(w.alice, "alice"), run="run-w2")["message"]
    assert one != two
    for msg in (one, two):
        for bad in ("Traceback", "SELECT", ".db", str(tmp_path), "abf_", "bob"):
            assert bad not in msg, bad


def test_the_words_of_the_refusal_and_the_screen_have_no_other_currency(w):
    # TC-009 (W16)
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    w.used(uid, 72.5)
    w.basis(uid, 30)
    texts = [w.launch(w.caller(uid, "alice"))["message"]]
    w.cap(uid, 100.00)
    texts.append(w.launch(w.caller(uid, "alice"), run="run-w2")["summary"])
    for t in texts:
        for bad in ("NT$", "TWD", "新台幣", "匯率", "exchange rate"):
            assert bad not in t, bad


# ---- US3: entries that are not checked --------------------------------------------------------------------------------

def test_a_slurm_launch_never_reads_the_cap_the_rates_or_the_index(monkeypatch, tmp_path):
    # TC-034 (W9)
    from human_harness import World as Human
    from abf_platform import store
    h = Human(tmp_path, monkeypatch)
    ann = h.user("ann")
    for name in ("cap_problem", "launch_estimate", "load_rates"):
        monkeypatch.setattr(_cost(), name, never, raising=False)
    monkeypatch.setattr(store, "cloud_cap", never)
    out = h.launch(caller=ann)
    assert out["state"] == "pending"
    pending = h.confirmations()[0]
    assert out["summary"] == "\n".join(plain(_build().launch_screen(json.loads(pending["bundle_json"]), "lab-a")))


def test_a_local_caller_without_an_account_is_not_checked_against_a_cap(w, monkeypatch):
    # TC-037 (W11)
    w.env(None)
    seen = []

    async def ask(platform_path, kind, ce_name, bundle, text, *a, **k):
        seen.append(text)
        return {"ok": True}

    monkeypatch.setattr(_actions(), "_ask", ask)
    monkeypatch.setattr(_cost(), "cap_problem", never)
    out = asyncio.run(_actions().request_launch(w.plat, pipeline=PIPE, revision="3.14.0", run_name="run-l", ce_name="gcb1",
                                                samplesheet=str(sheet_file(w.box.tmp)), params={"genome": "GRCh38"}, caller=None))
    assert out == {"ok": True}
    assert seen[0].split("\n")[2] == NO_COST


# ---- US2: the screen -------------------------------------------------------------------------------------------------

def test_the_first_line_no_longer_says_there_is_no_estimate(box):
    # TC-015, TC-050 (B1)
    lines = _build().launch_screen(box.bundle(), "gcb1")
    assert lines[1] == ("| 費用：按下 y 之後，這個 run 會在 Google Cloud 專案 lab-project-1 裡建立 Batch 工作與虛擬機，由 Google 向實驗室的 "
                        "Google Cloud 帳號收費。主控程序跑在平台主機上，取消請用平台的取消指令。")


def test_the_second_line_without_a_cost_is_the_plain_no_estimate_line(box):
    # TC-016, TC-017 (B2)
    lines = _build().launch_screen(box.bundle(), "gcb1")
    assert lines[2] == "| " + NO_COST and "無法預估" in lines[2] and "US$" not in lines[2]
    assert not re.search(r"NT\$|USD|US\$|TWD|[$＄￥¥€£]\s?[0-9]|[0-9]\s?(元|美元|台幣)", "\n".join(lines))


def test_a_known_cost_prints_two_decimals_the_basis_and_the_date(box):
    # TC-021, TC-022, TC-030 (B3)
    b = _build()
    cost = {"usd": 2.5, "basis": "run old-1", "as_of": "2026-10-24", "unknown_reasons": [], "currency": "USD"}
    assert b.launch_screen(box.bundle(), "gcb1", cost)[2] == "| " + KNOWN % (2.5, "run old-1", "2026-10-24")
    zero = b.launch_screen(box.bundle(), "gcb1", dict(cost, usd=0.0))[2]
    assert zero == "| " + KNOWN % (0.0, "run old-1", "2026-10-24") and "US$0.00" in zero
    assert "價目讀於 不明）" in b.launch_screen(box.bundle(), "gcb1", dict(cost, as_of=None))[2]


def test_an_unknown_cost_prints_the_first_reason(box):
    # TC-025, TC-026, TC-070 (B4)
    b = _build()
    line = b.launch_screen(box.bundle(), "gcb1", {"usd": None, "unknown_reasons": ["a", "b"]})[2]
    assert line == "| " + UNKNOWN % "a"
    empty = b.launch_screen(box.bundle(), "gcb1", {"usd": None, "unknown_reasons": []})
    assert "無法預估（原因不明 (reason unknown)）" in empty[2] and len(empty) == len(b.launch_screen(box.bundle(), "gcb1"))


def test_a_long_or_hostile_reason_is_escaped_and_cut(box):
    # TC-027, TC-028 (B5)
    b = _build()
    base = len(b.launch_screen(box.bundle(), "gcb1"))
    reason = "x\ny\x1b[31m" + "z" * 300
    lines = b.launch_screen(box.bundle(), "gcb1", {"usd": None, "unknown_reasons": [reason]})
    assert len(lines) == base
    line = lines[2]
    assert "\x1b" not in line and "\n" not in line and "\\n" in line and "\\x1b" in line
    assert "z" * 150 in line and "z" * 201 not in line
    assert line.endswith(TAIL)


def test_a_hostile_basis_cannot_break_the_screen(box):
    # TC-029 (B6)
    b = _build()
    base = len(b.launch_screen(box.bundle(), "gcb1"))
    cost = {"usd": 1.0, "basis": "run a\nb\x1b[31m", "as_of": "2026-10-24\n", "unknown_reasons": []}
    lines = b.launch_screen(box.bundle(), "gcb1", cost)
    assert len(lines) == base and "\x1b" not in lines[2] and "\n" not in lines[2] and "\\x1b" in lines[2]


def test_a_slurm_screen_does_not_look_at_the_cost():
    # TC-036 (B7)
    from test_launch_platform import bundle
    b = _build()
    assert b.launch_screen(bundle(), "lab-a", {"usd": 1.0}) == b.launch_screen(bundle(), "lab-a")


def test_no_file_still_says_there_is_no_estimate_and_cap():
    # TC-050 (B8): this file is left out by its path
    needles = ("還沒有費用預估與上限", "接線之前確認畫面仍寫")
    hits = []
    for top in ("platform", "docs", "README.md"):
        root = REPO_ROOT / top
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for p in files:
            if p.resolve() == THIS_FILE or {"__pycache__", ".git", "node_modules"} & set(p.parts) or p.suffix in (".pyc", ".db", ".png"):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if any(n in text for n in needles):
                hits.append(str(p))
    assert hits == []


# ---- US4: the estimate -------------------------------------------------------------------------------------------------

def test_launch_estimate_is_estimate_launch_with_the_defaults(w):
    # TC-041, TC-042, TC-047 (C1)
    w.mp.setenv("ABF_PLATFORM_DB", str(w.index))
    w.run("old", w.alice, pipeline=PIPE, tasks=_hours(5))
    c = _cost()
    got = c.launch_estimate(w.plat, {"pipeline": PIPE}, w.alice)
    assert got == c.estimate_launch(w.index, w.plat, w.alice, PIPE, RATES) and got["usd"] == pytest.approx(1.00)
    for bad in ({}, None, "x", {"pipeline": None}):
        out = c.launch_estimate(w.plat, bad, w.alice)
        assert out["usd"] is None and "還沒有成功跑過" in " ".join(out["unknown_reasons"])


def test_estimate_says_why_when_a_run_exists_but_cannot_be_priced(w):
    # TC-043 (C2)
    w.run("r", w.alice, pipeline=PIPE, tasks=_hours(5))
    out = w.estimate(w.alice, PIPE, rates=EMPTY_RATES)
    assert out["usd"] is None and out["basis"] is None
    reasons = " ".join(out["unknown_reasons"])
    assert "尚未填入價目" in reasons and "還沒有成功跑過" not in reasons


def test_estimate_still_says_no_history_when_there_is_no_candidate(w):
    # TC-044, TC-045 (C3)
    w.run("slurm", w.alice, pipeline=PIPE, ce="nano4", platform="slurm-platform", tasks=_hours(4))
    w.run("others", w.bob, pipeline=PIPE, tasks=_hours(1))
    w.run("failed", w.alice, pipeline=PIPE, status="failed", tasks=_hours(3), started="2026-09-22T00:00:00Z")
    w.run("other-pipe", w.alice, pipeline="nf-core/y", tasks=_hours(2), started="2026-09-21T00:00:00Z")
    out = w.estimate(w.alice, PIPE)
    assert out["usd"] is None and out["basis"] is None and "還沒有成功跑過" in " ".join(out["unknown_reasons"])
    w.run("bobs-z", w.bob, pipeline="nf-core/z", tasks=_hours(1))
    mine = w.estimate(w.alice, "nf-core/z")
    assert mine["usd"] is None and "還沒有成功跑過" in " ".join(mine["unknown_reasons"])


def test_a_priceable_older_run_still_beats_an_unpriceable_newer_one(w):
    # TC-046 (C4)
    w.mp.setenv("ABF_PLATFORM_DB", str(w.index))
    w.run("older", w.alice, pipeline=PIPE, tasks=_hours(5), started="2026-08-01T00:00:00Z")
    w.run("newer", w.alice, pipeline=PIPE, tasks=[_task(machine_type="c9-fake-8")], started="2026-09-01T00:00:00Z")
    out = _cost().launch_estimate(w.plat, {"pipeline": PIPE}, w.alice)
    assert out["usd"] == pytest.approx(1.00) and "older" in out["basis"]


# ---- the constitution and the scope ------------------------------------------------------------------------------------

def test_the_new_code_cannot_stop_anything():
    # TC-068 (K3)
    assert "cancel" not in inspect.getsource(_actions()._cloud_check)
    assert "cancel" not in inspect.getsource(_build().cost_line)
