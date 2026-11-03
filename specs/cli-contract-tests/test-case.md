# 測試案例：abf-platform 命令列契約測試（退出碼、stdout／stderr 分離、說明文字快照）

**規格**：`specs/cli-contract-tests/plan.md`（本任務無獨立 spec.md，以 plan 的「目標」「維護者原話」「失敗先行測試」「完成標準」「不做」為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，命令列怎麼反應（拒絕、提示、停下），而且不外洩內部資訊。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做，或有一條測試把「目前沒有」釘住，日後有人加了會變紅。

名詞：「葉子」＝最底層、真的會執行動作的命令（例如 `user add`），不是 `user` 這種只分類的上層。「快照」＝提交進版本庫的文字檔，測試只拿來比對，不自動改寫。退出碼：0＝成功、1＝執行失敗、2＝參數用法錯。

## User Story 1 — 每個命令的退出碼、輸出分流、錯誤不外洩（優先度 P1）

維護者原話（逐字）：「per command happy path, bad-arg (exit 2), runtime failure (exit 1)」「--json parses and stdout/stderr are separated; NO_COLOR」「errors have what/why/next and no traceback without --debug」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 1「per command …」；作法 5；失敗先行 2（`test_every_leaf_is_in_the_matrix`） | 功能 | 測試用的命令矩陣已寫好；`build_parser()` 是命令列的真實命令樹（含 `abf_launch` 掛進來的 `launches`、`fetch-records`、`launch`、`cancel`、`forget`、`resume`、`relaunch`） | 把矩陣裡的葉子集合，和從 `build_parser()` 走訪出來的葉子集合比對 | 兩個集合完全相同；少登記任何一個葉子（或多登記不存在的）測試就紅。可在行程內跑完的葉子，矩陣為其登記「成功、參數錯誤、執行失敗」三種案例；確實沒有某種路徑的命令（例如不可能失敗者），矩陣內明寫「無此路徑」與理由，不得留空 | 自動：`platform/tests/test_cli_contract.py::test_every_leaf_is_in_the_matrix` |
| TC-002 | 作法 5 末項；失敗先行 3（`test_leaf_help_exits_zero`） | 功能 | 矩陣中的每個葉子 | 對每個葉子執行 `<命令> --help` | 每一個葉子都：結束時退出碼為 0（`SystemExit(0)`）、stdout 有內容、stderr 是空的 | 自動：`test_cli_contract.py::test_leaf_help_exits_zero` |
| TC-003 | 原話 1「bad-arg (exit 2)」；作法 5；失敗先行 4（`test_bad_arg_exits_two`） | 例外 | 矩陣中的每個葉子；資料夾用暫存的 `ABF_PLATFORM_DB` | 對每個葉子至少給一次錯誤用法：缺必填參數，或給錯型別（例如 `--port abc`）；沒有任何參數可錯的葉子，給一個不存在的選項 | 每個案例：`SystemExit(2)`；stderr 含 `usage:`；stdout 是空的；輸出不含 `Traceback` | 自動：`test_cli_contract.py::test_bad_arg_exits_two` |
| TC-004 | 原話 1「runtime failure (exit 1)」；作法 4；失敗先行 5（`test_runtime_failure_exits_one`） | 例外 | 暫存資料夾；下列七種壞情況：`user add`（名字重複）、`user cloud-cap`（沒有這個人／壞數字）、`ce create`（壞設定）、`ce show`（沒有這個環境）、`web --host 0.0.0.0`、`dataset show`（沒有這個資料集）、`agent-token new`（沒給 `--user`） | 逐一執行這七種 | 每個案例：退出碼 1；stdout 是空的；stderr 至少 20 個字元且含中文說明；其中 `user add`、`user cloud-cap`、`ce create`、`web --host 0.0.0.0`、`agent-token new` 這五種以 `rejected:` 開頭；`ce show` 以 `compute environment ` 開頭；`dataset show` 不檢查前綴（維護者裁決 11-03：合約對齊現況程式，不改 cli.py；統一錯誤格式另開任務）；輸出不含 `Traceback`、`File "`、`SELECT `、`INSERT `、`sqlite`、測試暫存路徑 | 自動：`test_cli_contract.py::test_runtime_failure_exits_one` |
| TC-005 | 原話 2「stdout/stderr are separated」；失敗先行 6（`test_happy_paths_keep_stdout_and_stderr_apart`） | 功能 | 暫存資料夾；乾淨環境 | 依序成功執行：`token new`、`user add`、`pat new`、`ce list`、`dataset list`、`rebuild` | 每個都：退出碼 0、stderr 是空的；`token new` 的 stdout 恰好有一個 `abf_…` 開頭的 token（不重複驗證儲存，那是 `test_cli.py::test_tc017` 的事） | 自動：`test_cli_contract.py::test_happy_paths_keep_stdout_and_stderr_apart` |
| TC-006 | 原話 2「--json parses」（現況版：既有的 JSON 輸出）；原話 3「--json … snapshots (committed)」；作法 3 第 2 點；失敗先行 7（`test_json_outputs_parse`） | 功能 | 暫存資料夾裡先建好一個環境與一個資料集；輸出中的時間戳與隨機值已先正規化 | 執行 `ce show <環境>` 與 `dataset show <資料集>` | 兩者的 stdout 都能被 `json.loads` 解析；stderr 是空的；stdout 與已提交的 `cli_json_*.txt` 快照內容相同（`ce show`、`dataset show` 各一份） | 自動：`test_cli_contract.py::test_json_outputs_parse` |
| TC-007 | 原話 2「NO_COLOR」；作法 3 末項；失敗先行 8（`test_no_color`） | 功能 | 兩種環境各跑一次：設 `NO_COLOR=1`、以及完全不設 | 在兩種環境下各執行三個代表性命令：`--help`、一個成功命令、一個失敗命令 | 六次執行的 stdout 加 stderr 全部不含 `\x1b[`（ANSI 顏色控制碼） | 自動：`test_cli_contract.py::test_no_color` |
| TC-008 | 原話 4「no traceback」；作法 4；失敗先行 9（`test_errors_never_leak`，行程內部分） | 例外 | TC-003、TC-004 的所有案例輸出 | 掃過這些案例的 stdout 與 stderr，找洩漏詞：`Traceback`、`File "`、`SELECT `、`INSERT `、`sqlite`、測試暫存路徑 | 沒有任何一個詞出現 | 自動：`test_cli_contract.py::test_errors_never_leak` |
| TC-009 | 原話 4「no traceback」；失敗先行 9（真行程部分） | 例外 | 用 `sys.executable` 起一個真的子行程；暫存資料夾；環境名稱「不存在」 | 執行 `python -m abf_platform ce show 不存在` | 退出碼 1；stderr 不含 `Traceback`（確認沒被捕捉的例外不會漏到使用者眼前） | 自動：`test_cli_contract.py::test_errors_never_leak`（真行程案例） |
| TC-010 | 作法 5 第二點（長駐命令只測參數錯誤） | 例外 | 不啟動任何伺服器 | 執行 `serve --port abc`、`web --port abc`、`mcp --port abc`（以實際 `build_parser()` 有 `--port` 的命令為準） | 每個都 `SystemExit(2)`，stderr 有 `usage:`，stdout 是空的，沒有佔用任何埠；`web --host 0.0.0.0` 的拒絕（退出碼 1、`rejected:`、無堆疊）已由 TC-004 涵蓋 | 自動：`test_cli_contract.py::test_bad_arg_exits_two`（含 serve／web／mcp） |
| TC-011 | 作法 5 第三點（`user passwd`） | 例外 | 測試不接終端機（非 TTY） | 執行 `user passwd`（帶它需要的參數） | 命令列拒絕並說明（以實際行為為準，寫進斷言）；不卡在等輸入、不露堆疊；stdout 沒有密碼相關內容 | 自動：`test_cli_contract.py`（`user passwd` 案例） |
| TC-012 | 原話 4「without --debug」、原話 2「--json」、原話 5「--version」（現況缺口）；作法 3 第 1 點；失敗先行 10（`test_documented_gaps`） | 不在範圍 | `build_parser()` 目前的狀態 | 檢查 `build_parser()` 的頂層與各子命令選項 | 目前**沒有** `--json`、`--debug`、`--version` 三個選項；測試通過且不用 `skip`。日後有人加上，這條會變紅，提醒同時補對應測試 | 自動：`test_cli_contract.py::test_documented_gaps` |

