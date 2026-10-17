# Nothing existing: the HTML of the three-pane page of spec 011a; no template library is wanted for one read-only page, and every value is escaped here.
"""The three-pane page (spec 011a), as pure functions from dicts to strings.

No database, no file and no network is touched here: `web.py` reads through the actions with the logged-in caller and hands the
answers in. The stage of a run is worked out from its status each time (`stage_of`); nothing about a stage is stored. The page has no
script, no `style=` attribute and no external address, and its one stylesheet is the constant `STYLE`, whose sha256 goes into the
content-security-policy (`style_source`).
"""
import base64
import hashlib
import html
import urllib.parse

STAGES = ("launch", "running", "results", "downstream", "finished")
STAGE_NAMES = {"launch": "送出", "running": "執行中", "results": "結果", "downstream": "下游分析", "finished": "完成"}
PLACEHOLDER = {"launch": "012b", "downstream": "016", "finished": "013b"}      # the feature that will provide the stage
LIST_CAP = 100
REFRESH_SECONDS = 15
# status -> (symbol, text label, css class); the label and the symbol carry the meaning, the colour only helps
STATES = {"running": ("▶", "執行中"), "succeeded": ("✓", "成功"), "failed": ("✗", "失敗"), "lost": ("⏸", "失聯/暫停")}
COUNTS = ("succeeded", "cached", "failed", "aborted", "running", "pending", "submitted")

STYLE = (
    "body{font-family:sans-serif;max-width:60em;margin:1.5em auto;padding:0 1em}"
    "pre{background:#f4f4f4;padding:1em;overflow-x:auto;white-space:pre-wrap}button{font-size:1.1em;padding:.4em 1.2em}"
    ".bad{color:#a00}.ok{color:#070}"
    "body.board{max-width:none;margin:0;padding:0}"
    ".grid{display:grid;grid-template-columns:18em 1fr 20em;gap:1em;padding:1em;align-items:start}"
    "@media (max-width:900px){.grid{grid-template-columns:1fr}}"
    ".pane{border:1px solid #ccc;border-radius:.4em;padding:.6em 1em;min-width:0;overflow-wrap:anywhere}"
    ".pane h2,.pane h3{margin:.2em 0 .5em;font-size:1.05em}"
    "ul.runs{list-style:none;margin:0;padding:0}ul.runs li{margin:.25em 0}"
    ".state{font-weight:bold;white-space:nowrap}"
    ".state-running{color:#0b4fb3}.state-succeeded{color:#1a7a1a}.state-failed{color:#b00020}.state-lost{color:#9a6200}"
    ".strip{display:flex;flex-wrap:wrap;gap:.3em;align-items:center}"
    ".strip a{padding:.2em .6em;border:1px solid #999;border-radius:.3em;text-decoration:none}"
    ".strip a.here{background:#eee;font-weight:bold}"
    ".more,.muted{color:#666}.who{border-top:1px solid #ccc;margin-top:1em;padding-top:.5em}"
    "progress{width:100%}"
)


def style_source():
    """The CSP source for the stylesheet: the sha256 of exactly the text between <style> and </style>."""
    return "'sha256-%s'" % base64.b64encode(hashlib.sha256(STYLE.encode("utf-8")).digest()).decode("ascii")


def esc(text):
    return html.escape(str(text), quote=True)


def stage_of(status):
    """The stage a run belongs to, from its status alone: running, lost and failed are `running`; succeeded is `results`."""
    return "results" if status == "succeeded" else "running"


def pick_stage(raw, default):
    return raw if raw in STAGES else default


def _href(run_id, stage=None):
    out = "/?run=" + urllib.parse.quote(str(run_id), safe="")
    if stage:
        out += "&stage=" + stage
    return esc(out)


def _state(status):
    symbol, label = STATES.get(status, ("?", str(status)))
    css = status if status in STATES else "unknown"
    return '<span class="state state-%s">%s %s</span>' % (css, symbol, esc(label))


def _run_item(run):
    return '<li>%s <a href="%s">%s</a></li>' % (_state(run["status"]), _href(run["id"]), esc(run["name"]))


def _capped(items):
    shown = "".join(items[:LIST_CAP])
    more = '<p class="more">還有 %d 筆</p>' % (len(items) - LIST_CAP) if len(items) > LIST_CAP else ""
    return "<ul class=\"runs\">%s</ul>%s" % (shown, more)


