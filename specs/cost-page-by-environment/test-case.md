# 測試案例：費用頁以運算環境為單位＋分析頁費用列

**規格**：`specs/cost-page-by-environment/plan.md`（本任務沒有 spec.md，「對應需求」欄引用 plan.md 的段落：作法 N、env01–env14、裁決、待決、不做、專長守則）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、顯示 `—`）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「環境」＝使用者自己建立的運算環境（例如一個 Slurm 站台、一個 Google Cloud Batch）。「SU」是 Slurm 站台的計算點數，「US$」是美元。「hand-off 紀錄」＝這個分析送出時記下它跑在哪個環境的那一筆紀錄。`—` 表示「算不出來」，絕不等於 0。

測試種子（多數 TC 共用，沿用 `test_web_cost.py` 的 `w` fixture 與 `seed`）：使用者 ann 有四個分析：Slurm 環境一個（已完成）、Google Batch 環境一個（已完成）、AWS Batch 環境一個（已完成）、再加一個執行中；使用者 bob 另有自己的分析。

## User Story 1 — 費用頁：一個環境一列，可展開（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標「只有一個環境時就是一列」；env01；作法 6 | 功能 | ann 只有一個 Slurm 環境，底下有 2 個已完成分析 | 開 `/usage` | 中間窗格只有一個 `details.env`，且帶 `open`（直接展開） | 自動：`test_cost_by_env.py`（env01） |
| TC-002 | env01；作法 3 | 功能 | 同 TC-001，兩個分析各有已知 SU | 開 `/usage` | 該列的 SU 數字等於兩個分析 SU 之和 | 自動：`test_cost_by_env.py`（env01） |
| TC-003 | 目標「一個運算環境一列」；env02；作法 6 | 功能 | ann 有 Slurm、Google、AWS 各一個分析（共三個環境） | 開 `/usage` | 中間窗格有三個 `details.env`，一個環境一個 | 自動：`test_cost_by_env.py`（env02） |
| TC-004 | 目標「不跨環境加總」；env02 | 功能 | 同 TC-003 | 開 `/usage`，搜尋頁面文字 | 沒有任何一段「總計」文字同時含 `SU` 與 `US$`；頁面上沒有跨環境的合計數字 | 自動：`test_cost_by_env.py`（env02） |
| TC-005 | 作法 6「`<summary>` 一行」 | 功能 | 同 TC-003，Slurm 環境有 3 個分析 | 看 Slurm 那一列的 `<summary>` | 同一行依序有：環境名（不是連結）、環境類型小字（如 Slurm）、用量、「共 3 個分析」（en：對應英文） | 自動：`test_cost_by_env.py` |
| TC-006 | 作法 6「展開後是 table.tbl」 | 功能 | 同 TC-003 | 看任一環境展開後的內容 | 是 `table.tbl`，欄頭依序為 分析名稱／開始時間／用量／狀態（en 為對應英文） | 自動：`test_cost_by_env.py` |
| TC-007 | 作法 4「排序」 | 功能 | ann 的三個環境，最新分析的開始時間各不同 | 開 `/usage` | 環境列依「該環境最新一個分析的開始時間」新到舊排列 | 自動：`test_cost_by_env.py` |
| TC-008 | 作法 4「排序」 | 功能 | 同一環境內有 3 個開始時間不同的分析 | 展開該環境 | 分析列由新到舊 | 自動：`test_cost_by_env.py` |
| TC-009 | 作法 6「零 JS、原生展開」；專長守則（前端限制） | 功能 | 同 TC-003 | 看 `/usage` 的 HTML | 展開靠 `<details>`／`<summary>` 原生元素；環境列沒有任何 `<script`、沒有 `on*=` 事件屬性 | 自動：`test_cost_by_env.py`（env08） |
| TC-010 | 作法 6「環境名照原樣顯示並跳脫」 | 例外 | ann 有一個環境，名稱含 `<b>x</b>` | 開 `/usage` | 頁面上看到的是文字 `<b>x</b>`（已跳脫），HTML 裡沒有真的 `<b>` 標籤 | 自動：`test_cost_by_env.py` |
| TC-011 | 作法 6「標題列、上一月／下一月導覽保留」 | 功能 | ann 有 2026-10 的分析 | 開 `/usage?month=2026-10`，再點上一月 | 標題列與月份導覽仍在，導覽指到 2026-09 與 2026-11 | 自動：`test_web_cost.py`（既有，更新後仍綠） |
| TC-012 | 作法 6「`bad_month` 提示保留」 | 例外 | 任意使用者 | 開 `/usage?month=不是月份` | 顯示既有的 bad_month 提示，回 200，不當機 | 自動：`test_web_cost.py` |
| TC-013 | 作法 6「`empty` 句保留」；env13 新形狀 | 功能 | ann 在 2026-01 沒有任何分析 | 開 `/usage?month=2026-01` 與 `?lang=en` | 顯示既有的「這個月沒有分析」那句（zh／en 各一），沒有環境列，不出現 `0`、`NaN`，回 200 | 自動：`test_web_cost.py` |
| TC-014 | 維護者原話：「國網／雲端二分法很奇怪」；plan.md 目標 | 功能 | ann 有 Slurm、Google、AWS 各一個分析 | 開 `/usage`（zh 與 en） | 頁面的頂層分類是「一個環境一列」；沒有「國網」「雲端」當分類標籤的標題或分區；三個環境各一列、各用各的單位 | 自動：`test_cost_by_env.py`（env02、env08） |

