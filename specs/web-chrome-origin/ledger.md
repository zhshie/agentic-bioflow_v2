# Ledger: web-chrome-origin

| What | Old value | New value | Reason |
|---|---|---|---|
| `Referrer-Policy` header, `_HEADERS` in platform/abf_platform/web.py:44 | `no-referrer` | `same-origin` | Chrome sends Origin: null under no-referrer |

Pins on the old value found by `grep -rni referrer`: none besides web.py itself (no test, doc or spec named it).

## WCO-3 moved out of pytest

WCO-3 (a real Chrome logs in and presses send) was a pytest test that skipped when Playwright or Chrome was absent. CI has neither, and CI fails on any skipped test ("nothing may be skipped on CI"). It is now the manual script `scripts/dev/check_chrome_login.py` (steps in docs/TESTING.md, "Chrome login (web-chrome-origin)"). WCO-1 and WCO-2 stay in pytest unchanged.
