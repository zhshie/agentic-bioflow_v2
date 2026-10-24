# 測試案例：畫布 017d 組合流程經同一確認流程送出（純後端）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源只有 `specs/017d-launch-composed/plan.md`（沒有 spec.md）。依據順序：裁決二 > 裁決（含 A 至 E）> 計畫上文。
名詞：「組合」＝使用者在畫布上拖出來、存成版本的流程；「內容包」＝平台算好、要交給站台代理的整包送出資料；
「專案檔」＝這個組合自己的 main.nf、nextflow.config、modules.json 與 nf-core 模組檔；
「站台代理」＝在叢集那一頭真正動手的程式；「黃金圖」＝fastqc 接 multiqc 的小圖（017b 的夾具）。
-->

**規格**：`specs/017d-launch-composed/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

## User Story 1 — 送到確認頁，本人按了才有工作（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 完成標準 1；原話 3；F | 功能 | 本人已存下黃金圖（fastqc→multiqc）的組合版本；有一張兩列、欄位 `sample,reads` 的樣本表；有一個可用的環境 | 本人呼叫 `request_pipeline_launch`（給 pipeline_id、run_name、樣本表） | 回答 `state: pending`，並帶 `/c/<rid>` 確認頁連結 | 自動：`platform/tests/test_pipeline_launch.py` |
| TC-002 | 原話 5（憲法 6）；F 6 | 功能 | 同 TC-001，呼叫完、本人還沒按送出 | 查 `jobs` 與 `confirmations` | `jobs` 裡沒有任何 `launch_nextflow`；`confirmations` 有恰好一筆待確認 | 自動：`test_pipeline_launch.py` |
| TC-003 | 完成標準 1；F 6 | 功能 | 同 TC-002 | 本人在確認頁按「送出」（approve） | `jobs` 裡出現恰好一個 `launch_nextflow` 工作，其 `bundle_sha256` 等於確認當時顯示的那份 | 自動：`test_pipeline_launch.py` |
| TC-004 | F 6（`find_approved`） | 功能 | 同 TC-003，已送出並排隊 | 用完全相同的選擇再呼叫一次 `request_pipeline_launch` | 回答「已排隊」並指向同一個工作；沒有新增工作或新的待確認 | 自動：`test_pipeline_launch.py` |
| TC-005 | F 6；`test_pipeline_launch_uses_the_same_pending_request_and_page…` | 功能 | 同 TC-002 | 讀確認頁 `/c/<rid>` 的事實（既有的 `confirmation_facts`） | 顯示管線為 `abf-composed/<組合名稱>` 與版本；沿用既有確認頁，沒有新的頁面或管道 | 自動：`test_pipeline_launch.py` |
| TC-006 | F 6；`MAX_OPEN_PENDING` 共用 | 例外 | 本人已有 10 筆待確認（`MAX_OPEN_PENDING = 10`），其中有 nf-core 送出也有組合送出 | 再送一筆組合送出 | 被拒絕，話與 nf-core 送出遇到同一上限時相同；上限是兩種送出合算，不是各算各的 | 自動：`test_pipeline_launch.py` |
| TC-007 | F 2；`test_default_version_is_the_newest` | 功能 | 本人的組合有版本 1、2、3 | 呼叫時不給 `version` | 用的是版本 3（內容包 `revision` 為 `0.3.0`） | 自動：`test_pipeline_launch.py` |
| TC-008 | F 2；`test_missing_version_lists_the_versions_there_are` | 例外 | 本人的組合只有版本 1、2 | 給 `version=9` | 被拒絕，回答用 `get_pipeline` 現有的「有的版本：…」列出 1、2；沒有任何列寫進 `confirmations` | 自動：`test_pipeline_launch.py` |
| TC-009 | F 1 | 例外 | 同 TC-001 | 同時給 `samplesheet` 檔與 `samplesheet_text`；另一次兩者都不給 | 兩次都以「未送出：…」拒絕，話與 `request_launch` 遇到同樣情形時一致 | 自動：`test_pipeline_launch.py` |
| TC-010 | F 1（HTTP 呼叫者只能讀自己上傳資料夾） | 例外 | 以 HTTP 呼叫者身分；樣本表檔在他自己的上傳資料夾之外 | 呼叫 `request_pipeline_launch` | 被拒絕，話與 `request_launch` 同；沒有讀到那個檔 | 自動：`test_pipeline_launch.py` |
| TC-011 | F 6（`jobs.check_run_name`） | 例外 | 已有一個同名的 run_name 在用 | 用同名再送組合 | 以「未送出：…」拒絕，話與 nf-core 送出同名時相同 | 自動：`test_pipeline_launch.py` |
| TC-012 | F 5（`input`、`outdir` 既有規則） | 例外 | 同 TC-001 | `params` 裡帶 `input`；另一次帶 `outdir` | 兩次都被拒絕，話與 nf-core 送出同；沒有寫入待確認 | 自動：`test_pipeline_launch.py` |
| TC-013 | F（與 `request_launch` 簽名對齊） | 例外 | 同 TC-001 | `params` 給一個不是「名稱到值的對照」的東西（例如清單） | 以「params 必須是名稱到值的對照」類的話拒絕 | 自動：`test_pipeline_launch.py` |
| TC-014 | F 6（`_finish_launch`）；「不新增任何確認管道」 | 功能 | 讀 `actions/__init__.py` | 檢查 `request_launch` 與 `request_pipeline_launch` | 兩者都呼叫同一個私有 `_finish_launch`，後半段（找已批准、查名稱、畫面、`_ask`）不重複；沒有新的 job 種類、`REQUEST_TOOLS` 登記或確認管道 | 自動：`test_pipeline_launch.py` |
| TC-015 | 完成標準 1；原話 3 | 功能 | 黃金圖已存；本人 approve 後有一個 `launch_nextflow` 工作；用 `test_station_launch.py` 風格的假站台 | 假站台領走工作、跑 `run_launch` | `<run_folder>/pipeline/` 下有 `main.nf`、`nextflow.config`、`modules.json` 與 fastqc、multiqc 兩個模組的 `main.nf`；`head.sh` 最後一行啟動 `<run_folder>/pipeline/main.nf` | 自動：`platform/tests/test_pipeline_launch_station.py` |
| TC-016 | 裁決 10 | 功能 | 讀 `request_launch` 與 `request_pipeline_launch` 的簽名與既有測試 | 比對 | `request_launch` 的簽名與行為沒變（既有測試全綠）；`request_pipeline_launch` 的簽名是同樣的選項、把 `pipeline`／`revision` 換成 `pipeline_id`／`version`，另有只給測試用的 `data=` | 自動：`test_pipeline_launch.py` |

## User Story 2 — 送出前的閘門：現算驗證，不信存檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 原話 2；裁決 1；F 3 | 例外 | 本人存了 017c 的 `bad_edges` 圖（有 error 發現）的版本 | 呼叫 `request_pipeline_launch` | 被拒絕；回答用白話列出至少一條 error 的 `message`，並說「到組合頁修正後存成新版本再送」 | 自動：`test_pipeline_launch.py` |
| TC-018 | F 3；`test_a_graph_with_an_error_finding…` | 例外 | 同 TC-017，先記下 `jobs`、`confirmations`、`launches` 的列數 | 呼叫後再數 | 三張表列數都沒變 | 自動：`test_pipeline_launch.py` |
| TC-019 | F 3（最多 5 條） | 例外 | 一個有超過 5 條 error 的圖 | 呼叫 `request_pipeline_launch` | 回答列出 5 條 error 的 `message`，其餘寫成「另有 N 條」（N 為實際剩下的數字） | 自動：`test_pipeline_launch.py` |
| TC-020 | F 3；裁決 1、4；`test_a_graph_with_only_warnings…` | 功能 | 黃金圖（唯一發現是入口的 `OPEN_INPUT` warning） | 呼叫 `request_pipeline_launch` | 放行：回 `state: pending` 與 `/c/<rid>` | 自動：`test_pipeline_launch.py` |
| TC-021 | 裁決 1；`test_the_gate_recomputes…` | 例外 | 先 `validate_pipeline` 存下 ok；之後用 `data=` 換掉目錄使這張圖變成 `GRAPH_STALE` | 呼叫 `request_pipeline_launch(data=換過的目錄)` | 被拒絕（以現算為準，不信存下的 ok） | 自動：`test_pipeline_launch.py` |
| TC-022 | 裁決 1；同上反過來 | 功能 | 存下的驗證結果是舊的 error，但以現在的目錄這張圖其實沒有 error | 呼叫 `request_pipeline_launch` | 放行（以現算為準） | 自動：`test_pipeline_launch.py` |
| TC-023 | 裁決 1（「不需要使用者先按一次驗證」） | 功能 | 黃金圖的版本，從來沒有跑過驗證（沒有存下的驗證紀錄） | 呼叫 `request_pipeline_launch` | 放行，回 `pending` | 自動：`test_pipeline_launch.py` |
| TC-024 | F 3（不寫 `pipeline_validations`）；裁決 1 | 功能 | 記下 `pipeline_validations` 的列數 | 呼叫 `request_pipeline_launch`（放行的與被拒的各一次） | 列數沒變：送出前的請求不寫任何驗證紀錄 | 自動：`test_pipeline_launch.py` |
| TC-025 | 裁決二-4 | 功能 | 呼叫時不給 `data=` | 呼叫 `request_pipeline_launch` | 閘門用 `catalogue.load()` 的目錄現算（預設行為），結果與 TC-020 相同 | 自動：`test_pipeline_launch.py` |

## User Story 3 — 擁有者：別人的與不存在的回一樣的話（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 原話 7；F 2；專長守則（跨使用者讀） | 例外 | 兩位使用者 A、B（仿 `test_pipelines_store.py` 的雙使用者夾具）；A 有組合 | B 用 A 的組合編號送出；另一次 B 用一個不存在的編號送出 | 兩次回答的字（`words`）完全相同 | 自動：`test_pipeline_launch.py` |
| TC-027 | F 2 | 例外 | 一個根本不存在的組合編號 | 本人送出 | 回答「找不到這個組合」 | 自動：`test_pipeline_launch.py` |
| TC-028 | 專長守則（跨使用者寫）；F 2 | 例外 | 同 TC-026，先記下 `confirmations`、`jobs` 的列數 | B 用 A 的組合送出 | `confirmations` 與 `jobs` 都沒有新列；B 沒有讀到 A 的組合內容 | 自動：`test_pipeline_launch.py` |
| TC-029 | 擁有者規則（環境由呼叫者過濾） | 例外 | A 有自己的環境；B 在 `ce_name` 指向 A 的環境 | B 用自己的組合送出但指向 A 的環境 | 被拒絕，話與 `request_launch` 指向別人環境時相同 | 自動：`test_pipeline_launch.py` |
| TC-030 | F 2 | 功能 | 同 TC-026 | A 用自己的組合送出 | 放行（兩人並存時，擁有者不受影響） | 自動：`test_pipeline_launch.py` |
| TC-031 | 專長守則（跨使用者寫）；憲法 2 同一人 | 例外 | A 的組合送出已產生待確認 `/c/<rid>` | B 以自己的登入打開 A 的 `/c/<rid>`、嘗試按送出 | 被拒絕，與 nf-core 送出的待確認被別人按時相同；沒有工作產生 | 自動：`test_pipeline_launch.py` |

## User Story 4 — 專案檔怎麼組（`build_project`）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | B 5；夾具；`test_golden_project_matches…` | 功能 | 黃金圖＋兩列 `sample,reads` 樣本表；夾具 `fixtures/pipeline_launch/fastqc_multiqc/` 的手算標準答案 | `build_project(...)` | `project` 的鍵恰好是 `main.nf`、`nextflow.config`、`modules.json`、fastqc 與 multiqc 兩個模組的 `main.nf`（`modules/nf-core/<path>/main.nf`）；每個檔逐字等於標準答案 | 自動：`test_pipeline_launch.py` |
| TC-033 | B 5；`test_project_is_deterministic…` | 功能 | 同 TC-032 | 連續建兩次 | 兩次 `project` 完全相同；`project_sha256` 等於 `sha256(canonical_json(project))` | 自動：`test_pipeline_launch.py` |
| TC-034 | B 1 | 功能 | 同 TC-032 | 拿 `main.nf` 與 017b 的黃金 `main.nf` 比 | 只差兩處：被替換的那一行、加進去的 `ch_rows` 那一行；其他每個字元相同 | 自動：`test_pipeline_launch.py` |
| TC-035 | B 2；夾具 | 功能 | 同 TC-032 | 看 `main.nf` | `ch_qc_in0 = Channel.empty()  // OPEN INPUT…` 那一行被逐字換成 `    ch_qc_in0 = ch_rows.map { row -> [ [id: row.sample], file(row.reads, checkIfExists: true) ] }`；`workflow {` 後第一行是 `    ch_rows = Channel.fromPath(params.input).splitCsv(header: true)` | 自動：`test_pipeline_launch.py` |
| TC-036 | B 2；`test_open_input_lines_…changed_line_shape_is_an_error` | 例外 | 把 017b 渲染出的 `Channel.empty()  // OPEN INPUT` 那一行形狀換掉 | `build_project(...)` | 丟 `ProjectError`（找不到預期的那一行），不產出專案檔 | 自動：`test_pipeline_launch.py` |
| TC-037 | B 2（沒有開放輸入） | 功能 | 一張圖的所有輸入都已接上（沒有 `open_inputs`） | `build_project(...)` | `main.nf` 裡沒有 `ch_rows` 那一行，也沒有任何樣本表綁定 | 自動：`test_pipeline_launch.py` |
| TC-038 | B 2（string） | 功能 | 合成目錄：開放輸入的記錄型別為 `string`，名字 `tag` | `build_project(...)` | 該元素寫成 `row.tag` | 自動：`test_pipeline_launch.py` |
| TC-039 | B 2（integer） | 功能 | 記錄型別 `integer`，名字 `depth` | 同上 | 元素寫成 `(row.depth as Integer)` | 自動：`test_pipeline_launch.py` |
| TC-040 | B 2（float） | 功能 | 記錄型別 `float`，名字 `rate` | 同上 | 元素寫成 `(row.rate as Double)` | 自動：`test_pipeline_launch.py` |
| TC-041 | B 2（boolean） | 功能 | 記錄型別 `boolean`，名字 `flag` | 同上 | 元素寫成 `row.flag.toBoolean()` | 自動：`test_pipeline_launch.py` |
| TC-042 | B 2、6（directory） | 功能 | 記錄型別 `directory`，名字 `indir` | 同上 | 元素寫成 `file(row.indir, checkIfExists: true)`，且 `indir` 在回傳的 `path_columns` 裡 | 自動：`test_pipeline_launch.py` |
| TC-043 | B 2（只有一筆非 meta 記錄且無 meta） | 功能 | 通道只有一筆 `file` 記錄、沒有 meta | 同上 | 元素直接是該值（`file(row.<名字>, checkIfExists: true)`），沒有外面的 `[ ]` | 自動：`test_pipeline_launch.py` |
| TC-044 | B 2（其餘用 `[ … ]`） | 功能 | 通道有 meta 加一筆 file（如黃金圖）或有兩筆非 meta 記錄 | 同上 | 元素用 `[ … ]` 包起來，meta 在第一格，順序依目錄順序 | 自動：`test_pipeline_launch.py` |
| TC-045 | B 2；`test_unsupported_input_type_names_node_input_and_record` | 例外 | 開放輸入的記錄型別是 `list`（夾具 `unsupported/`） | `build_project(...)` | 丟 `ProjectError`，點名節點、輸入編號、記錄名 | 自動：`test_pipeline_launch.py` |
| TC-046 | B 2（缺漏型別） | 例外 | 開放輸入的記錄沒有型別 | 同上 | 同 TC-045：丟 `ProjectError` 點名節點、輸入編號、記錄名 | 自動：`test_pipeline_launch.py` |
| TC-047 | B 2；`test_missing_required_column…`；夾具 `unsupported/` | 例外 | 樣本表標題列缺少一個非 optional 記錄的欄（例：缺 `reads`） | `build_project(...)` | 丟 `ProjectError`，用白話列出「樣本表需要這些欄：sample、reads…（缺：reads）」 | 自動：`test_pipeline_launch.py` |
| TC-048 | B 2（有 meta 的通道一律需要 `sample` 欄） | 例外 | 樣本表沒有 `sample` 欄，通道有 meta | 同上 | 丟 `ProjectError`，缺的欄列出 `sample` | 自動：`test_pipeline_launch.py` |
| TC-049 | B 2；`test_missing_optional_column…` | 功能 | `optional` 為 true 的記錄，樣本表標題列沒有該欄 | 同上 | 該元素寫成 `[]`，不報錯 | 自動：`test_pipeline_launch.py` |
| TC-050 | B 2；`test_channels_with_the_same_names_share_columns` | 功能 | 兩個節點的開放輸入都有同名同型別的記錄 `reads` | 同上 | 樣本表只需要一個 `reads` 欄，兩個通道都讀它 | 自動：`test_pipeline_launch.py` |
| TC-051 | B 2；`test_same_name_different_type_is_refused` | 例外 | 兩個節點的記錄同名但型別不同 | 同上 | 丟 `ProjectError` | 自動：`test_pipeline_launch.py` |
| TC-052 | B 2；`test_unsafe_column_names_are_refused` | 例外 | 記錄名含引號、空白、`$`（不符 `^[A-Za-z_][A-Za-z0-9_]*$`） | 同上 | 丟 `ProjectError`，三種都被擋 | 自動：`test_pipeline_launch.py` |
| TC-053 | B 2；`test_user_text_never_reaches_groovy` | 例外 | 樣本表某格寫成 `'; evil()` | `build_project(...)` | 該字串沒有出現在任何一個專案檔裡 | 自動：`test_pipeline_launch.py` |
| TC-054 | B 6 | 功能 | 黃金圖（`reads` 是 `file` 記錄） | 看回傳的 `path_columns`、`columns` | `path_columns` 恰好是 file／directory 記錄對應的欄名（`reads`）；`columns` 列出樣本表需要的欄 | 自動：`test_pipeline_launch.py` |
| TC-055 | B 6；`test_file_columns_are_added_to_path_columns…` | 例外 | 樣本表 `reads` 欄某格指到允許讀取範圍之外的路徑 | 經 `request_pipeline_launch` 送出 | 被既有的 `_check_samplesheet` 拒絕，話與 nf-core 送出同 | 自動：`test_pipeline_launch.py` |
| TC-056 | B 3；裁決 5；`test_publish_block_is_appended_once…` | 功能 | 黃金圖 | 看專案的 `nextflow.config` | 末尾有恰好一段標明 `// added by the platform at launch` 的 `process.publishDir`，在節點設定之後，`mode: 'copy'`，輸出到 `${params.outdir}/<process 名小寫>` | 自動：`test_pipeline_launch.py` |
| TC-057 | B 4 | 功能 | 黃金圖 | 看專案檔 | `modules.json` 在專案裡，內容與 017b 渲染的相同 | 自動：`test_pipeline_launch.py` |
| TC-058 | B 5；裁決 6；`test_project_size_and_file_count_limits` | 例外 | 專案檔全部 UTF-8 位元組總和超過 2 MiB（另測剛好 2 MiB 允許） | `build_project(...)` | 丟 `ProjectError`，訊息說出上限數字 | 自動：`test_pipeline_launch.py` |
| TC-059 | B 5；裁決 6 | 例外 | 檔案數超過 2,000（另測剛好 2,000 允許） | 同上 | 丟 `ProjectError`，訊息說出上限數字 | 自動：`test_pipeline_launch.py` |
| TC-060 | 裁決 8；A 2 | 例外 | 圖用到一個標為 `unsupported`（有 `bin/`）的模組（合成 sources） | `build_project(...)` | 丟 `ProjectError`，點名該模組與理由（如「需要 bin/ 目錄，目前無法帶到站台」），並建議換成別的模組 | 自動：`test_pipeline_launch.py` |
| TC-061 | 裁決二-6；原話 1（不做巢狀子流程） | 例外 | 合成模組的 `main.nf` 裡有 `include {`；另一個有 `workflow ` 宣告 | `build_project(...)` | 兩個都被拒絕，點名該模組；代碼 `UNSUPPORTED_MODULE` 可從錯誤物件或訊息讀到 | 自動：`test_pipeline_launch.py` |
| TC-062 | 裁決二-6；A 3 | 功能 | 真資料裡的 fastqc 與 multiqc 模組 | 對這兩個模組套用 TC-061 的檢查 | 都不被擋（黃金例用真資料能組出專案） | 自動：`test_pipeline_launch.py` |
| TC-063 | B；錯誤訊息規則 | 例外 | 觸發 TC-036、045、047、051、058 各一個 `ProjectError` | 讀訊息 | 每一則都同時有中文與英文，說明發生什麼事與怎麼改 | 自動：`test_pipeline_launch.py` |
| TC-064 | F 4 | 例外 | 經 `request_pipeline_launch` 觸發任一種 `ProjectError`（如缺欄） | 呼叫 | 回答以「未送出：」開頭、帶 ProjectError 的話；`confirmations`、`jobs` 沒有新列 | 自動：`test_pipeline_launch.py` |
| TC-065 | B（純函式：不讀資料庫、不連網、不寫檔） | 功能 | 平台資料夾不存在、檔案系統唯讀的情境 | 呼叫 `build_project(...)` | 仍能產出專案；`build_project` 不引入 `store`、`jobs`、`confirm`，不開檔寫入 | 自動：`test_pipeline_launch.py` |

