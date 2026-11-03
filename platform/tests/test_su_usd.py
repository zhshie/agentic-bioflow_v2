# Nothing existing: tests of the side-note dollars next to SU (spec: specs/su-usd); the formula, the config keys and the wording are ours.
"""su-usd: SU x the NT$ price of one SU / the rate in the config = about US$, shown beside the SU on the cost page and the run page.
Test cases TC-001 ... TC-091 are named in the comments (specs/su-usd/test-case.md)."""
import json
import re
import socket
import sqlite3

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from test_web_board import no_cjk, pane, plain, style_of
from test_web_cost import card, cards, get, seed, table_rows, usage, w  # noqa: F401  (w is the fixture)

RATES_FILE = REPO_ROOT / "configs" / "sites" / "su_rates.json"
PKG = PLATFORM_DIR / "abf_platform"


def real_rates():
    return json.loads(RATES_FILE.read_text(encoding="utf-8"))


def set_rates(tmp_path, monkeypatch, **changes):
    """Point the platform at a copy of the real rates file with these top-level changes (a value of "DROP" removes the key)."""
    from abf_platform import su
    data = real_rates()
    for k, v in changes.items():
        if v == "DROP":
            data.pop(k, None)
        else:
            data[k] = v
    path = tmp_path / "su_rates.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(su, "RATES_PATH", path)
    return data


def as_nano4(w, name):
    """Make a seeded run a nano4 one: its compute environment names suSite nano4 and its tasks ran on an ngs partition."""
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET config_json = ? WHERE name = 'nchc1'", (json.dumps({"suSite": "nano4"}),))
    con.close()
    con = sqlite3.connect(str(w.ip.index))
    with con:
        con.execute("UPDATE task_usage SET queue = 'ngs92G' WHERE run_id = ?", ("id-" + name,))
    con.close()


def get_run(w, user, rid):
    from abf_platform import actions
    return actions.get_run(w.ip.index, rid, caller=user, platform_path=w.ip.state_db)


def cost_value(text):
    m = re.search(r'<h2 class="ct">(?:費用|Cost)</h2><p class="cv">(.*?)</p>', text, re.S)
    assert m, "no cost card"
    return plain(m.group(1))


def login_get(w, name, url):
    from test_web_board import login
    return login(w, name).get(url)


# ---- US1: usd_of and the config ---------------------------------------------------------------------------------------------

def test_tc001_to_005_usd_of_formula():
    from abf_platform import su
    rates = real_rates()
    assert rates["su_plan_type"] == "nstc"
    got = su.usd_of(51.5, "nano4", rates)
    assert got == pytest.approx(51.5 * 0.1 / 32) and got != round(got, 2)                       # TC-001
    for plan, price in (("academic", 0.2), ("industry", 0.37)):                                 # TC-002, TC-003
        assert su.usd_of(51.5, "nano4", dict(rates, su_plan_type=plan)) == pytest.approx(51.5 * price / 32)
    assert su.usd_of(100, "taiwania3", rates) == pytest.approx(100 * 0.08 / 32)                  # TC-004: the top-level price
    other = dict(rates, usd_twd=dict(rates["usd_twd"], rate=40.0))                              # TC-005: only the config's rate differs
    assert su.usd_of(51.5, "nano4", other) == pytest.approx(51.5 * 0.1 / 40)


def test_tc006_tc007_config_keys():
    rates = real_rates()
    assert rates["su_plan_type"] == "nstc"
    u = rates["usd_twd"]
    assert u["rate"] == 32.0 and u["as_of"] == "2026-10-13"
    assert u["source"] == "https://moneyexchangerate.org/currencyexchange/twd/usd/40400" and "每月手動更新一次" in u["note"]


def test_tc009_to_015_usd_of_missing_pieces():
    import copy
    from abf_platform import su
    rates = real_rates()
    assert su.usd_of(None, "nano4", rates) is None                                               # TC-009
    r = copy.deepcopy(rates)
    r["sites"]["nano4"]["twd_per_su"]["nstc"] = None
    assert su.usd_of(51.5, "nano4", r) is None                                                   # TC-010
    r = copy.deepcopy(rates)
    del r["usd_twd"]
    assert su.usd_of(51.5, "nano4", r) is None                                                   # TC-011
    for bad in (0, -32):                                                                         # TC-012, TC-013
        assert su.usd_of(51.5, "nano4", dict(rates, usd_twd=dict(rates["usd_twd"], rate=bad))) is None
    assert su.usd_of(51.5, "nano4", dict(rates, su_plan_type="gov")) is None                     # TC-014
    r = copy.deepcopy(rates)
    del r["su_plan_type"]
    assert su.usd_of(51.5, "nano4", r) is None
    assert su.usd_of(51.5, "nano4", None) is None                                                # TC-015


