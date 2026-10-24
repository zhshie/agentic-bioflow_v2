# nano4 acceptance table (blank template)

> 依 2026-10-22 計畫撰寫；實機跑時以當時 v3 為準。

**How to use.** This file is a blank template and stays blank. Each time someone runs the acceptance on nano4 (the maintainer first, colleagues later), copy it to `specs/007b-launch/acceptance-nano4-<date>-<name>.md` and fill in the copy. Steps and expected outputs are in `docs/TESTING.md`, section "nano4 acceptance" (TC-047n to TC-051n). Leave a cell empty if you did not do that step, and say why in 備註. Write real values only; never paste a token.

First acceptance: Claude Desktop only.

| Row | What to write |
|---|---|
| 網頁路徑：M2 | Not checked now. Left for milestone M2 (the web page, click-only, whole flow). Do not fill in. |

## 1. Run

| 欄位 | 填寫 |
|---|---|
| 日期 | 2026-10-24 |
| 填表人 | developer-agent（依自己的 run 紀錄代填）；啟動確認人 zhshie（2026-10-24 11:14:20 在確認頁按下） |
| 走哪條路（二選一：國網模組／自裝 Nextflow） | 未記錄（紀錄只寫計算環境 nano4，沒寫走國網模組還是自裝 Nextflow） |
| 說明 | 「國網模組」＝用國網提供的 Nextflow 模組。「自裝 Nextflow」＝在 `/work/<site_user>` 自己裝 Nextflow 與插件（週四國網路徑跑不通時才走）。 |

## 2. Preflight (TC-047n): fill `pass`, `fail` or `unchecked`

r4 因共用 ssh 連線過期，在 preflight 被拒、什麼都沒建立；r5 沒留逐項輸出，所以十一項都寫未記錄。

| 項目 | 結果 |
|---|---|
| `connect` | 未記錄 |
| `work_dir` | 未記錄 |
| `sbatch` | 未記錄 |
| `squeue` | 未記錄 |
| `sinfo` | 未記錄 |
| `java` | 未記錄 |
| `nextflow` | 未記錄 |
| `head_queue` | 未記錄 |
| `modules`（preflight-nano4 合併後） | 未記錄 |
| `site_pipeline`（preflight-nano4 合併後） | 未記錄 |
| `library`（preflight-nano4 合併後） | 未記錄 |

## 3. SU (TC-048n step 1 and TC-050n step 4)

`wallet` is the NCHC command that shows your SU balance. Run it on nano4: `wallet`. 差額 ＝ wallet 前 減 wallet 後 (before minus after).

| 欄位 | 填寫 |
|---|---|
| launch 前預估 SU（Claude Desktop 問 get_run 前一次同設定 run 的 su；貼上 su 整段；是 null 就寫「unknown」加 unknown_reasons） | 未記錄 |
| wallet 前（`wallet` 全文） | 未記錄（wallet 沒讀） |
| wallet 後（`wallet` 全文） | 未記錄（wallet 沒讀） |
| 差額（前 減 後） | 未記錄（wallet 沒讀） |

## 4. Launch (TC-048n)

| 欄位 | 填寫 |
|---|---|
| run 名稱與 `<rid>` | run 名稱 `ampliseq_day5_nano4_r5`；平台 run id `ae0d52e5e5fe5a98`（填在 `<rid>` 位置，是平台 run id；與確認頁網址 `/c/<rid>` 是否同一個值：未記錄）。nf-core/ampliseq 2.18.0，計算環境 `nano4`，由 Claude Desktop 經平台 MCP 連接器送出。 |
| `head.sh` 全文（貼上） | 未記錄 |
| `squeue` 輸出（`squeue -u $USER -o '%i %P %j %T'`；head 應在 `ngsconsole`，子作業在 ngs） | 未記錄（整段輸出）；僅記 Slurm head 作業 606916 在 partition `ngsconsole`。 |

## 5. Way back (TC-049n)

| 欄位 | 填寫 |
|---|---|
| 計算節點 curl 輸出（應為 401，且有 `X-ABF-Platform`） | 未記錄 |
| `abf-platform launches` 的 `way_back`（應為 `direct`） | 未記錄 |
| `ss -ltnp \| grep -c <relay port>`（應為 0） | 未記錄 |

## 6. Trace and result page (TC-050n)

| 欄位 | 填寫 |
|---|---|
| trace 行數（`tail -n +2 <run folder>/trace.txt \| wc -l`） | 未記錄（`trace.txt` 行數沒數）。平台收到了 Nextflow trace 事件。 |
| 結果頁截圖檔名 | 未記錄 |

## 7. Tokens must not leak (TC-050n step 5)

Both must print 0. `tower.token` itself is not scanned (that is where the token belongs).

| 欄位 | 填寫 |
|---|---|
| `grep -c token <run folder>/head.sh`（應為 0） | 未記錄 |
| `grep -c token <run folder>/slurm-<jobid>.out`（應為 0） | 未記錄 |

## 8. Fallback (TC-051n)

| 欄位 | 填寫 |
|---|---|
| 用的 revision、`head.sh` 的 `nextflow run ... -r ...` 那一行 | 未記錄（本次沒做 TC-051n） |

## 9. 備註

| 欄位 | 填寫 |
|---|---|
| 備註 | 完成：Nextflow log「Pipeline completed successfully」12:00:31；WorkflowStats succeededCount=71、failedCount=1（一個 task OUT_OF_MEMORY，自動重試後成功）；head 作業 606916 狀態 COMPLETED，耗時 00:46:06。<br>SU 實測（代替 wallet 差額）：11:10–12:05 之間共 73 個 Slurm 作業合計 3.288 核心小時（ngs125g 0.800、ngs62g 1.174、ngsconsole 0.768、ngs16g 0.411、ngs8g 0.135），ngs 每核心小時 1 SU，約 3.3 SU；依 repo 站台費率 `nano4.twd_per_su.nstc = 0.1`，約 NT$0.33。量法：`sacct -X` 的 ElapsedRaw × AllocCPUS。<br>結果資料夾內容：barrnap、cutadapt、dada2、fastqc、input、multiqc、overall_summary.tsv、phyloseq、pipeline_info、qiime2、summary_report、treesummarizedexperiment。<br>前史：r1–r3（2026-10-23／24）因四個站台問題失敗，已由 PR #181 修（nf-tower 插件目錄、NFCORE_SITE_REFERENCES、ref_taxonomy_storage、站台 singularity 映像壞）；r4 因共用 ssh 連線過期，在 preflight 被拒、未建立任何東西。<br>未做／未記錄的步驟照上面各節標「未記錄」；第一次驗收只走 Claude Desktop，網頁路徑留 M2。 |
