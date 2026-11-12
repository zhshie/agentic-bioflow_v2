# mcp-gallery-actions：AI 代使用者打包與刪除圖庫中的圖（圖庫第 3 片）

狀態：計畫（lead，2026-11-13）。風險 L（新增寫入類 MCP 工具、動 `confirm.py`、`store.py` 的確認種類遷移）。
前置：`mcp-publish-figure`（第 1 片）與 `mcp-publish-figure-gallery`（第 2 片）及它們各自的修正輪（F1–F8、G1–G5）。本片的分支疊在第 2 片上；第 1、2 片還在修時不得改它們的行為，遇到必須改的就停手回報。

## 維護者原話

1. 2026-11-12：「AI要能夠代使用者完成所有事，包括按按鈕(使用者說"確認"就行)」。這推翻第 2 片計畫裡「打包與刪除不產生任何 MCP 寫入工具」的裁決（原話 7 的選 B 只剩「圖庫只含經確認通道寫入者」仍有效）。
2. 2026-11-12：「以後若使用者要回去拿當時未勾選的項目還是要可以」。打包只改旗標，永不刪圖；只有刪除會讓圖消失。
3. 既有的（第 2 片原話 2）：「具體打包什麼都是使用者跟LLM討論」。

## 目標

lab-agent（使用者自己串接的 LLM）能經 MCP 提出「把這幾張圖設為交付包內容」與「刪除這張圖」，使用者說「確認」之後才生效。網頁上的按鈕照留，兩條路做同一件事、走同一個動作層函式。

## 作法

1. 兩個新的 MCP 工具，都只是「提出申請」，形狀與 `publish_figure` 相同（共用 `_ask`，ELICITED／PAGE／CHAT 三個通道，`request_id`＋`user_confirmed` 只在本人回答後才可帶）：
   - `pack_figures(run_id, names, request_id?, user_confirmed?)`：`names` 是這次要在交付包裡的完整集合（可為空＝清空交付包）。語意與網頁相同：結果＝這個集合。
   - `delete_figure(run_id, name, request_id?, user_confirmed?)`：一次一張。
2. 確認種類：新增一個不建 job 的種類 `gallery_change`（進 `confirm.NO_JOB_KINDS`），bundle 內有 `action`（`pack`｜`delete`）、`run_id`、名稱清單、以及申請當下算出的「會發生什麼」：
   - pack：哪些圖會被加入、哪些會被移出（移出的仍留在圖庫）、哪些不變。
   - delete：哪張圖、是否目前在交付包內、會一併刪掉它的程式碼檔與參數檔。
   確認畫面（表單、確認頁、聊天摘要；中、英）照 bundle 顯示這些，文字為正式書面語。bundle 很小（只有名稱），不含圖的內容。
3. 核准時（`approve` 的 writer 分支）：
   - 重新讀圖庫，重算「會發生什麼」；與畫面顯示的不同（例如期間有圖被刪、被取代、被別的打包改過）就拒絕、什麼都不改，請 LLM 重新提出。
   - 通過才呼叫第 2 片既有的動作層函式 `pack_figures`／`delete_figure`，持有第 2 片 G1 的那把圖庫鎖。
   - 擁有者檢查與「別人的與不存在的同一句答覆」照 `publish_figure`。
4. 遷移：`_migrate_confirmation_kinds` 加入 `gallery_change`，作法與第 1 片相同（單一交易、失敗回滾、連跑兩次結果相同、舊列不變、jobs 的 CHECK 不變）。
5. 工具清單類的釘住測試全部同步（工具數 23→25；唯讀工具數不變）。第 1 片驗收時漏掉的那一組釘住測試清單在第 1 片計畫的 F1，這次一開始就照那份清單同步。
6. 瀏覽器內建聊天（`chat_tools.py`）：本片不提供這兩個工具，與 `publish_figure` 一致。是否提供列入晨報請維護者決定。
7. 文件：`docs/PLATFORM.md`（兩個工具、確認種類、語意）、`docs/TESTING.md`（手動步驟）、`CHANGELOG.md`。工具描述寫明：只有本人回答後才可帶 `user_confirmed`；打包是「設為這個集合」，沒列到的會移出但不會被刪。

## 範圍（可改的檔）

