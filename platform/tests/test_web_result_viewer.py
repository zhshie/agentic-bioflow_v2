# Nothing existing: tests of web-result-viewer (the preview link in the two listings, the page /run/preview, the picture route /run/image and, in step B, the
# sandboxed report route /run/report); the plan and the cases are specs/web-result-viewer/plan.md and test-case.md. Cases are named in the comments (TC-001 ...).
"""web-result-viewer. Step A: pictures (PNG and SVG only through <img>). Step B (below): the white-listed HTML reports in a sandboxed iframe."""
import hashlib
import re
import urllib.parse
from pathlib import Path

import pytest

from human_harness import World
from test_results_files import INTERNAL, LIMIT, STYLE_SHA256, file_jobs, file_url, ok_result, reply_file
from test_web_board import pane
from test_web_finished import read_outputs, section, url as finished_url, world
from test_web_results_outputs import ENTRIES
from test_web_wording_sweep import banned_in

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) + b"\xff\xff\x00\xfe IEND"
SVG_EVIL = b'<?xml version="1.0"?><!-- c --><svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect/></svg>'
HTML = b"<html><body><script>var x = 1;</script>\xff\xfe\x00 binary \x80</body></html>\n"
NOT_AN_IMAGE = b"<html><body>not an image</body></html>"
ROUTES_OTHER = ("image", "report")
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
            assert tag not in pane(text, "middle") and (tag in ("<form", "<button") or tag not in text), (kind, tag)
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
        for route in ROUTES_OTHER:
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
    assert img.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in csp_of(img)          # TC-075 (ADVERSARY fix round)
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
    for path in ("/run/preview", "/run/image", "/run/report"):
        assert set(routes[path].methods) == {"GET", "HEAD"}, path
    kinds = {r["kind"] for r in w.sql("SELECT kind FROM jobs")}
    rows_before = [w.sql("SELECT COUNT(*) FROM %s" % t)[0][0] for t in ("confirmations", "launches")]
    ready(w, c, rid, "plot.png", PNG)
    c.get(purl(rid, "plot.png", "image"))
    for path in ("/run/preview", "/run/image", "/run/report"):
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
        assert banned_in(re.sub(r"/[\w/.-]+", " ", visible(r.text))) == [], name      # the site path in the too-large sentence is the station's, not ours
        assert not INTERNAL.search(r.text), name
        if name != "ready":
            assert re.search(r"[◌✕]", r.text) and len(visible(r.text)) > 10, name


# ---- Step B: the white-listed HTML reports in a sandboxed iframe ---------------------------------------------------------

REPORT_SCRIPT = b"<html><head><style>p{color:red}</style></head><body><p>hi</p><script>var x = 1;</script>\xff\xfe\x00 binary \x80</body></html>\n"


def iframes(text):
    return re.findall(r"<iframe\b[^>]*>", text)


def report_page(w, c, rid, path="multiqc_report.html", extra=""):
    return ready(w, c, rid, path, REPORT_SCRIPT, extra=extra)


def test_tc040_041_042_043_the_iframe(w):
    # TC-040, TC-041, TC-042, TC-043
    ann, c, rid = world(w)
    r = report_page(w, c, rid)
    assert r.status_code == 200
    tags = iframes(r.text)
    assert len(tags) == 1 and r.text.count("<iframe") == 1
    assert re.search(r'\ssandbox="allow-scripts"(\s|>)', tags[0])
    assert "allow-same-origin" not in r.text
    for word in ("allow-forms", "allow-popups", "allow-top-navigation", "allow-modals", "allow-downloads", "by-user-activation"):
        assert word not in r.text, word
    assert 'src="/run/report?run=%s&amp;path=multiqc_report.html"' % rid in tags[0]
    assert 'title="multiqc_report.html"' in tags[0] and 'referrerpolicy="no-referrer"' in tags[0]


