# 測試案例：preflight-nano4（預檢先 module load，並檢查站台 pipeline 版本與唯讀映像庫）

<!--
Written by the verifier (CONTRACT mode) from the plan after the 2026-10-23 rulings, before any code.
There is no spec.md for this task: specs/preflight-nano4/plan.md is the spec. 作法 1-8 and 裁決 P2/P4/P5/P9/P10/P11 are cited as 「作法 n」「P n」.
-->

**規格**：`specs/preflight-nano4/plan.md`（無獨立 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、連線斷掉時，系統怎麼反應（拒絕、點名、說下一步、停下）。
- **不在範圍**：計畫「不做」或裁決明講不在本任務修的事；測試確認它真的沒做。

名詞：**預檢**（preflight）＝正式啟動前，先到站台確認環境對不對。**FakeSite**＝測試用的假站台（`platform/tests/station_harness.py`），不碰真的 nano4。**calls log**＝假站台記下的「它被叫了哪些指令」。**CE**＝計算環境（compute environment）。
以下「結果名稱」都指預檢結果清單裡每一項的 `name`。

## User Story 1 — 先 module load，java／nextflow 才找得到（優先度 P1）

維護者原話（裁示 17）：「nano4 若週四跑不通 → 先在 `/work/u9613010` 自裝 Nextflow＋插件跑通」——所以 `modules` 為空時，預檢不得硬要 `module load`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-01 | 作法 2 | 功能 | CE `modules=["biology/Nextflow/26.10.0"]`；假站台的 module 認得它 | 跑預檢 | 結果多一項 `modules`，狀態 `pass`，detail 是 `loaded: biology/Nextflow/26.10.0` | 自動：`platform/tests/test_station_e2e.py::test_pf_modules_loaded_before_java_and_nextflow` |
| TC-PF-02 | 作法 3 | 功能 | 同 TC-PF-01 | 跑預檢，看 calls log | 實際執行的 java 指令與 nextflow 指令，都以 `module load biology/Nextflow/26.10.0 && ` 開頭；java／nextflow 兩項仍照原規則判定（找得到且版本夠就 `pass`） | 自動：同上測試 |
| TC-PF-03 | 作法 2 | 功能 | CE `modules=["m/one","m/two"]`；兩個都認得 | 跑預檢 | 站台執行的是 `module load m/one && module load m/two`（依此順序）；`modules` 為 `pass`，detail 是 `loaded: m/one, m/two`；java／nextflow 指令前綴同一整串 | 自動：`test_station_e2e.py`（新增 `test_pf_two_modules_chain_in_order`） |
| TC-PF-04 | 作法 3；裁示 17 | 功能 | CE `modules=[]`（自裝 Nextflow 的情況） | 跑預檢，看 calls log 與結果 | 結果裡沒有 `modules` 這一項；calls log 完全沒有 `module` 指令；java／nextflow 的指令與現在逐字相同（`java -version`、`nextflow -version`，沒有前綴） | 自動：`test_station_e2e.py`（新增 `test_pf_empty_modules_means_no_module_load`） |
| TC-PF-05 | 作法 7 | 功能 | CE 只設 `modules`（認得） | 跑預檢，依序比對結果名稱 | 名稱清單恰為 `connect, work_dir, sbatch, squeue, sinfo, modules, java, nextflow, head_queue`（`modules` 在 `sinfo` 之後、`java` 之前） | 自動：`test_station_e2e.py`（新增 `test_pf_order_with_modules`） |
| TC-PF-06 | 作法 2；裁示 17「失敗訊息要能讓非工程師知道下一步」 | 例外 | CE `modules=["biology/Nextflow/26.10.0"]`；假站台的 module 不認得它 | 跑預檢 | `modules` 為 `fail`；detail 含模組名 `biology/Nextflow/26.10.0`，並含 `self-installed Nextflow` 與中文 `載入不了模組 biology/Nextflow/26.10.0：請檢查計算環境的 modules，或清空它改用自裝 Nextflow`；整體 `ok` 為 false | 自動：`test_station_e2e.py::test_pf_missing_module_is_named_with_the_next_step` |
| TC-PF-07 | 作法 2「點名第一個失敗的模組」 | 例外 | CE `modules=["m/ok","m/bad1","m/bad2"]`；只有 `m/ok` 認得 | 跑預檢 | `modules` 為 `fail`，detail 點名的是 `m/bad1`（第一個失敗的），不是 `m/bad2` | 自動：`test_station_e2e.py`（新增 `test_pf_first_failing_module_is_the_one_named`） |
| TC-PF-08 | 作法 3（失敗時 java／nextflow 照探測） | 例外 | 同 TC-PF-06（module 不認得） | 跑預檢 | 結果裡仍有 `java` 與 `nextflow` 兩項（各自獨立判定：此情況下站台找不到它們，兩項都是 `fail`），calls log 看得到這兩條帶 `module load … && ` 前綴的指令被執行過；沒有因為 `modules` 失敗而少報任何一項；連線沒有斷，所以不會變成只剩 connect 的中止結果 | 自動：`test_station_e2e.py`（新增 `test_pf_failed_modules_still_probes_java_and_nextflow`） |
| TC-PF-09 | P4 站台端再驗 | 例外 | 送給站台的 CE 帶 `modules=["a;b"]` | 對站台送 preflight 工作 | 工作被拒絕（Refusal），訊息點名鍵 `modules`；calls log 裡沒有任何含 `a;b` 的站台指令（根本沒送到站台） | 自動：`test_station_e2e.py`（新增 `test_pf_module_with_shell_characters_is_refused`） |
| TC-PF-10 | P4 | 例外 | 送給站台的 CE：一次 `sitePipelines[0].module="x y"`、一次 `sitePipelines[0].home="lower_case"` | 各送一次 preflight 工作 | 兩次都被拒絕，訊息分別點名 `sitePipelines` 的 module 與 home；站台沒有被叫任何探測指令 | 自動：`test_station_e2e.py`（新增 `test_pf_bad_site_pipeline_module_or_home_is_refused`） |

