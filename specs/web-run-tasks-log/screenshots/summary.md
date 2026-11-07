# ui_check summary

Base: http://127.0.0.1:44087  |  2026-11-07 13:15

| page | width | lang | HTTP | critical | serious | moderate | minor |
|---|---|---|---|---|---|---|---|
| board | 1440 | zh | 200 | 1 | 0 | 1 | 0 |
| results | 1440 | zh | 200 | 1 | 0 | 1 | 0 |
| board | 1440 | en | 200 | 1 | 0 | 1 | 0 |
| results | 1440 | en | 200 | 1 | 0 | 1 | 0 |
| board | 390 | zh | 200 | 1 | 0 | 1 | 0 |
| results | 390 | zh | 200 | 1 | 0 | 1 | 0 |
| board | 390 | en | 200 | 1 | 0 | 1 | 0 |
| results | 390 | en | 200 | 1 | 0 | 1 | 0 |

## Serious / critical violations

- **critical** meta-refresh (1440, zh) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (1440, zh) - results - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (1440, en) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (1440, en) - results - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, zh) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, zh) - results - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, en) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, en) - results - 1 node(s), e.g. meta[http-equiv="refresh"]

## Screenshots (8)

- board-1440-zh.png
- results-1440-zh.png
- board-1440-en.png
- results-1440-en.png
- board-390-zh.png
- results-390-zh.png
- board-390-en.png
- results-390-en.png

## 各頁改動（白話）

- board：分析頁的「任務」分頁失敗任務列多一格「日誌」連結，「日誌」分頁不再是灰色「之後開放」。
- results：結果頁的「日誌」分頁同樣列出失敗任務並附錯誤／輸出／全部三個連結。
- 備註：種子資料的 run 沒有失敗任務，截圖只看得到頁面外框；新的 /run/log 整頁未被截圖。
- axe：8 筆 critical 全是 meta-refresh（頁面自動 15 秒刷新，既有設計），非本任務新增。
