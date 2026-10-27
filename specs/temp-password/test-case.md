# 測試案例：遠端同事的一次性臨時密碼（後端）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Source: specs/temp-password/plan.md (there is no spec.md; the plan carries the maintainer's words and the three rulings. Where rulings conflict, the larger ruling number wins, as the plan says).
-->

**規格**：`specs/temp-password/plan.md`（本任務沒有獨立 spec.md，維護者原話與三份裁決都在計畫裡）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「臨時密碼」＝管理者在平台主機終端機產生、只顯示一次、72 小時內有效的密碼；「必須改」（`must_change`）＝這個使用者目前持有的是臨時密碼（資料庫欄位 `users.temp_until` 有值）；「fail-closed」＝預設拒絕，漏檢查也只是看起來像沒登入，不會放行。

所有「自動」案例由 executor 寫成測試，每個測試在註解寫出自己的 TC 編號。store 層案例用 `human_harness.World` 的 `w`（`w.ip.tokens` 是 tokens.db），時間一律傳 `now`；終端機案例用 `launch_harness.Pty` 與 `cli_argv`。新測試放 `platform/tests/test_temp_password.py`，文件案例放 `platform/tests/test_onboarding_doc.py`。括號裡的 T 編號是計畫裡「失敗先行測試」的編號。

## US1 — 管理者發臨時密碼（資料層）（優先度 P1）

維護者原話：「照你建議」（管理者發一次性臨時密碼）、「一次性」（只顯示一次、改過一次後不再是臨時、過期作廢）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | T1；作法 3 | 功能 | 有使用者 ann | `issue_temporary_password(tokens, "ann", now=1000.0)` | 回傳的鍵恰好是 `password` 與 `expires_at`；密碼長度 16，且符合 `[A-Za-z0-9_-]{16}` | 自動：`platform/tests/test_temp_password.py` |
| TC-002 | T1；作法 3；裁決 4 | 功能 | 同上 | 同上 | `expires_at` 等於 1000.0 加 259200；`store.TEMP_PASSWORD_SECONDS` 等於 `72*3600` | 自動 |
| TC-003 | T2；作法 3 | 功能 | ann 已有帳號 | 對 ann 連發兩次臨時密碼 | 兩次的密碼不相同 | 自動 |
| TC-004 | T2；作法 3 | 功能 | 發了臨時密碼 | 讀 `users.password_hash`，並掃整個資料夾位元組（`test_web_login.py` 的 `data_bytes` 做法） | 雜湊符合 `scrypt$…` 格式；密碼本身的位元組不在資料夾任何地方 | 自動 |
| TC-005 | T3；作法 3 | 功能 | ann 有兩個以上登入中的 session | 對 ann 發臨時密碼 | ann 的所有 `web_sessions` 都被刪掉（所有瀏覽器登入同時結束） | 自動 |
| TC-006 | T3；作法 3（跨使用者） | 功能 | ann 與 bob 都有 session、各有密碼 | 對 ann 發臨時密碼 | bob 的 session、`password_hash`、`temp_until` 都跟發之前完全一樣 | 自動 |
| TC-007 | 作法 3「再發一次＝覆蓋前一組」 | 功能 | ann 已拿到臨時密碼 A | 再發一次得到 B | A 不能再登入（`check_web_password` 回 None）；B 可以，且 `must_change` 為 True | 自動 |
| TC-008 | 作法 3 | 功能 | ann 目前持有一般密碼 P | 對 ann 發臨時密碼 | P 不能再登入；ann 的 `must_change` 變成 True | 自動 |
| TC-009 | T3；作法 3 | 例外 | 沒有使用者 ghost | `issue_temporary_password(tokens, "ghost")` | 丟 `ValueError`，訊息為 `no such user: ghost (沒有這個使用者)`，含「沒有這個使用者」 | 自動 |
| TC-010 | T3；作法 3 | 例外 | 同 TC-009，另有使用者 ann | 對 ghost 發 | `users` 表列數不變；所有使用者的 `password_hash`、`temp_until`、所有 `web_sessions` 都不變（資料庫完全不變） | 自動 |

