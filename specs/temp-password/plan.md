---
id: temp-password
title: 管理者發一次性臨時密碼：`user passwd <name> --temporary`（後端：資料庫欄位、產生與驗證、改密碼函式、文件），網頁改密碼頁由 web-change-password 做
tier: B
kinds: backend
lane: L-account
after: 
base: v3（`origin/v3` @ 6dc879a；所有行號都是該版本）
source: developer-agent 讀碼查證（2026-10-25）；維護者 10-25「照你建議」（遠端同事無法在平台主機的終端機自己打密碼）
---

# temp-password

> 本檔由 developer-agent 起草（2026-10-25）。**只做後端與文件**：網頁的「改密碼」路由與畫面、登入頁導向，由前端任務 `web-change-password`（`after: temp-password`）做；本檔「前端合約」一節就是交給它的介面。B 級（後端行為改變）；但**憲法與 ADR 的字句要維護者點頭**（見裁決 1），不在本任務內改。
> **名詞**：「臨時密碼」＝管理者在平台主機終端機產生、只顯示一次、72 小時內有效、第一次登入就必須改掉的密碼。「must_change」＝這個使用者目前持有的是臨時密碼（資料庫欄位 `users.temp_until` 不是空值）。

## 目標
管理者在平台主機的終端機執行 `abf-platform user passwd <name> --temporary`，得到一組隨機臨時密碼（只顯示一次、私下交給本人）；本人用它登入網頁後，除了「改密碼」之外什麼都不能做，改完才是正常帳號。對使用者的意義：遠端同事（`cli.py:148-177` 現在要求本人在平台主機的真實終端機自己打密碼）不必碰平台主機也能有自己的網頁密碼；管理者從頭到尾不知道最終密碼。

## 維護者原話（verifier 出題用）
- 「照你建議」（2026-10-25，針對：管理者發一次性臨時密碼，本人第一次網頁登入必須改掉）→ T1～T9、T19～T24。
- 「一次性」→ 臨時密碼只顯示一次（T19）、改過一次後不再是臨時（T9）、過期作廢（T5）。
- 「第一次網頁登入必須改」→ 用臨時密碼登入的 session 預設什麼都不能做（T7）。
- 既有裁示（`docs/PLATFORM.md:495`、`ADR 0006` :108）：「按的必須是我本人、AI 不能代按」→ 臨時密碼只能在真實終端機產生與顯示，AI 用管道或子行程呼叫拿不到（T20）。
- `CLAUDE.md` 專長守則：「密碼不得出現在日誌或任何回應中」→ 唯一例外是這一次性的終端機輸出（裁決 3），其餘處處不得出現（T2、T22）。

## 範圍：檔案（共 9 個含 ledger）
- `platform/abf_platform/store.py`
  - `TOKEN_SCHEMA` 的 `users` 表（:100-107）最後加 `temp_until REAL`；`_migrate_tokens`（:739-745 處理 `password_hash` 的那一段旁）加同型 migration。
  - 常數 `TEMP_PASSWORD_SECONDS = 72 * 3600`（寫成這個樣子：`tests/platform_storage_doc_test.sh:101-103` 的正則只認 `NAME = 數字*數字` 的常數，文件寫的「72 hours」要對得上它）。
  - 新增 `issue_temporary_password`、`change_web_password`；改 `set_web_password`（:1109）、`check_web_password`（:1129）、`web_session_user`（:1161）。
- `platform/abf_platform/cli.py`：`cmd_user_passwd`（:148）加 `--temporary` 分支；`passwd` 子指令（:574-577）加旗標與說明；檔頭 docstring 第 2 行 `user add|cloud-cap|passwd` 改為 `user add|cloud-cap|passwd [--temporary]`（`git grep` 沒有任何測試釘這行，改了不會紅）。
- `platform/tests/test_temp_password.py`（新；檔首 `# Nothing existing: …` ≥15 字，`test_scope.py:76` 檢查）。
- `platform/tests/test_onboarding_doc.py`：新增文件測試；`check_flags`（:51）的旗標正則加 `temporary`（有意更新）。
- `docs/ONBOARDING.md`：§2 第 2 步與 §3 歡迎信（細節在「作法」）。
- `docs/OPERATIONS.md`：:117 的指令表那一列。
- `docs/PLATFORM.md`：:495 那一段（登入說明）與 :632-634 的儲存表**不改列、只在 :495 加句**（見作法 9）。
- `specs/temp-password/ledger.md`
- **不准動**：`platform/abf_platform/web.py`（前端任務的）、`actions/`、`mcp_server.py`、`oauth.py`、`.specify/memory/constitution.md`、`docs/adr/0006-…md`（憲法與 ADR 不在實作時改，見裁決 1）、`docs/INSTALL.md`、`docs/TESTING.md`（本任務沒有手動驗收，見「完成標準」）。

