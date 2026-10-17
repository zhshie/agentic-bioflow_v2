# Ledger w0-adr0009-followthrough

- 2026-10-17 plan written by the developer-agent.
- 2026-10-17 RED: added 79 lines of W0 checks (TC-001..043, 059) to `tests/platform_direction_docs_test.sh`, run before any doc change: 43 FAIL lines, all W0 lines for the wording not yet written (010, Who paragraph, Stage 3 row, waiting list, open questions, ADR 0004 pointer, POSITIONING points 1 and 9). Four unrelated lines (`TC-010/TC-014 nomain/withmain` in the shell-driven sub-tests) also fail in the WSL run; checked against the base below.
- The four `nomain/withmain` FAIL lines in the RED run are not a real failure: that sub-test clones HEAD (committed docs) and runs the new test file in it, so it fails whenever a RED commit is on top of old docs. They pass again once docs are committed (GREEN).
- Anchor note: TC-030's check string was changed from `account is created` to `is an account created` before GREEN (own new test, matches the sentence as written).

## Rewritten pins in `tests/platform_direction_docs_test.sh` (old expectation / new expectation / why)
Line numbers are those before the edit.
- `:256` TC-022 stage 3 heading: `| 3 | **Web** (features 011–014)` -> `(features 011–014, 016)`. Studios is feature 016, inside Stage 3 (ADR 0009, plan round 2).
- `:392` TC-060a same string -> same new heading. Same reason.
- `:290` TC-025 waiting-list table lines: 16 -> 17. One row added (owed parity).
- `:471` 4.1.0 TC-017 `010: the two-role lab` -> `010: postponed (ADR 0009)`. Roles are postponed by ADR 0009.
- `:472` Stage 2 done-when `the PI sees it on the web` -> `the student sees it on the web`. No PI view while roles are postponed.
- `:474` 011 `011: dashboard and run detail, matching ...` -> `011a–e), matching ...`. ADR 0009 has no dashboard page; the right pane and projects/analyses replace it.
- `:475` 012 `SU estimate with a cap, matching ...` -> `(012a–d); cost shown per compute environment ..., a cloud cap per person per month ..., and no NCHC SU cap in dev mode; matching ...`. Cost per compute environment, cap per person per month (ADR 0009).
- `:476` 013 `the delivery package, matching ...` -> `the finished page with the delivery package (013a–b), matching ...`. Same structure, 013a–b.
- `:478` Stage 3 done-when `A lab member with no AI tool completes setup → launch → runs → rendered reports → the package from the web pages alone (figures from scripts ...); Two` -> `A person with no AI tool completes setup → launch → running → results → downstream (in a Studio) → finished from the web alone; Two`. New journey incl. Studio; second half kept verbatim.
- `:274` (role row text `PI and member roles are enforced`) not changed; only its stage cell is now `postponed (ADR 0009)`.
- Unchanged and still passing: ADR 0005 PI text (`:188-189`), SEQERA_PARITY counts and star items (`:340`, `:344`), 014 chat pins (`:393-400`).

## Old ROADMAP / POSITIONING sentences pinned by tests and what replaced them
- Who: `the PI pays and sees the whole lab` -> one person per account, own runs only, PI view postponed with roles (ADR 0009).
- Stage 2 row: `010: the two-role lab`, `the PI sees it on the web` -> postponed; student sees it on the web.
- Stage 3 row: dashboard / launch form with `SU estimate with a cap` / reports -> three-pane wording above; Studios 016 added; done-when rewritten.
- Waiting list: role row stage `2` -> `postponed (ADR 0009)`; owed-parity row added.
- POSITIONING point 1 (`簡化成 PI／成員兩種角色`, `儀表板`, `Studios` in the not-built list) -> Studios built (v3.0.0), right pane instead of a dashboard page, roles postponed; point 9 marked postponed; point 1 of the breakthrough table (measured NCHC refusal) untouched.
- ADR 0004: one added line under Studios; the pinned sentence stays.