## User Story 2 — 單位跟著環境，計價不誤歸（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 作法 3 表格第 1 列；作法 6 | 功能 | Slurm 環境（`slurm-platform`），分析已完成且有 cpus／realtime／queue | 開 `/usage` | 該列與分析列的用量用 `su_text` 的字樣（SU 單位），分析值由該 run 自己環境的 `suSite` 計價 | 自動：`test_cost_by_env.py`、`test_web_cost.py` |
| TC-016 | 裁決（11-06 追進度）：以定案草稿為準，SU 旁顯示概略美元（草稿例「1,240 SU ≈ US$ 3.9」，維護者「好的可以」） | 功能 | Slurm 環境，匯率檔有日期；已知 SU 用量 | 開 `/usage` | SU 旁出現依匯率算的概略美元數字；頁面帶 `usd_note`（說明是依費率檔概估、不是帳單），原樣保留 | 自動：`test_web_cost.py`、`test_su_usd.py` |
| TC-017 | 作法 3「匯率日期缺就 None」 | 例外 | Slurm 環境，匯率檔沒有日期 | 開 `/usage` 與 `my_usage` | `usd_approx` 為 None，頁面不顯示概略美元也不顯示 `US$ 0.00`；SU 數字照常顯示，不報錯 | 自動：`test_cost_by_env.py` |
| TC-018 | 作法 3 表格第 2 列；作法 6 | 功能 | Google Batch 環境（`googlebatch-platform`），費率檔有該區域費率，分析已完成 | 開 `/usage` | 該列與分析列的用量顯示 `US$ %.2f` 格式（例 `US$ 1.20`），單位是美元 | 自動：`test_cost_by_env.py` |
| TC-019 | env06「未知不當 0」 | 例外 | Google Batch 環境，`cloud_rates.json` 的 `rates` 是空清單 | 開 `/usage` 與 `my_usage` | 該環境 `total is None`；頁面該列顯示 `—` 與原因說明，不顯示 `US$ 0.00` | 自動：`test_cost_by_env.py`（env06） |
| TC-020 | env03；作法 3 表格第 3 列 | 例外 | AWS Batch 環境（hand-off 列指向 `awsbatch-platform`），分析已完成 | 開 `/usage` 與 `my_usage` | 該環境 `unit=="USD"`、`total is None`、原因含「尚無此環境的費用估算」；頁面顯示 `—`＋該原因，絕不是 `US$ 0.00` | 自動：`test_cost_by_env.py`（env03） |
| TC-021 | 作法 3 表格第 3 列 | 例外 | Azure Batch 環境與 K8s 環境各一個分析 | `my_usage` 與開 `/usage` | 兩環境都是 `unit=="USD"`、用量 None、原因含「尚無此環境的費用估算」；原因為雙語「中文 (English)」格式 | 自動：`test_cost_by_env.py` |
| TC-022 | 作法 3 表格第 4 列、作法 4；裁決第 3 點（本機非平台 run） | 例外 | ann 有一個分析沒有 hand-off 紀錄（本機非平台 run），另有一個 Slurm 分析 | 開 `/usage` 與 `my_usage` | 沒有 hand-off 的分析落在 `unit is None` 的環境列，`name` 為 None（頁面顯示 `—`），用量 None＋原因；它不進任何 SU 或 USD 總數，也不被算成 0 | 自動：`test_cost_by_env.py` |
| TC-023 | env03「環境紀錄被刪掉的 run」；作法 1 洞 2 | 例外 | ann 的一個分析 hand-off 指向的環境紀錄已被刪除；另有一個 Slurm 分析 | `my_usage` 與開 `/usage` | 那個分析落在 `unit is None` 的環境，原因含「環境紀錄已不存在 (the environment is no longer on record)」；Slurm 環境 `total` 只含 Slurm 分析 | 自動：`test_cost_by_env.py`（env03） |
| TC-024 | 作法 3 表格第 4 列「其他 KINDS」 | 例外 | hand-off 指向一個不屬於 Slurm／Google／AWS／Azure／K8s 的環境類型 | `my_usage` | `unit is None`、用量 None、原因沿用 `_NOT_SENT_HERE`，不算 0 | 自動：`test_cost_by_env.py` |
| TC-025 | 作法 6「`unit is None` 的環境小字寫原因」 | 功能 | 同 TC-023 | 開 `/usage` | 該環境的 summary 小字寫出原因（zh／en 各自語言），不是空白 | 自動：`test_cost_by_env.py` |
| TC-026 | env03 誤計回歸；作法 1 洞 1（本任務查證） | 功能 | 一個 Slurm 分析（SU 100）與一個 AWS Batch 分析，AWS 分析的 task 有 cpus／realtime／queue | `my_usage` 與開 `/usage` | Slurm 環境 `total` 恰為 100（只含 Slurm 分析）；AWS 分析不進任何 SU 總數；整個回傳沒有 `su` 鍵 | 自動：`test_cost_by_env.py`（env03） |
| TC-027 | env04；作法 1 洞 3 | 功能 | 兩個 Slurm 環境，`suSite` 不同，且都不是 `default_site`，各有一個分析 | `my_usage` 與開 `/usage` | 兩個環境各用自己的站點計價；每環境 `total` 等於其分析列之和；不用 `default_site` | 自動：`test_cost_by_env.py`（env04） |
| TC-028 | 作法 4「`my_usage` 新形狀」 | 功能 | 同「測試種子」 | 呼叫 `my_usage` | 頂層鍵恰為 `month`、`environments`、`cloud`（無 `su`、`runs`）；每個環境有 `name, kind, unit, site, total, usd_approx, unknown_runs, unknown_reasons, analyses_count, analyses`；`site`、`usd_approx` 只有 SU 環境有值；`kind` 是顯示名（如 Slurm）；每個分析有 `name, started_at, state, value, usd_approx, unknown_reasons` | 自動：`test_web_cost.py`（test_co11 改新形狀） |
| TC-029 | 作法 2 | 功能 | 一個 Google Batch 分析、一個 AWS 分析 | 呼叫 `_launch_facts(platform_path, run_name)` | 回傳含 `cloud, location, pipeline, ce, platform` 五鍵；`cloud` 仍只對 Google Batch 為真（AWS 為假）；簽章不變 | 自動：`test_cost_by_env.py` |
| TC-030 | 作法 2「替身沒有新鍵時用 `.get`」 | 例外 | 測試把 `_launch_facts` 換成只回舊三鍵的替身（沿用 test_web_cost.py 的 monkeypatch） | 開 `/usage` | 不當機、回 200；該分析被視為未知環境（`unit is None`），不進 SU 總數 | 自動：`test_web_cost.py` |