## 作法
**1. 資料庫（決定：單一欄位 `temp_until`，不用 `must_change` 旗標）。** `users.temp_until REAL`，可空。空＝一般密碼；有值＝目前密碼是臨時的，且到這個時間（epoch 秒）作廢。理由：一個欄位同時表達「必須改」與「期限」，不會出現「旗標開著但沒有期限」的狀態；忘了拿去用的臨時密碼自動失效，不會變成長期有效的弱憑證（證據：`web_sessions` 也是以 `expires_at` 管期限，:108-113）。**欄名不得含** `user／role／org／team／member／login／password／email／session／cookie`（`test_station_envs.py:531` 的 `banned_schema_words` 會把它抓出來；`test_human_channel.py:593` 還釘著 EXEMPT 清單恰好六項，不准加）。`temp_until` 不含這些字。
**2. 舊庫升級（需要 migration）。** 完全仿 `password_hash` 那段（store.py:739-745）：`PRAGMA table_info(users)` 沒有 `temp_until` 才 `ALTER TABLE users ADD COLUMN temp_until REAL`，另一個行程先加了就不報錯（`sqlite3.OperationalError` 再查一次欄位，仍沒有才 raise）。舊列全部是 NULL＝一般密碼，行為不變。放在 `_migrate_tokens(con)` 裡、`password_hash` 那段之後。**不重建表、不動 `web_sessions`**（它的欄位被 `test_human_channel.py:605-609` 釘死）。
**3. `issue_temporary_password(tokens_path, name, now=None)`**（定案）：
   - 回傳 `{"password": <16 字元>, "expires_at": <float>}`。密碼＝`secrets.token_urlsafe(12)`（剛好 16 個字元，字元集 `A-Za-z0-9_-`，遠大於 `MIN_PASSWORD_CHARS = 8`，store.py:157）。`now=None` 時用 `time.time()`；`expires_at = now + TEMP_PASSWORD_SECONDS`。
   - 同一個交易內：`password_hash = hash_password(password)`、`temp_until = expires_at`、`DELETE FROM web_sessions WHERE user_id = ?`（與 `set_web_password` :1122-1124 同型）。再發一次＝覆蓋前一組。
   - 不存在的使用者：`ValueError("no such user: %s (沒有這個使用者)" % name)`（與 :1120 同句），資料庫完全不變。
   - 密碼只存在回傳值裡；不寫日誌、不寫檔、不進例外訊息。
**4. `set_web_password`**（:1109）：同一個 UPDATE 把 `temp_until` 設回 NULL（終端機正常設的密碼不是臨時的）。長度檢查（:1112-1115）抽成私有 `_check_password_length(password)` 給 `change_web_password` 共用，**錯誤訊息字句不變**（`test_web_login.py` 與 `test_review_fixes.py:173-179` 依賴）。
**5. `check_web_password(tokens_path, name, password, now=None)`** → `{"user_id", "name", "lab", "must_change": bool}` 或 `None`。`must_change = temp_until IS NOT NULL`。臨時密碼過期（`now > temp_until`）→ `None`，**和密碼錯誤一樣的耗時**（照現有做法：先對 `stored` 或 `dummy` 雜湊比對，最後才判斷期限，:1129-1145）。簽章加的是最後一個關鍵字參數，`web.py:251` 現在的三個位置參數呼叫與 `test_review_fixes.py:158-168`、`test_review_fixes_2.py:124-129` 的三參數替身都不受影響。
**6. `web_session_user(tokens_path, sid, now, allow_must_change=False)`** → `{"user_id", "name", "lab", "must_change": bool}` 或 `None`。**預設（fail-closed）**：該使用者 `temp_until` 有值時回 `None`——所以目前 `web.py` 所有 `user_of` 的路由（:322、334、406、428、484、565、615、673、685，含 OAuth 的 `/authorize`）對臨時密碼的 session 一律當成沒登入，前端就算漏掉某條路由也按不了「送出」。只有改密碼頁傳 `allow_must_change=True` 才拿得到（此時 `must_change` 為 True）。臨時密碼已過期的使用者即使 `allow_must_change=True` 也回 `None`。一般使用者兩種呼叫都回 `must_change: False`。
**7. `change_web_password(tokens_path, name, old, new, keep_sid=None, now=None)`**（定案；放 store 層，不放動作層——證據見裁決 2）：
   - 成功回傳 `{"user_id", "name", "lab"}`；失敗一律 `ValueError`，訊息雙語、單行、不含任何密碼（與 `set_web_password` 同風格）。
   - **檢查順序固定**（測試依序）：① `new` 不是字串或短於 8 → `"the password must be at least 8 characters (密碼至少 8 個字元)"`；長於 1000 → `"the password must be at most 1000 characters (密碼最多 1000 個字元)"`（兩句與 :1113、:1115 逐字相同）；② `new == old` → `"the new password must differ from the current one (新密碼不能跟目前的一樣)"`；③ 驗證 `old`：用 `check_web_password(tokens_path, name, old, now)`，`None`（密碼錯、使用者不存在、已停用、臨時密碼過期、`old` 長於 1000 字元都算）→ `"the current password is wrong (目前的密碼不對)"`（同一句，不洩漏是哪一種）；`old` 長於 1000 字元不做雜湊，直接這句。
   - 驗證通過後，在同一個交易內 `UPDATE users SET password_hash = ?, temp_until = NULL WHERE id = ? AND password_hash = <驗證時讀到的那個雜湊>`；`rowcount == 0`（驗證到更新之間密碼被別人改了）→ `ValueError("the password was changed meanwhile, log in again (密碼剛被改過，請重新登入)")`，什麼都不改。
   - 同交易：`DELETE FROM web_sessions WHERE user_id = ?`，**但保留** `id_hash = _hash(keep_sid)` 那一筆（`keep_sid` 是呼叫者目前 cookie 裡的 session id；`None` 則全刪，與 `set_web_password` 相同）。
   - 臨時與一般使用者都可呼叫（一般使用者之後想自己改密碼也走同一個函式）。
