---
id: resume-edit-params-c
title: 續跑可改參數與資源：把被測試釘住的字句（MCP 開場句）、兩份技能、ADR 0009 一行註記、SEQERA_PARITY、CHANGELOG 改成新說法
tier: C
kinds: backend
lane: L12-resume
base: v3
after: resume-edit-params-b
source: resume-edit-params 的第 3 片（共 4 片）；維護者 10-23 常設方向「跟Seqera platform一樣的模式，不要自己定義」；維護者 2026-10-24 11:20 核可此 C 級改動；舊計畫裁決 8（文件）
---

# resume-edit-params-c

> 本檔由 developer-agent 依 `resume-edit-params.md`（舊版，不再派）重新切分，行號重對 `origin/v3` @ `b5dcb09`。**只處理本任務**。
> ⚠️ **前置：b 片（`resume-edit-params-b`）已合進 `v3`**；沒合就 BLOCKED。本片只改「文字」：沒有任何程式邏輯；`docs/PLATFORM.md` 與 `docs/TESTING.md` 在 d 片（要等 cloud-cost PR #188 合併，因為它也改那兩份）。
> 不碰 `skills/launch/SKILL.md`、`hooks/*`、`scripts/launch_recheck.sh`、`web.py`。

## 目標
b 片之後，工具真的接受改動了，但 MCP 開場句、兩份技能、ADR、對照表還在說「續跑只收名稱、參數不能改」。本片把它們改成與行為一致，讓 AI 客戶端與人讀到的說法一樣；並把 009e 當初為了「續跑只收名稱」而釘住的那一句測試改掉。

## 維護者原話（verifier 出題用）
- 「續跑可改參數與資源（照 Seqera）」——developer-agent 提案 2026-10-24 02:00；維護者在 2026-10-24 12:00 期限前沒有回覆 → 依預設照此範圍進行。
- 維護者 10-23 常設方向：「跟Seqera platform一樣的模式，不要自己定義」→ 名詞與行為照 Seqera 的 Resume（改參數、加設定檔，其餘不動）；不自創新概念。
- 維護者 10-24：「所有 PR 自己合併」→ Tier C（改方向）仍由 developer-agent 在 verifier PASS 與 CI 綠之後合併。
- 009e 原設計（被本任務翻掉的部分）：「續跑只收 run 名稱」；ADR 0009：「changing the samples or the parameters starts a new analysis」→ 現在變成「改樣本表／管線／版本／環境＝新分析；改一部分參數與資源＝仍是同一個分析的下一次嘗試」。
- 不變的底線（009e／憲章）：任何寫入都要人說 yes；續跑只在同一個專屬資料夾；原本四個檔（`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`）不被改動，站台用它們的 sha 檢查資料夾還是不是第一次送出的那個。
- 補記（2026-10-24 11:20）：維護者核可「這是 C 級改動」，可依此拆片進行。
- 本片負責的句子：「與 spec 009e、ADR 0009 的差異」要寫進 ADR 註記與對照表；「名詞照 Seqera」。

## 範圍：檔案（最終版，9 個；只准改這些）
- `platform/abf_platform/guidance.py`（改：`FIXED_SENTENCE`，`:16-21`，只那一句；`MAX_BYTES = 2048`（:14）不變）
- `platform/tests/test_keep_submissions.py`（只准動 `test_tc107_…`，`:850` 那一行斷言）
- `skills/operational/SKILL.md`（改：第 131 行那一段）
- `skills/runs/SKILL.md`（改：第 32-38 行「Actions only ask」段補一句例外；第 345 行；第 535 行）
- `docs/adr/0009-web-layout-three-panes.md`（改：第 44-46 行那句後面加一行註記）
- `docs/SEQERA_PARITY.md`（改：Resume 那一列，第 33 行）
- `CHANGELOG.md`（改：在 `3.0.0-dev` 清單加一條）
- `platform/tests/test_resume_edit_params_words.py`（新）
- `specs/resume-edit-params-c/ledger.md`（新）

**不准動**：上列以外的任何檔；尤其 `docs/PLATFORM.md`、`docs/TESTING.md`（d 片）、`skills/launch/SKILL.md`、`web.py`、`abf_station/*`、`abf_launch/*`、`mcp_server.py`、`chat_tools.py`。

