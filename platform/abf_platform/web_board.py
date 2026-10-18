# Nothing existing: the HTML of the read-only board of spec 011a (web design v1, DESIGN.md); no template library is wanted for a handful of read-only pages, and every value is escaped here.
"""The board pages (spec 011a, web design v1), as pure functions from dicts to strings.

No database, no file and no network is touched here: `web.py` reads through the actions with the logged-in caller and hands the
answers in. The stage of a run is worked out from its status each time (`stage_of`); nothing about a stage is stored. The pages have no
script, no `style=` attribute and no external address, and their one stylesheet is the constant `STYLE`, whose sha256 goes into the
content-security-policy (`style_source`). Every word of the interface comes from the one table `STRINGS` (zh and en, same keys); run
names, ids and Nextflow's own failure text are data and are never translated. Colours, type sizes, spacings and radii are only the
tokens of DESIGN.md.
"""
import base64
import datetime
import hashlib
import html
import urllib.parse

STAGES = ("launch", "running", "results", "downstream", "finished")
PLACEHOLDER = {"launch": "012b", "downstream": "016", "finished": "013b"}      # the feature that will provide the stage
LIST_CAP = 100
REASON_CAP = 80
REFRESH_SECONDS = 15
TAIPEI = datetime.timedelta(hours=8)
# status -> symbol; the symbol and the text label carry the meaning, the colour only helps
SYMBOLS = {"running": "▶", "succeeded": "✓", "failed": "✗", "lost": "⏸"}
COUNTS = ("succeeded", "cached", "failed", "aborted", "running", "pending", "submitted")
SETTINGS = (("set_ce", ()), ("set_cred", ()), ("set_keys", ("set_ai_key", "set_second_key")), ("set_me", ("set_step", "set_dev")),
            ("set_ops", ()), ("set_roles", ()))

STRINGS = {
    "zh": {
        "title": "agentic-bioflow", "now": "現在", "mine": "我的 run", "none_yet": "還沒有 run。", "later": "之後開放",
        "new_project": "＋ 新專案", "search_projects": "搜尋專案或分析", "upload": "↑ 上傳資料", "settings": "設定", "explorer": "資料瀏覽",
        "dashboard": "儀表板", "logout": "登出", "cost_su": "SU —", "cost_cloud": "雲端 NT$ —", "tab_progress": "分析進度", "tab_chat": "聊天",
        "search": "搜尋", "all_analyses": "全部分析", "yours_only": "只顯示你的", "more": "還有 %d 筆", "group": "%s（%d）",
        "card_running": "正在跑", "card_attention": "需要注意",
        "stage_launch": "送出", "stage_running": "執行中", "stage_results": "結果", "stage_downstream": "下游", "stage_finished": "完成",
        "state_running": "執行中", "state_succeeded": "成功", "state_failed": "失敗", "state_lost": "失聯/暫停",
        "count_succeeded": "成功", "count_cached": "快取", "count_failed": "失敗", "count_aborted": "中止", "count_running": "執行中",
        "count_pending": "等待", "count_submitted": "已送出",
        "started": "開始", "ended": "結束", "prev": "← 上一階段", "next": "下一階段 →", "not_reached": "這個 run 還沒到這個階段。",
        "no_reason": "原因未記錄", "not_found_title": "找不到這個 run", "not_found_body": "沒有這個 run，或它不是你的。",
        "back": "回到「現在」", "set_ce": "運算環境", "set_cred": "憑證", "set_keys": "密碼與金鑰", "set_ai_key": "AI 模型金鑰",
        "set_second_key": "Jev 金鑰（選填）", "set_me": "個人", "set_step": "逐步模式", "set_dev": "開發模式", "set_ops": "營運者後台",
        "set_roles": "角色（老師／學生）",
    },
    "en": {
        "title": "agentic-bioflow", "now": "Now", "mine": "My runs", "none_yet": "No runs yet.", "later": "Coming later",
        "new_project": "+ New project", "search_projects": "Search projects or analyses", "upload": "↑ Upload data", "settings": "Settings",
        "explorer": "Data explorer", "dashboard": "Dashboard", "logout": "Log out", "cost_su": "SU —", "cost_cloud": "Cloud NT$ —",
        "tab_progress": "Progress", "tab_chat": "Chat", "search": "Search", "all_analyses": "All analyses", "yours_only": "Yours only",
        "more": "%d more", "group": "%s (%d)", "card_running": "Running now", "card_attention": "Needs attention",
        "stage_launch": "Launch", "stage_running": "Running", "stage_results": "Results", "stage_downstream": "Downstream",
        "stage_finished": "Finished",
        "state_running": "Running", "state_succeeded": "Succeeded", "state_failed": "Failed", "state_lost": "Lost/paused",
        "count_succeeded": "Succeeded", "count_cached": "Cached", "count_failed": "Failed", "count_aborted": "Aborted",
        "count_running": "Running", "count_pending": "Pending", "count_submitted": "Submitted",
        "started": "Started", "ended": "Ended", "prev": "← Previous stage", "next": "Next stage →",
        "not_reached": "This run has not reached this stage.",
        "no_reason": "reason not recorded", "not_found_title": "Run not found", "not_found_body": "There is no such run, or it is not yours.",
        "back": "Back to Now", "set_ce": "Compute environments", "set_cred": "Credentials", "set_keys": "Passwords and keys",
        "set_ai_key": "AI model key", "set_second_key": "Jev key (optional)", "set_me": "Personal", "set_step": "Step-by-step mode",
        "set_dev": "Development mode", "set_ops": "Operator panel", "set_roles": "Roles (teacher / student)",
    },
}

