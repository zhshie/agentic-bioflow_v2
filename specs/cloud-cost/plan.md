---
id: cloud-cost
title: 雲端費用：預估、記下已用、每人每月上限擋下新的送出（只用雲端自己的幣別 USD，不換算）
tier: B
kinds: backend
lane: L7-cloud（共用檔 store.py／receiver.py／cli.py 屬 L2，不可與 L2 任務平行）
base: v3（C-1 `gcb-ce-type`、C-2 `gcb-launch` 已合併；本任務從現在的 v3 開分支）
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 3 的 C-3 `cloud-cost`（拷問 10-21 第二輪第 10 點）；姊妹模組 `platform/abf_platform/su.py`（`estimate-su` 系列）
---

# cloud-cost

> 本檔由 developer-agent 寫（2026-10-24）。**只處理 C-3 的前半**：①預估一次雲端 run 約花多少美元、②記下每個 task 實際用了什麼機器（讓「已用」算得出來）、③每人每月上限擋下新的送出。**自動停（watchdog，會自己建取消工作）不在本任務**，那是還沒裁決的 C 級問題（見裁決 1）。B 級（使用者看得到的新能力）→ verifier 通過＋CI 綠由 developer-agent 自合。
> **車道注意**：本任務改 `store.py`、`receiver.py`、`cli.py`（L2 共用檔），不可與其他動這幾個檔的任務平行；更不可與執行中的 `017d-launch-composed` 同時動它的四個檔（裁決 5）。
> **這份計畫與 replan 原文有四處不同**，都是對照 v3 現況後的修正：①費率檔不放 `configs/cloud/rates.json`（憲法測試禁止，見裁決 2）；②原文把「`request_launch` 在 `_ask` 前擋下」當成本任務的一部分，但那個呼叫點在 017d 執行中的禁改檔裡，改列「待 developer-agent 裁決」；③原文的自動停（watchdog／`POLICY` 確認通道）整段不做（裁決 1）；④原文說 `ADR 0009` 定了美元不換算，**v3 的 `docs/adr/0009` 是網頁版面三欄，不是費用**，依據只有維護者 10-18／10-21 的原話（見「環境事實」）。

## 目標
讓管理者開帳號時給每位使用者一個「每月雲端費用上限（美元）」；使用者要在 Google Batch 環境送出新的分析時，平台先用雲端自己的價目表（美元，不換算）估這次約多少、加上本月已經花的，若會超過上限，就在**建立任何東西之前**用白話拒絕，並寫明「上限、已用、剩下」各是多少美元。

為什麼這樣切：
1. 維護者要的是「顯示雲端自己的幣別、不換算、每人每月上限由管理者設」；NT$1,000 只是 GCP 帳單那邊的預算，不是平台的上限，所以平台程式裡**不得出現台幣或匯率**。
2. 「已用」不能憑空算：現有 `task_usage` 只記 `cpus／realtime／queue`（給 SU 用），沒有「這個 task 在哪種機器上、是不是 spot」，所以要先讓接收端（receiver）多存這兩欄，才算得出美元。
3. 價目表是**資料**不是程式碼（跟 `su.py` 同一套做法）：每一筆都帶來源網址與讀取日期；查不到的機器型號就標「未知」並說原因，不猜、不補 0。
4. 攔下的是「新的送出」；已經在跑的 run 不會被這個任務停掉（停掉別人正在跑的東西是另一個、還沒裁決的問題）。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`（行號為該檔現況）。每句至少對應一條測試案例（對應見「失敗先行測試」的標記）：
- 「Google Batch 雲端：等你開好 GCP 帳號（預算 NT$1,000）；費用顯示美元、每人每月上限、超過自動停。接著 AWS Batch、Azure／K8s。」（第 16 行）→ 顯示美元（T1、T9）；每人每月上限（T6–T8）；「超過自動停」**本任務不做**，見裁決 1（T13 鎖住「沒有偷做」）。
- 「雲端費用**照 10-18 裁示**：顯示雲端自己的幣別（美元）、不換算、每人每月上限由管理者開帳號時設，NT$1,000 只是 GCP 帳單預算」（第 46 行，裁示 10 的一部分）→ 不換算（T10）；上限由管理者在開帳號時設、使用者改不了（T11）；NT$1,000 不是平台的上限（T10 檢查平台原始碼沒有 `NT$`／`TWD`／匯率）。
- 「4. 四種計算環境都建：nano4 → Google Batch（開發上限 NT$1,000/月）→ AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行，裁示 4）→ 只做 Google Batch；AWS／Azure／K8s 的價目與上限不在本任務（T14）。
- 「12. （10-21 拷問）雲端第一個真實使用者＝他自己的自費帳號；收費理由＝「不用自己架、有人維護」（託管＋支援，每實驗室固定月費，像 Seqera）；年底若只能交兩塊＝**雲端跑通＋花費控制**與**網頁全流程（國網）**，畫布與聊天排年後」（第 50 行）→ 這一條就是「花費控制」的來源；手動驗收要在他自己的帳號上用真實價目表算一次（完成標準手動第 3 步）。
- 「14. （10-21 拷問三）**B 級部分自合**：網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併，事後列進每日清單」（第 54 行）→ 本任務不改網頁畫面（T14）。
- 「**C-3 `cloud-cost`**（B／backend）：`platform/abf_platform/cloud_cost.py`（`su.py` 姊妹）＋`configs/cloud/rates.json`（以雲端自己的幣別計，美元；**不換算**，ADR 0009）；預估＝同管線最近成功 run 的 core-hours × 費率，無歷史用 `resourceLimits` 保守估；settings `cloud_cap_usd_per_person_month`（管理者開帳號時設，使用者不能改）；`request_launch` 在 `_ask` 前：估計＋當月已花 > cap → 拒絕並顯示「約 US$X，本月已用 $Y／上限 $Z」；自動停：`abf-platform watchdog`（與 receiver 同進程，每 60 s 累計，投影超上限 → 建 `cancel_run` job，確認通道記 `POLICY` 指向 launch 的 rid，launch 畫面已寫明「超過 NT$Z 自動停」）。**C 級待裁決**：POLICY 通道是否合憲（「每個寫入要本人答應」）。前置：receiver 補存每 task 的 cpus／realtime／machineType（`records.py`）。新寫 `docs/CLOUD.md`。」（第 168 行）→ 本任務採其中：模組名與姊妹關係、美元不換算、cap 由管理者設、拒絕時顯示「約／已用／上限」、receiver 補存機器型號、新寫 `docs/CLOUD.md`；**不採**：`configs/cloud/rates.json` 路徑（裁決 2）、watchdog 與 `POLICY` 通道（裁決 1）、「launch 畫面寫明超過 NT$Z 自動停」（沒有自動停就不能寫，且畫面不得出現台幣）。
- 「**兩個還要你裁決的**：超過雲端上限「自動停」算不算本人同意的寫入；README／路線圖的措辭。」（第 24 行）→ 證明自動停尚未裁決，本任務不得先做（裁決 1）。

## 範圍：檔案（只准改這些）
新增：
- `platform/abf_platform/cloud_cost.py`（新；平台側，**不啟動任何程式**；檔首 `# Nothing existing: …`）
- `platform/abf_platform/data/cloud_rates.json`（新；價目表資料，每筆帶 `source` 與 `read_on`）
- `platform/tests/test_cloud_cost.py`（新；檔首 `# Nothing existing: …`）
- `docs/CLOUD.md`（新）
- `specs/cloud-cost/ledger.md`（新，executor 進度帳本）

