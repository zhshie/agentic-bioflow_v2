# 測試案例：站台第二道鎖的佇列名稱檢查補上「不准含 ..」

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
本件沒有 spec.md；`specs/station-queue-dotdot/plan.md` 同時是規格。下表「對應需求」欄引用 plan.md 的段落名稱。
-->

**規格**：`specs/station-queue-dotdot/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

白話說明：「站台」是實驗室叢集那邊替平台跑工作的小程式；「第二道鎖」是站台收到工作後自己再檢查一次佇列名稱（叢集上排隊用的名字，例如 `ct224`）。「平台端」是第一道鎖，已經會拒收含 `..` 的名字；站台端這次要補上同一條，讓兩邊拒收同一批名字。程式裡站台端的函式叫 `rules.clean_queue(value, label)`，拒收時丟 `rules.Refusal`；平台端的檢查是 `compute_envs._check_slurm(config)`，拒收時丟 `CEError`。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、不該收的輸入進來時，系統怎麼反應（拒絕）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

新測試檔：`platform/tests/test_station_queue_name.py`（標「自動」的列都在這個檔，除非另外寫明）。每個測試的註解要寫出自己的 TC 編號。

## User Story 1 — 站台第二道鎖拒收含 `..` 的佇列名（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「目標」；「失敗先行測試」第 1 點 | 例外 | 站台端 `rules` 模組可載入，不連網、不開資料庫 | 呼叫 `rules.clean_queue("a..b", "headQueue")` | 丟出 `rules.Refusal`，不回傳字串 | 自動：`platform/tests/test_station_queue_name.py` |
| TC-002 | 「失敗先行測試」第 1 點 | 例外 | 同上 | 呼叫 `rules.clean_queue("..", "headQueue")` | 丟出 `rules.Refusal` | 自動：`platform/tests/test_station_queue_name.py` |
| TC-003 | 「失敗先行測試」第 1 點 | 例外 | 同上 | 呼叫 `rules.clean_queue("x..", "headQueue")` | 丟出 `rules.Refusal` | 自動：`platform/tests/test_station_queue_name.py` |
| TC-004 | 「作法」決定：走既有 Refusal 與文字；「不做」：不改拒絕訊息 | 例外 | 同上 | 分別對 `"a..b"` 與改前就會被拒的 `"normal\n"` 呼叫 `rules.clean_queue(名字, "headQueue")`，取兩個 Refusal 的文字 | 兩段文字完全相同，都是「headQueue is not a valid queue name (letters, digits, _ . - only)」 | 自動：`platform/tests/test_station_queue_name.py` |
| TC-005 | 專長守則（backend）：錯誤訊息說明原因與處理方式、不露內部資訊 | 例外 | 同上 | 對 `"a..b"` 取得 Refusal 的文字 | 文字含欄位名 `headQueue` 與允許的字元說明（letters, digits, _ . - only）；不含 `Traceback`、不含檔案系統路徑、不含任何密鑰或 token | 自動：`platform/tests/test_station_queue_name.py` |

## User Story 2 — 正常佇列名的結果不變（對照組，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-006 | 「目標」：正常佇列名結果不變；「失敗先行測試」對照組 | 功能 | 同上 | 呼叫 `rules.clean_queue("ct224", "headQueue")` | 原樣回傳 `"ct224"`，不丟例外；改前改後都綠 | 自動：`platform/tests/test_station_queue_name.py` |
| TC-007 | 同上 | 功能 | 同上 | 呼叫 `rules.clean_queue("gp4", "headQueue")` | 原樣回傳 `"gp4"` | 自動：`platform/tests/test_station_queue_name.py` |
| TC-008 | 同上 | 功能 | 同上 | 呼叫 `rules.clean_queue("a.b", "headQueue")`（單一個點） | 原樣回傳 `"a.b"`，不被誤判成含 `..` | 自動：`platform/tests/test_station_queue_name.py` |
| TC-009 | 同上 | 功能 | 同上 | 呼叫 `rules.clean_queue("a_b-c.1", "headQueue")` | 原樣回傳 `"a_b-c.1"` | 自動：`platform/tests/test_station_queue_name.py` |
| TC-010 | 「失敗先行測試」對照組：空字串仍被拒 | 例外 | 同上 | 呼叫 `rules.clean_queue("", "headQueue")` | 丟出 `rules.Refusal`（與改前行為相同） | 自動：`platform/tests/test_station_queue_name.py` |
| TC-011 | 「失敗先行測試」對照組：非字串仍被拒 | 例外 | 同上 | 分別呼叫 `rules.clean_queue(None, "headQueue")` 與 `rules.clean_queue(123, "headQueue")` | 兩次都丟出 `rules.Refusal` | 自動：`platform/tests/test_station_queue_name.py` |
| TC-012 | 「失敗先行測試」兩分支比對：`test_launch_bundle.py` 要跑；「範圍」：既有斷言不准動 | 例外 | 本分支完成後 | 執行 `ABF_PYTEST_TARGETS=tests/test_launch_bundle.py bash tests/platform_test.sh`（在 `platform/` 下） | 全部通過，包含既有的 `rules.clean_queue("normal\n", "headQueue")` 仍被拒（`test_launch_bundle.py:536` 附近） | 自動：`platform/tests/test_launch_bundle.py` |

## User Story 3 — 兩道鎖拒收同一批名字（優先度 P1）

比對名單固定為計畫列出的名字：拒收組 `a..b`、`..`、`x..`；收下組 `ct224`、`gp4`、`a.b`、`a_b-c.1`；另有空字串與非字串。平台端一律經 `compute_envs._check_slurm(config)`，`config` 含合法絕對路徑的 `workDir` 與要試的 `headQueue`，其餘鍵只用 `_SLURM_CONFIG` 內的；拒收時丟 `CEError`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 「目標」：兩道鎖拒收同一批名字；「失敗先行測試」一致性；裁決 2 | 例外 | 平台端、站台端模組都可載入；config 其餘欄位都合法 | 對 `a..b`、`..`、`x..` 各自：平台端 `_check_slurm(config)` 與站台端 `clean_queue(名字, "headQueue")` | 每個名字兩邊都拒（`CEError` 與 `Refusal`），沒有任何一個名字只被一邊拒 | 自動：`platform/tests/test_station_queue_name.py` |
| TC-014 | 「失敗先行測試」一致性（收下的一側）；裁決 2 | 功能 | 同上 | 對 `ct224`、`gp4`、`a.b`、`a_b-c.1` 各自跑兩邊 | 每個名字兩邊都收：平台端不丟 `CEError`，站台端原樣回傳該名字。（此列同時證明平台端這側不是空檢查：它真的收得下正常名、拒得掉 `..`） | 自動：`platform/tests/test_station_queue_name.py` |
| TC-015 | 「失敗先行測試」一致性：同一組名字（上面全部） | 例外 | 同上 | 對空字串與非字串（`None`、`123`）各自跑兩邊 | 兩邊都拒（平台端 `CEError`，站台端 `Refusal`） | 自動：`platform/tests/test_station_queue_name.py` |

## User Story 4 — 範圍、流程與證據（優先度 P1）

這幾列多半看「改了什麼」與「ledger 貼了什麼」，由閱卷者直接讀 `git diff <base>...HEAD` 與 `specs/station-queue-dotdot/ledger.md`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 「不做」：不改 `_QUEUE` 的允許字元 | 不在範圍 | 本分支完成後 | 看 `platform/abf_station/rules.py` 的 diff | `_QUEUE = re.compile(r"^[A-Za-z0-9_.-]+\Z")` 這行沒被動 | 手動：閱卷者讀 diff（本件不改 `docs/TESTING.md`） |
| TC-017 | 「範圍：檔案」；完成標準：`git diff --stat` 只含兩處 | 不在範圍 | 同上 | 看 `git diff --stat <base>...HEAD`（不含 `specs/station-queue-dotdot/` 下的 ledger 與計畫） | 只有 `platform/abf_station/rules.py` 與新檔 `platform/tests/test_station_queue_name.py`；`compute_envs.py`、`fetch.py`、`records.py`、`cloud_store.py`、`launch.py`、`mcp_server.py`、`handlers.py`、`web/`、`.github/`、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`、constitution、任何既有測試檔都沒出現 | 手動：閱卷者讀 diff |
| TC-018 | 「作法」決定：其他一行不動；「裁決」1：本件只補佇列 | 不在範圍 | 同上 | 看 `rules.py` 的 diff | 只有 `clean_queue` 的拒收條件多了 `or ".." in value`（約一行）；`path_problem`、`clean_path`、`clean_root`、`clean_environment` 等其他函式、拒絕訊息文字都沒變；沒有順手修其他漂移（有發現的寫在 ledger「後續」） | 手動：閱卷者讀 diff 與 ledger |
| TC-019 | 「不做」：不把兩邊規則合成共用常數 | 不在範圍 | 同上 | 看 `rules.py` 與 `compute_envs.py` | 站台端仍自己定義 `_QUEUE` 並自己判斷 `..`，沒有從 `compute_envs` 匯入佇列規則或共用常數；`compute_envs.py` 完全沒被改 | 手動：閱卷者讀 diff |
| TC-020 | 「不做」：不需要 migration；專長守則：資料結構變動要有 migration 或明寫不需要 | 不在範圍 | 同上 | 看 diff 有沒有資料庫結構、遷移檔、資料檔變動 | 沒有任何 migration 或資料內容變動；計畫已明寫「不需要 migration（沒有資料變動）」 | 手動：閱卷者讀 diff |
| TC-021 | 「範圍：檔案」：新測試檔頭；裁決 3 | 功能 | 本分支完成後 | 讀 `platform/tests/test_station_queue_name.py` 前 40 行 | 有一行 `# Nothing existing: …`，字數至少 15 個字，內容是「既有測試 test_launch_bundle.py 只直接測換行結尾的佇列名；沒有任何測試覆蓋 `..`」的意思 | 手動：閱卷者讀檔 |
| TC-022 | 「失敗先行測試」：改程式前先確認紅，紅的輸出貼進 ledger | 功能 | 新測試檔已寫好、`rules.py` 還是 base 的樣子 | 閱卷者把新測試檔放到 base（`origin/v3`）的 `rules.py` 上跑一次（或讀 ledger 貼的紅輸出再自己重跑確認） | TC-001、TC-002、TC-003、TC-013 紅（`clean_queue` 回傳了原字串）；TC-006 到 TC-011 與 TC-014、TC-015 綠；ledger 內貼有這份紅的輸出 | 手動：閱卷者在 base 上跑單檔並讀 ledger |
| TC-023 | 「失敗先行測試」兩分支比對；專案 CLAUDE.md「Calibration failures」 | 功能 | 本分支完成後 | 在 base 與本分支各跑 `test_station_queue_name.py`（base 側用同一份新檔）與 `test_launch_bundle.py`，並讀 ledger | base 上 `test_launch_bundle.py` 綠、本分支也綠；新檔在本分支全綠；ledger 貼有兩分支的輸出 | 手動：閱卷者兩分支各跑單檔並讀 ledger |
| TC-024 | 「完成標準」：整個 `platform/tests` 全綠 | 功能 | 本分支完成、工作樹乾淨 | 完成記號 `GREEN <HEAD sha>` 與 HEAD 相符（由 `tests/run_all.sh` 在 WSL 跑出；已知環境紅見 dev-plans README「通例：已知環境紅」） | 全套綠，或只有 README 已列的已知環境紅；沒有因本次修改新增的紅 | 自動：`tests/run_all.sh`（`platform/tests` 全套） |
| TC-025 | 完成標準：沒有既有測試被改弱；「範圍」：任何既有測試的既有斷言不准碰 | 例外 | 本分支完成後 | 看 diff 中所有既有測試檔 | 既有測試檔（含 `test_launch_bundle.py`）沒有任何被刪除、放寬、略過或改預期值的斷言；只多出新檔 | 手動：閱卷者讀 diff |

## 憲法與安全網

本件碰到的是安全網「規格或計畫不得放寬」的精神（第二道鎖只能更嚴），以及專案 CLAUDE.md 的第一則校準失敗（修安全閘門時收窄了它擋的範圍，反而放過舊的）。憲法條文沒有直接點名佇列名稱檢查。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 安全網「不得放寬」；維護者原話「絕不放寬安全網」；A 級「只更嚴、合法輸入行為不變」；校準失敗 1 | 例外 | 同一份名單：`a..b`、`..`、`x..`、`""`、`None`、`123`、`"normal\n"`、`ct224`、`gp4`、`a.b`、`a_b-c.1` | 閱卷者在 base 與本分支各對 `rules.clean_queue(名字, "headQueue")` 跑一次，逐一比對 | 本分支拒收的名字包含 base 拒收的全部（`""`、`None`、`123`、`"normal\n"` 兩邊都拒）；base 收下的 `ct224`、`gp4`、`a.b`、`a_b-c.1` 本分支仍收下且回傳值相同；唯一的差別是 `a..b`、`..`、`x..` 從收下變成拒收 | 手動：閱卷者兩分支各跑同一份名單 |
