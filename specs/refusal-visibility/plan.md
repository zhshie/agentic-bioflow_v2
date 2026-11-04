---
id: refusal-visibility
title: 站台因「沒有開著的連線」退回時，退回原因與開線指令送到網頁：站台結果帶結構化 open_command，確認頁與分析清單頁不再對被退回的工作顯示「已送出」
tier: B
risk: L
kinds: backend, ui
review: maintainer（網頁畫面有改動；4 張截圖：確認頁 × 1440／390 × zh／en）
lane: 新車道（不碰 confirm.py、actions/__init__.py、mcp_server.py——那三個是 mcp-chat-confirm 車道 L44 獨占；本片可現在就並行開工）
depends: 無（與 mcp-chat-confirm 檔案不相交）；後續 confirm-status-query 會讀本片寫進 result_json 的 `open_command`（可選鍵，沒有就略過）
branch: feat/refusal-visibility
base: v3（查證時 `origin/v3` @ 1802fde4；行號會漂，以符號名為準）
source: GitHub issue 349（zhshie/agentic-bioflow_v2）的 B3＋B2；memory/handoff/2026-11-04-abf-mcp-confirm-not-registering.md
---

# refusal-visibility

## 目標
站台以「No open connection to the site」退回工作時：①站台回給平台的結果多一個結構化欄位 `open_command`（使用者要自己貼的那一行）；②`jobs.clean_result` 只收符合嚴格格式的值；③網頁確認頁 `/c/<id>` 與分析清單頁在連到的工作被退回時顯示「退回原因＋那一行指令」，**絕不**再寫「已送出」。對使用者的意義：他按了送出、站台沒收，頁面直接告訴他「沒送出，原因是連線沒開，在平台主機的 WSL 終端機貼這一行」，不必回頭問 AI。

## 維護者原話（verifier 出題用）
GitHub issue 349 是 maintainer 的評估，逐字（中英對照原文）：
- 「按鈕本身沒壞。真正的缺口是**站台退回的原因到不了 AI 和使用者**。」→ RV-01～RV-08。
- B3：「站台退回時，在結果裡另外放一個 `open_command` 欄位（`connect_failure` 已經從 stderr 擷取這一行）。`jobs.clean_result` 只接受符合嚴格格式的值：`^(wsl\.exe -e )?ssh( -o [A-Za-z]+=[^\s;&|$`]+)+ [\w.@-]+ true$`，≤600 字元，不合就丟掉。」→ RV-01～RV-04。
- 「**指令以 `on_site.sh` 印出的那一行為唯一來源**（`no_master()`…），不在平台另外硬寫一份。⚠️ 交辦內容提議的 `-o ControlPath=$HOME/.ssh/cm-%r-%h-%p` 如果跟 `ssh_control_path` 設定不一樣，開出來的 master 外掛**找不到**（2.15.0 的 Windows/WSL 事故就是這樣）。… ControlPath 一定要和 `$CP` 逐字相同。主機名取自 CE 的設定，不取自使用者的輸入。」→ RV-02、RV-05、裁決 1。
- 顯示文字（launch 回覆、確認頁、runs 頁共用一段）：「站台連線沒開，工作沒有送出（什麼都沒建立）。請在**平台主機 `<agent 主機名>`** 的 WSL 終端機貼上下面這行，輸入 passphrase 和 OTP 後，回到 AI 重新呼叫 launch：`<open_command>`」；英文：「The connection to the site is not open; nothing was submitted. On the **station host `<host>`**, paste this line into a WSL terminal, enter your passphrase and OTP, then call launch again: `<open_command>`」→ RV-06、RV-07。
- B2：「確認頁和 runs 頁對 refused 的 job 顯示上面那段文字，不再顯示『已送出』。確認頁『已送出。工作編號 N』也改成『已排入佇列（平台編號 N），站台結果見 runs 頁』。」→ RV-06～RV-10。（見裁決 3。）
- T3：「確認頁：confirmed 而且 job 被 refused → 顯示退回原因和指令，頁面上**不出現**『已送出』。job 是 queued/done 時維持原文案。」→ RV-06、RV-09。
- 護欄：「平台沒有任何端點接收 passphrase/OTP，也沒有轉送到 ssh（grep 檢查加路由清單檢查）。」「**不收密碼、不做 web pty，URL scheme 先不做。**」→ RV-12。
- 維護者在聊天要求的指令（經 peer session 轉達）：`ssh -fN -o ControlMaster=yes -o ControlPersist=12h -o ControlPath=$HOME/.ssh/cm-%r-%h-%p -i ~/.ssh/nchc_t3c4 u9613010@nano4.nchc.org.tw`——**與 issue 349 的結論衝突，見裁決 1（採 issue，不採這一行）**。

## 範圍：檔案（只准改這些）
- `platform/abf_station/handlers.py`、必要時 `platform/abf_station/rules.py`（`Refusal` 帶一個可選屬性）與 launch 預檢被退回的那條路徑（`handlers.py:96` 的 `_refused(str(e))`；`launch.py:1880` 的 `Refusal`）。只做一件事：被退回的原因是 `reason=no-master` 時，結果 dict 多 `open_command`，值**就是既有 `_open_command(err)` 從 on_site.sh 輸出擷取到的那一行**。不改 `connect_failure` 的文字、不改 `_open_command` 的擷取規則。
- `platform/abf_platform/jobs.py`：`clean_result` 加 `open_command` 驗證（只對 `launch_nextflow`）；新增唯讀 helper（依 job id／confirmation id 讀 state 與清洗後的退回資訊）。不改 schema、不 migration。
- `platform/abf_platform/web.py`：`state_page` 的 confirmed 分支與 `board_page` 各加一次 helper 呼叫。
- `platform/abf_platform/web_board.py`：`STRINGS` zh／en 各加同名鍵；沿用既有提示框 class（`<p class="bad">`、`.notice`），不新增 CSS 元件。
- `docs/PLATFORM.md`（一小段）、`docs/TESTING.md`（手動步驟＋4 張截圖步驟）、`CHANGELOG.md`
- 測試（新）：`platform/tests/test_refusal_visibility.py`（檔首 40 行內 `# Nothing existing: <理由，≥15 字>`，`test_scope.py` TC-070）
- 測試（改）：僅依「必須更新的既有斷言」。
- `specs/refusal-visibility/ledger.md`（新）、`specs/refusal-visibility/screens/`（截圖）

