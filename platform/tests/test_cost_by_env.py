# Nothing existing: tests of the cost page by compute environment and the cost row of the run page (specs/cost-page-by-environment); the page and its numbers are ours.
"""cost-page-by-environment: GET /usage is one expandable row per compute environment (unit follows the environment, nothing summed across them),
`actions.my_usage` has the new shape, `actions.run_usage` feeds the cost row of the run page. TC-NNN and envNN are named in the comments
(specs/cost-page-by-environment/test-case.md and plan.md)."""
import hashlib
import json
import re
import sqlite3
import time

import pytest

from helpers import PLATFORM_DIR
from test_web_board import no_cjk, pane, plain, style_of
from test_web_cost import H, cap, get, login, seed, usage, w  # noqa: F401  (w is the fixture)

PKG = PLATFORM_DIR / "abf_platform"
AWS = "awsbatch-platform"
NO_ESTIMATE = "尚無此環境的費用估算"
GONE = "環境紀錄已不存在 (the environment is no longer on record)"
V3_COLOURS = ['#0b5aa8', '#101214', '#14291c', '#15171a', '#15263a', '#1a2c3a', '#1b6837', '#1c5d8a', '#1e2125', '#1f2328', '#33270e', '#33373d',
              '#3a1916', '#575e66', '#646a73', '#78c792', '#7db8e2', '#80b6f2', '#865700', '#8f8b82', '#9cccf0', '#a2a8b0', '#b0261d', '#d6d3cc',
              '#e2b35e', '#e2edf5', '#e2f0e6', '#e3edf9', '#e9e7e2', '#ecebe6', '#f28b81', '#f6f5f2', '#f7edd6', '#fae6e3', '#ffffff']


def envs(w_, caller, **kw):
    return {e["name"]: e for e in usage(w_, caller, **kw)["environments"]}


def blocks(text):
    """[(open?, inner html)] of the environment rows of the middle pane."""
    return [(bool(o), inner) for o, inner in re.findall(r'<details class="pgroup env"( open)?>(.*?)</details>', pane(text, "middle"), re.S)]


def summary(inner):
    return plain(re.search(r"<summary>(.*?)</summary>", inner, re.S).group(1))


def block_of(text, name):
    return [b for b in blocks(text) if name in summary(b[1])][0]


def analysis_rows(inner):
    body = re.search(r"<tbody>(.*?)</tbody>", inner, re.S).group(1)
    return [[plain(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S)] for r in re.findall(r"<tr>(.*?)</tr>", body, re.S)]


def rates_file(w_, monkeypatch, tmp_path, mutate):
    from abf_platform import su
    rates = json.loads(su.RATES_PATH.read_text(encoding="utf-8"))
    mutate(rates)
    p = tmp_path / "su_rates_test.json"
    p.write_text(json.dumps(rates), encoding="utf-8")
    monkeypatch.setattr(su, "RATES_PATH", p)


def no_handoff(monkeypatch, *names):
    from abf_platform import cloud_cost
    real = cloud_cost._launch_facts
    monkeypatch.setattr(cloud_cost, "_launch_facts", lambda plat, name: None if name in names else real(plat, name))


# ---- US1: one row per environment ---------------------------------------------------------------------------------------

def test_env01_single_environment_is_one_open_row(w):
    # env01: TC-001, TC-002
    ann = w.user("ann")
    seed(w, "run-a", ann, hours=2, ce="slurm-a")
    seed(w, "run-b", ann, hours=3, ce="slurm-a")
    got = blocks(get(w, "ann").text)
    assert len(got) == 1 and got[0][0] is True
    assert "5.00 SU" in summary(got[0][1]) and "slurm-a" in summary(got[0][1]) and "共 2 個分析" in summary(got[0][1])
    assert envs(w, ann)["slurm-a"]["total"] == pytest.approx(5.0)


