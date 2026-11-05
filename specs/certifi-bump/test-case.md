# 測試案例：certifi 升版（修 pip-audit PYSEC-2026-4320）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
-->

**規格**：`specs/certifi-bump/plan.md`（本任務為 C 級，沒有獨立 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

維護者原話（計畫引述）：「建議升版，C 級」。意思是：升版，不是加忽略；不碰保護路徑、不改行為。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

說明：「constraints 檔」指 `platform/constraints.txt`，是平台釘住每個依賴版本的清單。「ignore 檔」指 `platform/pip-audit-ignore.txt`，是安全掃描「允許忽略的漏洞」清單，目前刻意留空。新測試檔是 `platform/tests/test_certifi_pin.py`，每個自動測試要在註解寫上它對應的 TC 編號。

## User Story 1 — 把 certifi 升到修正版，安全掃描轉綠（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者原話「建議升版，C 級」；目標；失敗先行測試第 1 條 | 功能 | constraints 檔已改完 | 逐行讀 constraints 檔，找出 certifi 那一行，把版本號依 `.` 切成數字比較 | 版本 >= 2026.10.18（`certifi==2026.10.18` 或更新）；舊的 `2026.7.22` 不再出現 | 自動：`platform/tests/test_certifi_pin.py::test_constraints_pins_certifi_at_or_above_fix` |
| TC-002 | 失敗先行測試第 1 條（有且恰好一行） | 功能 | 同上 | 逐行解析（不是搜字串）數 `certifi==` 或 `certifi>=` 的行數 | 恰好一行，不是零行也不是兩行 | 自動：同上測試 |
| TC-003 | 失敗先行測試第 2 條 | 功能 | 版本解析函式存在 | 比較 `2026.7.22` 與 `2026.10.18` | 判定 `2026.7.22` 小於 `2026.10.18`（數字比較；用字串比較會把 7 排在 10 後面而誤判） | 自動：`platform/tests/test_certifi_pin.py::test_certifi_version_parser_compares_numerically` |
| TC-004 | 作法第 1 步（先寫測試、確認紅） | 功能 | 把 constraints 檔還原成 base（v3）的內容，certifi 為 2026.7.22 | 跑 TC-001 的測試 | 測試失敗（紅）；改成新版後轉綠。驗收者在 base 內容上實跑確認它會紅 | 自動：驗收者對 base 的 constraints 內容跑 `platform/tests/test_certifi_pin.py` |
| TC-005 | 維護者原話（升版而不是加忽略）；失敗先行測試第 3 條 | 功能 | ignore 檔 | 讀 ignore 檔，去掉 `#` 開頭的註解與空行 | 剩下零個有效行（維持「Empty on purpose」），沒有把 PYSEC-2026-4320 加進去 | 自動：`platform/tests/test_certifi_pin.py::test_pip_audit_ignore_stays_empty` |
| TC-006 | 完成標準第 4 條 | 功能 | 本機有網路 | 執行 `pip-audit -r platform/constraints.txt --no-deps --disable-pip` | 輸出沒有 PYSEC-2026-4320 | 自動（有網路時）：executor 把輸出貼進 ledger |
| TC-007 | 計畫「允許的斷言（既有測試）」Python 部分 | 功能 | constraints 檔已改完 | 跑 `test_azure_upload.py`、`test_catalogue.py`、`test_chat_tools.py`、`test_cloud_upload.py`、`test_k8s_launch.py`、`test_guidance.py` | 全部維持綠；這些測試沒有被修改；`test_guidance.py` 仍看到 `mcp==2.3.0` 那一行 | 自動：上述既有測試檔 |
| TC-008 | 計畫「允許的斷言（既有測試）」shell 部分；完成標準第 1 條 | 功能 | constraints 檔已改完 | 跑 `tests/platform_test.sh`、`tests/testing_web_doc_test.sh`、`tests/ci_security_workflow_test.sh`（以及完成時的 `tests/run_all.sh` 全套） | 全部綠，其中 `ci_security_workflow_test.sh` 仍看到 `pip-audit -r platform/constraints.txt --no-deps --disable-pip` 這串字（環境性紅依 README 通例） | 自動：上述 shell 測試與 `tests/run_all.sh` |
| TC-009 | 環境事實；完成標準第 4 條 | 例外 | 本機沒有網路，無法跑 pip-audit | 完成 TC-006 的步驟 | ledger 明白寫「無網路、未跑 pip-audit，以 PR 上 `security` 工作流為準」，而不是留白或假裝跑過 | 自動：驗收者讀 ledger |
| TC-010 | 範圍：檔案（ledger 記實際版本；開工前再 grep 一次） | 功能 | 開工前與完成時 | 執行 `git grep -n -i certifi origin/v3 -- ':!platform/abf_platform/data'` 並讀 ledger | ledger 記下實際選的 certifi 版本（>= 2026.10.18），並說明 grep 結果：除 `constraints.txt:5` 外沒有新的釘版處；若有，已一併改並寫進 ledger | 自動：驗收者讀 ledger 並重跑該 grep |

