# web-confirm-plain: the confirmation page says it in plain words first

Tier B (visible change). Maintainer 2026-10-19: "好的按照你的建議" — the confirmation page `/c/<id>` should open with a short plain summary; the full technical content stays on the page but folded.

## What changes
- C1. In `platform/abf_platform/web.py` `state_page`, above the 送出 button, show a short plain block (a definition list) with what the person is deciding: what kind of request (送出新分析 / 續跑 / 重跑 / 取消 / 刪除保留內容), run name, pipeline and version, compute environment, number of samples, and the new folder when there is one. Take these from the request's existing data (prefer structured fields the action layer already has; if only the summary text has them, add one small action-layer helper that returns them, placed in WEB_ONLY per the parity rule — never parse in the page and never import confirm in web.py). A field that is not known is left out, not shown as "-".
- C2. The full content that is sent (today's `<pre>` text, unchanged byte for byte) stays on the same page inside a `<details>` element whose summary reads 完整內容（技術細節） / "Full content (technical)". Native HTML, no script. Principle I.2 still holds: everything sent is on the page before the person presses 送出, nothing is hidden behind another request.
- C3. The `<pre>` wraps long lines (CSS `white-space: pre-wrap; overflow-wrap: anywhere`) so a phone at 390 px shows whole paths with no horizontal scroll, inside or outside the block.
- C4. Same on the confirmed page (after 送出): plain block + folded full content. Expired and void pages unchanged.
- C5. ?lang=en has an English version of the plain block labels. Zero JS, one stylesheet, CSP hash updated, no inline style.

## Out of scope
Changing what is sent, the approve flow, CSRF, owner rules, or other pages.

## Tests first
- The pending page shows the plain block with the right values for a launch, a relaunch and a cancel request, and the 送出 form still posts with CSRF.
- The full summary text is present byte-for-byte inside a `<details>` on the pending page (no information removed).
- No `<script>`, no `style=`; CSP hash matches the one stylesheet.
- At 390 px the page has no horizontal scroll (test the CSS rule exists on the pre).
- English page labels are English.
- Approve path unchanged: existing confirm-page tests still pass unchanged except string swaps listed in the ledger.

## Named change to an existing test (added in the 2026-10-19 fix round)
- `platform/tests/test_web_board.py::test_tcs45_confirm_pages_share_the_style` has one assertion narrowed on purpose: `c.get("/c/<id>?lang=en").text == r.text` (whole page) becomes `style_of(c.get("/c/<id>?lang=en").text) == style_of(r.text)` (the stylesheet). Why: C5 gives the English confirmation page English labels, so the whole page cannot equal the Chinese one; what the test protects (one shared stylesheet, one CSP hash) is kept, and the English page content is covered by `test_web_confirm_plain.py` (TC-021, TC-023). This is the only existing assertion changed. Maintainer or verifier to confirm.