def test_tc044_045_page_and_its_headers(w):
    # TC-044, TC-045
    ann, c, rid = world(w)
    r = report_page(w, c, rid)
    tag = iframes(r.text)[0]
    assert re.search(r'\swidth="\d+%?"', tag) and re.search(r'\sheight="\d+"', tag)
    assert "style=" not in r.text and "<script" not in r.text and r.text.count("<style>") == 1
    assert "隔離" in visible(r.text) and "不能讀取本站資料" in visible(r.text)
    assert 'href="/run/file?run=%s&amp;path=multiqc_report.html"' % rid in r.text and "tab=outputs" in r.text
    csp = csp_of(r)
    assert csp == base_csp(c) + "; frame-src 'self'"
    assert "img-src" not in csp and "script-src" not in csp and "unsafe-eval" not in csp
    assert r.headers["x-frame-options"] == "DENY"


def test_tc046_no_other_page_has_frame_src(w):
    # TC-046
    ann, c, rid = world(w)
    answered(w, c, rid, "a.txt", b"x")
    got = [ready(w, c, rid, "plot.png", PNG), c.get(purl(rid, "a.txt")), c.get(purl(rid, "multiqc_report.html")), ready(w, c, rid, "fake.png", NOT_AN_IMAGE)]
    answered(w, c, rid, "multiqc/summary_report.html", error={"error": "too_large", "size": LIMIT + 1})
    got.append(c.get(purl(rid, "multiqc/summary_report.html")))
    answered(w, c, rid, "summary_report.html", error={"error": "site_unreachable", "message": "x"})
    got.append(c.get(purl(rid, "summary_report.html")))
    for r in got:
        assert "frame-src" not in csp_of(r) and "script-src" not in csp_of(r) and "<iframe" not in r.text


def test_tc047_048_049_050_report_route_headers(w):
    # TC-047, TC-048, TC-049, TC-050
    ann, c, rid = world(w)
    r = ready(w, c, rid, "multiqc_report.html", REPORT_SCRIPT, "report")
    assert r.status_code == 200
    h = r.headers
    assert h["content-type"] == "text/html; charset=utf-8" and h["x-content-type-options"] == "nosniff"
    assert h["cache-control"] == "private, no-store" and h["referrer-policy"] == "no-referrer"
    assert h["x-frame-options"] == "SAMEORIGIN"
    csp = csp_of(r)
    assert "frame-ancestors 'self'" in csp and "frame-ancestors 'none'" not in csp
    assert csp.startswith("sandbox allow-scripts;") and "allow-same-origin" not in csp
    for part in ("connect-src 'none'", "form-action 'none'", "default-src 'none'", "frame-src 'none'", "base-uri 'none'"):
        assert part in csp, part


@pytest.mark.parametrize("path", ["summary_report.html", "multiqc/multiqc_report.html"])
def test_tc051_052_other_white_listed_names(w, path):
    # TC-051, TC-052
    ann, c, rid = world(w)
    r = report_page(w, c, rid, path)
    assert len(iframes(r.text)) == 1 and 'sandbox="allow-scripts"' in r.text
    g = c.get(purl(rid, path, "report"))
    assert g.status_code == 200


def test_tc058_report_bytes_are_untouched(w):
    # TC-058
    ann, c, rid = world(w)
    g = ready(w, c, rid, "multiqc_report.html", REPORT_SCRIPT, "report")
    assert g.content == REPORT_SCRIPT


def test_tc059_other_names_get_no_report(w):
    # TC-059
    ann, c, rid = world(w)
    for name in ("evil.html", "multiqc_report.html.txt", "multiqc_report.htm"):
        g = ready(w, c, rid, name, REPORT_SCRIPT, "report")
        assert g.status_code == 404 and g.content == b"", name


def test_tc060_061_062_not_ready_gives_no_report(w):
    # TC-060, TC-061, TC-062
    ann, c, rid = world(w)
    g = c.get(purl(rid, "multiqc_report.html", "report"))
    assert g.status_code == 404 and g.content == b""
    answered(w, c, rid, "summary_report.html", error={"error": "site_unreachable", "message": "x"})
    g = c.get(purl(rid, "summary_report.html", "report"))
    assert g.status_code == 404 and g.content == b""
    answered(w, c, rid, "multiqc/multiqc_report.html", error={"error": "too_large", "size": LIMIT + 1})
    p = c.get(purl(rid, "multiqc/multiqc_report.html"))
    assert "大於網頁下載上限 25 MB" in visible(p.text) and "<iframe" not in p.text
    g = c.get(purl(rid, "multiqc/multiqc_report.html", "report"))
    assert g.status_code == 404 and g.content == b""


