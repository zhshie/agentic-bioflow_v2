# 送出前再查一次代理程式還活著（#7） progress ledger

- [x] RED: tests/launch_recheck_test.sh (T1-T9, TC-008, 013, 016-020)
- [x] scripts/launch_recheck.sh (read-only; egress + agent status; no cache)
- [x] skills/launch/SKILL.md: gate sentence (reach), step 7 notice, step 8 re-check and FAIL branch
- [x] docs/PITFALLS.md #56
- [ ] Manual (TC-021/022, real ssh deployment, not run by executor): `agent_ctl.sh stop` then `scripts/launch_recheck.sh` should exit 1 with `FAIL agent` and the restart command; after `start`, exit 0.
