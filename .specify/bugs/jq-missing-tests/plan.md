# Fix plan: jq-missing-tests (issue #70)

Tier A: no hook changes; the suite becomes stricter about what it can and cannot judge.
Read `assessment.md` first.

## What changes

1. **`tests/run_all.sh` stops on a missing tool, like it stops on MSYS.** Before any test file
   runs (after option parsing and after `--list`, which still works without the tools), check that jq computes a known answer (the same probe the hooks use:
   `jq -c .a <<<'{"a":[1]}'` gives `[1]`, a trailing CR allowed) and that `python3` runs
   (`python3 -c 'print(1)'` prints `1`; the Store stub prints nothing). If either fails: print
   one message naming each missing tool, saying that the gates themselves still refuse without
   jq and pointing to `tests/gates_without_jq_test.sh` for that, with the install lines
   (`sudo apt install jq`, `brew install jq`), and exit 3 without running any file. A new
   option `--allow-missing-tools` runs anyway, and the final verdict line then names the
   missing tools so the reds are attributed. Exit codes otherwise unchanged.
2. **New `tests/gates_without_jq_test.sh`, needing no jq at all.** It hides jq with
   `tests/lib/nojq_path.sh` when jq exists (CI), runs as-is when it does not, builds every
   input with `printf`, and asserts for each row of the assessment's table: exit 2 and
   "BLOCKED" on stderr for the gated inputs, exit 0 for `ls -la`. `guard_plugin_files.sh` rows
   set `CLAUDE_PLUGIN_ROOT` to a scratch directory. It must pass on a machine with no jq, so
   `run_all.sh` must still run it when jq is missing: the stop in item 1 says to run it
   directly, and `run_all.sh --only gates_without_jq` must work without jq (the tool check is
   skipped when every selected file is `gates_without_jq_test.sh`).
3. **`tests/run_all_test.sh`** gains cases: with jq hidden, `run_all.sh` exits 3, prints the
   message, and creates no per-test log; with `--allow-missing-tools` it runs and the verdict
   names jq; `--list` works without jq; `--only gates_without_jq` works without jq.
4. **Docs**: `docs/TESTING.md` says the suite needs jq and python3, what exit 3 means, and
   that `gates_without_jq_test.sh` is the check that a missing jq does not open the gates.
   `docs/PITFALLS.md` gets one entry: "22 red files without jq were the tests, not the gates".

## Tests (RED first)

- `run_all_test.sh` new cases fail on main (no tool check, no option).
- `gates_without_jq_test.sh` is new; it should pass on main already (the gates hold). That is
  intended: it is a guard against a future fail-open, so the executor shows it FAILING once by
  temporarily breaking one hook's no-jq exit (e.g. local edit `exit 2` -> `exit 0`), records
  that in the fix notes, and restores the hook. The hook change is never committed.

## Out of scope

- Any change to the hooks.
- Installing jq anywhere (the maintainer's WSL included).
- Rewriting the 22 files to run without jq.
- Issues #66 and #71.

## Done when

- WSL without jq: `run_all.sh` exits 3 with the message; `run_all.sh --only gates_without_jq`
  passes; `bash tests/gates_without_jq_test.sh` passes.
- CI (with jq): full suite green, including both new/changed files.
- Issue #70 closed by the PR with the assessment's table quoted.
