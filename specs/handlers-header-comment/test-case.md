# 測試案例：handlers.py 第 1 行註解改成九種工作

<!--
Written by the verifier (CONTRACT mode) from specs/handlers-header-comment/plan.md. 本件沒有 spec.md 與維護者逐字例句；
plan.md 的「目標」「決定」「失敗先行測試」「完成標準」「不做」就是依據。沒有發明計畫沒寫的行為。
-->

**規格**：`specs/handlers-header-comment/plan.md`（本件無 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、之後有人動了程式時，系統（測試）怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

白話背景：`platform/abf_station/handlers.py` 第 1 行是一句英文註解（給人看、不影響程式），現在寫「這是兩個內建的唯讀處理器」，但同檔實際是九種工作（`JOB_KINDS`），其中三種（`launch_nextflow` 啟動分析、`cancel_run` 取消、`clean_work` 清理）在使用者確認後會寫入。本件只把這一行改對，並加一則測試，之後再加新種類卻忘了改這行，測試就會變紅。AST＝程式碼解析後的結構，註解不會進去，所以兩版 AST 相同就代表「程式行為完全沒變」。

「自動」的案例指令（相對於 `platform/`）：`ABF_PYTEST_TARGETS=tests/test_handlers_header.py bash tests/platform_test.sh`。新測試檔裡每則測試要在註解寫上它對應的 TC 編號。「手動」的案例由閱卷者在 worktree 內重跑計畫「手動檢查」所列指令或讀檔，輸出與判斷要記進 ledger。