## User Story 2 — 確認站台預裝的 pipeline 真的是 CE 說的版本（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-11 | 作法 4 | 功能 | CE `sitePipelines=[{pipeline:"nf-core/ampliseq", revision:"2.18.0", module:"biology/nf-core-ampliseq/2.18.0", home:"NFCORE_AMPLISEQ_HOME"}]`；假站台該 module 認得、`$NFCORE_AMPLISEQ_HOME/main.nf` 讀得到、nextflow.config 的 `manifest { version = '2.18.0' }` | 跑預檢 | 多一項 `site_pipeline`，狀態 `pass`，detail 含 `nf-core/ampliseq 2.18.0` | 自動：`test_station_e2e.py::test_pf_site_pipeline_version_matches` |
| TC-PF-12 | 作法 4（去掉開頭 v） | 功能 | 同 TC-PF-11，分兩次：(a) CE revision `v2.18.0`、站台版本 `2.18.0`；(b) CE revision `2.18.0`、站台版本 `v2.18.0` | 各跑一次預檢 | 兩次 `site_pipeline` 都是 `pass`（`v` 前綴被忽略） | 自動：`test_station_e2e.py::test_pf_site_pipeline_v_prefix_is_ignored` |
| TC-PF-13 | 作法 4（commit revision） | 功能 | CE revision 是 40 位十六進位（例如 `0123456789abcdef0123456789abcdef01234567`）；站台 `main.nf` 讀得到，但 nextflow.config 的版本是完全不相干的 `9.9.9` | 跑預檢 | `site_pipeline` 是 `pass`；detail 含 `commit revision, version not compared` | 自動：`test_station_e2e.py::test_pf_site_pipeline_commit_revision_not_compared` |
| TC-PF-14 | P5（版本只從 manifest 取） | 功能 | 站台 nextflow.config 內容是 `params { version = '9.9' }` 加 `manifest { version = '2.18.0' }`；CE revision `2.18.0` | 跑預檢 | 取到的版本是 `2.18.0`，`site_pipeline` 為 `pass`（區塊外的 `version=` 不採用） | 自動：`test_station_e2e.py`（新增 `test_pf_version_comes_only_from_the_manifest_block`） |
| TC-PF-15 | P5（單引號或雙引號；第一個 version） | 功能 | 站台 nextflow.config 是 `manifest { nextflowVersion = '!>=24.04.2'  version = "2.18.0" }`（雙引號，且前面有一個名稱只是結尾像 version 的別的鍵）；CE revision `2.18.0` | 跑預檢 | 取到 `2.18.0`、`site_pipeline` 為 `pass`（鍵必須剛好叫 `version`，`nextflowVersion` 不算；雙引號也讀得到） | 自動：`test_station_e2e.py`（新增 `test_pf_version_key_must_be_exactly_version`） |
| TC-PF-16 | 作法 4（一個 CE 一項結果涵蓋所有條目） | 功能 | CE 有兩條 sitePipelines（例如 ampliseq 2.18.0 與 rnaseq 3.14.0），站台兩條都對 | 跑預檢 | 結果裡 `site_pipeline` 只出現一次，是 `pass`，detail 同時列出 `nf-core/ampliseq 2.18.0` 與 `nf-core/rnaseq 3.14.0` | 自動：`test_station_e2e.py`（新增 `test_pf_site_pipeline_one_result_for_all_entries`） |
| TC-PF-17 | 作法 1、4 | 功能 | CE `sitePipelines=[]` | 跑預檢，看結果與 calls log | 結果裡沒有 `site_pipeline` 項（不是 `unchecked`）；calls log 沒有任何讀 `main.nf`／`nextflow.config` 的指令 | 自動：`test_station_e2e.py`（新增 `test_pf_no_site_pipelines_means_no_site_pipeline_check`） |
| TC-PF-18 | 作法 4 | 例外 | 站台版本 `2.17.0`，CE revision `2.18.0` | 跑預檢 | `site_pipeline` 為 `fail`；detail 兩個版本都點名：`nf-core/ampliseq: the site has 2.17.0, the environment says 2.18.0`，並含中文 `站台裝的是 2.17.0，設定說 2.18.0` | 自動：`test_station_e2e.py::test_pf_site_pipeline_mismatch_names_both_versions` |
| TC-PF-19 | 作法 4 | 例外 | 站台 `$NFCORE_AMPLISEQ_HOME/main.nf` 不存在（變數有設） | 跑預檢 | `site_pipeline` 為 `fail`；detail 是 `nf-core/ampliseq 2.18.0: not installed where the module says`，並含中文 `站台找不到這個版本` | 自動：`test_station_e2e.py::test_pf_site_pipeline_missing_main_nf` |
| TC-PF-20 | 作法 4（module 載入失敗） | 例外 | 該條的 module（`biology/nf-core-ampliseq/2.18.0`）假站台不認得 | 跑預檢 | `site_pipeline` 為 `fail`，用與 TC-PF-19 同一句「not installed where the module says（站台找不到這個版本）」 | 自動：`test_station_e2e.py`（新增 `test_pf_site_pipeline_module_load_failure`） |
| TC-PF-21 | P4（變數沒設要與「未安裝」分開） | 例外 | 假站台環境根本沒設 `NFCORE_AMPLISEQ_HOME` | 跑預檢 | `site_pipeline` 為 `fail`；detail 是 `the site variable NFCORE_AMPLISEQ_HOME is not set`，含中文 `站台沒有設定 NFCORE_AMPLISEQ_HOME`；且不是 TC-PF-19 的「not installed」那句 | 自動：`test_station_e2e.py`（新增 `test_pf_site_variable_not_set_is_told_apart_from_not_installed`） |
| TC-PF-22 | P5 | 例外 | 站台 nextflow.config 完全沒有 `manifest` 區塊（只有 `params { version = '9.9' }`） | 跑預檢 | `site_pipeline` 為 `fail`；detail 含 `cannot read the pipeline version`，中文 `讀不出版本`（不得拿 `params` 裡的 9.9 去比） | 自動：`test_station_e2e.py`（新增 `test_pf_no_manifest_block_cannot_read_version`） |
| TC-PF-23 | 作法 4（commit 版仍要讀得到 main.nf） | 例外 | CE revision 是 40 位十六進位；站台 `main.nf` 不存在 | 跑預檢 | `site_pipeline` 為 `fail`，用「not installed where the module says（站台找不到這個版本）」那句 | 自動：`test_station_e2e.py`（新增 `test_pf_commit_revision_still_needs_main_nf`） |
| TC-PF-24 | 作法 4（全部通過才 pass） | 例外 | CE 兩條 sitePipelines，第一條對、第二條站台版本不符 | 跑預檢 | 結果裡 `site_pipeline` 仍只有一項，為 `fail`；detail 點名不符的那條（含它的 pipeline 名與兩個版本）；整體 `ok` 為 false | 自動：`test_station_e2e.py`（新增 `test_pf_one_bad_entry_fails_the_single_site_pipeline_result`） |

