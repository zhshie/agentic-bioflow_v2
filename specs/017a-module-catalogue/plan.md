---
id: 017a-module-catalogue
title: nf-core 模組目錄快照與查詢函式（畫布的積木清單，先不對外開工具）
tier: A
kinds: backend
lane: L5
base: v3
---

# 017a-module-catalogue

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/017a-module-catalogue/plan.md`。**只處理本任務**。
> 2026-10-23（筆電）**整份重寫**：前兩版被 verifier 退回（10-22 兩次，理由見檔尾「上一版退回理由」）。這版的關鍵改變＝**不新增 MCP 工具、不動動作層**——對外的工具與網頁路由留到 017e 一次開（MCP 工具與 `/modules` 頁面同時上，parity 表不必先變長）。退回理由裡的工具數、READ_TOOLS、OWED、ledger 釘子因此全部不再牽動。

## 目標
把全部 nf-core 模組（約 1,500 個）的 `meta.yml` 做成一份提交在 repo 的 JSON 快照，加上載入、搜尋、描述三個函式。這是拖拉畫布的積木清單；017b（組裝）、017c（驗證）、017e（畫面與工具）都從這裡讀。

## 維護者原話（verifier 出題用）
- 「積木＝nf-core 模組，全部約 1,500 個；pipeline 與 module 都要相容所有 nf-core 既有的。」（10-21 裁示 5）→ 快照要涵蓋 `modules/nf-core/**/meta.yml` 全部，新舊兩種 meta.yml 格式都要讀得懂。
- 「不自建工具庫」（10-21 不做清單）→ 只讀 nf-core/modules，不自己維護或改寫模組內容。

## 範圍：檔案（最終版，只准改這些）
- `platform/abf_platform/catalogue.py`（新：攤平、建快照、載入、搜尋、描述；檔尾 `if __name__ == "__main__"` 是重產快照的指令）
- `platform/abf_platform/data/nf-core-modules.json`（新，提交產物；`data/` 底下**不放 `__init__.py`**）
- `platform/pyproject.toml`（只改 `package-data` 一行）
- `platform/tests/test_catalogue.py`（新）
- `platform/tests/test_guidance.py`（只改 `test_tc406_package_data_covers_the_skills` 的正規式，見「允許更新的既有斷言」）
- `docs/PLATFORM.md`（在 `## What the platform stores` 之前加一節 `## nf-core module catalogue`：檔案位置、上游 sha、怎麼重產、重產是一個 A 級 PR）
- `specs/017a-module-catalogue/ledger.md`（新，executor 的進度帳本）

## 作法
1. **上游固定版本**：`nf-core/modules` @ `5ed90b42e78410e7411e9c6bdfeff33226d6c58e`（2026-10-23 07:44 UTC 的 master）。
2. **`flatten(path, meta) -> dict`**（`path`＝`modules/nf-core/` 之後、`meta.yml` 之前的相對路徑，用 `/`，例 `samtools/sort`）：
   - `name`：`meta["name"]`（必須是非空字串，否則丟 `ValueError("meta.yml has no name")`）。
   - `description`：字串的空白壓成單一空格（`" ".join(s.split())`）；缺 → `""`。
   - `keywords`：只留字串元素；缺 → `[]`。
   - `tools`：`meta["tools"]` 是「單鍵 dict」的清單 → `[{"name": 鍵, "homepage": 值.get("homepage") 或 None, "licence": 清單}]`；`licence` 是字串 → `[字串]`，缺 → `[]`。
   - `inputs`：`meta["input"]` 是清單，第 i 個元素（i 從 0）：是清單（新格式，一個 channel 的 tuple）→ 裡面每個單鍵 dict 各出一筆 `{"channel": i, "name": 鍵, "type": 值.get("type"), "pattern": 值.get("pattern")}`；是單鍵 dict（舊格式）→ 出一筆，`channel` 也是 i。缺 → `[]`。
   - `outputs`：`meta["output"]` 是 dict（新格式）→ 依原順序，每個 channel 名 c 底下的每個 tuple 清單裡每個單鍵 dict 出一筆 `{"channel": c, "name": 鍵, "type": …, "pattern": …}`；是清單（舊格式）→ 每個單鍵 dict 出一筆，`channel` = 該鍵。**channel 名以 `versions` 開頭的整個略過**（兩種格式都略）。`topics` 不讀。
   - 缺的 `type`／`pattern` 寫 `null`。
   - 回傳鍵順序固定：`name, path, description, keywords, tools, inputs, outputs`。
