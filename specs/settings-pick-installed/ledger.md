# 設定頁登記管線改成從站台已安裝清單挑選；雲端不顯示登記 progress ledger

## 進度
- [x] 站台盤點（S01-S15）：`platform/abf_station/handlers.py` 新增 `site_inventory()`，`preflight()` 在 connect 通過後多一步只讀盤點，結果放獨立欄位 `site_inventory`；啟動（launch/resume）的預檢呼叫不盤點（`inventory=False`）。測試：`platform/tests/test_station_site_inventory.py`（新檔，沒有併入既有檔）。
- [x] 平台收結果（A06）：`platform/abf_platform/jobs.py` `clean_result` 保留並驗證 `site_inventory`（**計畫範圍漏列 jobs.py，已補**；不改 job kind、不 migration）。
- [x] 動作層（A01-A07）：`actions.site_pipeline_inventory`（只讀，最近一次含清單的預檢）、`actions.reload_site_inventory`（排一次預檢）。`register_site_pipeline` 未改。
- [x] 網頁（B、R、D）：`web.py` 的 `POST /settings/pipelines` 接受 `pick`（伺服器端查表，不信任瀏覽器的 module／home）；新路由 `POST /settings/inventory`（CSRF 用途 `settings-inventory` ＋ same-origin）；`web_settings.py` 依環境類型三種畫面。
- [x] 文件：`docs/SETTINGS.md`「Register from the web page」改寫；`docs/TESTING.md` 新增「設定頁從站台清單挑選」手動一節（M01-M03）。

## 實作決定（計畫／合約沒訂的細節）
- `site_inventory` 的 error 原因欄位名為 `reason`（中文 (English) 格式，最多 200 字），只在 `status=error` 時有。
- 重新讀取的路徑 `/settings/inventory`；CSRF 用途 `settings-inventory`。
- 雲端型別名稱在 `web_settings.CLOUD_TYPES`（web_settings 不得匯入 compute_envs），`test_the_pinned_cloud_types` 釘它與 `compute_envs.PLATFORM_HOST_TYPES` 相同。
- 其他不支援的型別（lsf 等）：只列已登記清單，不顯示登記表單。
- 清單 `ok` 但全部已登記（D11）：不顯示下拉與「登記」，仍有灰字讀取時間、重新讀取按鈕與進階區；沒有多寫一句（計畫未訂，見報告問題）。
- 沒有「載入中」畫面：重新讀取是普通表單送出，排入後以 `inv_queued` 通知告知。
- `inv_queued`／`inv_no_agent` 句子與英文依合約「出題者訂定的字串」表。

## 被改動的既有測試斷言（X08；只加不刪）
1. `test_web_settings_register.py::test_d05_button_words`：Slurm 區塊多了「重新讀取站台清單」按鈕，中英兩處允許集合各加一項（登記、移除仍須都在）。
2. `test_web_settings_register.py::test_d14_d15_words`：跳過 `pf_pick_gone` 的禁用字檢查——計畫逐字指定的 400 句含「這個」（合約註記 1）。
3. `test_web_settings_register.py::test_d16_only_this_task_has_forms`：設定頁中欄的表單 action 集合加入 `/settings/inventory`。
4. `test_web_settings.py::test_st08_still_read_only`：同上，兩處 action 集合加入 `/settings/inventory`。
5. `test_web_parity.py`：`WEB_ONLY` 表加入 `site_pipeline_inventory`、`reload_site_inventory`（含理由）。

## 環境註記
- worktree 以 Windows git 建立：WSL 內 `constitution_scope_test.sh` 若因讀不到 git 而紅＝環境問題，以 CI 為準（計畫裁決 5）。
- python3 在 Git Bash 是 Windows 商店空殼；編輯與測試都經 WSL。

## 全套測試後追加改動的既有測試斷言（同樣只加不刪）
6. `test_station_e2e.py::test_pf_empty_modules_means_no_module_load`：預檢工作現在多一次只讀的 `module -t avail`／`module show`；「沒有 module load」的斷言不變，只把這兩種只讀呼叫排除在「以 module 開頭的呼叫」之外。
7. `test_station_e2e.py::test_pf_old_environment_unchanged`：完整指令序列仍逐條比對（`pf.commands[:-1]`），另外釘住最後一次呼叫就是盤點（含 `abf_inv=`）。
8. `test_station_launch.py`（兩處 `nothing_happened`）：預檢工作可有 `module -t avail`／`module show`（只讀）；`dangerous()`、`destructive()`、守護檔案不變等斷言不變。啟動閘門（launch／resume 的預檢）不讀清單：`preflight()` 預設 `inventory=False`，只有預檢工作（`handle`）傳 True。
9. 路由清單釘住：`test_confirm_page.py`、`test_cleanup_offer.py`、`test_dataset_cli.py`、`test_web_board.py` 各加入 `POST /settings/inventory`。
10. `test_owner_guard.py`：`NO_TOOL` 加入 `site_pipeline_inventory`、`reload_site_inventory`（網頁專用，附理由）。
11. `test_web_board.py`：`/settings` 允許重新讀取按鈕的表單（action `/settings/inventory`）與其 hidden `ce`，並把 `<details class="padv">`（計畫指定的進階區）排除在「details 只准是 menu 或 stage」的計數之外（三處：tch11、tcs39、tn10）。
