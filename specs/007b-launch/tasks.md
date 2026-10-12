# Tasks: 007b launch, live progress, cancel

Progress ledger. Order per plan "Tasks"; each task is RED (tests, seen failing) then GREEN. A session that stops reads this first.

- [x] T1 nf-tower 1.17.5 fixtures (real Nextflow 25.10.4, `fixtures/record_payloads.py`), second pair pinned in `pins.env` and `tests/platform_test.sh`, receiver + rebuild drop a retried task from the failed list (TC-028, 029, 054). Commits c64caf0 (RED), be848a7 (GREEN).
- [x] T2 platform side: `confirmations`/`launches`/`meta` tables, migration of 007's `jobs`, instance id + `X-ABF-Platform`, run token made at claim / bound / revoked, enqueue guard (`jobs.py`, `confirm.py`), `abf_launch` package (CLI launch/cancel/launches/fetch-records, tty question, visible escaping), `abf_station/launch.py` `render_bundle()` (landed here because the CLI imports it), `records.py`. Tests: test_launch_bundle.py, test_launch_platform.py, test_launch_cli.py, launch_harness.py. Commits 0cf6401 (RED), 501af83 (GREEN).
  - Deviation: the CLI lives in a new package `platform/abf_launch/` (not abf_platform/cli.py) because test_scope TC-061 forbids the word `station` in abf_platform sources and the CLI must import `abf_station.launch`.
  - Deviation: environment variable names accept `[A-Za-z_][A-Za-z0-9_]*` (plan said capitals) because ce_apply.sh puts `http_proxy`/`https_proxy` into every environment.
  - Existing tests narrowed here (TC-060): test_station_envs TC-063 and TC-084, test_station_platform TC-090.
- [x] T3 agent side: `launch.py` execution, `cancel.py`, `fetch.py`, `Site.call(input=)`, hello facts, extended fake site, LAUNCH_ALLOW entry. Commits a2099de (RED), see git log for the GREEN. cancel/fetch tests (test_station_cancel.py) were written after the code, not before.
- [x] T4 channel: `on_site.sh --forward/--unforward/--check-forward`, `nf_relay.py` loopback rule (golden file from main bd9d42b), hop-by-hop preflight (`launch._channel`), `abf-station unforward`, hello carries the platform instance id, real-Nextflow chain tests (TC-026, 027, 033, 039, 045). Commits 2fd2c49 (RED), GREEN after it.
- [ ] T5 checks and docs: `LAUNCH_ALLOW` entry, docs (TC-058), full suite, executor-status.
