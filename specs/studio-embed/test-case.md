# 測試案例：下游階段把 RStudio 嵌進網頁（studio-embed）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本任務沒有 spec.md，計畫即規格（同 studios-new-tab 的做法）。
測試檔預期：`platform/tests/test_studio_embed.py`（頁面、CSP、設定、--r）、`tests/studio_embed_deploy_test.sh`（unit 與 env.example 的靜態檢查）；每個測試在註解寫它的 TC 編號。
-->

**規格**：`specs/studio-embed/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：功能、例外、不在範圍。名詞：「設定」指部署設定 `ABF_STUDIO_URL`；「下游頁」指成功分析的 `/?run=<id>&stage=downstream`；「今天的頁面」指本任務開始前（origin/v3 的 74416bc4）同一請求的回應。

## User Story 1 — 設定 ABF_STUDIO_URL：只收本機位址，錯的在啟動時拒絕（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 做什麼 1；例子 1 | 功能 | 設定為 `http://127.0.0.1:8790` 或 `http://localhost:8790` | 以這個值啟動 `abf-platform web` | 兩個值都被接受，平台正常啟動；之後下游頁使用的正是這個字串，一字不差 | 自動：`platform/tests/test_studio_embed.py` |
| TC-002 | 做什麼 1；例子 5 | 例外 | 設定為下列任一：`https://127.0.0.1:8790`、`http://example.com:8790`、`http://127.0.0.1.evil.com:8790`、`http://localhost.evil.com:8790`、`http://127.0.0.1:8790@evil.com`、`http://0.0.0.0:8790`、`http://[::1]:8790`、`http://127.1:8790`、`http://2130706433:8790`、`ftp://127.0.0.1:8790`、`javascript:alert(1)`、`//127.0.0.1:8790`、`*` | 啟動 `abf-platform web` | 每一個都被拒絕，平台不啟動（理由見 TC-004）；沒有任何一個值能進到頁面或 CSP | 自動：`platform/tests/test_studio_embed.py` |
| TC-003 | 做什麼 1；例子 5 | 例外 | 設定為下列任一：`http://127.0.0.1`（沒有埠）、`http://127.0.0.1:0`、`http://127.0.0.1:99999`、`http://127.0.0.1:abc`、`http://127.0.0.1:8790/x`、`http://127.0.0.1:8790?a=1`、`http://127.0.0.1:8790#f`、`http://u:p@127.0.0.1:8790`、`http://127.0.0.1:8790; script-src *`、`http://127.0.0.1:8790 'unsafe-inline'`、含空白或換行的值；另有結尾多一個 `/` 的 `http://127.0.0.1:8790/` | 啟動 `abf-platform web` | 前面各形都被拒絕。結尾 `/` 那一個可以拒絕，也可以正規化成沒有 `/`；兩種都可，但任何有路徑或多餘字元的字串都不得出現在 CSP 或 iframe 來源（見 TC-019、TC-007） | 自動：`platform/tests/test_studio_embed.py` |
| TC-004 | 做什麼 1；例子 5 | 例外 | 設定為 TC-002 或 TC-003 的任一壞值 | 啟動 `abf-platform web` | 結束碼 1；訊息說明設定名稱 `ABF_STUDIO_URL`、為什麼被拒絕、要改成什麼樣子（中英並列，格式同 `--public-url` 被拒時的訊息）；`uvicorn.run` 與 `create_app` 都沒有被呼叫（沒有任何東西在聽） | 自動：`platform/tests/test_studio_embed.py` |
| TC-005 | 做什麼 1；例子 4 | 功能 | 設定未設定，或設定為空字串（systemd 的 env 檔寫 `ABF_STUDIO_URL=` 時） | 啟動 `abf-platform web` | 平台正常啟動，視同沒有設定（見 TC-022） | 自動：`platform/tests/test_studio_embed.py` |
| TC-006 | 做什麼 1、4 | 功能 | 目前 `deploy/systemd/abf-web.service.in` 的 `ExecStart` 參數；env 檔分別有、沒有 `ABF_STUDIO_URL` | 把 `ExecStart` 的參數（`${…}` 展開後，空值不留下任何參數）交給 `abf-platform web` 的命令列解析 | 兩種情況都解析成功，不出現「缺少參數值」的錯誤；設定有填時被讀到並套用，沒填時等同未設定。設定在 `cmd_web` 內於 `--public-url` 檢查之後、`create_app` 之前讀取並檢查；如果新增旗標（建議不新增，直接讀環境變數），它在空值時不得讓程序無法啟動 | 自動：`platform/tests/test_studio_embed.py` |

