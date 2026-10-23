# 測試案例：SU 費率檔跟著安裝包走；補強 estimate-su-mcp 的四條鬆測試（su-followups）

**規格**：`specs/su-followups/plan.md`（本任務沒有獨立 spec.md，計畫含目標、範圍、失敗先行測試與「不做」，即規格；計畫的「維護者原話」寫明「無原話」，所以沒有逐字範例，TC 全部由計畫的目標與失敗先行測試推出）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（回「不知道」並說原因、不崩）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「安裝包」＝用 `pip` 裝起來的 wheel（abf-platform 的安裝檔）；「checkout」＝直接用 git 取下來的原始碼資料夾；「費率檔」＝`configs/sites/su_rates.json`（各站點的 SU 係數與每 SU 的台幣價）。下面所有「安裝包情境」都是照 `platform/tests/test_station_packaging.py` 的做法：把 repo 複製、`pip wheel` 建 wheel、解開，再用 `python -I`（隔離模式，不吃目前資料夾與環境變數裡的模組）從一個沒有 repo 的資料夾匯入。

## US1 — 費率檔跟著安裝包走（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SF-01 | 目標 1；失敗先行測試 1 | 功能 | 安裝包情境：wheel 解開後，從一個沒有 repo 的資料夾、用 `-I` 獨立 Python 匯入 `abf_platform.su` | 呼叫 `su.load_rates()` | 回傳的不是 None；`sites.nano4.twd_per_su` 存在，且 `nstc`、`academic`、`industry` 三個數字與 repo 裡 `configs/sites/su_rates.json` 的 nano4 完全相同 | 自動：`platform/tests/test_su_packaged.py::test_rates_found_from_the_packaged_plugin` |
| TC-SF-02 | 目標 1（先找安裝包裡 `abf_station/plugin/configs/sites/su_rates.json`） | 功能 | 同 TC-SF-01 的安裝包情境 | 讀 `su.RATES_PATH` | 它指到解開的 wheel 裡 `abf_station/plugin/configs/sites/su_rates.json` 那一份（路徑結尾與位置都對），且那個檔存在 | 自動 |
| TC-SF-03 | 目標 1（「pip 安裝的平台讀得到 SU 費率」，讀到之後真的拿來算） | 功能 | 同 TC-SF-01 的安裝包情境 | 用 `su.load_rates()` 的結果對 nano4 站點算兩個 task：2 個 cpu 跑 1800000 毫秒（半小時）與 1 個 cpu 跑 3600000 毫秒（一小時），兩個的分區都是 `ngs92G` | `su` 是 2.0、`twd_nstc` 是 0.2、`twd_academic` 是 0.4、`twd.industry` 是 0.74；`unknown_reasons` 是空的（與 checkout 裡 `test_get_run_has_su_for_a_nano4_run` 同一組數字） | 自動 |
| TC-SF-04 | 目標 1（「先找安裝包……沒有再退回 repo 路徑」＝安裝包優先） | 功能 | 一個環境同時有兩份費率檔：安裝包裡的真檔，與放在 repo 路徑（`su.py` 上兩層的 `configs/sites/`）、內容故意不同的另一份（例如 nano4 的 `nstc` 改成 999） | `-I` 匯入 `abf_platform.su`，呼叫 `su.load_rates()` | 讀到的是安裝包裡那份（nano4 的 `nstc` 不是 999） | 自動 |
| TC-SF-05 | 目標 1（沒有就退回 repo 路徑）；失敗先行測試 2 | 功能 | 在 checkout 底下（`platform/abf_station/` 底下沒有 `plugin/` 資料夾）直接匯入 `abf_platform.su` | 看 `su.RATES_PATH` 並呼叫 `su.load_rates()` | `RATES_PATH` 等於 repo 根的 `configs/sites/su_rates.json`；`load_rates()` 不是 None，且有 `taiwania3`、`nchc`、`nano4` 三個站點 | 自動：`platform/tests/test_su_packaged.py::test_checkout_still_uses_repo_configs` |
| TC-SF-06 | 目標 1（兩處都找不到時，沿用既有「讀不到＝不知道」的規則）；專長守則（錯誤訊息不露內部路徑） | 例外 | 安裝包情境，但把解開的 wheel 裡 `abf_station/plugin/configs/` 整個刪掉，而且 repo 路徑也沒有費率檔 | `-I` 匯入 `abf_platform.su`；呼叫 `su.load_rates()`；再用它的結果呼叫 `su.su_of_tasks` | 匯入不丟例外；`load_rates()` 回 None；`su_of_tasks` 回 `su` 為 None，`unknown_reasons` 含「費率檔讀不到 (the rates file cannot be read)」；每一條原因字串都不含檔案路徑（沒有資料夾分隔符號、沒有 `su_rates.json` 這個檔名、沒有那個暫存資料夾的路徑） | 自動 |
| TC-SF-07 | 目標 1（既有的測試靠改 `su.RATES_PATH` 模擬「費率檔壞了」，改路徑尋找方式不能讓它們失效） | 功能 | 既有的 `test_unreadable_rates_file_gives_null_site`（TC-030）與 `test_suSite_with_unreadable_rates_file`（TC-050） | 一個字都不改，跑這兩條 | 都通過（`RATES_PATH` 仍是模組上的名字，`load_rates()` 每次呼叫時才讀它） | 自動：`platform/tests/test_su_in_get_run.py` |

