---
id: cloud-cost-wire
title: 雲端費用接線：Google Batch 的送出在建立任何東西之前先過每月上限，確認畫面寫真實預估（價目表仍空，所以今天預估都是「無法預估」）
tier: B
kinds: backend
lane: L2-platform-ce
base: v3（cloud-cost PR #188 與 017d `launch-composed` 都已合併；本任務從現在的 v3 開分支。行號以 `origin/v3` @ `817898f` 為準，開工前 `git fetch -q origin` 後若有漂移，以函式名為準）
source: memory/dev-plans/cloud-cost.md 裁決二 1（「接到 `request_launch` 與改確認頁那句『還沒有費用預估與上限』，另開 `cloud-cost-wire`，排在 017d 合併之後」）、待裁決 A／B；維護者 10-24 核可「超上限只擋新送出、不自動停」
---

# cloud-cost-wire

> 本檔由 developer-agent 寫（2026-10-24）。B 級（使用者看得到的新行為，但沒有新畫面、沒有新工具）→ verifier 通過＋CI 綠由 developer-agent 自合。
> **這是 cloud-cost 的第二半**：#188 已合併了模組（`cloud_cost.py`）、儲存（`cloud_caps`）、`user add --cloud-cap-usd`／`user cloud-cap` 與收存機器型號的 receiver，**但沒有接進送出流程**，所以今天上限擋不住任何送出（`docs/CLOUD.md:41`）。本任務只做接線與確認畫面的那一句。
> **與 `resume-edit-params-b` 的關係**：它之後會動同兩個檔。本任務動的函式很少：`actions/__init__.py` 只動 `_finish_launch`、新增一個 `_cloud_check`、改一行 import；`build.py` 只動 `GCB_COST`、`gcb_launch_screen`、`launch_screen`、新增 `cost_line`。**不碰** `request_resume`、`_request_attempt`、`prepare_resume`、`resume_screen`、`read_edit_args`、`relaunch_screen`、`_attempt_lines`。兩任務的 diff 不相交，但同檔，不要同一個 worktree 平行派；先後順序不拘，後到的做 rebase。

## 目標
使用者（有帳號的人）從網頁或 AI 要在 Google Batch 環境送出分析時，平台在**建立任何東西之前**（不建確認、不排工作、不寫 `jobs`）先查每月雲端上限；會超過就用白話拒絕並寫明上限、已用、剩下各是多少美元；沒超過就照常顯示確認畫面，畫面上用一行寫這次約多少美元，或寫「無法預估」並說原因。

為什麼這樣做：
1. 維護者要的是「花費控制」（年底只能交兩塊時的其中一塊）。#188 做了算法但沒接線，等於還沒有控制。
2. 確認畫面現在那句「平台目前還沒有費用預估與上限」（`platform/abf_launch/build.py:464`）接線後會變成假話，必須在同一個 PR 換掉，否則使用者被騙。
3. 價目表出貨時是空的（`platform/abf_platform/data/cloud_rates.json` 的 `regions` 為 `{}`，`cloud-rates-fill` 之後才填），所以**今天每一次估計都是「無法預估」**；上限只擋得住「沒設上限」「上限 0」「本月已用滿」。這是照實呈現，不是缺陷，文件與 PR 說明都要寫。
4. 不自動停止任何正在跑的工作（維護者裁示）。

## 維護者原話（verifier 出題用）
逐字取自 `memory/dev-plans/cloud-cost.md` 的「維護者原話」節（該節各句後面的「→ …」是舊任務的測試對應，本檔不沿用，對應改列在本節末）。

- 「Google Batch 雲端：等你開好 GCP 帳號（預算 NT$1,000）；費用顯示美元、每人每月上限、超過自動停。接著 AWS Batch、Azure／K8s。」（`memory/PLAN-abf-v3-replan-2026-10.md` 第 16 行）
- 「雲端費用**照 10-18 裁示**：顯示雲端自己的幣別（美元）、不換算、每人每月上限由管理者開帳號時設，NT$1,000 只是 GCP 帳單預算」（第 46 行，裁示 10 的一部分）
- 「4. 四種計算環境都建：nano4 → Google Batch（開發上限 NT$1,000/月）→ AWS Batch → Azure／K8s。架構照 Seqera（憑證 → 計算環境 → Pipeline → Run）。」（第 40 行，裁示 4）
- 「12. （10-21 拷問）雲端第一個真實使用者＝他自己的自費帳號；收費理由＝「不用自己架、有人維護」（託管＋支援，每實驗室固定月費，像 Seqera）；年底若只能交兩塊＝**雲端跑通＋花費控制**與**網頁全流程（國網）**，畫布與聊天排年後」（第 50 行）
- 「14. （10-21 拷問三）**B 級部分自合**：網頁畫面以外的 B 級（後端行為改變），verifier 通過＋CI 綠就由我合併，事後列進每日清單」（第 54 行）
- 「**C-3 `cloud-cost`**（B／backend）：`platform/abf_platform/cloud_cost.py`（`su.py` 姊妹）＋`configs/cloud/rates.json`（以雲端自己的幣別計，美元；**不換算**，ADR 0009）；預估＝同管線最近成功 run 的 core-hours × 費率，無歷史用 `resourceLimits` 保守估；settings `cloud_cap_usd_per_person_month`（管理者開帳號時設，使用者不能改）；`request_launch` 在 `_ask` 前：估計＋當月已花 > cap → 拒絕並顯示「約 US$X，本月已用 $Y／上限 $Z」；自動停：`abf-platform watchdog`（與 receiver 同進程，每 60 s 累計，投影超上限 → 建 `cancel_run` job，確認通道記 `POLICY` 指向 launch 的 rid，launch 畫面已寫明「超過 NT$Z 自動停」）。**C 級待裁決**：POLICY 通道是否合憲（「每個寫入要本人答應」）。前置：receiver 補存每 task 的 cpus／realtime／machineType（`records.py`）。新寫 `docs/CLOUD.md`。」（第 168 行）
- 「**兩個還要你裁決的**：超過雲端上限「自動停」算不算本人同意的寫入；README／路線圖的措辭。」（第 24 行）
- 維護者 10-24 的核可（developer-agent 轉述，見 `cloud-cost.md` 裁決二）：「超上限只擋新送出、不自動停」。
- 維護者 10-21／10-24 對本任務範圍的指示（任務單原文）：「`cap_problem` 接進 `request_launch`，在 `check_run_name` 與確認畫面之間；沒設上限的使用者送雲端一律拒絕；預估不明則允許但確認畫面寫無法預估；那句『平台目前還沒有費用預估與上限』換成真實預估那一行；價目表仍是空的，所以今天每個預估都是未知；不自動停止執行中的工作。」

