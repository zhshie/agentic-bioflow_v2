# 測試案例：移除 test_onboarding_doc 釘死 6061925 的一次性檢查

**規格**：`specs/onboarding-test-pinned-base/plan.md`（A 級小修，沒有 spec.md，以 plan 為準；plan 無維護者原話）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

本次只改一個測試檔 `platform/tests/test_onboarding_doc.py`（加上 ledger），沒有新增測試檔（計畫明寫「不需新增測試檔」）。所以下列「驗證方式」的「自動」，指的是驗收時執行檔案內既有測試，或執行下列指令檢查，而不是新寫的測試。

名詞：「完整 clone」＝有完整提交歷史的複本，能找到提交 `6061925`；CI 用的是淺層 clone（只抓最近幾筆），找不到 `6061925`，所以舊檢查在 CI 上被悄悄跳過。

## User Story 1 — 拿掉只在 #211 那次 PR 才需要的「釘死 6061925」檢查（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1 | 功能 | 修正完成的分支 | 在 `platform/tests/test_onboarding_doc.py` 找 `test_tc047_tc051_other_docs_untouched`；並執行 `pytest platform/tests/test_onboarding_doc.py --collect-only -q` | 檔案裡沒有這個函式，收集到的測試清單也沒有它（整個函式刪掉，不是留空殼、不是加 skip） | 自動：`pytest --collect-only` ＋ `grep -n tc047 platform/tests/test_onboarding_doc.py` 無輸出 |
| TC-002 | 作法 2 | 功能 | 修正完成的分支，README 目前的樣子（有且只有一行指向 `docs/ONBOARDING.md`，在 `docs/PITFALLS.md` 那行之前，前後各一空行） | 執行 `pytest platform/tests/test_onboarding_doc.py::test_tc045_tc046_readme_pointer` | 測試仍存在且通過（保留前半，沒有整個刪掉） | 自動：`pytest platform/tests/test_onboarding_doc.py -k tc045` |
| TC-003 | 作法 2（前半仍有效） | 例外 | 暫時把 README 改成有兩行含 `docs/ONBOARDING.md`（只在驗收者的暫存複本做，不留在分支） | 執行 `test_tc045_tc046_readme_pointer` | 測試失敗（仍要求「有且只有一行」指向） | 自動：驗收時在暫存複本改 README 後跑該測試 |
| TC-004 | 作法 2（前半仍有效） | 例外 | 暫時把指向 `docs/ONBOARDING.md` 的那行移到 `docs/PITFALLS.md` 那行之後（暫存複本） | 執行 `test_tc045_tc046_readme_pointer` | 測試失敗（仍要求「在 PITFALLS 那行之前」） | 自動：同上 |
| TC-005 | 作法 2（前半仍有效） | 例外 | 暫時把指向那行前面或後面的空行拿掉（暫存複本） | 執行 `test_tc045_tc046_readme_pointer` | 測試失敗（仍要求「前後各一空行」） | 自動：同上 |
| TC-006 | 作法 2、目標第 2 點 | 功能 | 完整 clone；暫時在 README 任一不相關位置加一行文字，指向那行與空行規則不變（暫存複本） | 執行 `test_tc045_tc046_readme_pointer` | 測試仍通過（不再拿 6061925 的 README 逐行比對，README 以後改動不會讓它變紅） | 自動：驗收時在暫存複本改 README 後跑該測試 |
| TC-007 | 作法 3 | 功能 | 修正完成的分支 | 在 `platform/tests/test_onboarding_doc.py` 搜尋 `BASE`、`_git`、`subprocess` | 三者都不再出現（刪除後已無人使用，一起刪）；其餘需要的 import（`re`、`Path`、`REPO_ROOT`）仍在、檔案可正常執行 | 自動：`grep -nE 'BASE\|_git\|subprocess' platform/tests/test_onboarding_doc.py` 無輸出，且 TC-009 通過 |
| TC-008 | 完成標準第 2 條 | 功能 | 修正完成的分支 | 在 `platform/tests/test_onboarding_doc.py` 搜尋 `6061925` | 無任何結果（只限這個測試檔；ledger 與 plan 可以提到它） | 自動：`grep -n 6061925 platform/tests/test_onboarding_doc.py` 無輸出 |
| TC-009 | 失敗先行測試、完成標準第 1 條 | 功能 | 一份完整 clone（`git cat-file -t 6061925` 回 `commit`） | 先在修正前的 base 提交執行 `pytest platform/tests/test_onboarding_doc.py`，再在修正後的分支執行同一指令 | 修正前：`test_tc047_tc051_other_docs_untouched` 紅（因為 docs 有 2 檔 `PLATFORM.md`、`TESTING.md` 與 6061925 不同）；修正後：整個檔案全綠，沒有失敗、沒有被新增的 skip／xfail | 自動：兩次 `pytest` 輸出對照 |
| TC-010 | 作法 4 | 功能 | 修正完成的分支 | 讀 `specs/onboarding-test-pinned-base/ledger.md` | ledger 記有完整 clone 上「修正前 test_tc047 紅」與「修正後全檔綠」兩段輸出（實際貼出的 pytest 結果，不是只寫「已通過」） | 自動：驗收者讀檔對照 TC-009 自己跑的結果 |
| TC-011 | 完成標準第 1 條 | 功能 | 修正完成的分支，在 WSL 或 Linux | 執行 `tests/run_all.sh`（依 CLAUDE.md 的 WSL 指令） | 全套綠 | 自動：`tests/run_all.sh` |

## 不在範圍（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 不做：不改 docs/ 任何檔、不改 ONBOARDING.md | 不在範圍 | 修正完成的分支與其 base | 執行 `git diff <base>...HEAD --stat -- docs/` | 無任何輸出（`docs/` 底下包含 `docs/ONBOARDING.md` 都沒有改；沒有為了讓測試變綠而去改文件） | 自動：`git diff --stat` 無輸出 |
| TC-013 | 不做：不改其他測試 | 不在範圍 | 修正完成的分支與其 base | 比對 `test_onboarding_doc.py` 其餘測試函式（除 `test_tc045_tc046_readme_pointer` 的後三行與 `test_tc047…`）及其他測試檔 | 其餘函式內容與 base 逐字相同（沒有放寬斷言、沒有加 skip）；`platform/tests/` 其他檔案、`tests/` 沒有差異 | 自動：`git diff <base>...HEAD -- platform/tests tests` 只出現 TC-001、TC-002、TC-007 要求的刪除 |
| TC-014 | 範圍：只准改兩個檔 | 不在範圍 | 修正完成的分支與其 base | 執行 `git diff <base>...HEAD --name-only` 與 `git status --porcelain` | 只有 `platform/tests/test_onboarding_doc.py` 與 `specs/onboarding-test-pinned-base/ledger.md`（plan.md 為先前已提交的計畫，不算新改動）；工作區乾淨 | 自動：兩個 git 指令 |

<!--
說明：
- 本計畫沒有涉及憲法條目的行為（只動一個文件測試），故不設「憲法與安全網」一節。
- 專長守則（backend）的對等性、跨使用者、確認管道、錯誤訊息、migration 等 TC：本次只刪除測試碼，沒有動作層、寫入動作、資料結構、錯誤訊息，皆不適用，因此不產生對應 TC；驗收時於「專長守則檢查」逐項註明不適用。
- TC-003 至 TC-006 的暫存複本修改不得留在分支，驗收後須還原。
- 本文件通過 `合約已確認` 後，實作期間不得修改。
-->
