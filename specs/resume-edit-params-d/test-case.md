# 測試案例：續跑可改參數與資源（d：文件與手動檢查）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本件沒有 spec.md，依據是計畫（含「裁決三」）與維護者原話。
-->

**規格**：`specs/resume-edit-params-d/plan.md`（本件沒有 spec.md，計畫即依據；計畫「作法」與「裁決三」衝突處以「裁決三」為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做，或文件沒有暗示它做得到。

驗證方式：「自動」＝新測試檔 `platform/tests/test_resume_edit_params_docs.py`（或既有測試）；「手動（閱卷）」＝verifier 讀 `git diff <base>...HEAD` 與文件原文判定；「混合」＝兩者都要。「PLATFORM.md」「TESTING.md」指 `docs/` 下的檔；所有位置一律以標題定位，不看行號。

## User Story 1 — PLATFORM.md 說清楚續跑現在能帶什麼（優先度 P1）

維護者原話：「續跑可改參數與資源（照 Seqera）」；「跟Seqera platform一樣的模式，不要自己定義」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 PLATFORM.md 第 1 條；測試 `test_platform_md_says_a_resume_may_carry_params_and_extra_config_and_a_relaunch_the_name_alone` | 功能 | 實作完成後的 `docs/PLATFORM.md`「Resume and relaunch (spec 009e)」一節 | 讀這一節開頭說明 | 寫明：`resume` 另可帶 `params` 與 `extra_config`；`relaunch` 仍只收 run 名稱 | 自動：`test_resume_edit_params_docs.py` |
| TC-002 | 維護者原話「改樣本表／管線／版本／環境＝新分析；改一部分參數與資源＝仍是同一個分析的下一次嘗試」；作法第 1 條 | 功能 | 同上 | 讀同一節的分界句 | 寫明：改樣本、管線、版本或環境是新分析（要用 `launch`）；續跑改一部分參數或加資源設定，仍是同一個分析 | 自動：同上（第 1 個測試） |
| TC-003 | 作法第 1 條（舊句要拿掉） | 功能 | 同上 | 在整份 PLATFORM.md 找舊句「can be gone on with by its name alone」與「Changing the samples, the parameters, the revision, the pipeline or the environment is a new analysis」 | 舊整句不再存在；「by its name alone」不再同時指 resume 與 relaunch；全文沒有任何「resume 只有一個參數／只收名稱」的說法 | 自動：同上（第 1 個測試） |
| TC-004 | 作法第 2 條；裁決三 3、對應測試 `test_the_resume_command_examples_in_section_9_parse_with_the_real_parser` | 功能 | 同一節的指令範例區 | 取出範例區所有 `abf-platform resume …` 與 `abf-platform relaunch …` 行，交給真的指令解析器（`abf_platform.cli.build_parser()`） | 有一行 `abf-platform resume ampliseq-d5 --param min_reads=100 --config-file bigmem.config`；原本的 resume、relaunch 範例仍在；每一行都被解析器接受；至少檢查到 3 行 | 自動：同上 |
| TC-005 | 作法第 3 條 | 功能 | 同一節的 MCP 說明段 | 讀「Over MCP they are the tools `resume` and `relaunch`…」 | `relaunch` 寫成一個參數；`resume` 寫成一個必填（run 名稱）加兩個可選（`params`、`extra_config`）；舊的「each with the one argument `run_name`」不在 | 自動：同上（第 1 個測試） |
| TC-006 | 作法「`Thirteen tools` 那段」；裁決三 4 | 功能 | PLATFORM.md 開頭的工具說明（現為「Thirteen tools…」） | 讀這一段對 `resume` 的說法 | 與 TC-005 一致：若這段原有與「one argument」衝突的字就已改掉；若原本沒有這類字樣就沒被動（只要求全文沒有「resume 只有一個參數」的說法，見 TC-003） | 手動（閱卷） |

## User Story 2 — 說清楚有改動與沒改動的續跑各長什麼樣（優先度 P1）

