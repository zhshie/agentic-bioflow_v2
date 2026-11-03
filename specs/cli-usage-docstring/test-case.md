# 測試案例：abf-platform 說明首行補齊所有指令（cli-usage-docstring）

**規格**：`specs/cli-usage-docstring/plan.md`（此件沒有獨立 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「說明首行」＝`platform/abf_platform/cli.py` 第 2 行的那段字串（程式裡叫 `__doc__`，也是執行 `abf-platform --help` 時最上面那段描述）。「群組段落」＝說明用 ` | ` 切開後的每一段，例如 `dataset register|list|show`。

比對規則（計畫裁決 5）：把說明去掉開頭 `abf-platform:` 後用 ` | ` 切成段；每段第一個字是群組名；其餘部分取第一個空白前的 `a|b|c` 清單、去掉 `[...]` 方括號內容後用 `|` 切成名稱集合（例：`user add|cloud-cap|passwd [--temporary]|welcome` → {add, cloud-cap, passwd, welcome}）。

本件沒有維護者的「我打這句、它應該做這件事」式範例；唯一的維護者原話是派工指示「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」與「若發現需要改動指令行為，停下回報 BLOCKED」，對應 User Story 2 與「不在範圍」。

## User Story 1 — 說明首行列出每一個指令，且以後漏列會被測試抓到（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「目標」；失敗先行測試 1（`test_every_top_level_command_is_named_in_the_doc`） | 功能 | 取 `cli.build_parser()` 登記的全部頂層指令（目前共 12 個：serve、web、token、agent-token、user、pat、oauth、ce、mcp、rebuild、runs、dataset） | 逐一檢查說明首行是否有以該指令名開頭的一段 | 12 個全都有自己的一段；改字前因缺 `oauth`、`dataset` 而失敗，改字後通過 | 自動：`platform/tests/test_cli_usage_doc.py::test_every_top_level_command_is_named_in_the_doc` |
| TC-002 | 計畫「目標」；失敗先行測試 2（`test_every_nested_command_is_named_in_the_doc`）；裁決 5 | 功能 | 取 parser 裡每個有子指令的群組（ce 除外）的全部第二層名稱：token{new}、agent-token{new,revoke}、user{add,cloud-cap,welcome,passwd}、pat{new,list,revoke}、oauth{revoke}、runs{assign,offer-cleanup}、dataset{register,list,show}，共 16 個 | 逐一檢查該名稱是否在「自己群組那一段」的名稱集合裡 | 16 個全都在自己群組的段落裡；改字前因缺 `offer-cleanup`、`register`、`show`（以及 `oauth revoke`）而失敗，改字後通過 | 自動：`platform/tests/test_cli_usage_doc.py::test_every_nested_command_is_named_in_the_doc` |
| TC-003 | 裁決 5（`dataset list` 漏寫不會因 `pat list` 而誤綠） | 例外 | 在驗收者的暫存副本裡，把說明的 dataset 段落刪掉 `list`（`pat` 段仍有 `list`） | 執行 TC-002 的測試 | 測試失敗，並指出 dataset 缺 list；不會因為別的群組也有 `list` 而通過。驗收後副本丟棄，不留在分支上 | 手動：閱卷者變異檢查（刪字後單檔重跑 TC-002，不動分支） |
| TC-004 | 裁決 4（`ce ...` 原樣保留） | 功能 | 改完後的說明首行 | 讀說明首行裡 ce 的那一段 | 仍是原樣的 `ce ...`，沒有被展開、改寫或刪除 | 手動：閱卷者讀 `platform/abf_platform/cli.py` 第 2 行 |
| TC-005 | 裁決 4（第二層測試明確排除 ce，並寫一行理由註解） | 功能 | 新測試檔 `platform/tests/test_cli_usage_doc.py` | 讀第二層測試裡排除 ce 的地方 | 明確排除 `ce`，旁邊有一行註解說明理由（說明裡的 `ce ...` 是刻意要使用者看 `ce --help`） | 手動：閱卷者讀測試檔 |
| TC-006 | 失敗先行測試 3（`test_doc_has_no_dangling_count`） | 功能 | 說明首行 | 檢查說明是否含 `four commands` | 不含；改字前因含該句而失敗，改字後通過 | 自動：`platform/tests/test_cli_usage_doc.py::test_doc_has_no_dangling_count` |
| TC-007 | 計畫「決定」、裁決 1（刪句、不放新數量詞） | 功能 | 改完後的說明首行 | 讀整行 | 「the four commands of the hand-off record (see their own --help)」整句已不在；整行沒有新增任何數量詞（如 four、five、三個、四個之類的個數說法） | 手動：閱卷者讀 `platform/abf_platform/cli.py` 第 2 行 |
| TC-008 | 計畫「決定」、裁決 5（新寫法格式） | 功能 | 改完後的說明首行 | 讀 oauth、dataset、runs 三段 | 寫成符合比對規則的格式：`oauth revoke USER`（參數名依 cli.py:783–784 的實際參數 `user`）、`dataset register\|list\|show`、`runs assign\|offer-cleanup`；原本的 `runs assign RUN --user NAME` 帶參數寫法已改成 `runs assign\|offer-cleanup` | 手動：閱卷者讀 `platform/abf_platform/cli.py` 第 2 行 |
| TC-009 | 失敗先行測試「對照組」 | 功能 | 說明首行 | 檢查 `serve`、`web`、`token`、`mcp`、`rebuild` 是否仍在說明裡 | 五個都還在；這則測試改字前就綠、全程不得變紅 | 自動：`platform/tests/test_cli_usage_doc.py`（對照組測試，改字前後都綠） |
| TC-010 | 計畫「決定」第 2 點、裁決 2（`--help` 開頭變長是唯一可見差異） | 功能 | 已改好的分支，不連網、不開資料庫 | 閱卷者執行 `abf-platform --help`（只印說明，不執行任何子指令） | 正常結束；最上面的描述就是新的說明首行，含 oauth、dataset、runs 的 offer-cleanup；其餘（子指令清單、各自的 help 文字）與 base 逐字相同 | 手動：閱卷者在兩個分支各跑一次並比對輸出 |