## User Story 3 — 唯讀映像庫讀得到（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-25 | 作法 5（snapshot）；P9 | 功能 | CE `environment` 含 `{name:"NXF_SINGULARITY_LIBRARYDIR", value:"/opt/lib/img"}` 與另一個 `{name:"A", value:"1"}` | 呼叫 `compute_envs.snapshot` | 結果有新鍵 `singularityLibraryDir`，值是 `/opt/lib/img`；結果裡找不到 `A` 這個環境變數或它的值，也沒有 `environment` 鍵 | 自動：`platform/tests/test_station_envs.py`（新增 `test_snapshot_carries_singularity_library_dir_only`） |
| TC-PF-26 | 作法 5；「允許更新的既有斷言」 | 功能 | 沒設 `NXF_SINGULARITY_LIBRARYDIR` 的 CE | 呼叫 `snapshot` | `singularityLibraryDir` 為 `None`；`test_tc_ls_23_24_26_snapshot_carries_the_three_keys_and_nothing_more` 的鍵集合恰為原本 10 個加上 `singularityLibraryDir`（共 11 個），該測試其餘斷言不變 | 自動：`test_station_envs.py::test_tc_ls_23_24_26_snapshot_carries_the_three_keys_and_nothing_more` |
| TC-PF-27 | 作法 5 | 功能 | CE 的 `NXF_SINGULARITY_LIBRARYDIR` 指向假站台上讀得到且可進入的資料夾 | 跑預檢，看結果與 calls log | 多一項 `image_library`，`pass`；站台執行的指令是 `test -r "<dir>" && test -x "<dir>"` | 自動：`test_station_e2e.py::test_pf_image_library_readable` |
| TC-PF-28 | 作法 5（不要求在 readRoots 內） | 功能 | 映像庫資料夾不在 CE 的 `readRoots`、也不在 workDir 之下 | 跑預檢 | 沒有被拒絕，`image_library` 為 `pass` | 自動：`test_station_e2e.py`（新增 `test_pf_image_library_need_not_be_inside_read_roots`） |
| TC-PF-29 | 作法 1、5 | 功能 | CE 的 `environment` 有 `NXF_SINGULARITY_CACHEDIR` 等其他變數，但沒有 `NXF_SINGULARITY_LIBRARYDIR` | 跑預檢 | 結果裡沒有 `image_library` 項（不是 `unchecked`）；calls log 沒有 `test -r` 映像庫的指令 | 自動：`test_station_e2e.py`（新增 `test_pf_no_library_dir_means_no_image_library_check`） |
| TC-PF-30 | 作法 5 | 例外 | 映像庫資料夾在假站台上不存在（或讀不到） | 跑預檢 | `image_library` 為 `fail`；detail 點名資料夾，句型 `the read-only image library <dir> cannot be read`，含中文 `唯讀映像庫讀不到` | 自動：`test_station_e2e.py::test_pf_image_library_unreadable_names_the_dir` |
| TC-PF-31 | 作法 5（讀與進入兩個都要） | 例外 | 映像庫資料夾存在、可讀，但沒有進入（x）權限 | 跑預檢 | `image_library` 為 `fail`，同 TC-PF-30 的句型 | 自動：`test_station_e2e.py`（新增 `test_pf_image_library_without_execute_permission_fails`） |
| TC-PF-32 | 作法 5（clean_root 同等規則） | 例外 | 送給站台的 CE，其 `NXF_SINGULARITY_LIBRARYDIR` 經 snapshot 後的 `singularityLibraryDir` 分三次是：相對路徑 `img/lib`、`/`、含 `..` 的路徑 | 各送一次 preflight 工作 | 三次都被拒絕（Refusal），訊息點名 `singularityLibraryDir`；站台沒有被叫任何指令 | 自動：`test_station_e2e.py`（新增 `test_pf_unsafe_library_dir_is_refused`） |

