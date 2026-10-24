# Nothing existing: tests of the finished stage (provenance + delivery package list, DESIGN.md v2 screen 10); the page is ours.
"""finished-stage: test cases are named in the comments (TC-001 ...), see specs/finished-stage/test-case.md."""
import base64
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

from human_harness import World
from test_web_board import no_cjk, pane, plain, seed, style_of
from test_web_results_outputs import ENTRIES, finish, launch_to, listings

NOW = time.time()
HOUR = 3600
LAUNCHED = 1_760_000_000          # a fixed instant, so the shown time is known
PARAMS = {"max_cpus": 8, "outdir": "/very/long/" + "x" * 150, "skip_qc": True}


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def keep(w, name, bundle):
    """Give the launch row of `name` a confirmed confirmation that holds `bundle` (what launch_prefill reads)."""
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE launches SET confirmed_at = ? WHERE run_name = ?", (LAUNCHED, name))
        con.execute("INSERT INTO confirmations (id, sha256, kind, created_at, state, channel, confirmed_at, ce_name, bundle_json) "
                    "VALUES (?, 'abc', 'launch', ?, 'confirmed', 'WEB', ?, 'lab-a', ?)", ("c-" + name, LAUNCHED - 5, LAUNCHED, json.dumps(bundle)))
    con.close()


def forget(w, name):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE confirmations SET forgotten_at = ?, bundle_json = NULL WHERE id = ?", (NOW, "c-" + name))
    con.close()


def world(w, name="ann-done", params=PARAMS, kept=True, who="ann"):
    ann = w.user(who)
    rid = seed(w, name, "succeeded", ann, started=NOW - 3 * HOUR, ended=NOW - 2 * HOUR, counts=dict(succeeded=4))
    launch_to(w, name, "/data/wd/runs/" + name)
    if kept:
        keep(w, name, {"pipeline": "nf-core/ampliseq", "revision": "2.11.0", "params": dict(params),
                       "samplesheet": [{"sample": "SECRET_SAMPLE_1", "fastq_1": "a.fq"}]})
    c = w.web()
    assert w.login(c, who).status_code == 303
    return ann, c, rid


def url(rid, extra=""):
    return "/?run=%s&stage=finished%s" % (rid, extra)


def mid(text):
    return pane(text, "middle")


def section(text, title):
    m = re.search(r'<section class="card"><h2>%s</h2>(.*?)</section>' % re.escape(title), mid(text), re.S)
    assert m, title
    return m.group(1)


def prov_rows(text, title="來源紀錄"):
    return re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", section(text, title), re.S)


def pack_rows(text, title="交付包"):
    return [(plain(k), plain(v)) for k, v in re.findall(r"<li><span>(.*?)</span> (.*?)</li>", section(text, title), re.S)]


def read_outputs(w, rid, c, entries):
    c.get("/?run=%s&stage=results&tab=outputs" % rid)          # the Outputs tab queues the listing
    finish(w, listings(w)[-1]["id"], entries=entries)


def no_launch_record(w):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("DELETE FROM launches")
    con.close()


def test_fs01_succeeded_run_opens_finished_stage(w):
    # TC-040, TC-020, TC-047, TC-001
    ann, c, rid = world(w)
    t = c.get(url(rid)).text
    m = mid(t)
    assert "來源紀錄" in m and "交付包" in m and "013b" not in m and "還沒到這個階段" not in m
    assert [plain(k) for k, _ in prov_rows(t)] == ["管線", "版本", "改過的參數", "運算環境", "送出時間", "完成時間", "送出者", "樣本表"]
    assert [k for k, _ in pack_rows(t)] == ["報告", "結果表格", "MultiQC 報告", "圖", "方法段落（含版本）", "樣本表"]
    assert m.count('class="steps"') == 1 and 'rel="prev"' in m


