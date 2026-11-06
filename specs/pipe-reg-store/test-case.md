# 測試案例：管線登記紀錄表與狀態機（動作層，先不接檢查與測試）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
No spec.md exists for this task: the plan (with its 2026-11-05 rulings) is the requirement source.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：無獨立 spec.md，以 `specs/pipe-reg-store/plan.md`（含「裁決」與「裁決（自動補，2026-11-05）」）為準　**總覽**：`test-case-overview.md`

名詞（一句話）：「動作層」＝網頁、指令、聊天共用的那一組函式；「登記紀錄」＝表 `pipeline_registrations` 裡的一列（運算環境＋管線＋版本）；「舊資料」＝運算環境設定裡原有的 `sitePipelines` 清單；「確認管道」＝人按「是」的途徑（終端機、MCP 表單、確認頁）。

測試用夾具：既有 `w` 夾具、兩位使用者的 token（下稱「使用者甲」「使用者乙」）；slurm 環境＝nano4 形狀；雲端環境＝googlebatch。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

維護者原話對應（2026-11-04）：
- 「『新增管線』在 nano4 與雲端伺服器的概念我希望都一樣……登記就是從 nf-core 裡面選所有的 pipeline」→ TC-001、TC-003、TC-059
- 「後面經過安裝、test sample 跑過等等流程之後才顯示登記成功」→ TC-056、TC-057（本片不會有任何項目顯示為已登記）
- 「我要已安裝的管線都是有經過你使用內建測試資料測試過的，這邊只是額外顯示讓使用者做額外測試」→ TC-051、TC-056（nano4 既有 4 筆只顯示為「待測試」，不算已登記）
- 表單三欄「運算環境、管線、版本」→ TC-001（三個欄位就是提出登記的全部輸入）
- ADR 0006「每個寫入都經人工確認；未確認不改變資料」→ TC-023～TC-026

## 一、提出登記與紀錄內容（計畫「作法・函式」「資料表」「source」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 `test_propose_creates_checking_row`；原話 1、表單三欄 | 功能 | 使用者甲有一個 slurm 環境，登記表是空的 | 甲以人工確認提出 `ce=該環境`、`pipeline="nf-core/rnaseq"`、`revision="3.26.0"` | 回 `ok` 為真；甲列出該環境的清單恰好一筆，`state=="checking"`、`source=="site-module"`，三個欄位與輸入相同 | 自動：`platform/tests/test_pipeline_registrations.py` |
| TC-002 | 計畫「函式」list 每筆欄位 | 功能 | 同 TC-001 做完 | 甲列出清單 | 每筆都帶 `compute_env`、`pipeline`、`revision`、`source`、`state`、`reason`、`failed_step`、`test_run`、`tested_at`、`updated_at` 這十個欄位 | 自動 |
| TC-003 | 計畫 `test_propose_on_cloud_env_is_remote`；原話 1（雲端與 nano4 同一組狀態） | 功能 | 甲有一個 googlebatch 環境 | 甲以人工確認提出 `nf-core/rnaseq` `3.26.0` | 清單一筆，`source=="remote"`，`state=="checking"`（與 slurm 環境起始狀態相同） | 自動 |
| TC-004 | 計畫 `test_duplicate_propose_is_not_doubled` | 功能 | 甲已提出過同一組（環境、管線、版本），目前非 removed | 甲再提出一次同一組 | 回 `{"ok": True, "changed": False, "state": "checking"}`；表內該組仍只有一列 | 自動 |
| TC-005 | 計畫 `test_removed_then_proposed_again_returns_to_checking` | 功能 | 甲提出後又移除了同一組（目前 removed） | 甲再提出同一組 | 回 `ok` 為真；清單出現該組且 `state=="checking"`；表內該組仍只有一列（不新增第二列） | 自動 |
| TC-006 | 計畫「PITFALLS 第 55 條」（三者比對） | 功能 | 甲的同一環境 | 甲提出 `nf-core/rnaseq` `3.26.0` 與 `nf-core/rnaseq` `3.25.0` | 清單兩筆，各自版本正確，互不覆蓋 | 自動 |
| TC-007 | 計畫「PITFALLS 第 55 條」（唯一鍵含運算環境） | 功能 | 甲有兩個運算環境 A、B | 甲對 A、B 各提出同一組 `nf-core/rnaseq` `3.26.0` | 表內兩列、各自 `compute_env` 為 A、B；列 A 的清單只有 A 那筆，列 B 的清單只有 B 那筆 | 自動 |
| TC-008 | 裁決 2（表裡有列即不再當舊資料） | 功能 | 甲的 slurm 環境 `sitePipelines` 已有 `nf-core/rnaseq` `3.26.0`，登記表為空 | 甲以人工確認對同一組提出登記 | 清單中該組恰好一筆（不重複），`state=="checking"`，不是舊資料（`legacy` 不為真） | 自動 |
| TC-009 | 計畫 `test_table_is_created_on_first_use_and_old_db_still_opens`（migration TC） | 功能 | 一個舊的平台狀態資料庫，內沒有 `pipeline_registrations` 表 | 在其上先列清單，再以人工確認提出一筆 | 列清單回 `ok` 且 `items` 為空；提出成功；既有的 `compute_envs`、`jobs` 等表與資料都還在、可讀 | 自動 |

