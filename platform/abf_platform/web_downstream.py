# Nothing existing: the downstream stage of a succeeded run (DESIGN.md screen 9, ADR 0010 Decided 3 and Question 3 option B, ADR 0011 point 4): RStudio in the page, or how to start a Studio, and a new-tab link.
"""The downstream stage, as a pure function from the answers of the actions to a string.

No database, no file and no network is touched here, and the platform does not store the address of a Studio, does not start, stop, probe or
proxy anything and does not run any script. Two things can be drawn.

* With the deployment setting ABF_STUDIO_URL (`studio_embed`, already checked by `studio_embed_url`: `http://127.0.0.1:<port>` or `http://localhost:<port>`
  and nothing else): one `<iframe>` whose source is exactly that address, a new-tab link above it, a hint for a blank frame, two R lines to paste into
  the RStudio Console, and the terminal commands folded in a `<details>`. The browser, not the platform, connects to that address, so it is the address
  on the computer of the person looking at the page. Only this page's CSP gains `frame-src` (web.py).
* Without it, the page as it was: a form that takes the address of the person's own Studio from the query string of this one request, and one
  `target="_blank"` link to it (not a frame), only when `studio_url` accepts it.

Every word is in the two tables below (zh and en, same keys).
"""
import re
import urllib.parse

from .web_finished import _e      # the one escape of the pages; not copied here

MAX_LENGTH = 300
SECRET_KEYS = ("token", "password", "key", "secret")

STRINGS = {
    "zh": {
        "intro": "下游分析於使用者自己的電腦或雲端環境進行，平台不代為執行，也不在 NC" "HC 登入節點啟動。",
        "folder": "結果資料夾", "unread": "尚未讀取輸出", "see_outputs": "查看輸出",
        "copy_note": "此為站台上的結果資料夾。請用下列指令，把結果表拉到自己的電腦。",
        "commands_note": "平台不執行腳本；請在自己的電腦執行下列指令，結果表會放到該電腦的資料夾。",
        "placeholder_note": "指令中的「<平台網址>」請替換為平台管理者提供的公開網址；第一行只需在首次使用時執行。",
        "paste": "貼上自己 Studio 的網址", "open": "開啟連結",
        "local_note": "http://localhost 開頭的網址，僅在瀏覽器與 Studio 位於同一台電腦時才能連線。",
        "link": "在新分頁開啟 Studio",
        "own_url": "此網址由使用者自行提供，平台不儲存、不檢查其內容。",
        "bad_scheme": "請輸入以 http:// 或 https:// 開頭的網址。",
        "bad_host": "網址缺少主機名稱，請輸入完整的網址，例如 http://localhost:8787/。",
        "bad_long": "網址長度已逾 300 個字元，請改貼較短的網址。",
        "bad_space": "網址不得含空白或換行，請重新複製網址。",
        "bad_secret": "網址不得含帳號、密碼或 token；請改貼不含這些內容的位址。",
        "embed_note": "下方畫面是這台電腦上的 RStudio，瀏覽器直接連到本機，不經過平台；平台不啟動它，也不檢查它是否在執行。",
        "embed_link": "在新分頁開啟 RStudio",
        "embed_title": "RStudio（本機）",
        "embed_blank": "若下方畫面空白：可能是 RStudio 尚未啟動，或瀏覽器擋下了對本機的連線。請按「在新分頁開啟 RStudio」，"
                       "或依 docs/OPERATIONS.md 的「Desktop platform in WSL（桌機）」一節的步驟啟動。",
        "r_note": "把下列兩行貼進 RStudio 的 Console：第一行取回結果表並載入；第二行把目前 Plots 窗格的圖送到圖庫，仍須本人在確認頁按送出。"
                  "需先在這台電腦執行過 studio-connect，且 RStudio 找得到 abf-platform。",
        "terminal_summary": "改用終端機指令（備用）",
    },
    "en": {
        "intro": "Downstream analysis is done on your own computer or cloud environment; the platform does not run it for you and does not start it on the NC" "HC login node.",
        "folder": "Results folder", "unread": "Outputs not read yet", "see_outputs": "View outputs",
        "copy_note": "This is the results folder on the site. Use the commands below to pull the result tables to your own computer.",
        "commands_note": "The platform does not run scripts; run the commands below on your own computer, and the result tables are put in a folder on that computer.",
        "placeholder_note": "In the commands, replace <platform address> with the public address the platform administrator gave you; the first command is only needed the first time.",
        "paste": "Paste the address of your own Studio", "open": "Open link",
        "local_note": "An address that starts with http://localhost works only when the browser and the Studio are on the same computer.",
        "link": "Open Studio in a new tab",
        "own_url": "This address was given by you; the platform does not store it and does not check its content.",
        "bad_scheme": "Enter an address that starts with http:// or https://.",
        "bad_host": "The address has no host name; enter the full address, for example http://localhost:8787/.",
        "bad_long": "The address is longer than 300 characters; paste a shorter one.",
        "bad_space": "The address must not contain spaces or line breaks; copy it again.",
        "bad_secret": "The address must not contain a user name, password or token; paste an address without them.",
        "embed_note": "The frame below is the RStudio on this computer: the browser connects to this computer directly, not through the platform; the platform does not start it and does not check whether it is running.",
        "embed_link": "Open RStudio in a new tab",
        "embed_title": "RStudio (this computer)",
        "embed_blank": "If the frame below is blank, RStudio is not started on this computer, or the browser blocked the connection to this computer. "
                       "Press \"Open RStudio in a new tab\", or start it with the steps in docs/OPERATIONS.md, section \"Desktop platform in WSL\".",
        "r_note": "Paste the two lines below into the RStudio Console: the first fetches the result tables and loads them; the second sends the plot now in the Plots pane "
                  "to the gallery, and the person still presses Send on the confirmation page. Run studio-connect on this computer first, and RStudio must be able to find abf-platform.",
        "terminal_summary": "Terminal commands instead (fallback)",
    },
}