def test_fs02_other_states_not_reached(w, monkeypatch):
    # TC-041, TC-042, TC-043, TC-044, TC-046
    from abf_platform import actions
    calls = []
    monkeypatch.setattr(actions, "launch_prefill", lambda *a, **k: calls.append("prefill") or {"found": False})
    real = actions.run_outputs
    monkeypatch.setattr(actions, "run_outputs", lambda *a, **k: calls.append("outputs") or real(*a, **k))
    ann = w.user("ann")
    ids = {st: seed(w, "n-" + st, st, ann) for st in ("running", "failed", "lost")}
    c = w.web()
    w.login(c, "ann")
    for st, rid in ids.items():
        t = c.get(url(rid)).text
        assert "這個 run 還沒到這個階段。" in mid(t) and "來源紀錄" not in mid(t) and "交付包" not in mid(t), st
        t2 = c.get("/?run=%s&stage=running" % rid).text
        cell = re.search(r'<li[^>]*data-step="finished"[^>]*>(.*?)</li>', mid(t2), re.S)
        assert "is-later" in cell.group(0) and "<a" not in cell.group(1) and "完成" in cell.group(1), st
    assert calls == []


def test_fs03_provenance_kept(w):
    # TC-002, TC-003, TC-005, TC-006, TC-007, TC-008
    ann, c, rid = world(w)
    t = c.get(url(rid)).text
    rows = dict((plain(k), v) for k, v in prov_rows(t))
    assert rows["管線"] == "nf-core/ampliseq" and rows["版本"] == "2.11.0" and rows["運算環境"] == "lab-a"
    codes = re.findall(r"<code>(.*?)</code>", rows["改過的參數"])
    assert codes == ["max_cpus: 8", "outdir: " + PARAMS["outdir"], "skip_qc: true"]
    from abf_platform import web_board
    assert plain(rows["送出時間"]) == web_board.taipei_time(LAUNCHED)
    assert re.fullmatch(r"\d\d-\d\d \d\d:\d\d", plain(rows["完成時間"])) and not re.search(r"\d{4}-\d\d-\d\dT|Z\b", rows["完成時間"])
    assert plain(rows["送出者"]) == "ann"
    assert rows["樣本表"] == '<span class="later">之後開放</span>' and "<a" not in rows["樣本表"]
    assert "style=" not in t


def test_fs03b_no_changed_parameters(w):
    # TC-004
    ann, c, rid = world(w, params={})
    rows = dict((plain(k), plain(v)) for k, v in prov_rows(c.get(url(rid)).text))
    assert rows["改過的參數"] == "— 全部用預設值"


def test_fs04_provenance_not_kept(w):
    # TC-009, TC-010, TC-011
    ann, c, rid = world(w)
    forget(w, "ann-done")
    t = c.get(url(rid)).text
    sec = section(t, "來源紀錄")
    assert "這次送出的內容已不保留。" in sec and sec.index("這次送出的內容已不保留。") < sec.index("<dl")
    rows = dict((plain(k), plain(v)) for k, v in prov_rows(t))
    for k in ("管線", "版本", "改過的參數", "運算環境"):
        assert rows[k] == "— 內容已不保留", k
    assert re.fullmatch(r"\d\d-\d\d \d\d:\d\d", rows["送出時間"]) and re.fullmatch(r"\d\d-\d\d \d\d:\d\d", rows["完成時間"])
    assert "nf-core" not in t and "2.11.0" not in t and "max_cpus" not in t
    assert "—" in sec


def test_fs05_not_from_platform(w):
    # TC-012, TC-013, TC-014, TC-C03
    ann, c, rid = world(w, kept=False)
    no_launch_record(w)
    t = c.get(url(rid)).text
    sec = section(t, "來源紀錄")
    assert plain(sec) == "— 不是從平台送出的分析，沒有來源紀錄。" and "<dl" not in sec
    for label in ("管線", "版本", "運算環境"):
        assert label not in sec
    assert len(pack_rows(t)) == 6


