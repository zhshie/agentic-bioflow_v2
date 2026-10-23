---
id: web-v2-skeleton
title: 網頁改成 DESIGN.md v2 骨架：左欄依專案的分析清單、三種狀態、右欄＝這個分析的對話與 Seqera 式失敗通知
tier: B
kinds: ui
lane: L7-web-redesign
base: v3
source: DESIGN.md v2（PR #167 已合）、ADR 0011、PR #166 的 failure 欄位；草稿 https://claude.ai/artifact/3B2pu4Fo1GfLPYNqjBRAES（V3-failed／V3-running）
supersedes: web-list-home（10-23 HOLD，清單首頁＋處置欄已被否決）
---

# web-v2-skeleton

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/web-v2-skeleton/plan.md`。**只處理本任務**。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只要功能正確、沿用現有樣式表的 class 與 token，不追求新視覺。

## 目標
網頁照 DESIGN.md v2 的三欄骨架運作：左欄是依專案分組的分析清單（每列兩行：名稱＋狀態、`階段 · 細節`），中欄是選中的那個分析，右欄只放這個分析的正式通知。狀態只有三種；失敗通知用 Seqera 的欄位，只有一顆按鈕。「現在」頁拿掉。

## 維護者原話（verifier 出題用）
1. 「狀態只要running, failed, successed就好，failed下面再去分原因，看是要改參數、重跑、續跑，直接告訴使用者要做甚麼，不是讓他們選。"現在"的這個中間畫面有點多餘」（10-22 23:50）
2. 「我說過不要口語的AI，但你給使用者的按鈕都是"用24G續跑"，哪有一個固定的按鈕會這樣寫?」（10-23）
3. 「處置那邊很奇怪，不需要。我希望一個session處裡一條pipline，出問題非用者決定不可的問題了，ai直接告訴使用者要幹嘛。下載、看結果甚麼的點進去看就好了。」（10-23）
4. 「為甚麼沒看到之前設計過的，pipline裡面要有的launch, run, result等左右視窗?」（10-23）
5. 「分成四類 改成 跟Seqera platform一樣的模式，不要自己定義」（10-23 20:15）
6. 「進來之後馬上可以看到各個run的狀態與進度」（DESIGN.md 原話 1）
7. 「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」（DESIGN.md 原話 7）

## 範圍：檔案
- `platform/abf_platform/web_board.py`
- `platform/abf_platform/web.py`（只動 `board`／`board_page`／`read_details` 與首頁選擇；`/act/*`、確認頁、登入不動）
- `platform/abf_platform/status.py`（只在 `_view` 加一個鍵 `project`）
- `platform/tests/test_web_board.py`
- `platform/tests/test_web_running.py`
- `platform/tests/test_web_actions.py`（只限裁決 5 的 TC-004）
- `platform/tests/test_web_v2_skeleton.py`（新檔）

## 作法

**資料**
- `status._view` 加 `"project": row["project_name"]`（欄位不存在或為 NULL → `None`）。`list_runs`／`get_run` 都帶它。不改表、不需要 migration（`project_name` 欄已在 `store.py`）。
- 失敗資訊只讀 run 的 `failure` 欄位（#166：`status_seqera`、`failed_tasks`、`failure_reason`、`log`、`actions`）。網頁不自己分類原因。`web.py` 的 `read_details`／`reasons`／`steps` 不再需要：清單用 `list_runs` 每列已有的 `failure`，選中的 run 用 `get_run` 的 `failure`。

**三種狀態**（只是顯示）：`running`→「▶ 執行中／Running」；`succeeded`→「✓ 完成／Succeeded」；`failed` 與 `lost`→「✗ 失敗／Failed」。`SYMBOLS["lost"]` 改成 `✗`、lost 的 CSS 狀態類用 failed 的。頁面上任何地方不再出現「失聯／暫停／Lost／Paused」作為狀態字。

**`/` 不再有自己的頁**：沒有 `?run=` 時，伺服器選一個 run 當成選中，直接畫那個 run 的頁（不轉址，網址不變）：
1. 最新的 failed／lost run（`started_at` 新到舊的第一個）；
2. 沒有就最新的 run；
3. 完全沒有 run → 中欄畫空狀態：一行 `還沒有分析／No analyses yet` ＋一個連到 `/launch` 的「＋ 新分析」。
「現在／Now」標題、attention 卡、running 卡、紅色計數一律拿掉。

**左欄**（取代 `_left` 的清單部分；設定、登出、灰字項目保留）：
- 依 `project` 分組，組名＝專案名（小標題 `h3`）；`project` 為 `None` 的放最後一組「未分專案／No project」。組的順序＝組內最新 run 的 `started_at` 新到舊；組內 run 新到舊。總數仍受 `LIST_CAP`。
- 每列是一個連到 `?run=<id>` 的連結，兩行：
  - 第 1 行：名稱 ＋ 狀態（符號＋文字，帶狀態 class）。
  - 第 2 行 `階段 · 細節`：running →「執行 · 完成數 / 總數」；`status_seqera`=`failed` →「執行 · <failed_tasks[0].name，沒有就 —>」；`status_seqera`=`cancelled` →「執行 · 已取消／Cancelled」；`status_seqera`=`unknown`（lost）→「執行 · 站台沒有回應／Site not responding」；succeeded →「結果／Results」。
- 選中的那列加 `here`（既有 class）。最上方「＋ 新分析」連 `/launch`（取代現在的 launch 導覽字）。拿掉「現在」與紅色數字。

**中欄**（`_run_page`）：
- 標題列不變（名稱、狀態徽章），下面加切換：`主視窗` 是目前頁（`aria-current="page"`），`終端機` 是灰字不是連結，後面接 `之後開放／Coming later`（終端機在後端車道，另案）。
- 五階段條、上一步／下一步、摘要卡、分頁照舊。
- 拿掉中欄的「這個分析的通知」卡（`notices_here`）——通知只在右欄。
- 執行中階段的 續跑／重跑／取消 按鈕留在標題列（＝該 run 的選單；DESIGN「The other action stays in the run menu」）。

**右欄**（取代 `_right`）：
- 標頭：小字「這個分析的對話／This analysis」＋選中 run 的名稱。沒有選中 run 時只放標頭小字＋`—`。
- 通知依時間排列；本任務只有一種：選中的 run 若 `failure` 不為 `None`，畫一張失敗通知：
  - 級別列：`! 需要你處理／Action needed`，右邊時間（failed 用 `ended_at`，lost 用 `last_message_at`，台北時間 `HH:MM`）。
  - 欄位（`<dl>`，順序固定）：`步驟／Step` = `failed_tasks[0].name`（包在 `<code>`；沒有就 `—`）；`原因／Reason` = `failure_reason` 的最後 3 個非空行（每行截 `REASON_CAP` 字）；沒有 `failure_reason` 時：cancelled →「已取消／Cancelled」、unknown →「站台沒有回應／Site not responding」、其他 → `failed_tasks[0].error_message` 第一行或 `—`；`之後／Next` = `actions[0]` 的動詞加「（確認頁）／(confirmation page)」，例：「續跑（確認頁）」。
  - 恰一顆按鈕：`actions[0]` 的固定動詞（`續跑／Resume` 或 `重跑／Re-run`），用既有 `Acts.form(verb, run_id)`（POST `/act/<verb>` → 確認頁）。
- 其他 run 的任何資訊都不出現在右欄（不再有全部分析的分組、計數）。
- 最下方一行灰字 `問這個分析 之後開放／Ask about this analysis — coming later`（對話在 M5，另案）；不放輸入框。
- 按鈕文字只能是固定動詞；數字、檔名、記憶體量只出現在欄位，不出現在按鈕或級別列。

**不能放掉的限制**：零 JavaScript、無 `style=`、單一樣式表（CSP 雜湊）、15 秒 refresh、每人只看自己的 run（左欄、右欄、`/` 的預設選擇都只用 caller 自己的 run）、`?lang=en` 每個字都有英文。

## 失敗先行測試
`platform/tests/test_web_v2_skeleton.py`（用 `test_web_board` 既有的 `seed()`；種：專案 P1 的 1 筆 running、1 筆 succeeded；專案 P2 的 1 筆 failed（failed task `NFCORE_AMPLISEQ:DADA2_DENOISING`、failure_reason 5 行、有 succeeded task → actions 以 resume 開頭）、1 筆 failed 沒有任何 succeeded／cached task（→ 只有 relaunch）；無專案的 1 筆 lost、1 筆 cancelled；另一位使用者 1 筆 failed）：
- `test_v01_root_opens_newest_failed_run`：`GET /` 200，中欄 h1 是最新那筆 failed／lost 的名稱；沒有「現在／Now」標題、沒有 `data-card=`。
- `test_v02_root_without_failed_opens_newest`：只有 running／succeeded 時，h1 是最新那筆。
- `test_v03_root_empty_state`：沒有 run → 「還沒有分析」＋連到 `/launch` 的「＋ 新分析」。
- `test_v04_only_three_state_words`：整頁狀態字只出現 執行中／完成／失敗（en：Running／Succeeded／Failed）；不出現「失聯」「暫停」「Lost」「Paused」「⏸」。
- `test_v05_left_grouped_by_project`：左欄組名依序符合「各組最新 run 新到舊」，無專案組在最後；每列第 2 行符合「作法」的對照（含 cancelled、unknown、succeeded「結果」）。
- `test_v06_right_is_this_analysis_only`：選 P1 的 running → 右欄只有標頭與名稱、沒有通知、不出現其他 run 的名稱。
- `test_v07_failure_notice_fields`：選 P2 failed → 右欄恰一張通知，級別「! 需要你處理」，`<dt>` 依序 步驟／原因／之後；步驟是 `<code>NFCORE_AMPLISEQ:DADA2_DENOISING</code>`；原因是 failure_reason 最後 3 個非空行；之後「續跑（確認頁）」。
- `test_v08_exactly_one_button_actions0`：上一筆右欄恰一顆按鈕「續跑」，form action `/act/resume`；只有 relaunch 的那筆是「重跑」→ `/act/relaunch`；POST 後 303 到 `/c/<id>`、沒有直接建立 job。
- `test_v09_button_text_is_fixed_verb`：右欄與標題列所有按鈕文字 ∈ {續跑, 重跑, 取消, 登出}（en 對應），不含數字、GB、檔名。
- `test_v10_lost_and_cancelled_reason`：lost 那筆原因「站台沒有回應」、cancelled 那筆原因「已取消」。
- `test_v11_no_notice_in_middle`：中欄（`data-pane="middle"`）內沒有 `class="notice`。
- `test_v12_terminal_switch_is_grey`：中欄有「主視窗」（`aria-current="page"`）與「終端機」＋「之後開放」，且「終端機」不在 `<a>` 內。
- `test_v13_owner_rule`：另一位使用者的 failed 不在左欄、不會被 `/` 預設選中、`?run=<他的 id>` 404。
- `test_v14_english`：`?lang=en` 下 v04、v05、v07、v08 的字全是英文。
- `test_v15_constraints_hold`：`/` 與失敗 run 頁無 `<script`、無 `style=`、CSP 雜湊相符、有 15 秒 refresh。
- `test_v16_project_key`：`actions.list_runs` 與 `get_run` 每筆都有 `project` 鍵；P1 的 run 為 `"P1"`，無專案的為 `None`。

**允許更新的既有斷言**（行為依維護者裁示改變，不是放水；PR 說明逐條列「舊斷言 → 新斷言」）：
- `test_web_board.py` 中測 Now 頁、attention／running 卡、`card_*`、左欄「現在」與紅色計數、右欄「全部分析」分組與計數、`⏸`／「失聯」狀態字、中欄通知卡的斷言。
- `test_web_running.py` 中測中欄通知卡欄位（問題／原因／可選動作、多顆按鈕）與 `_notice` 的斷言 → 改測右欄新欄位。
- **不准改**：`test_web_actions.py`（除裁決 5 的 TC-004）、`test_confirm_page.py`、`test_web_confirm_plain.py`、`test_web_parity.py`、`test_web_login.py`、`test_web_chrome_origin.py`。其中任何一條因本任務變紅，回報 BLOCKED，不要自己改。

## 完成標準（done when）
十六條新測試綠；改寫的既有斷言在 PR 說明逐條列出；全套 `tests/run_all.sh` 綠；上面「不准改」的測試檔一字未改。截圖（1440／390 px × zh／en，失敗 run 頁＋執行中 run 頁）由 developer-agent 用 `memory/scripts/abf-shots/` 拍，不是 executor 的事。

## 環境事實
- 現況（origin/v3 1db9ad5）：首頁 `Route("/", board)`（`web.py:607`）→ `board_page`（`web.py:378`）→ `web_board.render_board`；`read_details`（`web.py:~365`）用 `get_run` 讀 failed run 的 `failure_reason` 與第一個 failed task；`_left`（`web_board.py:349`）、`_right`（`:584`）、`_notice`（`:439`）、`_now_page`（`:555`）、`failed_ids_shown`（`:602`）、`SYMBOLS`（`:25`）、`REFRESH_SECONDS = 15`（`:22`）、`REASON_CAP = 80`（`:21`）。
- `failures.summarize`（`failures.py`）：lost → `status_seqera="unknown"`；有 `cancel_requested_at` → `"cancelled"`；`actions` 在有 succeeded／cached task 時是 `["resume","relaunch"]`，否則 `["relaunch"]`。`actions/__init__.py:78-90` 的 `list_runs` 每個 failed／lost 列已帶 `failure`。
- `store.py` runs 表已有 `project_name TEXT`。
- 截圖工具（developer-agent 用，不是 executor）：`memory/scripts/abf-shots/`。

## 不做
- 終端機、自動續跑、OTP（後端車道，ADR 0011）。
- 對話輸入框與 AI 回覆（M5）。
- 自動處理通知（nf-core 重試）與下游通知（項目／檔案／下一步）——沒有資料來源，之後的任務做。
- 新視覺、改 token、改確認頁、改 `/act/*`。
- 不動 `failures.py`、`actions/__init__.py`。

## 裁決
（2026-10-24 預檢後，developer-agent。與上面各段衝突時以本段為準。）
1. **「專案」＝ `project_name`，它其實是 Nextflow 的 projectName（pipeline 名，例 `nf-core/ampliseq`、`main.nf`）**——平台目前沒有使用者層級的「專案」概念。本任務照樣用它分組，組名照原字顯示；NULL 的放「未分專案／No project」。測試種子用 `nf-core/ampliseq`、`nf-core/rnaseq` 代替 P1／P2。真正的專案概念另案。
2. **級別列沿用既有的 pill**：`<span class="level state-failed"><span class="sq"></span> 待處理</span>`（en `Pending`），不加「!」、不改成「需要你處理／Action needed」——`test_web_actions.py` TC-042／TC-045 釘住這個寫法（方塊＋一個字，不加新符號）。test_v07 改成斷言這個 pill。
3. **右欄沒有通知時**顯示既有字「目前沒有待處理的事／Nothing pending」（TC-043 釘住），test_v06 照此斷言。
4. **狀態字**：只改 board 用的 `state_*`：`state_succeeded` 「成功」→「完成」（en 已是 Succeeded）；`state_lost` 改成與 `state_failed` 相同（失敗／Failed）。**`chip_*`（/launch 頁的方塊字）不動**（TC-044 釘住 `Done`）。test_v04 只檢查 `/` 與 `/?run=` 頁、只看 `state_*` 輸出的位置（左欄列與標題徽章），不看 `/launch`。
5. **`test_web_actions.py::test_tc004_notices_carry_real_forms` 允許改寫**（唯一一條）：舊＝中欄 `<article>` 內同時有 resume 與 relaunch 表單；新＝右欄（`data-pane="right"`）的 `<article>` 內恰一個表單，verb＝`failure.actions[0]`，POST 後得到確認頁 id。PR 說明列舊→新。`test_web_actions.py` 其他測試仍不准改。
6. **「最新」的同分處理**：照 `list_runs` 的順序（`started_at DESC, rowid DESC`）取第一個，不另排序。
7. **測試種子 helper**（寫在新檔 `test_web_v2_skeleton.py` 內，不改 `test_web_board.seed`）：`project_name` 用 `UPDATE runs SET project_name=? WHERE id=?`；failed task 沿用 `test_web_running.py` 的 `extra()` 寫法插 `failed_tasks`；cancelled 依 `jobs.cancel_requested_at` 讀的 state db launches 表做 UPDATE（先讀 `jobs.py` 確認欄名）。
8. **不動 `docs/TESTING.md`**（L1 車道的 preflight-nano4 也在改它；車道檔案集合必須不相交）。截圖步驟由 developer-agent 自己做。
9. `test_web_parity.py` 不受影響：網頁仍只呼叫 `list_runs`／`get_run` 與既有 request_*；拿掉 `read_details` 不新增呼叫。`test_resume_scope.py`：`web.py` 不准新增名字含 resume／relaunch 的識別字。

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
