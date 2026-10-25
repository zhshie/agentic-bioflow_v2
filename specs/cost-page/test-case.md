# 測試案例：費用頁 /usage（cost-page）

**規格**：`specs/cost-page/plan.md`（本任務沒有獨立 spec.md，計畫即規格；維護者原話引自計畫「維護者原話」與 `DESIGN.md` 畫面 11）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：「國網」＝國家高速網路中心的 HPC（NCHC）；「SU」＝國網的計價單位；「雲端」＝Google Batch；「抬頭」＝每頁最上面那條深色列；「卡」＝頁面上的一格摘要方塊；「制式通知」＝平台固定格式的提示框。表中提到的 `co01`…`co12` 是計畫列的測試名（`platform/tests/test_web_cost.py` 的 `test_coNN_*`）；執行者另加的測試在 `test_web_cost.py` 內以 TC 編號註記。

維護者原話（逐字，作為預期結果的依據）：

1. DESIGN.md 畫面 11：「**Cost** (`#cost`, from the masthead meter): cards NCHC SU / Cloud used / cap / remaining; "never converted" line; Action-needed notice when a launch would exceed the cloud cap (use NCHC / wait for reset); per-analysis table with status Running / Reconciled / Estimate, bill pending.」
2. 10-18 裁示：「雲端費用照 10-18 裁示：顯示雲端自己的幣別（美元）、不換算、每人每月上限由管理者開帳號時設」
3. 「先把功能做起來吧，以後再改美觀」
4. 「做成產品英文版面是必須的」

## User Story 1 — 看到本月國網 SU 與雲端用量（四張卡＋固定說明）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 頁面 2；原話 1「cards NCHC SU / Cloud used / cap / remaining」 | 功能 | ann 已登入，本月有分析 | 開 `GET /usage` | 回應 200；中欄有四張卡，標題依序為「國網 SU（本月）」「雲端已用（本月）」「雲端上限」「雲端剩餘」 | 自動：co01 |
| TC-002 | 頁面 3；原話 1「"never converted" line」；原話 2 | 功能 | 同上 | 看固定說明 | 出現整句「雲端費用以美元顯示，不換算新台幣；國網以 SU 計。數字是依執行紀錄估算，略低於實際帳單。」 | 自動：co01 |
| TC-003 | 頁面 2；co02 | 功能 | 本月有兩個已結束的國網分析，SU 分別為 5.10 與 7.20 | 開 `/usage` | 「國網 SU（本月）」卡的數字是「12.30」（兩位小數） | 自動：co02 |
| TC-004 | 作法「不給部分和」；co02 | 例外 | 本月兩個國網分析，其中一個沒有用量紀錄、算不出 SU | 開 `/usage` | 「國網 SU（本月）」卡的數字是「—」；不是 5.10、不是 7.20（部分和），也不是「0.00」 | 自動：co02 |
| TC-005 | 頁面 2「None → 「—」＋卡內小字原因第一條」；co02 | 例外 | 同 TC-004 | 看同一張卡 | 卡內有小字，內容是算不出原因清單的第一條 | 自動：co02 |
| TC-006 | 頁面 2；co03 | 功能 | ann 雲端上限 50、本月雲端已用 12.34 | 開 `/usage` | 「雲端已用（本月）」卡的數字是「US$ 12.34」 | 自動：co03 |
| TC-007 | 頁面 2；co03 | 功能 | 同 TC-006 | 看上限卡 | 「雲端上限」卡的數字是「US$ 50.00」 | 自動：co03 |
| TC-008 | 頁面 2；co03 | 功能 | 同 TC-006 | 看剩餘卡 | 「雲端剩餘」卡的數字是「US$ 37.66」 | 自動：co03 |
| TC-009 | 原話 2「顯示雲端自己的幣別（美元）、不換算」；co03 | 功能 | 同 TC-006 | 分別開 `/usage` 與 `/usage?lang=en`，在整頁文字找「NT$」 | 兩版整頁都沒有「NT$」；雲端金額一律是 US$ | 自動：co03 |
| TC-010 | 頁面 2「`unknown_runs > 0` → 加小字」 | 例外 | 本月雲端有 2 個分析算不出價、1 個算得出 | 看「雲端已用（本月）」卡 | 卡內有小字「另有 2 個分析算不出」 | 自動 |
| TC-011 | 作法 cloud 段「`month_used`」 | 例外 | 同 TC-010；算得出的那個是 US$ 1.20 | 看已用數字 | 已用只含算得出的 1.20（顯示「US$ 1.20」），算不出的沒被當 0 加進去、也沒被猜一個數 | 自動 |
| TC-012 | 頁面 2；原話 2「上限由管理者開帳號時設」；co04 | 例外 | ann 沒有被設定上限 | 看上限卡 | 數字是「未設定」 | 自動：co04 |
| TC-013 | 頁面 2；co04 | 例外 | 同 TC-012 | 看同一張卡 | 卡內有小字「由管理者設定」 | 自動：co04 |
| TC-014 | 頁面 2；co04 | 例外 | 同 TC-012 | 看剩餘卡 | 數字是「—」 | 自動：co04 |
| TC-015 | 頁面 2「剩餘為 0」；裁決 6；co05 | 例外 | 上限 10、本月雲端已用 12.34（超過上限） | 看剩餘卡 | 數字是「US$ 0.00」，不是負數 | 自動：co05 |
| TC-016 | 頁面 2「卡片用既有「需處理」樣式」；co05 | 例外 | 同 TC-015 | 檢查剩餘卡的樣式 class 與 `<style>` | 卡片套用樣式表裡已經存在的狀態樣式（一個在本任務之前就定義過的 class）；樣式表沒有為此新增顏色值 | 自動 |
| TC-017 | 專長守則「狀態絕不只靠顏色」 | 例外 | 同 TC-015 | 看剩餘卡的 HTML 文字 | 除了數字與 class 之外，卡上另有一個符號和一個文字標示（說明這張卡需要處理），不是只靠顏色 | 自動 |
| TC-018 | 原話 3「先把功能做起來吧，以後再改美觀」；限制「只用現有 class 與 token」 | 功能 | ann 已登入 | 取 `/usage` 的樣式表，套用既有 `test_tc057` 的規則（字級、圓角、間距、無新顏色值） | 通過同樣的規則，且頁面仍只有一份樣式表 | 自動 |

