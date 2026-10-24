# 測試案例：雲端費用上限接進送出流程（Google Batch）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and file paths stay as they are.
-->

**規格**：`specs/cloud-cost-wire/plan.md`（沒有獨立 spec.md；以計畫含裁決、裁決二、裁決三為準，裁決與正文衝突時以裁決為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞（第一次出現就解釋）：**上限**＝管理者替每個帳號設定的每月雲端美元上限；**已用**＝這個人本月已花的雲端運算費；**預估**＝這次送出約會花多少（依同管線最近一次成功的雲端 run 推算）；**無法預估**＝算不出來，畫面明說，不亂猜；**確認畫面**＝按「送出」之前給本人看的那一頁；**價目表**＝每種機器每小時多少錢的表，出貨時是空的，所以**今天每次預估都是無法預估**；**W／B／C／K 編號**＝計畫「失敗先行測試」與「憲法與範圍」裡的原編號，括號內附上方便對照。

維護者的原話（逐字，取自計畫「維護者原話」）對應：「每人每月上限」「超過就擋」「約／已用／上限」→ TC-001、003、006、010、011；「沒設上限者不准」→ TC-004、005、013、014；「顯示美元、不換算」→ TC-012、021、029；「超過自動停」**不做**（10-24：超上限只擋新送出、不自動停）→ TC-068；「預估不明則允許，畫面寫無法預估」→ TC-023、024、025、026、031；「那句『平台目前還沒有費用預估與上限』換掉」→ TC-015、050。

