---
id: env-vars-documented
title: 程式讀取的每個 ABF_* 環境變數都要寫進 docs/；補上漏掉的六個，並加一支測試防再漏
tier: A
kinds: backend
lane: L41-env-docs
branch: docs/env-vars-documented
base: origin/v3（行號取自 origin/v3@0259726；executor 開工前用 `git show origin/v3:<檔>` 重查）。與目前忙碌檔無交集：只動 docs/PLATFORM.md、docs/OPERATIONS.md 與一支新測試；只**讀** jobs.py／put_upload.py／gcb_launch.py，不改。
source: developer-agent 清理掃描 2026-10-29（待 developer-agent 確認）。證據＝比對 `platform/abf_platform|abf_station|abf_launch/*.py` 讀到的 ABF_* 名字與 `docs/*.md` 提到的名字，差集共七個。
---

# env-vars-documented

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。**不改任何產品程式碼**，只補文件與加一支讀文字檔的測試。

## 目標
程式會讀 27 個 `ABF_*` 環境變數，其中六個（加一個內部殼層變數）在 `docs/` 裡完全找不到。最嚴重的是 `ABF_STATION_UPLOADS`：缺了它，網頁上傳（`/upload`）排的 `put_upload` 工作會被代理拒絕，錯誤訊息叫使用者「請管理者設定」，但管理者翻遍 `docs/` 找不到要設什麼、設成哪個資料夾。本任務把六個變數補進文件，並加一支測試：往後程式新增 `ABF_*` 變數卻沒寫文件，測試就紅。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- `docs/PLATFORM.md:871` 現行說法（要保持成立）：「Settings that only the tests change: `ABF_PLATFORM_DEADLINE_PIPELINE_FILES` (default 90) …」——「只有測試會改」的設定，文件裡本來就有寫出來；本任務是補齊，不是新增政策。
- `platform/abf_station/put_upload.py:84` 程式自己的話：「這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS），請管理者設定」——文件要讓管理者做得到這句話。
- A 級的前提：若發現要改產品行為才能讓文件成立，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `docs/PLATFORM.md`（「Online, offline, and the numbers」表，第 193–200 行；與第 871 行段落）
- `docs/OPERATIONS.md`（第 234 行「The web page /upload」那一點附近，加一句；不動其他段）
- `platform/tests/test_env_vars_documented.py`（**新檔**；檔頭第一行照本 repo 慣例寫 `# Nothing existing: …` 說明搜過沒有現成測試，見 `platform/tests/test_cloud_upload_docs.py:1`）
- **不准碰**：`platform/abf_platform/jobs.py`、`platform/abf_station/*.py`（任何產品程式碼）、`web.py`、`web_board.py`、`web_settings.py`、`compute_envs.py`、`cli.py`、`launch.py`、`deploy/`、`tests/*.sh`、既有測試的既有斷言。