## 二、名稱與版本驗證（計畫「名稱與版本驗證」、裁決 5）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 計畫 `test_bad_name_or_revision_names_the_field`；裁決 5 | 例外 | 甲有一個 slurm 環境；已人工確認 | 提出 `pipeline="nf-core/A B"`，版本 `3.26.0` | 回 `ok` 為假、`field=="pipeline"`；訊息以「管線名稱格式不合」開頭（沿用既有句）；表內沒有新增列 | 自動 |
| TC-011 | 同上 | 例外 | 同上 | 提出 `pipeline="../x"` | 回 `ok` 為假、`field=="pipeline"`，訊息同 TC-010；表不變 | 自動 |
| TC-012 | 裁決 5（空或非字串） | 例外 | 同上 | 提出 `pipeline` 為空字串；另提出 `pipeline` 為數字 | 兩次都回 `ok` 為假、`field=="pipeline"`、訊息為「pipeline 必須填寫 (pipeline is required)」；表不變 | 自動 |
| TC-013 | 計畫 `test_bad_name_or_revision_names_the_field`（空版本） | 例外 | 同上 | 提出 `pipeline="nf-core/rnaseq"`、`revision=""` | 回 `ok` 為假、`field=="revision"`、訊息為「revision 必須填寫 (revision is required)」；表不變 | 自動 |
| TC-014 | 裁決 5（壞版本） | 例外 | 同上 | 分別提出版本 `main`、`1` | 兩次都回 `ok` 為假、`field=="revision"`、訊息中點名 revision；表不變 | 自動 |
| TC-015 | 裁決 5（壞版本） | 例外 | 同上 | 分別提出版本 `v1.`、`1.2.3 `（尾端有空白） | 兩次都回 `ok` 為假、`field=="revision"`、訊息中點名 revision；表不變 | 自動 |
| TC-016 | 裁決 5（壞版本） | 例外 | 同上 | 提出 39 位十六進位字串當版本 | 回 `ok` 為假、`field=="revision"`；表不變 | 自動 |
| TC-017 | 裁決 5（好版本） | 功能 | 同上，每次用不同管線或確認每次獨立 | 分別提出版本 `3.26.0`、`v2.1`、40 位小寫十六進位字串 | 三次都回 `ok` 為真，清單可見對應版本 | 自動 |
| TC-018 | 裁決 5（`ce` 欄位） | 例外 | 已人工確認 | 提出 `ce` 為空字串；另提出 `ce` 不是字串 | 回 `ok` 為假、`field=="ce"`；表不變 | 自動 |
| TC-019 | 裁決 5（驗證順序） | 例外 | 甲有 slurm 環境 | 提出時管線與版本都不合法（`nf-core/A B`、`main`） | 回的 `field` 是 `"pipeline"`（管線先於版本） | 自動 |
| TC-020 | 裁決 5（順序：ce 先於管線）；裁決 4 | 例外 | 甲 | 提出一個不存在的環境名，且管線也不合法 | 回 `{"ok": False, "field": None, "message": "找不到所選的運算環境 (compute environment not found)"}`（環境找不到優先） | 自動 |
| TC-021 | 計畫「名稱與版本驗證」「直接引用該常數、不複製」 | 功能 | 讀 `platform/abf_platform/actions/registrations.py` | 檢查版本與管線名稱的判斷來源 | 版本判斷引用 `compute_envs._REVISION`、管線名稱引用既有 `_SP_NAME`；新檔裡沒有另一份相同的正規式字面；測試中把該常數換成寬鬆規則時，行為隨之改變 | 自動 |
| TC-022 | 計畫「錯誤訊息白話、雙語」 | 例外 | 觸發 TC-010～TC-020 的各種拒絕 | 讀回應的 `message` | 每則都是「中文 (english)」格式，說明發生什麼事與怎麼處理；不含堆疊、SQL、檔案路徑 | 自動 |

