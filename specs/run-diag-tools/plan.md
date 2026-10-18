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
