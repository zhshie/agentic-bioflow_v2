---
id: hosted-deploy
title: 一間實驗室一台主機的部署包（deploy/：systemd 單元＋Caddy https＋備份腳本）與 INSTALL／OPERATIONS 文件
tier: A
kinds: backend
lane: L5-deploy
base: v3（只新增 deploy/ 與 tests/ 新檔、改兩份文件；不碰 platform/ 程式碼，可與其他車道平行）
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 6 的 H-1（第 186 行）與拷問裁決 11（第 48 行）
---

# hosted-deploy

> 本檔由 developer-agent 助理草擬（2026-10-24）。**A 級**（會影響他怎麼把平台交給別人用）：verifier 通過後由他本人驗收，不自合。**只做檔案與靜態測試**：不真的部署、不連網、CI 沒有 Docker。「在 VPS 上實裝一次」與「在常開桌機開 Funnel」是他自己要做的事（replan 第 215 行），不在本任務。

## 目標
把平台三個程序（`abf-platform serve`／`mcp --http`／`web`）變成一包可以照抄就跑起來的部署檔：開機自動啟、當掉自動重啟、前面一個 Caddy 擋 https 與分流、一支備份腳本、一份只有佔位符的設定範例。同一份檔案先在常開桌機（Tailscale Funnel 當 https）試用，之後原封搬到租來的 VPS（Caddy 自動申請憑證）。

對他的意義：試用階段同事能用一個網址連上平台；收費階段不用重寫部署，只換網域；而且 `docs/INSTALL.md`／`docs/OPERATIONS.md` 第一次被一個真實流程驗證（目前 OPERATIONS 的第 2、3 節只寫「尚未建」）。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`：
- 「**H-1 `hosted-deploy`**（A／infra）：`deploy/` 一鍵部署（一間實驗室一台：Docker Compose 或 systemd；平台＋receiver＋Caddy https；備份 `platform.sqlite3` 與 `_personal/`）；`docs/OPERATIONS.md` 加「託管一間實驗室」一節；在 VPS 上實裝一次（他租，約 NT$150～300/月）。」（第 186 行）→ 每個名詞對應一條測試：`deploy/` 存在；平台＋receiver 即 `web`／`mcp`／`serve` 三個程序都有單元；Caddy 設定；備份腳本；OPERATIONS 有「託管一間實驗室」小節。（備份對象的實際檔名見裁決 5，與原文的 `platform.sqlite3`／`_personal/` 不同。）
- 「11. （10-21 第三輪）試用帳號＝**每位同事自己的 nano4 帳號**……平台主機：**兩個方向本來就都在路線圖**（ADR 0002 開源框架＝使用者自己架；ADR 0004 他託管收費＝像 cloud.seqera.io），程式同一份、只差部署地點。**試用跑在常開桌機 DESKTOP-7J5L5BJ＋Tailscale Funnel**（走「使用者自己架」那條，順便驗證 `docs/INSTALL.md`／`docs/OPERATIONS.md`）；開始收費時再租 VPS（走託管那條）。不另加任務，只在 M1-06 的 SETTINGS／OPERATIONS 補「公開網址」一節。」（第 48 行）→ 同一份 `deploy/` 要同時支援「Funnel 在前面」與「VPS 上 Caddy 直接對外」；文件兩條路都寫；既有「公開網址」小節（`docs/docs_nano4_keys.sh` 釘住）不能被弄壞。
- 「13. （10-21 拷問二）託管＝**一間實驗室一台平台**（每實驗室一個 VPS／容器，程式不改，不做跨實驗室隔離；ADR 0005 不動）。」（replan 第 52 行，同段）→ 部署包不含多租戶、不含跨實驗室任何東西；「程式不改」＝本任務不改 `platform/` 程式碼。
- 「8. 進度回報網址：本週用 Tailscale Funnel 給筆電平台一個 https 公開網址；正式版平台跑在常開機或託管主機的公開網址。程式改法兩者相同（`way_back: direct` ＋ `platform_public_url`），所以現在就照正式版的方式寫。」（第 44 行）→ Caddy 要把 Nextflow 的進度回報（receiver）也從同一個網址轉進去，不只轉網頁與 MCP。
- 「我自己要做的（不派）：在常開桌機裝 Tailscale Funnel 並把平台以 `--public-url` 跑起來（步驟給他看一次）……」（第 215 行）→ 文件寫到他照著做就能做；不替他執行。

## 範圍：檔案（只准改這些）
新增（全部在 `deploy/` 與 `tests/`）：
- `deploy/systemd/abf-serve.service`
- `deploy/systemd/abf-mcp.service`
- `deploy/systemd/abf-web.service`
- `deploy/Caddyfile.template`
- `deploy/backup.sh`
- `deploy/env.example`
- `tests/hosted_deploy_test.sh`（新；檔首照 repo 慣例寫目的與 TC 對應；`tests/run_all.sh` 會自動掃到，不必登記）
- `specs/hosted-deploy/ledger.md`（executor 進度帳本）

修改（只准動下列檔案的下列範圍）：
- `docs/OPERATIONS.md`：第 2 節（一個網址：改寫成現況，兩種前端）、第 3 節（單元檔：改成「`deploy/systemd/` 出貨」）、第 4 節（備份：指向 `deploy/backup.sh`）、第 6 節（刪掉已做的兩條）。**只用 `###` 小節加內容，不新增 `##` 標題**（見「既有測試」）。
- `docs/INSTALL.md`：只在第 1 節「What you need」與第 3 節 Claude Desktop 的「需要公開 https 位址」那段，補一句指向 OPERATIONS 的託管小節；不新增 `##`。
- `docs/TESTING.md`：新增「hosted-deploy」小節，寫手動驗收（見完成標準）。

