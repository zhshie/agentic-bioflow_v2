# #93 item 6: the runs skill calls the platform's MCP tools instead of tw progress ledger

- [x] Failing test first: tests/skill_runs_uses_actions_test.sh (RED commit), with the tw-era skill kept as tests/fixtures/runs_skill/SKILL.tw-era.md so the test proves it goes red on it (TC-014).
- [x] skills/runs/SKILL.md: state read through `list_runs` and `get_run`; `cancel`, `resume`, `relaunch` described as requests the person confirms; no `tw` left. Frontmatter, six status branches, reporting format, Jev routes and site scripts (why_pending.sh, egress_ctl.sh, fetch.sh) unchanged.

## Decisions the plan did not spell out

- Status mapping: v3 `get_run` reports running, succeeded, failed, lost. SUBMITTED stays as a branch (the six headings are pinned by runs_report_format_test.sh) but is reached from a launched run that is not listed yet or shows no task done; `lost` goes to UNKNOWN (said verbatim); a cancelled run reads as failed on v3, and the CANCELLED branch still asks whether someone cancelled it.
- The work board is `list_runs` with codes by position, computed fresh; scripts/runs_board.sh is no longer called by this skill (the script stays: scripts are out of scope).
- Succeeded step 1 uses `list_agents` instead of agent_ctl.sh.
- The unavailable steps keep their place in the skill and say "not available on v3 yet (owed: <id>)"; the test requires the ids in the skill and the ids below to be the same set.

## Owed (steps with no v3 equivalent yet; no tool was invented)

- owed: task-health  one-command stuck-task check (scripts/task_health.sh reads through the Seqera CLI); the skill uses get_run plus why_pending.sh by hand.
- owed: resize-relaunch  relaunch into a changed box or time (scripts/relaunch_with_override.sh); `relaunch` cannot change settings, so the skill says a new `launch` is the route.
- closed (S8, was owed: log-download): the skill reads a failed task's log with `read_task_log`, not fetch.sh.
- owed: run-params  reading a run's launch parameters back from the platform.
- owed: measurements  per-process and per-task memory use and requested resources; the execution trace on disk stays as the source.
- owed: tune-resources  scripts/tune_resources.sh (box-size tuning after a run); step 4 of SUCCEEDED says so.

## Retired tests

Retired assertions: see "Rulings S7 to S11" below; before that none. No existing test was edited, deleted or loosened; the existing tests that read skills/runs/SKILL.md (runs_report_format_test.sh, jev_test.sh, egress_allow_test.sh, flow_skills_layout_test.sh, off_design_single_path.sh, works_without_host_test.sh, column_output_relay_rule.sh) pass unchanged.

## Fix round (TC-023)

The "Reading a measurement" table and the walltime bullet still told the AI to "relaunch one tier up" or relaunch with more time. They now say a larger box or more time is a new `launch` the person confirms (consistent with owed: resize-relaunch). `tests/skill_runs_uses_actions_test.sh` TC-023 gained a second check that looks at "relaunch" with or without backticks (this adds an assertion; none was loosened).

## Rulings S1 to S6 round

- S1: each of the six branch headings keeps one `Mapping:` line (SUBMITTED = launched but not in `list_runs`, max 3 checks, "已送出、還沒開始"; RUNNING/FAILED/SUCCEEDED = the platform status; CANCELLED = failed plus a cancel request sent; UNKNOWN = lost or any other). Open question for the maintainer: the "cancel request was sent" fact is in `abf-platform launches`, not in the ten MCP tools, so the skill names no tool for it.
- S2: the RUNNING "reversible" sentence now says `resume` (same folder, cache); CANCELLED paragraph split so `relaunch` is only "new folder, from the start".
- S2 fix round: the end of the RUNNING section still said a relaunch costs "one more spell in the queue, not the run over again" (a tw-era line from when relaunch used -resume). It now says a relaunch starts from the start in a new folder. `tests/skill_runs_uses_actions_test.sh` TC-088 gained a paragraph-level check for that wording (an added assertion, none loosened).
- S3: the .command.err step and the Jev triage step say "v3 尚未提供 task 的資料夾路徑" and no path is built.
- S4: unchanged from the first round; the scripts that use the Seqera CLI inside (task_health.sh, tune_resources.sh, relaunch_with_override.sh) are marked and owed below; runs_board.sh and agent_ctl.sh are replaced by `list_runs` / `list_agents`. No script touched.
- S5: one step added to docs/TESTING.md (step 6 of the 009e section).
- S6: tests/column_output_relay_rule.sh and tests/jev_test.sh were not edited and pass.
- closed (S7, was owed: task-folder-path): the skill takes the task folder from `get_run`'s `workdir`.

