# 測試案例：dev-profiles-hook（執行者與驗證者把計畫裡的「專長守則」當硬規則）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務是 chore，沒有 spec.md；「對應需求」欄指的是 `specs/dev-profiles-hook/plan.md` 的「Changes」第幾項、「Out of scope」「Done when」，以及計畫末尾引用的維護者原話。
-->

**規格**：`specs/dev-profiles-hook/plan.md`（chore，無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

維護者的原話（計畫引用，逐字）：

- 「版面我完全不滿意，請你直接參考 Seqera 以及 Galaxy 的網頁」
- 「但以後developer會開發各種不同的專案，不限於agentic-bioflow」

名詞說明：「專長守則」＝開發主導者（developer-agent）依工作類型（例如畫面、後端）把一份「這類工作要遵守的規則」原文貼進計畫，標題以 `## 專長守則` 開頭；「執行者」是寫程式的 agent（`.claude/agents/executor.md`），「驗證者」是出題與驗收的唯讀 agent（`.claude/agents/verifier.md`）。

## User Story 1 — 執行者把專長守則當硬規則（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫變更 1、變更 3 | 功能 | 變更已完成 | 檢查 `.claude/agents/executor.md` | 檔內有標題 `## Specialty brief in the plan`，且有「專長守則」這個詞 | 自動：`tests/dev_workflow_test.sh` |
| TC-002 | 計畫變更 1 | 功能 | 同上 | 讀 executor.md 該段文字 | 明說：計畫若有標題以 `## 專長守則` 開頭的段落，其中規則「在本檔其他所有規則之外」同樣對這個任務有約束力（硬規則，不是建議） | 手動：驗收者逐字讀檔對照計畫變更 1（docs/TESTING.md 無對應步驟，見總覽疑點 2） |
| TC-003 | 計畫變更 1（位置） | 功能 | 同上 | 看 executor.md 各段順序 | 新段落出現在「How to work」之後 | 手動：驗收者讀檔與 `git diff` |
| TC-004 | 變更 1；維護者原話 1 | 例外 | 計畫附了一份畫面類的專長守則；計畫與專案的 DESIGN.md 都只寫到「請參考 Seqera 以及 Galaxy 的網頁」那種程度，沒有寫明任何顏色、字型、間距或版面配置 | 讀 executor.md 該段文字，看執行者遇到這種情況被要求怎麼做 | 明說要停下：回報 BLOCKED，或列在「卡住的原因／要問的問題」；明說「絕不自己猜」（never guess）；舉的例子涵蓋顏色、字型、間距、版面配置四種「沒寫就不准自己決定」的東西 | 手動：驗收者逐字讀檔（同 TC-002） |
| TC-005 | 計畫變更 1 | 例外 | 計畫附了專長守則，但守則的內容與計畫本文互相矛盾 | 讀 executor.md 該段文字 | 明說同樣要停下（BLOCKED 或列入「卡住的原因／要問的問題」），不得自行挑一邊 | 手動：驗收者逐字讀檔（同 TC-002） |
| TC-006 | 計畫變更 1 | 功能 | 變更已完成 | 檢查 executor.md 的「Report format」 | 回報格式裡有一行 `專長守則：照做／無（計畫沒附）／偏離（原因）` | 自動：`tests/dev_workflow_test.sh`（逐字比對該行；計畫變更 3 列的是最少檢查，此行為 TC 驅動的補充，見總覽疑點 1） |
| TC-007 | 計畫變更 1（位置） | 功能 | 同上 | 看回報格式內該行與「範圍外的改動」的先後 | `專長守則：…` 這行在 `範圍外的改動：…` 之前 | 手動：驗收者讀檔與 `git diff` |

## User Story 2 — 驗證者把專長守則納入出題與驗收（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 計畫變更 2、變更 3 | 功能 | 變更已完成 | 檢查 `.claude/agents/verifier.md` | 檔內有標題 `## Specialty brief in the plan`，且有「專長守則檢查」這個詞 | 自動：`tests/dev_workflow_test.sh` |
| TC-009 | 計畫變更 2（位置） | 功能 | 同上 | 看 verifier.md 各段順序 | 新段落出現在「You must not」之前 | 手動：驗收者讀檔與 `git diff` |
| TC-010 | 計畫變更 2（CONTRACT） | 功能 | 計畫附了專長守則 | 讀 verifier.md 該段文字（出題模式部分） | 明說：守則裡「適用於這個任務」的每一條執行者規則與驗證者規則，至少要對應到一個測試案例 | 手動：驗收者逐字讀檔對照計畫變更 2 |
| TC-011 | 計畫變更 2（ACCEPTANCE） | 功能 | 計畫附了專長守則，且守則點名了檢查方式（例如對產生出來的 HTML 檔跑版面偵測工具） | 讀 verifier.md 該段文字（驗收模式部分） | 明說：驗證者要執行守則點名的檢查，且這些檢查是唯讀的 | 手動：驗收者逐字讀檔對照計畫變更 2 |
| TC-012 | 計畫變更 2（ACCEPTANCE） | 功能 | 同上 | 讀同一段文字 | 明說：違反守則中標為「硬規則」的任何一條，判 FAIL | 手動：驗收者逐字讀檔 |
| TC-013 | 計畫變更 2（ACCEPTANCE） | 功能 | 同上 | 讀同一段文字 | 明說：守則指定要交給人判斷的發現，寫在「需要人看的事」之下 | 手動：驗收者逐字讀檔 |
| TC-014 | 計畫變更 2 | 功能 | 變更已完成 | 檢查 verifier.md 的 ACCEPTANCE「Report format」 | 回報格式裡有一行 `專長守則檢查：……（計畫沒附就寫「無」）` | 自動：`tests/dev_workflow_test.sh`（逐字比對該行；補充檢查，見總覽疑點 1） |
| TC-015 | 計畫變更 2（位置） | 功能 | 同上 | 看該行與「與 main 比較的退步」的先後 | `專長守則檢查：…` 這行在 `與 main 比較的退步：…` 之後 | 手動：驗收者讀檔與 `git diff` |

