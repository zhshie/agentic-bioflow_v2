# Nothing existing: the middle column of GET /settings (settings-page, lane L8); the page, its checklist rules and its words are ours.
"""The middle column of the settings page: what the person's own setup looks like, and the form that registers or removes a pipeline version.

It draws what web.py hands it (the answer of the read action list_compute_envs) and reads nothing
itself: no database, no network, no write. The one thing a person can do here is register or remove a pipeline version on their own
compute environment (settings-register-pipeline): the forms only send to web.py, which asks the action layer. Every section that is not built
yet stays greyed "coming later".
"""
import hashlib
import re

from . import web_board, web_launch
from .web_board import esc

DONE, MISSING, LATER, GONE, FAIL = "done", "missing", "later", "gone", "fail"
# compute environment status -> how the table shows it (settings-page ledger, ruling 8). Anything not listed is "unchecked", never ok.
CE_OK = {"available"}
CE_BAD = {"invalid", "unsupported", "disabled"}

STRINGS = {
    "zh": {
        "setup": "使用前檢查", "s_done": "完成", "s_missing": "未完成", "s_later": "之後開放",
        "st_account": "帳號", "st_token": "存取權杖", "st_ce": "運算環境", "st_ai": "AI 金鑰",
        "token_hint": "在終端機用 abf-platform token new 建立。", "check_cmd": "請用指令確認",
        "ce_none": "沒有運算環境。", "ce_down": "主要運算環境無法使用：",
        "th_name": "名稱", "th_platform": "平台", "th_status": "狀態", "th_agent": "站台代理", "th_pipes": "已登記管線", "th_used": "上次使用時間",
        "primary": "主要", "ce_ok": "可用", "ce_bad": "無法使用", "ce_unk": "未檢查", 
        "ce_later": "新增或修改運算環境", "no_ce": "沒有運算環境。",
        "tok_later": "建立或撤銷權杖", "key_note": "金鑰只存在你的瀏覽器，不會送到平台。",
        "pf_l_pipeline": "管線（例 nf-core/ampliseq）", "pf_l_revision": "版本（例 2.18.0）",
        "pf_l_module": "模組名稱（站台 module load 使用的名稱，例 biology/nf-core-ampliseq/2.18.0）",
        "pf_l_home": "管線資料夾變數（模組設定的環境變數名稱，例 NFCORE_AMPLISEQ_HOME）",
        "pf_s_pipeline": "管線", "pf_s_revision": "版本", "pf_s_module": "模組名稱", "pf_s_home": "管線資料夾變數",
        "pf_reg": "登記", "pf_remove": "移除", "pf_confirm": "確認", "pf_back": "返回", "pf_reg_head": "登記管線",
        "pf_empty": "此環境目前未登記管線：送出時直接取用 nf-core 官方版本。登記第一筆後，只能送出已登記的管線版本。",
        "pf_fail": "未能完成：",
        "pf_required": "%s為必填。",
        "pf_e_pipeline": "管線名稱格式不正確：須為 nf-core/<名稱>，名稱僅限小寫字母、數字與連字號。",
        "pf_e_revision": "版本格式不正確：須為發行版本（例 2.18.0）或 40 字元提交碼，不接受分支名稱。",
        "pf_e_module": "模組名稱格式不正確：僅限英文字母、數字與 _ . / + -，且不得含 ..。",
        "pf_e_home": "管線資料夾變數格式不正確：僅限大寫字母、數字與底線，且不得以數字開頭。",
        "pf_n_added_queued": "已登記，並已排入使用前檢查。",
        "pf_n_added_no_agent": "已登記。站台代理目前離線，使用前檢查將於代理上線後執行。",
        "pf_n_added_not_checkable": "已登記。此運算環境類型不執行使用前檢查。",
        "pf_n_added_check_refused": "已登記。使用前檢查未能排入，請稍後於設定頁重新登記以再次檢查。",
        "pf_n_removed": "已移除。", "pf_n_gone": "此管線版本已不在清單中。",
        "pf_c_add": "確認新增管線版本", "pf_c_remove": "確認移除管線版本",
        "pf_c_action": "動作", "pf_c_env": "運算環境", "pf_op_add": "新增", "pf_op_remove": "移除",
        "pf_expired_title": "表單已失效", "pf_expired": "表單的記號不正確或已失效，什麼都沒有改。請重新整理頁面後再試。",
        "pf_foreign_title": "來源不符", "pf_foreign": "表單不是從本頁送出的，什麼都沒有改。請重新整理頁面後再試。",
    },
    "en": {
        "setup": "Before you start", "s_done": "Done", "s_missing": "Missing", "s_later": "Coming later",
        "st_account": "Account", "st_token": "Access token", "st_ce": "Compute environment", "st_ai": "AI key",
        "token_hint": "Create one in a terminal with abf-platform token new.", "check_cmd": "Check with the command",
        "ce_none": "No compute environment.", "ce_down": "The primary compute environment is unavailable: ",
        "th_name": "Name", "th_platform": "Platform", "th_status": "Status", "th_agent": "Site agent", "th_pipes": "Registered pipelines",
        "th_used": "Last used",
        "primary": "Primary", "ce_ok": "Available", "ce_bad": "Unavailable", "ce_unk": "Not checked", 
        "ce_later": "Adding or changing compute environments", "no_ce": "No compute environment.",
        "tok_later": "Creating or revoking tokens", "key_note": "The key stays in your browser and is never sent to the platform.",
        "pf_l_pipeline": "Pipeline (e.g. nf-core/ampliseq)", "pf_l_revision": "Version (e.g. 2.18.0)",
        "pf_l_module": "Module name (the name used by module load on the site, e.g. biology/nf-core-ampliseq/2.18.0)",
        "pf_l_home": "Pipeline folder variable (the environment variable the module sets, e.g. NFCORE_AMPLISEQ_HOME)",
        "pf_s_pipeline": "Pipeline", "pf_s_revision": "Version", "pf_s_module": "Module name", "pf_s_home": "Pipeline folder variable",
        "pf_reg": "Register", "pf_remove": "Remove", "pf_confirm": "Confirm", "pf_back": "Back", "pf_reg_head": "Register a pipeline",
        "pf_empty": "No pipelines are registered here: runs use the nf-core release directly. "
                    "Once you register one, only registered pipeline versions can be run here.",
        "pf_fail": "Not completed: ",
        "pf_required": "%s is required.",
        "pf_e_pipeline": "The pipeline name is not valid: it must be nf-core/<name>, and the name may use lower-case letters, digits and hyphens only.",
        "pf_e_revision": "The version is not valid: it must be a release (e.g. 2.18.0) or a 40-character commit id; branch names are not accepted.",
        "pf_e_module": "The module name is not valid: letters, digits and _ . / + - only, and no ..",
        "pf_e_home": "The pipeline folder variable is not valid: capital letters, digits and underscores only, and it must not start with a digit.",
        "pf_n_added_queued": "Registered. A pre-use check has been queued.",
        "pf_n_added_no_agent": "Registered. The site "      # split in two pieces on purpose: test_scope keeps the words of the site side out of one line of the platform's source
                               "agent is offline; the pre-use check will run when it connects.",
        "pf_n_added_not_checkable": "Registered. This type of compute environment has no pre-use check.",
        "pf_n_added_check_refused": "Registered. The pre-use check could not be queued; register it again later on the Settings page to retry.",
        "pf_n_removed": "Removed.", "pf_n_gone": "This pipeline version is no longer registered.",
        "pf_c_add": "Confirm adding the pipeline version", "pf_c_remove": "Confirm removing the pipeline version",
        "pf_c_action": "Action", "pf_c_env": "Compute environment", "pf_op_add": "Add", "pf_op_remove": "Remove",
        "pf_expired_title": "Form expired", "pf_expired": "The form token is wrong or has expired; nothing was changed. Reload the page and try again.",
        "pf_foreign_title": "Wrong origin", "pf_foreign": "The form was not sent from this page; nothing was changed. Reload the page and try again.",
    },
}
SYMBOL = {DONE: "✓", MISSING: "✗", LATER: "—", GONE: "○", FAIL: "✕"}
CLASS = {DONE: "chip state-succeeded", MISSING: "chip state-failed", LATER: "chip muted", GONE: "chip muted", FAIL: "chip state-failed"}
NOTICES = ("added_queued", "added_no_agent", "added_not_checkable", "added_check_refused", "removed", "gone")      # the only values ?notice= may carry
FIELDS = ("pipeline", "revision", "module", "home")


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


