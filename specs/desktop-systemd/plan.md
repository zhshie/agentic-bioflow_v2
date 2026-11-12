# desktop-systemd：桌機（WSL）上用 systemd 讓平台開機自動啟動、當掉自動重啟

狀態：計畫（lead，2026-11-13）。風險 M（`deploy/` 下新增檔、文件、測試；不動 `platform/`、`hooks/`、`.github/`、憲法、`plugin.json`；既有三個 unit 不改）。

## 為什麼換作法

維護者的話（BRIEF，產品底線）：「平台自動啟動／重啟」。他在 2026-11-12 已同意：改 WSL 系統設定、重啟 WSL 一次、平台停約一分鐘、他重輸 OTP。

先前的 `platform-autostart`（自寫的 bash 看守腳本，PR #391）為了避開 sudo 與重啟 WSL 而做，兩輪對抗審各找到一批會在無人看管時出事的洞（硬殺後留下第二組平台、鎖卡住、排程工作不會因非零結束碼重試、記錄上限擋不住等）。這些正是 systemd 已經解決的事。憲法原則 I.1 要求每支腳本寫明「它不是哪個既有工具」；那支腳本寫的是「不是 systemd」，而 repo 本來就有 `deploy/systemd/` 的三個 unit 與安裝說明。結論：桌機也用 systemd，自寫的看守腳本不合併（PR #391 保留為草稿，待維護者決定是否關閉）。

## 做什麼

1. `deploy/systemd/abf-station@.service.in`：站台 agent 的範本 unit（`%i` 是這個 agent 的名字）。
   - `EnvironmentFile=%h/.config/abf-platform/env`（共用）與 `EnvironmentFile=%h/.config/abf-platform/station-%i.env`（每個 agent 自己的：`ABF_STATION_TOKEN_FILE`、`ABF_STATION_DEPLOYMENT`、`ABF_STATION_PLUGIN_ROOT`，可選 `PATH`）。
   - `ExecStart=%h/<venv>/bin/abf-station run --platform http://127.0.0.1:8787 --token-file ${ABF_STATION_TOKEN_FILE} --deployment ${ABF_STATION_DEPLOYMENT} --plugin-root ${ABF_STATION_PLUGIN_ROOT}`。
   - `After=abf-serve.service`、`Wants=abf-serve.service`、`Restart=on-failure`、`RestartSec=5`，其餘欄位比照既有三個 unit。權杖只以檔案路徑出現。
   - 不可用 `PrivateTmp`／`NoNewPrivileges` 擋到 agent 需要的東西（它要用使用者的 SSH 共用連線 socket，在 `~/.ssh/` 下；要能執行 `ssh`）：範本裡每個加固選項都要有一句註解說明為何不影響這兩件事，沒把握的就不加。
2. `deploy/systemd/station.env.example`：上面三個變數的範例，全是佔位字。
3. `deploy/wsl/keep-wsl-running.ps1`（Windows 端）：註冊一個「使用者登入時」執行的排程工作（名稱 `abf-wsl-keepalive`），動作是 `wsl.exe -d <distro> --exec /bin/sleep infinity`，隱藏視窗，一般權限。它只做一件事：讓 WSL 在登入後啟動並保持開著；啟動與重啟平台是 systemd 的事。
   - 預設只印出將要做什麼，加 `-Apply` 才註冊；`-Remove` 移除；重複 `-Apply` 結果相同；不提權，需要權限時說明並停手；UTF-8 BOM 或純 ASCII；`-Distro` 沒給用預設 distro。
4. `docs/OPERATIONS.md` 新增一小節「桌機（WSL）」，放在既有 systemd 安裝說明之內或之後（`tests/operations_doc_test.sh` 釘住 `##` 標題數，所以用 `###`），依序寫：
   1. 前提（WSL 2、Ubuntu 22.04 以上）。
   2. 開 systemd：`/etc/wsl.conf` 加 `[boot]` `systemd=true`（要 sudo，由本人做）；`wsl --shutdown` 後重開。明寫後果：WSL 裡所有東西都會停，國網的共用 SSH 連線會斷，重開後要本人重新連線並輸入 OTP。
   3. 寫 `~/.config/abf-platform/env`（含 `ABF_PUBLIC_URL`；以及平台行程需要的其他環境變數，例如部署的設定檔位置——手動啟動時這類變數來自 `~/.bashrc`，systemd 不讀它，必須寫進 env 檔）。
   4. 裝四個 unit、每個 agent 一份 `station-<名字>.env`、`systemctl --user daemon-reload`、`systemctl --user enable --now abf-serve abf-web abf-mcp abf-station@<名字>`。
   5. `loginctl enable-linger <使用者>`（要 sudo 與否照實寫；讓服務不依賴有人開著終端機）。
   6. Windows 端註冊 `abf-wsl-keepalive`。
   7. 怎麼看狀態（`systemctl --user status 'abf-*'`）、看記錄（`journalctl --user -u abf-web -n 50`）、停、重啟、移除。
   8. 從手動啟動換過來：先停掉手動起的行程（否則搶連接埠），平台中斷約一分鐘。
   9. 做不到的事：國網連線不會自動恢復（要 OTP）；Tailscale Funnel 不歸它管。
