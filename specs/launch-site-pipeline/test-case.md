# 測試案例：站台啟動先 module load，命中 sitePipelines 用本地路徑啟動（launch-site-pipeline，M1-02）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
來源只有 `specs/launch-site-pipeline/plan.md`（含裁決 0–12）；本任務沒有 spec.md，維護者原話引自 plan「維護者原話」一節。
-->

**規格**：`specs/launch-site-pipeline/plan.md`（本任務無 spec.md）　**總覽**：`test-case-overview.md`

名詞（一句話解釋）：
- **站台（site）**：實驗室實際跑分析的叢集（這裡是國網 nano4）；**站台代理（agent）**是在站台上代使用者送出工作的程式。
- **head 腳本（head.sh）**：送到叢集上、負責啟動 Nextflow 的那份 shell 腳本；使用者在終端機確認的就是它。
- **module load**：叢集上「把某套軟體載入環境」的指令。
- **命中**：計算環境（CE，compute environment）的 `sitePipelines` 清單裡有一筆 `(pipeline, revision)` 與這次要跑的完全相同。
- **假 CE**：測試用的假計算環境，一律用裁決 1 的值：`modules=["biology/Nextflow/26.10.0"]`、`siteConfigVars=["NFCORE_SITE_CONFIG","NFCORE_SITE_REFERENCES"]`、`sitePipelines=[{"pipeline":"nf-core/ampliseq","revision":"2.18.0","module":"biology/nf-core-ampliseq/2.18.0","home":"NFCORE_AMPLISEQ_HOME"}]`（裁決 9：modules 只有 Nextflow 一項）。以下簡稱「nano4 假 CE」。
- **逐位元相同**：兩份文字連一個字元、一個換行都一樣。
- 「模擬執行」＝測試把 head 腳本放進暫存資料夾，用假的 `nextflow`、假的 `module` 指令實際用 bash 跑一次，記下它收到的參數（沿用 `test_launch_bundle.py` 的 `run_head` 做法）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

測試放哪裡：能放在範圍內的 `platform/tests/test_launch_bundle.py`、`test_station_launch.py`、`test_station_envs.py` 就放那裡；需要別的現有測試檔的框架（續跑、跨使用者、動作清單）時，在現有檔「只新增案例、不改舊案例」視為合法。每個自動測試要在註解寫 TC 編號。