## User Story 2 — 成功分析的下游頁：RStudio 在頁面中間（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 做什麼 2；例子 1 | 功能 | 設定為 `http://127.0.0.1:8790`；一個已成功、屬於登入者的分析 | 開 `/?run=<id>&stage=downstream` | 中間欄恰好有一個 `<iframe>`，`src` 與設定逐字相同，有非空的 `title`；頁面上沒有其他 `<iframe>` | 自動：`platform/tests/test_studio_embed.py` |
| TC-008 | 做什麼 2 | 功能 | 同 TC-007 | 看 iframe 上方 | 有一行說明，加一個「在新分頁開啟 RStudio」連結：`href` 與設定逐字相同、`target="_blank"`、`rel="noopener noreferrer"`，位置在 iframe 之前 | 自動：`platform/tests/test_studio_embed.py` |
| TC-009 | 例子 5：任何情況下都不嵌入 loopback 以外的位址 | 例外 | 設定為 `http://127.0.0.1:8790`；請求另帶 `&studio=` 取下列各值：`https://evil.example/`、`http://localhost:8790`、`http://127.0.0.1:9999`、`javascript:alert(1)`、`data:text/html,x` | 開下游頁 | 每一次 iframe 的 `src` 仍然只等於設定；`studio=` 的值不得出現在任何 `<iframe>`、不得進 CSP；壞值仍照今天的方式顯示一則錯誤（`role="alert"`）。舊的貼上表單是否保留不在此判定 | 自動：`platform/tests/test_studio_embed.py` |
| TC-010 | 做什麼 2；例子 3 | 功能 | 同 TC-007；RStudio 沒有啟動（平台不知道也不檢查） | 開下游頁（繁中與 `lang=en`） | 頁面正常顯示（200）；有一句說明嵌入畫面空白時怎麼辦，點出兩個原因（RStudio 沒在這台電腦上啟動、瀏覽器擋下本機連線）和兩個作法（按「在新分頁開啟」、照 `docs/` 的步驟啟動），並指向 `docs/OPERATIONS.md` 的那一節 | 自動：`platform/tests/test_studio_embed.py` |
| TC-011 | 做什麼 2；例子 2 | 功能 | 同 TC-007，分析 id 為 `<id>` | 看頁面上可複製的 R 指令 | 兩行 R 指令放在可複製的 `<pre>` 內：第一行含 `eval(parse(text` 與 `system2(`，帶 `fetch-results`、`<id>`、`--r`；第二行帶 `publish-figure` 與 `<id>`；兩行都不含權杖、密碼 | 自動：`platform/tests/test_studio_embed.py` |
| TC-012 | 做什麼 2 | 例外 | 下游頁以 id 為 `x<b>"y&z'\w` 的分析（直接呼叫 `render_downstream`） | 看輸出 | R 指令裡的 id 是正確跳脫的 R 字串（引號與反斜線不能讓它跳出字串），同時 HTML 也跳脫（不能長出標籤、不能離開屬性或 `<pre>`）；英文頁沒有中日韓字元 | 自動：`platform/tests/test_studio_embed.py` |
| TC-013 | 做什麼 2 | 功能 | 同 TC-007 | 看終端機指令區塊 | 今天的三行終端機指令（`studio-connect`、`fetch-results`、`publish-figure`）內容不變，放在不帶 `open` 的 `<details>` 裡，位置在兩行 R 指令之後（次要位置） | 自動：`platform/tests/test_studio_embed.py` |
| TC-014 | 做什麼 2；不做：不新增 CSS | 功能 | 同 TC-007 | 檢查 iframe 與整頁 | iframe 帶 `allow` 屬性：非空、不含 `*`、不含 camera／microphone／geolocation 之類與本任務無關的權限；帶 `referrerpolicy`；尺寸只用 `width`／`height` 屬性（`width="100%"`、`height` 為不小於 600 的數字）；整頁沒有 `style=`；頁面用到的每個 class 名稱都存在於 `web_board.STYLE`；`STYLE` 的 sha256 仍等於 `test_results_files.py` 的 `STYLE_SHA256`。若做不到而必須加樣式，實作者停手回報，不加 | 自動：`platform/tests/test_studio_embed.py` |
| TC-015 | 做什麼 2；不做 | 功能 | 同 TC-007 | 檢查頁面與路由 | 頁面沒有 `<script`，沒有 `http-equiv="refresh"`；沒有新路由、沒有新 action（`test_no_new_route_no_new_action` 原樣通過） | 自動：`platform/tests/test_studio_embed.py` |
| TC-016 | 做什麼 2 | 例外 | 同 TC-007，語言 `en` | 開 `lang=en` 的下游頁 | 英文頁沒有中日韓字元；`web_downstream.STRINGS` 的 zh 與 en 鍵相同、值都非空；zh 字串過禁用詞檢查 | 自動：`platform/tests/test_studio_embed.py` |
| TC-017 | 做什麼 2；例子 6 | 例外 | 設定存在；分析為執行中、失敗、別人的、不存在的各一個，另有成功分析但 `stage=results` | 各開對應的頁面 | 都沒有 iframe、沒有 `frame-src`；別人的與不存在的仍是 404，且不洩漏 id | 自動：`platform/tests/test_studio_embed.py` |
| TC-018 | 不做（第 1～4 條） | 不在範圍 | 設定存在 | 看下游頁與啟動過程 | 只有一個 iframe，沒有 Jupyter、網頁終端機；沒有每位使用者各自的位址輸入；平台沒有對該位址發出任何連線（啟動與出頁時 socket 被監看，零次連線）；`platform/abf_station/` 沒有被修改（`git diff`） | 自動：`platform/tests/test_studio_embed.py` |