## User Story 1 — handlers.py 第 1 行與程式一致，且有測試防再過期（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「失敗先行測試」第 1 則 `test_first_line_does_not_claim_read_only` | 功能 | 改完後的 `platform/abf_station/handlers.py` | 測試用純文字讀檔，取第 1 行、轉小寫 | 第 1 行不含 `read-only`（大小寫不拘）；只看第 1 行，第 2 行起的說明文字不影響結果 | 自動：`tests/test_handlers_header.py::test_first_line_does_not_claim_read_only` |
| TC-002 | 計畫「失敗先行測試」第 2 則 `test_first_line_does_not_claim_two_handlers` | 功能 | 同上 | 取第 1 行、轉小寫 | 第 1 行不含 `two built-in`，也沒有 `two` 後面接 `handler`（`handler`／`handlers`）的寫法 | 自動：`tests/test_handlers_header.py::test_first_line_does_not_claim_two_handlers` |
| TC-003 | 計畫「目標」；「失敗先行測試」第 3 則 `test_first_line_names_the_job_kind_count` | 功能 | 同上；`JOB_KINDS` 現在是九個元素 | 測試用 `ast` 從原始碼取 `JOB_KINDS` 這個 tuple 的長度 N（現在 9），轉成英文數字詞（`nine`），檢查第 1 行 | 第 1 行含 `nine`（即與 `JOB_KINDS` 的個數對得上） | 自動：`tests/test_handlers_header.py::test_first_line_names_the_job_kind_count` |
| TC-004 | 計畫「失敗先行測試」對照組；「作法」對照 | 功能 | 同上 | 讀第 1 行 | 第 1 行仍以 `# Not Ansible modules or Celery tasks` 開頭（保留「不是 Ansible 模組、不是 Celery 任務」的理由與 `# Not …` 前綴寫法）；此則改前、改後都必須是綠 | 自動：`tests/test_handlers_header.py`（測試名由執行者定，註解標 TC-004） |
| TC-005 | 計畫「失敗先行測試」對照組 | 功能 | 同上 | 用 `ast` 取 `JOB_KINDS` 長度 | 長度寫死為 9 的斷言通過；之後多一種或少一種 kind，這則會紅，提醒同時改註解；此則改前、改後都必須是綠 | 自動：`tests/test_handlers_header.py`（註解標 TC-005） |
| TC-006 | 計畫「決定」：後半改成「九種 job kind、其中三種在確認後寫入」，語意與模組說明一致 | 功能 | 改完後的第 1 行 | 閱卷者讀第 1 行，對照第 2–8 行模組說明 | 第 1 行說明這些是九種工作的內建處理器，且點出其中有三種會寫入、而且是在確認之後；不再把它們說成唯讀；與第 2–8 行描述的 `launch_nextflow`／`cancel_run`／`clean_work` 一致 | 手動：讀 `handlers.py:1` 與 `handlers.py:2-8`，結論記 ledger |
| TC-007 | 計畫「作法」對照、「決定」：保留理由「a job is only data for them」 | 功能 | 同上 | 閱卷者讀第 1 行 | 第 1 行仍表達「job 對它們只是資料、不是指令」的意思（原句後半「只是資料、不是命令」沒有被刪掉或改壞） | 手動：讀 `handlers.py:1`，結論記 ledger |
| TC-008 | 計畫「失敗先行測試」：先寫、改字前跑一次確認紅 | 功能 | 新測試檔已存在；ledger 有「改字前」的測試輸出 | 閱卷者讀 ledger 的紅燈輸出；並在不動工作樹的前提下，對 base（`origin/v3`）版 `handlers.py` 的內容重跑新測試（例如在暫存副本） | base 版上 TC-001、TC-002、TC-003 三則為紅，TC-004、TC-005 兩則為綠；改字後五則全綠 | 手動：ledger 紅燈輸出＋閱卷者重跑 |
| TC-009 | 計畫「失敗先行測試」：純文字讀、不 import 站台模組、不連網、不開資料庫 | 功能 | 新檔 `platform/tests/test_handlers_header.py` | 閱卷者讀測試檔的 import 與取值方式 | 以 `Path(...).read_text` 讀 `handlers.py`；沒有 `import abf_station`／`from abf_station`，沒有網路、資料庫、啟動程序的呼叫 | 手動：讀檔 |
| TC-010 | 計畫「範圍：檔案」：檔頭要有 `# Nothing existing: …` | 功能 | 新檔 `platform/tests/test_handlers_header.py` | 看檔案前 40 行 | 有一行以 `# Nothing existing:` 開頭，冒號後至少 15 個字，且說的是為何不加進既有檔（現有 handlers 測試驗證各 kind 的行為，沒人檢查檔頭註解有沒有跟上 `JOB_KINDS`） | 手動：`sed -n '1,40p'` 讀檔，結論記 ledger |
| TC-011 | 計畫「決定」「完成標準」：用 `git diff -U0` 確認差異只有第 1 行 | 功能 | 實作完成的分支 | `git diff -U0 origin/v3 -- platform/abf_station/handlers.py` | 只有一個差異區塊，且只動第 1 行（一行刪、一行增）；檔案總行數與 base 相同 | 手動：貼輸出進 ledger，閱卷者重跑 |
| TC-012 | 計畫「失敗先行測試」手動檢查：兩分支 AST dump 相等 | 功能 | 同上 | 對 base 與分支的 `handlers.py` 各做 `ast.parse` 後 `ast.dump`，比較 | 兩份 AST dump 完全相等（程式行為沒變，只有註解變） | 手動：貼輸出進 ledger，閱卷者重跑 |
| TC-013 | 計畫「完成標準」：整個 `platform/tests` 套件全綠 | 功能 | 實作完成、已提交的 HEAD | 全套測試（WSL 跑 `tests/run_all.sh`）；閱卷者只看完成記號 `GREEN <HEAD sha>`，不重跑全套 | 全綠（計畫說的「已知環境紅」若有，只剩那一條視同綠）；完成記號與 HEAD 相符且工作樹乾淨 | 自動：`tests/run_all.sh`（由完成記號證明） |
| TC-014 | 計畫「作法」：新增文字不得含站台掃描禁用的完整單字；「失敗先行測試」對照組 | 例外 | 改完後的第 1 行 | 跑既有 `test_station_static.py`（含禁用小寫完整單字 `azure` 的掃描與其他禁字掃描）與 `test_scope.py` | 兩個既有檔不改、全綠；新第 1 行沒有觸發任何一條站台掃描 | 自動：`platform/tests/test_station_static.py`、`platform/tests/test_scope.py` |
| TC-015 | 計畫「裁決 1」：寫 nine，靠測試防漂移 | 例外 | 新測試檔 | 閱卷者讀 TC-003 那則測試如何得到期望字 | 期望的數字詞是由 `JOB_KINDS` 的長度推出來的，不是在測試裡寫死 `nine`；所以之後 `JOB_KINDS` 多一個元素而第 1 行仍寫 nine，這則會變紅 | 手動：讀測試檔，結論記 ledger |
| TC-016 | 計畫「失敗先行測試」：第 1 行（小寫後）檢查 | 例外 | 新測試檔 | 閱卷者讀 TC-001、TC-002 的取值 | 檢查前先把第 1 行轉小寫，所以 `Read-Only`、`Two Built-in` 這類大小寫寫法也會被抓到 | 手動：讀測試檔，結論記 ledger |
| TC-017 | 計畫「不做」第 1 條：不改第 2 行起任何內容、`JOB_KINDS`、任何 handler 邏輯 | 不在範圍 | 同 TC-011／TC-012 | 看 diff 與 AST | 第 2 行起（模組說明、`JOB_KINDS`、`ARG_KEYS`、所有函式）逐字沒變；第 2 行仍是以 `"""What the agent does:` 開頭 | 手動：`git diff -U0` 輸出＋AST 相等，記 ledger |
| TC-018 | 計畫「範圍」不准碰；「不做」第 2、3 條 | 不在範圍 | 實作完成的分支 | `git diff --stat origin/v3`（不計 `specs/handlers-header-comment/` 底下的計畫與 ledger） | 只出現 `platform/abf_station/handlers.py` 與 `platform/tests/test_handlers_header.py` 兩個檔；`jobs.py`、`store.py`、任何 `web*.py`、`docs/` 都沒有出現 | 手動：貼 stat 輸出進 ledger，閱卷者重跑 |
| TC-019 | 計畫「範圍」：不准碰任何既有測試的既有斷言 | 不在範圍 | 同上 | 看 `platform/tests/` 與 `tests/` 底下的 diff | 只有新增 `test_handlers_header.py`；沒有任何既有測試檔被改、刪、跳過或放寬 | 手動：`git diff --stat`＋`git diff origin/v3 -- platform/tests tests`，記 ledger |
| TC-020 | 計畫「環境事實」：不准改 spec.md、test-case*.md、constitution、ROADMAP、.github、plugin.json | 不在範圍 | 同上 | 看整體 diff 清單 | 這些檔案都不在 diff 內；實作期間 `test-case.md`／`test-case-overview.md` 也沒被改 | 手動：`git diff --name-only origin/v3`，記 ledger |
| TC-021 | 計畫「不做」：不需要 migration | 不在範圍 | 同上 | 看 diff 清單 | 沒有資料庫 migration 檔或 schema 變動（計畫已寫明不需要的理由：只動註解與新測試） | 手動：看 TC-018 的清單，記 ledger |