## User Story 1 — 超過每月上限的新送出，在建立任何東西之前被白話擋下（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | W1；作法 5；維護者「約／已用／上限」 | 例外 | Google Batch 環境；有帳號的使用者上限 US$20.00、本月已用約 US$14.50、同管線最近成功 run 可估價 US$6.00 | 該使用者呼叫 `actions.request_launch` | 回 `ok` 為 False、`sent` 為 False；訊息以「未送出：」開頭，且含 `US$20.00`、`US$14.50`、`US$5.50`、`US$6.00`，並含處理方式（請找管理者調整上限，或下個月再送出） | 自動：`platform/tests/test_cloud_wire.py`（W1，`test_over_the_cap_is_refused_before_anything_is_created`） |
| TC-002 | W1；目標「建立任何東西之前」 | 例外 | 同 TC-001；`_ask` 與 `build.launch_screen` 被設成「一被呼叫就丟錯」 | 同 TC-001 | 沒有丟錯（兩者都沒被呼叫）；`confirmations`、`jobs`、`launches` 三張表的列數與呼叫前相同 | 自動：`test_cloud_wire.py`（W1） |
| TC-003 | W2；維護者「超過就擋」 | 例外 | 上限 US$20.00、本月已用 US$20.00（等於上限）；預估算不出來 | 呼叫 `actions.request_launch` | 被拒絕，訊息含「不能再送出新的雲端分析」；三張表列數不變 | 自動：`test_cloud_wire.py`（`test_a_month_already_used_up_is_refused_whatever_the_estimate`） |
| TC-004 | W3；維護者「沒設上限的使用者送雲端一律拒絕」 | 例外 | 有帳號、沒有設上限 | 呼叫 `actions.request_launch` | 被拒絕，訊息含 `cloud-cap`（告訴管理者要設）；三張表列數不變 | 自動：`test_cloud_wire.py`（`test_a_person_with_no_cap_cannot_launch_to_the_cloud`） |
| TC-005 | W4 | 例外 | 上限設成 0 | 呼叫 `actions.request_launch` | 被拒絕；三張表列數不變 | 自動：`test_cloud_wire.py`（`test_a_cap_of_zero_refuses`） |
| TC-006 | W5；判斷式「已用＋預估 > 上限才拒絕」 | 功能 | 上限 US$20.00、已用 US$14.50、預估 US$5.50（合計剛好 US$20.00） | 呼叫 `actions.request_launch` | 不被拒絕：回 `state` 為 `"pending"` 且有 `confirmation_url`；`confirmations` 多一列 | 自動：`test_cloud_wire.py`（`test_exactly_at_the_cap_goes_on_to_the_screen`） |
| TC-007 | W8；作法 1 順序「名稱 → 上限 → 畫面」 | 例外 | run 名稱已被佔用，且這次也超過上限 | 呼叫 `actions.request_launch` | 回的是「run 名稱」的拒絕文字，不是上限的拒絕文字 | 自動：`test_cloud_wire.py`（`test_the_run_name_is_judged_before_the_cap`） |
| TC-008 | W10；作法 1 兩個入口共用 `_finish_launch` | 例外 | Google Batch 環境；超過上限；用組合管線入口 `request_pipeline_launch`（夾具造不出時，直接呼叫 `_finish_launch` 並在測試註解寫明） | 呼叫該入口 | 和一般 nf-core 入口同樣被拒；三張表列數不變 | 自動：`test_cloud_wire.py`（`test_the_composed_pipeline_entry_is_checked_the_same_way`） |
| TC-009 | W12；上限是「每人」的 | 功能 | 同一個索引上有 A、B 兩人；A 已用滿；B 在自己的上限內 | A 送出、B 送出 | A 被拒；B 得到 `pending`（A 的用量不影響 B） | 自動：`test_cloud_wire.py`（`test_one_person_over_the_cap_does_not_block_another`） |
| TC-010 | W14；作法 5「直接用 cap_problem 的文字」 | 例外 | 同一組輸入 | 比對 `_finish_launch` 的拒絕訊息與 `cloud_cost.cap_problem(...)` 的回傳 | 訊息 == `"未送出：" + cap_problem 的回傳`（沒有改寫、沒有新增文字） | 自動：`test_cloud_wire.py`（`test_the_refusal_is_the_one_cap_problem_gives`） |
| TC-011 | W15；專長守則：錯誤訊息不露內部資訊 | 例外 | TC-001 與 TC-004 的情境 | 看拒絕訊息 | 不含 `Traceback`、`SELECT`、`.db`、測試暫存路徑、token、另一位使用者的名字 | 自動：`test_cloud_wire.py`（`test_no_secret_path_or_sql_in_the_refusal`） |
| TC-012 | W16；維護者「顯示美元、不換算」 | 例外 | TC-001（拒絕）、TC-019（有預估）、TC-023（無法預估）三種情境 | 看拒絕訊息與確認畫面的 `summary` | 都不含 `NT$`、`TWD`、`新台幣`、`匯率`、`exchange rate` | 自動：`test_cloud_wire.py`（`test_the_words_of_the_refusal_and_the_screen_have_no_other_currency`） |
| TC-013 | 完成標準·手動 1 | 例外 | 維護者自己的 GCP 帳號；某帳號用 `abf-platform user cloud-cap <名> 0` 設成 0 | 從網頁（或 AI）對 `gcb1` 送出，不按「送出」 | 被白話拒絕，訊息有上限、已用、剩下；`jobs`、`confirmations` 沒有新列；不花錢 | 手動：`docs/TESTING.md`「Cloud cost wiring」第 1 步 |
| TC-014 | 完成標準·手動 2 | 例外 | 另一個沒設上限的帳號 | 同樣從網頁（或 AI）對 `gcb1` 送出 | 被拒絕，訊息提到 `cloud-cap`；不花錢 | 手動：`docs/TESTING.md`「Cloud cost wiring」第 2 步 |

