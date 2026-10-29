---
id: upgrade-agents-reconnect-check
title: 平台升級腳本重啟後，逐一確認每個已註冊的站台代理人都重新連上，沒連上就用白話點名並以非零結束
tier: B（原擬 A；查證後降級，理由見「## 裁決」第 1 條）
kinds: backend
lane: L35-upgrade-reconnect
branch: fix/upgrade-agents-reconnect-check
base: origin/v3（行號取自 origin/v3@835d47e；executor 開工前用 `git show origin/v3:<檔>` 重查）
source: 2026-10-29 nano4 停擺——平台重啟後站台代理人收到 403，沒有人發現
---

# upgrade-agents-reconnect-check

> 只有計畫、沒有程式。**tier 暫列 B**：派工前需維護者點頭（見裁決 1、2）。

## 目標
平台升級（拉新碼、安裝、重啟三個服務）之後，由一支腳本等一小段有限時間，確認重啟前在線的每個站台代理人都重新打過招呼；沒打的就用白話列出名字並以非零結束。這樣「重啟後代理人被拒（403）卻沒人發現」會在升級當下被抓到，而不是等使用者發現跑不動。

## 維護者原話（verifier 出題用）
- 「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」
- 「絕不放寬安全網」
- 除上述兩句之外，**沒有**與本件相關的維護者原話。事件描述（2026-10-29 nano4 停擺，代理人重啟後 403 無人察覺）來自派工說明，不是維護者逐字裁示，verifier 不得把它當原話出題。

## 範圍：檔案（只准改這些）
- 新增 `deploy/platform-upgrade.sh`（名稱待裁決 2）
- 新增 `tests/platform_upgrade_test.sh`（`run_all.sh` 會以 `tests/*.sh` 自動收進，見 `tests/run_all.sh:340`）
- `docs/OPERATIONS.md`：只改「Upgrade」那一段（約第 203–214 行），把三行指令旁加一句「或執行 `deploy/platform-upgrade.sh`」
- `tests/hosted_deploy_test.sh`：**僅**第 283 行 `want_list` 加入新檔名一項（TC-069 釘死 `deploy/` 內容，不改它就會紅）。這是既有斷言的必要改動，不是放寬；需維護者在裁決 2 點頭。
- **不准碰**：`platform/` 底下任何檔案（含 `agents.py`、`cli.py`、`mcp_server.py`、`store.py`）、`deploy/backup.sh`、`deploy/systemd/*`、其他既有測試的斷言。

## 作法
- **證據（origin/v3@835d47e）**
  - **腳本不存在**：全部分支與歷史搜 `platform-upgrade` 都沒有結果（`git log --all -S"platform-upgrade"` 空）。現行升級是 `docs/OPERATIONS.md:203-212` 的三行手動指令：`git pull`、`pip install ./platform`、`systemctl --user restart abf-serve abf-mcp abf-web`。所以這件是「新增一支腳本」，不是「在既有腳本加檢查」。
  - **平台怎麼知道代理人連著**：`platform/abf_platform/agents.py:30-32` `status_of`——最後聯絡超過三次心跳（`common.py:139` `offline_after_seconds()` = 3×20 = 60 秒）算 offline；`agents.py:116` `touch` 與 `agents.py:83-85` `register` 寫 `last_seen_at`；`agents.py:40-56` `list_agents(state_path, at)` 唯讀開檔，回傳 `name`、`status`、`last_contact_at`（ISO 毫秒）。「已註冊」＝`agents` 表有列（`store.py:200` 起；說過 hello 就永久有列）。
  - **403 為何不更新 last_seen**：`agents.py:160` 與 `agents.py:152`——owner 不符或 token 名不符回 403，且 `register`（`agents.py:82`）在寫入前就拋 `OwnerMismatch`，所以被拒的代理人 `last_seen_at` 不會動。「重啟後 last_seen 沒前進」因此正好抓得到這個失敗。
  - **沒有現成的終端指令列代理人**：`platform/abf_platform/cli.py` 沒有 `agents` 子命令（只有 MCP `mcp_server.py:69-72` 與 `actions/__init__.py:228` 的 `list_agents`）。**但不需要新 API**：腳本用平台 venv 的 python 直接呼叫既有的 `agents.list_agents`（唯讀）即可。
