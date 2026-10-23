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

## 裁決（2026-10-22，developer-agent，回應 verifier 出題退回）
0. **前置與範圍**：本任務在 `ce-nano4-keys` 合進 `v3` 之後開工（重跑 `reuseContract:false`）。「不做」裡的「不改 compute_envs.py」**撤回**：本任務要在 `compute_envs.snapshot` 把三鍵帶給站台（缺則空清單），範圍檔加 `platform/abf_platform/compute_envs.py`、`platform/tests/test_station_envs.py`（只加 snapshot 的測試）。CE 三鍵的驗證規則沿用 ce-nano4-keys 已合併的 `_check_site_keys`，站台端 `_check_ce` 只再驗形狀（清單／物件），不重抄正則；結尾換行一律用 `\Z`。
1. **CE 三鍵的形狀（與 ce-nano4-keys 相同）**：
   `modules: ["biology/Nextflow/26.10.0"]`（模組名清單）；
   `siteConfigVars: ["NFCORE_SITE_CONFIG", "NFCORE_SITE_REFERENCES"]`（環境變數名清單）；
   `sitePipelines: [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "biology/nf-core-ampliseq/2.18.0", "home": "NFCORE_AMPLISEQ_HOME"}]`。
   `rules.clean_environment` 放行這三鍵（照上面形狀，其餘丟掉）。測試用的假 CE 就用這組值。
2. **`-c` 行只來自 `siteConfigVars`**：作法裡寫死的 `-c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES"` 只是 nano4 那組值的結果，不是固定內容。規則＝`siteConfigVars` 每一項依序一個 `-c "$VAR"`；清單空就一個都沒有。順序：站台的 `-c` 在前、我們的 `-c nextflow.config` 最後。命中與未命中都套用這條（未命中也要吃站台 config）。
3. **modules 的載入與 golden**：只要 `modules` 非空，head 腳本就在 `umask 077` 之後逐行 `module load`，**命中與未命中都載**；命中再多載命中項的 `module`。因此「未命中＝逐位元等於舊 golden」只對 `modules` 為空且 `siteConfigVars` 為空的 CE 成立（既有 golden 全部屬此，所以舊 golden 不變）。tc013c 改寫為：同 nano4 CE、revision 2.17.0 → `pipeline_source.kind == "remote"`、exec 行是 `nf-core/ampliseq -r 2.17.0`、仍有 `module load biology/Nextflow/26.10.0`、沒有 ampliseq 的 module load；golden 新增 `nano4-miss` 鍵記錄它。
4. **`pipeline_source` 只放 bundle**（`bundle_json` 內），`launches` 表不加欄、不需 migration；ledger 寫明。
5. **續跑（resume）**：`render_resume` 走同一個 `_head_script`，沿用原 bundle 的 `pipeline_source` 與 CE 三鍵（`ce_out` 白名單加這三鍵），所以本地路徑啟動的 run 續跑仍從本地路徑、仍先 module load。加一條 TC：命中的 run 續跑的 head 腳本同樣含 module load 與 `"$NFCORE_AMPLISEQ_HOME"`、不含 ` -r `。
6. **既有測試的合法更新**（寫進 ledger）：`test_launch_bundle.py`／`test_station_launch.py` 若有列舉 bundle 鍵或 `ce_out` 鍵的斷言，加 `pipeline_source` 與三鍵是合法更新；其餘斷言不動。

## 裁決二（2026-10-23，回應第二次出題退回）
7. **`-profile singularity` 要在 exec 行**（維護者原話的啟動行有它；nano4 的映像快取就是 singularity）：exec 行固定 `nextflow run <來源> [-r <rev>] -name … -profile singularity -params-file params.yaml [-c "$VAR"…] -c nextflow.config -with-tower …`。T3 既有 golden 也含它（若沒有，表示 T3 的 profile 由 nextflow.config 給；那就只在 `site_profile`／站台 config 指定 singularity 的 CE 加——executor 以既有 golden 為準，二者擇一並在 ledger 寫明）。
8. **站台端驗證**：`_check_ce` 直接重用 `compute_envs._module_problem`／`_var_problem`（import，不重抄），所以 `modules=["a;b"]` 在站台也被拒並點名 `modules`。裁決 0 的「只驗形狀」撤回。
9. **假 CE 一律用裁決 1 的值**（modules 只有 Nextflow 一項）；test_station_envs 既有 NANO4 常數不動也不混用。
10. **其餘細節**：`module load` 失敗要讓腳本停下（`module load X || exit 1`），位置在 `umask 077` 之後、任何 nextflow 指令之前；舊 bundle 沒有 `pipeline_source` → 視為 `{"kind":"remote"}`；`sitePipelines` 有重複 (pipeline, revision) 時取第一項（CE 驗證已在 ce-nano4-keys 拒絕重複則不會發生）；`-resume` 照現在的位置不動。
