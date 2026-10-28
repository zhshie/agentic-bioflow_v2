---
id: preflight-ssh-fold
title: reach=ssh 時，preflight.sh 把「egress／agent／資源契約」三次站台呼叫併成一次（issue #13 第 3 項的殘餘）
tier: A
kinds: backend
lane: L3-preflight
branch: fix/preflight-ssh-fold
base: v3（`origin/v3` 2233693；查證日 2026-10-28）
source: GitHub zhshie/agentic-bioflow_v2 issue #13 第 3 項。技能層的合併已完成（見「查證結果」），本檔只處理剩下的 preflight.sh。
---

# preflight-ssh-fold

> 本檔由 developer-agent 助手起草（2026-10-28）。A 級：使用者可見的輸出與結束碼逐字不變，只減少 ssh 往返。

## 目標
`reach: ssh` 時，`scripts/preflight.sh` 現在為了「站台能回答的三件事」連開三次 `on_site.sh --script`（外加前面一次 `--check-reach`）。改成三件事共用**一次** `--script` 呼叫，其餘行為一個字都不變。對使用者的意義：每次 launch／setup 的 preflight 少兩個 ssh session，離 PITFALLS 16e 的 session 上限（超過會無聲卡死）更遠一點。

### 查證結果（動手前的事實，全在 `origin/v3`）
- 技能層已完成，不重做：`scripts/site_report.sh`（commit 19fb297，標頭 `:1-27` 引用 issue #13）已把 agent／resources／provenance／inventory 併成一次；`skills/downstream/SKILL.md` 步驟 1 與 >500 MB 分支已改用它；`tests/site_report_test.sh` 已存在。`skills/finish/SKILL.md:85-92` 步驟 1 沒有任何 `on_site.sh` 呼叫（本機讀 `analysis.md`、本機跑 `collect_provenance.py --brief`）。`--brief` 與 `scripts/env.sh` 也都已存在。
- 殘餘：`scripts/preflight.sh:49`（`--check-reach`）、`:111`（`egress_ctl.sh status`）、`:116`（`agent_ctl.sh status`）、`:120`（`check_resource_contract.sh`）——ssh 部署每次 preflight 開 4 次，`:110` 的 `if [ "$SITE" = 1 ]` 區塊內 3 次可併。
- `on_site.sh` 的 `--script` 模式把整個 `scripts/` 與 `configs/` 打包送過去（`scripts/on_site.sh:524-540`），所以新增一支兄弟腳本不用登記任何相依清單（`:527-533` 註解）。
- `--script egress_ctl.sh` 在 `scripts/on_site.sh:480-488` 有特例（為 `start` 讀額外網域並帶 `NF_RELAY_EXTRA_*`）。`status` 不需要這些；包裝腳本以別的檔名呼叫時不經過這個特例，executor 要實測 `egress_ctl.sh status` 的輸出在兩種呼叫下相同（見 T11）。
- `--check-reach`（`scripts/preflight.sh:49`）不併：它決定後面要不要問站台，且 master 掛掉時不能往下問（`:41-43` 註解）。
- 站台三項現況沒有 short-circuit：`:111-122` 前一項失敗不影響後一項；併起來必須維持。
- 計算 session 數的說明：`ssh -O check` 是控制面、不算 session（PITFALLS 16e）；但測試用的假 ssh 看到的是「ssh 被呼叫幾次」，所以測試數字是呼叫次數：改前 4、改後 2。

## 維護者原話（verifier 出題用）
issue #13 第 3 項逐字：

