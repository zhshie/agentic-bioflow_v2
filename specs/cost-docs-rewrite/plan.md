---
id: cost-docs-rewrite
title: 費用規格改寫（純文件）：費用頁以運算環境為單位、每月費用提醒額度由使用者自設、雲端預算只教不讀、AWS／Azure 補資源標籤
tier: C
kinds: docs
risk: M
lane: L61-cost-docs-rewrite
branch: docs/cost-docs-rewrite
base: origin/v3@b3ec5b32
source: 2026-11-04-frontend-decisions.md 任務 7-12～7-14；2026-11-05-cloud-budget-research.md（⑥ 節）；維護者 11-05／11-06 回覆「4 件全好」
---

# cost-docs-rewrite

> 只改文件（＋一個新增的文件釘字測試檔）。不改任何執行期程式。這份是規格：後續三份計畫（費用頁、cost-reminder-quota、雲端標籤）都以它為準，所以每個字串在「作法」裡寫死。

## 目標
把 `DESIGN.md`、`docs/CLOUD.md`、`docs/PLATFORM.md` 裡仍寫「管理者設雲端上限、網頁只讀、費用頁分國網／雲端兩區、含 NT$ 與 Reconciled」的段落，改成維護者 11-05 定下的新規格。對使用者的意義：往後三份實作計畫有同一份、可逐字驗收的規格可依；文件不再說「管理者替你設上限」。

## 維護者原話（verifier 出題用）
- 「國網／雲端二分法很奇怪」（11-05，費用頁）→ 案例：DESIGN.md 第 11 項不再有「NCHC SU／Cloud used」兩區卡片、不再以國網／雲端分區。
- 「雲端上限不該由管理者設，是使用者自己的事」（11-05）→ 案例：CLOUD.md、PLATFORM.md 第 776／889 行不再寫「只有管理者」「管理者替你設」「網頁不能改」。
- 他回「4 件全好」，四件內容：（1）額度由使用者本人設；（2）未設不擋雲端送出；（3）雲端預算由帳戶擁有者在雲端後台設、abf 只教；（4）AWS／Azure 補資源標籤、標籤含帳號名。→ 四件各至少一條案例（見「失敗先行測試」）。
- 名稱定稿：「每月費用提醒額度」。→ 案例：三份文件裡不再有「每人每月上限」「雲端上限」作為這個功能的名稱（現行程式訊息除外，見裁決 1）。
- 費用頁定案草稿 https://claude.ai/artifact/DguBi1tA1vpwmj1B7zd1GY（Version 6），他回「好的可以」。→ verifier 以此為版面依據；DESIGN.md 第 11 項的字要與草稿一致（每環境一列可展開、單位依環境、不加總）。
- 7-12：不要用「個人 · 存取權杖」→ 案例：DESIGN.md 第 12 項不再有「Personal」分組，「存取權杖」單獨一項。
- 11-05 費用頁 v3「不好」→ 不得回到 v3 的版面描述（國網／雲端兩區卡片）。

## 範圍：檔案（只准改這些）
- `DESIGN.md`：只改第 11 項（`**Cost**` 那行，origin/v3 約第 78 行）與第 12 項（`**Settings**` 那行，約第 79 行）。「## 用字」節（約第 82 行起）與上傳段一字不動（`test_h11_design_has_the_word_list`、`test_tc101_design_md_upload_data_paragraph` 釘住）；維護者原話表第 19～25 列一字不動（`tests/charter_v4_workflow_test.sh` TC-040～044 釘住）。
- `docs/CLOUD.md`：「一句話」、第 19 行的「請管理者……」、「上限怎麼設」整節、「拒絕的時候看到什麼」、「目前的限制」中關於管理者／台幣的條目所需最小改動，新增「雲端預算：帳戶擁有者自己設」節與「確認畫面」的「未設定」第 4 種寫法。
- `docs/PLATFORM.md`：第 776 行（Cloud cap 卡片）、第 889 行（保存期限表 `cloud_caps` 列）、「The cost page」節開頭加一行狀態註記；Google 以外的 AWS 設定表（約第 376～389 行）與 Azure 設定表（約第 498～514 行）各加標籤一列與隱私／待實測註記。
- `platform/tests/test_cost_docs_spec.py`（**新增檔**，只讀文件字串；見「失敗先行測試」）。
- **不准碰**：所有程式（`platform/abf_platform/`、`platform/abf_station/`）、既有測試檔（`test_cloud_cost.py`、`test_cloud_wire.py`、`test_aws_launch.py`、`test_azure_launch.py`、`test_gcb_launch.py`、`test_scope.py`、`test_onboarding_doc.py`）、`platform/tests/__golden__/`、`docs/TESTING.md`（第 670～682 行手動步驟）、`docs/OPERATIONS.md`、onboarding 文件、`specs/`、`.github/`。PLATFORM.md 第 110～111 行（CLI 範例）、第 324 行（Google `process.resourceLabels`）、第 778／782 行（現行費用頁描述）不動（裁決 3）。

