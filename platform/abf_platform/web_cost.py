# Nothing existing: the HTML of the cost page (DESIGN.md screen 11); like web_board.py it is a pure function from the answer of the my_usage action to a string, with the page's own words in one table.
"""The cost page GET /usage (cost-page-by-environment, web design v2 screen 11), as pure functions from dicts to strings.

No database, file or network is touched here, and nothing but `web_board` (the frame, the escaping, the times) is imported: `web.py` asks the
`my_usage` action for the logged-in caller and hands the answer in. Two cards (the cloud cap and what is left of it), the fixed line that says
nothing is added across environments, and one expandable row per compute environment: the unit follows the environment (SU or US dollars), and
inside it one line per analysis with a status of two kinds only: running, or an estimate whose bill has not come. A figure that is not known is
shown as a dash and never as 0.00. No script, no `style=`; the classes and tokens are those of web_board's one stylesheet.
"""
import datetime
import re

from . import web_board

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])\Z")
CAP_KEY = "cap_" + "usd"        # the cap is read from the answer by this key only; the word itself stays out of every file but the store's

STRINGS = {
    "zh": {
        "title": "費用", "empty_month": "— %s 尚無分析", "card_cap": "雲端上限", "card_left": "雲端剩餘",
        "unset": "未設定", "set_by_admin": "由管理者設定", "unknown_runs": "另有 %d 個分析無法計算",
        "action": "待處理：本月雲端額度已用盡",
        "note": "各運算環境用各自的單位（SU 或美元）顯示，不互相換算、不加總。數字依執行紀錄估算，略低於實際帳單。",
        "th_name": "分析名稱", "th_started": "開始時間", "th_usage": "用量", "th_state": "狀態",
        "state_running": "執行中",
        "empty": "— 本月尚無分析", "bad_month": "月份格式不符，已顯示本月。", "prev": "← 上一月", "next": "下一月 →",
        "no_reason": "無法計算", "analyses": "共 %d 個分析", "no_env": "未記錄的運算環境",
        "wait": "分析結束後才能計算", "not_sent": "沒有送出紀錄，無法判斷運算環境", "not_stored": "紀錄沒有保存每個步驟的用量",
        "usd_note": "SU 以 %s 匯率概算為美元，並非帳單金額。",
    },
    "en": {
        "title": "Cost", "empty_month": "— No analyses in %s", "card_cap": "Cloud cap",
        "card_left": "Cloud remaining", "unset": "Not set", "set_by_admin": "Set by the administrator",
        "unknown_runs": "%d more analyses could not be priced", "unknown_run": "1 more analysis could not be priced",
        "action": "Action needed: this month's cloud cap is used up",
        "note": "Each compute environment is shown in its own unit (SU or US dollars); nothing is converted or added across environments. "
                "Figures are estimates from the run records and a little below the actual bill.",
        "th_name": "Analysis", "th_started": "Started", "th_usage": "Usage", "th_state": "Status",
        "state_running": "Running",
        "empty": "— No analyses this month", "bad_month": "The month is not in the form YYYY-MM, so this month is shown.",
        "prev": "← Previous month", "next": "Next month →",
        "no_reason": "Not available", "analyses": "%d analyses", "analysis": "1 analysis", "no_env": "No environment on record",
        "wait": "Available once the analysis has ended", "not_sent": "No hand-off record, so the environment is not known",
        "not_stored": "The record keeps no usage for each step",
        "usd_note": "SU figures are converted to US dollars at the %s rate, roughly; this is not a bill.",
    },
}
for _lang in STRINGS:        # the shared words are the board's (the run page shows them too): one wording, in web_board
    STRINGS[_lang].update({w: web_board.STRINGS[_lang][w] for w in ("usd_about", "usd_under", "state_estimate")})
_ENGLISH_TAIL = re.compile(r"\(([^()]*)\)\s*$")
_CN_TAIL = re.compile(r"\s*\([^()]*\)\s*$")
_CJK = re.compile(r"[　-鿿＀-￯]")
_MAPPED = (("還沒結束", "wait"), ("沒有平台送出的紀錄", "not_sent"), ("沒有保存每個", "not_stored"))      # reasons the page words in its own plain way


def current_month(now):
    """'YYYY-MM' in Asia/Taipei of an epoch (seconds)."""
    return (datetime.datetime.fromtimestamp(float(now), datetime.timezone.utc) + web_board.TAIPEI).strftime("%Y-%m")


def pick_month(raw):
    """(month to ask for, whether the text given was bad): None asks for the current month; a missing month is not bad."""
    if raw is None or raw == "":
        return None, False
    return (raw, False) if MONTH.match(raw) else (None, True)


