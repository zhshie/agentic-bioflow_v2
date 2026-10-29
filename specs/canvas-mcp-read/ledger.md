# 畫布後端的五個唯讀動作開給 MCP：找模組、看模組、列我的 pipeline、看某版、看驗證結果 progress ledger

## 進度（executor）
- [x] 新測試 `platform/tests/test_mcp_canvas_read.py`（TC-001…027、032、039–041、044–045、052）
- [x] `actions/catalogue.py`（新，薄包裝）、`mcp_server.py` 五個唯讀工具（`_add_canvas_reads`，`import ... as`）、docstring 與第 1 行數字改為 fifteen
- [x] `chat_tools.CHAT_SYSTEM_PROMPT` 加一行（13-1），`test_chat_tools.py` 加 TC-033/034 斷言
- [x] 釘住名單的既有測試只改名單／計數（見下「偏離」一條例外）

### 改程式前的紅色輸出（RED commit e44029d7）
`9 failed, 3 passed`：test_find_module_fastqc_shape (KeyError)、test_find_module_nothing、test_describe_module (KeyError: 'found')、test_wrappers_with_data (ImportError: actions.catalogue)、test_owner_reads (KeyError: 'pipelines')、test_other_user_sees_nothing、test_tools_equal_the_action_layer、test_registration (五個名字不在工具列)、test_import_style_and_not_exported。

### MCP 呼叫 `find_module("fastqc")` 的實際回傳（節錄）
`{"sha": "5ed90b42e78410e7411e9c6bdfeff33226d6c58e", "count": 3, "modules": [{"name": "fastqc", "path": "fastqc", "description": "Run FastQC on sequenced reads", "inputs": [{"channel": 0, "name": "meta", "type": "map", ...}, {"channel": 0, "name": "reads", "type": "file", ...}], "outputs": [{"channel": "html", "name": "*.html", "type": "file", ...}, ...]}, ...]}`

### OWED
四張 parity 表與 `test_web_parity.py` 一字未改；OWED 仍是原本五個，沒有變大。

### 偏離與需要驗收者注意
- (修正輪) 先前把三個守門測試放寬或略過，已收窄，覆蓋範圍不再比原本小：
  - `test_catalogue.py::test_no_tool_route_or_action_mentions_the_catalogue`：不再整檔略過。`mcp_server.py` 只剔除「那一行 `import ... actions.catalogue as catalogue_actions`」與 `_add_canvas_reads` 函式本體與其呼叫，剩下的文字仍不准出現 catalogue；`actions/catalogue.py` 改為斷言它保持薄（不得出現 sqlite3／subprocess／abf_platform.store／urllib）；`web.py`、`web_board.py`、`actions/` 其餘檔照舊禁。
  - `test_pipelines_store.py`：`mcp_server.py` 的 `actions.pipelines` 改為「剔除那一行指定 import 後，全文不得再出現」（比先前的 count==1 更嚴）；其餘字與其餘檔照舊。
  - `test_owner_guard.py`：五個新工具不再被排除在 `parity_problems` 之外；它們的動作從 `actions.catalogue`／`actions.pipelines` 依名字找出（必須恰為那五個），以 `extra_actions` 併入，全部 20 個工具都過對等性迴圈。
  - `test_su_usd.py`：五個名字不再只是被排除；先斷言它們各在兩個子模組之一有同名可呼叫動作，其餘工具照舊檢查 `actions` 套件。
  - `test_actions_layer.py`：本來就對五個名字檢查子模組內有同名可呼叫動作（不是單純 continue），未再改。
- `test_pat.py`、`test_mcp.py`、`test_mcp_server_doc.py`、`test_chat_tools.py` 與各 launch／ce 測試：只改名單與計數（含 13-4 的數字詞表與 13-1 的提示斷言）。
- `test_pat.py` TC-D14 只掃 `build_server` 本體（仍是 10 個），因五個工具在 `_add_canvas_reads`，故該數字不動。
- `get_pipeline`／`get_validation` 的 `pipeline_id` 型別為 int（動作層 id 為整數）。
- 不需要 migration（13-5）。
- 全套第一輪還抓到釘名單的檔不在計畫清單內（`git grep '"my_usage"'` 沒列到）：`test_cleanup_offer.py`（名單加五個）、`test_su_in_get_run.py`、`test_aws_launch.py`、`test_gcb_launch.py`、`test_azure_launch.py`（計數 15→20，名單加五個）。
- `test_dataset_launch.py` 也釘排序後的工具名單（第二輪全套抓到），已更新；`test_aws_ce.py::test_a_missing_credential_file_says_where_to_put_it` 第二輪紅一次、單跑綠（與本片無關的環境偶發）。

### git diff --stat（TC-042；基準 a26710c4 = 計畫提交前的 v3，只含 platform/ 內檔，不含 specs/）
計畫清單外、只改名單與計數的測試檔：test_cleanup_offer.py、test_su_in_get_run.py、test_aws_launch.py、test_gcb_launch.py、test_azure_launch.py、test_dataset_launch.py（及 test_estimate_su 等單行名單）；全套抓到釘住五個舊名字的檔都在此列。

```
 platform/abf_platform/actions/catalogue.py         |  31 +++
 platform/abf_platform/actions/chat_tools.py        |   1 +
 platform/abf_platform/mcp_server.py                |  50 ++++-
 platform/tests/test_actions_layer.py               |  10 +-
 platform/tests/test_aws_ce.py                      |   2 +-
 platform/tests/test_aws_launch.py                  |   4 +-
 platform/tests/test_azure_ce.py                    |   2 +-
 platform/tests/test_azure_launch.py                |   4 +-
 platform/tests/test_azure_upload.py                |   2 +-
 platform/tests/test_catalogue.py                   |   8 +
 platform/tests/test_chat_tools.py                  |  10 +-
 platform/tests/test_cleanup_offer.py               |   3 +-
 platform/tests/test_dataset_launch.py              |   4 +-
 platform/tests/test_estimate_su.py                 |   2 +-
 platform/tests/test_gcb_ce.py                      |   2 +-
 platform/tests/test_gcb_launch.py                  |   4 +-
 platform/tests/test_guidance.py                    |   2 +-
 platform/tests/test_http_site_samplesheet.py       |   2 +-
 platform/tests/test_human_channel.py               |   2 +-
 platform/tests/test_k8s_ce.py                      |   2 +-
 platform/tests/test_keep_submissions.py            |   4 +-
 platform/tests/test_launch_e2e.py                  |   4 +-
 platform/tests/test_launch_platform.py             |   4 +-
 platform/tests/test_mcp.py                         |   8 +-
 platform/tests/test_mcp_canvas_read.py             | 219 +++++++++++++++++++++
 platform/tests/test_mcp_server_doc.py              |  12 +-
 platform/tests/test_oauth_mcp.py                   |   4 +-
 platform/tests/test_owner_guard.py                 |  10 +-
 platform/tests/test_pat.py                         |   7 +-
 platform/tests/test_pipelines_store.py             |   4 +
 platform/tests/test_resume_edit_params_platform.py |   2 +-
 platform/tests/test_resume_entrypoints.py          |   4 +-
 platform/tests/test_station_envs.py                |   2 +-
 platform/tests/test_station_launch.py              |   2 +-
 platform/tests/test_su_in_get_run.py               |   2 +-
 platform/tests/test_su_usd.py                      |  10 +-
 platform/tests/test_web_board.py                   |   2 +-
 37 files changed, 389 insertions(+), 58 deletions(-)
```