def check_steps(t, lang, envs):
    """The four lines of the checklist as (label, state, note, chip text). Item 3 reads only the primary environment (else the first)."""
    env = _primary(envs)
    if env is None:
        ce = (MISSING, t["ce_none"])
    elif _ce_kind(env) != "ok":
        ce = (MISSING, t["ce_down"] + _message(env.get("message"), lang))
    else:
        ce = (DONE, "")
    return [(t["st_account"], DONE, "", t["s_done"]), (t["st_token"], LATER, t["token_hint"], t["check_cmd"]),
            (t["st_ce"],) + ce + (t["s_" + ce[0]],), (t["st_ai"], LATER, "", t["s_later"])]


def _setup(t, lang, envs):
    items = "".join("<li><span>%s</span> %s%s</li>" % (esc(label), _chip(state, text), (' <span class="muted">%s</span>' % esc(note)) if note else "")
                    for label, state, note, text in check_steps(t, lang, envs))
    return '<section class="card sec" id="setup"><h2>%s</h2><ol>%s</ol></section>' % (esc(t["setup"]), items)


def _grey_line(t, key):
    return '<p class="off">%s %s</p>' % (esc(t[key]), web_board._later(t))


def _ce_row(t, lang, env):
    kind = _ce_kind(env)
    if kind == "ok":
        status = _chip(DONE, t["ce_ok"])
    elif kind == "bad":
        status = "%s %s" % (_chip(MISSING, t["ce_bad"]), esc(_message(env.get("message"), lang)))
    else:
        status = _chip(LATER, t["ce_unk"])
    who = esc(env.get("agent") or "—")
    pipes = (env.get("config") or {}).get("sitePipelines")
    pipes = "<br>".join(esc("%s %s" % (p.get("pipeline", ""), p.get("revision", ""))) for p in pipes if isinstance(p, dict)) if pipes else ""
    name = esc(env.get("name")) + (' <span class="badge state-running">%s</span>' % esc(t["primary"]) if env.get("primary") else "")
    return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (name, esc(env.get("platform") or "—"), status, who, pipes or "—", esc(_when_iso(env.get("lastUsed")))))


