---
id: resume-edit-params-a
title: 續跑的內容包與站台端：可帶「改過的參數」與「資源設定檔」，多寫兩個新檔、原四檔不動（只動 abf_station/launch.py；還沒有任何呼叫端會用到）
tier: C
kinds: backend
lane: L12-resume
base: v3
after:
source: resume-edit-params 的第 1 片（共 4 片：a 站台與內容包、b 動作層與 CLI／MCP 與確認畫面、c 被測試釘住的字句與技能與 ADR、d PLATFORM.md／TESTING.md）；維護者 10-23 常設方向「跟Seqera platform一樣的模式，不要自己定義」；維護者 2026-10-24 11:20 核可此 C 級改動；docs/adr/0009-web-layout-three-panes.md 第 44-46 行；spec 009e
---

# resume-edit-params-a

> 本檔由 developer-agent 依 `resume-edit-params.md`（舊版，不再派）重新切分，行號重對 `origin/v3` @ `b5dcb09`（已含 017d #190）。**只處理本任務**。前置：017d、gcb-launch 已合進 v3，無需等其他任務；從最新 `origin/v3` 開分支。
> 本片完成後 `render_resume*` 與 `run_resume` 已能處理改動，但 **platform 端沒有任何呼叫端傳入改動**，所以對使用者沒有可見變化；b 片才接上。
> 組合圖（017d）與 Google Batch 的 run，續跑仍然拒絕（`launch.py:754`、`:1158`、`:1163` 已有，不動）。

## 目標
讓站台代理能執行「帶改動的續跑」：改過的參數與資源設定另存成這次嘗試的新檔，Nextflow 用它們接著跑，沒受影響的已完成 task 沿用快取。原本四個檔（`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`）一個字不動，站台仍用它們的 sha 檢查資料夾還是不是第一次送出的那個。沒有改動時，行為與內容包 hash 與今天逐位元組相同。

## 維護者原話（verifier 出題用）
- 「續跑可改參數與資源（照 Seqera）」——developer-agent 提案 2026-10-24 02:00；維護者在 2026-10-24 12:00 期限前沒有回覆 → 依預設照此範圍進行。
- 維護者 10-23 常設方向：「跟Seqera platform一樣的模式，不要自己定義」→ 名詞與行為照 Seqera 的 Resume（改參數、加設定檔，其餘不動）；不自創新概念。
- 維護者 10-24：「所有 PR 自己合併」→ Tier C（改方向）仍由 developer-agent 在 verifier PASS 與 CI 綠之後合併。
- 009e 原設計（被本任務翻掉的部分）：「續跑只收 run 名稱」；ADR 0009：「changing the samples or the parameters starts a new analysis」→ 現在變成「改樣本表／管線／版本／環境＝新分析；改一部分參數與資源＝仍是同一個分析的下一次嘗試」。
- 不變的底線（009e／憲章）：任何寫入都要人說 yes；續跑只在同一個專屬資料夾；原本四個檔（`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`）不被改動，站台用它們的 sha 檢查資料夾還是不是第一次送出的那個。
- 補記（2026-10-24 11:20）：維護者核可「這是 C 級改動」，可依此拆片進行。
- 本片負責的句子：「可以改一部分參數、可以加資源設定」「原本四個檔不被改動」「任何寫入都要人說 yes（yes 之後改任何東西都會被擋）」。

## 範圍：檔案（最終版，3 個；只准改這些）
- `platform/abf_station/launch.py`（改：`_head_script` 加兩個可選參數；`render_resume`、`render_resume_bundle` 加 `overrides=None`；新增 `MAX_EXTRA_CONFIG`、`_check_extra_config`、`RESUME_OPTIONAL`（新增的函式名不得含 `resume`／`relaunch`，`test_keep_submissions.py:782` 的 TC-084 會掃；常數不受限）；改 `run_resume`、`_probe`、`_check_folder`）
- `platform/tests/test_resume_edit_params_station.py`（新；用 `resume_harness.py`、`station_harness.py` 的現成夾具，**不改**那兩個檔）
- `specs/resume-edit-params-a/ledger.md`（新）

