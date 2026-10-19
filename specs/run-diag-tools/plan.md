# run-diag-tools: what the runs skill needs from the platform

Source: maintainer 2026-10-18 「都照你的建議」 = add the missing platform tools before switching skills (draft PR #136). ROADMAP stage 2 already lists `read_task_log` among the 009 MCP tools. B tier (new tools users' AI will call).

## Goal: three read-only, owner-only tools (same 'not found' answer for another user's run as get_run)
1. `get_run` additionally returns, for each failed task, its work folder path on the site (`workdir`) when the trace carries it (the nf-tower task event has `workdir`; store it with the failed task, no second run state: tests/no_second_run_state_test.sh stays green). Missing -> field absent, never guessed.
2. `read_task_log(run_name, task, which)` with which in {err, out, log} (`.command.err`, `.command.out`, `.command.log`): asks the run's station agent to read that one file from the task's workdir, returns the last N lines (cap 200 lines / 64 KB), read-only; refused when the task has no recorded workdir or the agent is offline (say which). Follow how `list_site_files` asks the agent today (read actions/__init__.py, agents.py, jobs.py); reuse that path, do not open a new channel. The agent side must confine the read to that workdir (no `..`, no symlink out) — mirror list_site_files' confinement.
3. Cancel facts: `get_run` returns `cancel_requested_at` when a confirmed cancel request exists for that run (the fact `abf-platform launches` already prints). Lets the skill tell 'cancelled' from 'failed'.
Each new or extended tool: MCP tool in mcp_server.py with the same name as the action; the actions-layer parity tests and tool lists updated (no count lowered); listed as owed on the web (ledger).

## Tests (write first): platform/tests/test_run_diag_tools.py
workdir stored and returned for failed tasks; absent when the event lacks it; read_task_log returns capped tail via a fake agent; path escape refused; another user's run -> not found; offline agent -> clear refusal; cancel_requested_at present only after a confirmed cancel.

## Out of scope
skills/ (PR #136 updates after this lands), web, CHANGELOG.md, docs other than the PLATFORM.md tool list lines for these tools.

## Rulings after contract round 1 (developer-agent, 2026-10-18)
- D1 Existing tests this change must update (each listed in specs/run-diag-tools/ledger.md with old expectation, new expectation, reason): (a) platform/tests/test_followup3.py:77 — the failed-task key set gains `workdir` on fail_run, nf2510_fail, nf2510_retry; (b) platform/tests/test_nextflow_e2e.py `_COMPARED` / `_same_runs` — add a named exclusion `_NOT_REBUILT = {"workdir"}` because rebuild.py reads the trace file, which has no full workdir; a rebuilt run simply has no workdir; (c) platform/tests/test_actions_layer.py `BASELINE` and the tool lists in test_mcp.py, test_oauth_mcp.py, test_pat.py, test_human_channel.py, test_guidance.py gain `read_task_log` and the new get_run description. No count lowered, no assertion removed without replacement.
- D2 `task` = the task name exactly as get_run shows it in failed_tasks. A name that is not one of the run's failed tasks is refused as "no recorded workdir for this task".
- D3 `cancel_requested_at` = exactly the fact `abf-platform launches` prints (launches.cancel_requested_at, written when the cancel job finished ok). Confirmed-but-queued or refused cancels do not set it.
- D4 New job kind `read_task_log`: extend the jobs.kind CHECK with a table-rebuild migration following store.py:352; an older platform.db opens, keeps its rows and can take the new job (test). Add the agent handler and whitelist its kind and argument keys in abf_station/handlers.py; the agent confines the read to the recorded workdir (no `..`, no symlink out), like list_site_files.
- D5 Other refusals: a run not launched from this platform (no launches row) -> "no station agent is known for this run"; file missing in the workdir -> "file not found in the task folder". The cap (200 lines / 64 KB, last lines kept) is enforced on the agent and re-checked on the platform; the answer says when it was cut. The tool description warns, like list_site_files, that log text goes to the model the user chose.
- Files: also platform/abf_station/handlers.py, platform/abf_platform/jobs.py, and the tests named in D1.