## User Story 2 — 確認畫面第 2 行寫真實預估，或寫「無法預估」並說原因（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | B1；作法 4；維護者「那句換掉」 | 功能 | Google Batch 環境的內容包 | 二參數呼叫 `build.launch_screen(box.bundle(), "gcb1")` | 第 1 行（`lines[1]`）等於新的整句：「費用：按下 y 之後，這個 run 會在 Google Cloud 專案 %s 裡建立 Batch 工作與虛擬機，由 Google 向實驗室的 Google Cloud 帳號收費。主控程序跑在平台主機上，取消請用平台的取消指令。」（專案名代入；沒有「平台目前還沒有費用預估與上限」那句） | 自動：`platform/tests/test_gcb_launch.py`（`test_the_screen_says_google_bills_the_lab_in_its_first_paragraph`，只改 `sentence` 與它的比對）、`test_cloud_wire.py`（B1） |
| TC-016 | B2；作法 4「沒傳 cost」 | 功能 | 同 TC-015 | 二參數呼叫 `launch_screen`（終端機入口的呼叫方式） | 第 2 行（`lines[2]`）等於「費用預估：無法預估（這個送出入口沒有算預估 (this way of sending does not work out an estimate)）。平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。」，含「無法預估」，不含 `US$` | 自動：`test_cloud_wire.py`（`test_the_second_line_without_a_cost_is_the_plain_no_estimate_line`） |
| TC-017 | B2；作法 4 末段；`test_gcb_launch.py` TC-062 系列 | 功能 | 同 TC-015 | 看二參數呼叫的整個畫面 | 仍含連續的「由 Google 向實驗室的 Google Cloud 帳號收費」；整段不符合正規式 `NT\$\|USD\|US\$\|TWD\|[$＄￥¥€£]\s?[0-9]\|[0-9]\s?(元\|美元\|台幣)`；各欄位標籤與檔案區塊標題原樣都在 | 自動：`test_gcb_launch.py`（同函式其餘斷言原樣不動）、`test_cloud_wire.py`（B2） |
| TC-018 | W5 | 功能 | TC-006 的情境（預估 US$5.50，剛好到上限） | 看回傳的 `summary` | 含「費用預估：約 US$5.50」 | 自動：`test_cloud_wire.py`（W5） |
| TC-019 | W6；作法 4「算得出」 | 功能 | 上限 US$20.00、已用 US$14.50、預估 US$2.00；可估價的 run 名為 `<名字>` | 呼叫 `actions.request_launch` | 回 `pending`；`summary` 的第 3 行（`lines[2]` 去掉前綴「\| 」）逐字等於「費用預估：約 US$2.00（依你最近一次成功的同管線雲端 run <名字> 的實際運算時間推算；只含虛擬機運算費用，不含磁碟與網路；價目讀於 <as_of 日期>）。平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。」 | 自動：`test_cloud_wire.py`（`test_an_estimate_that_fits_shows_its_line_on_the_screen`） |
| TC-020 | W6；作法 4「不得改 bundle」；裁決 6 | 功能 | 同 TC-019 | 比對資料庫裡的 `confirmations` 列 | `screen_text` 與回傳的 `summary` 相同；`confirmations.sha256` 等於 `common.bundle_sha256(bundle)`（預估只在畫面文字，沒進內容包） | 自動：`test_cloud_wire.py`（W6） |
| TC-021 | B3；維護者「顯示美元」 | 功能 | `cost={"usd": 2.5, "basis": "run old-1", "as_of": "2026-10-24", …}` | 呼叫 `gcb_launch_screen`／`launch_screen` 帶 cost | 第 3 行與 TC-019 的格式逐字相同，金額印成 `US$2.50`（兩位小數）、basis 與日期代入 | 自動：`test_cloud_wire.py`（`test_a_known_cost_prints_two_decimals_the_basis_and_the_date`） |
| TC-022 | B3 | 功能 | `cost["usd"]` 為 `0.0`；另有 `as_of` 缺值的一組 | 同上 | `0.0` 印成 `US$0.00`（不當成「沒有」）；`as_of` 缺時日期處寫「不明」 | 自動：`test_cloud_wire.py`（B3） |
| TC-023 | W7；維護者「預估不明則允許，畫面寫無法預估」 | 功能 | 有上限、有餘額；這個管線沒有任何成功的雲端歷史 | 呼叫 `actions.request_launch` | 不被拒絕，回 `pending`；`summary` 第 3 行含「無法預估」與「還沒有成功跑過」，不含 `US$` | 自動：`test_cloud_wire.py`（`test_an_estimate_that_cannot_be_worked_out_is_allowed_and_says_so`） |
| TC-024 | W7；作法 3 理由修正 | 功能 | 有上限、有餘額；有一個成功的同管線雲端 run，但價目表是出貨的空表 | 呼叫 `actions.request_launch` | `pending`；第 3 行含「無法預估」與「尚未填入價目」，**不含**「還沒有成功跑過」（那句對這位使用者是錯的），不含 `US$` | 自動：`test_cloud_wire.py`（W7） |
| TC-025 | B4 | 功能 | `cost={"usd": None, "unknown_reasons": ["a", "b"], …}` | 呼叫畫面函式 | 第 3 行含「無法預估（a）」，不含 `b`（只取第一個原因） | 自動：`test_cloud_wire.py`（`test_an_unknown_cost_prints_the_first_reason`） |
| TC-026 | B4 | 例外 | `cost` 的 `usd` 為 `None`、`unknown_reasons` 是空清單 | 呼叫畫面函式 | 第 3 行含「原因不明 (reason unknown)」，仍是單一一行 | 自動：`test_cloud_wire.py`（B4） |
| TC-027 | B5；裁決三 3；專長守則 | 例外 | 原因含換行、`\x1b[31m`、共 300 字 | 呼叫畫面函式 | 畫面行數與沒有這個原因時相同（單一行）；控制字元被寫成看得見的跳脫（不會真的換行或變色）；「原因」這一段不超過 200 字 | 自動：`test_cloud_wire.py`（`test_a_long_or_hostile_reason_is_escaped_and_cut`） |
| TC-028 | 裁決三 3 | 例外 | 同 TC-027 的 300 字原因 | 看第 3 行的結尾 | 句尾聲明「平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。」完整保留，沒有被一起截掉 | 自動：`test_cloud_wire.py`（B5，須斷言結尾） |
| TC-029 | B6；維護者「不換算」之外的安全：畫面不被竄改 | 例外 | `basis` 含換行與跳脫碼 | 呼叫畫面函式 | 畫面行數不變，跳脫被寫成看得見的文字 | 自動：`test_cloud_wire.py`（`test_a_hostile_basis_cannot_break_the_screen`） |
| TC-030 | 作法 4 三種一行 | 功能 | 三種情況：算得出、算不出、沒傳 cost | 看三行的結尾 | 三種都以同一句聲明收尾：「平台只擋下超過每月上限的新送出，不會自動停止已經在跑的工作；實際金額請看 Google 的帳單。」 | 自動：`test_cloud_wire.py`（B2、B3、B4 的斷言） |
| TC-031 | 完成標準·手動 3 | 功能 | 維護者的 GCP 帳號；有餘額的帳號（價目表仍空） | 對 `gcb1` 送出，看確認畫面，**不要按「送出」** | 第二行是「費用預估：無法預估（…）」並帶原因；不花錢 | 手動：`docs/TESTING.md`「Cloud cost wiring」第 3 步 |
| TC-032 | 完成標準·手動 5（延後） | 功能 | 等 `cloud-rates-fill` 完成、價目表有真資料；有歷史的管線 | 第二次對同管線送出，看確認畫面 | 第二行有 `US$` 金額與 basis | 手動：`docs/TESTING.md`「Cloud cost wiring」第 5 步（今天做不了，列延後，不擋合併） |
| TC-033 | 「不做」：不在畫面顯示本月已用／剩多少 | 不在範圍 | 上限內、有預估的送出（TC-019 情境） | 看 `summary` 全文 | 不含「本月已用」「已用」「剩」這些字（只有拒絕訊息帶這三個數字；畫面要顯示是 012d 的費用頁） | 自動：`test_cloud_wire.py`（在 W6 加這條斷言） |

