# 測試案例：CI 失敗只重跑一次＋隔離名單（ci-quarantine）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
-->

**規格**：`specs/ci-quarantine/plan.md`（本任務沒有獨立的 spec.md，計畫即規格；「裁決二」優先於計畫其他段落）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白拒絕。

## 先看這段：測試怎麼擺（所有「自動」案例共用）

白話：「測試跑法」是一支叫 `run_all.sh` 的程式，它把 `tests/` 底下每個測試檔跑一遍。這次的改動讓它可以「失敗的檔再跑一次」，並且有一份「隔離名單」`tests/quarantine.txt`，登記「已知會偶爾失敗、但已經開 issue 在處理」的測試檔。

- **沙盒**：測試在臨時資料夾裡複製一份 `run_all.sh` 與 `scripts/utils/portable.sh`，裡面只放小型假測試檔，**絕不跑真的整套**（會無限遞迴）。
- **四種假測試檔**：`ok_test.sh`（永遠通過）；`flaky_test.sh`（第一次失敗、第二次通過，每次執行都在「計數檔」加一）；`bad_test.sh`（永遠失敗，也計數，第二次輸出含 `second-run-marker`）；`slow_test.sh`（第一次睡 3 秒、搭配 `--timeout 1` 會逾時，第二次立刻通過）。**計數檔**＝記錄某個假檔被執行了幾次，用來證明「只重跑一次」或「根本沒跑」。
- **固定日期**：一律用環境變數 `RUN_ALL_TODAY=2026-10-24` 當「今天」（TC-055 例外，專門驗系統日期）。
- **假 uname**：PATH 前面放一個回答 `Linux` 的假 `uname`，且所有執行都帶 `--allow-missing-tools`，讓測試在 Git Bash 也能跑。
- **名單範例（有效）**：`tests/flaky_test.sh #12 2026-11-01`（三欄：檔案、issue、到期日）。
- 驗證方式「自動」＝寫在 `tests/run_all_retry_test.sh`（或計畫指定的既有測試）並在註解標 TC 編號；「手動」＝閱卷者看 diff、ledger 或 PR 描述（`docs/TESTING.md` 此任務不准改，故不引用）。

## User Story 1 — 不帶旗標時，行為與今天完全相同（優先度 P1）

