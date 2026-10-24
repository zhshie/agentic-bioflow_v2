# 測試案例：CI 失敗只重跑一次＋隔離名單（ci-quarantine）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
Revised 2026-10-24 after the review: plan sections 裁決三 and 裁決四 override the earlier plan text and the first version of this file.
IDs are never renumbered: rows that no longer apply are struck through and kept; rows whose expected result changed keep their ID and are marked 【修訂】.
-->

**規格**：`specs/ci-quarantine/plan.md`（本任務沒有獨立的 spec.md，計畫即規格；「裁決二」「裁決三」「裁決四」優先於計畫其他段落，且後者優先於前者）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白拒絕。

## 先看這段：測試怎麼擺（所有「自動」案例共用）

白話：「測試跑法」是一支叫 `run_all.sh` 的程式，它把 `tests/` 底下每個測試檔跑一遍。這次的改動讓它可以「失敗的檔再跑一次」，並且有一份「隔離名單」`tests/quarantine.txt`，登記「已知會偶爾失敗、但已經開 issue 在處理」的測試檔。

- **沙盒**：測試在臨時資料夾裡複製一份 `run_all.sh` 與 `scripts/utils/portable.sh`，裡面只放小型假測試檔，**絕不跑真的整套**（會無限遞迴）。
- **四種假測試檔**：`ok_test.sh`（永遠通過）；`flaky_test.sh`（第一次失敗、第二次通過，每次執行都在「計數檔」加一）；`bad_test.sh`（永遠失敗，也計數，第二次輸出含 `second-run-marker`）；`slow_test.sh`（第一次睡 3 秒、搭配 `--timeout 1` 會逾時，第二次立刻通過）。**計數檔**＝記錄某個假檔被執行了幾次，用來證明「只重跑一次」或「根本沒跑」。
- **「今天」**（裁決三 2）：一律是真實的 UTC 日期（`date -u +%F`）。**不再有改日期的後門**：測試不設 `RUN_ALL_TODAY`，改成用「今天+N」算出日期來造名單（今天-1＝昨天、今天+3、今天+15、今天+20…）。日數加減在測試裡也不得用 `date -d`（`tests/portable_userland.sh` 的規則）。測試跑完要再讀一次 UTC 今天，若跨過了 UTC 午夜就把該案例重做一次，避免邊界誤判。下文「**有效到期日**」＝今天+3。
- **名單範例（有效）**：`tests/flaky_test.sh #12 <今天+3>`（三欄：檔案、issue、到期日）。
- **假 uname**：PATH 前面放一個回答 `Linux` 的假 `uname`，且所有執行都帶 `--allow-missing-tools`，讓測試在 Git Bash 也能跑；少數案例（TC-086～TC-088）明寫例外。
- 驗證方式「自動」＝寫在 `tests/run_all_retry_test.sh`（或計畫指定的既有測試）並在註解標 TC 編號；「手動」＝閱卷者看 diff、ledger、PR 描述，或親自執行一次（`docs/TESTING.md` 此任務不准改，故不引用）。

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
| TC-009 | 作法 1「不帶旗標一字不動」；完成標準第 3 項 | 功能 | 同一個假測試目錄；base（`origin/v3`，`47701fb`）的 `run_all.sh` 與新的 `run_all.sh` | 兩邊各不帶旗標跑一次，輸出正規化後比對 | ledger 貼出兩份正規化輸出，`diff` 為空；且 `git diff` 顯示不帶旗標路徑的原程式字元沒被改（只有原結論那行被包進 `if [ "$RETRY" = 0 ]` 的形式，`RETRY=0` 走原字串）。閱卷者可自行對 base 重跑一次確認 | 手動：閱卷看 `specs/ci-quarantine/ledger.md` 與 `git diff` |
| TC-010 | 完成標準第 2 項；「既有測試零斷言需要修改」 | 功能 | 在 WSL 或 Linux，工作樹乾淨 | 跑全套 `bash tests/run_all.sh`（不帶旗標） | 結尾 `all green`；其中 `run_all_count_test.sh`、`run_all_test.sh` 原樣通過；ledger 貼出該輸出 | 自動：全套 `tests/run_all.sh`（WSL／Linux） |

## User Story 2 — 失敗的檔只重跑一次，重跑才綠的叫 FLAKY 並單獨列出（優先度 P1）

