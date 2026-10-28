# 測試案例：cloud-cleanup-backfill（舊的成功分析也能提出清理，終端機指令）

**規格**：`specs/cloud-cleanup-backfill/plan.md`（本任務沒有 spec.md，計畫即規格；維護者原話在計畫「維護者原話」一節）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

**讀這份文件前先知道的三件事**

1. 「申請」＝一張待確認的清理請求（資料庫 `confirmations` 表裡 `kind='clean_work'`、狀態 `pending` 的一列）。只有 run 的擁有者本人在網頁確認頁按「送出」才會真的刪；這個指令只負責建這張請求。
2. **旗標以 2026-10-27 裁決 4 為準**：不加 `--apply` 一律只預覽、什麼都不建；下面凡是寫「建出申請」的步驟都帶 `--apply`。計畫表格裡 T1、T2、T4 等沒寫 `--apply` 的舊寫法，一律讀成帶 `--apply`。
3. 夾具＝測試用的假資料。「run 甲／乙」＝兩個狀態為 `succeeded`、有擁有者、有工作編號的 run（甲屬於 alice、乙屬於 bob）；「run 丙」＝狀態為 `failed` 的 run。所有自動測試都寫在 `platform/tests/test_cleanup_backfill.py`，每條測試在註解裡標它對應的 TC 編號。