對應（verifier 出題時每句至少一條）：
- 「每人每月上限」「超過就擋」「約／已用／上限」→ W1、W2、W5、W6、W14、W15。
- 「沒設上限者不准」→ W3、W4。
- 「顯示美元、不換算」→ W16、B3、B6、K4。
- 「超過自動停」**不做**（維護者 10-24 裁示只擋新送出）→ K3 鎖住「沒有偷做」。
- 「預估不明則允許，畫面寫無法預估」→ W7、B4、B5、C2、C3。
- 「那句換掉」→ B1、B8。
- 「B 級、不改網頁畫面、後端行為」→ K5。

## 範圍：檔案（只准改這些；≤10 個）
修改：
1. `platform/abf_platform/actions/__init__.py`——只動：①第 27 行 import 加一個**帶底線的別名** `cloud_cost as _cost`（理由見作法 1）；②`_finish_launch`（:597–607）內加兩行呼叫與一個參數；③新增私有函式 `_cloud_check`（放在 `_finish_launch` 前面）。不新增任何公開名稱。
2. `platform/abf_launch/build.py`——只動：`GCB_COST`（:463–464）、`gcb_launch_screen`（:479–496）、`launch_screen`（:533–536）；新增 `cost_line`（放在 `gcb_launch_screen` 前面）。
3. `platform/abf_platform/cloud_cost.py`——①`estimate_launch`（:208–217）找不到可估價的 run 時，改回傳「最新一個合格但算不出來的 run」的原因（作法 3）；②新增 `launch_estimate`（放在 `estimate_launch` 後面）。`cap_problem`（:228–261）**不動**。
4. `platform/tests/test_gcb_launch.py`——只改 `test_the_screen_says_google_bills_the_lab_in_its_first_paragraph`（:720–）內 `sentence` 與它的比對（見「必須更新的既有斷言」）。
5. `docs/CLOUD.md`——「目前的限制」第二條（:41）改寫；加「確認畫面長什麼樣」與「哪些入口受上限管」兩段。
6. `docs/PLATFORM.md`——「Money」段（:292）改寫。
7. `docs/TESTING.md`——「Cloud cost (cloud-cost)」小節（:579–588）第 4 步括號（:586）改寫；新增「Cloud cost wiring」小節（手動驗收）。
新增：
8. `platform/tests/test_cloud_wire.py`（新；檔首 `# Nothing existing: …`；沿用 `test_cloud_cost.py` 的 `World`、`RATES`、`_task`、`_hours` 與 `test_gcb_launch.py` 的 `box` 夾具，用 `from … import` 引入，**不複製**）
9. `specs/cloud-cost-wire/ledger.md`（executor 進度帳本）

**閘門檔，executor 不得碰**：`platform/pyproject.toml`、`platform/setup.py`、`platform/abf_platform/data/cloud_rates.json`（價目表仍空，由 `cloud-rates-fill` 填）。

**禁碰（任務單明示）**：`platform/abf_station/*`、`hooks/*`、`tests/run_all.sh`、`.github/*`、`platform/abf_platform/cloud_store.py`、`platform/abf_platform/actions/datasets.py`。
另外不碰：`store.py`、`receiver.py`、`platform/abf_platform/cli.py`（#188 已做完）、`platform/abf_launch/cli.py`（終端機入口，見「不做」與裁決 5）、`web.py`、`mcp_server.py`、`jobs.py`、`confirm.py`、`su.py`。

