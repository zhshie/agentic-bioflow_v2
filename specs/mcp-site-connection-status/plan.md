---
id: mcp-site-connection-status
title: MCP 看得到站台連線狀態、錯誤訊息註明 agent、get_run 的 SU 不再洗版
tier: B
kinds: [backend]
risk: L        # 範圍含 platform/abf_station/，依 README 規則自動 L；呼叫者要求 M，見「待決」
lane: platform-mcp
base: v3
---

## 目標
MCP 呼叫端在叫 `run_outputs`／`list_site_files` 之前，就能從 `list_agents`／`list_compute_envs` 看到「這個計算環境的站台連線現在開著沒」；連線沒開時的錯誤訊息講明「到哪一台機器（agent 名稱）的 WSL 開」；`get_run` 的 SU 不再 125 行洗版，`su.site` 取自該 run 的計算環境。
意義：維護者最基本要求是「用 MCP 請 lab-agent 跑完分析並顯示在網頁」；現在 agent 顯示 online 卻在讀結果時才撞牆。

## 維護者原話（verifier 出題用）
> 「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」

對應案例：(a) list_agents／list_compute_envs 事前可見連線狀態；(b) 連線沒開時錯誤訊息可直接照做、不會開錯機器；(c) get_run 在 nano4 給出可讀的 SU 或明確的 unknown。

## 範圍：檔案
- `platform/abf_platform/common.py`（FACT_TEXT 加 `site_link`、`site_link_at`；clean_facts）
- `platform/abf_platform/agents.py`（view 附連線欄）
- `platform/abf_platform/compute_envs.py`（list_all 每個 CE 附 `site_connection`）
- `platform/abf_platform/actions/__init__.py`（list_agents、list_compute_envs、run_outputs、list_site_files、`_su_of_run`）
- `platform/abf_platform/su.py`（彙總 unknown_reasons；site_of_run 不再默默落 taiwania3）
- `platform/abf_platform/mcp_server.py`（只改上述工具的 description 文字，不增減工具）
- `platform/abf_station/launch.py`（own_facts 附連線）、`platform/abf_station/agent.py`（Beat 每次重算 facts，已是 callable，確認即可）
- `scripts/on_site.sh`（新增唯讀模式 `--check-master`）
- `configs/sites/su_rates.json`（只在需要時；nano4 的 `ngs*`、`big-mem*` 在 v3 已有）
- 測試：見下「允許更新的既有斷言」與「失敗先行測試」；新增 `platform/tests/test_site_connection_status.py`、`tests/on_site_check_master_test.sh`
- `docs/PITFALLS.md`（加一條）、`docs/PLATFORM.md`（agent facts 清單，若有列）

## 作法
讀自 origin/v3（工作樹是舊的，不可信）。

**(1) 連線狀態：agent 回報，平台唯讀轉述。** 平台從不呼叫 agent，所以只能由 agent 在 hello／beat 帶 facts。
- `scripts/on_site.sh --check-master`：只做 `master_is_up`（`ssh -O check`，控制通道，不開 session、不佔 slot、不等 OTP、不嘗試登入）；`reach: local` 回 0。退出碼 0 開／1 沒開。不可用現成 `--check-reach`：它會 `acquire_slot` 並實際開一個 `ssh host true` session（上限 15 秒，PITFALLS 16e 說會吃 MaxSessions），不唯讀。WSL 橋接（`bridge_kind`）沿用同一條路。
- `own_facts(ctx)` 加兩個鍵：`site_link` ∈ `open|closed|unknown`（`reach` 為 local/none 時 `open`/`unknown` 依 reach 決定，ssh 時看 `--check-master`；呼叫逾時或出錯 → `unknown`，絕不當 open）、`site_link_at`（ISO 時間）。檢查本身限時 3 秒，失敗不影響 hello。
- `common.FACT_TEXT` 加 `site_link: 8`、`site_link_at: 40`；`clean_facts` 對 `site_link` 只收三個值，其餘 None。
- `agents.view` 新增 `site_link`、`site_link_at`（來自 facts_json；舊 agent 沒帶 → `unknown`）。連線欄標明「截至 site_link_at，agent 自報」，過久（超過 3 次心跳）視為 `unknown`，因為 agent offline 時舊值不可信。
- `compute_envs.list_all`（經 actions.list_compute_envs）每個 CE 附 `site_connection: {state, as_of, agent}`，由該 CE 的 `agent` 欄查 agent 的 facts；找不到 agent → `unknown`。純讀取，不寫庫。
- 不加新 MCP 工具（工具數維持 22，多個測試釘死）。

