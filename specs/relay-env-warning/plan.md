---
id: relay-env-warning
title: 直接用 NF_RELAY_PEER_PREFIXES= 前綴啟動中繼時，確認閘門要像 NF_RELAY_EXTRA_DOMAINS= 一樣點名警告
tier: A
kinds: backend
lane: L-hook（只動 hooks/confirm_launch.sh 與 tests/confirm_launch_test.sh；不與其他任務的檔案相交）
base: v3
after: relay-prefix-nano4
source: memory/dev-plans/relay-prefix-nano4.md 裁決 5 與裁決二第 2 點（「直接啟動時的警告另開小任務」）；PR #185（feat/relay-prefix-nano4）新增了 NF_RELAY_PEER_PREFIXES
---

# relay-env-warning

> 本檔由 developer-agent 寫（2026-10-24）。A 級：只讓一道既有的安全閘門「多說一句話」，不放寬任何東西、使用者看不到新畫面 → verifier 通過＋CI 綠由 developer-agent 自合。
> **`hooks/` 是受保護路徑**：developer-agent 必須在 PR 上跑 `/code-review`（不能只靠 verifier）。
> **前置**：`relay-prefix-nano4`（PR #185）要先合進 `v3`。該 PR 讓中繼讀環境變數 `NF_RELAY_PEER_PREFIXES`；沒有它，本任務要警告的東西還不存在。開工時以最新 `v3` 為準。

## 目標
`hooks/confirm_launch.sh` 在有人以 `NF_RELAY_EXTRA_DOMAINS=… bash scripts/egress_ctl.sh start` 這種**直接帶環境變數**的方式啟動中繼時，會在詢問裡點名「這條指令自己帶了一份清單」。對 `NF_RELAY_PEER_PREFIXES=`（決定**哪些主機可以連進中繼**）也要做同樣的事。對使用者的意義：他按「允許」之前，會看到這條指令偷帶了一份改變連線對象的清單，而不是只看到預設摘要。

## 維護者原話（verifier 出題用）
- 逐字取自 `memory/dev-plans/relay-prefix-nano4.md` 裁決 5：「該 hook 對 `NF_RELAY_EXTRA_DOMAINS=` 前綴會加警告（第 391–402 行），對對端前綴照理也該有；但這是安全閘門檔……必須兩個分支各跑一遍測試。」→ 要警告；要在 base 與分支各跑一次測試檔比對。
- 裁決二第 2 點：「`hooks/confirm_launch.sh` 不動；直接啟動時的警告另開小任務。」→ 本任務就是那個小任務。
- 本任務指示（developer-agent 2026-10-24）：照 EXTRA_DOMAINS 的樣子做，訊息風格與離場行為都照抄（警告／詢問，絕不默默放行；不得比 EXTRA_DOMAINS 的情況更弱）。→ 每一條 EXTRA_DOMAINS 的既有案例，都要有一條 PEER_PREFIXES 的對應案例。

## 範圍：檔案（只准改這些）
- `hooks/confirm_launch.sh`（只在第 391–402 行那個 `if [[ $CMD == *NF_RELAY_EXTRA_DOMAINS=* ]]…fi` 區塊**之後**，加一個結構相同的區塊）
- `tests/confirm_launch_test.sh`（只**新增**：一個輔助函式＋斷言列，加在現有 `envp` 那組之後；既有行一個字都不改）
- `specs/relay-env-warning/ledger.md`（新，executor 進度帳本）

**禁止碰**：`scripts/nf_relay.py`、`scripts/egress_ctl.sh`、`scripts/on_site.sh`、`platform/**`、`deploy/`、`docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`；也不改 `hooks/hooks.json`、`skills/`、`commands/`。

