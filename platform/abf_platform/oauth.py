# Not a hand-written OAuth server, and not the SDK's AuthSettings on the MCP door: the mcp==2.3.0 handlers (metadata, /authorize, /token, /register, /revoke, the S256 PKCE check, the redirect-uri match) do the protocol; this is only their storage in tokens.db, the limits, and the consent page's database side. Alternatives: Authlib / a hosted IdP (a second service for one connector) and a pasted token (what this replaces).
"""Minimal OAuth 2.1 for Claude Desktop's custom connector (spec 009i).

The authorization server lives in the 009c web app (abf_platform.web): metadata, /register, /authorize, /token, /revoke and a consent
page. Everything it keeps is in tokens.db and is a hash or a fact, never a secret in clear:

  oauth_clients   a connector that registered itself (public client: PKCE, no secret); unused for CLIENT_IDLE_SECONDS it is forgotten
  oauth_requests  one /authorize call waiting for a person (REQUEST_SECONDS); decided once, allow or deny
  oauth_codes     sha256 of an authorization code (CODE_SECONDS, single use), bound to client, redirect, PKCE challenge and the user
  tokens          kind oauth_access (ACCESS_SECONDS) and oauth_refresh (REFRESH_SECONDS, rotated at each use), label = client id

An OAuth token proves who the caller is, like a PAT, and nothing more: it opens no confirmation channel, the consent click writes no
confirmations row, and launch / cancel over it still only make a pending request a person must press 送出 on.
"""
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from urllib.parse import urlparse

from mcp.server.auth.provider import (AccessToken, AuthorizationCode, AuthorizationParams, RefreshToken, RegistrationError,
                                      TokenError, construct_redirect_uri)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.responses import JSONResponse

from . import store

SCOPE = "mcp"                       # the one scope: what a PAT can do, as the user
ACCESS_SECONDS = 3600
REFRESH_SECONDS = 30 * 86400
CODE_SECONDS = 300
REQUEST_SECONDS = 600
CLIENT_IDLE_SECONDS = 30 * 86400
MAX_CLIENTS = 200
REGISTRATIONS_PER_HOUR = 10         # per client address, counted over the last hour (docs/PLATFORM.md)
MAX_TRACKED_ADDRESSES = 10000
LOOPBACK = ("127.0.0.1", "::1", "localhost")
ALLOWED_GRANTS = ("authorization_code", "refresh_token")


def redirect_is_allowed(uri):
    """https, or http to this machine (a native app's loopback redirect); no credentials in it, no fragment."""
    try:
        parsed = urlparse(str(uri))
        host = parsed.hostname or ""
        parsed.port
    except ValueError:
        return False
    if parsed.username or parsed.password or parsed.fragment or not host:
        return False
    return parsed.scheme == "https" or (parsed.scheme == "http" and host in LOOPBACK)


@contextmanager
def _immediate(con):
    """One transaction that takes the write lock first, so two requests that race for the same code or request id queue up."""
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.rollback()
        raise
    else:
        con.commit()


class PlatformCode(AuthorizationCode):
    grant_id: str
    user_id: int


class RegisterRateCap:
    """ASGI middleware: at most REGISTRATIONS_PER_HOUR POST /register per client address per hour (429 after that). In memory, so a
    restart forgives; a live window is never dropped, and past MAX_TRACKED_ADDRESSES new addresses are refused."""

    def __init__(self, app, clock=time.time):
        self.app = app
        self.clock = clock
        self.seen = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/register" and scope["method"] == "POST":
            now = self.clock()
            address = (scope.get("client") or ("",))[0]
            live = [t for t in self.seen.get(address, ()) if now - t < 3600]
            if len(live) >= REGISTRATIONS_PER_HOUR or (address not in self.seen and len(self.seen) >= MAX_TRACKED_ADDRESSES):
                self.seen[address] = live
                response = JSONResponse({"error": "temporarily_unavailable", "error_description": "too many registrations from this address, try later"},
                                        status_code=429, headers={"Retry-After": "3600", "Cache-Control": "no-store"})
                await response(scope, receive, send)
                return
            live.append(now)
            self.seen[address] = live
        await self.app(scope, receive, send)