## US1 — 補提清理申請（指令跑起來）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 T1；作法 1、2 | 功能 | run 甲（alice）、乙（bob）為 succeeded，run 丙為 failed；`confirmations` 表沒有申請 | 管理者執行 `abf-platform runs offer-cleanup --all --apply` | 結束碼 0；`confirmations` 表多出恰好 2 列，都是 `kind='clean_work'`、狀態 `pending`，分別對應甲和乙；丙沒有 | 自動：`platform/tests/test_cleanup_backfill.py` |
| TC-002 | 計畫 T1；作法 4 | 功能 | 同 TC-001 | 同 TC-001，看輸出 | 甲那一行是「甲: 已提出申請，請 alice 登入網頁在確認頁按送出 (offered; alice presses send on the confirmation page)」的格式（run 名、擁有者名字照實代入）；乙那一行同格式、擁有者是 bob；輸出恰好 3 個 run 行加 1 行總結 | 自動 |
| TC-003 | 計畫 T1；作法 4 | 功能 | 同 TC-001 | 同 TC-001，看丙那一行 | 丙那一行以「丙: 略過：」開頭，後面接 `offer_cleanup` 回傳的 reason 原文（含「沒有成功跑完」的白話原因），不翻譯、不改寫 | 自動 |
| TC-004 | 計畫 T1；作法 4 | 功能 | 同 TC-001 | 同 TC-001，看最後一行 | 最後一行是「已提出 2 張、略過 1 個 (offered 2, skipped 1)」 | 自動 |
| TC-005 | 計畫 T2；作法 1 | 功能 | 同 TC-001 | 執行 `abf-platform runs offer-cleanup 甲 --apply`（只給 run 名） | 結束碼 0；`confirmations` 表只多 1 列（甲的）；乙沒有申請 | 自動 |
| TC-006 | 作法 2；裁決 3 | 功能 | 同 TC-001 | 同 TC-001 後查每張申請的擁有者欄 | 甲的申請擁有者是 alice 的使用者編號、乙的是 bob 的；兩者都等於各自 hand-off 紀錄（交接紀錄）裡的 user_id，不是執行指令的人 | 自動 |
| TC-007 | 計畫 T4；作法 1 | 功能 | run 甲屬 alice、乙屬 bob，都 succeeded | 執行 `abf-platform runs offer-cleanup --all --user alice --apply` | 只建 alice 的申請（`confirmations` 多 1 列、擁有者 alice）；bob 沒有申請，輸出裡 bob 的 run 沒有「已提出」那一行 | 自動 |
| TC-008 | 作法 1（`--user` 與 RUN 並用） | 功能 | 同 TC-007 | 執行 `abf-platform runs offer-cleanup 乙 --user alice --apply`（乙不屬於 alice） | 乙那一行是「略過：」；`confirmations` 表沒有新列；結束碼 0 | 自動 |
| TC-009 | 計畫 T9；作法 4 | 功能 | run 甲、乙都 succeeded；`offer_cleanup` 被換成對甲回 `{"offered": False, "reason": "quota full"}`、對乙照常的假貨 | 執行 `abf-platform runs offer-cleanup --all --apply` | 甲那一行逐字含 `quota full`；乙仍照常處理並建出申請；結束碼 0 | 自動 |
| TC-010 | 作法 4（結束碼） | 功能 | 只有 run 丙（failed），沒有任何可提的 run | 執行 `abf-platform runs offer-cleanup --all --apply` | 結束碼仍是 0（指令跑完就是 0，即使全部略過）；總結行是「已提出 0 張、略過 1 個 (offered 0, skipped 1)」 | 自動 |
| TC-011 | 計畫 T3；作法 1 | 例外 | `confirmations` 表有 N 列 | 執行 `abf-platform runs offer-cleanup --apply`（沒給 run 名也沒給 `--all`） | 結束碼 1；訊息用白話說明要給 run 名或 `--all`；`confirmations` 表仍是 N 列 | 自動 |
| TC-012 | 計畫 T3；作法 1 | 例外 | 同上 | 執行 `abf-platform runs offer-cleanup 甲 --all --apply`（兩者都給） | 結束碼 1；白話訊息說只能二選一；`confirmations` 表仍是 N 列 | 自動 |
| TC-013 | 計畫 T3；作法 4 | 例外 | 使用者名單裡沒有 nobody | 執行 `abf-platform runs offer-cleanup --all --user nobody --apply` | 結束碼 1；白話訊息說沒有這個使用者；`confirmations` 表列數不變 | 自動 |
| TC-014 | 計畫 T13；作法 2 | 例外 | 沒有叫 `no-such-run` 的 run | 執行 `abf-platform runs offer-cleanup no-such-run --apply` | 結束碼 0；該行含「略過：」和 `no such run`；`confirmations` 表沒有新列 | 自動 |
| TC-015 | 計畫 T15；作法 7 | 例外 | run 丁是 succeeded 但沒有擁有者（`add_run(name, None)`） | 執行 `abf-platform runs offer-cleanup 丁 --apply` | 該行「略過：」並顯示 `offer_cleanup` 回的「沒有擁有者」那句原文；`confirmations` 表沒有新列 | 自動 |
| TC-016 | 作法 1（`allow_abbrev=False`） | 例外 | 任何狀態 | 執行 `abf-platform runs offer-cleanup --al --apply`（旗標縮寫） | 被當成不認得的選項而拒絕（結束碼非 0），不會被猜成 `--all`；`confirmations` 表沒有新列 | 自動 |
| TC-017 | 作法 4；專長守則（錯誤訊息／日誌） | 例外 | 以 TC-011、TC-012、TC-013 的錯誤輸入，以及 `offer_cleanup` 丟例外（TC-037 的情境）各跑一次 | 看每次的完整輸出（含錯誤訊息） | 輸出沒有 Python 堆疊（Traceback）、沒有 SQL、沒有檔案系統路徑、沒有任何權杖或密碼；錯誤訊息說明發生什麼事、該怎麼做 | 自動 |

## US2 — 預覽、重複與逾時（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 裁決 4（2026-10-27）：預設只預覽 | 功能 | run 甲、乙為 succeeded、有擁有者；`confirmations` 表有 N 列 | 執行 `abf-platform runs offer-cleanup --all`（不加 `--apply`） | 結束碼 0；`confirmations` 表仍是 N 列；甲、乙兩行都出現「會提出申請 (would offer)」 | 自動 |
| TC-019 | 裁決 4：「`--all` 不加 `--apply` 一律只預覽」，預設只預覽 | 功能 | 同 TC-018 | 執行 `abf-platform runs offer-cleanup 甲`（指定 run 名、不加 `--apply`） | `confirmations` 表仍是 N 列；甲那一行出現「會提出申請」 | 自動 |
| TC-020 | 計畫 T7；作法 1 | 功能 | 同 TC-018 | 執行 `abf-platform runs offer-cleanup --all --list` | 輸出出現「會提出申請」字樣；`confirmations` 表列數不變 | 自動 |
| TC-021 | 作法 3；作法 4 | 功能 | run 甲 succeeded、run 丙 failed | 執行 `abf-platform runs offer-cleanup --all`（預覽） | 甲「會提出申請」；丙是「略過：」加原因，不會被說成會提出 | 自動 |
| TC-022 | 計畫 T8；作法 2 | 功能 | run 甲、乙都 succeeded | 連續執行兩次 `abf-platform runs offer-cleanup --all --apply` | 第二次之後 `confirmations` 表的 `clean_work` 列數與第一次之後相同（依內容重用，不重複建）；第二次的「已提出」數等於第一次或 0 | 自動 |
| TC-023 | 計畫 T10；作法 5 | 功能 | 假時鐘：第一次呼叫 `offer_cleanups` 對甲建出申請 | 時鐘往後撥 8 天，再呼叫 `offer_cleanups(…, clock=+8d)` | `confirmations` 表共 2 列 `clean_work`，其中只有 1 列還沒逾時（新的一列）；沒有新增邏輯，是既有 `offer_cleanup` 在舊申請逾時後建了新的 | 自動 |

