# 測試案例：設定頁登記／移除管線版本（settings-register-pipeline）

<!--
Written by the verifier (CONTRACT mode) from specs/settings-register-pipeline/plan.md (3rd version, with rulings 1-14), DESIGN.md and PRODUCT.md. No spec.md exists for this task: the plan is the spec.
Reader: the maintainer (not an engineer). Language: 繁體中文; identifiers, paths, routes, notice keys stay as they are.
-->

**規格**：`specs/settings-register-pipeline/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞（一句話）：
- **運算環境**：使用者在設定頁看到的一台伺服器或國網帳號，管線版本登記在它底下。
- **登記**：把「某管線的某版本、站台上載入它用的模組名稱、模組設定的資料夾變數」存進該運算環境的設定（`config.sitePipelines`）。
- **使用前檢查**：平台請站台代理確認該站台真的載得到登記的模組（preflight）。
- **確認頁**：第一步送出後出現、寫入前讓人按「確認」的頁面（ADR 0006：每個寫入都經人確認）。
- **CSRF 權杖**：防止別的網站代使用者送表單的一次性記號。
- 測試檔縮寫 `T` ＝ `platform/tests/test_web_settings_register.py`（新檔）。範例資料取自計畫：管線 `nf-core/ampliseq`、版本 `2.18.0`、模組 `biology/nf-core-ampliseq/2.18.0`、變數 `NFCORE_AMPLISEQ_HOME`。「ann」「ben」是兩位不同使用者；「ann-ce」是 ann 名下的運算環境。

## 維護者原話對照

| 原話 | 對應 TC |
|---|---|
| 原話 1「登記管線要做，畢竟是裝在使用者自己租的伺服器或國網。」＋目標「登記後 `/launch` 第 3 步就不再顯示『尚未登記』」 | A01、C01、E01、D24 |
| 原話 2「先把功能做起來吧，以後再改美觀」 | D13（只用既有 class，不新增視覺）、全部功能 TC 先於美觀 |
| 原話 3「跟Seqera platform一樣的模式，不要自己定義」（登記放在運算環境設定裡由使用者自己填） | A07、X06、D01 |
| DESIGN 原話 7「介面上不要有AI太口語化的回覆，要有制式化的通知呈現」 | N01–N06、N11、D10 |
| DESIGN 2026-10-27「一樣要注意中文的顯示不能口語」 | D14 |
| DESIGN 原話 13「哪有一個固定的按鈕會這樣寫?」（按鈕只用固定動詞） | D05 |
| DESIGN 原話 5「做成產品英文版面是必須的」 | B20、D02、D15、N01–N06 |

## 1. 動作層：登記、移除、只讀檢查（作法 1；裁決 9、10）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| A01 | 作法 1；原話 1 | 功能 | ann 有可用的運算環境 ann-ce（雲端以外、可預檢類型），站台代理在線，登記清單為空 | 以 `confirmed_by=PAGE`、`caller=ann` 呼叫 `register_site_pipeline`，欄位為範例資料 | 回傳 ok；ann-ce 的 `sitePipelines` 恰好多一筆 `{pipeline, revision, module, home}` 且四值與送入相同；佇列中恰好新增一筆該環境的預檢工作；`preflight` 為 `"queued"` | 自動：`T` |
| A02 | 作法 1（三個人工管道） | 功能 | 同 A01 | 分別以 `TERMINAL`、`ELICITED`、`PAGE` 為 `confirmed_by` 呼叫登記 | 三種都被接受並寫入 | 自動：`T` |
| A03 | 作法 1；Safety Net | 例外 | 同 A01，記下資料庫內容 | 呼叫 `register_site_pipeline` 時 `confirmed_by` 缺少、為 `None`、為字串 `"PAGE"`、為長得像管道的假物件 | 每次都被拒絕（訊息為無人工確認管道）；ann-ce 的設定、工作佇列、更新時間與呼叫前完全相同 | 自動：`T` |
| A04 | 作法 1；Safety Net | 例外 | ann-ce 已有一筆登記，記下資料庫內容 | 呼叫 `remove_site_pipeline` 時 `confirmed_by` 缺少、為 `None`、為字串、為假物件 | 每次都被拒絕；資料庫與呼叫前完全相同，該筆仍在 | 自動：`T` |
| A05 | 作法 1（同 pipeline＋revision＝取代） | 功能 | ann-ce 已有 `nf-core/ampliseq 2.18.0` 一筆，module 為 M1 | 再登記 `nf-core/ampliseq 2.18.0`，module 改為 M2 | 清單筆數不變；該筆的 module 變為 M2；其他筆不變；無重複 | 自動：`T` |
| A06 | 作法 1 | 功能 | ann-ce 已有 `nf-core/ampliseq 2.18.0` | 登記 `nf-core/ampliseq 2.17.0` | 清單變兩筆，原有一筆原封不動 | 自動：`T` |
| A07 | 原話 3；作法 1 | 功能 | ann-ce 設有 `modules`、`siteConfigVars`、說明、代理、憑證等其他設定 | 登記一筆後比對 | 只有 `sitePipelines` 改變；環境名稱、說明、代理、擁有者、`modules`、`siteConfigVars` 及其他 config 鍵與登記前相同（登記存在運算環境自己的設定裡，沒有新概念） | 自動：`T` |
| A08 | 作法 1 | 功能 | ann-ce 有兩筆登記，記下工作佇列 | 以 `PAGE` 移除其中一筆 | 回傳 `ok: True, changed: True`；該筆消失、另一筆仍在；工作佇列沒有新增預檢 | 自動：`T` |
| A09 | 作法 1 | 例外 | ann-ce 的清單中沒有 `nf-core/rnaseq 3.14.0`，記下資料庫內容 | 以 `PAGE` 移除 `nf-core/rnaseq 3.14.0` | 回傳 `{"ok": True, "changed": False}`；資料庫與呼叫前完全相同 | 自動：`T` |
| A10 | 作法 1；backend 守則（跨使用者寫） | 例外 | ben 擁有 ben-ce；ann 為呼叫者；記下 ben-ce 內容 | ann 以 `PAGE` 對 ben-ce 呼叫 `register_site_pipeline` | 回應為「找不到」，與呼叫一個不存在的環境名稱時完全相同（不洩漏 ben-ce 存在）；ben-ce 沒有改變、沒有排工作 | 自動：`T` |
| A11 | 作法 1；backend 守則（跨使用者寫） | 例外 | ben-ce 已有一筆登記 | ann 以 `PAGE` 對 ben-ce 呼叫 `remove_site_pipeline` 要移除該筆 | 回應為「找不到」，與不存在的環境相同；ben-ce 的那筆仍在 | 自動：`T` |
| A12 | 作法 1（驗證照舊由 `clean()` 做，錯誤原樣回傳） | 例外 | ann-ce，記下資料庫內容 | 分別登記：module 含 `..`；home 為小寫 `nfcore_home`；revision 為分支名 `main` | 每次都失敗，且回報的原因指出是哪一欄（例如 `sitePipelines[...].module`、`.home`、`.revision`），文字與 `compute_envs.clean()` 的訊息一致；資料庫不變、不排預檢 | 自動：`T` |
| A13 | 作法 1（管線名稱判斷） | 例外 | ann-ce，記下資料庫內容 | 分別登記管線名稱：`acme/rnaseq`、`NF-CORE/x`、`nf-core/`、`nf-core/-x`、`nf-core/` 加 65 個合法字元、`nf-core/x` 後面接換行 | 每次都失敗並說明管線名稱格式不合；資料庫不變 | 自動：`T` |
| A14 | 作法 1（管線名稱判斷） | 功能 | ann-ce | 分別登記 `nf-core/ampliseq`、`nf-core/a1-b2`、`nf-core/` 加正好 64 個合法字元的名稱 | 三者都被接受 | 自動：`T` |
| A15 | 作法 1、裁決 9（代理離線） | 功能 | ann-ce 的站台代理離線（或沒有代理） | 登記一筆 | 登記成功寫入；`preflight` 為 `"no_agent"`；不拋錯 | 自動：`T` |
| A16 | 作法 1、裁決 9（類型不檢查） | 功能 | ann 有一個平台類型不屬於可預檢類型（`CHECKABLE` 以外）的運算環境 | 登記一筆 | 登記成功寫入；`preflight` 為 `"not_checkable"`；工作佇列沒有新增預檢 | 自動：`T` |
| A17 | 裁決 9（其他拒絕） | 例外 | 預檢排入被拒絕，原因不是離線也不是沒有代理 | 登記一筆 | 登記仍成功寫入；`preflight` 為第四種值（不是 queued、no_agent、not_checkable 之一）；不拋出未處理的例外 | 自動：`T` |
| A18 | 裁決 10 | 功能 | ann-ce，記下資料庫全部內容 | 呼叫 `check_site_pipeline_change` 檢查一筆合法的新增、一筆存在的移除、一筆不存在的移除 | 前兩者回報可以進行、第三者回報該筆已不在；呼叫前後資料庫（含工作佇列）逐位元相同；此函式不需要 `confirmed_by` | 自動：`T` |
| A19 | 裁決 10 | 例外 | 同 A18，另有 ben-ce | 用 A12、A13 的壞值與 ben-ce 呼叫 `check_site_pipeline_change` | 壞值得到與 A12／A13 同一種欄位錯誤；ben-ce 得到「找不到」；資料庫不變 | 自動：`T` |
| A20 | 作法 1（CLI 輸出逐字不變） | 功能 | 把 `_queue_first_preflight` 搬成共用 helper 之後 | 以 CLI 建立或更新運算環境，分別遇到：代理在線、沒有代理在線、類型不檢查 | 三種情況的輸出與 base 版逐字相同（`preflight queued (預檢已排入); the status changes when the agent has answered`、`沒有代理在線，尚未預檢 (no agent online, not checked yet): ...`、環境自己的訊息）；既有 `test_dataset_cli.py` 等釘死測試仍綠 | 自動：既有 `platform/tests/test_dataset_cli.py` 與 `T` |

## 2. 網頁第一步：`POST /settings/pipelines`（作法 2、裁決 6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| B01 | 作法 2 第一步 | 功能 | ann 已登入；ann-ce 清單中沒有該筆；記下資料庫（含工作佇列） | ann 送出 `op=add`、ce、pipeline、revision、module、home（範例資料）與 purpose `settings-pipeline` 的 CSRF | 回 200 確認頁，頁面列出六項：動作（新增）、環境、管線、版本、模組名稱、管線資料夾變數，值與送入相同；資料庫與工作佇列完全沒有改變 | 自動：`T` |
| B02 | 作法 2 確認頁 | 功能 | 取得 B01 的確認頁 | 檢查頁面的表單 | 表單送往 `/settings/pipelines/confirm`；六個欄位以 hidden 帶回；另有 CSRF，其用途為 `settings-pipeline-confirm:` 加上（op、ce、pipeline、revision、module、home 依序以換行串接後的 sha256）；有「確認」按鈕；「返回」是連到 `/settings` 的連結，不是送出鈕 | 自動：`T` |
| B03 | 作法 2 第一步（移除） | 功能 | ann-ce 有該筆登記；記下資料庫 | ann 送出 `op=remove` 與該筆的 pipeline、revision、module、home | 回 200 確認頁，動作顯示為移除，其餘五項同樣列出；資料庫不變，該筆仍在 | 自動：`T` |
| B04 | 作法 2、裁決 6、12（gone） | 例外 | ann-ce 沒有該筆登記 | ann 送出 `op=remove` 指向不存在的一筆 | 回 303，位置為 `/settings?notice=gone&ce=ann-ce#ce-ann-ce`；資料庫不變；跟隨後，ann-ce 那一列上方顯示「○ 此管線版本已不在清單中。」 | 自動：`T` |
| B05 | 計畫失敗先行測試（module 含 `..`） | 例外 | ann-ce | 送出 `op=add`，module 為 `biology/../x` | 回 400，重畫設定頁；不是確認頁；資料庫不變；ann-ce 那一列上方有錯誤句且指出模組名稱欄；各欄已填的值保留在表單裡 | 自動：`T` |
| B06 | 計畫失敗先行測試（home 小寫） | 例外 | ann-ce | 送出 `op=add`，home 為 `nfcore_ampliseq_home` | 回 400，重畫設定頁；錯誤句指出管線資料夾變數欄、並說明只能大寫字母、數字與底線；已填值保留；資料庫不變 | 自動：`T` |
| B07 | 計畫失敗先行測試（revision 是分支名） | 例外 | ann-ce | 送出 `op=add`，revision 為 `main` | 回 400；錯誤句指出版本欄、並說明須為發行版本或 40 字元提交碼、不收分支名；已填值保留；資料庫不變 | 自動：`T` |
| B08 | 計畫失敗先行測試（非 nf-core） | 例外 | ann-ce | 送出 `op=add`，pipeline 為 `acme/rnaseq` | 回 400；錯誤句指出管線欄；已填值保留；資料庫不變 | 自動：`T` |
| B09 | 計畫失敗先行測試（大寫擁有者） | 例外 | ann-ce | 送出 `op=add`，pipeline 為 `NF-CORE/x` | 回 400；錯誤句指出管線欄；已填值保留；資料庫不變 | 自動：`T` |
| B10 | 作法 2、3（四欄必填；op 白名單） | 例外 | ann-ce | 分別送出：四欄之一為空、`op` 為 `add` 與 `remove` 以外的值、缺 `ce` | 每次回 400，不顯示確認頁，資料庫不變；空欄的錯誤句指出是哪一欄 | 自動：`T` |
| B11 | 作法 2（環境是自己的）；backend 守則（跨使用者） | 例外 | ben 擁有 ben-ce；ann 已登入 | ann 送出 `ce=ben-ce` 的 add 與 remove | 回 400，不顯示確認頁；錯誤句顯示在頁首；內容與送出不存在的環境名稱時相同；頁面不出現 ben-ce 的任何資料 | 自動：`T` |
| B12 | 作法 2（CSRF） | 例外 | ann 已登入 | 分別送出：沒有 CSRF 欄、錯誤的 CSRF、別的用途的 CSRF（例如登出用的） | 每次回 403，不顯示確認頁、不寫入；403 頁說明表單失效、什麼都沒有改、請重新整理後再試 | 自動：`T` |
| B13 | 作法 2（same_origin） | 例外 | ann 已登入，備有正確 CSRF | 以別的來源網址（Origin 或 Referer）送出 | 回 403，不顯示確認頁、不寫入 | 自動：`T` |
| B14 | 作法 2（未登入） | 例外 | 沒有登入的 cookie | 對 `/settings/pipelines` 與 `/settings/pipelines/confirm` 各送一次 POST | 兩者都回 303 導向 `/login`；不寫入 | 自動：`T` |
| B15 | 作法 2（臨時密碼） | 例外 | ann 以臨時密碼登入、尚未改密碼 | 對兩條新路由各送一次 POST | 兩者都回 303 導向 `/welcome`；不寫入 | 自動：`T` |
| B16 | 裁決 5 | 功能 | ann-ce 的登記清單為空 | ann 對 ann-ce 送出 add（登記第一筆） | 確認頁多出一句：「此環境目前未登記管線：送出時直接取用 nf-core 官方版本。登記第一筆後，只能送出已登記的管線版本。」（`?lang=en` 為英文對應句） | 自動：`T` |
| B17 | 裁決 5 | 功能 | ann-ce 只有一筆登記 | ann 對該筆送出 remove（移除最後一筆） | 確認頁出現與 B16 相同的那一句 | 自動：`T` |
| B18 | 裁決 5 | 功能 | ann-ce 已有一筆；另有兩筆的環境 | 對 ann-ce 送出 add 第二筆；對兩筆的環境送出 remove 其中一筆 | 兩個確認頁都沒有那一句 | 自動：`T` |
| B19 | 裁決 12；作法 2 | 例外 | ann-ce | 觸發 B05 的錯誤 | 錯誤句緊接在 ann-ce 那一列上方，句首有符號 `✕`，並有文字；不只靠顏色 | 自動：`T` |
| B20 | 原話 5（英文版面）；裁決 14 | 功能 | ann 使用 `?lang=en` | 走完：設定頁表單、第一步確認頁、第一步錯誤、第二步、通知 | 全程維持英文，沒有跳回中文；確認頁的按鈕為 Confirm、Back | 自動：`T` |

