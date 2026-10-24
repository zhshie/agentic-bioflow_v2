# 測試案例：hosted-deploy —— 一間實驗室一台主機的部署包（systemd＋Caddy＋備份）

<!--
Written by the verifier (CONTRACT mode, 2026-10-24) from specs/hosted-deploy/plan.md (including 裁決 / 裁決二 / 裁決三 and the 專長守則 backend), the constitution, and the maintainer's lines quoted in the plan.
There is no spec.md; the plan is the only source (裁決 17 accepts this). The maintainer said the test cases must come from the examples in the plan, so every case below is taken from a sentence of the plan. Nothing is invented beyond what the plan states.
Where the plan's body and 裁決三 disagree (the Caddy routing split), 裁決三 wins, as the plan itself says.
Reader: the maintainer, who is not an engineer.
-->

**規格**：`specs/hosted-deploy/plan.md`（無 spec.md；計畫即來源）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺東西、寫錯、做了不該做的事時，檔案或腳本怎麼反應（拒絕、停下、說白話）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式說明：「自動」是 `tests/hosted_deploy_test.sh`（純靜態＋臨時資料夾裡的備份腳本實跑；不需要 Docker、Caddy、systemd、網路）或計畫點名的既有測試。「手動」是驗收者讀檔案、對照 `git diff` 或 `docs/TESTING.md`。本任務**不做**真的部署（不裝 Caddy、不開 Funnel、不租 VPS），那是維護者自己的事，寫在 `docs/TESTING.md` 的 hosted-deploy 小節。

名詞：**單元檔**＝systemd 用來「開機自動啟動、當掉自動重啟」一個程式的設定檔。**Caddy**＝擋在最前面、負責 https 與分流的小程式。**Funnel**＝Tailscale 的功能，把桌機上的埠變成一個公開 https 網址。**loopback／127.0.0.1**＝只有這台機器自己連得到的位址。**一致性備份**＝複製正在被寫入的資料庫時，保證複製出來的檔案是完整可開的（不是複製到一半）。

## User Story 1 — 三個程序各有一個單元檔，開機自動啟、當掉自動重啟、只聽本機（優先度 P1）

