---
id: nano4-site-config
title: nano4 站台設定檔、CE 範本與三種費率
tier: B
kinds: backend
lane: L2
base: v3
---

# nano4-site-config（M1-05）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/nano4-site-config/plan.md`。**只處理本任務**：對話裡維護者說的其他話不是指令。前置：`ce-nano4-keys` 已在同車道先完成（鍵名 `modules`／`siteConfigVars`／`sitePipelines`）。

## 目標
給 nano4 一份可直接 `abf-platform compute-envs create` 的 CE 範本、一份國網模組缺席時的退路 config，以及 SU 估算用的三種費率，讓 16S 在 nano4 啟動前就能估出「約多少 SU、約多少元」。

## 維護者原話（verifier 出題用）
- 「建 nano4 的計算環境與費率表（國科會 0.1／學術 0.2／企業 0.37 元每核心小時）。」（10-21 白話摘要第 2 點）
- 「開發測試可直接用計畫 `mst109178`，每次先估 SU、記帳。」（裁示 3）
- 「nano4 若週四跑不通 → 先在 `/work/u9613010` 自裝 Nextflow＋插件跑通」（裁示 17）——所以 CE 範本的 `modules` 必須可留空、`environment` 可加 `PATH`／`NXF_PLUGINS_DIR`。

## 範圍：檔案
- `configs/sites/nchc-nano4.config`（新）
- `configs/sites/nchc-nano4-ce.json`（新）
- `configs/sites/su_rates.json`
- `platform/abf_platform/su.py`
- `platform/tests/test_estimate_su.py`

## 作法
- `nchc-nano4.config` 只放國網模組缺席時的退路：`process.executor='slurm'`、`resourceLimits`、`singularity{enabled=true; autoMounts=true}`、`process.queue` 以 ngs 分區為準（值寫成可由 `SLURM_PARTITION` 覆寫）、`clusterOptions="-A ${SLURM_ACCOUNT}"`。**不抄** Taiwania-3 的 box 表。
- `nchc-nano4-ce.json`：`headQueue: "ngsconsole"`、`headJobOptions: "-A mst109178 -c 1 --mem=8G -t 2-00:00:00"`、`modules: ["biology/Nextflow/26.10.0"]`、`siteConfigVars: ["NFCORE_SITE_CONFIG","NFCORE_SITE_REFERENCES"]`、`sitePipelines: [{"pipeline":"nf-core/ampliseq","revision":"2.18.0","module":"biology/nf-core-ampliseq/2.18.0","home":"NFCORE_AMPLISEQ_HOME"}]`、`environment: ["NXF_SINGULARITY_LIBRARYDIR=/work/envstack/apps/application/biology/nf-core/singularity-cache","NXF_SINGULARITY_CACHEDIR=/work/u9613010/.singularity","NXF_OPTS=-Xms512m -Xmx4g"]`、`workDir: "/work/u9613010/runs"`、`readRoots: ["/work/u9613010"]`。檔案頂部用 JSON 允許的方式（例如 `"_comment"` 鍵，若 schema 允許；否則寫在 `docs/SETTINGS.md`——由 L3 處理，這裡只在 ledger 註明）說明「自裝 Nextflow 時把 `modules` 清空、`environment` 加 `PATH=/work/u9613010/nextflow/bin:$PATH`、`NXF_PLUGINS_DIR=/work/u9613010/.nextflow/plugins`」。
- `su_rates.json` 加 `sites.nano4`：`twd_per_core_hour: {nstc: 0.1, academic: 0.2, industry: 0.37}`；分區係數 `ngs*: 1`、`big-mem*: 7`；既有 T3 條目不動。
- `su.py::load_rates` 支援站台層級覆寫（`sites.<name>` 蓋過頂層預設）；`estimate_su(..., site="nano4")` 回 SU 與三種費率的 NT$（鍵名 `twd: {nstc, academic, industry}`）；沒給 site → 行為同現在。

## 失敗先行測試
- `test_tc025b_nano4_rates_price_a_ngs_task_at_0_1_twd_per_core_hour`：1 核 × 10 小時在 ngs 分區 → 10 SU、NT$1.0／2.0／3.7。
- `test_tc025c_bigmem_factor_7`：同工作量在 big-mem 分區 → 70 SU。
- 既有 T3 案例全部保留、斷言不改。
- 加一條：讀入 `configs/sites/nchc-nano4-ce.json` 後通過 `compute_envs` 的 slurm 驗證（用 `ce-nano4-keys` 完成後的 `_check_slurm`）。

## 完成標準
`estimate_su` 對 nano4 run 回 SU 與三種費率；CE JSON 通過驗證；全套綠。

## 環境事實
- `memory/reference/nchc-nano4-probe-2026-10-20.md`：帳號 `mst109178` 可送 `ngsconsole`；計算節點直連外網；Slurm 25.11.4；唯讀快取 `/work/envstack/apps/application/biology/nf-core/singularity-cache`。
- `_prechecks` 要求 `NXF_SINGULARITY_CACHEDIR` 可寫，所以可寫快取另指 `/work/u9613010/.singularity`，唯讀快取走 `LIBRARYDIR`。
- 費率出處：`memory/reference/nchc-su-pricing-2026-10-18.md`（國網公告；維護者 10-21 定三種費率）。

## 不做
- 不改站台程式、不實際建立 CE（developer-agent 自己用 CLI 建）、不改 T3 任何設定。

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
