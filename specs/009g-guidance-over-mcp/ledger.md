# Ledger: 009g-guidance-over-mcp


## RED (before any implementation)

`pytest tests/test_guidance.py` + the three edited tests: 28 failed (guidance module missing, no prompts/resources, instructions still the old text, no package-data, no setup.py). The remaining 59 selected tests passed.

## Edited existing assertions (only these three)

- `test_actions_layer.py` TC-A10: `instructions` comparison now `== guidance.routing_instructions()` plus independent words (five flow names, read-only, terminal); tools half unchanged (BASELINE tools untouched).
- `test_actions_layer.py` TC-E07: renamed `test_tce07_exactly_the_five_flow_prompts_on_the_server`, asserts the five prompts, names = flow dirs, text = SKILL.md body.
- `test_actions_layer.py` TC-C01: allowed import set `{actions}` -> `{actions, guidance}`.

## GREEN

- Added `platform/abf_platform/guidance.py`, wired `instructions`, five prompts and six `skill://` resources in `mcp_server.py` (`_add_guidance`, outside the tool functions), `platform/setup.py` (build_py copy), `package-data` in `pyproject.toml`, `.gitignore` entry, docs (PLATFORM.md, TESTING.md manual check, CHANGELOG).
- `skills/` untouched; the six tools untouched. Plan's header for guidance.py was rewritten (tc070 judged the planned one IN-REPO).
- `platform/tests` pytest (test_guidance, test_actions_layer, test_mcp, test_scope): 93 passed; TC-404 wheel build ran (not skipped).
- Full suite (WSL, tests/run_all.sh, at the GREEN commit): 104/104 passed, all green. Rerun at HEAD after this ledger line: see executor-status.
