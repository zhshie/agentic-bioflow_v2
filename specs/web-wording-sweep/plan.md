---
id: web-wording-sweep
title: 網頁中文用字清掃：除 /launch 外，看板、分析頁、設定、費用、完成頁、登入／改密碼／授權／確認頁的中文一律改成正式書面語，並把禁用詞測試擴大到每個頁面與每張中文字串表
tier: B
kinds: ui
lane: L7-web-redesign
base: origin/v3@129ff36（10-29 #263 上傳頁已合併；行號取自 e79a555，開工前重 grep）
source: 維護者 2026-10-27「中文顯示不能口語。」（DESIGN.md:80 另記「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」）；DESIGN.md「用字」一節末段（"Other screens … are not yet swept; that is the backlog item `web-wording-sweep`"）；先前任務 guided-launch-2b 已清 /launch 並建禁用詞測試 platform/tests/test_web_guided_launch_2b.py:17（BANNED）、:563-598
---

# web-wording-sweep

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/web-wording-sweep/plan.md`。**只處理本任務**。
> 與 `feat/web-upload-page`（L17）可能同時在跑：兩邊都動 `web_board.py` STRINGS。本任務**只改既有字串的值，不加不刪鍵**；合併衝突取兩邊聯集。**`platform/abf_platform/web_upload.py` 不在範圍**（見「## 待裁決」第 1 點）。

## 目標
看板（左、中、右欄）、分析頁各階段與各分頁、設定頁、費用頁、完成頁、登入／設定自己密碼（/welcome）／連接器授權／確認頁的繁體中文，全部改成正式書面語（陳述事實或平實請求；無口語、無「你還沒…」句型、無指代不明的「這個」）；英文版不動。禁用詞測試從只看 /launch 擴大到每個頁面與每張中文字串表，之後新增字串違規會當場紅。

## 維護者原話（verifier 出題用）
1. 「中文顯示不能口語。」（2026-10-27）
2. 「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」（2026-10-27，DESIGN.md:80；這兩句已在 /launch 清掉，測試要保證它們在所有頁面都不出現）
3. 維護者看到的違規例：「我的 run」「還沒有 run。」（看板左欄標題與空狀態）——兩句字面都必須在全部頁面的中文版消失。
4. DESIGN.md「用字」第 1-3 條：說狀態，不說「人做了沒做」；點名事物，不用「這個」；一個動作一個動詞（選用／套用／送出／載入）。
5. 「我說過不要口語的AI，但你給使用者的按鈕都是"用24G續跑"，哪有一個固定的按鈕會這樣寫?」（10-23，DESIGN.md:19）——按鈕一律是固定名稱的書面語，不是句子。

## 範圍：檔案
- `platform/abf_platform/web_board.py`（只改 `STRINGS["zh"]` 的**值**與中文字面；不加不刪鍵；不改英文）
- `platform/abf_platform/web.py`（只改中文字面：`_PLAIN["zh"]`、登入頁、設定自己密碼頁、確認頁、授權頁的中文半句；不改路由、不改英文半句、不改雙語並列的格式）
- `platform/abf_platform/web_settings.py`（只改 `STRINGS["zh"]`）
- `platform/abf_platform/web_cost.py`（只改 `STRINGS["zh"]`）
- `platform/abf_platform/web_finished.py`（只改 `STRINGS["zh"]`）
- `platform/tests/test_web_wording_sweep.py`（**新檔**：擴大後的禁用詞測試，見「## 失敗先行測試」）
- `platform/tests/test_web_guided_launch_2b.py`（只限：把 `BANNED` 與 `banned_in` 的定義改成從新檔匯入共用；既有斷言一條都不刪）
- 因字串改了而被逐字釘住、必須同步改期望值的既有測試（只改期望字串，不刪斷言、不放寬；ledger「Existing assertions that changed」逐條列檔:行、改前、改後、依據＝本計畫對照表）：`test_web_board.py`、`test_web_cost.py`、`test_web_finished.py`、`test_web_settings.py`、`test_web_welcome.py`、`test_web_login.py`、`test_web_confirm_plain.py`、`test_web_running.py`、`test_web_results_outputs.py`、`test_web_status_squares_3.py`、`test_web_v2_skeleton.py`、`test_web_actions.py`、`test_web_parity.py`、`test_web_fixes_1.py`、`test_clean_page.py`、`test_cleanup_offer.py`、`test_oauth_consent.py`（實際要改哪幾個，以「改字串後哪些測試紅」為準；不在此清單的檔若也紅，先停下回報）
- `DESIGN.md`（只限「用字」一節：末段 "Other screens … are not yet swept; that is the backlog item `web-wording-sweep`" 改為已全部清掃（web-wording-sweep，10-29）並說明禁用詞由 `test_web_wording_sweep.py` 在每個頁面與每張中文字串表檢查；把本計畫新增的禁用詞補進該節清單）

**不在範圍**：`platform/abf_platform/web_upload.py`（feat/web-upload-page 進行中，見待裁決 1）、`web_launch.py` 與 `web_board.py` 的 `GUIDED`（2b／2d 已清）、`welcome.py`（只產出英文信，給 CLI）、`confirm.py` 等 action 層（見待裁決 2）。

## 作法
### 1. 字串對照表（origin/v3@e79a555 量得；行號為該 commit 的檔內行號，改前先重 grep，行號可能漂移）
原則：「run」（指一次分析）→「分析」；「這個／這次／這個月」→ 點名事物（該次分析／此資料夾／本月）；「你／你的」→「您／您的」（與 /launch 已用的「您名下」一致；能省略主詞就省略）；「什麼都沒有X」→「未X任何內容」；「做不了」「讀不到」「算不出」→ 書面語。專有名詞（管線、運算環境、樣本表、中間檔、續跑、重跑、SU、MultiQC）沿用 DESIGN.md／既有字串，不改。

**web_board.py（STRINGS["zh"]）**

| 行 | 鍵 | 現文 | 改為 |
|---|---|---|---|
| 37 | mine | 我的 run | 我的分析 |
| 37 | none_yet | 還沒有 run。 | 尚無分析紀錄。 |
| 40 | no_analyses | 還沒有分析 | 尚無分析 |
| 42 | this_analysis | 這個分析的對話 | 本分析的對話 |
| 42 | ask_here | 問這個分析 | 詢問本分析 |
| 43 | c_open | 打開確認頁 | 開啟確認頁 |
| 44 | c_content_text | 這個 run 已成功；它的中間檔（work）可以清掉，結果不會被動。 | 該次分析已成功；其中間檔（work）可清理，結果不受影響。 |
| 45 | c_next_text | 打開確認頁，看清楚要刪的資料夾再決定。 | 請開啟確認頁，核對將刪除的資料夾後再決定。 |
| 47 | r_site | 站台沒有回應 | 站台無回應 |
| 41 | row_site | 執行 · 站台沒有回應 | 執行 · 站台無回應 |
| 52 | not_reached | 這個 run 還沒到這個階段。 | 該次分析尚未進行至此階段。 |
| 53 | not_found_title | 找不到這個 run | 找不到該次分析 |
| 53 | not_found_body | 沒有這個 run，或它不是你的。 | 無此分析，或該分析不屬於您。 |
| 57 | quick | 用這個 run 的內容再啟動一次 | 沿用設定重新分析（與 GUIDED 的 g_quick 同名，見待裁決 4） |
| 60 | no_notices | 目前沒有通知 | 目前無通知 |
| 60 | no_failed_tasks | 沒有失敗的任務 | 無失敗任務 |
| 70 | r_none | 什麼都沒有送出。 | 未送出任何內容。 |
| 70 | r_generic | 這件事現在做不了。 | 目前無法執行此操作。 |
| 70 | r_form | 這個表單的記號不對或已失效，什麼都沒有送出。請重新整理頁面再按。 | 表單驗證碼不符或已失效，未送出任何內容。請重新整理頁面後再操作。 |
| 75 | o_failed | 讀不到 | 無法讀取 |
| 75 | o_none | 沒有輸出資料夾紀錄 | 無輸出資料夾紀錄 |
| 76 | o_empty | 這個資料夾是空的 | 此資料夾為空 |

維持不改：`level_action`「待處理」（見待裁決 7）、`row_stopped`／`r_stopped`「已取消」、`state_*`、`count_*`、`stage_*`、`tab_*`、`th_*`、`ty_*`、`dur_*`、`card_*`、`l_*`、`e_*`（已是書面語）。

**web_settings.py（STRINGS["zh"]，約第 19-26 行）**

| 鍵 | 現文 | 改為 |
|---|---|---|
| ce_none／no_ce | 沒有運算環境。 | 尚無運算環境。 |
| key_note | 金鑰只存在你的瀏覽器，不會送到平台。 | 金鑰僅儲存於您的瀏覽器，不會傳送至平台。 |
| token_hint | 在終端機用 abf-platform token new 建立。 | 請於終端機執行 abf-platform token new 建立。 |
| check_cmd | 請用指令確認 | 請以指令確認 |

**web_cost.py（STRINGS["zh"]，約第 21-29 行）**

| 鍵 | 現文 | 改為 |
|---|---|---|
| th_where | 在哪裡跑 | 執行位置 |
| empty | — 這個月還沒有分析 | — 本月尚無分析 |
| bad_month | 月份格式不對，顯示本月。 | 月份格式不符，已顯示本月。 |
| no_reason | 算不出 | 無法計算 |
| unknown_runs | 另有 %d 個分析算不出 | 另有 %d 個分析無法計算 |
| note | …數字是依執行紀錄估算，略低於實際帳單。 | …數字依執行紀錄估算，略低於實際帳單。 |
| usd_note | SU 換美元依 %s 匯率約略換算，不是帳單。 | SU 以 %s 匯率概算為美元，並非帳單金額。 |
| action | 待處理：本月的雲端額度已用完 | 待處理：本月雲端額度已用盡 |

**web_finished.py（STRINGS["zh"]，約第 12-18 行）**

| 鍵 | 現文 | 改為 |
|---|---|---|
| params | 改過的參數 | 已變更的參數 |
| defaults | 全部用預設值 | 全部採預設值 |
| gone_note | 這次送出的內容已不保留。 | 該次送出的內容已不保留。 |
| foreign | 不是從平台送出的分析，沒有來源紀錄。 | 此分析並非經由平台送出，無來源紀錄。 |
| no_multiqc | 這次沒有產生 | 該次未產生 |
| no_files | 沒有檔案 | 無檔案 |

**web.py（行號為 origin/v3 檔內行號）**

| 行 | 位置 | 現文（中文半句） | 改為 |
|---|---|---|---|
| 79 | `_PLAIN["zh"]["run"]` | run 名稱 | 分析名稱 |
| 151 | 登入頁說明 | 請用你的姓名與網頁密碼登入（網頁密碼不是 AI 用的權杖；…或用管理者給你的一次性臨時密碼）。 | 請以您的姓名與網頁密碼登入（網頁密碼不同於 AI 使用的權杖；於平台主機的終端機以 abf-platform user passwd 設定，或使用管理者提供的一次性臨時密碼）。 |
| 240 | 來源不符 | 這個表單不是從本頁送出的，什麼都沒有改。 | 此表單並非由本頁送出，未變更任何內容。 |
| 301 | /welcome 說明 | 你用的是管理者給的臨時密碼，它 72 小時內有效、只能用來設定你自己的密碼。設好之後就用新密碼登入。 | 目前使用的是管理者提供的臨時密碼，效期 72 小時，僅可用於設定個人密碼。設定完成後，請改以新密碼登入。 |
| 334／443／917 | 表單已失效 | 這個表單的記號不對或已失效，什麼都沒有改（送出）。請重新整理頁面再按。 | 同 `r_form` 新文，「未變更任何內容」或「未送出任何內容」依原句 |
| 375／422／434／544／896／911 | 找不到 | 沒有這個申請。／沒有這個網址。 | 無此申請。／無此網址。 |
| 377 | 不是你的申請 | 這個申請不是你送出的，所以這裡不能看也不能按。 | 該申請並非由您送出，無法在此檢視或操作。 |
| 402／405 | 確認頁說明 | 下面就是會被刪除（送出／取消）的全部內容。確定了再按「確認刪除」（「送出」）；按了才會排進佇列。 | 以下為將被刪除（送出／取消）的全部內容。確認無誤後，請按「確認刪除」（「送出」）；按下後才會排入佇列。 |
| 413 | 逾時 | 這個申請已逾時（7 天），不會自動重新提出。 | 該申請已逾時（7 天），不會自動重新提出。 |
| 414／889 | 逾時 | 這個申請已逾時（10 分鐘）。請回到 AI（連接器）重新送出（重新開始）。 | 該申請已逾時（10 分鐘）。請返回 AI（連接器）重新送出（重新開始）。 |
| 416／417 | 作廢 | 這個申請已作廢：%s。 | 該申請已作廢：%s。 |
| 455 | 清理已送出 | 已送出。工作編號 %s。代理會開始清理這個 run 的中間檔；結果不會被動。 | 已送出。工作編號 %s。代理將清理該次分析的中間檔，結果不受影響。 |
| 456 | 已送出 | …你可以回到 AI，用同樣的參數再呼叫一次，它會告訴你工作編號。 | …可返回 AI，以相同參數再呼叫一次，將回報工作編號。 |
| 870／873 | 授權頁 | 允許之後，它可以讀你的 runs，也可以請求送出分析…（不能替你送出）…在這個網站的確認頁按「送出」。 | 允許後，該連接器可讀取您的分析紀錄，並可請求送出分析…（不能代您送出）…於本網站的確認頁按「送出」。 |
| 876-877 | 授權頁 | 要求連到這個平台，並以你的身分運作。／它會把你導回…如果你不認得這個網站，按「拒絕」。 | 要求連線至本平台，並以您的身分運作。／連線完成後將導回：…。若不認得該網站，請按「拒絕」。 |
| 887 | 已處理 | 這個申請已經處理過了。請回到連接器重新開始。 | 該申請已處理完畢。請返回連接器重新開始。 |
| 925 | 未處理 | 什麼都沒有改。請回到連接器重新開始。 | 未變更任何內容。請返回連接器重新開始。 |
| 868 | 授權頁 | (沒有名稱 unnamed) | (未命名 unnamed) |

登入失敗頻繁、密碼長度、兩次輸入不同、請先登入等雙語行（web.py:267、277-279、340-348、437、914）的中文半句已是書面語，維持；測試只確認它們不含禁用詞。

### 2. 新增禁用詞（在 2b 的 `BANNED` 之上，清單改放 `test_web_wording_sweep.py` 供兩邊共用）
2b 既有 22 個詞不動。新增：`你`（「您」不算）、`什麼都`、`做不了`、`讀不到`、`算不出`、`被動`、`還沒`、`這次`、`這個月`、`我們`、`咱`、`沒有這個`、`在哪裡`，以及獨立的拉丁字 `run`／`runs`（正規表達式 `(?<![A-Za-z])runs?(?![A-Za-z])`，只在**中文頁面的可見文字**檢查；`<code>`、`<pre>`、`<kbd>` 內與管線描述欄除外；字串表值內一律不准）。
例外要逐條寫在測試裡並註明理由：雙語並列頁（登入、/welcome、授權頁）只檢查**第一個英文括號之前**的中文半句。

### 3. 測試的覆蓋方式
- **字串表遍歷**：對 `web_board.STRINGS["zh"]`、`web_board.GUIDED["zh"]`、`web_settings.STRINGS["zh"]`、`web_cost.STRINGS["zh"]`、`web_finished.STRINGS["zh"]`、`web._PLAIN["zh"]` 每個值逐詞檢查。**防漏守衛**：用 `ast` 掃 `abf_platform/web*.py`，找出所有模組層、含中文值的字典；清單必須等於測試遍歷的表集合（未來新增中文表沒納入就紅）。
- **渲染頁面**：沿用 `test_web_actions.py` 的 `login`／`area_sheet`／`rid_of` 與 `test_web_guided_launch.py` 的 `rig` 夾具，對下列路徑取 HTML，用 `plain_text` 去標籤後逐詞檢查：`/`（無分析的空看板；有分析、左欄分組的看板）、分析頁每個階段（`?stage=launch|running|results|downstream|finished`）與每個分頁（`?tab=tasks|logs|info|config|metrics|outputs`；涵蓋 failed／lost／succeeded／running 與失敗通知）、`/usage`（有資料、空月份、壞月份）、`/settings`（有環境、無環境、環境不可用）、`/login`（含各錯誤訊息）、`/welcome`（含兩次密碼不同、過長、頻繁失敗）、`/c/<id>`（launch／cancel／clean_work 三種：待確認、已送出、逾時、作廢、他人的）、`/consent/<id>`（兩種 limits 分支與已處理）、`/launch`（2b 已有，改為呼叫共用函式）。
- 側欄屬看板頁面，不另測；另有一案單獨斷言左欄字串（「我的分析」「尚無分析紀錄。」）。
- 英文頁：上面頁面各取 `?lang=en` 版，用既有 `no_cjk`（`test_web_board.py:102`）斷言不含中文（2b 只測 /launch；本次擴大到全部頁面）。

## 失敗先行測試
`test_web_wording_sweep.py`（先寫、現在會紅）：
1. `test_banned_words_cover_every_zh_string_table`：遍歷所有中文字串表，違規為 0；目前紅（`mine`、`none_yet`、`no_analyses` 等約 40 個值）。
2. `test_every_zh_table_is_covered`：`ast` 掃出的中文字典集合等於測試遍歷集合。
3. `test_board_empty_state_is_formal`：空看板含「我的分析」「尚無分析紀錄。」，不含「我的 run」「還沒有 run。」（維護者原話 3）。
4. `test_board_with_runs_has_no_banned_word`：running／succeeded／failed／lost 各狀態 × 左、中、右欄。
5. `test_run_page_every_stage_and_tab`：每階段每分頁。
6. `test_cost_settings_finished_pages`：`/usage`（含「— 本月尚無分析」、壞月份）、`/settings`（含「尚無運算環境。」）、完成頁（gone／foreign／無檔案／該次未產生）。
7. `test_welcome_login_consent_confirm_pages`：登入、/welcome、授權、確認頁各分支，只檢查括號前的中文半句。
8. `test_refusal_lines_on_the_board`：各種被拒的按鈕（取消他人的分析、資料夾仍有工作等）取 flash 行，中文版不含禁用詞（action 層來的訊息見待裁決 2；未納入時只測 `r_*` 鍵產生的句子）。
9. `test_english_pages_have_no_cjk_everywhere`：上列頁面 `?lang=en` 不含中文。
10. `test_guard_catches_every_new_word`：每個新增詞塞進假 HTML 都被抓到；「您」不被「你」誤抓；`<code>run</code>` 與管線描述欄不誤報；雙語括號後的英文不誤報（作法同 2b 的 TC-113／114）。
11. `test_2b_still_uses_the_shared_list`：2b 的 `BANNED` 與新檔的是同一個物件（或子集）；2b 對 `/launch` 的原斷言（「選用這個樣本」「用過的」）仍在且綠。
12. 手動（依 README 通例，ledger 貼證據，不寫自動測試）：`git diff --stat` 只含範圍內的檔；`web.py` 路由程式碼零改動；改前改後 `?lang=en` 全部頁面 HTML 逐字相同（同一組夾具各輸出一份比對）。

## 完成標準（done when）
上列全綠；整套 `tests/run_all.sh --timeout 900` 綠（已知環境紅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 且只剩這一條，視同綠，見 README 通例）；第 1 節對照表每一列都有對應 TC，或在 ledger 註明維持不改的理由；英文頁 HTML 改前改後逐字相同；ledger 列出所有被迫改期望值的既有測試（檔:行、改前、改後）。

## 環境事實
- 現有禁用詞測試：`platform/tests/test_web_guided_launch_2b.py:17`（`BANNED`，22 詞）、`:42`（`banned_in`）、`:563-598`（`test_h11_*`）；它只讀 `/launch` 主欄，且把管線描述欄（`prow`／`scol` 第二格）剔除（`zh_words`，:34-39）。另有 `test_web_actions.py:408`（`要你處理`／`需要處理` 全平台字面）與 `test_web_board.py:322,965`（零星禁詞），本任務不動。
- 用字規則出處：`DESIGN.md:80-86`（「用字」一節）與 DESIGN.md:7、:19（維護者原話）；末段明寫其他畫面尚未清掃、屬 `web-wording-sweep`。`PRODUCT.md` 在 repo 根目錄，executor 開工先讀。
- 中文字串集中在：`web_board.py:35-84`（STRINGS zh）與 `:874` 起（GUIDED，已清）、`web_settings.py:17-27`、`web_cost.py:21-29`、`web_finished.py:11-19`、`web.py:79-80`（`_PLAIN`）與 web.py 內嵌的登入、/welcome、確認、授權頁中文。`welcome.py` 是 CLI 的英文信，非網頁。
- 英文與中文共用同一個 `STRINGS` 結構（鍵相同），本任務不改鍵，所以鍵一致性類測試（如 `test_web_parity.py`）不受影響。
- 全套測試超過單次指令 10 分鐘上限（桌機上 platform 分片約 6 分鐘，全套更久）：跑 `tests/run_all.sh --timeout 900` 時一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 這類迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；不准在測試還在背景跑時就交報告（同 web-upload-page 裁決 23）。
- `feat/web-upload-page` 正在動 `web_upload.py`、`web_board.py`（STRINGS 新增行與上傳按鈕）、`web.py`（路由）。本任務只改既有字串的值以避免衝突；合併後上傳頁的中文由待裁決 1 的後續補掃。

## 不做
- 不改英文字串、不改任何字串表的鍵、不改路由、不改版面與樣式（純文字替換）。
- 不動 `web_upload.py`、`/launch`（含 GUIDED）、`welcome.py`、action 層（`confirm.py`、`jobs.py` 等；後者見待裁決 2）。
- 不把雙語並列頁（登入、/welcome、授權頁）改成 `?lang` 單語；不改「中文 (English)」並列格式。
- 不改 DESIGN.md 的用字規則本身，只補清單與進度句。

## 待裁決
1. **`web_upload.py`（feat/web-upload-page 進行中）**：本任務不碰它。建議：web-upload-page 合併後，**另開一個小任務**只跑本任務的測試（字串表遍歷＋渲染 `/upload`、`/upload/{batch}`），有違規再補改。在那之前，web-upload-page 計畫裁決 16 已要求它通過 DESIGN.md 禁用清單。本任務的 `ast` 防漏守衛在它合併後若發現新的中文字典會紅，這是刻意的提醒。
2. **action 層來的中文訊息**（經 `plain_reason` 顯示在看板被拒按鈕那一行）：`confirm.py:390`「這個 run 還有工作在排隊或進行中，不能刪除」與 `confirm.py:145`「不是你的申請」同樣口語，維護者看得到。建議**納入**，只改這兩三句的中文半句（括號內英文不動），連同釘死它們的測試（`test_cleanup_offer.py`、`test_confirm*.py`）；不改等於維護者下次又看到。未獲裁決前，測試案 8 只測 `r_*` 鍵。
3. **「你」改「您」或省略主詞**：建議統一用「您」（與 /launch 已有的「您名下」一致），能省略就省略（如 `key_note` 可寫「金鑰僅儲存於瀏覽器」）。若維護者偏好全面省略，只改對照表措辭，不影響測試設計。
4. **看板 `quick` 按鈕統一名稱**：`quick`（「用這個 run 的內容再啟動一次」）與 /launch 的 `g_quick`（「沿用設定重新分析」）是同一個動作。建議兩處同名「沿用設定重新分析」（DESIGN.md 用字第 3 條：一個動作一個動詞；維護者原話 5：按鈕是固定名稱，不是句子）。
5. **「run」作為英文名詞是否全面禁用**：DESIGN.md 的中文名詞用「分析」；本計畫禁用中文頁面中獨立的 `run`／`runs`（`<code>`／`<pre>`／管線描述欄除外）。維護者若想保留某些產品詞，把該條從新增禁用詞拿掉即可；建議禁用（維護者原話 3 已點名「我的 run」）。
6. **登入／/welcome／授權頁的「中文 (English)」並列**：形式上雙語並存，與「每個畫面有英文版（`?lang=en`）」的規則不一致，但改成單語是版面改動。建議本次不動，記在 DESIGN.md Open，另案排。
7. **`level_action`「待處理」**：維護者字面禁令只針對「要你處理／需要處理」（`test_web_actions.py:408`），「待處理」未被禁，建議維持。

## 裁決（developer-agent 2026-10-29，取代「待裁決」的建議欄）
1. **web_upload.py 納入**：#263 已於 10-29 合併，上傳頁中文一併清掃。只改 `web_upload.py` 的 `STRINGS["zh"]` 值（不加不刪鍵、不改英文），照「作法」原則；改了哪些逐條寫進 ledger 對照表。測試 6 加 `/upload` 與 `/upload/{batch}`（待傳、完成、失敗三種狀態）；`ast` 防漏守衛要涵蓋它。範圍與「不做」裡「不動 web_upload.py」作廢。
2. **action 層訊息納入**：`confirm.py:390`、`confirm.py:145` 與同類的口語中文半句（括號內英文不動），連同釘死它們的測試（`test_cleanup_offer.py`、`test_confirm*.py`，只改期望字串）。測試 8 改為測完整的 flash 行。只限看板會顯示的拒絕訊息；其他 action 層訊息看到就寫進 ledger「後續」，不改。
3. **「您」**：照建議，統一用「您」，能省略主詞就省略。
4. **quick 按鈕**：照建議，改成「沿用設定重新分析」，與 g_quick 同名。
5. **禁用獨立的 run／runs**：照建議（`<code>`／`<pre>`／管線描述欄除外）。
6. **雙語並列頁**：本次不動，在 DESIGN.md Open 記一行。
7. **「待處理」**：維持。
8. **DESIGN.md**：「用字」一節只改末段＋補禁用詞；裁決 6 的 Open 一行另加在 Open 段。
9. **禁用詞清單的結構（預檢 10-29）**：2b 的 22 字 `BANNED` 原封保留當底，新檔另立 `BANNED_ALL = BANNED + 新增詞`；`test_h11_guard_catches_every_word`（`== [w]`）一字不改、繼續只跑 2b 的清單。新檔的「守衛抓得到每個詞」測試改用 `w in banned_in(...)`（新詞彼此有包含關係，如「還沒」⊂「還沒有」、「這個」⊂「這個月」）。
10. **表外的違規也要改（預檢 10-29）**：目標是「全部中文字串表與渲染頁違規為 0」，對照表只是起點。預檢已知表外項：`web_settings` 的 `pf_expired`、`pf_foreign`（「什麼都沒有改」）；`web.py:306` 標題「設定你自己的密碼」、`web.py:383` 標題「不是你的申請」；`web_upload` 的 `intro`、`cmds_note`、`p_keep`（「你」）與其他口語句。全照「作法」原則改，逐條記進 ledger 對照表。
11. **可同步改期望字串的測試再加這些（預檢 10-29）**：`test_oauth_mcp.py`、`test_confirm_page.py`、`test_cleanup_confirm.py`、`test_web_settings_register.py`、`test_web_upload.py`。只改期望字串，不刪斷言。**不含** `test_aws_launch.py`、`test_azure_launch.py`、`test_gcb_launch.py`——它們釘的是 launch 動作層訊息，不在本件範圍，這三檔若變紅＝改到了不該改的東西，停下回報。
12. **confirm.py 範圍（預檢 10-29，取代裁決 2 的例子）**：只改 `confirm.py:390`（看板拒絕刪除那句）與 `test_cleanup_confirm.py:281`。`confirm.py:145` 是英文在前、看板看不到，不改；看板看到的「不是你的申請」是 `web.py:383` 的標題，依裁決 10 改。
13. **web.py 內嵌中文**：約 81 句不在字串表，`ast` 守衛管不到，由測試 5–7 的渲染頁檢查把關；行號已漂移 5–14 行，以 grep 為準。

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
