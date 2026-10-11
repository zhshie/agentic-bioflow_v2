# Tasks: 007 station agent + compute environments (slice 1)

## S0 — facts

- [x] T000 each compute environment type's `platform` identifier read from Seqera's public documentation and written into `research.md` with the URL (the API reference page is drawn in the browser, so the identifiers come from the "Available platform values" table; the text says so)

## S1 — RED

- [x] T001 tests for the 89 automatic cases: `platform/tests/test_station_platform.py` (agent protocol, fake clock), `test_station_envs.py` (environments, commands, MCP), `test_station_fakeplatform.py` (hostile jobs, token file and URL rules), `test_station_e2e.py` (real platform process + real agent process + fake site), `test_station_static.py`, `test_station_docs.py`, helpers in `station_harness.py`; seen failing because `abf_station` and the new commands did not exist (commit `RED:`)
- [x] T002 the 008 assertions named in plan Revision 2 item 8, widened and not weakened: MCP tool count two to six (`test_mcp.py`), header check covers `abf_station/` (`test_scope.py`)

## S2 — GREEN

- [x] T003 `platform/abf_platform/`: `platform.db` (`store.py`), `tokens.db` migration with `kind`, `agent_name`, `revoked_at`, `agents.py` (hello, poll as an asyncio deadline loop, result), `jobs.py` (queue, deadlines, late answers), `compute_envs.py` (14 types, credential scan, primary rule), `cli.py` (`agent-token`, `ce`), `mcp_server.py` (four new read-only tools), `receiver.py` wiring
- [x] T004 `platform/abf_station/`: `cli.py` (start-up checks), `agent.py` (poll loop, beat during a job, signals), `handlers.py` (preflight, list_site_files), `rules.py` (the agent's own allow-list), `site.py` (the only module that starts a program: `scripts/on_site.sh`, values quoted); `pyproject.toml` lists the package and the `abf-station` script
- [x] T005 docs: `docs/PLATFORM.md` sections 6 to 8, `docs/SEQERA_PARITY.md` section F per type, `docs/ROADMAP.md` Stage 1 and Stage 4, manual cases TC-076, 079, 080, 081, 088, 093, 094, 095 in `docs/TESTING.md`

## Close

- [x] T006 full suite in WSL, compared with `main`
- [ ] T007 independent acceptance (verifier); manual cases TC-076, TC-079, TC-080, TC-081 (CI half), TC-088, TC-093, TC-094, TC-095
