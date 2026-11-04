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
