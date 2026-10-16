# 測試案例：009b 動作層（platform/abf_platform/actions/），行為不變（refactor）

**規格**：無 `spec.md`（這是 refactor，依維護者指示一律以 `specs/009b-action-layer/plan.md` 為準；plan 的「給維護者」三句是他看得懂的承諾）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人想繞過時，系統怎麼反應（拒絕、停下）。
- **不在範圍**：計畫「Not in this PR」明講這次不做的事；測試確認它真的沒做。

維護者的話（計畫「給維護者」，逐字）：「你用起來完全一樣：MCP 仍然只有六個唯讀工具；送出與取消仍然只能在終端機按 y。」下面 TC-A11、TC-B13、TC-B14、TC-B16、TC-B17 直接用這兩句當輸入與預期結果。

名詞：**動作層**＝`platform/abf_platform/actions/` 裡「一個動作一個函式」的程式；**TERMINAL**＝計畫裡那個只代表「人在終端機按了 y」的專用記號；**JobRefused**＝平台拒絕排入工作時丟出的錯誤；**AST 掃描**＝用程式讀原始碼的結構（不是只搜文字）來檢查誰引用了誰。

「前後一樣」的基準＝計畫起點 `v3`（目前提交 `bc9a93b` 的行為）。

## User Story 1 — 查詢動作集中成一層，MCP 用起來一樣（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-A01 | 計畫·設計 1（讀取動作） | 功能 | 套件建好 | 匯入 `abf_platform.actions` | 有 `list_runs`、`get_run`、`list_compute_envs`、`get_compute_env`、`list_agents`、`list_site_files` 六個函式；其中 `list_site_files` 是非同步（async）函式；第一個位置參數是路徑 | 自動：`platform/tests/test_actions_layer.py`（計畫 5(a)） |
| TC-A02 | 計畫·設計 5(a) | 功能 | `build_server(...)` 建好一台伺服器 | 列出伺服器上所有 MCP 工具名 | 每個工具名在 `actions` 裡都有同名函式；工具名集合正好等於那六個唯讀動作，不多不少 | 自動：`test_actions_layer.py` |
| TC-A03 | 計畫·Contract round 1 第 1 項 | 功能 | 一個索引路徑 | 呼叫 `actions.platform_path_for(index_path)`；再用 `platform_path_for(index_path, 明確路徑)` | 不給第二個參數時結果等於 `store.default_platform_path(index_path)`；給了明確路徑就用明確路徑；`build_server(index_path)` 不帶 `platform_path` 時查到的環境與以前相同 | 自動：`test_actions_layer.py` |
| TC-A04 | 計畫·設計 1；給維護者 第 2 句 | 功能 | 資料庫裡有三個 run（既有測試的 fixture） | 透過 MCP 呼叫 `list_runs`、`get_run`（真實 id） | 回傳內容與重構前逐欄相同：`{"runs": [...]}` 與單一 run 的狀態、時間、task 數、失敗 task | 自動：既有 `platform/tests/test_mcp.py`（含 tc025，不得改動斷言）全綠 |
| TC-A05 | 計畫·設計 1（本體不變） | 功能 | 資料庫裡沒有 id 為 `deadbeefdeadbeef` 的 run | 呼叫 `get_run("deadbeefdeadbeef")` | 回傳 `found: False`、`id` 為該值、`message` 為 `Run not found: deadbeefdeadbeef (找不到這個 run)`，與重構前逐字相同 | 自動：`test_actions_layer.py`（對 `actions.get_run` 與經 MCP 兩條路都驗） |
| TC-A06 | 計畫·設計 1（本體不變） | 功能 | 沒有名為 `nope` 的算力環境 | 呼叫 `get_compute_env("nope")`；另呼叫 `list_compute_envs` | 前者回 `found: False`、`name: nope`、`message` 為 `Compute environment not found: nope (找不到這個算力環境)`；後者回 `{"compute_envs": [...]}`，與重構前相同 | 自動：`test_actions_layer.py` |
| TC-A07 | 計畫·Contract round 1 第 1 項（時鐘在 actions 裡） | 功能 | 一個很久沒聯絡的 agent、一個剛聯絡的 agent | 呼叫 `list_agents` | 久沒聯絡的顯示 offline、剛聯絡的顯示 online，判斷用的時間由 `actions` 內部取（`status.now()`），結果與重構前相同 | 自動：`test_actions_layer.py` ＋ 既有 agents 相關測試不改動全綠 |
| TC-A08 | 計畫·設計 1（list_site_files 本體不變） | 功能 | 有一個 online 的 agent 與一個可讀資料夾，代理回覆列表 | 呼叫 `list_site_files(compute_env, path)` | 回傳含 `compute_env`、`path`（用代理回的 path），並併入代理回的檔名／大小／時間；與重構前相同 | 自動：既有 `platform/tests/test_station_envs.py` 相關測試不改動全綠 |
| TC-A09 | 計畫·設計 1（list_site_files 本體不變） | 例外 | 路徑不合法（例如不在可讀範圍）或環境離線 | 呼叫 `list_site_files` | 回傳 `ok: False` 與拒絕原因 `message`（取自 `JobRefused` 的文字）；不丟例外、不排入任何不該排的工作 | 自動：`test_actions_layer.py` ＋既有 `test_station_envs.py` |
| TC-A10 | 計畫·設計 2（逐位元組不變） | 功能 | 取 `v3` 起點的伺服器：每個工具的名稱、說明文字、annotations、輸入欄位 schema、伺服器 `instructions` 全文，寫成測試裡的固定字串 | 對重構後的 `build_server(...)` 取同樣資料並比對 | 完全相同，一個字都不差 | 自動：`test_actions_layer.py` |
| TC-A11 | 給維護者 第 2 句：「MCP 仍然只有六個唯讀工具」 | 功能 | 伺服器建好 | 列出工具 | 正好六個：`get_compute_env`、`get_run`、`list_agents`、`list_compute_envs`、`list_runs`、`list_site_files`；每個 `read_only_hint` 為 True；`destructive_hint` 不是 True；輸入欄位沒有 `confirm`、`yes`、`launch`、`cancel`、`kind`、`command` 之類 | 自動：既有 `test_mcp.py::test_tc024_exactly_six_read_only_tools` 與 `test_launch_platform.py:275`，不得改動斷言 |
| TC-A12 | 計畫·設計 1（讀取動作只讀） | 功能 | 一個有資料的平台 | 呼叫六個唯讀動作，前後比對資料庫與索引 | 沒寫入任何 run 狀態；回傳內容裡沒有任何 token／憑證 | 自動：既有 `test_station_envs.py::test_tc073_the_read_only_tools_write_nothing_and_show_no_token` 不改動全綠 |
| TC-A13 | 計畫·設計 2（工具本體變成一行呼叫） | 功能 | 讀 `mcp_server.py` 原始碼（AST） | 檢查六個工具函式的本體 | 每個工具本體（去掉說明字串後）只有一個陳述式，且該陳述式是呼叫 `actions.<同名函式>`（`list_site_files` 是 `return await actions.list_site_files(...)`）；本體裡沒有 `if`、`try`、迴圈 | 自動：`test_actions_layer.py` |

