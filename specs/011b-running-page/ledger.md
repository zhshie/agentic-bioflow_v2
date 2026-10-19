# Ledger 011b

## Tasks

- [x] RED `2793134`: `platform/tests/test_web_running.py` (notice fields zh/en, Now card, four cards, tasks bar, five tabs, limits, read-only).
- [x] GREEN: `web_board.py` (`_notice`, `_sum_cards`, `_tasks_bar`, `tab_body`, `_running_body`, STRINGS zh/en, stylesheet classes `.notice .sumcards .rtabs .tbl .soon`), `web.py` (`read_details`: reason and first failed task per failed run; `?tab=`; the clock).
- [x] Docs: `docs/TESTING.md` (011b section, TC-D05), `CHANGELOG.md`.
- [ ] Manual (verifier / maintainer): TC-V01 to V06 screenshots at 1440 and 390 (zh, en), TC-D01 to D04, D07 by reading this ledger and the diff.

No route, table, column or migration was added: `?tab=` rides on the existing `GET /`.

## Changed pins (old / new / reason), TC-D01, TC-D02

All in `platform/tests/test_web_board.py`; each change is the smallest that keeps the test's purpose.

| Test | Old | New | Reason |
|---|---|---|---|
| `test_tcl25_l26_failed_key_fact` (TC-L25, TC-S34) | attention card line `endswith(A*79 + "…")`, short reason, `原因未記錄` | same values read from the notice's 原因 field (helpers `card_notices`, `notice_cause`) | N1: the card's items are formal notices; the right-column item pin is unchanged |
| `test_r10_reason_marker_left_tag_and_wrapping` (R10-1) | card line ends with the cut / exact reason; full reason in `/?run=id-cut` | same values from the 原因 field; full reason looked for in `/?run=id-cut&tab=info` | N1; and TC-R11 forbids the reason text outside the 原因 field on the default tab, so the whole text moved to the Run info tab |
| `test_tcl34_english_reason_not_recorded` (TC-L34) | card line ends with "reason not recorded" | the notice's Cause field is "reason not recorded" | Ruling Q1: the pin moves to the component's field; right-column item unchanged |
| `test_tcs32_s33_s34_now_page` (TC-S32 to S34) | attention items per run with `✗ 失敗`, reason at the end, `⏸ 失聯/暫停` without 原因 | notices per run: state class, title 分析失敗 / 與站台失去聯絡, 原因 field (`Out of memory`, `原因未記錄`, `三次心跳沒有回應`) | N1; Q1; a lost notice now has a cause |
| `test_tch08_states_and_symbols` (TC-S30, TC-H08) | failed and lost have one card line with the state label | failed and lost have one notice with the state class, `!` and 需要處理 | N1; the symbol, word and colour triple is the level pill |
| `test_tcs36_cards_are_read_only` (TC-S36) | words 重跑 and 續跑 absent from the middle column | still no form, button or non-run link; 重跑／續跑 appear only as greyed `gbtn` spans and the options line | N1 requires greyed 續跑／重跑 |
| `test_tcs37_attention_cap` (TC-S37) | 100 card lines | 100 notices; "還有 150 筆" unchanged | N1 |
| `test_tcl14_l15_l16_middle` (TC-L14 to L16) | all `<dt>/<dd>` pairs of the middle column are the 7 counts | the pairs inside `<dl class="counts">` are the 7 counts | the page also has the notice's field list |
| `test_tn02_no_detail_logs_or_resume` (TC-N02) | page has no `logs` word | same, after removing `href` attributes | the Logs tab link says `tab=logs`; the tab is a grey panel with no log text |
| `test_tn10_n13_n17_n19_n20_nothing_beyond_the_plan` (TC-N10 etc.) | query keys `{run, stage, lang}`; words 目前步驟, Current step, Metrics absent | keys also `tab`; those three words dropped from the absent list | 011b adds `?tab=`, the four summary cards and the Metrics tab |

My own tests in `test_web_running.py` were adjusted once during GREEN: the `<1m` check unescapes HTML; the "every link keeps lang=en" check allows exactly the 中 link of the language switch; a lost run with no `last_message_at` is fed to `_notice` directly because the column is NOT NULL in index.db.

No assertion was deleted, skipped or loosened without a replacement.

## Owed (Q7), TC-D03

The action layer does not give these yet, so the page shows "—" or leaves them out until it does. `#138` (read_task_log) adds `workdir` and `cancel_requested_at` to `get_run`; it had not landed in v3 when this was built, and the page does not depend on it. Once it lands, the page uses them with no change here:

- compute environment name: card 運算環境 is "—" (it reads `run["compute_env"]` if the action layer ever returns it);
- work directory column of the failed tasks table: "—" (shows `workdir` when the task has it; tested through `tab_body`);
- launch facts such as `cancel_requested_at` on the Run info tab: absent (shown as `MM-DD HH:mm` when present; tested through `tab_body`).

## Decisions where the plan was silent

- The 011a grey block with the full failure reason is no longer on the stage page; the full text is on the Run info tab (TC-R11 keeps it out of the default tab).
- A succeeded run opened with `&stage=running` shows the running stage page (no notice).
- Duration of a lost run runs to "now".
- Task bar fill rule: unchanged from 011a, (succeeded + cached) / total.
