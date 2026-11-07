# Nothing existing: tests of web-result-viewer (the preview link in the two listings, the page /run/preview, the picture route /run/image and, in step B, the
# sandboxed report route /run/report); the plan and the cases are specs/web-result-viewer/plan.md and test-case.md. Cases are named in the comments (TC-001 ...).
"""web-result-viewer. Step A: pictures (PNG and SVG only through <img>). Step B (below): the white-listed HTML reports in a sandboxed iframe."""
import hashlib
import re
import urllib.parse

import pytest

from human_harness import World
from test_results_files import INTERNAL, LIMIT, STYLE_SHA256, file_jobs, file_url, ok_result, reply_file
from test_web_finished import read_outputs, section, url as finished_url, world
from test_web_results_outputs import ENTRIES
from test_web_wording_sweep import banned_in

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) + b"\xff\xff\x00\xfe IEND"
SVG_EVIL = b'<?xml version="1.0"?><!-- c --><svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect/></svg>'
HTML = b"<html><body><script>var x = 1;</script>\xff\xfe\x00 binary \x80</body></html>\n"
NOT_AN_IMAGE = b"<html><body>not an image</body></html>"
CJK = re.compile(r"[　-〿㐀-鿿豈-﫿＀-￯]")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def entry(name, size=100, kind="file"):
    return {"name": name, "type": kind, "size": size, "modified": "2026-10-20T08:00:00Z"}


FILES = [entry(n) for n in ("plot.png", "fig.svg", "PLOT.PNG", "multiqc_report.html", "summary_report.html", "fake.png", "fake.svg")]
OTHERS = [entry(n) for n in ("a.txt", "b.tsv", "c.bam", "d.pdf", "e.htm", "f.jpg", "g.gif", "evil.html")]
LISTING = ENTRIES + FILES + OTHERS + [entry("big.png", LIMIT + 1)]


def quoted(path):
    return urllib.parse.quote(path, safe="/")


def purl(rid, path, route="preview", extra=""):
    return "/run/%s?run=%s&path=%s%s" % (route, rid, quoted(path), extra)


def link(rid, path, route="preview"):
    return 'href="/run/%s?run=%s&amp;path=%s"' % (route, rid, quoted(path))


def answered(w, c, rid, path, data=None, error=None):
    """Queue the read of `path` (through the download route), answer it as the agent would, and leave it in the cache of the action."""
    assert c.get(file_url(rid, path)).status_code == 200
    if error is not None:
        reply_file(w, "error", dict(ok=False, **error))
    else:
        reply_file(w, "done", ok_result(data, name=path.rsplit("/", 1)[-1]))


def ready(w, c, rid, path, data, route="preview", extra=""):
    answered(w, c, rid, path, data)
    return c.get(purl(rid, path, route, extra))


def rows(text, name):
    return [r for r in re.findall(r"<(?:li|tr)\b.*?</(?:li|tr)>", text, re.S) if re.search(r">%s<" % re.escape(name), r)]


def pages(w, c, rid):
    read_outputs(w, rid, c, LISTING)
    return {"finished": c.get(finished_url(rid)).text, "outputs": c.get("/?run=%s&stage=results&tab=outputs" % rid).text}


def csp_of(r):
    return r.headers.get("content-security-policy", "")


def base_csp(c):
    return csp_of(c.get("/settings"))


def visible(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S))).strip()


# ---- US1: the listings ------------------------------------------------------------------------------------------------

def test_tc001_002_listings_keep_their_download_links(w):
    # TC-001, TC-002
    ann, c, rid = world(w)
    read_outputs(w, rid, c, LISTING)
    fin = c.get(finished_url(rid)).text
    sec = section(fin, "交付包")
    assert re.search(r'>zeta\.txt</a> <span class="muted">2\.0 KB</span>', sec)
    assert 'href="/run/file?run=%s&amp;path=multiqc/multiqc_report.html">MultiQC 報告</a>' % rid in sec
    out = c.get("/?run=%s&stage=results&tab=outputs" % rid).text
    assert 'href="/run/file?run=%s&amp;path=zeta.txt"' % rid in out


