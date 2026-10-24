# 測試案例：續跑可改參數與資源（a：站台與 bundle）（resume-edit-params-a）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) from the plan only: there is no spec.md for this task.
The maintainer's words are quoted in plan.md under 「維護者原話」 and in the 「完成標準」 example; every row below comes from a line of
plan.md (目標, A-E 節, 失敗先行測試, 完成標準, 不做, 裁決, 裁決二, 專長守則). Nothing was added that the plan does not state.
-->

**規格**：`specs/resume-edit-params-a/plan.md`（本件沒有 spec.md，計畫即依據）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、被改動、不合規則時，系統怎麼反應（拒絕、點名、停下，且沒有寫入）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白拒絕而不是悄悄接受。

名詞：

- 「續跑」＝讓 Nextflow 在同一個專屬資料夾接著上次跑，沒被改動影響的已完成工作沿用快取。
- 「改動」＝`overrides`，形狀 `{"params": {只含被改或新增的參數}, "extra_config": "額外設定文字"}`。
- 「原始內容包」＝第一次送出時的內容包（`origin`），含四個原檔：`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`。
- N＝這次是第幾次嘗試（`attempt`，2 以上）。新檔名依 N：`head-N.sh`、`params-N.yaml`、`extra-N.config`。
- 「站台」＝代理在國網那一端實際寫檔、送出 Slurm 工作的程式；測試用的是會真的跑 shell 的假站台。
- 「yes」＝本人在確認畫面按送出；「yes 之後被改」＝內容包在確認之後被換成別的內容。
- 自動驗證檔：`platform/tests/test_resume_edit_params_station.py`（以下簡稱「新測試檔」）；每個測試在註解裡寫出它對應的 TC 編號。
- 「手動（閱卷）」＝閱卷者讀本任務的 `ledger.md` 與 `git diff --stat`／diff 逐句對照預期結果，不需要另寫文件（計畫裁決二.5；本片不改 `docs/`）。
- 「黃金文字／黃金雜湊」＝在改動程式之前、由今天的行為產生並寫死在測試裡的文字或 sha256；不得用 `origin/v3` 或 `git diff <base>` 當比較對象，也不得改動後再重新產生貼上。
- 各 TC 的「對應需求」欄寫的是計畫章節與計畫「失敗先行測試」裡的具名測試。

