# 測試案例：預算內免逐次確認（憲法 8.0.0 BUDGET 通道）

**規格**：無 spec.md；依 `specs/dev-mode-launch/plan.md`（含 2026-11-10 裁決）為合約依據　**總覽**：`test-case-overview.md`

名詞（一行說明）：
- **待確認**：平台照今天的做法，不自己送出，等本人按「好」（表單、確認頁、終端機或聊天回覆）。
- **BUDGET（預算內直接成立）**：本人事先在設定頁填了「單次 SU 上限」「每月 SU 上限」，AI 提出的送出在額度內時，平台直接排隊，並記為 BUDGET。
- **SU**：國網 nano4 的計算用量單位。**預估**＝同一個 pipeline、同一個站台歷史上成功的 run 的最大值。
- 「四種動作」＝ launch（送出）、resume（續跑）、relaunch（重送）、cancel（取消）。
- 「本月已用」一律指提出請求的那位使用者本人本月的用量（月界用台北時間）。
- 「不洩堆疊」＝回應與日誌裡沒有程式堆疊、內部路徑、SQL。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式的檔名：`P` = `platform/tests/test_budget_launch.py`（計畫指定的新測試檔，每條 TC 的測試要在註解寫上 TC 編號）；`D` = `tests/budget_doc_test.sh`。

## 區段 1 — 額度內 AI 的送出直接成立，其餘照今天要確認（優先度 P1）

