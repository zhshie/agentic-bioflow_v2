# 測試案例：臨時密碼登入後的「設定自己的密碼」頁（/welcome）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Source: specs/web-change-password/plan.md (no spec.md; the plan carries the maintainer's words, the seven steps, the ten failing-first tests W1-W10 and the rulings 1-8; where the plan text and a ruling disagree, the ruling wins, as the plan says).
-->

**規格**：`specs/web-change-password/plan.md`（本任務沒有獨立 spec.md，維護者原話與裁決都在計畫裡）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：

- 「臨時密碼」＝管理者在平台主機終端機用 `abf-platform user passwd <name> --temporary` 產生、只顯示一次、72 小時內有效的密碼（上一個任務 `temp-password` 已做好）。
- 「臨時 session」＝用臨時密碼登入後，瀏覽器拿到的登入狀態（cookie）。「一般 session」＝用自己設的密碼登入的。
- 「記一次失敗」＝登入頁已有的防猜密碼機制：同一個姓名 1 分鐘內錯 5 次（`FAIL_LIMIT`）、同一個網路位址 1 分鐘內錯 20 次（`IP_FAIL_LIMIT`）就回 429「太頻繁」。`/welcome` 沿用同一組計數。
- 「csrf」＝表單裡藏的一個防偽記號，沒帶或不對就拒絕。
- 「不呼叫 store」＝網頁程式在自己這一層就擋下，沒有去動資料庫裡的密碼。

所有「自動」案例由 executor 寫成測試，每個測試在註解寫出自己的 TC 編號。新測試放 `platform/tests/test_web_welcome.py`（用既有的 `w.web()`、`w.login(...)`；臨時密碼用 `store.issue_temporary_password`；時間用 `clock` 參數移動）；既有測試的修改只限計畫許可的那幾個。表單三個密碼欄的欄位名稱依計畫作法 5 稱為 `old`（目前的臨時密碼）、`new`（新密碼）、`confirm`（再輸入一次），隱藏欄為 `csrf`。「手動」案例由閱卷者讀 diff、截圖或 `docs/TESTING.md` 核對。

維護者原話（出題依據）：

1. 「照你建議」（2026-10-25；回應：遠端同事沒辦法到平台主機的終端機打密碼，由管理者發一次性臨時密碼，第一次網頁登入必須改成自己的）
2. 憲法 6.1.0：「a session that logged in with it reaches only the page that changes the password; it cannot see runs or press send」

## US1 — 臨時密碼登入後被帶到 /welcome（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | W1；作法 2；原話 1 | 功能 | 使用者 ann 持有管理者剛發的臨時密碼 | 在 `/login` 送出 ann 的姓名與臨時密碼 | 回 303，`Location` 是 `/welcome`；有設登入 cookie，且 cookie 的屬性與一般登入一致（HttpOnly、SameSite=Strict、path=/） | 自動：`platform/tests/test_web_welcome.py` |
| TC-002 | W1；作法 2 | 功能 | 同 TC-001 | 登入表單另帶 `next=/usage` | 回 303，`Location` 仍是 `/welcome`（不是 `/usage`） | 自動 |
| TC-003 | 作法 2「忽略 `next`」 | 功能 | 同 TC-001；ann 有一筆待確認的申請 `rid` | 登入表單另帶合法的 `next=/c/<rid>`（現行允許的那種網址） | 回 303，`Location` 仍是 `/welcome`（不是 `/c/<rid>`） | 自動 |
| TC-004 | W1；作法 2「否則照舊」 | 功能 | ann 用自己設的一般密碼；有合法的 `next=/c/<rid>` | 先帶 `next` 登入，再用另一個瀏覽器不帶 `next` 登入 | 帶 `next` 的回 303 到 `/c/<rid>`；不帶的回 303 到 `/`（兩者都與改動前一樣） | 自動 |

## US2 — 臨時 session 只到得了 /welcome（優先度 P1）

