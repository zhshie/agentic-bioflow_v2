---
id: 017b-compose
title: 組裝積木：畫布圖的資料模型、每人一份的儲存、轉成 Nextflow 專案檔（只做後端，先不對外開工具）
tier: B
kinds: backend
lane: L5
base: v3
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 4（017b）；依 017a（PR #172）的 catalogue.py
---

# 017b-compose

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/017b-compose/plan.md`。**只處理本任務**。
> 與 017a 同一個原則：**不新增 MCP 工具、不加網頁路由、不碰 `actions/__init__.py`**——對外的工具與路由留到 017e 一次開（屆時同時補 parity 表與工具數斷言）。
> 與總表（replan 第 156 行）的差異全部列在「裁決」，以「裁決」為準：本任務**不抓 GitHub 模組檔、不做 zip、不做型別檢查、不做分享連結**。

## 目標
把畫布上的一張圖（節點＝nf-core 模組、邊＝某模組的輸出通道接到另一個模組的輸入通道、每個節點有自己的參數）做成：①一份有版本、只有擁有者看得到的儲存；②一支純函式 `render`，把圖轉成可給 `nextflow run` 用的 `main.nf`、`modules.json`、`nextflow.config`，同一張圖永遠產出逐字相同的檔案。017c（驗證）、017d（送出）、017e（畫面與工具）都從這裡讀。

## 維護者原話（verifier 出題用）
- 「拖模組、連線、填參數、驗證、送去跑、匯出 zip、版本紀錄與分享；不做巢狀子流程。」（10-21 裁示 5）→ 圖裡沒有「子流程」這種節點；每個節點只能是目錄裡的一個模組；每次存檔留一個版本；參數存在節點上。
- 「積木＝nf-core 模組，全部約 1,500 個；pipeline 與 module 都要相容所有 nf-core 既有的。」（裁示 5）→ 轉出來的 `modules.json` 與 include 寫法要照 nf-core 既有格式；目錄裡任何一個模組（含舊格式 meta.yml 的）都要能被轉。
- 「不自建工具庫」（10-21 不做清單）→ 不複製、不改寫模組內容；只寫「用哪個模組、哪個 sha」。
- 總表 017b 失敗先行：「兩節點圖產出一 include 一 edge；……版本 append-only。」→ 兩節點圖（fastqc→multiqc）轉出兩條 include、一條接線；版本只能新增，舊版內容不變。
- 擁有者規則（`docs/PLATFORM.md` 第 440 行起「Whose it is」）：「a caller sees and uses only their own」，別人的與不存在的回一樣的話。

## 範圍：檔案（最終版，只准改這些）
- `platform/abf_platform/compose.py`（新：純函式，不碰資料庫、不碰網路、不 import `store`）
- `platform/abf_platform/actions/pipelines.py`（新：儲存與讀取，**仿 `actions/datasets.py`**——子模組、各函式收 `caller=`、資料表在第一次使用時 `CREATE TABLE IF NOT EXISTS`；**不**在 `actions/__init__.py` 匯入）
- `platform/tests/test_compose.py`（新：純函式與 golden）
- `platform/tests/test_pipelines_store.py`（新：儲存、擁有者、版本）
- `platform/tests/fixtures/compose/`（新：`fastqc_multiqc/`、`fan_in_and_twins/`、`old_format_module/` 三個資料夾，各含 `graph.json` 與標準答案 `main.nf`、`modules.json`、`nextflow.config`）
- `docs/PLATFORM.md`（在 `## What the platform stores` 之前加 `## Composed pipelines`；該表加一列；見裁決 9）
- `specs/017b-compose/ledger.md`（新，executor 的進度帳本）

**不准動**：`store.py`（不加表、不加欄、不改 `STATE_SCHEMA`）、`actions/__init__.py`、`mcp_server.py`、`web.py`、`catalogue.py`、`pyproject.toml`（不需新增 package-data，沒有新資料檔）、`constraints.txt`（只用標準庫）。

## 作法

