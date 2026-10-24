---
id: 017d-launch-composed
title: 把存好、驗證過的組合送去跑：走和 nf-core 送出同一條確認流程，內容包帶著專案檔與 nf-core 模組檔，站台代理把它們寫進這次 run 的資料夾再啟動（續跑與原樣重跑這版不做）
tier: B
kinds: backend
lane: L5
base: v3
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 4（017d，第 158 行）；依 017a（catalogue.py）、017b（compose.py、actions/pipelines.py）、017c（validate.py，PR #178 已合）與 M1-02（站台 pipeline 的本地路徑啟動，已合）
---

# 017d-launch-composed

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/017d-launch-composed/plan.md`。**只處理本任務**。
> ⚠️ **前置**：從最新的 `origin/v3`（寫本檔時是 `174ed8f`）開分支；017a、017b、017c 已在 v3。PR #176（目錄帶 `optional`）已合；PR #179（必填而沒接的輸入變 error）合不合都不影響本任務（入口節點的必填輸入本來就維持 warning，見裁決 4）。
> 與 017a／017b／017c 同一個原則：**不新增 MCP 工具、不加網頁路由、不碰 `mcp_server.py`、`web.py`**——對外的名字（`launch_pipeline`）留到 017e 一次開。本任務只交出動作層函式與站台側行為。
> 與總表（replan 第 158 行）的差異全部列在「裁決」，以「裁決」為準：**不用 `project_tar`（改成文字檔的對照表）、專案檔寫進每個 run 自己的資料夾（不共用 `<workDir>/pipelines/`）、不做容器檢查、續跑與重跑不支援**。

## 目標
讓一個**已存下來、現在驗證仍沒有 error** 的組合版本，經過和 nf-core 管線**完全相同**的確認流程送去 nano4 跑：平台算出內容包（樣本表、參數、環境、`head.sh`，再加上這張圖的專案檔），產生確認頁 `/c/<rid>`，本人按「送出」後變成一個 `launch_nextflow` 工作，站台代理領走、用自己的設定重算一遍內容包、一模一樣才動手：把專案檔寫進 `<run_folder>/pipeline/`、再 `sbatch head.sh`；`head.sh` 最後一行改成啟動本地的 `<run_folder>/pipeline/main.nf`。進度回報（`-with-tower`）、站台設定檔（`siteConfigVars`）、擁有者規則、結果頁都沿用，不另開一條路。**平台不連網、不啟動程式；啟動指令的字樣只在 `abf_station/launch.py`。**

## 維護者原話（verifier 出題用）
- 「拖模組、連線、填參數、驗證、送去跑、匯出 zip、版本紀錄與分享；不做巢狀子流程。」（10-21 裁示 5）→ 「送去跑」是畫布的一等動作；這張票交出它的後端。
- 「拖拉畫布做到 GenXflo 程度再多兩件（直接送去跑、送前三層驗證）。」（裁示 5）→ 送出前要過驗證：有 error 的版本不能送。
- 總表 017d：「done：版本頁 launch → `/c/<rid>` → 站台跑起、結果頁可見。」→ 本任務交出「launch 動作 → 確認頁 → 工作 → 站台跑起」；版本頁按鈕是 017e。
- 裁示 3：「啟動＝借國網零件、自己啟動：`nextflow run $NFCORE_<P>_HOME -profile singularity -c $NFCORE_SITE_CONFIG -c $NFCORE_SITE_REFERENCES`，不走 `nfcore-submit`」→ 站台設定檔照舊用 `siteConfigVars` 加進命令列，組合管線只是把「跑哪個目錄」換成本地專案。
- 憲法 6／ADR 0006（每個寫入要本人答應）與 10-14 裁示（「`sbatch` 與 abf launch 不需再確認」是指代理端；**平台確認頁上本人按送出 `/c/<rid>` 一直都在**）→ 組合送出也走 `_ask`，沒有任何自動送出。
- 憲章原則 2（`test_scope.py` TC-071、`tests/no_second_run_state_test.sh` 的 `LAUNCH_ALLOW`）：平台不啟動程式，啟動 Nextflow 的那串指令在平台程式碼裡只准出現在 `platform/abf_station/launch.py` 一處 → 平台只組資料，站台負責成字與啟動。
- 擁有者規則（`docs/PLATFORM.md` 第 473 行起「Whose it is」）：別人的與不存在的回一樣的話。

## 範圍：檔案（最終版，只准改這些）
新增：
- `platform/abf_platform/module_sources.py`（新：讀 `data/nf-core-module-sources.json.gz`；`load`、`files_for`；`snapshot` 子命令，供維護者重生資料。只用標準函式庫；不連網）
- `platform/abf_platform/data/nf-core-module-sources.json.gz`（新：與目錄快照**同一個 nf-core/modules commit**（`5ed90b42e78410e7411e9c6bdfeff33226d6c58e`）每個模組的 `main.nf`、`templates/*`、`resources/*` 文字檔；見作法 A）
- `platform/abf_platform/pipeline_launch.py`（新：純函式 `build_project` ＋ 動作層用的 `prepare`；名字與內文**不得**含 `compose` 子字串，理由見環境事實）
- `platform/tests/test_module_sources.py`、`platform/tests/test_pipeline_launch.py`、`platform/tests/test_pipeline_launch_station.py`（新）
- `platform/tests/fixtures/pipeline_launch/`（新：`fastqc_multiqc/`＝`graph.json`＋樣本表＋手算的標準答案 `main.nf`／`nextflow.config`／檔案清單；`unsupported/`）
- `specs/017d-launch-composed/ledger.md`（新）

修改：
- `platform/abf_launch/build.py`（改：`prepare_launch` 加 `composed=None`；保留擁有者名稱 `abf-composed`；`_predecessor` 對組合的 run 拒絕續跑／重跑；`launch_screen` 對組合多顯示專案）
- `platform/abf_station/launch.py`（改：`render_bundle(..., composed=None)`；`_head_script` 多一種來源；`run_launch` 重算時帶 `composed`、把專案檔寫進 `pipeline/`；專案檔形狀檢查；`render_resume` 遇到組合的 origin 拒絕）
- `platform/abf_platform/actions/__init__.py`（改：新增 `request_pipeline_launch`；把 `request_launch` 的後半段抽成共用的私有 `_finish_launch`，兩者不重複邏輯）
- `platform/pyproject.toml`（改：`package-data` 加 `data/*.json.gz`，只此一處）
- `platform/tests/fixtures/golden_head_scripts.json`（改：**只加**一個 `composed` 鍵，既有鍵一個位元都不動）
- `platform/tests/test_launch_bundle.py`、`platform/tests/test_station_launch.py`（改：只新增測試）、`platform/tests/test_pipelines_store.py`（改：只改「允許更新的既有斷言」那一處）
- `docs/PLATFORM.md`（改：`## Composed pipelines` 補 `### Launching a composed pipeline`；`### What was handed over` 補一句；見裁決 11）

**不准動**：`store.py`（不加表、不改 `STATE_SCHEMA`、不改 `jobs` 的 CHECK、`launches` 不加欄）、`jobs.py`、`confirm.py`、`compose.py`、`catalogue.py`、`validate.py`、`actions/pipelines.py`、`data/nf-core-modules.json`、`mcp_server.py`、`web.py`、`web_board.py`、`abf_station/handlers.py`／`rules.py`／`agent.py`、`constraints.txt`、`tests/no_second_run_state_test.sh`（它的 `LAUNCH_ALLOW` 維持只有 `abf_station/launch.py` 一條）。

## 作法

### A. 模組檔從哪來（回答：不在叢集上、不在送出當下連網）
**證據**（細節見環境事實）：①`head.sh` 不設 `NXF_OFFLINE`（全 repo 只有測試夾具設），nano4 的登入與計算節點直連外網，但台灣杉三是防火牆＋relay，不能假設外網；②017b 的 `main.nf` 用 `include { X } from './modules/nf-core/<path>/main'`，所以模組檔**必須存在於專案資料夾裡**，Nextflow 不會替本地腳本去 GitHub 抓；③平台主機的測試必須無網路（017b、017c 全是純函式）。結論：**平台在建內容包時，從它自己帶著的資料取出這張圖用到的模組檔，放進內容包；站台只寫檔，不抓檔。**

做法（仿 `catalogue.py` 的快照指令與同一條更新規則）：
1. `module_sources.py` 的 `snapshot` 子命令：`PYTHONPATH=platform python -m abf_platform.module_sources snapshot --modules <nf-core/modules 的 checkout> --sha <sha> --out platform/abf_platform/data/nf-core-module-sources.json.gz`。每個 `modules/nf-core/<path>/` 取 `main.nf`，以及該資料夾下 `templates/` 與 `resources/` 的**文字檔**（能以 UTF-8 解碼、不含 NUL）；**不取** `meta.yml`、`environment.yml`、`tests/`。輸出 `{"source": "nf-core/modules", "sha": <sha>, "modules": {<path>: {"files": {<相對路徑>: <文字>}, "unsupported": <null 或理由>}}}`，鍵排序、`ensure_ascii=False`、gzip 時 `mtime=0`，同一個 sha 產出**逐位元相同**的檔。
2. `unsupported` 的理由：模組資料夾有 `bin/`（Nextflow 要執行權限，內容包不帶）、有取不下來的二進位檔、檔名不合形狀、任一檔含 TC-072 形狀的路徑（`(/home|/work|/scratch|/staging|/lustre)/名字/`；不改檔，整個模組標 unsupported，因為改了就不再是上游原檔）、單檔超過 200,000 字元。launch 遇到 unsupported 的模組 → 點名那個模組拒絕（裁決 8）。
3. 載入：`module_sources.load(path=None)`（`functools.lru_cache`）；`files_for(paths, sources=None)` → `{"modules/nf-core/<path>/<相對路徑>": 文字}`，任一 path 不在資料裡或 unsupported 就丟 `ValueError`（中英說明）。**`load()` 檢查 `sources["sha"] == catalogue.load()["sha"]`**，不相等就拒絕（圖裡的 `sha` 是目錄的 sha，兩份資料不能各走各的）。
4. 大小：**估計**約 2116 個模組、平均幾 KB 的 `main.nf`，壓縮後約 1.5～3 MB（**未量**；ledger 要記實際大小）。**壓縮後超過 8 MiB 就 BLOCKED 回報**，不要硬收進 repo（備案見裁決 2）。更新快照是一個獨立的 A 級 PR。
5. executor 需要網路 clone `nf-core/modules` 才能生資料檔；沒網路 → BLOCKED，不要手寫、不要只放幾個模組。

### B. 專案檔怎麼組（`pipeline_launch.build_project`，純函式）
`build_project(canonical, name, version, header, *, data=None, sources=None) -> {"project": {相對路徑: 文字}, "project_sha256": str, "path_columns": [..], "columns": [..]}`，錯誤丟 `ProjectError`（訊息中英、說怎麼改）。不讀資料庫、不連網、不寫檔。
1. `compose.render(canonical, name, version, data)` 取 `main.nf`、`modules.json`、`nextflow.config` 與 `open_inputs`（**不改 `compose.py`**；渲染結果與 017b 逐字相同）。
2. **把沒接的輸入接到樣本表**（`open_inputs` 是 017b 留給 017d 的洞：它們現在是 `Channel.empty()`，不處理的話送出的 run 會空轉成功；見 017b 裁決 3）。規則（裁決 3）：
   - 對每個 `open_inputs` 項，用 `catalogue.describe` 取該通道的輸入記錄（依目錄順序）。每筆記錄產生一個元素：`map`（meta，必在第一格）→ `[id: row.sample]`；`file`、`directory` → `file(row.<名字>, checkIfExists: true)`；`string` → `row.<名字>`；`integer` → `(row.<名字> as Integer)`；`float` → `(row.<名字> as Double)`；`boolean` → `row.<名字>.toBoolean()`；其他型別（`list`、缺漏）→ `ProjectError` 點名節點、輸入編號、記錄名。通道只有一筆非 meta 記錄且無 meta → 直接用該值，其餘用 `[ ... ]`。
   - `<名字>` 必須符合 `^[A-Za-z_][A-Za-z0-9_]*$`（程式碼檢查，不符 → `ProjectError`）；Groovy 只由這個封閉的樣板與通過檢查的識別字組成，**使用者的任何文字都不會進 Groovy**。
   - `optional` 為 true 的記錄：樣本表標題列沒有該欄 → 該元素寫 `[]`；非 optional 的記錄標題列沒有該欄 → `ProjectError`，列出「樣本表需要這些欄：sample、reads…（缺：…）」。有 meta 的通道一律需要欄 `sample`。
   - 不同節點的開放輸入若記錄名字相同（例：兩個工具都吃 `reads`）→ **共用同一欄**；名字相同但型別不同 → `ProjectError`。
   - 把 017b 渲染出的每一行 `    ch_<id>_in<i> = Channel.empty()  // OPEN INPUT: …` **逐字**換成 `    ch_<id>_in<i> = ch_rows.map { row -> <元素> }`，並在 `workflow {` 後第一行加 `    ch_rows = Channel.fromPath(params.input).splitCsv(header: true)`。找不到預期的那一行 → `ProjectError`（017b 若改了行形狀，這條會紅，是設計）。沒有任何開放輸入 → 不加 `ch_rows`。
   - 只用 `params.input` 這一份樣本表（`params.yaml` 的 `input` 本來就由送出流程固定為 `<run_folder>/samplesheet.csv`）。
3. **加一段平台寫的設定到專案的 `nextflow.config` 末尾**（標明 `// added by the platform at launch`）：`process.publishDir`，把每個 process 的輸出複製到 `${params.outdir}/<process 名小寫>`（nf-core 模組本身不發佈輸出，發佈寫在各 pipeline 的設定裡；沒有這段，run 成功但 `results/` 是空的，結果頁沒東西看；裁決 5）。
4. 模組檔：`module_sources.files_for(用到的模組 path 集合, sources)` 取得 `modules/nf-core/<path>/…`；`modules.json` 也放進專案（上游 sha 的紀錄，Nextflow 不用，給人查）。
5. 組成 `project`＝`{相對路徑: 文字}`，鍵含 `main.nf`、`nextflow.config`、`modules.json`、`modules/nf-core/…`。`project_sha256 = sha256(common.canonical_json(project))`。大小：全部檔案 UTF-8 位元組總和 ≤ 2 MiB、檔案數 ≤ 2,000（裁決 6）。
6. `path_columns`：樣本表裡對應 `file`／`directory` 記錄的欄名（交給既有的 `_check_samplesheet`，使這些欄的每個格子都被當路徑檢查、必須在允許讀取的範圍內）。

### C. 內容包的形狀（`abf_station/launch.py`）
- `render_bundle(..., composed=None)`；`composed={"pipeline_id": int, "version": int, "project": {…}}`。**`composed is None` 時，產出和今天逐位元相同**（既有的 hash、golden、確認憑證都不能變）。
- `composed` 不是 None 時：
  - `pipeline` 必須是 `abf-composed/<名稱>`（名稱符合 `PIPELINE_PART`）、`revision` 必須恰好是 `"0.<version>.0"`（正是 017b 寫進 manifest 的版本字串，也符合現有的 `REVISION` 正規式，所以 `_check_pipeline`／`_check_revision` 不必放寬）；不符 → `BundleError`。
  - 檢查 `project`：鍵必須是 `main.nf`、`nextflow.config`、`modules.json`，或符合 `^modules/nf-core/[a-z0-9_]+(/[a-z0-9_]+)*/(main\.nf|templates/[A-Za-z0-9_.-]+|resources/[A-Za-z0-9_.-]+)$`；沒有 `..`、不以 `/` 開頭、不含反斜線；值必須是文字，過 `_check_text`（不含 NUL、ESC、CR、雙向控制字元）；單檔 ≤ 200,000 字元、總計 ≤ 2 MiB、檔數 ≤ 2,000；`main.nf` 與 `nextflow.config` 必須存在。違反 → `BundleError` 點名鍵。
  - 內容包新增兩個鍵：`"project": project`、`"pipeline_source": {"kind": "composed", "pipeline_id": …, "version": …, "project_sha256": sha256(canonical_json(project))}`（四個鍵）。`_pipeline_source(site, …)` 的「站台 pipeline 命中」**對組合不適用**（組合永遠走本地專案，不會被 `sitePipelines` 劫持）。
  - `files` 的 `samplesheet.csv`、`params.yaml`、`nextflow.config` 照舊，`head.sh` 見 D；`samplesheet`、`params` 照舊。
- `RECORDS` 與 `LAUNCH_KEYS` 不變（`project` 是內容包的一部分，會被雜湊與確認；不是平台事後加的紀錄）。
- 舊版代理收到有 `project` 鍵的包：它重算不出 `project`，比對失敗、拒絕（「內容與代理依自己的設定重新產生的不一致」）——安全地失敗，訊息不精確；PR 說明寫「組合送出需要新版站台代理」。

### D. `head.sh`（同一個檔、同一處）
`_head_script(..., source)` 多一種來源 `kind == "composed"`：
- `module load`：只載 `site["modules"]`（CE 的 Nextflow 模組，例：`biology/Nextflow/26.10.0`），不載來源模組。
- 最後一行：`exec nextflow run <q(run_folder + "/pipeline/main.nf")> -name <run_name> -params-file params.yaml<站台設定 -c…> -c nextflow.config -with-tower <endpoint>`（沒有 `-r`；`siteConfigVars` 的 `-c "$VAR"` 在前、我們的 `nextflow.config` 在最後，與 M1-02 同序；`-with-tower` 不變）。
- 專案自己的 `pipeline/nextflow.config` 由 Nextflow 從腳本所在目錄自動讀到，之後才是啟動目錄的檔與 `-c` 依序（後者勝出），所以 `report.overwrite` 那段在最後的 `-c nextflow.config` 仍生效。**這一點是從 Nextflow 文件推出，本 repo 沒有驗證過**：ledger 記「手動未驗證：nano4 實跑確認專案設定被讀到」，並有一個用真 Nextflow 離線跑本地專案的測試鎖住（`test_composed_head_script_runs_the_local_project_offline`）。
- `render_resume` 遇到 `origin["pipeline_source"]["kind"] == "composed"` → `BundleError`（裁決 7）。

### E. 站台側 `run_launch`
1. `verify_confirmation` 不變（確認憑證、雜湊、單次使用）。
2. 重算：`render_bundle(..., composed=…)`，`composed` 取自 `bundle["pipeline_source"]`（`pipeline_id`、`version`）與 `bundle["project"]`；`pipeline_source["kind"]=="composed"` 但沒有 `project`、或有 `project` 但 `kind` 不是 composed → `Refusal`。`rebuilt != bundle`（去掉 `RECORDS`）就拒絕，與今天同。`project_sha256` 是代理自己算的，所以改一個字元就不一致。
3. 寫檔：現在是一次 `tar -x` 寫 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`、`tower.token`；組合時**同一次 tar** 再加 `pipeline/<相對路徑>`（依鍵排序；`tar -x` 會建父資料夾；權限 `0600`、`umask 077`）。仍是「`mkdir <folder>` 失敗＝專屬資料夾已存在＝不覆蓋」，所以**沒有任何共用資料夾、沒有「sha 相同略過」的競態**（裁決 6）。
4. `_prechecks`（預檢、容器快取可寫、反向通道）不變。只有一次 `sbatch`。
5. 不做容器檢查（裁決 9）。