維護者原話 2：「a session that logged in with it reaches only the page that changes the password; it cannot see runs or press send」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-005 | W2；作法 3 | 功能 | ann 有一筆名字很特別的 run；ann 用臨時密碼登入 | 用臨時 session 打 `GET /` | 回 303，`Location` 是 `/welcome`；回應內容不含那個 run 的名字 | 自動 |
| TC-006 | W2；作法 3 | 功能 | 同 TC-005 | 用臨時 session 分別打 `GET /settings`、`GET /usage` | 兩者都回 303 到 `/welcome`，內容不含 run 名稱 | 自動 |
| TC-007 | W2；作法 3 | 功能 | 同 TC-005 | 用臨時 session 打 `GET /launch` 與 `POST /launch` | 兩者都回 303 到 `/welcome`；沒有新增任何申請或工作（`w.jobs()` 仍為空） | 自動 |
| TC-008 | W2；作法 3 | 功能 | 同 TC-005 | 用臨時 session 對 `/act/resume`、`/act/relaunch`、`/act/cancel` 各送一次 POST（同來源，帶任意 csrf） | 三者都回 303 到 `/welcome`；沒有新增任何申請或工作 | 自動 |
| TC-009 | W2；裁決 2 | 功能 | ann 有一張待確認單 `rid` | 用臨時 session 打 `GET /c/<rid>` | 回 303 到 `/welcome`；確認單仍是 pending；內容不含 run 名稱 | 自動 |
| TC-010 | W2；裁決 2；原話 2「cannot press send」 | 功能 | 同 TC-009 | 用臨時 session 對 `/c/<rid>` 送 POST，csrf 用「正確算出的」那一個 | 回 303 到 `/welcome`；沒有任何工作被送出（`w.jobs()` 為空）；確認單仍是 pending | 自動 |
| TC-011 | W2；裁決 2 | 功能 | 有一筆屬於 ann 的 OAuth 同意請求 `rid`（尚未決定） | 用臨時 session 打 `GET /consent/<rid>` 與 `POST /consent/<rid>`（`decision=allow`，csrf 正確） | 兩者都回 303 到 `/welcome`；該 OAuth 請求仍未被決定、沒有發出授權碼 | 自動 |
| TC-012 | 原話 2；裁決 1（`test_tc027`） | 功能 | ann 有 run 與待確認單；ann 用臨時密碼登入 | 對網站上每一條路由、每個方法各送一次請求，只略過 `/login`、`/logout`、`/.well-known*`、`/register`、`/token`、`/revoke`、`/welcome`、`/authorize`（共至少 8 條） | 每一個回應都是 303 且 `Location` 是 `/welcome`；沒有任何回應含 run 名稱；沒有工作被送出、確認單仍 pending（即 `test_tc027` 改後的樣子） | 自動：`platform/tests/test_temp_password.py::test_tc027` |
| TC-013 | W2；作法 3「原行為」 | 例外 | 完全沒登入（沒有 cookie） | 打 `GET /`、`/settings`、`/usage`、`/launch`，`POST /launch`、`POST /act/resume` | 全部回 303 到 `/login`（與改動前一樣，不是 `/welcome`） | 自動 |
| TC-014 | 裁決 2「沒登入的行為維持原樣」 | 例外 | 完全沒登入；有一張確認單 `rid` 與一筆 OAuth 同意請求 | 打 `GET /c/<rid>`、`POST /c/<rid>`、`GET /consent/<rid>`、`POST /consent/<rid>` | 與改動前逐項相同：GET 回 200 的登入頁（帶 `next`），POST 回 401 的登入頁；不是導向 | 自動 |
| TC-015 | 作法 3「否則照舊」；W7 | 例外 | 臨時 session 已建立，之後時間移過 72 小時 | 用那個 session 打 `GET /` | 回 303 到 `/login`（臨時密碼已過期，不再被導到 `/welcome`） | 自動 |
| TC-016 | 作法 3「否則照舊」 | 例外 | 帶一個簽章不對的偽造 cookie | 打 `GET /` | 回 303 到 `/login`，不是 `/welcome` | 自動 |
| TC-017 | 作法 3「不改判斷」 | 功能 | ann 已用一般密碼登入、有一筆 run | 打 `GET /` | 回 200，看得到自己的 run（與改動前一樣，沒有被導去 `/welcome`） | 自動 |
| TC-018 | 裁決 1（`test_tc025`） | 功能 | ann 用臨時密碼登入 | 用臨時 session 打 `GET /` | 回 303，`Location` 是 `/welcome`（原本期望 `/login`，這是計畫許可的唯一改動） | 自動：`platform/tests/test_temp_password.py::test_tc025` |
| TC-019 | 裁決 1 | 功能 | 一個臨時 session、一個沒登入的瀏覽器 | 兩邊各打 `/authorize`（GET 與 POST，同樣的參數） | 兩邊的狀態碼與 `Location` 逐項相同（行為沒變） | 自動 |
| TC-020 | 裁決 1「其他斷言一字不改」 | 功能 | `test_temp_password.py` 裡 `test_tc026` 等保護臨時 session 的測試 | 跑這些測試；比對與 base 的差異 | 全部照舊通過；除 `test_tc025`、`test_tc027` 外，該檔其他測試沒有被改 | 自動：`platform/tests/test_temp_password.py` |