## 作法
1. **接線點與順序（`actions/__init__.py`）**：`request_launch`（:562–581）與 `request_pipeline_launch`（:610–626）都把後半段交給 `_finish_launch`（:581、:626；`test_pipeline_launch.py:486` 也釘著兩者都呼叫它）。檢查放在 `_finish_launch` 裡，一處改好兩個入口（一般 nf-core 與組合管線）：
   ```
   found = confirm.find_approved(...)        # 現有 :599，不動
   if found: return _queued(...)             # 現有，不動
   try: jobs.check_run_name(...)             # 現有 :601–605，不動
   except jobs.JobRefused ...                # 現有，不動
   problem, cost = _cloud_check(platform_path, ce, bundle, caller)     # 新
   if problem: return _no("未送出：%s" % problem)                      # 新
   text = build.as_text(build.launch_screen(bundle, ce, cost))         # 改：多傳 cost
   ```
   - 順序：run 名稱被拒 → 上限被拒 → 顯示畫面 → `_ask`。名稱先於上限，因為名稱錯是更便宜的修正，且與任務單「between `check_run_name` and the launch screen」一致。
   - 「已經有本人的 yes」那條路（`find_approved` → `_queued`，:599–601）在檢查**之前**，不受影響：本人按過「送出」後的第二次呼叫只是取回工作編號，不是新的送出。這代表「第一次呼叫（上限內）→ 本人按送出 → 第二次呼叫」之間若上限被調低，不會重新檢查；這個視窗最長是確認的有效期（600 秒，見 `test_human_channel.py:429` 一帶），接受。
   - import 用別名：`from .. import cloud_cost as _cost`（加進 :27 的 import 行）。**必須帶底線**：`test_cloud_cost.py:602` 斷言 `dir(actions)` 沒有任何不以底線開頭、名稱含 `cloud` 的名字；不帶底線會讓它變紅。同理 `actions/__init__.py` 內**不得出現** `cloud_cap`、`cap_usd`、`cloud-cap` 這幾個字串（`test_cloud_cost.py:604–628` 掃整個 `abf_platform/`，只准 `store.py`、`cloud_cost.py`、`cli.py` 知道它們）；用 `_cost.cap_problem` 即可，變數名不要叫 `cap`／`cloud_cap`。
   - 不新增任何公開動作名稱，所以 `test_web_parity.py` 的 `INTERNAL`／`OWED` 清單不動。簽名不動：`request_launch`、`request_pipeline_launch`、`_finish_launch` 的參數列都不變（`test_pipeline_launch.py:489–495` 比對它們）。
2. **`_cloud_check(platform_path, ce, bundle, caller)` → `(problem 或 None, cost 或 None)`**：
   - 環境不是 Google Batch（`build.is_gcb(platform_path, ce)`，`build.py:269`）→ `(None, None)`，立刻回，**不讀價目表、不讀上限、不開索引**（Slurm 的送出一個位元都不變）。
   - `caller is None`（本機終端機或 stdio，沒有帳號）→ `(None, None)`：不查上限、不算預估，畫面走預設那一行（作法 4）。理由與取捨見裁決 5。
   - 否則 `problem = _cost.cap_problem(platform_path, ce, bundle, caller.user_id)`；有 `problem` → `(problem, None)`（不再算預估）；沒有 → `cost = _cost.launch_estimate(platform_path, bundle, caller.user_id)`，回 `(None, cost)`。
   - 索引路徑一律用 `cap_problem` 的預設（`store.default_index_path()`，`cloud_cost.py:236`）——沿用 cloud-cost 裁決二 4。**不新增 `index_path` 參數**。
   - 這個函式不啟動任何程式、不寫任何東西、不連網。
3. **`cloud_cost.py` 兩處小改**：
   - `launch_estimate(platform_path, bundle, user_id, *, index_path=None, rates=None)` → 與 `estimate_launch` 同形狀的字典（`usd`、`currency`、`unknown_reasons`、`as_of`、`basis`）。路徑與價目表的預設同 `cap_problem`（`index_path or store.default_index_path()`；`rates if rates is not None else load_rates()`）；`pipeline = bundle.get("pipeline")`。
   - `estimate_launch` 的理由修正：現在它對「有歷史但算不出來」與「根本沒有歷史」都回 `NO_HISTORY`（「你還沒有成功跑過」，`cloud_cost.py:24、217`），當價目表是空的時這句話對使用者是錯的。改成：走訪時記下**第一個**（最新的）合格（成功、同 pipeline、Google Batch）但 `usd` 為 `None` 的 run 的 `out`；全部都算不出來時回 `dict(那個 out, basis=None)`（它的 `unknown_reasons` 就是真正的原因，例如「尚未填入價目」）；一個合格 run 都沒有才回 `NO_HISTORY`。有可估價的 run 時行為不變（回第一個可估價的）。
4. **確認畫面（`build.py`）**：
   - `launch_screen(bundle, ce_name, cost=None)`、`gcb_launch_screen(bundle, ce_name, cost=None)`：第三參數選用，預設 `None`；Slurm 分支完全不看它（`launch_screen` :533–536 的 Slurm 路徑一字不改，`test_gcb_launch.py:1103` 的雜湊不能變）。所有現有二參數呼叫仍可用（`abf_launch/cli.py:93`、`relaunch_screen` :617、各測試）。
   - `GCB_COST`（:463–464）拿掉那一句假話，其餘一字不改，變成：
     「費用：按下 y 之後，這個 run 會在 Google Cloud 專案 %s 裡建立 Batch 工作與虛擬機，由 Google 向實驗室的 Google Cloud 帳號收費。主控程序跑在平台主機上，取消請用平台的取消指令。」
     它仍是畫面的第 1 行（`lines[1]`）。
   - 新增 `cost_line(cost)` → 一行文字（不含 `terminal.PREFIX`），`gcb_launch_screen` 把它放成緊接著的第 2 行（`lines[2]`），用 `terminal.PREFIX + terminal.esc(...)`，與 :483 同一寫法：
     - **算得出（`cost["usd"]` 不是 `None`）**：「費用預估：約 US$%.2f（依你最近一次成功的同管線雲端 %s 的實際運算時間推算；只含虛擬機運算費用，不含磁碟與網路；價目讀於 %s）。平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。」——三個 `%`：金額（兩位小數）、`cost["basis"]`（形如 `run <名字>`）、`cost["as_of"]`（`YYYY-MM-DD`，缺就寫「不明」）。
     - **算不出（`usd` 是 `None`）**：「費用預估：無法預估（%s）。平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。」——`%s` 取 `unknown_reasons[0]`，整段先 `terminal.esc` 再截到前 200 字，沒有原因時寫「原因不明 (reason unknown)」。
     - **沒傳 `cost`（`None`：終端機、沒有帳號的 stdio）**：「費用預估：無法預估（這個送出入口沒有算預估 (this way of sending does not work out an estimate)）。平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。」
   - **不得改 `bundle`**：畫面是 `bundle` 以外的資訊，`common.bundle_sha256`、`find_approved` 的比對、`confirmations.sha256` 都不變（`test_human_channel.py:182` 一帶）。預估只出現在畫面文字（也就是 `confirmations.screen_text`）。
   - 預設那一行與「算不出」那一行**都不得含** `US$`、數字加貨幣字樣（`test_gcb_launch.py:730` 的正規式 `NT\$|USD|US\$|TWD|[$＄￥¥€£]\s?[0-9]|[0-9]\s?(元|美元|台幣)` 對二參數呼叫的整個畫面仍要過）。
