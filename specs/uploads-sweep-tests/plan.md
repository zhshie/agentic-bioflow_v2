---
id: uploads-sweep-tests
title: uploads_web.sweep（清掉上傳留下的舊暫存夾）完全沒有測試；補上，尤其要釘住「絕不刪別的東西」
tier: A
kinds: backend
lane: L48-upload-sweep-test
branch: test/uploads-sweep-tests
base: origin/v3@82a49e17
source: 2026-10-30 清理掃描（逐模組查 platform/tests 有沒有引用，sweep 零次）
---

# uploads-sweep-tests

> 只有計畫、沒有程式。A 級（只加測試，不改任何程式）→ verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
網頁上傳一次會在使用者的上傳區建一個暫存夾 `.incoming-<批次>`；請求當掉或斷電時它會被留下。`uploads_web.sweep(area)` 負責在下一次上傳開始前把「超過 24 小時」的舊暫存夾清掉。它會**刪檔**，所以最怕的是刪錯東西，但整個 `platform/tests` 沒有任何一支測試呼叫過它。補測試，釘住四件事：舊的被清、新的不動、名字不是 `.incoming-` 開頭的任何東西（使用者已上傳完成的檔案、`.batches` 紀錄）絕不動、上傳區不存在時不報錯。**不改 `uploads_web.py`。**

## 維護者原話（verifier 出題用）
- 沒有可引用的逐字原話（本片來自清理掃描）。
- 本次派工指示（2026-10-30）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- 程式自己的說法（verifier 用它出題，不是原話）：`platform/abf_platform/uploads_web.py:1-7` 模組說明「Any refusal, and any failure, removes the whole folder」；`:55` `sweep` 的說明「Remove the staging folders a request left behind long ago (a crash, a power cut). Best effort.」

## 範圍：檔案（只准改這些）
- 新增 `platform/tests/test_uploads_sweep.py`（新檔，只含純檔案系統測試，用 `tmp_path`）
- **不准碰**：`platform/abf_platform/uploads_web.py` 與其他程式、`platform/tests/test_web_upload.py`（既有，不動）、`web.py`、`mcp_server.py`、`jobs.py`、`build.py`、`launch.py`、`compute_envs.py`、`tests/platform_upgrade_test.sh`、`docs/`。

## 作法
- **證據（origin/v3@82a49e17）**：
  - `uploads_web.py:24` `STALE_SECONDS = 86400`；`:37-38` `incoming_for(area, batch)` ＝ `area/.incoming-<batch>`；`:41-51` `discard(folder)` 只刪資料夾裡的檔案再 `rmdir`，裡面若有子資料夾，`rmdir` 失敗被吞掉、資料夾留著；`:54-68` `sweep(area, now=None, older=STALE_SECONDS)`：`os.listdir(area)` 失敗就直接返回；只處理名字以 `.incoming-` 開頭的項目；用 `now - getmtime(path) > older`（嚴格大於）決定要不要 `discard`。
  - 唯一的呼叫者 `web.py:869`：每次 POST /upload 在讀請求前執行 `uploads_web.sweep(area)`。
  - `platform/tests` 內搜尋 `sweep`，只有無關的 `test_web_wording_sweep.py`；`uploads_web.sweep` 零測試。`test_web_upload.py:421` 與 `:539` 只用 `incoming_for` 與 `receive` 的清理。
  - `sweep` 的第二參數 `now` 可注入，所以不必改檔案時間以外的任何東西：測試用 `os.utime` 把夾子的時間調舊，並傳固定的 `now`，不用 `sleep`。
- **測試案例（新檔，函式名由 executor 定，內容如下）**：
  1. 舊的被清：建 `area/.incoming-<32個a>/` 內含 `1.part`、`2.part`，用 `os.utime` 把夾子調成 `now - 86401`，呼叫 `sweep(area, now=now)`，夾子整個不存在。
  2. 剛好 86400 秒不清（嚴格大於）：同上但調成 `now - 86400`，夾子與裡面的檔案都還在。這條釘住邊界，將來有人改成 `>=` 會紅。
  3. 新的不動：調成 `now - 10`，還在。
  4. **別的東西絕不動**：同一個 `area` 內放 `final.fastq.gz`（模擬已完成上傳的檔）、`.batches/`（內含一個檔）、`incoming-nodot/`（名字沒有開頭的點）、`.incomingX`（沒有連字號），全部用 `os.utime` 調成 `now - 10**7` 秒（極舊），呼叫 `sweep`，它們全都還在、內容不變。這是整片最重要的一條。
  5. 上傳區不存在：`sweep(tmp_path / "nope")` 不丟例外、回傳 `None`。
  6. 特徵化：舊夾子裡有子資料夾時，`sweep` 不丟例外，且（因 `discard` 只刪檔）夾子本身還在、其中的檔案已被刪。executor 必須先在 v3 上親眼確認這個行為再寫斷言；若實際行為不同，回報而不是改斷言去湊。
  7. 一個夾子清失敗不影響下一個：兩個舊夾子，第一個含子資料夾（清不乾淨），第二個正常；呼叫後第二個必須已被清掉。
