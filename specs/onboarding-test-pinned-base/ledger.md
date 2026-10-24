# 移除 test_onboarding_doc 釘死 6061925 的一次性檢查 progress ledger

- [x] 移除 6061925 釘死檢查（完整 clone，`git cat-file -t 6061925` = commit）
  - 修正前 `pytest platform/tests/test_onboarding_doc.py -q`：
    `FAILED platform/tests/test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` / `1 failed, 40 passed in 12.29s`（docs/PLATFORM.md 等與 6061925 有差異）
  - 修正後同指令：`40 passed in 1.22s`
  - 改動：刪 test_tc047…、刪 test_tc045 後半的 base 比對、刪 BASE／_git／import subprocess
