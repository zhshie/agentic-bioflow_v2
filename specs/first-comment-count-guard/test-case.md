# 測試案例：mcp_server.py 第一行註解的工具數字改由測試算出真實數字比對

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
-->

**規格**：`specs/first-comment-count-guard/`（本片沒有 spec.md；依據是 `dev-plans/first-comment-count-guard.md` 計畫，下稱「計畫」）　**總覽**：`test-case-overview.md`

白話說明：`platform/abf_platform/mcp_server.py` 的第 1 行是一句註解，裡面寫了「offers fifteen read-only tools」這類數字。現在的測試只確認這行沒有 six／seven，所以數字寫錯成別的字（例如 ten）測試照樣過。這一片要讓測試自己數出「真正登記的唯讀工具有幾個」，再要求第 1 行的數字字剛好就是這個數。這是「只收緊、不放寬」的 A 級測試補強，使用者看得到的行為不變。

下文「護欄函式」指計畫新增的 `_first_line_problems(first, n)`：給它第 1 行文字和真實數量 n，回傳問題清單，空清單代表通過。「唯讀工具數 n」指測試用 `ast` 數出的 `_READ_ONLY` 工具個數（本 worktree 目前是 15，全部工具 20 個）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：壞資料或壞狀況出現時，護欄怎麼反應（必須變紅、必須回報問題）。
- **不在範圍**：計畫明講不做的事；確認真的沒做。

## US1 — 護欄函式本身判斷正確（純函式層，永久留在測試檔）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「失敗先行測試」第 1 條 `test_first_line_guard_rejects_stale_count_ten`；作法 1（值必須等於 n） | 例外 | 實際唯讀工具數 n 是 15 | 把 `# ... offers ten read-only tools ...` 當第 1 行、n=15 交給護欄函式 | 回傳的問題清單不是空的（數字字 ten 對不上 15，被擋下） | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-002 | 計畫「失敗先行測試」第 2 條 `test_first_line_guard_rejects_old_six_seven`；作法 1（不得含值 ≠ n 的數字字，涵蓋舊斷言） | 例外 | 實際唯讀工具數 n 是 10 | 分別把含 six 的一行、含 seven 的一行（例如 `... offers six read-only tools ...`、`... offers seven read-only tools ...`）交給護欄函式，n=10 | 兩次回傳的問題清單都不是空的 | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-003 | 計畫「失敗先行測試」第 3 條 `test_first_line_guard_rejects_missing_count`；作法 1（至少要有緊接 read-only 的數字字）；裁決 1 | 例外 | 任一 n（例如 15） | 把完全沒有數字字的一行（例如 `# offers read-only tools`）交給護欄函式 | 回傳的問題清單不是空的，且說明「第 1 行沒寫唯讀工具數」之類的原因 | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-004 | 計畫「失敗先行測試」第 4 條 `test_first_line_guard_accepts_matching_count`；作法 1 | 功能 | 實際唯讀工具數 n 是 15 | 把 `... offers fifteen read-only tools` 交給護欄函式，n=15 | 回傳空清單（通過） | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-005 | 作法 1（數字字必須緊接 `read-only`） | 例外 | n=15 | 把有數字字但不緊接 read-only 的一行（例如 `# offers fifteen tools`）交給護欄函式 | 回傳的問題清單不是空的（沒有緊接 read-only 的數字字，等於沒寫唯讀工具數） | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-006 | 作法 1（第 1 行不得含任何值 ≠ n 的數字字） | 例外 | n=15 | 把同時有對的數字和別的錯數字字的一行（例如 `# offers fifteen read-only tools ... ten ...`）交給護欄函式 | 回傳的問題清單不是空的（即使 fifteen 對了，多出來的 ten 也要被擋） | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-007 | 裁決 2（舊斷言 six／seven 在 n=6 或 7 時會誤紅，新版不該誤紅） | 功能 | n=6 | 把 `... offers six read-only tools` 交給護欄函式，n=6 | 回傳空清單（數字字剛好是真實數量就該過，不因為出現 six 而誤紅） | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-008 | 作法 4（n 超出 `NUMBERS` 範圍 → 測試要紅並說「請擴 NUMBERS」，不准靜默略過） | 例外 | `NUMBERS` 只到 fifteen；n=16（或任何超出表的值） | 以 n=16 讓護欄（函式或使用它的測試）判斷任何一行 | 結果是紅／回報問題，不是靜默通過；訊息指示「請擴 `NUMBERS`」 | 自動：`platform/tests/test_mcp_server_doc.py`（若這條行為放在測試本體而非護欄函式，閱卷者以一次性 n=16 重現） |