## User Story 2 — 每個分析各花多少、是估算還是還在跑（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 頁面 4；原話 1「per-analysis table」；co01 | 功能 | ann 本月有分析 | 看表頭 | 五欄依序為「分析名稱」「開始時間」「在哪裡跑」「用量」「狀態」 | 自動：co01 |
| TC-020 | 頁面 4「連到 `/?run=<id>`」 | 功能 | 本月有一個叫 run-a 的分析 | 看 run-a 那一列的名稱 | 名稱是連結，指向 `/?run=<該分析的 id>`（英文頁帶 `lang=en`） | 自動 |
| TC-021 | 頁面 4；作法 `where` | 功能 | 本月有一個送到國網的分析 | 看該列「在哪裡跑」 | 顯示「國網」 | 自動 |
| TC-022 | 頁面 4「`12.30 SU`」；作法 `su` | 功能 | 同 TC-021，該分析已結束、SU 為 5.10 | 看該列「用量」 | 顯示「5.10 SU」 | 自動 |
| TC-023 | 頁面 4；作法 `where` | 功能 | 本月有一個送到雲端（Google Batch）的分析 | 看該列「在哪裡跑」 | 顯示「雲端」 | 自動 |
| TC-024 | 頁面 4「`US$ 1.20`」；作法 `usd` | 功能 | 同 TC-023，該分析已結束、費用 1.20 美元 | 看該列「用量」 | 顯示「US$ 1.20」 | 自動 |
| TC-025 | 作法 `where`「不是平台送出的 → None」 | 例外 | 本月有一個無法判斷運算環境的分析 | 看該列「在哪裡跑」 | 顯示「—」 | 自動 |
| TC-026 | 頁面 4；原話 1「Running」；co06 | 功能 | 本月有一個還在跑的分析 | 看該列「狀態」 | 顯示「⟳ 執行中」 | 自動：co06 |
| TC-027 | 作法 `runs`「數字一律 None」；co06 | 功能 | 同 TC-026 | 看該列「用量」 | 顯示「—」（不是 0.00） | 自動：co06 |
| TC-028 | 作法 `runs`「running／lost → running」 | 例外 | 本月有一個狀態是 lost（失聯）的分析 | 看該列 | 狀態同樣是「⟳ 執行中」，用量「—」 | 自動 |
| TC-029 | 頁面 4；原話 1「Estimate, bill pending」；co06 | 功能 | 本月有一個已結束的分析 | 看該列「狀態」 | 顯示「≈ 估算・帳單未到」 | 自動：co06 |
| TC-030 | 作法 `runs`；頁面 4 | 例外 | 本月有一個已結束、但算不出費用的雲端分析 | 看該列 | 用量「—」，狀態仍是「≈ 估算・帳單未到」 | 自動 |
| TC-031 | 限制「每人只看自己的」；co06 | 例外 | ann 與 bob 本月各有分析 | ann 登入開 `/usage` | 表裡只有 ann 的分析，看不到 bob 的任何分析名稱 | 自動：co06 |
| TC-032 | 作法 `runs`「這個月開始的分析」；co06 | 功能 | ann 有一個上個月開始的分析 | 開 `/usage`（預設本月） | 上個月的分析不在表裡 | 自動：co06 |
| TC-033 | 裁決 8（台北時間、以開始時間計） | 功能 | ann 有一個分析開始於 UTC 2026-09-30 16:30（台北已是 10 月 1 日 00:30） | 分別開 `/usage?month=2026-10` 與 `/usage?month=2026-09` | 該分析只出現在 2026-10，不出現在 2026-09 | 自動 |
| TC-034 | 作法 `runs`「最新在前」 | 功能 | 本月有三個不同開始時間的分析 | 看表的順序 | 開始時間最晚的在最上面，依序往下 | 自動 |
| TC-035 | 作法 `runs`「最多 50 筆」 | 功能 | 本月有 51 個分析 | 看表 | 表有 50 列；被省略的是最舊的那一個 | 自動 |
| TC-036 | 頁面 4「沒有分析 → 「— 這個月還沒有分析」」 | 例外 | ann 本月沒有任何分析 | 開 `/usage` | 表的位置顯示「— 這個月還沒有分析」，頁面不出錯 | 自動 |
| TC-037 | 專長守則「狀態表達：符號＋文字」 | 功能 | 表裡同時有「執行中」與「估算」兩種列 | 看兩種狀態格的 HTML 文字 | 每一格都同時含一個符號與一個文字（⟳ 執行中／≈ 估算・帳單未到），不是只靠 class 顏色 | 自動 |
| TC-038 | 頁面 4「英文 `Running`／`Estimate · bill pending`」；原話 4 | 功能 | 表裡同時有執行中與已結束的列 | 開 `/usage?lang=en` | 狀態格分別是符號加「Running」、符號加「Estimate · bill pending」 | 自動：co09 |

