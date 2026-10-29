---
id: records-not-records-cloud-configs
title: 平台端 records.name_ok 的「不當紀錄收」名單補上三個雲端設定檔（gcb.config、aws.config、Azure 設定檔）
tier: A
kinds: backend
lane: L21-records-denylist
branch: test/records-not-records-cloud-configs
base: origin/v3@bb0e8d6（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 清理掃描（A 級：只讓平台少收幾個本來就不是 Nextflow 紀錄的檔，合法輸入沒有任何使用者看得到的行為變化）
---

# records-not-records-cloud-configs

> 本檔由 developer-agent 的 subagent 寫（2026-10-29），只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
平台收下站台代理送回的「Nextflow 紀錄」前，會再用 `records.name_ok` 檢查檔名（第二道鎖，與站台端 `fetch.py` 各自獨立，一個出錯不會同時開兩扇門）。站台端的拒收名單有八個名字，平台端只有五個：少了三個雲端送出時寫進同一個資料夾的設定檔。把它們補齊，讓兩道鎖拒收同一批平台檔。對正常使用者沒有可見變化（真正的 trace 檔從不叫這些名字）。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- 程式檔頭的承諾（`records.py:5`）：「Only the names Nextflow writes for these records are accepted.」
- A 級的前提：只更嚴、合法輸入行為不變；若發現需要改動合法輸入的行為，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/records.py`（只動第 20 行 `_NOT_RECORDS` 一行）
- `platform/tests/test_records_names.py`（**新檔**；檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，說明為何不加進既有檔，例如「現有測試只檢查換行結尾的名字（test_launch_bundle.py:531），沒有檢查平台寫的檔名是否被擋」）
- **不准碰**：`platform/abf_station/fetch.py`（另有車道在改）、`launch.py`、各 `*_launch.py`、`web*.py`、`cloud_store.py`、k8s／計算環境類型相關檔、任何既有測試的既有斷言。

## 作法
- **證據一（站台端名單有八個）**：`platform/abf_station/fetch.py:18` `_NOT_RECORDS = {"tower.token", "params.yaml", "head.sh", "nextflow.config", "samplesheet.csv", "gcb.config", "aws.config", "az" "ure.config"}`。
- **證據二（平台端名單只有五個）**：`platform/abf_platform/records.py:20` `_NOT_RECORDS = {"tower.token", "params.yaml", "head.sh", "nextflow.config", "samplesheet.csv"}`。
- **證據三（那三個檔真的寫進同一個資料夾）**：`platform/abf_station/launch.py:566` `GCB_FILE_NAMES` 含 `gcb.config`（774 行寫入）；`launch.py:786` `AWS_FILE_NAMES` 含 `aws.config`（946 行寫入）；`launch.py:958` `AZURE_CONFIG_NAME = "az" "ure.config"`。
- **證據四（現在會被收下）**：`records.py:29` `name_ok` 對這三個名字：符合 `_TRACE`（第 19 行，首字英數、其餘 `[A-Za-z0-9._-]`）、不在 `_NOT_RECORDS`、不以 `slurm-` 或 `.nextflow` 開頭，所以回傳 True；`store_files`（第 43 行起）就會寫到 `records/<run>/` 並讓 `abf-platform rebuild` 當作一份紀錄讀。這些設定檔含 bucket、專案、資源群組等部署資訊。站台端雖已擋，平台端這道鎖的設計目的就是「站台出錯時仍擋得住」。
- **決定**：在第 20 行集合內加三個名字。Azure 那個名字沿用站台的兩段寫法 `"az" "ure.config"`（站台套件有掃描禁止裸的小寫單字；平台端是否有同類掃描由 executor 在跑 `test_scope`／`test_station_static` 時確認，兩段寫法在兩邊都安全）。其他一行不動。
- 不新增拒絕訊息；被擋的名字走既有的 `records.py:44`「not a record of Nextflow」。

## 失敗先行測試
先寫、在改程式前跑一次，確認紅，紅的輸出貼進 ledger。新檔 `platform/tests/test_records_names.py`，不連網、不開資料庫；`from abf_platform import records` 即可。
- `test_the_platform_refuses_every_file_the_launch_writes_that_is_not_a_record`（參數化三個名字 `gcb.config`、`aws.config`、`"az" "ure.config"`）：`records.name_ok(name) is False`。**現在紅**：回傳 True。
- `test_store_files_does_not_write_them`：對每個名字呼叫 `records.store_files(tmp_path, "run-one", [{"name": name, "data": base64 of b"SECRET_CONFIG"}])`；結果 `files == []`、`refused` 有一項含該名字、`tmp_path/"run-one"` 底下沒有該檔。**現在紅**：檔被寫入。
- 對照組（必須一直綠）：`.nextflow.log`、`.nextflow.log.3`、`.nextflow/history`、`trace-1.txt`、`trace-2026-10-29_1.txt`、`params.txt`、`head.log`、`aws.config.txt` 仍然 `name_ok` 為 True；原有五個名字仍為 False；既有 `test_launch_bundle.py::test_security_f4_the_other_validators_too` 不改、保持綠。
- 兩邊一致性（對照組）：`records._NOT_RECORDS <= fetch._NOT_RECORDS`（平台端每一個都在站台端；站台端可以更多，如果另一車道已加 `-N` 變體樣式，不屬這個集合）。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」：動閘門要在兩個分支跑同一份測試檔比對）：在 `origin/v3` 與本分支各跑 `test_launch_bundle.py` 與新檔，貼輸出；再用 `trace.txt`、`trace-3.txt`、`.nextflow.log.12` 逐一 `name_ok`，兩分支結果必須相同。

## 完成標準（done when）
- 兩則新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」，只剩那一條視同綠）。
- ledger 記：`git diff --stat` 只含「範圍」列的兩個檔；`records.py` 只動一行；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_records_names.py bash tests/platform_test.sh`（相對於 `platform/`；`ABF_PYTEST_ARGS` 可加 `-k`）。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 必須在本機磁碟；同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 讀碼一律 `git -C <repo> show origin/v3:<path>`；實作在 worktree 的 `test/records-not-records-cloud-configs` 分支，base 為 `origin/v3`。

## 不做
- 不動 `_TRACE`、`_LOG`、`MAX_BYTES`、`store_files` 的流程；不動 `_NOT_RECORDS` 既有成員。
- 不碰 `fetch.py`；續跑會寫的 `head-N.sh`、`params-N.yaml`、`extra-N.config`（`launch.py:1272–1280`）屬站台端另一件，平台端要不要同步擋見裁決 1。
- 不新增使用者可見的錯誤文字、不改文件、不需要 migration（沒有資料結構或資料內容變動；已存在 `records/` 底下的舊檔不刪不改）。

## 裁決
1. **平台端要不要也擋續跑檔（`head-N.sh` 等）？** 站台端那件用「樣式」處理；平台端也補會更完整，但做法（樣式還是逐一列名）要等站台端那件定案才能對齊，否則兩道鎖的規則不同。**建議：本件只補三個名字；續跑檔在站台端那件合併後另開一件對齊。**
2. **要不要把兩份名單合成一份共用常數？** 這會讓「兩道鎖各自獨立」的設計意義消失（見 `platform/abf_station/rules.py:1`「a second lock on purpose, written separately from the platform's」），也要動 `fetch.py`。**建議：不合併，只用「平台端是站台端的子集」這則測試防再漂移。**

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