@pytest.mark.parametrize("names", [["plot.png"], ["fig.svg"], ["multiqc_report.html", "summary_report.html", "PLOT.PNG"]])
def test_tc003_004_005_006_preview_link_follows_the_download_link(w, names):
    # TC-003, TC-004, TC-005, TC-006 (va11)
    ann, c, rid = world(w)
    got = pages(w, c, rid)
    for kind, text in got.items():
        for name in names:
            row = rows(text, name)
            assert row, (kind, name)
            dl = 'href="/run/file?run=%s&amp;path=%s"' % (rid, quoted(name))
            assert dl in row[0] and link(rid, name) in row[0], (kind, name)
            assert row[0].index(dl) < row[0].index(link(rid, name)), (kind, name)
            assert ">預覽</a>" in row[0]


def test_tc006b_multiqc_link_of_the_finished_page_has_a_preview_link(w):
    # TC-006
    ann, c, rid = world(w)
    sec = section(pages(w, c, rid)["finished"], "交付包")
    assert 'path=multiqc/multiqc_report.html">MultiQC 報告</a>' in sec and link(rid, "multiqc/multiqc_report.html") in sec


def test_tc007_listings_gain_only_plain_links(w):
    # TC-007
    ann, c, rid = world(w)
    before = pages(w, c, rid)
    for kind, text in before.items():
        for tag in ("<img", "<iframe", "<script", "<form", "<button", "style="):
            assert tag not in text.replace('<form method="post" action="/logout">', ""), (kind, tag)
        assert text.count("<style>") == 1
    sec = section(before["finished"], "交付包")
    assert "<form" not in sec and "<button" not in sec and 'href="/download' not in sec


def test_tc008_009_010_no_link_for_other_types_but_the_fakes_get_one(w):
    # TC-008, TC-009, TC-010
    ann, c, rid = world(w)
    for kind, text in pages(w, c, rid).items():
        for name in [e["name"] for e in OTHERS]:
            row = rows(text, name)
            assert row and "/run/preview" not in row[0], (kind, name)
        for name in ("fake.png", "fake.svg"):
            assert link(rid, name) in rows(text, name)[0], (kind, name)


def test_tc011_too_large_has_no_preview_link(w):
    # TC-011
    ann, c, rid = world(w)
    for kind, text in pages(w, c, rid).items():
        assert "/run/preview?run=%s&amp;path=big.png" % rid not in text, kind
        assert "big.png" in text and ("25 MB" in text)


def test_tc012_download_route_is_unchanged(w):
    # TC-012, TC-072
    ann, c, rid = world(w)
    r = ready(w, c, rid, "plot.png", PNG, route="file")
    assert r.status_code == 200 and r.content == PNG
    assert r.headers["content-disposition"] == 'attachment; filename="plot.png"'
    assert r.headers["content-type"] == "application/octet-stream"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "private, no-store"
    assert "img-src" not in csp_of(r) and csp_of(r) == base_csp(c)


# ---- US2: pictures ----------------------------------------------------------------------------------------------------

def test_tc013_014_015_036_png_preview_page(w):
    # TC-013, TC-014, TC-015, TC-036
    ann, c, rid = world(w)
    r = ready(w, c, rid, "plot.png", PNG)
    assert r.status_code == 200
    assert '<img src="/run/image?run=%s&amp;path=plot.png"' % rid in r.text and 'alt="plot.png"' in r.text
    csp = csp_of(r)
    for part in ("img-src 'self'", "default-src 'none'", "form-action 'self'", "frame-ancestors 'none'", "base-uri 'none'"):
        assert part in csp, part
    assert "script-src" not in csp and "frame-src" not in csp
    assert r.headers["x-frame-options"] == "DENY"
    assert "<script" not in r.text and "style=" not in r.text and r.text.count("<style>") == 1
    assert 'href="/run/file?run=%s&amp;path=plot.png"' % rid in r.text
    assert 'href="/?run=%s&amp;stage=results&amp;tab=outputs"' % rid in r.text