def test_fs06_package_rows_follow_outputs(w):
    # TC-021, TC-022, TC-023, TC-024, TC-025, TC-026, TC-027, TC-028, TC-029, TC-030, TC-031, TC-032, TC-036, TC-C03
    ann, c, rid = world(w)
    page = c.get(url(rid)).text
    rows = dict(pack_rows(page))
    assert rows["結果表格"].startswith("— 尚未讀取輸出") and rows["MultiQC 報告"].startswith("— 尚未讀取輸出")
    assert 'href="/?run=%s&amp;stage=results&amp;tab=outputs"' % rid in section(page, "交付包")
    for k in ("報告", "圖", "方法段落（含版本）", "樣本表"):
        assert rows[k] == "之後開放", k
    c.get("/?run=%s&stage=results&tab=outputs" % rid)         # queued, not answered yet
    rows = dict(pack_rows(c.get(url(rid)).text))
    assert rows["結果表格"].startswith("— 尚未讀取輸出") and "✓" not in rows["結果表格"] and "沒有" not in rows["MultiQC 報告"]
    finish(w, listings(w)[-1]["id"], entries=ENTRIES)
    rows = dict(pack_rows(c.get(url(rid)).text))
    assert rows["結果表格"] == "✓ 在輸出資料夾" and rows["MultiQC 報告"] == "✓ 在輸出資料夾"
    finish(w, listings(w)[-1]["id"], entries=[e for e in ENTRIES if e["name"] != "multiqc"])
    rows = dict(pack_rows(c.get(url(rid)).text))
    assert rows["結果表格"] == "✓ 在輸出資料夾" and rows["MultiQC 報告"] == "— 這次沒有產生"
    finish(w, listings(w)[-1]["id"], entries=[{"name": "multiqc_data", "type": "dir", "size": 1, "modified": ""},
                                              {"name": "multiqc", "type": "file", "size": 1, "modified": ""}])
    assert dict(pack_rows(c.get(url(rid)).text))["MultiQC 報告"] == "— 這次沒有產生"
    finish(w, listings(w)[-1]["id"], entries=[])
    rows = dict(pack_rows(c.get(url(rid)).text))
    assert rows["結果表格"] == "— 沒有檔案"
    finish(w, listings(w)[-1]["id"], ok=False, state="done", message="no")
    assert dict(pack_rows(c.get(url(rid)).text))["結果表格"].startswith("— 尚未讀取輸出")


def test_fs07_finished_page_never_queues_a_listing(w, monkeypatch):
    # TC-033, TC-034, TC-050, TC-092
    from abf_platform import actions
    seen = []
    real = actions.run_outputs
    monkeypatch.setattr(actions, "run_outputs", lambda *a, **k: seen.append(k) or real(*a, **k))
    pre = []
    real_pre = actions.launch_prefill
    monkeypatch.setattr(actions, "launch_prefill", lambda *a, **k: pre.append(1) or real_pre(*a, **k))
    ann, c, rid = world(w)
    for _ in range(3):
        c.get(url(rid))
    assert listings(w) == [] and seen and all(k.get("enqueue") is False for k in seen)
    n = len(pre)
    c.get("/?run=%s&stage=launch" % rid)
    c.get("/?run=%s&stage=running" % rid)
    c.get("/?run=%s&stage=results" % rid)
    assert len(pre) == n
    src = (Path(__file__).resolve().parent.parent / "abf_platform" / "web_finished.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(socket|ssl|http|urllib|requests|subprocess|paramiko)", src, re.M)


def test_fs08_download_is_coming_later(w):
    # TC-035, TC-090
    ann, c, rid = world(w)
    t = c.get(url(rid)).text
    sec = section(t, "交付包")
    assert '<p class="off">下載交付包 <span class="later">之後開放</span></p>' in sec
    assert 'href="/download' not in t and "<form" not in mid(t) and "<button" not in mid(t)
    assert [j for j in w.sql("SELECT kind FROM jobs") if j["kind"] != "list_site_files"] == []