## User Story 5 — 模組檔資料（`module_sources.py` 與資料檔）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-066 | A 1；`test_snapshot_is_byte_identical…` | 功能 | 一個小的假 checkout（tmp 目錄） | 用同一個 sha 跑 `snapshot` 兩次 | 兩份輸出逐位元相同 | 自動：`platform/tests/test_module_sources.py` |
| TC-067 | A 1 | 功能 | 同 TC-066 | 讀輸出 | 形狀是 `{"source": "nf-core/modules", "sha": …, "modules": {<path>: {"files": {…}, "unsupported": …}}}`；鍵排序、`ensure_ascii=False`、gzip `mtime=0` | 自動：`test_module_sources.py` |
| TC-068 | A 1；`test_snapshot_keeps_only_main_templates_and_resources` | 功能 | 假 checkout 的模組裡有 `main.nf`、`templates/`、`resources/` 文字檔，也有 `meta.yml`、`environment.yml`、`tests/` | 跑 `snapshot` | 只有 `main.nf`、`templates/*`、`resources/*` 的文字檔進輸出；`meta.yml`、`environment.yml`、`tests/` 都不在 | 自動：`test_module_sources.py` |
| TC-069 | A 2 | 例外 | 假 checkout 有模組含 `bin/` 資料夾 | 跑 `snapshot` | 該模組 `unsupported` 為說明理由的字串 | 自動：`test_module_sources.py` |
| TC-070 | A 2 | 例外 | 假 checkout 有模組含取不下來的二進位檔（含 NUL 或不能 UTF-8 解碼） | 同上 | 該模組標 `unsupported` 並有理由 | 自動：`test_module_sources.py` |
| TC-071 | A 2 | 例外 | 假 checkout 有模組含檔名不合形狀的檔 | 同上 | 該模組標 `unsupported` 並有理由 | 自動：`test_module_sources.py` |
| TC-072 | A 2；TC-072 形狀 | 例外 | 假 checkout 有模組某檔含 `/home/<名字>/` 之類形狀的路徑 | 同上 | 整個模組標 `unsupported`，且沒有改任何檔的內容 | 自動：`test_module_sources.py` |
| TC-073 | A 2 | 例外 | 假 checkout 有模組某檔超過 200,000 字元 | 同上 | 該模組標 `unsupported` 並有理由 | 自動：`test_module_sources.py` |
| TC-074 | A 3；`test_load_refuses_sources_of_another_sha` | 例外 | 合成的模組資料，其 `sha` 與目錄的 `sha` 不同 | `module_sources.load(...)` | 被拒絕 | 自動：`test_module_sources.py` |
| TC-075 | A 3；`test_sources_sha_equals_the_catalogue_sha` | 功能 | 真資料 `data/nf-core-module-sources.json.gz` 與 `data/nf-core-modules.json` | 比較兩者的 `sha` | 相等，且都是 `5ed90b42e78410e7411e9c6bdfeff33226d6c58e` | 自動：`test_module_sources.py` |
| TC-076 | `test_every_catalogue_module_has_files_or_a_named_reason` | 功能 | 真資料 | 逐一檢查目錄的每個模組 | 每個都出現在 sources；`unsupported` 不為 null 的都有理由字串 | 自動：`test_module_sources.py` |
| TC-077 | `test_fastqc_and_multiqc_are_present_and_supported` | 功能 | 真資料 | 查 fastqc 與 multiqc | 兩者都在，`unsupported` 為 null，並有 `main.nf` | 自動：`test_module_sources.py` |
| TC-078 | A 3 | 功能 | 合成資料 | `files_for(["fastqc"…], sources)` | 回傳的鍵是 `modules/nf-core/<path>/<相對路徑>`，值是文字 | 自動：`test_module_sources.py` |
| TC-079 | A 3；`test_files_for_names_the_missing_or_unsupported_module` | 例外 | 要的 path 不在資料裡；另一次是 unsupported | `files_for(...)` | 丟 `ValueError`，點名那個模組，中英說明 | 自動：`test_module_sources.py` |
| TC-080 | A 3（`lru_cache`） | 功能 | 預設路徑 | 連續呼叫 `load()` 兩次 | 回傳同一個物件（有快取） | 自動：`test_module_sources.py` |
| TC-081 | 裁決 A；A 4；裁決 2 | 功能 | 真資料檔 | 量檔案大小；讀 ledger | 壓縮後不超過 8 MiB；ledger 記了實際大小與 unsupported 的模組數 | 自動：`test_module_sources.py` |
| TC-082 | A；`test_module_sources_source_has_no_network_or_program_words` | 功能 | 讀 `module_sources.py` 原始碼 | 檢查 | 只用標準函式庫；不含 `urllib`、`requests`、`socket`、`subprocess`、啟動 Nextflow 的指令字樣 | 自動：`test_module_sources.py` |
| TC-083 | 範圍；`pyproject.toml` | 功能 | 讀 `platform/pyproject.toml` 的 diff | 比對 | `package-data` 只多一個 glob：`data/*.json.gz`，其他不動 | 自動：`test_module_sources.py` |
| TC-084 | TC-072（`test_scope.py`） | 功能 | 掃 `platform/` 底下所有檔，含新資料檔與 `fixtures/pipeline_launch/*` | 跑 `test_scope.py` | 沒有 `(/home|/work|/scratch|/staging|/lustre)/名字/` 形狀的路徑 | 自動：`platform/tests/test_scope.py` |