5. `docs/TESTING.md`：維護者在桌機上要做的手動步驟（重開機後網站是好的；砍掉一個行程幾秒後回來、其他不受影響；一個指令看得到哪些在跑；權杖不在任何 unit 或 env 範例裡）。
6. `CHANGELOG.md` 一行。`tests/hosted_deploy_test.sh` 的 TC-069（`deploy/` 的檔案清單）加入新檔，其餘斷言不動。

## 不做

- 不在這個 PR 對維護者的桌機做任何更動（不寫 `/etc/wsl.conf`、不註冊排程工作、不停行程、不寫他的 env 檔）。
- 不改既有三個 unit 的內容。
- 不合併、不刪除 `platform-autostart` 的看守腳本分支。
- 不處理國網連線自動恢復、不處理 Funnel。
- 不新增相依。

## 維護者的例子（驗收以此為準）

1. 「我把電腦重開機、登入，什麼都不做，過一兩分鐘打開網站，平台是好的。」
2. 「平台當掉（我把其中一個行程砍掉），幾秒後它自己回來，其他的沒受影響。」
3. 「我想知道現在哪些在跑，下一個指令就看得到。」
4. 「它不會同時跑兩份。」（同一個 unit 只會有一個實例；文件寫明換過來前要停掉手動起的那幾個。）
5. 「裡面沒有我的權杖。」

合併前驗得到的只有：unit 與腳本的形狀正確、範例無權杖無真實路徑、文件步驟齊全且提到的每個指令與檔名都存在；若測試環境有 `systemd-analyze`，用 `systemd-analyze verify` 檢查範本（把佔位字換成暫存路徑後）；有 `powershell.exe` 時跑安裝腳本的預設模式確認不產生工作。五個例子的實際行為都屬人工項，要在桌機上做。

## 測試怎麼做

- bash 測試 `tests/desktop_systemd_test.sh`（比照 `tests/hosted_deploy_test.sh` 的風格），先寫會失敗的測試。
- 全套以 PR 上的 CI 為準。

## 裁決（lead，2026-11-13，回應 verifier P1–P8）

P1 範例檔放 `deploy/station.env.example`（不放 `deploy/systemd/` 下）。`tests/hosted_deploy_test.sh` 點名改兩處、其餘不動：TC-069 的檔案清單加入 `deploy/systemd/abf-station@.service.in`、`deploy/station.env.example`、`deploy/wsl/keep-wsl-running.ps1`；TC-083 的 `.service.in` 數由 3 改 4。
P2 站台 unit 只帶 `NoNewPrivileges=true`（附一句註解），不帶 `PrivateTmp`、`ProtectHome`、`ProtectSystem`、`PrivateNetwork`、`RestrictAddressFamilies`、`ReadOnlyPaths`、`ReadWritePaths`。
P3 站台 unit 加 `RestartPreventExitStatus=2 3`：設定有錯或權杖被拒就停在 failed，不無止境重試。
P4 文件寫明 agent 拒絕啟動的原因看 `journalctl --user -u 'abf-station@<名字>'`。
P5 排程工作明設：執行時間不設上限、用電池也啟動、換電池不停止、同時只留一個實例、隱藏、觸發器指定目前使用者、一般權限。
P6 照建議：兩個 `EnvironmentFile` 都不加 `-`；env 檔的 `PATH` 要寫完整；用 `%i`；agent 名字只用英數、底線、點。
P7 linger 與保活工作兩者都要，文件照實寫可能需要 sudo、`systemd=true` 需要新版 WSL（`wsl --update`）、沒有人登入 Windows 時不會啟動。這幾點實際行為是人工項。
P8 照建議。

## 裁決（lead，2026-11-13，驗收不通過之後的修正輪）

驗收：unit 與腳本的形狀都過，但文件照字面做會把維護者卡在唯一能用的機器上。以下全部要修（D1–D8 是文件，D9 是腳本），每項都要有 `tests/desktop_systemd_test.sh` 的檢查釘住。