## User Story 4 — 舊環境不變、nano4 一次回報 11 項（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-33 | 完成標準；作法 7 | 功能 | 一個 nano4 型 CE：`modules`、`sitePipelines`、`NXF_SINGULARITY_LIBRARYDIR` 三者都設，假站台全部備妥 | 跑預檢 | 結果恰 11 項，順序為 `connect, work_dir, sbatch, squeue, sinfo, modules, java, nextflow, head_queue, site_pipeline, image_library`；全部 `pass`；`ok` 為 true；message 是 `all 11 checks passed` | 自動：`test_station_e2e.py`（新增 `test_pf_nano4_environment_reports_eleven_checks_in_order`） |
| TC-PF-34 | 作法 1；完成標準「舊環境逐字不變」 | 功能 | 三鍵都空、沒有映像庫的舊型 CE | 跑預檢 | 結果名稱集合仍等於既有的 `CHECKS`（那 8 項）、無任何條件式項目；每項判定與以前相同；calls log 與 base（改動前）逐字相同（與 base 對照用的指令清單寫死在測試裡） | 自動：`test_station_e2e.py::test_pf_old_environment_unchanged` |
| TC-PF-35 | 作法 1 | 功能 | 既有 TC-041、TC-042 | 跑 `test_station_e2e.py` 既有的 TC-041／TC-042 | 兩者原樣通過；`CHECKS` 常數仍是 8 項、未被改動；這兩個測試沒有被改寫（對 base 比對不出差異） | 自動：`test_station_e2e.py`（TC-041、TC-042 原有測試） |
| TC-PF-36 | 作法 1（`_verdict` 不改仍要算到新檢查） | 例外 | nano4 型 CE，只有 `image_library` 失敗，其餘皆過 | 跑預檢 | `ok` 為 false；message 是 `not passed: image_library` | 自動：`test_station_e2e.py`（新增 `test_pf_failed_conditional_check_fails_the_verdict`） |
| TC-PF-37 | 作法 1；launch 與 preflight 共用 | 功能 | 既有啟動測試用的 SITE_CE（有 modules＋sitePipelines）與 FakeSite 預設設定 | 跑 `test_station_launch.py`、`test_launch_bundle.py`、`test_station_envs.py` 全部既有測試 | 全綠；除 TC-PF-26 允許的那一條鍵集合外，沒有任何既有斷言被刪、放寬、跳過或改期望值（啟動前的預檢現在也會跑新檢查，所以假站台預設必須認得 SITE_CE 的模組與 pipeline 目錄） | 自動：`test_station_launch.py`、`test_launch_bundle.py`、`test_station_envs.py`（既有） |

