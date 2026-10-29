# 測試案例：job-kinds-stale-docs（jobs.py／store.py 說明改成「九種、三種會寫」）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：只有 `specs/job-kinds-stale-docs/plan.md`（沒有 spec.md）。所有預期結果取自計畫的「證據／決定／失敗先行測試／完成標準／不做」，沒有另外發明。
-->

**規格**：`specs/job-kinds-stale-docs/plan.md`（本件無 spec.md）　**總覽**：`test-case-overview.md`

維護者原話（計畫引用）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「過期文件與程式矛盾」要附 `file:line` 證據，且要能描述一則現在會紅的測試。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「種類（kind）」＝工作佇列裡一筆工作的類型，程式目前有九種（`jobs.KINDS`）；「會寫的三種」＝`launch_nextflow`、`cancel_run`、`clean_work`，排進佇列一定要有人先按過確認（`jobs.CONFIRMED`）。

## User Story 1 — 說明文字與程式一致，且之後會自動提醒（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「過期說明一」；測試 `test_jobs_module_doc_names_every_job_kind` | 功能 | 新測試檔 `platform/tests/test_job_kinds_docs.py` 已存在，`jobs.py` 開頭說明已改 | 對 `jobs.KINDS` 的每一個種類，檢查 `` `種類名` `` 是否出現在 `jobs.__doc__` | 九種全部出現，包含 `clean_work`；任一種缺席測試就失敗 | 自動：`ABF_PYTEST_TARGETS=tests/test_job_kinds_docs.py bash tests/platform_test.sh` |
| TC-002 | 計畫「過期說明一」；測試 `test_jobs_module_doc_counts_the_kinds_that_need_a_confirmation`（事實部分） | 功能 | 同上 | 檢查 `len(jobs.CONFIRMED)` | 等於 3 | 自動：同上 |
| TC-003 | 計畫「過期說明一」；同一測試（文字部分） | 功能 | 同上 | 檢查 `jobs.__doc__` 是否含 `those two kinds` | 不含 | 自動：同上 |
| TC-004 | 計畫「決定」第一點；「過期說明一」 | 功能 | `jobs.py` 開頭說明已改 | 閱卷者讀 `platform/abf_platform/jobs.py` 開頭說明字串 | 說明把會寫的三種寫成 `launch_nextflow`、`cancel_run`、`clean_work`，並說這三種排進佇列必須帶確認；不再出現「those two kinds」或只講兩種 | 手動：閱卷者逐字讀檔，引用 `path:line` |
| TC-005 | 計畫「決定」第一點 | 功能 | 同上 | 閱卷者讀 `put_upload` 在說明裡的描述 | 仍寫明 `put_upload` 把使用者自己的上傳檔寫進使用者自己的雲端前綴、免確認（按 Upload 就是同意） | 手動：同 TC-004 |
| TC-006 | 計畫「決定」第一點 | 功能 | 同上 | 閱卷者讀 `pipeline_files` 在說明裡的描述 | 明確歸為只讀（與 `preflight`、`list_site_files`、`fetch_run_records`、`read_task_log` 同類） | 手動：同 TC-004 |
| TC-007 | 計畫「過期說明二」 | 功能 | `jobs.py` 已改 | 閱卷者讀 `CONFIRMED = {...}` 上一行的 `#` 註解 | 註解講的是三種（含 `clean_work`），不再寫「the two kinds that write on the site」；`CONFIRMED` 那一行本身不變 | 手動：同 TC-004 |
| TC-008 | 計畫「過期說明三」 | 功能 | 同上 | 閱卷者讀 `_check_confirmation` 的函式說明字串 | 講的是三種會寫的種類，不再寫「the two kinds that write」；函式本體（`want = CONFIRMED[kind]` 起）不變 | 手動：同 TC-004 |
| TC-009 | 計畫「過期說明四」；測試 `test_store_comment_counts_the_job_kinds` | 功能 | `store.py` 註解已改 | 讀 `store.py` 原始碼文字，找 `exactly (\w+) job kinds`，把英文數字轉成整數 | 找得到、且等於 `len(jobs.KINDS)`（目前 9） | 自動：同 TC-001 |
| TC-010 | 計畫「過期說明四」（「三種會寫那半句本身是對的」） | 功能 | 同上 | 閱卷者讀 `store.py` 該段 `#` 註解 | 總數不再寫 eight；仍寫明 `launch_nextflow`、`cancel_run`、`clean_work` 只能帶確認進佇列，`put_upload` 寫使用者自己的雲端前綴、免確認 | 手動：閱卷者逐字讀檔 |
| TC-011 | 計畫「決定」第二、三點 | 功能 | 兩檔已改 | 閱卷者比對 base 與 HEAD 的 `jobs.py` 第 1 行與開頭說明的「Nine kinds exist」 | 第 1 行「nine job kinds」未動；說明裡的數字仍是 nine | 手動：`git diff -U0 origin/v3 -- platform/abf_platform/jobs.py` |
| TC-012 | 計畫測試 `test_store_check_constraint_lists_the_same_kinds_as_jobs`（對照組） | 功能 | 改字前後各跑一次 | 從 `store.STATE_SCHEMA` 取 `jobs` 表的 `kind IN (...)` 括號內名稱 | 集合等於 `set(jobs.KINDS)`；改字前、改字後都是綠 | 自動：同 TC-001 |
| TC-013 | 計畫測試 `test_handlers_and_jobs_agree_on_the_kinds`（對照組） | 功能 | 改字前後各跑一次 | 比較 `set(handlers.JOB_KINDS)` 與 `set(jobs.KINDS)` | 相等；改字前、改字後都是綠 | 自動：同 TC-001 |
| TC-014 | 計畫「失敗先行測試」、完成標準第 1 條 | 功能 | 新測試檔已寫、兩檔說明尚未改（base 內容） | 閱卷者把新測試檔放到 base 的 `jobs.py`／`store.py` 上跑，或讀 ledger 貼的紅輸出，再看改字後 | 改前 TC-001、TC-002（或 TC-003）、TC-009 對應的三則測試紅，原因分別是 `clean_work` 不在說明裡、說明仍寫 two、store 註解仍寫 eight；TC-012、TC-013 兩則改前改後都綠；改後前三則全綠 | 手動：閱卷者重跑或核對 ledger 的紅輸出 |
| TC-015 | 計畫「目標」（之後再加新種類忘了改說明就會紅） | 例外 | 新測試檔已寫 | 閱卷者讀測試碼：TC-001 是否逐一迭代 `jobs.KINDS`；TC-009 是否拿 `len(jobs.KINDS)` 比較而非寫死 9 | 兩者都跟著 `KINDS` 走，沒有寫死清單或數字；假設 `KINDS` 多一種而說明沒提，TC-001 會紅；假設 KINDS 長度變了而 store 註解沒改，TC-009 會紅 | 手動：閱卷者讀 `path:line` |
| TC-016 | 計畫「失敗先行測試」前言 | 功能 | 新測試檔已寫 | 閱卷者讀新測試檔的 import 與執行內容 | 只讀原始碼文字與常數；不連網、不開資料庫、不啟動伺服器 | 手動：閱卷者讀檔 |

