# 測試案例：refusal-visibility（站台因「沒有開著的連線」退回時，原因與開線指令送到網頁）

**規格**：`specs/refusal-visibility/plan.md`（本片沒有 spec.md；維護者原話在計畫「維護者原話」節，逐字引自 GitHub issue 349 與 T3）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「退回」＝站台收到工作、預檢沒過，回「沒送出」。「open_command」＝使用者要自己貼到終端機的那一行連線指令，由站台腳本 `scripts/on_site.sh` 印出，是唯一來源。「確認頁」＝網頁 `/c/<編號>`。「分析清單頁」＝網頁首頁 `/`。

自動測試放在 `platform/tests/test_refusal_visibility.py`，每個測試在註解寫上它對應的 TC 編號（測試名前綴 `test_tcr`）。夾具：站台測試參考 `test_station_realpath_down.py`（`NO_MASTER`、`OPEN_CMD`、`RELOGIN`），網頁測試參考 `test_confirm_page.py`、`test_web_nano4_path.py`，世界夾具 `human_harness.World`。

通用夾具說明（下文簡稱「合格行」）：`ssh -o ControlMaster=auto -o ControlPath=~/.ssh/cm-%r-%h-%p -o ControlPersist=8h -o ServerAliveInterval=60 u@nano4.nchc.org.tw true`，運算環境（CE）的 `hostName` 為 `nano4.nchc.org.tw`。「退回訊息（連線斷）」＝以 `No open connection to the site` 開頭的訊息。