def _hidden(pairs):
    return "".join('<input type="hidden" name="%s" value="%s">' % (esc(k), esc(v)) for k, v in pairs)


def _lang_field(lang):
    return [("lang", "en")] if lang == "en" else []


def _flash(t, flash, where):
    """The one sentence of a notice or a failure, with its symbol: `where` is the environment row it sits above (None: the top of the page)."""
    if not flash or flash.get("ce") != where:
        return ""
    if flash["kind"] == "fail":
        return '<p class="bad">%s</p>' % _chip(FAIL, flash["text"])
    state = GONE if flash["key"] == "gone" else DONE
    return '<p class="notice">%s</p>' % _chip(state, t["pf_n_" + flash["key"]])


def _remove_form(t, lang, pf_csrf, env, entry):
    pairs = [("op", "remove"), ("ce", env["name"])] + [(k, entry.get(k, "")) for k in FIELDS] + [("csrf", pf_csrf)] + _lang_field(lang)
    return ('<form class="act" method="post" action="/settings/pipelines">%s<button type="submit">%s</button></form>'
            % (_hidden(pairs), esc(t["pf_remove"])))


def _field_label(t, key):
    return '<span>%s %s</span>' % (esc(t["pf_l_" + key]), web_launch.star(t))


def _env_block(t, lang, env, pf_csrf, flash, given):
    """Under the table, one block per environment: its registered pipeline versions (each with a remove button), the sentence for an empty
    list, and the form that registers one. The block is the anchor `#ce-<name>`; a notice for it stands right above."""
    name = env["name"]
    listed = [p for p in ((env.get("config") or {}).get("sitePipelines") or []) if isinstance(p, dict)]
    items = "".join("<li>%s %s</li>" % (esc("%s %s" % (p.get("pipeline", ""), p.get("revision", ""))), _remove_form(t, lang, pf_csrf, env, p))
                    for p in listed)
    body = ("<ul>%s</ul>" % items) if listed else '<p class="muted">%s</p>' % esc(t["pf_empty"])
    values = given if given else {}
    inputs = "".join('<label>%s<input name="%s" value="%s" required></label>' % (_field_label(t, k), k, esc(values.get(k, ""))) for k in FIELDS)
    form = ('<form class="lform" method="post" action="/settings/pipelines">%s%s<button type="submit">%s</button></form>'
            % (_hidden([("op", "add"), ("ce", name), ("csrf", pf_csrf)] + _lang_field(lang)), inputs, esc(t["pf_reg"])))
    return ('%s<div id="ce-%s"><h3>%s</h3><p class="muted">%s</p>%s<h4>%s</h4><p class="muted">%s</p>%s</div>'
            % (_flash(t, flash, name), esc(name), esc(name), esc(t["th_pipes"]), body, esc(t["pf_reg_head"]), esc(t["g_legend"]), form))


