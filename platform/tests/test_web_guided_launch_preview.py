# Nothing existing: tests of 012b-2-guided-launch (step 4 of /launch shows the first rows of the chosen samplesheet, the role of every column, the
# missing required columns and the paired count). Test cases are TC-nnn in specs/012b-2-guided-launch/test-case.md.
import json
import re
from pathlib import Path

import pytest

from abf_launch import build
from test_web_actions import area_sheet, login
from test_web_board import no_cjk
from test_web_guided_launch import SEL, rig, set_env  # noqa: F401  (rig is a fixture)
from test_web_guided_launch_2 import A, fk, good_files, loading_files, error_files, plain_text, step  # noqa: F401  (fk is a fixture)

PAIRED = ("sample", "fastq_1", "fastq_2")


def schema_input(required, optional=()):
    props = {n: {"type": "string"} for n in list(required) + list(optional)}
    return json.dumps({"type": "array", "items": {"type": "object", "properties": props, "required": list(required)}})


def with_schema(fk, required, optional=()):
    fk.files = good_files(schema_input=A()._pf_view("schema_input", {"status": "ok", "text": schema_input(required, optional)}))


def put(rig, user, name, content):
    area_sheet(rig.w, user, name)
    path = Path(rig.w.ip.state_db.parent) / "uploads" / user.name / name
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return path


def csv_text(header, rows):
    return "\n".join([",".join(header)] + [",".join(r) for r in rows]) + "\n"


def ann_of(rig):
    if not hasattr(rig, "_ann"):
        rig._ann = rig.user("ann")
    return rig._ann


def page(rig, content, name="s.csv", lang=""):
    user = ann_of(rig)
    set_env(rig, "lab-a", status="available")
    put(rig, user, name, content)
    c = login(rig, "ann")
    return c, c.get(SEL + "&samplesheet=" + name + lang), user


def four_of(r):
    return step(r.text, 4)


def test_preview_replaces_not_yet_open(rig, fk):
    # TC-001, TC-522
    c, r, _ = page(rig, csv_text(PAIRED, [("a", "x", "y")]))
    four = four_of(r)
    assert r.status_code == 200 and "樣本表預覽" in plain_text(four) and "<table" in four
    assert "預覽與欄位角色" not in r.text


def test_preview_first_five_rows_and_total(rig, fk):
    # TC-002, TC-003, TC-004, TC-005
    rows = [("s%d" % i, "a%d" % i, "b%d" % i) for i in range(8)]
    c, r, _ = page(rig, csv_text(PAIRED, rows))
    four = four_of(r)
    pv = four[four.index("樣本表預覽"):]
    assert len(re.findall(r"<tr><td>s\d", pv)) == 5 and "s5" not in pv
    assert "共 8 列" in plain_text(four) and "僅顯示前 5 列" in plain_text(four)
    _, r, _ = page(rig, csv_text(PAIRED, rows[:5]), name="five.csv")
    assert "共 5 列" in plain_text(four_of(r)) and "僅顯示前 5 列" not in plain_text(four_of(r))
    _, r, _ = page(rig, csv_text(("sample", "fastq_2", "fastq_1", "extra"), [("a", "b", "c", "d")]), name="ord.csv")
    heads = re.findall(r"<th>([^<]*)</th>", four_of(r).split("樣本表預覽")[1].split("</thead>")[0])
    assert heads == ["sample", "fastq_2", "fastq_1", "extra"]


def test_empty_header_only(rig, fk):
    # TC-006
    _, r, _ = page(rig, csv_text(PAIRED, []))
    assert r.status_code == 200 and "共 0 列" in plain_text(four_of(r))


def test_cell_truncation(rig, fk):
    # TC-007 .. TC-010
    _, r, _ = page(rig, csv_text(("c",), [("a" * 60 + "ZZZZZZZZZZ",)]))
    assert "a" * 60 + "…" in r.text and "ZZZZZZZZZZ" not in r.text
    _, r, _ = page(rig, csv_text(("c",), [("b" * 60,)]), name="b.csv")
    assert "b" * 60 in r.text and "b" * 60 + "…" not in r.text
    _, r, _ = page(rig, csv_text(("c",), [("字" * 60,)]), name="z.csv")
    assert "字" * 60 + "</td>" in r.text
    _, r, _ = page(rig, csv_text(("c",), [("字" * 60 + "尾",)]), name="y.csv")
    assert "字" * 60 + "…" in r.text and "尾" not in four_of(r)