### F. 平台側：怎麼走到確認頁（`pipeline_launch.py` ＋ `actions/__init__.py`）
`actions/__init__.py::request_pipeline_launch(platform_path, *, pipeline_id, version=None, run_name, samplesheet=None, samplesheet_text=None, ce_name=None, params=None, caller=None, person=None, clock=time.time, remote=False)`（`async`，簽名與 `request_launch` 對齊，把 `pipeline`／`revision` 換成 `pipeline_id`／`version`；總表說「`pipeline` 介面不變」，這裡以「`request_launch` 的簽名不變」為準，見裁決 10）：
1. 與 `request_launch` 同樣的樣本表輸入檢查與讀取（檔或文字；HTTP 呼叫者只能讀自己上傳資料夾）；`build.parse_samplesheet(raw)` 取得列。
2. **擁有者**：`pipeline_launch.prepare(...)`（函式內才 import `actions.pipelines`，避免循環）呼叫 `pipelines.get_pipeline(platform_path, pipeline_id, version, caller=caller)`——別人的與不存在的回同一句（`找不到這個組合`）；`version` 不存在回該函式現有的「有的版本：…」。
3. **閘門（裁決 1）**：呼叫 `validate.validate(graph)`（純函式，毫秒級，**現算**；017c 裁決 5 明說送出前要自己呼叫，不信任可能過期的存檔）。`ok` 為 False → 拒絕，回答列出 error 發現的 `message`（最多 5 條，其餘寫「另有 N 條」），並說「到組合頁修正後存成新版本再送」。只有 warning（含入口節點的 `OPEN_INPUT`）→ 放行。**不寫 `pipeline_validations`**（送出前的請求不寫任何表；驗證紀錄由 017e 的「驗證」動作負責）。
4. `build_project(...)`（B 節）→ 失敗 → `未送出：<ProjectError 的話>`。
5. `build.prepare_launch(platform_path, ce=ce_name, pipeline="abf-composed/<名稱>", revision="0.<版本>.0", run_name=…, samplesheet_rows=rows, params=params, path_columns=（使用者給的 ∪ `build_project` 回的）, composed={…}, check_name=False, owner=…, area=…)`；使用者在 `params` 裡不能給 `input`、`outdir`（既有規則）。
6. 之後與 `request_launch` 相同：`confirm.find_approved`（同樣的內容再呼叫一次回「已排隊」）→ `jobs.check_run_name` → `build.launch_screen` → `_ask(... "launch" ...)`（表單或確認頁；AI 不能代按）。共用部分抽成私有 `_finish_launch(platform_path, ce, bundle, run_name, caller, person, clock, remote)`，兩個函式都呼叫它。**不新增任何確認管道。**

