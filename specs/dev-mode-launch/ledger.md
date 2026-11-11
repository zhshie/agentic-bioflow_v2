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

## 2026-11-11：executor 第二輪（run 20261111T1055-L48-dev-mode），交接，未綠
已完成（commit 7d67679e、19221e2f、fc11a227）：
- [x] 裁決 17：`docs/PLATFORM.md`、`docs/PRINCIPLES.md`、`CHANGELOG.md`、`docs/TESTING.md` TC-078 改為「已核可（2026-11-11）」。
- [x] `skills/launch/SKILL.md` 一句、`docs/adr/0006` 加註。
- [x] `platform/tests/test_budget_launch.py`：既有測試的 TC 編號更正，新增 `test_bg_25` 到 `test_bg_46`（TC-001 到 TC-076、TC-092 到 TC-095 的自動案例）。該檔 58 個全過。
- [x] `web.py` 的 `budget_post` 拿掉路由自己的「兩格都填或都空」規則（TC-003、TC-004；專長守則）。
- [x] `CHANGELOG.md` 的條目移到 keep-submissions 之下（`test_keep_submissions.py::test_tc073` 釘住第一條）。

卡住（需要 lead 裁決，我沒有改）：
- `platform/tests/test_web_wording_sweep.py::test_cost_settings_finished_pages`（第 494 行）回報設定頁有禁用字「你」。來源是 `web_devmode.py:26` 的 `bg_unset`「未設定＝每次都問你」，這是 TC-057 指定的原文；`DESIGN.md` 第 88 行與該測試的 `NEW_WORDS` 禁止頁面中文出現「你」。兩者不能同時成立，也不是裁決 14 說的「新增項目不在釘住集合內」。要嘛改 TC-057 的字（例如「未設定＝每次送出前都要確認」），要嘛核可例外。

還沒做：裁決 14 的釘住集合更新。整包 pytest 在 3e98abd1 跑過一次：36 失敗、25 錯誤、7863 過。
- 25 個錯誤全是 `test_launch_nextflow.py`、`test_nextflow_e2e.py`、`test_launch_e2e.py`、`test_pipeline_export.py` 要釘住的 Nextflow，只能經 `tests/platform_test.sh` 跑，不是本任務造成。
- `test_aws_upload`、`test_azure_upload`、`test_byte_channel_a` 各 1 條在整包裡紅（agent offline），單獨跑是綠的；與本任務無關，全套重跑時再看。
- 已逐條讀過、確定是「新增項目不在釘住集合內」的（下一位只加項目）：
  - 指令 `auto-send`／`auto-send list`：`test_cleanup_offer.py:815`、`test_cli_contract.py:163`、`test_cli_snapshots.py`（`cli_tree.txt`、`cli_help_top.txt` 兩個快照）、`test_station_envs.py:430`、`:451`、`test_dataset_cli.py:183`。
  - 路由 `POST /settings/budget`：`test_confirm_page.py:305`、`test_owner_binding.py:822`、`test_web_downstream.py:226`、`test_web_board.py::test_tch11_read_only`（表單 regex 與路由清單）、`test_dataset_cli.py:183`。
  - 欄位 `auto_su_single`、`auto_su_month`、`budget_note`：`test_cleanup_store.py`（248 與另外三條同因）、`test_http_site_samplesheet.py:554`（摘要值）、`test_k8s_launch.py:1434`（32 對 31）、`test_pat.py:701`、`test_temp_password.py:512`、`:543`、`test_web_actions.py:615`、`test_web_nano4_path.py:582`（摘要值）、`test_mcp_launch_pipeline.py:355`（`store.py` 有 diff）。
  - 設定頁新區塊：`test_web_board.py:963`（h2 清單加「預算內免逐次確認」）、`test_web_board.py:1244`（兩個輸入框，表單 regex 加 `budget`）、`test_web_settings_register.py:810`（按鈕字加 `Save`）。
  - 通道 `BUDGET`：`test_resume_scope.py:65`。
  - 新模組／新動作：`test_cleanup_store.py:501`（`budget.py`）、`test_cleanup_store.py::test_the_upgrade_deletes_and_recomputes_nothing`、`test_owner_guard.py:209`（`get_my_budget`／`set_my_budget` 加進 `NO_TOOL`）、`test_k8s_launch.py::test_the_user_visible_actions_are_those_of_the_base`。
  - 後四項（`test_cleanup_store.py:501`、`test_the_upgrade_deletes_and_recomputes_nothing`、`test_k8s_launch` 的 actions、`test_mcp_launch_pipeline.py:355`）我只看到一行訊息，動手前請再讀完整失敗訊息確認原因。