## 作法
- **證據**（origin/v3@0259726）：
  - 差集（程式有、`docs/*.md` 沒有）：`ABF_PLATFORM_DEADLINE_CLEAN`、`ABF_PLATFORM_DEADLINE_PUT_UPLOAD`、`ABF_PLATFORM_DEADLINE_READ_TASK_LOG`、`ABF_STATION_UPLOADS`、`ABF_STATION_PUT_TIMEOUT`、`ABF_STATION_GCB_SETTLE_SECONDS`、`ABF_FORWARD_PORT`。
  - 前三個：`platform/abf_platform/jobs.py:29-30` 的 `DEADLINE_SECONDS`（`read_task_log` 60、`clean_work` 600、`put_upload` 3600）與 `jobs.py:31-39` 的 `_DEADLINE_ENV`；讀取在 `jobs.py:74`。文件現況：`docs/PLATFORM.md:198-199` 只列 `preflight`、`list_site_files` 兩列；`PLATFORM.md:871` 補了 `PIPELINE_FILES`、`LAUNCH`、`CANCEL`、`FETCH`，其餘三個漏掉。
  - `ABF_STATION_UPLOADS`：`platform/abf_station/put_upload.py:22`（常數）、`:81-84`（沒設、不是絕對路徑、或不是資料夾 → 拒絕）、`:5-6`（檔案必須在 `<ABF_STATION_UPLOADS>/<owner>/` 裡）。平台端暫存位置＝`store.uploads_root`（`platform/abf_platform/store.py:309-315`：`ABF_PLATFORM_UPLOADS`，否則 `platform.db` 旁的 `uploads`）；`actions/uploads.py:252` 把這個資料夾交給 `enqueue_put_upload`。`docs/OPERATIONS.md:95` 已寫 `ABF_PLATFORM_UPLOADS`，`:234` 寫「Each file waits on the platform host until the agent has copied it」，但沒說代理從哪個資料夾讀。
  - `ABF_STATION_PUT_TIMEOUT`：`put_upload.py:23`（「for tests, else TIMEOUT_SECONDS」）、`:42-48`、預設 3600（`:24`）。
  - `ABF_STATION_GCB_SETTLE_SECONDS`：`platform/abf_station/gcb_launch.py:28-29`（預設 5.0）、`:91-95`、用於 `:209`（head 程序在這幾秒內就消失，視為沒起來）。
  - `ABF_FORWARD_PORT`：只是 `platform/abf_station/launch.py:490-493` 產生的 head 腳本裡的殼層變數，不是設定。**不寫進文件**，測試的白名單收它。
- **決定（文件）**：
  - `PLATFORM.md` 表：在第 199 行後補三列 `Job deadline, read_task_log | 60 seconds | ABF_PLATFORM_DEADLINE_READ_TASK_LOG`、`… clean_work | 600 …`、`… put_upload | 3600 …`（同樣欄位格式）。`PLATFORM.md:871` 段落補 `ABF_STATION_PUT_TIMEOUT`（秒，預設 3600，覆寫 put_upload 的複製時限）與 `ABF_STATION_GCB_SETTLE_SECONDS`（秒，預設 5，head 程序這幾秒內消失就當作沒起來），語氣沿用「Settings that only the tests change」。
  - `OPERATIONS.md:234`：緊接那一點加一句——跑 `abf-station run` 的代理要設 `ABF_STATION_UPLOADS`，值是與平台 `uploads_root` 同一個資料夾的絕對路徑（預設 `platform.db` 旁的 `uploads`，或 `ABF_PLATFORM_UPLOADS`）；沒設時，上傳會被代理拒絕，訊息為「這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS）」。**「必須同一個資料夾」是從程式推得（平台把檔案放 `uploads_root/<user>/`、代理讀 `ABF_STATION_UPLOADS/<owner>/`），executor 要在 `test_byte_channel_b.py` 找到兩邊對得上的證據再寫；找不到就改寫成「指向平台暫存上傳檔的資料夾」並在 ledger 說明。**
- **決定（測試）**：新檔 `platform/tests/test_env_vars_documented.py`，不啟動任何服務、不連網：
  - 掃 `platform/abf_platform/**/*.py`、`platform/abf_station/**/*.py`、`platform/abf_launch/**/*.py`，用 `ABF_[A-Z0-9_]+`（完整名字，結尾不得是底線）取出名字。
  - 讀 `docs/*.md` 全文；每個名字必須整串出現其中，白名單只有 `ABF_FORWARD_PORT`（理由寫在白名單旁的註解：殼層變數，非設定）。
  - 白名單用 `assert` 形式限定「只准這一個」；不得用萬用字元。路徑用 `from helpers import PLATFORM_DIR, REPO_ROOT`（`platform/tests/helpers.py:19-20`）。