**不准動**：`platform/abf_platform/` 底下全部（含 `web.py`、`jobs.py`、`store.py`、`confirm.py`、`actions/`）、`platform/abf_launch/`、其他測試檔（既有斷言一個字都不改）、`docs/`、`skills/`、`pyproject.toml`、`constraints.txt`、`scripts/launch_recheck.sh`、`hooks/*`。`flaky-tests` 計畫列的測試檔不碰。

## 作法
行號皆 `origin/v3` @ `b5dcb09`。

### A. 兩個新輸入（只在續跑，只在 `abf_station/launch.py`）
- `overrides`：可選的對照，形狀 `{"params": {只含被改或新增的鍵}, "extra_config": "文字"}`。**正規化**：缺的鍵、`{}`、空字典、空字串＝沒有該項；兩項都沒有（或 `overrides` 為 `None`）＝**沒有改動**，輸出與今天逐位元組相同。出現這兩個鍵以外的鍵、型別不對（`params` 不是字典、`extra_config` 不是字串）＝`BundleError`，訊息點名欄位（中英）。
- 語意：`params` **蓋在第一次送出的參數（`origin["params"]`）上**——同名取新值、沒提到的保留、可新增鍵、**不支援刪除**（要拿掉就改成預設值，或重新 launch）。`extra_config` 是額外的 Nextflow 設定，只收資源類（C 節）。
- **不收**：樣本表、`input`、`outdir`、管線、版本、CE、session id、run 名稱——仍由 `origin` 與呼叫端決定。

### B. 檔案與指令
有改動時（N＝attempt 數，`:745` 已限定 2–9999 的整數），`render_resume` 回傳的字典依序多寫：
- `params-N.yaml`＝`_params_yaml(合併後的 params, origin["run_folder"])`（`:403`；`input`／`outdir` 照舊指向原資料夾的 `samplesheet.csv`／`results`）。取代 `params.yaml` 的角色；**原 `params.yaml` 不動**。
- `extra-N.config`：只在 `extra_config` 非空時才有。內容＝一行 `// added by the platform: extra settings of resume N`＋使用者的文字（結尾補一個換行）。
- `head-N.sh`：`_head_script`（`:416`）加兩個可選參數 `params_file="params.yaml"`、`extra_file=None`。最後一行（`:465-466`）變成
  `exec nextflow run <target>[ -resume <session>] -name <新名> -params-file params-N.yaml<site -c …> -c nextflow.config -c extra-N.config -with-tower <endpoint>`（沒有 `extra_file` 時沒有 `-c extra-N.config`）。`-c extra-N.config` 緊接在 `-c nextflow.config` 之後，所以它比平台的 `OVERWRITE_BLOCK`（`:52`）更晚被讀——這就是 C 節必須是封閉語法的原因。兩個參數取預設時輸出與今天逐位元組相同。組合圖的分支（`:461-463`）不動（續跑本來就拒絕）。
- 字典鍵的順序固定為 `head-N.sh`、`params-N.yaml`、`extra-N.config`。