## User Story 5 — 連線中途斷掉時，照既有方式中止（優先度 P2）

連線中止（abandon）的既有行為：結果只剩 `connect` 為 `fail`，其餘全是 `unchecked`（說明需要有效連線）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-38 | 作法 6；P10 | 例外 | nano4 型 CE；站台在模組探測那一步斷線（連線檢查也已失敗） | 跑預檢，依序比對結果名稱 | 結果名稱依序為 `connect, work_dir, sbatch, squeue, sinfo, modules, java, nextflow, head_queue, site_pipeline, image_library`；只有 `connect` 是 `fail`（附斷線原因），其餘 10 項全是 `unchecked`；沒有任何一項顯示為 `pass` | 自動：`test_station_e2e.py::test_pf_connection_lost_during_module_probe` |
| TC-PF-39 | 作法 6 | 例外 | nano4 型 CE；站台在 `site_pipeline` 探測那一步斷線 | 跑預檢 | 與 TC-PF-38 同一個中止形狀與同一份名稱順序（只有 `connect` 為 `fail`，其餘 `unchecked`），之前已跑過的項目不留下 `pass` | 自動：`test_station_e2e.py`（新增 `test_pf_connection_lost_during_site_pipeline_probe`） |
| TC-PF-40 | 作法 6 | 例外 | nano4 型 CE；站台在 `image_library` 探測那一步斷線 | 跑預檢 | 同 TC-PF-39 | 自動：`test_station_e2e.py`（新增 `test_pf_connection_lost_during_image_library_probe`） |
| TC-PF-41 | P10（rest_unchecked 帶入適用的條件式檢查） | 例外 | nano4 型 CE；一開始就連不上站台 | 跑預檢 | `connect` 為 `fail`；其餘（含 `modules`、`site_pipeline`、`image_library`）全是 `unchecked`，順序同 TC-PF-38 | 自動：`test_station_e2e.py`（新增 `test_pf_unreachable_site_lists_applicable_conditional_checks_unchecked`） |
| TC-PF-42 | P10（不適用的不出現） | 例外 | 舊型 CE（三鍵都空、無映像庫）；站台斷線 | 跑預檢 | 中止結果仍只有原本那 8 個名稱（`connect` 為 `fail`、其餘 7 項 `unchecked`），不出現 `modules`／`site_pipeline`／`image_library`；既有的斷線測試原樣通過 | 自動：`test_station_e2e.py`（既有斷線測試＋新增 `test_pf_connection_lost_old_environment_has_only_eight_names`） |