def test_tc016_017_image_route_headers_and_bytes(w):
    # TC-016, TC-017
    ann, c, rid = world(w)
    r = ready(w, c, rid, "plot.png", PNG, route="image")
    assert r.status_code == 200 and r.content == PNG and PNG.count(b"\xff") > 1
    assert r.headers["content-type"] == "image/png"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "private, no-store"
    assert csp_of(r).startswith("default-src 'none'") and "sandbox" in csp_of(r)
    assert r.headers["x-frame-options"] == "DENY" and "content-disposition" not in r.headers


def test_tc018_019_svg_only_through_img(w):
    # TC-018, TC-019
    ann, c, rid = world(w)
    page = ready(w, c, rid, "fig.svg", SVG_EVIL)
    assert "<img" in page.text and "/run/image?run=%s&amp;path=fig.svg" % rid in page.text
    assert "<svg" not in page.text and "alert(1)" not in page.text
    r = c.get(purl(rid, "fig.svg", "image"))
    assert r.status_code == 200 and r.headers["content-type"] == "image/svg+xml" and r.content == SVG_EVIL
    csp = csp_of(r)
    assert "sandbox" in csp and "default-src 'none'" in csp and "script-src" not in csp
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "private, no-store"


def test_tc020_no_parameter_chooses_the_type(w):
    # TC-020
    ann, c, rid = world(w)
    answered(w, c, rid, "plot.png", PNG)
    for extra in ("&type=text/html", "&content_type=text/html", "&mime=text/html"):
        assert c.get(purl(rid, "plot.png", "image", extra)).headers["content-type"] == "image/png"


def test_tc021_extension_is_not_case_sensitive(w):
    # TC-021
    ann, c, rid = world(w)
    r = ready(w, c, rid, "PLOT.PNG", PNG)
    assert "<img" in r.text and "/run/image?run=%s&amp;path=PLOT.PNG" % rid in r.text


@pytest.mark.parametrize("name,data", [("fake.png", NOT_AN_IMAGE), ("fake.svg", b"just text")])
def test_tc022_023_024_fakes_are_not_previewed(w, name, data):
    # TC-022, TC-023, TC-024
    ann, c, rid = world(w)
    r = ready(w, c, rid, name, data)
    assert r.status_code == 200 and "此檔類型不提供預覽" in r.text
    assert "<img" not in r.text and "<iframe" not in r.text
    assert 'href="/run/file?run=%s&amp;path=%s"' % (rid, name) in r.text and "tab=outputs" in r.text
    img = c.get(purl(rid, name, "image"))
    assert img.status_code == 404 and img.content == b""


def test_tc025_026_other_types_are_not_previewed(w):
    # TC-025, TC-026
    ann, c, rid = world(w)
    for name in [e["name"] for e in OTHERS]:
        answered(w, c, rid, name, b"data \xff data")
        r = c.get(purl(rid, name))
        assert r.status_code == 200 and "此檔類型不提供預覽" in r.text, name
        assert "<img" not in r.text and "<iframe" not in r.text and 'href="/run/file?run=%s&amp;path=%s"' % (rid, name) in r.text and "tab=outputs" in r.text
        for route in ("image", "report"):
            g = c.get(purl(rid, name, route))
            assert g.status_code == 404 and g.content == b"", (name, route)


