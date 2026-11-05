# Nothing existing: tests of web-bugs-b (#338 cost page words and month titles, #341 title-row facts line, #342 right column, #343 phone targets).
"""web-bugs-b: the TC numbers are named in the comments (TC-001 ...). Pure functions only; no browser."""
import calendar
import re
import subprocess

import pytest

from abf_platform import web_board, web_cost
from human_harness import World
from test_web_board import no_cjk, pane, plain
from test_web_v2_skeleton import std

NOW = calendar.timegm((2026, 11, 15, 4, 0, 0))
TASK = "NFCORE_AMPLISEQ:AMPLISEQ:RENAME_RAW_DATA_FILES"
REASON = "task %s: 分區 ngs8g 沒有 SU 係數 (no SU factor for partition ngs8g)" % TASK


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def usage_data(month="2026-11", reasons=(REASON,), left=None):
    d = web_cost.empty_usage(month)
    d["su"] = {"total": None, "unknown_reasons": list(reasons), "site": None}
    d["cloud"]["remaining_usd"] = left
    return d


def usage(data, lang="zh"):
    return web_cost.render_usage("ann", "tok", [], data, lang=lang, now=NOW)


def middle(text):
    return pane(text, "middle")


def small_of_first_card(text):
    return plain(re.search(r"<small>(.*?)</small>", middle(text), re.S).group(1))


# ---- #338
def test_338_zh_reason_has_no_task_name():  # TC-001, TC-003
    text = usage(usage_data())
    assert "分區 ngs8g 沒有 SU 係數" in small_of_first_card(text)
    assert "NFCORE_AMPLISEQ" not in text and "task " not in text
    assert "(no SU factor" not in small_of_first_card(text)


def test_338_en_reason_unchanged():  # TC-002
    text = usage(usage_data(), "en")
    assert small_of_first_card(text) == "no SU factor for partition ngs8g"
    no_cjk(text)


def test_338_reason_fallbacks():  # TC-004 .. TC-007
    for lang, fixed in (("zh", "無法計算"), ("en", "Not available")):
        assert small_of_first_card(usage(usage_data(reasons=()), lang)) == fixed
        assert small_of_first_card(usage(usage_data(reasons=["task X: "]), lang)) == fixed
    two = "task X: 分區 a 沒有 SU 係數 (no SU factor for partition a); 缺 cpus (no cpus)"
    assert "缺 cpus" not in usage(usage_data(reasons=[two])) and "分區 a" in usage(usage_data(reasons=[two]))
    assert "no cpus" not in usage(usage_data(reasons=[two]), "en")
    en = usage(usage_data(reasons=["task X: 壞 (原因 不明)"]), "en")
    assert small_of_first_card(en) == "Not available"
    no_cjk(en)


def test_338_past_month_titles_show_month():  # TC-008, TC-009
    zh = usage(usage_data("2026-10"))
    assert "國網 SU（2026-10）" in zh and "雲端已用（2026-10）" in zh and "（本月）" not in zh
    en = usage(usage_data("2026-10"), "en")
    assert "(2026-10)" in en and "this month" not in en
    no_cjk(en)


def test_338_current_month_titles_unchanged():  # TC-010
    zh = usage(usage_data("2026-11"))
    assert "國網 SU（本月）" in zh and "雲端已用（本月）" in zh
    assert "this month" in usage(usage_data("2026-11"), "en")


def test_338_empty_month_sentence():  # TC-012, TC-013
    assert "— 2099-01 尚無分析" in plain(middle(usage(usage_data("2099-01"))))
    en = usage(usage_data("2099-01"), "en")
    assert "No analyses in 2099-01" in en
    no_cjk(en)
    assert "— 本月尚無分析" in plain(middle(usage(usage_data("2026-11"))))
    assert "No analyses this month" in usage(usage_data("2026-11"), "en")


def test_338_action_only_this_month():  # TC-014
    assert "待處理：本月雲端額度已用盡" in usage(usage_data("2026-11", left=0.0))
    assert "待處理：本月雲端額度已用盡" not in usage(usage_data("2026-10", left=0.0))


# ---- #341
def run_dict(**over):
    r = {"id": "abc123", "name": "ann-run", "status": "running", "started_at": "2026-11-05T01:00:00Z", "tasks": {"succeeded": 1}}
    r.update(over)
    return r


def head_of(text):
    return re.search(r'<div class="head">(.*?)</div><nav class="views">', text, re.S).group(1)


def meta_of(text):
    return plain(re.search(r'<p class="meta">(.*?)</p>', head_of(text), re.S).group(1))


def board(selected, lang="zh", tab=None):
    return web_board.render_board("ann", "tok", [selected], selected, lang=lang, tab_param=tab, now=NOW)


FULL = dict(pipeline="nf-core/rnaseq", revision="3.14.0", compute_env="site-a", last_message_at="2026-11-05T03:30:00Z", ended_at="2026-11-05T05:00:00Z")