## User Story 1 — 帶改動的續跑，多寫新檔、原檔不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | B 節；完成標準第 1 條；`test_overrides_change_the_head_script_and_add_files_only` | 功能 | 一份第一次送出的原始內容包；attempt=2 | 呼叫續跑的檔案產生，帶 `overrides={"params": {"min_reads": 100}, "extra_config": "process.memory = '16 GB'"}` | 回傳的字典鍵依序恰為 `head-2.sh`、`params-2.yaml`、`extra-2.config`，沒有第四個鍵 | 自動 |
| TC-002 | B 節（最後一行）；`test_overrides_change_the_head_script_and_add_files_only`、`test_the_extra_file_has_the_header_comment_and_comes_after_nextflow_config` | 功能 | 同 TC-001 | 讀 `head-2.sh` 的最後一行 | 形如 `exec nextflow run <目標> -resume <session> -name <新名> -params-file params-2.yaml …  -c nextflow.config -c extra-2.config -with-tower <endpoint>`：用的是 `params-2.yaml`（不再出現 `-params-file params.yaml`）；`-c extra-2.config` 緊接在 `-c nextflow.config` 之後（順序是先 nextflow.config 後 extra）；若環境有站台設定檔，它們的 `-c` 仍排在 `-c nextflow.config` 之前 | 自動 |
| TC-003 | B 節（沒有 `extra_file` 時沒有 `-c extra-N.config`）；`test_overrides_change_the_head_script_and_add_files_only` | 功能 | 一份原始內容包；attempt=2 | 只帶 `overrides={"params": {"min_reads": 100}}`（沒有 extra_config） | 回傳的鍵依序恰為 `head-2.sh`、`params-2.yaml`；沒有 `extra-2.config`；`head-2.sh` 最後一行有 `-params-file params-2.yaml`，且整行沒有 `extra-2.config` | 自動 |
| TC-004 | B 節（有改動時一律多寫 `params-N.yaml`；N 依 attempt）；A 節 | 功能 | 一份原始內容包；attempt=3 | 只帶 `overrides={"extra_config": "process.cpus = 4"}`（沒有 params） | 回傳的鍵依序恰為 `head-3.sh`、`params-3.yaml`、`extra-3.config`（編號都是 3）；`params-3.yaml` 含原始內容包 `params` 的每一個鍵與值，沒有多出任何參數 | 自動 |
| TC-005 | B 節（`params-N.yaml` 的 `input`／`outdir`）；`test_params_yaml_keeps_input_and_outdir_of_the_origin_folder` | 功能 | 一份原始內容包，帶任一合法參數改動 | 讀 `params-N.yaml` | `input` 指向原專屬資料夾的 `samplesheet.csv`，`outdir` 指向原專屬資料夾的 `results`（與原始 `params.yaml` 的兩行相同），不指向任何新位置 | 自動 |
| TC-006 | B 節（`extra-N.config` 內容）；`test_the_extra_file_has_the_header_comment_and_comes_after_nextflow_config` | 功能 | 一份原始內容包；attempt=3；extra_config 為合法的一行 | 讀 `extra-3.config` | 第一行恰為 `// added by the platform: extra settings of resume 3`，其後是使用者的文字；整個檔結尾剛好一個換行：使用者文字結尾沒有換行、有一個換行、有多個空行三種寫法，寫出的檔都剛好以一個換行結尾 | 自動 |
| TC-007 | 裁決二.2；B 節 | 功能 | extra_config 的行首有空格或 tab 縮排、行尾有空白，其餘合法（例如區塊內縮排的 `cpus = 4`） | 產生續跑檔案 | 不被拒絕；寫出的 `extra-N.config` 保留使用者的縮排與行尾空白（比對規則時才去掉，寫出時不改） | 自動 |
| TC-008 | 目標；B 節；E 節；`test_overrides_change_the_head_script_and_add_files_only` | 功能 | 一份原始內容包 | 帶改動產生續跑檔案後，檢查原始內容包 | 原始內容包的四個原檔文字（`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`）與產生前逐位元組相同；回傳的字典裡沒有這四個檔名的任何一個 | 自動 |