def test_tc027_028_too_large(w):
    # TC-027, TC-028
    ann, c, rid = world(w)
    answered(w, c, rid, "big.png", error={"error": "too_large", "size": LIMIT + 1})
    r = c.get(purl(rid, "big.png"))
    assert "大於網頁下載上限 25 MB" in visible(r.text) and "<img" not in r.text
    img = c.get(purl(rid, "big.png", "image"))
    assert img.status_code == 404 and img.content == b""


def test_tc029_030_037_waiting(w):
    # TC-029, TC-030, TC-037
    ann, c, rid = world(w)
    r = c.get(purl(rid, "plot.png"))
    assert r.status_code == 200 and "◌" in r.text and "<img" not in r.text
    assert 'http-equiv="refresh" content="15;url=/run/preview?run=%s&amp;path=plot.png"' % rid in r.text
    img = c.get(purl(rid, "plot.png", "image"))
    assert img.status_code == 404 and img.content == b""
    reply_file(w, "done", ok_result(PNG, name="plot.png"))
    assert "<img" in c.get(purl(rid, "plot.png")).text


def test_tc031_032_errors_are_said_in_the_known_words(w):
    # TC-031, TC-032
    ann, c, rid = world(w)
    answered(w, c, rid, "plot.png", error={"error": "site_unreachable", "message": "x"})
    r = c.get(purl(rid, "plot.png"))
    assert "<img" not in r.text and "✕" in r.text and "站台" in visible(r.text) and "路徑" not in visible(r.text)
    ann2, c2, rid2 = world(w, name="ann-two", who="ann2")
    answered(w, c2, rid2, "plot.png", error={"error": "changed", "message": "x"})
    r2 = c2.get(purl(rid2, "plot.png"))
    assert "<img" not in r2.text and 'href="/run/preview?run=%s&amp;path=plot.png&amp;retry=1"' % rid2 in r2.text
    assert "/run/file?" not in r2.text.replace('href="/run/file?run=%s&amp;path=plot.png"' % rid2, "")


def test_tc033_034_035_owner_rule_and_login(w):
    # TC-033, TC-034, TC-035
    ann, c, rid = world(w)
    bob, cb, rid_b = world(w, name="bob-done", who="bob")
    before = len(file_jobs(w))
    r = c.get(purl(rid_b, "plot.png"))
    ref = c.get(file_url(rid_b, "plot.png"))
    assert r.status_code == 404 and r.text == ref.text and rid_b not in r.text
    img = c.get(purl(rid_b, "plot.png", "image"))
    assert img.status_code == 404 and img.content == b""
    assert len(file_jobs(w)) == before
    anon = w.web()
    base = anon.get(file_url(rid, "plot.png"))
    for route in ("preview", "image"):
        g = anon.get(purl(rid, "plot.png", route))
        assert (g.status_code, g.headers.get("location")) == (base.status_code, base.headers.get("location")) and g.content == base.content


def test_tc038_english(w):
    # TC-038
    ann, c, rid = world(w)
    r = ready(w, c, rid, "plot.png", PNG, extra="&lang=en")
    assert '<html lang="en">' in r.text and not CJK.search(r.text) and "lang=en" in r.text
    assert 'href="/run/file?run=%s&amp;path=plot.png&amp;lang=en"' % rid in r.text


def test_tc039_nothing_of_downstream_is_touched():
    # TC-039 is a manual check (docs/TESTING.md); here only that the downstream page module does not know the new routes
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "abf_platform" / "web_downstream.py")
    if src.exists():
        assert "/run/preview" not in src.read_text(encoding="utf-8")


# ---- US4: nothing else is loosened ------------------------------------------------------------------------------------

