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

## GREEN (baseline generated from tree)
```
ok    scripts/**/*.sh: no helper duplicate beyond the baseline (29 definitions of 8 names)
ok    detector: finds name() / function name / one-line forms, ignores comments, calls and same-file redefinition
ok    ratchet: a duplicate absent from the baseline is reported
ok    ratchet: a duplicate listed in the baseline passes
ok    ratchet: a new copy of an already-duplicated name is reported
ok    ratchet: a baseline line that is no longer a duplicate is reported (baseline only shrinks)
all passed
```

## Mutation proof (scripts restored after each; never committed)
```
## mutation 1: new duplicate name (helper "boxline" added to two scripts)
FAIL  scripts/**/*.sh helper duplicates differ from the baseline
      NEW   boxline in scripts/status.sh is a duplicate of a helper already defined in another script
      NEW   boxline in scripts/where.sh is a duplicate of a helper already defined in another script
ok    detector: finds name() / function name / one-line forms, ignores comments, calls and same-file redefinition
ok    ratchet: a duplicate absent from the baseline is reported
ok    ratchet: a duplicate listed in the baseline passes
ok    ratchet: a new copy of an already-duplicated name is reported
ok    ratchet: a baseline line that is no longer a duplicate is reported (baseline only shrinks)
1 failed
rc=1
## mutation 2: new copy of existing name die in scripts/where.sh
FAIL  scripts/**/*.sh helper duplicates differ from the baseline
      NEW   die in scripts/where.sh is a duplicate of a helper already defined in another script
ok    detector: finds name() / function name / one-line forms, ignores comments, calls and same-file redefinition
ok    ratchet: a duplicate absent from the baseline is reported
ok    ratchet: a duplicate listed in the baseline passes
ok    ratchet: a new copy of an already-duplicated name is reported
ok    ratchet: a baseline line that is no longer a duplicate is reported (baseline only shrinks)
1 failed
rc=1
## mutation 3: say() removed from scripts/preflight.sh (baseline now stale)
35:say() { printf "%-10s %-14s %s\n" "$1" "$2" "$3"; [ "$1" = FAIL ] && fail=1; return 0; }
FAIL  scripts/**/*.sh helper duplicates differ from the baseline
      STALE say in scripts/launch_recheck.sh is no longer a duplicate: delete its line from the baseline
      STALE say in scripts/preflight.sh is no longer a duplicate: delete its line from the baseline
ok    detector: finds name() / function name / one-line forms, ignores comments, calls and same-file redefinition
ok    ratchet: a duplicate absent from the baseline is reported
ok    ratchet: a duplicate listed in the baseline passes
ok    ratchet: a new copy of an already-duplicated name is reported
ok    ratchet: a baseline line that is no longer a duplicate is reported (baseline only shrinks)
1 failed
rc=1
## restored
 M tests/shell_helper_dupes_test.sh
?? tests/shell_helper_dupes_baseline.txt
all passed
```