## User Story 2 — 參數是「蓋上去」，並沿用啟動時的驗證（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | A 節（語意）；`test_params_overlay_replaces_keeps_and_adds_and_never_deletes` | 功能 | 原始參數有 `a`、`b`；改動帶 `{"params": {"a": 新值, "c": 新鍵}}` | 讀 `params-N.yaml` | `a` 是新值（同名取新）；`b` 保留原值（沒提到的保留）；`c` 被新增；`input`、`outdir` 照舊 | 自動 |
| TC-010 | A 節（不支援刪除）；裁決 5；`test_params_overlay_replaces_keeps_and_adds_and_never_deletes` | 不在範圍 | 原始參數有 `b`；改動不提 `b` | 讀 `params-N.yaml`；另試把 `b` 設成 `None` | `b` 仍在且是原值（沒有任何辦法在續跑中刪掉參數）；`{"b": None}` 被拒絕並點名 `b` | 自動 |
| TC-011 | C 節（`params` 合併後整份再驗）；`test_params_overrides_are_refused_like_a_launch` | 例外 | 改動的 `params` 含 `input`，或含 `outdir` | 產生續跑檔案 | 兩種都被拒絕（BundleError）並在訊息點名 `input` 或 `outdir`；沒有回傳任何檔 | 自動 |
| TC-012 | C 節；`test_params_overrides_are_refused_like_a_launch` | 例外 | 改動的 `params` 分別含：巢狀字典、list、`None`、`nan`、`inf`、壞的名稱（如 `1bad`、含空格） | 逐案產生續跑檔案 | 每一案都被拒絕並點名該參數名；每一案的拒絕結果與同一個值交給啟動時的參數檢查（`_check_params`）完全一致（同樣被拒、點名同一個鍵） | 自動 |
| TC-013 | C 節（`_check_text`）；`test_params_overrides_refuse_control_characters_and_overlong_text` | 例外 | 改動的某個字串參數分別含：NUL、CR、ESC、雙向控制字元，或長度超過字元上限 | 逐案產生續跑檔案 | 每一案被拒絕，訊息點名該參數；沒有回傳任何檔 | 自動 |
| TC-014 | A 節（形狀錯誤）；`test_overrides_of_the_wrong_shape_are_refused` | 例外 | `overrides` 分別為：多一個 `params`、`extra_config` 以外的鍵（如 `queue`）；`params` 不是字典（如 list）；`extra_config` 不是字串（如數字） | 逐案產生續跑檔案 | 每一案被拒絕（BundleError），訊息同時有中文與英文，並點名出錯的欄位（未知的鍵／`params`／`extra_config`）；沒有回傳任何檔 | 自動 |
| TC-015 | A 節（不收）；不做 | 不在範圍 | `overrides` 分別帶 `samplesheet`、`input`、`outdir`、`pipeline`、`revision`、`ce`、`session_id`、`run_name` 這幾個鍵 | 逐案產生續跑檔案 | 每一案都被拒絕並點名該鍵；樣本表、管線、版本、環境、session id、run 名稱仍只由原始內容包與呼叫端決定，無法經由改動更換 | 自動 |

