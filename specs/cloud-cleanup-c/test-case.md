# 測試案例：代理替 Slurm（nano4）的 run 刪掉那個叫 work 的目錄（cloud-cleanup-c）

**規格**：`specs/cloud-cleanup-c/plan.md`（本功能沒有 spec.md，以 plan.md 的目標、作法、手算範例與「維護者原話」為準）　**總覽**：`test-case-overview.md`

白話名詞：「work 目錄」＝Nextflow 放每個 task 中間檔的 `work/`，不是結果。「代理」＝跑在使用者那邊、替平台碰叢集的小程式。「run 資料夾」＝`<workDir>/runs/<名稱>`，裡面有 `results/`、`work/`、`head.sh` 等。「確認憑證」＝使用者按「確認刪除」後平台附上的那張單子，代理第一步就驗它。「內容包」＝那張單子裡存的資料（bundle），`clean_work` 的內容包鍵恰為 `version`、`run_name`、`slurm_job_id`、`run_folder`、`agent`、`ce`、`work`。「假站台」＝測試用的假叢集（`FakeSite`），有真的檔案系統，可以看到到底刪了什麼。「捷徑」＝符號連結。「結束碼」＝那一條遠端指令回報的數字，11 到 20 各代表一項核對不符。

本片只寫代理端；平台此刻還不會送出這種工作，所以使用者看不到任何變化。以下所有工作都是測試手工做出來交給代理的。

**標準環境**（除非該列另外寫明）：`workDir=/work/u1/abf`，`site_user=tester`，資料夾 `F=/work/u1/abf/runs/ampliseq-d5`，run 名稱 `ampliseq-d5`；假站台上 `F/work`（內有一些檔案）、`F/results`、`/work/u1/abf/rawdata`、`/work/u1/abf/analysis`（後兩者與 results 各放一個 `guard.txt`）都真的存在；工作帶有齊全且相符的確認憑證與雜湊；`work` 的擁有者就是 `site_user`；`squeue` 查不到該使用者在 F 的工作。（路徑在假站台上以等價的暫存路徑代入。）

**「拒絕」的意思**：代理回的狀態是 `refused`（拒絕），訊息是白話、非空、不含堆疊；凡是標「路徑類／內容類拒絕」的列，另外必須 `site.calls()` 沒有任何遠端指令、`site.destructive()` 為空。標「叢集端拒絕（碼 N）」的列，遠端指令恰好送出一條，`site.destructive()` 為空（沒有任何 `rm`），且訊息含「沒有改動任何東西」。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者或資料做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「不支援」。

維護者原話對照（逐字，出自計畫「維護者原話」）：
- 「跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪」→ TC-001 到 TC-006（沒有確認就一條遠端指令都不送）、TC-045／TC-048（刪的是中間檔、結果不在範圍）、TC-074（代理自己不會「自動」清理）。
- 「C-7 `cloud-cleanup`（B／backend）：succeeded 後建『刪除 work 目錄』的待確認請求（走 `_ask`，新 kind `clean_work`；對 nano4 也適用）」→ TC-009、TC-026、TC-027（種類名恰為 `clean_work`；Slurm 環境能走完）。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」→ TC-030、TC-031、TC-032、TC-033、TC-035、TC-037、TC-064、TC-086（含這些字或最後一段不是 `work`，一律拒絕，沒有旗標可關：TC-069）。
- 「網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併」→ TC-075、TC-079（本片無網頁畫面、只動計畫列的檔）。
- 「平台不啟動程式」（`test_scope.py` TC-071）→ TC-085、TC-089（`rm -rf` 這串字在整個 `abf_station/` 只出現在 `clean.py`，平台端沒有）。
- 「每個寫入要本人答應」→ TC-001 到 TC-008（代理端第一步永遠是驗確認憑證）。

專長守則（backend）對照：確認管道 TC＝TC-001～TC-005、TC-008；錯誤訊息與日誌 TC＝TC-007、TC-059、TC-060、TC-065、TC-066；對等性 TC＝TC-026；migration 說明＝TC-077；代理層沒有「使用者」概念，跨使用者的對應項是「work 的擁有者必須是 site_user」（TC-055）與「別的代理的工作被拒」（TC-012），使用者隔離本身屬 b 片平台端。

