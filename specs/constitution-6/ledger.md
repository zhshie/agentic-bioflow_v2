# Constitution 6.0.0: run index, every write tool, stored credentials join progress ledger

- [x] 1. docs/ROADMAP.md: run-index and gates rows deleted; credential and write-tool rows keep their principle text and gain the 6.0.0 notes; 15 table lines.
- [x] 2. docs/PRINCIPLES.md: "waits for its check" corrected; 6.0.0 entry added (three rules, their tests, what did not move and why).
- [x] 3. README.md and CLAUDE.md: constitution 5.0.0 cites became 6.0.0.
- [x] 4. tests/constitution_scope_test.sh: version string, Last Amended 2026-10-18, PINNED_SN_SHA256.
  - old fingerprint: fd9129685c1c52a2790926ed8f6d92e186c9ff036bb8d24155837bcbe51de0ae
  - new fingerprint: bb125d3a27489ca5aa08951bf58d0ba547be88c259a006bb1e32907c6c399bd1 (the test's own method: Safety Net section, printf '%s\n', tr -d '\r', SHA-256; the issue #71 scratch cases TC-002/TC-007 pass again)
- [x] 5. tests/platform_direction_docs_test.sh: TC-001, TC-059 re-pinned to 6.0.0; TC-006, TC-023 (run index, gates), W0 TC-027 inverted; TC-025 and W0 TC-026 now 15 lines; lines for the credential and write-tool rows unchanged. New variable PI2 (principle I.2 text) because P1 is reassigned by the issue #71 block.
- [x] 6. tests/constitution_6_test.sh (new): (a) check files, (b) test prefixes defined, (c) write-tool list equals the registered tools plus a self-test that an unlisted tool turns it red, (d) ROADMAP rows, (e) PRINCIPLES entry.
- [x] 7. Full suite green in WSL at the final commit (an earlier run had one timing flake in test_station_e2e online/offline, unrelated; it passed on rerun).
