# certifi 升到 2026.10.18（修 pip-audit PYSEC-2026-4320） progress ledger

- [x] 選用版本：certifi==2026.10.18（platform/constraints.txt:5，僅此一行改）。新測試 platform/tests/test_certifi_pin.py（TC-001..005）。
- 開工前 grep（排除 platform/abf_platform/data）：除 constraints.txt:5 外只有 certificate 一詞，無新釘版處。
- `git diff --stat origin/v3 -- .github platform/pip-audit-ignore.txt`：空輸出。
- TC-006/009：未跑 pip-audit（未嘗試連網），以 PR 上 `security` 工作流為準。
- 2026-11-06：已合併 origin/v3（TC-U28 已刪）。全套在 381978fc：第一輪 platform_clock 抖動（重跑 ok）；第二輪 platform_shard_6 逾時，單獨重跑一次 ok（286s）；其餘全綠，共 150/150。