## User Story 1 — 沒有本人確認，代理什麼都不做（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 2.1；原話 16「經本人確認」 | 例外 | 標準環境，但工作的 `args` 沒有 `confirmation_id` | 把工作交給代理 | 拒絕；假站台沒有收到任何遠端指令（含 squeue）；`destructive()` 為空；`F/work` 仍在 | 自動：`platform/tests/test_station_clean.py` |
| TC-002 | 作法 2.1；原話 16 | 例外 | 標準環境，內容包在確認之後被改過一個字元（雜湊不符） | 交給代理 | 拒絕，訊息說內容與確認時不符；一條遠端指令都不送；`destructive()` 為空 | 自動 |
| TC-003 | 作法 2.1；原話 16 | 例外 | 標準環境，確認憑證的紀錄已標為用過（`used_at` 有值） | 交給代理 | 拒絕；一條遠端指令都不送；`destructive()` 為空 | 自動 |
| TC-004 | 作法 2.1；原話 16 | 例外 | 標準環境，憑證種類是 `launch`（一張啟動用的憑證） | 交給代理 | 拒絕，訊息說憑證種類不符；一條遠端指令都不送；`destructive()` 為空 | 自動 |
| TC-005 | 作法 2.1；原話 16 | 例外 | 標準環境，憑證種類是 `cancel`（一張取消用的憑證） | 交給代理 | 拒絕，訊息說憑證種類不符；一條遠端指令都不送；`destructive()` 為空 | 自動 |
| TC-006 | 計畫測試「同一份確認的第二次執行被拒」 | 例外 | 標準環境，同一個代理（同一個 `ctx`）已用這張憑證成功清過一次 | 把同一個工作再交給代理一次 | 第二次拒絕（憑證已用過）；整個過程 `destructive()` 只有第一次的那一行；遠端指令總共只送過一條 | 自動 |
| TC-007 | 專長守則：錯誤訊息 | 例外 | TC-001 到 TC-005 的五種未確認情形 | 讀代理回的訊息 | 每一則都用白話說出缺了什麼（沒有確認、內容不符、種類不符、已用過其中之一），不含 `Traceback`、不含代理自己的原始碼路徑 | 自動 |
| TC-008 | 憲法「每個寫入要本人答應」；作法 2.1（第一步永遠是驗確認） | 例外 | 一個沒有確認憑證、而且內容包也是惡意的工作（run 名稱含 `;`、work 指向 `results`） | 交給代理 | 拒絕的原因是「沒有確認憑證」，而不是內容包問題（證明驗憑證在所有其他核對之前）；沒有任何遠端指令 | 自動 |
| TC-009 | 原話 C-7「對 nano4 也適用」；作法 2 全部通過 | 功能 | 標準環境，確認憑證種類為 `clean_work`、雜湊相符、尚未用過 | 交給代理 | 通過確認這一關並往下做：恰好送出一條遠端指令（下一步見 TC-045） | 自動 |

