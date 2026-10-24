# 測試案例總覽：資料庫先學會「clean_work」這個種類與「work_cleaned_at」欄位（cloud-cleanup-a）

狀態：合約已確認（2026-10-24，verifier）

**規格**：`specs/cloud-cleanup-a/plan.md`（本件沒有 spec.md，計畫即依據）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 全新資料庫認得 clean_work，寫入鎖不鬆（TC-001 至 008） | 4 | 4 | 0 | 8 |
| US2 — 舊資料庫升級：每一列原封不動（TC-009 至 021） | 13 | 0 | 0 | 13 |
| US3 — 重複開啟、中途失敗、同時開啟、唯讀開啟都安全（TC-022 至 029） | 3 | 5 | 0 | 8 |
| US4 — 本片只讓資料庫放得下，沒有功能上線（TC-030 至 035） | 0 | 0 | 6 | 6 |
| US5 — 既有測試只准改六處（TC-036 至 043） | 8 | 0 | 0 | 8 |
| US6 — 交付紀錄（TC-044 至 048） | 4 | 0 | 1 | 5 |
| 憲法與安全網（TC-049 至 052） | 4 | 0 | 0 | 4 |
| **合計** | 36 | 9 | 7 | 52 |

驗證方式：純自動 38 條；「自動＋閱卷」混合 8 條（TC-032、036 至 042）；純手動（閱卷）6 條（TC-031、044 至 048）。即自動驗證共 46 條、手動 6 條。
總數 52 條，在「每片 ≤60 TC」的上限內。計畫列的 21 個具名新測試全部對得上 TC（見下）；另有 5 條（TC-006、015、016、020、028）寫在計畫內文但不在那 21 個名字之內，可併入同主題的測試，但每條要有自己的斷言。

## 請你判斷的三件事

1. **每條是不是你要的？** 尤其是 TC-001／003（`clean_work` 確認種類與工作種類同名、跟 `launch`／`cancel` 分開）、TC-004／005（你在 `CLAUDE.md` §3.4 的鎖：寫入型工作沒有確認憑證，資料庫就拒絕）、TC-009／011（升級後每一列、每個連結都沒變）。
2. **有沒有漏掉的出錯情況？** 想像升級時出事：中途斷掉（TC-025／026）、兩個程式同時開（TC-027）、舊庫裡有指向不存在請求的壞連結（TC-028）、只讀的程式碰到舊庫（TC-029）。
3. **「不在範圍」對嗎？** 這片不做的事：沒有任何程式會寫入 `clean_work` 或 `work_cleaned_at`（TC-030）、不動 `confirm.py`／`jobs.py`／網頁／代理（TC-031、035）、不加表不加索引（TC-032）、不刪舊列（TC-033）、不改文件（TC-048）。

## 覆蓋檢查

- 計畫「失敗先行測試」列的 21 個具名測試，全部有對應 TC（對應需求欄寫出測試名）：是。對照：
  `test_fresh_confirmations_take_clean_work_…`＝TC-001、002；`test_fresh_jobs_take_clean_work_only_with_a_confirmation`＝TC-003、004、005；`test_fresh_jobs_still_refuse_…`＝TC-007；`test_launches_has_work_cleaned_at_…`＝TC-008；`…have_the_same_structure…`（裁決二 第 9 點已改名）＝TC-019；`test_old_confirmations_table_is_rebuilt_…`＝TC-009；`test_a_database_before_009c_…`＝TC-010；`test_jobs_referencing_…`＝TC-011；`test_foreign_key_check_is_empty_…`＝TC-012；`test_jobs_sequence_counter_survives`＝TC-013；`test_a_jobs_table_without_read_task_log_…`＝TC-014；`test_a_launches_table_without_the_attempt_columns_…`＝TC-017；`test_old_launches_rows_keep_every_old_value_…`＝TC-018；`test_opening_twice_changes_nothing`＝TC-022、023；`test_a_failure_in_the_copy_step_…`＝TC-025；`test_the_next_open_after_that_failure_succeeds`＝TC-026；`test_a_second_connection_…`＝TC-027；`test_an_already_new_confirmations_table_is_not_touched`＝TC-024；`test_pending_and_void_requests_…`＝TC-021；`test_read_only_open_of_an_old_database_…`＝TC-029；`test_store_source_has_no_subprocess_and_no_forbidden_word`＝TC-050、051。
