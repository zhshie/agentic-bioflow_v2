# cb-D3 plan: regex end anchor `$` -> `\Z` in validate.py and cloud_store.py

Source: cloud-burn tasks.json D3 (shard A, order 21, risk M).

## Goal
`validate._PLAIN` (platform/abf_platform/validate.py:14) and `cloud_store._BUCKET` (platform/abf_platform/cloud_store.py:11)
end with a bare `$`, which in Python also matches just before a trailing `\n`. So `"txt\n"` passes as a plain extension and
`"my-bucket\n"` passes as a bucket name. End both with `\Z` (same form as `compose._NAME`) and shrink the baseline.

## Files
- platform/abf_platform/validate.py (line 14, one regex)
- platform/abf_platform/cloud_store.py (line 11, one regex)
- tests/regex_end_anchor_baseline.txt (delete exactly the two matching lines, delete only)
- platform/tests/test_regex_anchor_fixes.py (new)
- specs/cb-D3/plan.md, specs/cb-D3/ledger.md

## Approach
Replace the trailing `$` by `\Z` in the two literals. Nothing else changes: `.match` stays, so every string that does not end in
a newline behaves as before. The only shapes that change are those whose last character is exactly one `\n` after an otherwise
valid name.

## RED tests (platform/tests/test_regex_anchor_fixes.py)
- `validate._PLAIN` rejects "txt\n"; `validate._extensions("*.txt\n")` and a brace form return None.
- `cloud_store._BUCKET` / `_container_ok("gs", ...)` reject "my-bucket\n" (and 63/64-char edges with a newline).
- Regression table: the shapes that were accepted/rejected on the base (recorded by /tmp/cb/D3_cal/shapes.py on both trees) still
  give the same answer except the trailing-newline ones. Public `parse_gs` still rejects a newline (the control-character check
  fires first), so that path is unchanged; the RED cases therefore go through the compiled regex and `_container_ok`.
- Source guard: neither file's literal ends in a bare `$`.

## Done criteria
New tests RED on base, green after the fix; `tests/regex_end_anchor_test.sh` green with the two baseline lines gone (no stale
lines, no new hits); full `tests/run_all.sh` green; old shapes re-run against base and branch, diff is only the newline shapes.

## Environment facts
venv /tmp/cb/venv, `pip install -e /tmp/cb/D3/platform pytest`; egg-info/build removed after install.

## Not doing
No other baseline line, no other regex, no behaviour change to parse_*; no edit to compose.py or hot files.
