# MCP 看得到站台連線狀態、錯誤訊息註明 agent、get_run 的 SU 不再洗版 progress ledger

## 進度

- [x] 全部三件實作完成（RED fa1afa1b，GREEN 見 git log）：site_link 事實（common/agents/launch/agent）、`on_site.sh --check-master`、list_compute_envs 的 `site_connection`、連線錯誤補 agent 名、SU 依分區彙總與 CE 無 suSite 不退 taiwania3。
- 實測 nano4：`configs/sites/nchc-nano4-ce.json` 已有 `"suSite": "nano4"`，`su_rates.json` 已有 nano4 的 `ngs*`（1）與 `big-mem*`（7），不需新增；根因是舊 CE 記錄沒有 suSite 時落到 default_site。
- 既有測試改動（計畫允許）：test_actions_layer BASELINE、test_su_in_get_run 兩處（CE 存在但無 suSite 現在回 None）、test_refusal_visibility TC-090 白名單、ASPECT_GAPS 兩行縮減。
- 憲法與安全網 diff：無（`git diff main...HEAD --stat -- .specify hooks .claude-plugin` 空）。

## 修正輪（全套紅之後）
- 全套先前紅：test_owner_guard（動作層讀取補 owner）、station_static（launch.py 不留 `"ssh"` 字面與 `ssh -` 字樣）、cost 頁面與 test_su_usd（計畫裁決只針對 get_run：`site_of_run(strict=True)` 只由 get_run 用，用量頁／my_usage 仍沿用 default_site）、pitfalls_format（釘數 95 -> 96，Touches 詞補進條目）。
- 既有測試改動：test_su_usd 的 seed 預設給 Slurm CE `suSite: taiwania3`（get_run 不再猜站台）；test_su_in_get_run 的 site_of_run 斷言還原為預設站台並新增 strict 斷言；test_refusal_visibility TC-090 白名單多放 mcp_server.py、agent.py（site_link 文字）；pitfalls_format 釘數。
- 已知環境問題：test_mcp_launch_pipeline::test_no_schema_change 比對 mirror 的 origin/v3（= 工作樹本地 v3 分支，已過期 075b6177），與本件無關（store.py 本件未動）。

## 對抗審修正輪（2026-11-08）
- run_outputs 的連線錯誤補句：完成的 listing 取 job 列的 agent（`jobs.latest_listing` 多回 `agent`），被拒時取 CE 現在的 agent；不再取 launch 的 agent（CE 換 agent 後會指錯機器）。
- `on_site.sh --check-master`：ssh -O check 用 `clocked $CHECK_TMO` 限時，逾時回 124，agent 端對 124 回 unknown；shell 測試加掛住的假 ssh。
- 站台只有一種答案：`estimate_su`、`run_usage`／`my_usage`（`_su_of_run`）也用 strict，CE 無 suSite 一律 NO_SU_SITE；撤回上一輪「用量頁維持 default_site」。CE 已不存在的舊 run 仍用 default_site（TC-053）。
- 既有測試改動：`test_web_cost.py` 的 `seed` 讓 Slurm CE 預設帶 `suSite: taiwania3`（只補輸入，斷言不動；test_cost_by_env、test_su_usd 共用）。`test_site_connection_status.py` 夾具對沒有 agent 的 job 寫空字串（原為 "x"）。
- 文件：PITFALLS 第 60 條、PLATFORM.md suSite 列同步。
