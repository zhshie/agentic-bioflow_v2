# 測試案例：桌機（WSL）用 systemd 開機自動啟動、當掉自動重啟

<!--
Written by the verifier (CONTRACT mode). Reader: the maintainer, who is not an engineer.
手動 cases are steps in docs/TESTING.md run on the maintainer's desktop; 自動 cases are in tests/desktop_systemd_test.sh
(shape only: file contents, no secret, docs complete) unless another file is named.
-->

**規格**：`specs/desktop-systemd/plan.md`（本功能沒有 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：unit ＝ systemd 的「服務說明檔」，告訴系統這個程式怎麼啟動、當掉後怎麼辦。WSL ＝ Windows 裡跑 Linux 的功能。linger ＝ 讓使用者的服務在沒有人開終端機時也能跑的開關。

本功能「平台真的有沒有在你的桌機上自動起來」只有你的桌機看得到，所以標「手動」的是真正的驗收；標「自動」的只保證檔案的形狀與文件齊全。

## User Story 1 — 登入後什麼都不做，平台自己起來（優先度 P1）

你的話：「我把電腦重開機、登入，什麼都不做，過一兩分鐘打開網站，平台是好的。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「做什麼」1；例 1 | 功能 | repo 內有 `deploy/systemd/abf-station@.service.in` | 讀這個檔 | 有 `[Install]` 且 `WantedBy=default.target`；有 `After=abf-serve.service` 與 `Wants=abf-serve.service`；檔名含 `@`（範本，每個 agent 一份） | 自動：`tests/desktop_systemd_test.sh` |
| TC-002 | 計畫「做什麼」1 | 功能 | 同上 | 讀 `ExecStart` | 以 `%h/<venv>/bin/abf-station run` 開頭；參數恰為 `--platform http://127.0.0.1:8787`、`--token-file ${ABF_STATION_TOKEN_FILE}`、`--deployment ${ABF_STATION_DEPLOYMENT}`、`--plugin-root ${ABF_STATION_PLUGIN_ROOT}`；這些旗標每一個都是 `platform/abf_station/cli.py` 的 `run` 子命令真的有的（對照 cli.py，不是只對照計畫） | 自動 |
| TC-003 | 計畫「做什麼」1 | 功能 | 同上 | 讀 `EnvironmentFile` 行 | 恰兩行：`%h/.config/abf-platform/env` 在前，`%h/.config/abf-platform/station-%i.env` 在後；後者前面沒有 `-`（缺檔要明確失敗，不要靜默啟動）；檔名用 `%i`，不是 `%I` | 自動 |
| TC-004 | 計畫「做什麼」3；例 1 | 功能 | repo 內有 `deploy/wsl/keep-wsl-running.ps1` | 讀腳本 | 註冊的工作名稱是 `abf-wsl-keepalive`；觸發是「使用者登入時」；動作是 `wsl.exe` 加 `--exec`、`/bin/sleep`、`infinity`；沒有其他動作（不啟動、不重啟平台） | 自動 |
| TC-005 | 計畫「做什麼」3（審查 P5） | 功能 | 同上 | 讀工作的設定 | 執行時間上限設為無限（不是預設的 72 小時）；用電池時也啟動、換電池不停止；`-Hidden`；同時只留一個實例；觸發器指定目前使用者；權限等級是一般（Limited） | 自動 |
| TC-006 | 計畫「做什麼」4.2 | 功能 | `docs/OPERATIONS.md` 有 `###` 小節標題含 `WSL` | 讀該小節 | 寫出：在 `/etc/wsl.conf` 加 `[boot]` 與 `systemd=true`；這步要 sudo、由本人做；之後 `wsl --shutdown` 再重開 | 自動 |
| TC-007 | 計畫「做什麼」4.2 | 例外 | 同上 | 讀 `wsl --shutdown` 附近的文字 | 明寫後果：WSL 裡所有東西都會停；國網的共用 SSH 連線會斷；重開後要本人重新連線並輸入 OTP | 自動 |
| TC-008 | 計畫「做什麼」4.3 | 功能 | 同上 | 讀 env 檔那一步 | 明寫 systemd 不讀 `~/.bashrc`；平台行程需要的環境變數（例如部署的設定檔位置）必須寫進 `~/.config/abf-platform/env`；並提到 `ABF_PUBLIC_URL` | 自動 |
| TC-009 | 計畫「做什麼」4.5（審查 P7） | 功能 | 同上 | 讀 linger 那一步 | 有 `loginctl enable-linger`；照實說要不要 sudo（被要求密碼時用 `sudo loginctl enable-linger`）；說明作用是不依賴有人開著終端機；並說明保活工作與 linger 各管一件事 | 自動 |
| TC-010 | 計畫「做什麼」4 的順序 | 功能 | 同上 | 依文字順序讀步驟 | 順序是：前提 → 開 systemd → 寫 env → 裝 unit 與每個 agent 的 `station-<名字>.env` → `daemon-reload` → `enable --now abf-serve abf-web abf-mcp abf-station@<名字>` → linger → Windows 端註冊 `abf-wsl-keepalive` → 看狀態／記錄／停／重啟／移除 → 從手動換過來 → 做不到的事；另寫明「沒有人登入 Windows 時不會啟動」 | 自動 |
| TC-011 | 例 1 | 功能 | 桌機已照文件裝好並重開機一次 | 重開機、登入 Windows，什麼都不做，等一兩分鐘，打開平台網站 | 網站正常，能登入、看到內容 | 手動：`docs/TESTING.md` |
| TC-012 | 例 1（審查 P7） | 功能 | 同上，登入後不開任何終端機 | 十分鐘後再打開網站，再用 `wsl -l -v` 看 | 網站仍正常；WSL 狀態是 Running（保活工作真的讓 WSL 沒被關掉） | 手動 |
| TC-013 | 審查 P7 | 功能 | 桌機 | 在 WSL 內跑 `wsl --version`（Windows 端）與 `systemctl --user status`；照文件做 linger | 能看出 WSL 版本夠新、`systemd` 已開、`systemctl --user` 可用；若 linger 要密碼，文件的說法與實際一致（維護者回報） | 手動 |

