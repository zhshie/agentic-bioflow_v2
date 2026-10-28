# 測試案例總覽：時鐘測試項目拆成兩個（每項 ≤180 秒）＋更正 suite-speed 帳本一句

狀態：合約已確認（2026-10-28，verifier）

<!--
The line above is the gate before code (constitution 2.1.0). The independent reviewer
(`verifier`, CONTRACT mode) starts it at "草稿" and changes it to
    狀態：合約已確認（YYYY-MM-DD，verifier）
only when the plan has no blocking finding and every example of the maintainer's is
covered. If the maintainer approves the cases himself, it may instead read
    狀態：已核可（YYYY-MM-DD，maintainer）
with his words quoted under "核可紀錄". Implementation does not start while it says 草稿.
-->

**規格**：`specs/suite-clock-split/plan.md`（A 級任務，無 spec.md）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 拆分前後，跑的測試完全一樣 | 8 | 0 | 0 | 8 |
| US2 — 時鐘分成兩個項目，且 run_all.sh 認得新項目 | 8 | 3 | 0 | 11 |
| US3 — 每個項目實測都 ≤ 180 秒 | 3 | 1 | 0 | 4 |
| US4 — 兩處文字更正與範圍乾淨 | 3 | 0 | 0 | 3 |
| 不在範圍（計畫「不做」與「不准動」） | 0 | 0 | 6 | 6 |
| 憲法與安全網 | 1 | 0 | 0 | 1 |
| **合計** | 23 | 4 | 6 | 33 |

自動驗證 16 條、手動驗證 17 條。

（自動：SC-01、02、03、04、05、06、07、08、09、11、15、17、18、19、20、29。手動：SC-10、12、13、14、16、21、22、23、24、25、26、27、28、30、31、32、33——手動的意思是閱卷者照該列寫的指令在 WSL 重跑，或讀 diff／ledger 核對。）

## 請你判斷的三件事

1. **每條是不是你要的？** 有沒有哪條的「預期結果」跟你想的不一樣。重點看 SC-01（拆完之後跑的測試一個都沒少、沒重複）與 SC-21／SC-22（每個項目 ≤ 180 秒）。
2. **有沒有漏掉的出錯情況？** 想像別的車道同時在跑完整套件、機器負載高的時候，秒數會漂移；計畫的規則是負載 ≤ 3 才把 180 秒當硬條件，負載 > 3 只記錄、只要求沒有 TIMEOUT。
3. **「不在範圍」對嗎？** 這次不碰 CI 設定（連註解也不碰，依裁決 2）、不碰憲法的過期字面「四個入口」、不碰 web 相關檔。過期的 CI 註解會留到另案。

## 覆蓋檢查

- 規格裡的需求共 8 條（完成標準 1～8），全部都有測試案例：是（1→SC-21、SC-23；2→SC-22；3→SC-01、SC-02、SC-15、SC-26；4→SC-12；5→SC-13（依裁決 2 改判「.github 零變動」）；6→SC-11、SC-23 與各 SC；7→SC-25、SC-30；8→SC-24）
- 規格裡的驗收情境（計畫 SC-01…SC-09、SC-12…SC-14 共 12 條）全部都有測試案例：是（SC-10、SC-11 計畫漏編，已補）
- 維護者原話：計畫註明「A 級，無維護者原話」，來源是 suite-speed verifier 報告 needs-human 第 2、4、5 點；三點分別對到 SC-21／SC-22、SC-12、SC-13（依裁決 2）：是
- 規格裡「不在範圍」（「不做」7 條＋「不准動」＋裁決 2、3）共 7 組，全部都有「不在範圍」測試案例：是（SC-09、13、30、31、32、33；憲法字面不改併入 SC-30）

## 我（撰寫者）不確定的地方

- 計畫本文有四處仍寫「CI 註解只改註解」，與裁決 2（`.github/` 必須零變動）矛盾；我照裁決寫（SC-13），請 developer-agent 之後把計畫本文同步。
- 「手動」類（共 17 條）的步驟沒有放進 `docs/TESTING.md`；計畫只說記進 `specs/suite-clock-split/ledger.md` 並由閱卷者重跑。每列已寫明具體指令與判準，閱卷時以此為準。可以接受嗎？
- SC-21：負載 > 3 時秒數超過 180 秒，是否仍算通過？我照計畫寫成「只記錄、要求沒有 TIMEOUT 行」，並在閱卷報告「需要人看的事」提醒你。

## 核可紀錄

<!-- Date, the maintainer's own words, and which TCs changed because of his review. -->

（尚未由維護者核可；上方狀態為 verifier 確認合約，非維護者核可。）