**8. CLI：`abf-platform user passwd <name> --temporary`**（`add_argument("--temporary", action="store_true")`；`allow_abbrev=False` 已設，:575）：
   - **仍然必須是真實終端機**（決定）：沿用 `terminal.terminal_problem()`（`cli.py:152-155`）。理由：臨時密碼會印在螢幕上，若不限終端機，AI 用 Bash 工具呼叫 `abf-platform user passwd x --temporary` 就拿到輸出、可以登入網頁替本人按「送出」——正是 `docs/adr/0006…:104-110` 當初為什麼規定密碼只能在真實終端機設的原因。「密碼是輸出不是輸入，不會進 shell 歷史」只解決歷史紀錄，不解決 AI 呼叫。不通過時：`rejected: 臨時密碼只能顯示在真正的終端機上，這裡不行（%s）(a temporary password is shown only at a real terminal, never to a pipe or a script)`，exit 1，資料庫不變。
   - 順序：終端機檢查 → 使用者存在（`store.user_id_of`，:157 同款訊息 `rejected: 沒有這個使用者 (no such user): %s; add one with: abf-platform user add`）→ `issue_temporary_password` → 輸出。**不呼叫 `getpass`、不提示輸入。**
   - 輸出（走 `_say`，標準輸出，**恰好這四行**，第 2 行只有密碼本身，方便測試擷取）：
     ```
     temporary web password of <name> (一次性臨時密碼，只顯示這一次):
     <16 字元密碼>
     Send it to <name> privately, not in a chat with an AI. It works for 72 hours, and <name> must change it at the first login (請私下交給本人；72 小時內有效，第一次登入必須改掉).
     Shown once and kept nowhere: if it is lost, run this command again (只顯示這一次、不留任何紀錄，弄丟就重新執行這個指令).
     ```
     「72」由 `TEMP_PASSWORD_SECONDS` 算出，不手寫兩次。每個登入中的瀏覽器 session 同時結束，不另印（文案已在第 3 行之後的行為裡；不需要多一行）。
   - 不寫日誌、不寫檔；沒有新增任何 `logging` 呼叫。
   - 不帶 `--temporary` 的行為**一字不改**（兩次輸入、`getpass`、:148-177 全部原樣）。
**9. 文件**（全英文為主，每節開頭中文要點的慣例照舊）：
   - `docs/ONBOARDING.md` §2 第 2 步（現 :37-43）：保留原本的 `abf-platform user passwd <name>` 區塊與其說明句（`test_tc010` 要求 `^abf-platform user passwd <name>\s*$` 單獨一行、全節含 `twice`、`real terminal`、`no flag`/`no option`），**刪掉**句末 `(How a remote colleague should set it is still to be decided by the maintainer.)`，改成「遠端同事（沒有平台主機 shell）」一段，含另一個單獨一行的區塊 `abf-platform user passwd <name> --temporary`，說明：顯示一次、私下交給本人（不要貼進與 AI 的對話）、72 hours 內有效、本人第一次網頁登入會被要求改密碼、忘了就重發。`user passwd` 在 §2 第一次出現的位置仍要早於 `pat new`（`test_tc006` 用 `find` 比位置）。
   - `docs/ONBOARDING.md` §3 歡迎信（仍恰好一個 code fence，`test_tc019`）：「Claude Desktop: use your web password (set with me)」那行（現 :89）改成兩種情況：同事在你身邊（你帶他在終端機設）或「I send you a temporary password separately; the first time you log in to the web page you must change it」。保留 `PAT`、`password`、`NCHC` 三個詞（`test_tc021`），不放任何範例密碼（`test_tc041`）。
   - `docs/OPERATIONS.md` :117：指令表那列改為 `abf-platform user passwd <name> [--temporary]`，說明加「`--temporary` 發一次性臨時密碼，顯示一次，72 小時內有效」。
   - `docs/PLATFORM.md` :495（Login 段）：現句「The password is set by the person with `abf-platform user passwd <name>`, typed twice on a real terminal (no flag, no file, no variable can stand in for the keyboard)」**保留**（它對一般流程仍真），其後加一句：臨時密碼的存在、72 hours、用它登入只能到改密碼頁、改完才算一般帳號、`web_session_user` 預設拒絕臨時密碼的 session。「一個新密碼或停用使用者會立刻結束 session」那句不動。
   - `docs/PLATFORM.md:632` 的儲存表列（`users` 在 `tokens.db`）**不改**：它寫的是「scrypt hashes of web passwords」，新欄位 `temp_until` 只是期限，仍符合；`tests/platform_storage_doc_test.sh` 不需要動。executor 跑該腳本確認仍綠（見失敗先行測試 T30）。
