# Nothing existing: the HTML of the three-column page of spec 011a (layout B, after Galaxy); no template library is wanted for one read-only page, and every value is escaped here.
"""The three-column page (spec 011a, layout B), as pure functions from dicts to strings.

No database, no file and no network is touched here: `web.py` reads through the actions with the logged-in caller and hands the
answers in. The stage of a run is worked out from its status each time (`stage_of`); nothing about a stage is stored. The page has no
script, no `style=` attribute and no external address, and its one stylesheet is the constant `STYLE`, whose sha256 goes into the
content-security-policy (`style_source`). Every word of the interface comes from the one table `STRINGS` (zh and en, same keys); run
names, ids and Nextflow's own failure text are data and are never translated.
"""
import base64
import hashlib
import html
import urllib.parse

STAGES = ("launch", "running", "results", "downstream", "finished")
PLACEHOLDER = {"launch": "012b", "downstream": "016", "finished": "013b"}      # the feature that will provide the stage
LIST_CAP = 100
REASON_CAP = 80
REFRESH_SECONDS = 15
# status -> symbol; the symbol and the text label carry the meaning, the colour only helps
SYMBOLS = {"running": "▶", "succeeded": "✓", "failed": "✗", "lost": "⏸"}
COUNTS = ("succeeded", "cached", "failed", "aborted", "running", "pending", "submitted")

STRINGS = {
    "zh": {
        "mine": "我的 run", "none_yet": "還沒有 run。", "later": "之後開放", "tree": "專案與分析", "settings": "設定", "logout": "登出",
        "pick": "選一個 run", "pick_hint": "從左邊挑一個 run。", "cost": "本月 SU — · 雲端 —", "more": "還有 %d 筆",
        "group": "%s（%d）",
        "stage_launch": "送出", "stage_running": "執行中", "stage_results": "結果", "stage_downstream": "下游", "stage_finished": "完成",
        "state_running": "執行中", "state_succeeded": "成功", "state_failed": "失敗", "state_lost": "失聯/暫停",
        "count_succeeded": "成功", "count_cached": "快取", "count_failed": "失敗", "count_aborted": "中止", "count_running": "執行中",
        "count_pending": "等待", "count_submitted": "已送出",
        "started": "開始", "ended": "結束", "prev": "← 上一階段", "next": "下一階段 →", "not_reached": "這個 run 還沒到這個階段。",
        "no_reason": "原因未記錄", "not_found_title": "找不到這個 run", "not_found_body": "沒有這個 run，或它不是你的。",
        "back": "回到清單", "title": "agentic-bioflow",
    },
    "en": {
        "mine": "My runs", "none_yet": "No runs yet.", "later": "Coming later", "tree": "Projects and analyses", "settings": "Settings",
        "logout": "Log out",
        "pick": "Pick a run", "pick_hint": "Choose a run on the left.", "cost": "SU this month — · Cloud —", "more": "%d more",
        "group": "%s (%d)",
        "stage_launch": "Launch", "stage_running": "Running", "stage_results": "Results", "stage_downstream": "Downstream",
        "stage_finished": "Finished",
        "state_running": "Running", "state_succeeded": "Succeeded", "state_failed": "Failed", "state_lost": "Lost/paused",
        "count_succeeded": "Succeeded", "count_cached": "Cached", "count_failed": "Failed", "count_aborted": "Aborted",
        "count_running": "Running", "count_pending": "Pending", "count_submitted": "Submitted",
        "started": "Started", "ended": "Ended", "prev": "← Previous stage", "next": "Next stage →",
        "not_reached": "This run has not reached this stage.",
        "no_reason": "reason not recorded", "not_found_title": "Run not found", "not_found_body": "There is no such run, or it is not yours.",
        "back": "Back to the list", "title": "agentic-bioflow",
    },
}