## User Story 2 — 只改字，不改任何執行行為（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 計畫「決定」最後一點；「失敗先行測試」手動檢查 | 功能 | 兩檔已改 | `git diff -U0 origin/v3 -- platform/abf_platform/jobs.py platform/abf_platform/store.py`，逐行看變更行 | 每一個變更行不是 `#` 開頭註解，就是落在 `"""` 說明字串之內；沒有任何其他變更行 | 手動：閱卷者重跑並貼輸出 |
| TC-018 | 計畫「完成標準」第 3 條 | 功能 | 兩檔已改 | 兩個分支各對 `jobs.py`、`store.py` 做 `ast.parse`，去掉所有 docstring（模組與函式，含 `_check_confirmation`）後比對 | 兩檔的 AST 各自完全相等（含 `STATE_SCHEMA`、`_JOBS_TABLE` 的 SQL 字串、`CONFIRMED`、`KINDS`、`DEADLINE_SECONDS`） | 手動：閱卷者重跑並貼輸出 |
| TC-019 | 計畫「範圍：檔案」；完成標準第 3 條 | 功能 | 實作完成 | `git diff --stat origin/v3...HEAD`（排除 `specs/job-kinds-stale-docs/` 下的計畫與 ledger） | 只有 `platform/abf_platform/jobs.py`、`platform/abf_platform/store.py`、`platform/tests/test_job_kinds_docs.py` 三個檔 | 手動：閱卷者重跑 |
| TC-020 | 計畫「範圍」：不准碰任何既有測試的既有斷言 | 功能 | 實作完成 | 閱卷者比對 base 與 HEAD 中既有測試檔 | 沒有任何既有測試檔被改；沒有斷言被移除、放寬或改預期值 | 手動：`git diff --stat` 與逐檔比對 |
| TC-021 | 計畫「範圍」：新檔檔頭 | 功能 | 新檔已建 | 閱卷者讀 `platform/tests/test_job_kinds_docs.py` 前 40 行 | 有一行 `# Nothing existing: …`，冒號後說明為何不加進既有檔，至少 15 個字（例如現有測試檢查清單與順序、沒檢查說明文字） | 手動：閱卷者讀檔（`tests/scripts_name_their_alternative.sh` 只掃 `scripts/`、`hooks/`，不涵蓋此檔） |
| TC-022 | 計畫「環境事實」：套件掃描測試 | 例外 | 兩檔已改 | 跑 `platform/tests/test_scope.py` | `test_tc061_no_ssh_no_scheduler_no_outgoing_connection_in_the_source` 綠：新寫的說明與註解不含 `station`（子字串）、`ssh`、`sbatch`、`scancel`、`site agent` 等被禁字 | 自動：`ABF_PYTEST_TARGETS=tests/test_scope.py bash tests/platform_test.sh` |
| TC-023 | 計畫「完成標準」第 2 條 | 功能 | 實作完成、HEAD 乾淨 | 整個 `platform/tests` 套件（WSL 跑 `tests/run_all.sh`） | 全綠；已知環境紅（dev-plans README「通例：已知環境紅」）只剩那一條視同綠 | 自動：完成記號 `GREEN <HEAD sha>`（閱卷者不重跑全套） |
| TC-024 | 計畫「不做」第 2 點；裁決 2 | 不在範圍 | 實作完成 | 閱卷者看 `platform/abf_station/handlers.py` 是否有變更 | 無變更；第 1 行「two built-in read-only handlers」原樣保留（本件不順手清） | 手動：`git diff --stat` |
| TC-025 | 計畫「不做」第 3 點 | 不在範圍 | 實作完成 | 閱卷者看 `docs/PLATFORM.md` 是否有變更 | 無變更 | 手動：`git diff --stat` |
| TC-026 | 計畫「範圍」：不准碰的檔 | 不在範圍 | 實作完成 | 閱卷者看 `web*.py`、`cloud_store.py`、`launch.py`、k8s／計算環境類型相關檔是否有變更 | 全部無變更 | 手動：`git diff --stat` |
| TC-027 | 計畫「不做」第 1 點 | 不在範圍 | 實作完成 | 跑既有測試 `platform/tests/test_byte_channel_a.py`（`test_tc015_tc016_kinds_end_with_put_upload_and_confirmed_is_unchanged`）、`test_byte_channel_b.py`（`test_tc001_put_upload_is_the_last_kind`），均未被改動 | 兩則綠：種類清單與順序、`CONFIRMED` 內容、`handlers.JOB_KINDS` 都與 base 相同，沒有悄悄改常數、CHECK 約束、清單或順序 | 自動：`ABF_PYTEST_TARGETS="tests/test_byte_channel_a.py tests/test_byte_channel_b.py" bash tests/platform_test.sh` |
| TC-028 | 計畫「不做」第 3 點（不需要 migration） | 不在範圍 | 實作完成 | 閱卷者看變更清單與 TC-018 的 AST 結果 | 沒有新增 migration，資料表結構與 CHECK 約束的 SQL 文字與 base 完全相同 | 手動：`git diff --stat` 與 TC-018 輸出 |