def test_tc070_071_074_075_other_pages_keep_the_base_headers(w):
    # TC-070, TC-071, TC-074, TC-075, TC-077
    from abf_platform import web_board
    ann, c, rid = world(w)
    got = pages(w, c, rid)
    base = base_csp(c)
    assert hashlib.sha256(web_board.STYLE.encode("utf-8")).hexdigest() == STYLE_SHA256
    for url in ("/", "/settings", "/usage", "/login", "/?run=%s&stage=finished" % rid, "/?run=%s&stage=results&tab=outputs" % rid, file_url(rid, "plot.png")):
        r = c.get(url)
        assert csp_of(r) == base or url == "/login", url
        assert "img-src" not in csp_of(r) and "frame-src" not in csp_of(r), url
        assert r.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in csp_of(r)
    prev = ready(w, c, rid, "plot.png", PNG)
    img = c.get(purl(rid, "plot.png", "image"))
    assert img.headers["x-frame-options"] == "DENY"
    other = [ready(w, c, rid, "fake.png", NOT_AN_IMAGE), c.get(purl(rid, "a.txt"))]
    for r in [prev] + other:
        assert r.headers["x-frame-options"] == "DENY" and r.text.count("<style>") == 1
        assert hashlib.sha256(re.search(r"<style>(.*?)</style>", r.text, re.S).group(1).encode("utf-8")).hexdigest() == STYLE_SHA256
    for r in other:
        assert csp_of(r) == base
    assert got["finished"] and got["outputs"]


def test_tc073_launch_headers_unchanged():
    # TC-073
    from abf_platform import web, web_board
    assert web.LAUNCH_HEADERS["Content-Security-Policy"] == ("default-src 'none'; img-src 'self'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
                                                             % web_board.style_source())


def test_tc080_081_101_routes_are_read_only(w):
    # TC-080, TC-081, TC-101
    ann, c, rid = world(w)
    routes = {r.path: r for r in c.app.routes if getattr(r, "path", "").startswith("/run/")}
    for path in ("/run/preview", "/run/image"):
        assert set(routes[path].methods) == {"GET", "HEAD"}, path
    kinds = {r["kind"] for r in w.sql("SELECT kind FROM jobs")}
    rows_before = [w.sql("SELECT COUNT(*) FROM %s" % t)[0][0] for t in ("confirmations", "launches")]
    ready(w, c, rid, "plot.png", PNG)
    c.get(purl(rid, "plot.png", "image"))
    for path in ("/run/preview", "/run/image"):
        assert c.post(path + "?run=%s&path=plot.png" % rid).status_code == 405
    assert {r["kind"] for r in w.sql("SELECT kind FROM jobs")} <= kinds | {"read_run_file"}
    assert [w.sql("SELECT COUNT(*) FROM %s" % t)[0][0] for t in ("confirmations", "launches")] == rows_before


def test_tc083_no_zip_or_download_all(w):
    # TC-083
    ann, c, rid = world(w)
    sec = section(pages(w, c, rid)["finished"], "交付包")
    assert "全部下載" not in sec and ".zip" not in sec


def test_tc086_087_wording_and_states(w):
    # TC-086, TC-087
    from abf_platform import web_preview
    for lang in ("zh", "en"):
        assert web_preview.STRINGS[lang].keys() == web_preview.STRINGS["zh"].keys()
    assert banned_in(" ".join(web_preview.STRINGS["zh"].values())) == []
    ann, c, rid = world(w)
    states = {"ready": ready(w, c, rid, "plot.png", PNG), "none": c.get(purl(rid, "a.txt")) if answered(w, c, rid, "a.txt", b"x") is None else None,
              "wait": c.get(purl(rid, "fig.svg"))}
    answered(w, c, rid, "big.png", error={"error": "too_large", "size": LIMIT + 1})
    states["big"] = c.get(purl(rid, "big.png"))
    answered(w, c, rid, "PLOT.PNG", error={"error": "site_unreachable", "message": "Traceback x"})
    states["down"] = c.get(purl(rid, "PLOT.PNG"))
    for name, r in states.items():
        assert banned_in(visible(r.text)) == [], name
        assert not INTERNAL.search(r.text), name
        if name != "ready":
            assert re.search(r"[◌✕]", r.text) and len(visible(r.text)) > 10, name
