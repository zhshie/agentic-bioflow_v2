# 畫布 017c：組合流程的靜態檢查 progress ledger

- [x] `platform/abf_platform/validate.py`：純函式 `validate(canonical, data=None)`；七種 code（GRAPH_STALE、META_MISMATCH、TYPE_MISMATCH、PATTERN_MISMATCH、MIXED_SOURCES、OPEN_INPUT、DUPLICATE_PROCESS）；只 import `re`、`catalogue`、`compose`。
- [x] `platform/abf_platform/actions/pipelines.py`：表 `pipeline_validations`（第一次使用時建，進 `_TABLES`）、`validate_pipeline`、`get_validation`；不在 `actions/__init__.py` 匯入。
- [x] `platform/tests/test_validate.py`、`platform/tests/test_pipelines_validation.py`、`test_pipelines_store.py`（只把「五個公開函式」改成七個）、`platform/tests/fixtures/validate/` 三組夾具。
- [x] `docs/PLATFORM.md`：`### Validation` 一節與 stores 表一列（「How long」欄為過 `platform_storage_doc_test.sh` 的格式，寫成 `no automatic deletion; replaced by the next check of the same version.`，只改寫法沒改測試）。
- [x] 沒有動 `store.py`、`jobs.py`、`abf_station/`、`compose.py`、`catalogue.py`、快照、`actions/__init__.py`、`mcp_server.py`、`web.py`；不需要 migration（只新增一張由 `CREATE TABLE IF NOT EXISTS` 在第一次使用時建的表；舊的 `platform.db` 原樣可用；讀取函式自己先建表）。

## 實作時選的讀法（plan 沒寫死之處）

- 兩邊 classes 都是空集合（例：`[meta]` 接 `[meta]`）：視為相容，不報 TYPE_MISMATCH。
- PATTERN_MISMATCH 與 META／TYPE 各自獨立判斷：同一條邊兩者都成立就兩項都報。副檔名取「展開大括號、去掉前導 `*`、`.`、`_` 之後，最後一個 `.` 後的字」；含 `|`、`$`、`{}` 殘留等取不出者整個 pattern 不比。「檔案類記錄」＝`file`／`directory`。
- MIXED_SOURCES：同一個輸入只回一項（點名依邊排序下第一對不相容的來源）。不相容＝`has_meta` 不同，或兩邊 classes 都非空、不相交、且沒有 `any`。
- DUPLICATE_PROCESS：以渲染時的呼叫名（`<PROCESS>`，同模組多節點時 `<PROCESS>_<ID大寫>`）為準，同一呼叫名來自不同 path 就撞名；`node`＝撞名節點 id 排序後第一個，`channel` 為 null，message 列出全部節點。
- GRAPH_STALE 時 `open_inputs` 為空清單。壞參數（含 `publishDir`、`ext.args1`、控制字元、非字串、過長）依裁決二 1 一律是 GRAPH_STALE，沒有 PARAM_* code。
- `graph_sha256`＝`compose.graph_json(圖)` 的 sha256。

## 標準答案的手推（沒有用 `validate` 的輸出回填；先寫 expected，再讓測試去比）

訊息範本先定好再套（中文＋英文括號，英文只用 ASCII）。類別：map→meta、file／directory→path、string／boolean／integer／float→val、其他→any；通道第一筆若是 meta 則 has_meta 為真，classes 是其餘記錄的類別。

### good_fastqc_multiqc（真實目錄）
- 邊 `qc.zip → report.0`：fastqc zip＝[meta(map), *.zip(file, `*_{fastqc.zip}`)]，has_meta 真、classes {path}；multiqc 輸入 0＝[meta, 5 個 file]，has_meta 真、classes {path}。同 has_meta、classes 相交 → 無型別發現。pattern：multiqc 端有 5 筆檔案類記錄（不是恰好一筆）→ 不比。
- 沒有別的邊進同一輸入 → 無 MIXED_SOURCES。process 名 FASTQC、MULTIQC 不同 → 無 DUPLICATE。
- 沒接的輸入：`qc` 輸入 0（meta, reads）；`qc` 沒有任何進邊 → 入口寫法。`report` 輸入 0 已接。
- 結果：1 項 OPEN_INPUT（warning），`ok` 為 True。