## 三、確認管道（計畫「函式」「失敗先行測試」；ADR 0006）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 計畫 `test_unconfirmed_propose_and_remove_change_nothing`（提出） | 例外 | 甲有 slurm 環境；記下表的列數 | 呼叫提出，`confirmed_by=None` | 丟出「沒有人工確認管道」的拒絕（`JobRefused`）；表的列數與呼叫前相同 | 自動 |
| TC-024 | 同上（移除） | 例外 | 甲已有一筆 `checking` 的紀錄；記下列數 | 呼叫移除，`confirmed_by=None` | 丟出同樣的拒絕；列數不變；該筆仍是 `checking`、清單仍看得到 | 自動 |
| TC-025 | 既有 `_require_human` 的規則（只認三個人工管道） | 例外 | 同上 | 提出與移除各一次，`confirmed_by` 給一個假字串（如 `"alice"`） | 都被拒絕、表不變 | 自動 |
| TC-026 | 裁決 3、5（`_require_human` 先行） | 例外 | 甲 | 以 `confirmed_by=None` 且輸入不合法（壞管線、不存在的紀錄）呼叫提出與移除 | 一律丟出人工確認拒絕，而不是回驗證錯誤或「找不到」 | 自動 |

## 四、範圍與不在範圍（計畫「不做」「範圍：檔案」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 不做 1：排檢查 | 不在範圍 | 甲；記下 `jobs` 表列數 | 以人工確認提出一筆，再移除 | `jobs` 表列數不變（沒有排任何檢查工作）；`_start_check(env, row)` 存在，呼叫回 `None` | 自動 |
| TC-028 | 不做 1：寫 `sitePipelines`；計畫「remove 本片不碰 sitePipelines」 | 不在範圍 | 甲的 slurm 環境 `sitePipelines` 有 4 筆；記下整份設定 | 提出一筆新的、再移除它 | 該環境的整份設定（含 `sitePipelines`）與操作前逐字相同 | 自動 |
| TC-029 | 範圍：檔案（只准改這些）；不做 3、4（沒有 MCP、指令列、網頁、不改既有 register/remove） | 不在範圍 | 實作完成 | 執行 `git diff --stat origin/v3...HEAD` | 只列出：`platform/abf_platform/actions/registrations.py`、`platform/abf_platform/actions/__init__.py`、`platform/tests/test_pipeline_registrations.py`、`platform/tests/test_actions_layer.py`、`platform/tests/test_owner_guard.py`、`platform/tests/test_web_parity.py`（僅在需要時）、`docs/TESTING.md`，以及 `specs/pipe-reg-store/` 下的計畫與 ledger；沒有 `compute_envs.py`、`store.py`、`abf_station/`、`web*.py`、`mcp_server.py`、`cli.py`、`jobs.py` | 手動：`docs/TESTING.md`（本任務新增步驟 a） |
| TC-030 | 不做 4：不改既有 `register_site_pipeline`／`remove_site_pipeline`；計畫「本片不得改」的測試 | 不在範圍 | 實作完成 | 跑 `test_web_settings_register.py`、`test_settings_pick_installed.py`、`test_station_envs.py`（含 NANO4 `sitePipelines` 段） | 全綠，且這三個檔案在本分支沒有任何改動 | 自動 |
| TC-031 | 計畫「環境事實：jobs 工作種類不新增」 | 不在範圍 | 甲；用完所有新函式 | 讀 `jobs` 表的種類限制 | 仍是原本十種，沒有新增種類 | 自動 |