5. **拒絕文字**：直接用 `cap_problem` 已有的雙語白話（`cloud_cost.py:224–261`：沒設上限 `NO_CAP`、已用滿、預估會超過），外加既有的 `未送出：` 前綴，經 `_no(...)`（:431）。**不新增、不改拒絕文字**。金額都是 `US$` 兩位小數，名稱「上限／已用／剩」都在裡面。不含堆疊、路徑、SQL、他人資訊。
6. **為什麼不另外把預估放進 `bundle`／`get_run`**：維持 cloud-cost 裁決的邊界（不動 `get_run` 形狀、不動 MCP 工具）。費用頁屬 012d。
7. **文件**：
   - `docs/CLOUD.md`：「目前的限制」第二條（:41，「這個檢查已經做成模組…接線之前確認畫面仍寫…」）整句換成：「從網頁或 AI 送出到 Google Batch 時，平台在建立任何東西之前先查這個上限；確認畫面第二行寫這次的預估或『無法預估』。**例外：平台主機上管理者自己打的 `abf-launch` 終端機指令，以及沒有帳號的本機 stdio，不查上限**（它們是管理者的入口，沒有『這個人』可以套用上限）。」新增一段「確認畫面長什麼樣」（引作法 4 的三種一行）；保留既有「沒有歷史就是未知」「價目表目前是空的」等段，並把「這次 merge 後上限還沒接進送出流程」那句改成已接線。`test_cloud_cost.py` 的文件測試（`test_the_cloud_document_says_what_it_must`）要求的詞（`只含運算`、`同一個 pipeline`、`最近一次成功`、`--cloud-cap-usd`、`不會自動停止正在跑的雲端工作`、`只會擋下新的送出`、`帳單預算`、`太平洋時間`、`第一次`、`擋不住` 等）一個都不能少；且不得出現 `NT$`。
   - `docs/PLATFORM.md:292`：把「but the launch screen does not use it yet; the actual amount is on Google's invoice. The launch screen says this in its first paragraph, without a number.」改成英文白話：平台在網頁與 AI 的送出到 Google Batch 時，先查每人每月上限，確認畫面的第二行寫預估（或「無法預估」與原因）；第一段仍不含數字；實際金額看 Google 帳單；平台不會自動停止已在跑的工作。保留前面「費用：按下 y 之後…」那句中文。
   - `docs/TESTING.md`：見「完成標準」手動。

## 失敗先行測試（`platform/tests/test_cloud_wire.py` 與 `test_gcb_launch.py` 那一處；現在都會紅；不碰網路、不啟動程式）
測試用價目表與資料同 `test_cloud_cost.py` 的 `RATES`／`World`（假的，只在測試裡）。以 `monkeypatch` 把 `status.now` 固定、把 `ABF_PLATFORM_DB` 指到測試的索引（`cap_problem` 預設取 `store.default_index_path()`），平台、索引、`tokens.db` 放同一資料夾。呼叫入口一律是 `actions.request_launch`（或 `actions._finish_launch`），`caller` 用 `actions.Caller(user_id, name, lab)`，不經 `person`（走網頁確認的那條，回 `state: "pending"`）。

