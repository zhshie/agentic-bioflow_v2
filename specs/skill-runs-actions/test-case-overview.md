# 測試案例總覽：skill-runs-actions（runs skill 改呼叫平台的 MCP 工具，不再用 tw）

狀態：合約已確認（2026-10-18，verifier）

**規格**：`specs/skill-runs-actions/plan.md`（此功能沒有獨立 spec.md；計畫即規格）　**明細**：`test-case.md`

## 一眼看完

| 區塊 | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| 1 查狀態改走平台工具（TC-001 至 TC-014） | 14 | 0 | 0 | 14 |
| 2 動作只請求、由人確認（TC-020 至 TC-024） | 3 | 2 | 0 | 5 |
| 3 沒有對應的步驟：明講、記帳（TC-030 至 TC-032） | 1 | 2 | 0 | 3 |
| 4 結構與既有測試不退步（TC-040 至 TC-047） | 8 | 0 | 0 | 8 |
| 5 淘汰舊測試的規矩（TC-050、TC-051） | 1 | 1 | 0 | 2 |
| 6 不在範圍（TC-060 至 TC-065） | 0 | 0 | 6 | 6 |
| 憲法與安全網（TC-070 至 TC-072） | 3 | 0 | 0 | 3 |
| **合計** | 30 | 5 | 6 | 41 |

自動驗證 40 條、手動驗證 1 條（TC-024，引用 `docs/TESTING.md` 既有的「Resume and relaunch (009e)」第 2 步）。

## 請你判斷的三件事

1. **每條是不是你要的？** 特別看 TC-001（skill 裡不能再有 `tw` 指令）、TC-020／TC-021（動作只請求、確認一定是人）、TC-030（還在呼叫 tw 的腳本要明講「v3 尚未提供」）。
2. **有沒有漏掉的出錯情況？** 例如 AI 對使用者說「我幫你確認了」、或 skill 說 `relaunch` 工具能改記憶體大小。這些在 TC-021、TC-023。
3. **「不在範圍」對嗎？** 其他 skill、platform/、hooks/、CHANGELOG.md、docs/PLATFORM.md、所有 scripts 都不動（TC-060 至 TC-065）。

## 覆蓋檢查

- 計畫的目標與規則共 5 組（Goal；Rule 1 只用 v3 存在的工具；Rule 2 沒有對應就明講並記帳；Rule 3 結構與語氣不變；Rule 4 淘汰舊測試的規矩），全部都有測試案例：是。
- 計畫「Tests」兩點全部都有測試案例：是（第 1 點：TC-001、TC-002、TC-003、TC-012、TC-014、TC-020；第 2 點：TC-046、TC-047）。
- 計畫的範例與句子：沒有維護者逐字範例，TC 全部取自計畫的目標、規則與 Tests 原文。
- 計畫「Out of scope」共 5 條（其他 skill、platform/、hooks/、CHANGELOG.md、docs/PLATFORM.md），加上 Rule 4 的「不改其他 script」共 6 條，全部都有「不在範圍」測試案例：是。
- 驗收時要在 main 與本分支各跑一次新測試（TC-014）：新測試對 main 必須失敗。

## 我（撰寫者）不確定的地方

1. **狀態字怎麼對應？** v3 的 `get_run` 只回 running、succeeded、failed、lost；沒有 SUBMITTED、CANCELLED（取消的 run 對 Nextflow 是 failed）。六個分支標題被 `tests/runs_report_format_test.sh` 釘住。計畫沒說這兩個分支在 v3 要怎麼接，所以我沒有為「對應方式」寫 TC。這需要 developer-agent 在實作前答覆，最好寫進 ledger。
2. **還在呼叫 tw 的腳本要算進來嗎？** `task_health.sh`、`tune_resources.sh`、`relaunch_with_override.sh`、`runs_board.sh`、`agent_ctl.sh` 內部都呼叫 tw，而計畫又不許改腳本。我把規則 2 套用在它們身上（TC-030）：要嘛換成平台工具，要嘛明講 v3 尚未提供並記進 ledger。若計畫只想管 SKILL.md 的字面 tw，請明說，TC-030 就要放寬。
3. **TC-011 是推論。** 「Seqera Platform 是唯一真相」那句直接和新做法衝突，我當作「只改怎麼讀狀態」的一部分。若你認為那句該保留，TC-011 要刪。
4. **沒有人實際讓 AI 照新 skill 跑一次的手動步驟。** 憲法要求動 `skills/` 的發版前要走手動半邊；計畫沒有新增 `docs/TESTING.md` 的步驟，我只能引用現有的 resume／relaunch 那一步（TC-024）。
5. **「tw」出現在說明文字算不算違規？** TC-001 允許「某句明講這一步 v3 尚未提供」時提到 `tw`；其他地方一律不准。

## 核可紀錄

（尚無。狀態由 verifier 依「計畫無阻擋問題、所有計畫句子皆有 TC」設為合約已確認；上列不確定處不改變已寫出的 TC 的檢查內容，只決定是否要追加或放寬。）