## US2 — 補強 #171 閱卷指出的四條鬆測試（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SF-10 | 目標 2 TC-014 | 功能 | 一個 nano4 的 run（兩個 task，同 TC-010：預期 2.0 SU），platform.db 裡有它的 launch 與 `suSite: nano4` 的 CE | 在同一個行程裡，經 MCP 伺服器真的呼叫 `get_run` 工具（用 `test_actions_layer.py` 既有的 `server.call_tool("get_run", …)` 方式，不是只列出工具清單） | 回傳裡有 `su`，`su.su` 是 2.0，`twd_nstc` 0.2、`twd_academic` 0.4、`site` 是 `nano4`；整個 `su` 內容與直接呼叫 `actions.get_run` 的 `su` 完全相同 | 自動：`platform/tests/test_su_in_get_run.py` |
| TC-SF-11 | 目標 2 TC-083（TC-020 這一種） | 例外 | 已結束、成功數大於 0、`task_usage` 完全沒有列、沒有 launch 紀錄的舊 run | 問 `get_run`，取 `su.unknown_reasons` | 清單不是空的；其中**每一條**都不含：這次測試用的暫存資料夾路徑、`.db` 或 `.json` 檔名、`SELECT`／`task_usage`／`sqlite` 等 SQL 字樣、`Traceback`、`token`（不分大小寫） | 自動 |
| TC-SF-12 | 目標 2 TC-083（TC-022 這一種） | 例外 | 沒有 `task_usage` 表的舊 index | 問 `get_run`，取 `su.unknown_reasons` | 同 TC-SF-11：清單不空，每一條都乾淨 | 自動 |
| TC-SF-13 | 目標 2 TC-083（TC-025 這一種） | 例外 | 還在跑（`running`）的 run，已有幾列用量 | 問 `get_run`，取 `su.unknown_reasons` | 同 TC-SF-11：清單不空，每一條都乾淨 | 自動 |
| TC-SF-14 | 目標 2 TC-083（TC-027 這一種） | 例外 | 已結束、成功數 3 但 `task_usage` 只有 2 列的 run | 問 `get_run`，取 `su.unknown_reasons` | 同 TC-SF-11：清單不空，每一條都乾淨 | 自動 |
| TC-SF-15 | 目標 2 TC-083（TC-030 這一種） | 例外 | 費率檔讀不到（把 `su.RATES_PATH` 指到不存在的檔），已結束且有用量列的 run | 問 `get_run`，取 `su.unknown_reasons` | 同 TC-SF-11：清單不空，每一條都乾淨（特別是不把那個不存在的檔案路徑印出來） | 自動 |
| TC-SF-16 | 目標 2 TC-073 | 例外 | 用 `rebuild.py` 的 `rebuild()` 從一個有 `.nextflow/history`、log 與 trace 檔（至少一個 COMPLETED task，history 標為正常結束）的 launch 資料夾真的重建出一個 run；platform.db 讓呼叫者擁有這個 run | 問 `get_run` | 找得到這個 run（`found` 不是 false）；`su.su`、`twd_nstc`、`twd_academic` 都是 null（不是 0）；`unknown_reasons` 恰好是 TC-020 那一句：「這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 …」（重建的 run 完全沒有用量列）；這個 run 是 `rebuild()` 建出來的，不是手工塞進 index 的 | 自動 |
| TC-SF-17 | 目標 2 TC-048（platform.db 不存在） | 例外 | index 裡有一個已結束、用量列是 `ct56` 分區（4 個 cpu、2 小時）的 run；platform.db 的路徑指到一個不存在的檔 | 呼叫 `actions.estimate_su`（不指定 site、不帶 caller），讓它自己走 `site_of_run` 的判斷 | 用預設站點 `taiwania3` 算：`su` 是 8、`twd_nstc` 是 0.64、沒有 `twd` 鍵；不丟例外 | 自動 |
| TC-SF-18 | 目標 2 TC-048（platform.db 打不開） | 例外 | 同 TC-SF-17，但 platform.db 是一個內容不是資料庫的檔（`not a database at all` 重複寫入） | 呼叫 `actions.estimate_su`（不指定 site、不帶 caller） | 同 TC-SF-17：預設站點 `taiwania3`，`su` 8、`twd_nstc` 0.64、沒有 `twd` 鍵；不丟例外 | 自動 |
| TC-SF-19 | 失敗先行測試（第一、二條新測試要先紅） | 功能 | 完成後的 `specs/su-followups/ledger.md` | 驗收者讀 ledger | 對 `test_rates_found_from_the_packaged_plugin` 與 `test_checkout_still_uses_repo_configs` 各有一段，寫明：在舊的 `RATES_PATH`（或等同的破壞）下哪個測試是紅的、紅在哪個斷言，以及改完後轉綠 | 手動：驗收者讀 ledger，必要時在 base 上重跑該測試確認是紅 |
| TC-SF-20 | 失敗先行測試（四條補強各自先證明「弄壞被測的那一段會紅」） | 功能 | 同 TC-SF-19 | 驗收者讀 ledger | TC-014、TC-083、TC-073、TC-048 四條補強各有一段，寫明弄壞了哪一段（例如：讓 MCP 的 `get_run` 不帶 `su`；讓某個 unknown 原因含路徑；讓重建的 run 不再回 unknown；讓 `site_of_run` 不回預設站點）、哪個測試因此變紅；而不是只寫「已驗證」 | 手動：驗收者讀 ledger，並隨機挑一條在程式上重做一次破壞，確認測試真的紅 |
| TC-SF-21 | 驗收者規則：不准弱化既有測試（四條補強只能更嚴） | 功能 | 這次變更對 `platform/tests/test_su_in_get_run.py` 的差異 | 驗收者對照 base 比較 | 既有測試沒有被刪、跳過或放寬任何斷言；被補強的四條（`test_mcp_get_run_is_the_same_action`、`test_get_run_su_is_null_with_reason_for_an_old_run` 與另四種 unknown、`test_a_run_without_usage_rows_stays_unknown`、`test_site_of_run_without_a_platform_db_is_the_default`）斷言只增不減；其餘測試一個字不動 | 手動：驗收者比對 diff |

