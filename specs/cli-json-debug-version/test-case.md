# 測試案例：abf-platform 命令列加上 --version、--json、--debug

**規格**：`specs/cli-json-debug-version/plan.md`（本任務沒有獨立 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞（各表共用）：

- 「**葉節點**」＝最末一層的指令，例如 `ce show`、`user add`。
- 「**既有指令清單**」＝現有測試 `platform/tests/test_cli_contract.py` 裡的 `MATRIX`，列出每個葉節點的「成功／失敗／參數錯誤」做法。
- 「**v3 / 不加旗標時**」＝改動之前的行為。
- 「**三段式錯誤**」＝錯誤有 `what`（發生什麼）、`why`（為什麼）、`next`（下一步）三段，三段都是非空的白話字串。
- 旗標一律寫在指令**前面**：`abf-platform --json ce show x`。
- 所有自動測試放在 `platform/tests/test_cli_flags.py`（新檔），或是既有測試檔維持全綠；每條測試在註解寫上它對應的 TC 編號。

## User Story 1 — `--version` 印出產品版本（優先度 P1）

維護者原話（裁決一）：「`--version` prints the product version from plugin.json (not pyproject 0.1.0)」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 裁決一；作法 2 | 功能 | 本 checkout 的 `.claude-plugin/plugin.json` 有 `version`（現為 `3.0.0-dev`）；不指定任何子指令 | 執行 `abf-platform --version` | 結束碼 0；stdout 恰為一行 `abf-platform ` 加上測試**直接讀 plugin.json 取得**的 version（不寫死字串）；stderr 空；沒有被「必須給子指令」擋掉 | 自動：`test_cli_flags.py::test_version_prints_plugin_json_version` |
| TC-002 | 裁決一 | 功能 | 同 TC-001 | 執行 `abf-platform --version` | stdout 不含 `0.1.0` | 自動：同上 |
| TC-003 | 作法 2 | 功能 | 同 TC-001 | 執行 `abf-platform --json --version` | stdout 恰為一個 JSON 物件 `{"ok":true,"command":"version","data":{"version":"<plugin.json 的 version>"}}`（解析後比對，`data.version` 與讀檔結果相等，`ok` 為 true） | 自動：`test_version_json` |
| TC-004 | 作法 1、2（三旗標順序任意） | 功能 | 同 TC-001 | 執行 `abf-platform --version --json`（順序反過來） | 結果與 TC-003 相同 | 自動：`test_version_json` |
| TC-005 | 作法 2 | 例外 | 把版本檔路徑指向不存在的檔案（測試用 monkeypatch） | 執行 `abf-platform --version`（不加 `--json`） | 結束碼 1；stdout 空；stderr 是一句以 `rejected:` 開頭、含中文說明的話（what＝找不到產品版本）；不含 `0.1.0` | 自動：`test_version_missing_plugin_json_is_a_three_part_error` |
| TC-006 | 作法 2、4 | 例外 | 同 TC-005 | 執行 `abf-platform --json --version` | 結束碼 1；stdout 空；stderr 為一個 JSON 物件，`error` 有 `what`（找不到產品版本）、`why`（版本記在 .claude-plugin/plugin.json，這份安裝裡沒有它）、`next`（從 repository 的 checkout 執行，或設 PYTHONPATH=platform），三者皆非空；不含 `0.1.0` | 自動：同上 |
| TC-007 | 作法 2（「沒有 version 鍵」） | 例外 | plugin.json 存在，但裡面沒有 `version` 鍵 | 執行 `abf-platform --version` | 與 TC-005 相同：結束碼 1、stdout 空、stderr 一句 `rejected:` 開頭，不退回印 `0.1.0` | 自動：同上 |

## User Story 2 — `--json` 成功時每個指令只印一個固定格式的物件（優先度 P1）