## User Story 2 — 當掉幾秒後自己回來，其他不受影響（優先度 P1）

你的話：「平台當掉（我把其中一個行程砍掉），幾秒後它自己回來，其他的沒受影響。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 計畫「做什麼」1；例 2 | 功能 | 站台範本 | 讀 `[Service]` | `Restart=on-failure`、`RestartSec=5`，與既有三個 unit 一致 | 自動 |
| TC-015 | 審查 P3 | 例外 | 站台範本 | 讀 `[Service]` | 有 `RestartPreventExitStatus=2 3`（設定有錯或權杖被拒就停下，不每 5 秒無止境重試） | 自動 |
| TC-016 | 計畫「做什麼」1 的加固條款（審查 P2） | 例外 | 站台範本 | 讀所有加固類選項 | 不出現 `PrivateTmp`、`ProtectHome`、`ProtectSystem`、`PrivateNetwork`、`RestrictAddressFamilies`、`ReadOnlyPaths`、`ReadWritePaths`；若出現 `NoNewPrivileges` 等其他加固選項，它前一行是註解，說明為何不影響「用 `~/.ssh/` 下的共用連線 socket 執行 `ssh`」與「寫部署資料夾和 /tmp」 | 自動 |
| TC-017 | 計畫「測試怎麼做」 | 功能 | 環境有 `systemd-analyze`（沒有就略過並說明） | 把 `<venv>` 換成暫存路徑、複製站台範本到暫存資料夾，跑 `systemd-analyze verify --user` | 不報告站台 unit 的錯誤（沒裝時顯示「略過」，不算失敗） | 自動 |
| TC-018 | 例 2 | 功能 | 平台已在桌機上跑起來 | 找到其中一個行程（例如 `systemctl --user show -p MainPID abf-web`）並砍掉 | 幾秒內它回來，行程編號不同；另外兩個服務與站台 agent 的行程編號沒變 | 手動 |
| TC-019 | 審查 P3 | 例外 | 把某個站台 agent 的權杖檔權限改成別人可讀（或指到不存在的檔） | 啟動該 agent 的 unit | 狀態停在 failed，不會每幾秒重跑；`journalctl --user -u 'abf-station@<名字>'` 看得到一行 `abf-station will not start: …` 說明原因 | 手動 |
| TC-020 | 計畫「做什麼」1 的加固條款（審查 P2） | 功能 | 國網共用連線已由本人連上（輸入過 OTP）；agent 由 systemd 啟動 | 在網站上做一件需要 agent 讀國網的唯讀工作 | 工作成功；證明 systemd 啟動的 agent 能用 `~/.ssh/` 下的共用連線 socket 執行 `ssh`，也能寫部署資料夾與 /tmp | 手動 |
| TC-021 | 計畫「不做」第 2 條 | 功能 | 本分支 | 以 `git diff origin/v3 -- deploy/systemd/abf-serve.service.in deploy/systemd/abf-web.service.in deploy/systemd/abf-mcp.service.in` 比較 | 三個既有 unit 一個字都沒改 | 自動 |

