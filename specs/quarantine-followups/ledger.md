# 隔離名單補強：最多 28 天、測試不跨午夜翻轉、重跑用乾淨暫存 progress ledger

## Progress (2026-10-24, executor)

- [x] RED 4bbda46: tests written first. Against the old runner 140 cases were red, for the right reason (the old runner rejects the four-column data and has no since rules and no clean retry TMPDIR). Excerpt:

```
TC-101 old three-column line (found 3): exit 1                         FAIL
TC-101 old three-column line (found 3): says 'found 3'                 FAIL
TC-101 names the file:line                                             FAIL
TC-101 tells what to add                                               FAIL
TC-103 since in the future: says 'in the future'                       FAIL
TC-107 since-15, expiry today+14 (= since+29): says '28 days'          FAIL
TC-107 prints the since date                                           FAIL
TC-121a shim 2030-02-28, expiry +14: exit 0                            FAIL
TC-130 retry does not see the first run's leftover: exit 0             FAIL
TC-130 green after retry: 1                                            FAIL
TC-131a/b: no tmpdir record (the first run never started: the old runner rejected the 4-column list)
TC-137 test file was not re-run on the shared TMPDIR                   FAIL
```

- [x] GREEN 3c937e3: `tests/run_all.sh` (since column, rules 1-7 in the plan's order; QUAR stays three columns; the retry gets `$LOGDIR/tmp.<name>.retry` via `env TMPDIR=`; mkdir failure = failed retry; usage/header/hint text), `tests/quarantine.txt` header (line 12 stays the platform line, so PS-24 is unchanged), `tests/run_all_retry_test.sh` (date shim on PATH, `qline`, one clock reading, midnight rerun removed, new cases TC-101..TC-138).
- [x] `bash tests/run_all_retry_test.sh` in WSL: 321 cases ok, 0 failed.
- [x] TC-139 (stand-in for crossing midnight): the whole file under `TZ=UTC-14` and under `TZ=UTC+12` both end `all run_all_retry cases ok`; the two outputs are byte-identical (`cmp`). TC-123 (shim day 2026-12-31):
  `TC-123a shim 2026-12-31, expiry 2027-01-14: exit 0  ok`, `TC-123b ... expiry 2027-01-15: exit 1  ok`, `says '14 days'  ok`.
- [x] `tests/run_all_test.sh` and `tests/run_all_count_test.sh` are untouched.

## Known limit (TC-156)

`since` is typed by hand; the machine cannot prove it was not changed. Setting it to today is another way to renew. That cannot be stopped, but it shows on the same line of the PR diff where a reviewer sees it. Reading git history (`git log -S`) is unreliable in a shallow CI clone, so this task does not do it. No test file went red because of the new retry TMPDIR (no BLOCKED).

## Pending for developer-agent

- `.github/workflows/tests.yml` lines 26-28 say "expiry <= 14 days": still true, only incomplete; not touched (decision 2).
- An old three-column line followed by `# comment` gets "since is not a real date" rather than "found 3" (overview, uncertainty 2); still rejected.
- TC-136, TC-153, TC-154, TC-156 are for the reviewer to check in the diff and this ledger.