**不准動（硬規則）**：`platform/abf_platform/confirm.py`、`platform/abf_platform/actions/__init__.py`、`platform/abf_platform/mcp_server.py`、`platform/abf_platform/actions/chat_tools.py`、`guidance.py`、`store.py`、`compute_envs.py`（本片**不**新增 `site_login_command`，見裁決 1）、`scripts/on_site.sh`（只讀它，不改）、`.github/`、`hooks/`、`plugin.json`、`.specify/memory/constitution.md`、其他 `web_*.py`。`tools.json` 快照零 diff（沒有改任何 MCP 工具）。

## 作法
1. **站台端（B3）**：預檢／launch 被退回、且原因是 `reason=no-master` 時，`("refused", {"ok": False, "message": …, "open_command": <一行>})`。`<一行>` 只能來自 `_open_command(res.err)`（它讀 on_site.sh `no_master()` 印出的那一行，含 `wsl.exe -e` 前綴與 `$CP` 展開後的 ControlPath）。`_open_command` 回空字串就**不放**這個欄位。**訊息文字不變**（`connect_failure` 照舊把同一行附在 message 後）。`test_station_static.py` 禁止站台 Python 原始碼出現 `ControlMaster`／`ssh -` 字面：新增程式不得寫這類字面（沿用 `_open_command` 既有的 regex 寫法即可）。把 `open_command` 從 `Refusal` 帶到 `_refused` 的方式由執行者決定（例：`Refusal` 加可選屬性）；要動 `rules.py` 或 `launch.py` 以外的站台檔先在 ledger 說明。
2. **平台驗證（B3）**：`jobs.clean_result("launch_nextflow", result)` 讀 `result["open_command"]`，全部成立才保留，否則丟掉該鍵（其餘欄位照舊）：①是字串、`len ≤ 600`；②`re.fullmatch(r"(wsl\.exe -e )?ssh( -o [A-Za-z]+=[^\s;&|$`]+)+ [\w.@-]+ true", s)`（issue 的格式，不含換行、`;`、`&`、`|`、`$`、反引號）；③最後的 `<host>` 部分（若含 `user@` 取 `@` 之後）**等於這個工作所屬運算環境 `config["hostName"]`**（用 `job["compute_env"]` 查 CE；查不到 CE 或沒有 hostName → 丟掉）。其他 kind 一律不收此鍵（`out` 的鍵集合與以前相同）。`ssh_control_path` 不由平台驗證——它由 on_site.sh 決定，平台只負責不信任格式。
3. **唯讀 helper（jobs.py）**：`jobs.refusal_of(state_path, job_id)` → 該 job 是 `refused`／`error` 時回 `{"state", "reason", "open_command"|None, "host"|None}`，否則 `None`。`reason` 取 `result_json.message`，**第一句**，經與 `_outputs_reason` 同等的清洗（不外洩 Traceback／SQL／憑證樣式，最長 300；`jobs.py` 內已有 `_short`，內部字眼過濾若在 `actions` 內就複製最小必要版並在 ledger 說明，不 import `actions`）。`open_command` 取 `result_json.open_command`，**讀出時再驗一次**第 2 點的格式（資料庫裡的舊值也不信任）。再加 `jobs.latest_refusal(state_path, user_id, now, max_age=3600)` → 該使用者最近一筆 `launch_nextflow` job（經 `confirmations.caller_user_id` 連回），若它是 `refused` 且 `finished_at` 在 `max_age` 內，回同樣的 dict（含 `job_id`、`ce`）；否則 `None`。只讀，用 `store.open_readonly`。
4. **共用文字與判斷「是不是連線斷」**：`web_board.STRINGS` 加 `refusal_site_down`、`refusal_other`、`refusal_cmd_label`、`refusal_queued_note` 等同名鍵（zh、en 鍵集合相同，`test_web_wording_sweep.py` 掃）。「連線斷」＝退回訊息含穩定前綴 `No open connection to the site`（與 `test_station_realpath_down.py` 同一前綴）。連線斷且有合格 `open_command` → 顯示 issue 規定的那段文字（zh／en）＋`<pre>` 內放那一行；連線斷但沒有 `open_command` → 只顯示說明與「請查看站台主機的終端機提示」，**不自己組指令**；其他退回原因（Java 版本、sessions-exhausted 等）→ 顯示 `reason` 一句，不顯示登入指令。`<agent 主機名>` 用該 job 的 `agent` 欄（工作所屬代理名）；沒有就寫運算環境名。
5. **確認頁（B2）**：`state_page` 的 `confirmed` 分支：用 `req["job_id"]` 呼叫 `jobs.refusal_of`。有退回 → 輸出 `<p class="bad">` 退回區塊（第 4 點），**不輸出**「已送出」三字，也不輸出 `class="ok"` 的送出句；其餘（`req` 無 job、queued、claimed、done）→ 輸出與以前**逐位元組相同**的 `<p class="ok">已送出。工作編號 N。</p>`（見裁決 3）。`confirm_post` 剛按完送出那一刻 job 必為 queued，其路徑不動。
6. **分析清單頁（B2）**：`board_page` 在清單上方用 `jobs.latest_refusal(...)` 判斷，有就顯示同一個區塊一次（同一個 helper、同一組 STRINGS）；沒有就頁面與以前相同。別的使用者的退回不出現。退回的 CE 之後有較新的成功 launch job 時，`latest_refusal` 因「最近一筆不是 refused」自然回 `None`。
7. **所有動態文字一律 HTML 跳脫**；指令放 `<pre>`，不放屬性值；**沒有表單、按鈕、輸入框、連結到 ssh**。「複製」按鈕不做（見不做）。
8. 順序：先寫 RV 測試（紅）→ 站台＋`clean_result` → helper → 兩個頁面 → 文件 → 截圖。