## US2 — 臨時密碼的登入判斷與期限（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | T4；作法 5 | 功能 | ann 持有臨時密碼 T | `check_web_password(tokens, "ann", T)` | 回 `{"user_id","name","lab","must_change": True}`，鍵恰好這四個 | 自動 |
| TC-012 | T4；作法 5 | 功能 | bob 持有一般密碼 | 用該密碼呼叫 `check_web_password` | `must_change` 為 False | 自動 |
| TC-013 | T4 | 例外 | ann 持有臨時密碼 | 用錯誤密碼呼叫 | 回 None | 自動 |
| TC-014 | T4 | 例外 | ann 持有臨時密碼，且 ann 已被停用 | 用正確的臨時密碼呼叫 | 回 None | 自動 |
| TC-015 | T5；作法 5 | 功能 | ann 臨時密碼 `expires_at` 為 E | `check_web_password(..., now=E-1)` | 通過，`must_change` 為 True | 自動 |
| TC-016 | T5；「一次性…過期作廢」 | 例外 | 同上 | `check_web_password(..., now=E+1)`（密碼正確） | 回 None | 自動 |
| TC-017 | T5；作法 5 | 功能 | monkeypatch `store.password_matches` 計次 | 分別做一次「臨時密碼過期後登入」與一次「密碼錯誤登入」 | 兩種情況 `password_matches` 都恰好被呼叫一次（耗時相同，不讓人用快慢猜出是過期還是錯） | 自動 |
| TC-018 | T6；作法 4 | 功能 | ann 持有臨時密碼 | 用 `set_web_password` 設新密碼 | `temp_until` 為 NULL；新密碼登入的 `must_change` 為 False | 自動 |
| TC-019 | 作法 4 | 例外 | 一般使用者 | `set_web_password` 傳 7 字元與傳 1001 字元 | 兩種都丟 `ValueError`，訊息與改動前逐字相同（`the password must be at least 8 characters (密碼至少 8 個字元)`、`the password must be at most 1000 characters (密碼最多 1000 個字元)`） | 自動 |
| TC-020 | 作法 5 | 功能 | 既有三參數呼叫與三參數替身 | `check_web_password(tokens, name, password)` 只給三個位置參數；跑 `test_review_fixes.py`、`test_review_fixes_2.py` 既有三參數替身測試 | 三參數呼叫仍可用，既有測試不改就通過 | 自動：`platform/tests/test_review_fixes.py`、`test_review_fixes_2.py` |

## US3 — 臨時密碼的登入什麼都不能做（fail-closed）（優先度 P1）

維護者原話：「第一次網頁登入必須改」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | T7；作法 6 | 例外 | ann 用臨時密碼建了一個 session | `web_session_user(tokens, sid, now)`（不帶旗標） | 回 None（預設當成沒登入） | 自動 |
| TC-022 | T7；作法 6 | 功能 | 同上 | `web_session_user(..., allow_must_change=True)` | 回含 `user_id`、`name`、`lab`、`must_change: True` 的資料 | 自動 |
| TC-023 | T7；作法 6 | 功能 | bob 持有一般密碼並有 session | 分別以預設與 `allow_must_change=True` 呼叫 | 兩次都回 `must_change: False` | 自動 |
| TC-024 | T7；作法 6 | 例外 | ann 的臨時密碼已過期（now 大於 `expires_at`） | 分別以預設與 `allow_must_change=True` 呼叫 | 兩次都回 None | 自動 |
| TC-025 | T8；「第一次網頁登入必須改」 | 例外 | ann 持有臨時密碼 | `w.login(client, "ann", 臨時密碼)` 後 `client.get("/")` | 登入本身回 303；接著 `/` 看到的是登入頁，不是看板 | 自動 |
| TC-026 | T8；ADR 0006「按的必須是我本人」 | 例外 | ann 持有臨時密碼並已登入；ann 有一張待確認申請 `<rid>` | 帶正確 csrf 對 `POST /c/<rid>` 按送出 | 回應不是 200，且 `w.jobs()` 為空（沒有任何工作被送出） | 自動 |
| TC-027 | 作法 6、前端合約「每一條需要登入的路由不用改」 | 例外 | 用臨時密碼登入的 session；列舉 `web.py` 中所有需要登入的路由（含 OAuth 的 `/authorize`） | 逐一用該 session 請求 | 每一條都像沒登入一樣處理（導向登入頁或拒絕），沒有任何一條回出該使用者的資料或接受送出 | 自動 |
| TC-028 | 前端合約「登出不需要改」 | 功能 | 用臨時密碼登入的 session | POST 登出 | 登出成功，該 session 被刪掉 | 自動 |