## User Story 2 — 送出與取消仍然只能在終端機按 y（優先度 P1）

維護者原話：「送出與取消仍然只能在終端機按 y。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-B01 | 計畫·設計 5(d) | 功能 | 一個可用的算力環境與一份合法的送出內容（bundle） | `actions.launch(state, ce, bundle, confirmed_by=actions.TERMINAL)` | 剛好排入一筆 launch 工作、寫入一筆 kind 為 launch 的確認紀錄，確認紀錄裡的雜湊等於 `common.bundle_sha256(bundle)`；回傳 `(確認編號, 工作編號)`，與直接呼叫 `confirm.confirm_launch` 的結果同形 | 自動：`test_actions_layer.py`（計畫 5(d)） |
| TC-B02 | 計畫·設計 1（cancel） | 功能 | 已有一筆送出紀錄（有 Slurm 工作編號）與合法的取消內容 | `actions.cancel(state, ce, bundle, confirmed_by=actions.TERMINAL)` | 剛好排入一筆 `cancel_run` 工作、一筆 kind 為 cancel 的確認紀錄；回傳 `(確認編號, 工作編號)` | 自動：`test_actions_layer.py` |
| TC-B03 | 計畫·Contract round 1 第 3 項 | 功能 | 假時鐘、`deadline_seconds=10`、`offline_after` 指定值 | 用這些關鍵字呼叫 `actions.launch`／`actions.cancel`（有 TERMINAL） | 工作的建立時間、期限與 offline 判斷，和用相同參數直接呼叫 `confirm.confirm_launch`／`confirm_cancel` 的結果完全一致（參數原封傳下去） | 自動：`test_actions_layer.py`；對照既有 `test_launch_platform.py` 的同類斷言 |
| TC-B04 | 計畫·設計 5(c) | 例外 | 同 TC-B01 的環境與內容，記下 jobs／confirmations／launches 三張表的筆數 | `actions.launch(..., confirmed_by="yes")` | 丟 `JobRefused("no human confirmation channel")`；三張表筆數不變 | 自動：`test_actions_layer.py` |
| TC-B05 | 計畫·設計 5(c) | 例外 | 同上 | `actions.launch(..., confirmed_by=True)` | 同 TC-B04：拒絕、三張表不變 | 自動：`test_actions_layer.py` |
| TC-B06 | 計畫·設計 5(c) | 例外 | 同上 | `actions.launch(..., confirmed_by=None)` | 同 TC-B04：拒絕、三張表不變 | 自動：`test_actions_layer.py` |
| TC-B07 | 計畫·設計 5(c)；Contract round 2 第 2 項 | 例外 | 同上 | `actions.launch(state, ce, bundle)`（不給 `confirmed_by`） | 丟錯（Python 的 TypeError 或 JobRefused 皆可接受）；jobs、confirmations、launches 三張表都沒有新增 | 自動：`test_actions_layer.py` |
| TC-B08 | 計畫·設計 1（cancel 同樣拒絕） | 例外 | 已有送出紀錄與合法取消內容，記下三張表筆數 | `actions.cancel` 分別用 `confirmed_by="yes"`、`True`、`None`、不給 | 前三者丟 `JobRefused("no human confirmation channel")`，不給者丟錯；三張表筆數不變 | 自動：`test_actions_layer.py` |
| TC-B09 | 計畫·設計 1（TERMINAL 是物件不是字串） | 例外 | 同 TC-B04 | 檢查 `isinstance(actions.TERMINAL, str)`；再分別用 `str(actions.TERMINAL)`、`"TERMINAL"`、`"terminal"` 當 `confirmed_by` 呼叫 `launch` | `TERMINAL` 不是字串；三個長得像的字串全被拒絕（`JobRefused`），三張表不變 | 自動：`test_actions_layer.py` |
| TC-B10 | 計畫·Contract round 1 第 6 項 | 例外 | `state_path` 指向一個不存在的路徑 | `actions.launch(state_path, "x", {}, confirmed_by="yes")` | 丟的是 `JobRefused("no human confirmation channel")`（不是「找不到資料庫」或別的錯）；該路徑沒被建立，也沒開任何資料庫連線——表示 `confirmed_by` 檢查排在所有驗證與資料庫存取之前 | 自動：`test_actions_layer.py` |
| TC-B11 | 計畫·設計 1（驗證照舊）；Safety Net 送出前驗證 | 例外 | (a) 環境離線或不存在；(b) run 名稱已被用掉 | 各自 `actions.launch(..., confirmed_by=actions.TERMINAL)` | 丟 `JobRefused`，文字與重構前 `jobs.check_target`／`jobs.check_run_name`／`confirm_launch` 的拒絕文字相同；confirmations 與 jobs 都沒有新增（確認與排入「全有或全無」） | 自動：`test_actions_layer.py` ＋既有 `test_launch_platform.py`／`test_launch_followup.py` 不改動全綠 |
| TC-B12 | 計畫·設計 1（cancel 驗證照舊） | 例外 | 取消內容指向離線的環境或別的 agent | `actions.cancel(..., confirmed_by=actions.TERMINAL)` | 丟 `JobRefused`，文字與重構前相同；沒有新增任何確認或工作 | 自動：`test_actions_layer.py` ＋既有 `test_launch_platform.py` |
| TC-B13 | 給維護者 第 2 句；計畫·設計 3 | 功能 | 終端機（偽終端）、合法的 `abf-platform launch …` 參數 | 看完畫面後在提問「確定送出？(y/N)」回答 `y` | 與重構前完全相同：交給代理、印出「已交給代理 … 確認編號 …」、之後印出「已送出：Slurm 工作編號 …」，離開碼 0；佇列裡剛好一筆 launch | 自動：既有 `platform/tests/test_launch_cli.py`、`test_launch_e2e.py` 不改動斷言全綠 |
| TC-B14 | 給維護者 第 2 句；計畫·設計 3（「只在 terminal.ask 回答 yes 之後」） | 例外 | 同 TC-B13，但 spy 住 `actions.launch` | 在提問回答 `n`（或直接 Enter） | stderr 印「未送出」，離開碼 1；`actions.launch` 一次都沒被呼叫；jobs、confirmations 沒有新增 | 自動：`test_actions_layer.py` ＋既有 `test_launch_cli.py` |
| TC-B15 | 給維護者 第 2 句；計畫·設計 3（TTY 檢查留在 terminal.py） | 例外 | 沒有互動終端機（管線、無 TTY），帶或不帶任何旗標／環境變數 | 執行 `abf-platform launch …` | 在問任何問題之前就拒絕，文字說「要在終端機上互動回答 y 才會送出…沒有任何旗標或環境變數能代替這個回答」；沒有排入任何工作，`actions.launch` 未被呼叫 | 自動：既有 `test_launch_cli.py` ＋`test_actions_layer.py` |
| TC-B16 | 給維護者 第 2 句；計畫·設計 3（cancel） | 功能 | 終端機、一筆已送出的 run | `abf-platform cancel <run>`，在「確定取消？(y/N)」回答 `y` | 與重構前相同：排入一筆 cancel_run、印出「取消請求已送出（Slurm 工作 …）」，離開碼 0 | 自動：既有 `test_launch_cli.py`／`test_launch_followup.py` 不改動斷言全綠 |
| TC-B17 | 給維護者 第 2 句（cancel 回答 n） | 例外 | 同 TC-B16，spy 住 `actions.cancel` | 在提問回答 `n` | stderr 印「未取消」，離開碼 1；`actions.cancel` 未被呼叫；沒有新增工作或確認 | 自動：`test_actions_layer.py` ＋既有 `test_launch_cli.py` |
| TC-B18 | 計畫·設計 3 | 功能 | 讀 `abf_launch/cli.py`（AST） | 檢查 import 與 `cmd_launch`、`cmd_cancel` | 不再匯入 `confirm`；兩個指令各只透過 `actions.launch`／`actions.cancel` 排工作，呼叫都帶 `confirmed_by=actions.TERMINAL`，且在同一函式內位於 `terminal.ask(...)` 呼叫之後 | 自動：`test_actions_layer.py` |
| TC-B19 | 計畫·設計 3（提問留在 terminal.py） | 功能 | 讀 `abf_launch/cli.py` 與 `terminal.py` | 檢查誰負責 TTY 檢查與 y/n 提問 | `terminal.py` 仍定義 `terminal_problem`、`ask`；`cli.py` 自己沒有 `input(` 或自己讀 stdin 的提問 | 自動：`test_actions_layer.py` |
| TC-B20 | 計畫·Facts（TC-061 要保持綠） | 功能 | 既有測試 | 跑 `test_launch_platform.py:697` 那條（CLI 沒有 resume、retry、yes 之類旗標） | 通過，且該測試斷言與 `v3` 起點相同 | 自動：既有 `test_launch_platform.py`（TC-061）不改動全綠 |