## User Story 3 — 未知不當 0、執行中、筆數與上限（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | env06；作法 3 末段 | 功能 | ann 有一個執行中的分析 | `my_usage` 與開 `/usage` | 該分析 `state=="running"`、用量 None、原因為 `su.RUN_NOT_ENDED`；不進環境 `total`；該環境 `unknown_runs` 加一；頁面狀態欄有「執行中」 | 自動：`test_cost_by_env.py`（env06） |
| TC-032 | 作法 4「沿用雲端卡做法」；待決 5 | 功能 | 同一 Slurm 環境：兩個已完成分析（SU 各 50）＋一個執行中 | `my_usage` 與開 `/usage` | 環境 `total` 為 100（已知加總），`unknown_runs==1`，頁面小字有「另有 1 個分析無法計算」類字句；不是整列變 `—` | 自動：`test_cost_by_env.py` |
| TC-033 | 作法 4「沒有任何已知用量時 total=None」 | 例外 | 一個環境只有一個執行中分析 | `my_usage` 與開 `/usage` | `total is None`，該列用量顯示 `—`，不顯示 0 | 自動：`test_cost_by_env.py` |
| TC-034 | 作法 6「沿用 `unknown_runs`／`unknown_run` 字串」 | 功能 | 環境 A 有 1 個算不出的分析，環境 B 有 2 個 | 開 `/usage` 與 `?lang=en` | A 用單數字串、B 用複數字串（en 的單複數正確，如 1 run／2 runs 類寫法依既有字串） | 自動：`test_web_cost.py`（ruling13 更新後） |
| TC-035 | 目標「未知一律 None＋原因，絕不是 0」 | 例外 | 種子含 AWS 分析、執行中分析、Google 費率空的分析 | 開 `/usage` 並搜尋 | 這三類分析的用量欄都是 `—`；頁面上不出現把它們顯示成 `0`、`0 SU`、`US$ 0.00` | 自動：`test_cost_by_env.py` |
| TC-036 | 專長守則「狀態＝符號＋文字＋顏色」；作法 6 | 功能 | 一個執行中、一個已估算完成的分析 | 看 `/usage` 的 HTML | 執行中列同時有 `state-running` 樣式、符號、詞「執行中」；完成列有 `state_estimate` 的詞與符號；不是只有 class | 自動：`test_web_cost.py`（co06 更新後） |
| TC-037 | env05；作法 4「最多列 50」 | 功能 | 一個環境有 60 個分析 | `my_usage` 與開 `/usage` | `analyses` 只有 50 個（新到舊）、`analyses_count==60`；頁面「共 60 個分析」 | 自動：`test_cost_by_env.py`（env05） |
| TC-038 | env05；作法 4「total 對全部分析計算」 | 功能 | 同 TC-037，每個分析 SU 都是 10，最舊的 10 個不在列出的 50 之內 | `my_usage` | 環境 `total` 為 600，不是 500 | 自動：`test_cost_by_env.py`（env05） |
| TC-039 | env02；作法 4「刪除 su 與 runs 兩鍵」 | 功能 | 同「測試種子」 | 呼叫 `my_usage` | 回傳沒有 `su`、沒有 `runs` 鍵；不存在任何跨環境的總數欄位 | 自動：`test_cost_by_env.py`（env02） |
| TC-040 | env02「每個 unit 只有一種」 | 功能 | 同「測試種子」 | 呼叫 `my_usage` | `environments` 的每一項 `unit` 只有 `SU`、`USD`、None 之一，且同一環境內所有分析用同一單位 | 自動：`test_cost_by_env.py`（env02） |