## User Story 2 — 內容包、身分、部署設定、期限與工作種類（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 作法 2.2：鍵集合恰為 `KEYS` | 例外 | 標準環境，內容包多一個鍵（例如 `delete_results`），憑證與雜湊照新內容重算而相符 | 交給代理 | 路徑類／內容類拒絕，訊息說內容包欄位不對 | 自動 |
| TC-011 | 作法 2.2：鍵集合恰為 `KEYS` | 例外 | 標準環境，內容包缺一個鍵（拿掉 `work`），雜湊相符 | 交給代理 | 路徑類／內容類拒絕 | 自動 |
| TC-012 | 作法 2.2：`agent` 要等於本代理名稱 | 例外 | 標準環境，內容包的 `agent` 是另一個代理的名字，雜湊相符 | 交給代理 | 路徑類／內容類拒絕，訊息說這是給另一個代理的 | 自動 |
| TC-013 | 作法 2.2；「不做」Google Batch（d 片） | 不在範圍 | 內容包的 `ce.platform` 是 Google Batch，其餘合格，雜湊相符 | 交給代理 | 拒絕，訊息明白說「Google Batch 的清理尚未支援」並指出 cloud-cleanup-d；一條遠端指令都不送；`destructive()` 為空 | 自動 |
| TC-014 | 作法 2.2：其他非 Slurm 由 `rules.clean_environment` 拒 | 例外 | 內容包的 `ce.platform` 是 Slurm 與 Google Batch 以外的值，雜湊相符 | 交給代理 | 路徑類／內容類拒絕，訊息說只有 Slurm 環境能做 | 自動 |
| TC-015 | 作法 2.3 | 例外 | 內容包的 `ce` 是空值、字串或缺少，雜湊相符（三種各一次） | 交給代理 | 三次都是路徑類／內容類拒絕；沒有未處理的例外（代理不當掉） | 自動 |
| TC-016 | 計畫測試「惡意名稱」；作法 2.3 | 例外 | 標準環境，`run_name`（連同 `run_folder` 的最後一段）依序換成：含空白、含 `;`、含 `$()`、含反引號、含換行、含 BIDI 控制字元、65 字元過長、`..`；雜湊每次重算相符 | 各交給代理一次 | 八次全是路徑類／內容類拒絕 | 自動（參數化） |
| TC-017 | 計畫測試「惡意 workDir」；作法 2.3 | 例外 | 內容包 `ce.workDir` 依序換成含空白、`;`、`$()`、反引號、換行、BIDI 字元、`..`、結尾斜線、相對路徑、`/`；雜湊相符 | 各交給代理一次 | 全部路徑類／內容類拒絕 | 自動（參數化） |
| TC-018 | 計畫測試「惡意 folder」；作法 2.4 | 例外 | `run_folder`（與相符的 `work`）依序換成含空白、`;`、`$()`、反引號、換行、BIDI 字元、`..`；雜湊相符 | 各交給代理一次 | 全部路徑類／內容類拒絕 | 自動（參數化） |
| TC-019 | 作法 2.3：`slurm_job_id` 是 1 到 2^31-1 的整數（非布林） | 例外 | 標準環境，`slurm_job_id` 依序為 `True`、`0`、`-1`、`2147483648`、字串 `"123"`、`None`；雜湊相符 | 各交給代理一次 | 全部路徑類／內容類拒絕 | 自動（參數化） |
| TC-020 | 作法 2.5；計畫測試「沒有 site_user」 | 例外 | 標準環境，但部署設定檔沒有 `site_user`（也沒有可退回的 `site_host`） | 交給代理 | 拒絕，訊息白話說「部署設定沒有 site_user」；一條遠端指令都不送 | 自動 |
| TC-021 | 作法 2.5：site_user 要符合 `^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z` | 例外 | 標準環境，`site_user` 設成含空白或含 `;` 的值 | 交給代理 | 拒絕；一條遠端指令都不送 | 自動 |
| TC-022 | 作法 2.6：期限不足；計畫測試 | 例外 | 標準環境，工作的剩餘期限低於代理的最小剩餘（預設 60 秒），例如剩 30 秒 | 交給代理 | 拒絕（期限不夠）；一條遠端指令都不送；`destructive()` 為空 | 自動 |
| TC-023 | 作法 2.6：遠端指令逾時 `int(min(300, left - 15))` | 功能 | 標準環境，工作剩餘期限分別為 1000 秒與 100 秒 | 各交給代理一次，觀察送去站台的那一次呼叫所帶的逾時值 | 剩 1000 秒時逾時值是 300；剩 100 秒時逾時值約為 85（`int(100 - 已用掉的時間 - 15)`，不超過 85、不小於 84）；兩次都沒有第二次呼叫 | 自動 |
| TC-024 | 計畫測試「額外參數仍被拒」；`ARG_KEYS` | 例外 | 一個 `clean_work` 工作，`args` 除 `bundle`、`confirmation_id`、`bundle_sha256` 之外多一個鍵（例如 `force`） | 交給代理（走 `handlers.handle`） | 拒絕，說這個工作帶了代理不收的參數；一條遠端指令都不送 | 自動 |
| TC-025 | 計畫測試「仍拒絕不認得的種類」 | 例外 | 一個種類為 `clean_work2`（或 `clean_all`）的工作 | 交給 `handlers.handle` | 拒絕；訊息的「代理做的種類」清單含 `clean_work` | 自動 |
| TC-026 | 專長守則：對等性；作法 handlers | 功能 | 載入 `handlers` | 同時列舉 `JOB_KINDS` 與 `ARG_KEYS` 的鍵，並對每個種類各送一個空工作看分派 | 兩邊集合相等（缺一邊就失敗）；`clean_work` 在兩邊；`clean_work` 的工作被分派到 `clean.run_clean`（不是落到「不支援」） | 自動 |
| TC-027 | 作法 handlers：`ARG_KEYS["clean_work"] == launch.LAUNCH_KEYS` | 功能 | 載入 `handlers` 與 `launch` | 比較 | `ARG_KEYS["clean_work"]` 恰等於 `{bundle, confirmation_id, bundle_sha256}` | 自動 |
| TC-028 | 作法 handlers：不動其他種類 | 功能 | 載入 `handlers` | 比對既有六個種類 | `preflight`、`list_site_files`、`launch_nextflow`、`cancel_run`、`fetch_run_records`、`read_task_log` 的名稱與各自的 `ARG_KEYS` 與本片之前一字不差；`clean_work` 是第七個 | 自動 |

