# agent-token-revoke-by-id progress ledger

- [x] RED: platform/tests/test_agent_token_revoke_id.py written first; 21 failed / 6 passed (the 6 are the unchanged by-name and flag-rejection cases).
- [x] GREEN: store.list_agent_tokens / revoke_agent_token, cli `agent-token list` and `revoke --id`, docs OPERATIONS.md and PLATFORM.md; 27 passed. No migration (tokens columns unchanged). No existing test touched.