## US3 — 永不替人確認、永不刪（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 計畫 T5；維護者原話「經本人確認刪」 | 功能 | 代理用 `FakeSite(destructive_log=True)`；run 甲、乙 succeeded | 執行 `abf-platform runs offer-cleanup --all --apply` | `jobs` 表裡 `clean_work` 工作為 0 列 | 自動 |
| TC-025 | 計畫 T5；作法 6 | 功能 | 同 TC-024 | 同 TC-024 後查 `launches` 表 | 所有列的 `work_cleaned_at` 都還是空的 | 自動 |
| TC-026 | 計畫 T5；維護者原話 | 功能 | 同 TC-024 | 同 TC-024 後查假代理的 `destructive.log` | 沒有任何紀錄（沒有任何刪除動作被送到代理） | 自動 |
| TC-027 | 裁決 4；維護者原話「每個寫入要本人答應」 | 功能 | 同 TC-018 | 預覽（`--all`、`--list`、指定 run 名不加 `--apply` 各一次） | `confirmations` 表和 `jobs` 表（全部種類）的列數都不變 | 自動 |
| TC-028 | 作法 6；憲法原則 I.2 | 功能 | 同 TC-024 | `--apply` 之後查申請狀態 | 新建的申請狀態都是 `pending`，沒有任何一列被確認或變成別的狀態 | 自動 |
| TC-029 | 專長守則：跨使用者讀 | 例外 | alice 的 run 甲已有 `pending` 申請；bob 在網頁登入 | bob 開 alice 這張申請的確認頁網址 | 被拒絕（看不到、不洩漏內容），回應與「沒有這張申請」相同 | 自動 |
| TC-030 | 專長守則：跨使用者寫 | 例外 | 同 TC-029 | bob 對 alice 這張申請送出「送出」 | 被拒絕；申請狀態仍是 `pending`；`jobs` 表仍沒有 `clean_work` 工作 | 自動 |
| TC-031 | 計畫 T6；作法 6；維護者原話「scancel…一律擋住」 | 功能 | 讀 `cli.py` 的 `cmd_runs_offer_cleanup` 和 `actions/__init__.py` 的 `offer_cleanups` 原始碼（用語法樹取該函式本身） | 掃描這兩個函式 | 不含 `approve`、`enqueue`、`subprocess`、`os.system`，也不寫 `work_cleaned_at` | 自動 |
| TC-032 | 計畫 T6 | 功能 | 同 TC-031 | 與 base 比對「通道字樣」`TERMINAL`、`PAGE` 在 `abf_platform/` 原始碼出現的次數 | 次數不增加 | 自動 |
| TC-033 | 專長守則：路由／指令處理函式不得有第二份邏輯；裁決 2 | 功能 | 讀 `cmd_runs_offer_cleanup` 原始碼；另用假的 `offer_cleanups` 換掉動作 | 掃描該函式；執行指令看輸出是否隨假動作改變 | 該函式不含 `create_pending`、`prepare_clean`、`latest_launch`（自己不判斷資格、不建申請），輸出完全由 `actions.offer_cleanups` 的回傳決定 | 自動 |