來源：計畫「目標」「作法 2、3」「失敗先行測試」前七條；維護者原話 H-1「平台＋receiver 即 `web`／`mcp`／`serve` 三個程序都有單元」「`deploy/` 存在」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 TC `deploy-files`；H-1「`deploy/` 存在」 | 功能 | 實作完成 | 檢查 `deploy/systemd/abf-serve.service`、`abf-mcp.service`、`abf-web.service`、`deploy/Caddyfile.template`、`deploy/backup.sh`、`deploy/env.example` | 六個檔都存在且不是空檔 | 自動：`tests/hosted_deploy_test.sh` |
| TC-002 | 計畫 TC `deploy-files`；作法 5 | 功能 | 同上 | 看 `deploy/backup.sh` 的權限與第一行 | 有執行權限位；第一行是 shebang，且為 `#!/usr/bin/env bash` | 自動 |
| TC-003 | 計畫 TC `three-services`；H-1「三個程序都有單元」 | 功能 | 同上 | 讀三個單元的 `ExecStart` | `abf-serve.service` 跑的是 `abf-platform serve`、`abf-mcp.service` 是 `abf-platform mcp --http`、`abf-web.service` 是 `abf-platform web`；三者各自**恰好**一個子命令，沒有互相串錯；可執行檔路徑用 `<venv>` 佔位符（如 `%h/<venv>/bin/abf-platform`），不是真實路徑 | 自動 |
| TC-004 | 計畫 TC `three-services` | 功能 | 同上 | 把 TC-003 的三個子命令名稱拿去對 `platform/abf_platform/cli.py` 的 `add_parser(...)` | 三個名稱（`serve`、`mcp`、`web`）都真的是 `cli.py` 的子命令 | 自動 |
| TC-005 | 計畫 TC `ports-localhost-only`；作法 2 | 功能 | 同上 | 讀三個單元 `ExecStart` 的 `--host` 與 `--port` | 三個都有 `--host 127.0.0.1`；埠依序是 serve `8787`、mcp `8788`、web `8789` | 自動 |
| TC-006 | 計畫 TC `ports-match-code` | 功能 | 同上 | 把單元裡的埠對 `cli.py` 中 `serve`／`web`／`mcp` 的 `default=` | 兩邊一致（程式改了預設埠、部署檔沒跟，這條會紅） | 自動 |
| TC-007 | 計畫 TC `ports-localhost-only`；裁決 4 | 例外 | 同上 | 在三個單元、`deploy/Caddyfile.template`、`deploy/env.example` 搜尋對外綁定寫法 | 找不到 `0.0.0.0`、`[::]`、`--host ::` | 自動 |
| TC-008 | 計畫 TC `ports-localhost-only` | 例外 | 同上 | 列出三個單元每一個 `--host` 後面接的值 | 每個值都是 loopback（`127.0.0.1`）；沒有任何非 loopback 位址 | 自動 |
| TC-009 | 作法 2 | 功能 | 同上 | 讀 `abf-mcp.service` 與 `abf-web.service` 的 `ExecStart` | 兩者都帶 `--public-url ${ABF_PUBLIC_URL}`（由 env 檔提供網址） | 自動 |
| TC-010 | 計畫 TC `restart-and-env`；作法 2 | 功能 | 同上 | 讀三個單元 | 每個都有 `Restart=on-failure` 與 `RestartSec=5` | 自動 |
| TC-011 | 計畫 TC `restart-and-env`；作法 2 | 功能 | 同上 | 讀三個單元 | 每個都有 `EnvironmentFile=%h/.config/abf-platform/env` | 自動 |
| TC-012 | 計畫 TC `restart-and-env`；作法 2、裁決 3 | 功能 | 同上 | 讀三個單元的 `[Install]` | 每個都是 `WantedBy=default.target`（使用者單元，不是系統單元） | 自動 |
| TC-013 | 作法 2 | 功能 | 同上 | 讀三個單元 | 每個都有 `NoNewPrivileges=true` 與 `PrivateTmp=true` | 自動 |
| TC-014 | 作法 2「不加 `ProtectHome`／`ProtectSystem`」 | 不在範圍 | 同上 | 在三個單元搜尋 | 沒有 `ProtectHome`、沒有 `ProtectSystem`（資料夾在 `$HOME` 底下，加了會寫不進去） | 自動 |
| TC-015 | 計畫「作法 3」 | 功能 | 同上 | 讀 `deploy/env.example` | 有 `ABF_PUBLIC_URL=https://<your-domain>`、`ABF_PLATFORM_DB=<data-folder>/index.db`、`ABF_SITE_ADDRESS=<your-domain>` 三項，並有註解說明（複製成 `~/.config/abf-platform/env`、權限 600） | 自動 |
| TC-016 | 計畫 TC `env-example-placeholders` | 功能 | 同上 | 逐行看 `deploy/env.example` 每個有值的行 | 每個值都是 `<…>` 佔位符、`https://<your-domain>`、`127.0.0.1…` 開頭，或空；沒有 `=` 後面接長度 ≥ 20 的英數字串 | 自動 |
| TC-017 | 作法 3 | 功能 | 同上 | 讀 `deploy/env.example` 的註解 | 寫明「權杖只用 `abf-platform pat new` 當下顯示一次，不進任何檔案」的意思；檔內沒有 `ABF_PAT` 這類權杖變數 | 自動 |

## User Story 2 — Caddy 擋在前面：https 與分流，兩種前端共用一份模板（優先度 P1）

來源：計畫作法 4、TC `caddy-routes`／`caddy-https`、**裁決三 13～14（蓋過作法 4 的路徑歸屬）**；維護者原話第 44 行「Caddy 要把 Nextflow 的進度回報（receiver）也從同一個網址轉進去」、第 48 行「同一份 `deploy/` 要同時支援 Funnel 在前面與 VPS 上 Caddy 直接對外」。

