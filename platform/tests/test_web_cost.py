# Nothing existing: tests of the cost page GET /usage and the my_usage action (spec: specs/cost-page); the page and its numbers are ours.
"""cost-page: GET /usage (SU, cloud used / cap / remaining, one line per analysis) and the my_usage read action.
Test cases TC-001 ... TC-116 are named in the comments (specs/cost-page/test-case.md); co01 ... co12 are the plan's test names."""
import ast
import asyncio
import base64
import hashlib
import json
import re
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR
from human_harness import World, tool_json
from test_web_board import cjk, login, no_cjk, pane, plain, style_of

PKG = PLATFORM_DIR / "abf_platform"
H = 3600000
GCB = "googlebatch-platform"
SRC = "https://example.test/price-page"
CLOUD_RATES = {"currency": "USD", "regions": {"us-central1": {
    "n2-standard-4": {"standard": 0.20, "spot": 0.06, "source": SRC, "read_on": "2026-10-24"}}}}
CAP_NOTE = "由管理者設定"
NOTE_ZH = "雲端費用以美元顯示，不換算新台幣；國網以 SU 計。數字是依執行紀錄估算，略低於實際帳單。"


@pytest.fixture
def w(tmp_path, monkeypatch):
    from abf_platform import cloud_cost
    rates = tmp_path / "cloud_rates.json"
    rates.write_text(json.dumps(CLOUD_RATES), encoding="utf-8")
    monkeypatch.setattr(cloud_cost, "RATES_PATH", rates)
    return World(tmp_path, monkeypatch)


def this_month():
    import datetime
    from abf_platform import su
    return datetime.datetime.fromtimestamp(time.time(), su.TAIPEI).strftime("%Y-%m")


def epoch_of(iso):
    import calendar
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


def seed(w, name, owner, where="nchc", status="succeeded", hours=1.0, started=None, cpus=1, tasks=None, ce=None):
    """One run in index.db with its task rows, and the hand-off record naming `owner` and the environment (where: nchc, cloud or None)."""
    from abf_platform import store
    started = int(started if started is not None else time.time() - 600)
    rid = "id-" + name
    final = status if status in ("succeeded", "failed") else None
    last = time.time() if status == "running" else (time.time() - 10 ** 6 if status == "lost" else started + 100)
    if tasks is None:
        tasks = [] if hours is None else [dict(realtime_ms=int(hours * H))]
    con = store.connect_index(w.ip.index)
    with con:
        con.execute("INSERT INTO runs (id, session_id, run_name, final_status, started_at, ended_at, last_message_at, n_succeeded) "
                    "VALUES (?,?,?,?,?,?,?,?)", (rid, "s-" + rid, name, final, started, started + 100 if final else None, last, len(tasks)))
        for i, t in enumerate(tasks):
            con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue, machine_type, price_model, cloud_zone) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (rid, "%d:1" % i, "T", "COMPLETED", cpus, t.get("realtime_ms"),
                         "ct56" if where == "nchc" else None,
                         t.get("machine_type", "n2-standard-4" if where == "cloud" else None),
                         t.get("price_model", "standard" if where == "cloud" else None),
                         t.get("zone", "us-central1-a" if where == "cloud" else None)))
    con.close()
    if where is not None:
        ce = ce or ("gcb1" if where == "cloud" else "nchc1")
        con = store.connect_state(w.ip.state_db)
        with con:
            con.execute("INSERT OR IGNORE INTO compute_envs (name, platform, status, is_primary, config_json, created_at, updated_at) "
                        "VALUES (?, ?, 'ready', 0, '{}', 1, 1)", (ce, GCB if where == "cloud" else "slurm-platform"))
            at = time.time() + w.n_launch()
            con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                        (name, "/f/" + name, ce, "a1", at, owner.user_id))
            con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state, confirmed_at, bundle_json) VALUES (?,?,?,?,?,?,?)",
                        ("c-" + name, "x", "launch", at, "confirmed", at, json.dumps({"pipeline": "nf-core/x"})))
        con.close()
    elif owner is not None:
        con = store.connect_state(w.ip.state_db)
        with con:
            con.execute("INSERT INTO launches (run_name, run_folder, ce, agent, confirmed_at, user_id) VALUES (?,?,?,?,?,?)",
                        (name, "/f/" + name, "gone-ce", "a1", time.time(), owner.user_id))
        con.close()
    return rid


