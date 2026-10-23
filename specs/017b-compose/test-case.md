# 測試案例：017b 組裝積木——畫布圖的資料模型、每人一份的儲存、轉成 Nextflow 專案檔（純後端）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務沒有 spec.md；依據是 `plan.md`（含「維護者原話」「作法 A／B／C／D」「夾具與標準答案」「失敗先行測試」「裁決」「專長守則（backend）」）。每條預期結果都出自 plan 明寫的內容，沒有另外發明。
-->

**規格**：`specs/017b-compose/plan.md`（沒有 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」。

名詞：「圖」＝畫布上的一張組合（節點＝一個 nf-core 模組，邊＝一個模組的輸出接到另一個模組的輸入）。「標準形式」＝`normalize` 整理後的固定寫法（排序好、補上 sha），同一張圖不論輸入順序都得到同一份。「golden」＝計畫「夾具與標準答案」寫死的標準輸出。「快照」＝提交在 repo 的 `nf-core-modules.json`（2,116 個模組，sha `5ed90b42e78410e7411e9c6bdfeff33226d6c58e`）。「process 名」＝模組在 Nextflow 裡的名字（由 `path` 換成大寫底線產生）。「開放輸入」＝沒有任何邊接上的輸入通道。「別人的」＝另一位使用者建的組合。除非另標，純函式測試在 `platform/tests/test_compose.py`，儲存測試在 `platform/tests/test_pipelines_store.py`；兩處的 `fastqc_multiqc` 圖與標準答案原樣取自 plan。

## User Story 1 — 圖的形狀、驗證與標準形式（`compose.normalize`）（優先度 P1）

