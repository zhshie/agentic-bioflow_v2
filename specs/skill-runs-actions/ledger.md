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
- owed: log-download  downloading a run's log through the platform; the skill reads the work-directory file with fetch.sh.
- owed: run-params  reading a run's launch parameters back from the platform.
- owed: measurements  per-process and per-task memory use and requested resources; the execution trace on disk stays as the source.
- owed: tune-resources  scripts/tune_resources.sh (box-size tuning after a run); step 4 of SUCCEEDED says so.

## Retired tests

Retired assertions: none. No existing test was edited, deleted or loosened; the existing tests that read skills/runs/SKILL.md (runs_report_format_test.sh, jev_test.sh, egress_allow_test.sh, flow_skills_layout_test.sh, off_design_single_path.sh, works_without_host_test.sh, column_output_relay_rule.sh) pass unchanged.

## Fix round (TC-023)

The "Reading a measurement" table and the walltime bullet still told the AI to "relaunch one tier up" or relaunch with more time. They now say a larger box or more time is a new `launch` the person confirms (consistent with owed: resize-relaunch). `tests/skill_runs_uses_actions_test.sh` TC-023 gained a second check that looks at "relaunch" with or without backticks (this adds an assertion; none was loosened).