維護者原話（lead 轉述）：Q2「nano4 SU 預算內 AI 送出免逐次確認；雲端花錢的動作永遠要確認」；Q21「免確認的門檻由使用者在設定頁自己設定（單次與每月 SU），沒設定就一律要確認」；10-13「取消直接開放」；11-03「開發模式讓 AI 直接送出是對的」。計畫對應：TC-A、TC-B、TC-C、TC-D。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | Q21「沒設定就一律要確認」；計畫 TC-A | 例外 | 新使用者，單次與每月兩個數字都是「未設」；已有該使用者擁有的 nano4 run | 以該使用者身分，經 AI 工具提出 launch、resume、relaunch、cancel 各一次 | 四次都回「待確認」；沒有任何工作入列（`jobs` 為空）；沒有 `channel='BUDGET'` 的列；行為與 `test_tch09` 的斷言相同 | 自動：`P` |
| TC-002 | Q21；計畫「額度沒設時行為與今天逐位元組相同」 | 例外 | 同 TC-001；先記下 `confirmations` 與 `jobs` 的行數與內容 | 做 TC-001 的四種請求（都不按確認） | `jobs` 行數不變；`confirmations` 只多出各請求的待確認列，與未改程式前同樣的請求所產生的列逐欄相同（除新增的空欄位 `budget_note`＝空） | 自動：`P` |
| TC-003 | Q21「單次與每月」缺一就確認；計畫 TC-B | 例外 | 只設單次上限 20；每月未設；歷史預估 10 | 提出 launch、resume、relaunch、cancel | 四種都回「待確認」，沒有工作入列 | 自動：`P` |
| TC-004 | 同上；計畫 TC-B | 例外 | 只設每月上限 100；單次未設；歷史預估 10 | 提出 launch、resume、relaunch、cancel | 四種都回「待確認」，沒有工作入列 | 自動：`P` |
| TC-005 | Q2「預算內免逐次確認」；計畫 TC-C | 功能 | 兩數字都設：單次 20、每月 100；該 pipeline 在 nano4 歷史成功預估 10 SU；本人本月已用 50；目標是 nano4 | 該使用者經 AI 工具提出 launch | 直接入列，不經表單或確認頁；`confirmations.channel`＝`BUDGET`，`confirmed_at` 非空，`caller_user_id`＝提出請求的使用者，`budget_note` 含預估 10 與兩個上限（20、100） | 自動：`P` |
| TC-006 | 同上；計畫 TC-C | 功能 | 同 TC-005 | 提出 resume | 同 TC-005 的全部結果（channel、confirmed_at、caller、budget_note） | 自動：`P` |
| TC-007 | 同上；計畫 TC-C | 功能 | 同 TC-005 | 提出 relaunch | 同 TC-005 的全部結果 | 自動：`P` |
| TC-008 | 計畫 TC-C「重複同一請求回同一 job」 | 功能 | 同 TC-005，且該 launch 已直接入列 | 用同一內容再送一次同一請求 | 回傳同一個 job，沒有多入列、沒有第二筆 BUDGET 列 | 自動：`P` |
| TC-009 | 10-13「取消直接開放」；計畫 TC-C | 功能 | 兩數字都設（單次 20、每月 100）；目標是本人擁有的 nano4 run | 提出 cancel | 直接成立：記為 `BUDGET`（`confirmed_at` 非空、`caller_user_id` 為本人），不經確認頁 | 自動：`P` |
| TC-010 | 計畫作法 4 的回傳形狀與白話 | 功能 | 同 TC-005 | 看 launch 直接成立時回傳的內容 | 與「本人在表單按好」成立時同形的 `_queued` 結果，多一個 `channel: BUDGET`，並含一句白話：「在你設定的 SU 額度內，已直接送出。預估 X SU，你的單次上限 Y、本月已用 Z／上限 W」（X、Y、Z、W 為當次實際數字：10、20、50、100） | 自動：`P` |
| TC-011 | Q2；計畫 TC-D「預估 30 ＞ 單次 20」 | 例外 | 兩數字都設（單次 20、每月 100）；歷史預估 30 SU | 提出 launch | 回「待確認」，沒有工作入列 | 自動：`P` |
| TC-012 | 計畫 TC-D「本月已用 95（95＋10＞100）」 | 例外 | 單次 20、每月 100；預估 10；本人本月已用 95 | 提出 launch | 回「待確認」，沒有工作入列 | 自動：`P` |
| TC-013 | 計畫 TC-D「剛好等於上限→成立」（單次） | 功能 | 單次 20、每月 100；預估剛好 20；本月已用 0 | 提出 launch | 直接成立（BUDGET） | 自動：`P` |
| TC-014 | 計畫 TC-D「剛好等於上限→成立」（每月） | 功能 | 單次 20、每月 100；預估 10；本月已用 90（90＋10＝100） | 提出 launch | 直接成立（BUDGET） | 自動：`P` |
| TC-015 | 計畫 TC-D「無歷史（estimate None）」；Q-a「第一次跑某 pipeline 一定要按」 | 例外 | 兩數字都設；這個 pipeline 在該站台沒有任何成功 run | 提出 launch | 回「待確認」，沒有工作入列 | 自動：`P` |
| TC-016 | 計畫 TC-D「month_total 為 None」 | 例外 | 兩數字都設；預估 10；本月用量算不出來 | 提出 launch | 回「待確認」，沒有工作入列 | 自動：`P` |
| TC-017 | 計畫 TC-D、作法 8（fail-closed） | 例外 | 兩數字都設；SU 計算（`su`）丟出例外 | 提出 launch | 回「待確認」（不報錯、不放行）；回應不含程式堆疊 | 自動：`P` |
| TC-018 | 計畫 TC-D「rates 檔缺」 | 例外 | 兩數字都設；SU 費率檔不存在 | 提出 launch | 回「待確認」；回應不含堆疊、內部路徑 | 自動：`P` |
| TC-019 | 計畫作法 8「資料庫讀失敗」 | 例外 | 兩數字都設；讀取使用者額度或歷史時資料庫丟出例外 | 提出 launch | 回「待確認」，沒有工作入列 | 自動：`P` |
| TC-020 | 2026-11-10 裁決 3(a)；Q-d「0＝什麼都不放行」 | 例外 | 單次上限 0、每月 100；預估 0 | 提出 launch | 回「待確認」（上限為 0 時即使預估是 0 也不放行） | 自動：`P` |
| TC-021 | 同上 | 例外 | 單次 20、每月上限 0；預估 0；本月已用 0 | 提出 launch | 回「待確認」 | 自動：`P` |
| TC-022 | Q-d「0＝什麼都不放行」套用到 cancel（見總覽不確定處第 1 條） | 例外 | 單次 0、每月 100（另測單次 20、每月 0）；目標是本人擁有的 nano4 run | 提出 cancel | 回「待確認」 | 自動：`P` |
| TC-023 | Q-a 預估＝同 pipeline 同站台「歷史成功 run」取最大值 | 功能 | 同 pipeline、同站台歷史：成功 run 用量 8、10、15 SU；另有一個失敗 run 用量 50 | 計算預估（經 `su.estimate_launch` 與 launch 的 BUDGET 判斷） | 預估＝15（不是 50、不是平均）；`budget_note` 記的預估是 15 | 自動：`P` |
| TC-024 | Q-a「同一 pipeline 在同一站台」 | 例外 | 只有「另一個 pipeline」或「另一個站台」的成功歷史，要提出的這個 pipeline 在 nano4 沒有歷史 | 提出 launch | 預估算不出來（None）→ 回「待確認」 | 自動：`P` |
| TC-025 | 計畫作法 3(g)「月界用既有 Asia/Taipei」 | 功能 | 每月上限 100；預估 10；有一筆 90 SU 的用量落在「台北時間上個月最後一天」，本月（台北）用量 0 | 在台北時間本月第一天提出 launch | 上月用量不計入「本月已用」→ 直接成立（BUDGET）；反向：同一筆用量落在台北時間本月內時，90＋10＝100 仍成立、超過則待確認 | 自動：`P` |
| TC-026 | 2026-11-10 裁決 3(c)「本月已用＝本人」 | 功能 | 甲、乙各自設好額度；乙本月已用 95 SU，甲本月已用 0；每月上限 100；預估 10 | 甲提出 launch | 甲直接成立（乙的用量不算進甲的額度） | 自動：`P` |
| TC-027 | 計畫作法 3(a)「stdio 無呼叫者→要確認」 | 例外 | 兩數字都設；請求經 stdio 進來（沒有呼叫者身分） | 提出 launch、cancel | 回「待確認」；沒有 `BUDGET` 列 | 自動：`P` |
| TC-028 | 計畫作法 3(d)「目標 compute env 是 SU 站台（nano4）」 | 例外 | 兩數字都設；目標環境既不是 nano4 也不是雲端（非 SU 站台） | 提出 launch、resume、relaunch | 回「待確認」 | 自動：`P` |

