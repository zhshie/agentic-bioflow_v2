# CLI 加 --json／--debug／--version progress ledger

- [x] 測試先行：platform/tests/test_cli_flags.py（TC-001..062），RED a769edaf
- [x] 實作：platform/abf_platform/cliout.py（新）、cli.py（根旗標 --version／--json／--debug、_Parser、_err 加 why／next）
- [x] 允許改的既有測試：test_cli_contract.py::test_documented_gaps（改成陳述現況：根有三旗標、葉沒有 --json／--debug）、__golden__/cli_help_top.txt（只多三行選項）
- [x] docs/PLATFORM.md 新增「Command-line flags」一節
- [x] 相關測試（flags、contract、snapshots、cli、dataset_cli、usage_doc、launch_cli、agent_token_revoke_id）：445 過，只有 test_cli.py::test_tc035 在我的直接 WSL 跑紅，原因是該測試把 HOME 指到空目錄，WSL 的 ~/.local 裝的 starlette 因而 import 不到（環境問題，與本任務無關）；以 abf-fast-suite 全套結果為準，見下。
- 全套：見最後一次執行的結果（abf-fast-suite --retry-failed-once）。
- 已知環境紅：constitution_scope_test.sh（WSL）、test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched。
