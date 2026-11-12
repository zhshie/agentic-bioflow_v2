# Nothing existing: no other module of this package speaks to the platform from a user's own computer; it holds the personal token file and the MCP client the user-side commands share.
"""The connection of the commands that run on a user's own computer (studio-connect, fetch-results).

It is the one module that reads or writes the personal token and the one that reaches the network, and only through the MCP client package: the
platform's public address plus `/mcp`, with `Authorization: Bearer <token>`. It never opens the platform's databases and never imports the server's
code. The token is kept in one file on this computer (`ABF_STUDIO_CONFIG`, else `~/.abf/studio.json`), is never printed, logged or put in a message,
and the environment variable `ABF_PAT` wins over the file when it is set.

`open_session()` is the async context manager the commands use; its `call_tool(name, args)` returns the dict a tool answered, and an error of the
connection is a `StudioError` that carries the exit code (2 not set up, 3 connection or token) and a message that says what happened and what to do."""
import asyncio
import contextlib
import getpass
import json
import os
import re
import ssl
import sys
from pathlib import Path

CONFIG_ENV = "ABF_STUDIO_CONFIG"
PAT_ENV = "ABF_PAT"
MCP_PATH = "/mcp"
CALL_TIMEOUT = 30.0        # seconds for one tool call, and for opening a session
RETRIES = 2                # a public address that does not answer is tried again at most this many times
RETRY_DELAY = 2.0          # seconds between two tries
LOOPBACK = ("127.0.0.1", "localhost", "::1")

