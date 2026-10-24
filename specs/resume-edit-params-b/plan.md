---
id: resume-edit-params-b
title: 續跑可以帶改過的參數與資源設定：build／動作層／CLI／MCP 接上 a 片的內容包，確認畫面列出「改了什麼」（不做網頁）
tier: C
kinds: backend
lane: L12-resume
base: v3
after: resume-edit-params-a
source: resume-edit-params 的第 2 片（共 4 片）；維護者 10-23 常設方向「跟Seqera platform一樣的模式，不要自己定義」；維護者 2026-10-24 11:20 核可此 C 級改動；a 片（站台與內容包）
---

# resume-edit-params-b

> 本檔由 developer-agent 依 `resume-edit-params.md`（舊版，不再派）重新切分，行號重對 `origin/v3` @ `b5dcb09`。**只處理本任務**。
> ⚠️ **前置：a 片（`resume-edit-params-a`）已合進 `v3`**，才從最新 `origin/v3` 開分支；沒合就 BLOCKED，不要自己拿 a 片的程式。a 沒合時 `render_resume_bundle` 沒有 `overrides` 參數。
> 本片只動 `platform/abf_launch/cli.py`，**不是** `platform/abf_platform/cli.py`（cloud-cost PR #188 會改後者）；不碰 `web.py`（網頁照舊以 `run_name` 呼叫 `request_resume`，所以新參數一律可選）、`store.py`、`receiver.py`、`datasets.py`、`cloud_*.py`。**不必通知前端 session。**

## 目標
一個失敗（或被取消）的 run，可以透過 CLI 與 MCP 的 `resume` 帶「要改的參數」與「資源設定」續跑（例：把某個 process 的記憶體加大再接著跑）。人看到的是「舊值 → 新值」的差異、資源設定全文與完整的最後一行指令，說 yes 才會送；沒受影響的已完成 task 仍沿用快取。樣本表、管線、版本、運算環境仍不能在續跑裡換。沒帶任何改動時，一切與今天相同。

## 維護者原話（verifier 出題用）
- 「續跑可改參數與資源（照 Seqera）」——developer-agent 提案 2026-10-24 02:00；維護者在 2026-10-24 12:00 期限前沒有回覆 → 依預設照此範圍進行。
- 維護者 10-23 常設方向：「跟Seqera platform一樣的模式，不要自己定義」→ 名詞與行為照 Seqera 的 Resume（改參數、加設定檔，其餘不動）；不自創新概念。
- 維護者 10-24：「所有 PR 自己合併」→ Tier C（改方向）仍由 developer-agent 在 verifier PASS 與 CI 綠之後合併。
- 009e 原設計（被本任務翻掉的部分）：「續跑只收 run 名稱」；ADR 0009：「changing the samples or the parameters starts a new analysis」→ 現在變成「改樣本表／管線／版本／環境＝新分析；改一部分參數與資源＝仍是同一個分析的下一次嘗試」。
- 不變的底線（009e／憲章）：任何寫入都要人說 yes；續跑只在同一個專屬資料夾；原本四個檔（`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`）不被改動，站台用它們的 sha 檢查資料夾還是不是第一次送出的那個。
- 補記（2026-10-24 11:20）：維護者核可「這是 C 級改動」，可依此拆片進行。
- 本片負責的句子：「確認管道不變：人看到的是『舊值 → 新值』的差異與完整的最後一行指令，說 yes 才會送」「只做 CLI 與 MCP，不做網頁」「沒有改動時行為不變」。