## 區段 2 — 花錢與刪除永遠要本人確認（優先度 P1）

維護者原話（lead 轉述）：Q2「雲端花錢的動作永遠要確認」。計畫對應：TC-E、TC-F、TC-K。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | Q2「雲端花錢永遠要確認」；計畫 TC-E | 例外 | 兩數字都設到 1,000,000；目標是雲端環境（如 Google Batch）；歷史預估很小 | 提出 launch | 回「待確認」，沒有工作入列，沒有 `BUDGET` 列 | 自動：`P` |
| TC-030 | 同上 | 例外 | 同 TC-029 | 提出 resume、relaunch | 兩者都回「待確認」，沒有 `BUDGET` 列 | 自動：`P` |
| TC-031 | 計畫作法 3(e)「`_cloud_check` 照舊先跑」；TC-E「行為不變」 | 功能 | 雲端環境，使用者有雲端美元額度設定 | 提出 launch，並比較改前改後 | 雲端額度檢查的結果與訊息與改前相同，且仍在預算判斷之前執行；既有雲端額度測試全數通過、斷言未被改 | 自動：`P` ＋ 既有 cloud 額度測試 |
| TC-032 | 2026-11-10 裁決 3(b)「cancel 不放行雲端 run」 | 例外 | 兩數字都設；目標 run 在雲端環境 | 提出 cancel | 回「待確認」，沒有 `BUDGET` 列 | 自動：`P` |
| TC-033 | 同上「無法判斷 run 所在環境時當作要確認」 | 例外 | 兩數字都設；目標 run 所在環境查不到 | 提出 cancel | 回「待確認」 | 自動：`P` |
| TC-034 | Q2；計畫 TC-F「forget 永遠要本人」 | 例外 | 兩數字都設；本人有一個可刪紀錄的 run | 經 AI 工具提出 `request_forget` | 回「待確認」；該 run 的紀錄與資料都還在；沒有 `BUDGET` 列 | 自動：`P` |
| TC-035 | 計畫 TC-F「清工作目錄永遠要本人」；憲法 Safety Net「刪 work/ 要明確確認」 | 例外 | 兩數字都設；有一個 run 的 `work/` 目錄 | 經 AI 工具提出 `clean_work` | 回「待確認」；目錄原封不動；沒有 `BUDGET` 列 | 自動：`P` |
| TC-036 | 計畫作法 4、TC-F：BUDGET 不是可直接餵給動作的通道 | 例外 | 兩數字都設 | 在動作層直接呼叫 `launch(…, BUDGET)` | 被拒，訊息含 `no human confirmation channel`；沒有工作入列 | 自動：`P`、`platform/tests/test_actions_layer.py` |
| TC-037 | 同上 | 例外 | 兩數字都設 | 在動作層直接呼叫 `cancel(…, BUDGET)` | 被拒，訊息含 `no human confirmation channel`；run 沒被取消 | 自動：`P`、`platform/tests/test_actions_layer.py`（`test_tcb04_to_b06_b09_*`） |
| TC-038 | 同上 | 例外 | 兩數字都設 | 在動作層直接呼叫 `forget(…, BUDGET)` | 被拒，訊息含 `no human confirmation channel`；紀錄不動 | 自動：`P` |
| TC-039 | 裁決 F Q-b「`ABF_HOSTED` 部署拒絕 BUDGET」；計畫 TC-K | 例外 | 環境變數 `ABF_HOSTED=1`；兩數字都設；其餘條件都在額度內 | 提出 launch、resume、relaunch | 都回「待確認」，沒有 `BUDGET` 列 | 自動：`P` |
| TC-040 | 同上 | 例外 | 同 TC-039 | 提出 cancel | 回「待確認」 | 自動：`P` |
| TC-041 | 計畫作法 7「設定頁註明『此部署不啟用』」 | 功能 | `ABF_HOSTED=1` | 本人開設定頁 | 頁面在額度欄位附近註明「此部署不啟用」；未設 `ABF_HOSTED` 時沒有這句 | 自動：`P` |

