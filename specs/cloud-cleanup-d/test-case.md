# 測試案例：Google Batch 清理（先列出再刪 bucket 裡這個 run 的 work 前綴）

**規格**：`specs/cloud-cleanup-d/plan.md`（本任務沒有獨立 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

## 讀表前先認識的幾個詞

- **代理**：跑在平台主機上、替使用者實際動手的小程式（`abf_station`）。本片只改它的 `clean.py`。
- **work 前綴**：Nextflow 在雲端桶（bucket）裡留下的中間檔，位置固定是 `gs://<桶>/<子資料夾>/runs/<run 名>/work/`。**結果**在同一層的 `results/`，不能動。
- **標準情境**（下表沒另外寫的前置條件都用它）：使用者已按「確認刪除」（憑證種類 `clean_work`，沒用過）；Google Batch 環境的 run `r1`；`workDir=gs://lab-bucket/work`；專案 `lab-project-1`；內容包的 `work` 是 `gs://lab-bucket/work/runs/r1/work`；`storage_root`、`run_folder` 都正確；`head.pid` 記的主控程序已經不在；金鑰在位且預檢通過。
- **假雲端桶**：測試用的假 `gcloud`，只記物件名稱、模擬 `ls`／`rm` 的「前綴」行為。裡面有 `runs/r1/work/x`、`runs/r1/work/sub/y`，以及同層的 `runs/r1/work2/x`、`runs/r1/work-keep`、`runs/r1/results/a.tsv`。這個假行為本身是對官方文件的假設，真桶驗證在 f 片。
- **零呼叫**：假 `gcloud` 與假 `ps` 一次都沒被呼叫（連「問金鑰」的唯讀預檢也沒有），假雲端桶內容原封不動。

## User Story 1 — 確認過的 run：只刪它自己的 work 前綴（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；手算範例 1；維護者原話「跑完經本人確認刪中間檔（work），結果保留」「kind `clean_work`，對 nano4 也適用」 | 功能 | 標準情境 | 代理執行這個已確認的清理工作 | 結果為完成：`ok: true`、`cleaned: true`、`run_name: r1`，訊息為「已刪除 bucket 裡 gs://lab-bucket/work/runs/r1/work 底下的物件；results 沒有動」。假雲端桶裡 `work/x`、`work/sub/y` 沒了；`work2/x`、`work-keep`、`results/a.tsv` 全部還在 | 自動：`platform/tests/test_station_clean_gcb.py` |
| TC-002 | 作法 2.6 | 功能 | 標準情境 | 同 TC-001，記錄所有 `gcloud` 呼叫 | 刪除之前有先呼叫唯讀列出，參數恰為 `["gcloud","storage","ls","--recursive","--project","lab-project-1","gs://lab-bucket/work/runs/r1/work/"]`；這次列出發生在刪除呼叫之前 | 自動：同上 |
| TC-003 | 作法 2.7；裁決 3 | 功能 | 標準情境 | 同 TC-001，數含 `rm` 動詞的呼叫 | 恰好一次，參數恰為 `["gcloud","storage","rm","--recursive","--project","lab-project-1","gs://lab-bucket/work/runs/r1/work/"]`：只有一個網址，沒有 `--continue-on-error`，沒有 `--all-versions` | 自動：同上 |
| TC-004 | 作法 2.4／2.6／2.7；範圍（`site.run_fixed`） | 功能 | 標準情境 | 同 TC-001，攔截代理對外的呼叫 | `ps`、`ls`、`rm` 三種呼叫都經過 `site.run_fixed`、參數是清單（不是一串要交給 shell 的字）；`ps` 參數恰為 `["ps","-o","user=","-o","args=","-p","<head.pid 的數字>"]`；逾時分別是 20、120、300 秒；程式沒有直接呼叫 `subprocess` | 自動：同上 |
| TC-005 | 作法 2.6（子資料夾標題） | 功能 | 標準情境；假 `ls` 的輸出含 `gs://lab-bucket/work/runs/r1/work/sub/:` 這種以冒號結尾的子資料夾標題行與其下物件 | 執行清理 | 標題行去掉冒號後在 `…/work/` 底下，視為合格，照常刪除並回 `cleaned: true` | 自動：同上 |
| TC-006 | 手算範例 7 | 功能 | 標準情境，但假雲端桶的 `work/` 底下沒有任何物件（`ls` 沒有物件行） | 執行清理 | 回完成：`ok: true`、`cleaned: true`（「已經沒有東西」）；含 `rm` 動詞的呼叫 0 次 | 自動：同上 |
| TC-007 | 作法 2.6（`rc != 0` 且表示沒有符合的物件） | 功能 | 標準情境，但假 `ls` 回「沒有符合的物件」的那種非零結束碼與訊息（照 ledger 記載的官方結束碼與訊息） | 執行清理 | 與 TC-006 相同：`cleaned: true`，不呼叫 `rm` | 自動：同上 |
| TC-008 | 手算範例 14 | 功能 | 標準情境，但 `head.pid` 的 pid 還活著，命令列不含 `-name r1`（pid 被別的程式借用） | 執行清理 | 視為主控程序已不在，繼續列出並刪除，回 `cleaned: true` | 自動：同上 |
| TC-009 | 作法 2.4（`rc != 0` 或沒有輸出＝已不在） | 功能 | 標準情境，但 `ps` 回非零結束碼（或沒有任何輸出） | 執行清理 | 視為主控程序已不在，繼續列出並刪除，回 `cleaned: true` | 自動：同上 |

