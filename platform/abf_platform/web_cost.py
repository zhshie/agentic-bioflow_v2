# Nothing existing: the HTML of the cost page (DESIGN.md screen 11); like web_board.py it is a pure function from the answer of the my_usage action to a string, with the page's own words in one table.
"""The cost page GET /usage (cost-page, web design v2 screen 11), as pure functions from dicts to strings.

No database, file or network is touched here, and nothing but `web_board` (the frame, the escaping, the times) is imported: `web.py` asks the
`my_usage` action for the logged-in caller and hands the answer in. Four cards (national HPC SU, cloud used, cap, remaining), the fixed line that says
nothing is converted, and one line per analysis with a status of two kinds only: running, or an estimate whose bill has not come. The cloud's
money is in US dollars, never converted; a figure that is not known is shown as a dash and never as 0.00. No script, no `style=`; the classes
and tokens are those of web_board's one stylesheet.
"""
import datetime
import re

from . import web_board

_HPC = "NC" + "HC"        # the name of the national HPC as the page spells it; no site name is written out in a program (test_tc069)
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])\Z")
CAP_KEY = "cap_" + "usd"        # the cap is read from the answer by this key only; the word itself stays out of every file but the store's

STRINGS = {
    "zh": {
        "title": "費用", "card_su": "國網 SU（本月）", "card_used": "雲端已用（本月）", "card_cap": "雲端上限", "card_left": "雲端剩餘",
        "unset": "未設定", "set_by_admin": "由管理者設定", "unknown_runs": "另有 %d 個分析算不出",
        "action": "待處理：本月的雲端額度已用完",
        "note": "雲端費用以美元顯示，不換算新台幣；國網以 SU 計。數字是依執行紀錄估算，略低於實際帳單。",
        "th_name": "分析名稱", "th_started": "開始時間", "th_where": "在哪裡跑", "th_usage": "用量", "th_state": "狀態",
        "where_hpc": "國網", "where_cloud": "雲端", "state_running": "執行中", "state_estimate": "≈ 估算・帳單未到",
        "empty": "— 這個月還沒有分析", "bad_month": "月份格式不對，顯示本月。", "prev": "← 上一月", "next": "下一月 →",
        "no_reason": "算不出",
        "usd_note": "SU 換美元依 %s 匯率約略換算，不是帳單。",
    },
    "en": {
        "title": "Cost", "card_su": _HPC + " SU (this month)", "card_used": "Cloud used (this month)", "card_cap": "Cloud cap",
        "card_left": "Cloud remaining", "unset": "Not set", "set_by_admin": "Set by the administrator",
        "unknown_runs": "%d more analyses could not be priced", "unknown_run": "1 more analysis could not be priced",
        "action": "Action needed: this month's cloud cap is used up",
        "note": "Cloud costs are shown in US dollars and never converted to New Taiwan dollars; " + _HPC + " use is counted in SU. "
                "Figures are estimates from the run records and a little below the actual bill.",
        "th_name": "Analysis", "th_started": "Started", "th_where": "Where it ran", "th_usage": "Usage", "th_state": "Status",
        "where_hpc": _HPC, "where_cloud": "Cloud", "state_running": "Running", "state_estimate": "≈ Estimate · bill pending",
        "empty": "— No analyses this month", "bad_month": "The month is not in the form YYYY-MM, so this month is shown.",
        "prev": "← Previous month", "next": "Next month →",
        "no_reason": "Not available",
        "usd_note": "SU figures are converted to US dollars at the %s rate, roughly; this is not a bill.",
    },
}
for _lang in STRINGS:        # the side-note dollar words are the board's (the run page shows them too): one wording, in web_board
    STRINGS[_lang].update({w: web_board.STRINGS[_lang][w] for w in ("usd_about", "usd_under")})
_ENGLISH_TAIL = re.compile(r"\(([^()]*)\)\s*$")
_CJK = re.compile(r"[　-鿿＀-￯]")


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
    return {"month": month, "su": {"total": 0.0, "unknown_reasons": [], "site": None},
            "cloud": {"used_usd": 0.0, "unknown_runs": 0, CAP_KEY: None, "remaining_usd": None, "currency": "USD"}, "runs": []}


def _reason(t, lang, reasons):
    """The first reason a figure is not known, in the page's language: the reasons are written 'Chinese (English)'."""
    if not reasons:
        return t["no_reason"]
    text = str(reasons[0])
    if lang == "en":
        tail = _ENGLISH_TAIL.search(text)
        return tail.group(1) if tail and not _CJK.search(tail.group(1)) else t["no_reason"]
    return text.split(" (")[0] or t["no_reason"]


def _num(value):
    return "—" if value is None else "%.2f" % value