## User Story 3 — CSP 只在這一頁多 frame-src（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 做什麼 2；例子 6 | 功能 | 設定為 `http://127.0.0.1:8790`；成功分析 | 取下游頁的 `Content-Security-Policy` | 把 `; frame-src http://127.0.0.1:8790` 拿掉後，剩下的字串與今天的基本政策逐字相同（含 style 雜湊）；`frame-src` 的值只有這個設定一個來源，沒有 `*`、`'self'`、其他位址；`frame-ancestors 'none'`、`X-Frame-Options: DENY`、`default-src 'none'`、`form-action 'self'`、`base-uri 'none'` 都還在；沒有 `script-src`、沒有 `'unsafe-inline'` | 自動：`platform/tests/test_studio_embed.py` |
| TC-020 | 例子 6 | 例外 | 設定存在；已登入 | 逐一開：`/`、`/settings`、`/usage`、`/login`、`/launch`、`/upload`、看板、確認頁 `/c/<id>`、同意頁、完成頁（`stage=finished`，含有圖庫圖片的）、結果頁（`results` 與 `outputs`）、執行中分析的下游階段、404 頁、`/run/figure`、`/run/image`、`/run/report`、`/run/preview` | 全部都沒有 `frame-src`、沒有 `<iframe>`，標頭與沒有設定時逐字相同；只有 HTML 預覽頁的 `frame-src 'self'` 與沙箱 iframe 維持現狀（`test_web_result_viewer.py` 原樣通過） | 自動：`platform/tests/test_studio_embed.py` |
| TC-021 | 做什麼 2 | 例外 | 設定存在；成功分析的各種狀態（正常、帶 `flash`、帶壞的 `studio=`、`lang=en`） | 逐一取回應 | 「CSP 有 `frame-src`」與「本文有 `<iframe>`」永遠同時成立或同時不成立，且 `frame-src` 的值等於 iframe 的 `src`；回應標頭只被這一個分支設定 | 自動：`platform/tests/test_studio_embed.py` |

