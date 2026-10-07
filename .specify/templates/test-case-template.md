# 測試案例：[功能名稱]

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Write every row so that it can be
judged without reading code: what is set up, what the person or the system does,
what must be seen. No internal jargon without a one-line explanation.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/[###-feature]/spec.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

## User Story 1 — [標題]（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | FR-001；US1 情境 1 | 功能 | [開始前的狀態] | [誰做了什麼] | [必須看到什麼] | 自動：`tests/[檔名].sh` |
| TC-002 | FR-002 | 例外 | [狀態] | [動作] | [拒絕／提示的內容] | 自動 |
| TC-003 | 規格「不在範圍」第 1 條 | 不在範圍 | [狀態] | [動作] | [明白說不支援，且沒有做 X] | 手動：`docs/TESTING.md` |

## User Story 2 — [標題]（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|

## 憲法與安全網

<!-- Only if the feature touches one: which invariant or Safety Net rule could it break, and which TC proves it does not. Delete this section otherwise. -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|

<!--
Rules for the writer:
- Every acceptance scenario and every FR in spec.md maps to at least one TC. Every
  "out of scope" item in spec.md maps to at least one 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 (a test file under tests/, named once it exists, "自動" until then)
  or 手動 (a step in docs/TESTING.md's manual half). Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