## US4 — 動作層與 dry_run（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 計畫 T12；作法 3 | 功能 | run 甲符合資格（可提） | 呼叫 `offer_cleanup(…, dry_run=True)` | `confirmations` 表不增加；回傳含 `would_offer` 鍵，甲為 `True`、`offered` 為 `False` | 自動 |
| TC-035 | 計畫 T12；作法 3 | 功能 | run 甲可提；run 丙 failed | 呼叫 `offer_cleanup(…, dry_run=False)`（預設） | 回傳的鍵集合與 f 片完全一樣：成功是 `{"offered", "id"}`、略過是 `{"offered", "reason"}`；沒有 `would_offer` 鍵 | 自動 |
| TC-036 | 裁決 5 | 功能 | 讀 `inspect.signature(actions.offer_cleanup)` | 看參數列表與 `dry_run` 的種類和預設值 | 參數列表是 `platform_path, index_path, run_name, clock, dry_run`；`dry_run` 是關鍵字參數、預設 `False`；不給它時行為與 base 位元不變（f 片原有測試全綠） | 自動：`platform/tests/test_cleanup_offer.py` |
| TC-037 | 計畫 T11；作法 2 | 例外 | `offer_cleanup` 被換成對甲丟例外、對乙正常的假貨 | 呼叫 `offer_cleanups(…)` 處理甲和乙 | 不丟出例外；甲那一列 `offered=False` 且有 reason；乙照常處理 | 自動 |
| TC-038 | 作法 2（回傳形狀） | 功能 | run 甲可提、丙 failed、另給一個不存在的名字 | 呼叫 `offer_cleanups(…, run_names=[…])` | 回傳含 `ok=True`、`results`（每列有 `run_name`、`offered`、`reason`、`owner`）、`offered` 數、`skipped` 數；`offered` + `skipped` 等於 `results` 列數；`owner` 是使用者名字，沒有擁有者或查不到時是 `None` | 自動 |
| TC-039 | 作法 2（去重、保序） | 功能 | 給的 run 名單是「甲、乙、甲」 | 呼叫 `offer_cleanups(…, run_names=["甲","乙","甲"])` | `results` 只有甲、乙兩列，順序是甲、乙；`confirmations` 只多 2 列 | 自動 |
| TC-040 | 作法 2（`user_id` 篩選） | 功能 | 甲屬 alice、乙屬 bob | 呼叫 `offer_cleanups(…, user_id=alice 的編號)` | 乙那一列 `offered=False`，reason 是 `not that user's run`；乙沒有申請 | 自動 |
| TC-041 | 作法 2（`run_names=None`） | 功能 | 索引裡有 succeeded 的甲、乙，以及 failed 的丙、running 的戊 | 呼叫 `offer_cleanups(…)` 不給 `run_names` | 只對 succeeded 的 run 逐一嘗試；丙、戊不在 `results` 裡（或至少沒被提出） | 自動 |
| TC-042 | 裁決 7；專長守則：對等性 | 功能 | 打開 `test_web_parity.py` | 檢查 `INTERNAL` 表，並執行該檔 | `INTERNAL` 比 base 只多 `offer_cleanups` 一個名字；沒有改任何其他表、沒有放寬任何檢查；該檔原有的『每個公開動作不是網頁路由就是 MCP 工具就是 INTERNAL』檢查通過（動作層函式清單與使用者可見動作清單兩邊對得上） | 自動：`platform/tests/test_web_parity.py` |
| TC-043 | 裁決 6、8 | 功能 | 打開 `test_cleanup_offer.py` | 執行該檔 | `actions.__doc__` 不含 `offer_cleanup`（本任務沒有改模組最上面的說明）；`receiver.py` 與 base 完全一樣，`complete()` 裡 `offer_cleanup` 恰好出現一次 | 自動：`platform/tests/test_cleanup_offer.py` |