class PlatformOAuthProvider:
    """The SDK's OAuthAuthorizationServerProvider over tokens.db. `clock` is a parameter so a test can move time."""

    def __init__(self, tokens_path, base_url, clock=time.time):
        self.tokens_path = tokens_path
        self.base_url = base_url.rstrip("/")
        self.clock = clock

    def _con(self):
        return store.connect_tokens(self.tokens_path)

    # ---- clients -----------------------------------------------------------------------------------------------------
    def _forget_idle_clients(self, con, now):
        con.execute("DELETE FROM oauth_clients WHERE COALESCE(last_used_at, created_at) < ?", (now - CLIENT_IDLE_SECONDS,))
        con.execute("DELETE FROM oauth_requests WHERE expires_at < ?", (now - 86400,))

    async def get_client(self, client_id):
        if not isinstance(client_id, str) or not client_id:
            return None
        now = self.clock()
        con = self._con()
        try:
            with con:
                self._forget_idle_clients(con, now)
                row = con.execute("SELECT info_json FROM oauth_clients WHERE client_id = ?", (client_id,)).fetchone()
            return OAuthClientInformationFull.model_validate_json(row["info_json"]) if row else None
        finally:
            con.close()

    async def register_client(self, client_info):
        uris = client_info.redirect_uris or []
        if not uris or not all(redirect_is_allowed(u) for u in uris):
            raise RegistrationError("invalid_redirect_uri", "every redirect_uri must be https, or http to localhost / 127.0.0.1 / [::1], with no credentials or fragment")
        if not set(client_info.grant_types) <= set(ALLOWED_GRANTS) or list(client_info.response_types) != ["code"]:
            raise RegistrationError("invalid_client_metadata", "only grant_types authorization_code and refresh_token, and response_types code, are served")
        # This server registers public clients only (PKCE protects the code): a secret the SDK minted is not kept and not asked for.
        client_info.token_endpoint_auth_method = "none"
        client_info.client_secret = None
        client_info.client_secret_expires_at = None
        now = self.clock()
        con = self._con()
        try:
            with _immediate(con):
                self._forget_idle_clients(con, now)
                if con.execute("SELECT COUNT(*) FROM oauth_clients").fetchone()[0] >= MAX_CLIENTS:
                    raise RegistrationError("invalid_client_metadata", "too many registered connectors; try again later")
                con.execute("INSERT INTO oauth_clients (client_id, info_json, created_at, last_used_at) VALUES (?, ?, ?, NULL)",
                            (client_info.client_id, client_info.model_dump_json(), now))
        finally:
            con.close()

    # ---- the consent request -----------------------------------------------------------------------------------------
    async def authorize(self, client, params: AuthorizationParams):
        rid = secrets.token_hex(16)
        now = self.clock()
        con = self._con()
        try:
            with con:
                con.execute("INSERT INTO oauth_requests (id, client_id, redirect_uri, redirect_explicit, code_challenge, state, resource, "
                            "created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (rid, client.client_id, str(params.redirect_uri), int(params.redirect_uri_provided_explicitly),
                             params.code_challenge, params.state, params.resource, now, now + REQUEST_SECONDS))
                con.execute("UPDATE oauth_clients SET last_used_at = ? WHERE client_id = ?", (now, client.client_id))
        finally:
            con.close()
        return "%s/consent/%s" % (self.base_url, rid)

    def consent_request(self, rid):
        """{'id', 'client_name', 'redirect_host', 'redirect_origin', 'state' (decided or not), 'expired'} for the consent page, else None."""
        con = self._con()
        try:
            row = con.execute("SELECT r.*, c.info_json FROM oauth_requests r LEFT JOIN oauth_clients c ON c.client_id = r.client_id "
                              "WHERE r.id = ?", (rid,)).fetchone()
        finally:
            con.close()
        if row is None:
            return None
        info = json.loads(row["info_json"]) if row["info_json"] else {}
        parsed = urlparse(row["redirect_uri"])
        return {"id": rid, "client_id": row["client_id"], "client_name": info.get("client_name") or "", "redirect_host": parsed.hostname or "",
                "redirect_origin": "%s://%s" % (parsed.scheme, parsed.netloc), "decision": row["decision"],
                "expired": row["expires_at"] <= self.clock()}

    def consent_decide(self, rid, user_id, decision):
        """Press Allow or Deny once. Returns (status, location): status is 'allowed' / 'denied' (location = where the connector goes next)
        or 'unknown' / 'expired' / 'decided' / 'user' (nothing happened, location None). Allow mints the code in the same transaction that
        marks the request decided, so two presses make one code at most. No confirmations row is written, no job is queued."""
        now = self.clock()
        con = self._con()
        try:
            with _immediate(con):
                row = con.execute("SELECT * FROM oauth_requests WHERE id = ?", (rid,)).fetchone()
                if row is None:
                    return "unknown", None
                if row["decision"] is not None:
                    return "decided", None
                if row["expires_at"] <= now:
                    return "expired", None
                if decision == "deny":
                    con.execute("UPDATE oauth_requests SET decision = 'deny', decided_at = ? WHERE id = ?", (now, rid))
                    return "denied", construct_redirect_uri(row["redirect_uri"], error="access_denied", state=row["state"])
                if con.execute("SELECT 1 FROM users WHERE id = ? AND disabled_at IS NULL", (user_id,)).fetchone() is None:
                    return "user", None
                code = secrets.token_urlsafe(32)
                con.execute("UPDATE oauth_requests SET decision = 'allow', decided_at = ? WHERE id = ?", (now, rid))
                con.execute("INSERT INTO oauth_codes (code_hash, grant_id, client_id, redirect_uri, redirect_explicit, code_challenge, resource, "
                            "user_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (store.token_hash(code), secrets.token_hex(16), row["client_id"], row["redirect_uri"], row["redirect_explicit"],
                             row["code_challenge"], row["resource"], user_id, now, now + CODE_SECONDS))
                return "allowed", construct_redirect_uri(row["redirect_uri"], code=code, state=row["state"])
        finally:
            con.close()

    # ---- codes and tokens ---------------------------------------------------------------------------------------------
    def _revoke_grant(self, grant_id):
        if not grant_id:
            return
        con = self._con()
        try:
            with con:
                con.execute("UPDATE tokens SET revoked_at = ? WHERE grant_id = ? AND revoked_at IS NULL", (self.clock(), grant_id))
        finally:
            con.close()

    async def load_authorization_code(self, client, authorization_code):
        con = self._con()
        try:
            row = con.execute("SELECT * FROM oauth_codes WHERE code_hash = ?", (store.token_hash(authorization_code),)).fetchone()
        finally:
            con.close()
        if row is None or row["client_id"] != client.client_id:
            return None
        if row["used_at"] is not None:
            self._revoke_grant(row["grant_id"])       # RFC 6749 4.1.2: a code used twice ends what the first use made
            return None
        if row["expires_at"] <= self.clock():
            return None
        return PlatformCode(code=authorization_code, scopes=[SCOPE], expires_at=row["expires_at"], client_id=row["client_id"],
                            code_challenge=row["code_challenge"], redirect_uri=row["redirect_uri"],
                            redirect_uri_provided_explicitly=bool(row["redirect_explicit"]), resource=row["resource"],
                            grant_id=row["grant_id"], user_id=row["user_id"])

    def _mint(self, con, user_id, client_id, grant_id, now):
        access, refresh = "abf_oat_" + secrets.token_urlsafe(32), "abf_ort_" + secrets.token_urlsafe(32)
        for token, kind, ttl in ((access, "oauth_access", ACCESS_SECONDS), (refresh, "oauth_refresh", REFRESH_SECONDS)):
            con.execute("INSERT INTO tokens (token_hash, created_at, kind, expires_at, user_id, label, grant_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (store.token_hash(token), now, kind, now + ttl, user_id, client_id, grant_id))
        return OAuthToken(access_token=access, expires_in=ACCESS_SECONDS, scope=SCOPE, refresh_token=refresh)

    async def exchange_authorization_code(self, client, authorization_code):
        now = self.clock()
        con = self._con()
        try:
            with _immediate(con):
                used = con.execute("UPDATE oauth_codes SET used_at = ? WHERE code_hash = ? AND used_at IS NULL AND expires_at > ?",
                                   (now, store.token_hash(authorization_code.code), now)).rowcount
                if used != 1:
                    refused = "code_used"
                elif con.execute("SELECT 1 FROM users WHERE id = ? AND disabled_at IS NULL", (authorization_code.user_id,)).fetchone() is None:
                    refused = "user"
                else:
                    return self._mint(con, authorization_code.user_id, client.client_id, authorization_code.grant_id, now)
        finally:
            con.close()
        if refused == "code_used":
            self._revoke_grant(authorization_code.grant_id)
        raise TokenError("invalid_grant", "the authorization code is not valid")

    async def load_refresh_token(self, client, refresh_token):
        con = self._con()
        try:
            row = con.execute("SELECT t.grant_id, t.label, t.expires_at, t.revoked_at, u.disabled_at FROM tokens t "
                              "JOIN users u ON u.id = t.user_id WHERE t.token_hash = ? AND t.kind = 'oauth_refresh'",
                              (store.token_hash(refresh_token),)).fetchone()
        finally:
            con.close()
        if row is None or row["label"] != client.client_id:
            return None
        if row["revoked_at"] is not None:
            self._revoke_grant(row["grant_id"])       # a refresh token used again after it was rotated or revoked: the family ends
            return None
        if row["expires_at"] <= self.clock() or row["disabled_at"] is not None:
            return None
        return RefreshToken(token=refresh_token, client_id=row["label"], scopes=[SCOPE], expires_at=int(row["expires_at"]))

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        now = self.clock()
        digest = store.token_hash(refresh_token.token)
        con = self._con()
        try:
            with _immediate(con):
                row = con.execute("SELECT user_id, grant_id FROM tokens WHERE token_hash = ? AND kind = 'oauth_refresh'", (digest,)).fetchone()
                took = con.execute("UPDATE tokens SET revoked_at = ? WHERE token_hash = ? AND kind = 'oauth_refresh' AND revoked_at IS NULL",
                                   (now, digest)).rowcount
                if row is None or took != 1:
                    refused = True
                else:
                    return self._mint(con, row["user_id"], client.client_id, row["grant_id"], now)
        finally:
            con.close()
        raise TokenError("invalid_grant", "the refresh token is not valid")

    async def load_access_token(self, token):
        con = self._con()
        try:
            row = con.execute("SELECT label, expires_at FROM tokens WHERE token_hash = ? AND kind = 'oauth_access' AND revoked_at IS NULL "
                              "AND expires_at > ?", (store.token_hash(token), self.clock())).fetchone()
        finally:
            con.close()
        return AccessToken(token=token, client_id=row["label"], scopes=[SCOPE], expires_at=int(row["expires_at"])) if row else None

    async def revoke_token(self, token):
        """Revoke the token and every other token of the same authorization (access and refresh go together)."""
        con = self._con()
        try:
            with con:
                row = con.execute("SELECT grant_id FROM tokens WHERE token_hash = ? AND kind IN ('oauth_access', 'oauth_refresh')",
                                  (store.token_hash(token.token),)).fetchone()
                if row and row["grant_id"]:
                    con.execute("UPDATE tokens SET revoked_at = ? WHERE grant_id = ? AND revoked_at IS NULL", (self.clock(), row["grant_id"]))
        finally:
            con.close()