維護者原話：「不帶旗標時行為與今天完全相同；本機 executor／verifier 的跑法仍然單次嚴格。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | R01；作法 1 | 功能 | 沙盒有兩個永遠通過的假檔；沒有任何旗標 | 執行 `run_all.sh` | 退出碼 0；輸出經正規化（刪 `logs:` 行、`root:` 行換成 `root: X`、各行尾 `<n>s` 去掉）後，逐字等於測試內嵌的期望文字：橫幅、兩行 `ok`、`2/2 passed`、`all green` | 自動：`tests/run_all_retry_test.sh` |
| TC-002 | R02；作法 1 | 例外 | 沙盒有 `ok_test.sh` 與 `bad_test.sh`；沒有旗標 | 執行 | 退出碼 1；摘要為 `1/2 passed, 1 failed`；`bad_test.sh` 計數檔＝1（只跑一次）；輸出**不含** `FLAKY`、**不含** `retry` | 自動 |
| TC-003 | R03；作法 1、6 | 例外 | 沙盒有 `flaky_test.sh`（第一次失敗）；沒有旗標 | 執行 | 退出碼 1；計數檔＝1（今天就是嚴格單次，不會自動重跑） | 自動 |
| TC-004 | R04；作法 3 | 功能 | 沙盒 `tests/quarantine.txt` 寫滿亂碼；全部假檔通過；沒有旗標 | 執行 | 退出碼 0；輸出沒有任何 `quarantine:` 訊息（名單根本沒被讀） | 自動 |
| TC-005 | R05；作法 1 | 功能 | 無 | 執行 `run_all.sh --help` | 用法文字同時含 `--retry-failed-once` 與 `--check-quarantine` | 自動 |
| TC-006 | 作法 5「環境問題 3 與用法錯誤 2 不變」 | 例外 | 無 | 執行 `run_all.sh --no-such-flag`（不帶、以及與 `--retry-failed-once` 同帶各一次） | 兩次都退出碼 2，並印 `unknown option` 與用法；不開跑任何測試 | 自動 |
| TC-007 | R37；作法 1 | 功能 | 真實 repo 的 `tests/run_all.sh` | 讀它的第 1–20 行 | 沒有 ≥10 的獨立整數；仍含 `run time` 字樣（避免既有 `run_all_count_test.sh` 的 TC-001／TC-002 變紅） | 自動 |
| TC-008 | R38 | 功能 | 真實 repo | 執行 `bash tests/run_all.sh --list` | 列出的檔數＝`ls tests/*.sh` 的檔數減 `run_all.sh`；清單含 `run_all_retry_test.sh`（新測試自己有被收進去） | 自動 |
| TC-009 | 作法 1「不帶旗標一字不動」；完成標準第 3 項 | 功能 | 同一個假測試目錄；base（`origin/v3`，`47701fb`）的 `run_all.sh` 與新的 `run_all.sh` | 兩邊各不帶旗標跑一次，輸出正規化後比對 | ledger 貼出兩份正規化輸出，`diff` 為空；且 `git diff` 顯示原第 170–226 行的字元沒被改（只有原第 227 行被包進 `if [ "$RETRY" = 0 ]` 的形式，`RETRY=0` 走原字串） | 手動：閱卷看 `specs/ci-quarantine/ledger.md` 與 `git diff` |
| TC-010 | 完成標準第 2 項；「既有測試零斷言需要修改」 | 功能 | 在 WSL 或 Linux，工作樹乾淨 | 跑全套 `bash tests/run_all.sh`（不帶旗標） | 結尾 `all green`；其中 `run_all_count_test.sh`、`run_all_test.sh` 原樣通過；ledger 貼出該輸出 | 自動：全套 `tests/run_all.sh`（WSL／Linux） |

## User Story 2 — 失敗的檔只重跑一次，重跑才綠的叫 FLAKY 並單獨列出（優先度 P1）

維護者原話：「失敗的那幾支只重跑一次（跟 CI 現行規則一樣）」；「重跑才綠的檔以 `FLAKY <名稱>` 單獨列出，絕不悄悄併進 passed；沒登記的 FLAKY 要失敗並說明『修掉或加一行隔離』」；「紅照常顯示」。