## User Story 3 — 不受影響的入口與既有的確認（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | W9；作法 2「Slurm 一個位元都不變」 | 功能 | Slurm 環境（`lab-a`）；`_cost.cap_problem`、`_cost.launch_estimate`、`_cost.load_rates`、`store.cloud_cap` 都設成「一被呼叫就丟錯」 | 有帳號的使用者呼叫 `actions.request_launch` | 沒丟錯，回 `pending`；`summary` 與 `build.launch_screen(b, "lab-a")` 的結果逐字相同 | 自動：`test_cloud_wire.py`（`test_a_slurm_launch_never_reads_the_cap_the_rates_or_the_index`） |
| TC-035 | B7；作法 4；校準：壓縮後別人也不能偷變 | 功能 | 既有的 Slurm 畫面雜湊測試 | 跑 `test_gcb_launch.py` 該測試 | 仍綠且該測試沒被改動（雜湊不變） | 自動：`platform/tests/test_gcb_launch.py`（:1103 一帶，既有） |
| TC-036 | B7 | 功能 | Slurm 環境 | `build.launch_screen(b, "lab-a", {"usd": 1.0})` 與不傳第三參數各呼叫一次 | 兩者逐行相同（Slurm 分支完全不看 cost） | 自動：`test_cloud_wire.py`（B7 新增部分） |
| TC-037 | W11；裁決 5 | 功能 | 沒有帳號的呼叫者（`caller=None`，本機 stdio，`person` 能問）；Google Batch；資料庫裡沒有任何 `cloud_caps` 列 | 呼叫 `actions.request_launch` | 不被上限拒絕；`summary` 第 3 行是「沒傳 cost」的預設那一行（TC-016 的句子）；`cap_problem` 沒被呼叫 | 自動：`test_cloud_wire.py`（`test_a_local_caller_without_an_account_is_not_checked_against_a_cap`） |
| TC-038 | W13；裁決三 1 | 功能 | 第一次呼叫 `pending` → 本人按送出（`confirm.approve`）→ 把上限改成 0 | 同參數第二次呼叫 | 回的是取回工作編號（`_queued`），不重新檢查、不說「未送出」；`jobs` 恰好一個 `launch_nextflow` | 自動：`test_cloud_wire.py`（`test_the_yes_that_already_exists_is_not_checked_again`） |
| TC-039 | 完成標準·手動 4 | 功能 | nano4（Slurm）環境 | 送出，看確認畫面 | 畫面與接線前完全相同 | 手動：`docs/TESTING.md`「Cloud cost wiring」第 4 步 |
| TC-040 | 「不做」：不給 `abf-launch` 終端機入口接上限；裁決 5 | 不在範圍 | 看 diff | `git diff --name-only origin/v3...HEAD` | 沒有 `platform/abf_launch/cli.py`；終端機入口仍是二參數呼叫、不查上限（見 TC-016 的預設那一行） | 手動：`docs/TESTING.md`「Cloud cost wiring」的 The reviewer 段 |

