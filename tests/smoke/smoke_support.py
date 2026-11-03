"""Support code for the post-deploy smoke tests (read-only).

Plain module (not a conftest): the probe functions, the skip marks, and a fake
site used by the self-proof tests.  There is no default site; the target comes
only from SMOKE_BASE_URL.  Failure messages name the check, what was expected
and the status code or header name seen.  They never contain a response body,
a cookie, or any part of the URL except the host name.
"""
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

TIMEOUT = 10
SKIP_REASON = "SMOKE_BASE_URL is not set; smoke tests never default to a real site"
MARKERS_OPT = "markers=smoke: read-only checks against a deployed site; need SMOKE_BASE_URL"

SMOKE_MARKS = [
    pytest.mark.smoke,
    pytest.mark.skipif(not os.environ.get("SMOKE_BASE_URL", "").strip(), reason=SKIP_REASON),
]


def smoke(fn):
    """Mark a test as a smoke probe: marker plus skip when SMOKE_BASE_URL is unset."""
    for mark in SMOKE_MARKS:
        fn = mark(fn)
    return fn


class CheckFailed(Exception):
    pass


class CheckSkipped(Exception):
    pass


def base_url():
    """Validated base URL from the environment (scheme://host[:port][/prefix])."""
    raw = os.environ.get("SMOKE_BASE_URL", "").strip()
    if not raw:
        pytest.skip(SKIP_REASON)
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        pytest.fail("SMOKE_BASE_URL must start with the http or https scheme", pytrace=False)
    if parts.username is not None or parts.password is not None:
        pytest.fail("the site address must not contain a user name or password", pytrace=False)
    return parts.scheme + "://" + parts.netloc + parts.path.rstrip("/")


def run_check(check, base):
    try:
        check(base)
    except CheckFailed as exc:
        pytest.fail(str(exc), pytrace=False)
    except CheckSkipped as exc:
        pytest.skip(str(exc))


