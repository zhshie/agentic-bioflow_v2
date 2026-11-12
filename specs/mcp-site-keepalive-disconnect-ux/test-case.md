# 測試案例：連線保活、掉線紅色提示、擋新送出（mcp-site-keepalive-disconnect-ux）

**規格**：`specs/mcp-site-keepalive-disconnect-ux/plan.md`（本件沒有獨立 spec.md，計畫與其裁決 1～11 即規格）　**總覽**：`test-case-overview.md`

維護者原話（逐字對應到下列案例）：

- 「Q3不要只有8hr, 如果可以更久就改，第一步先只做『連線狀態可見＋掉線時明確提示』」→ TC-009～TC-013、TC-033～TC-037、TC-053～TC-056、TC-061～TC-066
- 「目前我到底能不能夠用MCP請lab-agent跑完分析並顯示在網頁上? 這是我最基本的要求」→ TC-047～TC-052（掉線不影響已在跑的 run、恢復後能重送）

名詞：「站台連線」＝人在自己電腦的 WSL 終端機輸入一次性密碼（OTP）開出的共用 ssh 連線（ControlMaster）。「掉線」＝某個 agent 向平台回報 `site_link=closed` 且回報是新鮮的（超過 3 次心跳沒更新就當 `unknown`）。`open`、`unknown`、過期、舊 agent 沒帶欄位，一律不算掉線。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫「不做」明講這次不做的事；測試確認它真的沒做。

驗證方式「自動」＝指令、測試或讀 diff／讀檔就能判定；「手動」＝要維護者親眼看真畫面。

