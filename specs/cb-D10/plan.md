# cb-D10 plan: duplicate-definition ratchet

Source: cloud-burn tasks.json D10.

## Goal
A production `.py` def (function, async function, class, method) that is AST-identical (docstrings
stripped) and same-named in two or more files is copy-paste drift waiting to happen. Today's set is
recorded in a baseline that may only shrink; any new or grown group fails.

## Files
- `platform/tests/test_no_duplicate_defs.py` (new)
- `platform/tests/duplicate_defs_baseline.txt` (new)
- `specs/cb-D10/plan.md`, `specs/cb-D10/ledger.md`

## Approach
- Production = `platform/abf_platform/`, `platform/abf_station/`, `platform/abf_launch/`, `scripts/` (`*.py`);
  tests, docs, `.specify/` and `platform/setup.py` are not production.
- `find_duplicates(sources)` is pure (path -> source text): walk every def/class, strip docstrings
  (module, class, def), `ast.dump` the node (no line numbers), group by (name, dump), keep groups in >= 2
  distinct files, drop whitelisted names.
- Whitelist `main` and `render`, each with a written reason (a name every entry point or renderer has).
- Baseline line: `name file1 file2 ...` (sorted). A current group passes only if its file set is a subset of a
  baseline line of the same name; a baseline line that no current group equals exactly is stale and fails with
  the shrunk line to write. So the baseline can only get smaller.
- Self-tests on synthetic sources prove the detector (identical, docstring-only difference, different body,
  same file twice, whitelist, nested method, decorator).

## RED tests
1. Commit the test with an empty baseline: the real-tree test fails and names the 8 groups present today.
2. Mutation proof (not committed): copy a production def into a second file -> fails; delete a duplicate so a
   baseline line goes stale -> fails; restore both.

## Done criteria
Test green with the baseline filled; check_scope OK; `tests/run_all.sh` all passed.

## Environment facts
venv `/tmp/cb/venv`, worktree `/tmp/cb/D10` from `origin/v3` 1802fde4. New test file is picked up by the REST
shard of `tests/platform_test.sh` automatically.

## Not doing
No de-duplication of the 8 groups (production code is out of the allowed files); no changes to run_all or CI.
