# 費用頁以運算環境為單位＋分析頁費用列 progress ledger

## 1. 作法 1 查證

- `su.month_total` 在 v3 頁面沒有人用。`docs/PLATFORM.md` 說 SU 卡用它是錯的。
- 舊 `my_usage` 有三個洞：AWS／Azure／K8s 被當成 nchc；已刪除的環境被當成 nchc；總數與列的站台不一致。

## 2. `_launch_facts` 鍵

`cloud_cost._launch_facts` 現在多回 `ce`、`platform`，舊三鍵不變。

## 3. 進度（executor）

- [x] `cloud_cost._launch_facts` 加 `ce`、`platform`。
- [x] `actions.my_usage` 改為 `{month, environments, cloud}`（頂層恰為合約三鍵；匯率日期改放各 SU 環境的 `usd_rate_as_of`，修正輪）；`su`、`runs` 兩鍵刪除；不呼叫 `su.month_total`。
- [x] `actions.run_usage`（只給網頁，`WEB_ONLY`，不是 MCP 工具）。
- [x] `web_cost.py` 重寫：上限與剩餘合成頁面最上方一行 `<p class="muted">`（修正輪由兩張卡改回一行）＋固定句＋每個環境一個 `<details>`，單一環境時預設展開；`web_board.cost_row` 放進分析頁。
- [x] 測試：`tests/test_cost_by_env.py`（新）；既有測試依「允許改動」改形狀。
- [x] DESIGN.md 第 11 項與 `test_cost_docs_spec.py` L33 照裁決改。

## 4. 範圍查證（對 base b96e916a，`git diff --stat`）

只動了：`DESIGN.md`（第 11 項）、`platform/abf_platform/{actions/__init__,cloud_cost,mcp_server,web,web_board,web_cost}.py`、測試檔（`test_cost_by_env` 新增；`test_web_cost`、`test_web_bugs_b`、`test_su_usd`、`test_web_parity`、`test_actions_layer`、`test_web_wording_sweep`、`test_cost_docs_spec`）、`docs/TESTING.md`、`specs/cost-page-by-environment/*`。`docs/PLATFORM.md`、`docs/CLOUD.md`、`su.py`、`.github/`、`web_board._mast` 未動；沒有新資料表或欄位。

## 5. 給 developer-agent：cost-docs-rewrite 該更正的 PLATFORM.md

- 本 worktree 的 `docs/PLATFORM.md` 776–788 行（「The cost page」一節；origin/v3 上是 770–782 行）：
  - 782 行「NCHC SU (card): `su.month_total` …」寫錯了：費用頁從沒用 `su.month_total`，現在也不是卡片，而是每個 Slurm 環境一行的小計。
  - 783 行「Cloud used (card)」同樣不再是卡片，是每個 Google Batch 環境一行的小計。
  - 卡片全部消失；只剩頁面最上方一行小字顯示雲端上限與雲端剩餘（修正輪：先前誤做成兩張卡，已改回計畫的一行）。
  - 788 行 masthead 那句仍成立（本任務沒動 masthead）。
  - 應補：`my_usage` 新形狀、`run_usage`、單位規則（slurm 為 SU、googlebatch 為 USD、aws／az／k8s 為 USD 但尚無估算、刪除的環境與沒有 hand-off 紀錄的 run 是 unit None）。

## 6. planIssues 待決 1–5 的最終處理

1. 上限行：留一行，不改上限語意或寫入口。
2. masthead：沒動，後續任務。
3. AWS／Azure／K8s：顯示 `—`＋「尚無此環境的費用估算」，單位 USD，值 None，不估算。
4. 範圍字句：「整個分析（含失敗的步驟）」。`su.run_tasks` 與 `cloud_cost` 都不依 task 狀態過濾，字句成立。
5. 環境小計遇到無法計算的分析：已知加總＋「另有 N 個分析無法計算」；整個環境都算不出來時顯示 `—` 加第一個原因。

偏離一（修正輪改）：頂層鍵已回到合約的 `month`、`environments`、`cloud`。但 TC-016/069 要求頁面註腳帶匯率日期（`usd_note` 一字不差），而網頁路由只准呼叫 `my_usage`，日期只能由 `my_usage` 帶出；因此各 Slurm（SU）環境多一個 `usd_rate_as_of`（其餘環境為 None）。TC-028 對環境鍵寫「有 …」未寫「恰為」，這樣字面上不違約，但仍是多一個鍵，請 developer-agent 認可，或改派（例如新增專供網頁的動作）。

偏離二：`test_su_usd.py` TC-071 原斷言「分析頁不讀費率」。新費用列走 `run_usage`（它讀費率），所以該測試把 `actions.run_usage` 換成回 `{}` 的替身，原斷言一字不動。此測試不在「允許改動」清單，在此說明。

## 7. 允許改動的既有斷言與原因

