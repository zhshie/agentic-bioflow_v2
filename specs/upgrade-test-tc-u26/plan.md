---
id: upgrade-test-tc-u26
status: needed
title: TC-U26 在 v3 上必紅（它拿「和 merge-base 的差異」當檢查，但差異早已併入）；改成檢查現況
tier: A
kinds: backend
lane: L47-upgrade-u26
branch: fix/upgrade-test-tc-u26
base: origin/v3@2552583b；executor 開工前用 `git show origin/v3:<檔>` 重查行號
source: specs/upgrade-hint-followup/ledger.md 第 7 行（閱卷時發現並註明「base 上本來就紅」）
---

# upgrade-test-tc-u26

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。
> **調查結論（給派工者）：需要做（status: needed）。** TC-U26 在 v3 上必紅，不是偶發；證據見下。**尚未實跑**——主 checkout 目前在分支 `pr103`、不是 v3，依指示不跑，結論來自讀程式碼加既有 ledger。executor 動手前先在乾淨的 v3 worktree 實跑一次，把紅輸出貼進 ledger 當 RED 證據；若紅輸出與下面推演不符，回報 developer-agent，不要硬改。

## 目標
`tests/platform_upgrade_test.sh` 的 TC-U26 宣稱「`tests/hosted_deploy_test.sh` 只在 want_list 多了 `$D/platform-upgrade.sh` 一項」，但它的檢查方式是「對照 merge-base 的 diff 必須恰好 1 行刪、1 行增」。那一項早在 upgrade 腳本 PR 合併時就進了 v3，現在 v3 上對 merge-base 的 diff 是空的，所以必紅。改成直接檢查「現在的 want_list 真的含這一項、其餘六項沒少」，讓這條測試恢復它原本想保護的事。

## 維護者原話（verifier 出題用）
- 原計畫 `specs/upgrade-agents-reconnect-check/test-case.md:15`：「絕不放寬安全網」→ TC-U25、TC-U26、TC-U27。
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。

## 範圍：檔案（只准改這些）
- `tests/platform_upgrade_test.sh`（只改 TC-U26 那一個 `if … ok … else bad … fi` 區塊，原約第 226 行，並把它移到外層 git 判斷之前）
- **不准碰**：`deploy/` 底下任何檔、`tests/hosted_deploy_test.sh`、`platform/`、`docs/`、`.github/`、TC-U28 區塊（見裁決 3）、`specs/` 下任何檔。

## 作法
- **證據**（origin/v3@2552583b）：
  - `tests/platform_upgrade_test.sh:223-229`：`mb=$(git merge-base origin/v3 HEAD …)`；:225 `d=$(git diff -U0 "$mb" -- tests/hosted_deploy_test.sh | …)`；:226 要求 `grep -c '^-'` 與 `grep -c '^+'` **都恰為 1** 且新增行含 `$D/platform-upgrade.sh`，否則 `bad "TC-U26"`。
  - `tests/hosted_deploy_test.sh:283`：`want_list` 已含 `$D/platform-upgrade.sh`（那一項早已合併）。
  - 推演：在 v3 上 HEAD＝origin/v3 → merge-base ＝ HEAD → diff 為空 → 兩個 `grep -c` 都是 0，不等於 1 → `bad "TC-U26"`。在 v3 之上的任何分支只要沒碰 `hosted_deploy_test.sh` 也同樣紅；若碰了別處，行數又不對，也紅。所以這條在這個 repo 的任何正常狀態下都不會綠。
  - 旁證：`specs/upgrade-hint-followup/ledger.md:7` 已記「TC-U26 … already FAILs on the base (108bfdff) … #281 is already merged so the diff is empty」，當時因超出範圍刻意沒碰。
  - 不是偶發：判斷式只依 git 歷史，與時間、網路、順序無關。**唯一例外**：沒有 git 或沒有 `origin/v3` 引用時，:223 的 `if` 失敗 → 走 :229 `skip`（淺 clone 沒抓 origin/v3 的 CI 會看到 skip 而非紅，保護力同樣為零）。