## US4 — 本人改密碼（優先度 P1）

維護者原話：「一次性」→ 改過一次後不再是臨時。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | T9；作法 7 | 功能 | ann 持有臨時密碼 T 與一個 session sid | `change_web_password(tokens, "ann", T, "a brand new passphrase", keep_sid=sid)` | 回傳的鍵恰好是 `user_id`、`name`、`lab` | 自動 |
| TC-030 | T9；「一次性」 | 功能 | 同上，已改成功 | 分別用舊臨時密碼與新密碼 `check_web_password` | 舊臨時密碼回 None；新密碼通過且 `must_change` 為 False；`temp_until` 為 NULL | 自動 |
| TC-031 | T9；作法 7；裁決 6 | 功能 | ann 有 sid 與其他 session | 以 `keep_sid=sid` 改密碼 | sid 那一筆還在，ann 其他 session 全沒了 | 自動 |
| TC-032 | T9；作法 7 | 功能 | ann 有多個 session | 以 `keep_sid=None` 改密碼 | ann 的 session 全沒了 | 自動 |
| TC-033 | 作法 7（跨使用者） | 功能 | ann 與 bob 各有 session | 改 ann 的密碼時 `keep_sid` 給 bob 的 session id | ann 的 session 全被刪；bob 的 session 一筆不少 | 自動 |
| TC-034 | T10；作法 7③ | 例外 | ann 持有臨時密碼 | 給錯誤的 `old` | `ValueError`，訊息逐字為 `the current password is wrong (目前的密碼不對)`；`password_hash`、`temp_until` 不變 | 自動 |
| TC-035 | T10 | 例外 | 沒有使用者 ghost | `change_web_password(tokens, "ghost", …)` | 同一句 `the current password is wrong (目前的密碼不對)`，不透露使用者不存在 | 自動 |
| TC-036 | T10 | 例外 | ann 已被停用 | 用正確的舊密碼改 | 同一句；雜湊不變 | 自動 |
| TC-037 | T10 | 例外 | ann 的臨時密碼已過期 | 用該臨時密碼當 `old`，傳入過期後的 `now` | 同一句；雜湊與 `temp_until` 不變 | 自動 |
| TC-038 | T10 | 例外 | monkeypatch `password_matches` 計次 | `old` 為 1001 字元 | 同一句；`password_matches` 一次都沒被呼叫（過長的不做雜湊） | 自動 |
| TC-039 | T11；作法 7① | 例外 | `new` 為 7 字元且 `new == old` | 呼叫 | 訊息為 `the password must be at least 8 characters (密碼至少 8 個字元)`（長度檢查先於「不能一樣」） | 自動 |
| TC-040 | T11；作法 7① | 例外 | `new` 為 1001 字元 | 呼叫 | 訊息為 `the password must be at most 1000 characters (密碼最多 1000 個字元)` | 自動 |
| TC-041 | 作法 7①「new 不是字串」 | 例外 | `new` 為 None（或數字） | 呼叫 | 訊息為「至少 8 個字元」那句，不丟其他例外 | 自動 |
| TC-042 | T11；作法 7② | 例外 | `new == old`，長度合法，`old` 正確 | 呼叫 | 訊息為 `the new password must differ from the current one (新密碼不能跟目前的一樣)` | 自動 |
| TC-043 | T11；作法 7 | 例外 | `new == old`，長度合法，但 `old` 其實是錯的 | 呼叫 | 仍是「must differ」那句（此檢查先於驗證舊密碼） | 自動 |
| TC-044 | T12 | 功能 | `new` 剛好 8 字元 | 呼叫 | 成功 | 自動 |
| TC-045 | T12 | 功能 | `new` 剛好 1000 字元 | 呼叫 | 成功 | 自動 |
| TC-046 | T13；作法 7；裁決三 12 | 例外 | monkeypatch `store.password_matches`，讓它在回傳前呼叫 `set_web_password` 改掉密碼 | `change_web_password` | 丟 `ValueError`，訊息含 `changed meanwhile`（`the password was changed meanwhile, log in again (密碼剛被改過，請重新登入)`）；`password_hash` 是 `set_web_password` 設的那個，不是本次的新密碼 | 自動 |
| TC-047 | T14；作法 7 | 功能 | bob 持有一般密碼 | `change_web_password` 改密碼 | 成功，`temp_until` 仍是 NULL | 自動 |
| TC-048 | 作法 7；專長守則（錯誤訊息） | 例外 | 觸發 TC-034、TC-035、TC-039、TC-040、TC-042、TC-046 的每一個錯誤 | 讀例外訊息 | 每則都是單行、同時含英文與中文、不含 `old` 也不含 `new` 的內容 | 自動 |

