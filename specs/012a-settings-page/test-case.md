# 測試案例：設定頁第一片（個人逐步模式與開發模式、憑證已設定狀態）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
這個功能沒有 spec.md；`specs/012a-settings-page/plan.md` 同時當規格，下表「對應需求」引用它的「作法 N」、「裁決」、「六項必填檢核」、「維護者原話」。
-->

**規格**：`specs/012a-settings-page/plan.md`（無獨立 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式欄的 `T:` 代表 `platform/tests/test_web_settings_personal.py`（新檔）裡的測試；其他檔案寫全名。「畫面」都指已登入使用者看到的 `/settings` 頁面，除非另外說明。「中間欄」是 `/settings` 頁中間那一欄。

維護者原話與它們對應的案例：
- DESIGN.md 畫面 12：「**Settings**: compute environments, credentials (token, 12 h), Secrets (AI model key, Jev key optional; browser only), Personal (step-by-step mode, development mode); Operator panel and Roles as dashed "coming later".」→ TC-001、TC-002、TC-003、TC-030、TC-052、TC-055
- PLAN 第 145 行：「運算環境／憑證（只顯示「已設定」）／個人（逐步模式、開發模式＝國網不限 SU、畫面醒目標示）／模型金鑰只存瀏覽器」→ TC-013、TC-030、TC-033、TC-052、TC-054
- DESIGN.md 維護者原話第 9 點：「不需要Jev "開關"，只要在設定讓使用者可以放金鑰。」→ TC-054（本片不做輸入，只確認沒有悄悄亂做；見總覽「不確定的地方」）
- DESIGN.md 維護者原話第 2 點：「系統設定先。然後右側有對話框，直接對話系統就會引導使用者快速上手建專案，選pipline條參數等等」→ TC-057（本片只做設定，右欄不動）

## User Story 1 — 個人段：逐步模式與開發模式可存可改（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 2；DESIGN 畫面 12「Personal (step-by-step mode, development mode)」 | 功能 | 已登入使用者 | 開 `GET /settings` | 「個人」那一段裡有兩列：「逐步模式」、「開發模式」；每列各有一個按鈕；這一段不再有灰字「之後開放」。頁面的段落標題順序仍是：使用前檢查、運算環境、憑證、密碼與金鑰、個人、營運者後台、角色（老師／學生） | 自動：`T::test_personal_section_has_two_switches` |
| TC-002 | 作法 1；六項檢核 6（空狀態） | 功能 | 剛建立的新使用者（兩個旗標欄位都是空值） | 開 `GET /settings` | 逐步模式那列顯示狀態字「開」、符號「✓」、按鈕「關閉」（預設＝開） | 自動：`T::test_defaults_step_on_dev_off` |
| TC-003 | 作法 1；六項檢核 6 | 功能 | 同 TC-002 | 開 `GET /settings` | 開發模式那列顯示狀態字「關」、符號「—」、按鈕「開啟」（預設＝關） | 自動：`T::test_defaults_step_on_dev_off` |
| TC-004 | 作法 2 | 功能 | 已登入，開發模式為關 | 送出開發模式那列的表單（`POST /settings/personal`，key=dev_mode、on=1，合法 csrf） | 回應是轉址到 `/settings?notice=personal-saved`（英文使用者可多帶 `&lang=en`） | 自動：`T::test_turn_dev_on_persists_and_shows_banner` |
| TC-005 | 作法 1、2 | 功能 | TC-004 之後 | 重新開 `GET /settings` | 開發模式那列顯示「開」、「✓」、按鈕「關閉」；重新登入後仍是開 | 自動：`T::test_turn_dev_on_persists_and_shows_banner` |
| TC-006 | 作法 2；六項檢核 3 | 功能 | 剛存完一個開關，停在 `/settings?notice=personal-saved` | 看頁面頂端提示區 | 頂端提示區（既有 flash 位置）有一句「已儲存。」；沒有新增段落 | 自動：`T::test_turn_dev_on_persists_and_shows_banner` |
| TC-007 | 作法 1 | 功能 | 逐步模式為開、開發模式為關 | 送出 key=step_mode、on=0 | 轉址成功；再開頁面逐步模式為「關／—／開啟」；開發模式仍是「關」（兩個旗標各自獨立） | 自動：`T::test_set_each_flag_independently` |
| TC-008 | 作法 1 | 功能 | 開發模式為開 | 送出 key=dev_mode、on=0 | 轉址成功；再開頁面開發模式為「關／—／開啟」 | 自動：`T::test_turn_dev_off` |
| TC-009 | 作法 2、3；裁決 B；六項檢核 1 | 功能 | 已登入 | 看每個開關的表單，再按其中一個 | 每列是一個 `method="post"`、`action="/settings/personal"` 的表單，含隱藏欄 `csrf`、`key`、`on`、`lang`；按下去一次就存，中間沒有確認頁（沒有任何要再按一次「確認」的畫面） | 自動：`T::test_switch_forms_and_one_click_save` |
| TC-010 | 目標「每人一份」；作法 1 | 功能 | 使用者 A、B 兩個帳號，B 沒設定過 | A 開啟開發模式、關閉逐步模式 | B 開 `/settings` 仍是預設（逐步＝開、開發＝關）；A 重新開頁面看到自己的設定 | 自動：`T::test_banner_is_per_person` |
| TC-011 | 範圍：store.py；完成標準（遷移證明） | 例外 | 一個舊的資料庫：`users` 表還沒有 `step_mode`、`dev_mode` 兩欄，裡面已有使用者 | 用新程式開啟這個資料庫並以舊使用者登入看 `/settings` | 資料庫可以正常開啟、原有使用者資料沒掉；兩個新欄是空值，畫面顯示預設（逐步＝開、開發＝關）；之後能正常儲存開關 | 自動：`T::test_old_database_migrates_to_defaults` |
| TC-012 | 作法 1 | 功能 | 使用者 A、B；A 開了開發模式 | 以 A 的身分呼叫讀取動作 `get_my_settings` | 回傳只有 `step_mode`、`dev_mode` 兩個布林值，內容是 A 自己的；不含 B 的資料，也不接受指定別人 | 自動：`T::test_get_my_settings_reads_only_self` |