## 作法
1. **位置與條件完全照抄**：緊接在既有 EXTRA_DOMAINS 區塊之後（同一個 `RELAY_START_RE` 命中的 `if` 裡面），條件為 `[[ $CMD == *NF_RELAY_PEER_PREFIXES=* ]] && [[ $CMD != *on_site.sh* ]]`。`on_site.sh` 例外照舊：經 `on_site.sh` 時變數一律被設定檔的值取代（relay-prefix-nano4 作法 6），所以只有直接啟動需要點名。
2. **取值照抄**：同樣用正則 `RELAY_PEER_OVR_RE='NF_RELAY_PEER_PREFIXES=([^[:space:];&|]*)'` 加 `BASH_REMATCH[1]`；**不用** `${CMD#*…}`（長指令上是平方時間，#62）。
3. **訊息接在 `RELAY_LIST` 後面**（和 EXTRA_DOMAINS 一樣是附加一段，不另開一次 `ask`），固定句型：
   `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES=${值}, which changes which hosts may connect to the relay: it would accept hosts whose names start with THAT list instead of the deployment's setting (default cpn,gpn,bgm,lgn,localhost). Show the user the prefixes it names.`
   這句**不得含** `overrides this deployment's list`（那是 EXTRA_DOMAINS 專用字樣，既有 `envp` 測試靠它區分；兩段各自可辨）。
4. **離場行為不變且不更弱**：既有流程對任何 `egress_ctl.sh start|restart` 本來就 `ask`（要使用者明確同意）；本任務只是在同一個 `ask` 的文字裡多一段。不新增 `allow` 路徑、不新增 `exit 0` 分支、不改 `ask` 的呼叫方式。兩個變數同時出現時，兩段警告都要出現（先 EXTRA 後 PEER，順序固定）。
5. **便宜**：repo 教訓是 hook 逾時＝放行。所以新增的檢查只能是一個 bash 內建的子字串比對（`[[ == *…* ]]`）；只有命中時才多跑一次 `[[ =~ ]]`，不 fork、不呼叫 `grep`/`jq`/`python`。未帶該變數的指令（絕大多數）成本為一次子字串比對。
6. **空值也警告**：`NF_RELAY_PEER_PREFIXES=`（空）時，中繼會退回預設，但這條指令仍然是「帶了自己的值」，照 EXTRA_DOMAINS 的做法一樣點名（值顯示為空）。不為空值開例外——例外就是繞過閘門的縫。

## 失敗先行測試
全部放 `tests/confirm_launch_test.sh`，緊接在現有 `envp` 斷言列（第 798–801 行）之後。新增輔助函式 `envq`（複製 `envp`，只把比對字串換成 `THIS COMMAND ALSO SETS NF_RELAY_PEER_PREFIXES`）。現在全會紅（hook 沒有這段）。

應「有警告」（`has`）：
- `PEER-1 an env prefix on a relay start is named`：`NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start`
- `PEER-2 ...through env`：`env NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh restart`
- `PEER-3 ...through export`：`export NF_RELAY_PEER_PREFIXES=25a-cpn; bash scripts/egress_ctl.sh start`
- `PEER-4 an empty value is still named`：`NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start`
- `PEER-5 a quoted script path still triggers`：`NF_RELAY_PEER_PREFIXES=zzz-aaa bash "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start`
- `PEER-6 both variables: both warnings`：`NF_RELAY_EXTRA_DOMAINS=evil.org NF_RELAY_PEER_PREFIXES=zzz-aaa bash scripts/egress_ctl.sh start`（`envq` 查 PEER 段在；另用既有 `envp` 查 EXTRA 段也在）
- `PEER-7 the value is shown`：`NF_RELAY_PEER_PREFIXES=25a-cpn,25a-lgn bash scripts/egress_ctl.sh start` 的輸出含 `NF_RELAY_PEER_PREFIXES=25a-cpn,25a-lgn`