## User Story 1 — 站台退回時結果多一個 open_command，平台只收符合嚴格格式的值（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | RV-01；B3 | 功能 | 站台夾具讓 `on_site` 回 `needs-human reason=no-master` 加一行 `OPEN_CMD` | 對站台送 launch 預檢 | 退回結果的 `open_command` 與 `OPEN_CMD` 逐字相同 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-002 | RV-01；「訊息文字不變」 | 功能 | 同 TC-001 | 同 TC-001 | 退回結果的 `message` 與動工前相同：仍含 `RELOGIN` 與 `OPEN_CMD` | 自動：同上 |
| TC-003 | RV-01；作法 1「回空字串就不放」 | 例外 | `reason=no-master`，但輸出裡沒有可擷取的指令行 | 同 TC-001 | 結果裡沒有 `open_command` 這個鍵，`ok`、`message` 照舊 | 自動：同上 |
| TC-004 | RV-01 | 例外 | 站台回 `sessions-exhausted`（連線數用完） | 同 TC-001 | 結果裡沒有 `open_command` 鍵 | 自動：同上 |
| TC-005 | RV-01 | 例外 | 站台預檢因 Java 版本不符被退回 | 同 TC-001 | 結果裡沒有 `open_command` 鍵 | 自動：同上 |
| TC-006 | RV-02；issue「以 on_site.sh 印出的那一行為唯一來源」 | 功能 | 用真的 `scripts/on_site.sh`，`ON_SITE_SSH_BIN` 指向假 ssh（比照 `tests/on_site_test.sh` 的 `no_master_run`），取得它印出的指令行 | 該輸出經站台擷取 | `open_command` 與 on_site.sh 印出的那一行逐字相同（含 `wsl.exe -e` 前綴與展開後的 ControlPath） | 自動：同上 |
| TC-007 | RV-02 | 功能 | 平台與站台的非測試原始碼 | 搜 `ControlPersist`、`ControlMaster=yes` | 找不到任何硬寫的指令樣板（`jobs.py` 驗證用的 regex 不含具體 ControlPath，不算） | 自動：同上 |
| TC-008 | RV-05；裁決 1 | 功能 | 平台所有非測試原始碼（新測試檔自己除外） | 搜字串 `nchc_t3c4`、`u9613010`、`cm-%r-%h-%p -i` | 都找不到（維護者聊天裡那條指令沒有被寫死進平台） | 自動：同上 |
| TC-009 | 作法 1；`test_station_static.py` | 功能 | 站台 Python 原始碼 | 跑 `test_station_static.py` | 仍綠：原始碼沒有 `ControlMaster`、`ssh -` 字面 | 自動：`platform/tests/test_station_static.py` |
| TC-010 | RV-03；B3 | 功能 | 合格行放在 launch_nextflow 結果的 `open_command`，job 所屬 CE 的 hostName 為 `nano4.nchc.org.tw` | 經 `jobs.clean_result` | `open_command` 保留，值不變 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-011 | RV-03 | 功能 | 合格行前面加 `wsl.exe -e ` | 同 TC-010 | 保留 | 自動：同上 |
| TC-012 | RV-03；issue 嚴格格式 | 例外 | 合格行分別被塞入 `;`、`&&`、`$(`、反引號、換行、`\|`（各一個版本） | 同 TC-010 | 每一個版本的 `open_command` 都被丟掉，其餘欄位不受影響 | 自動：同上 |
| TC-013 | RV-03；「≤600 字元」 | 例外 | 一個 601 字元、其餘格式合格的指令 | 同 TC-010 | 丟掉 | 自動：同上 |
| TC-014 | RV-03 | 例外 | `open_command` 是 None、整數、list | 同 TC-010 | 都丟掉，不出錯 | 自動：同上 |
| TC-015 | RV-03；作法 2「其他 kind 一律不收」 | 例外 | `put_upload`、`clean_work`、`preflight` 的結果帶合格的 `open_command` | 各自經 `jobs.clean_result` | 輸出與動工前完全相同（沒有 `open_command`，鍵集合不變） | 自動：同上 |
| TC-016 | RV-04；「主機名取自 CE 設定，不取自使用者的輸入」 | 例外 | 指令行裡的 host 是 `evil.example.org`，CE 的 hostName 是 `nano4.nchc.org.tw` | 同 TC-010 | `open_command` 丟掉，`ok`、`message` 保留 | 自動：同上 |
| TC-017 | RV-04 | 例外 | 格式合格，但 job 所屬 CE 沒有 `hostName` | 同 TC-010 | `open_command` 丟掉，其餘欄位不受影響 | 自動：同上 |
| TC-018 | RV-04 | 例外 | 格式合格，但 job 所屬 CE 不存在 | 同 TC-010 | `open_command` 丟掉，其餘欄位不受影響，不出錯 | 自動：同上 |
| TC-019 | 作法 2 ③ | 功能 | 指令行最後是 `u@nano4.nchc.org.tw true`（含 `user@`），CE hostName 為 `nano4.nchc.org.tw` | 同 TC-010 | 保留（比對 `@` 之後的主機） | 自動：同上 |
| TC-020 | 作法 2「其餘欄位照舊」 | 功能 | launch_nextflow 結果含 `slurm_job_id`、`run_name`、`run_folder`、`left_on_site`、`message`（上限 2000） | 經 `jobs.clean_result`，分別帶合格與不合格的 `open_command` | 這些欄位的清洗結果與動工前相同，不論 `open_command` 被保留或丟掉 | 自動：同上 |