## User Story 2 — 說明文字與命令樹以提交的快照釘住（優先度 P1）

維護者原話（逐字）：「--help and --json syrupy snapshots (committed)」「Never run --snapshot-update blindly: review each snapshot diff.」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 原話 6；作法 2；失敗先行 1（`test_snapshot_missing_fails`） | 功能 | 比對輔助函式 `assert_golden(名稱, 文字)`；未設 `ABF_UPDATE_GOLDEN`；用暫存目錄當快照資料夾 | (a) 對不存在的快照檔呼叫；(b) 對內容不同的快照檔呼叫；(c) 兩種情況下檢查有沒有檔案被寫出；(d) 設 `ABF_UPDATE_GOLDEN=1` 再對不同內容呼叫一次 | (a) 失敗，不自動建檔；(b) 失敗並印出 unified diff（逐行差異）；(c) 未設環境變數時絕不寫檔；(d) 只有設了才寫檔，而且寫檔後這個測試**仍標記失敗**，逼人看 diff 後再重跑 | 自動：`platform/tests/test_cli_snapshots.py::test_snapshot_missing_fails` |
| TC-014 | 原話 3；作法 6(a)；失敗先行 11（`test_command_tree_snapshot`） | 功能 | 已提交 `platform/tests/__golden__/cli_tree.txt` | 走訪 `build_parser()` 的每個葉子，每葉輸出一行「命令路徑｜選項字串｜是否必填｜預設值｜help 全文」，排序後與 `cli_tree.txt` 比對 | 完全相同；任何命令、選項、預設值或說明文字被改動，測試就紅並印出差異；路徑中的暫存目錄先換成 `<TMP>`，以 `\n` 比對（CRLF 先正規化） | 自動：`test_cli_snapshots.py::test_command_tree_snapshot` |
| TC-015 | 原話 3「--help … snapshots」；作法 6(b)；失敗先行 11（`test_help_snapshots`） | 功能 | 設 `COLUMNS=100`；已提交 `cli_help_*.txt`（頂層一份、代表性葉子兩份） | 取得 `abf-platform --help` 與兩個代表性葉子的 `--help` 原文；把標題 `optional arguments:` 與 `options:` 正規化成同一個字；與快照比對 | 三份都與已提交快照完全相同；Python 小版本造成的標題差異不會讓它變紅 | 自動：`test_cli_snapshots.py::test_help_snapshots` |
| TC-016 | 原話 3「(committed)」；作法 2；失敗先行 12（`test_snapshots_are_committed`） | 功能 | `platform/tests/__golden__/` 資料夾 | 檢查資料夾裡每個檔案，以及測試程式引用的每個快照名稱 | 每個檔案非空、UTF-8、沒有 CRLF（只有 LF）；每個被引用的快照名稱都有對應檔案；至少有 `cli_tree.txt`、`cli_help_*.txt`（3 份）、`cli_json_*.txt`（2 份） | 自動：`test_cli_snapshots.py::test_snapshots_are_committed` |