維護者原話（本片負責的句子）：「畫面固定句要如實說這一點，不承諾『全部沿用』」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-007 | 作法「What a resume is」：無改動時照舊 | 功能 | 「What a resume is」條列 | 讀沒有改動時的說明 | 與修改前相同：只多一個 `head-<N>.sh`，畫面用「這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變」 | 手動（閱卷） |
| TC-008 | 作法「What a resume is」：有改動時多寫的檔 | 功能 | 同上 | 讀有改動時的說明 | 寫明多寫 `params-<N>.yaml`（完整參數檔，`input`／`outdir` 照舊）與 `extra-<N>.config`（只在有資源設定時才有），且 `resume.overrides` 記錄改了什麼 | 自動：同上 |
| TC-009 | 裁決三 5；作法「畫面改用 `EDITED_SENTENCE`」 | 功能 | `platform/abf_launch/build.py` 的 `EDITED_SENTENCE` 常數 | 比對文件與程式常數 | PLATFORM.md 逐字含有 `build.EDITED_SENTENCE`（「這是續跑：同一個資料夾；下面的參數與設定有改，用到它們的 task 會重新跑，其餘已完成的 task 沿用」），並寫明畫面列出舊→新與設定全文 | 自動：同上（測試 import 程式裡的常數來比對，不得把句子再抄一份寫死） |
| TC-010 | 作法「What a resume is」：Nextflow 的語意 | 功能 | 同上 | 讀有改動時的說明 | 寫明：用到被改動的參數或資源的 task 會重跑，其餘沿用 | 自動：同上 |
| TC-011 | 維護者原話「不承諾『全部沿用』」 | 功能 | 同上 | 讀有改動時的說明全文 | 沒有任何一句承諾「改了之後所有已完成的 task 都會沿用」；「樣本和參數不變」那句只出現在無改動的說明裡，不出現在有改動的說明裡 | 手動（閱卷） |

## User Story 3 — 說清楚哪些可以改、哪些不行（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法「What may be changed」：params | 功能 | 同一節新增的「What may be changed」條列 | 讀 params 的說明 | 寫明：`params` 蓋在第一次送出的參數上；不能刪除參數（只能新增或改值） | 手動（閱卷）；事實對照 `platform/abf_launch/build.py` 的 `edits_of`／`prepare_resume` | 
| TC-013 | 作法「What may be changed」：六個 key；測試 `test_platform_md_names_the_six_keys_the_ascii_rule_and_the_20000_limit` | 功能 | 同上 | 讀 `extra_config` 的說明 | 逐一點名 `cpus`、`memory`、`time`、`disk`、`maxRetries`、`errorStrategy`，且恰這六個，與 `abf_station/launch.py` 的 `EXTRA_KEYS` 一致 | 自動：同上 |
| TC-014 | 作法「What may be changed」：值的形式 | 功能 | 同上 | 讀 `extra_config` 的說明 | 寫明這是封閉語法：只收資源設定行（單行 `process.<key> = <值>`，或放在 `process {`／`withName`／`withLabel` 區塊內），不是任意 Nextflow 設定；值要符合固定形式（例如記憶體、時間寫成帶單位的引號字串） | 手動（閱卷）；對照 `abf_station/launch.py` 的 `EXTRA_VALUE`、`EXTRA_ASSIGN`、`EXTRA_BLOCK` |
| TC-015 | 作法「What may be changed」：ASCII 規則 | 功能 | 同上 | 讀 `extra_config` 的說明 | 寫明只准 ASCII 可列印字元（加換行與 tab），且不准有反斜線 | 自動：同上 |
| TC-016 | 作法「What may be changed」：20000 字元 | 功能 | 同上 | 讀 `extra_config` 的說明 | 寫明上限 20000 字元，與 `abf_station/launch.py` 的 `MAX_EXTRA_CONFIG` 一致 | 自動：同上 |
| TC-017 | 作法「What may be changed」：為什麼 | 功能 | 同上 | 讀「為什麼要這樣限制」 | 寫明 `-c extra-<N>.config` 排在平台的 `nextflow.config` 後面（後面的說了算），所以必須限制語法，不能讓它推翻平台自己的設定 | 手動（閱卷）；對照 `abf_station/launch.py` 起 Nextflow 那一行 |
| TC-018 | 作法「What may be changed」：路徑型參數 | 功能 | 同上 | 讀路徑型參數的說明 | 寫明改動的路徑型參數受與 `launch` 相同的 116b 限制（在自己的上傳資料夾內） | 手動（閱卷） |
| TC-019 | 維護者原話「改樣本表／管線／版本／環境＝新分析」；計畫目標「哪些仍不能換」 | 不在範圍 | 同一節 | 讀文件中樣本、管線、版本、環境的說法 | 沒有任何一句暗示續跑可以換這四樣；仍明說那是新分析、要用 `launch` | 手動（閱卷） |
| TC-020 | 作法「`actions` 清單後那句」 | 功能 | PLATFORM.md 描述 `actions` 欄位處 | 讀 `actions` 清單後那一段 | 舊句「A resume here cannot yet change resources or parameters…; the gap is `resume-edit-params`」不在；改成：續跑現在可以改一部分參數與加資源設定（CLI、MCP）；網頁表單與運算環境切換還沒做；`actions` 欄位本身不變、不需要 migration | 混合：舊句消失由 `test_resume_edit_params_docs.py` 的第 1 個測試檢查；新句內容由閱卷 |
| TC-021 | 作法「網頁表單與運算環境切換還沒做」 | 不在範圍 | 同上 | 在 PLATFORM.md 找有沒有說網頁表單或運算環境切換已經做好 | 沒有；網頁仍是唯讀，文件只說這兩樣「還沒做」 | 手動（閱卷） |

