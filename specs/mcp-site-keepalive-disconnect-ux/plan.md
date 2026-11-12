---
id: mcp-site-keepalive-disconnect-ux
title: 站台連線掉線時網頁頂端紅色提示、新 run 被擋並說明恢復方式；開連線指令改長效保活並記錄真實存活時間
tier: B
kinds: backend, ui
risk: M        # 本件不改 platform/abf_station/（agent 側 site_link 由 mcp-site-connection-status 提供）；若 executor 發現必須動 abf_station/ 則升 L 並回報
lane: platform-mcp
serves: S1-CONN
depends: mcp-site-connection-status   # 必須在它合併之後才開工，見「環境事實」的檔案衝突表
base: v3
---

## 目標
站台共用連線（國網 ControlMaster）掉了的時候：①網頁每一頁頂端出現紅色提示，MCP 回覆的訊息明講「連線已掉，請在哪台機器的 WSL 重新登入」；②這時送出新 run 會被擋下並說明怎麼恢復，已經在跑的 run 完全不受影響；③開連線的指令改成長效保活（`ControlPersist=yes`＋`ServerAliveInterval=60`＋`ServerAliveCountMax=10`），並有一支常駐的 WSL 小程式每 10 分鐘把 `ssh -O check` 的結果寫成 log，量出國網真實的存活上限。OTP 仍由人輸入，平台與 agent 不代開。
意義：維護者最基本要求是用 MCP 請 lab-agent 跑完分析並顯示在網頁；現在連線掉了是到讀結果或送出時才撞牆（10-23 曾不到 8 小時就掉），使用者看不到原因也不知道去哪台機器處理。

## 維護者原話（verifier 出題用）
> 「Q3不要只有8hr, 如果可以更久就改，第一步先只做『連線狀態可見＋掉線時明確提示』」

> 「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」

對應案例：
- 「不要只有 8hr，可以更久就改」→ 開連線指令的 `ControlPersist` 不再是 `8h`（改 `yes`），並有 log 可量出實際上限（案例 K1、K2、K3）。
- 「連線狀態可見＋掉線時明確提示」→ 網頁頂端紅條（案例 B1～B4）、MCP／拒絕訊息講明機器與動作（案例 M1～M3）。
- 「最基本的要求」→ 掉線不會讓已在跑的 run 受影響（案例 R1～R2）、掉線被擋後說明恢復方式，恢復後同一申請可重新送出（案例 R3）。

## 範圍：檔案
新增：
- `platform/abf_platform/site_link.py`（檔頭 `# Nothing existing: …` 一行；唯讀 helper：`closed_agents(state_path, user_id, now)`、`down_message(agent)`）
- `scripts/keepalive_log.sh`（WSL 內常駐的記錄迴圈）
- `tests/keepalive_log_test.sh`、`platform/tests/test_site_disconnect_ux.py`

修改：
- `scripts/on_site.sh`（只改 `no_master()` 印的那一行與其說明文字；**不碰** `master_is_up`、`--check-master` 與其他分支）
- `scripts/reset_master.sh`（第 62 行同一條開連線指令與 64–66 行說明）
- `platform/abf_platform/jobs.py`（只在 `enqueue_confirmed` 的 `kind == "launch_nextflow"` 分支、`_target` 之後加一個檢查；不動 `_OPEN_COMMAND*` 與 `valid_open_command`）
- `platform/abf_platform/web.py`（每個請求把「這個人的掉線 agent 清單」放進 context variable，比照 `DEV_MODE`）
- `platform/abf_platform/web_board.py`（`STRINGS` zh／en 新字串、`STYLE` 加一條規則、`_frame` 畫紅條）；`web_devmode.py` 旁不新增檔，context variable 放 `site_link.py`
- `platform/abf_platform/mcp_server.py`（只改 `launch`、`launch_pipeline`、`relaunch`、`resume` 的 description 加一句「站台連線掉線時會被擋」；工具數仍 22）
- 文件：`docs/PLATFORM.md`（171–174 行指令範例與「ControlPersist=8h keeps the connection for the day」、688 行「at most 8 hours」）、`docs/SITE_ADAPTER.md`（約 148–150 行）、`docs/PITFALLS.md`（加一條）
- 既有測試的更新見「允許更新的既有斷言」

## 作法
讀自 origin/v3（工作樹是舊的，不可信）。連線狀態來源是 **mcp-site-connection-status** 已定的事實鍵：agent 在 hello／beat 自報 `site_link` ∈ `open|closed|unknown`、`site_link_at`，`agents.view` 附這兩欄（超過 3 次心跳視為 `unknown`）。本件**只讀它，不重做**；它沒合併就不能開工。