送出路徑（`actions`）：
- **W1 `test_over_the_cap_is_refused_before_anything_is_created`**：上限 20.00、已用 14.50、預估 6.00 → 回 `ok False`、`sent False`、訊息以「未送出：」開頭，含 `US$20.00`、`US$14.50`、`US$5.50`、`US$6.00`；`confirmations`、`jobs`、`launches` 表的列數與呼叫前相同；`_ask`（monkeypatch 成一被呼叫就丟錯）沒被呼叫；`build.launch_screen`（同法）沒被呼叫。
- **W2 `test_a_month_already_used_up_is_refused_whatever_the_estimate`**：已用 20.00（= 上限）、預估算不出來 → 拒絕，文字含「不能再送出新的雲端分析」；列數不變。
- **W3 `test_a_person_with_no_cap_cannot_launch_to_the_cloud`**：有帳號、沒設上限 → 拒絕，文字含 `cloud-cap`；列數不變。
- **W4 `test_a_cap_of_zero_refuses`**：上限 0 → 拒絕；列數不變。
- **W5 `test_exactly_at_the_cap_goes_on_to_the_screen`**：上限 20.00、已用 14.50、預估 5.50（合計剛好 20.00）→ 回 `state "pending"`、有 `confirmation_url`；`confirmations` 多一列；`summary` 含「費用預估：約 US$5.50」。
- **W6 `test_an_estimate_that_fits_shows_its_line_on_the_screen`**：上限 20.00、已用 14.50、預估 2.00 → pending；`summary` 的第 3 行（`lines[2]`，去掉前綴後）等於作法 4「算得出」那一行（金額 `US$2.00`、basis `run <名字>`、日期是 `as_of`）；`confirmations.screen_text` 與 `summary` 相同；`confirmations.sha256` 等於 `common.bundle_sha256(bundle)`（預估沒進 bundle）。
- **W7 `test_an_estimate_that_cannot_be_worked_out_is_allowed_and_says_so`**：有上限、有餘額、沒有歷史（或用出貨的空價目表）→ pending；`summary` 第 3 行含「無法預估」與原因（沒有歷史時含「還沒有成功跑過」；有歷史但價目表為空時含「尚未填入價目」，不含「還沒有成功跑過」）；不含 `US$`。
- **W8 `test_the_run_name_is_judged_before_the_cap`**：run 名稱已被佔用且超過上限 → 回的是名稱的拒絕文字，不是上限的。
- **W9 `test_a_slurm_launch_never_reads_the_cap_the_rates_or_the_index`**：Slurm 環境，monkeypatch `_cost.cap_problem`、`_cost.launch_estimate`、`_cost.load_rates`、`store.cloud_cap` 為一被呼叫就丟錯 → pending 正常；`summary` 與沒接線前逐字相同（`build.launch_screen(b, "lab-a")` 的結果，沿用 `test_human_channel.py:182` 的比對）。
- **W10 `test_the_composed_pipeline_entry_is_checked_the_same_way`**：用 `request_pipeline_launch`（夾具沿用 `test_pipeline_launch.py` 的 `d` 與組合管線，環境換成 Google Batch）超過上限 → 同樣被拒、列數不變；或，若夾具無法造出 Google Batch 的組合送出，直接呼叫 `actions._finish_launch` 並在測試註解寫明（兩個入口都經它，由 `test_pipeline_launch.py:486` 釘住）。
- **W11 `test_a_local_caller_without_an_account_is_not_checked_against_a_cap`**：`caller=None`（stdio 且 `person` 能問）到 Google Batch → 不被上限拒絕（即使沒有任何 `cloud_caps` 列）；`summary` 第 3 行是「沒傳 cost」的預設那一行；`cap_problem` 沒被呼叫。
- **W12 `test_one_person_over_the_cap_does_not_block_another`**：A 已用滿被拒；B（自己的上限內）在同一個索引上 pending。
- **W13 `test_the_yes_that_already_exists_is_not_checked_again`**：第一次呼叫 pending → 本人按送出（測試用 `confirm.approve`）→ 把上限調成 0 → 第二次同參數呼叫 → 仍回 `_queued`（取回工作編號）；`jobs` 恰好一個 `launch_nextflow`。（鎖住「檢查在 `find_approved` 之後」這個有意的順序，見作法 1。）
- **W14 `test_the_refusal_is_the_one_cap_problem_gives`**：`_finish_launch` 的拒絕訊息 == `"未送出：" + cloud_cost.cap_problem(...)` 的回傳（同一組輸入）。
- **W15 `test_no_secret_path_or_sql_in_the_refusal`**：W1／W3 的訊息不含 `Traceback`、`SELECT`、`.db`、`tmp_path` 的字串、token、另一位使用者的名字。
- **W16 `test_the_words_of_the_refusal_and_the_screen_have_no_other_currency`**：W1／W6／W7 的訊息與 `summary` 不含 `NT$`、`TWD`、`新台幣`、`匯率`、`exchange rate`。

確認畫面（`build`）：
- **B1 `test_the_first_line_no_longer_says_there_is_no_estimate`**（即「必須更新的既有斷言」那一個）：二參數 `build.launch_screen(box.bundle(), "gcb1")` 的 `lines[1]` 等於新的 `GCB_COST` 全句（作法 4）。
- **B2 `test_the_second_line_without_a_cost_is_the_plain_no_estimate_line`**：二參數呼叫的 `lines[2]` 等於「沒傳 cost」那一行，含「無法預估」，不含 `US$`；整段畫面仍過 `test_gcb_launch.py:730` 的正規式。
- **B3 `test_a_known_cost_prints_two_decimals_the_basis_and_the_date`**：`cost={"usd": 2.5, "basis": "run old-1", "as_of": "2026-10-24", …}` → 第 3 行與作法 4 逐字相同（`US$2.50`）；`usd` 為 `0.0` 時印 `US$0.00`（不當成「沒有」）。
- **B4 `test_an_unknown_cost_prints_the_first_reason`**：`cost={"usd": None, "unknown_reasons": ["a", "b"], …}` → 第 3 行含「無法預估（a）」，不含 `b`；`unknown_reasons` 為空 → 「原因不明」。
- **B5 `test_a_long_or_hostile_reason_is_escaped_and_cut`**：原因含換行、`\x1b[31m`、300 字 → 畫面是單一行（`lines` 數量與沒有它時相同）、控制字元被寫成可見的跳脫、截在 200 字內。
- **B6 `test_a_hostile_basis_cannot_break_the_screen`**：`basis` 含換行與跳脫碼 → 同上，畫面行數不變。
- **B7 `test_the_slurm_screen_is_byte_identical`**：沿用 `test_gcb_launch.py:1103` 的雜湊（既有測試，不改，列在這裡是為了 verifier 確認它仍綠）；另加：`build.launch_screen(b, "lab-a", {"usd": 1.0})`（Slurm 環境傳了 cost）的結果與不傳時逐行相同。
- **B8 `test_no_file_still_says_there_is_no_estimate_and_cap`**：`platform/`、`docs/`、`README.md` 的文字檔中，沒有任何一個含「還沒有費用預估與上限」或「接線之前確認畫面仍寫」（除了 `specs/` 底下已歸檔的舊計畫，那些不掃）。

