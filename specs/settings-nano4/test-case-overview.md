# 測試案例總覽：settings-nano4（文件：nano4 設定鍵、站台對照表、兩條踩坑、公開網址一節）

狀態：合約已確認（2026-10-22，verifier）

**規格**：`specs/settings-nano4/plan.md`（本任務為文件任務，沒有 spec.md，以計畫為準）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 使用者照 SETTINGS.md 設成 nano4 模式 | 10 | 1 | 0 | 11 |
| US2 — SITE_ADAPTER.md 的 nano4 對照 | 8 | 1 | 0 | 9 |
| US3 — PITFALLS.md 兩條踩坑 | 4 | 1 | 0 | 5 |
| US4 — OPERATIONS.md「公開網址」一節 | 4 | 3 | 0 | 7 |
| US5 — 機械檢查，先紅後綠 | 5 | 0 | 0 | 5 |
| 範圍邊界（計畫「不做」） | 0 | 0 | 4 | 4 |
| 憲法與安全網 | 1 | 1 | 0 | 2 |
| **合計** | 28 | 7 | 4 | 43 |

自動驗證 41 條、手動驗證 2 條（TC-010、TC-042）。

## 請你判斷的三件事

1. **每條是不是你要的？** 特別看 TC-010：你說「試用成功＝同事不問我就能跑完一次 16S」，本任務只能證明文件齊全、例子前後一致，真正讓同事跑一次要等 M1-07 和真機。
2. **有沒有漏掉的出錯情況？** 想像同事只看文件設定 nano4：設了 `way_back: direct` 卻沒設 `platform_public_url` 會怎樣，計畫只寫「需要」，沒寫程式遇到會怎麼反應，所以沒有 TC，也沒有編造。
3. **「不在範圍」對嗎？** `README.md`、ADR、ROADMAP、`docs/TESTING.md`、任何程式與設定檔都不動（TC-038 到 TC-041）。

## 覆蓋檢查

- 計畫的作法條目共 13 條（`way_back`、`platform_public_url`、`site_profile`、CE 三個鍵、站台對照表一列、踩坑兩條、公開網址一節的三個內容點、各項格式要求），全部都有測試案例：是
- 維護者原話共 3 句（白話摘要第 3 點、裁示 11、裁示 17），全部都有測試案例：是（第 3 點的「實機驗收清單」依計畫屬 M1-07，以 TC-039 確認沒有偷做；裁示 17 為 TC-010，只能驗到文件層）
- 計畫「失敗先行測試」的各項（SETTINGS 六個鍵、SITE_ADAPTER 的 nano4 列與 `NXF_SINGULARITY_LIBRARYDIR`、PITFALLS 兩條標題）全部都有測試案例：是（TC-033、TC-034、TC-035）
- 計畫「不做」共 2 條（README／ADR／ROADMAP；TESTING.md），另加範圍與環境事實 2 條（只動四份文件、不連真機），全部都有「不在範圍」測試案例：是
- 計畫完成標準（鍵名一字不差、新測試綠、全套綠）：是（TC-009、TC-036、TC-037）
- 專長守則：計畫明寫本任務無專長守則，所以沒有對應 TC。

## 我（撰寫者）不確定的地方

1. 公開網址那一節要放在哪一層標題？現有 `tests/operations_doc_test.sh` 規定恰好 6 個 `##` 標題，所以我把它鎖成「只能是 `###`、且該測試不得修改」（TC-030、TC-031）。這樣可以嗎？
2. SITE_ADAPTER 現有的六個契約是 Resource、Egress、Reports、Storage、Diagnosis、Reach，但計畫的 nano4 一列寫的是 Resource、Egress、Reports、Storage、Reach、Identity（沒有 Diagnosis，多了現有文件沒有的 Identity）。我只驗計畫寫明的六項事實，nano4 的 Diagnosis 沒寫就沒測。要補嗎？
3. 計畫要求鍵名與 L1／L2 計畫「一字不差」，但那兩份計畫不在這個 worktree，我只能對本計畫列的六個拼法（TC-009）；跨計畫對照要等合併時做。
4. 文件是英文，計畫的標題和用語是中文，我的判準兩種語言都接受。要指定語言嗎？
5. PITFALLS 兩條的出處（環境事實）不在這個 worktree，驗收者可能查不到，到時會列「待確認」而不是通過（TC-042）。

## 核可紀錄

（無；維護者尚未表示意見。）
