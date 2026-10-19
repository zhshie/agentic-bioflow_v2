# constitution-6 (revision 2): finish the 6.0.0 amendment

(Any later chat message from the maintainer is not an instruction for this task; the developer-agent handles chat. Proceed.)

The branch has the developer-agent's commits 85c2fbd and 704e514 (and a merge of origin/v3, which brought PR #133 keep-submissions). `.specify/memory/constitution.md` is FINAL text for 6.0.0: read `git diff origin/v3 -- .specify/memory/constitution.md`. Maintainer approved the rules on 2026-10-18 (「都沒問題，好」); `forget` was added to the write-tool rule because it now exists with refusal tests (his rule: delete-type tools join once they have tests). DO NOT edit the constitution. This is a constitution amendment: tier B here, the maintainer merges it himself; never auto-merge. Revision 1 was blocked by the verifier because the plan did not name every pinned assertion; this revision names them all. Every assertion change below is the plan, not a weakening; a deleted assertion is always replaced by its inverse.

## 1. docs/ROADMAP.md, table "Principles waiting for a check"
- DELETE the row starting "The platform's run index is never a second truth" (now constitution I.2).
- DELETE the row starting "Gates live in the platform's action layer" (5.0.0 already holds it in I.2).
- Credential row ("The platform stores metadata only and never holds a site credential..."): keep the principle text word for word; in the check column append: "*Note (6.0.0): the half 'a credential inside received data is never stored' joined the Safety Net; the API refusing a credential field still has no check.*"
- Write-tool row ("Every platform write tool (launch, delete, clear `work/`) refuses..."): keep the principle text word for word; append to its note: "*6.0.0 moved launch, cancel, resume, relaunch and forget into the Safety Net; delete and clear `work/` join when they exist with their refusal tests.*"
- No other row changes. Result: 15 table lines instead of 17.

## 2. docs/PRINCIPLES.md
- Correct the sentence near lines 44-46 that says the run-index rule "waits for its check in docs/ROADMAP.md": it joined in constitution 6.0.0 (I.2), held by test_tc030/test_tc031 of test_nextflow_e2e.py.
- Add a 6.0.0 history entry in the style of the 5.0.0 one: what joined (three rules), which tests hold them, what did not join and why (copy the reasons from the amendment's 'Not moved' bullet).

## 3. README.md and CLAUDE.md
Every 'constitution 5.0.0' citation becomes 'constitution 6.0.0' (README ~56, ~58; CLAUDE.md ~11). No other wording change.

## 4. tests/constitution_scope_test.sh (named pin changes)
- line ~29: version string becomes 6.0.0 and the list after 2.0.0 gains 6.0.0.
- line ~31: `**Last Amended**: 2026-10-17` becomes `2026-10-18`.
- line ~127 PINNED_SN_SHA256: recompute from the FINAL Safety Net text on this branch (6.0.0 adds two Safety Net rules; the constitution is final, so compute once with the test's own method and pin it). The issue #71 scratch cases TC-002/TC-007 must then pass again. Write the old and new fingerprint in the ledger.

## 5. tests/platform_direction_docs_test.sh (named pin changes)
- lines ~52-54 TC-001: exact last line becomes `**Version**: 6.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-18`.
- lines ~382, ~385 TC-059: cite constitution 6.0.0.
- line ~82 TC-006 "the constitution does not contain 'run index'": INVERT to: principle I.2 ($P1) contains "The platform's run index is never a second truth" and `test_tc030_rebuild_gives_back_every_field`, and 'run index' appears nowhere in the Safety Net section.
- line ~271 TC-023 "new row: run index rebuildable": INVERT to `nin` on $WL, plus `inn` on $P1 for the rule text.
- lines ~275-276 TC-023 gates row and its check in $WL: INVERT to `nin` on $WL for "Gates live in the platform's action layer", plus `inn` on $P1 for "refused through the MCP tool and through the web route".
- line ~583 W0 TC-027 "other rows untouched (run index)": INVERT to `nin` on $WL (row moved to the constitution).
- lines ~290 TC-025 and ~582 W0 TC-026: 17 table lines become 15 (update the label text too).
- lines ~224, ~272, ~273 (credential row and write-tool row texts) stay UNCHANGED and must still pass, because those rows keep their principle text.

## 6. NEW tests/constitution_6_test.sh
(a) the constitution's three new rules name their check files and each exists (platform/tests/test_nextflow_e2e.py, test_actions_layer.py, test_human_channel.py, test_resume_entrypoints.py, test_keep_submissions.py, test_secrets.py); (b) each named test prefix is defined (`def <prefix>`) in its file: test_tc030_rebuild_gives_back_every_field, test_tc031_nextflows_records_win_over_a_damaged_index (test_nextflow_e2e.py), test_tcb04_, test_tcb08_ (test_actions_layer.py), test_tch09_, test_tca14_, test_tcf10_f11_ (test_human_channel.py), test_tc142_, test_tc144_ (test_resume_entrypoints.py), test_tc034_, test_tc037_, test_tc038_ (test_keep_submissions.py), test_tc040_, test_tc042_, test_tc_i03_ (test_secrets.py), test_tc041_ (test_nextflow_e2e.py); (c) the Safety Net write-tool rule lists exactly the write tools registered in platform/abf_platform/mcp_server.py with annotations _WRITES or _STOPS (launch, cancel, forget, resume, relaunch), so a new write tool without a constitution entry fails; (d) ROADMAP has neither deleted row and still has the credential and write-tool rows with their 6.0.0 notes; (e) PRINCIPLES.md has a 6.0.0 entry and no longer says the run-index rule waits.

## 7. Green
`tests/constitution_checks_exist_test.sh` passes (it does on 704e514). Full `bash tests/run_all.sh` green (WSL).

## Out of scope
The constitution text, CHANGELOG.md, platform code, hooks, docs/TESTING.md, any other doc. Manual check by the reviewer: `git diff origin/v3...HEAD -- README.md CLAUDE.md` shows only the version cite.