def test_341_head_has_meta_line():  # TC-018, TC-019, TC-021
    for lang in ("zh", "en"):
        text = board(run_dict(**FULL), lang)
        line = meta_of(text)
        for v in ("nf-core/rnaseq", "3.14.0", "site-a", web_board._time("2026-11-05T01:00:00Z"), web_board._time("2026-11-05T03:30:00Z")):
            assert v in line, (lang, v)
        if lang == "en":
            no_cjk(text)
    assert web_board._time("2026-11-05T05:00:00Z") in meta_of(board(run_dict(**dict(FULL, last_message_at=None))))
    only = meta_of(board(run_dict(**dict(FULL, last_message_at=None, ended_at=None))))
    assert only.count(web_board._time("2026-11-05T01:00:00Z")) == 2


def test_341_meta_line_missing_values_dash():  # TC-022
    line = meta_of(board(run_dict()))
    assert line.count("—") >= 3 and web_board._time("2026-11-05T01:00:00Z") in line


def test_341_info_tab_has_new_rows():  # TC-023, TC-024
    for lang, labels in (("zh", ("管線", "版本", "運算環境", "最後更新")), ("en", ("Pipeline", "Revision", "Compute environment", "Last update"))):
        text = board(run_dict(**FULL), lang, tab="info")
        dts = re.findall(r"<dt>(.*?)</dt>", re.search(r'<dl class="fields">(.*?)</dl>', text, re.S).group(1))
        for lab in labels:
            assert lab in dts, (lang, lab, dts)
        for old in ("開始", "結束") if lang == "zh" else ("Started", "Ended"):
            assert old in dts
        if lang == "en":
            no_cjk(text)


def test_341_read_run_adds_pipeline_revision(w, monkeypatch):  # TC-025 .. TC-028
    from abf_platform import actions
    ann, c, ids = std(w)
    url = "/?run=%s" % ids["running"]
    monkeypatch.setattr(actions, "launch_prefill", lambda *a, **k: {"found": True, "kept": True, "pipeline": "nf-core/rnaseq", "revision": "3.14.0", "ce_name": "ce-x"})
    line = meta_of(c.get(url).text)
    assert "nf-core/rnaseq" in line and "3.14.0" in line and "ce-x" in line
    for answer in ({"found": False, "kept": False}, {"found": True, "kept": False, "launched_at": "2026-11-01T00:00:00Z"}):
        monkeypatch.setattr(actions, "launch_prefill", lambda *a, answer=answer, **k: answer)
        line = meta_of(c.get(url).text)
        assert "nf-core" not in line and "—" in line


# ---- #342 / #343
def media(css, query):
    start = "@media (%s){" % query
    i = css.index(start) + len(start)
    depth, j = 1, i
    while depth:
        depth += {"{": 1, "}": -1}.get(css[j], 0)
        j += 1
    return css[i:j - 1]


def test_342_right_column_360_300():  # TC-031 .. TC-033
    css = web_board.STYLE
    assert "272px minmax(0,1fr) 360px" in css and "232px minmax(0,1fr) 300px" in css
    assert not re.search(r"grid-template-columns:[^;}]*(320px|288px)", css)


def test_343_mobile_min_target_rules():  # TC-038, TC-039, TC-040
    block = media(web_board.STYLE, "max-width:900px")
    rule = re.search(r"([^{}]*)\{[^}]*min-height:24px[^}]*\}", block)
    assert rule and "min-width:24px" in rule.group(0)
    for sel in (".pager a", ".rtabs a", ".otbl a", ".ostat a", ".switch a", ".views a", ".tbl a", ".rail a"):
        assert sel in rule.group(1), sel
    assert "display:inline-flex" in rule.group(0) and "align-items:center" in rule.group(0)
    assert "min-height:24px" not in web_board.STYLE.replace(block, "")


def test_343_otbl_filename_not_anywhere():  # TC-042 .. TC-045
    css = web_board.STYLE
    code = re.search(r"\.otbl code\{([^}]*)\}", css).group(1)
    assert "anywhere" not in code and "overflow-wrap:normal" in code and "word-break:keep-all" in code
    otbl = re.search(r"\.otbl\{([^}]*)\}", media(css, "max-width:900px")).group(1)
    assert "overflow-x:auto" in otbl and "table-layout:auto" in otbl
    assert "overflow-wrap:anywhere" in re.search(r"\.tbl th,\.tbl td\{([^}]*)\}", css).group(1)


def test_style_colours_are_not_new():  # TC-053
    base = subprocess.run(["git", "show", "86363c0b:platform/abf_platform/web_board.py"], capture_output=True, text=True, encoding="utf-8").stdout
    hexes = lambda s: set(re.findall(r"#[0-9a-fA-F]{3,8}\b", s))
    assert hexes(web_board.STYLE) <= hexes(base)


def test_style_no_inline_no_script(w):  # TC-050
    ann, c, ids = std(w)
    for url in ("/?run=%s" % ids["done"], "/?run=%s&stage=running&tab=info&lang=en" % ids["running"], "/usage?month=2026-10"):
        text = c.get(url).text
        assert "style=" not in text and "<script" not in text, url