## User Story 4 — 只看自己的、讀不到索引、純讀（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | env07；DESIGN 限制「每人只看自己的」 | 例外 | ann 有 Slurm 環境與分析；bob 另有自己的分析 | 以 bob 的身分開 `/usage` | 看不到 ann 的環境列、名稱、數字；只看到 bob 自己的 | 自動：`test_cost_by_env.py`（env07） |
| TC-042 | env07；作法 4「caller=None」 | 例外 | 沒有呼叫者身分 | 呼叫 `my_usage(caller=None)` | 回 `{"found": False, ...}`（v3 行為），不含任何費用資料 | 自動：`test_cost_by_env.py`（env07） |
| TC-043 | env13；專長守則（錯誤訊息不露內部） | 例外 | 讀索引時丟 `sqlite3.Error` | 開 `/usage` | 回 200，是空頁（`environments: []`、`cloud` 段仍在），頁面沒有堆疊、內部路徑、SQL | 自動：`test_cost_by_env.py`（env13）、`test_web_bugs_b.py` |
| TC-044 | 作法 4「純讀，不寫任何東西」 | 功能 | 一組有資料的 index.db 與 platform.db | 呼叫 `my_usage` 與 `run_usage` 前後比對兩個資料庫 | 兩個資料庫內容與檔案修改時間都沒有變 | 自動：`test_cost_by_env.py` |