### C. 驗證（沿用啟動時的規則，不新發明）
- `params`：合併後整份再過 `_check_params`（`:325`）——拒絕 `input`／`outdir`、拒絕非純量（巢狀、list、None）、非有限數字、名稱格式、`_check_text` 的長度與 NUL／CR／ESC／雙向控制字元。
- `extra_config`，依序：①`_check_text("extra_config", 文字, allow_cr=False, limit=MAX_EXTRA_CONFIG)`，`MAX_EXTRA_CONFIG = 20000`；②**只准 ASCII 可列印字元（0x20–0x7E）加換行與 tab，且不准反斜線**（連註解裡也不准；理由：Groovy／Java 會在讀程式之前處理 `\uXXXX`，註解可以因此被提早結束）；③新函式 `_check_extra_config` 的**封閉行語法**——不符合任何一種行＝整份拒絕，訊息點名第幾行與規則：
  - 空行；整行 `//` 註解（行尾不准再接註解）。
  - 單行賦值：`process.<key> = <值>`。
  - 區塊：`process {`、`withName: '<名>' {`、`withLabel: '<名>' {`、單獨一個 `}`；區塊內只有 `<key> = <值>` 行與區塊開關。`<名>` 只含 `A-Za-z0-9_:.*|-`，最長 200。巢狀最多兩層（`process` 內一層 `withName`／`withLabel`）。大括號必須成對。
  - `<key>` 只准 `cpus`、`memory`、`time`、`disk`、`maxRetries`、`errorStrategy`。
  - `<值>` 依 key：`cpus`、`maxRetries`＝至多 4 位的整數；`memory`、`disk`＝單引號字串 `'<數字> <單位>'`，單位 `B`／`KB`／`MB`／`GB`／`TB`（數字可含小數點，空白可有可無）；`time`＝單引號字串，由一或多段 `<整數><單位>` 以空白相接，單位 `ms`／`s`／`m`／`h`／`d`（例 `'4h'`、`'1h 30m'`）；`errorStrategy`＝`'retry'`／`'terminate'`／`'ignore'`／`'finish'`。
  - 因為語法是封閉的，下列都「不符合任何行」而被拒：`$`、反引號、`.execute`、`new`、閉包 `{ … ->`／`{ task`、條件式資源（`memory = { 4.GB * task.attempt }`）、`includeConfig`、`env`、`workDir`、`executor`、`tower`、`params`、`report`、`timeline`、`trace`、`dag`、`docker`、`singularity`、`apptainer`、`container`、`beforeScript`、`afterScript`、`ext`、`publishDir`、`queue`、`clusterOptions`、`maxErrors`。測試要逐一列出這些，確認真的被拒。
- 全部在 `render_resume` 裡做，所以平台端（b 片的 `prepare_resume`）與代理端重建（`run_resume`）用的是**同一份**規則。

### D. 內容包與雜湊
- `render_resume_bundle(…, overrides=None)`：有改動時 `files` 多上述新檔，`resume` 多一個鍵 `overrides`（正規化後的內容）；**沒改動時 `resume` 沒有 `overrides` 這個鍵**，`files` 只有 `head-N.sh`，所以今天的 bundle 與它的 sha256 完全不變。
- `RESUME_KEYS`（`:804`）原樣；新增 `RESUME_OPTIONAL = {"overrides"}`。`run_resume`（`:1152`）的欄位檢查（`:1160`）改成「`set(resume) - RESUME_OPTIONAL == RESUME_KEYS`」。`origin` 仍是第一次送出的 bundle 原封不動；`:1182` 的 `rebuilt != …` 比對不動。
- `run_resume` 重建（`:1186`）時把 `resume.get("overrides")` 餵給 `render_resume_bundle`，結果與送來的 bundle 整份比對（`:1193`）。因此「yes 之後改 `overrides`、`params-N.yaml`、`extra-N.config`、`head-N.sh`、拿掉 `overrides`、多放一個空的 `overrides`、多加不認得的鍵」任何一處，都被這個比對擋下；`overrides` 在 bundle 裡，所以也在 sha256 裡（平台端的 sha 比對在 b 片驗證）。
- 只有 `overrides` 的內容可以不同於 origin；origin 仍須等於「代理用自己的設定重新產生的第一次 bundle」。

