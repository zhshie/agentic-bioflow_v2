# Nothing existing: the downstream stage of a succeeded run (DESIGN.md screen 9, ADR 0010 Decided 3 and Question 3 option B): how to start a Studio, and a new-tab link.
"""The downstream stage, as a pure function from the answers of the actions to a string.

No database, no file and no network is touched here. The page only draws what was asked for in the query string of this one request: the platform
does not store the address of a Studio, does not start anything and does not run any script. The one link made here is the address the person gave
(a `target="_blank"` link, never a frame), and only when `studio_url` accepts it. Every word is in the two tables below (zh and en, same keys).
"""
import html
import re
import urllib.parse

MAX_LENGTH = 300
SECRET_KEYS = ("token", "password", "key", "secret")

STRINGS = {
    "zh": {
        "intro": "下游分析於使用者自己的電腦或雲端環境進行，平台不代為執行，也不在 NCHC 登入節點啟動。",
        "folder": "結果資料夾", "unread": "尚未讀取輸出", "see_outputs": "查看輸出",
        "copy_note": "請先將此資料夾複製到自己的電腦或雲端環境，再於該處啟動 Studio。",
        "jupyter": "Jupyter", "rstudio": "RStudio",
        "placeholder_note": "指令中的「<本機結果資料夾>」請替換為複製後的資料夾路徑。",
        "paste": "貼上自己 Studio 的網址", "open": "開啟連結",
        "local_note": "http://localhost 開頭的網址，僅在瀏覽器與 Studio 位於同一台電腦時才能連線。",
        "link": "在新分頁開啟 Studio",
        "own_url": "此網址由使用者自行提供，平台不儲存、不檢查其內容。",
        "bad_scheme": "請輸入以 http:// 或 https:// 開頭的網址。",
        "bad_host": "網址缺少主機名稱，請輸入完整的網址，例如 http://localhost:8787/。",
        "bad_long": "網址長度已逾 300 個字元，請改貼較短的網址。",
        "bad_space": "網址不得含空白或換行，請重新複製網址。",
        "bad_secret": "網址不得含帳號、密碼或 token；請改貼不含這些內容的位址。",
    },
    "en": {
        "intro": "Downstream analysis is done on your own computer or cloud environment; the platform does not run it for you and does not start it on the NCHC login node.",
        "folder": "Results folder", "unread": "Outputs not read yet", "see_outputs": "View outputs",
        "copy_note": "Copy this folder to your own computer or cloud environment first, then start the Studio there.",
        "jupyter": "Jupyter", "rstudio": "RStudio",
        "placeholder_note": "In the commands, replace <local results folder> with the path of the copied folder.",
        "paste": "Paste the address of your own Studio", "open": "Open link",
        "local_note": "An address that starts with http://localhost works only when the browser and the Studio are on the same computer.",
        "link": "Open Studio in a new tab",
        "own_url": "This address was given by you; the platform does not store it and does not check its content.",
        "bad_scheme": "Enter an address that starts with http:// or https://.",
        "bad_host": "The address has no host name; enter the full address, for example http://localhost:8787/.",
        "bad_long": "The address is longer than 300 characters; paste a shorter one.",
        "bad_space": "The address must not contain spaces or line breaks; copy it again.",
        "bad_secret": "The address must not contain a user name, password or token; paste an address without them.",
    },
}

_SECRET_QUERY = re.compile(r"(?:^|[?&;#])(?:%s)=" % "|".join(SECRET_KEYS), re.I)


def _e(text):
    return html.escape(str(text), quote=True)


def studio_url(raw):
    """(accepted address, None), (None, None) for an empty value, or (None, the key of the reason in STRINGS). Pure: trims, then checks length,
    blanks, scheme, host and secrets."""
    if not isinstance(raw, str):
        return None, None
    text = raw.strip()
    if not text:
        return None, None
    if len(text) > MAX_LENGTH:
        return None, "bad_long"
    if re.search(r"[\s\x00-\x1f\x7f]", text):
        return None, "bad_space"
    if not re.match(r"https?://", text, re.I):
        return None, "bad_scheme"
    try:
        parts = urllib.parse.urlsplit(text)
        host = parts.hostname
    except ValueError:
        return None, "bad_host"
    if not host:
        return None, "bad_host"
    if "@" in parts.netloc or _SECRET_QUERY.search("?" + parts.query + "#" + parts.fragment):
        return None, "bad_secret"
    return text, None


def _folder(t, lang, run, outputs, board):
    out = outputs or {}
    if out.get("found") is not False and out.get("state") == "ready" and out.get("path"):
        return '<p><span class="muted">%s</span> <code>%s</code></p><p class="muted">%s</p>' % (_e(t["folder"]), _e(out["path"]), _e(t["copy_note"]))
    link = '<a href="%s">%s</a>' % (board._url(lang, run["id"], "results", tab="outputs"), _e(t["see_outputs"]))
    return '<p><span class="muted">%s</span> <span class="muted">— %s</span> %s</p><p class="muted">%s</p>' % (_e(t["folder"]), _e(t["unread"]), link, _e(t["copy_note"]))


def _commands(t, lang):
    folder = "<local results folder>" if lang == "en" else "<本機結果資料夾>"
    jup = 'jupyter lab --notebook-dir "%s"' % folder
    rs = 'docker run --rm -p 127.0.0.1:8787:8787 -e DISABLE_AUTH=true -v "%s":/home/rstudio/results rocker/rstudio' % folder
    return ('<p>%s</p><pre class="reason">%s</pre><p>%s</p><pre class="reason">%s</pre><p class="muted">%s</p>'
            % (_e(t["jupyter"]), _e(jup), _e(t["rstudio"]), _e(rs), _e(t["placeholder_note"])))


def _form(t, lang, run):
    hidden = '<input type="hidden" name="run" value="%s"><input type="hidden" name="stage" value="downstream">' % _e(run["id"])
    if lang == "en":
        hidden += '<input type="hidden" name="lang" value="en">'
    return ('<form method="get" action="/">%s<label for="studio">%s</label> <input type="url" id="studio" name="studio" value="">'
            ' <button type="submit">%s</button></form><p class="muted">%s</p>'
            % (hidden, _e(t["paste"]), _e(t["open"]), _e(t["local_note"])))


def _answer(t, studio):
    ok, why = studio_url(studio)
    if why:
        return '<p class="bad" role="alert"><span>✗</span> %s</p>' % _e(t[why])
    if not ok:
        return ""
    return ('<p><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></p><p><code>%s</code></p><p class="muted">%s</p>'
            % (_e(ok), _e(t["link"]), _e(ok), _e(t["own_url"])))


def render_downstream(lang, run, outputs, studio, title):
    """The card of the downstream stage of a succeeded run. `outputs` is the answer of `run_outputs(enqueue=False)` (or None), `studio` the raw
    `studio` query value (or None), `title` the heading the board uses for this stage."""
    from . import web_board      # imported here: web_board imports this module, and only the link helper is wanted from it
    lang = "en" if lang == "en" else "zh"
    t = STRINGS[lang]
    inner = '<p>%s</p>%s%s%s%s' % (_e(t["intro"]), _folder(t, lang, run, outputs, web_board), _commands(t, lang), _form(t, lang, run), _answer(t, studio))
    return '<section class="card"><h2>%s</h2>%s</section>' % (_e(title), inner)