## 範圍：檔案（最終版，8 個；只准改這些）
- `platform/abf_launch/build.py`（改：`prepare_resume` 收 `params`、`extra_config`；新增 `EDITED_SENTENCE`、`read_edit_args`；改 `resume_screen`；`_attempt_lines` 與 `relaunch_screen` 不動）
- `platform/abf_launch/cli.py`（改：`resume` 子命令加 `--param`、`--params-file`、`--config-file`；`_attempt`；說明文字；`relaunch` 不動）
- `platform/abf_platform/actions/__init__.py`（改：`request_resume` 與 `_request_attempt` 加兩個可選參數；docstring。`request_relaunch` 簽名不動）
- `platform/abf_platform/mcp_server.py`（改：`resume` 工具加可選的 `params`、`extra_config`；檔頭說明與工具描述；`relaunch` 不動）
- `platform/abf_platform/actions/chat_tools.py`（改：聊天提示裡 `resume` 一行；`REQUEST_TOOLS` 不變）
- `platform/tests/test_resume_edit_params_platform.py`（新）
- `platform/tests/test_resume_entrypoints.py`（只准動「允許更新的既有斷言」列的四處）
- `specs/resume-edit-params-b/ledger.md`（新）

**不准動**：`web.py`、`confirm.py`、`jobs.py`、`store.py`、`receiver.py`、`cli.py`（`abf_platform/` 底下那支）、`actions/datasets.py`、`cloud_store.py`、`cloud_cost.py`、`abf_station/*`（a 片的成果）、`guidance.py`（c 片）、`docs/`、`skills/`、`scripts/launch_recheck.sh`、`hooks/*`、`flaky-tests` 計畫列的測試檔。

## 作法
行號皆 `origin/v3` @ `b5dcb09`。

### A. `prepare_resume`（`build.py:404`）
簽名：`prepare_resume(state, run, *, index_path, owner=None, area=None, params=None, extra_config=None)`。前半（重建 origin 並比對，`:404-425`）原樣。之後：
1. `params` 不是字典、`extra_config` 不是字串＝`Refusal`（白話，中英）。`params` 內與 origin 同名**且型別與值都相同**（`type(a) is type(b) and a == b`）的鍵先丟掉；空字串的 `extra_config` 視為沒給。丟完兩項都空＝**等同沒有改動**：走今天的路徑，內容包與畫面逐字相同。
2. 有改動時呼叫 `bundle_mod.render_resume_bundle(…, overrides={"params": …, "extra_config": …})`（a 片提供）。`BundleError`（含資源設定的語法拒絕）轉成 `Refusal(str(e))`，訊息本來就點名欄位與行號。`bundle["resume"]["origin"]` 仍是 `copy.deepcopy(origin)`。
3. **路徑參數的 116b 限制也套在改動上**：`area` 不是 `None` 時（HTTP 呼叫者），另呼叫一次 `prepare_launch`，`params` 用「origin 參數蓋上改動」的合併結果、其餘同現有那次（`check_name=False`、`samplesheet_rows=origin["samplesheet"]`），只取它的 `upload_paths`（`_confine` 已含 `params` 裡看起來像路徑的值，`build.py:230`）放進 `bundle["upload_paths"]`，取代只由 origin 算出的那份。這樣一個 HTTP 使用者不能靠續跑把參數指到別人的上傳資料夾；站台端 `_check_upload_paths`（`launch.py:957`）在 job 時再驗一次。`area` 是 `None`（終端機、stdio）時行為同今天。
4. 組合圖（`build.py:377`）與 Google Batch（`build.py:344`）的 run，在 `_predecessor` 就已被拒，有無改動都一樣，不改。

### B. 確認畫面（`resume_screen`，`build.py:601`）
- 先修一個脆弱處：找腳本改成 `script = "head-%d.sh" % r["attempt"]`，不再用 `next(iter(bundle["files"]))`（現在 `files` 會有多個檔）。
- 沒有 `resume.overrides`＝逐字同今天（固定句 `這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變` 一字不改；`test_resume_entrypoints.py:84,193`、`test_resume_platform.py:137` 在釘它）。
- 有 `resume.overrides` 時：固定句換成模組常數 `EDITED_SENTENCE = "這是續跑：同一個資料夾；下面的參數與設定有改，用到它們的 task 會重新跑，其餘已完成的 task 沿用"`；其餘 `_attempt_lines` 的欄位與「指令（head-N.sh 的最後一行）」不變——那一行現在含 `params-N.yaml` 與 `-c extra-N.config`，人看到的就是真正會跑的東西。在 `_attempt_lines` 之後依序追加：①每個被改的參數一行 `參數 <名>：<舊值> → <新值>`，新增的寫 `參數 <名>：（新增）→ <新值>`（值一律過 `terminal.esc`）；②有 `extra_config` 時 `terminal.block("extra-N.config", 完整文字)`；③原有的「接續的 session」與 `head-N.sh` 全文區塊。
- `relaunch_screen`、`_attempt_lines` 不動。