def test_env02_three_environments_nothing_added(w):
    # env02: TC-003, TC-004, TC-014, TC-028, TC-039, TC-040
    ann = w.user("ann")
    seed(w, "run-n", ann, hours=5, ce="slurm-a")
    seed(w, "run-c", ann, "cloud", hours=6, ce="gcb-a")
    seed(w, "run-w", ann, "nchc", ce="aws-a", platform=AWS)
    seed(w, "run-live", ann, status="running", ce="slurm-a")
    for url in ("/usage", "/usage?lang=en"):
        text = get(w, "ann", url).text
        got = blocks(text)
        assert len(got) == 3, url
        for _o, inner in got:
            if "gcb-a" in summary(inner) or "aws-a" in summary(inner):
                assert "SU" not in summary(inner), url
        outside = plain(re.sub(r'<details class="pgroup env".*?</details>', " ", pane(text, "middle"), flags=re.S))
        outside = re.sub(r"SU 以 \S+ 匯率概算為美元，並非帳單金額。|SU figures are converted to US dollars at the \S+ rate, roughly; this is not a bill\.", "", outside)
        assert not ("SU" in outside and "US$" in outside), url
        assert "國網" not in text and "雲端已用" not in text and "NCHC" not in text, url
    got = usage(w, ann)
    assert set(got) == {"month", "environments", "cloud"}
    assert {e["unit"] for e in got["environments"]} == {"SU", "USD"}
    keys = {"name", "kind", "unit", "site", "total", "usd_approx", "unknown_runs", "unknown_reasons", "analyses_count", "analyses", "usd_rate_as_of"}
    for e in got["environments"]:
        assert set(e) == keys and e["unit"] in ("SU", "USD", None)
        assert all(set(a) == {"name", "started_at", "state", "value", "usd_approx", "unknown_reasons"} for a in e["analyses"])
        assert (e["site"] is not None) == (e["unit"] == "SU")
    by = {e["name"]: e for e in got["environments"]}
    assert by["slurm-a"]["kind"] == "Slurm" and by["gcb-a"]["kind"] == "Google Cloud Batch" and by["gcb-a"]["site"] is None
    assert by["gcb-a"]["usd_approx"] is None and by["slurm-a"]["usd_approx"] is not None


