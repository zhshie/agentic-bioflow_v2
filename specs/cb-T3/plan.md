# cb-T3 plan: scripts/utils/file_discovery.py

- Source: cloud-burn tasks.json T3.
- Goal: `find_index_file` and `detect_input_type` have no caller anywhere in the repo
  (`git grep` at origin/v3 62c91293 finds only their definitions, plus two prose lines in
  `docs/reports/sweep-2026-11.md`). Delete them and what only they used (`INDEX_EXTENSIONS`,
  the `Path` and `Optional` imports). Add tests for `discover_files` and `count_files_by_type`,
  which had none by name.
- Files: `scripts/utils/file_discovery.py`, `tests/file_discovery_test.sh` (new),
  `specs/cb-T3/plan.md`, `specs/cb-T3/ledger.md`.
- Callers found: `scripts/generate_samplesheet.py:46,55` uses `discover_files` only.
  Brief says delete only if zero callers outside tests: zero found (no test referenced them either).
- Approach: (1) test file asserting behaviour of the two kept functions, plus two absence
  cases for the dead functions; (2) delete the dead code.
- RED tests: the two absence cases fail on unchanged code. The behaviour cases pass on
  unchanged code (code already right), so they get a mutation proof instead.
- Done: new test file green; check_scope OK; full `tests/run_all.sh` last line says all passed.
- Environment: venv at /tmp/cb/venv, `pip install -e platform pytest`; build/egg-info removed.
- Not doing: touching `generate_samplesheet.py`, `sample_inference.py`, docs, other tests.
