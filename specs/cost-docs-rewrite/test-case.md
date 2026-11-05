# 測試案例：費用規格改寫（純文件）——以運算環境為單位、每月費用提醒額度由使用者自設

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本任務沒有 spec.md；`specs/cost-docs-rewrite/plan.md`（含「維護者原話」「作法」「裁決」「裁決（自動補，2026-11-06）」）即規格。
「對應需求」欄寫的是 plan 的段落：維護者原話＝「原話」、作法 N＝「作」N、裁決 N＝「裁」N、自動補裁決 N＝「補裁」N。
-->

**規格**：`specs/cost-docs-rewrite/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

說明：本任務只改文件，所以「預期結果」都是「文件裡看得到／看不到什麼字」。「自動」＝新增檔 `platform/tests/test_cost_docs_spec.py`（下稱「釘字測試」）或既有測試檔必須真的斷言這個預期結果，驗收時若測試斷言得比預期結果弱，判不通過。「手動」＝verifier 驗收時打開文件或 `git diff` 逐項比對（本任務禁止改 `docs/TESTING.md`，所以手動步驟寫在本表，不寫進 TESTING.md）。

## User Story 1 — DESIGN.md 費用頁（第 11 項）與設定頁（第 12 項）依新規格改寫（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作 1；原話「國網／雲端二分法很奇怪」 | 功能 | 改寫完成的 `DESIGN.md` | 讀 `**Cost**` 那一行 | 含 "one row per compute environment"（以運算環境為單位、每個環境一列）、"expand"（可展開看該環境底下的分析），並說明只有一個環境時就一列；含 "per compute environment" | 自動：`platform/tests/test_cost_docs_spec.py::test_design_cost_item_is_per_environment_rows` |
| TC-002 | 作 1 | 功能 | 同上 | 讀 `**Cost**` 那一行 | 寫明單位依環境：國網（Slurm）環境用 SU、雲端環境用美元；含 "never summed" 與 "never converted"（不加總、不換算） | 自動：釘字測試（同上測試，須斷言 "never summed"） |
| TC-003 | 作 1 | 功能 | 同上 | 讀 `**Cost**` 那一行 | 新增「分析頁費用列」，欄位順序寫成 "environment / usage / status / scope"，並指出對應 Seqera 執行頁的 "Metrics" 分頁 | 自動：釘字測試（"Metrics" 在 A 組第 1 條；"environment / usage / status / scope" 在補強 (f)） |
| TC-004 | 作 1；原話「11-05 費用頁 v3『不好』」 | 功能 | 同上 | 讀 `**Cost**` 那一行 | 不含 "Reconciled"、不含 "Estimate, bill pending"、不含 "NCHC SU / Cloud used"（舊版卡片與狀態詞已刪） | 自動：釘字測試（A 組第 1 條；"Estimate, bill pending" 須一併斷言） |
| TC-005 | 作 1；補裁 2 | 功能 | 同上 | 讀 `**Cost**` 那一行 | 不含 "NT$"。（只限第 11 項這一行；第 34 行 Masthead 仍有 "cloud NT$ used / cap"，見 TC-054，不算失敗） | 自動：釘字測試（A 組第 1 條，範圍限定於 `**Cost**` 那一行） |
| TC-006 | 作 1 | 功能 | 同上 | 讀 `**Cost**` 那一行 | 保留 "Action-needed" 通知概念；觸發條件改為「這次送出會超過本人自設的每月費用提醒額度」；不再出現 "cloud cap"；「用 Slurm 環境／等下月重置」兩個出路的句子可留 | 自動：釘字測試（補強 (f) 斷言 "Action-needed"；條件句由 verifier 讀檔確認） |
| TC-007 | 作 1；原話「費用頁定案草稿 Version 6，他回『好的可以』」；補裁 5 | 功能 | 打得開 artifact `https://claude.ai/artifact/DguBi1tA1vpwmj1B7zd1GY`（Version 6） | verifier 開連結，對照 `**Cost**` 那一行 | 文字與草稿一致：每環境一列可展開、單位依環境、不加總；沒有草稿以外的卡片或區塊。連結打不開則標 UNVERIFIED，交維護者本人看，不得用猜測代替 | 手動：verifier 驗收時開連結對照 |
| TC-008 | 原話「國網／雲端二分法很奇怪」（11-05） | 功能 | 同上 | 讀 `**Cost**` 那一行 | 費用頁不再以「國網一區、雲端一區」分區：沒有「NCHC SU / Cloud used」兩張卡片，國網與雲端環境只是同一張環境列表裡的不同列 | 自動：釘字測試（"NCHC SU / Cloud used" 不存在；A 組第 1 條） |
| TC-009 | 作 2；原話 7-12「不要用『個人 · 存取權杖』」 | 功能 | 同上 | 讀 `**Settings**` 那一行 | 含 "Access token"，且「存取權杖」單獨一項；不含 "Personal ("（不再以 Personal 為組名） | 自動：`platform/tests/test_cost_docs_spec.py::test_design_settings_access_token_is_its_own_item` |
| TC-010 | 作 2 | 功能 | 同上 | 讀 `**Settings**` 那一行 | 逐步模式（step-by-step mode）、開發模式（development mode）各自另列，不掛在 Personal 底下；「Operator panel and Roles as dashed "coming later"」保持原樣 | 手動：verifier 讀 `git diff` 的第 12 項 |
| TC-011 | 作 2；原話「4 件全好」（1）額度由使用者本人設 | 功能 | 同上 | 讀 `**Settings**` 那一行 | 設定頁項目中列出「每月費用提醒額度」（monthly cost reminder quota，英文措辭計畫未固定），並註明由使用者本人設 | 手動：verifier 讀 `git diff`（計畫未固定英文字串，見總覽疑問 3） |
| TC-012 | 作 1「不得自己加卡片」 | 功能 | 同上 | 讀 `**Cost**` 那一行 | 不再有任何卡片（cards）描述，不含 "cards" | 自動：釘字測試（須斷言不含 "cards"） |

