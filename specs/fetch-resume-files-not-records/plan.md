---
id: fetch-resume-files-not-records
title: fetch_run_records 的「不當紀錄讀」名單補上續跑會寫的三種檔（params-N.yaml、extra-N.config、head-N.sh）
tier: A
kinds: backend
lane: L19-fetch-denylist
branch: test/fetch-resume-files-not-records
base: origin/v3@bb0e8d6（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 清理掃描（A 級：只讓站台代理少讀幾個本來就不該讀的檔，合法輸入沒有任何使用者看得到的行為變化）
---

# fetch-resume-files-not-records

> 本檔由 developer-agent 的 subagent 寫（2026-10-29），只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
站台代理的 `fetch_run_records` 只准讀 Nextflow 自己的紀錄（日誌、history、日誌裡點名的 trace 檔），並用 `_NOT_RECORDS` 擋掉平台寫進專屬資料夾的檔（`tower.token`、`params.yaml`…）。續跑（resume）會再寫三種檔進同一個資料夾，卻沒進這份名單。把它們補進去，讓「平台寫的檔一律不當紀錄讀」這個保證完整。對正常使用者沒有可見變化（真正的 trace 檔從不叫這些名字）。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」。
- 程式檔頭的承諾（`fetch.py:1–8`）：「reads back only Nextflow's own logs and trace of one launch folder」、「`tower.token`, `params.yaml` and every other file are never asked for」。
- A 級的前提：只更嚴、合法輸入行為不變；若發現需要改動合法輸入的行為，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_station/fetch.py`（只動 `_NOT_RECORDS` 附近一個新常數，與 `run_fetch` 內約 80 行的那個條件）
- `platform/tests/test_station_cancel.py`（新測試加在 `test_tc035_a_link_a_trace_outside...` 之後、`# ---- a resumed run keeps the folder...` 之前，約 196 行）
- **不准碰**：`launch.py`、`gcb_launch.py`、`aws_launch.py`、`azure_launch.py`、`platform/abf_platform/web*.py`、`cloud_store.py`、k8s／計算環境類型相關檔、任何既有測試的既有斷言。

## 作法
- **證據一（續跑寫哪些檔）**：`platform/abf_station/launch.py:1272–1280`：續跑有變更時寫 `head-%d.sh`、`params-%d.yaml`，有額外設定時再寫 `extra-%d.config`；無變更時只寫 `head-%d.sh`（1271–1272）。`launch.py:1728` 的註解也這樣說。三種都在同一個專屬資料夾；`head-N.sh` 含送出指令，`params-N.yaml` 是使用者參數的完整檔案。
- **證據二（名單沒有它們）**：`platform/abf_station/fetch.py:18` `_NOT_RECORDS = {"tower.token", "params.yaml", "head.sh", "nextflow.config", "samplesheet.csv", "gcb.config", "aws.config", "az" "ure.config"}`——全是首次送出的固定檔名，沒有 `-N` 變體。
- **證據三（為什麼會被讀到）**：`fetch.py:73–78` 從 `.nextflow.log*` 的 `Workflow started -- trace file: (.+)` 取名字；`fetch.py:80` 只擋「不符 `_TRACE`」「在 `_NOT_RECORDS`」「以 `.nextflow` 或 `slurm-` 開頭」。`params-2.yaml`、`extra-2.config`、`head-2.sh` 符合 `_TRACE`（`fetch.py:17`，首字英數、其餘 `[A-Za-z0-9._-]`）、不在名單、不以那兩個前綴開頭，所以日誌若這樣寫，就會被 `_read`（`fetch.py:83`）讀出並以 base64 送回平台。日誌是站台上的檔，不是平台寫的，這道名單就是為這種情況而設。
- **決定**：把「續跑檔」做成**樣式**而不是逐一列舉，新增一個模組層常數（例如 `_RESUME_FILE = re.compile(r"^(head|params|extra)-[0-9]+\.(sh|yaml|config)\Z")`），第 80 行加 `or _RESUME_FILE.match(name)`。`_NOT_RECORDS` 這個集合**保留不改**（三個測試檔以 `in fetch._NOT_RECORDS` 斷言它：`test_aws_launch.py:644`、`test_azure_launch.py:627`、`test_gcb_launch.py:1056`）。拒絕訊息沿用 `fetch.py:81` 現句。
- 不改讀取日誌或 history 的路徑（`_LOG`、`.nextflow/history` 照舊）。