## User Story 2 — 開發模式開著時，每一頁頂端有醒目標示（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 作法 4；PLAN 第 145 行「開發模式＝國網不限 SU、畫面醒目標示」；裁決 2 | 功能 | 使用者已開啟開發模式 | 開首頁 `/` | 頁面有一條橫幅，文字逐字是「開發模式已開啟：國網運算不限制 SU」，並含符號「!」 | 自動：`T::test_turn_dev_on_persists_and_shows_banner` |
| TC-014 | 作法 4 | 功能 | 同 TC-013 | 開 `/settings` | 同樣的橫幅（同一句話、含「!」）出現 | 自動：`T::test_turn_dev_on_persists_and_shows_banner` |
| TC-015 | 作法 4 | 功能 | 同 TC-013，且有一個分析（run）頁可開 | 開某個 run 頁 | 同樣的橫幅出現 | 自動：`T::test_turn_dev_on_persists_and_shows_banner` |
| TC-016 | 作法 4「橫幅出現在每一頁（`_frame` 共用）」 | 功能 | 同 TC-013 | 開其他共用同一外框的已登入頁面：`/launch`、`/usage`、`/upload` | 每一頁都出現同樣的橫幅 | 自動：`T::test_banner_on_every_framed_page` |
| TC-017 | 作法 4「在 masthead 下方畫一條橫幅」 | 功能 | 同 TC-013 | 看 `/` 的 HTML 順序 | 橫幅在頁首（masthead）之後、三欄內容之前；每頁只出現一條 | 自動：`T::test_banner_position_and_count` |
| TC-018 | 作法 4；失敗先行測試 test_banner_not_shown_when_off | 功能 | 開發模式為關（含新使用者；以及開過再關掉的使用者） | 開 `/`、`/settings`、某 run 頁 | 三頁都沒有橫幅，頁面也不含「開發模式已開啟」這句話 | 自動：`T::test_banner_not_shown_when_off` |
| TC-019 | 目標「每人一份」；失敗先行測試 test_banner_is_per_person | 功能 | A 開了開發模式，B 沒開 | 以 B 的身分，依序開 `/`、`/settings`、run 頁（可在 A 開頁面之後立刻開，兩人交替各開幾次） | B 的每一頁都沒有橫幅，A 的每一頁都有（不會因為前一個請求是 A 而串到 B） | 自動：`T::test_banner_is_per_person` |
| TC-020 | 作法 4「符號、文字、顏色三者並用」；專長守則 | 功能 | 開發模式為開 | 看橫幅的 HTML | 同一個橫幅元素內同時有符號「!」、文字、以及顏色用的 class（不是只有 class） | 自動：`T::test_state_not_by_colour_alone` |
| TC-021 | 作法 4；裁決 4；專長守則（只用 DESIGN tokens） | 功能 | 開發模式為開 | 檢查橫幅用的 CSS 規則與整頁 CSS | 底色用 `--lost-bg`、文字與符號用 `--lost`；新增的 CSS 規則沒有新的顏色字面值（如 `#xxxxxx`）、沒有左側色條（`border-left` 之類）；CSS 仍只在那一個既有的 `<style>` 裡 | 自動：`T::test_banner_css_uses_only_existing_tokens` |
| TC-022 | 作法 4 | 功能 | 只關閉逐步模式，開發模式保持關 | 開 `/`、`/settings` | 沒有橫幅（橫幅只跟開發模式有關，逐步模式不觸發） | 自動：`T::test_step_mode_alone_shows_no_banner` |