### A. 圖的形狀（`compose.py`）
輸入圖（dict，JSON 可序列化）：
```json
{"nodes": [{"id": "qc", "module": "fastqc", "sha": "5ed90b42e78410e7411e9c6bdfeff33226d6c58e", "params": {"ext.args": "--quiet"}},
           {"id": "report", "module": "multiqc"}],
 "edges": [{"from": {"node": "qc", "output": "zip"}, "to": {"node": "report", "input": 0}}]}
```
- `id`：`^[a-z][a-z0-9_]{0,31}$`，圖內不重複。小寫＋底線是為了直接當 Groovy 變數名的一部分。
- `module`：目錄裡的模組 `name`（`catalogue.describe` 能找到；比對不分大小寫，**存下來的是目錄裡的標準寫法**）。
- `sha`：可省略；省略時補成目前目錄快照的 `sha`。給了但不等於目前快照 sha → 拒絕（本版只有一份快照，不支援舊 sha）。
- `params`：可省略（視為 `{}`）。鍵只准 `ext.args`、`ext.args2`…`ext.args9`、`ext.prefix`（`^ext\.(args[2-9]?|prefix)$`），值只准字串（≤ 1000 字元、不含換行與其他控制字元）。其他鍵或型別 → 拒絕並點名該節點與鍵。
- 邊的 `from.output`：必須是該模組在目錄 `outputs` 裡出現過的 `channel` 名，**且是合法識別字**（`^[A-Za-z_][A-Za-z0-9_]*$`；否則回「這個輸出通道名不能接線」並點名）。`to.input`：整數，必須是該模組在目錄 `inputs` 裡出現過的 `channel` 編號（`inputs[].channel`，從 0）。
- 拒絕的情況（全部在存檔時、渲染前攔下）：頂層出現 `nodes`、`edges` 以外的鍵；節點 0 個；節點超過 200、邊超過 1000；`id` 重複；邊指向不存在的節點；重複的邊；**自己接自己或形成環**；序列化後超過 256 KiB。
- `normalize(graph, data=None) -> (canonical, problems)`：`data` 預設 `catalogue.load()`。`problems` 是字串清單，**每條同時含中文原因與英文，並說明怎麼改**（例：`邊 qc.zipp 沒有這個輸出通道，可選：html、zip (module fastqc has no output channel zipp; choose one of: html, zip)`）。有任何 problem 就不回 canonical（回 `None`）。
- **標準形式**（canonical）：節點依 `id` 排序、邊依 `(from.node, from.output, to.node, to.input)` 排序、`params` 鍵排序、補上 `sha`；`graph_json = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`。同一張圖不論輸入順序，存下來的文字與渲染結果逐字相同。

### B. 轉成 Nextflow 專案檔（`compose.py::render`）
`render(canonical, name, version, data=None) -> {"files": {"main.nf": str, "modules.json": str, "nextflow.config": str}, "open_inputs": [...]}`。純函式，不讀網路、不寫檔、不啟動任何程式。

**來源（本任務實際讀過的，作法照這些寫）**
- 模組 include 與接線的既有寫法：`nf-core/rnaseq` 的 `workflows/rnaseq/main.nf`（https://raw.githubusercontent.com/nf-core/rnaseq/master/workflows/rnaseq/main.nf ）——`include { X } from '../../modules/nf-core/…'`、同一個模組要用多次時 `include { DESEQ2_QC as DESEQ2_QC_RSEM }`、取輸出 `PROCESS.out.<emit名>`、多個來源合併用 `.mix()`。
- `modules.json` 格式：nf-core/tools 的 pipeline 範本（https://raw.githubusercontent.com/nf-core/tools/dev/nf_core/pipeline-template/modules.json ）與 `nf-core/rnaseq` 的 `modules.json`（https://raw.githubusercontent.com/nf-core/rnaseq/master/modules.json ）——最外層 `name`、`homePage`、`repos`；`repos["https://github.com/nf-core/modules.git"].modules["nf-core"]["<模組路徑>"] = {"branch": "master", "git_sha": "<40 位 sha>", "installed_by": ["modules"]}`；有斜線的模組用整條路徑當鍵（例 `samtools/sort`）。
- 模組介面規則：https://nf-co.re/docs/guidelines/components/modules ——第 n 個輸入通道的 meta 叫 `meta`、`meta2`…`meta<n>`；每個工具的版本輸出獨立（目錄快照已略過 versions，本版不接它）。
- **沒讀到、因此不寫進規格的**：`nf-core modules install` 的原始碼細節。本版**不執行**那個指令（總表已定：不在平台主機跑），只照上面兩份實際檔案的樣子寫 `modules.json`。