### open_inputs_twins（真實目錄）
- 邊 `s1.bam → report.0`、`s2.bam → report.0`：samtools_sort bam＝[meta, `${prefix}.bam`(file, `*.{bam}`)]，has_meta 真、classes {path}；對 multiqc 輸入 0 同上 → 無型別發現；multiqc 端多筆檔案記錄 → 不比 pattern。
- 同一輸入兩個來源：兩者簽名相同（真、{path}）→ 無 MIXED_SOURCES。同模組兩節點 → 呼叫名 SAMTOOLS_SORT_S1、SAMTOOLS_SORT_S2，不同 → 無 DUPLICATE。
- 沒接的輸入：`s1`、`s2` 各自沒有任何進邊（入口）：輸入 0（meta, bam）、1（meta2, fasta, fai）、2（index_format）共六項；`report` 輸入 0 已接。
- 順序：error 無；warning 依 (node, channel)：s1:0, s1:1, s1:2, s2:0, s2:1, s2:2。`ok` 為 True。

### bad_edges（合成目錄，放在 `bad_edges.json` 的 `catalogue`）
模組：a 無輸入、輸出 out＝[meta(map), out(file, `*.{bam}`)]；b 輸入 0＝[x(file)]；c 輸入 0＝[meta(map), s(string)]；d 輸入 0＝[d0(file)]、輸入 1＝[d1(file)]；e 無輸入、輸出 out＝[f(file)]；g 輸入 0＝[meta(map), v(file, `*.{vcf}`)]。
簽名：a.out＝(真,{path})；e.out＝(假,{path})；b.0＝(假,{path})；c.0＝(真,{val})；d.1＝(假,{path})；g.0＝(真,{path})。
邊（依標準順序）：
1. `a.out → b.0`：has_meta 真≠假 → META_MISMATCH（node b、channel 0）；不再做 TYPE。pattern：b 端檔案記錄 pattern 為 null → 不比。
2. `a.out → c.0`：has_meta 都真；classes {path} 對 {val} 不相交、都非空、無 any → TYPE_MISMATCH（c, 0）。pattern：c 端沒有檔案類記錄 → 不比。
3. `a.out → d.1`：真≠假 → META_MISMATCH（d, 1），來源 a.out。pattern：d1 pattern null → 不比。
4. `e.out → d.1`：假=假；{path} 與 {path} 相交 → 無型別發現。pattern：兩端 pattern 皆 null → 不比。
5. `a.out → g.0`：真=真；{path} 與 {path} 相交 → 無型別發現。pattern：兩端各恰一筆檔案記錄，`*.{bam}`→{bam}，`*.{vcf}`→{vcf}，不相交 → PATTERN_MISMATCH（warning，g, 0）。
`d` 輸入 1 有兩條進邊（3、4）：來源簽名 (真,{path}) 對 (假,{path})，has_meta 不同 → MIXED_SOURCES（d, 1），點名 a.out 與 e.out。
沒接的輸入：d 輸入 0（d0）沒有邊；d 有別的進邊（輸入 1）→ 「少了一個輸入」寫法 → OPEN_INPUT（d, 0, warning）。a、e 沒有輸入；b.0、c.0、g.0 已接。
process 名 A、B、C、D、E、G 互不相同 → 無 DUPLICATE。
排序：error 先：(b,0,META)、(c,0,TYPE)、(d,1,META)、(d,1,MIXED)（同 node、channel 依 code 字母序 META < MIXED）；再 warning：(d,0,OPEN)、(g,0,PATTERN)。`ok` 為 False。

## 未驗證

- 對真實 nf-core 模組檔跑 lint／空跑：**未驗證**（本任務不做，裁決 2；留給站台側的 017c2）。

## 給後續的備忘

- 017d 擋 launch：直接呼叫 `validate_pipeline` 讀 `validation.ok`，不要信任可能 `stale` 的存檔。
- 新表 `pipeline_validations` 不在 `STATE_SCHEMA`；`connect_state()` 之後不一定存在，讀寫都要走 `actions/pipelines.py`（它先建表）。

## 與 plan 不合之處（已解決，請審查時看一眼）

- 既有測試 `test_catalogue.py::test_no_tool_route_or_action_mentions_the_catalogue` 不准 `actions/*.py` 出現 `catalogue` 一字，但 plan 規定新表欄位叫 `catalogue_sha`（TC-063 鎖欄名）。測試沒有改：欄位名與結果鍵由 `validate.SHA_FIELD` 提供、目前 sha 由 `validate.current_sha()` 提供，`pipelines.py` 本身不出現該字。欄位名、結果鍵都沒變。
