# 測試案例：samplesheet 欄名以 _file／_path 結尾也要當路徑欄檢查

**規格**：`specs/samplesheet-suffix-path-column/plan.md`（本任務沒有 spec.md，也沒有維護者原話；依據是計畫與 `path_cells` 自己的 docstring）　**總覽**：`test-case-overview.md`

名詞：「路徑欄」＝樣本表（samplesheet）裡，系統會逐格檢查「是不是絕對路徑、有沒有落在允許讀取的範圍內」的欄。「允許讀取範圍（roots）」＝發起 launch 時 `roots` 列的資料夾。「被拒」＝產生 launch 包（bundle）時丟出 `BundleError`，使用者看到白話拒絕訊息，沒有任何檔案被寫出。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、使用者做了不該做的事時，系統怎麼反應（拒絕）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

下列自動測試都加在 `platform/tests/test_launch_bundle.py`，用該檔既有的 `refused(...)`（斷言被拒）與 `render(...)`（斷言通過並產生 bundle）。每條測試的註解要寫出它的 TC 編號。

## User Story 1 — 欄名以 _file／_path 結尾的欄，跟 reads 欄一樣被檢查（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「失敗先行測試」1；目標 | 例外 | 樣本表 `[["id","bam_path"],["s1","relative.fq"]]`，其餘輸入用 `inputs()` 預設值 | 呼叫產生 bundle | 被拒（`BundleError`）；訊息指出是 `bam_path` 這一欄、第 2 列。base 上這條是「DID NOT RAISE」 | 自動：`platform/tests/test_launch_bundle.py::test_suffix_path_column_is_judged` |
| TC-002 | 計畫「失敗先行測試」2 | 例外 | 樣本表 `[["id","reads_file"],["s1","<相對路徑，例如 relative.fq>"]]` | 呼叫產生 bundle | 被拒；訊息指出是 `reads_file` 欄 | 自動：`test_launch_bundle.py::test_suffix_file_column_is_judged` |
| TC-003 | 計畫「失敗先行測試」3 | 例外 | 樣本表 `[["id","BAM_PATH"],["s1","relative.fq"]]`（欄名大寫） | 呼叫產生 bundle | 被拒（欄名比對不分大小寫） | 自動：`test_launch_bundle.py::test_suffix_match_is_case_insensitive` |
| TC-004 | 計畫「目標」：roots 之外的路徑現在會被放行 | 例外 | 樣本表 `[["id","bam_path"],["s1","/etc/passwd"]]`（絕對路徑，但在 roots 之外） | 呼叫產生 bundle | 被拒；訊息說路徑在允許讀取的範圍之外 | 自動：`test_launch_bundle.py` 內新增一條，註解寫 TC-004 |
| TC-005 | 計畫「目標」：同樣的值放在 reads 欄就被拒，修好後兩者一致 | 例外 | 兩份樣本表，只差欄名：`reads` 與 `bam_path`，同一個值 `relative.fq` | 各呼叫一次產生 bundle | 兩次都被拒，且拒絕原因相同（都是「不是絕對路徑／在允許範圍之外」那一句，只有欄名不同） | 自動：`test_launch_bundle.py` 內新增一條，註解寫 TC-005 |
| TC-006 | 計畫「失敗先行測試」5 | 功能 | 樣本表 `[["id","bam_path"],["s1","/data/storage/rawdata/s1.bam"]]`（roots 之內的絕對路徑） | 呼叫產生 bundle | 正常產生 bundle；`files["samplesheet.csv"]` 裡有 `s1,/data/storage/rawdata/s1.bam` 這一列，路徑原樣不變（合法用法沒被誤擋） | 自動：`test_launch_bundle.py::test_suffix_path_column_inside_roots_passes` |

## User Story 2 — 不是路徑欄的欄不被誤傷，原有行為不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 計畫「失敗先行測試」4 | 功能 | 樣本表 `[["id","profile"],["s1","some/relative text"]]` | 呼叫產生 bundle | 正常產生，不被當路徑檢查（修改前後都綠） | 自動：`test_launch_bundle.py` 內新增控制組，註解寫 TC-007 |
| TC-008 | 計畫「失敗先行測試」4 | 功能 | 樣本表 `[["id","filepath_note"],["s1","some/relative text"]]`（欄名含 path 但不是以 `_path` 結尾） | 呼叫產生 bundle | 正常產生，不被當路徑檢查 | 自動：`test_launch_bundle.py` 內新增控制組，註解寫 TC-008 |
| TC-009 | 計畫「失敗先行測試」4 | 功能 | 樣本表 `[["sample","note"],["s1","free/relative text"]]` 與預設的 `sample` 欄（`s1`） | 呼叫產生 bundle | 正常產生，`sample` 欄不被當路徑檢查 | 自動：`test_launch_bundle.py` 內新增控制組，註解寫 TC-009 |
| TC-010 | 計畫「失敗先行測試」4：reads 欄既有行為不變 | 功能 | 既有測試 `test_tc011_the_path_columns_can_be_named` 與該檔其餘所有既有測試，一個字都沒改 | 跑 `platform/tests/test_launch_bundle.py` | 既有測試全綠，其中 `reads` 欄放 `relative.fq` 與 `/etc/x` 仍被拒、`note` 欄放自由文字仍通過 | 自動：`test_launch_bundle.py`（既有測試） |