## User Story 2 — 沒確認、內容包不對、路徑不對：一律拒絕（優先度 P1）

下表每一列的共同預期：回覆是「被拒絕」，用白話說明原因；除非另外寫明，都是**零呼叫**，假雲端桶不變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 維護者原話「經本人確認」；失敗先行測試第 1 條 | 例外 | 五種情況各做一次：①沒有確認憑證 ②憑證的雜湊與內容包對不上 ③憑證已被用過一次 ④憑證種類是 `launch` ⑤憑證種類是 `cancel` | 執行清理 | 五種都被拒絕，零呼叫（`gcloud` 一個字都不呼叫），桶不變 | 自動：同上 |
| TC-011 | 作法 1（鍵集合） | 例外 | 標準情境，內容包多一個或少一個欄位 | 執行清理 | 被拒絕（欄位不對），零呼叫 | 自動：同上 |
| TC-012 | 作法 2.1 | 例外 | 標準情境，內容包的 `agent` 不是這台代理的名字 | 執行清理 | 被拒絕（這個清理是給另一個代理的），零呼叫 | 自動：同上 |
| TC-013 | 作法 2.2 | 例外 | 標準情境，`run_folder` 不是 `<storage_root>/_gcb_runs/r1`（差一個字也算） | 執行清理 | 被拒絕，零呼叫 | 自動：同上 |
| TC-014 | 作法 2.2（沒有 storage_root） | 例外 | 標準情境，但部署設定沒有 `storage_root` | 執行清理 | 被拒絕，訊息用白話寫出「部署設定沒有 storage_root」，零呼叫 | 自動：同上 |
| TC-015 | 作法 2.1（程序編號） | 例外 | 標準情境，`slurm_job_id` 分別為 0、-1、2147483648、`True`、字串 `"123"` | 各執行一次 | 全部被拒絕，零呼叫 | 自動：同上 |
| TC-016 | 作法 2.1（run 名稱） | 例外 | 標準情境，run 名稱不符平台的命名規則（例如大寫開頭、含空白、超過 64 字） | 執行清理 | 被拒絕，零呼叫 | 自動：同上 |
| TC-017 | 失敗先行測試（惡意 run 名稱） | 例外 | run 名稱含空白、`;`、`$()`、換行、雙向文字控制字元（BIDI）各一種 | 各執行一次 | 全部被拒絕，在任何外部命令之前（零呼叫） | 自動：同上 |
| TC-018 | 失敗先行測試（惡意 workDir） | 例外 | `workDir` 與 `work` 路徑含空白、`;`、`$()`、換行、BIDI 各一種 | 各執行一次 | 全部被拒絕，在任何外部命令之前（零呼叫） | 自動：同上 |
| TC-019 | 手算範例 2 | 例外 | 標準情境，內容包 `work` 為 `gs://lab-bucket/work/runs/r1/results` | 執行清理 | 被拒絕（含 results、最後一段不是 work），零呼叫，`results/a.tsv` 還在 | 自動：同上 |
| TC-020 | 手算範例 3 | 例外 | 標準情境，內容包 `work` 分別為 `…/work/*`、`…/work*`、`…/work?`、`…/work[ab]`、`…/work{a,b}` | 各執行一次 | 五種都被拒絕（萬用字元），零呼叫，桶不變 | 自動：同上 |
| TC-021 | 手算範例 4 | 例外 | 標準情境，內容包 `work` 為 `gs://other-bucket/work/runs/r1/work` | 執行清理 | 被拒絕（桶與 workDir 不同），零呼叫 | 自動：同上 |
| TC-022 | 手算範例 5 | 例外 | 標準情境，內容包 `work` 為 `gs://lab-bucket/work/runs/r1/` | 執行清理 | 被拒絕（最後一段不是 work），零呼叫 | 自動：同上 |
| TC-023 | 手算範例 8 | 例外 | 標準情境，內容包 `work` 為 `gs://lab-bucket/work/runs/r1/work/../results` | 執行清理 | 被拒絕（含 `..`），零呼叫，`results/a.tsv` 還在 | 自動：同上 |
| TC-024 | 作法 2.3（不得有 `.` 段） | 例外 | 標準情境，內容包 `work` 為 `gs://lab-bucket/work/./runs/r1/work` | 執行清理 | 被拒絕（含 `.` 段），零呼叫 | 自動：同上 |
| TC-025 | 手算範例 9 | 例外 | 兩種各做一次：`workDir=gs://lab-bucket/work/rawdata`（work 為 `gs://lab-bucket/work/rawdata/runs/r1/work`）；`workDir=gs://lab-bucket/analysis`（work 為 `gs://lab-bucket/analysis/runs/r1/work`） | 各執行一次 | 兩種都被拒絕（含 `rawdata`／`analysis` 段），零呼叫 | 自動：同上 |
| TC-026 | 作法 2.3（不得有 `results` 段）；`CLAUDE.md` §3.4 | 例外 | `workDir=gs://lab-bucket/results`，內容包 `work` 為 `gs://lab-bucket/results/runs/r1/work` | 執行清理 | 被拒絕（含 `results` 段），零呼叫 | 自動：同上 |
| TC-027 | 手算範例 10 | 例外 | 標準情境，內容包 `work` 為 `gs://lab-bucket/work/runs/r2/work`（run 是 r1） | 執行清理 | 被拒絕（與這個 run 重算的路徑不同），零呼叫，r2 若有物件也不變 | 自動：同上 |
| TC-028 | 手算範例 11 | 例外 | 標準情境，內容包 `work` 為 `gs://lab-bucket/work//runs/r1/work` | 執行清理 | 被拒絕（空段），零呼叫 | 自動：同上 |
| TC-029 | 手算範例 12 | 例外 | 標準情境，環境的 `workDir=gs://lab-bucket`（桶底下沒有子資料夾），`work` 為 `gs://lab-bucket/runs/r1/work` | 執行清理 | 被拒絕（既有環境規則要求至少一層子資料夾），零呼叫 | 自動：同上 |
| TC-030 | 作法 2.3（逐字，不容許結尾斜線） | 例外 | 標準情境，內容包 `work` 為 `gs://lab-bucket/work/runs/r1/work/`（多一個結尾斜線） | 執行清理 | 被拒絕（與重算值不逐字相等），零呼叫 | 自動：同上 |