STRINGS = {
    "zh": {
        "not_configured": "尚未設定平台連線。請先執行 abf-platform studio-connect --server <平台網址>，把平台網址與自己的權杖存到這台電腦。",
        "config_open": "設定檔 {path} 的權限過寬，其他使用者可能讀取其中的權杖，因此拒絕使用。請執行 chmod 600 {path} 後再試一次。",
        "config_bad": "設定檔 {path} 的內容無法使用（需要平台網址與權杖兩項）。請重新執行 abf-platform studio-connect --server <平台網址>。",
        "bad_url": "平台網址的格式不正確：需為 https://主機 的形式，不含路徑（僅本機的 http://127.0.0.1:埠 與 http://localhost:埠 例外）。請改用正確的網址後再執行一次。",
        "no_token": "沒有收到權杖。請以隱藏輸入貼上權杖，或用 --token-stdin 從標準輸入提供；權杖由平台管理者以 pat new 發出。",
        "bad_token_chars": "權杖含有空白或換行，無法使用。請重新複製權杖後再執行一次。",
        "token_bad": "權杖不正確或已被撤銷。請向平台管理者重新索取權杖（管理者以 abf-platform pat new 發出），再執行 abf-platform studio-connect。",
        "session_bad": "平台拒絕了這項連線（帳號已停用，或連線階段已失效）。請重新執行一次；仍失敗請洽平台管理者。",
        "offline": "這台電腦無法連上網路，或找不到平台主機。請先確認本機網路，並以 studio-connect 的 --server 網址為準：{url}。",
        "unreachable": "平台公開網址無回應：平台所在機器可能未開機，或 Tailscale Funnel／MCP 服務未啟動（網址：{url}）。請稍後再試，或請平台管理者確認。",
        "site_closed": "平台可以連線，但計算站台的連線沒有開啟，因此讀取不到結果。請洽平台管理者，請其重新開啟站台連線後再試。",
        "site_link": "站台連線狀態：{state}（回報時間：{as_of}；代理：{agent}）",
        "tool_error": "平台回報該項操作失敗。請稍後再試；仍失敗請洽平台管理者。",
        "bad_answer": "平台的回覆格式無法辨識。請確認 abf-platform 套件與平台是同一版本後，再執行一次。",
        "write_failed": "無法寫入設定檔 {path}。請確認該資料夾可寫入且磁碟尚有空間，再執行一次。",
        "server_line": "平台網址：{server}",
        "saved": "權杖已存入 {path}",
        "overwritten": "已覆蓋原有的設定。",
        "cloud_note": "此設定檔位於個人資料夾，請勿放進雲端同步的資料夾。",
        "token_prompt": "權杖（輸入時不會顯示）：",
    },
    "en": {
        "not_configured": "No platform connection is set up yet. First run abf-platform studio-connect --server <platform address> to store the address and your own token on this computer.",
        "config_open": "The settings file {path} can be read by other users, so it is refused. Run chmod 600 {path} and try again.",
        "config_bad": "The settings file {path} cannot be used (it needs a platform address and a token). Run abf-platform studio-connect --server <platform address> again.",
        "bad_url": "The platform address is not valid: it must look like https://host with no path (only http://127.0.0.1:port and http://localhost:port on this computer are allowed). Use a valid address and run it again.",
        "no_token": "No token was given. Paste it at the hidden prompt or pass it with --token-stdin; the platform administrator issues it with pat new.",
        "bad_token_chars": "The token contains a space or a line break and cannot be used. Copy it again and run it again.",
        "token_bad": "The token is wrong or has been revoked. Ask the platform administrator for a new token (issued with abf-platform pat new), then run abf-platform studio-connect.",
        "session_bad": "The platform refused the connection (the account is disabled, or the session is no longer valid). Run it once more; if it still fails, contact the platform administrator.",
        "offline": "This computer cannot reach the network, or cannot find the platform host. Check the local network first, and go by the --server address given to studio-connect: {url}.",
        "unreachable": "The platform's public address does not answer: the platform machine may be off, or the Tailscale Funnel or MCP service is not running (address: {url}). Try again later, or ask the platform administrator to check.",
        "site_closed": "The platform is reachable, but the connection to the compute site is not open, so the result cannot be read. Ask the platform administrator to open the site connection again, then retry.",
        "site_link": "Site connection: {state} (as of {as_of}; agent: {agent})",
        "tool_error": "The platform reported that the operation failed. Try again later; if it still fails, contact the platform administrator.",
        "bad_answer": "The answer of the platform is not in a format that can be read. Make sure the abf-platform package is the same version as the platform, then run it again.",
        "write_failed": "The settings file {path} could not be written. Make sure the folder is writable and the disk has space, then run it again.",
        "server_line": "Platform address: {server}",
        "saved": "The token was stored in {path}",
        "overwritten": "The earlier settings were overwritten.",
        "cloud_note": "This settings file is in a personal folder; do not put it in a folder that a cloud service synchronises.",
        "token_prompt": "Token (not shown as you type): ",
    },
}


def lang():
    """The language of the messages: English when the locale says en, else Chinese (the language of the lab)."""
    loc = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
    return "en" if loc.lower().startswith("en") else "zh"


def tr(key, **kw):
    return STRINGS[lang()][key].format(**kw)


class StudioError(Exception):
    """A failure the user can act on. `code` is the exit code, `text` says what happened and what to do; `retry` marks a failure worth trying again."""

    def __init__(self, code, key, retry=False, **kw):
        self.code, self.key, self.retry = code, key, retry
        self.text = tr(key, **kw)
        super().__init__(self.text)

    def parts(self):
        """(what happened, what to do) split at the first sentence end, for the --json envelope."""
        m = re.search(r"(?<=[。])|(?<=\.)(?=\s)", self.text)
        if not m:
            return self.text, None
        return self.text[:m.start()].strip(), self.text[m.start():].strip() or None


# ---- the settings file ------------------------------------------------------------------------------------------------------------------

def config_path():
    env = os.environ.get(CONFIG_ENV)
    return Path(env) if env else Path.home() / ".abf" / "studio.json"


def permission_bits_trusted():
    """Whether the mode bits of a file say who can read it. On Windows (and its Unix-like shells) they are a fiction, so nothing is refused by them."""
    return os.name == "posix" and sys.platform not in ("cygwin", "msys")


