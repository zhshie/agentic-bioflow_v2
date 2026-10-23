# 測試案例：網頁改成 DESIGN.md v2 骨架（左欄清單、三狀態、右欄 Seqera 式失敗通知）

<!--
Written by the verifier (CONTRACT mode). Source of truth: specs/web-v2-skeleton/plan.md (including 裁決 1~9, which win over the body), DESIGN.md, and the maintainer's words quoted there. Nothing here is invented beyond the plan.
-->

**規格**：`specs/web-v2-skeleton/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫「不做」或「不准動」的事；測試確認它真的沒做。

驗證方式「自動」＝寫在 `platform/tests/test_web_v2_skeleton.py`（計畫的 test_v01～v16 之下），每條測試要在註解寫出它的 TC 編號。「手動」＝閱卷者看 `git diff` 或 PR 截圖。

## 標準種子（下面簡稱「標準種子」）

沿用 `test_web_board` 既有的 `seed()`；專案名依裁決 1 用 `nf-core/ampliseq`、`nf-core/rnaseq`（它其實是 Nextflow 的管線名，網頁照原字顯示）。Ann 登入，時間由新到舊：

| 代稱 | 擁有者 | 專案 | 狀態 | 補充 |
|---|---|---|---|---|
| ann-running | Ann | nf-core/ampliseq | running | 已完成 2、執行中 1、等待 2（共 5；不放快取，避免「完成數」要不要算快取的歧義）；1 小時前開始 |
| ann-failed-resume | Ann | nf-core/rnaseq | failed | 失敗任務 `NFCORE_AMPLISEQ:DADA2_DENOISING`；failure_reason 5 行（其中一行含「24 GB」）；有 succeeded 任務（所以 actions 以 resume 開頭）；2 小時前 |
| ann-done | Ann | nf-core/ampliseq | succeeded | 3 小時前 |
| ann-failed-relaunch | Ann | nf-core/rnaseq | failed | 沒有任何 succeeded／cached 任務（只有 relaunch）；4 小時前 |
| ann-lost | Ann | 無 | lost | 5 小時前 |
| ann-cancelled | Ann | 無 | 已要求取消（failure.status_seqera 為 cancelled） | 6 小時前 |
| bob-failed | Bob | 無 | failed | 30 分鐘前（全場最新，但不是 Ann 的） |

在此種子下，Ann 的 `/` 預設應選中 ann-failed-resume（Ann 自己最新的 failed／lost）。

## User Story 1 — `/` 沒有自己的頁：預設選一個分析、空狀態、只看自己的（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法「`/` 不再有自己的頁」1；計畫 test_v01 | 功能 | 標準種子，Ann 已登入 | `GET /`（沒有 `?run=`） | 回 200（不是 301／302／303 轉址）；中欄 `<h1>` 是 `ann-failed-resume`（不是較新的 ann-running，也不是 Bob 的） | 自動 |
| TC-002 | 作法「拿掉」；DESIGN「No "Now" entry」；維護者原話「"現在"的這個中間畫面有點多餘」；test_v01 | 功能 | 同 TC-001 | `GET /` | 頁面沒有「現在」「Now」標題、沒有 `data-card=`、沒有 `class="red"` 紅色計數、沒有「正在跑」「需要注意」卡片標題 | 自動 |
| TC-003 | 作法 2；test_v02 | 功能 | Ann 只有 ann-running 與 ann-done（沒有 failed／lost） | `GET /` | 中欄 `<h1>` 是 `ann-running`（最新的那筆） | 自動 |
| TC-004 | 作法 1（lost 也算） | 功能 | Ann 只有 ann-running、ann-done、ann-lost、ann-cancelled | `GET /` | 中欄 `<h1>` 是 `ann-lost`（最新的 failed／lost；不是較新的 ann-running） | 自動 |
| TC-005 | 裁決 6 | 功能 | Ann 有兩筆 failed，`started_at` 完全相同 | `GET /` | 選中的是 `list_runs` 順序（`started_at DESC, rowid DESC`）的第一筆，也就是後寫入的那筆 | 自動 |
| TC-006 | 作法 3；test_v03 | 功能 | Ann 沒有任何 run | `GET /` | 回 200；中欄有一行「還沒有分析」；沒有 run 的 `<h1>` 名稱 | 自動 |
| TC-007 | 作法 3；test_v03 | 功能 | 同 TC-006 | 看中欄 | 中欄內有文字為「＋ 新分析」的連結，`href` 指向 `/launch` | 自動 |
| TC-008 | 作法「沒有 `?run=` 時」的反面 | 功能 | 標準種子 | `GET /?run=<ann-done 的 id>` | 中欄 `<h1>` 是 `ann-done`（明確指定的優先於預設選擇）；網址不被改寫 | 自動 |
| TC-009 | 限制「每人只看自己的」；test_v13 | 例外 | 標準種子（Bob 的 failed 比 Ann 全部都新） | Ann `GET /` | 預設選中的仍是 ann-failed-resume；整頁任何位置都沒有 `bob-failed` 的名稱 | 自動 |
| TC-010 | test_v13 | 例外 | Ann 沒有 run，Bob 有一筆 failed | Ann `GET /` | 是空狀態（「還沒有分析」），不會選中 Bob 的 run | 自動 |
| TC-011 | test_v13 | 例外 | 標準種子 | Ann `GET /?run=<bob-failed 的 id>` | 回 404 的「找不到這個 run」頁；頁面不重複該 id、不含 `bob-failed` 名稱 | 自動 |
| TC-012 | 維護者原話 6（DESIGN 原話 1）「進來之後馬上可以看到各個run的狀態與進度」 | 功能 | 標準種子 | Ann 登入後只做一次 `GET /`，不點任何東西 | 左欄一次列出 Ann 的全部 6 筆，每筆都有狀態字；ann-running 那筆的第 2 行顯示進度「2 / 5」 | 自動 |

## User Story 2 — 狀態只有三種（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 作法「三種狀態」；維護者原話 1「狀態只要running, failed, successed就好」；test_v04 | 功能 | 標準種子 | 看 `GET /` 與 `GET /?run=<id>` 的左欄列與中欄標題徽章 | running 顯示「▶ 執行中」；succeeded 顯示「✓ 完成」（不是「成功」）；failed 顯示「✗ 失敗」 | 自動 |
| TC-014 | 作法「三種狀態」；DESIGN「A lost run is Failed… a cancelled run is Failed」；test_v04 | 功能 | 標準種子 | 看 ann-lost 與 ann-cancelled 的左欄列與標題徽章 | 兩者都顯示「✗ 失敗」，與 failed 完全同一組符號與文字 | 自動 |
| TC-015 | 專長守則「符號＋文字＋顏色」；作法「lost 的 CSS 狀態類用 failed 的」 | 功能 | 標準種子 | 看每種狀態那一列的 HTML | 每列同時含符號（▶／✓／✗）、狀態文字、狀態 class；lost 那列的 class 是 `state-failed`，沒有 `state-lost` | 自動 |
| TC-016 | 作法「頁面上任何地方不再出現…」；裁決 4；test_v04 | 功能 | 標準種子 | 看 `/` 與 `/?run=` 頁的左欄列、標題徽章，以及 lost 那筆 `?tab=info` 的「狀態」列 | 這些位置都沒有「失聯」「暫停」「Lost」「Paused」「⏸」 | 自動 |
| TC-017 | 限制「`?lang=en` 每個字都有英文」；test_v14 | 功能 | 標準種子 | `GET /?lang=en` 與各 run 頁 | 狀態字是 Running／Succeeded／Failed；lost 與 cancelled 也是 Failed | 自動 |
| TC-018 | 維護者原話 1「failed下面再去分原因」 | 功能 | ann-failed-resume、ann-lost、ann-cancelled 各開一次 | 看各頁標題徽章與右欄 | 三頁徽章都是「✗ 失敗」；原因（步驟／原因欄）只出現在右欄的欄位裡，不改變狀態字 | 自動 |
| TC-019 | 裁決 4「`chip_*` 不動」 | 不在範圍 | 標準種子 | `GET /launch?from=<ann-done 的 id>&lang=en` | /launch 頁的方塊字仍是 `Done`（沒被改成 Succeeded） | 自動 |

## User Story 3 — 左欄：依專案分組的清單（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法「左欄」；test_v05 | 功能 | 標準種子 | 看左欄 | 組名（`h3`）依序是 `nf-core/ampliseq`、`nf-core/rnaseq`、`未分專案`（組內最新 run 新到舊） | 自動 |
| TC-021 | 作法「放最後一組」 | 功能 | 標準種子再加一筆無專案的 succeeded，比 Ann 其他 run 都新 | 看左欄 | `未分專案` 仍是最後一組 | 自動 |
| TC-022 | 作法「組內 run 新到舊」 | 功能 | 標準種子 | 看各組內順序 | ampliseq 組：ann-running 在 ann-done 之前；rnaseq 組：ann-failed-resume 在 ann-failed-relaunch 之前；未分專案組：ann-lost 在 ann-cancelled 之前 | 自動 |
| TC-023 | 作法「組的順序＝組內最新 run 的 started_at」 | 功能 | 把 rnaseq 組的 run 改成都比 ampliseq 組新 | 看左欄 | `nf-core/rnaseq` 排在 `nf-core/ampliseq` 之前（依時間，不是依字母） | 自動 |
| TC-024 | 作法「每列是一個連到 `?run=<id>` 的連結，兩行」 | 功能 | 標準種子 | 看每一列 | 每列是 `<a>`，`href` 含 `?run=<該 run 的 id>`；第 1 行是名稱＋狀態（符號＋文字），第 2 行是「階段 · 細節」 | 自動 |
| TC-025 | 作法第 2 行 running；test_v05 | 功能 | 標準種子 | 看 ann-running 第 2 行 | 「執行 · 2 / 5」 | 自動 |
| TC-026 | 作法第 2 行 failed | 功能 | 標準種子 | 看 ann-failed-resume 第 2 行 | 「執行 · NFCORE_AMPLISEQ:DADA2_DENOISING」 | 自動 |
| TC-027 | 作法第 2 行 failed、沒有 failed task | 功能 | 加一筆 failed 且沒有任何失敗任務紀錄 | 看它的第 2 行 | 「執行 · —」 | 自動 |
| TC-028 | 作法第 2 行 cancelled；test_v05 | 功能 | 標準種子 | 看 ann-cancelled 第 2 行 | 「執行 · 已取消」 | 自動 |
| TC-029 | 作法第 2 行 unknown（lost）；test_v05 | 功能 | 標準種子 | 看 ann-lost 第 2 行 | 「執行 · 站台沒有回應」 | 自動 |
| TC-030 | 作法第 2 行 succeeded；test_v05 | 功能 | 標準種子 | 看 ann-done 第 2 行 | 「結果」 | 自動 |
| TC-031 | 作法「選中的那列加 `here`」 | 功能 | 標準種子 | `GET /?run=<ann-done 的 id>` 與 `GET /` | 前者只有 ann-done 那列帶 `here`；後者只有 ann-failed-resume 那列帶 `here`；任何時候恰一列 | 自動 |
| TC-032 | 作法「最上方『＋ 新分析』連 `/launch`」；「拿掉『現在』與紅色數字」 | 功能 | 標準種子 | 看左欄最上方 | 有「＋ 新分析」連到 `/launch`；左欄沒有「現在」、沒有紅色數字、沒有舊的「啟動分析」導覽字 | 自動 |
| TC-033 | 作法「設定、登出、灰字項目保留」 | 功能 | 標準種子 | 看左欄下方 | 有「設定」連到 `/settings`；有「登出」表單；灰字項目後面仍接「之後開放」 | 自動 |
| TC-034 | 作法「總數仍受 `LIST_CAP`」 | 功能 | Ann 有 `LIST_CAP + 5` 筆 run | `GET /` | 左欄只列 `LIST_CAP` 筆，並顯示「還有 5 筆」 | 自動 |
| TC-035 | 限制「左欄只用 caller 自己的 run」；test_v13 | 例外 | 標準種子 | Ann `GET /` | 左欄沒有 Bob 的 run，列數＝6 | 自動 |
| TC-036 | 限制「`?lang=en`」；test_v05／test_v14 | 功能 | 標準種子 | `GET /?lang=en` | 無專案組名是 `No project`；第 2 行的已取消、站台沒有回應、結果都是英文（Cancelled、Site not responding、Results）；整頁沒有中文字元 | 自動 |
| TC-037 | 作法「欄位不存在或為 NULL → `None`」 | 例外 | 一個沒有 `project_name` 欄的舊索引，內有 run | `GET /` | 頁面正常（不是 500）；該 run 歸在「未分專案」 | 自動 |
| TC-038 | 作法「`status._view` 加 `project`」；test_v16 | 功能 | 標準種子 | 呼叫 `actions.list_runs` 與 `actions.get_run` | 每一筆都有 `project` 鍵；ampliseq 的 run 是 `"nf-core/ampliseq"`；無專案的是 `None` | 自動 |

## User Story 4 — 中欄：切換、五階段條、不放通知（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 維護者原話 4「為甚麼沒看到…launch, run, result等左右視窗？」；作法「五階段條…照舊」 | 功能 | 標準種子 | `GET /?run=<ann-running 的 id>` | 頁面依序有 `data-pane` 為 left、middle、right 三欄；中欄階段條依序是 送出、執行中、結果、下游、完成 | 自動 |
| TC-040 | 作法「標題列不變」 | 功能 | 標準種子 | 看中欄標題列 | 有 run 名稱 `<h1>` 與狀態徽章（符號＋文字） | 自動 |
| TC-041 | 作法「`主視窗` 是目前頁」；test_v12 | 功能 | 標準種子 | 看中欄切換 | 「主視窗」帶 `aria-current="page"` | 自動 |
| TC-042 | 作法「`終端機` 是灰字不是連結，後面接 `之後開放`」；test_v12 | 功能 | 標準種子 | 看中欄切換 | 「終端機」不在任何 `<a>` 內，後面接「之後開放」 | 自動 |
| TC-043 | 作法「拿掉中欄的通知卡」；test_v11 | 功能 | 標準種子 | `GET /?run=<ann-failed-resume 的 id>` | 中欄（`data-pane="middle"`）內沒有 `class="notice` | 自動 |
| TC-044 | 作法「通知只在右欄」；test_v11 | 功能 | 標準種子 | 開 ann-lost 頁與 ann-running 頁 | 中欄同樣沒有 `class="notice`，也沒有「這個分析的通知」標題 | 自動 |
| TC-045 | 作法「摘要卡、分頁、上一步／下一步照舊」 | 功能 | 標準種子 | 開 ann-failed-resume 的執行階段頁 | 仍有 4 張摘要卡、5 個分頁（任務／日誌／執行資訊／設定檔／指標）、上一階段／下一階段連結 | 自動 |
| TC-046 | 作法「續跑／重跑／取消 按鈕留在標題列」 | 功能 | 標準種子 | 開 ann-failed-resume 的執行階段頁 | 標題列有 resume、relaunch、cancel 三個表單，按鈕文字只用固定動詞（續跑／重跑／取消） | 自動 |
| TC-047 | 維護者原話 3「下載、看結果甚麼的點進去看就好了」 | 功能 | 標準種子 | 在左欄點 ann-done | 中欄階段條目前階段是「結果」（`data-current="results"`） | 自動 |
| TC-048 | 維護者原話 3「處置那邊很奇怪，不需要」；DESIGN「There is no 處置 column anywhere」 | 功能 | 標準種子 | 看 `/`、失敗 run 頁、running run 頁 | 整頁都沒有「處置」二字 | 自動 |
| TC-049 | 限制「`?lang=en`」；test_v14 | 功能 | 標準種子 | `GET /?run=<ann-failed-resume 的 id>&lang=en` | 中欄切換是英文，「終端機」對應字後接 `Coming later`；整頁沒有中文字元 | 自動 |