**main.nf 的規則**（逐行決定性，順序固定）
1. 第一行 `#!/usr/bin/env nextflow`；第二行 `// Generated by abf-platform compose (pipeline <name> v<version>); do not edit by hand.`；空一行。
2. include 區：節點依「拓撲順序」（Kahn 演算法，同層一律先取 `id` 字典序最小者）。每個節點的 process 名＝目錄裡該模組的 **`path` 把 `/` 換成 `_` 再轉大寫**（`samtools/sort` → `SAMTOOLS_SORT`；用 `path` 不用 `name`，因為目錄裡有 18 個 `name` 與 path 對不上，例如 `name` 為 `STRdust`、path 為 `strdust`）。同一個模組在圖裡出現不只一次 → 該模組的**每個**節點都用別名 `<PROCESS>_<ID轉大寫>`；只出現一次 → 不用別名。每個不同模組一行：`include { SAMTOOLS_SORT } from './modules/nf-core/samtools/sort/main'`（同模組多節點則一行一個別名）。include 行依 process 名排序。
3. `workflow {` 區塊（四格縮排）：依拓撲順序，每個節點一行呼叫 `NAME(arg0, arg1, …)`，參數個數＝該模組 `inputs` 裡不同 `channel` 編號的個數，依編號由小到大。每個參數：
   - 沒有邊接到該輸入通道 → 變數 `ch_<id>_in<i>`，並在 `workflow {` 開頭（呼叫之前）依 `(id, i)` 排序各出一行 `ch_<id>_in<i> = Channel.empty()  // OPEN INPUT: <id> input <i> (<該通道的輸入名，逗號分隔>)`；
   - 一條邊 → `<SRC>.out.<output>`（`SRC` 是來源節點的 process 名或別名）；
   - 多條邊 → 依 `(來源節點, 輸出名)` 排序後 `A.out.x.mix(B.out.y)`（串多個就連續 `.mix(`）。
4. 檔尾恰一個 `\n`。
5. `open_inputs`＝上面那些沒接的輸入：`[{"node": id, "input": i, "names": [...]}]`，同一個排序。**這是給 017c／017e 顯示「還有哪些輸入沒接」的**；渲染本身不當錯誤（理由見裁決 3）。

**modules.json 規則**：`json.dumps(…, indent=4, sort_keys=True, ensure_ascii=False) + "\n"`（與 nf-core 的四格縮排一致）。內容：`name`＝組合的名字、`homePage`＝`""`、`repos` 如上，只列用到的模組（同模組多節點只列一次），`git_sha`＝節點的 `sha`（＝目錄快照的 upstream sha，它是 nf-core/modules master 上的真實 commit，nf-core 工具可據此還原模組檔）。

**nextflow.config 規則**：先 `// Generated by …` 一行；`manifest { name = '<組合名>'; version = '0.<版本>.0' }`（拆成多行）；有任何節點有 `params` 時，再一個 `process { … }` 區塊，每個有參數的節點一段 `withName: '<NAME 或別名>' { ext.args = '…' }`，節點依 `id` 排序、鍵依字典序。**字串值的跳脫**：只輸出單引號字串，`\` → `\\`、`'` → `\'`、`$` → `\$`（防止 Groovy 插值）；值已在 A 節擋掉換行與控制字元，渲染時再檢查一次，仍有就丟 `ValueError`（兩層都擋，因為這一段會被 Nextflow 當程式執行）。

### C. 儲存（`actions/pipelines.py`）
兩張表，第一次使用時 `CREATE TABLE IF NOT EXISTS`（與 `actions/datasets.py:30` 的 `datasets` 同一套做法），放在 `platform.db`：
```sql
CREATE TABLE IF NOT EXISTS pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (owner_user_id, name)
);
CREATE TABLE IF NOT EXISTS pipeline_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL REFERENCES pipelines(id),
    version INTEGER NOT NULL,
    graph_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (pipeline_id, version)
);
CREATE TRIGGER IF NOT EXISTS pipeline_versions_no_update BEFORE UPDATE ON pipeline_versions
    BEGIN SELECT RAISE(ABORT, 'pipeline versions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS pipeline_versions_no_delete BEFORE DELETE ON pipeline_versions
    BEGIN SELECT RAISE(ABORT, 'pipeline versions are append-only'); END;
```
（`UNIQUE` 對 `owner_user_id` 為 NULL 的列不生效，所以和 datasets 一樣在程式裡用 `owner_user_id IS ?` 先查，見 `actions/datasets.py` 的 `register_dataset`。）