## User Story 3 — 現在哪些在跑，下一個指令就看得到（優先度 P1）

你的話：「我想知道現在哪些在跑，下一個指令就看得到。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 計畫「做什麼」4.7；例 3 | 功能 | 文件小節 | 讀「怎麼看」 | 有 `systemctl --user status 'abf-*'` 與 `journalctl --user -u abf-web -n 50` 兩個指令，各說明看到什麼 | 自動 |
| TC-023 | 計畫「做什麼」4.7 | 功能 | 文件小節 | 讀「停、重啟、移除」 | 每一項有一個可複製的指令（`systemctl --user stop`／`restart`／`disable --now`，並說移除 unit 檔後 `daemon-reload`），且指令涵蓋四個 unit，含 `abf-station@<名字>` | 自動 |
| TC-024 | 計畫「合併前驗得到的」 | 功能 | 文件小節 | 取出小節中每個 `abf-platform <子命令>`、`abf-station <子命令>`、反引號裡的 repo 檔案路徑 | 子命令都真的存在於 `platform/abf_platform/cli.py` 與 `platform/abf_station/cli.py`；每個路徑都真的存在於 repo；`tests/operations_doc_test.sh`（六個 `##` 標題）與 `tests/hosted_deploy_test.sh` 的文件路徑檢查仍通過 | 自動 |
| TC-025 | 審查 P4 | 功能 | 文件小節 | 讀「怎麼看記錄」 | 明寫 agent 拒絕啟動的原因看 `journalctl --user -u 'abf-station@<名字>'`（因為 systemd 下沒有終端機可看到那行訊息） | 自動 |
| TC-026 | 例 3 | 功能 | 桌機，四個服務都已啟用 | 打 `systemctl --user status 'abf-*'` | 一個指令就列出四個服務（serve、web、mcp、station），每個都標 `active (running)`；你不用查文件就看得懂哪個在跑 | 手動 |

## User Story 4 — 不會同時跑兩份（優先度 P1）

你的話：「它不會同時跑兩份。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 計畫「做什麼」4.8；例 4 | 功能 | 文件小節 | 讀「從手動啟動換過來」 | 明寫：先停掉手動起的行程（否則搶連接埠、會有兩份）；平台中斷約一分鐘；並在步驟 4（`enable --now`）之前 | 自動 |
| TC-028 | 審查 P6 | 功能 | 文件與範例 | 讀實例名規則 | 文件寫明 agent 名字只用英數、底線、點；範例檔名 `station-<名字>.env` 的名字與 unit 實例名 `abf-station@<名字>` 一致 | 自動 |
| TC-029 | 例 4 | 功能 | 平台已由 systemd 跑著 | 連打兩次 `systemctl --user start abf-web`，再用 `systemctl --user status 'abf-*'` 與 `ps` 看 | 每個服務只有一個行程；第二次 start 沒有多出一份 | 手動 |
| TC-030 | 例 4 | 例外 | 平台已由 systemd 跑著 | 在終端機手動再啟動一份平台（舊的做法） | 手動那份起不來（連接埠被占用）並顯示錯誤，原本那份不受影響 | 手動 |

## User Story 5 — 裡面沒有我的權杖（優先度 P1）

