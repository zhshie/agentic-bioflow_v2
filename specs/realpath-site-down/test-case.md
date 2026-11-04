# 測試案例：站台連線斷掉時，讀檔／列目錄／讀 log 回 site_unreachable＋重新登入句（realpath-site-down）

**規格**：`specs/realpath-site-down/plan.md`（本任務沒有獨立 spec.md，計畫即規格；維護者原話在計畫「維護者原話」節）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：「三個入口」＝列資料夾 `list_site_files`（程式裡的 `listing`）、讀結果檔 `read_run_file`（`readfile`）、讀失敗 log `read_run_log`（`readlog`）。「假站台」＝測試用的假 site，可以指定每個指令回什麼，並留下呼叫紀錄。「重新登入句」＝站台連線檢查（`--check-reach`）失敗時，既有的 `connect_failure` 給出的句子，例如 "No open connection to the site. Log in once in a WSL terminal first (請先在 WSL 終端機登入站台): " 後面接重新登入那一行指令。

測試檔：`platform/tests/test_station_realpath_down.py`（新）。下列「自動」除 TC-013、TC-014 外都在這個檔，每個測試在註解寫上 TC 編號。除非另有說明，假站台的 `--check-reach` 回失敗、`reason=no-master`，且使用一般的 run 名稱（不是 `-aN` 續跑名稱，因為續跑名稱在 realpath 前會多一次找資料夾的呼叫）。

## User Story 1 — 連線斷掉時，三個入口說對原因（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；失敗先行測試第 1 條 | 功能 | 假站台對 `realpath` 回 rc 255、錯誤輸出含 "Permission denied (keyboard-interactive)"；`--check-reach` 失敗並帶 `reason=no-master` 與開連線的那一行指令 | 對一個在允許範圍內的路徑呼叫 `listing` | 回 `("error", {...})`，其中 `error` 恰為 `site_unreachable`，`message` 含重新登入句與假站台給的那一行指令；沒有丟 `Refusal` | 自動：`platform/tests/test_station_realpath_down.py` |
| TC-002 | 作法 1；失敗先行測試第 1 條 | 功能 | 同 TC-001 的假站台 | 對 `readfile`（read_run_file 的處理函式）送一個結果檔路徑 | 回 `("error", {...})`，`error` 恰為 `site_unreachable`，`message` 含重新登入句與那一行指令；沒有丟 `Refusal` | 自動：同上 |
| TC-003 | 作法 1；失敗先行測試第 1 條 | 功能 | 同 TC-001 的假站台 | 對 `readlog` 要一個失敗 task 的 log | 回 `("error", {...})`，`error` 恰為 `site_unreachable`，`message` 含重新登入句與那一行指令；沒有丟 `Refusal` | 自動：同上 |
| TC-004 | 作法 1（逾時）；失敗先行測試第 2 條 | 例外 | 假站台對 `realpath` 逾時（rc 124）；`--check-reach` 同 TC-001 | 三個入口各呼叫一次 | 三者都回 `site_unreachable`，沒有丟 `Refusal` | 自動：同上 |
| TC-005 | 作法 1（needs-human）；失敗先行測試第 2 條 | 例外 | 假站台對 `realpath` 回非 0、錯誤輸出含 `on_site: needs-human`；`--check-reach` 同 TC-001 | 三個入口各呼叫一次 | 三者都回 `site_unreachable`，沒有丟 `Refusal` | 自動：同上 |
| TC-006 | 維護者原話 1：「先讓「MCP 讀取／下載結果檔」在國網跑得動」（國網連線過期是常態，要給對的原因與補救指令） | 功能 | 國網連線過期：假站台對 `realpath` 回 rc 255 "Permission denied (keyboard-interactive)"，`--check-reach` 回 `reason=no-master` 與重新登入指令 | 同事讀一個結果檔（read_run_file） | 回應講的是連線／登入問題並給出重新登入那一行指令；`message` 不含「路徑不正確」、不含 "could not say where the path leads"、不含「站台無法確認路徑的真實位置」 | 自動：同上 |
| TC-007 | 維護者原話 2：「跟Seqera platform一樣的模式，不要自己定義」（沿用既有 `site_unreachable`＋`connect_failure`） | 功能 | 同 TC-001 的假站台；另備一個「realpath 成功、後面的步驟（判斷種類）回 rc 255」的情況，`--check-reach` 設定相同 | 對同一個入口，各跑一次「realpath 斷線」與「後段步驟斷線」 | 兩次的 `error` 都是 `site_unreachable`，`message` 逐字相同（同一句、同一個代碼） | 自動：同上 |
| TC-008 | 作法 1（`_site_down` 會先檢查再決定句子） | 例外 | 假站台對 `realpath` 回 rc 255；但 `--check-reach` 回成功（連線檢查沒壞） | 三個入口各呼叫一次 | 三者都回 `site_unreachable`，沒有丟 `Refusal`；`message` 等於既有 `_site_down` 在同條件下給的句子（"The site could not do this (exit code 255)."） | 自動：同上 |
| TC-009 | 失敗先行測試第 5 條 | 功能 | 同 TC-001 的假站台，記下所有呼叫 | 三個入口各呼叫一次 | 假站台的呼叫紀錄只有 `realpath` 那一次與 `--check-reach`，沒有任何讀內容、判斷種類、取大小的呼叫 | 自動：同上 |

