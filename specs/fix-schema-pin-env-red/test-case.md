# 測試案例：修 test_no_schema_change 的環境誤報（三點比對）

**規格**：`specs/fix-schema-pin-env-red/plan.md`（此任務無 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「釘點測試」＝ `platform/tests/test_mcp_launch_pipeline.py::test_no_schema_change`（TC-032 原案），它保證 launch_pipeline 這個功能不准動資料庫結構。「三處」＝ `migrations`、`abf_platform/store.py`、`abf_platform/schema.sql`。「分支」＝本任務的開發分支；「base 前進」＝ v3 在分支切出後又有人改了東西。

## User Story 1 — 沒碰資料庫結構的分支不再被誤報擋住（優先度 P1）

維護者原話：「以後開發務必將工作排到最滿」（10-24）；「在還沒到規定 token 上限，都將開發進程拉到最趕」。這條誤報讓 6 條車道閒置。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「失敗先行測試」`test_schema_pin_ignores_base_advance`；作法 2 | 功能 | 在暫時 git repo 裡：分支切出後，v3（`origin/v3`）又改了 `schema.sql`／`store.py`；分支本身一個字都沒動這三處 | 用比對 helper 對這個 repo 做 `origin/v3...HEAD` 比對 | 回傳為空（沒有任何差異）。同一個情境用舊寫法（兩個點、`origin/v3`）會非空，所以此測試在舊寫法下會紅 | 自動：`platform/tests/test_mcp_launch_pipeline.py::test_schema_pin_ignores_base_advance` |
| TC-002 | 計畫目標；完成標準第 1 條「原 TC-032 在落後 v3 的 worktree 也綠」 | 功能 | 驗收用的 worktree 的 `origin/v3` 比分支切出時新（落後 v3），且分支沒動三處 | 單獨執行 `test_no_schema_change` | 通過（綠）。不再因為本機 `origin/v3` 快照較新而誤紅 | 自動：`platform/tests/test_mcp_launch_pipeline.py::test_no_schema_change` |
| TC-003 | 計畫「裁決」作法定案；作法 1 | 功能 | 看分支對 base 的 diff | 讀 `test_no_schema_change` 的內容 | 它用 `origin/v3...HEAD`（三個點，與 merge-base 比）；工作目錄（`HERE.parent`）與三個路徑參數與原來完全相同；且它真的呼叫 helper（不是 helper 寫好了卻沒人用） | 手動：驗收者以 `git diff v3...HEAD` 核對（`docs/TESTING.md` 無此步驟，見總覽「不確定」） |

## User Story 2 — 分支真的改了資料庫結構時，釘點仍然紅（優先度 P1）

維護者／lead 原意：TC-032 的原意是「這個功能不准動資料庫 schema，保護力道不得變弱」；lead 2026-11-07 裁決：「分支若真的改了這三處，測試仍然紅」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-004 | 計畫「失敗先行測試」`test_schema_pin_still_catches_branch_change`；作法 2 | 例外 | 暫時 git repo：分支上有一個 commit 改了 `abf_platform/schema.sql` | 用同一個比對 helper 做 `origin/v3...HEAD` 比對 | 回傳非空（看得到 `schema.sql` 的差異）；以此為依據的釘點測試會紅 | 自動：`platform/tests/test_mcp_launch_pipeline.py::test_schema_pin_still_catches_branch_change` |
| TC-005 | 裁決「這三處」；保護力道不變 | 例外 | 暫時 git repo：分支上有一個 commit 改了 `abf_platform/store.py` | 同上 | 回傳非空（看得到 `store.py` 的差異） | 自動：同檔，`test_schema_pin_still_catches_branch_change`（須涵蓋 store.py；或同檔另一條測試） |
| TC-006 | 裁決「這三處」；保護力道不變 | 例外 | 暫時 git repo：分支上有一個 commit 在 `migrations/` 新增或修改了檔案 | 同上 | 回傳非空（看得到 `migrations/` 的差異） | 自動：同檔，同上 |
| TC-007 | 計畫「不做」：不刪這條測試、不改成永遠綠 | 功能 | 看分支改完後的 `test_no_schema_change` | 讀測試內容並與 base 版本比對 | 測試仍存在；仍是斷言比對結果為空（`out.strip() == ""` 或等價強度）；三個路徑參數一個不少；沒有被 skip、沒有 try/except 吞掉、沒有條件式放行 | 手動：驗收者以 `git diff v3...HEAD -- platform/tests/test_mcp_launch_pipeline.py` 核對 |

## User Story 3 — 完成標準與證據（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 完成標準第 3 條 | 功能 | 執行者完成實作 | 開 `specs/fix-schema-pin-env-red/ledger.md` | 帳本裡附有一段實際跑出來的輸出：分支真的改了 `schema.sql` 時，釘點比對非空／測試是紅的；不是只有文字敘述 | 手動：驗收者讀 ledger.md |
| TC-009 | 完成標準第 2 條 | 功能 | 分支 HEAD 乾淨 | 在 WSL／Linux 跑全套 `bash tests/run_all.sh`（由 gate 標記 `GREEN <HEAD sha>` 代表） | 全套綠，且 gate 標記與 HEAD 相符 | 自動：`tests/run_all.sh` |

## User Story 4 — 不在範圍（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 計畫「不做」第 1 條：不改 `store.py`、`migrations/`、`schema.sql` | 不在範圍 | 本任務分支 | 對三處做 `git diff v3...HEAD -- migrations abf_platform/store.py abf_platform/schema.sql` | 輸出為空（本任務自己沒碰這三處；這也是任務自身通過釘點的條件） | 手動：驗收者執行該 git 指令 |
| TC-011 | 計畫作法 3：不動其他同名 `test_no_schema_change`（test_k8s_ce、test_web_actions 等） | 不在範圍 | 本任務分支 | 列出 `git diff --name-only v3...HEAD`，並 grep 其他測試檔的 `test_no_schema_change` | 被改動的檔案只有 `platform/tests/test_mcp_launch_pipeline.py` 與 `specs/fix-schema-pin-env-red/` 下的檔案；其他檔裡的同名測試內容與 base 完全一致 | 手動：驗收者以 git diff 核對 |
| TC-012 | 計畫「範圍：檔案」：該檔只改 `test_no_schema_change`（外加新增的 helper 與兩條新測試） | 不在範圍 | 本任務分支 | 檢視 `platform/tests/test_mcp_launch_pipeline.py` 的 diff | 除了 `test_no_schema_change`、新增的 helper、新增的反證測試，其他既有測試一行都沒改、沒刪、沒被放寬 | 手動：驗收者以 git diff 核對 |
| TC-013 | 計畫「不做」：不動 CI 設定；裁決：supervise／dev-worker 的孤兒問題不是本任務、已另行修好 | 不在範圍 | 本任務分支 | 列出 `git diff --name-only v3...HEAD` | 清單中沒有 `.github/` 下任何檔案，也沒有 `supervise.js`、`dev-worker.md`、`spec.md`、`test-case*.md`（`specs/fix-schema-pin-env-red/` 之外）的改動 | 手動：驗收者以 git diff 核對 |
