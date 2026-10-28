# 擁有者綁定補三個縫：舊 token 拒絕、ce --owner 認領、守衛測試（#116） progress ledger

- [x] US1: agents.register refuses a no-user token on an owned agent; cli agent-token new needs --user once users exist, refuses another user's agent
- [x] US2: compute_envs._claim_agent in create/update; store.assign_orphans adopts unowned agents of single-owner environments
- [x] US3: platform/tests/test_owner_guard.py (scanner, allow-list, tool/action pairing)
- [x] Docs: PLATFORM.md, OPERATIONS.md, TESTING.md (Owner binding follow-up), CHANGELOG.md
- Station files (station_harness.py, test_station_envs.py, test_station_platform.py): touched only if the full suite shows them red.