**(1) 判定只認「新鮮的 closed」。** `site_link.closed_agents(state_path, user_id, now)`：回傳該使用者自己的、`agents.view` 給 `site_link == "closed"` 的 agent 名稱（排序）。擁有權規則與 `jobs._target` 相同（116：環境與 agent 必須是呼叫者自己的；沒有 user 的終端機 yes 不過濾，視為全部）。`open`、`unknown`、過期、舊 agent 沒帶欄位——**一律不擋、不顯示紅條**（猜不到就不誤傷）。純讀取，不寫庫、不 enqueue。

**(2) 網頁頂端紅條。** `web.py` 每個請求取得 `closed_agents(...)` 放進 context variable `SITE_DOWN_AGENTS`（預設空，登入頁等為空）。`web_board._frame` 在 `devbar` 之後、`wb` 之前加 `<div class="linkbar" role="alert">…</div>`；沒有掉線時**不輸出任何元素**（避免既有頁面快照多一個空 div）。class 名稱用 `linkbar`，不可用 `devbar`（`test_web_settings_personal.py` 用 `<div class="devbar"` 做計數與移除）。字串（`STRINGS` 兩種語言都加，鍵 `linkbar_down`）：
- zh：`站台連線已掉：請在執行 agent「%s」那台機器的 WSL 終端機重新登入（貼上開連線指令並輸入 OTP）。已在跑的 run 不受影響；新的 run 在恢復前無法送出。`
- en：`The site connection is down. On the machine running agent "%s", log in again in its WSL terminal (paste the connect line, type the one-time code). Runs already going are not affected; new runs cannot be sent until it is back.`
多個 agent 掉線則每個一行。agent 名稱先過與 agent 命名相同的字元限制（見 mcp-site-connection-status 的 `_NAME` 處理）再拼入，並 `esc()`。紅條不含 `ControlPersist` 字樣（`test_refusal_visibility.py` TC-007 禁止 platform 非測試原始碼出現，`jobs.py` 例外）。`STYLE` 加 `.linkbar` 一條規則（顏色沿用 `.devbar` 的紅色變數）；**這會改變 `web_board.STYLE` 的 SHA-256**，見允許更新清單。

**(3) 掉線時新 run 送出被擋。** 在 `jobs.enqueue_confirmed` 的 `launch_nextflow` 分支（`name_problem` 之後、`_insert_job` 之前）：若 `row["agent"]` 在 `closed_agents` 內 → `raise JobRefused(site_link.down_message(agent))`。這是 web 按鈕、MCP 表單 yes、終端機 `abf-platform launch` 共同的單一入口（`confirm.approve` 與 `confirm_launch` 都經過它），`confirm.approve` 會把該申請標為 void 並帶原因，使用者重新呼叫 launch 就能在恢復後重送。
- 訊息：`No open connection to the site (agent "<agent>"). 連線已掉，請在執行 agent「<agent>」那台機器的 WSL 終端機重新登入，再重新送出。已在跑的 run 不受影響 (runs already going are not affected).` 開頭**必須維持** `jobs.SITE_DOWN` 字串 `No open connection to the site`，這樣 `_refusal_of_row`／`web_board` 的既有「站台連線沒開」分類照常運作。
- **只擋 `launch_nextflow`**：`cancel`、`clean_work`、`fetch`、`read_task_log`、`read_run_file`、`list_site_files`、`preflight` 的路徑完全不加檢查（取消與讀 log 在掉線時要仍可試；它們自己遇到斷線會走既有的錯誤訊息，由 mcp-site-connection-status 補機器名）。
- **已在跑的 run 不動**：不改 `launches`、run 狀態、`lost` 判定、Beat 或任何已 enqueue 的 job；掉線只影響「之後的新 launch 入列」。

**(4) MCP 回覆。** 訊息走既有路徑：`approve` 失敗 → `NotApproved("failed", message)` → MCP 與網頁都顯示 (3) 的訊息。executor 要先在 v3 追出 `NotApproved` 的訊息在 MCP 的 `launch` 與網頁 confirm 頁各自怎麼呈現（`web.py` 的 approve 路徑、`mcp_server.py`），確保**整句**（含機器名與 WSL）原樣出現，不被 `_first_sentence`／`REFUSAL_LIMIT=300` 截掉：訊息長度控制在 300 字元內。`run_outputs`／`list_site_files` 的斷線訊息註明機器是 mcp-site-connection-status 的工作，本件不重做。