## US5 — 舊資料庫升級（migration）（優先度 P1）

專長守則：資料結構有變動，必須附 migration 並有可套用的測試。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | T15；作法 2 | 功能 | 手動建的舊 tokens.db：`users` 只有 `id,name,lab,created_at,disabled_at`，`users` 與 `web_sessions` 各一列（做法比照 `test_pat.py:237-251`） | `store.connect_tokens(path).close()` | `users` 多了最後一欄 `temp_until`，型別 REAL；舊列內容不變、`temp_until` 為 NULL；`web_sessions` 那一列還在 | 自動 |
| TC-050 | T15 | 功能 | 已升級一次的庫 | 再開一次 | 整個資料庫逐列傾印與第一次升級後完全相同（重複升級不改任何東西） | 自動 |
| TC-051 | T15；作法 2 | 功能 | 一個舊庫 | 四個執行緒同時開啟升級（仿 `test_cloud_cost.py` 的 `test_two_processes_upgrading_at_once_do_not_fail`） | 沒有任何例外，最後只有一欄 `temp_until` | 自動 |
| TC-052 | T16 | 功能 | 只有 `password_hash`、沒有 `temp_until` 的庫（上一版升過的） | 開啟 | 升級成功，`temp_until` 為最後一欄 | 自動 |
| TC-053 | T16 | 功能 | 一個全新庫與一個升級庫 | 比較 `PRAGMA table_info(users)` | 兩者完全相同 | 自動 |
| TC-054 | T17；作法 1 | 功能 | 升級後的舊庫 | 呼叫 `test_station_envs.banned_schema_words(tokens_db)` 並檢查 `test_station_envs.EXEMPT` | 結果為空清單；`EXEMPT` 沒有被改動 | 自動 |
| TC-055 | T18 | 功能 | 升級後的舊庫，ann 在其中 | 跑完整流程：`issue_temporary_password` → 登入 → `change_web_password` → 新密碼登入 | 每一步都成功 | 自動 |
| TC-056 | 裁決二 7、裁決三 15 | 功能 | 測試自己用舊版 `CREATE TABLE users`（沒有 `temp_until`）建庫，放一筆有密碼的使用者；用平台開 tokens.db 的正常入口（executor 在測試註明用哪個函式名）開啟 | 開啟後檢查 | `PRAGMA integrity_check` 為 ok；原本的密碼仍能登入且 `must_change` 為 False；`temp_until` 為 NULL | 自動 |
| TC-057 | 作法 2「不動 `web_sessions`」 | 功能 | 升級前後各讀一次 | 比較 `web_sessions` 欄位 | 欄位集合與升級前完全相同（`test_human_channel.py` 釘住的欄位仍成立） | 自動 |

## US6 — 終端機指令 `abf-platform user passwd <name> --temporary`（優先度 P1）