## 五、擁有者規則（跨使用者；計畫「函式」「裁決 4」、專長守則）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 計畫 `test_second_user_cannot_read_or_write`（讀）；裁決 4 | 例外 | 甲有環境 E 與其中一筆紀錄；乙有自己的 token | 乙以 `ce=E` 列清單；另以一個完全不存在的環境名列清單 | 兩次都回 `{"ok": False, "field": None, "message": "找不到所選的運算環境 (compute environment not found)"}`，且兩個回應逐字相等（不透露環境存在） | 自動 |
| TC-033 | 裁決 4（`ce=None`） | 例外 | 同上 | 乙以 `ce=None` 列清單 | 看不到甲的任何紀錄（含甲環境的舊資料） | 自動 |
| TC-034 | 計畫 `test_second_user_cannot_read_or_write`（寫：提出） | 例外 | 同上；記下表列數 | 乙以人工確認、對甲的環境 E 提出登記 | 回「找不到所選的運算環境」；表的列數不變 | 自動 |
| TC-035 | 同上（寫：移除） | 例外 | 同上 | 乙以人工確認、對甲的那筆紀錄移除 | 回「找不到所選的運算環境」；甲的那筆仍在、狀態不變 | 自動 |
| TC-036 | 計畫「全部依 caller 篩擁有者」 | 例外 | 同上 | 乙對環境 E 呼叫 `list_registered_pipelines` | 回「找不到所選的運算環境」，與不存在的環境名回應相同 | 自動 |
| TC-037 | 同上，檔案以使用者過濾 | 例外 | 甲的 slurm 環境有舊資料 `sitePipelines` | 乙列清單（`ce=None`），再以甲的環境名列清單 | 舊資料項目不會出現在乙的任何回應裡 | 自動 |
| TC-038 | 計畫「依 caller 篩擁有者」 | 功能 | 甲、乙各有自己的環境，各提出一筆 | 兩人各自列清單 | 甲只看到甲的那筆、乙只看到乙的那筆 | 自動 |

## 六、動作清單對等性與既有測試（計畫「允許的斷言變動」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 計畫「對等性：新函式名出現在動作清單測試」；專長守則對等性 | 功能 | 實作完成 | 跑 `platform/tests/test_actions_layer.py` | 全綠；新的四個函式名（`list_pipeline_registrations`、`propose_pipeline_registration`、`remove_pipeline_registration`、`list_registered_pipelines`）出現在該檔對應名單（寫入者依確認管道歸類）；測試同時列舉兩邊，缺一邊就失敗 | 自動：`platform/tests/test_actions_layer.py` |
| TC-040 | 計畫「允許的斷言變動」test_owner_guard | 功能 | 實作完成 | 跑 `platform/tests/test_owner_guard.py` | 全綠；四個新函式各有一句擁有者說明 | 自動：`platform/tests/test_owner_guard.py` |
| TC-041 | 計畫「只准加入新函式名，不准刪、放寬」；裁決 1(b)、6 | 不在範圍 | 實作完成 | 執行 `git diff origin/v3...HEAD` 於 `test_actions_layer.py`、`test_owner_guard.py`、`test_web_parity.py` | 這三個檔案只有新增行，沒有被刪除或修改的行 | 手動：`docs/TESTING.md`（本任務新增步驟 b） |
| TC-042 | 計畫「允許的斷言變動」test_web_parity；裁決 6 | 功能 | 實作完成 | 跑 `platform/tests/test_web_parity.py` | 全綠；若該檔要求每個動作有網頁入口，新函式以該檔既有的暫列方式列出並註明 `pipe-reg-settings-ui` 接上；若無要求則該檔未被改動 | 自動：`platform/tests/test_web_parity.py` |
| TC-043 | 計畫「完成標準」 | 功能 | 實作完成 | 在 WSL 跑 `tests/run_all.sh` | 全綠（已知環境紅依 dev-plans README）；新測試檔在改前為紅、改後為綠 | 自動：`tests/run_all.sh` |