## 作法
**統一的狀態註記（固定字串，CLOUD.md 與 PLATFORM.md 各放一次）**：「規格已定；程式尚未改（見 cost-reminder-quota 計畫）。在那之前，終端機指令仍是唯一寫入口，未設額度仍擋雲端送出。」目的：規格已改、程式還沒改的這段期間，文件不說假話。

**1. DESIGN.md 第 11 項（費用頁，`#cost`）改寫成**（英文，與該檔現有語言一致；下列為必含片語）：
- 以運算環境為單位，**每個環境一列（one row per compute environment）**，可展開（expand）看該環境底下的分析；只有一個環境時就一列。
- 單位依環境：國網（Slurm）環境寫 SU，雲端環境寫美元；**不加總、不換算（never summed, never converted）**。
- 新增分析頁費用列：欄位順序「環境／用量／狀態／範圍（environment / usage / status / scope）」，對應 Seqera 執行頁 Metrics 分頁。
- 刪除：「cards NCHC SU / Cloud used / cap / remaining」「Reconciled」「Estimate, bill pending」的狀態詞、國網／雲端分區；DESIGN.md 本無「NT$」字樣（研究交接記的 NT$ 實在 PLATFORM.md 第 782 行），驗收只確認它不出現。
- 保留：Action-needed 通知概念，但條件改為「這次送出會超過本人設的每月費用提醒額度」（用 Slurm 環境／等下月重置兩個出路的句子可留）。
- 版面依據 = 上述 artifact Version 6；不得自己加卡片。

**2. DESIGN.md 第 12 項（Settings）**：把「Personal (step-by-step mode, development mode)」分組拆開：**「存取權杖（Access tokens）」單獨一項**；逐步模式、開發模式另列，不要再以「Personal」為組名。「Operator panel and Roles as dashed "coming later"」保持。「每月費用提醒額度」列入設定頁項目（由使用者本人設，實作見 cost-reminder-quota）。

**3. docs/CLOUD.md「上限設定」整節改寫**（段名改為「## 每月費用提醒額度（你自己設）」）。必含固定字串：
- 名稱「每月費用提醒額度」；由使用者本人在網頁設，單位美元，範圍 0～1,000,000（沿用現行驗證範圍，只改誰設）。
- 未設時**不擋**雲端送出；送出確認頁第 4 種寫法固定為：「未設定每月費用提醒額度。實際費用以雲端帳單為準。」（併入「確認畫面長什麼樣」，原有三種寫法保持；該節的「只有三種寫法」改成「四種」）。
- 已設且「已用＋預估 > 額度」仍拒絕新的送出（它是本人自己訂的提醒線，不是雲端的預算；本人可自己調高）。拒絕訊息範例改為：「……會超過。請到網頁調整每月費用提醒額度，或下個月再送出」。
- 本節說明名稱的意思：「提醒」＝本人給自己的線；平台算的是估算（只含運算）；真正的保護在雲端預算（下一節）。
- 沿用不動：「只含運算」「約」「同一個 pipeline」「最近一次成功」「第一次」「擋不住」整段（第 19 行僅把「請管理者替第一位使用者把上限設小一點」改成「請本人把額度設小一點，例如 5 美元」）；「不會自動停止正在跑的雲端工作」「只會擋下新的送出」；價目表一節與「要等價目表填入後才會生效」；「太平洋時間」「台北時間」；第 45 行「台幣」「帳單預算」那條（雲端預算只是 Google 的事後提醒、平台沒有台幣）。
- 「目前的限制」中「管理者自己打的 `abf-launch` 不查上限」那條保留，把「上限」改稱「額度」；「按送出前管理者調低」條改為「按送出前本人調低額度」。

