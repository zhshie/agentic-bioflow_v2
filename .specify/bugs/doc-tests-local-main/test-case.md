# 測試案例：doc-tests-local-main（issue #71）

<!--
Written by the verifier (CONTRACT mode). Reader: the maintainer, who is not an engineer.
-->

**規格**：`.specify/bugs/doc-tests-local-main/assessment.md`（A 級修補，無維護者範例；基準是 issue #71 原文：「compare against a pinned value (hash / fixed text) or fail when the ref is missing」）　**總覽**：`test-case-overview.md`

白話：有兩個檢查本來是「拿本機的 main 來比對」，GitHub 自動測試沒有 main，就印「略過」然後算通過。修法是改成跟寫死在測試裡的標準答案比，而且任何情況都不准略過。

類型只有三種：

- **功能**：修補說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人改了不該改的東西時，檢查怎麼反應（必須失敗並說明）。
- **不在範圍**：這次明講不做的事；確認真的沒做。

「沒有 main 的環境」指：`git clone --depth 1` 出來的複本（和 GitHub 自動測試的檢出方式相同），其中 `git rev-parse --verify -q main` 找不到 main。

## 檢查一 — 憲法「安全網」那段不得悄悄被改（`tests/constitution_scope_test.sh`）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 修補 1；issue #71 | 功能 | 原封不動的修補後分支，本機有 main | 執行 `bash tests/constitution_scope_test.sh` | 全部通過，輸出含一行「安全網整段與標準答案一致」之類的 ok，沒有任何「skipped／略過」字樣 | 自動：`tests/constitution_scope_test.sh` |
| TC-002 | 修補 1；issue #71「fail when the ref is missing」的反面 | 功能 | 原封不動的內容，但在沒有 main 的淺層複本裡 | 在該複本執行同一個測試 | 一樣全部通過，而且「整段比對」那一行確實有跑（有 ok 行），沒有「skipped」 | 自動：`tests/constitution_scope_test.sh`（測試內自己建淺層複本） |
| TC-003 | issue #71 的核心：沒有 main 也要抓得到 | 例外 | 沒有 main 的淺層複本，憲法「Safety Net」那段任何一個字被改掉（例如把 `Never delete` 改成 `Do not delete`） | 在該複本執行測試 | 測試失敗（結束碼非 0），訊息指出安全網整段與標準答案不符，並印出目前那段的開頭幾行；修補前同樣情況是印「skipped」然後通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-004 | 修補 1 | 例外 | 本機有 main，同樣改掉安全網一個字 | 執行測試 | 一樣失敗；結果不取決於 main 存在與否 | 自動：`tests/constitution_scope_test.sh` |
| TC-005 | 修補 1；防止把錯的版本寫死 | 功能 | 修補完成後 | 驗收者用 main 上的憲法取出安全網那段，算 SHA-256，與測試裡寫死的值比 | 兩者完全相同（標準答案就是 main 現在的安全網，沒有偷換成別的） | 手動：驗收者以 `git show main:.specify/memory/constitution.md` 取出該段核對 |
| TC-006 | 修補 1：「沒有雜湊工具就失敗，不是略過」 | 例外 | 把 PATH 縮到沒有 `sha256sum`、`shasum`、`python3` | 執行測試 | 測試失敗，訊息說明找不到可用的雜湊工具；不是「skipped」也不是通過 | 自動：`tests/constitution_scope_test.sh`（測試內以縮小 PATH 的子程序驗證） |
| TC-007 | 修補 1：不能擋住正常修憲 | 功能 | 只改憲法「安全網」以外的地方，例如在 Amendments 加一條新修正案、改 Version 行 | 執行測試 | 指紋檢查仍通過（只有安全網那段的改動會觸發） | 自動：`tests/constitution_scope_test.sh` |
| TC-008 | 憲法：修憲要「可見」而非「不可能」 | 功能 | 安全網一個字被改，同時測試裡的指紋也更新成新值（模擬同一個 PR 內的合法修憲） | 執行測試 | 指紋檢查通過；而若只改安全網、不改指紋，失敗訊息（TC-003）會印出目前指紋值，讓人知道怎麼更新 | 自動：`tests/constitution_scope_test.sh` |
| TC-009 | 修補 3 | 功能 | 修補完成後 | 檢查 `tests/constitution_scope_test.sh` 內容 | 檔內沒有 `git show main:`、沒有 `rev-parse --verify -q main`、沒有「skipped」略過分支（針對這項檢查） | 自動：`tests/constitution_scope_test.sh`（測試自檢本檔） |

