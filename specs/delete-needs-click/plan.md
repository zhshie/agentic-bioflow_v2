# delete-needs-click：刪除圖庫中的圖，必須由本人在表單或確認頁上按下確認

狀態：計畫（lead，2026-11-13）。風險 L（動確認通道對一個種類的核准條件；安全網只收緊、不放寬）。
前置：`mcp-gallery-actions`（圖庫第 3 片，已在 v3）。

## 維護者原話

1. 2026-11-12：「AI要能夠代使用者完成所有事，包括按按鈕(使用者說"確認"就行)」。
2. 2026-11-13：lead 說明「刪除不能復原，而平台分不出『本人說了確認』與『AI 自己說本人確認了』；建議只有刪除改成必須經表單或確認頁，打包維持現狀」，維護者答：「好」。

## 為什麼

圖庫第 3 片的對抗審（發現 1，已實測）：`delete_figure(run, name)` 取得 `request_id` 後，再呼叫一次帶 `request_id` 與 `user_confirmed=true` 就會刪除，平台無從分辨這個「確認」是不是本人說的。存圖與打包可以挽回，刪除不行。

## 做什麼

1. `gallery_change` 且 `action=delete` 的申請，只能由 ELICITED（用戶端表單）或 PAGE（確認頁，本人登入後按下）核准。
2. 經對話轉達（CHAT：同一工具再帶 `request_id`＋`user_confirmed=true`）一律拒絕，不刪任何東西，申請維持待確認、不作廢、不消耗；答覆用正式書面語說明「刪除無法復原，須由本人在確認頁按下確認」並附上該筆申請的確認頁網址（與第一次提出時給的相同）。中、英。
3. 第一次提出刪除時（用戶端不支援表單的情況）的答覆也改為只指向確認頁，不再告訴 LLM 可以帶 `user_confirmed` 轉達。
4. `delete_figure` 的工具描述與參數說明照實改寫：`user_confirmed` 對刪除無效。參數仍保留在 schema 中或移除，由實作時以「既有釘住測試改動最少且描述不說謊」為準，在 ledger 說明選擇。
5. `pack_figures`、`publish_figure` 與其他所有種類（launch、cancel、resume、relaunch、clean_work、forget）行為一字不動。
6. 文件：`docs/PLATFORM.md`（該工具與確認通道的段落）、`docs/TESTING.md`（第 3 片手動步驟中刪除的那一條改為「在確認頁按確認」）、`CHANGELOG.md`。

## 範圍（可改的檔）

`platform/abf_platform/actions/__init__.py`、`actions/figures.py`、`mcp_server.py`、`docs/`、`CHANGELOG.md`、`platform/tests/`、`specs/delete-needs-click/`。`confirm.py`、`store.py` 預期不需要改；若必須改，停手回報。

## 不做

- 不改其他種類與其他工具；不改確認逾時、待確認上限；不新增路由、不新增相依。
- 不碰 `.github/`、`hooks/`、憲法、`plugin.json`、`platform/abf_station/`、`jobs.py`、CSS。
- 瀏覽器內建聊天仍不提供這兩個工具。

## 驗收以此為準（例子）

1. LLM 提出刪除 a，接著自己帶 `request_id`＋`user_confirmed=true` 再呼叫 → 拒絕，a 仍在、程式碼與參數檔仍在，答覆含確認頁網址；之後本人在確認頁按確認 → a 被刪除。
2. 本人在用戶端表單按確認 → a 被刪除（與現在相同）。
3. LLM 對打包帶 `request_id`＋`user_confirmed=true`（本人已回答）→ 照常生效（與現在相同）。
4. 反覆以對話轉達刪除 30 次 → 一張圖都沒少，申請仍可由本人在確認頁核准或等它逾時。
5. 另一位使用者的 `request_id`、其他種類的 `request_id` → 與現在相同的拒絕。

## 測試怎麼做

先寫會失敗的測試；三個通道各有案例；其他種類不受影響以它們既有的測試為證；L 級證明（改了哪幾行、為什麼不需動 `confirm.py`）寫進 ledger。全套以 PR 上的 CI 為準。

## 裁決（lead，2026-11-13，回應 verifier Q1–Q7）

Q1–Q7 全部照 verifier 的建議答案：
Q1 新拒絕與確認頁網址只給「呼叫者自己的、仍在等待中的、內容相同的刪除申請」；別人的、別種的、捏造的、內容改過的、逾時的、作廢的維持現有拒絕、不帶網址。
Q2 已由本人確認過的刪除申請再被轉達，維持現有「先前已經確認並執行過」。
Q3 申請仍在等待但圖庫已變動時，轉達仍得新拒絕、申請維持待確認；「圖庫已變動」由本人在確認頁按下時才看到。
Q4 只帶 `user_confirmed=true`、沒帶 `request_id` 的刪除呼叫：仍拒絕、不建申請列，訊息改為指向確認頁。
Q5 兩個參數保留在 schema，刪除用自己的說明字串（寫明對刪除無效）；打包的說明與快照不動。
Q6 只在 gallery_change 且 action=delete 時換說法，其他種類字串一字不動。
Q7 表單通道不動。
既有測試只准改合約 TC-033 點名的 R1–R6。