**4. docs/CLOUD.md 新增「## 雲端預算：帳戶擁有者自己設（abf 只教）」**：
- 誰設：雲端帳戶（AWS 帳號／Google Cloud 帳單帳戶／Azure 訂閱）的**擁有者**，在雲端後台設；abf 只教，**不讀雲端預算，也不給 abf 的金鑰任何帳單讀取權限**（不要 `budgets:ViewBudget`、不要帳單帳戶角色）。
- 教學步驟寫在本節（本文件即「教學步驟位置」；確認頁與 `/usage` 之後只指向這一節）：三雲各一小段，**只寫後台選單路徑名稱**（AWS：Billing and Cost Management → Budgets，並到 Cost allocation tags 啟用 `abf-user`／`abf-run`；Google：Billing → Budgets & alerts，帳單報表按標籤篩選；Azure：Cost Management → Budgets，開 tag inheritance）。**不貼網址**，除非執行者逐一開啟確認有效；也不貼 Seqera 網域（`test_scope.py` 禁）。
- 必講的限制：雲端預算只通知、不擋；帳單資料延遲約 8～24 小時；AWS 標籤貼上後要啟用為 cost allocation tag，最多再等約一天才有資料。
- 不得出現：新台幣、匯率、NT$ 金額（`test_the_cloud_document_says_what_it_must` 禁；唯一例外是第 45 行既有的「台幣」「帳單預算」那條）。

**5. 過渡段（保留兩條指令名，避免改既有測試）**：CLOUD.md 保留一個明確標示的小段「（過渡：程式尚未改時）」，內含狀態註記與兩條現行指令 `abf-platform user add <名字> --lab <實驗室> --cloud-cap-usd 20`、`abf-platform user cloud-cap <名字> 25`，並註明「這是平台主機上的舊寫入口，將由使用者網頁取代」。理由：`test_the_cloud_document_says_what_it_must` 要求 CLOUD.md 含「user add」「--cloud-cap-usd」「user cloud-cap」。

**6. docs/PLATFORM.md**：
- 第 776 行：改為「Cloud 卡片顯示本人自設的每月費用提醒額度（美元），未設顯示『未設定』並可在此頁設定；本頁顯示與設定的是同一個值」＋狀態註記（程式尚未改前，頁面仍只讀）。不再出現「the administrator set」「The page cannot change it」。
- 第 889 行：列文字改為「本人的每月費用提醒額度（美元），由本人在網頁設定；現行由管理者於終端機（`abf-platform user add --cloud-cap-usd`、`abf-platform user cloud-cap`）寫入，將由使用者網頁取代（實作在 cost-reminder-quota 計畫）」；存放處 `tokens.db`（`cloud_caps`）不變；保存期限欄改為「無自動刪除；只有本人能改」並附狀態註記。**標明 `cloud_caps` 的寫入入口將由使用者網頁取代，只改規格、不改表。**
- 「The cost page」節開頭加一行：「本節描述現行頁面；版面將依 DESIGN.md 第 11 項改版（費用頁計畫）。」第 778、782 行不動。
- AWS 設定表（約第 376～389 行）加一列 `process.resourceLabels`（或 AWS 對應鍵，執行者先讀該表既有鍵名風格）：內容 `abf-user=<帳號名>`、`abf-run=<run 名>`；其後註記三句——「帳號名會出現在雲端帳單上（隱私）」「不放帳號名就無法按人分帳」「標籤是否由 Batch 帶到底下的 EC2 實例：**待實測**；標籤貼上後要在 AWS 啟用為 cost allocation tag 才能在帳單依標籤分帳」。
- Azure 設定表（約第 498～514 行）加一列：標籤 `abf-user=<帳號名>`（**只放不隨每次 run 改變的標籤**；`abf-run` 先不放，待實測確認不會每次開新 pool 再加）＋同樣的隱私註記與「是否帶到實際運算資源：**待實測**（本平台用既有 pool，`azure.batch.allowPoolCreation` 為 false，標籤可能根本不套用）」。
- 這兩列的文字**不得**含 `NT$`、`USD`、`US$`、`TWD`、12 位連續數字（`test_aws_launch.py`／`test_azure_launch.py` 掃整個 AWS／Azure 節）；也不得動兩節既有必含字串（見「失敗先行測試」B 組）。
- Google 節（第 324 行）不改；它已經是「使用者標籤＋`abf-run=<run 名>`」，只在新增標籤列的說明中指出 AWS／Azure 比照。