以下除特別說明外，都帶 `--retry-failed-once`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | R06；作法 5 | 功能 | 全部假檔通過；名單有效或無關 | 帶旗標執行 | 退出碼 0；輸出含 `all green`；不含 `FLAKY`；不含 `== retry`；每個假檔計數＝1 | 自動 |
| TC-012 | R07 | 功能 | 同 TC-011，但 `tests/quarantine.txt` 是空檔 | 帶旗標執行 | 結果同 TC-011 | 自動 |
| TC-013 | R08；作法 2「檔案不存在視同空名單」 | 功能 | 同 TC-011，沙盒沒有 `tests/quarantine.txt` | 帶旗標執行 | 結果同 TC-011 | 自動 |
| TC-014 | R09；作法 5 | 例外 | 沙盒有 `ok_test.sh`、`flaky_test.sh`；名單沒有登記 flaky | 帶旗標執行 | 退出碼 1；輸出有一行**行首**就是 `FLAKY flaky_test.sh`，後面接 `  NOT in tests/quarantine.txt` | 自動 |
| TC-015 | R09；作法 5 | 例外 | 同 TC-014 | 帶旗標執行，看錯誤輸出（stderr） | 含 `FLAKY not quarantined: flaky_test.sh`，並含 `Fix the test` 與 `tests/quarantine.txt`，以及格式提示 `tests/<name>.sh <issue> <YYYY-MM-DD> (at most 14 days out)` | 自動 |
| TC-016 | R10；作法 5 | 功能 | 名單有效登記 `tests/flaky_test.sh #12 2026-11-01` | 帶旗標執行 | 退出碼 0；仍有一行以 `FLAKY flaky_test.sh` 開頭，後接 `  quarantined #12 until 2026-11-01` | 自動 |
| TC-017 | R10；作法 5「刻意不含 all green」 | 功能 | 同 TC-016 | 帶旗標執行，看最後一行 | 含 `green after retry: 1`，且整個輸出**不含** `all green` | 自動 |
| TC-018 | R11；作法 4「不改第一輪計數」 | 功能 | 沙盒有 ok、ok、flaky（共 3 檔），flaky 已登記 | 帶旗標執行 | 摘要行仍是第一輪數字 `2/3 passed, 1 failed`（重跑才過的檔沒有被併進 passed） | 自動 |
| TC-019 | R12 | 功能 | 同 TC-018 | 帶旗標執行 | `FLAKY flaky_test.sh` 行出現在摘要行**之後**，且位於標題 `== FLAKY (failed the first run, passed the retry) ==` 底下 | 自動 |
| TC-020 | R13；維護者「紅照常顯示」 | 功能 | 同 TC-016（flaky 已登記） | 帶旗標執行 | 輸出仍含 `== output of what did not pass ==` 與 `--- flaky_test.sh ---`（第一輪的紅沒被吞掉） | 自動 |
| TC-021 | R14；作法 4 | 功能 | 沙盒有 `ok_test.sh`、`flaky_test.sh`，各自計數 | 帶旗標執行 | `ok_test.sh` 計數＝1（沒被重跑）；`flaky_test.sh` 計數＝2（重跑恰好一次） | 自動 |
| TC-022 | R14；作法 4 | 功能 | 沙盒有兩個 flaky 類檔（名稱字母序 a、b） | 帶旗標執行 | 出現標題 `== retry: re-running 2 file(s) once ==`；之後每檔一行 `retry <名稱> ... ok`；順序與第一輪相同（循序，不並行） | 自動 |
| TC-023 | R15；作法 5 | 例外 | 沙盒有 `bad_test.sh`（兩次都失敗）；不在名單 | 帶旗標執行 | 退出碼 1；`bad_test.sh` 計數＝2；輸出含 `== FAILED twice ==` 與 `FAILED bad_test.sh`；該檔重跑那行為 `retry bad_test.sh ... FAIL` | 自動 |
| TC-024 | R15；作法 5 | 例外 | 同 TC-023 | 帶旗標執行 | 輸出**不含** `FLAKY bad_test.sh`；含 `second-run-marker`（印出的是重跑 log 的尾端） | 自動 |
| TC-025 | R16；作法 5「隔離只饒過重跑會綠，不饒過真紅」 | 例外 | 同 TC-023，但 `bad_test.sh` 已登記在有效名單 | 帶旗標執行 | 仍退出碼 1，仍含 `FAILED bad_test.sh` | 自動 |
| TC-026 | R17；作法 5 | 例外 | 沙盒有 `slow_test.sh`（第一次逾時、第二次通過），用 `--timeout 1`；不在名單 | 帶旗標執行 | 被視為 FLAKY（有 `FLAKY slow_test.sh` 行，後接 `NOT in tests/quarantine.txt`）；退出碼 1 | 自動 |
| TC-027 | R17 | 功能 | 同 TC-026，但 `slow_test.sh` 已登記在有效名單 | 帶旗標執行 | 有 `FLAKY slow_test.sh` 行含 issue；退出碼 0 | 自動 |
| TC-028 | 作法 4、5「逾時」 | 例外 | 一個兩次都逾時的假檔（用 `--timeout 1`） | 帶旗標執行 | 重跑那行為 `retry <名稱> ... TIMEOUT`；該檔進 `== FAILED twice ==`；退出碼 1；不出現 FLAKY | 自動 |
| TC-029 | R18；作法 5 | 例外 | 兩個 flaky 檔，一個已登記、一個沒登記 | 帶旗標執行 | 退出碼 1；`FLAKY not quarantined:` 錯誤訊息只點名沒登記的那個，不含已登記的那個 | 自動 |
| TC-030 | R19 | 例外 | 一個已登記的 flaky＋另一個 `bad_test.sh` 真紅 | 帶旗標執行 | 退出碼 1 | 自動 |
| TC-031 | R20 | 功能 | 沙盒有 ok、flaky 等檔 | 帶 `--retry-failed-once --only flaky` 執行 | 只跑、只重跑名稱含 flaky 的檔；`ok_test.sh` 計數＝0 | 自動 |
| TC-032 | R21 | 功能 | 沙盒有多個假檔 | 分別執行 `--retry-failed-once --list` 與 `--list` | 兩者輸出逐字相同，退出碼都是 0 | 自動 |
| TC-033 | 作法 5 第一點 | 例外 | 一輪下來實際跑完的檔數不等於預期檔數（摘要出現 `INCOMPLETE`） | 帶旗標執行 | 照舊退出碼 1；重跑無法補救這種情況，不會因為重跑而變成通過。（沙盒難製造時，改由閱卷讀 `git diff` 確認該判斷在結論函式最前面） | 手動：閱卷讀 diff（能自動製造則自動） |