維護者原話：「拖模組、連線、填參數……不做巢狀子流程。」「積木＝nf-core 模組……pipeline 與 module 都要相容所有 nf-core 既有的。」總表 017b 失敗先行：「兩節點圖產出一 include 一 edge」。→ 節點只能是目錄裡的模組；參數存在節點上；舊格式模組也要能用；同一張圖永遠得到同一份標準形式。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話「兩節點圖」；作法 A | 功能 | plan 作法 A 那張圖：節點 `qc`（fastqc，sha `5ed90b42…`，params `ext.args`＝`--quiet`）與 `report`（multiqc），一條邊 `qc.zip` → `report` 輸入 0 | `normalize(graph)` | `problems` 為空；`canonical` 有 2 個節點、1 條邊；邊內容為 from `qc`／`zip`、to `report`／0 | 自動：`test_compose.py` |
| TC-002 | 作法 A（module 存標準寫法）；`test_module_names_are_stored_canonically` | 功能 | 節點寫 `"module": "FASTQC"` | `normalize` | `canonical` 裡這個節點的 `module` 是 `fastqc` | 自動 |
| TC-003 | 原話「含舊格式」；作法 A；環境事實（name 與 path 對不上） | 功能 | 節點寫 `"module": "strdust"`（全小寫；目錄裡的標準寫法是 `STRdust`） | `normalize` | 沒有 problem；`canonical` 存的是 `STRdust` | 自動 |
| TC-004 | 作法 A（sha 可省略）；`test_missing_sha_is_filled_from_the_snapshot` | 功能 | 節點沒有 `sha` 欄 | `normalize` | `canonical` 的該節點 `sha` 等於快照 sha `5ed90b42e78410e7411e9c6bdfeff33226d6c58e` | 自動 |
| TC-005 | 作法 A（sha 等於快照則可） | 功能 | 節點 `sha` 寫成快照 sha | `normalize` | 沒有 problem | 自動 |
| TC-006 | 作法 A 標準形式；`test_render_is_deterministic_and_order_independent` | 功能 | 同一張圖，把 `nodes`、`edges` 順序打亂、`params` 的鍵順序打亂，得到另一份輸入 | 兩份都 `normalize` | 兩份 `canonical` 相等；序列化文字 `graph_json` 逐字相同 | 自動 |
| TC-007 | 作法 A 標準形式 | 功能 | 節點 id 為 `b`、`a`、`c`；多條邊；一個節點 params 有 `ext.prefix` 與 `ext.args` | `normalize` | 節點依 `id` 排序；邊依 (from.node, from.output, to.node, to.input) 排序；`params` 的鍵依字典序 | 自動 |
| TC-008 | 作法 A（params 可省略視為空） | 功能 | 節點沒有 `params` 欄 | `normalize` | 沒有 problem；該節點的 `params` 是 `{}` | 自動 |
| TC-009 | 作法 A（params 鍵白名單）；裁決 5 | 功能 | 一個節點的 params 含 `ext.args`、`ext.args2`、`ext.args3`…`ext.args9`、`ext.prefix`，值都是短字串 | `normalize` | 沒有 problem | 自動：`test_param_keys_and_values_are_restricted` |
| TC-010 | 作法 A（節點上限 200，超過才拒） | 功能 | 恰好 200 個節點（id 各不同、同一個模組）、沒有邊 | `normalize` | 沒有 problem | 自動：`test_limits_nodes_edges_and_size` |
| TC-011 | 作法 A（值 ≤ 1000 字元） | 功能 | 一個 `ext.args` 值恰好 1000 個字元 | `normalize` | 沒有 problem | 自動 |
| TC-012 | 作法 A（sha 不符則拒）；`test_wrong_sha_is_refused` | 例外 | 節點 `sha` 寫成 40 個 0 | `normalize` | 回 `canonical` 為 `None`；有 problem 說明這個 sha 不是目前快照的 sha | 自動 |
| TC-013 | 作法 A；`test_unknown_module_is_refused_and_names_it` | 例外 | 節點 `"module": "fastqcc"`（目錄裡沒有） | `normalize` | `canonical` 為 `None`；problem 含 `fastqcc` 這個名字，也含 `search`（告訴使用者去查名字） | 自動 |
| TC-014 | 作法 A（輸出通道必須存在）；`test_edge_to_a_missing_output_channel_lists_the_real_ones` | 例外 | 邊 from 寫 `qc.zipp`（fastqc 真實輸出只有 `html`、`zip`） | `normalize` | `canonical` 為 `None`；problem 含 `qc.zipp`、含真實名字 `html` 與 `zip`；中英並陳，例如「邊 qc.zipp 沒有這個輸出通道，可選：html、zip (module fastqc has no output channel zipp; choose one of: html, zip)」 | 自動 |
| TC-015 | 作法 A（輸出通道名須是合法識別字） | 例外 | 以注入的模組目錄 `data=` 做一個輸出通道名為 `my-out`（含減號）的模組，邊從它接出 | `normalize(graph, data)` | `canonical` 為 `None`；problem 含「這個輸出通道名不能接線」並點名 `my-out` | 自動 |
| TC-016 | 作法 A（輸入編號必須存在）；`test_edge_to_a_missing_input_channel_is_refused` | 例外 | 邊的 to 指向 multiqc 的輸入 5（multiqc 只有輸入 0） | `normalize` | 被拒；problem 指出這個輸入編號不存在 | 自動 |
| TC-017 | 作法 A（`to.input` 須為整數） | 例外 | 邊的 to.input 寫成字串 `"0"` | `normalize` | 被拒 | 自動 |
| TC-018 | 作法 A；`test_edge_to_a_missing_node_is_refused`（接到不存在的節點） | 例外 | 邊的 to.node 是圖裡沒有的 `nope` | `normalize` | 被拒；problem 點名 `nope` | 自動 |
| TC-019 | 作法 A（邊指向不存在的節點，起點端） | 例外 | 邊的 from.node 是圖裡沒有的 `nope` | `normalize` | 被拒；problem 點名 `nope` | 自動 |
| TC-020 | 作法 A；`test_duplicate_edge_is_refused` | 例外 | 同一條邊（四個欄位完全相同）寫了兩次 | `normalize` | 被拒 | 自動 |
| TC-021 | 作法 A；`test_cycles_and_self_loops_are_refused` | 例外 | 一個節點的輸出接到自己的輸入 | `normalize` | 被拒 | 自動 |
| TC-022 | 作法 A；同上 | 例外 | 節點 a 接到 b、b 又接回 a（a→b→a） | `normalize` | 被拒 | 自動 |
| TC-023 | 作法 A（id 格式 `^[a-z][a-z0-9_]{0,31}$`） | 例外 | 分別試四個 id：`QC`（大寫）、`1qc`（數字開頭）、`_qc`（底線開頭）、33 個字元長的 id | `normalize` | 四個都被拒；problem 點名該 id | 自動 |
| TC-024 | 作法 A（id 不重複） | 例外 | 兩個節點用同一個 id `qc` | `normalize` | 被拒；problem 點名 `qc` | 自動 |
| TC-025 | 作法 A（頂層只准 nodes、edges）；裁決 2 | 例外 | 圖的頂層多一個 `inputs` 鍵 | `normalize` | 被拒；problem 點名 `inputs` | 自動 |
| TC-026 | 作法 A（節點 0 個） | 例外 | `nodes` 是空清單 | `normalize` | 被拒 | 自動 |
| TC-027 | 作法 A（節點超過 200）；`test_limits_nodes_edges_and_size` | 例外 | 201 個節點 | `normalize` | 被拒，problem 中英並陳 | 自動 |
| TC-028 | 作法 A（邊超過 1000） | 例外 | 一張不成環、其他都合法的圖，有 1001 條互不相同的邊 | `normalize` | 被拒，problem 中英並陳；拒絕的原因只能是邊數過多（圖本身沒有別的毛病） | 自動 |
| TC-029 | 作法 A（序列化後超過 256 KiB） | 例外 | 一張其他都合法、但序列化後超過 256 KiB 的圖（節點數與邊數都在上限內） | `normalize` | 被拒，problem 中英並陳 | 自動 |
| TC-030 | 作法 A（params 鍵白名單）；`test_param_keys_and_values_are_restricted` | 例外 | 節點 `qc` 的 params 含 `publishDir` | `normalize` | 被拒；problem 同時點名節點 `qc` 與鍵 `publishDir` | 自動 |
| TC-031 | 作法 A（鍵正規式 `^ext\.(args[2-9]?|prefix)$`） | 例外 | 節點 params 含 `ext.args1`（另試 `ext.args10`） | `normalize` | 兩個都被拒；problem 點名節點與該鍵 | 自動 |
| TC-032 | 作法 A（值不含換行） | 例外 | `ext.args` 的值含換行字元 | `normalize` | 被拒；problem 點名節點與鍵 | 自動 |
| TC-033 | 作法 A（值不含其他控制字元） | 例外 | `ext.args` 的值含 `\x07`（另試 `\t`、`\x00`） | `normalize` | 都被拒；problem 點名節點與鍵 | 自動 |
| TC-034 | 作法 A（值只准字串） | 例外 | `ext.args` 的值是整數 `5`（另試 `true`、清單） | `normalize` | 都被拒；problem 點名節點與鍵 | 自動 |
| TC-035 | 作法 A（值 ≤ 1000 字元） | 例外 | `ext.args` 的值有 1001 個字元 | `normalize` | 被拒；problem 點名節點與鍵 | 自動 |
| TC-036 | 作法 A（problem 中英並陳並說怎麼改）；`test_problems_are_bilingual_and_say_what_to_do` | 例外 | 取 TC-012 至 TC-035 各種被拒情況產生的所有 problem | 逐條檢查 | 每一條都含中文字，也含 ASCII 英文的括號段 | 自動 |
| TC-037 | 作法 A（有 problem 就不回 canonical） | 例外 | 一張圖同時有兩個毛病（未知模組＋重複 id） | `normalize` | 回傳的 `canonical` 是 `None`；`problems` 非空 | 自動 |

## User Story 2 — 轉成 Nextflow 專案檔（`compose.render`）（優先度 P1）