## User Story 5 — 右欄：這個分析的對話與 Seqera 式失敗通知（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 作法「右欄」標頭 | 功能 | 標準種子 | 開 ann-failed-resume 與 ann-running | 右欄標頭有小字「這個分析的對話」＋選中 run 的名稱 | 自動 |
| TC-051 | 裁決 3；test_v06 | 功能 | 標準種子 | `GET /?run=<ann-running 的 id>` | 右欄只有標頭、名稱與「目前沒有待處理的事」；沒有 `<article`、沒有表單 | 自動 |
| TC-052 | 作法「其他 run 的任何資訊都不出現在右欄」；test_v06 | 功能 | 標準種子 | 開 ann-running，再開 ann-failed-resume | 兩次右欄內都不出現其他任何 run 的名稱 | 自動 |
| TC-053 | 作法「不再有全部分析的分組、計數」 | 功能 | 標準種子 | 看右欄 | 沒有「全部分析」、沒有 `data-stage=` 分組、沒有 ▶／!／✓ 計數列 | 自動 |
| TC-054 | 作法「恰一張失敗通知」；test_v07 | 功能 | 標準種子 | 開 ann-failed-resume | 右欄恰一個 `<article>`（一張通知） | 自動 |
| TC-055 | 裁決 2；test_v07 | 功能 | 標準種子 | 開 ann-failed-resume，再開 ann-lost（各看 zh 與 en） | 級別列是 `<span class="level state-failed"><span class="sq"></span> 待處理</span>`（en 為 `Pending`）；lost 也用 `state-failed`；整頁沒有「需要你處理」「Action needed」 | 自動 |
| TC-056 | 作法「`<dl>` 順序固定」；test_v07 | 功能 | 標準種子 | 開 ann-failed-resume | 通知內 `<dt>` 依序恰為 步驟、原因、之後 | 自動 |
| TC-057 | 作法「步驟包在 `<code>`」；test_v07 | 功能 | 標準種子 | 開 ann-failed-resume | 步驟欄是 `<code>NFCORE_AMPLISEQ:DADA2_DENOISING</code>` | 自動 |
| TC-058 | 作法「沒有就 `—`」 | 功能 | 一筆 failed 且沒有失敗任務紀錄 | 開它 | 步驟欄是 `—` | 自動 |
| TC-059 | 作法「原因＝failure_reason 最後 3 個非空行」；test_v07 | 功能 | failure_reason 共 5 個非空行，且中間或結尾夾空白行 | 開 ann-failed-resume | 原因欄恰是最後 3 個非空行（依序），前 2 行與空白行不出現 | 自動 |
| TC-060 | 作法「每行截 `REASON_CAP` 字」 | 功能 | failure_reason 最後一行超過 100 字 | 開它 | 該行顯示前 80 個字，第 81 個字起不出現 | 自動 |
| TC-061 | 作法「沒有 failure_reason：cancelled →已取消」；test_v10 | 功能 | 標準種子 | 開 ann-cancelled | 原因欄是「已取消」（en：Cancelled） | 自動 |
| TC-062 | 作法「unknown →站台沒有回應」；test_v10 | 功能 | 標準種子 | 開 ann-lost | 原因欄是「站台沒有回應」（en：Site not responding） | 自動 |
| TC-063 | 作法「其他 → failed_tasks[0].error_message 第一行」 | 功能 | 一筆 failed 沒有 failure_reason，失敗任務的 error_message 有兩行 | 開它 | 原因欄只有 error_message 的第一行 | 自動 |
| TC-064 | 作法「或 `—`」 | 功能 | 一筆 failed 沒有 failure_reason、也沒有失敗任務 | 開它 | 原因欄是 `—` | 自動 |
| TC-065 | 作法「之後＝actions[0] 的動詞加（確認頁）」；test_v07 | 功能 | 標準種子 | 開 ann-failed-resume | 之後欄是「續跑（確認頁）」 | 自動 |
| TC-066 | 同上 | 功能 | 標準種子 | 開 ann-failed-relaunch | 之後欄是「重跑（確認頁）」 | 自動 |
| TC-067 | 作法「failed 用 `ended_at`，台北時間」 | 功能 | ann-failed-resume 的 ended_at 已知 | 開它 | 級別列右邊的時間含該 ended_at 換成台北時間的 `HH:MM` | 自動 |
| TC-068 | 作法「lost 用 `last_message_at`」 | 功能 | ann-lost 的 last_message_at 已知 | 開它 | 級別列右邊的時間含該 last_message_at 換成台北時間的 `HH:MM` | 自動 |
| TC-069 | 作法「恰一顆按鈕…`Acts.form`」；test_v08 | 功能 | 標準種子 | 開 ann-failed-resume | 右欄恰一個表單，按鈕「續跑」，form action 是 `/act/resume` | 自動 |
| TC-070 | 同上；test_v08 | 功能 | 標準種子 | 開 ann-failed-relaunch | 右欄恰一個表單，按鈕「重跑」，form action 是 `/act/relaunch` | 自動 |
| TC-071 | 作法「→ 確認頁」；test_v08 | 功能 | 標準種子 | 按右欄那顆按鈕送出表單 | 回 303，導向 `/c/<id>`；尚未建立任何 job | 自動 |
| TC-072 | 維護者原話 2「你給使用者的按鈕都是"用24G續跑"，哪有一個固定的按鈕會這樣寫？」；test_v09 | 功能 | 標準種子（ann-failed-resume 的原因含「24 GB」） | 看右欄與標題列所有按鈕 | 按鈕文字全屬 {續跑, 重跑, 取消, 登出}（en 對應），不含數字、GB、檔名 | 自動 |
| TC-073 | 作法「數字、檔名、記憶體量不出現在…級別列」 | 功能 | 標準種子 | 看 ann-failed-resume 的級別列 | 級別列文字只有「待處理」（en：Pending），沒有數字或檔名；時間在右邊另一格 | 自動 |
| TC-074 | 維護者原話 7（DESIGN 原話 7）「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」 | 功能 | 標準種子 | 看 ann-failed-resume 與 ann-lost 的通知 | 通知內容只有級別列、三個固定欄位、一顆按鈕；沒有「問題」「可選動作」「Options」欄，也沒有「三次心跳沒有回應」之類的句子 | 自動 |
| TC-075 | 維護者原話 5「改成 跟Seqera platform一樣的模式，不要自己定義」；作法「網頁不自己分類原因」 | 功能 | 兩筆 failed，failure_reason 各是不同的唯一字串 | 各開一次 | 原因欄的文字完全來自該筆的 failure_reason（最後 3 個非空行），不含任何網頁自己加的分類詞；步驟欄只來自 failed_tasks[0].name | 自動 |
| TC-076 | 作法「最下方一行灰字 `問這個分析 之後開放`」 | 功能 | 標準種子 | 看右欄最下方 | 最後一行是灰字「問這個分析 之後開放」（en：Ask about this analysis — coming later），不是連結 | 自動 |
| TC-077 | 計畫「不做」：對話輸入框與 AI 回覆 | 不在範圍 | 標準種子 | 看右欄 | 沒有 `<textarea>`、沒有文字輸入框、沒有「傳送」按鈕 | 自動 |
| TC-078 | 限制「`?lang=en`」；test_v07／v14 | 功能 | 標準種子 | `GET /?run=<ann-failed-resume 的 id>&lang=en` | 右欄標頭 `This analysis`；欄位 `Step`／`Reason`／`Next`；之後欄 `Resume (confirmation page)`；沒有中文字元 | 自動 |
| TC-079 | 限制「`?lang=en`」；test_v08 | 功能 | 標準種子 | 開 ann-failed-resume 與 ann-failed-relaunch（`lang=en`） | 按鈕分別是 `Resume`、`Re-run`；form 帶 `lang=en` | 自動 |
| TC-080 | 作法「沒有選中 run 時只放標頭小字＋`—`」 | 功能 | Ann 沒有任何 run | `GET /` | 右欄有標頭小字與 `—`；沒有按鈕、沒有任何 run 名稱 | 自動 |

