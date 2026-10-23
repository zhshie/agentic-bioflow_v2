# 測試案例總覽：HTTP launch 可用環境 readRoots 內的站台檔；MCP launch 加 samplesheet_text

狀態：合約已確認（2026-10-23，verifier）

<!--
The line above is the gate before code (constitution 2.1.0). The independent reviewer
(`verifier`, CONTRACT mode) starts it at "草稿" and changes it to
    狀態：合約已確認（YYYY-MM-DD，verifier）
only when the plan has no blocking finding and every example of the maintainer's is
covered. If the maintainer approves the cases himself, it may instead read
    狀態：已核可（YYYY-MM-DD，maintainer）
with his words quoted under "核可紀錄". Implementation does not start while it says 草稿.
-->

**規格**：`specs/http-launch-site-samplesheet/plan.md`（沒有獨立 spec.md；plan 的目標、維護者原話、作法、不做段即規格）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 站台檔案路徑能從 Claude 送出 | 10 | 0 | 0 | 10 |
| US2 — 不該放行的形狀仍然被拒 | 0 | 14 | 0 | 14 |
| US3 — samplesheet_text 參數 | 4 | 8 | 0 | 12 |
| US4 — 沒被放寬的其他規則 | 5 | 5 | 0 | 10 |
| US5 — 確認管道與跨使用者 | 1 | 6 | 0 | 7 |
| US6 — 文件、舊釘子、對等性 | 4 | 0 | 0 | 4 |
| 不在範圍（計畫「不做」段） | 0 | 0 | 5 | 5 |
| 憲法與安全網 | 1 | 2 | 0 | 3 |
| **合計** | 25 | 35 | 5 | 65 |

自動驗證 65 條、手動驗證 0 條。

## 請你判斷的三件事

1. **每條是不是你要的？** 有沒有哪條的「預期結果」跟你想的不一樣。特別是 US2（哪些形狀仍然要拒）與 TC-024（samplesheet 檔本身仍須在自己的上傳資料夾，只放寬 CSV 裡的格子）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它。
3. **「不在範圍」對嗎？** 這次不做的事（上傳工具、代理去站台讀 samplesheet、遠端站台每人資料夾、角色與共享、網頁表單加 `samplesheet_text`），有沒有其實這次就該做的。

## 覆蓋檢查

- 規格裡的需求共 6 條（作法 1 路徑格規則、作法 2 samplesheet_text、作法 3 resume/relaunch、作法 4 文件、失敗先行測試各項、完成標準各項），全部都有測試案例：是
  - 作法 1 → TC-001、002、005、006、011..024、037..040、044..046、CS-03
  - 作法 2 → TC-001、003、004、007..009、025..036、047、048、CS-01
  - 作法 3 → TC-010
  - 作法 4 → TC-054
  - 失敗先行測試各條（text 通過、路徑通過、readRoots 包住 uploads 指到別人、readRoots 之外被拒、兩個都給／都沒給、1 MiB、NUL、同 text 兩次、終端機與 stdio 不變、TC-049 改寫）→ TC-001、002、011、019、025、026、028、030、008、039、040、046、036、055
  - 完成標準（測試全綠、文件三處、ledger、PR 標題）→ TC-054、055、056；PR 標題屬流程，不由 TC 驗
- 維護者原話與例子：「放寬 readRoots 內站台檔」→ TC-001、002；「uploads 內仍只能是自己的」→ TC-011..018、023；「加 samplesheet_text」→ TC-001、025..036；nano4／ampliseq 2.18.0／10 個 Day5 fastq／`sampleID,forwardReads`／`path_columns=["forwardReads"]`，且不再出現舊拒絕字句 → TC-001、TC-003、TC-007：是
- 規格裡「不做」共 5 條（上傳工具、代理去站台讀 samplesheet、遠端站台每人資料夾、角色與共享、不改誰能按送出與代理端複查），全部都有「不在範圍」測試案例：是（TC-058..062；代理端複查不改另見 TC-041..043）
- 專長守則（backend）的 verifier 規則（對等性、跨使用者讀與寫、確認管道、錯誤訊息與日誌、migration）全部有 TC：是（TC-056／036、TC-049／050／051／044、TC-047／048／CS-01／CS-02、TC-052／053、TC-057）

## 我（撰寫者）不確定的地方

1. 路徑格剛好是 A 自己的資料夾本身（沒有檔名的目錄）：舊規則拒，116b 的 params 規則放行；計畫說「同一條規則」。這格要放行還是拒？我沒有用 TC 釘死它。
2. 核可後，共享資料夾（readRoots 內、不在上傳區）裡的連結被改指向別人的上傳資料夾：代理端複查只蓋上傳區記錄的格子，這次不擋（計畫明寫不改代理端複查）。請求當下的連結有 TC-013 守住。這個剩餘風險你接受嗎？
3. 空字串的 `samplesheet_text` 我當成「沒給內容」而拒絕（TC-027）。這樣對嗎？
4. 網頁表單這次不加 `samplesheet_text`（只有 MCP 加）。這樣對嗎？
5. verifier 不能碰真正的 nano4，所以「真實 10 個 Day5 fastq 在站台上真的跑起來」沒有 TC 能證明；TC-001／003／007 只證明平台這側會放行並送到代理。要不要在 merge 後由你或 lab-agent 實跑一次？

## 核可紀錄

（尚無。維護者 2026-10-23 的原話已記在計畫「維護者原話」，是出題依據，不是對本份案例的核可。）
