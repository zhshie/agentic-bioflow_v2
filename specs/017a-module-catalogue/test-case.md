# 測試案例：017a nf-core 模組目錄快照與查詢函式

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務沒有 spec.md；依據是 `plan.md`（含「維護者原話」「作法」「夾具與標準答案」「失敗先行測試」「裁決」）。每條預期結果都出自 plan 明寫的內容，沒有另外發明。
-->

**規格**：`specs/017a-module-catalogue/plan.md`（沒有 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「快照」＝提交在 repo 裡的 `nf-core-modules.json`，把全部 nf-core 模組的說明檔（meta.yml）攤平後存成一份清單。「攤平」＝把 meta.yml 轉成固定欄位的簡單格式。「新格式／舊格式」＝nf-core meta.yml 的兩種寫法（輸入是清單的清單、輸出是字典＝新；輸出是清單＝舊）。「golden」＝計畫「夾具與標準答案」裡寫死的標準輸出。本檔所說的測試都放在 `platform/tests/test_catalogue.py`（除非另標），夾具 FASTQC／SAMTOOLS_SORT／BROKEN 原樣取自 plan。

## User Story 1 — 把 meta.yml 攤平成快照（優先度 P1）

維護者原話：「積木＝nf-core 模組，全部約 1,500 個；pipeline 與 module 都要相容所有 nf-core 既有的。」→ 新舊兩種格式都要讀得懂；「不自建工具庫」→ 只讀、不改寫模組內容。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者原話（新舊格式）；作法 2、3；`test_snapshot_of_three_fixtures_equals_the_golden` | 功能 | 夾具 SAMTOOLS_SORT、BROKEN、FASTQC、`("bad/yaml", "while parsing a block mapping")`，順序如 plan | `build_snapshot([SAMTOOLS_SORT, BROKEN, FASTQC, ("bad/yaml", "while parsing a block mapping")], "abc123")` | 結果與 plan「夾具與標準答案」那一大段完全相等（count 2、兩個模組、兩筆 errors、fastqc 新格式、samtools_sort 舊格式、versions 都不在 outputs） | 自動：`platform/tests/test_catalogue.py` |
| TC-002 | 作法 3「依 name 再 path 排序」 | 功能 | 兩個模組 name 相同、path 不同（例 `b/x`、`a/x`，name 都是 `same`），以及 name 不同的另一個；輸入順序故意倒過來 | `build_snapshot` | `modules` 先依 name、name 相同再依 path 排序 | 自動 |
| TC-003 | 作法 2、3「回傳鍵順序固定」「沒有 generated_at」 | 功能 | golden 的輸出 | 檢查鍵順序 | 頂層鍵依序為 `source, sha, count, modules, errors`；每個模組鍵依序為 `name, path, description, keywords, tools, inputs, outputs`；任何地方都沒有 `generated_at` | 自動 |
| TC-004 | 作法 2 description | 功能 | description 為 `"  a\n b\t c "`；另一個模組沒有 description | `flatten` | 前者變 `"a b c"`（空白壓成單一空格、頭尾去掉）；後者是 `""` | 自動 |
| TC-005 | 作法 2 keywords | 功能 | keywords 為 `["a", 3, None, "b"]`；另一個模組沒有 keywords | `flatten` | 前者只留字串 `["a", "b"]`；後者 `[]` | 自動 |
| TC-006 | 作法 2 tools | 功能 | tools 為單鍵 dict 清單：一個 licence 是字串 `"MIT"`、一個沒有 licence 也沒有 homepage | `flatten` | 第一個 licence 變 `["MIT"]`；第二個 licence 是 `[]`、homepage 是 `None`；每筆形狀 `{"name","homepage","licence"}` | 自動 |
| TC-007 | 作法 2 inputs（新格式） | 功能 | `input` 是兩個 tuple 清單：第一個含 meta、reads；第二個含 index | `flatten` | 第一個 tuple 的兩筆 channel 都是 0，第二個 tuple 的那筆 channel 是 1；每筆有 `channel,name,type,pattern` | 自動 |
| TC-008 | 作法 2 inputs（舊格式） | 功能 | SAMTOOLS_SORT 的 `input`（單鍵 dict 清單：meta、bam） | `flatten` | `meta` 的 channel 是 0、`bam` 的 channel 是 1，bam 的 pattern 是 `*.{bam,cram,sam}` | 自動 |
| TC-009 | 作法 2 outputs（新格式） | 功能 | FASTQC 的 `output`（dict：html、zip、versions_fastqc） | `flatten` | outputs 的 channel 是輸出名 `html`、`zip`，依原順序；每個 channel 先 `meta` 再檔案那筆（`*.html`、`*.zip`），pattern 如 plan | 自動 |
| TC-010 | 作法 2 outputs（舊格式） | 功能 | SAMTOOLS_SORT 的 `output`（清單：meta、bam、versions） | `flatten` | channel 就是各自的鍵：`meta`、`bam` | 自動 |
| TC-011 | 作法 2「versions 開頭整個略過」；`test_versions_channels_are_skipped_in_both_formats`（新格式半） | 功能 | 新格式 `output` 含 `versions_fastqc` 與 `versions` 兩個 channel | `flatten` | outputs 裡沒有任何 channel 名以 `versions` 開頭的項 | 自動 |
| TC-012 | 同上（舊格式半） | 功能 | 舊格式 `output` 清單含 `{"versions": …}` 與 `{"versions_x": …}` | `flatten` | outputs 裡沒有 channel 名以 `versions` 開頭的項，其餘照常保留 | 自動 |
| TC-013 | 作法 2「topics 不讀」 | 功能 | FASTQC（有 `topics`） | `flatten` | 輸出任何地方都沒有 topics 的內容 | 自動 |
| TC-014 | 作法 2「缺的 type／pattern 寫 null」 | 功能 | 一個輸入／輸出項沒有 type、沒有 pattern | `flatten` | 該項 `type` 與 `pattern` 都是 `None`（寫成 JSON 是 null） | 自動 |
| TC-015 | 裁決 4；`test_cluster_like_paths_are_masked` | 功能 | description 含 `/home/alice/x` | `flatten` | 輸出含 `<path>/x`，不含 `/home/alice/` | 自動 |
| TC-016 | 裁決 4「每個輸出的字串欄位」 | 功能 | 叢集式路徑（`/scratch/bob/y`、`/lustre/carol/z` 等）分別放在 keyword、tool 的 homepage、輸入的 pattern | `flatten` | 這三個欄位的輸出都不含原路徑，命中的那段換成 `<path>/` | 自動 |
| TC-017 | 裁決 2；`test_odd_shapes_are_skipped_not_fatal` | 功能 | meta 有 name，`tools: None`、`input: [None, 3, {"a": None}]` | `build_snapshot` | 模組照樣產生（count 1、errors 空），`inputs` 是 `[]`，`tools` 是 `[]` | 自動 |
| TC-018 | 裁決 2「缺或為 null → []」 | 功能 | 一個模組沒有 tools／input／output；另一個這三項都是 `None` | `flatten` | 三項都是 `[]`，不丟例外 | 自動 |
| TC-019 | 作法 2 name、作法 3 | 例外 | BROKEN（沒有 name）；另兩個 meta 的 name 分別是 `""` 與 `123` | `flatten`；再用 `build_snapshot` | `flatten` 丟 `ValueError("meta.yml has no name")`；`build_snapshot` 把三者各記一筆 `{"path", "reason": "meta.yml has no name"}`，不進 modules | 自動 |
| TC-020 | 作法 3「讀檔失敗時呼叫端放字串」 | 例外 | `("bad/yaml", "while parsing a block mapping")` | `build_snapshot` | errors 有 `{"path": "bad/yaml", "reason": "while parsing a block mapping"}`，其他模組不受影響 | 自動 |
| TC-021 | 作法 3「非 dict 非字串」 | 例外 | meta 是 `None`、是 `3`、是 `["x"]` | `build_snapshot` | 每個都記一筆 reason `"meta.yml is not a mapping"` | 自動 |
| TC-022 | 裁決 2「任何例外都轉成 errors」 | 例外 | 三個模組，其中一個讓 `flatten` 丟 `RuntimeError("boom")`（測試以替身 `flatten` 製造） | `build_snapshot` | 不中斷：另兩個照常進 modules；errors 有 `{"path": <該模組>, "reason": "boom"}` | 自動 |
| TC-023 | 作法 4；`test_dumps_is_stable_and_ends_with_one_newline` | 功能 | golden 結果 | 對同輸入呼叫兩次 `dumps` | 兩次逐字相同；結尾恰一個 `\n`（不是零個或兩個）；不含 `generated_at` | 自動 |
| TC-024 | 作法 4 | 功能 | 一個 description 含中文與 `é` 的模組 | `dumps` | 字元原樣出現、沒有 `\uXXXX` 跳脫；縮排是 1 個空格（第二行以一個空格加 `"source"` 開頭）；鍵順序不被排序；`json.loads` 還原後等於原 dict | 自動 |