## User Story 3 — 不綁特定專案，並留下紀錄（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 計畫「Why」；維護者原話 2：「但以後developer會開發各種不同的專案，不限於agentic-bioflow」 | 功能 | 變更已完成 | 讀 executor.md 與 verifier.md 兩個新段落（只看新增的部分） | 新增文字不點名 agentic-bioflow、011a、Seqera、Galaxy，也不寫某個專案才有的路徑；規則以標題前綴 `## 專長守則` 觸發，不是只對某一個專案或某一種工作類型生效，所以把這兩個檔複製到新專案就能用 | 手動：驗收者讀 `git diff` 的新增行 |
| TC-017 | 計畫變更 4；維護者原話 1 | 功能 | 變更已完成 | 看 `docs/PITFALLS.md` 檔尾 | 在第 50 條之後新增一條（編號 51），格式照既有條目（粗體標題含日期）；內容簡短，說：011a 的版面被整個否決，因為計畫沒有畫面規格；修法＝開發主導者的設計關卡（PRODUCT.md / DESIGN.md）加上把 `## 專長守則` 貼進計畫，執行者與驗證者視為硬規則（本 PR）；舊的第 1–50 條一字未動 | 手動：驗收者讀 `git diff docs/PITFALLS.md` |

## User Story 4 — 範圍邊界與完成條件（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 計畫「Out of scope」：工具、模型 | 不在範圍 | 變更已完成 | 比對兩個 agent 檔與 `main` 的檔頭（frontmatter） | `tools`、`model`、`maxTurns` 等欄位與 `main` 完全相同；verifier 的 `tools` 一行仍沒有任何寫入工具 | 手動：驗收者讀 `git diff`（寫入工具部分另有 TC-024 自動把關） |
| TC-019 | 計畫「Out of scope」：Stop hook、worktree 規則 | 不在範圍 | 變更已完成 | 跑 `bash tests/dev_workflow_test.sh` | 既有的「executor 有擋住結束的 Stop 關卡」「重複嘗試結束時關卡仍然有效」「executor 在指定的 worktree 工作」檢查全部仍是 ok | 自動：`tests/dev_workflow_test.sh`（既有檢查） |
| TC-020 | 計畫「Out of scope」：不改其他檔 | 不在範圍 | 變更已完成 | `git diff --name-only main...HEAD` | 只出現計畫列的四個檔（executor.md、verifier.md、`tests/dev_workflow_test.sh`、`docs/PITFALLS.md`）加上 `specs/dev-profiles-hook/` 底下的檔；憲法、spec 範本、CI、`plugin.json` 都沒被動 | 手動：驗收者讀 `git diff --name-only` |
| TC-021 | 計畫變更 3「Keep every existing check unchanged」 | 不在範圍 | 變更已完成 | 看 `tests/dev_workflow_test.sh` 的 `git diff` | 只有新增行；沒有任何既有檢查被刪除、改弱、跳過或改了預期字串 | 手動：驗收者讀 `git diff` |
| TC-022 | 計畫「Done when」 | 功能 | 變更已完成 | 跑 `bash tests/dev_workflow_test.sh` | 含新增檢查在內全部 ok，最後印 `all passed`、結束碼 0 | 自動：`tests/dev_workflow_test.sh` |
| TC-023 | 計畫「Done when」 | 功能 | 變更已完成，在 WSL 或 Linux | 跑 `bash tests/run_all.sh` | 整套全綠 | 自動：`tests/run_all.sh`（WSL；以 CI 結果為準） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 開發流程「Independent acceptance」：驗收者必須唯讀 | 功能 | 變更已完成 | 跑 `bash tests/dev_workflow_test.sh`，看「verifier: tools grant no write」 | 該項是 ok：verifier 的 `tools` 一行沒有 Edit、Write、NotebookEdit 或 `*` | 自動：`tests/dev_workflow_test.sh`（既有檢查） |
| TC-025 | 開發流程「Test cases before code」「Green at every stage」：執行者不得弱化測試、不得派別的 agent | 功能 | 變更已完成 | 跑同一支測試，看「executor: never weakens a test」「executor: cannot dispatch agents」 | 兩項都是 ok；新增的專長守則段落沒有取代或鬆綁「Never weaken a test to make it pass」那條 | 自動：`tests/dev_workflow_test.sh`（既有檢查） |
| TC-026 | 原則 8（先量測／讀來源再主張；PITFALLS 每條對應真實失敗）| 功能 | 變更已完成 | 對照 TC-017 新增的條目與維護者 2026-10-18 的原話「版面我完全不滿意，請你直接參考 Seqera 以及 Galaxy 的網頁」 | 條目講的事（011a 版面被否決、原因是計畫沒有畫面規格）是真實發生的事件，而且條目沒有宣稱本 PR 做不到的事 | 手動：`docs/TESTING.md` 程序 P2 |