## User Story 1 — 站台連線掉線時，網頁每一頁頂端出現紅色提示（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 【機器可驗】 | 作法 (1)；測試 1 | 功能 | 使用者 u1 有兩個 agent：`desktop-gcb`、`desktop`，都自報 `site_link=closed` 且新鮮 | 呼叫 `site_link.closed_agents(state_path, u1, now)` | 回傳 `["desktop", "desktop-gcb"]`（排序後的名稱） | 自動：`platform/tests/test_site_disconnect_ux.py` |
| TC-002 【機器可驗】 | 作法 (1)；測試 1 | 例外 | agent 自報 `open` 且新鮮 | 同上 | 不在清單內（猜不到就不誤傷） | 自動：同上 |
| TC-003 【機器可驗】 | 作法 (1)；測試 1 | 例外 | agent 的 `site_link` 為 `unknown` | 同上 | 不在清單內 | 自動：同上 |
| TC-004 【機器可驗】 | 作法 (1)；測試 1 | 例外 | agent 最後一次回報 `closed`，但已超過 3 次心跳沒更新（`agents.view` 視為 `unknown`） | 同上 | 不在清單內 | 自動：同上 |
| TC-005 【機器可驗】 | 作法 (1)；測試 1 | 例外 | 舊 agent 的資料沒有 `site_link` 欄位 | 同上 | 不在清單內，也不報錯 | 自動：同上 |
| TC-006 【機器可驗】 | 作法 (1)；測試 2；專長守則（跨使用者讀） | 例外 | u2 的 agent 自報 closed；u1 自己的 agent 是 open | 以 u1 呼叫 `closed_agents` | 清單為空，看不到 u2 的 agent | 自動：同上 |
| TC-007 【機器可驗】 | 作法 (1) | 功能 | 沒有 user 的終端機呼叫（user_id 為空），兩個不同使用者的 agent 都 closed | 呼叫 `closed_agents(state_path, None, now)` | 回傳兩個 agent（視為全部，與 `jobs._target` 的規則相同） | 自動：同上 |
| TC-008 【機器可驗】 | 作法 (1)；測試 3 | 功能 | 記下 `jobs` 表列數與每個 agent 的 `agents.last_seen_at` | 呼叫 `closed_agents` 數次 | 呼叫前後 `jobs` 列數與 `last_seen_at` 完全不變（純讀取，不寫庫、不 enqueue） | 自動：同上 |
| TC-009 【機器可驗】 | 作法 (2)；B1；原話「連線狀態可見」 | 功能 | u1 的 agent `desktop` 自報 closed，介面語言 zh | u1 登入後載入 `/` | HTML 含 `class="linkbar"`、`role="alert"`、agent 名 `desktop`、字樣 `WSL`；含 zh 原文「站台連線已掉：請在執行 agent「desktop」那台機器的 WSL 終端機重新登入（貼上開連線指令並輸入 OTP）。已在跑的分析不受影響；新的分析在恢復前無法送出。」（中文用「分析」，不含「run」） | 自動：同上 |
| TC-010 【機器可驗】 | 作法 (2)；B1 | 功能 | 同 TC-009，介面語言 en | 載入 `/` | HTML 含 `class="linkbar"`、`role="alert"`、`desktop`、`WSL`，並含 en 原文「The site connection is down. On the machine running agent "desktop", log in again in its WSL terminal (paste the connect line, type the one-time code). Runs already going are not affected; new runs cannot be sent until it is back.」（agent 名經 HTML 跳脫後的形式） | 自動：同上 |
| TC-011 【機器可驗】 | 作法 (2)；B1 | 功能 | 同 TC-009 | 分別以 zh、en 載入 `/launch` 與 `/settings` | 兩頁在 zh、en 都含 `class="linkbar"`、agent 名與 `WSL` | 自動：同上 |
| TC-012 【機器可驗】 | 作法 (2)、環境事實（所有頁都經 `_frame`） | 功能 | 同 TC-009 | 載入 usage、upload、downstream 三種頁 | 每一頁頂端都有 `class="linkbar"` 紅條 | 自動：同上 |
| TC-013 【機器可驗】 | 作法 (2)；裁決 9 | 功能 | u1 兩個 agent `desktop`、`desktop-gcb` 都 closed | 載入 `/` | 每個 agent 各一個 `<div class="linkbar" role="alert">`（共 2 個，一行一個），各自含自己的 agent 名 | 自動：同上 |
| TC-014 【機器可驗】 | 作法 (2)；B2 | 例外 | agent 自報 `open`（新鮮） | 載入 `/` | HTML 不含 `linkbar`，且與「掉線清單為空時」的輸出逐字相同（不多一個空 div） | 自動：同上 |
| TC-015 【機器可驗】 | 作法 (2)；B2 | 例外 | agent 自報 `unknown` | 載入 `/` | 同 TC-014：無 `linkbar`，逐字相同 | 自動：同上 |
| TC-016 【機器可驗】 | 作法 (2)；B2 | 例外 | agent 的 closed 已過期（超過 3 次心跳） | 載入 `/` | 同 TC-014：無 `linkbar`，逐字相同 | 自動：同上 |
| TC-017 【機器可驗】 | 完成標準（網頁畫面證據）；「agent 回 open 後紅條消失」 | 功能 | agent 先自報 closed（頁面有紅條） | agent 再自報 `open`，重新載入 `/` | 紅條消失，HTML 不含 `linkbar` | 自動：同上 |
| TC-018 【機器可驗】 | 作法 (2)；B3；專長守則（跨使用者讀） | 例外 | u1 的 agent closed；u2 登入且 u2 自己的 agent 都是 open | u2 載入 `/` | u2 看不到紅條，頁面也不含 u1 的 agent 名 | 自動：同上 |
| TC-019 【機器可驗】 | 作法 (2)（預設空，登入頁等為空） | 例外 | 有 agent closed，未登入 | 載入登入頁 | 沒有紅條 | 自動：同上 |
| TC-020 【機器可驗】 | 作法 (2)；B4 | 例外 | agent 名含 `<`、`"`（嘗試放進紅條） | 載入 `/` | 名稱先過與 agent 命名相同的字元限制，並經 `esc()`；HTML 中不出現原樣的 `<` 或 `"` 片段（不可被注入標籤） | 自動：同上 |
| TC-021 【機器可驗】 | 作法 (2)；`test_refusal_visibility.py` TC-007 | 功能 | 有 agent closed | 載入 `/`，並掃描 platform 非測試原始碼 | 紅條 HTML 不含 `ControlPersist`；`platform/` 非測試原始碼除 `jobs.py` 外沒有新增 `ControlPersist` | 自動：`platform/tests/test_site_disconnect_ux.py`、`platform/tests/test_refusal_visibility.py` |
| TC-022 【機器可驗】 | 作法 (2)；裁決 5、8 | 功能 | 同時有 `devbar` 與掉線 | 載入頁面 | `linkbar` 在 `devbar` 之後、主版面（`wb`）之前，滿寬一列；class 是 `linkbar` 不是 `devbar`；頁面中 `<div class="devbar"` 的數量與沒有掉線時相同 | 自動：同上 |
| TC-023 【機器可驗】 | 裁決 9（符號＋文字＋顏色） | 功能 | 有 agent closed | 載入 `/` | 紅條結構為 `<div class="linkbar" role="alert"><span aria-hidden="true">✗</span><span>…文字…</span></div>`；同時含 ✗、文字、`role="alert"`；不用「!」；符號不在 `STRINGS` 字串裡 | 自動：同上 |
| TC-024 【機器可驗】 | 作法 (2)；裁決 5 | 功能 | 讀 `web_board.STRINGS` | 檢查鍵 `linkbar_down` | zh、en 兩種語言都有，內容與計畫 (2) 原文逐字相同，且不含驚嘆號 | 自動：同上 |
| TC-025 【機器可驗】 | 裁決 8 | 功能 | 讀 `web_board.STYLE` | 取出 `.linkbar` 規則 | 含 `var(--failed-bg)` 與 `var(--failed)`；不含 `--lost`；不含任何色碼字面值（如 `#xxxxxx`、`rgb(`）；不用左側色條（無 `border-left`）；版面為 flex、gap 8px、padding 8px 16px、font-weight 600；`.devbar` 規則不變 | 自動：同上 |
| TC-026 【機器可驗】 | 裁決 10 | 功能 | 讀 `web_board.py` 的 CSS 變數表 | 檢查 `prefers-color-scheme: dark` 區段 | 深色區段已有 `--failed` 與 `--failed-bg`；`.linkbar` 沒有自帶色碼、沒有新增的深色區段 | 自動：同上 |
| TC-027 【機器可驗】 | 裁決 5 | 功能 | 讀 `.linkbar` 規則與紅條 HTML | 檢查位置與互動 | 沒有 `position:fixed`／浮動；沒有關閉按鈕或 JS；不在右欄；連線恢復前一直顯示 | 自動：同上 |
| TC-028 【機器可驗】 | 裁決 5（寬度） | 功能 | 兩個 agent 掉線（含長名稱）；用瀏覽器（Playwright）渲染 `/` | 寬度 1440 與 390 px 各量一次 | 兩種寬度都沒有水平捲動（`scrollWidth <= clientWidth`） | 自動：審查者以 `scripts/ui_check.py` 或 Playwright 實跑 |
| TC-029 【機器可驗】 | 專長守則（ui）：文字檢查 | 功能 | 把有紅條的 `/` 渲染成 zh、en 兩個 HTML 檔 | 執行 impeccable 偵測器 `detect <file.html>` | 偵測器違規為零或已處理；有未處理的違規判不通過 | 自動：審查者實跑偵測器 |
| TC-030 【機器可驗】 | 專長守則（ui）；裁決 5 | 功能 | 應用程式用假資料起起來，agent 自報 closed | 1440／390 寬 × zh／en 共 4 張截圖，並跑 axe | axe 沒有 serious 或 critical；截圖存在 repo 之外或被 `.gitignore` 排除的資料夾 | 自動：審查者實跑 |
| TC-031 【機器可驗】 | 完成標準（網頁畫面證據） | 功能 | 讀 `specs/mcp-site-keepalive-disconnect-ux/ledger.md` | 檢查畫面證據段 | ledger 寫了 zh 與 en 紅條截圖的檔名與看到的字，以及「agent 回 open 後紅條消失」的紀錄 | 自動：讀 ledger |
| TC-032 【實機驗】 | 裁決 5、6（無核可草稿，以 `DESIGN.md` 為依據）；原話「連線狀態可見＋掉線時明確提示」 | 功能 | 合併後，維護者拿到 zh／en × 1440／390 共 4 張真實畫面截圖 | 維護者親眼看頂端紅條 | 他看得出「站台連線掉了、要去哪台機器的 WSL 做什麼、已在跑的 run 不受影響」，且畫面符合 `DESIGN.md` 的失敗狀態色、符號與用字。他回「不好」則另開修正件，本件不因此退回 | 手動：維護者看截圖（依裁決 6 列入每日清單）；通過＝他沒有回「不好」 |

