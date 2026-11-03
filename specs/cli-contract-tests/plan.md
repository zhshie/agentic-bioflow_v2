---
id: cli-contract-tests
title: abf-platform 命令列的契約測試（退出碼、stdout／stderr 分離、說明文字快照）——依現況 argparse 寫，不假設 click
tier: C
kinds: cli
risk: M
lane: L44-cli-contract-tests
branch: test/cli-contract-tests
base: v3
source: developer-agent 派工單（CliRunner＋syrupy 命令列測試）；本計畫查證後發現前提與 v3 不符，見「環境事實」
---

# cli-contract-tests

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/cli-contract-tests/plan.md`。**只處理本任務**。只新增測試，不改 `cli.py`。

## 目標
給 `abf-platform` 命令列（`platform/abf_platform/cli.py` 與其掛進來的 `platform/abf_launch/cli.py`）一組契約測試：每個可在測試中跑完的命令各有成功、參數錯誤（退出碼 2）、執行失敗（退出碼 1）三種結果的斷言；stdout 與 stderr 分開；錯誤不露堆疊、內部路徑、SQL；說明文字與命令樹以已提交的快照釘住，任何改動都要經人看過 diff。使用者意義：改命令列時，退出碼、錯誤格式、`--help` 不會被悄悄改掉。

## 維護者原話（verifier 出題用）
派工單原文（developer-agent 轉述維護者的要求，逐字）：
1. 「Add CliRunner (click) + syrupy tests for the abf-platform CLI: per command happy path, bad-arg (exit 2), runtime failure (exit 1)」→ 每個命令三種結果各一條案例。
2. 「--json parses and stdout/stderr are separated; NO_COLOR」→ stdout 與 stderr 分離一律要測；`--json`、`NO_COLOR` 見「作法 3」的現況判定。
3. 「--help and --json syrupy snapshots (committed)」→ 說明文字與 JSON 輸出的快照要提交進版本庫。
4. 「errors have what/why/next and no traceback without --debug」→ 錯誤訊息要說發生什麼、為什麼、下一步；沒有 `--debug` 時不得有堆疊。
5. 「--version equals plugin.json version」→ 見「作法 3」：現況沒有 `--version`，且兩個版本號本來就不同。
6. 「Never run --snapshot-update blindly: review each snapshot diff.」→ 快照只能由人看過 diff 後更新；測試預設為比對，不得在測試裡自動覆寫。
7. 「Do not touch platform/abf_station/ or plugin.json.」「any change to CI/workflow files is out of scope」→ 上述三處與 `.github/` 一律不動。

## 範圍：檔案
- 新增 `platform/tests/test_cli_contract.py`（命令契約：退出碼、stdout／stderr、無堆疊）。
- 新增 `platform/tests/test_cli_snapshots.py`（說明文字與命令樹快照；含小型比對輔助函式，見作法 2）。
- 新增 `platform/tests/__golden__/`（提交進版本庫的快照檔，文字檔 UTF-8、LF）。
- **不改**：`platform/abf_platform/`、`platform/abf_launch/`、`platform/abf_station/`、`.claude-plugin/plugin.json`、`.github/`、`tests/platform_test.sh`、`platform/pyproject.toml`、`platform/constraints.txt`。
- 被釘住、必須維持原樣的既有檔：
  - `platform/tests/test_cli_usage_doc.py`（模組說明字串須列出每個命令；本任務不改 `cli.__doc__`）。
  - `platform/tests/test_guidance.py` 第 461～462 行（釘住 `pyproject.toml` 的 `dependencies = ["mcp>=2.3,<3", "python-multipart"]` 與 `constraints.txt` 的 `mcp==2.3.0`）。
  - `platform/tests/test_catalogue.py::test_yaml_is_not_a_dependency`、`test_azure_upload.py` 約 835 行、`test_chat_tools.py` 約 322 行（讀 `pyproject.toml`／`constraints.txt` 的內容斷言）。
  - 既有 `platform/tests/test_cli.py`、`test_dataset_cli.py`、`test_launch_cli.py`（只准旁邊新增，不改）。
  - 列出全部：`git -C <repo> grep -n -E "pyproject|constraints|build_parser|add_subparsers" origin/v3 -- platform/tests tests`。

## 作法
1. **工具：不用 click、不用 syrupy**（理由見環境事實）。直接呼叫 `abf_platform.cli.main(argv)`，以 pytest 的 `capsys` 分別取 stdout、stderr；`SystemExit` 用 `pytest.raises` 取 `.code`（argparse 的參數錯誤是 `SystemExit(2)`，不是 return）。需要真行程的案例（`python -m abf_platform`，確認未捕捉的例外不外洩）沿用 `helpers.run_cli`／`pkg_env`，解譯器一律 `sys.executable`。資料夾用 `pkg_env(ABF_PLATFORM_DB=tmp_path/"data"/"index.db")`；行程內案例用 `monkeypatch.setenv("ABF_PLATFORM_DB", …)` 並清掉其他 `ABF_PLATFORM_*`。
2. **快照＝提交進版本庫的文字檔＋預設只比對**：輔助函式 `assert_golden(name, text)` 讀 `platform/tests/__golden__/<name>.txt`；內容不同就失敗並印出 unified diff；檔案不存在也失敗（不自動建立）。只有環境變數 `ABF_UPDATE_GOLDEN=1` 才寫檔，且寫檔後該測試仍標記失敗，逼人看 diff 後再重跑。快照檔由 executor 第一次產生後**逐檔人工審閱**再提交，ledger 貼 `git diff --stat` 與每份快照的前 20 行。
3. **現況缺口（此切片只記錄、不假裝測了）**：v3 的命令列是 argparse，沒有 `--json`、`--debug`、`--version`、`NO_COLOR` 的處理，錯誤格式是 `rejected: <英文>（<中文>）` 並 `return 1`，沒有統一的 what/why/next 結構，也沒有全域的堆疊開關。因此：
   - 不寫會立刻紅的 `--json`／`--debug`／`--version` 測試，也不用 `skip` 假裝；改成一條 `test_documented_gaps`，斷言 `build_parser()` 目前**沒有**這幾個選項（日後有人加上，這條會紅，提醒同時補測試）。
   - 對現有的 JSON 輸出（`ce show`、`dataset show` 以 `json.dumps` 印出）：測 stdout 可被 `json.loads` 解析、stderr 為空，並各留一份快照。
   - `--version` 對 `plugin.json`：不寫。兩個版本號本來就不同（`plugin.json` 為 `3.0.0-dev`，`pyproject.toml`／`abf_platform.__version__` 為 `0.1.0`），且 plugin.json 禁止動；改為待 developer-agent 決定（見回報問題 1）。
   - `NO_COLOR`：命令列從不輸出 ANSI。測試以 `NO_COLOR=1` 與未設兩種環境跑代表性命令（`--help`、一個成功、一個失敗），斷言 stdout＋stderr 不含 `\x1b[`。這同時防住 Python 3.14 起 argparse 說明文字預設上色的變化。
4. **錯誤格式斷言（現況版）**：每個「執行失敗」案例斷言：退出碼 1；stdout 為空；stderr 以 `rejected:` 開頭、至少 20 字元、含 `(`／`（` 之後的中文說明；不含 `Traceback`、`File "`、`SELECT `、`INSERT `、`sqlite`、`str(tmp_path)`。沿用既有測試的同款斷言寫法（見 `test_aws_ce.py:856`、`test_agent_token_revoke_id.py:265`）。
5. **命令矩陣**（executor 以實際 `build_parser()` 為準，用迴圈走遍葉子命令並在測試內斷言「矩陣涵蓋全部葉子」，缺一個就紅）：
   - 可在行程內跑完的：`token new`、`agent-token new|list|revoke`、`user add|cloud-cap|welcome`、`pat new|list|revoke`、`oauth revoke`、`ce create|update|list|show|…`、`dataset register|list|show`、`runs assign|offer-cleanup`、`rebuild`、以及 `abf_launch` 掛進來的 `launches`、`fetch-records`、`launch|cancel|forget|resume|relaunch`（只測參數錯誤與可預期的拒絕）。
   - 長駐命令 `serve`、`web`、`mcp`：不測「成功」（會佔埠），只測參數錯誤（`--port abc` → 2）與 `web --host 0.0.0.0` 被拒（退出碼 1、`rejected:`、無堆疊）；成功路徑已由 `test_cli.py` 的 `start_cli` 案例涵蓋。
   - `user passwd`：需要終端機輸入，只測非終端機時的拒絕訊息（以實際行為為準）。
   - 每個葉子：`--help` → `SystemExit(0)`、stdout 非空、stderr 空。
6. **說明文字快照**：(a) 命令樹快照——走訪 `build_parser()`（用 `_subparsers._group_actions[0].choices`，與 `test_cli_usage_doc.py` 同法），每個葉子輸出一行「命令路徑｜選項字串｜是否必填｜預設值｜help 全文」，排序後存 `cli_tree.txt`；(b) 頂層 `abf-platform --help` 與兩個代表性葉子的原始說明，設 `COLUMNS=100`，並把 Python 3.10 的 `optional arguments:` 與 3.10+ 的 `options:` 標題正規化成同一字，存 `cli_help_*.txt`。(a) 是主要保護，(b) 只作人看的輔助，避免因 Python 小版本差異而在 CI 變紅。
7. **WSL／跨平台**：快照檔以 `\n` 比對（讀入時 `newline=""` 後正規化 CRLF）；路徑一律先把 `str(tmp_path)` 換成 `<TMP>` 再比對。

## 失敗先行測試
這是新增覆蓋，現況程式碼多半已經符合，所以「先紅」以下列方式取得：先寫測試與**尚未提交的快照**，第一次跑因快照檔不存在而紅（作法 2），再人工審閱產生的檔案後提交。逐條：
1. `test_snapshot_missing_fails`：`assert_golden` 對不存在的檔案必須失敗；對不同內容必須失敗並印 diff；`ABF_UPDATE_GOLDEN` 未設時絕不寫檔。
2. `test_every_leaf_is_in_the_matrix`：矩陣的葉子集合＝`build_parser()` 的葉子集合。
3. `test_leaf_help_exits_zero`（每個葉子）：`--help` → 0、stdout 非空、stderr 空。
4. `test_bad_arg_exits_two`（每個葉子至少一個）：缺必填參數或給錯型別 → `SystemExit(2)`；stderr 有 `usage:`；stdout 空；無 `Traceback`。
5. `test_runtime_failure_exits_one`：至少涵蓋 `user add`（重名）、`user cloud-cap`（無此人／壞數字）、`ce create`（壞設定）、`ce show`（無此環境）、`web --host 0.0.0.0`、`dataset show`（無此資料集）、`agent-token new`（無 `--user`）。斷言見作法 4。
6. `test_happy_paths_keep_stdout_and_stderr_apart`：`token new`、`user add`、`pat new`、`ce list`、`dataset list`、`rebuild` 成功 → 退出碼 0、stderr 空；`token new` 的 stdout 恰有一個 `abf_…` token（與 `test_cli.py::test_tc017` 一致，不重複驗證儲存）。
7. `test_json_outputs_parse`：`ce show`、`dataset show` 的 stdout 可 `json.loads`、stderr 空；與 `cli_json_*.txt` 快照相符（快照內不含時間戳與隨機值，必要時先正規化）。
8. `test_no_color`：作法 3 的 `NO_COLOR` 斷言，兩種環境都不含 `\x1b[`。
9. `test_errors_never_leak`：作法 4 的洩漏詞清單，掃過案例 4、5 的所有輸出；另加一條真行程案例，確認 `python -m abf_platform ce show 不存在` 的 stderr 不含 `Traceback`。
10. `test_documented_gaps`：`build_parser()` 目前沒有 `--json`、`--debug`、`--version`（作法 3）。
11. `test_command_tree_snapshot`、`test_help_snapshots`：作法 6。
12. `test_snapshots_are_committed`：`__golden__/` 下每份檔案非空、UTF-8、無 CRLF，且每個被引用的快照名都存在。

## 完成標準（done when）
- 上面每條測試存在並綠；`tests/run_all.sh --timeout 900` 全綠（環境紅依 README 通例）。
- `git diff --stat` 只含「範圍：檔案」列的新增檔；`cli.py`、`pyproject.toml`、`constraints.txt`、`plugin.json`、`.github/`、`tests/platform_test.sh`、`platform/abf_station/` 零差異（ledger 貼證據）。
- 每份快照都有人工審閱記錄（ledger 貼前 20 行與審閱結論）；沒有任何一次寫檔是用 `ABF_UPDATE_GOLDEN=1` 一次性蓋掉全部卻沒看 diff。
- 新測試不依賴 `click`、`syrupy`、網路，且在 CI 的測試 venv（只裝 `mcp pytest httpx`，依 `constraints.txt`）下可跑。
- 專長守則檢查一行寫進報告。

## 環境事實
- **CLI 不是 click**：`platform/abf_platform/cli.py` 第 3 行 `import argparse`，`build_parser()`（約 737 行）用 `argparse.ArgumentParser(prog="abf-platform")`；`main(argv=None)`（約 905 行）回傳 `args.func(args)`；入口 `python -m abf_platform`（`__main__.py`）與 `[project.scripts] abf-platform = "abf_platform.cli:main"`。`abf_station` 另有自己的 `cli.py`，不在本任務。click 8.5.0 在 `constraints.txt` 只是 `mcp`／uvicorn 的間接依賴，專案沒有一行 click 程式；用 `click.testing.CliRunner` 只能測 click 命令，測不到這個 argparse 命令列。
- **syrupy 不是依賴**：`platform/pyproject.toml` 只有 `test = ["pytest", "httpx"]`；`constraints.txt` 沒有 syrupy；全 repo 沒有任何 `__snapshots__`。CI（`.github/workflows/tests.yml`）以 `tests/platform_test.sh` 第 252 行 `pip install -c constraints.txt 'mcp>=2.3,<3' pytest httpx` 建 venv，快取鍵含 `platform/constraints.txt` 的雜湊。要讓 CI 有 syrupy，必須改 `tests/platform_test.sh`（與 `constraints.txt`）——超出「只准新增測試」的範圍；若測試檔 `import syrupy` 而 venv 沒有，整份在 CI 上直接紅，若用 `importorskip` 則在 CI 靜默跳過、等於沒有覆蓋。所以本切片用標準函式庫的比對輔助函式取代，並把「改用 syrupy」列為後續（見「不做」）。
- `pyproject.toml` 的 `dependencies` 行被 `test_guidance.py` 逐字釘住；就算要加 syrupy，也只能加在 `[project.optional-dependencies] test`，且仍要同步 `platform_test.sh` 與 `constraints.txt`。
- `.claude-plugin/plugin.json` 版本為 `3.0.0-dev`；`abf_platform/__init__.py` 與 `pyproject.toml` 為 `0.1.0`。沒有任何程式讀 `plugin.json` 的版本，`platform/tests` 也沒有讀它的測試。
- 輸出走 `_say`（stdout）與 `_err`（stderr），皆 `flush=True`；錯誤慣例 `_err("rejected: …（中文）")` 後 `return 1`；`compute_envs.CEError` 與 `ValueError` 在命令函式內被接住。argparse 的參數錯誤由 argparse 自己 `SystemExit(2)`。
- 測試輔助：`platform/tests/helpers.py` 的 `pkg_env`、`run_cli`、`start_cli`；`conftest.py` 把 `platform/` 與 `tests/` 放進 `sys.path`。
- 本機 Windows 與 WSL：沿用既有測試的跑法（`tests/run_all.sh`，見裁決 1）；Git Bash 的 `python3` 可能是商店替身（PITFALLS 20c），所以測試只用 `sys.executable`。
- **PITFALLS（docs/PITFALLS.md）已查，相符項**：
  - 「20c. Two Windows-specific traps…」——`python3` 是 Microsoft Store 替身、跑了不印東西就結束；檢查：測試與輔助函式一律 `sys.executable`，不用 `command -v python3`。
  - 「16d. On this cluster, `python3` on PATH is a lockdown, not a stub.」——叢集上 `python3` 為受限直譯器；檢查：同上，不經 PATH 找 python。
  - 「46. Tests that make a temporary clone go all red when run in WSL from a Windows-made worktree (2026-10-14).」——本任務的測試不建暫時 clone；若 WSL 下 `constitution_scope_test.sh` 紅，是環境問題，以 CI 為準（裁決 4）。
  - 專案根目錄沒有 `PITFALLS.md`（只有 `docs/PITFALLS.md`），也沒有 `docs/solutions/`。

## 不做
- 不改 `cli.py`／`abf_launch/cli.py`，不新增 `--json`、`--debug`、`--version`、`NO_COLOR` 處理，不統一錯誤格式為 what/why/next。這些是產品改動，另開任務並於該任務補上對應測試；`test_documented_gaps` 會在它們落地時變紅提醒。
- 不引入 click 版命令列、不用 `CliRunner`；不引入 syrupy。要改用 syrupy 須另開任務：加進 `pyproject.toml` 的 `test` extra、`constraints.txt`、`tests/platform_test.sh` 的 `pip install`，並把 `__golden__/` 轉成 `__snapshots__/`；其中 `tests/platform_test.sh`／workflow 是否可動由維護者決定。
- 不加 `--version` 與 `plugin.json` 相等的測試，也不動 `plugin.json`。
- 不測 `serve`／`web`／`mcp` 的長駐成功路徑（已有 `test_cli.py`）；不測 `abf_station` 的命令列。
- 不改任何既有測試。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 20。
3. 快照更新規則：任何 `__golden__/` 檔的變動都必須在 ledger 附 diff 並說明原因；verifier 以 `git diff --stat` 與逐檔閱讀核對，不接受「全部重新產生」。
4. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明；落地前 `git merge origin/v3`。

## 專長守則（cli）

### executor

- 結束碼固定：0＝成功、1＝執行期失敗、2＝用法錯誤（參數錯、缺參數）。不自創其他碼，除非規格寫明。
- stdout 只放結果，stderr 放訊息、進度、警告。管線串接時 stdout 必須乾淨可解析。
- 提供 `--json`（機器可讀，穩定欄位）；尊重 `NO_COLOR` 環境變數與非 TTY（不輸出顏色、不跳進度動畫）。
- 錯誤訊息三要素：發生什麼（what）、為什麼（why）、下一步（next）。預設不印 traceback，只有 `--debug` 才印。
- 不在非互動環境提示輸入：缺資訊就以用法錯誤（碼 2）結束並說明要加哪個旗標；危險動作用 `--yes` 之類旗標，不用 TTY 提問。
- `--help` 每個指令都有，含至少一個範例；`--version` 輸出的版本必須等於 `plugin.json`（或專案指定的唯一版本來源）。
- 密鑰不得出現在輸出或日誌；從環境變數或設定檔讀，不收命令列明文參數。
- 先寫測試：每個指令用 click 的 `CliRunner`（或專案使用的等價物）測 happy path、錯誤參數、執行期失敗三種。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 每個新增或改動的指令各 3 條：成功、錯誤參數（結束碼 2）、執行期失敗（結束碼 1）。
- 輸出分流 TC：成功時 stdout 可被 JSON 解析（`--json`），stderr 無結果資料；失敗時訊息在 stderr。
- `NO_COLOR` TC：設定後輸出不含 ANSI 跳脫碼。
- 錯誤訊息 TC：含 what／why／next；不含 traceback，加 `--debug` 才有。
- `--version` 與版本來源檔一致的 TC。
- 快照 TC（syrupy）：`--help` 與 `--json` 輸出與入版控的快照比對。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：結束碼不符；結果寫到 stderr 或訊息寫到 stdout；缺 `--help` 範例；`--version` 與版本來源不一致；錯誤訊息只有堆疊；非互動環境卡在提問。
- **FAIL（快照）**：diff 中出現盲目 `--snapshot-update`（快照變動卻沒有對應的規格或需求依據）；快照被刪或改弱。
- **「需要人看的事」**：指令與旗標命名是否一致、說明文字是否白話。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
