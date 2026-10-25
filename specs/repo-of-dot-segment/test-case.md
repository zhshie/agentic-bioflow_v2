# 測試案例：releases.repo_of 拒絕「.」段與結尾換行

**規格**：`specs/repo-of-dot-segment/plan.md`（本片是 tier A 小修，沒有獨立 spec.md；計畫與維護者原話即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞：「管線名稱檢查」指 `platform/abf_platform/releases.py` 的 `repo_of`，它把使用者打的管線名稱整理成 `owner/name` 的樣子，不合格就丟出 `ValueError`（錯誤）。之後這個名稱會被拿去組 GitHub 網址，所以要在這一層就擋掉怪名字。「單點段」指用 `/` 切開後，某一段只有一個 `.`（例如 `./x` 的第一段）。

維護者原話對照：「Pin an exact pipeline revision, never a branch」（名稱與版本都要是確定、乾淨的值）與 2026-10-25「好，放寬」（名稱檢查是放寬後的安全邊界）。這兩句沒有給具體輸入；具體輸入一律取自計畫「失敗先行測試」列出的六個壞名字與 `a.b/c.d`，下列 TC 逐字使用。

## User Story 1 — 含單點段的名字被拒絕（優先度 P1）

每條「拒絕」的共同預期：丟出 `ValueError`，訊息同時含中文與英文（與既有拒絕案例同一個檢查：中文字元與至少三個英文字母都在）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「作法」2；失敗先行測試 `"./x"` | 例外 | 無 | 把 `./x` 交給 `repo_of` | 被拒絕：`ValueError`，訊息含中文與英文 | 自動：`platform/tests/test_releases.py::test_t2_repo_of_rejects[./x]` |
| TC-002 | 計畫「作法」2；`"x/."` | 例外 | 無 | 把 `x/.` 交給 `repo_of` | 被拒絕：`ValueError`，訊息含中文與英文 | 自動：`test_t2_repo_of_rejects[x/.]` |
| TC-003 | 計畫「作法」2；`"./."` | 例外 | 無 | 把 `./.` 交給 `repo_of` | 被拒絕：`ValueError`，訊息含中文與英文 | 自動：`test_t2_repo_of_rejects[./.]` |
| TC-004 | 計畫「作法」2；`"."`（補成 `nf-core/.`） | 例外 | 無 | 把單獨一個 `.` 交給 `repo_of`（它會先被補成 `nf-core/.`） | 被拒絕：`ValueError`，訊息含中文與英文 | 自動：`test_t2_repo_of_rejects[.]` |

## User Story 2 — 結尾帶換行的名字被拒絕（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 計畫「作法」1；`"nf-core/ampliseq\n"` | 例外 | 無 | 把 `nf-core/ampliseq` 後面多接一個換行字元交給 `repo_of` | 被拒絕：`ValueError`，訊息含中文與英文（基準版會放行，這條必須先紅後綠） | 自動：`test_t2_repo_of_rejects` 的 `nf-core/ampliseq\n` 案例 |
| TC-006 | 計畫「作法」1；`"ampliseq\n"` | 例外 | 無 | 把 `ampliseq` 後面多接一個換行字元交給 `repo_of`（會先被補成 `nf-core/ampliseq\n`） | 被拒絕：`ValueError`，訊息含中文與英文 | 自動：`test_t2_repo_of_rejects` 的 `ampliseq\n` 案例 |