- 之後：`tests/run_all.sh` 全套（`abf-fast-suite … --retry-failed-once`）還沒跑過。

## 第三輪（run 20261111-1240，裁決 13–20）

- [x] 裁決 18：`web_devmode.py` 的 `bg_unset` 改為「未設定＝每次都需確認」（英文同義）。RED 5054ba8e、GREEN f693c3d3；`test_budget_launch.py`、`test_web_wording_sweep.py` 綠。
- [x] 裁決 14：釘住集合只加新增項目（未刪既有項目、未放寬斷言）。
  - 指令 `auto-send`／`auto-send list`：`test_cleanup_offer.py`、`test_cli_contract.py`（MATRIX 多一個 leaf）、`test_station_envs.py`、`__golden__/cli_tree.txt`、`__golden__/cli_help_top.txt`（18c08bc7）。
  - 路由 `POST /settings/budget`、動作 `get_my_budget`／`set_my_budget`、通道 `BUDGET`、設定頁新區塊與 `Save` 按鈕：`test_confirm_page.py`、`test_owner_binding.py`、`test_dataset_cli.py`、`test_web_downstream.py`、`test_web_board.py`、`test_web_settings_register.py`、`test_owner_guard.py`、`test_resume_scope.py`（d808c4ca 與其後一筆）。
  - 欄位 `auto_su_single`、`auto_su_month`、`budget_note`：`test_pat.py`、`test_temp_password.py`、`test_web_actions.py`、`test_cleanup_store.py`（舊列逐值相同，另加最後一欄為 NULL）、摘要值重算 `test_k8s_launch.py`（結構、路由 31→32、動作 60→62；已驗證拿掉新增項目後舊摘要值不變）、`test_http_site_samplesheet.py`、`test_web_nano4_path.py`（a0f288ab）。
  - `budget.py` 說明文字裡的「clean_work」改成「work-folder cleanup」，讓 `test_cleanup_store.py:501` 照舊成立，測試沒動。
- [ ] 卡住：`platform/tests/test_mcp_launch_pipeline.py::test_no_schema_change`（TC-032，第 355 行）。它斷言 `git diff --stat origin/v3...HEAD -- <schema 檔>` 為空；本任務合法改了 `platform/abf_platform/store.py`（+62 行，三個欄位）。這條沒有「集合」可加項目，要過只能改判斷邏輯或基準，裁決 14 明文不准，所以沒動，等 lead 裁決。可選的最小改法：(a) 該測試對本分支允許 `store.py` 的差異只含這三個欄位的新增行；(b) 合併後它自然變綠（三點比較），由 lead 決定合併前接受這一條紅。
- 整包 pytest 其餘已知與本任務無關的紅：Nextflow 釘住的 25 個 error（只能經 `tests/platform_test.sh` 跑）、`test_aws_upload`／`test_azure_upload`／`test_byte_channel_a` 整包跑時偶發（單獨跑綠）。
- 沒有 push、沒有開 PR、沒有動憲法與三條憲法釘住測試。
- 全套（`abf-fast-suite … --retry-failed-once`）在 efa19405 跑過一次：151/152。唯一紅的是 `platform_shard_5_test.sh`，裡面只有 `test_mcp_launch_pipeline.py::test_no_schema_change` 一條失敗（1 failed, 1031 passed），重試後仍紅。其餘釘住測試全綠。
