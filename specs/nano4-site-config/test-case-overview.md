# 測試案例總覽：nano4 站台設定檔、CE 範本與三種費率（nano4-site-config）

狀態：合約已確認（2026-10-23，verifier）

<!--
Source note: no spec.md. Every case comes from specs/nano4-site-config/plan.md (目標, 維護者原話, 作法, 失敗先行測試, 完成標準, 不做, and the 裁決 section of 2026-10-22, which overrides the older wording of 作法 where they differ). IDs carry the prefix N4- to avoid colliding with TC-001 ... TC-C05 in platform/tests/test_estimate_su.py.
-->

**規格**：`specs/nano4-site-config/plan.md`（沒有 spec.md）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 在 nano4 啟動前估 SU 與三種費率 | 7 | 1 | 0 | 8 |
| US2 — 分區萬用字元規則，且不影響 T3 | 6 | 1 | 0 | 7 |
| US3 — nano4 的 CE 範本 | 6 | 0 | 0 | 6 |
| US4 — 退路 config `nchc-nano4.config` | 5 | 0 | 1 | 6 |
| US5 — 出處與核對步驟有留下 | 3 | 0 | 0 | 3 |
| US6 — 不在範圍 | 0 | 0 | 4 | 4 |
| 憲法與安全網 | 4 | 1 | 0 | 5 |
| **合計** | 31 | 3 | 5 | 39 |

自動驗證 34 條、手動驗證 5 條（N4-15、N4-30、N4-31、N4-33、N4-34：只能看 `git diff` 或 `ledger.md`／`docs/TESTING.md` 的內容，沒有可寫的自動測試）。

## 請你判斷的三件事

1. **每條是不是你要的？** 最重要的數字：1 核心跑 10 小時，ngs 分區＝10 SU、NT$ 1.0／2.0／3.7（國科會／學術／企業）；big-mem 分區＝70 SU、NT$ 7.0／14.0／25.9（N4-01、N4-03）。N4-05 另外要求 nano4 回答裡舊有的 `twd_nstc`、`twd_academic` 也要等於新的 `twd` 對應值（見下面「不確定」第 1 點）。
2. **有沒有漏掉的出錯情況？** 想像成員會怎麼用錯它：分區名對不上（N4-08）、T3 被新規則誤傷（N4-11）、看別人的 run（N4-C5）、改壞既有測試（N4-15）、自裝 Nextflow 退路時 CE 範本被驗證擋下（N4-21）。
3. **「不在範圍」對嗎？** 這次不做：不改 T3 任何設定（N4-32、N4-33）、不改站台程式也不實際建立 CE（N4-34）、不改 `actions.estimate_su` 的簽名（N4-35）、不抄 Taiwania-3 的 box 表（N4-28）。

## 覆蓋檢查

- 計畫的需求共 9 組（SU 估算與三種費率、`load_rates`／site 覆寫、分區萬用字元、CE 範本、`nchc-nano4.config`、`su_rates.json` 新增 nano4、既有 T3 案例保留、完成標準、手動核對與出處），全部都有測試案例：是
- 計畫「失敗先行測試」4 條：`tc025b`→N4-01、N4-02；`tc025c`→N4-03；既有 T3 案例保留→N4-14、N4-15；CE JSON 通過 `_check_slurm`→N4-16。全部都有測試案例：是
- 裁決 1 至 8，全部都有測試案例：是（1：前置條件，N4-16 需含三鍵的 base 才會通過；2：N4-19；3：N4-20、N4-22；4：N4-03、N4-04、N4-07；5：N4-02、N4-09 至 N4-11；6：N4-29；7：N4-05、N4-06、N4-12、N4-35；8：N4-30）
- 維護者逐字原話共 3 句，全部都有用他的話當輸入的測試案例：是（第 1 句→N4-01、N4-03、N4-07；第 2 句→N4-17、N4-01；第 3 句→N4-21、N4-22）
- 計畫「不做」共 3 項（不改站台程式、不實際建立 CE、不改 T3 設定），全部都有「不在範圍」測試案例：是（N4-32 至 N4-34；另加 N4-28、N4-35）
- 後端專長守則：對等性→N4-35；跨使用者→N4-C5；確認管道→本任務沒有新增寫入動作，不適用；錯誤訊息與密鑰→N4-08、N4-C4；migration→N4-31、N4-C3

## 我（撰寫者）不確定的地方

1. nano4 回答裡舊有的 `twd_nstc`、`twd_academic` 該是多少？計畫只說「仍回」，沒說值。我依「sites.<name> 蓋過頂層預設」寫成「等於 `twd.nstc`、`twd.academic`」（nano4 的 10 SU 就是 1.0／2.0，而不是用 T3 的 0.08 算出 0.8）。這樣理解對嗎？
2. `nchc-nano4.config` 是 Nextflow 語法，這裡沒辦法執行 Nextflow，N4-23 至 N4-28 只能用文字比對檢查；語法本身對不對，要等 nano4 實機啟動才知道。這樣可以接受嗎？
3. 計畫「作法」段仍寫著舊的做法（environment 用字串、CE JSON 放 `_comment`、鍵名 `twd_per_core_hour`），已被「裁決」取代。我一律照裁決出題；要不要請 developer-agent 順手把「作法」段改乾淨，避免執行者讀混？
4. 分區 `ngs*` 的預設 `process.queue` 值（N4-26）計畫只說「以 ngs 分區為準」，沒指定是哪一個，所以 TC 只要求「ngs 開頭、可被 `SLURM_PARTITION` 覆寫」。

## 核可紀錄

（無；本合約由 verifier 確認，維護者尚未以 `已核可` 核可。）
