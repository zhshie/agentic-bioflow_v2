# 測試案例總覽：憲法 4.1.0——`skills/` 是判斷與流程的家；ADR 0006；v3 路線圖

狀態：合約已確認（2026-10-15，verifier）

**規格**：`.specify/amendments/4.1.0-skills-home/plan.md` 與 `docs/adr/0006-four-entries-one-action-layer.md`（修憲沒有 spec.md）　**明細**：`test-case.md`

**確認依據**：計畫與 ADR 已處理我第一輪提出的五個阻擋問題（PRINCIPLES.md 第 5 條、TC-026 釘字、v3 的 CI 觸發改在 `v3` 分支、done-when 的「畫圖走聊天」、POSITIONING 的「沒有 AI 工具」句），並採用 II.5 並列三處的寫法與「不承諾 MAJOR 版本號」。他的五個例子都有指到具體文件句子的案例。

## 一眼看完

| 區塊 | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| A 憲法本文與 4.1.0 紀錄（TC-001 到 015） | 15 | 0 | 0 | 15 |
| B ROADMAP（TC-016 到 026） | 11 | 0 | 0 | 11 |
| C POSITIONING（TC-027 到 030） | 4 | 0 | 0 | 4 |
| D CONTEXT（TC-031 到 034） | 4 | 0 | 0 | 4 |
| E ADR 0006／0003／0004（TC-035 到 046） | 12 | 0 | 0 | 12 |
| F 釘字、引用文件、紅燈先行（TC-047 到 054） | 8 | 0 | 0 | 8 |
| G 不在範圍（TC-055 到 064） | 0 | 0 | 10 | 10 |
| 憲法與安全網（TC-065 到 072） | 8 | 0 | 0 | 8 |
| **合計** | 62 | 0 | 10 | 72 |

自動驗證 57 條、手動驗證 15 條。

手動驗證的 15 條是 TC-051、052、055 到 063、065、068、069、072。它們都是拿 PR 跟 `main` 比的檢查，由驗收者在 ACCEPTANCE 模式執行並把證據寫進報告，不寫進 `docs/TESTING.md`（計畫已接受這個做法）。「例外」為 0，因為這支 PR 只改文件與釘字，沒有執行期的出錯情境。

## 他的五個例子在哪裡被檢查

| 例子 | 去向 |
|---|---|
| E1 「只加 MCP 網址就能用」 | 憲法 Rationale（TC-008）、ROADMAP 009 格的 `instructions` 與每個 skill 一個 prompt（TC-016）、POSITIONING 開頭「接 MCP 網址」（TC-027）、ADR（TC-036） |
| E2 「平台純粹靠GUI介面也要能使用」 | 憲法 Rationale（TC-009）、ROADMAP Stage 3 done-when 第一句（TC-020）、POSITIONING「平台網頁」與「直接用平台網頁點選」（TC-027、029）、ADR（TC-037） |
| E3 「平台也要有對話介面…」 | 憲法 Rationale（TC-010）、ROADMAP 014 原句不變（TC-019）、POSITIONING「聊天介面」（TC-027）、ADR（TC-038） |
| E4 網頁範圍、畫圖走聊天 | 憲法 Rationale（TC-011）、ROADMAP done-when 與括號（TC-020、021）、ADR（TC-039） |
| E5 「好，加 v3 分支觸發」 | 憲法 Rationale（TC-011）、ROADMAP v2/v3 段（TC-022）、ADR「CI 觸發設在 v3 分支本身」（TC-040）、這支 PR 沒碰 `.github/`（TC-060） |

## 請你判斷的三件事

1. **每條是不是你要的？** 特別看 TC-027（POSITIONING 的四個入口）、TC-020 與 TC-021（網頁到「打包」為止，圖走聊天）、TC-029（沒有 AI 的人直接用網頁點選）。
2. **有沒有漏掉的出錯情況？** 這支 PR 只改文件，我沒想到執行期的出錯情境；如果你有，請說。
3. **「不在範圍」對嗎？** 這次不動 `commands/`、`skills/`、`hooks/`、`scripts/`、`platform/`、`.github/`、CHANGELOG。「加 v3 分支觸發」由 `v3` 分支自己做，不在這支 PR。

## 覆蓋檢查

- 計畫「What changes」各小節（§1、§2、§3、§4、§4b、§5、§6）全部都有測試案例：是。
- 他的 5 個例子全部都有測試案例，且預期結果指到具體的文件句子：是。
- 計畫 §7「Not in this PR」共 3 條（涵蓋 commands/、skills/、hooks/、scripts/、platform/、.github/、LAB_AGENTS、CONDITIONS、detect_conditions.sh、CHANGELOG），全部都有「不在範圍」案例：是（TC-055 到 063；TC-064 另補「動作層只是計畫」）。
- 驗收情境：修憲沒有 Given/When/Then 驗收情境，以計畫的各小節代之。
- 紅燈先行（計畫「Red first」）：TC-051、052。
- 憲法與安全網：Safety Net 逐字不變（TC-065、066）；II.5 仍點名 `tests/works_without_host_test.sh`（TC-004、067）；憲法只改三處（TC-068）；舊修正案不動（TC-069）。

## 我（撰寫者）不確定的地方

1. 計畫「給維護者」第 2 點仍寫「再隨它大修（6.0.0）」，與 ADR 和 4.1.0 紀錄不承諾版本號不一致；要不要順手改成「隨 009 的 MAJOR 修憲」？（這段不是任何文件的引用來源，不影響本合約檢查什麼。）

## 核可紀錄

（尚無；本合約由 verifier 確認，維護者尚未另外核可。）
