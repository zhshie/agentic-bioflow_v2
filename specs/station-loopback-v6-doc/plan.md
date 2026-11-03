---
id: station-loopback-v6-doc
title: station 的「純 http 只准本機」拒絕訊息與 PLATFORM.md 補上 `::1`，與程式實際行為一致
tier: A
kinds: backend
lane: L29-station-loopback-doc
branch: fix/station-loopback-v6-doc
base: origin/v3@43ab7c6（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 Sonnet 掃描（developer-agent 已於 10-29 12:3x 在 origin/v3 逐行核對屬實）
---

# station-loopback-v6-doc

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
`abf-station` 檢查平台網址時，純 `http://` 只准「這台機器」。程式把 `::1`（IPv6 的本機位址）和 `localhost`、`127.0.0.1` 一起當本機放行，但拒絕訊息和 `docs/PLATFORM.md` 都只說「只有 `localhost` 和 `127.0.0.1`」。使用者照文件以為 `http://[::1]:8788` 會被拒，實際上被放行；被拒時訊息也沒告訴他 `::1` 可用。把訊息與文件改成程式真正的行為。程式的判斷一個字都不動。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- 文件規則本身（`docs/PLATFORM.md:176`）：「Plain `http://` is only for the same machine.」——意圖是「本機才准純 http」，`::1` 就是本機；程式碼其他三處（`abf_platform/cli.py:14`、`oauth.py:57`、`web.py:79`）與 PLATFORM.md:649、:701 也都把 `::1` 當本機。
- A 級的前提：不改任何放行／拒絕的結果；若發現必須動判斷才能一致，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_station/cli.py`：只動 `url_problem`（第 38–45 行）回傳的那串拒絕訊息，把 "only localhost and 127.0.0.1 may use http" 改成 "only localhost, 127.0.0.1 and ::1 may use http"；其餘字元、判斷式、`LOOPBACK`（第 18 行）一字不改。
- `docs/PLATFORM.md`：只動第 176 行那一句（"except `localhost` and `127.0.0.1`" 補成 "except `localhost`, `127.0.0.1` and `::1`"）；不動檔案其他行。
- 測試：加進既有 `platform/tests/test_station_docs.py`（檔頭已有 `# Nothing existing:` 行，不必新增）。
- **不准碰**：`abf_station/agent.py`、`abf_station/launch.py`、`abf_station/rules.py`、`records.py`、`handlers.py`、`abf_platform/common.py`（`public_url` 的放行範圍另案，**不准放寬**）、`specs/`、任何既有測試的既有斷言。

## 作法
- **證據**（origin/v3@43ab7c6）：
  - `abf_station/cli.py:18` `LOOPBACK = ("127.0.0.1", "localhost", "::1")`
  - `abf_station/cli.py:42` `if parts.scheme == "http" and parts.hostname not in LOOPBACK:`——`urlparse("http://[::1]:8788").hostname` 是 `"::1"`，在 `LOOPBACK` 內，放行。
  - `abf_station/cli.py:43–44` 訊息 `"... Use HTTPS; only localhost and 127.0.0.1 may use http."`
  - `docs/PLATFORM.md:176` "Use HTTPS for every platform address except `localhost` and `127.0.0.1`: the agent refuses a plain `http://` address anywhere else"
  - 對照：`abf_station/agent.py:21` 同一個 `LOOPBACK` 並對它略過 proxy；`abf_platform/cli.py:14`、`oauth.py:57`、`web.py:79`、`http_auth.py:24` 都含 `::1`。
- **決定**：程式行為是對的（`::1` 確實是本機，其他模組一致），改的是訊息與文件，不是判斷。

## 失敗先行測試
先寫、改前跑一次確認紅，紅的輸出貼進 ledger。
- `from abf_station import cli`：`cli.url_problem("http://example.com:8788")` 回傳的字串要含 `"::1"`。**現在紅**。
- `PLATFORM.md` 第 176 行那一段（用 `flat(read("PLATFORM.md"))` 找 "Plain `http://` is only for the same machine" 起的那一句）要含 `::1`。**現在紅**。
- 一致性：對 `("http://localhost:1", "http://127.0.0.1:1", "http://[::1]:1")` 每個 `cli.url_problem(u) is None`，對 `("http://example.com", "http://192.168.1.5:8788", "http://[::2]:1")` 每個回傳非 None。**現在綠，必須一直綠**（鎖住判斷不被動到）。
- 對照組：`url_problem("https://example.com")` 為 None；`url_problem("ftp://x")` 與 `url_problem("http://")` 仍回傳非 None，且字串與改前相同（這兩條的訊息不在改動範圍）。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `test_station_docs.py`，貼輸出。

## 完成標準（done when）
- 兩條新測試改前紅、改後綠；一致性與對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含「範圍」列的檔；`cli.py` 只動一個字串；`PLATFORM.md` 只動一行；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_station_docs.py bash tests/platform_test.sh`（相對於 `platform/`；`ABF_PYTEST_ARGS` 可加 `-k`）。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改 `url_problem` 的判斷、不改 `LOOPBACK`、不改其他兩個拒絕訊息。
- 不動 `abf_platform/common.py:198` `public_url`（它只放行 `127.0.0.1`、`localhost`，不含 `::1`；要一致得放寬一個安全檢查，另案、C 級決定，不在本件）。
- 不改 `specs/007-station-agent/plan.md`（歷史規格，同樣只寫兩個，不改）。
- 不需要 migration（沒有資料結構或資料內容變動）。

## 裁決
1. **改程式還是改文件？** 程式把 `::1` 當本機放行，與其他模組一致；改成拒絕 `::1` 會改行為。**定案：改訊息與文件，不動判斷。**
2. **測訊息文字的哪一段？** 只斷言含 `"::1"`，不鎖整句，讓之後改措辭不會弄壞測試。**定案：`"::1" in msg`。**
3. **PLATFORM.md 測試怎麼找那一句？** 先 `flat()` 壓掉換行，再取 "Plain `http://` is only for the same machine" 之後到第一個句點（". "）為止。**定案：用這個切法，找不到起點就斷言失敗。**
4. **`public_url` 的 `::1`？** 放寬是放寬安全檢查。**定案：不做，列「不做」。**
5. **手動 TC**：只有 `git diff origin/v3...HEAD` 範圍檢查，ledger 貼 diff 統計即可。

### developer-agent 確認（2026-10-29）
證據已在 origin/v3@43ab7c6 核對屬實（cli.py LOOPBACK 含 ::1、拒絕訊息與 PLATFORM.md:176 只列 localhost 與 127.0.0.1）；裁決如上。A 級：不改任何放行／拒絕結果。

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
