# Fix plan: doc-tests-local-main (issue #71)

Tier A (tests only; makes a check stricter). No change to the constitution, CONTEXT.md or hooks.

## What changes

1. `tests/constitution_scope_test.sh`: replace the `main` comparison with a pinned reference — the SHA-256 of the Safety Net section text as extracted today (`$SN`, constitution 3.0.0), written in the test with a comment: "changes only with a MAJOR amendment; update this hash in the same PR, where the reviewer sees it". The hash tool is chosen portably (`sha256sum`, else `shasum -a 256`, else python3 hashlib); if none is available the test FAILS with a message, never skips. On mismatch it prints the diff-free message plus the first lines of the current section.
2. `tests/platform_direction_docs_test.sh` TC-034: replace `git show main:CONTEXT.md` with a pinned list of the bold terms CONTEXT.md defines today (main bec2ea5 or later), kept in the test; every pinned term must still be defined. New terms may be added freely; removing one requires editing the list. No skip path remains.
3. Both tests: no remaining "skipped" branch for these checks; grep confirms no `git show main:` / `rev-parse --verify -q main` remains in these two files.

## Tests (RED first)

- RED: run each test in a clone with no `main` ref (e.g. `git clone --depth 1 --branch <this branch>` into a scratch dir, or `GIT_DIR` pointing nowhere) on a copy whose Safety Net has one word changed / one CONTEXT.md term removed: today it prints "skipped" and passes; after the fix it fails.
- GREEN: unchanged repo passes with and without a `main` ref.
- Mutation: change one word of the Safety Net → constitution_scope_test fails; delete one CONTEXT.md term → platform_direction_docs_test fails. Restore.

## Out of scope

- `tests/in_use_speed_test.sh` (reads main on purpose).
- Changing CI checkout depth.
- Any constitution or CONTEXT.md text.

## Done when

Both checks run (never skip) on CI's shallow checkout, fail on the mutations above, pass on the unchanged repo; CI green; verifier ACCEPT.
