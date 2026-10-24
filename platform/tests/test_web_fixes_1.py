# Nothing existing: tests of web-v2-fixes-1 (header actions in a menu, failed stage cell, stopped-at card, long names).
"""web-v2-fixes-1: the TC numbers are named in the comments (TC-001 ...)."""
import base64
import hashlib
import re

import pytest

from human_harness import World
from test_web_board import no_cjk, pane, plain, strip_cells, style_of
from test_web_v2_skeleton import FAILED_STEP, buttons, left_rows, std


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def page(c, ids, key, lang=""):
    return c.get("/?run=%s%s" % (ids[key], "&lang=en" if lang else "")).text


def head_of(text):
    return re.search(r'<div class="head">(.*?)</div><nav class="views">', text, re.S).group(1)


def menu_of(text):
    return re.search(r'<details class="menu">(.*?)</details>', text, re.S)


def visible_buttons(text):
    mid = re.sub(r"<details\b.*?</details>", "", pane(text, "middle"), flags=re.S)
    return buttons(mid + pane(text, "right")), mid


def cards(text):
    return [(plain(a), plain(b)) for a, b in re.findall(r'<h2 class="ct">(.*?)</h2><p class="cv">(.*?)</p>', text, re.S)]


def test_f01_header_actions_are_in_a_closed_menu(w):
    # TC-001, TC-002, TC-003, TC-014, TC-015, TC-016
    _, c, ids = std(w)
    for lang, word in (("", "更多"), ("en", "More")):
        head = head_of(page(c, ids, "resume", lang))
        m = menu_of(head)
        assert m and head.count('<form class="act"') == m.group(1).count('<form class="act"') == 3
        assert re.search(r'<details class="menu"><summary>%s</summary>' % word, head)
    t = page(c, ids, "running")
    assert menu_of(head_of(t)).group(1).count('<form class="act"') == 3
    done = page(c, ids, "done")
    assert 'class="menu"' not in done and '<form class="act"' not in head_of(done)
    t = c.get("/?run=%s&stage=launch" % ids["resume"]).text
    assert 'class="menu"' not in t and '<form class="act"' not in pane(t, "middle")


def test_f02_one_visible_button_on_a_failed_page(w):
    # TC-004, TC-005, TC-006, TC-007
    _, c, ids = std(w)
    for key, word in (("resume", "續跑"), ("relaunch", "重跑")):
        t = page(c, ids, key)
        bs, mid = visible_buttons(t)
        assert bs == [word]
        assert "<button" in pane(t, "right") and "<button" not in mid
    bs, _ = visible_buttons(page(c, ids, "lost"))
    assert len(bs) == 1 and bs[0] in ("續跑", "重跑")


def test_f03_menu_forms_unchanged(w):
    # TC-008, TC-009, TC-010, TC-011, TC-012, TC-057
    _, c, ids = std(w)
    m = menu_of(page(c, ids, "resume")).group(1)
    assert re.findall(r'action="(/act/\w+)"', m) == ["/act/resume", "/act/relaunch", "/act/cancel"]
    assert buttons(m) == ["續跑", "重跑", "取消"]
    for f in re.findall(r"<form.*?</form>", m, re.S):
        assert 'name="run" value="%s"' % ids["resume"] in f and re.search(r'name="csrf" value="[^"]+"', f)
    assert m.rindex("</form>") < m.index("/launch?from=%s" % ids["resume"])
    en = menu_of(page(c, ids, "resume", "en")).group(1)
    assert buttons(en) == ["Resume", "Re-run", "Cancel"]
    assert en.count('name="lang" value="en"') == 3 and "Launch again from this run" in plain(en)
    for verb in ("resume", "relaunch", "cancel"):
        f = re.search(r'<form class="act" method="post" action="/act/%s">(.*?)</form>' % verb, m, re.S).group(1)
        r = c.post("/act/" + verb, data=dict(re.findall(r'name="(\w+)" value="([^"]*)"', f)))
        assert r.status_code == 200 and "<form" in r.text


def test_f04_running_page_menu_and_no_visible_button(w):
    # TC-013, TC-014, TC-049
    _, c, ids = std(w)
    t = page(c, ids, "running")
    assert visible_buttons(t)[0] == []
    assert re.search(r'<details class="menu"><summary>更多</summary>', t)
    assert buttons(menu_of(t).group(1)) == ["續跑", "重跑", "取消"]


