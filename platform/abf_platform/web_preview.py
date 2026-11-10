# Nothing existing: showing a result file inside the site (PNG, SVG through img, two named HTML reports in a sandboxed iframe); the download route only sends attachments.
"""web-result-viewer: what a result file may be shown as inside the site. The decision (`kind_of`), the headers of the three routes that show a file
(/run/preview the page, /run/image the picture; step B adds /run/report) and the pages themselves. Nothing here reads a file or the database: the
routes in web.py hand over the answer of `actions.run_file`, the same read the download route uses.

The only things shown: a PNG or SVG through <img> (never inlined), and, in step B, two HTML reports by name inside a sandboxed iframe. The
download route stays the way to get any file."""
import re

from . import web_board

REPORT_NAMES = ("multiqc_report.html", "summary_report.html")      # the reports the pipelines write; every other .html is a download only
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_SVG_START = re.compile(rb"<svg[\s>/]", re.I)
_SVG_WS = frozenset(b" \t\n\r\f\v")


def _doctype_end(data, k):
    """Index just past the `>` that closes a <!DOCTYPE ...> whose body starts at `k`, or -1. A `>` inside quotes, inside the `[ ... ]` internal subset
    or inside a comment of that subset does not close it. One forward pass, so linear in len(data)."""
    n, quote, subset = len(data), None, False
    while k < n:
        c = data[k:k + 1]
        if quote:
            if c == quote:
                quote = None
        elif subset and data.startswith(b"<!--", k):
            j = data.find(b"-->", k + 4)
            if j < 0:
                return -1
            k = j + 2
        elif c in (b'"', b"'"):
            quote = c
        elif c == b"[":
            subset = True
        elif c == b"]":
            subset = False
        elif c == b">" and not subset:
            return k + 1
        k += 1
    return -1


def _svg_head(data):
    """True when `data` is (optional BOM, whitespace, <?xml?>, comments, <!DOCTYPE>) then `<svg`. A single left-to-right scan: each step moves forward
    to the first closing mark, so the time is linear in len(data) whatever the bytes are (a backtracking regex took exponential time on stacked comments)."""
    i, n = 0, len(data)
    while i < n:
        if data[i] in _SVG_WS:
            i += 1
        elif data.startswith(b"\xef\xbb\xbf", i):
            i += 3
        elif data[i:i + 5].lower() == b"<?xml":
            j = data.find(b"?>", i + 5)
            if j < 0:
                return False
            i = j + 2
        elif data.startswith(b"<!--", i):
            j = data.find(b"-->", i + 4)
            if j < 0:
                return False
            i = j + 3
        elif data[i:i + 9].lower() == b"<!doctype":
            j = _doctype_end(data, i + 9)
            if j < 0:
                return False
            i = j
        else:
            break
    return _SVG_START.match(data, i) is not None

STRINGS = {
    "zh": {"p_title": "預覽結果檔", "p_none": "此檔類型不提供預覽。", "p_download": "下載", "p_preview": "預覽", "p_back": "回到輸出分頁",
           "p_note": "報告在隔離框內顯示，其中的程式不能讀取本站資料。報告內的連結可能無法使用，可下載後再開啟。"},
    "en": {"p_title": "Preview a result file", "p_none": "This file type has no preview.", "p_download": "Download", "p_preview": "Preview",
           "p_back": "Back to Outputs",
           "p_note": "The report is shown in an isolated frame; its code cannot read the data of this site. Links inside the report may not work; download it to open it."},
}


def kind_of(path, data=None):
    """"png", "svg", "html" or None. Given only the path: the candidate by name (a listing never reads a file). Given the bytes too: the candidate
    that the bytes bear out (a PNG starts with its signature, an SVG has an <svg> element after the declaration), else None."""
    name = str(path or "").rsplit("/", 1)[-1]
    low = name.lower()
    if low.endswith(".png"):
        kind = "png"
    elif low.endswith(".svg"):
        kind = "svg"
    elif low in REPORT_NAMES:
        kind = "html"
    else:
        return None
    if data is None:
        return kind
    if kind == "png":
        return kind if data.startswith(PNG_MAGIC) else None
    if kind == "svg":
        return kind if _svg_head(data[:65536]) else None
    return kind


