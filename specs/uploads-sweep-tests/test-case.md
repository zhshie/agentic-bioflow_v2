# 測試案例：uploads_web.sweep 補測試（清掉過期上傳暫存夾）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本片沒有 spec.md，來源是 plan.md；沒有維護者逐字原話（plan 的「維護者原話」一節明寫「沒有可引用的逐字原話」）。
預期結果全部來自 plan 的「作法」七條、「失敗先行測試」、「完成標準」、「不做」與「裁決」；沒有加入 plan 沒說的行為。
-->

**規格**：`specs/uploads-sweep-tests/plan.md`（本片無 spec.md）　**總覽**：`test-case-overview.md`

名詞（一行說明）：
- **暫存夾**：網頁上傳時在使用者上傳區建的 `.incoming-<批次>` 資料夾，請求當掉或斷電時會被留下。
- **sweep**：`uploads_web.sweep(area, now=None, older=86400)`，在下一次上傳開始前清掉「超過 24 小時」的舊暫存夾。
- **now / 調舊**：測試傳入固定的整數 `now`（例如 `1_800_000_000`），再用 `os.utime` 把夾子的修改時間設成 `now - N` 秒；不等待、不用真實時間。
- 以下「夾子」都是先把裡面的檔案建好，**最後**才 `os.utime` 調時間（因為在夾子裡新增或刪除項目會把夾子時間改回現在）。

類型只有三種：

- **功能**：plan 說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、不該被動到的東西時，系統怎麼反應（不刪、不報錯）。
- **不在範圍**：plan 明講這次不做的事；確認它真的沒做。

## User Story 1 — sweep 只清「超過 24 小時的 `.incoming-` 暫存夾」，其他一概不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；目標「舊的被清」 | 功能 | 上傳區 `area` 內有 `.incoming-` 加 32 個 `a` 的資料夾，內含 `1.part`、`2.part`；夾子時間調成 `now - 86401` | 呼叫 `sweep(area, now=now)` | 該夾子整個不存在（連同兩個 `.part` 檔） | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-002 | 作法 2；裁決 4 | 功能 | 同 TC-001，但夾子時間調成剛好 `now - 86400` | 呼叫 `sweep(area, now=now)` | 夾子還在，`1.part`、`2.part` 也還在（「超過」是嚴格大於，剛好 86400 秒不清） | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-003 | 作法 3；目標「新的不動」 | 功能 | 同 TC-001，但夾子時間調成 `now - 10` | 呼叫 `sweep(area, now=now)` | 夾子還在，`1.part`、`2.part` 也還在 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-004 | 作法 4（「整片最重要的一條」）；目標「已上傳完成的檔案絕不動」 | 例外 | 同一個 `area` 內有檔案 `final.fastq.gz`（模擬已完成上傳的檔，有內容）；時間調成 `now - 10**7`（極舊） | 呼叫 `sweep(area, now=now)` | `final.fastq.gz` 還在，內容與原來完全相同 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-005 | 作法 4；目標「`.batches` 紀錄絕不動」 | 例外 | 同一個 `area` 內有資料夾 `.batches/`，裡面一個檔案；`.batches/` 時間調成 `now - 10**7` | 呼叫 `sweep(area, now=now)` | `.batches/` 還在，裡面的檔案還在、內容不變 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-006 | 作法 4 | 例外 | 同一個 `area` 內有資料夾 `incoming-nodot/`（名字開頭沒有點），裡面有檔案；時間調成 `now - 10**7` | 呼叫 `sweep(area, now=now)` | `incoming-nodot/` 還在，裡面的檔案還在、內容不變 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-007 | 作法 4 | 例外 | 同一個 `area` 內有項目 `.incomingX`（名字沒有連字號）；時間調成 `now - 10**7` | 呼叫 `sweep(area, now=now)` | `.incomingX` 還在，內容不變 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-008 | 作法 5；目標「上傳區不存在時不報錯」 | 例外 | 路徑 `tmp_path / "nope"` 不存在 | 呼叫 `sweep(tmp_path / "nope")` | 不丟出任何例外 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-009 | 作法 5 | 例外 | 同 TC-008 | 呼叫 `sweep(tmp_path / "nope")` 並取回傳值 | 回傳值是 `None` | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-010 | 作法 6（特徵化） | 功能 | 舊暫存夾（時間 `now - 86401`）內有 `.part` 檔，另有一個子資料夾；executor 已先在 v3 上親眼確認此行為 | 呼叫 `sweep(area, now=now)` | 不丟出例外 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-011 | 作法 6（特徵化） | 功能 | 同 TC-010 | 呼叫 `sweep(area, now=now)` | 暫存夾本身還在（因為 `discard` 只刪檔、有子資料夾就無法移除資料夾），夾子裡直接的 `.part` 檔已被刪 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-012 | 作法 7 | 例外 | `area` 內兩個舊暫存夾（都調成 `now - 86401`）：一個含子資料夾（清不乾淨），另一個只有 `.part` 檔（正常）；不論系統列出的先後順序 | 呼叫 `sweep(area, now=now)` | 不丟出例外，且正常的那一個已被整個清掉 | 自動：`platform/tests/test_uploads_sweep.py` |