def test_cell_content_is_escaped(rig, fk):
    # TC-011, TC-012, TC-013, TC-014, TC-601
    with_schema(fk, ["sample"])
    _, r, _ = page(rig, csv_text(("sample", "<b>x</b>", 'a"b'), [("<script>alert(1)</script>", "1", "2")]))
    four = four_of(r)
    assert "&lt;script&gt;" in four and "<script" not in r.text
    assert "&lt;b&gt;x&lt;/b&gt;" in four and "&quot;" in four and "<b>x" not in four
    roles = four.split("欄位角色")[1]
    assert "&lt;b&gt;" in roles and "&quot;" in roles


def test_column_roles_symbol_and_text(rig, fk):
    # TC-101 .. TC-107, TC-114
    with_schema(fk, PAIRED, ["strandedness"])
    _, r, _ = page(rig, csv_text(("sample", "fastq_1", "strandedness", "extra"), [("a", "b", "c", "d")]))
    roles = four_of(r).split("欄位角色")[1]
    assert "<td>sample</td><td>✓ 必填</td>" in roles and "<td>strandedness</td><td>✓ 選填</td>" in roles
    assert "<td>extra</td><td>— 管線無此欄</td>" in roles
    assert '<td>fastq_2</td><td class="bad">✗ 缺少必填欄</td>' in roles
    assert len(re.findall(r"<tr><td>(?:sample|fastq_1|strandedness|extra)</td>", roles)) == 4
    _, r, _ = page(rig, csv_text(PAIRED, [("a", "b", "c")]), name="full.csv")
    assert "缺少必填欄" not in r.text


def test_maintainer_example_no_chatty_sentence(rig, fk):
    # TC-104, TC-105, TC-521, TC-108
    with_schema(fk, ["sample", "forwardReads", "reverseReads"])
    _, r, _ = page(rig, csv_text(("sample", "forwardReads"), [("a", "b")]))
    four = plain_text(four_of(r))
    assert "✗ 缺少必填欄" in four and "reverseReads" in four
    for bad in ("AI", "改不了", "選用這個樣本", "用過的", "樣本表少了"):
        assert bad not in four
    assert "送出（前往確認頁）" in r.text


def test_no_pipeline_selected_preview_only(rig, fk):
    # TC-109, TC-307
    user = ann_of(rig)
    set_env(rig, "lab-a", status="available")
    put(rig, user, "s.csv", csv_text(PAIRED, [("a", "b", "c")]))
    c = login(rig, "ann")
    r = c.get("/launch?samplesheet=s.csv")
    four = four_of(r)
    assert r.status_code == 200 and "樣本表預覽" in four and "欄位角色" not in four and "已配對" not in four
    r = c.get("/launch")
    assert "選定樣本表後顯示預覽。" in plain_text(four_of(r)) and "預覽與欄位角色" not in r.text and "分析名稱" in r.text


def test_paired_count_when_both_fastq_columns(rig, fk):
    # TC-201 .. TC-206
    with_schema(fk, PAIRED)
    rows = [("a", "1", "2"), ("b", "1", "2"), ("c", "1", "2"), ("d", "1", "")]
    _, r, _ = page(rig, csv_text(PAIRED, rows))
    assert "已配對 3／4" in plain_text(four_of(r))
    rows = [("s%d" % i, "1", "2" if i < 6 else "") for i in range(8)]
    _, r, _ = page(rig, csv_text(PAIRED, rows), name="e.csv")
    assert "已配對 6／8" in plain_text(four_of(r))
    _, r, _ = page(rig, csv_text(PAIRED, [("a", "1", "   ")]), name="w.csv")
    assert "已配對 0／1" in plain_text(four_of(r))
    _, r, _ = page(rig, csv_text(("sample", "fastq_1"), [("a", "1")]), name="n2.csv")
    assert "已配對" not in r.text
    _, r, _ = page(rig, csv_text(("sample", "fastq_2"), [("a", "1")]), name="n1.csv")
    assert "已配對" not in r.text
    with_schema(fk, ["sample", "fastq_1"])
    _, r, _ = page(rig, csv_text(PAIRED, [("a", "1", "2")]), name="p.csv")
    assert "已配對" not in r.text