def preview_link(lang, run_id, path):
    """The `Preview` link of a listing, or "" for a file that has no preview by name."""
    if kind_of(path) is None:
        return ""
    t = STRINGS[web_board.pick_lang(lang)]
    return '<a href="%s">%s</a>' % (web_board._url(lang, run_id, path="/run/preview", sub=path), web_board.esc(t["p_preview"]))


def page_headers(base, kind=None):
    """Headers of the preview page: the base ones, and only for a picture that is ready `img-src 'self'` (the same form as /launch)."""
    headers = dict(base)
    if kind in ("png", "svg"):
        headers["Content-Security-Policy"] = base["Content-Security-Policy"].replace("default-src 'none'; ", "default-src 'none'; img-src 'self'; ", 1)
    if kind == "html":
        headers["Content-Security-Policy"] = base["Content-Security-Policy"] + "; frame-src 'self'"
    return headers


def report_headers(base):
    """Headers of the report itself, for the iframe of the preview page: the report runs its scripts but `sandbox allow-scripts` (no allow-same-origin)
    makes it an opaque origin, and the policy lets it load nothing from the network nor send a form. Only this route may be framed (by the site)."""
    return dict(base, **{"Content-Type": "text/html; charset=utf-8", "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
                         "Referrer-Policy": "no-referrer", "X-Frame-Options": "SAMEORIGIN",
                         "Content-Security-Policy": "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' blob:; "
                                                    "style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; "
                                                    "frame-src 'none'; frame-ancestors 'self'; base-uri 'none'; worker-src blob:"})


def image_headers(base, kind):
    """Headers of the picture itself: the type comes from our decision, never from the file; opened on its own it can run nothing (`sandbox`)."""
    return dict(base, **{"Content-Type": "image/png" if kind == "png" else "image/svg+xml", "X-Content-Type-Options": "nosniff",
                         "Cache-Control": "private, no-store", "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; sandbox"})


def _links(lang, run_id, path, t):
    esc = web_board.esc
    return '<p><a href="%s">%s</a> <a href="%s">%s</a></p>' % (
        web_board._url(lang, run_id, path="/run/file", sub=path), esc(t["p_download"]),
        web_board._url(lang, run_id, "results", tab="outputs"), esc(t["p_back"]))


def render_none(run_id, path, lang="zh"):
    """The page of a file that has no preview: one line, the way to download, the way back."""
    lang = web_board.pick_lang(lang)
    t = STRINGS[lang]
    body = '<p class="ostat state-failed"><span class="sym">✕</span> %s</p>%s' % (web_board.esc(t["p_none"]), _links(lang, run_id, path, t))
    return web_board.document(t["p_title"], body, lang=lang)


def render_image(run_id, path, name, lang="zh"):
    """The page of a picture: the file name, the picture through <img> (its address is the picture route), the way to download, the way back."""
    lang = web_board.pick_lang(lang)
    t = STRINGS[lang]
    src = web_board._url(lang, run_id, path="/run/image", sub=path)
    src = src.replace("&amp;lang=en", "")        # the picture route does not speak a language
    body = '<h1>%s</h1><p><img src="%s" alt="%s" width="100%%"></p>%s' % (web_board.esc(name), src, web_board.esc(name), _links(lang, run_id, path, t))
    return web_board.document(t["p_title"], body, lang=lang)


def render_report(run_id, path, name, lang="zh"):
    """The page of a white-listed report: the file name, one line on what the frame is, the report in a sandboxed iframe (its address is the report
    route; the sandbox is `allow-scripts` alone), the way to download, the way back. The size is in attributes: the stylesheet is not changed."""
    lang = web_board.pick_lang(lang)
    t = STRINGS[lang]
    src = web_board._url(lang, run_id, path="/run/report", sub=path).replace("&amp;lang=en", "")
    body = ('<h1>%s</h1><p class="muted">%s</p><p><iframe sandbox="allow-scripts" src="%s" title="%s" referrerpolicy="no-referrer" width="100%%" height="800"></iframe></p>%s'
            % (web_board.esc(name), web_board.esc(t["p_note"]), src, web_board.esc(name), _links(lang, run_id, path, t)))
    return web_board.document(t["p_title"], body, lang=lang)