## User Story 3 — 主控程序還在跑、金鑰不對：不刪（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 手算範例 13 | 例外 | 標準情境，但 `head.pid` 的 pid 還活著，命令列含 `-name r1` | 執行清理 | 被拒絕，訊息說主控程序還在跑；`gcloud` 零呼叫（連預檢與 `ls` 都沒有），桶不變 | 自動：同上 |
| TC-032 | 手算範例 15 | 例外 | 標準情境，但 run 資料夾裡沒有 `head.pid` | 執行清理 | 被拒絕，訊息為「找不到 head.pid，無法確認主控程序已結束」；`gcloud` 零呼叫，桶不變 | 自動：同上 |
| TC-033 | 作法 2.4 | 例外 | `head.pid` 內容不是純數字（例如 `abc`、空檔） | 執行清理 | 被拒絕（同上訊息），`gcloud` 零呼叫 | 自動：同上 |
| TC-034 | 作法 2.4 | 例外 | `head.pid` 的數字與內容包的 `slurm_job_id` 不同 | 執行清理 | 被拒絕，`gcloud` 零呼叫 | 自動：同上 |
| TC-035 | 裁決二第 4 點 | 例外 | 標準情境，但 `ps` 回了不只一行 | 執行清理 | 被拒絕，訊息為「無法確認主控程序已結束（ps 回了不只一行），保守起見不刪」；`gcloud` 零呼叫 | 自動：同上 |
| TC-036 | 作法 2.4（`ps` 逾時）；失敗先行測試 | 例外 | 標準情境，但 `ps` 逾時 | 執行清理 | 結果是 error，訊息為「查詢逾時，沒有刪任何東西，也不重試」；`ps` 只呼叫一次；`gcloud` 零呼叫（沒列、沒刪） | 自動：同上 |
| TC-037 | 作法 2.5 | 例外 | 標準情境，但金鑰檔不存在 | 執行清理 | 被拒絕，沒有任何 `ls`、`rm` 呼叫，桶不變 | 自動：同上 |
| TC-038 | 作法 2.5 | 例外 | 標準情境，但金鑰檔權限太開（別人讀得到） | 執行清理 | 被拒絕，沒有任何 `ls`、`rm` 呼叫，桶不變 | 自動：同上 |
| TC-039 | 作法 2.5 | 例外 | 標準情境，但金鑰檔不是服務帳戶金鑰 | 執行清理 | 被拒絕，沒有任何 `ls`、`rm` 呼叫，桶不變 | 自動：同上 |
| TC-040 | 作法 2.5 | 例外 | 標準情境，但金鑰所屬專案與環境的專案不同 | 執行清理 | 被拒絕，沒有任何 `ls`、`rm` 呼叫，桶不變 | 自動：同上 |
| TC-041 | 作法 2.5（兩個唯讀 `gcloud` 問題） | 例外 | 標準情境，但預檢的唯讀 `gcloud` 問題失敗 | 執行清理 | 被拒絕，沒有 `ls`、`rm` 呼叫，桶不變 | 自動：同上 |