**7. 順序**：先寫測試（紅）→ 改 DESIGN.md → CLOUD.md → PLATFORM.md → 跑 A、B 兩組確認綠。

## 失敗先行測試
**A 組：新增 `platform/tests/test_cost_docs_spec.py`（現在必紅，改完轉綠）**——用 `git show`／讀檔取文件文字，不連網：
1. `test_design_cost_item_is_per_environment_rows`：DESIGN.md `**Cost**` 那行含 "per compute environment"、"never summed"、"Metrics"，且**不含** "Reconciled"、"NT$"、"NCHC SU / Cloud used"。
2. `test_design_settings_access_token_is_its_own_item`：`**Settings**` 那行含 "Access token"（或「存取權杖」，依該檔語言），且不含 "Personal (" 。
3. `test_cloud_doc_quota_is_user_set_and_unset_does_not_block`：CLOUD.md 含「每月費用提醒額度」與固定句「未設定每月費用提醒額度。實際費用以雲端帳單為準。」，且**不含**「只有管理者」「請找管理者調整上限」「請管理者替第一位使用者」。
4. `test_cloud_doc_teaches_cloud_budget_and_never_reads_it`：CLOUD.md 含「帳戶擁有者」「abf 只教」「不讀雲端預算」「Cost allocation tags」「Budgets」；不含 `budgets:ViewBudget` 作為「需要的權限」的寫法（只准出現在「不需要」的句子）。
5. `test_platform_cloud_cap_lines_are_user_set`：PLATFORM.md 不含「The page cannot change it」「the administrator set」「set only by the administrator」；含「每月費用提醒額度」與統一狀態註記；第 889 行那列含「將由使用者網頁取代」。
6. `test_aws_azure_sections_have_labels_and_pending_measurement`：PLATFORM.md AWS 節與 Azure 節各含 `abf-user=` 與「待實測」與「帳單」（隱私註記）；AWS 節含 `abf-run=`；Azure 節**不含** `abf-run=`（裁決 4）。
7. 反向證明（mutation）：把 CLOUD.md 固定句改一個字、或把 PLATFORM.md 的「待實測」刪掉，對應測試必紅。

