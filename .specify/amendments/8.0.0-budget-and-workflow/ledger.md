# Ledger: constitution 8.0.0 (draft)

2026-11-11. Branch `feat/dev-mode-launch`, merged with `origin/v3` at `f82fb65f` (merge, no
rebase). One conflict, `docs/TESTING.md`: both sides added a section at the same place; both kept.

## Red first (commit a034636c)

On the 7.0.0 text:

- `tests/budget_doc_test.sh`: 62 checks failed, 24 passed.
- `tests/constitution_scope_test.sh`: 3 failed (version, Last Amended, TC-E5).
- `tests/platform_direction_docs_test.sh`: 1 failed (TC-001).
- `tests/charter_v4_workflow_test.sh`: 1 failed (TC-028).

## Green

- `.specify/memory/constitution.md`: I.2, the Safety Net's launch rule and write-tool rule with its
  Check line, the last rule of the Development Workflow, the 8.0.0 record, the version line.
- `PINNED_SN_SHA256`: `ee51f3e242ab5ccef38a8e449aed544b98bf10802c6507ab5999c8143309f2b4` →
  `8a59945b56b093823dd07c7441335266693c99623391917dbbf74ad114caa321` (the two rules above are inside
  the Safety Net section; computed with the test's own method).
- The records 2.0.0 to 7.0.0 are byte for byte what they were: fingerprint
  `6874bc14cc16ef85c5e6a4bd61029315f86397fb767fdbc8518575d85f730765` before and after.
- `docs/PLATFORM.md`, `docs/PRINCIPLES.md`: one paragraph each.

## Assertions changed in existing tests

Only pinned values: the version string `7.0.0` → `8.0.0` (four places), the date `2026-11-05` →
`2026-11-11` (four places), the label of one check, and `PINNED_SN_SHA256`. No assertion was
removed, skipped or loosened.

## Not done here

- Approval: `PENDING`. The pull request is a draft, opened without `--auto`, not merged.
- `skills/launch/SKILL.md` and `docs/adr/0006-…` (listed in the feature plan): left as they are; no
  pinned test asks for them and the amendment task limits documents to the smallest sync.
- `deploy/`: untouched (ruling 4 of 2026-11-10).