## US5 — 守門測試與文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 計畫 T14；裁決 4 | 功能 | 走訪整棵指令樹（比照 `test_launch_platform.py` 的 TC-061 走法），與 base 比 | 比對新增的選項與子指令名字 | 新增的名字只有 `offer-cleanup`、`all`、`list`、`apply`（`user` 早已存在）；不含 `retry`、`confirm`、`yes`、`y`、`force`、`assume-yes`、`no-confirm` | 自動 |
| TC-045 | 計畫完成標準；TC-G02 | 功能 | 本任務的程式碼已加入 | 執行 `platform/tests/test_confirm_page.py` 的 TC-G02，不改該測試 | 通過：非測試的 `.py` 沒有 `--yes`、`--force`（除既有那兩行）、`--no-confirm`、`--assume-yes`，也沒有 `ABF_…(DEV\|YES\|SKIP\|NOCONFIRM\|AUTO_CONFIRM\|ASSUME)` | 自動：`platform/tests/test_confirm_page.py` |
| TC-046 | 計畫「允許新增的名字」 | 功能 | 本任務的程式碼已加入 | 執行 `platform/tests/test_launch_platform.py`（含 TC-061），該測試本身與 base 相同 | 通過，且 TC-061 的程式碼一個字沒改 | 自動：`platform/tests/test_launch_platform.py` |
| TC-047 | 計畫查證結果（`ADOPTING`） | 功能 | 讀 `cli.py` 的 `ADOPTING` | 比對 base | 仍然是 `("serve", "web", "mcp", "ce")`，`runs` 沒被加進去（不替沒有擁有者的 run 認領） | 自動 |
| TC-048 | 計畫完成標準；環境事實 | 功能 | 本任務的程式碼已加入 | 執行 `platform/tests/test_scope.py`（TC-061／TC-071，掃 `abf_platform/` 全部原始碼） | 通過：新程式碼與輸出文字沒有 `ssh`、`sbatch`、`scancel`、`tw `、`station`、`socket` 等禁用字；寫的是「代理／agent」 | 自動：`platform/tests/test_scope.py` |
| TC-049 | 計畫「失敗先行測試」檔首規則（TC-070） | 功能 | 新檔 `platform/tests/test_cleanup_backfill.py` | 看檔案第一行 | 以 `# Nothing existing: ` 開頭，後面理由至少 15 個字 | 自動 |
| TC-050 | 計畫完成標準：新增測試 ≤ 30 條 | 功能 | 本任務完成 | 驗收者數 `test_cleanup_backfill.py` 的測試函式數 | 不超過 30 條 | 手動：`docs/TESTING.md`（驗收者以 `git diff` 核對） |
| TC-051 | 計畫完成標準；裁決 5、7 | 功能 | 本任務完成 | 驗收者對 `git diff <base>...HEAD` 核對所有測試檔 | 既有測試沒被刪、跳過或放寬；唯二被改的既有斷言是：`test_cleanup_offer.py` 第 393 行的參數列表只在結尾加 `"dry_run"`、`test_web_parity.py` 的 `INTERNAL` 只加 `offer_cleanups`；PR 說明有『以前／以後／理由』 | 手動：`docs/TESTING.md`（驗收者以 `git diff` 核對） |
| TC-052 | 計畫「範圍：檔案」「不准動」；裁決 5、7 | 功能 | 本任務完成 | 驗收者執行 `git diff --name-only <base>...HEAD` | 只含：`platform/abf_platform/cli.py`、`platform/abf_platform/actions/__init__.py`、`platform/tests/test_cleanup_backfill.py`、`docs/OPERATIONS.md`、`docs/TESTING.md`、`specs/cloud-cleanup-backfill/ledger.md`，加上裁決 5、7 准許的 `platform/tests/test_cleanup_offer.py`、`platform/tests/test_web_parity.py`（共 8 個）；`store.py`、`confirm.py`、`jobs.py`、`receiver.py`、`web.py`、`web_board.py`、`mcp_server.py`、`guidance.py`、`actions/chat_tools.py`、`abf_station/*`、`abf_launch/*`、`docs/PLATFORM.md` 都沒動 | 手動：`docs/TESTING.md`（驗收者以 `git diff` 核對） |
| TC-053 | 計畫範圍：`docs/OPERATIONS.md` | 功能 | `docs/OPERATIONS.md` 已加指令說明 | 執行 `bash tests/operations_doc_test.sh` | 通過：六個 `##` 標題不增不減，文中提到的 `abf-platform` 指令名和 repo 路徑都真的存在 | 自動：`tests/operations_doc_test.sh` |
| TC-054 | 計畫範圍：`docs/OPERATIONS.md` | 功能 | 同 TC-053 | 驗收者讀第 5 個 `##`（Administration from the CLI） | 有一小段說明 `abf-platform runs offer-cleanup`：預設只預覽、`--apply` 才建申請、刪除仍要擁有者在確認頁按送出 | 手動：`docs/TESTING.md` |
| TC-055 | 計畫範圍：`docs/TESTING.md` | 功能 | `docs/TESTING.md` 已加小節 | 驗收者讀「cloud-cleanup-backfill」小節 | 小節存在，步驟具體到不懂程式的人能照做，依序是：找 f 片上線前就成功的 run → `abf-platform runs offer-cleanup <run>`（預覽）→ 加 `--apply` 執行 → 以擁有者身分登入網頁看確認頁出現清理申請 → 不按、確認 nano4 上 `work` 仍在 | 手動：`docs/TESTING.md` |
| TC-056 | 計畫完成標準：手動（nano4 實機） | 功能 | nano4 上有一個 f 片上線前就成功的 run，擁有者有帳號 | 維護者依 TC-055 的步驟實機操作 | 預覽只列「會提出申請」；加 `--apply` 後擁有者在網頁右欄「待處理」看到通知、確認頁出現清理申請；不按送出，nano4 上該 run 的 `work` 資料夾還在 | 手動：`docs/TESTING.md` |