分流歸屬（照 `platform/abf_platform/` 原始碼，裁決三 13）：
`/trace/*`、`/user-info`、`/agent/hello`、`/agent/poll`、`/agent/result/*` → 8787；`/mcp*`、`/.well-known/oauth-protected-resource*` → 8788；`/.well-known/oauth-authorization-server`、`/register`、`/authorize`、`/token`、`/revoke`、`/consent/*` → 8789；其餘一律 → 8789。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 裁決三 13；維護者第 44 行（進度回報也從同一網址轉進去）；計畫 TC `caddy-routes` | 功能 | 實作完成 | 讀 `deploy/Caddyfile.template`，找 `/trace/*` 與 `/user-info` 屬於哪個 `handle` | 兩者都指到 `127.0.0.1:8787` | 自動：`tests/hosted_deploy_test.sh` |
| TC-019 | 裁決三 13（`agents.py` 的 agent 路徑） | 功能 | 同上 | 找 `/agent/hello`、`/agent/poll`、`/agent/result/*` | 三者都指到 `127.0.0.1:8787` | 自動 |
| TC-020 | 裁決三 13；H-1「平台＋receiver」 | 功能 | 同上 | 找 `/mcp*` 與 `/.well-known/oauth-protected-resource*` | 兩者都指到 `127.0.0.1:8788` | 自動 |
| TC-021 | 裁決三 13（`web.py` 的 `auth_routes`） | 功能 | 同上 | 找 `/.well-known/oauth-authorization-server`、`/register`、`/authorize`、`/token`、`/revoke`、`/consent/*` | 六者都指到 `127.0.0.1:8789`（不是 8788） | 自動 |
| TC-022 | 計畫 TC `caddy-routes`；作法 4「最後一條是兜底」 | 功能 | 同上 | 看檔案裡最後一個 `handle` | 最後一個 `handle` 是不帶路徑條件的兜底，指到 `127.0.0.1:8789`（網頁）；它之後沒有別的 `handle` | 自動 |
| TC-023 | 裁決三 13；待裁決 3 的前提被改 | 例外 | 同上 | 在模板搜尋 `/.well-known/*`（整段萬用）這種寫法 | 不存在。因為 `/.well-known/oauth-authorization-server` 在 8789，一條 `/.well-known/*` → 8788 會把它送錯地方 | 自動 |
| TC-024 | 計畫 TC `caddy-routes`；作法 4「不憑記憶寫」 | 功能 | 同上 | 取出模板內每一個路徑前綴，去 `platform/abf_platform/*.py` 找 | 每個前綴都找得到依據：要嘛該字串在原始碼裡逐字出現（如 `/trace/`、`/agent/`、`/user-info`、`/consent/`、`/register`、`/mcp`），要嘛是原始碼呼叫了 SDK 的路由產生函式（`create_auth_routes`→`/authorize`、`/token`、`/revoke`；`create_protected_resource_routes`→`/.well-known/oauth-protected-resource`）；測試要寫明每個前綴採哪一種依據 | 自動 |
| TC-025 | 裁決二 8「原始碼的每條路由都有對應分流」 | 功能 | 同上 | 反向：列出 `receiver.py`（`/trace/create`、`/trace/{rid}/begin\|progress\|heartbeat\|complete`、`/user-info`）、`agents.py`（三條 `/agent/…`）、`mcp`／`http_auth.py`（`/mcp`、protected-resource）、`web.py` 的 `auth_routes` 與 `/consent/{rid}` 的路由 | 上列每一條，模板裡都有一個涵蓋它、且指到 TC-018～021 所列後端的前綴；沒有路由掉進錯的後端 | 自動 |
| TC-026 | 計畫 TC `ports-localhost-only` | 功能 | 同上 | 列出 Caddyfile 每個 `reverse_proxy` 的目標 | 至少有一個 `reverse_proxy`；每個目標都恰好是 `127.0.0.1:8787`、`127.0.0.1:8788` 或 `127.0.0.1:8789` | 自動 |
| TC-027 | 計畫 TC `caddy-https`；裁決 2；維護者第 48 行 | 功能 | 同上 | 讀 Caddyfile 的站台位址 | 站台位址是 `{$ABF_SITE_ADDRESS}`；檔內沒有寫死的網域或 `.ts.net` 名稱 | 自動 |
| TC-028 | 計畫 TC `caddy-https` | 例外 | 同上 | 搜尋會關掉憑證的寫法 | 沒有 `tls internal`、沒有 `auto_https off`（Funnel 用法靠 `http://` 位址自然不申請憑證，不需要關閉開關） | 自動 |
| TC-029 | 裁決二 8「歸屬不明就停下」 | 功能 | 同上 | 檢查模板內所有路徑前綴與其後端 | 同一個路徑前綴不會同時出現在兩個不同後端；沒有兩條規則互相蓋掉（例如較廣的萬用規則排在較窄的規則前面，把它吃掉） | 自動 |
| TC-030 | 作法 4「不加 log 檔路徑」「`header` 不是必要」 | 不在範圍 | 同上 | 在 Caddyfile 搜尋 `log` 指令 | 沒有指定 log 檔路徑的寫法（用預設，進 journald） | 自動 |
| TC-031 | 裁決 2「不拆成兩個檔」 | 不在範圍 | 同上 | 列出 `deploy/` 下名字含 `Caddyfile` 的檔 | 只有 `Caddyfile.template` 一個，沒有 VPS 版／Funnel 版各一份 | 自動 |