維護者原話：「失敗的那幾支只重跑一次（跟 CI 現行規則一樣）」；「重跑才綠的檔以 `FLAKY <名稱>` 單獨列出，絕不悄悄併進 passed；沒登記的 FLAKY 要失敗並說明『修掉或加一行隔離』」；「紅照常顯示」。

以下除特別說明外，都帶 `--retry-failed-once`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | R06；作法 5 | 功能 | 全部假檔通過；名單有效或無關 | 帶旗標執行 | 退出碼 0；輸出含 `all green`；不含 `FLAKY`；不含 `== retry`；每個假檔計數＝1 | 自動 |
| TC-012 | R07 | 功能 | 同 TC-011，但 `tests/quarantine.txt` 是空檔 | 帶旗標執行 | 結果同 TC-011 | 自動 |
| ~~TC-013~~ | ~~R08；作法 2「檔案不存在視同空名單」~~ | — | **作廢**：裁決三 7 改為「名單檔不見＝失敗」，由 TC-078、TC-085 取代 | — | — | — |
| TC-014 | R09；作法 5 | 例外 | 沙盒有 `ok_test.sh`、`flaky_test.sh`；名單沒有登記 flaky | 帶旗標執行 | 退出碼 1；輸出有一行**行首**就是 `FLAKY flaky_test.sh`，後面接 `  NOT in tests/quarantine.txt` | 自動 |
| TC-015 【修訂：裁決三 8】 | R09；作法 5 | 例外 | 同 TC-014 | 帶旗標執行，看錯誤輸出（stderr） | 含 `flaky_test.sh`、`Fix the test`、`tests/quarantine.txt`，以及格式提示 `tests/<name>.sh <issue> <YYYY-MM-DD> (at most 14 days out)`；**stderr 沒有任何一行以 `FLAKY ` 開頭**（句子可寫成 `Not quarantined (flaky): …` 之類，用詞不釘） | 自動 |
| TC-016 | R10；作法 5 | 功能 | 名單有效登記 `tests/flaky_test.sh #12 <今天+3>` | 帶旗標執行 | 退出碼 0；仍有一行以 `FLAKY flaky_test.sh` 開頭，後接 `  quarantined #12 until <今天+3 的日期>` | 自動 |
| TC-017 | R10；作法 5「刻意不含 all green」 | 功能 | 同 TC-016 | 帶旗標執行，看最後一行 | 含 `green after retry: 1`，且整個輸出**不含** `all green` | 自動 |
| TC-018 | R11；作法 4「不改第一輪計數」 | 功能 | 沙盒有 ok、ok、flaky（共 3 檔），flaky 已登記 | 帶旗標執行 | 摘要行仍是第一輪數字 `2/3 passed, 1 failed`（重跑才過的檔沒有被併進 passed） | 自動 |
| TC-019 | R12 | 功能 | 同 TC-018 | 帶旗標執行 | `FLAKY flaky_test.sh` 行出現在摘要行**之後**，且位於標題 `== FLAKY (failed the first run, passed the retry) ==` 底下 | 自動 |
| TC-020 | R13；維護者「紅照常顯示」 | 功能 | 同 TC-016（flaky 已登記） | 帶旗標執行 | 輸出仍含 `== output of what did not pass ==` 與 `--- flaky_test.sh ---`（第一輪的紅沒被吞掉） | 自動 |
| TC-021 | R14；作法 4 | 功能 | 沙盒有 `ok_test.sh`、`flaky_test.sh`，各自計數 | 帶旗標執行 | `ok_test.sh` 計數＝1（沒被重跑）；`flaky_test.sh` 計數＝2（重跑恰好一次） | 自動 |
| TC-022 | R14；作法 4 | 功能 | 沙盒有兩個 flaky 類檔（名稱字母序 a、b） | 帶旗標執行 | 出現標題 `== retry: re-running 2 file(s) once ==`；之後每檔一行 `retry <名稱> ... ok`；順序與第一輪相同（循序，不並行） | 自動 |
| TC-023 | R15；作法 5 | 例外 | 沙盒有 `bad_test.sh`（兩次都失敗）；不在名單 | 帶旗標執行 | 退出碼 1；`bad_test.sh` 計數＝2；輸出含 `== FAILED twice ==` 與 `FAILED bad_test.sh`；該檔重跑那行為 `retry bad_test.sh ... FAIL` | 自動 |
| TC-024 | R15；作法 5 | 例外 | 同 TC-023 | 帶旗標執行 | 輸出**不含** `FLAKY bad_test.sh`；含 `second-run-marker`（印出的是重跑 log 的尾端） | 自動 |
| TC-025 | R16；作法 5「隔離只饒過重跑會綠，不饒過真紅」 | 例外 | 同 TC-023，但 `bad_test.sh` 已登記在有效名單 | 帶旗標執行 | 仍退出碼 1，仍含 `FAILED bad_test.sh` | 自動 |
| TC-026 【修訂：裁決三 4、裁決四 4】 | 作法 5；裁決三 4 | 例外 | 沙盒有 `slow_test.sh`（第一次逾時、第二次本來會通過），用 `--timeout 1`；不在名單 | 帶旗標執行 | **逾時的檔不重跑**：`slow_test.sh` 計數檔＝1；輸出**沒有** `FLAKY slow_test.sh`；第一輪照舊顯示它逾時；退出碼 1（照第一輪的失敗處理）。其餘輸出不釘 | 自動 |
| TC-027 【修訂：裁決三 4、裁決四 4】 | 作法 5；裁決三 4 | 例外 | 同 TC-026，但 `slow_test.sh` 已登記在有效名單 | 帶旗標執行 | 登記也救不了逾時：計數檔＝1；沒有 `FLAKY slow_test.sh`；退出碼 1 | 自動 |
| TC-028 【修訂：裁決三 4】 | 作法 4、5；裁決三 4 | 例外 | 一個兩次都會逾時的假檔（`--timeout 1`） | 帶旗標執行 | 只跑第一輪、**不重跑**（計數檔＝1，輸出沒有 `retry <名稱>` 那一行）；不出現 FLAKY；退出碼 1 | 自動 |
| TC-029 【修訂：裁決三 8】 | R18；作法 5 | 例外 | 兩個 flaky 檔，一個已登記、一個沒登記 | 帶旗標執行 | 退出碼 1；stderr 的「沒登記」錯誤訊息只點名沒登記的那個，不含已登記的那個的檔名 | 自動 |
| TC-030 | R19 | 例外 | 一個已登記的 flaky＋另一個 `bad_test.sh` 真紅 | 帶旗標執行 | 退出碼 1 | 自動 |
| TC-031 | R20 | 功能 | 沙盒有 ok、flaky 等檔 | 帶 `--retry-failed-once --only flaky` 執行 | 只跑、只重跑名稱含 flaky 的檔；`ok_test.sh` 計數＝0 | 自動 |
| TC-032 | R21 | 功能 | 沙盒有多個假檔 | 分別執行 `--retry-failed-once --list` 與 `--list` | 兩者輸出逐字相同，退出碼都是 0 | 自動 |
| TC-033 | 作法 5 第一點 | 例外 | 一輪下來實際跑完的檔數不等於預期檔數（摘要出現 `INCOMPLETE`） | 帶旗標執行 | 照舊退出碼 1；重跑無法補救這種情況，不會因為重跑而變成通過。（沙盒難製造時，改由閱卷讀 `git diff` 確認該判斷在結論函式最前面） | 手動：閱卷讀 diff（能自動製造則自動） |
| TC-078 | 裁決三 7；裁決四 5 | 例外 | 沙盒沒有 `tests/quarantine.txt`；假檔全綠（每個會寫計數檔） | 帶 `--retry-failed-once` 執行 | 退出碼**非零**；**沒有任何測試被執行**（計數檔都不存在）；訊息含 `tests/quarantine.txt`（說明名單檔不見了）。**不再默默當空名單** | 自動 |
| TC-079 | 裁決三 4 | 例外 | 沙盒有 `flaky_test.sh`（第一次紅、第二次綠）與 `slow_test.sh`（第一次逾時），`--timeout 1`；flaky 已登記 | 帶旗標執行 | `flaky_test.sh` 計數＝2（照常重跑）；`slow_test.sh` 計數＝1（不重跑）；重跑標題只算可重跑的檔：`== retry: re-running 1 file(s) once ==`；因為逾時那個仍是失敗，退出碼 1 | 自動 |
| TC-080 | 裁決三 6 | 功能 | `flaky_test.sh` 第二次執行時會印一行 `retry-run-marker`；已登記；帶 `--verbose` | 帶 `--verbose --retry-failed-once` 執行 | 畫面輸出（stdout）含 `retry-run-marker`（重跑的輸出也印到畫面）；退出碼 0 | 自動 |
| TC-081 | 裁決三 6（對照）；作法 4 | 功能 | 同 TC-080，但**不帶** `--verbose` | 帶 `--retry-failed-once` 執行 | 畫面輸出**不含** `retry-run-marker`（沒要求就只印 `retry flaky_test.sh ... ok` 一行，內容在 `.retry.log`）；退出碼 0 | 自動 |
| TC-082 | 裁決三 5 | 功能 | 讓工具檢查判定 jq 不可用（例如 PATH 前放一個執行即失敗的假 `jq`），帶 `--allow-missing-tools`；`flaky_test.sh` 已登記 | 帶旗標執行 | 第一輪摘要有 `run with --allow-missing-tools, … missing` 提示；**含 `green after retry` 的結論行也帶同一句提示**（整個輸出中該提示至少出現兩次）；退出碼 0 | 自動 |
| TC-083 | 裁決三 5 | 例外 | 同 TC-082，但 `flaky_test.sh` **沒**登記 | 帶旗標執行 | 退出碼 1；摘要與結論兩處都帶 `run with --allow-missing-tools`（stdout＋stderr 合併後該句至少出現兩次） | 自動 |