## User Story 2 — 其他失敗維持原樣，舊行為不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 作法 2；失敗先行測試第 3 條 | 例外 | 假站台對 `realpath` 回 rc 1、錯誤輸出 "No such file"（不是斷線） | 三個入口各呼叫一次 | 三者都丟 `rules.Refusal`，句子逐字等於 v3：列資料夾 "the site could not say where the path leads, so it is not listed (站台無法確認路徑的真實位置)"；讀結果檔 "the site could not say where the path leads, so it is not read (站台無法確認路徑的真實位置)"；讀 log "the site could not say where the task folder leads, so it is not read (站台無法確認路徑的真實位置)" | 自動：同上 |
| TC-011 | 作法 2（輸出不是 NUL 結尾） | 例外 | 假站台對 `realpath` 回 rc 0，但輸出不以 NUL 結尾 | 三個入口各呼叫一次 | 三者都丟與 TC-010 同樣逐字的 `Refusal`，不是 `site_unreachable` | 自動：同上 |
| TC-012 | 作法 2（段數不符）；失敗先行測試第 4 條 | 例外 | 假站台對 `realpath` 回 rc 0、NUL 結尾，但段數與要查的路徑數不符（偽造換行／多出一段） | 三個入口各呼叫一次 | 三者都丟與 TC-010 同樣逐字的 `Refusal`（既有第 153 行附近那條案例不變） | 自動：同上 |
| TC-013 | 作法 3 | 功能 | 同 `test_station_owner.py` 直接呼叫 `handlers._real_path` 的方式 | 直接呼叫 `handlers._real_path(site, path, roots)`：一次 realpath 正常、一次是非斷線的失敗（如 TC-010） | 正常時回 `(真實路徑, 各 root 的真實路徑)` 的 tuple；非斷線失敗時回 `None`；呼叫方式與回傳形狀與 v3 相同 | 自動：`platform/tests/test_station_owner.py`（既有，只增不減） |
| TC-014 | 計畫「範圍：檔案」被釘住的既有測試；完成標準 2 | 功能 | v3 上通過的既有測試 | 跑 `test_station_owner.py`、`test_owner_gaps.py`、`test_resume_platform.py`，以及 v3 上含 "could not say where" 的每一條測試 | 全部綠；與 base 比對，這些測試檔只有新增行，沒有刪除、放寬、跳過；realpath 正常時三個入口的行為與 v3 一樣 | 自動：上列既有測試檔 |
| TC-015 | 範圍：`PITFALLS.md` 加一條 | 功能 | 變更完成 | 打開 `docs/PITFALLS.md` | 有一條新增項目，意思是「第一步 ssh 失敗不可當成輸入錯誤」，並說明斷線要回連線錯誤、不是路徑拒絕 | 手動：驗收時讀 `docs/PITFALLS.md` 的 diff |

## 憲法與安全網

對應原則 VI「Nothing Goes Quiet」（失敗要講清楚原因與下一步）與安全網的憑證規則（密鑰、token 不出現在輸出）；以及既有的 fail closed（站台說不出路徑就絕不讀）。fail closed 由 TC-009、TC-010 至 TC-012 證明。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 原則 VI；專長守則「錯誤訊息」 | 例外 | 同 TC-001 的斷線情況 | 對三個入口看回應 | `message` 說明發生什麼事（連線斷了）與怎麼處理（重新登入那一行指令）；不含堆疊追蹤（"Traceback"）、不含 SQL 字樣 | 自動：`platform/tests/test_station_realpath_down.py` |
| TC-017 | 安全網：憑證不出現在輸出；專長守則「密鑰不得出現在日誌或回應」 | 例外 | 假站台斷線時的錯誤輸出中塞入一個假的 token／密碼字串 | 三個入口各呼叫一次，檢查回應 | 回應內容不含該假 token／密碼字串 | 自動：同上 |

## User Story 3 — 這次不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 計畫「不做」第 1 條：不自動重連、不嘗試開 ControlMaster | 不在範圍 | 同 TC-001 的斷線情況，記下所有呼叫 | 三個入口各呼叫一次 | 呼叫紀錄中沒有任何嘗試開啟或關閉共用連線的呼叫（沒有 ControlMaster、沒有 `-O`、沒有登入動作），只有 `realpath` 與 `--check-reach`；回應只是請人手動重新登入 | 自動：`platform/tests/test_station_realpath_down.py` |
| TC-019 | 計畫「不做」第 2 條與作法 4：不加新錯誤碼、不改平台端顯示文字 | 不在範圍 | 變更完成 | 檢查斷線時回傳的 `error` 值，並列出 `platform/abf_station/` 內傳給 `_failure(` 的所有錯誤碼 | 斷線的 `error` 恰為既有的 `site_unreachable`；整個錯誤碼集合與 v3 完全相同，沒有新增 | 自動：同上 |
| TC-020 | 計畫「不做」第 3 條與作法 4：不動其他沒有呼叫 `_real_path` 的站台函式、不改平台端、不改 MCP、不改網頁字串 | 不在範圍 | 變更完成 | 驗收時看 `git diff v3...HEAD` | 變動的檔案只有計畫「範圍：檔案」列的那些（`handlers.py`、`readfile.py`、`readlog.py`、新測試、既有測試只增不減、`PITFALLS.md`）以及 specs 下的記錄；`handlers.py` 的變動只在 `_real_path`／`listing` 與新增的內部函式；三個呼叫處的非斷線程式碼是只新增分支，沒有改寫既有句子 | 手動：驗收時讀 `git diff v3...HEAD` |