## User Story 2 — 載入、搜尋、描述（優先度 P1）

這是拖拉畫布的積木清單；017b／017c／017e 從這裡讀。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 6「給 path 時不快取」 | 功能 | 暫存目錄裡寫一份快照 JSON | `load(path)`；改寫檔案內容；再 `load(path)` | 第一次得到檔案內容；第二次得到新內容（沒被快取住） | 自動 |
| TC-031 | 作法 6「以 lru_cache 快取」 | 功能 | 預設路徑 | 連呼叫兩次 `load()` | 兩次回傳同一個物件（`is`），且是 dict | 自動 |
| TC-032 | 作法 6；`test_missing_catalogue_file_does_not_raise` | 例外 | `tmp_path / "none.json"` 不存在 | `load(tmp_path / "none.json")` | 不丟例外；`count == 0`、`sha is None`、`modules == []`、`source == "nf-core/modules"`、`errors` 恰一筆 | 自動 |
| TC-033 | 作法 6 訊息 | 例外 | 同 TC-032 | 看那筆 error | `path == ""`；`reason` 含「模組目錄檔不存在：」、該檔路徑、與「(the module catalogue file is missing)」 | 自動 |
| TC-034 | 作法 7；`test_search_ranks_exact_name_first` | 功能 | golden 當 data | `search("FastQC", data)` | 第一筆 `name == "fastqc"` | 自動 |
| TC-035 | 作法 7 keyword 命中 | 功能 | golden 當 data | `search("bam", data)` | 第一筆是 `samtools_sort` | 自動 |
| TC-036 | 作法 7 分數順序 | 功能 | 假資料五個模組，各自只在一種層級命中同一個 `q`：name 完全相等、name 開頭、name 包含、keyword 包含、description 包含；另有兩個同分模組 | `search(q, data)` | 順序依序是 完全相等 → 開頭 → name 包含 → keyword → description；同分的依 name 排序 | 自動 |
| TC-037 | 裁決 3；作法 7「去頭尾空白、轉小寫」 | 功能 | keyword 是 `"Quality Control"`、description 含 `Sort SAM`（大小寫混合） | `search("  QUALITY  ", data)`、`search("sort sam", data)` | 兩個查詢都找得到對應模組（大小寫不影響，頭尾空白被去掉） | 自動 |
| TC-038 | 作法 7「空字串 → []」；`test_search_empty_query_is_empty_and_caps_at_50`（前半） | 例外 | 任一 data | `search("   ", data)`、`search("", data)` | 都回 `[]` | 自動 |
| TC-039 | 作法 7「都不中就不列」 | 例外 | golden 當 data | `search("zzzznotamodule", data)` | 回 `[]` | 自動 |
| TC-040 | 作法 7「取前 50」；同測試後半 | 功能 | 造 60 個名字都含 `x` 的假模組（例 `x00`…`x59`） | `search("x", data)` | 恰 50 筆，且是依 (分數, name) 排序後最前面的 50 個 | 自動 |
| TC-041 | 作法 7「每筆回 name, path, description」 | 功能 | golden 當 data | `search("fastqc", data)` | 每筆的鍵恰為 `{"name","path","description"}`，內容與該模組相同 | 自動 |
| TC-042 | 作法 8；`test_describe_found_carries_sha_and_channels` | 功能 | golden 當 data（sha `abc123`） | `describe("FASTQC", data)` | `found` 為 True、`sha == "abc123"`、`inputs[1]["name"] == "reads"`，並帶該模組全部欄位（name、path、description、keywords、tools、inputs、outputs） | 自動 |
| TC-043 | 作法 8；`test_describe_unknown_is_a_clean_not_found` | 例外 | golden 當 data | `describe("nope", data)` | 回傳的鍵恰為 `{"found","name","message"}`，`found` 為 False，`name == "nope"` | 自動 |
| TC-044 | 作法 8 訊息 | 例外 | 同上 | 看 `message` | 等於 `找不到模組 nope；用 search 找相近的名字 (no module named nope; use search to find a similar name)`（含「search」） | 自動 |
| TC-045 | 作法 8「空字串也是找不到」 | 例外 | golden 當 data | `describe("", data)` | `found` 為 False，鍵同 TC-043，不丟例外 | 自動 |

