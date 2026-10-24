---
id: resume-edit-params-d
title: 續跑可改參數與資源：docs/PLATFORM.md「Resume and relaunch」一節與 docs/TESTING.md 手動檢查改成新說法（等 cloud-cost 合併後再做）
tier: C
kinds: backend
lane: L12-resume
base: v3
after: resume-edit-params-c, cloud-cost
source: resume-edit-params 的第 4 片（共 4 片）；維護者 10-23 常設方向「跟Seqera platform一樣的模式，不要自己定義」；維護者 2026-10-24 11:20 核可此 C 級改動；舊計畫裁決 8（文件）
---

# resume-edit-params-d

> 本檔由 developer-agent 依 `resume-edit-params.md`（舊版，不再派）重新切分，行號重對 `origin/v3` @ `b5dcb09`。**只處理本任務**。
> ⚠️ **前置：c 片已合，且 cloud-cost（PR #188）已合進 `v3`**：#188 也改 `docs/PLATFORM.md` 與 `docs/TESTING.md`（它的範圍列了「What the platform stores」表、「Money」段與 TESTING 的 cloud-cost 小節），同時開會互相衝突。cloud-cleanup 計畫也會在這兩份加小節（加在別處）；若它先合，開工時重對行號即可。沒滿足就 BLOCKED。
> 純文件＋一個字句測試；不碰任何程式、技能、`web.py`。

## 目標
`docs/PLATFORM.md` 與 `docs/TESTING.md` 對 `resume` 的說法與行為一致：續跑可帶改動、畫面長什麼樣、哪些仍不能換、還沒在國網實測；並補上「改參數的續跑沿用快取」的手動檢查。

## 維護者原話（verifier 出題用）
- 「續跑可改參數與資源（照 Seqera）」——developer-agent 提案 2026-10-24 02:00；維護者在 2026-10-24 12:00 期限前沒有回覆 → 依預設照此範圍進行。
- 維護者 10-23 常設方向：「跟Seqera platform一樣的模式，不要自己定義」→ 名詞與行為照 Seqera 的 Resume（改參數、加設定檔，其餘不動）；不自創新概念。
- 維護者 10-24：「所有 PR 自己合併」→ Tier C（改方向）仍由 developer-agent 在 verifier PASS 與 CI 綠之後合併。
- 009e 原設計（被本任務翻掉的部分）：「續跑只收 run 名稱」；ADR 0009：「changing the samples or the parameters starts a new analysis」→ 現在變成「改樣本表／管線／版本／環境＝新分析；改一部分參數與資源＝仍是同一個分析的下一次嘗試」。
- 不變的底線（009e／憲章）：任何寫入都要人說 yes；續跑只在同一個專屬資料夾；原本四個檔（`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`）不被改動，站台用它們的 sha 檢查資料夾還是不是第一次送出的那個。
- 補記（2026-10-24 11:20）：維護者核可「這是 C 級改動」，可依此拆片進行。
- 本片負責的句子：「畫面固定句要如實說這一點，不承諾『全部沿用』」「還沒在國網驗證」。

## 範圍：檔案（最終版，4 個；只准改這些）
- `docs/PLATFORM.md`（改：「Resume and relaunch (spec 009e)」一節；`actions` 清單後那句；開頭工具說明一處）
- `docs/TESTING.md`（改：「Resume and relaunch (009e)」一節）
- `platform/tests/test_resume_edit_params_docs.py`（新）
- `specs/resume-edit-params-d/ledger.md`（新）

**不准動**：程式碼、技能、ADR、`SEQERA_PARITY.md`、`CHANGELOG.md`（c 片）、`web.py`、其他計畫新增的小節。