應「沒有警告」（`lacks`，對照組）：
- `PEER-8 a plain relay start does not say it`：`bash scripts/egress_ctl.sh start`
- `PEER-9 through on_site.sh it is not named`：`NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/on_site.sh egress_ctl.sh start`（走 `on_site.sh` 例外，與 EXTRA_DOMAINS 一致）
- `PEER-10 the EXTRA_DOMAINS-only case does not mention peers`：`NF_RELAY_EXTRA_DOMAINS=evil.org bash scripts/egress_ctl.sh start`
- `PEER-11 a stop does not say it`：`NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh stop`（只有 start/restart 才進這個區塊）

仍須「詢問」（不得被放行）：
- `PEER-12 the ask itself still happens`：以現有 `idg` 輔助函式（期望 `ask`）對 PEER-1、PEER-2、PEER-3 的指令各一條——證明新增的是文字、閘門本身仍在。

**既有斷言會被改的清單：無。** 第 798–801 行四條 `envp`、整個 `idg`／`idw` 組、其餘全部原樣；若有任何一條需要改才能綠，那是本任務做錯了，回報 BLOCKED。

## 完成標準（done when）
- 上面所有新測試綠；`bash tests/confirm_launch_test.sh` 全綠；全套綠（WSL 內 `bash tests/run_all.sh`，見 repo CLAUDE.md「For the executor and verifier」）。
- **兩個分支各跑一遍**（repo CLAUDE.md 校正失敗紀錄的要求）：在 `origin/v3`（含已合併的 #185）與本分支各跑 `bash tests/confirm_launch_test.sh`，輸出存檔後**逐行比對**：差異只允許是新增的 PEER-1…12 行；既有每一行的 ok／FAIL 狀態一致。比對結果貼進 ledger。
- `git diff --name-only origin/v3...HEAD` 只出現「範圍」列的三個檔；`git diff` 對 `scripts/`、`platform/`、`deploy/`、`docs/` 為空。
- `git diff hooks/confirm_launch.sh` 只有新增行（沒有刪除、沒有改動既有行）。
- developer-agent 在 PR 上跑過 `/code-review`，無未處理的 high 項。

手算對照（verifier 可直接用）：

| 指令 | PEER 警告？ | EXTRA 警告？ | 為什麼 |
|---|---|---|---|
| `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh start` | 有（值 `25a-cpn`） | 無 | 直接帶變數啟動 |
| `env NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh restart` | 有 | 無 | `restart` 也算啟動 |
| `export NF_RELAY_PEER_PREFIXES=25a-cpn; bash scripts/egress_ctl.sh start` | 有 | 無 | 子字串在整條指令裡 |
| `NF_RELAY_PEER_PREFIXES= bash scripts/egress_ctl.sh start` | 有（值為空） | 無 | 空值不開例外 |
| `NF_RELAY_EXTRA_DOMAINS=evil.org NF_RELAY_PEER_PREFIXES=zzz-aaa bash scripts/egress_ctl.sh start` | 有 | 有 | 兩段都出現 |
| `bash scripts/egress_ctl.sh start` | 無 | 無 | 沒帶變數 |
| `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/on_site.sh egress_ctl.sh start` | 無 | 無 | on_site.sh 會用設定檔的值取代 |
| `NF_RELAY_PEER_PREFIXES=25a-cpn bash scripts/egress_ctl.sh stop` | 無 | 無 | 非 start／restart |

以上每一條 `egress_ctl.sh start／restart` 形式都仍然 `ask`（本來就是，不因本任務改變）。