**10. 前端合約**（給 `web-change-password`；本任務不實作，但函式簽章在此釘死）：
   - **登入**（`web.py:251` 附近）：`who = store.check_web_password(...)` 之後，`who["must_change"]` 為 True → 照常 `create_web_session`，但回 303 到改密碼頁（忽略 `next`），不是 `HOME`。
   - **每一條需要登入的路由**：不用改——`store.web_session_user(...)` 預設對臨時密碼 session 回 `None`，等於沒登入。**只有改密碼頁**呼叫 `store.web_session_user(tokens_path, sid, now, allow_must_change=True)`（需要 `must_change` 時看回傳的 `must_change`）。
   - **改密碼 POST**：呼叫 `store.change_web_password(tokens_path, name, old, new, keep_sid=<cookie 的 sid>)`；`ValueError` 的訊息可直接顯示給本人（已雙語、無密碼）。成功後 303 到首頁，**同一個 cookie 繼續有效**（`keep_sid`），不必重新登入。
   - **防猜**：改密碼頁要驗 `old`，所以必須沿用登入頁的失敗計數（`by_name`／`by_ip`，`web.py:240-262`）；`old` 超過 `store.MAX_PASSWORD_CHARS` 的處理比照登入頁的 `too_long`。CSRF 比照 `logout_post`（`web.py:269-276`）的做法。
   - **路由名稱限制**（既有測試釘的，前端任務要有意更新它們並在 PR 說明）：路徑不得含 `reset|forgot|passwd|password`，且 `/account` 必須維持 404（`test_oauth_mcp.py:402-407`，`test_tch05`）；路由集合（`test_owner_binding.py:817-823`）與 `web.py` 用到的 `store.*` 名稱集合（:826-828）都是**逐項相等**的斷言，加一個就得改一次；`store.change_web_password` 要加進那個集合。
   - **登出**不需要改：`logout_post` 只用 `session_id`，不經 `user_of`（:269-276），臨時密碼的 session 也能登出。

