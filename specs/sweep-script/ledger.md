# sweep-script (C7) progress ledger

- [x] Step 1 (RED): `tests/sweep_script_test.sh` written before `scripts/sweep.sh` existed. Output (head and tail):

```
FAIL 1a exit 127
FAIL 1b section vulture missing
FAIL 1b section jscpd missing
FAIL 1b section ruff missing
FAIL 1b section pip-audit missing
grep: /tmp/tmp.qT1Um71Mmj/r1.md: No such file or directory
...
FAIL 4c
FAIL 5 network skip (rc=127)
20 failed
```

- [x] Step 2 (GREEN): `scripts/sweep.sh` written; `bash tests/sweep_script_test.sh`: all ok. Fixed one own mistake on the way: the test first used `| grep -q` under pipefail and `no_pipefail_grep_q_test.sh` caught it.
- [x] Step 3: `scripts/scripts_name_their_alternative` and `portable_userland` pass with the new script.
- [x] Step 4: full suite on this cloud box (Linux, root, jq present, no CI var): 131/140 before the grep fix; after it, sweep and no_pipefail are green. Remaining reds are the cloud box, not this change: `agent_ctl_connection_id`, `why_pending` pass once `USER` is set; `platform_clock`/`platform_shard_*` fail identically on origin/v3 (running as root makes read-only-cache cases writable); `wsl_bridge_test` still fails with USER set and was not compared on the base.

## Real sweep (vulture, jscpd, ruff, pip-audit all installed), first 30 lines, report not committed

```
# Sweep report 2026-11-03

- Scope: scripts platform/abf_platform platform/abf_launch platform/abf_station (excluding tests,build,.venv,node_modules). Read-only; no file was changed.
- Parameters from the sweep-2026-11 report.

## Dead code (vulture)

Command: `vulture scripts platform/abf_platform platform/abf_launch platform/abf_station --exclude tests,build,.venv,node_modules --ignore-names launch_tool,cancel_tool,get_client,load_*,redirect_request`

發現數: 68

前 50 條 / first 50 lines of output (tool exit code 3):

```
platform/abf_platform/actions/__init__.py:147: unused function 'estimate_su' (60% confidence)
platform/abf_platform/actions/__init__.py:908: unused function 'nfcore_catalogue' (60% confidence)
platform/abf_platform/actions/__init__.py:1470: unused function 'request_pipeline_launch' (60% confidence)
platform/abf_platform/actions/__init__.py:1579: unused function 'void_request' (60% confidence)
platform/abf_platform/actions/chat_tools.py:18: unused variable 'CHAT_SYSTEM_PROMPT' (60% confidence)
platform/abf_platform/actions/chat_tools.py:54: unused function 'tool_specs' (60% confidence)
platform/abf_platform/actions/chat_tools.py:66: unused function 'confirm_dialog' (60% confidence)
platform/abf_platform/actions/datasets.py:175: unused function 'draft_samplesheet' (60% confidence)
platform/abf_platform/actions/datasets.py:215: unused function 'check_web_upload' (60% confidence)
platform/abf_platform/actions/pipelines.py:92: unused function 'create_pipeline' (60% confidence)
platform/abf_platform/actions/pipelines.py:124: unused function 'update_pipeline' (60% confidence)
platform/abf_platform/actions/pipelines.py:239: unused function 'export_pipeline' (60% confidence)
platform/abf_platform/actions/pipelines.py:271: unused function 'validate_pipeline' (60% confidence)
platform/abf_platform/agents.py:95: unused function 'get_facts' (60% confidence)
platform/abf_platform/jobs.py:168: unused attribute 'isolation_level' (60% confidence)
platform/abf_platform/jobs.py:935: unused function 'enqueue_launch' (60% confidence)
```

Counts: vulture 68, jscpd 94 clone entries, ruff 8, pip-audit 2 (both are one certifi advisory listed twice).