## User Story 5 — 分析頁費用列（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-045 | env09；作法 7；DESIGN 第 11 項 | 功能 | ann 一個已完成（結果階段）的分析 | 開 `/?run=<id>` 與 `&lang=en` | 有一個 `table.tbl`，一列，欄頭依序為 環境／用量／狀態／範圍（en：Environment／Usage／Status／Scope） | 自動：`test_cost_by_env.py`（env09） |
| TC-046 | env09；作法 7「範圍」；裁決第 5 點 | 功能 | 同 TC-045 | 看費用列的「範圍」欄 | 文字等於 `STRINGS` 該 key 的字串（zh「整個分析（含失敗的步驟）」，en「Whole analysis, failed steps included」，或 executor 查證後改寫並在 ledger 說明的字句）；測試用 key 取值，不在測試裡重寫字句 | 自動：`test_cost_by_env.py`（env09） |
| TC-047 | 作法 7「讀 task_usage 全部列，含失敗的 task」；裁決第 5 點 | 功能 | 一個分析有兩個 task：一個成功、一個失敗，各有可計價用量 | `run_usage`、`my_usage`、分析頁費用列 | 失敗 task 的用量有被算進該分析的值（若 executor 查到 `su.py` 或 `run_tasks_cost` 其實有依狀態過濾，則範圍字句已改寫成與實際相符，且此 TC 照改後字句比對） | 自動：`test_cost_by_env.py` |
| TC-048 | env09「執行階段也有」 | 功能 | ann 一個執行中的分析 | 開 `/?run=<id>` | 同樣有欄頭為 環境／用量／狀態／範圍 的費用列；用量 `—`，狀態「執行中」 | 自動：`test_cost_by_env.py`（env09） |
| TC-049 | 作法 7「位置」 | 功能 | 結果階段與執行階段各一個分析 | 看兩頁的 HTML 順序 | 費用列緊接在四張摘要卡之後（兩個階段都是） | 自動：`test_cost_by_env.py` |
| TC-050 | env09 | 功能 | Slurm 完成的分析 | 開分析頁 | 費用列的環境欄是該環境名，用量欄是 `su_text` 的字樣（SU），狀態是 `state_estimate` 的詞 | 自動：`test_cost_by_env.py`（env09） |
| TC-051 | env09 | 功能 | AWS Batch 的分析 | 開分析頁 | 環境欄顯示該 AWS 環境名，用量欄為 `—`，不是 0 | 自動：`test_cost_by_env.py`（env09） |
| TC-052 | 作法 7 | 功能 | Google Batch 的分析，費率有 | 開分析頁 | 用量欄為 `US$ %.2f` 格式 | 自動：`test_cost_by_env.py` |
| TC-053 | 作法 7「環境 None 顯示 `—`」 | 例外 | 沒有 hand-off 紀錄的分析 | 開分析頁 | 環境欄 `—`、用量欄 `—`，頁面正常 | 自動：`test_cost_by_env.py` |
| TC-054 | 作法 7「狀態同費用頁」 | 功能 | 一個執行中、一個已完成的分析 | 各開分析頁 | 狀態欄用 `state_running`／`state_estimate` 的詞（含符號與文字，不只靠顏色） | 自動：`test_cost_by_env.py` |
| TC-055 | 作法 7；test_su_usd 釘住 | 功能 | 結果階段的分析 | 開分析頁 | 既有的「運算」「費用」兩張摘要卡仍在，內容與改動前相同（如費用卡 `SU —`） | 自動：`test_su_usd.py`（L476–478 不改） |
| TC-056 | env09；作法 5「不是呼叫者的 run」 | 例外 | ann 的分析；以 bob 身分 | bob 開 ann 的 `/?run=<id>`；呼叫 `run_usage(caller=bob)` | 與 `get_run` 相同的 not-found，不洩漏 ann 的環境名、用量；分析頁拿不到費用列 | 自動：`test_cost_by_env.py`（env09） |
| TC-057 | env13；作法 7「`sqlite3.Error`」 | 例外 | 讀索引時丟 `sqlite3.Error` | 開 `/?run=<id>` | 回 200，費用列一列全 `—`，不 500，沒有堆疊或路徑 | 自動：`test_cost_by_env.py`（env13） |
| TC-058 | 作法 5「回傳形狀」 | 功能 | ann 的分析 | 呼叫 `actions.run_usage(index_path, run_id, caller=ann, platform_path=...)` | 回 `{"found": True, "environment", "kind", "unit", "value", "usd_approx", "state", "unknown_reasons"}` 這些鍵 | 自動：`test_cost_by_env.py` |
| TC-059 | env10；作法 5「共用 `_usage_item`」 | 功能 | 同一個分析（涵蓋 Slurm、Google、AWS、執行中各一） | 分別呼叫 `run_usage` 與 `my_usage` | 兩者對同一分析給同樣的 value／state／unknown_reasons | 自動：`test_cost_by_env.py`（env10） |
| TC-060 | 計畫「不做」：把 `run_usage` 做成 MCP 工具；作法 5 | 不在範圍 | 工具清單與網頁動作清單 | 比對 `test_web_parity.py` 的 `WEB_ONLY` 與 `READ_NAMES` | `WEB_ONLY` 有 `run_usage` 且附指定說明；`READ_NAMES` 沒有；MCP 工具表沒有 `run_usage` | 自動：`test_web_parity.py`、`test_cost_by_env.py`（env10） |
| TC-061 | 作法 5「`get_run` 的鍵集合不動」 | 功能 | ann 的分析 | 呼叫 `get_run` | 鍵集合與 v3 完全相同 | 自動：既有 `get_run` 相關測試 |
| TC-062 | 作法 5「不存在的 run」 | 例外 | 一個不存在的 run id | 呼叫 `run_usage` | 回與 `get_run` 相同的 not-found | 自動：`test_cost_by_env.py` |
| TC-063 | env11；tc060；專長守則（動作層唯一） | 功能 | 原始碼 | 重跑 `test_web_cost_module_goes_through_actions_only` 的 AST 掃描並涵蓋 `web_board.py` | `web_cost.py`、`web_board.py` 沒有 import `jobs／status／compute_envs／confirm／agents`，只經 `actions` 取資料 | 自動：`test_web_cost.py`、`test_cost_by_env.py`（env11） |
| TC-064 | 作法 7、範圍：檔案（`web.py` 只改傳遞，不加新路由） | 功能 | 原始碼與路由表 | 檢查 `web.py` 路由與 `read_run` | `read_run` 只多呼叫一次 `actions.run_usage`，結果放 `view["usage"]`；路由清單與 v3 相同（沒有新增） | 自動：`test_web_parity.py` |