## User Story 1 — 命中 sitePipelines：先 module load，用本地路徑啟動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LS-01 | plan「失敗先行測試」`test_tc013b_a_…`；裁決 1 | 功能 | nano4 假 CE；pipeline `nf-core/ampliseq`、revision `2.18.0` | 組出啟動內容包（bundle），讀 `files["head.sh"]` | 含 `module load biology/Nextflow/26.10.0`、含 `module load biology/nf-core-ampliseq/2.18.0`、含 `exec nextflow run "$NFCORE_AMPLISEQ_HOME"`，且整份腳本不含 ` -r `（前後各一空白的 -r） | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-02 | plan「完成標準」；裁決 3（golden） | 功能 | 同 TC-LS-01 | 組出 head 腳本，與 `fixtures/golden_head_scripts.json` 的 `nano4` 鍵比對 | golden 檔新增 `nano4` 鍵；組出的腳本與它逐位元相同；腳本含兩行 `module load` 與上述 `exec` 行 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-03 | 作法「`_head_script`」；裁決 10 | 功能 | 同 TC-LS-01 | 逐行讀 head 腳本 | 每行 module 指令的格式恰為 `module load <名稱> \|\| exit 1`；Nextflow 那行在 ampliseq 那行之前；兩行都出現在 `umask 077` 那行之後（不要求緊接）、`exec` 那行之前；任何 `nextflow` 指令之前沒有別的 `nextflow run` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-04 | 作法「最後一行改為…」；裁決 2 | 功能 | 同 TC-LS-01，本機直連（local）的 facts | 取 head 腳本最後一行 | 恰為 `exec nextflow run "$NFCORE_AMPLISEQ_HOME" -name run-one -params-file params.yaml -c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config -with-tower http://127.0.0.1:8787`（順序：站台的 `-c` 在前、我們的 `-c nextflow.config` 最後、`-with-tower` 在其後；`$…` 用雙引號包住） | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-05 | 作法「`-with-tower …`」；既有 forward 變體 | 功能 | 同 TC-LS-01，但 facts 為反向通道（reach=ssh，有 forward_file） | 取 head 腳本最後一行 | 與 TC-LS-04 相同，只是結尾是 `-with-tower "http://127.0.0.1:${ABF_FORWARD_PORT}"`；forward 的那幾行（讀 port、檢查）照舊都在 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-06 | 維護者原話 1：「`nextflow run $NFCORE_<P>_HOME … -c $NFCORE_SITE_CONFIG -c $NFCORE_SITE_REFERENCES`」；裁決 2 | 功能 | nano4 假 CE；模擬執行環境設 `NFCORE_AMPLISEQ_HOME=/opt/x y/ampliseq`（含空白）、`NFCORE_SITE_CONFIG=/s/site.config`、`NFCORE_SITE_REFERENCES=/s/refs.config`；假 `module` 指令記下被載入的名稱 | 模擬執行 head 腳本 | 假 `nextflow` 收到的參數依序恰為 `run`、`/opt/x y/ampliseq`（含空白仍是同一個參數）、`-name`、`run-one`、`-params-file`、`params.yaml`、`-c`、`/s/site.config`、`-c`、`/s/refs.config`、`-c`、`nextflow.config`、`-with-tower`、`http://127.0.0.1:8787`；沒有 `-r`；假 `module` 依序收到 `load biology/Nextflow/26.10.0`、`load biology/nf-core-ampliseq/2.18.0`；假 `nextflow` 在兩次 module 之後才被呼叫；腳本通過 `bash -n` 語法檢查 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-07 | 作法「`pipeline_source`」 | 功能 | nano4 假 CE，ampliseq 2.18.0 | 組出 bundle，讀 `bundle["pipeline_source"]` | 恰等於 `{"kind":"site-module","module":"biology/nf-core-ampliseq/2.18.0","home":"NFCORE_AMPLISEQ_HOME"}`（沒有多的鍵） | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-08 | 裁決 2（`-c` 行只來自 `siteConfigVars`，依序） | 功能 | 假 CE 的 `siteConfigVars=["B_CFG","A_CFG","C_CFG"]`，其餘照 nano4；命中 | 組出 head 腳本，取 `exec` 行 | `-c` 依序為 `-c "$B_CFG" -c "$A_CFG" -c "$C_CFG" -c nextflow.config`；不再出現 `NFCORE_SITE_CONFIG`、`NFCORE_SITE_REFERENCES` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-09 | 裁決 2（清單空就一個都沒有）；作法「沒列就不加」 | 功能 | 假 CE 的 `siteConfigVars=[]`，`sitePipelines` 仍命中 | 組出 head 腳本，取 `exec` 行 | 恰為 `exec nextflow run "$NFCORE_AMPLISEQ_HOME" -name run-one -params-file params.yaml -c nextflow.config -with-tower http://127.0.0.1:8787`；整份腳本沒有 `NFCORE_SITE` 字樣 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-10 | 裁決 10（重複取第一項） | 功能 | 假 CE 的 `sitePipelines` 有兩筆同為 `(nf-core/ampliseq, 2.18.0)`：第一筆 module=`m/first`、home=`FIRST_HOME`，第二筆 module=`m/second`、home=`SECOND_HOME` | 組出 bundle 與 head 腳本 | `pipeline_source` 是第一筆（`m/first`、`FIRST_HOME`）；腳本含 `module load m/first`、`"$FIRST_HOME"`，不含 `m/second`、`SECOND_HOME` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-11 | 作法（只改 head 腳本）；「不做」不碰 queue | 功能 | 同一份輸入，分別用「無三鍵的 CE」與「nano4 假 CE」組 bundle | 比較兩份 bundle | `files` 裡 `samplesheet.csv`、`params.yaml`、`nextflow.config` 兩者逐位元相同（`nextflow.config` 仍以 `OVERWRITE_BLOCK` 結尾）；head 腳本所有 `#SBATCH` 行相同；bundle 的 `pipeline` 仍是 `nf-core/ampliseq`、`revision` 仍是 `2.18.0` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-12 | 維護者原話 2：「站台 launch 對外介面不變（MCP `launch` 仍收 `nf-core/ampliseq`＋`2.18.0`）」 | 功能 | 平台上有一個帶三鍵的計算環境（經正常的建立流程存入）和上線的代理 | 透過既有的終端機／動作層 launch，只給 pipeline=`nf-core/ampliseq`、revision=`2.18.0`、樣本表與參數（和改動前完全相同的參數） | 建立出一筆等待確認的 launch；使用者要確認的畫面內容（bundle 的 head 腳本）含 `module load` 兩行與 `"$NFCORE_AMPLISEQ_HOME"`、不含 ` -r `；呼叫時不需要任何新參數 | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-13 | 維護者原話 1 的 `$NFCORE_<P>_HOME`（變數名來自 CE，不寫死） | 功能 | 假 CE 另有一筆 `{"pipeline":"nf-core/rnaseq","revision":"3.14.0","module":"biology/nf-core-rnaseq/3.14.0","home":"NFCORE_RNASEQ_HOME"}` | 以 `nf-core/rnaseq` `3.14.0` 組 head 腳本 | 含 `module load biology/nf-core-rnaseq/3.14.0`、`exec nextflow run "$NFCORE_RNASEQ_HOME"`；不含 `NFCORE_AMPLISEQ_HOME`、不含 ampliseq 的 module load | 自動：`platform/tests/test_launch_bundle.py` |