維護者原話（裁決二）：「`--json` prints one JSON object per command with stable keys and errors as {error:{what,why,next}}」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 裁決二；作法 3 | 功能 | 既有指令清單中每個「能成功」的葉節點（排除 serve／web／mcp／passwd／abf_launch 註冊的指令），資料庫在暫存資料夾 | 對每個加上 `--json` 執行其成功情境 | 結束碼 0；stdout 恰好一個 JSON 物件（不是兩個、不是物件加雜字）；stderr 空 | 自動：`test_json_success_envelope_has_stable_keys` |
| TC-009 | 裁決二；作法 3（鍵名只許四個） | 功能 | 同 TC-008 | 同 TC-008 | 物件的鍵集合恰為 `ok`、`command`、`data`、`output` 四個，不多不少；`ok` 為 true；`output` 是一個清單 | 自動：同上 |
| TC-010 | 作法 3 | 功能 | 資料庫裡有 `s1` 這個 ce | 執行 `abf-platform --json ce show s1` | `command` 的值是 `ce show`（指令路徑，空白分隔） | 自動：`test_json_success_envelope_has_stable_keys` |
| TC-011 | 作法 3 | 功能 | 同 TC-010 | 分別執行 `--json ce show s1` 與不加旗標的 `ce show s1` | `--json` 物件的 `data`，等於不加旗標時 stdout 解析出來的那個物件 | 自動：`test_json_data_of_ce_show_and_dataset_show_equals_plain_output` |
| TC-012 | 作法 3 | 功能 | 資料庫裡有一個已登記的資料集 | 分別執行 `--json dataset show …` 與不加旗標的 `dataset show …` | `data` 等於不加旗標時 stdout 解析出來的物件 | 自動：同上 |
| TC-013 | 作法 3（包裝不吃字） | 功能 | 同 TC-008 的每個葉節點 | 同一指令分別加／不加 `--json` | 把 `output` 清單用換行接起來再補結尾換行（清單為空則為空字串），逐字等於不加旗標時的 stdout | 自動：`test_json_output_lines_equal_plain_stdout` |
| TC-014 | 作法 6（印出密鑰的指令） | 功能 | 可執行 `token new`、`pat new`、`agent-token new` 的環境 | 各加 `--json` 執行 | 密鑰出現在物件的 `output` 裡（與今天 stdout 相同的那幾行）；stderr 空；沒有在 `output` 以外的地方多出現一次 | 自動：`test_json_output_lines_equal_plain_stdout`（含這三個指令） |
| TC-015 | 裁決三、二交會；作法 8 | 功能 | 同 TC-008 | 分別執行 `--debug --json X` 與 `--json X` | 兩者 stdout 完全相同（逐字） | 自動：`test_debug_with_json_keeps_object_identical` |
| TC-016 | 作法 1（三旗標順序任意） | 功能 | 同 TC-008 | 分別執行 `--json --debug X` 與 `--debug --json X` | stdout 逐字相同，結束碼相同 | 自動：同上 |
| TC-017 | 計畫「不做」第 1 條（逐指令結構化結果） | 不在範圍 | 同 TC-008 | 除 `ce show`、`dataset show` 外，對其他成功的葉節點加 `--json` | 它們的 `data` 是 `{}`（空物件），指令印出的內容在 `output`；沒有悄悄多出新鍵或新的結構化內容 | 自動：`test_json_success_envelope_has_stable_keys` |

## User Story 3 — `--json` 失敗時是 what／why／next，且不該進管線的指令會被拒絕（優先度 P1）