維護者原話：「照你建議」；既有裁示（`docs/PLATFORM.md`、ADR 0006）：「按的必須是我本人、AI 不能代按」→ 臨時密碼只能在真實終端機產生與顯示。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 | T19；作法 8 | 功能 | 有使用者 ann；用 `Pty(cli_argv("user","passwd","ann","--temporary"))` 跑在真終端機 | 執行並等它結束 | 結束碼 0；螢幕上密碼恰好出現一次 | 自動 |
| TC-059 | T19；作法 8 | 功能 | 同上 | 用 `splitlines()` 取輸出 | 輸出恰好四行（不計行尾空白）；第 2 行只有密碼本身，長度 16 且符合字元集 `A-Za-z0-9_-` | 自動 |
| TC-060 | 作法 8（輸出恰好四行） | 功能 | 同上 | 讀第 1、3、4 行 | 第 1 行為 `temporary web password of ann (一次性臨時密碼，只顯示這一次):`；第 3 行含 `Send it to ann privately` 與 `72 hours` 與 `must change it at the first login`；第 4 行含 `Shown once and kept nowhere` 與「弄丟就重新執行這個指令」 | 自動 |
| TC-061 | T19；作法 8「不呼叫 getpass、不提示輸入」 | 功能 | 同上 | 看螢幕 | 沒有出現 `New web password`，也沒有 `Type it again` | 自動 |
| TC-062 | T19；作法 8；「第一次網頁登入必須改」 | 功能 | 同上，取得螢幕上的密碼 | 用該密碼 `w.login`；查 `check_web_password`；讀 `users.temp_until` | 登入回 303；`must_change` 為 True；`temp_until` 約為現在時間加 259200 秒（容許數十秒誤差） | 自動 |
| TC-063 | T20；作法 8；ADR 0006 | 例外 | 有使用者 ann | 用 `subprocess.run([... "user","passwd","ann","--temporary"], input="\n", capture_output=True)`（非終端機，等同 AI 用管道呼叫） | 結束碼不為 0；輸出含 `rejected:` 與「終端機」；`hashes(w)` 與執行前相同；ann 的 `temp_until` 仍為 NULL | 自動 |
| TC-064 | T20；憲法 5.0.0「AI 不能代按」 | 例外 | 同 TC-063 | 讀非終端機呼叫的 stdout 與 stderr | 沒有出現成功格式的輸出（沒有 `temporary web password of`，沒有 `Shown once`） | 自動 |
| TC-065 | 作法 8（順序：終端機檢查在前） | 例外 | 沒有使用者 ghost | 以非終端機方式對 ghost 執行 `--temporary` | 結束碼不為 0；訊息是「終端機」那句，不是「沒有這個使用者」那句；資料庫不變 | 自動 |
| TC-066 | T21；作法 8 | 例外 | 沒有使用者 ghost；Pty 真終端機 | `user passwd ghost --temporary` | 結束碼不為 0；螢幕含「沒有這個使用者」與 `abf-platform user add` 的提示；螢幕上沒有任何密碼 | 自動 |
| TC-067 | T21 | 例外 | 同 TC-066 | 檢查資料庫 | `users` 表仍是空的 | 自動 |
| TC-068 | 裁決三 14；T20 外洩檢查 | 功能 | TC-058 的 Pty 執行，從 stdout 第 2 行取出密碼 | 檢查 stdout 其餘三行 | 密碼不在其餘三行 | 自動 |
| TC-069 | 裁決三 14 | 功能 | 同上，stderr 另行擷取 | 檢查 stderr | stderr 不含該密碼 | 自動 |
| TC-070 | 裁決三 14；專長守則（密碼不得出現在回應） | 功能 | 同上 | 掃 `tokens.db` 每個表的每個文字欄位 | 沒有任何欄位含該密碼（只有雜湊） | 自動 |
| TC-071 | 裁決三 14 | 功能 | 同上 | 用 `rglob` 讀測試資料夾底下每個檔案的位元組 | 沒有任何檔案含該密碼 | 自動 |
| TC-072 | T23；作法 8 | 例外 | 有使用者 ann | `["user","passwd","ann","--temporary","--password","x"]` | argparse 拒絕，結束碼不為 0，沒有改任何密碼 | 自動 |
| TC-073 | T23 | 例外 | 同上 | `["user","passwd","ann","--temporary","x"]` | argparse 拒絕，結束碼不為 0，沒有改任何密碼 | 自動 |
| TC-074 | 作法 8（`allow_abbrev=False`） | 例外 | 同上 | `["user","passwd","ann","--temp"]`（旗標縮寫） | 被拒絕，結束碼不為 0；沒有發出臨時密碼 | 自動 |
| TC-075 | T23 | 功能 | 環境變數 `ABF_WEB_PASSWORD` 設成某個值 V；Pty 真終端機 | 執行 `--temporary` | 螢幕第 2 行是 16 字元的隨機密碼，不等於 V | 自動 |
| TC-076 | T24；作法 8「一字不改」 | 功能 | 有使用者 ann；Pty | 不帶 `--temporary` 跑 `user passwd ann`（用 `set_by_terminal`） | 仍然問兩次密碼（`New web password for ann:` 與 `Type it again:`），仍能設成功 | 自動 |
| TC-077 | T24；作法 4 | 功能 | ann 持有臨時密碼 | 不帶旗標用終端機設一個新密碼 | `must_change` 為 False，`temp_until` 為 NULL | 自動 |
| TC-078 | T24；作法 8 | 功能 | 無 | 執行 `abf-platform user passwd --help` | 輸出含 `--temporary` | 自動 |