## User Story 3 — 寫入被拒時的反應（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 六項檢核 2；裁決 7；test_post_refused_cases | 例外 | 已登入，開發模式為關 | `POST /settings/personal`，key=dev_mode、on=1，但 csrf 是錯的 | 回 400；頁內一句白話說明；開發模式仍為關 | 自動：`T::test_post_refused_cases` |
| TC-024 | 六項檢核 2；裁決 7 | 例外 | 沒有登入 | `POST /settings/personal`，key=dev_mode、on=1 | 被導向登入頁，或回 4xx（兩者都算）；之後該使用者的旗標沒有被改 | 自動：`T::test_post_refused_cases` |
| TC-025 | 作法 1；六項檢核 2 | 例外 | 已登入 | `POST /settings/personal`，key=`role`（不認得的鍵），其他合法 | 回 400；頁內一句白話；兩個旗標都沒變；資料庫沒有多出任何東西 | 自動：`T::test_post_refused_cases` |
| TC-026 | 裁決 7 | 例外 | 已登入 | `POST /settings/personal`，key=dev_mode、on=`maybe` | 回 400；頁內一句白話；旗標沒變 | 自動：`T::test_post_refused_cases` |
| TC-027 | 作法 1「無頻道（非 PAGE）拒絕，同 register_site_pipeline 的 K01 寫法」 | 例外 | 一個沒有頁面頻道的呼叫者（沒帶頻道、帶 None、帶其他字、帶長得像 PAGE 的物件） | 呼叫寫入動作 `set_my_setting(key, on)` | 每種情況都被拒絕（和既有頁面寫入動作同樣的拒絕方式），旗標沒變 | 自動：`T::test_set_my_setting_refuses_without_page_channel` |
| TC-028 | 六項檢核 2、3；專長守則（介面文字用白話） | 例外 | 寫入被拒或寫入失敗（例如存檔出錯） | 看被拒後的頁面 | 失敗句出現在頁面頂端提示區（既有位置，與「失敗」提示同一種樣式），不新增段落；句子說發生什麼事與下一步，不出現錯誤代碼或程式名詞 | 自動：`T::test_refusal_sentence_in_top_flash` |
| TC-029 | 六項檢核 2「欄位值不丟」 | 例外 | 一個旗標已設成某值（例如逐步模式關、開發模式開），然後送出被拒的請求（錯 csrf） | 看被拒後頁面上兩個開關 | 兩列仍顯示被拒前的狀態（逐步＝關、開發＝開），不被重設成預設 | 自動：`T::test_refusal_keeps_current_values` |