## 作法
`docs/PLATFORM.md`（行號 @ `b5dcb09`；若 cloud-cost／cloud-cleanup 先合，以標題為準重對）：
- `:425` 起的「Resume and relaunch (spec 009e)」：
  - `:427`「…can be gone on with by its name alone」：`relaunch` 仍只收名稱；`resume` 另可帶 `params` 與 `extra_config`。「Changing the samples, the parameters, the revision, the pipeline or the environment is a new analysis」改成「changing the samples, the pipeline, the revision or the environment is a new analysis; a resume that changes some parameters or adds resource settings is still the same analysis」。
  - `:430` 的指令範例區加一行 `abf-platform resume ampliseq-d5 --param min_reads=100 --config-file bigmem.config`（`tests/test_launch_docs.py` 會用真的 parser 檢查這一節的指令，所以旗標要與 b 片一致）。
  - `:434`「each with the one argument `run_name`」改為 `relaunch` 一個、`resume` 一個必填加兩個可選。
  - `:437`「What a resume is」：無改動時照舊；有改動時多寫 `params-<N>.yaml`（完整參數檔，`input`／`outdir` 照舊）與 `extra-<N>.config`（只在有資源設定時），`resume.overrides` 記錄改了什麼；原四檔不動；畫面改用 `EDITED_SENTENCE` 並列出舊→新與設定全文；固定句不承諾「全部沿用」（Nextflow 的語意：用到被改動的參數或資源的 task 重跑，其餘沿用）。
  - 新增一條「**What may be changed**」：`params` 蓋在第一次送出的參數上、不能刪除；`extra_config` 的封閉語法（六個 key、值的形式、只准 ASCII 且無反斜線、20000 字元）與為什麼（`-c extra-<N>.config` 排在平台的 `nextflow.config` 後面）；路徑型參數同 launch 的 116b 限制。
  - 新增一條「**Asking again**」：帶改動的 `resume` 被確認後，同內容再呼叫會被「只能對最新的一次」擋下並指出已存在的那一次；工作編號用 `get_run`。
  - `:444`「Not yet accepted on NCHC」補一句：同樣適用於改參數的續跑（「改參數後續跑沿用其餘快取」只用假站台檢查過）。
  - `:443`、`:512` 兩條（forgotten run、owner）不改。
- `:355`「Twelve tools…」那段與 `:434` 的「resume」說明對齊（只改與「one argument」衝突的字）。
- `:555`「A resume here cannot yet change resources or parameters, as Seqera's Resume dialog can; the gap is `resume-edit-params`. No migration: the field is worked out when asked.」改成：續跑現在可以改一部分參數與加資源設定（CLI、MCP）；網頁表單與運算環境切換還沒做；欄位本身（`actions` 清單）不變、不需要 migration。
- `:595`（組合圖續跑被拒）與 `:314`（Google Batch）不改：兩者續跑仍然拒絕，有無改動都一樣。

`docs/TESTING.md`（`:435` 起「Resume and relaunch (009e)」）：
- `:438` 第 2 點「the samples and parameters cannot change」改成「a resume may carry changed parameters and extra resource settings; the samples, pipeline, revision and environment cannot change」。
- 在 `:439-440`（Taiwania-3 實測，標「not yet done」）之後加一點：**改參數的續跑沿用快取（not yet done）**——對真的失敗的 run 做 `abf-platform resume RUN --param <會影響下游 process 的參數>=<新值> --config-file <含 process.memory 的檔>`，答 y；通過條件：Nextflow 以 `-resume <session id> -params-file params-2.yaml … -c extra-2.config` 啟動；`get_run` 顯示沒受影響的 task 為 cached、受影響的重跑；原資料夾的 `params.yaml`、`nextflow.config`、`head.sh`、`samplesheet.csv` 沒有被改。
- 通例（閱卷看 diff）：「改動範圍只含這四個路徑」由 executor 把 `git diff --stat` 貼 ledger，verifier 依 ledger 並自己重跑核對；不必寫進 TESTING.md。

## 失敗先行測試
新檔 `platform/tests/test_resume_edit_params_docs.py`（讀文件字句，仿 `test_launch_docs.py` 的 `read`／`flat`；每個先紅）：
- `test_platform_md_says_a_resume_may_carry_params_and_extra_config_and_a_relaunch_the_name_alone`：新字句在、舊句「by its name alone」不再同時指 resume 與 relaunch、`resume-edit-params` 那句「the gap is」已不在。
- `test_platform_md_names_the_six_keys_the_ascii_rule_and_the_20000_limit`。
- `test_platform_md_says_a_repeated_call_after_the_yes_is_refused_and_names_the_attempt`。
- `test_platform_md_still_says_not_yet_accepted_on_nchc_and_that_composed_and_google_batch_cannot_resume`。
- `test_the_resume_command_examples_in_section_9_parse_with_the_real_parser`（含新的 `--param`、`--config-file` 範例）。
- `test_testing_md_has_the_changed_params_cache_check_marked_not_yet_done`。
- 既有 `test_launch_docs.py`、`test_station_docs.py`、`tests/platform_direction_docs_test.sh` 仍綠。