## User Story 3 — 路徑由代理重算並逐字比對（優先度 P1）

這一節每一列都是「路徑類拒絕」（一條遠端指令都不送、`destructive()` 為空），除了標「功能」的兩列。「重算值」＝`F + "/work"`。對應計畫手算範例的編號寫在「對應需求」欄。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 手算範例 2 | 例外 | 標準環境；內容包 `work=F/work/`（結尾多一個斜線） | 交給代理 | 拒絕：不是逐字相等 | 自動：`test_station_clean.py`（表格參數化） |
| TC-030 | 手算範例 3；原話「擋住 results」 | 例外 | 內容包 `work=F/results` | 交給代理 | 拒絕：含 `results`、最後一段不是 `work`；`F/results` 內容不變 | 自動 |
| TC-031 | 手算範例 4 | 例外 | 內容包 `work=F/work/../results` | 交給代理 | 拒絕：含 `..`；`F/results` 內容不變 | 自動 |
| TC-032 | 手算範例 5；原話「擋住 rawdata」 | 例外 | 內容包 `work=/work/u1/abf/rawdata` | 交給代理 | 拒絕：含 `rawdata`、不等於重算值；`rawdata/guard.txt` 位元不變 | 自動 |
| TC-033 | 手算範例 6 | 例外 | 內容包 `work=F`（整個 run 資料夾） | 交給代理 | 拒絕：最後一段不是 `work`；整個 F 完好 | 自動 |
| TC-034 | 手算範例 7 | 例外 | 內容包 `work=/work/u1/abf/runs/other-run/work`，但 `run_folder` 仍是 F | 交給代理 | 拒絕：與重算值不同；`other-run/work`（若存在）與 `F/work` 都不被碰 | 自動 |
| TC-035 | 手算範例 8；原話「擋住 analysis」 | 例外 | 內容包 `work=/work/u1/abf/analysis/work` | 交給代理 | 拒絕：含 `analysis`；`analysis/guard.txt` 位元不變 | 自動 |
| TC-036 | 手算範例 17 | 例外 | run 名稱 `other-a2`，`run_folder=F`（leaf 為 `ampliseq-d5`），`work=F/work` | 交給代理 | 拒絕：名稱與資料夾的最後一段對不上（既不等於 leaf，也不是 leaf 加 `-aN` 的截斷公式） | 自動 |
| TC-037 | 手算範例 19 | 例外 | `workDir=/work/u1/results/abf`，`run_folder` 與 `work` 照它組出 | 交給代理 | 拒絕：路徑含 `results` 這一段（刻意保守） | 自動 |
| TC-038 | 手算範例 21 | 例外 | `run_folder=/work/u1/abf/runs/x/y`，`work=…/runs/x/y/work` | 交給代理 | 拒絕：不是 `workDir/runs/<名稱>` 的形狀 | 自動 |
| TC-039 | 手算範例 16；作法 2.4「續跑用原資料夾」 | 功能 | run 名稱 `ampliseq-d5-a2`，`run_folder=F`，`work=F/work`，其餘標準 | 交給代理 | 刪除成功（狀態 `done`、`cleaned` 為 true）；`F/work` 消失；`F/results` 不動 | 自動 |
| TC-040 | 手算範例 18 | 功能 | 一個 64 字元的資料夾名稱 `L`（`run_folder=…/runs/L`），run 名稱為 `L` 前 61 字元加 `-a2`（共 64 字元） | 交給代理 | 刪除成功；該資料夾的 `work` 消失 | 自動 |
| TC-041 | 作法 2.4：續跑次數 N 至少 2 | 例外 | run 名稱 `ampliseq-d5-a1`（對應資料夾 F），其餘標準 | 交給代理 | 拒絕（`-a1` 不是續跑那一次） | 自動 |
| TC-042 | 作法 2.4：不容許結尾斜線 | 例外 | `run_folder=F/`（結尾斜線），`work=F//work` 與 `work=F/work` 各一次 | 各交給代理一次 | 兩次都拒絕 | 自動 |
| TC-043 | 作法 2.4：`normalize(folder) == folder` | 例外 | `run_folder` 依序為 `/work/u1/abf/runs/./ampliseq-d5`、`/work/u1/abf//runs/ampliseq-d5` | 各交給代理一次 | 兩次都拒絕（不正規化、不替人修） | 自動（參數化） |
| TC-044 | 作法 2.4：work 的各段不得有 `.` | 例外 | 內容包 `work=F/./work` | 交給代理 | 拒絕 | 自動 |