維護者原話：「轉出來的 modules.json 與 include 寫法要照 nf-core 既有格式；目錄裡任何一個模組（含舊格式 meta.yml 的）都要能被轉。」「不自建工具庫」→ 只寫「用哪個模組、哪個 sha」，不複製模組內容。總表：「兩節點圖產出一 include 一 edge」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 完成標準 1；`test_fastqc_multiqc_renders_the_golden`；原話「兩節點圖」 | 功能 | `fixtures/compose/fastqc_multiqc/graph.json`（plan 作法 A 那張圖） | `render(normalize(graph)[0], "demo-qc", 1)` | `files["main.nf"]` 與 plan 標準答案逐字相同：有兩條 include（FASTQC、MULTIQC）、一個 `ch_qc_in0 = Channel.empty()  // OPEN INPUT: qc input 0 (meta, reads)`、`FASTQC(ch_qc_in0)`、`MULTIQC(FASTQC.out.zip)` | 自動：`test_compose.py` |
| TC-039 | 同上（modules.json 標準答案） | 功能 | 同 TC-038 | 同 TC-038 | `files["modules.json"]` 與 plan 標準答案逐字相同（`name` 為 `demo-qc`、`homePage` 為空字串、fastqc 與 multiqc 各一項，sha 都是 `5ed90b42…`） | 自動 |
| TC-040 | 同上（nextflow.config 標準答案） | 功能 | 同 TC-038 | 同 TC-038 | `files["nextflow.config"]` 與 plan 標準答案逐字相同（manifest 名 `demo-qc`、版本 `0.1.0`、只有 `withName: 'FASTQC'` 一段、`ext.args = '--quiet'`） | 自動 |
| TC-041 | 作法 B 規則 5；同上 | 功能 | 同 TC-038 | 同 TC-038 | `open_inputs` 恰好等於 `[{"node": "qc", "input": 0, "names": ["meta", "reads"]}]` | 自動 |
| TC-042 | 作法 B main.nf 規則 1、4 | 功能 | 同 TC-038 | 渲染 `demo-qc` 版本 1 | `main.nf` 第一行是 `#!/usr/bin/env nextflow`；第二行是 `// Generated by abf-platform compose (pipeline demo-qc v1); do not edit by hand.`；第三行是空行；檔案結尾恰有一個換行字元（不是零個也不是兩個） | 自動 |
| TC-043 | 作法 B「同一張圖永遠逐字相同」；`test_render_is_deterministic_and_order_independent` | 功能 | TC-006 的兩份打亂順序的輸入 | 各自 `normalize` 後同名同版本 `render`；其中一份再 `render` 一次 | 三次結果（三個檔與 `open_inputs`）逐字相同 | 自動 |
| TC-044 | 裁決 10 | 功能 | 同一張標準形式的圖 | 用版本 1 與版本 3 各 `render` 一次（同名） | `main.nf` 檔頭與 `nextflow.config` 的檔頭、manifest 版本不同（`v1`／`0.1.0` 對 `v3`／`0.3.0`）；`modules.json` 兩次逐字相同 | 自動 |
| TC-045 | 作法 B 規則 2；環境事實（18 個 name 與 path 對不上）；`test_process_name_comes_from_the_path_not_the_name` | 功能 | 圖裡有一個 `STRdust` 節點（path 是 `strdust`），夾具 `old_format_module/` | `render` | `main.nf` 的 include 是 `include { STRDUST } from './modules/nf-core/strdust/main'`；呼叫用 `STRDUST(…)`；整個檔案找不到 `STRdust` 這個寫法當 process 名 | 自動 |
| TC-046 | 同上 | 功能 | 圖裡有一個 `CUSTOM_CLUSTERMETRICS` 節點（path 是 `custom/clustermetrics`），同夾具 | `render` | include 是 `include { CUSTOM_CLUSTERMETRICS } from './modules/nf-core/custom/clustermetrics/main'`；呼叫用 `CUSTOM_CLUSTERMETRICS(…)` | 自動 |
| TC-047 | 作法 B 規則 2（`samtools/sort` → `SAMTOOLS_SORT`） | 功能 | 圖裡有一個 `samtools_sort` 節點（path 是 `samtools/sort`），只出現一次 | `render` | include 是 `include { SAMTOOLS_SORT } from './modules/nf-core/samtools/sort/main'` | 自動 |
| TC-048 | 原話「目錄裡任何一個模組都要能被轉」；`test_every_catalogue_module_has_a_valid_process_name` | 功能 | 快照全部 2,116 個模組 | 每個模組算 process 名（path 的 `/` 換 `_` 再轉大寫） | 每個都符合 `^[A-Z][A-Z0-9_]*$`；2,116 個彼此不重複（若有重複，這條紅燈，executor 回報，不得自行改規則） | 自動 |
| TC-049 | 作法 B 規則 2（每個不同模組一行、依 process 名排序） | 功能 | 圖含 multiqc 與 fastqc（節點 id 故意讓 multiqc 排在前面） | `render` | include 兩行；`FASTQC` 在 `MULTIQC` 之前 | 自動 |
| TC-050 | 作法 B 規則 2（同模組多節點用別名）；`test_fan_in_uses_mix_and_twins_get_aliases` | 功能 | 夾具 `fan_in_and_twins/`：兩個 `samtools_sort` 節點 `s1`、`s2`，加一個 multiqc | `render` | include 有 `include { SAMTOOLS_SORT as SAMTOOLS_SORT_S1 } from './modules/nf-core/samtools/sort/main'` 與 `… as SAMTOOLS_SORT_S2 …` 各一行；不存在不帶別名的 `include { SAMTOOLS_SORT }` | 自動 |
| TC-051 | 作法 B 規則 2（只出現一次就不用別名） | 功能 | 同 TC-050 的圖 | `render` | multiqc 的 include 是不帶別名的 `include { MULTIQC } from './modules/nf-core/multiqc/main'` | 自動 |
| TC-052 | 作法 B 規則 3（多條邊用 mix）；plan 夾具描述 | 功能 | 同 TC-050；multiqc 輸入 0 同時接 `s1.bam` 與 `s2.bam` | `render` | 呼叫行是 `MULTIQC(SAMTOOLS_SORT_S1.out.bam.mix(SAMTOOLS_SORT_S2.out.bam))` | 自動 |
| TC-053 | 作法 B 規則 3（串多個就連續 `.mix(`） | 功能 | 三個 `samtools_sort` 節點 `s1`、`s2`、`s3` 的 `bam` 都接到 multiqc 輸入 0 | `render` | multiqc 的那個參數依序含 `…_S1.out.bam`、`…_S2.out.bam`、`…_S3.out.bam` 三個來源，來源之間以 `.mix(` 串接，沒有任何一個被丟掉 | 自動 |
| TC-054 | 作法 B 規則 3（依 (來源節點, 輸出名) 排序） | 功能 | 同 TC-052，但 `s2` 的邊在邊清單裡寫在 `s1` 的前面 | `normalize` 後 `render` | 呼叫行與 TC-052 逐字相同（S1 在前、S2 在後） | 自動 |
| TC-055 | 作法 B 規則 2（拓撲順序） | 功能 | 兩個節點：id 為 `zz` 的 fastqc 接到 id 為 `aa` 的 multiqc | `render` | `workflow {` 裡 `FASTQC(…)` 那行在 `MULTIQC(…)` 那行之前（來源先於使用者，即使使用者的 id 字典序較小） | 自動 |
| TC-056 | 作法 B 規則 2（同層取 id 字典序最小者） | 功能 | 同 TC-050（`s1`、`s2` 彼此無關） | `render` | 呼叫順序是 `SAMTOOLS_SORT_S1(…)`、`SAMTOOLS_SORT_S2(…)`，再 `MULTIQC(…)` | 自動 |
| TC-057 | 作法 B 規則 3（參數個數＝不同輸入通道編號的個數） | 功能 | 圖含 fastqc（輸入通道 0）、samtools_sort（0、1、2）、STRdust（0、1、2、3）各一個 | `render` | `FASTQC` 呼叫有 1 個參數；`SAMTOOLS_SORT` 有 3 個；`STRDUST` 有 4 個（multiqc 的 6 個輸入名同屬通道 0，只算 1 個參數） | 自動 |
| TC-058 | 作法 B 規則 3（沒接的輸入）；plan 夾具描述 | 功能 | 夾具 `fan_in_and_twins/`，`s1` 的三個輸入通道都沒有邊 | `render` | `workflow {` 開頭有 `ch_s1_in0`、`ch_s1_in1`、`ch_s1_in2` 各一行，每行形如 `ch_s1_in1 = Channel.empty()  // OPEN INPUT: s1 input 1 (meta2, fasta, fai)`；通道 0 的括號內是 `meta, bam`、通道 2 的是 `index_format` | 自動 |
| TC-059 | 作法 B 規則 3（出現在呼叫之前、依 (id, i) 排序） | 功能 | 同 TC-058（`s1`、`s2` 共六個開放輸入） | `render` | 六行 `Channel.empty()` 全部在第一個呼叫行之前，順序為 `s1` 的 0、1、2，再 `s2` 的 0、1、2 | 自動 |
| TC-060 | 作法 B 規則 5 | 功能 | 同 TC-058 | `render` | `open_inputs` 有六筆，每筆含 `node`、`input`、`names`，順序與 TC-059 的行順序相同；`s1` 輸入 1 的 names 是 `["meta2", "fasta", "fai"]` | 自動 |
| TC-061 | 作法 B 規則 3（有邊就不是開放輸入） | 功能 | 同 TC-038（multiqc 輸入 0 已接 `qc.zip`） | `render` | `main.nf` 裡沒有 `ch_report_in0`；`open_inputs` 裡沒有 `report` | 自動 |
| TC-062 | 裁決 3（沒接的輸入不是錯誤） | 功能 | 同 TC-038（fastqc 輸入 0 沒接） | `render` | 正常回傳三個檔與非空的 `open_inputs`，沒有丟例外、沒有 problem | 自動 |
| TC-063 | 作法 B modules.json；`test_modules_json_matches_nf_core_shape` | 功能 | 同 TC-050 的圖 | `json.loads(files["modules.json"])` | 最外層只有 `name`、`homePage`、`repos`；`repos["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]` 的每一項恰好只有 `branch`、`git_sha`、`installed_by` 三個鍵 | 自動 |
| TC-064 | 作法 B modules.json（有斜線用整條路徑當鍵） | 功能 | 圖含 `samtools_sort`、`STRdust`、`CUSTOM_CLUSTERMETRICS` | 同上 | 鍵是 `samtools/sort`、`strdust`、`custom/clustermetrics`（用 path，不是 name，也不是 `STRdust`） | 自動 |
| TC-065 | 作法 B modules.json（同模組多節點只列一次） | 功能 | 同 TC-050（兩個 samtools_sort 節點） | 同上 | `samtools/sort` 這個鍵只出現一次 | 自動 |
| TC-066 | 作法 B modules.json（git_sha＝節點的 sha） | 功能 | 同 TC-038 | 同上 | 每一項 `git_sha` 等於節點的 `sha`；`branch` 是 `master`；`installed_by` 是 `["modules"]` | 自動 |
| TC-067 | 作法 B modules.json（`indent=4, sort_keys=True` 加結尾換行） | 功能 | 同 TC-038 | 取 `files["modules.json"]` 文字 | 文字等於 `json.dumps(json.loads(文字), indent=4, sort_keys=True, ensure_ascii=False) + "\n"` | 自動 |
| TC-068 | 作法 B nextflow.config（manifest） | 功能 | 同一張圖用名字 `demo-qc`、版本 3 渲染 | `render` | config 含 `name = 'demo-qc'` 與 `version = '0.3.0'`，檔頭註解寫 `pipeline demo-qc v3` | 自動 |
| TC-069 | 作法 B nextflow.config（有 params 才出 process 區塊） | 功能 | 圖裡所有節點都沒有 params | `render` | config 只有檔頭註解與 `manifest { … }`，找不到 `process {` | 自動 |
| TC-070 | 作法 B nextflow.config（withName、節點依 id 排序、鍵依字典序、別名用別名名） | 功能 | 夾具 `fan_in_and_twins/`：`s1`、`s2` 都有 params（含 `ext.prefix` 與 `ext.args`） | `render` | config 的 `process {` 裡有 `withName: 'SAMTOOLS_SORT_S1'` 在 `withName: 'SAMTOOLS_SORT_S2'` 之前；每段內 `ext.args` 在 `ext.prefix` 之前；沒有 params 的 multiqc 沒有段落 | 自動 |
| TC-071 | 作法 B 跳脫；`test_param_strings_are_escaped_in_the_config` | 功能 | 某節點 `ext.args` 的值是 `a'b$c\d` | `render` | config 裡該行是 `ext.args = 'a\'b\$c\\d'` | 自動 |
| TC-072 | 作法 B 跳脫（防止 Groovy 插值） | 功能 | 同 TC-071 | 用字元掃描（或 `ast`）逐字元檢查該字串 | 單引號字串內沒有任何未被反斜線跳脫的單引號，也沒有未跳脫的 `$` | 自動 |
| TC-073 | 作法 B 跳脫（渲染時再檢查一次）；`test_render_refuses_a_control_character_even_if_normalize_was_skipped` | 例外 | 直接手寫一份壞的 canonical（`ext.args` 值含換行），不經過 `normalize` | `render` | 丟出 `ValueError` | 自動 |
| TC-074 | 原話「不自建工具庫」；作法 B 輸出形狀 | 功能 | 同 TC-038 | `render` | `files` 的鍵恰好是 `main.nf`、`modules.json`、`nextflow.config` 三個，沒有第四個（沒有 `nextflow_schema.json`、沒有模組檔） | 自動 |
| TC-075 | 作法 B「純函式，不讀網路、不寫檔」 | 功能 | 在空的暫存工作目錄執行；網路連線被測試擋掉 | `render` 一次 | 正常回傳；工作目錄裡沒有新增任何檔案；沒有嘗試連網 | 自動 |
| TC-076 | 作法 B；`test_compose_module_is_pure` | 功能 | `platform/abf_platform/compose.py` 原始碼 | 掃描原始碼 | 不含 `import store`、`sqlite3`、`urllib`、`requests`、`socket`、`subprocess`、`open(` | 自動 |
| TC-077 | 夾具與標準答案（三組）；`test_process_name_comes_from_the_path_not_the_name`、`test_fan_in_uses_mix_and_twins_get_aliases` | 功能 | `fixtures/compose/` 的 `fastqc_multiqc/`、`fan_in_and_twins/`、`old_format_module/` 三個資料夾，各有 `graph.json`、`main.nf`、`modules.json`、`nextflow.config` | 各自 `normalize` 後 `render`（名字與版本依各夾具的標準答案檔頭） | 三組的三個檔都與夾具裡的標準答案逐字相同；`fastqc_multiqc/` 的標準答案與 plan 文字一字不差 | 自動 |
| TC-078 | plan 夾具描述（`params` 含單引號與 `$` 驗證跳脫） | 功能 | 夾具 `fan_in_and_twins/` 的 `graph.json` 有一個 `ext.args` 含單引號與 `$` | 讀該夾具的 `nextflow.config` 標準答案 | 該值在檔案中已被跳脫（`\'`、`\$`），且與 `render` 的輸出相同 | 自動 |