## 作法
### A. MCP 開場句（`guidance.py` 的 `FIXED_SENTENCE`）
- 把「A failed run is resumed or relaunched with its name alone.」改成「A failed run is relaunched with its name alone; a resume may also carry changed parameters and extra resource settings.」其餘字不動。整份開場句（表＋段落＋這句）必須仍 ≤ `MAX_BYTES`（2048 bytes）：若超過，只能縮短**這一句**的措辭，不得刪別句、不得調高上限。
- 改完後 `test_keep_submissions.py:850` 的斷言（舊句的完整字串）改為檢查新句；同一測試的 `:851`（`deletes nothing until the person says yes`）與 `:852`（長度）不動。
- `test_resume_entrypoints.py:62-66`（`SENTENCE in routing_instructions()`）是另一句，不受影響。

### B. 兩份技能
- `skills/operational/SKILL.md:131`：把「…can be gone on with by its name alone…The samples and parameters are those of the first launch; a different analysis is a `launch`」改成：`relaunch` 仍只收名稱；`resume` 另可帶 `params`（只寫要改的鍵，蓋在第一次送出的參數上，不能刪除）與 `extra_config`（只收資源設定：`cpus`、`memory`、`time`、`disk`、`maxRetries`、`errorStrategy`）；CLI 是 `--param`、`--params-file`、`--config-file`；樣本、管線、版本、運算環境要換就是新的 `launch`；用到被改動的參數或資源的 task 會重跑，其餘沿用。
- `skills/runs/SKILL.md`：①`:32-38`「Actions only ask」段在「call the same tool again with the same `run_name` to get the job number」後補一句：帶改動的 `resume`，被確認後再呼叫會被拒絕並指出已存在的那一次（run 名稱），工作編號請用 `get_run` 查那個名稱（b 片的已知後果）；②`:345`「`relaunch` and `resume` cannot change parameters.」改為「`relaunch` cannot change parameters; a `resume` may carry the corrected `params`」，並保留「改樣本或管線是新分析、用 `launch`」；③`:535` 結尾「The samples and parameters are those of the first launch; changing them is a new `launch`」同樣改為與 operational 一致。`:132` 那段（resume 算可還原）不改。
- 兩份都保留含 `resume` 與 `relaunch` 的那一行（`test_resume_entrypoints.py:156` TC-138 在找它），不動 routing 表。

### C. ADR 0009、對照表、CHANGELOG
- ADR 0009 第 46 行那句後面加一行，逐字：`（Amended by the resume-edit-params task, 2026-10: a resume may change some parameters and add resource settings and stays the same analysis; changing the samples, pipeline, revision or compute environment still starts a new analysis.）`。ADR 其他段落不動。
- `docs/SEQERA_PARITY.md:33`：`| Resume | Have | |` 改成 `| Resume | Have, with edit | parameters and a restricted resource config can be changed on resume (CLI, MCP); compute-environment switch and web form: not done |`。各節標題的項數與「83」不變（`tests/platform_direction_docs_test.sh` TC-028 會數）。
- `CHANGELOG.md`：一條，說明 `resume` 可帶 `params`／`extra_config`、白名單、對組合圖與 Google Batch 仍拒絕、`relaunch` 不變、不需要 migration、未在國網實測。

## 失敗先行測試
新檔 `platform/tests/test_resume_edit_params_words.py`（每個先紅）：
- `test_the_mcp_instructions_say_a_resume_may_carry_edits_and_a_relaunch_takes_the_name_alone`：`guidance.routing_instructions()` 含新句、不含舊句「resumed or relaunched with its name alone」，且 ≤ 2048 bytes。
- `test_both_skills_say_what_a_resume_may_change_and_what_it_may_not`（用 `guidance.read_skill`）：含 `params`、`extra_config`、六個允許的 key、三個 CLI 旗標、「new `launch`」；operational 仍有含 `resume` 與 `relaunch` 的行。
- `test_the_runs_skill_no_longer_says_a_resume_cannot_change_parameters`：不含「`relaunch` and `resume` cannot change parameters」；含 `get_run` 取工作編號的那句。
- `test_adr_0009_has_the_amendment_line_verbatim_and_nothing_else_changed`：含逐字註記；ADR 其餘行與「changing the samples or the parameters starts a new analysis」那句仍在。
- `test_the_parity_row_for_resume_says_have_with_edit`；`test_the_parity_section_counts_did_not_change`（沿用 `tests/platform_direction_docs_test.sh` TC-028 的判準）。
- `test_the_changelog_has_one_entry_for_resume_edit_params`。
- 既有：`test_keep_submissions.py::test_tc107_…` 改後綠。

預估：約 8 個具名測試、約 12 個案例；上限 60。