## 區段 3 — 只有本人能在設定頁設數字（優先度 P1）

維護者原話：Q21「免確認的門檻由使用者在設定頁自己設定」；憲法 8.0.0 第 4 點「只有本人能設數字……AI 自己不能把上限調高」。計畫對應：TC-G、TC-H、TC-M。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-042 | Q21；計畫作法 2 | 功能 | 使用者已登入網頁 | 在設定頁填單次 20、每月 100，按「儲存」（`POST /settings/budget`） | 儲存成功；`get_my_budget` 讀回 20 與 100；設定頁顯示這兩個數字 | 自動：`P` |
| TC-043 | 憲法 8.0.0 第 4 點；計畫 TC-G | 例外 | 使用者數字原為「未設」 | 以 ELICITED（表單）、TERMINAL（終端機）通道呼叫 `set_my_budget` | 都被拒，資料庫沒有寫入 | 自動：`P` |
| TC-044 | 同上 | 例外 | 同 TC-043 | 以 None（無通道）、模型自己給的字串、只有 token 的呼叫去呼叫 `set_my_budget` | 都被拒，資料庫沒有寫入 | 自動：`P` |
| TC-045 | 計畫作法 2、Q-d（仿 `set_cloud_cap`） | 例外 | 使用者已有單次 20、每月 100 | 用負數、NaN 呼叫 `set_my_budget`（PAGE） | 被拒並說明原因；原值 20、100 不變 | 自動：`P` |
| TC-046 | 同上 | 例外 | 同 TC-045 | 用布林值（True/False）、字串（如 "50"、"abc"）呼叫 | 被拒；原值不變 | 自動：`P` |
| TC-047 | Q-d「0–1,000,000」 | 例外 | 同 TC-045 | 用 1,000,001 呼叫 | 被拒；原值不變 | 自動：`P` |
| TC-048 | Q-d 邊界 | 功能 | 同 TC-045 | 分別存 0 與 1,000,000 | 兩者都被接受並讀回原值（0＝什麼都不放行） | 自動：`P` |
| TC-049 | 計畫作法 2「None（清除）」 | 功能 | 使用者已有兩個數字 | 儲存時把兩欄都清空（None） | 兩個數字變回「未設」；之後的請求回「待確認」 | 自動：`P` |
| TC-050 | 專長守則「跨使用者寫入」；計畫 TC-G「乙不能改甲的數字」 | 例外 | 甲、乙兩位使用者；甲已設 20、100 | 用乙的登入／token 改甲的數字 | 被拒；甲的數字不變 | 自動：`P` |
| TC-051 | 專長守則「跨使用者讀取」 | 例外 | 同 TC-050 | 用乙的登入／token 讀甲的額度 | 被拒或看不到；只看得到乙自己的 | 自動：`P` |
| TC-052 | 計畫作法 2 AST 掃描；爆炸半徑 (2) | 例外 | 程式碼原始檔 | 掃描誰呼叫 `set_my_budget` 與 `store.set_user_budget` | 只有 `web_settings`／`web.py` 的 `POST /settings/budget` 路由與動作層；`mcp_server.py`、`chat_tools.py` 內沒有 | 自動：`P` |
| TC-053 | 計畫作法 2、TC-I「MCP 不新增」 | 例外 | MCP 工具名單、`chat_tools.tool_specs()`、`platform/tests/mcp/snapshots/tools.json` | 列出所有工具名與參數 | 沒有名稱含 `budget`、`su`、`limit` 的工具或參數；`tools.json` 快照與基準零差異 | 自動：`P`、`platform/tests/mcp` 快照測試 |
| TC-054 | 計畫作法 5；爆炸半徑 (1) | 例外 | 程式碼原始檔 | AST 掃描所有能到達 `confirm.approve(…, BUDGET.name, …)` 的呼叫點 | 只有 `_ask`、`_request_attempt` 內的預算分支；`test_actions_layer.py` 白名單只列這兩處；`approve` 對無呼叫者（stdio）回 `not_yours` | 自動：`platform/tests/test_actions_layer.py`、`P` |
| TC-055 | 計畫作法「CSRF 與 `/settings/personal` 同」 | 例外 | 已登入 | 對 `POST /settings/budget` 送不帶（或錯誤）CSRF 憑證的請求 | 被拒，數字不變；帶正確 CSRF 才成功（同 `/settings/personal`） | 自動：`P` |
| TC-056 | 專長守則「對等性」；`test_web_parity.py` | 功能 | 網頁動作清單與動作層函式清單 | 測試同時列舉兩邊 | 新路由 `POST /settings/budget` 與 `set_my_budget`、`get_my_budget` 一一對應，缺一邊就失敗；路由處理函式內沒有第二份邏輯 | 自動：`platform/tests/test_web_parity.py` |
| TC-057 | 計畫作法 6「設定頁顯示目前兩個數字與『未設定＝每次都需確認』」 | 功能 | 使用者未設與已設兩種狀態 | 開設定頁 | 未設時顯示「未設定＝每次都需確認」；已設時顯示目前的兩個數字；文字不在 `web_settings.STRINGS`（`test_ce08` 雜湊不變） | 自動：`P`、`test_ce08` |
| TC-058 | 憲法擁有者規則；計畫 TC-H | 例外 | 甲設好額度（兩數字、額度內）；甲有 nano4 run | 乙提出對甲的 run 的 cancel | 被拒（不是甲的 run），沒有取消、沒有 `BUDGET` 列 | 自動：`P` |
| TC-059 | 同上 | 例外 | 同 TC-058 | 乙提出對甲的 run 的 resume | 被拒，沒有入列、沒有 `BUDGET` 列 | 自動：`P` |
| TC-060 | 專長守則「migration 可套用」；計畫 TC-M | 功能 | 舊資料庫（沒有 `users.auto_su_single`、`users.auto_su_month`、`confirmations.budget_note`），含既有使用者與確認列 | 以新程式開啟這個舊庫 | 三個新欄出現；既有列與既有設定值不變；所有人的兩個數字都是 NULL（＝未設），請求都回「待確認」 | 自動：`P` |
| TC-061 | 計畫作法 1「第二個進程先加了也算成功」 | 功能 | 資料庫已有新欄（或兩個進程同時補欄） | 再開啟一次、或模擬另一進程已補好欄 | 不報錯，欄位與資料不變 | 自動：`P` |
| TC-062 | 計畫「既有且釘住」`test_tcf10_f11`（schema 禁字） | 例外 | 新資料庫結構 | 掃描所有欄名 | 沒有名為 session 或 password 的欄位 | 自動：`platform/tests/test_human_channel.py`（`test_tcf10_f11`） |