## 七、移除登記（裁決 3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 計畫「函式」remove | 功能 | 甲有一筆 `checking` 的紀錄 | 甲以人工確認移除它 | 回 `ok` 為真；清單不再出現該筆；表中該列仍在、`stage` 為 `removed`（列數不變） | 自動 |
| TC-045 | 裁決 3：`test_remove_unknown_registration_is_refused` | 例外 | 甲的環境，表裡沒有 `nf-core/rnaseq` `3.26.0` | 甲以人工確認移除這一組 | 回 `{"ok": False, "field": None, "message": "找不到此登記紀錄 (registration not found)"}`；表不變 | 自動 |
| TC-046 | 裁決 3：`test_remove_legacy_only_is_refused` | 例外 | 甲的環境 `sitePipelines` 有 `nf-core/rnaseq` `3.26.0`，表裡沒有 | 甲以人工確認移除這一組 | 回 TC-045 同樣的拒絕；表不變；環境設定的 `sitePipelines` 不變 | 自動 |
| TC-047 | 裁決 3：`test_remove_twice_is_noop` | 功能 | 甲有一筆已 `removed` 的紀錄 | 甲再移除一次 | 回 `{"ok": True, "changed": False, "state": "removed"}`；表不變 | 自動 |
| TC-048 | 裁決 3（環境找不到） | 例外 | 甲 | 以人工確認、對不存在的環境名移除 | 回「找不到所選的運算環境 (compute environment not found)」 | 自動 |
| TC-049 | 計畫「PITFALLS 第 55 條」 | 功能 | 甲的環境 A、B 各有同一組 `nf-core/rnaseq` `3.26.0` | 甲移除 A 的那筆 | B 的那筆仍在、狀態不變；A 的清單不再出現它 | 自動 |
| TC-050 | 裁決 2：`test_removed_row_suppresses_legacy_entry` | 功能 | 甲的環境 `sitePipelines` 有 `nf-core/rnaseq` `3.26.0`；甲先提出該組再移除它 | 甲列清單 | 該組不在清單中（不會以舊資料再冒出來）；其他三筆舊資料仍在；環境的 `sitePipelines` 不變 | 自動 |

## 八、清單與舊資料合併（計畫「函式」list／list_registered、「對外狀態」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 計畫 `test_legacy_site_pipelines_show_as_awaiting_test`；原話 2 | 功能 | 甲的 nano4 形狀環境，`sitePipelines` 有 4 筆（ampliseq 2.18.0、rnaseq 3.26.0、sarek 3.9.0、scrnaseq 4.2.0），登記表為空 | 甲對該環境列清單 | 回 4 筆，每筆 `state=="awaiting_test"`、`source=="site-module"`、`legacy` 為真，管線與版本與設定一一相同 | 自動 |
| TC-052 | 同上（「表沒有新增任何行」） | 功能 | 同 TC-051 | 列清單前後比對表的列數 | 兩次都是 0 列（只讀合併，不寫表） | 自動 |
| TC-053 | 計畫「removed 不回傳」 | 功能 | 甲有一筆 removed 與一筆 checking | 列清單 | 只看到 checking 那筆 | 自動 |
| TC-054 | 計畫「函式」list 的回傳形狀 | 功能 | 甲的環境沒有紀錄也沒有 `sitePipelines` | 列清單 | 回 `{"ok": True, "items": []}` | 自動 |
| TC-055 | 計畫 `test_registered_list_excludes_legacy_and_checking`（形狀） | 功能 | 甲的環境有 `checking` 紀錄 | 呼叫 `list_registered_pipelines` | 回 `ok` 為真，`items` 為空 | 自動 |
| TC-056 | 計畫 `test_registered_list_excludes_legacy_and_checking`；原話 1、2 | 功能 | 甲的環境有 4 筆舊資料與 1 筆 `checking` | 呼叫 `list_registered_pipelines`；另列完整清單 | 已登記清單為空；完整清單裡沒有任何項目的 `state` 是 `registered` | 自動 |
| TC-057 | 不做 2：推導已登記；計畫「testing 原樣回傳」 | 不在範圍 | 直接在表中放入 `stage` 為 `awaiting_test`、`testing`、`failed` 的列 | 呼叫 `list_registered_pipelines` | 仍為空（本片不推導已登記） | 自動 |
| TC-058 | 計畫「對外狀態 `_state(row, run_status)`」 | 功能 | 表中有 `checking`、`preparing`、`awaiting_test`、`testing`、`failed` 各一列 | 對各列呼叫 `_state(row, None)`；並列清單 | 回傳值等於該列的 `stage`；清單中的 `state` 同為該值 | 自動 |
| TC-059 | 計畫「函式」list（`ce=None`）；原話 1 | 功能 | 甲有 slurm 環境與 googlebatch 環境，各提出一筆 | 甲以 `ce=None` 列清單 | 兩環境的紀錄都在，各帶自己的 `compute_env` 與 `source` | 自動 |
| TC-060 | 計畫「函式」list（`ce=`） | 功能 | 同 TC-059 | 甲以 `ce=slurm 環境` 列清單 | 只有該環境的紀錄 | 自動 |

