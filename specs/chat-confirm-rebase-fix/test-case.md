# 測試案例：PR #376 rebase 並修好 test_tcm_47 基準

**規格**：`specs/chat-confirm-rebase-fix/plan.md`（本件沒有 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

白話說明：PR #376 把憲法升到 7.0.0（新增第四種人的同意通道 CHAT），維護者 2026-11-07 已說「同意 7.0.0」。它被 CI 擋住，只因為 `test_tcm_47`（「沒有新增表、沒有新增欄位」那條測試）寫死的舊基準，跟 v3 後來合進來的 `/settings/personal` 路由與 `step_mode`、`dev_mode` 欄位對不上。本件只做兩件事：把 #376 跟最新 v3 合在一起，並把那條測試的基準更新到包含這三樣東西。CHAT 行為和憲法條文都不准動。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

「ledger」指執行者交出的完成報告，內含基準更新的差異清單。

## User Story 1 — 把 #376 與最新 v3 合在一起（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 1 | 功能 | #376 分支落後最新 v3 | 執行者取得最新 `origin/v3` 並整合進 #376 分支 | #376 分支的歷史包含 `origin/v3` 的最新提交（`git merge-base --is-ancestor origin/v3 HEAD` 成立）；#376 原本的提交都還在，沒有遺失 | 手動：驗收者讀 git 紀錄 |
| TC-002 | 作法 1「保留 v3 的新內容與 #376 的 CHAT 新增」 | 功能 | 整合時有衝突的檔案 | 逐檔解衝突 | 每個衝突檔同時保有 v3 的新內容（含 `/settings/personal` 路由、`step_mode`、`dev_mode`）和 #376 的 CHAT 新增；任何一邊的內容都沒被整段丟掉 | 手動：驗收者讀合併提交的衝突檔差異 |
| TC-003 | 作法 4「不用 --force」 | 功能 | #376 分支已在遠端 | 以 `git merge origin/v3` 的方式整合並推送 | 推送是正常前進（fast-forward），沒有使用 `--force`／`--force-with-lease`；ledger 寫明沒有 force；若真需要 force，事先已問過維護者 | 手動：驗收者讀 git reflog／PR 提交列表與 ledger |
| TC-004 | 裁決「憲法版本仍是 7.0.0」；完成標準 | 例外 | 整合完成 | 讀憲法版本，並跑釘版本與指紋的測試（`tests/constitution_scope_test.sh` 與 `test_tcm_*` 內的憲法版本檢查） | 憲法版本仍是 7.0.0（不是 6.2.0，也不是別的）；版本釘測試全綠；憲法條文沒有因整合而被改動 | 自動：`tests/constitution_scope_test.sh`、`platform/tests/test_chat_confirm.py` |

## User Story 2 — `test_tcm_47` 的基準更新（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 作法 2「確認差異只來自…」 | 功能 | 整合完成、基準尚未更新 | 執行 `test_tcm_47`，讀失敗訊息 | 測試是紅的，且 ledger 記錄的失敗差異恰好只有三樣：`/settings/personal` 路由、`step_mode` 欄位、`dev_mode` 欄位。若差異還有別的東西，執行者必須停下回報，不能照樣更新基準 | 手動：驗收者讀 ledger 的失敗訊息 |
| TC-006 | 目標；失敗先行測試「完成後綠」 | 功能 | 基準已更新 | 執行 `platform/tests/test_chat_confirm.py::test_tcm_47_no_new_column_no_new_table` | 通過（綠） | 自動：`platform/tests/test_chat_confirm.py` |
| TC-007 | 作法 2「在 ledger 逐項列出新增了什麼」 | 功能 | 基準已更新 | 讀 ledger | ledger 逐項列出基準新增的內容：`/settings/personal` 路由、`step_mode` 欄位、`dev_mode` 欄位，沒有列其他項目，也沒有漏列；列出的項目與測試檔實際差異一致 | 手動：驗收者比對 ledger 與測試檔差異 |
| TC-008 | 失敗先行測試「真的新增欄位時仍會紅」 | 例外 | 基準已更新、測試綠 | 暫時在 users 表加一個假欄位，執行 `test_tcm_47`，再移除假欄位 | 加了假欄位後測試轉紅；移除後回到綠；ledger 附上這個紅／綠的證明；最終提交裡沒有留下假欄位 | 自動：`platform/tests/test_chat_confirm.py`（ledger 附證明） |
| TC-009 | 失敗先行測試「真的新增表…仍會紅」 | 例外 | 基準已更新、測試綠 | 檢查 `test_tcm_47` 對「資料表集合」的判斷 | 若多出一張不在基準裡的表，測試會失敗（基準是完整表清單的比對，不是只比 `step_mode`、`dev_mode`、`/settings/personal` 三項而放行其他）；基準沒有被改成只看那三樣 | 自動：`platform/tests/test_chat_confirm.py` |
| TC-010 | 範圍「只准把…納入基準」；完成標準「無一條被改弱」 | 功能 | 基準已更新 | 比對 `test_chat_confirm.py` 在更新前後的差異 | `test_tcm_47` 的改動只有基準結構雜湊與路由清單；沒有被刪除、放寬、跳過（skip）或換成較弱的斷言；檔內其他測試一行都沒動 | 手動：驗收者讀該檔的 git diff |

