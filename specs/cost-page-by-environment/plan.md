---
id: cost-page-by-environment
title: 費用頁改以運算環境為單位（每環境一列可展開）＋分析頁費用列
tier: B
kinds: ui, backend
risk: M
lane: web-cost
base: v3 (origin/v3 @ b3ec5b32)
blocked_on: cost-docs-rewrite
source: 維護者 11-06 對費用頁 v4（Version 6）答「好的可以」；DESIGN.md 第 11 項（由 cost-docs-rewrite 改寫後為準）
---

## 目標

`GET /usage` 改成「一個運算環境一列，可展開看該環境的分析」：單位跟著環境（SU 或美元），不跨環境加總，只有一個環境時就是一列；刪掉 NT$、Reconciled 與「國網／雲端」二分；分析頁新增一列費用（環境／用量／狀態／範圍）。後端先給出「每個分析屬於哪個環境、用什麼單位、用量多少」。對使用者的意義：用 Slurm 站台、Google、AWS 各一份分析的人，不會再看到被誤歸為國網的雲端用量，也不會看到不同單位被加在一起。

`blocked_on: cost-docs-rewrite`：本任務依改寫後的 DESIGN.md 第 11 項；該文件改好、合併後才派。本任務**不碰** DESIGN.md、PLATFORM.md、CLOUD.md。

## 維護者原話（verifier 出題用）

- 「國網／雲端二分法很奇怪」（他要求參考 Seqera 或其他平台；查證結果見「環境事實」：Seqera 沒有跨分析的費用頁，費用在單次 run 頁的 Metrics「Estimated cost」；Terra 分三層；DNAnexus 以專案上限管；Galaxy 沒有——沒有任何一家把「國網／雲端」當頂層分類，一律以環境／專案為單位）。
- 費用頁 v4（Version 6）：他回「好的可以」。
- 定案草稿：https://claude.ai/artifact/DguBi1tA1vpwmj1B7zd1GY （executor 不必讀；版面以改寫後 DESIGN.md 第 11 項為準）。
- 名稱「每月費用提醒額度」**不在本任務範圍**（屬 cost-reminder-quota）。
- 任務簡述見「目標」；網頁畫面改變須 1440／390 px × zh／en 四張截圖＋白話說明、不得新色票、用字走既有用字表。

每句至少一條測試：見「失敗先行測試」env01–env14。

## 範圍：檔案

只准改：
- `platform/abf_platform/web_cost.py`（整頁改版；STRINGS 是本頁的用字表）
- `platform/abf_platform/web_board.py`（分析頁費用列；STRINGS 加字；STYLE 樣式只用現有 token；`_mast` 與 `su_text` 不動）
- `platform/abf_platform/web.py`（`read_run` 多取一次 `actions.run_usage`；`usage_page` 只改傳遞，不加新路由）
- `platform/abf_platform/actions/__init__.py`（`my_usage` 新形狀；新增 `run_usage`；抽出共用的 `_usage_item`）
- `platform/abf_platform/cloud_cost.py`（只有 `_launch_facts` 多回 `ce`、`platform` 兩個鍵，既有三鍵與簽章不變）
- `platform/abf_platform/mcp_server.py`（只改 `my_usage` 工具說明文字，與模組頂端說明若提到「國網 SU」才改）
- 測試：`platform/tests/test_web_cost.py`、`test_web_bugs_b.py`、`test_su_usd.py`、`test_web_parity.py`（WEB_ONLY 加 `run_usage`）、`test_actions_layer.py`（BASELINE 重釘）、新檔 `platform/tests/test_cost_by_env.py`
- `docs/TESTING.md`（加本功能的手動截圖步驟與測試清單；**不是** PLATFORM／DESIGN／CLOUD）

**不准碰**：`docs/PLATFORM.md`、`docs/CLOUD.md`、`DESIGN.md`（cost-docs-rewrite 負責）、`platform/abf_platform/su.py`（`month_total` 不改不刪，見作法 1）、`web_board._mast`（見「待決」）、`platform/abf_station/`、`.github/`。

## 作法

### 1. 查證：`su.month_total` 會不會把本機／雲端誤計成國網 SU？（他的推論，已獨立查，origin/v3 @ b3ec5b32）

結論：**他的推論成立，而且 v3 現行費用頁用的是另一套迴圈，只防住一半。**

