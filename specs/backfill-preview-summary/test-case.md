# 測試案例：runs offer-cleanup 預覽的總結行不再寫「已提出 0 張」

**規格**：`specs/backfill-preview-summary/plan.md`（本任務為 B 級小改動，以 plan 為規格，沒有獨立 spec.md）　**總覽**：`test-case-overview.md`

背景（白話）：終端機指令 `abf-platform runs offer-cleanup` 不加 `--apply` 時只是「預覽」，什麼都不會真的送出；但舊版最後一行仍寫「已提出 0 張、略過 N 個」，讀起來像真的送了東西。這次只把「預覽時的最後一行」改成預覽專用的一句，加 `--apply` 時的最後一行一個字都不變。

兩句的固定寫法（逐字）：

- 預覽：`預覽：會提出 N 張、略過 M 個；要真的提出請加 --apply (preview: would offer N, skip M; add --apply to offer)`
- 加 `--apply`：`已提出 N 張、略過 M 個 (offered N, skipped M)`

名詞：「預覽」＝沒給 `--apply`，或同時給了 `--list`。N＝這次「會提出」的 run 數；M＝其餘沒有要提出的 run 數（N＋M＝列出的 run 總數）。

測試情境用語：`three` ＝ 三個 run：`r-a`（屬 alice、跑成功）、`r-b`（屬 bob、跑成功）、`r-c`（屬 alice、失敗）。即「2 個可提、1 個略過」。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：邊角情況（例如什麼都不會提出）時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 預覽時最後一行是預覽專用句（優先度 P1）

維護者原話與對應：他 10-21 定「使用者看得到的行為改變要能說以前…以後…」。以前：預覽最後一行寫「已提出 0 張」；以後：寫「預覽：會提出 N 張…要真的提出請加 --apply」。他 10-27 定「中文顯示不能口語」，沿用正式用字。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 T1；目標；維護者「以後：預覽：會提出 N 張…要真的提出請加 --apply」 | 功能 | `three`（2 個可提、1 個略過） | 執行 `runs offer-cleanup --all`（沒有 `--apply`） | 結束碼 0；輸出最後一行逐字等於 `預覽：會提出 2 張、略過 1 個；要真的提出請加 --apply (preview: would offer 2, skip 1; add --apply to offer)`（略過是 1，不是 3） | 自動：`platform/tests/test_cleanup_backfill.py` |
| TC-002 | 計畫 T1「輸出沒有『已提出』」；維護者「以前：預覽最後一行寫已提出 0 張」 | 功能 | 同 TC-001 | 同 TC-001，檢查整段輸出（含每一列與最後一行） | 整段輸出任何一行都不含「已提出」二字 | 自動 |
| TC-003 | 計畫 T3；目標「同時給 --list 也算預覽」 | 功能 | `three` | 執行 `runs offer-cleanup --all --list --apply` | 視為預覽：最後一行逐字等於 TC-001 的預覽句（會提出 2 張、略過 1 個）；資料庫沒有新增任何清理申請 | 自動 |
| TC-004 | 目標「N＝這次會提出的 run 數」（單一 run 的形狀） | 功能 | `three` | 執行 `runs offer-cleanup r-a`（只給一個 run 名、沒有 `--apply`） | 最後一行逐字等於 `預覽：會提出 1 張、略過 0 個；要真的提出請加 --apply (preview: would offer 1, skip 0; add --apply to offer)` | 自動 |
| TC-005 | 目標「N＝這次會提出的 run 數」；維護者「以前寫已提出 0 張」（沒有任何可提時） | 例外 | 只有一個失敗的 run `r-c` | 執行 `runs offer-cleanup --all`（沒有 `--apply`） | 最後一行逐字等於 `預覽：會提出 0 張、略過 1 個；要真的提出請加 --apply (preview: would offer 0, skip 1; add --apply to offer)`；整段輸出不含「已提出」 | 自動 |
| TC-006 | 目標；範圍「略過」只算沒有要提出的（含指定使用者過濾後被略過的） | 功能 | `three` | 執行 `runs offer-cleanup --all --user alice`（沒有 `--apply`） | 最後一行逐字等於 `預覽：會提出 1 張、略過 2 個；要真的提出請加 --apply (preview: would offer 1, skip 2; add --apply to offer)`（r-a 會提、r-b 不是 alice 的、r-c 失敗） | 自動 |
| TC-007 | 作法 2「兩種句子都中英並列」；維護者「中文顯示不能口語」；環境事實「新句只提 --apply」 | 功能 | 同 TC-001 | 執行預覽，取最後一行 | 前半是中文、括號內是英文，格式與檔內其他句子一致；句中提到的選項只有 `--apply`，不含 `--yes`、`--force`；用詞為「預覽」「會提出」「要真的提出請加」，不用口語；`test_confirm_page.py` 的禁字檢查（TC-G02）仍通過 | 自動 |

