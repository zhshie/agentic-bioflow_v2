# launch: rendered nextflow.config allows report/timeline overwrite (aborted runs logged 'Report file already exists') progress ledger

- [x] Upstream search (TC-017). Searched nextflow-io/nextflow with gh: issue 6692 "TraceObserverV2 - onFlowComplete firing twice" (closed 2026-07-17, same stack: Session.shutdown0 from Session.destroy, "Report file already exists ... report.overwrite"); issue 3627 and 3334 (older, the message itself); PR 7781 (merged 2026-10-09) says PR 7349 made `Session.shutdown0()` run only once. Which release carries the run-once change was not found ("查不到"); so it is NOT claimed that a released version fixes this. The config fix is applied for the pinned 26.04.7 either way, and offline test TC-011 shows 26.04.7 still logs the error without it.
- [x] Red first: tests added and committed as RED (TC-001..006, 008, 009, 010, 011, 013, 015, 016, 019, 020).
- [x] `platform/abf_station/launch.py`: `OVERWRITE_BLOCK` appended to every rendered `nextflow.config` (user text first, verbatim; commented; only the two settings).
- [x] Offline real-Nextflow test done (SIGINT reproduces the error): TC-010, TC-011, TC-013 in `platform/tests/test_nextflow_e2e.py`. TC-012 and TC-014 (NCHC, Nextflow 25.10.4, real cancel) still need the maintainer's NCHC recheck (`specs/007b-launch/acceptance-nchc.md`); steps added to `docs/TESTING.md`.
- [x] Docs: `docs/PITFALLS.md` 46; `docs/PLATFORM.md` section 9 (TC-019, test in `test_launch_docs.py`); `docs/TESTING.md` cancel step.

## Existing expectations changed (TC-015), each only because the block is the sole difference

- `platform/tests/test_launch_bundle.py` (`== "process.executor = 'slurm'\n"`): now `startswith` that exact text and the rest, minus comments, is exactly the two settings.
- `platform/tests/test_launch_cli.py` (`config == ["process.executor = 'slurm'"]`): now first line equals it verbatim, the remaining non-comment lines are exactly the two settings, and a comment is present.
- `platform/tests/test_station_launch.py`: `config_block` case added to the tamper test (TC-008); import of `render` added. No existing assertion changed.

Not touched: receiver and its tests, `.github/`, `plugin/`, `hooks/`, `.claude-plugin/`.