函式（全部第一個參數是 `platform_path`，都有 `caller=None`；`None`＝本機終端，看得到全部，與其他 action 一致）：
- `create_pipeline(platform_path, *, name, graph, caller=None, clock=time.time) -> dict`：`name` 用 `^[a-z][a-z0-9-]{0,39}$`（會變成 manifest 的名字）。先 `normalize`；有 problem → `{"ok": False, "message": "<第一條>", "problems": [...]}`，**什麼都不寫**。成功寫一列 `pipelines`＋版本 1，同一個交易（`BEGIN IMMEDIATE`）。同擁有者同名已存在 → `{"ok": False, "message": "你已經有一個叫 X 的組合；用 update 存新版本 (a pipeline named X already exists; save a new version instead)"}`。回 `{"ok": True, "pipeline": {"id", "name", "version": 1, "created_at"}}`。
- `update_pipeline(platform_path, pipeline_id, *, graph, caller=None, clock=...) -> dict`：只**新增**一列 `pipeline_versions`（版本＝目前最大＋1）。`normalize` 後與最新版 `graph_json` 逐字相同 → 不新增，回 `{"ok": True, "unchanged": True, "pipeline": {…同最新版…}}`。別人的與不存在的組合 → 同一句 `找不到這個組合 (pipeline not found): <id>`。
- `list_pipelines(platform_path, *, caller=None)`：`{"ok": True, "pipelines": [{"id", "name", "version"(最新), "n_nodes", "created_at", "updated_at"}]}`，依 `name`、`id` 排序；只含擁有者自己的（`caller` 非 None 時 `WHERE owner_user_id = ?`）。
- `get_pipeline(platform_path, pipeline_id, version=None, *, caller=None)`：沒給版本＝最新。回 `{"ok": True, "found": True, "id", "name", "version", "versions": [1..n], "graph": <dict>, "created_at"}`；找不到（含別人的、版本不存在）→ `{"ok": False, "found": False, "message": …}`，**別人的與不存在的字句相同**（測試用 `words()` 比，仿 `test_datasets.py` 的 TC-076）。
- `render_pipeline(platform_path, pipeline_id, version=None, *, caller=None, data=None)`：`get_pipeline` ＋ `compose.render`；回 `{"ok": True, "name", "version", "files": {...}, "open_inputs": [...]}`。**不寫檔、不排工作**。
- 這些函式**不呼叫** `confirm`、`jobs`、`status`、`subprocess`（理由：它們只寫平台自己的資料庫，不碰站台、不花 SU，與 012c 的 datasets 同類；見裁決 1）。

### D. migration
**不需要 migration。** 理由：沒有改任何既有資料表或欄位（`STATE_SCHEMA` 不動）；`pipelines`、`pipeline_versions` 是全新的表，由 `CREATE TABLE IF NOT EXISTS` 在第一次使用時建立，舊的 `platform.db` 原樣可用、新的也不預建（與 `datasets` 相同）。副作用要在 PR 說明寫明：**`connect_state()` 之後這兩張表不一定存在**，讀取函式要自己先建表（`_table(con)`），不能假設。

## 夾具與標準答案（developer-agent 準備；executor 原樣放進 `fixtures/compose/`）
`fastqc_multiqc/graph.json`＝上面 A 節那張圖（`fastqc` 的 `zip` 接 `multiqc` 的輸入 0）。以 `compose.render(normalize(graph)[0], "demo-qc", 1)` 必須得到：

`main.nf`
```groovy
#!/usr/bin/env nextflow
// Generated by abf-platform compose (pipeline demo-qc v1); do not edit by hand.

include { FASTQC } from './modules/nf-core/fastqc/main'
include { MULTIQC } from './modules/nf-core/multiqc/main'

workflow {
    ch_qc_in0 = Channel.empty()  // OPEN INPUT: qc input 0 (meta, reads)
    FASTQC(ch_qc_in0)
    MULTIQC(FASTQC.out.zip)
}
```
`modules.json`
```json
{
    "homePage": "",
    "name": "demo-qc",
    "repos": {
        "https://github.com/nf-core/modules.git": {
            "modules": {
                "nf-core": {
                    "fastqc": {
                        "branch": "master",
                        "git_sha": "5ed90b42e78410e7411e9c6bdfeff33226d6c58e",
                        "installed_by": [
                            "modules"
                        ]
                    },
                    "multiqc": {
                        "branch": "master",
                        "git_sha": "5ed90b42e78410e7411e9c6bdfeff33226d6c58e",
                        "installed_by": [
                            "modules"
                        ]
                    }
                }
            }
        }
    }
}
```
`nextflow.config`
```groovy
// Generated by abf-platform compose (pipeline demo-qc v1); do not edit by hand.
manifest {
    name = 'demo-qc'
    version = '0.1.0'
}

process {
    withName: 'FASTQC' {
        ext.args = '--quiet'
    }
}
```
`open_inputs` ＝ `[{"node": "qc", "input": 0, "names": ["meta", "reads"]}]`。