## User Story 2 — 確認頁對被退回的工作顯示原因與指令，不再寫「已送出」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | RV-06（主線）；B2、T3 | 功能 | 使用者核准後，job 被標 `refused`，`result_json` 是 `{"ok": False, "message": "No open connection to the site. Log in once…", "open_command": 合格行}` | 擁有者開 `/c/<編號>`（zh） | 頁面含退回原因，含整行合格行且放在 `<pre>` 內，含「平台主機」 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-022 | RV-06；T3「頁面上不出現『已送出』」 | 功能 | 同 TC-021 | 開 `/c/<編號>`（zh 與 en 各一次） | 兩個語言的頁面都不含「已送出」三字 | 自動：同上 |
| TC-023 | RV-06 | 功能 | 同 TC-021 | 開 `/c/<編號>`（zh 與 en） | 頁面不含 `class="ok"`（沒有綠色送出句） | 自動：同上 |
| TC-024 | RV-06；維護者英文顯示文字 | 功能 | 同 TC-021 | 開 `/c/<編號>?lang=en` | 頁面含 "station host"，整行合格行在 `<pre>` 內 | 自動：同上 |
| TC-025 | 維護者顯示文字（中文） | 功能 | 同 TC-021，job 的代理名為 `agent-1` | 開 `/c/<編號>`（zh） | 文字含「站台連線沒開，工作沒有送出」「平台主機 `agent-1`」「WSL 終端機」「passphrase」「OTP」「重新呼叫 launch」，最後接整行指令 | 自動：同上 |
| TC-026 | 維護者顯示文字（英文） | 功能 | 同 TC-025 | 開 `/c/<編號>?lang=en` | 文字含 "The connection to the site is not open; nothing was submitted."、"station host" 加 `agent-1`、"paste this line into a WSL terminal, enter your passphrase and OTP, then call launch again"，最後接整行指令 | 自動：同上 |
| TC-027 | 作法 4「用該 job 的 agent 欄」 | 功能 | job 有 `agent` 欄 | 開 `/c/<編號>` | 「平台主機」後面寫的是 agent 名，不是 CE 名 | 自動：同上 |
| TC-028 | 作法 4「沒有就寫運算環境名」 | 功能 | job 沒有 `agent` 欄 | 開 `/c/<編號>` | 「平台主機」後面寫的是運算環境名 | 自動：同上 |
| TC-029 | RV-05 後半；RV-02 | 功能 | 夾具讓 on_site 印出某一行 X，經站台、`clean_result` 存進資料庫 | 開 `/c/<編號>` | 頁面上的指令等於 X，而不是平台裡任何常數 | 自動：同上 |
| TC-030 | RV-08；作法 4 | 例外 | 退回訊息（連線斷），但沒有 `open_command` | 開 `/c/<編號>` | 有說明與「請查看站台主機的終端機提示」，沒有 `<pre>`，平台沒有自己組出任何指令 | 自動：同上 |
| TC-031 | RV-08 | 例外 | 退回原因是 Java 版本不符 | 開 `/c/<編號>` | 顯示一句原因；沒有 `<pre>` 指令；頁面沒有 `ssh `；不含「已送出」 | 自動：同上 |
| TC-032 | RV-08；PITFALLS 16e | 例外 | 退回原因是 `sessions are used up` | 開 `/c/<編號>` | 顯示一句原因；沒有 `<pre>` 指令；沒有 `ssh `；不顯示登入指令 | 自動：同上 |
| TC-033 | 作法 3、5（`refused`／`error`） | 例外 | job 狀態為 `error`，`result_json.message` 有一句原因 | 開 `/c/<編號>` | 顯示該原因的退回區塊，不含「已送出」，不含登入指令 | 自動：同上 |
| TC-034 | 作法 3「第一句」「最長 300」 | 例外 | `message` 有多句、總長超過 300 | 開 `/c/<編號>` | 只顯示第一句，且不超過 300 字 | 自動：同上 |
| TC-035 | 作法 3「清洗」；後端守則（錯誤訊息不露內部資訊） | 例外 | `message` 內含 `Traceback`、SQL 片段、類似憑證的字串 | 開 `/c/<編號>` | 頁面不出現這些內容；原因仍說明發生什麼事 | 自動：同上 |
| TC-036 | RV-09；T3「queued/done 維持原文案」 | 功能 | job 為 queued | 開 `/c/<編號>` | 與動工前逐位元組相同，仍是 `<p class="ok">已送出。工作編號 N。</p>` | 自動：同上 |
| TC-037 | RV-09 | 功能 | job 為 claimed | 開 `/c/<編號>` | 與動工前逐位元組相同 | 自動：同上 |
| TC-038 | RV-09 | 功能 | job 為 done | 開 `/c/<編號>` | 與動工前逐位元組相同 | 自動：同上 |
| TC-039 | 作法 5「req 無 job」 | 功能 | 已核准的請求還沒有 job | 開 `/c/<編號>` | 與動工前逐位元組相同 | 自動：同上 |
| TC-040 | RV-09；作法 5 | 功能 | 待確認的請求 | 在確認頁按送出（`confirm_post`） | 回應與動工前相同 | 自動：同上 |
| TC-041 | RV-10 | 例外 | 退回 `message` 含 `<script>alert(1)</script>` | 開 `/c/<編號>` | 頁面沒有未跳脫的 `<script>` 標籤（以跳脫文字顯示） | 自動：同上 |
| TC-042 | RV-10；作法 3「讀出時再驗一次」 | 例外 | 繞過驗證直接寫進資料庫的 `open_command`，內含 `<script>` 或 `;` | 開 `/c/<編號>` | 壞指令不顯示（沒有 `<pre>` 指令），頁面無未跳脫標籤 | 自動：同上 |
| TC-043 | 作法 7 | 例外 | 同 TC-021 | 檢查退回區塊的 HTML | 指令只在 `<pre>` 內，不在任何屬性值；區塊內沒有表單、按鈕、輸入框，也沒有指向 ssh 的連結 | 自動：同上 |
| TC-044 | 後端守則：跨使用者讀 | 例外 | 使用者 A 的 job 被退回；使用者 B 有自己的登入 | B 開 A 的 `/c/<編號>` | 被拒絕（與現有擁有者檢查相同）；回應不含 A 的退回原因與指令 | 自動：同上 |
| TC-045 | 後端守則：跨使用者寫 | 例外 | 使用者 A 的待確認請求；使用者 B 有自己的登入 | B 對 A 的請求按送出 | 被拒絕，資料不變（現有行為不被本片改變） | 自動：同上 |
| TC-046 | 後端守則：確認管道（沒有確認就不得寫入） | 功能 | 退回狀態的 job，記下資料庫各表內容 | 開 `/c/<編號>` 與 `/` 數次 | 開頁面前後資料庫各表內容完全相同（新的查詢只讀） | 自動：同上 |
| TC-047 | 計畫「網頁釘字」節 | 功能 | 既有釘字測試 | 跑 `test_confirm_page.py`、`test_pending_confirm_restart.py`、`test_web_confirm_plain.py`、`test_web_nano4_path.py`、`test_clean_page.py` | 全綠，且這些測試檔本片沒有被改弱 | 自動：上述各檔 |