**(5) 開連線指令改保活（單一來源）。** 平台從不自己寫指令樣板，`open_command` 是 agent 擷取 `on_site.sh` 印的那一行（refusal-visibility 的裁決 1），所以只改 `scripts/on_site.sh:201` 與 `scripts/reset_master.sh:62`，兩處改成同一條：
`$open_ssh -o ControlMaster=auto -o ControlPath=$CP -o ControlPersist=yes -o ServerAliveInterval=60 -o ServerAliveCountMax=10 $HOST true`
- `ControlPersist=yes`＝master 沒有閒置逾時，靠 `ServerAlive*` 偵測死線；`ServerAliveInterval=60`×`CountMax=10` ＝ 約 10 分鐘網路中斷內不放棄（原本預設 CountMax=3、只容忍約 3 分鐘）。
- 說明文字（204–209 行與 reset_master.sh 64–68 行）同步改：不再宣稱「8h」，註明「存活上限由 `scripts/keepalive_log.sh` 的 log 量測」，並保留既有已知事實（`wsl --shutdown`、機器睡眠會終止）。
- 新行須通過 `jobs.valid_open_command`（`ServerAliveCountMax` 已在白名單、長度 < 600、無禁用字元）；不改該函式。
- 國網未公布時限（10-23 曾 <8h 死），所以**不宣稱**「改了就不會掉」，文件與提示只說「已延長偵測容忍並開始量測」。

**(6) 保活記錄程式 `scripts/keepalive_log.sh`（WSL 內執行，不放進 `platform/abf_station/`，因 `test_station_static.py:90` 禁止站台原始碼出現 ssh／ControlPersist）。**
- 迴圈：每 `ABF_KEEPALIVE_INTERVAL` 秒（預設 600）呼叫 `bash scripts/on_site.sh --check-master`（零 session、不佔 slot、不等 OTP；此旗標由 mcp-site-connection-status 新增，**不得自己另寫 `ssh -O check`**，以免與 16e 的 slot 計算分歧）。`ABF_KEEPALIVE_ONCE=1` 時只跑一輪（給測試）。
- log 檔 `${ABF_KEEPALIVE_LOG:-$HOME/.abf/keepalive.log}`，一行一筆，空白分隔 key=value：`ts=<ISO8601 含時區> machine=<hostname> master=open|closed rc=<退出碼>`；偵測到 open→closed 時另寫一行 `event=closed lasted_min=<自上次 closed→open 或程式啟動後首次 open 起算的分鐘數> last_open=<ISO>`；closed→open 寫 `event=reopened`。檔案超過 1 MB 時改名為 `.1`（只留一份）。
- 不開連線、不輸入 OTP、不寫任何憑證；`kill` 即停。不自動啟動，使用方式寫進 `docs/PLATFORM.md` 與 PITFALLS：`nohup bash scripts/keepalive_log.sh >/dev/null 2>&1 &`。
- 目的是量出實際上限：維護者之後把 log 的 `event=closed lasted_min` 貼回來，再決定要不要調整。

## 失敗先行測試
新檔 `platform/tests/test_site_disconnect_ux.py`（先紅）：
1. `test_closed_agents_only_fresh_closed`：closed＋新鮮→列出；open、unknown、過期的 closed、舊 agent 無欄位→不列。（B/R 前提）
2. `test_closed_agents_only_own_agents`：別人的 agent closed 不出現在我的清單。
3. `test_listing_is_read_only`：呼叫前後 `jobs` 列數與 `agents.last_seen_at` 不變。
4. B1 `test_board_shows_red_bar_when_closed`：有 closed agent 的使用者載入 `/`（及 `/launch`、`/settings`），HTML 含 `class="linkbar"` 與 agent 名與 "WSL"；zh、en 各一。
5. B2 `test_no_bar_when_open_or_unknown`：HTML 不含 `linkbar`，且與沒有此功能時的輸出逐字相同（open／unknown／過期各一）。
6. B3 `test_bar_not_shown_to_other_users`：A 的 agent closed，B 登入看不到。
7. B4 `test_bar_escapes_agent_name`：agent 名含 `<`、`"` → 不原樣出現在 HTML。
8. M1 `test_launch_refused_names_agent_and_wsl`：closed 時 `approve` launch → `NotApproved`，訊息含 agent 名、"WSL"、以 `No open connection to the site` 開頭、長度 ≤ 300。
9. M2 `test_message_survives_first_sentence`：訊息經 `jobs._first_sentence`／`_refusal_of_row` 後仍含 agent 名（分類為 `site_down`）。
10. M3 `test_mcp_launch_message_shows_whole_sentence`：經 MCP `launch` → yes 的路徑，回覆含機器名與 WSL。
11. R1 `test_running_run_unaffected_when_closed`：已有一個 running 的 run，agent 變 closed 後 `get_run` 狀態、`launches` 列、既有 job 完全不變。
12. R2 `test_cancel_and_reads_not_blocked_when_closed`：closed 時 `cancel`、`fetch`、`read_task_log` 仍照舊 enqueue（不被本檢查擋）。
13. R3 `test_launch_goes_through_after_reopen`：closed 被擋 → agent 回報 open → 重新 launch 成功入列。
14. `test_open_and_unknown_do_not_block_launch`：open／unknown 時 launch 照舊成功（不誤擋）。
15. K1 `test_open_command_from_on_site_is_valid_and_keepalive`：用假 ssh（`ON_SITE_SSH_BIN`，比照 `tests/on_site_test.sh` 的 `no_master_run`）取得印出的行；斷言含 `ControlPersist=yes`、`ServerAliveInterval=60`、`ServerAliveCountMax=10`、不含 `ControlPersist=8h`，且 `jobs.valid_open_command(line, host)` 不為 None（含 `wsl.exe -e` 前綴版本）。
16. `test_platform_sources_have_no_command_template`：既有 TC-007/008/094 仍綠（platform 非測試原始碼沒有新增 `ControlPersist`）。
shell：`tests/keepalive_log_test.sh`（K2、K3）：
- K2：`ABF_KEEPALIVE_ONCE=1` 與假 `on_site.sh`（以環境變數指向，回 0）→ log 一行含 `master=open rc=0`、ISO 時間、`machine=`；假回 1 → `master=closed rc=1`。
- K3：先 open 再 closed 的兩輪 → 第二輪另寫 `event=closed lasted_min=`；log 超 1 MB → 輪替成 `.1`；腳本全程沒有呼叫 `ssh`（假 ssh 沒被叫到）、沒有 `sleep` 以外的等待（ONCE 模式不睡）。
並更新 `tests/reset_master_test.sh:32`（見下）。