**(2) 錯誤訊息註明 agent。** 在 actions 層補，不動 `handlers.connect_failure` 與釘死的 REFUSAL 句子（見測試清單）：`run_outputs` 的 error 回覆與 `list_site_files` 的 failure 回覆，若訊息含 "No open connection to the site"，在後面接一句 `Run it in the WSL terminal of the machine running agent "<agent>" (請在執行 agent「<agent>」那台機器的 WSL 終端機執行).`；agent 名取自該 run／CE 的 `agent` 欄。訊息本文中的 ControlPath 家目錄路徑原樣保留（那是那台機器的）。agent 名稱先過 `_NAME` 同樣的字元限制才拼進訊息。

**(3) get_run 的 SU。** v3 已有：`su_rates.json` 的 `sites.nano4`（`ngs*`＝1、`big-mem*`＝7）、CE 的 `suSite: nano4`、`su.site_of_run`。根因推定（待 executor 在 v3 上實測確認，不要先假設）：該 run 的 CE 沒有 `suSite` 或 run 找不到 CE，`site_of_run` 落到 `default_site`＝taiwania3，而 taiwania3 沒有 ngs* 分區 → 全部 unknown、site 標錯。
- `site_of_run`：run 的 CE 存在但沒有 `suSite` → 回 `None`，`_su_of_run` 的 `site` 為 `null`，並加**一行**原因「計算環境未設定 suSite，無法判定站台（compute environment has no suSite）」，不再默默用 default_site。找不到 CE 的舊 run 才維持 default_site（既有行為）。
- `su_of_tasks`：`unknown_reasons` 依分區彙總：同一分區只出一行，格式「分區 P 沒有 SU 係數，共 N 個 task（no SU factor for partition P: N tasks）」；多分區各一行，依分區名排序。`su` 數值規則不變：任一 task 未知 → 總值維持 null，不用猜的。
- 不改 `twd_per_su` 與係數數字；不放寬「未知就 null」的安全網。

## 失敗先行測試
新檔 `platform/tests/test_site_connection_status.py`（先紅）：
1. `test_clean_facts_site_link_only_three_values`：`open|closed|unknown` 保留，其他 → None。
2. `test_list_agents_reports_site_link_unknown_for_old_agent`：facts 無 `site_link` → `unknown`。
3. `test_list_agents_reports_closed_and_open`：兩個 agent 各自 hello 帶 closed／open，`list_agents` 照列。
4. `test_stale_site_link_becomes_unknown`：last_contact 超過 offline_after → `unknown`。
5. `test_list_compute_envs_attaches_site_connection_by_ce_agent`：nano4 CE 的 agent closed → CE 項 `site_connection.state == "closed"`；CE 指向不存在 agent → `unknown`。
6. `test_listing_connection_is_read_only`：呼叫前後 platform.db 的 `jobs` 表列數與 `agents.last_seen_at` 不變，且過程不 enqueue 任何 job。
7. `test_run_outputs_error_names_agent`：站台斷線時 `run_outputs` 的 error 含 agent 名與 "WSL"。
8. `test_list_site_files_failure_names_agent`：同上。
9. `test_agent_name_with_odd_chars_not_spliced`：agent 名含空白／引號 → 訊息不拼入。
10. `test_unknown_reasons_aggregated_by_partition`：125 個 task、5 個無係數分區 → `unknown_reasons` 長度 ≤ 5，每行含分區名與 task 數。
11. `test_su_site_unset_ce_is_not_taiwania3`：CE 無 suSite → `su.site is None`，一行原因，`su.su is None`。
12. `test_su_site_from_ce_suSite_nano4`：CE `suSite: nano4`、分區 `ngs62g` → 有數值、`site == "nano4"`。
13. `test_unknown_partition_still_null_not_guessed`：不在表內分區 → 總值 null。
agent 側：`platform/tests/test_station_site_link.py`：`own_facts` 在 ssh reach 下 `--check-master` 回 1 → `closed`、回 0 → `open`、逾時 → `unknown`，且全程不呼叫 `--check-reach`。
shell：`tests/on_site_check_master_test.sh`：用 `ON_SITE_SSH_BIN` 假 ssh，斷言 `--check-master` 不開 session（假 ssh 沒收到 `true` 指令）、無 master 時退出 1、不佔 slot。