## 區段 4 — 可見（每日摘要）、不變、不混淆（優先度 P2）

維護者原話：10-15 訪談「每一次免確認送出，都列在開發者的每日摘要裡」；Q20「樣本表由 LLM 產生、貼給使用者確認」（確認輸入，不算逐次確認 run）。計畫對應：TC-I、TC-J、TC-L。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-063 | 10-15 訪談；計畫作法 6、TC-J | 功能 | 已有 TC-005／006／007／009 產生的 BUDGET 列（共 4 筆） | 執行 `abf-platform auto-send list` | 4 筆都列出，一筆一行、tab 分隔、依時間排序，欄位依序為 `confirmed_at`、呼叫者名稱、種類、run 名稱、確認編號、`budget_note` | 自動：`P` |
| TC-064 | 計畫 TC-J「`--since` 過濾」 | 功能 | 同 TC-063，BUDGET 列分散在不同時間 | 執行 `auto-send list --since <某 ISO 時間>` | 只列出該時間（含）之後的列 | 自動：`P` |
| TC-065 | 計畫 TC-J「取消額度後仍能列歷史」 | 功能 | 同 TC-063，之後本人把兩個數字都清除 | 執行 `auto-send list` | 歷史 BUDGET 列仍然列出 | 自動：`P` |
| TC-066 | 計畫作法 6「沒有則印指定句」 | 功能 | 沒有任何 BUDGET 列 | 執行 `auto-send list` | 印出 `no budget-approved sends` | 自動：`P` |
| TC-067 | 計畫作法 6「唯讀」 | 功能 | 同 TC-063；先記下資料庫內容 | 執行 `auto-send list` | 資料庫內容完全不變（`confirmations`、`jobs`、`users`） | 自動：`P` |
| TC-068 | 計畫 TC-I；「不改任何 MCP 工具說明與 `FIXED_SENTENCE`」 | 功能 | 額度未設 | 讀所有 MCP 工具說明與 `FIXED_SENTENCE` | 與改前位元組相同（`test_resume_edit_params_words` 的兩句「does not start anything until the person says yes」「you cannot say it for them」一字不變） | 自動：`platform/tests/test_resume_edit_params_words.py`、`P` |
| TC-069 | 計畫 TC-I「網頁各頁 HTML 與基準比對」 | 功能 | 額度未設 | 取首頁、確認頁、runs 頁、設定頁 HTML | 首頁、確認頁、runs 頁與基準相同；設定頁除新增的兩個數字欄與「儲存」外與基準相同 | 自動：`P`、`test_web_*` 系列 |
| TC-070 | Q20；計畫 TC-L、裁決 E | 例外 | 使用者有一個待確認的樣本表（既有輸入確認步驟） | 本人確認樣本表 | `confirmations` 沒有因此新增任何 run 核准列；沒有工作入列 | 自動：`P` |
| TC-071 | 計畫 TC-L「額度內 launch 仍由 `budget.decide` 判定」 | 功能 | 樣本表已確認；兩數字都設，預估在額度內 | 提出 launch | 直接成立，記為 `BUDGET`（核准來自額度判斷，不是樣本表確認） | 自動：`P` |
| TC-072 | 計畫 TC-L「額度外的 launch 仍待確認」 | 例外 | 樣本表已確認；預估超過單次上限 | 提出 launch | 回「待確認」；樣本表確認不被當成 run 核准 | 自動：`P` |
| TC-073 | 計畫裁決 C「012a 開發模式不授予任何免確認」 | 例外 | 使用者的 `users.dev_mode`＝開（012a 個人開關），兩個 SU 數字未設 | 提出 launch、cancel | 回「待確認」；`git grep -n dev_mode` 顯示 `users.dev_mode` 與 `web_devmode.py` 既有函式語意未被改 | 自動：`P` |