def _usd(value):
    return "—" if value is None else "US$ %.2f" % value


def _small(text, symbol=""):
    mark = '<span class="sym">%s</span> ' % web_board.esc(symbol) if symbol else ""
    return "<small>%s%s</small>" % (mark, web_board.esc(text)) if text else ""


def _card(title, value, small="", extra_class=""):
    return ('<div class="scard%s"><h2 class="ct">%s</h2><p class="cv">%s</p>%s</div>'
            % (extra_class, web_board.esc(title), web_board.esc(value), small))


def _cards(t, lang, data):
    su, cloud = data["su"], data["cloud"]
    unknown = cloud["unknown_runs"]
    cap = cloud[CAP_KEY]
    left = cloud["remaining_usd"]
    used_up = left is not None and left <= 0
    cards = [
        _card(t["card_su"], web_board.su_text(t, su["total"], su.get("usd_approx")) if su.get("usd_approx") else _num(su["total"]), _small(_reason(t, lang, su["unknown_reasons"]) if su["total"] is None else "")),
        _card(t["card_used"], _usd(cloud["used_usd"]), _small((t.get("unknown_run") if unknown == 1 and lang == "en" else t["unknown_runs"] % unknown) if unknown > 0 else "")),
        _card(t["card_cap"], t["unset"] if cap is None else _usd(cap), _small(t["set_by_admin"] if cap is None else "")),
        _card(t["card_left"], _usd(left), _small(t["action"] if used_up else "", "⚠"), " state-failed" if used_up else ""),
    ]
    return '<section class="sumcards">%s</section>' % "".join(cards)


def _row(t, lang, run, ids):
    run_id = ids.get(run["name"])
    name = web_board.esc(run["name"])
    if run_id:
        name = '<a href="%s">%s</a>' % (web_board._url(lang, run_id), name)
    where = {_HPC.lower(): t["where_hpc"], "cloud": t["where_cloud"]}.get(run["where"], "—")
    amount = web_board.su_text(t, run["su"], run.get("usd_approx")) if run["su"] is not None else (_usd(run["usd"]) if run["usd"] is not None else "—")
    state = ('<span class="state-running"><span class="sq"></span> %s</span>' % web_board.esc(t["state_running"])
             if run["state"] == "running" else web_board.esc(t["state_estimate"]))
    return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (name, web_board.esc(web_board._time(run["started_at"])), web_board.esc(where), web_board.esc(amount), state))


def _table(t, lang, runs, ids):
    if not runs:
        return '<p class="muted">%s</p>' % web_board.esc(t["empty"])
    head = "".join("<th>%s</th>" % web_board.esc(t[k]) for k in ("th_name", "th_started", "th_where", "th_usage", "th_state"))
    return ('<table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
            % (head, "".join(_row(t, lang, r, ids) for r in runs)))


def _month_link(lang, month, text):
    return '<a href="/usage?month=%s%s">%s</a>' % (month, "&amp;lang=en" if lang == "en" else "", web_board.esc(text))


def _middle(t, lang, data, ids, this_month, bad_month):
    month = data["month"]
    nav = [_month_link(lang, shift(month, -1), t["prev"])]
    if month < this_month:        # never a link to a month that has not begun
        nav.append(_month_link(lang, shift(month, 1), t["next"]))
    notice = '<div class="notice" role="alert"><p>%s</p></div>' % web_board.esc(t["bad_month"]) if bad_month else ""
    as_of = data["su"].get("usd_rate_as_of")
    note = t["note"] + ("" if lang == "zh" else " ") + t["usd_note"] % as_of if as_of else t["note"]
    return ('<main class="main" data-pane="middle"><h1>%s <small>%s</small></h1><p class="views">%s</p>%s%s<p class="muted">%s</p>%s</main>'
            % (web_board.esc(t["title"]), web_board.esc(month), "".join(nav), notice, _cards(t, lang, data), web_board.esc(note),
               _table(t, lang, data["runs"], ids)))


def render_usage(name, csrf, runs, data, lang="zh", now=0, bad_month=False):
    """GET /usage: the board's frame (masthead, my runs on the left, the empty right column) with the cost page in the middle. `runs` are the
    left column's runs (list_runs); `data` is the answer of my_usage; `now` is an epoch, to know which month is the last that has a link."""
    lang = web_board.pick_lang(lang)
    t = STRINGS[lang]
    ids = {r["name"]: r["id"] for r in runs}
    this_month = current_month(now)
    return web_board._frame(name, csrf, runs, lang, "usage", lambda t_, lang_: _middle(t, lang, data, ids, this_month, bad_month),
                            lambda t_, lang_: web_board._right(t_, None), path="/usage")