## 3. 網頁第二步：`POST /settings/pipelines/confirm`（作法 2、裁決 6–8）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| C01 | 作法 2 第二步；原話 1 | 功能 | ann-ce 代理在線，確認頁已取得（B01） | ann 按「確認」（送出 hidden 欄位與確認用 CSRF） | 回 303，位置為 `/settings?notice=added_queued&ce=ann-ce#ce-ann-ce`；ann-ce 清單多了該筆；佇列新增恰好一筆預檢；跟隨後該列上方顯示「✓ 已登記，並已排入使用前檢查。」 | 自動：`T` |
| C02 | 作法 2 第二步（移除） | 功能 | 移除確認頁已取得（B03） | ann 按「確認」 | 回 303，位置為 `/settings?notice=removed&ce=ann-ce#ce-ann-ce`；該筆消失；不排預檢 | 自動：`T` |
| C03 | 作法 2（欄位雜湊綁進 CSRF） | 例外 | 已取得確認頁與確認用 CSRF | 六個欄位（op、ce、pipeline、revision、module、home）逐一改掉其中一欄後送出 | 六次都回 403，且資料庫不變 | 自動：`T` |
| C04 | 作法 2、裁決 2 | 例外 | 已取得第一步用的 CSRF（purpose `settings-pipeline`） | 把第一步用的 CSRF 拿來送第二步；另把某一組欄位的確認用 CSRF 拿去送另一組欄位 | 兩種都回 403，不寫入 | 自動：`T` |
| C05 | 作法 2（CSRF、來源） | 例外 | ann 已登入 | 對第二步送出：缺 CSRF、錯 CSRF、別的來源 | 每次回 403，不寫入 | 自動：`T` |
| C06 | backend 守則（跨使用者寫） | 例外 | ann 取得確認頁；ben 已登入 | ben 用自己的 session 送出 ann 的欄位與 ann 的確認用 CSRF | 回 403（權杖綁定登入階段），ann-ce 不變 | 自動：`T` |
| C07 | backend 守則（跨使用者寫）；裁決 7 | 例外 | ben 已登入，並為「ce=ann-ce」的欄位組出屬於他自己 session 的有效確認用 CSRF | ben 送出第二步 | 回 400 重畫設定頁；頁首顯示「✕ 未能完成：」加原因（找不到該環境）；ann-ce 沒有被改；不洩漏 ann-ce 存在 | 自動：`T` |
| C08 | 裁決 7 | 例外 | 已取得確認頁；之後 ann-ce 被刪除 | ann 按「確認」 | 回 400 重畫設定頁；環境已不存在，所以錯誤句顯示在頁首「✕ 未能完成：<原因>」；不寫入 | 自動：`T` |
| C09 | 裁決 7（`clean()` 退回） | 例外 | 已取得確認頁；之後 ann-ce 的清單被補到 100 筆（上限） | ann 按「確認」 | 回 400 重畫設定頁；ann-ce 那一列上方顯示「✕ 未能完成：」加動作層回的原因（指出 `sitePipelines`）；清單不變 | 自動：`T` |
| C10 | 裁決 8 | 例外 | 已取得移除確認頁；之後同一筆被別處先移除 | ann 按「確認」 | 回 303，notice 為 `gone`（`/settings?notice=gone&ce=ann-ce#ce-ann-ce`），顯示「○ 此管線版本已不在清單中。」；不改資料 | 自動：`T` |
| C11 | 裁決 2（可重做） | 功能 | 已按過一次「確認」成功 | 以同一組欄位與同一確認用 CSRF 再送一次 | 不出錯；清單仍只有一筆（無重複） | 自動：`T` |
| C12 | 作法 2、backend 守則（路由不得自己做邏輯） | 功能 | 以監看替身記錄對動作層的呼叫 | 走完第二步 | 對 `register_site_pipeline`／`remove_site_pipeline` 的呼叫帶 `confirmed_by=actions.PAGE`、`caller` 為登入者；寫入只發生在這個呼叫裡 | 自動：`T` |
| C13 | 作法 2、裁決 9（離線） | 功能 | ann-ce 代理離線 | 走完新增兩步 | 303 的 notice 為 `added_no_agent`；跟隨後顯示「✓ 已登記。站台代理目前離線，使用前檢查將於代理上線後執行。」；清單已多一筆 | 自動：`T` |
| C14 | 作法 2、裁決 9（不檢查類型） | 功能 | ann 有不可預檢類型的運算環境 | 走完新增兩步 | notice 為 `added_not_checkable`；顯示「✓ 已登記。此運算環境類型不執行使用前檢查。」；清單已多一筆 | 自動：`T` |
| C15 | 裁決 9（其他拒絕） | 例外 | 預檢排入被拒（原因非離線） | 走完新增兩步 | notice 為 `added_check_refused`；顯示「✓ 已登記。使用前檢查未能排入，請稍後於設定頁重新登記以再次檢查。」；清單已多一筆 | 自動：`T` |