## US3 — /welcome 頁面本身（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | W3；作法 4 | 功能 | ann 用臨時密碼登入 | 用臨時 session 打 `GET /welcome` | 回 200；標題是「設定你自己的密碼 (set your own password)」 | 自動 |
| TC-022 | 作法 4；裁決 4 | 功能 | 同 TC-021 | 看 `/welcome` 的說明文字 | 含中文句「你用的是管理者給的臨時密碼，它 72 小時內有效、只能用來設定你自己的密碼。設好之後就用新密碼登入。」，以及英文句「You are using a one-time temporary password from your administrator. It works for 72 hours and only lets you set your own password. After that, log in with your new password.」 | 自動 |
| TC-023 | W3；作法 4 | 功能 | 同 TC-021 | 看表單欄位 | 恰好三個密碼欄（`type="password"`）：「目前的臨時密碼」`old`（`autocomplete="current-password"`）、「新密碼」`new` 與「再輸入一次新密碼」`confirm`（兩者 `autocomplete="new-password"`） | 自動 |
| TC-024 | 作法 4 | 功能 | 同 TC-021 | 看欄位旁的長度說明 | 與登入頁同一句格式，數字取自程式常數：「（8 到 1000 個字元 / 8 to 1000 characters）」 | 自動 |
| TC-025 | W3；作法 4 | 功能 | 同 TC-021 | 看表單的隱藏欄與按鈕 | 有隱藏欄 `csrf`，值等於這個 session 對 `"welcome"` 算出的記號；有且只有一顆送出鈕「設定密碼 (set password)」 | 自動 |
| TC-026 | 作法 4 | 功能 | 同 TC-021 | 看頁面上的登出表單 | 有一個 `POST /logout` 的表單，csrf 值等於該 session 對 `"logout"` 算出的記號 | 自動 |
| TC-027 | W10 | 功能 | 臨時 session | 用該頁的登出表單送出（csrf 正確），再打 `GET /welcome` | 登出回 303 到 `/login` 並清掉 cookie；之後 `GET /welcome` 回 303 到 `/login` | 自動 |
| TC-028 | W3；作法 4「不出現任何 run」 | 功能 | ann 有 run、專案與費用資料；ann 用臨時密碼登入 | 看 `GET /welcome` 的全部內容 | 不含 ann 任何 run 名稱、專案名稱、費用 | 自動 |
| TC-029 | W3；作法 4 | 例外 | ann 用一般密碼登入 | 打 `GET /welcome` | 回 303 到 `/`（一般使用者改密碼仍走終端機） | 自動 |
| TC-030 | W3；作法 4 | 例外 | 沒有 cookie | 打 `GET /welcome` | 回 303 到 `/login` | 自動 |
| TC-031 | W7 | 例外 | 臨時 session 已建立，時間移過 72 小時 | 用那個 session 打 `GET /welcome` | 回 303 到 `/login` | 自動 |
| TC-032 | 作法 5.2 | 例外 | 沒有 cookie | 同來源送 `POST /welcome`（任意欄位） | 回 303 到 `/login`，沒有任何密碼被改 | 自動 |
| TC-033 | 作法 5.2 | 例外 | ann 用一般密碼登入，csrf 值自己算對 | 送 `POST /welcome`（同來源，三欄都填） | 回 303 到 `/`；ann 的密碼沒有被改（仍可用原密碼登入） | 自動 |