## User Story 4 — 叢集端核對、真的刪、與結束碼（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-045 | 手算範例 1；作法 2.9 | 功能 | 標準環境，`work=F/work` | 交給代理 | 狀態 `done`；結果含 `ok: true`、`cleaned: true`、`run_name=ampliseq-d5`；訊息為「已刪除 <F>/work；results 沒有動」；假站台上 `F/work` 已不存在，`F/results` 仍在 | 自動 |
| TC-046 | 作法 2.7：只送一條遠端指令 | 功能 | 同 TC-045 | 交給代理後看 `site.calls()` | 恰好一個 `on_site` 呼叫（整個清理只問叢集一次） | 自動 |
| TC-047 | 作法 2.7；手算範例 1；計畫測試「一次 rm、對象只有 work」 | 功能 | 同 TC-045 | 看 `site.destructive()` | 恰好一行；那一行是 `rm -rf --one-file-system -- work`：對象是字面的 `work`，含 `--one-file-system`，沒有 `*`、沒有 `$`、沒有絕對路徑 | 自動 |
| TC-048 | 計畫測試「work 之外的東西位元不變」；「不做」 | 功能 | 標準環境；清理前對整個 workDir 做 `snapshot` | 清理成功後再 `snapshot` | `results/`、`rawdata/`、`analysis/`（含各自的 `guard.txt`）、run 資料夾本身、`head.sh`、`.nextflow*`、`slurm-*.out`（先放進去）與 `work` 之外所有檔案，內容與權限位元級不變；只有 `F/work` 這一棵樹少了 | 自動 |
| TC-049 | 手算範例 11；作法 3 | 功能 | `F/work` 內有一個連到 `/work/u1/abf/rawdata/x.fastq.gz` 的連結 | 交給代理 | 刪除成功；連結被刪掉，但 `rawdata/x.fastq.gz` 還在且位元不變（只刪連結、不跟進去） | 自動 |
| TC-050 | 手算範例 14（碼 20） | 功能 | 標準環境，但叢集上 `F/work` 不存在 | 交給代理 | 狀態 `done`、`cleaned: true`；`destructive()` 為空（沒有刪任何東西）；其餘檔案不變 | 自動 |
| TC-051 | 手算範例 9（碼 14） | 例外 | 叢集上 `F/work` 其實是一個連到 `F/results` 的連結 | 交給代理 | 叢集端拒絕（碼 14），訊息說 `work` 本身是捷徑；`F/results` 內容與那個連結都沒有被動 | 自動 |
| TC-052 | 手算範例 10（碼 12） | 例外 | 叢集上 F 的上層（例如 `runs`）被換成連到別處的連結，使 `realpath .` 不等於 F | 交給代理 | 叢集端拒絕（碼 12），訊息說資料夾本身或上層是捷徑；連結另一端的內容不變 | 自動 |
| TC-053 | 手算範例 12（碼 17） | 例外 | `F/results/a.tsv` 是連到 `F/work/ab/cdef/a.tsv` 的連結 | 交給代理 | 叢集端拒絕（碼 17），訊息說 results 裡有指向 work 的捷徑、刪了結果會壞；`work` 與 `results` 都完好 | 自動 |
| TC-054 | 手算範例 13（碼 13） | 例外 | 假 `squeue -u tester -o %Z` 列出 `F`（該使用者還有工作在這個資料夾裡跑） | 交給代理 | 叢集端拒絕（碼 13），訊息說這個資料夾裡還有 Slurm 工作；`work` 完好 | 自動 |
| TC-055 | 手算範例 15（碼 16）；專長守則：擁有者規則 | 例外 | `F/work` 的擁有者不是 `site_user`（假站台上讓兩者不同） | 交給代理 | 叢集端拒絕（碼 16），訊息說 `work` 不是你的；`work` 完好 | 自動 |
| TC-056 | 手算範例 20（碼 18） | 例外 | 假站台的 `squeue` 失敗（`squeue_fail`） | 交給代理 | 叢集端拒絕（碼 18），訊息說問不到 Slurm 佇列、無法確認工作已結束；`work` 完好 | 自動 |
| TC-057 | 作法 2.8：碼 11 | 例外 | 叢集上 run 資料夾 F 不存在（進不去） | 交給代理 | 叢集端拒絕（碼 11），訊息說進不了資料夾；`destructive()` 為空 | 自動 |
| TC-058 | 作法 2.8：拒絕訊息含「沒有改動任何東西」 | 例外 | 碼 11、12、13、14、16、17、18 各一個情境（碼 15 見 TC-059；碼 15 的情境若假站台造得出來也列入） | 逐一交給代理，讀訊息 | 每一則都是 `refused`，且含「沒有改動任何東西」 | 自動（參數化） |
| TC-059 | 作法 2.8：每個碼一句白話、指出哪一項不符 | 例外 | 用假站台直接回報結束碼 11 到 18（含 15） | 逐一讀代理的答覆 | 八個碼的訊息兩兩不同，各自指出是哪一項核對不符（進不去、捷徑、有工作在跑、work 是捷徑、真實位置不對、擁有者不對、results 有連結、問不到佇列） | 自動（參數化） |
| TC-060 | 作法 2.9：不轉貼站台原始輸出 | 例外 | 假站台在標準輸出與錯誤輸出各印一串可辨認的字（例如 `SECRET-RAW-OUT-12345`），分別搭配結束碼 0、13、99 | 交給代理，讀完整答覆 | 三種答覆都不含那串字 | 自動 |
| TC-061 | 作法 2.7：固定樣板、只有三個值會變 | 功能 | 兩組不同的 `folder`、`user`（各含一個需要引號的字元如 `-`、`.`）執行兩次 | 取代理送出的那條指令字串，把 `folder`、`user`、`folder + "/work"` 三個值換成佔位符 | 兩次得到同一個樣板，且與計畫第 2.7 節的十行逐行對得上（cd、realpath、squeue、grep、test -d、test ! -L、realpath work、stat、find、rm）；刪除的對象是字面 `work` | 自動 |
| TC-062 | 作法 2.8：逾時 | 例外 | 假站台讓那一條遠端指令超過逾時（回 `timed_out`） | 交給代理 | 狀態 `error`；訊息含「逾時」與「可能只刪了一部分」；遠端指令總共只送了一條（沒有重試） | 自動 |
| TC-063 | 作法 2.8：其他非零結束碼 | 例外 | 假站台那條指令回結束碼 99 | 交給代理 | 狀態 `error`；訊息含結束碼 99 與「可能只刪了一部分；work_cleaned_at 沒記，可以再申請」；遠端指令只送一條，不重試 | 自動 |
| TC-064 | 原話「直接 scancel … 一律擋住」；憲法掃描 | 功能 | 標準環境（成功案例）與 TC-051 到 TC-056 的拒絕案例 | 看假站台的 `dangerous()` | 全部為空：沒有 `scancel`、`sbatch`、`srun`、`nextflow run` | 自動 |
| TC-065 | 專長守則：錯誤訊息不露堆疊與內部路徑 | 例外 | TC-051 到 TC-063 所有拒絕與 error 的答覆 | 讀答覆全文 | 不含 `Traceback`、不含代理原始碼路徑；error 的答覆說明發生什麼事，以及可以再申請 | 自動 |
| TC-066 | 專長守則：密鑰不在日誌與答覆 | 例外 | 在部署設定檔放一個代理不會用到的假密鑰（例如 `fake_token = SECRET-TOKEN-98765`），跑一次成功與一次拒絕 | 蒐集代理的答覆與 `Site` 的日誌輸出 | 全文都不含 `SECRET-TOKEN-98765` | 自動 |
| TC-067 | 範圍：假 `squeue` 新增 `-u <user> -o %Z` | 功能 | 假站台登錄三個工作：兩個屬 `tester`（工作目錄 `F1`、`F2`）、一個屬 `other`（`F3`） | 執行 `squeue -h -u tester -o %Z` | 輸出恰為兩行，一行一個工作目錄（`F1`、`F2`），沒有 `F3`、沒有名稱與使用者欄；`squeue_fail` 開著時仍失敗 | 自動 |
| TC-068 | 範圍：既有 `-j`、`-n` 行為與輸出不動 | 功能 | 同一個假站台，登錄數個工作 | 執行 `squeue -h -j <編號>` 與 `squeue -h -n <名稱>` | 輸出仍是 `名稱｜使用者｜工作目錄` 的格式，內容與本片之前相同（與 base 比對） | 自動 |