你的話：「裡面沒有我的權杖。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 計畫「做什麼」2 | 功能 | repo 內有 `deploy/station.env.example`（放在 `deploy/` 下、不放 `deploy/systemd/` 底下，審查 P1） | 讀這個檔 | 恰好有 `ABF_STATION_TOKEN_FILE`、`ABF_STATION_DEPLOYMENT`、`ABF_STATION_PLUGIN_ROOT` 三個變數（`PATH` 只出現在註解裡）；值全是 `<...>` 佔位字；`TOKEN_FILE` 的值是路徑，不是權杖本身 | 自動 |
| TC-032 | 例 5；計畫「合併前驗得到的」 | 功能 | 新增的所有檔：站台範本、`station.env.example`、`keep-wsl-running.ps1`、新文件小節 | 掃描 | 沒有權杖形狀（`abf_pat_…`、`Bearer <字>`、`password=值`）、沒有私鑰標頭、沒有真實主機名／帳號、沒有 `/home/<名字>/`、`/Users/<名字>/`、`C:\Users` 這類個人路徑（含 `.ps1`，既有 TC-075–077 只掃 `deploy/` 與兩份文件，新腳本在 `deploy/` 下所以也在內；新測試另外單獨掃新文件小節與 `.ps1`）；`tests/hosted_deploy_test.sh` 的 TC-075–077 仍通過 | 自動 |
| TC-033 | 例 5 | 功能 | 站台範本 | 找「token」出現的行 | 權杖只以「檔案路徑」變數出現（`ABF_STATION_TOKEN_FILE`），沒有任何一行讓權杖內容直接寫進 unit 或 `Environment=` | 自動 |
| TC-034 | 計畫「做什麼」2；例 5 | 例外 | 文件小節 | 讀權杖檔那一步 | 說明權杖檔權限 600、放在 WSL 自己的家目錄（不是 Windows 磁碟）、權杖用 `abf-platform` 的指令產生並只顯示一次，不寫進 unit 或 env 範例（與 `cli.py` 對權杖檔的檢查一致） | 自動 |
| TC-035 | 例 5 | 功能 | 桌機已照文件裝好 | 在桌機的 `~/.config/systemd/user/` 與 `~/.config/abf-platform/` 底下搜尋你的權杖文字 | 完全找不到（只會找到權杖檔的「路徑」） | 手動 |

## User Story 6 — Windows 端腳本：預設只印、不提權、可移除（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | 計畫「做什麼」3 | 功能 | `keep-wsl-running.ps1` | 讀腳本 | 不加 `-Apply` 時只印出「將要做什麼」；註冊工作的呼叫只出現在 `-Apply` 才進入的分支 | 自動 |
| TC-037 | 計畫「合併前驗得到的」 | 功能 | 環境有 `powershell.exe`（沒有則略過並說明） | 不加參數執行腳本，再列出工作 | 印出計畫；不存在 `abf-wsl-keepalive` 工作 | 自動 |
| TC-038 | 計畫「做什麼」3 | 功能 | `keep-wsl-running.ps1` | 讀腳本 | `-Apply` 重複執行結果相同（先檢查或先取代，不會產生兩個工作）；有 `-Remove` 分支；`-Remove` 對不存在的工作不報錯 | 自動 |
| TC-039 | 計畫「做什麼」3 | 功能 | 桌機 | 先 `-Apply` 兩次，查工作清單；再 `-Remove`，再查 | 兩次後只有一個 `abf-wsl-keepalive`；移除後沒有 | 手動 |
| TC-040 | 計畫「做什麼」3「不提權」 | 例外 | `keep-wsl-running.ps1` | 讀腳本 | 沒有 `-Verb RunAs`、沒有 `#Requires -RunAsAdministrator`、沒有自己提權的程式；權限等級是 Limited；遇到權限不足時印出說明並停手 | 自動 |
| TC-041 | 計畫「做什麼」3 | 例外 | `keep-wsl-running.ps1` | 檢查檔案位元組 | 純 ASCII，或以 UTF-8 BOM 開頭（Windows PowerShell 5 才不會把非 ASCII 讀壞） | 自動 |
| TC-042 | 計畫「做什麼」3 | 功能 | `keep-wsl-running.ps1` | 讀腳本 | 有 `-Distro` 參數；沒給時動作裡不帶 `-d`（用預設 distro）；給了才帶，且含空白的名字有加引號 | 自動 |
| TC-043 | 憲法 I.1（見憲法段） | 功能 | `keep-wsl-running.ps1` 與站台範本 | 看前 40 行 | 每個檔有一行 `# Not <既有工具>: <至少 15 字的理由>`（腳本例如「不是自寫的看守腳本」須指向 systemd／工作排程器這類 repo 外的工具）；該工具名不是 repo 內檔案 | 自動 |