# ---- US2: the action layer and MCP ----------------------------------------------------------------------------------------

def two_runs(w):
    ann = w.user("ann")
    seed(w, "run-a", ann, hours=5.10)
    seed(w, "run-b", ann, hours=7.20)
    return ann


def test_tc016_to_019_my_usage_usd(w):
    ann = two_runs(w)
    got = usage(w, ann)
    total = got["su"]["total"]
    assert got["su"]["usd_approx"] == pytest.approx(total * 0.08 / 32)                           # TC-016 (by formula, not 0.03)
    assert got["su"]["usd_rate_as_of"] == "2026-10-13"                                           # TC-017
    for row in got["runs"]:                                                                      # TC-018
        assert row["usd_approx"] == pytest.approx(row["su"] * 0.08 / 32)
    seed(w, "cl-a", ann, "cloud", hours=6)
    again = usage(w, ann)
    cloud_row = [r for r in again["runs"] if r["name"] == "cl-a"][0]
    assert cloud_row["usd_approx"] is None and cloud_row["usd"] == pytest.approx(1.2)            # TC-019
    assert again["cloud"]["used_usd"] == pytest.approx(1.2)                                      # TC-080: the cloud numbers stay


def test_tc020_tc022_get_run_usd(w):
    ann = w.user("ann")
    rid = seed(w, "run-n", ann, hours=51.5)
    as_nano4(w, "run-n")
    view = get_run(w, ann, rid)
    assert view["su"]["su"] == pytest.approx(51.5)
    assert view["su"]["usd_approx"] == pytest.approx(51.5 * 0.1 / 32)                            # TC-020
    assert set(view["su"]) == {"su", "twd_nstc", "twd_academic", "unknown_reasons", "twd", "site", "usd_approx"}   # TC-022


def test_tc021_key_sets(w):
    ann = two_runs(w)
    seed(w, "cl-a", ann, "cloud", hours=6)
    got = usage(w, ann)
    assert set(got) == {"month", "su", "cloud", "runs"}
    assert set(got["su"]) == {"total", "unknown_reasons", "site", "usd_approx", "usd_rate_as_of"}
    for row in got["runs"]:
        assert set(row) == {"name", "started_at", "where", "state", "su", "usd", "unknown_reasons", "usd_approx"}
    assert set(got["cloud"]) == {"used_usd", "unknown_runs", "cap_usd", "remaining_usd", "currency"}


def test_tc023_tc024_mcp_same_as_actions(w):
    from helpers import tool_json
    ann = two_runs(w)
    rid = seed(w, "run-n", ann, hours=51.5)
    as_nano4(w, "run-n")
    assert tool_json(w.call("my_usage", {}, caller=ann)) == json.loads(json.dumps(usage(w, ann)))
    assert tool_json(w.call("get_run", {"run_id": rid}, caller=ann))["su"] == json.loads(json.dumps(get_run(w, ann, rid)["su"]))


def test_tc025_mcp_descriptions_say_usd_approx():
    src = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    assert src.count("usd_approx") >= 2
    from test_actions_layer import BASELINE
    base = {t["name"]: t["description"] for t in json.loads(BASELINE)["tools"]}
    import asyncio
    from test_actions_layer import _server, _tools
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        tools = {t.name: t.description for t in _tools(_server(str(Path(d) / "index.db")))}
    for name in ("get_run", "my_usage"):
        assert "usd_approx" in tools[name] and tools[name].startswith(base[name])


def test_tc026_tc027_tc028_unknown_su_gives_none(w):
    ann = w.user("ann")
    seed(w, "run-open", ann, hours=None)                    # no usage rows: SU cannot be worked out
    seed(w, "run-live", ann, status="running")
    got = usage(w, ann)
    assert got["su"]["total"] is None and got["su"]["usd_approx"] is None                        # TC-026
    assert all(r["usd_approx"] is None for r in got["runs"])                                     # TC-026, TC-027
    live = seed(w, "run-live2", ann, status="running")
    assert get_run(w, ann, live)["su"]["usd_approx"] is None                                     # TC-028