- `test_web_cost.py`：`NOTE_ZH` 換成新固定句；co01（上限一行、不再有卡片，表頭四欄）；co02–co05（卡片數值改看 `environments[*].total` 與上限那一行）；ruling12／13／14（改為各環境各自的總數與小計）；co06、where／amount 列（少了「執行位置」欄，改看環境名）；newest-launch、month-edge（鍵改為 `environments[*].analyses`）；co09 英文；co11 鍵集；not-known 與 status-cells。`table_rows` 與 `seed` 輔助函式改成跨多個表、`seed` 加參數。保留的性質：他人看不到、US$ 不轉換、無 JS／`style=`、CSP hash、讀不到索引不 500、未知值不寫成 0。禁字表只增不減。
- `test_web_bugs_b.py`：L71、L79 卡片標題斷言改為標題列月份（卡片已不存在）；`usage_data()` 回傳形狀換成 `environments`。
- `test_su_usd.py`：note；用到 `su`、`runs` 鍵的斷言換成 `environments`；L476–478 與 L530–533 沒動。
- `test_web_wording_sweep.py`：`th_where` 換成 `th_usage`（「用量」），禁字表沒放寬。
- `test_web_parity.py`：`WEB_ONLY` 加 `run_usage`。`test_actions_layer.py`：`BASELINE` 的 `my_usage` 說明字。

## 7b. 修正輪（verifier 退回 TC-030／TC-071／TC-099）

- TC-030：`actions._usage_item`、`my_usage`、`run_usage` 對 `_launch_facts` 的 `ce`／`platform` 一律用 `.get`；新增 `test_web_cost.py::test_tc030_old_three_key_facts_do_not_crash`（替身只回舊三鍵；先紅 KeyError 後綠）：`/usage` 回 200、該分析是 `unit None` 的環境、`run_usage` 與分析頁也回 200。
- TC-071：上限列改回頁面最上方恰好一行 `<p class="muted">`（`web_cost._cap_line`，在 note 之前）：「雲端上限：… · 雲端剩餘：…」，未設定時「未設定（由管理員設定）」，過額（本月）時同一行內有 `<span class="state-failed"><span class="sym">⚠</span> 待處理…</span>`。`_card`／`_cards` 刪除，沒有 `sumcards` 留在費用頁。co01／co04／co05／co03／co09 與 test_su_usd tc040／tc053 的斷言改成對這一行（`cap_line()` 輔助函式取代 `cards()`／`card()`）。此前 ledger 兩處互相矛盾（進度寫兩張卡、planIssues 寫一行），現以一行為準。
- TC-099：以下既有測試被改、**不在計畫「允許改動」清單**，必須由維護者或 developer-agent 認可（executor 無權自行核可，也沒有把它們改回，因為改回會讓新增的分析頁費用列表或新 `my_usage` 形狀使它們紅）：`test_web_board` tn10、`test_web_results_outputs` ro04、`test_web_running` r79_r92（「無 `<table`」檢查先扣掉費用列表）；`test_results_files` `mid()`、`test_clean_page` `mask()`（比對前遮掉費用列）；`test_owner_guard`（NO_TOOL）、`test_web_downstream`、`test_k8s_launch`（動作名單與數量 58 到 59、雜湊）；`test_head_nodefail`（讀新形狀）；`test_web_settings_ce_mobile` ce08（STRINGS 雜湊）；`test_su_usd` tc071（`run_usage` 換成回 `{}` 的替身）與 tc058（「卡片 SU 0.00」改成「沒有 Slurm 環境列」）；`test_web_bugs_b` 的 `test_338_past_month_titles_show_month`／`current_month_titles`（卡片標題已不存在，改看標題列月份）。計畫明列者（L71、L79）不在此列。

## 8. 手動項

截圖與 axe 掃描需要瀏覽器，CI 沒有 Chromium，所以是手動：步驟在 `docs/TESTING.md`「費用頁以運算環境為單位」一節。必附 12 張：費用頁多環境 4、分析頁費用列 4、費用頁單一環境 4（1440／390 x zh／en）。executor 沒有拍。

## 9. 全套測試後補修（8 條）

不在「允許改動」清單、但因 `run_usage` 與分析頁費用列而必須動的既有斷言（性質都保留）：`test_owner_guard`（NO_TOOL 加 run_usage）、`test_web_downstream` 與 `test_k8s_launch`（動作名單／數量／雜湊 58 到 59）、`test_web_board` tn10 與 `test_web_results_outputs` ro04（「無 table」改為扣除費用列那一張表後仍無 table）、`test_gcb_ce`／`test_oauth_mcp`（改 `mcp_server.py` 的 my_usage 說明，不再出現 Google 字樣；`BASELINE` 同步）。`run_usage` 以固定名呼叫 `get_run`，使 tcl29「一次頁面讀取只問一次 get_run」不變。
