---
id: station-queue-dotdot
title: 站台第二道鎖的佇列名稱檢查補上「不准含 ..」，與平台端一致
tier: A
kinds: backend
lane: L25-station-queue
branch: fix/station-queue-dotdot
base: origin/v3@7bc7e15（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 Sonnet 掃描（developer-agent 已在 origin/v3 逐行核對）
---

# station-queue-dotdot

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
平台建立計算環境時，佇列名稱（headQueue 等）含 `..` 會被拒絕；站台代理收到工作後會用 `rules.clean_queue` 自己再判一次（第二道鎖，設計上平台判過的站台都要再判），但站台這道鎖少了 `..` 這條，`"a..b"` 會被放行。補上一個條件，讓兩道鎖拒收同一批名字。正常佇列名（例如 `ct224`、`gp4`）結果不變。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- `platform/abf_station/rules.py` 檔頭：第二道鎖刻意和平台端分開寫、各自判斷（見該檔第 1 行起的說明）。
- A 級的前提：只更嚴、合法輸入行為不變；若發現需要改動合法輸入的行為，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_station/rules.py`（只動 `clean_queue`，第 84–85 行附近的條件，加 `or ".." in value`）
- 測試：`platform/tests/test_launch_bundle.py` 是目前唯一呼叫 `clean_queue` 的測試檔；**新建** `platform/tests/test_station_queue_name.py`（檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，內容見裁決 3）。
- **不准碰**：`compute_envs.py`（平台端已經對）、`fetch.py`、`records.py`、`cloud_store.py`、`launch.py`、`mcp_server.py`、`handlers.py`、`web/`、任何既有測試的既有斷言。

## 作法
- **證據**（origin/v3@7bc7e15）：
  - `platform/abf_station/rules.py:14` `_QUEUE = re.compile(r"^[A-Za-z0-9_.-]+\Z")`；`rules.py:84–85` `def clean_queue(value, label):` / `if not isinstance(value, str) or not _QUEUE.match(value):`——沒有 `..` 檢查。
  - `platform/abf_platform/compute_envs.py:225` `if v is not None and (not isinstance(v, str) or not _QUEUE.match(v) or ".." in v):` → 平台端拒收。
- **決定**：`clean_queue` 的拒收條件加 `or ".." in value`，走既有的 Refusal 與文字。其他一行不動。

## 失敗先行測試
先寫、改程式前跑一次確認紅，紅的輸出貼進 ledger。不連網、不開資料庫。
- `clean_queue("a..b", "headQueue")`、`clean_queue("..", "headQueue")`、`clean_queue("x..", "headQueue")` 都要丟 `Refusal`（用 rules.py 實際的例外類別名）。**現在紅**：回傳原字串。
- 對照組（必須一直綠）：`ct224`、`gp4`、`a.b`、`a_b-c.1` 仍通過並原樣回傳；空字串與非字串仍被拒（同既有行為）。
- 兩道鎖一致性：同一組名字（上面全部）丟給平台端 `compute_envs` 的佇列檢查與站台端 `clean_queue`，「拒／收」結果逐一相同。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑新檔與 `test_launch_bundle.py`，貼輸出。

## 完成標準（done when）
- 新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含 `rules.py` 一行與新測試檔；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_station_queue_name.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不把兩邊規則合成共用常數（兩道鎖刻意各自寫）。
- 不改 `_QUEUE` 的允許字元；不改拒絕訊息。
- 不需要 migration（沒有資料變動）。

## 裁決
1. **要不要順手檢查 rules.py 其他函式是否也和平台端漂移？** 範圍會變大，且 rules.py 可能有其他車道在讀。**定案：本件只補佇列；看到其他漂移寫進 ledger「後續」。**
2. **一致性測試入口（預檢 10-29）**：「平台端的佇列檢查」在 `abf_platform.compute_envs._check_slurm(config)`（compute_envs.py:193），要完整 Slurm 字典。**定案**：平台端呼叫 `_check_slurm(config)`，config 含合法絕對路徑的 `workDir` 與 `headQueue`，其餘鍵依 `_SLURM_CONFIG`，拒收時丟 `CEError`；站台端呼叫 `rules.clean_queue(value, "headQueue")`。
3. **檔頭說明（預檢 10-29）**：test_launch_bundle.py:536 已直接呼叫 `rules.clean_queue("normal\n", "headQueue")`。**定案**：`# Nothing existing:` 寫「既有測試 test_launch_bundle.py 只直接測換行結尾的佇列名；沒有任何測試覆蓋 `..`」。

### developer-agent 確認（2026-10-29）
證據已在 origin/v3@7bc7e15 逐行核對屬實；裁決如上。A 級：只收緊，不放寬任何安全網。

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
