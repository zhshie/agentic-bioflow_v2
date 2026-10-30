# MCP 讀取結果檔：run_outputs 加子資料夾、新增 read_run_file（文字分頁、二進位給下載連結） progress ledger

## 完成項目
- [x] 動作層 `actions.read_run_file`（`READ_CHARS = 200_000`；文字 = 嚴格 UTF-8 且無 NUL，ruling 7；`offset > total` 為 `bad_offset`，`offset == total` 為空字串且無 `next_offset`，ruling 8；二進位回 `download_url = web_base_url + /run/file?run=<id>&path=<urlencoded>`，ruling 9）。`run_file` 的欄位照 v3 現有的（ruling 11），沒有改 `run_file`、jobs、store、migrations、web routes。
- [x] `mcp_server.py`：`run_outputs(run_id, path=None)`，新工具 `read_run_file(run_id, path, offset=0)`（十六個工具、其中十一個唯讀）。
- [x] `skills/downstream/SKILL.md`：只增不減（沒有終端機時用 MCP 讀小表；文字不提任何特定 pipeline）。
- [x] `docs/PLATFORM.md`、`docs/TESTING.md`（新段落「MCP reads a result file」五個手動步驟）。
- [x] 新測試 `platform/tests/test_mcp_run_file.py`（TC-001..037 的自動項）。

## 改過的既有斷言（全部只加 `read_run_file`，沒有放寬）
- 工具名清單加 `read_run_file`：test_actions_layer(READ_NAMES)、test_aws_ce、test_aws_launch、test_azure_ce、test_azure_launch、test_azure_upload、test_chat_tools、test_estimate_su、test_gcb_ce、test_gcb_launch、test_http_site_samplesheet、test_k8s_ce、test_station_envs、test_station_launch、test_web_board、test_mcp、test_oauth_mcp、test_human_channel、test_keep_submissions、test_su_usd、test_resume_entrypoints、test_dataset_launch、test_launch_e2e、test_launch_platform、test_resume_edit_params_platform、test_owner_guard、test_guidance(READ_TOOLS)。
- 數量 20 -> 21：test_pat.py:384、test_oauth_mcp.py:44、test_aws_launch、test_azure_launch、test_gcb_launch；test_mcp_server_doc（NUMBERS 加 sixteen、EXPECTED 加 read_run_file、20 -> 21、唯讀 15 -> 16）。
- test_pat.py:752 `== 10` -> `== 11`（ruling 10）：它數的是 `build_server` 裡巢狀函式定義（主 MCP 伺服器的非 canvas 工具），不是 `_add_canvas_reads` 的，所以新工具讓它加 1。test_pat.py:760 的 kw 清單加 `run_outputs -> subpath`、`read_run_file -> offset`（兩個工具多的參數）。
- test_su_usd.py：只是名單加 `read_run_file`（字母序在 `my_usage` 與 `read_task_log` 之間）。
- test_actions_layer.py：BASELINE 內 `run_outputs` 的描述與 schema（多 optional `path`）換成新的；`test_tca10` 的過濾排除 `read_run_file`（它要多收 `path`/`offset`，不是只收 run_id 的讀工具）。
- test_web_parity.py：`WEB_ROUTES` 加 `read_run_file`；INTERNAL 加常數 `READ_CHARS`。
- test_k8s_launch.py：動作名 50 -> 51，雜湊換成 `c855b9be…`（已在 WSL 用同一函式算過，51 個名字含 `read_run_file`）。
- test_results_files.py `test_tc039_no_new_mcp_tool`：名字過濾排除 `read_run_file`（那個測試防的是 #297 當時不加工具；本任務就是加它）。

## 環境備註
- `constitution_scope_test.sh` 在 WSL 紅是環境問題（ruling 6），不是這次改動造成。
- `test_launch_e2e.py::test_tc034…` 在 fast-suite 下 ERROR（要用 `tests/platform_test.sh` 跑第二個固定版 Nextflow），與本任務無關。

## git diff --stat（base..HEAD 的測試／程式變動，提交前）
 docs/PLATFORM.md                                   |  4 +-
 docs/TESTING.md                                    | 10 ++++
 platform/abf_platform/actions/__init__.py          | 61 ++++++++++++++++++++++
 platform/abf_platform/mcp_server.py                | 31 ++++++++---
 platform/tests/test_actions_layer.py               |  6 +--
 platform/tests/test_aws_ce.py                      |  2 +-
 platform/tests/test_aws_launch.py                  |  4 +-
 platform/tests/test_azure_ce.py                    |  2 +-
 platform/tests/test_azure_launch.py                |  4 +-
 platform/tests/test_azure_upload.py                |  2 +-
 platform/tests/test_chat_tools.py                  |  2 +-
 platform/tests/test_dataset_launch.py              |  2 +-
 platform/tests/test_estimate_su.py                 |  2 +-
 platform/tests/test_gcb_ce.py                      |  2 +-
 platform/tests/test_gcb_launch.py                  |  4 +-
 platform/tests/test_guidance.py                    |  2 +-
 platform/tests/test_http_site_samplesheet.py       |  2 +-
 platform/tests/test_human_channel.py               |  2 +-
 platform/tests/test_k8s_ce.py                      |  2 +-
 platform/tests/test_k8s_launch.py                  |  2 +-
 platform/tests/test_keep_submissions.py            |  2 +-
 platform/tests/test_launch_e2e.py                  |  2 +-
 platform/tests/test_launch_platform.py             |  2 +-
 platform/tests/test_mcp.py                         |  4 +-
 platform/tests/test_mcp_run_file.py                |  8 +--
 platform/tests/test_mcp_server_doc.py              | 12 ++---
 platform/tests/test_oauth_mcp.py                   |  4 +-
 platform/tests/test_owner_guard.py                 |  2 +-
 platform/tests/test_pat.py                         |  6 +--
 platform/tests/test_results_files.py               |  2 +-
 platform/tests/test_resume_edit_params_platform.py |  2 +-
 platform/tests/test_resume_entrypoints.py          |  2 +-
 platform/tests/test_station_envs.py                |  2 +-
 platform/tests/test_station_launch.py              |  2 +-
 platform/tests/test_su_usd.py                      |  2 +-
 platform/tests/test_web_board.py                   |  2 +-
 platform/tests/test_web_parity.py                  |  3 +-
 skills/downstream/SKILL.md                         | 16 ++++++
 38 files changed, 164 insertions(+), 59 deletions(-)

## 第二輪修正（全套測試後）
- test_su_in_get_run.py `== 20` -> `== 21`（工具數，只加）。
- `tests/platform_storage_doc_test.sh` 釘住 PLATFORM.md 的 "nine read-only tools" 與 "Fourteen tools."（原文就已落後實際數量）；沒有改那支測試，PLATFORM.md 保留原句，另加一句說 `read_run_file` 是多出來的唯讀工具。
- `test_scope.py` TC-061 禁用字 `site agent`：把動作層一句錯誤文字的 "site agent" 改為 "agent"。

## 第三輪修正（TC-039）
- docs/PLATFORM.md 的工具數量句改為「Twenty-one tools. Sixteen are read-only」並列出 16 個唯讀工具（與 mcp_server.py 一致），拿掉先前補的「多出來的唯讀工具」那句。
- tests/platform_storage_doc_test.sh 只改了 TC-020 的段落定位字串 "Fourteen tools." -> "Twenty-one tools."（錨點，斷言本身不變）。
- 第 6 行 "nine read-only tools"（item 2，列的是第 6 到 8 節那九個）仍由同一支測試釘住，未動。