def test_f05_failed_stage_cell(w):
    # TC-019 .. TC-026
    _, c, ids = std(w)
    for key in ("resume", "lost"):
        cells = strip_cells(page(c, ids, key))
        assert plain(cells["running"][1]) == "✗ 執行" and {"is-current", "is-failed"} <= set(cells["running"][0])
    cells = strip_cells(page(c, ids, "resume"))
    order = ("launch", "running", "results", "downstream", "finished")
    assert [plain(cells[s][1]) for s in order] == ["✓ 送出", "✗ 執行", "結果", "下游", "完成"]
    assert [sorted(cells[s][0]) for s in order] == [["is-done"], ["is-current", "is-failed"], ["is-later"], ["is-later"], ["is-later"]]
    en = strip_cells(page(c, ids, "resume", "en"))
    assert plain(en["running"][1]) == "✗ Run" and "is-failed" in en["running"][0]
    run = strip_cells(page(c, ids, "running"))
    assert plain(run["running"][1]) == "執行中" and "is-failed" not in run["running"][0]
    done = strip_cells(page(c, ids, "done"))
    assert plain(done["running"][1]) == "✓ 執行中" and done["running"][0] == ["is-done"]
    assert re.search(r"\.steps \.is-failed[^}]*var\(--(failed|c)\)", style_of(page(c, ids, "resume")))


def test_f06_stopped_at_card(w):
    # TC-027 .. TC-034
    _, c, ids = std(w)
    cs = cards(pane(page(c, ids, "resume"), "middle"))
    assert cs[0] == ("停在", FAILED_STEP) and [x[0] for x in cs[1:]] == ["耗時", "運算環境", "費用"]
    assert cards(pane(page(c, ids, "relaunch"), "middle"))[0] == ("停在", "TRIMGALORE (s1)")
    assert cards(pane(page(c, ids, "stopped"), "middle"))[0] == ("停在", "—")
    assert cards(pane(page(c, ids, "lost"), "middle"))[0] == ("停在", "—")
    en = pane(page(c, ids, "resume", "en"), "middle")
    assert cards(en)[0] == ("Stopped at", FAILED_STEP) and no_cjk(en)
    assert cards(pane(page(c, ids, "running"), "middle"))[0][0] == "目前步驟"
    assert cards(pane(page(c, ids, "running", "en"), "middle"))[0][0] == "Current step"


def test_f07_long_names_wrap(w):
    # TC-035, TC-036, TC-055
    _, c, ids = std(w)
    t = page(c, ids, "resume")
    css = re.sub(r"\s+", "", style_of(t))
    assert re.search(r"\.r2\{[^}]*overflow-wrap:anywhere", css)
    assert "overflow-wrap" not in re.search(r"\.nm\{[^}]*\}", css).group(0)
    assert [x[3] for x in left_rows(t) if "ann-failed-resume" in x[2]][0].endswith(FAILED_STEP)


def test_f08_constraints_hold(w):
    # TC-017, TC-018, TC-039 .. TC-043, TC-046
    _, c, ids = std(w)
    for key in ("resume", "running"):
        r = c.get("/?run=" + ids[key])
        t = r.text
        assert "<script" not in t and "style=" not in t and 'rel="stylesheet"' not in t and t.count("<style>") == 1
        digest = base64.b64encode(hashlib.sha256(re.search(r"<style>(.*?)</style>", t, re.S).group(1).encode()).digest()).decode()
        assert "sha256-" + digest in r.headers["content-security-policy"]
        assert '<meta http-equiv="refresh" content="15">' in t
        assert not re.search(r'(src|href)="https?://', t)
        e = page(c, ids, key, "en")
        assert no_cjk(pane(e, "middle")) and no_cjk(pane(e, "right"))
    css = re.sub(r"\s+", "", style_of(t))
    m = re.search(r"\.menu>summary\{[^}]*\}", css).group(0)
    assert "min-height:44px" in m and "display:flex" in m and "align-items:center" in m
    assert "summary:focus-visible{outline:2px" in css and not re.search(r"(\.menu|summary)[^{]*\{[^}]*outline:(none|0)", css)