**必須仍綠、不准改**：`test_launch_docs.py`、`test_station_docs.py`、`test_gcb_ce.py:865`、`test_gcb_launch.py:1160`（它們讀 `SEQERA_PARITY.md` 的別列）、`tests/platform_direction_docs_test.sh`、`tests/skill_runs_uses_actions_test.sh`、`test_resume_entrypoints.py:60-66, :156`、`test_guidance.py`、全套 `platform/tests` 與 CI。

## 完成標準（done when）
- 上列測試與全套 `platform/tests`、`tests/` 的 shell 測試、CI 綠。
- `git diff --stat` 只含「範圍：檔案」列的路徑（證據貼 ledger）；`guidance.py` 與 `test_keep_submissions.py` 只動上述那一句（`git diff` 貼 ledger）。
- PR 說明寫明：reverse 009e／ADR 0009 的哪一句、新舊句子對照、不需要 migration。

## 環境事實
- `platform/abf_platform/guidance.py`（@ `b5dcb09`）：`MAX_BYTES = 2048`（:14）；`FIXED_SENTENCE`（:16-21，舊句在 :19）；組字與長度檢查（:104-107）。
- 舊計畫要改 `test_guidance.py:396` 是過時的：該測試（`test_tc501_…`）現在只檢查工具名單與唯讀屬性，不讀這一句；真正釘住舊句的是 `platform/tests/test_keep_submissions.py:850`（`test_tc107_…`）。
- `docs/adr/0009-web-layout-three-panes.md:44-46`（「changing the samples or the parameters starts a new analysis」在 :46 結尾）；`docs/SEQERA_PARITY.md:33`；`skills/operational/SKILL.md:131`；`skills/runs/SKILL.md:32-38, :132, :345, :535`；`CHANGELOG.md:5`（`3.0.0-dev` 清單）。
- `tests/fixtures/runs_skill/SKILL.tw-era.md` 是「舊版技能必須讓檢查失敗」的夾具（`tests/skill_runs_uses_actions_test.sh` TC-014），**不要改**。
- 其他計畫的重疊：`CHANGELOG.md` 可能同時被別的任務加行（只加一條，衝突時保留雙方）；`skills/launch/SKILL.md` 不在本片範圍。

## 不做
- 不改任何程式邏輯；不改 `docs/PLATFORM.md`、`docs/TESTING.md`（d 片）；不改 ADR 0009 的其他段落；不改 `skills/launch/SKILL.md`。
- 不新增 skill、不新增 MCP 工具、不動 routing 表。

## 裁決（已寫進上文；與上文衝突時以上文為準，兩者不應衝突）
1. 文件：ADR 0009 加逐字一行註記；`SEQERA_PARITY.md` Resume 列改為 `Have, with edit` 並寫備註；`PLATFORM.md` 在 d 片（把「by its name alone」「What a resume is」「screen shows…」三處改成有／無改動兩種寫法，並加一句「Not yet accepted on NCHC」同樣適用於改參數的續跑）。
2. MCP 開場句只改那一句，仍 ≤ 2048 bytes；測試改成讀新句。
3. 組合圖與 gcb 的續跑維持拒絕；文字不得暗示它們可以改參數續跑。
4. 技能要誠實寫出 b 片的已知後果（帶改動的 `resume` 確認後再呼叫不會回工作編號）。
5. 決定權：Tier C，維護者 2026-10-24 11:20 核可；合併由 developer-agent 在 verifier PASS 與 CI 綠之後執行。
6. 待維護者確認：無。

## 裁決（2026-10-24 17:10 developer-agent，以本段為準）
1. FIXED_SENTENCE 超過 2048 位元組上限時只縮那一句。

## 裁決二（2026-10-24 22:50 developer-agent，回應出題退回；以本段為準，取代作法 B①、失敗先行測試第 3 條與裁決 4 中「被拒絕、用 get_run 查」的說法）
1. skills/runs/SKILL.md 的「已知後果」照 b 片（#201）實際行為寫：**同一份改動在按「是」之後再呼叫一次＝回同一個工作編號**；**不同的改動，或改動與一般續跑互換**，才會被「只能對最新的一次」規則拒絕，訊息會指出已存在的那一次。失敗先行測試第 3 條改成檢查這兩句，不再提 get_run。
2. ADR 0009 的註記另起一行、放在第 2 點最後一行之後，其餘逐字不動。
3. 開場句長度約 1717 位元組，低於 2048，不必縮句。

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