## 失敗先行測試（新檔 `platform/tests/test_refusal_visibility.py`，前綴 `test_tcr`；先寫、現在都紅）
- **RV-01** `station_adds_open_command_on_no_master`：站台測試夾具（參考 `test_station_realpath_down.py` 的 `NO_MASTER`＝`on_site: needs-human reason=no-master\n<OPEN_CMD>\n`）餵入 launch 預檢 → 退回結果 `open_command == OPEN_CMD`（逐字）；`message` 與動工前相同（仍含 `RELOGIN` 與 `OPEN_CMD`）。`sessions-exhausted`、java 版本不符 → 結果**沒有** `open_command` 鍵。
- **RV-02** `command_text_is_the_one_on_site_prints`：用真的 `scripts/on_site.sh`（`ON_SITE_SSH_BIN` 假 ssh，比照 `tests/on_site_test.sh` 的 `no_master_run`）取得它印出的指令行，經站台擷取 → `open_command` 等於該行；且在平台與站台 Python 原始碼（`git grep -n "ControlPersist\|nchc_t3c4\|ControlMaster=yes" -- platform`）找不到任何硬寫的指令樣板（`jobs.py` 的 regex 不算：regex 不含具體 ControlPath）。
- **RV-03** `clean_result_accepts_only_the_strict_format`：合格行（`ssh -o ControlMaster=auto -o ControlPath=~/.ssh/cm-%r-%h-%p -o ControlPersist=8h -o ServerAliveInterval=60 u@nano4.nchc.org.tw true`，CE hostName 為 `nano4.nchc.org.tw`）→ 保留；加 `wsl.exe -e` 前綴 → 保留；含 `;`、`&&`、`$(`、反引號、換行、`|` → 丟掉；601 字元 → 丟掉；非字串（None、整數、list）→ 丟掉；只有 `launch_nextflow` 收，`put_upload`／`clean_work`／`preflight` 帶此鍵 → `out` 與以前相同。
- **RV-04** `host_must_be_the_compute_envs_host`：行內 host 是 `evil.example.org`、或 CE 沒有 `hostName`、或 job 的 CE 不存在 → 丟掉，其餘欄位（`ok`、`message`）不受影響。
- **RV-05** `maintainer_literal_control_path_is_not_baked_in`：整個 `platform/`（含測試以外）不含字串 `nchc_t3c4`、`u9613010`、`cm-%r-%h-%p -i`；顯示在頁面上的指令等於夾具裡 on_site 印出的那一行，而非任何平台常數。
- **RV-06** `confirm_page_refused_job_shows_reason_and_command_not_sent`（**主線**）：核准後把 job 標 `refused`、`result_json={"ok":False,"message":"No open connection to the site. Log in once…","open_command":<合格行>}` → GET `/c/<id>`：含退回原因、含整行指令在 `<pre>` 內、含「平台主機」（zh）；`?lang=en` 含 "station host"；**頁面不含「已送出」，也不含 `class="ok"`**。
- **RV-07** `runs_page_shows_same_text`：同一情境 GET `/`（zh／en）含與 RV-06 相同的退回區塊與指令；另一位使用者看分析清單 → 沒有該區塊；超過 1 小時 → 沒有；其後有成功 launch → 沒有。
- **RV-08** `other_refusals_show_reason_without_login_command`：退回訊息是 java 版本、`sessions are used up` → 顯示一句原因、**沒有** `<pre>` 指令、沒有 `ssh `；連線斷但無 `open_command` → 有說明、沒有 `<pre>`。
- **RV-09** `queued_and_done_wording_unchanged`：job 為 queued／claimed／done → `/c/<id>` 與動工前逐位元組相同（`已送出。工作編號 N。`）；`confirm_post` 回應不變。
- **RV-10** `html_is_escaped`：`message` 與 `open_command`（用繞過驗證直接寫 DB 的方式）含 `<script>` → 頁面無未跳脫標籤；讀出時再驗證使壞指令不顯示。
- **RV-11** `strings_keys_match`：`STRINGS["zh"]` 與 `STRINGS["en"]` 新鍵集合相同。
- **RV-12** `no_password_or_otp_anywhere`（護欄）：①所有 MCP 工具 input_schema 屬性名不含 `password|passwd|otp|one.?time|verification|secret`（`token` 若既有就列白名單並註明）；②所有 route 路徑不含 `connect|ssh|login-site`；③退回狀態下 `/c/<id>` 與 `/` 的 HTML：`<input` 沒有 `type="password"`、`name` 不含 `password|otp|code`，沒有 `<button` 文字含「幫我連線」「connect for me」；④對現有 POST 路由帶 `password=x&otp=123456` → 不被讀取、不出現在回應、`confirmations`／`jobs`／sessions 全表不含 `123456`。
- **RV-13** `nothing_else_changes`：`git diff origin/v3 --stat` 不含 `confirm.py`、`actions/__init__.py`、`mcp_server.py`、`tools.json`（閱卷手動案例，證據貼 ledger）。