## User Story 3 — 備份腳本：一致性備份、只備份不可重建的檔案、缺東西時說白話（優先度 P1）

來源：計畫作法 5、TC `backup-script`／`backup-script-runs`、**裁決三 15、16**、裁決 5（備份檔名以 `docs/OPERATIONS.md` 第 4 節為準，不是 replan 原文的 `platform.sqlite3`／`_personal/`）。備份對象：`tokens.db`、`platform.db`、`web_signing.key`、`uploads/`、`records/`；**不備份** `index.db`（可重建）。

測試用的假資料夾：兩個真 SQLite 檔用 `python3` 建，其餘各放一個小檔，設 `ABF_PLATFORM_DB` 指向它，在臨時資料夾跑 `deploy/backup.sh <tmp>/out`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 計畫 TC `backup-script`；作法 5 | 功能 | 實作完成 | 對 `deploy/backup.sh` 跑 `bash -n`，並讀檔頭 | 語法檢查通過；含 `set -euo pipefail` | 自動：`tests/hosted_deploy_test.sh` |
| TC-033 | 計畫 TC `backup-script`；H-1「備份」 | 功能 | 同上 | 讀腳本內容 | 提到 `tokens.db`、`platform.db`、`web_signing.key`、`uploads`、`records`；資料庫用 `.backup`（sqlite3 指令）或 Python 的 `backup`（`Connection.backup`）複製，沒有拿裸 `cp` 複製資料庫 | 自動 |
| TC-034 | 計畫 TC `backup-script-runs` | 功能 | 臨時資料夾裡有假資料夾（五項俱全） | 跑 `deploy/backup.sh <tmp>/out` | 結束碼 0；`<tmp>/out/` 底下出現名為 `abf-backup-<UTC 時間>` 的資料夾；其中有兩個資料庫的備份、`web_signing.key`、`uploads/`、`records/` 各自的副本 | 自動 |
| TC-035 | **裁決三 16** | 例外 | 假資料夾沒有 `web_signing.key`（web 從沒啟動過），其餘俱全 | 跑備份腳本 | 結束碼 0（照樣成功）；印出一行白話，意思是「web 尚未啟動過，略過簽章金鑰」；備份資料夾裡沒有 `web_signing.key` | 自動 |
| TC-036 | 計畫 TC `backup-script-runs` | 功能 | 同 TC-034 | 用 `python3` 開備份出來的兩個資料庫，與原資料庫比對內容 | 兩個都打得開，且內容與原本相同 | 自動 |
| TC-037 | 計畫 TC `backup-script-runs`；作法 5 | 功能 | 同 TC-034，另外在假資料夾放一個 `index.db` | 跑備份腳本 | 備份資料夾裡沒有 `index.db`（它可用 `abf-platform rebuild` 重建，不備份） | 自動 |
| TC-038 | 計畫 TC `backup-script-runs`；作法 5「缺任何必備檔就非零結束並用白話說缺哪個」 | 例外 | 假資料夾缺 `tokens.db` | 跑備份腳本 | 結束碼不是 0；訊息用白話說明缺的是 `tokens.db` | 自動 |
| TC-039 | **裁決三 16**（`tokens.db`、`platform.db` 缺了仍非零） | 例外 | 假資料夾缺 `platform.db` | 跑備份腳本 | 結束碼不是 0；訊息用白話說明缺的是 `platform.db` | 自動 |
| TC-040 | 作法 5「`$1`（目的資料夾）必填」 | 例外 | 不帶任何參數 | 跑備份腳本 | 結束碼不是 0；訊息用白話說明要給目的資料夾（並說該怎麼給）；沒有備份出任何東西 | 自動 |
| TC-041 | 作法 5「資料夾位置從 `ABF_PLATFORM_DB`／`XDG_DATA_HOME` 推導，與 `store.py` 的 `default_index_path` 規則一致」 | 功能 | 沒有設 `ABF_PLATFORM_DB`，只設 `XDG_DATA_HOME` 指向臨時資料夾，其下 `abf-platform/` 放好五項 | 跑備份腳本 | 結束碼 0，備份的是 `$XDG_DATA_HOME/abf-platform/` 底下的檔案（與 `default_index_path` 規則一致） | 自動 |
| TC-042 | **裁決三 15** | 功能 | 把 `tokens.db`、`platform.db`（`ABF_PLATFORM_STATE`）、`uploads/`（`ABF_PLATFORM_UPLOADS`）分別放在 index 旁邊以外的位置，並設對應的 `ABF_PLATFORM_TOKENS`／`ABF_PLATFORM_STATE`／`ABF_PLATFORM_UPLOADS` | 跑備份腳本 | 三個覆蓋變數各自生效：備份裡是被覆蓋位置上的檔案內容，不是 index 旁邊（不存在或不同）的那份 | 自動 |