STYLE = (
    "body{font-family:sans-serif;max-width:60em;margin:1.5em auto;padding:0 1em}"
    "pre{background:#f4f4f4;padding:1em;overflow-x:auto;white-space:pre-wrap}button{font-size:1.1em;padding:.4em 1.2em}"
    ".bad{color:#a00}.ok{color:#070}"
    ":root{--surface:#f6f5f2;--raised:#fff;--sunken:#ecebe6;--ink:#1f2328;--muted:#575e66;--line:#d6d3cc;--line2:#8f8b82;"
    "--accent:#1c5d8a;--accent-weak:#e2edf5;--focus:#1c5d8a;"
    "--running:#0b5aa8;--running-bg:#e3edf9;--succeeded:#1b6837;--succeeded-bg:#e2f0e6;"
    "--failed:#b0261d;--failed-bg:#fae6e3;--lost:#865700;--lost-bg:#f7edd6}"
    "@media (prefers-color-scheme:dark){:root{--surface:#15171a;--raised:#1e2125;--sunken:#101214;--ink:#e9e7e2;--muted:#a2a8b0;"
    "--line:#33373d;--line2:#646a73;--accent:#7db8e2;--accent-weak:#1a2c3a;--focus:#9cccf0;"
    "--running:#80b6f2;--running-bg:#15263a;--succeeded:#78c792;--succeeded-bg:#14291c;--failed:#f28b81;--failed-bg:#3a1916;"
    "--lost:#e2b35e;--lost-bg:#33270e}}"
    "body.board{max-width:none;margin:0;padding:0;background:var(--surface);color:var(--ink);font-size:14px;line-height:21px}"
    "body.board *{box-sizing:border-box}body.board a{color:var(--accent);text-decoration:none}body.board a:hover{text-decoration:underline}"
    "body.board a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}"
    "body.board h1{font-size:20px;line-height:28px;margin:0}body.board h2{font-size:15px;line-height:22px;margin:0}"
    "body.board h3{font-size:12px;line-height:18px;margin:0;color:var(--muted)}body.board p{margin:0}"
    ".mast{display:flex;align-items:center;gap:16px;height:40px;padding:0 16px;background:var(--ink);color:var(--surface)}"
    ".mast .brand{font-weight:600}.mast .end{margin-left:auto;display:flex;align-items:center;gap:16px;font-size:13px}"
    "body.board .mast a{color:var(--surface);padding:0 8px}.switch{display:flex}.switch a+a{border-left:1px solid var(--surface)}"
    ".switch a.here{font-weight:700;text-decoration:underline}"
    ".wb{display:grid;grid-template-columns:232px 1fr 272px;min-height:600px}.wb>*{min-width:0}"
    ".side{background:var(--raised);border-right:1px solid var(--line);padding:16px;display:flex;flex-direction:column;gap:16px}"
    ".side .foot{margin-top:auto;border-top:1px solid var(--line);padding-top:12px;display:flex;flex-direction:column;gap:4px}"
    ".tree{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}"
    "body.board .tree a{display:flex;justify-content:space-between;gap:8px;padding:4px 8px;border-radius:4px;color:var(--ink)}"
    "body.board .tree a.here{background:var(--accent-weak);color:var(--accent);font-weight:600}"
    ".tree .st{font-size:12px;white-space:nowrap}"
    ".off,.later,.muted,.more{color:var(--muted)}.later{font-size:12px}"
    ".main{padding:24px;display:flex;flex-direction:column;gap:16px;overflow-wrap:anywhere}"
    ".head{display:flex;align-items:center;gap:12px;flex-wrap:wrap}"
    ".badge{display:inline-flex;gap:4px;padding:0 8px;border-radius:999px;font-size:12px;line-height:20px;font-weight:600;white-space:nowrap}"
    ".state-running{color:var(--running);background:var(--running-bg)}.state-succeeded{color:var(--succeeded);background:var(--succeeded-bg)}"
    ".state-failed{color:var(--failed);background:var(--failed-bg)}.state-lost{color:var(--lost);background:var(--lost-bg)}"
    ".steps{display:flex;gap:8px;list-style:none;margin:0;padding:0}.steps li{flex:1;min-width:0}"
    "body.board .steps a{display:block;padding:8px 0 0;border-top:3px solid var(--line);color:var(--muted);font-size:13px}"
    ".steps .is-done a{border-top-color:var(--succeeded);color:var(--ink)}"
    ".steps .is-current a{border-top-color:var(--accent);color:var(--ink);font-weight:600}"
    ".steps .is-later a{border-top-style:dashed;border-top-color:var(--line2)}"
    ".steps a[aria-current]{outline:2px solid var(--focus);outline-offset:2px}"
    ".card{background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:16px;display:flex;flex-direction:column;gap:16px}"
    ".counts{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:0}"
    ".counts div{background:var(--sunken);border-radius:4px;padding:6px 8px;min-width:0}"
    ".counts dt{font-size:12px;line-height:18px;color:var(--muted)}.counts dd{margin:0;font-size:15px;font-weight:600}"
    ".kv{display:flex;gap:24px;flex-wrap:wrap}.kv span{color:var(--muted)}"
    "progress{width:100%;height:6px;border:0;border-radius:999px;background:var(--sunken)}"
    "progress::-webkit-progress-bar{background:var(--sunken);border-radius:999px}"
    "progress::-webkit-progress-value{background:var(--accent);border-radius:999px}progress::-moz-progress-bar{background:var(--accent)}"
    ".pager{display:flex;justify-content:space-between;font-size:13px}"
    ".reason{font-family:ui-monospace,Consolas,monospace;font-size:13px;background:var(--sunken);border:1px solid var(--failed);"
    "border-radius:4px;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}"
    ".hist{background:var(--raised);border-left:1px solid var(--line);padding:16px;display:flex;flex-direction:column;gap:12px}"
    ".cost{background:var(--sunken);border-radius:4px;padding:8px 12px;font-size:13px}"
    ".groups{display:flex;flex-direction:column;gap:12px}.group{display:flex;flex-direction:column;gap:6px}"
    ".item{display:block;padding:6px 10px;border-radius:4px;color:var(--ink)}body.board a.item{color:var(--ink)}"
    ".item:hover{text-decoration:none}.item .t{display:flex;gap:6px;font-size:13px;line-height:19px;font-weight:600}"
    ".item .s{display:block;font-size:12px;line-height:18px;font-weight:600;overflow-wrap:anywhere}"
    ".item.state-running{background:var(--running-bg)}.item.state-running .s{color:var(--running)}"
    ".item.state-succeeded{background:var(--succeeded-bg)}.item.state-succeeded .s{color:var(--succeeded)}"
    ".item.state-failed{background:var(--failed-bg)}.item.state-failed .s{color:var(--failed)}"
    ".item.state-lost{background:var(--lost-bg)}.item.state-lost .s{color:var(--lost)}"
    ".item.here{outline:2px solid var(--focus);outline-offset:-2px}"
    "@media (max-width:900px){.wb{grid-template-columns:1fr}.main{order:-2}.hist{order:-1}.counts{grid-template-columns:repeat(4,1fr)}}"
)


