# keep-submissions progress ledger

Maintainer's words (2026-10-18): 送出內容除非使用者刪除不然不刪.

- [x] Rule 1 and 2 (confirm.py): a confirmed row is never cleared by time; void and expired-pending rows still are after 7 days; the constant is `KEEP_UNSENT_SECONDS`. The two pins of R1 (`test_review_fixes.py`, `test_review_fixes_2.py`) and the three fixed tool lists (`test_human_channel.py`, `test_guidance.py`, `test_actions_layer.py`) were changed exactly as R1 says.
- [x] R8 (store.py): `forgotten_at REAL` and `forgotten_by TEXT` on `confirmations` and `jobs`, added by `_add_forgotten_columns` when a platform.db is opened; no new confirmation kind, no CHECK change.
- [x] Rule 3, R6, R7, R9, R10 (confirm.forget_content, actions.forget_check / forget / request_forget): clears bundle and screen of the run's confirmations and the job copy (`args_json` becomes `{"forgotten": true, "bundle": {"run_name": ...}}`); refused for running, lost, not yet in the index, or a queued/claimed job; already forgotten answers 「已經刪除過了 (already deleted)」.
- [x] Terminal `abf-platform forget RUN` (abf_launch/cli.py cmd_forget, screen in build.forget_screen): asks `y`, no `--yes`, no owner check, status check kept. MCP tool `forget` (R2, R11): the client's form only; otherwise the terminal hint, nothing written.
- [x] Docs: docs/PLATFORM.md retention paragraph and the `forget` action; CHANGELOG.
- [x] R15 (actions/__init__.py `forget_check`): "still starting" means the launch job is queued or claimed; a launch whose job was refused, failed (`error`) or `expired` and never reached the run index can be forgotten.
- [x] R14: the old-test edits R14 names (test_station_envs.py allow-list plus one test that `forgotten_org` still fails; CLI set, help and tool lists gain `forget`; tool counts gain one).

## Follow-up after PR #133 review (F1 to F5)

- [x] F1: `origin/v3` merged into the branch with a plain merge (commit e4c967f, nothing rebased, nothing force-pushed). 14 files conflicted; both sides were kept: the Forget and the Resume and relaunch sections of docs/PLATFORM.md, `forget_screen` and the 009e attempt screens in build.py, the `forget`, `resume` and `relaunch` subcommands and tools, and the 009e shard lists of tests/platform_test.sh with `test_keep_submissions.py` added to the last shard (fixed in the commit after the merge).
- [x] F2: resume and relaunch refuse a forgotten run with 「內容已被擁有者刪除 (content deleted by its owner)」, nothing queued: in `build._predecessor` (so the terminal commands and the MCP tools, after the owner check, so somebody else still gets "not found"), and in `jobs._lineage` (the queue check, so a yes given before the forget cannot start it; a pending request approved later is made void). `jobs.run_forgotten` reads it from the rows, for the run and every run it was made from. The hook point noted earlier (a confirmation with `forgotten_at`, or a job whose `args_json` has `"forgotten": true`) is exactly what it reads.
- [x] F3: every list and count of tools and actions is the union of the 009e tools and `forget`: eleven tools (`list_runs`, `get_run`, `list_compute_envs`, `get_compute_env`, `list_agents`, `list_site_files`, `launch`, `cancel`, `resume`, `relaunch`, `forget`), in the tests, in docs/PLATFORM.md ("Eleven tools"), in the MCP `instructions` (guidance.FIXED_SENTENCE), in the command set and help text. No count was lowered.
- [x] F4: `forget` is refused (「這個 run 還在準備中，不能刪除」) while the launch job went out (`done`) and the index does not know the run yet, until the index sees it or 24 hours after the job ended (`actions.FORGET_WAIT_SECONDS`, worked out from `jobs.finished_at`; nothing stored). A refused, failed or expired launch stays forgettable at once.
- [x] F5: the confirmation row of a terminal launch (and cancel) holds the bundle and the screen text (`confirm._confirm`, `actions.launch` and `cancel` keep their signatures and store the bundle; abf_launch/cli.py then calls `actions.keep_screen` to add the text the person was shown (not atomic with the confirmation, which is fine: the bundle is the part the hash binds)); `confirm.describe` still does not show a TERMINAL row on the page. 009e reads the content from the confirmation first (`jobs.launch_content`, used by `build._predecessor`), and from the launch job only for a row made before this change; 「太久了…」 is said only then. Link between a launch row and its confirmation: the launch job names it; when the job is gone, the confirmed launch made at the very moment the hand-off row says it was confirmed (`jobs.launch_confirmation`). No column was added for it.