## US4 — 設好新密碼，同一個登入直接進看板（優先度 P1）

維護者原話 1：「照你建議」——遠端同事拿一次性臨時密碼，第一次網頁登入改成自己的。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | W4；作法 5.9 | 功能 | ann 用臨時密碼登入，在 `/welcome` 取得 csrf | 送 `POST /welcome`：`old`＝臨時密碼，`new` 與 `confirm` 同為 8 字元以上的新密碼，csrf 正確，同來源 | 回 303 到 `/`；回應沒有 `Set-Cookie`（cookie 不動） | 自動 |
| TC-035 | W4；原話 1 | 功能 | 接 TC-034，ann 有一筆 run | 用同一個 cookie（不重新登入）打 `GET /` | 回 200，看得到 ann 自己的 run | 自動 |
| TC-036 | W4 | 功能 | 接 TC-034 | 在新瀏覽器分別用舊臨時密碼、新密碼登入 | 舊臨時密碼登入失敗（401）；新密碼登入成功，且 `must_change` 為 False（不再被導去 `/welcome`） | 自動 |
| TC-037 | 作法 5.9 | 功能 | 接 TC-034 | 用同一個 cookie 打 `GET /welcome` | 回 303 到 `/`（這個 session 已不是臨時的） | 自動 |
| TC-038 | 作法 5.9「成功→拿回剛計的那次」 | 功能 | 同一時間內，ann 先在 `/login` 錯 4 次（`FAIL_LIMIT`-1），再用臨時密碼登入，並在 `/welcome` 成功改密碼 | 登出後，在 `/login` 再錯 1 次 | 該次回 401（不是 429）：成功那一次沒有被算進失敗次數 | 自動 |
| TC-039 | 原話 1「照你建議」 | 功能 | 管理者對 ann 發臨時密碼（`store.issue_temporary_password`） | ann 用臨時密碼登入 → 落在 `/welcome` → 設好新密碼 → 看板 → 登出 → 用新密碼登入 → 再用臨時密碼登入 | 全程只登入一次就進看板；用新密碼登入成功；臨時密碼失敗 | 自動 |
| TC-040 | 完成標準；W4 | 功能 | `docs/TESTING.md` | 讀手動驗收新一節 | 有一節依序寫出：①終端機 `abf-platform user passwd <name> --temporary` 並記下密碼 ②瀏覽器登入、落在 `/welcome` ③直接打 `/` 會被帶回 `/welcome` ④設新密碼、進看板 ⑤登出再用新密碼登入成功、臨時密碼失敗；每步具體到可照做 | 手動：`docs/TESTING.md` |

