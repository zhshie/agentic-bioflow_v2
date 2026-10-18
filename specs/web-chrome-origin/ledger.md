# Ledger: web-chrome-origin

| What | Old value | New value | Reason |
|---|---|---|---|
| `Referrer-Policy` header, `_HEADERS` in platform/abf_platform/web.py:44 | `no-referrer` | `same-origin` | Chrome sends Origin: null under no-referrer |

Pins on the old value found by `grep -rni referrer`: none besides web.py itself (no test, doc or spec named it).

## WCO-3 moved out of pytest

WCO-3 (a real Chrome logs in and presses send) was a pytest test that skipped when Playwright or Chrome was absent. CI has neither, and CI fails on any skipped test ("nothing may be skipped on CI"). It is now the manual script `scripts/dev/check_chrome_login.py` (steps in docs/TESTING.md, "Chrome login (web-chrome-origin)"). WCO-1 and WCO-2 stay in pytest unchanged.

## Merge of origin/v3 (009i OAuth, #126)

Conflicts in `docs/TESTING.md` and `platform/abf_platform/web.py`; both sides kept, nothing loosened.

- `web.py`: v3's `Starlette(routes=[... /consent/{rid} ...] + auth_routes, middleware=[RegisterBodyCap, RegisterRateCap])` kept whole; this branch's `add_headers` middleware (`BaseHTTPMiddleware`, adds every `_HEADERS` entry incl. `Referrer-Policy: same-origin` with `setdefault`) is added after it with `app.add_middleware`, which puts it outermost. So it also wraps the responses `RegisterBodyCap` and `RegisterRateCap` make before any route runs (413, 429), plus the OAuth routes and the consent pages.
- `docs/TESTING.md`: both sections kept ("Chrome login (web-chrome-origin)" and "Claude Desktop custom connector (#117)").
- Tests: WCO-1 and WCO-2 unchanged; new `test_wco1_the_oauth_routes_and_the_register_cap_carry_the_header_too` asserts `Referrer-Policy: same-origin` (and `X-Frame-Options: DENY`) on the consent page (logged in and not), `/register` (201, 413 over the cap, bad body), `/authorize` 400, `/token` error, a consent POST refusal and a consent 404.