## User Story 4 — 「Asking again」：同一份改動再呼叫一次（優先度 P1）

維護者原話：「任何寫入都要人說 yes」（不變的底線）。以已合併的 b 片行為為準（裁決三 1）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 裁決三 1；測試 `test_platform_md_says_a_repeated_same_call_gets_the_same_job_and_a_different_one_is_refused…`（名稱以此為準，不再是 `…is_refused_and_names_the_attempt`） | 功能 | 同一節新增的「Asking again」條列 | 讀「帶改動的續跑已經被 yes 之後，用同樣內容再呼叫一次」的說明 | 寫明：回同一個工作編號，不會開第二個 job，也不會再問一次 | 自動：同上 |
| TC-023 | 裁決三 1 | 例外 | 同上 | 讀「用不同內容再呼叫」的說明 | 寫明：不同內容的呼叫被「只能對最新的一次」擋下，且訊息點名已經存在的那一次 | 自動：同上 |
| TC-024 | 裁決三 1：刪掉「工作編號用 get_run 看」 | 功能 | 同上 | 讀「Asking again」條列全文 | 沒有說「同內容再呼叫會被拒絕」；沒有「工作編號用 `get_run` 看」這句 | 自動：同上 |

## User Story 5 — 仍然成立的限制不被動到（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 作法「Not yet accepted on NCHC 補一句」；測試 `test_platform_md_still_says_not_yet_accepted_on_nchc_and_that_composed_and_google_batch_cannot_resume` | 功能 | 同一節的「Not yet accepted on NCHC」條列 | 讀這一條 | 原有內容仍在，並補一句：同樣適用於改參數的續跑——「改參數後續跑沿用其餘快取」只用假站台檢查過，還沒在國網驗證 | 自動：同上 |
| TC-026 | 維護者原話、裁決 3：組合圖與 Google Batch 續跑維持拒絕 | 不在範圍 | PLATFORM.md 組合圖「Not supported yet」與 Google Batch「Not yet」兩處 | 讀這兩處 | 兩處仍寫續跑會被拒絕，有無改動都一樣；文件任何地方都沒有暗示它們可以改參數續跑；這兩處原文未被修改 | 自動：同上（同一個測試）；原文未動由閱卷看 diff |
| TC-027 | 作法「forgotten run、owner 兩條不改」 | 不在範圍 | 「A forgotten run」條列與「Resume and relaunch. Only the owner…」條列 | 看 diff | 這兩條文字與修改前完全相同 | 手動（閱卷） |

## User Story 6 — TESTING.md 的手動檢查（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | 作法 TESTING.md「第 2 點」 | 功能 | `docs/TESTING.md`「Resume and relaunch (009e)」節第 2 點（The words） | 讀這一點 | 舊的「the samples and parameters cannot change」不在；改成「a resume may carry changed parameters and extra resource settings; the samples, pipeline, revision and environment cannot change」 | 手動（閱卷） |
| TC-029 | 作法 TESTING.md 新增一點；測試 `test_testing_md_has_the_changed_params_cache_check_marked_not_yet_done` | 功能 | 同一節 | 找 Taiwania-3 實測那兩點（標 not yet done）之後 | 多了一點，主題是「改參數的續跑沿用快取」，並標明 not yet done | 自動：同上 |
| TC-030 | 作法 TESTING.md 新增一點：步驟 | 功能 | 同上 | 讀新增那一點的步驟 | 寫明：對一個真的失敗的 run 執行 `abf-platform resume RUN --param <會影響下游 process 的參數>=<新值> --config-file <含 process.memory 的檔>`，並答 y | 自動：同上 |
| TC-031 | 作法 TESTING.md 新增一點：通過條件 1 | 功能 | 同上 | 讀通過條件 | 寫明：Nextflow 以 `-resume <session id> -params-file params-2.yaml … -c extra-2.config` 啟動 | 自動：同上 |
| TC-032 | 同上：通過條件 2 | 功能 | 同上 | 讀通過條件 | 寫明：`get_run` 顯示沒受影響的 task 為 cached、受影響的重跑 | 自動：同上 |
| TC-033 | 同上：通過條件 3 | 功能 | 同上 | 讀通過條件 | 寫明：原資料夾的 `params.yaml`、`nextflow.config`、`head.sh`、`samplesheet.csv` 沒有被改 | 自動：同上 |
| TC-034 | 裁決三 5：TESTING.md 第 5 點不改 | 功能 | 同一節原第 3、4、5、6 點 | 看 diff | 原第 3、4 點仍標 not yet done；原第 5 點（PR 要寫 not yet accepted on NCHC）與第 6 點（runs skill 手動檢查）文字不變（因插入一點而順延編號可以） | 手動（閱卷） |

