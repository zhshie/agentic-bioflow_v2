# 測試案例：安全關卡出事時改成擋下（issue #80，hooks-fail-open-on-timeout）

**規格**：`.specify/bugs/hooks-fail-open-on-timeout/assessment.md`（A 級修補，無維護者範例；官方文件引文與 issue #80 為依據）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：「關卡」＝Claude Code 執行指令前先跑的安全小程式（hooks 下的 confirm_launch.sh 等）。「onFailure block」＝官方開關，關卡超時、當掉或回了看不懂的東西時，改成擋下指令（預設是照樣執行）。「使用中」＝這個對話正在用 agentic-bioflow（憲法 2.0.0）；沒在用時關卡必須安靜。

## User Story 1 — 關卡出事時指令被擋下，不是放行（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | assessment「修法」；issue #80 待辦 1 | 功能 | `hooks/hooks.json` | 讀出所有 PreToolUse 裡執行 `confirm_launch.sh` 的項目（三個 matcher：Bash 類、Seqera/Tower MCP、Write/Edit 類） | 這三項每一項都有 `"onFailure": "block"` | 自動：`tests/hooks_fail_closed_test.sh` |
| TC-002 | 同上 | 功能 | 同上 | 讀出執行 `confirm_cleanup.sh` 的項目 | 有 `"onFailure": "block"` | 自動：`tests/hooks_fail_closed_test.sh` |
| TC-003 | 同上 | 功能 | 同上 | 讀出執行 `guard_plugin_files.sh` 的項目（兩個 matcher） | 兩項都有 `"onFailure": "block"` | 自動：`tests/hooks_fail_closed_test.sh` |
| TC-004 | 同上 | 功能 | 同上 | 讀出執行 `confirm_walkthrough.sh` 的項目 | 有 `"onFailure": "block"` | 自動：`tests/hooks_fail_closed_test.sh` |
| TC-005 | 計畫第 1 點（不動非關卡 hook） | 功能 | 同上 | 讀出 SessionStart、Stop、UserPromptSubmit、PostToolUse 的所有項目 | 全部都沒有 `onFailure`（它們出事不該擋住整個對話或使用者的提問） | 自動：`tests/hooks_fail_closed_test.sh` |
| TC-006 | 計畫第 4 點 (c) | 功能 | 同上 | 讀出每個 PreToolUse 項目的 timeout | 每項仍有 timeout，值仍是 30 | 自動：`tests/hooks_fail_closed_test.sh` |
| TC-007 | 計畫「What changes」 | 功能 | main 的 hooks.json 與修改後的 hooks.json | 逐項比較 | 是合法 JSON；matcher、command 與項目數（PreToolUse 7 項＋其他 4 項）與 main 相同，唯一差別是 PreToolUse 項目多了 onFailure（沒有關卡被順手刪掉或改掉） | 自動：`tests/hooks_fail_closed_test.sh` |
| TC-008 | issue #80 待辦 1；assessment 證據 | 功能 | Claude Code 2.1.295 以上；暫時把某個關卡換成會睡過頭超過 timeout 的假關卡（timeout 設 1 秒、睡 3 秒），掛上 `onFailure: block` | 要 Claude 跑一個普通指令（例如 `ls`） | 指令沒有被執行；畫面出現「failed; blocking because onFailure is "block"」之類的訊息，並指出是哪個關卡 | 手動：`docs/TESTING.md` |
| TC-009 | assessment「Not stated」：外掛的 hooks.json 是否認這個欄位 | 功能 | 以外掛方式安裝修改後的 agentic-bioflow，Claude Code 2.1.296 | 把外掛的任一關卡換成立刻當掉的假關卡（exit 1），再叫 Claude 跑一個普通指令；之後換回真的關卡，打一句會觸發啟動確認的指令 | 假關卡時指令被擋（證明外掛設定檔認 onFailure）；換回真關卡後，啟動指令仍跳出確認，外掛正常載入 | 手動：`docs/TESTING.md` |