修改：
- `platform/abf_platform/store.py`（①`task_usage` 加 `machine_type TEXT`、`price_model TEXT` 兩欄，建表敘述加、舊資料庫以 `ALTER TABLE` 補（仿 `_add_forgotten_columns` 的「欄位不在才加、被別的行程搶先加了就放過」寫法）；②`tokens.db` 新表 `cloud_caps(user_id INTEGER PRIMARY KEY, cap_usd REAL NOT NULL, set_at REAL NOT NULL)`，`TOKEN_SCHEMA` 加建表；③兩個小函式 `set_cloud_cap(tokens_path, user_id, usd)`、`cloud_cap(tokens_path, user_id)`，沒設就回 `None`）
- `platform/abf_platform/receiver.py`（約第 104 行 `task_usage` 的 INSERT／UPSERT：多存任務事件裡的 `machineType`、`priceModel`，非字串存 NULL；其餘不動）
- `platform/abf_platform/cli.py`（`user add` 加選用旗標 `--cloud-cap-usd`；新增 `user cloud-cap <name> <usd>` 讓管理者之後補設或調整；兩者都只有管理者在平台主機終端機下得了，沒有任何網頁／MCP／聊天入口能改）
- `platform/tests/test_gcb_ce.py`（只改「必須更新的既有斷言」列的一處）
- `platform/tests/test_web_actions.py`（只改 `SCHEMA` 的一列加上新表，及 `test_tc063` 的說明；見下）
- `docs/PLATFORM.md`（「What the platform stores」表加 `cloud_caps` 與 `task_usage` 新欄；「Money」那段（約第 290 行）的「The platform has no cost est…」改成指向 `docs/CLOUD.md`；`user add` 的說明加 `--cloud-cap-usd`）
- `docs/TESTING.md`（新增「cloud-cost」小節，含手動驗收）

**閘門檔，executor 不得碰（developer-agent 自己處理）**：
- `platform/pyproject.toml`、`platform/setup.py`：**預期不需要改**——`package-data` 已含 `"abf_platform" = [... "data/*.json"]`，`data/cloud_rates.json` 會跟著進 wheel（`data/nf-core-modules.json` 已是這樣）；不像 `su_rates.json` 要在 `setup.py` 從 `configs/` 複製。developer-agent 驗證這點；若發現不夠，由 developer-agent 自己改。
- `.gitignore`：不加項目（`cloud_rates.json` 是要 commit 的資料，不是建置產物）。

**禁碰（執行中的 `017d-launch-composed` 的檔案，改了會衝突）**：
- `platform/abf_launch/build.py`
- `platform/abf_station/launch.py`
- `platform/abf_platform/actions/__init__.py`
- `platform/abf_platform/pipeline_launch.py`

另外不碰：`platform/abf_platform/su.py`、`records.py`、`jobs.py`、`compute_envs.py`、`abf_station/*`（本任務不需要，且 C-2 剛合併）。

## 作法
1. **模組與簽章（`cloud_cost.py`，純平台側、唯讀運算，姊妹 `su.py` 的結構：載入價目 → 單 task 算 → 一個 run 加總 → 一個月加總）**：
   - `load_rates(path=None)`：讀 `data/cloud_rates.json`；讀不到／不是 JSON 物件 → `None`（同 `su.load_rates`）。預設路徑 `Path(__file__).parent / "data" / "cloud_rates.json"`（它是 commit 進 repo 的檔案，不需要 `su.py` 那種「wheel 版或 checkout 版」二選一）。
   - `cost_of_tasks(tasks, rates)` → `{"usd": float|None, "currency": "USD", "unknown_reasons": [...], "as_of": <價目最舊的 read_on>|None}`。每個 task 是含 `name, status, realtime_ms, machine_type, price_model, zone`（或 `region`）的字典。**只要有一個 task 缺什麼就整個 `usd` 為 `None`，附上每個 task 缺什麼的原因，不回部分總和**（跟 `su_of_tasks` 同一個嚴格態度）。
   - `run_tasks_cost(index_path, run_name, rates)`：從 `task_usage` 讀（唯讀，不建表；舊索引沒有新欄 → 視為「沒保存機器型號」→ `usd: None` 加原因「這個 run 的紀錄沒有保存機器型號 (the run record does not keep the machine type)」）。
   - `month_used(index_path, platform_path, user_id, month, rates)` → `{"usd": float, "unknown_runs": int}`：該使用者（`jobs.owned_run_names`）、啟動在 `month`（`'YYYY-MM'`，台北時間，沿用 `su._taipei_month`）、且最新一次送出的環境是 `googlebatch-platform` 的 run，其 `usd` 加總。**單一 run 算不出來時不讓整個月變成未知**：它計入 `unknown_runs`，`usd` 只加算得出的（上限檢查的白話訊息要寫「至少」並說明有 N 個 run 無法計價，見 4）。
   - `estimate_launch(index_path, platform_path, user_id, pipeline, rates)` → 同 `cost_of_tasks` 的形狀加 `basis`（`"run <名字>"` 或 `None`）：**預估＝該使用者自己、同一個 pipeline 名稱、最近一次成功、跑在 Google Batch、且算得出 `usd` 的 run 的 `usd`**（成功＝run 狀態成功；計算時該 run 的失敗重試 task 也算進去，因為它們真的花錢）。**沒有這種歷史 → `usd: None`，原因「這個 pipeline 你還沒有成功跑過的雲端紀錄，無法預估 (no earlier cloud run of this pipeline to estimate from)」；不用 `resourceLimits` 保守估**（見裁決 3）。
   - `cap_problem(platform_path, ce_name, bundle, user_id, *, index_path=None, tokens_path=None, rates=None, now=None)` → `None`（放行）或一段白話拒絕文字（`str`）。`index_path`、`tokens_path` 預設 `store.default_index_path()`／`store.default_tokens_path(index_path)`。**只對 `googlebatch-platform` 環境動作**；環境是 Slurm（或任何別種）→ 立刻回 `None`，不讀價目表、不讀上限、不開任何資料庫（所以 nano4 的送出完全不受影響）。