## User Story 3 — 提交的快照、發行與重產（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 作法 1；`test_committed_snapshot_is_the_pinned_upstream` | 功能 | repo 裡提交的 `platform/abf_platform/data/nf-core-modules.json` | `load()` | `sha == "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"` | 自動 |
| TC-051 | 同上；維護者原話「全部約 1,500 個」 | 功能 | 同上 | `load()` | `count >= 1000` | 自動 |
| TC-052 | 作法 3 | 功能 | 同上 | `load()` | `count == len(modules)`（errors 不計入） | 自動 |
| TC-053 | 完成標準「describe("fastqc") 有輸入輸出」 | 功能 | 同上 | `describe("fastqc")`（用預設 data） | `found` 為 True，`inputs` 裡有名為 `reads` 的項 | 自動 |
| TC-054 | 同上 | 功能 | 同上 | `describe("fastqc")` | `outputs` 不是空的 | 自動 |
| TC-055 | 作法 2「versions 略過」 | 功能 | 提交的快照 | 掃全部模組的 outputs | 沒有任何 output 的 channel 名以 `versions` 開頭 | 自動 |
| TC-056 | 作法 10 | 功能 | 提交的快照檔 | 量檔案大小 | ≤ 8 MB | 自動 |
| TC-057 | 作法 3、4、5「同一 sha 重產逐位元相同」 | 功能 | 提交的快照檔 | 讀檔文字，與 `dumps(load())` 比較 | 兩者逐字相同；結尾恰一個 `\n`；不含 `generated_at` | 自動 |
| TC-058 | 作法 3 排序、作法 2 鍵順序 | 功能 | 提交的快照 | 檢查全部模組 | modules 已依 (name, path) 排序、errors 已依 path 排序；每個模組鍵順序為 `name, path, description, keywords, tools, inputs, outputs` | 自動 |
| TC-059 | 作法 5；`test_catalogue_runs_without_pyyaml` | 功能 | 乾淨的 `sys.modules`（沒有 yaml） | 以 `importlib` 載入 `abf_platform.catalogue`，再用它的 `load`、`search`、`describe` | 載入後 `sys.modules` 裡仍沒有 `yaml`（模組層級不 import yaml，平台執行與測試不需要 PyYAML） | 自動 |
| TC-060 | 作法 6 發行；`test_package_data_ships_the_snapshot`（前半） | 功能 | `platform/pyproject.toml` | 讀 package-data | 含 `"data/*.json"` | 自動 |
| TC-061 | 同測試後半；「data/ 底下不放 `__init__.py`」 | 功能 | `platform/abf_platform/data/` | 列出目錄 | 沒有 `__init__.py`，且有 `nf-core-modules.json` | 自動 |
| TC-062 | 「允許更新的既有斷言」 | 功能 | `platform/tests/test_guidance.py::test_tc406_package_data_covers_the_skills` | 讀該測試 | 它精確比對一行 `package-data = {"abf_platform" = ["skills/*/SKILL.md", "data/*.json"]}`，仍然要求 skills（沒有放寬）；且 pyproject 真的就是這一行 | 自動：`platform/tests/test_guidance.py`；驗收另對照 `git diff` 確認只動這一個斷言 |
| TC-063 | 作法 5「沒裝 PyYAML 就印訊息並以 2 結束」 | 例外 | 以子行程執行 `python -m abf_platform.catalogue snapshot --modules <暫存空目錄> --sha x --out <暫存檔>`，並讓 `import yaml` 失敗（例：先把 `sys.modules["yaml"]` 設成 None） | 看輸出與結束碼 | 結束碼是 2；輸出含 `需要 PyYAML：python3 -m pip install pyyaml (PyYAML is needed to read meta.yml)`；不顯示堆疊 | 自動 |
| TC-064 | 範圍「docs/PLATFORM.md」 | 功能 | `docs/PLATFORM.md` | 找標題 | 有 `## nf-core module catalogue`，且位置在 `## What the platform stores` 之前 | 自動 |
| TC-065 | 同上「上游 sha」 | 功能 | 該節文字 | 檢查 | 含完整 sha `5ed90b42e78410e7411e9c6bdfeff33226d6c58e` 與檔案位置 `nf-core-modules.json` | 自動 |
| TC-066 | 同上「怎麼重產」 | 功能 | 該節文字 | 檢查 | 含重產指令 `python -m abf_platform.catalogue snapshot` | 自動 |
| TC-067 | 同上「重產是一個 A 級 PR」 | 功能 | 該節文字 | 檢查 | 同時提到 PR 與 A 級（`tier A`、`A-tier`、`A 級` 或 `A級` 擇一） | 自動 |

