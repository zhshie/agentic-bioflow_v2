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

## 價目表（TC-019 至 TC-023）

- 來源只用 Google 官方頁 `https://cloud.google.com/spot-vms/pricing`，讀取日 2026-10-24。頁面上區域選單預設選 Iowa (us-central1)，表格列出 `n2-standard-2/4/8`、`e2-standard-2/4/8` 的「Current Spot pricing (USD)」每小時價；檔內數字逐字取自該頁。
- **沒有 `standard`（on-demand）價**：Compute Engine 的 VM 價目頁（`vm-instance-pricing`、`all-pricing`）的價格表是用 JavaScript 載入的，用 curl 與無頭瀏覽器都讀不到數字；沒有憑記憶補。所以標 `standard` 的 task 目前會是「未知」，只有 spot 算得出。要補請 developer-agent 或維護者用瀏覽器開 `https://cloud.google.com/compute/vm-instance-pricing` 讀 `us-central1` 的值，加進同一筆。
- 頁面裡另有 41 個區域的隱藏資料（頁面原始碼內嵌，沒有區域標籤與表格的對應證據），所以只放頁面預設顯示的 Iowa 那一組；其他區域沒有列。
- TC-023（驗收者抽 3 筆打開網址核對）：同一個網址，核對時要看區域選單是 Iowa (us-central1)。

## 重建索引（裁決三 9）

`task_usage` 只由 receiver 寫入；`rebuild.py` 重建索引時**不**經 receiver、也不重建 `task_usage`（這是 SU 就有的既有行為，`records.py`／`rebuild.py` 不在本任務範圍）。後果：重建後的舊 run 沒有機器型號，`run_tasks_cost` 會回「這個 run 的紀錄沒有保存機器型號」，`month_used` 把它算進 `unknown_runs`（拒絕文字會寫「至少」），`estimate_launch` 跳過它。安全方向的失敗，沒有硬補。要讓重建也還原費用資料，需另開任務動 `rebuild.py`／`records.py`（裁決三 9 的情境，請 developer-agent 決定）。