2. **價目表 `platform/abf_platform/data/cloud_rates.json` 的形狀**（用 Google 公開價目頁；**executor 要自己去讀頁面填數字，不得憑記憶**；讀不到的機器型號不要列）：
   ```
   { "_about": "…Do not guess a number here (no entry, no price).",
     "currency": "USD",
     "regions": { "us-central1": { "n2-standard-4": { "standard": <USD/小時>, "spot": <USD/小時>,
                                                      "source": "<該筆讀自哪個網址>", "read_on": "YYYY-MM-DD" }, … } } }
   ```
   - 規則：**每一筆（每個區域的每個機器型號）都要有 `source`（`https://` 開頭）與 `read_on`（`YYYY-MM-DD`，讀的那天）**，缺任何一個，載入時該筆視為不存在。`standard`／`spot` 其中一個沒有就只缺那個。第一版只列首位使用者實際會用到的區域與機器型號（維護者開 GCP 專案時選的區域；問 developer-agent，預設 `us-central1`）與 nf-core 常見的幾個一般用途型號（n2／e2 系列的 2、4、8 vCPU），不求齊全。
   - `time` 之類的計價細節：價目表只存「每小時、每台機器」；磁碟、網路出口、Cloud Storage 都**不算**，文件與畫面都寫成「只含運算（虛擬機）費用」。
3. **單一 task 的算法**：`usd = (realtime_ms / 3_600_000) × rate[region][machine_type][price_model]`。`price_model` 取 task 事件的 `priceModel`（`spot` 或 `standard`，**大小寫不拘**），其他值或缺 → 未知（原因寫出看到的值）；`region` 取 task 的 `cloudZone` 去掉最後的 `-<字母>`（`us-central1-a` → `us-central1`），缺 → 未知；機器型號不在價目表 → 未知，原因 `機器型號 <名字> 不在價目表 (machine type <名字> is not in the rates)`。`realtime_ms` 缺 → 未知。**不用 `cpus` 推機器型號，也不假設預設機器**。
4. **拒絕文字（`cap_problem` 的回傳，雙語，仿 repo 慣例「中文 (English)」）**，所有金額寫成 `US$` 加兩位小數：
   - 超過：`本月雲端費用上限 US$20.00，已用約 US$14.50，剩約 US$5.50；這次預估約 US$6.00，會超過。請找管理者調整上限，或下個月再送出 (this month's cloud cap is US$20.00, about US$14.50 used, about US$5.50 left; this launch is estimated at about US$6.00)`
   - 已用滿（不論預估）：`…已用約 US$20.00，剩 US$0.00，這個月不能再送出新的雲端分析…`
   - 有 run 無法計價時，「已用」寫成「至少 US$X（另有 N 個 run 算不出來）」。
   - 預估算不出來但還有剩：**放行**（回 `None`），不阻擋；畫面提示由待裁決 A 決定，本任務不寫。
   - 沒設上限：**拒絕**，文字：`管理者還沒有替你設定每月雲端費用上限，所以不能送到雲端；請管理者執行 abf-platform user cloud-cap … (no monthly cloud cap is set for you)`（裁決 4）。
   - 判斷式：`已用 + 預估 > 上限` 才拒絕（剛好等於上限放行）；`已用 ≥ 上限` 一律拒絕；上限 0 等於不准。
   - 訊息不含堆疊、檔案路徑、SQL、使用者名稱以外的他人資訊；不含 `NT$`、`TWD`、匯率。