## User Story 6 — 內容包與 `head.sh`（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-085 | C（`composed is None` 逐位元相同） | 功能 | 既有夾具的 nf-core 送出 | 呼叫 `render_bundle(..., composed=None)` | 輸出、雜湊、既有 golden、確認憑證都和改動前逐位元相同；既有測試不改就全綠 | 自動：`platform/tests/test_launch_bundle.py` |
| TC-086 | C | 例外 | `composed` 不是 None，但 `pipeline` 不是 `abf-composed/…` | `render_bundle(...)` | 丟 `BundleError` | 自動：`test_launch_bundle.py` |
| TC-087 | C（名稱符合 `PIPELINE_PART`） | 例外 | `pipeline` 是 `abf-composed/` 加上不合 `PIPELINE_PART` 的名稱 | 同上 | 丟 `BundleError` | 自動：`test_launch_bundle.py` |
| TC-088 | C（`revision` 恰為 `0.<version>.0`） | 例外 | `revision` 不是 `0.<version>.0`（例：`1.0.0`，或與 `composed.version` 對不上） | 同上 | 丟 `BundleError` | 自動：`test_launch_bundle.py` |
| TC-089 | C；`test_bundle_shape_of_a_composed_launch` | 功能 | 一次組合送出 | 讀內容包的鍵 | 恰好比 nf-core 送出多 `project`；`pipeline_source` 恰好四個鍵：`kind`（值 `composed`）、`pipeline_id`、`version`、`project_sha256`（值等於 `sha256(canonical_json(project))`） | 自動：`test_pipeline_launch.py` |
| TC-090 | C | 功能 | 同 TC-089 | 讀 `pipeline`、`revision` | `pipeline == "abf-composed/<名稱>"`、`revision == "0.<版本>.0"` | 自動：`test_pipeline_launch.py` |
| TC-091 | C（`RECORDS`、`LAUNCH_KEYS` 不變） | 功能 | 讀 `abf_station/launch.py` | 比對 | `RECORDS` 與 `LAUNCH_KEYS` 與改動前相同；`project` 是內容包的一部分、會被雜湊與確認 | 自動：`test_launch_bundle.py` |
| TC-092 | D；裁決二-2；原話 4 | 功能 | `SITE_CE`（run_folder 為 `/data/w1/runs/run-one`），run_name `run-one`，tower 為 `http://127.0.0.1:8787`；`sitePipelines` 有 ampliseq | 產生組合的 `head.sh`，看最後一行 | 逐字等於 `exec nextflow run /data/w1/runs/run-one/pipeline/main.nf -name run-one -params-file params.yaml -c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c /data/w1/runs/run-one/pipeline/nextflow.config -c nextflow.config -with-tower http://127.0.0.1:8787` | 自動：`test_launch_bundle.py` |
| TC-093 | D（module load） | 功能 | 同 TC-092 | 看 `head.sh` 的 `module load` | 只有 CE 的 `modules`（例 `biology/Nextflow/26.10.0`）；沒有載任何來源模組 | 自動：`test_launch_bundle.py` |
| TC-094 | D（沒有 `-r`） | 功能 | 同 TC-092 | 看最後一行 | 沒有 `-r` | 自動：`test_launch_bundle.py` |
| TC-095 | D；裁決二-2 | 功能 | 同 TC-092 | 看 `-c` 的順序 | 站台的 `-c "$…"` 在最前、`-c <run_folder>/pipeline/nextflow.config` 其次、最後是 `-c nextflow.config`；`-with-tower <endpoint>` 不變 | 自動：`test_launch_bundle.py` |
| TC-096 | D；允許更新 | 功能 | 讀 `golden_head_scripts.json` | 比對 | 多一個 `composed` 鍵且等於上面產出；既有四個鍵（`forward`、`local`、`nano4-miss`、`nano4`）位元不變 | 自動：`test_launch_bundle.py` |
| TC-097 | C；`test_the_site_pipeline_hit_does_not_hijack…` | 功能 | `sitePipelines` 有 ampliseq，組合名稱剛好也叫 ampliseq | 產生組合的內容包 | 走本地專案（`pipeline_source.kind == "composed"`），不被站台 pipeline 命中劫持 | 自動：`test_launch_bundle.py` |
| TC-098 | C；`test_project_key_shapes_are_refused` | 例外 | `project` 的鍵含 `..`、以 `/` 開頭、含反斜線、含 `bin/`、不在 `modules/nf-core/` 前綴之下（各一次） | `render_bundle(..., composed=…)` | 每次都丟 `BundleError`，點名那個鍵 | 自動：`test_launch_bundle.py` |
| TC-099 | C | 例外 | 檔案內容含 NUL、ESC、CR、雙向控制字元（各一次） | 同上 | 每次都丟 `BundleError`，點名那個鍵 | 自動：`test_launch_bundle.py` |
| TC-100 | C（單檔 ≤ 200,000 字元） | 例外 | 一個檔 200,001 字元（另測 200,000 允許） | 同上 | 丟 `BundleError`，點名那個鍵 | 自動：`test_launch_bundle.py` |
| TC-101 | C（總計 ≤ 2 MiB） | 例外 | 全部檔案總和超過 2 MiB（另測剛好 2 MiB 允許） | 同上 | 丟 `BundleError` | 自動：`test_launch_bundle.py` |
| TC-102 | C（檔數 ≤ 2,000） | 例外 | 檔數 2,001（另測 2,000 允許） | 同上 | 丟 `BundleError` | 自動：`test_launch_bundle.py` |
| TC-103 | C（`main.nf`、`nextflow.config` 必須存在） | 例外 | `project` 缺 `main.nf`；另一次缺 `nextflow.config` | 同上 | 各丟 `BundleError`，點名缺的檔 | 自動：`test_launch_bundle.py` |
| TC-104 | C（值必須是文字） | 例外 | `project` 某個值不是文字（如數字、位元組） | 同上 | 丟 `BundleError` | 自動：`test_launch_bundle.py` |
| TC-105 | C；`test_the_hash_covers_the_project` | 功能 | 一份組合內容包 | 改某個模組檔的一個字元後重算 | `bundle_sha256` 不同 | 自動：`test_pipeline_launch.py` |
| TC-106 | D；裁決 7；`test_render_resume_refuses_a_composed_origin` | 例外 | 一個 `pipeline_source.kind == "composed"` 的 origin | `render_resume(...)` | 丟 `BundleError` | 自動：`test_launch_bundle.py` |
| TC-107 | 裁決 12 | 功能 | 讀 `BUNDLE_VERSION` | 檢查 | 仍是 1 | 自動：`test_launch_bundle.py` |
| TC-108 | C（舊版代理）；完成標準手動項 | 例外 | 一份舊版代理（不認得 `project`）收到組合包 | 在 nano4 實測；或讀 ledger | ledger 記為「未驗證」且寫明預期：舊代理重算不出 `project`、比對失敗、拒絕（訊息不精確），PR 說明寫「組合送出需要新版站台代理」 | 手動：讀 `ledger.md` 與 PR 說明；`docs/TESTING.md` |

