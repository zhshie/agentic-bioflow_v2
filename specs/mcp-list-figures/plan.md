# 計畫：MCP 下游引導與「列出圖庫」工具（mcp-list-figures）

本任務沒有獨立 spec.md，計畫即規格。

## 維護者原話（2026-11-14）

1. 「現在abf根本沒辦法讓使用者透過MCP使用內嵌的Rstudio，沒辦法在上面寫R script、產生圖跟打包」
2. 「Rstdio的問題去處理 代表你自己都還沒測試過abf目前到底能否透過MCP真的跑完」
3. 「Rstudio的事情都同意，你去修」

## 實測到的問題（2026-11-14，stdio 連 `abf-platform mcp`，只讀）

- `downstream` 提示詞 21,526 字元，全是外掛的終端機路線（`scripts/env.sh`、`intro.sh`、`inventory_outputs.py`），0 次提到 `publish_figure`、`pack_figures`。聊天客戶端照做會全部失敗。
- AI 發佈圖之後，沒有任何工具能看圖庫現在有什麼；`pack_figures` 要「整組名單」，AI 只能憑記憶給。

## 作法（這一段不動安全網、不動站台、不新增任何寫入路徑）

1. **新增唯讀工具 `list_figures(run_id, packed_only=false)`**：直接呼叫已存在、已有測試的 `actions.list_figures`。別人的分析與不存在的分析回同一句話。不排工作、不寫任何東西。
2. **`skills/downstream/SKILL.md` 加一節「Through the platform's MCP server」**，放在「Before anything else」之前：選分析 → 說明文字會送到哪個模型 → 看結果 → 問使用者要回答什麼 → 讀表 → 在自己能跑程式的地方畫圖並誠實說明在哪裡跑 → `publish_figure` → `list_figures` 核對 → `pack_figures` → 收尾。舊的每一行都保留（`test_tc036_037` 的基準檔規則），新增的行不含任何管線專屬字眼。
3. **路由說明（instructions）加一句**：畫好的圖用 `publish_figure` 進圖庫、`list_figures` 看圖庫；總長仍在 2 KB 內。
4. 同步：`mcp_server.py` 檔頭與說明字串的工具數（唯讀 15 → 16、總數 25 → 26）、`docs/PLATFORM.md`、工具清單快照與所有寫死清單的測試。

## 失敗先行測試

`platform/tests/test_mcp_list_figures.py`：工具存在且唯讀；發佈前為空、發佈並確認後列出名稱、說明與是否在交付包；工具與 action 回覆相同；別人的分析看不到；呼叫不新增工作與確認單；提示詞含 MCP 路線且排在終端機步驟之前；路由說明提到兩個工具且不超過 2 KB。

## 不做（第二段，另案，需維護者對修憲與 ADR 0010 的明確同意）

- AI 交 R script、使用者說「確認」後由站台在資料所在處執行（新的站台工作種類）。
- 平台經登入轉送 RStudio 畫面，讓別台電腦也能開。
- 讀二進位檔、讀超過 25 MB 的表。

## 完成標準

- 平台測試全綠、`tests/run_all.sh` 全綠、CI 綠。
- 部署後以真實 MCP 連線實測：讀表 → 畫圖 → 發佈（本人確認）→ `list_figures` 看到 → 打包 → 完成頁看到。
- 維護者親手試過才算完成。
