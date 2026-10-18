# 測試案例總覽：estimate_su（用 run 的 trace 算用掉多少國網 SU）

狀態：合約已確認（2026-10-18，verifier）

<!--
Source note: this task has no spec.md and no verbatim maintainer examples; every case comes from specs/estimate-su/plan.md (Build and Tests sections), which quotes issue #119. The test inputs (4 cores for 2 hours, factor 1.5, and so on) were chosen by the verifier as the "hand-made trace" the plan asks for.
-->

**規格**：`specs/estimate-su/plan.md`（沒有 spec.md）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 用公式從 trace 算出 SU 與金額 | 4 | 0 | 0 | 4 |
| US2 — 缺資料就說不知道，絕不猜 | 0 | 9 | 0 | 9 |
| US3 — action estimate_su：只看得到自己的 run | 3 | 3 | 0 | 6 |
| US4 — 某使用者某月的總計，讀的當下現算 | 3 | 0 | 0 | 3 |
| US5 — 費率檔與工作紀錄 | 6 | 0 | 0 | 6 |
| US6 — 範圍邊界 | 0 | 0 | 5 | 5 |
| 憲法與安全網 | 7 | 0 | 0 | 7 |
| **合計** | 23 | 12 | 5 | 40 |

自動驗證 38 條、手動驗證 2 條（TC-031、TC-032：本任務沒有動這些檔，只能看 git diff）。

## 請你判斷的三件事

1. **每條是不是你要的？** 特別是 TC-014：交付後 `estimate_su` 對任何真實 run 都回「未知（—）」，因為接收器沒存每個 task 的 cpus／realtime／分區，而國網各分區的 SU 係數 repo 裡也查不到（所以 TC-024 要求全部是 null）。只有手做的資料和測試注入的資料算得出數字。
2. **有沒有漏掉的出錯情況？** 想像成員會怎麼用錯它：看別人的 run（TC-017、TC-018）、費率檔被刪（TC-012）、部分 task 缺資料（TC-007 到 TC-010）。
3. **「不在範圍」對嗎？** 這次不做：MCP 工具、網頁顯示、改 receiver、CHANGELOG、PLATFORM.md、雲端費用（TC-029 到 TC-033）。

## 覆蓋檢查

- 計畫裡的需求（Build 1–4）共 4 條，全部都有測試案例：是
- 計畫 Tests 段列出的 5 項（公式、缺係數、別人的 run、月合計、不新增表欄）全部都有測試案例：是（TC-001/002、TC-005、TC-017、TC-020/021、TC-C02）
- 計畫「Out of scope」共 4 項（receiver、MCP／網頁、CHANGELOG.md、docs/PLATFORM.md），全部都有「不在範圍」測試案例：是（TC-029 到 TC-032；另加雲端費用 TC-033）
- 維護者逐字例句：計畫與 issue 引文沒有這類例句，所以沒有 TC 引用他的原話；已在上方註明。

## 我（撰寫者）不確定的地方

1. 計畫沒寫 realtime 的單位。TC-004 照 Nextflow 實際記錄（毫秒，fixtures 如 65005）寫；若你其實想用小時，要在實作前改計畫，TC-004 隨之改。
2. 月合計遇到「該月有 run 的 SU 是未知」時，總數是 None 還是只加已知的？該月沒有 run 時是 0 還是 None？「某月」用開始還是結束時間、哪個時區？計畫都沒說，所以沒有 TC（TC-020 的資料刻意避開月初月底）。這是使用者會看到的數字，建議你拍板。
3. 計畫的簽名 `estimate_su(caller, run_name)`、`month_total(user, month)` 缺索引路徑；TC 不鎖簽名，只要求「別人的 run 與不存在的 run 同樣回『找不到』」。
4. TC-016 要求 action 真的接到公式（用手做資料取代「讀 run 的 task 紀錄」那一步），避免只定義不連線的空殼；這需要程式留一個可替換的讀取點，由執行者決定怎麼做。
5. TC-031、TC-032 只能靠讀 git diff 驗證，`docs/TESTING.md` 沒有對應的手動步驟；驗收者需要照 diff 確認，或由你同意補一個步驟。
6. 費率檔在 `configs/sites/`，不在 platform 套件裡；安裝後 su.py 怎麼找到它，計畫沒說。TC-012 只要求「找不到就明說未知」。
7. TC-025 把「per partition」解讀為列出 nchc.config 的七個佇列，每個 factor 為 null；若你希望只列已知係數的分區，需改此條。

## 核可紀錄

（無；本合約由 verifier 確認，維護者尚未核可。）
