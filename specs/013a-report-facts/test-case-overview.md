# 測試案例總覽：013a 交付包裡的「事實報告」範本（不含 AI 文字）

狀態：合約已確認（2026-10-18，verifier）

<!--
The line above is the gate before code (constitution 2.1.0). The independent reviewer
(`verifier`, CONTRACT mode) starts it at "草稿" and changes it to
    狀態：合約已確認（YYYY-MM-DD，verifier）
only when the plan has no blocking finding and every example of the maintainer's is
covered. If the maintainer approves the cases himself, it may instead read
    狀態：已核可（YYYY-MM-DD，maintainer）
with his words quoted under "核可紀錄". Implementation does not start while it says 草稿.
-->

**規格**：`specs/013a-report-facts/plan.md`（沒有 spec.md；案例只依計畫與其 R1–R7 裁示推出）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 事實報告只用檔案填寫、缺的寫 not recorded | 12 | 7 | 2 | 21 |
| US2 — 組包放進 report.md、不蓋掉人改過的版本 | 6 | 5 | 2 | 13 |
| 憲法與安全網 | 9 | 0 | 0 | 9 |
| **合計** | 27 | 12 | 4 | 43 |

自動驗證 41 條、手動驗證 2 條（TC-042、TC-C09，都是驗收者讀 diff）。

編號對照（US1 功能 12：TC-001、002、003、007、009、010、011、014、015、016、017、018；例外 7：TC-004、005、006、008、012、013、019；不在範圍 2：TC-020、021。US2 功能 6：TC-030～034、040；例外 5：TC-035～039；不在範圍 2：TC-041、042。憲法 9：TC-C01～C09。）

## 請你判斷的三件事

1. **每條是不是你要的？** 有沒有哪條的「預期結果」跟你想的不一樣。例如：報告裡「開始時間、結束時間、狀態」目前一律會寫 `not recorded`（因為現有的紀錄檔沒有這些欄位，計畫已接受這個現況）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它。例如：在報告裡寫了自己的解讀，之後又重新組包，他的字會不會被蓋掉（TC-035～039 在管這件事）。
3. **「不在範圍」對嗎？** 這次不做：網頁、任何 AI 呼叫、雜湊（checksum）、把 MultiQC 報告複製進包、動 `platform/`、`docs/PLATFORM.md`、`CHANGELOG.md`。

## 覆蓋檢查

- 計畫的建置項目共 3 條（Build 1 腳本與五個小節、Build 2 組包與編輯保護、Build 3 可攜慣例），全部都有測試案例：是
- 計畫的裁示 R1–R7 共 7 條，全部都有測試案例：是（R1：TC-007、008、021；R2：TC-016、031～039；R3：TC-002～006；R4：TC-011、013、014、041；R5：TC-009、018；R6 只是夾具做法，由 TC-001 起的各案例使用；R7：TC-042）
- 計畫「Tests」段列出的檢查（五個標題、值與夾具相符、無 MultiQC、缺欄位、Interpretation 為空、文字可追溯、build_package 含 report.md、改過的 report.md 被保留）全部都有測試案例：是
- 計畫「Out of scope」共 3 條（不做網頁、不做任何 AI 呼叫、不動 platform/ 等三個檔），全部都有「不在範圍」測試案例：是（TC-020、TC-042）；裁示另外劃出的兩項（013a 不做 checksum、不複製 MultiQC 進包）也各有一條（TC-021、TC-041）
- 維護者原話的範例：計畫裡沒有逐字引用的維護者語句，只有計畫指定的字樣 `MultiQC report not found`、`not recorded`、`Interpretation`、`report.facts.md`，這些都被直接當作輸入或預期結果（TC-001、004～006、008、012、013、019、035～039）：是

## 我（撰寫者）不確定的地方

這些都不改變要檢查的東西，但實作者與你可能想一句話確認：

1. 計畫沒寫「provenance.json 或 methods.md 不存在時 `report_facts.py` 要怎麼辦」，所以沒有出題；要不要也規定成「明說缺哪個檔並停下」？
2. 計畫沒規定標題層級與每行的標籤用字（例如 Start 還是 Started）。TC-005 只認以 start／end／status 開頭的行，不分大小寫；若想固定寫法，請寫進計畫再改案例。
3. `.report.md.sha256` 放在 `submission/` 會被 `package_crate.py`（把整個包描述成 RO-Crate 的步驟）當成包內檔案列出來，計畫沒講這樣是否可以；本合約不檢查，只要求既有的 `package_crate_test.sh` 保持通過（TC-C08）。
4. TC-042 與 TC-C09 是請驗收者讀 diff，`docs/TESTING.md` 沒有對應的手動步驟（計畫 R7 本來就交給驗證者），這是否要補一段，由你決定。

## 核可紀錄

無（由 verifier 依計畫確認，維護者未另行核可）。