## User Story 3 — 隔離名單：每條要有 issue、最多 14 天、過期自動變紅（優先度 P1）

維護者原話：「隔離名單（照常跑、紅照常顯示、每條有 issue 與 ≤14 天到期）」；「名單到期自動變紅」（不需要人記得）。

規則：名單每條有效行**恰好三欄**：`tests/<檔名>.sh <issue> <YYYY-MM-DD>`，行尾可以有 `# 註解`（裁決三 7）。「今天」＝UTC 系統日期，沒有覆寫後門（裁決三 2）。到期日早於今天＝過期；晚於今天+14 天＝超過 14 天；等於今天或今天+14 都有效。**名單只在帶 `--retry-failed-once` 或 `--check-quarantine` 時才驗**，且在任何測試開跑前就驗；每個問題一行 `quarantine: tests/quarantine.txt:<行號>: <原因>`，退出碼 1。`tests/platform_test.sh` 與 `tests/platform_clock_test.sh` 不准進名單（裁決二 2、裁決三 1）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 【修訂：相對日期】 | R22；作法 2、3 | 例外 | 名單有一行到期日＝**今天-1（昨天）**；假檔全綠 | 帶旗標執行 | 退出碼 1；錯誤輸出（stderr）含 `quarantine: tests/quarantine.txt:<該行行號>:` 與 `expired` | 自動 |
| TC-035 | R22；作法 3「任何測試開跑前」 | 例外 | 同 TC-034，每個假檔都會寫計數檔 | 帶旗標執行 | 所有假檔的計數檔都**不存在**（沒有任何測試被執行） | 自動 |
| TC-036 【修訂：相對日期】 | R23 | 功能 | 到期日＝今天 | 帶旗標執行 | 名單有效（最後一天仍可用）；退出碼 0 | 自動 |
| TC-037 【修訂：相對日期】 | R24 | 功能 | 到期日＝今天+14 | 帶旗標執行 | 有效；退出碼 0 | 自動 |
| TC-038 【修訂：相對日期】 | R24；作法 2 | 例外 | 到期日＝今天+15 | 帶旗標執行 | 退出碼 1；訊息含 `14 days` | 自動 |
| TC-039 | R25 | 例外 | 一行只有兩欄（缺 issue） | 帶旗標執行 | 退出碼 1，訊息指出該行號 | 自動 |
| TC-040 | R26 | 功能 | issue 欄分別寫 `#12`、`https://github.com/zhshie/agentic-bioflow/issues/12`（各一次） | 帶旗標執行 | 兩種寫法都有效 | 自動 |
| TC-041 | R26 | 例外 | issue 欄分別寫 `12`、`#`、`https://example.com/x`（逐一各一次） | 帶旗標執行 | 三種都退出碼 1 | 自動 |
| TC-042 | R27 | 例外 | 到期日分別寫 `2026-13-40`、`2026-2-3`、`not-a-date`（逐一） | 帶旗標執行 | 三種都退出碼 1 | 自動 |
| TC-043 | R28；作法 2 | 例外 | 路徑分別寫：沙盒 `tests/` 裡不存在的 `tests/nope_test.sh`、`../x.sh`、`tests/a.txt`（逐一） | 帶旗標執行 | 三種都退出碼 1（防止打錯字使名單形同虛設） | 自動 |
| TC-044 | R29 | 例外 | 同一個路徑出現兩行 | 帶旗標執行 | 退出碼 1 | 自動 |
| TC-045 | R30；待裁決 2「不加第四欄」 | 不在範圍 | 一行有四欄，第四欄**不是**以 `#` 開頭的註解（例如多一個「測試識別」之類的欄位） | 帶旗標執行 | 退出碼 1（不支援 pytest 單一測試層級的隔離，第四欄被拒絕而不是被當選用欄位） | 自動 |
| TC-046 | R31 | 功能 | 名單含註解行（`#` 開頭）、空行、行尾 CRLF（`\r`）的有效行 | 帶旗標執行 | 全部被容忍；退出碼 0 | 自動 |
| TC-047 | R32 | 例外 | 名單有一行已過期；**這一輪所有測試都綠** | 帶旗標執行 | 仍退出碼 1（到期自動變紅，不需要有測試失敗） | 自動 |
| ~~TC-048~~ | ~~R33 閏年固定日期~~ | — | **作廢**：裁決三 2、裁決四 3 拿掉改今天的後門、取消固定日期案例，由 TC-091 的相對掃描取代 | — | — | — |
| ~~TC-049~~ | ~~R33 跨年固定日期~~ | — | **作廢**：同 TC-048 | — | — | — |
| TC-050 | R34；作法 3 | 功能 | 有效名單；沙盒內 `TMPDIR` 指向空資料夾 | 執行 `--check-quarantine` | 退出碼 0；沒有任何假檔被執行（計數檔不存在）；沒有建立 log 目錄（`bioflow-tests.*` 不存在） | 自動 |
| TC-051 | R34 | 例外 | 無效名單（例如已過期） | 執行 `--check-quarantine` | 退出碼 1，印出 `quarantine: tests/quarantine.txt:<行號>:` 訊息 | 自動 |
| TC-052 | R35 | 功能 | **真實** repo 的 `tests/quarantine.txt`（不是沙盒） | 執行真實 `$ROOT/tests/run_all.sh --check-quarantine`（帶假 uname 與 `--allow-missing-tools`） | 退出碼 0，不執行任何測試（不會遞迴）；日後有人加壞行，這條在 CI 就紅 | 自動 |
| TC-053 | 裁決二第 2 點 | 例外 | 沙盒**真的存在** `tests/platform_test.sh`（這樣不是因「檔不存在」被拒）；名單寫 `tests/platform_test.sh #12 <今天+3>` | 帶旗標執行 | 退出碼 1；訊息指出行號並說明 `platform_test.sh` 不准進隔離名單（隔離它等於放過整套 platform 測試） | 自動 |
| TC-054 | 作法 3「每個問題一行」 | 例外 | 名單有兩個不同的壞行（不同行號） | 帶旗標執行 | stderr 各有一行 `quarantine: tests/quarantine.txt:<各自行號>: <原因>`，兩個行號都出現；退出碼 1 | 自動 |
| TC-055 【修訂：裁決三 2】 | 作法 2「今天」的來源；裁決三 2 | 功能 | 先算出 UTC 今天 T；用 TZ 把本地時間調成比 UTC 早 14 小時、以及比 UTC 晚 12 小時各一次（這樣任何時刻至少有一個時區的「本地日期」≠ UTC 日期）；各放四條名單（各一次）：到期日＝T-1、T、T+14、T+15 | 帶旗標執行 | 兩個時區下判定都一樣：T-1 過期（退出碼 1）、T 有效、T+14 有效、T+15 超過 14 天（退出碼 1）——證明用的是 UTC 日期、不是本地日期，也沒有寫死日期 | 自動 |
| TC-056 【修訂：相對日期】 | 作法 2「純 bash 日數換算，不用 `date -d`，不依賴 python3」 | 功能 | PATH 上沒有可用的 python3，且 `date` 被換成「一被帶 `-d` 呼叫就失敗」的假指令（`date -u +%F` 照常回答） | 重跑 TC-037／TC-038 與 TC-091 的相對掃描 | 結果與原本完全相同（有效／無效判定都對） | 自動 |
| TC-057 | 範圍「新增 tests/quarantine.txt」；裁決 4 | 功能 | 真實 repo 新增的 `tests/quarantine.txt` | 讀檔 | 只有說明用的註解與空行，**沒有任何有效條目** | 自動 |
| TC-084 | 裁決三 7 | 功能 | 名單三行：`tests/flaky_test.sh #12 <今天+3> # tracked in the issue`；同樣內容但行尾是 CRLF；以及只有 `#12`、沒有行尾註解的一行（另一檔） | 帶旗標執行 | 全部有效，行尾註解不會把 issue 欄 `#12` 吃掉；退出碼 0。（對照：第四欄不是 `#` 開頭的註解仍被拒，見 TC-045） | 自動 |
| TC-085 | 裁決四 5 | 例外 | 沙盒沒有 `tests/quarantine.txt` | 執行 `--check-quarantine` | 退出碼**非零**；訊息含 `tests/quarantine.txt` 與 `missing`；不執行任何測試 | 自動 |
| TC-086 | 裁決三 3 | 例外 | 假 uname 回答 `MINGW64_NT-10.0`（原本 MSYS 會被拒絕、退出 3），**不帶** `--allow-msys`；有效名單 | 執行 `--check-quarantine` | 退出碼 0（不受 MSYS 拒絕影響）；無效名單則退出碼 1 並印 `quarantine:` 行；不印橫幅、不跑測試 | 自動 |
| TC-087 | 裁決三 3 | 例外 | 有效名單；帶 `--only` 一個沒有任何檔符合的字串（原本會 `no test files matched` 退出 2） | 執行 `--check-quarantine --only <不符合的字串>` | 退出碼 0；無效名單則退出碼 1 並印 `quarantine:` 行 | 自動 |
| TC-088 | 裁決三 3 | 例外 | jq 與 python3 都不可用（假指令執行即失敗），**不帶** `--allow-missing-tools`（原本會被擋）；有效名單 | 執行 `--check-quarantine` | 退出碼 0；無效名單則退出碼 1 並印 `quarantine:` 行；不跑測試 | 自動 |
| TC-089 | 裁決三 1 | 例外 | 沙盒**真的存在** `tests/platform_clock_test.sh`；名單寫 `tests/platform_clock_test.sh #12 <今天+3>` | 帶旗標執行 | 退出碼 1；訊息指出行號並說明它不准進隔離名單（與 `platform_test.sh` 同一套平台測試） | 自動 |
| TC-090 | 裁決三 2 | 例外 | 環境變數 `RUN_ALL_TODAY` 被設成別的日期：(a) 設成 `2000-01-01`、名單到期日＝今天+3；(b) 設成 `2000-01-01`、名單到期日＝`2000-01-05`；(c) 設成 `2099-01-01`、名單到期日＝今天+3 | 帶旗標執行 | 變數完全沒作用：(a) 有效、退出碼 0；(b) 依真實今天判為過期、退出碼 1、含 `expired`；(c) 有效、退出碼 0 | 自動 |
| TC-091 | 裁決四 3 | 功能 | 先算出 UTC 今天 T；對每個偏移 d＝-3、-2、…、+18，各放一條到期日＝T+d 的名單 | 逐一帶旗標執行 | 偏移 0 到 +14 全部有效（退出碼 0）；偏移 -3 到 -1 為過期（退出碼 1、含 `expired`）；偏移 +15 到 +18 為超過 14 天（退出碼 1、含 `14 days`）。（月底、閏日、跨年的換算只有在今天靠近時才被測到，見總覽「需要人看的事」） | 自動 |

