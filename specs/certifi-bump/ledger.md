# certifi 升到 2026.10.18（修 pip-audit PYSEC-2026-4320） progress ledger

- [x] 選用版本：certifi==2026.10.18（platform/constraints.txt:5，僅此一行改）。新測試 platform/tests/test_certifi_pin.py（TC-001..005）。
- 開工前 grep（排除 platform/abf_platform/data）：除 constraints.txt:5 外只有 certificate 一詞，無新釘版處。
- `git diff --stat origin/v3 -- .github platform/pip-audit-ignore.txt`：空輸出。
- TC-006/009：未跑 pip-audit（未嘗試連網），以 PR 上 `security` 工作流為準。