SANS = 'system-ui,-apple-system,"Segoe UI","Noto Sans TC","Microsoft JhengHei",sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
STYLE = (
    ":root{--surface:#f6f5f2;--raised:#ffffff;--sunken:#ecebe6;--ink:#1f2328;--muted:#575e66;--line:#d6d3cc;--line2:#8f8b82;"
    "--accent:#1c5d8a;--accent-weak:#e2edf5;--focus:#1c5d8a;"
    "--running:#0b5aa8;--running-bg:#e3edf9;--succeeded:#1b6837;--succeeded-bg:#e2f0e6;"
    "--failed:#b0261d;--failed-bg:#fae6e3;--lost:#865700;--lost-bg:#f7edd6}"
    "@media (prefers-color-scheme:dark){:root{--surface:#15171a;--raised:#1e2125;--sunken:#101214;--ink:#e9e7e2;--muted:#a2a8b0;"
    "--line:#33373d;--line2:#646a73;--accent:#7db8e2;--accent-weak:#1a2c3a;--focus:#9cccf0;"
    "--running:#80b6f2;--running-bg:#15263a;--succeeded:#78c792;--succeeded-bg:#14291c;--failed:#f28b81;--failed-bg:#3a1916;"
    "--lost:#e2b35e;--lost-bg:#33270e}}"
    "*{box-sizing:border-box}"
    "body{margin:0;font-family:" + SANS + ";font-size:13px;line-height:20px;background:var(--surface);color:var(--ink)}"
    "a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}"
    "a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}summary:focus-visible{outline:2px solid var(--focus);outline-offset:2px}"
    "h1{font-size:22px;line-height:28px;margin:0}h2{font-size:15px;line-height:22px;margin:0}p{margin:0}"
    "button{font:inherit;padding:8px 16px;border:1px solid var(--accent);border-radius:4px;background:var(--accent);"
    "color:var(--raised);cursor:pointer}"
    "input{font:inherit;padding:8px;border:1px solid var(--line2);border-radius:4px;background:var(--raised);color:var(--ink)}"
    "pre{font-family:" + MONO + ";font-size:13px;background:var(--sunken);border-radius:4px;padding:12px;overflow-x:auto;white-space:pre-wrap;margin:0}"
    "code{font-family:" + MONO + "}small{font-size:12px;color:var(--muted)}"
    ".bad{color:var(--failed)}.ok{color:var(--succeeded)}"
    ".narrow{max-width:640px;margin:0 auto;padding:24px;display:flex;flex-direction:column;gap:16px}"
    ".mast{display:flex;align-items:center;gap:16px;height:40px;padding:0 16px;background:var(--ink);color:var(--surface)}"
    ".mast .brand{font-weight:600}.mast .end{margin-left:auto;display:flex;align-items:center;gap:16px}"
    ".mast a{color:var(--surface);padding:0 8px}.mast a:focus-visible{outline-color:var(--surface)}"
    ".costs{display:flex;gap:12px}.cost{font-size:12px}"
    ".switch{display:flex}.switch a+a{border-left:1px solid var(--surface)}.switch a.here{font-weight:600;text-decoration:underline}"
    ".wb{display:grid;grid-template-columns:272px minmax(0,1fr) 320px;min-height:calc(100vh - 40px)}.wb>*{min-width:0}"
    "@media (max-width:1200px){.wb{grid-template-columns:232px minmax(0,1fr) 288px}}"
    ".side{background:var(--raised);border-right:1px solid var(--line);padding:16px;display:flex;flex-direction:column;gap:12px}"
    ".nav,.tools,.rows,.foot{display:flex;flex-direction:column;gap:4px}"
    ".foot{margin-top:auto;border-top:1px solid var(--line);padding-top:12px}"
    ".nv,.row{display:flex;align-items:center;gap:8px;padding:4px 8px;border-radius:4px;color:var(--ink)}"
    "a.nv.here,a.row.here{background:var(--accent-weak);font-weight:600}"
    ".nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.row .nm{flex:1}"
    ".stg{font-size:12px;color:var(--muted);white-space:nowrap}"
    ".off,.muted{color:var(--muted)}.off{padding:4px 8px}.later{font-size:12px;color:var(--muted)}.more{font-size:12px;color:var(--muted)}"
    ".state-running{--c:var(--running);--bg:var(--running-bg)}.state-succeeded{--c:var(--succeeded);--bg:var(--succeeded-bg)}"
    ".state-failed{--c:var(--failed);--bg:var(--failed-bg)}.state-lost{--c:var(--lost);--bg:var(--lost-bg)}"
    ".sym{color:var(--c)}"
    ".main{padding:24px;display:flex;flex-direction:column;gap:16px;overflow-wrap:anywhere}"
    ".head{display:flex;align-items:center;gap:12px;flex-wrap:wrap}"
    ".badge{display:inline-flex;gap:4px;padding:0 8px;border-radius:999px;font-size:12px;line-height:20px;font-weight:600;"
    "white-space:nowrap;color:var(--c);background:var(--bg)}"
    ".steps{display:flex;gap:8px;list-style:none;margin:0;padding:0}.steps li{flex:1;min-width:0}"
    ".steps a{display:block;padding:8px 0 0;color:var(--muted)}"
    ".steps .is-done a{border-top:3px solid var(--succeeded);color:var(--ink)}"
    ".steps .is-current a{border-top:3px solid var(--accent);color:var(--ink);font-weight:600}"
    ".steps .is-later a{border-top:3px dashed var(--line2)}"
    ".steps a[aria-current]{outline:2px solid var(--focus);outline-offset:2px}"
    ".card{background:var(--raised);border:1px solid var(--line);border-radius:6px;padding:16px;display:flex;flex-direction:column;gap:12px}"
    ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}"
    ".num{font-weight:600;font-size:15px;margin-left:8px}"
    ".lines{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}"
    ".line{display:flex;flex-wrap:wrap;gap:8px;padding:4px 8px;border-radius:4px;background:var(--bg);color:var(--ink)}"
    ".line .lb{color:var(--c);font-weight:600}.why{color:var(--muted)}"
    ".counts{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:0}"
    ".counts div{background:var(--sunken);border-radius:4px;padding:4px 8px;min-width:0}"
    ".counts dt{font-size:12px;color:var(--muted)}.counts dd{margin:0;font-size:15px;font-weight:600}"
    ".kv{display:flex;gap:12px;flex-wrap:wrap}.kv span{color:var(--muted)}.kv .done{color:var(--ink);font-weight:600}"
    "progress{display:block;width:100%;height:4px;border:0;border-radius:999px;background:var(--sunken);margin-top:4px;appearance:none}"
    "progress::-webkit-progress-bar{background:var(--sunken);border-radius:999px}"
    "progress::-webkit-progress-value{background:var(--accent);border-radius:999px}progress::-moz-progress-bar{background:var(--accent)}"
    ".pager{display:flex;justify-content:space-between}"
    ".reason{font-family:" + MONO + ";font-size:13px;background:var(--sunken);border:1px solid var(--failed);border-radius:4px;"
    "padding:12px;white-space:pre-wrap;margin:0}"
    ".sec ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}"
    ".rail{background:var(--raised);border-left:1px solid var(--line);padding:16px;display:flex;flex-direction:column;gap:12px}"
    ".tabs{display:flex;gap:16px;border-bottom:1px solid var(--line);padding-bottom:4px}.tab.is-on{font-weight:600}"
    ".tally{display:flex;gap:12px;font-weight:600}"
    ".group{display:flex;flex-direction:column;gap:8px}.group>summary{cursor:pointer;font-size:12px;font-weight:600;color:var(--muted)}"
    ".items{display:flex;flex-direction:column;gap:8px;margin-top:8px}"
    ".item{display:block;padding:8px 12px;border-radius:6px;color:var(--ink);background:var(--bg)}"
    "a.item{color:var(--ink)}.item:hover{text-decoration:none}"
    ".item .t{display:flex;gap:8px;font-weight:600}.item .t .nm{flex:1;white-space:normal;overflow-wrap:anywhere}"
    ".item .s{display:block;font-size:12px;font-weight:600;color:var(--c)}.item .why{display:block;font-size:12px;overflow-wrap:anywhere}"
    ".item.here{outline:2px solid var(--focus);outline-offset:-2px}"
    "@media (max-width:900px){.wb{grid-template-columns:1fr}.main{order:-2}.rail{order:-1}.costs{display:none}"
    ".counts{grid-template-columns:repeat(4,1fr)}}"
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


