# Fix: doc-tests-local-main

- **Branch**: `fix/71-doc-tests-pinned` (RED dabce80, GREEN see PR)
- **Changed**: `tests/constitution_scope_test.sh`; `tests/platform_direction_docs_test.sh`.

## What changed

- `constitution_scope_test.sh`: the Safety Net section is compared with a pinned SHA-256 (`PINNED_SN_SHA256`, input = `$SN` printed with `printf '%s\n'`, `\r` removed) instead of `main`'s copy. Any change to that section's text must update the value in the same PR; a mismatch prints the current fingerprint and the section's first lines. The hash tool is `sha256sum`, else `shasum -a 256`, else `python3`; with none the check FAILS. The `sn_has` fixed-string checks are untouched.
- `platform_direction_docs_test.sh` TC-034: the 15 bold terms of `CONTEXT.md` are pinned in `PINNED_TERMS`; each must still be defined. New terms are free; removing one means editing the list.
- No `main` ref and no skip branch remain in either file (TC-009, TC-015 check this).
- Both files build scratch shallow clones (`git clone --depth 1`, removed by a trap) and run themselves inside them: unchanged repo, mutated Safety Net, removed/added CONTEXT term, with and without a `main` ref, and with a PATH that has no hash tool. `DOC_TEST_INNER` stops the inner run from recursing.

## Evidence (WSL)

RED (dabce80): `constitution_scope_test.sh` 12 failed, `platform_direction_docs_test.sh` 8 failed (shallow clone printed the skip note and passed). GREEN: both all passed; `constitution_checks_exist_test.sh` unaffected.

Out of scope and untouched: `tests/in_use_speed_test.sh`, `.github/`, the constitution, `CONTEXT.md`, hooks.