## User Story 2 — 未命中就照舊從遠端拉；module 載入失敗就停下（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LS-14 | plan `test_tc013c_a_…`；裁決 3 | 功能 | nano4 假 CE；pipeline `nf-core/ampliseq`、revision `2.17.0`（CE 只登記 2.18.0） | 組出 bundle 與 head 腳本 | `pipeline_source == {"kind":"remote"}`；`exec` 行是 `exec nextflow run nf-core/ampliseq -r 2.17.0 -name run-one -params-file params.yaml -c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config -with-tower http://127.0.0.1:8787`；仍有 `module load biology/Nextflow/26.10.0`；沒有 ampliseq 的 module load；沒有 `NFCORE_AMPLISEQ_HOME` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-15 | 裁決 3（golden `nano4-miss`） | 功能 | 同 TC-LS-14 | 組出的 head 腳本與 golden 檔的 `nano4-miss` 鍵比對 | golden 檔新增 `nano4-miss` 鍵；腳本與它逐位元相同 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-16 | plan「完成標準」：未命中路徑逐位元不變；裁決 3 | 功能 | 沒有三鍵的 CE（既有測試用的 `ce_snapshot()`，三鍵缺或為空）；本機與反向通道兩種 facts | 組出 head 腳本 | 本機版等於 golden 的 `local`，反向通道版等於 golden 的 `forward`（逐位元）；`pipeline_source == {"kind":"remote"}`；腳本沒有 `module load`、沒有站台 `-c` | 自動：`platform/tests/test_resume_render.py` 既有的 golden 案例不改仍綠，另在範圍檔加上 `pipeline_source` 斷言 |
| TC-LS-17 | plan「完成標準」；裁決 3 | 功能 | `git diff` 比較 base 與 HEAD 的 `golden_head_scripts.json` | 讀 `local`、`forward` 兩鍵的內容 | 兩鍵與 base 逐位元相同（只新增 `nano4`、`nano4-miss` 兩鍵，沒有改舊的） | 自動：`platform/tests/test_resume_render.py` 既有 `test_tc013_a_first_launch_head_script_is_byte_for_byte_what_it_was_before` 不改仍綠；驗收者另讀 diff |
| TC-LS-18 | 作法「查 `sitePipelines` 是否命中 `(pipeline, revision)`」 | 功能 | nano4 假 CE；pipeline `nf-core/rnaseq`、revision `2.18.0`（revision 與登記的相同、pipeline 不同） | 組出 bundle 與 head 腳本 | 視為未命中：`pipeline_source == {"kind":"remote"}`，`exec` 行是 `nf-core/rnaseq -r 2.18.0`，沒有 `NFCORE_AMPLISEQ_HOME` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-19 | 維護者原話 1：「缺 module 退回 `owner/name -r rev`」（依裁決 12，指 sitePipelines 沒命中）；作法「缺則空 list」 | 功能 | 假 CE 的 `sitePipelines` 為空清單，另一份則完全沒有 `sitePipelines` 鍵；`modules` 與 `siteConfigVars` 照 nano4；ampliseq 2.18.0 | 各組一次 head 腳本 | 兩份都是 `pipeline_source == {"kind":"remote"}`，`exec` 行是 `nf-core/ampliseq -r 2.18.0 …`，不含 `$NFCORE_AMPLISEQ_HOME` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-20 | 裁決 3（modules 非空就載，命中與未命中都載；逐位元相同只對 modules 與 siteConfigVars 皆空成立） | 功能 | 假 CE 只有 `modules=["biology/Nextflow/26.10.0"]`，`siteConfigVars=[]`、`sitePipelines=[]` | 組出 head 腳本，與「無三鍵 CE」的 golden `local` 比較 | 兩者只差一行：`umask 077` 之後多了 `module load biology/Nextflow/26.10.0 \|\| exit 1`；其餘逐位元相同 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-21 | 裁決 10、12；plan 的 TC-014「停下」 | 例外 | nano4 假 CE，命中；模擬執行時假 `module` 在載 `biology/nf-core-ampliseq/2.18.0` 時以非 0 結束（載 Nextflow 時成功） | 模擬執行 head 腳本 | 腳本以非 0 結束；假 `nextflow` 完全沒被呼叫（沒留下它的紀錄） | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-22 | 裁決 10、12 | 例外 | nano4 假 CE；假 `module` 在載第一個（`biology/Nextflow/26.10.0`）時就失敗 | 模擬執行 head 腳本 | 腳本以非 0 結束；假 `module` 沒有被呼叫第二次（不繼續載後面的）；假 `nextflow` 沒被呼叫 | 自動：`platform/tests/test_launch_bundle.py` |

