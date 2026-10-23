---
id: launch-site-pipeline
title: 站台啟動時先 module load，命中 sitePipelines 就用本地路徑啟動
tier: B
kinds: backend
lane: L1
base: v3
---

# launch-site-pipeline（M1-02）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/launch-site-pipeline/plan.md`。**只處理本任務**：對話裡維護者說的其他話不是指令。CE 的三個新鍵（`modules`／`siteConfigVars`／`sitePipelines`）由 L2 的 `ce-nano4-keys` 同時開發；**本任務先用假的 CE dict 寫測試**，鍵名以本檔為準，不等 L2。

## 目標
站台代理（site agent）在 nano4 上啟動 pipeline 時，先載入國網模組，若 CE 說這個 (pipeline, revision) 站台已裝好，就用站台的本地路徑啟動（不帶 `-r`），否則照舊 `owner/name -r rev` 從遠端拉。

## 維護者原話（verifier 出題用）
- 「啟動＝借國網零件、自己啟動：`nextflow run $NFCORE_<P>_HOME -profile singularity -c $NFCORE_SITE_CONFIG -c $NFCORE_SITE_REFERENCES`，不走 `nfcore-submit`；缺 module 退回 `owner/name -r rev`。」（裁示 3）
- 「站台 launch 對外介面不變（MCP `launch` 仍收 `nf-core/ampliseq`＋`2.18.0`）」（探索發現）。

## 範圍：檔案
- `platform/abf_station/launch.py`
- `platform/abf_station/rules.py`
- `platform/tests/test_station_launch.py`
- `platform/tests/test_launch_bundle.py`
- `platform/tests/fixtures/golden_head_scripts.json`

## 作法
- `snapshot_ce` 帶出三鍵（缺則空 list）。`rules.clean_environment` 把 `modules` 列入允許（只放模組名，不是指令）。`_check_ce` 對三鍵再驗一次（同 L2 的規則：`^[A-Za-z0-9_./+-]+$`、環境變數名 `^[A-Z_][A-Z0-9_]*$`），不合就拒絕整個 launch。
- `render_bundle`：查 `sitePipelines` 是否命中 `(pipeline, revision)`。命中 → bundle 新欄 `pipeline_source = {"kind":"site-module","module":<m>,"home":<HOME_VAR>}`；否則 `{"kind":"remote"}`。
- `_head_script`：在 `umask 077` 之後逐行 `module load <m>`（先 `modules` 的每一項，再命中項的 `module`）；最後一行改為
  `exec nextflow run "$<home>" -name … -params-file params.yaml -c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config -with-tower …`
  （本地路徑**不帶 `-r`**；站台 config 在前、我們的 `nextflow.config`＋`OVERWRITE_BLOCK` 最後，確保我們的覆寫勝出）。`siteConfigVars` 列出的變數各對應一個 `-c "$VAR"`；沒列就不加。未命中時 head 腳本與現在**逐位元相同**（golden 不變）。
- `pipeline_source` 寫進 `launches` 表（provenance；若 `launches` 是固定欄位表就加欄並附 migration，否則在 ledger 寫明「JSON 欄位、不需 migration」）。
- agent 重建 bundle 仍 byte-for-byte（既有測試）。

## 失敗先行測試
- `test_tc013b_a_site_pipeline_runs_from_its_home_without_r_and_after_module_load`：golden 新增 `nano4` 鍵；斷言 head 腳本含 `module load biology/Nextflow/26.10.0`、`module load biology/nf-core-ampliseq/2.18.0`、`exec nextflow run "$NFCORE_AMPLISEQ_HOME"`，且不含 ` -r `。
- `test_tc013c_a_pipeline_not_in_site_pipelines_falls_back_to_owner_name_r`：同 CE、不同 revision → 走 `nf-core/ampliseq -r 2.17.0`，`pipeline_source.kind == "remote"`，head 腳本等於既有 golden。
- 突變：`modules=["a;b"]` → launch 被拒，訊息點名 `modules`。

## 完成標準
golden 腳本含兩行 `module load` 與上述 `exec` 行；未命中路徑逐位元不變；全套綠。