## User Story 2 — 平常的指令不會因為這個修法被誤擋（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 計畫第 2 點（稽核）；Done when | 功能 | 使用中的對話；一批普通呼叫：`ls`、`git status`、`cat 某檔`、`echo hi`、寫一個普通檔、編輯一個普通檔、非 Seqera 的 MCP 工具 | 把每一筆餵給四個關卡（confirm_launch、confirm_cleanup、guard_plugin_files、confirm_walkthrough） | 每個關卡的結束碼都是 0 或 2（不是 1、3、127 等；官方文件：其他碼在 onFailure block 下算出事而擋下） | 自動：`tests/gate_exit_contract_test.sh` |
| TC-011 | 同上 | 功能 | 同 TC-010 | 同 TC-010 | 標準輸出若有內容，必須是 Claude Code 讀得懂的合法 JSON（`jq -e .` 通過，且含合法的決定欄位）；沒內容也可以。壞 JSON 在新設定下會被當成出事而擋下 | 自動：`tests/gate_exit_contract_test.sh` |
| TC-012 | 計畫第 2 點「exit non-0/2、缺變數」 | 例外 | 使用中的對話；奇怪的輸入：空輸入、`{}`、缺 `tool_input`、缺 `session_id`、不是 JSON 的文字、`tool_input` 是數字 | 把每一筆餵給四個關卡（特別是有 `set -u` 的 confirm_walkthrough.sh 與 guard_plugin_files.sh） | 結束碼只能是 0 或 2，不會因為沒設定的變數而是 1 | 自動：`tests/gate_exit_contract_test.sh` |
| TC-013 | 同上 | 例外 | 同 TC-012 | 同 TC-012 | 標準輸出為空或合法 JSON | 自動：`tests/gate_exit_contract_test.sh` |
| TC-014 | 憲法 2.0.0「沒在用就安靜」；計畫 (b) | 功能 | 沒在使用外掛的對話（沒有標記、工作資料夾在部署之外、指令與外掛無關），包含一條約 32 KB 的普通長指令（長 `cd` 目標加很多 `../` 的 rm） | 餵給四個關卡 | 每個都在幾秒內結束碼 0 且標準輸出為空（不會因為慢到超時而在別的專案裡擋人） | 自動：`tests/gate_exit_contract_test.sh` |
| TC-015 | 計畫第 2、5 點；assessment「超時＝擋下」 | 功能 | 使用中的對話；一個約 1 MB 的普通 Write 內容；一條約 32 KB 但無害的指令（不含刪除或啟動字樣） | 餵給四個關卡並計時 | 每個關卡在 10 秒內結束（遠低於 timeout 30），結束碼 0 或 2。（會觸發刪除判斷的 32 KB 形狀不在此列，見 TC-023） | 自動：`tests/gate_exit_contract_test.sh` |
| TC-016 | 憲法「安全網」不放寬 | 功能 | 使用中的對話；已知會被關卡處理的呼叫：刪 `work/`、啟動 `nextflow run`、寫入外掛安裝目錄 | 餵給對應關卡 | 結果與 main 相同：該問的仍輸出 ask 的合法 JSON、該拒的仍輸出 deny 的合法 JSON，結束碼為 0（現有測試全數不改動地通過） | 自動：`tests/confirm_cleanup_test.sh`、`tests/confirm_launch_test.sh`、`tests/guard_plugin_files_test.sh`、`tests/confirm_walkthrough_test.sh` |
| TC-017 | 憲法原則 13；計畫第 2 點（jq 缺少本來就 exit 2） | 例外 | 使用中的對話；PATH 上沒有 jq | 餵一般 Bash 呼叫給 confirm_launch、confirm_cleanup、confirm_walkthrough | 結束碼仍是 2（刻意的拒絕，不是 1），訊息仍說明 jq 缺少與怎麼補；不因本次修改變成其他碼 | 自動：`tests/gates_without_jq_test.sh` |
| TC-018 | 憲法「無法判斷時當作使用中」 | 例外 | 狀態資料夾無法讀取（使用中判斷依規定當作「使用中」） | 餵一般 Bash 呼叫給四個關卡 | 關卡走完整檢查，結束碼 0 或 2、輸出為空或合法 JSON；判斷函式自己不會以其他碼結束 | 自動：`tests/in_use_test.sh` |