5. **receiver 補存（`receiver.py`）**：`task_usage` 的 UPSERT 多兩欄；`machineType`、`priceModel` 不是字串就存 NULL，長度各截到 64 字。已存在的 `cpus`、`realtime_ms`、`queue` 邏輯**不動**（`su.py` 與 `test_su_in_get_run.py` 依賴）。nano4／本機 run 的這兩欄本來就是 `null`（見 fixtures），存 NULL。
6. **上限的存放與設定**：`tokens.db` 的 `cloud_caps`（見範圍）；**只有 `abf-platform user add --cloud-cap-usd N` 與 `abf-platform user cloud-cap <name> <N>` 寫得進去**（`N` 必須是大於等於 0 的有限數字，上限 `1,000,000`，超過／非數字／NaN → 拒絕並白話說明）。不新增任何 MCP 工具、網頁路由、聊天指令能讀或寫上限（使用者「改不了」靠「根本沒有入口」，T11 列舉所有入口證明）。`user add` 不給旗標 = 沒設（裁決 4）。
7. **要用到哪裡（呼叫點，本任務只提供模組，不接線）**：`cap_problem` 要在「確認頁顯示之前」被呼叫一次，才能做到「建立任何東西之前拒絕」。這個呼叫點在被禁的檔案裡，見「待 developer-agent 裁決」A。本任務的測試直接呼叫 `cloud_cost.cap_problem(...)`，不經 `request_launch`。
8. **不改 Slurm、不改 `su.py`、不改 `get_run` 的回傳形狀**：「已用美元」目前只存在於 `cloud_cost` 的函式回傳與 `docs/CLOUD.md`，不放進 `get_run`（避免動 `test_su_in_get_run.py`／MCP 工具的輸出形狀）；要顯示在費用頁屬 012d，不是本任務。
9. **新檔規則**：`cloud_cost.py`、`test_cloud_cost.py` 前 40 行要有 `# Nothing existing: <≥15 字理由>`（`test_scope.py` TC-070）；理由寫「搜過 Seqera Platform（只有計費頁、沒有平台內的預估與上限）、Nextflow `google-batch` executor 的 trace（只有 machineType／priceModel，不報價）、Google Cloud Billing 預算警示（事後通知、不能在送出前擋），沒有現成的『送出前估算＋每人每月上限』，所以自己做」。`cloud_cost.py` 與 `store.py`／`receiver.py`／`cli.py` 的新增碼都不得含 `subprocess`、`Popen`、`os.system`、`threading`、`while True`、`nohup`、`setsid`、`ssh`、`import requests`、`urllib.request`、`socket`，也不得出現 `station` 這個字（任何大小寫、任何位置，**包含註解與字串**；TC-061 用 `re.search(r"station", 每行)`）——不准用拆字串（如 `"sta" + "tion"`）規避，要寫就改寫句子。

## 失敗先行測試（`platform/tests/test_cloud_cost.py`，現在都會紅；全部用 `tmp_path` 的假價目表與假資料庫，不碰網路、不啟動程式）
測試用價目表（**只在測試裡，不是真資料**）：region `us-central1`；`n2-standard-4`：standard 0.20、spot 0.06；`e2-standard-2`：standard 0.10；沒有 `c9-fake-8`。

價目與單一 task：
- **T1 `test_ten_hours_of_n2_standard_4_is_two_dollars`**：1 個 task，`machine_type=n2-standard-4`、`price_model=standard`、`realtime_ms=36_000_000`、`zone=us-central1-a` → `usd == 2.00`、`currency == "USD"`；同一個 task 改 `spot` → `0.60`。
- **T2 `test_two_tasks_add_up`**：task A（n2-standard-4 standard、5_400_000 ms＝1.5 h）→ 0.30；task B（e2-standard-2 standard、7_200_000 ms＝2 h）→ 0.20；run 合計 `0.50`。
- **T3 `test_an_unknown_machine_type_makes_the_whole_run_unknown_with_a_reason`**：任一 task 是 `c9-fake-8` → `usd is None`，`unknown_reasons` 有一筆含 `c9-fake-8`；**不是 0、不是部分總和**。另測：缺 `realtime_ms`、缺 `price_model`、`price_model="weird"`、`zone` 缺、`zone` 的區域不在價目表 → 各自 `None` 並說明缺什麼。
- **T4 `test_a_rate_entry_without_a_source_or_a_read_date_is_not_used`**：價目檔裡一筆缺 `source`（或缺 `read_on`、或 `source` 不是 `https://`、或 `read_on` 不是 `YYYY-MM-DD`）→ 該機器型號視為不在價目表（`usd is None`）。
- **T5 `test_the_shipped_rates_file_is_complete_and_honest`**：讀 `platform/abf_platform/data/cloud_rates.json`：`currency == "USD"`；每一筆都有 `https://` 的 `source` 與合法日期的 `read_on`，日期不得晚於今天；所有費率是大於 0 的有限數字；`spot` 若有則小於同型號的 `standard`；檔內沒有 `TWD`、`NT$`、`exchange`、`匯率`；至少有一個區域與一個機器型號；`read_on` 全部不早於 2026-10-24（確認不是舊記憶）。

預估、已用、上限：
- **T6 `test_estimate_is_the_cost_of_the_latest_successful_run_of_the_same_pipeline_of_this_user`**：此使用者有兩個同 pipeline 成功 run（舊 3.40、新 2.50）→ 預估 `2.50`、`basis` 指到新的那個；另一位使用者的 run、不同 pipeline 的 run、失敗的 run、Slurm 環境的 run 都不被採用。
- **T7 `test_no_history_means_unknown_estimate_not_a_guess`**：沒有歷史 → `usd is None` 且原因含「還沒有成功跑過」；**不得出現任何 `resourceLimits`／`maxvCpus` 推出的數字**。
- **T8 `test_cap_check_numbers`**（參數化，全用上面的假資料）：
  - 上限 20.00、已用 14.50、預估 2.00 → 放行（`None`）。
  - 上限 20.00、已用 14.50、預估 6.00 → 拒絕，文字含 `US$20.00`、`US$14.50`、`US$5.50`、`US$6.00`。
  - 已用 14.50、預估剛好 5.50（合計 20.00）→ 放行（剛好等於上限不擋）。
  - 已用 20.00、預估算不出來 → 拒絕（已用滿一律擋）。
  - 已用 14.50、預估算不出來 → 放行。
  - 上限 0 → 拒絕；沒設上限 → 拒絕且文字提到 `cloud-cap`。
  - 有 1 個 run 算不出來 → 文字含「至少」與「1 個 run」。
