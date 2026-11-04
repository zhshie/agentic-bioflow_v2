---
id: resume-cache-miss
title: 帶修改的續跑（resume）不該讓不相關的 task 重算：先鎖住平台這一側「續跑只改該改的」，並備好 nano4 三次續跑＋-dump-hashes 的診斷程序
tier: C
kinds: backend
risk: M
lane: L46-resume-cache
branch: fix/resume-cache-miss
base: origin/v3@62c91293；開工前 `git fetch` 並重查行號
source: dev-queue backlog `resume-cache-miss`（2026-10-25 nano4 觀察；2026-10-26 維護者「都ok」核可診斷）
---

# resume-cache-miss

> 只有計畫、沒有程式。C 級 backend；範圍不含 `.github/`、`hooks/`、`platform/abf_station/` 以外的保護路徑，但**會**讀（條件式才改）`platform/abf_station/launch.py`——`platform/abf_station/` 在 README 的 L 級清單內，若第二階段真的要改它，風險升為 L（見裁決 2）。本片預設只加測試與文件，風險 M。

## 目標
nano4 上對 r6（`/work/u9613010/runs/runs/ampliseq_day5_nano4_r6`）帶修改續跑，72 個 task 重算了 71 個（連看似無關的 FASTQC 雜湊都變了）。本片做兩件事：(1) 用離線測試證明平台產生的續跑檔案「與原送出相比只差該差的東西」，排除或定位平台端原因；(2) 寫好 nano4 診斷程序（三次便宜續跑＋`nextflow -dump-hashes` 比對），讓操作員一次跑完就知道是平台端還是 Nextflow／站台端。使用者意義：「續跑」才真的省時數。

## 維護者原話（verifier 出題用）
- backlog 原文（2026-10-25）：「nano4: resume of r6 with edits re-ran 71/72 tasks (FASTQC hash changed though unrelated). Diagnose with 3 cheap resumes (no edit / param only / config only; each needs maintainer y), then nextflow -dump-hashes diff. Folder /work/u9613010/runs/runs/ampliseq_day5_nano4_r6.」
- 2026-10-26 維護者：「都ok」（核可照上述方式診斷；每次續跑仍要他本人確認）。
- 專案安全底線（既有）：每個寫入都經人工確認管道；未確認不改變資料。本片不新增寫入路徑。

## 範圍：檔案（只准改這些）
- 新檔 `platform/tests/test_resume_cache_stability.py`
- `docs/TESTING.md`（只在既有「resume」相關手動案例節〔約 l.437-441〕之後新增一節「續跑快取診斷（nano4）」；不改既有段落）
- 新檔 `scripts/nf_hash_diff.py`（選用，離線小工具：讀兩份 `-dump-hashes` 輸出，列出第一個不同的欄位；純標準函式庫，不連網、不連叢集）
- `platform/abf_station/launch.py`：**預設不改**。只有離線測試證明平台端確實造成差異時才可動 `_params_yaml`／`render_resume`／`_head_script` 的相關行，且須先走裁決 2。
- 既有測試只准「加案例」：`resume_harness.py`；不准刪或放寬 `test_resume_render.py`、`test_resume_edit_params_station.py`、`test_launch_bundle.py` 的斷言。
- **不准碰**：`web.py`、`static/`、`platform/abf_platform/jobs.py`、`.github/`、dev-queue.json、`docs/PITFALLS.md`（新增條目是 executor 完成後另案由維護者決定）。

