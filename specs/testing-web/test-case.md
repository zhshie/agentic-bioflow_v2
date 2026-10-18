# 測試案例：Web 測試策略寫進 docs/TESTING.md

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
Source: specs/testing-web/plan.md only (no spec.md exists; maintainer instruction: cases come from the examples in the plan, nothing invented).
-->

**規格**：`specs/testing-web/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：測試本身在出錯時要會變紅（會擋下壞的文件），而不是永遠綠。
- **不在範圍**：計畫明講這次不做的事；確認真的沒做。

名詞說明：「新章節」指 `docs/TESTING.md` 裡標題為 `Testing the web` 的那一節，到下一個 `## ` 標題為止。TestClient 是 Starlette（本平台網頁用的框架）自帶的測試用「假瀏覽器」，直接對網頁程式發請求、拿回 HTML 文字，不需要真的開瀏覽器。

## User Story 1 — 機器怎麼測網頁（Half 1）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | Goal；Test 第 1 點 | 功能 | 實作完成 | 檢查 `docs/TESTING.md` 是否有標題 `Testing the web` | 找得到這個標題，且在整份文件只有一個 | 自動：`tests/testing_web_doc_test.sh` |
| TC-002 | Test 第 1 點 | 功能 | 同上 | 檢查 `docs/TESTING.md` 是否出現 `TestClient` 這個字 | 出現，且出現在新章節之內（不是只靠別處本來就有的字） | 自動：`tests/testing_web_doc_test.sh` |
| TC-003 | Goal Half 1 | 功能 | 同上 | 驗收者讀新章節的 Half 1 部分 | 寫明網頁是用 Starlette TestClient 測，對回傳的 HTML 斷言：狀態碼、關鍵文字、表單與連結存在 | 手動：驗收者讀 `docs/TESTING.md` 新章節 |
| TC-004 | Goal Half 1 | 功能 | 同上 | 驗收者讀新章節，看不用瀏覽器自動化這件事 | 明說不引入瀏覽器自動化依賴（Playwright／Selenium 之類），並給兩個理由：多一個很重的依賴、在 WSL／CI 上不穩；措辭沒有寫成「整個 repo 完全不用 Playwright」而與舊章節 Chrome login 矛盾 | 手動：驗收者讀 `docs/TESTING.md` 新章節 |
| TC-005 | Test 第 2 點 | 功能 | 同上 | 在 `platform/pyproject.toml` 與 `platform/constraints.txt` 搜尋 playwright、selenium、puppeteer（不分大小寫） | 兩個檔案都找不到任何一個 | 自動：`tests/testing_web_doc_test.sh` |
| TC-006 | Test 第 3 點 | 功能 | 同上 | 取出新章節裡點名的每個 `platform/tests/...py` 檔名，逐一檢查檔案存在 | 每個都存在；且至少點名了一個（沒點名任何檔案不算過） | 自動：`tests/testing_web_doc_test.sh` |
| TC-007 | Goal Half 1（用真實既有的網頁測試當例子） | 功能 | 同上 | 驗收者對新章節點名的每個檔案搜尋 `TestClient` | 每個被點名的例子檔裡真的有用到 TestClient（例如 `platform/tests/test_confirm_page.py`、`platform/tests/test_web_login.py` 這類） | 手動：驗收者 grep 後對照新章節 |
| TC-008 | Goal 平價測試 | 功能 | 同上 | 驗收者讀新章節的平價測試段 | 說明規則：每個動作都要同時有 MCP 工具和網頁路由，「欠帳清單」只會變短不會變長（出自 ROADMAP）；並說明它隨 011a 到來 | 手動：驗收者讀 `docs/TESTING.md` 新章節並對照 `docs/ROADMAP.md` 第 98 行 |
| TC-009 | Goal 平價測試（「若 v3 上還沒有檔案實作，就寫 not built yet」） | 功能 | 本分支上 `platform/tests/` 與 `tests/` 沒有任何平價測試檔 | 驗收者先搜尋確認沒有檔案實作平價測試，再看新章節 | 新章節寫了 `not built yet`；若驗收時其實已有檔案實作，則新章節必須改為指向該檔而不是寫 not built yet | 手動：驗收者 grep 平價測試並讀新章節 |
| TC-010 | Test 第 3 點（測試要會紅） | 例外 | 把新章節改成點名一個不存在的 `platform/tests/nope_does_not_exist.py` | 跑 `bash tests/testing_web_doc_test.sh` | 測試失敗並指出缺的檔名 | 自動：`tests/testing_web_doc_test.sh` |
| TC-011 | Test 第 2 點（測試要會紅） | 例外 | 在 `platform/pyproject.toml` 暫時加入一行含 playwright | 跑 `bash tests/testing_web_doc_test.sh` | 測試失敗並指出是 playwright | 自動：`tests/testing_web_doc_test.sh` |
| TC-012 | Test 第 1 點（測試要會紅） | 例外 | 把 `docs/TESTING.md` 新標題或 `TestClient` 或 `click-only` 任一個暫時拿掉 | 跑 `bash tests/testing_web_doc_test.sh` | 測試失敗並說缺的是哪一個 | 自動：`tests/testing_web_doc_test.sh` |