- **T9 `test_month_used_counts_only_this_user_this_month_and_cloud_runs`**：一個 run 啟動於 `2026-09-30T16:30:00Z`（台北時間 2026-10-01 00:30）→ 算進 `2026-10`、不算進 `2026-09`；別人的 run、Slurm 的 run 不算；失敗 task 的錢算進去（task 狀態 FAILED 也有 `realtime_ms`）。
- **T10 `test_amounts_are_us_dollars_and_nothing_is_converted`**：`cloud_cost.py`、`data/cloud_rates.json`、拒絕文字、`docs/CLOUD.md` 都不含 `NT$`、`TWD`、`新台幣`、`匯率`、`exchange rate`（`docs/CLOUD.md` 若要說明「NT$1,000 是 GCP 帳單預算、不是平台上限」，該句用「台幣」二字代替符號；測試允許 `docs/CLOUD.md` 出現「台幣」但不允許 `NT$` 與數字金額＋台幣）。
- **T11 `test_only_the_admin_command_can_set_a_cap_and_no_user_door_can`**：①`abf-platform user add --cloud-cap-usd 20` 與 `user cloud-cap <name> 25` 寫入成功並可讀回；②`-1`、`abc`、`nan`、`inf`、`1e9` → 拒絕，資料庫沒變；③列舉 MCP 工具名稱（仍 12 個）、`web.py`／`web_board.py` 的路由字串、`actions` 的公開名稱，都不含 `cloud_cap`／`cloud-cap`／`cap_usd`（證明沒有使用者入口）；④使用者以自己的 PAT 呼叫任何現有工具，都讀不到別人或自己的上限數字。

接線與保護：
- **T12 `test_slurm_launch_never_reads_the_rates_or_the_cap`**：`cap_problem` 對 Slurm 環境回 `None`，且（以 monkeypatch 讓 `load_rates`、`store.cloud_cap`、開資料庫的函式一被呼叫就丟錯）證明沒被呼叫。
- **T13 `test_nothing_stops_a_running_job_and_no_policy_channel_exists`**：`abf_platform/` 原始碼沒有 `watchdog`、`POLICY`；`jobs.py` 的 `kind` 檢查清單仍是原來六種；`confirm.py` 沒有新種類；`cloud_cost.py` 沒有 `enqueue_cancel`、`cancel_run` 字樣。
- **T14 `test_scope_stays_small`**：MCP 工具仍 12 個；沒有新網頁路由；`pyproject.toml` 沒有新相依（沒有 `google-cloud`）；原始碼沒有 `import google`／`boto3`；`git diff --name-only` 不含四個禁碰檔與 `su.py`（此項由 verifier 閱卷時做，測試內以讀取檔案內容雜湊對照現有 v3 的方式不可行，所以列在「完成標準」而非自動測試）。
- **T15 `test_receiver_keeps_machine_type_and_price_model_and_only_those_two_new_columns`**：送一個含 `machineType: "n2-standard-4"`、`priceModel: "spot"` 的 task 完成事件 → `task_usage` 該列兩欄正確；`machineType: null` → NULL；`machineType: 7`（非字串）→ NULL；既有欄位 `cpus／realtime_ms／queue` 與以前相同。
- **T16 `test_an_older_database_gets_the_new_columns_and_the_new_table`**：用舊結構（沒有 `machine_type`／`price_model`、沒有 `cloud_caps`）的資料庫開啟 → 補上；同時兩個行程搶著補不報錯；舊資料列保持原樣、新欄為 NULL。
- **T17 `test_no_secret_or_path_in_the_refusal`**：拒絕文字不含 `Traceback`、`SELECT`、`.db`、`tmp_path` 的字串、token。
- **T18 `test_the_new_files_follow_the_repo_rules`**：`cloud_cost.py`、`test_cloud_cost.py` 前 40 行有 `# Nothing existing:`；沒有 `station`（不分大小寫）、沒有 `subprocess`；`docs/CLOUD.md` 存在，含：價目表怎麼更新、`source`／`read_on` 規則、只含運算費用、預估怎麼來、上限怎麼設（兩條指令）、**沒有自動停**這句白話、NT$1,000 與上限的關係。

### 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
- `platform/tests/test_gcb_ce.py::test_nothing_of_the_later_slices_exists`（約第 802 行）：以前＝`assert not names & {"cloud_cost.py", "rates.json"}`；以後＝只剩 `{"rates.json"}`（拿掉 `"cloud_cost.py"`）。理由：本任務正是要建 `cloud_cost.py`；`rates.json` 這個檔名仍不得出現（我們的檔叫 `cloud_rates.json`，名字不相等，所以不撞）。同函式的其他斷言（沒有 `buckets create` 等、`-with-tower` 不在 `gcb_preflight.py`）原樣不動。
- `platform/tests/test_web_actions.py` 的 `SCHEMA`（約第 580–595 行）與 `test_tc063_no_schema_change`：以前＝兩個資料庫的表與欄位逐一相等，註解「TC-063: no migration, no new table or column」；以後＝加一列 `'tokens.cloud_caps': ('user_id', 'cap_usd', 'set_at')`，註解改成「本表由 cloud-cost 加入」。理由：上限必須存在某處，且使用者不能改，所以放在管理者才寫得到的 `tokens.db`。**這是本任務唯一對 `SCHEMA` 的改動**；`task_usage` 在 `index.db`，`SCHEMA` 只比對 `platform.db` 與 `tokens.db`，所以不受影響。
- 確認**不會**變紅、不准改（executor 先跑，紅了就停下回報而不是改測試）：`test_su_in_get_run.py`（自己的 INSERT 欄位清單仍可用，新欄可空）、`test_estimate_su.py`、`test_su_packaged.py`、`test_pat.py:700`（`users` 欄位仍是六個，因為上限放新表而不是新欄）、`test_human_channel.py` 與 `test_station_envs.py::test_tc086`（`banned_schema_words`：新欄名 `machine_type`、`price_model`、`cap_usd`、`set_at`、表名 `cloud_caps` 都不含被禁字；executor 要跑確認）、`test_web_parity.py`（本任務**不**往 `actions` 加公開名稱，所以 `INTERNAL`／`OWED` 清單不動；若 executor 發現非加不可，停下回報）、`test_guidance.py`／`test_pat.py:383`／`test_oauth_mcp.py:44`（MCP 工具仍 12 個，`READ_TOOLS` 清單不動）、`test_gcb_launch.py`（含 :726 附近的費用字樣測試與 :1068 的 12 個工具；因為不動 `build.py`，畫面字樣不變）、`test_scope.py`（TC-061、TC-070、TC-071）、`tests/no_per_pipeline_config.sh`（`configs/` 下只准 `sites`，所以價目表不放那裡）、`tests/credentials_stay_in_settings_test.sh`。