## User Story 2 — 只換一個版本號，其他都不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 範圍：檔案；不做（不順手升級、不重新生成整份檔） | 不在範圍 | 工作完成 | 執行 `git diff origin/v3...HEAD -- platform/constraints.txt` | 只有 certifi 那一行被改（1 行刪、1 行加）；第 1 行註解與其他所有依賴行完全相同 | 自動：驗收者跑該 git diff |
| TC-012 | 維護者原話（不加忽略）；範圍：不准改 | 不在範圍 | 工作完成 | 執行 `git diff --stat origin/v3 -- platform/pip-audit-ignore.txt` | 輸出為空（檔案連一個位元組都沒變）；輸出貼進 ledger | 自動：驗收者跑該 git diff |
| TC-013 | 完成標準第 3 條；不做第 1 條 | 不在範圍 | 工作完成 | 執行 `git diff --stat origin/v3 -- .github` | 輸出為空；沒有改任何工作流檔；輸出貼進 ledger | 自動：驗收者跑該 git diff |
| TC-014 | 範圍：不准改 `platform/abf_station/` | 不在範圍 | 工作完成 | 執行 `git diff --stat origin/v3 -- platform/abf_station` | 輸出為空 | 自動：驗收者跑該 git diff |
| TC-015 | 作法第 3 條；不做第 3 條 | 不在範圍 | 工作完成 | 在 `platform/pyproject.toml` 與 `platform/setup.py` 找 certifi | 沒有新增 certifi（它仍只是靠 constraints 釘住的傳遞依賴）；這兩個檔的 diff 為空 | 自動：驗收者跑 `git diff origin/v3 -- platform/pyproject.toml platform/setup.py` 與 grep |
| TC-016 | 不做第 4 條（不改文件） | 不在範圍 | 工作完成 | 執行 `git diff --stat origin/v3 -- docs` | 輸出為空；沒有任何文件被改 | 自動：驗收者跑該 git diff |
| TC-017 | 完成標準第 2 條 | 不在範圍 | 工作完成 | 執行 `git diff --stat origin/v3...HEAD` | 只列出 `platform/constraints.txt`（1 行改）、`platform/tests/test_certifi_pin.py`（新）、`specs/certifi-bump/*`；沒有其他檔 | 自動：驗收者跑該 git diff |

<!--
憲法與安全網：本任務只改依賴清單與一個新測試，不動 hooks、安全閘門、動作層或寫入路徑，也不動憲法條目的檢查，故不設此節。
專長守則（backend）的對等性、跨使用者、確認管道、錯誤訊息與日誌、migration 各項，依計畫「裁決」第 3 條對本案不適用（沒有動作層或寫入路徑；沒有資料結構或資料內容變動，計畫作法第 4 條已寫明不需要 migration），故無對應 TC。
-->
