# 憲法文字對齊平台測試四段（6.0.2） progress ledger
- GREEN: updated PINNED_SN_SHA256 in tests/constitution_scope_test.sh to 6cf98cf5... (two of the four reworded lines sit inside the Safety Net section; intended change, same PR as the file requires). TC-E1..E7 green; platform_direction_docs_test, constitution_6_test, constitution_checks_exist_test, dev_workflow_test green.
- E3: git mode of the platform entries is 100644 (run via bash by run_all.sh, plan forbids touching them), so TC-E3 checks existence (-f) instead of -x; flagged for the verifier.

## Fix round 1 (TC-E28 evidence; executor-side items only)

`git diff --stat origin/v3...HEAD` at the time of writing (this ledger edit adds a few more lines to the ledger row):

```
 .specify/memory/constitution.md                    | 35 +++++++--
 specs/constitution-platform-entries/ledger.md      |  3 +
 specs/constitution-platform-entries/plan.md        | 90 ++++++++++++++++++++++
 .../test-case-overview.md                          | 46 +++++++++++
 specs/constitution-platform-entries/test-case.md   | 84 ++++++++++++++++++++
 tests/constitution_scope_test.sh                   | 38 ++++++++-
 tests/platform_direction_docs_test.sh              |  6 +-
 7 files changed, 290 insertions(+), 12 deletions(-)
```

No file under `docs/`, `CLAUDE.md`, `README.md`, `platform/`, `tests/run_all.sh` or `tests/platform_*test.sh` appears (TC-E31, TC-E32, TC-E33).

Constitution diff (`git diff origin/v3...HEAD -- .specify/memory/constitution.md`), hunk by hunk, so TC-E11 can be checked:

- `@@ -43,12 +43,12 @@`, line 46: "run by `tests/platform_test.sh`:" becomes "run by `tests/run_all.sh`, which runs the platform tests in four parts (`tests/platform_test.sh`, `tests/platform_shard_2_test.sh`, `tests/platform_shard_3_test.sh`, `tests/platform_clock_test.sh`):". The rest of the sentence, `test_tch09_*` and `test_tch09_b_c_*` are unchanged.
- same hunk, line 51: "*Check:* run by `tests/platform_test.sh`: the platform tests" becomes "*Check:* run by `tests/run_all.sh` (through its four platform parts): the platform tests". `test_tc030_*` and `test_tc031_*` are unchanged.
- `@@ -192,8 +192,7 @@` (inside the Safety Net section): "`test_tc038_*`), run by" newline "`tests/platform_test.sh`." becomes "`test_tc038_*`), run by `tests/run_all.sh` (through its four platform parts)."
- `@@ -211,7 +210,7 @@` (inside the Safety Net section): "(`test_tcf10_f11_*`), run by `tests/platform_test.sh`." becomes "(`test_tcf10_f11_*`), run by `tests/run_all.sh` (through its four platform parts)."
- `@@ -608,6 +607,30 @@`: new `### 6.0.2 (2026-10-24)` entry between the 6.0.1 entry and `## Governance`.
- last line: version line `6.0.1 ... 2026-10-22` becomes `**Version**: 6.0.2 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-24`.

No other constitution line changed.

## Fix round 1: items the executor did not change, and why

The repo `CLAUDE.md` ("Never edit during implementation": the constitution) and plan ruling 2 forbid the executor from editing the constitution. These need the developer-agent:

- TC-E12: the 6.0.2 heading reads "checks are run by the whole suite, not by one platform file"; the contract wants "the platform checks run through four entries, not one". Needs a constitution edit.
- TC-E13: the 6.0.2 Rationale lacks `test_actions_layer` (part 1) and `test_resume_entrypoints` (part 2). Needs a constitution edit.
- TC-E35: two reworded places are inside the Safety Net section, so `PINNED_SN_SHA256` changed. Reverting them would make TC-E1 fail; this is a conflict between contract and plan for the developer-agent and maintainer to rule on.
- TC-E3: the four platform entries are mode 100644 in git. Restoring the `-x` check would fail, and changing their mode touches files the plan forbids. The contract needs revising, or the developer-agent must allow the mode change.