## User Story 3 — 本任務不做的事（優先度 P2）

維護者原話（逐字）：「Do not touch platform/abf_station/ or plugin.json.」「any change to CI/workflow files is out of scope」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 原話 7；範圍：檔案；完成標準第 2 點；不做第 1 點、第 5 點 | 不在範圍 | 實作完成、工作樹乾淨 | 驗收時執行 `git diff --stat <base>...HEAD` | 變動檔案只有「範圍：檔案」列的新增：`platform/tests/test_cli_contract.py`、`platform/tests/test_cli_snapshots.py`、`platform/tests/__golden__/` 下的快照檔（另加本任務自己的 `specs/cli-contract-tests/` 文件與 ledger）；`platform/abf_platform/`、`platform/abf_launch/`、`platform/abf_station/`、`.claude-plugin/plugin.json`、`.github/`、`tests/platform_test.sh`、`platform/pyproject.toml`、`platform/constraints.txt` 零差異；既有測試檔（含 `test_cli_usage_doc.py`、`test_cli.py`、`test_dataset_cli.py`、`test_launch_cli.py`、`test_guidance.py`）零差異；`cli.py` 沒有新增 `--json`／`--debug`／`--version`／`NO_COLOR` 處理 | 手動：驗收者以 `git diff --stat <base>...HEAD` 核對（此步驟寫在本任務 ledger，不新增到 `docs/TESTING.md` 以免超出範圍） |
| TC-018 | 原話 1 的 click／syrupy 前提（現況不符）；原話 5「--version equals plugin.json」；環境事實；作法 1；不做第 2、3 點；完成標準第 4 點 | 不在範圍 | 兩個新測試檔、`__golden__/` | 驗收時用搜尋核對兩個新測試檔：是否出現 `click`、`syrupy`、`CliRunner`、`plugin.json`、網路存取；並在只裝 `mcp pytest httpx`（依 `constraints.txt`）的環境執行兩個新測試檔 | 完全沒有 `click`／`syrupy`／`CliRunner` 的 import 或使用；沒有讀 `plugin.json` 版本、也沒有「`--version` 等於 `plugin.json`」的測試；不連網；兩份測試檔在上述精簡環境下可跑並全綠；快照用 `__golden__/`（不是 `__snapshots__/`） | 手動：驗收者搜尋並在精簡環境執行（見 ledger） |
| TC-019 | 作法 5 第二點；不做第 4 點 | 不在範圍 | 驗收時讀兩個新測試檔 | 搜尋有沒有任何測試真的以成功模式啟動 `serve`、`web`、`mcp`，或啟動 `abf_station` 命令列 | 沒有；這三個長駐命令只有參數錯誤（TC-010）與 `web --host 0.0.0.0` 被拒（TC-004）的案例，不佔埠；沒有任何 `abf_station` 命令列的測試 | 手動：驗收者讀測試檔核對 |

## 憲法與安全網

專案事實「Never run」：不得連到站台或 HPC、不啟動 pipeline、不刪使用者資料、不使用 `~/.config/agentic-bioflow` 對真實部署。本任務是純新增測試，不碰憲法第 1～13 條的檢查本身；只需證明新測試不越界。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 專案事實「Never run」；作法 1（隔離環境） | 功能 | 兩個新測試檔 | 驗收時讀測試檔：資料位置與環境變數如何設定；執行 `abf_launch` 掛進來的 `launch`／`cancel`／`forget`／`resume`／`relaunch` 的案例做了什麼 | 所有行程內案例都用 `monkeypatch.setenv("ABF_PLATFORM_DB", tmp_path/…)` 並清掉其他 `ABF_PLATFORM_*`；真行程案例用 `pkg_env(ABF_PLATFORM_DB=…)`；解譯器一律 `sys.executable`（不用 PATH 上的 `python3`）；不讀寫 `~/.config/agentic-bioflow`；launch 類命令只測參數錯誤與可預期的拒絕，沒有任何一個案例真的提交、取消或刪除東西 | 手動：驗收者讀測試檔核對（見 ledger） |