## 必須更新的既有斷言（預期幾乎零處；沒變紅就不碰）
先跑 `git grep -n "已送出。工作編號\|No open connection\|OPEN_CMD\|RELOGIN\|STRINGS\|clean_result" origin/v3 -- platform/tests tests docs`。
- **必須維持綠、不可為新功能改它們**（釘站台訊息；本片只**加**一個結果鍵，不改訊息）：`test_station_realpath_down.py`（`RELOGIN`、`OPEN_CMD`、`NO_MASTER`）、`test_station_channel.py:167`（`nomaster` → `WSL|共用連線|ControlPath`）、`test_launch_followup.py:23`（`REFUSAL`）、`test_station_e2e.py` 的 connect 檢查 detail、`test_station_static.py`（站台原始碼不得出現 `ControlMaster`／`ssh -`）、`tests/on_site_test.sh`（`no_master()` 輸出不改）。它們變紅＝動到不該動的，退回。
- **網頁釘字（queued／claimed／done 必須逐字不變）**：`test_confirm_page.py`、`test_pending_confirm_restart.py:79/96/115/126`、`test_web_confirm_plain.py:121`、`test_web_nano4_path.py:340/366/379`、`test_clean_page.py:138/253/257`（`已送出。工作編號 N。` 與清理版句子）。若這些測試的夾具 job 狀態是 `refused` 才變紅，才可改——並在 PR 說明逐條寫「以前／以後／理由」。
- **`clean_result` 釘鍵**：`test_cleanup_confirm.py::test_tc051_tc052_clean_result_keeps_only_the_expected_keys`、`test_aws_upload.py:215`、`test_azure_upload.py:225`、`test_byte_channel_a/b.py`：非 `launch_nextflow` kind 的輸出不變（RV-03 守住）。
- **網頁字串**：`test_web_wording_sweep.py`（zh／en 並列標題、中英鍵一致、禁用詞掃所有 `STRINGS` 值；新字串須通過而非放寬）、`test_web_board.py`（若釘 `STRINGS` 鍵數，只准加新鍵數）。
- `tools.json`：零 diff。

