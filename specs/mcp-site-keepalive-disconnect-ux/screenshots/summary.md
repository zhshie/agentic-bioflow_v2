# ui_check summary

Base: http://127.0.0.1:33323  |  2026-11-12 17:17

| page | width | lang | HTTP | critical | serious | moderate | minor |
|---|---|---|---|---|---|---|---|
| board | 1440 | zh | 200 | 1 | 0 | 1 | 0 |
| launch | 1440 | zh | 200 | 0 | 0 | 1 | 0 |
| settings | 1440 | zh | 200 | 0 | 0 | 1 | 0 |
| board | 1440 | en | 200 | 1 | 0 | 1 | 0 |
| launch | 1440 | en | 200 | 0 | 0 | 1 | 0 |
| settings | 1440 | en | 200 | 0 | 0 | 1 | 0 |
| board | 390 | zh | 200 | 1 | 0 | 1 | 0 |
| launch | 390 | zh | 200 | 0 | 0 | 1 | 0 |
| settings | 390 | zh | 200 | 0 | 0 | 1 | 0 |
| board | 390 | en | 200 | 1 | 0 | 1 | 0 |
| launch | 390 | en | 200 | 0 | 0 | 1 | 0 |
| settings | 390 | en | 200 | 0 | 0 | 1 | 0 |

## Serious / critical violations

- **critical** meta-refresh (1440, zh) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (1440, en) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, zh) - board - 1 node(s), e.g. meta[http-equiv="refresh"]
- **critical** meta-refresh (390, en) - board - 1 node(s), e.g. meta[http-equiv="refresh"]

## Screenshots (12)

- board-1440-zh.png
- launch-1440-zh.png
- settings-1440-zh.png
- board-1440-en.png
- launch-1440-en.png
- settings-1440-en.png
- board-390-zh.png
- launch-390-zh.png
- settings-390-zh.png
- board-390-en.png
- launch-390-en.png
- settings-390-en.png

## 各頁變更（中文）
- board：看板加入連線中斷的紅色提示並擋新送出（meta-refresh 違規為既有的自動重整，非本次新增）。
- launch：送出前檢查連線狀態，掉線時擋下。
- settings：連線狀態文字隨保活結果更新。

## meta-refresh 是既有的，不是本件新增（對照 base 9ae086b2）
- base `platform/abf_platform/web_board.py:956` 已有 `<meta http-equiv="refresh" ...>`，base `platform/tests/test_web_board.py:923` 就斷言它存在；`git diff 9ae086b2 HEAD -- web_board.py` 沒有動 `document()` 裡的 refresh 邏輯。
- base 上的 axe 結果已記在 `docs/reports/cloud-burn-2026-11/UI2.md`：board 在 1440／390 × zh／en 各有 1 個 critical `meta-refresh`，同一規則、同一節點；`docs/TESTING.md:1060` 寫明「note it, do not count it」。
- 本件新增的紅條 `.linkbar` 沒有任何 serious／critical 違規。
