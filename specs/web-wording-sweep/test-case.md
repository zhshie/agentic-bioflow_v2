# 測試案例：網頁中文全面改正式書面語＋禁用詞測試擴到每頁（web-wording-sweep）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Write every row so that it can be
judged without reading code: what is set up, what the person or the system does,
what must be seen. No internal jargon without a one-line explanation.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/web-wording-sweep/plan.md`（本任務沒有獨立 spec.md，計畫即規格；「## 裁決」一節優先於前面的「範圍」「不做」「待裁決」）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、被拒絕的畫面，頁面怎麼顯示（這裡特指：出錯或被拒絕時的中文也必須是書面語）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## 讀這份文件前

- 「中文版頁面」＝網址不帶 `?lang=en` 的頁面。「禁用詞」＝新檔 `platform/tests/test_web_wording_sweep.py` 裡的 `BANNED_ALL`：2b 既有 22 詞（用過、選好、寫死、自己填、自己調整、你還沒、還沒有、還不能、這個、這份、這條、這一版、一下、弄、搞、東西、喔、啦、吧、囉、蠻、超）＋ 新增 13 詞（你、什麼都、做不了、讀不到、算不出、被動、還沒、這次、這個月、我們、咱、沒有這個、在哪裡）＋ 獨立的拉丁字 `run`／`runs`。
- 「全部頁面」＝計畫「測試的覆蓋方式」列的頁面：`/`、分析頁（5 個階段、6 個分頁）、`/usage`、`/settings`、完成頁、`/login`、`/welcome`、`/c/<id>`、`/consent/<id>`、`/launch`，加上裁決 1 新增的 `/upload`、`/upload/{batch}`。
- 驗證方式「自動」＝新檔 `platform/tests/test_web_wording_sweep.py`（每條測試要在註解寫上它的 TC 編號），或計畫列為「因字串改了而同步改期望值」的既有測試。「手動」＝閱卷者看 `git diff`、`specs/web-wording-sweep/ledger.md`（沿用 guided-launch-2b 的做法；計畫明寫「依 README 通例，ledger 貼證據」）。
- 計畫表格裡用「…」省略的長句（`web_cost` 的 `note`、授權頁、`/c/<id>` 說明），測試只釘計畫寫出來的那一段，省略的部分不釘。

## User Story 1 — 維護者的原話在每個頁面都兌現（優先度 P1）

維護者原話：「中文顯示不能口語。」；「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」；看到的違規例「我的 run」「還沒有 run。」；「哪有一個固定的按鈕會這樣寫?」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 3；測試 3 | 功能 | 登入後，沒有任何分析的帳號 | 開中文版看板 `/` | 左欄標題是「我的分析」，空狀態是「尚無分析紀錄。」 | 自動：`test_board_empty_state_is_formal` |
| TC-002 | 原話 3；測試 3 | 功能 | 同 TC-001 | 同一頁找舊句子 | 整頁沒有「我的 run」，也沒有「還沒有 run。」 | 自動：`test_board_empty_state_is_formal` |
| TC-003 | 原話 3（「兩句字面都必須在全部頁面的中文版消失」） | 功能 | 「全部頁面」逐一渲染中文版 | 在每一頁的可見文字找「我的 run」「還沒有 run。」 | 每一頁都找不到這兩句 | 自動：`test_banned_words_cover_every_zh_string_table` 與各頁面測試 |
| TC-004 | 原話 2（DESIGN.md:80；「保證它們在所有頁面都不出現」） | 功能 | 「全部頁面」逐一渲染中文版 | 在每一頁的可見文字找「選用這個樣本」「用過的」 | 每一頁都找不到（不只 `/launch`） | 自動：各頁面測試（測試 4–7） |
| TC-005 | 原話 3；對照表 `no_analyses`、`mine` | 功能 | 有分析的帳號，左欄有分組，其中一組沒有分析 | 開中文版看板 | 左欄標題「我的分析」；空分組顯示「尚無分析」；沒有「我的 run」「還沒有分析」 | 自動：`test_board_empty_state_is_formal`、`test_board_with_runs_has_no_banned_word` |
| TC-006 | 原話 1；失敗先行測試 4–7 | 功能 | 用測試夾具渲染「全部頁面」的中文版 | 去掉標籤取可見文字，逐一比對禁用詞 | 每一頁違規數為 0（雙語頁只看第一個英文括號之前的中文半句；`<code>`／`<pre>`／`<kbd>` 與管線描述欄除外） | 自動：測試 4、5、6、7 |
| TC-007 | 原話 1；失敗先行測試 1 | 功能 | 取 `web_board.STRINGS["zh"]`、`web_board.GUIDED["zh"]`、`web_settings.STRINGS["zh"]`、`web_cost.STRINGS["zh"]`、`web_finished.STRINGS["zh"]`、`web_upload.STRINGS["zh"]`、`web._PLAIN["zh"]` | 每個值逐詞比對禁用詞（字串表值內獨立的 `run`／`runs` 一律不准） | 違規為 0 | 自動：`test_banned_words_cover_every_zh_string_table` |
| TC-008 | 原話 5；裁決 4；對照表 `quick` | 功能 | 分析頁上出現「再啟動」按鈕的狀態 | 看按鈕文字，並與 `GUIDED["zh"]["g_quick"]` 比較 | 看板的 `quick` 值是「沿用設定重新分析」，與 `/launch` 的 `g_quick` 是同一個字串；不是「用這個 run 的內容再啟動一次」 | 自動：既有 `test_web_board.py` 等同步改期望值＋測試 5 |
| TC-009 | 原話 5；DESIGN.md「用字」第 2、3 條 | 功能 | 看板上有確認頁按鈕與對話按鈕的狀態 | 讀按鈕文字 | `c_open` 是「開啟確認頁」、`ask_here` 是「詢問本分析」、`this_analysis` 是「本分析的對話」；都是固定名稱，不是句子，不含「你」「這個」 | 自動：測試 4、5 與同步改期望值的 `test_web_board.py` |

## User Story 2 — 字串對照表逐列改好（看板、設定、費用、完成頁）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 對照表 web_board：`mine`、`none_yet`、`no_analyses`、`this_analysis`、`ask_here` | 功能 | 讀 `web_board.STRINGS["zh"]` 與渲染結果 | 逐鍵比對 | 值依序是「我的分析」「尚無分析紀錄。」「尚無分析」「本分析的對話」「詢問本分析」；舊值「我的 run」「還沒有 run。」「還沒有分析」「這個分析的對話」「問這個分析」不再出現 | 自動：測試 1、3、4 與同步改期望值的既有測試 |
| TC-011 | 對照表 web_board：`c_open`、`c_content_text`、`c_next_text` | 功能 | 有「可清理中間檔」通知的看板 | 看通知卡 | 「開啟確認頁」；「該次分析已成功；其中間檔（work）可清理，結果不受影響。」；「請開啟確認頁，核對將刪除的資料夾後再決定。」 | 自動：測試 4 與同步改期望值的 `test_web_board.py`／`test_cleanup_offer.py` |
| TC-012 | 對照表 web_board：`r_site`、`row_site` | 功能 | 站台無回應的分析 | 看列與原因行 | `r_site` 是「站台無回應」；`row_site` 是「執行 · 站台無回應」 | 自動：測試 4、5 與同步改期望值 |
| TC-013 | 對照表 web_board：`not_reached`、`not_found_title`、`not_found_body`、`no_notices`、`no_failed_tasks` | 功能 | 分析頁：未到達的階段、不存在或他人的分析、無通知、無失敗任務 | 逐一開啟 | 「該次分析尚未進行至此階段。」；「找不到該次分析」；「無此分析，或該分析不屬於您。」；「目前無通知」；「無失敗任務」 | 自動：測試 5、5b 與同步改期望值 |
| TC-014 | 對照表 web_board：`r_none`、`r_generic`、`r_form` | 功能 | 看板上被拒的按鈕 | 讀被拒的那一行 | 「未送出任何內容。」；「目前無法執行此操作。」；「表單驗證碼不符或已失效，未送出任何內容。請重新整理頁面後再操作。」 | 自動：測試 8 與同步改期望值 |
| TC-015 | 對照表 web_board：`o_failed`、`o_none`、`o_empty` | 功能 | 輸出分頁：讀取失敗、無輸出資料夾紀錄、資料夾為空 | 逐一開啟 | 「無法讀取」；「無輸出資料夾紀錄」；「此資料夾為空」 | 自動：測試 5 與同步改期望值的 `test_web_results_outputs.py` |
| TC-016 | 對照表 web_settings：`ce_none`／`no_ce`、`key_note`、`token_hint`、`check_cmd` | 功能 | 設定頁（有環境、無環境、金鑰區、憑證區） | 逐鍵比對 | 「尚無運算環境。」；「金鑰僅儲存於您的瀏覽器，不會傳送至平台。」；「請於終端機執行 abf-platform token new 建立。」；「請以指令確認」 | 自動：測試 6 與同步改期望值的 `test_web_settings.py` |
| TC-017 | 對照表 web_cost：`th_where`、`empty`、`bad_month`、`no_reason`、`unknown_runs`、`note`、`usd_note`、`action` | 功能 | 費用頁各狀態 | 逐鍵比對 | 「執行位置」；「— 本月尚無分析」；「月份格式不符，已顯示本月。」；「無法計算」；「另有 %d 個分析無法計算」；`note` 結尾是「數字依執行紀錄估算，略低於實際帳單。」；「SU 以 %s 匯率概算為美元，並非帳單金額。」；「待處理：本月雲端額度已用盡」 | 自動：測試 6 與同步改期望值的 `test_web_cost.py` |
| TC-018 | 對照表 web_finished：`params`、`defaults`、`gone_note`、`foreign`、`no_multiqc`、`no_files` | 功能 | 完成頁各狀態 | 逐鍵比對 | 「已變更的參數」；「全部採預設值」；「該次送出的內容已不保留。」；「此分析並非經由平台送出，無來源紀錄。」；「該次未產生」；「無檔案」 | 自動：測試 6 與同步改期望值的 `test_web_finished.py` |
| TC-019 | 對照表 web.py:79 `_PLAIN["zh"]["run"]` | 功能 | 讀 `web._PLAIN["zh"]` | 比對 | `run` 的值是「分析名稱」，不是「run 名稱」 | 自動：測試 1、7 |
| TC-020 | 計畫「維持不改」；裁決 7 | 功能 | 對照表沒列的鍵 | 比較改前改後的值 | `level_action`「待處理」、`row_stopped`／`r_stopped`「已取消」、`state_*`、`count_*`、`stage_*`、`tab_*`、`th_*`、`ty_*`、`dur_*`、`card_*`、`l_*`、`e_*` 的值與改前完全相同 | 手動：閱卷者看 git diff |
| TC-021 | 目標「英文版不動」；「不做」第 1 條 | 功能 | 比較改前改後的所有字串表 | 看 `STRINGS["en"]` 與每張表的鍵 | 英文值逐字相同；zh／en 的鍵集合與改前相同（不加不刪鍵） | 手動：閱卷者看 git diff；`test_web_parity.py` 仍綠 |

## User Story 3 — 登入、/welcome、確認頁、授權頁的中文半句（優先度 P1）

這些句子寫在 `web.py` 裡、不在字串表，由渲染頁面把關（裁決 13）。行號以 grep 為準。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 對照表 web.py:151 | 功能 | 開 `/login` | 讀中文說明 | 含「請以您的姓名與網頁密碼登入（網頁密碼不同於 AI 使用的權杖；於平台主機的終端機以 abf-platform user passwd 設定，或使用管理者提供的一次性臨時密碼）。」；沒有「你」 | 自動：測試 7 與同步改期望值的 `test_web_login.py` |
| TC-023 | 對照表 web.py:240 | 功能 | 從別的來源送出表單 | 看被拒的畫面 | 中文半句是「此表單並非由本頁送出，未變更任何內容。」 | 自動：測試 7 與同步改期望值 |
| TC-024 | 對照表 web.py:301 | 功能 | 以臨時密碼登入後開 `/welcome` | 讀說明 | 含「目前使用的是管理者提供的臨時密碼，效期 72 小時，僅可用於設定個人密碼。設定完成後，請改以新密碼登入。」 | 自動：測試 7 與同步改期望值的 `test_web_welcome.py` |
| TC-025 | 對照表 web.py:334／443／917 | 例外 | 在 `/welcome`、`/c/<id>`、`/consent/<id>` 送出失效或記號不對的表單 | 讀被拒的畫面 | 中文半句與 `r_form` 同義：「表單驗證碼不符或已失效，」後接「未變更任何內容」（改動類）或「未送出任何內容」（送出類），再接「請重新整理頁面後再操作。」；不含「記號」「什麼都沒有」 | 自動：測試 7 與同步改期望值 |
| TC-026 | 對照表 web.py:375／422／434／544／896／911 | 例外 | 開不存在的申請編號、不存在的網址 | 讀「找不到」畫面 | 中文半句是「無此申請。」或「無此網址。」；不含「沒有這個」 | 自動：測試 7 與同步改期望值的 `test_web_confirm_plain.py` |
| TC-027 | 對照表 web.py:377 | 例外 | 開別人送出的申請的確認頁 | 讀畫面 | 中文半句是「該申請並非由您送出，無法在此檢視或操作。」 | 自動：測試 7 與同步改期望值 |
| TC-028 | 對照表 web.py:402／405 | 功能 | 開待確認的 `/c/<id>`（刪除、送出、取消三種） | 讀說明 | 含「以下為將被刪除（送出／取消）的全部內容。確認無誤後，請按「確認刪除」（「送出」）；按下後才會排入佇列。」（括號內依該頁種類只出現對應的一個詞）；按鈕名稱「確認刪除」「送出」不變 | 自動：測試 7 與同步改期望值的 `test_confirm_page.py`／`test_web_confirm_plain.py` |
| TC-029 | 對照表 web.py:413、414／889 | 例外 | 逾時的確認頁（7 天）與逾時的授權頁（10 分鐘） | 讀畫面 | 「該申請已逾時（7 天），不會自動重新提出。」；「該申請已逾時（10 分鐘）。請返回 AI（連接器）重新送出（重新開始）。」 | 自動：測試 7 與同步改期望值 |
| TC-030 | 對照表 web.py:416／417 | 例外 | 已作廢的申請 | 讀畫面 | 「該申請已作廢：%s。」 | 自動：測試 7 與同步改期望值 |
| TC-031 | 對照表 web.py:455、456 | 功能 | 清理申請送出後的頁面、已送出的頁面 | 讀畫面 | 清理：「已送出。工作編號 %s。代理將清理該次分析的中間檔，結果不受影響。」；已送出：含「可返回 AI，以相同參數再呼叫一次，將回報工作編號。」；不含「這個 run」「被動」 | 自動：測試 7 與同步改期望值的 `test_cleanup_confirm.py`／`test_web_confirm_plain.py` |
| TC-032 | 對照表 web.py:870／873 | 功能 | 開 `/consent/<id>`（兩種 limits 分支各一） | 讀授權說明 | 含「允許後，該連接器可讀取您的分析紀錄，並可請求送出分析」「（不能代您送出）」「於本網站的確認頁按「送出」」；不含「你的 runs」 | 自動：測試 7 與同步改期望值的 `test_oauth_consent.py`／`test_oauth_mcp.py` |
| TC-033 | 對照表 web.py:876–877 | 功能 | 開 `/consent/<id>` | 讀確認區 | 含「要求連線至本平台，並以您的身分運作。」「連線完成後將導回：」「若不認得該網站，請按「拒絕」。」 | 自動：測試 7 與同步改期望值 |
| TC-034 | 對照表 web.py:868 | 功能 | 授權的連接器沒有名稱 | 讀授權頁 | 顯示「(未命名 unnamed)」，不是「(沒有名稱 unnamed)」 | 自動：測試 7 與同步改期望值 |
| TC-035 | 對照表 web.py:887、925 | 例外 | 重複處理過的授權申請；未處理就離開的授權申請 | 讀畫面 | 「該申請已處理完畢。請返回連接器重新開始。」；「未變更任何內容。請返回連接器重新開始。」 | 自動：測試 7 與同步改期望值 |
| TC-036 | 計畫「雙語行維持」（web.py:267、277–279、340–348、437、914） | 功能 | 登入失敗頻繁、密碼長度、兩次輸入不同、請先登入等雙語行 | 取每行第一個英文括號之前的中文半句 | 不含禁用詞；仍是「中文 (English)」並列；英文半句與改前逐字相同 | 自動：測試 7 |

## User Story 4 — 表外的違規、上傳頁、action 層那一句（優先度 P1）

依裁決 1、2、10、11、12：目標是「全部中文字串表與渲染頁違規為 0」，對照表只是起點。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 裁決 10：`web_settings` 的 `pf_expired`、`pf_foreign` | 功能 | 設定頁的個人密碼過期、非本人兩種狀態 | 讀中文 | 不含「什麼都」「沒有改」等禁用詞，改成書面語；句子仍說明發生什麼事 | 自動：測試 6 與同步改期望值的 `test_web_settings_register.py` |
| TC-038 | 裁決 10：web.py 標題「設定你自己的密碼」 | 功能 | 開 `/welcome` | 讀標題 | 標題不含「你」，改成書面語（例如「您」或省略主詞） | 自動：測試 7 與同步改期望值的 `test_web_welcome.py` |
| TC-039 | 裁決 10：web.py 標題「不是你的申請」 | 例外 | 開別人的確認頁 | 讀標題 | 標題不含「你」，改成書面語；看板看得到的是這個標題 | 自動：測試 7 與同步改期望值 |
| TC-040 | 裁決 1、10：`web_upload.STRINGS["zh"]` | 功能 | 讀整張表 | 逐值比對禁用詞 | 違規為 0；`intro`、`cmds_note`、`p_keep` 不含「你」；其他口語句也改成書面語 | 自動：`test_banned_words_cover_every_zh_string_table`、`test_web_upload.py` 同步改期望值 |
| TC-041 | 裁決 1：測試 6 加 `/upload` | 功能 | 開中文版 `/upload`（有可傳的狀態與無資料的狀態） | 取可見文字比對禁用詞 | 違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-042 | 裁決 1：測試 6 加 `/upload/{batch}` 三種狀態 | 功能 | 中文版 `/upload/{batch}`：待傳、完成、失敗三種批次 | 各取可見文字比對 | 三種狀態違規皆為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-043 | 裁決 1：只改值，不加不刪鍵、不改英文 | 功能 | 比較改前改後的 `web_upload.py` | 看 diff | 只有 `STRINGS["zh"]` 的值有變；鍵與英文值不變；逐條改動記在 ledger 對照表 | 手動：閱卷者看 git diff 與 ledger |
| TC-044 | 裁決 2、12：`confirm.py:390` | 例外 | 某分析仍有工作在排隊或進行中，在看板按刪除 | 取被拒絕的完整那一行（flash 行） | 中文半句不含「這個 run」及任何禁用詞；括號內英文 `(a job of this run is still queued or running)` 不變；中文半句不為空 | 自動：`test_refusal_lines_on_the_board`；同步改期望值的 `test_cleanup_confirm.py` |
| TC-045 | 裁決 2、12（行為不變） | 例外 | 同 TC-044 | 按刪除 | 仍被拒絕，沒有任何資料夾被刪、沒有新工作排入；只是文字改了 | 自動：`test_cleanup_confirm.py` |
| TC-046 | 裁決 12：`test_cleanup_confirm.py:281` | 功能 | 看該測試的 diff | 比對改前改後 | 只有該處的期望字串改為新中文半句；斷言數量不變、不放寬 | 手動：閱卷者看 git diff 與 ledger |
| TC-047 | 裁決 12 | 不在範圍 | 看 `confirm.py:145`（英文在前、看板看不到的「不是你的申請」） | 比對 base | 沒被改動 | 手動：閱卷者看 git diff |
| TC-048 | 裁決 2（「其他 action 層訊息看到就寫進 ledger『後續』，不改」） | 不在範圍 | 看 diff 與 ledger | 找 `confirm.py`、`jobs.py` 等 action 層檔的改動 | 除 `confirm.py:390` 外 action 層沒有任何改動；其他看到的口語句只出現在 ledger「後續」 | 手動：閱卷者看 git diff 與 ledger |

## User Story 5 — 每個渲染頁面都掃過（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | 測試 4 | 功能 | 看板上有 running／succeeded／failed／lost 四種狀態的分析（含空看板與左欄分組） | 對左、中、右欄分別取可見文字 | 每種狀態 × 每欄違規為 0 | 自動：`test_board_with_runs_has_no_banned_word` |
| TC-050 | 測試 5 | 功能 | 一個分析 | 逐一開 `?stage=launch|running|results|downstream|finished` | 五個階段違規皆為 0 | 自動：`test_run_page_every_stage_and_tab` |
| TC-051 | 測試 5 | 功能 | failed／lost／succeeded／running 各一個分析 | 逐一開 `?tab=tasks|logs|info|config|metrics|outputs` | 每種狀態 × 六個分頁違規皆為 0 | 自動：`test_run_page_every_stage_and_tab` |
| TC-052 | 測試 5（失敗通知） | 功能 | 有失敗通知的分析 | 開分析頁與看板 | 通知卡與失敗任務區違規為 0 | 自動：`test_run_page_every_stage_and_tab` |
| TC-053 | 測試 6 | 功能 | `/usage` 有資料的月份 | 取可見文字 | 違規為 0；欄位名稱是「執行位置」 | 自動：`test_cost_settings_finished_pages` |
| TC-054 | 測試 6；對照表 `empty` | 功能 | `/usage` 沒有分析的月份 | 取可見文字 | 含「— 本月尚無分析」；違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-055 | 測試 6；對照表 `bad_month` | 例外 | `/usage?month=` 給壞格式 | 取可見文字 | 含「月份格式不符，已顯示本月。」；違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-056 | 對照表 `no_reason`、`unknown_runs` | 例外 | 有分析無法算 SU 的月份 | 取可見文字 | 含「無法計算」與「另有 N 個分析無法計算」；不含「算不出」 | 自動：`test_cost_settings_finished_pages` |
| TC-057 | 測試 6 | 功能 | `/settings` 有運算環境 | 取可見文字 | 違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-058 | 測試 6；對照表 `ce_none` | 功能 | `/settings` 沒有運算環境 | 取可見文字 | 含「尚無運算環境。」；違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-059 | 測試 6 | 例外 | `/settings` 環境不可用 | 取可見文字 | 違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-060 | 測試 6；對照表 `gone_note`、`foreign` | 功能 | 完成頁：內容已不保留的分析；非平台送出的分析 | 取可見文字 | 分別含「該次送出的內容已不保留。」「此分析並非經由平台送出，無來源紀錄。」；違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-061 | 測試 6；對照表 `no_files`、`no_multiqc` | 功能 | 完成頁：沒有檔案、沒有 MultiQC | 取可見文字 | 含「無檔案」「該次未產生」；違規為 0 | 自動：`test_cost_settings_finished_pages` |
| TC-062 | 測試 7 | 例外 | `/login` 的各錯誤訊息（含失敗太頻繁） | 取第一個英文括號之前的中文半句 | 違規為 0 | 自動：`test_welcome_login_consent_confirm_pages` |
| TC-063 | 測試 7 | 例外 | `/welcome`：兩次密碼不同、過長、頻繁失敗 | 同上 | 違規為 0 | 自動：`test_welcome_login_consent_confirm_pages` |
| TC-064 | 測試 7 | 功能 | `/c/<id>` 的 launch／cancel／clean_work 三種：待確認、已送出 | 取可見文字 | 六種組合違規為 0 | 自動：`test_welcome_login_consent_confirm_pages` |
| TC-065 | 測試 7 | 例外 | `/c/<id>` 三種各自的：逾時、作廢、他人的 | 取可見文字 | 九種組合違規為 0 | 自動：`test_welcome_login_consent_confirm_pages` |
| TC-066 | 測試 7 | 功能 | `/consent/<id>` 的兩種 limits 分支 | 取中文半句 | 違規為 0 | 自動：`test_welcome_login_consent_confirm_pages` |
| TC-067 | 測試 7 | 例外 | `/consent/<id>` 已處理過 | 取中文半句 | 違規為 0 | 自動：`test_welcome_login_consent_confirm_pages` |
| TC-068 | 測試 4–7；「`/launch`（2b 已有，改為呼叫共用函式）」 | 功能 | `/launch` 的各狀態（2b 的 `pages()`） | 用新檔的共用檢查函式掃 | 違規為 0，且 2b 自己的 `test_h11_no_banned_word` 仍綠 | 自動：2b 檔改呼叫共用函式後仍綠 |
| TC-069 | 測試 8；裁決 2 | 例外 | 在看板按：取消他人的分析、刪除仍有工作的資料夾、送出失效表單 | 取完整的 flash 行（含 action 層來的訊息） | 中文版整行不含禁用詞；每行仍說明發生什麼事與下一步 | 自動：`test_refusal_lines_on_the_board` |
| TC-070 | 測試 9 | 功能 | 上列所有頁面（含 `/upload`） | 加 `?lang=en` 取 HTML，用既有 `no_cjk` 檢查 | 每一頁都不含中文字 | 自動：`test_english_pages_have_no_cjk_everywhere` |

## User Story 6 — 禁用詞測試本身可靠，之後新增字串違規會當場紅（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-071 | 「作法」2；裁決 9 | 功能 | 讀新檔的 `BANNED_ALL` | 數內容 | 含 2b 的 22 詞（原封）＋ 你、什麼都、做不了、讀不到、算不出、被動、還沒、這次、這個月、我們、咱、沒有這個、在哪裡，以及獨立 `run`／`runs` 的規則 `(?<![A-Za-z])runs?(?![A-Za-z])` | 自動：`test_guard_catches_every_new_word` |
| TC-072 | 測試 10；裁決 9 | 功能 | 每個新增詞各塞進一段假 HTML | 呼叫檢查函式 | 每個詞都被抓到（用 `w in banned_in(...)`，因為詞彼此有包含關係，如「還沒」⊂「還沒有」） | 自動：`test_guard_catches_every_new_word` |
| TC-073 | 測試 10 | 功能 | 假 HTML 含「您」 | 呼叫檢查函式 | 「您」不被「你」誤抓；含「你」則被抓 | 自動：`test_guard_catches_every_new_word` |
| TC-074 | 測試 10；「作法」2 | 功能 | 假 HTML：`<code>run</code>`、`<pre>`、`<kbd>` 內的 run；管線描述欄的英文 | 呼叫檢查函式 | 不誤報 | 自動：`test_guard_catches_every_new_word` |
| TC-075 | 「作法」2 | 功能 | 假 HTML 與假字串表：可見文字有獨立的 run／runs；字串表值是「run 名稱」 | 呼叫檢查函式 | 都被抓到；`running`、`prune` 這類夾在英文字母中的不被抓 | 自動：`test_guard_catches_every_new_word` |
| TC-076 | 「作法」2 例外；測試 10 | 功能 | 雙語頁的假 HTML：第一個英文括號之前乾淨，括號之後有英文 | 呼叫檢查函式 | 只檢查括號之前的中文半句，括號後的英文不誤報；括號之前有禁用詞則被抓到 | 自動：`test_guard_catches_every_new_word` |
| TC-077 | 測試 2；「作法」3 防漏守衛 | 功能 | 用 `ast` 掃 `abf_platform/web*.py` 模組層含中文值的字典 | 與測試遍歷的表集合比較 | 兩者相等，集合共 7 張：`web_board.STRINGS`、`web_board.GUIDED`、`web_settings.STRINGS`、`web_cost.STRINGS`、`web_finished.STRINGS`、`web_upload.STRINGS`、`web._PLAIN` | 自動：`test_every_zh_table_is_covered` |
| TC-078 | 測試 2（「未來新增中文表沒納入就紅」） | 功能 | 餵掃描函式一段多了一張含中文字典的假原始碼 | 比對 | 掃描結果多出一張，守衛判定紅 | 自動：`test_every_zh_table_is_covered` |
| TC-079 | 裁決 9；測試 11 | 功能 | 看 2b 檔 | 比對 | 2b 的 `BANNED` 仍是原來 22 詞；`test_h11_guard_catches_every_word` 一字不改（仍是 `== [w]`、仍只跑 2b 的清單）且綠 | 自動：`test_2b_still_uses_the_shared_list` |
| TC-080 | 測試 11；「範圍：檔案」 | 功能 | 看 2b 檔與新檔 | 比對 | 2b 的 `BANNED` 與新檔共用同一份（同物件或 2b 為 `BANNED_ALL` 子集）；`banned_in` 是共用函式；2b 對 `/launch` 的「選用這個樣本」「用過的」斷言仍在且綠；既有斷言一條都不少 | 自動：`test_2b_still_uses_the_shared_list` |
| TC-081 | 「作法」2（`run` 只查可見文字）；分析名稱屬使用者資料 | 例外 | 頁面夾具的分析名稱含 `run`（例如 2b 夾具用的 `run-a`） | 渲染看板與分析頁並掃描 | 使用者命名的分析名稱不造成違規；排除方式（改夾具名稱或只排除名稱欄）不得讓介面字串逃過檢查，且寫進 ledger | 自動：測試 4、5 |
| TC-082 | 「失敗先行測試」前言（先寫、現在會紅） | 功能 | 新檔寫好、字串尚未改的狀態 | 跑 `test_banned_words_cover_every_zh_string_table` | 紅，列出約 40 個違規值（含 `mine`、`none_yet`、`no_analyses`）；ledger 貼這次紅燈的輸出 | 手動：閱卷者看 ledger |

## User Story 7 — 範圍、既有測試、文件、完成標準（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-083 | 「範圍：檔案」＋裁決 1、2、11、12 | 功能 | 比對 base 的檔案清單 | `git diff --stat` | 只含：`web_board.py`、`web.py`、`web_settings.py`、`web_cost.py`、`web_finished.py`、`web_upload.py`、`confirm.py`（僅 390 行）、新檔 `test_web_wording_sweep.py`、`test_web_guided_launch_2b.py`、計畫列的既有測試檔（含裁決 11 加的五個）、`DESIGN.md`、`specs/web-wording-sweep/` 下的文件 | 手動：閱卷者看 git diff |
| TC-084 | 「範圍」web.py；「不做」第 1 條 | 不在範圍 | 比對 base 的 `web.py` | 看 diff | 只有中文字面不同；路由、函式、邏輯、英文半句、雙語並列格式零改動 | 手動：閱卷者看 git diff |
| TC-085 | 「範圍」web_board.py | 功能 | 比對 base 的 `web_board.py` | 看 diff | 只有 `STRINGS["zh"]` 的值不同；`GUIDED`、英文、鍵、函式零改動 | 手動：閱卷者看 git diff |
| TC-086 | 「不做」第 1 條（不改版面與樣式） | 不在範圍 | 比對 base | 看 diff | 沒有樣式表、標籤結構、屬性的改動（純文字替換） | 手動：閱卷者看 git diff |
| TC-087 | 目標「英文版不動」；測試 12 | 不在範圍 | 用同一組夾具，改前、改後各輸出全部頁面的 `?lang=en` HTML | 逐字比對 | 完全相同；ledger 貼證據 | 手動：閱卷者看 ledger 並抽查重跑 |
| TC-088 | 「範圍」最後一點 | 功能 | 看既有測試檔的 diff | 逐條比對 | 只有期望字串改成新文；沒有刪斷言、沒有放寬、沒有跳過；ledger「Existing assertions that changed」逐條列檔:行、改前、改後、依據 | 手動：閱卷者看 git diff 與 ledger |
| TC-089 | 裁決 11（不含三檔）；「範圍」（清單外的檔變紅要停下回報） | 功能 | 比對 base | 看 `test_aws_launch.py`、`test_azure_launch.py`、`test_gcb_launch.py` 與清單外的測試檔 | 這三檔與清單外的檔零改動；三檔仍綠 | 手動：閱卷者看 git diff；在閱卷時單檔重跑這三檔 |
| TC-090 | 「環境事實」：`test_web_actions.py:408`、`test_web_board.py:322,965` | 功能 | 看這些斷言 | 比對 base | 「要你處理」「需要處理」及零星禁詞的斷言仍在，未被刪或放寬 | 手動：閱卷者看 git diff |
| TC-091 | 「範圍」DESIGN.md | 功能 | 看 DESIGN.md「用字」一節末段 | 比對 base | 「Other screens … are not yet swept; that is the backlog item `web-wording-sweep`」已改為「已全部清掃（web-wording-sweep，10-29）」，並說明禁用詞由 `test_web_wording_sweep.py` 在每個頁面與每張中文字串表檢查 | 手動：閱卷者讀 DESIGN.md |
| TC-092 | 「範圍」DESIGN.md | 功能 | 看同一節的禁用詞清單 | 比對 base | 清單補進新增的 13 個詞與獨立 `run`／`runs` | 手動：閱卷者讀 DESIGN.md |
| TC-093 | 「不做」第 5 條；裁決 8 | 功能 | 看 DESIGN.md 的 diff | 比對 | 「用字」第 1–4 條規則本身不變；只動末段、清單與 Open 段 | 手動：閱卷者看 git diff |
| TC-094 | 裁決 6、8 | 功能 | 看 DESIGN.md 的 Open 段 | 找新增行 | 有一行記「登入／`/welcome`／授權頁的『中文 (English)』並列與 `?lang` 單語規則不一致，另案排」之意 | 手動：閱卷者讀 DESIGN.md |
| TC-095 | 完成標準「對照表每一列都有對應 TC，或在 ledger 註明維持不改」；裁決 1、10 | 功能 | 看 ledger | 對照 58 列（board 22、settings 4、cost 8、finished 6、web.py 18） | 每一列有對應測試或 ledger 說明；`web_upload` 與表外項（裁決 10）逐條有「舊→新」 | 手動：閱卷者看 ledger |
| TC-096 | 完成標準 | 功能 | 在 WSL 或 Linux 跑整套 | `tests/run_all.sh --timeout 900`（背景執行，等跑完） | 全綠；唯一允許的紅是已知的 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` | 手動：看完成記號（GREEN＜sha＞）與 executor 的輸出 |
| TC-097 | 「不做」第 3 條 | 不在範圍 | 開 `/login`、`/welcome`、`/consent/<id>` 的中文版 | 看畫面 | 仍是「中文 (English)」並列，沒有被改成單語；格式與改前相同 | 自動：測試 7 與同步改期望值的既有測試 |
| TC-098 | 「不在範圍」：`web_launch.py`、`GUIDED`、`welcome.py` | 不在範圍 | 比對 base | 看 diff | 這三處零改動 | 手動：閱卷者看 git diff |