## User Story 4 — 憑證段只顯示「已設定／未設定」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 5；PLAN 第 145 行「憑證（只顯示「已設定」）」；DESIGN 畫面 12「credentials (token, 12 h)」 | 功能 | 使用者有一個未撤銷的存取權杖（用 `abf-platform token new` 建的） | 開 `/settings` | 憑證段有一行「存取權杖：已設定」，帶符號「✓」 | 自動：`T::test_credentials_say_set_or_not` |
| TC-031 | 作法 5；六項檢核 6（空狀態） | 功能 | 使用者沒有任何權杖 | 開 `/settings` | 憑證段有一行「存取權杖：未設定」，帶符號「—」 | 自動：`T::test_credentials_say_set_or_not` |
| TC-032 | 作法 5「是否有未撤銷的權杖」 | 功能 | 使用者的權杖都已撤銷 | 開 `/settings` | 顯示「存取權杖：未設定」 | 自動：`T::test_credentials_revoked_counts_as_not_set` |
| TC-033 | 作法 5；PLAN 第 145 行「只顯示」；既有 TC-034 的檢查 | 功能 | 使用者有權杖（已知權杖字串與它的雜湊） | 取整頁 HTML（`/settings`） | 整頁不含權杖字串，也不含它的雜湊 | 自動：`T::test_credentials_say_set_or_not` |
| TC-034 | 作法 5「該灰行保留」；`test_web_settings.py:257-266`（既有 TC-034 不退步） | 功能 | 任何使用者 | 看憑證段 | 仍有「請於終端機執行 abf-platform token new 建立。」這句，以及灰行「建立或撤銷權杖 之後開放」（原樣）；沒有表格 | 自動：`T::test_credentials_say_set_or_not`；`platform/tests/test_web_settings.py`（只加斷言，不刪） |
| TC-035 | 作法 5「不讀、不顯示權杖值與雜湊」 | 功能 | 使用者有多個權杖 | 看憑證段 | 只有一行已設定／未設定；沒有權杖清單、建立時間、編號、尾碼等其他資訊 | 自動：`T::test_credentials_show_no_token_details` |
| TC-036 | 作法 5；專長守則（狀態不只靠顏色） | 功能 | 有權杖與無權杖兩種使用者 | 看憑證那一行的 HTML | 兩種狀態都同時含符號（✓／—）與文字（已設定／未設定） | 自動：`T::test_state_not_by_colour_alone` |
| TC-037 | 作法 7；裁決 6 | 功能 | 有權杖與無權杖兩種使用者，`?lang=en` | 看憑證段 | 英文版顯示「Set」／「Not set」（含符號）；中間欄沒有中文字 | 自動：`T::test_english` |