## User Story 3 — 分析清單頁顯示同一個退回區塊，以及共用的唯讀查詢（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-048 | RV-07；B2 | 功能 | 使用者最近一筆 launch job 剛被退回（連線斷，有合格 `open_command`） | 開 `/`（zh） | 清單上方有與 TC-021 相同的退回區塊與整行指令 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-049 | RV-07 | 功能 | 同 TC-048 | 開 `/?lang=en` | 有相同的英文區塊（含 "station host"）與整行指令 | 自動：同上 |
| TC-050 | 作法 6「顯示一次」 | 功能 | 同一使用者有兩筆 refused 的 launch job | 開 `/` | 退回區塊只出現一次，而且是最近那一筆 | 自動：同上 |
| TC-051 | RV-07；後端守則：跨使用者 | 例外 | 使用者 A 的退回；使用者 B 登入 | B 開 `/` | 沒有任何退回區塊，也看不到 A 的指令 | 自動：同上 |
| TC-052 | RV-07；`max_age=3600` | 例外 | 退回已超過 1 小時 | 開 `/` | 沒有退回區塊 | 自動：同上 |
| TC-053 | 作法 3 | 功能 | 退回結束時間在 1 小時內（例如 59 分鐘前） | 開 `/` | 有退回區塊 | 自動：同上 |
| TC-054 | RV-07；作法 6 | 例外 | 退回之後，同一使用者又有一筆成功的 launch job | 開 `/` | 沒有退回區塊 | 自動：同上 |
| TC-055 | 作法 6「沒有就頁面與以前相同」 | 功能 | 使用者沒有任何被退回的 launch job | 開 `/` | 頁面與動工前逐位元組相同 | 自動：同上 |
| TC-056 | RV-08 | 例外 | 最近一筆 launch 被退回，原因是 Java 版本不符 | 開 `/` | 顯示一句原因，沒有 `<pre>`，沒有 `ssh ` | 自動：同上 |
| TC-057 | RV-08 | 例外 | 最近一筆 launch 被退回，連線斷但沒有 `open_command` | 開 `/` | 有說明，沒有 `<pre>`，平台沒有自己組指令 | 自動：同上 |
| TC-058 | 作法 3「該使用者最近一筆 launch_nextflow job」 | 功能 | 退回之後，同一使用者又有一筆較新的非 launch 工作（例如上傳或清理） | 開 `/` | 退回區塊仍顯示（只看 launch 類工作） | 自動：同上 |
| TC-059 | RV-11 | 功能 | `web_board.STRINGS` | 比較 zh 與 en 的新增鍵 | 兩邊新增的鍵集合完全相同；沒有 `refusal_queued_note` | 自動：同上 |
| TC-060 | 計畫「網頁字串」；作法 4 | 功能 | 新字串已加入 | 跑 `test_web_wording_sweep.py`、`test_web_board.py` | 全綠；禁用詞清單沒有被放寬（新字串須通過，不是改清單讓它過） | 自動：`platform/tests/test_web_wording_sweep.py` |
| TC-061 | 作法 3 | 功能 | job 狀態分別為 queued、claimed、done | 呼叫 `jobs.refusal_of` | 都回 `None`；`refused`、`error` 才回含 `state`、`reason`、`open_command`、`host` 的結果 | 自動：`platform/tests/test_refusal_visibility.py` |