## 不在範圍（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-057 | 計畫「不做」：不做網頁按鈕；T14；維護者原話「不是網頁按鈕」 | 不在範圍 | 取本任務前後 `web.py` 的路由表 | 逐字比對 | 路由表與 base 完全相同，沒有新網頁路由、沒有新按鈕 | 自動 |
| TC-058 | 計畫「不做」：不做 MCP 工具；裁決 1 | 不在範圍 | 取 MCP 伺服器的工具清單 | 與 base 比對；執行 `test_mcp.py`、`test_pat.py`、`test_oauth_mcp.py` | 工具清單與 base 相同（AI 不能替人要求清理）；那些釘著工具清單的測試不用改就通過 | 自動：`platform/tests/test_mcp.py` |
| TC-059 | 計畫「不做」：不自動、不排程、不在 `serve` 啟動時補提 | 不在範圍 | 資料庫裡有舊的 succeeded run（尚無申請） | 掃描 `abf_platform/` 非測試原始碼找 `offer_cleanups` 的引用；啟動網頁／平台一次 | `offer_cleanups` 只出現在 `actions/__init__.py` 的定義和 `cli.py` 的 `cmd_runs_offer_cleanup` 一處；啟動後 `confirmations` 表沒有新列 | 自動 |
| TC-060 | 計畫「不做」：不替沒有擁有者的 run 認領；作法 7 | 不在範圍 | 一個沒有擁有者的 succeeded run；一個有擁有者的 run | 掃描 `runs offer-cleanup` 的選項；執行指令（含 `--apply`）後查 `launches` 表 | 指令沒有 `--as`、`--owner` 之類替人認領的選項；所有 run 的 `user_id` 在指令前後完全不變 | 自動 |
| TC-061 | 計畫「不做」：不刪任何東西、不動代理端 | 不在範圍 | 代理用 `FakeSite(destructive_log=True)` | 執行 `abf-platform runs offer-cleanup --all --apply` | `jobs` 表總列數（任何種類）不變；代理端沒有收到任何工作、`destructive.log` 為空 | 自動 |
| TC-062 | 計畫「不做」：不改 7 天有效期與 50 張上限；作法 8（不需要 migration） | 不在範圍 | 執行指令前後各取一次資料庫的表與欄位定義 | 比對；另執行 `test_cleanup_store.py`、`test_cleanup_confirm.py`、`test_cleanup_offer.py`（後者只含 TC-036 准許的那一處改動） | 資料表與欄位定義前後完全相同（不需要 migration）；有效期與上限相關的既有測試不改就通過 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-063 | 原則 I.2（只有一條提交路徑、一定要本人答應；不得有第二條） | 功能 | 本任務的程式碼已加入 | 執行 `bash tests/no_second_run_state_test.sh`（它的提交掃描涵蓋 `platform/`） | 通過：新程式碼不提交任何工作、不新增第二份 run 狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-064 | 原則 I.2 通道規則；計畫完成標準 | 功能 | 本任務完成，在 WSL 執行 | `bash tests/run_all.sh` | 全部通過；尤其 `test_launch_platform.py`、`test_confirm_page.py`、`test_scope.py`、`operations_doc_test.sh` 不用放寬就綠 | 自動：`tests/run_all.sh` |