## US5 — 設定失敗各種情況與次數限制（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | W5；作法 5.5 | 例外 | ann 臨時 session；監看 store 的密碼更改函式 | `POST /welcome`：`new` 與 `confirm` 不同，其餘都對 | 回 400，頁面顯示「兩次輸入的新密碼不一樣 (the two new passwords differ)」；store 的更改函式沒被呼叫；ann 的密碼沒變 | 自動 |
| TC-042 | W5；作法 5.5 | 例外 | 同 TC-041 | 連送 5 次兩次新密碼不同，再送 1 次「目前密碼錯」 | 最後一次回 401（不是 429）：「兩次不同」不計失敗 | 自動 |
| TC-043 | W5；作法 5.8 | 例外 | ann 臨時 session | `POST /welcome`：`old` 填錯的密碼，其餘都對 | 回 401，頁面顯示含「目前的密碼不對」的雙語句；ann 的密碼沒變 | 自動 |
| TC-044 | W5；作法 5.8 | 例外 | 同 TC-043，同一分鐘內 | 連送 5 次 `old` 錯誤，再送第 6 次 | 前 5 次回 401；第 6 次回 429（「目前的密碼不對」計入失敗） | 自動 |
| TC-045 | W5；作法 5.8 | 例外 | ann 臨時 session | `POST /welcome`：`new` 與 `confirm` 都等於 `old` | 回 400，頁面顯示含「新密碼不能跟目前的一樣」的雙語句；密碼沒變；不計失敗（連送 5 次後再送一次「目前密碼錯」仍回 401） | 自動 |
| TC-046 | W5；作法 5.8 | 例外 | ann 臨時 session | `POST /welcome`：`new` 與 `confirm` 同為 7 個字元 | 回 400，頁面顯示含「密碼至少 8 個字元」的雙語句；密碼沒變；不計失敗 | 自動 |
| TC-047 | 作法 5.8「長度」 | 例外 | ann 臨時 session | `POST /welcome`：`new` 與 `confirm` 同為 1001 個字元 | 回 400，頁面顯示含「密碼最多 1000 個字元」的雙語句；密碼沒變；不計失敗 | 自動 |
| TC-048 | 作法 5.8「剛被改過」；裁決 6 | 例外 | 用替身讓 store 的更改函式丟出含「密碼剛被改過」的 `ValueError` | `POST /welcome`（其餘都對） | 回 400，頁面原樣顯示該句；不計失敗（連送 5 次後再送一次「目前密碼錯」仍回 401） | 自動 |
| TC-049 | W5；作法 5.6 | 例外 | ann 臨時 session；監看 store 的更改函式 | `POST /welcome`：`old` 為 1001 個字元，其餘都對 | 回 400，頁面顯示含「密碼最長 1000 個字元」的句子；store 沒被呼叫；計一次失敗（連送 5 次後第 6 次回 429） | 自動 |
| TC-050 | W5；作法 5.3 | 例外 | ann 臨時 session | `POST /welcome`：csrf 填錯的值，其餘都對 | 回 403；ann 的密碼沒變（臨時密碼仍可登入） | 自動 |
| TC-051 | 作法 5.3 | 例外 | 同 TC-050 | 連送 5 次 csrf 錯誤，再送 1 次「目前密碼錯」 | 最後一次回 401（不是 429）：csrf 錯不計失敗 | 自動 |
| TC-052 | 作法 5.3 | 例外 | ann 臨時 session | `POST /welcome` 完全不帶 `csrf` 欄 | 回 403；密碼沒變 | 自動 |
| TC-053 | W5；作法 5.1 | 例外 | ann 臨時 session | `POST /welcome`，`Origin` 是別的網站，其餘都對 | 回與登入頁相同的「來源不符 (wrong origin)」403 頁；密碼沒變 | 自動 |
| TC-054 | W6；作法 5.4 | 例外 | ann 臨時 session，同一分鐘內 | 在 `/welcome` 連續送 5 次 `old` 錯誤，再送第 6 次（這次 `old` 正確、其餘都對） | 第 6 次回 429，頁面含「登入失敗太頻繁，請一分鐘後再試 (too many tries, wait a minute)」且仍顯示設定密碼的表單；密碼沒變 | 自動 |
| TC-055 | W6 | 例外 | ann 先在 `/login` 用錯密碼 4 次，再用臨時密碼登入（成功，不增加計數） | 在 `/welcome` 送 1 次 `old` 錯誤（總數到 5），再送 1 次 | 第一次回 401，第二次回 429（`/login` 與 `/welcome` 共用同一個姓名計數） | 自動 |
| TC-056 | 作法 5.4（同一個網路位址） | 例外 | 同一位址在一分鐘內用數個不同姓名在 `/login` 錯滿 20 次（每個姓名都不到 5 次）；ann 另有臨時 session | 在 `/welcome` 送 `POST`（csrf 正確） | 回 429（`/login` 與 `/welcome` 共用同一個位址計數） | 自動 |
| TC-057 | 作法 5.4（沿用同一套時間窗） | 例外 | ann 在 `/welcome` 已被鎖（429） | 把時間移過 60 秒以上，再送一次正確的設定 | 不再是 429；設定成功（回 303 到 `/`） | 自動 |
| TC-058 | 作法 5.「順序固定」 | 例外 | ann 已被鎖（429 狀態） | 送 csrf 錯誤的 `POST /welcome` | 回 403（csrf 檢查在次數限制之前） | 自動 |
| TC-059 | 作法 5.「順序固定」 | 例外 | ann 已被鎖 | 送兩次新密碼不同的 `POST /welcome`（csrf 正確） | 回 429（次數限制在「兩次不同」之前） | 自動 |
| TC-060 | 作法 5.「順序固定」 | 例外 | ann 已被鎖 | 送來源不符的 `POST /welcome` | 回「來源不符」403（來源檢查最先） | 自動 |
| TC-061 | 作法 5「名字用 session 的 name」 | 例外 | ann 臨時 session；另有使用者 bob，持有一般密碼 | `POST /welcome` 多帶一個 `name=bob` 欄，`old` 填 bob 的密碼 | 回 401；bob 的密碼沒變、ann 的密碼沒變（只有 session 本人會被當作要改的人） | 自動 |
| TC-062 | W5；作法 5 末段 | 例外 | 任一失敗（TC-041、043、045、046、049 各一種） | 看重畫出來的表單 | 三個密碼欄一律是空的（沒有 `value` 屬性帶回剛輸入的內容） | 自動 |
| TC-063 | W8；作法 5 末段 | 例外 | 用三個容易辨認的獨特字串當 `old`、`new`、`confirm`；開啟 caplog | 逐一走過 TC-041、043、045、046、048、049、050、053、054 的各種失敗與成功 | 所有回應本文、`Location`、`Set-Cookie` 與 caplog 都不含那三個字串（成功那次同樣不含） | 自動 |