`cloud_cost` 兩處：
- **C1 `test_launch_estimate_is_estimate_launch_with_the_defaults`**：以環境變數指定索引後，`launch_estimate(plat, {"pipeline": p}, uid)` 與 `estimate_launch(索引, plat, uid, p, load_rates())` 結果相等；`bundle` 缺 `pipeline` 或不是字典時不丟錯，回 `NO_HISTORY`。
- **C2 `test_estimate_says_why_when_a_run_exists_but_cannot_be_priced`**：有一個成功、同 pipeline、Google Batch 的 run，但價目表為出貨的空表 → `usd None`、`basis None`、`unknown_reasons` 含「尚未填入價目」、**不含**「還沒有成功跑過」。
- **C3 `test_estimate_still_says_no_history_when_there_is_no_candidate`**：只有 Slurm 的 run、別人的 run、失敗的 run、別的 pipeline 的 run → `NO_HISTORY`（與 `test_cloud_cost.py:290` 同結論）。
- **C4 `test_a_priceable_older_run_still_beats_an_unpriceable_newer_one`**：同 `test_cloud_cost.py:282` 的情境，`launch_estimate` 回舊的那個的金額與 basis（鎖住修正沒改壞既有行為）。

憲法與範圍（多數是既有測試，列出讓 verifier 確認它們仍綠）：
- **K1**（既有）`test_scope.py` TC-070／TC-071／TC-061：平台原始碼不啟動任何程式，沒有 `station` 這個字（含註解與字串，不准拆字串規避）。新增的 `_cloud_check`、`launch_estimate`、`cost_line` 與測試檔都不得含 `subprocess`、`Popen`、`threading`、`while True`、`nohup`、`setsid`、`ssh`、`socket`、`urllib.request`。`test_cloud_wire.py` 前 40 行要有 `# Nothing existing: <≥15 字理由>`（TC-070）。
- **K2**（既有）`test_cloud_cost.py:602`（`dir(actions)` 沒有名稱含 `cloud` 的公開名）、`:604`／`:628`（`cloud_caps`／`cap_usd`／`cloud-cap` 只在 `store.py`、`cloud_cost.py`、`cli.py`）：仍綠。
- **K3**（既有）`test_cloud_cost.py` 的 `test_nothing_stops_a_running_job_and_no_policy_channel_exists`：`abf_platform/` 沒有 `watchdog`、`POLICY`；`cloud_cost.py` 沒有 `enqueue_cancel`、`cancel_run`；`jobs` 的 `kind` 清單仍是原來六種。另加一條斷言到 `test_cloud_wire.py`：`inspect.getsource(actions._cloud_check)` 與 `build.cost_line` 不含 `cancel`。
- **K4**（既有）`test_cloud_cost.py` 的 `test_no_other_currency_in_the_source_or_the_rates`：`cloud_cost.py` 與出貨價目表不含 `NT$`／`TWD`／`新台幣`／`匯率`／`exchange rate`；本任務對 `cloud_cost.py` 的新增碼也不得含。
- **K5**（既有）工具數量仍 13、沒有新網頁路由（`test_gcb_launch.py:1063–1069`，注意舊計畫寫的是 12，現況是 13）；`test_web_parity.py` 不動、仍綠；`tests/platform_test.sh` 綠。
- **K6**（手動案例，依 README 通例：executor 把證據貼進 ledger，verifier 自己重跑核對）：`git diff --stat origin/v3...HEAD` 只出現「範圍：檔案」列的 9 個檔；`actions/__init__.py` 的 diff 只在 `_finish_launch`、`_cloud_check`、第 27 行 import；`build.py` 的 diff 只在 `GCB_COST`、`cost_line`、`gcb_launch_screen`、`launch_screen`。

### 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
1. `platform/tests/test_gcb_launch.py::test_the_screen_says_google_bills_the_lab_in_its_first_paragraph`（:720–）的 `sentence`（:725–726）與 `assert lines[1] == sentence`：以前＝句子含「平台目前還沒有費用預估與上限；實際金額請看 Google 的帳單。」；以後＝句子是新的 `GCB_COST` 全句（作法 4，沒有那一句，直接接「主控程序跑在平台主機上，…」）。理由：那句話在接線後是假的。同函式其餘斷言（含 :730 的「無數字金額」正規式、各欄位標籤、檔案區塊標題）**原樣不動**，且對二參數呼叫的整個畫面仍要過。
2. `docs/CLOUD.md:41`、`docs/PLATFORM.md:292`、`docs/TESTING.md:586` 的文字（不是測試斷言，但它們逐字寫著「還沒有接」；由 B8 與 `test_cloud_cost.py` 的文件測試把關）。
3. **不會、也不准變紅**（executor 先跑，紅了就停下回報，不改測試）：`test_gcb_launch.py:1103`（Slurm 畫面雜湊）、`test_human_channel.py:182`、`test_keep_submissions.py:1130`（終端機送出的 `screen_text` 比對）、`test_pipeline_launch.py:486–495`（兩入口共用 `_finish_launch`、簽名不變）、`test_web_parity.py`、`test_cloud_cost.py` 全檔、`test_scope.py`、`test_gcb_ce.py`、`tests/no_per_pipeline_config.sh`、`tests/credentials_stay_in_settings_test.sh`。