`platform/abf_platform/actions/figures.py`、`actions/__init__.py`、`mcp_server.py`（或工具註冊所在處）、`confirm.py`（只加種類與 writer 分支）、`store.py`（只加遷移中的種類）、確認頁渲染所在檔（只加 `gallery_change` 的畫面）、`docs/`、`CHANGELOG.md`、`platform/tests/`、`specs/mcp-gallery-actions/`。

## 不做

- 不改網頁按鈕的行為與第 2 片的路由。
- 不新增「一次刪多張」、不新增復原刪除。
- 不讓任何通道在本人回答前寫入；不改確認逾時；不改既有種類（launch、cancel、resume、relaunch、clean_work、forget、publish_figure）的路徑。
- 不碰 `.github/`、`hooks/`、憲法、`plugin.json`、`platform/abf_station/`、`jobs.py`、CSS。
- 不新增相依。

## 驗收以此為準（例子）

1. LLM 提出打包 a、b（圖庫有 a、b、c，原本 c 在包內）→ 畫面寫明「加入 a、b；移出 c（仍留在圖庫）」→ 使用者說「確認」→ 交付包恰為 a、b，c 仍在圖庫、仍可下載，之後可再打包回來。
2. LLM 提出刪除 a → 畫面寫明會刪 a 與它的程式碼、參數，且 a 目前在交付包內 → 使用者沒回答、過了時限 → 什麼都沒變。
3. LLM 自己帶 `user_confirmed=true` 而沒有先提出、或帶別人的 `request_id`、或內容與提出時不同 → 拒絕，什麼都沒變。
4. 提出之後、確認之前，使用者在網頁上先刪了 b → 確認時拒絕並說明圖庫已變動，請重新提出。
5. 另一位使用者對這個 run 提出 → 與 run 不存在同一句答覆。
6. 網頁按鈕與 MCP 工具對同一個圖庫交錯操作，結果與依序操作相同（沒有遺失更新）。

## 測試怎麼做

- 先寫會失敗的測試；動作層、確認通道三個通道、遷移、工具清單同步、畫面中英文、跨使用者、重放、競爭各有案例。
- L 級證明寫進 ledger：`confirm.py`／`store.py` 改了哪幾行與原因、既有種類不受影響的證據（它們的既有測試）、遷移前後的實際輸出、`confirmations.kind` 每個讀寫位置的清單。
- 全套 `bash tests/run_all.sh` 綠（以 PR 上的 CI 為準）。

## 裁決（lead，2026-11-13，回應 verifier R1–R7、P1–P10）

R1 範圍加入 `platform/abf_platform/actions/chat_tools.py` 與 `platform/tests/test_chat_tools.py`：兩個新工具加進 `CHAT_EXCLUDED`，只增這一項排除。
R2 依維護者 2026-11-12 的話（「AI要能夠代使用者完成所有事，包括按按鈕」），點名放寬第 2 片的這幾處，且只放寬「`pack_figures`、`delete_figure` 不是工具」這一點：`test_actions_layer.py` 的 `test_gallery_page_actions_exist_in_the_action_layer_and_are_not_tools`（改為「是經確認通道的寫入工具」，工具數 25）、第 2 片 TC-057／TC-078 對應的斷言。`read_figure` 仍不是工具；`test_web_figures.py` 的 `not hasattr(actions, "pack_figures")` 不放寬，所以新的請求函式命名為 `request_pack_figures`、`request_delete_figure`。
R3 writer 依確認種類挑選（三處：CHAT、ELICITED、PAGE），`publish_figure` 仍走原本的 writer。
R4 核准時的「重新檢查＋寫入」在同一次持有圖庫鎖之內完成，並呼叫第 2 片的同一個核心函式。
R5 申請時的快照含每張圖的識別（`created` 與存入它的 `request_id`），同名被取代也算圖庫已變動。
R6／P4 三個通道在圖庫已變動時都說「圖庫已變動，請重新提出」。
R7／P6 沒有任何影響的申請不建申請列，回「沒有需要變更」。
P1 一個種類 `gallery_change`。P2 清空交付包多一行醒目說明，不多一道確認。P3 刪除包內的圖不拒絕，畫面明說。P5 整份「會發生什麼」與畫面不同就拒絕，含期間多了不相干的新圖。P7 `delete_figure` 標破壞性。P8、P9、P10 照建議。
開工條件：第 1 片 F1–F8 與第 2 片 G1–G5 都已併入本分支之後才派 executor。
