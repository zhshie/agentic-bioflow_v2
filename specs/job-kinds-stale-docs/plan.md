---
id: job-kinds-stale-docs
title: 把「工作種類有幾種、哪幾種會寫」的過期說明改對（jobs.py 開頭說明、store.py 註解），並加一則防再過期的測試
tier: A
kinds: backend
lane: L20-job-kinds-docs
branch: test/job-kinds-stale-docs
base: origin/v3@bb0e8d6（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 清理掃描（A 級：只改註解與說明文字、加一則測試，不改任何執行邏輯）
---

# job-kinds-stale-docs

> 本檔由 developer-agent 的 subagent 寫（2026-10-29），只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。純文字＋測試，不動邏輯。

## 目標
`jobs.py` 與 `store.py` 的說明文字還停在「八種／兩種會寫」，程式實際是九種、三種會寫（`clean_work` 加進來時沒回頭改）。把說明改成和程式一致，並加一則測試，之後再加新種類但忘了改說明就會紅。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「過期文件與程式矛盾」要附 `file:line` 證據，且要能描述一則現在會紅的測試。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/jobs.py`（只改註解與模組說明字串：第 4–11 行、第 64 行、第 415 行；**不動任何可執行行**）
- `platform/abf_platform/store.py`（只改第 176–177 行的註解）
- `platform/tests/test_job_kinds_docs.py`（**新檔**；檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，說明為何不加進既有檔，例如「現有測試檢查種類清單與順序，沒有檢查說明文字是否跟得上」）
- **不准碰**：`web*.py`、`cloud_store.py`、`launch.py`、k8s／計算環境類型相關檔、任何既有測試的既有斷言、`docs/PLATFORM.md`。

## 作法
### 證據（說明 vs 程式）
- 程式事實：`jobs.py:45` `KINDS = tuple(DEADLINE_SECONDS)`，`jobs.py:29–30` 有九個鍵（含 `clean_work`）；`store.py:242` 的 CHECK 列九種；`jobs.py:65` `CONFIRMED` 有三項（`launch_nextflow`、`cancel_run`、`clean_work`）；`store.py:254` 的 CHECK 對這三種強制要有 `confirmation_id`。
- 過期說明一：`jobs.py:4–7` 說「Nine kinds exist … `preflight`, `list_site_files`, `fetch_run_records`, `read_task_log` and `pipeline_files` only read; `put_upload` …; `launch_nextflow` and `cancel_run` write on the site, so a job of those two kinds can only be queued with a confirmation」——數字九是對的，但列出的只有八種，**漏了 `clean_work`**，且「those two kinds」應為三種（`jobs.py:65`）。
- 過期說明二：`jobs.py:64` 註解「the two kinds that write on the site」，下一行 `CONFIRMED` 有三項。
- 過期說明三：`jobs.py:415` `_check_confirmation` 說明「The one guard of the two kinds that write」，實際三種（第 416 行 `want = CONFIRMED[kind]`）。
- 過期說明四：`store.py:176–177`「The CHECK constraints let exactly eight job kinds in … the eighth, put_upload, writes to the user's own cloud prefix and needs none」——第 242 行已是九種（第九種 `pipeline_files` 只讀、不需確認）；「the three that write」那半句本身是對的。
- 對照：`handlers.py:19` 的 `JOB_KINDS` 也是九種，`handlers.py:2–7` 的說明已把九種都講到——這份是對的，改寫時照它的措辭。

### 決定
- 只改字：九種逐一列名；會寫的三種寫成 `launch_nextflow`、`cancel_run`、`clean_work`；`put_upload` 寫使用者自己的雲端前綴但免確認；`pipeline_files` 只讀。數字（nine）不變。
- 第 1 行的檔首註解「nine job kinds」本來就對，不動。
- 不改任何程式行；用 `git diff` 確認 `jobs.py` 與 `store.py` 的差異只落在 `#` 註解行與 `"""` 說明字串內。