## 作法
### 第 1 階段：離線（executor 全做；不連 nano4）
先讀實際渲染程式（PITFALLS 第 14 條精神）：`_head_script`（約 l.476-525）、`render_resume`（約 l.1547）、`_normalize_overrides`（約 l.1514）、`_params_yaml`（約 l.463）。已知事實：
- 無修改的續跑：head 與原送出「只差 job 名、`-name`、加上 `-resume <session>`」，沿用同一個 `params.yaml` 與 `nextflow.config`（檔案不重寫）。
- 有修改的續跑：另寫 `params-<N>.yaml`（原參數＋changed 鍵，`sorted(merged)` 排序、`input`／`outdir` 以 `run_folder` 重寫）與選用 `extra-<N>.config`；head 的 `-params-file` 改指 `params-<N>.yaml`，`-c extra-<N>.config` 排在 `-c nextflow.config` 之後。
- 要驗證的假設（H 系列，逐條寫成測試，能排除就排除）：
  - H1 `params-<N>.yaml` 與 `params.yaml` 在「沒被改的鍵」上逐字相同（含引號、浮點 `repr`、布林、排序）；若原 `params.yaml` 是舊版渲染器產生，重新渲染可能與它不同（例如 `repr` 對 `1e-05`）。
  - H2 `input`／`outdir` 的字串在兩份檔相同（路徑未被正規化成另一個樣子）。
  - H3 head 行除 `-name`、`-resume`、`-params-file`、`-c extra-N.config` 外，其餘（`-c "$NFCORE_SITE_CONFIG"`、`-c nextflow.config`、`-with-tower`、module 載入、環境變數）與原送出逐字相同。
  - H4 `render_resume` 用的 `origin` 是原送出的 bundle，不是重新計算的（模組版本、`NXF_*` 環境與原本一致）。
  - H5 `extra-<N>.config` 只含使用者給的設定加平台註解，沒有帶入會改變 task 雜湊的鍵（`process.container`、`env`、`ext.args`）——以測試斷言平台**自己**不寫這類鍵。
- 結論寫進 ledger：每條 H 標「已排除（附測試名）」或「平台端成立（附輸出差異）」。

### 第 2 階段：nano4 診斷（操作員用 skill `nano4-acceptance` 執行；本片只寫程序）
寫進 `docs/TESTING.md` 新節，三次續跑各需維護者本人確認（對 r6 資料夾，每次都記 session id、`get_run` 的 CACHED／總數）：
1. 無修改續跑 → 預期幾乎全 CACHED。若這一步就大量重算 → 原因在 session／工作目錄／檔案時間戳（站台或 Nextflow 端），與「修改」無關。
2. 只改一個下游才用的參數 → 只該重算受影響的 task。
3. 只加 `extra_config`（例如 `process.memory`）→ 預期全 CACHED（memory 不入雜湊）。
最後對 r6 工作目錄用 `nextflow -dump-hashes`（`-log`／`.nextflow.log` 內的 hash 欄位）取修改前後兩份，餵 `scripts/nf_hash_diff.py` 找第一個不同欄位（輸入檔路徑／大小／mtime、container、script、env 哪一個）。這一步在 nano4 登入節點由操作員手動執行；唯讀，不寫入平台。

### 第 3 階段：修正（條件式，可能另開一片）
- 若 H 系列有平台端成立 → 本片先寫紅測試，再依裁決 2 決定是否在本片內改 `launch.py`（會升 L）。
- 若 H 全排除、且診斷顯示是 Nextflow／站台行為（如輸入檔 mtime、`cache = 'lenient'`）→ 本片只留文件與測試，建議的設定（例如在 `OVERWRITE_BLOCK` 外另議 `process.cache`）列為後續片，**不在本片動 `OVERWRITE_BLOCK`**。

