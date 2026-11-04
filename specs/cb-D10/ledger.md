# cb-D10 ledger

## RED (test committed with an empty baseline), `pytest platform/tests/test_no_duplicate_defs.py`
```
>       assert not msg, "\n".join(msg)
E       AssertionError: new duplicate defs (share the function instead of copying it, or, if the name is a convention, whitelist it with a reason):
E           Refusal platform/abf_launch/build.py platform/abf_station/rules.py
E           _no platform/abf_platform/actions/datasets.py platform/abf_platform/actions/pipelines.py
E           _run platform/abf_station/aws_preflight.py platform/abf_station/azure_preflight.py platform/abf_station/gcb_preflight.py platform/abf_station/k8s_preflight.py
E           _shown platform/abf_platform/cloud_cost.py platform/abf_platform/compute_envs.py
E           credentials_path platform/abf_station/aws_preflight.py platform/abf_station/azure_preflight.py platform/abf_station/gcb_preflight.py platform/abf_station/k8s_preflight.py
E           load_rates platform/abf_platform/cloud_cost.py platform/abf_platform/su.py
E           path_problem platform/abf_platform/compute_envs.py platform/abf_station/rules.py
E           say platform/abf_station/agent.py platform/abf_station/cli.py
E       assert not ['new duplicate defs (share the function instead of copying it, or, if the name is a convention, whitelist it with a r...atform/compute_envs.py platform/abf_station/rules.py\n  say platform/abf_station/agent.py platform/abf_station/cli.py']

tests/test_no_duplicate_defs.py:84: AssertionError
=========================== short test summary info ============================
FAILED tests/test_no_duplicate_defs.py::test_no_new_duplicate_defs_and_baseline_only_shrinks
1 failed, 11 passed in 3.50s
```

## Mutation proofs (never committed; production files restored with git checkout)
```
=== MUTANT 2: a 5th copy of credentials_path (growth of a baselined group)
E       AssertionError: new duplicate defs (share the function instead of copying it, or, if the name is a convention, whitelist it with a reason):
E           credentials_path platform/abf_launch/__init__.py platform/abf_station/aws_preflight.py platform/abf_station/azure_preflight.py platform/abf_station/gcb_preflight.py platform/abf_station/k8s_preflight.py
E         baseline lines that no longer match (the baseline may only shrink; edit as shown):
E           credentials_path platform/abf_station/aws_preflight.py platform/abf_station/azure_preflight.py platform/abf_station/gcb_preflight.py platform/abf_station/k8s_preflight.py   -> delete this line
E       assert not ['new duplicate defs (share the function instead of copying it, or, if the name is a convention, whitelist it with a r.../azure_preflight.py platform/abf_station/gcb_preflight.py platform/abf_station/k8s_preflight.py   -> delete this line']
1 failed, 11 passed in 3.83s
Updated 1 path from the index
=== MUTANT 3: one baselined copy edited (group shrinks to 3 files, baseline line stale)
 platform/abf_station/k8s_preflight.py      | 2 +-
 platform/tests/duplicate_defs_baseline.txt | 8 ++++++++
 2 files changed, 9 insertions(+), 1 deletion(-)
E       AssertionError: baseline lines that no longer match (the baseline may only shrink; edit as shown):
E           credentials_path platform/abf_station/aws_preflight.py platform/abf_station/azure_preflight.py platform/abf_station/gcb_preflight.py platform/abf_station/k8s_preflight.py   -> credentials_path platform/abf_station/aws_preflight.py platform/abf_station/azure_preflight.py platform/abf_station/gcb_preflight.py
E       assert not ['baseline lines that no longer match (the baseline may only shrink; edit as shown):\n  credentials_path platform/abf_...h platform/abf_station/aws_preflight.py platform/abf_station/azure_preflight.py platform/abf_station/gcb_preflight.py']
1 failed, 11 passed in 3.77s
Updated 1 path from the index
=== restored
 M platform/tests/duplicate_defs_baseline.txt
```

Green with the baseline filled: `12 passed` (tests/test_no_duplicate_defs.py).
Later tweak: a grown group now says 'the group grew: remove the new copy' instead of 'delete this line'.

## Full suite (tested at HEAD c7faaa08; USER=root exported because the VM has no $USER, else agent_ctl_connection_id_test fails)
NOT GREEN locally: 137/144 passed, 7 failed. None involves test_no_duplicate_defs.py (its 12 tests pass inside the platform shards).
- platform_upgrade_test.sh TC-U28: asserts 'platform/ untouched' against the merge-base with origin/v3; it fails on any branch that adds a file under platform/ (names platform/tests/duplicate_defs_baseline.txt; T1, T5, D1, D3, D9 hit the same). It cannot fail once the branch is merged. Gate not edited.
- platform_clock/shard_5/6/7/platform_test: test_station_e2e tc056/tc082 (_winapi, python 3.13), test_cli_snapshots help_top, test_pipeline_launch_station tc124, test_station_launch tc022, test_station_resume tc026 (java missing / root can write read-only cache): environment, same on D5/D7/D8.
- wsl_bridge_test.sh: environment (no site / WSL).

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

137/144 passed, 7 failed
```