## 允許更新的既有斷言
以下測試釘住會變的常數或句子，只准照新行為更新，不准放寬其他斷言：
- `platform/tests/test_actions_layer.py`：BASELINE（約 36 行）、`list_agents` 測試（203–205 行）、排除項（225 行）——agent 項多兩個鍵。
- `platform/tests/mcp/snapshots/tools.json`（description 變動；工具數仍 22）；`platform/tests/mcp/test_mcp_contract_tools.py`（17、126、155–160 行）；`test_mcp_contract_writes.py`（106、111、138 行）。
- `platform/tests/test_estimate_su.py`：reasons 文字（45、70–71、104–105、164、176、259 行）；工具集合（297 行）。
- 連線句子相關，**預期不動**（因為 agent 名只在 actions 層追加、原句不改），executor 要確認它們仍綠：`test_failures.py:193`、`test_launch_followup.py:23`、`test_refusal_visibility.py:38`、`test_station_realpath_down.py:36/121`、`test_station_site_inventory.py:28`、`test_station_read_run_file.py:30`、`test_station_e2e.py:819/1221`、`test_head_nodefail.py:786`、`test_chat_tools.py:15`、`test_guidance.py:26`。若新追加句造成「完全相等」斷言失敗，改成 `startswith`／`in`，並在 ledger 說明。
- 文件文字：`test_onboarding_doc.py:223`、`test_station_docs.py:25`（提到 `--check-reach`）——只在改了文件時動。
- 22 工具集合測試：`test_aws_ce`、`test_azure_ce`、`test_gcb_ce`、`test_aws_launch`、`test_azure_launch`、`test_azure_upload`、`test_gcb_launch`、`test_dataset_launch`——預期不動；動到就是多加了工具，退回。

## 完成標準（done when）
- 上列新測試全綠；既有測試除「允許更新」清單外不動；完整 `platform/tests` 與 shell 測試綠。
- 用假資料實演：agent 自報 closed 時，`list_compute_envs` 在不 enqueue 任何 job 的情況下顯示 closed。
- `get_run` 對 nano4 125 task 的 run，回應的 `unknown_reasons` 不超過分區數行；`su.site` 不是 taiwania3（除非 CE 真的是）。
- 憲法檔與安全網（`rules`、確認流程、`cancel` 等）零 diff：`git diff --stat` 貼進 ledger。
- `docs/PITFALLS.md` 新增一條（格式：Symptom／Root cause／Check／Touches）。

## 環境事實
- MCP 站台：`https://desktop-7j5l5bj.tail6bf2f5.ts.net/mcp`；兩個 agent：`desktop`、`desktop-gcb`。nano4 的連線是人在桌機 WSL 輸入 OTP 開的 ControlMaster，agent 與平台都不能代開。
- lab-agent 試跑回報（`memory/handoff/2026-11-07-lead-to-lab-mcp-e2e-trial.md`「## 回報」）：#1 連線不可見、#2 訊息未註明機器、#4 SU 洗版與 site 標錯。
- 計畫帳號 `mst109178`；nano4 run 路徑在 `/work/<site_user>/runs/...`（程式碼與測試用 `<site_user>`，不寫真實帳號）。
- 新 `.py` 檔頭要有 `# Nothing existing: …` 一行；`handlers.py` 避免引號包住的 sbatch 樣式。
- `scripts/on_site.sh` 的 `--check-reach` 會佔 slot 並開 session（PITFALLS 16e）；`reach: local` 直接回 0。

### PITFALLS 已查（docs/PITFALLS.md；根目錄無 PITFALLS.md，無 docs/solutions）
- **16e. Too many on_site.sh calls on one master silently hang, not error.**
  Symptom：一 master 上的 on_site.sh 呼叫過多會靜默卡住，`ssh -O check` 與 preflight 的 reach 行仍顯示 OK。Check：`tests/on_site_parallel_test.sh`、`tests/reset_master_test.sh`。→ 本件因此用 `-O check` 而不是 `--check-reach`，且 `site_link: open` 只代表控制通道在，不保證下個 session 不卡；文件與 description 要寫明。