## 失敗先行測試
新檔 `platform/tests/test_resume_cache_stability.py`，用 `resume_harness`／`launch_harness` 既有夾具（ampliseq 站台模組、`NFCORE_AMPLISEQ_HOME`）。這些測試描述「應該成立」的不變量，若某條現在就綠，代表該假設已被排除，仍保留作回歸護欄；真正紅的那條就是平台端缺陷。紅綠狀態貼進 ledger。
- `test_resume_without_edit_reuses_origin_files`：無 overrides → `render_resume` 只回 `head-<N>.sh` 一個檔；其餘行與原 head 逐行相同，僅 `#SBATCH -J`、`-name`、`-resume` 不同。
- `test_resume_with_param_edit_keeps_unchanged_params_byte_identical`（H1、H2）：origin 的 `params` 含字串、整數、浮點（`1e-05`）、布林、含引號與非 ASCII 的字串；改一個鍵 → `params-2.yaml` 對 `params.yaml` 逐行比對，只有被改的那一行不同。
- `test_resume_params_yaml_matches_origin_render`：用 `_params_yaml(origin_params, run_folder)` 重算的文字與原 bundle `files["params.yaml"]` 逐字相同（確認重新渲染不漂移）。
- `test_resume_head_differs_only_in_allowed_flags`（H3）：有 param 與 extra 修改時，把 head 末行拆 token，移除 `-name X`、`-resume S`、`-params-file F`、`-c extra-N.config` 後，與原 head 末行 token 相同。
- `test_resume_env_and_modules_match_origin`（H4）：`module load`、`export` 行集合與原 head 相同。
- `test_resume_extra_config_has_no_hash_affecting_keys`（H5）：未帶 extra → 無 `extra-N.config`；帶 `process.memory` → 檔案內容恰為平台註解行＋使用者文字，不含平台自加的 `container`／`env`／`ext`。
- `test_resume_unconfirmed_changes_nothing`：未經本人確認，資料庫沒有新 run／job；沿用 `test_resume_platform.py` 的確認管道夾具。
- `test_nf_hash_diff_reports_first_difference`（若做 `scripts/nf_hash_diff.py`）：兩份人造輸出只差 `container` → 報 `container`；完全相同 → 報無差異；缺欄位不拋堆疊。

### 允許的斷言變動（既有測試釘住的東西，全列出）
本片預設不改程式輸出，下列既有測試必須原樣綠；除「加案例」外不准刪、放寬或改期望值。
- `test_resume_render.py:13`（golden head scripts，`fixtures/golden_head_scripts.json`）：續跑輸出逐位元組不變。
- `test_launch_bundle.py` l.495、771、779、790：`-resume %s` 位置與 `-name run-one-a2`（head 行順序 `exec nextflow run <target> -resume <sid> -name …`）。
- `test_resume_edit_params_station.py` l.31、335、449：帶修改的 head 行全文與 argv（`-params-file params-2.yaml`、`-c extra-2.config`）。
- `test_resume_edit_params_docs.py` l.89、123：說明文字 `-resume <session id>`、`-params-file params-2.yaml`、`-c extra-2.config`。
- `test_resume_platform.py`、`test_resume_scope.py`、`test_resume_entrypoints.py`、`test_resume_lineage.py`、`test_station_resume.py`、`resume_harness.py`（FILE_NAMES l.13）。
- `test_cleanup_offer.py:276`（「刪掉之後這個 run 不能再續跑（-resume）」整句）。
- 若第 3 階段改了 `launch.py`：以上 head 行斷言的任何變動須在裁決 2 取得維護者同意，並逐條列在 ledger。

