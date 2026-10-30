# 測試案例：雲端月上限說明改成符合「價目表為空」的現況

<!--
Written by the verifier (CONTRACT mode). Source: specs/cloud-cap-empty-rates-doc/plan.md (含裁決 4–7). 沒有維護者逐字原話；輸入與預期取自計畫寫明的情境與固定字串。
-->

**規格**：`specs/cloud-cap-empty-rates-doc/plan.md`（本片無 spec.md，以計畫為準；範圍以裁決 7 為準）　**總覽**：`test-case-overview.md`

固定片語（逐字，不得改）：
- 中文：`要等價目表填入後才會生效`
- 英文：`only takes effect once the price list is filled in`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、條件不同時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

驗證方式說明：「自動」＝`platform/tests/test_cloud_cost.py` 內的測試（`py -3 -m pytest platform/tests/test_cloud_cost.py`）。「手動」＝驗收者讀檔或看 `git diff`、ledger；`docs/TESTING.md` 目前沒有對應步驟（見總覽的疑問）。

## User Story 1 — 文件不再說「本月已用滿」今天擋得住（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 決定 4；裁決 5 | 功能 | 出貨的 `cloud_rates.json` 的 `regions` 是空的 | 掃 `docs/CLOUD.md` 每一行 | 凡是同一行同時含「價目表」與「空的」、又含「已用滿」的行，同一行也必須含「要等價目表填入後才會生效」 | 自動：`test_cloud_cost.py`（文件測試，計畫名 `test_cloud_doc_does_not_claim_the_monthly_cap_works_while_the_price_list_is_empty`） |
| TC-002 | 裁決 5 | 功能 | 同 TC-001 | 在 `docs/CLOUD.md` 全文找固定片語 | 全文至少一處含「要等價目表填入後才會生效」（不能因為沒有任何行符合條件而空過） | 自動：同 TC-001 的測試 |
| TC-003 | 裁決 4、5（`docs/TESTING.md` 第 621 行） | 功能 | 同 TC-001 | 掃 `docs/TESTING.md` 每一行 | 凡同一行同時含 "empty price list" 與 "used up" 者，同一行也含 "only takes effect once the price list is filled in"；且該檔全文至少一處含此英文固定片語 | 自動：`test_cloud_cost.py` |
| TC-004 | 裁決 4、7（`docs/CLOUD.md` 第 66 行） | 功能 | 同 TC-001 | 讀 `docs/CLOUD.md` 第 66 行那一句（「目前出貨的價目表是空的…」） | 句中若仍提到「已用滿」，同一句／同一行必含「要等價目表填入後才會生效」；不再把「已用滿」列為今天擋得住的項目；措辭與第 43 行一致 | 自動：由 TC-001 的掃描涵蓋；措辭一致由驗收者讀檔 |
| TC-005 | 作法 決定 2（第 43 行） | 功能 | 改完文件 | 讀 `docs/CLOUD.md` 第 43 行 | 說出四件事：(a) 價目表是空的，每次預估都是「無法預估」；(b) 每個 run 的實際花費也算不出來，「本月已用」一律當 0 美元，有未計價的 run 時只會標「至少」；(c) 上限今天只擋得住「沒設上限」「上限 0」；(d)「本月已用滿」要等價目表填入後才會生效 | 手動：驗收者讀 `docs/CLOUD.md` 第 43 行 |
| TC-006 | 作法 決定 1；證據（既有文件測試） | 功能 | 改完文件 | 跑既有 `test_the_cloud_document_says_what_it_must` | 維持綠：文件仍含「第一次」「擋不住」「只含運算」「同一個 pipeline」「最近一次成功」「不會自動停止正在跑的雲端工作」「只會擋下新的送出」「cloud_rates.json」 | 自動：既有測試（不得改動） |
| TC-007 | 作法 決定 1（第 19 行） | 功能 | 改完文件 | 讀 `docs/CLOUD.md` 第 19 行 | 仍說上限擋不住「這一次太貴」，且新補一句：價目表填入之前，連「本月已用滿」也擋不住（指向價目表一節）；其餘原句（替第一位使用者把上限設小，例如 5 美元）仍在 | 手動：驗收者讀 `docs/CLOUD.md` 第 19 行（計畫明說不加機器斷言） |
| TC-008 | 裁決 6（守衛） | 例外 | 假設將來 `cloud_rates.json` 已填入任何區域 | 讀 TC-001／TC-003 那支文件測試的開頭 | 測試一開始就判斷 `regions` 是否為空；非空時直接 `pytest.skip`（價目表填好後這幾句本來就該改寫），不會先做文件斷言再 skip，也不會因此失敗而擋住 `cloud-rates-fill` | 自動：測試原始碼由驗收者讀（守衛在任何斷言之前） |

