# 結果階段第一刀：摘要卡＋「輸出」分頁＋其餘分頁沿用或標之後開放 progress ledger

- [x] RED：`platform/tests/test_web_results_outputs.py`（ro01–ro14，涵蓋 TC-001…TC-093 的自動項）
- [x] `jobs.latest_listing(state_path, ce_name, path)`：唯讀，找同環境、同路徑最新一筆 list_site_files（不新增資料表、不需 migration）
- [x] `actions.run_outputs(index_path, platform_path, run_id, *, caller, relist=False, enqueue=True)`：擁有者規則、最新 launch 的 `run_folder/results`、不阻塞、loading／ready／error／unavailable、逾期排隊中的工作視為錯誤
- [x] `web_board.py`：結果階段頁（四張摘要卡、四個分頁、四個「之後開放」灰字、輸出分頁四種狀態）；自動更新網址不帶 `relist`
- [x] `web.py`：只在 run 頁 GET 呼叫 `actions.run_outputs`，不加路由
- [x] `docs/PLATFORM.md`：一段「Results stage: the output list」

## 有意的改動（PR 要寫明）

- **修正輪（verifier 退回 TC-053／054／093）**：`mcp_server.py` 登記同名唯讀工具 `run_outputs(run_id)`，本體只是一次 `actions.run_outputs(...)` 呼叫（和其他讀工具同形）。擁有者規則仍在動作層。上一輪「網頁專用、暫無 MCP 工具」的偏離撤回。
- `tests/test_web_parity.py`：`run_outputs` 從 `WEB_ONLY` 移到 `WEB_ROUTES`（網頁走 `GET /?run=<id>&stage=results`，同名 MCP 工具）；`tests/test_actions_layer.py`：`READ_NAMES` 加 `run_outputs`，`BASELINE` 的 tools 加一筆新工具（其餘六筆逐字不變）。
- **連動更新的既有「工具清單釘死」斷言（只在期望清單／數量加入 `run_outputs`，沒有放寬任何比對；計畫範圍只點名 parity 與 actions_layer，其餘是新工具的必然連動，PR 要寫明）**：`test_chat_tools.py:15`（READ_ONLY）、`test_estimate_su.py:297`、`test_gcb_ce.py:776`、`test_gcb_launch.py:1068-1069`（12→13）、`test_guidance.py:26`（READ_TOOLS）、`test_http_site_samplesheet.py:562`、`test_human_channel.py:159`、`test_keep_submissions.py:705`、`test_launch_platform.py:304`、`test_mcp.py:63,95`、`test_oauth_mcp.py:44,329`（12→13、清單）、`test_pat.py:383,751`（12→13、7→8）、`test_resume_entrypoints.py:46`、`test_station_envs.py:381`、`test_station_launch.py:729`、`test_su_in_get_run.py:412`（12→13）、`test_web_board.py:1192`（tn05）。
- 瀏覽器聊天的工具清單是從 MCP 伺服器推出來的，所以 `run_outputs` 也會出現在聊天可用的唯讀工具裡（`chat_tools.py` 沒改；它是唯讀，過 `classify_check`）。
- TC-093：`actions._outputs_reason` 多一道 `compute_envs.looks_like_credential`——站台回的訊息長得像憑證時，不原樣顯示，改顯示「站台讀不到這個資料夾」。`test_ro14` 改成植入假憑證（運算環境設定與說明、工作的參數與結果、站台訊息），檢查 ready／error 頁面（中英）、MCP 回覆、日誌、標準輸出都沒有它；拿掉過濾時此測試會紅。
- 外觀：新增 CSS 只有 `.otbl code{overflow-wrap:anywhere}` 與 `.ostat{…}`（沿用既有間距 8px），沒有新色碼。

## 改寫的既有斷言（裁決 4：舊→新＋理由）

1. `platform/tests/test_web_board.py:539`（`test_tch21_stage_bodies`）：舊 `"10-18 09:05" in …c.get("/?run=" + b)`（成功 run 的預設頁顯示任務卡的開始時間）→ 新 `…"/?run=" + b + "&tab=info"`。理由：結果階段不再有任務卡，開始時間改在「執行資訊」分頁。
2. `platform/tests/test_web_board.py:1265`（`test_tcs51_no_time_in_right_column`）：舊 `"10-18 09:12" in …c.get("/?run=" + s)`（結束時間在任務卡）→ 新 `…"/?run=" + s + "&tab=info"`。理由同上。
3. `platform/tests/test_web_running.py:361`（`test_n03_n04_other_stages_unchanged`）：舊迴圈含 `stage=results&tab=info`（斷言成功 run 的結果階段沒有分頁列與摘要卡）→ 新只留 `stage=launch`。理由：本任務就是要讓成功 run 的結果階段有摘要卡與分頁列，該斷言與需求直接相反；新行為由 `test_web_results_outputs.py` 驗證。

## 沒做／問題

- `docs/TESTING.md` 沒有對應 TC-075／078／084／086 的手動步驟（不在計畫檔案範圍內），驗收時這幾條會是 UNVERIFIED。
- 費用卡：與執行階段相同寫法（`SU —`），沒有自創數字。

## 修正輪補記：文件檢查與另一支釘死的清單

- `platform/tests/test_launch_e2e.py:185`（`test_tc010_tc061_*`）：期望的工具清單加 `run_outputs`。
- `tests/platform_storage_doc_test.sh:140,142`（文件寫「幾個唯讀工具／幾個工具」的檢查）：`seven read-only tools`→`eight read-only tools`、`Twelve tools.`→`Thirteen tools.`，與 `docs/PLATFORM.md` 同步改（文件說的工具數必須和程式一致，這支測試就是在守這件事）。