維護者原話（裁決二）：「errors as {error:{what,why,next}}」；任務簡述：「a unified what/why/next error format」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 裁決二；作法 4 | 例外 | 七種執行期失敗情境（沿用 `test_cli_contract.py` 的 `RUNTIME`）：user add、user cloud-cap 壞數字、ce create、ce show、web、dataset show、agent-token new | 各自加 `--json` 執行 | 結束碼 1；stdout 空；stderr 恰好是**一個** JSON 物件 | 自動：`test_json_error_is_what_why_next` |
| TC-019 | 裁決二 | 例外 | 同 TC-018 | 同 TC-018 | 物件 `ok` 為 false、有 `command`；`error` 有 `what`、`why`、`next` 三個鍵，三者都是**非空字串** | 自動：同上 |
| TC-020 | 作法 5（what＝去掉 `rejected: ` 的句子） | 例外 | 同 TC-018 | 同 TC-018 | `what` 不以 `rejected:` 開頭 | 自動：同上 |
| TC-021 | 作法 4（沿用 `no_leak`） | 例外 | 同 TC-018 | 同 TC-018 | stderr 不含堆疊、SQL、內部路徑（既有 `no_leak` 檢查通過） | 自動：同上 |
| TC-022 | 作法 4（參數錯誤） | 例外 | 無 | 執行 `abf-platform --json user add`（缺必要參數） | 結束碼 2；stdout 空；stderr 恰好一個 JSON 物件，`ok` 為 false，`error` 有非空的 `what`、`why`、`next` | 自動：`test_json_argparse_error_is_what_why_next` |
| TC-023 | 作法 4 | 例外 | 同 TC-022 | 同 TC-022 | `what` 是 argparse 自己的錯誤句；`why` 恰為「命令列參數不符合這個指令的格式」；`next` 以「用 abf-platform 」開頭並以「--help 看正確用法」結尾 | 自動：同上 |
| TC-024 | 作法 4（不洩漏） | 例外 | 同 TC-022 | 同 TC-022 | stderr 不含堆疊、SQL、內部路徑 | 自動：同上 |
| TC-025 | 作法 4（結束碼不變） | 例外 | 同 TC-018 與 TC-022 的失敗情境 | 同一指令分別加／不加 `--json` | 結束碼相同（執行期失敗 1、參數錯誤 2） | 自動：`test_json_error_is_what_why_next`、`test_json_argparse_error_is_what_why_next` |
| TC-026 | 作法 6 | 例外 | 測試讓伺服器啟動函式「一被呼叫就失敗」 | 執行 `abf-platform --json serve` | 結束碼 1；stdout 空；三段式錯誤；伺服器**沒有**被啟動 | 自動：`test_json_refused_for_long_running_and_secret_terminal_commands` |
| TC-027 | 作法 6 | 例外 | 同 TC-026 | 執行 `abf-platform --json web` | 同 TC-026 | 自動：同上 |
| TC-028 | 作法 6 | 例外 | 同 TC-026 | 執行 `abf-platform --json mcp` | 同 TC-026 | 自動：同上 |
| TC-029 | 作法 6（密碼只能顯示在真正的終端機） | 例外 | 有使用者 `bob` | 執行 `abf-platform --json user passwd bob` | 結束碼 1；stdout 空；三段式錯誤；沒有設定或顯示任何密碼 | 自動：同上 |
| TC-030 | 作法 6 | 例外 | 有使用者 `bob` | 執行 `abf-platform --json user passwd bob --temporary` | 結束碼 1；stdout 空；三段式錯誤；沒有產生也沒有顯示臨時密碼 | 自動：同上 |
| TC-031 | 作法 7 | 例外 | abf_launch 註冊進來的每個指令（launch／cancel／resume／relaunch／fetch-records 等，清單由 `test_cli_usage_doc._launch_commands()` 取得） | 各加 `--json` 執行 | 結束碼 1；stdout 空；stderr 為三段式錯誤：what＝「這個指令還不支援 --json」，why＝「它的輸出由 abf_launch 自己的出口產生，尚未接上 JSON 外殼」，next＝「不加 --json 執行，或等後續版本」 | 自動：`test_json_refused_for_launch_registered_commands` |
| TC-032 | 計畫「不做」第 2 條（launch 類指令的 `--json` 支援） | 不在範圍 | 同 TC-031；先記下任務表的列數 | 同 TC-031 | 沒有印出半個 JSON 物件；沒有任何站台或平台工作被排（任務表列數不變）；即「只拒絕並說清楚」，沒有悄悄做出 JSON 支援 | 自動：同上 |

## User Story 4 — `--debug` 只在 stderr 多印診斷，不動 stdout（優先度 P2）

