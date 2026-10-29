"""settings-ce-table-mobile: the compute-environment table becomes one card per row on a phone (markup + one CSS block only)."""
import hashlib
import json
import re

from helpers import PLATFORM_DIR
from test_web_settings import page, rows_of, two_envs, w  # noqa: F401  (w is the fixture)

ZH_HEAD = ["名稱", "平台", "狀態", "站台代理", "已登記管線", "上次使用時間"]
EN_HEAD = ["Name", "Platform", "Status", "Site agent", "Registered pipelines", "Last used"]
MEDIA = "@media (max-width:640px){"


def ce_section(w, lang, setup=True):
    if setup:
        two_envs(w, w.user("ann"))
    r, mid = page(w, lang=lang)
    h2 = "運算環境" if lang == "zh" else "Compute environments"
    sec, rows = rows_of(mid, h2)
    return r.text, sec, [x for x in rows if "<td" in x]


def media_block(css):
    start = css.index(MEDIA)
    depth, i = 0, start + len(MEDIA) - 1
    while True:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[start:i + 1], start, i + 1
        i += 1


def test_ce01_table_has_ce_class(w):
    # TC-001
    _, sec, _ = ce_section(w, "zh")
    assert '<table class="tbl ce">' in sec


def test_ce02_every_cell_labelled_zh(w):
    # TC-002, TC-004, TC-014
    _, sec, body = ce_section(w, "zh")
    assert len(body) == 2
    for row in body:
        assert re.findall(r'<td data-label="([^"]*)">', row) == ZH_HEAD
        assert row.count("<td") == 6
    assert re.findall(r"<th>(.*?)</th>", sec) == ZH_HEAD
    assert "<th " not in sec


def test_ce03_every_cell_labelled_en(w):
    # TC-003, TC-004
    _, sec, body = ce_section(w, "en")
    assert len(body) == 2
    for row in body:
        assert re.findall(r'<td data-label="([^"]*)">', row) == EN_HEAD
        assert row.count("<td") == 6


def test_ce04_mobile_rule_present(w):
    # TC-005
    text, _, _ = ce_section(w, "zh")
    block, _, _ = media_block(text)
    assert ".tbl.ce" in block and "attr(data-label)" in block and "thead{display:none}" in block


def test_ce05_no_base_rule_leak(w):
    # TC-015, TC-029: every .tbl.ce rule sits inside the one 640px block
    text, _, _ = ce_section(w, "zh")
    css = re.search(r"<style>(.*?)</style>", text, re.S).group(1)
    block, s, e = media_block(css)
    outside = css[:s] + css[e:]
    assert ".tbl.ce" not in outside
    assert css.count(MEDIA) == 1


def test_ce06_colours_only_existing_variables(w):
    # TC-012
    text, _, _ = ce_section(w, "zh")
    block, _, _ = media_block(text)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", block)
    for name in re.findall(r"var\((--[a-z-]+)\)", block):
        assert name in ("--raised", "--line", "--muted")


def test_ce07_other_tables_untouched():
    # TC-017: run page, cost page and upload page keep the plain table
    for name in ("web_board.py", "web_cost.py", "web_upload.py"):
        src = (PLATFORM_DIR / "abf_platform" / name).read_text(encoding="utf-8")
        assert "tbl ce" not in src and "data-label" not in src, name


def test_ce08_no_new_strings():
    # TC-019: hashes taken from the base commit's STRINGS
    from abf_platform import web_board, web_settings
    got = [hashlib.sha256(json.dumps(m.STRINGS, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for m in (web_settings, web_board)]
    assert got == ["82228e36c502def9667ae1c87a618f96b4b53baa811f2bfa4338621cb081094b",
                   "a339098eba9596dcfa00837b8e73be10117df7171e05aa878f35120bbaf8b7a6"]


def test_ce09_no_inline_style(w):
    # TC-032
    for lang in ("zh", "en"):
        _, sec, _ = ce_section(w, lang, setup=(lang == "zh"))
        table = re.search(r"<table.*?</table>", sec, re.S).group(0)
        assert "style=" not in table