def shift(month, step):
    y, m = int(month[:4]), int(month[5:])
    n = y * 12 + (m - 1) + step
    return "%04d-%02d" % (n // 12, n % 12 + 1)


def empty_usage(month):
    """What the page shows when the index cannot be read: nothing used, nothing listed (an unreadable index is an empty month, not a 500)."""
    return {"month": month, "environments": [], "usd_rate_as_of": None,
            "cloud": {"used_usd": 0.0, "unknown_runs": 0, CAP_KEY: None, "remaining_usd": None, "currency": "USD"}}


def _reason(t, lang, reasons):
    """The first reason a figure is not known, in the page's language: the reasons are written 'Chinese (English)'."""
    if not reasons:
        return t["no_reason"]
    text = str(reasons[0])
    for marker, key in _MAPPED:
        if marker in text:
            return t[key]
    if text.startswith("task ") and ": " in text:        # the task's name is the program's word, not the person's: only the reason stays
        text = text.split(": ", 1)[1]
    text = text.split("; ")[0]
    if lang == "en":
        tail = _ENGLISH_TAIL.search(text)
        return tail.group(1) if tail and not _CJK.search(tail.group(1)) else t["no_reason"]
    return _CN_TAIL.sub("", text).strip() or t["no_reason"]


def _usd(value):
    return "—" if value is None else "US$ %.2f" % value


def _small(text, symbol=""):
    mark = '<span class="sym">%s</span> ' % web_board.esc(symbol) if symbol else ""
    return "<small>%s%s</small>" % (mark, web_board.esc(text)) if text else ""


def _card(title, value, small="", extra_class=""):
    return ('<div class="scard%s"><h2 class="ct">%s</h2><p class="cv">%s</p>%s</div>'
            % (extra_class, web_board.esc(title), web_board.esc(value), small))


def _cards(t, data, this_month):
    cloud = data["cloud"]
    cap = cloud[CAP_KEY]
    left = cloud["remaining_usd"]
    used_up = left is not None and left <= 0 and data["month"] == this_month        # the action is this month's to do
    cards = [
        _card(t["card_cap"], t["unset"] if cap is None else _usd(cap), _small(t["set_by_admin"] if cap is None else "")),
        _card(t["card_left"], _usd(left), _small(t["action"] if used_up else "", "⚠"), " state-failed" if used_up else ""),
    ]
    return '<section class="sumcards">%s</section>' % "".join(cards)


def _amount(t, unit, value, usd):
    return web_board.usage_text(t, unit, value, usd)


def _row(t, lang, unit, a, ids):
    run_id = ids.get(a["name"])
    name = web_board.esc(a["name"])
    if run_id:
        name = '<a href="%s">%s</a>' % (web_board._url(lang, run_id), name)
    state = ('<span class="state-running"><span class="sq"></span> %s</span>' % web_board.esc(t["state_running"])
             if a["state"] == "running" else web_board.esc(t["state_estimate"]))
    return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (name, web_board.esc(web_board._time(a["started_at"])), web_board.esc(_amount(t, unit, a["value"], a.get("usd_approx"))), state))


def _env_block(t, lang, env, ids, is_open):
    unit = env["unit"]
    count = env["analyses_count"]
    count_text = (t["analysis"] if count == 1 and lang == "en" else t["analyses"] % count)
    unknown = env["unknown_runs"]
    unknown_text = ""
    if env["total"] is not None and unknown > 0:
        unknown_text = t["unknown_run"] if unknown == 1 and lang == "en" else t["unknown_runs"] % unknown
    elif env["total"] is None:
        unknown_text = _reason(t, lang, env["unknown_reasons"])
    bits = [web_board.esc(env["name"] or t["no_env"]), web_board.esc(env["kind"] or ""),
            "<strong>%s</strong>" % web_board.esc(_amount(t, unit, env["total"], env.get("usd_approx"))),
            _small(count_text), _small(unknown_text)]
    head = "".join("<th>%s</th>" % web_board.esc(t[k]) for k in ("th_name", "th_started", "th_usage", "th_state"))
    rows = "".join(_row(t, lang, unit, a, ids) for a in env["analyses"])
    return ('<details class="pgroup env"%s><summary>%s</summary><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></details>'
            % (" open" if is_open else "", " ".join(b for b in bits if b), head, rows))


def _envs(t, lang, envs, ids, month, this_month):
    if not envs:
        return '<p class="muted">%s</p>' % web_board.esc(t["empty"] if month == this_month else t["empty_month"] % month)
    return '<div class="pgroups">%s</div>' % "".join(_env_block(t, lang, e, ids, len(envs) == 1) for e in envs)


def _month_link(lang, month, text):
    return '<a href="/usage?month=%s%s">%s</a>' % (month, "&amp;lang=en" if lang == "en" else "", web_board.esc(text))


def _middle(t, lang, data, ids, this_month, bad_month):
    month = data["month"]
    nav = [_month_link(lang, shift(month, -1), t["prev"])]
    if month < this_month:        # never a link to a month that has not begun
        nav.append(_month_link(lang, shift(month, 1), t["next"]))
    notice = '<div class="notice" role="alert"><p>%s</p></div>' % web_board.esc(t["bad_month"]) if bad_month else ""
    as_of = data.get("usd_rate_as_of")
    shows_su = any(e["unit"] == "SU" and e["usd_approx"] is not None for e in data["environments"])
    note = t["note"] + ("" if lang == "zh" else " ") + t["usd_note"] % as_of if as_of and shows_su else t["note"]
    return ('<main class="main" data-pane="middle"><h1>%s <small>%s</small></h1><p class="views">%s</p>%s%s<p class="muted">%s</p>%s</main>'
            % (web_board.esc(t["title"]), web_board.esc(month), "".join(nav), notice, _cards(t, data, this_month), web_board.esc(note),
               _envs(t, lang, data["environments"], ids, month, this_month)))


def render_usage(name, csrf, runs, data, lang="zh", now=0, bad_month=False):
    """GET /usage: the board's frame (masthead, my runs on the left, the empty right column) with the cost page in the middle. `runs` are the
    left column's runs (list_runs); `data` is the answer of my_usage; `now` is an epoch, to know which month is the last that has a link."""
    lang = web_board.pick_lang(lang)
    t = STRINGS[lang]
    ids = {r["name"]: r["id"] for r in runs}
    this_month = current_month(now)
    return web_board._frame(name, csrf, runs, lang, "usage", lambda t_, lang_: _middle(t, lang, data, ids, this_month, bad_month),
                            lambda t_, lang_: web_board._right(t_, None), path="/usage")
