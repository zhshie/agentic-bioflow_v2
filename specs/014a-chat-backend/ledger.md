# 014a backend: browser chat tool list and model-key refusal progress ledger

- [x] Tests first (RED): `platform/tests/test_chat_tools.py`, `platform/tests/test_model_key_refusal.py`.
- [x] `platform/abf_platform/actions/chat_tools.py`: `tool_specs` (derived from the MCP server, cached, runs `classify_check`), `classify_check`, `REQUEST_TOOLS`, `CHAT_SYSTEM_PROMPT`.
- [x] `platform/abf_platform/compute_envs.py`: two model-key patterns appended after the six existing ones.
- [x] `docs/TESTING.md`: 014a section for the manual cases TC-032, TC-036, TC-043.
- [x] Revision 2026-10-19: tests first (TC-050..053 in `test_chat_tools.py`, TC-005 wording, TC-003 narrowed for the helper name `confirm_dialog`); `chat_tools.confirm_dialog` added; `CHAT_SYSTEM_PROMPT` rule 1 and the request heading rewritten for the 「確認送出嗎？」 window. (The plan calls the new cases TC-030..033, which already exist here, so they are numbered TC-050..053.)