## User Story 6 — 不能放掉的限制（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-081 | 限制「零 JavaScript」；test_v15 | 功能 | 標準種子 | 取 `/`、失敗 run 頁、空狀態頁 | 都沒有 `<script` | 自動 |
| TC-082 | 限制「無 `style=`」；test_v15 | 功能 | 同上 | 同上 | 都沒有 `style=` | 自動 |
| TC-083 | 限制「單一樣式表（CSP 雜湊）」；test_v15 | 功能 | 同上 | 同上 | 恰一個 `<style>`、沒有 `<link rel=stylesheet>`；回應標頭 CSP 內的 sha256 與該 `<style>` 內容的雜湊相符 | 自動 |
| TC-084 | 限制「15 秒 refresh」；test_v15 | 功能 | 同上 | 同上 | 都有 `<meta http-equiv="refresh" content="15">` | 自動 |
| TC-085 | 專長守則「不載外部資源」 | 功能 | 同上 | 同上 | 頁面沒有指向 `http://`／`https://` 的 `src`、CSS 載入或外部字型 | 自動 |
| TC-086 | 限制「`?lang=en` 每個字都有英文」；test_v14 | 功能 | 標準種子 | `GET /?lang=en` 與每個 run 的 `?run=…&lang=en` | 整頁沒有任何中日韓字元（含全形「＋」；run 名稱與 Nextflow 原文是資料，種子用英文） | 自動 |
| TC-087 | 專長守則「手機寬度可用」 | 功能 | 失敗 run 頁、執行中 run 頁 | 在 390 px 寬看（developer-agent 截圖） | 不橫向捲動、順序為中欄→右欄→左欄、按鈕夠大 | 手動：PR 截圖 |
| TC-088 | 計畫「完成標準」截圖 | 功能 | 同上 | 1440／390 px × zh／en 四種組合各拍失敗 run 頁與執行中 run 頁 | 共 8 張截圖附在 PR | 手動：PR 截圖 |
| TC-089 | 專長守則「鍵盤焦點外框可見」 | 功能 | 標準種子 | 檢查樣式表 | 連結與按鈕的 `:focus-visible` 外框規則仍在 | 自動 |