## 完成標準（done when）
- 自動：W1–W16、B1–B8、C1–C4 全綠；K1–K5 對應的既有測試仍綠；全套綠（含 `tests/platform_test.sh`）；工具數量仍 13；Slurm 的送出、內容包、畫面一個位元都不變。
- `git diff --name-only origin/v3...HEAD` 只出現「範圍：檔案」列的 9 個檔；**不得**出現任何「禁碰」或「另外不碰」的檔。
- `docs/CLOUD.md`、`docs/PLATFORM.md`、`docs/TESTING.md` 更新完；`docs/CLOUD.md` 白話寫明「從網頁或 AI 送出才受上限管、管理者的終端機入口不管」「目前不會自動停止正在跑的雲端工作」「價目表目前是空的，所以預估都是無法預估」。
- PR 說明必須寫明：①今天價目表為空，所以預估一律「無法預估」，上限只擋得住「沒設上限／上限 0／本月已用滿」；②終端機入口與無帳號 stdio 不受管（裁決 5）；③「必須更新的既有斷言」逐條；④不自動停。
- 手動（維護者，他自己的 GCP 帳號；**第 1–3 步不花錢**，因為都在確認畫面之前被擋或只看畫面，不按「送出」）：
  1. 對一個帳號 `abf-platform user cloud-cap <名> 0`，從網頁（或 AI）對 `gcb1` 送出：確認被白話拒絕，訊息有上限／已用／剩下，且 `jobs`、`confirmations` 沒有新列。
  2. 同一帳號改成沒設上限的另一個帳號再送：拒絕，訊息提到 `cloud-cap`。
  3. 對有餘額的帳號送出：確認畫面第二行是「費用預估：無法預估（…）」並帶原因（價目表仍空）；不要按「送出」。
  4. 對 nano4（Slurm）環境送出：畫面與以前完全相同。
  5. （等 `cloud-rates-fill` 完成、價目表有真資料後才做）有歷史的 pipeline 第二次送出，畫面第二行有 `US$` 金額與 basis。

## 環境事實
（以 `git fetch -q origin` 後的 `origin/v3` @ `817898f` 為準；以 `MSYS_NO_PATHCONV=1 git show "origin/v3:<path>"` 讀）
- `platform/abf_platform/actions/__init__.py`：import 在 :27（已有 `compute_envs, jobs, status, store, su` 等）；`_caller_id` :427；`_no` :431（回 `{"ok": False, "sent": False, "message": …}`）；`_ask` :452；`request_launch` :562–581（收 `caller`、`person`、`clock`、`remote`，**沒有 `index_path`**）；`_finish_launch` :597–607（`find_approved` :599→`_queued`、`check_run_name` :601–605、`build.launch_screen` :606、`_ask` :607）；`request_pipeline_launch` :610–626（:626 同樣呼叫 `_finish_launch`）。`Caller` 的說明（:48–51）：`None` 是本機終端機或 stdio，「sees and uses everything」。
- `platform/abf_launch/build.py`：`is_gcb` :269；`GCB_COST` :463–464（唯一使用處是 :483；別處沒有 import 它）；`GCB_CANCEL_NOTE` :465；`gcb_launch_screen` :479–496（`lines[0]` 標題、`lines[1]` 是 `GCB_COST % ce["project"]`）；`launch_screen` :533（Google Batch 分支 :535–536）；`relaunch_screen` :613–617（呼叫二參數 `launch_screen`；Google Batch 的 run 在 `_predecessor` 就被 `GCB_NO_RESUME` 拒絕，`build.py:344`，所以這條路不會走到 Google Batch 的畫面）。`build.py` 已有 `from abf_platform import agents, compute_envs, jobs, status, store`（:19）。
- `platform/abf_launch/terminal.py`：`PREFIX = "| "`（:13）、`esc`（:17）、`pair`（:49）。
- `platform/abf_launch/cli.py`：`cmd_launch` :77，直接呼叫 `build.prepare_launch` :84 與 `launch_screen(bundle, ce_name)` :93，**不經過 `actions.request_launch`**；`_account` :60 的說明寫著「the terminal is the administrator's」。
- `platform/abf_platform/cloud_cost.py`：`NO_HISTORY` :24；`estimate_launch` :208–217（走訪 `_runs_of` 的結果，成功＋同 pipeline 才算；`run_tasks_cost` 回 `usd None` 就跳過）；`NO_CAP` :224–225；`cap_problem` :228–261（非 Google Batch 環境 :233–235 立即回 `None`；沒設上限 :238–240；預設路徑 :236–237）。
- `platform/abf_platform/store.py`：`default_index_path` :276（`ABF_PLATFORM_DB` 優先）、`default_tokens_path` :285、`set_cloud_cap` :747、`cloud_cap` :761。
- 價目表出貨為空：`platform/abf_platform/data/cloud_rates.json`（`"regions": {}`）。因此今天 `cost_of_tasks` 對任何 task 都回未知，理由含「尚未填入價目」（`cloud_cost.py:104–105`）。
- 憲法：平台不啟動程式（TC-071）；平台原始碼不含 `station` 這個字（TC-061）；新 `.py` 前 40 行 `# Nothing existing:`（TC-070）。
- 測試現況（`test_gcb_launch.py`）：`sentence` :725–726；「無數字金額」正規式 :730；Slurm 畫面雜湊 :1103；工具數 13：:1063–1069。`test_cloud_cost.py`：`World` :184、`test_estimate_skips_a_newer_run_it_cannot_price` :282、`test_no_history_means_unknown_estimate_not_a_guess` :290（斷言 :295 要有「還沒有成功跑過」）、`dir(actions)` 斷言 :602、`cloud_caps` 掃描 :604／:628。
- 確認的有效期 600 秒（`test_human_channel.py:429` 一帶的 `now + 601`）。
- 文件現況：`docs/CLOUD.md:41`、`docs/PLATFORM.md:292`、`docs/TESTING.md:579–588`。`docs/OPERATIONS.md` 沒有需要改的字句。