## 允許更新的既有斷言
以下只准照新行為更新，不准放寬其他斷言：
- `tests/reset_master_test.sh:32`：`t "ssh closes the master and prints the reconnect line" 0 "ControlPersist=8h"` → 期望 `ControlPersist=yes`。
- `platform/tests/test_results_files.py:27` `STYLE_SHA256`（698 行比對）：新增 `.linkbar` 規則後重算並更新該常數；`platform/tests/test_web_downstream.py:236` 是從 test_results_files.py 讀這個值，不必另改，但要確認仍綠。
- `platform/tests/test_refusal_visibility.py:138`（TC-090 `_absent("site_link") == []`）：mcp-site-connection-status 已必須改它；本件新增的 `site_link.py` 也含該字樣。若前者已改，確認該行已不再斷言 `site_link`；若未改，則只改這一行，`abf-station connect`／`abf-connect://` 的斷言保留。
- `platform/tests/test_refusal_visibility.py:20` `GOOD` 只是合格行的夾具，不必改（舊格式仍合法）；122、133、165、167 行**不動**，執行者要確認仍綠。
- `platform/tests/mcp/snapshots/tools.json`（description 變動；工具數仍 22）與 `platform/tests/mcp/test_mcp_contract_tools.py`、`test_mcp_contract_writes.py` 中釘 description 的行（與 mcp-site-connection-status 同檔，後合併的人解衝突）。
- 預期**不動**、executor 要確認仍綠：`platform/tests/test_web_settings_personal.py`（devbar 計數 237、254、366、418–419）、`test_station_static.py:90`（tc087，站台原始碼無 ssh／ControlPersist）、`tests/on_site_test.sh`（`no_master_run`，144 行附近）、`tests/on_site_parallel_test.sh`、`test_failures.py:193`、`test_refusal_visibility.py` 全檔、`test_launch_followup.py:23`、`test_chat_tools.py:15`、`test_guidance.py:26`。
- 22 工具集合的測試（`test_aws_ce`、`test_azure_ce`、`test_gcb_ce`、`test_aws_launch`、`test_azure_launch`、`test_azure_upload`、`test_gcb_launch`、`test_dataset_launch`）預期不動；動到就是多加了工具，退回。
- 文件測試：`test_onboarding_doc.py:223`、`test_station_docs.py:25`、`test_launch_docs.py:79`（讀 PITFALLS.md）——只在改了那幾份文件字句時才動，且只改被釘住的那句。