def test_tc029_to_031_missing_usd_twd(w, tmp_path, monkeypatch):
    ann = two_runs(w)
    rid = seed(w, "run-n", ann, hours=3)
    plain_total = usage(w, ann)["su"]["total"]
    cases = ({"usd_twd": "DROP"},
             {"usd_twd": {"rate": 32.0}},                                                        # TC-030
             {"usd_twd": {"as_of": "2026-10-13"}})                                               # TC-031
    for change in cases:
        set_rates(tmp_path, monkeypatch, **change)
        got = usage(w, ann)
        assert got["su"]["usd_approx"] is None and got["su"]["usd_rate_as_of"] is None, change
        assert got["su"]["total"] == pytest.approx(plain_total)
        assert all(r["usd_approx"] is None for r in got["runs"])
    set_rates(tmp_path, monkeypatch, usd_twd="DROP")
    assert get_run(w, ann, rid)["su"]["usd_approx"] is None and get_run(w, ann, rid)["su"]["su"] == pytest.approx(3)


def test_tc032_owner_rule(w):
    ann, bob = w.user("ann"), w.user("bob")
    rid = seed(w, "ann-run", ann, hours=5)
    assert get_run(w, bob, rid)["found"] is False and "usd_approx" not in json.dumps(get_run(w, bob, rid))
    mine = usage(w, bob)
    assert mine["runs"] == [] and "ann-run" not in json.dumps(mine) and mine["su"]["total"] == 0
    assert [r["name"] for r in usage(w, ann)["runs"]] == ["ann-run"]
    assert get_run(w, ann, rid)["su"]["usd_approx"] is not None