## User Story 3 — 隔離名單：每條要有 issue、最多 14 天、過期自動變紅（優先度 P1）

維護者原話：「隔離名單（照常跑、紅照常顯示、每條有 issue 與 ≤14 天到期）」；「名單到期自動變紅」（不需要人記得）。

規則：名單每條有效行**恰好三欄**：`tests/<檔名>.sh <issue> <YYYY-MM-DD>`。「今天」＝`RUN_ALL_TODAY`，沒設才用系統日期。到期日早於今天＝過期；晚於今天+14 天＝超過 14 天；等於今天或今天+14 都有效。**名單只在帶 `--retry-failed-once` 或 `--check-quarantine` 時才驗**，且在任何測試開跑前就驗；每個問題一行 `quarantine: tests/quarantine.txt:<行號>: <原因>`，退出碼 1。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | R22；作法 2、3 | 例外 | 今天 2026-10-24；名單有一行到期日 2026-10-23（昨天）；假檔全綠 | 帶旗標執行 | 退出碼 1；錯誤輸出（stderr）含 `quarantine: tests/quarantine.txt:<該行行號>:` 與 `expired` | 自動 |
| TC-035 | R22；作法 3「任何測試開跑前」 | 例外 | 同 TC-034，每個假檔都會寫計數檔 | 帶旗標執行 | 所有假檔的計數檔都**不存在**（沒有任何測試被執行） | 自動 |
| TC-036 | R23 | 功能 | 到期日＝2026-10-24（今天） | 帶旗標執行 | 名單有效（最後一天仍可用）；退出碼 0 | 自動 |
| TC-037 | R24 | 功能 | 到期日＝2026-11-07（今天+14） | 帶旗標執行 | 有效；退出碼 0 | 自動 |
| TC-038 | R24；作法 2 | 例外 | 到期日＝2026-11-08（今天+15） | 帶旗標執行 | 退出碼 1；訊息含 `14 days` | 自動 |
| TC-039 | R25 | 例外 | 一行只有兩欄（缺 issue） | 帶旗標執行 | 退出碼 1，訊息指出該行號 | 自動 |
| TC-040 | R26 | 功能 | issue 欄分別寫 `#12`、`https://github.com/zhshie/agentic-bioflow/issues/12`（各一次） | 帶旗標執行 | 兩種寫法都有效 | 自動 |
| TC-041 | R26 | 例外 | issue 欄分別寫 `12`、`#`、`https://example.com/x`（逐一各一次） | 帶旗標執行 | 三種都退出碼 1 | 自動 |
| TC-042 | R27 | 例外 | 到期日分別寫 `2026-13-40`、`2026-2-3`、`not-a-date`（逐一） | 帶旗標執行 | 三種都退出碼 1 | 自動 |
| TC-043 | R28；作法 2 | 例外 | 路徑分別寫：沙盒 `tests/` 裡不存在的 `tests/nope_test.sh`、`../x.sh`、`tests/a.txt`（逐一） | 帶旗標執行 | 三種都退出碼 1（防止打錯字使名單形同虛設） | 自動 |
| TC-044 | R29 | 例外 | 同一個路徑出現兩行 | 帶旗標執行 | 退出碼 1 | 自動 |
| TC-045 | R30；待裁決 2「不加第四欄」 | 不在範圍 | 一行有四欄（多一個「測試識別」之類的欄位） | 帶旗標執行 | 退出碼 1（不支援 pytest 單一測試層級的隔離，第四欄被拒絕而不是被當選用欄位） | 自動 |
| TC-046 | R31 | 功能 | 名單含註解行（`#` 開頭）、空行、行尾 CRLF（`\r`）的有效行 | 帶旗標執行 | 全部被容忍；退出碼 0 | 自動 |
| TC-047 | R32 | 例外 | 名單有一行已過期；**這一輪所有測試都綠** | 帶旗標執行 | 仍退出碼 1（到期自動變紅，不需要有測試失敗） | 自動 |
| TC-048 | R33 | 功能 | `RUN_ALL_TODAY=2028-02-20`（閏年）；分別放到期日 2028-03-05 與 2028-03-06 | 帶旗標執行 | 2028-03-05 有效；2028-03-06 無效（退出碼 1） | 自動 |
| TC-049 | R33 | 功能 | `RUN_ALL_TODAY=2026-12-25`；分別放到期日 2027-01-08 與 2027-01-09 | 帶旗標執行 | 2027-01-08 有效；2027-01-09 無效（退出碼 1）（跨年） | 自動 |
| TC-050 | R34；作法 3 | 功能 | 有效名單；沙盒內 `TMPDIR` 指向空資料夾 | 執行 `--check-quarantine` | 退出碼 0；沒有任何假檔被執行（計數檔不存在）；沒有建立 log 目錄（`bioflow-tests.*` 不存在） | 自動 |
| TC-051 | R34 | 例外 | 無效名單（例如已過期） | 執行 `--check-quarantine` | 退出碼 1，印出 `quarantine: tests/quarantine.txt:<行號>:` 訊息 | 自動 |
| TC-052 | R35 | 功能 | **真實** repo 的 `tests/quarantine.txt`（不是沙盒） | 執行真實 `$ROOT/tests/run_all.sh --check-quarantine`（帶假 uname 與 `--allow-missing-tools`） | 退出碼 0，不執行任何測試（不會遞迴）；日後有人加壞行，這條在 CI 就紅 | 自動 |
| TC-053 | 裁決二第 2 點 | 例外 | 沙盒**真的存在** `tests/platform_test.sh`（這樣不是因「檔不存在」被拒）；名單寫 `tests/platform_test.sh #12 2026-11-01` | 帶旗標執行 | 退出碼 1；訊息指出行號並說明 `platform_test.sh` 不准進隔離名單（隔離它等於放過整套 platform 測試） | 自動 |
| TC-054 | 作法 3「每個問題一行」 | 例外 | 名單有兩個不同的壞行（不同行號） | 帶旗標執行 | stderr 各有一行 `quarantine: tests/quarantine.txt:<各自行號>: <原因>`，兩個行號都出現；退出碼 1 | 自動 |
| TC-055 | 作法 2「今天」的來源 | 功能 | 不設 `RUN_ALL_TODAY`；名單一行到期日 `2000-01-01`、另一情境到期日＝系統今天（`date +%F`） | 帶旗標執行 | 2000-01-01 判為已過期（退出碼 1，含 `expired`）；到期日＝系統今天的名單有效（證明沒有寫死日期、用的是系統日期） | 自動 |
| TC-056 | 作法 2「純 bash 日數換算，不用 `date -d`，不依賴 python3」 | 功能 | PATH 上沒有 `python3`，且 `date` 被換成「一被帶 `-d` 呼叫就失敗」的假指令 | 重跑 TC-048／TC-049 的邊界日期 | 結果與 TC-048／TC-049 完全相同（有效／無效判定都對） | 自動 |
| TC-057 | 範圍「新增 tests/quarantine.txt」；裁決 4 | 功能 | 真實 repo 新增的 `tests/quarantine.txt` | 讀檔 | 只有說明用的註解與空行，**沒有任何有效條目** | 自動 |