### E. 站台資料夾檢查與寫入
- `_probe`（`:1095`）把「這次要新建的檔」從一個擴成一組（`head-N.sh`，有改動時再加 `params-N.yaml`、`extra-N.config`）。舊的 `head=exists|free` 行照舊只針對 `head-N.sh`；其餘新檔，每個已存在（或是捷徑）就多輸出一行 `exists=<檔名>`。`_check_folder`（`:1109`）看到任何 `exists=` 就拒絕並點名該檔，**不覆蓋**。
- `FILE_NAMES` 四個原檔的 sha 檢查（`:1132-1134`）**完全不動**：新檔加在旁邊，不是改原檔。
- 寫入（`:1206-1207`）：`tar -x` 一次寫入「這次的新檔＋`tower.token`」，什麼都不刪、不改原檔，然後一次 `sbatch`（`_submit`，`:1063`）。無改動時寫入的仍恰是 `head-N.sh`＋`tower.token`。
- 不需要 migration：本片不碰資料庫；舊的、尚未被回答或已排進佇列的續跑 bundle 沒有 `overrides` 鍵，行為與今天相同。

## 失敗先行測試
新檔 `platform/tests/test_resume_edit_params_station.py`（名字如下，每個先紅；括號是參數化的案例）。**不得用 `origin/v3`／`git diff <base>` 當比較對象**；「與今天相同」一律用測試裡寫死的黃金文字或既有測試的斷言。
- `test_overrides_change_the_head_script_and_add_files_only`：`files` 恰為 `head-N.sh`＋`params-N.yaml`（＋`extra-N.config`）；最後一行含 `-params-file params-N.yaml` 且 `-c nextflow.config -c extra-N.config` 依此順序；origin 的四檔文字逐位元組相同。
- `test_without_overrides_the_resume_is_byte_for_byte_today`：寫死的 `head-2.sh` 黃金文字相符；`files` 只有一個鍵；`resume` 沒有 `overrides`。
- `test_empty_overrides_are_no_overrides`（`None`、`{}`、`{"params":{}}`、`{"extra_config":""}`）：結果與不帶時相同。
- `test_params_overlay_replaces_keeps_and_adds_and_never_deletes`、`test_params_yaml_keeps_input_and_outdir_of_the_origin_folder`。
- `test_params_overrides_are_refused_like_a_launch`（`input`、`outdir`、巢狀、list、None、nan、inf、壞名稱）：`BundleError` 點名鍵；與 `_check_params` 逐案一致。`test_params_overrides_refuse_control_characters_and_overlong_text`（NUL、CR、ESC、雙向、超長）。
- `test_overrides_of_the_wrong_shape_are_refused`（未知鍵、`params` 不是字典、`extra_config` 不是字串）。
- `test_extra_config_accepts_the_resource_lines`（`process.memory = '8 GB'`、`process.cpus = 4`、三行寫法 `process {` ／ `withName: 'FASTQC' {` ／ `cpus = 4` ／ `}` ／ `}`（同一行寫法被拒，見裁決二）、`withLabel`、`time = '1h 30m'`、`errorStrategy = 'retry'`、註解與空行）。
- `test_extra_config_refuses_everything_else`（C 節末列的全部寫法；每個點名行號）、`test_extra_config_is_ascii_only_without_backslash_or_cr`、`test_extra_config_too_long_is_refused`。
- `test_extra_config_cannot_undo_the_platforms_overwrite_block`：`report.overwrite = false`、`timeline.overwrite = false` 被拒。
- `test_the_extra_file_has_the_header_comment_and_comes_after_nextflow_config`。
- `test_overrides_are_in_the_bundle_and_in_its_hash`：`resume.overrides` 正規化後存在；`origin` 與輸入的 origin 深度相等；改任一處 `bundle_sha256` 就變。
- `test_a_site_module_origin_takes_overrides`（本地模組啟動的 origin 也可）、`test_composed_and_google_batch_origins_are_still_refused_with_overrides`（`COMPOSED_NO_RESUME`／`GCB_NO_RESUME` 原字句）。
- 站台（沿用 `test_station_resume.py` 的 `site`、`fake` 夾具寫法）：`test_station_refuses_a_bundle_changed_after_the_yes`（改 `resume.overrides.params`、`files["params-N.yaml"]`、`files["extra-N.config"]`、`files["head-N.sh"]`、拿掉 `overrides`、空 `overrides`、多加不認得的鍵；連 sha 一起改也被重建比對擋下）、`test_station_writes_the_new_files_once_and_leaves_the_originals_alone`（tar 恰含新檔＋`tower.token`、無刪除、一次 `sbatch`）、`test_station_refuses_when_params_n_or_extra_n_exists_or_is_a_link`（沒有寫入）、`test_original_files_sha_check_still_applies_with_overrides`、`test_station_without_overrides_writes_exactly_head_and_token`、`test_a_resume_confirmation_with_overrides_is_spent_once`、`test_station_origin_changed_consistently_is_refused`。
- `test_no_second_copy_of_run_state`：`bash tests/no_second_run_state_test.sh` 綠。