D1 裝 unit 那一步先 `mkdir -p ~/.config/systemd/user ~/.config/abf-platform`。
D2 「從手動啟動換過來」寫明真實情況與順序：`wsl --shutdown` 本身就會停掉所有手動起的平台行程；重開後、啟用服務前，用一個指令確認沒有殘留（列出行程，不是砍行程），有殘留才給出停止它們的確切指令。不得寫「按 Ctrl+C 或關掉終端機」。
D3 新增「退回手動啟動」一小段：停用並移除四個服務、把 `/etc/wsl.conf` 的 `systemd=true` 拿掉、`wsl --shutdown`、用原本的方式啟動（指向既有的升級／啟動說明所在處）；並說明保活工作要一併 `-Remove`。
D4 多個 agent：寫明「每個 agent 各一份 `station-<名字>.env`、各 enable 一次」，舉兩個 agent 的例子；可沿用既有的權杖檔（檔名不必等於實例名）；實例名只用英數、底線、點，不能含 `-`。
D5 國網重新連線：給出確切作法（`scripts/reset_master.sh` 或 setup 流程中開共用連線的那一步，以 repo 實際存在者為準），並說明要本人輸入 OTP。
D6 env 檔要放什麼，照程式實際讀的寫，不得舉會誤導的例子：平台三個服務讀哪些變數；agent 需要哪些（共用連線、部署資料夾之外，Google Batch 的 agent 需要 Java 17／`JAVA_HOME`、nextflow 與 gcloud 在 `PATH`、`ABF_STATION_GCP_CREDENTIALS`、`ABF_STATION_UPLOADS`，以 `docs/OPERATIONS.md` 既有說明與程式為準）。寫一句：手動啟動時這些來自 `~/.bashrc`，systemd 不讀它，所以先把 `~/.bashrc` 裡 export 的每一項對照一遍。`deploy/station.env.example` 的註解同步補上。
D7 每個 `cp deploy/...` 之前寫明先 `cd` 到 repo。`docs/TESTING.md`：TC-018 教他怎麼一次看四個服務的行程編號前後有沒有變；TC-030 給出確切指令（手動再起一份 web，預期看到連接埠被占用的錯誤）；TC-013 寫明每個指令要看到什麼。
D8 不得寫「hidden window」這類不實的話。照 D9 的實際行為寫。
D9 保活工作不得讓使用者每次登入看到一個不能關的黑視窗。排程工作的動作改為 `powershell.exe -NoProfile -WindowStyle Hidden -Command "& wsl.exe [-d <distro>] --exec /bin/sleep infinity"`（視窗可能閃一下就消失）。這修訂 TC-004 的「動作是 wsl.exe」為「動作是經隱藏視窗的 powershell 啟動 wsl.exe，最終執行的仍恰為 `wsl.exe [-d <distro>] --exec /bin/sleep infinity`」。是否真的不留視窗屬人工項，文件與 TESTING 照實寫「若仍看到視窗，請最小化不要關，並回報」。
另：文件補一句——若公司政策禁止 `-ExecutionPolicy Bypass`，把腳本複製到 Windows 資料夾後以滑鼠右鍵「用 PowerShell 執行」，或回報。

## 裁決（lead，2026-11-13，第二次驗收（窄 REJECT）之後）

E1（最重要，看起來會像資料全部不見）：步驟 3 複製 `deploy/env.example` 之後，緊接著明寫：在複製出來的檔裡刪掉 `ABF_PLATFORM_DB=...` 那一行與 `ABF_SITE_ADDRESS=...` 那一行（後者是 Caddy 用的）；只有 `~/.bashrc` 原本就 export 了 `ABF_PLATFORM_DB` 才放回去，而且值要一模一樣；絕不自己編一個新資料夾——新資料夾等於一個空的平台。啟用服務之後加一個檢查點：網站上要看得到原本的分析記錄；是空的就停下，回到步驟 3。這段要用醒目的方式寫（獨立一段、開頭標「重要」）。`deploy/env.example` 該行的註解可加一句指向這段，但不改變數本身。
E2 清殘留：不得給 `pkill -f 'abf-platform|abf-station'`。改為 `pgrep -af 'abf-(platform|station) (serve|web|mcp|run)'` 列出，再寫「只對列出的行程編號用 `kill <編號>`」。另外在步驟 2（`wsl --shutdown`）之前加一步：趁手動起的行程還在，先列出並存下它們的完整指令列與相關環境變數（`ABF_`、`PATH`、`JAVA_HOME`、`XDG_` 開頭的），並提醒：服務用的是 8787／8788／8789 與 `--public-url ${ABF_PUBLIC_URL}`，若手動啟動時用了別的連接埠或旗標，先改 unit 再啟用。
E3 國網重新連線：寫成確切的三步——在原本那個互動式終端機（因為部署設定檔的位置來自 `~/.bashrc`）、先 `cd` 到 plugin 資料夾、執行 `scripts/on_site.sh --check-reach`，把它印出的那一行貼上並由本人輸入 OTP；再以 `scripts/on_site.sh --check-master; echo $?` 確認印出 0。不得指向 `reset_master.sh`（那是關連線）。寫明：agent 約每 25 秒自己重查一次，不必重啟；一分鐘內到網站的站台連線狀態看是否變回「開」（這是人工項）。
E4 中斷時間照實寫：平台從 `wsl --shutdown` 起到服務啟用完成為止都是停的。把「寫 env、準備 unit 檔、每個 agent 的 env」這些準備工作全部移到 shutdown 之前做完，shutdown 之後只剩「確認無殘留、`daemon-reload`、`enable --now`、看狀態」，並寫「中斷時間約幾分鐘，取決於你打這幾個指令的速度」。注意：`/etc/wsl.conf` 也在 shutdown 之前改好；`~/.config/systemd/user/` 下的檔可以在 systemd 還沒開時就先放好。
E5 `sed` 那一行不得寫死 venv 的資料夾名：寫「換成你的 venv 資料夾名（在家目錄下）」，並給一個指令找出它（看現有行程的指令列）。
每項都要有 `tests/desktop_systemd_test.sh` 的檢查釘住；E2 的檢查要釘「文件不含寬的 pkill 樣式」。