def _url(lang, run=None, stage=None, path="/"):
    """A link to a board page: `/` or `/settings` with a query. `lang=en` is kept on every link of an English page."""
    query = []
    if run:
        query.append("run=" + urllib.parse.quote(str(run), safe=""))
    if stage:
        query.append("stage=" + stage)
    if lang == "en":
        query.append("lang=en")
    return esc(path + ("?" + "&".join(query) if query else ""))


def _css(status):
    return status if status in SYMBOLS else "unknown"


def _sym(status):
    return SYMBOLS.get(status, "?")


def _state(t, status):
    return t.get("state_" + str(status), str(status))


def _time(iso):
    """`MM-DD HH:mm` in Asia/Taipei (a fixed +8 hours: Taiwan has no summer time) from the UTC text of the run view."""
    try:
        moment = datetime.datetime.strptime(str(iso), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return "—"
    return (moment + TAIPEI).strftime("%m-%d %H:%M")


def _later(t):
    return '<span class="later">%s</span>' % esc(t["later"])


def _grey(t, key):
    return '<span class="off">%s %s</span>' % (esc(t[key]), _later(t))


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


def _done_total(run):
    tasks = run.get("tasks") or {}
    return tasks.get("succeeded", 0) + tasks.get("cached", 0), tasks.get("total", 0)


def _progress(run):
    done, total = _done_total(run)
    return '<progress value="%d" max="%d"></progress>' % (done, total) if total else "<progress></progress>"


def _reason(t, run, reasons):
    return _first_line((reasons or {}).get(run["id"]) or "", REASON_CAP) or t["no_reason"]


def _attention(numbered):
    return [(r, n) for r, n in numbered if r["status"] in ("failed", "lost")]


def _mast(t, name, lang, run, stage, path="/"):
    zh_here = "" if lang == "en" else ' class="here"'
    en_here = ' class="here"' if lang == "en" else ""
    return ('<header class="mast"><span class="brand">agentic-bioflow</span><span class="end">'
            '<span class="costs"><span class="cost">%s</span><span class="cost">%s</span></span>'
            '<span class="switch"><a href="%s"%s>中</a><a href="%s"%s>EN</a></span><span class="who">%s</span></span></header>'
            % (esc(t["cost_su"]), esc(t["cost_cloud"]), _url("zh", run, stage, path), zh_here, _url("en", run, stage, path), en_here, esc(name)))


def _left(t, runs, selected_id, lang, csrf, here):
    rows = []
    for run in runs[:LIST_CAP]:
        mark = " here" if run["id"] == selected_id else ""
        rows.append('<a class="row state-%s%s" href="%s"><span class="sym">%s</span><span class="nm">%s</span><span class="stg">%s</span></a>'
                    % (_css(run["status"]), mark, _url(lang, run["id"]), _sym(run["status"]), esc(run["name"]),
                       esc(t["stage_" + stage_of(run["status"])])))
    body = ('<div class="rows">%s</div>%s' % ("".join(rows), _more(t, len(runs)))) if runs else '<p class="muted">%s</p>' % esc(t["none_yet"])
    return ('<aside class="side" data-pane="left"><nav class="nav"><a class="nv%s" href="%s">%s</a></nav><h2>%s</h2>'
            '<div class="tools">%s%s%s</div>%s'
            '<div class="foot"><a class="nv%s" href="%s">%s</a>%s%s'
            '<form method="post" action="/logout"><input type="hidden" name="csrf" value="%s"><button type="submit">%s</button></form>'
            '</div></aside>'
            % (" here" if here == "now" else "", _url(lang), esc(t["now"]), esc(t["mine"]), _grey(t, "new_project"), _grey(t, "search_projects"),
               _grey(t, "upload"), body, " here" if here == "settings" else "", _url(lang, path="/settings"), esc(t["settings"]),
               _grey(t, "explorer"), _grey(t, "dashboard"), esc(csrf), esc(t["logout"])))


def _task_card(t, run):
    tasks = run.get("tasks") or {}
    done, total = _done_total(run)
    cells = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (esc(t["count_" + c]), esc(tasks.get(c, 0))) for c in COUNTS)
    out = ('%s<p class="kv"><span class="done">%d / %d</span></p><p class="kv"><span>%s</span> %s <span>%s</span> %s</p><dl class="counts">%s</dl>'
           % (_progress(run), done, total, esc(t["started"]), esc(_time(run.get("started_at"))), esc(t["ended"]), esc(_time(run.get("ended_at"))), cells))
    if run.get("failure_reason"):
        out += '<pre class="reason">%s</pre>' % esc(run["failure_reason"])
    return out