def test_schema_loading_error_and_missing(rig, fk):
    # TC-110 .. TC-113
    fk.files = loading_files()
    _, r, _ = page(rig, csv_text(PAIRED, [("a", "b", "c")]))
    four = plain_text(four_of(r))
    assert "樣本表預覽" in four and "讀取中" in four and "欄位角色" not in four and "已配對" not in four
    fk.files = error_files()
    _, r, _ = page(rig, csv_text(PAIRED, [("a", "b", "c")]))
    assert r.status_code == 200 and "樣本表預覽" in four_of(r) and "欄位角色" not in four_of(r) and "已配對" not in four_of(r)
    fk.files = good_files(schema_input={"status": "none"})
    _, r, _ = page(rig, csv_text(PAIRED, [("a", "b", "c")]))
    four = four_of(r)
    assert "樣本表預覽" in four and "欄位角色" not in four and "✗" not in four[four.index("樣本表預覽"):] and r.status_code == 200      # the "✗" above the preview is the existing schema_input line


def test_no_sheet_selected_no_preview(rig, fk):
    # TC-301 .. TC-305
    ann_of(rig)
    set_env(rig, "lab-a", status="available")
    c = login(rig, "ann")
    four = plain_text(four_of(c.get(SEL)))
    assert "尚無已上傳的樣本表，請先上傳。" in four and "選定樣本表後顯示預覽。" not in four and "樣本表預覽" not in four
    assert 'href="/upload' in four_of(c.get(SEL))
    put(rig, ann_of(rig), "s.csv", csv_text(PAIRED, [("a", "b", "c")]))
    r = c.get(SEL)
    four = plain_text(four_of(r))
    assert r.status_code == 200 and "選定樣本表後顯示預覽。" in four and "樣本表預覽" not in four and "尚無已上傳" not in four
    r = c.get(SEL + "&samplesheet=../x")
    assert r.status_code == 200 and "選定樣本表後顯示預覽。" in plain_text(four_of(r))


def test_only_own_uploads(rig, fk):
    # TC-306, TC-401 .. TC-404
    ann, bob = ann_of(rig), rig.user("bob")
    set_env(rig, "lab-a", status="available")
    put(rig, bob, "other.csv", "secretcol\nUNIQUESECRET\n")
    put(rig, ann, "mine.csv", csv_text(PAIRED, [("a", "b", "c")]))
    c = login(rig, "ann")
    r = c.get(SEL + "&samplesheet=other.csv")
    assert "UNIQUESECRET" not in r.text and "選定樣本表後顯示預覽。" in plain_text(four_of(r))
    for bad in ("other.csv", "../bob/other.csv", "/etc/passwd", "../x"):
        with pytest.raises(build.Refusal) as e:
            A().preview_samplesheet(rig.w.ip.state_db, ann, bad)
        assert "UNIQUESECRET" not in str(e.value)


def test_unreadable_sheet_says_so_and_send_still_works(rig, fk):
    # TC-308 .. TC-311, TC-313, TC-314, TC-316
    cases = [(b"a,b\n" + b"x," * 700_000 + b"\n", "樣本表大於 1 MiB，無法預覽。"),
             (b"a,b\n1,\x002\n", "樣本表不是 UTF-8 文字檔，無法預覽。"),
             (b"a,b\n\xff\xfe,2\n", "樣本表不是 UTF-8 文字檔，無法預覽。"),
             (b"", "樣本表是空的，沒有標頭列。")]
    for i, (content, said) in enumerate(cases):
        _, r, _ = page(rig, content, name="bad%d.csv" % i)
        four = four_of(r)
        assert r.status_code == 200 and said in plain_text(four), (i, plain_text(four))
        assert '<p class="bad"><span class="csym">✗</span> %s</p>' % said in four
        assert "樣本表預覽" not in four and "欄位角色" not in four
        assert "送出（前往確認頁）" in r.text and "Traceback" not in four