## User Story 4 — 列出或刪除出錯：誠實回報、不重試（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-042 | 手算範例 6；失敗先行測試 | 例外 | 標準情境，但假 `ls` 回了 `gs://lab-bucket/work/runs/r1/work2/x`（不是以 `…/work/` 開頭） | 執行清理 | 被拒絕，訊息說「列出的物件不全在 work 底下（前綴撞名），不刪」；`rm` 呼叫 0 次；`work2/x` 還在 | 自動：同上 |
| TC-043 | 裁決二第 3 點 | 例外 | 標準情境，但 `ls` 逾時 | 執行清理 | 回「被拒絕」，內容為 `ok: false`、`cleaned: false`、訊息「列出雲端暫存檔逾時，沒有刪任何東西；稍後可以再申請」；`rm` 呼叫 0 次 | 自動：同上 |
| TC-044 | 作法 2.6（其他非零） | 例外 | 標準情境，但 `ls` 回非零結束碼，且訊息不是「沒有符合的物件」 | 執行清理 | 結果是 error，沒有 `cleaned: true`；`rm` 呼叫 0 次；訊息經過洗淨 | 自動：同上 |
| TC-045 | 作法 2.7；失敗先行測試 | 例外 | 標準情境，但 `rm` 回非零結束碼 | 執行清理 | 結果是 error，沒有 `cleaned: true`；訊息含「可能只刪了一部分；work_cleaned_at 沒記，可以再申請」；`rm` 恰好呼叫 1 次（不重試） | 自動：同上 |
| TC-046 | 作法 2.7；失敗先行測試 | 例外 | 標準情境，但 `rm` 逾時 | 執行清理 | 同 TC-045 的 error 與訊息，沒有 `cleaned: true`；`rm` 恰好呼叫 1 次 | 自動：同上 |

