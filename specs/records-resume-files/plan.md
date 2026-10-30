---
id: records-resume-files
title: 平台端 records.name_ok 也拒收續跑檔（head-N.sh、params-N.yaml、extra-N.config），與站台端一致
tier: A
kinds: backend
lane: L26-records-resume
branch: fix/records-resume-files
base: origin/v3（#266 已於 10-29 03:30 UTC 合併，可派；#266 改的是同一檔 records.py 第 20 行。行號取自 origin/v3@7bc7e15，executor 開工前用 `git show origin/v3:<檔>` 重查）
source: PR #265 與 #266 的 verifier「需要人看的事」＋ records-not-records-cloud-configs 計畫裁決 1（續跑檔待站台端合併後另開一件對齊）
---

# records-resume-files

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
續跑（resume）時，launch 會在 run 資料夾寫 `head-N.sh`、`params-N.yaml`、`extra-N.config`，可能含密鑰。站台端 `fetch.py` 已在 #265 拒收它們；平台端收紀錄時的第二道鎖 `records.name_ok` 還會收下（它們符合 `_TRACE`、不在 `_NOT_RECORDS`）。補一條同樣的樣式，讓兩道鎖拒收同一批檔。真正的 Nextflow 紀錄（trace、.nextflow.log、params.txt、head.log）結果不變。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- `records.py:5` 檔頭：「Only the names Nextflow writes for these records are accepted.」
- A 級的前提：只更嚴、合法輸入行為不變；若發現需要改動合法輸入的行為，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/records.py`（加一行 `_RESUME_FILE` 常數，`name_ok` 最後的 return 加 `and not _RESUME_FILE.match(name)`）
- `platform/tests/test_records_names.py`（#266 新建的檔；只**新增**測試函式，不改既有斷言——唯一例外：若既有的「名單剛好八個」測試只鎖 `_NOT_RECORDS` 集合，它不受影響、不准改）
- **不准碰**：`platform/abf_station/fetch.py`（已正確）、`launch.py`、`web/`、`cloud_store.py`、`rules.py`、`compose.py`、`actions/`、任何既有測試的既有斷言。

## 作法
- **證據**（origin/v3@7bc7e15）：
  - 站台端 `platform/abf_station/fetch.py:19` `_RESUME_FILE = re.compile(r"^(head|params|extra)-[0-9]+\.(sh|yaml|config)\Z")`，於 `fetch.py:81` 拒收。
  - 平台端 `platform/abf_platform/records.py` 的 `name_ok`（約第 23–29 行）：`return bool(_TRACE.match(name)) and name not in _NOT_RECORDS and not name.startswith(("slurm-", ".nextflow"))`——沒有續跑檔樣式。
- **決定**：平台端另寫一份**相同樣式**的常數（不 import 站台端：兩道鎖刻意各自寫，見 `platform/abf_station/rules.py:1` 的說明）；不新增拒絕訊息，走既有「not a record of Nextflow」。

## 失敗先行測試
加進 `platform/tests/test_records_names.py`，先寫、改程式前跑一次確認紅，紅的輸出貼進 ledger。
- `head-1.sh`、`params-2.yaml`、`extra-10.config`、`head-123.sh` 的 `records.name_ok` 為 False。**現在紅**。
- `store_files(tmp_path, "run-one", [{"name": n, "data": base64(b"SECRET_RESUME")}])` 對上面每個名字：`files == []`、`refused` 有一項、硬碟上沒有該檔、回傳裡沒有 `SECRET_RESUME`。**現在紅**。
- 對照組（必須一直綠）：`head.log`、`params.txt`、`trace-1.txt`、`.nextflow.log.2`、`head-1.sh.txt`、`params-x.yaml`、`extra-1.json` 的 `name_ok` 仍為 True（後三個證明樣式沒有過寬）；原有被擋的八個名字仍為 False；#266 的既有測試全綠。
- 兩道鎖一致性：用一組名字（上面全部）分別丟平台端 `records._RESUME_FILE` 與站台端 `fetch._RESUME_FILE`，比對結果逐一相同（只比樣式，不 import 站台端到正式程式碼）。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `test_records_names.py` 與 `test_launch_bundle.py`，貼輸出。

## 完成標準（done when）
- 新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含「範圍」列的兩個檔；`records.py` 只多一行常數＋一個條件；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_records_names.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改 `_NOT_RECORDS`、`_TRACE`、`_LOG`、`MAX_BYTES`、`store_files` 流程。
- 不刪已經存在 `records/` 底下的舊檔（沒有使用者資料變動；不需要 migration）。
- 不把兩邊樣式合成共用常數。

## 裁決
1. **為什麼不 import 站台端的樣式？** 兩道鎖刻意各自寫，一邊出錯另一邊仍擋得住。**定案：平台端自己寫一份，以一致性測試防漂移。**

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