另兩組由 executor 依 A、B 節規則手算、經 developer-agent 看過再固定（**不可用程式輸出反過來當標準答案**）：
- `fan_in_and_twins/`：兩個 `samtools_sort` 節點（`s1`、`s2`）＋一個 `multiqc`；`multiqc` 輸入 0 同時接 `s1.bam` 與 `s2.bam`。預期 include 為 `SAMTOOLS_SORT as SAMTOOLS_SORT_S1`、`SAMTOOLS_SORT as SAMTOOLS_SORT_S2`，呼叫 `MULTIQC(SAMTOOLS_SORT_S1.out.bam.mix(SAMTOOLS_SORT_S2.out.bam))`；`samtools_sort` 的三個輸入通道（0、1、2）各出一個 `ch_s1_in0…`、`ch_s1_in1…`、`ch_s1_in2…` 開放輸入。`params` 含一個含單引號與 `$` 的 `ext.args`，驗證跳脫。
- `old_format_module/`：目錄裡 `name` 與 path 對不上的模組（`strdust`／`STRdust`、`custom/clustermetrics`），驗證 process 名由 path 產生。

## 失敗先行測試（現在都會紅）

**`platform/tests/test_compose.py`**（純函式，不需資料庫）
- `test_fastqc_multiqc_renders_the_golden`：三個檔案與 `open_inputs` 逐字等於標準答案。
- `test_render_is_deterministic_and_order_independent`：節點與邊打亂順序、`params` 鍵打亂 → `normalize` 後 `graph_json` 相同、`render` 結果逐字相同；連渲染兩次相同。
- `test_fan_in_uses_mix_and_twins_get_aliases`：對 `fan_in_and_twins/` 的標準答案。
- `test_process_name_comes_from_the_path_not_the_name`：`old_format_module/` 的標準答案。
- `test_every_catalogue_module_has_a_valid_process_name`：目錄全部模組（2,116 個）的 process 名都符合 `^[A-Z][A-Z0-9_]*$` 且彼此不重複（若有重複，這條紅燈，讀它的訊息再回報，不要自行改規則）。
- `test_module_names_are_stored_canonically`：`"module": "FASTQC"` → 存下來是 `fastqc`。
- `test_unknown_module_is_refused_and_names_it`：problem 含該名字與「search」。
- `test_wrong_sha_is_refused`、`test_missing_sha_is_filled_from_the_snapshot`。
- `test_edge_to_a_missing_output_channel_lists_the_real_ones`：`qc.zipp` → problem 含 `html`、`zip`。
- `test_edge_to_a_missing_input_channel_is_refused`、`test_edge_to_a_missing_node_is_refused`、`test_duplicate_edge_is_refused`。
- `test_cycles_and_self_loops_are_refused`：`a→b→a`、`a→a` 各一。
- `test_limits_nodes_edges_and_size`：201 個節點、1001 條邊、超過 256 KiB 各被拒。
- `test_param_keys_and_values_are_restricted`：鍵 `publishDir`、值含換行、值非字串、值超過 1000 字元各被拒，problem 點名節點與鍵。
- `test_param_strings_are_escaped_in_the_config`：值 `a'b$c\d` 轉出 `'a\'b\$c\\d'`；用 `ast`／字元掃描證明輸出裡沒有未跳脫的單引號。
- `test_render_refuses_a_control_character_even_if_normalize_was_skipped`：直接餵壞的 canonical 給 `render` → `ValueError`。
- `test_problems_are_bilingual_and_say_what_to_do`：每條 problem 含中文字與 ASCII 英文括號段。
- `test_compose_module_is_pure`：`compose.py` 原始碼不含 `import store`、`sqlite3`、`urllib`、`requests`、`socket`、`subprocess`、`open(`（render 不寫檔）。
- `test_modules_json_matches_nf_core_shape`：`json.loads` 後 `repos["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]` 的每一項恰好有 `branch`、`git_sha`、`installed_by`；有斜線的模組以整條路徑為鍵。