_SERVER = re.compile(r"^(?P<scheme>https?)://(?P<host>\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)(?::(?P<port>[0-9]{1,5}))?/?$")


def check_server(raw):
    """The address in its stored form (lower case, no closing slash), or a StudioError. It must be https://host with no path, user, query or fragment;
    plain http only for this computer itself, because the token would cross the network in clear text."""
    m = _SERVER.match(raw.strip()) if isinstance(raw, str) else None
    if not m:
        raise StudioError(2, "bad_url")
    scheme, host, port = m.group("scheme").lower(), m.group("host").lower(), m.group("port")
    if port is not None and not 0 < int(port) < 65536:
        raise StudioError(2, "bad_url")
    if scheme == "http" and host.strip("[]") not in LOOPBACK:
        raise StudioError(2, "bad_url")
    return "%s://%s%s" % (scheme, host, ":" + port if port else "")


def check_token(raw):
    token = raw.strip() if isinstance(raw, str) else ""
    if not token:
        raise StudioError(2, "no_token")
    if re.search(r"\s|[\x00-\x1f\x7f]", token):
        raise StudioError(2, "bad_token_chars")
    return token


def load_config():
    """{server, token, path} from the settings file, with the token of ABF_PAT instead when that is set. A missing file is exit 2 with the next step; on
    a system whose mode bits mean something, a file that others can read is refused."""
    path = config_path()
    try:
        st = path.stat()
    except OSError:
        raise StudioError(2, "not_configured") from None
    if permission_bits_trusted() and st.st_mode & 0o077:
        raise StudioError(2, "config_open", path=path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        server = check_server(data["server"])
        token = check_token(os.environ.get(PAT_ENV) or data["token"])
    except (OSError, ValueError, KeyError, TypeError, StudioError):
        raise StudioError(2, "config_bad", path=path) from None
    return {"server": server, "token": token, "path": str(path)}


def save_config(server, token):
    """Write the settings file: the folder 0700 when it is made here, the file 0600, through a temporary file and one replace, so a failure leaves the old
    file whole and no half file. Returns (path, whether an earlier file was replaced)."""
    path = config_path()
    replaced = path.exists()
    tmp = path.with_name("%s.%s.tmp" % (path.name, os.urandom(4).hex()))
    try:
        fresh = not path.parent.exists()
        os.makedirs(path.parent, exist_ok=True)
        if fresh and os.name == "posix":
            os.chmod(path.parent, 0o700)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"server": server, "token": token}, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise StudioError(1, "write_failed", path=path) from None
    return path, replaced


def ask_token():
    """The token typed at a hidden prompt."""
    return getpass.getpass(tr("token_prompt"))


# ---- the connection ---------------------------------------------------------------------------------------------------------------------

def _leaves(exc, depth=0):
    """Every exception inside an exception group (the MCP client's task groups wrap what went wrong), and the causes down the chain."""
    inner = getattr(exc, "exceptions", None)
    if inner and depth < 8:
        for e in inner:
            yield from _leaves(e, depth + 1)
        return
    yield exc
    for nxt in (exc.__cause__, exc.__context__):
        if nxt is not None and depth < 8:
            yield from _leaves(nxt, depth + 1)


def classify(exc, seen, server):
    """The StudioError for something that went wrong while talking to the platform. `seen` is the list of HTTP status codes of the error answers
    of the attempt, because the MCP client reports every one of them as the same internal error."""
    from httpx2 import ConnectError, NetworkError, TimeoutException
    if isinstance(exc, StudioError):
        return exc
    if 401 in seen:
        return StudioError(3, "token_bad")
    if 403 in seen or 404 in seen:
        return StudioError(3, "session_bad")
    if any(s in (502, 503, 504) for s in seen):
        return StudioError(3, "unreachable", retry=True, url=server)
    leaves = list(_leaves(exc))
    if any(isinstance(e, ssl.SSLError) for e in leaves) or any(isinstance(e, (TimeoutError, TimeoutException)) for e in leaves):
        return StudioError(3, "unreachable", retry=True, url=server)
    if any(isinstance(e, (OSError, ConnectError, NetworkError)) for e in leaves):
        return StudioError(3, "offline", url=server)
    return StudioError(3, "unreachable", retry=True, url=server)