## User Story 5 — 中英文、前端限制、手機與一致性（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 作法 7；裁決 6；test_english | 功能 | `GET /settings?lang=en`，新使用者與已開啟開發模式的使用者 | 看個人段 | 出現「Step-by-step mode」、「Development mode」、狀態字「On」／「Off」、按鈕「Turn on」／「Turn off」；中間欄（`mid()`）不含任何中文字 | 自動：`T::test_english` |
| TC-039 | 作法 4 | 功能 | 開發模式為開，`?lang=en` | 開 `/`、`/settings` | 橫幅文字逐字是「Development mode is on: NCHC compute has no SU limit」，含「!」；該頁中間欄與橫幅沒有中文字 | 自動：`T::test_english` |
| TC-040 | 裁決 7 | 功能 | 英文使用者送出一個開關 | 跟著轉址看頁面 | 頁面是英文，頂端有一句成功提示，且沒有中文字（句子內容不鎖定） | 自動：`T::test_english_notice_after_save` |
| TC-041 | 作法 2；六項檢核；專長守則（前端限制） | 功能 | 開發模式開／關各一次 | 取 `/settings`、`/` 的 HTML 與回應標頭 | 整頁無 `<script`、無 `style=`、只有一個 `<style>`、沒有外部網址請求；CSP 標頭與修改前逐字相同（`default-src 'none'; style-src <sha256>; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`，雜湊依新 CSS 重算） | 自動：`T::test_no_script_no_inline_style`；`test_web_settings.py:330`；`test_web_v2_skeleton.py:404` |
| TC-042 | 作法 1、8；範圍：既有測試 | 功能 | 已登入 | 取 `/settings` | 段落標題仍是七段、順序不變（使用前檢查、運算環境、憑證、密碼與金鑰、個人、營運者後台、角色（老師／學生）），沒有增減；英文版前三段不變 | 自動：`test_web_settings.py:89`、`:316`；`test_web_board.py:962` |
| TC-043 | 裁決 5 | 功能 | 本片新增的所有中文字串（橫幅、已設定／未設定、開啟／關閉、已儲存。及其他新句） | 跑既有的用字檢查 | `test_web_wording_sweep.py` 沒有被修改，且全綠（沒有撞到禁字表如「這個」「一下」「還沒有」） | 自動：`platform/tests/test_web_wording_sweep.py` |
| TC-044 | 作法 2；專長守則 | 功能 | 開／關兩種狀態各一列 | 看個人段 HTML | 每一列都同時含符號（開＝✓、關＝—）與狀態字（開／關），不是只靠 class 顏色 | 自動：`T::test_state_not_by_colour_alone` |
| TC-045 | 專長守則（鍵盤操作） | 功能 | 已登入 | 看個人段 HTML | 每個開關是原生的 `<button type="submit">`（放在 form 裡），可以用 Tab 走到、Enter 按下；沒有用 JS 模擬 | 自動：`T::test_switches_are_native_buttons` |
| TC-046 | 六項檢核 5（手機寬度） | 功能 | 390 寬的畫面 | 跑 `scripts/dev/check_settings_mobile.py`（含個人段兩列與開發模式橫幅） | 沒有橫向捲動；開關按鈕的點擊高度不小於頁面上既有按鈕 | 自動：`scripts/dev/check_settings_mobile.py` |
| TC-047 | 專長守則；裁決 8 | 功能 | 起得來的應用程式 | 跑 `scripts/dev/ui_check.py`（1440／390 寬 × 中／英，共 4 張截圖，含開發模式橫幅畫面） | 4 張截圖產生；axe 無障礙掃描沒有 serious 或 critical | 自動：`scripts/dev/ui_check.py` |
| TC-048 | 範圍：test_web_parity.py | 功能 | 新增 `set_my_setting`、`get_my_settings` 兩個動作 | 跑 parity 測試 | `WEB_ONLY` 內有這兩個動作，`set_my_setting` 的理由寫「網頁專用，個人旗標，無 MCP 工具」；parity 全套綠 | 自動：`platform/tests/test_web_parity.py` |
| TC-049 | 作法 1；範圍：test_actions_layer.py | 功能 | 同上 | 列出 MCP 工具 | `set_my_setting` 不是 MCP 工具（AI 不能替人改這兩個旗標）；`PAGE_WRITE_NAMES` 含 `set_my_setting` | 自動：`platform/tests/test_actions_layer.py`（`test_srp_k01_*`） |