### C. 動作層（`actions/__init__.py`）
- `request_resume(platform_path, *, run_name, params=None, extra_config=None, caller=None, person=None, clock=…, remote=False, index_path=None)`；`_request_attempt`（`:575`）加同樣兩個參數，**只有 resume 用**；`request_relaunch` 簽名不變。不新增任何名稱含 `resume`／`relaunch` 的函式（任何檔、任何可見度；`test_keep_submissions.py:782` 的 TC-084 掃整個 `platform/` 的函式名，`test_actions_layer.py:666` 的 `dir(a)` 檢查也原樣綠；所以 CLI 輔助函式叫 `read_edit_args`，不叫 `read_resume_…`）。
- **呼叫端給了任一非空改動（`params` 非空字典或 `extra_config` 非空字串）時，不呼叫 `confirm.find_attempt`**，直接 `prepare` 建請求，靠 `create_pending` 的 hash 去重（`confirm.py:70`：相同內容、相同呼叫者的待回答請求只會有一份）。理由：`find_attempt`（`confirm.py:191`）只用「parent_run＋種類」找已確認的嘗試，會把「改過參數的續跑」誤當成「剛才那個一般續跑」而回傳舊工作編號，悄悄丟掉使用者的改動。沒給改動時照今天先呼叫 `find_attempt`。
- 已知後果（要寫進測試並照實描述，不要在這片偷偷修）：一次帶改動的續跑被確認排進佇列之後，用同樣內容再呼叫一次，會被既有的「只能對最新的一次」規則（`build.py:_predecessor` 的 `newer` 檢查）拒絕，訊息會指出已存在的那一次（含 run 名稱），不會直接回工作編號；要拿工作編號請用 `get_run` 查那個名稱。同一 predecessor 的第二份不同內容也被同一條規則擋下（`test_resume_lineage.py` 的 TC-121／TC-128 不改）。

### D. MCP 與聊天（`mcp_server.py`、`chat_tools.py`）
- `resume` 工具簽名：`resume_tool(ctx, run_name: str, params: dict | None = None, extra_config: str | None = None)`；`relaunch` 仍只有 `run_name`。其他額外參數（`revision`、`samplesheet`、`ce_name`、`session_id`…）仍被丟棄或拒絕。
- 描述改成：「可選擇性帶 `params`（只寫要改的鍵，蓋在第一次送出的參數上）與 `extra_config`（資源設定，例如 `process.memory = '16 GB'`）；管線、版本、樣本、環境仍是第一次送出的，要換就是新的 launch」，並**保留**「不會自己送出」「The person says yes…」「It does not start anything until the person says yes.」整段與 `readOnlyHint`／`destructiveHint` 為 False。檔頭說明（`:16-17`）同步改。
- `chat_tools.py:30` 那一行改成含「可選 params、extra_config」；`REQUEST_TOOLS`（:16）不變。

### E. CLI（`abf_launch/cli.py`）
- `abf-platform resume RUN [--param name=value]… [--params-file FILE] [--config-file FILE] [--user U]`；`relaunch` 子命令一個旗標都不加。
- `build.py` 新增 `read_edit_args(params_file, param_items, config_file)` → `(params 或 None, extra_config 或 None)`：`--params-file` 用 `read_params_file`（`build.py:67`）、`--param` 用 `infer`（`build.py:57`）——與 `prepare_launch`（`:135`，不改它）同一套；`--config-file` 讀 UTF-8 文字檔，讀不到、不是 UTF-8、超過 20000 字元＝`Refusal`。`_attempt`（`cli.py:106`）對 resume 把兩者傳進 `prepare`。
- 禁止的旗標仍禁止：`--yes`、`-y`、`--force`、`--assume-yes`、`--no-confirm`、`--y`、`--revision`、`--samplesheet`、`--ce`、`--pipeline`、`--run-name`、`--session`；`--params`（單數 s，不是 `--params-file`）也仍被拒（子命令是 `allow_abbrev=False`）。