## User Story 3 — 所有入口只經過動作層，且沒有第二條排工作的路（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 計畫·設計 5(b) | 功能 | 讀 `mcp_server.py`（AST，含 `from . import x` 這種相對匯入與 `import abf_platform.x`） | 列出它從 `abf_platform` 匯入的所有東西 | 只有 `actions`；沒有 `agents`、`compute_envs`、`jobs`、`status`、`store`、`confirm` | 自動：`test_actions_layer.py` |
| TC-C02 | 計畫·Contract round 1 第 5 項 | 功能 | 讀 `mcp_server.py` 全文 | (a) 找 `actions.launch`、`actions.cancel`、`TERMINAL` 的任何引用（屬性、from-import、別名）；(b) 用正規式 `confirm\b` 搜全文 | 兩者都找不到 | 自動：`test_actions_layer.py` ＋既有 `test_launch_platform.py:254` 的文字掃描 |
| TC-C03 | 計畫·設計 5(b)；Contract round 1 第 2 項 | 功能 | 掃 `platform/abf_platform/`、`platform/abf_station/`、`platform/abf_launch/` 底下非測試的 Python（AST） | 找出所有匯入 `confirm` 模組的檔案（`from . import confirm`、`from .confirm import …`、`from abf_platform import confirm`、`import abf_platform.confirm`、`importlib`） | 只有 `actions` 套件底下的檔案；`abf_launch/cli.py` 不在其中；`platform/tests/` 不在掃描範圍 | 自動：`test_actions_layer.py` |
| TC-C04 | 計畫·Contract round 2 第 1 項（阻擋性） | 功能 | 掃同樣三個目錄的非測試 Python（AST） | 找出所有引用 `actions.launch`、`actions.cancel`、`TERMINAL` 的檔案（屬性、from-import、別名都算） | 只有 `abf_launch/cli.py` 與 `actions` 套件本身；其他檔案（含 `mcp_server.py`、`receiver.py`、`abf_station/*`、`abf_platform/cli.py`）一個都沒有——終端機指令仍是排入 launch／cancel 的唯一入口 | 自動：`test_actions_layer.py` |
| TC-C05 | 計畫·設計 5(b)、Contract round 2 第 1 項（掃描要能變紅） | 例外 | 在暫存目錄造假原始碼：`mcp_server` 式檔案匯入 `jobs`；一般檔案 `from abf_platform import confirm`；另一檔案 `from abf_platform import actions as a; a.launch(...)`；再一檔案 `from abf_platform.actions import TERMINAL` | 對這些假檔跑與 TC-C01、C03、C04 同一套掃描函式 | 每一種形式都被抓到並回報違規檔名；乾淨的檔案不被誤報 | 自動：`test_actions_layer.py` |
| TC-C06 | 計畫·Facts（釘住的守門測試）；Not in this PR（不改它們） | 功能 | 取 `v3` 起點與本分支 | 跑 `test_launch_platform.py::TC-010`（第 254 行，沒有 launch／cancel／confirm 路由，`mcp_server.py`／`receiver.py`／`agents.py` 文字不含 `confirm`）、第 275 行、`test_mcp.py::tc024`、`test_launch_platform.py` TC-061（第 697 行）、`tests/no_second_run_state_test.sh`；並比對這幾處的 `git diff` | 兩邊都通過；這些測試的斷言、以及 `LAUNCH_ALLOW`（只有 `platform/abf_station/launch.py` 一筆）在 diff 裡沒有任何改動 | 自動：上述既有測試；diff 部分由驗收審查者讀 |
| TC-C07 | 計畫·設計 6、Contract round 1 第 3 項 | 功能 | 本分支相對 `v3` 的 diff | 列出動到的既有測試檔 | 除了「匯入壞掉才不得不改」之外，沒有任何既有測試被改；每一個被改的檔案與原因都寫在 `ledger.md`；沒有斷言被刪、放寬、跳過，沒有預期值為遷就新輸出而改 | 手動：驗收審查者讀 `git diff v3...HEAD` 與 `ledger.md`（`docs/TESTING.md` 無對應步驟） |

