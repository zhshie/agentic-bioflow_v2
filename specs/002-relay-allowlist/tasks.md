# Tasks: 對外白名單可由部署自己擴充

**Input**: `spec.md`, `test-case.md` (approved 2026-09-30), `plan.md` (approved 2026-09-30)
Every task is test-first: write the test for its TCs, run it, record RED, implement, record GREEN. Each stage ends with `bash tests/run_all.sh` green in WSL.

## Stage S1 — `scripts/egress_allow.sh` (US1 add, US2 list/remove)

- [x] T001 [TC-005, TC-006, TC-018] `tests/egress_allow_test.sh`: validation — reject `*`, `com`, `0.0.0.0`, `10.1.2.3`, `::1`, empty, `a..b`, a label over 63 chars, `-x.org`; accept `download.example.org`, `Example.ORG.` (stored as `example.org`); `add` without `--reason` or with an empty one refuses; more than 100 entries refuses
- [x] T002 [TC-001, TC-014, TC-015, TC-017] same test: `add` writes `domain<TAB>date<TAB>reason` to `<root>/config/egress_allow.tsv` (root from a temp `LAB_SETTINGS_*` fixture, the way `tests/settings_test.sh` builds one); duplicate add says already present; `remove` deletes the line; `list` prints domain/date/reason and `來源不明` for a hand-added line with no date or reason; `domains` prints the comma list
- [x] T003 [TC-020, TC-021] header `# Nothing existing: …`; path derived like `token_file()`; passes `tests/no_hardcoded_paths.sh`, `tests/scripts_name_their_alternative.sh`, `tests/portable_userland.sh`
- [x] T004 implement `scripts/egress_allow.sh`; `docs/SETTINGS.md` documents the file (travels with the root; per deployment)

## Stage S2 — the relay reads the list (US1)

- [x] T005 [TC-002, TC-003, TC-004, TC-008, TC-009, TC-023] `tests/nf_relay_domains_test.sh`: import `scripts/nf_relay.py` with `NF_RELAY_EXTRA_DOMAINS` / `NF_RELAY_EXTRA_NOTE` set (no network, no server started): an extra domain and its subdomain pass `domain_ok`; an unlisted one does not; `evilexample.org` does not pass for `example.org`; an invalid entry is dropped and named; the startup lines list built-in and this-deployment groups separately; with a note and no list, the startup says the list was not loaded and why
- [x] T006 [TC-019] same test: the peer restriction (`ALLOW_HOST_PREFIXES` and its check) behaves exactly as on main
- [x] T007 [TC-008, TC-009, TC-010, TC-011] `tests/on_site_test.sh` (dry-run): `on_site.sh --script egress_ctl.sh start` carries `NF_RELAY_EXTRA_DOMAINS` from this deployment's file; a broken or unreadable file carries no domains and a `NF_RELAY_EXTRA_NOTE` saying why; a second deployment root carries its own list only
- [x] T008 implement: `nf_relay.py` (`EXTRA_DOMAINS`, startup log), `on_site.sh` carry (and the `reach: local` path)

## Stage S3 — the gate and the commands (US1, US2)

- [x] T009 [TC-007, TC-016] `tests/confirm_launch_test.sh`: `bash scripts/egress_allow.sh add x.org --reason r` → ask (naming domain and reason); `remove` → ask; `list` / `domains` → quiet; wrapped in `on_site.sh '…'` → ask
- [x] T010 implement the rule in `hooks/confirm_launch.sh` beside the resident-process gate, using the shared splitter's quote-free column
- [x] T011 [TC-012, TC-022] `commands/runs.md`, `commands/launch.md`: the approved-host step names `scripts/egress_allow.sh add <host> --reason …`, then the existing restart; no text tells anyone to edit plugin files; `tests/command_layer_is_site_neutral.sh` stays green
- [x] T012 [TC-013] the same command text says adding to the built-in list is the maintainer's change (manual check)
- [x] T013 `docs/SITE_ADAPTER.md` egress contract row mentions the per-deployment list; `docs/PITFALLS.md` only if something surprising turns up

## Close

- [ ] T014 full suite in WSL; `tests/confirm_launch_test.sh` natively in Git Bash; time `hooks/confirm_launch.sh` natively (must stay ~1–2 s)
- [ ] T015 independent acceptance (read-only verifier) against spec + approved test cases + diff
- [ ] T016 maintainer: TC-013 by hand; add one domain on the real cluster, restart the outbound channel, relaunch