### F. 不需要 migration
沒有新表、新欄位；`confirmations.bundle_json` 本來就存整份 bundle。舊的、尚未回答的續跑請求沒有 `overrides`，行為同今天。PR 說明要寫這一點。

## 失敗先行測試
新檔 `platform/tests/test_resume_edit_params_platform.py`，沿用 `test_resume_platform.py`、`test_resume_entrypoints.py` 的 `rig` 夾具寫法（夾具在測試檔裡就照做一份，不 import 測試檔）。每個先紅。
- build／畫面：`test_prepare_resume_with_params_builds_overrides_and_keeps_the_origin`；`test_unchanged_values_are_dropped_and_nothing_left_is_a_plain_resume`（內容包逐字同無改動）；`test_params_must_be_a_mapping_and_extra_config_text`；`test_a_bad_param_or_extra_config_is_a_refusal_that_names_the_field`（`input`、`outdir`、`includeConfig`、`$`）；`test_screen_shows_the_param_diff_the_extra_config_and_the_real_last_line`（舊→新、`（新增）`、`extra-N.config` 全文、最後一行含新檔名）；`test_screen_swaps_the_fixed_sentence_only_when_overrides_exist`（無改動＝舊句且不含「→」；有改動＝新句且不含「樣本和參數不變」）；`test_screen_escapes_control_characters_in_changed_values`；`test_the_resume_screen_finds_its_script_by_attempt_number`（把 `files` 順序倒過來仍正確）。
- 116b 與擁有者：`test_a_path_param_outside_the_callers_uploads_is_refused_over_http`、`test_a_path_param_inside_them_is_recorded_in_upload_paths`、`test_without_an_area_nothing_about_upload_paths_changes`；`test_an_edited_resume_is_still_owner_only_and_the_words_are_uniform`（別人的與不存在的 run 同一句話，仿 TC-100–103）；`test_composed_and_google_batch_runs_are_still_refused_with_edits`。
- 動作層：`test_edits_skip_find_attempt_and_a_plain_resume_still_uses_it`；`test_the_same_edited_resume_twice_is_one_pending_request`；`test_after_the_yes_the_same_edited_call_is_refused_and_names_the_existing_attempt`（照實釘住 C 節的已知後果）；`test_a_second_different_edit_for_the_same_predecessor_is_refused`；`test_request_relaunch_takes_no_edits`；`test_the_yes_for_an_edited_resume_is_for_exactly_that_content`（yes 之後改 `resume.overrides` 的任一處，平台端 sha 比對擋下，仿 `test_resume_lineage.py` TC-089–093）。
- MCP／聊天：`test_mcp_resume_takes_run_name_and_two_optional_fields_and_relaunch_still_only_one`（兩者都沒有能說 yes 的欄位）；`test_mcp_resume_with_extra_fields_still_drops_revision_samplesheet_ce_and_session`；`test_mcp_resume_with_edits_queues_a_job_only_after_the_form_is_accepted`；`test_the_chat_prompt_says_resume_can_carry_params_and_extra_config`。
- CLI：`test_cli_resume_takes_param_params_file_and_config_file_and_relaunch_does_not`；`test_cli_param_values_are_read_like_launch`（`n=3`→整數、`f=true`→布林）；`test_cli_config_file_that_is_missing_not_utf8_or_too_long_is_refused`；`test_cli_edited_resume_shows_the_diff_before_the_question`（仿 `test_resume_entrypoints.py:195` 的 pty 寫法）。

預估：約 24 個具名測試、約 40 個案例；上限 60。