## 完成標準（done when）
- 上列新測試全綠；既有測試除「允許更新」外不動；完整 `platform/tests` 與 shell 測試（含 `tests/on_site_test.sh`、`tests/reset_master_test.sh`、`tests/keepalive_log_test.sh`）綠。
- **網頁畫面證據**（M 級：網頁畫面另附截圖）：用假資料讓一個 agent 自報 `closed`，截圖 `/` 頂端紅條（zh 與 en 各一）；agent 回 `open` 後紅條消失。截圖檔名與看到的字寫進 ledger。
- 實演：掉線時送出 launch 被擋，訊息含機器名與 WSL；已在跑的 run 的 `get_run` 前後 diff 為空；恢復後重新 launch 入列。
- 實演 `keepalive_log.sh`：貼一段真的跑出來的 log（假 `on_site.sh` 即可，標明是模擬）。
- 憲法檔與安全網（`rules`、確認流程、`cancel` 流程）零 diff；`git diff --stat` 貼進 ledger；無 `CREATE TABLE`／`ALTER TABLE`／migration；`git diff origin/v3 --name-only` 沒有 `platform/abf_station/`、`.github/`、`hooks/`、`constitution.md`、`plugin.json`（若有必須升 L）。
- `docs/PITFALLS.md` 新增一條（Symptom／Root cause／Check／Touches）：連線存活上限未知，log 用法與 `event=closed lasted_min` 的讀法；`ControlPersist=yes` 不等於永不掉。

## 環境事實
- 維護者 11-07 定案的三件事：①掉線紅條＋MCP 明講機器；②掉線擋新 run、不影響已在跑的；③保活指令與 10 分鐘 log。國網未公布時限，10-23 曾不到 8 小時就掉；因此 log 是量測、不是承諾。
- 連線是人在桌機 WSL 輸入 OTP 開的 ControlMaster，agent 與平台都不能代開（`docs/LAB_AGENTS.md` M16）。MCP 站台：`https://desktop-7j5l5bj.tail6bf2f5.ts.net/mcp`；兩個 agent：`desktop`、`desktop-gcb`。
- **依賴 mcp-site-connection-status 提供**：`site_link`／`site_link_at` 事實鍵與 `agents.view` 欄、`scripts/on_site.sh --check-master`、`run_outputs`／`list_site_files` 斷線訊息註明機器、`get_run` SU 修正。LLM 診斷用的 `get_run`／`read_task_log` 已存在，不重做。
- **同車道同檔衝突表**（兩件都改，必須序列化，本件在後）：`scripts/on_site.sh`（它加 `--check-master` 分支，本件只改 `no_master()`，區段不重疊）；`platform/abf_platform/actions/__init__.py`、`common.py`、`agents.py`、`compute_envs.py`、`su.py`（本件**不碰**）；`platform/abf_platform/mcp_server.py`（兩件都改 description，後者解衝突）；`platform/tests/mcp/snapshots/tools.json`；`platform/tests/test_refusal_visibility.py:138`。
- 其他在跑的相鄰件若碰 `web_board.py`／`web.py`／`jobs.py`，需 supervise 判車道是否相交；本件在 `web_board.py` 只動 `STRINGS`、`STYLE`、`_frame`。
- 現況：`scripts/on_site.sh:201` 印 `ControlPersist=8h -o ServerAliveInterval=60`；`jobs.py:1238–1258` 白名單已含 `ServerAliveCountMax`；`jobs.SITE_DOWN = "No open connection to the site"`；`web_board.py:925–937` 已有「站台連線沒開，工作沒有送出」的事後頁面（用 `open_command`）；`_frame` 在 `web_board.py:946`，所有頁（board、launch、settings、usage、upload、downstream）都經它。
- 新 `.py` 檔頭要有 `# Nothing existing: …` 一行；`handlers.py` 避免引號包住的 sbatch 樣式（本件不碰）。

### PITFALLS 已查（`docs/PITFALLS.md`；根目錄無 PITFALLS.md、無 `docs/solutions/`）
- **16e. Too many on_site.sh calls on one master silently hang, not error.** Symptom：一個 master 上 on_site.sh 呼叫過多會靜默卡住，`ssh -O check` 與 preflight 的 reach 行仍顯示 OK。Check：`tests/on_site_parallel_test.sh`、`tests/reset_master_test.sh`。→ 紅條與擋送只代表「控制通道沒了」；`open` 不保證下個 session 不卡，所以只在 `closed` 動作；`keepalive_log.sh` 一律走零 session 的 `--check-master`，不得每 10 分鐘開 session。
- **16b／16g（Windows 多工條目，Touches: ssh, on_site.sh, ControlPersist, ControlPath, WSL2, Git Bash，PITFALLS 約 860–877 行）**：Symptom：Git Bash／PowerShell 不能 multiplex，`Master running` 後 `mux_client_request_session: read from master failed`。Check：`tests/on_site_test.sh`。→ 指令必須在 WSL 終端機執行、保留 `wsl.exe -e` 前綴；紅條與訊息都寫「WSL 終端機」；`keepalive_log.sh` 也只在 WSL 內跑。
- **`wsl.exe`／ControlPath 條目（約 1018–1061 行，Touches: wsl.exe, ssh, ControlPath, on_site.sh）**：Symptom：把推論當量測。→ 不宣稱 `ControlPersist=yes` 就不會掉，只記錄量測。
- **58. A failed first ssh step was read as bad input (realpath-site-down).** Symptom：連線過期時 `read_run_file`／`list_site_files` 答「路徑被拒」。Check：`platform/tests/test_station_realpath_down.py`。→ 本件不碰這些路徑，也不得把 `site_unreachable` 改回 path refused。
- **57. preflight under reach ssh opened 4 sessions.** Check：`tests/preflight_ssh_fold_test.sh`。→ 本件不得讓任何週期動作多開 session。
- refusal-visibility 的裁決 1（`specs/refusal-visibility/plan.md`）：開連線指令以 `on_site.sh` 印的那一行為唯一來源，平台不存樣板；`test_refusal_visibility.py` TC-007／008／094 守住。→ 只改 `on_site.sh`／`reset_master.sh`，平台不新增 `ControlPersist`。
- web.py／web_board.py／jobs.py／STYLE 雜湊：PITFALLS 已查，無相符項（但 `STYLE_SHA256` 與 devbar 計數有測試守，見允許更新清單）。

