# 網頁改成 DESIGN.md v2 骨架（左欄清單、三狀態、右欄 Seqera 式失敗通知） progress ledger

## Done

- [x] D1 `status._view` carries `project` (the run's `project_name`, `None` when the column is missing or NULL); `list_runs` and `get_run` both give it. No migration.
- [x] D2 Three states: `SYMBOLS["lost"]` is `✗`, lost takes the failed style class (the `.state-lost` rule is gone), `state_succeeded` is 完成, `state_lost` is the same word as `state_failed`. `chip_*` (the `/launch` squares) untouched.
- [x] D3 `/` has no page of its own: `web_board.default_run` picks the newest failed or lost run of the caller (`list_runs` order), else the newest, and `web.board_page` draws that run's page at the same URL; no run at all draws 還沒有分析 and a 「＋ 新分析」 link to `/launch`. `read_details`/`read_reasons` and the Now page, the attention and running cards, the red count are gone.
- [x] D4 Left column: runs grouped by `project` (an `h3` per group, ordered by each group's newest run, 未分專案 last), two lines per row (name + symbol + state word; `stage · detail`), `＋ 新分析` on top.
- [x] D5 Middle column: `主視窗` / grey `終端機 之後開放` under the title; the notice card is gone from the middle.
- [x] D6 Right column: head "這個分析的對話" + run name; for a failed or lost run one `<article class="notice">` with the level pill (待處理, ruling 2), the time as HH:mm, Step / Reason / Next in a `<dl>`, and exactly one button (`failure.actions[0]`, through `Acts.form`); a run that did not fail says 目前沒有待處理的事 (ruling 3); last, grey 「問這個分析 之後開放」. No other run's data.
- [x] D7 Dead CSS of the removed parts (`.nowline`, `.red`, `.cards`, `.lines`, `.line`, `.item*`, `.tabs`, `.tally`, `.group*`, `.items`, `.aname`, `.ntitle`, `.num`) removed; new rules only reuse existing tokens (`.r1`, `.r2`, `h3`, `.proj`, `.views`).
- [x] New tests: `platform/tests/test_web_v2_skeleton.py` (test_v01 .. v16, plus v01b, v05b, v07b, v08b for the TCs that need their own seed).

## Rewritten old assertions (old -> new)

`test_web_board.py` (helpers `group_head`, `items`, `card`, `card_lines`, `card_notices`, `notice_cause`, `card_num`, `tally`, `_red_n` removed with the things they read):

- `test_tcs19_s20_left_column`: first link 現在 -> 「＋ 新分析」 (`/launch`); lost row `⏸ 失聯/暫停` -> `✗ 失敗`, class `state-failed`; succeeded text 成功 -> 完成.
- `test_tcs21_s22_left_grey_and_settings`: forms counted in the whole page -> in the left column (the opened run's own buttons are in the middle).
- `test_tcs23_selected_mark`: `現在` marked on `/` -> exactly one run row marked on `/` and on `?run=`; right column has no `here`.
- `test_tcs24_s25_right_head`: 分析進度／聊天／全部分析／搜尋 head -> 「這個分析的對話」+ name + 目前沒有待處理的事 + grey 問這個分析.
- `test_tcs26_counts_row`: tally `▶ 3 ! 3 ✓ 4` -> no tally.
- `test_tch22_l19_l20_groups`: right-column groups 執行中（4）／結果（3） -> left-column project groups (`h3`), none in the right column.
- `test_tcs01_ten_runs_at_once`: every run in left and right, group counts, tally, card numbers -> every run in the left column only; the right column names the opened run only.
- `test_tcl21_item_is_one_link`, `test_tcl22_l23_numbers_and_done`, `test_tcs27_s28_item_lines`: right-column items (numbers, `n/m`, progress bars, one-line reason) -> left rows and their second line (`執行 · 8 / 10`, `執行 · —`, `執行 · 站台沒有回應`, `結果`).
- `test_tcl25_l26_failed_key_fact`, `test_r10_reason_marker_left_tag_and_wrapping`: reason cut at 79 characters plus an ellipsis, first line only -> the Reason field of the right-hand notice: last three non-empty lines, each cut at `REASON_CAP` (80) plus an ellipsis; no reason and no task -> a dash (was 原因未記錄). Left tags: 成功 -> 完成, 失聯/暫停 -> 失敗; wrapping classes `.item/.line/.why` -> `.notice/.scard`.
- `test_tcl28_selected_item`, `test_tcl29_...`, `test_tcl30_...`, `test_tcs37_attention_cap`: right-column item mark, up to 100 `get_run` calls, numbers 250..151, attention card of 250 -> left row mark (also the default one), exactly one `get_run` (the opened run), left cap 100 plus 還有 150 筆, one notice.
- `test_tch10_stage_param`: `/?stage=running` showed the Now page -> shows the default run's page at that stage.
- `test_tch08_states_and_symbols`: `⏸`／失聯 -> `✗`／失敗; card lines -> the notice pill on the right.
- `test_tcs32_s33_s34_now_page`, `test_tcs35_nothing_to_notify`, `test_tcs36_cards_are_read_only`, `test_tch18_empty_states`, `test_tch03_only_own_runs`, `test_tch12d_item_fact_is_escaped`, `test_tcl31_default_is_chinese`, `test_tcl34_english_reason_not_recorded`, `test_tcs50_red_number_matches_attention`, `test_tcs51_no_time_in_right_column`: Now page / cards / red number / right-column items -> the default-run page, the right-column notice (Reason, escaping, dash), `主視窗`, no red number (default run per person), HH:mm in the notice only.
- `test_tcl35_l36_l37_switch_and_links`: "at least 8 links" -> "at least 6" (the right column no longer links every run); the rest of the assertion unchanged.
- `test_tn10_n13_n17_n19_n20_nothing_beyond_the_plan`: `終端機`／`Terminal` removed from the list of words that must not appear (they are now the grey switch).

`test_web_running.py`: `test_r01_r13_...`, `test_r12_r14_...`, `test_r07_r19_...`, `test_r30_r36_...`, `test_r34_...`: middle-column notice (問題／原因／可選動作, two buttons, 分析失敗, 與站台失去聯絡, `MM-DD HH:mm`, 原因未記錄) -> right-column notice (步驟／原因／之後, one button, `HH:mm`, dash); the attention card tests -> the right column of the opened run. `test_r60_r78_order_and_tabs`: `<article` in the order list -> `class="views"`, and no `<article` in the middle. `test_r103_r114_...`: notice form count 2/3/0 -> 1/1/0.

`test_web_actions.py` (ruling 5, the one allowed): `test_tc004_notices_carry_real_forms`: both `resume` and `relaunch` forms in the middle `<article>` -> exactly one form in the right-hand `<article>`, verb = `failure.actions[0]`, POST gives a confirmation id.

Untouched: `test_confirm_page.py`, `test_web_confirm_plain.py`, `test_web_parity.py`, `test_web_login.py`, `test_web_chrome_origin.py`, `docs/TESTING.md`, `failures.py`, `actions/__init__.py`, `/act/*`.

## Not done (as planned)

Terminal, automatic resume, OTP, the chat box, automatic and downstream notices: other lanes. Screenshots: developer-agent.

## Known environment red (ruling 10)

`tests/init_workspace_test.sh` "site side with no run area known fails clearly" returns rc 1 (expected 2) on the desktop WSL because `mkdir /work` is refused; base `1db9ad5` is red the same way and GitHub CI is green. Excluded from "full suite green"; the test is untouched. Full suite: 117/118, only this one red.

## Ruling 11 (overrides contract TC-096 for two files)

- `test_failures.py::test_untouched_modules_do_not_know_failure` (TC-043): module tuple `("web.py", "web_board.py", "receiver.py", "status.py")` -> `("web.py", "receiver.py", "status.py")`; `web_board.py` reads the run's failure field.
- `test_launch_nextflow.py` (loop at the end of the TC-045 test): `"已取消"` absent from every `abf_platform/*.py` -> same for every file except `web_board.py`.
- `web_board.py`: the concatenation dodges `"fail" + "ure"` and `"已取" "消"` became plain literals.
- `test_launch_platform.py::test_tc045_the_platform_writes_no_run_state_called_cancelled_anywhere`: quoted `cancelled|canceled|已取消` absent from every `abf_platform/*.py` -> same for every file except `web_board.py` (display label only).
- `test_resume_scope.py::test_tc160_...`: quoted `resumed|cancelled|canceled|已取消|已續跑` absent from every `source_files()` entry -> same except `web_board.py`.
