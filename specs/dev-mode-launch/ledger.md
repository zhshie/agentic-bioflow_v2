# 預算內免逐次確認（憲法 8.0.0 BUDGET 通道） progress ledger

2026-11-10（`date +%F`）。origin/v3 已含 #376（憲法 7.0.0）。

## 完成
- [x] budget.py（decide／check，fail-closed）、su.estimate_launch／month_used_at、store 三個新欄與 set_user_budget／user_budget、actions 的 BUDGET 分支與 get/set_my_budget、confirm.approve／find_* 加 BUDGET（ef552636）
- [x] 設定頁兩個數字與 `POST /settings/budget`、`abf-platform auto-send list [--since]`、`test_budget_launch.py` 共 24 個測試綠（TC 雲端、forget、BUDGET 直餵被拒、設定頁、託管、auto-send、AST 掃描、migration）
- [x] test_chat_confirm 的 `test_tcm_47` 基準更新，新增欄位 `auto_su_single`、`auto_su_month`、`budget_note`，新路由 `POST /settings/budget`
- [x] CHANGELOG、OPERATIONS（auto-send list）、TESTING（TC-078 手動步驟）
- [x] deploy/ 託管單元檔：依裁決 4 延後（H-1 部署包未合併），本片不改 deploy/

## 未完成（卡住）
- [ ] 憲法 8.0.0 草案（I.2、Safety Net 兩條、Check 行、8.0.0 條目、版本行）：executor 的編輯被 hook 擋下（`.specify/memory/constitution.md` 屬契約／閘門檔），不得繞過。需要 developer-agent 套用，內容見 decisions.tsv 與下方。
- [ ] 釘住測試的更新（`PINNED_SN_SHA256` 與版本字串於 constitution_scope_test、platform_direction_docs_test、charter_v4_workflow_test）與 `tests/budget_doc_test.sh`：同屬 tests/*.sh 閘門檔，待憲法落地後一併處理
- [ ] docs/PLATFORM.md、skills/launch/SKILL.md 一句、docs/adr/0006 加註
- 憲法草案要點：Approval 欄只寫 `**Approval.** PENDING: 維護者尚未對修正案全文表示同意。合併前必須由維護者親口同意後補上其原話。`；`(today …)` 括號不動；Check 行加 `platform/tests/test_budget_launch.py` (`test_bg_*`)；日期 2026-11-10。

## 2026-11-11：憲法 8.0.0 草案落地（由憲法起草代理套用，非 executor）
- [x] 與 `origin/v3`（f82fb65f）合併（merge，無 rebase）；`docs/TESTING.md` 衝突兩邊都保留。
- [x] 憲法草案：I.2、Safety Net 的 launch 規則與 write-tool 規則（含 Check 行）、8.0.0 條目、版本行；日期 2026-11-11（取代上方「日期 2026-11-10」）。Approval 欄為 PENDING。
- [x] 釘住測試：三檔的版本字串與日期、`PINNED_SN_SHA256`（`ee51f3e2…` → `8a59945b…`）；新增 `tests/budget_doc_test.sh`。沒有刪除或放寬任何斷言。
- [x] `docs/PLATFORM.md`、`docs/PRINCIPLES.md` 各一段。`skills/launch/SKILL.md` 一句與 `docs/adr/0006` 加註未做（修憲任務限定文件最小同步）。
- 超出本計畫範圍、待 lead 裁決：應 lead 2026-11-11 指示，同一修正案另改了 Development Workflow 最後一條（實機驗收可在合併後、裁決代理、受保護路徑自動合併）；與 TC-081「憲法 diff 只限 I.2、Safety Net、8.0.0 條目、版本行」不符，該案需裁決或改題。紀錄在 `.specify/amendments/8.0.0-budget-and-workflow/`。