## 完成標準（done when）
- 自動：RV-01～13 綠；上節既有測試全綠（`tests/run_all.sh`，WSL）；`git diff --name-only` 只含「範圍：檔案」；`confirm.py`、`actions/__init__.py`、`mcp_server.py`、`compute_envs.py`、`tools.json`、`scripts/on_site.sh` 零 diff；站台 diff 只有「退回結果多一個鍵」。
- 閱卷（M）：RV-02 的 on_site 實際輸出行與頁面上的指令並列貼進 ledger（證明同源）；`grep` 證據：平台無硬寫指令樣板。
- **截圖（review: maintainer，網頁有改動）**：測試平台造一個 `refused`＋合格 `open_command` 的 launch job，截 4 張——**確認頁 `/c/<id>` × 寬 1440／390 × `?lang=zh`／`?lang=en`**；另附分析清單頁 zh/1440 與 en/390 各一（可選但建議）。存 `specs/refusal-visibility/screens/`，ledger 逐張列檔名與看到的字。390 寬不得橫向捲動頁面（`<pre>` 內可捲）；每張確認頁都**看不到「已送出」**。
- 手動（`docs/TESTING.md` 新增）：斷開 ssh master → launch → 在確認頁按送出 → 站台退回 → 重新整理確認頁看到原因與指令；在平台主機 WSL 貼指令登入（OTP 由人輸入）後再 launch → 成功；全程網站沒有任何密碼或 OTP 輸入框。

