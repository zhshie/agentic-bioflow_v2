# web-chrome-origin (bug, tier A)
Bug: in real Chrome, logging in and pressing 送出 on /c/<id> returns 403 "來源不符" (found 2026-10-18 by a Playwright run).
Cause: web.py sent `Referrer-Policy: no-referrer`; under it Chrome sends `Origin: null` on same-origin form POSTs, and `same_origin()` rightly rejects "null".
Fix: send `Referrer-Policy: same-origin` (real Origin/Referer on same-origin requests, nothing cross-origin); `same_origin()` is unchanged, "null", foreign and (as before) only non-browser missing Origin.
Tests: platform/tests/test_web_chrome_origin.py: WCO-1 header on every response, WCO-2 null/foreign refused and own origin accepted, WCO-3 real Chrome via Playwright (skipped when unavailable).
Tier: A.