- **不使用** `time.sleep`、不使用真實時間差；每條測試都用注入的 `now`。

## 失敗先行測試
這片是補缺口，現行程式本身沒壞，所以「紅」要靠突變證明，不可為了變紅去改 `uploads_web.py` 的 repo 內容。
- 先把新測試檔寫好、跑一次，在 v3 上**應全綠**（描述現況）。若有任何一條紅，代表我的讀法錯，停下來回報。
- **突變證明（一次性、貼 ledger，不進 repo）**：在 worktree 暫時做三個改動各跑一次 `py -3 -m pytest platform/tests/test_uploads_sweep.py`，每次都要有對應測試轉紅，跑完立刻 `git checkout -- platform/abf_platform/uploads_web.py` 還原：
  - 把 `if n.startswith(".incoming-"):` 改成 `if True:` → 第 4 條紅（會刪掉別的東西）。
  - 把 `now - os.path.getmtime(path) > older` 改成 `>=` → 第 2 條紅。
  - 把 `if now - ... > older:` 的判斷整行拿掉（一律清）→ 第 3 條紅。
  最終 diff 不得含 `uploads_web.py`。

## 完成標準（done when）
- 新測試檔 7 條全綠；三個突變各自讓指定的那條紅，三段輸出與還原後的綠都貼 ledger。
- `py -3 -m pytest platform/tests/test_uploads_sweep.py platform/tests/test_web_upload.py` 全綠；全套綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含 `platform/tests/test_uploads_sweep.py`（新增）。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。
- 測試只用 `tmp_path` 與 `os.utime`，不連網、不啟動任何程式、不花錢；`uploads_web` 會 import `python_multipart` 與 `starlette`，它們已在專案的測試環境裡（`constraints.txt` 有釘）。Windows 用 `py -3 -m pytest …`，或依專案慣例在 WSL。
- Windows 上 `os.utime` 對資料夾可用；若在 Windows 遇到權限問題改在 WSL 跑，並在 ledger 說明。
- 全套：從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`；超過 10 分鐘一律 `run_in_background`，用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 等；背景還在跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改 `sweep`／`discard` 的任何行為（包含讓 `discard` 能刪子資料夾）。
- 不動 `web.py` 的呼叫方式。
- 不新增依賴、不新增 CLI 旗標、不改 `STALE_SECONDS`。

## 裁決
1. **`sweep` 用資料夾的修改時間判斷「舊」。資料夾時間只在裡面「新增或刪除項目」時才更新，寫入既有檔案不會更新。** 若有一次上傳連續跑超過 24 小時，它的暫存夾理論上會被別的請求清掉。2 GB 上限下實際上不會發生，**建議：不處理，只在 ledger 記一句**；真要處理屬行為變更，另案請維護者裁決。
2. **第 6 條特徵化釘住「子資料夾會讓 `discard` 清不乾淨」這個現況，算不算替缺陷背書？** 暫存夾本來只放 `<n>.part` 檔（`uploads_web.py:2-7`、`:130`），子資料夾不會正常出現；釘住的目的是讓「將來有人改 `discard` 的行為」時會有測試提醒。**建議：保留，並在測試註解寫明這是特徵化、不是期望行為。**
3. **測試放新檔還是併進 `test_web_upload.py`？** 後者需要整套網頁測試的夾具（World、Duo），這幾條不需要，且併進去會增加與其他分支的合併衝突。**建議：新檔。**
4. （2026-10-30 預檢第 5 條）測試用的 `now` 必須是整數值常數（例如 `1_800_000_000`），所有 `os.utime` 的時間也都用整數秒，讓第 2 條的 `>` 與突變 `>=` 的判定精確；不得用 `time.time()` 或浮點數。

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