## 4. 通知（notice）顯示（作法 2、裁決 6、9、12）

句子皆取自計畫；中文為正式書面語。每個通知「句首有符號、符號後是文字」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N01 | 作法 4 | 功能 | ann 已登入，有 ann-ce | 開 `/settings?notice=added_queued&ce=ann-ce` | ann-ce 那一列上方顯示「✓ 已登記，並已排入使用前檢查。」；`?lang=en` 顯示「✓ Registered. A pre-use check has been queued.」 | 自動：`T` |
| N02 | 作法 4 | 功能 | 同上 | `notice=added_no_agent` | 「✓ 已登記。站台代理目前離線，使用前檢查將於代理上線後執行。」／「✓ Registered. The site agent is offline; the pre-use check will run when it connects.」 | 自動：`T` |
| N03 | 作法 4 | 功能 | 同上 | `notice=added_not_checkable` | 「✓ 已登記。此運算環境類型不執行使用前檢查。」／「✓ Registered. This type of compute environment has no pre-use check.」 | 自動：`T` |
| N04 | 作法 4 | 功能 | 同上 | `notice=removed` | 「✓ 已移除。」／「✓ Removed.」 | 自動：`T` |
| N05 | 作法 4、裁決 12 | 功能 | 同上 | `notice=gone` | 「○ 此管線版本已不在清單中。」／「○ This pipeline version is no longer registered.」（符號為 ○，不是 ✓） | 自動：`T` |
| N06 | 裁決 9 | 功能 | 同上 | `notice=added_check_refused` | 「✓ 已登記。使用前檢查未能排入，請稍後於設定頁重新登記以再次檢查。」／「✓ Registered. The pre-use check could not be queued; register it again later on the Settings page to retry.」 | 自動：`T` |
| N07 | 作法 2（白名單） | 例外 | ann 已登入 | 開 `notice=bogus`、`notice=<script>x</script>`、`notice=`（空） | 三者都不顯示任何通知；輸入的文字不被原樣印在頁面上；頁面其餘部分正常 | 自動：`T` |
| N08 | 裁決 6 | 功能 | ann 已登入 | 開 `/settings?notice=removed&ce=ann-ce` | 通知出現在 ann-ce 那一列上方，且該列有 `id="ce-ann-ce"` 的錨點 | 自動：`T` |
| N09 | 裁決 6 | 例外 | ben 擁有 ben-ce；ann 已登入 | ann 開 `?notice=removed&ce=ben-ce`、`?notice=removed&ce=不存在的名稱`、`?notice=removed`（無 ce） | 三者的通知都顯示在頁面頂端，不在任何環境列上方；頁面不出現 ben-ce | 自動：`T` |
| N10 | 作法 2；backend 守則 | 例外 | 記下資料庫 | 對 `/settings` 發出帶各種 notice 值的 GET | 資料庫完全不變（GET 不寫入） | 自動：`T` |
| N11 | 裁決 7、12 | 功能 | 觸發 C09（失敗） | 讀回應頁面 | 中文為「✕ 未能完成：<原因>」；`?lang=en` 為「✕ Not completed: <reason>」；符號、文字俱在 | 自動：`T` |