def _compute(t, lang, envs, pf_csrf=None, flash=None, given=None):
    if not envs:
        body = '<p class="muted">%s</p>' % esc(t["no_ce"])
    else:
        head = "".join("<th>%s</th>" % esc(t[k]) for k in ("th_name", "th_platform", "th_status", "th_agent", "th_pipes", "th_used"))
        body = '<table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (head, "".join(_ce_row(t, lang, e) for e in envs))
        if pf_csrf:
            body += "".join(_env_block(t, lang, e, pf_csrf, flash, (given or {}).get(e["name"])) for e in envs)
    return '<section class="card sec"><h2>%s</h2>%s%s</section>' % (esc(t["set_ce"]), body, _grey_line(t, "ce_later"))


def _credentials(t):
    return ('<section class="card sec"><h2>%s</h2><p class="muted">%s</p>%s</section>'
            % (esc(t["set_cred"]), esc(t["token_hint"]), _grey_line(t, "tok_later")))


def _keys(t):
    return ('<section class="card sec"><h2>%s</h2><ul><li>%s</li></ul><p class="muted">%s</p></section>'
            % (esc(t["set_keys"]), web_board._grey(t, "set_ai_key"), esc(t["key_note"])))


def _rest(t):
    out = ""
    for head, entries in web_board.SETTINGS[3:]:      # personal, operator panel, roles: as before, still to come
        inner = "<ul>%s</ul>" % "".join("<li>%s</li>" % web_board._grey(t, e) for e in entries) if entries else "<p>%s</p>" % web_board._later(t)
        out += '<section class="card sec"><h2>%s</h2>%s</section>' % (esc(t[head]), inner)
    return out


def words(lang):
    t = dict(web_board.STRINGS[web_board.pick_lang(lang)])
    t.update(STRINGS[web_board.pick_lang(lang)])
    return t