## 區段 5 — 錯誤訊息與祕密（backend 專長守則）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-074 | 專長守則「錯誤訊息說明原因與處理方式」；計畫作法 3「回要確認，不報錯」 | 例外 | 任何要確認的情況（如 TC-011、TC-015、TC-017、TC-018、TC-019） | 看回給使用者／AI 的訊息 | 說明為什麼還要本人確認、使用者該怎麼做（例如到確認頁按好）；不含堆疊、內部路徑、SQL | 自動：`P` |
| TC-075 | 同上 | 例外 | TC-043～TC-047 的各種被拒情況 | 看被拒訊息 | 說明哪個值不合法或為何不能由此通道設定，以及應該怎麼做（例如本人登入後到設定頁修改）；不含堆疊、內部路徑、SQL | 自動：`P` |
| TC-076 | 專長守則「密鑰不得出現在日誌或回應」 | 例外 | 已有 BUDGET 列；使用者持有 token | 檢查 `budget_note`、`auto-send list` 輸出、請求與設定的回應與日誌 | 沒有 token、密碼或其他密鑰 | 自動：`P` |

## 區段 6 — 憲法 8.0.0 草案、文件、範圍

計畫對應：裁決 A、G、H；2026-11-10 裁決 1、2、4；「完成標準」。注意：計畫舊稿的「TC-076」對應本區段 TC-077、TC-078，「TC-085」對應 TC-086。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-077 | 2026-11-10 裁決 1、2；裁決 G | 功能 | 8.0.0 條目已寫入 `.specify/memory/constitution.md` | 讀 8.0.0 條目的 Approval 欄 | Approval 欄唯一內容是 `**Approval.** PENDING: 維護者尚未對修正案全文表示同意。合併前必須由維護者親口同意後補上其原話。`；不含任何維護者引言（也沒有「同意，但4)按照1)」） | 自動：`D` |
| TC-078 | 同上；A 級（放寬安全網）要維護者親口同意才能合併 | 功能 | 本片 PR | 查 PR 狀態 | PR 為 draft；沒有 `--auto`（自動合併）；沒有被合併 | 手動：`docs/TESTING.md`（執行者須在該檔手動部分寫出此步驟） |
| TC-079 | 裁決 G「新條目 `### 8.0.0 (<日期>)`，六段」；計畫 `D` 檔 | 功能 | 憲法檔 | 讀 8.0.0 條目與檔尾版本行 | 條目標題為 `### 8.0.0 (YYYY-MM-DD)`，含 Rationale、What changes、Sync Impact Report、Impact on existing deployments、Version（MAJOR）、Approval 六段；檔尾版本行的日期與條目標題日期是同一字串 | 自動：`D`、`tests/constitution_scope_test.sh` |
| TC-080 | 裁決 A 第 3、5 點；`D`「含 never 雲端與 forget」 | 功能 | 8.0.0 條目文字 | 讀 What changes | 明寫「never」：雲端（Google Batch 等）送出永遠要確認、`forget` 與清工作目錄永遠要本人；並如實寫出限制：比逐次確認弱、預估可能不準、自動續跑算入額度、cancel 在兩數字都設時不再逐次問；寫明它與 5.0.0／7.0.0「待確認請求、token、模型的回答不是通道」的關係；寫明設數字只有本人在設定頁 | 自動：`D` |
| TC-081 | 範圍「憲法只准改 I.2、Safety Net 規則與其 Check 行、新增 8.0.0 條目、檔尾版本行」 | 例外 | 憲法 diff（對 base） | 比對 diff | 只有上述段落有變動；`(today …)` 括號原文一字不動（`tests/constitution_6_test.sh` TC-045）；7.0.0 與更早條目一字不動 | 自動：`tests/constitution_6_test.sh`；ACCEPTANCE 讀 diff |
| TC-082 | 裁決 G「Check 行加 `test_budget_launch.py`（前綴 `test_bg`）」 | 功能 | 憲法 Safety Net 的 write-tool 規則 | 跑 `tests/constitution_checks_exist_test.sh` | Check 行含新測試檔且該檔存在，檢查通過 | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-083 | 裁決 G「更新釘住測試讓全套綠」 | 功能 | 憲法改完 | 跑 `tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`、`tests/charter_v4_workflow_test.sh`、`tests/dev_workflow_test.sh` | 全部通過；`PINNED_SN_SHA256` 與版本字串更新為新值，其他斷言沒有被刪或放寬 | 自動：以上各檔 |
| TC-084 | 計畫 `D`、`tests/operations_doc_test.sh` | 功能 | 文件（`docs/PLATFORM.md`、`docs/OPERATIONS.md`、`docs/TESTING.md`、`CHANGELOG.md`、`skills/launch/SKILL.md`） | 掃文件內每個 `abf-platform auto-send …` | 每個都對應真的 `sub.add_parser`；`skills/launch/SKILL.md` 只多一句，被釘的句子不動；`docs/adr/0006-…` 只加註 | 自動：`D`、`tests/operations_doc_test.sh` |
| TC-085 | 範圍「新測試檔首 40 行內 `# Nothing existing: <理由，≥15 字>`」 | 功能 | `platform/tests/test_budget_launch.py` | 跑 `test_scope.py`（TC-070） | 檔首 40 行內有 `# Nothing existing:` 且理由至少 15 字 | 自動：`platform/tests/test_scope.py` |
| TC-086 | 2026-11-10 裁決 4（`deploy/` 託管單元檔延後） | 功能 | `deploy/` 目錄 | 檢查 `deploy/`、`env.example` | 若 `deploy/` 下已存在含 `ABF_HOSTED` 的單元檔，其值為 1；`env.example` 無論如何不含 `ABF_HOSTED`；沒有單元檔則該項略過並註明；`tests/hosted_deploy_test.sh` 的 TC-016、TC-017、TC-007 一字不改且通過 | 自動：`D`、`tests/hosted_deploy_test.sh` |
| TC-087 | 範圍「只准改這些」與「不准碰」 | 例外 | 本片 diff（對 base） | `git diff --stat` | 只含「範圍：檔案」所列檔；`spec.md`、`test-case*.md`、`docs/ROADMAP.md`、`.github/`、`web_devmode.py` 既有函式沒有變動；既有釘住的測試只新增例外案例，沒有刪除或放寬斷言 | 自動：`D`（檔案清單）；ACCEPTANCE 讀 diff |
| TC-088 | 完成標準「全套 `tests/run_all.sh` 全綠」 | 功能 | 實作完成 | 在 WSL 跑 `tests/run_all.sh`（已知環境紅除外） | 全綠；完成記號 `GREEN <HEAD sha>` 與 HEAD 相符、工作樹乾淨 | 自動：`tests/run_all.sh` |
| TC-089 | 計畫「`test_tcm_47` 基準值更新逐條說明」 | 功能 | `platform/tests/test_chat_confirm.py` | 跑 `test_tcm_47_no_new_column_no_new_table` | 通過；基準結構雜湊、確認表欄位、路由清單更新為新值，分別明列新增的欄位（`auto_su_single`、`auto_su_month`、`budget_note`）與新路由（`POST /settings/budget`）；沒有改成只比部分 | 自動：`platform/tests/test_chat_confirm.py` |