## US7 — 文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-079 | T25；作法 9 | 功能 | `docs/ONBOARDING.md` | 讀 §2 | 含單獨一行 `abf-platform user passwd <name> --temporary` | 自動：`platform/tests/test_onboarding_doc.py` |
| TC-080 | T25；作法 9 | 功能 | 同上 | 讀 §2 | 同節含 `72 hours`、`privately`、`change` | 自動 |
| TC-081 | T25；作法 9 | 功能 | 同上 | 搜全文 | 不存在 `still to be decided` | 自動 |
| TC-082 | T25；裁決三 13 | 功能 | 同上 | 跑 `test_tc006`、`test_tc010`、`test_tc018` | 原樣通過：§2 仍有單獨一行 `abf-platform user passwd <name>`、全節含 `twice`、`real terminal`、`no flag`（或 `no option`），`user passwd` 仍早於 `pat new`，一行一命令且沒有 `&&` 與 `;` | 自動 |
| TC-083 | 裁決二 9、裁決三 13 | 功能 | `docs/ONBOARDING.md`、`docs/PLATFORM.md` | 搜舊句 | 「no flag, no file, no variable can stand in for the keyboard」這句舊話在兩份文件裡都不再原樣出現（已改寫成與「no flag can type the person's own password; `--temporary` makes a one-time one」同義） | 自動 |
| TC-084 | T26 | 功能 | `test_onboarding_doc.py`、`cli.py` | 讀 `check_flags` 的旗標正則；讀 `cli.py` | 正則包含 `temporary`；`--temporary` 在 `cli.py` 是 `add_argument` | 自動 |
| TC-085 | T26（仿 `test_tc043`） | 例外 | 把 `--temporary` 改成 `--temporarily` 的 `cli.py` 複本 | 用 `check_flags` 檢查 | 回傳非空（抓得到文件與程式不一致） | 自動 |
| TC-086 | T27；作法 9 | 功能 | ONBOARDING §3 歡迎信 | 數 code fence、找字 | 仍恰好一個 code fence，內含 `temporary`、`PAT`、`password`、`NCHC` | 自動 |
| TC-087 | 作法 9 | 功能 | 同上 | 讀歡迎信裡原本「Claude Desktop: use your web password」那一行 | 改成兩種情況：同事在身邊（帶他在終端機設）；或「臨時密碼另外私下寄給你，第一次登入網頁必須改掉」（含 `separately` 與 `must change`） | 自動 |
| TC-088 | T27；`test_tc041` 風格 | 例外 | 同上 | 掃歡迎信 | 沒有任何 16 字元的類密碼字串、沒有範例密碼 | 自動 |
| TC-089 | T28；作法 9 | 功能 | `docs/OPERATIONS.md` | 讀指令表 | 含 `abf-platform user passwd <name> [--temporary]` | 自動 |
| TC-090 | 作法 9 | 功能 | 同上 | 讀該列說明 | 說明 `--temporary` 發一次性臨時密碼、顯示一次、72 小時（`72`）內有效 | 自動 |
| TC-091 | T28 | 功能 | `docs/PLATFORM.md` 登入說明段（Login） | 讀該段 | 含 `temporary` 與 `72 hours` | 自動 |
| TC-092 | 作法 9 | 功能 | 同上 | 讀該段 | 說明：用臨時密碼登入只能到改密碼頁、改完才算一般帳號、`web_session_user` 預設拒絕臨時密碼的 session | 自動 |
| TC-093 | 作法 9 | 功能 | 同上 | 讀該段 | 「一個新密碼或停用使用者會立刻結束 session」那句仍在、沒被改 | 自動 |
| TC-094 | 作法 8（docstring） | 功能 | `cli.py` 檔頭 | 讀第 2 行 | 為 `user add|cloud-cap|passwd [--temporary]` | 自動 |
| TC-095 | 裁決二 5 | 功能 | `cmd_user_passwd` | 讀 docstring | 含「no flag can type the person's own password」與「`--temporary` makes a one-time one」 | 自動 |
| TC-096 | T29 | 功能 | `test_onboarding_doc.py` | 跑 `test_tc035`、`test_tc036`、`test_tc042`、`test_tc043` | 原樣通過（子指令與旗標對照仍一致） | 自動 |