## US6 — 登入頁說明句、文件與畫面限制（優先度 P2）

計畫的前端限制：零 JS、無 `style=`、單一樣式表、390 px 無橫捲、`Cache-Control: no-store`；畫面沿用登入頁外框，視為 DESIGN.md 已決定（裁決 3）。`/welcome` 沒有載入中或空的狀態（沒有 JS、沒有資料列表）；它的狀態是：初始、400／401（錯誤）、403（失效／來源不符）、429（太頻繁）、成功（導向）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-064 | 作法 6 | 功能 | 沒登入 | 打 `GET /login` | 說明句是「請用你的姓名與網頁密碼登入（網頁密碼不是 AI 用的權杖；它在平台主機的終端機用 `abf-platform user passwd` 設定，或用管理者給你的一次性臨時密碼）。」 | 自動 |
| TC-065 | 作法 6 | 功能 | 同上 | 看 `GET /login` 全文 | 不再含舊句「它只能在終端機用」 | 自動 |
| TC-066 | 範圍：檔頭路由清單 docstring | 功能 | `platform/abf_platform/web.py` 檔頭 | 讀檔頭路由清單 | 清單列出 `/welcome`（GET 與 POST） | 手動：閱卷者讀 diff |
| TC-067 | 裁決 7 | 功能 | `docs/PLATFORM.md` 網頁路由說明散文 | 讀該段 | 補了一句 `/welcome`：臨時密碼登入後唯一可到的頁面，設定自己的密碼 | 手動：閱卷者讀 diff |
| TC-068 | 作法 7；專長守則 | 功能 | 取得 `/welcome` 初始頁與 TC-041、043、050、054 的各錯誤頁 HTML | 檢查每份 HTML | 沒有 `<script`、沒有 `on…=` 事件屬性、沒有 `style=`；只有一份樣式表；沒有指向外部網址的資源 | 自動 |
| TC-069 | 作法 7 | 功能 | 同 TC-068 | 看 200／400／401／403／429 各種回應標頭 | 都有 `Cache-Control: no-store`、`X-Frame-Options: DENY`，`Content-Security-Policy` 與登入頁的相同 | 自動 |
| TC-070 | 作法 4；裁決 3 | 功能 | 同 TC-068 | 比較 `/welcome` 與 `/login` 的 HTML 外框 | 使用同一個頁面外框與同一份樣式表引用（沒有新增樣式或視覺元素） | 自動 |
| TC-071 | 專長守則「狀態不只靠顏色」；裁決 5 | 功能 | 取得 TC-041、043、054 的錯誤頁 | 看錯誤訊息 | 每個錯誤都是放在 `<p class="bad">` 裡的完整句子（說明發生什麼事），不是只靠 `bad` 的顏色表意；不要求另加符號（裁決 5） | 自動 |
| TC-072 | 專長守則「使用者視角白話」 | 功能 | 取得 `/welcome` 初始頁與各錯誤頁 | 搜尋頁面文字 | 不出現內部詞：`must_change`、`temp_until`、`ValueError`、`store`、`session`、`Traceback` | 自動 |
| TC-073 | 專長守則「手機可用」；作法 7 | 功能 | developer-agent 附在 PR 的 `/welcome` 390 px 截圖 | 看截圖 | 沒有橫向捲動；欄位與按鈕夠大可點；文字不被裁掉 | 手動：閱卷者看截圖 |
| TC-074 | 專長守則「焦點外框可見」 | 功能 | `/welcome` 頁，用鍵盤 Tab 切換 | 依序 Tab 過三個欄位、按鈕、登出鈕 | 每個可操作元件取得焦點時外框看得到（沿用既有樣式） | 手動：閱卷者開頁面操作或看截圖 |
| TC-075 | 完成標準（截圖） | 功能 | PR 說明 | 看附圖 | 有三張：`/welcome` 1440 px、`/welcome` 390 px、錯誤狀態（兩次新密碼不同） | 手動：閱卷者看 PR |
| TC-076 | 專長守則（偵測器） | 功能 | 把 `/welcome` 初始頁與錯誤頁用測試客戶端存成 HTML 檔 | `sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>` | 偵測器能跑完；其發現列入報告「需要人看的事」，不單獨判失敗 | 手動：閱卷者執行 |