def _stage_card(t, run, stage):
    if stage in PLACEHOLDER:
        inner = '<p>— <span class="muted">%s</span></p>' % esc(PLACEHOLDER[stage])
    elif stage != "running" and stage_of(run["status"]) != stage:
        inner = '<p>— <span class="muted">%s</span></p>' % esc(t["not_reached"])
    else:
        inner = _task_card(t, run)
    return '<section class="card"><h2>%s</h2>%s</section>' % (esc(t["stage_" + stage]), inner)


def _run_page(t, selected, stage_param, lang):
    own = stage_of(selected["status"])
    current = pick_stage(stage_param, own)
    index, rank = STAGES.index(current), STAGES.index(own)
    cells = []
    for n, s in enumerate(STAGES):
        kind = "is-done" if n < rank else ("is-current" if n == rank else "is-later")
        mark = ' aria-current="step"' if s == current else ""
        label = ("✓ " if kind == "is-done" else "") + t["stage_" + s]
        cells.append('<li class="%s" data-step="%s"><a href="%s"%s>%s</a></li>' % (kind, s, _url(lang, selected["id"], s), mark, esc(label)))
    prev_ = ('<a rel="prev" href="%s">%s</a>' % (_url(lang, selected["id"], STAGES[index - 1]), esc(t["prev"]))) if index > 0 else "<span></span>"
    next_ = ('<a rel="next" href="%s">%s</a>' % (_url(lang, selected["id"], STAGES[index + 1]), esc(t["next"]))) \
        if index < len(STAGES) - 1 else "<span></span>"
    status = selected["status"]
    badge = '<span class="badge state-%s">%s %s</span>' % (_css(status), _sym(status), esc(_state(t, status)))
    return ('<main class="main" data-pane="middle"><div class="head"><h1>%s</h1>%s</div>'
            '<ol class="steps" data-current="%s">%s</ol>%s<p class="pager">%s%s</p></main>'
            % (esc(selected["name"]), badge, current, "".join(cells), _stage_card(t, selected, current), prev_, next_))


