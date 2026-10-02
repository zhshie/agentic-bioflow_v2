# 測試案例總覽：新電腦、第二位成員也要先用公開資料驗證

狀態：已核可（2026-10-02，maintainer；先行實作後補核可）

<!--
Normally the line above is the approval gate and reads
    狀態：已核可（YYYY-MM-DD，maintainer）
only after the maintainer approves. This feature was built ahead of that on his
explicit instruction to finish all of batch C before reporting; the PR must not
merge until he approves these test cases.
-->

**規格**：`specs/004-onboarding-proof/spec.md`　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 沒證明過的電腦拿不到指令清單 | 3 | 10 | 0 | 13 |
| US2 — setup 的說明照新規則走 | 3 | 0 | 0 | 3 |
| 憲法與安全網 | 1 | 0 | 1 | 2 |
| **合計** | 7 | 10 | 1 | 18 |

自動驗證 18 條、手動驗證 0 條；真叢集上的實測放進手動驗收清單。

## 請你判斷的三件事

1. **每條是不是你要的？** 特別是 TC-002：你現在用的這台筆電也沒有證明紀錄，下次跑 setup 會被要求補跑一次 `nf-core/demo`。
2. **有沒有漏掉的出錯情況？**
3. **「不在範圍」對嗎？** launch 本身不擋沒證明的電腦，只在 setup 擋。

## 覆蓋檢查

- 規格裡的需求（FR）共 7 條，全部都有測試案例：是
- 規格裡的驗收情境共 10 條（US1 7＋US2 3），全部都有測試案例：是
- 規格裡「不在範圍」共 3 條：第 1 條有 TC-016；第 2 條（環境改變後舊證明失效）、第 3 條（自動送證明 run）是範圍說明，本次不改，無法測試。

## 我（撰寫者）不確定的地方

1. **證明只認 `nf-core/demo`，不認 `nextflow-io/hello`**。hello 只證明能送 job；demo 才證明容器、參考資料、Platform 讀回結果都通（setup.md 第 8 步自己的說法）。
2. **送出者比對用設定裡的 `seqera_user`**。如果設定裡沒有這個值，就不比對送出者。

## 驗收後的改動

1. **TC-017、TC-018（新增）**：獨立驗收發現，舊的 run 或別台電腦已用過的 run 都能被記成這台的證明。現在要求 run 是 7 天內送的，而且沒被別台用過。
2. **不改、另開 issue**：電腦的身分是「主機名稱＋系統類型」（T30 就有的設計）。兩台主機名稱一樣時會共用證明，這次不動。

## 核可紀錄

- 2026-10-02 維護者：「merge #50 #51 處理#48, #49」——以 merge 指示核可本測試案例與驗收後新增的 TC-017、TC-018；機器身分問題另案 #49 處理。