- **決定**
  1. 重啟**前**：讀 `list_agents`，記下 `status == online` 的名字（期望集合）與時間 T0（取自重啟前一刻的 epoch 秒）。
  2. 重啟三個服務（指令可由環境變數 `ABF_UPGRADE_RESTART_CMD` 覆寫，預設為文件上那行；測試用它換成假指令，絕不呼叫真的 `systemctl`）。
  3. 重啟**後**：每 2 秒（`ABF_UPGRADE_POLL_SECONDS`）讀一次，直到期望集合每個代理人的 `last_contact_at` 晚於 T0，或超時。預設上限 120 秒（`--wait N` / `ABF_UPGRADE_WAIT_SECONDS`；心跳 20 秒，120 秒夠三次心跳＋一次重試）。
  4. 全部回來：印一行 `All N agents reconnected.`，結束碼 0。
  5. 有人沒回來：用白話印出「這些代理人重啟後沒有重新連上：A、B。請檢查它們的 token 和擁有者（`abf-platform agent-token`、`docs/TESTING.md` 的 403 一節），並看代理人的日誌」，結束碼 1。重啟指令本身失敗：原樣失敗（結束碼非 0，不進入等待）。
  6. 重啟前沒有任何在線代理人：印「沒有在線代理人可檢查」，結束碼 0（見裁決 3）。
  7. 腳本只讀 `platform.db`，不寫、不刪、不 `scancel`、不碰站台；不印 token。資料夾尋找方式照 `deploy/backup.sh`（`ABF_PLATFORM_DB`／`ABF_PLATFORM_STATE`／`XDG_DATA_HOME`）。
- 腳本風格照 `deploy/backup.sh`：`#!/usr/bin/env bash`、`set -euo pipefail`、可執行位元、參數錯誤結束碼 2。

## 失敗先行測試
全在新檔 `tests/platform_upgrade_test.sh`（風格照 `tests/hosted_deploy_test.sh`：`ok`/`bad` 函式、`TC-` 標籤、暫存資料夾、不碰網路不碰 systemd）。測試用平台自己的 `store.init_state` 與 `agents.register(state, name, version, clock)` 在暫存 `platform.db` 造代理人；假重啟指令是一個小腳本，用 `register` 讓指定代理人「重連」。改程式前整檔紅（檔案不存在），紅的輸出貼進 ledger。
- TC-U1 兩個代理人都在線，假重啟讓兩個都重連 → 結束碼 0，輸出含 `2 agents reconnected`。
- TC-U2 兩個在線，假重啟只讓 `alpha` 重連 → 結束碼 1，輸出含 `beta`、不含 `alpha`（在「沒重連」那句裡）；用 `ABF_UPGRADE_WAIT_SECONDS=3` 縮短等待，整支測試在 15 秒內跑完。
- TC-U3 **403 情境**：`beta` 的 token 名字對不上擁有者，假重啟對 `beta` 呼叫 `register` 會拋 `OwnerMismatch`（不寫入）→ 結束碼 1 且點名 `beta`。這條是本事件的重現。
- TC-U4 重啟前就離線的代理人（`last_seen_at` 很舊）不列入期望 → 它不重連也不算失敗，結束碼 0。
- TC-U5 重啟前沒有任何代理人 → 結束碼 0，輸出有「沒有在線代理人可檢查」。
- TC-U6 重啟指令本身結束碼非 0 → 腳本結束碼非 0，且**沒有**進入等待（用 `time` 或標記檔確認 3 秒內結束）。
- TC-U7 超時有界：`ABF_UPGRADE_WAIT_SECONDS=2` 且無人重連 → 在 ≤ 6 秒內結束，不會無限等。
- TC-U8 靜態：檔案存在、可執行、shebang 為 `#!/usr/bin/env bash`、`bash -n` 通過、含 `set -euo pipefail`；程式碼（排除註解）不含 `curl|wget|scp|rsync|ssh|rm |scancel|DELETE|UPDATE|INSERT`（唯讀＋不碰站台）。
- TC-U9 輸出與日誌不含 token：造一個 tokens.db 內含字串 `SECRET_TOKEN_VALUE`，跑 TC-U2 情境，輸出不含該字串。
- 對照組（必須一直綠）：`bash tests/hosted_deploy_test.sh` 全綠（含更新後的 TC-069）；`bash tests/platform_test.sh` 不受影響。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `hosted_deploy_test.sh`，貼輸出，證明唯一差異是 TC-069 清單多一項。