## 不在範圍（本片明講不做的事）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 「不做」第 3 條；作法 4「本片只標示，不改任何 SU 判斷」 | 不在範圍 | 同一使用者，先關再開開發模式 | 比較 `/usage`（費用頁）在兩種模式下的內容 | 除了橫幅之外，頁面內容（SU 額度、數字、提示）完全相同；沒有任何「不限 SU」的實際判斷被加進去 | 自動：`T::test_dev_mode_changes_no_su_judgement` |
| TC-051 | 「不做」第 3 條；裁決 D | 不在範圍 | 同一使用者，逐步模式開與關 | 比較 `/launch`、`/` 在兩種狀態下的內容 | 除了設定頁的開關列之外，其他頁面內容相同；逐步模式目前只存旗標、只顯示 | 自動：`T::test_step_mode_changes_nothing_else` |
| TC-052 | 作法 6；裁決 A；test_ai_key_section_unchanged；DESIGN 畫面 12「Secrets (AI model key…; browser only)」 | 不在範圍 | 任何使用者 | 看「密碼與金鑰」段 | 這一段和修改前逐字相同：AI 模型金鑰的灰字項目（含「之後開放」）與「金鑰僅儲存於您的瀏覽器，不會傳送至平台。」；英文版同樣原樣 | 自動：`T::test_ai_key_section_unchanged` |
| TC-053 | 作法 8；`test_web_settings.py:105、172` | 不在範圍 | 任何使用者 | 看「使用前檢查」 | 四步不變；第 4 項 AI 金鑰仍是「—」加「之後開放」 | 自動：`platform/tests/test_web_settings.py` |
| TC-054 | 裁決 A、裁決 3；維護者原話第 9 點「只要在設定讓使用者可以放金鑰」；PLAN「模型金鑰只存瀏覽器」 | 不在範圍 | 任何使用者 | 看 `/settings` 的 HTML | 沒有任何輸入模型金鑰的欄位（無 AI 金鑰的 `<input>`）、沒有 localStorage 相關內容、仍然無 `<script`；也就是本片沒有悄悄做出金鑰輸入（此原話尚未被滿足，留待 012a-2） | 自動：`T::test_no_model_key_input` |
| TC-055 | 「不做」第 4 條；DESIGN 畫面 12「Operator panel and Roles as dashed "coming later"」 | 不在範圍 | 任何使用者 | 看 `/settings` | 沒有建立或撤銷權杖的按鈕或表單；「營運者後台」「角色」兩段仍是灰字「之後開放」，沒有新功能 | 自動：`T::test_later_items_stay_grey` |
| TC-056 | 「不做」第 2 條；裁決 C | 不在範圍 | 跑 parity 測試 | 檢查 `OWED` | `OWED` 集合沒有縮小（仍含 `get_compute_env`、`list_agents`，其餘不變）；沒有新增這兩個動作的網頁路由；`test_tcs07_owed_is_written_out` 沒被修改 | 自動：`platform/tests/test_web_parity.py` |
| TC-057 | 「不做」第 5 條；作法 8；維護者原話第 2 點（右側對話框） | 不在範圍 | 任何使用者 | 看左欄、右欄、運算環境表、登記管線表單 | 左欄、右欄、運算環境表、登記管線表單和修改前一樣；既有測試（`test_web_settings.py`、`test_web_settings_register.py`、`test_web_settings_ce_mobile.py`、`test_web_v2_skeleton.py:202`、`test_web_board.py:317`）只改計畫列出的預期、不刪案例且全綠 | 自動：上列既有測試檔 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 | Safety Net：憑證「never printed」（頁面不印權杖） | 功能 | 使用者有權杖 | 取 `/settings` 與 `/` 全頁 HTML | 沒有權杖字串，也沒有它的雜湊 | 自動：`T::test_credentials_say_set_or_not` |
| TC-059 | Safety Net：平台不存憑證（`test_secrets.py`） | 功能 | 開關各按過一次 | 比較 `users` 表與資料庫 | 新增的只有 `step_mode`、`dev_mode` 兩個整數欄；沒有任何權杖、金鑰或憑證被寫進新欄或新表 | 自動：`T::test_store_adds_only_two_integer_columns` |
| TC-060 | Safety Net：寫入必須走人操作的頻道（`test_actions_layer.py` tcb04–tcb08、`test_srp_k01_*`） | 功能 | 新增 `set_my_setting` | 跑 `test_actions_layer.py` | 既有頻道規則的測試全綠；`set_my_setting` 只有網頁路由會呼叫，沒有從任何 MCP 或 CLI 路徑被呼叫 | 自動：`platform/tests/test_actions_layer.py` |
| TC-061 | 憲法 I.2 與送出規則：只有確認過的啟動才會送出工作 | 功能 | 開關各按幾次 | 比較工作表（jobs）與待確認請求前後 | 沒有新增任何工作、沒有新增待確認請求（開關不啟動工作、不花錢） | 自動：`T::test_flags_start_no_jobs` |
