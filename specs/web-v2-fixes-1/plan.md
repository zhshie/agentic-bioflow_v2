---
id: web-v2-fixes-1
title: 網頁 v2 第一批修正：標題列按鈕收進選單、失敗 run 的階段條與目前步驟、左欄長名稱換行
tier: B
kinds: ui
lane: L7-web-redesign
base: v3
source: PR #177 截圖（developer-agent 自查三個瑕疵）＋維護者 10-24「按照你的建議」（標題列三顆按鈕收進選單，只留右欄一顆）
---

# web-v2-fixes-1

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/web-v2-fixes-1/plan.md`。**只處理本任務**。前置：web-v2-skeleton（PR #177）已合併。
> 維護者 10-23：「先把功能做起來吧，以後再改美觀」——只用現有 class 與 DESIGN.md token，不追求新視覺。

## 目標
失敗的分析頁上只有一個看得到的主動作（右欄通知那顆）；其他動作收進標題列的「更多」選單。失敗 run 的階段條與「目前步驟」說實話。左欄長步驟名不再超出欄位。

## 維護者原話（verifier 出題用）
1. 「狀態只要running, failed, successed就好，failed下面再去分原因，看是要改參數、重跑、續跑，直接告訴使用者要做甚麼，不是讓他們選。」（10-22 23:50）
2. developer-agent 10-24 問：「失敗頁上方還留著『續跑／重跑／取消』三顆按鈕，右欄又有一顆『續跑』。要不要把上方三顆收進選單，只留右欄那一顆？」維護者答：「按照你的建議。」（10-24）

## 範圍：檔案
- `platform/abf_platform/web_board.py`
- `platform/tests/test_web_board.py`（只限下方「要改寫的既有斷言」）
- `platform/tests/test_web_running.py`（同上）
- `platform/tests/test_web_v2_skeleton.py`（同上）
- `platform/tests/test_web_fixes_1.py`（新檔）

## 作法
**1. 標題列選單（`_run_page`）**
- 現在標題列直接放 `acts.form` 的三顆按鈕（resume、relaunch、cancel）＋「用這個 run 的內容再啟動一次」連結。改成一個零 JS 的原生選單：`<details class="menu"><summary>更多</summary>…</details>`（en `More`），三個 form 與那條連結原樣放進 `<details>` 裡面，順序不變。
- 每個 form 的 action、hidden 欄位、按鈕文字一字不變（`/act/*` 與確認頁不動，ADR 0006 不變）。
- 選單在所有 run 頁都一樣（執行中也收進選單），只在原本就會出現按鈕的情況出現（`running` 階段頁且有 acts）。
- `<details>` 關著時，標題列看得到的按鈕數＝0；整頁看得到的 `<button>` 只剩右欄通知那顆（失敗 run）或 0 顆（執行中）。`<summary>` 要能用鍵盤聚焦、焦點外框可見、點擊目標高度 ≥ 44px（沿用既有按鈕的 min-height 規則）。
- CSS 只加 `.menu` 與 `.menu > summary` 的規則，沿用既有 token；不新增顏色、字型、間距數值。

**2. 失敗 run 的階段條**
- `status` 為 failed 或 lost 時，「執行」那一格的文字由「執行中／Running」改成「✗ 執行／✗ Run」，加 class `is-failed`（顏色沿用 `state-failed` 的 token）。其他格不變；running 時仍是「執行中」，succeeded 時仍是「✓ 執行中」以外的既有寫法不動。
- 新字串鍵：`stage_running_failed`：zh「執行」、en「Run」。

**3. 失敗 run 的「目前步驟」卡**
- failed／lost 時，卡片標題改成「停在／Stopped at」（新鍵 `card_stopped_at`），內容＝`first_failed(failure)`（第一個失敗 task 名）；沒有就 `—`。running 時不變。

**4. 左欄長名稱換行**
- 左欄每列第 2 行（`.r2`）加 `overflow-wrap: anywhere`（`.nm` 維持省略號，見裁決 8），讓 `NFCORE_AMPLISEQ:DADA2_DENOISING` 這種長字在欄內換行；1440 與 390 寬都不得超出左欄、頁面不得橫向捲動。

**不能放掉的限制**：零 JavaScript（`<details>` 是原生元素，不算 JS）、無 `style=`、單一樣式表且 CSP 雜湊相符、15 秒 refresh、每人只看自己的 run、英文頁無 CJK。

## 失敗先行測試
`platform/tests/test_web_fixes_1.py`（種子沿用 `test_web_v2_skeleton.std`）：
- `test_f01_header_actions_are_in_a_closed_menu`：失敗 run 頁標題列（`<div class="head">`）內所有 `<form class="act">` 都在 `<details class="menu">` 裡；`<details>` 沒有 `open` 屬性；`<summary>` 文字為「更多」（en `More`）。
- `test_f02_one_visible_button_on_a_failed_page`：把所有 `<details>…</details>` 去掉後，整頁 `<button>` 恰一顆，在右欄、文字＝`failure.actions[0]` 對應的字。
- `test_f03_menu_forms_unchanged`：選單內三個 form 的 action（/act/resume、/act/relaunch、/act/cancel）、hidden `run`／`csrf`、按鈕文字與改之前相同；POST 其中一個仍回確認頁、不建 job。
- `test_f04_running_page_menu_and_no_visible_button`：執行中 run 頁，去掉 `<details>` 後 `<button>` 0 顆；選單存在。
- `test_f05_failed_stage_cell`：failed 與 lost run 的階段條「執行」格文字為「✗ 執行」（en「✗ Run」）、class 含 `is-failed`；running run 仍為「執行中」。
- `test_f06_stopped_at_card`：failed run（有失敗 task）的卡片標題「停在」、內容 `NFCORE_AMPLISEQ:DADA2_DENOISING`；沒有失敗 task 的 failed run 內容 `—`；running run 仍是「目前步驟」。
- `test_f07_long_names_wrap`：樣式表含 `.r2` 與 `.nm` 的 `overflow-wrap: anywhere`。
- `test_f08_constraints_hold`：失敗頁與執行中頁無 `<script`、無 `style=`、CSP 雜湊相符、有 15 秒 refresh、`?lang=en` 無 CJK。

**要改寫的既有斷言**（行為依維護者 10-24 裁示改變；ledger 逐條列「舊 → 新」）：
- 斷言標題列有三顆可見按鈕、或數整頁 `<button>` 數量的既有測試 → 改成在 `<details class="menu">` 內找。
- `test_web_board.py:571` 一類釘階段名 `["送出","執行中",…]` 的斷言：只在 failed／lost 種子上改成「✗ 執行」；running 種子不變。
- 斷言 failed run 卡片「目前步驟」為 `—` 的既有斷言 → 「停在」＋失敗步驟。
- 其他測試檔（`test_web_actions.py`、`test_confirm_page.py`、`test_web_confirm_plain.py`、`test_web_parity.py`、`test_resume_scope.py`、`test_launch_*.py`、`test_failures.py`）一字不改；若因此變紅，回報 BLOCKED，不要自行改。

## 完成標準（done when）
八條新測試綠；改寫的既有斷言在 ledger 逐條列出；全套綠（裁決 1 的已知環境紅除外）。截圖由 developer-agent 拍。

## 環境事實
- 現況（origin/v3，PR #177 合併後）：`_run_page`（`web_board.py:~543`）裡 `buttons = "".join(acts.form(verb, …) for verb in ("resume","relaunch","cancel"))`、`quick` 連結；階段格 `cells`（`kind` = is-done／is-current／is-later，`label = ("✓ " if done) + t["stage_"+s]`）；`_current_step`（`:~425`）；`_detail`、`first_failed`、`_failure_of`；`Acts.form`（`:~439`）；`STRINGS` 中 `stage_running`、`card_step`。
- 全套測試在這台桌機 WSL 要 `--timeout 900`（platform_test.sh 約 6 分鐘）；跑 pytest 後先刪 `platform/**/__pycache__`，否則 `jev_test.sh` TC-085 會被 .pyc 誤判紅。

## 不做
- 不動右欄通知、確認頁、`/act/*`、`failures.py`、`actions/__init__.py`。
- 不決定「選單裡哪些動作該出現」（例如失敗 run 還留取消）——原樣收進去，之後再議。
- 不做終端機、對話、自動續跑。

## 裁決
1. **已知環境紅**：`tests/init_workspace_test.sh` 的「site side with no run area known fails clearly」在桌機 WSL 因 `mkdir /work` 權限紅（base 同紅、CI 綠）。判定全套綠時只排除這一條；ledger 記下後寫 `GREEN <HEAD>`。
2. 英文字：`More`、`✗ Run`、`Stopped at`。中文：`更多`、`✗ 執行`、`停在`。
3. 守則測試若有掃描「已取消」「failure」等字，`web_board.py` 已有例外（PR #177 裁決 11），不需再改。

4. **數按鈕的範圍＝中欄＋右欄**（`data-pane="middle"` 與 `data-pane="right"`）。左欄底部的「登出」按鈕不算、不動。f02：去掉 `<details>` 後中欄＋右欄 `<button>` 恰一顆（右欄）；f04：中欄＋右欄 0 顆。
5. **44px**：允許 `.menu > summary` 新增 `min-height: 44px`（並用 flex／align-items 置中），這是本任務唯一新增的數值；其他不新增顏色、字型、間距數值。
6. **CSS 允許範圍**＝`.menu`、`.menu > summary`、`.steps .is-failed`（顏色用既有 state-failed token）、`.r2` 的 `overflow-wrap: anywhere`。
7. **階段條**：succeeded 的執行格維持現況（`✓ 執行中`、無 is-failed）。failed／lost 的執行格 class 可以是 `is-current is-failed`；`test_web_board.py:561-569` 對 failed／lost 種子斷言單一 is-* 的，在範圍內改寫為「含 is-current 與 is-failed」。數按鈕的 `test_web_board.py:703`、`:807`、`test_web_running.py:187` 也在範圍內改寫（改成在 `<details class="menu">` 內數）。全部列進 ledger。
8. **左欄長名**：只要求 `.r2` 換行；`.nm` 維持單行省略號（不改）。f07 改成只檢查 `.r2`。1440／390 都不得超出左欄、不得橫向捲動。
9. **沒有 acts 時**：選單照樣出現，裡面只有那條「再啟動一次」連結；不另出題。

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
