# cb-D8: root CLAUDE.md without numbers that go stale

Source: cloud-burn tasks.json D8.

## Goal
Remove the counts and lists in CLAUDE.md that rot, and point at the thing that is always right.

## Files
CLAUDE.md, tests/claude_md_no_stale_counts_test.sh (new), specs/cb-D8/{plan,ledger}.md.

## Approach
1. `# all 73, ~100s, one verdict + exit code` -> no number; the run prints its own `N/M passed` line.
2. "every push to `main`" -> "every push to the branches listed in `.github/workflows/tests.yml`" (that file lists main and v3).
3. Constitution version: the only hard-coded version in the file is "constitution 6.0.0", but
   `tests/platform_direction_docs_test.sh` TC-059 (HOT, not editable here) pins that exact string,
   and "Constitution 2.0.0" is pinned by constitution_scope_test.sh. They name the version in which
   a rule changed, not the current one. Left in place; recorded as a FINDING.
4. New lint test: CLAUDE.md must not match `all [0-9]+` or `[0-9]+ tests`; also must not claim CI runs on
   pushes to `main` alone.

## RED tests
tests/claude_md_no_stale_counts_test.sh fails on current CLAUDE.md (line "all 73").

## Done criteria
New test green, run_all green, scope guard clean.

## Environment facts
Pins checked with git grep over tests/: the sentences changed here are not pinned by any test
(only `bash tests/run_all.sh`, "Platform is the execution backend 2.17.0 uses...", `constitution 6.0.0`,
`Constitution 2.0.0`, `hooks/in_use.sh` are, and all stay).

## Not doing
No constitution-version rewrite, no other CLAUDE.md edits, no HOT test edits.
