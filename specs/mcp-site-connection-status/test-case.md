# 測試案例：MCP 看得到站台連線狀態、錯誤訊息註明 agent、get_run 的 SU 不再洗版

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
沒有 spec.md：依計畫「自動補」裁決第 4 點，以 plan.md 的作法 (1)(2)(3)、完成標準、不做 取代 FR；
維護者原話拆成案例 (a)(b)(c) 對應 User Story 1–3。
-->

**規格**：`specs/mcp-site-connection-status/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

維護者原話：「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」
- 案例 (a)：list_agents／list_compute_envs 事前可見連線狀態 → User Story 1
- 案例 (b)：連線沒開時錯誤訊息可直接照做、不會開錯機器 → User Story 2
- 案例 (c)：get_run 在 nano4 給出可讀的 SU 或明確的 unknown → User Story 3

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、資料怪異時，系統怎麼反應（顯示未知、不拼進訊息、不放行）。
- **不在範圍**：計畫「不做」的事；測試確認它真的沒做。

名詞：「站台連線」＝人在桌機 WSL 輸入 OTP 開好的那條通往 nano4 的 SSH 連線通道（ControlMaster）。「agent」＝桌機上替平台做事的程式（例如 `desktop`、`desktop-gcb`）。「CE」＝計算環境。「SU」＝計算點數。程式碼與測試一律用 `<site_user>`，不寫真實帳號。

## User Story 1 — 呼叫 run_outputs 之前就看得到站台連線狀態（案例 a，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法(1) FACT_TEXT／clean_facts | 功能 | agent 回報的 facts 裡有 `site_link` | 分別放入 `open`、`closed`、`unknown` 交給 clean_facts | 三個值都原樣保留 | 自動：`platform/tests/test_site_connection_status.py::test_clean_facts_site_link_only_three_values` |
| TC-002 | 作法(1) clean_facts | 例外 | 同上 | 放入 `maybe`、數字 `123` 這類不是三值之一的內容 | 該欄變成 None，不會被當成 open | 自動：同上測試 |
| TC-003 | 案例 (a)；作法(1) agents.view | 功能 | agent `desktop` 在 hello 帶 `site_link: closed` | 呼叫 `list_agents` | `desktop` 那一項的 `site_link` 是 `closed` | 自動：`test_list_agents_reports_closed_and_open` |
| TC-004 | 案例 (a) | 功能 | 兩個 agent（`desktop`、`desktop-gcb`）各自 hello，一個帶 `closed`、一個帶 `open` | 呼叫 `list_agents` | 兩個 agent 各自列出自己的狀態，沒有互相串到 | 自動：同上測試 |
| TC-005 | 作法(1)：舊 agent 沒帶 → unknown | 例外 | agent 的 facts 完全沒有 `site_link`（舊版 agent） | 呼叫 `list_agents` | 該 agent 的 `site_link` 是 `unknown`（不是 open、不是缺欄位） | 自動：`test_list_agents_reports_site_link_unknown_for_old_agent` |
| TC-006 | 作法(1)：過久視為 unknown | 例外 | agent 最後一次回報 `open`，但距離上次聯絡已遠超離線門檻（`offline_after`，也遠超 3 次心跳） | 呼叫 `list_agents` | 該 agent 的 `site_link` 是 `unknown`，不是舊的 `open` | 自動：`test_stale_site_link_becomes_unknown` |
| TC-007 | 作法(1)：標明「截至 site_link_at，agent 自報」 | 功能 | agent hello 帶 `closed` 與 `site_link_at` | 呼叫 `list_agents` | 該項同時帶 `site_link_at`，且連線欄有「agent 自報／截至該時間」的標示 | 自動：`test_site_connection_status.py`（list_agents 連線欄標示） |
| TC-008 | 案例 (a)；作法(1) compute_envs | 功能 | nano4 的 CE 其 `agent` 欄是 `desktop`，`desktop` 回報 `closed` | 呼叫 `list_compute_envs` | 該 CE 項 `site_connection.state == "closed"` | 自動：`test_list_compute_envs_attaches_site_connection_by_ce_agent` |
| TC-009 | 作法(1)：`{state, as_of, agent}` | 功能 | 同 TC-008，另一個 CE 的 agent 回報 `open` | 呼叫 `list_compute_envs` | 該 CE 的 `site_connection` 含 `state`（`open`）、`as_of`、`agent`（該 CE 的 agent 名） | 自動：同上測試 |
| TC-010 | 作法(1)：找不到 agent → unknown | 例外 | 某 CE 的 `agent` 欄指向一個不存在的 agent | 呼叫 `list_compute_envs` | 該 CE 的 `site_connection.state == "unknown"` | 自動：同上測試 |
| TC-011 | 完成標準：不 enqueue 任何 job | 功能 | 假資料：agent 自報 closed，記下 platform.db 的 `jobs` 表列數 | 呼叫 `list_agents` 與 `list_compute_envs` | 呼叫後 `jobs` 表列數不變（沒有新增任何 job），且 CE 照樣顯示 closed | 自動：`test_listing_connection_is_read_only` |
| TC-012 | 作法(1)：純讀取、不寫庫 | 功能 | 記下 `agents.last_seen_at` | 呼叫 `list_agents` 與 `list_compute_envs` | `agents.last_seen_at` 前後相同（查詢不更新任何 agent 紀錄） | 自動：同上測試 |
| TC-013 | 作法(1)：agent 項多兩個鍵 | 功能 | 既有 `test_actions_layer.py` 的 agent 項鍵集合 | 執行更新後的 `test_actions_layer.py` | agent 項只比原來多 `site_link`、`site_link_at` 兩個鍵，其餘鍵與其他斷言不變 | 自動：`platform/tests/test_actions_layer.py`（BASELINE、list_agents 測試、排除項） |
| TC-014 | 作法(1)：文件與 description 要寫明 | 功能 | MCP 工具說明（tools.json） | 讀 `list_agents`、`list_compute_envs` 的 description | 說明連線狀態是 agent 自報、`open` 只代表控制通道在、不保證下一個連線不卡 | 自動：`platform/tests/mcp/test_mcp_contract_tools.py` 與 `snapshots/tools.json` |
| TC-015 | 作法(1) own_facts | 功能 | agent 設定 `reach: ssh`，假的 `--check-master` 回傳 1（沒開） | 呼叫 `own_facts` | `site_link == "closed"` | 自動：`platform/tests/test_station_site_link.py` |
| TC-016 | 作法(1) own_facts | 功能 | `reach: ssh`，假的 `--check-master` 回傳 0（開著） | 呼叫 `own_facts` | `site_link == "open"` | 自動：同上 |
| TC-017 | 作法(1)：逾時 → unknown | 例外 | `reach: ssh`，假的 `--check-master` 逾時沒回 | 呼叫 `own_facts` | `site_link == "unknown"`，絕不是 `open` | 自動：同上 |
| TC-018 | 作法(1)：出錯 → unknown | 例外 | `reach: ssh`，假的 `--check-master` 以 0／1 以外的結果結束，或執行時丟出錯誤 | 呼叫 `own_facts` | `site_link == "unknown"`，絕不是 `open` | 自動：同上 |
| TC-019 | 作法(1)／PITFALLS 16e、57：不用 `--check-reach` | 功能 | `reach: ssh` 的 closed、open、逾時三種情境 | 呼叫 `own_facts` | 全程沒有呼叫過 `--check-reach` | 自動：同上 |
| TC-020 | 自動補裁決 1：local → open | 功能 | agent 設定 `reach: local` | 呼叫 `own_facts` | `site_link == "open"`，且沒有呼叫 `--check-master` 也沒有呼叫 `--check-reach` | 自動：同上 |
| TC-021 | 自動補裁決 1：none → unknown | 例外 | agent 設定 `reach: none` | 呼叫 `own_facts` | `site_link == "unknown"`（沒有可連的站台，不能說 open），且沒有呼叫 `--check-master` 也沒有呼叫 `--check-reach` | 自動：同上 |
| TC-022 | 作法(1)：site_link_at | 功能 | 任一 reach | 呼叫 `own_facts` | 帶 `site_link_at`，內容是可解析的 ISO 時間 | 自動：同上 |
| TC-023 | 作法(1)：檢查失敗不影響 hello | 例外 | 連線檢查丟出錯誤 | agent 送 hello | hello 照常送出，只是 `site_link` 是 `unknown`；agent 沒有因此停擺 | 自動：同上 |
| TC-024 | 作法(1)：Beat 每次重算 facts | 功能 | 第一次心跳時連線檢查回「開」，之後改回「沒開」 | agent 連送兩次心跳 | 第二次心跳帶的是 `closed`（不是沿用第一次的 `open`） | 自動：同上 |
| TC-025 | 作法(1)：檢查限時 3 秒 | 功能 | `reach: ssh` | 呼叫 `own_facts`，檢視對 `--check-master` 設的時限 | 時限是 3 秒 | 自動：同上 |
| TC-026 | 作法(1) on_site.sh `--check-master` | 功能 | 假 ssh（`ON_SITE_SSH_BIN`）回報控制通道存在 | 執行 `scripts/on_site.sh --check-master` | 退出碼 0 | 自動：`tests/on_site_check_master_test.sh` |
| TC-027 | 同上 | 功能 | 假 ssh 回報沒有控制通道 | 執行 `--check-master` | 退出碼 1 | 自動：同上 |
| TC-028 | 同上：不開 session | 功能 | 假 ssh 會記錄收到的所有指令 | 執行 `--check-master`（開著與沒開兩種） | 假 ssh 從未收到 `true` 指令（沒開任何 session）；只做 `-O check` | 自動：同上 |
| TC-029 | 同上：不佔 slot | 功能 | 記下 slot 目錄狀態 | 執行 `--check-master` | 執行前後 slot 沒有被佔用 | 自動：同上 |
| TC-030 | 作法(1)：`reach: local` 回 0 | 功能 | `reach: local` | 執行 `--check-master` | 退出碼 0，且假 ssh 完全沒被呼叫 | 自動：同上 |

## User Story 2 — 連線沒開時，錯誤訊息講明到哪一台機器開（案例 b，優先度 P1）

被追加的句子（計畫作法 (2)）：`Run it in the WSL terminal of the machine running agent "<agent>" (請在執行 agent「<agent>」那台機器的 WSL 終端機執行).`

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 案例 (b)；作法(2) run_outputs | 功能 | 站台斷線；某 run 的 agent 是 `desktop` | 呼叫 `run_outputs` | error 回覆含 `desktop` 與 `WSL` | 自動：`test_run_outputs_error_names_agent` |
| TC-032 | 作法(2)：追加句形式 | 功能 | 同 TC-031 | 呼叫 `run_outputs` | error 以上述追加句結尾，agent 名放進引號與「」內 | 自動：同上測試 |
| TC-033 | 案例 (b)；作法(2) list_site_files | 功能 | 站台斷線；該 run 的 agent 是 `desktop` | 呼叫 `list_site_files` | failure 回覆含 `desktop` 與 `WSL` | 自動：`test_list_site_files_failure_names_agent` |
| TC-034 | 案例 (b)：不會開錯機器 | 功能 | 兩個 agent（`desktop`、`desktop-gcb`）；run 屬於 `desktop-gcb` | 呼叫 `run_outputs` | 訊息點名 `desktop-gcb`，不含 `desktop` 當成要開的機器 | 自動：`test_site_connection_status.py`（兩 agent 區分） |
| TC-035 | 作法(2)：原文保留 | 功能 | 站台斷線 | 呼叫 `run_outputs` | 原訊息本文（含 ControlPath 家目錄路徑）原樣保留，追加句只接在後面 | 自動：同上 |
| TC-036 | 作法(2)：agent 名先過字元限制 | 例外 | run 的 agent 名含空白與引號（例如 `my "box"`） | 呼叫 `run_outputs` 與 `list_site_files` | 追加句整句不出現，agent 名沒有被拼進訊息，原訊息完整保留 | 自動：`test_agent_name_with_odd_chars_not_spliced` |
| TC-037 | 自動補裁決 3 | 例外 | run 沒有 `agent` 欄 | 呼叫 `run_outputs` | 訊息與追加前逐字相同，沒有空的或佔位的 agent 名 | 自動：`test_site_connection_status.py`（無 agent 欄，run_outputs） |
| TC-038 | 自動補裁決 3 | 例外 | CE 沒有 `agent` 欄 | 呼叫 `list_site_files` | 訊息與追加前逐字相同，沒有空的或佔位的 agent 名 | 自動：同上（list_site_files） |
| TC-039 | 作法(2)：只在含 "No open connection to the site" 時追加 | 例外 | 一個不含該句的錯誤（例如路徑被拒） | 呼叫 `run_outputs` | 訊息沒有被追加任何 WSL 句子 | 自動：同上 |
| TC-040 | PITFALLS 58 | 例外 | nano4 連線過期（site_unreachable） | 呼叫 `list_site_files` | 仍然答「站台連不上」，不會變回「路徑被拒」 | 自動：`platform/tests/test_station_realpath_down.py`（不動） |
| TC-041 | 作法(2)：不動釘死句子 | 功能 | 既有釘死連線句子的測試 | 執行 `test_failures.py`、`test_launch_followup.py`、`test_refusal_visibility.py`、`test_station_site_inventory.py`、`test_station_read_run_file.py`、`test_station_e2e.py`、`test_head_nodefail.py`、`test_chat_tools.py`、`test_guidance.py` | 全綠；若有「完全相等」斷言被改成 `startswith`／`in`，ledger 有說明 | 自動：上列既有測試 |

## User Story 3 — get_run 的 SU 不再洗版、站台不再標錯（案例 c，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-042 | 案例 (c)；完成標準 | 功能 | nano4 的 run，125 個 task，分布在 5 個沒有 SU 係數的分區 | 呼叫 `get_run` | 回應的 `unknown_reasons` 不超過 5 行（不超過分區數），每行含分區名與 task 數 | 自動：`test_unknown_reasons_aggregated_by_partition` |
| TC-043 | 作法(3)：格式 | 功能 | 同上 | 檢視其中一行 | 格式是「分區 P 沒有 SU 係數，共 N 個 task（no SU factor for partition P: N tasks）」 | 自動：同上測試 |
| TC-044 | 作法(3)：多分區排序 | 功能 | task 分布在 `zeta`、`alpha`、`mid` 三個無係數分區 | 呼叫 `get_run` | 三分區各一行，依分區名排序（`alpha`、`mid`、`zeta`） | 自動：`test_site_connection_status.py`（多分區排序） |
| TC-045 | 作法(3)：數字正確 | 功能 | 125 個 task 全部無係數 | 呼叫 `get_run` | 各行 N 加總等於無係數 task 數（125） | 自動：`test_unknown_reasons_aggregated_by_partition` |
| TC-046 | 作法(3)：同分區只一行 | 功能 | 所有無係數 task 都在同一分區 | 呼叫 `get_run` | `unknown_reasons` 只有一行 | 自動：`test_site_connection_status.py` |
| TC-047 | 作法(3)／裁決 2：寧可標未知 | 功能 | run 的 CE 存在但沒有 `suSite` | 呼叫 `get_run` | `su.site` 是 `null`，不是 taiwania3 | 自動：`test_su_site_unset_ce_is_not_taiwania3` |
| TC-048 | 作法(3) | 功能 | 同 TC-047 | 檢視 `unknown_reasons` | 剛好一行原因：「計算環境未設定 suSite，無法判定站台（compute environment has no suSite）」 | 自動：同上測試 |
| TC-049 | 作法(3) | 功能 | 同 TC-047 | 檢視 `su.su` | 是 `null`（不用猜的） | 自動：同上測試 |
| TC-050 | 作法(3)：站台取自 CE | 功能 | CE 設 `suSite: nano4`，task 分區是 `ngs62g` | 呼叫 `get_run` | `su.su` 有數值，`su.site == "nano4"` | 自動：`test_su_site_from_ce_suSite_nano4` |
| TC-051 | 作法(3)：不改「未知就 null」 | 例外 | task 分區不在 SU 係數表內 | 呼叫 `get_run` | 總值維持 `null`，沒有猜一個係數 | 自動：`test_unknown_partition_still_null_not_guessed` |
| TC-052 | 作法(3)：任一 task 未知 → 總值 null | 例外 | 一部分 task 在有係數分區（`ngs62g`），一個 task 在無係數分區 | 呼叫 `get_run` | 總值是 `null`，不是只加總已知的 | 自動：`test_site_connection_status.py` |
| TC-053 | 作法(3)：找不到 CE 的舊 run 維持舊行為 | 功能 | run 對應的 CE 已不存在 | 呼叫 `get_run` | 沿用 default_site（既有行為），不報錯 | 自動：`platform/tests/test_estimate_su.py` 或 `test_site_connection_status.py` |

## User Story 4 — 計畫明講這次不做的事（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | 不做：不新增 MCP 工具 | 不在範圍 | 工具快照 | 比對 `tools.json` 的工具名單與數量 | 仍是 22 個，名單與原本相同 | 自動：`platform/tests/mcp/test_mcp_contract_tools.py` |
| TC-055 | 範圍：mcp_server 只改 description | 不在範圍 | 工具快照新舊對照 | 比對各工具的參數結構 | 只有 description 文字變動，沒有任何參數新增或移除 | 自動：`platform/tests/mcp/` 快照測試 |
| TC-056 | 不做：22 工具集合測試不動 | 不在範圍 | 一組釘住 22 工具的既有測試 | 執行 `test_aws_ce`、`test_azure_ce`、`test_gcb_ce`、`test_aws_launch`、`test_azure_launch`、`test_azure_upload`、`test_gcb_launch`、`test_dataset_launch` | 全綠，且這些檔案沒有 diff | 自動：上列既有測試 |
| TC-057 | 不做：查詢時不登入、不等待、不重試、不代輸入 OTP | 不在範圍 | 假 ssh 記錄所有指令；沒有控制通道 | 執行 `--check-master` | 立即退出碼 1，假 ssh 只收到 `-O check`，沒有任何登入、等待或重試 | 自動：`tests/on_site_check_master_test.sh` |
| TC-058 | 不做：不補係數、不改 twd_per_su | 不在範圍 | `configs/sites/su_rates.json` 與 `su.py` 的 diff | 檢視 diff | 沒有新增 taiwania3 或其他站台的係數，沒有改動既有係數數字，`twd_per_su` 沒變 | 自動：`platform/tests/test_estimate_su.py` |
| TC-059 | 不做：圖片／HTML 顯示缺口另開件 | 不在範圍 | `read_run_file` 的既有測試 | 執行 `test_station_read_run_file.py` | 仍只回文字，行為未擴充，測試全綠 | 自動：`platform/tests/test_station_read_run_file.py` |
| TC-060 | 不做：#3、#5、#6 另開件；範圍外檔案不動 | 不在範圍 | 本件的 `git diff --stat` | 對照計畫「範圍：檔案」清單（`docs/TESTING.md` 新段 (a)） | 所有改動檔案都在清單內；筆電 plugin 預設站台、succeeded 卻 failed:2、sarek 跑滿 48 小時這三件沒有任何對應改動 | 手動：`docs/TESTING.md`「mcp-site-connection-status：驗收者檢查三件事」(a) |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-061 | 安全網：平台寫入工具（`launch`、`launch_pipeline`、`cancel`、`resume`、`relaunch`、`forget`）須有人確認 | 功能 | 本件改了 `actions/__init__.py` | 執行 `test_actions_layer.py`（`test_tcb04_*` 到 `test_tcb08_*`）、`test_human_channel.py`、`test_resume_entrypoints.py`、`test_keep_submissions.py` | 全綠；確認流程相關斷言沒有被放寬 | 自動：上列既有測試 |
| TC-062 | 不做：不改憲法、不放寬安全網、不改確認流程 | 不在範圍 | 本件的 diff | 以 `git diff --stat` 看 `.specify/memory/constitution.md`、`hooks/`、確認流程、`cancel` 相關檔 | 以上檔案零 diff，`git diff --stat` 已貼進 ledger | 手動：`docs/TESTING.md` 新段 (b) |
| TC-063 | 憲法第 3 條：不寫個人路徑與真實帳號 | 功能 | 本件所有新增與修改的檔案 | 搜尋真實計畫帳號與個人家目錄路徑 | 程式、測試、文件都只用 `<site_user>` 之類的佔位，找不到真實帳號 | 手動：`docs/TESTING.md` 新段 (a)（驗收者檢查 diff） |
| TC-064 | 憲法第 8 條：PITFALLS 新增一條 | 功能 | `docs/PITFALLS.md` | 讀新增條目 | 有一條新條目，格式含 Symptom／Root cause／Check／Touches，Check 指向本件新測試 | 手動：`docs/TESTING.md` Procedure P2 |
| TC-065 | 憲法第 8 條：先量再斷言 | 功能 | ledger | 讀 ledger | 有「線上 nano4 的 CE 紀錄是否缺 `suSite`」的實測紀錄（結果寫明），且 SU 係數表補了 nano4 的 `ngs*` 分區或明確標未知 | 手動：`docs/TESTING.md` Procedure P2 |
| TC-066 | 憲法第 11 條：on_site.sh 的既有檢查 | 功能 | 本件改了 `scripts/on_site.sh` | 執行 `tests/on_site_test.sh`、`tests/wsl_bridge_test.sh` | 全綠 | 自動：上列測試 |
| TC-067 | PITFALLS 16e、57：不多開 session | 功能 | 同上 | 執行 `tests/on_site_parallel_test.sh`、`tests/reset_master_test.sh`、`tests/preflight_ssh_fold_test.sh` | 全綠；hello 每次心跳沒有多開 session | 自動：上列測試 |
| TC-068 | 計畫「允許更新的既有斷言」 | 功能 | 本件改動的既有測試檔 | 對照 base 比較 | 只動清單內的斷言（BASELINE、list_agents、tools.json 契約測試、`test_estimate_su.py` 的 reasons 文字），沒有放寬、刪除或略過其他斷言 | 手動：`docs/TESTING.md` 新段 (c) |
| TC-069 | 裁決 4：`test_refusal_visibility.py:138` TC-090 | 功能 | 既有斷言 | 執行更新後的 `test_refusal_visibility.py` | 斷言只多放行 `site_link` 欄位，其他斷言原樣 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-070 | 自動補裁決 2：TESTING.md 新段 | 功能 | `docs/TESTING.md` | 讀新增段落 | 有「mcp-site-connection-status：驗收者檢查三件事」，含 (a) 改動檔案在清單內 (b) 憲法與安全網零 diff (c) 既有斷言只照清單更新，並附 PITFALLS 新條目與 nano4 `suSite` 實測的檢查步驟（併入 P2） | 手動：`docs/TESTING.md` |
| TC-071 | 作法(1)：文件寫明 open 的意義 | 功能 | 本件新增或修改的文件（PITFALLS 新條目或 docs） | 讀文件 | 寫明 `site_link: open` 只代表控制通道在，不保證下一個連線不卡 | 手動：`docs/TESTING.md` Procedure P2 |
| TC-072 | 計畫「文件文字」：釘住文件句子的測試 | 功能 | 本件若改了文件 | 執行 `test_onboarding_doc.py`、`test_station_docs.py` | 全綠；只有在改了文件時才動這兩個測試 | 自動：上列既有測試 |
