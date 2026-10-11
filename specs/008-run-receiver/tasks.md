# Tasks: 008 run receiver + read-only MCP

## S0 — environment and facts

- [x] T000 venv on WSL Python 3.10.6 (`virtualenv`, because the system python has no `ensurepip`); `mcp` 2.3.0 installs; `platform/constraints.txt` written from what resolved
- [x] T001 pinned Nextflow 26.04.7 and `nf-tower` 1.28.3 with sha256 (`platform/tests/pins.env`); heartbeat interval, request and progress fields, the literal Authorization header and the Nextflow file formats written into `research.md` with file:line
- [x] T002 real payloads recorded from real runs of the fixture pipelines into `platform/tests/fixtures/payloads/` (version and what was replaced in each file header); a real heartbeat is in `heartbeat_run.json`

## S1 — RED

- [x] T003 `platform/tests/` (unit, replay, MCP, CLI, scope, wrapper, e2e) and `tests/platform_test.sh`; seen failing because `abf_platform` did not exist (commit `RED:`)

## S2 — GREEN

- [x] T004 `platform/abf_platform/`: `common`, `store`, `receiver`, `status`, `rebuild`, `mcp_server`, `cli`; `platform/pyproject.toml`; `.gitignore` entries
- [x] T005 `docs/PLATFORM.md`; manual steps for TC-023, TC-050, TC-052, TC-053, TC-063, TC-064, TC-073 in `docs/TESTING.md`; note in the first row of `docs/ROADMAP.md` "Principles waiting for a check"

## Close

- [x] T006 full suite in WSL, compared with `main`
- [ ] T007 independent acceptance (verifier); manual cases TC-023, TC-050, TC-052 (CI half), TC-053, TC-063, TC-064, TC-073