維護者原話（裁決三）：「`--debug` only adds stderr diagnostics and never changes stdout」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 裁決三；作法 8 | 功能 | 既有指令清單中每個葉節點的成功情境 | 同一指令分別加／不加 `--debug` | 結束碼與 stdout 逐字相同 | 自動：`test_debug_never_changes_stdout_or_exit` |
| TC-034 | 裁決三 | 功能 | 既有指令清單中每個葉節點的失敗情境 | 同一指令分別加／不加 `--debug` | 結束碼與 stdout 逐字相同 | 自動：同上 |
| TC-035 | 作法 8 | 功能 | 同 TC-033 | 加 `--debug` 執行；再不加執行 | 加 `--debug` 時 stderr 至少一行以 `debug: ` 開頭；不加時 stderr 沒有任何 `debug:` 開頭的行 | 自動：同上 |
| TC-036 | 作法 8（每行以 `debug: ` 開頭） | 功能 | 平常 stderr 為空的成功情境 | 加 `--debug` 執行 | stderr 的每一行都以 `debug: ` 開頭，沒有其他東西 | 自動：同上 |
| TC-037 | 作法 8（指令路徑、選項名稱不含值） | 功能 | 一個帶選項的指令，例如 `ce create` 或 `pat new` 加上有值的選項 | 加 `--debug` 執行 | debug 行含指令路徑與「給了哪些選項」的名稱（例如 `--name`），**不含**這些選項的值 | 自動：`test_debug_lines_leak_nothing` |
| TC-038 | 作法 8（結束碼、耗時） | 功能 | 同 TC-033 | 加 `--debug` 執行 | debug 行含結束碼與以毫秒計的耗時 | 自動：`test_debug_never_changes_stdout_or_exit` |
| TC-039 | 作法 8（不得洩漏） | 例外 | 帶 `--token`／密碼類選項值的情境（`user add … --password` 若存在；否則用 `pat new` 與 `ce create` 的值），家目錄在暫存資料夾 | 加 `--debug` 執行 | stderr 不含任何選項的值、不含暫存家目錄路徑、不含環境變數的值、不含 `Traceback`；選項只以名稱出現 | 自動：`test_debug_lines_leak_nothing` |
| TC-040 | 作法 8（未預期例外的堆疊） | 功能 | 測試讓某個指令丟出未預期的例外 | 加 `--debug` 執行 | stderr 出現該例外的堆疊；stdout 與結束碼和不加 `--debug` 時相同 | 自動：`test_flags_*` 或同檔新增的未預期例外測試（註明 TC-040） |
| TC-041 | 作法 8（不加 `--debug` 時不變） | 例外 | 同 TC-040 | 不加 `--debug` 執行 | 未預期例外的表現（stderr、結束碼）與 v3 相同，沒有新增 `debug:` 行 | 自動：同上 |
| TC-042 | 作法 7 括號（`--debug` 對 launch 類指令照常可用） | 功能 | 一個 abf_launch 註冊的指令，以及該測試用的假目錄 | 分別加／不加 `--debug` 執行 | 結束碼與 stdout 逐字相同；加了之後 stderr 有 `debug: ` 行 | 自動：`test_debug_never_changes_stdout_or_exit`（含 launch 類指令） |

## User Story 5 — 不加旗標時一切逐字不變；旗標只掛在根、寫在指令前（優先度 P1）