## User Story 2 — 掉線時送出新 run 會被擋下，並說明怎麼恢復（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 【機器可驗】 | 作法 (3)；M1；原話「掉線時明確提示」 | 功能 | u1 的 agent `desktop` 新鮮 closed，u1 有一個待確認的 launch 申請（目標 agent `desktop`） | 人按 yes（`approve`） | 得到 `NotApproved("failed", message)`；message 以 `No open connection to the site` 開頭，含 agent 名 `desktop` 與 `WSL`，長度 ≤ 300 字元 | 自動：`platform/tests/test_site_disconnect_ux.py` |
| TC-034 【機器可驗】 | 作法 (3)；目標「訊息明講請在哪台機器的 WSL 重新登入」 | 功能 | 同 TC-033 | 讀 message | 含「連線已掉，請在執行 agent「desktop」那台機器的 WSL 終端機重新登入，再重新送出」與「已在跑的分析不受影響」（zh 用「分析」，不含「run」；en 為 runs already going are not affected） | 自動：同上 |
| TC-035 【機器可驗】 | 作法 (3)(4)；M2 | 功能 | 同 TC-033，refusal 訊息已存進被拒的申請列 | 把訊息送過 `jobs._first_sentence`／`_refusal_of_row` | 結果仍含 agent 名 `desktop`，且分類為 `site_down`（既有「站台連線沒開」分類照常運作） | 自動：同上 |
| TC-036 【機器可驗】 | 作法 (4)；M3；原話「掉線時明確提示」 | 功能 | 經 MCP `launch` 取得表單，人答 yes | 讀 MCP 回覆 | 回覆含機器名與 `WSL`，整句原樣出現，沒有被 `REFUSAL_LIMIT=300` 或 `_first_sentence` 截掉 | 自動：同上 |
| TC-037 【機器可驗】 | 作法 (4)（MCP 與網頁都顯示） | 功能 | 同 TC-033，改走網頁確認頁按下確認 | 讀網頁回應 | 網頁顯示整句，含 agent 名與 `WSL` | 自動：同上 |
| TC-038 【機器可驗】 | 作法 (3)（單一入口：web 按鈕、MCP 表單 yes、終端機 `abf-platform launch`） | 功能 | 同 TC-033，改走終端機 `abf-platform launch` 的 yes | 送出 | 同樣被擋、訊息同 TC-033 | 自動：同上 |
| TC-039 【機器可驗】 | 作法 (3)；`mcp_server.py` 的 `launch`、`launch_pipeline`、`relaunch`、`resume` | 功能 | agent closed；分別以 `launch_pipeline`、`relaunch`、`resume` 產生待確認申請 | 各自按 yes | 四種都被擋，訊息含 agent 名與 `WSL` | 自動：同上 |
| TC-040 【機器可驗】 | 作法 (3)（`confirm.approve` 標為 void 並帶原因） | 功能 | 同 TC-033 | 按 yes 被擋後查資料 | 該申請被標為 void 且帶原因；`jobs` 沒有新增任何列 | 自動：同上 |
| TC-041 【機器可驗】 | 作法 (1)；測試 14 | 例外 | agent 自報 `open` | 對該 agent 送出 launch 並按 yes | 照舊成功入列（不誤擋） | 自動：同上 |
| TC-042 【機器可驗】 | 作法 (1)；測試 14 | 例外 | agent 的 `site_link` 為 `unknown` | 同上 | 照舊成功入列 | 自動：同上 |
| TC-043 【機器可驗】 | 作法 (3) | 例外 | u1 有 `desktop`（closed）與 `desktop-gcb`（open） | 對 `desktop-gcb` 送出 launch 並按 yes | 成功入列；只有目標 agent 掉線才擋 | 自動：同上 |
| TC-044 【機器可驗】 | 作法 (1)(3)；專長守則（跨使用者） | 例外 | u1 的 agent closed；u2 的 agent open | u2 對自己的 agent 送出 launch 並按 yes | 成功入列，不受 u1 的掉線影響 | 自動：同上 |
| TC-045 【機器可驗】 | 作法 (3)（開頭必須維持 `jobs.SITE_DOWN`） | 功能 | 讀 `jobs.SITE_DOWN`；被擋的申請在網頁「失敗」頁 | 檢查常數與頁面 | `jobs.SITE_DOWN == "No open connection to the site"`；既有「站台連線沒開，工作沒有送出」頁面分類仍適用於新訊息 | 自動：同上，加 `platform/tests/test_refusal_visibility.py` |
| TC-046 【機器可驗】 | 作法 (3)(4)；專長守則（錯誤訊息） | 例外 | agent 名取命名規則允許的最長長度，且 closed | 按 yes 被擋 | 訊息仍 ≤ 300 字元，含原因與處理方式；不含堆疊、內部路徑、SQL；不含密鑰 | 自動：同上 |