`build.py` 的改動：
- `prepare_launch(..., composed=None)`：有 `composed` 時，傳進 `bundle_mod.inputs_from_environment`／`render_bundle`。沒有 `composed` 但 `pipeline` 的擁有者是 `abf-composed` → `Refusal("abf-composed 是平台自己的組合管線專用名稱；要送組合請用 launch_pipeline (…)")`（擋住網頁表單或 `launch_prefill` 帶來的假名稱，不會跑去 GitHub 找）。
- `launch_screen`：有 `project` 時，在「管線」「版本」之後多顯示：組合名稱與版本、專案檔數、`project_sha256`；然後**完整印出 `main.nf` 與專案的 `nextflow.config`**（`terminal.block`，與 `head.sh` 同樣處理控制字元），再列出其餘檔案的「路徑、位元組數、sha256 前 12 碼」（模組檔不印內文，並寫「這些是 nf-core/modules 在 commit <sha> 的原檔」）。沒有 `project` 時畫面與今天逐字相同。
- `_predecessor`：取到 `origin` 後，`origin.get("pipeline_source", {}).get("kind") == "composed"` → `Refusal`（話見裁決 7）；續跑與重跑共用這個入口。

### G. 不需要 migration
**不需要。** 內容包本來就是 JSON：存在 `confirmations.bundle_json`、`jobs.args_json`（TEXT）；新鍵 `project` 與 `pipeline_source` 的新形狀只出現在新送出的包裡。沒有改任何表或欄位（`STATE_SCHEMA`、`jobs` 的 CHECK、`launches` 的欄都不動；`launches` 不需要記 `pipeline_id`，因為 `bundle_json` 已有，與 M1-02 的 `pipeline_source` 同做法）。舊的 `platform.db` 與舊的 bundle 原樣可用；`test_http_site_samplesheet.py::test_tc057_no_table_or_column_changed` 不變。唯一的部署變動是 `pyproject.toml` 的 `package-data` 多一個 glob，以及多一個資料檔（裝新版本即得）。

