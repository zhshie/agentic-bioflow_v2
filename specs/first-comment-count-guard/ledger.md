# mcp_server.py 第一行註解的工具數字改由測試算出真實數字比對 progress ledger

## 進度（executor, 20261030-0640-L46b）
- [x] 全部完成。只改 `platform/tests/test_mcp_server_doc.py`；`mcp_server.py` 未動（突變已 `git checkout` 還原）。

### 空殼先紅（TC-014）
`_first_line_problems` 先寫成 `return []`：`6 failed, 6 passed`。紅：stale_count_ten（TC-001）、old_six_seven（TC-002）、missing_count（TC-003）、count_not_next_to_read_only（TC-005）、extra_wrong_number_word（TC-006）、n_out_of_range（TC-008）；綠：accepts_matching_count（TC-004）、accepts_six_when_n_is_six（TC-007）與其他既有測試。（commit `RED:`）實作後 `12 passed`。

### 突變證明（TC-012/013/020），一次性，已還原
第 1 行 `fifteen read-only` 換成錯字，同時跑新測試檔與舊版（`origin/v3` 的測試檔，暫存為 test_old_doc_tmp.py 後刪除）：
- ten：新 `test_first_comment_line_does_not_name_an_old_count` 紅；舊版綠（舊護欄漏掉）。
- six：新紅；舊也紅。
- seven：新紅；舊也紅（舊護欄擋得住的新版都擋）。

### 為什麼新版比舊斷言 `"six" not in first and "seven" not in first` 更嚴（TC-019）
1. 舊：只擋 six、seven 兩字。新：第 1 行不得含 NUMBERS 內任何值 ≠ n 的數字字（six、seven 在 n≠6、7 時都被擋，另加 ten～fourteen）。
2. 舊：沒數字字也過。新：必須有緊接 `read-only` 的數字字。
3. 舊：不比對實際數量。新：該數字字必須等於以 `ast` 算出的 `_READ_ONLY` 工具數。
4. 舊在 n=6 或 7 時會誤紅；新在數字字等於 n 時放行。
5. n 超出 NUMBERS 時紅並提示「請擴 NUMBERS」。NUMBERS 未動（n=15 在表內）。

n 由 `_read_only_count()` 以 `_tools()` 算，與 `test_module_doc_counts_the_read_only_tools` 同算法，未寫死。其他既有測試與 NUMBERS／EXPECTED 一字未動。
