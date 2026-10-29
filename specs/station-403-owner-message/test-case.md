# 測試案例：站台代理收到 403 時依平台訊息分辨名稱不符與擁有者不符

**規格**：`specs/station-403-owner-message/plan.md`（本件沒有 spec.md，計畫即規格；維護者原話引自計畫「維護者原話」一節）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、平台回了看不懂的東西時，系統怎麼反應。
- **不在範圍**：計畫明講不做的事；測試確認它真的沒做。

## 名詞與判讀規則（先讀這段）

- 「站台代理」＝實驗室那台機器上常駐的 `abf-station` 程式，會向平台報到（hello）、領工作（poll）、回報結果（result）。平台不讓它做事時回 403，站台代理就停下來並印一句話給使用者看；本次只改這句話。
- 三句話的**措辭由實作者定**，所以測試只比對下列「錨點」，不比對整句：
  - 「指向名稱」＝文字含 `--name`。
  - 「指向另一位使用者」＝文字含「另一位使用者」。
  - 「說名稱不符」＝文字含「另一個代理名稱」（或英文 `another agent name`）。
  - 「有狀態碼」＝文字含 `403`。
  - 「有下一步」＝擁有者不符那句含 `--user`；名稱不符與不確定那兩句含 `--name`（計畫三句要點裡各自的下一步）。
- 「真平台的兩種 403」＝測試用 `test_owner_tokens.py` 同款的 `World`／`Duo`／`TestClient` 向真平台造出來的回應，不是手抄的字串：(a) 擁有者不符＝用 alice 的 token 對 bob 已擁有的代理名稱 hello；(b) 名稱不符＝body 的 `name` 填與 token 不同的名稱 hello。
- 測試檔：`platform/tests/test_station_rejected.py`（新檔）。每個「自動」的 TC 由實作者在測試裡以註解標 TC 編號。

## User Story 1 — 擁有者不符：不再叫人去查名稱（優先度 P1）

> 目前的問題：這個代理名稱已屬於另一位使用者，站台卻說「token 是為別的代理名稱做的」，使用者照做是走錯方向。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；決定 2（含 `belongs to another user`）；失敗測試 `test_owner_mismatch_is_not_called_a_name_problem` | 功能 | 真平台上 bob 已擁有代理名稱 `ag`；拿屬於 alice 的 token 對 `ag` 報到，取得平台真的回的 403 內容 | 把這個 `(403, 內容)` 交給站台的 `_rejected(403, body)` | 回傳的文字指向「另一位使用者」 | 自動：`tests/test_station_rejected.py` |
| TC-002 | 同上 | 功能 | 同 TC-001 | 同 TC-001 | 回傳的文字**不含** `another agent name`，也不含「另一個代理名稱」（不再把擁有者問題說成名稱問題） | 自動：`tests/test_station_rejected.py` |
| TC-003 | 決定 3（每句含狀態碼、原因、下一步） | 功能 | 同 TC-001 | 同 TC-001 | 文字含 `403`，且含下一步 `--user` | 自動：`tests/test_station_rejected.py` |
| TC-004 | 裁決 2（片語由真平台驗證，防兩邊漂移） | 功能 | 同 TC-001 | 讀平台真的回的 `message` | 該 message 含 `belongs to another user`（不分大小寫）。平台哪天改了這句，這條就會紅 | 自動：`tests/test_station_rejected.py` |

## User Story 2 — 名稱不符：原本說對的話不能弄丟（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | 決定 2（含 `another agent name`）；失敗測試 `test_name_mismatch_still_says_name`（對照組，改前改後都要綠） | 功能 | 真平台上，token 是為 `ag` 做的，但報到時 body 的 `name` 填別的名字，取得真的 403 內容 | 交給 `_rejected(403, body)` | 文字指向名稱（含 `--name`），且說名稱不符（含「另一個代理名稱」） | 自動：`tests/test_station_rejected.py` |
| TC-006 | 同上 | 功能 | 同 TC-005 | 同 TC-005 | 文字**不含**「已經屬於另一位使用者」 | 自動：`tests/test_station_rejected.py` |
| TC-007 | 決定 3 | 功能 | 同 TC-005 | 同 TC-005 | 文字含 `403`，且含下一步 `--name` | 自動：`tests/test_station_rejected.py` |
| TC-008 | 裁決 2 | 功能 | 同 TC-005 | 讀平台真的回的 `message` | 該 message 含 `another agent name`（不分大小寫）。平台改了這句，這條會紅 | 自動：`tests/test_station_rejected.py` |