預估：約 25 個具名測試、約 50 個案例（參數化案例計入）；上限 60。

**必須仍綠、不准改**：`test_resume_render.py`（TC-012／013 與 :86、:101 一帶）、`test_station_resume.py`（TC-019–021／033／036／038／039）、`test_launch_bundle.py:718-740, :929-932`、`test_resume_platform.py`（TC-006／007／011）、`test_resume_scope.py`（TC-157–160）、全套 `platform/tests`、`bash tests/no_second_run_state_test.sh`、CI。

## 完成標準（done when）
- 一份帶 `overrides={"params": {"min_reads": 100}, "extra_config": "process.memory = '16 GB'"}` 的續跑內容包，經假站台：寫入 `head-N.sh`、`params-N.yaml`、`extra-N.config`、`tower.token`，一次 `sbatch`，原四檔不變。
- 不帶改動的續跑，bundle 與 sha256 與今天完全相同。
- 上列測試與全套 `platform/tests`、`bash tests/no_second_run_state_test.sh`、CI 綠。
- `git diff --stat` 只含「範圍：檔案」列的 3 個路徑（證據貼 ledger，通例：閱卷看 diff）。
- ledger 記：「未在國網實測改參數後沿用快取」（手動檢查在 d 片的 TESTING.md）。
- PR 說明寫明：白名單為什麼存在與它比舊版多的限制（裁決 3）、不需要 migration、本片之後 platform 端仍不會送出改動。

## 環境事實
- `platform/abf_station/launch.py`（@ `b5dcb09`）：`MAX_VALUE`（:44）；`FILE_NAMES`（:47）；`OVERWRITE_BLOCK`（:52）；`RUN_NAME`（:33）、`SESSION_ID`（:34）、`PARAM_NAME`（:38）；`_check_text`（:83）；`_check_params`（:325）；`_params_yaml`（:403，合併 `input`／`outdir`）；`_head_script`（:416，組合圖分支 :461-463，其餘最後一行 :465-466）；`render_bundle`（:470，`params` 存的是 `_check_params` 之後的使用者參數，不含 `input`／`outdir`）；`render_resume`（:739，組合圖拒絕 :754-755）；`render_resume_bundle`（:771，`resume` 的鍵 :781）；`RESUME_KEYS`（:804）；`_tar`（:867）；`_prechecks`（:1036）；`_submit`（:1063）；`_probe`（:1095）；`_check_folder`（:1109，四檔 sha :1132-1134）；`run_resume`（:1152；GCB 拒絕 :1158；欄位檢查 :1160；組合圖 :1163；重建 :1177；比對 :1182；expected :1186-1194；`script` :1195；probe :1200；寫入 :1206-1207）。
- `platform/abf_platform/jobs.py:496-531`（`_lineage`）只讀 `resume.of_run`、`resume.attempt`，不檢查 `resume` 的鍵集合，所以多一個 `overrides` 鍵不需要改它。
- 測試夾具：`platform/tests/resume_harness.py`（`make_folder`:18、`resume_bundle`:36）；`FakeSite` 是真的跑 shell，所以 `_probe` 的輸出格式可以自由加行。
- `--resume` 的語意（Nextflow 行為）：沒被改動影響的 task 沿用快取；用到被改動的參數或資源的 task 重跑。尚未在國網實測，只用假站台檢查。

