# 測試案例總覽：憲法 6.2.0（合併規則對齊現況）＋ PRODUCT.md／DESIGN.md 補原話

狀態：合約已確認（2026-11-03，verifier）

**規格**：`specs/charter-v4-workflow/plan.md`（本任務無 spec.md，以計畫及其兩輪「裁決（自動補）」為準）　**明細**：`test-case.md`

## 派工前提（給 developer-agent，不是給 executor）

憲法文字由 developer-agent 預先 commit 在 `charter-v4-base`，executor 不得改憲法。核對時發現目前工作樹的憲法**還沒有**兩輪裁決要求補回的字句：Workflow 最後一條沒有 "modified or removed"，6.2.0 條目的 What changes 也沒有寫「需求的修改或刪除仍等維護者的 yes」。TC-008 與 TC-022 在目前的 base 上會是紅的。派 executor 之前，須先在 `charter-v4-base` 補上這兩處；否則 executor 無法讓它們變綠（它不准改憲法），只能回報 BLOCKED。

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 憲法 6.2.0 條文與版本（TC-001 到 TC-027） | 27 | 0 | 0 | 27 |
| US2 — PRODUCT.md（TC-030 到 TC-037） | 6 | 0 | 2 | 8 |
| US3 — DESIGN.md 原話 23–25（TC-038 到 TC-046） | 4 | 0 | 5 | 9 |
| US4 — 測試（TC-047 到 TC-053、TC-057） | 7 | 0 | 1 | 8 |
| 憲法與安全網（TC-028、029、054、055、056） | 3 | 0 | 2 | 5 |
| US5 — 範圍與流程（TC-058 到 TC-063） | 3 | 0 | 3 | 6 |
| **合計** | 50 | 0 | 13 | 63 |

自動驗證 48 條、手動驗證 15 條（合計 63）。

說明：

- 「例外」為 0：本任務只改文件與測試，沒有執行時出錯的情況；「舊字句不得殘留」放在功能，「不該動的沒動」放在不在範圍。
- 計畫裁決第一輪 6 寫的「自動 41、手動 14」來自已不存在的舊版合約；這裡是重新逐條數出來的 48／15，以本表為準。
- 手動案例都標明「不適用 `docs/TESTING.md`」（計畫裁決第二輪 2：該手動半部只在動到 `commands/`、`skills/`、`hooks/` 的發行前跑），具體指令寫在各列的步驟欄，證據貼 `specs/charter-v4-workflow/ledger.md`。
- 計畫指定的編號已對上：TC-030（Not 行 later 清單之前不含 "web terminal;"）、TC-031（later 子句含 web terminal、later、constitution amendment）。

## 維護者原話對照

| 原話 | 對應 TC |
|---|---|
| 2026-10-24「以後你都自己合併」 | TC-007、TC-017 |
| 2026-11-03「合併規則同意」 | TC-006、TC-018、TC-026、TC-062 |
| 2026-10-23 網頁終端機「是中欄有個可以切換主視窗跟終端機的按鈕…」 | TC-031（PRODUCT.md 改成 later）、TC-032（不宣告已核可）、TC-042（DESIGN.md 原話 19 逐字未動）、TC-060 |
| 2026-10-30「介面還是不好，AWS, Azure介面就不能跟國網一樣，請你去參考Seqera platform的介面，不要都自己腦補」 | TC-035、TC-039 |
| 2026-11-03「我的意思是介面設計多去參考Seqera, galaxy等」 | TC-035、TC-040 |
| 2026-10-27「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」 | TC-038、TC-044 |

## 請你判斷的三件事

1. **每條是不是你要的？** 特別是 TC-008／TC-022：使用者看得到的變更不再等你的 yes，但「需求被修改或刪除」仍等你的 yes。這是裁決後的寫法（收緊，不是放寬），請確認「合併規則同意」涵蓋它（TC-062 要求 PR 描述點名這一句）。
2. **有沒有漏掉的出錯情況？** 本任務沒有執行時出錯情境；若你擔心某句舊規則殘留（例如別處還寫「只有維護者合併」），TC-061 的 `git grep` 會查。
3. **「不在範圍」對嗎？** 網頁終端機、自動續跑、OTP 的憲法修正案是另案（TC-032、TC-060）；PRODUCT.md 只寫成「之後，待它自己的修正案」。

## 覆蓋檢查

- 計畫「作法」第 0 到 8 點共 9 條，全部都有測試案例：是（0→TC-028、029；1→TC-005 到 TC-010；2→TC-011；3→TC-015 到 TC-027；4→TC-012 到 TC-014；5→TC-001、004；6→TC-030 到 TC-037；7→TC-038 到 TC-043、046；8→TC-002、003、050）
- 維護者原話 6 句，全部都有測試案例，且 TC 的輸入或預期結果用他的原字：是（見上表）
- 計畫「不做」5 條（不改原則與 Safety Net；不做開發模式啟動；不做網頁終端機／自動續跑／OTP 修正案；不改 CLAUDE.md、PRINCIPLES、README、ROADMAP；不改 .github、plugin.json、hooks），全部都有「不在範圍」測試案例：是（TC-056、TC-058、TC-060、TC-059、TC-059）
- 專長守則：計畫寫明本任務沒有專長守則（docs），無對應 TC。
- 憲法觸及：Development Workflow、Amendments、Governance 三處；原則、Invariants、Safety Net 沒有被改，由 TC-054、055、056 把關。

## 我（撰寫者）不確定的地方

- 派工前提（見上）：developer-agent 是否已在 `charter-v4-base` 補上 "modified or removed"？目前工作樹沒有。
- TC-031 不要求 "web terminal" 子句的具體版面（括號或分號），只要求它與 roles、Data Explorer、Dashboard 同處 later 清單；若你要固定成某種寫法，請說。
- TC-049（新測試登進 run_all）的做法取決於 `run_all.sh` 是用名單還是自動找檔；若名單在 `.github/` 內，executor 須停下來問，不得改。

## 核可紀錄

（尚無；維護者尚未親自核可，目前為 verifier 確認。）