## User Story 7 — 檔案與文件就位（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 計畫「做什麼」6（審查 P1） | 功能 | 本分支 | 跑 `bash tests/hosted_deploy_test.sh` | 全部通過；TC-069 的檔案清單恰為舊的六個加上 `deploy/systemd/abf-station@.service.in`、`deploy/station.env.example`、`deploy/wsl/keep-wsl-running.ps1`；TC-083 改為四個 `.service.in`；兩處以外的斷言與 `origin/v3` 相同（逐行比較，沒有放寬） | 自動 |
| TC-045 | 計畫「做什麼」4 | 功能 | 本分支 | 跑 `bash tests/operations_doc_test.sh` | 通過；`docs/OPERATIONS.md` 仍恰好六個 `##` 標題；新小節是 `###`，位於第 3 節（Keeping them running）之內或之後、第 4 節之前 | 自動 |
| TC-046 | 計畫「做什麼」5 | 功能 | `docs/TESTING.md` | 讀新的桌機小節 | 有四個步驟對應：重開機後網站好的（TC-011）、砍行程幾秒後回來（TC-018）、一個指令看得到哪些在跑（TC-026）、權杖不在任何 unit 或 env 檔（TC-035）；另有「連打兩次 start 不會兩份」（TC-029）；每步寫明要看到什麼 | 自動 |
| TC-047 | 計畫「做什麼」6 | 功能 | `CHANGELOG.md` | 讀最上面一節 | 新增一行提到桌機（WSL）用 systemd 自動啟動；不改其他行 | 自動 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-048 | 計畫「不做」：受保護路徑與憲法 | 不在範圍 | 本分支 | `git diff --name-only origin/v3...HEAD` | 沒有任何檔在 `platform/`、`hooks/`、`.github/`、`.specify/memory/constitution.md`、`plugin.json` 之下；`platform/pyproject.toml` 沒變 | 自動 |
| TC-049 | 計畫「不做」：國網連線自動恢復 | 不在範圍 | 文件小節與新檔 | 讀文件；找新檔中呼叫 `ssh`／輸入 OTP 的地方 | 文件明寫「國網連線不會自動恢復，要本人重新連線並輸入 OTP」；新 unit、腳本都沒有重連或輸入 OTP 的動作 | 自動 |
| TC-050 | 計畫「不做」：Funnel | 不在範圍 | 文件小節與 `deploy/` | 讀文件；找 `tailscale`、`caddy` 的 unit | 文件明寫 Tailscale Funnel 不歸這套管；沒有新增 tailscale 或 caddy 的 unit | 自動 |
| TC-051 | 計畫「不做」：不動維護者的桌機 | 不在範圍 | 本分支的新檔與測試 | 找會寫 `/etc/wsl.conf`、註冊排程、停行程、寫使用者 env 檔的可執行程式 | `.ps1` 只有在 `-Apply` 才註冊，且 `/etc/wsl.conf` 只出現在文件裡，沒有任何腳本或測試去寫它；`tests/desktop_systemd_test.sh` 不呼叫 `systemctl`、`wsl`、`schtasks`、`Register-ScheduledTask`（比照 TC-072 的寫法） | 自動 |
| TC-052 | 計畫「不做」：自寫看守腳本不合併 | 不在範圍 | 本分支 | 找 repo 新增的檔名或內容含 supervisor／autostart／watchdog 的腳本 | 沒有；文件沒有教人使用自寫看守腳本 | 自動 |
| TC-053 | 計畫「不做」：不新增相依 | 不在範圍 | 本分支 | 看 `platform/pyproject.toml`、任何 requirements 檔 | 沒有新增（含在 TC-048；此處單獨列出一行結果） | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | I.1（建造前先說它不是哪個既有工具） | 功能 | 本分支 | 跑 `bash tests/scripts_name_their_alternative.sh` | 通過（本功能不在 `scripts/` 或 `hooks/` 下新增檔；若新增就必須有 `# Not …` 行）；並且 TC-043 的兩個新檔各有此行 | 自動 |
| TC-055 | 安全網：憑證只放設定區 | 功能 | 本分支 | 跑 `bash tests/credentials_stay_in_settings_test.sh` | 通過；沒有新增的被追蹤檔含權杖形狀的值 | 自動 |
| TC-056 | 安全網：啟動執行要經過本人確認 | 功能 | 站台範本與三個既有 unit | 讀所有 `ExecStart` | 只啟動 `abf-platform serve/web/mcp` 與 `abf-station run`（唯讀工作）；沒有 unit 或腳本呼叫 `launch`、`tw`、`nextflow`；本功能沒有改任何 hook | 自動 |
