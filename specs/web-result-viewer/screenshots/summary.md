# UI 證據（TC-091 至 TC-094、TC-099）

2026-11-08 重拍。上一版 results 與 board 兩組截圖位元組完全相同（同一個畫面），已刪除，改拍真正的預覽頁。
截圖由臨時測試（用既有的 World 夾具起真站台、真 Chromium、axe-core；用完已刪，不在 repo）產生：
真 PNG 檔的預覽頁、含 script 的 HTML 報告預覽頁（iframe 內 script 有跑）、輸出分頁（有預覽連結）、完成頁。
四頁 x 寬度 1440／390 x 語言 zh／en = 16 張。

## axe 結果（本分支）

| 頁 | 嚴重 | 重大 | 中 |
|---|---|---|---|
| preview-png（四種寬度語言組合） | 0 | 0 | 0 |
| preview-report（四種組合） | 0 | 0 | 0 |
| outputs（輸出分頁，四種組合） | meta-refresh 1 | 0 | landmark-unique 2 |
| finished（完成頁，四種組合） | meta-refresh 1 | 0 | landmark-unique 1 |

本任務新增的兩種頁（圖片預覽、報告預覽）axe 零違規。

## meta-refresh 是既有問題，已用基準比對證明

`base-summary.md` 是在基準 d4dd182e（本任務之前）用同一支 `scripts/dev/ui_check.py --start` 跑的：
board 與 results 在八種組合上都有同一筆 critical meta-refresh（`meta[http-equiv="refresh"]`），moderate landmark-unique 也相同。
原因是 `web_board.document(..., refresh=True)` 的看板頁自動重整，基準就有（`git show d4dd182e:platform/abf_platform/web_board.py` 有該行）。
本任務沒有新增任何 meta refresh（新預覽頁無 refresh，只有「等待中」狀態沿用既有檔案頁的重整）。
結論：critical 數量與基準相同，不是本任務引入。是否要另開任務移除自動重整，由維護者決定。

## 其他證據

以下沿用先前紀錄。

