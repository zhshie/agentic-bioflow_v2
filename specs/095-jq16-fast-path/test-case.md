# 測試案例：#95 hook 的「一次 jq」快速路徑在 jq 1.6 上也能用

<!--
Written by the verifier (CONTRACT mode) from specs/095-jq16-fast-path/plan.md (a bug-fix plan: there is no spec.md; the plan's
"給維護者", "Facts" and "Design decisions" are the source of every case).
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/095-jq16-fast-path/plan.md`（修補計畫，無獨立 spec.md）　**總覽**：`test-case-overview.md`

名詞先說明：
- **快速路徑**：關卡（hook）一開始用「一次 jq」把工具名稱與指令都讀出來；讀不出來才退回「每個欄位各跑一次 jq」的慢路徑。兩條路徑結論相同，只差速度。
- **預算**：`tests/gate_process_count_test.sh` 規定每次呼叫最多啟動幾個外部程式（launch 3、cleanup 2、walkthrough 4、guard_plugin_files 2；jq 在其中算一個）。
- **jq 1.6／1.7.1**：Ubuntu 22.04／WSL 預設是 1.6；CI 與 `/usr/local/bin/jq` 是 1.7.x。1.6 看不懂舊寫法 `sub("\\n+\\z"; "")`，新寫法是 `def t: if endswith("\n") then .[:-1] | t else . end;` 搭配 `map(t + "\u001f")`。

類型只有三種：**功能**、**例外**、**不在範圍**。

註：標「需 jq 1.6」的自動案例，在只有 jq 1.7 的機器（含目前的 CI）上會顯示 SKIP；SKIP 不算通過，驗收時必須有在 WSL 上實際跑過 1.6 的紀錄（ledger）。

## User Story 1 — 在 jq 1.6 上，每次 Bash 呼叫只跑一次 jq（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 給維護者 1；Facts（修前 21 項失敗） | 功能 | WSL，PATH 最前面是 jq 1.6（`/usr/bin/jq`） | 執行 `bash tests/gate_process_count_test.sh` | 最後印出 `all passed`，沒有任何一項 FAIL；修前同樣情況是「21 failed」且列出 `started: jq jq jq jq awk` | 自動：`tests/jq_versions_test.sh`（需 jq 1.6）＋ `tests/gate_process_count_test.sh` |
| TC-002 | 給維護者 1；Changes 2 | 功能 | 同 TC-001 | launch 關卡（`confirm_launch`）收到 `ls -la` 等無關指令 | 啟動的外部程式數 ≤ 3，且 jq 只出現一次 | 自動：`tests/jq_versions_test.sh`（需 jq 1.6） |
| TC-003 | 給維護者 1；Changes 2 | 功能 | 同 TC-001 | 刪除保護（`confirm_cleanup`）收到無關指令 | 啟動的外部程式數 ≤ 2，且 jq 只出現一次 | 自動：`tests/jq_versions_test.sh`（需 jq 1.6） |
| TC-004 | 給維護者 1；Changes 2 | 功能 | 同 TC-001 | 說明關卡（`confirm_walkthrough`）收到無關指令 | 啟動的外部程式數 ≤ 4，且 jq 只出現一次 | 自動：`tests/jq_versions_test.sh`（需 jq 1.6） |
| TC-005 | 給維護者 1；Changes 2 | 功能 | 同 TC-001 | 外掛檔案保護（`guard_plugin_files`）收到 `ls -la` | 啟動的外部程式數 ≤ 2，且 jq 只出現一次 | 自動：`tests/jq_versions_test.sh`（需 jq 1.6） |
| TC-006 | Facts（1.7.1 全過）；Changes 3 | 功能 | WSL，PATH 最前面是 jq 1.7.1（`/usr/local/bin/jq`） | 執行 `bash tests/gate_process_count_test.sh` | 印出 `all passed`；修完後 1.7.1 仍然全過、預算數字沒變 | 自動：`tests/jq_versions_test.sh` |

## User Story 2 — 所有關卡的判斷與訊息一字不變（優先度 P1）

「舊寫法」＝ `sub("\\n+\\z"; "")`（只在 1.7.1 上跑）；「新寫法」＝四支 hook 實際使用的那段 `t`。下列每條都是：同一個輸入餵給兩者，輸出必須逐位元相同。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | Design 3（結尾沒有換行） | 功能 | 指令字串 `ls -la` | 新舊寫法各處理一次 | 輸出相同，內容未被改動 | 自動：`tests/jq_versions_test.sh` |
| TC-008 | Design 3（結尾一個換行） | 功能 | 指令字串 `ls -la\n` | 同上 | 輸出相同，結尾那一個換行被去掉 | 自動：`tests/jq_versions_test.sh` |
| TC-009 | Design 3（結尾很多換行） | 功能 | 指令字串 `ls -la\n\n\n` | 同上 | 輸出相同，結尾所有換行都被去掉 | 自動：`tests/jq_versions_test.sh` |
| TC-010 | Design 3（只有換行） | 功能 | 指令字串 `\n\n\n` | 同上 | 輸出相同，結果是空字串（後面仍帶分隔符） | 自動：`tests/jq_versions_test.sh` |
| TC-011 | Design 3（中間有換行） | 功能 | 指令字串 `a\nb\n\nc\n` | 同上 | 輸出相同，只去掉最後的換行，中間的換行完整保留 | 自動：`tests/jq_versions_test.sh` |
| TC-012 | Design 1、3（CRLF） | 功能 | 指令字串 `a\r\n` 與 `a\r` | 同上 | 輸出相同；`\r` 不會被去掉（與舊行為一致，只去 `\n`） | 自動：`tests/jq_versions_test.sh` |
| TC-013 | Design 3（Unicode） | 功能 | 含中文與 emoji、結尾有換行的字串 | 同上 | 輸出相同，字元未被切壞 | 自動：`tests/jq_versions_test.sh` |
| TC-014 | Design 3（100 KB 本文） | 功能 | 約 100 KB 的字串，結尾一個換行 | 同上 | 輸出相同，且在合理時間內完成 | 自動：`tests/jq_versions_test.sh` |
| TC-015 | Design 3（結尾 5,000 個換行） | 功能 | 本文後接 5,000 個換行 | 同上 | 輸出相同（5,000 個都去掉），沒有因遞迴過深而失敗 | 自動：`tests/jq_versions_test.sh` |
| TC-016 | Design 3（新寫法跑在每個找到的 jq 上） | 功能 | 機器上同時有 jq 1.6 與 1.7.1 | 新寫法在 1.6 與 1.7.1 上各跑 TC-007 至 TC-015 的全部輸入 | 兩個版本輸出相同，且都等於舊寫法在 1.7.1 上的輸出 | 自動：`tests/jq_versions_test.sh`（需 jq 1.6 與 1.7） |
| TC-017 | 給維護者 2；Facts（決策釘住測試）；Changes 3 | 功能 | WSL，jq 1.6 在 PATH 最前面 | 逐一執行：`confirm_launch_test.sh`、`confirm_cleanup_test.sh`、`confirm_cleanup_behind_heredoc_test.sh`、`confirm_cleanup_candidates_timing_test.sh`、`confirm_walkthrough_test.sh`、`guard_plugin_files_test.sh`、`in_use_test.sh`、`in_use_speed_test.sh`、`conditions_matrix_test.sh`、`gate_big_input_test.sh`、`gate_exit_contract_test.sh`、`gate_output_failclosed_test.sh`、`hooks_fail_closed_test.sh`、`principle_13_test.sh`、`gates_without_jq_test.sh`（共 15 支） | 15 支全部通過，且沒有改動任何一支 | 自動：上列 15 支各自的 `tests/*.sh` |
| TC-018 | 給維護者 2；Facts；Changes 3 | 功能 | WSL，jq 1.7.1 在 PATH 最前面 | 同 TC-017 的 15 支 | 15 支全部通過 | 自動：上列 15 支各自的 `tests/*.sh` |
| TC-019 | 給維護者 2；Constitution Check（測試不為了過關而改） | 功能 | 本分支與 `main` 比較 | 比對 `tests/` 底下既有檔案的差異 | 既有測試檔只有 `tests/gate_process_count_test.sh` 多了「印出 jq 版本」那一行；沒有任何斷言被移除、放寬、跳過或改預期值；預算數字未動；新增的只有 `tests/jq_versions_test.sh` | 自動：`git diff main...HEAD -- tests/`（驗收時檢查） |
| TC-020 | 給維護者 2；Changes 2；Design 2 | 功能 | 本分支與 `main` 比較 | 比對四支 hook 的差異：`hooks/confirm_cleanup.sh`、`hooks/confirm_launch.sh`、`hooks/confirm_walkthrough.sh`、`hooks/guard_plugin_files.sh` | 每支只動快速路徑那段 jq 程式（`sub(...)` 換成 `t` 並加上 `def t`）；所有拒絕／提示訊息文字、欄位清單、`abf-jq-ok` 暗記檢查、`JQ_SHAPE`／`JQ_REST` 檢查都沒有變 | 自動：`git diff main...HEAD -- hooks/`（驗收時檢查） |
| TC-021 | Changes 3 | 功能 | WSL | 分別在 jq 1.6 在前、jq 1.7.1 在前時執行 `bash tests/run_all.sh` | 兩次整套都通過（零個測試被改） | 手動：`docs/TESTING.md`（WSL 跑全套），兩次輸出記入 ledger |

## User Story 3 — 新測試把「兩個 jq 版本」釘住（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | Changes 1（先紅後綠） | 功能 | 還沒改 hook，只有新增的 `tests/jq_versions_test.sh` | 在 WSL 執行它 | jq 1.6 那一半 FAIL（行程數超標）、jq 1.7.1 那一半 PASS；兩份輸出都存進 `specs/095-jq16-fast-path/ledger.md`，且是修 hook 之前取得的 | 手動：ledger 內有修前輸出 |
| TC-023 | Design 4（找 1.6） | 功能 | 設 `ABF_JQ16` 指向一個 1.6 的 jq；另一次不設，系統 `/usr/bin/jq` 是 1.6 | 執行 `bash tests/jq_versions_test.sh` | 兩種情況都找到 1.6，並為它建一個放在 PATH 最前面的替身目錄，跑 `gate_process_count_test.sh` 與等價案例 | 自動：`tests/jq_versions_test.sh` |
| TC-024 | Design 4（找 1.7） | 功能 | 設 `ABF_JQ17`；另一次不設，`/usr/local/bin/jq` 是 1.7 | 執行 `bash tests/jq_versions_test.sh` | 兩種情況都找到 1.7 並同樣跑完 | 自動：`tests/jq_versions_test.sh` |
| TC-025 | Design 4（找不到就 SKIP） | 例外 | 機器上找不到 jq 1.6（例如 CI 只有 1.7） | 執行 `bash tests/jq_versions_test.sh` | 1.6 那一半印出 `SKIP`（明寫是 1.6 沒找到），不印 `PASS`；1.7 那一半照常執行並 PASS | 自動：`tests/jq_versions_test.sh` |
| TC-026 | Design 4（用 `--version` 查證） | 例外 | `ABF_JQ16` 或 `/usr/bin/jq` 實際是 jq 1.7（例如 Ubuntu 24.04） | 執行 `bash tests/jq_versions_test.sh` | 不把它當 1.6 使用；1.6 那一半顯示 `SKIP`，而不是拿 1.7 假裝跑過 1.6 | 自動：`tests/jq_versions_test.sh` |
| TC-027 | Design 5 | 功能 | 任一 jq | 執行 `bash tests/gate_process_count_test.sh` | 輸出多一行印出「目前使用的 jq 版本」；所有預算數字（3／2／4／2／5／5／5／3／3）與其他輸出行為和修前一致 | 自動：`tests/gate_process_count_test.sh` |
| TC-028 | 給維護者 3；Facts（CI 只有 1.7） | 功能 | CI 環境（`ubuntu-latest`，只有 jq 1.7.x） | 跑 `bash tests/run_all.sh` | `jq_versions_test.sh` 被整套跑到；1.7 那一半通過、1.6 那一半明顯顯示 SKIP；整套仍是綠 | 自動：`tests/run_all.sh`（CI 結果） |

## User Story 4 — 文件記錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | Changes 4（PITFALLS） | 功能 | 修完之後 | 打開 `docs/PITFALLS.md` | 新增一則簡短條目：hook 的 jq 程式裡用到的正規表示式錨點必須在 jq 1.6 與 1.7 都能執行，並以 `\z` 為例 | 自動：`docs/PITFALLS.md` 內可查（驗收時閱讀） |
| TC-030 | Changes 4（CHANGELOG） | 功能 | 修完之後 | 打開 `CHANGELOG.md` | 只新增一行說明這次修正；沒有改動其他條目 | 自動：`git diff main...HEAD -- CHANGELOG.md`（驗收時檢查） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 憲法第 13 條（jq 缺失時要明說、要拒絕） | 例外 | PATH 上沒有 jq | 執行 `bash tests/gates_without_jq_test.sh` 與 `tests/confirm_launch_test.sh`、`confirm_cleanup_test.sh`、`confirm_walkthrough_test.sh`、`plugin_intro_test.sh` 的「no jq」段落 | 全過；關卡仍拒絕它無法排除的指令並說出該怎麼修（訊息不變） | 自動：`tests/gates_without_jq_test.sh` 等 |
| TC-032 | 憲法第 13 條；安全網（快速路徑的驗證仍在） | 例外 | jq 1.6 在 PATH 最前面；用壞掉的 jq（回答 `{}`、回答文字、或兩個 JSON）餵關卡 | 執行 `confirm_cleanup_test.sh`、`gate_output_failclosed_test.sh`、`hooks_fail_closed_test.sh` | 全過；壞答案不被信任，仍退回探測路徑並拒絕，與 jq 1.7.1 上的結果相同 | 自動：上列 `tests/*.sh`（在 1.6 下跑） |
| TC-033 | 安全網（沒有放寬任何被擋的形狀） | 功能 | `main` 與本分支各執行一次 | 兩邊都在 jq 1.7.1 下執行 TC-017 那 15 支關卡測試，並比較每支的通過／失敗結果與被拒絕的指令形狀 | 兩邊逐支結果相同；`main` 擋下的形狀本分支一樣擋下 | 自動：這 15 支 `tests/*.sh`（驗收時兩個分支各跑並比對） |

## 不在範圍（plan「Not in this PR」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 不動 CI（`.github/`） | 不在範圍 | 本分支與 `main` 比較 | 看差異有沒有 `.github/` 底下的檔案 | 沒有任何 `.github/` 檔案被改（要不要在 CI 加 jq 1.6 另外問維護者） | 自動：`git diff main...HEAD --stat -- .github/`（驗收時檢查） |
| TC-035 | 不改任何判斷、訊息、欄位清單、預算 | 不在範圍 | 本分支與 `main` 比較 | 比對四支 hook 的 jq 欄位清單、`abf-jq-ok` 暗記邏輯、所有訊息字串，與 `gate_process_count_test.sh` 的預算數字 | 全部與 `main` 相同，沒有趁機調整 | 自動：`git diff main...HEAD -- hooks/ tests/gate_process_count_test.sh`（驗收時檢查） |
| TC-036 | 不做共用函式庫重構 | 不在範圍 | 本分支與 `main` 比較 | 看 `hooks/` 的差異 | 沒有新增被四支 hook 共同 `source` 的檔案；四支各自仍擁有自己那份 jq 程式文字 | 自動：`git diff main...HEAD --stat -- hooks/`（驗收時檢查） |
| TC-037 | 不做執行期 jq 版本檢查 | 不在範圍 | 本分支的 hook | 在 `hooks/` 搜尋 `jq --version` 或依版本分支的程式 | 找不到；hook 在兩個版本上走同一份程式，不因版本不同而分岔 | 自動：`grep` 於 `hooks/`（驗收時檢查） |
| TC-038 | 不動 `v3` 線 | 不在範圍 | 本分支（基底是 `main` 的 v2 線） | 看差異有沒有 v3 線專屬的檔案或分支 | 沒有；v3 之後要移植另案處理 | 自動：`git diff main...HEAD --stat`（驗收時檢查） |
