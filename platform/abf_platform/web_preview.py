"""web-result-viewer: what a result file may be shown as inside the site. The decision (`kind_of`), the headers of the three routes that show a file
(/run/preview the page, /run/image the picture; step B adds /run/report) and the pages themselves. Nothing here reads a file or the database: the
routes in web.py hand over the answer of `actions.run_file`, the same read the download route uses.

The only things shown: a PNG or SVG through <img> (never inlined), and, in step B, two HTML reports by name inside a sandboxed iframe. The
download route stays the way to get any file."""
import re

from . import web_board

REPORT_NAMES = ("multiqc_report.html", "summary_report.html")      # the reports the pipelines write; every other .html is a download only
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_SVG_HEAD = re.compile(rb"\A(?:\s|\xef\xbb\xbf|<\?xml.*?\?>|<!--.*?-->|<!DOCTYPE[^>]*>)*<svg[\s>/]", re.S | re.I)

STRINGS = {
    "zh": {"p_title": "預覽結果檔", "p_none": "此檔類型不提供預覽。", "p_download": "下載", "p_preview": "預覽", "p_back": "回到輸出分頁"},
    "en": {"p_title": "Preview a result file", "p_none": "This file type has no preview.", "p_download": "Download", "p_preview": "Preview",
           "p_back": "Back to Outputs"},
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
        return kind if _SVG_HEAD.match(data[:65536]) else None
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
    return headers


def image_headers(base, kind):
    """Headers of the picture itself: the type comes from our decision, never from the file; opened on its own it can run nothing (`sandbox`)."""
    return dict(base, **{"Content-Type": "image/png" if kind == "png" else "image/svg+xml", "X-Content-Type-Options": "nosniff",
                         "Cache-Control": "private, no-store", "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"})


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
