# cb-T5 plan: path rules parity test

- Source: cloud-burn tasks.json T5.
- Goal: `abf_station.rules.path_problem` (platform/abf_station/rules.py:23) and
  `abf_platform.compute_envs.path_problem` (platform/abf_platform/compute_envs.py:79) are two
  deliberately separate copies of one rule ("a second lock on purpose"). Nothing checks that they
  keep giving the same answer. Add a test that feeds both the same inputs and asserts equal answers.
- Files: `platform/tests/test_path_rules_parity.py` (new), `specs/cb-T5/plan.md`, `specs/cb-T5/ledger.md`.
  `platform/abf_station/` is read-only (FORBIDDEN), so no source file changes.
- Approach: inputs = legal paths, '..' in several positions, relative, empty, non-string, very long
  (at and over MAX_PATH), non-allowlisted characters (space, quote, ;, $, newline, NUL, non-ASCII),
  trailing newline. Parametrised test asserts station == platform; plus a guard that the table is
  not vacuous (legal -> None, the others -> a code). Also assert MAX_PATH equal.
- If the two already disagree on a case: do not fix; record a FINDING and drop the case.
- RED tests: pure test addition (code already right) so mutation proof instead: temporarily break
  one copy (a `/tmp` copy of the module is not possible, so edit in the worktree and `git checkout`
  it back), show the new test fails, restore. The mutant is never committed.
- Done: new test green, check_scope OK, run_all last line says all passed.
- Environment: venv at /tmp/cb/venv, `pip install -e platform pytest`; build/egg-info removed.
- Not doing: unifying the two functions, touching abf_station, testing path_message/path_reason texts.