## User Story 4 — 畫面、前端限制與人看得到的成品（優先度 P1，維護者看截圖）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-062 | 完成標準「截圖」 | 功能 | 測試平台造一個 refused 加合格 `open_command` 的 launch job | 截確認頁 1440 寬與 390 寬，各 zh、en，共 4 張 | 4 張都在 `specs/refusal-visibility/screens/`，`ledger.md` 逐張列檔名與看到的字 | 手動：`docs/TESTING.md`（新增步驟） |
| TC-063 | 完成標準；T3 | 功能 | TC-062 的 4 張截圖 | 看每一張 | 每一張都看不到「已送出」 | 手動：同上 |
| TC-064 | 完成標準「390 寬不得橫向捲動」 | 功能 | 390 寬確認頁 | 在 390 寬看頁面 | 整頁不能左右捲動；過長的指令只在 `<pre>` 內部捲動 | 手動：同上 |
| TC-065 | 專長守則（ui）：axe | 功能 | 起真實應用程式，確認頁為退回狀態 | 跑 axe 無障礙掃描 | 沒有 serious 或 critical 的問題 | 手動：同上 |
| TC-066 | 專長守則（ui）：前端限制 | 功能 | 退回狀態的 `/c/<編號>` 與 `/` | 檢查回應 | 沒有 inline style；沒有請求外部網址；內容安全政策（CSP）標頭存在 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-067 | 作法 7；專長守則（ui） | 功能 | 退回狀態的頁面 | 檢查退回區塊 | 區塊沒有加入任何 `<script>` 或事件屬性；沒有新增前端元件 | 自動：同上 |
| TC-068 | 作法 4「沿用既有提示框 class，不新增 CSS 元件」 | 功能 | 本片 diff | 看 `web_board.py` 與其他檔的變動 | 只用既有的 `<p class="bad">`、`.notice`；沒有新增 CSS 規則、顏色、字型或間距數值 | 手動：`docs/TESTING.md` |
| TC-069 | 專長守則（ui）：狀態不只靠顏色 | 功能 | 退回區塊 | 檢查區塊 HTML | 區塊含文字說明（「沒有送出」等），不是只靠 class 的顏色；符號的有無與既有 `bad` 提示框一致 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-070 | 專長守則（ui）：用語白話 | 功能 | TC-062 的截圖 | 維護者讀中英文字 | 看得出「沒送出、原因、下一步要貼哪一行」，沒有堆疊、內部代碼 | 手動：`docs/TESTING.md` |
| TC-071 | 完成標準「手動」 | 功能 | `docs/TESTING.md` | 讀新增的手動步驟 | 步驟齊全且可照做：斷開 ssh master → launch → 在確認頁按送出 → 站台退回 → 重新整理確認頁看到原因與指令 → 在平台主機 WSL 貼指令（OTP 由人輸入）→ 再 launch 成功；全程網站沒有密碼或 OTP 輸入框 | 手動：`docs/TESTING.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-072 | 護欄；RV-12 ① | 功能 | 所有 MCP 工具的 input_schema | 列出所有屬性名 | 都不含 `password`、`passwd`、`otp`、`one.?time`、`verification`、`secret`（既有的 `token` 若存在，列白名單並註明） | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-073 | 護欄；RV-12 ② | 功能 | 平台所有 route | 列出路徑 | 沒有任何路徑含 `connect`、`ssh`、`login-site` | 自動：同上 |
| TC-074 | 護欄；RV-12 ③ | 功能 | 退回狀態的 `/c/<編號>` 與 `/` | 檢查 HTML | `<input` 沒有 `type="password"`，`name` 不含 `password`、`otp`、`code`；沒有文字含「幫我連線」「connect for me」的 `<button` | 自動：同上 |
| TC-075 | 護欄；RV-12 ④ | 例外 | 現有 POST 路由 | 送 `password=x&otp=123456` | 不被讀取、不出現在回應；`confirmations`、`jobs`、sessions 各表都不含 `123456` | 自動：同上 |
| TC-076 | 不准動清單；RV-13 | 功能 | 本片分支 | `git diff origin/v3 --stat` | 完全沒有 `confirm.py`、`actions/__init__.py`、`mcp_server.py`、`actions/chat_tools.py`、`guidance.py`、`store.py`、`compute_envs.py`、`scripts/on_site.sh`、`.github/`、`hooks/`、`plugin.json`、`.specify/memory/constitution.md`、其他 `web_*.py`（`web_board.py` 除外） | 手動：`docs/TESTING.md`，證據貼 `ledger.md` |
| TC-077 | 完成標準「tools.json 零 diff」 | 功能 | MCP 工具快照 `tools.json` | 跑快照測試並看 diff | 快照測試綠，`tools.json` 零 diff | 自動：既有快照測試（`tests/run_all.sh` 的平台部分） |
| TC-078 | 範圍：檔案；完成標準 | 功能 | 本片分支 | `git diff --name-only origin/v3` | 只含計畫「範圍：檔案」列的檔案；站台只動 `handlers.py`、`rules.py`、`launch.py` 的退回路徑，動到其他站台檔時 ledger 有說明 | 手動：`docs/TESTING.md`，證據貼 `ledger.md` |
| TC-079 | 站台 diff 只加一個結果鍵；PITFALLS 已查項 | 功能 | 既有站台測試 | 跑 `test_station_realpath_down.py`、`test_station_channel.py`、`test_launch_followup.py`、`test_station_e2e.py` | 全綠，這些測試檔沒有被改弱（站台訊息文字沒變） | 自動：上述各檔 |
| TC-080 | PITFALLS 16b／16g；環境事實 | 功能 | `scripts/on_site.sh` | 跑 `tests/on_site_test.sh` | 綠；`no_master()` 輸出沒變 | 自動：`tests/on_site_test.sh` |
| TC-081 | 憲法安全網：寫入工具須經人確認 | 功能 | 本片新增的程式 | 檢查新增的查詢與頁面程式；跑 `test_actions_layer.py`（`test_tcb04_*` 到 `test_tcb08_*`）、`test_human_channel.py` | 沒有新增任何寫入路徑（新查詢經 `store.open_readonly` 只讀）；既有確認測試全綠 | 自動：上述各檔 |
| TC-082 | 後端守則：對等性 | 功能 | 使用者可見的 MCP 工具清單與動作層函式清單 | 兩邊一一對應的既有對等性測試 | 仍綠；本片沒有新增、刪除或改名任何工具；兩個頁面的退回判斷都呼叫同一個 `jobs` 查詢與同一組字串，路由處理函式裡沒有第二份判斷邏輯 | 自動：既有對等性測試，加 `platform/tests/test_refusal_visibility.py` |
| TC-083 | `clean_result` 釘鍵 | 功能 | 既有釘鍵測試 | 跑 `test_cleanup_confirm.py`（`test_tc051_tc052_*`）、`test_aws_upload.py`、`test_azure_upload.py`、`test_byte_channel_a.py`、`test_byte_channel_b.py` | 全綠且未被改弱 | 自動：上述各檔 |
| TC-084 | 憲法第 7 條（不需要找維護者）；後端守則（錯誤訊息說明原因與處理） | 功能 | 連線斷的退回頁（中、英） | 讀頁面文字 | 同時說明發生了什麼（沒送出、什麼原因）與下一步（在哪裡貼哪一行） | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-085 | 後端守則：結構變動需 migration 或明寫不需要 | 功能 | 本片 diff | 檢查是否有資料庫欄位、schema 或 migration 變動 | 沒有（計畫寫明不需要 migration）；`result_json` 只多一個可選鍵 | 手動：`docs/TESTING.md`，證據貼 `ledger.md` |
| TC-086 | 完成標準「閱卷（M）」 | 功能 | `specs/refusal-visibility/ledger.md` | 讀 ledger | 有 TC-006 的 on_site 實際輸出行與頁面指令並列、平台無硬寫樣板的 grep 證據、PITFALLS 重查結果、TC-062 截圖逐張說明 | 手動：`docs/TESTING.md` |
| TC-087 | 後端守則：密鑰不得出現在日誌或回應 | 例外 | 退回狀態的頁面，帶 `password=x&otp=123456` 的請求 | 擷取請求過程的日誌與回應 | 日誌與回應都不含 `123456`、密碼、token | 自動：`platform/tests/test_refusal_visibility.py` |

## 不在範圍（計畫「不做」節）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-088 | 不做：幫我連線按鈕、web pty、URL scheme、嵌入式終端、代為登入 | 不在範圍 | 退回狀態的頁面與平台原始碼 | 搜頁面與原始碼 | 沒有 `abf-connect://`、沒有嵌入式終端或 iframe、沒有代連 ssh 的 route、沒有收 passphrase／密碼／OTP 的欄位 | 自動：`platform/tests/test_refusal_visibility.py` |
| TC-089 | 不做：複製指令按鈕 | 不在範圍 | 退回狀態的頁面 | 檢查退回區塊 | 只有 `<pre>` 文字，沒有複製按鈕，沒有剪貼簿相關程式 | 自動：同上 |
| TC-090 | 不做：C2（站台心跳 `site_link`、`_target` 預檢、連線斷時保留 pending） | 不在範圍 | 本片 diff 與原始碼 | 搜 `site_link`；連線斷時按送出 | 沒有新增 `site_link` 或預檢；連線斷時的核准行為與動工前相同 | 自動：同上 |
| TC-091 | 不做：C3（`abf-station connect` 本機小工具） | 不在範圍 | 本片 diff | 看是否新增 connect 指令或入口 | 沒有新增 | 自動：同上 |
| TC-092 | 不做：B1（重複 `launch` 回 `state=refused`＋`last_refusal`）與 C1（`get_request_status`） | 不在範圍 | 工作剛被退回後，使用者再呼叫 `launch` | 比對 `launch` 回覆與工具清單 | `launch` 回覆與動工前相同，沒有 `last_refusal` 欄；工具清單沒有 `get_request_status` | 自動：同上 |
| TC-093 | 裁決 3（Q1）：queued 文案不改 | 不在範圍 | job 為 queued 的確認頁 | 開 `/c/<編號>` | 仍是「已送出。工作編號 N。」，不出現「已排入佇列」；`STRINGS` 沒有 `refusal_queued_note` 鍵 | 自動：同上 |
| TC-094 | 裁決 1：不採維護者聊天裡的指令；不新增 `site_login_command` | 不在範圍 | 平台非測試原始碼 | 搜 `site_login_command`、`-fN`、`ControlPersist=12h`、`-i ~/.ssh/` | 都找不到；`compute_envs.py` 沒有變動 | 自動：同上 |
| TC-095 | 不做：輪詢、排程 | 不在範圍 | 退回頁面與本片 diff | 檢查是否有自動重新整理、計時器、背景工作 | 沒有；說明只在下次成功 launch 後自然消失（TC-054） | 自動：同上 |
| TC-096 | 不做：改站台訊息文字、改 `on_site.sh`、統一 8h／12h | 不在範圍 | 連線斷的站台退回 | 比對 `message` 與動工前；跑 `tests/on_site_test.sh` | `message` 與動工前相同；on_site.sh 的持久度設定沒變 | 自動：`platform/tests/test_refusal_visibility.py`、`tests/on_site_test.sh` |
