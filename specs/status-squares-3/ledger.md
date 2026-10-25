# 分析狀態一律色塊＋詞、三種（執行中／失敗／完成） progress ledger

- [x] 實作：`platform/abf_platform/web_board.py`——刪 `SYMBOLS`／`_sym`，所有分析狀態改色塊＋詞（左欄、標題徽章、資訊表、階段列、通知等級、送出頁來源 run）；三詞 執行中／完成／失敗（lost→失敗，未知→灰色塊＋未知）；`state-unknown` 用既有 `--muted`／`--sunken`；任務計數「成功→完成」「Succeeded→Done」；通知等級徽章改用分析狀態詞；無通知句改「目前沒有通知／No notices」。
- [x] 新測試 `platform/tests/test_web_status_squares_3.py`（ss01–ss05 與 TC-001..047 自動項）。
- [x] `DESIGN.md` States 一句、`docs/TESTING.md` 新增一節手動步驟。
- 沒動：引導式送出 ✓ ● ○、設定頁運算環境 ✓ ✗ —、輸出分頁 ⟳ ✗ 與打包清單 ✓（裁決 4、6）。

## 改寫的既有斷言（只換字串，舊→新＋理由）

理由通則：狀態符號（▶ ✓ ✗）換成色塊 `class="sq"`；狀態詞「成功／Succeeded」統一為「完成／Done」；通知等級「待處理／Pending」換成該分析的狀態詞（裁決 7）；無通知句換字（裁決 7）。沒有刪斷言、沒有跳過。

- `test_web_actions.py::test_tc042_tc043_pending_pill_and_empty_lines`：等級徽章字樣 待處理→失敗、Pending→Failed；「目前沒有待處理的事」→「目前沒有通知」；「Nothing pending」→「No notices」。理由：裁決 7。
- `test_web_actions.py::test_tc044_tc045_status_is_a_square_plus_a_word_and_no_new_glyph`：徽章 `"Pending" in pill`→`"Failed" in pill`。理由：裁決 7。
- `test_web_board.py::test_tcs19_s20_left_column`：`want` 的 ▶／✗／✗／✓→`class="sq"`。理由：符號改色塊。
- `test_web_board.py::test_tcs24_s25_right_head`：「目前沒有待處理的事」→「目前沒有通知」。理由：裁決 7。
- `test_web_board.py::test_tcl21_item_is_one_link`：▶／✓／✗→`class="sq"`。
- `test_web_board.py::test_tcl22_l23_numbers_and_done`：`x.split()[1]`→`x.split()[0]`。理由：列文字前面少了符號一個字。
- `test_web_board.py::test_tch21_stage_bodies`：任務計數標籤「成功」→「完成」（裁決 5）。
- `test_web_board.py::test_tch08_states_and_symbols`：▶✓✗→`class="sq"`；`startswith(sym)`→`sym in`；徽章 regex 的符號換成 `<span class="sq"></span>`＋詞；右欄 `"待處理" in`→狀態詞 in 並加 `"待處理" not in`。
- `test_web_board.py::test_tch21 階段列（stage strip 名稱）`：`n.replace("✓ ", "")`→直接比 `names`（階段名稱不變，符號不存在）。
- `test_web_board.py::test_tcs29_stage_strip_style`：`"✓" in plain(cell)`→`'class="sq"' in cell`（launch、running 有色塊，results 沒有）。
- `test_web_board.py::test_tcl14_l15_l16_middle`：標題徽章 regex 加 `<span class="sq"></span>`、`"✗"`→`'class="sq"'`；任務計數「成功」→「完成」。
- `test_web_board.py::test_tcs35_nothing_to_notify`：「目前沒有待處理的事」→「目前沒有通知」。
- `test_web_board.py::test_tcl32_l33_english`：任務計數 `succeeded`→`done`。
- `test_web_board.py::test_r10_reason_marker_left_tag_and_wrapping`：左欄英文詞 `Succeeded`→`Done`。
- `test_web_fixes_1.py::test_f05_failed_stage_cell`：階段格文字「✗ 執行」→「執行」＋失敗色塊在；「✓ 送出」→「送出」；「✗ Run」→「Run」；「✓ 執行中」→「執行中」＋完成色塊在。理由：裁決 8。
- `test_web_running.py::test_r01_r13_failed_and_lost_notice_fields`：`"待處理" in`→`"失敗" in` 並加 `"待處理" not in`。
- `test_web_running.py::test_r12_r14_english_and_missing_data`：`"Pending" in`→`"Failed" in` 並加 `"Pending" not in`。
- `test_web_running.py::test_r34_empty_attention`：「目前沒有待處理的事」→「目前沒有通知」。
- `test_web_running.py::test_r40_r44_title_and_cards`：`"✗ 失敗" in plain(mid)`→色塊＋失敗的 HTML 片段。
- `test_web_running.py::test_r45_r52_current_step_and_duration`：「目前沒有待處理的事」→「目前沒有通知」、「Nothing pending」→「No notices」。
- `test_web_running.py::test_r55_r58_tasks_bar_and_legend`：標籤「成功」→「完成」、`Succeeded`→`Done`（裁決 5）。
- `test_web_running.py::test_r79_r92_tab_contents`：資訊分頁 `"✗ 失敗" in info`→色塊＋失敗的 HTML 片段。
- `test_web_results_outputs.py::test_ro01_results_stage_has_cards_and_tabs`：`"✓" in plain(m)`→`'class="sq"' in m`。
- `test_web_results_outputs.py::test_ro01b_other_tabs_reuse_the_running_stage_bodies`：`"✓" in info`→`'class="sq"' in info`。
- `test_web_v2_skeleton.py::test_v01_root_opens_newest_failed_run`：每列含 ▶／✓／✗→每列結尾是三詞之一。
- `test_web_v2_skeleton.py::test_v04_only_three_state_words`：列文字少了符號；徽章 `✗ 失敗`→色塊＋失敗；英文 `✓ ann-done Succeeded`→`ann-done Done`，其餘符號去掉。
- `test_web_v2_skeleton.py::test_v06_right_is_this_analysis_only`：「目前沒有待處理的事」→「目前沒有通知」。
- `test_web_v2_skeleton.py::test_v07_failure_notice_fields`：等級徽章 待處理→失敗（兩處）。
- `test_web_v2_skeleton.py::test_v14_english`：等級徽章 Pending→Failed。

## 合併 origin/v3 後：費用頁（#215）

- `platform/abf_platform/web_cost.py`：每分析表狀態欄，執行中的列改為 `<span class="state-running"><span class="sq"></span> 執行中／Running</span>`（原「⟳ 執行中／⟳ Running」）；「≈ 估算・帳單未到」是帳單狀態，照舊。
- `test_web_status_squares_3.py::test_ss01_no_state_glyphs`：加掃 `/usage`（zh、en）：無 ▶✓✗⏸⟳，且有色塊＋詞。
- 改寫的既有斷言（只換字串，去掉「⟳ 」）：
  - `test_web_cost.py` co06：`rows["run-live"][4]`、`rows["run-lost"][4]` 的 `"⟳ 執行中"`→`"執行中"`。
  - `test_web_cost.py` 英文頁：`rows["run-live"][4] == "⟳ Running"`→`"Running"`。
  - `test_web_cost.py::test_status_cells_have_symbol_and_word`（TC-037）：regex `^(⟳ 執行中|≈ 估算・帳單未到)$`→`^(執行中|≈ 估算・帳單未到)$`。
