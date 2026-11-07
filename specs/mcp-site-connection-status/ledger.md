# MCP 看得到站台連線狀態、錯誤訊息註明 agent、get_run 的 SU 不再洗版 progress ledger

## 進度

- [x] 全部三件實作完成（RED fa1afa1b，GREEN 見 git log）：site_link 事實（common/agents/launch/agent）、`on_site.sh --check-master`、list_compute_envs 的 `site_connection`、連線錯誤補 agent 名、SU 依分區彙總與 CE 無 suSite 不退 taiwania3。
- 實測 nano4：`configs/sites/nchc-nano4-ce.json` 已有 `"suSite": "nano4"`，`su_rates.json` 已有 nano4 的 `ngs*`（1）與 `big-mem*`（7），不需新增；根因是舊 CE 記錄沒有 suSite 時落到 default_site。
- 既有測試改動（計畫允許）：test_actions_layer BASELINE、test_su_in_get_run 兩處（CE 存在但無 suSite 現在回 None）、test_refusal_visibility TC-090 白名單、ASPECT_GAPS 兩行縮減。
- 憲法與安全網 diff：無（`git diff main...HEAD --stat -- .specify hooks .claude-plugin` 空）。