維護者原話（裁決四）：「existing command outputs unchanged without the flags (tests must pin this)」；任務簡述：「errors look like 'rejected: English（中文）'」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-043 | 裁決四；作法 5 | 功能 | 既有指令清單每個葉節點的成功／失敗／參數錯誤情境 | 不加任何旗標執行 | stdout、stderr、結束碼三項都與 v3 逐字相同；由 `test_cli_contract.py`、`test_cli_snapshots.py`、`test_cli.py`、`test_dataset_cli.py` 等整組維持全綠證明 | 自動：`test_without_flags_nothing_changes`（以既有測試檔全綠為準） |
| TC-044 | 裁決四；任務簡述 | 功能 | 七種執行期失敗，加上 `ce show`、`dataset show` 找不到的情境 | 不加旗標執行 | 七種的 stderr 逐字等於 v3，仍以 `rejected:` 開頭且括號後有中文；`ce show`／`dataset show` 找不到的句子逐字等於 v3，且不以 `rejected:` 開頭 | 自動：`test_plain_mode_err_text_unchanged` |
| TC-045 | 任務簡述（unified what/why/next）；作法 5 | 功能 | `platform/abf_platform/cli.py` | 用程式語法樹掃描所有 `_err(...)` 呼叫 | 每一個呼叫都帶 `why=` 與 `next=`，且不是空字面（漏一處就紅） | 自動：`test_every_err_call_has_why_and_next` |
| TC-046 | 作法 1；範圍（`cli_help_top.txt`） | 功能 | 無 | 執行 `abf-platform --help` | 根選項多出 `--version`、`--json`、`--debug` 三項說明；`cli_help_top.txt` 與舊版相比只多這三行，其他不變 | 自動：`test_cli_snapshots.py`（更新後的 `cli_help_top.txt`）；驗收者另逐行讀 diff |
| TC-047 | 作法 1(c) | 功能 | 無 | 執行快照測試 | `cli_tree`、`cli_help_user_add`、`cli_help_ce_create`、`cli_json_ce_show`、`cli_json_dataset_show` 快照檔零改動且測試綠 | 自動：`test_cli_snapshots.py` |
| TC-048 | 允許的斷言（`test_documented_gaps`） | 功能 | 無 | 執行 `test_cli_contract.py::test_documented_gaps` | 斷言改為：根 parser 有 `--version`、`--json`、`--debug`；葉節點沒有 `--json`／`--debug`；`dataset register`／`dataset show` 自己的 `--version`（資料集版本）仍在。其餘斷言只增不減 | 自動：`test_cli_contract.py::test_documented_gaps` |
| TC-049 | 作法 1(a) | 功能 | 已登記的資料集 | 執行 `abf-platform dataset show <名稱> --version`（旗標寫在葉節點後） | 仍是資料集版本的意思，行為與 v3 相同 | 自動：`test_dataset_cli.py` 維持綠 |
| TC-050 | 作法 9 | 功能 | 無 | 讀 `cli.__doc__` | 「abf-platform: a \| b \| …」那一行格式不變，`test_cli_usage_doc.py` 綠 | 自動：`test_cli_usage_doc.py` |
| TC-051 | 完成標準（文件） | 功能 | 無 | 讀 `docs/PLATFORM.md` 命令列段 | 寫有 `--version`、`--json`、`--debug` 三個旗標的說明、「旗標要放在指令前面」，以及錯誤的 what／why／next 三段 | 自動：`test_cli_flags.py` 內一條讀檔檢查（註明 TC-051）；驗收者另讀文件看是否白話 |
| TC-052 | 「允許的斷言」shell 測試 | 功能 | 無 | 執行 `tests/install_doc_test.sh`、`migration_doc_test.sh`、`operations_doc_test.sh`、`hosted_deploy_test.sh`、`jev_test.sh` | 全綠；`jev_test.sh` 仍認 plugin.json 版本為 `3.0.0-dev`（本案只讀不改） | 自動：上列 shell 測試 |
| TC-053 | 範圍（只准改的檔案） | 功能 | 無 | 看 `git diff --stat` | 既有測試與快照除 `test_documented_gaps` 與 `cli_help_top.txt` 外零改動；`RUNTIME` 七案、`xfail(strict=True)` 案、`test_not_found_shows_use_their_own_wording`、`test_agent_token_revoke_id.py`、`test_owner_tokens.py:19`、`test_temp_password.py:633` 的斷言逐字未動 | 自動：整套既有測試維持綠；驗收者另以 `git diff --stat` 核對 |
| TC-054 | 作法 1（旗標不接受在指令之後） | 例外 | 無 | 執行 `abf-platform ce list --json` | 結束碼 2（葉節點不認 `--json`） | 自動：`test_flags_not_accepted_after_the_command` |
| TC-055 | 作法 1(b) | 例外 | 無 | 執行 `abf-platform agent-token list --json` | 結束碼 2，與既有 `test_agent_token_revoke_id.py:344` 一致、該測試不改且綠 | 自動：`test_agent_token_revoke_id.py` |
| TC-056 | 計畫「不做」第 3 條（不加旗標的錯誤不改三段式）；裁決五 | 不在範圍 | 任一執行期失敗情境 | 不加旗標執行 | stderr 仍只是那一句 `rejected: …`（或 `ce show`／`dataset show` 的專用找不到句），沒有多出 why／next 的段落或標籤 | 自動：`test_plain_mode_err_text_unchanged` |
| TC-057 | 計畫「不做」第 4、5 條（`abf-station`、不改版本來源檔） | 不在範圍 | 無 | 看 diff 與既有測試 | `platform/abf_station/`、`platform/abf_launch/cli.py`、`.claude-plugin/plugin.json`、`platform/pyproject.toml` 零改動；`abf_platform.__version__` 仍是 `0.1.0`；`abf-station --version` 仍印它原本印的（`__version__`） | 自動：`jev_test.sh`、既有 abf_station 測試維持綠；驗收者另以 `git diff --stat` 核對 |
| TC-058 | 計畫「不做」第 5 條（不為 pip 安裝版另找版本來源）；作法 2 | 不在範圍 | `__version__` 與 pyproject 仍是 `0.1.0`，但 plugin.json 讀不到 | 執行 `abf-platform --version` | 仍是失敗（結束碼 1），不會悄悄改印 `0.1.0` 或任何備援版本 | 自動：`test_version_missing_plugin_json_is_a_three_part_error` |
| TC-059 | 計畫「不做」第 4 條（`NO_COLOR`、shell 補全） | 不在範圍 | 無 | 執行 `abf-platform --help`，並跑 `test_no_color` | 根選項相較舊版只多 `--version`、`--json`、`--debug` 三個，沒有補全或顏色相關新選項；`test_no_color` 不改且綠 | 自動：`test_cli_snapshots.py`、`test_cli_contract.py::test_no_color` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 5.0.0／Safety Net 憑證規則：網頁密碼只能在真正的終端機設定與顯示 | 例外 | 沒有終端機（測試環境） | 分別執行 `--json user passwd bob`、`--json user passwd bob --temporary`，以及不加旗標的 `user passwd bob` | 前兩者被拒絕，任何 JSON 輸出裡都沒有密碼或臨時密碼；不加旗標的拒絕句子與 v3 相同（`test_user_passwd_refuses_without_a_terminal`、`test_temp_password.py:633` 不改且綠） | 自動：`test_json_refused_for_long_running_and_secret_terminal_commands` 與既有測試 |
| TC-061 | Safety Net 憑證規則：密鑰不得多一個暴露面 | 例外 | `pat new` 可執行 | 執行 `abf-platform --debug --json pat new …` | 產生的 token 只出現在 stdout 物件的 `output` 中（與不加旗標時 stdout 同樣位置）；stderr 完全沒有該 token 的任何片段 | 自動：`test_debug_lines_leak_nothing` |
| TC-062 | 憲法 Principle I.2／5.0.0：launch、cancel、resume、relaunch 要有人親自說 yes，不得被腳本化通道繞過 | 例外 | 同 TC-031 | 各加 `--json` 執行；再不加旗標執行 | 加 `--json` 時被拒絕，沒有排任何工作；不加旗標時仍照原本的詢問流程（`test_launch_cli.py` 不改且綠） | 自動：`test_json_refused_for_launch_registered_commands`、`test_launch_cli.py` |
| TC-063 | 計畫作法 9：`adopt_orphans`／`ADOPTING` 行為不變 | 功能 | 無 | 執行 `test_owner_guard.py`（把 `abf_platform/cli.py` 列為受檢檔）、`test_pat.py`（以語法樹讀 `cmd_mcp`）、`test_actions_layer.py`、`test_user_welcome.py` | 全綠，不需改動這些測試 | 自動：上列既有測試 |