## Fix round (TC-030, ce_apply.sh)

- owed: ce-apply  fixing a compute environment's resource contract (scripts/ce_apply.sh calls `tw compute-envs export/import/view`); the resource-floor NEVER branch now says it is not available on v3 yet and tells the AI to report the mismatch instead of running the script. Open question for the maintainer: is there a v3 way to change the compute environment, or should one be added as a platform tool?
- `tests/skill_runs_uses_actions_test.sh`: the script-name list in TC-030 gained `ce_apply`, and a bullet-by-bullet TC-030 check was added (the old paragraph-level check could not see a bullet inside a list that elsewhere says "not available on v3 yet"). Added assertions only; none loosened.

## Fix round (TC-023, params)

- `skills/runs/SKILL.md` `params` branch: "correct or remove that option, then relaunch" is now "a new analysis: ask through `launch` with the corrected parameters, the person confirms; `relaunch`/`resume` cannot change parameters" (relaunch keeps the first launch's samples and parameters). The cancel/resume sentence near the end was reworded in plain English ("can be continued by its name alone"), same meaning.
- `tests/skill_runs_uses_actions_test.sh`: one added TC-023 check (no relaunch/resume line says parameters or options can be changed); it was red on the old line first. Nothing loosened.

## Rulings S7 to S11 round (#138 merged into v3)

- S7/S8: `skills/runs/SKILL.md` takes the failed task's folder from `get_run`'s `workdir` and reads its log with `read_task_log` (`which` err, then out, then log); three refusals (no workdir, not launched from this platform, agent offline) each have a one-line fall-back; only a task with no `workdir` makes the skill ask the person. Jev triage runs for the first failing task that has a `workdir`; the returned text is saved to a temporary file for `jev.sh triage --err`, then deleted.
- S9: CANCELLED mapping rests on `cancel_requested_at`; RUNNING and CANCELLED say a cancel was already asked for (time in Asia/Taipei) and do not offer another `cancel`.
- S10: the `input` fix says a corrected samplesheet is a new launch, not `relaunch`.
- S11: owed list is 6 items (task-health, resize-relaunch, run-params, measurements, tune-resources, ce-apply).
- Retired tests (Rule 4, TC-111): in `tests/skill_runs_uses_actions_test.sh` the S3 assertions TC-089 (task folder path said missing in 2 places, in the .command.err step, in the Jev step) and TC-091 (task-folder-path ledgered and tagged), and the TC-090 ban on any backticked `workdir`, no longer apply because S7/S8 closed those owed items. Replaced by TC-100 (wording gone), TC-101, TC-102, TC-103, TC-104, TC-105, TC-106 (workdir, read_task_log, refusals), TC-110 (exactly 6 owed) and a reworded TC-090 (only `workdir`, no invented field or hashed path). The TC-012 name check also allows the field name `cancel_requested_at`.
- Open question for the maintainer: the `.exitcode` file cannot be read by `read_task_log` (err, out, log only); the "no `.command.log` and no `.exitcode`" branch is unchanged.

## Fix round (TC-094, TESTING.md step 6)

- `docs/TESTING.md` step 6 (the one line this PR adds, still "1 0" for TC-097): it now says the AI reads a failed task's log with `read_task_log`, the task folder coming from `get_run`'s `workdir`; the "v3 尚未提供" example is now "the params a run was started with", no longer a task's folder path.
- `tests/skill_runs_uses_actions_test.sh`: one added TC-094 check (step names `read_task_log`, no "task's folder path"); red first. Nothing loosened.