## User Story 3 — 計算環境的三個新鍵帶進站台，並在站台再驗一次（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LS-23 | 裁決 0（`compute_envs.snapshot` 把三鍵帶給站台） | 功能 | 存了一個帶 nano4 三鍵的 Slurm 計算環境 | 呼叫 `compute_envs.snapshot`（平台交給代理的內容） | 結果含 `modules`、`siteConfigVars`、`sitePipelines`，值與存入的完全相同（`sitePipelines` 每筆仍是 `pipeline`、`revision`、`module`、`home` 四個鍵） | 自動：`platform/tests/test_station_envs.py` |
| TC-LS-24 | 裁決 0、作法「缺則空 list」 | 功能 | 一個沒有三鍵的 Slurm 計算環境 | 呼叫 `compute_envs.snapshot` 與 `launch.snapshot_ce`（帶 `config` 的 view） | 兩者的 `modules`、`siteConfigVars`、`sitePipelines` 都是 `[]`（不是缺鍵、不是 `None`） | 自動：`platform/tests/test_station_envs.py`、`platform/tests/test_launch_bundle.py` |
| TC-LS-25 | 作法「`snapshot_ce` 帶出三鍵」 | 功能 | 帶 nano4 三鍵的計算環境 view | 呼叫 `launch.snapshot_ce` | 結果的三鍵值等於 view 裡的值；原有的鍵（`name`、`workDir`、`headQueue`、`environment`、`nextflowConfig` 等）一個不少、值不變 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-26 | `compute_envs.snapshot` 既有承諾「只給工作需要的，不多給」 | 功能 | 計算環境同時有 `environment`、`nextflowConfig`、`headJobOptions`、三鍵 | 呼叫 `compute_envs.snapshot` | 鍵集合恰為改動前的鍵加上三鍵；`environment`、`nextflowConfig`、`headJobOptions` 等不在其中 | 自動：`platform/tests/test_station_envs.py` |
| TC-LS-27 | 作法「`rules.clean_environment` 把 `modules` 列入允許」；裁決 1（放行三鍵、其餘丟掉） | 功能 | 一個合法的環境 dict，附 nano4 三鍵與一個不認得的鍵 `evil` | 呼叫 `rules.clean_environment` | 輸出含三鍵且值照原樣；輸出沒有 `evil`；原有的 `workDir`、`launchDir`、`readRoots`、`headQueue`、`computeQueue` 判斷結果不變 | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-28 | plan「突變」：`modules=["a;b"]` → launch 被拒，訊息點名 `modules` | 例外 | 假 CE 的 `modules=["a;b"]` | 組 bundle | 被拒絕（`BundleError`），訊息含 `modules`，沒有產出任何 bundle | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-29 | 作法「`_check_ce` 對三鍵再驗」；裁決 8（重用 `compute_envs._module_problem`） | 例外 | `modules` 分別為：`["a b"]`、`["$(id)"]`、`["a`id`"]`、`[""]`、`["x/../y"]`、`[5]`、`"biology/Nextflow/26.10.0"`（字串而非清單） | 各組一次 bundle | 每一種都被拒，訊息點名 `modules`；沒有任何一個變成腳本內容 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-30 | 作法；裁決 8（`siteConfigVars` 用環境變數名規則） | 例外 | `siteConfigVars` 分別為：`["lower_case"]`、`["A;B"]`、`["1ABC"]`、`["A B"]`、`[""]`、`"NFCORE_SITE_CONFIG"`（字串而非清單） | 各組一次 bundle | 每一種都被拒，訊息點名 `siteConfigVars` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-31 | 作法；裁決 0、8（`sitePipelines` 形狀與 module／home 規則） | 例外 | `sitePipelines` 為一筆命中的項目但：`home="x;y"`；`home="lower"`；`module="a;b"`；少一個鍵；多一個鍵；項目不是物件；整個值不是清單 | 各組一次 bundle | 每一種都被拒，訊息點名 `sitePipelines`；`home` 的惡意值（例如 `X"; touch /tmp/pwn; "`）不會出現在任何輸出的腳本裡 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-32 | 裁決 0（結尾換行一律用 `\Z`）；既有 `security_f4` 的做法 | 例外 | `modules=["a\n"]`、`siteConfigVars=["A\n"]`、`sitePipelines` 的 `module="a\n"`、`home="A\n"` 各一份 | 各組一次 bundle | 每一份都被拒（結尾換行不算合法名稱），訊息點名對應的鍵 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-33 | 作法「不合就拒絕整個 launch」 | 例外 | 一份已確認的 bundle，其 `ce.modules` 被改成 `["a;b"]` | 交給代理執行 launch 工作（`run_launch`） | 代理拒絕（Refusal，訊息說「內容不合規則」並點名 `modules`）；站台上沒有建立資料夾、沒有 `sbatch` | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-34 | 環境事實：`_check_ce` 拒絕 `preRunScript`／`postRunScript`（007b 安全決定） | 例外 | nano4 假 CE，另設 `preRunScript="module load evil"` | 組 bundle | 仍被拒，訊息是既有的「不支援：這一片不執行事前／事後腳本」；`modules` 的存在不會讓腳本欄位被放行 | 自動：`platform/tests/test_launch_bundle.py`（既有 `test_tc025_pre_and_post_run_scripts_are_refused_never_skipped` 不改仍綠） |
| TC-LS-35 | 專長守則（backend）：錯誤訊息說明發生什麼、怎麼處理，不露內部 | 例外 | `modules=["a;b"]`、`siteConfigVars=["a"]`、`sitePipelines` 缺鍵各一份 | 取各自的拒絕訊息 | 訊息說出是哪個鍵、哪個值有問題、可用的字元（例如「letters, digits and _ . / + - only」之類的處理提示）；不含 `Traceback`、不含檔案路徑（`.py`、`/home`）、不含 SQL | 自動：`platform/tests/test_launch_bundle.py` |

