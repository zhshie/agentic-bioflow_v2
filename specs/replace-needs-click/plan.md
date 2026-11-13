# replace-needs-click：存圖若會蓋掉圖庫中既有的圖，必須由本人在表單或確認頁按下確認

狀態：計畫（lead，2026-11-13）。風險 L（確認通道對一種情況的核准條件；安全網只收緊）。
前置：`delete-needs-click`（已在 v3）。本案是同一條規則的延伸，作法比照該案。

## 維護者原話

1. 2026-11-12：「AI要能夠代使用者完成所有事，包括按按鈕(使用者說"確認"就行)」。
2. 2026-11-13：對「刪除必須經表單或確認頁」答「好」。
3. 2026-11-13：lead 說明「AI 用同名檔案存圖會蓋掉舊圖、移除它的程式碼與參數檔，救不回來，實質上是刪除，目前不需要本人按鈕」，提出做法一「存圖如果會蓋掉既有的圖，就比照刪除，必須在表單或確認頁按下確認；存新圖維持說確認就行」，維護者答：「選『一』」。

## 為什麼

`delete-needs-click` 的對抗審（發現 1，已實測）：`publish_figure` 以既有檔名提出，再帶 `request_id`＋`user_confirmed=true` 轉達，舊圖的內容被換掉、`.code.txt`／`.params.txt` 被移除，無法復原。

## 做什麼

1. `publish_figure` 的申請若在提出當下會取代圖庫中既有的圖（bundle 的 `replaces` 非空），只能由 ELICITED 或 PAGE 核准。
2. 這種申請經對話轉達（CHAT）一律拒絕：不寫入任何東西，申請維持待確認、不作廢、不消耗；答覆以正式書面語說明「這次存入會取代圖庫中既有的圖，原圖無法復原，須由本人在確認頁按下確認」，附該筆申請的確認頁網址。網址只給呼叫者自己的、仍在等待中的、內容相同的申請（比照 delete-needs-click 的 Q1）。中、英。
3. 這種申請第一次提出時的答覆只指向確認頁，不告訴 LLM 可以轉達。
4. 核准時才發現會取代（提出時該名稱還不存在，之後才有同名的圖）：既有行為是 N4 的識別比對，不同即拒絕（409／「圖庫已變動」）；確認這條路在 CHAT 上不會造成取代，若會，則同樣拒絕。
5. 不會取代任何圖的存圖（新名稱）維持現狀：對話轉達可用。
6. `publish_figure` 的工具描述與參數說明照實補一句：取代既有的圖時 `user_confirmed` 無效。
7. RStudio 的 `publish-figure` 指令本來就不帶 `user_confirmed`、只印確認連結，不受影響；確認它的說明文字仍然正確。
8. `pack_figures`、`delete_figure` 與其他所有種類行為一字不動。
9. 文件：`docs/PLATFORM.md`、`docs/TESTING.md`、`CHANGELOG.md`。

## 範圍（可改的檔）

`platform/abf_platform/actions/__init__.py`、`actions/figures.py`、`mcp_server.py`、`docs/`、`CHANGELOG.md`、`platform/tests/`、`specs/replace-needs-click/`。`confirm.py`、`store.py` 預期不需要改；若必須改，停手回報。

## 不做

- 不保留被取代的舊版本（維護者選了做法一，不是做法二）。
- 不改其他種類、逾時、待確認上限；不新增路由、相依。
- 不碰 `.github/`、`hooks/`、憲法、`plugin.json`、`platform/abf_station/`、`jobs.py`、CSS。

## 驗收以此為準（例子）

1. 圖庫已有 a.png。LLM 以 a.png 提出存圖，接著自己帶 `request_id`＋`user_confirmed=true` → 拒絕；a.png 的內容、程式碼檔、參數檔逐位元組不變；答覆含確認頁網址。之後本人在確認頁按確認 → a.png 被新圖取代。
2. LLM 以新名稱 new.png 提出存圖，本人在聊天回答後 LLM 轉達 → 照常存入（與現在相同）。
3. 本人在用戶端表單按確認取代 a.png → 取代成功（與現在相同）。
4. 反覆轉達取代申請 30 次 → a.png 不變，申請仍可由本人在確認頁核准或逾時。
5. 以 new.png 提出（當時不存在），之後有人存了同名的 new.png，LLM 再轉達 → 既有的圖不被取代。
6. 別人的、別種的 `request_id` → 與現在相同的拒絕，不帶網址。

## 測試怎麼做

先寫會失敗的測試；三個通道各有案例；其他種類以既有測試為證；被反轉的既有測試由合約逐條點名，只准改那些；L 級證明寫進 ledger。全套以 PR 上的 CI 為準（含 `platform/tests/mcp/`，該目錄在 `fable/mcp-tests-in-ci` 合併前不在 CI 內，須在本機跑到實際結果）。

## 裁決（lead，2026-11-13，回應 verifier Q1–Q9）

Q1–Q9 全部照 verifier 的建議答案（原文在 `test-case-overview.md`「我不確定的地方」）。要點：
Q1 計畫第 4 點不改程式，只加測試釘住既有行為（CHAT 為 refused 並作廢，PAGE 為 409）。
Q2 拒絕答覆把確認頁網址放進 `url`。
Q3 `publish_figure` 描述重寫並維持在 600 字內，不新增任何豁免清單項目。
Q4 `publish_figure` 用自己的兩段參數說明，共用字串不動。
Q5 邊界比照 delete-needs-click 的 Q1–Q4。
Q6 以申請當時 bundle 的 `replaces` 判斷；清單中有一個名稱會取代，整份申請只能由表單或確認頁核准。
Q7 `publish_figure` 的工具標註本案不改，ledger 記為已知限制，是否改列入給維護者的問題。
Q8 沒有可反轉的既有測試；既有檔只准改 `tools.json` 中 publish_figure 的兩段參數說明（R1）。發現還有別的非改不可，停手回報。
Q9 `_ask` 只在 publish_figure 且 `replaces` 非空時多一道只讀攔截；`confirm.py`、`store.py` 不動。