**B 組：既有測試必須保持綠（不改測試檔；先 `git grep` 再改，任何一條轉紅就是文案動錯了）**：
- `platform/tests/test_cloud_cost.py::test_the_cloud_document_says_what_it_must`：CLOUD.md 保留「只含運算」「約」「同一個 pipeline」「最近一次成功」「user add」「--cloud-cap-usd」「user cloud-cap」「不會自動停止正在跑的雲端工作」「只會擋下新的送出」「台幣」「帳單預算」「cloud_rates.json」「source」「read_on」「https://」「YYYY-MM-DD」「太平洋時間」「台北時間」「第一次」「擋不住」；不含「NT$」、台幣金額、「新台幣」、「匯率」、exchange rate。
- `test_cloud_cost.py::test_cloud_doc_does_not_claim_the_monthly_cap_works_while_the_price_list_is_empty`：CLOUD.md 保留「要等價目表填入後才會生效」；`docs/TESTING.md` 的英文「only takes effect once the price list is filled in」不動。
- `platform/tests/test_cloud_wire.py`：第 130、153 行釘程式拒絕訊息（程式沒改，維持）；`test_no_file_still_says_there_is_no_estimate_and_cap` 禁止「還沒有費用預估與上限」「接線之前確認畫面仍寫」出現在 AWS 節以外的地方——新文字不得用這兩串。
- `platform/tests/test_aws_launch.py::test_docs_describe_the_launch_the_billing_sentence_and_the_requirements`（約第 1234 行）：AWS 節保留 `process.executor`、`process.queue`、`aws.region`、`workDir`、`process.resourceLimits`、"Java 17"、"Nextflow"、"aws CLI"、"storage_root"、"s3://"、「由 AWS 向實驗室的 AWS 帳號收費」、"SIGTERM"、"AWS Console"、"resume"、"per-task"、"head process"、"AMI"、"credential"、句子「平台(目前)還沒有費用預估與上限」；節內不得匹配 `NT\$|USD|US\$|TWD` 或 `\b\d{12}\b`。
- `platform/tests/test_azure_launch.py::test_platform_md_documents_azure_launch`（約第 1211 行）：Azure 節保留 `process.executor`、`process.queue`、`workDir`、`azure.batch.accountName`、`azure.batch.location`、`azure.storage.accountName`、`azure.batch.allowPoolCreation`、`azure.batch.autoPoolMode`、`process.resourceLimits`、"Java 17"、"Nextflow"、"az CLI"、"storage_root"、"az://"、"dockerCompatible"、"task slots"、"container"、"SIGTERM"、"Azure Portal"、"resume"、"per-task"、"head process"、「由 Azure 向實驗室的 Azure 帳號收費」、"ABF_STATION_AZURE_CREDENTIALS"、句子「本系統目前沒有費用預估與上限」；同樣不得匹配上面的金額／12 位數規則。
- `platform/tests/test_gcb_launch.py`（約第 551、1148 行）：Google `resourceLabels` 說明；PLATFORM.md 第 324 行不動。
- `platform/tests/test_scope.py`：PLATFORM.md 不含 `/home|/work|/scratch|/staging|/lustre/<name>/` 路徑，不含 `cloud.seqera.io`、`api.cloud.seqera.io`、`tower.nf`。
- `test_web_guided_launch_2b.py::test_h11_design_has_the_word_list`、`test_web_upload.py::test_tc101_design_md_upload_data_paragraph`、`tests/charter_v4_workflow_test.sh`（TC-040～044 釘維護者原話表）：DESIGN.md 該三處不動。
- 先掃一次其餘釘字：`git grep -n "Reconciled\|cloud cap\|cloud-cap\|Personal\|管理者" origin/v3 -- platform/tests tests` 與 `git grep -n "請找管理者調整上限" origin/v3 -- platform/tests`，結果列進 ledger；不在上面清單、卻釘到被改字串的測試，列為「須同批處理」並回報 developer-agent，不要自己改測試檔。

## 完成標準（done when）
- 三份文件的改寫逐條符合「作法」1～6；A 組 6 條綠、B 組全綠（只剩「已知環境紅」`test_tc047_tc051_other_docs_untouched` 視同綠）。
- `git diff --stat` 只含：`DESIGN.md`、`docs/CLOUD.md`、`docs/PLATFORM.md`、`platform/tests/test_cost_docs_spec.py`。DESIGN.md 的 diff 只在第 11、12 項；PLATFORM.md 的 diff 不含第 110、324、778、782 行。證據貼進 ledger.md。
- 文件不說假話：凡規格已改而程式未改之處，都帶統一狀態註記。
- 風險 M 的「網頁畫面截圖」：本任務不改網頁畫面，**不需截圖**；verifier 以 diff 與文字比對閱卷。
- 版面比對：DESIGN.md 第 11 項與 artifact Version 6 一致（verifier 打開連結對照）。

