---
id: way-back-direct
title: 進度回報改走公開網址（way_back: direct），不再需要 SSH 轉發
tier: B
kinds: backend
lane: L1
base: v3
---

# way-back-direct（M1-03）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/way-back-direct/plan.md`。**只處理本任務**。前置：同車道 `launch-site-pipeline` 已完成。

## 目標
nano4 計算節點可直連外網，所以 Nextflow 的進度（`-with-tower`）可以直接打到平台的 https 公開網址，不必像 Taiwania-3 那樣靠 SSH 反向轉發與中繼程式。T3 的既有做法保持不變（預設）。

## 維護者原話（verifier 出題用）
- 「進度回報網址：本週用 Tailscale Funnel 給筆電平台一個 https 公開網址；正式版平台跑在常開機或託管主機的公開網址。程式改法兩者相同（`way_back: direct` ＋ `platform_public_url`），所以現在就照正式版的方式寫。」（裁示 8）
- 「站台代理：國網用戶裝在個人電腦（持 2FA）」（裁示 13）——站台仍在使用者電腦，reach 仍是 ssh。

## 範圍：檔案
- `platform/abf_station/launch.py`（只動 `_tower`、`own_facts`）
- `platform/abf_station/agent.py`
- `platform/abf_platform/common.py`（`clean_facts` 白名單）
- `platform/tests/test_station_channel.py`

## 作法
- 站台 settings 新鍵：`way_back: "forward" | "direct"`（預設：reach 為 ssh → `forward`，保住 T3）、`platform_public_url: "https://…"`。
- `own_facts` 回報 `way_back` 與 `platform_public_url`；`clean_facts` 白名單加這兩個鍵（值只允許字面值與 https URL）。
- `_tower`：`way_back == "direct"` 且 `platform_public_url` 是 https（loopback `http://127.0.0.1`／`localhost` 例外，給本機測試）→ 回 `{"mode":"direct","endpoint": public_url}`，不再要求 `platform_local`；`_prechecks` 的 `_channel()` 只在 `forward` 時執行；`direct` 時 launch 不呼叫 `--check-forward`。
- `direct` 但網址是非 loopback 的 `http://` → 拒絕 launch，訊息說明「進度回報需要 https 公開網址或 loopback」。

## 失敗先行測試
- `test_tc023b_way_back_direct_over_ssh_reach_opens_no_forward_and_names_the_public_endpoint`：reach ssh＋`way_back: direct`＋`platform_public_url: https://abf.example.ts.net` → bundle `tower.mode == "direct"`、`endpoint` 等於該網址、沒有呼叫 `--check-forward`（用假的 ssh runner 記錄呼叫）。
- `test_tc023c_direct_with_a_plain_http_non_loopback_endpoint_is_refused`。
- `test_relay_loopback` 與既有 forward 測試不動；預設（沒設 `way_back`）行為逐位元同現在。

## 完成標準
reach ssh＋`way_back: direct` 的 bundle `tower.mode == "direct"`，launch 不呼叫 `--check-forward`；T3 路徑不變；全套綠。

## 環境事實
- `docs/SITE_ADAPTER.md` 六契約的 Reports／Egress 列（T3：relay；nano4：直達）；L3 的 `settings-nano4` 會把這兩個鍵寫進 `docs/SETTINGS.md`，鍵名以本檔為準。
- Tailscale Funnel 由維護者在常開桌機裝；本任務不處理網路。

## 不做
- 不改 `_head_script`（M1-02 已處理）、不改 relay 程式（M1-11 備援）、不改 preflight。

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