## User Story 4 — CI 帶旗標，FLAKY 顯示在摘要（優先度 P2）

白話：改的是 GitHub 自動測試的設定檔 `.github/workflows/tests.yml`。依「裁決二」，這個檔**不給 executor 改**，由 developer-agent 在 verifier 通過後（或同一分支另一個 commit）改；所以本節全部用閱卷看 diff，**必須對最終 HEAD 驗**。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 【修訂：裁決四 2】 | R36；作法 7 | 功能 | tests.yml 已被 developer-agent 修改 | 看 diff 與檔案 | 測試那個 step 有 `shell: bash`，指令以 `bash tests/run_all.sh --retry-failed-once` 開頭、後面可以有其他旗標（`--timeout 900` 為裁決四 2 所允許），並以 `2>&1 \| tee "$RUNNER_TEMP/run_all.out"` 收尾；step 名稱為 `bash tests/run_all.sh --retry-failed-once`；舊的獨立一行 `run: bash tests/run_all.sh` 不見了 | 手動：閱卷看 diff |
| TC-059 | R36；作法 7（必要檢查名稱） | 功能 | 同上 | 看檔案 | job id 仍是 `run_all:`，`Install jq` step 仍在且未改（job 名與其他 step 名不得改，否則必要檢查失效） | 手動：閱卷看 diff |
| TC-060 【修訂：裁決三 8、裁決四 1】 | R36；作法 7 | 功能 | 同上 | 看新增的 step | 有一個 `if: always()` 的 step：用能抓 `FLAKY <名稱>.sh  …` 的 `grep -E '^FLAKY [^ ]+.sh  '` 讀 `$RUNNER_TEMP/run_all.out`，有輸出時往 `$GITHUB_STEP_SUMMARY` 追加標題 `### FLAKY tests` 與那些行（markdown 清單） | 手動：閱卷看 diff |
| TC-061 | 作法 7 | 例外 | 同上 | 讀新 step 的邏輯 | 沒有 FLAKY 時什麼都不寫；此 step 自己不會讓 job 失敗（tee 與測試的結果仍由前一個 step 決定） | 手動：閱卷看 diff |
| TC-062 【修訂】 | 作法 7「其餘既有內容不動」 | 功能 | 同上 | 對 base 比 tests.yml 的 diff | 只有：測試 step 改寫、其後新增的 step、頂端註解末加說明；其他行（觸發條件、runner、checkout、Install jq）都沒動 | 手動：閱卷看 diff |
| TC-063 | 完成標準第 4 項 | 功能 | PR 已開出 | 看 CI 結果 | `run_all` job 綠；在沒有 FLAKY 時，`$GITHUB_STEP_SUMMARY` 沒有多出任何段落 | 手動：看 PR 的 CI 紀錄 |
| TC-064 | 作法 8；完成標準第 5 項 | 功能 | PR 已開出 | 看 PR 描述 | 有內建 `/code-review` 的結論（只採高信心結果），且無高信心問題 | 手動：看 PR 描述 |
| TC-065 | 裁決二第 1 點；CLAUDE.md「Never edit `.github/`」 | 不在範圍 | executor 的實作 commit | 看 git log／diff | executor 自己的 commit **沒有**改 `.github/`；tests.yml 的變更在 developer-agent 的另一個 commit | 手動：閱卷看 git log |
| TC-092 | 裁決四 1（計畫稱「TC-103 交叉驗證」） | 功能 | tests.yml 已修改；沙盒跑出真實輸出：一個已登記 flaky＋一個未登記 flaky（stdout 與 stderr 以 `2>&1` 合併，和 CI 一樣）；另一份是全綠輸出 | 閱卷者把 tests.yml 摘要 step 裡的 grep 式子原樣取出，套在這兩份輸出上 | 對 flaky 輸出：**恰好**抓到每個 flaky 檔各一行 `FLAKY <名稱>.sh  …`；**抓不到** `== FLAKY (failed the first run, passed the retry) ==` 標題、也抓不到 stderr 的錯誤句、`green after retry` 行；對全綠輸出：什麼都抓不到 | 手動：閱卷者實跑 |