## User Story 4 — 這次不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 不做：不加 MCP 工具 | 不在範圍 | `platform/abf_platform/mcp_server.py` 與工具清單 | 檢查 | 不含 `catalogue` 字樣；工具數相關既有測試（`test_pat.py:383/751`、`test_oauth_mcp.py:44`、`test_estimate_su.py` TC-029）原樣綠 | 自動：既有測試 + `test_catalogue.py` 內的靜態檢查 |
| TC-071 | 不做：不加網頁路由、不改 `actions/`（專長守則：動作層對等） | 不在範圍 | `web.py`、`web_board.py`、`actions/*.py` | 檢查 | 都不 import 也不提 `catalogue`；`test_web_parity.py` 原樣綠（動作名單兩邊沒新增） | 自動 |
| TC-072 | 不做：不讀 `subworkflows/`；不在平台主機跑 `nf-core modules install` | 不在範圍 | `catalogue.py` 原始碼 | 檢查 | 不含 `subworkflows`、不 import `subprocess`、不呼叫 `os.system`；重產只走 `modules/nf-core/**/meta.yml` | 自動 |
| TC-073 | 不做：擁有者過濾（目錄是公開資料） | 不在範圍 | `catalogue.py` | 檢查函式簽名 | `load` 參數只有 `path`、`search` 只有 `q, data`、`describe` 只有 `name, data`；沒有 user／owner／token 參數 | 自動 |
| TC-074 | 作法 9「不需要 migration」 | 不在範圍 | `catalogue.py` 與 repo | 檢查 | `catalogue.py` 不 import `sqlite3` 或 `abf_platform.store`；沒有新增 migration 檔 | 自動 |
| TC-075 | 作法 5「不改 dependencies、不改 constraints.txt」 | 不在範圍 | `platform/pyproject.toml`、`platform/constraints.txt` | 檢查 | 兩個檔都不出現 `yaml`（不分大小寫） | 自動 |

