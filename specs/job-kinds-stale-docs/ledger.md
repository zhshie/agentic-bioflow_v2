# jobs.py／store.py 註解改成三種寫入類型 progress ledger

- [x] 新測試檔 `platform/tests/test_job_kinds_docs.py`（RED commit）。改字前紅：`jobs.py opening text does not name: ['clean_work']`；`those two kinds` 仍在說明；store 註解 `eight`≠9；對照組 TC-012/013 綠（共 4 failed, 1 passed）。
- [x] 改 `jobs.py`（開頭說明、CONFIRMED 註解、_check_confirmation 說明、Who writes 句）與 `store.py` 註解；改後 5 passed。
- [x] AST 比對（去 docstring）：jobs True、store True。diff 只含 jobs.py、store.py、新測試檔。
