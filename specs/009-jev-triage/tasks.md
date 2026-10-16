# Tasks: Jev triage for FAILED runs

Single lane, in order. Every task is red-first: the TC it serves fails before the change. TC numbers come from `test-case.md` once the contract is confirmed.

## Phase 1: Decision and docs that set the boundary
- [ ] T001 `docs/adr/0007-jev-optional-triage.md`: context (POSITIONING rejection), maintainer's 10-16 words quoted from spec Input, decision (opt-in, own key, disclosed send, fail-open, `JEV_ENDPOINT` for a future local model), consequences.
- [ ] T002 `docs/POSITIONING.md:91`: ❌ → optional, off by default, own key, disclosed; link ADR 0007.

## Phase 2: Foundation (blocks US1–US4)
- [ ] T003 `scripts/settings.sh`: `jev_key_file()` next to `token_file()`; read `jev.enabled`, `jev.daily_cap`, `jev.min_confidence` with defaults; `.gitignore` adds `.typesafe_key`.
- [ ] T004 `tests/fixtures/jev/`: responses for high confidence, low confidence, unknown, `__500__`, `__timeout__`, `__429_then_ok__`, malformed JSON.
- [ ] T005 `scripts/jev.sh triage`: output contract in plan.md; disabled / no_key / capped / empty / missing curl or jq / failed paths; UTF-8 cleaning; last 200 lines; first-use notice; daily counter.
- [ ] T006 `tests/jev_test.sh`: every US2/US3 scenario through `JEV_DRY_RUN`; asserts no network call when disabled (fake `curl` on PATH that fails the test if invoked).
- [ ] T007 `tests/credentials_stay_in_settings_test.sh`: include `TYPESAFE_API_KEY` / `.typesafe_key`.

## Phase 3: US1 — the call site
- [ ] T008 `commands/runs.md` FAILED: new step after "No `.command.log`…" and before "Anything else"; the 7 non-memory category routes (short: what to look at first, usual fix, when to ask); memory points at "Out of memory". Says Jev changes no ⏸ step.
- [ ] T009 `skills/operational/SKILL.md`: fixed check order includes the Jev step.
- [ ] T010 Golden test: with Jev disabled, the FAILED-section script outputs used by the flow are byte-identical to main.

## Phase 4: US4 — measurement
- [ ] T011 `tests/jev_test.sh`: all 42 `labels.json` items run under `JEV_DRY_RUN`; the 5 rule-handled items (T01, T03, T05, T14, T43) are shown not to reach `jev.sh` per the runs.md order.
- [ ] T012 `scripts/dev/jev_replay.sh`: real-key run over the 37 scorable items → `specs/009-jev-triage/replay-report.md` (accuracy overall and per category, wrong ids, threshold recommendation, tokens, latency). Manual; not in `run_all.sh`; refuses without a key.

## Phase 5: Polish
- [ ] T013 `docs/SETTINGS.md` Jev section; `docs/TESTING.md` manual on/off walkthrough; `.claude-plugin/plugin.json` minor bump; PITFALLS entry if needed.
- [ ] T014 WSL `bash tests/run_all.sh` green; CI green.

## After merge (maintainer, manual)
- Run `scripts/dev/jev_replay.sh` with a real key; only if ≥ 90% does `docs/SETTINGS.md` say "建議開啟".
- Add real NCHC `.command.err` samples to `labels.json` when available.