**不准動（硬規則）**：
- `platform/abf_platform/`、`platform/abf_station/`、`platform/abf_launch/` 底下任何檔案（其他任務正在那裡跑）。
- **閘門檔，executor 開發期間不得編輯**（repo `CLAUDE.md`「For the executor and verifier」的 Never edit 清單，加上維護者交辦）：`spec.md`、`test-case*.md`（含 `specs/hosted-deploy/test-case.md`、`test-case-overview.md`，由 verifier 出）、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/` 底下全部（含 `workflows/tests.yml`）、`.claude-plugin/plugin.json`、`platform/pyproject.toml`（維護者交辦：視為閘門檔，本任務不需要動）。
- 既有的 `tests/*.sh`、`platform/tests/*.py`：不改（見下節）。

## 作法
1. **選型與搜尋紀錄（決定：systemd 使用者單元＋Caddy，不用 Docker Compose）**。
   - 搜過：「Caddy reverse_proxy automatic HTTPS systemd Python web service vs Docker Compose」→ 結果幾乎都是 Caddy 放在 Docker Compose 裡的寫法（`caddy:alpine` 容器、80／443、掛 Caddyfile），沒有找到把兩種做法逐項比較的來源；「Tailscale Funnel serve set-path 443 8443 10000」→ 官方 CLI 文件 https://tailscale.com/docs/reference/tailscale-cli/funnel：Funnel 只開 443、8443、10000 三個埠，反向代理目標目前只支援 `http://127.0.0.1`。
   - 候選：①Docker Compose＋`caddy:alpine`（網路上最常見）；②systemd 單元＋主機上的 Caddy（Caddy 官方就有 systemd 與 apt 套件）。
   - 採 ②，一行理由：這個專案的 OPERATIONS 第 3 節本來就是 systemd 使用者單元、首位主機是 Windows 桌機上的 WSL（裝 Docker Desktop 太重）、而且 gcb 路徑需要平台主機有 Java／Nextflow／gcloud，包進容器會更複雜；同一組單元檔在 VPS 與 WSL 都能用。Compose 版若將來需要，另開任務（不在本任務）。
   - 沒找到可直接套用的現成 repo（搜到的多是通用 Caddy 範例），所以 `deploy/` 自己寫，檔案很小。
2. **三個單元檔（使用者單元，`WantedBy=default.target`，配 `loginctl enable-linger`）**：
   - `abf-serve.service`：`ExecStart=%h/<venv>/bin/abf-platform serve --host 127.0.0.1 --port 8787`
   - `abf-mcp.service`：`… mcp --http --host 127.0.0.1 --port 8788 --public-url ${ABF_PUBLIC_URL}`
   - `abf-web.service`：`… web --host 127.0.0.1 --port 8789 --public-url ${ABF_PUBLIC_URL}`
   - 三個都有：`EnvironmentFile=%h/.config/abf-platform/env`、`Restart=on-failure`、`RestartSec=5`、`NoNewPrivileges=true`、`PrivateTmp=true`。`<venv>` 是佔位符，文件說明怎麼換成實際路徑。單元裡**不得**有任何 token、密碼、金鑰、主機名稱。
   - 不加 `ProtectHome`／`ProtectSystem`（資料夾在 `$HOME` 底下，加了會讓服務寫不進去；不加不是疏漏）。
3. **`deploy/env.example`**（複製成 `~/.config/abf-platform/env`，權限 600）：只放佔位符與註解：`ABF_PUBLIC_URL=https://<your-domain>`、`ABF_PLATFORM_DB=<data-folder>/index.db`（可省略，預設見 OPERATIONS 第 4 節）、`ABF_SITE_ADDRESS=<your-domain>`（Caddy 用）。**不放**任何 `ABF_PAT`、密碼、token；註解寫明「權杖只用 `abf-platform pat new` 當下顯示一次，不進任何檔案」。
4. **`deploy/Caddyfile.template`**：一份模板、兩種用法，站台位址用環境變數 `{$ABF_SITE_ADDRESS}`：
   - **VPS（Caddy 直接對外）**：`ABF_SITE_ADDRESS=<your-domain>` → Caddy 自動申請並續期憑證（Let's Encrypt）。
   - **常開桌機（Funnel 在前面）**：`ABF_SITE_ADDRESS=http://127.0.0.1:8080` → Caddy 只在本機 8080 收 http（開頭是 `http://` 就不做自動 https），Funnel 用 `tailscale funnel --bg 8080` 指到它並負責 https。
   - 分流（`handle` 區塊，**最後一條是兜底，一定要放最後**）：進度回報與 agent 的路徑 → `127.0.0.1:8787`；`/mcp*` 與 OAuth 相關路徑（`/.well-known/*` 與 `mcp_server.py` 的 `auth_routes` 列出的授權／換票／註冊路徑）→ `127.0.0.1:8788`；其餘一律 → `127.0.0.1:8789`（網頁）。**executor 要先讀 `platform/abf_platform/receiver.py`（`/trace/*`、`/user-info`，另需找出 agent 請求的路徑）與 `mcp_server.py` 的路由，把實際路徑逐一列進模板，並在測試裡斷言「模板裡每條路徑前綴在原始碼中都找得到」**，不憑記憶寫。
   - 加 `header` 不是必要；不加 log 檔路徑（用預設，journald）。
5. **`deploy/backup.sh`**（bash，`set -euo pipefail`，`#!/usr/bin/env bash`）：備份對象照 `docs/OPERATIONS.md` 第 4 節實際表格，**不是 replan 原文的 `platform.sqlite3`／`_personal/`**（那兩個名字在 v3 不存在，見裁決 5）：`tokens.db`、`platform.db`（SQLite，用一致性備份：`sqlite3 <db> ".backup <dest>"`，沒有 `sqlite3` 指令時退而用 `python3 -c` 的 `sqlite3` 模組 `Connection.backup`；不用 `cp` 直接複製正在寫的資料庫）、`web_signing.key`、`uploads/`、`records/`。**不備份** `index.db`（可 `abf-platform rebuild` 重建）。輸出到 `$1`（目的資料夾，必填）下的 `abf-backup-<UTC 時間>/`，目錄 700、檔案 600；資料夾位置從 `ABF_PLATFORM_DB`／`XDG_DATA_HOME` 推導，與 `store.py` 的 `default_index_path` 規則一致；不連網、不上傳、不刪舊備份（保留與搬出主機是文件裡寫的人工步驟）。缺任何必備檔就非零結束並用白話說缺哪個。
6. **文件**（`docs/OPERATIONS.md`，全用英文，與現有文件一致）：
   - 第 2 節改寫：兩種前端（VPS 的 Caddy／桌機的 Funnel）各一個步驟清單，指向 `deploy/Caddyfile.template`；Funnel 部分只寫指令（`tailscale funnel --bg 8080`）與埠限制，不寫維護者自己的主機名；「Not built yet」中對應兩條刪除。
   - 第 3 節改寫：說明單元檔在 `deploy/systemd/`，安裝步驟（複製到 `~/.config/systemd/user/`、`systemctl --user daemon-reload`、`enable --now`、`loginctl enable-linger <user>`）；保留「權杖不進單元檔」那句。
   - 第 4 節加一句 `deploy/backup.sh` 的用法與「還原＝停三個服務、把檔案放回資料夾」。
   - 新增 `### Hosting one lab`（放在第 5 節底下，與既有 `### Public URL`、`### Google Batch…` 並列，**標題含「託管一間實驗室」的英文對應 `Hosting one lab`，並在小節第一行用中文括號標一次「託管一間實驗室」**）：一間實驗室一台、VPS 的最低需求（Linux、可開 80／443、Python 3.10+、systemd）、建立專用使用者與 `enable-linger`、從零到「`curl -i https://<your-domain>/user-info` 回 401 且有 `X-ABF-Platform` 標頭」的逐步清單、備份排程範例（cron 或 systemd timer，**只寫範例文字**，不出貨檔案）、升級步驟。
   - 範例一律只用 `<your-domain>`、`<venv>`、`<data-folder>`；不寫真實主機名、不寫 `DESKTOP-7J5L5BJ`、不寫 tailnet 名稱。
   - `docs/INSTALL.md` 的補句**不得**含 snake_case 的反引號詞（`install_doc_test.sh` TC-005 會把它當成 MCP 工具名去查）。
7. **測試（`tests/hosted_deploy_test.sh`，純靜態，不需 Docker、不連網、不啟動任何服務）**：用 grep／sed／awk／bash 內建剖析檔案；`systemd-analyze` 不在 CI 保證存在，**不得依賴**（有的話可額外跑 `verify` 當加分，沒有就略過並印 skip，不算失敗）。

## 失敗先行測試（`tests/hosted_deploy_test.sh`，現在都會紅，因為 `deploy/` 還不存在）
- `TC deploy-files`：`deploy/systemd/abf-{serve,mcp,web}.service`、`deploy/Caddyfile.template`、`deploy/backup.sh`、`deploy/env.example` 六個檔都存在、非空、`backup.sh` 有執行權限位且首行為 shebang。
- `TC three-services`：三個單元的 `ExecStart` 各恰好是 `abf-platform serve`／`mcp --http`／`web`，且三個子命令名稱都真的存在於 `platform/abf_platform/cli.py`（同 `operations_doc_test.sh` 的 `add_parser` 比對法）。
- `TC ports-localhost-only`：三個單元分別含 `--host 127.0.0.1` 與 `--port 8787`／`8788`／`8789`（serve／mcp／web）；任何單元、Caddyfile、env 範例**不得**出現 `0.0.0.0`、`[::]`、`--host ::`，也不得有 `--host` 後面接非 loopback 位址；Caddyfile 的每個 `reverse_proxy` 目標都是 `127.0.0.1:<8787|8788|8789>`。
- `TC ports-match-code`：單元裡的預設埠與 `cli.py` 中 `serve`／`web`／`mcp` 的 `default=` 一致（防止程式改了埠、部署檔沒跟）。
- `TC caddy-routes`：Caddyfile 分三段，`/trace/*` 與 `/user-info` 指 8787、`/mcp*` 與 `/.well-known/*` 指 8788、最後的兜底指 8789；兜底 `handle` 是檔案中最後一個 `handle`；模板內出現的每個路徑前綴在 `platform/abf_platform/*.py` 原始碼中都找得到。
- `TC caddy-https`：Caddyfile 使用 `{$ABF_SITE_ADDRESS}`，沒有寫死的網域；有 `reverse_proxy` 且沒有 `tls internal`／`auto_https off` 之類會關掉憑證的寫法（Funnel 用法靠 `http://` 位址自然不申請，不需要關閉開關）。
- `TC restart-and-env`：三個單元都有 `Restart=on-failure`、`EnvironmentFile=`、`WantedBy=default.target`。
- `TC no-secrets`：所有 `deploy/` 檔案與兩份文件的新增內容，沒有 `abf_pat_` 後接 8 個以上英數字、沒有 `Bearer ` 後接實際值（`<PAT>` 佔位符可）、沒有 `password=`／`ABF_PAT=` 後接非 `<…>` 的值、沒有私密金鑰標頭字串（**測試內用字串拼接組出要找的樣式，例如 `"-----BEGIN ""PRIVATE KEY"`，不要在測試或任何檔案寫出字面**——`tests/credentials_stay_in_settings_test.sh` 會掃）。
- `TC no-real-host`：`deploy/` 檔案與文件新增內容不含 `DESKTOP-7J5L5BJ`、不含 `.ts.net`（tailnet 主機名）、不含 `nchc.org.tw` 的帳號 `u9613010`；網域一律是 `<your-domain>` 形式。
- `TC env-example-placeholders`：`deploy/env.example` 每個有值的行，值都是 `<…>` 佔位符、`https://<your-domain>`、`127.0.0.1…` 或空；沒有 `=` 後接長英數字串（長度 ≥ 20）。
- `TC backup-script`：`backup.sh` 通過 `bash -n`；內容含 `set -euo pipefail`、含 `tokens.db`、`platform.db`、`web_signing.key`、`uploads`、`records`，**不含** `index.db` 的複製（只可出現在「不備份」註解），不含 `curl`、`wget`、`scp`、`rsync`、`ssh`（不連網）、不含 `rm `；呼叫 `.backup` 或 Python `backup`，不是裸 `cp` 資料庫。
- `TC backup-script-runs`（可跑的行為測試，在臨時資料夾）：建一個假的資料夾（兩個真 SQLite 檔用 `python3` 建、另三項各放一個小檔），設 `ABF_PLATFORM_DB` 指向它，跑 `deploy/backup.sh <tmp>/out`：結束碼 0；輸出目錄存在；兩個資料庫備份能被 `python3` 開起來且內容相同；`index.db` 沒被複製；缺 `tokens.db` 時非零結束且訊息提到 `tokens.db`；權限為 700／600（`stat`；在 Git Bash 沒有 POSIX 權限語意時略過這一條並印 skip）。
- `TC docs-host-section`：`docs/OPERATIONS.md` 有 `### Hosting one lab`、含「託管一間實驗室」、含 `deploy/systemd`、`deploy/Caddyfile.template`、`deploy/backup.sh`、`loginctl enable-linger`、`tailscale funnel`、`<your-domain>`；「Not built yet」一節不再含「Service-manager unit files」那條與「Tailscale Funnel and proxy configuration」那條。
- `TC docs-paths-exist`：兩份文件中反引號包住的 `deploy/…` 路徑都真的存在。
- `TC no-code-touched`：`git diff --name-only <base>…HEAD` 不含 `platform/abf_platform/`、`platform/abf_station/`、`platform/abf_launch/`、`platform/pyproject.toml`、`docs/ROADMAP.md`、`.github/`（base 取 `origin/v3`；沒有 git 或 base 時略過並印 skip）。

## 完成標準（done when）
- 自動：`bash tests/hosted_deploy_test.sh` 全綠；下列既有測試原樣綠：`bash tests/operations_doc_test.sh`、`bash tests/install_doc_test.sh`、`bash tests/docs_nano4_keys.sh`、`bash tests/harness_kits_test.sh`、`bash tests/credentials_stay_in_settings_test.sh`，以及 `platform/tests/test_gcb_launch.py` 的文件斷言（第 1163 行）；完整套件 `tests/run_all.sh` 在 WSL／Linux 綠。
- 驗收者看 `git diff --name-only origin/v3...HEAD`：只出現「範圍」列出的檔案。
- 手動（維護者，**不是本任務執行**，記入 `docs/TESTING.md` 的 hosted-deploy 小節）：
  1. 常開桌機（WSL）：複製單元檔、填 `env`、`systemctl --user enable --now` 三個服務，`systemctl --user status` 皆 active。
  2. 本機起 Caddy（`ABF_SITE_ADDRESS=http://127.0.0.1:8080`），`tailscale funnel --bg 8080`；從手機行動網路開 `https://<funnel 網址>/` 看到登入頁；`curl -i https://<funnel 網址>/user-info` 回 401 且有 `X-ABF-Platform`。
  3. 把 Claude Desktop 的連接器指到 `https://<funnel 網址>/mcp`，走完 OAuth 登入與同意頁（`docs/TESTING.md` 既有待記錄的那項）。
  4. 殺掉其中一個服務程序，5 秒內被 systemd 拉起。
  5. 跑 `deploy/backup.sh ~/backups`，從備份還原到空資料夾後 `abf-platform pat list` 能列出權杖。
  6. 租 VPS 後同一組檔案、改 `ABF_SITE_ADDRESS=<your-domain>`，Caddy 自動取得憑證（H-1 原文的「在 VPS 實裝一次」）。

## 環境事實
（行號為 2026-10-24 讀 `origin/v3`）
- 三個子命令與預設：`platform/abf_platform/cli.py` 第 506–516、590–596 行：`serve --host 127.0.0.1 --port 8787`、`web --host（只收 loopback）--port 8789 --public-url`、`mcp --http --host 127.0.0.1 --port 8788 --public-url`。**三個程序已經有綁定位址旗標，部署不需要程式改動。** `web --public-url` 若是非 loopback 的 http 會被拒絕；`web --host` 非 loopback 會被拒絕（第 62–70 行）。
- 資料資料夾：`platform/abf_platform/store.py` 第 268–286 行：`ABF_PLATFORM_DB`（預設 `${XDG_DATA_HOME:-~/.local/share}/abf-platform/index.db`）、`ABF_PLATFORM_TOKENS`、`ABF_PLATFORM_STATE` 預設都在 index 旁邊。要備份的檔案表在 `docs/OPERATIONS.md` 第 4 節。
- receiver 路徑（`platform/abf_platform/receiver.py` 第 277–282 行）：`/trace/create`、`/trace/{rid}/begin|progress|heartbeat|complete`、`/user-info`。MCP 與 OAuth：`mcp_server.py` 第 526 行起（`/.well-known/oauth-authorization-server` 等）。網頁路由：`web.py` 第 592–597 行（`/`、`/settings`、`/launch`、`/act/{verb}`、`/login`、`/logout`、`/c/{rid}`、`/consent/{rid}`）。agent 對 8787 的請求路徑本檔未逐一列出，executor 須自行找出（`grep -n "Route(" platform/abf_platform/*.py platform/abf_platform/actions/*.py`）。
- 套件入口：`platform/pyproject.toml` 的 `[project.scripts]`：`abf-platform`、`abf-station`；Python ≥3.10；依賴只有 `mcp>=2.3,<3`。安裝在 venv 裡，單元的 `ExecStart` 指 venv 的 `bin/abf-platform`。
- Funnel：只開 443／8443／10000，代理目標只支援 `http://127.0.0.1`（Tailscale 官方 CLI 文件，2026-10-24 讀）。所以桌機路徑是「Funnel → 127.0.0.1:8080 的 Caddy → 三個程序」。
- ADR：`docs/adr/0002-open-core-apache.md`（開源、使用者自己架）與 `docs/adr/0004-self-hosted-platform-mcp-first.md`（維護者託管，像 cloud.seqera.io）決定了「同一份程式、兩種部署地點」；`docs/SETTINGS.md` 第 308–319 行的 `way_back: direct` 與 `platform_public_url`（必須 https）是進度回報要走公開網址的原因。
- 既有文件測試（見下節）釘住了文件結構；`tests/run_all.sh` 會自動掃 `tests/*.sh`，新測試不必登記；它拒絕原生 Git Bash，要在 WSL／Linux 跑。
- 系統上 CI 沒有 Docker，也不保證有 Caddy、systemd、sqlite3 指令；測試只能靠 bash 與 `python3`。

## 既有測試：哪些斷言可能因本任務的文件修改而被影響
**不准改這些測試；若紅了，改文件，不改測試。** 逐項列出的是會踩到的釘子：
- `tests/operations_doc_test.sh`：**OPERATIONS.md 必須剛好 6 個 `## ` 標題**，順序比對 `[Pp]rocess`、`[Hh]ost|TLS`、`[Rr]unning`、`[Bb]ack`、`[Aa]dmin`、`Not built yet`（所以新內容只能放 `###` 以下，不要改既有六個標題的關鍵字）；文件中每個 `abf-platform <word>` 的 `<word>` 必須是 `cli.py` 的真子命令（文件別寫 `abf-platform backup` 之類不存在的命令；備份腳本寫 `deploy/backup.sh`）；反引號包住、以 `docs|platform|tests|scripts|skills|hooks|specs|configs|extensions` 開頭並有副檔名的路徑必須存在（`deploy/` 不在此清單內，但引用 `tests/hosted_deploy_test.sh` 時必須存在）。
- `tests/install_doc_test.sh`：INSTALL.md 必須剛好 6 個 `##`，依序以 `What you need`、`Claude Code`、`Claude Desktop`、`Codex`、`Check it works`、`Not built yet` 開頭；每個 `abf-platform <sub>` 必須存在；**反引號裡長得像 `snake_case` 的詞會被當成 MCP 工具名去 `mcp_server.py` 查**（所以 INSTALL 不要寫 `platform_public_url`、`way_back` 之類，這兩個詞只能出現在 OPERATIONS／SETTINGS）；反引號路徑含 `/` 且有副檔名者必須存在於 repo；不得有 `abf_pat_` 後接 8 個以上英數字。
- `tests/docs_nano4_keys.sh`（TC-026～029）：OPERATIONS.md 必須保留一個符合 `^###+ .*([Pp]ublic URL|公開網址)` 的標題，並含 `Tailscale Funnel`、`user-info`、`401`、`X-ABF-Platform`。
- `tests/harness_kits_test.sh`：讀 INSTALL.md（第 56–89 行）做套件與文件一致性檢查；INSTALL 只加一句，改完先跑。
- `platform/tests/test_gcb_launch.py` 第 1163 行：`INSTALL.md + OPERATIONS.md` 合起來必須仍含 `Java 17`、`Nextflow`、`gcloud`，且不含非 `lab-project-1` 的 `…@….iam.gserviceaccount.com`；既有的「Google Batch on the platform host」小節（OPERATIONS 第 107 行起）整段保留。
- `tests/credentials_stay_in_settings_test.sh`：掃整個 repo 的祕密樣式；新檔與測試內都用拼接，不寫金鑰標頭字面。
- `specs/ops-doc/test-case.md`、`specs/install-doc/…`（若存在）：屬閘門檔，不改；以其對應的上述 `.sh` 為準。

## 不做
- 不真的部署、不裝 Caddy、不開 Funnel、不租 VPS、不呼叫任何網路（那些是他自己做，replan 第 215 行）。
- 不寫 Docker Compose／Dockerfile（選型已定 systemd；Compose 版另開任務）。
- 不改 `platform/abf_platform/`、`platform/abf_station/`、`platform/abf_launch/` 任何檔案；不加旗標、不改預設埠。若發現確實需要程式改動，寫進下面「待 developer-agent 裁決」，不要自己動手。
- 不出貨安裝腳本（`install.sh`）、不出貨備份排程單元（文件只給範例文字）、不做自動備份上傳／輪替。
- 不做多實驗室／多租戶（ADR 0005 不動）、不做監控告警、不做 WAF 或速率限制。
- 不處理站台代理（`abf-station`）的部署；雲端（Google Batch）用的代理跑在平台主機上，其單元檔不在本任務。
- 不改 `docs/ROADMAP.md`（閘門檔）；ROADMAP 的勾選由維護者在驗收後處理。

## 裁決（2026-10-24，developer-agent 助理草擬；與上文衝突時以本段為準）
1. **systemd 使用者單元＋Caddy，不做 Docker Compose。** 理由見作法 1。**另一選項**：Compose＋`caddy:alpine`，換來「VPS 上一個指令起全部」，代價是 Windows 桌機要 Docker Desktop、gcb 需要的 Java／Nextflow／gcloud 要另外處理。**預設：systemd。**
2. **一份 `Caddyfile.template`，用 `ABF_SITE_ADDRESS` 切換 VPS／Funnel 兩種用法**，不拆成兩個檔。理由：模板只有分流規則不同於「前面是誰」，拆開會讓兩份分流規則漂移。
3. **單元用「使用者單元」而非系統單元。** 理由：與現有 OPERATIONS 第 3 節一致、不需要 root、桌機的 WSL 與 VPS 同一套；代價是 VPS 上要建專用使用者並 `enable-linger`（文件寫明）。
4. **三個服務全部只綁 127.0.0.1，由 Caddy 對外**（維護者要求「Caddy https」；`web` 本來就拒絕非 loopback）。
5. **備份對象照 v3 實際檔案**（`tokens.db`、`platform.db`、`web_signing.key`、`uploads/`、`records/`），不照 replan 原文的 `platform.sqlite3`／`_personal/`（v3 沒有這兩個名字；`_personal/` 是站台代理的個人資料夾，屬代理主機而非平台）。SQLite 用一致性備份而不是 `cp`。**請維護者知悉原文名稱已校正。**
6. **進度回報（`/trace/*`）也從公開網址轉進 8787。** 理由：replan 第 44 行，`way_back: direct` 的計算節點要打公開 https 網址；這代表 8787 的 receiver 也經 Caddy 暴露，它自己靠 run token 驗證（`/user-info` 無 token 回 401）。
7. **新測試是 shell 檔（`tests/hosted_deploy_test.sh`），不是 pytest。** 理由：維護者指示用 shell 測試；與 `operations_doc_test.sh` 同風格；不依賴 Docker／systemd／Caddy。

## 待 developer-agent 裁決
（本任務不改程式；以下若成立再開別的任務）
1. **agent 請求的路徑有沒有集中前綴？** 若散在 `receiver.py` 多處，Caddy 的 8787 分流清單會很長且易漏。建議之後在 `platform/abf_platform/` 加統一前綴（例如 `/agent/*`）；現在先由 executor 把實際路徑逐條列進模板，並以測試鎖住「模板路徑在原始碼都存在」。
2. **是否要 `serve` 也能被 Caddy 之外的人打到？** 目前三個都只綁 loopback，沒有程式改動需求。若將來要把 receiver 放另一台機器，才需要綁定位址旗標與非 loopback 的風險提示（`serve` 已有 `_risk_line`）。
3. **OAuth 的授權／換票路徑是否全在 `/.well-known` 與 `/mcp` 底下？** 若不是（`mcp_server.py` 第 526 行附近的 `auth_routes` 另有根路徑），Caddy 要為它們各開一條，executor 須逐條對照，發現有路徑落在 8789（網頁）卻應屬 8788 就停下回報。
4. **`platform/pyproject.toml` 的 `package-data` 不含 `deploy/`**：`deploy/` 是 repo 級檔案，不隨 pip 套件安裝。使用者要用就得 clone repo。若將來希望「`pip install` 後 `abf-platform deploy-init` 吐出這些檔」，要改 pyproject 與 cli，另案。

## 裁決二（2026-10-24 developer-agent，回答上面待裁決；以本段為準）
8. 待裁決 1、3：executor 逐條從原始碼列出 8787／8788 的實際路徑寫進模板，測試鎖住「模板裡每個路徑前綴在原始碼都找得到」以及「原始碼的每條路由都有對應分流」；發現路徑歸屬不明（同一前綴兩個服務都有）就停下回報 BLOCKED，不猜。統一前綴另案。
9. 待裁決 2、4：維持現狀，不改程式、不改 pyproject；deploy/ 隨 repo 發，不進 pip 套件。
10. 不寫 install.sh；「一鍵」＝文件裡一段可整段複製的指令。
11. 專長守則用 backend（沒有 infra 守則檔）。A 級：verifier 通過＋CI 綠由 developer-agent 自己合併。
12. 裁決 5 的備份檔名校正接受。

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
