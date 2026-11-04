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
