# 測試案例總覽：沒在用 agentic-bioflow 時，plugin 完全安靜

狀態：已核可（2026-10-02，maintainer）

<!--
The line above is the approval gate. It becomes
    狀態：已核可（YYYY-MM-DD，maintainer）
only after the maintainer says so in the conversation, and the words he used are
quoted under "核可紀錄" below. /speckit-plan does not run while it says 草稿.
-->

**規格**：`specs/005-plugin-scope/spec.md`　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 沒在用 abf 的 session 不被打擾 | 6 | 0 | 0 | 6 |
| US2 — 在用 abf 時，安全網照舊 | 9 | 1 | 0 | 10 |
| US3 — 判斷失誤時往安全那邊倒 | 1 | 3 | 0 | 4 |
| 憲法、文件與效能 | 3 | 0 | 1 | 4 |
| **合計** | 19 | 4 | 1 | 24 |

全部自動驗證。

## 請你判斷的三件事

1. **TC-003 是你要的嗎？** 不在用時，`rm -rf results/` 也不會攔。這是你選「全部關掉」的直接後果，憲法要升到 2.0.0。
2. **TC-020 對嗎？** 主 session 用過 abf，它派出的 subagent 也算在用（TC-006）；但另一個獨立 session 用過，不算。
3. **TC-009、TC-010 的資料夾規則夠嗎？** 只有在部署的根目錄或 run 區裡才算在用。如果你常在別的資料夾裡處理 abf 的結果，那裡不會被保護。

## 覆蓋檢查

- 需求 FR-001～008 都有測試案例：是（FR-001 由 TC-001～005 與 TC-007～013 共同覆蓋）
- 驗收情境共 13 條（US1 5、US2 6、US3 2），全部都有測試案例：是
- 不在範圍 3 條：第 1 條有 TC-024；第 2、3 條是另一張單（#34、#35），本次不測。

## 我（撰寫者）不確定的地方

1. **subagent 帶主 session 的 ID：已確認**。官方 hooks 文件寫明 PreToolUse 對 subagent 也觸發，帶同一個 `session_id`，另外加 `agent_id`／`agent_type`〔來源：code.claude.com/docs/en/hooks.md〕。所以主 session 在用，它的 subagent 也算在用（TC-006 的前提成立）。
2. **TC-023 的速度量測**容易受機器負載影響，所以只比平均、設容許誤差，不設絕對秒數。

## 核可紀錄

- 2026-10-02 維護者：「005、006 核可，#31 關掉」