## 不在範圍與邊界

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-090 | 計畫「不做」：終端機 | 不在範圍 | 標準種子 | `GET /terminal`；看中欄 | 回 404；頁面沒有 iframe、ttyd，終端機只是灰字 | 自動 |
| TC-091 | 計畫「不做」：自動處理通知與下游通知 | 不在範圍 | 標準種子 | 看所有 run 頁的右欄 | 沒有「已自動處理」「已完成」級別列、沒有「診斷／依據／結果」「項目／檔案／下一步」欄、沒有「打包」按鈕 | 自動 |
| TC-092 | 計畫「不做」：新視覺、改 token；維護者原話「以後再改美觀」 | 不在範圍 | 本任務的 diff | 看樣式表的變更 | 沒有新增顏色、字型、字級、間距、圓角的新值；只沿用既有 class 與 token | 手動：閱卷者 `git diff` |
| TC-093 | 計畫「不准改」清單 | 不在範圍 | 本任務的 diff | `git diff` 這幾個檔 | `test_confirm_page.py`、`test_web_confirm_plain.py`、`test_web_parity.py`、`test_web_login.py`、`test_web_chrome_origin.py` 一字未改 | 手動：閱卷者 `git diff` |
| TC-094 | 計畫「不做」：不動 `failures.py`、`actions/__init__.py`、`/act/*`、確認頁、登入 | 不在範圍 | 本任務的 diff | `git diff` | 這些檔案與函式沒有變更；`web.py` 只動 `board`／`board_page`／`read_details` 與首頁選擇 | 手動：閱卷者 `git diff` |
| TC-095 | 裁決 8 | 不在範圍 | 本任務的 diff | `git diff` | `docs/TESTING.md` 未被修改 | 手動：閱卷者 `git diff` |
| TC-096 | 計畫「允許更新的既有斷言」 | 不在範圍 | 本任務的 diff | 逐一看被改動的既有斷言 | 只限 test_web_board.py（Now 頁、attention／running 卡、左欄「現在」與紅數字、右欄分組與計數、⏸／失聯、中欄通知卡）與 test_web_running.py（中欄通知卡欄位、`_notice`）；每條在 PR 說明有「舊斷言 → 新斷言」；沒有被刪掉、放寬或跳過的斷言 | 手動：閱卷者 `git diff` |
| TC-097 | 裁決 5「唯一一條」 | 不在範圍 | 本任務的 diff | `git diff platform/tests/test_web_actions.py` | 只有 `test_tc004_notices_carry_real_forms` 被改，其他測試不變 | 手動：閱卷者 `git diff` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-098 | 不變式 2（不留第二份 run 狀態）；裁決 9 | 功能 | 本任務完成後 | 跑 `tests/no_second_run_state_test.sh` 與 `test_web_parity.py` | 都綠；網頁仍只呼叫 `list_runs`／`get_run` 與既有 request_*，沒有新增呼叫 | 自動 |
| TC-099 | 不變式 2（送出前要使用者確認） | 例外 | 標準種子 | 按右欄「續跑」或「重跑」；再跑 `test_confirm_page.py` 的 TC-H09 | 只到確認頁 `/c/<id>`，未確認不建立 job；既有「未確認的送出被拒」測試仍綠 | 自動 |
| TC-100 | 裁決 9（`test_resume_scope.py`） | 功能 | 本任務完成後 | 跑 `test_resume_scope.py` | 綠；`web.py` 沒有新增名字含 resume／relaunch 的識別字 | 自動 |
| TC-101 | 不變式 7（每一步先說明會做什麼） | 功能 | 標準種子 | 看 ann-failed-resume 通知的「之後」欄 | 欄位在按鈕之前就寫明按下後的動作與「（確認頁）」 | 自動 |
| TC-102 | 裁決 5 | 功能 | 標準種子 | 跑改寫後的 `test_tc004_notices_carry_real_forms` | 右欄（`data-pane="right"`）的 `<article>` 內恰一個表單，verb＝`failure.actions[0]`，POST 後得到確認頁 id；中欄不再有通知表單 | 自動 |

<!--
IDs are never renumbered after approval.
-->