- **58. A failed first ssh step was read as bad input (realpath-site-down).**
  Symptom：nano4 連線過期後 `read_run_file`／`list_site_files` 答「路徑被拒」。Check：`platform/tests/test_station_realpath_down.py`。→ 動 `list_site_files` 錯誤訊息時不得把 site_unreachable 改回 path refused。
- **57. preflight under reach ssh opened 4 sessions**（Check：`tests/preflight_ssh_fold_test.sh`）→ 本件不得讓 hello 每次心跳多開 session；`--check-master` 必須零 session。
- SU（su_rates／suSite）、facts、list_agents：PITFALLS 已查，無相符項。

## 不做
- 不新增 MCP 工具（唯讀連線狀態工具留作後續）。
- 不在查詢時登入、等待或重試連線；不代人輸入 OTP。
- 不改憲法、不放寬安全網、不改確認流程。
- 不處理 lab-agent 回報的 #3（筆電 plugin 預設站台 t3-c4 與 MCP run 不同站）、#5（succeeded 卻 failed:2 的說明）、#6（sarek 跑滿 48 小時）——另開件。
- 不補 taiwania3 或其他站台的 SU 係數；不改 `twd_per_su`。
- 圖片／HTML 顯示在網頁的缺口（read_run_file 只回文字）另開件。

## 待決（給 developer-agent）
1. 風險：agent 側（`platform/abf_station/`）必動才能讓連線狀態可見，依規則是 L，與要求的 M 衝突。替代：只切第一片（平台側 SU＋錯誤訊息＝M），連線狀態改由 abf_station 另件做（L）；但這樣需求 (1) 這輪無法完成。計畫先照 L 寫。
2. CE 無 `suSite` 時 `su.site` 回 null 還是沿用 default_site？計畫採 null＋一行原因。
3. 要不要先在 v3 實機看 nano4 CE 紀錄是否缺 `suSite`（根因推定未驗）。

## 裁決（lead，2026-11-07，回應計畫撰寫者的三點）
1. 風險維持 **L**，不拆件（連線狀態是第一步的核心）；PASS 後跑對抗審，通過前不掛自動合併。
2. CE 沒有 `suSite` 時，`su.site` 回 null——接受（寧可標未知，不可標錯站台）。
3. 先確認線上 nano4 的 CE 紀錄是否缺 `suSite`（已知 nano4 的 config 無 `suSite` 鍵）；若缺，ledger 記錄，並在 SU 係數表補 nano4 的 `ngs*` 分區或明確標未知；`unknown_reasons` 依分區彙總成一行。
4. 與 `mcp-site-keepalive-disconnect-ux` 同改 `on_site.sh`、`mcp_server.py`、`tools.json`、`test_refusal_visibility.py:138`：本件先合併；該 TC-090 斷言由本件修改（放行 site_link 欄位，不得放寬其他斷言）。

## 裁決（自動補，2026-11-07）
依據：repo 的 `scripts/inspect_sides.sh`（reach local → `site.reachable=yes`；reach none → `site.reachable=unknown`，註明 Platform 管理的 CE 沒有 login node）與 `scripts/launch_recheck.sh`（none 無 relay 可檢查）。
1. `own_facts` 的 `site_link`：`reach: local` → 固定 `open`（與 `--check-master` 對 local 回 0 一致）；`reach: none` → 固定 `unknown`（沒有可連的站台，不能說 open；與 inspect_sides 的 none → unknown 一致）。`reach: ssh` 才看 `--check-master`。各加一條 TC（local→open、none→unknown），放入 `platform/tests/test_station_site_link.py`，且兩者都不呼叫 `--check-master`／`--check-reach`。
2. 範圍加入 `docs/TESTING.md`：新增一段「mcp-site-connection-status：驗收者檢查三件事」——(a) 改動檔案都在「範圍：檔案」清單內；(b) 憲法與安全網（rules、確認流程、cancel 等）`git diff --stat` 零 diff；(c) 既有斷言只照「允許更新的既有斷言」清單更新。另附 PITFALLS 新條目與 nano4 CE `suSite` 實測紀錄的檢查步驟（併入 Procedure P2）。
3. run／CE 沒有 `agent` 欄（或 agent 名未過 `_NAME` 字元限制）時：整句不追加，原訊息完整保留，不寫空的或佔位的 agent 名。TC-045 加一句此斷言：無 agent 欄時，訊息與追加前逐字相同。
4. 沒有 spec.md：以本計畫條目（作法 (1)(2)(3)、完成標準、不做）取代 FR；維護者原話拆成案例 (a)(b)(c)，如計畫「維護者原話」段所列，不再改動。
5. 風險等級以 L 為準（lead 裁決已推翻 M）；PASS 後跑對抗審，通過前不掛自動合併。不影響出題。
6. 專長守則：本任務無 [backend] 守則，不需要對應 TC。