## 失敗先行測試（現在全紅；新檔 `platform/tests/test_temp_password.py`，另有文件測試加在 `test_onboarding_doc.py`）
store 層（用 `human_harness.World` 的 `w`，`w.ip.tokens` 是 tokens.db；時間一律傳 `now`）：
- **T1** `issue_temporary_password(tokens, "ann", now=1000.0)` 回 `{"password","expires_at"}`；`len(password)==16`、`re.fullmatch(r"[A-Za-z0-9_-]{16}", …)`；`expires_at == 1000.0 + 259200`；`store.TEMP_PASSWORD_SECONDS == 72*3600`。
- **T2** 連發兩次密碼不同；`users.password_hash` 符合 `scrypt$…` 格式；`password.encode()` 不在 `data_bytes(w)`（`test_web_login.py:51-55` 的 helper 掃整個資料夾）。
- **T3** 發臨時密碼同時刪掉該使用者所有 `web_sessions`、不動別人的；不存在的使用者 → `ValueError` 含「沒有這個使用者」且 users 表列數不變。
- **T4** 用臨時密碼 `check_web_password(...)` → `{"user_id","name","lab","must_change": True}`；一般密碼的使用者 → `must_change: False`；錯密碼、停用使用者 → `None`。
- **T5** 期限：`now=expires_at-1` 通過；`now=expires_at+1` → `None`；過期與錯密碼都只呼叫一次 `password_matches`（monkeypatch 計次，證明耗時相同）。
- **T6** `set_web_password` 之後 `temp_until` 為 NULL、`must_change` 為 False。
- **T7** `web_session_user`：臨時密碼使用者的 session 預設 → `None`；`allow_must_change=True` → `{"must_change": True,…}`；一般使用者兩種呼叫都 `must_change: False`；臨時密碼過期後兩種呼叫都 `None`。
- **T8** 行為上的 fail-closed：用臨時密碼走 `w.login(client, "ann", <temp>)`（回 303），接著 `client.get("/")` 看到的是登入頁而不是看板；對一張該使用者的待確認申請 `POST /c/<rid>`（帶 csrf 也一樣）不是 200 且 `w.jobs() == []`。
- **T9** `change_web_password(tokens,"ann",temp,"a brand new passphrase", keep_sid=sid)` 回 `{"user_id","name","lab"}`；舊臨時密碼再登入 → `None`；新密碼 → `must_change: False`；`temp_until` 為 NULL；`keep_sid` 那筆 session 還在、其他全沒了；`keep_sid=None` 時全沒了。
- **T10** 錯誤 `old`、不存在的使用者、停用使用者、過期的臨時密碼、`old` 長 1001 字元：全部同一句 `the current password is wrong (目前的密碼不對)`；雜湊與 `temp_until` 不變；1001 字元那條不呼叫 `password_matches`。
- **T11** 檢查順序：`new` 7 字元＋`new==old` → 「至少 8」那句；`new` 1001 字元 → 「最多 1000」那句；`new==old`（長度合法）→ 「must differ」那句，且此時 `old` 即使是錯的也是這句（先於驗證）；三句與上文逐字相同。
- **T12** `new` 剛好 8 與剛好 1000 字元都成功。
- **T13** 驗證與更新之間密碼被改（monkeypatch `store.password_matches` 讓它在回傳前呼叫 `set_web_password`）→ `ValueError` 含 `changed meanwhile`，雜湊是 `set_web_password` 設的那個。
- **T14** 一般（非臨時）使用者也能 `change_web_password` 成功，且 `temp_until` 仍是 NULL。
migration：
- **T15** 舊 tokens.db（手動建只有 `id,name,lab,created_at,disabled_at` 的 `users` 表與 `web_sessions`，各一列；比照 `test_pat.py:237-251` 的做法）→ `store.connect_tokens(path).close()` 之後 `users` 多一欄 `temp_until`（最後一欄、`REAL`）、舊列內容不變且 `temp_until` 為 NULL、`web_sessions` 那列還在；再開一次，整個資料庫逐列傾印與第一次後完全相同；四個執行緒同時升級不丟例外（仿 `test_cloud_cost.py:716-730` 的 `test_two_processes_upgrading_at_once_do_not_fail`）。
- **T16** 只有 `password_hash` 沒有 `temp_until` 的舊庫（上一版剛升過的）也能升；全新庫與升級庫的 `PRAGMA table_info(users)` 完全相同。
- **T17** 升級後 `test_station_envs.banned_schema_words(tokens_db) == []`，且 `test_station_envs.EXEMPT` 沒被改（`test_human_channel.py:605-609` 仍綠）。
- **T18** 在升級後的舊庫上 `issue_temporary_password` 與 `change_web_password` 都能跑完整流程。
CLI（用 `launch_harness.Pty` 與 `cli_argv`，同 `test_web_login.py:24-31`）：
- **T19** `Pty(cli_argv("user","passwd","ann","--temporary"))` → 結束碼 0；螢幕上密碼**恰好出現一次**；用 `splitlines()` 取第 2 行，`len==16` 且符合字元集；沒有出現 `New web password`（沒有提示輸入）；該密碼可 `w.login` 成功（303）且 `check_web_password` 的 `must_change` 為 True。
- **T20** 非終端機（`subprocess.run([... "user","passwd","ann","--temporary"], input="\n", capture_output=True)`，仿 `test_web_login.py:80-84`）→ 結束碼不為 0、輸出含「終端機」、輸出沒有任何 16 字元的類密碼字串（`re.search(r"\b[A-Za-z0-9_-]{16}\b", out)` 為 None，但允許英文單字：用 `hashes(w)` 與 `temp_until` 為 NULL 為主斷言），`hashes(w)` 不變。
- **T21** 不存在的使用者（Pty）→ 結束碼不為 0、螢幕含「沒有這個使用者」、users 表仍是空的。
- **T22** 密碼不進任何其他地方：T19 結束後 `data_bytes(w)` 不含該密碼；`caplog` 為 DEBUG 時、`cli.py` 在整個執行中沒有把密碼送進 logging（以靜態檢查補：`cli.py` 原始碼不含 `logging`／`print(` 之外的輸出路徑，只有 `_say`；`store.py` 的 `issue_temporary_password` 不含 `import random`）。
- **T23** `--temporary` 不能被旗標、檔案、環境變數指定密碼：`["--temporary","--password","x"]`、`["--temporary","x"]` 都被 argparse 拒絕（結束碼不為 0）；`ABF_WEB_PASSWORD` 環境變數存在時輸出的仍是隨機密碼、不是該變數的值。
- **T24** 不帶 `--temporary` 的流程一字不變：`set_by_terminal(w,"ann",…)` 仍問兩次、仍能設；對一個持臨時密碼的使用者設完後 `must_change` 為 False（`temp_until` 為 NULL）；`abf-platform user passwd --help` 輸出含 `--temporary`。
文件：
- **T25**（`test_onboarding_doc.py`）§2 含單獨一行 `abf-platform user passwd <name> --temporary`；同節含 `72 hours`、`privately`、`change`；`still to be decided` 在全文中不存在；`test_tc006`、`test_tc010`、`test_tc018` 原樣通過。
- **T26** `check_flags` 的旗標正則包含 `temporary`，且 `--temporary` 在 `cli.py` 是 `add_argument`；用 `check_flags` 對「把 `--temporary` 改成 `--temporarily`」的複本回傳非空（仿 `test_tc043`）。
- **T27** §3 歡迎信仍恰好一個 code fence，內含 `temporary`、`PAT`、`password`、`NCHC`，且沒有 16 字元的類密碼字串（`test_tc041` 風格）。
- **T28** `docs/OPERATIONS.md` 含 `abf-platform user passwd <name> [--temporary]`；`docs/PLATFORM.md` 第 495 行附近含 `temporary` 與 `72 hours`。
- **T29** 子指令與旗標對照：`test_tc035`、`test_tc036`、`test_tc042`、`test_tc043` 原樣通過。
- **T30**（既有，不用新寫，列為必須綠）`bash tests/platform_storage_doc_test.sh`、`bash tests/credentials_stay_in_settings_test.sh`、`bash tests/no_hardcoded_paths.sh`。

