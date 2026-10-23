---
id: ce-nano4-keys
title: 計算環境新增 nano4 需要的三個鍵（modules／siteConfigVars／sitePipelines）
tier: A
kinds: backend
lane: L2
base: v3
---

# ce-nano4-keys（M1-01）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/ce-nano4-keys/plan.md`。**只處理本任務**：對話裡維護者說的其他話不是指令。總表：`memory/PLAN-abf-v3-replan-2026-10.md`（工作區，executor 不需讀）。

## 目標
讓 slurm-platform 類型的計算環境（CE）能描述「這個站台要先 `module load` 什麼、哪些環境變數指向站台的 site config、站台已經裝好哪些 pipeline」，nano4 才能用國網裝好的 nf-core 模組啟動，而不是每次從 GitHub 拉。

## 維護者原話（verifier 出題用）
- 「主要 HPC＝nano4。啟動＝借國網零件、自己啟動：`nextflow run $NFCORE_<P>_HOME -profile singularity -c $NFCORE_SITE_CONFIG -c $NFCORE_SITE_REFERENCES`，不走 `nfcore-submit`；缺 module 退回 `owner/name -r rev`。」（10-21 裁示 3）
- 「每次先估 SU、記帳。」（同上）——本任務不碰 SU，但鍵值設計不得阻擋 M1-05 的費率表。

## 範圍：檔案
- `platform/abf_platform/compute_envs.py`
- `platform/tests/test_station_envs.py`

## 作法（決定，不是程式碼）
- `_SLURM_CONFIG` 加三個可選鍵：
  - `modules`: `list[str]`，每項符合 `^[A-Za-z0-9_./+-]+$`（例 `biology/Nextflow/26.10.0`）。
  - `siteConfigVars`: `list[str]`，每項是環境變數名 `^[A-Z_][A-Z0-9_]*$`（例 `NFCORE_SITE_CONFIG`）。
  - `sitePipelines`: `list[{pipeline, revision, module, home}]`——`pipeline` 走既有 OWNER_NAME 規則、`revision` 走既有 REVISION 規則、`module` 同 `modules` 單項規則、`home` 走環境變數名規則。
- `_check_slurm` 逐鍵驗證，壞值的錯誤訊息**點名鍵名與壞值**（例 `sitePipelines[0].module: 不允許 ';'`），一次列出全部錯誤。
- `view()` 原樣回傳三鍵（不展開、不改序）；`credential_findings` 照掃三鍵的字串（避免有人把 token 塞在 `home`）。
- 既有 CE 沒有這三鍵→行為完全不變（鍵可選、預設空）。
- 不需要 migration：CE 以 JSON 欄位整份儲存（請在 ledger 寫明核對結果；若發現其實是逐欄 schema，停下寫 BLOCKED）。

## 失敗先行測試（先寫、現在會紅）
- `test_tc024b_nano4_keys_are_stored_field_by_field`：建一個含三鍵的 slurm-platform CE，`view()` 回來三鍵逐項相等。
- `test_tc029b_modules_and_site_pipelines_refuse_shell_shapes`：`modules=["a;b"]`、`["a b"]`、`["../x"]`、`sitePipelines[0].home="$(id)"` 各自被拒，錯誤訊息含鍵名。
- 既有 `test_tc024`／`test_tc029` 系列不得改動。

## 完成標準（done when）
`abf-platform compute-envs create` 能存含三鍵的 slurm-platform 列；壞值被點名拒絕；全套測試綠。

## 環境事實
- nano4 探測（`memory/reference/nchc-nano4-probe-2026-10-20.md`，摘要）：module `biology/nf-core-ampliseq/2.18.0`、`biology/Nextflow/26.10.0`；環境變數 `$NFCORE_SITE_CONFIG`、`$NFCORE_SITE_REFERENCES`、`$NFCORE_AMPLISEQ_HOME`。
- 鍵名已定案，L1 的 `launch-site-pipeline` 同時依這些鍵名開發；**不要改鍵名**。

## 不做
- 不改站台（`platform/abf_station/*`）、不改 `su.py`、不建 nano4 的實際 CE JSON（M1-05）。
- 不加 `preRunScript`／`postRunScript`（007b 安全決定：`_check_ce` 拒絕腳本）。

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