## User Story 2 — 人怎麼從頭到尾只用點的跑 16S（Half 2）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | Test 第 1 點 | 功能 | 實作完成 | 檢查 `docs/TESTING.md` 是否出現 `click-only` | 出現在新章節之內 | 自動：`tests/testing_web_doc_test.sh` |
| TC-014 | Goal Half 2 | 功能 | 同上 | 驗收者讀新章節的 Half 2 | 有一個名為「click-only 16S end to end」的人工程序，用編號步驟，順序為 setup → launch → running → results → finished 五個階段，每個階段至少有一個編號步驟 | 手動：驗收者讀 `docs/TESTING.md` 新章節 |
| TC-015 | Goal Half 2（what to check at each step） | 功能 | 同上 | 驗收者逐階段看 | 五個階段每一個都寫了「要檢查什麼」（看到什麼算過） | 手動：驗收者讀 `docs/TESTING.md` 新章節 |
| TC-016 | Goal Half 2（what to record） | 功能 | 同上 | 驗收者逐階段看 | 五個階段每一個都寫了「要記錄什麼」 | 手動：驗收者讀 `docs/TESTING.md` 新章節 |
| TC-017 | Goal Half 2（done only by clicking in the web） | 功能 | 同上 | 驗收者讀每個步驟的動作 | 每一步都是在網頁上點選完成；沒有任何一步要求打終端機指令、用 MCP 工具或請 AI 代做 | 手動：驗收者讀 `docs/TESTING.md` 新章節 |
| TC-018 | Goal Half 2（mark as Stage 3 procedure; pages not all built） | 功能 | 同上 | 驗收者讀該程序的開頭或標註 | 明說這是第 3 階段（Stage 3，網頁功能 011–013）用的程序，並明說程序走過的頁面還沒有全部做出來 | 手動：驗收者讀 `docs/TESTING.md` 新章節並對照 `docs/ROADMAP.md` 第 48 行 |

## User Story 3 — 這次不做的事（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | Out of scope：No code | 不在範圍 | 實作完成 | 驗收者看 `git diff main...HEAD --stat`（相對於計畫提交 fd77184 之後的變更） | 變更的檔案只有 `docs/TESTING.md`、`tests/testing_web_doc_test.sh` 與 `specs/testing-web/` 下的檔案；`platform/`、`hooks/`、`scripts/`、`skills/`、`commands/` 沒有任何變動 | 手動：驗收者 diff |
| TC-020 | Out of scope：Only the new section；Goal「do not rewrite the rest」 | 不在範圍 | 同上 | 驗收者看 `docs/TESTING.md` 的 diff | 只有新增行（新章節）；沒有任何既有行被刪除或改寫（含 Half 1/2/3、Procedure P1/P2 與 Chrome login 章節） | 手動：驗收者 diff |
| TC-021 | Out of scope：Do not edit CHANGELOG.md | 不在範圍 | 同上 | 驗收者看 diff | `CHANGELOG.md` 沒有任何變動 | 手動：驗收者 diff |
| TC-022 | Out of scope：no browser-automation dependency | 不在範圍 | 同上 | 驗收者看 diff | `platform/pyproject.toml`、`platform/constraints.txt` 與其他依賴清單沒有任何新增行；也沒有新增瀏覽器自動化的腳本 | 手動：驗收者 diff |

## 憲法與安全網

文件變更不碰安全網，但憲法的原則 7、8 把「檢查」指向 `docs/TESTING.md` 的 Procedure P1 與 P2，這次在同一份文件加章節，要證明沒有弄壞。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 原則 7、8（Check 指向 Procedure P1、P2） | 功能 | 實作完成 | 跑 `bash tests/constitution_checks_exist_test.sh` | 通過；`docs/TESTING.md` 仍有 Procedure P1 與 Procedure P2 兩個標題 | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-024 | 開發流程「每階段 run_all 全綠」 | 功能 | 同上 | 在 WSL／Linux 跑 `bash tests/run_all.sh`（或看 CI 結果） | 全綠，包含新加的 `tests/testing_web_doc_test.sh`，且其他讀取 `docs/TESTING.md` 的既有測試沒有變紅 | 自動：`tests/run_all.sh` |

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
