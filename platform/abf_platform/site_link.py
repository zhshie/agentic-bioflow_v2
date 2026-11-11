# Nothing existing: which agents have just said their site connection is closed, the one refusal sentence and the red bar that say so
# (mcp-site-keepalive-disconnect-ux); agents.list_agents already holds the word, this only reads it and words the two places that show it.
"""The site connection as the person must be told about it: a read-only list, one sentence, one bar."""
import contextvars
import html as _html

from . import agents, jobs

# set again by web.user_of for every request (the names of this person's agents whose link is fresh and closed), like DEV_MODE
SITE_DOWN_AGENTS = contextvars.ContextVar("abf_site_down_agents", default=())

BAR_ZH = ("站台連線已掉：請在執行 agent「%s」那台機器的 WSL 終端機重新登入（貼上開連線指令並輸入 OTP）。"
          "已在跑的 run 不受影響；新的 run 在恢復前無法送出。")
BAR_EN = ('The site connection is down. On the machine running agent "%s", log in again in its WSL terminal (paste the connect line, '
          'type the one-time code). Runs already going are not affected; new runs cannot be sent until it is back.')


def closed_agents(state_path, owner, at):
    """Names (sorted) of the agents of `owner` (None: all) that are online and whose last word is site_link=closed. Read only; an offline
    or silent agent is `unknown` in agents.view, so it never shows here."""
    return sorted(a["name"] for a in agents.list_agents(state_path, at, owner=owner) if a["site_link"] == "closed")


def down_message(agent):
    """The sentence a refused launch carries: it starts with jobs.SITE_DOWN, names the agent and the WSL terminal in its first sentence,
    and stays under the 300 characters confirm keeps."""
    return ("%s: 連線已掉，請在執行 agent「%s」那台機器的 WSL 終端機重新登入，再重新送出。"
            "已在跑的 run 不受影響 (runs already going are not affected)" % (jobs.SITE_DOWN, str(agent)[:64]))


def bar_html(names, lang):
    """One red bar per agent, in the shape of the development-mode bar; the name is escaped."""
    text = BAR_EN if lang == "en" else BAR_ZH
    return "".join('<div class="linkbar" role="alert"><span aria-hidden="true">✗</span><span>%s</span></div>'
                   % (text % _html.escape(n, quote=True)) for n in names)
