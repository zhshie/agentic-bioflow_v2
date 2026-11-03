# 測試案例：clean-page-fee-flake（確認頁文字檢查被隨機 id 誤觸發）

<!--
Written by the verifier (CONTRACT mode). 這件是 A 級測試修正，沒有 spec.md；依據是 specs/clean-page-fee-flake/plan.md（含 developer-agent 2026-10-29 確認的三項裁決）。
「對應需求」欄寫的是計畫的段落。維護者沒有留下逐字的操作範例，只有計畫「維護者原話」三條；以下 TC 的輸入與預期結果都來自計畫裡寫明的情境，沒有加料。
-->

**規格**：`specs/clean-page-fee-flake/plan.md`（本件無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、邊界情況下，檢查要怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

名詞：「文字檢查」＝ `platform/tests/test_clean_page.py` 裡檢查「確認頁與看板的文字不含 費用／月費／30 天／cost／Cost／fee」的那條測試。「遮罩」＝把 32 個以上的十六進位字元（0-9、a-f）換成 `X`。「替身」＝測試裡暫時換掉 `secrets.token_hex` 的假零件，讓請求 id 變成固定值。

## User Story 1 — 請求 id 碰巧含 fee 時，文字檢查不再誤判變紅（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「失敗先行測試」(a) | 功能 | 測試把 `confirm` 模組的 `secrets` 換成替身，`token_hex(16)` 固定回傳 `"feed" * 8`（32 字元）；用 `run_and_request(w, ann)` 建立請求 | 登入後取確認頁 `/c/<id>` | 頁面原文（未遮罩）確實含 `fee`；測試對此有斷言，證明這個情境真的撞到、不是空跑 | 自動：`ABF_PYTEST_TARGETS=tests/test_clean_page.py bash tests/platform_test.sh` |
| TC-002 | 計畫「失敗先行測試」(b)；作法決定 1 | 功能 | 同 TC-001 | 取遮罩後的文字（確認頁去掉 style 區塊＋看板通知，再把 `[0-9a-f]{32,}` 換成 `X`），用文字檢查的六個詞（費用、月費、30 天、cost、Cost、fee）比對 | 遮罩後的文字不含任何一個詞，檢查通過（不報錯） | 自動 |
| TC-003 | 計畫「對照組」 | 功能 | 沒有換替身（用真的隨機 id） | 執行原測試 `test_the_texts_have_no_fee_or_thirty_day_reminder_and_the_style_sheet_is_unchanged` | 通過 | 自動 |
| TC-004 | 計畫「對照組」；作法決定 2（`BASE_STYLE` 那兩行一字不動） | 功能 | 同 TC-003 | 原測試最後兩行：取看板的 style 區塊算雜湊 | 雜湊仍須等於 `BASE_STYLE`（`66b9a8e1a9c6f7d2`）；斷言仍在，且通過 | 自動 |
| TC-005 | 計畫「對照組」 | 功能 | 本分支 | 執行 `test_clean_page.py` 裡所有其他既有測試（含 `test_no_inline_style_no_external_resource_and_the_same_headers_as_a_launch_page`） | 全部通過；替身只在新測試內生效，沒有影響別的測試 | 自動 |
| TC-006 | 計畫「失敗先行測試」改前紅；「完成標準」第 1、3 點 | 功能 | 實作過程 | 先讓 `_words_of(w, rid)` 回傳未遮罩文字，跑新的第一條測試；再加遮罩 | ledger 貼有「改前紅」的輸出（失敗訊息指出 `fee` 在頁面中）與「改後綠」的輸出；若 ledger 沒有紅燈輸出即不通過 | 手動：閱卷時讀 `specs/clean-page-fee-flake/ledger.md`（見總覽疑問 1） |
| TC-007 | 計畫「兩分支比對」 | 功能 | `origin/v3` 與本分支各一份 | 兩邊各跑 `test_clean_page.py` | ledger 貼出兩邊輸出；`origin/v3` 上既有測試的通過／失敗與本分支相同（本分支只多出新測試且全綠）；沒有任何既有測試在本分支變差 | 手動：閱卷時讀 ledger，並由驗收者在兩個分支各跑一次該檔 |
| TC-008 | 計畫「失敗先行測試」；裁決 2 | 功能 | 新測試裡的替身 | 呼叫替身的 `token_hex(16)` | 回傳 32 個字元的 `feedfeed…`（長度 = 2×參數）；`confirm.secrets` 的其他屬性（例如真 `secrets` 上有的其他函式）仍取得真的那個，沒被弄壞 | 自動 |
| TC-009 | 計畫「失敗先行測試」；裁決 2 | 功能 | 新測試結束後 | 測試離開後再看 `confirm.secrets` | 已還原成真的 `secrets`（用 `monkeypatch`，不洩漏到其他測試） | 自動 |
| TC-010 | 計畫「完成標準」第 2 點 | 功能 | 本分支 HEAD | 在 WSL 跑整個 `platform/tests` 套件 | 全綠（已知環境紅依 dev-plans README「通例：已知環境紅」，須與 `origin/v3` 同樣） | 自動：`tests/run_all.sh`（完成記號 `GREEN <HEAD sha>` 為證） |