- **決定（改法）**：把 TC-U26 換成「看現況」的檢查，**不再依賴 git 歷史**（因此不需要 `origin/v3`，淺 clone 也能跑、不再被 skip）：
  1. `tests/hosted_deploy_test.sh` 裡以 `want_list=` 開頭的那一行含 `$D/platform-upgrade.sh`（`grep -E '^want_list=.*\$D/platform-upgrade\.sh'`）。
  2. 同一行仍含其餘六項：`Caddyfile.template`、`backup.sh`、`env.example`、`systemd/abf-mcp.service.in`、`systemd/abf-serve.service.in`、`systemd/abf-web.service.in`。
  標籤：`TC-U26 hosted_deploy_test.sh want_list names platform-upgrade.sh and the six originals`。「hosted_deploy_test.sh 全綠」已由 :222 的 TC-U24/U25/U30 負責，不重複。
- 結構：把 TC-U26 區塊移到 :223 的 `if mb=…` 之前；TC-U28 留在原 if 內不動。

## 失敗先行測試
- RED（改前）：在乾淨 v3 worktree 跑 `bash tests/platform_upgrade_test.sh`，預期含一行 `TC-U26 … FAIL`，末尾 `1 FAILED`。紅輸出貼進 ledger。需要時先 `git fetch origin v3`。
- **負向證明**（一次性、貼進 ledger，不進 repo）：在 worktree 內暫時把 `tests/hosted_deploy_test.sh:283` 的 `$D/platform-upgrade.sh` 刪掉，新 TC-U26 必須紅；再還原後只刪 `backup.sh`，新 TC-U26 也必須紅；最後 `git checkout -- tests/hosted_deploy_test.sh` 還原。證明新檢查真的在檢查，不是換成無條件 ok。
- GREEN（改後）：同一支腳本 TC-U26 為 ok，整支 `all platform_upgrade tests passed`；ok 行數 ＝ 改前 ok 行數 ＋ 1。

## 完成標準（done when）
- RED 紅輸出、負向證明兩次紅、GREEN 全綠都已貼 ledger。
- `bash tests/platform_upgrade_test.sh` 全綠；全套 `tests/run_all.sh` 全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含 `tests/platform_upgrade_test.sh`；除 TC-U26 區塊外沒有任何既有斷言被刪或放寬；TC-U26 不再 skip。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。
- 單檔：在 WSL repo 根目錄 `bash tests/platform_upgrade_test.sh`；沒有 Python ≥3.10＋starlette 時整支腳本會 `skip` 並 exit 0（:27-30），看到 skip 不等於綠，要換有 starlette 的環境。
- 全套：從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`；超過 10 分鐘一律 `run_in_background`，用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 等；背景還在跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 與 `upgrade-hint-followup`（L43）改同一支檔但不同區塊（它刪 TC-U27 並新增一條）；若它先合併，rebase 即可，行號會動，照標籤文字找區塊。

## 不做
- 不放寬：不把 TC-U26 改成無條件 ok、不用 `|| true`、不降成 skip。
- 不改 TC-U28（它在 v3 上 diff 為空所以綠，語意是功能分支的範圍護欄，沒有壞）。
- 不改 `hosted_deploy_test.sh`、`platform-upgrade.sh`。

## 裁決
1. **TC-U26 到底紅還是偶發？** 必紅。依據：判斷式只依 git diff，v3 上 diff 為空；既有 ledger 已在 base 上觀察到同一現象。**本次未實跑**（主 checkout 在 `pr103`，依規定不跑），由 executor 的 RED 步驟實測。
2. **把 diff 檢查換成現況檢查，算不算放寬？** 不算：原檢查只在「那個 PR 尚未合併」的當下有意義，現在它永遠紅、也不保護任何東西。新檢查驗的是它標籤上宣稱的事（清單含該項、其餘六項沒少），並有負向證明。**定案：換，verifier 要檢視負向證明。**
3. **TC-U28 要不要一起處理？** 不要，它沒壞。**定案：留在原 if 內不動。**
4. **路徑問題？** 用相對 repo 根的 `tests/hosted_deploy_test.sh`；腳本開頭已 `cd "$ROOT"`（:9），與同檔其他區塊一致。

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