## User Story 5 — 金鑰與回覆內容不外洩（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | 作法 2.5（金鑰路徑只放環境變數） | 功能 | 標準情境 | 同 TC-001，記錄每次外部呼叫的參數與環境 | `ls`、`rm` 的環境變數含 `GOOGLE_APPLICATION_CREDENTIALS=<金鑰路徑>` 與 `CLOUDSDK_CORE_DISABLE_PROMPTS=1`；金鑰路徑沒有出現在任何一次呼叫的參數裡 | 自動：同上 |
| TC-048 | 專長守則（密鑰不得出現在回應） | 功能 | 標準情境 | 同 TC-001 | 回覆的每個欄位與訊息都不含金鑰路徑 | 自動：同上 |
| TC-049 | 作法 2.6；專長守則 | 例外 | 標準情境，但假 `ls` 失敗，輸出中夾帶金鑰路徑與權杖字樣 | 執行清理 | 訊息中金鑰路徑被換成 `[key file]`，權杖類字樣被洗掉 | 自動：同上 |
| TC-050 | 作法 2.7；專長守則 | 例外 | 標準情境，但假 `rm` 失敗，輸出中夾帶金鑰路徑與權杖字樣 | 執行清理 | 訊息中金鑰路徑被換成 `[key file]`，權杖類字樣被洗掉 | 自動：同上 |
| TC-051 | 專長守則（日誌不得有密鑰） | 功能 | 標準情境，成功與一種失敗各跑一次，收集所有日誌輸出 | 執行清理 | 日誌中沒有金鑰路徑 | 自動：同上 |
| TC-052 | 作法 2.5（不用 `_head_env`） | 功能 | 標準情境，部署設定裡另有一個使用者自訂的環境變數 | 同 TC-001，看 `ls`、`rm` 的環境 | 環境只有「乾淨環境」加上那兩個變數；使用者自訂變數沒有被帶進去 | 自動：同上 |
| TC-053 | 專長守則（錯誤訊息說明原因與怎麼辦，不露內部細節） | 例外 | 收集 TC-010 至 TC-046 中各類拒絕與錯誤的回覆 | 檢查文字 | 每則都說明發生什麼事，且在可以再試時說明怎麼辦（例如「可以再申請」）；沒有堆疊追蹤、SQL、本機內部路徑 | 自動：同上 |

## User Story 6 — 這次不做的事與既有行為不變（優先度 P2）