## User Story 4 — 續跑（resume）也從本地路徑、也先 module load（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LS-36 | 裁決 5 | 功能 | 命中的 nano4 假 CE 組出的第一次 bundle（origin）；session id 為合法 UUID | `render_resume(origin, run_name="run-one-a2", attempt=2, session_id=SID)` | 輸出 `head-2.sh` 含兩行 `module load …`、含 `"$NFCORE_AMPLISEQ_HOME"`、不含 ` -r `；最後一行含 `-resume <SID>` 與 `-name run-one-a2`、含站台的 `-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES"` 且 `-c nextflow.config` 在最後 | 自動：`platform/tests/test_launch_bundle.py` 或 `test_station_launch.py` |
| TC-LS-37 | 裁決 5；既有「續跑與第一次只差兩處」的承諾 | 功能 | 同 TC-LS-36 | 比較第一次的 `head.sh` 與 `head-2.sh` 逐行 | 只有 `#SBATCH -J` 那一行和最後一行不同；`module load` 行兩邊相同 | 自動：同 TC-LS-36 |
| TC-LS-38 | 裁決 5（沿用原 bundle 的 CE 三鍵） | 功能 | 未命中的 nano4 假 CE（revision 2.17.0）組出的 origin | 同上續跑 | `head-2.sh` 有 `module load biology/Nextflow/26.10.0`、沒有 ampliseq 的 module load；最後一行是 `exec nextflow run nf-core/ampliseq -r 2.17.0 -resume <SID> -name …`，含站台 `-c` | 自動：同 TC-LS-36 |
| TC-LS-39 | 裁決 6（既有斷言不動）；plan「未命中逐位元不變」 | 功能 | 沒有三鍵的 CE 的 origin | 既有續跑測試（`test_resume_render.py` 內 TC-012 系列） | 既有斷言一字不改仍通過：最後一行以 `exec nextflow run nf-core/ampliseq -r 2.18.0 ` 開頭、含 `-resume <SID> `；腳本沒有 `module load` | 自動：`platform/tests/test_resume_render.py`（不改） |
| TC-LS-40 | 裁決 10：「舊 bundle 沒有 `pipeline_source` → 視為 `{"kind":"remote"}`」 | 功能 | 一份「改動前格式」的 origin：沒有 `pipeline_source`、`ce` 裡沒有三鍵 | `render_resume` | 不出錯；輸出等於改動前的續跑腳本（遠端 `-r`、沒有 module load） | 自動：`platform/tests/test_launch_bundle.py` 或 `test_station_launch.py` |
| TC-LS-41 | 裁決 5（命中的 run 續跑仍從本地路徑）；既有續跑的重建比對 | 功能 | 命中的 nano4 假 CE 之第一次 launch 已完成（假站台上有資料夾、history、head.sh 等），一份續跑 bundle 已確認 | 交給代理執行續跑（`run_resume`） | 代理接受重建比對、寫入 `head-2.sh` 與新 token、`sbatch` 一次；寫到站台的 `head-2.sh` 含 `module load` 與 `"$NFCORE_AMPLISEQ_HOME"`、不含 ` -r ` | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-42 | 裁決 10（舊 bundle 視為遠端）；改動前啟動的 run 仍能續跑 | 功能 | 一份「改動前格式」的 origin（無 `pipeline_source`、`ce` 無三鍵）及其續跑 bundle，已確認；假站台狀態符合 | 交給代理執行續跑 | 代理不會因為「重建結果多了 `pipeline_source`／三鍵」而拒絕；續跑照舊成功，寫出的 `head-2.sh` 是遠端版（含 `-r`、無 module load） | 自動：`platform/tests/test_station_launch.py` |