def make_flash(envs, kind, key=None, text=None, ce=None):
    """What to say above an environment row (or at the top of the page when `ce` is not one of the person's own environments).
    kind "notice" takes a key of NOTICES (anything else says nothing); kind "fail" takes the sentence."""
    where = ce if ce in {e.get("name") for e in envs} else None
    if kind == "notice":
        return {"kind": "notice", "key": key, "ce": where} if key in NOTICES else None
    return {"kind": "fail", "text": text, "ce": where}


def field_error(lang, field, value):
    """The sentence for a box that is empty or wrong, naming the box; None for a field that has no box."""
    t = words(lang)
    if field in FIELDS:
        return t["pf_required"] % t["pf_s_" + field] if not value else t["pf_e_" + field]
    return None


def render_middle(lang, envs, pf_csrf=None, flash=None, given=None):
    """The middle column. `envs` is the list inside the answer of list_compute_envs."""
    lang = web_board.pick_lang(lang)
    t = words(lang)
    return ('<main class="main" data-pane="middle"><h1>%s</h1>%s%s%s%s%s%s</main>'
            % (esc(t["settings"]), _flash(t, flash, None), _setup(t, lang, envs), _compute(t, lang, envs, pf_csrf, flash, given),
               _credentials(t), _keys(t), _rest(t)))


def render(name, csrf, runs, lang, envs, pf_csrf=None, flash=None, given=None):
    """GET /settings: the same frame as the board, this middle column. The left and right columns stay as web_board draws them.
    `pf_csrf` is the token of the register and remove forms (without it no form is drawn); `flash` says a notice or a failure; `given` holds
    what a person typed, {environment name: {box: text}}, so that a refused form comes back filled."""
    return web_board._frame(name, csrf, runs, lang, "settings", lambda t, lang_: render_middle(lang, envs, pf_csrf, flash, given),
                            lambda t, lang_: web_board._right(t, None), path="/settings")


def purpose_of(f):
    """The purpose of the CSRF token of the confirmation page: the six boxes, in order, hashed, so a changed box makes the token wrong."""
    text = "\n".join(str(f.get(k, "")) for k in ("op", "ce", "pipeline", "revision", "module", "home"))
    return "settings-pipeline-confirm:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_confirm(name, csrf, runs, lang, f, token, first_or_last):
    """Step one's answer: what is about to change, and the button that makes it so. Nothing is written until that button is pressed."""
    lang = web_board.pick_lang(lang)
    t = words(lang)
    adding = f["op"] == "add"
    rows = [(t["pf_c_action"], t["pf_op_add"] if adding else t["pf_op_remove"]), (t["pf_c_env"], f["ce"]), (t["pf_s_pipeline"], f["pipeline"]),
            (t["pf_s_revision"], f["revision"]), (t["pf_s_module"], f["module"] or "—"), (t["pf_s_home"], f["home"] or "—")]
    dl = '<dl class="kv">%s</dl>' % "".join("<dt>%s</dt><dd>%s</dd>" % (esc(k), esc(v)) for k, v in rows)
    hint = '<p class="muted">%s</p>' % esc(t["pf_empty"]) if first_or_last else ""
    pairs = [(k, f[k]) for k in ("op", "ce", "pipeline", "revision", "module", "home")] + [("csrf", token)] + _lang_field(lang)
    back = "/settings" + ("?lang=en" if lang == "en" else "")
    mid = ('<main class="main" data-pane="middle"><h1>%s</h1><section class="card sec">%s%s'
           '<form class="lform" method="post" action="/settings/pipelines/confirm">%s<button type="submit">%s</button></form>'
           '<p><a href="%s">%s</a></p></section></main>'
           % (esc(t["pf_c_add"] if adding else t["pf_c_remove"]), dl, hint, _hidden(pairs), esc(t["pf_confirm"]), esc(back), esc(t["pf_back"])))
    return web_board._frame(name, csrf, runs, lang, "settings", lambda t_, lang_: mid, lambda t_, lang_: web_board._right(t_, None), path="/settings")