## User Story 3 — 額外設定檔（extra_config）只收封閉的資源語法（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | C 節（單行賦值與各 key 的值）；`test_extra_config_accepts_the_resource_lines` | 功能 | extra_config 分別為：`process.memory = '8 GB'`、`process.cpus = 4`、`process.time = '1h 30m'`、`process.errorStrategy = 'retry'`、`process.maxRetries = 3`、`process.disk = '100.5 GB'`、`process.memory = '512MB'`（單位前無空白） | 逐案產生續跑檔案 | 每一案都被接受，`extra-N.config` 含該行；各 key 的值形式：`memory`／`disk` 單位 B／KB／MB／GB／TB；`time` 單位 ms／s／m／h／d、可多段以空白相接；`errorStrategy` 為 retry／terminate／ignore／finish；`cpus`／`maxRetries` 至多 4 位整數 | 自動 |
| TC-017 | C 節（區塊）；裁決二.1；`test_extra_config_accepts_the_resource_lines` | 功能 | extra_config 是分行寫的區塊：`process {` ／ `withName: 'FASTQC' {` ／ `cpus = 4` ／ `}` ／ `}`；另一份把 `withName` 換成 `withLabel: 'process_high' {`；另一份在其中夾註解（整行 `//`）與空行 | 逐案產生續跑檔案 | 三份都被接受，`extra-N.config` 含原樣的各行 | 自動 |
| TC-018 | 裁決二.1；`test_extra_config_refuses_everything_else`（另加：同一行寫法被拒且訊息含分行提示） | 例外 | extra_config 為 `process { withName: 'X' { cpus = 4 } }`（整個區塊寫在同一行） | 產生續跑檔案 | 被拒絕，訊息點名該行，並提示「請分行寫，每行一個 `{`、一個設定或一個 `}`」 | 自動 |
| TC-019 | C 節（封閉語法）；`test_extra_config_refuses_everything_else` | 例外 | extra_config 分別為含以下寫法的一行：`$`（如 `process.memory = "${x}"`）、反引號、`.execute`、`new`、閉包（`{ … ->`、`{ task`）、條件式資源（`process.memory = { 4.GB * task.attempt }`） | 逐案產生續跑檔案 | 每一案整份被拒絕，訊息點名第幾行與被違反的規則；沒有回傳任何檔 | 自動 |
| TC-020 | C 節（不符合任何行而被拒的清單）；不做；`test_extra_config_refuses_everything_else` | 不在範圍 | extra_config 逐一為：`includeConfig`、`env`、`workDir`、`executor`、`tower`、`params`、`report`、`timeline`、`trace`、`dag`、`docker`、`singularity`、`apptainer`、`container`、`beforeScript`、`afterScript`、`ext`、`publishDir`、`queue`、`clusterOptions`、`maxErrors` 的設定行；每個都以單行 `process.<名> = …`（或 `<名> = …`／`<名> { …`）與區塊內 `<名> = …` 兩種寫法各試一次 | 逐案產生續跑檔案 | 清單裡每一個、每種寫法都被拒絕（測試要逐一列出，不得以抽樣代替），訊息點名第幾行；這些設定在續跑裡明確不支援 | 自動 |
| TC-021 | C 節（`<值>` 依 key）；`test_extra_config_refuses_everything_else` | 例外 | extra_config 分別為：`process.cpus = 12345`（5 位）、`process.cpus = 1.5`、`process.memory = 8`（沒有引號）、`process.memory = '8 XB'`（未知單位）、`process.time = '1x'`、`process.errorStrategy = 'foo'`、`process.maxRetries = 'a'` | 逐案產生續跑檔案 | 每一案被拒絕並點名第幾行 | 自動 |
| TC-022 | C 節（大括號必須成對） | 例外 | extra_config 分別為：`process {` 與 `cpus = 4` 後缺少 `}`；多出一個單獨的 `}` | 逐案產生續跑檔案 | 兩案都被拒絕並點名行 | 自動 |
| TC-023 | C 節（巢狀最多兩層） | 例外 | extra_config 為 `process {` 內再開 `withName: 'A' {`，其內又開 `withLabel: 'B' {`（三層） | 產生續跑檔案 | 被拒絕並點名該行 | 自動 |
| TC-024 | C 節（行尾不准再接註解） | 例外 | extra_config 為 `process.cpus = 4 // more`；另一份為 `// note // more`（整行註解後再接註解） | 逐案產生續跑檔案 | 兩案都被拒絕並點名該行 | 自動 |
| TC-025 | C 節（`<名>` 只含 `A-Za-z0-9_:.*|-`，最長 200） | 例外 | `withName` 的名稱分別為：含空格、含 `;`、含 `$` 的名稱，長度 201 的名稱；另一份名稱剛好 200 個合法字元 | 逐案產生續跑檔案 | 含不合法字元的與長 201 的被拒絕並點名該行；長度剛好 200 的合法名稱被接受 | 自動 |
| TC-026 | C 節②（只准 ASCII 可列印加換行與 tab，不准反斜線）；`test_extra_config_is_ascii_only_without_backslash_or_cr` | 例外 | extra_config 分別為：註解裡有中文字、有 `é`、有 0x7F、有其他控制字元（如 0x01）、有 CR（`\r`）、有反斜線（含註解裡的 `// A`） | 逐案產生續跑檔案 | 每一案整份被拒絕；tab 與換行仍可使用（TC-007 與 TC-017 的縮排、多行不受影響） | 自動 |
| TC-027 | C 節①（`MAX_EXTRA_CONFIG = 20000`）；`test_extra_config_too_long_is_refused` | 例外 | 一份由合法註解行組成、長度剛好 20000 字元的 extra_config；一份 20001 字元的 | 逐案產生續跑檔案 | 20000 字元者被接受；20001 字元者被拒絕，訊息點名 `extra_config` 與長度上限 | 自動 |
| TC-028 | C 節末段（OVERWRITE_BLOCK 不得被蓋掉）；`test_extra_config_cannot_undo_the_platforms_overwrite_block` | 例外 | extra_config 分別為 `report.overwrite = false`、`timeline.overwrite = false` | 逐案產生續跑檔案 | 兩案都被拒絕（它們不符合任何允許的行）；平台寫進 `nextflow.config` 的 `report.overwrite = true`、`timeline.overwrite = true` 因此不可能被後讀的 `extra-N.config` 蓋掉 | 自動 |
| TC-029 | C 節（不符合任何一種行＝整份拒絕，訊息點名第幾行與規則） | 例外 | extra_config 共五行：第 1、2、4、5 行合法，第 3 行是不合法的一行（如 `process.queue = 'x'`） | 產生續跑檔案 | 整份被拒絕（前面合法的行不會被單獨接受）；訊息點名「第 3 行」（第一行算第 1 行）與被違反的規則，並說明該怎麼改（改成允許的資源行或拿掉該行）；訊息沒有堆疊追蹤 | 自動 |