## 失敗先行測試
先寫、在改程式前跑一次，確認紅，紅的輸出貼進 ledger。寫法比照同檔 `test_tc035_a_link_a_trace...`（用 `make_records`、`fetch_job`、`agent_on`、`run_job`、`names`）。
- `test_tc036_a_trace_name_that_is_a_file_the_platform_wrote_for_a_resume_is_refused`（參數化 `params-2.yaml`、`extra-2.config`、`head-2.sh`）：
  - `f = make_records(site)`；再寫該名字的檔（內容 `SECRET_RESUME_VALUE`）；把 `.nextflow.log` 改成含一行 `Workflow started -- trace file: <名字>`。
  - 跑 `fetch_job` → `res["state"] == "done"`；`name not in names(res)`；`"SECRET_RESUME_VALUE" not in str(res)`；`res["result"]["refused"]` 有一項含該名字。
  - **現在會紅**：該名字會出現在 `names(res)`，內容被送回。
- 對照組（必須維持綠）：`trace-1.txt`、`trace-2026-10-29_1.txt`、`params.txt`、`head.log`（像但不符樣式）仍被讀；既有 `test_tc034`、`test_tc035` 不改、保持綠；`test_aws_launch.py:641`、`test_azure_launch.py:624`、`test_gcb_launch.py` 同類斷言保持綠。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」：動閘門要在兩個分支跑同一份測試檔比對）：在 `origin/v3` 與本分支各跑 `test_station_cancel.py`，貼輸出；再用 `trace.txt`、`trace-3.txt` 當 trace 名稱，兩分支結果必須相同。

## 完成標準（done when）
- 新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」，只剩那一條視同綠）。
- ledger 記：`git diff --stat` 只含「範圍」列的檔；`fetch.py` 只動一個常數與一個條件；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_station_cancel.py bash tests/platform_test.sh`（相對於 `platform/`；`ABF_PYTEST_ARGS` 可加 `-k`）。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 必須在本機磁碟；同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；測試還在背景跑時不准交報告。
- 站台程式碼不得出現小寫單字 `azure`（`test_station_static.py:46`）；本次改動不新增這個字。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 讀碼一律 `git -C <repo> show origin/v3:<path>`；實作在 worktree 的 `test/fetch-resume-files-not-records` 分支，base 為 `origin/v3`。

## 不做
- 不動 `_TRACE`、`_LOG`、`LIMIT`、讀取路徑；不動 `_NOT_RECORDS` 的既有成員。
- 不改 `launch.py` 的檔名產生方式、不統一各雲端的檔名常數。
- 不新增使用者可見的錯誤文字、不改文件、不需要 migration（沒有資料結構或資料內容變動）。
- 不處理「日誌可被竄改，所以要不要改成白名單（只認 `trace*`）」——那是設計改動，見裁決 1。

## 裁決
1. **用「補樣式」還是「改白名單」？** 現況是黑名單（擋已知的平台檔），每加一種平台檔就要記得補一次，這次就是漏了。白名單（只認 Nextflow 預設的 `trace-*.txt`）更根本，但使用者可用 `-with-trace` 任意命名 trace 檔，改白名單可能讓合法 trace 讀不到，屬可見行為變化，不是 A 級。**建議：本件只補樣式（A 級）；白名單另開一件交你決定。**
2. **樣式要不要也涵蓋 `slurm-*.out` 以外的其他 head job 輸出？** 目前 `slurm-` 前綴已擋。**建議：不擴大，只補這三種（有 `launch.py:1272–1280` 的出處）。**
3. **測試放既有 `test_station_cancel.py` 還是新檔？** 該檔已有 `make_records` 等現成夾具，fetch 的測試本來就在這裡（TC-034、TC-035）。**建議：放既有檔。**

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