def test_fs09_owner_rule(w, monkeypatch):
    # TC-048, TC-049
    from abf_platform import actions
    ann, c, rid = world(w)
    w.user("bob")
    bob = w.web()
    assert w.login(bob, "bob").status_code == 303
    calls = []
    monkeypatch.setattr(actions, "launch_prefill", lambda *a, **k: calls.append(1) or {"found": False})
    monkeypatch.setattr(actions, "run_outputs", lambda *a, **k: calls.append(1) or {})
    r = bob.get(url(rid))
    assert r.status_code == 404 and "nf-core" not in r.text and "max_cpus" not in r.text and calls == []


def test_fs10_english(w):
    # TC-060, TC-074, TC-075
    ann, c, rid = world(w)
    t = c.get(url(rid, "&lang=en")).text
    assert no_cjk(t) and "Provenance" in t and "Delivery package" in t
    assert [plain(k) for k, _ in prov_rows(t, "Provenance")] == ["Pipeline", "Revision", "Changed parameters", "Compute environment",
                                                                 "Launched", "Finished", "Launched by", "Samplesheet"]
    assert [k for k, _ in pack_rows(t, "Delivery package")] == ["Report", "Tables", "MultiQC report", "Figures", "Methods with versions",
                                                                "Samplesheet"]
    sec = section(t, "Delivery package")
    assert "Download delivery package" in sec and "Coming later" in sec and "<a" in sec and 'href="/download' not in t
    forget(w, "ann-done")
    assert no_cjk(c.get(url(rid, "&lang=en")).text)
    read_outputs(w, rid, c, ENTRIES)
    assert no_cjk(c.get(url(rid, "&lang=en")).text)
    no_launch_record(w)
    assert no_cjk(c.get(url(rid, "&lang=en")).text)


def test_fs11_constraints_hold(w):
    # TC-062, TC-070, TC-071, TC-072, TC-073, TC-077, TC-097
    ann, c, rid = world(w)
    for state in ("kept", "gone"):
        if state == "gone":
            forget(w, "ann-done")
        r = c.get(url(rid))
        t = r.text
        assert "<script" not in t and "style=" not in t and t.count("<style>") == 1
        digest = base64.b64encode(hashlib.sha256(style_of(t).encode("utf-8")).digest()).decode("ascii")
        assert "style-src 'sha256-%s'" % digest in r.headers["content-security-policy"]
        assert re.search(r'<meta http-equiv="refresh" content="15', t)
        text = plain(section(t, "來源紀錄") + section(t, "交付包"))
        assert not re.search(r"[我你]", re.sub("送出者", "", text))
        assert "SECRET_SAMPLE_1" not in t and "fastq" not in t
    assert re.search(r"\.prov\{[^}]*overflow-wrap:anywhere", style_of(t))
    assert re.search(r"\.prov dd\{[^}]*overflow-wrap:anywhere", style_of(t))


def test_fs12_web_board_touches_are_minimal():
    # TC-082, TC-083
    from abf_platform import web_board
    root = Path(__file__).resolve().parent.parent / "abf_platform"
    src = (root / "web_board.py").read_text(encoding="utf-8")
    assert len(re.findall(r"^from \. import web_finished", src, re.M)) == 1
    assert "finished" not in web_board.PLACEHOLDER
    assert len(re.findall(r"^def render_\w+", (root / "web_finished.py").read_text(encoding="utf-8"), re.M)) == 1
    assert "Provenance" not in src and "來源紀錄" not in src


def test_fs13_finished_link_in_strip(w):
    # TC-045
    ann, c, rid = world(w)
    cell = re.search(r'<li[^>]*data-step="finished"[^>]*>(.*?)</li>', mid(c.get("/?run=" + rid).text), re.S).group(1)
    assert 'href="/?run=%s&amp;stage=finished"' % rid in cell