## User Story 3 — 每人一份、有版本的儲存（`actions/pipelines.py`）（優先度 P1）

維護者原話：「版本只能新增，舊版內容不變」（總表 017b）；「a caller sees and uses only their own，別人的與不存在的回一樣的話」（`docs/PLATFORM.md` 的 Whose it is）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-079 | 作法 C `create_pipeline`／`get_pipeline`；`test_create_then_get_roundtrips_the_canonical_graph` | 功能 | 使用者 A；TC-001 那張圖 | `create_pipeline(name="demo-qc", graph=…, caller=A)`，再 `get_pipeline` 該 id | `get` 回 `ok` 與 `found` 為真，`name`＝`demo-qc`，`version`＝1，`versions`＝`[1]`，`graph` 等於 `normalize` 的 canonical | 自動：`test_pipelines_store.py` |
| TC-080 | 作法 C（回傳形狀） | 功能 | 同 TC-079 | 看 `create_pipeline` 的回傳 | `{"ok": True, "pipeline": {"id", "name", "version": 1, "created_at"}}`，四個欄位都在 | 自動 |
| TC-081 | 作法 A 標準形式（graph_json 寫法） | 功能 | 同 TC-079 | 直接讀資料庫 `pipeline_versions` 的 `graph_json` | 該文字等於 `json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))` | 自動 |
| TC-082 | 作法 C `update_pipeline`；原話「每次存檔留一個版本」；`test_update_appends_a_version_and_old_ones_do_not_change` | 功能 | 已建好的組合（版本 1） | 用兩張不同的圖各 `update_pipeline` 一次 | 版本變成 2、3；`get_pipeline` 的 `versions` 是 `[1, 2, 3]` | 自動 |
| TC-083 | 原話「版本 append-only，舊版內容不變」 | 功能 | 同 TC-082，已存到版本 3 | 讀資料庫版本 1 的 `graph_json`；`get_pipeline(version=1)` | 版本 1 的 `graph_json` 與第一次存下時逐位元相同；`get_pipeline(version=1)` 仍回舊圖 | 自動 |
| TC-084 | 作法 C `get_pipeline`（沒給版本＝最新） | 功能 | 同 TC-082 | 不帶版本呼叫 `get_pipeline` | 回版本 3 的圖，`version`＝3 | 自動 |
| TC-085 | 作法 C `update_pipeline`（同圖不新增）；`test_update_with_the_same_graph_makes_no_new_version` | 功能 | 組合最新版是某張圖 | 用逐字相同的標準形式再 `update_pipeline`（輸入順序可不同） | 回 `{"ok": True, "unchanged": True, "pipeline": {…同最新版…}}`；`pipeline_versions` 的列數不變 | 自動 |
| TC-086 | 作法 C `list_pipelines`；擁有者規則 | 功能 | A 有兩個組合（其一有 2 個版本），B 有一個 | A 呼叫 `list_pipelines(caller=A)` | 只含 A 的兩個；每筆有 `id`、`name`、`version`（最新）、`n_nodes`、`created_at`、`updated_at` | 自動 |
| TC-087 | 作法 C `list_pipelines`（依 name、id 排序） | 功能 | A 依序建了名字 `zeta`、`alpha` 兩個組合 | `list_pipelines(caller=A)` | `alpha` 在 `zeta` 之前 | 自動 |
| TC-088 | 完成標準 1 | 功能 | A 用 `fastqc_multiqc` 圖建立名為 `demo-qc` 的組合 | `render_pipeline` 取回 | 三個檔與 plan 標準答案逐字相同（`version`＝1，`name`＝`demo-qc`） | 自動 |
| TC-089 | 作法 C `render_pipeline`（版本參數） | 功能 | 組合有版本 1、2（圖不同） | `render_pipeline(version=1)` 與不帶版本各呼叫一次 | 前者用版本 1 的圖、檔頭寫 `v1`；後者用版本 2 的圖、檔頭寫 `v2` | 自動 |
| TC-090 | 作法 C `render_pipeline`（回傳形狀） | 功能 | 同 TC-088 | 看回傳 | 含 `ok`、`name`、`version`、`files`、`open_inputs` | 自動 |
| TC-091 | 作法 C `create_pipeline`（同擁有者內同名才擋）；`test_same_name_twice_is_refused_per_owner_but_other_owner_may_reuse_it` | 功能 | A 已有名為 `demo-qc` 的組合 | B 用同名 `demo-qc` 建立 | 成功（B 可以重用 A 的名字） | 自動 |
| TC-092 | 作法 C（`caller=None`＝終端機看得到全部）；`test_terminal_caller_none_sees_everything` | 功能 | A、B 各有組合 | `caller=None` 呼叫 `list_pipelines`、`get_pipeline`、`render_pipeline` | 列出兩人全部組合；能取得與渲染任何一個 | 自動 |
| TC-093 | 裁決 6（終端機建的組合只有終端機看得到） | 功能 | 以 `caller=None` 建一個組合（擁有者為空） | A 呼叫 `list_pipelines`、`get_pipeline` | 清單不含它；`get` 回找不到 | 自動 |
| TC-094 | 作法 D；`test_old_platform_db_works_without_a_migration` | 功能 | 舊的 `platform.db`（只由 `connect_state` 建，沒有這兩張表） | 直接 `list_pipelines` | 回 `{"ok": True, "pipelines": []}`，不丟例外 | 自動 |
| TC-095 | 作法 D（舊庫即用） | 功能 | 同 TC-094，接在其後 | `create_pipeline` | 成功；表在第一次使用時建立 | 自動 |
| TC-096 | 作法 D（讀取函式自己先建表） | 功能 | 同 TC-094（沒有表） | 直接 `get_pipeline` 一個 id | 回找不到（`found` 為假），不丟例外 | 自動 |
| TC-097 | 作法 C（建立與版本 1 同一個交易） | 功能 | 讓寫入版本 1 的那一步失敗（測試注入錯誤） | `create_pipeline` | 回失敗；`pipelines` 裡沒有留下半個組合（兩張表都是 0 列） | 自動 |
| TC-098 | 作法 C `create_pipeline`；`test_invalid_graph_writes_nothing` | 例外 | 圖有 problem（例如未知模組） | `create_pipeline` | 回 `{"ok": False, "message": <第一條 problem>, "problems": […]}`；之後 `pipelines`、`pipeline_versions` 都是 0 列 | 自動 |
| TC-099 | 作法 C（name 格式 `^[a-z][a-z0-9-]{0,39}$`） | 例外 | 分別試名字：`Demo`（大寫）、`1demo`、`my_qc`（底線）、41 個字元長 | `create_pipeline` | 四個都被拒；什麼都沒寫入 | 自動 |
| TC-100 | 作法 C（同名訊息） | 例外 | A 已有 `demo-qc` | A 再 `create_pipeline(name="demo-qc")` | `ok` 為假；`message` 是「你已經有一個叫 demo-qc 的組合；用 update 存新版本 (a pipeline named demo-qc already exists; save a new version instead)」；列數不變 | 自動 |
| TC-101 | 作法 C（`owner IS ?` 的重複檢查，NULL 擁有者） | 例外 | 以 `caller=None` 建了 `demo-qc` | 再以 `caller=None` 建同名 | 被拒，訊息同 TC-100（資料庫的 UNIQUE 對 NULL 不生效，由程式檢查） | 自動 |
| TC-102 | 作法 C `update_pipeline` | 例外 | 組合存在 | 用有 problem 的圖 `update_pipeline` | 被拒；版本數不變 | 自動 |
| TC-103 | 作法 C（找不到的訊息） | 例外 | 沒有 id 為 999 的組合 | `update_pipeline(999, …)` | `message` 是「找不到這個組合 (pipeline not found): 999」 | 自動 |
| TC-104 | 作法 C `get_pipeline`（版本不存在） | 例外 | 組合只有版本 1 | `get_pipeline(version=5)` | `{"ok": False, "found": False, "message": …}` | 自動 |
| TC-105 | 作法 C `get_pipeline`（組合不存在） | 例外 | 沒有 id 為 999 的組合 | `get_pipeline(999)` | `ok` 與 `found` 都為假，有 `message` | 自動 |
| TC-106 | 作法 C 觸發器；`test_versions_table_refuses_update_and_delete` | 例外 | 已有一個版本列 | 直接對 `pipeline_versions` 下 `UPDATE` | 被資料庫拒絕（`sqlite3.IntegrityError` 或 `OperationalError`，訊息含 `pipeline versions are append-only`）；該列內容不變 | 自動 |
| TC-107 | 同上 | 例外 | 同上 | 直接對 `pipeline_versions` 下 `DELETE` | 被資料庫拒絕；該列仍在 | 自動 |
| TC-108 | 專長守則：跨使用者（讀）；`test_other_user_cannot_get_list_or_render` | 例外 | A 建了組合 | B 呼叫 `get_pipeline(A 的 id)` | 回找不到（`found` 為假） | 自動 |
| TC-109 | 專長守則：跨使用者（讀） | 例外 | 同 TC-108 | B 呼叫 `render_pipeline(A 的 id)` | 回找不到；沒有任何檔案內容 | 自動 |
| TC-110 | 專長守則：跨使用者（讀） | 例外 | 同 TC-108 | B 呼叫 `list_pipelines(caller=B)` | 清單不含 A 的組合 | 自動 |
| TC-111 | 擁有者規則「別人的與不存在的同一句」（仿 `test_datasets.py` TC-076） | 例外 | A 的組合 id 與一個不存在的 id | B 對兩者各 `get_pipeline` | `words(別人的訊息, name) == words(不存在的訊息, name)`（兩句拿掉被問的名字／id 後完全相同） | 自動 |
| TC-112 | 同上（更新） | 例外 | 同 TC-111 | B 對兩者各 `update_pipeline` | 兩句相同，都是「找不到這個組合 (pipeline not found): <id>」 | 自動 |
| TC-113 | 專長守則：跨使用者（寫）；`test_other_user_cannot_update` | 例外 | A 的組合有 1 個版本 | B 對 A 的組合 `update_pipeline`（用合法的圖） | 被拒；A 的版本數仍是 1，A 的最新圖沒變 | 自動 |
| TC-114 | 專長守則：錯誤訊息；`test_error_messages_hide_internals` | 例外 | 觸發 TC-098、100、103、105 的各種被拒回應，並收集當時的日誌 | 檢查回應與日誌 | 不含 SQL 字樣、堆疊（Traceback）、`platform.db` 路徑；每句說明發生什麼事與該怎麼做 | 自動 |

