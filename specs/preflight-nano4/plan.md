---
id: preflight-nano4
title: preflight 先 module load，並檢查站台 pipeline 版本與唯讀快取
tier: A
kinds: backend
lane: L1
base: v3
---

# preflight-nano4（M1-04）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/preflight-nano4/plan.md`。**只處理本任務**。前置：同車道 `launch-site-pipeline`、`way-back-direct` 已完成。

## 目標
啟動前的自檢（preflight）在 nano4 上要先 `module load` 才找得到 java／nextflow；還要確認站台裝好的 pipeline 版本真的等於 CE 說的版本、唯讀映像快取可讀。錯了要點名，不要等到跑了才失敗。

## 維護者原話（verifier 出題用）
- 「nano4 若週四跑不通 → 先在 `/work/u9613010` 自裝 Nextflow＋插件跑通」（裁示 17）——所以 `modules` 為空時 preflight 不得硬要 `module load`。
- 「試用成功標準＝同事不問我就能跑完一次 16S」（裁示 17）——失敗訊息要能讓非工程師知道下一步。

## 範圍：檔案
- `platform/abf_station/handlers.py`
- `platform/tests/test_station_platform.py`

## 作法
- `CHECK_ORDER` 追加 `modules`、`site_pipeline`、`singularity_library`（排在 java／nextflow 之前的只有 `modules`；其餘順序由 executor 依既有慣例排並在 ledger 寫明）。
- java／nextflow 探測指令前綴 `module load <m1>; module load <m2>; `（`modules` 為空則不加前綴，行為同現在）。
- `modules` 檢查：每個模組 `module load <m>` 成功；失敗 → fail，訊息「找不到模組 <m>，請確認站台設定或改用自裝 Nextflow」。
- `site_pipeline`：對 CE `sitePipelines` 每一項：`module load <module>; test -r "$<home>/main.nf"` 且 `$<home>/nextflow.config` 的 `manifest.version` 等於 `revision`（不等 → fail，訊息點名「站台裝的是 X，設定說 Y」）。沒有 `sitePipelines` → unchecked。
- `singularity_library`：CE env 有 `NXF_SINGULARITY_LIBRARYDIR` 時 `test -r` 該目錄；缺 → unchecked（不是 fail）。
- 全部透過既有的假站台（fake site）測，不連真機。

## 失敗先行測試
- `test_preflight_loads_modules_before_java_and_nextflow`：假站台記錄指令，斷言 java 探測指令以 `module load biology/Nextflow/26.10.0;` 開頭。
- `test_preflight_site_pipeline_version_mismatch_fails_and_names_it`：假的 `nextflow.config` 寫 `version = '2.17.0'`，CE 說 `2.18.0` → fail，訊息含兩個版本號。
- `test_preflight_without_modules_is_unchanged`：`modules` 空 → 指令與現在的 golden 相同。

## 完成標準
假站台覆蓋三種失敗；`modules` 空時行為不變；全套綠。（nano4 真機 preflight 全過屬維護者的手動驗收 TC-047n，不在本任務。）

## 環境事實
- `handlers.py::preflight` 目前直接在登入節點跑 `java -version`／`nextflow -version`；nano4 兩者都在 Lmod 模組裡（探索發現）。
- 國網快取是否含 ampliseq 2.18.0 全部映像未知（總表風險 7）；本任務只驗目錄可讀。

## 不做
- 不改 launch 腳本、不改 CE 驗證、不連真機。

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