def _line(t, run, lang, reasons):
    status = run["status"]
    why = ' <span class="why">%s</span>' % esc(_reason(t, run, reasons)) if status == "failed" else ""
    return ('<li><a class="line state-%s" href="%s"><span class="sym">%s</span> <span class="lb">%s</span> <span class="nm">%s</span>%s</a></li>'
            % (_css(status), _url(lang, run["id"]), _sym(status), esc(_state(t, status)), esc(run["name"]), why))


def _card(t, which, runs, lang, reasons, key):
    shown = "".join(_line(t, r, lang, reasons) for r in runs[:LIST_CAP])
    body = ('<ul class="lines">%s</ul>%s' % (shown, _more(t, len(runs)))) if runs else '<p class="muted">—</p>'
    return '<section class="card" data-card="%s"><h2>%s<span class="num">%d</span></h2>%s</section>' % (which, esc(t[key]), len(runs), body)


def _now_page(t, runs, lang, reasons):
    numbered = _numbered(runs)
    running = [r for r, _ in numbered if r["status"] == "running"]
    attention = [r for r, _ in _attention(numbered)]
    empty = '<p class="muted">%s</p>' % esc(t["none_yet"]) if not runs else ""
    return ('<main class="main" data-pane="middle"><h1>%s</h1>%s<div class="cards">%s%s</div></main>'
            % (esc(t["now"]), empty, _card(t, "running", running, lang, reasons, "card_running"),
               _card(t, "attention", attention, lang, reasons, "card_attention")))