## 不在範圍（計畫「不做」與「不准動」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-066 | 不做 1；作法 6 | 不在範圍 | 本機 executor／verifier 跑法 `memory/scripts/abf-fast-suite.sh`（在工作區，不在 repo） | 看 diff；並由 developer-agent 在 ledger／PR 聲明 | diff 沒有任何 `memory/` 路徑；該檔仍是 `exec bash tests/run_all.sh "$@"`，不帶旗標，本機仍單次嚴格 | 手動：閱卷看 diff（工作區檔案需 developer-agent 聲明） |
| TC-067 | 不做 2 | 不在範圍 | 看 `tests/run_all.sh` | 對 base 比 diff | `PER_TEST_TIMEOUT=300` 那行沒被改；`--timeout` 預設值不變（CI 傳 `--timeout 900` 是命令列參數，不是改預設） | 手動：閱卷看 diff |
| TC-068 | 不做 2；「既有測試零斷言」 | 不在範圍 | 對 base 比 `tests/` | `git diff <base>...HEAD -- tests/` | 變更只有 `tests/run_all.sh`（修改）、`tests/quarantine.txt`、`tests/run_all_retry_test.sh`（新增）；`run_all_test.sh`、`run_all_count_test.sh`、`jev_test.sh`、`dev_workflow_test.sh` 與其他既有測試**一個字元都沒改** | 手動：閱卷看 diff |
| TC-069 | 不做 2 | 不在範圍 | 看整個 diff | 搜 `skip`、`xfail`、`SKIP` 等新增 | 沒有新增任何跳過或預期失敗的機制 | 手動：閱卷看 diff |
| TC-070 | 不做 3 | 不在範圍 | 看 `tests/run_all.sh` 的 diff | 搜 `git ` 指令 | 名單驗證沒有查 `git log` 或任何 git 歷史；到期只比對「檢查當天」（TC-034～TC-038、TC-091 在不是 git repo 的沙盒中全部成立，亦佐證） | 手動：閱卷看 diff |
| TC-071 | 不做 5 | 不在範圍 | 看 tests.yml 的 diff | 搜 `gh issue`、`issues: write`、API 呼叫 | CI 沒有對 FLAKY 自動開 issue；只寫摘要 | 手動：閱卷看 diff |
| TC-072 | 範圍「不准動」 | 不在範圍 | 看整個 diff | 對照清單 | 這些檔沒被改：`hooks/*`、`platform/abf_station/launch.py`、`platform/tests/test_resume_edit_params_station.py`、`docs/TESTING.md`、`CLAUDE.md`、`scripts/utils/portable.sh`、`spec.md`、`test-case*.md`（實作期間）、憲法、`docs/ROADMAP.md`、`.claude-plugin/plugin.json` | 手動：閱卷看 diff |
| TC-073 | 不做 6 | 不在範圍 | 看 diff | 找 ruleset／required status checks 相關變更 | diff 沒有改 `strict_required_status_checks` 或任何分支保護設定（那是另案，且不在 repo 內，需 developer-agent 聲明） | 手動：閱卷看 diff（設定本身需人確認） |
| TC-074 | 範圍：只准改指定檔 | 不在範圍 | 看 `git diff --stat <base>...HEAD` | 比對允許清單 | 變更的檔只落在：`tests/run_all.sh`、`tests/quarantine.txt`、`tests/run_all_retry_test.sh`、`specs/ci-quarantine/` 底下的文件（含 `ledger.md`）、`.github/workflows/tests.yml`（developer-agent 的 commit）；沒有任何產品程式碼被動。（同分支若合併進其他任務的檔，以 `git diff <merge-base>...HEAD` 對本任務自己的提交判斷） | 手動：閱卷看 diff |