## 完成標準（done when）
- TC-U1…U9 改前紅（檔案不存在）、改後綠；對照組全程綠。
- 整個測試套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含「範圍」列的檔案；`platform/` 沒有任何改動；`hosted_deploy_test.sh` 的差異只有 `want_list` 一項；沒有既有測試被改弱。
- 在 `docs/OPERATIONS.md` 的 Upgrade 段，原本的三行指令**一字未動**（腳本是多一條路，不取代手動路徑）。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`bash tests/platform_upgrade_test.sh`（多數檔在 Git Bash 可跑；本檔只用 bash 與平台 venv 的 python）。
  - 全套：`tests/run_all.sh` 拒絕原生 Git Bash，在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 必須在本機磁碟，不能在同步硬碟；同一個 checkout 同時跑兩次會互相弄壞暫存副本。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 不准跑：任何真的 `systemctl`、碰站台／HPC、用 `~/.config/agentic-bioflow` 對真實部署。測試的資料全在暫存資料夾，`ABF_PLATFORM_DB`／`ABF_PLATFORM_STATE`／`ABF_PLATFORM_TOKENS` 一律指向它。
- 心跳常數：`common.py:96` 心跳 20 秒；`common.py:139` 離線門檻 60 秒；測試可用 `ABF_AGENT_HEARTBEAT_SECONDS`（`common.py:130`）縮短。

## 不做
- 不改 `platform/` 任何程式；不新增 API、CLI 子命令或資料表欄位（不需要 migration：只讀既有 `agents` 表）。
- 不自動修復沒連上的代理人（不重發 token、不重啟站台）；只偵測並點名。
- 不把檢查掛進 systemd 單元或排程；本件只是升級腳本的一步。
- 不取代 `docs/OPERATIONS.md` 現有的手動三行升級。
- 不做備份（Upgrade 段開頭已寫「先備份」，腳本只在輸出提醒一句，不執行 `backup.sh`）。
- 不通知任何外部（無 email、無 webhook）。

## 裁決
1. **A 還是 B？** 派工說明的條件是「讓安全網更嚴、不改正常成功路徑」才算 A。但 `abf-platform-upgrade.sh` 在 origin/v3@835d47e 根本不存在，這件實際是「新增一支操作員腳本＋改一行既有測試清單＋改文件」，是使用者（操作員）看得到的新入口，不符 A 的「不改使用者看得到的行為」。**建議：定 B。** 不需要新平台 API（讀既有 `agents.list_agents` 即可），所以不是 C。若維護者其實手上有一支沒進 repo 的腳本，請給路徑，則改為 A 並把範圍換成該檔。
2. **腳本放哪、叫什麼？** **建議：`deploy/platform-upgrade.sh`**（與 `backup.sh` 同為操作員腳本）；代價是 `tests/hosted_deploy_test.sh:283` 的 TC-069 要加一項。替代是放 `scripts/`，但那裡是給外掛的，不建議。
3. **重啟前沒有在線代理人算通過還是失敗？** **建議：通過（結束碼 0）並印一句說明。** 全新部署第一次升級不該被擋；而「重啟前就離線」的代理人另有它的離線訊號，不是本檢查要管的。
4. **期望集合怎麼定？** **建議：只算重啟前 `online` 的代理人。** 不算所有曾經註冊過的：退役的代理人永遠不會回來，會讓每次升級都失敗，操作員很快就會學會忽略（等於沒有安全網）。
5. **「重連」怎麼判定？** **建議：`last_contact_at` 晚於 T0（重啟前一刻）。** 不用 `status == online`，因為重啟前的最後聯絡可能還在 60 秒窗內，會誤判成已重連。
6. **等待上限？** **建議：預設 120 秒，可用 `--wait`／`ABF_UPGRADE_WAIT_SECONDS` 改。** 心跳 20 秒，120 秒涵蓋三次心跳加一次重試；超時就算沒連上。
7. **腳本要不要也執行 `git pull` 與 `pip install`？** **建議：要，依文件順序，任何一步失敗就停（`set -e`），在那之後才重啟。** 但這會讓腳本在測試裡需要假指令：每一步都能用環境變數覆寫（`ABF_UPGRADE_PULL_CMD`、`ABF_UPGRADE_INSTALL_CMD`、`ABF_UPGRADE_RESTART_CMD`），預設是文件上的指令。若維護者想要更小，可退為「只做重啟＋檢查」，pull 與 install 仍手動；我仍建議全包，否則還是有人會忘了某一步。
8. **失敗時要不要自動回復到舊版本？** **建議：不要。** 回復屬於改動部署的動作，超出偵測的範圍；腳本只點名並給下一步提示。

### developer-agent 確認
（待 developer-agent 逐條確認後補上。）

### developer-agent 確認（2026-10-29）
裁決 1–8 全照建議定案：B 級（新增操作者腳本 `deploy/platform-upgrade.sh`，非 UI → verifier 通過＋CI 綠自合）；只看重啟前在線的代理、以 last_contact_at > T0 判定重連、預設等 120 秒、不自動回滾。本機沒有未推送的舊腳本，維持 B。

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