## User Story 4 — 預估的算法與「為什麼算不出來」的原因（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | C1；作法 3 | 功能 | 用環境變數指定測試索引；有可估價的歷史 | 比對 `launch_estimate(plat, {"pipeline": p}, uid)` 與 `estimate_launch(索引, plat, uid, p, load_rates())` | 兩者結果相等（`usd`、`currency`、`unknown_reasons`、`as_of`、`basis` 都同） | 自動：`test_cloud_wire.py`（`test_launch_estimate_is_estimate_launch_with_the_defaults`） |
| TC-042 | C1 | 例外 | 內容包缺 `pipeline`，或內容包不是字典 | 呼叫 `launch_estimate` | 不丟錯，回「還沒有成功跑過」那個未知（`NO_HISTORY`） | 自動：`test_cloud_wire.py`（C1） |
| TC-043 | C2；裁決 7 | 功能 | 有一個成功、同管線、Google Batch 的 run，但價目表是出貨的空表 | 呼叫 `estimate_launch` | `usd` 為 `None`、`basis` 為 `None`、`unknown_reasons` 含「尚未填入價目」，**不含**「還沒有成功跑過」 | 自動：`test_cloud_wire.py`（`test_estimate_says_why_when_a_run_exists_but_cannot_be_priced`） |
| TC-044 | C3 | 功能 | 四種各自的情境：只有 Slurm 的 run／別人的 run／失敗的 run／別的管線的 run | 呼叫 `estimate_launch` | 每種都回「還沒有成功跑過」（`NO_HISTORY`），與 `test_cloud_cost.py:290` 同結論 | 自動：`test_cloud_wire.py`（`test_estimate_still_says_no_history_when_there_is_no_candidate`）、`test_cloud_cost.py`（既有，仍綠） |
| TC-045 | C3；專長守則：擁有者規則 | 例外 | 使用者 B 沒有歷史；使用者 A 有可估價的成功 run | 以 B 的身分算預估 | B 的預估是未知（不會借用 A 的 run、也不會看到 A 的資訊） | 自動：`test_cloud_wire.py`（C3「別人的 run」那一組） |
| TC-046 | C4 | 功能 | 較舊的 run 可估價、較新的 run 算不出來（同 `test_cloud_cost.py:282` 情境） | 呼叫 `launch_estimate` | 回舊的那個的金額與 basis（修正沒改壞既有行為：有可估價的 run 時輸出不變） | 自動：`test_cloud_wire.py`（`test_a_priceable_older_run_still_beats_an_unpriceable_newer_one`）、`test_cloud_cost.py`（`test_estimate_skips_a_newer_run_it_cannot_price`，既有） |
| TC-047 | 「不做」：不用 `resourceLimits`／`maxvCpus` 估價 | 不在範圍 | 環境設定只有 `maxvCpus`／`resourceLimits`、沒有歷史 | 呼叫 `launch_estimate` | `usd` 為 `None`，沒有任何用資源上限猜出的數字 | 自動：`test_cloud_cost.py`（`test_no_history_means_unknown_estimate_not_a_guess`，既有，仍綠）＋`test_cloud_wire.py`（C1） |
| TC-048 | 「不做」：不改 `cap_problem` 的判斷式與拒絕文字 | 不在範圍 | 看 diff 與既有測試 | `git diff origin/v3...HEAD -- platform/abf_platform/cloud_cost.py`；跑 `test_cloud_cost.py` 全檔 | `cap_problem`、`NO_CAP`、`_money` 沒有任何改動；`test_cloud_cost.py` 全檔仍綠 | 手動：`docs/TESTING.md`「Cloud cost wiring」的 The reviewer 段（diff）＋自動：`test_cloud_cost.py` |
| TC-049 | 「不做」：不填價目表、不改 `cloud_rates.json` | 不在範圍 | 看 diff | `git diff --name-only origin/v3...HEAD` | 沒有 `platform/abf_platform/data/cloud_rates.json`；它的 `regions` 仍是 `{}` | 自動：`test_cloud_cost.py`（出貨價目為空的既有斷言）；手動：The reviewer 段（diff） |