## User Story 3 — 掉線不影響已在跑的 run，恢復後能重送（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 【機器可驗】 | 作法 (3)；R1；原話「我最基本的要求」 | 功能 | 已有一個 running 的 run；記下 `get_run` 結果、`launches` 列、既有 job 列 | agent 變成 closed 後再取一次 | `get_run` 狀態、`launches` 列、既有 job 與之前完全相同（diff 為空） | 自動：`platform/tests/test_site_disconnect_ux.py` |
| TC-048 【機器可驗】 | 作法 (3)（不改 `launches`、run 狀態、`lost` 判定、Beat） | 功能 | 讀 `git diff <base>...HEAD` | 檢查 | 沒有改動 `launches`、run 狀態、`lost` 判定或 Beat 的程式；`jobs.py` 只在 `launch_nextflow` 分支加一個檢查 | 自動：讀 diff |
| TC-049 【機器可驗】 | 作法 (3)；R2 | 功能 | agent closed，有一個可取消的 run | 送出 `cancel` | 照舊 enqueue，沒有被本檢查擋 | 自動：同 TC-047 的測試檔 |
| TC-050 【機器可驗】 | 作法 (3)；R2 | 功能 | agent closed | 送出 `fetch` | 照舊 enqueue，沒有被本檢查擋 | 自動：同上 |
| TC-051 【機器可驗】 | 作法 (3)；R2 | 功能 | agent closed | 送出 `read_task_log` | 照舊 enqueue，沒有被本檢查擋 | 自動：同上 |
| TC-052 【機器可驗】 | 作法 (3)；R3 | 功能 | launch 因 closed 被擋（申請 void） | agent 回報 `open`，使用者重新呼叫 launch 並按 yes | 成功入列（恢復後可重新送出） | 自動：同上 |