_SECRET_QUERY = re.compile(r"(?:^|[?&;#])(?:%s)=" % "|".join(SECRET_KEYS), re.I)


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


_EMBED_ADDRESS = re.compile(r"http://(?:127\.0\.0\.1|localhost):([1-9][0-9]{0,4})")
LOOPBACK_NAMES = ("127.0.0.1", "localhost")


def studio_embed_url(raw):
    """(address, None) when `raw` is exactly `http://127.0.0.1:<port>` or `http://localhost:<port>` (port 1 to 65535, no leading zero), (None, None) for an
    unset or empty value, else (None, the reason as one word: space, scheme, secret, host, port or path). Nothing is trimmed or repaired: a value with a
    path, a trailing slash, a query, a fragment, a user name or any blank is refused, so what is returned can be put in a frame source and in a CSP as it is.
    Pure: nothing is read from the environment and nothing is connected to."""
    if raw is None or raw == "":
        return None, None
    if not isinstance(raw, str):
        return None, "scheme"
    m = _EMBED_ADDRESS.fullmatch(raw)
    if m and int(m.group(1)) <= 65535:
        return raw, None
    if re.search(r"[\s\x00-\x1f\x7f]", raw):
        return None, "space"
    if not raw.startswith("http://"):
        return None, "scheme"
    try:
        parts = urllib.parse.urlsplit(raw)
        host, port = parts.hostname, parts.port
    except ValueError:
        return None, "port"
    if "@" in parts.netloc:
        return None, "secret"
    if host not in LOOPBACK_NAMES:
        return None, "host"
    if port is None or port == 0:
        return None, "port"
    if parts.path or parts.query or parts.fragment or raw.endswith(("?", "#")):
        return None, "path"
    return None, "port"


def _folder(t, lang, run, outputs, board):
    out = outputs or {}
    if out.get("found") is not False and out.get("state") == "ready" and out.get("path"):
        return '<p><span class="muted">%s</span> <code>%s</code></p><p class="muted">%s</p>' % (_e(t["folder"]), _e(out["path"]), _e(t["copy_note"]))
    link = '<a href="%s">%s</a>' % (board._url(lang, run["id"], "results", tab="outputs"), _e(t["see_outputs"]))
    return '<p><span class="muted">%s</span> <span class="muted">— %s</span> %s</p><p class="muted">%s</p>' % (_e(t["folder"]), _e(t["unread"]), link, _e(t["copy_note"]))


