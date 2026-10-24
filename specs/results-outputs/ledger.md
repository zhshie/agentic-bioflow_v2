# 結果階段第一刀：摘要卡＋「輸出」分頁＋其餘分頁沿用或標之後開放 progress ledger

- [x] RED：`platform/tests/test_web_results_outputs.py`（ro01–ro14，涵蓋 TC-001…TC-093 的自動項）
- [x] `jobs.latest_listing(state_path, ce_name, path)`：唯讀，找同環境、同路徑最新一筆 list_site_files（不新增資料表、不需 migration）
- [x] `actions.run_outputs(index_path, platform_path, run_id, *, caller, relist=False, enqueue=True)`：擁有者規則、最新 launch 的 `run_folder/results`、不阻塞、loading／ready／error／unavailable、逾期排隊中的工作視為錯誤
- [x] `web_board.py`：結果階段頁（四張摘要卡、四個分頁、四個「之後開放」灰字、輸出分頁四種狀態）；自動更新網址不帶 `relist`
- [x] `web.py`：只在 run 頁 GET 呼叫 `actions.run_outputs`，不加路由
- [x] `docs/PLATFORM.md`：一段「Results stage: the output list」

## 有意的改動（PR 要寫明）

- `tests/test_web_parity.py`：`WEB_ONLY` 新增 `run_outputs`（網頁專用的動作，暫無 MCP 工具）。**偏離 TC-053／TC-054 的「MCP 同名 read tool」**：加 MCP 工具會讓約 20 支計畫範圍外的測試變紅（`test_mcp`、`test_human_channel`、`test_web_board::test_tn05` 等都釘死了工具清單），計畫只允許在「parity 測試要求時」登記，而 parity 測試接受 `WEB_ONLY`。要不要補 MCP 工具由維護者決定。
- 外觀：新增 CSS 只有 `.otbl code{overflow-wrap:anywhere}` 與 `.ostat{…}`（沿用既有間距 8px），沒有新色碼。

## 改寫的既有斷言（裁決 4：舊→新＋理由）

1. `platform/tests/test_web_board.py:539`（`test_tch21_stage_bodies`）：舊 `"10-18 09:05" in …c.get("/?run=" + b)`（成功 run 的預設頁顯示任務卡的開始時間）→ 新 `…"/?run=" + b + "&tab=info"`。理由：結果階段不再有任務卡，開始時間改在「執行資訊」分頁。
2. `platform/tests/test_web_board.py:1265`（`test_tcs51_no_time_in_right_column`）：舊 `"10-18 09:12" in …c.get("/?run=" + s)`（結束時間在任務卡）→ 新 `…"/?run=" + s + "&tab=info"`。理由同上。
3. `platform/tests/test_web_running.py:361`（`test_n03_n04_other_stages_unchanged`）：舊迴圈含 `stage=results&tab=info`（斷言成功 run 的結果階段沒有分頁列與摘要卡）→ 新只留 `stage=launch`。理由：本任務就是要讓成功 run 的結果階段有摘要卡與分頁列，該斷言與需求直接相反；新行為由 `test_web_results_outputs.py` 驗證。

## 沒做／問題

- `docs/TESTING.md` 沒有對應 TC-075／078／084／086 的手動步驟（不在計畫檔案範圍內），驗收時這幾條會是 UNVERIFIED。
- 費用卡：與執行階段相同寫法（`SU —`），沒有自創數字。
