# Nothing existing: tests of web-confirm-plain (the confirmation page says it in plain words first, the full content folded).
"""web-confirm-plain: test cases are named in the comments (TC-001 ...), see specs/web-confirm-plain/test-case.md."""
import base64
import csv
import hashlib
import html
import re

import pytest

from helpers import PLATFORM_DIR
from human_harness import csrf_of
from resume_harness import Rig
from test_web_actions import act_form, area_sheet, login, rid_of, run_of, request_of

WEB = PLATFORM_DIR / "abf_platform" / "web.py"


@pytest.fixture
def rig(tmp_path, monkeypatch):
    return Rig(tmp_path, monkeypatch)


def plain_of(text):
    """The plain block as {label: value}, or None when the page has none."""
    m = re.search(r'<dl class="fields plain">(.*?)</dl>', text, re.S)
    if m is None:
        return None
    return {html.unescape(k): html.unescape(v) for k, v in re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", m.group(1), re.S)}


def folded_of(text):
    """(summary text, pre text) of the one <details> of the page, or None."""
    m = re.search(r"<details(?P<attrs>[^>]*)>\s*<summary>(?P<s>.*?)</summary>\s*<pre>(?P<p>.*?)</pre>\s*</details>", text, re.S)
    if m is None:
        return None
    return html.unescape(m.group("s")), html.unescape(m.group("p")), m.group("attrs")


def samples_of(rig):
    with open(rig.w.sheet, newline="", encoding="utf-8") as f:
        return len(list(csv.reader(f))) - 1


def ask(rig, c, verb, run_id):
    fields = act_form(c.get("/?run=" + run_id).text, verb, run_id)
    return rid_of(c.post("/act/" + verb, data=fields))


def launched(rig, ann, **over):
    return rig.w.launch(caller=ann, **over)["id"]


def test_tc001_tc006_tc009_tc013_tc014_launch_page(rig):
    # TC-001, TC-006, TC-009, TC-013, TC-014
    ann = rig.user("ann")
    rid = launched(rig, ann)
    c = login(rig, "ann")
    page = c.get("/c/" + rid).text
    p = plain_of(page)
    assert p == {"種類": "送出新分析", "run 名稱": "run-one", "管線": "nf-core/ampliseq", "版本": "2.18.0", "環境": "lab-a",
                 "樣本數": str(samples_of(rig))}
    assert page.index('class="fields plain"') < page.index("<button")
    summary, pre, attrs = folded_of(page)
    assert pre == request_of(rig, rid)["summary"] and summary == "完整內容（技術細節）" and "open" not in attrs
    assert page.count(html.escape(request_of(rig, rid)["summary"], quote=True)) == 1
    assert not re.search(r"<script|\son\w+=|style=", page)


def test_tc002_tc011_relaunch_and_tc003_tc012_resume(rig):
    # TC-002, TC-003, TC-011, TC-012
    ann = rig.user("ann")
    again = run_of(rig, ann, "run-c")
    failed = run_of(rig, ann, "run-a")
    c = login(rig, "ann")
    rid = ask(rig, c, "relaunch", again)
    page = c.get("/c/" + rid).text
    p = plain_of(page)
    assert p["種類"] == "重跑" and p["run 名稱"] == "run-c-a2" and p["管線"] == "nf-core/ampliseq" and p["版本"] == "2.18.0"
    assert p["環境"] == "lab-a" and p["樣本數"] == str(samples_of(rig))
    summary = request_of(rig, rid)["summary"]
    assert p["新資料夾"] in summary and "run-c-a2" in p["新資料夾"]
    assert folded_of(page)[1] == summary
    rid = ask(rig, c, "resume", failed)
    page = c.get("/c/" + rid).text
    p = plain_of(page)
    assert p["種類"] == "續跑" and p["run 名稱"] == "run-a-a2" and p["管線"] == "nf-core/ampliseq" and p["版本"] == "2.18.0"
    assert p["環境"] == "lab-a" and p["樣本數"] == str(samples_of(rig)) and "新資料夾" not in p
    assert folded_of(page)[1] == request_of(rig, rid)["summary"]


def test_tc004_tc005_tc010_cancel_and_no_placeholders(rig):
    # TC-004, TC-005, TC-010
    ann = rig.user("ann")
    going = run_of(rig, ann, "run-b", status=None)
    c = login(rig, "ann")
    rid = ask(rig, c, "cancel", going)
    page = c.get("/c/" + rid).text
    assert plain_of(page) == {"種類": "取消", "run 名稱": "run-b"}
    assert folded_of(page)[1] == request_of(rig, rid)["summary"]
    launch = plain_of(c.get("/c/" + launched(rig, ann)).text)
    for block in (plain_of(page), launch):
        assert all(v.strip() not in ("", "-", "N/A", "未知") for v in block.values())


def test_tc015_pre_wraps_long_lines():
    # TC-015
    from abf_platform import web_board
    rule = re.search(r"pre\{([^}]*)\}", web_board.STYLE).group(1).replace(" ", "")
    assert "white-space:pre-wrap" in rule and "overflow-wrap:anywhere" in rule


def test_tc017_tc018_confirmed_page(rig):
    # TC-017, TC-018
    ann = rig.user("ann")
    rid = launched(rig, ann)
    c = login(rig, "ann")
    before = plain_of(c.get("/c/" + rid).text)
    assert c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)}).status_code == 200
    page = c.get("/c/" + rid).text
    assert "已送出。工作編號" in page and plain_of(page) == before
    summary, pre, attrs = folded_of(page)
    assert pre == request_of(rig, rid)["summary"] and "open" not in attrs and "<button" not in page