## US3 — 計畫明講這次不做的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SF-30 | 不做：不改計費公式 | 不在範圍 | 既有 `platform/tests/test_estimate_su.py` 與 `test_su_in_get_run.py` 裡的數字案例（nano4 兩個 task 算出 2.0 SU、0.2／0.4／0.74 元；taiwania3 的 4 cpu × 2 小時算出 8） | 不改數字，全部跑 | 全部通過；`su_of_tasks`、`_factor_of`、`MS_PER_HOUR` 的內容沒有因這個任務而改 | 自動：`platform/tests/test_estimate_su.py`、`platform/tests/test_su_in_get_run.py` |
| TC-SF-31 | 不做：不改 get_run 形狀 | 不在範圍 | 既有 `test_get_run_has_su_for_a_nano4_run`、`test_default_site_run_has_no_twd_key`、`test_tool_list_unchanged` | 不改一個字，跑 | 全部通過：`su` 的鍵仍是 `su`、`twd_nstc`、`twd_academic`、`unknown_reasons`、`site`（nano4 另有 `twd`）；MCP 工具仍是 12 個、沒有 `estimate_su` | 自動 |
| TC-SF-32 | 不做：不改 receiver | 不在範圍 | 既有接收器測試（`test_receiver_keeps_cpus_realtime_queue_of_finished_tasks` 等 TC-001 至 TC-007） | 不改一個字，跑 | 全部通過；接收器的程式檔不在這次的 diff 裡 | 自動：`platform/tests/test_su_in_get_run.py`；接收器程式檔不在 diff 另由 TC-SF-33 確認 |
| TC-SF-33 | 計畫「範圍：檔案」（只准動四個檔）；不做：不改 `rebuild.py`（TC-SF-16 靠它不變） | 不在範圍 | 這次變更對 base 的差異（`git diff <base>...HEAD`） | 驗收者列出動過的檔案 | 只有 `platform/abf_platform/su.py`、`platform/tests/test_su_in_get_run.py`、`platform/tests/test_su_packaged.py`、`specs/su-followups/ledger.md`（`plan.md` 是 `/supervise` 複製進來的，不算）；`rebuild.py`、`mcp_server.py`、`actions/__init__.py`、`store.py`、`setup.py`、`test-case*.md` 都沒動 | 手動：驗收者比對 diff |
| TC-SF-34 | 裁決 1：不需要 migration（驗證理由成立） | 不在範圍 | 這次變更對 base 的差異 | 驗收者看資料結構相關檔 | `store.py` 的 `SCHEMA` 沒變、沒有新增表或欄位、沒有 migration 檔；`su.py` 只多了「找費率檔的位置」，沒有任何寫入（`INSERT`／`UPDATE`／`CREATE`）的新語句 | 手動：驗收者比對 diff |