## 夾具與標準答案（developer-agent 準備；executor 原樣放進 `fixtures/pipeline_launch/`）
**單元測試不依賴真實模組檔的內容**：`test_pipeline_launch.py` 用小型合成的 `sources`（3～4 個手寫模組，各幾行 `main.nf`）與 017c 風格的合成目錄 dict；只有「黃金例」與資料檔本身的測試用真資料。
- `fastqc_multiqc/graph.json`＝017b 的 `fixtures/compose/fastqc_multiqc/graph.json`；樣本表 `sample,reads` 兩列；標準答案 `main.nf`（017b 黃金 `main.nf` 把 `ch_qc_in0 = Channel.empty()  // OPEN INPUT…` 那一行換成 `ch_qc_in0 = ch_rows.map { row -> [ [id: row.sample], file(row.reads, checkIfExists: true) ] }`，並在 `workflow {` 後加 `ch_rows = …` 一行）、`nextflow.config`（017b 黃金 ＋ 標記為平台加的 `publishDir` 段）、檔案清單（`main.nf`、`modules.json`、`nextflow.config`、fastqc 與 multiqc 兩個模組的 `main.nf`）。**標準答案由 developer-agent 手算寫出，不得用程式輸出回填**；ledger 逐項寫推導（同 017b、017c）。
- `unsupported/`：合成 sources 裡一個 `bin/` 模組、一個 `list` 型別輸入、一個缺必要欄位的樣本表。

## 失敗先行測試（現在都會紅）

**`platform/tests/test_module_sources.py`**
- `test_snapshot_is_byte_identical_for_the_same_sha`：用一個小的假 checkout（tmp 目錄）跑兩次，輸出逐位元相同；鍵排序、`mtime=0`。
- `test_snapshot_keeps_only_main_templates_and_resources`：假 checkout 裡有 `meta.yml`、`tests/`、`environment.yml` → 都不在輸出。
- `test_snapshot_marks_bin_dirs_binary_files_and_path_shapes_unsupported`。
- `test_sources_sha_equals_the_catalogue_sha`（真資料）；`test_load_refuses_sources_of_another_sha`（合成）。
- `test_every_catalogue_module_has_files_or_a_named_reason`（真資料：目錄的每個模組都出現在 sources，`unsupported` 不為 null 的要有理由字串；ledger 記有幾個 unsupported）。
- `test_fastqc_and_multiqc_are_present_and_supported`（真資料）。
- `test_files_for_names_the_missing_or_unsupported_module`。
- `test_module_sources_source_has_no_network_or_program_words`：原始碼不含 `urllib`、`requests`、`socket`、`subprocess`、啟動 Nextflow 的指令字樣（`snapshot` 子命令讀的是已 clone 的資料夾，不自己 clone）。

