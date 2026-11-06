---
id: web-bugs-a
title: 網頁畫面五個缺陷（#335 確認頁英文版、#336 失敗計數與任務分頁矛盾、#337 已完成分析的「更多」選單、#339 內部編號、#340 專案群組標題 main.nf）
tier: C
kinds: ui
risk: M
lane: L6-web
branch: fix/web-bugs-a
base: v3
review: maintainer
source: GitHub zhshie/agentic-bioflow_v2 #335 #336 #337 #339 #340；DESIGN.md Skeleton／Formal notices／Running stage／Constraints
---

# web-bugs-a

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/web-bugs-a/plan.md`。
> **2026-11-05 查 origin/v3（b00263c6）：五個 issue 都還是 OPEN，程式碼裡的成因都還在，沒有一個已被修掉、沒有一個被丟掉。** #361（012b-2 預覽）、#334（結果摘要卡）與本任務無關；#363（拒絕可見性）尚未合併，不碰。
> 以下行號取自 b00263c6，executor 動手前先對 origin/v3 目前版本再看一次（**行號未逐條重驗者，請 executor 先確認仍可重現再改**）。

## 目標
五個畫面缺陷一次修掉，頁面其餘部分、CSS、CSP 不變：(1) 確認頁 `/c/<token>` 與其 404 在 `?lang=en` 下全英文；(2) 失敗計數大於 0 時，「任務」分頁不再寫「無失敗任務」；(3) 已完成（succeeded）的分析，「更多」選單不再給續跑／重跑／取消；(4) 送出／下游階段改顯示灰字「之後開放」（Coming later），不再顯示內部編號 `012b`／`016`；(5) 左欄不再以腳本檔名 `main.nf` 當專案群組標題。使用者看到的每個畫面前後一致、英文版不含中文。

## 維護者原話（verifier 出題用）
以下為 issue 原文（逐字），每句對應至少一條測試（TC 以「失敗先行測試」名稱為準）。

**#335**（對應 `test_confirm_en_*`、`test_confirm_404_en`）：
> 英文版（`?lang=en`）的確認頁 `/c/<token>`（清理中間檔）標題與說明句仍是中文，與英文欄位混在同一頁：標題：「清理確認」；說明句：「以下為將被刪除的全部內容。確認無誤後，請按「確認刪除」；按下後才會排入佇列。」
> 另外，不存在的確認頁網址 `/c/doesnotexist?lang=en` 回 404，頁面內容「找不到 (not found)／無此網址。」在英文版同樣是中文。
> 英文版不得出現中文（run 名稱除外）。出處：DESIGN.md「Constraints」："Language by `?lang=en` server-side; every screen exists in English."；R05「做成產品英文版面是必須的」。
> DESIGN.md「Open」只列出登入、/welcome、同意頁仍中英並列；確認頁與 `/c/*` 404 不在該清單內。
> 實際：頁面上沒有語言切換連結，使用者無法自行改回。

**#336**（對應 `test_tasks_tab_*`）：
> 已完成（狀態「完成」）的分析，run 頁「執行中」階段同時顯示互相矛盾的數字：web-test-2：`71 / 75`，計數卡「失敗 4」，但分頁「任務」內容為「無失敗任務」。
> 英文版 `&lang=en` 相同：`Failed 4`＋`No failed tasks`。
> 同一頁的數字須互相一致：失敗計數大於 0 時，「任務」分頁要列出對應任務（或明確標示這些失敗已被忽略／已重試成功）。
> 預期行為的細部（忽略、重試如何計數）規格未寫，不確定；但「失敗 4」與「無失敗任務」並列必有一者顯示錯誤，或缺少說明。

**#337**（對應 `test_menu_*`）：
> 已完成（「完成」）的分析，run 頁（執行中階段）標題列的「更多」選單仍提供可按的「續跑」「重跑」「取消」三個按鈕與「沿用設定重新分析」連結。「取消」對一個已結束的分析沒有意義。
> 取消只應出現在執行中的分析；已完成的分析不提供取消。
> 規格未明寫「取消僅限執行中」，此為由上述狀態模型推得的預期，不確定；至少「對已完成分析按取消」不應是可點的選項。
> DESIGN.md「Formal notices」："one button = `failure.actions[0]` … The other action stays in the run's menu."，即選單內的動作應依 run 的 `failure.actions` 決定，而不是一律列出。

**#339**（對應 `test_stage_placeholder_*`）：
> run 頁的「送出」階段與「下游」階段，內容區只顯示標題加一行「— 012b」／「— 016」。這兩個是內部計畫（ticket）編號，使用者看不懂，也沒有標示「之後開放」。
> 規格寫了、但尚未實作的畫面須灰掉並標「之後開放」（Coming later），不得顯示內部編號。
> 同一分析的「完成」階段則正確使用灰字「之後開放」標示未實作項目，兩者不一致。

**#340**（對應 `test_left_group_*`）：
> 左欄分析清單的專案群組小標題顯示為「main.nf」（Nextflow 的腳本檔名），而不是專案名稱。web-test-1、web-test-2 都跑 `nf-core/ampliseq 2.18.0`，卻歸在「main.nf」之下。所有 nf-core 管線的腳本檔名都叫 `main.nf`，依此分組沒有區分作用。
> 左欄依專案分組，專案名稱作為小標題。出處：DESIGN.md「Skeleton／Left column」："analyses grouped by project (project name as a small heading)"。
> 目前「＋ 新專案」標為「之後開放」，若尚無專案概念，不確定正確的顯示（可能不顯示標題或顯示預設專案名），但不應顯示腳本檔名。

## 範圍：檔案
- `platform/abf_platform/web.py`：**只動** `_page`（加選用參數 `lang="zh"`，原樣傳給 `web_board.document`）、`view_of`（加 `lang`，404 用英文頁）、`state_page` 內的標題／說明句／逾時／作廢／已送出字串（依 `lang` 選）、`confirm_get`／`confirm_post` 開頭的 404、act 路由的 404（:644 一帶）。不動 /settings、/launch、其他路由、`_HEADERS`／CSP。
- `platform/abf_platform/web_board.py`：`STRINGS` zh／en 兩邊各加新鍵；`PLACEHOLDER` 與 `_stage_card`（#339）；`_projects`（#340）；`tab_body` 的 tasks 分支（#336）；`_run_page` 的選單組裝（#337）。不動 `_report_cell`、`SETTINGS`、`_frame`、CSS。
- 新測試：`platform/tests/test_web_bugs_a.py`。
- 因預期改變而要改的既有測試（只改預期，ledger 逐條列舊→新與理由）：見下表。
- **不碰**：`web_launch.py`、`web_settings.py`、`status.py`、`receiver.py`、`store.py`、`mcp_server.py`、`static/*`、`DESIGN.md`、`memory/dev-queue.json`。

### 允許改動的既有斷言（其餘既有斷言一字不改）
| 檔案:行（b00263c6） | 現在釘的東西 | 怎麼改 |
|---|---|---|
| `test_clean_page.py:119,125`（`test_the_expired_and_void_…`） | 迴圈 `zh`／`en` 兩種語言都斷言 `清理確認`、`該申請已逾時（7 天），不會自動重新提出。` | zh 照舊；en 改斷言英文標題與英文逾時句，並斷言 en 頁無中文 |
| `test_clean_page.py:158`（`BASE_CONFIRM`）、`:159`（`BASE_EXPIRED`） | zh／en 確認頁逐位元組雜湊 | **只重釘 `-en` 鍵**；`-zh` 鍵必須原值（證明中文頁沒變）。ledger 貼新舊雜湊 |
| `test_clean_page.py:94` | en 頁含 `Confirm delete` 按鈕、無 `取消確認` | 保持；可加斷言 en 頁無中文標題 |
| `test_web_board.py:547`（`test_tch21_stage_bodies` 一帶） | launch／downstream 階段含 `012b`／`016` | 改為含 `之後開放`、不含 `012b`／`016`；finished 那條不動 |
| `test_web_board.py:383` | 單一群組標題 `["未分專案"]` | 預期不變（必須仍綠） |
| `test_web_running.py:217` | 失敗 run 的選單含 續跑／重跑／取消 三個 form | 不變（failed 不動，必須仍綠） |
| `test_web_running.py:308–309`、`test_web_results_outputs.py:108` | 失敗數為 0 時 `無失敗任務`／`No failed tasks` | 不變（failed=0 時文字不變，必須仍綠）；若 results_outputs 的 world 另有 failed>0，改成斷言新的說明句 |
| `test_web_wording_sweep.py:250` | `STRINGS["zh"]["no_failed_tasks"] == "無失敗任務"` | 不變；新字串全過其禁字表（`BANNED`：這個、一下、還沒有、這份、弄、搞、東西……；單獨的拉丁字 `run` 也算） |
| `test_web_wording_sweep.py` 的 `bad_page`／`test_english_pages_have_no_cjk_everywhere`（:296–308、:570–580） | 各階段頁無禁字；en 頁無 CJK | 不改、必須綠（#339／#336 新字串要過） |
| `test_web_finished.py:287` | `"finished" not in web_board.PLACEHOLDER` | 不變（PLACEHOLDER 改成 tuple `("launch","downstream")` 仍成立） |
| `test_web_v2_skeleton.py:193,204,211` | 群組 `nf-core/ampliseq`、`nf-core/rnaseq`、`未分專案`／`No project` | 不變、必須綠 |
| 其他同類釘死 `/c/` 中文：`test_confirm_page.py:87`、`test_web_confirm_plain.py:143`、`test_pending_confirm_restart.py:211`（404 `無此申請`）、`test_launch_profiles.py:708`、`test_oauth_mcp.py:290` | zh（預設）頁 | 全部不變；zh 預設頁位元組不得變 |

## 作法
**#335 確認頁英文版**
1. `_page(title, body, status=200, form_action=None, lang="zh")`：只多傳 `lang=lang` 給 `web_board.document`；不給 lang 的既有呼叫位元組不變。
2. `state_page` 內所有中文字串用 `lang` 選一組（建議區域 dict `_CONFIRM = {"zh": {...}, "en": {...}}`，zh 值逐字等於現行字串）。英文：標題 `Confirm clean-up`／`Confirm launch`／`Confirm cancel`（clean／launch／其他）；說明句 `Everything that will be deleted is shown below. If it is correct, press "Confirm delete"; nothing is queued until you press it.`（非 clean：`Everything that will be sent is shown below. If it is correct, press "Send"; …`，按鈕 `Send`）；已送出 `Sent. Job number %s.`；逾時 `This request has expired (7 days) and will not be raised again.`／`This request has expired (10 minutes). Please send it again.`；作廢 `This request was voided: %s.`（非 clean 加 ` Please send it again.`）。zh 值一字不改（`-zh` 雜湊證明）。
3. 404：`/c/doesnotexist?lang=en` 英文標題 `Not found`、內文 `No such address.`；`view_of` 的 404 `Not found`／`No such request.`；403 `Not yours`／`That request was not sent by you, so it cannot be viewed or acted on here.`。`confirm_get`／`confirm_post`／act 路由在讀 lang 後再組 404（RID 不合時也要讀 `request.query_params["lang"]`）。zh 404 維持 `找不到 (not found)`／`無此網址。`／`無此申請。`。
4. `<pre>` 內的技術摘要與資料值（run 名稱、路徑）不翻（裁決 R7）。POST 結果頁維持中文（裁決 R2，列後續）。

**#336 任務分頁**
5. `tab_body` tasks 分支：`n = (run.get("tasks") or {}).get("failed", 0)`；`rows = run.get("failed_tasks") or []`。`rows` 為空且 `n > 0` → 不寫 `no_failed_tasks`，改寫新鍵 `failed_unlisted`（zh：`失敗計數 %d，但沒有可列出的失敗任務明細；這些失敗可能已被忽略或重試成功。`；en：`The failed count is %d, but no failed task has a recorded detail; these may have been ignored or retried successfully.`）。`rows` 非空但 `n > len(rows)` → 表格下加同一類說明句（`failed_partial`：列出 %d 個、計數 %d）。`n == 0` 且 `rows` 空 → 照舊 `無失敗任務`。說明句放 `<p class="muted">`，不新增 class、不用 `style=`。計數卡不動。

**#337 更多選單**
6. `_run_page`：`menu` 內的 `buttons` 改成依狀態：`status == "succeeded"` → 不給 resume／relaunch／cancel（`buttons = ""`）；`failed`／`lost` → 現狀（resume／relaunch／cancel 三個，維持 `test_web_running.py:217`）；`running` → 現狀。「沿用設定重新分析」連結（`quick`）**保留**（它是 `/launch?from=` 的新分析，對已完成的分析有意義）。succeeded 時選單只剩 quick 連結（仍是 `<details class="menu">`）。裁決 R4 說明預設與替代。

**#339 之後開放**
7. `PLACEHOLDER` 改為 `("launch", "downstream")`（不再帶內部編號）；`_stage_card` 該分支改為 `inner = '<p>— %s</p>' % _later(t)`，即灰字 `之後開放`／`Coming later`（用既有 `_later`，`<span class="later">`）。不新增 CSS 與字串（`later` 鍵已有 zh／en）。

**#340 專案群組**
8. `_projects`：先把 run 的 `project` 正規化——`None`、空字串、以及「看起來是腳本檔名」者（無 `/` 且結尾 `.nf`，如 `main.nf`）一律視為沒有專案（`None`），歸入既有「未分專案／No project」群組。`nf-core/ampliseq` 這類有 `/` 的名稱維持原狀。不改 `receiver.py`／`store.py`，不加資料來源（裁決 R6）。

**共通**：新字串兩邊同鍵；en 頁無 CJK（run 名稱除外）；全頁無 `<script`、無 `style=`、單一 `<style>`、CSP 標頭不變；狀態不只靠顏色。

## 六項必填檢核（ui 計畫固定段）
1. 確認頁規則：本片不改任何「寫入／花錢」動作的流程；`/c/*` 仍是唯一確認處；#337 只是**少給**按鈕，不新增任何會寫入的入口。
2. 失敗狀態：讀不到 `failed_tasks`、計數缺漏 → 視為 0／空，不丟 500；404／403 英文頁狀態碼不變。
3. 提示句位置：#336 說明句在「任務」分頁表格處（取代原「無失敗任務」位置），不新增 flash。
4. 要改的舊測試：見「範圍：檔案」的允許改動表。
5. 手機寬度：不新增版面元素（一行 muted 文字、一行灰字、少幾個按鈕）；`scripts/dev/ui_check.py` 在 origin/v3 **不存在**（只有 `check_chrome_login.py`、`check_settings_mobile.py`），不跑；PR 附 1440／390 × zh／en 截圖由 executor 用現有方式取得，取不到就在 ledger 註明（M 級網頁畫面另附截圖）。
6. 空狀態：failed=0 且無明細 =「無失敗任務」；無任何 run =「尚無分析紀錄。」（不動）；只有 `main.nf` 群組的 run = 只有「未分專案」一個群組。

## 失敗先行測試
新檔 `test_web_bugs_a.py`，沿用 `test_web_board.py` 的 `seed`／`pane`／`login` 輔助與 `test_clean_page.py` 的 `run_and_request`。先寫、在未修的 v3 上會紅：
- `test_confirm_en_title_intro_button`：`/c/<rid>?lang=en`（clean_work）→ 不含 `清理確認`、`以下為將被刪除`；含 `Confirm delete`；除 run 名稱與 `<pre>` 外無 CJK。
- `test_confirm_en_launch_and_cancel_pages`：launch／cancel 的 pending 頁 en → 英文標題、英文說明句、按鈕 `Send`，無 CJK。
- `test_confirm_en_confirmed_expired_void`：三種狀態 en → 英文句（`Sent. Job number`、`expired (7 days)`、`voided`）、無 CJK；zh 句不變。
- `test_confirm_zh_unchanged`：zh 頁仍含 `<h1>清理確認</h1>` 與原說明句（並由 `BASE_CONFIRM`／`BASE_EXPIRED` 的 `-zh` 鍵原值證明）。
- `test_confirm_404_en`：`/c/doesnotexist?lang=en` → 404、含 `Not found`、無 CJK；不帶 lang 仍是 `找不到 (not found)`＋`無此網址。`；他人的 rid + en → 403 英文；不存在的合法 rid + en → 404 英文。
- `test_tasks_tab_unlisted_failures_zh_en`：succeeded run、`failed=4`、無 `failed_tasks` → tasks 分頁含 `失敗計數 4`、**不含** `無失敗任務`；en 含 `failed count is 4`、不含 `No failed tasks`。
- `test_tasks_tab_partial_rows_note`：failed=4、`failed_tasks` 兩列 → 表格仍在，下方有說明句。
- `test_tasks_tab_zero_failed_unchanged`：failed=0 → `無失敗任務`／`No failed tasks`，與 v3 一致。
- `test_menu_succeeded_has_no_action_forms`：succeeded run `stage=running` → `<details class="menu">` 內無 `/act/` form，無 `續跑`／`重跑`／`取消`；有 `沿用設定重新分析` 連結；en 同理（`Resume`／`Re-run`／`Cancel` 不在）。
- `test_menu_failed_lost_running_unchanged`：failed／lost／running 的選單仍是三個 form（沿用 `test_web_running.py:217` 的斷言形狀）。
- `test_stage_placeholder_launch_downstream`：`stage=launch`、`stage=downstream` 的中間欄不含 `012b`、`016`；含 `之後開放`（en：`Coming later`），且在 `class="later"` 內。
- `test_left_group_script_name_is_no_project`：run 的 project 為 `main.nf` → 左欄 `<h3>` 沒有 `main.nf`，該 run 在「未分專案」（en：`No project`）下；`nf-core/ampliseq` 與 `nf-core/rnaseq` 仍各自成群、順序規則不變。
- `test_page_constraints_after_changes`：上列各頁無 `<script`、無 `style=`、單一 `<style>`、CSP 標頭同 v3；en 頁 `no_cjk`；`banned_in` 掃新字串為空。

## 完成標準（done when）
新測試全綠；允許改動表內的既有測試改預期後綠；整套 `tests/run_all.sh --timeout 900` 綠（背景跑；已知環境紅見 README 通例）；`git diff --stat` 只含「範圍：檔案」列的檔，且 `web.py` 的 diff 不含 /settings、/launch；`BASE_CONFIRM`／`BASE_EXPIRED` 只有 `-en` 鍵變、`-zh` 鍵原值（ledger 貼新舊雜湊）；ledger 貼 diff stat、逐條被改的既有斷言；PR 附五處畫面（確認頁 en、任務分頁、succeeded 選單、送出／下游階段、左欄）zh／en 截圖。

## 環境事實
- origin/v3＝b00263c6（2026-11-05 查）。五個 issue 皆 OPEN（`gh issue view` 確認）。
- 程式位置：`web.py` `_PLAIN` :90、`_page` :151、`view_of` :386、`state_page` :437、`confirm_get` :462、`confirm_post` :472；`web_board.py` `PLACEHOLDER` :22、`_projects` :450、`_left` :460、`_stage_card` :487、`tab_body` :741、`_run_page` :770（選單 :796–800）、`document(title, body, refresh, board, lang, …)`、`pick_lang`。`status.py:59` 的 `project` 取自 Nextflow `projectName`（以路徑啟動的 run 就是腳本檔名 `main.nf`）；`tasks` 計數來自 runs 表 `n_*`，`failed_tasks` 來自另一張表（兩者可不一致，#336 的成因）。
- DESIGN.md 相關條文：Skeleton（左欄依專案分組、專案名為小標題；未實作項灰字「之後開放」）、Formal notices（一個按鈕＝`failure.actions[0]`，另一個留在選單）、Running stage（Resume／Re-run 在 run 選單 → 確認頁）、Constraints（`?lang=en` 伺服器端；每個畫面都有英文版）、Open（只有登入、/welcome、同意頁中英並列）。
- 頁面硬限制：無 `<script`、無 `style=`、單一 `<style>`、CSP 不變、不新增 CSS；`test_web_wording_sweep.py` 禁字表；en 頁無 CJK（run 名稱除外）。
- 並行任務：另有「web bug batch B」「SSH 掉線原因」兩份計畫，檔案可能與 `web_board.py` 重疊，落地前 `git merge origin/v3`，衝突只保留雙方新增。
- PITFALLS 已查（`docs/PITFALLS.md`；`docs/solutions/` 不存在）：網頁相關只有第 51 條「The 011a web layout was rejected because the plan had no design spec (2026-10-18).」——Symptom: the maintainer rejected the whole 011a web layout（計畫只寫功能、verifier 只閱功能）。對應本片：每項修正都依 DESIGN.md 條文與 issue 的「預期」寫斷言，不另創視覺決策；其餘條目的 `launch`／`web` 皆指 plugin／Seqera 路徑，無相符項。

## 不做
- POST 結果頁（`已送出`、`未送出`、`表單已失效`）的英文版——後續片（裁決 R2）。
- `/c/*` 上的語言切換連結——DESIGN.md 沒定義（裁決 R1）。
- 翻譯 `<pre>` 技術摘要；翻譯動作層寫出的 `summary`。
- 真正的「專案」概念、以管線名稱（如 `nf-core/ampliseq`）分組的資料來源（需改 `receiver.py`／`status.py`／`store.py`）——後續片（裁決 R6）。
- 結果階段（Results）的選單、其他階段的選單；`failure.actions` 驅動的選單全面改寫（裁決 R4 的方案 B）。
- #363 與任何其他 issue；不改 DESIGN.md、CSS、CSP、`dev-queue.json`。

## 裁決（預設值，維護者無異議 executor 照做）
- **R1** `/c/*` 不加語言切換連結。理由：DESIGN.md 無此設計；英文版由 `?lang=en` 進入（通知連結已帶）。
- **R2** 本片只修 GET 頁與其 404；POST 結果頁維持中文，列後續。
- **R3** #336 規則：`failed` 計數大於可列出的明細列數時，顯示 `failed_unlisted`／`failed_partial` 說明句；不嘗試判斷「忽略」或「重試成功」（規格未寫）。文字見「作法」第 5 點。
- **R4** #337 預設方案 A：只有 `succeeded` 的分析移除 resume／relaunch／cancel；`failed`／`lost`／`running` 維持現狀（既有測試 `test_web_running.py:217` 不動）。方案 B（所有狀態依 `failure.actions` 決定選單，running 只留 cancel，failed 只留 actions 內的動作）會改動 :217 與 `test_web_board.py`、`test_web_resume_edit.py`（:127、:146–183）、`test_web_fixes_1.py` 的多條斷言，風險升級；維護者要 B 再重跑 `reuseContract:false`。
- **R5** #339 用既有 `_later(t)` 灰字；「送出」階段的送出摘要（DESIGN.md 畫面 5／6）是後續功能，不在本片做。
- **R6** #340 暫以「`*.nf` 且無 `/` 的名稱＝腳本檔名＝沒有專案」處理；更好的來源（Seqera 風格的 pipeline 名稱）列後續。
- **R7** en 確認頁的 CJK 檢查豁免 `<pre>`（技術摘要）與資料值（run 名稱、路徑）；其餘不得有中文。

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