## 不做
- 不重做 mcp-site-connection-status 的任何一項（`site_link` 欄位、`--check-master`、SU 修正、`run_outputs`／`list_site_files` 訊息註明機器）。
- 不改 `platform/abf_station/`；agent 側自報連線狀態維持它的實作。
- 不在查詢或送出時登入、重試、等待連線；不代人輸入 OTP；不自動啟動 `keepalive_log.sh`、也不由 agent 或平台去啟動。
- 不擋 cancel、fetch、讀 log／讀檔、preflight；不改已在跑的 run 的任何狀態。
- 不新增 MCP 工具；不放寬安全網或確認流程。
- 不做「launch 表單產生當下就預檢、不讓使用者白按一次 yes」：目前擋在 yes 之後（approve），表單先出現是後續改進，另開件。
- 不依 log 自動調整參數；量測結果出來後由維護者決定下一步。
- 不處理 lab-agent 試跑回報的 #3、#5、#6，也不處理圖片／HTML 顯示缺口（見 mcp-site-connection-status 的「不做」）。

## 待決（給 developer-agent）
1. 「WSL 內常駐程序」：本計畫解讀為①ssh master 本身以 `ControlPersist=yes` 常駐、②`keepalive_log.sh` 是另一支常駐的記錄迴圈（人用 `nohup` 啟動）。若維護者其實要「常駐程序自動維持／重連連線」，那需要 OTP，與「OTP 由人輸入」衝突，應回報而不是實作。
2. 新 run 擋在 yes 之後還是表單產生時：本計畫選前者（改動最小、單一入口）。
3. 風險 M 的前提是不碰 `platform/abf_station/`；若實作時發現 agent 側必須改（例如 `site_link` 在 mcp-site-connection-status 的實作不足以判斷新鮮度），升 L 並先回報。

## 裁決（lead，2026-11-07，回應計畫撰寫者的三點）
1. 「WSL 內常駐程序」解讀接受：ControlPersist=yes 的 master 常駐，加人用 nohup 啟動的 keepalive_log.sh 記錄迴圈；**不做自動重連**（需要 OTP，維持由人輸入）。
2. 新 run 擋在使用者按 yes 之後（enqueue_confirmed）接受；表單出現時不預檢，但網頁頂端紅色提示在掉線時一直顯示。表單預檢另案。
3. 硬依賴 `mcp-site-connection-status`（`--check-master`、`site_link`）：必須排在它合併之後。
4. 測試衝突：`test_refusal_visibility.py:138` 的 TC-090（禁止出現 site_link）與 `mcp-site-connection-status` 衝突，**由先合併的那件修改，後合併的那件 rebase 時沿用**；只允許改這一條斷言的範圍（放行 site_link 欄位），不得放寬其他斷言。`tests/reset_master_test.sh:32` 的 ControlPersist=8h 斷言改為 `yes`、`STYLE_SHA256` 因新增紅條 CSS 重算，屬允許的斷言變動。

## 裁決（lead，2026-11-11：設計依據，放行設計閘）
5. 本件的畫面只有一個元件：頁面頂端的掉線紅條。不需要另出草稿，設計依據＝repo 根 `DESIGN.md`（origin/v3）既有規則，executor 不做任何新的視覺決定：
   - 顏色只用 `DESIGN.md`「Tokens」節的 `status-failed`（#b0261d）與它的 `-bg` 底色；深色模式用 `tokens.json` 的對應值。不新增顏色、不寫死其他色碼。實作上沿用 `.devbar` 已用的同一組變數。
   - 位置：`_frame` 內 `devbar` 之後、主版面之前，滿寬一列；不遮住內容、不固定浮動、不可關閉（連線恢復才消失）。這是全站狀態列，不屬於 `DESIGN.md`「Formal notices」節的右欄通知元件，不得放進右欄。
   - 文字：照本計畫 (2) 的 zh／en 字串，遵守 `DESIGN.md`「用字」節（不口語、不用驚嘆號、動詞固定）。不加圖示以外的裝飾；`role="alert"`。
   - 寬度 1440 與 390 px 都不得出現水平捲動；多個 agent 掉線時每個一行。