## User Story 2 — 只加測試、證明測試真的會抓錯、範圍不外溢（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 範圍：檔案；完成標準「`git diff --stat` 只含新檔」 | 不在範圍 | 實作完成，所有改動已提交 | 查 `git diff --stat origin/v3...HEAD`（可另加本任務 ledger 與 specs 目錄下檔案，但程式與測試的部分） | 程式與測試方面只新增 `platform/tests/test_uploads_sweep.py` 一個檔，沒有修改或刪除任何既有檔案 | 手動：verifier 閱卷時讀 diff（ledger 亦須記 `git diff --stat`） |
| TC-014 | 不做「不改 sweep／discard 的任何行為（包含讓 discard 能刪子資料夾）」「不改 STALE_SECONDS」 | 不在範圍 | 同 TC-013 | 查 `git diff origin/v3...HEAD -- platform/abf_platform/uploads_web.py` | 輸出為空；`STALE_SECONDS` 仍是 `86400`，`discard` 仍只刪檔 | 手動：verifier 閱卷時讀 diff |
| TC-015 | 不做「不動 web.py 的呼叫方式」「不新增依賴、不新增 CLI 旗標」；範圍「不准碰」清單 | 不在範圍 | 同 TC-013 | 查 diff 是否碰到 `web.py`、`mcp_server.py`、`jobs.py`、`build.py`、`launch.py`、`compute_envs.py`、`tests/platform_upgrade_test.sh`、`docs/`、`platform/tests/test_web_upload.py`、依賴釘版檔（`constraints.txt`） | 以上檔案全都沒有改動 | 手動：verifier 閱卷時讀 diff |
| TC-016 | 作法「不使用 `time.sleep`、不使用真實時間差」 | 功能 | 新測試檔完成 | 在 `platform/tests/test_uploads_sweep.py` 搜尋 `sleep` 與 `time.time` | 都沒有出現；每條測試都用注入的 `now` | 手動：verifier 閱卷時搜尋該檔 |
| TC-017 | 裁決 4 | 功能 | 新測試檔完成 | 讀測試檔裡的 `now` 與所有 `os.utime` 的時間值 | `now` 是整數常數（例如 `1_800_000_000`）；所有 `os.utime` 的時間都是整數秒，沒有浮點數 | 手動：verifier 閱卷時讀該檔 |
| TC-018 | 環境事實「只用 `tmp_path` 與 `os.utime`，不連網、不啟動任何程式」 | 功能 | 新測試檔完成 | 讀測試檔，看它碰到的檔案系統位置與外部呼叫 | 所有檔案都建在 `tmp_path` 之下；沒有網路、沒有啟動外部程式、沒有碰真實的使用者上傳區 | 手動：verifier 閱卷時讀該檔 |
| TC-019 | 失敗先行測試「在 v3 上應全綠（描述現況）」；完成標準「7 條全綠」 | 功能 | 新測試檔寫好，`uploads_web.py` 與 v3 相同 | 執行 `py -3 -m pytest platform/tests/test_uploads_sweep.py` | 涵蓋 plan 七條案例的測試全部通過，沒有被跳過（skip）或預期失敗（xfail）的 | 自動：`platform/tests/test_uploads_sweep.py` |
| TC-020 | 突變證明 1 | 功能 | 一次性：暫時把 `if n.startswith(".incoming-"):` 改成 `if True:` | 執行 `py -3 -m pytest platform/tests/test_uploads_sweep.py` | 第 4 條案例（TC-004 至 TC-007 所屬的「別的東西絕不動」測試）變紅 | 手動：ledger 貼輸出（一次性，不進 repo） |
| TC-021 | 突變證明 2 | 功能 | 一次性：暫時把 `now - os.path.getmtime(path) > older` 改成 `>=` | 執行同一指令 | 第 2 條案例（TC-002 剛好 86400 秒不清）變紅 | 手動：ledger 貼輸出 |
| TC-022 | 突變證明 3 | 功能 | 一次性：暫時把 `if now - ... > older:` 判斷整行拿掉（一律清） | 執行同一指令 | 第 3 條案例（TC-003 新的不動）變紅 | 手動：ledger 貼輸出 |
| TC-023 | 突變證明收尾「跑完立刻還原」；「最終 diff 不得含 uploads_web.py」 | 功能 | 三次突變都跑完後，執行 `git checkout -- platform/abf_platform/uploads_web.py` | 再跑 `py -3 -m pytest platform/tests/test_uploads_sweep.py`，並查 `git status` | 測試全綠；`uploads_web.py` 沒有任何未提交或已提交的改動 | 手動：ledger 貼還原後的綠與 `git status` |
| TC-024 | 完成標準「`test_uploads_sweep.py` 與 `test_web_upload.py` 一起全綠」 | 功能 | 新測試檔已加入 | 執行 `py -3 -m pytest platform/tests/test_uploads_sweep.py platform/tests/test_web_upload.py` | 全綠（既有網頁上傳測試沒被影響） | 自動：`platform/tests/test_uploads_sweep.py`、`platform/tests/test_web_upload.py` |
| TC-025 | 裁決 1 | 功能 | 實作完成 | 讀 ledger | 有一句話記下：sweep 以資料夾修改時間判斷「舊」、寫入既有檔案不會更新資料夾時間，連續超過 24 小時的上傳理論上可能被清；決定不處理、行為變更另案請維護者裁決 | 手動：verifier 閱卷時讀 ledger |
| TC-026 | 裁決 2 | 功能 | 新測試檔完成 | 讀 TC-010／TC-011（子資料夾案例）的測試註解 | 註解明寫這是「特徵化（描述現況）、不是期望行為」，目的是將來有人改 `discard` 行為時提醒 | 手動：verifier 閱卷時讀該檔 |

<!--
專長守則（backend）檢查：本片只新增檔案系統測試，不新增或改動任何網頁／API／聊天動作、寫入動作、使用者紀錄、錯誤訊息、日誌或資料結構，
所以對等性、跨使用者、確認管道、錯誤訊息與日誌、migration 各條都不適用，沒有對應 TC；TC-013 至 TC-015 保證確實沒有碰到那些程式。
憲法與安全網：本片不改任何憲法條目或 Safety Net 規則涵蓋的程式，故不設「憲法與安全網」一節。
-->
