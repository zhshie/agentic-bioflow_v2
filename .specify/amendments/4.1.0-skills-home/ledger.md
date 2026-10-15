# Ledger: constitution 4.1.0

## Red first (commit bec2944)

Run with `DOC_TEST_INNER=1 bash tests/platform_direction_docs_test.sh` (skips the scratch-clone
block) and `bash tests/constitution_scope_test.sh` on the unedited documents.

- `tests/constitution_scope_test.sh` failed: "version is 4.1.0 ...", "Last Amended is the day of
  the latest amendment" (plus the scratch-clone case TC-002, which reads the same version).
- `tests/platform_direction_docs_test.sh`: 71 assertions failed, among them TC-001 (version line),
  TC-003, TC-004, TC-006 (heading, position), TC-007, TC-008 to TC-014 (4.1.0 record),
  TC-016 to TC-018, TC-020, TC-022 (ROADMAP rows and paragraph), TC-023/024/025 (waiting list),
  TC-026/028/029 (POSITIONING), TC-031 to TC-033 (CONTEXT), TC-044/045 (ADR notes),
  TC-047/059 (CLAUDE.md, README.md), TC-049 (PRINCIPLES.md). TC-005, TC-035 to TC-043 and TC-046
  passed already (ADR 0006 was on the branch and quotes what the TCs quote; no mismatch found).

## Files changed (green commit)

`.specify/memory/constitution.md` (II.5 first sentence and Check line, 4.1.0 record, version line),
`docs/ROADMAP.md`, `docs/POSITIONING.md`, `CONTEXT.md`, `docs/PRINCIPLES.md`,
`docs/adr/0003-host-strategy.md`, `docs/adr/0004-self-hosted-platform-mcp-first.md`, `CLAUDE.md`,
`README.md`, `tests/constitution_scope_test.sh`, `tests/platform_direction_docs_test.sh`.

## Notes

- Plan §1 and TC-004 both change the Check line of II.5 (`from skills/, docs/ and scripts/`); done.
- CONTEXT.md: the two new entries put the definition on the same line as the term (as the plan
  quotes them) so that `one function per platform action` matches case-sensitively.
- TC-025's "16 lines" counts lines starting with `|`; the old `^\| ` count excludes the separator.

## Suite result and what was not done

See the final report (filled in after the WSL run).

## Fix round 1 (2026-10-15, after /code-review; plan §8)

- Item 2 red first: `tests/platform_direction_docs_test.sh` TC-031 edited before `CONTEXT.md`; run in the WSL clone
  showed `FAIL` on `4.1.0 TC-031: MCP tool layer: the old 'each write tool carries its own gate' is gone` (the old
  sentence still found) and on the new-sentence `inn`. Then `CONTEXT.md` edited: green.
- The old pin `...gains the ADR 0006 sentence` (`...the gate lives there.`) became stale with the new sentence, so
  its pinned string now reads the full new sentence (without this the test failed and TC-010/TC-014 of issue #71
  cascaded); the plan said "keep the other TC-031 assertions", this is the same assertion with the new text.
- Item 1: `docs/ROADMAP.md` waiting-list row check text replaced; the *Note* is untouched; 16 rows unchanged.
- Item 2: `CONTEXT.md` MCP tool layer sentence replaced; `test-case.md` TC-031 expected text updated, note
  `（2026-10-15 /code-review 後修正）`.
- Item 3: every label in the 4.1.0 block (from the `# ---- Constitution 4.1.0` header to the end) prefixed `4.1.0 `;
  the header `echo` and the earlier amendment's labels are untouched; no pinned string changed (other than item 2).
- Results (WSL, clean clone suite-clone-4-1-0 with the edited files copied in): `tests/platform_direction_docs_test.sh`
  all passed; `tests/constitution_scope_test.sh` all passed. The full suite was not run this round (only these two
  tests and the two docs changed), as instructed.