## 環境事實
- `scripts/on_site.sh:184` `no_master()`：印 `"    $open_ssh -o ControlMaster=auto -o ControlPath=$CP -o ControlPersist=8h -o ServerAliveInterval=60 $HOST true"`；WSL 橋接時 `open_ssh="wsl.exe -e ssh"`；`CP="$(setting ssh_control_path …)"`（第 71 行，預設由 `site_control_path_default "$BRIDGE"` 決定）。這一行就是 B3 的唯一來源。
- 站台 `handlers.py:101` `_open_command(err)`：從 stderr 取第一個符合 `^(?:wsl\.exe -e )?ssh\s` 且含 `ControlPath` 與 `true` 的行；`connect_failure(res)`（:122）在 `reason=no-master` 時回 `"No open connection to the site. Log in once in a WSL terminal first (請先在 WSL 終端機登入站台): " + cmd`，並以 `DETAIL_LIMIT=300` 截前綴保指令完整；`_refused(text)`（:36）回 `("refused", {"ok": False, "message": text[:600]})`。
- 預檢被退回在 `launch.py:1880` 丟 `rules.Refusal("預檢未通過，沒有建立任何東西：" + …)`，`handlers.py:96` 接成 `_refused(str(e))`；`aws_launch.py:60`／`azure_launch.py:79`／`gcb_launch.py:132` 同型。**只需要處理 `reason=no-master` 這條**；其餘雲端路徑沒有 ssh master。
- `jobs.clean_result(kind, result, stored=None)`（jobs.py:1210）在 `jobs.py:1366` 被呼叫（`cleaned = clean_result(job["kind"], result, stored)`），`launch_nextflow` 分支已收 `slurm_job_id`、`run_name`、`run_folder`、`left_on_site`；`message` 上限 2000。
- `web.py:434` `state_page(req, sid, rid, lang)`；confirmed 分支 `web.py:449-450` 現在無條件輸出 `<p class="ok">已送出。工作編號 %s。</p>`；`req` 來自 `actions.describe_request`，有 `job_id`（**不改 actions，只在 web.py 用 `jobs.refusal_of(state_path, req["job_id"])`**）。`view_of`（:383）已做擁有者檢查。
- 運算環境 `hostName` 驗證在 `compute_envs.py:238`（`_HOST` regex）；config 裡取 `config["hostName"]`。
- 夾具：`human_harness.World`（`w.user/launch/call/jobs/confirmations/clock`）；網頁測試參考 `test_confirm_page.py`、`test_web_nano4_path.py`；站台測試參考 `test_station_realpath_down.py`。
- **PITFALLS 已查（`docs/PITFALLS.md`；無 `docs/solutions/`），相符項必讀**：①**「A failed first ssh step was read as bad input」（2026-10-30，realpath-site-down）**——症狀：`read_run_file` 與 `list_site_files` 在連 nano4 的共用連線過期時回「path refused」；Check：`platform/tests/test_station_realpath_down.py`（本片不改站台訊息，只加結果鍵）。②**on_site.sh 的 Windows 多工條目（16b／16g，Touches: ssh, on_site.sh, ControlPersist, ControlPath, WSL2, Git Bash）**——症狀：Windows 兩個原生 shell 都不能 multiplex；Check：`tests/on_site_test.sh`；故指令必須在 WSL 終端機執行、並含 `wsl.exe -e` 前綴時原樣顯示。③**「too many `on_site.sh` calls on one master silently hang」（16e）**——Check：`tests/on_site_parallel_test.sh`、`tests/reset_master_test.sh`；`sessions-exhausted` 不顯示登入指令（RV-08）。④**`wsl.exe`／ControlPath 條目（Touches: wsl.exe, ssh, ControlPath, on_site.sh）**——症狀：把推論當量測；本片因此不自創 ControlPath。其餘（web.py、jobs.py、`clean_result`、`state_page`）在 PITFALLS 無相符項。執行者開工前再 grep 一次，有新增項要在 ledger 引用。
- 2.15.0 事故（issue 349 引述）：Git Bash 自己的 ssh 開出來的 master 在 Windows 家目錄，外掛在 WSL 找不到——**ControlPath 與開線的 ssh 程式都要與 on_site.sh 逐字相同**。

## 不做
- **任何「幫我連線」按鈕、web pty、URL scheme（`abf-connect://`）、嵌入式終端、由平台／網站／AI 代為登入**；不收 passphrase／密碼／OTP，不加 SSH 代連 route。RV-12 守住。
- 「複製指令」按鈕（純文字＋剪貼簿）：issue 建議但需要新的前端元件；本片只顯示 `<pre>`，使用者自己選取。後續片再做。
- C2（站台心跳 `site_link` 與 `_target` 預檢、連線斷時 `approve` 保留 pending）、C3（`abf-station connect` 本機小工具）：issue 的 C 級項，另片，需先問 maintainer。
- B1（重複 `launch` 回 `state=refused`＋`last_refusal`）與 C1（`get_request_status`）：在 `confirm-status-query`（L44 之後）。
- 不改 `confirm.py`／`actions/__init__.py`／`mcp_server.py`／`tools.json`／`guidance.py`；不改站台訊息文字、不改 `on_site.sh`；不統一 8h／12h 持久度。
- 不新增 DB 欄位或 migration；不做輪詢或排程（說明在下次成功 launch 後自然消失）。