## User Story 5 — 舊假話移除、文件、改動範圍（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | B8；目標 2；維護者「那句換掉」 | 功能 | `platform/`、`docs/`、`README.md` 的文字檔 | 搜尋「還沒有費用預估與上限」與「接線之前確認畫面仍寫」 | 一個檔都沒有（`specs/` 底下已歸檔的舊計畫不掃；`platform/tests/test_cloud_wire.py` 本身以路徑排除，不准拆字串規避） | 自動：`test_cloud_wire.py`（`test_no_file_still_says_there_is_no_estimate_and_cap`） |
| TC-051 | 「必須更新的既有斷言」1 | 功能 | `test_gcb_launch.py` 的 diff | 比對 base 與 HEAD | 該函式只改 `sentence` 與 `lines[1] == sentence` 的比對；:730 的無數字正規式、欄位標籤、區塊標題斷言原樣；整個檔案沒有別的斷言被刪、放寬或跳過 | 手動：The reviewer 段（diff 比對） |
| TC-052 | 作法 7·CLOUD.md；目標 | 功能 | `docs/CLOUD.md` | 讀「目前的限制」第二條 | 寫成：從網頁或 AI 送出到 Google Batch 時，平台在建立任何東西之前先查上限；確認畫面第二行寫預估或「無法預估」；舊的「還沒有接到送出畫面」「接線之前確認畫面仍寫…」已改成已接線 | 手動：閱卷者讀檔（The reviewer 段） |
| TC-053 | 作法 7·CLOUD.md；裁決 5、裁決二 1 | 功能 | `docs/CLOUD.md` | 讀同一條 | 白話寫明例外：平台主機上管理者自己打的 `abf-launch` 終端機指令、沒有帳號的本機 stdio，**不查上限**；並寫明這是個缺口（持有終端機的人可用 `--user` 替任何帳號送出而繞過該帳號的上限） | 手動：閱卷者讀檔 |
| TC-054 | 作法 7·CLOUD.md「確認畫面長什麼樣」 | 功能 | `docs/CLOUD.md` | 找這一段 | 有這一段，且寫出作法 4 的三種一行（算得出／算不出／沒傳 cost） | 手動：閱卷者讀檔 |
| TC-055 | 完成標準；裁決三 1 | 功能 | `docs/CLOUD.md` | 讀全文 | 白話寫明：目前不會自動停止正在跑的雲端工作；價目表目前是空的，所以預估都是「無法預估」，上限只擋得住「沒設上限／上限 0／本月已用滿」；本人按送出之前、確認有效期（約 600 秒）內上限被調低不會重查（已知限制） | 手動：閱卷者讀檔 |
| TC-056 | 作法 7·CLOUD.md；K4 | 功能 | `docs/CLOUD.md` | 跑 `test_cloud_cost.py` 的 `test_the_cloud_document_says_what_it_must` | 要求的詞（`只含運算`、`同一個 pipeline`、`最近一次成功`、`--cloud-cap-usd`、`不會自動停止正在跑的雲端工作`、`只會擋下新的送出`、`帳單預算`、`太平洋時間`、`第一次`、`擋不住` 等）一個都不少；不出現 `NT$` | 自動：`platform/tests/test_cloud_cost.py`（既有） |
| TC-057 | 作法 7·PLATFORM.md | 功能 | `docs/PLATFORM.md` 的「Money」段 | 讀這一段 | 保留中文「費用：按下 y 之後…」句；改寫為：網頁與 AI 送出到 Google Batch 時先查每人每月上限，確認畫面第二行寫預估（或「無法預估」與原因）；第一段仍不含數字；實際金額看 Google 帳單；不會自動停止已在跑的工作；舊的「launch screen does not use it yet」已不在 | 手動：閱卷者讀檔 |
| TC-058 | 作法 7·TESTING.md；完成標準手動 | 功能 | `docs/TESTING.md` | 讀「Cloud cost (cloud-cost)」第 4 步與新小節 | 第 4 步括號（「The call is not yet in the launch screen」）已改寫；有「Cloud cost wiring」小節，列出手動第 1–5 步（TC-013、014、031、039、032 的步驟）與給閱卷者的 The reviewer 段，每步具體到能照做 | 手動：閱卷者讀檔 |
| TC-059 | 完成標準·PR 說明 | 功能 | 合併前的 PR 說明 | 讀 PR 說明 | 寫明：①今天價目表為空，預估一律「無法預估」，上限只擋得住「沒設上限／上限 0／本月已用滿」；②終端機入口與無帳號 stdio 不受管；③「必須更新的既有斷言」逐條（以前／以後／理由）；④不自動停 | 手動：developer-agent 合併前核對（閱卷者看不到 PR 文字時此條記為待確認） |
| TC-060 | 範圍：檔案；完成標準；K6 | 不在範圍 | HEAD 對 `origin/v3` 的 diff | `git diff --name-only origin/v3...HEAD` | 只出現範圍表的 9 個檔，加上 `specs/cloud-cost-wire/` 底下的計畫、測試案例與帳本；**沒有**任何「禁碰」檔（`platform/abf_station/*`、`hooks/*`、`tests/run_all.sh`、`.github/*`、`cloud_store.py`、`actions/datasets.py`、`platform/pyproject.toml`、`platform/setup.py`）與「另外不碰」檔（`store.py`、`receiver.py`、`cli.py`、`abf_launch/cli.py`、`web.py`、`mcp_server.py`、`jobs.py`、`confirm.py`、`su.py`） | 手動：The reviewer 段（K6，executor 貼證據進 ledger，閱卷者重跑） |
| TC-061 | 範圍：函式；K6；作法 1、4 | 不在範圍 | `actions/__init__.py` 與 `build.py` 的 diff | 逐段看 diff | `actions/__init__.py` 只動第 27 行 import（帶底線別名）、`_finish_launch`、新增 `_cloud_check`；`build.py` 只動 `GCB_COST`、`cost_line`、`gcb_launch_screen`、`launch_screen`；`request_resume`、`_request_attempt`、`prepare_resume`、`resume_screen`、`read_edit_args`、`relaunch_screen`、`_attempt_lines` 一個字都沒動 | 手動：The reviewer 段（K6） |
| TC-062 | 作法 1；「不做」：不新增公開動作名稱 | 不在範圍 | 既有測試 | 跑 `test_pipeline_launch.py:486–495` 與 `test_cloud_cost.py:602` | `request_launch`、`request_pipeline_launch`、`_finish_launch` 的參數列不變，兩入口仍都呼叫 `_finish_launch`；`dir(actions)` 沒有任何名稱含 `cloud` 的公開名；`test_web_parity.py` 的 `INTERNAL`／`OWED` 清單沒改 | 自動：`test_pipeline_launch.py`、`test_cloud_cost.py`、`test_web_parity.py`（既有，仍綠且未改） |
| TC-063 | 裁決三 4；專長守則：資料變動要附 migration 或寫明不需要 | 不在範圍 | 看 diff | `git diff origin/v3...HEAD -- platform/abf_platform/store.py platform/abf_platform/receiver.py` | 兩檔都沒有改，沒有任何資料表或欄位變動；計畫已明寫「不需要 migration」的理由 | 手動：The reviewer 段（diff） |
| TC-064 | 「不做」：不新增 `index_path` 參數；不改 `get_run`／MCP 工具／網頁路由 | 不在範圍 | 看 diff | 讀 `_cloud_check` 的簽名與 `mcp_server.py`、`web.py` 的 diff | `_cloud_check(platform_path, ce, bundle, caller)` 只有這四個參數；索引路徑用預設；`mcp_server.py`、`web.py` 沒改 | 手動：The reviewer 段（diff） |