6. 維護者的方向已足夠（原話見上：「連線狀態可見＋掉線時明確提示」），不再訪談。合併後截圖（zh／en × 1440／390）列進每日清單請他事後看；他回「不好」另開修正件。
7. `kinds` 原寫成 `[backend, ui]` 造成守則沒貼上，已改為 `backend, ui` 並重貼守則。

## 裁決（自動補，2026-11-11）
以下取代裁決 5 中有歧義的字句；與前文衝突時以本節為準。
8. 顏色（紅條不是琥珀條）：`.devbar` 用的是 `--lost`／`--lost-bg`（琥珀），**本件不得沿用**。`.linkbar` 規則只用 `var(--failed)`（文字與符號）與 `var(--failed-bg)`（底色），即 DESIGN.md 的 `status-failed`／`status-failed-bg`；不寫任何色碼字面值、不用左側色條。取代 (2) 的「沿用 `.devbar` 的紅色變數」與裁決 5 的「沿用 `.devbar` 已用的同一組變數」。只沿用 `.devbar` 的版面（flex、gap 8px、padding 8px 16px、font-weight 600）。TC 的紅色判定＝`.linkbar` 規則含 `var(--failed-bg)` 與 `var(--failed)`，且不含 `--lost`。
9. 符號：要有符號（UI 守則：符號＋文字＋顏色）。用 DESIGN.md 失敗狀態既有的「✗」，結構比照 `.devbar`：`<div class="linkbar" role="alert"><span aria-hidden="true">✗</span><span>…</span></div>`，多個 agent 掉線時每個 agent 一個這樣的 div（一行一個）。不用「!」（避免與 `.devbar` 琥珀警示混淆，也符合「不用驚嘆號」）。符號 span 不放進文字字串；`STRINGS` 的 `linkbar_down` 仍照 (2) 的 zh／en 原文。TC 須檢查 HTML 同時含 ✗、文字與 `role="alert"`。
10. 深色模式值的來源：`web_board.py` 的 CSS 變數表已有 `--failed`／`--failed-bg` 的亮色（約 211 行：#b0261d／#fae6e3）與深色（約 214 行，`prefers-color-scheme: dark` 區段：#f28b81／#3a1916）；`.linkbar` 用變數名即自動換色，不新增深色區段、不另查 `tokens.json`。（`--lost` 的深色值在 215 行，與本件無關。）TC：深色區段內存在 `--failed` 與 `--failed-bg`，且 `.linkbar` 沒有自帶色碼。
11. 依賴確認（supervise）：開工前確認 base 已含 mcp-site-connection-status（`site_link`／`site_link_at`、`agents.view` 欄、`on_site.sh --check-master`）；未含則不開工。所有 TC 以該件已合併為前提，出題用其合併後的介面。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。

## 專長守則（ui）

### executor

- 先讀專案根目錄的 `PRODUCT.md`（給誰用、要解決什麼）與 `DESIGN.md`（版面線框、tokens、每個畫面與狀態、維護者的原話例子）。讀不到就 BLOCKED，不自己發明設計。
- 只准用 `DESIGN.md` 定義的 tokens（色彩、字型、字級、間距、圓角）與版面。不新增任何視覺決策：不自創顏色、字型、間距數值，不順手「美化」。
- `DESIGN.md` 沒決定的事，一律寫進報告的「卡住的原因／要問的問題」，不猜。
- `DESIGN.md` 列出的每個畫面、每個狀態都必須做出來，包含空狀態、載入中、錯誤、失敗。少一個就不算完成。
- 遵守計畫寫明的前端限制（例如 CSP、禁用 inline style、不載外部資源、只在允許處使用 JS）。限制與設計衝突時停下來問，不自行取捨。
- 狀態絕不只靠顏色：一律「符號＋文字＋顏色」三者並用。
- 手機寬度可用（不橫向捲動、點擊目標夠大），鍵盤操作時焦點外框可見。
- 介面文字用使用者視角的白話，不露出內部術語、錯誤代碼或程式名詞；錯誤訊息說發生什麼事與下一步。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- `DESIGN.md` 的每個畫面、每個狀態都至少對應 1 個 TC（含空、載入、錯誤、失敗）。
- 維護者的原話例子逐字對應到 TC。
- 計畫列的前端限制各對應 TC（例如頁面不得含 inline style、不得請求外部網址、CSP 標頭存在）。
- 狀態表達 TC：每個狀態輸出的 HTML 同時含符號、文字，不得只靠 class 顏色。