## 憲法與安全網

本任務新增一份 JSON 與兩個 Python 檔，會碰到下列既有的檢查；每一條都要在加入快照之後仍然綠。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 原則 I 第 1 條（每個來源檔說明它不是什麼／為何自己寫）；裁決 1 | 功能 | `catalogue.py`、`test_catalogue.py` | 跑 `test_scope.py::test_tc070_every_python_source_names_its_alternative` | 兩個檔前 40 行內各有一行 `# Nothing existing: …`（理由 ≥ 15 字），測試綠 | 自動：`platform/tests/test_scope.py` |
| TC-C02 | 原則 II 第 3 條（沒有個人或叢集路徑）；裁決 4 | 功能 | 已提交的快照與 `docs/PLATFORM.md` | 跑 `test_scope.py::test_tc072_no_personal_or_cluster_paths` | 綠；整份 JSON 沒有 `(/home\|/work\|/scratch\|/staging\|/lustre)/名字/` 這種形狀 | 自動 |
| TC-C03 | 安全網：金鑰形狀不得提交 | 功能 | 已提交的快照 | 跑 `test_launch_static.py::test_tc074_no_token_or_account_is_committed` | 綠 | 自動 |
| TC-C04 | 原則 I（不得出現 Seqera 服務位址或 `tw` 呼叫）；`test_scope.py` TC-051 掃整個 `platform/` 含 JSON | 功能 | 已提交的快照 | 跑 `test_scope.py::test_tc051_no_seqera_service_address_and_no_tw_call` | 綠；若快照內容撞上，須回報而不是改測試 | 自動 |
| TC-C05 | 原則 III 第 6 條（不為特定 pipeline 放設定） | 功能 | 快照放在 `platform/abf_platform/data/`，不在 `configs/` | 跑 `bash tests/no_per_pipeline_config.sh` | 綠 | 自動：`tests/no_per_pipeline_config.sh` |
| TC-C06 | 開發流程：不得放寬既有斷言 | 功能 | 本次差異 | 檢查 `test_tc407_packages_is_not_extended`、`test_tcd01`、`test_tc404`、`test_web_parity.py`、工具數測試 | 這些測試原樣通過；除 `test_tc406_package_data_covers_the_skills` 一處外，沒有任何既有測試檔的斷言被改、被跳過 | 自動：既有測試；驗收另比對 `git diff` |
| TC-C07 | 完成標準「全套綠」 | 功能 | HEAD | 在 WSL 跑 `tests/run_all.sh` | 全綠，完成記號 `GREEN <HEAD sha>` 與 HEAD 相符 | 自動：`tests/run_all.sh` |
| TC-C08 | 專長守則（backend）：錯誤訊息說明原因、不露堆疊 | 例外 | TC-032／TC-043 的錯誤結果 | 檢查 `errors` 與 `message` 文字 | 不含 `Traceback`、不含 `File "…py"` 這類堆疊；說明發生了什麼事 | 自動 |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
