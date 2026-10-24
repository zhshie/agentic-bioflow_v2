# 引導式送出第一刀：/launch 七步編號引導（不連網） progress ledger

- [x] RED：`platform/tests/test_web_guided_launch.py`（gl01–gl13，TC 編號寫在每條測試註解）
- [x] 動作層新 read `list_used_pipelines`（`actions/__init__.py`）＋ MCP 同名唯讀 tool（`mcp_server.py`）；不加資料表、不需 migration
- [x] `web_board.render_launch` 改寫成七步 `<details>`（狀態：✓／●／○＋文字＋樣式），`web.py` 只改 `/launch` 的 GET／POST 處理，沒有新路由
- [x] CSS：只加 `.gstep*`／`.gno`／`.gbody` 等步驟狀態與編號規則（`STYLE` 在 `web_board.py` 內，沒有 static 資料夾），顏色與間距全沿用既有 token
- [x] `docs/PLATFORM.md`（一段「The guided launch page」＋工具數）、`docs/TESTING.md`（新節「Guided launch」手動步驟）
- [ ] 截圖：由 developer-agent 補（1440／390 × zh／en）

## 決定與偏離

- 步驟 4／5／6 的選擇靠各步驟自己的小 GET 表單（`<form class="lform" method="get">`，沿用既有 `.lform` 樣式），送出後回到 `/launch` 並帶參數；最後一步才是 `POST /launch`。沒有 JS、沒有 session、沒有 cookie。
- 路線 ① 需要「這條管線＋版本的全部用過的分析」，所以 `list_used_pipelines` 多兩個選填參數 `pipeline`、`revision`：給了就改列這一組的每一次（最多 20 筆），形狀不變；MCP tool 不帶參數。
- 站台連線檢查只看 `list_compute_envs` 給的 `status`／`message`（沒有 `checked_ok` 欄）；`get_compute_env` 沒有被網頁呼叫。
- 步驟 1 沒選管線時狀態是「之後」（不是目前），目前＝第 2 步。
- `?from=` 同時接受 run 的 id 與 run 名稱（表格連結用名稱）。
- 前置檢查 ✗ 不在網頁擋送出；實際上動作層對不可用環境、未登記版本照舊拒絕（400，第 7 步重繪並顯示拒絕句），所以「✗ 仍 303」只對動作層不拒絕的項目成立。TC-050 的字面「連 ✗ 都 303」在動作層本來就拒絕時做不到，以 `test_gl08b_*` 驗「網頁不擋、由動作層決定」。

## 被改寫的既有斷言（裁決 4）

`platform/tests/test_web_actions.py`
- `test_tc020_the_form_has_the_fields` 最後一行（約 :288）：舊 `assert not re.search(r"(?i)step ?\d|第\s*\d\s*步", mid)` → 新 `assert len(re.findall(r'<details class="gstep ', mid)) == 7`。理由：這條斷言的是 /launch 的版面（舊版表單不得出現步驟編號），本任務就是要把版面改成七步編號；欄位名稱、`required`、`<ol`／`<svg` 等斷言沒動。

## 工具清單／工具數釘死斷言（只加 `list_used_pipelines`）

| 檔案:行 | 舊 → 新 |
|---|---|
| `platform/tests/test_web_parity.py:18` | `WEB_ROUTES` 加 `"list_used_pipelines": "GET /launch …"`（網頁與 MCP 都用，所以放 WEB_ROUTES；OWED／INTERNAL／WEB_ONLY 沒放寬） |
| `platform/tests/test_actions_layer.py:27` | `READ_NAMES` 加 `list_used_pipelines` |
| `platform/tests/test_actions_layer.py:35` | `BASELINE` 的 tools 清單在 `list_site_files` 與 `read_task_log` 之間加 `list_used_pipelines` 一筆（說明文字與 schema 同 `mcp_server.py`） |
| `platform/tests/test_chat_tools.py:15` | `READ_ONLY` 加一項 |
| `platform/tests/test_guidance.py:26` | `READ_TOOLS` 加一項 |
| `platform/tests/test_web_board.py:1192` | 工具名單加一項 |
| `platform/tests/test_mcp.py:63`、`:95` | 排序後的工具名單加一項 |
| `platform/tests/test_pat.py:383` | `len(tools) == 13` → `14` |
| `platform/tests/test_pat.py:751` | `len(tools) == 8` → `9` |
| `platform/tests/test_oauth_mcp.py:329` | 排序後的工具名單加一項 |
| `test_estimate_su.py:297`、`test_gcb_ce.py:776`、`test_gcb_launch.py:1068-1069`（另 `== 13` → `== 14`）、`test_http_site_samplesheet.py:562`、`test_station_launch.py:729`、`test_station_envs.py:381`、`test_human_channel.py:159`、`test_keep_submissions.py:705`、`test_launch_e2e.py:185`、`test_launch_platform.py:304`、`test_resume_edit_params_platform.py:431`、`test_resume_entrypoints.py:46`（皆在 `platform/tests/`） | 各一份工具名單加一項 |
| `tests/platform_storage_doc_test.sh:140`、`:142` | 文件必須寫 "eight read-only tools" → "nine read-only tools"；"Thirteen tools." → "Fourteen tools."（對應 `docs/PLATFORM.md` 同步改） |