## User Story 6 — 文件與紀錄照實寫（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-43 | 範圍：`docs/PLATFORM.md` | 功能 | 實作完成 | 閱卷時讀 `docs/PLATFORM.md` 的「### Preflight」表 | 表下有三項條件式檢查（`modules`、`site_pipeline`、`image_library`）的說明，每項寫了「什麼條件下才出現」與「失敗時下一步」；名稱與程式一致 | 手動：閱卷者讀 `docs/PLATFORM.md`（非 `docs/TESTING.md` 步驟，見總覽說明） |
| TC-PF-44 | P2；P9 | 功能 | 實作完成 | 閱卷時讀 `docs/TESTING.md` TC-047n 那一步 | 原本寫 `library` 的地方已改為 `image_library`；`modules`、`site_pipeline` 名稱與程式一致 | 手動：閱卷者讀 `docs/TESTING.md`（TC-047n 附近） |
| TC-PF-45 | 作法 8；「允許更新的既有斷言」 | 功能 | 實作完成 | 閱卷時讀 `specs/preflight-nano4/ledger.md` | ledger 寫明：不需要 migration（預檢結果本來就存在 `compute_envs` 的 JSON 欄位）；列出被允許更新的那一條既有斷言（`test_tc_ls_23_24_26…` 的鍵集合） | 手動：閱卷者讀 ledger |
| TC-PF-46 | 「除此之外不改任何既有斷言」 | 功能 | 實作完成 | 閱卷時對 base 比對本任務碰到的所有既有測試檔（`test_station_e2e.py`、`test_station_envs.py`、`station_harness.py` 及任何被連帶改到的測試） | 唯一被改的既有斷言是 TC-PF-26 那條鍵集合；其餘既有測試沒有被刪除、放寬、跳過，期望值也沒被改成貼合新輸出；`specs/preflight-nano4/plan.md` 與 `test-case*.md` 在實作期間沒有被編輯 | 手動：閱卷者比對 diff |