## User Story 4 — 沒填設定：下游頁和今天一模一樣（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 做什麼 1；例子 4 | 功能 | 設定未設定；成功分析；今天的頁面快照（由 origin/v3 的程式在改動前產生並存檔，繁中與英文、有與沒有 `?studio=`、已讀與未讀輸出，共 8 份，含回應標頭） | 開對應的下游頁 | 本文與標頭與快照逐位元組相同；沒有 `frame-src` | 自動：`platform/tests/test_studio_embed.py` |
| TC-023 | 例子 4 | 功能 | `platform/tests/test_web_downstream.py` 與 `test_web_result_viewer.py` | 與 origin/v3 比對 diff，並執行 | 這兩個檔案沒有任何斷言被移除、放寬或改值；全部通過 | 自動：`platform/tests/test_studio_embed.py`（比對 diff） |

## User Story 5 — 命令列 fetch-results --r（P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 做什麼 3；例子 2 | 功能 | 用既有的假平台測試夾具（不需真的 R）；一個有結果表的分析 | 執行 `abf-platform fetch-results <run> --r` | 標準輸出每一行不是 `#` 註解，就是 `<名稱> <- read.csv(...)`／`read.delim(...)` 形的指派；括號與引號成對、可被 R 解析（測試用字串規則檢查形狀，不執行 R）；內容與不加 `--r` 時印出的那段 R 程式相同 | 自動：`platform/tests/test_studio_embed.py` |
| TC-025 | 做什麼 3 | 例外 | 同 TC-024，但讀取失敗、沒有表、尚未設定 `studio-connect` 各一次 | 執行 `--r` | 進度、警告、錯誤訊息都走標準錯誤；標準輸出沒有任何非 R 的文字（空或只有註解）；結束碼與不加 `--r` 時相同 | 自動：`platform/tests/test_studio_embed.py` |
| TC-026 | 做什麼 3 | 功能 | 既有 `platform/tests/test_studio_cli*.py`；黃金檔 | 不加 `--r` 執行；比對 `__golden__/cli_tree.txt` 與 `cli_help_top.txt` | 不加 `--r` 的輸出與結束碼不變（既有測試原樣通過）；兩份黃金檔只有 `fetch-results` 一列多了 `--r`（`cli_tree.txt` 第 17 行、`cli_help_top.txt` 的用法行），別的指令一字不動；`web` 那列只有在新增旗標時才改 | 自動：`platform/tests/test_studio_embed.py` |
| TC-027 | 不做；做什麼 3 | 不在範圍 | `publish-figure` 的黃金檔與測試 | 檢查 diff 與執行 | `publish-figure` 沒有新增旗標、沒有自動確認、沒有改任何行為（`test_studio_publish.py`、黃金檔原樣通過）；`confirm.py`、`store.py` 沒被修改 | 自動：`platform/tests/test_studio_embed.py`（比對 diff） |
| TC-028 | 做什麼 2；例子 2 | 功能 | 下游頁的第二行 R 指令 | 靜態檢查該行 | 這行自己可獨立貼上：只用基本 R（不含 `library(`、`install.packages`）；把目前的圖存成暫存的 png 檔，再呼叫 `publish-figure <id>` 並帶那個檔案；不含任何確認旗標 | 自動：`platform/tests/test_studio_embed.py` |

