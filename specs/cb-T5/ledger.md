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

## Full suite, first run at 80381d07 (before the fix below)
`platform_test.sh` failed `test_scope.py::test_tc072_no_personal_or_cluster_paths`: my test table used `/work/<name>/` paths, which match the repo's no-hardcoded-paths pattern (`/work/run1/`, `/work/a..b/c`). Fixed by using `/data/...` in the test table (same inputs otherwise, 49 passed again).

## Environment / pre-existing failures (also fail in the T3 and T4 full runs on this VM)
agent_ctl_connection_id_test, why_pending_test, wsl_bridge_test, platform_clock_test, platform_shard_4/6/7 (and shard_5 in T3/T4).
`platform_upgrade_test.sh` TC-U28 ("platform/ ... untouched since the merge base with origin/v3") fails for ANY commit that touches platform/, including this one: FINDING, not fixed (tests/ not in scope).

## Full suite at 90bb3ee072910b4bb577d6fca17441464863fcfc (not green locally)
133/141 passed, 8 failed: the 7 environment failures listed above plus platform_upgrade_test.sh (TC-U28, finding). platform_test.sh now passes. Last 20 lines:
```
FAIL       agent          not running - Platform will show no outputs (scripts/on_site.sh --script scripts/agent_ctl.sh start)
FAIL       resources      tar: Child returned status 141
FAIL       compute-env    ce is 'unreachable'>>
missing rsync on MSYS is FAILed by name                    ok
and it says plainly that Git Bash ships none               ok
and gives an install route rather than nothing             ok

-- (i) install_deps.sh: tw on MSYS is named plainly, not folded into 'unknown platform' --
install_deps.sh --cli-only fails cleanly, not silently     ok
it names the gap as unmeasured (R4), a real answer         ok
and gives the Windows asset to fetch by hand               ok
it does not fall back to the generic unknown-platform text ok
shim does not run wsl.exe from the caller's own cwd        ok
and lands in a directory that exists                       ok
only settings.sh decides whether the bridge is in play     ok
and nothing hardcodes the control-path default beside it   ok

3 failed

133/141 passed, 8 failed
```