- `su.month_total`（su.py:190）把使用者名下、該月開始的**每一個** run 都加起來，全部以呼叫端給的**單一 site** 計價，不看運算環境種類；任何一個 run 算不出就整個回 None。所以若費用頁用它：雲端（Google／AWS／Azure／K8s）run 的 task 只要有 cpus／realtime 就會被乘上國網分區係數算成 SU，沒有 `queue` 的雲端 task 則讓整個總數變 None。
- 但 v3 的費用頁**沒有**用它：`git grep month_total origin/v3 -- platform` 只出現在 su.py 本身和 test_estimate_su.py（只有測試用）。是 `docs/PLATFORM.md` 770–782 行寫「國網 SU 卡用 `su.month_total`」寫錯了（交給 cost-docs-rewrite 更正，本任務不改）。
- 現行 `actions.my_usage`（actions/__init__.py:188）自己的迴圈改為：跳過 `facts is None or facts["cloud"]` 的 run 再加總。這有三個洞：
  1. `_launch_facts` 的 `cloud` 只在環境類型是 `googlebatch-platform` 時為真（cloud_cost.py:171）。**AWS Batch、Azure Batch、K8s 的 run 被標成 `where="nchc"`，被加進國網 SU 總數**。
  2. 環境紀錄已被刪掉（`compute_envs.get` 回 None）的 run 也是 `cloud=False`，同樣被當成國網。
  3. 總數用 `rates["default_site"]` 計價，每列卻用 run 自己的環境 `suSite`（`su.site_of_run`）；兩個 Slurm 站台並存時總數與各列對不起來（AR01 F2、AR08 FU-1 已有重現）。
- 「本機（非平台）run」：沒有 hand-off 紀錄，`facts is None`，v3 是**跳過、不計**，沒有誤計；本機環境類型尚不存在（issue #367，不做）。
- 修法：費用頁與 `my_usage` **一律不用** `month_total`；改成「依每個 run 最新一筆 hand-off 紀錄所指的環境分組，單位由該環境的 `platform` 決定」，不存在跨環境的總數，所以三個洞同時消失。`month_total` 留在原處（test_estimate_su 釘著它），不被任何頁面呼叫。

### 2. `_launch_facts` 加鍵（cloud_cost.py）

回傳 `{cloud, location, pipeline, ce, platform}`：`ce` 是 hand-off 列的環境名（可能是 None），`platform` 是該環境紀錄的 `platform` 類型字串（環境已刪或沒填為 None）。既有三鍵語意不變（`cloud` 仍只對 Google Batch 為真，`month_used` 等舊呼叫者靠它）。簽章 `(platform_path, run_name)` 不變（test_web_cost.py:295 會 monkeypatch 它，替身回傳的 dict 沒有新鍵時，新程式要用 `.get`，且視為「沒有 hand-off 紀錄」之外的未知環境）。

### 3. 單位規則（每個環境一種單位，由 `platform` 定）

| 環境 `platform` | 單位 | 每分析用量 |
|---|---|---|
| `slurm-platform` | SU | `_su_of_run`（用該 run 自己環境的 `suSite`）；`usd_approx` 照舊當旁註，匯率日期缺就 None |
| `googlebatch-platform` | USD | `cloud_cost.run_tasks_cost`（費率檔空則 None＋原因） |
| `awsbatch-platform`／`azbatch-platform`／`k8s-platform` | USD | **None**，原因「尚無此環境的費用估算」（雙語照 `_reason` 的「中文 (English)」格式）；不得算成 0 |
| 其他 KINDS 或環境已刪／沒有 hand-off 紀錄 | 無單位（`unit: None`） | None，原因沿用 `_NOT_SENT_HERE` 或「環境紀錄已不存在 (the environment is no longer on record)」 |

未知一律是 None＋原因，絕不是 0。執行中的分析：`state:"running"`，用量 None，原因 `su.RUN_NOT_ENDED`（沿用）。

### 4. `my_usage` 新形狀（actions）