**`platform/tests/test_pipelines_store.py`**（用現有 `helpers`／`owner_harness` 的雙使用者夾具，仿 `test_datasets.py`）
- `test_create_then_get_roundtrips_the_canonical_graph`。
- `test_update_appends_a_version_and_old_ones_do_not_change`：存三次 → 版本 1、2、3；版本 1 的 `graph_json` 逐位元不變；`get_pipeline(version=1)` 仍回舊圖。
- `test_update_with_the_same_graph_makes_no_new_version`：`unchanged` 為 True、版本數不變。
- `test_versions_table_refuses_update_and_delete`：直接對 `pipeline_versions` 下 `UPDATE`、`DELETE` 都得到 `sqlite3.IntegrityError`／`OperationalError`（`RAISE(ABORT…)`）。
- `test_invalid_graph_writes_nothing`：被拒的 `create_pipeline` 之後 `pipelines`、`pipeline_versions` 都是 0 列。
- `test_same_name_twice_is_refused_per_owner_but_other_owner_may_reuse_it`。
- **跨使用者（讀）**：`test_other_user_cannot_get_list_or_render`——B 對 A 的組合做 `get_pipeline`、`render_pipeline` 得 not found；`list_pipelines` 不含它；且 `words(別人的訊息) == words(不存在的訊息)`。
- **跨使用者（寫）**：`test_other_user_cannot_update`——B 對 A 的組合 `update_pipeline` 被拒，A 的版本數不變。
- `test_terminal_caller_none_sees_everything`。
- `test_no_confirmation_or_job_is_made`：`create`／`update`／`render` 前後 `jobs`、`confirmations`、`launches` 列數不變（仿 `test_datasets.py` 的 tc080）。
- `test_pipelines_store_has_no_submit_path`：`actions/pipelines.py` 與 `compose.py` 原始碼不含 `subprocess`、`os.system`、`sbatch`、`srun`、`qsub`、`confirm`、`jobs`、`queue`（仿 tc078）。
- `test_error_messages_hide_internals`：被拒回應與日誌不含 SQL、堆疊、`platform.db` 路徑。
- `test_old_platform_db_works_without_a_migration`：用沒有這兩張表的舊 `platform.db`（`connect_state` 建的）直接 `list_pipelines` → 空清單、不丟例外；之後 `create_pipeline` 成功。
- `test_state_schema_is_untouched`：`store.STATE_SCHEMA` 不含 `pipelines` 字樣（防止有人偷加進去而漏改 fingerprint）。
- `test_pipelines_columns_say_nothing_about_runs`：欄位恰為上面 SQL 的欄位（仿 datasets tc077：這些表描述「要跑什麼」，沒有狀態、沒有 run）。

## 允許更新的既有斷言
**預期一條都不用改。** 逐項確認（executor 必須跑並確認仍綠，不准改）：
- `platform/tests/test_http_site_samplesheet.py::test_tc057_no_table_or_column_changed`（`SCHEMA_SHA256`，約第 545 行）：只比 `d.state` 當時的 `sqlite_master`；本任務**不改 `STATE_SCHEMA`**，兩張表只在 `pipelines.py` 被呼叫時才出現，該測試不呼叫 → 不變。**若 executor 發現它變紅，代表有人把表加進了 `STATE_SCHEMA`，退回去，不要更新雜湊。**
- `platform/tests/test_estimate_su.py::test_tcc02_nothing_is_stored`（`_tables()` 前後比對）、`test_failures.py::test_read_only_and_no_secret`（`sqlite_master` 前後比對）、`test_receiver.py::test_tc062_…`（掃 `index.db` 欄名不含 user／role 等字）：都不呼叫新函式 → 不變。
- `test_web_parity.py`（`public_names()` 只看 `actions` 套件的公開名字且排除模組）：`actions/pipelines.py` 是子模組、`actions/__init__.py` 不匯入 → 四張表不用動。**如果 executor 覺得得改這個檔，就是做錯了。**
- `test_catalogue.py`、`test_guidance.py`（package-data 正規式）、`test_pat.py`／`test_oauth_mcp.py`／`test_estimate_su.py` 的工具數：不牽動（沒新工具、沒新資料檔）。
- 必過的靜態檢查：`test_scope.py` TC-070（`compose.py`、`pipelines.py`、兩個新測試檔前 40 行要有 `# Nothing existing: …`，理由 ≥15 字）、TC-071（`abf_platform/**/*.py` 不得出現 `nextflow run`、`subprocess`、`threading`、`while True` 等字樣——**包含註解與 docstring**，寫說明時別用這幾個詞）、TC-072（`platform/` 底下所有檔，含 `fixtures/compose/*`，不得有 `(/home|/work|/scratch|/staging|/lustre)/名字/` 形狀）、`test_launch_static.py:104-118` TC-074（金鑰形狀）。
- `tests/platform_storage_doc_test.sh`：會讀 `## What the platform stores` 的表；新增一列後要跑一次確認仍綠（見裁決 9）。

## 完成標準（done when）
- `fastqc→multiqc` 圖經 `create_pipeline` 存下、`render_pipeline` 取回的三個檔，與標準答案逐字相同。
- 上面所有測試綠；全套 `platform/tests` 綠；`bash tests/platform_storage_doc_test.sh` 綠。
- `git diff --stat` 只含「範圍：檔案」列的路徑；`store.py`、`actions/__init__.py` 沒有變動。
- PR 說明寫明：不需要 migration 的理由、`connect_state` 後兩張表不一定存在、與總表 017b 的差異（見裁決）。
- 手動（留給 017d 之後）：把渲染結果放進真實 nf-core 模組檔後 `-stub-run`。**本任務不做**，ledger 記「未驗證」。

