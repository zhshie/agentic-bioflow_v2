# Nothing existing: the middle column of GET /settings (settings-page, lane L8); the page, its checklist rules and its words are ours.
"""The middle column of the settings page: what the person's own setup looks like, read only.

It draws what web.py hands it (the answers of the read actions list_compute_envs, list_agents and list_my_tokens) and reads nothing
itself: no database, no network, no write. Every section that is not built yet stays greyed "coming later".
"""
import re

from . import web_board
from .web_board import esc

DONE, MISSING, LATER = "done", "missing", "later"
# compute environment status -> how the table shows it (settings-page ledger, ruling 8). Anything not listed is "unchecked", never ok.
CE_OK = {"available"}
CE_BAD = {"invalid", "unsupported", "disabled"}

STRINGS = {
    "zh": {
        "setup": "使用前檢查", "s_done": "完成", "s_missing": "未完成", "s_later": "之後開放",
        "st_account": "帳號", "st_token": "存取權杖", "st_ce": "運算環境", "st_ai": "AI 金鑰",
        "token_hint": "在終端機用 abf-platform token new 建立。",
        "ce_none": "沒有運算環境。", "ce_down": "主要運算環境無法使用：", "agent_down": "站台代理離線。",
        "th_name": "名稱", "th_platform": "平台", "th_status": "狀態", "th_agent": "站台代理", "th_pipes": "已登記管線", "th_used": "上次使用時間",
        "primary": "主要", "ce_ok": "可用", "ce_bad": "無法使用", "ce_unk": "未檢查", "online": "在線", "offline": "離線",
        "ce_later": "新增或修改運算環境", "no_ce": "沒有運算環境。",
        "th_label": "標籤", "th_created": "建立時間", "tok_ok": "有效", "tok_revoked": "已撤銷", "no_tok": "沒有存取權杖。",
        "tok_later": "建立或撤銷權杖", "key_note": "金鑰只存在你的瀏覽器，不會送到平台。",
    },
    "en": {
        "setup": "Before you start", "s_done": "Done", "s_missing": "Missing", "s_later": "Coming later",
        "st_account": "Account", "st_token": "Access token", "st_ce": "Compute environment", "st_ai": "AI key",
        "token_hint": "Create one in a terminal with abf-platform token new.",
        "ce_none": "No compute environment.", "ce_down": "The primary compute environment is unavailable: ", "agent_down": "The agent on the site is offline.",
        "th_name": "Name", "th_platform": "Platform", "th_status": "Status", "th_agent": "Site agent", "th_pipes": "Registered pipelines",
        "th_used": "Last used",
        "primary": "Primary", "ce_ok": "Available", "ce_bad": "Unavailable", "ce_unk": "Not checked", "online": "Online", "offline": "Offline",
        "ce_later": "Adding or changing compute environments", "no_ce": "No compute environment.",
        "th_label": "Label", "th_created": "Created", "tok_ok": "Valid", "tok_revoked": "Revoked", "no_tok": "No access tokens.",
        "tok_later": "Creating or revoking tokens", "key_note": "The key stays in your browser and is never sent to the platform.",
    },
}
SYMBOL = {DONE: "✓", MISSING: "✗", LATER: "—"}
CLASS = {DONE: "chip state-succeeded", MISSING: "chip state-failed", LATER: "chip muted"}


def _chip(state, text):
    """One status: symbol, word and class together (never the colour alone)."""
    return '<span class="%s"><span aria-hidden="true">%s</span> %s</span>' % (CLASS[state], SYMBOL[state], esc(text))


def _when_iso(iso):
    return web_board._time(re.sub(r"\.\d+Z$", "Z", str(iso))) if iso else "—"


def _when_epoch(epoch):
    return web_board.taipei_time(epoch) or "—"


def _message(text, lang):
    """The message of an environment as one plain line, without its closing full stop."""
    return web_board.plain_reason(text, lang).rstrip("。.")


def _ce_kind(env):
    if env.get("status") in CE_OK:
        return "ok"
    return "bad" if env.get("status") in CE_BAD else "unk"


def _primary(envs):
    for env in envs:
        if env.get("primary"):
            return env
    return envs[0] if envs else None


def check_steps(t, lang, envs, agents, tokens):
    """The four lines of the checklist as (label, state, note)."""
    live = any(not tok.get("revoked_at") for tok in tokens)
    env = _primary(envs)
    if env is None:
        ce = (MISSING, t["ce_none"])
    elif _ce_kind(env) != "ok":
        ce = (MISSING, t["ce_down"] + _message(env.get("message"), lang))
    elif not any(a.get("name") == env.get("agent") and a.get("status") == "online" for a in agents):
        ce = (MISSING, t["agent_down"])
    else:
        ce = (DONE, "")
    return [(t["st_account"], DONE, ""), (t["st_token"], DONE if live else MISSING, "" if live else t["token_hint"]),
            (t["st_ce"],) + ce, (t["st_ai"], LATER, "")]


