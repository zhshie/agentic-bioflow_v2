---
id: clean-page-fee-flake
title: test_clean_page 的「頁面沒有 fee 這個字」會被隨機十六進位 id 誤觸發（CI 偶爾紅）——先遮掉 id 與 CSRF 再比對
tier: A
kinds: backend
lane: L42-clean-page-flake
branch: fix/clean-page-fee-flake
base: origin/v3（行號取自 origin/v3@0259726；executor 開工前用 `git show origin/v3:<檔>` 重查）。與忙碌檔無交集：只改一支既有測試檔，不碰任何產品程式碼。
source: GitHub Actions run 40866704682（v3 push，PR #279 合併，2026-10-29 11:36 UTC）shard 3/4 失敗，`--retry-failed-once` 重跑後綠，記為 FLAKY；失敗行 `FAILED tests/test_clean_page.py::test_the_texts_have_no_fee_or_thirty_day_reminder_and_the_style_sheet_is_unchanged - assert 'fee' not in '<!doctype h...v></article>'`。（待 developer-agent 確認）
---

# clean-page-fee-flake

> 只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。**只改測試檔。**

## 目標
`test_clean_page.py` 有一條檢查「確認頁與看板的文字沒有『費用／fee／cost』這些字」。它比對的是整頁 HTML，而頁面裡有隨機產生的 32 位十六進位 id（確認請求 id）與 CSRF token；十六進位字母只有 a–f，`fee` 剛好能由 `f`、`e`、`e` 組成，所以每跑一次約有 1% 的機率，隨機 id 裡剛好出現 `fee`，測試無端變紅（CI 已發生一次，靠自動重跑才綠）。修法：比對前先把十六進位長串遮掉。對使用者的意義：CI 少一次假紅，主導者與 executor 不用再分辨真假紅。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- 同檔檔頭（`platform/tests/test_clean_page.py:3-4`）程式作者自己的說法：「a hash of the page with every 32+ hex run, i.e. ids and CSRF tokens, masked」——這支檔案的其他比對早就先遮掉 id 與 token，這條漏了。
- `docs/TESTING.md`／flaky-tests 系列（`memory/dev-plans/flaky-tests.md`、`flaky-three.md` 檔頭）慣例：「讓測試變確定性只能更嚴，不能更鬆」；不得加 skip／xfail／retry，不得刪斷言。

## 範圍：檔案（只准改這一個）
- `platform/tests/test_clean_page.py`（只動 `test_the_texts_have_no_fee_or_thirty_day_reminder_and_the_style_sheet_is_unchanged`，第 457–467 行，與在其後新增測試函式）
- **不准碰**：任何 `platform/abf_platform/` 產品程式碼、`confirm.py`、`web.py`、`web_board.py`、`web_settings.py`、其他測試檔、其他測試函式的既有斷言。

## 作法
- **證據**（origin/v3@0259726）：
  - 失敗的比對：`platform/tests/test_clean_page.py:457-467`。第 461 行 `words = re.sub(r"<style>.*?</style>", "", c.get("/c/" + rid).text, flags=re.S) + notices(board(w, "ann").text)[0]`；第 463–464 行 `for word in ("費用", "月費", "30 天", "cost", "Cost", "fee"): assert word not in words`。
  - 為什麼有隨機十六進位：確認請求 id 是 `secrets.token_hex(16)`（`platform/abf_platform/confirm.py:46`，另 `:98` 產生第二種 id），頁網址 `/c/<rid>` 與表單 action 會把它印進 HTML；CSRF token 同為十六進位長串（見檔頭註解）。
  - 同檔已有的遮罩函式：`test_clean_page.py:30-33` 的 `mask()`，第一行 `re.sub(r"[0-9a-f]{32,}", "X", text)`。
- **決定**：
  1. 第 461 行組出 `words` 之後、迴圈之前，先把 `[0-9a-f]{32,}` 遮成 `X`（沿用 `mask()` 的第一個正規式；**不要**直接呼叫 `mask()`，它還會把含 `/tmp/` 的字串遮掉，那會藏住真正想檢查的文字）。
  2. 文字清單、斷言、`css`／`BASE_STYLE` 那兩行**一字不動**。
  3. 不改成 `\bfee\b`：那會放過 `fees`／`fee:` 之類真正的違規字，變鬆。
  4. 遮罩只吃 32 字元以上的十六進位長串；`fee` 若出現在正常文字裡（例如「fee」「fees」），遮罩碰不到，仍會被抓到。