## User Story 4 — 沒有改動時，與今天逐位元組相同（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 目標；裁決 4；`test_without_overrides_the_resume_is_byte_for_byte_today` | 功能 | 一份原始內容包；attempt=2；不帶 `overrides` | 產生續跑檔案 | `head-2.sh` 全文等於測試裡寫死的黃金文字（今天的輸出）；回傳的字典只有 `head-2.sh` 一個鍵 | 自動 |
| TC-031 | D 節；`test_without_overrides_the_resume_is_byte_for_byte_today` | 功能 | 同 TC-030，改為產生續跑內容包 | 讀內容包 | `files` 只有 `head-2.sh`；`resume` 的鍵恰為 `of_run`、`of_slurm_job_id`、`session_id`、`attempt`、`origin`，沒有 `overrides` 這個鍵 | 自動 |
| TC-032 | A 節（正規化）；`test_empty_overrides_are_no_overrides` | 功能 | 原始內容包；改動分別為 `None`、`{}`、`{"params": {}}`、`{"extra_config": ""}`、`{"params": {}, "extra_config": ""}` | 逐案產生續跑檔案與續跑內容包 | 每一案的檔案、內容包（含 `resume` 沒有 `overrides` 鍵）與 sha256 都和「不帶 `overrides`」的結果完全相同 | 自動 |
| TC-033 | 目標；完成標準第 2 條；裁決 4 | 功能 | 同 TC-030 的無改動續跑內容包 | 算內容包的 sha256 | 等於測試裡寫死的黃金雜湊（今天的值）；已確認但還沒執行的舊請求因此不受影響 | 自動 |
| TC-034 | 「必須仍綠、不准改」；專長守則（新函式名不得含 resume／relaunch） | 功能 | 本任務完成；既有測試檔一個字沒改 | 跑 `test_resume_render.py`、`test_station_resume.py`、`test_launch_bundle.py`、`test_resume_platform.py`、`test_resume_scope.py`、`test_keep_submissions.py`（含 TC-084 掃函式名） | 全部通過；新增的函式（`_check_extra_config` 等）名稱不含 `resume`／`relaunch`，所以 TC-084 仍綠 | 自動 |
| TC-035 | E 節（不需要 migration；舊的續跑 bundle 沒有 `overrides`）；`test_station_without_overrides_writes_exactly_head_and_token` | 功能 | 一份不帶 `overrides` 的續跑內容包（舊形狀），資料夾是第一次送出時的樣子 | 交給站台執行 | 狀態完成；tar 寫入的檔恰為 `head-N.sh` 與 `tower.token`；一次 `sbatch`；沒有 `params-N.yaml`、`extra-N.config` | 自動 |