def style_source():
    """The CSP source for the stylesheet: the sha256 of exactly the text between <style> and </style>."""
    return "'sha256-%s'" % base64.b64encode(hashlib.sha256(STYLE.encode("utf-8")).digest()).decode("ascii")


def esc(text):
    return html.escape(str(text), quote=True)


def pick_lang(raw):
    """English only for exactly `en`; anything else (missing, unknown, markup) is the default Chinese."""
    return "en" if raw == "en" else "zh"


def stage_of(status):
    """The stage a run belongs to, from its status alone: running, lost and failed are `running`; succeeded is `results`."""
    return "results" if status == "succeeded" else "running"


def pick_stage(raw, default):
    return raw if raw in STAGES else default


def _url(lang, run=None, stage=None):
    """A link to the board: only `/` with a query. `lang=en` is kept on every link of an English page."""
    query = []
    if run:
        query.append("run=" + urllib.parse.quote(str(run), safe=""))
    if stage:
        query.append("stage=" + stage)
    if lang == "en":
        query.append("lang=en")
    return esc("/" + ("?" + "&".join(query) if query else ""))


def _css(status):
    return status if status in SYMBOLS else "unknown"


def _state_text(t, status):
    return "%s %s" % (SYMBOLS.get(status, "?"), esc(t.get("state_" + str(status), status)))


def _badge(t, status):
    return '<span class="badge state-%s">%s</span>' % (_css(status), _state_text(t, status))


def _more(t, total):
    return '<p class="more">%s</p>' % esc(t["more"] % (total - LIST_CAP)) if total > LIST_CAP else ""


def _numbered(runs):
    """[(run, number)] newest first; the number is the place among all of this user's runs by start time, oldest = 1."""
    by_time = sorted(range(len(runs)), key=lambda i: (runs[i].get("started_at") or "", -i))
    number = {i: n + 1 for n, i in enumerate(by_time)}
    return [(runs[i], number[i]) for i in sorted(range(len(runs)), key=lambda i: number[i], reverse=True)]


