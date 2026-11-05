---
id: cli-json-debug-version
title: abf-platform 命令列加上 --version、--json、--debug，並讓錯誤有統一的「發生什麼／為什麼／下一步」結構
tier: B
kinds: [cli]
risk: M
branch: feat/cli-json-debug-version
base: v3
source: specs/cli-contract-tests（11-03）的 test_documented_gaps 明寫「CLI 目前沒有 --json、--debug、--version，哪天加了這條會變紅，合約測試要跟著一起寫」；錯誤現況是 `rejected: English（中文）` 一句話，程式讀不出原因與下一步
---

# cli-json-debug-version

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/cli-json-debug-version/plan.md`。**只處理本任務**。risk M（範圍不含 `.github/`、`hooks/`、`plugin.json`〔只讀〕、`platform/abf_station/`；tier B 是「使用者看得見的 CLI 行為改變」，非 A）。

## 目標
`abf-platform` 的使用者（和寫腳本、接 Claude 的人）可以：`abf-platform --version` 看到產品版本；`abf-platform --json <指令>` 每個指令只印**一個** JSON 物件、鍵名固定，失敗時是 `{"error":{"what","why","next"}}`；`abf-platform --debug <指令>` 在 stderr 多出診斷行、stdout 一個字都不變。**不加旗標時，每個指令的輸出、結束碼、錯誤句子與現在逐字相同。**

**給 digest 的一行（Tier B）**：以前它會（沒有 `--version`／`--json`／`--debug`；出錯只印一句 `rejected: English（中文）`，腳本得靠字串比對）…，以後改成（三個旗標都有；`--json` 回固定鍵的 JSON，錯誤分成 what／why／next 三段；不加旗標時行為不變）。

## 維護者原話（verifier 出題用）
1. developer-agent 11-04 裁決一：「`--version` prints the product version from plugin.json (not pyproject 0.1.0)」→ 輸出的版本字串要等於 `.claude-plugin/plugin.json` 的 `version`（現為 `3.0.0-dev`）；測試**讀檔比對**，不寫死字串；不得是 `0.1.0`。
2. 裁決二：「`--json` prints one JSON object per command with stable keys and errors as {error:{what,why,next}}」→ stdout 恰好一個 JSON 物件；鍵固定；失敗時鍵為 `error.what`、`error.why`、`error.next`，三者皆為非空字串。
3. 裁決三：「`--debug` only adds stderr diagnostics and never changes stdout」→ 同一指令加 `--debug` 與不加，stdout 逐字相同、結束碼相同；多出來的只在 stderr。
4. 裁決四：「existing command outputs unchanged without the flags (tests must pin this)」→ 不加旗標的輸出由測試釘住（stdout、stderr、結束碼三項），其中包含既有 `rejected:` 句子。
5. 任務簡述：「errors look like 'rejected: English（中文）'」與「a unified what/why/next error format」→ 每個 `_err(` 呼叫點都要能提供 what／why／next（見作法 5）。

## 範圍：檔案
只准改這些：
- `platform/abf_platform/cli.py`：根 parser 加三個旗標；`main` 的 JSON／debug 外殼；`_say`／`_err` 的統一出口；每個 `_err(` 呼叫點補 why／next。
- 新檔 `platform/abf_platform/cliout.py`（可選；若放在 cli.py 內不超過約 120 行就不另開）：封裝「輸出模式」（plain／json）、版本讀取、debug 行。
- 新測試：`platform/tests/test_cli_flags.py`。
- 既有測試只准**依合約更新**的兩處：`platform/tests/test_cli_contract.py::test_documented_gaps`（見「允許的斷言」）、`platform/tests/__golden__/cli_help_top.txt`（根 `--help` 多三行，逐行讀 diff 後以 `ABF_UPDATE_GOLDEN=1` 更新）。
- 文件：`docs/PLATFORM.md`（命令列段加 `--version`／`--json`／`--debug` 三行說明與錯誤三段）。
- **不改** `platform/abf_launch/cli.py`、`platform/abf_station/`、`.claude-plugin/plugin.json`、`pyproject.toml`、`platform/abf_platform/__init__.py` 的 `__version__`（維持 0.1.0，與 `--version` 無關）。

## 作法
1. **旗標只掛在根 parser，且必須寫在指令之前**：`abf-platform --json ce show x`、`abf-platform --debug --json runs …`。理由：(a) `dataset register|show` 已有自己的 `--version`（資料集版本），掛到葉節點會撞名；(b) `test_agent_token_revoke_id.py:344` 釘住 `agent-token list --json` 結束碼 2（葉節點不認 `--json`），掛根不破；(c) `cli_tree`／葉節點的 `--help` 快照不變。三個旗標在根的順序任意（`--json --debug` 同 `--debug --json`）。
2. **`--version`**：stdout 印一行 `abf-platform <版本>`，結束碼 0，stderr 空。版本取自 repo 內 `.claude-plugin/plugin.json`（路徑由 `Path(__file__).resolve().parents[2]` 推，`PYTHONPATH=platform` 或 editable 安裝都找得到）。讀不到或沒有 `version` 鍵 → 失敗：結束碼 1，stdout 空，stderr 為三段式錯誤（what＝「找不到產品版本」，why＝「版本記在 .claude-plugin/plugin.json，這份安裝裡沒有它」，next＝「從 repository 的 checkout 執行，或設 PYTHONPATH=platform」）；**不得**退回 pyproject 的 0.1.0（裁決一）。`--json --version` 輸出 `{"ok":true,"command":"version","data":{"version":"<版本>"}}`。`--version` 單獨出現時不要求子指令（不能被 `required=True` 擋掉）。
3. **`--json` 成功格式（固定鍵）**：`{"ok": true, "command": "<指令路徑，空白分隔，如 ce show>", "data": <物件>, "output": ["<原本會印到 stdout 的每一行>", …]}`。
   - `_say` 在 JSON 模式下改為把行收進緩衝，指令結束後由 `main` 一次印出那一個物件（所以「一個指令一個物件」不靠各指令自己守）。
   - `data`：已經輸出 JSON 的 `ce show`、`dataset show` 把原本那個物件放進 `data`（內容與不加旗標時 stdout 解析後相同）；其他指令 `data` 為 `{}`。**本片不要求為每個指令重做結構化結果**（見不做）。`output` 一律有。
   - 鍵名只許這四個；之後加鍵要走新任務。
4. **`--json` 失敗格式**：結束碼不變（執行期失敗 1、參數錯誤 2）；**stdout 空**，stderr 印一個物件 `{"ok": false, "command": "…", "error": {"what": "…", "why": "…", "next": "…"}}`。argparse 的參數錯誤（結束碼 2）在 `--json` 模式下也走這個格式：`what`＝argparse 的錯誤句、`why`＝「命令列參數不符合這個指令的格式」、`next`＝「用 abf-platform <指令> --help 看正確用法」。三段皆非空、不含堆疊、SQL、內部路徑（沿用 `no_leak`）。
5. **三段式的來源（unified what/why/next）**：`_err(text, why=None, next=None)` 簽章；不加旗標時**只印 `text`**，與現在逐字相同（why／next 被忽略）。JSON 模式下 `what`＝`text` 去掉開頭 `rejected: `；`why`、`next` 由呼叫點給。第一片要求 `cli.py` 內**每一個** `_err(` 呼叫點（共約 49 處）都帶 `why=`、`next=`——**用 AST 測試強制**（`test_every_err_call_has_why_and_next`），漏一處就紅。why／next 的字面可以從現有句子後半拆出（例如 `; add one with: abf-platform user add` → next），不得新發明與事實不符的建議。
6. **長時間或不能進管線的指令在 `--json` 下拒絕**（結束碼 1、三段式錯誤）：`serve`、`web`、`mcp`（不會「結束」，不可能只印一個物件）；`user passwd`、`user passwd --temporary`、顯示臨時密碼的路徑（既有規則「密碼只能顯示在真正的終端機」；JSON 會被管線接走）。`token new`、`pat new`、`agent-token new` 等會印出密鑰的指令照既有行為把密鑰放進 `output`（與今天 stdout 相同，不新增暴露面）。
7. **abf_launch 註冊進來的指令（launch／cancel／resume／relaunch／fetch-records 等）本片在 `--json` 下一律拒絕**：what＝「這個指令還不支援 --json」，why＝「它的輸出由 abf_launch 自己的出口產生，尚未接上 JSON 外殼」，next＝「不加 --json 執行，或等後續版本」。不得讓它們在 JSON 模式下印出半個物件。（`--debug`、`--version` 對它們照常可用。）
8. **`--debug`**：只寫 stderr，每行以 `debug: ` 開頭。內容限定：指令路徑、**給了哪些選項的名稱（不含值）**、結束碼、耗時（毫秒）、以及未預期例外的堆疊（不加 `--debug` 時未預期例外的行為不變）。**不得**印任何選項的值、環境變數、token、密碼、資料庫或家目錄路徑。`--debug` 不得改變 stdout、結束碼、`--json` 的物件內容。
9. 不改 `adopt_orphans`／`ADOPTING` 的行為；不改 `cli.__doc__` 的「abf-platform: a | b | …」一行格式（`test_cli_usage_doc.py` 解析它）；旗標說明放在 argparse `help=`，不放進這行。
10. 不引入新依賴、不改 `pyproject.toml`。

## 失敗先行測試
全在 `platform/tests/test_cli_flags.py`，沿用 `test_cli_contract.py` 的 `home`／`call`／`no_leak` 做法（in-process `cli.main`，DB 在 tmp_path）。先寫、現在會紅。
- `test_version_prints_plugin_json_version`：`call(["--version"])` → 結束碼 0、stdout＝`abf-platform ` ＋ 直接讀 `.claude-plugin/plugin.json` 的 `version`、stderr 空；且 stdout 不含 `0.1.0`。
- `test_version_json`：`--json --version` 與 `--version --json` → stdout 解析後 `data.version` 等於 plugin.json 版本，`ok` 為 true。
- `test_version_missing_plugin_json_is_a_three_part_error`：以 monkeypatch 讓版本檔路徑指向不存在檔 → 結束碼 1、stdout 空、stderr 有 what／why／next 三段（plain 模式為一句 `rejected:` 開頭且含中文說明；`--json` 為三鍵物件），且不含 `0.1.0`。
- `test_json_success_envelope_has_stable_keys`：對 MATRIX 中每個「可成功」的葉節點（沿用 test_cli_contract 的 MATRIX／`_run_case`，排除 serve／web／mcp／passwd／abf_launch 指令）加 `--json` → stdout 恰好一個 JSON 物件，鍵集合恰為 `{"ok","command","data","output"}`，`ok is True`，stderr 空，結束碼 0。
- `test_json_data_of_ce_show_and_dataset_show_equals_plain_output`：`--json ce show s1` 的 `data` 等於不加旗標時 stdout 解析的物件（兩個既有 JSON 指令）。
- `test_json_output_lines_equal_plain_stdout`：同一指令加／不加 `--json`，`"\n".join(output)+"\n"`（或空）等於 plain stdout（證明包裝不吃字）。
- `test_json_error_is_what_why_next`：七種執行期失敗情境（user add、user cloud-cap 壞數字、ce create、ce show、web、dataset show、agent-token new；沿用 `RUNTIME`）加 `--json` → 結束碼 1、stdout 空、stderr 單一物件，`error` 三鍵且皆為非空字串、`what` 不以 `rejected:` 開頭、`no_leak` 通過。
- `test_json_argparse_error_is_what_why_next`：`--json user add`（缺參數）→ 結束碼 2、stdout 空、stderr 為三鍵物件，不含 `usage:` 堆疊以外的洩漏。
- `test_json_refused_for_long_running_and_secret_terminal_commands`：`--json serve`、`--json web`、`--json mcp`、`--json user passwd bob`、`--json user passwd bob --temporary` → 結束碼 1、stdout 空、三段式錯誤；且**沒有**啟動任何伺服器（serve／web／mcp 以 monkeypatch 讓 uvicorn／mcp 啟動函式一被呼叫就失敗）。
- `test_json_refused_for_launch_registered_commands`：abf_launch 註冊的每個指令（由 `test_cli_usage_doc._launch_commands()` 取得）加 `--json` → 結束碼 1、stdout 空、三段式錯誤，且沒有任何站台／平台工作被排（任務表列數不變）。
- `test_every_err_call_has_why_and_next`：用 `ast` 掃 `cli.py` 所有 `_err(...)` 呼叫，每一個都有 `why=` 與 `next=` 關鍵字且為非空字面或運算式。
- `test_plain_mode_err_text_unchanged`：不加旗標時，上面七種失敗與 `ce show`／`dataset show` 找不到的 stderr 逐字等於 v3（由 `git show origin/v3:…` 事先抄成測試內的常數，或以既有 `test_cli_contract`／`test_agent_token_revoke_id` 的斷言為準）。
- `test_debug_never_changes_stdout_or_exit`：MATRIX 中每個葉節點的 happy 與 fail 情境，加 `--debug` 與不加，`(rc, stdout)` 逐字相同；且 `--debug` 時 stderr 至少一行以 `debug: ` 開頭，不加時沒有任何 `debug:` 行。
- `test_debug_lines_leak_nothing`：帶 `--token`／密碼類選項值（如 `user add … --password` 若存在；否則用 `pat new` 與 `ce create` 的值）時，`--debug` 的 stderr 不含任何選項值、不含 tmp 家目錄路徑、不含 `Traceback`；選項只以名稱出現。
- `test_debug_with_json_keeps_object_identical`：`--debug --json X` 與 `--json X` 的 stdout 完全相同。
- `test_flags_not_accepted_after_the_command`：`ce list --json` → 結束碼 2（維持葉節點不認；與 `test_agent_token_revoke_id.py:344` 一致）。
- `test_without_flags_nothing_changes`（釘住裁決四）：不加旗標，對 MATRIX 每個葉節點的 happy／fail／bad 情境，記錄 `(rc, stdout, stderr)` 與 `git show origin/v3` 上同一測試環境的輸出比對——實作上由既有 `test_cli_contract.py`、`test_cli_snapshots.py`、`test_cli.py`、`test_dataset_cli.py` 等整組維持全綠來證明；ledger 附 `git diff --stat` 證明這些檔案除下節兩處外零改動。

## 允許的斷言（既有測試）
下列既有測試釘住本案會碰的句子或常數，**只准新增、不刪不放寬**（執行前用 `git -C <repo> grep -n "<字串>" origin/v3 -- platform/tests` 逐條對一次行號）：
- `test_cli_contract.py`：`test_documented_gaps`（約 333～346 行）**必定變紅**（它自己寫「哪天加了會變紅」）——這是唯一准許改的斷言：把「`--json`／`--debug` 不存在」改為「這兩個**只**在根 parser，葉節點沒有」，把「根沒有 `--version`」改為「根有 `--version`，且 `dataset register|show` 的 `--version`（資料集版本）仍在」。`RUNTIME` 的 TC-004 七案（`rejected:` 開頭、括號後有中文）、`xfail(strict=True)` 的 `ce show`／`dataset show` 與 `test_not_found_shows_use_their_own_wording`（找不到句子不以 `rejected:` 開頭）**逐字不動**；`test_user_passwd_refuses_without_a_terminal`、`test_happy_paths_exit_zero_with_empty_stderr`、`test_errors_never_leak*`、`test_no_color` 不動。
- `test_cli_snapshots.py`：`cli_tree`、`cli_help_user_add`、`cli_help_ce_create`、`cli_json_ce_show`、`cli_json_dataset_show` 快照**必須不變**；只有 `cli_help_top.txt` 允許更新（根選項多 `--version`、`--json`、`--debug` 三行），diff 要在 ledger 逐行說明。
- `test_agent_token_revoke_id.py`：17、18（`rejected: no live agent token with id %s`／`give either an agent name or --id N …`）、344（`agent-token list --json` 結束碼 2）。
- `test_owner_tokens.py:19`（`rejected: say whose agent this is with --user NAME (請用 --user 名字 指定這個代理是誰的)`）；`test_temp_password.py:633`（`rejected:` ＋ `終端機`）。
- `test_cli_usage_doc.py`（`cli.__doc__` 的指令清單）：docstring 那一行格式不動。
- `test_cli.py`、`test_dataset_cli.py`、`test_launch_cli.py`、`test_user_welcome.py:321`（in-process 與子程序呼叫 `abf_platform.cli.main`）、`test_actions_layer.py:499`（`_cli_tree`）、`test_pat.py:426`（以 AST 讀 `cmd_mcp`）、`test_owner_guard.py:118`（把 `abf_platform/cli.py` 列為受檢檔）：行為不變，維持綠。
- 以 shell 讀 `cli.py` 的文件測試：`tests/install_doc_test.sh:33`、`tests/migration_doc_test.sh:46`、`tests/operations_doc_test.sh:11`、`tests/hosted_deploy_test.sh:24`——只讀字串，改 `cli.py` 後須仍綠。
- `tests/jev_test.sh:508` 釘 `plugin.json` 版本為 `3.0.0-dev`：本案只讀 plugin.json，不改它。

## 完成標準（done when）
- 上節「失敗先行測試」每條綠；`tests/run_all.sh` 全綠（環境紅依 README 通例）。
- 不加旗標時行為與 v3 逐字相同：除 `test_documented_gaps` 與 `cli_help_top.txt` 外，所有既有測試與快照檔零改動（`git diff --stat` 貼進 ledger）。
- `abf-platform --version` 在本 checkout 印出 plugin.json 的版本（附實跑輸出）；`--json ce show` 與 `--debug ce show` 附實跑輸出。
- 閱卷另看：debug 行無任何選項值／密鑰；`--json` 錯誤三段皆為白話、非空；`docs/PLATFORM.md` 已寫三旗標與「旗標要放在指令前面」。
- PR 說明含 digest 那句「以前它會…，以後改成…」。

## 環境事實
- 入口：`platform/pyproject.toml` 的 `abf-platform = "abf_platform.cli:main"`；`__main__.py` 只轉呼叫 `main`。`main(argv)` 現為 `build_parser().parse_args(argv)` → `adopt_orphans()`（`ADOPTING = serve, web, mcp, ce`）→ `args.func(args)`（cli.py 約 898～911 行，共 911 行）。
- 輸出出口：`_say`（stdout）與 `_err`（stderr）各一個函式（cli.py 19、22 行）；`_err(` 約 49 處，皆以 `rejected:` 開頭或為 `ce show`／`dataset show` 的專用找不到句。`abf_launch/cli.py` 另有自己的 `_say`／`_err`（37、41 行）與 `add_commands(sub)`（446 行），本片不碰。
- 已會印 JSON 的只有 `ce show`（cli.py 約 469 行）與 `dataset show`（約 642 行）：`json.dumps(…, indent=2, sort_keys=True, ensure_ascii=False)`。
- 版本：`.claude-plugin/plugin.json` 的 `version` ＝ `3.0.0-dev`（blob 761b9ef）；`pyproject.toml` 與 `abf_platform.__version__` 都是 `0.1.0`，維持不動。`abf-station` 的 `--version` 用 `__version__`（`platform/abf_station/cli.py:142`），**不在本案範圍**，也不要改成一致。
- **pip 非 editable 安裝的風險**：`docs/PLATFORM.md` 第 17 行教人 `pip install ./platform`；非 editable 安裝後 `.claude-plugin/plugin.json` 不在套件旁邊，`--version` 會走作法 2 的失敗路徑。這是裁決一的直接後果，已列為問題請 developer-agent 確認（見回報）；executor 照作法 2 實作，不自行加 fallback。
- 測試殼層：`platform/tests/test_cli_contract.py` 的 `MATRIX`、`_run_case`、`call`、`no_leak`、`make_launch_dirs`、`helpers.run_cli/pkg_env` 可直接重用；`test_cli_snapshots.py` 的 `assert_golden`（`ABF_UPDATE_GOLDEN=1` 會寫檔但仍報失敗，需再跑一次）。
- 完整測試：`tests/run_all.sh` 在 Git Bash 會拒跑，請走 WSL（見 CLAUDE.md「For the executor and verifier」）；repo 與 worktree 要在本機磁碟。
- PITFALLS 已查，無相符項（`docs/PITFALLS.md` 搜 cli／argparse／stdout／stderr／version／json／rejected／plugin.json：命中的 `UnsupportedClassVersionError`、`nf-core` CLI、`claude` CLI 與本案無關；無 `docs/solutions/`）。

## 不做
- `--json` 的**逐指令結構化結果**（目前只有 `ce show`、`dataset show` 有 `data`，其餘 `data` 為 `{}`、內容在 `output`）：後續切片，逐指令加鍵要另開任務。
- abf_launch 註冊的指令（launch／cancel／resume／relaunch／fetch-records…）的 `--json` 支援：本片只拒絕並說清楚，後續切片接上 JSON 外殼。
- 把不加旗標時的錯誤句子也改成三段式：會動被測試釘住的 `rejected:` 句子，屬另一個 tier B 決定，要先問維護者。
- `abf-station --version` 與 `abf-station` 其他指令；`NO_COLOR` 處理；shell 補全；旗標放在指令之後（`ce list --json`）的支援。
- 改 `pyproject.toml`／`__version__`／`plugin.json`；為 pip 安裝版另找版本來源。

## 裁決
1. 以下四條逐字來自 developer-agent 11-04：(1) `--version` prints the product version from plugin.json (not pyproject 0.1.0)；(2) `--json` prints one JSON object per command with stable keys and errors as {error:{what,why,next}}；(3) `--debug` only adds stderr diagnostics and never changes stdout；(4) existing command outputs unchanged without the flags (tests must pin this).
2. 本計畫補的決定（executor 照做、不再問；若 developer-agent 不同意，改派前先告知）：①旗標只在根、須寫在指令之前；②JSON 錯誤印 stderr、stdout 空、結束碼不變；③serve／web／mcp／passwd／abf_launch 指令在 `--json` 下拒絕；④版本檔讀不到＝失敗，不退回 0.1.0；⑤不加旗標的錯誤句子不動。
3. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值。
4. 整套測試一律 `run_in_background`＋等待迴圈跑；WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明。
5. 「已知環境紅」依 README 通例（`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched`）。

## 裁決（developer-agent 11-04，回覆計畫幫手的待確認問題）
- Q1 版本來源：維持「讀不到 plugin.json 就三段式報錯、不退回 0.1.0」；pip 非 editable 安裝的版本來源列後續切片，不在本任務。
- Q2 文字模式的 what/why/next 不在本任務；維護者若要統一文字錯誤另開 tier B。
- Q3 旗標只掛根 parser、寫在指令前；abf_launch 指令的 --json 列後續切片。
- Q4 車道由我登佇列時補。

## 專長守則（[cli]）

（工作區沒有 `.claude/dev-profiles/[cli].md`；本任務無專長守則。）