## 5. 設定頁畫面與字串（作法 3、4；DESIGN.md「用字」、Constraints）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| D01 | 作法 3、4；原話 3 | 功能 | ann 有兩個運算環境 | 開 `/settings` | 每個運算環境列在「已登記管線」清單下方都有「登記管線」表單，含四個欄位，標籤逐字為：「管線（例 nf-core/ampliseq）」「版本（例 2.18.0）」「模組名稱（站台 module load 使用的名稱，例 biology/nf-core-ampliseq/2.18.0）」「管線資料夾變數（模組設定的環境變數名稱，例 NFCORE_AMPLISEQ_HOME）」，表單送往 `/settings/pipelines` 且 `op=add` | 自動：`T` |
| D02 | 原話 5；作法 4 | 功能 | 同上，`?lang=en` | 開設定頁 | 標籤逐字為：「Pipeline (e.g. nf-core/ampliseq)」「Version (e.g. 2.18.0)」「Module name (the name used by module load on the site, e.g. biology/nf-core-ampliseq/2.18.0)」「Pipeline folder variable (the environment variable the module sets, e.g. NFCORE_AMPLISEQ_HOME)」 | 自動：`T` |
| D03 | 作法 3 | 功能 | ann-ce 有兩筆登記 | 開設定頁 | 兩筆登記旁各有一個「移除」小表單，各自帶該筆的 pipeline、revision、module、home 與 `op=remove`，送往 `/settings/pipelines`；沒有登記的環境不出現移除鈕 | 自動：`T` |
| D04 | 作法 3；用字第 4 條；裁決 11 | 功能 | 開設定頁 | 檢查登記表單 | 四個欄位的標籤都有 `<span class="req" title="必填">*</span>`（英文 title 為 Required）；表單上方有圖例「* 必填」（英文「* Required」）；標籤本身沒有重複「必填」二字；四個欄位皆有 `required` 屬性 | 自動：`T` |
| D05 | 作法 4；DESIGN 原話 13 | 功能 | 開設定頁、確認頁 | 讀按鈕文字 | 中文按鈕只用固定動詞：登記、移除、確認、返回；英文為 Register、Remove、Confirm、Back；按鈕上沒有數字或檔名 | 自動：`T` |
| D06 | 作法 3 | 功能 | 開設定頁 | 比對位置 | 登記表單位於該環境「已登記管線」清單之後（下方）；清單為空的環境同樣有表單 | 自動：`T` |
| D07 | 裁決 5 | 功能 | ann-ce 登記清單為空 | 開設定頁 | 表單上方顯示：「此環境目前未登記管線：送出時直接取用 nf-core 官方版本。登記第一筆後，只能送出已登記的管線版本。」；`?lang=en` 為「No pipelines are registered here: runs use the nf-core release directly. Once you register one, only registered pipeline versions can be run here.」 | 自動：`T` |
| D08 | 裁決 5 | 功能 | ann-ce 有一筆以上登記 | 開設定頁 | 該環境沒有 D07 的句子 | 自動：`T` |
| D09 | DESIGN 畫面 12（空狀態） | 例外 | ann 沒有任何運算環境 | 開設定頁 | 仍顯示既有的「沒有運算環境。」，沒有登記表單，頁面正常（200） | 自動：`T` |
| D10 | 專長守則（狀態不只靠顏色）；DESIGN States | 功能 | 渲染：各種 notice、步驟一錯誤句、第二步失敗句、空清單提示 | 檢查輸出的 HTML | 每個狀態句同時含符號（✓／○／✕）與文字；符號與文字不是只靠 class 區分 | 自動：`T` |
| D11 | DESIGN Constraints；計畫「CSP 不變」 | 功能 | 渲染設定頁（含通知與錯誤）與確認頁 | 檢查 HTML | 沒有任何 `style=` 屬性；沒有 `<script`；沒有指向外部網址（`http://`、`https://`）的資源；沒有新增的外部字型或圖片 | 自動：`T` |
| D12 | 作法 2「CSP 不變」 | 功能 | 對 `GET /settings`、`POST /settings/pipelines`（成功與失敗）、`POST /settings/pipelines/confirm`（成功與失敗）取得回應 | 讀回應標頭 | 每個回應的 Content-Security-Policy 與 `web._HEADERS` 完全相同（`default-src 'none'`、不含 `img-src`、`form-action 'self'`），並帶 `Cache-Control: no-store`、`X-Frame-Options: DENY` | 自動：`T` |
| D13 | 作法 3；原話 2；專長守則（只用 DESIGN tokens） | 功能 | 比對 base | 檢查新標記用到的 class 與樣式表 | 新標記用到的每個 class 都已存在於現有樣式表；樣式表檔案（`components/bundle.css` 或現行單一樣式表）與 base 相同，沒有新增顏色、字型、間距數值 | 自動：`T` |
| D14 | DESIGN「用字」；DESIGN 2026-10-27 原話 | 功能 | 本任務新增的全部中文字串；確認頁、重畫的錯誤頁、兩條新路由的 403 頁（中文） | 以 DESIGN 禁用字清單比對（用過、選好、寫死、自己填、自己調整、你還沒、還沒有、還不能、這個、這份、這條、這一版、一下、弄、搞、東西、喔、啦、吧、囉、蠻、超） | 沒有任何一個禁用字出現 | 自動：`T` |
| D15 | 原話 5；作法 4 | 功能 | 本任務新增的每個中文字串鍵 | 檢查英文字串表 | 每個鍵都有非空的英文對應；英文字串不含中文字；英文頁面（`?lang=en`）所有新增文字都是英文 | 自動：`T` |
| D16 | 裁決 1 | 例外 | 開設定頁 | 檢查中欄的表單與輸入 | 中欄除了本任務的登記／移除表單（送往 `/settings/pipelines`）外沒有其他表單，沒有權杖清單 action；頁面最外層只有登出一個表單；`POST /settings` 仍回 405；沒有登入時仍導向 `/login` | 自動：`test_web_settings.py::test_st08_still_read_only`（只放寬為允許本任務表單）與 `T` |
| D17 | backend 守則（跨使用者讀） | 例外 | ann、ben 各有環境與登記 | ben 開 `/settings`；ann 開 `/settings` | 各自只看到自己的環境、登記與表單；ann 的環境名稱與登記不出現在 ben 的頁面，反之亦然 | 自動：`T` |
| D18 | 作法 4（`g_reg_bad` 改句） | 功能 | ann-ce 有一筆登記；`/launch` 第 3 步選了另一個未登記的版本 | 開 `/launch` | 提示為「此管線版本尚未在所選運算環境登記，請先至設定頁登記。」；`?lang=en` 為「This pipeline version is not registered on the selected compute environment. Register it on the Settings page first.」；設定頁連結仍在 | 自動：`test_web_board.py` 與 `T` |
| D19 | 計畫「範圍：檔案」docs | 功能 | 讀文件 | 檢查 `docs/PLATFORM.md`、`docs/SETTINGS.md` | `PLATFORM.md` 原「設定頁唯讀」一段已改為說明可從網頁登記／移除管線；`SETTINGS.md` 的 `sitePipelines` 附近新增「從網頁登記」說明，兩處與實際行為一致 | 手動：閱卷者讀文件 |
| D20 | 計畫「範圍：檔案」docs/TESTING.md | 功能 | 讀文件 | 檢查 `docs/TESTING.md` | 新增一節手動項目，逐條包含：390 px 寬無橫向捲動、Tab 鍵焦點外框、中英各看一次、在真站台登記一次並看使用前檢查結果；每條步驟具體到可照做 | 手動：閱卷者讀文件 |
| D21 | 專長守則（手機可用） | 功能 | 瀏覽器視窗 390 px 寬，開設定頁與確認頁 | 上下左右捲動 | 沒有橫向捲軸；按鈕與輸入欄可點、不被切掉 | 手動：`docs/TESTING.md` 新增節 |
| D22 | 專長守則（鍵盤、焦點外框） | 功能 | 開設定頁 | 只用 Tab 鍵走過登記表單、移除鈕、確認頁的按鈕 | 每個可操作項目取得焦點時有看得見的外框 | 手動：`docs/TESTING.md` 新增節 |
| D23 | 原話 5；專長守則 | 功能 | 中文與 `?lang=en` 各開一次 | 看設定頁、確認頁、通知 | 兩種語言版面都完整、沒有殘留另一種語言的新字串 | 手動：`docs/TESTING.md` 新增節 |
| D24 | 原話 1；目標 | 功能 | 一個真實站台（維護者的國網或租用伺服器），站台上已用 `module` 裝好某 nf-core 管線版本 | 在設定頁登記，按確認，等代理回報 | 登記出現在清單；使用前檢查有結果；`/launch` 第 3 步選該版本時不再顯示「尚未登記」 | 手動：`docs/TESTING.md` 新增節（維護者執行） |

