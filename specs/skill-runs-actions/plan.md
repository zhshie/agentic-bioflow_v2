# skill-runs-actions: the runs skill calls the actions

Source: issue #93 item 6 ('Skill content per skill calls the actions; each retires its tw-era tests and scripts (B tier, one PR per skill)'), ADR 0006 (four entries, one action layer), docs/PLATFORM.md, docs/INSTALL.md. First skill of the series: `runs` (check on, debug, deliver a run). B tier: it changes what the AI does for the user.

## Goal
In `skills/runs/SKILL.md`, every step that today reads run state through `tw` (Seqera CLI; 18 mentions) uses the abf platform's MCP tools instead: `list_runs`, `get_run` (status, task counts, failure_reason), and for actions `cancel`, `resume`, `relaunch` (each only asks; the person confirms on a human channel - never describe the AI as confirming). Steps that read files on the site keep their existing site scripts (scripts/on_site.sh etc.) unless an MCP tool covers them (`list_site_files`).

## Rules
1. Read docs/PLATFORM.md and platform/abf_platform/mcp_server.py for the exact tool names and arguments; name only tools that exist on v3.
2. Remove `tw` from the skill's instructions. If a step has no platform equivalent yet (e.g. something only Seqera offered), keep the step but say plainly it is not available on v3 yet, and list it in the ledger as owed - do not invent a tool.
3. Keep the skill's structure, triggers and user-facing tone; change only how state is read and actions are requested.
4. Retire tests that only pin the tw-era wording of this skill: each retired assertion must be replaced by one that pins the new behaviour, or listed in the ledger with the reason it no longer applies. No other skill or script is changed in this PR; scripts still used by other skills stay.

## Tests (write first)
- A test (new, e.g. tests/skill_runs_uses_actions_test.sh) that fails today: skills/runs/SKILL.md contains no `tw ` command invocation; every MCP tool name it mentions in backticks exists in mcp_server.py; it mentions get_run and list_runs; wherever it mentions cancel/resume/relaunch it also says a person confirms.
- tests/run_all.sh stays green; existing skill tests (flow_skills_layout_test.sh, skill_portability_test.sh, skill_names_command_file_test.sh, commands_scope_tw_to_the_workspace.sh etc.) either stay green or are updated per rule 4.

## Out of scope
Other skills (one PR each, later). platform/ code. hooks/. CHANGELOG.md is NOT edited (other lanes). docs/PLATFORM.md not edited.

## Rulings after acceptance round (developer-agent, 2026-10-18)
- S1 Status mapping (v3 get_run/list_runs only return running, succeeded, failed, lost). Keep the six branch headings (tests pin them) and put one mapping line under each: SUBMITTED = the launch was confirmed but the run is not in `list_runs` yet (say "已送出、還沒開始", check again later; never wait forever — after 3 checks tell the person); RUNNING = running; FAILED = failed; SUCCEEDED = succeeded; CANCELLED = failed whose facts say a cancel was sent (Nextflow reports a cancelled run as failed, docs/PLATFORM.md); UNKNOWN = lost (three heartbeats silent) or any other value.
- S2 Fix the contradiction: resume = same folder, finished tasks come back from the cache; relaunch = new folder, from the start. Correct the RUNNING section's sentence.
- S3 get_run gives no work-folder path for a failed task. Where the skill needs `.command.err` / Jev triage input, say plainly "v3 尚未提供 task 的資料夾路徑" and list it in the ledger as owed (a platform tool to add later). Do not invent a path.
- S4 Agree with the verifier's reading: steps that call scripts which use `tw` internally (task_health.sh, tune_resources.sh, relaunch_with_override.sh, runs_board.sh, agent_ctl.sh) stay, each marked "v3 尚未提供" and listed as owed. The scripts are not changed here.
- S5 Add one manual step to docs/TESTING.md under the runs/009e section: ask the AI, following the new skills/runs/SKILL.md, about one failed and one running run on a test platform; check it uses list_runs/get_run, never `tw`, and that every cancel/resume/relaunch waits for the person's yes.
- S6 Keep tests/column_output_relay_rule.sh and tests/jev_test.sh anchors green; if a pinned name is removed, update that test per rule 4 and log it in the ledger.

## Rulings, 2026-10-19 (after #138 merged into v3)

The maintainer chose "platform tools first"; #138 is now in v3. It adds `read_task_log(run_name, task, which)` (end of `.command.err|out|log` of one failed task, read-only), a `workdir` per task in `get_run`, and `cancel_requested_at` on a run.

- S7. Owed item **task-folder-path** is closed: the skill takes the task folder from `get_run`'s `workdir`. Remove the "v3 尚未提供 task 的資料夾路徑" wording at both places (around l.235 and l.242); the per-run check runs whenever `workdir` is present, and only falls back to asking the person when `get_run` has no `workdir` for that task (say so in one plain sentence).
- S8. Owed item **log-download** is closed: the skill reads the failed task's log with `read_task_log` (`which` = err first, then out/log if err is empty), not with `scripts/fetch.sh`. Keep the refusals of `read_task_log` (no workdir, not launched from this platform, agent offline) as plain one-line fall-backs.
- S9. Cancel: when a run has `cancel_requested_at`, the skill says a cancel was already asked for (with the time, Asia/Taipei) and does not offer another `cancel`.
- S10. The `input` branch (around l.332): "correct the samplesheet row, then relaunch" contradicts S1 (relaunch reuses the same samplesheet and params). Reword: a corrected samplesheet means a **new launch** (the launch skill / `launch`), not `relaunch`; `relaunch` is only for re-running the same inputs.
- S11. The ledger's owed list drops task-folder-path and log-download (6 items remain). The other "not available on v3 yet" items stay as they are.
- S12. Re-grade the whole contract; TC-023 (params route) was fixed in 2d4bab2 and must be graded again.