驗證方式欄寫「手動」的，是閱卷者讀 diff 或 ledger（計畫明言本片文件在 f 片，沒有新增 `docs/TESTING.md` 步驟）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | 範圍；失敗先行測試 | 不在範圍 | 本片完成後 | 掃描 `abf_station/*.py` 與 `abf_platform/*.py` | `storage rm` 字樣只出現在 `abf_station/clean.py` | 自動：同上 |
| TC-055 | 範圍（既有斷言只放寬 `storage rm`） | 不在範圍 | 本片完成後 | 掃描全部原始檔 | 另外三個字樣（`buckets create`、`services enable`、`service-accounts create`）在包含 `clean.py` 的所有原始檔都不出現；`clean.py` 以外的檔案四個字樣都不准出現 | 自動：`platform/tests/test_gcb_ce.py`、`platform/tests/test_cloud_upload.py` |
| TC-056 | 範圍（兩個釘子的更新方式） | 不在範圍 | 看 `test_gcb_ce.py` 與 `test_cloud_upload.py` 的 diff | 比對基底 | `test_gcb_ce.py` 裡 `re.search(r"buckets create\|…\|storage rm", text)` 那一行字面不變；`test_cloud_upload.py` 的 `options == [四個字樣]` 不變；放寬只限 `abf_station/clean.py` 且該檔仍檢查前三個字樣 | 手動：閱卷者讀 diff |
| TC-057 | 範圍；失敗先行測試 | 不在範圍 | 本片完成後 | 掃描 `abf_station/*.py` | `rm -rf` 字樣仍只出現在 `clean.py` | 自動：同 TC-001 的測試檔與 `test_station_clean.py` |
| TC-058 | 不做：不寫第二條寫入路徑、不用其他工具、不重試 | 不在範圍 | 本片完成後 | 掃描 `clean.py` 與其呼叫 | 沒有 `gcloud batch jobs delete`、`buckets delete`、`gsutil`、`rclone`、`--continue-on-error`、`--all-versions`；沒有任何雲端函式庫被 import（`test_no_cloud_library_is_imported` 仍綠）；`rm` 的呼叫沒有放在迴圈或重試裡 | 自動：同上 |
| TC-059 | 不做：不處理版本控制／軟刪除；環境事實③ | 不在範圍 | 看 ledger | 找版本控制／軟刪除的說明 | ledger 寫明官方說明對「bucket 開了物件版本控制或軟刪除時，`rm` 之後物件是否仍保留、是否仍計費、是否還原得回來」的結論與網址，供 f 片使用；程式沒有任何清除舊版本或軟刪除物件的動作 | 手動：閱卷者讀 ledger |
| TC-060 | 不做：不改 Slurm 的清理；失敗先行測試 | 功能 | 本片完成後 | 跑 `test_station_clean.py` 裡 Slurm 的所有測試 | 全部維持綠，行為與 c 片相同 | 自動：`platform/tests/test_station_clean.py` |
| TC-061 | 範圍（必須更新的既有斷言 1）；裁決二第 2 點 | 功能 | 本片完成後 | 跑 `test_tc013_a_google_batch_bundle_is_refused_in_plain_words` | 這條測試改成「Google Batch 內容包交給 `_clean_gcb`」：不再出現「尚未支援」，被拒絕的原因是 d 片規則之外的（例如金鑰缺失），且沒有任何東西經 `ctx.site.call` 送出 | 自動：`platform/tests/test_station_clean.py` |
| TC-062 | 裁決二第 1 點（TC-073 改寫） | 功能 | 本片完成後 | 跑 c 片的 TC-073 那條測試 | 改寫後仍有效：`clean.py` 不含 `import subprocess`、`os.system`、`os.popen`、`start_detached`；`run_fixed` 只出現在 `_clean_gcb` 與 `_head_gone` 兩個函式內（用 `ast` 找範圍）；`ctx.site.call(` 仍恰出現一次 | 自動：`platform/tests/test_station_clean.py` |
| TC-063 | 不做：不做平台端；憲法原則 2 | 不在範圍 | 本片完成後 | 看 `git diff <base>...HEAD` | `platform/abf_platform/*`、`platform/abf_launch/*` 一個檔都沒改；`gcloud` 只由代理經 `site.run_fixed` 啟動 | 手動：閱卷者讀 diff |
| TC-064 | 範圍：檔案、禁碰；完成標準 | 不在範圍 | 本片完成後 | `git diff --name-only <base>...HEAD`、`git diff --stat` 看禁碰檔 | 只有計畫「範圍：檔案」所列的 6 個檔（`clean.py`、新測試檔、`test_station_clean.py`、`test_gcb_ce.py`、`test_cloud_upload.py`、`ledger.md`）；`launch.py`、`gcb_launch.py`、`cancel.py`、`gcb_preflight.py`、`site.py`、`rules.py`、`handlers.py`、`test_gcb_launch.py` 位元級不變；`git diff --stat` 已貼進 ledger | 手動：閱卷者讀 diff 與 ledger |
| TC-065 | 作法 3（不需要 migration）；專長守則 | 不在範圍 | 本片完成後 | 看 diff | 沒有資料庫或資料結構的變動、沒有 migration 檔；計畫已明寫「不需要 migration」的理由 | 手動：閱卷者讀 diff |
| TC-066 | 完成標準；專長守則（對等性） | 不在範圍 | 本片完成後 | 跑既有的 MCP 工具數與使用者可見動作對應測試 | MCP 工具數仍是 12，沒有新增任何使用者可見的動作或路由；既有對等性測試仍綠 | 自動：既有測試（`tests/platform_test.sh` 涵蓋） |
| TC-067 | 完成標準（手動：ledger 核對） | 功能 | 看 ledger | 找 `gcloud storage rm --help` 與官方文件的核對 | ledger 寫明並附網址：①`rm --recursive` 的結尾斜線只刪該前綴、不波及 `work2/`、`work-keep`；②`ls` 對不存在前綴的結束碼與訊息；③`--project` 對 `rm` 可用；④`ps` 沿用 `run_cancel` 已在用的形式。任何一項與計畫假設不符，ledger 必須寫「停手回報」而不是繼續 | 手動：閱卷者讀 ledger |
| TC-068 | 範圍（既有斷言只准改指定那幾條） | 不在範圍 | 比對基底與本片的測試檔 | 逐一比對 `test_station_clean.py`、`test_gcb_ce.py`、`test_cloud_upload.py`、`test_gcb_launch.py` | 除 TC-056、TC-061、TC-062 所述之外，沒有任何斷言被刪除、放寬、跳過或把預期值改成配合新輸出；`test_gcb_launch.py` 完全沒改；`spec`／`test-case*.md` 在實作中沒被改 | 手動：閱卷者讀 diff |