## US8 — 這次不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-097 | 不做 1；範圍「不准動」`web.py` | 不在範圍 | 網頁路由集合 | 跑 `test_owner_binding.py` 的路由集合與 `store.*` 名稱集合斷言；`git diff --stat -- platform/abf_platform/web.py` | 兩個集合不變、斷言不改就通過；`web.py` 零改動；沒有任何新路由或畫面（沒有「改密碼頁」，那是 `web-change-password` 的事） | 自動：`platform/tests/test_owner_binding.py`；另閱卷重跑 diff 指令（輸出貼 ledger） |
| TC-098 | 不做 2 | 不在範圍 | MCP 工具清單 | 列舉工具；跑 `test_actions_layer.py`、`test_human_channel.py`、`test_web_parity.py` | 工具數仍為 14、沒有新工具、沒有名稱含 `passwd` 或 `login` 的工具；`actions/`、`guidance.py`、`mcp_server.py` 零改動 | 自動：上列既有測試；另閱卷重跑 `git diff --name-only` |
| TC-099 | 不做 3；裁決 3 | 不在範圍 | 已對 ann 發過臨時密碼 | 找任何能再把它顯示出來的路徑：`store` 的函式、CLI 子指令；再執行一次 `--temporary` | 沒有任何函式或指令回傳既有的臨時密碼（資料庫只有雜湊）；重新執行得到的是另一組新密碼，舊的作廢（弄丟只能重發） | 自動 |
| TC-100 | 不做 4 | 不在範圍 | `cli.py`、`store.py` 原始碼 | 檢查匯入與呼叫 | 沒有匯入或使用 `smtplib`、`email`、`subprocess` 等寄信或啟動其他程式的機制；指令只在終端機顯示 | 自動 |
| TC-101 | 不做 5 | 不在範圍 | `abf-platform --help` 與路由 | 列出所有子指令與路由；跑 `test_oauth_mcp.py` 的 `forgot`／`reset` 檢查 | 沒有新增任何忘記密碼或重設密碼的入口（忘了就找管理者重發）；既有檢查原樣通過 | 自動 |
| TC-102 | 不做 6；範圍清單（以裁決三 16 的 8 個檔為準） | 不在範圍 | 本任務 diff | `git diff --name-only <base>...HEAD` | 只有 `store.py`、`cli.py`、`test_temp_password.py`、`test_onboarding_doc.py`、`docs/ONBOARDING.md`、`docs/OPERATIONS.md`、`docs/PLATFORM.md`、`specs/temp-password/ledger.md`，以及（裁決四追認）`platform/tests/test_pat.py`、`platform/tests/test_web_actions.py` 各只在 users 欄位清單加 `temp_until`；憲法、`docs/adr/0006-…md`、`docs/INSTALL.md`、`docs/TESTING.md` 都沒動 | 自動：executor 把指令輸出貼進 ledger，閱卷重跑 |
| TC-103 | 不做 7 | 不在範圍 | `store.py` | 檢查 `MIN_PASSWORD_CHARS`、`MAX_PASSWORD_CHARS`、`hash_password`、`password_matches` | 長度規則仍是 8 到 1000；`hash_password` 與 `password_matches` 沒有任何改動（仍是 scrypt、參數不變） | 自動：`store.MIN_PASSWORD_CHARS==8`、`MAX_PASSWORD_CHARS==1000` 的斷言；另閱卷看 diff |
| TC-104 | 作法 8「不帶 --temporary 的行為一字不改」；完成標準 | 不在範圍 | `cmd_user_passwd` | 看 diff | 不帶 `--temporary` 的路徑（終端機檢查、使用者檢查、兩次 `getpass`、不一致與例外訊息、成功訊息）程式碼零改動；只有 docstring 與新增的 `--temporary` 分支不同 | 自動：TC-076、TC-077 為行為證據；另閱卷看 diff |