## User Story 2 — 真正的違規字仍然被抓到，檢查沒有變鬆（優先度 P1）

這些 TC 證明「遮罩只吃十六進位長串」；對應維護者原話「讓測試變確定性只能更嚴，不能更鬆」「絕不放寬安全網」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫「真違規仍被抓」 | 功能 | 遮罩後的頁面文字 | 在後面接上 `"monthly fee"`，用同一個檢查函式比對 | 判為違規（`AssertionError` 或回傳違規，擇一） | 自動 |
| TC-012 | 同上 | 功能 | 同上 | 接上 `"費用"` | 判為違規 | 自動 |
| TC-013 | 同上 | 功能 | 同上 | 接上 `"30 天"` | 判為違規 | 自動 |
| TC-014 | 同上 | 功能 | 同上 | 接上 `"cost"` | 判為違規 | 自動 |
| TC-015 | 作法決定 3、4 | 例外 | 文字含 `fees`（單字，無十六進位） | 遮罩後比對 | 仍判為違規（沒有改成 `\bfee\b` 那種放過 `fees` 的寫法） | 自動 |
| TC-016 | 作法決定 3、4 | 例外 | 文字含 `fee:` | 遮罩後比對 | 仍判為違規 | 自動 |
| TC-017 | 作法決定 1（不直接呼叫 `mask()`） | 例外 | 文字含像 `/tmp/fee` 的路徑樣式字串 | 遮罩後比對 | 仍判為違規（`mask()` 的第二條規則會把含 `/tmp/` 的字串遮掉，這裡不能用） | 自動 |
| TC-018 | 作法決定 4（只遮 32 字元以上） | 例外 | 文字含一段少於 32 字元的十六進位且含 `fee`（例如 31 字元） | 遮罩後比對 | 不被遮掉，仍判為違規 | 自動 |
| TC-019 | 計畫「真違規仍被抓」（回報方式擇一、另一種不採用） | 功能 | 本分支測試檔 | 讀新增的檢查函式與 TC-011～TC-014 | 全程只用一種回報方式（全用 `pytest.raises(AssertionError)` 或全用布林），沒有混用 | 手動：閱卷時讀 diff |
| TC-020 | 計畫「完成標準」第 3 點；「不做」最後一條（不放寬詞表） | 功能 | 本分支與 `origin/v3` | `git diff origin/v3...HEAD -- platform/tests/test_clean_page.py` | 原測試的詞表 `("費用", "月費", "30 天", "cost", "Cost", "fee")` 六個詞逐字還在，檢查迴圈 `assert word not in words` 還在 | 手動：閱卷時讀 diff |