```
{ "month": "YYYY-MM",
  "environments": [ { "name": str|None, "kind": str|None,     # kind＝compute_envs.KINDS 的顯示名（Slurm／Google Cloud Batch…），給網頁當小字，web_cost 不得 import compute_envs
                      "unit": "SU"|"USD"|None, "site": str|None,   # site 只有 SU 環境有
                      "total": float|None, "usd_approx": float|None,   # usd_approx 只有 SU 環境有
                      "unknown_runs": int, "unknown_reasons": [str], "analyses_count": int,
                      "analyses": [ {name, started_at, state:"running"|"estimate", value: float|None, usd_approx, unknown_reasons} ] } ],
  "cloud": { …… 維持 v3 的五鍵：used_usd, unknown_runs, cap_usd, remaining_usd, currency …… } }
```
- 刪除 `su`（總數）與 `runs`（扁平列）兩鍵；`cloud` 整段不動（上限／剩餘屬 cost-reminder-quota，本任務不改它的語意，見「待決」）。
- 環境的 `total`：同環境內已知用量的加總，`unknown_runs` 是該環境算不出的分析數；**沿用 v3 雲端卡的做法**（已知的加總＋另有 N 個無法計算），不是「有一個未知整列變 None」；整個環境沒有任何已知用量時 `total=None`。跨環境永不相加。
- 排序：環境依「最新一個分析的開始時間」新到舊；`analyses` 新到舊，每環境最多列 50（`_USAGE_RUNS_CAP`），`analyses_count` 是真實總數，`total` 對全部分析計算、不只對列出的 50 個。
- 只列呼叫者自己的 run；`caller=None` 仍回 `{"found": False, ...}`（v3 行為）。純讀，不寫任何東西。
- 輸出的 JSON 不得含 `twd`／`NT`（test_co11 與 test_no_other_currency 的斷言保留）。

### 5. 新增 `actions.run_usage(index_path, run_id, *, caller, platform_path)`（分析頁費用列用）

回 `{"found": True, "environment": name|None, "kind", "unit", "value", "usd_approx", "state", "unknown_reasons"}`；run 不是呼叫者的或不存在，回與 `get_run` 相同的 not-found。與 `my_usage` 共用 `_usage_item`，不得另寫一套計價。**網頁專用、不是 MCP 工具**：在 `test_web_parity.py` 的 `WEB_ONLY` 加一行 `"run_usage": "the cost row of the run page (cost-by-environment): one run's environment, unit and usage; reads only; no MCP tool (get_run already carries su)"`。`get_run` 的鍵集合不動。

### 6. 費用頁版面（web_cost.py）

- 去掉四張卡（國網 SU／雲端已用／雲端上限／雲端剩餘）與「執行位置」欄，去掉 `where_hpc`、`where_cloud`、`card_su*`、`card_used*`、`_HPC`。
- 標題列、上一月／下一月導覽、`bad_month` 提示、`empty` 句保留。
- 每個環境一個 `<details class="pgroup env">`（**零 JS、原生展開**；`pgroup` 的樣式 web_board STYLE 已有）；`<summary>` 一行：環境名（連結不加）＋kind 小字＋用量（SU 環境用 `web_board.su_text`，USD 環境用 `US$ %.2f`，未知用 `—`）＋「共 N 個分析」；展開後是既有 `table.tbl`，欄為 分析名稱／開始時間／用量／狀態（狀態沿用 `state_running`／`state_estimate` 與 `state-running` 樣式）。環境只有一個時 `<details open>`。
- 未知的小字：`unknown_runs>0` 時沿用 `unknown_runs` / `unknown_run` 字串；`unit is None` 的環境小字寫原因。
- 上限列：`cloud.cap_usd` 不為 None 時，在頁面最上方留**一行** `<p class="muted">`，字句沿用 v3 的 `card_cap`／`card_left`／`set_by_admin`／`action` 的詞（這幾個字串**留在 STRINGS**，不改名）；為 None 時顯示 v3 的「未設定」。這一行屬 cost-reminder-quota 日後會改，本任務只保證行為不退步（過額時 `state-failed`＋`⚠` 的提醒仍在）。
- `note` 改為：zh「各運算環境用各自的單位（SU 或美元）顯示，不互相換算、不加總。數字依執行紀錄估算，略低於實際帳單。」en「Each compute environment is shown in its own unit (SU or US dollars); nothing is converted or added across environments. Figures are estimates from the run records and a little below the actual bill.」`usd_note`（SU 概算美元的匯率句）原樣保留。**不得出現**：新台幣、NT$、TWD、匯率（usd_note 那一句除外，test 已有扣除寫法）、Reconciled、已對帳、「國網」「雲端」當分類標籤、站台名。環境名由使用者自己取，照原樣顯示並跳脫（不算站台名；`"NC"+"HC"` 拆字規則不變）。
- 每個新字串 zh／en 成對放進 `STRINGS`，英文版不得有 CJK（既有 `no_cjk` 檢查）；zh 遵守用字掃描禁字（你、這個、這次、這個月、還沒、算不出、讀不到、在哪裡、單獨的 run／runs…，執行前 grep `test_web_wording_sweep.py` 的禁字表確認）。

