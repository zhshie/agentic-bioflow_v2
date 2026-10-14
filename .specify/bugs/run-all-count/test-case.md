# 測試案例：run_all.sh 開頭不再寫死測試檔數量

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`.specify/bugs/run-all-count/assessment.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：檢查本身出錯時，它要能真的亮紅燈。
- **不在範圍**：計畫明講這次不做的事；確認真的沒動。

維護者的兩個例子（原文，下面的 TC 直接用他的話當輸入與預期）：

- 例 1：「我打開 tests/run_all.sh，開頭不該告訴我一個錯的數字；要嘛寫對、要嘛不寫數字。」
- 例 2：「我跑 `bash tests/run_all.sh --list | wc -l`，數字要跟 `ls tests/*.sh | grep -v run_all.sh | wc -l` 一樣。」

本檔所有案例都不寫死檔案數量（現在是 101，以後會變）；一律比較「兩邊是否相等」。「開頭」依計畫指 `tests/run_all.sh` 的第 1–20 行。

## US1 — 打開 run_all.sh，開頭不會看到錯的數字（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 例 1；計畫 Remediation (b) | 功能 | 修好後的 `tests/run_all.sh` | 執行 `bash tests/run_all_count_test.sh`，它去讀 `tests/run_all.sh` 的第 1–20 行，找出獨立的整數（前後不是英數字、`#` 之外的數字，例如 `39`、`78`、`94`、`100`） | 第 1–20 行裡沒有任何 10 以上的獨立整數，測試結束代碼為 0；個位數（如 `twice`、`1`）不算 | 自動：`tests/run_all_count_test.sh` |
| TC-002 | 例 1；計畫 Remediation（改寫成描述機制） | 功能 | 修好後的 `tests/run_all.sh` | 讀第 1–20 行，找說明「測試檔從哪來、怎麼算」的那句 | 開頭仍有一句話說明：這個資料夾裡除了 `run_all.sh` 以外的每個 `.sh` 測試檔都會跑，數量是執行時才數（文字要含 `run time` 或 `runtime`）；沒有被整段刪掉了事 | 自動：`tests/run_all_count_test.sh` |
| TC-003 | 例 1（「要嘛寫對」）；計畫 Remediation | 功能 | 修好後的 `tests/run_all.sh` | 驗收者人工讀第 1–20 行，對照程式實際行為（開頭的 banner 只印 root／version／logs；檔案數在最後的總結行 `N/M passed` 與 `INCOMPLETE: only … of … test files ran` 才出現） | 開頭對「數量在哪裡看得到」的任何說法都與程式一致，不能寫成「banner 印出數量」這種不實的話；若沒提就算符合 | 手動：驗收者讀 `tests/run_all.sh` 第 1–20 行與 `git diff` |

## US2 — `--list` 列出的數量等於實際測試檔數量（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-004 | 例 2；計畫 Remediation (a) | 功能 | `tests/` 底下有若干 `.sh` 檔，Git Bash 或 WSL 皆可 | 執行 `bash tests/run_all.sh --list`，數它印出的行數；再數 `tests/*.sh` 中檔名不是 `run_all.sh` 的檔案數 | 兩個數字相等；測試比的是相等，不寫死任何數字，測試結束代碼為 0 | 自動：`tests/run_all_count_test.sh` |
| TC-005 | 計畫 Remediation（新檔放在 `tests/`、結束代碼判定） | 功能 | 新測試檔 `tests/run_all_count_test.sh` 已存在 | 執行 `bash tests/run_all.sh --list` | 輸出中有一行 `run_all_count_test.sh`（它自己也被排進整套測試）；且同一次輸出的行數仍等於 TC-004 的實際檔案數（表示新檔也算進去了） | 自動：`tests/run_all_count_test.sh` |

## US3 — 新測試真的會失敗（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-006 | 計畫 Remediation「(b) must be red on current main before the fix; (a) may already pass today — say so in the ledger」 | 例外 | main 上未修的 `tests/run_all.sh`（第 4、6、11、15 行有 39、78、39、39） | 驗收者拿 main 版的 `tests/run_all.sh` 開頭，以和 TC-001 相同的判斷規則檢查（例如把 main 版檔案放到暫存位置，餵給新測試的同一段邏輯，或在暫存複本上還原那句舊話再跑） | 檢查 (b) 失敗（結束代碼非 0，並指出是哪個數字）；`fix.md` 的 ledger 寫明 (b) 在修之前是紅的、(a) 本來就是綠的 | 手動：驗收者在暫存複本上重跑，並讀 `.specify/bugs/run-all-count/fix.md` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 計畫 Out of scope：run_all.sh 的行為與結束代碼 | 不在範圍 | 修好後的分支 | 驗收者比對 `git diff main...HEAD -- tests/run_all.sh` | 被改動的只有 `set -uo pipefail` 之前的註解行；沒有任何非註解行（指令、判斷、結束代碼）被改 | 手動：驗收者讀 diff |
| TC-008 | 計畫 Out of scope：其他測試檔 | 不在範圍 | 修好後的分支 | 驗收者執行 `git diff main...HEAD --stat -- tests/` | 除了新增 `tests/run_all_count_test.sh` 與註解修改的 `tests/run_all.sh` 外，`tests/` 底下沒有任何其他檔案被新增、修改或刪除（包含 `tests/run_all_test.sh`） | 手動：驗收者讀 diff 統計 |
| TC-009 | 計畫 Out of scope：run_all.sh 的行為與結束代碼 | 不在範圍 | 修好後的分支，WSL 或 CI（整套只在 WSL／Linux 跑） | 執行既有的 `bash tests/run_all_test.sh`（它測 `run_all.sh` 的結束代碼與選項，未被修改） | 原本通過的案例全部照舊通過，沒有被跳過 | 自動：`tests/run_all_test.sh` |