## User Story 3 — 只改一支測試檔，不碰產品、不放寬（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 計畫「範圍：檔案」；「完成標準」第 3 點 | 不在範圍 | 本分支 | `git diff --stat origin/v3...HEAD`（扣掉 `specs/clean-page-fee-flake/` 下的計畫、ledger 與驗證者產出） | 其餘只有 `platform/tests/test_clean_page.py` 一個檔案 | 手動：閱卷時跑 git diff（見總覽疑問 1） |
| TC-022 | 計畫「不做」第 1 條；「範圍」不准碰 | 不在範圍 | 本分支 | 看 `platform/abf_platform/`（含 `confirm.py`、`web.py`、`web_board.py`、`web_settings.py`）的 diff | 無任何變更；`confirm.py` 的 id 仍是 `secrets.token_hex(16)`（長度、字元集沒改成避開 `fee`） | 手動：閱卷時讀 diff |
| TC-023 | 計畫「範圍」：其他測試函式的既有斷言不准動 | 不在範圍 | 本分支 | 看 `test_clean_page.py` 的 diff 中被刪除或修改的行 | 只出現在 `test_the_texts_have_no_fee_…` 內「組出 `words` 之後、迴圈之前」加遮罩的位置（以及為共用而抽出 `_words_of` 的改寫）；其他測試函式、檔頭 `mask()`、`BASE_STYLE`、`css` 那兩行沒有任何被刪或被改的行 | 手動：閱卷時讀 diff |
| TC-024 | 計畫「不做」最後一條；維護者原話（不得加 skip／xfail／retry，不得刪斷言） | 不在範圍 | 本分支 | 在 `platform/tests/` 的 diff 中搜 `skip`、`xfail`、`retry`、`flaky`、`@pytest.mark` 新增行，並數斷言 | 沒有新增這些標記；原測試的斷言一條沒少 | 手動：閱卷時讀 diff |
| TC-025 | 計畫「作法」決定 3；「不做」 | 不在範圍 | 本分支 | 在檢查函式與測試中找 `\b` 單字邊界或縮窄詞表的寫法 | 沒有 | 手動：閱卷時讀 diff |
| TC-026 | 計畫「不做」第 2 條 | 不在範圍 | 本分支與 ledger | 看其他測試檔的 diff 與 ledger | 其他測試檔無變更；ledger 有一行掃描結果（掃過 `bad`、`add`、`dec`、`ace`、`face`、`cafe`、`beef`、`dead`、`feed`、`fee`），若發現別處也中，只回報不順手修 | 手動：閱卷時讀 diff 與 ledger |
| TC-027 | 計畫「環境事實」不准改；裁決 3 | 不在範圍 | 本分支 | 看 `docs/PITFALLS.md`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 的 diff | 全部無變更（`specs/clean-page-fee-flake/` 的 `test-case*.md` 在實作期間也未被改） | 手動：閱卷時讀 diff |

## 專長守則（backend）對應

本件不改任何產品程式碼（沒有路由、動作層、寫入路徑、資料表），專長守則的規則不新增被改動面；以下兩條證明既有保護沒被這次修改碰壞。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | 專長守則：資料結構變動須附 migration 或寫明不需要 | 不在範圍 | 本分支 | 看 diff 是否含資料表結構或 migration 檔 | 沒有；計畫已寫明只動一支測試檔，不需要 migration | 手動：閱卷時讀 diff |
| TC-029 | 專長守則：確認管道、擁有者規則（跨使用者）；密鑰不外露 | 功能 | 本分支 | 執行同檔既有的「別人看不到我的清理提醒」「沒按確認不改資料」類測試（例如 `test_clean_requests_is_a_read_that_filters_by_caller_and_is_not_a_tool_or_a_route`、`test_no_clean_request_is_made_by_looking_around`） | 這些測試與 `origin/v3` 上逐字相同且全綠；替身只活在新測試內，產品的 id 與 CSRF 產生方式未變 | 自動 |

<!--
- 驗證方式只有「自動」與「手動」。TC-006、007、019～028 的「手動」是閱卷者讀 git diff 與 ledger；docs/TESTING.md 沒有對應步驟，因為計畫只准改一支測試檔（見總覽疑問 1）。
- 編號確認後不重編。
-->
