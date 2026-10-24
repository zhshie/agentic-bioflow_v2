# 畫布 017d：組合流程經同一確認流程送出 progress ledger

## 進度
- [x] module_sources + 資料檔（TC-066 至 083）：`module_sources.py`、`data/nf-core-module-sources.json.gz`、`pyproject.toml` 多一個 glob `data/*.json.gz`。
- [x] 內容包／head.sh／站台寫檔（TC-085 至 124、170、171）：`abf_station/launch.py` 的 `render_bundle(..., composed=None)`、`_head_script` 第三種來源、`run_launch` 重算與同一次 tar 寫 `pipeline/…`、`run_resume`／`render_resume` 拒絕組合。`golden_head_scripts.json` 只加 `composed` 一個鍵。
- [x] 平台側（TC-001 至 064、125 至 144、166 至 169、172、174）：`pipeline_launch.py`（`build_project`、`prepare`）、`build.py`（保留名稱、`composed` 參數、續跑／重跑拒絕、確認畫面）、`actions/__init__.py`（`request_pipeline_launch`、共用的 `_finish_launch`、`_sheet_and_area`）。
- [x] 文件：`docs/PLATFORM.md`（`### Launching a composed pipeline`、`### What was handed over` 補一句）、`docs/TESTING.md`（nano4 手動驗收，裁決二-3）。

## 資料檔（TC-081、159；裁決 A、8）
- 來源：nf-core/modules @ 5ed90b42e78410e7411e9c6bdfeff33226d6c58e（shallow fetch，`core.autocrlf=false` 確保是上游原位元組；第一次在 Windows 預設換行轉換下產生過 CRLF 的版本，發現後重做，所以 snapshot 也把含 CR／ESC／雙向控制字元的模組標 unsupported）。產生指令：`python -m abf_platform.module_sources snapshot --modules <checkout> --sha <sha> --out abf_platform/data/nf-core-module-sources.json.gz`。
- 實際大小：759290 bytes（約 0.72 MiB），遠低於 8 MiB。gzip 壓縮等級用 8 而不是 9：`tests/jev_test.sh` 的 TC-085 用不分大小寫的 `grep -rli jev platform` 掃二進位檔，等級 9 的輸出剛好含有 `jev` 三個位元組（純屬巧合）會讓那個既有測試變紅；等級 8 沒有。日後重生資料檔若又撞到，換一個壓縮等級即可（同一個等級對同一個 sha 仍逐位元相同）。
- 模組數 2116（與目錄快照逐一對上）；unsupported 4 個，其餘 2112 個可用：`custom/addmostsevereconsequence`、`custom/addmostseverepli`（resources 底下有巢狀檔名 `resources/usr/bin/…`，形狀不符）、`last/dotplot`（main.nf 含 TC-072 形狀的叢集路徑，不改上游原檔所以整個標 unsupported）、`blobtk/create`（main.nf 含控制字元）。含 `include {` 或 `workflow ` 宣告的模組：0 個（對這份資料掃過）。

## 標準答案的手算推導（TC-154）
標準答案寫在 `platform/tests/fixtures/pipeline_launch/fastqc_multiqc/`，是我依計畫文字用手寫成，沒有用被測程式的輸出回填。
- `main.nf`：017b 黃金 `main.nf`（`tests/fixtures/compose/fastqc_multiqc/main.nf`）只動兩處。①被換掉的一行：`    ch_qc_in0 = Channel.empty()  // OPEN INPUT: qc input 0 (meta, reads)` → `    ch_qc_in0 = ch_rows.map { row -> [ [id: row.sample], file(row.reads, checkIfExists: true) ] }`。理由：fastqc 的輸入 0 有兩筆記錄 `meta`（map）與 `reads`（file），有 meta 所以用 `[ … ]` 包起來，meta 在第一格寫 `[id: row.sample]`，file 寫 `file(row.reads, checkIfExists: true)`。②加進去的一行：`workflow {` 之後第一行 `    ch_rows = Channel.fromPath(params.input).splitCsv(header: true)`（計畫 B 節 2）。其餘每個字元不變。
- `nextflow.config`：017b 黃金 `nextflow.config` 原文，後面空一行，接平台寫的一段：註解行以 `// added by the platform at launch` 起頭，然後 `process.publishDir = [ path: { "${params.outdir}/${task.process.tokenize(':')[-1].toLowerCase()}" }, mode: 'copy' ]`（裁決 5；`task.process` 取最後一段並轉小寫，與 nf-core 自己的 modules.config 寫法同形）。
- 檔案清單：`main.nf`、`modules.json`（與 017b 黃金相同，單元測試直接拿 017b 夾具比）、`nextflow.config`、`modules/nf-core/fastqc/main.nf`、`modules/nf-core/multiqc/main.nf`（兩個模組都沒有 `templates/` 與 `resources/`）。
- `golden_head_scripts.json` 的 `composed`：照 `nano4` 的稿子手改兩處（拿掉第二行 `module load`，最後一行改成 TC-092 的字樣）。
- TC-136 的 `bundle_sha256` 寫死值 `1d240f37…06b3`：在 base（54900a2）的檔案上跑 `test_launch_bundle.render()` 算出來的，不是新程式算的。

