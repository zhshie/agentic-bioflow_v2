---
id: su-followups
title: SU 費率檔跟著安裝包走；補強 estimate-su-mcp 的四條鬆測試
tier: A
kinds: backend
lane: L10-su
base: v3
---

# su-followups

> 本檔由 developer-agent 寫（2026-10-24），`/supervise` 複製進 worktree。**只處理本任務**。

## 目標
1. pip 安裝的平台讀得到 SU 費率：`platform/abf_platform/su.py` 的 `RATES_PATH` 現在是 `Path(__file__).resolve().parents[2] / "configs" / "sites" / "su_rates.json"`，安裝後找不到。改成：先找 #170 打包進來的 `abf_station/plugin/configs/sites/su_rates.json`（用 `importlib` 找到 `abf_station` 套件位置），沒有再退回 repo 路徑。
2. 補強 #171 閱卷指出的四條鬆測試（`platform/tests/test_su_in_get_run.py`）：
   - TC-014：真的經 MCP 的 `get_run` 工具呼叫一次（用 `test_mcp.py`／`test_actions_layer.py` 既有的 in-process MCP 呼叫方式），斷言回傳含 `su`。
   - TC-083：TC-020、022、025、027、030 每一種 `unknown_reasons` 都檢查不含路徑、SQL 字樣與 token。
   - TC-073：走 `rebuild.py` 重建一個 run 後問 `get_run`，斷言 `su` 為 null 且原因是「沒有用量紀錄」。
   - TC-048：經 `actions.estimate_su` 走一次 `site_of_run` 的判斷。

## 維護者原話（verifier 出題用）
- 無原話；來源是 PR #171 verifier 閱卷的「放水」清單與 #170 ledger 的「欠」（su.py 讀 su_rates.json 用 repo 路徑）。

## 範圍：檔案
- `platform/abf_platform/su.py`
- `platform/tests/test_su_in_get_run.py`
- `platform/tests/test_su_packaged.py`（新檔，檔首 `# Nothing existing:` 標頭）
- `specs/su-followups/ledger.md`

## 失敗先行測試
- `test_su_packaged.py::test_rates_found_from_the_packaged_plugin`：仿 `test_station_packaging.py` 的做法建 wheel 解開、`-I` 獨立 Python 匯入 `abf_platform.su`，讀得到費率（nano4 的 `twd_per_su` 存在）。
- `test_su_packaged.py::test_checkout_still_uses_repo_configs`。
- 上述四條補強，各自先證明「把被測的那一段弄壞會紅」（在 ledger 記下怎麼證明的）。

## 完成標準
全套綠。

## 不做
- 不改計費公式、不改 get_run 形狀、不改 receiver。

## 裁決（2026-10-24，developer-agent）
1. 不需要 migration。

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