## User Story 2 — 除了說明首行，其他一概不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫「手動檢查」；範圍「只改第 2 行」 | 功能 | 分支與 base（`origin/v3`）可比 | 執行 `git diff -U0 origin/v3 -- platform/abf_platform/cli.py` | 只有第 2 行一處改動；第 1 行註解沒動 | 手動：閱卷者重跑計畫所列指令（裁決 6） |
| TC-012 | 計畫「手動檢查」；維護者原話「不改使用者看得到的行為」 | 功能 | 兩個分支的 `cli.py` | 兩邊各做 `ast.parse` 後比較 | 只有那一個字串常數（模組說明）不同，其他節點全部相等 | 手動：閱卷者重跑計畫所列指令（裁決 6），AST 比對輸出貼進 ledger |
| TC-013 | 計畫「失敗先行測試」對照組；「既有測試不改」 | 功能 | 既有 `platform/tests/test_cli.py`、`platform/tests/test_dataset_cli.py` | 比對 base 與 HEAD 這兩檔，並跑這兩檔 | 兩檔與 base 一字不差（沒有刪斷言、沒有放寬）；兩檔全綠 | 自動：`ABF_PYTEST_TARGETS="tests/test_cli.py tests/test_dataset_cli.py" bash tests/platform_test.sh`（在 `platform/` 下） |
| TC-014 | 計畫「完成標準」第 2 點 | 功能 | 完成標記 `GREEN <HEAD sha>` | 全套 `platform/tests` 已由執行者在 HEAD 跑過（閱卷者不重跑，只核對完成標記） | 全綠；已知環境紅（dev-plans README「通例：已知環境紅」）不算 | 自動：`tests/run_all.sh`（WSL）；閱卷者核對完成標記 |
| TC-015 | 計畫「完成標準」第 3 點；範圍檔案清單 | 功能 | 分支 | 執行 `git diff --stat origin/v3` | 只含 `platform/abf_platform/cli.py`（一行）與新檔 `platform/tests/test_cli_usage_doc.py`，沒有第三個檔 | 手動：閱卷者重跑指令 |
| TC-016 | 範圍：新測試檔檔頭規定 | 功能 | 新檔 `platform/tests/test_cli_usage_doc.py` | 看檔案前 40 行 | 有一行 `# Nothing existing: …`，冒號後至少 15 個字，內容說明既有 test_cli.py、test_dataset_cli.py 驗各指令的行為、沒有任何測試檢查模組說明有沒有列出 build_parser 的子指令 | 手動：閱卷者讀測試檔檔頭 |
| TC-017 | 計畫「失敗先行測試」：改字前先跑一次確認紅，紅輸出貼進 ledger | 功能 | ledger（執行紀錄） | 讀 ledger | 有改字前的紅輸出，且紅的是 TC-001、TC-002、TC-006 三則；TC-009 對照組在同一次輸出裡是綠 | 手動：閱卷者讀 ledger |
| TC-018 | 計畫「失敗先行測試」：不連網、不開資料庫、不執行任何子指令 | 例外 | 新測試檔 | 讀測試檔 | 只用 `cli.build_parser()` 與 `cli.__doc__`；沒有網路、資料庫、subprocess、也沒有呼叫任何子指令的 `func` | 手動：閱卷者讀測試檔 |