def test_tc033_parity_and_read_only():
    from abf_platform import actions
    src = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    tools = set(re.findall(r'name="([a-z_]+)"', src))
    assert tools == {"cancel", "forget", "get_compute_env", "get_run", "launch", "list_agents", "list_compute_envs", "list_runs",
                     "list_site_files", "list_used_pipelines", "my_usage", "read_run_file", "read_task_log", "relaunch", "resume", "run_outputs",
                     "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}   # base plus the five canvas reads (canvas-mcp-read)
    import abf_platform.actions.catalogue as cat_actions    # canvas-mcp-read: the five canvas reads have their actions in these two submodules
    import abf_platform.actions.pipelines as pipe_actions
    canvas = {"find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation"}
    for name in canvas:
        assert callable(getattr(cat_actions, name, None)) or callable(getattr(pipe_actions, name, None)), name
    for name in tools - {"launch", "cancel", "resume", "relaunch", "forget"} - canvas:
        assert callable(getattr(actions, name, None)), name
    for name in ("get_run", "my_usage"):
        assert re.search(r'name="%s", annotations=_READ_ONLY' % name, src)
    web = (PKG / "web.py").read_text(encoding="utf-8")
    assert "actions.my_usage" in web and "actions.get_run" in web


def test_tc034_no_leaks_when_config_missing(w, tmp_path, monkeypatch, caplog):
    ann = two_runs(w)
    rid = seed(w, "run-n", ann, hours=3)
    from abf_platform import su
    monkeypatch.setattr(su, "RATES_PATH", tmp_path / "nowhere.json")
    out = json.dumps([usage(w, ann), get_run(w, ann, rid)], ensure_ascii=False)
    for url in ("/usage", "/?run=" + rid):
        r = login_get(w, "ann", url)
        assert r.status_code == 200
        for text in (r.text, out):
            assert "Traceback" not in text and "su_rates.json" not in text and "nowhere" not in text
    assert "su_rates.json" not in caplog.text and "token" not in caplog.text.lower()


# ---- US3: the cost page -----------------------------------------------------------------------------------------------------

def rows_by_name(text):
    return {r[0]: r for r in table_rows(text)}


def test_tc035_nano4_row(w):
    ann = w.user("ann")
    seed(w, "run-n", ann, hours=51.5)
    as_nano4(w, "run-n")
    r = get(w, "ann")
    assert rows_by_name(r.text)["run-n"][3] == "51.50 SU（約 US$0.16）"


def test_tc036_to_038_card_and_rows(w, monkeypatch):
    ann = two_runs(w)
    r = get(w, "ann")
    assert card(r.text, 0)[2] == "12.30 SU（約 US$0.03）"                                          # TC-036
    rows = rows_by_name(r.text)
    assert rows["run-a"][3] == "5.10 SU（約 US$0.01）" and rows["run-b"][3] == "7.20 SU（約 US$0.02）"      # TC-037
    from abf_platform import actions
    real = actions.my_usage

    def stub(*a, **k):
        d = real(*a, **k)
        d["su"] = dict(d["su"], usd_approx=1.2345)
        d["runs"] = [dict(x, usd_approx=1.2345) for x in d["runs"]]
        return d
    monkeypatch.setattr(actions, "my_usage", stub)
    r = get(w, "ann")
    assert "約 US$1.23" in card(r.text, 0)[2] and all("約 US$1.23" in row[3] for row in table_rows(r.text))   # TC-038


def test_tc039_tc040_cloud_unchanged(w):
    ann = w.user("ann")
    seed(w, "cl-a", ann, "cloud", hours=61.7)
    seed(w, "run-a", ann, hours=5.10)
    from test_web_cost import cap
    cap(w, ann, 50)
    r = get(w, "ann")
    assert rows_by_name(r.text)["cl-a"][3] == "US$ 12.34"                                         # TC-039
    assert [c[2] for c in cards(r.text)][1:] == ["US$ 12.34", "US$ 50.00", "US$ 37.66"]          # TC-040
    assert all("約 US$" not in c[2] for c in cards(r.text)[1:])


def test_tc041_tc042_small_amounts(w):
    ann = w.user("ann")
    seed(w, "run-s", ann, hours=3.0)
    r = get(w, "ann")
    assert card(r.text, 0)[2] == "3.00 SU（約 US$0.01 以下）" and rows_by_name(r.text)["run-s"][3] == "3.00 SU（約 US$0.01 以下）"   # TC-041
    assert "0.00" not in card(r.text, 0)[2]
    seed(w, "run-t", ann, hours=5.10)
    assert rows_by_name(get(w, "ann").text)["run-t"][3] == "5.10 SU（約 US$0.01）"               # TC-042


def test_tc043_tc044_footnote(w, tmp_path, monkeypatch):
    two_runs(w)
    note = "雲端費用以美元顯示，不換算新台幣；國網以 SU 計。數字依執行紀錄估算，略低於實際帳單。"
    mid = plain(pane(get(w, "ann").text, "middle"))
    assert note + "SU 以 2026-10-13 匯率概算為美元，並非帳單金額。" in mid                         # TC-043
    data = real_rates()
    set_rates(tmp_path, monkeypatch, usd_twd=dict(data["usd_twd"], as_of="2026-11-02"))
    assert "SU 以 2026-11-02 匯率概算為美元，並非帳單金額。" in plain(pane(get(w, "ann").text, "middle"))   # TC-044


def test_tc045_to_049_english(w):
    ann = two_runs(w)
    seed(w, "run-s", ann, hours=3.0)
    r = get(w, "ann", "/usage?lang=en")
    assert card(r.text, 0)[2] == "15.30 SU (≈ US$0.04)"                                          # 12.30 + 3.00 = 15.30 -> 0.0382
    rows = rows_by_name(r.text)
    assert rows["run-a"][3] == "5.10 SU (≈ US$0.01)" and rows["run-b"][3] == "7.20 SU (≈ US$0.02)"        # TC-046
    assert rows["run-s"][3] == "3.00 SU (≈ under US$0.01)"                                       # TC-047
    mid = plain(pane(r.text, "middle"))
    assert "SU figures are converted to US dollars at the 2026-10-13 rate, roughly; this is not a bill." in mid    # TC-048
    assert no_cjk(r.text)                                                                        # TC-049


def test_tc047_card_under_a_cent_english(w):
    ann = w.user("ann")
    seed(w, "run-s", ann, hours=3.0)
    assert card(get(w, "ann", "/usage?lang=en").text, 0)[2] == "3.00 SU (≈ under US$0.01)"


def test_tc050_tc051_front_end_limits(w, tmp_path, monkeypatch):
    import base64
    import hashlib
    two_runs(w)
    shown = {}
    for lang in ("zh", "en"):
        r = get(w, "ann", "/usage" + ("?lang=en" if lang == "en" else ""))
        t = r.text
        assert "約 US$" in t or "≈ US$" in t
        assert "<script" not in t and "style=" not in t and "<link" not in t and t.count("<style>") == 1
        assert not re.search(r"\son[a-z]+=", t) and not re.findall(r"https?://", re.sub(r"<style>.*?</style>", "", t, flags=re.S))
        csp = r.headers["content-security-policy"]
        digest = base64.b64encode(hashlib.sha256(style_of(t).encode("utf-8")).digest()).decode()
        assert "style-src 'sha256-%s'" % digest in csp and "script-src" not in csp and "unsafe-inline" not in csp
        shown[lang] = (style_of(t), set(re.findall(r'class="([^"]+)"', t)))
    set_rates(tmp_path, monkeypatch, usd_twd="DROP")
    plain_page = get(w, "ann").text                                                              # TC-051
    assert shown["zh"][0] == style_of(plain_page) and shown["zh"][1] == set(re.findall(r'class="([^"]+)"', plain_page))


def test_tc052_status_words(w):
    ann = w.user("ann")
    seed(w, "run-live", ann, status="running")
    seed(w, "run-done", ann, hours=5.10)
    rows = rows_by_name(get(w, "ann").text)
    assert rows["run-live"][4] == "執行中" and rows["run-done"][4] == "≈ 估算・帳單未到"


def test_tc053_used_up_still_shows_usd(w):
    from test_web_cost import cap
    ann = w.user("ann")
    seed(w, "cl-a", ann, "cloud", hours=61.7)
    seed(w, "run-a", ann, hours=5.10)
    cap(w, ann, 10)
    r = get(w, "ann")
    left = card(r.text, 3)
    assert "state-failed" in left[0] and "⚠" in left[3] and "待處理：本月雲端額度已用盡" in left[3]
    assert card(r.text, 0)[2] == "5.10 SU（約 US$0.01）"


def test_tc054_tc055_unknown_su(w):
    ann = w.user("ann")
    seed(w, "run-open", ann, hours=None)
    r = get(w, "ann")
    c = card(r.text, 0)
    assert c[2] == "—" and c[3] and "約 US$" not in r.text.split("</style>")[1]
    assert rows_by_name(r.text)["run-open"][3] == "—"


def test_tc056_tc057_tc060_no_rate_in_config(w, tmp_path, monkeypatch):
    two_runs(w)
    for change in ({"usd_twd": "DROP"}, {"usd_twd": {"rate": 32.0}}):
        set_rates(tmp_path, monkeypatch, **change)
        for url in ("/usage", "/usage?lang=en"):
            r = get(w, "ann", url)
            body = r.text.split("</style>")[1]
            assert "約 US$" not in body and "≈" not in body.replace("≈ 估算", "").replace("≈ Estimate", "")
            assert "換美元" not in body and "converted to US dollars" not in body
        r = get(w, "ann")
        assert card(r.text, 0)[2] == "12.30"
        rows = rows_by_name(r.text)
        assert rows["run-a"][3] == "5.10 SU" and rows["run-b"][3] == "7.20 SU"
        assert "雲端費用以美元顯示" in plain(pane(r.text, "middle"))


def test_tc058_tc059_zero(w):
    ann = w.user("ann")
    seed(w, "cl-a", ann, "cloud", hours=6)
    r = get(w, "ann")
    assert card(r.text, 0)[2] == "0.00" and "約 US$" not in card(r.text, 0)[2]                   # TC-058
    seed(w, "run-z", ann, hours=0.0)
    r = get(w, "ann")
    assert rows_by_name(r.text)["run-z"][3] == "0.00 SU"                                         # TC-059


def test_tc061_tc062_empty_and_unreadable(w, monkeypatch):
    w.user("ann")
    r = get(w, "ann")
    assert r.status_code == 200 and "— 本月尚無分析" in plain(pane(r.text, "middle")) and table_rows(r.text) == []
    assert "約 US$" not in r.text.split("</style>")[1]
    from abf_platform import actions, web_cost
    monkeypatch.setattr(actions, "my_usage", lambda *a, **k: web_cost.empty_usage(k.get("month") or "2026-10"))
    r = get(w, "ann")
    assert r.status_code == 200 and "— 本月尚無分析" in plain(pane(r.text, "middle"))


# ---- US4: the run page -------------------------------------------------------------------------------------------------------

def test_tc066_to_070_run_page_cost_card(w):
    ann = w.user("ann")
    rid = seed(w, "run-n", ann, hours=51.5)
    as_nano4(w, "run-n")
    assert cost_value(login_get(w, "ann", "/?run=" + rid).text) == "51.50 SU（約 US$0.16）"       # TC-066
    en = login_get(w, "ann", "/?run=%s&lang=en" % rid)
    assert cost_value(en.text) == "51.50 SU (≈ US$0.16)" and no_cjk(en.text.replace("找不到", ""))   # 找不到: a reason the outputs tab already shows                       # TC-069
    small = seed(w, "run-s", ann, hours=3.0, ce="nchc2")
    assert cost_value(login_get(w, "ann", "/?run=" + small).text) == "3.00 SU（約 US$0.01 以下）"   # TC-068
    assert cost_value(login_get(w, "ann", "/?run=%s&lang=en" % small).text) == "3.00 SU (≈ under US$0.01)"   # TC-070
    failed = seed(w, "run-f", ann, status="failed", hours=5.10, ce="nchc2")                                    # TC-067
    view = get_run(w, ann, failed)
    from abf_platform import web_board
    want = "%.2f SU（約 US$%.2f）" % (view["su"]["su"], view["su"]["usd_approx"])
    assert cost_value(login_get(w, "ann", "/?run=" + failed).text) == want


def test_tc071_run_page_uses_get_run_only(w, monkeypatch):
    ann = w.user("ann")
    rid = seed(w, "run-a", ann, hours=5)
    from abf_platform import actions, su
    canned = actions.get_run(w.ip.index, rid, caller=ann, platform_path=w.ip.state_db)
    canned["su"] = dict(canned["su"], su=7.0, usd_approx=7.77)

    def stub(*a, **k):
        return dict(canned)
    monkeypatch.setattr(actions, "get_run", stub)
    calls = []
    monkeypatch.setattr(actions, "my_usage", lambda *a, **k: calls.append("my_usage"))
    monkeypatch.setattr(su, "load_rates", lambda *a, **k: calls.append("rates") or None)
    assert cost_value(login_get(w, "ann", "/?run=" + rid).text) == "7.00 SU（約 US$7.77）"
    assert "my_usage" not in calls and "rates" not in calls


def test_tc072_run_page_limits(w, tmp_path, monkeypatch):
    ann = w.user("ann")
    ids = [seed(w, "run-ok", ann, hours=5.1), seed(w, "run-f", ann, status="failed", hours=5.1)]
    with_usd = {}
    for rid in ids:
        for lang in ("", "&lang=en"):
            t = login_get(w, "ann", "/?run=%s%s" % (rid, lang)).text
            assert "<script" not in t and "style=" not in t and t.count("<style>") == 1
            with_usd[(rid, lang)] = (style_of(t), set(re.findall(r'class="([^"]+)"', t)))
    set_rates(tmp_path, monkeypatch, usd_twd="DROP")
    for (rid, lang), (style, classes) in with_usd.items():
        t = login_get(w, "ann", "/?run=%s%s" % (rid, lang)).text
        assert style_of(t) == style and set(re.findall(r'class="([^"]+)"', t)) == classes


def test_tc073_tc074_unknown_su_keeps_dash(w):
    ann = w.user("ann")
    live = seed(w, "run-live", ann, status="running")
    assert cost_value(login_get(w, "ann", "/?run=" + live).text) == "SU —"
    open_ = seed(w, "run-open", ann, hours=None)
    assert cost_value(login_get(w, "ann", "/?run=" + open_).text) == "SU —"


def test_tc075_tc076_run_page_no_rate_or_zero(w, tmp_path, monkeypatch):
    ann = w.user("ann")
    rid = seed(w, "run-a", ann, hours=5.1)
    zero = seed(w, "run-z", ann, hours=0.0)
    assert cost_value(login_get(w, "ann", "/?run=" + zero).text) == "0.00 SU"                       # TC-076
    set_rates(tmp_path, monkeypatch, usd_twd="DROP")
    assert cost_value(login_get(w, "ann", "/?run=" + rid).text) == "5.10 SU"                        # TC-075


def test_tc077_other_user_sees_not_found(w):
    ann, bob = w.user("ann"), w.user("bob")
    rid = seed(w, "ann-run", ann, hours=5)
    r = login_get(w, "bob", "/?run=" + rid)                                   # somebody else's run
    gone = login_get(w, "bob", "/?run=deadbeefdeadbeef")                      # a run that is not there at all
    assert r.status_code == gone.status_code == 404, (r.status_code, gone.status_code)
    assert r.text == gone.text                                                # the very same 404 page, nothing to tell them apart
    assert "找不到該次分析" in r.text
    assert "5.00 SU" not in r.text and "約 US$" not in r.text.split("</style>")[1]


# ---- US5: what is not done ---------------------------------------------------------------------------------------------------

def test_tc078_no_network(w, monkeypatch):
    ann = two_runs(w)
    rid = seed(w, "run-n", ann, hours=3)
    real_connect = socket.socket.connect

    def refuse(self, addr, *a, **k):
        if isinstance(addr, tuple):                        # an internet address; the test client itself uses no socket
            raise AssertionError("network used: %r" % (addr,))
        return real_connect(self, addr, *a, **k)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    assert usage(w, ann)["su"]["usd_approx"] is not None
    assert get_run(w, ann, rid)["su"]["usd_approx"] is not None
    assert "約 US$" in get(w, "ann").text
    assert "約 US$" in login_get(w, "ann", "/?run=" + rid).text


def test_tc079_no_ntd(w):
    ann = two_runs(w)
    rid = seed(w, "run-n", ann, hours=3)
    for url in ("/usage", "/usage?lang=en", "/?run=" + rid, "/?run=%s&lang=en" % rid):
        body = login_get(w, "ann", url).text.split("</style>")[1].replace("不換算新台幣", "").replace("New Taiwan dollars", "")
        assert "NT$" not in body and "twd" not in body.lower() and "新台幣" not in body


def test_tc081_masthead_unchanged(w):
    ann = two_runs(w)
    rid = seed(w, "run-n", ann, hours=3)
    for url, want in (("/", ["SU —", "雲端 US$ —"]), ("/settings", ["SU —", "雲端 US$ —"]), ("/launch", ["SU —", "雲端 US$ —"]),
                      ("/usage", ["SU —", "雲端 US$ —"]), ("/?run=" + rid, ["SU —", "雲端 US$ —"]), ("/?lang=en", ["SU —", "Cloud US$ —"])):
        t = login_get(w, "ann", url).text
        m = re.search(r'<a class="costs".*?</a>', t, re.S)
        text = plain(m.group(0))
        assert all(x in text for x in want) and "約" not in text and "≈" not in text, url


def test_tc082_settings_has_no_rate_field(w):
    w.user("ann")
    t = login_get(w, "ann", "/settings").text
    inputs = re.findall(r"<(?:input|select|textarea)\b[^>]*>", t)
    assert not any(re.search(r"(?i)rate|usd|匯率", x) for x in inputs)


def test_tc083_no_migration():
    assert not [p for p in PKG.rglob("*") if "migrat" in p.name.lower()]
    for name in ("su.py", "web_cost.py", "web_board.py"):
        text = (PKG / name).read_text(encoding="utf-8")
        assert "CREATE TABLE" not in text and "ALTER TABLE" not in text, name


# ---- constitution -------------------------------------------------------------------------------------------------------------

def test_tc089_nothing_stored_and_no_cache(w, tmp_path, monkeypatch):
    ann = two_runs(w)
    rid = seed(w, "run-n", ann, hours=3)

    def snapshot():
        out = {}
        for path in (w.ip.index, w.ip.state_db):
            con = sqlite3.connect(str(path))
            for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                out[(path.name, name)] = con.execute("SELECT * FROM %s" % name).fetchall()
            con.close()
        return out
    before = snapshot()
    first = usage(w, ann)["su"]["usd_approx"]
    get_run(w, ann, rid)
    get(w, "ann")
    login_get(w, "ann", "/?run=" + rid)
    assert snapshot() == before
    data = real_rates()
    set_rates(tmp_path, monkeypatch, usd_twd=dict(data["usd_twd"], rate=40.0))
    assert usage(w, ann)["su"]["usd_approx"] == pytest.approx(first * 32 / 40)


def test_tc091_gaps_are_not_zero_dollars(w, tmp_path, monkeypatch):
    ann = w.user("ann")
    rid = seed(w, "run-a", ann, hours=5.1)
    seed(w, "run-open", ann, hours=None)
    set_rates(tmp_path, monkeypatch, usd_twd="DROP")
    for url in ("/usage", "/usage?lang=en", "/?run=" + rid):
        body = login_get(w, "ann", url).text.split("</style>")[1]
        assert "US$0.00" not in body and "約 US$0" not in body
