# 測試案例總覽：nano4 計算環境範本收進 16S 實跑的四個修正（nano4-ce-fixes）

狀態：合約已確認（2026-10-24，verifier）

<!--
Source note: no spec.md. Every case comes from specs/nano4-ce-fixes/plan.md (目標, 維護者原話 [the 2026-10-24 run record, not literal words], 作法, 失敗先行測試, 完成標準, 不做, 裁決, 裁決二, 專長守則 backend). No expected behaviour was invented beyond the plan.
-->

**規格**：`specs/nano4-ce-fixes/plan.md`（沒有 spec.md）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — CE 範本（N4F-01～12） | 11 | 1 | 0 | 12 |
| US2 — 文件（N4F-13～32） | 20 | 0 | 0 | 20 |
| US3 — 只改該改的（N4F-33～46） | 8 | 0 | 6 | 14 |
| 憲法與安全網（N4F-47～48） | 2 | 0 | 0 | 2 |
| **合計** | 41 | 1 | 6 | 48 |

自動驗證 23 條、手動驗證 25 條。

手動的 25 條都是「閱卷人讀 `docs/SETTINGS.md`、`docs/PITFALLS.md`、ledger 或 git diff」。計畫只規定兩條自動測試做子字串檢查，文件內容的其餘細節（符號連結步驟、每個別名都放一份、掃描指令、為何拿掉 `NFCORE_SITE_REFERENCES`、PITFALLS 症狀）沒有自動檢查，閱卷時要引用行號。

## 請你判斷的三件事

1. **每條是不是你要的？** 四個修正各自對應的預期結果，有沒有跟你想的不一樣。尤其是：CE 範本預設就帶 `NXF_PLUGINS_DIR`（自裝 Nextflow 時改成覆寫），以及 `ref_taxonomy_storage` 只寫文件、不進 CE。
2. **有沒有漏掉的出錯情況？** 例如有人照舊範本建的 CE 要不要提示換掉：計畫沒有要求，所以沒有 TC。
3. **「不在範圍」對嗎？** 不改程式、不新增 CE 鍵、不做 preflight、不實際建 CE 或連站台、不動退路 config 與費率。

## 覆蓋檢查

- 計畫「維護者原話」的四個事實共 4 條，全部都有測試案例：是（事實 1＝N4F-03、13～15；事實 2＝N4F-01、02、21；事實 3＝N4F-20、43；事實 4＝N4F-04、16～19、25）
- 計畫「作法」1～4、「失敗先行測試」兩條新測試與點名的五項既有斷言、「完成標準」五項，全部都有測試案例：是
- 計畫「不做」共 6 條（不碰的檔、閘門檔、不改驗證與不新增 CE 鍵、不實際建 CE 或連站台、`ref_taxonomy_storage` 不進 CE、退路 config 與費率與 T3），全部都有「不在範圍」測試案例：是（N4F-39～44）
- 專長守則（backend）：資料結構變動要有 migration 或明寫不需要，已有 N4F-45；密鑰 N4F-48；對等性、跨使用者、確認管道、錯誤訊息四類在本任務不適用（沒有動作層、路由、store 的改動），已在「憲法與安全網」說明並由 N4F-39、40 守住

## 我（撰寫者）不確定的地方

1. 計畫的完成標準說「非 SETTINGS 文件沒有真實使用者名」，但 `docs/SITE_ADAPTER.md` 本來就有 `/work/u9613010`，而且 `tests/docs_nano4_keys.sh` 要求它留著。我照「本次不新增」出題（N4F-31）。你是否同意？
2. `docs/TESTING.md`「nano4 site config」一節第 3 項寫「既有測試只能新增行」，但本任務依計畫要改三處既有斷言。我讓閱卷人改依計畫點名的三處核對（N4F-36），不以該項原文為準。之後要不要另開任務修正那一項？
3. 新測試的「全文不含真實使用者名」，我解讀為不含 `u9613010` 與 `/work/envstack`。是否正確？

## 核可紀錄

<!-- Date, the maintainer's own words, and which TCs changed because of his review. -->

（尚無；本文件由 verifier 在 CONTRACT 模式出題，維護者未逐條核可。）
