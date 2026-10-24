# 測試案例總覽：送出 tw launch 前，當下重驗「輸出讀取 agent（Tower Agent）還活著」（issue #7）

狀態：合約已確認（2026-10-24，verifier）

**規格**：`specs/launch-reader-dies/plan.md`（本任務無獨立 spec.md，以 plan 與其中逐字引用的 issue #7 為準）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 重驗腳本抓得到兩個常駐程式倒了 | 6 | 11 | 5 | 22 |
| US2 — 技能步驟 8 送出前重驗、失敗停手 | 10 | 2 | 3 | 15 |
| US3 — 留下紀錄、只動准許的地方 | 5 | 0 | 9 | 14 |
| 憲法與安全網 | 2 | 0 | 0 | 2 |
| **合計** | 23 | 13 | 17 | 53 |

自動驗證 30 條、手動驗證 23 條（手動＝閱卷者讀檔／看 diff，或真站台步驟記進 ledger，詳見下面第 1 題）。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看 issue #7 你的原話對到的幾條：TC-003／TC-004（agent 倒了就要報、並給出重啟指令）、TC-009／TC-010（同一份設定、兩次呼叫之間 agent 倒了，第二次要報）、TC-029（檢查放在你說「確認執行」之後、送出同一個動作之前）、TC-030（修好後送同一條指令、不必重新確認）。
2. **有沒有漏掉的出錯情況？** 目前只管「agent／egress 行程不在了」；「行程在但 Platform 看不到它」依計畫不在範圍（TC-018、TC-036）。
3. **「不在範圍」對嗎？** 不自動重啟（TC-017、TC-035）、不改閘門 hook（TC-042、TC-043）、不查 agent 為什麼會死（TC-041）、不同步到 main（TC-047）、不動 relaunch（TC-037）。

## 覆蓋檢查

- 計畫的測試表 T1–T9 共 9 條，全部都有測試案例：是（T1→TC-003/004/005；T2→TC-001/002；T3→TC-011/012；T4→TC-014/015；T5→TC-006/007；T6→TC-009/010；T7→TC-023/024/025/026；T8→TC-032/033；T9→TC-016）。
- 維護者原話（issue #7）逐句對應：「just-in-time check…same `agent_ctl.sh status`」→TC-001/003/004；「died sometime between the earlier preflight pass and the actual launch call」→TC-009/010；「Restarting it … fixed it immediately」→TC-024/030/021/022；「right before … the actual `tw launch`」→TC-023/026/029；「relying solely on the earlier `preflight.sh` pass」→TC-032/033/034。全部有案例：是。
- 計畫「作法」逐項（腳本四種 reach 行為、egress-host、步驟 7 預告、步驟 8 插入、第 60 行改寫、PITFALLS）：全部有案例：是（TC-008、TC-013、TC-031、TC-034、TC-038 至 TC-041 是 T 表沒列、由作法句子導出的案例）。
- 計畫「不做」共 6 條，全部都有「不在範圍」測試案例：是（不改 hooks→TC-042/043；不自動重啟→TC-017/035；不查 Platform 看不到→TC-018/036；不調查為何死→TC-041；不改 preflight／prepare_launch／不新增設定鍵→TC-045/046；不同步 main→TC-047）。另外「不准動」清單→TC-044/045/048/049；「不涵蓋 relaunch」→TC-037。
- 完成標準逐項：新測試與既有測試綠→TC-050/052/053；hooks 無改動→TC-042/043；只改範圍內檔案→TC-044/045；無真實 tw／ssh→TC-016/051；禁改檔→TC-048；手動驗收→TC-021/022。全部有案例：是。

## 我（撰寫者）不確定的地方

1. `docs/TESTING.md` 在計畫「不准動」清單內，但規則要求手動案例的步驟寫在那裡。我把 23 條手動案例改成「閱卷者讀檔／看 diff」或「記進 ledger」。可以接受嗎？（不影響要檢查什麼，只影響手動步驟放哪裡。）
2. 計畫作法 2 的步驟 8 範例句先寫「呼叫 `tw launch` 的同一個 Bash 回合之前，先跑 …launch_recheck.sh」，但 T7 要求 `launch_recheck.sh` 第一次出現要在該段第一個 `tw launch` 字樣**之前**。executor 照字面抄會讓 T7 變紅；以 T7（TC-026）為準，措辭由 executor 調整。這樣處理對嗎？
3. TC-008、TC-013、TC-017 至 TC-020 是計畫「作法」文字有寫、但 T 表沒列的行為，已要求 executor 在 `tests/launch_recheck_test.sh` 補上。需要的話可以降級為手動閱卷。

## 核可紀錄

（無；本合約由 verifier 確認，尚未經維護者逐條核可。）