## User Story 7 — 站台側 `run_launch`（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-109 | E 2、3；`test_a_composed_launch_is_rebuilt_byte_for_byte…` | 功能 | 仿 `test_station_launch.py` 的 `site`／`fake` 夾具；一份已確認的組合內容包 | 真的跑 `run_launch` | 重算一模一樣；站台上 `pipeline/main.nf`、`pipeline/modules/nf-core/<path>/main.nf` 等每個檔的內容都等於 `bundle["project"]` | 自動：`test_pipeline_launch_station.py` |
| TC-110 | E 3 | 功能 | 同 TC-109 | 讀站台上的 `head.sh` | 等於內容包裡的 `head.sh` | 自動：`test_pipeline_launch_station.py` |
| TC-111 | E 3 | 功能 | 同 TC-109 | 查檔案權限 | 都是 `0600`（`umask 077`） | 自動：`test_pipeline_launch_station.py` |
| TC-112 | E 4 | 功能 | 同 TC-109 | 數 `sbatch` 次數 | 恰好一次 | 自動：`test_pipeline_launch_station.py` |
| TC-113 | E 3；裁決 6 | 功能 | 同 TC-109 | 看寫檔用的 tar | 同一次 tar 內含 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`、`tower.token`，再加 `pipeline/<相對路徑>`，依鍵排序；整個過程只有一次 `tar -x` | 自動：`test_pipeline_launch_station.py` |
| TC-114 | E 2；`test_a_project_file_changed_after_the_yes…` | 例外 | 已確認的內容包，其 `main.nf` 被改一個字元 | 跑 `run_launch` | 被拒絕（「內容與代理依自己的設定重新產生的不一致」）；站台上沒有寫任何檔、沒有 `sbatch` | 自動：`test_pipeline_launch_station.py` |
| TC-115 | E 2 | 例外 | 改一個模組檔的一個字元 | 同上 | 同 TC-114：拒絕且沒寫任何東西 | 自動：`test_pipeline_launch_station.py` |
| TC-116 | E 2（`project_sha256` 是代理自己算的） | 例外 | 改 `project_sha256` | 同上 | 同 TC-114：拒絕且沒寫任何東西 | 自動：`test_pipeline_launch_station.py` |
| TC-117 | E；C；`test_a_project_with_an_unlisted_path_is_refused` | 例外 | `project` 的鍵是 `pipeline/../x`；另一次是 `modules/nf-core/a/../../b` | 同上 | 各自被拒絕，沒寫任何東西 | 自動：`test_pipeline_launch_station.py` |
| TC-118 | E 2 | 例外 | 內容包 `pipeline_source.kind == "composed"` 但沒有 `project` | 同上 | `Refusal`，沒寫任何東西 | 自動：`test_pipeline_launch_station.py` |
| TC-119 | E 2 | 例外 | 內容包有 `project` 但 `pipeline_source.kind` 不是 composed | 同上 | `Refusal`，沒寫任何東西 | 自動：`test_pipeline_launch_station.py` |
| TC-120 | E 3；`test_the_run_folder_that_exists_already_is_not_overwritten` | 例外 | 該 run 的資料夾已存在 | 同上 | 拒絕（不覆蓋），原有檔案不變；沒有「sha 相同就略過」的捷徑 | 自動：`test_pipeline_launch_station.py` |
| TC-121 | D；裁決 7；`test_run_resume_refuses_a_composed_origin` | 例外 | 手工組一個有 `resume` 且 origin 是組合的包 | 跑 `run_resume` | 被拒絕，沒有動站台資料夾 | 自動：`test_pipeline_launch_station.py` |
| TC-122 | `test_an_nf_core_launch_through_the_agent_is_unchanged` | 功能 | 既有 `bundle_for` 夾具的 nf-core 送出 | 跑 `run_launch` | 寫出的檔案、`head.sh`、tar 內容與改動前相同；沒有 `pipeline/` 資料夾 | 自動：`test_pipeline_launch_station.py` |
| TC-123 | E 1；憲法 2 | 例外 | 組合內容包沒有有效的確認憑證（或憑證已用過） | 跑 `run_launch` | 被拒絕，沒寫任何東西；`verify_confirmation` 的行為與 nf-core 送出相同 | 自動：`test_pipeline_launch_station.py` |
| TC-124 | E 4 | 功能 | 組合內容包；站台的容器快取不可寫 | 跑 `run_launch` | `_prechecks` 照舊擋下（與 nf-core 送出同樣的話）；沒有 `sbatch` | 自動：`test_pipeline_launch_station.py` |

## User Story 8 — `build.py`：保留名稱、續跑拒絕、確認畫面（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-125 | 裁決 10；`test_the_reserved_owner_cannot_be_launched_as_an_nf_core_pipeline` | 例外 | 用 `socket.socket` 換成會丟例外的假物件 | `request_launch(pipeline="abf-composed/x", revision="0.1.0", …)` | 以白話拒絕；沒有連網（沒去 GitHub 找）；沒有寫待確認 | 自動：`test_pipeline_launch.py` |
| TC-126 | 裁決 10 | 例外 | `launch_prefill` 帶出一個 `abf-composed/…` 名稱 | 拿它再走 nf-core 送出 | 同 TC-125：白話拒絕、沒連網 | 自動：`test_pipeline_launch.py` |
| TC-127 | F（build.py 改動） | 例外 | 沒有 `composed` 參數，`pipeline` 擁有者是 `abf-composed` | `build.prepare_launch(...)`（網頁表單路徑） | 丟 `Refusal` | 自動：`test_pipeline_launch.py` |
| TC-128 | 裁決二-5 | 例外 | 觸發 TC-125 | 讀拒絕的話 | 為「組合流程只能從畫布送出（畫布送出介面尚未開放）」的中英並列；不提不存在的工具名（不含 `launch_pipeline`） | 自動：`test_pipeline_launch.py` |
| TC-129 | 裁決 7；`test_resume_and_relaunch_of_a_composed_run…`（續跑） | 例外 | 一個組合送出的 run（失敗的） | `prepare_resume` | `Refusal`，話為「自訂組合的 run 目前不能續跑或原樣重跑；請回到組合頁，用同一個版本重新送出（會再問一次確認）(a run of a composed pipeline cannot be resumed or relaunched yet; …)」 | 自動：`test_pipeline_launch.py` |
| TC-130 | 裁決 7（重跑） | 例外 | 同 TC-129 | `prepare_relaunch` | 同 TC-129 的拒絕與話 | 自動：`test_pipeline_launch.py` |
| TC-131 | F（`launch_screen`） | 功能 | 一份組合內容包 | 產生確認畫面 | 在「管線」「版本」之後多顯示：組合名稱與版本、專案檔數、`project_sha256` | 自動：`test_pipeline_launch.py` |
| TC-132 | F；`test_the_screen_shows_the_main_script_and_the_config…` | 功能 | 同 TC-131 | 看畫面 | 完整印出 `main.nf` 與專案的 `nextflow.config`（沒有被截短） | 自動：`test_pipeline_launch.py` |
| TC-133 | F | 功能 | 同 TC-131 | 看其餘檔案的部分 | 每個其餘檔列出路徑、位元組數、sha256 前 12 碼；模組檔不印內文；並寫「這些是 nf-core/modules 在 commit <sha> 的原檔」 | 自動：`test_pipeline_launch.py` |
| TC-134 | F（`terminal.block`，與 `head.sh` 同樣處理） | 例外 | 專案檔內容含控制字元 | 產生畫面 | 控制字元被處理掉，不能藉此改寫畫面其他部分（與 `head.sh` 同處理） | 自動：`test_pipeline_launch.py` |
| TC-135 | F；`test_the_screen_of_an_nf_core_launch_is_unchanged` | 功能 | 既有 nf-core 送出 | 產生確認畫面 | 與改動前逐字相同 | 自動：`test_pipeline_launch.py` |

## User Story 9 — 沒變的東西、資料結構、安全與範圍守門（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-136 | C；`test_a_non_composed_bundle_is_byte_identical_to_before` | 功能 | 既有夾具算出一份 nf-core 內容包 | 算 `bundle_sha256` | 等於測試裡寫死的值；該值取自 base 分支的實際執行結果，不是新程式算出來的 | 自動：`test_pipeline_launch.py` |
| TC-137 | G；`test_no_table_or_column_changed` | 功能 | 讀 `launches` 欄位與 `STATE_SCHEMA`、`jobs` 的 CHECK | 比對 | 全部不變；`test_http_site_samplesheet.py::test_tc057_no_table_or_column_changed` 照過 | 自動：`test_pipeline_launch.py` |
| TC-138 | G | 功能 | 一份改動前產生的舊內容包與舊 `platform.db` | 走確認、`run_launch` | 原樣可用（不需要 migration） | 自動：`test_pipeline_launch_station.py` |
| TC-139 | G；專長守則（migration） | 功能 | 讀計畫、ledger、PR 說明 | 檢查有沒有寫「不需要 migration」的理由 | 有寫理由：內容包本來就是 JSON 存在 TEXT 欄，新鍵只出現在新送出的包裡，沒有改任何表或欄位 | 手動：讀 `ledger.md` 與 PR 說明 |
| TC-140 | `test_building_a_launch_opens_no_socket` | 功能 | `socket.socket` 換成會丟例外的假物件 | 整條 `request_pipeline_launch` 到確認頁 | 完全沒有觸發假物件 | 自動：`test_pipeline_launch.py` |
| TC-141 | 專長守則（錯誤訊息）；`test_error_messages_hide_internals` | 例外 | 觸發 TC-017、027、045、047、125 等各種拒絕 | 讀每個被拒回應 | 都不含 SQL、堆疊、`platform.db` 路徑、`/home`／`/work` 形狀；都說明原因與怎麼處理 | 自動：`test_pipeline_launch.py` |
| TC-142 | 專長守則（密鑰不外洩） | 例外 | 組合送出一次，站台 tower token 與環境金鑰在內容包的 `files` 之外 | 搜遍所有回應、確認頁文字、專案檔與日誌 | 找不到 token 值或任何金鑰 | 自動：`test_pipeline_launch.py` |
| TC-143 | 憲章原則 2；`test_pipeline_launch_source_has_no_program_or_run_words` | 功能 | 讀 `pipeline_launch.py`、`module_sources.py`、`build.py` | 掃描 | 不含啟動 Nextflow 的指令字樣、`subprocess`、`sbatch` | 自動：`test_pipeline_launch.py` |
| TC-144 | 裁決二-1 | 功能 | 讀 `actions/__init__.py` | 掃描 | 沒有 `compose`、`composed`、`abf-composed` 任何字樣；它只 `from .. import pipeline_launch` 並呼叫 `pipeline_launch.prepare(...)`；`pipeline_launch.py`、`build.py`、`abf_station/launch.py` 可以出現這些字 | 自動：`test_pipeline_launch.py` |
| TC-145 | 允許更新的既有斷言 | 功能 | 讀 `test_pipelines_store.py` 的 diff | 比對 | 只改了一處：`actions/__init__.py` 的禁用字拿掉 `actions.pipelines`，`compose` 仍在禁用字裡；其他檔（`mcp_server.py`、`web.py`、`store.py`、`catalogue.py`）的規則原樣 | 手動：讀 `git diff` |
| TC-146 | 允許更新；放水檢查 | 功能 | 讀 `test_launch_bundle.py`、`test_station_launch.py`、`golden_head_scripts.json` 的 diff | 比對 base | 兩個測試檔只新增；既有斷言沒被移除、放寬或跳過；golden 只多 `composed` 一個鍵 | 手動：讀 `git diff` |
| TC-147 | 必須確認仍綠 | 功能 | 計畫「必須確認仍綠、不准改」列的各測試（`test_launch_bundle.py` 四個、`test_station_launch.py` 數個、`test_owner_gaps.py`、`test_owner_binding.py`、`test_resume_*`、`test_station_resume.py`、`test_station_static.py`、`test_launch_static.py`、`test_compose.py`、`test_validate.py`、`test_catalogue.py`、`test_web_parity.py`、工具數斷言） | 逐一跑 | 全綠，且這些測試本身沒被修改 | 自動：各自的 `platform/tests/` 檔 |
| TC-148 | 憲章原則 2；憲法 2 | 功能 | 專案根目錄 | 跑 `bash tests/no_second_run_state_test.sh` 與 `bash tests/platform_storage_doc_test.sh` | 兩者綠；`LAUNCH_ALLOW` 仍只有 `platform/abf_station/launch.py` 一條；`build.py`、`pipeline_launch.py` 的非註解行不含啟動指令；沒有新儲存項 | 自動：`tests/no_second_run_state_test.sh`、`tests/platform_storage_doc_test.sh` |
| TC-149 | 範圍：不准動 | 功能 | 讀 `git diff <base>...HEAD --stat` | 檢查下列檔案 | `store.py`、`jobs.py`、`confirm.py`、`compose.py`、`catalogue.py`、`validate.py`、`actions/pipelines.py`、`data/nf-core-modules.json`、`mcp_server.py`、`web.py`、`web_board.py`、`abf_station/handlers.py`／`rules.py`／`agent.py`、`constraints.txt`、`tests/no_second_run_state_test.sh` 都沒有變動 | 手動：讀 `git diff --stat` |
| TC-150 | 完成標準 4；裁決二-3 | 功能 | 讀 `git diff <base>...HEAD --stat` | 比對計畫「範圍：檔案」 | 修改過的路徑只在範圍列內（含裁決二-3 加的 `docs/TESTING.md`）；沒有其他檔 | 手動：讀 `git diff --stat` |
| TC-151 | 必須仍綠：`test_scope.py` TC-070、TC-071 | 功能 | 新增的 `module_sources.py`、`pipeline_launch.py`、三個新測試檔 | 跑 `test_scope.py` | 這些檔前 40 行都有 `# Nothing existing: …`（理由 ≥ 15 字）；`abf_platform/**/*.py` 含註解與說明文字都沒有啟動 Nextflow 的指令、`subprocess`、`threading`、`while True`、`nohup`、`setsid` | 自動：`test_scope.py` |
| TC-152 | 完成標準 3 | 功能 | 專案 `platform/tests` | 在 WSL／Linux 跑全套（`tests/run_all.sh`） | 全綠 | 自動：`tests/run_all.sh` |