## User Story 2 — 加 --apply 時最後一行完全不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 計畫 T2；目標「加 --apply 時最後一行不變」 | 功能 | `three` | 執行 `runs offer-cleanup --all --apply` | 最後一行逐字等於 `已提出 2 張、略過 1 個 (offered 2, skipped 1)`；既有斷言（現檔第 89 行）原封不動、仍通過 | 自動 |
| TC-009 | 裁決 1；範圍：只改預覽情境，`--apply` 情境不改 | 例外 | 只有一個失敗的 run `r-c` | 執行 `runs offer-cleanup --all --apply` | 最後一行仍逐字等於 `已提出 0 張、略過 1 個 (offered 0, skipped 1)`；現檔第 137 行這條斷言沒有被改成預覽句、沒有被放寬（此情境有給 `--apply`，不是預覽） | 自動 |
| TC-010 | 目標「加 --apply 時最後一行不變」；總結行數字取自動作層的回答 | 功能 | 動作層被換成假的，回答「offered 0、skipped 1、一個 made up 的略過列」 | 執行 `runs offer-cleanup zz --apply` | 有一行 `zz: 略過：made up`；最後一行逐字等於 `已提出 0 張、略過 1 個 (offered 0, skipped 1)`；現檔第 223 行斷言原封不動、仍通過 | 自動 |
| TC-011 | 目標；「不做：不改行為，只改字」 | 功能 | `three` | 執行 `runs offer-cleanup --all --apply` 後查資料庫 | 與改動前一樣：恰好 2 筆待處理（pending）清理申請，分別屬於 alice 與 bob；失敗的 r-c 沒有申請 | 自動 |

## User Story 3 — 判斷條件只有一份，且文件跟著改（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法 1「預覽與否用同一個條件，不另寫一份」 | 功能 | 動作層被換成會記下它收到的 `dry_run` 值的假函式；假函式在預覽時回傳帶 `would_offer` 的列 | 依序執行四種旗標組合：無旗標、`--list`、`--apply`、`--list --apply` | 動作層收到 `dry_run=True` 的組合（無旗標、`--list`、`--list --apply`），最後一行都是預覽句；收到 `dry_run=False` 的組合（只有 `--apply`），最後一行都是「已提出…」句；兩者不會對不上 | 自動 |
| TC-013 | 範圍：`docs/TESTING.md` cloud-cleanup-backfill 第 2 步補一句 | 功能 | 開啟 `docs/TESTING.md` 的「Offering a clean-up for an old run (cloud-cleanup-backfill)」一節 | 讀第 2 步 | 第 2 步新增一句，明說「最後一行以『預覽：』開頭」；第 3 步及其他步驟文字不變 | 手動：`docs/TESTING.md` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 不做 1：不改每列（會提出申請／已提出申請／略過）的句子 | 不在範圍 | `three` | 分別執行預覽（`--all`）與 `--all --apply` | 預覽每列仍是 `r-a: 會提出申請 (would offer)`、`r-b: 會提出申請 (would offer)`、`r-c: 略過：…`；`--apply` 每列仍是 `r-a: 已提出申請，請 alice 登入網頁在確認頁按送出 (offered; alice presses send on the confirmation page)`（bob 同理）與 `r-c: 略過：…`；現檔第 85、86、167、168 行等既有斷言不動、仍通過 | 自動 |
| TC-015 | 不做 2：不改 `actions.offer_cleanups` 的回傳形狀 | 不在範圍 | 讀變更的檔案清單與內容 | 檢查 `platform/abf_platform/actions/__init__.py` | 此檔沒有出現在變更中；既有的回傳形狀測試（`test_dry_run_and_the_shape_of_the_answer`）原封不動、仍通過；預覽句的數字完全在 `cli.py` 端算出 | 自動：同檔既有測試＋變更清單檢查 |
| TC-016 | 完成標準「diff 只含四個檔＋specs 目錄」；範圍「不准動」；裁決 1 | 不在範圍 | 實作完成後 | 列出相對於 base 的變更檔案，並比對 `test_cleanup_backfill.py` 的 diff | 變更檔只有 `platform/abf_platform/cli.py`、`platform/tests/test_cleanup_backfill.py`、`docs/TESTING.md`、`specs/backfill-preview-summary/` 底下檔案；`receiver.py`、`actions/__init__.py`、`tests/platform_test.sh`、其他測試檔、`.specify/`、`docs/ROADMAP.md` 都沒動；測試檔只做「新增預覽句與不含『已提出』的斷言」，沒有任何既有斷言被刪除、放寬或改值 | 手動：閱卷者逐檔比對 diff |

## 憲法與安全網

涉及的規則：專長守則（backend）的「確認管道」「動作層唯一邏輯」「錯誤訊息與日誌不洩密」「結構變動要 migration」；憲法第 9 條（寫給使用者的數字必須來自實際結果）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 確認管道：沒有確認就不得寫入；預覽什麼都不寫 | 功能 | `three`；記下清理申請與工作（jobs）的筆數 | 執行預覽（`--all`、`r-a`、`--all --list` 各一次） | 三次執行後，確認（confirmations）與工作的筆數與執行前完全相同；既有 `test_without_apply_nothing_is_written` 原封不動、仍通過 | 自動 |
| TC-018 | 動作層唯一邏輯／第 9 條：指令端只印動作層的回答，不自己判斷 | 功能 | 讀 `cmd_runs_offer_cleanup` 原始碼 | 執行既有的「指令從不確認、沒有第二份邏輯」測試 | 指令函式原始碼不含 `approve`、`enqueue`、`subprocess`、`os.system`、`work_cleaned_at`、`create_pending`、`prepare_clean`、`latest_launch`；預覽句的 N 來自動作層回傳的 `would_offer` 列，不是指令端另行查資料庫判斷；既有測試不動、仍通過 | 自動 |
| TC-019 | 結構變動要 migration：此任務不改資料結構 | 不在範圍 | 實作完成後 | 檢查變更檔案清單 | 沒有任何 migration、schema 或資料庫相關檔案被新增或修改；計畫與帳本寫明「不需要 migration，只改終端機文字」 | 手動：閱卷者看 diff 與 `ledger.md` |
| TC-020 | 錯誤訊息與日誌不洩密 | 功能 | `three` | 分別執行預覽與 `--apply`，檢查最後一行 | 兩種最後一行只含固定文字與兩個數字，不含 token、密碼、路徑、SQL 或堆疊 | 自動 |