### 允許更新的既有斷言
只准這四處（翻掉「續跑只收名稱」），其餘不准動：
- `platform/tests/test_resume_entrypoints.py:50` `test_tc133_tc134_tc135_…`：`resume` 允許 `props == {"run_name", "params", "extra_config"}`、`required == ["run_name"]`；`relaunch` 仍 `{"run_name"}`。`YES_FIELDS` 檢查不動。
- `:71` `test_the_descriptions_say_what_resume_and_relaunch_are_…`：`resume` 的描述改檢查含 `params`、`extra_config`；`relaunch` 不變。
- `:128` `test_tc148_…`：`params` 在 `resume` 呼叫裡不再被丟棄，改斷言它進了 `b["resume"]["overrides"]["params"]`；`revision`、`samplesheet`、`ce_name`、`session_id` 仍被丟棄／拒絕，並保證 `b["resume"]["origin"]["revision"] == "2.18.0"`。
- `:169` `test_tc140_tc141_tc147_…`：禁止旗標清單對 `resume` 移除 `["--param", "a=b"]`（`--params-file` 另測）；**對 `relaunch` 清單不變**；`--params`、`--revision`、`--samplesheet`、`--ce`、`--pipeline`、`--run-name`、`--session`、各 yes 旗標對兩者都仍被拒。

**必須仍綠、不准改（無改動路徑）**：`test_resume_platform.py`（TC-006／007／011 :71、TC-014–018 :129、TC-085／086、TC-088、TC-117）、`test_resume_render.py`、`test_station_resume.py`、`test_resume_lineage.py`（TC-089–097）、`test_resume_scope.py`（TC-146 :30、TC-157–160）、`test_actions_layer.py`（:28 `WRITE_NAMES`、:666）、`test_mcp.py:53`、`test_launch_platform.py:722`、`test_guidance.py`（本片不動 `guidance.py`）、全套 `platform/tests`、`bash tests/no_second_run_state_test.sh`、CI。

## 完成標準（done when）
- 對一個失敗的 run：`resume` 帶 `params={"min_reads": 100}` 與 `extra_config="process.memory = '16 GB'"` → 畫面顯示舊值 → 新值與完整設定與真正會跑的最後一行；yes 之後 job 排進佇列，內容包是 a 片的形狀。
- 不帶改動的 `resume`（CLI、MCP、網頁按鈕）行為與 bundle hash 與今天完全相同。
- 上列測試與全套 `platform/tests` 綠、`bash tests/no_second_run_state_test.sh` 綠、CI 綠。
- `git diff --stat` 只含「範圍：檔案」列的路徑；`web.py`、`confirm.py`、`store.py`、`jobs.py`、`abf_station/*` 沒有變動（證據貼 ledger）。
- PR 說明寫明：reverse 009e 的哪一句、不需要 migration 的理由、白名單來源（見 a 片裁決 3）、web 與 CE 切換為何不做、已知後果（C 節）。