## 失敗先行測試
加在原測試之後；先寫、改正式比對之前跑一次確認紅，紅的輸出貼進 ledger。
- `test_a_request_id_that_contains_fee_does_not_fail_the_wording_check`：用 `monkeypatch.setattr` 把 `confirm` 模組裡的 `secrets` 換成一個只改 `token_hex` 的替身（`token_hex(n)` 回傳 `"feed" * (n // 2)`，長度剛好 `2*n` 個字元；其他屬性轉給真的 `secrets`，避免弄壞別處），然後照原測試的步驟建立請求（`run_and_request(w, ann)`）、取確認頁。斷言：(a) 頁面原文**確實含** `fee`（證明這個情境真的撞到，防測試空過）；(b) 遮罩後的文字不含 `fee`。**改前**：若測試直接複製原斷言（對原文比對），會紅——這就是紅燈證據；實作時把「對原文比對」寫成一個小函式 `_words_of(w, rid)` 讓新舊測試共用，改前先讓它回傳未遮罩文字確認紅，再加遮罩轉綠。
- 對照組（必須一直綠）：在**未**替換 `token_hex` 的情況下，原測試 `test_the_texts_have_no_fee_or_thirty_day_reminder_and_the_style_sheet_is_unchanged` 仍綠；`test_no_inline_style_no_external_resource_and_the_same_headers_as_a_launch_page`（第 471 行起）及同檔所有其他測試維持綠。
- 真違規仍被抓：新增 `test_a_real_fee_word_is_still_caught`：把 `words` 的遮罩後文字加上字串 `"monthly fee"` 後，用同一個檢查函式比對，必須判為違規（以 `pytest.raises(AssertionError)` 或回傳布林皆可，由 executor 選一種，另一種不採用）；`"費用"`、`"30 天"`、`"cost"` 同理各一條。這條證明遮罩沒有把檢查變鬆。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑 `test_clean_page.py`，貼輸出。

## 完成標準（done when）
- 新增的第一條測試改前紅、改後綠；對照組與「真違規仍被抓」全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含 `platform/tests/test_clean_page.py`；原測試的詞表（`費用`、`月費`、`30 天`、`cost`、`Cost`、`fee`）與 `BASE_STYLE` 斷言逐字未改；沒有 skip／xfail／retry；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_clean_page.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- CI 已知此件：run 40866704682 shard 3/4 的失敗被 `--retry-failed-once` 標為 FLAKY 並通過，所以 v3 合併沒被擋；根因是上面的隨機 id，不是時序。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不改 `confirm.py` 的 id 長度、字元集（不把 id 改成不含 `fee` 的格式——那是用產品行為去遷就測試）。
- 不掃其他測試檔找類似問題；僅在 ledger 附一行掃描結果：`platform/tests` 內以「全由 a–f 構成的短字」做 `not in` 比對、而被比對文字含隨機十六進位的其他斷言（掃過 `bad`、`add`、`dec`、`ace`、`face`、`cafe`、`beef`、`dead`、`feed`、`fee`，2026-10-29 初步 grep 只找到本件；`test_web_welcome.py:534` 的 `bad` 是 `class="bad"` 計數，不受影響。此為粗略 grep，非完整稽核）。若 executor 發現別處也中，回報 developer-agent 另開一件，不在本件順手修。
- 不放寬詞表、不改 `\b` 邊界、不加 retry。

## 裁決
1. **遮罩門檻 32 字元。** 與同檔 `mask()`（第 31 行）一致；確認 id 與 token 都是 32 字元（`token_hex(16)`）。**建議：沿用 32。** 待 developer-agent 確認。
2. **替身 `secrets` 的寫法**：若 `confirm.py` 還用到 `secrets` 的其他函式，替身要轉給真的。**建議：用 `types.SimpleNamespace` 或小類別加 `__getattr__` 轉發。** 待 developer-agent 確認。
3. **是否順便給 `docs/PITFALLS.md` 加一條「測試比對整頁 HTML 前先遮十六進位 id」。** `PITFALLS.md` 不在本件範圍。**建議：不加；若 developer-agent 想要，另開文件小件。** 待 developer-agent 確認。

### developer-agent 確認（2026-10-29 21:1x）
三點全部照建議定案：遮罩門檻 32 個十六進位字元（沿用檔內 `mask()`）；只把 `token_hex` 換成固定值的轉發替身；不改 PITFALLS.md。只准改測試檔，不准改 `confirm.py` 或任何正式程式碼；不准刪掉或放寬原本對「fee／費用／cost」的檢查。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