## User Story 4 — 打包、標頭、文件、紀錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01 | 計畫·Contract round 1 第 4 項 | 功能 | 讀 `platform/pyproject.toml` | 檢查 `[tool.setuptools] packages` | 含 `"abf_platform.actions"`；且 `platform/abf_platform/` 底下每個有 `__init__.py` 的資料夾都在清單裡（沒漏打包） | 自動：`test_actions_layer.py` 或既有打包測試 |
| TC-D02 | 計畫·Contract round 1 第 5 項（標頭） | 功能 | `actions/` 底下所有 `.py` | 跑既有「每個 Python 原始碼都說明為何不用現成工具」檢查 | `actions/__init__.py` 及其他檔都有 `# Not <工具>: <理由>` 或 `# Nothing existing: <理由>` 標頭並通過判定；既有檢查本身未被放寬 | 自動：既有 `test_scope.py::test_tc070_every_python_source_names_its_alternative` 不改動全綠 |
| TC-D03 | 計畫·Changes 第 3 項（更新 confirm.py 說明） | 功能 | 讀 `confirm.py` 開頭說明 | 檢查文字 | 不再宣稱「只有終端機指令（abf_launch）呼叫這個模組」；改成說只有 `actions` 可呼叫，且 009c 之前 `actions` 只接受終端機記號；也不再宣稱有測試掃描呼叫者而實際沒有 | 自動：`test_actions_layer.py`（文字斷言）；內容由驗收審查者讀 |
| TC-D04 | 計畫·設計 7 | 功能 | 讀 `docs/PLATFORM.md` | 找「Action layer」一節 | 有這一節，短，且講到三件事：動作放在哪（`platform/abf_platform/actions/`）、每個入口都呼叫它們、目前唯一的確認管道是終端機；其他既有文件測試（如 `tests/platform_direction_docs_test.sh`）仍綠 | 自動：文件測試（若執行者新增）＋ `tests/platform_direction_docs_test.sh`；內容由驗收審查者讀 |
| TC-D05 | 計畫·設計 7 | 功能 | 讀 `CHANGELOG.md` | 看 `3.0.0-dev (unreleased)` 區段 | 新增一行說明動作層（行為不變）；其他既有行未被改動 | 自動：`tests/` 中既有 changelog／版本測試不改動全綠；內容由驗收審查者讀 |
| TC-D06 | 計畫·Changes 第 1、5 項（先紅後綠） | 功能 | `ledger.md` | 讀 ledger | 記有：在 `actions/` 建立之前，`test_actions_layer.py` 的 (a)(b)(c)(d) 跑出 FAIL 的證據；之後 `cd platform && python -m pytest -q` 全綠與 WSL `bash tests/run_all.sh` 全綠的證據；被改過的既有測試逐一列出（或寫「無」） | 手動：驗收審查者讀 `specs/009b-action-layer/ledger.md`（`docs/TESTING.md` 無對應步驟） |
| TC-D07 | 計畫·Changes 第 5 項 | 功能 | 本分支完成 | 跑整個 `platform` 的 pytest；跑 `tests/run_all.sh`（WSL／CI） | 全部通過，沒有被跳過的新增例外 | 自動：`cd platform && python -m pytest -q`；CI／WSL `bash tests/run_all.sh` |