## User Story 5 — 改動在內容包裡，也在雜湊裡（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | D 節；裁決二.4；`test_overrides_are_in_the_bundle_and_in_its_hash` | 功能 | 原始內容包；分別帶：params 與 extra_config 兩項；只帶 params；只帶 extra_config | 產生續跑內容包，讀 `resume` | `resume.overrides` 存在，內容是正規化後的改動：兩項都帶時兩項都在；只帶一項時只有那一個鍵（空字串、空字典的項不放鍵）；`files` 多了 `params-N.yaml`（與 `extra-N.config`，若有）；`resume.origin` 與輸入的原始內容包深度相等；`resume.overrides` 的 extra_config 文字與寫進 `extra-N.config` 的使用者部分一致 | 自動 |
| TC-037 | D 節；`test_overrides_are_in_the_bundle_and_in_its_hash` | 功能 | 一份帶改動的續跑內容包及其 sha256 | 分別改動其中一處：`resume.overrides.params`、`resume.overrides.extra_config`、`files["params-N.yaml"]`、`files["extra-N.config"]`、`files["head-N.sh"]`，再算 sha256 | 每改一處，sha256 都不同於原值（改動在雜湊之內，平台端的 sha 比對才擋得住） | 自動 |
| TC-038 | D 節；`test_a_site_module_origin_takes_overrides` | 功能 | 原始內容包是用站台上的本地模組啟動的（`pipeline_source` 為 site-module） | 帶合法改動產生續跑檔案 | 被接受；`head-N.sh` 照本地模組的寫法執行（用該模組的家目錄變數而非遠端管線），且仍有 `-params-file params-N.yaml` 與 `-c extra-N.config` | 自動 |
| TC-039 | 範圍說明；不做；裁決 6；`test_composed_and_google_batch_origins_are_still_refused_with_overrides` | 不在範圍 | 原始內容包是組合圖（composed）送出的 | 帶合法改動產生續跑檔案，並把同樣的續跑內容包交給站台 | 兩處都被拒絕，用的是原有的字句 `COMPOSED_NO_RESUME`（續跑一律維持拒絕，不因帶了改動而放行）；站台沒有寫入任何東西 | 自動 |
| TC-040 | 範圍說明；不做；裁決 6；`test_composed_and_google_batch_origins_are_still_refused_with_overrides` | 不在範圍 | 續跑內容包（外層或 origin 的環境）是 Google Batch 的 run，且帶改動 | 交給站台 | 被拒絕，用的是原有的字句 `GCB_NO_RESUME`；沒有寫入、沒有 sbatch | 自動 |