## User Story 6 — 部署：以使用者身分、只聽本機（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 做什麼 4 | 功能 | `deploy/systemd/abf-rstudio.service.in` | 靜態檢查 | 檔案存在；開頭註解寫明它不是什麼（照 `abf-station@.service.in` 的慣例，第一行「Not …」）；`ExecStart` 啟動 `rserver`，帶 `www-address`、`www-port`、`www-frame-origin`（值為 `${ABF_PUBLIC_URL}`）與 `auth-none`（選項名稱已在套件的 `rserver` 執行檔字串中看到；名稱不得拼錯）；`EnvironmentFile=%h/.config/abf-platform/env`；`WantedBy=default.target`；`Restart=on-failure` | 自動：`tests/studio_embed_deploy_test.sh` |
| TC-030 | 做什麼 4；失敗條件：以 root 執行 | 例外 | 同上 | 靜態檢查 | 沒有 `User=root`、沒有 `sudo`、沒有 `WantedBy=multi-user.target`、沒有 `AmbientCapabilities`／`CapabilityBoundingSet` 提權；沒有指向 `/etc/systemd/system` 的安裝步驟；沒有 `--server-user root` | 自動：`tests/studio_embed_deploy_test.sh` |
| TC-031 | 做什麼 4；失敗條件：聽非 loopback | 例外 | 同上與 `deploy/env.example` | 靜態檢查 | `www-address` 一定存在（不寫＝用預設，套件字串中有 `0.0.0.0`，預設值未驗證）且只有 `127.0.0.1`；全檔沒有 `0.0.0.0`、`[::]`、`::`；沒有 `www-socket` 指向可寫入的共用位置；`deploy/env.example` 的範例值是 `http://127.0.0.1:<埠>` | 自動：`tests/studio_embed_deploy_test.sh` |
| TC-032 | 做什麼 4；做什麼 1 | 功能 | unit、`env.example`、`docs/OPERATIONS.md` | 靜態檢查 | unit 取得的埠與 `ABF_STUDIO_URL` 同源（只有一個地方寫埠；如果 unit 用第二個變數，env.example 要把兩者放在一起並說明必須相同）；範例埠不是 8787、8788、8789（平台自己的三個埠；RStudio 預設 8787 會與 `abf-serve` 撞）；文件與範例的埠相同；`env.example` 的新行通過 `hosted_deploy_test.sh` 的 TC-015／016（值為佔位或 loopback） | 自動：`tests/studio_embed_deploy_test.sh` |
| TC-033 | 做什麼 4 | 功能 | `tests/hosted_deploy_test.sh`、`tests/desktop_systemd_test.sh` | 執行兩個檔案 | 兩檔全部通過：`hosted_deploy_test.sh` 的 TC-069 清單加入 `abf-rstudio.service.in`（十一個）、TC-083 改為五個 `.service.in`；`desktop_systemd_test.sh` 第 198 行（TC-044）同步改；`deploy/` 下只多這一個檔案；`deploy/systemd/` 以外沒有別的新檔；這些被改的斷言是計畫點名的改動，其他斷言不得變弱 | 自動：`tests/hosted_deploy_test.sh`、`tests/desktop_systemd_test.sh` |
| TC-034 | 不做（隨附與不碰的範圍） | 不在範圍 | `git diff --stat origin/v3...HEAD` | 檢查改動清單 | 倉庫裡沒有 RStudio 的任何檔案（`.deb`、二進位檔、`rserver.conf` 複本）；沒有新相依（`pyproject.toml`／requirements 不變）；`.github/`、`hooks/`、`.specify/memory/constitution.md`、`.claude-plugin/plugin.json`、`confirm.py`、`store.py`、`platform/abf_station/` 都沒有被改 | 自動：`tests/studio_embed_deploy_test.sh` |
| TC-035 | 做什麼 4、5 | 功能 | `docs/OPERATIONS.md` 桌機一節 | 靜態檢查 | 新增一步，含：安裝（使用者自己從 Posit 取得，本專案不隨附、不修改，AGPL）、啟用 unit、看狀態、停止、移除；明寫「任何能登入這台電腦的人與這台電腦上的任何程式都連得到它，所以只適合個人電腦；不得把這個埠對外公開」；明寫套件安裝會把以 root 執行的系統服務 `rstudio-server` 啟用並啟動（套件的安裝腳本確實如此），要先把它停用（`disable --now`），再啟用本專案的 unit；檢查只聽 `127.0.0.1` 的方式；既有的四個 unit 的啟停指令行不改（`desktop_systemd_test.sh` 的 TC-023、D3 原樣通過）；`CHANGELOG.md` 新增一條且不放在 `keep-submissions` 之前（TC-047 原樣通過） | 自動：`tests/studio_embed_deploy_test.sh` |