## User Story 3 — 認不出原因：誠實說兩種都有可能，不亂猜（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | 決定 2（沒有 message）；`test_unknown_403_covers_both_causes` | 例外 | 無 | `_rejected(403, {})` | 文字同時指向名稱（`--name`）與「另一位使用者」 | 自動：`tests/test_station_rejected.py` |
| TC-010 | 決定 2（格式不認得／平台將來改字） | 例外 | 無 | `_rejected(403, {"message": "something new"})` | 文字同時指向名稱（`--name`）與「另一位使用者」 | 自動：`tests/test_station_rejected.py` |
| TC-011 | 決定 2（message 不是字串就當沒有） | 例外 | 無 | `_rejected(403, {"message": 7})` | 不出錯；文字同時指向名稱（`--name`）與「另一位使用者」 | 自動：`tests/test_station_rejected.py` |
| TC-012 | 決定 1（`body=None` 預設） | 例外 | 無 | `_rejected(403, None)` | 不出錯；文字同時指向名稱（`--name`）與「另一位使用者」 | 自動：`tests/test_station_rejected.py` |
| TC-013 | 決定 3（每句含狀態碼、原因、下一步） | 例外 | 無 | `_rejected(403, {})` | 文字含 `403`，且含下一步 `--name` | 自動：`tests/test_station_rejected.py` |
| TC-014 | 決定 3（「彼此不同」） | 功能 | 無 | 取擁有者不符、名稱不符、不確定三種情況的文字 | 三句兩兩不相同 | 自動：`tests/test_station_rejected.py` |
| TC-015 | 決定 2（不分大小寫） | 功能 | 無 | `_rejected(403, {"message": "THIS AGENT BELONGS TO ANOTHER USER"})` 與 `{"message": "THIS TOKEN WAS MADE FOR ANOTHER AGENT NAME"}` | 前者與 TC-001 的擁有者不符那句相同，後者與 TC-005 的名稱不符那句相同 | 自動：`tests/test_station_rejected.py` |
| TC-016 | 決定 2（比對順序：先看擁有者，再看名稱） | 功能 | 無 | `_rejected(403, {"message": "belongs to another user ... another agent name"})`（兩個片語都有） | 得到擁有者不符那句（指向「另一位使用者」，不說名稱不符） | 自動：`tests/test_station_rejected.py` |

## User Story 4 — 三個呼叫點都把平台的話交給判斷，停止行為不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 決定 4（`hello`）；`test_every_call_site_passes_the_body` | 功能 | 把 `Client.post` 換成永遠回 `(403, {"message": "This agent belongs to another user"})`，不連網 | 呼叫 `Agent.hello()` | 丟出 `Rejected`，訊息是擁有者不符那句（指向「另一位使用者」、不說名稱不符） | 自動：`tests/test_station_rejected.py` |
| TC-018 | 決定 4（`answer`；原本把內容丟掉） | 功能 | 同 TC-017 | 呼叫 `Agent.answer(1, "done", {})` | 丟出 `Rejected`，訊息是擁有者不符那句 | 自動：`tests/test_station_rejected.py` |
| TC-019 | 決定 4（`loop`） | 功能 | `hello` 回 200（讓報到通過），之後 `poll` 回 `(403, {"message": "This agent belongs to another user"})` | 呼叫 `Agent.loop()` | 丟出 `Rejected`，訊息是擁有者不符那句 | 自動：`tests/test_station_rejected.py` |
| TC-020 | 決定 4（「`Rejected` 的流程完全不動」）；完成標準 | 功能 | 平台對報到回 403 | 呼叫 `agent.run(...)` | 印出以 `abf-station stopped:` 開頭、後接擁有者不符那句的訊息，並回傳 `EXIT_REJECTED` | 自動：`tests/test_station_rejected.py` |
| TC-021 | 不做：「不新增重試」；對照組「不重試、不進 backoff」 | 不在範圍 | 平台對報到回 403 | 呼叫 `Agent.hello()` | 立刻丟出 `Rejected`；`wait_or_retry` 沒有被呼叫、`failures` 仍為 0（沒有睡眠、沒有重試） | 自動：`tests/test_station_rejected.py` |