## User Story 3 — 從抬頭進來、換月份、登入、中英文與版面限制（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 抬頭；原話 1「from the masthead meter」；co08 | 功能 | ann 已登入 | 分別開 `/`、`/settings`、`/launch`、某分析頁，看抬頭的兩個費用字樣 | 每一頁的費用字樣都包在連到 `/usage` 的連結裡 | 自動：co08 |
| TC-040 | 抬頭「`cost_cloud` 改成「雲端 US$ —」」；co08 | 功能 | 同上 | 看中文頁抬頭 | 費用字樣是「SU —」與「雲端 US$ —」 | 自動：co08 |
| TC-041 | 抬頭「保留 `lang`」「Cloud US$ —」；co08 | 功能 | 同上 | 開 `/?lang=en` 看抬頭 | 費用字樣是「SU —」與「Cloud US$ —」，連結帶 `lang=en` | 自動：co08 |
| TC-042 | 原話 2「不換算」；co08 | 功能 | 同上 | 看中、英文任一頁的抬頭 | 抬頭沒有「NT$」 | 自動：co08 |
| TC-043 | 頁面 1 | 功能 | 開 `/usage?month=2026-10` | 看標題 | 中文頁標題「費用」＋「2026-10」；英文頁「Cost」＋「2026-10」 | 自動 |
| TC-044 | 作法「預設本月，台北時間」 | 功能 | 本月有分析 | 開 `/usage`（不帶 month） | 顯示的月份是目前台北時間的月份，列出該月分析 | 自動 |
| TC-045 | 作法 `?month=YYYY-MM`；co07 | 功能 | 8 月、9 月、10 月各有分析 | 開 `/usage?month=2026-09` | 表只列 9 月的分析，卡片數字也是 9 月的 | 自動：co07 |
| TC-046 | 作法「格式錯 → 當作本月」；co07 | 例外 | 本月有分析 | 開 `/usage?month=abc` | 顯示的是本月的資料（不是空白、不是錯誤頁） | 自動：co07 |
| TC-047 | 作法「顯示制式通知「月份格式不對，顯示本月。」」；co07 | 例外 | 同 TC-046 | 看同一頁 | 以制式通知的形式出現整句「月份格式不對，顯示本月。」 | 自動：co07 |
| TC-048 | 作法 `?month`；co07 | 功能 | 同上 | 開格式正確的 `/usage?month=2026-09` | 沒有「月份格式不對」通知 | 自動：co07 |
| TC-049 | 頁面 1「上一月連結」 | 功能 | 目前顯示 2026-10 | 點「上一月」 | 到 `month=2026-09`（保留 `lang`） | 自動 |
| TC-050 | 頁面 1「下一月不超過本月」；co07 | 功能 | 顯示的就是本月 | 找頁面上指向更晚月份的連結 | 沒有任何指向比本月更晚的月份連結 | 自動：co07 |
| TC-051 | 頁面 1；co07 | 功能 | 顯示的是本月的前一個月 | 點「下一月」 | 到本月，不會跳到更晚的月份 | 自動：co07 |
| TC-052 | 抬頭／頁面 1「保留 `lang`」；原話 4 | 功能 | 開 `/usage?month=2026-09&lang=en` | 看上一月、下一月連結 | 連結都帶 `lang=en` | 自動 |
| TC-053 | 作法「須登入；未登入轉到登入」；co12 | 例外 | 沒有登入 | 開 `GET /usage` | 被轉到登入頁（與其他頁相同） | 自動：co12 |
| TC-054 | co12「不洩漏數字」 | 例外 | 同 TC-053，資料庫有 ann 的分析與費用 | 看被轉去的回應內容 | 回應裡沒有任何分析名稱、SU 或美元數字 | 自動：co12 |
| TC-055 | 限制「英文版每個字都有」；原話 4；co09 | 功能 | 有資料的 ann 已登入 | 開 `/usage?lang=en`，看中欄文字 | 費用頁自己組出的文字沒有任何中文字（使用者自己取的分析名稱、語言切換的「中」除外） | 自動：co09 |
| TC-056 | 原話 1「cards NCHC SU / Cloud used / cap / remaining」；co09 | 功能 | 同上 | 看英文頁四張卡標題 | 四張卡標題分別含「NCHC SU」「used」「cap」「remaining」 | 自動：co09 |
| TC-057 | 頁面 3「（英文對應句）」；原話 1「"never converted" line」 | 功能 | 同上 | 看英文頁固定說明 | 有一句英文說明，含「convert」與「SU」，沒有中文字 | 自動：co09 |
| TC-058 | 限制「英文版每個字都有」 | 例外 | 英文頁，SU 算不出（如 TC-004 的情況） | 看國網 SU 卡內小字 | 小字是英文原因，沒有中文字 | 自動：co09 |
| TC-059 | 限制「制式通知」＋「英文版每個字都有」 | 例外 | 開 `/usage?month=abc&lang=en` | 看通知 | 有一則制式通知，內容是英文、沒有中文字 | 自動：co09 |
| TC-060 | 限制「英文版每個字都有」；頁面 4 | 例外 | 英文頁，本月沒有分析 | 看表的位置 | 有一句英文的「這個月沒有分析」說明，沒有中文字 | 自動：co09 |
| TC-061 | 限制「零 JavaScript、無 `style=`、單一樣式表」；原話 3；co10 | 功能 | 中文頁與英文頁、有資料與沒資料各一次 | 檢查回應 HTML | 沒有 `<script`、沒有 `on…=` 事件屬性、沒有 `style=`、只有一個 `<style>`、沒有 `<link`、沒有外部網址 | 自動：co10 |
| TC-062 | 限制「CSP 雜湊」；co10 | 功能 | 同 TC-061 | 檢查 `content-security-policy` 標頭 | style-src 含這份樣式表的 sha256；沒有 `script-src`、沒有 `'unsafe-inline'` | 自動：co10 |
| TC-063 | 限制「制式通知、無口語句」；co10；`test_tc040` | 功能 | 平台程式碼與頁面 | 執行既有的禁用字測試，並看頁面文字 | `test_tc040` 仍綠（平台內沒有「需要處理」「要你處理」）；頁面沒有口語句 | 自動：co10、`platform/tests/test_web_actions.py::test_tc040_tc041_*` |
| TC-064 | 裁決 2；co10 | 功能 | 登入後 | 看路由表；`GET /cost`、`POST /cost` | `/usage` 存在；沒有任何路徑含 `cost`；`/cost` 回 404 | 自動：co10 |
| TC-065 | 限制「390 px 無橫向捲動」 | 功能 | 手機寬度 390 px | 在 390 px 寬度開 `/usage` 與 `/usage?lang=en`（有資料、有 51 筆、無資料各一次） | 頁面不出現橫向捲軸；表格內容可讀 | 手動：`docs/TESTING.md`「費用頁」 |
| TC-066 | 專長守則「鍵盤操作時焦點外框可見」 | 功能 | 開 `/usage` | 用 Tab 鍵逐一走過抬頭連結、月份連結、表中名稱連結 | 每個停到的連結都有看得見的焦點外框 | 手動：`docs/TESTING.md`「費用頁」 |
| TC-067 | 原話 4；計畫「中英各看一次」 | 功能 | 開 `/usage` 與 `/usage?lang=en` | 各看一次整頁 | 兩版都完整、版面一致，沒有漏譯 | 手動：`docs/TESTING.md`「費用頁」 |
| TC-068 | 範圍「`docs/TESTING.md`（新增一節「費用頁」）」 | 功能 | 實作完成 | 讀 `docs/TESTING.md` | 有一節「費用頁」，列出 TC-065、066、067 的步驟，具體到別人能照做 | 手動：`docs/TESTING.md` |
| TC-069 | 範圍「`docs/PLATFORM.md`（一段：費用頁每個數字從哪來）」 | 功能 | 實作完成 | 讀 `docs/PLATFORM.md` | 有一段說明費用頁每個數字（國網 SU、雲端已用、上限、剩餘、每列用量）各從哪裡來 | 手動：`docs/TESTING.md`（驗收者讀 `docs/PLATFORM.md` 該段） |