### 既有測試與斷言的影響（逐條核對過）
- **預期因本任務變紅的既有斷言：沒有。** 原因逐項：`check_web_password`／`web_session_user` 的回傳只是多一個鍵，沒有任何測試做整個 dict 的相等比較（`git grep` 只有 `test_pat.py:502` 比 `lookup_pat`，是另一個函式）；`web.py` 不動，`test_owner_binding.py:817-828` 的路由與 `store.*` 名稱集合不變；`web_sessions` 欄位不動（`test_human_channel.py:605-609`）；`users` 新欄名通過 `banned_schema_words`（`test_station_envs.py:531`）；`SCHEMA_SHA256`（`test_http_site_samplesheet.py:543`）算的是 `platform.db`（`d.state`），不是 `tokens.db`；`test_web_board.py:900` 只搜 `stage` 這個字。
- **必須有意更新**：`test_onboarding_doc.py` 的 `check_flags`（:51）正則（T26）。
- **必須維持綠、改動文件時最容易碰到**：`test_onboarding_doc.py` 的 `test_tc006`（§2 命令順序）、`test_tc010`（:112-117）、`test_tc018`（一行一命令、不得有 `&&`／`;`）、`test_tc019`（§3 恰一個 fence）、`test_tc021`、`test_tc035`、`test_tc036`、`test_tc041`、`test_tc042`、`test_tc043`；`test_web_login.py` 的 `test_tcb01`～`tcb07`、`tcb23`、`tcb26`（一般流程、`set_web_password` 刪 session）；`test_review_fixes.py:154-179`、`test_review_fixes_2.py:117-146`（替身只收三個位置參數）；`test_oauth_mcp.py:393-407`（`web.py`／`oauth.py` 原始碼不得出現 `forgot`、`reset_password` 等字，且無 `passwd` 路由——本任務不動 `web.py` 所以不受影響，`cli.py` 不在該檢查名單內）；`test_actions_layer.py:622`、`test_human_channel.py:160`（工具名不得符合 `passwd|login`——本任務不新增 MCP 工具）。
- 動作層／parity：本任務**不新增 MCP 工具**，工具數仍 14（`docs/PLATFORM.md:357`），`guidance.py` 與 `test_web_parity.py` 不動。

## 完成標準（done when）
- 自動：T1～T29 綠；T30 三支檢查綠；全套綠（`tests/run_all.sh` 在 WSL）；`git diff --name-only` 只有「範圍：檔案」所列。
- 對一份**真實**舊 `tokens.db` 複本開啟一次：`SELECT * FROM users` 前後相同（多一欄 NULL）、`PRAGMA integrity_check` 為 ok（executor 拿不到就在 ledger 寫「由 developer-agent 在桌機補跑」，不算 UNVERIFIED）。
- 無手動驗收、`docs/TESTING.md` 不在範圍：本任務沒有畫面；端到端（臨時密碼登入→改密碼→進看板）的手動步驟由 `web-change-password` 放進 TESTING.md。
- 閱卷看 diff 的項目（依 dev-plans 通例）：改動範圍、`web.py` 零改動（`git diff --stat -- platform/abf_platform/web.py` 為空）、不帶 `--temporary` 的 `cmd_user_passwd` 路徑零改動——executor 把證據貼進 ledger。