## User Story 5 — 代理重建一致、來源紀錄（provenance）寫進 bundle（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LS-43 | 作法「agent 重建 bundle 仍 byte-for-byte」 | 功能 | 命中的 nano4 假 CE 組出並確認的 launch bundle，交給代理 | 代理執行 `run_launch` | 代理自己依設定重建的結果與 bundle 完全相同而接受；站台上寫入的 `head.sh` 與確認時的 `head.sh` 逐位元相同；`sbatch` 一次 | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-44 | 憲法 2（執行的必須是使用者看到的那一份） | 例外 | 同 TC-LS-43，但確認之後 bundle 的 `pipeline_source` 被改成 `{"kind":"remote"}`（`files` 與 sha 不動） | 代理執行 | 代理拒絕，理由是「內容與代理依自己的設定重新產生的不一致」；站台沒有任何改動 | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-45 | 憲法 2 | 例外 | 同 TC-LS-43，但 bundle 的 `ce.modules` 被改成多一項 `evil/mod`（`files` 不動） | 代理執行 | 代理拒絕（重建不一致）；站台沒有任何改動 | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-46 | 憲法 2（確認時的雜湊涵蓋 bundle 全部內容） | 功能 | 同一份輸入，分別用命中的 CE 與未命中的 CE 組 bundle | 對兩份 bundle 算 `common.bundle_sha256` | 兩個雜湊不同；且只改 `pipeline_source` 一個欄位也會讓雜湊改變 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-47 | 裁決 4（`pipeline_source` 只放 bundle，`launches` 表不加欄、不需 migration） | 功能 | 一次完整的 launch 確認（含命中）後 | 讀確認紀錄的 `bundle_json`，並比對 `launches` 表的欄位 | `bundle_json` 解析後含 `pipeline_source` 且等於 TC-LS-07 的值；`launches` 表欄位與 base 完全相同（`PRAGMA table_info(launches)` 不變）；沒有新增 migration 步驟 | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-48 | 作法「ledger 寫明」；專長守則（資料結構變動要有 migration 或明寫不需要） | 功能 | 實作完成後的 `specs/launch-site-pipeline/ledger.md` | 驗收者讀 ledger | ledger 明寫：`pipeline_source` 在 `bundle_json` 內、`launches` 表不加欄、不需要 migration，並寫出理由；另列出 `test_launch_bundle.py`／`test_station_launch.py` 中有更新的既有斷言（若有）及原因（裁決 6） | 手動：驗收者讀 `specs/launch-site-pipeline/ledger.md`（目前只有標題行） |