## User Story 2 — docs/CLOUD.md：「每月費用提醒額度（你自己設）」取代「管理者設上限」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 補裁 6 (a)(b) | 例外 | 改寫完成的 `docs/CLOUD.md` | 讀「拒絕的時候看到什麼」節 | 節內有統一狀態註記全文（「規格已定；程式尚未改（見 cost-reminder-quota 計畫）。在那之前，終端機指令仍是唯一寫入口，未設額度仍擋雲端送出。」），註記後有一句「現行程式仍顯示舊訊息，將由 cost-reminder-quota 計畫改」 | 手動：verifier 讀 CLOUD.md 該節 |
| TC-014 | 作 3；補裁 6 (b) | 例外 | 已設額度、「已用＋預估」會超過 | 讀「拒絕的時候看到什麼」節的訊息範例 | 範例改為「……會超過。請到網頁調整每月費用提醒額度，或下個月再送出」；不逐字引用舊句「請找管理者調整上限」 | 自動：釘字測試（A 組第 3 條斷言不含「請找管理者調整上限」；須再斷言含新句） |
| TC-015 | 補裁 1 | 功能 | 同上 | 讀 CLOUD.md 第 1、3、7 行 | 第 1 行標題恰為「# 雲端費用：預估、已用、每月費用提醒額度」；第 3 行「上限怎麼設」改為「額度怎麼設」；第 7 行改為「你自己設的每月費用提醒額度」，不再有「管理者替你設的每月上限」 | 自動：釘字測試（須斷言標題行全文；補裁 1 加的斷言） |
| TC-016 | 補裁 3；TC 出題要求 | 功能 | 同上 | 搜尋舊句「沒有任何網頁、MCP 工具或聊天指令能讀或改它」、「沒設上限就不能送到雲端（安全預設）」、「管理者把上限調低」 | 這三句只出現在「（過渡：程式尚未改時）」段內，且緊接統一狀態註記；正文（「每月費用提醒額度（你自己設）」「確認畫面」「目前的限制」）一律寫新規格 | 手動：verifier 讀 CLOUD.md 逐句找 |
| TC-017 | 作 3；原話「雲端上限不該由管理者設，是使用者自己的事」（11-05） | 功能 | 同上 | 在 CLOUD.md 全文找「只有管理者」「請找管理者調整上限」「請管理者替第一位使用者」「管理者替你設」 | 四串都不存在 | 自動：`platform/tests/test_cost_docs_spec.py::test_cloud_doc_quota_is_user_set_and_unset_does_not_block`（前三串在 A 組第 3 條；「管理者替你設」須一併斷言） |
| TC-018 | 作 3；原話「4 件全好」（1）額度由使用者本人設；補裁 4 (e) | 功能 | 同上 | 讀「## 每月費用提醒額度（你自己設）」節 | 段名恰為此；含名稱「每月費用提醒額度」；寫明由使用者本人在網頁設、單位美元；「0」與「1,000,000」寫在同一行（範圍 0～1,000,000，只改誰設） | 自動：釘字測試（A 組第 3 條＋補強 (e)） |
| TC-019 | 作 3；原話「4 件全好」（2）未設不擋雲端送出 | 功能 | 使用者尚未設額度 | 讀 CLOUD.md | 含固定句「未設定每月費用提醒額度。實際費用以雲端帳單為準。」，並寫明未設時不擋雲端送出 | 自動：釘字測試（A 組第 3 條） |
| TC-020 | 作 3 | 功能 | 同上 | 讀「確認畫面長什麼樣」節 | 該節改稱「四種」寫法（不再是「只有三種寫法」）；原有三種寫法保持，第 4 種即 TC-019 的固定句 | 自動：釘字測試（須斷言不含「只有三種寫法」、含「四種」及固定句） |
| TC-021 | 作 3；裁 2 | 例外 | 本人已設額度，「已用＋預估 > 額度」 | 讀 CLOUD.md | 寫明仍拒絕新的送出；說明這是本人自己訂的提醒線、不是雲端的預算；本人可自己調高；剛好等於額度放行的判斷式不變 | 手動：verifier 讀 CLOUD.md |
| TC-022 | 作 3 | 功能 | 同上 | 讀「每月費用提醒額度（你自己設）」節 | 說明名稱意思：「提醒」＝本人給自己的線；平台算的是估算（只含運算）；真正的保護在雲端預算（指向下一節） | 手動：verifier 讀 CLOUD.md |
| TC-023 | 作 3 | 功能 | 同上 | 讀第 19 行段落 | 「請管理者替第一位使用者把上限設小一點」改為「請本人把額度設小一點，例如 5 美元」；「第一次」「擋不住」整段保留 | 自動：釘字測試（新句須斷言；「第一次」「擋不住」由 `platform/tests/test_cloud_cost.py::test_the_cloud_document_says_what_it_must` 釘住） |
| TC-024 | 補裁 3 | 功能 | 同上 | 讀「目前的限制」節的第 41、42 行條目 | 第 41 行寫「先查本人的額度（已設才查）」；第 42 行寫「按送出前本人調低額度」，兩條都不含「管理者」把額度調低的說法 | 手動：verifier 讀 CLOUD.md |
| TC-025 | 作 3 | 功能 | 同上 | 讀「目前的限制」中 `abf-launch` 那條 | 「管理者自己打的 `abf-launch` 不查」這條保留，但「上限」一律改稱「額度」 | 手動：verifier 讀 CLOUD.md |
| TC-026 | 補裁 4 (b)；補裁 6 (a) | 功能 | 同上 | 在 CLOUD.md 內數統一狀態註記全文出現幾次 | 含全文（含「見 cost-reminder-quota 計畫」），且出現次數至少 2 | 自動：釘字測試（補強 (b)） |
| TC-027 | 補裁 6 (a) | 功能 | 同上 | 檢查統一狀態註記的位置 | 「每月費用提醒額度（你自己設）」節、「拒絕的時候看到什麼」節、「（過渡：程式尚未改時）」段三處各放一次（共三處，比 TC-026 的「至少 2」更嚴，以此為準） | 手動：verifier 讀 CLOUD.md 三處 |
| TC-028 | 作 5；裁 1 | 功能 | 同上 | 讀「（過渡：程式尚未改時）」小段 | 段名含「（過渡：程式尚未改時）」；內含統一狀態註記、指令 `abf-platform user add <名字> --lab <實驗室> --cloud-cap-usd 20` 與 `abf-platform user cloud-cap <名字> 25`，並註明「這是平台主機上的舊寫入口，將由使用者網頁取代」 | 自動：釘字測試（須斷言；「user add」「--cloud-cap-usd」「user cloud-cap」另由 `test_cloud_cost.py::test_the_cloud_document_says_what_it_must` 釘住） |
| TC-029 | 作 3 | 功能 | 同上 | 讀「目前的限制」中「台幣」「帳單預算」那條（約第 45 行） | 保留：雲端預算只是 Google 的事後提醒、平台沒有台幣、沒有任何換算 | 自動：`platform/tests/test_cloud_cost.py::test_the_cloud_document_says_what_it_must`（「台幣」「帳單預算」） |
| TC-030 | 作 4；作 3 | 功能 | 同上 | 在 CLOUD.md 找 "NT$"、「新台幣」「匯率」、exchange rate、台幣金額 | 都不存在（唯一例外是 TC-029 那條既有的「台幣」「帳單預算」敘述） | 自動：`test_cloud_cost.py::test_the_cloud_document_says_what_it_must` |
| TC-031 | 原話「名稱定稿：每月費用提醒額度」；補裁 1、4 (a) | 功能 | 三份改寫完成的文件 | 在 DESIGN.md、docs/CLOUD.md、docs/PLATFORM.md 找「每人每月上限」 | 三份都不存在 | 自動：釘字測試（補強 (a)） |
| TC-032 | 原話「名稱定稿」；補裁 1 | 功能 | 同上 | 在三份文件找「雲端上限」「每月上限」 | 不再當作這個功能的名稱使用；只允許出現在「（過渡：程式尚未改時）」段或明確標示為「現行程式訊息」處 | 手動：verifier 搜尋並逐處判斷 |

