# 測試案例：續跑可改參數與資源（b：平台、確認頁、MCP、CLI）（resume-edit-params-b）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) from the plan only: there is no spec.md for this task.
The maintainer's words are quoted in plan.md under 「維護者原話」 and in the 「完成標準」 example; every row below comes from a line of
plan.md (目標, A-F 節, 失敗先行測試, 允許更新的既有斷言, 完成標準, 不做, 裁決, 「2026-10-24 17:10 裁決」, 專長守則（backend））.
Where the top of the plan and the 17:10 ruling disagree, the plan says the 17:10 ruling governs; these rows follow it.
Nothing was added that the plan does not state.
-->

**規格**：`specs/resume-edit-params-b/plan.md`（本件沒有 spec.md，計畫即依據）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、被改動、不合規則、別人想碰時，系統怎麼反應（拒絕、點名、停下，且沒有寫入）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白拒絕而不是悄悄接受。

名詞：

- 「續跑」＝讓 Nextflow 在同一個專屬資料夾接著上次跑，沒被改動影響的已完成 task 沿用快取。
- 「改動」＝續跑時帶的 `params`（只寫要改或要加的參數，蓋在第一次送出的參數上）與 `extra_config`（資源設定文字，例如 `process.memory = '16 GB'`）。存進內容包後叫 `resume.overrides`。
- 「無改動的續跑」＝只給 run 名稱、沒有任何改動（或改動被丟光），也就是今天的續跑。
- 「確認畫面」＝人說 yes 之前看到的全文（終端機畫面、MCP 的表單、網頁確認頁看到的是同一份文字）。
- N＝這次是第幾次嘗試（`attempt`，2 以上）；新檔名依 N：`head-N.sh`、`params-N.yaml`、`extra-N.config`。這些檔由 a 片（已合進 `v3`）產生。
- 「yes」＝本人在確認畫面按送出；「yes 之後被改」＝內容包在確認之後被換成別的內容。
- 「新測試檔」＝`platform/tests/test_resume_edit_params_platform.py`；每個測試在註解裡寫出它對應的 TC 編號。
- 「手動（閱卷）」＝閱卷者讀 diff、`git diff --stat` 與 `specs/resume-edit-params-b/ledger.md` 逐句對照預期結果（本片不改 `docs/`，所以沒有 `docs/TESTING.md` 的新步驟）。
- 「黃金文字／黃金雜湊」＝在改動程式之前、由今天的行為產生並寫死在測試裡的文字或 sha256；不得改動後再重新產生貼上。
- 「逐案」＝一列裡列出的每一個例子都要各自有斷言，不得以抽樣代替。
- 起始資料（測試自訂）：第一次送出的參數有 `min_reads = 50`、`primer = "A"`；失敗的 run 叫 `x`；續跑是第 2 次嘗試。

## User Story 1 — 帶改動的續跑：確認畫面列出「改了什麼」，yes 之後排進佇列（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 完成標準第 1 條；B 節①；`test_screen_shows_the_param_diff_the_extra_config_and_the_real_last_line` | 功能 | 起始資料；run `x` 失敗 | 續跑帶 `params={"min_reads": 100}`，取確認畫面全文 | 畫面有一行 `參數 min_reads：50 → 100`（舊值在前、新值在後）；沒被改的 `primer` 不出現在「參數」行 | 自動：新測試檔 |
| TC-002 | B 節①（新增）；`test_screen_shows_the_param_diff_…` | 功能 | 起始資料；原本沒有 `new_flag` 這個參數 | 續跑帶 `params={"new_flag": "on"}`，取畫面 | 有一行 `參數 new_flag：（新增）→ on` | 自動：新測試檔 |
| TC-003 | 完成標準第 1 條；B 節②；`test_screen_shows_the_param_diff_…` | 功能 | 起始資料 | 續跑帶 `extra_config="process.memory = '16 GB'"`，取畫面 | 畫面有一個標題為 `extra-2.config` 的區塊，內容是完整的 `process.memory = '16 GB'`（全文，沒有省略） | 自動：新測試檔 |
| TC-004 | 完成標準第 1 條；B 節（最後一行）；`test_screen_shows_the_param_diff_…` | 功能 | 同 TC-001 加 TC-003 的改動同時帶上 | 取畫面，找「指令（head-N.sh 的最後一行）」那一行；再取內容包 `head-2.sh` 的最後一行 | 畫面上那一行含 `params-2.yaml` 與 `-c extra-2.config`，且和內容包 `head-2.sh` 實際最後一行完全相同（人看到的就是真正會跑的） | 自動：新測試檔 |
| TC-005 | 完成標準第 1 條；目標；`test_prepare_resume_with_params_builds_overrides_and_keeps_the_origin`、`test_mcp_resume_with_edits_queues_a_job_only_after_the_form_is_accepted` | 功能 | 起始資料；帶 `params={"min_reads": 100}` 與 `extra_config="process.memory = '16 GB'"` | 人在確認表單說 yes | 一個 job 排進佇列（只有一個）；內容包的 `files` 鍵依序恰為 `head-2.sh`、`params-2.yaml`、`extra-2.config`；`resume.overrides` 恰為 `{"params": {"min_reads": 100}, "extra_config": "process.memory = '16 GB'"}`（a 片的形狀） | 自動：新測試檔 |
| TC-006 | B 節②（有 `extra_config` 時才加區塊）；A 節；`test_screen_shows_the_param_diff_…` | 功能 | 起始資料 | 逐案：(a) 只帶 `params`；(b) 只帶 `extra_config` | (a) 畫面沒有 `extra-2.config` 區塊，內容包 `files` 沒有 `extra-2.config`；(b) 畫面沒有任何以 `參數 ` 開頭的行 | 自動：新測試檔 |
| TC-007 | B 節（追加順序）；`test_screen_shows_the_param_diff_…` | 功能 | 同 TC-004（兩種改動都帶） | 取畫面全文，依出現位置排序 | 順序為：原有的欄位與「指令」行 → 每個被改參數的 `參數 …` 行 → `extra-2.config` 區塊 → 「接續的 session」→ `head-2.sh` 全文區塊 | 自動：新測試檔 |
| TC-008 | B 節（固定句換成 `EDITED_SENTENCE`）；裁決（17:10）3；`test_screen_swaps_the_fixed_sentence_only_when_overrides_exist` | 功能 | 起始資料；帶任一非空改動 | 取畫面 | 含 `這是續跑：同一個資料夾；下面的參數與設定有改，用到它們的 task 會重新跑，其餘已完成的 task 沿用`，不含 `樣本和參數不變`；另含 `這次的改動是疊在第一次送出的參數上，前一次續跑的改動不會帶過來` | 自動：新測試檔 |
| TC-009 | B 節（值一律過 `terminal.esc`）；`test_screen_escapes_control_characters_in_changed_values` | 功能 | 起始資料；新值含 ESC（`\x1b`）、換行、CR 等控制字元（且該值本身合法到能走到畫面，例如單獨測畫面函式） | 取畫面 | 畫面全文沒有原始的 ESC 字元，且每個改動仍只占一行 `參數 …`（換行被轉成可見的跳脫寫法） | 自動：新測試檔 |
| TC-010 | B 節（先修脆弱處）；`test_the_resume_screen_finds_its_script_by_attempt_number` | 功能 | 一份有 `head-2.sh`、`params-2.yaml`、`extra-2.config` 的內容包；把 `files` 的鍵順序倒過來 | 取畫面 | 畫面最後的全文區塊仍是 `head-2.sh`（依 attempt 找，不是取第一個檔） | 自動：新測試檔 |
| TC-011 | A 節②（`origin` 仍是 deepcopy）；範圍外底線（原本四個檔不被改動）；`test_prepare_resume_with_params_builds_overrides_and_keeps_the_origin` | 功能 | 起始資料 | 帶改動 prepare 後，比對 `bundle["resume"]["origin"]` 與第一次送出的內容包 | `resume.origin` 與第一次送出的內容包逐項相等（含 `samplesheet`、`revision`、`params`、四個原檔文字）；`files` 裡沒有 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh` | 自動：新測試檔 |
| TC-012 | A 節①（與 origin 同名且型別與值都相同的鍵先丟掉）；`test_unchanged_values_are_dropped_and_nothing_left_is_a_plain_resume` | 功能 | 起始資料（`min_reads = 50` 整數） | 逐案：(a) 帶 `{"min_reads": 50, "primer": "B"}`；(b) 帶 `{"min_reads": 50.0}`；(c) 帶 `{"min_reads": True}`；(d) 帶 `{"min_reads": "50"}` | (a) `resume.overrides.params` 只有 `primer`，畫面沒有 `min_reads` 那行；(b)(c)(d) 值相等但型別不同（或型別不同的字串），都視為「有改」，留在 `overrides` 並顯示 `參數 min_reads：50 → …` | 自動：新測試檔 |

## User Story 2 — 不合規的改動被白話拒絕，什麼都不寫（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | A 節①；`test_params_must_be_a_mapping_and_extra_config_text` | 例外 | 起始資料 | 逐案：(a) `params` 給 list；(b) `params` 給字串；(c) `extra_config` 給數字；(d) `extra_config` 給 list | 每一案都是拒絕（Refusal／動作層的「未送出」），訊息中英並列，點名出錯的欄位（`params` 或 `extra_config`）；沒有建立確認請求、沒有 job | 自動：新測試檔 |
| TC-014 | A 節②（BundleError 轉成拒絕，點名欄位與行號）；`test_a_bad_param_or_extra_config_is_a_refusal_that_names_the_field` | 例外 | 起始資料 | 逐案：(a) `params={"input": "x"}`；(b) `params={"outdir": "x"}`；(c) `extra_config` 含 `includeConfig 'x.config'`；(d) `extra_config` 含 `$`（如 `process.memory = "${x}"`） | 每一案都被拒絕；(a)(b) 訊息點名 `input`／`outdir`；(c)(d) 訊息點名 `extra_config` 與出錯的那一行號；沒有建立確認請求、沒有 job | 自動：新測試檔 |
| TC-015 | 專長守則（錯誤訊息、日誌不含密鑰）；A 節②、動作層 `_no("未送出：…")` | 例外 | 起始資料；一個帶有 token 的使用者呼叫（HTTP 與 MCP） | 觸發 TC-013、TC-014 的各種拒絕，收集回應文字與日誌 | 訊息說明發生什麼事與該怎麼改（例如點名欄位）；沒有堆疊追蹤、沒有內部檔案路徑、沒有 SQL；回應與日誌都不含呼叫者的 token 或其他密鑰 | 自動：新測試檔 |
| TC-016 | 不做（不支援刪除參數）；裁決 3 | 不在範圍 | 起始資料；原本有 `primer` | 逐案：(a) 續跑帶改動但完全不提 `primer`；(b) 帶 `params={"primer": None}` | (a) 內容包的 `params-2.yaml` 仍含 `primer: A`（沒提到的參數保留原值）；(b) 被拒絕或 `primer` 仍是原值，不會把 `primer` 從 `params-2.yaml` 拿掉；沒有任何辦法在續跑中刪掉參數 | 自動：新測試檔 |
| TC-017 | A 節④；不做（組合圖與 gcb 維持拒絕）；`test_composed_and_google_batch_runs_are_still_refused_with_edits` | 不在範圍 | 一個組合圖送出的失敗 run；一個 Google Batch 送出的失敗 run | 逐案對兩者續跑，各試「帶改動」與「不帶改動」 | 四種組合都被拒絕，且「帶改動」的訊息與「不帶改動」的訊息是同一句（拒絕的理由不因有無改動而變） | 自動：新測試檔 |
| TC-018 | 目標（樣本表、管線、版本、運算環境仍不能在續跑裡換）；不做；E 節 | 不在範圍 | 動作層函式 `request_resume` | 讀它的參數清單 | 參數只有 `platform_path`、`run_name`、`params`、`extra_config`、`caller`、`person`、`clock`、`remote`、`index_path`；沒有 `revision`、`samplesheet`、`ce_name`、`pipeline`、`session_id` 或 run 名稱可改的欄位 | 自動：新測試檔 |

## User Story 3 — 動作層：重複呼叫、yes 只對那份內容、擁有者與上傳資料夾（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | C 節（沒給改動時照今天先呼叫 `find_attempt`）；裁決 2（無改動路徑不變）；`test_resume_platform.py` TC-014–018 照舊 | 功能 | run `x` 失敗；用無改動的一般續跑，yes 已說、job 已排入 | 對 `x` 再呼叫一次一般續跑（只給 run 名稱） | 回傳同一個工作編號（`sent`＝true，`queued`），沒有新 job、沒有新的確認請求 | 自動：新測試檔（並維持既有 `test_resume_platform.py` 綠） |
| TC-020 | C 節（靠 `create_pending` 去重）；`test_the_same_edited_resume_twice_is_one_pending_request` | 功能 | run `x` 失敗；同一位呼叫者；還沒有人說 yes | 以完全相同的改動呼叫兩次帶改動的續跑 | 只有一份待回答的確認請求（確認請求的數量為 1），兩次都指向同一份；沒有 job | 自動：新測試檔 |
| TC-021 | 裁決（17:10）1（`find_attempt` 比對 `resume.overrides`，同名同改動回同一個 job 號碼）；`confirm.py` 在範圍內 | 功能 | run `x` 失敗；帶改動 `params={"min_reads": 100}` 的續跑已說 yes 並排入佇列，工作編號為 J | 以完全相同的改動再呼叫一次 | 回傳工作編號 J（冪等）；沒有第二個 job、沒有第二份確認請求；不是「已有較新的一次」的拒絕 | 自動：新測試檔 |
| TC-022 | 裁決（17:10）1；C 節（改過的續跑不可被誤當成別的續跑）；「已知後果」第二半；`test_a_second_different_edit_for_the_same_predecessor_is_refused`（`test_resume_lineage.py` 的 TC-121／TC-128 不改） | 例外 | run `x` 失敗；先排入一次續跑（逐案：(a) 帶 `min_reads=100` 的改動續跑；(b) 不帶改動的一般續跑） | 逐案：對 (a) 之後呼叫帶不同改動（`min_reads=200`）的續跑；對 (b) 之後呼叫帶改動 `min_reads=100` 的續跑 | 兩案都不回傳先前那一次的工作編號、使用者的改動沒有被悄悄丟掉；被既有「只能對最新的一次」規則拒絕，訊息指出已存在的那一次（含它的 run 名稱）；沒有新 job | 自動：新測試檔 |
| TC-023 | 不變的底線（任何寫入都要人說 yes；yes 只對那份內容）；`test_the_yes_for_an_edited_resume_is_for_exactly_that_content`（仿 `test_resume_lineage.py` TC-089–093） | 例外 | 一份帶改動的續跑請求，人已說 yes、job 尚未被平台放行 | 逐案：yes 之後把 `resume.overrides.params` 的某個值、`resume.overrides.extra_config` 的某個字、`files["params-2.yaml"]` 的某個字各改一次 | 每一案平台端的 sha 比對都擋下，job 被拒絕、不排入、不送出 | 自動：新測試檔 |
| TC-024 | 專長守則（確認管道：未經確認不得改變資料）；憲章 invariant 2 | 例外 | 帶改動的續跑，逐案：(a) 只建立請求、沒人回答；(b) 人拒絕（decline） | 檢查資料庫與站台 | 兩案都沒有 job、沒有寫給站台的任何檔、確認請求不是 `confirmed` | 自動：新測試檔 |
| TC-025 | 專長守則（擁有者規則）；仿 TC-100–103；`test_an_edited_resume_is_still_owner_only_and_the_words_are_uniform` | 例外 | 兩位使用者 A、B；A 送出的 run `x` 失敗；有一個不存在的 run `nope` | B（HTTP）對 `x` 與對 `nope` 各呼叫帶改動的續跑 | 兩個回應是同一句話（「找不到」），看不出 `x` 存在；沒有確認請求、沒有 job | 自動：新測試檔 |
| TC-026 | 專長守則（跨使用者讀） | 例外 | A 的帶改動續跑請求待回答（有確認網址／編號） | B 登入後試著開 A 這份請求的確認頁、讀它的畫面全文 | 被拒絕或回「找不到」，B 看不到 A 的改動內容（舊值、新值、`extra_config`） | 自動：新測試檔 |
| TC-027 | 專長守則（跨使用者寫） | 例外 | 同 TC-026 | B 試著對 A 這份請求說 yes（頁面或表單） | 被拒絕；沒有 job；A 的請求狀態不變 | 自動：新測試檔 |
| TC-028 | A 節③（116b 套在改動上）；`test_a_path_param_outside_the_callers_uploads_is_refused_over_http` | 例外 | A、B 兩位使用者，各有自己的上傳資料夾；A 的 run 失敗 | A 經 HTTP 帶 `params` 其中一個值是指向 B 上傳資料夾下檔案的路徑 | 被拒絕（訊息白話）；沒有確認請求、沒有 job | 自動：新測試檔 |
| TC-029 | A 節③；`test_a_path_param_inside_them_is_recorded_in_upload_paths`、`test_without_an_area_nothing_about_upload_paths_changes` | 功能 | 同 TC-028 的設定 | 逐案：(a) A 經 HTTP 帶 `params` 路徑指向 A 自己的上傳資料夾；(b) 終端機／stdio（沒有 area）帶任何路徑參數 | (a) 通過，且該路徑出現在 `bundle["upload_paths"]`（由「origin 參數蓋上改動」的合併結果算出，取代只由 origin 算出的那份）；(b) 與今天相同：`upload_paths` 的有無與內容和無改動時的做法完全一致，沒有額外檢查 | 自動：新測試檔 |
| TC-030 | 不做（不改 relaunch）；C 節；`test_request_relaunch_takes_no_edits` | 不在範圍 | 動作層函式 `request_relaunch` | 讀它的參數清單 | 與改動前相同：沒有 `params`、`extra_config`；只有 run 名稱與既有的共用欄位 | 自動：新測試檔 |
| TC-031 | C 節（不新增名稱含 `resume`／`relaunch` 的函式）；`test_keep_submissions.py` TC-084、`test_actions_layer.py:666` | 不在範圍 | 本片全部改動 | 掃整個 `platform/` 的函式名，並檢查 `dir(actions)` | 除了既有的 `request_resume`、`request_relaunch`、`prepare_resume`、`prepare_relaunch`、`resume_screen`、`relaunch_screen` 等，沒有新增任何名稱含 `resume` 或 `relaunch` 的函式（CLI 輔助函式叫 `read_edit_args`）；上述兩個既有測試照舊綠 | 自動：既有 `test_keep_submissions.py`、`test_actions_layer.py` |

## User Story 4 — MCP 與聊天：`resume` 多兩個可選欄位，仍不能自己說 yes（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | D 節；允許更新的既有斷言（`test_resume_entrypoints.py:50`）；`test_mcp_resume_takes_run_name_and_two_optional_fields_and_relaunch_still_only_one` | 功能 | MCP server 的工具清單 | 讀 `resume` 與 `relaunch` 的輸入欄位與標註 | `resume` 欄位恰為 `run_name`、`params`、`extra_config`，必填只有 `["run_name"]`；`relaunch` 欄位仍恰為 `run_name`；兩者都沒有任何能說 yes 的欄位（`yes`、`confirm`、`approve`、`force` 這類）；兩者 `readOnlyHint`、`destructiveHint` 都是 False；工具總清單仍是既有的 13 個名稱，沒有新增工具 | 自動：新測試檔、既有 `test_resume_entrypoints.py` |
| TC-033 | D 節（描述）；`test_the_descriptions_say_what_resume_and_relaunch_are_…`（允許更新）；`test_tc136_…` 照舊 | 功能 | MCP 工具描述 | 讀 `resume` 與 `relaunch` 的描述，以及 server 的 instructions | `resume` 描述含 `params`（只寫要改的鍵，蓋在第一次送出的參數上）、`extra_config`（以 `process.memory = '16 GB'` 為例）、並說明管線、版本、樣本、環境仍是第一次送出的、要換就是新的 launch；`resume` 與 `relaunch` 的描述與 server instructions 仍含整段「不會自己送出」「The person says yes…」「It does not start anything until the person says yes.」 | 自動：新測試檔、既有 `test_resume_entrypoints.py` |
| TC-034 | D 節（其他額外參數仍被丟棄或拒絕）；允許更新的既有斷言（`:128`）；`test_mcp_resume_with_extra_fields_still_drops_revision_samplesheet_ce_and_session` | 不在範圍 | run `x` 失敗，第一次的 revision 是 `2.18.0` | 呼叫 `resume`，帶 `run_name`、`params={"primer": "OTHER"}` 加上 `revision="9.9.9"`、`samplesheet="/etc/passwd"`、`ce_name="elsewhere"`、`session_id=<另一個 UUID>` | 呼叫被拒絕，或額外欄位被丟棄；若排入：`params` 進了 `resume.overrides.params`，`resume.origin.revision` 仍是 `2.18.0`、session 仍是原本的、內容包沒有 `samplesheet`、環境不變 | 自動：新測試檔、既有 `test_resume_entrypoints.py` |
| TC-035 | 完成標準第 1 條；D 節；`test_mcp_resume_with_edits_queues_a_job_only_after_the_form_is_accepted` | 功能 | run `x` 失敗；使用者的 MCP 客戶端支援表單 | 呼叫 `resume`，帶 `params={"min_reads": 100}` 與 `extra_config="process.memory = '16 GB'"`，使用者在表單按接受 | 表單訊息只出現一次，內含 `參數 min_reads：50 → 100`、`process.memory = '16 GB'` 與最後一行指令；接受後才有 job（`sent`＝true、`state`＝queued、有工作編號） | 自動：新測試檔 |
| TC-036 | 目標（說 yes 才會送）；憲章 invariant 2（通道規則） | 例外 | 帶改動的 `resume`，逐案：(a) 表單按拒絕（decline）；(b) 經 HTTP 且客戶端沒有表單 | 呼叫 | (a) `sent`＝false，沒有 job；(b) `sent`＝false、`state`＝pending、回傳確認頁網址（含 `/c/`），沒有 job | 自動：新測試檔 |
| TC-037 | D 節；A 節②；E 節（拒絕訊息白話） | 例外 | run `x` 失敗 | MCP 呼叫 `resume`，帶 `params={"input": "x"}`（或 `extra_config` 含 `includeConfig`） | 回應是白話的「未送出」訊息，點名欄位；沒有表單、沒有確認請求、沒有 job | 自動：新測試檔 |
| TC-038 | D 節（聊天）；`test_the_chat_prompt_says_resume_can_carry_params_and_extra_config` | 功能 | 聊天的提示文字（`chat_tools.py`） | 讀提示裡 `resume` 那一行；讀 `REQUEST_TOOLS` | 那一行說明 resume 可選帶 `params`、`extra_config`；`REQUEST_TOOLS` 的內容與改動前相同（沒有新增或減少工具） | 自動：新測試檔 |
| TC-039 | D 節（檔頭說明同步改） | 功能 | `platform/abf_platform/mcp_server.py` 檔頭（原 :16-17） | 閱卷者讀檔頭 | 檔頭不再說續跑「只收 run 名稱」，改為說 `resume` 可選帶 `params`、`extra_config`；`relaunch` 的說法不變 | 手動（閱卷） |

## User Story 5 — CLI：`resume` 多三個旗標，`relaunch` 一個都不加（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | E 節；`test_cli_resume_takes_param_params_file_and_config_file_and_relaunch_does_not` | 功能 | 解析器（`abf-platform` 的命令列） | 解析 `resume x --param a=1 --param b=2 --params-file p.yaml --config-file c.config --user alice` | 成功；`--param` 可重複，兩個都收到；`--params-file`、`--config-file`、`--user` 各自收到 | 自動：新測試檔 |
| TC-041 | E 節（`relaunch` 一個旗標都不加）；不做 | 不在範圍 | 同上 | 逐案解析 `relaunch x --param a=b`、`relaunch x --params-file p.yaml`、`relaunch x --config-file c.config` | 三案都被拒絕（參數錯誤、結束）；`relaunch x` 與 `relaunch x --user alice` 仍可 | 自動：新測試檔、既有 `test_resume_entrypoints.py` |
| TC-042 | E 節（禁止的旗標仍禁止）；允許更新的既有斷言（`:169`） | 例外 | 同上 | 逐案對 `resume` 與 `relaunch` 解析：`--yes`、`-y`、`--force`、`--assume-yes`、`--no-confirm`、`--y`、`--revision`、`--samplesheet`、`--ce`、`--pipeline`、`--run-name`、`--session`、`--params a.yaml`（單數 s） | 每一案、對兩個子命令都被拒絕；`--param a=b` 對 `resume` 被接受（TC-040）但對 `relaunch` 仍被拒；`--params` 不會被當成 `--params-file` 的縮寫 | 自動：既有 `test_resume_entrypoints.py`、新測試檔 |
| TC-043 | E 節（與 `prepare_launch` 同一套）；`test_cli_param_values_are_read_like_launch` | 功能 | CLI 的 `--param` 與 `--params-file` | `--param n=3 --param f=true`；另給一個 `--params-file` | `n` 是整數 3、`f` 是布林 true（與 `launch` 相同的推斷）；`--params-file` 的內容與 `launch` 讀同一檔的結果相同；沒帶任何改動旗標時 `read_edit_args` 回 `(None, None)` | 自動：新測試檔 |
| TC-044 | E 節（`--config-file`）；`test_cli_config_file_that_is_missing_not_utf8_or_too_long_is_refused`（接受那一半） | 功能 | 一個合法的 UTF-8 設定檔，內容 `process.memory = '16 GB'`；另一個剛好 20000 字元的合法註解檔 | 逐案 `--config-file` | 兩案都被接受，內容原樣成為 `extra_config` | 自動：新測試檔 |
| TC-045 | E 節；`test_cli_config_file_that_is_missing_not_utf8_or_too_long_is_refused` | 例外 | 起始資料 | 逐案 `--config-file`：(a) 檔案不存在；(b) 不是 UTF-8 的檔；(c) 20001 字元的檔 | 三案都是白話拒絕（點名是哪個檔、哪裡不行）；沒有確認請求、沒有 job | 自動：新測試檔 |
| TC-046 | 完成標準第 1 條；目標；`test_cli_edited_resume_shows_the_diff_before_the_question`（仿 `test_resume_entrypoints.py:195` 的 pty 寫法） | 功能 | 互動終端機（pty）；run `x` 失敗 | 執行 `resume x --param min_reads=100 --config-file <含 process.memory = '16 GB'>` | 在問「要不要送出」的那句話之前，畫面已出現 `參數 min_reads：50 → 100`、`extra-2.config` 區塊全文、與完整的最後一行指令 | 自動：新測試檔 |
| TC-047 | 目標（說 yes 才會送）；憲章 invariant 2 | 例外 | 同 TC-046 | 在問題出現後回答 `n` | 顯示「未送出」之類的訊息；沒有 job、沒有確認請求被標為 confirmed、沒有寫給站台 | 自動：新測試檔 |
| TC-048 | 完成標準第 1 條 | 功能 | 同 TC-046 | 回答 `y` | 一個 job 交給代理；內容包 `resume.overrides` 為所給的改動；`files` 為 `head-2.sh`、`params-2.yaml`、`extra-2.config` | 自動：新測試檔 |
| TC-049 | E 節（沿用今天的終端機規則）；不變的底線 | 例外 | 非互動環境（管線、沒有終端機）；帶改動旗標 | 執行 `resume x --param min_reads=100` | 拒絕，說明要在終端機上互動回答 y 才會續跑；沒有任何旗標或環境變數能代替那個回答；沒有 job | 自動：新測試檔 |
| TC-050 | A 節②；E 節 | 例外 | 互動終端機 | 執行 `resume x --param input=foo`（或 `--config-file` 含 `includeConfig`） | 白話拒絕、點名欄位，結束碼非 0；沒有問 y、沒有確認請求、沒有 job | 自動：新測試檔 |
| TC-051 | E 節（說明文字） | 功能 | `abf-platform resume --help` 的說明 | 閱卷者讀說明 | 不再寫「只收 run 名稱」；說明列出 `--param`、`--params-file`、`--config-file`，並說管線、版本、樣本是第一次送出的；`relaunch --help` 的說法不變 | 手動（閱卷） |

## User Story 6 — 沒有改動時與今天完全相同；範圍不外溢（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-052 | A 節①（丟完兩項都空＝等同沒有改動）；完成標準第 2 條；`test_unchanged_values_are_dropped_and_nothing_left_is_a_plain_resume` | 功能 | 起始資料；一份「不帶任何改動」的基準內容包與畫面 | 逐案：(a) `params={}`；(b) `extra_config=""`；(c) 兩者皆空；(d) `params` 的每個值都與 origin 相同、`extra_config` 空 | 四案產生的內容包（含 sha256）與畫面全文都與基準逐字相同；`resume` 裡沒有 `overrides` 這個鍵 | 自動：新測試檔 |
| TC-053 | 完成標準第 2 條；B 節（無改動逐字同今天）；裁決 2；`test_screen_swaps_the_fixed_sentence_only_when_overrides_exist` | 功能 | 一份在改動程式之前由今天行為產生、寫死在測試裡的黃金內容包雜湊與黃金畫面 | 逐案：(a) 一般續跑的內容包 sha256；(b) 一般續跑的畫面；(c) MCP 一般續跑的表單訊息；(d) `relaunch` 的畫面 | (a) 等於黃金雜湊；(b) 等於黃金畫面，含固定句 `這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變`，不含「→」、不含 `參數 ` 行、不含 `EDITED_SENTENCE`、不含「前一次續跑的改動不會帶過來」；(c) 含同一固定句；(d) 含 `這是原樣重跑：全新資料夾，樣本與參數不變`，與今天相同 | 自動：新測試檔、既有 `test_resume_entrypoints.py:84,193`、`test_resume_platform.py:137` |
| TC-054 | 裁決（17:10）；F 節（不需要 migration）；舊的、尚未回答的續跑請求沒有 `overrides` | 功能 | 一份在這次改動之前建立、沒有 `overrides` 的續跑請求（待回答，或已確認未用） | 人說 yes，job 照常排入並執行確認／放行流程 | 照今天運作：job 排入；沒有新表、沒有新欄位；平台沒有因為缺 `overrides` 而出錯 | 自動：新測試檔 |
| TC-055 | 「必須仍綠、不准改」清單 | 功能 | 全套 `platform/tests` | 跑 `test_resume_platform.py`（TC-006／007／011、TC-014–018、TC-085／086、TC-088、TC-117）、`test_resume_render.py`、`test_station_resume.py`、`test_resume_lineage.py`（TC-089–097）、`test_resume_scope.py`（TC-146、TC-157–160）、`test_actions_layer.py`、`test_mcp.py`、`test_launch_platform.py`、`test_guidance.py`，再跑全套 | 全部通過；上述檔案沒有被修改 | 自動：既有測試與全套 |
| TC-056 | 「允許更新的既有斷言」只准四處 | 功能 | `git diff <base>...HEAD -- platform/tests/test_resume_entrypoints.py` | 閱卷者逐行讀 diff | 只有 `:50` 的欄位清單（`resume` 的 `props == {"run_name","params","extra_config"}`、`required == ["run_name"]`；`relaunch` 仍 `{"run_name"}`）、`:71` 的描述檢查、`:128` 的 `params` 進 `overrides`、`:169` 的旗標清單（只把 `["--param","a=b"]` 從 `resume` 移除、`relaunch` 不變）被改；`YES_FIELDS` 檢查、其他斷言沒有被放寬或刪除 | 手動（閱卷） |
| TC-057 | 不做（不做網頁、不加 MCP 新工具、不加 job 種類、`confirm.facts` 不加 `edited`、不加「最近用過的參數」、不自動建議、不自動重試） | 不在範圍 | 本片全部改動 | 閱卷者讀 diff；自動測試檢查工具清單與 `confirm.facts` | `web.py`、`store.py`、`jobs.py`、`receiver.py`、`abf_station/*`、`datasets.py`、`cloud_*.py`、`guidance.py`、`docs/`、`skills/` 沒有變動；網頁按鈕仍以 run 名稱呼叫 `request_resume`（無改動續跑）；MCP 工具清單仍是既有 13 個、沒有新增 job 種類；`confirm.facts` 沒有 `edited` 鍵；沒有任何程式記憶或建議參數，也沒有自動重試 | 手動（閱卷）加自動：既有 `test_mcp.py`、新測試檔 |
| TC-058 | 完成標準第 4 條；範圍：檔案（17:10 裁決加入 `confirm.py`，共 9 檔）；PR 說明要求 | 不在範圍 | 本片全部改動 | 閱卷者讀 `git diff --stat <base>...HEAD` 與 `specs/resume-edit-params-b/ledger.md` | 變動的路徑只在 `build.py`、`abf_launch/cli.py`、`actions/__init__.py`、`mcp_server.py`、`actions/chat_tools.py`、`confirm.py`、新測試檔、`test_resume_entrypoints.py`、`ledger.md` 之內；`abf_platform/cli.py` 沒有變動；ledger 貼出 `web.py`、`store.py`、`jobs.py`、`abf_station/*` 沒有變動的證據；PR 說明（若有）寫明：翻掉 009e 的哪一句、不需要 migration 的理由、白名單來源、網頁與 CE 切換為何不做、已知後果 | 手動（閱卷） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-059 | Invariant 1–3 與通道規則（唯一的送出路徑只在人確認後；沒有第二份 run 狀態；沒有寫死的個人路徑） | 功能 | 本片全部改動 | 跑 `bash tests/no_second_run_state_test.sh`、`bash tests/no_hardcoded_paths.sh`，以及 `tests/platform_test.sh` 裡的通道規則測試（`test_tch09_*`、`test_tch09_b_c_*`） | 全部通過；沒有新增送出檔；沒有新增寫死的個人或叢集路徑；未確認的啟動仍被 MCP 工具與網頁路由拒絕 | 自動：既有檢查 |
| TC-060 | 專長守則（對等性：每個使用者可見的動作對到唯一的動作層函式，路由處理函式沒有第二份邏輯） | 功能 | 續跑的使用者可見入口：CLI `resume`、MCP `resume`、聊天 `resume`、網頁按鈕 | 跑 `test_actions_layer.py`（`WRITE_NAMES` 清單與 `dir(a)`）；閱卷者確認 MCP 與聊天都呼叫 `request_resume`，網頁仍呼叫同一個 `request_resume`，這些入口裡沒有自己再組一次內容包或畫面的邏輯 | 動作清單與動作層函式清單一一對應，沒有多、沒有缺；CLI 走同一個 `build.prepare_resume`／`build.resume_screen` | 自動：既有 `test_actions_layer.py`；手動（閱卷）確認入口 |