## 區段 7 — 不在範圍（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-090 | 不做：第二片 Q31 自動續跑（裁決 D） | 不在範圍 | 本片程式碼 | `git grep -n auto_resume` 並看有沒有失敗偵測、自動續跑計數、「需要你處理」通知 | 都沒有；本片不自動續跑任何失敗的 run | 自動：`D` |
| TC-091 | 不做：Q20 樣本表由 LLM 產生 | 不在範圍 | 本片程式碼 | 檢查是否新增任何樣本表產生功能 | 沒有新增；只有「樣本表確認不等於 run 核准」的保證（TC-070） | 自動：`P`（TC-070）；ACCEPTANCE 讀 diff |
| TC-092 | 不做：產品模式取消免確認的最終答案（待維護者回答） | 不在範圍 | 本片程式碼與設定頁 | 檢查有沒有「產品模式／開發模式」切換影響 cancel | 沒有；cancel 只在兩數字都設時免確認，沒有第三個開關 | 自動：`P` |
| TC-093 | 不做：雲端與 forget、clean_work 的任何免確認路徑 | 不在範圍 | 程式碼原始檔 | AST 掃描 `request_forget`、`forget`、`clean_work` 與雲端分支內有沒有 `BUDGET` 或 `budget.decide` 的呼叫 | 都沒有 | 自動：`P` |
| TC-094 | 不做：以環境變數、MCP 工具、聊天頁、token、設定檔設額度；以終端機旗標開啟 | 不在範圍 | 一個未在設定頁設額度的使用者 | 設任何環境變數、設定檔項目、CLI 旗標，或用 MCP／聊天／token 想設額度 | 全部無效：沒有任何路徑寫入 `auto_su_*`，請求仍回「待確認」；`abf-platform` 沒有任何寫額度的子命令（`auto-send` 只有 `list`） | 自動：`P` |
| TC-095 | 不做：網頁終端機、OTP 轉送、新橫幅、改 `users.dev_mode` | 不在範圍 | 本片 diff | 檢查 diff 與設定頁、各頁 HTML | 沒有網頁終端機、OTP、新橫幅；012a 橫幅「國網運算不限制 SU」與 `users.dev_mode` 未改 | 自動：`P`（TC-069、TC-073）；ACCEPTANCE 讀 diff |
| TC-096 | 不做：`deploy/` 其他變動；MCP 工具說明與 `FIXED_SENTENCE` 的任何變動 | 不在範圍 | 本片 diff | `git diff --stat` 與 TC-068 | `deploy/` 沒有任何變動（託管單元檔延後，見 TC-086）；MCP 說明、`FIXED_SENTENCE`、`tools.json` 零變動；通知句只出現在請求回傳的 `_queued` 訊息 | 自動：`D`、`platform/tests/test_resume_edit_params_words.py` |