_n = [0]


def _n_launch():
    _n[0] += 1
    return _n[0]


World.n_launch = lambda self: _n_launch()


def cap(w, user, usd):
    from abf_platform import store
    store.set_cloud_cap(w.ip.tokens, user.user_id, usd)


def usage(w, caller, **kw):
    from abf_platform import actions
    return actions.my_usage(w.ip.index, w.ip.state_db, caller=caller, tokens_path=w.ip.tokens, **kw)


def cards(text):
    """[(class list, title, value, small text)] of the summary cards in the middle column."""
    out = []
    for m in re.finditer(r'<div class="(scard[^"]*)">(.*?)</div>', pane(text, "middle"), re.S):
        title = re.search(r'<h2 class="ct">(.*?)</h2>', m.group(2), re.S).group(1)
        value = re.search(r'<p class="cv">(.*?)</p>', m.group(2), re.S).group(1)
        small = " ".join(re.findall(r"<small>(.*?)</small>", m.group(2), re.S))
        out.append((m.group(1).split(), plain(title), plain(value), plain(small)))
    return out


def card(text, index):
    return cards(text)[index]


def table_rows(text):
    """[[cell texts]] of the body rows of the per-analysis table."""
    body = re.search(r"<tbody>(.*?)</tbody>", pane(text, "middle"), re.S)
    if not body:
        return []
    return [[plain(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", r, re.S)] for r in re.findall(r"<tr>(.*?)</tr>", body.group(1), re.S)]


def get(w, name, url="/usage"):
    return login(w, name).get(url)


# ---- US1: the four cards and the fixed line --------------------------------------------------------------------------

def test_co01_page_has_four_cards_note_and_table(w):
    # co01: TC-001, TC-002, TC-019
    ann = w.user("ann")
    seed(w, "run-a", ann)
    r = get(w, "ann")
    assert r.status_code == 200
    assert [c[1] for c in cards(r.text)] == ["國網 SU（本月）", "雲端已用（本月）", "雲端上限", "雲端剩餘"]
    assert NOTE_ZH in plain(pane(r.text, "middle"))
    head = re.search(r"<thead>(.*?)</thead>", pane(r.text, "middle"), re.S).group(1)
    assert [plain(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", head, re.S)] == ["分析名稱", "開始時間", "在哪裡跑", "用量", "狀態"]


def test_co02_su_total_and_unknown(w):
    # co02: TC-003, TC-004, TC-005, TC-074
    ann = w.user("ann")
    seed(w, "run-a", ann, hours=5.10)
    seed(w, "run-b", ann, hours=7.20)
    assert card(get(w, "ann").text, 0)[2] == "12.30 SU（約 US$0.03）"
    assert usage(w, ann)["su"]["total"] == pytest.approx(12.30)
    seed(w, "run-c", ann, hours=None)        # no usage rows: its SU cannot be worked out
    r = get(w, "ann")
    c = card(r.text, 0)
    assert c[2] == "—" and "5.10" not in c[2] and "0.00" not in c[2]
    got = usage(w, ann)["su"]
    assert got["total"] is None and got["unknown_reasons"]
    assert c[3] and c[3] == plain(got["unknown_reasons"][0]).split(" (")[0]


def test_co03_cloud_used_cap_remaining(w):
    # co03: TC-006 ... TC-009, TC-076, TC-078
    ann = w.user("ann")
    seed(w, "cl-a", ann, "cloud", hours=61.7)
    cap(w, ann, 50)
    for url in ("/usage", "/usage?lang=en"):
        r = get(w, "ann", url)
        assert [c[2] for c in cards(r.text)][1:] == ["US$ 12.34", "US$ 50.00", "US$ 37.66"], url
        assert "NT$" not in r.text.replace("不換算新台幣", "")
    got = usage(w, ann)["cloud"]
    assert got["cap_usd"] == 50 and got["remaining_usd"] == pytest.approx(37.66) and got["currency"] == "USD"


def test_unknown_cloud_runs_are_not_added_as_zero(w):
    # TC-010, TC-011
    ann = w.user("ann")
    seed(w, "cl-ok", ann, "cloud", hours=6)
    seed(w, "cl-x1", ann, "cloud", tasks=[dict(realtime_ms=H, machine_type="m-unknown")])
    seed(w, "cl-x2", ann, "cloud", tasks=[dict(realtime_ms=H, machine_type="m-unknown")])
    c = card(get(w, "ann").text, 1)
    assert c[2] == "US$ 1.20" and "另有 2 個分析算不出" in c[3]
    assert usage(w, ann)["cloud"]["unknown_runs"] == 2


def test_ruling12_su_card_ignores_cloud_runs(w):
    # ruling 12: one HPC run and one cloud run in the same month; the SU card shows the HPC run's number
    ann = w.user("ann")
    seed(w, "hpc-run", ann, hours=4.0)
    seed(w, "cloud-run", ann, "cloud", hours=6)
    assert usage(w, ann)["su"]["total"] == pytest.approx(4.0)
    assert card(get(w, "ann").text, 0)[2] == "4.00 SU（約 US$0.01）"
    seed(w, "hpc-open", ann, hours=None)        # an HPC run that cannot be priced still turns the card to a dash
    assert card(get(w, "ann").text, 0)[2] == "—"


def test_ruling13_english_plural(w):
    # ruling 13
    ann = w.user("ann")
    seed(w, "cl-ok", ann, "cloud", hours=6)
    seed(w, "cl-x1", ann, "cloud", tasks=[dict(realtime_ms=H, machine_type="m-unknown")])
    one = card(get(w, "ann", "/usage?lang=en").text, 1)[3]
    assert "1 more analysis could not be priced" in one and "analyses" not in one
    seed(w, "cl-x2", ann, "cloud", tasks=[dict(realtime_ms=H, machine_type="m-unknown")])
    two = card(get(w, "ann", "/usage?lang=en").text, 1)[3]
    assert "2 more analyses could not be priced" in two
    assert "另有 2 個分析算不出" in card(get(w, "ann").text, 1)[3]


def test_ruling14_future_or_missing_month_is_an_empty_table(w):
    # ruling 14
    ann = w.user("ann")
    seed(w, "run-a", ann)
    for m in ("2099-01", "1999-12", "0001-01"):
        r = get(w, "ann", "/usage?month=" + m)
        assert r.status_code == 200, m
        assert table_rows(r.text) == [], m
    assert "這個月還沒有分析" in plain(pane(get(w, "ann", "/usage?month=2099-01").text, "middle"))
    assert usage(w, ann, month="2099-01")["runs"] == []
    # "2026-13" is not the form YYYY-MM (TC-046/TC-095): the standard notice and this month, still no error
    bad = get(w, "ann", "/usage?month=2026-13")
    assert bad.status_code == 200 and "月份格式不對，顯示本月。" in plain(pane(bad.text, "middle"))


def test_co04_no_cap(w):
    # co04: TC-012, TC-013, TC-014, TC-077, TC-079
    ann = w.user("ann")
    r = get(w, "ann")
    assert card(r.text, 2)[2] == "未設定" and CAP_NOTE in card(r.text, 2)[3]
    assert card(r.text, 3)[2] == "—"
    got = usage(w, ann)["cloud"]
    assert got["cap_usd"] is None and got["remaining_usd"] is None


def test_co05_over_cap_is_zero_remaining(w):
    # co05: TC-015, TC-016, TC-017, TC-078, TC-099
    ann = w.user("ann")
    seed(w, "cl-a", ann, "cloud", hours=61.7)
    cap(w, ann, 10)
    r = get(w, "ann")
    c = card(r.text, 3)
    assert c[2] == "US$ 0.00"
    assert "state-failed" in c[0] and ".state-failed{" in style_of(r.text)        # a class the stylesheet already had
    assert "⚠" in c[3] or "!" in c[3]                                              # a symbol and a word, not colour alone
    assert "待處理" in c[3]
    assert usage(w, ann)["cloud"]["remaining_usd"] == 0
    assert "待處理" not in pane(r.text, "right")                                   # TC-099: no notice in the right column


def test_amounts_are_shown_with_two_decimals_but_not_rounded_inside(w):
    # TC-080
    ann = w.user("ann")
    seed(w, "cl-a", ann, "cloud", tasks=[dict(realtime_ms=int(0.617283 * H))])        # 0.617283 h x 0.20 = 0.1234566
    assert usage(w, ann)["cloud"]["used_usd"] == pytest.approx(0.1234566, rel=1e-6)
    assert usage(w, ann)["cloud"]["used_usd"] != round(usage(w, ann)["cloud"]["used_usd"], 2)
    assert card(get(w, "ann").text, 1)[2] == "US$ 0.12"


# ---- US2: one line per analysis --------------------------------------------------------------------------------------

def test_co06_rows_states(w):
    # co06: TC-026 ... TC-032, TC-037, TC-081, TC-082, TC-091
    ann, bob = w.user("ann"), w.user("bob")
    seed(w, "run-live", ann, status="running")
    seed(w, "run-done", ann, hours=5.10)
    seed(w, "run-lost", ann, status="lost")
    seed(w, "run-old", ann, started=time.time() - 40 * 86400)
    seed(w, "bob-run", bob)
    r = get(w, "ann")
    rows = {row[0]: row for row in table_rows(r.text)}
    assert set(rows) == {"run-live", "run-done", "run-lost"}
    assert rows["run-live"][3] == "—" and rows["run-live"][4] == "⟳ 執行中"
    assert rows["run-lost"][3] == "—" and rows["run-lost"][4] == "⟳ 執行中"
    assert rows["run-done"][2] == "國網" and rows["run-done"][3] == "5.10 SU（約 US$0.01）" and rows["run-done"][4] == "≈ 估算・帳單未到"
    assert "bob-run" not in r.text and "run-old" not in pane(r.text, "middle")
    assert "run-done" not in get(w, "bob").text and "bob-run" in get(w, "bob").text
    by_name = {x["name"]: x for x in usage(w, ann)["runs"]}
    assert by_name["run-live"]["state"] == "running" and by_name["run-live"]["su"] is None and by_name["run-live"]["usd"] is None
    assert any("run 還沒結束" in x for x in by_name["run-live"]["unknown_reasons"])
    assert by_name["run-done"]["state"] == "estimate"


def test_where_and_amount_per_row(w, monkeypatch):
    # TC-020 ... TC-025, TC-030
    from abf_platform import cloud_cost
    real = cloud_cost._launch_facts
    monkeypatch.setattr(cloud_cost, "_launch_facts", lambda plat, name: None if name == "run-x" else real(plat, name))      # not sent by the platform
    ann = w.user("ann")
    rid = seed(w, "run-n", ann, "nchc", hours=5.10)
    seed(w, "run-c", ann, "cloud", hours=6)
    seed(w, "run-x", ann, "nchc", hours=2)
    seed(w, "run-cx", ann, "cloud", tasks=[dict(realtime_ms=H, machine_type="m-unknown")])
    r = get(w, "ann")
    rows = {row[0]: row for row in table_rows(r.text)}
    assert rows["run-n"][2:4] == ["國網", "5.10 SU（約 US$0.01）"]
    assert rows["run-c"][2:4] == ["雲端", "US$ 1.20"]
    assert rows["run-x"][2:4] == ["—", "—"]
    assert rows["run-cx"][2:4] == ["雲端", "—"] and rows["run-cx"][4] == "≈ 估算・帳單未到"
    assert 'href="/?run=%s"' % rid in r.text
    assert 'href="/?run=%s&amp;lang=en"' % rid in get(w, "ann", "/usage?lang=en").text or 'href="/?run=%s&lang=en"' % rid in get(w, "ann", "/usage?lang=en").text
    by = {x["name"]: x["where"] for x in usage(w, ann)["runs"]}
    assert by == {"run-n": "nchc", "run-c": "cloud", "run-x": None, "run-cx": "cloud"}


def test_newest_a_launch_decides_where(w):
    # TC-083
    from abf_platform import store
    ann = w.user("ann")
    seed(w, "run-m", ann, "nchc")
    seed(w, "run-m2", ann, "cloud")
    con = store.connect_state(w.ip.state_db)
    with con:
        con.execute("UPDATE launches SET run_name = 'run-m' WHERE run_name = 'run-m2'")
        con.execute("UPDATE confirmations SET id = 'c-run-m-2' WHERE id = 'c-run-m2'")
    con.close()
    con = store.connect_state(w.ip.state_db)
    got = con.execute("SELECT count(*) FROM launches WHERE run_name = 'run-m'").fetchone()[0]
    con.close()
    assert got == 2
    assert [x["where"] for x in usage(w, ann)["runs"] if x["name"] == "run-m"] == ["cloud"]


def test_month_edge_order_and_limit(w):
    # TC-033, TC-034, TC-035
    ann = w.user("ann")
    seed(w, "edge", ann, started=epoch_of("2026-09-30T16:30:00Z"))
    assert [x["name"] for x in usage(w, ann, month="2026-10")["runs"]] == ["edge"]
    assert usage(w, ann, month="2026-09")["runs"] == []
    base = epoch_of("2026-08-10T00:00:00Z")
    for i in range(51):
        seed(w, "m%02d" % i, ann, started=base + i * 60)
    runs = usage(w, ann, month="2026-08")["runs"]
    assert len(runs) == 50 and runs[0]["name"] == "m50" and "m00" not in [x["name"] for x in runs]
    page = [row[0] for row in table_rows(get(w, "ann", "/usage?month=2026-08").text)]
    assert page[0] == "m50" and len(page) == 50


def test_empty_month(w):
    # TC-036, TC-060
    w.user("ann")
    assert "— 這個月還沒有分析" in plain(pane(get(w, "ann").text, "middle"))
    en = pane(get(w, "ann", "/usage?lang=en").text, "middle")
    assert "No analyses this month" in plain(en) and no_cjk(en)


# ---- US3: masthead, months, login, English, constraints --------------------------------------------------------------

def test_co08_masthead_links_to_usage_and_says_usd(w):
    # co08: TC-039 ... TC-042, TC-102
    ann = w.user("ann")
    rid = seed(w, "run-a", ann)
    c = login(w, "ann")
    for url, want, href in (("/", ["SU —", "雲端 US$ —"], "/usage"), ("/settings", ["SU —", "雲端 US$ —"], "/usage"), ("/launch", ["SU —", "雲端 US$ —"], "/usage"),
                            ("/?run=" + rid, ["SU —", "雲端 US$ —"], "/usage"), ("/?lang=en", ["SU —", "Cloud US$ —"], "/usage?lang=en"),
                            ("/usage", ["SU —", "雲端 US$ —"], "/usage")):
        t = c.get(url).text
        top = t[:t.index('data-pane="left"')]
        link = re.search(r'<a\b[^>]*href="([^"]*)"[^>]*>((?:(?!</a>).)*class="cost"(?:(?!</a>).)*)</a>', top, re.S)
        assert link and link.group(1) == href, url
        lines = re.findall(r'<span class="cost">(.*?)</span>', link.group(2), re.S)
        assert lines == want, url
        assert "NT$" not in top
        assert not re.search(r"\d", plain(re.search(r"<header.*?</header>", t, re.S).group(0)).replace("SU", ""))


def test_co07_month_param(w):
    # co07: TC-043 ... TC-052, TC-095
    ann = w.user("ann")
    seed(w, "run-aug", ann, started=epoch_of("2026-08-10T00:00:00Z"))
    seed(w, "run-sep", ann, started=epoch_of("2026-09-10T00:00:00Z"))
    seed(w, "run-now", ann)
    t = get(w, "ann", "/usage?month=2026-09").text
    assert [r[0] for r in table_rows(t)] == ["run-sep"] and "月份格式不對" not in t
    assert "2026-09" in plain(pane(t, "middle")) and "費用" in plain(pane(t, "middle"))
    assert "month=2026-08" in t and "month=2026-10" in t
    en = get(w, "ann", "/usage?month=2026-09&lang=en").text
    assert all("lang=en" in h for h in re.findall(r'href="([^"]*month=[^"]*)"', en))
    assert "Cost" in plain(pane(en, "middle"))
    bad = get(w, "ann", "/usage?month=abc")
    assert bad.status_code == 200 and [r[0] for r in table_rows(bad.text)] == ["run-now"]
    assert "月份格式不對，顯示本月。" in bad.text
    assert re.search(r"Traceback|sqlite|\.db\b|SELECT", bad.text) is None
    cur = get(w, "ann").text
    later = [m for m in re.findall(r"month=(\d{4}-\d{2})", cur) if m > this_month()]
    assert later == [] and "month=" + _prev(this_month()) in cur
    prev = get(w, "ann", "/usage?month=" + _prev(this_month())).text
    assert re.findall(r"month=(\d{4}-\d{2})", prev).count(this_month()) == 1        # "next" goes to this month and no further
    assert max(re.findall(r"month=(\d{4}-\d{2})", prev)) == this_month()


def _prev(month):
    y, m = int(month[:4]), int(month[5:])
    return "%04d-%02d" % ((y, m - 1) if m > 1 else (y - 1, 12))


def test_co12_login_required(w):
    # co12: TC-053, TC-054
    ann = w.user("ann")
    seed(w, "secret-run", ann, hours=5.10)
    r = w.web().get("/usage")
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert "secret-run" not in r.text and "5.10" not in r.text


def test_co09_english(w):
    # co09: TC-038, TC-055 ... TC-059
    ann = w.user("ann")
    seed(w, "run-live", ann, status="running")
    seed(w, "run-done", ann, hours=5.10)
    seed(w, "run-bad", ann, hours=None)
    r = get(w, "ann", "/usage?lang=en")
    mid = pane(r.text, "middle")
    seen = re.sub(r">run-[a-z]+<", "><", mid)
    assert cjk(seen) == []
    titles = [c[1] for c in cards(r.text)]
    assert "NCHC SU" in titles[0] and "used" in titles[1] and "cap" in titles[2] and "remaining" in titles[3]
    note = [p for p in re.findall(r"<p[^>]*>(.*?)</p>", mid, re.S) if "convert" in p]
    assert note and "SU" in note[0]
    assert card(r.text, 0)[3] and cjk(card(r.text, 0)[3]) == []
    rows = {row[0]: row for row in table_rows(r.text)}
    assert rows["run-live"][4] == "⟳ Running" and rows["run-done"][4] == "≈ Estimate · bill pending"
    flash = get(w, "ann", "/usage?month=abc&lang=en").text
    assert "The month is not in the form YYYY-MM, so this month is shown." in flash
    assert no_cjk(re.sub(r"run-[a-z]+", "", pane(flash, "middle")))


def test_co10_constraints_hold(w):
    # co10: TC-061 ... TC-064, TC-105
    ann = w.user("ann")
    seed(w, "run-a", ann, hours=1)
    c = login(w, "ann")
    for url in ("/usage", "/usage?lang=en"):
        r = c.get(url)
        t = r.text
        assert "<script" not in t and not re.search(r"\son\w+\s*=", t) and "style=" not in t and "<link" not in t
        assert t.count("<style>") == 1 and not re.search(r"https?://", re.sub(r"<style>.*?</style>", "", t, flags=re.S))
        csp = r.headers["content-security-policy"]
        digest = base64.b64encode(hashlib.sha256(style_of(t).encode("utf-8")).digest()).decode("ascii")
        assert "style-src 'sha256-%s'" % digest in csp and "script-src" not in csp and "'unsafe-inline'" not in csp
        assert not re.search(r"<form[^>]*action=\"[^\"]*\"[^>]*>(?:(?!</form>).)*(cap|limit|上限)", pane(t, "middle"), re.S)
    paths = [getattr(r, "path", "") for r in c.app.routes]
    assert "/usage" in paths and not [p for p in paths if "cost" in p]
    assert c.get("/cost").status_code == 404 and c.post("/cost").status_code in (404, 405)
    assert c.post("/usage").status_code in (404, 405)


def test_no_other_currency_no_reconciled_no_advice(w):
    # TC-097, TC-099, TC-100, TC-103, TC-108, TC-110
    ann = w.user("ann")
    seed(w, "cl-a", ann, "cloud", hours=61.7)
    seed(w, "run-n", ann, "nchc", hours=1)
    cap(w, ann, 10)
    for url in ("/usage", "/usage?lang=en"):
        t = get(w, "ann", url).text
        mid = plain(pane(t, "middle"))
        for word in ("已對帳", "Reconciled", "TWD", "即時匯率", "exchange rate", "改用國網", "等重置", "use NCHC", "taiwania3"):
            assert word not in mid, (url, word)
        assert "<form" not in pane(t, "middle") and "<input" not in pane(t, "middle")
    got = json.dumps(usage(w, ann))
    assert "TWD" not in got and "twd" not in got.lower() and "NT" not in got
    assert {x["state"] for x in usage(w, ann)["runs"]} <= {"running", "estimate"}


# ---- US4: the action and the tool -------------------------------------------------------------------------------------

def test_co11_my_usage_action_and_mcp_match(w):
    # co11: TC-070 ... TC-072, TC-084 ... TC-090, TC-092
    ann, bob = w.user("ann"), w.user("bob")
    seed(w, "ann-run", ann, hours=2)
    seed(w, "bob-run", bob, hours=3)
    seed(w, "ann-cl", ann, "cloud", hours=6)
    cap(w, ann, 50)
    got = usage(w, ann)
    assert set(got) == {"month", "su", "cloud", "runs"}
    assert set(got["su"]) == {"total", "unknown_reasons", "site", "usd_approx", "usd_rate_as_of"} and got["su"]["site"] == "taiwania3"
    assert set(got["cloud"]) == {"used_usd", "unknown_runs", "cap_usd", "remaining_usd", "currency"}
    assert got["month"] == this_month()
    for item in got["runs"]:
        assert set(item) == {"name", "started_at", "where", "state", "su", "usd", "unknown_reasons", "usd_approx"}
    assert sorted(x["name"] for x in got["runs"]) == ["ann-cl", "ann-run"]
    b = usage(w, bob)
    assert [x["name"] for x in b["runs"]] == ["bob-run"] and b["cloud"]["cap_usd"] is None and b["cloud"]["used_usd"] == 0
    assert b["su"]["total"] == pytest.approx(3.0) and got["su"]["total"] != b["su"]["total"]
    # ruling 12: ann has a cloud run too, yet her SU is the HPC run's alone, a number and not None
    assert got["su"]["total"] is not None and got["su"]["total"] == pytest.approx(2.0)
    assert got["su"]["unknown_reasons"] == []
    assert card(get(w, "ann").text, 0)[2] == "2.00 SU（約 US$0.01 以下）"
    assert "ann-run" not in get(w, "bob").text
    # the same through MCP
    out = tool_json(w.call("my_usage", {}, caller=ann))
    assert json.loads(json.dumps(out)) == json.loads(json.dumps(got))
    assert tool_json(w.call("my_usage", {"month": "2026-09"}, caller=ann))["month"] == "2026-09"


def test_my_usage_reads_only_and_asks_nothing(w):
    # TC-092, TC-112
    ann = w.user("ann")
    seed(w, "run-a", ann)
    before = (len(w.sql("SELECT * FROM jobs")), len(w.sql("SELECT * FROM confirmations")))
    c = login(w, "ann")
    c.get("/usage")
    usage(w, ann)
    assert c.post("/usage").status_code in (404, 405)
    assert (len(w.sql("SELECT * FROM jobs")), len(w.sql("SELECT * FROM confirmations"))) == before


def test_not_known_is_never_shown_as_zero(w):
    # TC-113
    ann = w.user("ann")
    seed(w, "run-live", ann, status="running")
    seed(w, "cl-x", ann, "cloud", tasks=[dict(realtime_ms=H, machine_type="m-unknown")])
    seed(w, "run-bad", ann, hours=None)
    mid = plain(pane(get(w, "ann").text, "middle"))
    assert card(get(w, "ann").text, 0)[2] == "—"
    assert "另有 1 個分析算不出" in mid
    assert not [r for r in table_rows(get(w, "ann").text) if r[0] in ("run-live", "cl-x", "run-bad") and "0.00" in r[3]]


def test_status_cells_have_symbol_and_word(w):
    # TC-037
    ann = w.user("ann")
    seed(w, "run-live", ann, status="running")
    seed(w, "run-done", ann)
    for row in table_rows(get(w, "ann").text):
        assert re.match(r"^(⟳ 執行中|≈ 估算・帳單未到)$", row[4])


# ---- code shape: one door, no network ---------------------------------------------------------------------------------

def test_web_cost_module_goes_through_actions_only():
    # TC-093, TC-094, TC-098
    src = (PKG / "web_cost.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            names |= {(n.module or "").split(".")[0]} | {a.name for a in n.names}
    assert not names & {"confirm", "jobs", "compute_envs", "agents", "status", "su", "cloud_cost", "store", "actions"}
    assert not names & {"urllib", "http", "socket", "requests", "ssl"}
    assert "cap_usd" not in src and "cloud_caps" not in src
    web = (PKG / "web.py").read_text(encoding="utf-8")
    fn = re.search(r"async def usage_page\(.*?(?=\n    async def |\n    # ----|\n    def )", web, re.S).group(0)
    calls = re.findall(r"\b(actions\.\w+|web_cost\.\w+)", fn)
    assert "actions.my_usage" in calls and {c for c in calls if c.startswith("actions")} <= {"actions.my_usage", "actions.Caller"}
    assert not re.search(r"\b(su|cloud_cost|store)\.", fn)