## User Story 4 — 文件：維護者照著做就能把平台架起來，兩條路都寫（優先度 P1）

來源：計畫作法 6、TC `docs-host-section`／`docs-paths-exist`、完成標準、「既有測試」一節、裁決二 10、**裁決三 14**；H-1「`docs/OPERATIONS.md` 加『託管一間實驗室』一節」、第 48 行「文件兩條路都寫；既有『公開網址』小節不能被弄壞」、第 215 行「文件寫到他照著做就能做；不替他執行」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-043 | **裁決三 14** | 功能 | 實作完成 | 讀 `docs/OPERATIONS.md` 的兩份逐步清單（VPS 與 Funnel） | 兩份清單都有「讓 Caddy 讀到 `ABF_SITE_ADDRESS`」這一步：用 `caddy run --config deploy/Caddyfile.template --envfile <env 檔>`（或系統單元的 `EnvironmentFile=`）；Funnel 用法用同一個 envfile，值為 `http://127.0.0.1:8080` | 自動：`tests/hosted_deploy_test.sh` |
| TC-044 | 計畫 TC `docs-host-section`；H-1「加『託管一間實驗室』一節」 | 功能 | 同上 | 看 `docs/OPERATIONS.md` 的標題 | 有 `### Hosting one lab`，位在第 5 節底下、與 `### Public URL`、`### Google Batch…` 並列；小節第一行用中文括號標一次「託管一間實驗室」 | 自動 |
| TC-045 | 計畫 TC `docs-host-section` | 功能 | 同上 | 在 `docs/OPERATIONS.md` 搜尋關鍵字 | 含 `deploy/systemd`、`deploy/Caddyfile.template`、`deploy/backup.sh`、`loginctl enable-linger`、`tailscale funnel`、`<your-domain>` | 自動 |
| TC-046 | 作法 6「第 2 節改寫」；維護者第 48 行 | 功能 | 同上 | 讀第 2 節 | 兩種前端（VPS 的 Caddy／桌機的 Funnel）各有一個步驟清單並指向 `deploy/Caddyfile.template`；Funnel 部分寫出指令 `tailscale funnel --bg 8080` 與只開 443／8443／10000 的埠限制；沒有維護者自己的主機名 | 自動 |
| TC-047 | 作法 6「第 3 節改寫」 | 功能 | 同上 | 讀第 3 節 | 說明單元檔在 `deploy/systemd/`；安裝步驟依序含：複製到 `~/.config/systemd/user/`、`systemctl --user daemon-reload`、`enable --now`、`loginctl enable-linger <user>` | 自動 |
| TC-048 | 作法 6「保留『權杖不進單元檔』那句」 | 功能 | 同上 | 讀第 3 節 | 原有的「權杖不進單元檔」那句仍在 | 自動 |
| TC-049 | 作法 6「第 4 節加一句」 | 功能 | 同上 | 讀第 4 節 | 有 `deploy/backup.sh` 的用法，並寫明「還原＝停三個服務、把檔案放回資料夾」 | 自動 |
| TC-050 | 計畫 TC `docs-host-section`；作法 6「第 6 節刪掉已做的兩條」 | 功能 | 同上 | 讀「Not built yet」一節 | 不再含「Service-manager unit files」那條與「Tailscale Funnel and proxy configuration」那條 | 自動 |
| TC-051 | 作法 6「`Hosting one lab` 內容」 | 功能 | 同上 | 讀 `### Hosting one lab` | 寫明：一間實驗室一台；VPS 最低需求（Linux、可開 80／443、Python 3.10+、systemd）；建立專用使用者並 `enable-linger` | 自動 |
| TC-052 | 作法 6；完成標準 | 功能 | 同上 | 讀 `### Hosting one lab` 的逐步清單 | 從零開始，最後一步是 `curl -i https://<your-domain>/user-info`，預期回 401 且回應有 `X-ABF-Platform` 標頭 | 自動 |
| TC-053 | 作法 6「備份排程範例（只寫範例文字）」 | 功能 | 同上 | 讀 `### Hosting one lab` | 有備份排程範例（cron 或 systemd timer）以**文字**呈現 | 自動 |
| TC-054 | 作法 6「升級步驟」 | 功能 | 同上 | 讀 `### Hosting one lab` | 有升級步驟 | 自動 |
| TC-055 | 裁決二 10「『一鍵』＝文件裡一段可整段複製的指令」 | 功能 | 同上 | 驗收者讀 `### Hosting one lab` | 有一段可整段複製貼上的指令區塊，照它做得到單元檔安裝與服務啟動（不要求真的執行） | 手動：驗收者讀文件 |
| TC-056 | 作法 6「範例一律只用 `<your-domain>`、`<venv>`、`<data-folder>`」 | 功能 | 同上 | 掃兩份文件的新增內容 | 範例位址／路徑只用這三個佔位符 | 自動 |
| TC-057 | 既有測試：`operations_doc_test.sh` | 功能 | 同上 | 跑 `bash tests/operations_doc_test.sh` | 原樣通過：`docs/OPERATIONS.md` 仍剛好 6 個 `##` 標題、順序與關鍵字不變（新內容只在 `###` 以下） | 自動：`tests/operations_doc_test.sh` |
| TC-058 | 維護者第 48 行「既有『公開網址』小節不能被弄壞」；既有測試 | 功能 | 同上 | 跑 `bash tests/docs_nano4_keys.sh` | 原樣通過：仍有符合「Public URL／公開網址」的 `###` 標題，且含 `Tailscale Funnel`、`user-info`、`401`、`X-ABF-Platform` | 自動：`tests/docs_nano4_keys.sh` |
| TC-059 | 作法 6「`docs/INSTALL.md` 只補兩句」 | 功能 | 同上 | 讀 `docs/INSTALL.md` 的 diff | 只有第 1 節「What you need」與第 3 節 Claude Desktop 的「需要公開 https 位址」那段各補一句，指向 OPERATIONS 的託管小節；沒有新增 `##` 標題；補的句子裡反引號詞沒有 snake_case | 自動 |
| TC-060 | 既有測試：`install_doc_test.sh`、`harness_kits_test.sh` | 功能 | 同上 | 跑這兩個測試 | 原樣通過（`INSTALL.md` 仍剛好 6 個 `##`、無 `abf_pat_`＋8 碼以上英數字、套件與文件一致） | 自動：`tests/install_doc_test.sh`、`tests/harness_kits_test.sh` |
| TC-061 | 既有測試：`platform/tests/test_gcb_launch.py` 第 1163 行 | 功能 | 同上 | 跑該文件斷言 | 原樣通過：`INSTALL.md`＋`OPERATIONS.md` 合起來仍含 `Java 17`、`Nextflow`、`gcloud`，且沒有非 `lab-project-1` 的 `…@….iam.gserviceaccount.com`；既有「Google Batch on the platform host」小節整段保留 | 自動：`platform/tests/test_gcb_launch.py` |
| TC-062 | 計畫 TC `docs-paths-exist`；`operations_doc_test.sh` 的路徑規則 | 功能 | 同上 | 取出兩份文件中反引號包住的 `deploy/…` 路徑，以及引用的 `tests/hosted_deploy_test.sh` | 每一個都真的存在 | 自動 |
| TC-063 | 既有測試規則：文件裡每個 `abf-platform <word>` 必須是 `cli.py` 的真子命令 | 功能 | 同上 | 掃兩份文件新增內容 | 沒有不存在的子命令（例如沒有 `abf-platform backup`；備份寫 `deploy/backup.sh`） | 自動：`tests/operations_doc_test.sh` |
| TC-064 | 完成標準「手動（維護者）」六步；維護者第 215 行 | 功能 | 同上 | 驗收者讀 `docs/TESTING.md` | 有 hosted-deploy 小節，逐項寫出六步：①WSL 複製單元檔、填 env、啟動三服務並 `status` 皆 active ②本機起 Caddy（`http://127.0.0.1:8080`）＋`tailscale funnel --bg 8080`，手機開登入頁、`curl -i …/user-info` 回 401＋`X-ABF-Platform` ③Claude Desktop 連接器指到 `…/mcp` 走完 OAuth 登入與同意頁 ④殺掉一個服務程序，5 秒內被拉起 ⑤跑 `deploy/backup.sh ~/backups`，還原到空資料夾後 `abf-platform pat list` 能列出權杖 ⑥VPS 同一組檔案、改 `ABF_SITE_ADDRESS=<your-domain>`，Caddy 自動取得憑證；每步具體到維護者能照做 | 手動：`docs/TESTING.md` |
| TC-065 | 作法 6「全用英文，與現有文件一致」 | 功能 | 同上 | 驗收者讀 `docs/OPERATIONS.md` 新增內容 | 文件新增內容為英文（唯一的中文是 `Hosting one lab` 小節第一行的「託管一間實驗室」標記） | 手動：驗收者讀文件 |

