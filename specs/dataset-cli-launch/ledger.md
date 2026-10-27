# 資料集登記指令＋launch 可指定資料集 progress ledger

- [x] `abf-platform dataset register|list|show` (cli.py), `request_launch(dataset=, dataset_version=)` (actions/__init__.py), MCP `launch` passes the two names (mcp_server.py).
- [x] Tests: test_dataset_cli.py (8), test_dataset_launch.py (9), test_datasets.py TC-064 changed per ruling 3 (before: no file names get_dataset; after: exactly one call inside request_launch, nowhere else in that file; reason: this task wires datasets into launch).
- No migration (table unchanged). Note: plan said 13 MCP tools; base has 15, pinned by name in TC-058 test.