## 不做
- 不做 platform 端（`prepare_resume`、動作、CLI、MCP、畫面）——b 片；不改任何文件——c、d 片。
- 不換 CE、不換樣本表、不換管線或版本、不改 run 名稱；不支援刪除參數；不支援 `queue`、`clusterOptions`、`executor`、`workDir`、`env`、`includeConfig`、容器設定、需要閉包的資源寫法；不支援完整的 Nextflow 設定檔——需要再開票。
- 對組合圖與 gcb 送出的 run，續跑一律維持拒絕。
- 不改 relaunch。不加 job 種類、不改 `jobs.py`／`store.py`。

## 裁決（已寫進上文；與上文衝突時以上文為準，兩者不應衝突）
1. `origin` 原封不動，改動另放 `resume.overrides`（D 節）：009e 的安全性來自「origin＝第一次送出的 bundle，yes 之後無法被換」，且站台用它的四個原檔 sha 驗資料夾。
2. 新檔加在旁邊，不改原檔（B、E 節）：資料夾會累積各次嘗試的檔，這正是紀錄。
3. `extra_config` 走封閉白名單，不是自由文字（C 節）。這是 developer-agent 對範圍報告的補強，不是維護者原話：`-c extra-N.config` 排在平台的 `nextflow.config` 後面，自由文字能覆蓋 `OVERWRITE_BLOCK`、`workDir`、`tower`、`executor`，也能執行任意 Groovy。**本次拆分另加兩條更保守的限制**（只准 ASCII、不准反斜線；行語法取代舊版的「語法限制＋禁字清單」兩套說法），已寫進 C 節。若維護者認為過嚴，唯一的放寬方式是在票內明確加項目，不是移除檢查。
4. 無改動路徑逐位元組不變（A、B、D 節）：既有 bundle 的 sha256、已確認但未執行的舊請求、既有釘住的測試都不受影響。
5. 參數是「蓋上去」，不是「整份重填」，不支援刪除（A 節），與 Seqera 的 Resume 一致。
6. 組合圖與 gcb 的續跑維持拒絕（本片只確認原拒絕在有改動時仍有效）。
7. 決定權：Tier C，維護者 2026-10-24 11:20 核可；合併由 developer-agent 在 verifier PASS 與 CI 綠之後執行。
8. 待維護者確認：無。

## 裁決（2026-10-24 17:10 developer-agent，以本段為準）
1. 前置已全部合併，開工以最新 v3 為準；若合約超過 60 條，照計畫在「render 與驗證」／「站台執行」切開。

## 裁決二（2026-10-24 17:30 developer-agent，回應出題退回；以本段為準，正文已同步改寫）
1. 同一行寫完整個區塊（`process { withName: 'X' { cpus = 4 } }`）拒絕，訊息要提示「請分行寫，每行一個 `{`、一個設定或一個 `}`」。失敗先行測試的「要接受」範例已改成分行寫法；另加一條「同一行寫法被拒且訊息含分行提示」。
2. 每行允許行首縮排（空格或 tab）與行尾空白，比對前去掉；寫出的檔保留使用者原樣。
3. 結尾換行正規化為剛好一個（原本有就不再補，有多個空行尾就收成一個）。
4. 正規化後的 `resume.overrides` 省略空的項（空字串、空清單都不放鍵），寫進 ledger。
5. TC-053／TC-054 以 ledger 與 diff 閱卷（README 通例）。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
