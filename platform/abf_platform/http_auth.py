# Not the SDK's resource-server auth settings on the MCP app: this one bearer check stays the only door (a personal access token, or since 009i an OAuth access token from tokens.db); the SDK only supplies the protected-resource metadata document.
"""The bearer check in front of the MCP server over HTTP (spec 009d, 009i).

Every request needs `Authorization: Bearer <token>` where the token is a personal access token or a live OAuth access token (made by
abf_platform.oauth after a web login and a click) of a user who is not disabled; anything else is a 401 with `WWW-Authenticate: Bearer`
(with `resource_metadata="<url>"` when this server has a public address, so a connector can find its way to the login) and a body that
never repeats what was sent. A valid token sets the caller for the duration of the request, read through current_caller(); a PAT and an
OAuth token of the same user give the same Caller. There is no way to switch this off. Local stdio never comes through here, so its
caller stays None. The one thing served without a token is the protected-resource metadata document (GET, that exact path).
"""
import collections
import contextvars
import json
from urllib.parse import urlparse

from mcp.server.auth.routes import build_resource_metadata_url, create_protected_resource_routes
from starlette.applications import Starlette

from . import store
from .actions import Caller

_caller = contextvars.ContextVar("abf_platform_caller", default=None)
_remote = contextvars.ContextVar("abf_platform_remote", default=False)
LOOPBACK = ("127.0.0.1", "::1", "localhost")
MAX_SESSIONS = 10000        # sessions whose owner is remembered; the oldest unused one is forgotten first (its client opens a new one)


def current_caller():
    return _caller.get()


def current_remote():
    """Whether the request in hand came from beyond this machine (a peer or a host name that is not loopback)."""
    return _remote.get()


def _header(scope, name):
    for key, value in scope.get("headers", ()):
        if key == name:
            return value.decode("latin-1")
    return None


def is_remote(scope):
    peer = (scope.get("client") or ("",))[0]
    host = (_header(scope, b"host") or "").strip().lower()
    host = host[1:host.index("]")] if host.startswith("[") and "]" in host else host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    return bool(peer and peer not in LOOPBACK) or bool(host and host not in LOOPBACK)


def _bearer(scope):
    for key, value in scope.get("headers", ()):
        if key == b"authorization":
            parts = value.decode("latin-1").split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip() or None
            return None
    return None


async def _reject(send, status, error, message):
    body = json.dumps({"error": error, "message": message}).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


async def _refuse(send, metadata_url=None):
    body = json.dumps({"error": "unauthorized", "message": "a personal access token or an OAuth access token is required "
                       "(Authorization: Bearer <token>)"}).encode()
    challenge = b'Bearer resource_metadata="' + metadata_url.encode("ascii", "ignore") + b'"' if metadata_url else b"Bearer"
    await send({"type": "http.response.start", "status": 401,
                "headers": [(b"www-authenticate", challenge), (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


class BearerAuth:
    """ASGI middleware: the app behind it is reached only with a valid personal access token, and an MCP session (its
    Mcp-Session-Id) is used only with a token of the user who opened it. The caller of a request is put in the request's own
    scope (`abf_caller`), which is what the tools read: not a variable that outlives the request."""

    def __init__(self, app, tokens_path, platform_path=None, public_url=None):
        self.app = app
        self.tokens_path = tokens_path
        self.platform_path = platform_path
        self.public_url = (public_url or "").rstrip("/")
        self.sessions = collections.OrderedDict()      # session id -> user id of the token that opened it
        self._discovered = None                        # (authorization server address, metadata url, metadata app)

    def discovery(self):
        """(metadata url, the SDK's metadata app) when this server has a public address and the web app has published its own,
        else (None, None): without both there is nothing to point a connector at."""
        if not self.public_url or not self.platform_path:
            return None, None
        try:
            server = store.get_meta(self.platform_path, "web_base_url")
        except Exception:
            server = None
        if not server:
            return None, None
        if self._discovered is None or self._discovered[0] != server:
            resource = self.public_url + "/mcp"
            routes = create_protected_resource_routes(resource, [server], resource_name="abf-platform")
            self._discovered = (server, str(build_resource_metadata_url(resource)), Starlette(routes=routes))
        return self._discovered[1], self._discovered[2]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        metadata_url, metadata_app = self.discovery()
        if metadata_app is not None and scope.get("method") == "GET" and scope.get("path") == urlparse(metadata_url).path:
            await metadata_app(scope, receive, send)          # the one answer given without a token
            return
        oauth_who = None
        try:
            token = _bearer(scope)
            who = store.lookup_pat(self.tokens_path, token)
            oauth_who = None if who else store.lookup_oauth_access(self.tokens_path, token)
            who = who or oauth_who
        except Exception:
            who = None
        if who is None:
            await _refuse(send, metadata_url)
            return
        session = _header(scope, b"mcp-session-id")
        if session is not None:
            owner = self.sessions.get(session)
            if owner is None:
                await _reject(send, 404, "session_not_found", "no such session; open a new one")
                return
            if owner != who["user_id"]:
                await _reject(send, 403, "forbidden", "this session was opened by another token")
                return
            self.sessions.move_to_end(session)
        caller = (Caller.connector(who["user_id"], who["name"], who["lab"], oauth_who["form_ok"]) if oauth_who
                  else Caller(who["user_id"], who["name"], who["lab"]))
        scope["abf_caller"] = caller
        scope["abf_remote"] = is_remote(scope)
        user_id, method = who["user_id"], scope.get("method")

        async def watching(message):
            if message["type"] == "http.response.start" and message["status"] < 400:
                if session is None:
                    new = _header({"headers": [(k, v) for k, v in message.get("headers", ())]}, b"mcp-session-id")
                    if new:
                        self.sessions[new] = user_id
                        while len(self.sessions) > MAX_SESSIONS:
                            self.sessions.popitem(last=False)
                elif method == "DELETE":
                    self.sessions.pop(session, None)
            await send(message)

        reset, reset_remote = _caller.set(caller), _remote.set(scope["abf_remote"])
        try:
            await self.app(scope, receive, watching)
        finally:
            _caller.reset(reset)
            _remote.reset(reset_remote)


def tokens_path_for(index_path, tokens_path=None):
    return tokens_path or store.default_tokens_path(index_path)