## 失敗先行測試
新檔 `platform/tests/test_job_kinds_docs.py`，先寫、改字前跑一次確認紅，紅的輸出貼進 ledger。測試只讀原始碼文字與常數，不連網、不開資料庫。
- `test_jobs_module_doc_names_every_job_kind`：對 `jobs.KINDS` 每一個種類，`"`%s`" % kind in jobs.__doc__`。**現在紅**：`clean_work` 不在開頭說明裡（`jobs.py:4–11`）。
- `test_jobs_module_doc_counts_the_kinds_that_need_a_confirmation`：`len(jobs.CONFIRMED) == 3`（先釘住事實），且 `jobs.__doc__` 不含 `those two kinds`。**現在紅**：說明仍寫 two。
- `test_store_comment_counts_the_job_kinds`：讀 `store.py` 原始碼文字，找 `exactly (\w+) job kinds`，把英文數字詞轉成整數，必須等於 `len(jobs.KINDS)`（9）。**現在紅**：寫的是 eight。
- `test_store_check_constraint_lists_the_same_kinds_as_jobs`（對照組，必須一直綠）：從 `store.STATE_SCHEMA` 取 `jobs` 表的 `kind IN (...)` 括號內名稱，集合等於 `set(jobs.KINDS)`。
- `test_handlers_and_jobs_agree_on_the_kinds`（對照組，必須一直綠）：`set(handlers.JOB_KINDS) == set(jobs.KINDS)`（import 寫法照 `test_byte_channel_b.py:183` 附近）。
- 手動檢查（記 ledger，verifier 自己重跑）：`git diff -U0 origin/v3 -- platform/abf_platform/jobs.py platform/abf_platform/store.py`，逐行確認沒有「不是 `#` 開頭也不在 `"""` 內」的變更行。

## 完成標準（done when）
- 前三則新測試改前紅、改後綠；兩則對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」，只剩那一條視同綠）。
- ledger 記：`git diff --stat` 只含「範圍」列的三個檔；`jobs.py`、`store.py` 沒有可執行行被改（兩分支各 `ast.parse` 後去掉 docstring 的 AST 比對相等，輸出貼上）。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_job_kinds_docs.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 必須在本機磁碟；同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；測試還在背景跑時不准交報告。
- 套件掃描測試：`jobs.py` 的原始碼會被 `test_scope`（TC-061）掃禁字（見 `jobs.py:41` 註解）；新增的說明文字不得含那個禁字的完整單字。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 讀碼一律 `git -C <repo> show origin/v3:<path>`；實作在 worktree 的 `test/job-kinds-stale-docs` 分支，base 為 `origin/v3`。

## 不做
- 不改任何可執行行、常數、CHECK 約束、種類清單或順序。
- 不改 `abf_station/handlers.py:1` 的過期註解「two built-in read-only handlers」（不在範圍，見裁決 2）。
- 不改 `docs/PLATFORM.md`；不需要 migration。

## 裁決
1. **要不要加「說明必須跟得上程式」的測試，還是只改字？** 只改字的話，下次加第十種又會漏。測試是讀原始碼文字的字串比對，略脆（改措辭可能誤紅）。**建議：加，但只釘「有沒有列到每個種類名」「數字等於 `len(KINDS)`」兩個鬆條件，不釘整句。**
2. **範圍要不要順手含 `abf_station/handlers.py:1` 的「two built-in read-only handlers」？** 那句同樣過期（現在是九種），但屬站台側檔案，且只有一行註解。**建議：不含，本件只在平台側兩個檔；想一次清完就另開一件並把 `handlers.py` 加進範圍。**
3. **新測試放新檔還是既有檔？** 既有的種類測試（`test_byte_channel_a.py:231`、`test_byte_channel_b.py:183`）檢查的是清單與順序，塞說明文字檢查會讓那兩檔離題。**建議：新檔 `test_job_kinds_docs.py`（需 `# Nothing existing:` 檔頭）。**

### developer-agent 確認（2026-10-29）
裁決全部照「建議」定案；base 為 origin/v3（bb0e8d6 或更新），行號以內容為準。

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