## 憲法與安全網（專長守則 backend 與 `.specify/memory/constitution.md` 原則 I/V）

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LS-49 | 原則 I 第 2 條（唯一的送出路徑要先經使用者確認）；專長守則「確認管道」 | 例外 | 帶三鍵的計算環境、命中的 launch，沒有確認憑證（或憑證種類不對／已用過） | 交給代理執行 launch | 被拒；站台上沒有建立資料夾、沒寫檔、沒 `sbatch`；既有 `test_unconfirmed_launch_is_refused` 與 `test_tc008_*` 不改仍綠 | 自動：`platform/tests/test_station_launch.py` |
| TC-LS-50 | 專長守則「跨使用者（讀）」 | 例外 | 使用者 A 以帶三鍵的計算環境發起（命中的）launch；使用者 B 持自己的 token | B 嘗試讀 A 的 launch／確認紀錄（含其 bundle 與 `pipeline_source`）、A 的計算環境三鍵 | 被拒，回應與「不存在」相同的說法；回應中看不到 A 的 module 名稱、home 變數名 | 自動：`platform/tests/test_owner_binding.py`（只新增案例） |
| TC-LS-51 | 專長守則「跨使用者（寫）」 | 例外 | 同 TC-LS-50 | B 嘗試確認／取消 A 的那筆待確認 launch | 被拒；A 的紀錄與站台都沒有變動 | 自動：`platform/tests/test_owner_binding.py`（只新增案例） |
| TC-LS-52 | 專長守則「對等性」；維護者原話 2 | 功能 | 改動後的程式 | 列舉使用者可見的 MCP 工具與動作層函式，並比對 `launch` 工具的參數 | 工具清單與動作層函式一一對應，與改動前相同（沒有新增或消失的動作）；`launch` 工具的參數名稱與必填項與 base 相同（沒有新增參數）；既有 `test_tca02_*`、`test_tca13_*` 不改仍綠 | 自動：`platform/tests/test_actions_layer.py`（不改，另在範圍檔加參數比對） |
| TC-LS-53 | 專長守則「日誌與回應不含密鑰」；原則 V | 例外 | 命中的 launch，run token 為特殊字串（如 `TOKEN_CANARY_f33d`） | 組出 bundle、模擬執行、代理執行；收集 bundle、head 腳本、拒絕訊息、代理日誌 | token 字串不出現在 bundle、`head.sh`、任何拒絕訊息或日誌（`head.sh` 只含 `tower.token` 檔名）；新加的 module 行與 `-c` 行不含任何密鑰 | 自動：`platform/tests/test_launch_bundle.py`、`test_station_launch.py` |
| TC-LS-54 | 原則 I 第 2 條（送出只准一個檔案）；`launch.py` 檔頭 | 功能 | 改動後的程式 | 跑 `tests/no_second_run_state_test.sh` | 通過；沒有新增任何會送出的檔案；`launch.py` 仍是唯一放 head 腳本模板與 `sbatch` 的地方（既有 `test_tc013_the_script_is_a_single_template_in_one_module` 不改仍綠） | 自動：`tests/no_second_run_state_test.sh` |
| TC-LS-55 | 原則 I（站台資訊來自 CE，不寫死）；`launch.py` 檔頭「Nothing here names a cluster…」 | 功能 | 改動後的 `platform/abf_station/launch.py`、`rules.py` | 檢查原始碼 | 不含 `nano4`、`NCHC`、`NFCORE_`、`biology/` 等站台專屬字串；模組名、變數名只來自 CE 的值 | 自動：`platform/tests/test_station_launch.py`（原始碼掃描） |