**`platform/tests/test_pipeline_launch.py`**（純函式 ＋ 動作層，雙使用者夾具仿 `test_pipelines_store.py`）
- `test_golden_project_matches_the_hand_derived_files`：黃金圖 ＋ 樣本表 → `project` 的鍵與每個檔逐字等於標準答案。
- `test_project_is_deterministic_and_its_hash_is_the_canonical_json_hash`。
- `test_open_input_lines_are_replaced_exactly_and_a_changed_line_shape_is_an_error`。
- `test_missing_required_column_is_named_in_plain_words`；`test_missing_optional_column_becomes_an_empty_list`；`test_channels_with_the_same_names_share_columns`；`test_same_name_different_type_is_refused`。
- `test_unsupported_input_type_names_node_input_and_record`；`test_unsafe_column_names_are_refused`（含引號、空白、`$`）；`test_user_text_never_reaches_groovy`（樣本表格子裡的 `'; evil()` 不出現在任何專案檔）。
- `test_file_columns_are_added_to_path_columns_and_checked_against_the_read_roots`（樣本表格子指到允許範圍之外 → 既有的 `_check_samplesheet` 拒絕）。
- `test_publish_block_is_appended_once_and_after_the_node_config`。
- `test_project_size_and_file_count_limits`（超過 2 MiB、超過 2,000 檔 → 拒絕、訊息說數字）。
- `test_a_graph_with_an_error_finding_is_refused_with_the_findings_in_plain_words`：用 017c 的 `bad_edges` 圖；回答含至少一條 error 的 `message`；`jobs`、`confirmations`、`launches` 列數不變。
- `test_a_graph_with_only_warnings_goes_through_to_the_confirmation_page`：黃金圖（唯一發現是入口的 `OPEN_INPUT` warning）→ 回 `state: pending` 與 `/c/<rid>`。
- `test_the_gate_recomputes_and_does_not_trust_a_stored_result`：先 `validate_pipeline` 存下 ok，再用 `data=` 換目錄使圖變 `GRAPH_STALE` → 送出被拒；反過來，存的結果是舊的 error、現在圖其實沒問題 → 以現算為準放行。
- `test_other_users_pipeline_answers_like_a_missing_one`：`words(別人的) == words(不存在的)`；B 的請求沒有在 `confirmations` 寫任何列。
- `test_missing_version_lists_the_versions_there_are`；`test_default_version_is_the_newest`。
- `test_nothing_is_queued_without_a_yes`：呼叫後 `jobs` 沒有 `launch_nextflow`；本人 `approve` 之後才有一個，且 `bundle_sha256` 等於確認時的。
- `test_asking_again_with_the_same_choices_returns_the_queued_job`（`find_approved`）。
- `test_pipeline_launch_uses_the_same_pending_request_and_page_as_a_launch`：確認頁 `/c/<rid>` 用既有 `confirmation_facts`（顯示 `abf-composed/…`、版本）；`MAX_OPEN_PENDING` 共用。
- `test_bundle_shape_of_a_composed_launch`：恰好比 nf-core 送出多 `project`；`pipeline_source` 恰好四個鍵；`pipeline == "abf-composed/<名稱>"`、`revision == "0.<版本>.0"`。
- `test_a_non_composed_bundle_is_byte_identical_to_before`：用既有夾具算一份 nf-core 包的 `bundle_sha256`，與改動前寫死的值相同（值寫在測試裡，取自 base 分支的執行結果，不是新程式算的）。
- `test_the_hash_covers_the_project`：改一個模組檔的一個字元 → `bundle_sha256` 不同。
- `test_the_reserved_owner_cannot_be_launched_as_an_nf_core_pipeline`：`request_launch(pipeline="abf-composed/x", revision="0.1.0", …)` 與 `launch_prefill` 帶出的名稱再送 → 白話拒絕，沒去連網。
- `test_resume_and_relaunch_of_a_composed_run_are_refused_in_plain_words`（`prepare_resume`、`prepare_relaunch` 各一）。
- `test_the_screen_shows_the_main_script_and_the_config_and_lists_module_files_by_hash`；`test_the_screen_of_an_nf_core_launch_is_unchanged`。
- `test_building_a_launch_opens_no_socket`：`socket.socket` 換成會丟例外的假物件，整條 `request_pipeline_launch` 到確認頁都不觸發。
- `test_no_table_or_column_changed`：`launches` 欄位清單與 `STATE_SCHEMA` 不變（仿 `test_station_launch.py` 的 `LAUNCHES_COLUMNS`）。
- `test_error_messages_hide_internals`：被拒回應不含 SQL、堆疊、`platform.db` 路徑、`/home`／`/work` 形狀。
- `test_pipeline_launch_source_has_no_program_or_run_words`：`pipeline_launch.py`、`module_sources.py`、`build.py` 不含啟動 Nextflow 的指令字樣、`subprocess`、`sbatch`；`pipeline_launch.py` 與 `actions/__init__.py` 不含 `compose` 子字串。

**`platform/tests/test_launch_bundle.py`**（只新增，不改既有）
- `test_composed_head_script_has_no_r_flag_and_no_source_module_load`：最後一行逐字等於 `exec nextflow run <run_folder>/pipeline/main.nf -name run-one -params-file params.yaml -c "$NFCORE_SITE_CONFIG" -c "$NFCORE_SITE_REFERENCES" -c nextflow.config -with-tower http://127.0.0.1:8787`（用 `SITE_CE`，`sitePipelines` 的 ampliseq 命中不影響組合）；`module load` 只有 CE 的 `modules`。
- `test_composed_head_script_is_in_the_golden_file`：`golden_head_scripts.json["composed"]` 等於產出；其他鍵未動。
- `test_composed_pipeline_and_revision_shapes`：`pipeline` 不是 `abf-composed/…`、`revision` 不是 `0.<version>.0` → `BundleError`。
- `test_project_key_shapes_are_refused`：`..`、絕對路徑、反斜線、`bin/`、非 `modules/nf-core` 前綴、含 NUL／ESC／CR／雙向控制字元、單檔過大、總量過大、缺 `main.nf`。
- `test_render_resume_refuses_a_composed_origin`。
- `test_the_site_pipeline_hit_does_not_hijack_a_composed_launch`。

**`platform/tests/test_pipeline_launch_station.py`**（仿 `test_station_launch.py` 的 `site`／`fake` 夾具，真的跑 `run_launch`）
- `test_a_composed_launch_is_rebuilt_byte_for_byte_and_the_project_lands_in_the_run_folder`：站台上 `pipeline/main.nf`、`pipeline/modules/nf-core/…/main.nf` 的內容等於 `bundle["project"]`；`head.sh` 等於內容包裡的；權限 `0600`；只有一次 `sbatch`。
- `test_a_project_file_changed_after_the_yes_is_refused_and_nothing_is_written`（改 `main.nf` 一個字元、改一個模組檔、改 `project_sha256` 各一）。
- `test_a_project_with_an_unlisted_path_is_refused`（`pipeline/../x`、`modules/nf-core/a/../../b`）。
- `test_a_composed_bundle_without_a_project_or_a_project_without_the_source_is_refused`。
- `test_the_run_folder_that_exists_already_is_not_overwritten`（沿用既有行為）。
- `test_run_resume_refuses_a_composed_origin`（手工組一個有 `resume` 的包）。
- `test_composed_head_script_runs_the_local_project_offline`：用 `test_launch_nextflow.py` 的 `Chain`／真 Nextflow（離線）與一個最小的本地專案（不含 nf-core 模組），確認 `head.sh` 的最後一行啟動的是 `pipeline/main.nf` 且專案 `nextflow.config` 被讀到。前置與 `test_launch_nextflow.py` 同一套；CI 禁止 skip，不另外加跳過條件。
- `test_an_nf_core_launch_through_the_agent_is_unchanged`：既有 `bundle_for` 夾具的 nf-core 送出，檔案、`head.sh`、tar 內容與改動前相同。

## 允許更新的既有斷言
只准照下面改，改動寫進 ledger：
- `platform/tests/test_pipelines_store.py::test_the_files_owned_by_other_work_do_not_mention_pipelines`（約第 319 行）：對 `actions/__init__.py` 這一個檔，禁用字從 `("create_pipeline", "render_pipeline", "pipeline_versions", "actions.pipelines", "compose")` 改成 `("create_pipeline", "render_pipeline", "pipeline_versions", "compose")`（拿掉 `actions.pipelines`，因為新函式要在函式內 import 它；`compose` 仍禁，所以新模組叫 `pipeline_launch`、不叫 `composed`）。其他檔（`mcp_server.py`、`web.py`、`store.py`、`catalogue.py`）原樣。
- `platform/tests/test_launch_bundle.py`、`test_station_launch.py`：**只新增**測試，不改既有的。若有既有測試因 `render_bundle` 多了關鍵字參數而紅，代表有人改動了 `composed is None` 的輸出 → 退回去，不要改測試。
- `platform/tests/fixtures/golden_head_scripts.json`：只加 `composed` 一個鍵。

