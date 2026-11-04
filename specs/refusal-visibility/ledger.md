# 預檢被拒要讓 AI 與網頁看得到原因與連線指令 progress ledger

- [x] 站台：`rules.Refusal.open_command`、`rules.open_command_in`、`launch._prechecks`、`handlers._refused` 帶出 `open_command`（只在 no-master 時）
- [x] 平台：`jobs.valid_open_command`／`host_of`／`clean_result(host=)`／`take_result` 查 CE hostName；`refusal_of`、`latest_refusal`
- [x] 網頁：`web_board.refusal_block`（確認頁與看板共用）、`web.state_page`、`web.board_page`；STRINGS 新增 `refusal_*` 四個 zh／en 鍵，沒有 `refusal_queued_note`
- [x] 文件：PLATFORM.md、TESTING.md（手動步驟、截圖步驟、閱卷證據步驟）、CHANGELOG.md
- [x] 截圖四張（1440／390、zh／en）到 `screens/`，另附看板兩張；用本機 Chrome 無頭模式截的，見下方「閱卷證據」第 4 項

## 做法備註
- 指令取自 connect 檢查 detail 結尾（即 `connect_failure` 逐字放進去的 `_open_command` 結果），沒有改 verdict 形狀。
- `clean_result` 沒有 CE，所以加 `host=` 參數，由 `take_result` 查 `compute_envs.config_json`。
- 憲法與 no-touch 清單內的檔案都沒動；沒有加 `nchc_t3c4`／`u9613010`／`ControlPersist=12h`／`site_login_command`。
- 修了一個自己寫出的退格字元（`\b` 變成 0x08），已改回並查過其他檔案沒有。

## 閱卷證據（TC-086；TC-076、TC-078、TC-085 的證據也在這裡）

### 1. TC-006：on_site.sh 實際輸出行與頁面指令並列
做法：真的 `scripts/on_site.sh true`，`ON_SITE_SSH_BIN` 指向永遠 `exit 255` 的假 ssh（比照 `tests/on_site_test.sh` 的 `no_master_run`），`site_host: me@example.org`。該輸出經真的站台 `handlers.handle`，再由 `jobs.take_result` 存進平台，最後由確認頁 `/c/<id>` 讀出。CE hostName 設為 example.org。
```
on_site.sh 印出的那一行 : ssh -o ControlMaster=auto -o ControlPath=/.ssh/cm-%r-%h-%p -o ControlPersist=8h -o ServerAliveInterval=60 me@example.org true
站台結果 open_command   : ssh -o ControlMaster=auto -o ControlPath=/.ssh/cm-%r-%h-%p -o ControlPersist=8h -o ServerAliveInterval=60 me@example.org true
頁面 <pre>（zh）         : ssh -o ControlMaster=auto -o ControlPath=/.ssh/cm-%r-%h-%p -o ControlPersist=8h -o ServerAliveInterval=60 me@example.org true
頁面 <pre>（en）         : ssh -o ControlMaster=auto -o ControlPath=/.ssh/cm-%r-%h-%p -o ControlPersist=8h -o ServerAliveInterval=60 me@example.org true
```
四行逐字相同（跑的腳本內 `assert pre == line` 通過）。ControlPath 開頭是 `/.ssh/`，是因為假環境沒有 HOME；真環境由 on_site.sh 自己展開，頁面照搬，不自己組。自動測試：`test_tcr006_the_command_is_the_line_on_site_prints`（`platform/tests/test_refusal_visibility.py:99`）、`test_tcr029_*`。

### 2. 平台沒有硬寫的指令樣板（grep）
對 `platform/` 非測試的原始碼搜 `ControlMaster=yes`、`ControlPersist`、`nchc_t3c4`、`u9613010`、`ControlPersist=12h`、`site_login_command`、`site_link`、`abf-connect://`：0 筆（`platform/abf_platform` 裡 `ControlPersist` 也是 0 筆）。自動測試：TC-007、008、090、091、094（同一測試檔）。

### 3. PITFALLS 重查（`docs/PITFALLS.md`；`docs/solutions/` 不存在；本分支沒有改 PITFALLS）
重新 grep `web.py`、`jobs.py`、`clean_result`、`state_page`、`open_command`、`refusal`、`no-master`：沒有新增、與計畫不同的相符項（相符行都是別片的 refusal 字樣，如 20h、cap）。計畫列的四項仍適用，處理如下：
- realpath-site-down（2026-10-30）：站台訊息文字沒改，只加結果鍵；`test_station_realpath_down.py` 在全套內綠。
- 16b／16g（Windows 兩個原生 shell 不能 multiplex）：指令原樣顯示，含 `wsl.exe -e` 前綴時不拆；頁面文字叫人在 WSL 終端機貼。`tests/on_site_test.sh` 在全套內綠（`on_site.sh` 零 diff）。
- 16e（同一 master 太多呼叫會掛）：`sessions-exhausted` 不帶 `open_command`，頁面不顯示登入指令（TC-004、TC-032）。
- wsl.exe／ControlPath：不自創，指令只取 on_site.sh 印出的那一行（上面第 1 項）。