## User Story 5 — 這次不做的事，確實沒做（優先度 P1）

來源：計畫「不做」「範圍」「不准動」、裁決 1、2、9、10、**裁決 13 的「程式不改」**（維護者原話第 52 行：託管＝一間實驗室一台，程式不改，不做跨實驗室隔離）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-066 | 計畫 TC `no-code-touched`；「不改 `platform/…`」；維護者第 52 行「程式不改」 | 不在範圍 | 有 git 與 base（`origin/v3`）；沒有就略過並印 skip | `git diff --name-only origin/v3...HEAD` | 不含 `platform/abf_platform/`、`platform/abf_station/`、`platform/abf_launch/`、`platform/pyproject.toml`、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`、`spec.md`、`.specify/memory/constitution.md`；`specs/hosted-deploy/test-case*.md` 在實作期間沒被改 | 自動 |
| TC-067 | 完成標準「驗收者看 `git diff --name-only origin/v3...HEAD`：只出現範圍列出的檔案」 | 不在範圍 | 同上 | 驗收者列出 diff 的檔名 | 只出現：`deploy/` 下六個檔、`tests/hosted_deploy_test.sh`、`specs/hosted-deploy/ledger.md`、`docs/OPERATIONS.md`、`docs/INSTALL.md`、`docs/TESTING.md`（`specs/hosted-deploy/` 下的 plan／合約檔是流程檔，不算越界） | 手動：驗收者看 `git diff` |
| TC-068 | 計畫「既有的 `tests/*.sh`、`platform/tests/*.py`：不改」 | 不在範圍 | 同上 | 驗收者逐一比對 diff 中既有測試檔與 base | 既有測試檔一個字都沒改（唯一的新測試檔是 `tests/hosted_deploy_test.sh`）；沒有放鬆斷言、跳過案例 | 手動：驗收者看 `git diff` |
| TC-069 | 「不做」：不寫 Docker Compose／Dockerfile、不出貨 `install.sh`、不出貨備份排程單元；裁決 1、10 | 不在範圍 | 實作完成 | 列出 `deploy/` 下所有檔案 | 恰好是計畫列的六個檔（`systemd/` 下恰好三個 `.service`）；沒有 `Dockerfile`、`docker-compose*`、`install.sh`、`.timer`、cron 檔 | 自動 |
| TC-070 | 「不做」：不做多租戶（ADR 0005 不動）、不處理 `abf-station` 單元；裁決 13 | 不在範圍 | 同上 | 驗收者讀 `deploy/` 與 `### Hosting one lab` | 沒有 `abf-station` 單元、沒有多實驗室／跨實驗室隔離的設定或說法；文件只說「一間實驗室一台主機」 | 手動：驗收者讀檔案 |
| TC-071 | 作法 5「不連網、不上傳、不刪舊備份」；「不做自動備份上傳／輪替」 | 不在範圍 | 同上 | 在 `deploy/backup.sh` 搜尋 | 不含 `curl`、`wget`、`scp`、`rsync`、`ssh`、`rm `；沒有上傳或輪替（保留與搬出主機是文件裡寫的人工步驟） | 自動 |
| TC-072 | 「不做」：不真的部署、不裝 Caddy、不開 Funnel、不呼叫網路；計畫作法 7「不啟動任何服務」 | 不在範圍 | 同上 | 掃 `tests/hosted_deploy_test.sh` 本身 | 測試檔不呼叫 `docker`、`caddy`、`systemctl`、`tailscale`、`curl`、`wget`，不啟動任何服務；只用 grep／sed／awk／bash 內建與 `python3` | 自動 |
| TC-073 | 作法 7「`systemd-analyze` 不得依賴」 | 例外 | 機器上沒有 `systemd-analyze` | 跑 `bash tests/hosted_deploy_test.sh` | 該項印出 skip，不算失敗，整支測試仍可全綠；有的話可額外跑 `verify` 當加分 | 自動 |
| TC-074 | 作法 7；完成標準 | 功能 | 實作完成 | 讀 `tests/hosted_deploy_test.sh` 檔首，並跑 `bash tests/run_all_count_test.sh` | 檔首寫明目的與 TC 對應；`bash tests/hosted_deploy_test.sh` 全綠；`run_all_count_test.sh` 仍通過（新檔被 `tests/run_all.sh` 自動掃到，不必登記） | 自動：`tests/hosted_deploy_test.sh`、`tests/run_all_count_test.sh` |

## 憲法與安全網

本任務碰到的條目：Safety Net「Credentials … never in git」（`tests/credentials_stay_in_settings_test.sh`）、「平台不存放進來的憑證」、不變條款 3「Anyone, Anywhere」（`tests/no_hardcoded_paths.sh`，個人路徑不寫死）；專長守則 backend 中適用於本任務的：密鑰不得出現在日誌或回應、錯誤訊息要說明原因與處理方式、資料結構變動需 migration 或寫明不需要。專長守則的其餘項（動作層對等性、跨使用者讀寫、寫入動作的人工確認）**不適用**：本任務沒有新增任何網頁／API／聊天動作，不碰 `platform/abf_platform/`（TC-066 守住這點）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-075 | Safety Net 憑證規則；計畫 TC `no-secrets`；專長守則（密鑰不得出現在任何檔案） | 例外 | 實作完成 | 掃 `deploy/` 全部檔案與兩份文件的新增內容 | 沒有 `abf_pat_` 後接 8 個以上英數字；沒有 `Bearer ` 後接實際值（`<PAT>` 佔位符可）；沒有 `password=`、`ABF_PAT=` 後接非 `<…>` 的值；沒有私密金鑰標頭字串。單元檔裡也沒有 token、密碼、金鑰、主機名稱 | 自動 |
| TC-076 | 計畫 TC `no-real-host` | 例外 | 同上 | 掃 `deploy/` 與兩份文件的新增內容 | 不含 `DESKTOP-7J5L5BJ`、不含 `.ts.net`、不含 `u9613010`；網域一律是 `<your-domain>` 形式 | 自動 |
| TC-077 | 不變條款 3（個人路徑不寫死）；作法 2 的 `<venv>`、`%h` | 例外 | 同上 | 掃 `deploy/` 與兩份文件的新增內容，找 `/home/<名字>/`、`/Users/<名字>/`、`C:\Users\…` 這類個人絕對路徑 | 一個都沒有；位置一律由 `%h`、`$HOME`、環境變數或 `<venv>`／`<data-folder>` 佔位符表示 | 自動 |
| TC-078 | 專長守則：密鑰不得出現在日誌或任何回應；Safety Net「never printed」 | 例外 | 假資料夾裡的 `web_signing.key` 與資料庫內放一段獨特的測試字串 | 跑備份腳本（成功與失敗兩種情形） | 腳本的標準輸出與錯誤輸出都不含那段測試字串（腳本不印檔案內容） | 自動 |
| TC-079 | Safety Net 憑證規則「owner only」；作法 5「目錄 700、檔案 600」 | 功能 | 在有 POSIX 權限語意的環境（WSL／Linux）跑 TC-034 的備份 | 用 `stat` 看備份資料夾與裡面的檔案 | 目錄權限 700、檔案權限 600；在 Git Bash 這種沒有 POSIX 權限語意的環境略過這一條並印 skip | 自動 |
| TC-080 | 專長守則：資料結構變動需 migration 或寫明不需要 | 不在範圍 | 同上 | 檢查 diff：沒有 `store.py`、資料表定義或 schema 相關檔案被改（同 TC-066） | 沒有資料結構變動，所以不需要 migration（計畫「環境事實」「不改程式」即其理由） | 自動：同 TC-066 |
| TC-081 | Safety Net 憑證規則；計畫 TC `no-secrets` 的拼接要求；既有測試 | 例外 | 同上 | 跑 `bash tests/credentials_stay_in_settings_test.sh`，並在 `tests/hosted_deploy_test.sh` 與所有新檔搜尋私密金鑰標頭的字面 | 該既有測試原樣通過；新測試與新檔裡沒有金鑰標頭字面（測試內用字串拼接組出要找的樣式） | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-082 | 完成標準「完整套件在 WSL／Linux 綠」；`tests/run_all.sh` | 功能 | 在 WSL／Linux | 跑 `tests/run_all.sh` | 全綠（含新測試與所有既有測試） | 自動：`tests/run_all.sh` |
