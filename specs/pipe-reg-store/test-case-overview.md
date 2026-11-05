# 測試案例總覽：管線登記紀錄表與狀態機（動作層，先不接檢查與測試）

狀態：合約已確認（2026-11-05，verifier）

**規格**：無獨立 spec.md，以 `specs/pipe-reg-store/plan.md`（含兩份「裁決」）為準　**明細**：`test-case.md`

## 一眼看完

| User Story（以計畫的主題分組） | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| 一、提出登記與紀錄內容（TC-001～009） | 9 | 0 | 0 | 9 |
| 二、名稱與版本驗證（TC-010～022） | 2 | 11 | 0 | 13 |
| 三、確認管道（TC-023～026） | 0 | 4 | 0 | 4 |
| 四、範圍與不在範圍（TC-027～031） | 0 | 0 | 5 | 5 |
| 五、擁有者規則（TC-032～038） | 1 | 6 | 0 | 7 |
| 六、動作清單對等性與既有測試（TC-039～043） | 4 | 0 | 1 | 5 |
| 七、移除登記（TC-044～050） | 4 | 3 | 0 | 7 |
| 八、清單與舊資料合併（TC-051～060） | 9 | 0 | 1 | 10 |
| 九、資料表（TC-061～066） | 2 | 4 | 0 | 6 |
| 憲法與安全網（TC-067～069） | 2 | 1 | 0 | 3 |
| **合計** | 33 | 29 | 7 | 69 |

自動驗證 66 條、手動驗證 3 條（TC-029、TC-041 為 `docs/TESTING.md` 新增的兩步；TC-066 為驗收者讀 ledger）。

固定編號：計畫裁決引用了 TC-029（改動檔案清單）、TC-032（乙以甲的環境名讀清單）、TC-041（三個名單測試只有新增行），本檔編號與之對上。

## 請你判斷的三件事

1. **每條是不是你要的？** 特別看 TC-001、TC-003（nano4 與雲端提出後都是「檢查中」）、TC-051、TC-056、TC-057（nano4 既有 4 筆只顯示「待測試」，這一版不會有任何管線顯示為「已登記」）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它：貼錯管線名（TC-010～012）、版本寫 `main`（TC-014）、替別人的環境登記（TC-034）、移除一個根本沒登記的東西（TC-045、046）。
3. **「不在範圍」對嗎？** 這版不排檢查、不寫環境的管線清單、不判定「已登記」、不接網頁／MCP／指令列、不改既有的登記與移除功能（TC-027～031、TC-057）。

## 覆蓋檢查

- 規格裡的需求（FR）：本任務沒有 spec.md，改以計畫條目計：資料表、對外狀態、名稱與版本驗證、source、四個函式、不需 migration、雙語錯誤訊息、計畫列出的 10 項失敗先行測試、五項允許的斷言變動、完成標準、PITFALLS 第 55 條、裁決 1～6。全部都有測試案例：是
- 維護者原話（4 段）全部有對應 TC（見 test-case.md 開頭對應表）：是
- 規格裡的驗收情境：無獨立情境；計畫列的 10 個測試名稱全部對上：`test_propose_creates_checking_row`→TC-001、`test_propose_on_cloud_env_is_remote`→TC-003、`test_unconfirmed_propose_and_remove_change_nothing`→TC-023／024、`test_second_user_cannot_read_or_write`→TC-032／034／035、`test_duplicate_propose_is_not_doubled`→TC-004、`test_removed_then_proposed_again_returns_to_checking`→TC-005、`test_bad_name_or_revision_names_the_field`→TC-010～017、`test_legacy_site_pipelines_show_as_awaiting_test`→TC-051／052、`test_registered_list_excludes_legacy_and_checking`→TC-055／056、`test_table_is_created_on_first_use_and_old_db_still_opens`→TC-009；裁決新增的 `test_removed_row_suppresses_legacy_entry`→TC-050、`test_remove_unknown_registration_is_refused`→TC-045、`test_remove_legacy_only_is_refused`→TC-046、`test_remove_twice_is_noop`→TC-047。全部有：是
- 規格裡「不在範圍」（計畫「不做」4 條）共 4 條，全部都有「不在範圍」測試案例：是（1 排檢查、寫 sitePipelines→TC-027／028；2 送出測試、推導已登記→TC-057；3 MCP、指令列、網頁→TC-029；4 不改既有 register／remove→TC-029／030）
- 專長守則（backend）：對等性→TC-039／040；跨使用者讀與寫各一→TC-032（讀）、TC-034／035（寫）；確認管道→TC-023～026；錯誤訊息與日誌→TC-022、TC-069；migration→TC-009（並由 TC-066 查 ledger 的「不需要 migration」理由）：全部有

## 我（撰寫者）不確定的地方

1. 本任務沒有 spec.md，計畫即需求。若維護者想要獨立規格，需回頭補；不影響本檔檢查的內容。
2. TC-066（ledger 內容）屬計畫「完成標準」，但裁決 1 只准 `docs/TESTING.md` 加兩步，所以它沒有 TESTING.md 步驟，改由驗收者直接讀 ledger。要不要再加第三步？
3. 計畫未規定的事，本檔刻意不斷言：首次提出時回傳的 `changed` 值；一般（非舊資料）項目是否帶 `legacy` 欄位；`ce=None` 時是否也合併各 slurm 環境的舊資料（TC-033、TC-037、TC-059 只檢查擁有者與紀錄列）；移除時對壞管線名／壞版本的驗證；壞版本的錯誤句子全文（只要求點名 `revision`）。
4. TC-029 允許的檔案清單把 `specs/pipe-reg-store/`（計畫與 ledger）算進去，因為它們已在分支上；若維護者認為 diff 應完全不含它們，請告知。

## 核可紀錄

（無；狀態為 verifier 確認，尚未有維護者親自核可。）