def _left(runs, name, csrf):
    body = _capped([_run_item(r) for r in runs]) if runs else "<p class=\"muted\">還沒有 run。</p>"
    return ("<div class=\"pane\" data-pane=\"left\"><h2>我的 run</h2>%s<p class=\"muted\">專案與分析（011b）尚未開放</p>"
            "<div class=\"who\"><p>%s</p><p class=\"muted\">設定（尚未開放）</p>"
            "<form method=\"post\" action=\"/logout\"><input type=\"hidden\" name=\"csrf\" value=\"%s\">"
            "<button type=\"submit\">登出</button></form></div></div>" % (body, esc(name), esc(csrf)))


def _tasks(run):
    tasks = run.get("tasks") or {}
    total = tasks.get("total", 0)
    done = tasks.get("succeeded", 0) + tasks.get("cached", 0)
    bar = ('<progress value="%d" max="%d">%d / %d</progress>' % (done, total, done, total)) if total else "<progress></progress>"
    rows = "".join("<li>%s: %s</li>" % (c, esc(tasks.get(c, 0))) for c in COUNTS)
    return "%s<p>%d / %d</p><ul>%s</ul>" % (bar, done, total, rows)


def _stage_body(run, stage):
    if stage in PLACEHOLDER:
        return "<p>— <span class=\"muted\">（%s）</span></p>" % PLACEHOLDER[stage]
    if stage_of(run["status"]) != stage:
        return "<p>— <span class=\"muted\">這個 run 還沒到這個階段。</span></p>"
    out = "<p>%s</p><p>開始：%s</p><p>結束：%s</p>" % (_state(run["status"]), esc(run.get("started_at") or "—"), esc(run.get("ended_at") or "—"))
    out += _tasks(run)
    if run.get("failure_reason"):
        out += "<pre>%s</pre>" % esc(run["failure_reason"])
    return out


def _middle(selected, stage_param):
    if selected is None:
        return "<div class=\"pane\" data-pane=\"middle\"><h2>選一個 run</h2><p class=\"muted\">從左邊挑一個 run。</p></div>"
    current = pick_stage(stage_param, stage_of(selected["status"]))
    i = STAGES.index(current)
    parts = []
    for s in STAGES:
        parts.append('<a href="%s"%s>%s</a>' % (_href(selected["id"], s), ' class="here" aria-current="step"' if s == current else "",
                                                esc(STAGE_NAMES[s])))
    strip = " → ".join(parts)
    prev_ = '<a rel="prev" href="%s">← %s</a>' % (_href(selected["id"], STAGES[i - 1]), esc(STAGE_NAMES[STAGES[i - 1]])) if i > 0 else ""
    next_ = ('<a rel="next" href="%s">%s →</a>' % (_href(selected["id"], STAGES[i + 1]), esc(STAGE_NAMES[STAGES[i + 1]]))
             if i < len(STAGES) - 1 else "")
    return ("<div class=\"pane\" data-pane=\"middle\"><h2>%s</h2><div class=\"strip\" data-current=\"%s\">%s</div>"
            "<p>%s %s</p>%s</div>" % (esc(selected["name"]), current, strip, prev_, next_, _stage_body(selected, current)))


def _right(runs):
    out = ["<div class=\"pane\" data-pane=\"right\"><div data-cost=\"month\"><h2>本月費用</h2><p>NCHC SU —</p><p>雲端 —</p></div>"]
    for s in STAGES:
        items = [r for r in runs if stage_of(r["status"]) == s]
        if s in PLACEHOLDER and not items:
            out.append('<section data-stage="%s"><h3>%s —</h3><p class="muted">%s</p></section>' % (s, esc(STAGE_NAMES[s]), PLACEHOLDER[s]))
        else:
            out.append('<section data-stage="%s"><h3>%s（%d）</h3>%s</section>'
                       % (s, esc(STAGE_NAMES[s]), len(items), _capped([_run_item(r) for r in items]) if items else "<p class=\"muted\">—</p>"))
    out.append("</div>")
    return "".join(out)


def document(title, body, refresh=False, board=False):
    """A whole page. Only the three-pane page asks for the meta refresh."""
    head = "<meta http-equiv=\"refresh\" content=\"%d\">" % REFRESH_SECONDS if refresh else ""
    return ("<!doctype html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">%s"
            "<title>%s</title><style>%s</style></head><body%s>%s</body></html>"
            % (head, esc(title), STYLE, " class=\"board\"" if board else "", body))


def render_board(name, csrf, runs, selected=None, stage_param=None):
    """The page of a logged-in user: `runs` newest first (as list_runs gives them), `selected` the detail of one run or None."""
    body = "<div class=\"grid\">%s%s%s</div>" % (_left(runs, name, csrf), _middle(selected, stage_param), _right(runs))
    return document("agentic-bioflow", body, refresh=True, board=True)