## 裁決（planner 的決定；Q 開頭的要 developer-agent 回覆）
1. **指令來源衝突（2026-11-04）**：維護者在聊天裡要的指令是 `ssh -fN -o ControlMaster=yes -o ControlPersist=12h -o ControlPath=$HOME/.ssh/cm-%r-%h-%p -i ~/.ssh/nchc_t3c4 u9613010@nano4.nchc.org.tw`；issue 349 的評估則規定「以 `on_site.sh` 印出的那一行為唯一來源，ControlPath 必須與 `$CP` 逐字相同」，因為不同的 ControlPath 會開出外掛找不到的 master（2.15.0 事故）。**採 issue：逐字使用 on_site.sh `no_master()` 印的那一行（由站台擷取後放進 `open_command`），不使用維護者聊天裡的 ControlPath、`-i ~/.ssh/nchc_t3c4` 金鑰與寫死的 `u9613010@nano4`；也不新增 `compute_envs.site_login_command`**（那等於在平台多存一份樣板）。理由：①`-o ControlPath=$HOME/.ssh/cm-%r-%h-%p` 若與使用者 `ssh_control_path` 設定不同就造成「已連線但外掛看不到」；②`nchc_t3c4` 在 repo 內查無出處；③user／host 寫死違反「主機取自 CE 設定」。若維護者仍要 `-fN`／`12h`／`-i`，應改 `on_site.sh` 的 `no_master()` 那一行（單一來源）並跑 `tests/on_site_test.sh`，不是在平台另寫一份——另片。
2. 驗證 regex 採 issue 原式；host 比對 CE `hostName`（不比對 user）。
3. **「已送出」文案**：issue 說確認頁 confirmed 一律改成「已排入佇列（平台編號 N）」，但 `test_confirm_page.py`／`test_pending_confirm_restart.py`／`test_web_nano4_path.py` 等釘著「已送出。工作編號 N」。**本片決定：只有 job 是 `refused`／`error` 時改版面（不含「已送出」）；queued／claimed／done 與無 job 時逐位元組不變**——這同時符合 T3「queued/done 維持原文案」與 brief「queued/done 文字不變」。若維護者要連 queued 也改成「已排入佇列」，需連同上列釘字測試一起改，請另行裁示（Q1）。
- **Q1（需回覆）**：同裁決 3——queued 是否也改「已排入佇列」？（預設：不改。）
- **Q2（需回覆）**：本片範圍含 `platform/abf_station/`，依 README 的規則 supervise 會自動判為 **L**（保護路徑優先）；frontmatter 照派工寫 M。登進佇列時請決定是否改填 L（L＝多交爆炸半徑證明＋Opus 對抗審）。（預設：站台只加一個結果鍵，仍填 M，但 supervise 若推 L 就照 L。）
- **Q3（需回覆）**：把 `open_command` 從 `Refusal` 帶到 `_refused` 需要改 `rules.py`（站台）。若不想動 `rules.py`，替代作法是在 `handlers.py` 的 launch 處理內，預檢退回後再呼叫一次 `site.call(["--check-reach"])` 取行（多一次 ssh 呼叫）。（預設：給 `Refusal` 加可選屬性。）
- **Q4（需回覆）**：顯示文字裡的「平台主機 `<agent 主機名>`」用 job 的 `agent` 欄；agent 名不一定等於主機名。（預設：用 agent 名；沒有就用 CE 名。）

### developer-agent 回覆（2026-11-04）
- Q1–Q4 全照預設（queued 文案不改；risk 寫 M；`Refusal` 加可選屬性 `open_command`；顯示名用 agent 名）。
- 與 mcp-chat-confirm（L44）檔案不相交，可平行；`rules.py` 只加可選屬性，不改既有規則行為。

### developer-agent 對出題 BLOCKED 的回覆（2026-11-04，第二次）
- 連線指令：依 issue #349 的 B3（他經追進度 session 轉達的需求本身）採 `scripts/on_site.sh` 的 `no_master()` 那一行，不用聊天裡 ControlPath 不同的那行（後者建出的 master 平台看不見，2.15.0 事故）。issue #349 即維護者授權，出題者照計畫出題。
- queued 文案：維持逐位元組不變（裁決 3）；`refusal_queued_note` 這個鍵**刪掉**，不新增。TC-044～047 照計畫。
- 風險層級：寫 L（碰 `platform/abf_station/`）；supervise 照 L 跑爆炸半徑＋Opus 對抗審。
- RV-05/RV-06 的「整個 platform/」＝只掃非測試的原始碼（新測試檔自己除外）。
- 行號漂移以符號名為準。CLAUDE.md 的「For the executor and verifier」節 v3 本來就有；先前 worktree 誤從 main 開，已重建在 origin/v3 上。

