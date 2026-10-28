# 設定頁登記／移除管線版本 progress ledger

- [x] 動作層：`register_site_pipeline`、`remove_site_pipeline`（寫入，`_require_human`）、`check_site_pipeline_change`（只讀）— `platform/abf_platform/actions/__init__.py`
- [x] 共用 helper：`compute_envs.queue_first_preflight`（回 code＋note）、`compute_envs.check_config_change`（只讀驗證）；`cli._queue_first_preflight` 改為呼叫它，輸出逐字不變 — `compute_envs.py`、`cli.py`
- [x] 網頁兩步驟：`POST /settings/pipelines`（只檢查、回確認頁）、`POST /settings/pipelines/confirm`（唯一寫入處，PAGE 管道）— `web.py`；確認用 CSRF 綁六個欄位的 sha256（無狀態、無 migration）
- [x] 畫面與字串：每個運算環境一塊 `#ce-<名>`（通知、已登記清單＋移除、登記表單、空清單提示）、確認頁、`✓ ○ ✕` 通知 — `web_settings.py`；`g_reg_bad` 改句 — `web_board.py`
- [x] 測試：`platform/tests/test_web_settings_register.py`（新檔，TC 編號寫在註解）
- [x] 文件：`docs/PLATFORM.md`（設定頁一段）、`docs/SETTINGS.md`（從網頁登記）、`docs/TESTING.md`（新增手動一節）

## 被改動的既有釘死測試（只加、只放寬計畫明寫的部分）

| 檔案::測試 | 改了什麼 | 理由 |
|---|---|---|
| `test_web_settings.py::test_st08_still_read_only` | 「頁面只有登出一個表單、中欄沒有 form/input/button」改為：頁面只有登出與 `/settings/pipelines` 兩種表單、中欄只允許後者；中欄仍不得有 select／textarea／a；其餘斷言（無權杖 action、GET 不改資料庫、POST /settings 405、未登入導向）不動 | 計畫裁決 1 |
| `test_web_settings.py::test_st04_ce_table` | 末行「區塊內沒有 a／button／input／form」改為只檢查 `<table>` 本身 | 登記表單放在表格下方（同一個 section）；表格本身仍維持純文字。屬裁決 1 同一件事 |
| `test_web_guided_launch_2d.py` 常數 `S2` | 改為新句「此管線版本尚未在所選運算環境登記，請先至設定頁登記。」 | 計畫作法 4：`g_reg_bad` 改句 |
| `test_dataset_cli.py::test_the_group_adds_only_its_three_commands_and_options_and_no_other_door` | `web.py` 路由清單加入 `/settings/pipelines`、`/settings/pipelines/confirm` | 計畫作法 2 新增兩條路由；只加項 |
| `test_web_parity.py` | `WEB_ONLY` 加 `register_site_pipeline`、`remove_site_pipeline`（理由「寫入需在網頁確認頁確認」）；`INTERNAL` 加 `check_site_pipeline_change`（理由「網頁兩步驟的第一步」） | 計畫作法 5、裁決 10；只加項 |
| `test_actions_layer.py` | 只在檔尾加：兩個動作的拒絕測試與「不是 MCP 工具」測試 | Safety Net 要求新寫入動作附拒絕測試（K01）；只加項 |
| `test_web_board.py::test_tch11_read_only` | `/settings` 的表單改為允許登出表單＋`/settings/pipelines` 表單（`/` 與執行頁原斷言不動）；路由清單加兩條新路由 | 計畫作法 2、裁決 1；只加項 |
| `test_web_board.py::test_tcs39_s40_s41_s42_settings` | 中欄「沒有 a／form／input／select／textarea／button」改為：先去掉 `/settings/pipelines` 的表單再檢查 | 裁決 1 |
| `test_web_board.py::test_tn10_n13_n17_n19_n20_nothing_beyond_the_plan` | `/settings` 的 input 檢查先去掉 `/settings/pipelines` 表單（其餘頁面斷言不動） | 裁決 1 |
| `test_confirm_page.py::test_tcg04_g05_g06_...routes...` | 路由清單加 `/settings/pipelines`、`/settings/pipelines/confirm`（皆 POST） | 作法 2；只加項 |
| `test_owner_binding.py::test_tc068_no_new_way_to_log_in` | 路由集合加兩條新路由（皆不登入任何人） | 作法 2；只加項 |
| `test_cleanup_offer.py::test_no_new_mcp_tool_no_new_route_no_new_cli_command` | `ROUTES` 加兩條新路由；MCP 工具與 CLI 指令清單不動 | 作法 2；只加項 |
| `test_temp_password.py:290` 附近（逐路由導向 `/welcome`） | 無需修改（新路由也會被導向 `/welcome`，測試通過） | — |
