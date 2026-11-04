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