## User Story 4 — 開連線指令改成長效保活（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-053 【機器可驗】 | 作法 (5)；K1；原話「不要只有 8hr，可以更久就改」 | 功能 | 用假 ssh（`ON_SITE_SSH_BIN`，比照 `tests/on_site_test.sh` 的 `no_master_run`）讓 `on_site.sh` 走到沒有 master 的分支 | 取得印出的開連線那一行 | 含 `ControlPersist=yes`、`ServerAliveInterval=60`、`ServerAliveCountMax=10`；不含 `ControlPersist=8h` | 自動：`platform/tests/test_site_disconnect_ux.py` |
| TC-054 【機器可驗】 | 作法 (5)；K1 | 功能 | 同 TC-053，另取含 `wsl.exe -e` 前綴的版本 | 把行送進 `jobs.valid_open_command(line, host)` | 兩個版本都回傳非 None（`jobs.valid_open_command` 本身未被修改） | 自動：同上 |
| TC-055 【機器可驗】 | 作法 (5)（兩處同一條） | 功能 | 執行 `scripts/reset_master.sh`（假 ssh） | 取印出的重連線那一行，與 `on_site.sh` 印的比較 | 兩者開連線指令相同，且含 TC-053 的三個選項 | 自動：`tests/reset_master_test.sh` |
| TC-056 【機器可驗】 | 作法 (5)（說明文字同步改） | 功能 | 讀 `scripts/on_site.sh` 與 `scripts/reset_master.sh` 的說明文字 | 檢查字句 | 不再宣稱「8h」；註明存活上限由 `scripts/keepalive_log.sh` 的 log 量測；仍保留「`wsl --shutdown`、機器睡眠會終止」的既有事實 | 自動：讀檔（grep） |
| TC-057 【機器可驗】 | 作法 (5)；範圍：檔案 | 功能 | 讀 `scripts/on_site.sh` 的 diff 並跑既有 shell 測試 | 檢查 | 只有 `no_master()` 的那一行與其說明改動；`master_is_up`、`--check-master` 與其他分支不變；`tests/on_site_test.sh`、`tests/on_site_parallel_test.sh` 仍綠 | 自動：讀 diff＋`bash tests/on_site_test.sh`、`bash tests/on_site_parallel_test.sh` |
| TC-058 【機器可驗】 | 允許更新的既有斷言 | 功能 | 讀 `tests/reset_master_test.sh` 的 diff | 檢查第 32 行 | 期望由 `ControlPersist=8h` 改為 `ControlPersist=yes`；該檔其他斷言沒有被放寬；測試綠 | 自動：`bash tests/reset_master_test.sh`＋讀 diff |
| TC-059 【機器可驗】 | 作法 (5)；裁決 1（平台不存樣板） | 功能 | 讀 `jobs.py` diff；跑 `test_refusal_visibility.py` | 檢查 | `_OPEN_COMMAND*` 與 `valid_open_command` 未動；platform 非測試原始碼（`jobs.py` 例外）沒有新增 `ControlPersist`；TC-007／008／094 仍綠 | 自動：`platform/tests/test_refusal_visibility.py`＋讀 diff |
| TC-060 【機器可驗】 | 作法 (5)；環境事實（不宣稱改了就不會掉） | 功能 | 讀 on_site.sh、reset_master.sh、紅條字串、docs 新增字句 | 搜尋「不會掉」「永不」「保證」「never」之類宣稱 | 沒有宣稱「改了就不會掉」；只說「已延長偵測容忍並開始量測」；沒有宣稱特定存活時數 | 自動：讀 diff（grep） |

