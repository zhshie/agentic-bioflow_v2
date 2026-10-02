# 測試案例總覽：「這台電腦」用自己的隨機 ID 認

狀態：草稿（待維護者核可）

<!--
The line above is the approval gate. It becomes
    狀態：已核可（YYYY-MM-DD，maintainer）
only after the maintainer says so in the conversation, and the words he used are
quoted under "核可紀錄" below. /speckit-plan does not run while it says 草稿.
-->

**規格**：`specs/006-machine-identity/spec.md`　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 更新、改名不會讓設定消失 | 3 | 0 | 0 | 3 |
| US2 — 舊版設定自動接上 | 4 | 2 | 0 | 6 |
| US3 — 兩個環境不再共用身分 | 1 | 2 | 0 | 3 |
| 文件與全套 | 2 | 0 | 0 | 2 |
| **合計** | 10 | 4 | 0 | 14 |

全部自動驗證。

## 請你判斷的三件事

1. **ID 長這樣可以嗎？** `laptop-7f3a91c2`：主機名稱加 8 碼隨機字元，讓人看得出是哪台。
2. **舊設定自動接上（TC-004～007）**：這樣你筆電現有的設定不用重做。Git Bash 的版本號不同也接得上。
3. **不在範圍**：整包家目錄被複製到新電腦時，仍會共用身分。這次不處理，004 的 7 天規則已經擋掉大部分的風險。

## 覆蓋檢查

- 需求 FR-001～006 都有測試案例：是
- 驗收情境共 10 條，全部有測試案例：是
- 不在範圍 2 條，都是範圍說明，本次不改，無法測試。

## 核可紀錄

（待補）
