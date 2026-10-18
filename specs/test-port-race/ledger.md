# test-port-race progress ledger

- [x] RED: platform/tests/test_port_race.py (TC-001, TC-002) fails on old helper (no reservation).
- [x] GREEN: helpers.free_port() claims the OS candidate with a per-port flock file in a shared temp dir (option 2); no production code touched.