## User Story 5 — 401 不變、不洩漏任何不該印的東西（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 決定 1；目標「401 的訊息不變」 | 功能 | 無 | `_rejected(401)` | 與 origin/v3 的那句逐字相同：`the platform rejected the token (401): it is wrong or it was revoked. Ask for a new one with `abf-platform agent-token new <name>`.`（測試裡斷言等於這個 base 字串） | 自動：`tests/test_station_rejected.py` |
| TC-023 | 決定 1 | 功能 | 無 | `_rejected(401, {"message": "x"})` | 與 TC-022 完全相同（401 不看 message） | 自動：`tests/test_station_rejected.py` |
| TC-024 | 決定 2；維護者原話（不得出現 token 或使用者名稱）；`test_texts_do_not_leak` | 例外 | 無 | `_rejected(403, {"message": "alice abf_SECRET"})`（認不出的格式，內含假 token `abf_SECRET` 與使用者名 `alice`） | 輸出不含 `abf_SECRET`、不含 `alice` | 自動：`tests/test_station_rejected.py` |
| TC-025 | 同上 | 例外 | 無 | `_rejected(403, {"message": "This agent belongs to another user: alice abf_SECRET"})`（片語有命中，同樣夾帶 alice 與假 token） | 輸出是擁有者不符那句，且不含 `abf_SECRET`、不含 `alice` | 自動：`tests/test_station_rejected.py` |
| TC-026 | 不做：「不把平台回的 message 原文印到終端機或日誌」 | 不在範圍 | 無 | 對 TC-024、TC-025 與真平台兩種 403 的 message，各自檢查輸出 | 輸出都**不含**該 message 的整句原文（只拿來比對、不回貼） | 自動：`tests/test_station_rejected.py` |