### 4. TC-062：截圖逐張（`specs/refusal-visibility/screens/`，Chrome 無頭模式；測試平台造 refused 加合格 open_command 的 launch job）
390 寬的檔案是把頁面放進 `<iframe width=390>` 截的（無頭 Chrome 的視窗不能比約 500 窄），所以右邊多一條灰色，不是頁面的一部分。
- `confirm-1440-zh.png`：標題「送出確認」；紅字「站台連線沒開，工作沒有送出。」；「平台主機 agent-t。請在 WSL 終端機貼上這一行，輸入 passphrase 與 OTP，然後重新呼叫 launch。」；灰底框內一行 ssh 指令，折成兩行；下方是請求摘要。沒有「已送出」。
- `confirm-1440-en.png`：同上英文：「The connection to the site is not open; nothing was submitted.」「station host agent-t: paste this line into a WSL terminal, enter your passphrase and OTP, then call launch again.」，框內同一行指令。沒有「已送出」。
- `confirm-390-zh.png`：同樣的字，指令在框內折成四行，全在畫面內，沒有橫向捲動。
- `confirm-390-en.png`：同樣的英文字，指令折成四行，全在畫面內。
- `board-1440-zh.png`（可選）：看板中欄頂端同一塊原因與指令，下面接「尚無分析」。
- `board-390-en.png`（可選）：窄版看板同一塊，下面接 No analyses yet。

量測（Chrome 無頭，注入 script）：390 寬時 `document.documentElement.scrollWidth` = 390，`<pre>` 的 scrollWidth = clientWidth = 342，即不橫向捲動（中英都是）；1440 寬（無頭視窗扣掉捲軸為 1424）scrollWidth = 1424，同樣沒有橫向捲動（TC-064）。四張確認頁的 HTML 都不含「已送出」（TC-063）。沒有跑的：TC-065（axe）；TC-070 的用語我只能自己看過，請閱卷端的人讀這四張圖。

### 5. TC-076：不准動清單
`git diff origin/v3 --name-only -- platform docs scripts hooks .github` 只列出：`docs/PLATFORM.md`、`docs/TESTING.md`、`platform/abf_platform/jobs.py`、`web.py`、`web_board.py`、`web_refusal.py`、`platform/abf_station/handlers.py`、`launch.py`、`rules.py`、`platform/tests/test_refusal_visibility.py`、`platform/tests/test_web_settings_ce_mobile.py`。沒有 `confirm.py`、`actions/__init__.py`、`mcp_server.py`、`actions/chat_tools.py`、`guidance.py`、`store.py`、`compute_envs.py`、`scripts/on_site.sh`、`.github/`、`hooks/`、`plugin.json`、憲法。例外：`web_refusal.py` 是新檔，依計畫裁決 R 第 2 點核准（TC-H16f 不准 `web.py` 直接 import jobs，所以用這個薄層轉呼叫 `jobs.refusal_of`／`jobs.latest_refusal`）。

### 6. TC-078：檔案範圍
全部變動檔：`CHANGELOG.md`、`docs/PLATFORM.md`、`docs/TESTING.md`、`platform/abf_platform/{jobs,web,web_board,web_refusal}.py`、`platform/abf_station/{handlers,launch,rules}.py`、`platform/tests/test_refusal_visibility.py`、`platform/tests/test_web_settings_ce_mobile.py`、`specs/refusal-visibility/*`。都在計畫「範圍：檔案」之內，只有兩項超出計畫原文，兩項皆由裁決 R 核准：新檔 `web_refusal.py`、`test_web_settings_ce_mobile.py` 的 STRINGS 雜湊值（只換雜湊，沒有放寬斷言）。站台只動 `handlers.py`、`rules.py`、`launch.py` 的退回路徑（`_refused`、`Refusal.open_command`、`_prechecks`），沒有動別的站台檔。

### 7. TC-085：不需要 migration
`git diff origin/v3 -- platform` 搜 `CREATE TABLE`、`ALTER TABLE`、`migration`：0 筆。`store.py` 沒動。`result_json` 只多一個可選鍵 `open_command`，只在 launch_nextflow 的 refused 結果、且通過嚴格格式與 CE hostName 比對時才存；舊資料沒有這個鍵時頁面照舊。所以不需要 migration。

### 8. 其他
- TESTING.md 這次補了：沒有密碼／OTP 輸入框那句（TC-071）、截圖步驟、閱卷證據步驟；並還原我先前不小心把 `### Head job ended…` 改成 `##` 的標題層級。
- 全套本機：TC-032（`test_no_schema_change`）依裁決 R2 是環境假紅（WSL 鏡像的 origin/v3 過期），以 GitHub CI 為準。
- 開放給 maintainer 決定：連線指令格式是否再收緊（計畫的嚴格格式仍放行 `> < ( ) ' "` 等字元）。

### 9. TC-065：axe 無障礙掃描（axe-core 4.10.2，本機 Chrome 無頭 `--dump-dom`，注入 `axe.run(document)`；步驟已寫進 TESTING.md 手動節第 7 步）
掃的是測試平台造 refused 加合格 open_command 後存下的頁面（與第 4 項截圖同一批）。
- `/c/<id>` 中文：violations 0 筆，passes 19，incomplete 0。
- `/c/<id>` 英文：violations 0 筆，passes 19，incomplete 0。
- `/` 看板中文與英文（附帶掃）：3 筆，全不在退回區塊內：`meta-refresh`（critical，目標 `meta[http-equiv="refresh"]`，看板自動更新標籤，`origin/v3` 的 web_board.py 本來就有，本片沒動）、`landmark-unique`（moderate，`.side`）、`page-has-heading-one`（moderate，`html`），後兩者也是看板既有結構。本片要求的確認頁沒有 serious 或 critical。
- 看板那筆既有的 critical `meta-refresh` 不是本片造成，也不在本片範圍；留給 maintainer 另案決定。
