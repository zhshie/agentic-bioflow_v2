# Ledger 012b

Write actions from the web: Resume / Re-run / Cancel buttons and a plain launch form, each ending on the existing confirmation page `/c/<id>`.

## Done

- [x] W1 Resume / Re-run / Cancel are real POST forms (`/act/{resume,relaunch,cancel}`) on the run page and on every notice. Each calls `request_resume` / `request_relaunch` / `request_cancel` for the logged-in caller and answers 303 to `/c/<id>`; a refusal is one plain line at the top of the run's page (409), nothing queued. The CSRF token is per login and per run (`act:<run id>`); the same-origin check is the one of 009i.
- [x] W2 `/launch`: one plain form (pipeline, pinned revision, run name, samplesheet from the caller's own uploads, environment from `list_compute_envs`, `key: value` parameters). Submit calls `request_launch`, 303 to `/c/<id>`. Quick launch is `/launch?from=<run id>`: prefilled from the earlier run's kept content (new read action `launch_prefill`), else a plain line says it is not kept.
- [x] W3 Parity: `launch`, `cancel` and `list_compute_envs` moved from OWED to WEB_ROUTES (the routes call `request_launch` / `request_cancel`, never `launch` / `cancel`); the two read helpers `launch_prefill` and `list_samplesheets` are in WEB_ONLY. OWED shrank from 7 names to 4 (`get_compute_env`, `list_agents`, `list_site_files`, `forget`). `resume` / `relaunch` have no action of that name: their routes are tied to `request_resume` / `request_relaunch` in the test's `WEB_VIA_REQUEST`.
- [x] W4 Wording: the two banned phrases are nowhere in `platform/`; the level pill is the word for "pending" (待處理 / "Pending") with a small coloured square (its own element `.sq`) in place of the old "!" glyph; the empty line of the notices card is 「目前沒有待處理的事」 / "Nothing pending".
- [x] W5 Zero JS, one stylesheet (grown by a few rules, all with tokens of DESIGN.md), no `style=`, owner rule through the action layer, `?lang=en` for every new string, Asia/Taipei times.
- [x] No migration: the databases did not change (pinned by `test_tc063_no_schema_change`).

## Glyphs that stay in the markup, for the later visual pass (W4)

Existing markup whose old tests pin the glyph; the new markup of this task has none.

- `▶ ✓ ✗ ⏸` in `SYMBOLS`: the rows of the left column, the right column items, the header badge of a run, the status cell of the Info tab.
- `✓` before a finished stage in the five-stage strip; `←` / `→` in the previous / next stage links.
- `▶ ! ✓` in the tally line at the top of the right column.
- `＋ ↑` in the greyed "new project" / "upload data" words of the left column.

## Old tests changed (W4, TC-050): only the string or the count, no assertion dropped or skipped

- `test_web_board.py::test_tchl08_states_and_symbols`: the level pill test `"!" in` and the old action-needed word became `class="sq"` in and 待處理 in (same count).
- `test_web_board.py::test_tcs36_cards_are_read_only`: the Now page cards are no longer form-free; the two "no button, no form" asserts became "every form is a POST to `/act/...`" and "one button per form"; the greyed-text count became a button count.
- `test_web_board.py::test_tch11_read_only`: the forms of a board page are the log-out form plus, only on a failed run's page, the `/act/` forms; the route table lists `/act/{verb}` and `/launch` too.
- `test_web_board.py::test_tn02_no_detail_logs_or_resume`: `action="..."` is stripped with `href` before looking for the word resume (the buttons post to `/act/resume`).
- `test_web_board.py::test_tn04_other_paths_stay_missing`: `/launch` left the list of missing paths (it is the launch page now).
- `test_web_board.py::test_tn10_n13_n17_n19_n20_nothing_beyond_the_plan`: links may also go to `/launch` and carry `?from=`.
- `test_web_running.py::test_r01_r13_failed_and_lost_notice_fields`, `test_r12_r14_english_and_missing_data`, `test_r40_r44_title_and_cards`, `test_r45_r52_current_step_and_duration`: the old action-needed words, "coming later" and 「之後開放」 became 待處理 / "Pending" / nothing; the "no form, no button" asserts became counts of the real buttons (2 on a failed notice, 3 in the header).
- `test_web_running.py::test_r103_r114_limits_and_readonly`: the form count per page is 1 log-out + 3 header buttons + the notice's buttons (2 failed, 3 lost, 0 running); `/launch` left the list of missing paths.
- `test_resume_scope.py::test_tc146_there_is_no_web_page_no_stage_board_no_button_and_no_list_attempts`: 011 and 012b did what 009e left out; `web.py` may now name `request_resume` / `request_relaunch` (and nothing of `prepare_*`), `list_attempts` still does not exist.
- `test_resume_scope.py::test_tc150_nothing_calls_a_resume_or_a_relaunch_by_itself`: `abf_platform/web.py` joined the files that may call `request_resume` / `request_relaunch` (they only ask a person); it left the "quiet" list.
- `test_web_running.py::test_r30_r36_attention_card_uses_the_component`: the notice of the failed run is found by its link, not by the text "f1" (the buttons' hex tokens can contain it).
- `test_owner_binding.py::test_tc068_no_new_way_to_log_in`, `test_confirm_page.py::test_tcg04_g05_g06_...`: the route tables list `/launch` and `/act/{verb}` (none of them logs anybody in or confirms anything); `/launch` left the missing-path list.
- `test_web_parity.py`: the tables and the OWED literal as in W3 above (the plan names this test); `test_tch16h` uses `forget` for the "an owed name called by the web is caught" example because `launch` is no longer owed.

## Not done on purpose (out of scope)

Upload and samplesheet creation (012c), the 7-step guided launch with schema groups and the diagram (012b-2), the cost page (012d), results (011c), chat, a forget button, any JS. The stage-1 placeholder card on a run's page still says `012b`.

## Questions left for the maintainer

- The status words: the plan says Running / 待處理 / Failed / Done as small squares; the existing rows, badges and tally still carry the old glyphs (listed above). English "Done" is used only on the new chip of the quick-launch line; the older English state word for a finished run is still "Succeeded".
- `ui` rule vs plan: DESIGN.md says symbol plus word plus colour; the plan says square plus word. The new chip and pill follow the plan (the square is its own element with the word beside it).
