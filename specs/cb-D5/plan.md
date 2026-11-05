# cb-D5 plan: regex end anchor `$` -> `\Z` in methods_text.py and collect_provenance.py

Source: cloud-burn tasks.json D5 (shard A, order 22, risk M).

## Goal
Four validators in scripts/methods_text.py (GITHUB_NAME_RE, REV_RE, SHA_RE, IMMUTABLE_REV_RE) and two in
scripts/collect_provenance.py (TIMESTAMPED, the DOI line match in dois_from_citations) end with a bare `$`, which in Python
also matches just before a trailing `\n`. End them with `\Z`. Also delete the dead `assets_dir` in methods_text.py (no caller)
and the test's monkeypatch of it.

## Files
- scripts/methods_text.py, scripts/collect_provenance.py
- tests/regex_end_anchor_baseline.txt (delete exactly the six matching lines)
- tests/package_gaps_test.sh (delete only the `m.assets_dir = lambda ...` line, ~:146)
- tests/methods_text_anchor_test.sh (new)
- specs/cb-D5/plan.md, specs/cb-D5/ledger.md

## Approach
Replace the trailing `$` by `\Z`; `.match` stays. Only strings ending in exactly one `\n` after an otherwise valid value change.
The DOI match runs on `line.rstrip()`, so it is behaviour-neutral; it is changed for the guard and the baseline.

## RED tests (tests/methods_text_anchor_test.sh)
Each regex rejects the newline-terminated shape and accepts ordinary ones; `is_immutable("v1.2.3\n")` is False; `assets_dir`
is gone; no `^...$` literal remains in either file.

## Done criteria
New test RED on base, green after; `tests/regex_end_anchor_test.sh` green with six lines gone; package_gaps_test.sh green;
full run_all.sh green.

## Environment facts
venv /tmp/cb/venv; egg-info/build removed after install.

## Not doing
No other baseline line, no other regex, no other file.