def _commands(t, lang, run):
    server = "<platform address>" if lang == "en" else "<平台網址>"
    figure = "<image file>" if lang == "en" else "<圖檔>"
    lines = "abf-platform studio-connect --server %s\nabf-platform fetch-results %s\nabf-platform publish-figure %s %s" % (server, run["id"], run["id"], figure)
    return '<p>%s</p><pre class="reason">%s</pre><p class="muted">%s</p>' % (_e(t["commands_note"]), _e(lines), _e(t["placeholder_note"]))


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


def _r_str(text):
    """`text` as one R string literal in double quotes: backslash and quote escaped, a control character written as \\xNN, so no value leaves the string."""
    out = str(text).replace("\\", "\\\\").replace('"', '\\"')
    return '"%s"' % re.sub(r"[\x00-\x1f\x7f]", lambda m: "\\x%02x" % ord(m.group(0)), out)


def _r_lines(run):
    """The two lines to paste into the RStudio Console, with the id of the run in them as an R string: fetch the tables and load them (the command prints
    only R code), and copy the plot now shown to a temporary png and propose it to the gallery (a proposal only: the person says yes on the confirmation page)."""
    rid = _r_str(run["id"])
    one = 'eval(parse(text = system2("abf-platform", c("fetch-results", %s, "--r"), stdout = TRUE)))' % rid
    two = ('local({f <- tempfile(fileext = ".png"); dev.copy(png, filename = f); invisible(dev.off()); '
           'system2("abf-platform", c("publish-figure", %s, f))})' % rid)
    return one + "\n" + two


def _embed(t, lang, run, url):
    """The frame of RStudio and what goes with it. The frame source and the link are `url` as it is; no style attribute, no class that is not in the stylesheet."""
    link = '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (_e(url), _e(t["embed_link"]))
    frame = ('<iframe src="%s" title="%s" width="100%%" height="700" allow="local-network-access" referrerpolicy="no-referrer"></iframe>'
             % (_e(url), _e(t["embed_title"])))
    return ('<p>%s</p><p>%s</p><p class="muted">%s</p>%s<p>%s</p><pre class="reason">%s</pre><details><summary>%s</summary>%s</details>'
            % (_e(t["embed_note"]), link, _e(t["embed_blank"]), frame, _e(t["r_note"]), _e(_r_lines(run)), _e(t["terminal_summary"]), _commands(t, lang, run)))


def render_downstream(lang, run, outputs, studio, title, *, studio_embed=None):
    """The card of the downstream stage of a succeeded run. `outputs` is the answer of `run_outputs(enqueue=False)` (or None), `studio` the raw
    `studio` query value (or None), `title` the heading the board uses for this stage. `studio_embed` is the address the deployment setting
    ABF_STUDIO_URL gave, already accepted by `studio_embed_url`, or None. With it the page holds one frame of that address; the form that takes an
    address from the query string is not drawn (that value is never a link, a frame or a CSP source), and a bad value is still told as an error."""
    from . import web_board      # imported here: web_board imports this module, and only the link helper is wanted from it
    lang = "en" if lang == "en" else "zh"
    t = STRINGS[lang]
    if studio_embed:
        ok, why = studio_url(studio)
        said = '<p class="bad" role="alert"><span>✗</span> %s</p>' % _e(t[why]) if why else ""
        inner = '<p>%s</p>%s%s%s' % (_e(t["intro"]), _folder(t, lang, run, outputs, web_board), _embed(t, lang, run, studio_embed), said)
        return '<section class="card"><h2>%s</h2>%s</section>' % (_e(title), inner)
    inner = '<p>%s</p>%s%s%s%s' % (_e(t["intro"]), _folder(t, lang, run, outputs, web_board), _commands(t, lang, run), _form(t, lang, run), _answer(t, studio))
    return '<section class="card"><h2>%s</h2>%s</section>' % (_e(title), inner)