## 允許更新的既有斷言（TC-145、146）
- `test_pipelines_store.py::test_the_files_owned_by_other_work_do_not_mention_pipelines`：**沒有改**。計畫允許把 `actions.pipelines` 拿掉，但我的設計（`actions/__init__.py` 只 `from .. import pipeline_launch`，`pipeline_launch.prepare` 在函式裡才 import `actions.pipelines`）讓 `actions/__init__.py` 裡根本沒有那個字串，所以沒有需要放寬的東西。
- **計畫沒列、但計畫自己的改動逼出來的兩處既有測試修改**（跑全套才發現，各只動一個字面值，沒有刪、放寬或跳過任何斷言）：
  - `test_web_parity.py` 的 `INTERNAL` 表加 `"request_pipeline_launch"`：計畫要求在 `actions/__init__.py` 新增這個公開函式，而該測試要求動作層每個公開名稱都在四張表之一（檔案自己的註解寫「加一個名字就要改這個測試、ledger 與計畫」）。對外的 MCP 工具與網頁路由本任務不加（017e 才會把它從 `INTERNAL` 移到對應的表）。計畫的「必須確認仍綠、不准改」清單與這一點互相矛盾，請 developer-agent 確認。
  - `test_guidance.py::test_tc406_package_data_covers_the_skills` 的字面值多 `"data/*.json.gz"`：計畫要求 `pyproject.toml` 的 `package-data` 多這個 glob（TC-083），而該測試比對整行。
- 另外 `test_scope.py::test_tc061` 抓到 `pipeline_launch.py` 一開始 import 了 `abf_station`（平台層原始碼不准出現 `station` 字樣）；改成經 `build.bundle_mod` 取用，測試本身沒動。
- `test_launch_bundle.py`：只在檔尾新增測試；`test_station_launch.py`：沒動；`golden_head_scripts.json`：只加 `composed`（JSON 最後一個鍵後多一個逗號是唯一動到既有那一行的地方，既有四個鍵的值一個位元都沒變）。

## 與計畫不同／要注意的地方
- 裁決二-1：`actions/__init__.py` 內沒有 `compose`、`composed`、`abf-composed` 字樣；對 nf-core 送出擋 `abf-composed/` 假名稱的檢查放在 `build.py`。
- 裁決二-2：`head.sh` 最後一行固定明寫 `-c <run_folder>/pipeline/nextflow.config`（站台的 `-c` 在前、最後是 `-c nextflow.config`）。
- Google Batch 環境不支援組合（`render_bundle` 的 GCB 分支遇到 `composed` 就丟 `BundleError`），計畫沒寫，因為 GCB 的內容包形狀不同；不屬於範圍擴大（只是白話拒絕）。
- `build_project` 對 `include {`／`workflow` 宣告的偵測用列首的正規式（`workflow.` 之類的屬性存取不算），代碼 `UNSUPPORTED_MODULE` 同時在錯誤物件的 `code` 與訊息文字裡。

## 未驗證（手動）
- nano4 實跑 fastqc→multiqc：專案的 `nextflow.config` 是否被讀到、`publishDir` 是否有輸出、容器由 nano4 線上拉取。步驟寫在 `docs/TESTING.md`。
- 舊版站台代理收到組合包的拒絕訊息：預期是代理重算不出 `project`、比對失敗、拒絕（訊息不精確：「內容與代理依自己的設定重新產生的不一致」）。PR 說明要寫「組合送出需要新版站台代理」。

## 不需要 migration 的理由（TC-139）
內容包本來就是 JSON，存在 `confirmations.bundle_json` 與 `jobs.args_json`（TEXT 欄）；新鍵 `project` 與新的 `pipeline_source` 形狀只出現在新送出的包裡。沒有改任何表、欄位、CHECK 或 `STATE_SCHEMA`；舊的 `platform.db` 與舊的內容包原樣可用。唯一的部署變動是 `pyproject.toml` 的 `package-data` 多一個 glob 與一個資料檔。