## 環境事實
（行號為 `origin/v3` @ 6dc879a；以函式名為準，動手前 `git fetch -q origin v3` 再核對。）
- `cli.py`：docstring 第 2 行 :2；`cmd_user_passwd` :148-177（`terminal.terminal_problem()` :152；`getpass` 兩次 :158-159；`store.set_web_password` :171；成功訊息 :176）；`passwd` 子指令 :574-577（`allow_abbrev=False`）。`pat new` 把 token「只顯示一次」是 `_say` 兩行（:182-186 附近），沒有 tty 要求——**它沒有要求，因為 PAT 本來就能被 AI 持有；臨時密碼不同，會直接當網頁登入用，所以這裡要求終端機**。
- `abf_launch/terminal.py:53-71`：`terminal_problem()` 要求 stdin、stdout 都是 tty、且是本程式的控制終端機（Linux 讀 `/proc/self/stat`；沒有 `/proc` 時只靠開 `/dev/tty`）。
- `store.py`：`TOKEN_SCHEMA` 的 `users` :100-107；`web_sessions` :108-113；`WEB_SESSION_SECONDS`／`MIN_PASSWORD_CHARS`／`MAX_PASSWORD_CHARS` :155-158；`hash_password` :1092；`password_matches` :1099；`set_web_password` :1109；`check_web_password` :1129；`create_web_session` :1149；`web_session_user` :1161；`end_web_session` :1177；`_migrate_tokens` :717-746；`connect_tokens` :749；`secrets` 已 import（:14）。登入的欄位 migration 先例：:739-745。`cloud-cleanup-a`（#213）的 `_add_cleanup_column`（:638-648）是另一個同型先例（`platform.db`）。
- `web.py`：登入 POST :230-266（`store.check_web_password` :251；失敗計數 `by_name`／`by_ip` :240-262）；登出 :269-276；`user_of` :177-179。**本任務不改這個檔。**
- 憲法 5.0.0（`.specify/memory/constitution.md:484-488`）與 `docs/adr/0006-…:104-110` 都寫「web password … set only at a terminal by the person (`abf-platform user passwd`)」。臨時密碼是「管理者在終端機發、本人在網頁改」，字面上跟「只在終端機由本人設」不同——見裁決 1。
- 憲法檢查：`tests/credentials_stay_in_settings_test.sh` 掃的是「git 追蹤檔案裡長得像 token 的值」與腳本是否印出 token 變數，**不掃 Python 產生的隨機值**；本任務的程式碼與文件裡不得出現任何範例密碼／token 形狀的字串。`tests/no_hardcoded_paths.sh` 對 `platform/` 不掃（`test_scope.py:5` 自行負責）。平台原始碼不得啟動其他程式（TC-071，`test_scope.py:99`）：本任務不用 subprocess。
- `tests/platform_storage_doc_test.sh:100-107`：文件儲存表裡寫的「N day/hour(s)」都要在 `platform/abf_platform/*.py` 找得到值相同的 `NAME = 數字*數字` 常數（所以常數要寫成 `TEMP_PASSWORD_SECONDS = 72 * 3600`）。
- 依賴的合併狀態：`account-onboarding`（#211）已在 `v3`（`docs/ONBOARDING.md` 存在）；`onboarding-test-pinned-base`（#218）已合併，`test_onboarding_doc.py` 不再釘 6061925，所以改 `OPERATIONS.md`／`PLATFORM.md` 不會踩舊的「其他文件沒動」檢查。
- 起草機器的 `python` 是 2.7，不代表 CI；executor 在 ledger 記 `sqlite3.sqlite_version` 與 `sys.version`。`secrets.token_urlsafe` 需要 Python 3.6 以上（專案其餘程式已用 f-string 以外的 3.x 功能，`store.py` 已 `import secrets` 並用 `secrets.token_urlsafe(32)`，:1150 附近）。

## 不做
- 不改 `web.py`、不新增任何路由或畫面（前端任務）。
- 不新增 MCP 工具、不動動作層（`actions/`）、不動 `guidance.py`／`mcp_server.py`。
- 不做「管理者能看到或找回密碼」：臨時密碼只存雜湊，弄丟只能重發。
- 不做 email／訊息自動寄送臨時密碼（管理者私下交給本人；平台沒有寄信功能，也不在這個任務加）。
- 不做忘記密碼的自助流程：`test_oauth_mcp.py:393-407` 明文禁止「reset／forgot」入口；忘了就找管理者重發臨時密碼。
- 不改憲法、ADR、`docs/INSTALL.md`、`docs/TESTING.md`。
- 不改密碼長度規則（8～1000）與雜湊參數（scrypt）。

## 裁決（2026-10-25，developer-agent；已併入上文，與其他段落不衝突）
1. **憲法與 ADR 的字句要維護者點頭，不在實作任務內改。** 憲法 5.0.0 第 484-488 行與 ADR 0006 第 108 行寫「密碼只在終端機由本人設」。臨時密碼讓「管理者在終端機發初始密碼、本人在網頁改成自己的」成為合法路徑。它保住的核心（AI 不能代按）靠三件事：臨時密碼只在真實終端機產生與顯示（作法 8）、臨時密碼的 session 什麼都做不了（作法 6，fail-closed）、最終密碼只有本人知道。但字面確實變了。executor 不得改憲法（`CLAUDE.md`「Never edit during implementation」）；developer-agent 另開一張修憲小單，由維護者決定措詞。**本任務合併不等這張單**（行為已受上面三件事約束），但 PR 說明要寫這一點。
2. **改密碼放 store 層，不放動作層。** 證據：登入本身就是 store 層（`web.py:251` 呼叫 `store.check_web_password`；`test_owner_binding.py:826-828` 把 `web.py` 用到的 `store.*` 名稱列為固定集合）；動作層是「launch／cancel／確認」這類帶 caller 的業務動作，且 `test_actions_layer.py:622`、`test_human_channel.py:160` 禁止動作／工具名出現 `passwd|login`。把改密碼放進動作層會牴觸這兩條，且得新增 parity 表項目與工具數說明。這是對 backend 專長守則「每個動作都呼叫動作層」的有意例外：登入、登出、改密碼屬身分機制，不是業務動作；PR 說明要寫這句。
3. **「密碼不得出現在日誌或任何回應中」的唯一例外：`--temporary` 對終端機輸出一次。** 這是功能本身（管理者必須看到才能轉交）；其餘一切——日誌、資料庫（只存雜湊）、例外訊息、非終端機的輸出、檔案——都不得出現（T2、T20、T22）。
4. **期限 72 小時，單一欄位。** 72 小時涵蓋週末與跨時區的遠端同事；比 24 小時少一次「過期又重發」。若維護者要改，只改 `TEMP_PASSWORD_SECONDS` 一個常數與兩份文件的「72 hours」（T28 會抓到不同步）。
5. **`web_session_user` 預設拒絕臨時密碼的 session（fail-closed），不是預設放行再要求前端逐路由檢查。** 理由：漏檢查一條路由就讓臨時密碼的人按得了「送出」，違背「按的必須是本人」；預設拒絕則前端漏掉也只是看起來像沒登入。代價：登入成功後前端必須直接導向改密碼頁（合約已寫），不能先回首頁。
6. **`change_web_password` 的 `keep_sid`**：改完密碼要不要保留當前 session？維護者原話只說「結束其他登入（如 `set_web_password`）」；保留當前的，是因為剛改完還要再登入一次沒有安全價值（剛剛已用舊密碼驗過），且避免臨時密碼的人在改完後又被丟回登入頁。