## User Story 5 — WSL 內的保活記錄程式，量出國網真實存活上限（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-061 【機器可驗】 | 作法 (6)；K2 | 功能 | `ABF_KEEPALIVE_ONCE=1`；以環境變數指向假 `on_site.sh`（回 0）；`ABF_KEEPALIVE_LOG` 指到暫存檔 | 執行 `scripts/keepalive_log.sh` | log 恰好一行，含 `master=open rc=0` | 自動：`tests/keepalive_log_test.sh` |
| TC-062 【機器可驗】 | 作法 (6)；K2 | 功能 | 同 TC-061，假 `on_site.sh` 回 1 | 執行 | log 一行含 `master=closed rc=1` | 自動：同上 |
| TC-063 【機器可驗】 | 作法 (6)（格式） | 功能 | 同 TC-061 | 檢查那一行 | 空白分隔的 key=value：`ts=` 為含時區的 ISO8601、`machine=` 為 hostname、`master=`、`rc=`；一筆一行 | 自動：同上 |
| TC-064 【機器可驗】 | 作法 (6)；K3 | 功能 | 連續兩輪：假 `on_site.sh` 先回 0 再回 1（可用極短間隔） | 執行並讀 log | 第二輪另寫一行含 `event=closed`、`lasted_min=`（自首次 open 起算的分鐘數）與 `last_open=`（ISO 時間） | 自動：同上 |
| TC-065 【機器可驗】 | 作法 (6)；K3 | 功能 | 連續幾輪：回 0、回 1、再回 0 | 執行並讀 log | 由 closed 轉回 open 時寫一行 `event=reopened` | 自動：同上 |
| TC-066 【機器可驗】 | 作法 (6)；K3 | 功能 | log 檔已超過 1 MB | 執行一輪 | 舊檔被改名為 `.1`（只留一份），新檔接著寫 | 自動：同上 |
| TC-067 【機器可驗】 | 作法 (6)（不得自寫 `ssh -O check`）；PITFALLS 16e、57 | 功能 | 假 `on_site.sh` 會記錄收到的參數；假 `ssh` 若被叫就記錄 | 執行 | 只呼叫 `on_site.sh --check-master`；假 `ssh` 完全沒被呼叫；腳本內容沒有自己的 `ssh` 指令 | 自動：同上 |
| TC-068 【機器可驗】 | 作法 (6) | 功能 | 沒設環境變數 | 連呼叫 `keepalive_log.sh` 兩次（第二次偵測到 closed）並檢查腳本 | 單次執行：每呼叫一次只檢查一次連線、追加一行 log，並從 log 最後一筆算 open→closed 存活分鐘，第二次偵測到 closed 時寫 event 行；預設 log 為 `$HOME/.abf/keepalive.log`（`ABF_KEEPALIVE_LOG` 可覆寫）；腳本不含 while／loop／nohup／sleep 常駐，也不在 `DAEMON_ALLOW` 內 | 自動：同上 |
| TC-069 【機器可驗】 | 作法 (6)（`kill` 即停；不自動啟動） | 功能 | 呼叫 `keepalive_log.sh` 一次 | 查腳本結束行為與平台、agent 程式碼 | 呼叫後程序自行結束（無常駐、無需 `kill`）；平台與 agent 的程式碼沒有任何地方啟動 `keepalive_log.sh` | 自動：`tests/keepalive_log_test.sh`＋讀 diff |
| TC-070 【機器可驗】 | 作法 (6)（不開連線、不輸入 OTP、不寫憑證） | 功能 | 讀腳本與跑出的 log | 檢查 | 腳本不開連線、不要求也不寫 OTP；log 內容只有 ts、machine、master、rc、event、lasted_min、last_open，沒有任何憑證 | 自動：同上 |
| TC-071 【機器可驗】 | 作法 (6)（不放進 `platform/abf_station/`） | 功能 | 看新檔位置並跑 `test_station_static.py` | 檢查 | 檔案在 `scripts/keepalive_log.sh`；`platform/tests/test_station_static.py` 的 tc087（站台原始碼無 ssh／ControlPersist）仍綠 | 自動：`platform/tests/test_station_static.py` |
| TC-072 【機器可驗】 | 完成標準（實演 `keepalive_log.sh`） | 功能 | 讀 ledger | 檢查 | ledger 貼了一段真的跑出來的 log，並標明是用假 `on_site.sh` 的模擬 | 自動：讀 ledger |

