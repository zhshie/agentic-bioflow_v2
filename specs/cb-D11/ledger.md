# Ledger cb-D11

## RED (no baseline yet)
```
# RED: baseline absent
$ bash tests/shell_helper_dupes_test.sh
FAIL  baseline missing: /tmp/cb/D11/tests/shell_helper_dupes_baseline.txt (generate it from the current tree)
ok    detector: finds name() / function name / one-line forms, ignores comments, calls and same-file redefinition
ok    ratchet: a duplicate absent from the baseline is reported
ok    ratchet: a duplicate listed in the baseline passes
ok    ratchet: a new copy of an already-duplicated name is reported
ok    ratchet: a baseline line that is no longer a duplicate is reported (baseline only shrinks)
1 failed
rc=1
```