## 憲法與安全網

這次改的是確認頁與授權頁的文字，會碰到「人的同意要走確認頁」與「每個拒絕要說清楚」的規則（憲法 5.0.0 的同意路徑；不變式 12、13 的精神：不悄悄失敗）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-099 | 5.0.0：同意經由確認頁；計畫 TC-028 | 功能 | `/c/<id>` 的 launch／cancel／clean_work 待確認頁 | 讀頁面、檢查表單 | 說明仍寫明會被刪除／送出／取消的全部內容，按鈕名稱仍是「確認刪除」「送出」，表單路由與改前相同；開頁（GET）本身不排入任何工作 | 自動：同步改期望值的 `test_web_confirm_plain.py`、`test_confirm_page.py` 仍綠 |
| TC-100 | 精神：拒絕要說清楚（Safety Net／不變式 13） | 功能 | 看板被拒按鈕、失效表單 | 讀被拒那一行 | 仍說明發生什麼事與下一步（例如「請重新整理頁面後再操作。」），沒有因改寫而變成只剩一個「無法執行」 | 自動：`test_refusal_lines_on_the_board` |

## 專長守則（ui）

計畫附有 `## 專長守則（ui）`；本任務是純文字替換，守則的前端限制與狀態規則以「不退步」為準。DESIGN.md 列的每個畫面與狀態（空、錯誤、失敗）都在 US5 有對應 TC。

| 編號 | 專長守則條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-101 | 前端限制：無 inline style、不載外部資源、CSP 標頭 | 功能 | 改字後的看板、確認頁、上傳頁、`/launch` | 跑既有的前端限制測試 | 無 `style=` 屬性、無外部網址、CSP 標頭存在，與改前相同 | 自動：既有 `test_web_board.py:247`、`:872`、`:1134`；`test_web_confirm_plain.py:153`；`test_web_upload.py:324`；`test_web_guided_launch_2d.py:675` 仍綠 |
| TC-102 | 狀態不只靠顏色（符號＋文字＋顏色） | 功能 | running／succeeded／failed／lost 的狀態標示 | 讀 HTML | 每個狀態仍同時有符號與文字（`state_*`、`count_*` 的文字沒被動到） | 自動：既有 `test_web_status_squares_3.py`、`test_web_board.py` 仍綠 |
