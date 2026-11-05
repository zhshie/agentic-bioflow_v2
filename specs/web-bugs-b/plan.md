---
id: web-bugs-b
title: 網頁四個畫面缺陷（#338 費用頁中文註記與月份標題、#341 run 頁標題列資訊行、#342 右欄寬度、#343 手機寬度可點區與檔名斷字）
tier: C
kinds: ui
risk: M
lane: L6-web
branch: fix/web-bugs-b
base: v3
review: maintainer
source: GitHub zhshie/agentic-bioflow_v2 issues #338、#341、#342、#343（2026-11-04，abf-test，run 876a9a8b617c67f1）；DESIGN.md Skeleton／Constraints／畫面 11
---

# web-bugs-b

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/web-bugs-b/plan.md`。
> **2026-11-05 查 origin/v3（b00263c6，已先 `git fetch`）：四個 issue 都還是 OPEN，v3 上都沒修，一個都沒丟。**
> **車道順序：`web-bugs-a`（同一批網頁檔，計畫由另一位 agent 寫）與本計畫都改 `web_board.py`、`web.py` 與同一批釘 CSS 長度／頁面雜湊的測試，所以本計畫必須排在 L6-web 車道、`web-bugs-a` 合併「之後」才跑；開工前先 `git merge origin/v3`，所有雜湊與長度重算，不要沿用本檔舊值。**
> 標「executor to confirm still reproduces」者：寫計畫時只讀了程式碼、沒有開瀏覽器重現；executor 先在 `--start` 的暫時平台上確認現象還在，再動手。

## 目標
四件事，使用者看到的樣子：
1. 費用頁（`/usage`）中文版的 SU 卡片註記，顯示的是「分區 ngs8g 沒有 SU 係數」這種原因，不是任務名稱；看過去月份時，卡片標題寫那個月，不寫「本月」。
2. run 頁標題列有一行「管線 版本 · 站台 · 開始 · 最後更新」，執行資訊分頁也看得到這些欄位。
3. 版面右欄寬度照 DESIGN.md：寬螢幕 360 px、≤1200 px 時 300 px。
4. 手機寬度（390 px）的結果階段輸出頁：可點的連結至少 24×24 CSS px；檔名不再在表格中間被切成一兩個字元。

## 維護者原話（verifier 出題用）
以下是四個 issue 的正文要點逐字（出題時每一條至少一個案例），再加 DESIGN.md 原文。

**#338**「web: 費用頁 — 中文版 SU 卡片註記顯示任務名稱，過去月份仍標「本月」」
> 中文「國網 SU（本月）」卡片的註記顯示 `task NFCORE_AMPLISEQ:AMPLISEQ:RENAME_RAW_DATA_FILES`，英文版同一張卡顯示 `no SU factor for partition ngs8g`。
> `/usage?month=2026-10` 時，卡片標題仍是「國網 SU（本月）」與「雲端已用（本月）」（英文 `this month`）。
> 預期：中文顯示對應 `no SU factor for partition ngs8g` 的中文原因，不是任務名稱；標題與所顯示的月份一致。
> 依據：DESIGN.md「Constraints」（"every screen exists in English"）、「Screens 11. Cost」。

**#341**「web: run 頁標題列 — 缺少「管線版本 · 站台 · 開始 · 最後更新」資訊行」
> 標題列只有名稱＋狀態徽章（＋「更多」）。管線與版本只在結果階段的「來源紀錄」看得到；「執行資訊」分頁只有 id、名稱、狀態、開始、結束，沒有管線版本與站台。
> 預期：標題列含 `pipeline revision · site · started · last update`。依據：DESIGN.md Skeleton／Middle。頁面：`/?run=876a9a8b617c67f1`、`/?run=876a9a8b617c67f1&stage=running&tab=info`。

**#342**「web: 版面 — 右欄寬度 320／288 px，與 DESIGN.md 規定的 360／300 px 不符」
> 1440 px：左 272、右 320（規格 360）。1100 px（≤1200）：左 232、右 288（規格 300）。CSS 為 `grid-template-columns:272px minmax(0,1fr) 320px`，≤1200 px 時 `232px … 288px`。
> 預期：DESIGN.md Skeleton「Right column 360px」；「≤1200px: 232 / fluid / 300.」；「Where this file and the drafts differ, this file wins」。
> issue 另註：若維護者是刻意改成 320／288，則應改 DESIGN.md（不確定哪一邊）。

**#343**「web: 結果階段輸出頁（390 px）— 多個可點連結小於 24 px，檔名在表格中途斷字」
> 連結高 16–20 px：中 29×20、EN 35×20、輸出表的資料夾連結與「下載」、「報告」「MultiQC 報告」、「重新讀取」、「← 上一階段」「下一階段 →」、「開啟確認頁」。36 個可點元素中 15 個在某個方向小於 24 px。
> 檔名在字中斷行（`cutadap`／`t`、`phylose`／`q`、`pipelin`／`e_info`、`overall`／`_summar`／`y.tsv`），且沒有水平捲動。
> 預期：可點目標 ≥24×24 CSS px（WCAG 2.2 SC 2.5.8，外部標準）；檔名不要斷成單字元碎片（水平捲動或縮窄其他欄）。頁面：`/?run=876a9a8b617c67f1&stage=results&tab=outputs`；其他 run 頁與 `/usage` 的「← 上一月」也偏小。

**DESIGN.md 原文**（Skeleton）：
> Middle (fluid): title row (name, state pill, `pipeline revision · site · started · last update`) … Right column 360px … ≤1200px: 232 / fluid / 300. ≤900px: one column, order middle → right → left.

DESIGN.md Constraints：single stylesheet, no inline style, every screen exists in English。DESIGN.md 開頭：「Where this file and the drafts differ, this file wins」。

## 範圍：檔案
只准改這些檔：
- `platform/abf_platform/web_cost.py`：`STRINGS` 新增依月份的字串；`_reason` 改寫；`_cards`／`_table`／`_middle` 傳入 `month`、`this_month`。
- `platform/abf_platform/web_board.py`：`STYLE`（右欄 360／300、≤900 px 的最小可點區、輸出表檔名不斷字）；`_run_page` 的 `.head` 內加資訊行；資訊分頁加列；`STRINGS` 加對應 zh／en 字串。
- `platform/abf_platform/web.py`：**只動 `read_run`**（:~515–527）：把管線、版本、站台放進 view。
- `docs/TESTING.md`：加「390 px 手動檢查」步驟（`scripts/dev/ui_check.py`，不改該腳本）。
- 新測試：`platform/tests/test_web_bugs_b.py`。
- 被釘住、需同步改預期的既有測試（只改預期，不刪案例，ledger 逐條列舊→新與理由）見下方「允許改動的斷言」：`test_web_board.py`、`test_web_cost.py`、`test_web_nano4_path.py`、`test_clean_page.py`、`test_results_files.py`、`test_settings_pick_installed.py`、`test_web_resume_edit.py`，必要時 `test_su_usd.py` 與標題列相關測試。
- 不碰：`su.py`、`actions/__init__.py`、`status.py`、`web_finished.py`（只讀取其既有輸出）、`dev-queue.json`、`web-bugs-a` 負責的部分。

### 允許改動的斷言（grep 自 origin/v3；行號合併 web-bugs-a 後會漂移，以內容為準）
**必須改：**
- `test_web_board.py:211-212`（`test_tcs11_s12_s13_layout_css`）：釘 `320px`／`288px` → 改 `360px`／`300px`。同區其他檢查不動。
- `test_web_cost.py:226`：`/usage?month=2099-01` 斷言含「本月尚無分析」→ 改為斷言含該月份的空表句（見作法 1.3），並斷言「本月」不在標題。
- STYLE 長度與雜湊（任何 CSS 改動都會變，**重算後填，不要猜**）：`test_web_nano4_path.py:545`（`len(web_board.STYLE) == 11475`）；`test_clean_page.py:158-163`（BASE_CONFIRM／BASE_EXPIRED／BASE_POST／BASE_BOARD 頁面雜湊）與 `BASE_STYLE '0b5b317c1dab4ca0'`（:468 檢查處）；`test_results_files.py:695`（`STYLE_SHA256`）；`test_settings_pick_installed.py:692`（`BASE_STYLE_SHA`）；`test_web_resume_edit.py:612`（字面 `0b5b317c1dab4ca0f958e92cd6a0fb7b03185461f29854ea4f6f83531823ae00`）。
**必須維持不變（目前月份字串一字不改）：**
- `test_web_cost.py:148`（卡片 `["國網 SU（本月）", "雲端已用（本月）", "雲端上限", "雲端剩餘"]`）、`:349-351`（「— 本月尚無分析」與 "No analyses this month"，英文 `no_cjk`）、`:190/215/525` 與 `test_web_wording_sweep.py:489`（「另有 N 個分析無法計算」）。
- `test_su_usd.py:370`（「待處理：本月雲端額度已用盡」）、`:412`、`:417`（「— 本月尚無分析」）。
- `test_web_wording_sweep.py:261-263`（`empty`／`bad_month`／`no_reason`／`unknown_runs`／`note`／`usd_note`／`action` 字串）、`:478`、`:480`。
**結構釘（資訊行必須在 `.head` 內、不加符號與禁用詞）：** `test_web_fixes_1.py:24`（`head_of` 正規式）、`test_web_status_squares_3.py:42`（`status_areas`）、`test_web_board.py:684/756/1270`（`<h1>…`）。
**資訊分頁釘（新增列不得破壞）：** `test_web_board.py:545/1284/1296`、`test_web_running.py:284-328`（含 :291 英文資訊分頁 `no_cjk`）、`test_web_results_outputs.py:92/106`、`test_results_files.py:590`。
**類別必須在 STYLE 內：** `test_web_nano4_path.py:546-557`（中欄用到的 class 都要在樣式表；禁 `style=`、`<script`；禁用詞掃描）、`test_web_resume_edit.py:524`。

## 作法
### 1. #338 費用頁（`web_cost.py`）
1.1 **原因文字**：`su.py` 的原因長這樣：`"task <名稱>: 分區 X 沒有 SU 係數 (no SU factor for partition X)"`，多段以 `"; "` 相接。`_reason(t, lang, reasons)` 改成：取 `reasons[0]` → 去掉開頭的 `task <名稱>: `（以第一個 `": "` 切，只在開頭是 `task ` 時切）→ 取第一段（`"; "` 前）→ 中文：去掉結尾括號 `(…)`（結尾錨定）；英文：取結尾括號內文（沿用 `_ENGLISH_TAIL`，仍須無 CJK，否則 `no_reason`）→ 空字串則 `no_reason`。**中英文顯示同一件事；中文文字不得含任務名稱。**
1.2 **卡片標題依月份**：新增 `card_su_month`（zh「國網 SU（%s）」、en `_HPC + " SU (%s)"`）、`card_used_month`（zh「雲端已用（%s）」、en "Cloud used (%s)"），`%s` 為 `YYYY-MM`。`month == this_month` 時照舊用 `card_su`／`card_used`（字串一字不改）；其他月份（含未來月）用依月份版。
1.3 **空表句與待處理句**：新增 `empty_month`（zh「— %s 尚無分析」、en "— No analyses in %s"，英文不得含 CJK）；非本月時 `_table` 用它。`action`（「待處理：本月雲端額度已用盡」）是本月的待辦，非本月不顯示（executor 先確認 `_middle` 目前是否只在本月算 `used_up`；是就不動，不是就加條件）。
1.4 `_cards`、`_table` 簽章加 `month`、`this_month`；`render_usage`、`current_month(now)` 簽章不變。
1.5 新字串進禁用詞掃描與 zh／en 對等（英文頁無 CJK）。

### 2. #341 標題列資訊行（`web_board.py`、`web.py`）
2.1 資料：`web.py` `read_run` 呼叫既有 `actions.launch_prefill(platform_path, view["name"], caller=caller)`（`read_finished` :538 已這樣用）；`found` 且 `kept` 時，把 `pipeline`、`revision` 放進 `view["pipeline"]`、`view["revision"]`；站台用既有 `view["compute_env"]`，沒有時用 prefill 的 `ce_name`。外來 run（`found: False`）與已忘記（`kept: False`）→ 這些欄位不放（顯示「—」）。**不改 `actions/__init__.py`、`status.py`。**
2.2 畫面：`_run_page` 的 `<div class="head">` 內、徽章與「更多」之後，加 `<p class="meta">管線 版本 · 站台 · 開始 · 最後更新</p>`（欄位之間用 ` · `）。「開始」用既有 `_time(started_at)`；「最後更新」取 `last_message_at`，沒有就 `ended_at`，再沒有就 `started_at`；任一值缺就顯示「—」。`render_board` 常被測試用手作的 run dict 呼叫，**一律 `.get`，缺鍵不得丟例外**。
2.3 CSS：`.head .meta{flex-basis:100%;margin:0;…}`（用既有 token 與色，不加新顏色），讓資訊行獨占一行；這是 CSS 改動，併入下面的重釘。
2.4 資訊分頁（`tab_body`）在既有列後加四列：管線、版本、站台、最後更新（沿用 `<dl class="fields">`）。新字串 zh／en 各一，英文無 CJK，過禁用詞掃描。標籤用既有詞：`started`「開始」、站台沿用 `web_finished.py` 的 `ce` 同義詞（executor 查現用字，不自造）。
2.5 判斷資訊行存在的測試只看 `.head` 內有 `class="meta"` 與四個值，不釘整行字面，避免之後改字就紅。

### 3. #342 右欄寬度（`web_board.py` CSS）
DESIGN.md 勝出（它自己寫「this file wins」）：`.wb` 的 `320px` → `360px`；`@media (max-width:1200px)` 的 `288px` → `300px`。左欄 272／232 不動，≤900 px 單欄規則不動。issue 的另一個可能（維護者刻意改成 320／288 → 改 DESIGN.md）**不採用**，列在 ledger 與 PR 說明供維護者推翻。

### 4. #343 手機可點區與檔名（`web_board.py` CSS）
4.1 只在 `@media (max-width:900px)` 內加（寬螢幕外觀不變，風險小）：`.switch a,.pager a,.views a,.rtabs a,.tbl a,.otbl a,.ostat a,.rail a` 設 `display:inline-flex;align-items:center;min-height:24px;min-width:24px`（連結行內補 `padding` 不改斜度；`.pager` 兩個鍵保持左右兩端）。「重新讀取」在 `.ostat` 內，麵包屑（`_crumbs`）也要過。
4.2 輸出表：拿掉 `.otbl code` 的 `overflow-wrap:anywhere`，改 `overflow-wrap:normal;word-break:keep-all`；表格外框（或 `.otbl` 本身在 ≤900 px）給 `overflow-x:auto`，讓長檔名靠水平捲動而不是斷成單字元。`.tbl{table-layout:fixed}`（:257）在 ≤900 px 的 `.otbl` 改回 `auto`。其他表（`.tbl th,.tbl td` 的 `overflow-wrap:anywhere`）不動。
4.3 不加 inline style、不加 `<script`；新規則放進同一個 `STYLE` 字串。
4.4 `/usage` 的「← 上一月」連結若在 ≤900 px 仍小於 24 px，用同一條規則涵蓋（executor to confirm still reproduces）。

### 5. CSS 重釘（最後做一次）
全部 CSS 改完、`git merge origin/v3`（含 web-bugs-a）之後，再重算並更新「必須改」清單內的長度與雜湊。ledger 逐條列舊值→新值與重算指令；不得為了讓測試過而改別的斷言。

## 六項必填檢核（ui）
1. 沒新顏色、沒新字型：只用 DESIGN.md token 與既有 class。
2. 無 inline style、無 `<script`：CSP `style-src sha256` 由 `style_source()` 自 `STYLE` 算出，STYLE 改了雜湊自動跟著，測試值才要重釘。
3. zh／en 對等：每個新字串兩語都有，英文頁面過 `no_cjk`。
4. 用字：制式通知，過禁用詞掃描（不口語，如「選用這個樣本」「用過的」之類不得出現）。
5. 寬度：1440 與 390 各看 zh／en；右欄 360／300 實測；390 px 無水平溢出（輸出表除外，它自己捲動）。
6. 可及性：`ui_check.py` 的 axe 無 serious／critical；≥24×24 在 390 px 逐一量。

## 失敗先行測試
新檔 `platform/tests/test_web_bugs_b.py`，先寫、改程式前必須紅。測試只用 `render_usage`、`render_board`、`web_board.STYLE`，不開瀏覽器（CI 沒有 Chromium）。
- `test_338_zh_reason_has_no_task_name`：reasons=`["task NFCORE_AMPLISEQ:AMPLISEQ:RENAME_RAW_DATA_FILES: 分區 ngs8g 沒有 SU 係數 (no SU factor for partition ngs8g)"]`；zh 卡片註記含「分區 ngs8g 沒有 SU 係數」、不含 `NFCORE_AMPLISEQ`、不含 `task `。
- `test_338_en_reason_unchanged`：同資料 en 註記為 `no SU factor for partition ngs8g`，無 CJK。
- `test_338_reason_fallbacks`：空 reasons → `no_reason`；只有 `task X: ` 無原因 → `no_reason`；多段 `"; "` 只取第一段；英文括號內含 CJK → `no_reason`。
- `test_338_past_month_titles_show_month`：`month=2026-10`、this_month=`2026-11`，zh 含「國網 SU（2026-10）」「雲端已用（2026-10）」且不含「（本月）」；en 含 `(2026-10)`、不含 `this month`、無 CJK。
- `test_338_current_month_titles_unchanged`：month==this_month 時仍是「國網 SU（本月）」「雲端已用（本月）」／`this month`。
- `test_338_empty_month_sentence`：非本月空表 zh「— 2099-01 尚無分析」、en "No analyses in 2099-01"；本月仍「— 本月尚無分析」。
- `test_341_head_has_meta_line`：run 頁 `.head` 內有 `class="meta"`，含 pipeline、revision、站台、開始時間、最後更新；zh／en 都有，en 無 CJK。
- `test_341_meta_line_missing_values_dash`：run dict 缺 pipeline／revision／last_message_at 也不丟例外，缺的顯示「—」。
- `test_341_info_tab_has_new_rows`：資訊分頁含管線、版本、站台、最後更新四列。
- `test_341_read_run_adds_pipeline_revision`：用 `kept` 的 prefill，`read_run` 的 view 有 `pipeline`、`revision`；外來／忘記的 run 沒有且不丟例外。
- `test_342_right_column_360_300`：`STYLE` 含 `272px minmax(0,1fr) 360px` 與 `232px minmax(0,1fr) 300px`，不含 `320px`／`288px` 的欄寬規則。
- `test_343_mobile_min_target_rules`：解析 `STYLE` 的 `@media (max-width:900px)` 區塊，含 `min-height:24px` 與涵蓋 `.pager a`、`.rtabs a`、`.otbl a`、`.ostat a`、`.switch a` 的規則。
- `test_343_otbl_filename_not_anywhere`：`.otbl code` 規則不再含 `overflow-wrap:anywhere`；≤900 px 有 `overflow-x:auto`。
- `test_style_no_inline_no_script`：頁面無 `style=`、`<script`。
紅綠紀錄：ledger 貼改前這些測試紅、改後綠。

## 完成標準（done when）
- 上列新測試全綠；「必須維持不變」的既有斷言一字未動且仍綠；「必須改」的斷言只改上面列的那些，且 ledger 有舊→新與理由。
- `git diff --stat` 只含「範圍：檔案」列的檔。
- 在 `ui_check.py --start`（1440／390 × zh／en，pages 含 `results`、`usage`）axe 無 serious／critical；ledger 貼摘要。附 `/usage?month=<過去月>` 與 `?stage=results&tab=outputs`（390 px）截圖（risk M 須附截圖）。
- 手動量：390 px 結果輸出頁所有可點元素 ≥24×24；檔名不再斷成單字元。
- `docs/TESTING.md` 有 390 px 手動檢查步驟。
- 已在 `web-bugs-a` 合併後的基底上重算並更新全部 STYLE 長度與頁面雜湊。

## 環境事實
- 全部是純函式 HTML：`web_board.py` 的單一 `STYLE` 字串（`style_source()` 給 CSP 雜湊），沒有 inline style、沒有 `<script`。CSS 位置（v3，以 grep 為準）：`.wb` 版面 :198-199；≤900 px 區塊 :285；`.head` :215；`.views` :207；`.pager` :234；`.rtabs a` :255；`.tbl` :257-258；`.otbl code`／`.ostat` :260；`.fields` :249-250。
- `_run_page` :770-809；資訊分頁 `tab_body` :~752-757；`_outputs_body` :686-717；`_time(iso)` 台北時間 `MM-DD HH:mm`，壞值回「—」。
- `su.py` 原因格式：`"task %s: %s"`，多段 `"; "`；`"分區 %s 沒有 SU 係數 (no SU factor for partition %s)"`、`"缺 cpus (no cpus)"`、`"費率檔讀不到 (the rates file cannot be read)"`、`"找不到站點 %s 的費率 (no rates for site %s)"`；任務標籤 `"task %s" % (name or taskId or index)`。
- `launch_prefill`（`actions/__init__.py`:284）三種回傳：外來 `{"found": False, "kept": False}`；已忘記 `{"found": True, "kept": False, "launched_at": …}`；保留 `kept: True` 並帶 `pipeline`、`revision`、`ce_name`、`params`。`status._view` 沒有 pipeline／revision／site。
- WCAG 2.2 SC 2.5.8（24×24 CSS px）是外部標準，不在 DESIGN.md。
- `scripts/dev/ui_check.py`（`--start` 起暫時平台並種一個成功的 run）與 `docs/TESTING.md` 在 origin/v3 都有；CI 沒有 Chromium，所以瀏覽器檢查是閱卷的手動步驟，不進 pytest。
- **PITFALLS 已查，無相符項**（`docs/PITFALLS.md` 沒有 web_board／web_cost／CSS／`/usage`／手機版的條目；`docs/solutions/` 不存在）。唯一鬆散相關：#51「設計類計畫必須帶專長守則段」——本檔檔尾已留該段標題，由 `build-dev-plans.py` 貼上。
- 已知環境紅（README 通例）：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 只剩這一條紅視同綠。

## 不做
- 不改 `su.py` 的原因格式、不改 `actions`／`status.py`（#341 的資料靠既有 `launch_prefill`）。
- 不改 DESIGN.md（#342 採規格為準；若維護者要 320／288，另開任務改 DESIGN.md 與測試）。
- 不把 24 px 規則套到 >900 px 的桌面版面（issue 只量 390 px）；不重做 `/usage` 之外的其他頁。
- 不改 `scripts/dev/ui_check.py`；不加 Playwright 進 pytest。
- 不處理 `web-bugs-a` 的項目；不碰 `dev-queue.json`。

## 裁決
1. **#342 以 DESIGN.md 為準**（360／300）。理由：DESIGN.md 自述「this file wins」，且 issue 也把它當規格。若維護者推翻，只需把兩個數字與測試改回、並改 DESIGN.md。
2. **#343 的 24 px 只套 ≤900 px**。理由：issue 在 390 px 量到；桌面版面不動可避免連帶改版與更多雜湊變動。WCAG 2.5.8 是外部標準，未見維護者逐字採納——列為待維護者確認。
3. **#341 管線／版本來自 `launch_prefill`，不改狀態層**。外來或已忘記的 run 顯示「—」，不是空白也不是錯誤。
4. **#338 非本月的空表句改成月份版，本月句不動**；因此 `test_web_cost.py:226` 是唯一被允許改預期的 cost 斷言。
5. **CSS 重釘只做一次、在合併 web-bugs-a 之後**，值由指令重算。

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
- **實際跑起來看（ACCEPTANCE，2026-11-03 加）**：用 `webapp-testing` 的 `with_server.py` 把真正的應用程式起起來，再用 Playwright 驗。腳本路徑 `G:/我的雲端硬碟/謝馬爾/.claude/skills/webapp-testing/scripts/with_server.py`，**先跑 `--help`** 看用法（把它當黑盒子用，不要先讀原始碼）；啟動指令與通訊埠寫在計畫裡。
  - repo 已有 `scripts/ui_check.py` 就直接跑它：1440／390 寬 × zh／en 共 4 張截圖，加 axe-core 無障礙掃描；**axe 出現 serious 或 critical 一律 FAIL**。
  - repo 還沒有 `ui_check.py`：verifier 自己用 Playwright（經 `with_server.py`）拍同樣 4 張截圖；axe 沒跑就標 **axe：UNVERIFIED**，並寫明缺什麼。
  - 截圖只能存到 repo 之外或 `.gitignore` 排除的資料夾，**絕不存進 Drive 工作區**；報告只貼路徑與張數。
  - 起不了應用程式（缺依賴、埠被占）標 UNVERIFIED 並寫明需要什麼，不改以靜態 HTML 當作通過。