## User Story 6 — 範圍與完成標準（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 不做：「不改平台端的任何回應、狀態碼、訊息文字」 | 不在範圍 | 本分支完成 | 跑既有 `tests/test_owner_tokens.py` | 全綠（其中 `MESSAGE = "This agent belongs to another user"` 鎖著平台的回應與 403 狀態碼）；TC-004、TC-008 也證明兩句平台話沒變 | 自動：`tests/test_owner_tokens.py`、`tests/test_station_rejected.py` |
| TC-028 | 範圍：不准碰 `platform/abf_platform/agents.py` 與其他平台端檔案 | 不在範圍 | 本分支完成 | `git diff --stat origin/v3...HEAD` | 清單裡沒有 `platform/abf_platform/` 底下任何檔案 | 手動：閱卷者核對 git diff（流程檢查，非 pytest） |
| TC-029 | 完成標準：「`git diff --stat` 只含 `agent.py` 與新測試檔」 | 不在範圍 | 本分支完成 | `git diff --stat origin/v3...HEAD`（扣掉 `specs/station-403-owner-message/` 的計畫與 ledger） | 只有 `platform/abf_station/agent.py` 與 `platform/tests/test_station_rejected.py` | 手動：閱卷者核對 git diff（流程檢查，非 pytest） |
| TC-030 | 不做：「不動 `abf-platform agent-token new` 的 CLI 訊息」 | 不在範圍 | 本分支完成 | 跑 `tests/test_owner_tokens.py`（其中斷言 `--user` 的提示與 `another user`）；並確認 diff 內沒有 `cli.py` | 全綠，且 `cli.py` 不在 diff | 自動：`tests/test_owner_tokens.py`；手動：閱卷者核對 git diff |
| TC-031 | 不做：「不改 docs；不需要 migration」 | 不在範圍 | 本分支完成 | 檢查 diff | 沒有 `docs/`、`web/`、`launch.py`、`.github/`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`，也沒有任何 migration 或資料結構檔 | 手動：閱卷者核對 git diff（流程檢查，非 pytest） |
| TC-032 | 範圍：不准改任何既有測試；閱卷「不得削弱測試」 | 不在範圍 | 本分支完成 | 對 `platform/tests/` 底下既有檔案比對 base | 既有測試檔零修改（只新增 `test_station_rejected.py`） | 手動：閱卷者核對 git diff（流程檢查，非 pytest） |
| TC-033 | 失敗先行測試：「改程式前跑一次確認紅」 | 功能 | 新測試檔寫好、`agent.py` 還沒改 | 在改前跑 `ABF_PYTEST_TARGETS=tests/test_station_rejected.py bash tests/platform_test.sh` | 標「現在紅」的（TC-001、TC-002、TC-009 至 TC-012、TC-013、TC-017 至 TC-019）為紅，對照組（TC-005 至 TC-008、TC-022 至 TC-026）為綠；紅的輸出貼進 `ledger.md` | 手動：閱卷者核對 ledger（流程檢查，非 pytest） |
| TC-034 | 完成標準：整個 `platform/tests` 全綠 | 功能 | 本分支完成 | 以 `tests/run_all.sh` 在 WSL 跑整套（已知環境紅依 dev-plans README「通例：已知環境紅」處理） | 全綠；完成記號 `GREEN <HEAD sha>` 與 HEAD 相符 | 自動：`tests/run_all.sh` |
| TC-035 | 兩分支比對（專案 CLAUDE.md「Calibration failures」） | 功能 | origin/v3 與本分支各一份 | 兩邊各跑 `test_station_rejected.py`、`test_owner_tokens.py`、`test_station_platform.py` | `test_owner_tokens.py`、`test_station_platform.py` 兩邊結果相同且全綠；`test_station_rejected.py` 在 base 紅（上列「現在紅」那幾條）、在本分支全綠；輸出貼進 ledger | 手動：閱卷者核對 ledger，並自行單檔重跑（非 docs/TESTING.md 步驟） |

## 憲法與安全網（backend 專長守則）

> 本件只改錯誤文字：不新增資料讀寫、路由或動作層，所以「對等性」「跨使用者讀寫」「寫入確認」「migration」不適用（TC-027、TC-031 證明平台端與資料結構沒動）。適用的是「錯誤訊息」與「不洩漏密鑰」兩條。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | backend：錯誤訊息說明發生了什麼事、使用者該怎麼處理 | 功能 | 無 | 取三種 403 情況的文字（擁有者不符、名稱不符、認不出） | 每句都含 `403`、一個原因、一個下一步（錨點見上方判讀規則）；用詞是否白話另由人判斷（見總覽） | 自動：`tests/test_station_rejected.py` |
| TC-037 | backend：不露出堆疊、內部路徑或 SQL | 例外 | 無 | 取三種 403 情況的文字 | 不含 `Traceback`、`.py`、`SELECT`、`/home`、`C:\` | 自動：`tests/test_station_rejected.py` |
| TC-038 | backend：密鑰、token、密碼不得出現在日誌或任何回應中 | 例外 | 平台回的 message 夾帶假 token `abf_SECRET`，代理持有的 token 也設成可辨識的假值 | 呼叫 `agent.run(...)` 並攔下它印出的所有輸出（stdout 與 stderr） | 輸出不含 `abf_SECRET`，也不含代理自己的 token 值 | 自動：`tests/test_station_rejected.py` |