## User Story 4 — 動作層與 MCP 同一份資料、只看自己的（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 作法 `my_usage` 回傳形狀 | 功能 | ann 的 caller | 呼叫 `my_usage` | 回傳的鍵為 `month`、`su`（`total`、`unknown_reasons`、`site`）、`cloud`（`used_usd`、`unknown_runs`、`cap_usd`、`remaining_usd`、`currency`）、`runs`，不多不少 | 自動：co11 |
| TC-071 | 作法 `runs` 形狀 | 功能 | 本月有分析 | 看 `runs` 的一項 | 鍵為 `name`、`started_at`、`where`、`state`、`su`、`usd`、`unknown_reasons`，不多不少 | 自動：co11 |
| TC-072 | 作法 `currency: "USD"`；原話 2 | 功能 | 同上 | 看 `cloud.currency` | 為「USD」；回傳裡沒有新台幣或換算欄位 | 自動：co11 |
| TC-073 | 作法 `su.total`＝`su.month_total`；`site`＝費率檔 `default_site` | 功能 | 本月有可算的國網分析 | 比較 `my_usage` 與直接用 `su.month_total(…, default_site, …)` | `su.total` 相同；`su.site` 等於 `default_site` | 自動 |
| TC-074 | 作法「任何一個分析算不出 → None 並帶原因」 | 例外 | 兩個國網分析，一個算不出 | 呼叫 `my_usage` | `su.total` 為 None，`su.unknown_reasons` 不空且含該分析算不出的原因；不是部分和 | 自動：co02 |
| TC-075 | 作法 `cloud.used_usd`／`unknown_runs`＝`month_used` | 功能 | 本月有雲端分析，其中 2 個算不出 | 比較 `my_usage` 與 `cloud_cost.month_used` | `used_usd`、`unknown_runs` 與 `month_used` 完全相同 | 自動 |
| TC-076 | 作法 `cap_usd`＝`store.cloud_cap` | 功能 | ann 上限 50 | 呼叫 `my_usage` | `cap_usd` 等於 50 | 自動：co03 |
| TC-077 | 作法「沒設 → None」 | 例外 | ann 沒設上限 | 呼叫 `my_usage` | `cap_usd` 為 None | 自動：co04 |
| TC-078 | 作法 `remaining_usd`＝`max(0, cap − used)` | 功能 | 上限 50、已用 12.34；另一情況上限 10、已用 12.34 | 呼叫 `my_usage` 兩次 | 剩餘分別為 37.66 與 0（不是負數） | 自動：co03、co05 |
| TC-079 | 作法「沒上限 → None」 | 例外 | ann 沒設上限 | 看 `remaining_usd` | 為 None | 自動：co04 |
| TC-080 | 裁決 6「金額一律保留兩位小數顯示、計算不四捨五入」 | 功能 | 雲端已用實際是 0.123456 | 看 `my_usage` 與頁面 | `used_usd` 仍是 0.123456（沒被四捨五入）；頁面顯示「US$ 0.12」 | 自動 |
| TC-081 | 作法 `state`、`runs`「run 還沒結束」 | 例外 | 本月有一個執行中（或 lost）的分析 | 看它在 `runs` 的那一項 | `state` 為 `running`，`su` 與 `usd` 為 None，`unknown_reasons` 含「run 還沒結束」 | 自動：co06 |
| TC-082 | 作法 `state` | 功能 | 本月有一個已結束的分析 | 看它在 `runs` 的那一項 | `state` 為 `estimate` | 自動：co06 |
| TC-083 | 作法 `where`「由該分析最新一次 launch 的運算環境決定」 | 功能 | 同一個分析先送到國網、後來又送到雲端 | 看該項 `where` | 為 `cloud`（以最新一次為準） | 自動 |
| TC-084 | 作法「`month=None` → 預設本月（台北時間）」 | 功能 | 本月有分析 | 呼叫 `my_usage` 不帶 month | `month` 為目前台北時間的 `YYYY-MM` | 自動 |
| TC-085 | 範圍「`mcp_server.py`（同名 read tool）」；co11 | 功能 | 同一位 caller 與同一月 | 分別呼叫動作層 `my_usage` 與 MCP 的 `my_usage` | 兩邊內容完全相同 | 自動：co11 |
| TC-086 | 作法 `month` 參數 | 功能 | 8、9 月各有分析 | 用 MCP 的 `my_usage` 帶 `month=2026-09` | 回的是 9 月的資料 | 自動 |
| TC-087 | 範圍「parity 要求」；決策 11 | 功能 | 實作完成 | 跑 `test_web_parity.py` 與 `test_actions_layer.py` | 工具／動作清單兩邊對得上，且只比之前多了 `my_usage` 一項 | 自動：`platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py` |
| TC-088 | 專長守則「跨使用者」；限制「每人只看自己的」；co11 | 例外 | ann、bob 各有分析 | bob 的 caller 呼叫 `my_usage` | `runs` 只含 bob 自己的，沒有 ann 的任何分析 | 自動：co11 |
| TC-089 | 同上 | 例外 | 同上，ann 與 bob 各有 SU、雲端用量 | 比較兩人的 `su.total`、`cloud.used_usd` | 各自只含自己的分析；bob 的數字不含 ann 的 | 自動：co11 |
| TC-090 | 同上；原話 2「每人每月上限」 | 例外 | ann 上限 50、bob 沒設 | bob 呼叫 `my_usage` | bob 的 `cap_usd` 為 None（沒有拿到 ann 的 50） | 自動 |
| TC-091 | 同上（網頁） | 例外 | 同 TC-088，bob 登入 | bob 開 `/usage` | 整頁沒有 ann 的任何分析名稱與金額 | 自動：co06 |
| TC-092 | 專長守則「寫入／跨使用者寫」（本任務只讀） | 例外 | ann 已登入 | 對 `/usage` 送 POST | 被拒絕（404 或 405）；資料沒有任何改變 | 自動 |
| TC-093 | 專長守則「路由處理函式不得有第二份邏輯」；`test_tc060` 精神 | 功能 | 實作完成 | 解析 `web_cost.py` 的 import 與呼叫 | 沒有 import `confirm`、`jobs`、`compute_envs`、`agents`、`status`、`su`、`cloud_cost`、`store`；沒有呼叫 `actions.launch/cancel/forget/…`；資料只經 `actions` | 自動 |
| TC-094 | 專長守則「動作層唯一入口」；裁決 7 | 功能 | 實作完成 | 解析 `web.py` 的 `/usage` 處理函式 | 處理函式只呼叫 `actions.my_usage` 與 `web_cost` 的組版函式，自己不算 SU／雲端／上限 | 自動 |
| TC-095 | 專長守則「錯誤訊息不露出堆疊、內部路徑或 SQL」 | 例外 | 開 `/usage?month=abc`，及月份格式錯的各種寫法 | 看回應 | 只有制式通知，沒有堆疊、檔案路徑或 SQL 字樣 | 自動 |
| TC-096 | 專長守則「密鑰不出現在回應」 | 例外 | ann 已登入，有 session cookie 與 token | 看 `/usage`（中、英）的回應內容 | 回應裡沒有 cookie 值、token、密碼 | 自動 |

