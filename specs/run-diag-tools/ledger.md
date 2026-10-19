# Platform tools the runs skill needs: read_task_log, task folder, cancel facts progress ledger

Plan: `specs/run-diag-tools/plan.md` (rulings D1-D5). Test cases: `test-case.md`. New tests: `platform/tests/test_run_diag_tools.py`.

## Tasks

- [x] 1. `get_run` returns `workdir` for a failed task when the nf-tower task event carries it. `failed_tasks.workdir` column (store.py, with the upgrade of an older index.db), written by receiver.py, shown by status.py; absent when missing; rebuild.py unchanged (a rebuilt run has none). TC-001..007.
- [x] 2. `read_task_log(run_name, task, which)`: action `actions.read_task_log`, MCP tool of the same name (mcp_server.py), job kind `read_task_log` (jobs.py `enqueue_task_log`, `cap_log`, `clean_result`), table-rebuild migration of the jobs CHECK (store.py `_migrate_jobs_kinds`), agent handler `platform/abf_station/readlog.py` whitelisted in handlers.py (`JOB_KINDS`, `ARG_KEYS`). Refusals: bad `which`, no recorded workdir (D2), no launch record, agent offline, file not found. Cap 200 lines / 64 KB enforced on the agent and again on the platform. TC-101..121.
- [x] 3. `get_run` returns `cancel_requested_at` (ISO, milliseconds) exactly when `launches.cancel_requested_at` is set (the fact `abf-platform launches` prints; jobs.py `cancel_requested_at`). No new status. TC-201..207.
- [x] 4. Registration and lists: the action layer parity tests, the tool lists and counts of the MCP tests (below), `docs/PLATFORM.md` tool lines, the one fixed sentence of `guidance.py` ("Seven tools ... read-only"). TC-301..309.

## Existing tests changed (D1), each: old expectation -> new expectation, and why

| Test | Old | New | Why |
|---|---|---|---|
| D1(a) `test_followup3.py` `test_tcf3_03_...` (fail_run, nf2510_fail, nf2510_retry) | key set of a failed task `{name, exit_code, error_message}` | `{name, exit_code, error_message, workdir}`; every other assertion of that test unchanged | the recorded task events carry `workdir`, so the failed task now has it |
| D1(b) `test_nextflow_e2e.py` `_compared` / `_same_runs` | the failed tasks of the live run and the rebuilt run compared whole | `_NOT_REBUILT_TASK_FIELDS = {"workdir"}` is left out of each failed task before comparing; all other compared items and fields unchanged; a new assertion that a rebuilt failed task has no `workdir` | rebuild.py reads the trace file, which has no full task folder. Deviation from the wording of D1(b): the plan says `_NOT_REBUILT = {"workdir"}`, but `_NOT_REBUILT` already exists in that file (a tuple of run-level keys, `("failure_reason",)`, still asserted absent) so it is kept and the new set has its own name |
| D1(c) `test_actions_layer.py` `BASELINE`, `READ_NAMES` | six read tools; `get_run` description without the two new facts | seven (`read_task_log` added, sorted position); `get_run` description is the new text; the other five tools identical byte for byte; comparison still a whole-JSON equality | new tool, new `get_run` description (plan, Goal 1 and 3) |
| D1(c) `test_mcp.py` (2 lists), `test_oauth_mcp.py`, `test_human_channel.py`, `test_launch_platform.py`, `test_keep_submissions.py`, `test_launch_e2e.py`, `test_resume_entrypoints.py` | sorted tool-name lists of 11 names | the same lists with `read_task_log` (12 names) | new tool |
| D1(c) `test_pat.py`, `test_oauth_mcp.py` (`test_tce01`) | `len(tools) == 11`; `len(tools) == 6` (tool bodies in `build_server`) | `== 12`; `== 7` | one more tool, one more tool function |
| D1(c) `test_launch_platform.py` `test_tc010_...` (banned argument names of read-only tools) | no read-only tool may have an argument named `run_name` (among `confirm`, `yes`, `kind`, `command`, `launch`, ...) | the same set, except that `read_task_log` alone may have `run_name`; all other banned names still apply to it | the plan fixes the signature `read_task_log(run_name, task, which)` |
| D1(c) `test_guidance.py` | `SIX_TOOLS` (six names) | renamed `READ_TOOLS`, seven names (`read_task_log` added) | new read-only tool; the name said "six" |
| D1(c) `test_station_envs.py` | `want` (six read-only names) | plus `read_task_log` (so it is also checked read-only on stdio and HTTP) | new tool |

Consequences of D4 (the new job kind) that D1 did not list; each only adds the new kind, nothing is relaxed:

| Test | Old | New | Why |
|---|---|---|---|
| `test_launch_platform.py` (the upgrade test, `kinds`; `jobs.KINDS` test) | five job kinds | six (`read_task_log` added) | D4: the jobs CHECK takes the new kind |
| `test_resume_scope.py` (`jobs.KINDS ==`) | five-kind tuple | six-kind tuple | same |
| `test_station_platform.py` (CHECK of a new file: kinds that go in, and the declared set) | five kinds | six kinds | same |

## Owed on the web (not done here; out of scope)

The web pages (`platform/abf_platform/web.py`) show none of these yet; they are owed:

- `read_task_log` (a way for a person to read the end of a failed task's log from the run page),
- `workdir` of a failed task on the run page,
- `cancel_requested_at` on the run page (so a person can tell "cancelled" from "failed").

## Not changed on purpose

`skills/` (PR #136 updates it after this lands), `platform/abf_platform/web.py`, `CHANGELOG.md`, `docs/TESTING.md`, and every document other than the tool lines of `docs/PLATFORM.md`.