### 7. 分析頁費用列（web_board.py＋web.py）

- 位置：緊接在 `_sum_cards` 與 `_results_cards` 的四張摘要卡之後（執行階段與結果階段都有），一個 `<table class="tbl">` 一列，欄頭 環境／用量／狀態／範圍（en：Environment／Usage／Status／Scope）。現有「運算」「費用」兩張卡**不動**（test_su_usd 釘著它們）。
- 環境：`run_usage` 的 `environment`（None 顯示 `—`）。用量：SU 用 `su_text`，USD 用 `US$ %.2f`，未知 `—`。狀態：`state_running`／`state_estimate` 同費用頁。
- 範圍：說明這個數字算了什麼。依 `su.run_tasks`／`su_of_tasks` 實際行為（讀 `task_usage` 全部列，含失敗的 task），zh「整個分析（含失敗的步驟）」，en「Whole analysis, failed steps included」。**executor 要先在 `su.py` 與 `cloud_cost.run_tasks_cost` 確認兩者都不依狀態過濾，字句才可照用；若有過濾，改寫字句使其與實際相符，並在 ledger 寫明。** 此字串寫成 `STRINGS` 裡一個 key，測試用 key 對應的字串斷言，不要把字句重寫在測試裡兩次。
- `web.py` 的 `read_run` 只多一次 `actions.run_usage(...)`，結果放 `view["usage"]`；web_board 不得 import `jobs／status／compute_envs…`（tc060）。`sqlite3.Error` 時 `view["usage"]=None`，頁面畫一列全 `—`，不得 500。

### 8. 畫面（risk M）

只用現有 token 與現有 class（`pgroup`、`tbl`、`muted`、`sumcards`、`state-running`、`state-failed`、`sym`）；STYLE 有新規則時只能引用 `var(--…)` 既有名稱，不得新增色碼或 token，不得 `style=`。因為 STYLE 變動，CSP 的 sha256 會隨 `web_board.style_hash()` 自動更新（test_co10 驗證）。
截圖：`scripts/dev/ui_check.py --start` 產出 `usage` 與一個分析頁（`results` 與執行中各一）的 1440／390 px × zh／en 共 **4 張**（兩頁各自 4 張，費用頁必附，分析頁費用列另附 4 張），並附 axe 結果；**每張要有一段白話說明**（這張畫面讓人看到什麼、與舊版差在哪）。種子資料要有：一個 Slurm 環境、一個 Google Batch 環境、一個 AWS 環境（單位 USD 但用量 `—`）、一個執行中分析，另一組截圖是「只有一個環境」。CI 沒有 Chromium，這是手動步驟，寫進 `docs/TESTING.md`。

## 失敗先行測試

新檔 `platform/tests/test_cost_by_env.py`（沿用 test_web_cost.py 的 `w` fixture 與 `seed`，`seed` 增一個 `platform=`／`ce_name=` 參數，在 test_web_cost.py 內改，允許）。先寫、現在會紅：