## User Story 3 — docs/CLOUD.md 新增「雲端預算：帳戶擁有者自己設（abf 只教）」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 作 4 | 功能 | 改寫完成的 `docs/CLOUD.md` | 找新增的節標題 | 有「## 雲端預算：帳戶擁有者自己設（abf 只教）」節，並寫明誰設：AWS 帳號／Google Cloud 帳單帳戶／Azure 訂閱的擁有者（含「帳戶擁有者」），在雲端後台設 | 自動：`platform/tests/test_cost_docs_spec.py::test_cloud_doc_teaches_cloud_budget_and_never_reads_it` |
| TC-034 | 作 4；原話「4 件全好」（3）雲端預算由帳戶擁有者在雲端後台設、abf 只教 | 功能 | 同上 | 讀該節 | 含「abf 只教」「不讀雲端預算」；寫明不給 abf 的金鑰任何帳單讀取權限；`budgets:ViewBudget` 若出現，只出現在「不需要」的句子 | 自動：同上測試 |
| TC-035 | 作 4；補裁 4 (c) | 功能 | 同上 | 讀該節 AWS 小段 | 只寫後台選單路徑名稱：「Billing and Cost Management → Budgets」，並到「Cost allocation tags」啟用 `abf-user`／`abf-run` | 自動：同上測試（含「Cost allocation tags」「Budgets」）＋補強 (c)（「Billing and Cost Management」） |
| TC-036 | 作 4；補裁 4 (c) | 功能 | 同上 | 讀該節 Google 小段 | 路徑名稱「Billing → Budgets & alerts」，帳單報表按標籤篩選 | 自動：釘字測試（補強 (c) 的「Budgets & alerts」） |
| TC-037 | 作 4；補裁 4 (c) | 功能 | 同上 | 讀該節 Azure 小段 | 路徑名稱「Cost Management → Budgets」，開 tag inheritance | 自動：釘字測試（補強 (c) 的「Cost Management」） |
| TC-038 | 作 4 | 功能 | 同上 | 讀該節的限制說明 | 寫明三件事：雲端預算只通知、不擋；帳單資料延遲約 8～24 小時；AWS 標籤貼上後要啟用為 cost allocation tag，最多再等約一天才有資料 | 手動：verifier 讀 CLOUD.md（計畫 A 組沒有斷言這三句） |
| TC-039 | 作 4；補裁 4 (d) | 功能 | 同上 | 只在「雲端預算」節範圍內找 `http://`、`https://`、Seqera 網域 | 都不存在（既有價目表一節的 `https://` 來源欄不在檢查範圍） | 自動：釘字測試（補強 (d)；`platform/tests/test_scope.py` 另禁 Seqera 網域） |
| TC-040 | 作 4 | 功能 | 同上 | 讀該節 | 該節內不含 "NT$"、「新台幣」「匯率」，不含任何台幣金額 | 自動：`test_cloud_cost.py::test_the_cloud_document_says_what_it_must`（整份文件層級；該節沒有例外條款） |

