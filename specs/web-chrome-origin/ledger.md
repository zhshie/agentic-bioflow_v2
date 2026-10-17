# Ledger: web-chrome-origin

| What | Old value | New value | Reason |
|---|---|---|---|
| `Referrer-Policy` header, `_HEADERS` in platform/abf_platform/web.py:44 | `no-referrer` | `same-origin` | Chrome sends Origin: null under no-referrer |

Pins on the old value found by `grep -rni referrer`: none besides web.py itself (no test, doc or spec named it).