## 憲法與安全網

本片重新定義 I.2 與 Safety Net 的 write-tool／launch 規則（MAJOR），以下證明沒被它弄破的規則。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-097 | Safety Net write-tool 規則；I.2 check `test_tch09_*` | 功能 | 額度未設 | 跑 `test_tch09_nothing_reaches_the_queue_through_the_tools_without_a_person` 與 `test_confirm_page.py::test_tch09_b_c_*` | 通過，斷言未被放寬：沒有人按好時 `w.jobs() == []` | 自動：`platform/tests/test_human_channel.py`、`platform/tests/test_confirm_page.py` |
| TC-098 | Safety Net write-tool 規則：`launch`／`cancel`／`forget` 仍只認 TERMINAL／ELICITED／PAGE（含 CHAT 特例） | 功能 | 既有測試 | 跑 `test_actions_layer.py`（`REFUSED`、`test_tcb01/02/03/04–b09`、`test_srp_k01…`）、`test_human_channel.py::test_tca14`、`test_resume_entrypoints.py`（`test_tc142`、`test_tc144`）、`test_keep_submissions.py`（`test_tc034/037/038`） | 全部通過；`REFUSED = "no human confirmation channel"` 不變；AST 白名單只新增 `_ask`／`_request_attempt` 內的 BUDGET 呼叫點 | 自動：以上各檔 |
| TC-099 | I.2「沒有第二份執行狀態」；`tests/no_second_run_state_test.sh` | 功能 | 本片新增檔 | 跑 `tests/no_second_run_state_test.sh` | 通過；`LAUNCH_ALLOW` 名單與 28 個自測沒有放寬；上限存在使用者設定，不是執行狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-100 | Safety Net 憑證規則（密鑰不外洩） | 功能 | 本片新增的設定、摘要、回應 | 跑 `tests/credentials_stay_in_settings_test.sh` 與 `platform/tests/test_secrets.py` | 通過（對應 TC-076） | 自動：以上兩檔 |
| TC-101 | I.2 通道清單：「待確認請求、token、模型的回答不是通道」（5.0.0／7.0.0）對 BUDGET 的例外限於額度內 | 例外 | 兩數字都設 | 看 BUDGET 的所有產生路徑 | BUDGET 只由動作層預算分支在 `budget.decide` 回「直接成立」時產生；不能由使用者輸入、token、待確認請求本身或模型字串造成（對應 TC-036～TC-038、TC-054） | 自動：`P`、`platform/tests/test_actions_layer.py` |