- env01 單環境：只有一個 Slurm 環境的人，`/usage` 的 middle 窗格只有一個 `details.env`、且帶 `open`；SU 值＝該環境分析之和。〔「只有一個環境時一列」〕
- env02 多環境不加總：Slurm（SU）＋Google（USD）＋AWS 各一個分析，middle 內有三個 `details.env`；沒有任何同時含 `SU` 與 `US$` 的總計文字；`my_usage` 回傳沒有 `su` 與 `runs` 鍵，且 `environments` 的每個 `unit` 只有一種。〔「不加總」〕
- env03 **誤計回歸（本任務的查證）**：AWS Batch 的 run（hand-off 列指向 `awsbatch-platform` 環境）不進任何 SU 總數：Slurm 環境 `total` 只含 Slurm run；AWS 環境 `unit=="USD"`、`total is None`、原因含「尚無此環境的費用估算」。同樣斷言環境紀錄被刪掉的 run 落在 `unit is None` 的環境，不計入 Slurm 總數。
- env04 兩個 Slurm 環境 `suSite` 不同：各自用自己的站點計價（總數與各列相符），不用 `default_site`。
- env05 每環境分析最多列 50、`analyses_count` 為真實數、`total` 含全部分析。
- env06 未知不當 0：Google 費率檔空 → 該環境 `total is None`、頁面顯示 `—`＋原因；執行中分析 → `state=="running"`、不進 `total`、`unknown_runs` 加一。
- env07 別人的分析不出現（bob 看不到 ann 的環境列；`caller=None` 回 `found False`）。
- env08 刪除清單（zh＋en，`/usage` 與 `/usage?lang=en`）：middle 不含 `NT$`、`新台幣`、`TWD`、`Reconciled`、`已對帳`、`國網`、`雲端已用`、`雲端剩餘`（上限那一行的字串是 `card_cap`／`card_left` 而不在此清單：`雲端上限` 與 `雲端剩餘` 允許存在，`國網` 與 `雲端已用` 不允許）、站台名；`<script`、`style=`、`<link`、`on*=` 皆無；`/cost` 仍 404。〔「刪 NT$、Reconciled、國網／雲端分區」〕
- env09 分析頁費用列：`/?run=<id>` 的結果階段與執行階段都有一個欄頭依序為 環境／用量／狀態／範圍（en：Environment／Usage／Status／Scope）的表，值對應 `run_usage`；Slurm 完成的分析顯示 `su_text` 的字樣；AWS 分析顯示環境名與 `—`；範圍字句等於 STRINGS 對應 key；別人的分析頁拿不到（沿用 get_run 的 not-found）。
- env10 `actions.run_usage` 與 `my_usage` 對同一分析給同一個 value／state／unknown_reasons；`run_usage` 不在 MCP 工具表（`WEB_ONLY` 有它、`READ_NAMES` 沒有）。
- env11 `web_cost.py`／`web_board.py` 只經 `actions`：重跑 `test_web_cost_module_goes_through_actions_only` 的 AST 掃描。
- env12 `su.month_total` 不被 `platform/abf_platform` 下任何非 su.py 的檔案引用（grep 斷言），守住查證結論。
- env13 讀不到索引（`sqlite3.Error`）時 `/usage` 回空頁（`empty_usage` 新形狀 `{"month", "environments": [], "cloud": {…}}`），分析頁費用列顯示 `—`，皆 200。
- env14 無新色票：STYLE 內顏色字面值集合與 v3 相同；重跑 test_co10（CSP hash）。

## 完成標準（done when）

1. env01–env14 與既有測試全綠；唯一允許的環境紅是 README 通例列的 `test_tc047_tc051_other_docs_untouched`。
2. `git diff --stat` 只含「範圍：檔案」所列；PLATFORM／DESIGN／CLOUD 未動（閱卷者核對）。
3. 4 張（費用頁）＋4 張（分析頁費用列）截圖與白話說明貼進 ledger；axe 無新違規；沒有新色碼。
4. `docs/TESTING.md` 有手動截圖步驟與新測試清單。
5. 「作法 1」的查證結論原樣寫進 ledger，並列出 cost-docs-rewrite 該更正的 PLATFORM.md 770–782 行與 708 行（masthead 描述）給 developer-agent。
6. 在 ledger 的「planIssues」列出下方「待決」項目的最終處理。

### 允許改動的既有斷言（有測試釘住，改動屬預期，不算違規）

下列都是 `git grep` origin/v3 找到的釘點；改它們時須在 ledger 寫「為何」並保留各測試原本想守的性質（讀不到索引不 500、別人看不到、US$ 不轉換、無 JS、CSP hash 等）：
- `test_web_cost.py`：L26 `NOTE_ZH`；L142–152 `test_co01`（四張卡＋note＋表）；co02／co03／co04／co05（卡片數值，改成對 `environments[*].total` 與上限那一行）；L194 `test_ruling12_su_card_ignores_cloud_runs`（改為 env03 的語意）；L205 `ruling13` 英文單複數；L218 `ruling14`；L259；L270 `test_co06_rows_states`；L283–311（`rows[...][2] == "國網"`、`by == {"run-n": "nchc", ...}` 的 `where` 值）；L332、L347（空月）；L477–503 `test_co11`（鍵集 `{"month","su","cloud","runs"}` 與 item 鍵集改為新形狀）；`seed()` 增參數。**保留不動**：L357 `test_co08` masthead、L436 `test_co10`、L456 `test_no_other_currency…`（禁字清單只增不減）、L541 AST 掃描。
- `test_web_bugs_b.py`：L71、L79（`"國網 SU（2026-10）"`、`"雲端已用（本月）"` 標題）；及同檔 `usage()` 的 `usage_data()` 輔助函式（回傳形狀要換成 `environments`）。
- `test_su_usd.py`：L309 `note = "雲端費用以美元顯示，不換算新台幣；國網以 SU 計…"`；該檔其他斷言（L476–478 run 頁費用卡 `SU —`、L530–533 masthead 兩段）**不動**。
- `test_web_parity.py`：`WEB_ONLY` 增 `run_usage`；`WEB_ROUTES["my_usage"]` 說明可更新。
- `test_actions_layer.py`：L28／L36 的 `BASELINE` JSON 內 `my_usage` 的工具說明（只有 mcp_server.py 的說明字改了才需要；重新用原腳本產生，不手改 JSON 以外的鍵）。
- 其他只在工具／路由清單裡點名 `my_usage` 的測試（test_chat_tools、test_guidance、test_human_channel、test_keep_submissions、test_launch_e2e、test_launch_platform、test_mcp、test_oauth_mcp、test_owner_binding、test_pat、test_resume_entrypoints、test_station_envs、test_station_launch、test_confirm_page、test_estimate_su:298）**預期不用改**；若有一條因形狀改動而紅，先查是否真依賴 `su`／`runs` 鍵再改。
- `test_web_board.py:180–216` 與 `test_su_usd.py:530`：masthead 兩段字（`SU —`／`雲端 US$ —`，`class="cost"` 兩個）**不動**（見待決 2）。
- `test_web_wording_sweep.py:484–485`：用 `cost.seed(...)` 把費用頁放進用字掃描；`seed` 的簽章保持向下相容（新參數給預設），掃描的禁字表不得放寬。