def test_tc063_064_owner_and_login(w):
    # TC-063, TC-064
    ann, c, rid = world(w)
    bob, cb, rid_b = world(w, name="bob-done", who="bob")
    before = len(file_jobs(w))
    r = c.get(purl(rid_b, "multiqc_report.html"))
    ref = c.get(file_url(rid_b, "multiqc_report.html"))
    assert r.status_code == 404 and r.text == ref.text and "<iframe" not in r.text
    g = c.get(purl(rid_b, "multiqc_report.html", "report"))
    assert g.status_code == 404 and g.content == b""
    assert len(file_jobs(w)) == before
    anon = w.web()
    base = anon.get(file_url(rid, "multiqc_report.html"))
    a = anon.get(purl(rid, "multiqc_report.html", "report"))
    assert (a.status_code, a.headers.get("location")) == (base.status_code, base.headers.get("location")) and a.content == base.content


def test_tc065_hostile_path_is_escaped(w):
    # TC-065 (the path is only ever in the page as an escaped or percent-coded value, so the quoted word never stands alone)
    ann, c, rid = world(w)
    path = 'a"<b>"allow-same-origin"/multiqc_report.html'
    r = report_page(w, c, rid, path)
    assert r.status_code == 200 and len(iframes(r.text)) == 1 and 'sandbox="allow-scripts"' in iframes(r.text)[0]
    assert '"allow-same-origin"' not in r.text and "<b>" not in r.text and 'sandbox="allow-scripts allow-same-origin' not in r.text


def test_tc066_no_parameter_chooses_the_report_type(w):
    # TC-066
    ann, c, rid = world(w)
    answered(w, c, rid, "multiqc_report.html", REPORT_SCRIPT)
    for extra in ("&type=text/plain", "&mime=image/png", "&content_type=application/zip", "&download=1"):
        g = c.get(purl(rid, "multiqc_report.html", "report", extra))
        assert g.headers["content-type"] == "text/html; charset=utf-8" and g.content == REPORT_SCRIPT, extra


def test_tc067_english_report_page(w):
    # TC-067
    ann, c, rid = world(w)
    r = report_page(w, c, rid, extra="&lang=en")
    assert '<html lang="en">' in r.text and not CJK.search(r.text) and "isolated" in visible(r.text)
    assert len(iframes(r.text)) == 1 and 'sandbox="allow-scripts"' in r.text and "allow-same-origin" not in r.text
    assert 'src="/run/report?run=%s&amp;path=multiqc_report.html"' % rid in r.text


def test_tc068_waiting_report_page(w):
    # TC-068
    ann, c, rid = world(w)
    r = c.get(purl(rid, "multiqc_report.html"))
    assert r.status_code == 200 and "◌" in r.text and "<iframe" not in r.text
    assert 'http-equiv="refresh" content="15;url=/run/preview?run=%s&amp;path=multiqc_report.html"' % rid in r.text


def test_tc074_075_report_headers_are_the_only_exception(w):
    # TC-074, TC-075
    ann, c, rid = world(w)
    page = report_page(w, c, rid)
    rep = c.get(purl(rid, "multiqc_report.html", "report"))
    img = ready(w, c, rid, "plot.png", PNG, "image")
    assert "frame-src 'self'" in csp_of(page) and "frame-src 'none'" in csp_of(rep)
    assert "img-src" not in csp_of(page) and "frame-src" not in csp_of(img)
    assert page.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in csp_of(page)
    assert img.headers["x-frame-options"] == "DENY"
    for url in ("/", "/settings", "/usage", "/?run=%s&stage=finished" % rid, "/?run=%s&stage=results&tab=outputs" % rid):
        r = c.get(url)
        assert "frame-src" not in csp_of(r) and r.headers["x-frame-options"] == "DENY", url