def _setup(t, lang, envs, agents, tokens):
    items = "".join("<li><span>%s</span> %s%s</li>" % (esc(label), _chip(state, t["s_" + state]), (' <span class="muted">%s</span>' % esc(note)) if note else "")
                    for label, state, note in check_steps(t, lang, envs, agents, tokens))
    return '<section class="card sec" id="setup"><h2>%s</h2><ol>%s</ol></section>' % (esc(t["setup"]), items)


def _grey_line(t, key):
    return '<p class="off">%s %s</p>' % (esc(t[key]), web_board._later(t))


def _ce_row(t, lang, env, agents):
    kind = _ce_kind(env)
    if kind == "ok":
        status = _chip(DONE, t["ce_ok"])
    elif kind == "bad":
        status = "%s %s" % (_chip(MISSING, t["ce_bad"]), esc(_message(env.get("message"), lang)))
    else:
        status = _chip(LATER, t["ce_unk"])
    agent = next((a for a in agents if a.get("name") == env.get("agent")), None)
    if agent is None:
        who = esc(env.get("agent") or "—")
        if env.get("agent"):
            who += " " + _chip(MISSING, t["offline"])
    else:
        up = agent.get("status") == "online"
        who = "%s %s <span class=\"muted\">%s</span>" % (esc(agent["name"]), _chip(DONE if up else MISSING, t["online" if up else "offline"]),
                                                         esc(_when_iso(agent.get("last_contact_at"))))
    pipes = (env.get("config") or {}).get("sitePipelines")
    pipes = "<br>".join(esc("%s %s" % (p.get("pipeline", ""), p.get("revision", ""))) for p in pipes if isinstance(p, dict)) if pipes else ""
    name = esc(env.get("name")) + (' <span class="badge state-running">%s</span>' % esc(t["primary"]) if env.get("primary") else "")
    return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (name, esc(env.get("platform") or "—"), status, who, pipes or "—", esc(_when_iso(env.get("lastUsed")))))


def _compute(t, lang, envs, agents):
    if not envs:
        body = '<p class="muted">%s</p>' % esc(t["no_ce"])
    else:
        head = "".join("<th>%s</th>" % esc(t[k]) for k in ("th_name", "th_platform", "th_status", "th_agent", "th_pipes", "th_used"))
        body = '<table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (head, "".join(_ce_row(t, lang, e, agents) for e in envs))
    return '<section class="card sec"><h2>%s</h2>%s%s</section>' % (esc(t["set_ce"]), body, _grey_line(t, "ce_later"))


def _credentials(t, tokens):
    if not tokens:
        body = '<p class="muted">%s</p>' % esc(t["no_tok"])
    else:
        rows = []
        for tok in tokens:
            if tok.get("revoked_at"):
                status = "%s %s" % (_chip(MISSING, t["tok_revoked"]), esc(_when_epoch(tok["revoked_at"])))
            else:
                status = _chip(DONE, t["tok_ok"])
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(tok.get("label") or "—"), esc(_when_epoch(tok.get("created_at"))), status))
        head = "".join("<th>%s</th>" % esc(t[k]) for k in ("th_label", "th_created", "th_status"))
        body = '<table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (head, "".join(rows))
    return '<section class="card sec"><h2>%s</h2>%s%s</section>' % (esc(t["set_cred"]), body, _grey_line(t, "tok_later"))


def _keys(t):
    return ('<section class="card sec"><h2>%s</h2><ul><li>%s</li></ul><p class="muted">%s</p></section>'
            % (esc(t["set_keys"]), web_board._grey(t, "set_ai_key"), esc(t["key_note"])))


def _rest(t):
    out = ""
    for head, entries in web_board.SETTINGS[3:]:      # personal, operator panel, roles: as before, still to come
        inner = "<ul>%s</ul>" % "".join("<li>%s</li>" % web_board._grey(t, e) for e in entries) if entries else "<p>%s</p>" % web_board._later(t)
        out += '<section class="card sec"><h2>%s</h2>%s</section>' % (esc(t[head]), inner)
    return out


def render_middle(lang, envs, agents, tokens):
    """The middle column. `envs`, `agents` and `tokens` are the lists inside the answers of list_compute_envs, list_agents and list_my_tokens."""
    lang = web_board.pick_lang(lang)
    t = dict(web_board.STRINGS[lang])
    t.update(STRINGS[lang])
    return ('<main class="main" data-pane="middle"><h1>%s</h1>%s%s%s%s%s</main>'
            % (esc(t["settings"]), _setup(t, lang, envs, agents, tokens), _compute(t, lang, envs, agents), _credentials(t, tokens),
               _keys(t), _rest(t)))


def render(name, csrf, runs, lang, envs, agents, tokens):
    """GET /settings: the same frame as the board, this middle column. The left and right columns stay as web_board draws them."""
    return web_board._frame(name, csrf, runs, lang, "settings", lambda t, lang_: render_middle(lang, envs, agents, tokens),
                            lambda t, lang_: web_board._right(t, None), path="/settings")