## 完成標準（done when）
- 自動：T1–T18 全綠；全套綠（含 `tests/platform_test.sh`、`tests/no_per_pipeline_config.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`）；MCP 工具仍 12 個；Slurm 的送出、內容包、畫面一個位元都不變（`git diff --name-only` 不含 `abf_launch/`、`abf_station/`）。
- 驗收者看 `git diff --name-only origin/v3...HEAD`：只出現上面「範圍：檔案」列的檔；**不得**出現 `platform/abf_launch/build.py`、`platform/abf_station/launch.py`、`platform/abf_platform/actions/__init__.py`、`platform/abf_platform/pipeline_launch.py`、`platform/pyproject.toml`、`platform/setup.py`；`test_gcb_ce.py`、`test_web_actions.py` 只動計畫列的兩處。
- 價目表是真資料：每一筆的 `source` 打得開、頁面上的數字與檔內相符（verifier 隨機抽 3 筆，用 WebFetch 或瀏覽器核對，結果寫進報告；打不開就標 UNVERIFIED 回報，不當 PASS）。
- 手動（維護者，他自己的 GCP 帳號，**會花很小一筆錢**——先確認 GCP 帳單預算與警示已設）：
  1. `abf-platform user add <名> --lab <lab> --cloud-cap-usd 5` 建一個帳號（或對現有帳號 `user cloud-cap <名> 5`）。
  2. 用 C-2 的方式在 `gcb1` 上跑一次最小的分析，跑完後檢查 `index.db` 的 `task_usage` 有 `machine_type`、`price_model`（**這一步驗證 Nextflow 的 `google-batch` executor 真的把這兩個值送進 tower 事件**；若兩欄是 NULL，代表 executor 沒送，停下回報，不要改成猜）。
  3. 用 `cloud_cost` 算這個 run 的 `usd`，和 Google Cloud Console 帳單裡同一時段的 Compute Engine 費用比：只含運算的預估與實際相差多少，寫進 ledger（預期略低，因為沒算開機與磁碟；差太多就回報 developer-agent，不要自己調價）。
  4. 把上限暫時設成低於「已用＋預估」，確認 `cap_problem` 回傳白話拒絕、數字正確；（若待裁決 A 已裁定接線）再用 `abf-launch … --ce gcb1` 確認真的在顯示確認畫面之前就被擋下、`jobs` 表列數沒變。
- 文件：`docs/CLOUD.md`、`docs/PLATFORM.md`、`docs/TESTING.md`（「cloud-cost」小節含手動驗收 1–4）更新完；`docs/CLOUD.md` 白話寫明「目前不會自動停止正在跑的雲端工作，只會擋下新的送出」。

## 環境事實
（以 `git fetch -q origin` 後的 `origin/v3` 為準；以 `git show origin/v3:<path>` 讀）
- 姊妹模組 `platform/abf_platform/su.py`：`load_rates`、`su_of_tasks`（缺任何一項就整個 `None` 並列原因）、`run_tasks`（讀 `task_usage`，唯讀，不建表）、`site_of_run`、`run_su`、`_taipei_month`、`month_total`（台北時間的日曆月；任何一個 run 未知就整月 `None`——**本任務刻意不同：月總計容許部分 run 未知，改計數**，見作法 1）。`estimate_su` 在 `actions/__init__.py:132`，是沒有 MCP 工具、沒有網頁路由的 v3 helper（`test_web_parity.py` 的 `INTERNAL` 內有它）；`cloud_cost` 比它更保守：**連 action 都不加**（因為 `actions/__init__.py` 在禁碰名單）。
- `task_usage` 表（`store.py:64` 起）：`run_id, task_key, name, status, cpus, realtime_ms, queue`；`receiver.py:104` 在 task 狀態為 `COMPLETED` 或 `FAILED` 時寫入。Tower 事件的 task 本來就有 `cloudZone`、`machineType`、`priceModel`、`numSpotInterruptions`（`platform/tests/fixtures/payloads/nf2510_ok.json` 約第 170–180 行；本機執行時為 `null`）。**查不到**：`google-batch` executor 實際會不會填這幾欄、`priceModel` 的值是不是 `spot`／`standard`（fixtures 只有 `null` 的樣本）——所以列為手動驗收第 2 步，且程式遇到其他值就標未知、不猜。
- 使用者與上限：`users` 表在 `tokens.db`（`store.py:97`，欄位 `id, name, lab, created_at, disabled_at, password_hash`），`create_user`（`store.py:~700`）、`cli.py:111 cmd_user_add`、`cli.py:535` 起的 `user` 子指令。`tokens.db` 的欄位補齊在 `_migrate_tokens`（`store.py:~640`），`platform.db` 的在 `_add_forgotten_columns`（`store.py:532`）。三個資料庫的路徑：`store.default_index_path / default_tokens_path / default_platform_path`（`store.py:268–290`，同一資料夾）。
- 使用者擁有的 run：`jobs.owned_run_names(platform_path, user_id)`（`jobs.py:280`）；最新送出：`jobs.latest_launch`（`jobs.py:296`）；環境類型：`compute_envs.get(platform_path, ce_name)["platform"]`（`googlebatch-platform`）。
- 送出路徑：`actions/__init__.py` `request_launch`（約 :489–526）依序：`build.prepare_launch`（:513）→ `confirm.find_approved` → `jobs.check_run_name`（:522）→ `build.launch_screen`（:525）→ `_ask`（:526）。終端機路徑：`platform/abf_launch/cli.py`（約 :84 呼叫 `build.prepare_launch`，:93 顯示畫面）。`build.py:451` 現有 gcb 畫面寫著「平台目前還沒有費用預估與上限」，`docs/PLATFORM.md:290` 也有一句對應英文。
- 憲法與掃描：`tests/no_per_pipeline_config.sh` 第 2 項——`configs/` 底下**只准有 `sites`**，其他任何子資料夾（含 `configs/cloud/`）直接 FAIL。因此價目表放 `platform/abf_platform/data/`（`data/nf-core-modules.json` 是先例）。`platform/pyproject.toml` 的 `package-data` 已含 `data/*.json`。`test_scope.py`：TC-070（新 `.py` 前 40 行 `# Nothing existing:`）、TC-071（`abf_platform/` 內不得有 `nextflow run`、`sbatch`、`subprocess`、`Popen`、`threading`、`while True`、`nohup`、`setsid` 等）、TC-061（不得有 `ssh`、`scancel`、`import requests`、`urllib.request`、`socket`，以及 `station` 這個字樣）。
- 維護者費用裁示的原文位置：`memory/PLAN-abf-v3-replan-2026-10.md` 第 16、24、40、46、50、54、168 行。該檔寫「ADR 0009」，但 `origin/v3:docs/adr/0009-web-layout-three-panes.md` 是網頁版面；**v3 裡查不到一份定「雲端費用顯示美元不換算」的 ADR**，依據是維護者 10-18／10-21 的話。
- Google 價目：公開價目頁網址由 executor 填進 `source`（本計畫不替它填數字；規劃者沒有讀過頁面，不寫記憶中的數字）。GCP Batch 本身是否另收服務費、磁碟與網路如何計，**本計畫查不到**，所以文件與畫面一律寫「只含運算（虛擬機）費用的預估」。
- 週期：月份用台北時間（沿用 `su.py`）。Google 帳單的月份切點是 Pacific 時間，兩者在每月初末最多差約半天；`docs/CLOUD.md` 寫一句即可，不處理。

