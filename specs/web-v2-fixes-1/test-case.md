# 測試案例：網頁 v2 第一批修正（標題列按鈕收進選單、失敗 run 階段條與目前步驟、左欄長名稱換行）

<!--
Written by the verifier (CONTRACT mode). Source of truth: specs/web-v2-fixes-1/plan.md (including 裁決 1~9, which win over the body), DESIGN.md, and the maintainer's words quoted there. Nothing here is invented beyond the plan.
-->

**規格**：`specs/web-v2-fixes-1/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫「不做」或「不准動」的事；測試確認它真的沒做。

驗證方式「自動」＝寫在 `platform/tests/test_web_fixes_1.py`（計畫的 test_f01～f08 之下，或同檔補的斷言），或是既有測試不改仍綠；每條新測試要在註解寫出它的 TC 編號。「手動」＝閱卷者看 `git diff`、`ledger.md` 或 PR 截圖（本任務不動 `docs/TESTING.md`，所以沒有 TESTING.md 的步驟可對照）。

## 標準種子（下面簡稱「標準種子」）

沿用 `test_web_v2_skeleton.std`。Ann 登入，其中用到的：

| 代稱 | 狀態 | 補充 |
|---|---|---|
| ann-running | running | 有一個執行中的步驟 |
| ann-failed-resume | failed | 失敗任務 `NFCORE_AMPLISEQ:DADA2_DENOISING`；有成功任務，所以 `failure.actions[0]` 是續跑 |
| ann-done | succeeded | |
| ann-failed-relaunch | failed | 失敗任務 `TRIMGALORE (s1)`；沒有成功任務，所以 `failure.actions[0]` 是重跑 |
| ann-lost | lost | 沒有失敗任務 |
| ann-cancelled | failed（已要求取消） | 沒有失敗任務 |
| bob-failed | failed | Bob 的，不是 Ann 的 |

「看得到的按鈕」＝把頁面裡所有 `<details>…</details>` 去掉之後，中欄（`data-pane="middle"`）加右欄（`data-pane="right"`）的 `<button>`（裁決 4；左欄底部的「登出」不算）。

## User Story 1 — 標題列的按鈕收進「更多」選單，只留右欄那一顆（優先度 P1）

維護者原話 2：developer-agent 問「失敗頁上方還留著『續跑／重跑／取消』三顆按鈕，右欄又有一顆『續跑』。要不要把上方三顆收進選單，只留右欄那一顆？」維護者答：「按照你的建議。」
維護者原話 1：「狀態只要running, failed, successed就好，failed下面再去分原因，看是要改參數、重跑、續跑，直接告訴使用者要做甚麼，不是讓他們選。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；test_f01；原話 2 | 功能 | 標準種子 | Ann 開 ann-failed-resume 的頁面（中文） | 標題列（`<div class="head">`）內每一個 `<form class="act">` 都在 `<details class="menu">` 裡面；標題列在 `<details>` 外面沒有任何按鈕表單 | 自動 |
| TC-002 | 作法 1；test_f01 | 功能 | 同上 | 看同一個 `<details class="menu">` | 沒有 `open` 屬性（預設關著）；`<summary>` 文字是「更多」 | 自動 |
| TC-003 | 作法 1；裁決 2；test_f01 | 功能 | 同上 | 開同一頁加 `?lang=en` | `<summary>` 文字是 `More`，仍在關著的 `<details class="menu">` 裡 | 自動 |
| TC-004 | test_f02；原話 2 | 功能 | 標準種子 | 開 ann-failed-resume 的頁面；去掉所有 `<details>…</details>` | 中欄＋右欄的 `<button>` 恰好 1 顆，在右欄，文字是「續跑」 | 自動 |
| TC-005 | test_f02；原話 2 | 功能 | 標準種子 | 開 ann-failed-relaunch 的頁面；去掉所有 `<details>…</details>` | 中欄＋右欄的 `<button>` 恰好 1 顆，在右欄，文字是「重跑」 | 自動 |
| TC-006 | test_f02；作法 3 與 DESIGN 失敗通知（lost 也走同一個通知） | 功能 | 標準種子 | 開 ann-lost 的頁面；去掉所有 `<details>…</details>` | 中欄＋右欄的 `<button>` 恰好 1 顆，在右欄，文字是該 run `failure.actions[0]` 對應的字（續跑或重跑） | 自動 |
| TC-007 | 原話 1；test_f02 | 功能 | 標準種子 | 開 ann-failed-resume 與 ann-failed-relaunch 的頁面 | 唯一看得到的那顆按鈕的字，跟右欄通知「之後」欄開頭的動作字一樣（續跑對續跑、重跑對重跑）：頁面直接告訴使用者做什麼，不是讓他在三顆裡選 | 自動 |
| TC-008 | 作法 1；test_f03 | 功能 | 標準種子 | 開 ann-failed-resume 的頁面，看 `<details>` 裡的表單 | 三個表單依序是 `/act/resume`、`/act/relaunch`、`/act/cancel`，按鈕文字依序是「續跑」「重跑」「取消」，跟改之前一樣 | 自動 |
| TC-009 | 作法 1；test_f03 | 功能 | 同上，加 `?lang=en` | 看 `<details>` 裡的表單 | 按鈕文字依序是 `Resume`、`Re-run`、`Cancel`，每個表單有 `<input type="hidden" name="lang" value="en">` | 自動 |
| TC-010 | 作法 1；test_f03 | 功能 | 標準種子 | 看 `<details>` 裡每個表單的隱藏欄位 | 每個表單都有 `run`（值＝這個 run 的 id）和 `csrf`（非空）兩個隱藏欄位，跟改之前一樣 | 自動 |
| TC-011 | 作法 1 | 功能 | 標準種子 | 看 `<details>` 裡的連結 | 「用這個 run 的內容再啟動一次」（en `Launch again from this run`）的連結在 `<details>` 裡、排在三個表單之後，網址是 `/launch?from=<這個 run 的 id>`（en 加 `&lang=en`），跟改之前一樣 | 自動 |
| TC-012 | 作法 1；test_f03 | 功能 | 標準種子，記下 job 數量 | 以 Ann 身分，用選單裡 `/act/resume` 表單的欄位 POST | 回的是確認頁（要人再按確認），沒有建立任何 job | 自動 |
| TC-013 | 作法 1；test_f04 | 功能 | 標準種子 | 開 ann-running 的頁面；去掉所有 `<details>…</details>` | 中欄＋右欄的 `<button>` 0 顆 | 自動 |
| TC-014 | 作法 1（執行中也收進選單）；test_f04 | 功能 | 標準種子 | 開 ann-running 的頁面 | 標題列有關著的 `<details class="menu">`，`<summary>` 是「更多」，裡面有三個表單（續跑、重跑、取消，順序同 TC-008）和「再啟動一次」連結 | 自動 |
| TC-015 | 作法 1（只在 running 階段頁出現） | 例外 | 標準種子 | 開 ann-done（已完成）的頁面 | 頁面沒有 `<details class="menu">`，標題列沒有任何 `<form class="act">`（跟改之前一樣沒有按鈕） | 自動 |
| TC-016 | 作法 1（只在 running 階段頁出現） | 例外 | 標準種子 | 開 ann-failed-resume 的頁面，加 `?stage=launch`（看別的階段） | 頁面沒有 `<details class="menu">`，標題列沒有任何 `<form class="act">`（跟改之前一樣） | 自動 |
| TC-017 | 作法 1；裁決 5 | 功能 | 標準種子 | 看樣式表 | `.menu > summary` 的規則含 `min-height:44px`（點擊目標高度 ≥ 44px），並用 flex／align-items 置中 | 自動 |
| TC-018 | 作法 1（鍵盤可聚焦、焦點外框可見） | 功能 | 標準種子 | 看 HTML 與樣式表 | `<summary>` 是 `<details>` 的原生第一個子元素（不靠 JavaScript 就能用鍵盤開關）；樣式表裡 `summary:focus-visible` 的外框規則仍在，且沒有任何規則對 `.menu` 或 `summary` 設 `outline:none`／`outline:0` | 自動 |

## User Story 2 — 失敗 run 的階段條與「目前步驟」說實話（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 作法 2；test_f05 | 功能 | 標準種子 | 開 ann-failed-resume 的頁面（中文），讀階段條「執行」那一格 | 文字是「✗ 執行」（有符號 ✗ 也有字），不是「執行中」 | 自動 |
| TC-020 | 作法 2；裁決 7；test_f05 | 功能 | 同上 | 同一格的 class | 同時含 `is-current` 和 `is-failed` | 自動 |
| TC-021 | 作法 2；test_f05 | 功能 | 標準種子 | 開 ann-lost 的頁面 | 「執行」那一格文字是「✗ 執行」，class 同時含 `is-current` 和 `is-failed`（lost 跟 failed 一樣） | 自動 |
| TC-022 | 作法 2；裁決 2；test_f05 | 功能 | 標準種子 | 開 ann-failed-resume 的頁面加 `?lang=en` | 「執行」那一格文字是「✗ Run」，class 含 `is-failed`；這個階段條沒有中文字 | 自動 |
| TC-023 | 作法 2；test_f05 | 功能 | 標準種子 | 開 ann-running 的頁面 | 「執行」那一格仍是「執行中」，class 沒有 `is-failed` | 自動 |
| TC-024 | 裁決 7 | 功能 | 標準種子 | 開 ann-done 的頁面 | 「執行」那一格維持現況「✓ 執行中」，class 是 `is-done`，沒有 `is-failed` | 自動 |
| TC-025 | 作法 2（其他格不變） | 功能 | 標準種子 | 開 ann-failed-resume 的頁面，讀五格 | 文字依序是「✓ 送出」「✗ 執行」「結果」「下游」「完成」；class 依序是 `is-done`、`is-current is-failed`、`is-later`、`is-later`、`is-later`（除了「執行」格都跟改之前一樣） | 自動 |
| TC-026 | 作法 2；裁決 6 | 功能 | 標準種子 | 看樣式表 | 有 `.steps .is-failed` 規則，顏色用既有失敗色 token（`var(--failed)` 或 `state-failed` 設的 `var(--c)`），沒有新寫死的色碼 | 自動 |
| TC-027 | 作法 3；test_f06 | 功能 | 標準種子 | 開 ann-failed-resume 的頁面（中文），讀摘要卡片標題 | 第一張卡片標題是「停在」，不是「目前步驟」 | 自動 |
| TC-028 | 作法 3；test_f06 | 功能 | 同上 | 讀第一張卡片內容 | 是 `NFCORE_AMPLISEQ:DADA2_DENOISING` | 自動 |
| TC-029 | 作法 3 | 功能 | 標準種子 | 開 ann-failed-relaunch 的頁面 | 第一張卡片標題「停在」，內容 `TRIMGALORE (s1)`（第一個失敗任務名） | 自動 |
| TC-030 | 作法 3；test_f06 | 功能 | 標準種子 | 開 ann-cancelled（failed 且沒有失敗任務）的頁面 | 第一張卡片標題「停在」，內容是 `—` | 自動 |
| TC-031 | 作法 3（failed／lost 都改） | 功能 | 標準種子 | 開 ann-lost（沒有失敗任務）的頁面 | 第一張卡片標題「停在」，內容是 `—` | 自動 |
| TC-032 | 作法 3；裁決 2 | 功能 | 標準種子 | 開 ann-failed-resume 的頁面加 `?lang=en` | 第一張卡片標題 `Stopped at`，內容 `NFCORE_AMPLISEQ:DADA2_DENOISING`；中欄沒有中文字 | 自動 |
| TC-033 | 作法 3；test_f06 | 功能 | 標準種子 | 開 ann-running 的頁面（中文與 `?lang=en`） | 第一張卡片標題仍是「目前步驟」（en `Current step`），內容仍是執行中步驟的名字，跟改之前一樣 | 自動 |
| TC-034 | 作法 3（只改標題與內容） | 功能 | 標準種子 | 開 ann-failed-resume 的頁面 | 另外三張卡片標題仍依序是「耗時」「運算環境」「費用」，內容規則跟改之前一樣 | 自動 |

## User Story 3 — 左欄長名稱換行（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 作法 4；裁決 8；test_f07 | 功能 | 標準種子 | 看樣式表 | `.r2` 的規則含 `overflow-wrap:anywhere` | 自動 |
| TC-036 | 作法 4（`NFCORE_AMPLISEQ:DADA2_DENOISING` 這種長字） | 功能 | 標準種子 | 開任一頁，讀左欄 ann-failed-resume 那列的第 2 行（`.r2`） | 內容是「<階段> · NFCORE_AMPLISEQ:DADA2_DENOISING」，長名字完整在 HTML 裡（沒有被程式截斷），由樣式讓它換行 | 自動 |
| TC-037 | 作法 4；裁決 8 | 功能 | 桌機版寬度 1440（用 Chrome DevTools 裝置模擬），標準種子，登入後開 ann-failed-resume | 看左欄；在瀏覽器 console 比 `document.documentElement.scrollWidth` 與 `clientWidth` | 長名字在左欄內換行，沒有超出左欄；`scrollWidth` 等於 `clientWidth`（沒有橫向捲動） | 手動：PR 截圖＋console 數字 |
| TC-038 | 作法 4；裁決 8 | 功能 | 手機寬度 390（`is_mobile` 的裝置模擬），同上 | 同上 | 長名字沒有超出欄位；`scrollWidth` 等於 `clientWidth` | 手動：PR 截圖＋console 數字 |

## User Story 4 — 不能放掉的限制（優先度 P1）

下列各條都同時對「失敗頁（ann-failed-resume）」與「執行中頁（ann-running）」檢查。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 限制「零 JavaScript」；test_f08 | 功能 | 標準種子 | 取兩頁 | 都沒有 `<script`（`<details>` 是原生元素，不算 JS） | 自動 |
| TC-040 | 限制「無 `style=`」；test_f08 | 功能 | 同上 | 取兩頁 | 都沒有 `style=` | 自動 |
| TC-041 | 限制「單一樣式表、CSP 雜湊相符」；test_f08 | 功能 | 同上 | 取兩頁與回應標頭 | 恰一個 `<style>`、沒有 `<link rel=stylesheet>`；CSP 標頭內的 sha256 與該 `<style>` 內容的雜湊相符（加了新規則之後仍相符） | 自動 |
| TC-042 | 限制「15 秒 refresh」；test_f08 | 功能 | 同上 | 取兩頁 | 都有 `<meta http-equiv="refresh" content="15">` | 自動 |
| TC-043 | 限制「英文頁無 CJK」；test_f08 | 功能 | 同上 | 取兩頁加 `?lang=en` | 中欄與右欄沒有任何中文字元（run 名稱本身除外） | 自動 |
| TC-044 | 限制「每人只看自己的 run」 | 例外 | 標準種子 | Ann 開 bob-failed 的網址 | 看不到 Bob 的 run（跟改之前一樣：不顯示 Bob 的名稱、步驟、按鈕與選單） | 自動 |
| TC-045 | 專長守則「狀態不只靠顏色」 | 功能 | 標準種子 | 取 ann-running、ann-done、ann-failed-resume、ann-lost 四頁的標題列徽章 | 每個徽章同時含符號與文字（▶ 執行中、✓ 完成、✗ 失敗；lost 與改之前一樣），沒有只剩 class 顏色的狀態 | 自動 |
| TC-046 | 專長守則「不載外部資源」 | 功能 | 標準種子 | 取失敗頁與執行中頁 | 沒有指向 `http://`／`https://` 的 `src`、CSS 載入或外部字型 | 自動 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | 「不做」：不動右欄通知 | 不在範圍 | 標準種子 | 開 ann-failed-resume 的頁面，看右欄 | 通知跟改之前一樣：級別「待處理」、欄位「步驟／原因／之後」、恰好 1 個表單與 1 顆按鈕；既有斷言（`test_web_running.py`、`test_web_v2_skeleton.py` 的通知相關測試）沒被改動而仍綠 | 自動 |
| TC-048 | 「不做」：不動確認頁、`/act/*`、`failures.py`、`actions/__init__.py` | 不在範圍 | 計畫的 worktree | `git diff v3...HEAD --stat` | 這四項沒有出現（`web_board.py` 裡的 `Acts.form` 輸出也沒變：同一個 action、隱藏欄位、按鈕文字） | 手動：看 git diff |
| TC-049 | 「不做」：不決定選單裡哪些動作該出現 | 不在範圍 | 標準種子 | 開 ann-failed-resume 與 ann-running 的頁面，數選單裡的表單 | 兩頁的選單都原樣放三個（續跑、重跑、取消）；沒有因為狀態被刪掉或新增（失敗 run 仍留「取消」） | 自動 |
| TC-050 | 「不做」：終端機、對話、自動續跑 | 不在範圍 | 標準種子，記下 job 數量 | 開失敗頁（GET） | 頁面沒有新增的終端機開關、輸入框或按鈕（中欄切換仍只有既有的灰色項目）；沒有建立任何 job（沒有自動續跑） | 自動 |
| TC-051 | 「其他測試檔一字不改」 | 不在範圍 | worktree | `git diff v3...HEAD -- platform/tests/` | `test_web_actions.py`、`test_confirm_page.py`、`test_web_confirm_plain.py`、`test_web_parity.py`、`test_resume_scope.py`、`test_launch_*.py`、`test_failures.py` 都沒有出現 | 手動：看 git diff |
| TC-052 | 「只限下方要改寫的既有斷言」；裁決 7 | 不在範圍 | worktree | `git diff v3...HEAD -- platform/tests/test_web_board.py platform/tests/test_web_running.py platform/tests/test_web_v2_skeleton.py`，對照 `ledger.md` | 被改的斷言只有：標題列／整頁數按鈕的（`test_web_board.py:703`、`:807`、`test_web_running.py:187`，改成在 `<details class="menu">` 內數，數量仍是 3 個表單、3 顆按鈕）、failed／lost 種子的階段條 class（`test_web_board.py:561-569`，改成含 `is-current` 與 `is-failed`）、failed run 卡片「目前步驟」為 `—` 的（改成「停在」加失敗步驟）；每條在 ledger 有「舊 → 新」與理由；沒有刪除、跳過或放寬其他斷言 | 手動：看 git diff＋ledger |
| TC-053 | 「範圍：檔案」 | 不在範圍 | worktree | `git diff v3...HEAD --stat` | 只有 `platform/abf_platform/web_board.py`、`platform/tests/` 下計畫列的四個檔案（`test_web_board.py`、`test_web_running.py`、`test_web_v2_skeleton.py`、新檔 `test_web_fixes_1.py`），以及 `specs/web-v2-fixes-1/` 底下的檔 | 手動：看 git diff |
| TC-054 | 維護者 10-23「先把功能做起來吧，以後再改美觀」；裁決 5、6 | 不在範圍 | worktree | 看 `web_board.py` 樣式表的 diff | 只新增 `.menu`、`.menu > summary`、`.steps .is-failed`、`.r2` 的 `overflow-wrap:anywhere`；沒有新顏色、字型、間距數值；唯一新數值是 `min-height:44px` | 手動：看 git diff |
| TC-055 | 裁決 8：`.nm` 維持省略號 | 不在範圍 | 標準種子 | 看樣式表的 `.nm` 規則 | 仍是單行省略號（`overflow:hidden;text-overflow:ellipsis;white-space:nowrap`），沒有 `overflow-wrap:anywhere` | 自動 |
| TC-056 | 「Never edit during implementation」 | 不在範圍 | worktree | `git diff v3...HEAD -- DESIGN.md PRODUCT.md docs/TESTING.md specs/web-v2-fixes-1/plan.md specs/web-v2-fixes-1/test-case.md specs/web-v2-fixes-1/test-case-overview.md` | 實作期間沒有改動這些檔（只允許 developer-agent 與 verifier 在計畫階段的提交） | 手動：看 git log／diff |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-057 | 不變條款 2：寫入只在人確認之後（頁面只問，不送出） | 功能 | 標準種子，記下 job 數量 | 以 Ann 身分，用選單裡 `/act/relaunch` 與 `/act/cancel` 表單的欄位各 POST 一次 | 兩次都回確認頁，沒有建立任何 job（跟 TC-012 的 resume 一樣；選單沒有繞過確認頁） | 自動 |
| TC-058 | 不變條款 2：不另存第二份 run 狀態 | 功能 | worktree | 跑 `bash tests/no_second_run_state_test.sh`；看 diff | 通過；「✗ 執行」與「停在」都是每次請求從 run 自己的紀錄算出，沒有新寫入檔案或欄位 | 自動：`tests/no_second_run_state_test.sh` |
| TC-059 | 開發流程：全套綠才算完成（裁決 1） | 功能 | worktree | 在 WSL 跑全套（`--timeout 900`），跑完先刪 `platform/**/__pycache__` | 計畫的八條新測試綠；全套綠，只允許 `tests/init_workspace_test.sh` 的「site side with no run area known fails clearly」這一條已知環境紅（base 同紅）；ledger 記下並寫 `GREEN <HEAD>` | 自動：`tests/run_all.sh`（WSL） |