class _Session:
    """What the commands talk to. Every call is one short MCP session of its own (open, ask, close), all inside one deadline: a session that is kept
    open across calls would have to be opened and closed outside any deadline, and a platform that stops answering would hang the command."""

    def __init__(self, http, cfg, seen):
        self._http, self._cfg, self._seen = http, cfg, seen

    async def _run(self, work):
        import anyio
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client
        url = self._cfg["server"] + MCP_PATH
        for attempt in range(RETRIES + 1):
            self._seen.clear()
            try:
                with anyio.fail_after(CALL_TIMEOUT):
                    async with Client(streamable_http_client(url, http_client=self._http)) as client:
                        return await work(client)
            except StudioError:
                raise
            except Exception as e:
                err = classify(e, self._seen, self._cfg["server"])
                if err.retry and attempt < RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise err from None

    async def call_tool(self, name, args):
        """The dict the tool answered."""
        result = await self._run(lambda client: client.call_tool(name, args))
        data = getattr(result, "structured_content", None)
        if not data:
            for block in getattr(result, "content", None) or []:
                text = getattr(block, "text", None)
                if text:
                    try:
                        data = json.loads(text)
                    except ValueError:
                        data = None
                    break
        if getattr(result, "is_error", False):
            raise StudioError(1, "tool_error")
        if not isinstance(data, dict):
            raise StudioError(1, "bad_answer")
        return data

    async def tool_names(self):
        listing = await self._run(lambda client: client.list_tools())
        return [t.name for t in listing.tools]


@contextlib.asynccontextmanager
async def open_session(config=None):
    """The session of the commands, for the stored (or given) address and token. The settings are checked first, so a missing or too open file is
    refused before anything is sent; the connection itself is made by each call, which tries again at most RETRIES times when the public address
    does not answer. Everything that can go wrong is a StudioError."""
    from httpx2 import AsyncClient, Timeout
    cfg = config if config is not None else load_config()
    seen = []

    async def note(response):
        if response.status_code >= 400:
            seen.append(response.status_code)
    async with AsyncClient(headers={"Authorization": "Bearer " + cfg["token"]}, event_hooks={"response": [note]}, timeout=Timeout(CALL_TIMEOUT)) as http:
        yield _Session(http, cfg, seen)


# ---- what the site connection says --------------------------------------------------------------------------------------------------------

SITE_DOWN_TEXT = "No open connection to the site"
SITE_DOWN_CODES = ("site_unreachable", "agent_offline")


def is_site_closed(answer):
    """Whether a tool answer says the connection to the compute site is not open (its words, or its code); a refused path is something else."""
    if not isinstance(answer, dict):
        return False
    reason = answer.get("reason") or answer.get("message") or ""
    return answer.get("code") in SITE_DOWN_CODES or (isinstance(reason, str) and SITE_DOWN_TEXT in reason)


async def site_link_lines(session, compute_env=None):
    """The lines that tell what the platform knows of the site connection of this compute environment; nothing when the platform does not say."""
    try:
        answer = await session.call_tool("list_compute_envs", {})
    except Exception:      # an extra hint must never turn into a second failure
        return []
    lines = []
    for env in answer.get("compute_envs") or []:
        link = env.get("site_connection") if isinstance(env, dict) else None
        if not isinstance(link, dict) or (compute_env and env.get("name") != compute_env):
            continue
        lines.append(tr("site_link", state=link.get("state"), as_of=link.get("as_of"), agent=link.get("agent")))
    return lines
