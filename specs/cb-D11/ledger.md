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

## Full suite (HEAD 20e664bf9103f4bab5a01b595fbd81107c288509, USER=root, venv on PATH)
NOT GREEN locally: 138/145 passed, 7 failed, all platform/environment (no _winapi in this python, terminal-width help snapshot, wsl_bridge, platform_clock + shards 4-8 pytest). shell_helper_dupes_test.sh and no_pipefail_grep_q_test.sh pass. Earlier D-tasks in this VM show the same 7-9 environmental failures. First run (USER unset) additionally failed agent_ctl_connection_id/why_pending (USER unbound) and no_pipefail_grep_q (my file used pipe into grep -q; fixed in 20e664bf).
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

138/145 passed, 7 failed
```