## 環境事實
- `platform/abf_launch/build.py`（@ `b5dcb09`）：`infer`（:57）；`read_params_file`（:67）；`prepare_launch`（:135，合併參數 :168-174，`area` 時 `_confine` :230 之後呼叫）；`params_area_refusal`（:199）；`_param_path`（:210）；`WORDS`（:315）、`TOO_OLD`、`CHANGED`；`_predecessor`（:327；Google Batch 拒絕 :344；組合圖拒絕 :377）；`prepare_resume`（:404-433）；`_attempt_lines`（:589）；`resume_screen`（:601）。
- `platform/abf_platform/actions/__init__.py`：`_ask`（:383）；`caller_area`（:427）；`_request_attempt`（:575，`find_attempt` :578）；`request_resume`（:591）；`request_relaunch`（:597）。
- `platform/abf_platform/confirm.py`：`create_pending`（:70，以 sha256＋種類＋呼叫者去重）；`find_attempt`（:191）；`facts`（:264）——**不改**；`web.py:291-299` 只讀它已知的幾個鍵，網頁完全不必動。
- `platform/abf_platform/jobs.py:496-531`（`_lineage`）：嘗試編號必須是最高＋1、續跑必須同資料夾；不看 `resume` 的其他鍵。
- `platform/abf_platform/mcp_server.py`：`_WRITES`（:27）；`resume` 工具 :138-147；`relaunch` :149-158；檔頭說明 :16-17。`chat_tools.py`：`REQUEST_TOOLS`（:16）、說明行 :30-31。
- `platform/abf_launch/cli.py`：`QUESTION_RESUME`（:29）；`_attempt`（:106，`prepare` 呼叫 :116）；`cmd_resume`（:136）；`launch` 的 `--param`／`--params-file`（:420-421）；`resume`／`relaunch` 子命令註冊（:427-436）。`abf_platform/cli.py:611` 只是呼叫 `launch_cli.add_commands`。
- 舊計畫（`resume-edit-params.md`）的這些行號已過時：`request_resume` 在 :591（舊 :560）、`resume_screen` 在 :601（舊 :489）、`prepare_resume` 在 :404（舊 :380）、`mcp_server` resume 在 :138-147 不變；舊計畫要從 `:169` 的禁用旗標清單移除 `--params` 是錯的，`--params` 要繼續被拒。

## 不做
- 不做網頁（`web.py` 不動；按鈕仍是無改動的續跑）、不加 MCP 新工具、不加 job 種類、不改 `jobs.py`／`store.py`。
- `confirm.facts` 不加 `edited` 鍵：網頁不讀它，加了是死碼；網頁要顯示時由前端 session 另開票。
- 不換 CE、不換樣本表、不換管線或版本、不改 run 名稱；不支援刪除參數；對組合圖與 gcb 送出的 run，續跑一律維持拒絕。
- 不加「最近用過的參數」之類的記憶；不自動建議參數；不在續跑裡自動重試；不改 relaunch。
- 不改字句與文件：`guidance.py`、技能、ADR、PARITY 在 c 片；`PLATFORM.md`、`TESTING.md` 在 d 片。

## 裁決（已寫進上文；與上文衝突時以上文為準，兩者不應衝突）
1. 呼叫端給了非空改動時不走 `find_attempt`（C 節）；重複送出同一份內容由 `create_pending` 去重，第二份不同內容由既有嘗試編號規則擋下。已知後果照實釘在測試裡。
2. 無改動路徑逐位元組不變（A 節第 1 點、B 節）。
3. 參數是「蓋上去」不是「整份重填」，不支援刪除（A 節）。與 Seqera 的 Resume 一致：以新值覆蓋。
4. 組合圖與 gcb 的續跑維持拒絕（A 節第 4 點）；兩者 bundle 形狀不同，不去猜。
5. 白名單與資源設定的語法限制在 a 片（裁決 3）；本片只負責把拒絕訊息白話地呈現。
6. **本次拆分新增（非維護者原話）**：①改動中的路徑參數套 116b 限制（A 節第 3 點）——舊計畫漏了，不補會讓 HTTP 使用者能經續跑指向別人的資料夾；②`resume_screen` 改用 attempt 找腳本；③`confirm.facts` 不加 `edited`。
7. 決定權：Tier C，維護者 2026-10-24 11:20 核可；合併由 developer-agent 在 verifier PASS 與 CI 綠之後執行。
8. 待維護者確認：無。

## 裁決（2026-10-24 17:10 developer-agent，以本段為準）
1. 開放問題 1：要。`find_attempt` 比對 `resume.overrides`，同名同改動再呼叫一次回傳同一個 job 號碼（冪等）；`platform/abf_platform/confirm.py` 加入範圍（共 9 檔）。原裁決 4「改過就跳過 find_attempt」作廢。
2. 不准動的是 `platform/abf_platform/cli.py`；`platform/abf_launch/cli.py` 可動。
3. 開放問題 5：確認頁加一句「這次的改動是疊在第一次送出的參數上，前一次續跑的改動不會帶過來」。
4. cloud-cleanup 排在本切片之後（同動 build.py、actions/__init__.py）。

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
