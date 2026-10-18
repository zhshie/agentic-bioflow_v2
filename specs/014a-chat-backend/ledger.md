# 014a backend: browser chat tool list and model-key refusal progress ledger

- [x] Tests first (RED): `platform/tests/test_chat_tools.py`, `platform/tests/test_model_key_refusal.py`.
- [x] `platform/abf_platform/actions/chat_tools.py`: `tool_specs` (derived from the MCP server, cached, runs `classify_check`), `classify_check`, `REQUEST_TOOLS`, `CHAT_SYSTEM_PROMPT`.
- [x] `platform/abf_platform/compute_envs.py`: two model-key patterns appended after the six existing ones.
- [x] `docs/TESTING.md`: 014a section for the manual cases TC-032, TC-036, TC-043.