def _first_line(text, cap):
    for line in str(text).splitlines():
        if line.strip():
            return line.strip()[:cap]
    return ""


def _fact(t, run, reasons):
    status = run["status"]
    if status == "running":
        tasks = run.get("tasks") or {}
        return "%d/%d" % (tasks.get("succeeded", 0) + tasks.get("cached", 0), tasks.get("total", 0))
    if status == "failed":
        return _first_line((reasons or {}).get(run["id"]) or "", REASON_CAP) or t["no_reason"]
    if status == "succeeded":
        return run.get("ended_at") or "—"
    return "—"


def _mast(name, lang, run, stage):
    zh_here = "" if lang == "en" else ' class="here"'
    en_here = ' class="here"' if lang == "en" else ""
    return ('<header class="mast"><span class="brand">agentic-bioflow</span><span class="end">'
            '<span class="switch"><a href="%s"%s>中</a><a href="%s"%s>EN</a></span><span class="who">%s</span></span></header>'
            % (_url("zh", run, stage), zh_here, _url("en", run, stage), en_here, esc(name)))


def _left(t, runs, selected_id, lang, csrf):
    rows = []
    for run in runs[:LIST_CAP]:
        here = ' class="here"' if run["id"] == selected_id else ""
        rows.append('<li><a%s href="%s"><span>%s</span><span class="st">%s</span></a></li>'
                    % (here, _url(lang, run["id"]), esc(run["name"]), _state_text(t, run["status"])))
    body = ('<ul class="tree">%s</ul>%s' % ("".join(rows), _more(t, len(runs)))) if runs else '<p class="muted">%s</p>' % esc(t["none_yet"])
    return ('<aside class="side" data-pane="left"><h2>%s</h2>%s<p class="off">%s <span class="later">%s</span></p>'
            '<div class="foot"><p class="off">%s <span class="later">%s</span></p>'
            '<form method="post" action="/logout"><input type="hidden" name="csrf" value="%s"><button type="submit">%s</button></form>'
            '</div></aside>' % (esc(t["mine"]), body, esc(t["tree"]), esc(t["later"]), esc(t["settings"]), esc(t["later"]),
                                esc(csrf), esc(t["logout"])))


def _task_card(t, run):
    tasks = run.get("tasks") or {}
    total = tasks.get("total", 0)
    done = tasks.get("succeeded", 0) + tasks.get("cached", 0)
    css = _css(run["status"])
    bar = ('<progress class="state-%s" value="%d" max="%d">%d / %d</progress>' % (css, done, total, done, total)) if total \
        else '<progress class="state-%s"></progress>' % css
    cells = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (esc(t["count_" + c]), esc(tasks.get(c, 0))) for c in COUNTS)
    out = ('%s<p class="kv"><b>%d / %d</b></p><p class="kv"><span>%s</span> %s <span>%s</span> %s</p><dl class="counts">%s</dl>'
           % (bar, done, total, esc(t["started"]), esc(run.get("started_at") or "—"), esc(t["ended"]), esc(run.get("ended_at") or "—"), cells))
    if run.get("failure_reason"):
        out += '<pre class="reason">%s</pre>' % esc(run["failure_reason"])
    return out


def _stage_card(t, run, stage):
    if stage in PLACEHOLDER:
        inner = '<p>— <span class="muted">%s</span></p>' % esc(PLACEHOLDER[stage])
    elif stage_of(run["status"]) != stage:
        inner = '<p>— <span class="muted">%s</span></p>' % esc(t["not_reached"])
    else:
        inner = _task_card(t, run)
    return '<section class="card"><h2>%s</h2>%s</section>' % (esc(t["stage_" + stage]), inner)


