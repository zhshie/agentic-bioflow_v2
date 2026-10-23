# 測試案例：失敗 run 照 Seqera 模式帶出失敗 task／exit code／日誌＋Resume／Relaunch（唯讀，不分類）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務沒有 spec.md，需求來源是 `specs/failure-seqera/plan.md`（含維護者原話）。
-->

**規格**：`specs/failure-seqera/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺東西、不該顯示的人、舊資料時，系統怎麼反應。
- **不在範圍**：計畫明講不做的事；測試確認它真的沒做。

名詞（一句話）：「view」＝狀態模組為一個 run 整理出的資料包（含 status、failed_tasks、tasks 計數等）；`summarize` ＝本任務新增、把失敗的 view 轉成固定五欄的函式；「動作層」＝網頁、MCP、聊天共用的那一層函式（`actions.get_run`、`actions.list_runs`）。

維護者原話（出題依據）：
1.「分成四類 改成 跟Seqera platform一樣的模式，不要自己定義」
2.「失敗原因直接參考Seqera platform架構。」
3.「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」（只回欄位值，不產生句子）

以下測試案例中，「手造 view」＝測試自己組一個資料包，不開伺服器；「種一筆」＝用既有的 store／平台測試工具在暫存目錄建一筆 run。

## User Story 1 — 失敗 run 的事實原樣帶出（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；ff01 | 例外 | 手造 view，status 為 `running` | 呼叫 `failures.summarize(view)` | 回傳 None（不是空字典） | 自動：`platform/tests/test_failures.py` |
| TC-002 | 作法 1；ff01 | 例外 | 手造 view，status 為 `succeeded` | 呼叫 `summarize` | 回傳 None | 自動：`test_failures.py` |
| TC-003 | 作法 2 failed_tasks；ff02；維護者原話 2 | 功能 | 手造 failed view，failed_tasks 只有一筆：`name="NFCORE_AMPLISEQ:AMPLISEQ:DADA2_DENOISING"`、`exit_code=137`、`error_message="Killed"`、`workdir="/work/ab/cdef"` | 呼叫 `summarize` | 結果的 `failed_tasks` 恰一筆，四個鍵（name、exit_code、error_message、workdir）逐鍵與輸入相等，`exit_code` 是整數 137 | 自動：`test_failures.py` |
| TC-004 | 作法 2「沿用排序、不改寫、不截斷」 | 功能 | 手造 failed view，failed_tasks 有 60 筆，名稱與 exit code 混雜、刻意不是字母順序 | 呼叫 `summarize` | 結果 `failed_tasks` 仍是 60 筆，順序與輸入完全相同，沒有被排序、去重或截斷 | 自動：`test_failures.py` |
| TC-005 | 作法 2「沒有就 []」 | 例外 | 手造 failed view，failed_tasks 是空串列（另一案：view 沒有 failed_tasks 這個鍵） | 呼叫 `summarize` | 結果 `failed_tasks == []`（兩種輸入都是），不報錯 | 自動：`test_failures.py` |
| TC-006 | 作法 2 failure_reason；維護者原話 2 | 功能 | 手造 failed view，`failure_reason="Process `X` terminated with an error exit status (137)"` | 呼叫 `summarize` | 結果 `failure_reason` 與輸入字串完全相同（不縮寫、不改寫） | 自動：`test_failures.py` |
| TC-007 | 作法 2「可為 None」 | 例外 | 手造 failed view，沒有 `failure_reason` 鍵 | 呼叫 `summarize` | 結果 `failure_reason` 為 None，不報錯 | 自動：`test_failures.py` |
| TC-008 | 作法 2「不改寫」 | 例外 | 手造 failed view，一筆 failed task 沒有 `workdir` 鍵（狀態模組本來就在事件沒帶時省略它） | 呼叫 `summarize` | 結果該筆 task 仍沒有 `workdir` 鍵，沒有被補成 None 或空字串，其餘鍵逐鍵相等 | 自動：`test_failures.py` |
| TC-009 | 作法 2 log；不新增讀日誌功能 | 功能 | 用 `status.get_run(..., detail=True)` 對種好的 failed run 取得真實 view | 呼叫 `summarize(真實 view)` | 結果 `log` 為 None（真實 view 沒有日誌鍵）；結果其他四欄照常有值 | 自動：`test_failures.py` |

## User Story 2 — Seqera 的狀態字與兩個動作（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 作法 2 status_seqera | 功能 | 手造 view，status `failed`，沒有 `cancel_requested_at` | 呼叫 `summarize` | `status_seqera == "failed"` | 自動：`test_failures.py` |
| TC-011 | 作法 2；ff03 | 功能 | 手造 view，status `lost`，沒有 `cancel_requested_at` | 呼叫 `summarize` | `status_seqera == "unknown"`（不是 failed、不是 lost） | 自動：`test_failures.py` |
| TC-012 | 作法 2；ff04 | 功能 | 手造 view，status `failed`，有 `cancel_requested_at` | 呼叫 `summarize` | `status_seqera == "cancelled"` | 自動：`test_failures.py` |
| TC-013 | 作法 2（cancelled 優先於 unknown） | 功能 | 手造 view，status `lost`，有 `cancel_requested_at` | 呼叫 `summarize` | `status_seqera == "cancelled"` | 自動：`test_failures.py` |
| TC-014 | 作法 2 actions；ff05 | 功能 | 手造 failed view，`tasks.succeeded=3`、`cached=0` | 呼叫 `summarize` | `actions == ["resume","relaunch"]`（順序也相同） | 自動：`test_failures.py` |
| TC-015 | 作法 2 actions；ff06 | 功能 | 手造 failed view，`tasks.succeeded=0`、`cached=0` | 呼叫 `summarize` | `actions == ["relaunch"]` | 自動：`test_failures.py` |
| TC-016 | 作法 2「succeeded + cached」 | 功能 | 手造 failed view，`succeeded=0`、`cached=2` | 呼叫 `summarize` | `actions == ["resume","relaunch"]`（快取也算可沿用） | 自動：`test_failures.py` |
| TC-017 | 作法 2 actions（規則不分 failed／lost） | 功能 | 手造 lost view，`succeeded=0`、`cached=0` | 呼叫 `summarize` | `actions == ["relaunch"]`，`status_seqera == "unknown"` | 自動：`test_failures.py` |
| TC-018 | 作法 2「固定五鍵」；ff07 | 功能 | TC-003、TC-011、TC-015 的三種 view | 各呼叫 `summarize` | 每個結果的鍵集合恰為 `{status_seqera, failed_tasks, failure_reason, log, actions}`，不多不少 | 自動：`test_failures.py` |
| TC-019 | ff07 | 功能 | 同 TC-018 的三種 view | 各呼叫 `summarize` | 每個結果的 `actions` 都是 `{resume, relaunch}` 的子集，且沒有重複項 | 自動：`test_failures.py` |
| TC-020 | 維護者原話 3（制式化、不產生句子） | 功能 | 同 TC-018 的三種 view，且 failed_tasks／failure_reason 用可辨識的字串 | 呼叫 `summarize`，把結果裡所有字串值收集起來 | 每個字串值不是「輸入 view 裡原有的字串」，就是固定詞彙 `failed／unknown／cancelled／resume／relaunch`；沒有任何平台自己組出來的句子 | 自動：`test_failures.py` |

## User Story 3 — 動作層出口與擁有者規則（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 作法 3；ff08 | 功能 | 用既有 store harness 為使用者 A 種一筆 failed run，含一個 `exit_code=137` 的失敗 task | 以 A 的身分呼叫 `actions.get_run` | 回傳含 `failure`，`failure["failed_tasks"][0]["exit_code"] == 137`，`failure["status_seqera"] == "failed"` | 自動：`test_failures.py` |
| TC-022 | 作法 3；ff08 | 功能 | 同 TC-021 | 以 A 的身分呼叫 `actions.list_runs` | 該筆那一列的 `failure["failed_tasks"][0]["exit_code"] == 137` | 自動：`test_failures.py` |
| TC-023 | 作法 3「其他列 failure 為 None」 | 例外 | 種一筆 running、一筆 succeeded、一筆 failed，同一使用者 | 呼叫 `actions.list_runs` | running 與 succeeded 兩列的 `failure` 是 None；failed 那列有內容 | 自動：`test_failures.py` |
| TC-024 | 作法 3「get_run 加 failure 欄位」 | 例外 | 種一筆 running（另一案 succeeded）run | 呼叫 `actions.get_run` | 回傳有 `failure` 這個鍵，值為 None | 自動：`test_failures.py` |
| TC-025 | 作法 3「列裡除了 failure 不多帶欄位」 | 功能 | 種數筆不同狀態的 run | 比對 `actions.list_runs` 每一列與 `status.list_runs` 同一列的鍵 | 動作層每列的鍵集合 ＝ 狀態模組該列的鍵集合 ＋ 恰好一個 `failure`；且原有欄位的值不變 | 自動：`test_failures.py` |
| TC-026 | 作法 3（lost 也補完整 view） | 功能 | 種一筆 run，最後訊息時間比 lost 門檻舊（用既有的假時鐘／`ABF_PLATFORM_CLOCK_OFFSET`），使其狀態為 `lost` | 呼叫 `actions.list_runs` | 該列 `status` 仍是 `lost`，`failure["status_seqera"] == "unknown"`，`failure["actions"]` 符合 TC-014／015 規則 | 自動：`test_failures.py` |
| TC-027 | 作法 3 get_run＋cancel_requested_at | 功能 | 種一筆 failed run，並讓它有一筆已確認的取消紀錄（`jobs.cancel_requested_at` 回傳時間） | 呼叫 `actions.get_run` | `failure["status_seqera"] == "cancelled"`；原有的 `cancel_requested_at` 欄位與 `status`（仍是 `failed`）不變 | 自動：`test_failures.py` |
| TC-028 | 作法 3 list_runs 補 `jobs.cancel_requested_at` | 功能 | 同 TC-027 | 呼叫 `actions.list_runs` | 該列 `failure["status_seqera"] == "cancelled"`；該列 `status` 仍是 `failed` | 自動：`test_failures.py` |
| TC-029 | ff08「另一位使用者看不到」；擁有者規則（讀） | 例外 | 使用者 A 的 failed run；使用者 B 另有身分 | 以 B 的身分呼叫 `actions.get_run` 查 A 的 run id | 回傳 `found == False` 與既有的「找不到這個 run」文字；回應中沒有 `failure`、沒有 137、沒有 A 的 task 名稱 | 自動：`test_failures.py` |
| TC-030 | ff08；擁有者規則（讀） | 例外 | 同 TC-029 | 以 B 的身分呼叫 `actions.list_runs` | 清單中沒有 A 的 run；整個回應序列化後不含 A 的 task 名稱或 137 | 自動：`test_failures.py` |
| TC-031 | 作法 3「get_run 直接用自己組好的 view」 | 功能 | 種一筆 failed run | 比對加欄位前後 `actions.get_run` 的原有欄位（processes、failed_tasks、failure_reason、cancel_requested_at、tasks…） | 原有欄位與值都不變；只多了 `failure` | 自動：`test_failures.py` |
| TC-032 | 作法 7「不需要 migration」；舊資料 | 例外 | 用 `test_followup3.py` 同款方法造一個舊版索引：failed run、沒有 `failure_reason` 欄、failed_tasks 沒有 `workdir` 欄 | 呼叫 `actions.get_run` 與 `actions.list_runs` | 不報錯；`failure["failure_reason"]` 為 None；`failed_tasks` 的 exit_code／error_message 照舊帶出 | 自動：`test_failures.py` |
| TC-033 | 既有行為不退步 | 例外 | 一個不存在的 run id | 呼叫 `actions.get_run` | 回傳 `found == False` 與既有 `RUN_NOT_FOUND_TEXT` 文字，沒有堆疊或內部路徑 | 自動：`test_failures.py` |

## User Story 4 — 不在範圍：不分類、不挑動作、不送出、不讀日誌（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 不做：不判斷資源碼；維護者原話 1 | 不在範圍 | 兩個手造 failed view，只有 exit code 不同（137 與 1），其餘（tasks 計數、cancel 狀態）完全相同 | 各呼叫 `summarize` | 兩個結果的 `status_seqera`、`actions`、鍵集合完全相同；唯一差別是帶出來的 exit_code 值 | 自動：`test_failures.py` |
| TC-035 | 不做：不比對錯誤訊息樣式 | 不在範圍 | 三個手造 failed view，只有 error_message 不同：`"Killed"`、`"Exceeded memory limit"`、`"No space left on device"` | 各呼叫 `summarize` | 三個結果的 `status_seqera`、`actions`、鍵集合完全相同；訊息只出現在原樣帶出的欄位裡 | 自動：`test_failures.py` |
| TC-036 | 維護者原話 1、2（不分四類、不自己定義）；不做：不分類原因 | 不在範圍 | 任一 failed 結果 | 檢查結果的鍵（含巢狀）名稱 | 沒有任何分類或原因判斷類的鍵（至少檢查 `cause`、`category`、`class`、`kind`、`type`、`reason_class`、`evidence`），也沒有 `failure_reason` 以外的原因欄位 | 自動：`test_failures.py` |
| TC-037 | 不做：不產生建議句、不替使用者挑動作 | 不在範圍 | 手造 failed view，有可沿用的 task（兩個動作都可用） | 呼叫 `summarize` | 結果沒有 `advice`、`hint`、`suggestion`、`recommended`、`default` 之類的鍵；`actions` 是單純兩個字串的串列，沒有標示哪個被建議 | 自動：`test_failures.py` |
| TC-038 | 不做：不自動送出續跑或重跑；ff09 | 不在範圍 | `platform/abf_platform/failures.py` 原始碼 | 用 `ast` 檢查它的 import | 不 import `jobs`、`confirm`、`receiver`（含 `from .. import jobs` 與 `from ..jobs import …` 兩種寫法） | 自動：`test_failures.py` |
| TC-039 | 不做：不自動送出；唯讀 | 不在範圍 | 種一筆 failed run，記下索引資料庫與工作狀態檔的內容指紋（`helpers.all_files_digest`） | 呼叫 `actions.get_run` 與 `actions.list_runs` 各數次 | 兩個檔的指紋前後完全相同；沒有新增任何待確認請求、沒有新增任何送出紀錄 | 自動：`test_failures.py` |
| TC-040 | 作法 1「不讀檔、不連網、不寫資料庫」；不做：不呼叫 AI／Jev | 不在範圍 | `failures.py` 原始碼 | 用 `ast` 檢查 import 與呼叫 | 不 import `sqlite3`、`socket`、`subprocess`、`urllib`、`http`、`requests`、`httpx`、`os` 以外的檔案存取模組；沒有呼叫 `open(`；不 import `status`／`actions`／`mcp_server`（保持純函式） | 自動：`test_failures.py` |
| TC-041 | 不做：不改 `status.py`；作法 3 | 不在範圍 | 種一筆 failed run | 呼叫 `status.get_run(..., detail=True)` 與 `status.list_runs` | 兩者回傳的 view／列都沒有 `failure` 鍵（`failure` 只由動作層加上） | 自動：`test_failures.py` |
| TC-042 | 作法 2 log「不新增讀日誌的功能」 | 不在範圍 | `failures.py` 原始碼；一筆 failed run | 檢查原始碼；呼叫 `actions.get_run` | `failures.py` 沒有出現 `read_task_log`、`.command.err` 等讀日誌的字樣；結果 `log` 沒有任何日誌內文 | 自動：`test_failures.py` |
| TC-043 | 不做：不改網頁、不改 `receiver.py`、不改 `status.py` | 不在範圍 | `web.py`、`web_board.py`、`receiver.py`、`status.py` 原始碼 | 檢查是否引用 `failures` 模組或把 `"failure"` 當鍵使用 | 四個檔都沒有引用 `failures`，也沒有 `"failure"` 這個鍵字面值（閱卷者另以 git diff 確認這四檔沒有變動） | 自動：`test_failures.py` |

## 憲法與安全網（含 backend 專長守則）

| 編號 | 憲法條目／專長守則 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 對等性（動作清單與動作層函式一一對應）；作法 4 | 功能 | 不修改 `test_web_parity.py` | 執行 `platform/tests/test_web_parity.py` | 全綠；`actions` 的公開名稱沒有多出 `summarize`（`failures` 是模組，不計入）；該測試檔本身沒被改動 | 自動：`test_web_parity.py` |
| TC-045 | TC-070（每個原始檔寫明為何不用現成工具） | 功能 | 新檔 `failures.py`、`test_failures.py` | 執行 `platform/tests/test_scope.py` 的 TC-070 | 通過；兩個新檔前 40 行內各有 `# Nothing existing: <理由>`，理由 ≥15 字且不是 `IN_REPO_PHRASES` 開頭 | 自動：`test_scope.py` |
| TC-046 | TC-061（原始碼不出現 ssh／station／tw ） | 功能 | 新檔 `failures.py`（含註解與 docstring） | 執行 `test_scope.py` 的 TC-061 與 TC-051 | 通過；`failures.py` 任何一行都沒有 `ssh`、`station`、`tw `、`sbatch`、`scancel` | 自動：`test_scope.py` |
| TC-047 | 專長守則：密鑰不得出現在回應 | 例外 | 種一筆 failed run，平台有發出的使用者 token／密碼（既有 harness 的 token） | 呼叫 `actions.get_run`、`actions.list_runs`，把回應序列化成文字 | 文字中不含任何已發出的 token 或密碼字串；回應只含 view 裡原有的資料 | 自動：`test_failures.py` |
| TC-048 | 專長守則：資料結構變動要有 migration，或計畫寫明不需要；作法 7 | 功能 | 種一筆 failed run，記下索引資料庫與工作狀態檔所有表與欄位（`sqlite_master`） | 呼叫 `actions.get_run`／`list_runs` 後再比對 | 表與欄位完全相同；此次 diff 沒有新增 migration 或 schema 變更；計畫已寫「不需要 migration」 | 自動：`test_failures.py` |
| TC-049 | 作法 6（PLATFORM.md 小節） | 功能 | `docs/PLATFORM.md` | 檢查是否有「Failed runs」小節 | 小節存在，且寫明四件事：各欄位意義、`lost` 對應 Seqera 的 `unknown`、`resume`／`relaunch` 對應 Seqera 的 Resume／Relaunch、本平台續跑還不能改資源與參數（缺口 `resume-edit-params`）；小節內沒有 `tw `、`station`、`ssh` 字樣 | 自動：`test_failures.py`（閱卷者另讀內容） |
| TC-050 | 作法 6（缺口記進帳本） | 功能 | `specs/failure-seqera/ledger.md` | 檢查「欠」一節 | 有一條 `resume-edit-params`，說明續跑還不能改資源與參數 | 自動：`test_failures.py`（閱卷者另讀內容） |
| TC-051 | 計畫「失敗先行測試」ff01–ff09 | 功能 | `platform/tests/test_failures.py` | 列出測試函式名稱並執行該檔 | 九個函式 `test_ff01…` 至 `test_ff09…` 都存在且全綠；沒有 skip／xfail | 自動：`test_failures.py` |
| TC-052 | 完成標準「全套綠」 | 功能 | 實作完成的 HEAD | 在 WSL 執行 `tests/run_all.sh` | 全綠；唯一允許的紅是 `tests/init_workspace_test.sh` 的「site side with no run area known」，且該檔未被修改；其他既有測試檔沒有被放寬或刪除 | 自動：`tests/run_all.sh` |