**必須確認仍綠、不准改**：
- `test_launch_bundle.py::test_tc_ls_07_pipeline_source_of_a_hit_and_a_miss`、`test_tc_ls_46_the_hash_covers_pipeline_source`、`test_tc_ls_36_37_38_a_resume_of_a_site_run_starts_from_the_same_place`、`test_tc_ls_16_20_without_site_keys_the_script_is_the_old_one_with_modules_one_line_more`。
- `test_station_launch.py::test_tc_ls_43_44_45_47_a_site_launch_is_rebuilt_byte_for_byte_and_a_changed_source_is_refused`、`test_tc_ls_44_45_a_bundle_changed_after_the_yes_is_refused`、`test_tc_ls_47`（`launches` 欄位不變）、`test_tc_ls_42_a_run_started_before_the_site_keys_existed_still_resumes_from_the_remote`、`test_unconfirmed_launch_is_refused`（`LAUNCH_ALLOW` 指向的那個）。
- `test_owner_gaps.py::test_tc050_nothing_new_is_made_on_the_site`（約第 320 行，nf-core 包的鍵集合不變）、`test_owner_binding.py` 的站台鍵段（約第 838～855 行）。
- `test_resume_render.py`（golden 的既有鍵）、`test_station_resume.py`、`test_resume_scope.py`。
- `test_station_static.py::test_tc084_nothing_in_either_package_submits_a_job_or_starts_a_run`、`test_tc091_…`。
- `test_scope.py`：TC-070（新增的 `module_sources.py`、`pipeline_launch.py`、三個新測試檔前 40 行要有 `# Nothing existing: …`，理由 ≥15 字）、TC-071（`abf_platform/**/*.py` 含註解與 docstring 都不得出現 Nextflow 啟動指令、`subprocess`、`threading`、`while True`、`nohup`、`setsid`…；**說明文字也別寫**）、TC-072（`platform/` 底下所有檔，含新資料檔與 `fixtures/pipeline_launch/*`，不得有 `(/home|/work|/scratch|/staging|/lustre)/名字/` 形狀——資料檔由 `snapshot` 在生成時就把這種模組標 unsupported）；`test_launch_static.py` TC-074（金鑰形狀；測試與夾具裡**不要寫出任何私鑰標頭字串**）。
- `test_pipelines_store.py::test_only_seven_public_functions_and_none_in_the_actions_package`、`test_pipelines_store_has_no_submit_path`（`pipelines.py` 本任務不改）。
- `test_compose.py`（含 TC-118）、`test_validate.py`、`test_catalogue.py`、`test_web_parity.py`、工具數斷言、`test_http_site_samplesheet.py::test_tc057_no_table_or_column_changed`。
- 腳本：`bash tests/no_second_run_state_test.sh`（`LAUNCH_ALLOW` 仍只有 `abf_station/launch.py` 一條；`build.py`、`pipeline_launch.py` 的非註解行不得含啟動指令）、`bash tests/platform_storage_doc_test.sh`（本任務不新增儲存項，應不變）。

## 完成標準（done when）
- 對黃金圖（fastqc→multiqc）存下後，`request_pipeline_launch` 回 `pending` 與 `/c/<rid>`；本人 `approve` 後有一個 `launch_nextflow` 工作；用 `test_station_launch.py` 的假站台跑 `run_launch`，`<run_folder>/pipeline/` 下有 `main.nf`、`nextflow.config`、`modules.json` 與兩個模組的 `main.nf`，`head.sh` 最後一行啟動 `pipeline/main.nf`。
- 含 error 發現的版本被拒，回答用白話列出原因；別人的與不存在的組合回同一句。
- 上面所有測試綠；全套 `platform/tests` 綠；`bash tests/no_second_run_state_test.sh`、`bash tests/platform_storage_doc_test.sh` 綠。
- `git diff --stat` 只含「範圍：檔案」列的路徑；`store.py`、`jobs.py`、`confirm.py`、`compose.py`、`catalogue.py`、`validate.py`、`actions/pipelines.py`、`web.py`、`mcp_server.py` 沒有變動；非組合的 nf-core 送出的內容包、`head.sh`、確認畫面逐位元不變。
- PR 說明寫明：不需要 migration 的理由、新資料檔的大小與更新方法、與總表 017d 的差異（裁決 2、6、7、9、10）、「組合送出需要新版站台代理」、以及未驗證項目。
- 手動（不在本任務，ledger 記「未驗證」）：在 nano4 真跑一次 fastqc→multiqc 組合（專案設定被讀到、`publishDir` 有輸出、容器由 nano4 線上拉取）；舊版代理收到組合包的拒絕訊息。

## 環境事實
- 現行送出入口與可重用的零件：`platform/abf_launch/build.py:131` `prepare_launch`（已有 `samplesheet_rows`、`owner`、`area`，原本是續跑用的）；`:439` `launch_screen`；`:307` `_predecessor`（續跑與重跑共用）；`platform/abf_platform/actions/__init__.py:493` `request_launch`、`:383` `_ask`（表單或確認頁，AI 不能代按）。
- 內容包與站台：`platform/abf_station/launch.py:409` `render_bundle`（回傳鍵：`version, agent, ce, run_name, run_folder, pipeline, revision, samplesheet, params, path_columns, account, tower, files, pipeline_source`）；`:157` `_pipeline_source`（M1-02：`{"kind":"remote"}` 或 `site-module`）；`:360`、`:403` `_head_script` 與 `target = …`（站台命中時是 `"$HOME 變數"`、否則 `owner/name -r rev`）；`:512` `LAUNCH_KEYS`、`:513` `RECORDS`；`:538` `verify_confirmation`；`:577` `_tar`；`:694` `run_launch`（重算後 `!=` 就拒絕；寫檔是 `mkdir <folder> && tar -x` 一次，資料夾已存在就拒絕）；`:734` `_prechecks`；`:793`、`:807` 續跑的 `_probe`／`_check_folder` 只驗四個 `FILE_NAMES` 的 sha256（這是不支援續跑的原因，裁決 7）；`:35`、`:36` `REVISION`、`PIPELINE_PART`（所以 `abf-composed/<名稱>` 與 `0.<版本>.0` 不必放寬規則）。
- 017b 的輸出：`platform/abf_platform/compose.py:258` `render`（`include … from './modules/nf-core/<path>/main'`；沒接的輸入渲染成 `ch_<id>_in<i> = Channel.empty()  // OPEN INPUT: …`；manifest 版本 `0.<版本>.0`；回傳 `open_inputs`）；`:19` `REPO_URL`；`:15-17` 圖的上限（200 節點、1000 邊、256 KiB）。`actions/pipelines.py:172` `get_pipeline`（擁有者過濾、「有的版本」訊息）、`:209` `validate_pipeline`、`:234` `get_validation`。`validate.py`（純函式，`validate(canonical, data)` 回 `{"ok", "checks", "catalogue_sha", "findings", "open_inputs"}`）。017c 裁決 5：「017d 擋 launch 時應直接呼叫 `validate_pipeline`（確定性、毫秒級、不花錢），不要信任可能過期的存檔」；017b 裁決 3：沒接的輸入「樣本表怎麼對到 `meta`＋`reads` 是 017c／017d 的事」。
- 目錄資料沒有 `container` 欄位：`catalogue.py` 的 `_entry`、`flatten` 只存 `name`、`path`、`description`、`keywords`、`tools`、`inputs`、`outputs`（輸入記錄多一個 `optional`）。所以總表 017d 的「對每個模組的 `container` 轉 singularity 檔名」在現有資料上做不到（裁決 9）。目錄快照 sha `5ed90b42e78410e7411e9c6bdfeff33226d6c58e`，`platform/abf_platform/data/nf-core-modules.json` 約 3.5 MB（實測檔案大小）；`pyproject.toml` 的 `package-data` 目前只有 `skills/*/SKILL.md`、`data/*.json`。
- 站台與網路（決定「模組檔放進內容包」的證據）：`configs/sites/nchc-nano4-ce.json` 的 `environment` 沒有 `NXF_OFFLINE`，`modules` 是 `biology/Nextflow/26.10.0`，`sitePipelines` 只有 ampliseq；全 repo 只有測試夾具設 `NXF_OFFLINE`（`platform/tests/e2e_harness.py:95`、`test_launch_nextflow.py:68`、`test_launch_e2e.py:196`、`fixtures/record_payloads.py:100`）。`memory/reference/nchc-nano4-probe-2026-10-20.md`「網路」與「第二輪」：nano4 登入節點與計算節點直連外網（github 200、quay 200），無 proxy；台灣杉三走防火牆＋relay。`memory/daily/2026-10-23.desktop-7j5l5bj.md` 沒有 head 離線模式的紀錄（查過，沒有）。結論：不依賴站台能不能上網，內容包自帶模組檔最穩；容器映像由 Nextflow 在計算節點自己拉，與本任務無關。
- 內容包的存放與大小：`confirmations.bundle_json` 與 `jobs.args_json` 都是 `TEXT`（`store.py:207`、`:229`），`confirm.create_pending` 與 `jobs.enqueue_confirmed` 各存一份；`confirm.py:24` `MAX_OPEN_PENDING = 10`；沒有找到對內容包大小的上限（`web.py:65` `MAX_BODY = 16384` 只管表單 POST；樣本表上限 1 MiB 在 `actions/__init__.py:468`）。所以本任務自訂上限 2 MiB／2,000 檔／單檔 200,000 字元（裁決 6）。
- 靜態規則：`tests/no_second_run_state_test.sh:63`（`LAUNCH_ALLOW` 只有 `platform/abf_station/launch.py`）與 `:107`（平台非註解行含 Nextflow 啟動指令一律擋，`build.py`、`pipeline_launch.py` 都在掃描範圍）；`test_scope.py` TC-071（約第 100 行）、TC-072（約第 134 行，掃 `platform/` 底下所有檔，以 `errors="replace"` 讀）；`test_station_static.py` TC-084（約第 73 行）。`test_pipelines_store.py:319` 禁止 `actions/__init__.py` 出現 `compose` 子字串（所以模組叫 `pipeline_launch`，函式叫 `request_pipeline_launch`，kind 字串 `"composed"` 只出現在 `build.py` 與 `launch.py`）。
- 擁有者：`build.prepare_launch(owner=…)` 已用呼叫者過濾環境與代理；`pipelines.get_pipeline` 已用 `_mine` 過濾組合；HTTP 呼叫者的樣本表限制在 `actions/__init__.py:427-470`。
- 文件落點：`docs/PLATFORM.md` 的 `## Composed pipelines`（第 542 行）、`### Validation`（第 548 行）、`### What was handed over`（第 412 行）。

