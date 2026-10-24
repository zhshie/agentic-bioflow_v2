# 續跑可改參數與資源（b：平台、確認頁、MCP、CLI） progress ledger

- [x] `platform/abf_launch/build.py`: `prepare_resume` 收 `params`／`extra_config`（沒變的值丟掉、空＝今天的路徑、`area` 時對合併後的參數再做 116b 檢查）；新增 `edits_of`、`read_edit_args`、`EDITED_SENTENCE`；`resume_screen` 依 attempt 找腳本，有改動時列「舊值 → 新值」、`extra-N.config` 全文。
- [x] `platform/abf_platform/actions/__init__.py`: `request_resume`／`_request_attempt` 加兩個可選參數；`request_relaunch` 簽名不動。
- [x] `platform/abf_platform/confirm.py`（17:10 裁決加入範圍）: `find_attempt` 比對 `resume.overrides`，同名同改動回同一個 job 號碼；無改動只找無改動的那一次。
- [x] `platform/abf_platform/mcp_server.py`、`actions/chat_tools.py`: `resume` 工具多可選的 `params`、`extra_config`；`relaunch` 不變。
- [x] `platform/abf_launch/cli.py`: `resume` 多 `--param`、`--params-file`、`--config-file`；`relaunch` 一個都沒加。
- [x] `platform/tests/test_resume_edit_params_platform.py`（新）與 `test_resume_entrypoints.py` 的四處允許更新的斷言。
- 不需要 migration：沒有新表、新欄位；舊的未回答請求沒有 `overrides`，行為同今天。
- 未動：`web.py`、`store.py`、`jobs.py`、`receiver.py`、`abf_station/*`、`abf_platform/cli.py`（`git diff --stat` 見 PR）。
