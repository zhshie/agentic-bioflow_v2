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

## 修正回合（verifier 退回 TC-001／TC-048）
- 問題：`render("abc\n")` 改前也會丟 ValueError（`_quote` -> `_bad_value` 擋換行），舊測試 `pytest.raises(ValueError)` 改前也綠。
- 修法（只動測試）：TC-001 測試改成要求錯誤訊息是名稱檢查那句（`match="名稱不合法"`），並直接斷言 `compose._NAME.match("abc\n") is None`、`compose._NAME.match("abc")` 非 None。改前 `_NAME` 收下 `"abc\n"`，所以改前紅。
- 兩分支比對方式：把四個程式檔換成 base `7bc7e15` 的內容（不是現在已前進的 origin/v3，那裡 datasets.py 多了別的函式，會讓 test_tc063 無關地紅），跑同一份四個測試檔；然後還原。

### 改前（程式檔 = 7bc7e15）
```
== test_compose
FAILED tests/test_compose.py::test_regex_dollar_newline_tc001_pipeline_name_with_newline_is_refused
FAILED tests/test_compose.py::test_regex_dollar_newline_tc002_node_id_with_newline_is_refused
FAILED tests/test_compose.py::test_regex_dollar_newline_tc003_param_key_with_newline_is_refused
FAILED tests/test_compose.py::test_regex_dollar_newline_tc004_output_name_with_newline_is_refused
4 failed, 44 passed
== test_pipelines_validation
FAILED tests/test_pipelines_validation.py::test_regex_dollar_newline_tc010_011_012_name_with_newline_is_refused_and_nothing_is_saved
1 failed, 15 passed
== test_datasets
FAILED tests/test_datasets.py::test_regex_dollar_newline_tc020_021_024_025_names
FAILED tests/test_datasets.py::test_regex_dollar_newline_tc022_023_version
2 failed, 67 passed
== test_name_anchors
FAILED tests/test_name_anchors.py::test_tc030_trailing_newline_identifier_is_refused
1 failed, 2 passed
```
### 改後（本分支）
```
== test_compose            48 passed
== test_pipelines_validation  16 passed
== test_datasets           69 passed
== test_name_anchors        3 passed
```
改前紅：TC-001～004、TC-010～012、TC-020/022（含 024/025/023 同測試函式內的帶換行案例）、TC-030；對照組同函式外的案例全綠。