## 不做
- 不加 MCP 工具、不加網頁路由、不改 `mcp_server.py`、`web.py`、`web_board.py`、`handlers.py`（017e：`launch_pipeline` 的名字、`confirm.JOB_KIND`／`REQUEST_TOOLS` 登記、parity 表）。
- **不支援續跑與原樣重跑**（裁決 7）：另開票 `017d2-resume-composed`（要把 `pipeline/` 下的檔案也放進 `_probe`／`_check_folder` 的 sha256 比對）。
- 不做容器檢查、不改目錄快照去帶 `container`（裁決 9）。
- 不做 `nf-core pipelines lint`、`-stub-run`、nf-test、zip 匯出（017c2、017e）。
- 不在 `launches` 表加欄、不加表、不改 `jobs` 的 job 種類。
- 不自動送出、不繞過確認頁；不做「驗證通過就自動 launch」。
- 不支援 `list` 型別或沒有型別的開放輸入、不支援模組 `bin/` 目錄、不支援子流程與 `include` 其他模組的模組。
- 不做配對式（paired-end）一格兩檔：一個 `reads` 欄一個檔案；雙端定序的組合要等樣本表綁定的第二版。
- 不做跨 run 共用專案資料夾、不做 sha 相同略過（裁決 6）。

## 裁決（預設照本檔，不改方向；與上文衝突時以本段為準）
1. **送出閘門＝現算驗證，不是信存檔。** 維護者的條件「最新驗證 ok 且沒過期才可送」，用 017c 裁決 5 的做法達成：送出時直接呼叫 `validate.validate(graph)`（確定性、毫秒、不寫表），`ok` 為 False 就拒絕。這樣「過期」不可能發生（現算永遠是現在的目錄），也不需要使用者先按一次「驗證」。warning（含入口節點的 `OPEN_INPUT`）不擋。不呼叫 `validate_pipeline` 是為了讓「請求送出」這一步不寫任何表（寫入只在本人按送出之後發生）。
2. **模組檔放在 repo 的 `data/nf-core-module-sources.json.gz`，不是主機快取、不是送出時抓。** 與目錄快照同 sha、同更新規則（A 級 PR、維護者機器生成）。壓縮後超過 8 MiB → BLOCKED，備案改為平台主機的快取目錄（維護者手動執行的 `abf-platform modules fetch`，平台執行時仍不連網）。
3. **樣本表綁定第一版的範圍（最大的一條待確認，見下）**：每個開放輸入通道由 `sample` 欄＋該通道非 meta 記錄的名字欄供應；一格一個值（一個檔）；同名記錄共用欄；`list`／缺型別不支援。理由：017b 把沒接的輸入渲染成 `Channel.empty()`，不處理的話送出的 run 會空轉成功。
4. **入口節點的必填輸入在驗證裡維持 warning**（沿用 `open-input-required` 裁決），真正的「欄位對不上」由 `build_project` 在送出時用樣本表標題列判定並白話拒絕。
5. **`publishDir` 由平台在送出時加進專案的 `nextflow.config`**，`mode: 'copy'`，輸出到 `${params.outdir}/<process 名小寫>`。不改 `compose.render`（017b 黃金不動）。理由：nf-core 模組不自己發佈輸出，沒有這段結果頁會是空的。
6. **專案檔寫進每個 run 自己的 `<run_folder>/pipeline/`，不用共用的 `<workDir>/pipelines/<id>@<ver>/`（總表的做法）**；內容包用 `{相對路徑: 文字}` 的對照表，不用 `project_tar`（base64 的 tar）。理由：①`run_launch` 現在就是「`mkdir <folder>` 失敗就拒絕＋一次 `tar -x`」，共用資料夾要新增「存在就比 sha 再略過」的站台端邏輯與競態；②文字對照表可直接被 `canonical_json` 雜湊、在確認頁顯示、在代理端逐檔檢查路徑；tar 要先解開才能檢查；③每個 run 一份拷貝，刪 run 就一起刪，且保證「這個 run 跑的就是它確認的那份」。代價：每個 run 多幾百 KB，可忽略。上限 2 MiB／2,000 檔／單檔 200,000 字元（總表是 5 MB 的 tar；文字檔對照表在 JSON 裡不用 base64，也不放大），估計一般圖遠低於此（200 節點 × 數 KB）。
7. **續跑與原樣重跑：不支援，用白話拒絕。** 拒絕的話：「自訂組合的 run 目前不能續跑或原樣重跑；請回到組合頁，用同一個版本重新送出（會再問一次確認）(a run of a composed pipeline cannot be resumed or relaunched yet; send the same version again from the pipeline page, which asks for a new yes)」。理由：續跑會在**已存在的**資料夾裡重用 `pipeline/`，而 `run_resume` 的資料夾探測（`launch.py:793`、`:807`）只比對四個固定檔的 sha256；若不把 `pipeline/` 的檔也比對，站台上有人改過 `main.nf` 後續跑，執行的就不是本人確認過的內容。要做就得動這段最敏感的程式，單獨一張票（`017d2-resume-composed`）。
8. **有 `unsupported` 的模組：點名拒絕**，訊息說明模組名與理由（例：「模組 xxx 需要 bin/ 目錄，目前無法帶到站台」），並建議換成別的模組。ledger 記真資料裡有幾個 unsupported。
9. **本任務不做容器檢查**（總表的那一句作廢）。理由：①目錄快照沒有 `container` 欄位；從模組 `main.nf` 的 `container` 指令用規則式解析容易錯，錯了就誤擋或誤放；②nano4 的登入與計算節點可直連外網，缺映像時 Nextflow 自己拉；③既有的 `_prechecks` 已驗 `NXF_SINGULARITY_CACHEDIR` 可寫。離線站台的容器預檢是之後的事（要先有 A 級票把 `container` 帶進快照）。
10. **保留擁有者名稱 `abf-composed`**，專供組合；nf-core 送出（`request_launch`、網頁表單、`launch_prefill` 帶回的名稱）用它一律白話拒絕。`pipeline` 欄位仍是「擁有者/名稱」，所以所有讀 `bundle["pipeline"]` 的地方（確認頁、`confirmation_facts`、結果頁）不用改。入口是新函式 `request_pipeline_launch`（總表說 `request_launch` 判斷 `pipeline_source`，但 `request_launch` 收的是 `pipeline`／`revision` 文字，沒有地方放 `pipeline_id`，硬塞會讓它的簽名變形；`request_launch` 的簽名與行為不變）。
11. **文件**：`docs/PLATFORM.md` 的 `## Composed pipelines` 補 `### Launching a composed pipeline`（誰能送、閘門、內容包多了什麼、檔案怎麼來、跑在哪裡、不支援續跑、需要新版站台代理）；`### What was handed over` 補一句 `pipeline/` 資料夾。不新增儲存項，`platform_storage_doc_test.sh` 不應變。
12. **版本相容**：`BUNDLE_VERSION` 維持 1（非組合的包逐位元不變，所以不需要升版）。