## User Story 6 — 刪除舊的分法與限制（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-065 | env08；目標「刪 NT$、Reconciled」 | 功能 | 任意有資料的月份 | 開 `/usage`（zh）與 `/usage?lang=en`，取中間窗格 | 不含 `NT$`、`新台幣`、`TWD`、`Reconciled`、`已對帳` | 自動：`test_cost_by_env.py`（env08） |
| TC-066 | env08；作法 6「不得出現」 | 功能 | 同 TC-065，環境的 `suSite` 有真實站台名 | 同 TC-065 | 不含 `國網`、`雲端已用`、站台名；`雲端上限`、`雲端剩餘` 只允許出現在上限那一行；「匯率」只允許出現在 `usd_note` 那句 | 自動：`test_cost_by_env.py`（env08）、`test_web_cost.py`（test_no_other_currency） |
| TC-067 | env08；作法 6 | 功能 | 同 TC-065 | 開 `/usage?lang=en` | 英文頁面沒有 CJK 字元，且無 `NT$`、`Reconciled`、站台名 | 自動：`test_web_cost.py`（`no_cjk`）、`test_cost_by_env.py` |
| TC-068 | 作法 6「`note` 改為」 | 功能 | 任意有資料的月份 | 開 `/usage` 與 `?lang=en` | zh：「各運算環境用各自的單位（SU 或美元）顯示，不互相換算、不加總。數字依執行紀錄估算，略低於實際帳單。」；en：「Each compute environment is shown in its own unit (SU or US dollars); nothing is converted or added across environments. Figures are estimates from the run records and a little below the actual bill.」 | 自動：`test_web_cost.py`（`NOTE_ZH` 更新） |
| TC-069 | 作法 6「`usd_note` 原樣保留」 | 功能 | Slurm 環境有概略美元 | 開 `/usage` | `usd_note` 那一句與 v3 一字不差 | 自動：`test_web_cost.py`、`test_su_usd.py` |
| TC-070 | 作法 6「去掉四張卡與『執行位置』欄」 | 功能 | 任意有資料的月份 | 開 `/usage` | 沒有國網 SU／雲端已用／雲端上限／雲端剩餘四張卡，沒有「執行位置」欄；`STRINGS` 沒有 `where_hpc`、`where_cloud`、`card_su*`、`card_used*`、`_HPC` | 自動：`test_web_cost.py`（co01 更新）、`test_cost_by_env.py` |
| TC-071 | 作法 6「上限列」；待決 1 | 功能 | 使用者設了每月上限，本月已用少於上限 | 開 `/usage` | 頁面最上方有恰好一行 `<p class="muted">`，字句沿用 `card_cap`／`card_left`／`set_by_admin`／`action` 的詞，顯示上限與剩餘 | 自動：`test_web_cost.py`（co04／co05 更新） |
| TC-072 | 作法 6「為 None 時顯示『未設定』」 | 功能 | 使用者沒設上限 | 開 `/usage` | 上限那一行顯示 v3 的「未設定」，不顯示 0 或空白 | 自動：`test_web_cost.py` |
| TC-073 | 作法 6「過額時 `state-failed`＋`⚠`」 | 功能 | 本月雲端已用超過上限 | 開 `/usage` | 上限那一行帶 `state-failed` 樣式與 `⚠` 符號與文字提醒（符號＋文字＋顏色） | 自動：`test_web_cost.py` |
| TC-074 | env08；tc051 | 功能 | 應用程式運行 | 請求 `/cost` | 回 404；路由路徑不含 `cost` | 自動：`test_cost_by_env.py`（env08）、`test_web_cost.py` |
| TC-075 | env08；專長守則（前端限制）；DESIGN 限制 | 功能 | 開 `/usage`、`/?run=<id>` 兩頁 | 檢查 HTML 與回應標頭 | 沒有 `<script`、`style=`、`<link`、`on*=`；沒有外部網址請求；CSP 標頭存在 | 自動：`test_cost_by_env.py`（env08）、`test_web_cost.py` |
| TC-076 | 作法 6 末段「用字」 | 功能 | 新增的 `STRINGS` 字串 | 跑 `test_web_wording_sweep.py`（含 `cost.seed(...)` 的費用頁） | 每個新字串 zh／en 成對；en 沒有 CJK；zh 沒有禁字表的字（你、這個、這次、這個月、還沒、算不出、讀不到、在哪裡、單獨的 run／runs…）；禁字表沒被放寬 | 自動：`test_web_wording_sweep.py` |
| TC-077 | 裁決（11-06 追進度）；裁決（自動補）第 1 點 | 功能 | 改動後的 `DESIGN.md` | 讀第 11 項（`11. **Cost**` 那一行） | 不再含 `never converted`；含「SU 旁可顯示依 su_rates.json 的概略美元，標明不是帳單；不跨環境相加」之意的新句；`never summed`、`Action-needed`、`environment / usage / status / scope` 等其他釘點仍在；`test_cost_docs_spec.py` 綠 | 自動：`test_cost_docs_spec.py` |