## 不在範圍（計畫「不做」與裁決）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-097 | 「不做 Reconciled」；裁決 3；原話 1「Reconciled」 | 不在範圍 | 表裡有執行中與已結束的列 | 在中、英文 `/usage` 找「已對帳」「Reconciled」 | 兩版都找不到；`runs.state` 只有 `running`、`estimate` 兩種；沒有為它佔位的欄位或空列 | 自動 |
| TC-098 | 「不接 Google 帳單或國網帳務 API」；「平台完全不連網」 | 不在範圍 | 實作完成 | 解析 `web_cost.py` 與 `my_usage` 實作的 import | 沒有 `urllib`、`http.client`、`socket`、`requests` 等連網模組；測試在無網路下通過 | 自動 |
| TC-099 | 「不做「送出會超過上限」的需處理通知」；原話 1「Action-needed notice when a launch would exceed the cloud cap」 | 不在範圍 | 剩餘為 0（TC-015 的情況） | 看 `/usage` 與任一分析頁的右欄 | 右欄沒有因此新增任何通知 | 自動：co05 |
| TC-100 | 同上；原話 1「use NCHC / wait for reset」 | 不在範圍 | 同上 | 看 `/usage` 全頁文字 | 沒有「改用國網」「等重置」之類的建議字樣 | 自動 |
| TC-101 | 「不改執行／結果階段的「費用」卡」 | 不在範圍 | 有執行中與已結束的分析 | 開兩種分析頁，看「費用」卡 | 兩張卡仍顯示「SU —」，沒有被填數字或加連結 | 自動：`test_web_board.py` tcs03_s04、`test_web_actions.py::test_tc051` |
| TC-102 | 「不在抬頭填數字」；裁決 9 | 不在範圍 | ann 本月有大量費用 | 看任一頁抬頭文字 | 只有「SU —」「雲端 US$ —」，沒有任何數字 | 自動：co08 |
| TC-103 | 「不換算幣別」；原話 2 | 不在範圍 | 有雲端費用 | 看 `/usage`（中、英）全頁與 `my_usage` 回傳 | 沒有「TWD」「匯率」「exchange rate」，也沒有任何新台幣金額（固定說明句內的「不換算新台幣」除外） | 自動 |
| TC-104 | 「不改確認頁」 | 不在範圍 | 實作完成 | 跑確認頁既有測試，比對 diff | `test_confirm_page.py` 等確認頁測試仍綠；確認頁相關程式沒有被改 | 自動：`platform/tests/test_confirm_page.py` |
| TC-105 | 「不加 JS」；限制「零 JavaScript」 | 不在範圍 | 實作完成 | 看 `/usage` 回應與 diff | 頁面沒有 `<script`，也沒有新增任何 JS 檔 | 自動：co10 |
| TC-106 | 「不加資料表、不需 migration」；`test_tc063` | 不在範圍 | 實作完成 | 跑 `test_tc063_no_schema_change`，看 diff | 資料表與欄位清單與 base 完全相同；沒有新增 migration | 自動：`platform/tests/test_web_actions.py::test_tc063_*` |
| TC-107 | 「不改管理者設定上限的 CLI」 | 不在範圍 | 實作完成 | 看 diff，跑上限相關既有測試 | `cli.py` 沒被改；設定上限的既有測試仍綠 | 自動 |
| TC-108 | 原話 2「上限由管理者開帳號時設」 | 不在範圍 | ann 已登入 | 看 `/usage` 中欄 | 沒有任何可以設定或修改上限的表單或輸入欄；上限卡只顯示 | 自動 |
| TC-109 | 裁決 2「不得放寬 tc051」 | 不在範圍 | 實作完成 | 比對 `test_tc051` 的 diff | `test_tc051` 的路徑規則（`upload\|cost\|chat\|forget\|samplesheet\|delete`）與 `/cost` 必須 404 的斷言原封不動 | 自動：`test_web_actions.py::test_tc051_*` |
| TC-110 | 裁決 10「頁面不另加說明」 | 不在範圍 | `default_site` 以外另有站台 | 看 `/usage` | 頁面沒有站台名稱、沒有多站台加總或說明 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-111 | 第 2 條（不得另存一份 run 狀態） | 功能 | 實作完成 | 跑 `tests/no_second_run_state_test.sh` | 通過；`my_usage` 的數字是讀取當下由 index 與價目算出，沒有另外存起來 | 自動：`tests/no_second_run_state_test.sh` |
| TC-112 | 第 2 條（只有一條送出路徑，須經人確認） | 例外 | 實作完成 | 開 `/usage`、呼叫 `my_usage` 前後，數 jobs 與確認請求的列數 | 列數不變；沒有產生任何確認請求或送出動作 | 自動 |
| TC-113 | 第 9 條（缺口要明寫，數字來自檔案） | 例外 | 有算不出的 SU、算不出的雲端分析、執行中的分析 | 看 `/usage` 各處 | 算不出的地方都顯示「—」或「另有 n 個分析算不出」，沒有任何地方把算不出顯示成 0.00 | 自動 |
| TC-114 | 第 3 條（不寫死個人路徑） | 功能 | 實作完成 | 跑 `tests/no_hardcoded_paths.sh` | 通過 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-115 | 安全網：既有守門測試要繼續綠（計畫「不能放掉的限制」） | 功能 | 實作完成 | 跑 `test_web_actions.py` 的 tc046–048、tc051、tc060、tc063、tc040，與全套 | 全部綠；`tests/init_workspace_test.sh`「site side with no run area known fails clearly」是已知環境紅（裁決 1），不算 | 自動：`platform/tests/test_web_actions.py`、`tests/run_all.sh` |
| TC-116 | 安全網：不得放鬆既有斷言（裁決 4） | 例外 | 實作完成 | 比對 base 與 HEAD 之間既有測試檔的 diff，對照 `specs/cost-page/ledger.md` | 被改寫的既有斷言只限：抬頭字串「雲端 NT$ —」／「Cloud NT$ —」、抬頭費用字樣「不是連結」、工具清單／工具數加 `my_usage`；每條在 ledger 以「舊→新＋理由」列出；其他既有斷言沒有被刪、放寬或跳過 | 自動（閱卷時以 `git diff` 比對 ledger） |