## 環境事實
- 目錄快照：`platform/abf_platform/data/nf-core-modules.json`，`sha` 為 `5ed90b42e78410e7411e9c6bdfeff33226d6c58e`，`count` 2116、`errors` 0；`catalogue.describe(name)` 回 `{"found": True, "sha": …, **模組全欄}`（`platform/abf_platform/catalogue.py:167`），`load()` 在 `:138`。
- 模組記錄的形狀：`inputs[]` 是 `{"channel": 整數, "name", "type", "pattern"}`（同一個 tuple 的元素共用 `channel`，例：`fastqc` 的 `meta`、`reads` 都是 0；`samtools_sort` 有 0、1、2 三個）；`outputs[]` 是 `{"channel": 輸出名(字串), …}`（`versions*` 已略過）。`multiqc` 輸入全在 channel 0。
- 目錄裡 `name` 與 `path` 對不上的有 18 個（例：`STRdust`／`strdust`、`CUSTOM_CLUSTERMETRICS`／`custom/clustermetrics`）；`name` 全部不重複。
- 仿的現成做法：`platform/abf_platform/actions/datasets.py:30`（`_TABLE`）、`:177`（`_table`）、`:193`（`register_dataset`，含 `owner_user_id IS ?` 的重複檢查與 `BEGIN IMMEDIATE`）、`:265`（`_rows` 的擁有者過濾）、`:279`（`list_datasets`）、`:286`（`get_dataset`，找不到與別人的同一句）；測試參考 `platform/tests/test_datasets.py` 的 TC-073～076（擁有者）、TC-077（欄位）、TC-078／080（無送出路徑、不產生 job）。
- 擁有者規則：`platform/abf_platform/actions/__init__.py:49`（`Caller` 的說明）、`:358`（`_caller_id`）；`docs/PLATFORM.md:440` 起「Whose it is」。
- 資料庫：`platform/abf_platform/store.py:168`（`STATE_SCHEMA`）、`:567`（`connect_state`，開 `foreign_keys = ON`）。
- 既有的表指紋測試：`platform/tests/test_http_site_samplesheet.py`（`SCHEMA_SHA256`，TC-057）。
- 文件落點：`docs/PLATFORM.md:498`（`## nf-core module catalogue`）、`:506`（`## What the platform stores`）。
- nf-core 的規則出處見作法 B 的「來源」；`nf-core/rnaseq` 用 `'../../modules/nf-core/…'` 是因為它的 include 寫在 `workflows/rnaseq/`；本版 `main.nf` 在專案根，所以是 `./modules/nf-core/<path>/main`（**這是依該資料夾位置推出來的，不是某份文件直接寫的**，017d 實跑時要確認）。

## 不做
- 不加 MCP 工具、不加網頁路由、不改 `actions/__init__.py`、`mcp_server.py`、`web.py`（017e 一次開；`compose_pipeline`、`list_pipelines`、`get_pipeline_version`、`export_pipeline` 的對外名字與 parity 表都留給它）。
- 不做**型別相容檢查**（`type`／`pattern` 對不對得上）、`nextflow_schema.json`、lint、`-stub-run`、nf-test（017c）。本版只確認「邊兩端存在」與「不成環」。
- 不抓 GitHub 上的模組檔、不快取、不組 zip、不寫任何檔到磁碟（17d／匯出另開；`render` 只回字串）。
- 不做送出（017d）、不做畫面（017e）。
- 不做分享連結（`shared_token`）與「實驗室內共享」：本版只有擁有者看得到。
- 不做組合改名、刪除組合、刪除版本（版本只能新增）。
- 不做巢狀子流程；不讀 `subworkflows/`；不在平台主機跑 `nf-core modules install`。
- 不接 `versions` 通道與 `topic: versions`（目錄快照已略過；`MULTIQC` 的版本彙整留待 017c 的 lint 要求出現再議）。