## 不做
- 不做自動停：沒有 watchdog、沒有定時累計、沒有自動建 `cancel_run` job、沒有 `POLICY` 確認通道、不改 `confirm.py`／`jobs.py` 的種類清單（裁決 1）。
- 不做 `resourceLimits` 或 `maxvCpus` 推估費用（裁決 3）；不用 `cpus` 反推機器型號。
- 不做任何貨幣轉換、匯率、台幣顯示；平台程式與價目表沒有 `NT$`／`TWD`。
- 不做儲存（Cloud Storage）費、網路出口費、磁碟費的估算（C-7 才會碰儲存月費）。
- 不接線進 `request_launch`／`build.prepare_launch`（它們在禁碰檔裡，見待裁決 A）；不改 gcb 的確認畫面文字（`build.py` 禁碰，見待裁決 B）。
- 不新增 MCP 工具、網頁路由、聊天指令、`actions` 公開函式；不改 `get_run` 回傳；不做費用頁（012d）。
- 不做 AWS Batch、Azure、K8s 的價目與上限（C-4、C-5）。
- 不改 Slurm 任何行為；不改 `su.py`、`records.py`、`compute_envs.py`、`abf_station/*`。
- 不去讀或寫真實的 GCP 帳單 API（不引入 `google-cloud-*` 相依；平台程式不連外，TC-061）。
- 不做跨實驗室、角色、群組上限（一間實驗室一台平台；上限只有「每人每月」一種）。

## 裁決（2026-10-24，developer-agent 起草；與上文衝突時以本段為準）
1. **本任務不自動停止任何正在跑的雲端工作。** 範圍＝預估＋記下已用＋每人每月上限擋下**新的**送出。理由：維護者自己列了「超過雲端上限『自動停』算不算本人同意的寫入」是還沒裁決的問題（replan 第 24 行與 C-3 的「C 級待裁決」）；沒有裁決就先做，等於替他決定。該問題仍是 C 級，待他回答後另開任務（暫名 `cloud-watchdog`）。**預設採此做法。**
2. **價目表放 `platform/abf_platform/data/cloud_rates.json`，不放 `configs/cloud/rates.json`。** 理由：`tests/no_per_pipeline_config.sh` 第 2 項明寫 `configs/` 只准有 `sites`，新增 `configs/cloud/` 會直接讓憲法檢查 FAIL；`data/` 已有 `nf-core-modules.json` 為先例，且 `pyproject.toml` 的 `package-data` 已含 `data/*.json`，打包不需改設定。檔名取 `cloud_rates.json` 而不是 `rates.json`，因為 C-1 的 `test_gcb_ce.py` 禁止名為 `rates.json` 的檔案出現（該禁令保留）。`pyproject.toml`／`setup.py` 為閘門檔，由 developer-agent 自行驗證與修改，executor 不碰。
3. **預估只用歷史，沒歷史就標未知，放行。** 原文「無歷史用 `resourceLimits` 保守估」不採：`maxvCpus` 在 C-2 已落成「單一 task 的 cpus 上限」，不是總量，也沒有時間長度，拿它估只會得到一個沒有依據的數字；維護者的規矩是「不猜」。代價：首位使用者第一次跑某個 pipeline 時，上限只擋得住「已用滿」，擋不住「這一次太貴」。這個缺口寫進 `docs/CLOUD.md`，並建議首位使用者的上限設小（例如 US$5）。**若維護者要保守估，另開小任務：需要先決定怎麼從 `resourceLimits`＋預期時間算，並且以 `get_run` 的歷史驗證。**
4. **沒設上限＝不准送到雲端。** 理由：「每人每月上限由管理者開帳號時設」，沒設就是管理者沒做這步，預設放行等於沒有上限。現有帳號要補設：`abf-platform user cloud-cap <名> <美元>`。這只影響 Google Batch 環境，nano4／Slurm 不受影響。**預設採此做法；要改成「沒設＝不限」是一行改動，但會違反『超過就擋』的初衷，不建議。**
5. **不碰四個禁碰檔，也不碰 `su.py`／`records.py`。** 理由：`017d-launch-composed` 在跑，同檔會衝突。因此 `cap_problem` 不接線，由待裁決 A 處理。
6. **上限存放：`tokens.db` 新表 `cloud_caps`，不是 `users` 加欄。** 理由：`users` 加欄會連動 `test_pat.py:700`、`test_web_actions.py` 的 `users` 欄位清單與登入相關測試；新表只動 `test_web_actions.py` 的 `SCHEMA` 一列。**另一選項**：`users.cloud_cap_usd REAL`，語意更直接，但要多改 `test_pat.py` 一處。**預設：新表。**
7. **「已用」的計價單位是 task 的 `realtime`（秒級），不含開機與關機、不含磁碟與網路。** 這會略低於 Google 的帳單；文件與拒絕文字都用「約」，並在 `docs/CLOUD.md` 說明。手動驗收第 3 步量出實際差距後再決定是否加一個固定比例（那是另一個任務，且要有帳單證據，不憑感覺）。
8. **FAILED 的 task 也算錢**（它們真的跑過），已存在的 `task_usage` 就是這樣記的；但「預估」只取最近一次**成功**的 run 當基準，避免拿一次提早失敗的便宜 run 當預估。
9. **機器型號與計價模式只信 Nextflow 回報的字串，大小寫不拘、其他值一律未知。** 不用 `cpus`／`memory` 推機器型號，不假設預設機器。
10. **新檔標頭與禁字**：見作法 9（含 `station` 一字不得出現，包括註解）。
11. **派工順序**：不可與動 `store.py`／`receiver.py`／`cli.py` 的任務平行；與 `017d-launch-composed` 可以平行（檔案不相交），但**接線**（待裁決 A）要等 017d 合併後才能做。