## User Story 4 — CI 帶旗標，FLAKY 顯示在摘要（優先度 P2）

白話：改的是 GitHub 自動測試的設定檔 `.github/workflows/tests.yml`。依「裁決二」，這個檔**不給 executor 改**，等 verifier 通過後由 developer-agent 在同一分支改；所以本節全部用閱卷看 diff，**必須在 tests.yml 提交後對最終 HEAD 補閱**。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 | R36；作法 7 | 功能 | tests.yml 已被 developer-agent 修改 | 看 diff 與檔案 | 測試那個 step 有 `shell: bash`，指令為 `bash tests/run_all.sh --retry-failed-once 2>&1 \| tee "$RUNNER_TEMP/run_all.out"`，step 名稱為 `bash tests/run_all.sh --retry-failed-once`；舊的獨立一行 `run: bash tests/run_all.sh` 不見了 | 手動：閱卷看 diff |
| TC-059 | R36；作法 7（必要檢查名稱） | 功能 | 同上 | 看檔案 | job id 仍是 `run_all:`，`Install jq` step 仍在且未改（job 名與其他 step 名不得改，否則必要檢查失效） | 手動：閱卷看 diff |
| TC-060 | R36；作法 7 | 功能 | 同上 | 看新增的 step | 有一個 `if: always()` 的 step：用 `grep '^FLAKY '` 讀 `$RUNNER_TEMP/run_all.out`，有輸出時往 `$GITHUB_STEP_SUMMARY` 追加標題 `### FLAKY tests` 與那些行（markdown 清單） | 手動：閱卷看 diff |
| TC-061 | 作法 7 | 例外 | 同上 | 讀新 step 的邏輯 | 沒有 FLAKY 時什麼都不寫；此 step 自己不會讓 job 失敗（`\|\| true` 只加在 grep 無輸出那一支，tee 與測試的結果仍由前一個 step 決定） | 手動：閱卷看 diff |
| TC-062 | 作法 7「其餘既有內容不動」 | 功能 | 同上 | 對 base 比 tests.yml 的 diff | 只有：測試 step 改寫、其後新增的 step、頂端註解末加兩行說明；其他行（觸發條件、runner、checkout、Install jq）都沒動 | 手動：閱卷看 diff |
| TC-063 | 完成標準第 4 項 | 功能 | PR 已開出 | 看 CI 結果 | `run_all` job 綠；在沒有 FLAKY 時，`$GITHUB_STEP_SUMMARY` 沒有多出任何段落 | 手動：看 PR 的 CI 紀錄 |
| TC-064 | 作法 8；完成標準第 5 項 | 功能 | PR 已開出 | 看 PR 描述 | 有內建 `/code-review` 的結論（只採高信心結果），且無高信心問題 | 手動：看 PR 描述 |
| TC-065 | 裁決二第 1 點；CLAUDE.md「Never edit `.github/`」 | 不在範圍 | executor 的實作 commit | 看 git log／diff | executor 自己的 commit **沒有**改 `.github/`；tests.yml 的變更在 verifier 通過後的另一個 commit | 手動：閱卷看 git log |

