---
id: handlers-header-comment
title: handlers.py 第 1 行註解說「兩個內建唯讀 handler」，實際是九種 job kind 且其中三種會寫入；改正註解並加一則防再過期的測試
tier: A
kinds: backend
lane: L23-handlers-header
branch: test/handlers-header-comment
base: origin/v3@bb0e8d6（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 清理掃描；job-kinds-stale-docs 計畫裁決 2 明說 handlers.py:1 不在該件範圍、要另開
---

# handlers-header-comment

> 本檔由 developer-agent 的 subagent 寫（2026-10-29），只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。只改一行註解、加一則測試。

## 目標
`platform/abf_station/handlers.py` 第 1 行的註解說「這是兩個內建唯讀 handler」，但同檔的模組說明與 `JOB_KINDS` 都列了九種 kind，其中 `launch_nextflow`、`cancel_run`、`clean_work` 會在確認後寫入。把第 1 行改成與程式一致，並加一則測試，之後再加 kind 卻忘了改說明就會紅。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「過期文件與程式矛盾」要附 `file:line` 證據，且要能描述一則現在會紅的測試。
- 前置計畫 `job-kinds-stale-docs`（裁決 2）：`handlers.py:1` 同樣過期，但屬另一件，不併入該計畫。

## 範圍：檔案（只准改這些）
- `platform/abf_station/handlers.py`（**只改第 1 行註解**，保留 `# Not …` 前綴的寫法慣例；不動第 2 行起任何內容）
- `platform/tests/test_handlers_header.py`（**新檔**；檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，說明為何不加進既有檔，例如「現有 handlers 測試驗證各 kind 的行為，沒有檢查檔頭註解有沒有跟上 JOB_KINDS；這則只讀原始碼文字」）
- **不准碰**：`jobs.py`、`store.py`（他線在改）、`web*.py`、任何既有測試的既有斷言、`docs/`。

## 作法
### 證據（說明 vs 程式）
- 過期說明：`handlers.py:1`「# Not Ansible modules or Celery tasks: … these are two built-in read-only handlers, and a job is only data for them…」——「兩個」「唯讀」兩處都不對。
- 程式事實：同檔模組說明（第 2–8 行）描述九種 kind，含 `launch_nextflow`、`cancel_run`、`clean_work`（這三種在使用者確認後寫入）；`handlers.py:19` 的 `JOB_KINDS` 是九個元素的 tuple。
- 對照：第 1 行前半（不是 Ansible module、不是 Celery task 的理由）仍然成立，要保留意思。

### 決定
- 只改第 1 行：保留 `# Not Ansible modules or Celery tasks:` 的理由，把後半改成「these are the built-in handlers for the nine job kinds (three of them write, after a confirmation), and a job is only data for them」之類，語意與模組說明一致。數字用九，與 `JOB_KINDS` 對得上。
- 新增文字不得含站台掃描測試禁用的完整單字（見 `test_station_static.py:46` 附近：不得出現小寫完整單字 azure；本行不需要提它）。
- 用 `git diff -U0` 確認差異只有第 1 行。

## 失敗先行測試
新檔 `platform/tests/test_handlers_header.py`，先寫、改字前跑一次確認紅，紅的輸出貼進 ledger。測試以純文字讀 `handlers.py`（`Path(...).read_text`），不 import 站台模組、不連網、不開資料庫。
- `test_first_line_does_not_claim_read_only`：第 1 行（小寫後）不得含 `read-only`。**現在紅**。
- `test_first_line_does_not_claim_two_handlers`：第 1 行不得含 `two built-in`（也不得是「兩個」意思的 `two` 後接 `handler`）。**現在紅**。
- `test_first_line_names_the_job_kind_count`：把 `JOB_KINDS`（用 `ast` 從原始碼取 tuple 長度 N，現在是 9）轉成英文數字詞（`nine`），第 1 行必須含該詞。**現在紅**。
- 對照組（必須一直綠）：第 1 行仍以 `# Not Ansible modules or Celery tasks` 開頭；`JOB_KINDS` 長度寫死為 9（先釘事實，之後加 kind 會紅，提醒同時改註解）；既有 handlers 與 `test_scope.py`、`test_station_static.py` 不改、保持綠。
- 手動檢查（記 ledger，verifier 重跑）：`git diff -U0 origin/v3 -- platform/abf_station/handlers.py` 只有第 1 行一處；兩分支 `ast.parse` 後 AST dump 相等（註解不進 AST），輸出貼上。

## 完成標準（done when）
- 前三則新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」，只剩那一條視同綠）。
- ledger 記：`git diff --stat` 只含「範圍」列的兩個檔；`handlers.py` 只動第 1 行；AST 比對輸出貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_handlers_header.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 必須在本機磁碟；同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 讀碼一律 `git -C <repo> show origin/v3:<path>`；實作在 worktree 的 `test/handlers-header-comment` 分支，base 為 `origin/v3`。

## 不做
- 不改 `handlers.py` 第 2 行起的任何內容、`JOB_KINDS`、任何 handler 邏輯。
- 不改 `jobs.py`／`store.py` 的說明（那是 `job-kinds-stale-docs` 的範圍）。
- 不改 `docs/`；不需要 migration。

## 裁決
1. **第 1 行要不要寫死「nine」？** 寫死會再過期，但有測試（`test_first_line_names_the_job_kind_count`）把關。**建議：寫 nine，靠測試防漂移。**
2. **和 `job-kinds-stale-docs` 的先後？** 檔案不重疊（本件只動 `handlers.py` 與新測試檔），可並行。**建議：不設先後。**

### developer-agent 確認（2026-10-29）
證據已在 origin/v3 逐行核對屬實；裁決全部照「建議」定案。A 級：只收緊或只改註解，不放寬任何安全網、不改使用者看得到的文字。

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