## User Story 3 — 範圍、完成標準與不在範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫「完成標準」：測試先紅後綠 | 功能 | 取 base（`v3`，e8619e2）的 `launch.py`，加上本任務新增的測試檔 | 閱卷者在 base 程式上單跑 TC-001、TC-002、TC-003 對應的三條測試；再在本任務 HEAD 上跑 | base 上三條都失敗（`DID NOT RAISE BundleError`）；HEAD 上三條都通過 | 手動：閱卷者在兩個版本各跑一次 `test_launch_bundle.py -k suffix` |
| TC-012 | 計畫「完成標準」：全套件綠 | 功能 | 本任務 HEAD | 依 `CLAUDE.md`「For the executor and verifier」在 WSL 跑 `tests/run_all.sh`（完成記號 `executor-status` 為 `GREEN <HEAD sha>`） | 全綠（或只剩 README 通例裡已知的環境紅，且逐條列出） | 自動：`tests/run_all.sh` |
| TC-013 | 計畫「範圍：檔案」 | 功能 | `git diff v3...HEAD --stat` | 閱卷者檢查被改的檔案 | 只有 `platform/abf_station/launch.py`、`platform/tests/test_launch_bundle.py`、`specs/samplesheet-suffix-path-column/ledger.md`，以及（僅當 `docs/` 有逐字列出預設路徑欄名且與新行為不符時）那一句文件；沒有其他檔 | 手動：閱卷者看 diff |
| TC-014 | 計畫「範圍」：既有測試原樣、只新增 | 功能 | `git diff v3...HEAD -- platform/tests/test_launch_bundle.py` | 閱卷者檢查 diff | 只有新增行；沒有任何既有行被刪除、改寫、改成 skip，或放寬斷言 | 手動：閱卷者看 diff |
| TC-015 | 計畫「作法」1、3 | 功能 | `git diff v3...HEAD -- platform/abf_station/launch.py` | 閱卷者檢查 diff | 程式碼只有 `path_cells` 裡把 `DEFAULT_PATH_COLUMN.match(h)` 改成 `.search(h)` 的一行；`DEFAULT_PATH_COLUMN` 的正規式文字沒變、沒有新增欄名、沒有任何錯誤訊息文字被改 | 手動：閱卷者看 diff |
| TC-016 | 計畫「完成標準」：帳本列出所有呼叫點 | 功能 | `specs/samplesheet-suffix-path-column/ledger.md` | 閱卷者讀帳本，並自己跑 `git grep -n DEFAULT_PATH_COLUMN` 對照 | 帳本列出 `DEFAULT_PATH_COLUMN` 的每一個使用處（目前只有 `launch.py` 的 `path_cells`）與處理方式；若有別處且在禁止碰的檔，帳本留一行給維護者 | 手動：閱卷者看帳本 |
| TC-017 | 計畫「完成標準」：全綠；`path_cells` 也被其他 launch 路徑共用（`launch.py` 另外三處、`platform/abf_launch/build.py`） | 功能 | 雲端 launch 的既有測試（`test_gcb_launch.py`、`test_aws_launch.py`、Azure 的 launch 測試）一個字都沒改 | 跑這些測試檔 | 全綠；其中 `test_gcb_launch.py` 的「非路徑欄不被檢查」那段仍通過 | 自動：`platform/tests/test_gcb_launch.py`、`test_aws_launch.py` 及 Azure launch 測試檔（既有測試） |
| TC-018 | 計畫「不做」：不擴充預設欄名清單 | 不在範圍 | 樣本表 `[["id","genome"],["s1","some/relative text"]]`（`genome` 不在預設欄名清單，也不是以 `_file`／`_path` 結尾） | 呼叫產生 bundle | 正常產生，`genome` 欄仍不被當路徑檢查（沒有偷偷擴充清單） | 自動：`test_launch_bundle.py` 內新增一條，註解寫 TC-018 |
| TC-019 | 計畫「不做」：不改 nf-core samplesheet 推斷、不碰網頁引導式 launch；「禁止碰」清單 | 不在範圍 | `git diff v3...HEAD --stat` | 閱卷者檢查被改的檔案 | 沒有 `web.py`、`web_board.py`、`static/*`、`DESIGN.md`、`test_web_*`、任何 `*aws*`／`*azure*`／`*gcb*` 檔、`compute_envs.py`、`jobs.py`、`.github/`、`tests/run_all.sh`、`tests/quarantine.txt`，也沒有產生 samplesheet 的腳本或其測試（如 `tests/generate_samplesheet_test.sh`） | 手動：閱卷者看 diff |