## 專長守則（[backend]）

（工作區沒有 `.claude/dev-profiles/[backend].md`；本任務無專長守則。）

## 裁決 (2026-11-08)
test_no_schema_change 失敗原因：分支基底 87107ae9 落後 origin/v3 (fcb26614)，v3 對 store.py 的改動被當成本分支差異。先 `git fetch origin v3` 並把分支 rebase（或 merge）到 origin/v3，再跑全套；不可修改或弱化該測試。aws_ce 偶發失敗重跑即可。

## 修訂（executor 補列，2026-11-08，驗收者 TC-060／TC-068 退回後；待維護者或 developer-agent 認可）
對抗審修正輪做了下列超出原清單的事。executor 無權自行核可範圍，這裡只把事實補進計畫，讓 `git diff --stat` 與計畫對得上；若不認可，要退回對應改動（見每項「退回的代價」）。

**範圍：檔案（追加）**
- `platform/abf_platform/jobs.py`（4 行）：`latest_listing` 多回 `agent` 欄，讓 `run_outputs` 的連線錯誤指到「跑 listing job 的那台」而不是 CE 換 agent 之前的那台。退回的代價：CE 換 agent 後，錯誤訊息會指錯機器（對抗審實跑重現）。
- `platform/abf_station/agent.py`：原清單寫「Beat 每次重算 facts，確認即可」，實際新增 `refresh_facts`（閒置 agent 每次空 poll 後重送 hello，約每 25 秒）。原因：Beat 只在執行 job 時跳，閒置 agent 的 `site_link` 會停在啟動時的值，MCP 看到的狀態就是舊的。已補測試 `test_idle_agent_says_facts_again_after_an_empty_poll`、`test_idle_refresh_failure_is_ignored`（`platform/tests/test_station_site_link.py`）。退回的代價：閒置時連線狀態不更新。
- 行為範圍：`estimate_su`、用量頁／`my_usage`（`_su_of_run`）也改成「CE 沒設 `suSite` 就顯示未知」（`site_of_run(strict=True)`），不只 `get_run`；同一個 run 不可有兩種站台答案。CE 已不存在的舊 run 仍用 default_site（TC-053）。

**允許更新的既有斷言（追加，皆只補輸入或縮減缺口，斷言數值未動）**
- `platform/tests/test_su_in_get_run.py:159`（`test_default_site_run_has_no_twd_key`）：fixture 由「CE 存在但無 `suSite`」改成「CE 不存在」，因為前者的行為依裁決 2 刻意改成未知；`:326-327` 新增 strict 斷言（只加不減）。
- `platform/tests/test_su_usd.py`：`seed` 包一層，Slurm CE 預設帶 `suSite: taiwania3`。
- `platform/tests/test_web_cost.py:76-79`：`seed` 的 Slurm CE 預設帶 `{"suSite": "taiwania3"}`（`test_cost_by_env`、`test_su_usd`、`test_web_cost` 共用輸入）。
- `platform/tests/test_refusal_visibility.py:138`：`_absent("site_link") == []` 改成白名單過濾；裁決 4 已允許，白名單除原預期外還放 `mcp_server.py`、`agent.py`、`launch.py`、`actions`（這些檔案的文字或欄位名含 `site_link`）。
- `platform/tests/mcp/test_mcp_contract_tools.py`：`ASPECT_GAPS` 移除 `('list_agents','when_not')`、`('my_usage','when')` 兩行（縮減已知缺口，不是放寬；stale 檢查會把關）。