# ------------------------------------------------------------------ http probe
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def fetch(base, method, path, body=None):
    """One request, no redirect following. Returns (status, headers, body bytes)."""
    req = urllib.request.Request(base + path, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        resp = _OPENER.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as err:
        resp = err
    except Exception as exc:  # connection refused, timeout, DNS ...
        host = urlsplit(base).hostname
        raise CheckFailed("%s %s: could not reach host %s (%s)"
                          % (method, path, host, type(exc).__name__)) from None
    try:
        data = resp.read(65536)
    finally:
        resp.close()
    return resp.status if hasattr(resp, "status") else resp.code, resp.headers, data


def _json(data):
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def _expect_status(item, got, want):
    if got != want:
        raise CheckFailed("%s: expected status %s, got %s" % (item, want, got))


# ---------------------------------------------------------------------- checks
def check_home(base):
    status, headers, _ = fetch(base, "GET", "/")
    if status == 200:
        return
    if status != 303:
        raise CheckFailed("home page GET /: expected status 303 or 200, got %s" % status)
    where = urlsplit(headers.get("Location") or "").path
    if where not in ("/login", "/welcome"):
        raise CheckFailed("home page GET /: expected redirect to /login or /welcome, "
                          "got a different Location")
    status, _, _ = fetch(base, "GET", where)
    _expect_status("home page redirect target " + where, status, 200)


def check_web_alive(base):
    status, _, data = fetch(base, "GET", "/login")
    _expect_status("web process GET /login", status, 200)
    if b"<form" not in data.lower():
        raise CheckFailed("web process GET /login: expected a page with a form, none found")


def check_oauth_metadata(base):
    path = "/.well-known/oauth-authorization-server"
    status, _, data = fetch(base, "GET", path)
    _expect_status("authorization server GET " + path, status, 200)
    doc = _json(data)
    if not isinstance(doc, dict) or "issuer" not in doc:
        raise CheckFailed("authorization server GET %s: expected JSON with an issuer field" % path)


def check_mcp_unauthenticated(base):
    status, headers, data = fetch(base, "POST", "/mcp", b"{}")
    _expect_status("MCP POST /mcp without credentials", status, 401)
    auth = headers.get("WWW-Authenticate") or ""
    if not auth.lower().startswith("bearer"):
        raise CheckFailed("MCP POST /mcp: expected a WWW-Authenticate header starting with Bearer, "
                          "header %s" % ("missing" if not auth else "has another scheme"))
    doc = _json(data)
    if not isinstance(doc, dict) or doc.get("error") != "unauthorized":
        raise CheckFailed("MCP POST /mcp: expected a JSON error of unauthorized")


def check_mcp_resource_metadata(base):
    path = "/.well-known/oauth-protected-resource/mcp"
    status, _, data = fetch(base, "GET", path)
    if status == 404:
        raise CheckSkipped("GET %s is 404: the site was probably started without --public-url" % path)
    _expect_status("MCP resource metadata GET " + path, status, 200)
    if not isinstance(_json(data), dict):
        raise CheckFailed("MCP resource metadata GET %s: expected a JSON object" % path)


def _csp_problems(headers):
    csp = headers.get("Content-Security-Policy")
    if not csp:
        return ["header Content-Security-Policy is missing"]
    out = []
    for need in ("default-src 'none'", "frame-ancestors 'none'"):
        if need not in csp:
            out.append("Content-Security-Policy lacks %s" % need)
    return out


def check_security_headers(base):
    status, headers, _ = fetch(base, "GET", "/login")
    _expect_status("headers of GET /login", status, 200)
    problems = _csp_problems(headers)
    if (headers.get("X-Frame-Options") or "").strip().upper() != "DENY":
        problems.append("X-Frame-Options is not DENY")
    if (headers.get("X-Content-Type-Options") or "").strip().lower() != "nosniff":
        problems.append("X-Content-Type-Options is not nosniff")
    if "no-store" not in (headers.get("Cache-Control") or "").lower():
        problems.append("Cache-Control lacks no-store")
    if problems:
        raise CheckFailed("security headers of GET /login: " + "; ".join(problems))


def check_404_headers(base):
    status, headers, _ = fetch(base, "GET", "/_smoke_no_such_path")
    _expect_status("GET /_smoke_no_such_path", status, 404)
    problems = _csp_problems(headers)
    if problems:
        raise CheckFailed("404 response must carry the CSP: " + "; ".join(problems))


ALL_CHECKS = [check_home, check_web_alive, check_oauth_metadata, check_mcp_unauthenticated,
              check_mcp_resource_metadata, check_security_headers, check_404_headers]


def run_all_checks(base):
    """Run every check; return the list of failure messages (skips are not failures)."""
    failures = []
    for check in ALL_CHECKS:
        try:
            check(base)
        except CheckSkipped:
            pass
        except CheckFailed as exc:
            failures.append(str(exc))
    return failures


# ------------------------------------------------------------------- fake site
class FakeSite:
    """A tiny local site on 127.0.0.1 shaped like the real web and MCP processes."""

    def __init__(self, home="login", login_status=200, drop=None, mcp_status=401,
                 oauth_status=200, resource_meta=True, not_found_status=404,
                 lower=False, secrets=False):
        self.opts = dict(home=home, login_status=login_status, drop=drop,
                         mcp_status=mcp_status, oauth_status=oauth_status,
                         resource_meta=resource_meta, not_found_status=not_found_status,
                         lower=lower, secrets=secrets)
        self.requests = []
        self.post_bodies = []
        self._server = None

    def __enter__(self):
        site = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body=b"", extra=None, web=True):
                o = site.opts
                hdrs = []
                if web:
                    drop = o["drop"]
                    if drop != "csp":
                        csp = ("default-src *" if drop == "csp_weak" else
                               "default-src 'none'; form-action 'self'; frame-ancestors 'none'")
                        hdrs.append(("Content-Security-Policy", csp))
                    if drop != "xfo":
                        hdrs.append(("X-Frame-Options", "DENY"))
                    if drop != "nosniff":
                        hdrs.append(("X-Content-Type-Options", "nosniff"))
                    if drop != "nostore":
                        hdrs.append(("Cache-Control", "no-store"))
                hdrs += list(extra or [])
                if o["secrets"]:
                    hdrs.append(("Set-Cookie", "session=SECRET123"))
                    if body.endswith(b"}"):
                        body = body[:-1] + b', "leak": "SECRET123"}'
                    else:
                        body = body + b" SECRET123"
                self.send_response(status)
                for name, value in hdrs:
                    self.send_header(name.lower() if o["lower"] else name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _record(self):
                site.requests.append((self.command, self.path.split("?")[0], dict(self.headers)))

            def do_GET(self):
                self._record()
                o, path = site.opts, self.path.split("?")[0]
                form = b"<html><form method=post></form></html>"
                if path == "/":
                    home = o["home"]
                    if home == "login":
                        self._send(303, extra=[("Location", "/login")])
                    elif home == "welcome":
                        self._send(303, extra=[("Location", "/welcome")])
                    elif home == "elsewhere":
                        self._send(303, extra=[("Location", "/somewhere-else")])
                    elif home == "500":
                        self._send(500)
                    else:
                        self._send(200, form)
                elif path == "/login":
                    self._send(o["login_status"], form)
                elif path == "/welcome":
                    self._send(200, form)
                elif path == "/.well-known/oauth-authorization-server":
                    self._send(o["oauth_status"], b'{"issuer": "http://127.0.0.1"}',
                               [("Content-Type", "application/json")])
                elif path == "/.well-known/oauth-protected-resource/mcp":
                    if o["resource_meta"]:
                        self._send(200, b'{"resource": "http://127.0.0.1/mcp"}',
                                   [("Content-Type", "application/json")], web=False)
                    else:
                        self._send(404, b"not found", web=False)
                else:
                    self._send(o["not_found_status"], b"not found")

            def do_POST(self):
                self._record()
                length = int(self.headers.get("Content-Length") or 0)
                site.post_bodies.append(self.rfile.read(length))
                if self.path.split("?")[0] == "/mcp":
                    status = site.opts["mcp_status"]
                    if status == 401:
                        self._send(401, b'{"error": "unauthorized"}',
                                   [("WWW-Authenticate", "Bearer realm=\"mcp\""),
                                    ("Content-Type", "application/json")], web=False)
                    else:
                        self._send(status, b"{}", web=False)
                else:
                    self._send(405)

            def do_PUT(self):
                self._record()
                self._send(405)

            do_DELETE = do_PATCH = do_PUT

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self._server.server_address[1]
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        return False