## User Story 4 — 這次不做的事（優先度 P2）

計畫「不做」與「裁決」明講：不加工具與路由、不做型別檢查、不抓網路／不組 zip、不做分享、不改名不刪除、不做巢狀子流程、不接 versions、不收圖層級的 inputs／params、不複製模組內容。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-115 | 不做 1：不加 MCP 工具 | 不在範圍 | 本任務完成 | `git diff` 看 `platform/abf_platform/mcp_server.py`；跑含工具數斷言的既有測試（`test_pat.py`、`test_oauth_mcp.py`、`test_estimate_su.py`） | `mcp_server.py` 沒有變動；工具數斷言不用改且全綠（沒有 `compose_pipeline`、`export_pipeline` 之類的新工具） | 自動 |
| TC-116 | 不做 1：不加網頁路由 | 不在範圍 | 本任務完成 | `git diff` 看 `web.py`；跑 `test_web_parity.py` | `web.py` 沒有變動；`test_web_parity.py` 沒改且仍綠 | 自動 |
| TC-117 | 範圍：不准動 `actions/__init__.py`；專長守則對等性 | 不在範圍 | 本任務完成 | 看 `actions/__init__.py` 的 diff；列出 `actions` 套件的公開名字 | `__init__.py` 沒有變動；公開名字裡沒有 `create_pipeline`、`update_pipeline`、`list_pipelines`、`get_pipeline`、`render_pipeline`（它們只在子模組 `actions.pipelines`） | 自動 |
| TC-118 | 不做 2、裁決 2：不做型別相容檢查 | 不在範圍 | 圖中 fastqc 的 `html`（檔案）接到 `samtools_sort` 的輸入 2（`index_format`，字串型） | `normalize` | 沒有 problem（本版只確認邊兩端存在與不成環） | 自動 |
| TC-119 | 不做 3：不抓 GitHub、不組 zip、不寫檔 | 不在範圍 | `compose.py` 與 `pipelines.py` 原始碼 | 掃描 | 不含 `zipfile`、`tarfile`、`shutil`、`urllib`、`requests`、`socket`；`render` 只回字串 | 自動 |
| TC-120 | 不做 5、裁決 2：不做分享連結與 validation | 不在範圍 | 建好兩張表 | 讀兩張表的欄位 | 沒有 `shared_token`、`validation_json`；任何函式都沒有分享相關的名字 | 自動 |
| TC-121 | 不做 6：不做改名、刪除組合、刪除版本 | 不在範圍 | `actions/pipelines.py` | 列出模組的公開函式 | 恰好是 `create_pipeline`、`update_pipeline`、`list_pipelines`、`get_pipeline`、`render_pipeline`；沒有 rename、delete、share 之類 | 自動 |
| TC-122 | 原話「不做巢狀子流程」；不做 7 | 不在範圍 | 節點 `"module": "bam_sort_stats_samtools"`（nf-core 的子流程，不在模組目錄） | `normalize` | 被拒，當成未知模組（problem 含該名字與 `search`）；圖裡沒有「子流程」這種節點 | 自動 |
| TC-123 | 不做 8：不接 `versions` 通道 | 不在範圍 | 邊從 fastqc 的 `versions` 接出 | `normalize` | 被拒（`versions` 不是該模組的輸出通道，problem 列出真實的 `html`、`zip`）；TC-038 的 `main.nf` 找不到 `versions` | 自動 |
| TC-124 | 裁決 2：圖層級的 inputs／params 本版不收 | 不在範圍 | 圖的頂層多一個 `params` 鍵 | `normalize` | 被拒，problem 點名 `params`（另見 TC-025 的 `inputs`） | 自動 |
| TC-125 | 原話「不自建工具庫」：不複製、不改寫模組內容 | 不在範圍 | 同 TC-038 | 檢查三個檔的文字 | `main.nf` 裡沒有任何 `process …{` 定義、沒有模組的腳本內容，只有 include 行與呼叫；整個輸出只寫「用哪個模組、哪個 sha」 | 自動 |

