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
| 日期 | |
| 填表人 | |
| 走哪條路（二選一：國網模組／自裝 Nextflow） | |
| 說明 | 「國網模組」＝用國網提供的 Nextflow 模組。「自裝 Nextflow」＝在 `/work/u9613010` 自己裝 Nextflow 與插件（週四國網路徑跑不通時才走）。 |

## 2. Preflight (TC-047n): fill `pass`, `fail` or `unchecked`

| 項目 | 結果 |
|---|---|
| `connect` | |
| `work_dir` | |
| `sbatch` | |
| `squeue` | |
| `sinfo` | |
| `java` | |
| `nextflow` | |
| `head_queue` | |
| `modules`（preflight-nano4 合併後） | |
| `site_pipeline`（preflight-nano4 合併後） | |
| `library`（preflight-nano4 合併後） | |

## 3. SU (TC-048n step 1 and TC-050n step 4)

`wallet` is the NCHC command that shows your SU balance. Run it on nano4: `wallet`. 差額 ＝ wallet 前 減 wallet 後 (before minus after).

| 欄位 | 填寫 |
|---|---|
| launch 前預估 SU（在 WSL 終端機呼叫 `actions.estimate_su`，指令全文見 `docs/TESTING.md` TC-048n 第 1 步；它不是 MCP 工具，Claude Desktop 打不了。貼上指令與輸出；查不到或算不出就寫「unknown」加原因） | |
| wallet 前（`wallet` 全文） | |
| wallet 後（`wallet` 全文） | |
| 差額（前 減 後） | |

## 4. Launch (TC-048n)

| 欄位 | 填寫 |
|---|---|
| run 名稱與 `<rid>` | |
| `head.sh` 全文（貼上） | |
| `squeue` 輸出（`squeue -u $USER -o '%i %P %j %T'`；head 應在 `ngsconsole`，子作業在 ngs） | |

## 5. Way back (TC-049n)

| 欄位 | 填寫 |
|---|---|
| 計算節點 curl 輸出（應為 401，且有 `X-ABF-Platform`） | |
| `abf-platform launches` 的 `way_back`（應為 `direct`） | |
| `ss -ltnp \| grep -c <relay port>`（應為 0） | |

## 6. Trace and result page (TC-050n)

| 欄位 | 填寫 |
|---|---|
| trace 行數（`tail -n +2 <run folder>/trace.txt \| wc -l`） | |
| 結果頁截圖檔名 | |

## 7. Tokens must not leak (TC-050n step 5)

Both must print 0. `tower.token` itself is not scanned (that is where the token belongs).

| 欄位 | 填寫 |
|---|---|
| `grep -c token <run folder>/head.sh`（應為 0） | |
| `grep -c token <run folder>/slurm-<jobid>.out`（應為 0） | |

## 8. Fallback (TC-051n)

| 欄位 | 填寫 |
|---|---|
| 用的 revision、`head.sh` 的 `nextflow run ... -r ...` 那一行 | |

## 9. 備註

| 欄位 | 填寫 |
|---|---|
| 備註 | |
