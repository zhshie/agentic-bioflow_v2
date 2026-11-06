# cb-D1 ledger

## RED (unchanged su.py, base 62c91293)
```
tests/test_su_finite.py:135: AssertionError
=========================== short test summary info ============================
FAILED tests/test_su_finite.py::test_number_rejects_non_finite[nan] - Asserti...
FAILED tests/test_su_finite.py::test_number_rejects_non_finite[inf] - Asserti...
FAILED tests/test_su_finite.py::test_number_rejects_non_finite[-inf] - Assert...
FAILED tests/test_su_finite.py::test_non_finite_money_rate_gives_none_not_nan[NaN]
FAILED tests/test_su_finite.py::test_non_finite_money_rate_gives_none_not_nan[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_money_rate_gives_none_not_nan[-Infinity]
FAILED tests/test_su_finite.py::test_non_finite_site_price_gives_none[NaN] - ...
FAILED tests/test_su_finite.py::test_non_finite_site_price_gives_none[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_site_price_gives_none[-Infinity]
FAILED tests/test_su_finite.py::test_non_finite_factor_is_unknown[NaN] - asse...
FAILED tests/test_su_finite.py::test_non_finite_factor_is_unknown[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_factor_is_unknown[-Infinity]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[cpus-nan]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[cpus-inf]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[realtime-nan]
FAILED tests/test_su_finite.py::test_non_finite_task_value_is_unknown[realtime-inf]
FAILED tests/test_su_finite.py::test_non_finite_usd_rate_is_none[Infinity] - ...
FAILED tests/test_su_finite.py::test_non_finite_price_or_su_gives_no_dollars[NaN]
FAILED tests/test_su_finite.py::test_non_finite_price_or_su_gives_no_dollars[Infinity]
FAILED tests/test_su_finite.py::test_non_finite_price_or_su_gives_no_dollars[-Infinity]
FAILED tests/test_su_finite.py::test_the_finite_check_is_the_one_in_cloud_cost
21 failed, 15 passed in 3.06s
```

## GREEN (su.py changed; HEAD below is the commit before this ledger entry)
test_su_finite.py: 36 passed. test_estimate_su, test_su_in_get_run, test_su_packaged, test_su_usd, test_cloud_cost, test_cloud_wire: all passed.
Not green locally: run_all.sh 132/141 passed, 9 failed. 8 of them fail identically on the unrelated T6 checkout (no platform/ change): agent_ctl_connection_id (USER unbound), platform_clock, platform_shard_4/5/6/7 (missing httpx in venv, snapshot, read-only-cache-as-root), why_pending, wsl_bridge.
The 9th is platform_upgrade_test.sh TC-U28 "platform/ ... untouched": it fails for any branch that touches platform/ (also T5), and tests/ is outside this task's files. FINDING.
run_all tail:
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

132/141 passed, 9 failed
```