## 環境事實

- repo：`C:\Users\marvi\Desktop\agentic-bioflow\agentic-bioflow_v2`，base `origin/v3`（@ b3ec5b32）。DESIGN.md 的限制（零 JS、無 `style=`、單一樣式表＋CSP hash、每人只看自己的）仍成立；tc051 要求路由路徑不含 `cost` 且 `/cost` 回 404；tc060 網頁檔不得 import `confirm/jobs/compute_envs/agents/status`；tc063 不得新增資料表或欄位（本任務**不需要 migration**，全是讀）；tc069 站台名不得以字面值寫在程式裡。
- 資料來源：`task_usage` 表（index.db）；hand-off 紀錄在 platform.db（`jobs.latest_launch`）；環境紀錄 `compute_envs.get(...)["platform"]`、`config["suSite"]`（選填）；SU 費率檔 `su.load_rates()`；Google 費率檔 `data/cloud_rates.json`（`rates` 清單可能是空的，則美元為 None）。AWS／Azure／K8s 目前**沒有**任何每分析費用估算（`cloud_cost` 只有 Google）。
- 每分析 SU 與 USD 的可得性（planIssues 結論）：
  - 每分析 SU：可，條件是分析已結束、`task_usage` 有列且每個 task 有 cpus／realtime／queue 對得上費率檔；執行中、沒有用量紀錄、分區沒有係數時為 None＋原因（`_su_of_run` 已有）。
  - 每分析美元：只有 Google Batch 可，且依賴 `cloud_rates.json` 有該區域費率；AWS／Azure／K8s 缺（見待決 3）。
  - 每分析的「環境名與類型」：**v3 的 `my_usage` 沒有**；`get_run` 也沒有（只有 `run_environment` 給名稱、頁面自己加）。本任務用 `_launch_facts` 加鍵補上。
  - 「範圍」欄位：v3 沒有現成欄位，是新的說明字句（作法 7）。
- 參考平台：Seqera／Terra／DNAnexus／Galaxy 的查證見「維護者原話」第一條；來源 `memory/handoff/2026-11-04-frontend-decisions.md` 任務 7-12～7-14、`2026-11-05-cloud-budget-research.md`。
- 相關弱點：`docs/reports/cloud-burn-2026-11/AR01.md` F2、`AR08.md` FU-1（作法 1 洞 3，含重現，可當 env04 種子）。
- 截圖腳本 `scripts/dev/ui_check.py`。
- PITFALLS 已查（`docs/PITFALLS.md`，用 my_usage／default_site／suSite／web_board／web_cost／/usage／month_total／googlebatch／rates／CSP／style 等詞 grep），無相符項；`docs/solutions/` 不存在。

## 不做

- 本機運算環境（issue #367，他說先不做）；不排 backlog。
- 「每月費用提醒額度」命名、上限的設定與提醒行為（cost-reminder-quota）；`cloud` 段（`cap_usd`、`remaining_usd`、`month_usage`）語意不改。
- 改 `su.month_total`（死碼，只有測試用；留著由 test_estimate_su 守）；改 `su.py`、`cloud_cost.py` 的計價邏輯。
- 為 AWS／Azure／K8s 做費用估算（接 cost-cloud 之類的後續任務）；填 `cloud_rates.json`。
- 改 `docs/PLATFORM.md`、`docs/CLOUD.md`、`DESIGN.md`；改 masthead（`web_board._mast`）。
- 新增路由、資料表、欄位、色票、JS、對外連結。
- 把 `run_usage` 做成 MCP 工具。