## 環境事實
- repo：`C:\Users\marvi\Desktop\agentic-bioflow\agentic-bioflow_v2`，base `origin/v3@b3ec5b32`（2026-11-06 查）。`PITFALLS.md` 在 `docs/PITFALLS.md`；沒有 `docs/solutions/`。
- 現行程式（本任務**不改**）：`tokens.db` 表 `cloud_caps(user_id, cap_usd, set_at)`；`abf-platform user add --cloud-cap-usd`、`abf-platform user cloud-cap` 是唯一寫入口；未設額度時程式**拒絕**雲端送出；拒絕訊息仍寫「請找管理者調整上限」（`test_cloud_wire.py` 130、153 行釘住）。這些都由 cost-reminder-quota 計畫改。
- Google Batch 已在 `process.resourceLabels` 寫「使用者標籤＋`abf-run=<run name>`」（PLATFORM.md 約第 324 行）；AWS、Azure 目前沒有標籤也沒有估算。
- 雲端預算性質（研究交接 ⑥ 前文）：只通知不擋；帳單資料延遲約 8～24 小時；AWS 標籤要啟用為 cost allocation tag（貼上後最多約 24 小時出現、啟用再最多約 24 小時）；Azure 標籤在 Nextflow 會貼到自動建立的 pool，標籤組合變動可能每次開新 pool，但本平台用既有 pool（`allowPoolCreation` false）所以影響要實測。
- Seqera 對照：估算費用在執行頁 Metrics 分頁、只供參考；標籤＋叫使用者去雲端商設預算；沒有跨分析費用頁。維護者 11-03 指示：介面多參考 Seqera、Galaxy，不要自己腦補。
- PITFALLS 已查：只有一條相符——`docs/PITFALLS.md` 約第 2483～2488 行（011a 版面被維護者否決的條目，症狀：「版面我完全不滿意，請你直接參考 Seqera 以及 Galaxy 的網頁」；檢查：none automated，設計類任務的計畫必須帶從 PRODUCT.md／DESIGN.md 抄來的專長守則段）。因此本計畫的版面一律以 Seqera 對照＋artifact Version 6 為準，專長守則段由 `build-dev-plans.py` 貼上，執行者不得自行更動版面。其餘模組（CLOUD.md、PLATFORM.md、`cloud_caps`、`resourceLabels`）無相符項。

## 不做
- 不寫任何程式；不改既有測試檔、golden 檔（`__golden__/cli_help_user_add.txt`、`cli_tree.txt`）。
- 不排本機運算（issue #367，維護者說先不做）。
- 後續片（各自一份計畫，這份不做）：
  1. 費用頁實作（每環境一列、分析頁費用列、移除 NT$／Reconciled；順帶改 PLATFORM.md 第 778、782 行與 `twd_per_su`）。
  2. cost-reminder-quota：使用者網頁設額度、未設不擋、確認頁固定句、拒絕訊息改為「請到網頁調整每月費用提醒額度」、移除或降級 `abf-platform user cloud-cap`／`--cloud-cap-usd`（連動 golden 檔、`test_cloud_cost.py` 548～605、`test_cloud_wire.py` 130／153、`test_onboarding_doc.py` 約 97～103 與 255～307、onboarding 文件、`docs/TESTING.md` 第 670～682 行、`docs/OPERATIONS.md`、PLATFORM.md 第 110～111 行）。
  3. AWS／Azure 資源標籤的程式實作與實測（AWS Batch 標籤是否帶到 EC2、Azure 既有 pool 下標籤是否生效、`abf-run` 是否可加進 Azure）。
- 不做雲端預算讀取（AWS Budgets／Google Budget API）、不給金鑰帳單權限（研究交接 ⑥ 選項 b，已否決）。

## 裁決
1. **過渡段保留兩條指令名**（作法 5）：保持 `test_the_cloud_document_says_what_it_must` 綠，避免本任務動既有測試；等 cost-reminder-quota 移除指令時再一起改該測試。
2. **已設額度且會超過仍擋新的送出**：名稱是「提醒額度」，但現行把關位置（建立確認頁之前）與研究交接 ⑥ 第 99 行「只擋 abf 送出、本人可自己調高」一致；維護者只裁決「未設不擋」，未要求取消把關。若 developer-agent 認為「提醒」應僅顯示、不擋，改作法 3 的第三點並回報。
3. **PLATFORM.md 第 778、782 行不在本任務**：它們描述現行頁面（含 NT$、Reconciled），屬費用頁實作片；本任務只在節首加一行狀態註記。
4. **Azure 標籤只放 `abf-user`**：研究交接指出 Azure 標籤變動可能每次開新 pool，故不放每次 run 都變的 `abf-run`；AWS 兩個都放。皆標「待實測」。
5. **新增一個文件釘字測試檔**：README 要求「失敗先行測試」；純文件任務仍以新增檔釘住新字串，不動既有測試。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