def test_tc100_no_credential_in_the_three_routes(w):
    # TC-100
    ann, c, rid = world(w)
    secrets = [v for v in c.cookies.values() if v]
    assert secrets
    got = [report_page(w, c, rid), c.get(purl(rid, "multiqc_report.html", "report")), ready(w, c, rid, "plot.png", PNG), c.get(purl(rid, "plot.png", "image"))]
    for r in got:
        blob = (r.text if r.headers["content-type"].startswith("text/") else "") + repr(dict(r.headers))
        for s in secrets:
            assert s not in blob
        assert 'name="csrf"' not in blob


def test_tc086_report_wording():
    # TC-086 (step B strings)
    from abf_platform import web_preview
    assert "p_note" in web_preview.STRINGS["zh"] and web_preview.STRINGS["en"].keys() == web_preview.STRINGS["zh"].keys()
    assert banned_in(" ".join(web_preview.STRINGS["zh"].values())) == []


# ---- the report attacks the site (TC-053 .. TC-057) -------------------------------------------------------------------------
# The real-browser half (a Chromium opens the preview page and the report's own script attacks the site) is the manual script
# scripts/dev/check_result_viewer_sandbox.py, with its steps in docs/TESTING.md: CI has no browser and may skip nothing (plan, lead ruling
# 2026-11-11 N+1). What stays here needs no browser and uses the same sample, ATTACK: everything a browser reads to decide that the report
# is an opaque origin with no network and no forms is in the response headers and in the iframe's attributes, and those are asserted below.

ATTACK = b"""<html><body><pre id="out">pending</pre><script>
var r = {};
try { r.cookie = "READ:" + document.cookie; } catch (e) { r.cookie = "ERR:" + e.name; }
try { r.parent = "READ:" + window.parent.document.title; } catch (e) { r.parent = "ERR:" + e.name; }
try { var f = document.createElement("form"); f.action = "/settings"; f.method = "post"; document.body.appendChild(f); f.submit(); r.form = "called"; } catch (e) { r.form = "ERR:" + e.name; }
function one(key, url) { return fetch(url).then(function (x) { return x.text(); }).then(function (t) { r[key] = "GOT:" + t.length; }).catch(function (e) { r[key] = "ERR:" + e.name; }); }
one("settings", "/settings").then(function () { return one("file", "/run/file?run=RID&path=a.txt"); }).then(function () {
  var o = document.getElementById("out"); o.textContent = JSON.stringify(r); o.setAttribute("data-done", "1"); });
</script></body></html>
"""

REPO = Path(__file__).resolve().parents[2]
SANDBOX_CHECK = REPO / "scripts" / "dev" / "check_result_viewer_sandbox.py"
SANDBOX_GRANTS = ("allow-same-origin", "allow-forms", "allow-popups", "allow-top-navigation", "allow-modals", "allow-downloads",
                  "allow-pointer-lock", "allow-presentation", "allow-storage-access", "by-user-activation")


def directives(csp):
    """The policy as {directive name: [its words]}; a name written twice is an error (a browser keeps only the first)."""
    out = {}
    for part in csp.split(";"):
        words = part.split()
        if words:
            assert words[0] not in out, words[0]
            out[words[0]] = words[1:]
    return out