## 不在範圍（計畫「不做」與裁決）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-47 | 不做：不改 `_verdict`、`CHECK_ORDER`、`apply_preflight` | 不在範圍 | 實作完成 | 讀 `handlers.CHECK_ORDER`、`compute_envs.apply_preflight` 與 `_verdict` 的行為 | `CHECK_ORDER` 仍恰為 `connect, work_dir, sbatch, squeue, sinfo, java, nextflow, head_queue`（不含新三項）；`_verdict` 判定規則不變（任何非 `pass` 即未通過）；`apply_preflight` 沒有改動 | 自動：`test_station_e2e.py`（新增 `test_pf_check_order_and_verdict_rule_unchanged`）＋閱卷者比對 diff |
| TC-PF-48 | 不做：不改站台啟動；P2 `snapshot_ce` 不帶 `singularityLibraryDir` | 不在範圍 | 實作完成 | 呼叫 `abf_station/launch.py::snapshot_ce`；並比對 diff | 回傳的啟動用快照沒有 `singularityLibraryDir` 鍵；`launch.py` 沒有被本任務修改 | 自動：`test_station_e2e.py`（新增 `test_pf_launch_snapshot_ce_does_not_carry_library_dir`）＋閱卷者比對 diff |
| TC-PF-49 | 不做：不檢查映像庫裡有沒有每個映像 | 不在範圍 | 映像庫資料夾存在、可讀可進入，但裡面是空的 | 跑預檢，看 calls log | `image_library` 為 `pass`；calls log 裡除了 `test -r`／`test -x` 外，沒有 `ls`、`find`、`stat` 等逐一檢視映像檔的指令 | 自動：`test_station_e2e.py`（新增 `test_pf_image_library_contents_are_not_inspected`） |
| TC-PF-50 | 不做：不在 nano4 實機跑 | 不在範圍 | 實作完成 | 閱卷時讀新增測試與 harness | 新測試全用 FakeSite；沒有任何測試、腳本或 ledger 步驟連到真的站台或 HPC；實機驗證仍留在 `docs/TESTING.md` 的 TC-047n | 手動：閱卷者讀測試與 diff |
| TC-PF-51 | P11 已知風險、不在本任務修 | 不在範圍 | 有 `modules` 的 CE | 跑預檢，看 calls log 與 diff | 所有探測指令都沒有 `source /etc/profile.d/lmod.sh`、`bash -l`、`lmod` 之類的字樣；`head.sh` 產生邏輯沒有被改 | 自動：`test_station_e2e.py`（新增 `test_pf_probes_do_not_source_lmod`） |
| TC-PF-52 | 作法 8：不需要 migration | 不在範圍 | 實作完成 | 閱卷時看 diff | 沒有新增 migration 檔、沒有新表或新欄位（`compute_envs` 的表結構定義未動）；理由寫在 ledger（對應 TC-PF-45） | 手動：閱卷者比對 diff |

## 憲法與安全網