## 完成標準（done when）
- 新測試檔全綠（或紅者即為證明的平台端缺陷，附輸出差異）；全套 `tests/run_all.sh` 全綠（已知環境紅見 dev-plans README）。
- ledger 有 H1–H5 逐條結論表；`git diff --stat` 只含範圍內檔；既有斷言除「允許的斷言變動」外沒被刪或放寬。
- `docs/TESTING.md` 新節含上述三次續跑與 `-dump-hashes` 的具體指令、每次要記的欄位、判讀表（哪個結果指向平台端／站台端）。
- 本機不跑 nano4；診斷由操作員之後執行（見環境事實）。M 級：沒有網頁畫面變動，不需截圖。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。單檔測試：`python -m pytest platform/tests/test_resume_cache_stability.py`（Python：`C:/Users/marvi/AppData/Local/Programs/Python/Python312/python.exe`）。
- 觀察出處：dev-queue backlog 2026-10-25（r6 資料夾 `/work/u9613010/runs/runs/ampliseq_day5_nano4_r6`，72 個 task 重算 71 個，FASTQC 雜湊變了）。nano4 站台模組 ampliseq 2.18.0；站台設定變數 `NFCORE_SITE_CONFIG`；唯讀測試資料 `/work/envstack/apps/application/biology/nf-core/testdata`。出處：`memory/reference/madcowork-nfcore-nano4-site-notes-2026-10-20.md`。
- 續跑與原送出共用同一個資料夾，Nextflow 靠該資料夾 `.nextflow/cache/<session>` 找快取；`-resume <session id>` 由平台帶入。Nextflow task 雜湊含：process 腳本、輸入檔（路徑＋大小＋mtime，預設 `standard` 模式）、container、env、`ext.args`、`task.cpus` 等不含 memory/time。修改的 param 若是上游才用的，下游重算是**正常**，所以第 2 步要選「下游才用」的參數。
- **nano4 診斷由操作員用 skill `nano4-acceptance` 做，每次續跑維護者本人確認**；本片不連 nano4。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- **PITFALLS 已查（`docs/PITFALLS.md`；`docs/solutions/` 不存在），相符項**：
  - 第 6c 條「A queued job cannot be resized here; `scontrol update` is refused outright」：其中記載 `tw runs relaunch` 預設續跑、同一 Session ID 的三次 bacass run 最後報 8/9 `CACHED`——證明在 Taiwania 端續跑能重用快取，nano4 的 71/72 是反例，要與之對照。
  - 第 14 條「Before writing a check, read the pipeline's module source」：先讀實際 `nextflow.config`／渲染程式再寫假設，夾具用真實寫法。
  - 第 50 條與 `OVERWRITE_BLOCK`（launch.py l.71）：每份渲染的 `nextflow.config` 結尾都附 `report.overwrite`／`timeline.overwrite`；這兩個設定不影響 task 雜湊，本片不得動它。
  - 第 52／53 條：唯讀映像快取與本地路徑不可加 `-r`；head 行不得動這兩處（本地模組走 `"$NFCORE_AMPLISEQ_HOME"`）。
  - 第 54 條「On nano4 an offline site, broken site images and the iGenomes config each break a run」：站台設定只留 `NFCORE_SITE_CONFIG`；續跑不得移除站台 `-c`。
  - 第 11 條：工作目錄須在計算節點看得到的檔案系統；續跑沿用原資料夾，不另換。
  - `umask 077` 在唯一的 `sbatch` 呼叫前：不得動。

## 不做
- 不改 `OVERWRITE_BLOCK`、不加 `process.cache = 'lenient'` 等站台／Nextflow 快取設定（診斷出站台端原因後另開一片，由維護者裁示）。
- 不改 `relaunch`（原樣重跑本來就不重用快取）。
- 不改 MCP／網頁的續跑畫面與參數（`web.py`、`mcp_server.py`、`static/`）。
- 不新增 PITFALLS 條目（診斷結論出來後，由 developer-agent 與維護者另案決定）。
- 不在 nano4 自動執行續跑；三次續跑都由維護者本人確認、操作員手動做。
- 雲端（gcb／aws／azure／k8s）的續跑快取行為。

## 裁決
1. **診斷由誰、何時做？** 建議：操作員在本片合併後用 `nano4-acceptance` 做三次續跑與 hash 比對，結果貼回 ledger；executor 只交離線測試與文件程序。理由：每次續跑需維護者 y，executor 不能代答。
2. **離線測試證明平台端有缺陷時，同片修還是另開一片？** 建議：另開一片（升 L，因為動 `platform/abf_station/`，需爆炸半徑證明與 Opus 對抗審）；本片把紅測試與差異輸出留在 ledger 即算完成診斷。
3. **要不要做 `scripts/nf_hash_diff.py`？** 建議：做，小而純離線，免得操作員手動比對數千行 hash 欄位；若維護者不要多一個腳本，刪掉該檔與對應測試，TESTING.md 改寫成手動 `diff` 指令。
4. **無修改續跑（診斷第 1 步）本身若已大量重算怎麼辦？** 建議：本片停在「定位為站台／Nextflow 端」，不猜修法；回報維護者，下一片另議。

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
