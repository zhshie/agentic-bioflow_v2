# Google Batch 計算環境（gcb-ce-type-2，依裁決二重做）progress ledger

- [x] RED: platform/tests/test_gcb_ce.py (TC-001..TC-109 automatic) and the 12-type updates of test_station_envs.py / test_station_docs.py
- [x] compute_envs.py: PLATFORM_HOST_TYPES / CHECKABLE, `_check_gcb` (agent required), `creating` on create, legacy `unsupported` row -> `creating` on a complete update, flat snapshot for the agent
- [x] jobs._target: a Google Batch environment takes the preflight only; every other kind is refused in plain words (C-2); cli: first preflight queued for CHECKABLE types, five flags, legacy rows checked before `ce preflight`
- [x] abf_station/gcb_preflight.py (8 checks, fake-able runner/which, agent-side key file location `ABF_STATION_GCP_CREDENTIALS`) + handlers.py branch; abf_platform has no subprocess and no key-file code
- [x] docs/PLATFORM.md, SEQERA_PARITY.md, TESTING.md
- [x] abf_station/site.py: `run_fixed` is the one place that starts gcloud (test_station_static TC-091 allows one module that starts programs); gcb_preflight imports no subprocess
- [ ] full suite at HEAD