## User Story 10 — 夾具、文件與交付（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-153 | 夾具 | 功能 | 讀 `platform/tests/fixtures/pipeline_launch/` | 列檔 | `fastqc_multiqc/` 有 `graph.json`、樣本表、手算的 `main.nf`、`nextflow.config`、檔案清單；`unsupported/` 有 `bin/` 模組、`list` 型別輸入、缺必要欄位的樣本表 | 自動：`test_pipeline_launch.py` |
| TC-154 | 夾具（手算、不得用程式輸出回填） | 功能 | 標準答案與 ledger 的推導 | 驗收者依計畫文字（被換掉的那一行、`ch_rows` 那一行、`publishDir` 段、017b 黃金）獨立重推 | 重推結果與夾具相同；ledger 逐項寫了推導；沒有用被測程式的輸出回填的痕跡 | 手動：讀夾具與 `ledger.md` |
| TC-155 | 夾具 | 功能 | 讀 `test_pipeline_launch.py` | 看 `sources` 與目錄用什麼 | 單元測試用小型合成的 sources（3～4 個手寫模組）與合成目錄；只有黃金例與資料檔本身的測試用真資料 | 手動：讀測試檔 |
| TC-156 | 裁決 11 | 功能 | 讀 `docs/PLATFORM.md` | 找 `## Composed pipelines` 之下 | 新增 `### Launching a composed pipeline`，寫到：誰能送、閘門、內容包多了什麼、檔案怎麼來、跑在哪裡、不支援續跑、需要新版站台代理 | 手動：讀 `docs/PLATFORM.md` |
| TC-157 | 裁決 11 | 功能 | 讀 `docs/PLATFORM.md` 的 `### What was handed over` | 檢查 | 補了一句講 `pipeline/` 資料夾 | 手動：讀 `docs/PLATFORM.md` |
| TC-158 | 裁決二-3 | 功能 | 讀 `docs/TESTING.md` | 找手動驗收段 | 有「在 nano4 真跑一次 fastqc→multiqc 組合」的步驟：專案設定被讀到、`publishDir` 有輸出、容器由 nano4 線上拉取；具體到別人能照做 | 手動：讀 `docs/TESTING.md` |
| TC-159 | 完成標準；A 4；裁決 2、8 | 功能 | 讀 `ledger.md` | 檢查 | 記了：資料檔實際大小、unsupported 模組數、標準答案的推導、「允許更新的既有斷言」改動、未驗證項（nano4 實跑、舊版代理拒絕訊息） | 手動：讀 `ledger.md` |
| TC-160 | 完成標準 5 | 功能 | 讀 PR 說明 | 檢查 | 寫明：不需要 migration 的理由、新資料檔的大小與更新方法、與總表 017d 的差異（裁決 2、6、7、9、10）、「組合送出需要新版站台代理」、未驗證項目 | 手動：讀 PR 說明 |