## 待 developer-agent 裁決
A. **`cap_problem` 的呼叫點在被禁止的檔案裡。** 要做到「在顯示確認畫面之前、建立任何東西之前拒絕」，最小的接線是**一行**，位置在 `platform/abf_platform/actions/__init__.py` 的 `request_launch`，`jobs.check_run_name(...)` 那個 `try` 區塊之後、`text = build.as_text(build.launch_screen(bundle, ce))`（約第 525 行）之前：
   ```
   problem = cloud_cost.cap_problem(platform_path, ce, bundle, _caller_id(caller))
   if problem: return _no("未送出：%s" % problem)
   ```
   （外加檔頂 `from .. import … cloud_cost`。）`actions/__init__.py` 是 `017d` 執行中的檔案，本任務不改。選項：①等 017d 合併後，由 developer-agent 用一個只動這兩行的小補丁接上（建議）；②改掛在 `build.prepare_launch`（`abf_launch/build.py`，同樣是 017d 禁改檔），好處是網頁、MCP、終端機三條路都經過，壞處同上；③終端機另一條路 `platform/abf_launch/cli.py`（約第 84 行 `build.prepare_launch` 之後、:93 顯示畫面之前）**不在禁碰名單**，可由本任務先接上，但這樣網頁與 MCP 路徑（走 `request_launch`）會漏掉，造成「終端機擋得住、網頁擋不住」的不一致，所以**不建議只做這一條**。目前本任務採「只交付模組與測試，不接線」，需要 developer-agent 在 017d 合併後補接線並補一條整合測試（`request_launch` 在上限內放行、超過時回 `_no(...)` 且 `jobs` 與 `confirmations` 表列數不變）。另一個待確認點：`request_launch` 沒有 `index_path` 參數，`cap_problem` 預設用 `store.default_index_path()`；若部署設了 `ABF_PLATFORM_DB` 以外的方式指定索引，接線時要把 index 路徑一起傳進來。
B. **gcb 確認畫面那句「平台目前還沒有費用預估與上限」在接線後會變成不實**（`platform/abf_launch/build.py:451`，另有 `platform/tests/test_gcb_launch.py:726` 與 `docs/PLATFORM.md:290` 逐字釘住它）。`build.py` 是禁碰檔，所以本任務不改；請 developer-agent 在 017d 合併、接線時一併把那句改成「平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單」之類（不得出現金額數字或台幣，`test_gcb_launch.py` 現有的「畫面第一段含『由 Google 向實驗室的 Google Cloud 帳號收費』、不含數字金額」斷言仍要過），並同步改 :726 與 PLATFORM.md。接線前，那句仍是真的。
C. **（給維護者，非工程）自動停算不算本人同意的寫入**——仍未裁決；決定前不開 `cloud-watchdog`。
D. **預設的月上限與首位使用者**：建議他自己的帳號先設一個小數字（例如 US$5），和 GCP 帳單預算形成兩層保護；數字由他定，本任務不寫死任何預設值。

## 裁決二（2026-10-24 developer-agent；維護者 10-24 核可「超上限只擋新送出、不自動停」；以本段為準）
1. 待裁決 A、B：本任務只交付模組、資料、儲存、CLI 與測試，不接線。接到 `request_launch` 與改確認頁那句「還沒有費用預估與上限」，另開 `cloud-cost-wire`，排在 017d 合併之後。本任務不得改 `actions/__init__.py`、`abf_launch/build.py`。
2. 沒有歷史資料時估計＝unknown，送出允許但確認頁要寫明「無法預估」；沒設上限的使用者送雲端一律拒絕（安全預設）。上限存新表 `cloud_caps`。
3. 真實費率由 executor 從 Google 官方價目頁填入，每筆附網址與讀取日期；讀不到就只放測試用費率，並在 ledger 寫明。
4. `cap_problem` 預設 `store.default_index_path()` 接受。

## 裁決三（2026-10-24 developer-agent，回應 verifier 出題退回；以本段為準）
5. 區域：`task_usage` 新增第三欄 `cloud_zone`（receiver 從 task 的 `cloudZone` 存入）；區域＝zone 去掉最後的 `-<字母>`。zone 缺時退用該 run 計算環境設定的 `location`（compute_envs.py 已有）；兩者都沒有才是 unknown。T6、T9、T15、T16 依此造資料，T15 標題改為「three new columns」。
6. 價目檔照 T5：每筆必須是真實價目、附 https 來源與讀取日；讀不到官方價目頁就回報 BLOCKED，不准放測試用費率進出貨檔（測試用費率只放在測試的 fixture）。取代裁決二第 3 點。
7. `web_board.py` 的「雲端 NT$ —」占位字留給 012d，本任務不動。
8. `cap_problem` 的 pipeline 名稱取 `bundle["pipeline"]`；T8 的拒絕情境、CLOUD.md 的台幣措辭照 verifier 合約的寫法接受。
9. 重建索引若不經 receiver，executor 回報 BLOCKED 說明，不硬過 TC-098。T14 列為手動檢查接受。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