## User Story 3 — 這次明講不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 計畫「不做」第 1 點：不改任何子指令的行為、旗標、`help=` 文字 | 不在範圍 | 兩個分支 | 以 TC-012 的 AST 比對，並比對 `abf-platform runs --help`、`abf-platform dataset --help`、`abf-platform oauth --help` 的輸出 | 所有 `add_parser`／`add_argument`／`help=`／函式都沒變；三個子指令的 `--help` 輸出與 base 逐字相同 | 手動：閱卷者兩分支各跑並比對 |
| TC-020 | 計畫「不做」第 2 點：不把說明改成自動從 parser 生成 | 不在範圍 | 改完的 `cli.py` | 看模組說明的寫法（AST） | 仍是寫死的字串常數，不是由 `build_parser()` 或任何函式組出來的 | 手動：閱卷者看 AST 比對結果與 cli.py 第 2 行 |
| TC-021 | 計畫「不做」第 3 點：不需要 migration | 不在範圍 | 分支 | 看 `git diff --stat origin/v3` | 沒有任何 migration、資料表結構或資料內容的變動 | 手動：閱卷者看 diff 統計 |
| TC-022 | 範圍「不准碰」清單與「不准改」清單 | 不在範圍 | 分支 | 看 `git diff --name-only origin/v3` | 不含 `compose.py`、`actions/pipelines.py`、`actions/datasets.py`、`abf_launch/build.py`、`abf_station/rules.py`、`records.py`、`web.py`、`web_upload.py`、web 模板、`confirm.py`、`compute_envs.py`、`jobs.py`、`store.py`、k8s 相關檔、`docs/`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`；`specs/cli-usage-docstring/` 下的 plan 與本檔在實作期間沒被改 | 手動：閱卷者看檔名清單 |

## 憲法與安全網

計畫「決定」第 3 點：新增文字要避開站台掃描禁字與 constitution 的 grep 掃描。說明首行是被這些掃描讀到的程式文字，所以證明兩條掃描仍過。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 第 2 條（Nextflow 的紀錄是事實來源，不保存第二份執行狀態；計畫指名的 `no_second_run_state_test.sh`） | 功能 | 改好的分支 | 執行該掃描測試 | 通過；新增的說明文字沒有觸發任何禁用字 | 自動：`bash tests/no_second_run_state_test.sh` |
| TC-024 | 第 4 條（命令層與站台無關，站台詞彙掃描） | 功能 | 改好的分支 | 執行該掃描測試 | 通過；新增的說明文字沒有把站台專用詞彙帶進命令層 | 自動：`bash tests/command_layer_is_site_neutral.sh` |

## 專長守則（backend）檢查

計畫裁決 3 已定：本件只改說明字串，守則中下列項目不適用，理由如下，不硬湊 TC。

- 對等性 TC（使用者動作清單 vs 動作層函式清單）：不適用。本件不新增、不改任何動作，說明首行對 parser 的對照已由 TC-001／TC-002 涵蓋。
- 跨使用者 TC（讀與寫各一）：不適用。沒有任何紀錄的讀寫路徑被改，TC-012 證明程式其餘部分不變。
- 確認管道 TC：不適用。沒有新增或修改寫入動作，TC-012／TC-019 證明。
- 錯誤訊息與日誌 TC（含密鑰不外洩）：不適用。沒有新增錯誤訊息或日誌；新測試不印任何憑證（TC-018）。
- migration TC：不適用，由 TC-021 確認沒有資料結構變動。