> ## 3. Per-check SSH hops don't batch
>
> Under \`reach: ssh\`, checks that logically belong together each open their own \`on_site.sh\` session: agent health, resource contract, provenance collection, results inventory. Each is a separate SSH round trip (and, per \`docs/PITFALLS.md\` 16e, a site that's run out of sessions can hang rather than fail — so more hops is also more exposure to that).
>
> **Suggested fix:** where a step's docs already say to run two or three of these checks back-to-back (e.g. \`finish\` step 1's "take stock" reads both \`analysis.md\` and runs \`collect_provenance.py\`), consider a single \`on_site.sh --script\` call that runs a small composed script doing all of them, rather than one \`on_site.sh\` invocation per check.

（反斜線為 GitHub 原樣。）對應測試：「agent health, resource contract … each open their own session」→ T1；「a single `on_site.sh --script` call」→ T1；「more hops is also more exposure」→ T1（次數下降）。維護者 2026-10-28 的範圍裁示見下方「裁決」，逐條對應 T2–T10。

## 範圍：檔案（只准改這些）
- `scripts/preflight_site.sh`（新；站台端包裝，依序跑三個既有腳本並印分段標記，不判斷、不改任何東西）
- `scripts/preflight.sh`（只動 `:110-123` 那個 `if [ "$SITE" = 1 ]` 區塊）
- `tests/preflight_ssh_fold_test.sh`（新；`tests/run_all.sh` 會自動收）
- `docs/PITFALLS.md`（檔尾新增一條：為什麼 ssh 下三件事併成一次、分段標記的格式、傳輸失敗時的行為）
- `specs/preflight-ssh-fold/ledger.md`（新，進度帳本）

**不准動**：`scripts/on_site.sh`、`scripts/site_report.sh`、`scripts/egress_ctl.sh`、`scripts/agent_ctl.sh`、`scripts/check_resource_contract.sh`、`tests/preflight_reach_test.sh` 與其他既有測試、`hooks/`、`skills/`、`platform/**`、`docs/` 其他檔。

## 作法
1. **新腳本 `scripts/preflight_site.sh`**（不帶參數；在站台上跑）。egress（`egress_ctl.sh status`）、agent（`agent_ctl.sh status`）、resources（`check_resource_contract.sh`）依序各跑一次，每段格式固定：
   ```
   @@preflight-begin egress
   <該腳本 stdout+stderr 原文>
   @@preflight-end egress rc=<退出碼>
   ```
   三段**無論前一段成敗都跑**（現況就是這樣），腳本本身 exit 0。呼叫兄弟腳本用 `"$HERE/<name>"`，風格同 `site_report.sh:67,74`（`== x ==` 分段風格若更合適可改用，但標記必須能被本機機械式解析、且不會與腳本輸出內容混淆）。輸出以 `2>&1` 合併，與現況 `out=$(… 2>&1)` 一致。
2. **`preflight.sh` 區塊**：`REACH=ssh` 時改成一次 `bundle=$(bash "$HERE/on_site.sh" --script "$HERE/preflight_site.sh" 2>&1)`，本機逐段解析 `rc` 與 `out`，之後**原樣沿用現有的三組 `say` 判斷**（成功印 `OK`、失敗印同樣的固定文字、`egress` 的 `grep -q WARNING` 與 `resources` 的 `head -1` 都套在解析出的 `out` 上）。`REACH=local` **保持現狀三次獨立呼叫**，一行不動，所以本機部署是照抄不是改寫。
3. **標記不全（傳輸本身壞了：ssh 逾時、包裝腳本沒送到、exit 255）**：三段都當失敗，各自用現有固定文字（`egress`／`agent`），`resources` 用 `head -1` 取整份輸出第一行；**不重試、不退回舊的三次呼叫**（重試一個卡住的 master 正是 PITFALLS 16e 要避免的事）。這是唯一與舊行為不逐字相同的路徑；見「待 developer-agent 裁決」。
4. **不新增設定鍵**；`ON_SITE_TIMEOUT` 對這次呼叫的意義是「三件事合計」（原本各自一個時鐘）。PITFALLS 新條目要寫明。

## 失敗先行測試（`tests/preflight_ssh_fold_test.sh`；現在會紅）
搭法：沿用 `tests/preflight_reach_test.sh` 的 `run()`／`has`／`hasnot`，假 ssh 比 `tests/on_site_test.sh:39` 的升級：每次被呼叫就 `echo "$*" >> $TMP/ssh.calls`；參數含 `-O check` 時 exit 0；否則把遠端指令交給本機 `bash -c`（stdin 的 tar 解到 `$TMP/site` 後在那裡執行，或直接 `cd` 到 repo——executor 擇一，寫進 ledger）。`LAB_SETTINGS_FILE` 設 `reach: ssh`、`site_host: me@example.org`、`storage_root`、`workspace_id`、`compute_env`；`TW_BIN` 指假 `tw`。三個站台腳本用旗標檔控制成敗（`$TMP/egress.up` 等）。

| # | 情境 | 期望（手算） |
|---|---|---|
| T1 | `reach: ssh`，三件事全綠 | `ssh.calls` 行數＝**2**（`--check-reach` 一次＋合併呼叫一次）；在 base 同一個測試跑出 4（紅燈輸出貼進 ledger） |
| T2 | 同 T1 | 輸出有 `^OK +egress`、`^OK +agent`、`^OK +resources`，exit 0 |
| T3 | 只有 egress 壞 | 有 `^FAIL +egress.*egress_ctl.sh.* start`，且同時有 `^OK +agent`、`^OK +resources`（前一段壞不擋後面）；exit 1 |
| T4 | 只有 agent 壞 | 有 `^FAIL +agent.*not running.*agent_ctl.sh.* start`，其餘兩項 `OK`；exit 1 |
| T5 | 只有資源契約壞 | 有 `^FAIL +resources`，且該行等於假契約腳本輸出的第一行；exit 1 |
| T6 | egress 輸出含 `WARNING`（rc=0） | 有 `^OK +egress` **和** `^FAIL +egress-host`（`started somewhere else`）；exit 1 |
| T7 | 三項全壞 | 三行 `FAIL`，各自固定文字；exit 1；`ssh.calls` 仍是 2 |
| T8 | `reach: local`（`LAB_RUNS_DIR` 已設） | `ssh.calls` 不存在或 0 行；輸出與 base 逐字相同（executor 在 base 與分支各跑一次 `diff`，貼 ledger） |
| T9 | `reach: ssh` 但 `--check-reach` 失敗（假 ssh 對 `-O check` exit 255） | 輸出沒有 `egress`／`agent`／`resources` 行；`ssh.calls` 恰 1 行；其餘同 `tests/preflight_reach_test.sh` 既有斷言 |
| T10 | 傳輸壞：`--check-reach` 通過，合併呼叫的假 ssh exit 255、無任何標記 | 三行 `FAIL`（固定文字；resources 行取首行）；exit 1；`ssh.calls` 恰 2 行（不重試） |
| T11 | 兩種呼叫同輸出 | 同一站台狀態下，`on_site.sh --script scripts/egress_ctl.sh status` 與 `preflight_site.sh` 內 egress 段原文相同 |
| T12 | 既有測試未改 | `tests/preflight_reach_test.sh`、`tests/on_site_test.sh`、`tests/site_report_test.sh`、`tests/credentials_stay_in_settings_test.sh`、`tests/no_second_run_state_test.sh` 零修改、全綠 |

**現在會紅的原因**：T1、T7（次數）、T10 在 base 算出 4／不符；`scripts/preflight_site.sh` 不存在，T11 找不到它。T2–T6、T8、T9 在 base 上本來就綠（它們是「行為不變」的守門員）——executor 先跑一次，貼紅綠分佈進 ledger；若 T2–T6、T8、T9 在 base 上不綠，代表假 ssh 搭得不對，先修測試再動手。

## 完成標準（done when）
- T1–T12 綠；整個 `tests/run_all.sh`（WSL）綠。
- `git diff --stat origin/v3 -- tests/preflight_reach_test.sh tests/on_site_test.sh` 為空（既有測試零改動）。
- `git diff --name-only` 只含「範圍：檔案」所列；「不准動」零命中。
- `REACH=local` 與 `REACH=none`，preflight 的 stdout／stderr／exit code 與 base 逐字相同（ledger 貼 diff）。
- 沒有真的 ssh／tw／Seqera 呼叫。
- 手動驗收（記 ledger，不擋合併）：在真 ssh 部署跑 `scripts/preflight.sh`，輸出與改前逐字相同，且站台 session 開啟少兩次。

## 環境事實
- 區塊與行號全在 `origin/v3:scripts/preflight.sh`（上文已列）；`reach=none` 不進該區塊（`:46`、`:110`）。
- 國網 Taiwania 是 `reach=ssh`；PITFALLS 16e：session 超過上限不報錯、只是卡住，`ssh -O check` 仍成功，所以 preflight 的 reach 行綠不代表後面不卡。
- 測試必須在 WSL／Linux 跑（`tests/run_all.sh` 開頭註解）；worktree 不可在同步磁碟。

## 不做
- 不改 `skills/`（技能層已完成，且 `finish` 步驟 1 本來就不經 ssh）。
- 不併 `--check-reach`；不碰 `site_report.sh`；不改 `on_site.sh`。
- 不與 `launch-reader-dies` 的 `launch_recheck.sh` 共用腳本（各自獨立；之後要共用再開單）。
- 不把 `REACH=local` 也改成走包裝腳本。
- 不新增設定鍵、不加快取。

## 待 developer-agent 裁決
1. 傳輸壞（T10）時「不重試、三項都報失敗」與舊行為（三次各自逾時、各印 `on_site.sh` 逾時訊息）不逐字相同。本檔預設接受這個差異（訊息本來就來自 `on_site.sh`，重試只會加深 16e）。若要求逐字相同，作法是標記不全時退回舊的三次呼叫——代價是在已壞的 master 上再開三個 session。
2. `ON_SITE_TIMEOUT` 變成三件事合計一個時鐘（預設仍 120 秒）。三件事全慢時比舊行為更容易逾時；是否調高這次呼叫的預設（要動 `on_site.sh`，故本任務沒做）？

## 裁決（2026-10-28 developer-agent）
1. Scope = scripts/preflight.sh lines ~111-120 only (egress status + agent status + resource contract → one `on_site.sh --script` call). --check-reach stays its own call (it decides whether the rest runs).
2. Stdout/stderr text and exit codes for every existing branch must stay byte-identical; existing preflight tests must pass unmodified. If one step's failure currently short-circuits the next, the bundled script must preserve that (per-section status markers parsed locally is fine; reuse site_report.sh's `== x ==` section style if it fits).
3. Test seed: fake ssh via ON_SITE_SSH_BIN counting sessions under reach: ssh → before 4, after 2; plus one case per section failing → same message/exit as before. Non-ssh reach (local/wsl) must open zero ssh sessions as today.
4. Doubt 2 (closing #13) is the maintainer's call — not your concern.
5. 待裁決 1：接受「傳輸壞時不重試、三項都報失敗」。這是裁決 2「逐字相同」唯一允許的例外，只限 on_site.sh 本身失敗（沒有任何標記）的情況；有標記的每一種情況仍須逐字相同。
6. 待裁決 2：不調高逾時、不改 on_site.sh。若實測三項合計常超過 120 秒，另開一件處理。
7. 計數只算 fake ssh 看到的開 session 呼叫；`ssh -O check` 不算（PITFALLS 16e），測試裡要明寫排除條件。

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