## User Story 6 — 文件與既有測試跟著新行為（優先度 P3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-073 【機器可驗】 | 範圍：文件；完成標準 | 功能 | 讀 `docs/PLATFORM.md` | 檢查指令範例與說明 | 不再有「ControlPersist=8h keeps the connection for the day」與「at most 8 hours」；指令範例是新的保活指令；說明為「由人手動或既有排程呼叫一次 `bash scripts/keepalive_log.sh`」，不含 `nohup`、不宣稱常駐 | 自動：讀檔（grep） |
| TC-074 【機器可驗】 | 範圍：文件 | 功能 | 讀 `docs/SITE_ADAPTER.md` 約 148～150 行 | 檢查 | 開連線指令與說明與新行為一致，不再宣稱 8h | 自動：讀檔（grep） |
| TC-075 【機器可驗】 | 完成標準（PITFALLS 新增一條） | 功能 | 讀 `docs/PITFALLS.md` | 檢查新增條目 | 有 Symptom／Root cause／Check／Touches 四欄；內容說連線存活上限未知、`keepalive_log.sh` 的用法、`event=closed lasted_min` 的讀法、`ControlPersist=yes` 不等於永不掉 | 自動：讀檔 |
| TC-076 【機器可驗】 | 允許更新的既有斷言（文件測試） | 功能 | 跑 `test_onboarding_doc.py`、`test_station_docs.py`、`test_launch_docs.py` | 執行 | 仍綠；若有改動只改被釘住的那一句 | 自動：這三個測試檔＋讀 diff |
| TC-077 【機器可驗】 | 允許更新的既有斷言；弱化測試規則 | 功能 | 對照 base，列出 diff 中所有改動的既有測試檔 | 逐一比對 | 既有測試只有計畫「允許更新」清單內的斷言被改（`reset_master_test.sh:32`、`STYLE_SHA256`、`test_refusal_visibility.py:138`、`tools.json` 與釘 description 的行）；沒有移除、放寬、跳過其他斷言 | 自動：讀 diff |
| TC-078 【機器可驗】 | 允許更新的既有斷言 | 功能 | 新增 `.linkbar` 規則後 | 跑 `test_results_files.py` 與 `test_web_downstream.py` | `STYLE_SHA256` 已重算並更新，兩個測試綠 | 自動：兩個測試檔 |
| TC-079 【機器可驗】 | 允許更新的既有斷言；裁決 4 | 功能 | 讀 `test_refusal_visibility.py` 第 138 行附近 | 檢查 | 該行不再斷言 `site_link` 不存在；`abf-station connect`、`abf-connect://` 的斷言保留；122、133、165、167 行未動；全檔綠 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-080 【機器可驗】 | 作法 (2)（class 用 `linkbar`，不可用 `devbar`） | 功能 | 跑 `platform/tests/test_web_settings_personal.py` | 執行 | devbar 計數（237、254、366、418–419 行）斷言不變且仍綠 | 自動：該測試檔 |
| TC-081 【機器可驗】 | 作法 (4)；`mcp_server.py` | 功能 | 讀 `platform/tests/mcp/snapshots/tools.json` 與 `mcp_server.py` | 檢查 `launch`、`launch_pipeline`、`relaunch`、`resume` 的 description | 四個都多了一句「站台連線掉線時會被擋」；其他工具 description 不變；MCP 契約測試綠 | 自動：`platform/tests/mcp/test_mcp_contract_tools.py`、`test_mcp_contract_writes.py` |
| TC-082 【機器可驗】 | 允許更新的既有斷言（22 工具集合） | 功能 | 跑 `test_aws_ce`、`test_azure_ce`、`test_gcb_ce`、`test_aws_launch`、`test_azure_launch`、`test_azure_upload`、`test_gcb_launch`、`test_dataset_launch` | 執行 | 全綠，且這些檔沒有被改動（動到就是多加了工具） | 自動：上列測試檔＋讀 diff |
| TC-083 【機器可驗】 | 完成標準（完整 `platform/tests` 與 shell 測試綠） | 功能 | 完成標記 `GREEN <HEAD sha>`、工作樹乾淨 | 檢查完成標記；`tests/keepalive_log_test.sh` 與 `tests/reset_master_test.sh` 在 shell 測試中被執行 | 完整套件在 HEAD 全綠，新舊測試都在其中 | 自動：`tests/run_all.sh`（在 WSL；由 gate 標記與 CI 判定） |

