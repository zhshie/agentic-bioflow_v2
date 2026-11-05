# cb-D13 ledger

## RED (test on unchanged script, base 1802fde4)
```
ok   compiles
ok   imports without running anything
FAIL header has: Purpose
FAIL header has: How to run
FAIL header has: One-off
ok   no playwright exits 77 (skip)
ok   no playwright: no traceback
ok   no playwright: names playwright as the reason
ok   no playwright: wrote nothing
ok   no playwright (--help) exits 77 (skip)
ok   no playwright (--help): no traceback
ok   no playwright (--help): names playwright as the reason
ok   no playwright (--help): wrote nothing
check_settings_mobile_smoke_test: FAIL
```

Only the three header cases fail; compile/import/skip cases already hold on the unchanged script.

## GREEN (new test after header edit)
```
ok   compiles
ok   imports without running anything
ok   header has: Purpose
ok   header has: How to run
ok   header has: One-off
ok   no playwright exits 77 (skip)
ok   no playwright: no traceback
ok   no playwright: names playwright as the reason
ok   no playwright: wrote nothing
ok   no playwright (--help) exits 77 (skip)
ok   no playwright (--help): no traceback
ok   no playwright (--help): names playwright as the reason
ok   no playwright (--help): wrote nothing
check_settings_mobile_smoke_test: PASS
```

## Full suite (base HEAD before this commit: 46745a5185606aa7ad98f2fba82a54d41617d02e)
NOT green locally: 9 files red, none touching this task; same environment failures seen in other cloud-burn runs on this VM (agent_ctl_connection_id, platform_clock, platform_shard_4/5/6/7/8, why_pending, wsl_bridge: station_e2e tc056/tc082, test_wrapper_nf2 needs the second nf pair, test_cli_snapshots cli_help_top, MSYS/ssh preflight cases). check_settings_mobile_smoke_test.sh is ok. Not verified against a clean origin/v3 run in this checkout.
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

136/145 passed, 9 failed
```

## FINDINGS
- check_settings_mobile.py treats argv[1] as the screenshot folder, so with playwright installed '--help' would create a folder named '--help' and run the whole check. Out of scope here (header-only task); the header now says it takes no options. Fix would be a one-line argv guard in the script.