- 計畫內文有、但不在那 21 個名字內的行為：裁決二 第 7 點的兩個方向（只有 `read_task_log`、沒有 `clean_work` 的舊 jobs 要重建＝TC-015；兩者都有就不動＝TC-016）、唯讀工作不受寫入鎖影響＝TC-006、007 庫路徑＝TC-020、外鍵檢查失敗要回滾＝TC-028：是（都有 TC）。
- 範圍：檔案的「必須更新的既有斷言」六處，全部有 TC：是（TC-036 至 041；TC-042 確認其他測試沒被動、沒被放水）。
- 計畫「完成標準」3 條，全部有 TC：是（第 1 條＝TC-043、045、034；第 2 條＝TC-046；第 3 條＝TC-048）。
- 計畫「不做」各項，全部有「不在範圍」TC：是（不改 `confirm.py`／`jobs.py`、不寫產生 `clean_work` 的程式＝TC-030、035、031；不動 `launches` 其他欄位／`jobs` 欄位順序／不加索引不加新表＝TC-032；不做資料搬移以外的清理＝TC-033；不碰 AWS／Azure／K8s 與送出／取消／續跑＝TC-031 的禁碰清單與 TC-034）。
- 維護者原話 4 句：「跑完經本人確認刪中間檔（work）…不自動刪」＝TC-001、003、030；「新 kind `clean_work`（確認種類與工作種類同名）」＝TC-001、003；「網頁畫面以外的 B 級…verifier 通過＋CI 綠就由我合併」＝TC-031、043；「直接 `scancel`，以及刪改叢集端…一律擋住」→ 資料庫層寫入鎖＝TC-004、005：是。
- 裁決 1 至 5 與裁決二 7 至 10：1＝TC-001、003；2＝流程；3＝TC-004、005；4＝TC-008、018、030（欄位只建不寫）；5＝TC-031、045；二-7＝TC-014 至 016；二-8（21 條為準）＝本表對照；二-9＝TC-019；二-10＝TC-046。
- 專長守則（backend）：migration TC＝TC-009 至 021、025 至 029（有資料結構變動，附 migration，計畫「migration 需要」已寫理由）；確認管道 TC＝TC-004、005（沒有憑證，資料不得改變）；對等性 TC＝本片沒有使用者可見動作，以 TC-034（工具數仍 12，無新動作）、TC-035（動作層不認識 `clean_work`）代替，既有 `test_actions_layer.py` 在 TC-043 全套中必須仍綠；跨使用者 TC＝本片沒有新增任何讀寫路徑（TC-030、031），擁有者欄位 `caller_user_id` 的逐列保留由 TC-009 驗證，既有的跨使用者測試在 TC-043 中必須仍綠；錯誤訊息與日誌不含密鑰＝本片不新增任何回應或日誌內容（遷移只在升級失敗時丟出錯誤，TC-025、028），不另設 TC。
- 憲法：原則 I（TC-070）＝TC-049；原則 II（TC-071、`no_second_run_state_test.sh`）＝TC-050、052；TC-061 禁用字＝TC-051；寫入要確認＝TC-004、005、052。

## 我（撰寫者）不確定的地方

1. TC-020（最舊的 007 庫升級後結構與新庫相同）不在計畫的 21 個名字內，我是依「目標」與「環境事實 :381」加的；若你覺得 007 庫已不會再遇到，可以刪，但要由你說。
2. TC-028：舊庫裡若有指向不存在請求的壞連結，計畫規定「回滾並丟錯」，也就是這個平台會打不開，直到有人修那筆壞資料。這是你要的行為嗎？（我照計畫寫，沒有改動。）
3. 計畫「作法」第 2 節第 1 點（含 `clean_work` 就跳過）與裁決二 第 7 點（同時含 `read_task_log` 與 `clean_work` 才跳過）字面不同；我照較晚、且是回應出題退回的裁決二。這樣對嗎？
4. TC-027（同時開啟）要怎麼造出「同時」由 executor 決定（兩個執行緒或在複製步驟停住）；我只規定結果：兩邊都不失敗、沒有重複列。

## 核可紀錄

（無；本合約由 verifier 確認，維護者未另行核可。）