## User Story 4 — docs/PLATFORM.md：費用卡片、保存期限表、AWS／Azure 資源標籤（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | 作 6；原話「雲端上限不該由管理者設」（PLATFORM.md 第 776 行） | 功能 | 改寫完成的 `docs/PLATFORM.md` | 讀第 776 行（Cloud 卡片） | 寫成：Cloud 卡片顯示本人自設的每月費用提醒額度（美元），未設顯示「未設定」並可在此頁設定；本頁顯示與設定的是同一個值；帶統一狀態註記（程式尚未改前頁面仍只讀） | 手動：verifier 讀該行 |
| TC-042 | 作 6；原話（同上） | 功能 | 同上 | 在 PLATFORM.md 全文找「The page cannot change it」「the administrator set」「set only by the administrator」 | 三串都不存在 | 自動：`platform/tests/test_cost_docs_spec.py::test_platform_cloud_cap_lines_are_user_set` |
| TC-043 | 作 6 | 功能 | 同上 | 在 PLATFORM.md 找「每月費用提醒額度」與統一狀態註記 | 兩者都存在（註記全文與 CLOUD.md 相同，PLATFORM.md 內放一次） | 自動：同上測試 |
| TC-044 | 作 6 | 功能 | 同上 | 讀第 889 行保存期限表 `cloud_caps` 那一列 | 列文字為「本人的每月費用提醒額度（美元），由本人在網頁設定；現行由管理者於終端機（`abf-platform user add --cloud-cap-usd`、`abf-platform user cloud-cap`）寫入，將由使用者網頁取代（實作在 cost-reminder-quota 計畫）」；含「將由使用者網頁取代」 | 自動：同上測試（斷言該列含「將由使用者網頁取代」） |
| TC-045 | 作 6 | 功能 | 同上 | 讀同一列的存放處與保存期限欄 | 存放處仍是 `tokens.db`（`cloud_caps`），表沒有改；保存期限欄為「無自動刪除；只有本人能改」並附狀態註記；只改規格、不改表 | 手動：verifier 讀該列 |
| TC-046 | 作 6；裁 3 | 功能 | 同上 | 讀「The cost page」節開頭 | 開頭加一行「本節描述現行頁面；版面將依 DESIGN.md 第 11 項改版（費用頁計畫）。」；節內其餘文字（含第 778、782 行）不變 | 手動：verifier 讀 `git diff` |
| TC-047 | 作 6；原話「4 件全好」（4）AWS／Azure 補資源標籤、標籤含帳號名 | 功能 | 同上 | 讀 AWS 設定表 | 新增一列 `process.resourceLabels`（或 AWS 對應鍵），內容含 `abf-user=<帳號名>` 與 `abf-run=<run 名>` | 自動：`platform/tests/test_cost_docs_spec.py::test_aws_azure_sections_have_labels_and_pending_measurement` |
| TC-048 | 作 6 | 功能 | 同上 | 讀 AWS 該列後的註記 | 含三句：帳號名會出現在雲端帳單上（隱私，須含「帳單」）；不放帳號名就無法按人分帳；標籤是否由 Batch 帶到底下的 EC2 實例「待實測」，且標籤貼上後要在 AWS 啟用為 cost allocation tag 才能依標籤分帳 | 自動：同上測試（斷言 AWS 節含「待實測」與「帳單」） |
| TC-049 | 作 6；裁 4；原話「4 件全好」（4） | 功能 | 同上 | 讀 Azure 設定表 | 新增一列標籤 `abf-user=<帳號名>`；不含 `abf-run=`（只放不隨每次 run 改變的標籤） | 自動：同上測試（Azure 節含 `abf-user=`、不含 `abf-run=`） |
| TC-050 | 作 6 | 功能 | 同上 | 讀 Azure 該列後的註記 | 含隱私註記（帳號名會出現在帳單上，含「帳單」）；「是否帶到實際運算資源：待實測」，並說明本平台用既有 pool、`azure.batch.allowPoolCreation` 為 false、標籤可能根本不套用 | 自動：同上測試（斷言 Azure 節含「待實測」與「帳單」） |
| TC-051 | 作 6 | 功能 | 同上 | 在 AWS 節與 Azure 節（含新增兩列）找 `NT\$`、`USD`、`US\$`、`TWD`、12 位連續數字 | 都不存在；兩節既有必含字串（`process.executor`、`azure.batch.allowPoolCreation`、「由 AWS 向實驗室的 AWS 帳號收費」等）全部保留 | 自動：`platform/tests/test_aws_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements`、`platform/tests/test_azure_launch.py::test_platform_md_documents_azure_launch` |