## 憲法與安全網

這個變更碰到：憲法原則 IV（數字要有證據、缺口要明寫：費率來自檔案、找不到就說讀不到，不猜）、backend 專長守則（對等性、跨使用者、唯讀不寫入、錯誤訊息不露路徑與 token、migration）、工作流程規則（新檔檔首標頭、完成標準全套綠）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-SF-40 | 專長守則：對等性（動作清單與動作層函式一一對應） | 功能 | 既有 `platform/tests/test_actions_layer.py` 與 `platform/tests/test_web_parity.py` | 不改一個字，跑 | 全部通過；這次沒有新增任何動作、MCP 工具或網頁路由 | 自動 |
| TC-SF-41 | 專長守則：跨使用者（讀） | 例外 | 使用者 A 的 run，已結束且有完整用量列；使用者 B 的身分 | B 問 A 的 run 的 `get_run`（既有 `test_another_users_run_has_no_su`，一個字不改） | 與現在一樣是「找不到」的形狀，沒有 `su` 鍵，看不到 A 的任何數字 | 自動 |
| TC-SF-42 | 專長守則：唯讀不寫入 | 功能 | 既有 `test_old_index_without_the_table_reads_as_unknown`（TC-082：問 `get_run` 前後 index 檔的位元組完全相同、沒有偷建表） | 不改一個字，跑 | 通過 | 自動 |
| TC-SF-43 | 工作流程規則：新檔檔首與路徑 | 功能 | 新增的 `platform/tests/test_su_packaged.py` | 跑 `platform/tests/test_scope.py` 與 `tests/no_hardcoded_paths.sh` | 新檔前 40 行內有 `# Nothing existing: <理由，≥15 字>`；新測試沒有 `/work/<真實帳號>/` 形式的路徑 | 自動：`platform/tests/test_scope.py`、`tests/no_hardcoded_paths.sh` |
| TC-SF-44 | 工作流程規則：完成標準「全套綠」 | 功能 | 完成後的 HEAD | 在 WSL 跑全套 `tests/run_all.sh` | 全綠；且 `executor-status` 是 `GREEN <HEAD sha>`、工作樹乾淨 | 自動：`tests/run_all.sh` |