## 憲法與安全網

<!-- 本件只改文字，不碰任何不變條款的執行邏輯；但專長守則（backend）的「確認管道」要求每個寫入動作未經確認不得改變資料，而被改說明的正是這三種寫入種類，故證明其行為未變。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 專長守則：確認管道（`clean_work`） | 例外 | 實作完成 | 跑既有 `platform/tests/test_cleanup_confirm.py::test_tc034_a_clean_work_job_is_refused_without_a_confirmation_at_the_queue_and_at_the_database` 與 `test_cleanup_store.py::test_fresh_jobs_take_clean_work_only_with_a_confirmation`（均未被改動） | 不帶確認排 `clean_work` 在佇列與資料庫兩層都被拒，資料不變 | 自動：`ABF_PYTEST_TARGETS="tests/test_cleanup_confirm.py tests/test_cleanup_store.py" bash tests/platform_test.sh` |
| TC-030 | 專長守則：確認管道（`launch_nextflow`、`cancel_run`） | 例外 | 實作完成 | 跑既有 `platform/tests/test_station_launch.py` 與 `test_launch_followup.py` 中「沒有確認就拒絕」的測試（均未被改動） | 不帶確認排 `launch_nextflow`、`cancel_run` 被拒（訊息含「no confirmation」），資料不變 | 自動：`ABF_PYTEST_TARGETS="tests/test_station_launch.py tests/test_launch_followup.py" bash tests/platform_test.sh` |