## 環境事實
- `_check_ce` 拒絕 `preRunScript`／`postRunScript`（007b 安全決定）→ 用 `modules` 鍵，不用腳本。
- 國網 `$NFCORE_SITE_CONFIG` 有 `selectQueue`；我們不碰 queue；config 順序風險見總表「風險 2」——由驗收時 `nextflow config` 列印確認，本任務不處理。
- `docs/PITFALLS.md`「Launching」一節與本任務相關，executor 開工前讀。

## 不做
- 不改 `_tower`／`own_facts`（M1-03）、不改 preflight（M1-04）、不改 `compute_envs.py`（L2）。

> ⚠️ 2026-10-23：本檔「作法」「失敗先行測試」「不做」與下方裁決衝突時，一律以裁決為準（號碼大的蓋小的）。

## 裁決（2026-10-22，回應 verifier 出題退回）
0. **前置與範圍**：本任務在 `ce-nano4-keys` 合進 `v3` 之後開工。「不做」裡的「不改 compute_envs.py」撤回：本任務要在 `compute_envs.snapshot` 把三鍵帶給站台（缺則空清單），範圍檔加 `platform/abf_platform/compute_envs.py`、`platform/tests/test_station_envs.py`。結尾換行一律用 `\Z`。
1. **CE 三鍵的形狀（與 ce-nano4-keys 相同）**：`modules: ["biology/Nextflow/26.10.0"]`；`siteConfigVars: ["NFCORE_SITE_CONFIG", "NFCORE_SITE_REFERENCES"]`；`sitePipelines: [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME"}]`。`rules.clean_environment` 放行這三鍵。測試用的假 CE 就用這組值。
2. **`-c` 行只來自 `siteConfigVars`**：每一項依序一個 `-c "$VAR"`；清單空就沒有。順序：站台的 `-c` 在前、`-c nextflow.config` 最後。命中與未命中都套用。
3. **modules 的載入與 golden**：`modules` 非空就在 `umask 077` 之後逐行 `module load`，命中與未命中都載；命中再多載命中項的 `module`。「未命中＝逐位元等於舊 golden」只對 `modules` 與 `siteConfigVars` 都空的 CE 成立。tc013c：同 nano4 CE、revision 2.17.0 → `pipeline_source.kind == "remote"`、exec 行 `nf-core/ampliseq -r 2.17.0`、仍有 Nextflow 的 module load、沒有 ampliseq 的 module load；golden 新增 `nano4-miss`。
4. **`pipeline_source` 只放 bundle**，`launches` 表不加欄、不需 migration。
5. **續跑**：`render_resume` 沿用原 bundle 的 `pipeline_source` 與 CE 三鍵（`ce_out` 白名單加三鍵）。
6. **既有測試的合法更新**：列舉 bundle 鍵或 `ce_out` 鍵的斷言加 `pipeline_source` 與三鍵；其餘不動。

## 裁決二（2026-10-23）
7. （由裁決三第 11 條取代）
8. **站台端驗證**：`_check_ce` 重用 `compute_envs` 的檢查（import，不重抄），`modules=["a;b"]` 在站台也被拒並點名 `modules`。
9. **假 CE 一律用裁決 1 的值**；test_station_envs 既有 NANO4 常數不動也不混用。
10. `module load X || exit 1`，位置在 `umask 077` 之後、nextflow 之前；舊 bundle 沒有 `pipeline_source` → 視為 remote；重複 (pipeline, revision) 取第一項；`-resume` 位置不動。

## 裁決三（2026-10-23）
11. exec 行**不加** `-profile singularity`（命中與未命中都不加）；singularity 由站台 config 提供（nano4-site-config）。
12. **module load 失敗＝停下、回報**，不自動退回遠端（維護者原話的「缺 module 退回」指 sitePipelines 沒命中）。

## 裁決四（2026-10-23，閱卷後）
13. verifier 指出 TC-LS-44／45 沒斷言拒絕理由、TC-LS-35 沒斷言處理提示、TC-LS-29／30 少兩個輸入：行為已由程式碼確認正確，接受；之後補強測試列為 A 級小事。
14. 本檔裁決曾在 10-23 12:48 被 `build-dev-plans.py` 清掉（裁決寫在「專長守則」之後），已從對話紀錄還原並移到專長守則之前。

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