## 憲法與安全網

touched：憲法 6.1.0（臨時密碼 session 只能到改密碼頁；個人權杖與 `Authorization: Bearer` 仍不能登入網頁）、原則 I.2（誰的「同意」算數：只有登入的本人在確認頁按送出）、`test_tch05`（網頁沒有重設／忘記密碼的門）、`web.py` 字詞檢查。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-077 | 6.1.0「A personal access token and an `Authorization: Bearer` header still never log into the web」 | 例外 | ann 有個人權杖 | 帶 `Authorization: Bearer <權杖>`、不帶 cookie，打 `GET /welcome` 與 `POST /welcome` | 都回 303 到 `/login`；ann 的密碼沒有被改 | 自動 |
| TC-078 | 作法 1；W9（`test_tch05`） | 功能 | 既有測試 `test_oauth_mcp.py::test_tch05_…` | 跑該測試；比對與 base | 一字不改、照舊通過：所有路由路徑不含 `reset|forgot|passwd|password`（`/welcome` 符合），`/account` 等仍回 404／405 | 自動：`platform/tests/test_oauth_mcp.py` |
| TC-079 | 作法 1；W9（原始碼字詞檢查） | 功能 | 既有字詞檢查（`test_oauth_mcp.py` 約 395-400 行） | 跑該測試 | `web.py` 原始碼不出現 `forgot`、`reset_password`、`resetpassword`、`google`、`github`、`openid`、`oidc`、`saml`、`idp`；測試本身沒被放寬 | 自動 |
| TC-080 | 原則 I.2；6.1.0「cannot press send」 | 功能 | 既有人類通道測試 `test_tch09_*`（`test_human_channel.py`）與 `test_tch09_b_c_*`（`test_confirm_page.py`） | 跑這些測試；比對與 base | 全部照舊通過，沒有被改：沒有確認就不會送出的規則沒被這次改動繞過 | 自動 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-081 | 不做：設定頁的「改密碼」入口 | 不在範圍 | ann 用一般密碼登入 | 打 `GET /settings` | 頁面沒有指向 `/welcome` 的連結、沒有任何改密碼的表單或按鈕；設定頁內容與 base 相同 | 自動 |
| TC-082 | 不做：一般使用者在網頁改密碼 | 不在範圍 | ann 用一般密碼登入 | 打 `GET /welcome`，再送 `POST /welcome`（csrf 自行算對） | GET 回 303 到 `/`、POST 回 303 到 `/`；密碼沒有被改（網頁上只開放臨時密碼那一次） | 自動 |
| TC-083 | 不做：忘記密碼、寄信重設 | 不在範圍 | 沒登入 | 對 `/forgot`、`/reset`、`/password`、`/passwd`、`/account` 送 GET 與 POST；看 `/login` 與 `/welcome` 頁面 | 全部 404（POST 為 404 或 405）；兩頁都沒有「忘記密碼」「寄信重設」的連結或文字 | 自動 |
| TC-084 | 不做：管理者在網頁發臨時密碼 | 不在範圍 | 網站的路由表與 `web.py` 原始碼 | 跑 `test_owner_binding.py::test_tc068_no_new_way_to_log_in` | 路由集合比 base 恰好多 `/welcome`；`web.py` 用到的 `store.*` 名稱比 base 恰好多 `change_web_password`（沒有 `issue_temporary_password` 之類）；該測試只加了這兩項 | 自動：`platform/tests/test_owner_binding.py` |
| TC-085 | 不做：不改 `store.py` 與 CLI；範圍「不准動」 | 不在範圍 | `git diff <base>...HEAD --stat` | 列出所有被改的檔案 | 沒有 `store.py`、`actions/`、`mcp_server.py`、`oauth.py`、`http_auth.py`、`cli.py`、`web_settings.py`、憲法、ADR、`spec.md`、`test-case*.md`；改動限於計畫「範圍：檔案」所列 | 手動：閱卷者核對 diff（不寫入 `docs/TESTING.md`） |
| TC-086 | 裁決 3「`web_board.py` 與樣式表不變」 | 不在範圍 | 同上 | 比對 `web_board.py` | 沒有任何改動（沒有新增顏色、字型、間距或元件） | 手動：閱卷者核對 diff |
| TC-087 | 範圍：既有測試只准動指定處 | 不在範圍 | 本次 diff 中所有被改的既有測試 | 逐檔比對與 base | `test_oauth_mcp.py` 的 `test_tch05` 與字詞檢查沒動；`test_temp_password.py` 只改 `test_tc025`、`test_tc027`；`test_owner_binding.py` 的 `test_tc068` 只加 `"/welcome"` 與 `"change_web_password"` 兩項；其他釘住登入頁說明句的測試只改那一句；每處都在 ledger 寫明理由；沒有被放寬、略過或改期望值的斷言 | 手動：閱卷者核對 diff 與 ledger |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