## User Story 5 — 不在範圍：只改文件、只動指定位置（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-052 | 「不做」第 1 條；範圍；完成標準 | 不在範圍 | 實作完成的分支 | `git diff --stat <base>...HEAD`（含未提交） | 只含四個檔：`DESIGN.md`、`docs/CLOUD.md`、`docs/PLATFORM.md`、`platform/tests/test_cost_docs_spec.py`；沒有 `platform/abf_platform/`、`platform/abf_station/` 程式，沒有既有測試檔、`__golden__/`、`docs/TESTING.md`、`docs/OPERATIONS.md`、onboarding 文件、`specs/`、`.github/` 的改動 | 手動：verifier 驗收時比對 diff |
| TC-053 | 範圍（DESIGN.md） | 不在範圍 | 同上 | 看 `DESIGN.md` 的 diff | 只動第 11、12 項；「## 用字」節、上傳段、維護者原話表第 19～25 列一字不動 | 手動：verifier 比對 diff |
| TC-054 | 補裁 2 | 不在範圍 | 同上 | 看 `DESIGN.md` 第 34 行（Masthead） | 一字不動，仍有 "cloud NT$ used / cap"；已知殘留，須由 developer-agent 記在 ledger（留給費用頁實作片），不算失敗 | 手動：verifier 比對 diff 與 ledger |
| TC-055 | 裁 3；範圍（PLATFORM.md） | 不在範圍 | 同上 | 看 `docs/PLATFORM.md` 的 diff | 第 110～111 行（CLI 範例）、第 324 行（Google `process.resourceLabels`）、第 778／782 行（現行費用頁描述）都不在 diff 內 | 手動：verifier 比對 diff |
| TC-056 | 「不做」：本機運算、雲端預算讀取 | 不在範圍 | 同上 | 讀三份文件新增的文字 | 沒有把「本機運算」（issue #367）寫成已提供的功能；沒有把「abf 讀取雲端預算」或「給金鑰帳單權限」寫成作法（只寫「不讀」） | 手動：verifier 讀 diff |

