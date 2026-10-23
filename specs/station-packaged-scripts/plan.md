---
id: station-packaged-scripts
title: pip 安裝的站台代理自帶 scripts/，不必再給 --plugin-root
tier: A
kinds: backend
lane: L8-packaging
base: v3
---

# station-packaged-scripts

> 本檔由 developer-agent 寫（2026-10-24），`/supervise` 複製進 worktree。**只處理本任務**。

## 目標
`pip install` 平台後，`abf-station run` 不帶 `--plugin-root` 也能找到 `scripts/on_site.sh`（以及它會呼叫的同資料夾腳本）。今天的實況：桌機 WSL 用 pip 裝的 venv 跑站台代理，拒跑「the site script … was not found; give the plugin folder with --plugin-root」，只能手動指 repo 路徑。

## 維護者原話（verifier 出題用）
- 無原話；這是 2026-10-23 桌機部署實際踩到的 bug（站台代理必須加 `--plugin-root /mnt/c/.../wt/deploy` 才能啟動）。驗收情境：在一個只裝了 wheel、沒有 repo 的環境，`abf-station run` 的部署檢查不再因找不到 on_site.sh 而拒跑。

## 範圍：檔案
- `platform/setup.py`（build hook 另外複製 repo 的 `scripts/` 進 `<build_lib>/abf_station/plugin/scripts`）
- `platform/pyproject.toml`（只在需要時新增 package-data；見裁決 2）
- `platform/abf_station/site.py`（新增 `default_plugin_root()`）
- `platform/abf_station/cli.py`（第 100、114 行的預設改用 `site.default_plugin_root()`；找不到時的訊息說明「安裝裡沒有，也沒給 --plugin-root」）
- `.gitignore`（忽略建置時的複本 `platform/abf_station/plugin/`）
- `platform/tests/test_station_packaging.py`（新檔）
- `platform/tests/test_guidance.py`（只在裁決 2 允許的範圍改 TC-406）

## 作法
1. 照 `abf_platform/skills/` 的既有做法（`setup.py` 的 `BuildPyWithSkills`、`guidance.py:30-36` 的 `skills_dir`）：建置時把整個 repo `scripts/` 複製到 `abf_station/plugin/scripts/`（整個資料夾，因為 `on_site.sh` 會 source `settings.sh`、呼叫 `egress_allow.sh` 與 `--script NAME`）。
2. `site.default_plugin_root()`：若 `Path(__file__).parent / "plugin" / "scripts" / "on_site.sh"` 存在，回傳 `Path(__file__).parent / "plugin"`；否則回傳 `Path(__file__).resolve().parents[2]`（repo checkout 的舊行為）。`--plugin-root` 仍優先。
3. 腳本以 `bash <path>` 執行或保留執行位元，二擇一，維持現在 Site 呼叫方式可運作。

## 失敗先行測試（`platform/tests/test_station_packaging.py`）
- `test_sp01_wheel_ships_the_scripts_folder`：仿 TC-404 用 `pip wheel` 建 wheel，wheel 內有 `abf_station/plugin/scripts/on_site.sh`、`settings.sh`、`egress_allow.sh`，內容與 repo 的 `scripts/` 逐位元相同。
- `test_sp02_default_plugin_root_prefers_the_packaged_copy`：在暫存目錄假造 `abf_station/plugin/scripts/on_site.sh` 的情境（monkeypatch 模組路徑），`default_plugin_root()` 回傳 packaged 路徑。
- `test_sp03_checkout_falls_back_to_repo_root`：沒有 packaged 複本時回傳 repo 根，且 `on_site_script(...)` 存在。
- `test_sp04_explicit_plugin_root_still_wins`：給 `--plugin-root` 時用它。
- `test_sp05_copy_is_gitignored_and_untracked`：仿 TC-408。

## 完成標準
五條綠；全套綠。

## 環境事實
- 細節見 origin/v3：`platform/abf_station/site.py:41-49`、`cli.py:88-114,149,153`、`setup.py`（BuildPyWithSkills）、`guidance.py:30-36`、`test_guidance.py:310-360`（TC-404～408）。
- `su.py:15` 讀 `configs/sites/su_rates.json` 有同類潛在問題，**本件不做**，記進 ledger 的「欠」。

## 不做
- 不改 on_site.sh 本身；不改 su.py；不改站台協定。

## 裁決（2026-10-24，developer-agent）
1. 全套裡若只剩 `tests/init_workspace_test.sh` 的「site side with no run area known」一條紅、且它在 base 同樣紅（另案 init-workspace-hermetic 會修），視同全綠，executor 寫 `GREEN <sha>` 並在報告註明。
2. TC-406 釘死 package-data 的 regex：優先不動 package-data（建置 hook 複製進 build_lib 後，用 `[tool.setuptools.package-data]` 另一個表或 `include-package-data`/MANIFEST 的方式能被 wheel 收進就好）。若無法避免改 package-data，允許把 TC-406 改成「含 abf_platform 那一條且另含 abf_station 的 plugin/scripts」，並在 ledger 寫「以前／以後」。
3. 不需要 migration。

## 裁決二（2026-10-24 01:20，回應 verifier 出題退回）
4. **configs/ 一起打包**：建置 hook 同時複製 repo 的 `scripts/` 與 `configs/` 到 `abf_station/plugin/`（結構 `plugin/scripts/…`、`plugin/configs/…`，與 repo 根相同），讓 on_site.sh 的 `ROOT`＝`plugin/`、ssh 模式的 `tar -C "$ROOT" scripts configs` 與遠端腳本讀 `$ROOT/configs/sites/*` 都成立。目標「不必再給 --plugin-root」包含 reach=ssh。加測試：wheel 內 `abf_station/plugin/configs/sites/` 與 repo `configs/sites/` 逐位元相同；以 packaged plugin root 執行 ssh 送出那行的 tar（可在測試裡對 plugin root 實跑 `tar -cz -C <root> scripts configs` 到 /dev/null）成功。
5. 整個 scripts/ 資料夾（含子資料夾）都帶；TC-SP-02 照此。
6. 找不到時的訊息照現在的寫法保留腳本路徑（使用者需要知道），補上「安裝版裡沒有，也沒給 --plugin-root」。
7. `.gitignore` 忽略 `platform/abf_station/plugin/`；範圍檔清單加 `platform/abf_station/plugin/`（只限建置產物，不提交）。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