## 檢查二 — 詞彙表 CONTEXT.md 不得刪掉舊詞（`tests/platform_direction_docs_test.sh`，TC-034）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 修補 2 | 功能 | 原封不動的修補後分支；分別在有 main 與沒有 main 的淺層複本裡 | 各執行 `bash tests/platform_direction_docs_test.sh` | 兩種環境都通過，TC-034 那一行是 ok，沒有「skipped」 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-011 | issue #71 的核心 | 例外 | 沒有 main 的淺層複本，CONTEXT.md 刪掉一個詞（例如整個 `**Run index**` 段） | 執行測試 | 測試失敗，訊息點名被刪的詞 `[Run index]`；修補前同樣情況是「skipped」並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-012 | 修補 2 | 例外 | 本機有 main，同樣刪掉一個詞 | 執行測試 | 一樣失敗並點名那個詞 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-013 | 修補 2：標準答案不得少於 main 現有詞彙 | 功能 | 修補完成後 | 測試裡寫死的詞清單與 main 的 CONTEXT.md 粗體詞比對 | 清單恰為這 15 個：Prototype、Product、Execution backend、Brain、Muscle、Platform、Station agent、Run index、MCP tool layer、Buyer、Operator、Experiment spec、Deliverable、Reproducible、Data stays local；測試本身斷言這 15 個都在 CONTEXT.md | 自動：`tests/platform_direction_docs_test.sh` |
| TC-014 | 修補 2：「新增詞可自由加」 | 功能 | CONTEXT.md 另外新增一個粗體詞 | 執行測試 | 仍通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-015 | 修補 3 | 功能 | 修補完成後 | 檢查 `tests/platform_direction_docs_test.sh` 內容 | 檔內沒有 `git show main:`、沒有 `rev-parse --verify -q main`、沒有 TC-034 的「skipped」分支 | 自動：`tests/platform_direction_docs_test.sh`（測試自檢本檔） |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 修補「不在範圍」：`tests/in_use_speed_test.sh` | 不在範圍 | 修補完成 | 比對該檔與 main | 該檔沒有任何改動（它刻意跟 main 的 hook 比速度，並在沒有 main 時明說略過，不屬這次） | 手動：驗收者 `git diff main...HEAD -- tests/in_use_speed_test.sh` 為空 |
| TC-017 | 修補「不在範圍」：不改 CI 檢出深度 | 不在範圍 | 修補完成 | 比對 `.github/workflows/` | 沒有任何改動 | 手動：驗收者 `git diff main...HEAD -- .github` 為空 |
| TC-018 | 修補「不在範圍」：不改憲法、CONTEXT.md、hooks | 不在範圍 | 修補完成 | 比對 `.specify/memory/constitution.md`、`CONTEXT.md`、`hooks/` | 三者都沒有改動；變更只在這兩個測試檔（外加本 bug 目錄的文件） | 手動：驗收者 `git diff main...HEAD --stat` 核對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 安全網（四條規則＋適用範圍）不得被放寬或悄悄改 | 功能 | 修補完成後 | 取分支上憲法的安全網整段與 main 的比對 | 逐字相同（本修補只讓檢查更嚴，不碰條文） | 手動：驗收者以 diff 核對；自動面由 TC-001、TC-003 保證 |
| TC-020 | 開發流程：測試不得被削弱 | 功能 | 修補完成後 | 比對兩個測試檔與 main | 除了被取代的兩段（整段比對、TC-034）外，沒有任何斷言被刪除、放寬或改成略過；TC-040..TC-044 的固定字串檢查（`sn_has`）全部還在 | 手動：驗收者 `git diff main...HEAD -- tests/` 核對 |
| TC-021 | 開發流程：每一階段完整測試全綠，CI 必須先綠 | 功能 | 修補完成後 | 在 CI（淺層檢出）與 WSL／Linux 跑 `bash tests/run_all.sh` | 全綠，且兩個檢查在 CI 的輸出中是 ok 而不是 note／skipped | 自動：`tests/run_all.sh`（CI 結果） |
| TC-022 | 憲法 Safety Net「適用範圍」的 Check 行（`tests/constitution_scope_test.sh`） | 功能 | 修補完成後 | 讀憲法 Check 行並確認 `tests/constitution_checks_exist_test.sh` | 該 Check 行引用的測試檔存在，`constitution_checks_exist_test.sh` 通過；憲法沒因此需要改字 | 自動：`tests/constitution_checks_exist_test.sh` |