## 憲法與安全網

涉及的條目：第 1 條（新 `.py` 前 40 行有 `# Nothing existing:`）；第 2 條（平台不啟動程式、沒有監看常駐程式、送出只經本人確認的管道）；第 9 條（數字來自檔案，缺口要明寫）；第 13 條（失靈不能靜默）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-065 | 第 1 條；K1（TC-070） | 功能 | 新檔 `platform/tests/test_cloud_wire.py` | 看前 40 行 | 有 `# Nothing existing: <至少 15 字的理由>` | 自動：`platform/tests/test_scope.py`（TC-070，既有） |
| TC-066 | 第 2 條；K1（TC-071） | 功能 | 新增的 `_cloud_check`、`launch_estimate`、`cost_line` 與新測試檔 | 掃平台原始碼 | 不含 `subprocess`、`Popen`、`threading`、`while True`、`nohup`、`setsid`、`ssh`、`socket`、`urllib.request`（平台不啟動任何程式、不連網） | 自動：`test_scope.py`（TC-071，既有） |
| TC-067 | 第 2 條；K1（TC-061） | 功能 | 同上 | 掃平台原始碼（含註解與字串） | 沒有 `station` 這個字（不准拆字串規避） | 自動：`test_scope.py`（TC-061，既有） |
| TC-068 | 第 2 條；維護者 10-24「超上限只擋新送出、不自動停」；K3 | 不在範圍 | 看原始碼 | 跑 `test_cloud_cost.py::test_nothing_stops_a_running_job_and_no_policy_channel_exists`；檢查 `inspect.getsource(actions._cloud_check)` 與 `build.cost_line` | `abf_platform/` 沒有 `watchdog`、`POLICY`；`cloud_cost.py` 沒有 `enqueue_cancel`、`cancel_run`；`jobs` 的 `kind` 仍是原來六種；`_cloud_check` 與 `cost_line` 的原始碼不含 `cancel` | 自動：`test_cloud_cost.py`（既有）＋`test_cloud_wire.py`（新斷言） |
| TC-069 | 第 2 條（確認管道）；專長守則：確認管道 TC | 功能 | 既有的人工確認測試 | 跑 `test_human_channel.py`（含 :182 的比對）與 `test_keep_submissions.py`（:1130） | 仍綠且未被改動：沒有本人答應就不會有工作；終端機送出的 `screen_text` 比對不變；被上限拒絕時沒有留下確認或工作（見 TC-002） | 自動：`test_human_channel.py`、`test_keep_submissions.py`（既有） |
| TC-070 | 第 9 條、第 13 條 | 功能 | 三種畫面狀態：算得出、算不出、沒傳 cost | 數畫面行數、看第 3 行 | 每一種都剛好多出一行說明（不是沉默）；算不出時寫原因，不出現任何猜出來的數字 | 自動：`test_cloud_wire.py`（B2、B3、B4、W7） |
| TC-071 | K2；「上限只有管理者知道」 | 功能 | `test_cloud_cost.py:602`、:604–:628 | 跑該檔 | `actions` 沒有含 `cloud` 的公開名；`cloud_caps`／`cap_usd`／`cloud-cap` 只出現在 `store.py`、`cloud_cost.py`、`cli.py`（`actions/__init__.py` 內沒有這幾個字串） | 自動：`test_cloud_cost.py`（既有） |
| TC-072 | K4；維護者「不換算」 | 功能 | `cloud_cost.py` 與出貨價目表 | 跑 `test_no_other_currency_in_the_source_or_the_rates` | 不含 `NT$`、`TWD`、`新台幣`、`匯率`、`exchange rate`；本任務對 `cloud_cost.py` 的新增碼也不含 | 自動：`test_cloud_cost.py`（既有） |
| TC-073 | K5；專長守則：對等性 | 功能 | 既有的工具數與路由測試 | 跑 `test_gcb_launch.py:1063–1069` 與 `test_web_parity.py` | 工具數量仍是 13；沒有新網頁路由；網頁動作清單與動作層函式清單仍一一對應（`test_web_parity.py` 未改） | 自動：`test_gcb_launch.py`、`test_web_parity.py`（既有）；全套 `tests/platform_test.sh` 綠 |
| TC-074 | 完成標準；「不會、也不准變紅」 | 功能 | 全套測試 | 跑 `tests/platform_test.sh` 與下列既有守門：`test_gcb_ce.py`、`tests/no_per_pipeline_config.sh`、`tests/credentials_stay_in_settings_test.sh`、`test_scope.py`、`test_cloud_cost.py` 全檔 | 全綠；除 `test_gcb_launch.py` 那一處與新檔 `test_cloud_wire.py` 外，沒有任何既有測試檔被修改（沒有斷言被刪、放寬或跳過） | 自動：全套；手動：The reviewer 段（diff 比對） |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
