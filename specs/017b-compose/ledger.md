# 畫布 017b：組合流程的資料模型、依使用者儲存、轉成 Nextflow main.nf（純後端） progress ledger

- [x] `platform/abf_platform/compose.py`：`normalize`（圖形狀驗證、標準形式）、`render`（main.nf、modules.json、nextflow.config、open_inputs）。純函式，只用標準庫與 `catalogue`。
- [x] `platform/abf_platform/actions/pipelines.py`：`create_pipeline`、`update_pipeline`、`list_pipelines`、`get_pipeline`、`render_pipeline`；兩張表第一次使用時建立，觸發器擋 UPDATE／DELETE；不在 `actions/__init__.py` 匯入。
- [x] `platform/tests/test_compose.py`、`platform/tests/test_pipelines_store.py`、`platform/tests/fixtures/compose/` 三組夾具。
- [x] `docs/PLATFORM.md`：新增 `## Composed pipelines` 與 stores 表一列；`tests/platform_storage_doc_test.sh` 綠。
- [x] 沒有動 `store.py`、`actions/__init__.py`、`mcp_server.py`、`web.py`、`catalogue.py`、`pyproject.toml`、`constraints.txt`；不需要 migration。

## 手算標準答案的紀錄

`fan_in_and_twins/` 與 `old_format_module/` 的 `main.nf`、`modules.json`、`nextflow.config` 是先依 plan 作法 A、B 的規則手寫（process 名由 path 推、別名 `<PROCESS>_<ID轉大寫>`、include 依呼叫名排序、開放輸入依 (id, 通道號)、`.mix(` 串接、config 的 `withName` 依 id、鍵依字典序、`\`、`'`、`$` 跳脫），再寫程式去比；第一次跑就逐字相同，沒有拿程式輸出回頭改答案。這兩組的標準答案請 developer-agent 在審查時再看一次。

## 實作時選的讀法（plan 沒寫死之處）

- 拓撲順序：用「每次從可取的節點中挑 id 字典序最小者」（堆積），不是一層一層；兩組夾具與 TC-055、TC-056 兩種讀法答案一致。
- 三個以上來源：`A.out.x.mix(B.out.y).mix(C.out.z)`（連續 `.mix(`）。
- 節點上多餘的鍵（`id`、`module`、`sha`、`params` 以外）：拒絕並點名，而不是默默丟掉。
- `render` 另外檢查名稱（`^[a-z][a-z0-9-]{0,39}$`）與版本（1 以上整數），不合丟 `ValueError`，因為它們會進註解與 config。
- `get_pipeline` 回的 `created_at` 是組合建立時間；`list_pipelines` 的 `updated_at` 是最新版時間。

## 未驗證

- 真實 nf-core 模組檔下的 `-stub-run`：**未驗證**。`./modules/nf-core/<path>/main` 這個 include 路徑是依資料夾位置推出來的，017d 實跑時要確認。

## 給 017c 的備忘

- `-stub-run` 閘門必須同時看 `render` 回的 `open_inputs`，不能只看結束碼：沒接的輸入被渲染成 `Channel.empty()`，這樣的專案空轉也會「成功」。
- 型別相容檢查（邊兩端的 `type`／`pattern`）本版沒做，TC-118 明定 fastqc 的 html 接 samtools_sort 的 `index_format` 是被接受的。
- 兩張表不在 `STATE_SCHEMA`，`connect_state()` 之後不一定存在；讀取要走 `actions/pipelines.py`（它自己先建表），不要直接 `SELECT`。