3. **`build_snapshot(items, sha) -> dict`**：`items` 是 `(path, meta)` 的序列；`meta` 若不是 dict（讀檔失敗時呼叫端放字串錯誤訊息）或 `flatten` 丟 ValueError → 記進 `errors`：`{"path": path, "reason": <字串>}`（非 dict 非字串 → `"meta.yml is not a mapping"`）。回傳：
   `{"source": "nf-core/modules", "sha": sha, "count": len(modules), "modules": [...依 name 再 path 排序...], "errors": [...依 path 排序...]}`。**沒有 `generated_at`**（讓同一 sha 重產的檔案逐位元相同）。
4. **`dumps(snapshot) -> str`**：`json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n"`，不排序鍵（保持作法 2、3 的順序）。
5. **重產指令**（只給維護者／developer-agent 用，不在測試裡跑）：`python -m abf_platform.catalogue snapshot --modules <nf-core/modules 的 checkout> --sha <sha> --out <路徑>`。它走 `<checkout>/modules/nf-core/**/meta.yml`，用 `yaml.safe_load` 讀（**PyYAML 在函式內才 import**；沒裝就印 `需要 PyYAML：python3 -m pip install pyyaml (PyYAML is needed to read meta.yml)` 並以 2 結束），YAML 解析錯誤時把錯誤第一行當 `meta` 字串交給 `build_snapshot`。`catalogue.py` 其他部分只用標準庫，**平台執行與測試都不需要 PyYAML**（不改 `dependencies`、不改 `constraints.txt`）。
6. **`load(path=None) -> dict`**：預設讀 `Path(__file__).parent / "data" / "nf-core-modules.json"`，結果以 `functools.lru_cache` 快取（給 path 時不快取）；檔案不存在 → 回 `{"source": "nf-core/modules", "sha": None, "count": 0, "modules": [], "errors": [{"path": "", "reason": "模組目錄檔不存在：<路徑> (the module catalogue file is missing)"}]}`，不丟例外。
7. **`search(q, data=None) -> list`**：`data` 預設 `load()`。`q` 去頭尾空白、轉小寫；空字串 → `[]`。對每個模組算分：name 完全相等 0、name 開頭符合 1、name 包含 2、任一 keyword 包含 3、description 包含 4；都不中就不列。依 `(分數, name)` 排序取前 50；每筆回 `{"name", "path", "description"}`。
8. **`describe(name, data=None) -> dict`**：name 比對不分大小寫、完全相等。找到 → `{"found": True, "sha": data["sha"], **該模組全欄}`；找不到 → `{"found": False, "name": name, "message": "找不到模組 %s；用 search 找相近的名字 (no module named %s; use search to find a similar name)" % (name, name)}`。空字串也是找不到。
9. **不需要 migration**：不碰任何資料表；快照是隨套件發行的唯讀檔。
10. **快照檔大小**：約 1,500 筆，預期 1～3 MB；超過 8 MB 寫進 ledger 並在 PR 說明提出（不要自行刪欄位）。

