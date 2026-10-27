# 站台代理讀 nf-core 官網管線清單（搜尋全部 nf-core 管線用） progress ledger

## 進度

- [x] 失敗先行：`platform/tests/test_nfcore_catalogue.py` + `fixtures/catalogue/pipelines-small.json`，實作前跑：`62 failed, 20 passed`（commit d894346 `RED:`）。紅的原因：`PARTS`/`PF_PARTS` 沒有 `catalogue`、`HOSTS` 沒有 `nf-co.re`、`actions.nfcore_catalogue` 不存在、`jobs.CATALOGUE_CACHE_SECONDS` 等常數不存在、PLATFORM.md／TESTING.md 沒有新文字。
- [x] 站台 `abf_station/pipeline_files.py`：`catalogue` part、第四主機、`CATALOGUE_URL`、`_catalogue`／`_catalogue_entries`、`_problem` 先驗 parts；`handlers.py` 說明句。
- [x] 平台 `jobs.py`：`PF_PARTS`、新常數、`pf_arguments`、`_clean_catalogue`；`store.py` 未動（沒有 migration）。
- [x] 動作層 `actions/__init__.py`：`# ---- nfcore-catalogue: begin/end` 區塊，公開名稱只有 `nfcore_catalogue`。
- [x] 文件：`docs/PLATFORM.md` 三處、`docs/TESTING.md` 新一節（手動步驟，executor 未執行）。
- [ ] 手動（合併後）：TC-103～TC-106 的輸出待貼。

## 既有測試斷言更新（舊→新＋理由）

1. `test_station_pipeline_files.py` 檔首 docstring：「four kinds of public GitHub file」→「five kinds of public file (the fifth is nf-core's own pipeline list, test_nfcore_catalogue.py)」；文字對上程式。
2. 同檔 TC-004：`the_three_hosts_are_allowed` → `the_four_hosts_are_allowed`，迴圈加 `https://nf-co.re/pipelines.json`；第四主機放行。
3. 同檔 `BAD_URLS`：刪 `https://nf-co.re/pipelines.json`；加 `http://nf-co.re/pipelines.json`、`https://nf-co.re.evil.com/pipelines.json`、`https://www.nf-co.re/pipelines.json`；原網址現為合法，新增三個釘住「只有逐字 nf-co.re」。
4. 同檔 TC-047：`job(["catalogue"])` 一行加註解「catalogue takes no repo／revision (CS-08)」，並加 `refused(ctx, net, job(["schema", "catalogue"], repo=None, revision=None))`；意思從「沒有 catalogue」變成「catalogue 不跟管線一起問」。
5. `test_pipeline_files_queue.py` `BAD_ARGS`（TC-066）：只加不刪四筆 `(None, None, ["schema"])`、`("nf-core/ampliseq", None, ["catalogue"])`、`(None, "2.18.0", ["catalogue"])`、`(None, None, ["catalogue", "schema"])`；新規則反例在 enqueue 端也釘住。
6. `test_pipeline_files_action.py` TC-159：`nothing_for_the_whole_nf_core_catalogue` → `the_catalogue_is_its_own_action`；`assert not hasattr(...)` 翻成 `callable(actions.nfcore_catalogue)`；`pipeline_files` 簽章仍無 `catalogue`；加 `pf(world, parts=["catalogue"])["error"] == "bad_input"`（加 `world` fixture）；維護者 10-26 放行，清單走獨立動作。
7. 同檔 TC-135：`no_mcp_tool_for_the_two_actions` → `..._three_actions`，集合加 `"nfcore_catalogue"`；第三個無 MCP 工具的動作。
8. `test_web_parity.py` `WEB_ONLY`：加 `"nfcore_catalogue"` 一列；動作層多一個公開名稱。
9. `test_catalogue.py::test_no_tool_route_or_action_mentions_the_catalogue`（TC-070/071，裁決 6）：舊＝所有檔含 `actions/__init__.py` 都不得含 `catalogue`；新＝只對 `actions/__init__.py` 先刪 `# ---- nfcore-catalogue: begin`…`end` 區塊與識別字 `nfcore_catalogue` 再檢查，其他檔不變。理由：兩個 catalogue 是不同東西（官網管線清單 vs 模組目錄），舊測試本意不變。