## User Story 3 — 其他行為不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 計畫「失敗先行測試」`a.b/c.d` | 功能 | 無 | 把 `a.b/c.d`（段內含點，但不是單點段）交給 `repo_of` | 被接受，原樣回傳 `a.b/c.d`，沒有被誤擋 | 自動：`platform/tests/test_releases.py` 內一條斷言（放在哪個測試函式由執行者決定，只要不刪改既有案例） |
| TC-008 | 計畫「作法」3；既有 `test_t1_repo_of_accepts` | 功能 | 無 | 把 `ampliseq` 交給 `repo_of` | 回傳 `nf-core/ampliseq` | 自動：`test_t1_repo_of_accepts`（原樣、不修改） |
| TC-009 | 計畫「作法」3；既有 `test_t1_repo_of_accepts` | 功能 | 無 | 把 `nf-core/ampliseq` 與 `lab/own-flow` 各交給 `repo_of` | 各自原樣回傳 | 自動：`test_t1_repo_of_accepts`（原樣、不修改） |
| TC-010 | 計畫「完成標準」：既有案例不變且綠 | 例外 | 無 | 把既有壞名字 `""`、`../x`、`a/b/c`、`nf core/x`、`None` 各交給 `repo_of` | 全部仍被拒絕，行為與基準版相同 | 自動：`test_t2_repo_of_rejects` 既有五個參數 |
| TC-011 | 計畫「作法」2、「不做」：不改錯誤訊息文字 | 例外 | 無 | 對任一壞名字（例如 `./x`）取得 `ValueError` 的訊息 | 訊息文字與基準版逐字相同：`pipeline 名稱不合格（要寫 owner/name，例如 nf-core/ampliseq） / invalid pipeline name '<輸入>', expected owner/name`（不露出堆疊、路徑） | 自動：測試中把訊息與上述固定文字比對（或閱卷者以 `git diff` 確認該字串未變） |

## User Story 4 — 範圍與完成標準（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 計畫「範圍：檔案」；完成標準第 2 條 | 不在範圍 | 實作完成 | 執行 `git diff <base>...HEAD --name-only` | 只列出三個檔：`platform/abf_platform/releases.py`、`platform/tests/test_releases.py`、`specs/repo-of-dot-segment/ledger.md`，沒有第四個（包括沒有 `test-case*.md`、計畫、其他程式） | 手動：閱卷者執行該 git 指令（不另寫入 `docs/TESTING.md`，因為不是使用者操作步驟） |
| TC-013 | 計畫「範圍」：`releases.py` 只改 `_REPO` 與 `repo_of` | 不在範圍 | 實作完成 | 檢視 `git diff` 中 `releases.py` 的變動 | 只有 `_REPO` 與 `repo_of` 內的變動；`_TAG`、`usable`、`pick_latest`、`parse_ls_remote`、`lookup` 等其他函式一字未動 | 手動：閱卷者看 diff |
| TC-014 | 計畫「範圍」：測試檔不刪不改既有案例 | 不在範圍 | 實作完成 | 比較 `test_releases.py` 與基準版 | 只有新增（參數清單加案例、新增的斷言）；既有案例、既有參數值、既有斷言無任何刪除、改寫、放寬或跳過 | 手動：閱卷者看 diff |
| TC-015 | 計畫「環境事實」：不加任何 import | 不在範圍 | 實作完成 | 跑 `test_scope.py` 的 TC-061／TC-071（掃 `abf_platform/`） | 兩條仍綠；`releases.py` 沒有新增 import | 自動：`platform/tests/test_scope.py` 既有 TC-061、TC-071 |
| TC-016 | 計畫「不做」：不碰 release-lookup-job 的代理端檢查；`lookup` 等行為不變 | 不在範圍 | 實作完成 | 跑 `test_releases.py` 中 `repo_of` 以外的既有測試（`usable`、`pick_latest`、`parse_ls_remote`、`lookup`） | 全部仍綠、沒被修改；沒有任何代理端或網路相關的新檔案或新程式 | 自動：`platform/tests/test_releases.py` 既有 T3 以後案例 |
| TC-017 | 計畫「完成標準」：全套綠 | 功能 | 實作完成 | 執行者跑完整測試套件（`tests/run_all.sh`，在 WSL） | 在最終 HEAD 上全綠，並留下 `GREEN <HEAD sha>` 完成記號 | 自動：`tests/run_all.sh`（由完成記號與閱卷者的 gate 檢查證明，閱卷者不重跑全套） |
