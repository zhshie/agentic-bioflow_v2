# 測試案例總覽：續跑可改參數與資源（c 片：說明文字、技能、ADR、對照表）

狀態：合約已確認（2026-10-24，verifier）

**規格**：`specs/resume-edit-params-c/plan.md`（本任務沒有 spec.md，計畫即來源；以「裁決二」為準，它取代作法 B(1)、失敗先行測試第 3 條與裁決 4 中「被拒絕、用 get_run 查」的說法）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — MCP 開場句改成新說法 | 7 | 0 | 1 | 8 |
| US2 — 兩份技能與已知後果的說法 | 13 | 1 | 1 | 15 |
| US3 — ADR 0009、對照表、CHANGELOG | 10 | 0 | 0 | 10 |
| US4 — 範圍與完成標準 | 4 | 0 | 3 | 7 |
| 憲法與安全網 | 2 | 0 | 1 | 3 |
| **合計** | 36 | 1 | 5 | 43 |

自動驗證 31 條、手動驗證 12 條（手動＝閱卷者讀 git diff 核對，編號：TC-006、008、021、024、039、040、041、042、043、044、045、052）。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看 TC-001（新開場句逐字）、TC-030（ADR 註記逐字）、TC-032（對照表 Resume 列逐字）、TC-020（「同一份改動再呼叫＝同一個工作編號；不同改動才被拒絕」）。這些字句全部取自計畫，沒有另外發明。
2. **有沒有漏掉的出錯情況？** 本片只改文字，唯一的「出錯面」是文字說得比實際行為多：TC-011（六個鍵＝實際白名單）、TC-012（三個旗標真的存在）、TC-022（不暗示組合流程與 Google Batch 可改參數續跑）。
3. **「不在範圍」對嗎？** 不動 routing 表、不新增技能或 MCP 工具、不改 `launch` 技能、不改 `PLATFORM.md`／`TESTING.md`（d 片）、不改任何程式邏輯。

## 覆蓋檢查

- 計畫「作法」與「範圍」的要求共 3 組（A 開場句、B 兩份技能、C ADR／對照表／CHANGELOG）加完成標準，全部都有測試案例：是
- 計畫的失敗先行測試共 7 個具名測試，全部對應到 TC：開場句→TC-001～003；兩份技能→TC-010～016；runs 不再說不能改→TC-018～020；ADR→TC-030～031；對照表→TC-032～034；CHANGELOG→TC-035～038；`test_tc107` 改後綠→TC-005：是
- 維護者原話逐條對應：「跟Seqera一樣、不要自己定義」→ TC-032（備註照 Seqera 的 Resume）、TC-015；「所有 PR 自己合併」→ 屬流程，不產生程式碼 TC；「任何寫入都要人說 yes」→ TC-050；「續跑只在同一個資料夾、原本四個檔不動」→ TC-051；「改樣本／管線／版本／環境＝新分析；改一部分參數與資源＝仍是同一個分析的下一次嘗試」→ TC-015、TC-030：是
- 計畫「必須仍綠」清單（`test_launch_docs.py`、`test_station_docs.py`、`test_gcb_ce.py:865`、`test_gcb_launch.py:1160`、`platform_direction_docs_test.sh`、`skill_runs_uses_actions_test.sh`、`test_resume_entrypoints.py:60-66/:156`、`test_guidance.py`、全套與 CI）：TC-007、023、034、046：是
- 計畫「不做」共 5 條（不改程式邏輯、不改 PLATFORM／TESTING、不改 ADR 其他段、不改 launch 技能、不新增 skill／工具／不動 routing 表），全部都有「不在範圍」或對應的不變 TC：是（TC-008、024、031、041、042）
- 專長守則（backend）：本片不新增任何動作、路由、紀錄或資料結構，對等性、跨使用者、確認管道、錯誤訊息、migration 這幾類 TC 沒有新的東西可測。確認管道由 TC-050 守住「文字不得弱化」；migration 由 TC-038 要求 CHANGELOG 寫明「不需要 migration」。

## 我（撰寫者）不確定的地方

1. TC-006、008、021、024、039、040～045、052 是「閱卷者讀 git diff 核對」的手動項，但 `docs/TESTING.md` 沒有這個任務的對應步驟（該檔在 d 片才改，本片不准動）。閱卷時可否直接以 `git diff <base>...HEAD` 與 ledger 的貼證當手動證據？（我的做法是可以，因為 `docs/TESTING.md` 既有條目也是這種 git diff 範圍檢查。）
2. 「PR 說明要寫明 reverse 009e／ADR 0009 的哪一句、新舊句對照、不需要 migration」是完成標準之一，但 PR 文字不在檔案裡，閱卷者無法從檔案確認，所以沒有 TC。需要有人在合併前看一眼 PR 說明。
3. `tests/skill_runs_uses_actions_test.sh` 的 TC-023 是逐行用關鍵字檢查，對 `runs` 技能新增的句子很敏感（句子含 resume／relaunch 加上 memory 或 param 等字，就必須同行帶有 cannot／not／never／same／new `launch` 之類限定語）。這不是計畫的缺陷，但執行者寫 `runs` 的新句時要留意；已由 TC-023 把關。

## 核可紀錄

（無；本合約由 verifier 確認，維護者尚未以自己的話核可。）