## User Story 6 — 站台只執行確認過的那一份，並且只新增檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | 完成標準第 1 條；E 節；`test_station_writes_the_new_files_once_and_leaves_the_originals_alone` | 功能 | 資料夾是第一次送出的樣子（四個原檔、`tower.token`、`.nextflow/history`、`work/` 裡有已完成的工作）；內容包帶 `overrides={"params": {"min_reads": 100}, "extra_config": "process.memory = '16 GB'"}` 且已確認 | 交給站台執行 | 狀態完成；資料夾裡寫入了 `head-N.sh`、`params-N.yaml`、`extra-N.config`、`tower.token`；一次 `sbatch`（送的是 `head-N.sh`）；四個原檔的內容與 sha 與執行前相同；`work/` 與 `.nextflow/` 與執行前相同 | 自動 |
| TC-042 | E 節（一次 `tar -x` 寫入這次的新檔＋token）；`test_station_writes_the_new_files_once_and_leaves_the_originals_alone` | 功能 | 同 TC-041；另一案只帶 params | 檢查站台收到的 tar | 帶兩項改動時，tar 的檔恰為 `head-N.sh`、`params-N.yaml`、`extra-N.config`、`tower.token`；只帶 params 時恰為 `head-N.sh`、`params-N.yaml`、`tower.token`；兩案都是一次寫入、一次 `sbatch` | 自動 |
| TC-043 | D 節；`test_station_refuses_a_bundle_changed_after_the_yes` | 例外 | 一份帶改動、已確認的續跑內容包；yes 之後分別改：`resume.overrides.params`、`files["params-N.yaml"]`、`files["extra-N.config"]`、`files["head-N.sh"]` | 逐案交給站台 | 每一案都被拒絕（與代理依自己設定重建的內容包不一致）；沒有寫入、沒有 `sbatch`、資料夾與執行前相同 | 自動 |
| TC-044 | D 節；`test_station_refuses_a_bundle_changed_after_the_yes` | 例外 | 同 TC-043；yes 之後分別：拿掉 `resume.overrides`；給一份沒有改動卻多放了空的 `overrides`（`{}`）的無改動內容包；在 `resume` 裡多加一個不認得的鍵 | 逐案交給站台 | 每一案都被拒絕；沒有寫入、沒有 `sbatch` | 自動 |
| TC-045 | D 節（連 sha 一起改）；`test_station_refuses_a_bundle_changed_after_the_yes` | 例外 | 同 TC-043；改過的內容包連同它的 `bundle_sha256` 與確認一起配合改過（假裝確認是對這份被換過的內容做的） | 交給站台 | 仍被拒絕：重建比對（代理自己重新算出整份內容包）擋下，不是只靠 sha；沒有寫入 | 自動 |
| TC-046 | D 節（`origin` 必須等於代理重新產生的第一次內容包）；`test_station_origin_changed_consistently_is_refused` | 例外 | 續跑內容包的 `origin`（例如其中的參數與對應的原檔文字）被一致地改成另一組值，sha 與確認也配合 | 交給站台 | 被拒絕：只有 `overrides` 的內容可以不同於 origin，origin 必須等於代理用自己設定重新產生的第一次內容包；沒有寫入 | 自動 |
| TC-047 | E 節（`_probe`／`_check_folder` 的 `exists=`）；`test_station_refuses_when_params_n_or_extra_n_exists_or_is_a_link` | 例外 | 專屬資料夾裡已有一個一般檔 `params-N.yaml`；另一案已有 `extra-N.config`（內容包兩個檔都要寫） | 逐案交給站台 | 兩案都被拒絕，訊息點名該檔名，說明不覆蓋；沒有寫入任何檔（包含 `head-N.sh`、`tower.token`）、沒有 `sbatch`；既有的那個檔內容沒被動過 | 自動 |
| TC-048 | E 節（捷徑也算存在）；`test_station_refuses_when_params_n_or_extra_n_exists_or_is_a_link` | 例外 | 專屬資料夾裡 `params-N.yaml`（另一案 `extra-N.config`）是一個指向別處的捷徑（symlink） | 逐案交給站台 | 兩案都被拒絕並點名該檔；沒有寫入、沒有 `sbatch`；捷徑指向的目標沒被寫入 | 自動 |
| TC-049 | E 節（四個原檔的 sha 檢查完全不動）；`test_original_files_sha_check_still_applies_with_overrides` | 例外 | 帶改動的續跑內容包；專屬資料夾裡原檔 `params.yaml` 被人改過一個字（另一案是原檔不見了） | 逐案交給站台 | 兩案都被拒絕，訊息點名 `params.yaml`（和第一次送出時寫下的不一樣，或不見了）；沒有寫入、沒有 `sbatch` | 自動 |
| TC-050 | 不變的底線（確認只用一次）；`test_a_resume_confirmation_with_overrides_is_spent_once` | 例外 | 一份帶改動的續跑已確認並成功執行過一次 | 把同一份工作（同一個確認）再交給站台一次 | 第二次被拒絕（確認已用過）；第二次沒有寫入、沒有新的 `sbatch`，總共只有一次 `sbatch` | 自動 |