def _settings_page(t):
    secs = []
    for head, entries in SETTINGS:
        inner = "<ul>%s</ul>" % "".join("<li>%s</li>" % _grey(t, e) for e in entries) if entries else "<p>%s</p>" % _later(t)
        secs.append('<section class="card sec"><h2>%s</h2>%s</section>' % (esc(t[head]), inner))
    return '<main class="main" data-pane="middle"><h1>%s</h1>%s</main>' % (esc(t["settings"]), "".join(secs))


def _item(t, run, number, selected_id, lang, reasons):
    status = run["status"]
    mark = " here" if run["id"] == selected_id else ""
    done, total = _done_total(run)
    why = '<span class="why">%s</span>' % esc(_reason(t, run, reasons)) if status == "failed" else ""
    return ('<a class="item state-%s%s" href="%s"><span class="t"><span class="n">%d:</span><span class="nm">%s</span>'
            '<span class="sym">%s</span></span><span class="s">%s %s %d/%d</span>%s%s</a>'
            % (_css(status), mark, _url(lang, run["id"]), number, esc(run["name"]), _sym(status), _sym(status), esc(_state(t, status)),
               done, total, why, _progress(run)))


def _right(t, runs, selected_id, lang, reasons):
    numbered = _numbered(runs)
    count = lambda *statuses: sum(1 for r in runs if r["status"] in statuses)
    out = ['<aside class="rail" data-pane="right"><div class="tabs"><span class="tab is-on">%s</span>%s</div><h2>%s</h2><p class="muted">%s</p>%s'
           '<p class="tally"><span>▶ %d</span><span>! %d</span><span>✓ %d</span></p>'
           % (esc(t["tab_progress"]), _grey(t, "tab_chat"), esc(t["all_analyses"]), esc(t["yours_only"]), _grey(t, "search"),
              count("running"), count("failed", "lost"), count("succeeded"))]
    if not runs:
        out.append('<p class="muted">%s</p>' % esc(t["none_yet"]))
    for stage in ("running", "results"):
        mine = [(r, n) for r, n in numbered if stage_of(r["status"]) == stage]
        blocks = "".join(_item(t, r, n, selected_id, lang, reasons) for r, n in mine[:LIST_CAP])
        out.append('<details open class="group" data-stage="%s"><summary>%s</summary><div class="items">%s%s</div></details>'
                   % (stage, esc(t["group"] % (t["stage_" + stage], len(mine))), blocks if mine else '<p class="muted">—</p>', _more(t, len(mine))))
    out.append('<section class="group" data-stage="later"><p class="later">%s</p></section></aside>' % esc(t["later"]))
    return "".join(out)


