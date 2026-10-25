# 測試案例：constitution_scope_test.sh 時好時壞（constitution-scope-flake）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務沒有 spec.md，只有 plan.md；「對應需求」欄引用 plan 的章節。
所有預期結果都來自 plan 寫明的內容，沒有另外發明行為。
-->

**規格**：`specs/constitution-scope-flake/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，做到了。
- **例外**：出錯、重現不了、缺東西時，系統怎麼反應。
- **不在範圍**：計畫明講不做或禁止的事；確認它真的沒做。

名詞：**ledger**＝`specs/constitution-scope-flake/ledger.md`，執行者記錄實測過程與結果的檔案。**base**＝`origin/v3`。**模擬 CI 條件**＝計畫作法 1 列的四件事：淺層 clone（`git clone --depth 1`）、沒有 `main` 這個分支、`TMPDIR`（暫存資料夾）換成另一個資料夾、同時跑兩份。

## User Story 1 — 先重現、找出原因（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；失敗先行測試 | 功能 | 還沒改 `tests/constitution_scope_test.sh`（base 版本） | 在 WSL 連跑 50 次：`for i in $(seq 50); do bash tests/constitution_scope_test.sh >/tmp/cs.$i 2>&1 \|\| echo FAIL $i; done` | ledger 貼出這個指令、跑的次數 50、紅了幾次、紅的是第幾次 | 手動：閱卷者讀 ledger 並對照指令 |
| TC-002 | 作法 1 | 功能 | 同上 | 另外在四種模擬 CI 條件下各跑：淺層 clone、沒有 `main` 分支、`TMPDIR` 換成另一個資料夾、同時跑兩份 | ledger 對這四種條件各有一行：做法與結果（紅或綠、跑幾次）；「同時跑兩份」要寫明是同一個資料夾還是兩個副本 | 手動：閱卷者讀 ledger |
| TC-003 | 作法 1、2 | 功能 | TC-001、TC-002 中至少一次紅 | 查看紅的那次輸出 | ledger 寫明：哪一種條件會紅、紅在哪一條（案例名稱，也就是輸出裡 `FAIL` 那一行）、根因是什麼 | 手動：閱卷者讀 ledger，並抽一次紅的輸出核對 |
| TC-004 | 失敗先行測試（重現不了的分支） | 例外 | 50 次加四種模擬條件都沒有紅 | 照計畫處理 | ledger 寫明試過的條件與結果；仍然完成 TC-011 的「失敗時印出哪一條」；執行者回報 BLOCKED 讓 developer-agent 決定，而不是宣稱已修好 | 手動：閱卷者讀 ledger 與執行者回報 |

## User Story 2 — 修好，讓每次結果一樣（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 完成標準 1 | 功能 | 修好之後 | 同 TC-001 的指令再連跑 50 次 | ledger 貼出結果：50 次 0 紅；閱卷者自己再跑該檔一次也是 `all passed` | 手動：閱卷者讀 ledger，並自己跑 `bash tests/constitution_scope_test.sh` 一次 |
| TC-006 | 完成標準 1；作法 1 | 功能 | 修好之後 | 在 TC-002 的四種模擬 CI 條件下各跑，每種至少跑到 ledger 寫明的次數 | ledger 對四種條件各貼出結果：全部 0 紅 | 手動：閱卷者讀 ledger |
| TC-007 | 完成標準 2 | 功能 | 修好之後 | 在一般環境跑 `bash tests/constitution_scope_test.sh` | 最後一行是 `all passed`，結束碼 0 | 自動：`tests/constitution_scope_test.sh` |
| TC-008 | 完成標準 2（既有案例一條不少） | 功能 | base 版本與修好版本各跑一次，都是綠 | 比對兩次輸出裡以 `ok` 結尾的案例名稱 | base 印出的每一條案例名稱，修好版本都還印出，且都是 `ok`；案例總數不少於 base（修好版可以多，不可以少） | 手動：閱卷者在 base 與 HEAD 各跑一次並比對名稱清單，貼進驗收報告 |
| TC-009 | 完成標準 2（斷言不放寬）；作法 3 | 功能 | 看 `git diff origin/v3...HEAD -- tests/constitution_scope_test.sh` | 逐條看被改動的檢查 | 沒有任何既有斷言被刪、被改寬、被改成只要存在就算過，或預期值被改成配合新輸出；被動到的斷言各有 ledger 說明 | 手動：閱卷者讀差異 |
| TC-010 | 作法 3 | 功能 | TC-003 已找到根因 | 對照 ledger 寫的根因與程式差異 | 程式改動直接對準 ledger 寫的根因（例如固定 clone 來源、檢查 clone 完成、不依賴共用暫存、不依賴時間）；不是只在外面包一層 | 手動：閱卷者對照 ledger 與差異 |

## User Story 3 — 下次再紅，直接看到是哪一條（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 作法 4 | 功能 | 造一個必然失敗的情境（例如在副本裡改動 Safety Net 區段，讓指紋那一條失敗） | 跑測試，只看 stderr（標準錯誤輸出） | stderr 裡出現失敗那一條的案例名稱與原因，所以只看輸出尾巴的人也能知道是哪一條 | 自動：`tests/constitution_scope_test.sh`（檔內案例，或另一支新增的 `tests/` 檔） |
| TC-012 | 作法 4（「也寫到 stderr」）；完成標準 2 | 功能 | 同 TC-011 | 跑測試，看 stdout（標準輸出） | 失敗那一行仍照原格式出現在 stdout（`名稱 ... FAIL: 原因`），所以檔內用 `grep 'FAIL'` 判斷內層結果的案例照常運作 | 自動：`tests/constitution_scope_test.sh` |
| TC-013 | 作法 4 | 功能 | 全部案例都過 | 跑測試，看 stderr | stderr 裡沒有任何由「失敗印出」這個新功能產生的行，不會在全綠時誤報 | 自動：`tests/constitution_scope_test.sh` |

## User Story 4 — 不在範圍／禁止的事（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 維護者原話（run_all 訊息：「Fix the test, or add one line per file to tests/quarantine.txt」，本任務選 Fix the test）；不做 1 | 不在範圍 | 看 `git diff origin/v3...HEAD -- tests/quarantine.txt` | 檢查差異 | 差異為空；`tests/quarantine.txt` 裡沒有 `constitution_scope_test.sh` | 手動：閱卷者讀差異與檔案 |
| TC-015 | 不做 1（不改 run_all 的 FLAKY 判定）；範圍：檔案 | 不在範圍 | 看 `git diff origin/v3...HEAD -- tests/run_all.sh` | 檢查差異 | 若沒改，差異為空；若有改，ledger 寫明理由（根因在輸出截斷或共用暫存），且 `--retry-failed-once` 與 FLAKY 判定的行為一行都沒變 | 手動：閱卷者讀差異與 ledger |
| TC-016 | 不做 2 | 不在範圍 | 看 `git diff origin/v3...HEAD` | 檢查 `.specify/memory/constitution.md` 與 `PINNED_SN_SHA256=` 那一行 | 憲法檔差異為空；`PINNED_SN_SHA256` 的值與 base 完全相同 | 手動：閱卷者讀差異 |
| TC-017 | 作法 3（禁止加重試迴圈掩蓋、跳過案例） | 不在範圍 | 看測試檔差異 | 檢查有沒有為了讓它變綠而重跑失敗的檢查、跳過或移除案例 | 沒有「失敗就再跑一次直到過」的迴圈，沒有被跳過或移除的案例；允許「等到 clone 真的完成」這種檢查實際條件的等待 | 手動：閱卷者讀差異 |
| TC-018 | 範圍：檔案 | 不在範圍 | 看 `git diff --name-only origin/v3...HEAD` | 列出改動的檔案 | 只有 `tests/constitution_scope_test.sh`、`specs/constitution-scope-flake/ledger.md`，以及（有 ledger 理由時才可以）`tests/run_all.sh`；其餘只准是計畫與合約文件本身 | 手動：閱卷者讀清單 |

## 憲法與安全網

<!-- 此測試檔是憲法 Safety Net 區段所列的 Check 之一（「the three Check files」）。本任務不改規則，但改的是守住規則的檢查，所以要證明檢查沒變弱。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | Safety Net：Check 檔名 `tests/in_use_test.sh`、`tests/in_use_speed_test.sh`、`tests/constitution_scope_test.sh` | 功能 | 修好之後 | 跑 `bash tests/constitution_checks_exist_test.sh`；確認 `tests/constitution_scope_test.sh` 檔名未變 | 通過；三個 Check 檔仍存在、名稱沒變 | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-020 | Safety Net 以指紋鎖住（TC-040..TC-044；issue #71：沒有 `main` 分支與有 `main` 分支都要擋得住） | 功能 | 修好之後 | 在淺層副本裡改動 Safety Net 區段，分別在沒有 `main` 與有 `main` 的副本跑 | 兩種都失敗在指紋那一條，且印出目前的指紋；改動後同步更新指紋則通過；沒有任何一種被改成通過 | 自動：`tests/constitution_scope_test.sh`（檔內既有案例 TC-002、TC-003、TC-004、TC-006、TC-007、TC-008 仍在且為 `ok`） |
| TC-021 | 維護者原話「全綠才准停」；完成標準 3 | 功能 | 修好之後、工作樹乾淨 | 在 WSL 跑全套 `tests/run_all.sh`（CLAUDE.md 寫的指令） | 全套綠，完成記號是 `GREEN <HEAD sha>` 且與 HEAD 相符 | 自動：`tests/run_all.sh` |

## 專長守則（backend）

<!-- 本任務只改一支測試腳本，沒有網頁／API／聊天動作、沒有寫入動作、沒有使用者紀錄。動作層對等性、跨使用者、確認管道三組 TC 不適用，已在總覽註明。以下只對應確實有關的兩條。 -->

| 編號 | 專長守則條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 密鑰、token、密碼不得出現在日誌或任何回應中；錯誤訊息要說明發生什麼 | 功能 | TC-011 新增的 stderr 輸出 | 檢查新增的輸出內容與測試時的失敗輸出 | 只含案例名稱、原因與指紋；不含任何密鑰、token、密碼；原因說得出發生了什麼 | 手動：閱卷者讀差異與一次失敗輸出 |
| TC-023 | 資料結構或內容變動必須附 migration，或明寫不需要 | 功能 | 看 `git diff --name-only origin/v3...HEAD` | 檢查有沒有資料結構或資料檔改動 | 沒有；ledger 或總覽寫明「不需要 migration」及理由 | 手動：閱卷者讀清單與 ledger |
