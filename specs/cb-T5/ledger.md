# cb-T5 ledger

Base: origin/v3 62c91293de611d265d8fbf3d0a128bea849be98c

## Disagreements on unchanged code
None: all 49 cases (47 inputs, MAX_PATH equality, non-vacuity) pass on the base. No case dropped, no FINDING of a disagreement.

## Mutation proof (pure test addition; code already right)
Each mutant was applied to the worktree, the new test run, then restored with `git checkout -- <file>`; nothing mutated is committed.
Clean base: `49 passed`.

```
## MUT1: station _PATH_CHARS uses $ instead of \Z (accepts trailing newline)
 platform/abf_station/rules.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
-_PATH_CHARS = re.compile(r"^[A-Za-z0-9_./@+=:,-]+\Z")
+_PATH_CHARS = re.compile(r"^[A-Za-z0-9_./@+=:,-]+$")
FAILED tests/test_path_rules_parity.py::test_same_answer[dotdot_and_newline]
FAILED tests/test_path_rules_parity.py::test_same_answer[trailing_newline] - ...
FAILED tests/test_path_rules_parity.py::test_table_is_not_vacuous - Assertion...
3 failed, 46 passed in 0.10s
## MUT2: platform MAX_PATH 1024 -> 2048
-MAX_PATH = 1024
+MAX_PATH = 2048
FAILED tests/test_path_rules_parity.py::test_max_path_is_the_same - assert 10...
FAILED tests/test_path_rules_parity.py::test_same_answer[len_over_limit] - As...
FAILED tests/test_path_rules_parity.py::test_same_answer[long_and_dotdot] - A...
3 failed, 46 passed in 0.12s
## MUT3: station drops the dotdot check
-    if ".." in value.split("/"):
+    if False:
FAILED tests/test_path_rules_parity.py::test_same_answer[dotdot_absolute_root]
FAILED tests/test_path_rules_parity.py::test_same_answer[dotdot_alone] - Asse...
FAILED tests/test_path_rules_parity.py::test_same_answer[dotdot_leading] - As...
FAILED tests/test_path_rules_parity.py::test_same_answer[dotdot_middle] - Ass...
FAILED tests/test_path_rules_parity.py::test_same_answer[dotdot_trailing] - A...
5 failed, 44 passed in 0.17s
```