## 環境事實
（行號為 `origin/v3`；先 `git -C <repo> fetch -q origin`，用 `git show origin/v3:<path>` 讀。#185 合併前，變數出自分支 `origin/feat/relay-prefix-nano4`：`scripts/nf_relay.py` 第 248 行 `_PEER_RAW = os.environ.get("NF_RELAY_PEER_PREFIXES", "")`、`scripts/egress_ctl.sh` 第 83 行、`scripts/on_site.sh` 第 497／509 行。）
- `hooks/confirm_launch.sh`：`RESIDENT_RE` 在第 364 行附近；第 391–402 行是 `#45` 的 `NF_RELAY_EXTRA_DOMAINS=` 警告（`[[ $CMD == *NF_RELAY_EXTRA_DOMAINS=* ]] && [[ $CMD != *on_site.sh* ]]`，用 `RELAY_OVR_RE` 取值，附加到 `RELAY_LIST`），其後才是 `ask`。警告只是 `ask` 文字的一部分。
- `tests/confirm_launch_test.sh` 第 789–801 行：`envp` 輔助函式與四條斷言；比對字串是 `overrides this deployment's list`，用 `LAB_SETTINGS_FILE="$TMP/id_env.yaml"`；`idg`（期望 ask／allow）定義在檔案較前面，沿用即可。
- repo 教訓：hook 逾時＝放行（所以檢查必須便宜）；改閘門曾放行三種本該擋的形狀（CLAUDE.md 校正失敗 #1）→ 必須兩分支各跑一遍。
- repo CLAUDE.md「For the executor and verifier」：規則文件 `.specify/memory/constitution.md`；單檔測試 `bash tests/<name>.sh`；全套 `tests/run_all.sh` 須在 WSL／Linux（從 ASCII 路徑呼叫 `wsl.exe`）；repo 與 worktree 要在本機磁碟；**不得**改 `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`；**不得**連站台或 HPC。

## 不做
- 不改中繼、`egress_ctl.sh`、`on_site.sh` 的任何行為，也不改設定檔與文件。
- 不新增別的攔截：不對別的環境變數（例如 `NF_RELAY_PORT`）加警告、不對 `on_site.sh` 路徑加警告。
- 不重構既有 EXTRA_DOMAINS 區塊（不抽共用函式——為了讓 diff 只有新增行、好審）。
- 不改 `hooks/hooks.json` 的 matcher、不改 hook 逾時設定。
- 不改任何既有測試斷言。

## 裁決（2026-10-24，developer-agent 起草；與上文衝突時以本段為準）
1. **只加不改**：新區塊緊接在 EXTRA_DOMAINS 區塊之後，不合併、不抽函式。理由：安全閘門檔的審查成本由 diff 大小決定；純新增行可以逐行對照，抽函式會動到既有行，反而要重驗既有三種形狀。**另一選項**：抽共用函式。**預設：複製結構。**
2. **訊息獨立一段、用不同字樣**（不重用 `overrides this deployment's list`）。理由：既有 `envp` 測試以該字樣判斷 EXTRA 警告；兩段字樣相同會讓一種警告的缺席被另一種掩蓋。
3. **空值照樣警告。** 理由：「帶了自己的值」本身就是要使用者知道的事，空值例外等於替繞過閘門留縫。
4. **`on_site.sh` 例外保留。** 理由：relay-prefix-nano4 作法 6 讓 `on_site.sh` 一律以設定檔值覆蓋呼叫者環境，這裡警告會是假警報；與 EXTRA_DOMAINS 一致。
5. **等 #185 合併後再開工。** 理由：測試用的變數名稱與語意在 #185 才定案；若 #185 改名，本任務跟著改一處。

## 裁決三（2026-10-24 developer-agent，回應 verifier 出題退回；以本段為準）
3. 手動案例（git diff 範圍、兩分支逐行比對）不寫進 docs/TESTING.md：executor 把 `git diff --stat`、hook diff 只有新增行的證據、兩分支 confirm_launch_test.sh 輸出比對貼進 ledger.md，閱卷以 ledger 為依據並自己重跑核對。這是本專案所有「閱卷時看 diff」類手動案例的通例。
4. PEER-7 照 verifier 的 TC-009：斷言比對警告句，不比對整條指令。
5. 空值的說明改成「空值會被忽略，改用部署設定 relay_peer_prefixes」，與 egress_ctl.sh 的行為一致；仍然要警告（裁決二 1）。

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