## 憲法、安全網與完成標準

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 安全網「寫入都要人說 yes」；原則 I.2（確認通道）；維護者底線「任何寫入都要人說 yes」 | 例外 | 一份帶改動的續跑工作，其確認不存在，或確認是針對另一份內容包的（內容不符），或確認屬於另一個代理 | 交給站台 | 被拒絕；在拒絕之前站台上沒有任何寫入、沒有 `sbatch`（只有唯讀的查詢） | 自動 |
| TC-052 | 安全網「不刪使用者資料」；E 節（什麼都不刪、不改原檔） | 功能 | 同 TC-041 的成功執行，站台記錄所有指令 | 檢查站台收到的所有指令與執行後的資料夾 | 沒有任何刪除或危險指令；`samplesheet.csv`、`nextflow.config`、`params.yaml`、`head.sh`、`work/`、`.nextflow/` 都在且內容不變；比執行前多的只有新檔與被換新的 `tower.token` | 自動 |
| TC-053 | 完成標準第 4 條；範圍：檔案（只准改 3 個）；裁決二.5 | 功能 | 本任務完成後的分支 | 閱卷者看 `git diff --stat`／diff（對 base 分支） | 只含三個路徑：`platform/abf_station/launch.py`、`platform/tests/test_resume_edit_params_station.py`、`specs/resume-edit-params-a/ledger.md`；沒有改 `resume_harness.py`、`station_harness.py`、其他測試檔、`docs/`、`skills/`、`pyproject.toml`、`constraints.txt`、`scripts/launch_recheck.sh`、`hooks/*`、`spec`／`test-case*.md`；既有測試沒有被刪減或放鬆的斷言 | 手動（閱卷） |
| TC-054 | 完成標準第 5 條；環境事實（尚未在國網實測）；裁決二.5 | 功能 | 本任務完成後的 `specs/resume-edit-params-a/ledger.md` | 閱卷者讀 ledger | 內有明寫的一句：未在國網實測改參數後沿用快取（手動檢查在 d 片的 TESTING.md）；沒有任何字句聲稱已在國網驗證沿用快取 | 手動（閱卷） |
| TC-055 | 安全網「憑證不在 params 檔、不被印出」；專長守則（密鑰不得出現在日誌或回應） | 功能 | 一次帶改動、成功的續跑，token 是一個可辨認的測試值 | 找該 token 值 | 只出現在站台資料夾的 `tower.token`；不在 `params-N.yaml`、`extra-N.config`、`head-N.sh`、內容包、工作結果與代理輸出裡 | 自動 |
| TC-056 | 原則 I.2（不得有第二份 run 狀態）；`test_no_second_copy_of_run_state` | 功能 | 本任務完成後的工作樹 | 跑 `bash tests/no_second_run_state_test.sh` | 通過；提交掃描與狀態掃描都沒有新發現 | 自動 |
| TC-057 | 不做；裁決 7；專長守則（資料結構變動要有 migration 或明寫不需要） | 不在範圍 | 本任務完成後的 diff | 閱卷者讀 diff 與計畫「E 節」「不做」 | 沒有 platform 端變動（`platform/abf_platform/`、`abf_launch/` 無改動，沒有任何呼叫端傳入 `overrides`，所以使用者看不到變化）；沒有新增動作、CLI、MCP 工具、畫面或 job 種類；`jobs.py`、`store.py` 沒變；relaunch 的程式沒變；沒有資料庫結構變動也沒有 migration 檔（計畫已明寫不需要 migration） | 手動（閱卷） |
| TC-058 | 「必須仍綠」；完成標準第 3 條 | 功能 | 本任務完成後的 HEAD | 在 WSL／Linux 跑全套 `platform/tests` 與 `tests/run_all.sh`；CI | 全綠；新測試檔的全部測試都在其中且通過 | 自動 |
| TC-059 | 完成標準第 4 條（證據貼 ledger）；裁決二.4 | 功能 | 本任務完成後的 ledger | 閱卷者讀 ledger | 內有 `git diff --stat` 的輸出（只有三個路徑）；內有一句記錄「正規化後的 `resume.overrides` 省略空的項」 | 手動（閱卷） |

<!--
Notes for the acceptance reviewer (not test rows):
- 專長守則（backend）對照：確認管道 TC＝TC-051；錯誤訊息 TC＝TC-014、TC-018、TC-029（說明原因與處理方式、無堆疊）；密鑰 TC＝TC-055；migration＝TC-057（不需要，計畫已明寫）。
- 對等性 TC（動作清單對動作層函式清單）與跨使用者 TC：本片沒有新增任何使用者可見的動作、路由或紀錄（platform 端是 b 片），所以沒有新的對等性或跨使用者 TC；TC-057 確認這件事。
- 弱化檢查：TC-034 與 TC-053 一起確認既有測試沒被放鬆。
-->
