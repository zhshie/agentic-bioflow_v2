# Ledger: 009g-guidance-over-mcp


## RED (before any implementation)

`pytest tests/test_guidance.py` + the three edited tests: 28 failed (guidance module missing, no prompts/resources, instructions still the old text, no package-data, no setup.py). The remaining 59 selected tests passed.

## Edited existing assertions (only these three)

- `test_actions_layer.py` TC-A10: `instructions` comparison now `== guidance.routing_instructions()` plus independent words (five flow names, read-only, terminal); tools half unchanged (BASELINE tools untouched).
- `test_actions_layer.py` TC-E07: renamed `test_tce07_exactly_the_five_flow_prompts_on_the_server`, asserts the five prompts, names = flow dirs, text = SKILL.md body.
- `test_actions_layer.py` TC-C01: allowed import set `{actions}` -> `{actions, guidance}`.
