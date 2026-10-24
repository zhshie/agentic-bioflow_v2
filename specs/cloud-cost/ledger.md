# 雲端費用：預估、記錄用量、每人每月上限（美元，不換算） progress ledger

- [x] RED：`platform/tests/test_cloud_cost.py`（TC-001 至 TC-122 的自動部分）先寫、先紅（`cloud_cost` 匯入失敗）。
- [x] `store.py`：`task_usage` 加 `machine_type`／`price_model`／`cloud_zone`（建表＋舊庫以 ALTER 補、被搶先補了就放過）；`tokens.db` 新表 `cloud_caps`；`parse_cloud_cap`／`set_cloud_cap`／`cloud_cap`。
- [x] `receiver.py`：task 完成事件多存三欄，非字串存 NULL、截 64 字。
- [x] `cli.py`：`user add --cloud-cap-usd`、`user cloud-cap <名> <美元>`（0 到 1,000,000；壞數字先拒絕、不建帳號）。
- [x] `cloud_cost.py`：`load_rates`、`cost_of_tasks`、`run_tasks_cost`、`month_used`、`estimate_launch`、`cap_problem`（只對 `googlebatch-platform` 動作，其他環境立刻回 None）。
- [x] `data/cloud_rates.json`：真實價目，見下「價目表」。
- [x] 文件：`docs/CLOUD.md`（新）、`docs/PLATFORM.md`（指令、儲存表、Money 段）、`docs/TESTING.md`（cloud-cost 小節，手動驗收 1 至 4）。
- [x] 既有斷言（計畫列的兩處）：`test_gcb_ce.py` 的 `{"cloud_cost.py", "rates.json"}` 改成 `{"rates.json"}`；`test_web_actions.py` 的 `SCHEMA` 加 `tokens.cloud_caps` 一列與註解。
- [ ] 手動驗收 1 至 4（TC-116 至 TC-119）：維護者做，這裡不做。手動第 3 步與帳單的差距：尚未量。

## 價目表（裁決四 10、11；TC-019 至 023、134）

- 出貨的 `data/cloud_rates.json` 先清空（`regions` 為空，保留格式與欄位說明）。原本的六筆 spot 價無法核對、也沒有一般價，已移除。空價目時 `cost_of_tasks` 回未知並附理由「尚未填入價目」。真實價目由之後的 `cloud-rates-fill` 填（Cloud Billing Catalog API）。
- TC-023、TC-118：不適用／延後。手動驗收第 3 步（對帳單）未做，原因：目前沒有價目。TC-119 空價目下只驗得了上限 0／已用滿。
- TC-137：PR 說明必須寫明「本次 merge 後上限不會擋任何送出（未接線，cloud-cost-wire 負責）」。

## 自寫測試預期值調整（TC-130、裁決四 12）

- 以前：`test_the_shipped_rates_file_is_complete_and_honest` 要求出貨檔至少一筆價目、日期不早於 2026-10-24。以後：`test_the_shipped_rates_file_is_valid_and_empty` 要求檔案合法、有條目時才檢查來源與日期、且條目為零。理由：裁決四 10。
- 以前：TC-077、078 用 PAT 逐一呼叫。以後：`test_no_user_door_to_the_cap`、`test_the_cap_is_never_read_back_by_any_existing_door` 用靜態掃描原始碼。理由：裁決四 12 接受。

## 重建索引（裁決三 9）

`task_usage` 只由 receiver 寫入；`rebuild.py` 重建索引時**不**經 receiver、也不重建 `task_usage`（這是 SU 就有的既有行為，`records.py`／`rebuild.py` 不在本任務範圍）。後果：重建後的舊 run 沒有機器型號，`run_tasks_cost` 會回「這個 run 的紀錄沒有保存機器型號」，`month_used` 把它算進 `unknown_runs`（拒絕文字會寫「至少」），`estimate_launch` 跳過它。安全方向的失敗，沒有硬補。要讓重建也還原費用資料，需另開任務動 `rebuild.py`／`records.py`（裁決三 9 的情境，請 developer-agent 決定）。