## User Story 2 — 程式現況被測試釘住，文件與程式不能再分家（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | 失敗先行 #1（特徵化） | 功能 | 載入出貨的（空）價目表；某使用者的月上限設為 5.0 美元；替他放兩筆已結束的 Google Batch run（在空價目表下是未計價） | 查他的「本月已用」，再問一次雲端送出會不會被上限擋 | 本月已用金額為 0；`unknown_runs` 至少 1；`ask` 的結果是 `None`（放行）。也就是：價目表為空時，累積用量不會讓月上限「用滿」 | 自動：`test_cloud_cost.py`（計畫名 `test_empty_rates_never_count_used_money_so_the_monthly_cap_cannot_fill`）；v3 上應直接綠 |
| TC-010 | 裁決 6（守衛） | 例外 | 假設 `cloud_rates.json` 已含任何區域 | 讀 TC-009 測試的開頭 | 先判斷價目表有無區域；有區域就 `pytest.skip("price list is filled; …")`，之後才做斷言；不是先斷言再 skip | 自動：測試原始碼由驗收者讀 |
| TC-011 | 失敗先行 #2、#3；突變證明 | 功能 | 一個乾淨的 worktree | (1) 改文件前先跑文件測試；(2) 改完文件後再跑；(3) 暫時把 `docs/CLOUD.md` 第 43 行還原成舊句子再跑，然後還原 | (1) 紅（舊文件把「本月已用滿」列為擋得住）；(2) 綠；(3) 紅，還原後綠。紅／綠輸出貼在 ledger；最終 diff 不含這次暫時還原 | 手動：驗收者查 ledger |

## User Story 3 — 只改文件與測試，其他一律不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 不做 1；範圍「不准碰」 | 不在範圍 | 實作完成 | `git diff <base>...HEAD --stat` | 不含 `platform/abf_platform/cloud_cost.py`，也不含 `web.py`、`mcp_server.py`、`jobs.py`、`build.py`、`launch.py`、`compute_envs.py`、`tests/platform_upgrade_test.sh` 等任何程式檔；`cap_problem` 沒有改成在價目表為空時擋 | 手動：驗收者看 diff |
| TC-013 | 不做 2；範圍 | 不在範圍 | 實作完成 | 看 `platform/abf_platform/data/cloud_rates.json` 與既有 `test_the_shipped_rates_file_is_valid_and_empty` | 價目表檔案沒被改、沒填價；`regions` 仍為空；既有測試維持綠 | 自動：既有 `test_the_shipped_rates_file_is_valid_and_empty` |
| TC-014 | 不做 3；裁決 2 | 不在範圍 | 實作完成 | 看 diff 有沒有 `specs/` 底下（`specs/cloud-cost-wire/plan.md`、`specs/cloud-cost/test-case-overview.md` 等）的變動 | `specs/` 歷史紀錄一字未動（本任務自己的 `specs/cloud-cap-empty-rates-doc/` 之外） | 手動：驗收者看 diff |
| TC-015 | 不做 4 | 不在範圍 | 實作完成 | 看 diff 有沒有新依賴、新 CLI 旗標 | 沒有新增依賴、沒有新增 CLI 旗標 | 手動：驗收者看 diff |
| TC-016 | 裁決 4、7；完成標準 | 不在範圍 | 實作完成 | `git diff <base>...HEAD --stat` 與逐行看 diff | 檔案只有三個：`docs/CLOUD.md`、`docs/TESTING.md`、`platform/tests/test_cloud_cost.py`。`docs/CLOUD.md` 只動第 19、43、66 行三處；`docs/TESTING.md` 只動第 621 行一處；其他文件句子不新增、不刪除。測試檔只新增測試，既有測試沒有被刪、改、略過或放寬 | 手動：驗收者看 diff 並對照 base |
| TC-017 | 環境事實「不准改」 | 不在範圍 | 實作完成 | 看 diff | 沒有改 `spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` | 手動：驗收者看 diff |
| TC-018 | 完成標準 | 功能 | 實作完成 | 跑 `py -3 -m pytest platform/tests/test_cloud_cost.py` | 全檔綠（價目表為空時，新文件測試與特徵化測試皆執行並通過，不是靠 skip 過關）；既有 `test_with_the_empty_shipped_rates_the_cap_still_works` 與 `test_the_cloud_document_says_what_it_must` 維持綠 | 自動：`test_cloud_cost.py` |

## 憲法與安全網

<!-- 計畫只引用派工指示「絕不放寬安全網」；未逐條對應 constitution 編號。專長守則（backend）的對等性、跨使用者、確認管道、日誌密鑰、migration 各項，本片不碰執行期、路由或資料，不適用；只留 TC-020 說明 migration。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 派工指示「絕不放寬安全網」（雲端月上限） | 功能 | 空價目表 | 對照 base：上限 5 美元時放行；上限 0 時仍被擋（既有 `test_with_the_empty_shipped_rates_the_cap_still_works`）；沒設上限時仍不准送雲端（既有 `test_no_cap_set_means_no_cloud_launch`） | 三種行為與 base 完全相同，沒有任何一種被放寬或收緊 | 自動：既有測試維持綠 |
| TC-020 | 專長守則（backend）：資料結構變動需 migration | 不在範圍 | 實作完成 | 看 diff 有沒有資料結構、資料內容的變動 | 沒有；因此不需要 migration | 手動：驗收者看 diff |