## 憲法與安全網

白話：憲法「開發流程」要求每階段 `bash tests/run_all.sh` 全綠、合併前 CI 必須綠。這次改動讓 CI 可以「重跑才綠」，風險是把真紅洗成綠。下列三條證明不會；Safety Net（hooks 閘門）此任務沒碰（見 TC-072）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-075 | 開發流程「Green at every stage」 | 例外 | 一個第一次失敗、第二次會過的檔；**不帶旗標**（本機跑法） | 執行 | 仍退出碼 1，不會自動重跑（本機驗證仍單次嚴格；同 TC-003 的測試證明） | 自動 |
| TC-076 | 開發流程「CI 必須綠」 | 例外 | 兩次都失敗的檔，不論有沒有登記在名單；以及逾時的檔，不論有沒有登記 | 帶旗標執行 | 一律退出碼 1，不會出現 `green after retry`（同 TC-023、TC-025、TC-027、TC-030 的測試證明） | 自動 |
| TC-077 | 開發流程「CI 必須綠」 | 例外 | 重跑才綠但沒登記，或名單已過期，或名單檔不見 | 帶旗標執行 | 一律退出碼 1／非零（FLAKY 沒登記會紅；過期自動變紅，不靠人記得；名單檔不見也紅；同 TC-014、TC-047、TC-078 的測試證明） | 自動 |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