## User Story 3 — 使用者知道需要較新的 Claude Code（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 計畫第 3 點；assessment「需要 2.1.295 以上」 | 功能 | README 或外掛需求列表所在的文件 | 讀「需求」處 | 明寫：關卡出事時擋下（fail closed）需要 Claude Code 2.1.295 以上 | 手動：`docs/TESTING.md` |
| TC-020 | assessment「Not stated：低於 2.1.295 的行為」 | 例外 | 同 TC-019 | 讀同一處 | 對低於 2.1.295 的行為，只寫「官方文件沒說明、未驗證」這類誠實的話（例如可能維持舊的放行行為，也可能不認這個欄位），不宣稱已確認的行為 | 手動：`docs/TESTING.md` |
| TC-021 | 憲法 2.0.0（沒在用就安靜） | 例外 | 沒在使用外掛的對話；SessionStart 開始 | 跑 `hooks/session_start.sh` | 輸出與 main 完全一樣：沒有任何版本提示或其他新字 | 自動：`tests/session_start_test.sh`、`tests/constitution_scope_test.sh` |
| TC-022 | 計畫第 3 點（有版本才提示，沒有就只寫文件） | 功能 | 若實作了版本提示：使用中的對話，SessionStart 輸入帶有低於 2.1.295 的版本 | 跑 `hooks/session_start.sh` | 恰好多一行版本提示，且只在「使用中且版本可得且低於 2.1.295」才出現；版本高於或未提供時輸出與 main 相同。若執行者結論是 SessionStart 拿不到版本而只寫文件，則輸出與 main 相同，並在 fix.md 寫明原因 | 自動：`tests/session_start_test.sh` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 計畫第 5 點／Out of scope：不限制 confirm_cleanup.sh 每段的成本 | 不在範圍 | 本次的 diff | 讀 `hooks/confirm_cleanup.sh` 的 diff | 沒有新增長度或路徑層數上限；超長刪除指令超時就被擋，而 fix.md 有記下這件事與「跟進項目」 | 手動：`docs/TESTING.md`（驗收者讀 diff 與 fix.md） |
| TC-024 | 計畫 Out of scope：非關卡 hook | 不在範圍 | 本次的 diff | 讀 `hooks/next_step.sh`、`hooks/plugin_intro.sh` 的 diff，並看 hooks.json 非 PreToolUse 項目 | 兩個檔案沒有改動；非 PreToolUse 項目沒有 onFailure | 手動：`docs/TESTING.md`（驗收者讀 diff；hooks.json 部分另見 TC-005） |
| TC-025 | 計畫 Out of scope：憲法文字 | 不在範圍 | 本次的 diff | 讀 `.specify/memory/constitution.md` 的 diff | 沒有任何改動（不修憲） | 手動：`docs/TESTING.md`（驗收者讀 diff） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 原則 13：安全網做不了事時不能悄悄放行 | 功能 | Claude Code 2.1.295 以上；把關卡換成立刻當掉（exit 1）的假關卡 | 叫 Claude 跑普通指令 | 指令被擋，且訊息指出是哪個關卡出事（不是靜默放行也不是靜默卡住） | 手動：`docs/TESTING.md` |
| TC-C02 | 原則 13：也不能悄悄拒絕所有東西 | 例外 | 使用中的對話；PATH 最前面放一個假的 python3（在 Windows 上常見的商店替身，會以 9009 之類的碼結束）與一個壞掉的 awk 之外的環境不變 | 餵 TC-010 那批普通呼叫給四個關卡 | 結束碼仍是 0 或 2、輸出為空或合法 JSON（假 python3 不會讓普通指令被擋） | 自動：`tests/gate_exit_contract_test.sh` |
| TC-C03 | 安全網範圍：沒在用時整個安全網保持安靜 | 功能 | 沒在使用外掛的對話 | 餵普通呼叫與會被關卡處理的呼叫（刪 `work/`、啟動指令）給四個關卡與 session_start | 都沒有任何輸出、結束碼 0（範圍規則沒有被新設定弄壞） | 自動：`tests/constitution_scope_test.sh`、`tests/in_use_test.sh` |
| TC-C04 | 安全網四條規則不放寬 | 功能 | 修改後的整個倉庫 | 跑 `tests/run_all.sh`（WSL 或 CI）；比對 diff 中碰到的 tests/ 檔案 | 全綠；沒有任何現有測試被刪斷言、跳過或改期望值（只允許新增 `tests/hooks_fail_closed_test.sh` 與 `tests/gate_exit_contract_test.sh` 並加進 run_all） | 自動：`tests/run_all.sh` |
