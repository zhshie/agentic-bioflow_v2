---
id: samplesheet-suffix-path-column
title: samplesheet 欄名以 _file／_path 結尾（bam_path、reads_file…）也要當路徑欄檢查
tier: A
kinds: backend
lane: L16-suffix-path-column（只動 platform/abf_station/launch.py 的一行 regex 呼叫與 test_launch_bundle.py；不與 azure-upload／azure-clean／k8s／web 任務相交）
branch: fix/samplesheet-suffix-path-column
base: v3
source: developer-agent 清債掃描（2026-10-29，Sonnet 子代理在 origin/v3 e8619e2 上實跑證明會失敗）
---

# samplesheet-suffix-path-column

## 目標
`launch.py` 的 `DEFAULT_PATH_COLUMN` 第二個分支 `_(file|path)\Z` 本意是「欄名以 `_file`／`_path` 結尾」，但 `path_cells` 用 `.match()`（從字首比對），所以只有欄名剛好以 `_file`／`_path` 開頭時才中，`bam_path`、`reads_file`、`fasta_file` 全部漏掉。對使用者的意義：這些欄裡的相對路徑或 roots 之外的路徑現在會被放行、bundle 照產生，到站台上才失敗或讀到不該讀的地方；同樣的值放在 `reads` 欄就會當場被白話拒絕。修好後兩者一致。這是只讓檢查變嚴的修正（A 級）。

## 維護者原話（verifier 出題用）
- 本任務沒有維護者原話；依據是程式自己的 docstring（`path_cells`）：「a cell of a path column (named, or one of the usual names) or any cell that starts with /」，以及 regex 第二分支的明顯意圖。

## 範圍：檔案（只准改這些）
- `platform/abf_station/launch.py`（只改 `path_cells` 裡的 `DEFAULT_PATH_COLUMN.match(h)`，或 `DEFAULT_PATH_COLUMN` 本身；兩者擇一，見作法）
- `platform/tests/test_launch_bundle.py`（只新增測試；既有測試原樣）
- `specs/samplesheet-suffix-path-column/ledger.md`（新，進度帳本）
- 若 `docs/` 有逐字列出「預設路徑欄名」的句子而與新行為不符，可改那一句（先 `git grep -n -i "usual names\|path column" docs`；沒有就不動 docs）

**禁止碰**：`web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、任何 `*aws*`／`*azure*`／`*gcb*` 檔、`compute_envs.py`、`jobs.py`、`.github/`、`tests/run_all.sh`、`tests/quarantine.txt`。

## 作法
1. 最小修法：`path_cells` 的 `DEFAULT_PATH_COLUMN.match(h)` 改成 `DEFAULT_PATH_COLUMN.search(h)`。第一分支已有 `^…\Z`，`search` 不改變它的意義；第二分支 `_(file|path)\Z` 改為在欄名結尾比對。
2. 先 `git grep -n "DEFAULT_PATH_COLUMN" origin/v3` 找所有呼叫點；若別處（例如引導式 launch 或 pipeline_files）也用 `.match`，同樣改成 `.search`，並在帳本列出。若呼叫點在禁止碰的檔（web.py 等），不改，帳本記一行留給維護者。
3. 不改 regex 內容、不新增欄名、不改任何錯誤訊息。

## 失敗先行測試
加在 `platform/tests/test_launch_bundle.py`，用該檔既有的 `refused` 與「通過」helper：
1. `test_suffix_path_column_is_judged`：`refused(samplesheet=[["id", "bam_path"], ["s1", "relative.fq"]])`。今天在 v3 上 `DID NOT RAISE BundleError`（子代理已實跑證明）。
2. `test_suffix_file_column_is_judged`：同上，欄名 `reads_file`、值為 roots 之外的絕對路徑以外的相對路徑 → 被拒。
3. `test_suffix_match_is_case_insensitive`：欄名 `BAM_PATH` → 被拒（regex 有 `re.I`）。
4. 控制組（今天就綠、改後仍綠）：欄名 `profile`、`filepath_note`、`sample` 放相對字串不被當路徑；`reads` 欄既有行為不變（既有 `test_tc011_the_path_columns_can_be_named` 原樣綠）。
5. `test_suffix_path_column_inside_roots_passes`：`bam_path` 欄放 roots 內的絕對路徑 → bundle 正常產生（不能把合法用法也擋掉）。

## 完成標準（done when）
- 上述測試先紅（1–3、5 中至少 1–3 紅）後綠；`bash tests/run_all.sh` 全綠（或只剩 README 通例裡的已知環境紅）。
- diff 只動範圍內檔案；帳本列出所有 `DEFAULT_PATH_COLUMN` 呼叫點與處理方式。

## 環境事實
- 測試跑法見 repo 根 `CLAUDE.md`「For the executor and verifier」。
- 子代理在 origin/v3 e8619e2 上跑測試 1：`Failed: DID NOT RAISE BundleError`。

## 不做
- 不擴充預設欄名清單、不改 nf-core samplesheet 推斷、不碰網頁引導式 launch 的欄位判斷（若它另有實作）。

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