## 不在範圍（計畫「不做」與「不准動」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-066 | 不做 1；作法 6 | 不在範圍 | 本機 executor／verifier 跑法 `memory/scripts/abf-fast-suite.sh`（在工作區，不在 repo） | 看 diff；並由 developer-agent 在 ledger／PR 聲明 | diff 沒有任何 `memory/` 路徑；該檔第 52 行仍是 `exec bash tests/run_all.sh "$@"`，不帶旗標，本機仍單次嚴格 | 手動：閱卷看 diff（工作區檔案需 developer-agent 聲明） |
| TC-067 | 不做 2 | 不在範圍 | 看 `tests/run_all.sh` | 對 base 比 diff | `PER_TEST_TIMEOUT=300` 那行沒被改；`--timeout` 預設值不變 | 手動：閱卷看 diff |
| TC-068 | 不做 2；「既有測試零斷言」 | 不在範圍 | 對 base 比 `tests/` | `git diff <base>...HEAD -- tests/` | 變更只有 `tests/run_all.sh`（修改）、`tests/quarantine.txt`、`tests/run_all_retry_test.sh`（新增）；`run_all_test.sh`、`run_all_count_test.sh`、`jev_test.sh`、`dev_workflow_test.sh` 與其他既有測試**一個字元都沒改** | 手動：閱卷看 diff |
| TC-069 | 不做 2 | 不在範圍 | 看整個 diff | 搜 `skip`、`xfail`、`SKIP` 等新增 | 沒有新增任何跳過或預期失敗的機制 | 手動：閱卷看 diff |
| TC-070 | 不做 3 | 不在範圍 | 看 `tests/run_all.sh` 的 diff | 搜 `git ` 指令 | 名單驗證沒有查 `git log` 或任何 git 歷史；到期只比對「檢查當天」（TC-034～TC-049 在不是 git repo 的沙盒中全部成立，亦佐證） | 手動：閱卷看 diff |
| TC-071 | 不做 5 | 不在範圍 | 看 tests.yml 的 diff | 搜 `gh issue`、`issues: write`、API 呼叫 | CI 沒有對 FLAKY 自動開 issue；只寫摘要 | 手動：閱卷看 diff |
| TC-072 | 範圍「不准動」 | 不在範圍 | 看整個 diff | 對照清單 | 這些檔沒被改：`hooks/*`、`platform/abf_station/launch.py`、`platform/tests/test_resume_edit_params_station.py`、`docs/TESTING.md`、`CLAUDE.md`、`scripts/utils/portable.sh`、`spec.md`、`test-case*.md`（實作期間）、憲法、`docs/ROADMAP.md`、`.claude-plugin/plugin.json` | 手動：閱卷看 diff |
| TC-073 | 不做 6 | 不在範圍 | 看 diff | 找 ruleset／required status checks 相關變更 | diff 沒有改 `strict_required_status_checks` 或任何分支保護設定（那是另案，且不在 repo 內，需 developer-agent 聲明） | 手動：閱卷看 diff（設定本身需人確認） |
| TC-074 | 範圍：只准改指定檔 | 不在範圍 | 看 `git diff --stat <base>...HEAD` | 比對允許清單 | 變更的檔只落在：`tests/run_all.sh`、`tests/quarantine.txt`、`tests/run_all_retry_test.sh`、`specs/ci-quarantine/ledger.md`、（verifier 通過後才有的）`.github/workflows/tests.yml`，以及先前已提交的 `specs/ci-quarantine/` 文件；沒有任何產品程式碼被動 | 手動：閱卷看 diff |

## 憲法與安全網

白話：憲法「開發流程」要求每階段 `bash tests/run_all.sh` 全綠、合併前 CI 必須綠。這次改動讓 CI 可以「重跑才綠」，風險是把真紅洗成綠。下列三條證明不會；Safety Net（hooks 閘門）此任務沒碰（見 TC-072）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-075 | 開發流程「Green at every stage」 | 例外 | 一個第一次失敗、第二次會過的檔；**不帶旗標**（本機跑法） | 執行 | 仍退出碼 1，不會自動重跑（本機驗證仍單次嚴格；同 TC-003 的測試證明） | 自動 |
| TC-076 | 開發流程「CI 必須綠」 | 例外 | 兩次都失敗的檔，不論有沒有登記在名單 | 帶旗標執行 | 一律退出碼 1，不會出現 `green after retry`（同 TC-023、TC-025、TC-030 的測試證明） | 自動 |
| TC-077 | 開發流程「CI 必須綠」 | 例外 | 重跑才綠但沒登記，或名單已過期 | 帶旗標執行 | 一律退出碼 1（FLAKY 沒登記會紅；過期自動變紅，不靠人記得；同 TC-014、TC-047 的測試證明） | 自動 |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
