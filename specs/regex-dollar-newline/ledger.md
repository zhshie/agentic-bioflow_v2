# regex-dollar-newline progress ledger

- [x] 七條正規式結尾 `$` -> `\Z`（compose `_ID/_NAME/_KEY/_IDENT`、pipelines `_NAME`、datasets `_NAME`、build `OWNER_NAME`）；其餘字元不動。
- [x] 新測試加進 test_compose.py、test_pipelines_validation.py、test_datasets.py，新建 test_name_anchors.py（build 沒有合適的既有檔）。

## 改前（只有測試、程式未改）紅的輸出
- test_compose: FAILED tc002 (graph was accepted), tc003 (DID NOT RAISE), tc004 (DID NOT RAISE)；3 failed, 45 passed
- test_pipelines_validation: FAILED tc010_011_012；1 failed, 15 passed
- test_datasets: FAILED tc020_021_024_025, tc022_023；2 failed, 67 passed
- test_name_anchors: FAILED tc030 (DID NOT RAISE Refusal)；1 failed, 2 passed
改前紅的都是帶換行的案例；對照組（TC-005..009、013、021、023、025、031、032、050）全綠。

## 改後
compose 48 passed；pipelines_validation 16 passed；datasets 69 passed；name_anchors 3 passed。

## 注意
- 計畫的 TC-012/TC-024 的訊息相同比對已寫進測試（"abc\n" 與 "ABC"、`"a"*64+"\n"` 與 "a b"）。
- 兩分支比對：改前（RED commit，程式為 origin/v3 內容）與改後的輸出如上。
- 後續：未見其他疑似閘門。
