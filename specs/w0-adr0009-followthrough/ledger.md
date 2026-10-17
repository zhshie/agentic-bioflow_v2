# Ledger w0-adr0009-followthrough

- 2026-10-17 plan written by the developer-agent.
- 2026-10-17 RED: added 79 lines of W0 checks (TC-001..043, 059) to `tests/platform_direction_docs_test.sh`, run before any doc change: 43 FAIL lines, all W0 lines for the wording not yet written (010, Who paragraph, Stage 3 row, waiting list, open questions, ADR 0004 pointer, POSITIONING points 1 and 9). Four unrelated lines (`TC-010/TC-014 nomain/withmain` in the shell-driven sub-tests) also fail in the WSL run; checked against the base below.
