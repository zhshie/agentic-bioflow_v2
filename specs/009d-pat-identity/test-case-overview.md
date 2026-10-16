# 測試案例總覽：009d 個人存取權杖（PAT）與使用者身分，`mcp --http` 必須帶權杖

狀態：合約已確認（2026-10-16，verifier）

<!--
Gate before code (constitution 2.1.0). Plan has no blocking finding; every sentence of the maintainer's
three-sentence promise is covered by TCs that use his words. Non-blocking plan notes are in the verifier report.
-->

**規格**：無 `spec.md`（依維護者指示，一律以 `specs/009d-pat-identity/plan.md` 為準；plan 的「給維護者」三句是他看得懂的承諾）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 在終端機建立使用者與發權杖（只顯示一次） | 7 | 2 | 2 | 11 |
| US2 — `mcp --http` 必須帶權杖，stdio 不變 | 5 | 9 | 0 | 14 |
| US3 — 權杖不開別的門，別種權杖也不開 MCP | 2 | 4 | 0 | 6 |
| US4 — 身分只被記錄，不是新的確認方式 | 8 | 4 | 0 | 12 |
| US5 — 舊檔相容、既有測試不變、文件 | 7 | 0 | 0 | 7 |
| US6 — 這一步不做的事 | 0 | 0 | 8 | 8 |
| 憲法與安全網 | 5 | 1 | 0 | 6 |
| **合計** | 34 | 20 | 10 | 64 |

自動驗證 62 條、手動驗證 2 條（TC-P46、TC-P58：由驗收者用 `git diff v3...HEAD` 比對，不需要你操作）。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看三句：「`mcp --http` 現在必須帶 `Authorization: Bearer <PAT>`，否則 401；stdio（本機）不變、不用權杖」（US2）、「權杖只在終端機建立與撤銷，只顯示一次」（US1）、「送出與取消仍然只能在終端機按 y；身分只是被記錄下來，不是新的確認方式」（US4）。
2. **有沒有漏掉的出錯情況？** 例如：權杖被撤銷、使用者被停用、拿錯種類的權杖、不帶權杖。
3. **「不在範圍」對嗎？** 這次不做 OAuth、公開網址／TLS、角色權限（010）、每人算力限制、權杖到期／輪替、網頁登入。

## 覆蓋檢查

- 規格裡的需求（FR）：沒有 spec.md；以 plan 的 7 條設計決定（Design 1 到 7）與 7 個變更步驟代替，全部都有測試案例：是。
- plan「給維護者」三句（維護者的承諾）全部都有直接使用其用語的測試案例：是（第 1 句：TC-P01、P03、P06、P07；第 2 句：TC-P12 到 P21；第 3 句：TC-P34 到 P38、P57）。
- plan「Not in this PR」共 8 條（OAuth／探索資料；公開網址與 TLS；角色／PI／實驗室權限；每人算力限制；權杖到期輪替；網頁登入；新的確認方式；PAT 或 user 工具／不得改動 TC-010、tc024、TC-061、LAUNCH_ALLOW、hooks、憲法、`.github/`），全部都有「不在範圍」測試案例：是（TC-P09、P10、P51 到 P58）。
- plan「Pinned guards」九項皆有對應 TC：是（tc024、tc025、TC-010/TC-061、009b 規則、tc040、tc070、pyproject、credentials 腳本、test_cli/test_station_envs 見 TC-P42、P43、P46 到 P48、C02、C05）。

## 我（撰寫者）不確定的地方

1. `pat new --label` 的標籤要存在哪？plan 只說 tokens 加 `user_id`。（不影響檢查內容：TC-P04 只驗標籤在 `pat list` 看得到。）
2. 沒有「停用使用者」的指令，是這一步刻意不做嗎？（TC-P17 靠直接改資料庫來製造停用。）
3. 重複姓名的 `user add`、不存在使用者的 `pat new`，plan 沒說要怎麼回應；TC 只驗「不會有兩個同名使用者」。需要更明確的話，請回到 plan 補。
4. 確認紀錄上記的是使用者姓名還是 id？TC 接受兩者其一，只要能辨認出是誰。

## 核可紀錄

（無；本次由 verifier 確認合約，維護者未另行核可。）