## 不在範圍（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-084 【機器可驗】 | 不做：不在表單產生當下預檢 | 不在範圍 | agent closed | MCP 呼叫 `launch`（尚未按 yes） | 表單／待確認申請照常產生，沒有被拒；擋下只發生在按 yes 之後（`enqueue_confirmed`） | 自動：`platform/tests/test_site_disconnect_ux.py` |
| TC-085 【機器可驗】 | 不做：不擋 cancel、fetch、讀 log／讀檔、preflight（作法 (3)） | 不在範圍 | agent closed | 呼叫 `clean_work`、`read_run_file`、`list_site_files`、`preflight` 的路徑 | 路徑完全沒有新增本檢查；遇斷線走既有錯誤訊息（TC-049～TC-051 另證 cancel、fetch、read_task_log） | 自動：同上，加讀 diff |
| TC-086 【機器可驗】 | 不做：不新增 MCP 工具 | 不在範圍 | 列出 MCP 工具 | 計算工具數 | 仍為 22，沒有新增工具 | 自動：`platform/tests/mcp/` 契約測試 |
| TC-087 【機器可驗】 | 不做：不在查詢或送出時登入、重試、等待連線；不代人輸入 OTP；不自動啟動 `keepalive_log.sh` | 不在範圍 | agent closed，假 ssh 會記錄被呼叫 | 按 yes 送出 launch | 立刻被拒、不等待、不重試；沒有任何 ssh 或 OTP 動作；平台與 agent 沒有啟動 `keepalive_log.sh` | 自動：`platform/tests/test_site_disconnect_ux.py`＋讀 diff |
| TC-088 【機器可驗】 | 不做：不改 `platform/abf_station/`；風險 M 前提 | 不在範圍 | 讀 `git diff origin/v3 --name-only`（或 `<base>...HEAD`） | 檢查檔案清單 | 沒有 `platform/abf_station/`、`.github/`、`hooks/`、`constitution.md`、`plugin.json`（有就必須升 L） | 自動：讀 diff 清單 |
| TC-089 【機器可驗】 | 不做：不重做 mcp-site-connection-status | 不在範圍 | 讀 diff；跑 `test_site_connection_status.py`、`test_station_site_link.py`、`test_station_realpath_down.py` | 檢查 | 沒有改動 `actions/__init__.py`、`common.py`、`agents.py`、`compute_envs.py`、`su.py`；`site_link` 欄位、`--check-master`、`run_outputs`／`list_site_files` 訊息、SU 修正未被重做；`site_unreachable` 沒被改回「路徑被拒」；測試綠 | 自動：上列測試檔＋讀 diff |
| TC-090 【機器可驗】 | 不做：不改資料結構 | 不在範圍 | 讀 diff | 搜尋 | 沒有 `CREATE TABLE`、`ALTER TABLE`、migration | 自動：讀 diff（grep） |
| TC-091 【機器可驗】 | 不做：不依 log 自動調整參數 | 不在範圍 | 讀 `keepalive_log.sh` | 檢查 | 腳本只記錄，不改 `on_site.sh` 的指令、設定或任何參數 | 自動：讀腳本＋`tests/keepalive_log_test.sh` |
| TC-092 【機器可驗】 | 不做：不讓任何週期動作多開 session（PITFALLS 16e、57） | 不在範圍 | 跑 `tests/preflight_ssh_fold_test.sh`、`tests/on_site_parallel_test.sh` | 執行 | 仍綠；週期動作只有零 session 的 `--check-master` | 自動：上列測試檔 |

## 憲法與安全網

<!-- 本件碰到：確認管道（寫入工具須經人的 yes）、憑證不外洩（Safety Net）、擁有者規則（專長守則）。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-093 【機器可驗】 | Safety Net：寫入工具須經人的 yes（確認管道 TC） | 例外 | 未經確認的 launch 申請，agent closed 與非 closed 各一 | 在沒有人確認的情況下嘗試送出 | 仍然拒絕、資料不變；既有的 `test_actions_layer.py`（`test_tcb04_*`～`test_tcb08_*`）、`test_human_channel.py`、`test_chat_confirm.py` 仍綠且未被放寬 | 自動：上列測試檔 |
| TC-094 【機器可驗】 | Safety Net：確認管道不被新路徑繞過 | 功能 | 讀 `jobs.enqueue_confirmed` 的 diff | 檢查新增檢查的位置 | 檢查在 `launch_nextflow` 分支、`name_problem` 之後、`_insert_job` 之前；沒有新增任何不經確認就能入列的路徑 | 自動：讀 diff＋`platform/tests/test_site_disconnect_ux.py` |
| TC-095 【機器可驗】 | Safety Net：憲法、確認流程、`cancel` 流程零 diff | 功能 | 讀 `git diff` | 檢查 | `rules`、確認流程、`cancel` 流程與憲法檔零 diff；`git diff --stat` 已貼進 ledger | 自動：讀 diff＋ledger |
| TC-096 【機器可驗】 | Safety Net：憑證不外洩（錯誤訊息與日誌 TC） | 例外 | 掉線被擋；跑 `keepalive_log.sh`；渲染紅條 | 檢查回應、網頁、log | 拒絕訊息、紅條、keepalive log 都不含密鑰、token、OTP 或憑證 | 自動：`platform/tests/test_site_disconnect_ux.py`、`tests/keepalive_log_test.sh` |
| TC-097 【機器可驗】 | 專長守則：對等性（網頁動作與動作層函式一一對應） | 功能 | 本件不新增網頁路由或動作 | 跑既有的動作對等性測試 | 仍綠；紅條由 `_frame` 畫、擋送由 `jobs.enqueue_confirmed` 做，路由處理函式裡沒有第二份邏輯 | 自動：`platform/tests/test_actions_layer.py`＋讀 diff |
| TC-098 【機器可驗】 | 專長守則：跨使用者（寫） | 例外 | u1 的 agent closed，u1 有待確認申請；u2 用自己的身分 | u2 對 u1 的申請 approve | 被拒（沿用既有擁有者規則）；u1 的資料不變；訊息不洩漏 u1 的 agent 名 | 自動：`platform/tests/test_site_disconnect_ux.py` |