## User Story 11 — 這次不做的事（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-161 | 不做 1；專長守則（對等性）；017e | 不在範圍 | 列舉 MCP 工具清單、網頁路由清單、parity 表，以及動作層函式 | 比對 | 沒有新增 MCP 工具（沒有 `launch_pipeline`）、沒有新路由；`mcp_server.py`、`web.py`、`web_board.py`、`handlers.py` 沒變；工具數斷言與 `test_web_parity.py` 不變；`request_pipeline_launch` 只在動作層 | 自動：`test_web_parity.py`、`test_chat_tools.py`、`test_mcp.py` |
| TC-162 | 不做 2；裁決 7 | 不在範圍 | 讀 `abf_station/launch.py` 的續跑 `_probe`／`_check_folder` | 比對 base | 仍只比對四個 `FILE_NAMES` 的 sha256，沒有把 `pipeline/` 的檔加進去（那是 `017d2-resume-composed`）；續跑與重跑只是白話拒絕（見 TC-121、129、130） | 手動：讀 `git diff` |
| TC-163 | 不做 3；裁決 9 | 不在範圍 | 讀 diff | 找 `container` 解析、容器預檢 | 沒有解析模組 `container` 指令、沒有新增容器檢查、沒有改目錄快照去帶 `container`；`_prechecks` 不變 | 手動：讀 `git diff` |
| TC-164 | 不做 4 | 不在範圍 | 讀 diff | 找 lint、`-stub-run`、nf-test、zip 匯出 | 都沒有 | 手動：讀 `git diff` |
| TC-165 | 不做 5 | 不在範圍 | 讀 `store.py` 與 `git diff` | 檢查 | 沒有在 `launches` 加欄、沒有加表、沒有新 job 種類（`jobs` 的 CHECK 不變） | 自動：`test_pipeline_launch.py`（同 TC-137） |
| TC-166 | 不做 6；憲法 6 | 不在範圍 | 本人做了一次「驗證」動作（`validate_pipeline`）且結果 ok | 看 `confirmations` 與 `jobs` | 驗證通過不會自動產生確認或工作；沒有任何不經確認頁就能到達 `launch_nextflow` 的路徑 | 自動：`test_pipeline_launch.py` |
| TC-167 | 不做 7（list 或沒有型別的開放輸入） | 不在範圍 | 夾具 `unsupported/` 的 `list` 型別輸入圖 | 經 `request_pipeline_launch` 送出 | 明白拒絕說這個輸入型別不支援，點名節點與輸入；沒有悄悄產生專案、沒有待確認、沒有工作 | 自動：`test_pipeline_launch.py` |
| TC-168 | 不做 7；原話 1 | 不在範圍 | 圖用到有 `bin/` 的模組；另一個用到含 `include {` 或 `workflow ` 的模組 | 經 `request_pipeline_launch` 送出 | 各自明白拒絕、點名模組；沒有待確認、沒有工作 | 自動：`test_pipeline_launch.py` |
| TC-169 | 不做 8（配對式一格兩檔） | 不在範圍 | 樣本表 `reads` 欄某格寫成兩個檔（以空白或分號隔開） | 經 `request_pipeline_launch` 送出 | 該格被當成一個值、一個路徑檢查（多半被既有路徑檢查拒絕）；產生的 Groovy 裡沒有任何把格子拆成兩個檔的程式 | 自動：`test_pipeline_launch.py` |
| TC-170 | 不做 9；裁決 6 | 不在範圍 | 看 `run_launch` 寫檔 | 檢查 tar 的所有路徑與 `launch.py` | 專案檔只寫在 `<run_folder>/pipeline/` 之下；沒有共用的 `<workDir>/pipelines/…` 資料夾；沒有「sha 相同就略過」的邏輯 | 自動：`test_pipeline_launch_station.py` |
| TC-171 | 不做 10；裁決 6 | 不在範圍 | 讀組合內容包的鍵 | 檢查 | 沒有 `project_tar` 或任何 base64 的 tar；專案是 `{相對路徑: 文字}` 的對照表 | 自動：`test_pipeline_launch.py` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-172 | 憲法 2（唯一送出路徑要本人確認）；`test_human_channel.py`／`test_confirm_page.py` 的 `test_tch09_*` | 例外 | 一筆組合送出的待確認 | 試著用「模型自己能給的答案」（待確認本身、token、沒登入的請求）當作確認 | 都不成立：沒有 `launch_nextflow` 工作；只有本人以同一帳號在確認頁（或終端機、MCP 表單）答應才產生工作；既有 `test_tch09_*` 仍綠 | 自動：`test_pipeline_launch.py`、`test_human_channel.py`、`test_confirm_page.py` |
| TC-173 | 憲法 2（`no_second_run_state_test.sh` 的送出掃描） | 功能 | `platform/` 全部非註解行 | 跑 `tests/no_second_run_state_test.sh` | 啟動 Nextflow 的指令字樣只出現在 `platform/abf_station/launch.py` 一處；`build.py`、`pipeline_launch.py` 都沒有 | 自動：`tests/no_second_run_state_test.sh` |
| TC-174 | 憲法 2（送出前看過完整指令與內容） | 功能 | 一份組合的確認畫面 | 看畫面 | 本人在按送出前能看到要跑什麼：`head.sh`（含最後一行啟動 `pipeline/main.nf`）、完整 `main.nf` 與 `nextflow.config`、其餘檔的路徑與雜湊（TC-132、133 的內容） | 自動：`test_pipeline_launch.py` |
| TC-175 | 憲法 3（沒有個人路徑或叢集路徑寫死）；`tests/no_hardcoded_paths.sh` | 功能 | 新增的程式、夾具、資料檔 | 跑 `tests/no_hardcoded_paths.sh` 與 `test_scope.py` TC-072 | 全綠；run 資料夾等位置都來自站台設定與內容包，不是寫死 | 自動：`tests/no_hardcoded_paths.sh`、`test_scope.py` TC-072 |
| TC-176 | 憲法 4（指令層不指名排程器）；`tests/command_layer_is_site_neutral.sh` | 功能 | 本任務的程式（`build.py`、`pipeline_launch.py` 屬平台層，`sbatch` 只在站台 `launch.py`） | 跑 `tests/command_layer_is_site_neutral.sh` | 綠；指令層沒有因本任務而指名排程器、分區、佇列 | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-177 | 憲法 6（任何管線免設定）；`tests/no_per_pipeline_config.sh` | 功能 | 本任務新增的程式與資料 | 跑 `tests/no_per_pipeline_config.sh` | 綠；沒有為某個特定管線新增設定檔（模組檔資料是依 nf-core/modules 整包快照，不是逐管線設定） | 自動：`tests/no_per_pipeline_config.sh` |