### 待決（executor 照預設做，並在 ledger 的 planIssues 回報；developer-agent 看到可改派）

1. **上限行去留**：預設＝留一行（保行為不退步），由 cost-reminder-quota 日後處理；若 cost-docs-rewrite 改寫後的 DESIGN.md 第 11 項說上限整個搬走，則把該行拿掉並同步改 env08／co04／co05 的對應斷言。
2. **masthead 兩段字（`SU —`／`雲端 US$ —`）**：本身也是國網／雲端二分，但被 test_web_board.py:180–216、test_su_usd.py:530–533、test_web_cost.py:357 釘死，且不在「費用頁」的範圍；預設不動，列為後續任務（先看改寫後 DESIGN.md 怎麼說）。
3. **AWS／Azure／K8s 的每分析美元**：預設顯示 `—`＋「尚無此環境的費用估算」；是否要做估算要由維護者另裁。
4. **「範圍」的字句**：預設見作法 7；若改寫後 DESIGN.md 給了定案字句，以 DESIGN 為準。
5. **環境小計遇到執行中分析**：預設沿用雲端卡做法（已知加總＋「另有 N 個分析無法計算」），不是整列變 `—`；若定案草稿（claude.ai artifact）畫的是整列 `—`，以草稿為準並回報。

## 裁決（11-06 追進度，對照定案草稿 Version 6 後加）
- **草稿與規格有一處不一致**：定案草稿（他回「好的可以」）在 SU 旁顯示概略美元（例「1,240 SU ≈ US$ 3.9」，註明依 su_rates.json、不是帳單）；cost-docs-rewrite 合併後的 DESIGN.md 第 11 項寫「never converted」。以草稿為準。
- 本任務的範圍多加兩處：`DESIGN.md` 第 11 項把「never converted」改為「SU 旁可顯示依 su_rates.json 的概略美元，標明不是帳單；不跨環境相加」；`platform/tests/test_cost_docs_spec.py` 釘死 "never converted" 的那一條同步改成新句（這是本任務明示要改的既有測試，不算放寬）。
- 不同環境的數字仍不相加。

## 裁決（自動補，2026-11-06）

驗證者退回的六點，逐項定案（依本計畫既有條文與 repo 的 DESIGN.md 第 11 項、test_cost_docs_spec.py:33）：

1. **範圍矛盾**：以上方「裁決（11-06 追進度）」為準，它晚於並取代「不准碰」「不做」「完成標準 2」的相反字句。
   - 「範圍：檔案」的只准改清單加入 `DESIGN.md`（只改第 11 項的 "never converted" 那半句，改為「SU 旁可顯示依 su_rates.json 的概略美元，標明不是帳單；不跨環境相加」，其餘文字含 "Action-needed" 句、分析頁費用列句一字不動）與 `platform/tests/test_cost_docs_spec.py`（只把 L33 清單中的 "never converted" 換成新句的關鍵字；其餘釘點不動，不放寬）。
   - 「不准碰」與「不做」中的 DESIGN.md 一律刪除；PLATFORM.md、CLOUD.md 仍不准碰。
   - 完成標準 2 改為：`git diff --stat` 只含「範圍：檔案」所列（含 DESIGN.md、test_cost_docs_spec.py）；PLATFORM／CLOUD 未動；DESIGN.md 的 diff 只有第 11 項那一句。閱卷者核對這三點。
   - TC 預期：DESIGN.md 第 11 項不再含 "never converted"，含「不是帳單」之意的新句；test_cost_docs_spec 綠。