## Owed

- Web parity (R12): `forget` has an MCP tool and a terminal command but no web route. It is owed under `docs/ROADMAP.md:98` (owed parity: every action has an MCP tool and a web route). `resume` and `relaunch` (009e) have no web route either and are owed the same way: the owed list holds `forget`, `resume` and `relaunch`. The web stays read-only here (011a).

## Old-test edits the plan does not name (fix rounds)

Each only adds `forget`, a count, or moves pre-data to the old format; no assertion was removed, loosened or skipped.

- `test_station_envs.py` `banned_schema_words` allow-list: adds `forgotten_at`, `forgotten_by` (the scan rejects names containing `org`, and `org` sits inside `forgotten`); a made-up `forgotten_org` still fails, with one assertion that proves it. CLI set, help text and tool lists gain `forget` next to 009e's `resume` and `relaunch`.
- `test_pat.py`, `test_oauth_mcp.py`, `test_mcp.py`, `test_launch_e2e.py`, `test_launch_platform.py`, `test_human_channel.py`, `test_guidance.py`, `test_actions_layer.py`: tool lists gain `forget`; counts are v3's plus one (10 becomes 11).
- `test_resume_entrypoints.py::test_tc132_*`: the tool list gains `forget` (F3).
- `test_resume_scope.py::test_tc152_*`: the constant `confirm.KEEP_CONTENT_SECONDS` is named `KEEP_UNSENT_SECONDS` (plan rule 2).
- F5, forced: the two 009e "too old" tests (`test_resume_platform.py` TC-053/054 and the real-clean-up one) now make the first launch an old-format row first (`old_format(rig)`: the TERMINAL confirmation's bundle and screen set to NULL), because a terminal launch keeps its content in its confirmation now. Their assertions are word for word what they were.

## Known limits (R16)

Kept as they are; the maintainer may revisit any of them:

1. A `jobs` row's own copy is still removed with the row 7 days after the job ends (`jobs._insert_job` prunes). The confirmation keeps the content whatever the channel, so the submission is kept. Only a row made before F5 (the old format: a terminal launch of an older version) holds its content only in the job copy and the run folder.
2. `result_json` and `late_result_json` are results, not submission content: `forget` leaves them.
3. No web delete (owed web parity, R12 above).

## Rulings F7 to F12

- [x] F7: `actions.forget_check` refuses "still starting" only while the launch job row exists; with the job row pruned and the run not in the index, forget is allowed. `confirm.forget_content` also finds the launch confirmation through `jobs.launch_confirmation` when the job link is gone. Test: TC-147.
- [x] F8: `forget` is in the ask list of `extensions/claude-code-kit/settings.json`; `test_resume_entrypoints.py::test_tc137_*` pins the five names (the four old assertions are unchanged).
- [x] F9: the two 009e "太久了" tests were changed in their setup only: `test_resume_platform.py` TC-053/054 and the real-clean-up one call `old_format(rig)` first; their assertions are word for word what they were.
- [x] F10: `confirm.forget_content` voids every pending resume or relaunch request whose `of_run` is the forgotten run (content cleared, `forgotten_at` set); other runs' requests are untouched. The job-time check of F2 stays. TC-131 now expects the request void at once.
- [x] F11: a terminal-confirmed cancel keeps its bundle and screen text (`cmd_cancel` calls `actions.keep_screen`); tests TC-162 to TC-165.
- [x] F12: web parity for `forget` stays owed (see Owed above).