## User Story 7 — 不在範圍（確認真的沒做）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-078 | 裁決（自動補）第 4 點；DESIGN 第 11 項「Action-needed 提醒」留給 cost-reminder-quota | 不在範圍 | 本月用量將超過上限 | 看 `/usage` 與送出分析的畫面 | 沒有新增「送出會超過本月額度」的行動提示；只有舊的上限那一行（TC-071～073）；`DESIGN.md` 的 Action-needed 句一字未動 | 自動：`test_cost_by_env.py` |
| TC-079 | 計畫「不做」：本機運算環境（issue #367） | 不在範圍 | 一個沒有 hand-off 的本機分析 | 看 `compute_envs.KINDS` 與 `/usage` | 沒有新增「本機」環境類型；本機分析只落在 `unit is None` 的環境（TC-022） | 自動：`test_cost_by_env.py` |
| TC-080 | 計畫「不做」：為 AWS／Azure／K8s 做費用估算；改計價邏輯；填 `cloud_rates.json` | 不在範圍 | `git diff` | 檢查 `su.py`、`cloud_cost.py`、`data/cloud_rates.json` | `su.py` 沒改；`cloud_cost.py` 只有 `_launch_facts` 多回 `ce`、`platform`，其餘計價函式未動；`cloud_rates.json` 未改；AWS／Azure／K8s 仍顯示 `—`（TC-020、021） | 手動：`docs/TESTING.md`（閱卷核對 diff） |
| TC-081 | 計畫「不做」：「每月費用提醒額度」命名與上限設定、提醒行為；作法 4「`cloud` 整段不動」 | 不在範圍 | 呼叫 `my_usage` | 檢查 `cloud` 段 | `cloud` 段仍恰為 `used_usd, unknown_runs, cap_usd, remaining_usd, currency` 五鍵，語意與 v3 相同；頁面沒有出現「每月費用提醒額度」這個名稱 | 自動：`test_web_cost.py`（test_co11） |
| TC-082 | 計畫「不做」與待決 2：改 masthead | 不在範圍 | 任意頁面 | 看 masthead | 兩段字（`SU —`／`雲端 US$ —`，兩個 `class="cost"`）與 v3 相同，`web_board._mast`、`su_text` 沒被改 | 自動：`test_web_board.py`（L180–216）、`test_su_usd.py`（L530）、`test_web_cost.py`（co08） |
| TC-083 | 計畫「不做」：改 `su.month_total`；env12 | 不在範圍 | 原始碼 | grep `month_total` | `su.month_total` 沒改沒刪；`platform/abf_platform` 下除 `su.py` 以外的檔案都不引用它；`test_estimate_su.py` 仍綠 | 自動：`test_cost_by_env.py`（env12）、`test_estimate_su.py` |
| TC-084 | 計畫「不做」：改 PLATFORM.md／CLOUD.md；裁決第 1 點 | 不在範圍 | `git diff --stat` | 對照 base | `docs/PLATFORM.md`、`docs/CLOUD.md` 沒有任何改動 | 手動：`docs/TESTING.md`（閱卷核對） |
| TC-085 | 計畫「不做」：新增路由、資料表、欄位；tc063（不需要 migration） | 不在範圍 | 原始碼與資料庫結構 | 比對 base | 沒有新路由、沒有新資料表或欄位、沒有 migration 檔；tc063 仍綠 | 自動：`test_web_parity.py`、tc063 相關測試 |
| TC-086 | 計畫「不做」：新增色票；env14；作法 8 | 不在範圍 | 改動後的 `web_board.STYLE` | 擷取 STYLE 內顏色字面值集合，與 v3 比 | 集合與 v3 相同；新規則只引用既有 `var(--…)`；沒有 `style=`；CSP 的 sha256 隨 `style_hash()` 更新，`test_co10` 綠 | 自動：`test_cost_by_env.py`（env14）、`test_web_cost.py`（test_co10） |
| TC-087 | 裁決（自動補）第 1 點、完成標準 2 | 不在範圍 | `git diff base...HEAD -- DESIGN.md` | 看 diff | DESIGN.md 的 diff 只有第 11 項那半句；其餘文字（含 Action-needed 句、分析頁費用列句）一字不動 | 手動：`docs/TESTING.md`（閱卷核對） |
| TC-088 | 完成標準 2（修正後） | 不在範圍 | `git diff --stat base...HEAD` | 對照「範圍：檔案」 | 只含計畫「範圍：檔案」所列的檔案（含 DESIGN.md、test_cost_docs_spec.py）；沒有碰 `su.py`、`web_board._mast`、`platform/abf_station/`、`.github/` | 手動：`docs/TESTING.md`（閱卷核對） |