## 待維護者確認（developer-agent 預設照上面做；任一條要改請回覆）
1. **樣本表綁定的範圍**（裁決 3）：預設「一個 `sample` 欄＋每個輸入名一欄、一格一個檔」。受限：雙端定序（`reads` 兩個檔）、多條不同樣本表的入口都不支援。替代：①這張票不做綁定，只讓「完全沒有開放輸入」的圖能送——功能很少；②把綁定拆成 `017d2-samplesheet-binding`、本票先交其餘——**會讓本票的 done 不成立**，不建議。
2. **模組檔資料 2～8 MiB 進 repo**（裁決 2）：同意就照做；不同意的備案是平台主機的快取目錄。
3. **`publishDir` 預設 `copy`**（裁決 5）：大輸出會佔雙份空間；要 `symlink` 或「只發佈 multiqc 之類最終結果」要你說。
4. **續跑暫不支援**（裁決 7）：與 10-23 的「能自動續跑的就續跑」方向有落差；補做的票已建議（`017d2-resume-composed`），要不要排在 017e 之前請定。
5. **容器預檢拿掉**（裁決 9）：總表原本有這項，理由已寫；要保留就得先開一張 A 級票把 `container` 帶進快照。

## 裁決（2026-10-24 06:50，developer-agent，派工前）
A. **資料檔大小已實測**：nf-core/modules @ 5ed90b42 共 2116 個模組，`main.nf`＋`templates/`＋`resources/`（不含 tests）gzip -9 後 831,633 bytes（約 0.8 MB），遠低於 8 MiB 上限，資料檔進 repo。
B. executor 環境若無法 clone 上游，產生 `data/nf-core-module-sources.json.gz` 這一步回報 BLOCKED，由 developer-agent 用計畫的 snapshot 指令產生並提交（同 017a 的做法）。
C. 待決 1、3、5 採計畫預設（樣本表一格一檔、單端；publishDir copy；不做容器預檢）。
D. 待決 4：組合流程的續跑另開 `017d2-resume-composed`，排在 017e 之後；本件白話拒絕續跑／重跑。
E. 「專案 nextflow.config 會被 Nextflow 從腳本目錄自動讀到」必須用離線真 Nextflow 的測試鎖住；若 CI 沒有 Nextflow，該測試不得 skip（CI 禁止 skip），改為明確在 head.sh 加 `-c <run_folder>/pipeline/nextflow.config`，二擇一由 executor 依實測決定並記進 ledger。

## 裁決二（2026-10-24 09:50，developer-agent，回應 verifier 出題退回；與上文衝突一律以本段為準）
1. **`compose` 字樣禁令只針對 `actions/__init__.py`**（既有 test_pipelines_store 那條）。`actions/__init__.py` 只 `from .. import pipeline_launch` 並呼叫 `pipeline_launch.prepare(...)`，由它整包做完（呼叫 compose.render、組內容包、標 `pipeline_source.kind="composed"`）後回傳內容包與畫面；`actions/__init__.py` 內不出現 `compose`、`composed`、`abf-composed` 任何字樣。`pipeline_launch.py`、`build.py`、`abf_station/launch.py` 可以出現。對 nf-core 送出擋 `abf-composed/` 假名稱的檢查放在 `build.py`。
2. **head.sh 最後一行固定一種**：一律明寫 `-c <run_folder>/pipeline/nextflow.config`，順序為站台的 `-c` 在前、`-c <run_folder>/pipeline/nextflow.config`、最後 `-c nextflow.config`，目標是 `<run_folder>/pipeline/main.nf`，沒有 `-r`。裁決 E 的二擇一作廢。golden 照此。
3. **CI 沒有真的 Nextflow**（test_launch_nextflow 用 shim）。不寫「用真 Nextflow 證明 config 被讀到」的自動測試；改為斷言 head.sh 文字（第 2 點）與 tar 內容（`pipeline/main.nf`、`pipeline/nextflow.config`、`pipeline/modules/nf-core/<path>/main.nf` 都在）。實際在 nano4 跑一次列為手動驗收，寫進 `docs/TESTING.md`（範圍加這個檔）。TC-102 依此改寫。
4. `request_pipeline_launch(..., *, data=None)`：`data` 是只給測試用的目錄替換縫，預設 `catalogue.load()`；送出閘門用它重算 validate。
5. 對 `abf-composed/` 假名稱的拒絕訊息改為：「組合流程只能從畫布送出（畫布送出介面尚未開放）」（中英並列），不提不存在的工具名。
6. **含子流程或 include 其他模組的模組**：模組原始碼（main.nf）裡有 `include {` 或 `workflow ` 宣告者，`build_project` 拒絕並點名該模組（finding code `UNSUPPORTED_MODULE`），可測。
7. 計畫有寫但沒列測試名的行為，由 executor 補測試並註明 TC 編號（verifier 已在合約標出），不算擴大範圍。

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