<!-- 觸及的條目：原則 2（單一執行狀態來源的掃描，handlers.py 檔頭註解提到）、原則 3 第 7 條（不必找維護者）、預檢唯讀（handlers.preflight docstring）。後端專長守則的每條對應見總覽。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-PF-53 | 原則 2（`tests/no_second_run_state_test.sh` 掃 `handlers.py`） | 例外 | 實作完成 | 跑 `bash tests/no_second_run_state_test.sh`（Git Bash 可跑，不行則在 WSL） | 通過；新增的探測指令字串沒有被掃描誤判為「送出工作」的指令 | 自動：`tests/no_second_run_state_test.sh` |
| TC-PF-54 | 第 7 條 不必找維護者；裁示 17「同事不問我就能跑完」 | 功能 | TC-PF-06、18、19、21、22、30 各自產生的失敗結果 | 讀這六種失敗的 detail | 每一條都同時有英文與中文括號說明，並且指出「哪個東西有問題」與「下一步怎麼辦」或「站台缺什麼」，不是只有 `fail` 或錯誤碼 | 自動：`test_station_e2e.py`（上列各測試各自斷言這些句子）；用詞白不白話交維護者看 |
| TC-PF-55 | 後端守則：錯誤訊息不露堆疊、內部路徑 | 例外 | TC-PF-06、18、19、21、22、30 的失敗情境 | 檢查各 detail 與整個預檢結果 | 不含 `Traceback`、不含假站台暫存根目錄路徑、不含 nextflow.config 的原文片段；唯一出現的路徑是使用者自己設定並被要求點名的映像庫資料夾 | 自動：`test_station_e2e.py`（新增 `test_pf_failure_details_leak_no_internals`） |
| TC-PF-56 | 後端守則：密鑰不得出現在日誌或回應 | 例外 | FakeSite 預設的 CANARY 假密鑰（agent_connection、tw_token_file、私鑰內容）；nano4 型 CE 跑一次成功、一次各項失敗的預檢 | 檢查預檢結果、calls log 與 agent 日誌 | 這些 CANARY 字串一個都沒出現（新探測指令沒有把設定檔或環境內容帶出來） | 自動：`test_station_e2e.py`（新增 `test_pf_results_and_logs_carry_no_canary_secrets`） |
| TC-PF-57 | 預檢唯讀（"Nothing is created, changed or submitted on the site"）；後端守則：寫入需確認 | 例外 | nano4 型 CE，成功與各種失敗情境 | 跑預檢，比對假站台檔案樹前後，並檢查 calls log | 站台檔案樹前後完全相同；calls log 裡新增的指令只有讀取類（`module load`、`test`、`cat`／讀 nextflow.config、`command -v` 等），沒有 `mkdir`、`touch`、`rm`、`>` 寫檔、`sbatch` 等 | 自動：`test_station_e2e.py`（新增 `test_pf_new_probes_are_read_only`） |
| TC-PF-58 | 後端守則：對等性（一個動作一個函式，不得有第二份邏輯） | 功能 | 實作完成 | 列舉走預檢的入口：直接的 `preflight` 工作（`handlers.handle`）與啟動前自檢（`launch._prechecks`） | 兩個入口都呼叫同一個 `handlers.preflight`；同一個 nano4 型 CE 經兩個入口得到的預檢結果名稱與判定完全相同；`launch.py` 內沒有另一份 modules／site_pipeline／image_library 的檢查邏輯 | 自動：`test_station_e2e.py`（新增 `test_pf_job_and_launch_precheck_share_one_preflight`） |
| TC-PF-59 | 後端守則：擁有者規則（使用者只看得到自己的紀錄） | 例外 | 既有的跨使用者測試（`test_owner_binding.py`、`test_station_envs.py` 中的擁有者範圍測試） | 跑這些既有測試 | 全綠且未被改動；`snapshot` 多帶一個鍵並沒有放寬「只給擁有者自己的 CE」的規則 | 自動：`platform/tests/test_owner_binding.py`、`test_station_envs.py`（既有） |