def failed_ids_shown(runs):
    """The ids of the failed runs the page will show a reason for: the failed ones among the first LIST_CAP of the right column's
    first group, and the first LIST_CAP of the attention card (both in their order)."""
    numbered = _numbered(runs)
    group = [r for r, _ in numbered if stage_of(r["status"]) == "running"][:LIST_CAP]
    card = [r for r, _ in _attention(numbered)][:LIST_CAP]
    out = []
    for r in group + card:
        if r["status"] == "failed" and r["id"] not in out:
            out.append(r["id"])
    return out


def document(title, body, refresh=False, board=False, lang="zh"):
    """A whole page. Only the board asks for the meta refresh; a page that is not the board gets the narrow single column."""
    head = "<meta http-equiv=\"refresh\" content=\"%d\">" % REFRESH_SECONDS if refresh else ""
    wrapped = body if board else '<main class="narrow">%s</main>' % body
    return ("<!doctype html><html lang=\"%s\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">%s"
            "<title>%s</title><style>%s</style></head><body>%s</body></html>"
            % ("en" if lang == "en" else "zh-Hant", head, esc(title), STYLE, wrapped))


def _frame(name, csrf, runs, lang, reasons, here, middle, run=None, stage=None, path="/", refresh=False):
    lang = pick_lang(lang)
    t = STRINGS[lang]
    body = '%s<div class="wb">%s%s%s</div>' % (_mast(t, name, lang, run, stage, path), _left(t, runs, run, lang, csrf, here), middle(t, lang),
                                                _right(t, runs, run, lang, reasons))
    return document(t["title"], body, refresh=refresh, board=True, lang=lang)


def render_board(name, csrf, runs, selected=None, stage_param=None, lang="zh", reasons=None):
    """GET /: the page of a logged-in user. `runs` are newest first (as list_runs gives them); `selected` is the detail of one run, or
    None for the Now page; `reasons` maps the id of a failed run to its failure_reason (read by the caller, with the caller's rights)."""
    run_id = selected["id"] if selected is not None else None
    stage = pick_stage(stage_param, None) if selected is not None else None
    middle = (lambda t, lang_: _run_page(t, selected, stage_param, lang_)) if selected is not None \
        else (lambda t, lang_: _now_page(t, runs, lang_, reasons))
    return _frame(name, csrf, runs, lang, reasons, "now" if selected is None else "run", middle, run_id, stage, refresh=True)


def render_settings(name, csrf, runs, lang="zh", reasons=None):
    """GET /settings: the same frame, and a middle column of sections that are all still to come."""
    return _frame(name, csrf, runs, lang, reasons, "settings", lambda t, lang_: _settings_page(t), path="/settings")


def render_not_found(name, lang="zh"):
    """The 404 of the board: the same bytes for a missing run and for somebody else's, and it never repeats the requested id."""
    lang = pick_lang(lang)
    t = STRINGS[lang]
    body = ('%s<main class="main"><h1>%s</h1><p>%s</p><p><a href="%s">%s</a></p></main>'
            % (_mast(t, name, lang, None, None), esc(t["not_found_title"]), esc(t["not_found_body"]), _url(lang), esc(t["back"])))
    return document(t["title"], body, board=True, lang=lang)