def test_env02_summary_and_table_shape(w):
    # TC-005, TC-006, TC-007, TC-008, TC-009
    ann = w.user("ann")
    now = time.time()
    seed(w, "s-old", ann, hours=1, ce="slurm-a", started=now - 3000)
    seed(w, "s-mid", ann, hours=1, ce="slurm-a", started=now - 2000)
    seed(w, "s-new", ann, hours=1, ce="slurm-a", started=now - 1000)
    seed(w, "g-1", ann, "cloud", hours=1, ce="gcb-a", started=now - 500)
    seed(w, "a-1", ann, "nchc", ce="aws-a", platform=AWS, started=now - 100)
    text = get(w, "ann").text
    order = [re.search(r"aws-a|gcb-a|slurm-a", summary(i)).group(0) for _o, i in blocks(text)]
    assert order == ["aws-a", "gcb-a", "slurm-a"]
    inner = block_of(text, "slurm-a")[1]
    s = summary(inner)
    assert re.search(r"slurm-a\s+Slurm\s+3\.00 SU.*共 3 個分析", s) and "<a " not in re.search(r"<summary>.*?</summary>", inner, re.S).group(0)
    head = re.search(r"<thead>(.*?)</thead>", inner, re.S).group(1)
    assert '<table class="tbl">' in inner and [plain(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", head, re.S)] == ["分析名稱", "開始時間", "用量", "狀態"]
    assert [r[0] for r in analysis_rows(inner)] == ["s-new", "s-mid", "s-old"]
    en = block_of(get(w, "ann", "/usage?lang=en").text, "slurm-a")[1]
    assert [plain(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", re.search(r"<thead>(.*?)</thead>", en, re.S).group(1), re.S)] == ["Analysis", "Started", "Usage", "Status"]
    assert no_cjk(re.sub(r"slurm-a|s-\w+", "", en))
    for _o, i in blocks(text):
        assert "<script" not in i and not re.search(r"\son\w+\s*=", i)


def test_env02_environment_name_is_escaped(w):
    # TC-010
    ann = w.user("ann")
    seed(w, "run-a", ann, hours=1, ce="<b>x</b>")
    mid = pane(get(w, "ann").text, "middle")
    assert "&lt;b&gt;x&lt;/b&gt;" in mid and "<b>x</b>" not in mid


# ---- US2: unit follows the environment; nothing is booked to the wrong one ---------------------------------------------------

def test_env03_other_environments_never_count_as_slurm(w, monkeypatch):
    # env03: TC-020 ... TC-026, TC-035
    ann = w.user("ann")
    seed(w, "run-slurm", ann, hours=100, ce="slurm-a")
    seed(w, "run-aws", ann, "nchc", hours=7, ce="aws-a", platform=AWS)          # its task has cpus, realtime and queue, like a Slurm task
    seed(w, "run-az", ann, "nchc", ce="az-a", platform="azbatch-platform")
    seed(w, "run-k8s", ann, "nchc", ce="k8s-a", platform="k8s-platform")
    seed(w, "run-gone", ann, None, hours=3)
    seed(w, "run-lsf", ann, "nchc", ce="lsf-a", platform="lsf-platform")
    seed(w, "run-local", ann, "nchc", hours=2)
    no_handoff(monkeypatch, "run-local")
    got = usage(w, ann)
    assert "su" not in got and "runs" not in got
    by = {e["name"]: e for e in got["environments"]}
    assert by["slurm-a"]["total"] == pytest.approx(100.0) and by["slurm-a"]["analyses_count"] == 1
    for name in ("aws-a", "az-a", "k8s-a"):
        e = by[name]
        assert e["unit"] == "USD" and e["total"] is None and any(NO_ESTIMATE in x for x in e["unknown_reasons"]), name
        assert all("(" in x and re.search(r"\(no cost estimate", x) for x in e["unknown_reasons"])
    assert by["gone-ce"]["unit"] is None and by["gone-ce"]["total"] is None and any(GONE in x for x in by["gone-ce"]["unknown_reasons"])
    assert by["lsf-a"]["unit"] is None and by["lsf-a"]["analyses"][0]["value"] is None and by["lsf-a"]["analyses"][0]["unknown_reasons"]
    assert by[None]["unit"] is None and by[None]["total"] is None and by[None]["analyses"][0]["unknown_reasons"]
    text = get(w, "ann").text
    aws = summary(block_of(text, "aws-a")[1])
    assert "—" in aws and NO_ESTIMATE in aws
    assert "環境紀錄已不存在" in summary(block_of(text, "gone-ce")[1])                 # TC-025: the small text says why
    en = get(w, "ann", "/usage?lang=en").text
    assert "the environment is no longer on record" in summary(block_of(en, "gone-ce")[1]) and "no cost estimate" in summary(block_of(en, "aws-a")[1])
    mid = plain(pane(text, "middle"))
    assert "US$ 0.00" not in mid and not re.search(r"(?<![\d.])0(\.00)? SU", mid)
    for _o, inner in blocks(text):
        if "slurm-a" not in summary(inner):
            assert all(r[2] == "—" for r in analysis_rows(inner))


def test_env04_each_environment_uses_its_own_site(w, monkeypatch, tmp_path):
    # env04: TC-027
    def add(r):
        r["sites"]["siteA"] = {"partitions": {"ct56": {"factor": 1.0}}}
        r["sites"]["siteB"] = {"partitions": {"ct56": {"factor": 3.0}}}
    rates_file(w, monkeypatch, tmp_path, add)
    ann = w.user("ann")
    seed(w, "run-a", ann, hours=2, ce="slurm-a", config={"suSite": "siteA"})
    seed(w, "run-b", ann, hours=2, ce="slurm-b", config={"suSite": "siteB"})
    by = envs(w, ann)
    assert (by["slurm-a"]["site"], by["slurm-b"]["site"]) == ("siteA", "siteB")
    assert by["slurm-a"]["total"] == pytest.approx(2.0) and by["slurm-b"]["total"] == pytest.approx(6.0)
    for e in by.values():
        assert e["total"] == pytest.approx(sum(a["value"] for a in e["analyses"]))
    text = get(w, "ann").text
    assert "siteA" not in text and "siteB" not in text


def test_env04_dollar_beside_su_and_missing_rate_date(w, monkeypatch, tmp_path):
    # TC-016, TC-017, TC-069
    ann = w.user("ann")
    seed(w, "run-a", ann, hours=5.10, ce="slurm-a")
    e = envs(w, ann)["slurm-a"]
    assert e["usd_approx"] is not None and e["analyses"][0]["usd_approx"] == pytest.approx(e["usd_approx"])
    text = get(w, "ann").text
    assert "5.10 SU（約 US$0.01）" in summary(block_of(text, "slurm-a")[1])
    assert "SU 以 2026-10-13 匯率概算為美元，並非帳單金額。" in plain(pane(text, "middle"))
    def drop(r):
        r["usd_twd"].pop("as_of")
    rates_file(w, monkeypatch, tmp_path, drop)
    e = envs(w, ann)["slurm-a"]
    assert e["usd_approx"] is None and e["analyses"][0]["usd_approx"] is None and e["total"] == pytest.approx(5.10)
    mid = plain(pane(get(w, "ann").text, "middle"))
    assert "5.10 SU" in mid and "約 US$" not in mid and "US$ 0.00" not in mid and "匯率" not in mid


def test_env04_google_usd_and_rates_empty(w):
    # TC-018, TC-019, env06
    from abf_platform import cloud_cost
    ann = w.user("ann")
    seed(w, "run-g", ann, "cloud", hours=6, ce="gcb-a")
    text = get(w, "ann").text
    assert "US$ 1.20" in summary(block_of(text, "gcb-a")[1]) and analysis_rows(block_of(text, "gcb-a")[1])[0][2] == "US$ 1.20"
    cloud_cost.RATES_PATH.write_text(json.dumps({"currency": "USD", "regions": {}}), encoding="utf-8")
    e = envs(w, ann)["gcb-a"]
    assert e["total"] is None and e["unit"] == "USD" and e["unknown_reasons"]
    page = get(w, "ann").text
    s = summary(block_of(page, "gcb-a")[1])
    assert "—" in s and "US$ 0.00" not in page and "US$ 0.00" not in plain(pane(page, "middle"))


def test_env02_launch_facts_keys(w):
    # TC-029
    from abf_platform import cloud_cost
    ann = w.user("ann")
    seed(w, "run-g", ann, "cloud", ce="gcb-a")
    seed(w, "run-w", ann, "nchc", ce="aws-a", platform=AWS)
    g, a = cloud_cost._launch_facts(w.ip.state_db, "run-g"), cloud_cost._launch_facts(w.ip.state_db, "run-w")
    assert set(g) == {"cloud", "location", "pipeline", "ce", "platform"}
    assert g["cloud"] is True and g["ce"] == "gcb-a" and g["platform"] == "googlebatch-platform"
    assert a["cloud"] is False and a["ce"] == "aws-a" and a["platform"] == AWS


# ---- US3: unknown is not 0; running; counts and the limit -----------------------------------------------------------------------

def test_env06_running_and_partial_totals(w):
    # env06: TC-031, TC-032, TC-033, TC-034
    from abf_platform import su
    ann = w.user("ann")
    seed(w, "d1", ann, hours=50, ce="slurm-a")
    seed(w, "d2", ann, hours=50, ce="slurm-a")
    seed(w, "live", ann, status="running", ce="slurm-a")
    seed(w, "only-live", ann, status="running", ce="slurm-b")
    by = envs(w, ann)
    a = by["slurm-a"]
    assert a["total"] == pytest.approx(100.0) and a["unknown_runs"] == 1
    live = [x for x in a["analyses"] if x["name"] == "live"][0]
    assert live["state"] == "running" and live["value"] is None and live["unknown_reasons"] == [su.RUN_NOT_ENDED]
    assert by["slurm-b"]["total"] is None and by["slurm-b"]["unknown_runs"] == 1
    text = get(w, "ann").text
    assert "100.00 SU" in summary(block_of(text, "slurm-a")[1]) and "另有 1 個分析無法計算" in summary(block_of(text, "slurm-a")[1])
    b = summary(block_of(text, "slurm-b")[1])
    assert "—" in b and "0.00" not in b
    assert "執行中" in " ".join(" ".join(r) for r in analysis_rows(block_of(text, "slurm-a")[1]))
    assert "1 more analysis could not be priced" in summary(block_of(get(w, "ann", "/usage?lang=en").text, "slurm-a")[1])


def test_env05_fifty_listed_all_counted(w):
    # env05: TC-037, TC-038
    ann = w.user("ann")
    base = time.time() - 700
    for i in range(60):
        seed(w, "r%02d" % i, ann, hours=10, ce="slurm-a", started=base + i)
    e = envs(w, ann)["slurm-a"]
    assert len(e["analyses"]) == 50 and e["analyses_count"] == 60 and e["total"] == pytest.approx(600.0)
    names = [a["name"] for a in e["analyses"]]
    assert names[0] == "r59" and "r00" not in names and "r09" not in names and "r10" in names
    inner = block_of(get(w, "ann").text, "slurm-a")[1]
    assert "共 60 個分析" in summary(inner) and len(analysis_rows(inner)) == 50 and "600.00 SU" in summary(inner)


def test_env06_same_value_in_page_row_and_action(w):
    # TC-095
    ann = w.user("ann")
    seed(w, "run-w", ann, "nchc", ce="aws-a", platform=AWS)
    seed(w, "run-live", ann, status="running", ce="slurm-a")
    seed(w, "run-bad", ann, hours=None, ce="slurm-a")
    for e in usage(w, ann)["environments"]:
        assert all(a["value"] is None and a["unknown_reasons"] for a in e["analyses"])
    mid = plain(pane(get(w, "ann").text, "middle"))
    assert "US$ 0.00" not in mid and not re.search(r"(?<![\d.])0\.00 SU", mid)


# ---- US4: only mine, unreadable index, read only ---------------------------------------------------------------------------------

def test_env07_nobody_sees_anyone_elses(w):
    # env07: TC-041, TC-042, TC-097
    from abf_platform import actions
    ann, bob = w.user("ann"), w.user("bob")
    seed(w, "ann-run", ann, hours=2, ce="ann-env")
    seed(w, "bob-run", bob, hours=3, ce="bob-env")
    page = get(w, "bob").text
    assert "ann-env" not in page and "ann-run" not in page and "bob-env" in page
    assert [e["name"] for e in usage(w, bob)["environments"]] == ["bob-env"]
    assert "ann-run" not in json.dumps(usage(w, bob))
    assert actions.my_usage(w.ip.index, w.ip.state_db, caller=None)["found"] is False
    assert actions.run_usage(w.ip.index, "id-ann-run", caller=bob, platform_path=w.ip.state_db)["found"] is False


def test_env13_unreadable_index_is_an_empty_page(w, monkeypatch):
    # env13: TC-043, TC-057
    from abf_platform import actions, web_cost
    ann = w.user("ann")
    rid = seed(w, "run-a", ann, hours=2, ce="slurm-a")
    empty = web_cost.empty_usage("2026-10")
    assert empty["environments"] == [] and set(empty) == {"month", "environments", "cloud"} and "cap_usd" in empty["cloud"]

    def boom(*a, **k):
        raise sqlite3.OperationalError("no such table: runs at /secret/index.db")
    monkeypatch.setattr(actions, "my_usage", boom)
    r = get(w, "ann")
    assert r.status_code == 200 and blocks(r.text) == [] and not re.search(r"Traceback|sqlite|\.db\b|SELECT|/secret", r.text)
    monkeypatch.undo()
    monkeypatch.setattr(actions, "run_usage", boom)
    r = login(w, "ann").get("/?run=" + rid)
    assert r.status_code == 200 and not re.search(r"Traceback|sqlite|/secret", r.text)
    row = cost_table(r.text)
    assert row is not None and set(row[1]) == {"—"}


def test_env12_reads_only(w):
    # TC-044
    from abf_platform import actions
    ann = w.user("ann")
    rid = seed(w, "run-a", ann, hours=2, ce="slurm-a")
    seed(w, "run-g", ann, "cloud", ce="gcb-a")

    def snap():
        out = []
        for p in (w.ip.index, w.ip.state_db):
            out.append((hashlib.sha256(open(p, "rb").read()).hexdigest(), p.stat().st_mtime_ns))
        return out
    before = snap()
    usage(w, ann)
    actions.run_usage(w.ip.index, rid, caller=ann, platform_path=w.ip.state_db)
    assert snap() == before


# ---- US5: the cost row of the run page --------------------------------------------------------------------------------------------

def cost_table(text):
    """(heads, cells) of the cost row of the run page (the table whose first head is Environment), or None."""
    html = pane(text, "middle") if 'data-pane="middle"' in text else text
    for t in re.findall(r'<table class="tbl[^"]*">.*?</table>', html, re.S):
        heads = [plain(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", t, re.S)]
        if heads[:1] in (["環境"], ["Environment"]):
            rows = re.findall(r"<tr>(.*?)</tr>", re.search(r"<tbody>(.*?)</tbody>", t, re.S).group(1), re.S)
            assert len(rows) == 1
            return heads, [plain(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", rows[0], re.S)]
    return None


def test_env09_run_page_cost_row(w, monkeypatch):
    # env09: TC-045, TC-046, TC-048, TC-049, TC-050, TC-051, TC-052, TC-053, TC-054
    from abf_platform import actions, web_board
    ann = w.user("ann")
    zh, en = web_board.STRINGS["zh"], web_board.STRINGS["en"]
    done = seed(w, "run-done", ann, hours=5.10, ce="slurm-a")
    live = seed(w, "run-live", ann, status="running", ce="slurm-a")
    aws = seed(w, "run-aws", ann, "nchc", ce="aws-a", platform=AWS)
    gcb = seed(w, "run-gcb", ann, "cloud", hours=6, ce="gcb-a")
    loc = seed(w, "run-loc", ann, hours=1)
    no_handoff(monkeypatch, "run-loc")
    c = login(w, "ann")
    text = c.get("/?run=" + done).text
    heads, cells = cost_table(text)
    assert heads == ["環境", "用量", "狀態", "範圍"]
    u = actions.run_usage(w.ip.index, done, caller=ann, platform_path=w.ip.state_db)
    assert cells == ["slurm-a", web_board.usage_text(zh, u["unit"], u["value"], u["usd_approx"]), zh["state_estimate"], zh["cr_scope_text"]]
    assert "5.10 SU" in cells[1]
    assert re.search(r'<section class="sumcards">.*?</section>\s*<table class="tbl"><thead><tr><th>環境', text, re.S)        # right after the four cards
    h2, c2 = cost_table(c.get("/?run=%s&lang=en" % done).text)
    assert h2 == ["Environment", "Usage", "Status", "Scope"] and c2[2] == en["state_estimate"] and c2[3] == en["cr_scope_text"]
    lt = c.get("/?run=" + live).text
    h3, c3 = cost_table(lt)
    assert h3 == ["環境", "用量", "狀態", "範圍"] and c3[1] == "—" and "執行中" in c3[2]
    assert re.search(r'<section class="sumcards">.*?</section>\s*<table class="tbl"><thead><tr><th>環境', lt, re.S)
    assert 'class="state-running"' in lt and "⟳" in re.search(r'<table class="tbl"><thead><tr><th>環境.*?</table>', lt, re.S).group(0)
    assert cost_table(c.get("/?run=" + aws).text)[1][:2] == ["aws-a", "—"]
    assert cost_table(c.get("/?run=" + gcb).text)[1][1] == "US$ 1.20"
    assert cost_table(c.get("/?run=" + loc).text)[1][:2] == ["—", "—"]
    # the two cost cards stay as they were
    assert "SU —" in " ".join(re.findall(r'<p class="cv">(.*?)</p>', text)) or "5.10" in text


def test_env09_other_users_run_page_has_no_row(w):
    # TC-056
    from abf_platform import actions
    ann, bob = w.user("ann"), w.user("bob")
    rid = seed(w, "ann-run", ann, hours=5.10, ce="ann-env")
    got = login(w, "bob").get("/?run=" + rid).text
    assert "ann-env" not in got and "5.10" not in got and cost_table(got) is None
    assert actions.run_usage(w.ip.index, rid, caller=bob, platform_path=w.ip.state_db) == {
        "found": False, "id": rid, "message": actions.get_run(w.ip.index, rid, caller=bob, platform_path=w.ip.state_db)["message"]}
    assert actions.run_usage(w.ip.index, "id-nope", caller=ann, platform_path=w.ip.state_db)["found"] is False


def test_env10_run_usage_and_my_usage_agree(w):
    # env10: TC-047, TC-058, TC-059, TC-060
    from abf_platform import actions
    import test_web_parity as parity
    ann = w.user("ann")
    ids = {"s": seed(w, "run-s", ann, hours=2, ce="slurm-a"), "g": seed(w, "run-g", ann, "cloud", hours=6, ce="gcb-a"),
           "w": seed(w, "run-w", ann, "nchc", ce="aws-a", platform=AWS), "l": seed(w, "run-l", ann, status="running", ce="slurm-a")}
    mine = {a["name"]: a for e in usage(w, ann)["environments"] for a in e["analyses"]}
    for rid in ids.values():
        one = actions.run_usage(w.ip.index, rid, caller=ann, platform_path=w.ip.state_db)
        assert set(one) == {"found", "environment", "kind", "unit", "value", "usd_approx", "state", "unknown_reasons"} and one["found"] is True
        other = mine[rid[3:]]
        assert (one["value"], one["state"], one["unknown_reasons"]) == (other["value"], other["state"], other["unknown_reasons"])
    assert actions.run_usage(w.ip.index, ids["w"], caller=ann, platform_path=w.ip.state_db)["unit"] == "USD"
    assert "run_usage" in parity.WEB_ONLY
    assert 'name="run_usage"' not in (PKG / "mcp_server.py").read_text(encoding="utf-8")
    # failed tasks are counted (the scope says "failed steps included"): one completed task of 1 h and one failed of 2 h
    rid = seed(w, "run-f", ann, tasks=[dict(realtime_ms=H), dict(realtime_ms=2 * H)], ce="slurm-a")
    con = sqlite3.connect(str(w.ip.index))
    with con:
        con.execute("UPDATE task_usage SET status = 'FAILED' WHERE run_id = ? AND task_key = '1:1'", (rid,))
        con.execute("UPDATE runs SET n_succeeded = 1 WHERE id = ?", (rid,))
    con.close()
    assert actions.run_usage(w.ip.index, rid, caller=ann, platform_path=w.ip.state_db)["value"] == pytest.approx(3.0)
    assert [a["value"] for e in usage(w, ann)["environments"] for a in e["analyses"] if a["name"] == "run-f"] == [pytest.approx(3.0)]


# ---- US6: what is gone, what is not touched -------------------------------------------------------------------------------------------

def test_env08_deleted_words_and_constraints(w):
    # env08: TC-065, TC-066, TC-067, TC-070, TC-074, TC-075
    from abf_platform import web_cost
    ann = w.user("ann")
    seed(w, "run-n", ann, hours=1, ce="slurm-a", config={"suSite": "nano4"})
    seed(w, "run-c", ann, "cloud", hours=6, ce="gcb-a")
    cap(w, ann, 50)
    c = login(w, "ann")
    for url in ("/usage", "/usage?lang=en"):
        r = c.get(url)
        mid = plain(pane(r.text, "middle"))
        for word in ("NT$", "新台幣", "TWD", "Reconciled", "已對帳", "國網", "雲端已用", "NCHC", "Cloud used", "taiwania3", "nano4", "nchc"):
            assert word not in mid, (url, word)
        assert "<script" not in r.text and "style=" not in r.text and "<link" not in r.text and not re.search(r"\son\w+\s*=", r.text)
        assert "script-src" not in r.headers["content-security-policy"]
    en = pane(c.get("/usage?lang=en").text, "middle")
    assert no_cjk(re.sub(r"slurm-a|gcb-a|run-[nc]", "", en))
    assert c.get("/cost").status_code == 404
    t = plain(pane(c.get("/usage").text, "middle"))
    assert t.count("雲端上限") == 1 and "雲端剩餘" in t
    for key in list(web_cost.STRINGS["zh"]):
        assert not key.startswith(("card_su", "card_used")) and key not in ("where_hpc", "where_cloud", "th_where")
    assert not hasattr(web_cost, "_HPC")
    note = {"zh": "各運算環境用各自的單位（SU 或美元）顯示，不互相換算、不加總。數字依執行紀錄估算，略低於實際帳單。",
            "en": "Each compute environment is shown in its own unit (SU or US dollars); nothing is converted or added across environments. "
                  "Figures are estimates from the run records and a little below the actual bill."}
    assert web_cost.STRINGS["zh"]["note"] == note["zh"] and web_cost.STRINGS["en"]["note"] == note["en"]


def test_env14_no_new_colours():
    # env14: TC-086
    from abf_platform import web_board
    got = sorted(set(re.findall(r"#[0-9a-fA-F]{3,8}\b|(?:rgb|rgba|hsl|oklch)\([^)]*\)", web_board.STYLE)))
    assert got == V3_COLOURS


def test_env11_pages_reach_data_only_through_actions():
    # env11: TC-063, TC-098
    import ast
    for fname in ("web_cost.py", "web_board.py"):
        tree = ast.parse((PKG / fname).read_text(encoding="utf-8"))
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                names |= {(n.module or "").split(".")[0]} | {a.name for a in n.names}
        assert not names & {"confirm", "jobs", "compute_envs", "agents", "status", "su", "cloud_cost", "store"}, fname


def test_env12_month_total_has_no_caller():
    # env12: TC-083, TC-079
    from abf_platform import compute_envs
    for p in PKG.rglob("*.py"):
        if p.name != "su.py":
            assert "month_total" not in p.read_text(encoding="utf-8"), p.name
    assert "month_total" in (PKG / "su.py").read_text(encoding="utf-8")
    assert not [v for v in compute_envs.KINDS.values() if "本機" in v or "Local" in v]


def test_env15_my_usage_new_shape_has_cloud_part(w):
    # TC-081
    ann = w.user("ann")
    seed(w, "run-g", ann, "cloud", hours=6, ce="gcb-a")
    cap(w, ann, 50)
    got = usage(w, ann)["cloud"]
    assert set(got) == {"used_usd", "unknown_runs", "cap_usd", "remaining_usd", "currency"} and got["used_usd"] == pytest.approx(1.2)
    assert "每月費用提醒額度" not in get(w, "ann").text