## 九、資料表（計畫「資料表」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-061 | 計畫欄位：`UNIQUE (owner, compute_env, pipeline, revision)` | 例外 | 表已建立，有一列 | 直接再插入同樣的 (owner, compute_env, pipeline, revision) | 資料庫拒絕（完整性錯誤） | 自動 |
| TC-062 | 計畫欄位：`source` 限制 | 例外 | 表已建立 | 直接插入 `source` 為 `bogus` 的列；並確認 `site-module`、`site-fetch`、`remote` 皆可插入 | `bogus` 被拒絕；三個合法值被接受 | 自動 |
| TC-063 | 計畫欄位：`stage` 限制 | 例外 | 同上 | 直接插入 `stage` 為 `registered`（及其他不在清單的值） | 被拒絕；`checking`、`preparing`、`awaiting_test`、`testing`、`failed`、`removed` 皆可插入 | 自動 |
| TC-064 | 計畫欄位：`failed_step` 限制 | 例外 | 同上 | 直接插入 `failed_step` 為 `bogus`；另插入 NULL、`check`、`prepare`、`test` | `bogus` 被拒絕；其餘被接受 | 自動 |
| TC-065 | 計畫「表名不得用 pipelines／pipeline_versions／pipeline_validations」 | 功能 | 用過新函式的狀態資料庫 | 列出資料庫的表 | 有 `pipeline_registrations`；組合管線既有的三張表結構與資料不受影響；`store.STATE_SCHEMA` 內容未改（`store.py` 無改動） | 自動 |
| TC-066 | 計畫「完成標準」ledger；「不需要 migration」理由 | 功能 | 實作完成 | 驗收者讀 `specs/pipe-reg-store/ledger.md` | 有：新測試改前的紅輸出；「不需要 migration」的理由（新表首次使用時建立、不改既有表、舊 `sitePipelines` 讀時合併不搬資料）；未確認前後表列數比對 | 手動：驗收者讀 ledger（完成標準，不屬 `docs/TESTING.md` 步驟；見總覽疑問 2） |

## 憲法與安全網

<!-- Touches: the rule that every write goes through a person's channel (constitution lines 32-48, Safety Net "nothing else submits"), owner-only data, and no secrets in responses. -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-067 | 只有人工確認後才寫入（唯讀的動作不得寫） | 功能 | 甲的環境有舊資料與紀錄；記下所有表的列數 | 呼叫 `list_pipeline_registrations`、`list_registered_pipelines` 各數次 | 所有表的列數與內容不變 | 自動 |
| TC-068 | 「沒有別的路徑會送出工作」（constitution 第 32-48 行） | 功能 | 記下 `jobs` 與確認紀錄的列數 | 做完提出、重複提出、移除、重新提出 | 沒有新增任何工作或確認紀錄；沒有任何送出行為 | 自動 |
| TC-069 | 專長守則：日誌與回應不含密鑰；錯誤不露內部 | 例外 | 使用者甲、乙的 token 已知 | 跑完上述各拒絕情境，收集所有回應與例外訊息 | 其中不含任何 token 字串、不含 `Traceback`、SQL 字句或檔案系統路徑 | 自動 |
