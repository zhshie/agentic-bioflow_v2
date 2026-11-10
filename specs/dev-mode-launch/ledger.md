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
