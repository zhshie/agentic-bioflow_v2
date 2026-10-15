# tests: scratch clones must not inherit a main ref (main's push CI is red) progress ledger

## Progress

- [x] RED (TC-010): in a temp clone with `git checkout -B main`, pre-fix `bash tests/constitution_scope_test.sh` printed `scratch clone really has no main ref  FAIL`; `platform_direction_docs_test.sh` passed only because it had no such assertion. Added assertions TC-004/005 (constitution_scope_test.sh) and TC-006 (platform_direction_docs_test.sh); TC-004 fails before the fix.
- [x] GREEN: `mkclone` in both tests now detaches and deletes an inherited main for nomain clones (guarded by show-ref); withmain keeps/creates main.