## User Story 6 — 既有測試保持綠，新增釘字測試成立（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-057 | B 組 | 功能 | 改寫完成 | 跑 `platform/tests/test_cloud_cost.py::test_the_cloud_document_says_what_it_must` | 通過；CLOUD.md 仍含「只含運算」「約」「同一個 pipeline」「最近一次成功」「user add」「--cloud-cap-usd」「user cloud-cap」「不會自動停止正在跑的雲端工作」「只會擋下新的送出」「台幣」「帳單預算」「cloud_rates.json」「source」「read_on」「https://」「YYYY-MM-DD」「太平洋時間」「台北時間」「第一次」「擋不住」 | 自動：該測試 |
| TC-058 | B 組 | 功能 | 同上 | 跑 `test_cloud_cost.py::test_cloud_doc_does_not_claim_the_monthly_cap_works_while_the_price_list_is_empty` | 通過；CLOUD.md 仍含「要等價目表填入後才會生效」 | 自動：該測試 |
| TC-059 | B 組 | 功能 | 同上 | 跑 `platform/tests/test_cloud_wire.py` | 全部通過（程式拒絕訊息沒改）；新文字沒有出現「還沒有費用預估與上限」「接線之前確認畫面仍寫」於 AWS 節以外 | 自動：該檔 |
| TC-060 | B 組 | 功能 | 同上 | 跑 `platform/tests/test_aws_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements` | 通過 | 自動：該測試 |
| TC-061 | B 組 | 功能 | 同上 | 跑 `platform/tests/test_azure_launch.py::test_platform_md_documents_azure_launch` | 通過 | 自動：該測試 |
| TC-062 | B 組 | 功能 | 同上 | 跑 `platform/tests/test_gcb_launch.py` | 通過（Google `resourceLabels` 說明沒動） | 自動：該檔 |
| TC-063 | B 組 | 功能 | 同上 | 跑 `platform/tests/test_scope.py` | 通過；PLATFORM.md 沒有 `/home`、`/work`、`/scratch`、`/staging`、`/lustre/<name>/` 路徑，沒有 `cloud.seqera.io`、`api.cloud.seqera.io`、`tower.nf` | 自動：該檔 |
| TC-064 | B 組 | 功能 | 同上 | 跑 `test_web_guided_launch_2b.py::test_h11_design_has_the_word_list` | 通過（「## 用字」節沒動） | 自動：該測試 |
| TC-065 | B 組 | 功能 | 同上 | 跑 `test_web_upload.py::test_tc101_design_md_upload_data_paragraph` | 通過（上傳段沒動） | 自動：該測試 |
| TC-066 | B 組；原話表（DESIGN.md 第 19～25 列） | 功能 | 同上 | 跑 `bash tests/charter_v4_workflow_test.sh` | 釘維護者原話表的檢查全過（該檔的 TC-040～044 是它自己的編號，與本表無關）；已知環境紅 `test_tc047_tc051_other_docs_untouched` 視同綠 | 自動：該檔 |
| TC-067 | B 組最後一條 | 例外 | 同上 | 看 ledger 內 `git grep -n "Reconciled\|cloud cap\|cloud-cap\|Personal\|管理者" origin/v3 -- platform/tests tests` 與 `git grep -n "請找管理者調整上限" origin/v3 -- platform/tests` 的結果 | 結果已列入 ledger；任何不在計畫 B 組清單、卻釘到被改字串的測試，列為「須同批處理」並回報 developer-agent，執行者沒有自己改測試檔 | 手動：verifier 讀 ledger.md 與 diff |
| TC-068 | 失敗先行測試 A 組 | 功能 | 改寫完成 | 讀 `platform/tests/test_cost_docs_spec.py` 並執行 | 新增檔（base 上不存在）；只讀文件字串、不連網；含計畫 A 組第 1～6 條的六個測試（名稱如計畫），全部綠 | 自動：`platform/tests/test_cost_docs_spec.py` |
| TC-069 | A 組第 7 條（反向證明） | 功能 | 同上 | 把 CLOUD.md 固定句「未設定每月費用提醒額度。實際費用以雲端帳單為準。」改一個字；另一次把 PLATFORM.md 的「待實測」刪掉 | 前者使 `test_cloud_doc_quota_is_user_set_and_unset_does_not_block` 紅，後者使 `test_aws_azure_sections_have_labels_and_pending_measurement` 紅（verifier 在暫存副本上試，試完還原，不留改動） | 手動：verifier 驗收時在暫存副本上做 |
| TC-070 | 補裁 4 | 功能 | 同上 | 讀釘字測試 | 補強斷言 (a)～(f) 都存在：三份文件不含「每人每月上限」；CLOUD.md 含統一狀態註記全文；含「Billing and Cost Management」「Budgets & alerts」「Cost Management」；「雲端預算」節內無 `http://`／`https://`；「0」與「1,000,000」同一行；DESIGN.md Cost 行含 "environment / usage / status / scope" 與 "Action-needed" | 自動：`platform/tests/test_cost_docs_spec.py` |
| TC-071 | 「失敗先行測試」：現在必紅 | 功能 | base 分支的四份文件（釘字測試檔放進去） | 在暫存副本上，用 base 的文件跑釘字測試 | 計畫 A 組的測試在 base 文件上為紅，改完才轉綠（證明測試能失敗） | 手動：verifier 在暫存副本上跑 |

## 憲法與安全網

本任務只改文件，但文件在憲法第 3、8 條的檢查範圍內。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-072 | 第 3 條（不寫死個人或叢集路徑） | 功能 | 改寫完成 | 跑 `bash tests/no_hardcoded_paths.sh`；並在新增文字找 `/home`、`/work`、`/scratch`、`/lustre` | 通過；新增文字沒有個人／叢集路徑（雲端後台只寫選單路徑名稱，這不是檔案路徑） | 自動：`tests/no_hardcoded_paths.sh`（與 TC-063） |
| TC-073 | 第 8 條（先量測再宣稱） | 功能 | 同上 | 讀 AWS／Azure 新增標籤列的說明 | 「標籤是否帶到 EC2／實際運算資源」只寫「待實測」，沒有被寫成已證實或已不可能；不宣稱 AWS／Azure 現在已經貼上標籤（程式未改） | 手動：verifier 讀 diff |