## 不做
- 不自動停止任何正在跑的工作：沒有 watchdog、沒有 `POLICY` 通道、不建 `cancel_run` job。
- 不做 `resourceLimits`／`maxvCpus` 估價；不用 `cpus` 反推機器型號。
- 不填價目表（`cloud-rates-fill`）；不改 `cloud_rates.json`。
- 不給 `abf-launch` 終端機入口（`abf_launch/cli.py`）接上限與預估（裁決 5）；不改 `relaunch_screen`／續跑／重跑（Google Batch 的 run 本來就不能續跑或重跑）。
- 不改 `cap_problem` 的判斷式與拒絕文字；不改 `get_run`、MCP 工具、網頁路由或網頁畫面；不新增公開動作名稱。
- 不在畫面或訊息出現台幣或換算；不新增 `index_path` 參數。
- 不在確認畫面顯示「本月已用／剩多少」（只有拒絕訊息帶這三個數字；要顯示在畫面是 012d 的費用頁）。

## 裁決（2026-10-24，developer-agent 起草；本段與上文一致，若有衝突以本段為準）
1. **檢查放在 `_finish_launch`，不放 `request_launch` 本體。** 理由：一般 nf-core 送出與組合管線送出共用 `_finish_launch`（:581、:626），放那裡一處改好、兩個入口都管；位置仍在 `check_run_name` 與 `build.launch_screen` 之間，與任務單相符。**預設採此做法。**
2. **順序＝名稱 → 上限 → 畫面。** 「本人已按過送出的第二次呼叫」在檢查之前直接取回工作編號，不重查（視窗最長 600 秒，接受；W13 鎖住）。
3. **預估算不出來＝允許，畫面寫「無法預估」加第一個原因。** 沒設上限＝拒絕（cloud-cost 裁決四）。今天價目表空，所以今天一律「無法預估」。
4. **畫面：第 1 行保持費用／收費那一句（只拿掉假話），預估獨立成第 2 行。** 理由：第 1 行的「由 Google 向實驗室的 Google Cloud 帳號收費」是 C-2 的既有承諾（`test_gcb_launch.py` TC-062 系列），不混進數字；預估行在第 2 行，使用者一眼看得到。預設（沒傳 `cost`）也印一行「無法預估」，不是沉默。
5. **沒有帳號的呼叫者（`caller is None`：管理者的終端機、本機 stdio）與 `abf-launch` 終端機入口不受上限管。** 理由：上限是「每人」的，沒有帳號就沒有「這個人」可以套用；`Caller` 的定義與 `_account` 的說明都把這兩個入口當成管理者本人（`actions/__init__.py:48–51`、`abf_launch/cli.py:60–66`）。**這是一個缺口**：持有終端機的人可以用 `--user` 替任何帳號送出而繞過該帳號的上限。取捨：把終端機也接上需要改 `abf_launch/cli.py`（本任務不碰，且 `resume-edit-params-b` 也在動這個檔），而且會讓管理者自己的操作被自己設的上限擋住；不建議在本任務做，若維護者要，另開小任務。**預設採此做法，PR 說明與 `docs/CLOUD.md` 要寫明。**
6. **預估放在畫面文字，不放 `bundle`。** 理由：`bundle` 是被雜湊與比對的「會被送出的全部內容」，預估是會隨時間變的資訊，放進去會讓 `find_approved` 對不上。
7. **`estimate_launch` 的理由修正屬本任務。** 理由：不修的話，價目表為空時畫面會對有歷史的使用者說「你還沒有成功跑過」，是錯的；修法不改變有可估價 run 時的任何輸出。
8. **工具數量是 13，不是舊計畫寫的 12**（`test_gcb_launch.py:1063–1069` 現況）；不新增工具。
9. **import 一律帶底線別名、`actions` 內不出現 `cloud_cap`／`cap_usd`／`cloud-cap`**（作法 1），否則 `test_cloud_cost.py:602／604／628` 會紅。
10. **與 `resume-edit-params-b` 的衝突處理**：本任務的函式清單見檔頭；後到的 rebase，衝突若出現在 `build.py` 或 `actions/__init__.py`，只可能在 import 行與檔內相鄰位置，逐一以兩邊都保留解決，不重寫對方的函式。

## 裁決二（2026-10-24 20:10 developer-agent；以本段為準）
1. Caller 為 None（本機終端）不套上限：接受，PR 與 CLOUD.md 寫明這個缺口；終端 `--user` 繞過上限另案（會動 abf_launch/cli.py，排在 resume-edit-params-b 之後）。
2. （由裁決三 1 撤回）
3. 估計放在確認頁第 2 行，接受。W10 可直接呼叫 `_finish_launch`。行號漂移以函式名為準。

## 裁決三（2026-10-24 20:30 developer-agent，回應出題退回；以本段為準）
1. **撤回裁決二 2。** 我搞錯了流程：按下送出那一刻工作就已經建立，第二次呼叫只是回傳工作編號，那時再擋只會說假話（「未送出」）或得取消已排隊的工作（維護者定「不自動停」）。所以照作法 1 原文：第二次呼叫不重查，W13 照原文。上限的把關點是「建立確認頁之前」；確認頁 600 秒有效期內上限被調低的窗口，寫進 PR 與 CLOUD.md 當已知限制。
2. B8 的掃描排除 `platform/tests/test_cloud_wire.py` 本身（以路徑排除，不准拆字串）。
3. 「算不出」那一行：只截「原因」那一段到 200 字，句尾聲明（不會自動停止已經在跑的工作）永遠完整保留；TC-031 照此。
4. 不需要 migration：本任務不改任何資料表或欄位（store.py、receiver.py 都不碰）。

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