## 裁決二（2026-10-25，回應預檢 6 條）
5. 範圍是 9 個檔：上列 8 個＋`cli.py:149` 的 docstring 一併改成「no flag can type the person's own password; `--temporary` makes a one-time one」。
6. `change_web_password` 在**同一個交易**內 `SELECT password_hash, temp_until`、用 `password_matches` 驗舊密碼、再 `UPDATE ... WHERE name=? AND password_hash=<剛讀到的值>`；更新 0 列＝別人同時改過→回「目前的密碼不對」。
7. 刪掉「拿不到真舊庫就由 developer-agent 補跑」這個逃生口：改成自動測試——測試自己用舊版 `CREATE TABLE users`（無 temp_until）建庫、放一筆密碼，再跑 `init`，斷言 `PRAGMA integrity_check`＝ok、原密碼仍能登入、temp_until 為 NULL。`docs/TESTING.md` 不進範圍。
8. T20：測試從 `--temporary` 的 stdout 第 2 行取出那個密碼，斷言它不出現在 stderr、日誌（caplog 全等級）、`tokens.db` 的任何文字欄位；T22 刪掉原寫法，改為同一條斷言的 DEBUG 等級版本。
9. ONBOARDING §2 與 PLATFORM.md:495 的「no flag / no file」句改寫成與第 5 條同義，不保留原句。
10. 合併時機：本任務的 PR 等憲法修正（`constitution-temp-password`）合併後才合；文件寫入的就是修正後的規則，不會互相矛盾。
11. 憲法檢查補跑 `tests/no_per_pipeline_config.sh`、`tests/command_layer_is_site_neutral.sh`（本任務不碰 configs/ 與指令層，預期不受影響），結果貼 ledger。

## 裁決三（2026-10-25，回應 verifier 出題退回；號碼大的蓋小的）
12. **同時改密碼的情境定案**：`change_web_password` 在同一個交易內 `SELECT id, password_hash, temp_until`、用 `password_matches` 驗舊密碼（失敗＝「目前的密碼不對」），再 `UPDATE ... WHERE id=? AND password_hash=<剛讀到的值>`；**更新 0 列＝驗證後被別人改過 → `ValueError`「密碼剛被改過，請重新登入 (changed meanwhile)」**。作法 7、T13 照這句；裁決二第 6 條的「回『目前的密碼不對』」作廢。
13. **文件句子定案**：照裁決二第 9 條改寫，不保留原句；改寫後 ONBOARDING §2 仍須含 `twice`、`real terminal`、`no flag`（test_tc010 用），例：「no flag can type the person's own password: they type it twice at a real terminal; `--temporary` makes a one-time one instead」。作法 9「保留原句」作廢。
14. **T20 兩半都要**：非終端機被拒（作法 8）＋外洩檢查。外洩檢查對子行程的做法：從 Pty 執行的 stdout 第 2 行取出密碼，斷言它不在 stdout 其他行、stderr、`tokens.db` 任何文字欄位、以及測試資料夾底下任何檔案（`rglob` 讀每個檔的位元組）；`caplog` 只用於同程序呼叫 store 函式的那幾條。
15. 裁決二第 7 條的「init」＝平台開 `tokens.db` 的正常入口（`store` 裡現有的連線／建表函式，executor 在測試註明用哪個名字）。
16. 範圍以 8 個檔為準（cli.py 已在清單內）。

## 裁決四（2026-10-25，閱卷後）
17. **追認兩個檔**：`platform/tests/test_pat.py`（test_tcf03_f04 的 users 欄位清單加 `temp_until`）與 `platform/tests/test_web_actions.py`（`SCHEMA['tokens.users']` 加 `temp_until`）。加欄位必然要同步，仍是精確釘死欄位清單，不算放水。範圍改為 10 個檔；TC-102 已由 developer-agent 同步。
18. TC-069：真終端機下 stdout 與 stderr 同一螢幕，改為「除第 2 行外不含密碼」：接受，executor 在 ledger 補一句說明。

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
