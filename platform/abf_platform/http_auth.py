# Not the SDK's OAuth AuthSettings: OAuth 2.1 and its discovery pages are a later slice (ADR 0006); this is one plain bearer check against the personal access tokens in tokens.db, nothing more.
"""The bearer check in front of the MCP server over HTTP (spec 009d).

Every request needs `Authorization: Bearer <personal access token>` of a user who is not disabled; anything else is a
401 with `WWW-Authenticate: Bearer` and a body that never repeats what was sent. A valid one sets the caller for the
duration of the request, read through current_caller(). There is no way to switch this off. Local stdio never comes
through here, so its caller stays None.
"""
import contextvars
import json

from . import store
from .actions import Caller

_caller = contextvars.ContextVar("abf_platform_caller", default=None)


def current_caller():
    return _caller.get()


def _bearer(scope):
    for key, value in scope.get("headers", ()):
        if key == b"authorization":
            parts = value.decode("latin-1").split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip() or None
            return None
    return None


async def _refuse(send):
    body = json.dumps({"error": "unauthorized", "message": "a personal access token is required "
                       "(Authorization: Bearer <token>)"}).encode()
    await send({"type": "http.response.start", "status": 401,
                "headers": [(b"www-authenticate", b"Bearer"), (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


class BearerAuth:
    """ASGI middleware: the app behind it is reached only with a valid personal access token."""

    def __init__(self, app, tokens_path):
        self.app = app
        self.tokens_path = tokens_path

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            who = store.lookup_pat(self.tokens_path, _bearer(scope))
        except Exception:
            who = None
        if who is None:
            await _refuse(send)
            return
        reset = _caller.set(Caller(who["user_id"], who["name"], who["lab"]))
        try:
            await self.app(scope, receive, send)
        finally:
            _caller.reset(reset)


def tokens_path_for(index_path, tokens_path=None):
    return tokens_path or store.default_tokens_path(index_path)
