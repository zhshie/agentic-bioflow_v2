# 測試案例：011b 執行中階段頁與正式通知元件（唯讀）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Kind: ui + backend; both specialist rules (專長守則 ui 與 backend) apply.
There is no spec.md for 011b. The sources are: the plan (`specs/011b-running-page/plan.md`, scope N1 to N5, out of scope, and the rulings Q1 to Q10 of contract round 1), the root `DESIGN.md` (screen 7, "Formal notices", "States", and the maintainer's ten verbatim words), `PRODUCT.md`, and the 011a contract (`specs/011a-web-shell/test-case.md`) whose pins this slice must keep.
The maintainer instruction for this contract: the cases come from the examples in the plan. Nothing here invents behaviour the plan, its rulings or DESIGN.md do not state. Places where they are silent are listed in the overview under 「我（撰寫者）不確定的地方」 and are NOT pinned.
Language: 繁體中文; identifiers (TC-, Q, N) and file paths stay as they are.
-->

**規格**：`specs/011b-running-page/plan.md`（含「Rulings after contract round 1」Q1 至 Q10）、根目錄 `DESIGN.md`（畫面 7、Formal notices、States）、`PRODUCT.md`　**總覽**：`test-case-overview.md`

## 名詞與共用測試資料

名詞：

- 「通知」= 計畫 N1 的正式通知元件：一個方框，含等級標籤（符號＋文字）、分析名稱、右側時間、一行標題、一組「欄位清單」（問題／原因／可選動作）、按鈕區。
- 「欄位清單」= HTML 的 `<dl>`（`<dt>` 欄位名、`<dd>` 欄位值）。測試用它找到通知方框。
- 「灰按鈕」= 畫面上有字、看得到、但按了什麼都不會發生的按鈕：不在 `<form>` 裡、不是連結、不是可送出的控制項。
- 「現在頁」= 沒選 run 時 `/` 的中欄；「需要注意卡」是它的第二張卡。
- 「執行中階段頁」= 選了 run、階段為 running 時的中欄（設計稿畫面 7）。
- 「分頁」= 執行中階段頁上的 任務／日誌／執行資訊／設定檔／指標 五個連結，用網址的 `?tab=` 切換。
- 「台北時間」= Asia/Taipei，格式 `MM-DD HH:mm`（011a G7）。
- 「CJK 字元」= 中日韓文字；英文版測試用純 ASCII 的 run 名稱、使用者名稱、任務名稱與失敗原因，才能證明「畫面上的字」都換成英文。
- 「固定時鐘」= 測試把「現在」固定在 2023-11-14T02:05:00Z（做法由執行者定，011a 的測試怎麼固定就怎麼固定）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或明白標「之後開放」。

共用測試資料（甲 = ann、乙 = bob，各自登入；run 名稱為純 ASCII）：

- **F1**（甲，failed）：started_at 2023-11-14T00:00:00Z（台北 11-14 08:00）、ended_at 2023-11-14T02:05:00Z（台北 11-14 10:05）；`failure_reason` = `samplesheet is missing the reverseReads column` 換行 `second line`；`failed_tasks` 依名稱排序為 ① `FASTQC (sample2)`、exit_code 137、error_message `Process exceeded memory` 換行 `second line`；② `TRIMGALORE (sample3)`、exit_code 1、error_message `cutadapt failed`；任務數 succeeded 5、cached 4、failed 3、aborted 2、running 1、pending 6、submitted 7（total 28，每個數字都不同，才能驗證標籤與數字配對）；`processes` 裡沒有任何 running 的。
- **F2**（甲，failed）：`failure_reason` = `樣本表少了 reverseReads 欄`（設計原話 7 禁止的那種句子，這裡只當作「原因」欄的值）；沒有 `failed_tasks`。
- **F3**（甲，failed）：沒有 `failure_reason`、沒有 `failed_tasks`、沒有 ended_at。
- **F4**（甲，failed）：`failure_reason` 第一行 120 個 `A`，其後還有第二行。
- **L1**（甲，lost）：last_message_at 2023-11-14T03:00:00Z（台北 11-14 11:00），沒有 ended_at；另備 **L2**（甲，lost）沒有 last_message_at。
- **U1**（甲，running）：started_at 2023-11-14T00:00:00Z；`processes` 只有一個 running：`ALIGN (s1)`。**U2**（甲，running）：`processes` 有三個 running：`ALIGN (s1)`、`BWA (s2)`、`CALL (s3)`。**U3**（甲，running）：沒有任何 running 的 process。**U0**（甲，running）：任務數全是 0。
- **S1**（甲，succeeded）。
- **B1**（乙，failed）：run 名稱、任務名稱、error_message、workdir、failure_reason 都是只有乙這邊才有的獨特字串。

## User Story 1 — 正式通知元件的欄位與樣子（優先度 P1）

對應計畫 N1、裁定 Q1 至 Q4、Q9，設計稿 "Formal notices"，設計原話 7「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-R01 | N1；Q4；States | 功能 | 甲登入，有 F1 | GET `/?run=<F1>` | 「本 run 的通知」裡有一個通知，等級標籤是「! 需要處理」：符號 `!` 與文字「需要處理」都在 HTML 裡，不只靠顏色的 class | 自動 |
| TC-R02 | N1；Q9 | 功能 | 同上 | 同上 | 通知裡的分析名稱是 F1 的名稱，用等寬字型（樣式表對它設 `ui-monospace` 那組）；它是連結，連到 F1 自己的頁（`/?run=<F1>`） | 自動 |
| TC-R03 | N1；Q2 | 功能 | 同上 | 同上 | 通知右側的時間是 F1 的 ended_at 以台北時間顯示：`11-14 10:05`；頁面任何地方沒有原始 ISO 字串（沒有 `2023-11-14T`） | 自動 |
| TC-R04 | N1；Q3 | 功能 | 同上 | 同上 | 通知標題恰好是「分析失敗」，單行（沒有換行、沒有 `<br>`），標題裡沒有數字、沒有 `exit`、沒有錯誤代碼 | 自動 |
| TC-R05 | N1；Q1 | 功能 | 同上 | 同上 | 欄位「問題」的值是 `get_run` 失敗任務清單的第一筆名稱：`FASTQC (sample2)`；第二筆 `TRIMGALORE (sample3)` 不在通知裡 | 自動 |
| TC-R06 | N1；R10 | 功能 | 同上 | 同上 | 欄位「原因」的值是 `failure_reason` 的第一行 `samplesheet is missing the reverseReads column`；第二行 `second line` 不出現在通知裡 | 自動 |
| TC-R07 | N1；R10（80 字元切法照舊） | 功能 | 甲有 F4 | GET `/?run=<F4>` | 「原因」的值是 79 個 `A` 加「…」（共 80 字元以內），整串裡沒有連續 80 個 `A`，第二行不出現 | 自動 |
| TC-R08 | N1；Q4 | 功能 | 甲有 F1 | GET `/?run=<F1>` | 欄位「可選動作」的值是「續跑／重跑（之後開放）」 | 自動 |
| TC-R09 | N1 | 功能 | 同上 | 同上 | 通知的欄位清單恰好三個欄位，順序是「問題」「原因」「可選動作」 | 自動 |
| TC-R10 | N1；Q4；N4 | 功能 | 同上 | 同上 | 通知的按鈕區有「續跑」「重跑」兩個灰按鈕，看得到字；它們不在 `<form>` 裡、不是連結、不是可送出的控制項；整頁的 `<form>` 仍只有登出那一個 | 自動 |
| TC-R11 | 設計原話 7；N1 | 功能 | 甲有 F2（原因是 `樣本表少了 reverseReads 欄`） | GET `/?run=<F2>` | 通知裡除了 run 自己的值（名稱、原因）之外，頁面自己產生的字只有：等級標籤、時間、標題、三個欄位名、可選動作的字、兩個按鈕字；沒有「AI 改不了」之類的口語句子；`樣本表少了 reverseReads 欄` 只出現在「原因」欄裡 | 自動 |
| TC-R12 | 設計原話 5；Q4 | 功能 | 甲有 F1 | GET `/?run=<F1>&lang=en` | 通知是英文：等級標籤「! Action needed」、標題「Analysis failed」、欄位名「Problem」「Cause」「Options」、可選動作「Resume / Re-run (coming later)」、按鈕「Resume」「Re-run」；通知裡沒有任何 CJK 字元 | 自動 |
| TC-R13 | N1；Q2；Q3；Q4 | 功能 | 甲有 L1 | GET `/?run=<L1>` | 失聯通知：等級標籤「! 需要處理」、標題「與站台失去聯絡」、「問題」是「失聯」、「原因」是「三次心跳沒有回應」、「可選動作」是「續跑／重跑（之後開放）」、右側時間是 last_message_at 的台北時間 `11-14 11:00`、兩個灰按鈕 | 自動 |
| TC-R14 | 設計原話 5；Q4 | 功能 | 同上 | GET `/?run=<L1>&lang=en` | 失聯通知英文：標題「Lost contact with the site」、「Problem」是「Lost」、「Cause」是「No heartbeat three times in a row」、「Options」是「Resume / Re-run (coming later)」；通知裡沒有 CJK 字元 | 自動 |
| TC-R15 | N1；Q1 | 例外 | 甲有 F2（失敗、沒有任何失敗任務） | GET `/?run=<F2>` | 「問題」的值是「步驟未記錄」 | 自動 |
| TC-R16 | 設計原話 5；Q1 | 例外 | 同上 | GET `/?run=<F2>&lang=en` | 「Problem」的值是「step not recorded」 | 自動 |
| TC-R17 | N1；Q1 | 例外 | 甲有 F3（沒有失敗原因） | GET `/?run=<F3>` | 「原因」的值是「原因未記錄」 | 自動 |
| TC-R18 | 設計原話 5；Q1 | 例外 | 同上 | GET `/?run=<F3>&lang=en` | 「Cause」的值是「reason not recorded」 | 自動 |
| TC-R19 | Q2 | 例外 | 甲有 F3（沒有 ended_at）與 L2（沒有 last_message_at） | 各自 GET `/?run=<id>` | 兩個通知右側的時間都是「—」，不是空白、不是 `None`、不是原始 ISO | 自動 |
| TC-R20 | 專長守則（ui）；011a TC-H12 | 例外 | 甲的 run 名稱、失敗任務名稱、`failure_reason` 都含 `<script>x</script>` 與 `"><b>` | GET 該 run 的頁面（zh、en）與 `/` | 通知與整頁都沒有未跳脫的 `<script>`、`<b>`；文字以跳脫後的樣子出現；`<a href>` 的屬性有引號且沒有被帶出屬性 | 自動 |
| TC-R21 | DESIGN "No coloured side stripes" | 功能 | 取出通知方框（欄位清單的外層方框）的 class，與頁面內嵌的樣式表 | 讀樣式表裡套用到通知方框 class 的規則 | 這些規則沒有 `border-left`、`border-right`、`border-inline-start`、`border-inline-end`（沒有彩色側邊條） | 自動 |
| TC-R22 | N1（「一個元件到處用」） | 功能 | 甲有 F1 與 L1 | 分別取「現在頁」需要注意卡裡的通知與執行中階段頁上的通知 | 同一個 run 在兩處的通知，等級標籤、標題、三個欄位名與欄位值、時間、按鈕字完全相同 | 自動 |

## User Story 2 — 「現在」頁的「需要注意」卡改用通知元件（優先度 P1）

對應計畫 N1（Replace the one-line items…）、N4、Q1、Q9，設計原話 1「只有需要使用者決定的才會通知使用者」，011a 的 TC-S32 至 TC-S37、TC-S50。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-R30 | N1；N4 | 功能 | 甲有 F1、L1、U1、S1 | GET `/`（沒有 `run`） | 「需要注意」卡裡每個失敗或失聯的 run 是一個通知（含欄位清單），共 2 個；卡裡沒有舊的一行式項目（沒有不含欄位清單的失敗行）；U1、S1 不在這張卡裡 | 自動 |
| TC-R31 | N1；Q1 | 功能 | 同上 | 同上 | 卡裡 F1 的通知，標題、問題（`FASTQC (sample2)`）、原因、可選動作與 TC-R04 至 TC-R08 一樣；卡裡 L1 的通知與 TC-R13 一樣 | 自動 |
| TC-R32 | 011a TC-S32；N1 | 功能 | 同上 | 同上 | 「需要注意」卡標題旁的數字是 2（= 卡裡通知的個數）；左欄「現在」旁的紅色數字也是 2；右欄計數列「!」也是 2 | 自動 |
| TC-R33 | Q9 | 功能 | 同上 | 同上 | 卡裡每個通知的分析名稱是連結，連到該 run 自己的頁（`/?run=<id>`）；英文版（`?lang=en`）連結保留 `lang=en` | 自動 |
| TC-R34 | 011a TC-S35；設計原話 1 | 例外 | 甲只有 S1 與 U1 | GET `/` | 「需要注意」卡仍在、數字是 0、裡面沒有任何通知；succeeded 與 running 不產生通知 | 自動 |
| TC-R35 | 011a TC-S37 | 例外 | 甲有 250 個 failed 的 run | GET `/` | 「需要注意」卡的數字是 250，只列 100 個通知，下面寫「還有 150 筆」 | 自動 |
| TC-R36 | 設計原話 5 | 功能 | 甲有 F1、L1（純 ASCII 名稱） | GET `/?lang=en` | 「需要注意」卡的所有通知都是英文（TC-R12、TC-R14 的字），卡裡沒有任何 CJK 字元 | 自動 |
| TC-R37 | 011a TC-H03；專長守則（backend）跨使用者讀取 | 例外 | 乙有 B1（失敗）；甲有 F1 | 甲 GET `/`、`/?lang=en`、`/?run=<F1>` | 三頁都找不到乙的 run 名稱、任務名稱、error_message、workdir、failure_reason 的任何一個字串；「需要注意」卡的數字只算甲自己的 | 自動 |
| TC-R38 | Q1；011a TC-L34 的 pin 搬家 | 例外 | 甲有 F3（沒有原因）、純 ASCII 名稱 | GET `/?lang=en` | 「需要注意」卡裡 F3 的通知，「Cause」的值是「reason not recorded」（011a 原本把這句放在一行式項目裡，現在在元件的「原因」欄；右欄項目的同一句照舊） | 自動 |
| TC-R39 | 011a TC-S34 / TC-L25 的 pin 搬家 | 功能 | 甲有 F4（第一行 120 個 `A`） | GET `/` | 卡裡的通知「原因」是 79 個 `A` 加「…」；右欄項目的失敗重點同樣是 79 個 `A` 加「…」（右欄行為不變） | 自動 |

## User Story 3 — 執行中階段頁的標題、四張摘要卡、任務條（優先度 P1）

對應計畫 N2、裁定 Q5 至 Q8，設計稿畫面 7「title with Resume / Re-run, four summary cards (current step, duration, compute, cost), Tasks bar + legend, this analysis's notices」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-R40 | N2 | 功能 | 甲有 U1（running）、F1（failed）、L1（lost） | 各自 GET `/?run=<id>` | 標題列有 run 名稱（`<h1>`）與狀態徽章，徽章同時含符號與文字：▶ 執行中、✗ 失敗、⏸ 失聯/暫停 | 自動 |
| TC-R41 | N2；Q4 | 功能 | 同上 | 同上 | 標題列有「續跑」「重跑」兩個灰按鈕，旁邊有「之後開放」；不在 `<form>` 裡、不是連結、不是可送出的控制項 | 自動 |
| TC-R42 | N2；Q4 | 功能 | 甲有 U1 | GET `/?run=<U1>&lang=en` | 標題列的按鈕字是「Resume」「Re-run」，旁邊是「Coming later」；沒有 CJK 字元 | 自動 |
| TC-R43 | N2；Q5 | 功能 | 甲有 F1 | GET `/?run=<F1>` | 恰好四張摘要卡，依序標題是「目前步驟」「耗時」「運算環境」「費用」 | 自動 |
| TC-R44 | N2；Q5；設計原話 5 | 功能 | 同上 | GET `/?run=<F1>&lang=en` | 四張卡標題依序是「Current step」「Duration」「Compute」「Cost」 | 自動 |
| TC-R45 | N2；Q8 | 功能 | 甲有 U1（只有一個 running 的 process） | GET `/?run=<U1>` | 「目前步驟」卡的值是 `ALIGN (s1)`，沒有「等 N 項」 | 自動 |
| TC-R46 | N2；Q8 | 功能 | 甲有 U2（三個 running 的 process） | GET `/?run=<U2>` | 「目前步驟」卡的值是名稱排序第一個 `ALIGN (s1)` 加「等 2 項」 | 自動 |
| TC-R47 | 設計原話 5；Q8 | 功能 | 同上 | GET `/?run=<U2>&lang=en` | 「Current step」卡的值是 `ALIGN (s1)` 加「+2 more」 | 自動 |
| TC-R48 | N2；Q8 | 例外 | 甲有 U3（沒有 running 的 process）與 F1 | 各自 GET | 「目前步驟」卡的值是「—」 | 自動 |
| TC-R49 | N2；Q8 | 功能 | 甲有 F1（起 00:00:00Z、止 02:05:00Z） | GET `/?run=<F1>` | 「耗時」卡的值是「2 小時 5 分」（結束時間 − 開始時間，不是到現在） | 自動 |
| TC-R50 | N2；Q8；設計原話 5 | 功能 | 同上 | GET `/?run=<F1>&lang=en` | 「Duration」卡的值是「2h 5m」 | 自動 |
| TC-R51 | N2；Q8 | 功能 | 甲有 U1（起 00:00:00Z），固定時鐘 02:05:00Z | GET `/?run=<U1>` | 「耗時」卡的值是「2 小時 5 分」（還在跑，算到「現在」） | 自動 |
| TC-R52 | Q8 | 例外 | 甲有一個 started_at 與 ended_at 相差 40 秒的 failed run | GET 該 run（zh 與 `lang=en`） | 「耗時」卡的值分別是「不到 1 分」與「<1m」 | 自動 |
| TC-R53 | N2；Q7 | 例外 | 甲有 F1（`get_run` 沒有運算環境名稱） | GET `/?run=<F1>` | 「運算環境」卡的值是「—」 | 自動 |
| TC-R54 | N2；012d 才開放 | 功能 | 同上 | 同上 | 「費用」卡的值是「SU —」（英文版同樣是「SU —」）：沒有數字、沒有連結 | 自動 |
| TC-R55 | N2；設計稿「Tasks bar + legend」 | 功能 | 甲有 F1 | GET `/?run=<F1>` | 四張摘要卡之後有任務條（一條橫條）與圖例 | 自動 |
| TC-R56 | N2；C6 | 功能 | 同上（任務數 5、4、3、2、1、6、7） | 同上 | 圖例恰好七項，依序是「成功 5」「快取 4」「失敗 3」「中止 2」「執行中 1」「等待 6」「已送出 7」：每個標籤與它的數字配成一對，順序照 011a C6 | 自動 |
| TC-R57 | 設計原話 5；C6 | 功能 | 同上 | GET `/?run=<F1>&lang=en` | 圖例七項依序是「Succeeded 5」「Cached 4」「Failed 3」「Aborted 2」「Running 1」「Pending 6」「Submitted 7」；圖例沒有 CJK 字元 | 自動 |
| TC-R58 | Q6 | 例外 | 甲有 U0（任務數全是 0） | GET `/?run=<U0>` | 任務條是空的（沒有任何填滿的部分；若用 `<progress>`，沒有 `value`）；圖例七項的數字全是 0 | 自動 |
| TC-R59 | Q6 | 例外 | 同上 | 同上 | 「目前步驟」「運算環境」兩張卡是「—」，「費用」卡是「SU —」；「耗時」卡仍有耗時值（不是「—」） | 自動 |
| TC-R60 | N2；設計稿畫面 7 | 功能 | 甲有 F1 | GET `/?run=<F1>` | 頁面由上到下的順序是：標題列、四張摘要卡、任務條與圖例、本 run 的通知、分頁連結列、分頁內容 | 自動 |
| TC-R61 | N2；N1 | 功能 | 甲有 F1 | 同上 | 「本 run 的通知」區恰好一個通知（失敗通知，內容同 TC-R01 至 TC-R10） | 自動 |
| TC-R62 | N2；N1 | 功能 | 甲有 L1 | GET `/?run=<L1>` | 「本 run 的通知」區恰好一個通知（失聯通知，內容同 TC-R13） | 自動 |
| TC-R63 | N2；Q6；設計原話 1 | 例外 | 甲有 U1（執行中，沒問題） | GET `/?run=<U1>` | 「本 run 的通知」區沒有通知，寫「目前沒有需要你處理的事」 | 自動 |
| TC-R64 | 設計原話 5；Q6 | 例外 | 同上 | GET `/?run=<U1>&lang=en` | 同一處寫「Nothing needs you right now」，頁面該區沒有 CJK 字元 | 自動 |
| TC-R65 | 011a G7 | 功能 | 甲有 F1、U1 | GET 兩個 run 的每個分頁 | 任何地方的時間都是台北時間 `MM-DD HH:mm`（F1 開始 `11-14 08:00`、結束 `11-14 10:05`），沒有原始 ISO 字串 | 自動 |
| TC-R66 | 專長守則（ui）；States | 功能 | 甲有 U1、F1、L1 | 各自 GET | 每個狀態的輸出同時含符號、文字與狀態 class（標題徽章、通知等級標籤），不只靠 class 顏色 | 自動 |

## User Story 4 — 分頁與分頁內容（優先度 P1）

對應計畫 N2（tabs）、裁定 Q5、Q6、Q7。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-R70 | N2；Q5 | 功能 | 甲有 F1 | GET `/?run=<F1>` | 分頁列恰好五個連結，依序「任務」「日誌」「執行資訊」「設定檔」「指標」，連結的 `tab` 參數依序是 `tasks`、`logs`、`info`、`config`、`metrics`，並保留 `run=<F1>` | 自動 |
| TC-R71 | 設計原話 5；Q5 | 功能 | 同上 | GET `/?run=<F1>&lang=en` | 分頁名稱依序「Tasks」「Logs」「Run info」「Configuration」「Metrics」，沒有 CJK 字元 | 自動 |
| TC-R72 | Q5 | 功能 | 同上 | GET `/?run=<F1>`（沒有 `tab`） | 預設顯示「任務」分頁的內容，「任務」連結被標為目前分頁 | 自動 |
| TC-R73 | Q5 | 例外 | 同上 | GET `/?run=<F1>&tab=bogus`、`&tab=`（空值）、`&tab=TASKS` | 都當預設：顯示「任務」分頁，不是 500、不是空白頁、不是 404 | 自動 |
| TC-R74 | Q5 | 功能 | 同上 | 分別 GET `tab=tasks`、`logs`、`info`、`config`、`metrics` | 每次恰好一個連結被標為目前分頁（`aria-current`），就是被選的那個；目前分頁的標示不只靠顏色（有 `aria-current` 或文字／粗體等非顏色標記） | 自動 |
| TC-R75 | Q5；N3 | 功能 | 同上 | GET `/?run=<F1>&stage=running&tab=info` | 頁頭「中」「EN」兩個連結都保留 `run`、`stage`、`tab`，只有 `lang` 不同 | 自動 |
| TC-R76 | Q5；N3 | 功能 | 同上 | 同上 | 階段條的連結與上／下一階段連結保留 `run`、`tab` 與目前語言，只改 `stage` | 自動 |
| TC-R77 | N3；011a B6 | 功能 | 甲有 F1 | GET 五個分頁（`lang=en`） | 頁上每一個產生的連結（分頁、階段條、頁碼、通知裡的名稱、左右欄）都帶 `lang=en` | 自動 |
| TC-R78 | N2（"server-side links, zero JS"） | 功能 | 同上 | 讀五個分頁的 HTML | 分頁是單純的 `<a href>`；沒有 `<script`、沒有 `on*=`、沒有用 `<input type=radio/checkbox>` 切換 | 自動 |
| TC-R79 | N2（Tasks 分頁） | 功能 | 甲有 F1（兩個失敗任務） | GET `/?run=<F1>&tab=tasks` | 失敗任務表有欄位「名稱」「結束代碼」「錯誤訊息（第一行）」「工作目錄」，兩列：`FASTQC (sample2)` / 137 / `Process exceeded memory`；`TRIMGALORE (sample3)` / 1 / `cutadapt failed` | 自動 |
| TC-R80 | N2 | 功能 | 同上 | 同上 | 第一個任務的錯誤訊息只顯示第一行；第二行 `second line` 不在表裡 | 自動 |
| TC-R81 | N2；Q7 | 功能 | 以純函式餵一個帶 `workdir` 的失敗任務 `{name, exit_code, error_message, workdir: "/w/ab/cdef12"}` | 渲染 Tasks 分頁 | 工作目錄欄顯示 `/w/ab/cdef12` | 自動 |
| TC-R82 | Q7 | 例外 | F1 的失敗任務沒有 `workdir`（目前 `get_run` 不回） | GET `/?run=<F1>&tab=tasks` | 工作目錄欄顯示「—」（或這一欄不存在）；整頁沒有 `None`、`null`、`undefined` | 自動 |
| TC-R83 | Q6 | 例外 | 甲有 U1（沒有失敗任務） | GET `/?run=<U1>&tab=tasks` | 表的位置寫「沒有失敗的任務」，沒有空表頭 | 自動 |
| TC-R84 | 設計原話 5；Q6 | 例外 | 同上 | GET `…&lang=en` | 寫「No failed tasks」，沒有 CJK 字元 | 自動 |
| TC-R85 | 設計原話 5 | 功能 | 甲有 F1（純 ASCII） | GET 「任務」「執行資訊」分頁（`lang=en`） | 兩個分頁的表頭、欄位名、說明文字都是英文，沒有任何 CJK 字元 | 自動 |
| TC-R86 | 專長守則（ui）；011a TC-H12 | 例外 | 失敗任務的名稱、錯誤訊息、工作目錄都含 `<img src=x onerror=1>` | 渲染 Tasks 分頁 | 文字以跳脫後的樣子出現，沒有未跳脫的標籤 | 自動 |
| TC-R87 | N2（Run info） | 功能 | 甲有 F1 | GET `/?run=<F1>&tab=info` | 執行資訊列出：id、名稱、狀態（符號＋文字）、開始 `11-14 08:00`、結束 `11-14 10:05`；每個值都跟它的欄位名成對 | 自動 |
| TC-R88 | N2；Q7 | 例外 | 甲有 U1（還在跑，沒有 ended_at） | GET `/?run=<U1>&tab=info` | 結束欄是「—」，不是 `None`、不是空白 | 自動 |
| TC-R89 | N2；Q7 | 功能 | 以純函式餵一個帶 `cancel_requested_at` 的 run 資料 | 渲染 Run info 分頁 | 顯示該時間（台北時間 `MM-DD HH:mm`）與它的欄位名 | 自動 |
| TC-R90 | Q7 | 例外 | `get_run` 沒有 `cancel_requested_at`（目前如此） | GET `/?run=<F1>&tab=info` | 這個事實欄位不出現（或寫「—」）；整頁沒有 `None`、`null` | 自動 |
| TC-R91 | N2；Q5 | 功能 | 甲有 F1 | GET `tab=logs`、`tab=config`、`tab=metrics` | 三個分頁各是一塊灰色面板，寫「之後開放」；面板裡沒有日誌文字、沒有表單、沒有連結 | 自動 |
| TC-R92 | 設計原話 5 | 功能 | 同上 | 同上，`lang=en` | 三個灰色面板寫「Coming later」，沒有 CJK 字元 | 自動 |
| TC-R93 | N2（Logs 不依賴 #138） | 功能 | 同上 | 讀 `web.py`、`web_board.py` 與 parity 測試 | 網頁沒有呼叫 `read_task_log`（或任何新動作）；`WEB_ROUTES` 仍只有 `list_runs`、`get_run` | 自動 |

## User Story 5 — 擁有者、404、前端限制、唯讀（優先度 P1）

對應計畫 N3、N4，專長守則（backend）與（ui）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-R100 | N3；專長守則（backend）跨使用者讀取 | 例外 | 乙有 B1；甲登入 | 甲 GET `/?run=<B1>`，分別加 `&tab=tasks`、`logs`、`info`、`config`、`metrics`，以及 `&lang=en` | 都得到 404，而且和「不存在的 id」的 404 逐位元組相同；頁面不回聲請求的 id、也不回聲 `tab` | 自動 |
| TC-R101 | N3；011a TC-H05 | 例外 | 甲登入 | GET `/?run=nope&tab=info` | 404，和 TC-R100 的頁面逐位元組相同 | 自動 |
| TC-R102 | N3；011a TC-H01 | 例外 | 沒有登入 cookie | GET `/?run=<F1>&tab=info`、帶 Bearer header 的同一網址 | 都回 303 到 `/login`，不洩漏任何 run 資料 | 自動 |
| TC-R103 | N3；專長守則（ui）限制 | 功能 | 甲有 F1、L1、U1、S1 | GET 執行中階段頁的五個分頁與 `/`，各取 zh、en | 每頁恰好一個 `<style>`、沒有 `<link rel=stylesheet>`；沒有 `<script`；沒有 `style=` 屬性；沒有 `on*=`；沒有 `http://`、`https://`、`//` 開頭的外部網址 | 自動 |
| TC-R104 | N3；011a TC-H13 | 功能 | 同上 | 讀同樣各頁的回應標頭 | CSP 標頭存在：沒有 `script-src`、沒有 `'unsafe-inline'`；`style-src` 是那一份內嵌樣式表的 sha256，且和頁面內容算出來的相符（樣式表為了通知與新版面而變動，hash 跟著變） | 自動 |
| TC-R105 | 011a G9 | 功能 | 同上 | 對這些頁面上的每一個站內連結發 GET（帶登入 cookie） | 每一個連結都解析成功（200，或預期的 303），沒有死連結 | 自動 |
| TC-R106 | N3 | 功能 | v3 加 011a 的路由集合 | 比對網站實際路由與 011a TC-G04、`owner_binding` tc068 釘的路由集合 | 兩者相同；若 011b 新增了路由，它必須同時出現在這兩個釘住的集合與 parity 的 `WEB_ROUTES` 裡（缺一邊就紅）；沒有新增任何會寫入的路由（沒有 POST/PUT/DELETE 的新路徑） | 自動 |
| TC-R107 | N3；專長守則（backend）對等性 | 功能 | `platform/tests/test_web_parity.py` | 執行 parity 測試 | 全綠；`WEB_ROUTES` 只有 `list_runs`、`get_run`；OWED 的字面名單與 011a 相同或只變短，沒有新增名字；`web.py`、`web_board.py` 的 AST 掃描只呼叫 `WEB_ROUTES`、`WEB_ONLY`、`INTERNAL` 裡的名字，也沒有 import `confirm`、`jobs`、`compute_envs`、`agents`、`status` | 自動 |
| TC-R108 | N4；011a TC-H17 | 功能 | AST 掃描 | 掃 `web.py`、`web_board.py` 裡每個 `list_runs`、`get_run` 的呼叫，包括這次新增的（通知取失敗任務名稱、執行中階段頁） | 每一個都帶 `caller=` 而且不是 None（擁有者規則留在動作層） | 自動 |
| TC-R109 | N4；011a TC-H11 | 功能 | 甲有 F1、L1 | POST 到 `/`、`/?run=<F1>&tab=info`；列出五個分頁每頁的 `<form>` | POST 回 405；每一頁的 `<form>` 只有登出那一個（帶 CSRF）；灰按鈕不是表單也不是連結 | 自動 |
| TC-R110 | N4；N3 | 功能 | 記錄 db 檔的 hash | 依序 GET `/`、F1 與 L1 與 U1 的五個分頁 | GET 之後 db 檔的 hash 都沒變（沒有任何寫入） | 自動 |
| TC-R111 | N3 | 功能 | 取出頁面內嵌樣式表 | 掃新增的 class（通知、摘要卡、任務條、圖例、分頁、失敗任務表） | 它們的 `overflow-wrap:anywhere`（或等效）與 flex／grid 子元素的 `min-width:0` 都有，長名稱與長原因會換行；`@media (max-width:900px)` 下三欄仍是單欄，摘要卡能折行 | 自動 |
| TC-R112 | 專長守則（ui）「不自創顏色」 | 功能 | 取出頁面內嵌樣式表 | 重跑 011a 的 TC-S14、TC-S15、TC-S16 | 通知等級標籤、摘要卡、表格的新規則所用的顏色、字級、間距、圓角都在 DESIGN.md 的 token 集合內 | 自動 |
| TC-R113 | 設計原話 6；ADR 0004；R8 | 功能 | 甲有 F1 | GET 執行中階段頁五個分頁（zh、en）、`/` | 全文不含 011a TC-S31 掃的其他平台名稱，也不含 Jev 字樣（011a TC-N14） | 自動 |
| TC-R114 | N3；011a TC-H14 | 功能 | 甲登入 | GET `/`、`/?run=<F1>&tab=info`、`/settings` | `<meta http-equiv="refresh" content="15">` 只在 `/` 路徑（含 `?run=`、`?tab=`）上，其他頁沒有 | 自動 |
| TC-R115 | N4 | 功能 | 取 F1 的 Tasks 分頁與 Run info 分頁 | 查看標題列、分頁、通知的鍵盤順序 | 分頁連結都是可用鍵盤到達的 `<a>`；樣式表對連結有 `:focus-visible` 的 outline（011a TC-S18 仍成立） | 自動 |
| TC-R116 | 專長守則（backend）錯誤訊息 | 例外 | 乙的 run 或不存在的 run | 取 404 頁 | 404 頁說明「沒有這個 run，或它不是你的」並提供回到「現在」的連結；沒有堆疊、內部路徑、SQL | 自動 |

## User Story 6 — 文件、被改動的舊測試、人工檢視（優先度 P2）

對應計畫 N4、N5、Q1、Q7、Q10。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01 | N4（"any changed pin logged in the ledger"） | 功能 | 實作完成 | 與 `main`／v3 比對 `platform/tests/` 與 `tests/` 的 diff | 每一個被改的既有斷言都在 `specs/011b-running-page/ledger.md` 有一列「舊／新／理由」；沒有斷言被刪掉而沒有替代、沒有被 skip、沒有被放寬 | 手動：`docs/TESTING.md`（011b 帳本檢視） |
| TC-D02 | Q1；N4 | 功能 | 同上 | 讀帳本 | 帳本有一列說明 011a 的 TC-L34（「reason not recorded」）、TC-S34、TC-L25 的 pin 搬到通知元件的「原因」欄，寫出舊、新、理由 | 手動：`docs/TESTING.md` |
| TC-D03 | Q7 | 功能 | 同上 | 讀帳本 | 帳本記下三件「欠著」的事：運算環境名稱、工作目錄欄、發射事實（`cancel_requested_at` 等）在動作層提供之前顯示「—」或不出現；並寫明 #138 若已進 v3 則改用 | 手動：`docs/TESTING.md` |
| TC-D04 | 憲法「測試案例的作者不得改規格」 | 功能 | 同上 | 執行 `git diff <base>...HEAD -- DESIGN.md PRODUCT.md specs/011b-running-page/test-case.md specs/011b-running-page/test-case-overview.md` | 輸出為空（實作期間沒有改規格與測試案例） | 手動：`docs/TESTING.md` |
| TC-D05 | Q10；N5 | 功能 | 同上 | 讀 `docs/TESTING.md` | 有一節 011b 手動步驟，寫得出能照做：要拍的頁面（「現在」與失敗 run 的執行中階段頁）、桌面 1440 與手機 390 兩個寬度、中文與英文、用 CDP 裝置模擬、`scrollWidth == clientWidth` 的檢查方式 | 手動：`docs/TESTING.md` |
| TC-D06 | N4（"Existing 011a tests stay green"） | 功能 | 實作完成 | 在 WSL 或 CI 跑 `bash tests/platform_test.sh`（含 `test_web_board.py`、`test_web_parity.py`、`test_confirm_page.py`、`test_owner_binding.py`） | 全綠；011a 沒有因為本次改動而失敗，被改的 pin 都對應 TC-D01 的帳本列 | 自動 |
| TC-D07 | 專長守則（backend）結構變動 | 功能 | 實作完成 | 與 v3 比對 `platform/abf_platform/` 裡的資料結構檔（`store.py`、索引 schema、migration 目錄）的 diff | 沒有新的表、欄位、migration；計畫已寫「nothing stored (no new table/column)」，所以不需要 migration | 手動：`docs/TESTING.md` |
| TC-V01 | N5；原話 1「進來之後馬上可以看到各個run的狀態與進度」 | 功能 | 本機啟動 `abf-platform web`（loopback），灌入含 running、failed、lost、succeeded 的 e2e 假 run | 以 CDP 裝置模擬 1440 寬，中文與英文，各拍「現在」與一個失敗 run 的執行中階段頁（共 4 張） | 四張截圖附在 PR；看得到：需要注意卡裡是正式通知方框、失敗 run 頁有標題列、四張摘要卡、任務條與圖例、本 run 的通知、五個分頁；中文版全中文、英文版全英文 | 手動：`docs/TESTING.md` |
| TC-V02 | N5；專長守則（ui）手機寬度 | 功能 | 同上 | 同上，改 390 寬（手機），中文與英文，同樣 4 張 | 四張截圖附在 PR；單欄、順序中欄、右欄、左欄；通知與摘要卡沒有被切掉 | 手動：`docs/TESTING.md` |
| TC-V03 | N5 | 功能 | 同上 | 在 390 寬對上述 4 個頁面讀 `document.documentElement.scrollWidth` 與 `clientWidth` | 每個頁面兩個數字相等（沒有橫向捲動），數字寫進 PR | 手動：`docs/TESTING.md` |
| TC-V04 | 專長守則（ui）鍵盤 | 功能 | 同上 | 在失敗 run 的頁上只用 Tab 鍵走過：頁頭、分頁連結、通知裡的名稱連結 | 每一個停點都看得到焦點外框；灰按鈕不會被當成可按的停點 | 手動：`docs/TESTING.md` |
| TC-V05 | 專長守則（ui）驗收；偵測器 | 功能 | 把「現在」、F1、L1、U1 的五個分頁渲染成 HTML 檔 | 對每個 HTML 跑 Impeccable 偵測器（唯讀） | 沒有違反 DESIGN.md 的 token／畫面／狀態；其他發現（對比、字型、範本味）列給維護者看，不判 FAIL | 手動：`docs/TESTING.md` |
| TC-V06 | 維護者 2026-10-19「網頁外框可暫定這版 但可以更好」；原話 7 | 功能 | 同 TC-V01 的截圖 | 維護者看截圖 | 維護者判斷：通知看起來是不是「制式化的通知」而不是口語句子；外框是否維持他暫定的這版；「可以更好」的地方記進下一輪 | 手動：`docs/TESTING.md` |

## User Story 7 — 這次不做的事（不在範圍）

對應計畫「Out of scope」與 N2 的「不要依賴 #138」；設計原話 3。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-N01 | 不在範圍：網頁上的任何寫入動作 | 不在範圍 | 甲有 F1、L1 | 對 `/resume`、`/rerun`、`/relaunch`、`/cancel`、`/launch`、`/forget`、`/run/<id>/resume` 發 GET 與 POST；按下「續跑」「重跑」（灰按鈕） | 路徑都是 404 或 405；灰按鈕按下去沒有任何請求；資料庫沒有任何變化 | 自動 |
| TC-N02 | 不在範圍：上傳 | 不在範圍 | 甲登入 | 看 `/` 與 F1 頁左欄的「↑ 上傳資料」 | 仍是灰字「之後開放」，沒有檔案輸入欄、沒有拖放區 | 自動 |
| TC-N03 | 不在範圍：送出（launch，012b） | 不在範圍 | 甲有 F1 | GET `/?run=<F1>&stage=launch` | 仍是 011a 的占位內容「—」與 012b，沒有送出表單、沒有分頁、沒有四張摘要卡 | 自動 |
| TC-N04 | 不在範圍：結果階段（011c） | 不在範圍 | 甲有 S1 | GET `/?run=<S1>&stage=results`，與 `…&stage=results&tab=info` | 頁面是 011a 的結果階段內容，沒有 `tab` 連結列、沒有四張摘要卡、沒有任務條圖例；`tab` 參數被忽略 | 自動 |
| TC-N05 | 不在範圍：費用頁（012d） | 不在範圍 | 甲登入 | GET `/cost`；看 F1 頁的「費用」卡與頂欄 | `/cost` 是 404；費用卡與頂欄都是「SU —」，沒有數字、沒有連結 | 自動 |
| TC-N06 | 不在範圍：聊天（014） | 不在範圍 | 甲登入 | 看右欄「分析進度｜聊天」切換 | 「聊天」仍是灰字「之後開放」，沒有輸入框；通知裡沒有 AI 回覆文字 | 自動 |
| TC-N07 | 不在範圍：JS | 不在範圍 | 甲登入 | 掃新增頁面的 HTML、頁面載入的資源 | 沒有 `<script`、沒有 `on*=`；沒有任何 fetch／XHR 需要的程式碼 | 自動 |
| TC-N08 | 不在範圍：日誌內容（等 #138；N2） | 不在範圍 | 甲有 F1 | GET `/?run=<F1>&tab=logs` | 只有灰面板「之後開放」，沒有任何日誌文字，也沒有去讀日誌的動作被呼叫 | 自動 |
| TC-N09 | 設計原話 3「AI一律先除錯」；不在範圍：AI 自動處理 | 不在範圍 | 甲有 F1 | 讀通知與整頁 | 通知的「可選動作」只有「續跑／重跑（之後開放）」，沒有任何「AI 正在處理」「已自動修復」之類的字；自動處理屬之後的切片 | 自動 |
| TC-N10 | 不在範圍：新資料或新表（"nothing stored"） | 不在範圍 | 甲有 F1 | 看資料庫檔與 `docs/` | 沒有新的表、欄位、檔案；通知、分頁、已讀狀態都不被儲存 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-K01 | 憲法 I.2（不保存第二份 run 狀態）；原話 1 | 功能 | 甲有 F1（failed），通知已顯示 | 在索引裡把 F1 改成 succeeded，再 GET `/` 與 `/?run=<F1>` | 通知立刻消失（「需要注意」卡數字少 1；本 run 的通知區變成「目前沒有需要你處理的事」）：通知每次請求重算，沒有被保存或快取 | 自動 |
| TC-K02 | 憲法 I.2 的檢查 | 功能 | 實作完成 | 跑 `bash tests/no_second_run_state_test.sh` | 綠；本次沒有新增任何會保存 run 狀態的檔案 | 自動 |
| TC-K03 | 安全網：平台寫入工具都要人答應 | 功能 | 實作完成 | 與 v3 比對 `hooks/`、`.claude/`、`platform/abf_platform/actions/`、`jobs.py`、`mcp_server.py`、`store.py` 的 diff；跑 `test_actions_layer.py`、`test_human_channel.py`、`test_resume_entrypoints.py`、`test_keep_submissions.py` | 這些檔案沒有 diff；四個測試檔全綠；網頁沒有新增任何寫入路徑（灰按鈕是死的，不是半成品的寫入） | 自動 |
| TC-K04 | 安全網：憑證不外洩 | 功能 | 失敗原因與任務錯誤訊息裡放一個看起來像憑證的字串 | GET 通知與 Tasks 分頁 | 平台自己的 session cookie、CSRF 值、token 不出現在通知、分頁、錯誤頁；run 提供的字串只依原樣跳脫後顯示（平台不另外保存） | 自動 |
| TC-K05 | ADR 0009 第 7 點／#116：網頁一律傳呼叫者 | 例外 | 乙有 B1；乙登入另有 token | 用乙的身分 GET 甲的 F1 頁（五個分頁）；用甲的身分 GET 乙的 B1 頁 | 兩個方向都得到相同的 404；讀取篩選在動作層，不是靠畫面藏起來 | 自動 |