## 不在範圍（plan「不做」、裁決 11、12）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-LS-56 | 裁決 11（exec 行不加 `-profile singularity`，命中與未命中都不加） | 不在範圍 | nano4 假 CE，命中與未命中各一份 | 取兩份 head 腳本 | 兩份都不含 `-profile`；既有 golden 的 `local`／`forward` 也沒有 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-57 | 維護者原話 1：「不走 `nfcore-submit`」 | 不在範圍 | 命中與未命中各一份 | 掃 head 腳本、bundle 全部檔案與 `launch.py` 原始碼 | 都不含 `nfcore-submit` | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-58 | plan「環境事實」：我們不碰 queue（`selectQueue` 是站台 config 的事） | 不在範圍 | 無三鍵 CE、nano4 命中、nano4 未命中三份 | 比較三份 head 腳本的 `#SBATCH` 行與 `nextflow.config` | `#SBATCH` 行完全相同（`-p` 仍是 CE 的 `headQueue`）；`nextflow.config` 除既有內容外沒有新增 queue 相關設定 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-LS-59 | plan「不做」：不改 `_tower`／`own_facts`（M1-03）、不改 preflight（M1-04） | 不在範圍 | 改動後的程式 | 驗收者讀 `git diff <base>...HEAD`；跑既有 `_tower`、`own_facts`、preflight 相關測試 | `launch.py` 的 `_tower`、`own_facts` 與 `handlers.py` 的 preflight 沒有任何一行被改；相關既有測試不改仍綠 | 手動：驗收者讀 diff；自動：既有 `test_station_launch.py`、`test_launch_bundle.py` |
| TC-LS-60 | 裁決 0（`compute_envs.py` 只改 `snapshot`；三鍵的驗證規則沿用 ce-nano4-keys） | 不在範圍 | 改動後的程式 | 驗收者讀 `compute_envs.py` 的 diff；跑 `test_station_envs.py` 的 ce-nano4-keys 案例 | `_check_site_keys`、`_module_problem`、`_var_problem`、`_check_slurm` 沒有被改；`test_station_envs.py` 只新增 `snapshot` 的案例，ce-nano4-keys 既有案例（TC-NK 系列）一字不改仍綠 | 手動：驗收者讀 diff；自動：`platform/tests/test_station_envs.py` |
| TC-LS-61 | 裁決 12（module load 失敗就停下回報，不自動退回遠端） | 不在範圍 | 命中的 nano4 假 CE，模擬執行時 module 失敗 | 讀 head 腳本全文並模擬執行 | 腳本裡只有一個 `nextflow run`（沒有「失敗時改跑遠端版」的第二條路）；失敗時不呼叫任何 `nextflow` | 自動：`platform/tests/test_launch_bundle.py` |