## 夾具與標準答案（developer-agent 準備；executor 原樣放進 `test_catalogue.py`）
三個 `(path, meta)`（就是 meta.yml 被 `yaml.safe_load` 讀出來的 dict）：
```python
FASTQC = ("fastqc", {
    "name": "fastqc", "description": "Run FastQC on sequenced reads\n",
    "keywords": ["quality control", "qc"],
    "tools": [{"fastqc": {"description": "FastQC gives general quality metrics.", "homepage": "https://www.bioinformatics.babraham.ac.uk/projects/fastqc/", "licence": ["GPL-2.0-only"]}}],
    "input": [[{"meta": {"type": "map", "description": "Groovy Map"}}, {"reads": {"type": "file", "description": "FastQ files"}}]],
    "output": {"html": [[{"meta": {"type": "map"}}, {"*.html": {"type": "file", "pattern": "*_{fastqc.html}"}}]],
               "zip": [[{"meta": {"type": "map"}}, {"*.zip": {"type": "file", "pattern": "*_{fastqc.zip}"}}]],
               "versions_fastqc": [[{"${task.process}": {"type": "string"}}]]},
    "topics": {"versions": [[{"${task.process}": {"type": "string"}}]]}})
SAMTOOLS_SORT = ("samtools/sort", {
    "name": "samtools_sort", "description": "Sort SAM/BAM/CRAM file",
    "keywords": ["sort", "bam"],
    "tools": [{"samtools": {"homepage": "http://www.htslib.org/", "licence": "MIT"}}],
    "input": [{"meta": {"type": "map"}}, {"bam": {"type": "file", "pattern": "*.{bam,cram,sam}"}}],
    "output": [{"meta": {"type": "map"}}, {"bam": {"type": "file", "pattern": "*.{bam}"}}, {"versions": {"type": "file", "pattern": "versions.yml"}}]})
BROKEN = ("broken/one", {"description": "no name here"})
```
`build_snapshot([SAMTOOLS_SORT, BROKEN, FASTQC, ("bad/yaml", "while parsing a block mapping")], "abc123")` 必須等於：
```python
{"source": "nf-core/modules", "sha": "abc123", "count": 2,
 "modules": [
  {"name": "fastqc", "path": "fastqc", "description": "Run FastQC on sequenced reads", "keywords": ["quality control", "qc"],
   "tools": [{"name": "fastqc", "homepage": "https://www.bioinformatics.babraham.ac.uk/projects/fastqc/", "licence": ["GPL-2.0-only"]}],
   "inputs": [{"channel": 0, "name": "meta", "type": "map", "pattern": None}, {"channel": 0, "name": "reads", "type": "file", "pattern": None}],
   "outputs": [{"channel": "html", "name": "meta", "type": "map", "pattern": None}, {"channel": "html", "name": "*.html", "type": "file", "pattern": "*_{fastqc.html}"},
               {"channel": "zip", "name": "meta", "type": "map", "pattern": None}, {"channel": "zip", "name": "*.zip", "type": "file", "pattern": "*_{fastqc.zip}"}]},
  {"name": "samtools_sort", "path": "samtools/sort", "description": "Sort SAM/BAM/CRAM file", "keywords": ["sort", "bam"],
   "tools": [{"name": "samtools", "homepage": "http://www.htslib.org/", "licence": ["MIT"]}],
   "inputs": [{"channel": 0, "name": "meta", "type": "map", "pattern": None}, {"channel": 1, "name": "bam", "type": "file", "pattern": "*.{bam,cram,sam}"}],
   "outputs": [{"channel": "meta", "name": "meta", "type": "map", "pattern": None}, {"channel": "bam", "name": "bam", "type": "file", "pattern": "*.{bam}"}]}],
 "errors": [{"path": "bad/yaml", "reason": "while parsing a block mapping"}, {"path": "broken/one", "reason": "meta.yml has no name"}]}
```

## 失敗先行測試（`platform/tests/test_catalogue.py`，現在都會紅）
- `test_snapshot_of_three_fixtures_equals_the_golden`（上面那組，含 `count`、排序、errors）。
- `test_dumps_is_stable_and_ends_with_one_newline`（同輸入兩次 `dumps` 逐字相同；結尾恰一個 `\n`；不含 `generated_at`）。
- `test_versions_channels_are_skipped_in_both_formats`。
- `test_search_ranks_exact_name_first`：用 golden 當 data，`search("FastQC")[0]["name"] == "fastqc"`；`search("bam")` 的第一筆是 `samtools_sort`（keyword 命中）。
- `test_search_empty_query_is_empty_and_caps_at_50`：`search("   ") == []`；造 60 個名字含 `x` 的假模組 → 回 50 筆。
- `test_describe_found_carries_sha_and_channels`：`describe("FASTQC", data)` → `found` True、`sha == "abc123"`、`inputs[1]["name"] == "reads"`。
- `test_describe_unknown_is_a_clean_not_found`：`describe("nope", data)` 的鍵恰為 `{"found", "name", "message"}`，message 含「search」。
- `test_missing_catalogue_file_does_not_raise`：`load(tmp_path / "none.json")` → `count == 0` 且 `errors` 一筆。
- `test_committed_snapshot_is_the_pinned_upstream`：`load()` 的 `sha == "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"`、`count >= 1000`、`describe("fastqc")["found"]` 為 True 且 `inputs` 有 `reads`、檔案大小 ≤ 8 MB。
- `test_catalogue_runs_without_pyyaml`：以 `importlib` 載入 `abf_platform.catalogue` 時 `sys.modules` 裡沒有 `yaml`（模組層級不 import yaml）。
- `test_package_data_ships_the_snapshot`：`pyproject.toml` 的 package-data 含 `"data/*.json"`，且 `platform/abf_platform/data/` 沒有 `__init__.py`。

## 允許更新的既有斷言（其他一律不准動）
- `platform/tests/test_guidance.py:343` `test_tc406_package_data_covers_the_skills`：正規式改成精確比對新的一行 `package-data = {"abf_platform" = ["skills/*/SKILL.md", "data/*.json"]}`（仍然要求 skills，沒有放寬）。
- 確認不會變紅、不准改：`test_guidance.py::test_tc407_packages_is_not_extended` 與 `test_actions_layer.py::test_tcd01`（`data/` 不是 package，不加 `__init__.py`、`packages` 清單不動）、`test_guidance.py::test_tc404`（wheel 只比 skills）、`test_web_parity.py`（actions 沒有新名字）、工具數相關（`test_pat.py:383/751`、`test_oauth_mcp.py:44`、`test_estimate_su.py` TC-029）、`tests/no_per_pipeline_config.sh`（快照不在 `configs/`）。