## User Story 5 — 不在範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-069 | 「不做」：不做刪整個 run／刪結果的選項，也不做旗標 | 不在範圍 | 標準環境；工作的 `args` 加 `force`／`delete_results`／`all`（各一次），內容包也各加一個同名鍵（雜湊相符） | 交給代理 | 全部拒絕；`destructive()` 為空；沒有任何設定或環境變數能讓 `rawdata`／`results`／`analysis` 規則失效 | 自動 |
| TC-070 | 「不做」：不做批次清、部分清 | 不在範圍 | 內容包的 `work` 是兩個路徑組成的清單，或是 `F/work/ab` 這種 work 內部的某幾個 task 目錄 | 交給代理 | 拒絕；`destructive()` 為空 | 自動 |
| TC-071 | 「不做」：不用 `nextflow clean` | 不在範圍 | 標準環境成功案例 | 看 `site.calls()` 與那條指令 | 沒有任何 `nextflow` 程式被呼叫；指令字串不含 `nextflow` | 自動 |
| TC-072 | 「不做」：不重試、不加迴圈、不加執行緒 | 不在範圍 | `clean.py` 原始碼；TC-056、TC-062、TC-063 的失敗情境 | 掃原始碼找 `while`、`Thread`、`sleep`、`retry`；看失敗情境的呼叫數 | 原始碼沒有；每個失敗情境遠端指令都只送一條 | 自動 |
| TC-073 | 「不做」：不新增 `site` 呼叫方式 | 不在範圍 | `clean.py` 原始碼 | 掃原始碼 | 不 import `subprocess`、不用 `os.system`／`os.popen`、不呼叫 `run_fixed`；碰叢集只透過 `ctx.site.call` | 自動 |
| TC-074 | 原話 16「不自動刪」；目標「代理自己不會自動清理」 | 不在範圍 | `abf_station/` 全部原始碼 | 找出誰呼叫 `clean.run_clean` | 只有 `handlers.handle` 對 `clean_work` 工作的分派；沒有定時、啟動時、結束時或迴圈裡的自動呼叫 | 自動 |
| TC-075 | 範圍：只准改計畫列的 5 個檔 | 不在範圍 | 本任務的最終 HEAD | `git diff --name-only <base>...HEAD` | 只有 `platform/abf_station/clean.py`、`platform/abf_station/handlers.py`、`platform/tests/station_harness.py`、`platform/tests/test_station_clean.py`、`specs/cloud-cleanup-c/ledger.md` | 手動：驗收者用 `git diff` 核對 |
| TC-076 | 範圍：禁碰檔案與既有測試檔 | 不在範圍 | 同上 | 對 `abf_station/launch.py`／`cancel.py`／`gcb_launch.py`／`gcb_preflight.py`／`site.py`／`rules.py`、`abf_platform/*`、`abf_launch/*`、`tests/no_second_run_state_test.sh`、所有既有測試檔看 diff | 全部沒有改動；`station_harness.py` 的改動只有加 `-u`／`%Z` 的假 `squeue` 支援，其餘位元不變 | 手動：驗收者用 `git diff` 核對 |
| TC-077 | 作法 4：不需要 migration（專長守則） | 不在範圍 | 同上 | 看 diff 有無資料庫結構、migration 檔 | 沒有任何資料結構或 migration 變動 | 手動：驗收者用 `git diff` 核對 |
| TC-078 | 完成標準「文件：無」 | 不在範圍 | 同上 | 看 `docs/` 有無改動 | `docs/` 沒有改動 | 手動：驗收者用 `git diff` 核對 |
| TC-079 | 完成標準：Slurm 送出、取消、續跑、畫面、`head.sh`、golden 位元級不變 | 不在範圍 | 既有測試（送出、取消、續跑、golden、`test_run_diag_tools.py`、`tests/platform_test.sh`）一律不改 | 跑全套 | 全部通過，且沒有被放寬或跳過的斷言（`test_run_diag_tools.py:466` 的成員檢查仍過） | 自動：`tests/platform_test.sh` 與整個 `platform/tests/` |