預估：約 6 個具名測試、約 8 個案例；上限 60。

## 完成標準（done when）
- 上列測試與全套 `platform/tests`、shell 測試、CI 綠。
- `git diff --stat` 只含「範圍：檔案」列的 4 個路徑，且 `PLATFORM.md`／`TESTING.md` 只有 `resume` 相關段落的差異（證據貼 ledger）。
- 手動（不在本任務）：在 Taiwania-3 上實測改參數續跑沿用快取；ledger 記「未驗證」。

## 環境事實
- `docs/PLATFORM.md`（@ `b5dcb09`）：`:314`（Google Batch 拒絕續跑）；`:355`（十二個工具）；`:419-421`（forget 與續跑）；`:425-444`（本節：`:427` 名稱、`:430` 指令範例、`:434` MCP 一個參數、`:437` What a resume is、`:439` 站台做什麼、`:441` 編號欄位、`:443` 被 forget 的 run、`:444` Not yet accepted on NCHC）；`:512`（擁有者）；`:553-555`（`actions` 清單與 gap 句）；`:595`（組合圖拒絕）。舊計畫列的 `:391-410`、`:321`、`:519` 已過時。
- `docs/TESTING.md`：`:435-442`（Resume and relaunch (009e)，`:438` 字句、`:439-440` 未實測的兩點、`:442` 第 6 點）。
- 行為來源：a 片（`abf_station/launch.py` 的檔案與語法）、b 片（`EDITED_SENTENCE`、畫面、已知後果）。
- 與其他計畫的重疊：cloud-cost（#188）改 `PLATFORM.md` 的儲存表與 Money 段、`TESTING.md` 的 cloud-cost 小節；cloud-cleanup 在兩份加小節。本片只動 `resume` 相關段落。

## 不做
- 不改任何程式、技能、ADR、對照表、CHANGELOG；不改 `:314`、`:595`、`:443`、`:512`。
- 不新增章節標題（用現有「Resume and relaunch」節下的條列）；不寫尚未驗證的事為已驗證。

## 裁決（已寫進上文；與上文衝突時以上文為準，兩者不應衝突）
1. 文件：`PLATFORM.md` 該節把「by its name alone」「What a resume is」「screen shows…」三處改成有／無改動兩種寫法，並加一句「Not yet accepted on NCHC」同樣適用於改參數的續跑（作法第一組）。
2. 「改參數後續跑沿用其餘快取」只用假站台檢查過；文件與 ledger 一律寫「未驗證」，手動檢查寫進 `TESTING.md`。
3. 組合圖與 gcb 的續跑維持拒絕；文件不得暗示它們可改參數續跑。
4. 決定權：Tier C，維護者 2026-10-24 11:20 核可；合併由 developer-agent 在 verifier PASS 與 CI 綠之後執行。
5. 待維護者確認：無。

## 裁決（2026-10-24 17:10 developer-agent，以本段為準）
1. after 寫 resume-edit-params-c；另外等 cloud-cost（#188）合併後才開工，由 developer-agent 把關。

## 裁決三（2026-10-24 23:58，回應 verifier 第二次出題退回）
1. 「Asking again」以已合併 b 片的行為為準：同一份改動在 yes 之後再呼叫＝回同一個工作編號（不開第二個 job、不是拒絕）；**不同內容**的呼叫才被「只能對最新的一次」擋下並點名已存在的那一次（`test_resume_edit_params_platform.py` 約 343-360）。第 3 個測試改名為 `…a_repeated_same_call_gets_the_same_job_and_a_different_one_is_refused…`。刪掉「工作編號用 get_run 看」這句。
2. 前置：本片只改 PLATFORM.md／TESTING.md，與 c 片（#205，CI 中）檔案不相交、測試不依賴 c；**不等 c 合併，照常開工**。
3. `tests/test_launch_docs.py` 不檢查 resume：由新測試自己用真的 parser 涵蓋 resume 與 relaunch 的範例行（TC-003 照此）。
4. 行號以標題定位；`Thirteen tools` 那段若沒有「one argument」字樣就不改，只要求全文沒有「resume 只有一個參數」的說法。
5. 文件**逐字引用** `abf_launch/build.py` 的 EDITED_SENTENCE，測試對照程式裡的常數。TESTING.md 第 5 點不改。

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