2. **截圖張數**：「只有一個環境」那一組算必附，只拍費用頁（env01 的畫面）。必附共 12 張：費用頁多環境 4（1440／390 x zh／en）＋分析頁費用列 4（1440／390 x zh／en）＋費用頁單一環境 4。完成標準 3 照此改。
3. **沒有 hand-off 紀錄的 run（本機非平台 run）**：照作法 3 表格與作法 4 辦理，歸入 `unit: None` 的環境列，`name` 可為 None（網頁顯示 `—`），用量 None 加原因，不進任何 SU 或 USD 總數、不算 0。作法 1 的「v3 跳過不計」只描述 v3 現況（它不誤計），不是新行為的要求。TC-022 照作法 3、4 出題，不需改。
4. **DESIGN 第 11 項的「本月費用提醒額度會超過時的行動提示」**：確認留給 cost-reminder-quota，本任務不做；只保留舊的上限那一行（待決 1）。TC-078 照計畫列為不在範圍。DESIGN.md 該句不改。
5. **範圍字句**：executor 先讀 `su.py` 與 `cloud_cost.run_tasks_cost` 確認不依狀態過濾；字句寫「整個分析（含失敗的步驟）」時失敗 task 用量必須算進去（TC-047 條件式寫法成立）；若有過濾，改寫字句並在 ledger 寫明，TC-046／047 照改後字句比對。測試一律用 STRINGS key 斷言。
6. **spec.md**：本計畫沒有 spec.md，合約「對應需求」欄引用 plan.md 段落（作法 N、env01–env14、裁決、待決、不做、專長守則）。不需改計畫本文。

## 專長守則（ui）

### executor

- 先讀專案根目錄的 `PRODUCT.md`（給誰用、要解決什麼）與 `DESIGN.md`（版面線框、tokens、每個畫面與狀態、維護者的原話例子）。讀不到就 BLOCKED，不自己發明設計。
- 只准用 `DESIGN.md` 定義的 tokens（色彩、字型、字級、間距、圓角）與版面。不新增任何視覺決策：不自創顏色、字型、間距數值，不順手「美化」。
- `DESIGN.md` 沒決定的事，一律寫進報告的「卡住的原因／要問的問題」，不猜。
- `DESIGN.md` 列出的每個畫面、每個狀態都必須做出來，包含空狀態、載入中、錯誤、失敗。少一個就不算完成。
- 遵守計畫寫明的前端限制（例如 CSP、禁用 inline style、不載外部資源、只在允許處使用 JS）。限制與設計衝突時停下來問，不自行取捨。
- 狀態絕不只靠顏色：一律「符號＋文字＋顏色」三者並用。
- 手機寬度可用（不橫向捲動、點擊目標夠大），鍵盤操作時焦點外框可見。
- 介面文字用使用者視角的白話，不露出內部術語、錯誤代碼或程式名詞；錯誤訊息說發生什麼事與下一步。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- `DESIGN.md` 的每個畫面、每個狀態都至少對應 1 個 TC（含空、載入、錯誤、失敗）。
- 維護者的原話例子逐字對應到 TC。
- 計畫列的前端限制各對應 TC（例如頁面不得含 inline style、不得請求外部網址、CSP 標頭存在）。
- 狀態表達 TC：每個狀態輸出的 HTML 同時含符號、文字，不得只靠 class 顏色。

**ACCEPTANCE（閱卷）必須檢查：**
- 把每個有改動的頁面渲染成 HTML 檔（用專案的 test client，或計畫指名的 fixture）。做不到就標 UNVERIFIED，並寫明需要什麼才能驗。
- 對渲染出的 HTML 跑 Impeccable 偵測器（唯讀）：`sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`。
- **FAIL**：違反 `DESIGN.md` 的 tokens／畫面／狀態；違反計畫寫明的前端限制；狀態只靠顏色；缺少 DESIGN.md 列出的畫面或狀態。
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型、AI 範本味等）與品味問題。這些不判 FAIL。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。
- **實際跑起來看（ACCEPTANCE，2026-11-03 加）**：用 `webapp-testing` 的 `with_server.py` 把真正的應用程式起起來，再用 Playwright 驗。腳本路徑 `G:/我的雲端硬碟/謝馬爾/.claude/skills/webapp-testing/scripts/with_server.py`，**先跑 `--help`** 看用法（把它當黑盒子用，不要先讀原始碼）；啟動指令與通訊埠寫在計畫裡。
  - repo 已有 `scripts/ui_check.py` 就直接跑它：1440／390 寬 × zh／en 共 4 張截圖，加 axe-core 無障礙掃描；**axe 出現 serious 或 critical 一律 FAIL**。
  - repo 還沒有 `ui_check.py`：verifier 自己用 Playwright（經 `with_server.py`）拍同樣 4 張截圖；axe 沒跑就標 **axe：UNVERIFIED**，並寫明缺什麼。
  - 截圖只能存到 repo 之外或 `.gitignore` 排除的資料夾，**絕不存進 Drive 工作區**；報告只貼路徑與張數。
  - 起不了應用程式（缺依賴、埠被占）標 UNVERIFIED 並寫明需要什麼，不改以靜態 HTML 當作通過。

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