## User Story 6 — 交代紀錄（ledger）（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 完成標準：假站台與真叢集的已知差異 | 功能 | `specs/cloud-cleanup-c/ledger.md` | 讀 ledger | 有一段寫出假站台上 `rm -rf --one-file-system`、`realpath`、`stat -c %U`、`find -lname` 的行為與真實叢集（GNU coreutils）是否一致；有疑慮的列為 f 片手動驗收的一項 | 手動：驗收者讀 ledger |
| TC-081 | 環境事實：動手前讀官方說明頁 | 功能 | 同上 | 讀 ledger | 對 `nextflow clean`、`rclone purge`、Seqera Platform 的刪除各有一個官方說明頁網址，並寫明與計畫那句理由相符（不符則應已停手回報） | 手動：驗收者讀 ledger |
| TC-082 | 完成標準：`git diff --stat` 貼進 ledger | 功能 | 同上 | 讀 ledger 並自行重跑 `git diff --stat` | ledger 有 diff 統計，且與驗收者重跑的結果一致 | 手動：驗收者核對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-083 | 原則 I 第 1 條：每個檔案說明為何要自己寫（TC-070 檔頭規則，`test_scope.py`） | 功能 | 新檔 `clean.py` 與 `test_station_clean.py` | 檢查檔案前 40 行 | 各有一行 `# Nothing existing: ` 且理由至少 15 字；`clean.py` 的理由說明 `nextflow clean`、`rclone purge`、Seqera 的刪除為何不符 | 自動：`platform/tests/test_scope.py`（檔頭掃描） |
| TC-084 | 原則 I 第 2 條：只有一個提交路徑；`LAUNCH_ALLOW` 維持一筆 | 功能 | 本片 HEAD | 跑 `tests/no_second_run_state_test.sh`，並讀 `LAUNCH_ALLOW` | 通過；`LAUNCH_ALLOW` 仍只有 `platform/abf_station/launch.py` 一筆 | 自動：`tests/no_second_run_state_test.sh` 與 `test_station_clean.py` |
| TC-085 | 憲法：平台不啟動程式；刪除由代理執行 | 功能 | `abf_station/*.py` 與 `abf_platform/*.py` | 掃 `rm -rf` 這串字 | 只出現在 `abf_station/clean.py`；`abf_platform/` 沒有 | 自動 |
| TC-086 | 安全網：絕不刪 `rawdata/`、`results/`、`analysis/`（含 `guard.txt`） | 例外 | 標準環境，對 TC-029 到 TC-038、TC-041 到 TC-044、TC-051 到 TC-056 每一種拒絕情境各跑一次 | 每次前後對 `rawdata/`、`results/`、`analysis/` 做 `snapshot` | 每一次三個資料夾（含 `guard.txt`）位元級不變 | 自動（參數化） |
| TC-087 | 憲法既有掃描：`abf_station/` 靜態規則 | 功能 | 加入 `clean.py` 之後 | 跑 `test_station_static.py` 的既有掃描 | 全部通過：沒有 `listen`／`bind`、沒有 `getpass`、沒有第二個 import `subprocess` 的模組、不含字面的 `/work/<名稱>/` 路徑、不含 `srun`／`qsub`／`bsub`／`nextflow run` | 自動：`platform/tests/test_station_static.py` |
| TC-088 | 安全網：密鑰只在部署設定區 | 功能 | 本片 HEAD | 跑 `tests/credentials_stay_in_settings_test.sh` | 通過 | 自動 |
| TC-089 | 憲法：平台不啟動程式（`test_scope.py` TC-071、TC-061） | 功能 | 本片 HEAD | 跑 `platform/tests/test_scope.py` | 通過（掃的是 `abf_platform/`，本片沒有動它） | 自動 |
| TC-090 | 完成標準：MCP 工具數仍為 12 | 功能 | 本片 HEAD | 列出平台註冊的 MCP 工具 | 恰好 12 個，與 base 相同 | 自動 |

<!--
Rules for the writer:
- 不重新編號；移除的案例保留原列並劃線。
-->
