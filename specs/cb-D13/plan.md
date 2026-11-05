# cb-D13 plan

Goal: scripts/dev/check_settings_mobile.py has no test and no explicit statement of whether it is a one-off.
Add a header comment (purpose, how to run, one-off or not) and a smoke test that does not need Playwright or Chrome.
Source: cloud-burn tasks.json D13.

Files: scripts/dev/check_settings_mobile.py (header comment only, no code change), tests/check_settings_mobile_smoke_test.sh (new),
specs/cb-D13/plan.md, specs/cb-D13/ledger.md.

Approach: the test (1) compiles the script, (2) imports it as a module (no side effects at import), (3) checks the header names
Purpose / How to run / One-off, (4) with playwright masked out of find_spec (sys.modules['playwright']=None via a throwaway
sitecustomize), runs it with and without --help from an empty cwd: no traceback, exit 77, and a stderr/stdout line that names
playwright as the reason (a loud skip, never a pass).

RED tests: header check (fails on unchanged code: no "One-off" statement). The rest already hold on unchanged code.
Done: new test passes; check_scope clean; run_all green.
Environment: no playwright and no Chrome in the VM (and none in CI), so the real run is not exercised.
Not doing: any code change in the script (so `--help` is still not an option it knows: see ledger FINDING), pytest/CI wiring, running the real browser check.