## 憲法與安全網

<!-- 觸及的規則：專長守則（backend）六條（共用動作層、確認管道、擁有者、錯誤訊息、密鑰、migration）；`docs/PLATFORM.md` 的 Whose it is；`test_scope.py` TC-070／071／072；`test_launch_static.py` TC-074；`test_http_site_samplesheet.py` TC-057；`tests/platform_storage_doc_test.sh`。裁決 1：存一張圖只寫平台自己的 platform.db，不碰站台、不花 SU，確認管道不適用；以 TC-126、TC-127 證明沒有送出路徑、沒有產生工作。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-126 | 裁決 1；`test_pipelines_store_has_no_submit_path` | 功能 | `actions/pipelines.py` 與 `compose.py` 原始碼 | 掃描 | 不含 `subprocess`、`os.system`、`sbatch`、`srun`、`qsub`、`confirm`、`jobs`、`queue` | 自動 |
| TC-127 | 裁決 1；`test_no_confirmation_or_job_is_made` | 功能 | 記下 `jobs`、`confirmations`、`launches` 三表列數 | 依序 `create_pipeline`、`update_pipeline`、`render_pipeline` | 三表列數前後不變 | 自動 |
| TC-128 | 專長守則（資料結構）；`test_pipelines_columns_say_nothing_about_runs` | 功能 | 建好兩張表 | 讀欄位 | `pipelines` 恰有 `id`、`owner_user_id`、`name`、`created_at`；`pipeline_versions` 恰有 `id`、`pipeline_id`、`version`、`graph_json`、`created_at`；沒有狀態欄、沒有 run 相關欄 | 自動 |
| TC-129 | 作法 D、裁決 7；`test_state_schema_is_untouched` | 功能 | 一個只跑過 `connect_state` 的新 `platform.db` | 讀 `store.STATE_SCHEMA` 與資料庫 | `STATE_SCHEMA` 不含 `pipelines` 字樣；資料庫此時沒有這兩張表 | 自動 |
| TC-130 | 範圍：檔案（最終版） | 功能 | 實作完成 | `git diff <base>...HEAD --stat` | 變動的路徑只在 plan「範圍：檔案」列出的那些；`store.py`、`actions/__init__.py`、`mcp_server.py`、`web.py`、`catalogue.py`、`pyproject.toml`、`constraints.txt` 都沒有變動 | 自動（驗收者讀 diff） |
| TC-131 | 允許更新的既有斷言（一條都不改）；TC-057 | 功能 | `test_http_site_samplesheet.py::test_tc057_no_table_or_column_changed` | 跑該測試；看該檔 diff | 綠；`SCHEMA_SHA256` 沒被更新；該檔沒有變動 | 自動 |
| TC-132 | 同上（其他既有測試） | 功能 | `test_estimate_su.py`、`test_failures.py`、`test_receiver.py`、`test_web_parity.py`、`test_catalogue.py`、`test_guidance.py`、`test_pat.py`、`test_oauth_mcp.py` | 各自跑；看 diff | 全綠，且都沒有被修改 | 自動 |
| TC-133 | 裁決 11；`test_scope.py` TC-070 | 功能 | `compose.py`、`pipelines.py`、`test_compose.py`、`test_pipelines_store.py` | 看前 40 行；跑 `test_scope.py` | 四個檔各有一行 `# Nothing existing: …`，理由 15 字以上；該測試綠 | 自動 |
| TC-134 | `test_scope.py` TC-071 | 功能 | `abf_platform/**/*.py`（含註解與 docstring） | 跑 `test_scope.py` | 不出現 `nextflow run`、`subprocess`、`threading`、`while True` 等字樣；測試綠 | 自動 |
| TC-135 | `test_scope.py` TC-072；`test_launch_static.py` TC-074 | 功能 | `platform/` 底下所有檔，含 `fixtures/compose/*` | 跑兩個測試 | 沒有叢集路徑形狀（`/home/名字/` 等），沒有金鑰形狀；測試綠 | 自動 |
| TC-136 | 專長守則：密鑰不得出現在回應與日誌 | 功能 | 使用者 A 的呼叫者資料帶有 token／密碼雜湊（測試夾具已知其值） | 對五個函式各呼叫一次（含被拒的）並收集日誌 | 任何回應與日誌都不含該 token 或雜湊的字串 | 自動 |
| TC-137 | 裁決 9；文件 | 功能 | `docs/PLATFORM.md` | 讀文件 | 在 `## What the platform stores` 之前有 `## Composed pipelines`；內容含圖的形狀、擁有者、版本只增不改、`render` 輸出三個檔，並明說沒有 MCP 工具或網頁、017e 才開 | 自動：驗收者讀文件（`tests/platform_storage_doc_test.sh` 另跑） |
| TC-138 | 裁決 9；`tests/platform_storage_doc_test.sh` | 功能 | `docs/PLATFORM.md` 的 stores 表 | 看表；跑 `bash tests/platform_storage_doc_test.sh` | 新增一列 `Composed pipelines: …`，Where 欄是 `platform.db`（`pipelines`、`pipeline_versions`），How long 欄含 `no automatic deletion` 與 versions 不改不刪；測試綠；該測試檔沒有被改 | 自動 |
| TC-139 | 完成標準；弱化測試防線 | 功能 | 本任務新增的兩個測試檔 | 對照 plan「失敗先行測試」清單逐條找測試 | 清單中的每個測試名都存在，且斷言不弱於 TC 的預期結果；沒有被跳過（skip）的案例 | 自動（驗收者讀測試） |
| TC-140 | 完成標準 2 | 功能 | 實作完成 | 跑全套 `platform/tests` | 全綠；完成記號 `GREEN <HEAD sha>` 與 HEAD 相符 | 自動 |
| TC-141 | 防止實作中改合約 | 功能 | 實作完成 | `git diff <base>...HEAD` 看 `specs/017b-compose/` | `plan.md`、`test-case.md`、`test-case-overview.md` 沒有被改；只有 `ledger.md` 有變動 | 自動（驗收者讀 diff） |
| TC-142 | 完成標準末條；裁決 3 | 功能 | `specs/017b-compose/ledger.md` | 讀 ledger | 記著「真實 nf-core 模組檔下的 `-stub-run`：未驗證」，以及給 017c 的備忘：`-stub-run` 閘門必須同時看 `open_inputs`，不能只看結束碼 | 手動：驗收者讀 `ledger.md`（`docs/TESTING.md` 尚無此步驟） |
| TC-143 | 作法 D；完成標準 | 功能 | PR 說明 | 讀 PR 說明 | 寫明三件事：不需要 migration 的理由、`connect_state` 之後這兩張表不一定存在、與總表 017b 的差異（見裁決 2） | 手動：驗收者讀 PR 說明（`docs/TESTING.md` 尚無此步驟） |

<!--
Rules for the writer:
- Every acceptance scenario and every FR in spec.md maps to at least one TC. Every
  "out of scope" item in spec.md maps to at least one 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 (a test file under tests/, named once it exists, "自動" until then)
  or 手動 (a step in docs/TESTING.md's manual half). Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
