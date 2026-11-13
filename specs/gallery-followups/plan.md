# gallery-followups：圖庫三項後續（維護者 2026-11-13 的決定）

狀態：計畫（lead，2026-11-13）。風險 M（動 `chat_tools.py` 的排除清單、一個工具註記、完成頁一個勾選框；不動 `confirm.py`、`store.py`）。
前置：圖庫第 1–3 片、`delete-needs-click`、`replace-needs-click` 都已在 v3（74416bc4）。

## 維護者原話（2026-11-13）

lead 列了一張決定表請他回答，他答：「5.要 其他按照你建議」。表中與本案有關的三列：

- 第 2 列「已打包的圖，勾選框要不要預設勾著？」lead 建議：要（現在都不勾，沒勾就按打包會清空交付包）。
- 第 5 列「網站內建聊天要不要也能存圖、打包、刪圖？」他答：要。
- 第 7 列「AI 的存圖工具要不要標成具破壞性？」lead 建議：要，因為它可以蓋掉舊圖。

既有且仍有效的規則：刪圖與「會取代既有圖的存圖」只能由本人在表單或確認頁核准；打包與存新圖可以由對話轉達的「確認」核准。

## 做什麼

1. **完成頁的勾選框**（`web_finished.py`）：目前已在交付包內的圖，勾選框預設為勾選；不在包內的不勾。按下「打包所選的圖」的語意不變（結果＝勾選的集合）。第 2 片手動步驟裡「No box is pre-ticked after the press」的那句與對應的既有測試，依本決定點名改寫，只改這一點。旁邊那句說明文字若與新行為不符，同步改（中、英，正式書面語）。
2. **`publish_figure` 的工具註記**（`mcp_server.py`）：`destructive_hint` 改為 True，其餘三個註記不變。所有釘住註記與工具清單快照的測試同步（`platform/tests/mcp/snapshots/tools.json` 與第 3 片 A1 那類釘住測試）。`docs/PLATFORM.md` 列出具破壞性工具的那句補上它。
3. **內建聊天**（`actions/chat_tools.py`）：`publish_figure`、`pack_figures`、`delete_figure` 從 `CHAT_EXCLUDED` 移出，成為內建聊天可用的申請類工具，走與 MCP 相同的 `request_*` 函式與確認通道。
   - 內建聊天裡，使用者說「確認」的轉達，效力與 MCP 的對話轉達完全相同：打包與存新圖生效；刪圖與取代既有圖被拒並給本人確認頁網址。不得為內建聊天另開一條較寬的路。
   - 內建聊天怎麼把圖的位元組交給 `publish_figure`，由 verifier 讀現有程式後在合約裡寫明；若現有聊天通道根本無法傳遞圖檔內容，`publish_figure` 留在排除清單，合約寫明原因，只開放另外兩個，lead 會回報維護者。
   - 釘住「內建聊天不提供這三個工具」的既有測試，依本決定點名改寫。

## 不做

- 不做即時同步（需要在頁面加腳本，與網頁不用腳本的既有規則衝突，等維護者另外決定）。
- 不改確認通道、逾時、其他種類；不碰 `.github/`、`hooks/`、憲法、`plugin.json`、`platform/abf_station/`、`confirm.py`、`store.py`。
- 不新增相依。

## 驗收以此為準（例子）

1. 圖庫有 a（已打包）、b（未打包）→ 開完成頁，a 的框是勾的、b 沒勾 → 什麼都不動直接按打包 → 交付包仍是 a。
2. MCP 用戶端列工具時，`publish_figure` 與 `delete_figure` 都標示具破壞性，`pack_figures` 沒有。
3. 在內建聊天說「把 a、b 放進交付包」→ 出現申請 → 說「確認」→ 生效。
4. 在內建聊天說「刪除 a」→ 說「確認」→ a 還在，回覆給確認頁網址；到確認頁按下才刪。
5. 在內建聊天對別人的分析提出 → 與分析不存在同一句答覆。

## 測試怎麼做

先寫會失敗的測試；既有測試除上面點名的三處外不得放寬；全套以 PR 上的 CI 為準。

## 裁決（lead，2026-11-13，回應 verifier R1–R4）

R1 內建聊天沒有「帶 `user_confirmed` 轉達」這條路（憲法 7.0.0，聊天不給模型那兩個欄位），不新增。內建聊天裡打包的「確認」＝確認視窗上本人自己按的按鈕；`confirm_dialog` 讀懂圖庫工具回的 `url`／`request_id`，只對 `pack_figures`。
R2 `delete_figure` 在內建聊天沒有確認視窗、沒有按鈕，答覆只給確認頁網址，本人到確認頁按下才刪。
R3 聊天系統提示列出兩個新工具並說明刪圖不能在聊天裡確認；`test_chat_confirm.py::test_tcm_53` 的提示釘住是點名改寫的第四處。
R4 `publish_figure` 留在 `CHAT_EXCLUDED`（聊天頁沒有圖的位元組，也沒有工具能取得）；lead 回報維護者。
另：`tools.json` 不含註記，維持一字不動（TC-012）；上面「做什麼」2 裡「快照同步」一語以此為準。可改寫的既有測試以 verifier 報告 B 節清單為限：`test_web_figures.py::test_nothing_in_package_until_pack_pressed`；`test_replace_needs_click.py::test_rnc_the_tool_description_and_parameters_say_a_replace_needs_the_click`（註記那一個斷言）；`test_chat_tools.py` 的 `test_gallery_tools_are_excluded_from_the_browser_chat`、`test_tc001_tc034_*`、`test_tc020_*`、`test_tc052_*`；`test_head_nodefail.py::test_tc046_*`；`test_chat_confirm.py::test_tcm_53_*`（及 327 行的註解）。