## US2 — 真實的第 1 行被真實數量檢查（整合層與證明方式）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | 作法 3；計畫「整合層」 | 功能 | `mcp_server.py` 保持原樣（第 1 行寫 `offers fifteen read-only tools`） | 跑改寫後的 `test_first_comment_line_does_not_name_an_old_count` | 通過；測試內容是對真實檔案第 1 行呼叫護欄函式並要求問題清單為空，不再只是 `"six" not in first and "seven" not in first` | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-010 | 作法 2（n 與 `test_module_doc_counts_the_read_only_tools` 算法完全相同、不寫死） | 功能 | 讀改寫後的測試檔 | 閱卷者讀碼：n 是不是用 `_tools()` 數 `a == "_READ_ONLY"` 的個數，而不是寫死 15 | n 由 `ast` 算出，算法與文件字串那條既有測試相同；沒有把 15 或 `fifteen` 寫死在整合測試裡 | 手動：閱卷者讀碼（非 `docs/TESTING.md` 步驟） |
| TC-011 | 計畫「完成標準」第 2 條 | 功能 | worktree 乾淨，測試檔為改寫後版本 | `py -3 -m pytest platform/tests/test_mcp_server_doc.py`（或 WSL） | 整個檔案全綠：四條護欄函式測試、改寫後的整合測試，以及原有的 `test_registered_tools_are_the_known_twenty`、`test_module_doc_names_every_registered_tool`、`test_module_doc_counts_the_read_only_tools` 都通過 | 自動：`platform/tests/test_mcp_server_doc.py` |
| TC-012 | 計畫「突變證明」（新護欄抓得到錯字） | 例外 | 暫時用 `sed` 把 `mcp_server.py` 第 1 行的 `fifteen` 換成 `ten`（一次性，不進 repo） | 跑 `py -3 -m pytest platform/tests/test_mcp_server_doc.py` | 改寫後的 `test_first_comment_line_does_not_name_an_old_count` 變紅；跑完用 `git checkout -- platform/abf_platform/mcp_server.py` 還原，還原後再跑回到全綠 | 手動：閱卷者依 ledger 重做（一次性，非 `docs/TESTING.md` 步驟） |
| TC-013 | 計畫「突變證明」（舊護欄確實漏掉） | 例外 | 同 TC-012 的突變（`fifteen`→`ten`）；舊版測試檔用 `git show <base>:platform/tests/test_mcp_server_doc.py` 另存到暫存位置 | 用舊版測試檔對突變後的 `mcp_server.py` 跑 | 舊版 `test_first_comment_line_does_not_name_an_old_count` 仍是綠的（證明舊護欄抓不到 ten）；兩邊結果並列貼進 ledger | 手動：閱卷者依 ledger 重做 |
| TC-014 | 計畫「失敗先行測試」（空殼先紅） | 例外 | ledger 記錄實作順序 | 閱卷者讀 ledger：`_first_line_problems` 先寫成只有 `return []` 的空殼時的測試輸出 | ledger 貼有空殼輸出：TC-001、TC-002、TC-003 三條紅，TC-004 綠；之後實作才轉綠 | 手動：閱卷者讀 ledger |

## US3 — 計畫明講不做的事（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 計畫「不做」第 1 條；「範圍：不准碰」 | 不在範圍 | 實作完成、已提交 | `git diff <base>...HEAD -- platform/abf_platform/mcp_server.py`，並看 `git diff` 有無未提交變更 | 沒有任何差異（第 1 行文字也沒改；突變已還原） | 手動：閱卷者執行 git diff |
| TC-016 | 計畫「範圍：檔案」；「完成標準」第 3 條 | 不在範圍 | 實作完成 | `git diff --stat <base>...HEAD` | 變更檔案只有 `platform/tests/test_mcp_server_doc.py`（加上計畫允許的 `specs/first-comment-count-guard/ledger.md`）；沒有其他測試檔、`docs/`、`.github/`、`spec.md`、`test-case*.md` | 手動：閱卷者執行 git diff |
| TC-017 | 計畫「不做」第 2 條 | 不在範圍 | 比對 base 與 HEAD 的測試檔 | 閱卷者比對 `test_module_doc_counts_the_read_only_tools`、`test_module_doc_names_every_registered_tool`、`test_registered_tools_are_the_known_twenty` 與 `NUMBERS`、`EXPECTED` | 這幾條測試一字不差；`NUMBERS` 沒變（n=15 在表內，不需擴；若有擴，ledger 說明是因為 n 超表） | 手動：閱卷者比對 diff |
| TC-018 | 計畫「不做」第 3 條；「環境事實」（只讀原始碼文字，不需安裝 mcp） | 不在範圍 | 實作完成 | 看測試檔新增的 import 與 diff 有無依賴檔案（如 requirements、pyproject）變動 | 沒有新增依賴；新增程式只用標準函式庫（`re`、`ast`、`pathlib` 這類測試檔原本就有的）；測試仍不需安裝 mcp 就能跑 | 手動：閱卷者讀 diff |

## 憲法與安全網

這片不碰憲法的 13 條不變量本身，但派工與憲法決策分級要求 A 級「只收緊、不放寬」：放寬安全網是維護者的事。護欄測試屬於防止文件悄悄過期的網，下面兩條證明沒有放寬。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 開發流程／決策分級：A 級只收緊、不放寬安全網；計畫「完成標準」第 3 條、裁決 2 | 例外 | 舊的 `"six" not in first and "seven" not in first` 被新護欄取代 | 閱卷者讀 ledger | ledger 逐句說明為什麼新版比舊斷言更嚴（不含任何值 ≠ n 的數字字，涵蓋 six／seven，且還要求有數字字、數字要等於 n）；沒有任何既有斷言被悄悄刪掉而沒說明 | 手動：閱卷者讀 ledger 與 diff |
| TC-020 | 開發流程／決策分級：不放寬；比對 base（舊護欄擋得住的壞資料新護欄仍要擋） | 例外 | 暫時把 `mcp_server.py` 第 1 行的 `fifteen` 換成 `six`（再試一次換成 `seven`；一次性，不進 repo） | 用舊版測試檔和改寫後的測試檔各跑一次 | 舊版紅、新版也紅（舊護欄擋得住的，新護欄一個都沒漏）；之後還原 `mcp_server.py` | 手動：閱卷者重做 |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