**ACCEPTANCE（閱卷）必須檢查：**
- 把每個有改動的頁面渲染成 HTML 檔（用專案的 test client，或計畫指名的 fixture）。做不到就標 UNVERIFIED，並寫明需要什麼才能驗。
- 對渲染出的 HTML 跑 Impeccable 偵測器（唯讀）：`sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`。
- **FAIL**：違反 `DESIGN.md` 的 tokens／畫面／狀態；違反計畫寫明的前端限制；狀態只靠顏色；缺少 DESIGN.md 列出的畫面或狀態。
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型等）與品味問題。這些不判 FAIL（範本味例外，見文末補充：判 FAIL）。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。
- **實際跑起來看（ACCEPTANCE，2026-11-03 加）**：用 `webapp-testing` 的 `with_server.py` 把真正的應用程式起起來，再用 Playwright 驗。腳本路徑 `G:/我的雲端硬碟/謝馬爾/.claude/skills/webapp-testing/scripts/with_server.py`，**先跑 `--help`** 看用法（把它當黑盒子用，不要先讀原始碼）；啟動指令與通訊埠寫在計畫裡。
  - repo 已有 `scripts/ui_check.py` 就直接跑它：1440／390 寬 × zh／en 共 4 張截圖，加 axe-core 無障礙掃描；**axe 出現 serious 或 critical 一律 FAIL**。
  - repo 還沒有 `ui_check.py`：verifier 自己用 Playwright（經 `with_server.py`）拍同樣 4 張截圖；axe 沒跑就標 **axe：UNVERIFIED**，並寫明缺什麼。
  - 截圖只能存到 repo 之外或 `.gitignore` 排除的資料夾，**絕不存進 Drive 工作區**；報告只貼路徑與張數。
  - 起不了應用程式（缺依賴、埠被占）標 UNVERIFIED 並寫明需要什麼，不改以靜態 HTML 當作通過。
- **範本味（制式 AI 樣板感）（2026-11-10 加）**：實作要避免千篇一律的預設樣式（預設字型加預設配色、無意義漸層與卡片堆疊、裝飾性圖示）；一切視覺決定以 DESIGN.md 為準。
- **與核可草稿比對（2026-11-10 加）**：若計畫附有維護者已核可的設計草稿或截圖（design 類任務的產出），實作畫面必須與它一致；不一致處寫進報告，不自行取捨。
- **文字檢查（2026-11-10 加）**：改過的頁面渲染成 HTML 後，自己先跑 impeccable 偵測器並處理其發現，再交付。

### verifier 補充（2026-11-10）

- **FAIL**：畫面有範本味（制式 AI 樣板感）；截圖與維護者核可的草稿不一致且報告未說明；impeccable 偵測器的違規未處理。以上三條原本列為「需要人看的事」的範本味，改為判 FAIL。
- 計畫附有核可草稿時，逐畫面把實跑截圖與草稿並列比對，不一致處逐條列出；沒有草稿可比對則標 UNVERIFIED 並寫明缺什麼。
- 出題（CONTRACT）加：每個畫面一條「與核可草稿一致」的 TC，一條「通過 impeccable 文字檢查」的 TC。


## 裁決（lead，11-11 深夜，接全套紅燈兩題）
1. **不得把 keepalive_log.sh 加進 DAEMON_ALLOW**（該閘門守憲法 I.2『不得有監控常駐程式』，放寬屬 A 級，未獲授權）。改作法：keepalive_log.sh 改成**單次執行**——每呼叫一次只檢查一次連線、追加一行 log，並從 log 最後一筆算 open→closed 的存活分鐘；不得有 while／loop／nohup／sleep 常駐。docs 與 PITFALLS 的使用說明改成『由人手動或既有排程呼叫一次』，不宣稱常駐。TC K2／K3 對應改成單次呼叫的行為（連呼叫兩次、第二次偵測到 closed 時寫 event 行）；先前的 loop 版測試內容改寫，不是刪除。
2. **TC-009 中文連結列文字改用『分析』，不得含 run**（wording sweep 禁用字，不開例外）；verifier 重寫該 TC 的字串，頁面同一句。推送同一分支。


## 裁決（lead，11-12）
TC-009／034／068／069／073 的合約文字改成與 11-11 深夜裁決一致（單次執行的 keepalive_log.sh、無 loop／nohup／sleep、中文用『分析』）；由 worker 改合約後重驗，通過就推同一分支。