## User Story 7 — 真的 RStudio、真的瀏覽器（P1，人工）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | 做什麼 4 | 功能 | 桌機（WSL）已照 OPERATIONS 安裝並啟用 `abf-rstudio` | 看程序的擁有者；看監聽的埠 | `rserver` 的使用者是本人，不是 root；只聽 `127.0.0.1:<埠>`，從區網另一台電腦連不到；套件自帶的 root 系統服務已停用 | 手動：`docs/TESTING.md`（studio-embed） |
| TC-037 | 例子 1 | 功能 | 設定已填、RStudio 已啟動；成功分析 | 開下游頁；在 RStudio 裡畫一張圖 | 頁面中間就是 RStudio（不用另外登入）；圖出現在右下 Plots 窗格，看得清楚 | 手動：`docs/TESTING.md`（studio-embed） |
| TC-038 | 例子 2 | 功能 | 同 TC-037；已 `studio-connect` | 把第一行貼進 RStudio Console；再貼第二行 | 結果表載入，`View()` 看得到；第二行得到一個確認連結，按下後圖出現在圖庫 | 手動：`docs/TESTING.md`（studio-embed） |
| TC-039 | 例子 3 | 例外 | 設定已填，RStudio 沒有啟動 | 開下游頁 | 頁面仍正常；空白框旁的說明告訴我怎麼辦；「在新分頁開啟」連結在 | 手動：`docs/TESTING.md`（studio-embed） |
| TC-040 | 例子 1；做什麼 5 | 功能 | Chrome、Edge、Firefox 各一次 | 各開一次下游頁 | 每個瀏覽器記錄：嵌入成功或被擋，被擋時的訊息、`allow` 屬性實際用的字、是否需要 `www-same-site`／`www-frame-origin` 調整；被擋不算失敗，但要寫進 `specs/studio-embed/ledger.md` | 手動：`docs/TESTING.md`（studio-embed） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | Safety Net：憑證只在部署設定區；平台不存憑證 | 例外 | unit 範本、`env.example` 的新行、下游頁（設定有填，繁中與英文）、`--r` 的輸出 | 以 `hosted_deploy_test.sh` TC-075 同一組樣式（`abf_pat_…`、`Bearer …`、`password=`、`ABF_PAT=`、私鑰標頭）加上 `sk-`、`AKIA`、`token=`、`key=` 掃描 | 全部沒有權杖、密碼、金鑰的形狀；unit 沒有任何 `--auth-*` 密碼選項；沒有 `/home/<名字>/` 路徑、沒有真實主機名 | 自動：`tests/studio_embed_deploy_test.sh`、`platform/tests/test_studio_embed.py` |
| TC-042 | 憲法：寫入要有人按（ADR 0006） | 例外 | 下游頁上兩行 R 指令與 `publish-figure` | 檢查指令與流程 | 第二行只送出「提議」，沒有任何自動確認的旗標或參數；存入仍要本人在確認頁按（既有確認流程測試原樣通過）；頁面本身沒有任何會寫入的新表單或新動作 | 自動：`platform/tests/test_studio_embed.py` |
| TC-043 | 憲法：文件說的就是程式做的 | 功能 | `docs/PLATFORM.md`、`web_downstream.py` 檔頭、`docs/TESTING.md` | 靜態檢查 | `PLATFORM.md` 在 CSP 那段（第 726 行一帶）把下游頁列為例外，不再有與實際不符的「每頁同樣標頭」、「只有……多 frame-src」說法；`web_downstream.py` 檔頭不再寫「never a frame」；`TESTING.md` 有 studio-embed 一節，含 TC-036～040 的步驟（三種瀏覽器、Plots 窗格、貼兩行指令、空白時的退路） | 自動：`tests/studio_embed_deploy_test.sh` |