## US9 — 既有行為不變（改動最容易碰到的既有檢查）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-105 | 「既有測試的影響」 | 功能 | 既有一般流程 | 跑 `test_web_login.py` 的 `test_tcb01`～`tcb07`、`tcb23`、`tcb26` | 不改測試就通過（一般流程、`set_web_password` 刪 session、雙語長度訊息） | 自動：`platform/tests/test_web_login.py` |
| TC-106 | 作法 5 | 功能 | 三參數替身 | 跑 `test_review_fixes.py:154-179`、`test_review_fixes_2.py:117-146` | 不改測試就通過 | 自動 |
| TC-107 | 「既有測試的影響」 | 功能 | `web.py`、`oauth.py` 原始碼 | 跑 `test_oauth_mcp.py` 的 `forgot`／`reset_password` 與 `/account` 為 404、無 `passwd` 路由檢查 | 不改測試就通過 | 自動 |
| TC-108 | 作法 1、2 | 功能 | 資料庫結構釘住的測試 | 跑 `test_human_channel.py` 的 `web_sessions` 欄位與 `EXEMPT` 恰好六項檢查；`test_station_envs.py` 的 `banned_schema_words` | 不改測試就通過 | 自動 |
| TC-109 | 「動作層／parity」 | 功能 | 工具清單 | 跑 `test_actions_layer.py`（工具名不得符合 `passwd` 或 `login`）、`test_human_channel.py`、`test_web_parity.py` | 不改測試就通過，工具數仍為 14 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110 | 憑證規則（密碼不得出現在日誌或任何回應）；專長守則 | 例外 | `caplog` 設成 DEBUG（全等級）；同程序呼叫 store | 呼叫 `issue_temporary_password`，包含不存在使用者的失敗情況 | 日誌紀錄與例外訊息都不含任何密碼（臨時密碼只在回傳值裡） | 自動 |
| TC-111 | 同上 | 例外 | `caplog` 設成 DEBUG | 呼叫 `check_web_password`、`change_web_password`（成功與各種失敗） | 日誌紀錄與例外訊息都不含 `old`、`new` 或臨時密碼 | 自動 |
| TC-112 | 原則 I.2 與 Safety Net 的「送出必須經人確認」 | 功能 | 既有「未經確認不得送出」測試 | 跑 `test_human_channel.py` 的 `test_tch09_*`、`test_confirm_page.py` 的 `test_tch09_b_c_*`，加上 TC-026 | 都通過：未確認的 launch 仍被 MCP 與網頁路由拒絕；臨時密碼的 session 按不了送出 | 自動 |
| TC-113 | 原則 I.1（新檔要寫出為什麼自己做） | 功能 | `platform/tests/test_temp_password.py` | 跑 `test_scope.py`（約第 76 行的檢查） | 新檔檔首有 `# Nothing existing: …` 且說明至少 15 字，檢查通過 | 自動：`platform/tests/test_scope.py` |
| TC-114 | 文件儲存表與常數對得上 | 功能 | `docs/PLATFORM.md` 儲存表 | 跑 `bash tests/platform_storage_doc_test.sh` | 通過：文件寫的「72 hours」對得上 `TEMP_PASSWORD_SECONDS = 72 * 3600`；`users` 表那一列沒改 | 自動：`tests/platform_storage_doc_test.sh` |
| TC-115 | Safety Net：憑證不進 git、不被印出 | 功能 | 本任務全部變動檔案 | 跑 `bash tests/credentials_stay_in_settings_test.sh` | 通過；程式碼與文件裡沒有範例密碼或 token 形狀的字串 | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-116 | 原則 II.3（不寫死個人路徑） | 功能 | 同上 | 跑 `bash tests/no_hardcoded_paths.sh` | 通過 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-117 | 裁決二 11 | 功能 | 同上 | 跑 `bash tests/no_per_pipeline_config.sh` | 通過（本任務不碰 configs） | 自動：`tests/no_per_pipeline_config.sh` |
| TC-118 | 原則 II.4；裁決二 11 | 功能 | 同上 | 跑 `bash tests/command_layer_is_site_neutral.sh` | 通過（本任務不碰指令層） | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-119 | 平台原始碼不得啟動其他程式（TC-071，`test_scope.py:99`） | 功能 | `platform/abf_platform/*.py` | 跑 `test_scope.py` 該檢查 | 通過：本任務沒有新增 subprocess 之類的啟動 | 自動：`platform/tests/test_scope.py` |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