def _middle(t, selected, stage_param, lang):
    if selected is None:
        return '<main class="main" data-pane="middle"><h1>%s</h1><p class="muted">%s</p></main>' % (esc(t["pick"]), esc(t["pick_hint"]))
    own = stage_of(selected["status"])
    current = pick_stage(stage_param, own)
    index, rank = STAGES.index(current), STAGES.index(own)
    cells = []
    for n, s in enumerate(STAGES):
        kind = "is-done" if n < rank else ("is-current" if n == rank else "is-later")
        mark = ' aria-current="step"' if s == current else ""
        cells.append('<li class="%s" data-step="%s"><a href="%s"%s>%s</a></li>'
                     % (kind, s, _url(lang, selected["id"], s), mark, esc(t["stage_" + s])))
    prev_ = ('<a rel="prev" href="%s">%s</a>' % (_url(lang, selected["id"], STAGES[index - 1]), esc(t["prev"]))) if index > 0 else "<span></span>"
    next_ = ('<a rel="next" href="%s">%s</a>' % (_url(lang, selected["id"], STAGES[index + 1]), esc(t["next"]))) \
        if index < len(STAGES) - 1 else "<span></span>"
    return ('<main class="main" data-pane="middle"><div class="head"><h1>%s</h1>%s</div>'
            '<ol class="steps" data-current="%s">%s</ol>%s<p class="pager">%s%s</p></main>'
            % (esc(selected["name"]), _badge(t, selected["status"]), current, "".join(cells), _stage_card(t, selected, current), prev_, next_))


def _item(t, run, number, fact, selected_id, lang):
    here = " here" if run["id"] == selected_id else ""
    return ('<a class="item state-%s%s" href="%s"><span class="t"><span class="n">%d</span><span class="nm">%s</span></span>'
            '<span class="s">%s · %s</span></a>'
            % (_css(run["status"]), here, _url(lang, run["id"]), number, esc(run["name"]), _state_text(t, run["status"]), esc(fact)))


def _right(t, runs, selected_id, lang, reasons):
    numbered = _numbered(runs)
    out = ['<aside class="hist" data-pane="right"><p class="cost" data-cost="month">%s</p><div class="groups">' % esc(t["cost"])]
    for stage in ("running", "results"):
        mine = [(r, n) for r, n in numbered if stage_of(r["status"]) == stage]
        blocks = "".join(_item(t, r, n, _fact(t, r, reasons), selected_id, lang) for r, n in mine[:LIST_CAP])
        out.append('<section class="group" data-stage="%s"><h3>%s</h3>%s%s</section>'
                   % (stage, esc(t["group"] % (t["stage_" + stage], len(mine))), blocks if mine else '<p class="muted">—</p>',
                      _more(t, len(mine))))
    out.append('<section class="group" data-stage="later"><p class="later">%s</p></section></div></aside>' % esc(t["later"]))
    return "".join(out)


def failed_ids_shown(runs):
    """The ids of the failed runs the right column will show a reason for (the first LIST_CAP of its first group, in its order)."""
    shown = [r for r, _ in _numbered(runs) if stage_of(r["status"]) == "running"][:LIST_CAP]
    return [r["id"] for r in shown if r["status"] == "failed"]


def document(title, body, refresh=False, board=False, lang="zh"):
    """A whole page. Only the board asks for the meta refresh."""
    head = "<meta http-equiv=\"refresh\" content=\"%d\">" % REFRESH_SECONDS if refresh else ""
    return ("<!doctype html><html lang=\"%s\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">%s"
            "<title>%s</title><style>%s</style></head><body%s>%s</body></html>"
            % ("en" if lang == "en" else "zh-Hant", head, esc(title), STYLE, " class=\"board\"" if board else "", body))


def render_board(name, csrf, runs, selected=None, stage_param=None, lang="zh", reasons=None):
    """The page of a logged-in user: `runs` newest first (as list_runs gives them), `selected` the detail of one run or None;
    `reasons` maps the id of a failed run to its failure_reason (read by the caller, with the caller's rights)."""
    lang = pick_lang(lang)
    t = STRINGS[lang]
    selected_id = selected["id"] if selected is not None else None
    stage = pick_stage(stage_param, None) if selected is not None else None
    body = '%s<div class="wb">%s%s%s</div>' % (_mast(name, lang, selected_id, stage), _left(t, runs, selected_id, lang, csrf),
                                                _middle(t, selected, stage_param, lang), _right(t, runs, selected_id, lang, reasons))
    return document(t["title"], body, refresh=True, board=True, lang=lang)


def render_not_found(name, lang="zh"):
    """The 404 of the board: the same bytes for a missing run and for somebody else's, and it never repeats the requested id."""
    lang = pick_lang(lang)
    t = STRINGS[lang]
    body = ('%s<main class="main"><h1>%s</h1><p>%s</p><p><a href="%s">%s</a></p></main>'
            % (_mast(name, lang, None, None), esc(t["not_found_title"]), esc(t["not_found_body"]), _url(lang), esc(t["back"])))
    return document(t["title"], body, board=True, lang=lang)