def test_unreadable_when_gone(rig, fk, monkeypatch):
    # TC-312
    set_env(rig, "lab-a", status="available")
    put(rig, ann_of(rig), "gone.csv", "a\n1\n")
    c = login(rig, "ann")

    def refuse(*a, **k):
        raise build.Refusal("x")
    monkeypatch.setattr(A(), "preview_samplesheet", refuse)
    r = c.get(SEL + "&samplesheet=gone.csv")
    assert r.status_code == 200 and "無法讀取所選樣本表，請重新上傳。" in plain_text(four_of(r))


def test_action_shape(rig, fk):
    # TC-016, TC-207, TC-405
    ann = ann_of(rig)
    put(rig, ann, "e.csv", csv_text(("sample", "x"), [("s%d" % i, "1") for i in range(8)]))
    out = A().preview_samplesheet(rig.w.ip.state_db, ann, "e.csv", limit=5)
    assert set(out) == {"columns", "rows", "total", "truncated", "paired"} and len(out["rows"]) == 5 and out["total"] == 8 and out["truncated"] is True
    assert out["paired"] is None
    put(rig, ann, "z.csv", b"")
    with pytest.raises(build.Refusal):
        A().preview_samplesheet(rig.w.ip.state_db, ann, "z.csv")


def test_english(rig, fk):
    # TC-501 .. TC-518
    with_schema(fk, PAIRED, ["strandedness"])
    rows = [("s%d" % i, "1", "2" if i < 3 else "", "x", "y") for i in range(8)]
    _, r, _ = page(rig, csv_text(("sample", "fastq_1", "fastq_2", "strandedness", "extra"), rows), lang="&lang=en")
    four = four_of(r)
    t = plain_text(four)
    for w in ("Samplesheet preview", "8 rows in total", "Showing the first 5 rows", "Paired 3/8"):
        assert w in t, w
    assert "<td>sample</td><td>✓ Required</td>" in four and "✓ Optional" in four and "— Not in this pipeline" in four
    assert "Preview and column roles (not yet available)" not in r.text and no_cjk(four.replace("搜尋全部 nf-core", ""))
    with_schema(fk, ["sample", "reverseReads"])
    _, r, _ = page(rig, csv_text(("sample",), [("a",)]), name="m.csv", lang="&lang=en")
    assert "✗ Missing required column" in r.text and "reverseReads" in r.text and "1 row in total" in r.text
    _, r, _ = page(rig, b"", name="em.csv", lang="&lang=en")
    assert "The samplesheet is empty and has no header row." in r.text and no_cjk(four_of(r))
    r = login(rig, "ann").get(SEL + "&lang=en")
    assert "The preview appears once a samplesheet is selected." in r.text and no_cjk(four_of(r))


def test_strings_both_sides():
    # TC-519
    from abf_platform import web_board
    keys = [k for k in web_board.STRINGS["zh"] if k.startswith("g_pv_")]
    assert keys
    for k in keys:
        assert web_board.STRINGS["zh"][k] and web_board.STRINGS["en"].get(k), k


def test_no_script_no_inline_style_csp_unchanged(rig, fk):
    # TC-601 .. TC-606
    with_schema(fk, PAIRED, ["strandedness"])
    _, r, _ = page(rig, csv_text(PAIRED, [("a", "b", "c")]))
    assert "<script" not in r.text and "style=" not in r.text and r.text.count("<style") == 1
    assert r.headers["content-security-policy"].startswith("default-src 'none'; img-src 'self'; style-src ")
    four = four_of(r)
    pv = four[four.index("樣本表預覽"):]
    assert set(re.findall(r'class="([^"]+)"', pv)) <= {"tbl", "muted", "off", "bad", "csym"}
    assert "<input" not in pv and "<button" not in pv and "<textarea" not in pv      # TC-611