## User Story 8 — 畫面交付與文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-089 | 作法 8；裁決（自動補）第 2 點 | 功能 | 種子資料有：Slurm 環境、Google Batch 環境、AWS 環境（單位美元、用量 `—`）、一個執行中分析；另一組只有一個環境 | 跑 `scripts/dev/ui_check.py --start` | 共 12 張截圖：費用頁多環境 4（1440／390 px × zh／en）、分析頁費用列 4（1440／390 px × zh／en；結果階段與執行中各有出現）、費用頁單一環境 4；每張附一段白話說明（讓人看到什麼、與舊版差在哪）；截圖不在 Drive 工作區 | 手動：`docs/TESTING.md` |
| TC-090 | 作法 8；專長守則 | 功能 | 同 TC-089 | 跑 axe 掃描 | axe 沒有 serious 或 critical，也沒有新違規 | 手動：`docs/TESTING.md` |
| TC-091 | 專長守則「手機可用、鍵盤焦點可見」 | 功能 | 390 px 寬的費用頁與分析頁 | 檢視截圖，用鍵盤 Tab 到 summary 並按 Enter／空白鍵 | 沒有橫向捲動；summary 與連結的點擊區夠大；鍵盤聚焦時有可見外框；Enter 可展開／收合 | 手動：`docs/TESTING.md` |
| TC-092 | 完成標準 4 | 功能 | 改動後的 `docs/TESTING.md` | 讀該檔 | 有本功能的手動截圖步驟（含種子資料、`ui_check.py` 指令、截圖張數）與本功能新測試清單 | 手動：`docs/TESTING.md` |
| TC-093 | 完成標準 5；作法 1 | 功能 | ledger | 讀 ledger | 作法 1 的查證結論（`month_total` 誤計成立、三個洞）原樣寫入；並列出 cost-docs-rewrite 該更正的 `PLATFORM.md` 770–782 行與 708 行 | 手動：`docs/TESTING.md` |
| TC-094 | 完成標準 6；待決 1～5 | 功能 | ledger | 讀 ledger 的 planIssues | 待決 1～5 各有最終處理（預設或改動理由）；若採用與預設不同的做法，已回報 developer-agent | 手動：`docs/TESTING.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-095 | 原則 IV 第 9 條：數字來自檔案，缺口明寫在輸出裡 | 功能 | 一個沒有可計價紀錄的分析（AWS、執行中、費率空各一） | 在費用頁、分析頁費用列、`my_usage` 三處看同一分析 | 三處都是 None／`—`＋原因，沒有任何一處把缺口填成 0；有數字的地方能追到 `task_usage` 與費率檔 | 自動：`test_cost_by_env.py`（env03、env06、env09、env10） |
| TC-096 | 原則 IV 第 8 條：先讀原始碼再下結論（範圍字句） | 功能 | ledger 與 `su.py`、`cloud_cost.run_tasks_cost` | 讀 ledger 的範圍字句查證 | ledger 寫明已確認兩者是否依狀態過濾，字句與實際行為相符（對應 TC-046、047） | 手動：`docs/TESTING.md`（閱卷核對） |
| TC-097 | DESIGN 限制「每人只看自己的」；專長守則（篩選放在動作層，不靠畫面藏） | 例外 | ann 與 bob 各有分析 | 直接以 bob 呼叫 `actions.my_usage`、`actions.run_usage`（不經網頁） | `my_usage` 回傳不含 ann 的任何環境或分析；`run_usage` 對 ann 的 run 回 not-found | 自動：`test_cost_by_env.py`（env07） |
| TC-098 | 環境事實 tc069：站台名不得以字面值寫在程式裡 | 功能 | `web_cost.py`、`web_board.py` 原始碼 | 掃描原始碼 | 沒有寫死的站台名；`"NC"+"HC"` 拆字規則不變；使用者自取的環境名不算站台名 | 自動：tc069 相關測試 |
| TC-099 | 閱卷規則「放水」；允許改動的既有斷言清單 | 功能 | `git diff base...HEAD` 對 `platform/tests/` | 逐檔比對 | 被改的既有斷言都在計畫「允許改動」清單內，且各測試原本守的性質（讀不到索引不 500、別人看不到、US$ 不轉換、無 JS、CSP hash）仍被斷言；`test_co08`、`test_co10`、`test_no_other_currency…`、AST 掃描沒動，禁字清單只增不減；`test_su_usd.py` L476–478、L530–533 未動 | 手動：`docs/TESTING.md`（閱卷核對） |
| TC-100 | 專長守則（對等性）；作法 5；範圍：檔案 | 功能 | `test_web_parity.py` 與 `test_actions_layer.py` | 跑這兩個檔 | 網頁動作與動作層函式一一對應（`run_usage` 在 `WEB_ONLY`）；`BASELINE` 只因 `my_usage` 說明字改動而重新產生；兩檔綠 | 自動：`test_web_parity.py`、`test_actions_layer.py` |

<!--
IDs are never renumbered after approval; a removed case keeps its row, struck through.
後端專長守則的「寫入動作需經確認」與「跨使用者寫入被拒」：本功能全是讀取（作法 4、5 純讀；TC-044），沒有寫入動作，故無對應 TC；跨使用者「讀」見 TC-041、042、056、097。
-->
