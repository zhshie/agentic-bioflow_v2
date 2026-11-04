# cb-T4 ledger

Base: origin/v3 62c91293de611d265d8fbf3d0a128bea849be98c

## Base capture
Outputs of both functions captured on the unrenamed base (23 inputs for tune_resources.sh to_gb plus no-arg, 20 pairs for why_pending.sh to_gb) and pasted into tests/mem_to_gb_test.sh. Check: the same table run against the base with the names mapped back to to_gb passed 46/46.

## RED (new test on unchanged code)
```
tune_resources.sh defines mem_to_gb                        FAIL: no mem_to_gb() in tune_resources.sh
why_pending.sh defines mem_to_gb_ceil                      FAIL: no mem_to_gb_ceil() in why_pending.sh
tune_resources.sh no longer mentions bare to_gb            FAIL: 75:to_gb() {
why_pending.sh no longer mentions bare to_gb               FAIL: 86:to_gb() {

4 failed
```

## GREEN
tests/mem_to_gb_test.sh: all passed (46 table cases + 2 definitions + 2 absence checks). tests/tune_resources_test.sh: all passed.

## run_all (code commit f752ec63)
134/142 passed, 8 failed. NOT green locally. The same 8 files fail with the same results on unchanged origin/v3 in this VM (T2 base run /tmp/cb/t2_runall.out, T3 run): agent_ctl_connection_id_test, platform_clock_test, platform_shard_4..7_test, why_pending_test (one case, 'layer=scheduler' - also fails with this change stashed), wsl_bridge_test. Environment-related, not touched by this change.

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