## 憲法與安全網

本片碰到：原則 1（`test_scope.py` TC-070，新檔檔頭規則）、原則 2（`test_scope.py` TC-071，平台不啟動程式）、安全網「刪除 `work/` 需使用者明確確認」與「每個寫入都要本人答應」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-069 | 原則 1（TC-070） | 功能 | 本片完成後 | 檢查 `test_station_clean_gcb.py` 與 `clean.py` 的檔頭 | 新測試檔前 40 行有 `# Nothing existing: …` 且理由至少 15 字；`clean.py` 檔頭的理由把 `gcloud storage rm`「不核對路徑與前綴」納入；`test_scope.py` 的 TC-070 仍綠 | 自動：`platform/tests/test_scope.py` |
| TC-070 | 原則 2（TC-071） | 功能 | 本片完成後 | 跑 `test_scope.py` 的 TC-071 與 TC-061 | 仍綠：`abf_platform/` 沒有啟動程式的程式碼，`gcloud` 沒有從平台端被呼叫 | 自動：`platform/tests/test_scope.py` |
| TC-071 | 安全網（刪 work 要本人確認）；憲法 6／ADR 0006 | 例外 | 標準情境；使用者確認的是 `work=gs://lab-bucket/work/runs/r1/work` 的內容包，之後有人把內容包的 `work` 改成另一個看起來合法的路徑（`gs://lab-bucket/work/runs/r2/work`） | 執行清理 | 因為內容與使用者確認時不同（雜湊不符）被拒絕；零呼叫；r1 與 r2 的物件都沒被刪 | 自動：`platform/tests/test_station_clean_gcb.py` |