def test_tc053_054_055_056_057_the_attacking_report_is_served_sandboxed(w):
    # TC-053, TC-054, TC-055, TC-056, TC-057: the HTTP and HTML half, with the attack sample of the browser check
    ann, c, rid = world(w)
    attack = ATTACK.replace(b"RID", rid.encode())
    for probe in (b"document.cookie", b"window.parent.document", b"f.submit()", b'"/settings"', b"/run/file?run=" + rid.encode()):
        assert probe in attack, probe                                   # the sample still tries all five things
    answered(w, c, rid, "a.txt", b"secret file text")
    page = ready(w, c, rid, "multiqc_report.html", attack)
    secrets = [v for v in c.cookies.values() if v]
    assert secrets

    # the outer page: one iframe whose only grant is scripts, no script of its own, and not one byte of the report in it
    assert page.status_code == 200
    tags = iframes(page.text)
    assert len(tags) == 1 and page.text.count("<iframe") == 1
    assert re.findall(r'\bsandbox\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]*)', tags[0]) == ['"allow-scripts"']
    assert 'src="/run/report?run=%s&amp;path=multiqc_report.html"' % rid in tags[0] and "srcdoc" not in tags[0]
    for word in SANDBOX_GRANTS:
        assert word not in page.text, word
    assert "<script" not in page.text and "style=" not in page.text
    for leaked in ("document.cookie", "window.parent", "f.submit", "fetch(", 'id="out"'):
        assert leaked not in page.text, leaked
    outer = directives(csp_of(page))
    assert outer["frame-src"] == ["'self'"] and outer["default-src"] == ["'none'"] and outer["frame-ancestors"] == ["'none'"]
    assert "script-src" not in outer and "connect-src" not in outer and "unsafe" not in csp_of(page)
    assert page.headers["x-frame-options"] == "DENY"

    # the report itself: the bytes as they are, under a policy that makes it an opaque origin with no network and no forms
    rep = c.get(purl(rid, "multiqc_report.html", "report"))
    assert rep.status_code == 200 and rep.content == attack
    h = rep.headers
    assert h["content-type"] == "text/html; charset=utf-8" and h["x-content-type-options"] == "nosniff"
    assert h["cache-control"] == "private, no-store" and h["referrer-policy"] == "no-referrer"
    assert "set-cookie" not in h and "access-control-allow-origin" not in h and "content-disposition" not in h
    d = directives(csp_of(rep))
    assert d["sandbox"] == ["allow-scripts"]                            # TC-053, TC-056: no allow-same-origin, so no cookie and no parent
    for word in SANDBOX_GRANTS:
        assert word not in csp_of(rep), word
    assert d["connect-src"] == ["'none'"]                               # TC-054, TC-055: fetch, XHR, WebSocket, beacon
    assert d["form-action"] == ["'none'"]                               # TC-057 (and the sandbox has no allow-forms)
    assert d["default-src"] == ["'none'"] and d["frame-src"] == ["'none'"] and d["base-uri"] == ["'none'"]
    assert d["frame-ancestors"] == ["'self'"] and h["x-frame-options"] == "SAMEORIGIN"
    for name, words in d.items():                                       # no directive lets the report load or send anything over the network
        for word in words:
            assert word in ("allow-scripts", "'none'", "'self'", "'unsafe-inline'", "'unsafe-eval'", "data:", "blob:"), (name, word)
        assert "'self'" not in words or name == "frame-ancestors", name
    for r in (page, rep):                                               # TC-053: the login never travels into the report or its page
        blob = r.text + repr(dict(r.headers))
        for s in secrets:
            assert s not in blob

    # no other route hands the same bytes to a browser as something it would run
    assert c.get(purl(rid, "multiqc_report.html", "image")).status_code == 404
    dl = c.get(file_url(rid, "multiqc_report.html"))
    assert dl.content == attack and dl.headers["content-type"] == "application/octet-stream"
    assert dl.headers["content-disposition"].startswith("attachment") and dl.headers["x-content-type-options"] == "nosniff"
    # under another name the sample is not a report at all
    answered(w, c, rid, "evil.html", attack)
    assert c.get(purl(rid, "evil.html", "report")).status_code == 404 and "<iframe" not in c.get(purl(rid, "evil.html")).text
    # and the three routes do not take a POST, so the form of the sample has nothing to post to
    for route in ("preview", "image", "report"):
        assert c.post(purl(rid, "multiqc_report.html", route)).status_code in (403, 405), route


