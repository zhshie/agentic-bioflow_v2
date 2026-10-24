# 測試案例：雲端費用（預估、記錄用量、每人每月上限，美元不換算）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Every row can be judged without reading code.
Language: 繁體中文; identifiers (TC-, T#, FR) and file paths stay as they are.
-->

**規格**：`specs/cloud-cost/plan.md`（本任務沒有獨立 spec.md；計畫含「維護者原話」與三段裁決，裁決與正文衝突時以裁決為準）　**總覽**：`test-case-overview.md`

說明：「T#」是計畫「失敗先行測試」裡的編號，方便對照。所有測試用的價目表、帳號、run 都是 `tmp_path` 裡的假資料（假價目：區域 `us-central1`；`n2-standard-4` standard 0.20／spot 0.06；`e2-standard-2` 只有 standard 0.10；沒有 `c9-fake-8`），不連網、不啟動任何程式。「雲端」指計算環境類型 `googlebatch-platform`（Google Batch）。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、標未知）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」。

## User Story 1 — 價目表與單一 task 算費（優先度 P1）

維護者原話：「費用顯示美元」「顯示雲端自己的幣別（美元）、不換算」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | T1；原話「費用顯示美元」 | 功能 | 假價目表；1 個 task：`n2-standard-4`、standard、跑了 36,000,000 毫秒（10 小時）、區域 `us-central1-a` | 算這個 task 的費用 | 費用 = 2.00 美元，幣別標 `USD` | 自動：`test_cloud_cost.py` T1 |
| TC-002 | T1 | 功能 | 同上，但計價模式改 spot | 算費用 | 費用 = 0.60 美元 | 自動：T1 |
| TC-003 | T2 | 功能 | task A（`n2-standard-4` standard，1.5 小時）、task B（`e2-standard-2` standard，2 小時） | 算整個 run | A = 0.30、B = 0.20，run 合計 0.50 美元 | 自動：T2 |
| TC-004 | 作法 3（大小寫不拘） | 功能 | 同 TC-002，但計價模式寫成 `SPOT`（另一例 `Standard`） | 算費用 | 視為 spot／standard，金額與小寫相同（0.60／2.00） | 自動：test_cloud_cost.py（新） |
| TC-005 | 作法 1（`as_of`） | 功能 | 價目表兩筆都被用到，`read_on` 分別是 2026-10-24 與 2026-10-25 | 算一個含這兩種機器的 run | 回傳的 `as_of` 是較舊的那個日期 2026-10-24 | 自動：test_cloud_cost.py（新） |
| TC-006 | T3 | 例外 | 一個 run 兩個 task：一個正常、一個機器型號 `c9-fake-8`（價目表沒有） | 算 run 費用 | 整個 run 的費用是「未知」（不是 0、不是只加正常那個的部分總和）；原因寫出 `c9-fake-8` 不在價目表 | 自動：T3 |
| TC-007 | T3 | 例外 | 一個 task 缺跑多久（`realtime_ms`） | 算費用 | 費用未知，原因說缺跑多久 | 自動：T3 |
| TC-008 | T3 | 例外 | 一個 task 缺計價模式 | 算費用 | 費用未知，原因說缺計價模式 | 自動：T3 |
| TC-009 | T3 | 例外 | 一個 task 計價模式是 `weird` | 算費用 | 費用未知，原因寫出看到的值 `weird` | 自動：T3 |
| TC-010 | T3；裁決三 5 | 例外 | 一個 task 沒有區域也沒有 zone | 算費用 | 費用未知，原因說缺區域 | 自動：T3 |
| TC-011 | T3 | 例外 | 一個 task 的區域（例如 `europe-west1-b`）不在價目表 | 算費用 | 費用未知，原因說該區域沒有價目 | 自動：T3 |
| TC-012 | 範圍 2（standard／spot 缺一就只缺那個） | 例外 | `e2-standard-2` 價目只有 standard；一個 task 是 `e2-standard-2` + spot | 算費用 | 費用未知（不是拿 standard 價充數） | 自動：test_cloud_cost.py（新） |
| TC-013 | 作法 3、裁決 9 | 例外 | 一個 task 有 `cpus = 4` 但沒有機器型號 | 算費用 | 費用未知；不會用 CPU 數猜成 `n2-standard-4` | 自動：test_cloud_cost.py（新） |
| TC-014 | T4 | 例外 | 價目檔裡 `n2-standard-4` 這筆沒有 `source` | 算 `n2-standard-4` 的 task | 視為機器型號不在價目表，費用未知 | 自動：T4 |
| TC-015 | T4 | 例外 | 這筆沒有 `read_on` | 同上 | 同上，費用未知 | 自動：T4 |
| TC-016 | T4 | 例外 | 這筆的 `source` 不是 `https://` 開頭 | 同上 | 同上，費用未知 | 自動：T4 |
| TC-017 | T4 | 例外 | 這筆的 `read_on` 不是 `YYYY-MM-DD` 格式 | 同上 | 同上，費用未知 | 自動：T4 |
| TC-018 | 作法 1（`load_rates`） | 例外 | 價目檔不存在，或內容是 JSON 陣列而不是物件 | 載入價目表 | 回傳 `None`，不丟堆疊 | 自動：test_cloud_cost.py（新） |
| TC-019 | T5 | 功能 | 隨程式出貨的 `platform/abf_platform/data/cloud_rates.json` | 檢查檔案 | `currency` 是 `USD`；至少一個區域、一個機器型號；所有費率是大於 0 的有限數字；有 spot 的型號 spot 小於 standard | 自動：T5 |
| TC-020 | T5；範圍 2 | 功能 | 同上 | 檢查每一筆 | 每筆都有 `https://` 開頭的 `source` 與合法日期的 `read_on`，日期不晚於今天 | 自動：T5 |
| TC-021 | T5 | 功能 | 同上 | 檢查日期 | 所有 `read_on` 都不早於 2026-10-24（證明是這次讀頁面填的，不是舊記憶） | 自動：T5 |
| TC-022 | T5；維護者原話「不換算」 | 不在範圍 | 同上 | 搜尋檔案內容 | 沒有 `TWD`、`NT$`、`exchange`、`匯率` | 自動：T5 |
| TC-023 | 完成標準（價目表是真資料）；憲法第 9 條 | 功能 | 出貨價目檔 | 驗收者隨機抽 3 筆，打開該筆 `source` 網址核對頁面數字 | 3 筆的網址打得開且數字與檔內相符；打不開的標「未驗證」不算通過 | 手動：`docs/TESTING.md` cloud-cost 小節 |

## User Story 2 — 預估這次約花多少、算出本月已用（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | T6 | 功能 | 使用者甲有兩個同 pipeline、跑在 Google Batch 的成功 run：舊的 3.40 美元、新的 2.50 美元 | 預估甲再送同 pipeline | 預估 2.50 美元，`basis` 指到新的那個 run | 自動：T6 |
| TC-025 | T6（跨使用者） | 例外 | 另有使用者乙同 pipeline 的成功 run | 預估甲 | 乙的 run 不被採用 | 自動：T6 |
| TC-026 | T6 | 例外 | 甲另有不同 pipeline 的成功 run | 預估甲送 pipeline X | 不同 pipeline 的 run 不被採用 | 自動：T6 |
| TC-027 | T6、裁決 8 | 例外 | 甲最近一次同 pipeline 的 run 是失敗的（且比成功的新） | 預估 | 失敗的 run 不被採用，仍用成功的那個 | 自動：T6 |
| TC-028 | T6 | 例外 | 甲有同 pipeline 的成功 run，但跑在 Slurm | 預估 | Slurm 的 run 不被採用 | 自動：T6 |
| TC-029 | 作法 1（預估）、裁決 8 | 功能 | 被採用的成功 run 裡有一個失敗重試的 task 也有跑多久與機器型號 | 預估 | 該重試 task 的錢也算進預估 | 自動：test_cloud_cost.py（新） |
| TC-030 | 作法 1（「算得出 usd 的 run」） | 功能 | 甲最新的成功 run 算不出費用（機器型號不在價目表），較舊的成功 run 算得出 | 預估 | 預估用較舊且算得出的那個 run | 自動：test_cloud_cost.py（新） |
| TC-031 | T7、裁決 3 | 例外 | 甲從沒成功跑過這個 pipeline 的雲端 run | 預估 | 預估是「未知」，原因含「還沒有成功跑過」；不給任何數字 | 自動：T7 |
| TC-032 | T7、裁決 3；replan「無歷史用 resourceLimits 保守估」被明確不採 | 不在範圍 | 沒有歷史，但設定裡有 `resourceLimits`／`maxvCpus` | 預估 | 仍是「未知」，沒有任何由 `resourceLimits`／`maxvCpus` 推出的數字 | 自動：T7 |
| TC-033 | 作法 1（`run_tasks_cost`） | 例外 | 一個舊索引（task 紀錄沒有機器型號那幾欄）的 run | 算這個 run 的費用 | 費用未知，原因含「這個 run 的紀錄沒有保存機器型號」 | 自動：test_cloud_cost.py（新） |
| TC-034 | 裁決三 5 | 功能 | task 沒有 zone，但該 run 的計算環境設定了 location `us-central1` | 經 `month_used` 或 `estimate_launch` 算 | 以 `us-central1` 計價，算得出金額 | 自動：T6／T9 變體 |
| TC-035 | 裁決三 5 | 例外 | task 沒有 zone，計算環境也沒有 location | 同上 | 費用未知（原因說缺區域） | 自動：同上 |
| TC-036 | T9 | 功能 | 甲的雲端 run 啟動於 `2026-09-30T16:30:00Z`（台北時間 2026-10-01 00:30） | 算 `2026-10` 的已用 | 這個 run 算進 2026-10 | 自動：T9 |
| TC-037 | T9 | 例外 | 同上 | 算 `2026-09` 的已用 | 這個 run 不算進 2026-09 | 自動：T9 |
| TC-038 | T9（跨使用者） | 例外 | 乙在同月有雲端 run | 算甲的已用 | 乙的 run 不算 | 自動：T9 |
| TC-039 | T9 | 例外 | 甲在同月有 Slurm 的 run | 算甲的已用 | Slurm 的 run 不算 | 自動：T9 |
| TC-040 | 作法 1（最新一次送出的環境） | 例外 | 甲的某個 run 先送雲端、最新一次改送 Slurm | 算已用 | 不算（以最新一次送出的環境為準） | 自動：test_cloud_cost.py（新） |
| TC-041 | T9、裁決 8 | 功能 | 甲的雲端 run 裡有狀態 FAILED 但有跑多久的 task | 算已用 | 失敗 task 的錢也算進已用 | 自動：T9 |
| TC-042 | 作法 1（`month_used`） | 功能 | 甲本月兩個雲端 run：一個算得出（3.00 美元）、一個算不出 | 算已用 | 已用 = 3.00 美元（只加算得出的），`unknown_runs` = 1；整個月不會因此變成未知 | 自動：test_cloud_cost.py（新） |

## User Story 3 — 每人每月上限擋下新的雲端送出（優先度 P1）

維護者原話：「費用顯示美元、每人每月上限」；拒絕要「顯示『約 US$X，本月已用 $Y／上限 $Z』」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-043 | T8 | 功能 | 甲上限 20.00、本月已用 14.50、這次預估 2.00 | 問 `cap_problem`（要不要擋） | 放行（回 `None`） | 自動：T8 |
| TC-044 | T8；原話「約 US$X，本月已用 $Y／上限 $Z」 | 功能 | 上限 20.00、已用 14.50、預估 6.00 | 同上 | 拒絕；文字含 `US$20.00`、`US$14.50`、`US$5.50`、`US$6.00` | 自動：T8 |
| TC-045 | 作法 4（拒絕文字） | 例外 | 同 TC-044 | 看拒絕文字 | 白話說「會超過」並說明該怎麼辦：找管理者調整上限，或下個月再送出 | 自動：T8 |
| TC-046 | T8 | 功能 | 已用 14.50、預估剛好 5.50（合計剛好 20.00） | 同上 | 放行（剛好等於上限不擋） | 自動：T8 |
| TC-047 | T8 | 例外 | 已用 20.00（用滿）、預估算不出來 | 同上 | 拒絕（已用滿一律擋，不論預估） | 自動：T8 |
| TC-048 | 作法 4 | 例外 | 同 TC-047 | 看拒絕文字 | 文字寫出已用約 `US$20.00`、剩 `US$0.00`、這個月不能再送出新的雲端分析 | 自動：T8 |
| TC-049 | T8 | 功能 | 已用 14.50、預估算不出來（還有剩） | 同上 | 放行（預估未知不阻擋） | 自動：T8 |
| TC-050 | T8 | 例外 | 管理者把上限設成 0 | 同上 | 拒絕（上限 0 等於不准） | 自動：T8 |
| TC-051 | T8、裁決 4 | 例外 | 管理者從沒替這位使用者設上限 | 同上 | 拒絕；文字說明管理者還沒設每月雲端上限，並提到 `cloud-cap` 指令 | 自動：T8 |
| TC-052 | T8 | 例外 | 本月有 1 個 run 算不出費用 | 問 `cap_problem` 並走到拒絕 | 「已用」寫成「至少 US$X」，並含「1 個 run」算不出來的說明 | 自動：T8 |
| TC-053 | 作法 4 | 功能 | 任一拒絕情境，金額含 5.5（非整數） | 看拒絕文字 | 所有金額都寫成 `US$` 加兩位小數（如 `US$5.50`） | 自動：T8 |
| TC-054 | T12；作法 1 | 功能 | 計算環境是 Slurm（nano4）；讓讀價目、讀上限、開資料庫的函式一被呼叫就丟錯 | 問 `cap_problem` | 回 `None`，且上述函式都沒被呼叫（nano4 的送出完全不受影響） | 自動：T12 |
| TC-055 | 作法 1（「或任何別種」）；原話「只做 Google Batch」 | 功能 | 計算環境是 `googlebatch-platform` 以外的其他類型 | 問 `cap_problem` | 回 `None`，不讀價目表與上限 | 自動：T12 變體 |
| TC-056 | 裁決三 8 | 功能 | 甲有 pipeline A（成功 2.00 美元）與 pipeline B（成功 9.00 美元）的歷史；上限 20、已用 14 | 分別以 `bundle["pipeline"]` 為 A 與 B 問 | A 放行、B 拒絕（預估取自 bundle 指名的 pipeline） | 自動：T8／T6 變體 |
| TC-057 | 跨使用者（專長守則）；範圍外「無實驗室共用上限」 | 功能 | 甲已用 19.90（上限 20）；乙同一實驗室、上限 20、本月沒用 | 乙問 `cap_problem` | 乙不受甲的用量影響，放行 | 自動：test_cloud_cost.py（新） |
| TC-058 | 跨使用者 | 例外 | 甲有上限、乙沒有上限 | 乙問 `cap_problem` | 乙被拒絕（沒有設定），不會借用甲的上限 | 自動：test_cloud_cost.py（新） |
| TC-059 | 確認管道（專長守則）；作法 1 | 功能 | 記下 `jobs`、`confirmations`、`task_usage`、`cloud_caps` 各表列數 | 對放行與拒絕各問一次 `cap_problem` | 各表列數與內容完全沒變（它只是問，不寫入） | 自動：test_cloud_cost.py（新） |
| TC-060 | T17；專長守則（錯誤訊息） | 例外 | 任一拒絕情境（含 CLI 拒絕壞數字） | 檢查文字 | 不含 `Traceback`、`SELECT`、`.db`、測試暫存路徑字串、token | 自動：T17 |

## User Story 4 — 只有管理者能設上限（優先度 P1）

維護者原話：「每人每月上限由管理者開帳號時設」；計畫：使用者改不了。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-061 | T11 ① | 功能 | 平台主機終端機 | 執行 `abf-platform user add <名> --lab <lab> --cloud-cap-usd 20` | 帳號建立，讀回上限 = 20 美元 | 自動：T11 |
| TC-062 | T11 ① | 功能 | 已有該帳號 | 執行 `abf-platform user cloud-cap <名> 25` | 讀回上限 = 25 美元（可調整） | 自動：T11 |
| TC-063 | 作法 6、裁決 4 | 功能 | 執行 `user add` 但不給 `--cloud-cap-usd` | 讀回上限 | 沒設（`None`），程式沒有寫死的預設值 | 自動：T11 |
| TC-064 | T11 ② | 例外 | 帳號已有上限 20 | `user cloud-cap <名> -1` | 被拒絕並白話說明；上限仍是 20 | 自動：T11 |
| TC-065 | T11 ② | 例外 | 同上 | `user cloud-cap <名> abc` | 同上 | 自動：T11 |
| TC-066 | T11 ② | 例外 | 同上 | `user cloud-cap <名> nan` | 同上 | 自動：T11 |
| TC-067 | T11 ② | 例外 | 同上 | `user cloud-cap <名> inf` | 同上 | 自動：T11 |
| TC-068 | T11 ② | 例外 | 同上 | `user cloud-cap <名> 1e9` | 同上（超過 1,000,000） | 自動：T11 |
| TC-069 | 作法 6（上限 1,000,000） | 例外 | 同上 | `user cloud-cap <名> 1000001` | 被拒絕，上限不變 | 自動：test_cloud_cost.py（新） |
| TC-070 | 作法 6（「超過」才拒絕） | 功能 | 同上 | `user cloud-cap <名> 1000000` | 接受，讀回 1,000,000 | 自動：test_cloud_cost.py（新） |
| TC-071 | 作法 6（大於等於 0） | 功能 | 同上 | `user cloud-cap <名> 0` | 接受，讀回 0 | 自動：test_cloud_cost.py（新） |
| TC-072 | 專長守則（錯誤訊息） | 例外 | 同 TC-064 至 TC-068 | 看拒絕訊息 | 說明哪個值不合法、可接受的範圍（0 到 1,000,000 美元）；無堆疊、路徑、SQL | 自動：test_cloud_cost.py（新） |
| TC-073 | T11 ②（資料庫沒變） | 例外 | 沒有叫 `newbie` 的帳號 | `user add newbie --lab x --cloud-cap-usd abc` | 被拒絕，且沒有建立 `newbie` 這個帳號 | 自動：T11 |
| TC-074 | T11 ③、T14 | 功能 | 列舉 MCP 工具 | 對照名稱 | 仍是 12 個；名稱沒有 `cloud_cap`／`cloud-cap`／`cap_usd` | 自動：T11／T14 |
| TC-075 | T11 ③ | 功能 | 列舉 `web.py`、`web_board.py` 的路由字串 | 對照 | 沒有任何含 `cloud_cap`／`cloud-cap`／`cap_usd`；沒有新增網頁路由 | 自動：T11／T14 |
| TC-076 | T11 ③ | 功能 | 列舉 `actions` 公開名稱 | 對照 | 沒有任何含上述字樣，也沒有新增公開函式 | 自動：T11 |
| TC-077 | T11 ④；跨使用者讀 | 例外 | 甲的上限設成特別的數字 777.77；乙與甲各有 PAT（個人存取憑證） | 乙、甲各用自己的 PAT 呼叫每一個現有工具／網頁讀取 | 任何回應都讀不到 777.77（別人的或自己的上限） | 自動：T11 |
| TC-078 | 專長守則（跨使用者寫）；作法 6 | 例外 | 乙持有自己的 PAT | 對現有每個 MCP 工具與網頁路由，帶上名為 `cloud_cap_usd`／`cap_usd` 的欄位 | `cloud_caps` 表沒有任何變動（沒有任何入口能寫上限） | 自動：test_cloud_cost.py（新） |
| TC-079 | 專長守則（對等性） | 功能 | 本任務沒有新增使用者動作 | 跑 `test_web_parity.py` | 通過，且 `INTERNAL`／`OWED` 清單沒被改動 | 自動：`test_web_parity.py` |

## User Story 5 — 記下每個 task 用了什麼機器；舊資料庫能升級（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | T15、裁決三 5 | 功能 | 送一個 task 完成事件：`machineType: "n2-standard-4"`、`priceModel: "spot"`、`cloudZone: "us-central1-a"` | 接收端存入 | `task_usage` 該列三欄值正確 | 自動：T15 |
| TC-081 | T15 | 例外 | `machineType: null` | 存入 | 該欄為 NULL | 自動：T15 |
| TC-082 | T15 | 例外 | `machineType: 7`（不是字串） | 存入 | 該欄為 NULL | 自動：T15 |
| TC-083 | 作法 5 | 例外 | `priceModel` 不是字串 | 存入 | 該欄為 NULL | 自動：T15 |
| TC-084 | 作法 5（截 64 字） | 例外 | `machineType` 與 `priceModel` 各 100 字 | 存入 | 各截成 64 字 | 自動：T15 |
| TC-085 | T15、作法 5 | 功能 | 同 TC-080 的事件 | 存入 | `cpus`、`realtime_ms`、`queue` 與改動前一模一樣 | 自動：T15 |
| TC-086 | 作法 5（本機／nano4） | 功能 | 本機或 nano4 的事件（三個新欄位本來是 `null`） | 存入 | 三欄為 NULL | 自動：T15 |
| TC-087 | T15 標題「only … new columns」 | 功能 | 新建資料庫 | 讀 `task_usage` 欄位 | 比改動前恰好多 `machine_type`、`price_model`、`cloud_zone` 三欄，沒有別的 | 自動：T15 |
| TC-088 | T16 | 功能 | 舊結構的索引資料庫（沒有那三欄） | 開啟 | 補上三欄 | 自動：T16 |
| TC-089 | T16 | 功能 | 舊結構的 `tokens.db`（沒有 `cloud_caps`） | 開啟 | 補上 `cloud_caps` 表 | 自動：T16 |
| TC-090 | T16 | 例外 | 兩個行程同時對舊資料庫補欄位 | 同時開啟 | 都不報錯（被別人搶先補了就放過） | 自動：T16 |
| TC-091 | T16 | 功能 | 舊資料庫已有若干 task 列 | 升級後讀 | 舊列內容原樣，新欄為 NULL | 自動：T16 |
| TC-092 | 既有斷言更新；範圍外「無實驗室／角色／群組上限」 | 功能 | `test_web_actions.py` 的 `SCHEMA` | 跑 `test_tc063_no_schema_change` | `tokens.cloud_caps` 欄位恰為 `user_id`、`cap_usd`、`set_at`（以人為單位，沒有 lab／role／group 欄）；`platform.db` 與 `tokens` 其他表不變 | 自動：`test_web_actions.py` |

## User Story 6 — 不在範圍（確認真的沒做，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-093 | T13；原話「超過自動停」本任務不做 | 不在範圍 | `abf_platform/` 原始碼 | 搜尋 | 沒有 `watchdog`、`POLICY` | 自動：T13 |
| TC-094 | T13 | 不在範圍 | `jobs.py` | 看 `kind` 檢查清單 | 仍是原來六種，沒有新增 | 自動：T13 |
| TC-095 | T13 | 不在範圍 | `confirm.py` | 看確認種類 | 沒有新增種類 | 自動：T13 |
| TC-096 | T13 | 不在範圍 | `cloud_cost.py` | 搜尋 | 沒有 `enqueue_cancel`、`cancel_run` 字樣 | 自動：T13 |
| TC-097 | 目標 4（只擋新的送出） | 不在範圍 | 甲有一個正在跑的雲端 run，且本月已用已超過上限 | 問 `cap_problem` 得到拒絕 | `jobs` 表沒有新增任何取消工作，正在跑的 run 狀態不變 | 自動：test_cloud_cost.py（新） |
| TC-098 | T10；原話「不換算、NT$1,000 只是 GCP 帳單預算」 | 不在範圍 | `cloud_cost.py`、`data/cloud_rates.json` | 搜尋 | 都沒有 `NT$`、`TWD`、`新台幣`、`匯率`、`exchange rate` | 自動：T10 |
| TC-099 | T10 | 不在範圍 | 各種拒絕文字 | 搜尋 | 沒有上述字樣 | 自動：T10 |
| TC-100 | T10 | 不在範圍 | `docs/CLOUD.md` | 搜尋 | 沒有 `NT$`；沒有「數字金額＋台幣」；只允許以「台幣」二字說明 GCP 帳單預算不是平台上限 | 自動：T10 |
| TC-101 | T14、不做第 8 項 | 不在範圍 | `platform/pyproject.toml` | 看相依 | 沒有 `google-cloud`，沒有新相依 | 自動：T14 |
| TC-102 | T14；不去讀真實帳單 API | 不在範圍 | `abf_platform/` 原始碼 | 搜尋 | 沒有 `import google`、`boto3`（也沒有 AWS／Azure／K8s 的價目或上限） | 自動：T14 |
| TC-103 | 作法 8 | 不在範圍 | 跑 `test_su_in_get_run.py` | 看 `get_run` 回傳 | 形狀不變、測試未修改；回傳裡沒有「已用美元」 | 自動：`test_su_in_get_run.py` |
| TC-104 | 完成標準（Slurm 一個位元都不變） | 不在範圍 | 既有 Slurm 送出／內容包／畫面的測試 | 全部執行 | 全綠，且未被修改 | 自動：既有測試 |
| TC-105 | T14（手動）、完成標準 | 不在範圍 | 本任務分支 | 驗收者看 `git diff --name-only origin/v3...HEAD` | 不含 `platform/abf_launch/build.py`、`platform/abf_station/launch.py`、`platform/abf_platform/actions/__init__.py`、`platform/abf_platform/pipeline_launch.py`、`pyproject.toml`、`setup.py`、`su.py`、`records.py`、`jobs.py`、`compute_envs.py`、`abf_launch/`、`abf_station/`；只含計畫「範圍：檔案」列的檔 | 手動：驗收者閱卷時做 |
| TC-106 | 裁決二 1（不接線）、待裁決 A/B | 不在範圍 | `request_launch` 與 gcb 確認畫面 | 跑 `test_gcb_launch.py`（含 :726 附近的費用字樣） | 全綠；畫面仍寫「平台目前還沒有費用預估與上限」；`request_launch` 並未呼叫 `cap_problem` | 自動：`test_gcb_launch.py` |

## User Story 7 — 文件與維護者手動驗收（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-107 | T18、裁決 7 | 功能 | `docs/CLOUD.md` | 讀 | 存在，白話寫明「只含運算（虛擬機）費用」，磁碟、網路、儲存都不算，數字用「約」 | 自動：T18 |
| TC-108 | T18 | 功能 | 同上 | 讀 | 寫明預估怎麼來（取同使用者、同 pipeline、最近一次成功的雲端 run） | 自動：T18 |
| TC-109 | T18 | 功能 | 同上 | 讀 | 寫出設定上限的兩條指令：`user add … --cloud-cap-usd`、`user cloud-cap <名> <美元>` | 自動：T18 |
| TC-110 | T18、完成標準 | 功能 | 同上 | 讀 | 白話寫明「目前不會自動停止正在跑的雲端工作，只會擋下新的送出」 | 自動：T18 |
| TC-111 | T18、原話「NT$1,000 只是 GCP 帳單預算」 | 功能 | 同上 | 讀 | 說明 GCP 帳單預算（台幣）與平台上限的關係：帳單預算不是平台的上限（用「台幣」二字，不寫 `NT$`） | 自動：T18 |
| TC-112 | T18 | 功能 | 同上 | 讀 | 寫明價目表怎麼更新 | 自動：T18 |
| TC-113 | T18 | 功能 | 同上 | 讀 | 寫明每筆價目必須有 `source`（`https://`）與 `read_on`（`YYYY-MM-DD`） | 自動：T18 |
| TC-114 | 範圍：`docs/PLATFORM.md` | 功能 | `docs/PLATFORM.md` | 讀 | 「What the platform stores」表有 `cloud_caps` 與 `task_usage` 新欄；「Money」一段指向 `docs/CLOUD.md`；`user add` 說明有 `--cloud-cap-usd` | 手動：驗收者閱卷時讀文件 |
| TC-115 | 完成標準（文件） | 功能 | `docs/TESTING.md` | 讀 | 有「cloud-cost」小節，含手動驗收 1 至 4 | 手動：`docs/TESTING.md` |
| TC-116 | 手動 1 | 功能 | 維護者自己的帳號，GCP 帳單預算與警示已設 | 執行 `user add <名> --lab <lab> --cloud-cap-usd 5`（或 `user cloud-cap <名> 5`） | 帳號上限 5 美元 | 手動：`docs/TESTING.md` |
| TC-117 | 手動 2 | 功能 | 在 `gcb1` 跑一次最小分析 | 看 `index.db` 的 `task_usage` | 有 `machine_type`、`price_model`（若是 NULL，代表 Nextflow 沒送，停下回報，不改成猜） | 手動：`docs/TESTING.md` |
| TC-118 | 手動 3；原話「花費控制」 | 功能 | 同上 | 用 `cloud_cost` 算這個 run 的美元，與 Google Cloud Console 同時段 Compute Engine 費用比 | 差距寫進 ledger（預期略低；差太多回報，不自己調價） | 手動：`docs/TESTING.md` |
| TC-119 | 手動 4 | 功能 | 把上限暫時設成低於「已用＋預估」 | 問 `cap_problem` | 回白話拒絕，數字正確 | 手動：`docs/TESTING.md` |
| TC-120 | 裁決 3 | 功能 | `docs/CLOUD.md` | 讀 | 寫明缺口：第一次跑某 pipeline 沒有歷史，上限只擋得住「已用滿」、擋不住「這一次太貴」，並建議首位使用者上限設小（例如 5 美元） | 手動：驗收者閱卷時讀文件 |
| TC-121 | 環境事實（週期） | 功能 | `docs/CLOUD.md` | 讀 | 有一句說明月份用台北時間，Google 帳單以太平洋時間切月，月初月末最多差約半天 | 手動：驗收者閱卷時讀文件 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-122 | 第 1 條（先查有沒有現成的） | 功能 | `cloud_cost.py`、`test_cloud_cost.py` | 看前 40 行 | 都有 `# Nothing existing:` 加至少 15 字理由（`test_scope.py` TC-070） | 自動：T18、`test_scope.py` |
| TC-123 | 第 2 條（不得有第二條送出路徑／監看程式） | 例外 | `cloud_cost.py` 與 `store.py`／`receiver.py`／`cli.py` 的新增碼 | 掃描 | 沒有 `subprocess`、`Popen`、`os.system`、`threading`、`while True`、`nohup`、`setsid`、`ssh`、`import requests`、`urllib.request`、`socket` | 自動：`test_scope.py` TC-061、TC-071 |
| TC-124 | `station` 一字禁令（TC-061） | 例外 | 新增的 `.py` 檔與新增碼（含註解與字串） | 逐行搜尋 `station`（不分大小寫） | 沒有任何一行含 `station`，也沒有拆字串規避 | 自動：T18、`test_scope.py` TC-061 |
| TC-125 | 第 2 條 | 功能 | 全部改動 | `bash tests/no_second_run_state_test.sh` | 通過 | 自動：`tests/no_second_run_state_test.sh` |
| TC-126 | 第 2 條（索引可由 Nextflow 紀錄重建） | 功能 | 全部改動 | 跑 `test_tc030_rebuild_gives_back_every_field`、`test_tc031_nextflows_records_win_over_a_damaged_index` | 兩個都通過 | 自動：`test_nextflow_e2e.py` |
| TC-127 | 第 3 條（不寫死路徑） | 功能 | 價目檔路徑由 `__file__` 推出 | `bash tests/no_hardcoded_paths.sh` | 通過 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-128 | 第 6 條（`configs/` 只准 `sites`） | 功能 | 價目表放 `platform/abf_platform/data/cloud_rates.json` | `bash tests/no_per_pipeline_config.sh` | 通過；`configs/` 下沒有 `cloud/` | 自動：`tests/no_per_pipeline_config.sh` |
| TC-129 | 安全網（憑證只在設定檔） | 功能 | 全部改動 | `bash tests/credentials_stay_in_settings_test.sh` | 通過 | 自動：該 sh |
| TC-130 | 計畫「必須更新的既有斷言」 | 不在範圍 | `test_gcb_ce.py`、`test_web_actions.py` 的 diff | 驗收者逐行對照 base | `test_gcb_ce.py` 只改 `{"cloud_cost.py", "rates.json"}` 成 `{"rates.json"}` 一處；`test_web_actions.py` 只加 `tokens.cloud_caps` 一列與註解；其他既有測試一律未改（沒有放寬、刪除、跳過） | 手動：驗收者閱卷時做 |
| TC-131 | 計畫「確認不會變紅」清單 | 功能 | 全部改動 | 跑 `test_su_in_get_run.py`、`test_estimate_su.py`、`test_su_packaged.py`、`test_pat.py`（:700 `users` 仍六欄、:383）、`test_human_channel.py`、`test_station_envs.py::test_tc086`、`test_web_parity.py`、`test_guidance.py`、`test_oauth_mcp.py`、`test_gcb_launch.py`、`test_scope.py` | 全綠 | 自動：上述各檔 |
| TC-132 | 既有斷言更新理由 | 功能 | 本任務建了 `cloud_cost.py` 與 `cloud_rates.json` | 跑 `test_gcb_ce.py::test_nothing_of_the_later_slices_exists` | 通過；`cloud_cost.py` 不再被禁，名為 `rates.json` 的檔仍被禁（我們的檔叫 `cloud_rates.json`，不撞） | 自動：`test_gcb_ce.py` |
| TC-133 | 完成標準 | 功能 | 全部改動，已提交 | 全套（含 `tests/platform_test.sh`）在 WSL 跑 `tests/run_all.sh` | 全綠 | 自動：`tests/run_all.sh` |