def test_tc019_tc020_expired_and_void_pages_have_neither(rig):
    # TC-019, TC-020
    from abf_platform import actions
    ann = rig.user("ann")
    rid = launched(rig, ann)
    c = login(rig, "ann")
    actions.void_request(rig.state, rid, "test")
    r = c.get("/c/" + rid)
    assert r.status_code == 409 and plain_of(r.text) is None and "<details" not in r.text and "<button" not in r.text


def test_tc021_tc022_tc023_tc024_english(rig):
    # TC-021, TC-022, TC-023, TC-024
    ann = rig.user("ann")
    rid = launched(rig, ann)
    c = login(rig, "ann")
    zh = c.get("/c/" + rid).text
    en = c.get("/c/" + rid + "?lang=en").text
    p = plain_of(en)
    assert set(p) == {"Request", "Run name", "Pipeline", "Version", "Environment", "Samples"}
    assert p["Pipeline"] == "nf-core/ampliseq" and p["Environment"] == "lab-a"
    assert folded_of(en)[0] == "Full content (technical)"
    assert folded_of(en)[1] == folded_of(zh)[1]
    for page in (zh, en):
        assert not re.search(r"<script|\son\w+=|style=", page)


def test_tc025_tc026_one_stylesheet_and_csp(rig):
    # TC-025, TC-026
    ann = rig.user("ann")
    rid = launched(rig, ann)
    c = login(rig, "ann")
    r = c.get("/c/" + rid)
    sheets = re.findall(r"<style>(.*?)</style>", r.text, re.S)
    assert len(sheets) == 1
    digest = "sha256-" + base64.b64encode(hashlib.sha256(sheets[0].encode("utf-8")).digest()).decode("ascii")
    csp = r.headers["content-security-policy"]
    assert digest in csp and "default-src 'none'" in csp and "script-src" not in csp and "unsafe-inline" not in csp


def test_tc029_other_people_see_no_plain_block(rig):
    # TC-029
    ann, bob = rig.user("ann"), rig.user("bob")
    rid = launched(rig, ann)
    c = login(rig, "bob")
    r = c.get("/c/" + rid)
    assert r.status_code == 403 and plain_of(r.text) is None and "run-one" not in r.text and "<details" not in r.text
    assert plain_of(rig.w.web().get("/c/" + rid).text) is None


def test_tc008_facts_are_a_web_only_action_and_web_imports_no_confirm():
    # TC-008
    from test_web_parity import WEB_ONLY
    assert "request_facts" in WEB_ONLY
    src = WEB.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(abf_platform\.)?confirm\b", src, re.M)
