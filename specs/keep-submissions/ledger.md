# keep-submissions progress ledger

Maintainer's words (2026-10-18): 送出內容除非使用者刪除不然不刪.

- [x] Rule 1 and 2 (confirm.py): a confirmed row is never cleared by time; void and expired-pending rows still are after 7 days; the constant is `KEEP_UNSENT_SECONDS`. The two pins of R1 (`test_review_fixes.py`, `test_review_fixes_2.py`) and the three fixed tool lists (`test_human_channel.py`, `test_guidance.py`, `test_actions_layer.py`) were changed exactly as R1 says.
- [x] R8 (store.py): `forgotten_at REAL` and `forgotten_by TEXT` on `confirmations` and `jobs`, added by `_add_forgotten_columns` when a platform.db is opened; no new confirmation kind, no CHECK change.
- [x] Rule 3, R6, R7, R9, R10 (confirm.forget_content, actions.forget_check / forget / request_forget): clears bundle and screen of the run's confirmations and the job copy (`args_json` becomes `{"forgotten": true, "bundle": {"run_name": ...}}`); refused for running, lost, not yet in the index, or a queued/claimed job; already forgotten answers 「已經刪除過了 (already deleted)」.
- [x] Terminal `abf-platform forget RUN` (abf_launch/cli.py cmd_forget, screen in build.forget_screen): asks `y`, no `--yes`, no owner check, status check kept. MCP tool `forget` (R2, R11): the client's form only; otherwise the terminal hint, nothing written.
- [x] Docs: docs/PLATFORM.md retention paragraph and the `forget` action; CHANGELOG.

## Hook point for 009e (rule 4)

009e (resume / relaunch) is not on v3, and none of its code was pulled in. Whoever reads a confirmed bundle later must check, before using it, that the content is still there: a confirmation row with `bundle_json IS NULL` and `forgotten_at IS NOT NULL`, or a job whose `args_json` has `"forgotten": true` (the helper `confirm.forgotten_args` writes that shape, and `_named` in confirm.py reads it). That reader must refuse with 「內容已被擁有者刪除 (content deleted by its owner)」, not crash on the missing bundle.

## Owed

- Web parity (R12): `forget` has an MCP tool and a terminal command but no web route. It is owed under `docs/ROADMAP.md:98` (owed parity: every action has an MCP tool and a web route). The web stays read-only here (011a).
- Not asked by the plan, left as it is: a launch the agent refused never reaches the run index, so `forget` answers "still starting" for it (R7 read literally) and its content cannot be forgotten yet; and `jobs._insert_job` still deletes finished job rows 7 days after they finish (the job copy goes by time, the confirmation row does not). Both are for the developer-agent to decide.

## Old-test edits the plan (R1) does not name (fix round, 2026-10-18)

The verifier's TC-093 allows only the places TC-010 and TC-040 name. These edits to old tests are NOT named there. Each is forced by something the plan itself fixes; none can be undone without undoing the plan. They are listed so the plan owner can name them in R1 (or rule otherwise). Nothing was removed or skipped; every one only adds `forget` or a count.

- `test_station_envs.py:520-521` `banned_schema_words` allow-list: adds `forgotten_at`, `forgotten_by`. The scan rejects any column name containing `org`; the plan (R8) and TC-013/027 fix these two column names, and `org` sits inside `forgotten`. This is the only loosening (two exact names allowed).
- `test_station_envs.py:434, 453, 455`: CLI subcommand set and help text gain `forget` (plan: terminal `abf-platform forget RUN`).
- `test_station_envs.py:384`, `test_mcp.py:61,67,93`, `test_launch_e2e.py:183`, `test_launch_platform.py:301,306`, `test_human_channel.py:158`-style lists: tool list gains `forget` (same kind as the three lists R1 names).
- `test_pat.py:383`, `test_oauth_mcp.py:44,329`: tool count 8 becomes 9.

The executor cannot make TC-093 pass by code: removing these edits makes those old tests fail, and renaming the columns breaks TC-013/027. Decision needed from the developer-agent: amend R1 to name these, or rule another way.