## 不在範圍（計畫「Not in this PR」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E01 | 不在範圍：沒有新的 MCP 工具、沒有寫入類工具 | 不在範圍 | 伺服器建好 | 列出工具 | 工具仍是那六個；名稱沒有 `launch`、`cancel`、`confirm`；`actions` 裡的 `launch`、`cancel` 不會變成工具 | 自動：`test_actions_layer.py` ＋既有 `test_mcp.py::tc024` |
| TC-E02 | 不在範圍：沒有新的 HTTP 路由 | 不在範圍 | 一個運作中的平台 | 對 `/launch`、`/cancel`、`/confirm`、`/confirmation`、`/jobs`、`/runs/abc/cancel`、`/api/launch` 等路徑用 GET／POST／PUT／DELETE 各打一次，帶或不帶 token | 全部回 401、404 或 405；jobs、confirmations、launches 三張表筆數不變；`receiver.py` 的路由清單與 `v3` 起點相同 | 自動：既有 `test_launch_platform.py::test_tc010_there_is_no_door…`；路由清單相等由 `test_actions_layer.py` 比對 |
| TC-E03 | 不在範圍：沒有 elicitation（MCP 向人提問表單）、沒有確認頁面（009c） | 不在範圍 | 掃 `platform/` 非測試原始碼 | 找 `elicit`（不分大小寫）與任何「確認頁面」路由 | 一個都沒有；`actions.launch`／`cancel` 唯一接受的 `confirmed_by` 就是 `TERMINAL`（見 TC-B04 至 TC-B09） | 自動：`test_actions_layer.py` |
| TC-E04 | 不在範圍：沒有身分（009d） | 不在範圍 | `inspect.signature` | 檢查 `actions.launch`、`actions.cancel` 的參數 | 只有 `state_path`、`ce_name`、`bundle`、`confirmed_by`（僅限關鍵字）、`clock`、`deadline_seconds`、`offline_after`；沒有使用者、token、lab 之類的參數；`actions/` 底下沒有登入／身分程式 | 自動：`test_actions_layer.py` |
| TC-E05 | 不在範圍：沒有 resume（009e） | 不在範圍 | `actions` 與 `abf_launch` 的公開名稱 | 找 `resume`、`retry` | `actions` 裡沒有這類函式；CLI 沒有這類旗標（TC-B20 同一個既有測試） | 自動：`test_actions_layer.py` ＋既有 TC-061 |
| TC-E06 | 不在範圍：沒有開發模式（009f） | 不在範圍 | 讀 `actions/` 原始碼（AST）；另設環境變數 `ABF_DEV`、`ABF_PLATFORM_DEV`、`ABF_PLATFORM_YES`、`ABF_YES` 為 `1` | (a) 找 `os.environ`、`getenv`；(b) 在這些環境變數下用 `confirmed_by="yes"` 呼叫 `launch` | (a) `actions/` 自己沒有讀環境變數；(b) 仍被拒絕，三張表不變——沒有任何開關能讓非終端機的值通過 | 自動：`test_actions_layer.py` |
| TC-E07 | 不在範圍：不改 instructions／prompts（009g） | 不在範圍 | 伺服器建好 | 讀 `instructions`；列出 prompts | `instructions` 與 `v3` 起點逐字相同（同 TC-A10）；伺服器沒有新增任何 prompt | 自動：`test_actions_layer.py` |
| TC-E08 | 不在範圍：不改 hooks、憲法、`.github/`、不改釘住的測試與 `LAUNCH_ALLOW` | 不在範圍 | 本分支相對 `v3` 的 diff | 列出動到的路徑 | 沒有任何檔案位於 `hooks/`、`.specify/memory/constitution.md`、`.github/`；`tests/no_second_run_state_test.sh` 的 `LAUNCH_ALLOW` 與 TC-010／tc024／TC-061 的斷言沒有改動；`spec.md`、`test-case*.md` 在實作期間沒被改 | 手動：驗收審查者讀 `git diff v3...HEAD`（`docs/TESTING.md` 無對應步驟） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-F01 | 原則 I.2：至多一條自己的排工作路徑，且只在使用者確認後 | 功能 | 跑 `tests/no_second_run_state_test.sh`（其送出掃描涵蓋 `platform/abf_platform` 含新資料夾 `actions/`） | 執行；並檢查 `actions/` 原始碼 | 通過；`LAUNCH_ALLOW` 仍只有 `platform/abf_station/launch.py` 一筆；`actions/` 沒有 `sbatch` 之類的送出字樣——送出者仍只有代理的 launch 工作 | 自動：`tests/no_second_run_state_test.sh` |
| TC-F02 | 原則 I.2：不得有第二份 run 狀態、狀態機、常駐監看程式 | 功能 | 跑既有 `test_scope.py::test_tc071_no_submission_no_resident_loop_no_committed_database` | 執行；並確認 `actions/` 沒有自己的資料庫檔、迴圈或常駐程序 | 通過；`actions/` 只是呼叫現有的 `status`／`jobs`／`store`／`confirm`，沒有新增任何存放 run 狀態的檔案 | 自動：既有 `test_scope.py` TC-071，不改動全綠 |
| TC-F03 | 安全網：送出命令完整顯示並等明確確認才執行；計畫稱「沒有放寬任何關卡」 | 功能 | 在 `v3` 起點與本分支各跑一次 `test_launch_platform.py`、`test_launch_cli.py`、`test_station_launch.py::test_unconfirmed_launch_is_refused` | 比較兩邊結果與這些檔案的斷言 | 兩邊都通過；本分支的斷言沒有比 `v3` 弱；以前被拒絕的做法（無確認、確認雜湊對不上、環境離線、名稱重複）現在仍被拒絕，唯一新增的是對非終端機 `confirmed_by` 的拒絕 | 自動：上述既有測試；與 `v3` 比較由驗收審查者執行 |