## 失敗先行測試
加進新檔，先寫、改文件前跑一次確認紅，紅的輸出貼進 ledger。
- `test_every_abf_variable_the_code_reads_is_named_in_docs`：改前紅（失敗訊息列出六個名字）；改後綠。
- `test_the_allowlist_has_exactly_one_entry`：白名單集合 `== {"ABF_FORWARD_PORT"}`（防日後偷塞）。現在綠，必須一直綠。
- `test_the_scan_finds_the_names_it_should`：掃描結果至少包含 `ABF_PLATFORM_DEADLINE_PREFLIGHT`、`ABF_STATION_UPLOADS`、`ABF_PLATFORM_DB`（防正則寫壞而空過）。現在綠。
- `test_deadline_table_covers_every_job_kind`：`jobs.DEADLINE_SECONDS` 的每個 kind 在 `docs/PLATFORM.md` 中，其 `jobs._DEADLINE_ENV[kind]` 名字與 `jobs.DEADLINE_SECONDS[kind]` 的秒數出現在**同一行**（表格列或第 871 行段落皆可，同一行即可）。改前紅（`read_task_log`、`clean_work`、`put_upload`）；改後綠。這條防「名字有了、數字寫錯」。
- `test_station_uploads_is_explained_where_the_web_upload_is`：`docs/OPERATIONS.md` 中含 `ABF_STATION_UPLOADS` 的那一行，同一行還要含 `ABF_PLATFORM_UPLOADS` 或 `uploads_root` 其中之一，且含 `abf-station`。改前紅；改後綠。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `test_env_vars_documented.py`，貼輸出（v3 上六紅或更多、本分支全綠）。

## 完成標準（done when）
- 新測試改前紅、改後綠；既有 `platform/tests/test_cloud_upload_docs.py`、`test_job_kinds_docs.py`、`test_station_docs.py`、`test_mcp_server_doc.py`、`test_onboarding_doc.py` 全綠（它們讀同幾份文件）。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含「範圍」列的三個檔；`docs/` 的差異只有新增行（沒有刪改既有句子，除了第 871 行段落尾端的補寫）；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_env_vars_documented.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 平台測試分片檔（`platform_shard_*_test.sh` 等）依檔名列出測試；新檔放進 `platform/tests/` 後，確認 `test_platform_parts.py` 仍綠（它檢查每個測試檔都落在某一片）。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 其他進行中的任務也會改 `docs/PLATFORM.md`（例如 k8s 系列）：只在上述行附近**新增**，合併時衝突以保留雙方新增為準。

## 不做
- 不改任何 `ABF_*` 的名字、預設值或讀取邏輯；不把「只有測試會改」的變數升級成正式設定。
- 不掃 `scripts/`（`ABF_CACHE_DIR`、`ABF_PIPELINE_FETCHER` 屬 `methods_text.py`，另一套工具；若 developer-agent 要納入，另開一件）。
- 不掃 `hooks/` 的 `_ABF_ROOT` 之類（底線開頭的 shell 內部變數）。
- 不補 `deploy/env.example`（沒有這七個變數的位置）。

## 裁決
1. **`ABF_STATION_PUT_TIMEOUT`、`ABF_STATION_GCB_SETTLE_SECONDS` 要不要當「正式設定」寫？** 程式註解自稱「for tests」。**建議：寫在 `PLATFORM.md:871`「只有測試會改」那一段，不寫進 OPERATIONS。** 待 developer-agent 確認。
2. **`ABF_FORWARD_PORT` 白名單。** 它是 head 腳本內的殼層變數。**建議：白名單，不寫文件。** 待 developer-agent 確認。
3. **掃描範圍只含 `platform/`。** `scripts/methods_text.py` 的兩個變數（`ABF_CACHE_DIR`、`ABF_PIPELINE_FETCHER`）不在本件。**建議：維持本件範圍，需要再另開。** 待 developer-agent 確認。
4. **OPERATIONS.md 那句「必須同一個資料夾」的措辭**：見「作法」，以 executor 找到的測試證據為準。**建議：照作法的保守備案。** 待 developer-agent 確認。

### developer-agent 確認（2026-10-29 21:1x）
四點全部照建議定案：兩個測試用逾時寫進 PLATFORM.md 既有的「只有測試會改」那段；`ABF_FORWARD_PORT` 是唯一的允許例外；`scripts/` 不納入；`ABF_STATION_UPLOADS` 那句若找不到測試佐證「必須與平台上傳資料夾相同」，就改用較弱的「平台暫存上傳檔的資料夾」說法。

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