## 裁決（2026-10-24，預檢後；與上文衝突時以本段為準）
1. **存檔不經確認管道。** 理由與 012c `datasets` 同類、與總表裁示 9 一致：存一張圖只寫平台自己的 `platform.db`，不碰站台、不花 SU、不送出。「確認」留給 017d 的 launch。verifier 的「寫入動作需確認」那一條，對本任務的判定＝**不適用，理由見此**；仍須有測試證明沒有產生 `jobs`／`confirmations`／`launches` 列。
2. **與總表 017b 的差異（預設照本檔，不改方向）**：
   - 邊的型別檢查（總表「型別不合的邊被拒並點名兩端」）移到 017c，與驗證同處；017b 只擋「通道不存在」。
   - 節點的 `sha` 沿用目錄快照 sha；總表的 `inputs`／`params`（圖層級）本版不收，頂層出現就拒絕（017c 需要時再加欄位，是加法）。
   - `pipelines` 表不放 `shared_token`、`pipeline_versions` 不放 `validation_json`——到用得上的任務再用 `ALTER TABLE … ADD COLUMN` 加。
   - 總表的 `compose_pipeline`／`list_pipelines`／`get_pipeline_version`／`export_pipeline` 在本版對應 `create_pipeline`／`update_pipeline`／`list_pipelines`／`get_pipeline`／`render_pipeline`（子模組函式）；zip 屬 017d／017e。
   - 總表說 `compose.py::generate(graph)` 一支函式出四個檔；本版拆成 `normalize`（驗證形狀）與 `render`（產出三個檔），因為 017c 要單獨用 `normalize`。
3. **沒接的輸入不是錯誤。** 渲染成 `Channel.empty()` 並在 `open_inputs` 回報，由 017c／017e 決定要不要擋、怎麼讓使用者填（樣本表怎麼對到 `meta`＋`reads` 是 017c／017d 的事）。已知後果：這樣的專案 `-stub-run` 會「空轉成功」，所以 017c 的 `-stub-run` 閘門必須同時看 `open_inputs`，不能只看結束碼——在 ledger 寫進給 017c 的備忘。
4. **`nextflow.config` 是第三個檔。** 任務原文只提 `main.nf` 與 `modules.json`，但節點參數（`ext.args` 等）在 nf-core 慣例裡是靠 config 的 `withName` 選擇器設定，不是模組輸入；沒有這個檔參數就無處可去。manifest 也放這裡。`nextflow_schema.json` 仍歸 017c。
5. **參數鍵只開 `ext.args`、`ext.args2`…`ext.args9`、`ext.prefix`。** 因為字串會變成 Groovy 設定檔被執行，白名單比事後逃脫安全；要加 `publishDir`、`cpus` 之類是日後的加法。
6. **擁有者＝`caller.user_id`；組合名在同一擁有者內唯一**；終端機（`caller=None`）建的組合 `owner_user_id` 為 NULL，只有終端機看得到，與 `datasets` 一致。`assign_orphans`（`store.py:1070`）不處理這兩張表（只處理三個舊表）——日後若要讓終端機建的組合歸給唯一使用者，另開任務。
7. **表由程式第一次使用時建立，不放進 `STATE_SCHEMA`。** 好處：不改表指紋測試、不需 `_add_*_columns` 遷移、舊庫即用。壞處：`STATE_SCHEMA` 不再是「全部表」的唯一清單，`docs/PLATFORM.md` 必須把這兩張表寫進 stores 表（裁決 9）。若維護者偏好全進 `STATE_SCHEMA`，那是 B 級後端行為變更，要同時更新 TC-057 的雜湊並補遷移測試——**預設不這樣做，不需要維護者確認**。
8. **版本不可變用資料庫觸發器加測試雙重保證**；程式也不提供任何改動舊版的函式。
9. **文件**：`docs/PLATFORM.md` 在 `## What the platform stores` 之前加 `## Composed pipelines`（圖的形狀、擁有者、版本只增、`render` 輸出三個檔、**沒有 MCP 工具或網頁，017e 才開**），並在 stores 表加一列：`Composed pipelines: a name and numbered versions of a graph of nf-core modules, per owner | platform.db (pipelines, pipeline_versions) | no automatic deletion; versions are never changed or removed.` 加完跑 `bash tests/platform_storage_doc_test.sh`；它若因列的格式紅燈，只調整該列的寫法，不改測試。
10. **`render` 的 `version` 進 manifest 與檔頭註解，所以相同的圖在不同版本號下檔案不同**；「逐字相同」的保證是「同圖＋同名＋同版本號」。017d 以 `(pipeline_id, version)` 為單位送出，不受影響。
11. **檔首標頭**（`test_scope.py` TC-070）：`compose.py`、`pipelines.py`、`test_compose.py`、`test_pipelines_store.py` 前 40 行要有 `# Nothing existing: …`。範例：`# Nothing existing: nf-core has no library that turns a canvas graph into a pipeline project; nf-core/tools installs modules into a checkout, which the platform host must not run.`
12. **待維護者確認：無。** 以上都不改方向；唯一值得他知道的取捨是第 3 條（未接輸入渲染成空通道，會讓空跑「看起來成功」），已指定由 017c 擋。

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
