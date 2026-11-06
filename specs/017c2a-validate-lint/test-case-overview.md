# 測試案例總覽：組合管線驗證的可選 nf-core lint（017c2a-validate-lint）

狀態：合約已確認（2026-11-03，verifier）

<!--
The line above is the gate before code (constitution 2.1.0). The independent reviewer
(`verifier`, CONTRACT mode) starts it at "草稿" and changes it to
    狀態：合約已確認（YYYY-MM-DD，verifier）
only when the plan has no blocking finding and every example of the maintainer's is
covered. If the maintainer approves the cases himself, it may instead read
    狀態：已核可（YYYY-MM-DD，maintainer）
with his words quoted under "核可紀錄". Implementation does not start while it says 草稿.
-->

**規格**：`specs/017c2a-validate-lint/plan.md`（本任務沒有獨立 spec.md，計畫即規格）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 使用者驗證已存的組合時可選擇跑 lint（平台側） | 8 | 10 | 0 | 18 |
| US2 — 站台代理在自己主機跑 lint 並誠實回報 | 16 | 12 | 0 | 28 |
| US3 — 結果存在驗證紀錄、之後讀得到 | 10 | 10 | 0 | 20 |
| US4 — 舊資料升級不壞、既有行為不變 | 8 | 0 | 0 | 8 |
| US5 — 這次不做的事 | 0 | 0 | 10 | 10 |
| 憲法與安全網 | 2 | 0 | 0 | 2 |
| **合計** | 44 | 32 | 10 | 86 |

自動驗證 83 條、手動驗證 3 條（TC-045、TC-046、TC-047，在 `docs/TESTING.md` 新一節「組合的 lint (017c2a)」，維護者自己做）。

編號說明：TC 編號按 User Story 分段（001 起、020 起、050 起、080 起、100 起、120 起），段內有空號是刻意留的，不是漏掉。

## 請你判斷的三件事

1. **每條是不是你要的？** 有沒有哪條的「預期結果」跟你想的不一樣。（你沒有針對 lint 說過逐字原話，這些全部來自 developer-agent 的計畫與裁決。）
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它。
3. **「不在範圍」對嗎？** 這次不做的事，有沒有其實這次就該做的。特別是：lint 失敗的版本**仍然可以 launch**（TC-100），版本頁**不會**顯示 lint 結果（TC-101）。

## 覆蓋檢查

- 計畫的需求（作法 1 至 7、範圍檔案、追加裁決 3 至 6）共 7 條作法加 4 條追加，全部都有測試案例：是。對照：作法 1＝TC-001、002、004、005；作法 2＝TC-003、007 至 010、014、015、017；作法 3＝TC-051、061、062、080 至 082；作法 4＝TC-050 至 069；作法 5＝TC-020 至 040；作法 6＝TC-006、007、106；作法 7＝TC-085、109；追加 3＝TC-030、031；追加 4＝TC-053；追加 5＝TC-018；追加 6＝TC-017；範圍檔案（jobs、store、handlers、docs）＝TC-016、041、043、083、087。
- 計畫的「失敗先行測試」清單（平台 15 項加站台 9 項，含端到端）全部都有對應的 TC：是。
- 計畫的完成標準（舊資料庫自動升級、文件更新、手動三步）：升級＝TC-080 至 083；文件＝TC-087；手動三步＝TC-045 至 047。「ledger 與 PR 說明要寫的內容」不是行為，驗收時由 verifier 直接讀 ledger 與 PR 文字檢查，不另立 TC。
- 維護者逐字原話：計畫明載沒有；已用計畫與追加裁決的用語取代，沒有另加行為：是。
- 專長守則（backend）：跨使用者讀寫＝TC-011、012、013；確認管道＝TC-017（lint 工作依裁決不需確認，TC 確認它不啟動管線、不產生待確認請求）；錯誤訊息與日誌＝TC-005、014、028 至 030、068；migration＝TC-080 至 083；對等性＝TC-102；動作層唯一入口、路由不含第二份邏輯＝TC-101（網頁與 MCP 原始碼不含 lint）：全部有 TC：是。
- 計畫「不做」共 9 條（`-stub-run`／nf-test、lint 擋 launch、版本頁顯示、MCP／網頁 lint 參數或新工具、自動安裝、雲端類環境代理跑 lint、lint 放進 `checks`、通知與背景輪詢、修剪舊結果），全部都有「不在範圍」測試案例：是（TC-100 至 109；TC-101 同時涵蓋版本頁與 MCP／網頁參數兩條，TC-103 涵蓋 stub-run 與 nf-test）。

## 我（撰寫者）不確定的地方

這幾點都不改變要檢查的事，TC 已寫成不依賴答案；若答案跟 TC 的讀法不同，請告訴 developer-agent 重開合約。

1. 別人的計算環境（TC-011）：回應要跟「不存在的環境」完全一樣，這樣可以嗎？計畫沒寫外層是 `ok: False` 還是 `lint.state: refused`，TC 只要求兩種情況一模一樣。
2. 站台回報不合法的 `counts`（負數、字串、超過 100000）時，計畫寫「截斷／丟棄」但沒說丟掉後顯示什麼；TC-063、064 只要求不合法的數字不會原樣留下。這樣夠嗎？
3. `lint_report` 上限 8000 字元，加上平台自己加的第一行計數後，是整體仍不超過 8000（TC-062 採這個較嚴的讀法）嗎？
4. 驗證時靜態檢查沒過、又傳了 `lint=True`，計畫沒特別說，TC 沒有為此另寫案例（依計畫字面，靜態先做並存下，再照常請求 lint）。要不要靜態沒過就不跑 lint？

## 核可紀錄

<!-- Date, the maintainer's own words, and which TCs changed because of his review. -->
（尚無。本合約由 verifier 依計畫確認，維護者尚未親自核可。）