## User Story 3 — #376 能合併（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 完成標準「tests shard 1–4 全綠」 | 功能 | 已推送到 #376 分支 | 查 PR #376 的必要檢查 | tests shard 1、2、3、4 全部通過（尤其 shard 4/4）；PR 狀態仍為 MERGEABLE | 自動：CI（`gh pr checks 376`） |
| TC-012 | 作法 3 | 功能 | 本機 WSL 環境 | 在 WSL 從 ASCII 路徑執行 `bash tests/run_all.sh`（見 repo CLAUDE.md） | 全套綠；完成記號 `GREEN <HEAD sha>` 與 HEAD 相符、工作樹乾淨 | 自動：`tests/run_all.sh` |
| TC-013 | 完成標準「CHAT 通道行為測試無一條被改弱」 | 功能 | 整合與基準更新完成 | 比對 #376 原有的 CHAT 相關測試檔（`test_chat_confirm.py`、`test_chat_tools.py` 等）與整合前的差異；執行這些測試 | 除 TC-010 允許的基準更新外，沒有任何測試被刪、被放寬、被跳過、被改期望值；這些測試全綠 | 自動：`platform/tests/test_chat_confirm.py`、`platform/tests/test_chat_tools.py` |
| TC-014 | 完成標準「gitleaks／pip-audit 若仍紅」；裁決 | 例外 | gitleaks 或 pip-audit 在 PR 上仍為紅 | 讀 ledger 與 v3 上同一檢查的結果 | ledger 說明這是 v3 既有問題（v3 本身同樣紅），且沒有為了讓它變綠而放寬、略過或移除任何檢查；若它是必要檢查而擋合併，已回報 lead | 手動：驗收者讀 ledger 與 CI 結果 |

## User Story 4 — 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 目標／不做「不改 CHAT 行為」 | 不在範圍 | 本件完成 | 比對 #376 分支整合前後，非測試的程式檔差異 | 除解衝突所需外，CHAT 通道相關的程式（確認管道、動作層、路由）一行都沒改；沒有新增功能 | 手動：驗收者讀 git diff |
| TC-016 | 不做「不改憲法條文、不處理 8.0.0」 | 不在範圍 | 本件完成 | 比對 `.specify/memory/constitution.md` 與 `specs/` 下是否出現 8.0.0／`dev-mode-launch` 的內容 | 憲法條文與 #376 原本相同（版本 7.0.0）；沒有任何 8.0.0 或 `dev-mode-launch` 的條文、程式或測試 | 手動：驗收者讀 git diff |
| TC-017 | 不做「不放寬任何安全測試」；裁決「gitleaks／pip-audit 不是本件範圍」 | 不在範圍 | 本件完成 | 檢查 `.github/`、gitleaks／pip-audit 的設定與允許清單、安全相關測試的差異 | 這些檔案沒有任何改動；沒有新增忽略規則、允許清單項目或跳過標記 | 手動：驗收者讀 git diff |
| TC-018 | 範圍：檔案 | 不在範圍 | 本件完成 | 列出本件相對 #376 原分支（不含 v3 帶進來的內容）改動的檔案 | 只有「與 rebase 衝突的檔」和 `platform/tests/test_chat_confirm.py`；沒有其他檔案；沒有編輯 `specs/chat-confirm-rebase-fix/` 下的 plan 或 test-case 檔 | 手動：驗收者讀 `git diff --stat` |

## 憲法與安全網

本件碰到：憲法 7.0.0 的版本與指紋（TC-004、TC-016）、後端專長守則。本件不改行為，所以以下幾條是「沒有退步」的檢查：既有測試沒被改動且全部通過。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 專長守則：對等性（網頁動作與動作層函式一一對應） | 功能 | 整合完成 | 執行既有對等性測試 `platform/tests/test_web_parity.py` | 通過；該測試檔相對 base 沒有被修改；`set_my_setting` 對應 `/settings/personal` 的條目仍在 | 自動：`platform/tests/test_web_parity.py` |
| TC-020 | 專長守則：擁有者規則（跨使用者） | 例外 | 整合完成，兩位使用者 | 執行既有跨使用者測試（`test_owner_binding.py`、`test_web_settings_personal.py` 中第二位使用者讀寫第一位紀錄的案例） | 第二位使用者讀、寫第一位紀錄都被拒絕；測試全綠且未被修改 | 自動：`platform/tests/test_owner_binding.py`、`platform/tests/test_web_settings_personal.py` |
| TC-021 | 專長守則：確認管道（寫入需經人工確認） | 例外 | 整合完成 | 執行既有確認管道測試（`test_chat_confirm.py`、`test_confirm_page.py`、`test_actions_layer.py`） | 未經確認的寫入不改變資料（含 `dev_mode` 無人類通道被拒的案例）；測試全綠且未被削弱 | 自動：`platform/tests/test_chat_confirm.py`、`platform/tests/test_confirm_page.py`、`platform/tests/test_actions_layer.py` |
| TC-022 | 專長守則：錯誤訊息與日誌不洩漏密鑰 | 例外 | 整合完成 | 執行既有錯誤訊息／密鑰相關測試（`test_pat.py`、`test_web_confirm_plain.py`） | 全綠且未被修改；本件沒有新增任何會輸出日誌或回應的程式碼 | 自動：`platform/tests/test_pat.py`、`platform/tests/test_web_confirm_plain.py` |
| TC-023 | 專長守則：資料結構變動需 migration 或明寫不需要 | 功能 | 本件完成 | 讀 ledger，並檢查是否有 migration 檔被新增或改動 | ledger 明寫「不需要 migration」及理由（`step_mode`、`dev_mode` 是 v3 既有欄位，本件只更新測試基準）；沒有新增或改動 migration | 手動：驗收者讀 ledger 與 git diff |
