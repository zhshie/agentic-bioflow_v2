# cb-T6 ledger

Base: origin/v3 62c91293. Pure test addition: mutation proof instead of RED.

## Test on unchanged hooks
```
== helpers that are copies of one another ==
abf_cap: defined in exactly: confirm_cleanup.sh confirm_launch.sh confirm_walkthrough.sh guard_plugin_files.sh ok
abf_cap: confirm_launch.sh is identical to confirm_cleanup.sh                  ok
abf_cap: confirm_walkthrough.sh is identical to confirm_cleanup.sh             ok
abf_cap: guard_plugin_files.sh is identical to confirm_cleanup.sh              ok
abf_emit: defined in exactly: confirm_cleanup.sh confirm_launch.sh confirm_walkthrough.sh guard_plugin_files.sh ok
abf_emit: confirm_launch.sh is identical to confirm_cleanup.sh                 ok
abf_emit: confirm_walkthrough.sh is identical to confirm_cleanup.sh            ok
abf_emit: guard_plugin_files.sh is identical to confirm_cleanup.sh             ok
abf_jq_works: defined in exactly: confirm_launch.sh confirm_walkthrough.sh plugin_intro.sh ok
abf_jq_works: confirm_walkthrough.sh is identical to confirm_launch.sh         ok
abf_jq_works: plugin_intro.sh is identical to confirm_launch.sh                ok
== deny ==
deny: defined in exactly: confirm_cleanup.sh confirm_walkthrough.sh guard_plugin_files.sh ok
deny: guard_plugin_files.sh is identical to confirm_cleanup.sh                 ok
deny: confirm_walkthrough.sh is the pinned one-line form                       ok
deny: confirm_walkthrough.sh differs from the others in layout only            ok
== ask ==
ask: defined in exactly: confirm_cleanup.sh confirm_launch.sh                  ok
ask: confirm_cleanup.sh is the pinned one-message form (reason = context = $1) ok
ask: confirm_launch.sh is the pinned two-argument form (context $1, reason $2) ok
ask: the two copies still differ (so the exception is still needed)            ok

hook_helpers_consistent_test: all passed
```

## Mutation proof (hooks/ mutated temporarily, restored with git checkout -- hooks, never committed)
```
## extractor output sizes (lines)
abf_cap hooks/confirm_cleanup.sh defs=1
abf_cap hooks/confirm_launch.sh defs=1
abf_cap hooks/confirm_walkthrough.sh defs=1
abf_cap hooks/guard_plugin_files.sh defs=1
abf_emit hooks/confirm_cleanup.sh defs=1
abf_emit hooks/confirm_launch.sh defs=1
abf_emit hooks/confirm_walkthrough.sh defs=1
abf_emit hooks/guard_plugin_files.sh defs=1
abf_jq_works hooks/confirm_launch.sh defs=1
abf_jq_works hooks/confirm_walkthrough.sh defs=1
abf_jq_works hooks/plugin_intro.sh defs=1
deny hooks/confirm_cleanup.sh defs=1
deny hooks/confirm_walkthrough.sh defs=1
deny hooks/guard_plugin_files.sh defs=1
ask hooks/confirm_cleanup.sh defs=1
ask hooks/confirm_launch.sh defs=1
## MUTANT: abf_cap threshold 6000->5000 in guard_plugin_files.sh
abf_cap: guard_plugin_files.sh is identical to confirm_cleanup.sh              FAIL: bodies differ: diff <(body confirm_cleanup.sh) <(body guard_plugin_files.sh) ->3c3|<     if [ "${#1}" -gt 6000 ]; then|---|>     if [ "${#1}" -gt 5000 ]; then|
hook_helpers_consistent_test: 1 FAILED
exit=1
## MUTANT: abf_emit jq expression changed in confirm_walkthrough.sh
abf_emit: confirm_walkthrough.sh is identical to confirm_cleanup.sh            FAIL: bodies differ: diff <(body confirm_cleanup.sh) <(body confirm_walkthrough.sh) ->6c6|<             + (if $d != "-" then {permissionDecision: $d} else {} end)|---|>             
hook_helpers_consistent_test: 1 FAILED
exit=1
## MUTANT: abf_jq_works probe answer changed in plugin_intro.sh
abf_jq_works: plugin_intro.sh is identical to confirm_launch.sh                FAIL: bodies differ: diff <(body confirm_launch.sh) <(body plugin_intro.sh) ->4c4|<     [ "${o%$'\r'}" = '[1]' ]|---|>     [ "${o%$'\r'}" = '[2]' ]|
hook_helpers_consistent_test: 1 FAILED
exit=1
## MUTANT: ask args swapped in confirm_launch.sh (pin)
ask: confirm_launch.sh is the pinned two-argument form                         FAIL: got: ask() {|    abf_emit ask "$1" "$2"|    exit 0|}
hook_helpers_consistent_test: 1 FAILED
exit=1
## MUTANT: new deny() copy added to session_start.sh
deny: files that define it                                                     FAIL: expected [confirm_cleanup.sh confirm_walkthrough.sh guard_plugin_files.sh], found [confirm_cleanup.sh confirm_walkthrough.sh guard_plugin_files.sh session_start.sh] - add a ne
hook_helpers_consistent_test: 1 FAILED
exit=1
## MUTANT: deny body changed in guard_plugin_files.sh
deny: guard_plugin_files.sh is identical to confirm_cleanup.sh                 FAIL: bodies differ: diff <(body confirm_cleanup.sh) <(body guard_plugin_files.sh) ->2c2|<     abf_emit deny "$1" -|---|>     abf_emit deny "$1" "$1"|
hook_helpers_consistent_test: 1 FAILED
exit=1
## MUTANT: deny in walkthrough loses 'exit 0'
deny: confirm_walkthrough.sh is the pinned one-line form                       FAIL: got: deny()  { abf_emit deny "$1" -; }
deny: confirm_walkthrough.sh differs from the others in layout only            FAIL: statements differ: [abf_emit deny "$1" -|] vs [abf_emit deny "$1" -|exit 0|]
hook_helpers_consistent_test: 2 FAILED
exit=1
## CONTROL: comment-only edit in a hook copy must still pass
hook_helpers_consistent_test: all passed
exit=0
```

## Full suite (HEAD = base 62c91293 + this commit's two paths; written before commit)
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

134/142 passed, 8 failed
```

Not green locally, same environmental set as T4/T5 on this VM: agent_ctl_connection_id_test and why_pending_test fail only because $USER is unset (both pass with USER=root); platform_clock/shard_4..7 fail on station e2e / read-only-cache cases (running as root) and a CLI help snapshot; wsl_bridge_test fails on MSYS-simulation cases needing rsync/tw. None touch hooks or this test; hook_helpers_consistent_test.sh is ok in the run.
