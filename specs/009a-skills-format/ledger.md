# 009a-skills-format progress ledger

- [x] RED: tests/flow_skills_layout_test.sh + tests/lib/flow_skills.sh written; before the move it failed 12 checks (a, b via missing files, d commands/ present, e, f stale paths). Commit "RED: ...".
- [x] Move: `git mv commands/<n>.md skills/<n>/SKILL.md` x5, `name:` added as first key, path pointers updated. `git diff -M --summary`: five renames, each 99%.
- [x] skills/operational/SKILL.md: path pointers only (`skills/<command>/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}/skills/<command>/SKILL.md`, `skills/runs/SKILL.md`, `skills/*/SKILL.md`). Layout test (e) checks the generic spelling plus runs literal and that all five files resolve (operational only ever named runs literally; naming all five would add text).
- [x] scripts/: echo/printf and comment strings only. hooks/ untouched (comments there still say commands/, protected).
- [x] Tests: flow-file loops now use tests/lib/flow_skills.sh and fail if fewer than 5 files were read (commands_resolve_their_own_paths, commands_scope_tw_to_the_workspace, skill_requires_intro_test, command_layer_is_site_neutral); skill_portability_test shape checks run over all six skills, heading/H3/LAB_AGENTS stay operational-only; works_without_host tar list drops `commands`; no_hardcoded_paths / scripts_name_their_alternative drop commands; comment-only mentions reworded. confirm_launch_test.sh unchanged (gate fixture).
- [x] Docs: CLAUDE.md:26, docs (PRINCIPLES, TESTING incl. new section "When a release moves the flow files", others), marketplace.json description, CHANGELOG line.
- [x] `claude plugin validate .`: "Validation passed with warnings" (warnings: unquoted ${CLAUDE_PLUGIN_ROOT} in hooks, README has no install line; both pre-existing, not in scope).
- [x] platform/tests/test_scope.py:65 keeps `commands/` in its regex (harmless path classifier), as planned.