## 憲法與安全網

白話：本件是 A 級（只改註解、加測試），要證明的是「沒有碰到任何安全規則」，而不是新增行為。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 原則 I.1：每個檔要在檔頭說明「為何自己做」（`# Not <tool>: <reason>`／`# Nothing existing: <why>`）；handlers.py 第 1 行屬這種寫法，新測試檔也要照 | 功能 | 改完後的分支 | 跑 `tests/scripts_name_their_alternative.sh` | 仍通過（本件沒有讓檢查變紅；第 1 行保留 `# Not …:` 的寫法） | 自動：`tests/scripts_name_their_alternative.sh` |
| TC-023 | 安全網：平台每個寫入工具在有人回答前一律拒絕（`test_actions_layer.py` 的 `test_tcb04_*` 到 `test_tcb08_*`、`test_human_channel.py` 的 `test_tch09_*`／`test_tca14_*`） | 功能 | 改完後的分支 | 跑這些既有測試 | 全綠，且這些測試檔未被改動 | 自動：`platform/tests/test_actions_layer.py`、`platform/tests/test_human_channel.py` |
| TC-024 | 專長守則（backend）確認管道：每個寫入動作未經確認不得改變資料 | 功能 | 改完後的分支 | 看 TC-012 的 AST 結果，並跑既有的確認相關測試（如 `test_cleanup_confirm.py`、`test_confirm_page.py`） | `launch_nextflow`／`cancel_run`／`clean_work` 的程式結構與 base 完全相同，所以沒有新增任何不經確認的寫入路徑；既有確認測試全綠 | 自動：`platform/tests/test_cleanup_confirm.py`、`platform/tests/test_confirm_page.py`；搭配手動 TC-012 |
| TC-025 | 安全網：憑證不得出現在日誌或任何輸出；專長守則：密鑰、token、密碼不得出現 | 例外 | 實作完成的分支 | 閱卷者讀 `git diff origin/v3` 新增的每一行（第 1 行與新測試檔） | 沒有任何密鑰、token、密碼、帳號、內部路徑 | 手動：讀 diff，結論記 ledger |
| TC-026 | 專長守則（backend）對等性：使用者可見動作與動作層函式一一對應 | 不在範圍 | 同上 | 看 diff 清單 | 本件沒有新增、改名或刪除任何動作、路由或動作層函式；`web*.py`、動作層檔案都不在 diff 內 | 手動：看 TC-018 清單，記 ledger |
| TC-027 | 專長守則（backend）擁有者規則／跨使用者：使用者只能看與改自己的紀錄 | 不在範圍 | 同上 | 看 diff 清單與 AST 相等結果 | 本件沒有改任何依呼叫者身分過濾紀錄的程式（`store.py`、`jobs.py`、動作層都未動），不需要新增跨使用者測試 | 手動：看 TC-012、TC-018，記 ledger |
| TC-028 | 專長守則（backend）錯誤訊息與日誌：不露堆疊、內部路徑或 SQL；訊息說明原因與處理方式 | 不在範圍 | 同上 | 看 AST 相等結果 | 因為兩版 AST 相等（字串常數也包含在內），所有使用者看得到的訊息、日誌文字與 base 完全相同 | 手動：看 TC-012，記 ledger |

<!--
Rules for the writer:
- 每則計畫所列的測試與手動檢查都有 TC；沒有維護者逐字例句（本件是內部註解修正，不是使用者可見的功能）。
- 編號確認後不重編。
-->