## 完成標準（done when）
- `platform/abf_platform/data/nf-core-modules.json` 由作法 5 從固定 sha 產生並提交；`describe("fastqc")` 有輸入輸出。
- 上面 11 個測試綠；全套綠。

## 環境事實
- 重產快照時的 PyYAML：在 WSL 開暫存 venv，不改系統：`python3 -m venv /tmp/abf-snap && /tmp/abf-snap/bin/pip install pyyaml`，再用 `/tmp/abf-snap/bin/python -m abf_platform.catalogue snapshot …`（`PYTHONPATH=platform`）。
- 取上游：`git clone --filter=blob:none --no-checkout https://github.com/nf-core/modules /tmp/nfm && git -C /tmp/nfm checkout 5ed90b42e78410e7411e9c6bdfeff33226d6c58e -- modules/nf-core`。
- 新格式 meta.yml 的實例：`modules/nf-core/fastqc/meta.yml`（`input` 是清單的清單、`output` 是 dict、另有 `topics`）；舊格式 `output` 是清單。兩種在上游都還存在。

## 不做
- 不加 MCP 工具、不加網頁路由、不改 `actions/`（017e 一次開，屆時同時補 parity 表與工具數斷言）。
- 不做組裝（017b）、驗證（017c）、送出（017d）、畫面（017e）。
- 不在平台主機跑 `nf-core modules install`；不讀 `subworkflows/`。
- 不做擁有者過濾（目錄是公開資料）。

## 上一版退回理由（2026-10-22，供 verifier 對照；本版處理方式寫在括號）
- 快照放 `configs/` 撞 `no_per_pipeline_config.sh`（改放 `platform/abf_platform/data/`）。
- 漏點名工具數、READ_TOOLS、READ_ONLY、PLATFORM.md 工具數、`platform_storage_doc_test.sh:140-142`（本版不加工具，全部不牽動）。
- `test_tcs07` 要求 OWED 名字出現在 ledger（本版不動 OWED）。
- 回傳欄位、sha 位置、攤平規則、fixture 與 golden 未寫死（作法 2～8 與「夾具與標準答案」寫死）。
- 錯誤訊息要含處理建議、空字串回空清單（作法 6～8）。

## 裁決（2026-10-23，預檢後；與上文衝突時以本段為準）
1. **檔首標頭**（`platform/tests/test_scope.py:75-80` TC-070）：`catalogue.py` 與 `test_catalogue.py` 前 40 行內要有一行 `# Nothing existing: …`（理由 ≥15 字），例：`# Nothing existing: the snapshot is nf-core's own module metadata, flattened; the repository has no module catalogue.`
2. **任何壞資料都不中斷重產**：`tools` 缺或為 null → `[]`；`input`／`output` 缺或為 null → `[]`；清單裡既不是清單也不是單鍵 dict 的元素、或單鍵 dict 的值不是 dict（例如 null）→ 該元素略過、繼續（不記 errors）。`flatten` 對單一模組丟出的**任何例外**（不只 ValueError）都由 `build_snapshot` 轉成 `{"path", "reason": str(e)}` 記進 errors。新增測試 `test_odd_shapes_are_skipped_not_fatal`（`tools: None`、`input: [None, 3, {"a": None}]` → 模組照樣產生、inputs 為 `[]`）。
3. **比對一律不分大小寫**：作法 7 的 name／keywords／description 都先轉小寫再比；作法 8 同。
4. **TC-072 路徑規則**（`platform/tests/test_scope.py:134-136` 會掃 `platform/` 底下所有檔，含這份 JSON）：`flatten` 對每個輸出的字串欄位套用與 TC-072 相同的正規式 `(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/`，命中的那段換成 `<path>/`。範圍不變（寫在 `catalogue.py`）。新增測試 `test_cluster_like_paths_are_masked`（description 含 `/home/alice/x` → 輸出含 `<path>/x`、不含 `/home/alice/`）。產生快照後、提交前再對整個 JSON 跑一次 TC-072 與 `test_launch_static.py:104-118`（TC-074 金鑰形狀），兩者都要綠。
5. 失敗先行測試因此是 13 條；完成標準「11 個測試」改讀成 13 個。

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