## User Story 7 — 範圍、流程與測試品質（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 完成標準 2；通例 | 功能 | 實作完成的 worktree | verifier 自己跑 `git diff --stat <base>...HEAD`（加上未提交的 `git diff`） | 只含 4 個路徑：`docs/PLATFORM.md`、`docs/TESTING.md`、`platform/tests/test_resume_edit_params_docs.py`、`specs/resume-edit-params-d/ledger.md` | 手動（閱卷） |
| TC-036 | 完成標準 2：只有 resume 相關差異 | 功能 | 同上 | 看 `PLATFORM.md`、`TESTING.md` 的 diff | 差異只在：Resume and relaunch 一節、`actions` 清單後那句、開頭工具說明（若需要）；cloud-cost 的儲存表與 Money 段、TESTING 的 cloud-cost 小節及其他計畫的小節沒有被動 | 手動（閱卷） |
| TC-037 | 不做：不新增章節標題 | 不在範圍 | 同上 | 看兩份文件 diff 中新增行 | 沒有新增以 `#` 開頭的標題行；新內容都是現有「Resume and relaunch」節下的條列 | 手動（閱卷） |
| TC-038 | 不做／「不准動」 | 不在範圍 | 同上 | 看 diff 的檔案清單與內容 | 程式碼、技能、ADR、`SEQERA_PARITY.md`、`CHANGELOG.md`、`web.py` 完全沒被動（包含 `platform/abf_*`、`skills/`） | 手動（閱卷） |
| TC-039 | 失敗先行 | 功能 | 新測試檔 | verifier 把新測試檔放在 base 的文件上跑（或等價地確認每個具名測試在舊文件上會失敗） | 6 個具名測試在舊文件上全部失敗，在新文件上全部通過；測試不是只檢查檔案存在或只 grep 自己新增的字 | 手動（閱卷＋執行單一測試檔） |
| TC-040 | 完成標準 1：既有測試仍綠 | 功能 | 實作完成 | 跑 `platform/tests/test_launch_docs.py`、`platform/tests/test_station_docs.py`、`tests/platform_direction_docs_test.sh`，以及全套 `platform/tests` 與 shell 測試 | 全部通過 | 自動：既有測試 |
| TC-041 | 防放水 | 功能 | 同上 | 看 `git diff <base>...HEAD -- platform/tests` | 只有新增 `test_resume_edit_params_docs.py`；沒有既有測試被刪除、略過、放寬或改期望值 | 手動（閱卷） |
| TC-042 | 完成標準 2：證據貼 ledger | 功能 | `specs/resume-edit-params-d/ledger.md` | 讀 ledger | 貼有 `git diff --stat` 的輸出，與 TC-035 verifier 自己重跑的結果相符 | 手動（閱卷） |
| TC-043 | 完成標準 3：手動實測不在本任務 | 不在範圍 | ledger 與兩份文件 | 讀 ledger、新增的 TESTING.md 那一點 | 在 Taiwania-3 實測改參數續跑沿用快取沒有被做；ledger 記「未驗證」；TESTING.md 那一點仍標 not yet done | 手動（閱卷） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 憲章第 8 條（先量測或讀原始碼才宣稱）；計畫「不寫尚未驗證的事為已驗證」 | 功能 | 兩份文件中所有談到「改參數續跑沿用快取」的句子 | 逐句讀 | 每一句都帶「只用假站台檢查過」或「not yet」之類的標示；沒有任何一句寫成已在國網驗證 | 混合：「Not yet accepted on NCHC」一條由自動測試檢查；其他句子由閱卷 |
| TC-045 | 009e 底線：任何寫入都要人說 yes | 功能 | 同一節 | 讀「Every attempt asks again」那段 | 仍在，且沒有被改弱：帶改動的續跑也一樣要人說 yes 才會開始；上一次的 yes 不會被沿用 | 手動（閱卷）：看 diff 確認該句未被刪改 |
| TC-046 | 009e 底線：續跑只在同一個專屬資料夾；原四檔不動 | 功能 | 同一節「What a resume is」 | 讀有改動的說明 | 寫明有改動時原本的 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh` 四檔不被改動，站台用它們的 sha 檢查資料夾仍是第一次送出的那個；續跑只在同一個資料夾 | 自動：`test_resume_edit_params_docs.py` |
| TC-047 | 維護者常設方向「跟Seqera platform一樣的模式，不要自己定義」 | 不在範圍 | 新增的所有文件句子 | 找新名詞 | 沒有自創新概念或新名詞；只用既有的 `params`、`extra_config`、`resume.overrides`、`params-<N>.yaml`、`extra-<N>.config`，說法對應 Seqera Resume「改參數、加設定檔」 | 手動（閱卷） |