## 6. 空清單語意與 `/launch`（計畫失敗先行測試「空清單語意」；裁決 5）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| E01 | 目標；原話 1 | 功能 | ann-ce 登記清單為空，`/launch` 選 `nf-core/ampliseq 2.18.0` | 經網頁兩步登記該版本後開 `/launch` 並選同一版本 | 第 3 步不再顯示「尚未登記」提示（`g_reg_bad`）；POST 送出不被 `e_reg` 拒絕 | 自動：`T` |
| E02 | 計畫失敗先行測試 | 功能 | 同 E01 登記完成後 | `/launch` 改選同環境的另一個未登記版本（例如 `2.17.0`） | 出現新的 `g_reg_bad` 提示 | 自動：`T` |
| E03 | 計畫失敗先行測試 | 功能 | ann-ce 已有一筆；`/launch` 選另一個版本，目前顯示 `g_reg_bad` | 登記第二筆（就是那個版本）後再開 `/launch` | 該版本不再出現 `g_reg_bad` | 自動：`T` |
| E04 | 計畫失敗先行測試 | 功能 | ann-ce 只有一筆；`/launch` 選任一未登記版本，目前顯示 `g_reg_bad` | 移除最後一筆後再開 `/launch` | 任何版本都不再顯示 `g_reg_bad`，POST 送出不被 `e_reg` 拒絕（回到不需登記） | 自動：`T` |
| E05 | 裁決 5 | 功能 | ann-ce 清單為空 | 登記第一筆後開設定頁；再移除最後一筆後開設定頁 | 登記第一筆後該環境不再顯示裁決 5 的句子；移除最後一筆後句子重新顯示 | 自動：`T` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| X01 | 不做：不新增／刪除運算環境本身 | 不在範圍 | 檢查路由與設定頁 | 列出本任務新增的路由與表單 | 只有 `/settings/pipelines` 與 `/settings/pipelines/confirm` 兩條新路由；沒有新增、刪除或改名運算環境的表單或路由；「新增或修改運算環境」仍是灰色「之後開放」 | 自動：`T` |
| X02 | 不做：不幫使用者裝模組；不從網路查模組清單；平台不開對外連線 | 不在範圍 | 把對外連線（socket）封鎖，記下工作佇列 | 走完登記與移除 | 沒有任何對外連線嘗試；除了登記成功時的一筆預檢外，不排其他工作（沒有安裝、沒有列出模組的工作）；表單沒有由網路填入的模組下拉清單 | 自動：`T` |
| X03 | 不做：不改驗證規則、不放寬 | 不在範圍 | 比對 base | 比較 `compute_envs.py` 的驗證（`_module_problem`、`_var_problem`、`_check_site_keys` 的 sitePipelines 部分）與既有驗證測試 | 驗證規則與 base 相同（只允許新增小 helper）；既有 `clean()` 驗證測試無任何修改且全綠 | 自動：既有 compute_envs 測試；閱卷者以 `git diff` 比對 |
| X04 | 不做：不新增 MCP 工具（裁決 3） | 不在範圍 | 列出 MCP 伺服器的工具清單 | 與 base 比對 | 工具清單與 base 完全相同；沒有任何 `register`／`remove`／`site_pipeline` 之類的工具 | 自動：`T` |
| X05 | 不做：不動 `e_reg` | 不在範圍 | ann-ce 有登記清單，POST `/launch` 送出一個未登記的版本 | 讀回應 | 錯誤句仍逐字為「所選運算環境尚未登記此管線版本，無法送出。」／「The selected compute environment has not registered this pipeline version; nothing was sent.」；不同於已改的 `g_reg_bad` | 自動：`T` |
| X06 | 計畫「不需要 migration」；原話 3 | 不在範圍 | 比對 base | 比較資料庫結構（所有表與欄位）；用 base 版建出的舊資料庫走完登記 | 資料庫結構與 base 相同，沒有新表、新欄位、新 migration 檔；舊資料庫可完整登記與移除；登記資料存在運算環境自己的設定裡 | 自動：`T` |
| X07 | 範圍：既有釘死測試「只加不刪」；ledger 逐條列 | 不在範圍 | 比對 base 與 `ledger.md` | 檢查 `test_dataset_cli.py`、`test_cleanup_offer.py`、`test_confirm_page.py`、`test_web_board.py`、`test_owner_binding.py`、`test_temp_password.py`、`test_web_parity.py`、`test_actions_layer.py`、`test_web_settings.py::test_st08_still_read_only` 的差異 | 這些檔案只有新增項或（`test_st08` 與 `g_reg_bad` 斷言）計畫裁決 1、作法 4 明寫的改動；沒有刪除、跳過或放寬的斷言；ledger 逐條列出每一處被改的釘死斷言與理由 | 手動：閱卷者以 `git diff` 比對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| K01 | Safety Net「平台每個寫入工具在有人回答前都拒絕；新的寫入工具附自己的拒絕測試」 | 例外 | 新增的 `register_site_pipeline`、`remove_site_pipeline` | 在 `test_actions_layer.py` 檢查拒絕測試 | 兩個動作各有一個拒絕測試（缺管道、非管道物件皆拒絕且資料庫不變），並列入該檔的寫入工具清單，Safety Net 的 Check 欄涵蓋它們 | 自動：`platform/tests/test_actions_layer.py` |
| K02 | Safety Net（不經確認不得寫入）；原則 1 第 2 點（人的管道） | 例外 | 掃描 `web.py` 與 `web_settings.py` 所有路由 | 以語法樹找出呼叫 `register_site_pipeline`／`remove_site_pipeline` 的位置 | 只有第二步 `/settings/pipelines/confirm` 的處理函式呼叫它們，且帶 `actions.PAGE`；第一步與所有 GET 路由不呼叫任何寫入動作（只呼叫 `check_site_pipeline_change`） | 自動：`T` |
| K03 | backend 守則（對等性）；`test_web_parity.py` | 功能 | 動作層公開名稱 | 執行 parity 測試 | `register_site_pipeline`、`remove_site_pipeline` 列在 WEB_ONLY，理由為「寫入需在網頁確認頁確認」；`check_site_pipeline_change` 列在 INTERNAL（或既有的網頁專用唯讀輔助類），理由為「網頁兩步驟的第一步」；其他新增的公開 helper 也各在一張表；四張表聯集等於公開名稱、彼此不重疊 | 自動：`platform/tests/test_web_parity.py` |
| K04 | backend 守則（路由裡不得有第二份邏輯） | 功能 | 檢視 `web.py` 新路由 | 檢查匯入與呼叫 | `web.py`、`web_settings.py` 不匯入 `confirm`、`jobs`、`compute_envs`、`agents`、`status`（parity 測試的 FORBIDDEN_IMPORTS）；驗證、擁有者檢查與預檢都在動作層 | 自動：`platform/tests/test_web_parity.py` 與 `T` |
| K05 | Safety Net（憑證不外洩）；backend 守則（日誌與回應不含密鑰） | 例外 | 走完登記全流程與各種失敗（B05–B13、C03–C09），擷取回應與日誌 | 在其中搜尋 | 回應與日誌不含：登入階段 cookie 值、密碼、任何權杖、堆疊（`Traceback`、`File "`）、`SELECT`／`sqlite`、伺服器內部路徑；CSRF 值只出現在表單 hidden 欄位 | 自動：`T` |
| K06 | backend 守則（錯誤訊息說明發生什麼與怎麼處理） | 例外 | B05–B13、C03–C09 的失敗回應 | 讀訊息 | 欄位錯誤句指出哪一欄與允許的格式；403 頁說明什麼都沒有改並請重新整理頁面再試；動作失敗句說明原因；無一是空白頁或只有狀態碼 | 自動：`T` |
| K07 | 憲法 3（不得有寫死路徑）、1（每個程式標明替代品） | 功能 | 新增與修改的 Python／文件檔 | 執行 `bash tests/no_hardcoded_paths.sh`、`bash tests/scripts_name_their_alternative.sh` | 兩者通過（範例模組名稱 `biology/...` 只作為標籤範例，不被當成寫死路徑；新檔 `T` 與新增程式檔頭有 `# Nothing existing:` 或 `# Not <tool>:` 說明） | 自動：`tests/no_hardcoded_paths.sh`、`tests/scripts_name_their_alternative.sh` |
