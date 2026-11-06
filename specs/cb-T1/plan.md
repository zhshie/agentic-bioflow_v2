# cb-T1 plan: table tests for three untested functions in platform/abf_platform/common.py

Source: cloud-burn tasks.json T1 (shard A, kind code, risk S).

## Goal
`token_from_header`, `offline_after_seconds` and `run_failure_reason` in `platform/abf_platform/common.py`
have no direct test (grep over `platform/tests` finds none). Pin their documented behaviour with table tests.

## Files
- `platform/tests/test_common_untested.py` (new; the only code file)
- `specs/cb-T1/plan.md`, `specs/cb-T1/ledger.md`

## Approach
Pure test additions; the code under test is already right. One parametrized table per function:
- `token_from_header`: empty/None/whitespace, Bearer in any case, missing credential, extra spaces, non-Bearer schemes,
  Basic (valid `@token:` form, wrong user, empty password, bad base64, non-UTF-8, colon inside the token).
- `offline_after_seconds`: env unset, empty, non-numeric, negative, zero, nan, valid integer and fraction, padded value.
  It reads `ABF_AGENT_HEARTBEAT_SECONDS` through `monkeypatch`, so no state leaks.
- `run_failure_reason`: message wins over report, blank message falls back to the report's first non-empty line,
  non-str inputs, control characters collapse to one space, 1000-char cut, nothing -> None.

## RED tests
Mutation proof instead of RED (RULES 5.3): break each function temporarily, show the new tests fail, restore.
Mutants (each restored right after; common.py is unchanged in the commit): bearer scheme compared case-sensitively;
Basic ignores the `@token` user; `_seconds_from_env` accepts non-positive values; offline_after_seconds uses 2 beats;
run_failure_reason skips the control-character scrub, skips the 1000-char cut, prefers the report over the message.

## Done criteria
New file passes on unchanged code; each mutant makes at least one new test fail; scope guard OK; `tests/run_all.sh` green.

## Environment facts
venv at /tmp/cb/venv, `pip install -e platform pytest`; build/ and egg-info removed after install.

## Not doing
No change to `common.py`, `conftest.py` or any HOT/FORBIDDEN path. No fix if a case fails: it would be moved out and recorded as a finding.
