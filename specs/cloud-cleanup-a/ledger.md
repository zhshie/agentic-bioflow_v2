# store.py：CHECK、launches.work_cleaned_at、migration progress ledger

- [x] store.py: `confirmations.kind` CHECK takes `clean_work`; `jobs.kind` CHECK takes `clean_work` (last) and the write lock covers it; `launches.work_cleaned_at REAL` (last, nullable).
- [x] Migration: `_migrate_confirmation_kinds` (foreign keys off, one `BEGIN IMMEDIATE`, copy by shared column names, drop, rename, `foreign_key_check` must be empty, rollback on any failure, `finally` restores foreign keys and isolation level; runs after `_add_confirmation_state`/`_add_forgotten_columns`), `_jobs_kinds_current` (jobs rebuilt unless it has both `read_task_log` and `clean_work`), `_add_cleanup_column`.
- [x] New `platform/tests/test_cleanup_store.py` (28 tests, TC-001..033, 050, 051).
- Read before the rebuild: https://sqlite.org/lang_altertable.html ; `sqlite3.sqlite_version` in WSL Python 3.10.6 = 3.37.2 (>= 3.7.16).
- Real old-database copy: not available to the executor (no access to the maintainer desktop platform.db); developer-agent runs it on the desktop before merging (open once; SELECT * of every table before/after, `PRAGMA integrity_check`, `PRAGMA foreign_key_check`).

## Existing assertions updated (for the PR description: before / after / why)
- `test_http_site_samplesheet.py` `SCHEMA_SHA256`: 56f767...662f9d -> 0b6aad18...dfdbc (test's own algorithm; CHECKs and a column changed).
- `test_cloud_cost.py` (`test_nothing_stops_a_running_job_and_no_policy_channel_exists`): job kinds list + `clean_work`; confirmations kind string includes `'clean_work'`.
- `test_station_platform.py`: confirmation `c3` of kind `clean_work`, `("clean_work", "c3")` inserted, `declared` set + `clean_work`.
- `test_keep_submissions.py`: line with `CHECK (kind IN (...))` includes `'clean_work'`; TC-109 `drops` also drops/re-checks `work_cleaned_at`.
- `test_resume_scope.py`: the STATE_SCHEMA count string includes `'clean_work'`.
- `test_gcb_launch.py`: launches columns + `work_cleaned_at`; test renamed from "...columns_are_unchanged".
- NOT IN THE PLAN, found by the full-suite run: `test_launch_platform.py` `test_tc055_launches_holds_the_facts_of_the_handover_and_no_state` lists the launches columns; `"work_cleaned_at"` added to that list (same kind of change as the gcb one; the plan said this file was unaffected).

## git diff --stat (base 7f73157, before this line was added)
     platform/abf_platform/store.py               | 107 +++++-
     platform/tests/test_cleanup_store.py         | 538 +++++++++++++++++++++++++++
     platform/tests/test_cloud_cost.py            |   4 +-
     platform/tests/test_gcb_launch.py            |   4 +-
     platform/tests/test_http_site_samplesheet.py |   2 +-
     platform/tests/test_keep_submissions.py      |   4 +-
     platform/tests/test_launch_platform.py       |   2 +-
     platform/tests/test_resume_scope.py          |   2 +-
     platform/tests/test_station_platform.py      |   5 +-
     specs/cloud-cleanup-a/ledger.md              |  15 +
     10 files changed, 653 insertions(+), 30 deletions(-)

## Also not in the plan (the first full-suite run found them; same one-word change, `work_cleaned_at` appended to a pinned launches column list)
- `test_pipeline_launch.py` `test_no_table_or_column_changed` (launches column list).
- `test_web_actions.py` `SCHEMA` entry `platform.launches` (used by `test_tc063_no_schema_change`).
- `test_resume_lineage.py` `NEW_COLUMNS` (used by TC-122 and TC-125/126 column-order checks) and `test_station_launch.py` `LAUNCHES_COLUMNS` (its comment says this task does not touch `_LAUNCHES_TABLE`; it now does): `"work_cleaned_at"` appended. Found by the second full-suite run.