## 裁決 R（11-05，developer-agent）
1. `test_no_schema_change` 舊基準已過期，我已改成 origin/v3（commit a4c02be5）；不要再因它 BLOCKED。
2. 核准：新增 `web_refusal.py`（TC-H16f 逼出的最小改動）、`test_web_settings_ce_mobile.py` 的 STRINGS 雜湊更新、CHANGELOG 條目順序調整。
3. 修完 test_tc073 後請再完整跑一次全套，再交閱卷。四張截圖由閱卷端處理。

## 裁決 R2（2026-11-05，developer-agent）
TC-032（test_no_schema_change）本機 603/604 的唯一紅是環境假紅：測試比對的 origin/v3 在 WSL 鏡像是舊參照，你實際對真正 origin/v3 的 store.py 差異為 0，已證明。CI 是權威（同類 PR #359、#360 CI 綠）。不改測試、不要再同步鏡像、不要再 BLOCK：把 executor-status 記為 GREEN（註明 TC-032 本機環境紅）、直接交閱卷；四張截圖交閱卷端。

## 裁決 R3（2026-11-05，developer-agent；對抗審 FAIL 的修正，以本節為準）
1. **`error` 狀態不是「拒絕」。** 站台回「sbatch 結果不明：可能已送出」時，確認頁不得寫「站台拒絕了送出、工作沒有送出／nothing was submitted」，否則使用者會重送、同一工作在叢集上跑兩次。做法：只有 state=`refused` 才顯示「沒送出」那句（STRINGS refusal_other）；state=`error` 改顯示新字串（zh/en 都要）：「站台回報送出結果不明，工作可能已經送出。請先查看站台上的資料夾與 Slurm 工作（見下方說明）再決定要不要重送。」後面接站台原訊息與 left_on_site。
2. 這是新增測試：在新檔 `platform/tests/test_refusal_visibility_error_state.py` 加測試（zh、en 各一，error 狀態頁不含「沒有送出」「nothing was submitted」，含「可能已經送出」；refused 狀態頁行為不變）。不改合約檔 test-case.md。web_board.STRINGS 雜湊再更新一次，同裁決 R 第 2 點的理由。
3. **收緊 open_command 格式**（只會讓安全網更嚴，C 級）：`jobs.valid_open_command` 除原規則外，再拒絕含 `>` `<` `(` `)` 引號（單、雙）反斜線的字串，並要求每個 `-o` 的選項名稱在白名單 {ServerAliveInterval, ServerAliveCountMax, ConnectTimeout, StrictHostKeyChecking, UserKnownHostsFile, ControlMaster, ControlPath, ControlPersist, IdentitiesOnly, IdentityFile, Port, User}；`ProxyCommand`、`LocalCommand`、`PermitLocalCommand` 一律拒絕。加對應測試（含上一輪實測會過的 `ssh -o A=b>~/.bashrc u@nano4.nchc.org.tw true`，現在必須回 None）。若原合約有 TC 明確要求某個合法例子通過，以該例子為準、白名單補上它。
4. 其餘範圍不變；仍不准動 store.py、confirm.py、mcp_server.py。

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
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型、AI 範本味等）與品味問題。這些不判 FAIL。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。
- **實際跑起來看（ACCEPTANCE，2026-11-03 加）**：用 `webapp-testing` 的 `with_server.py` 把真正的應用程式起起來，再用 Playwright 驗。腳本路徑 `G:/我的雲端硬碟/謝馬爾/.claude/skills/webapp-testing/scripts/with_server.py`，**先跑 `--help`** 看用法（把它當黑盒子用，不要先讀原始碼）；啟動指令與通訊埠寫在計畫裡。
  - repo 已有 `scripts/ui_check.py` 就直接跑它：1440／390 寬 × zh／en 共 4 張截圖，加 axe-core 無障礙掃描；**axe 出現 serious 或 critical 一律 FAIL**。
  - repo 還沒有 `ui_check.py`：verifier 自己用 Playwright（經 `with_server.py`）拍同樣 4 張截圖；axe 沒跑就標 **axe：UNVERIFIED**，並寫明缺什麼。
  - 截圖只能存到 repo 之外或 `.gitignore` 排除的資料夾，**絕不存進 Drive 工作區**；報告只貼路徑與張數。
  - 起不了應用程式（缺依賴、埠被占）標 UNVERIFIED 並寫明需要什麼，不改以靜態 HTML 當作通過。
