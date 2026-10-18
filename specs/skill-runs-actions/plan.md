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