def test_tc053_057_browser_check_is_a_manual_script_and_nothing_here_is_skipped(tmp_path):
    # TC-053 .. TC-057, the browser half (lead ruling 2026-11-11 N+1 a, c, d): it lives in scripts/dev, uses this file's ATTACK, and without
    # Playwright it says so and ends non-zero - never a pass; this file skips nothing
    import os
    import subprocess
    import sys
    src = SANDBOX_CHECK.read_text(encoding="utf-8")
    compile(src, str(SANDBOX_CHECK), "exec")
    head = "\n".join(src.splitlines()[:20])
    for word in ("Nothing existing:", "Purpose", "How to run", "One-off", "ABF_PLAYWRIGHT_PYTHON"):
        assert word in head, word
    assert re.search(r"^\s*from test_web_result_viewer import .*\bATTACK\b", src, re.M) and "ATTACK =" not in src
    assert "sync_playwright" in src and "chromium" in src
    for tc in ("TC-053", "TC-054", "TC-055", "TC-056", "TC-057"):
        assert tc in src, tc
    for kept in ('res["cookie"]', 'res["settings"]', 'res["file"]', 'res["parent"]', '"/settings"', '"/run/file"', '!= "GET"', "top_has_iframe"):
        assert kept in src, kept                                        # every assertion the pytest version made is still made there
    mask = tmp_path / "mask"
    cwd = tmp_path / "cwd"
    mask.mkdir()
    cwd.mkdir()
    (mask / "sitecustomize.py").write_text('import sys\nsys.modules["playwright"] = None\n')
    env = {k: v for k, v in os.environ.items() if k != "ABF_PLAYWRIGHT_PYTHON"}
    env["PYTHONPATH"] = os.pathsep.join([str(mask)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PATH"] = str(tmp_path / "nopath")                              # and no other python3 to fall back on
    done = subprocess.run([sys.executable, str(SANDBOX_CHECK)], cwd=str(cwd), env=env, capture_output=True, text=True, timeout=120)
    said = done.stdout + done.stderr
    assert done.returncode == 77, said[-2000:]
    assert "playwright" in said and "ABF_PLAYWRIGHT_PYTHON" in said and "UNVERIFIED" in said and "Traceback" not in said
    assert "PASS" not in said and list(cwd.iterdir()) == []
    here = Path(__file__).read_text(encoding="utf-8")
    assert not re.search(r"pytest\.(skip|importorskip|xfail)\(|mark\.(skip|skipif|xfail)\b", here)
    doc = (REPO / "docs" / "TESTING.md").read_text(encoding="utf-8")
    assert "scripts/dev/check_result_viewer_sandbox.py" in doc and "【實機驗】" in doc


def test_svg_head_check_is_linear_time():
    # ADVERSARY (verifier fix round): stacked empty comments made the old backtracking regex take 2^n steps and froze the server's main loop
    import time
    from abf_platform import web_preview
    bad = b"<!---->" * 40 + b"<x>"
    t = time.time()
    assert web_preview.kind_of("plot.svg", bad) is None
    assert web_preview.kind_of("plot.svg", b"<!--a-->" * 5000 + b"<x>") is None
    assert web_preview.kind_of("plot.svg", b"<?xml " * 9000) is None
    assert time.time() - t < 1
    for good in (b"<svg>", b"\xef\xbb\xbf <?xml version='1'?>\n<!-- a --><!DOCTYPE svg PUBLIC 'x'>\n<SVG xmlns='x'/>", b"<!----><!----><svg/>"):
        assert web_preview.kind_of("plot.svg", good) == "svg", good
    assert web_preview.kind_of("plot.svg", b"<svgx>") is None


SVG_DTD = (b'<?xml version="1.0" encoding="utf-8"?>\n<!-- Generator: Adobe Illustrator 16.0.0 -->\n<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
           b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd" [\n<!ENTITY ns_flows "http://ns.adobe.com/Flows/1.0/">\n]>\n<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')


def test_svg_with_internal_dtd_subset_and_image_csp(w):
    # ADVERSARY (verifier fix round): TC-018 for a real SVG with a DOCTYPE internal subset; TC-075 for /run/image
    from abf_platform import web_preview
    assert web_preview.kind_of("fig.svg", SVG_DTD) == "svg"
    assert web_preview.kind_of("fig.svg", b"<!DOCTYPE svg [ <!-- ] > --> <!ENTITY a '>]'> ]>\n<svg/>") == "svg"
    assert web_preview.kind_of("fig.svg", b"<!DOCTYPE svg [ <!ENTITY a 'x'>\n<x/>") is None
    assert web_preview.kind_of("fig.svg", b"<!DOCTYPE svg [ ]>\n<html/>") is None
    ann, c, rid = world(w)
    page = ready(w, c, rid, "fig.svg", SVG_DTD)
    assert "<img" in page.text and "no preview" not in page.text.lower()
    r = c.get(purl(rid, "fig.svg", "image"))
    assert r.status_code == 200 and r.headers["content-type"] == "image/svg+xml"
    assert r.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in csp_of(r)
