# cb-D8 ledger

## RED (unchanged CLAUDE.md)
```
CLAUDE.md has no 'all <number>'                              FAIL: CLAUDE.md matches 'all [0-9]+': 137:bash tests/run_all.sh                    # all 73, ~100s, one verdict + exit code
CLAUDE.md has no '<number> tests'                            ok
CLAUDE.md CI trigger does not name only main                 FAIL: CLAUDE.md matches 'every push to `main`': 131:  then `bash tests/run_all.sh`, on every PR and every push to `main` — CI
2 failure(s)
```

## FINDING
"constitution 6.0.0" in CLAUDE.md line 11 is the version in which principle 2 changed, but the constitution is now 6.2.0.
It is pinned by tests/platform_direction_docs_test.sh TC-059 (HOT file) and by hasnt TC-047 for 4.0.0. Not changed here;
follow-up needs that HOT test to change in the same commit (reword to point at the Version line).

## Change
CLAUDE.md: "all 73, ~100s" -> no numbers; "every push to `main`" -> "the branches it lists" (tests.yml lists main and v3).

## Full suite (HEAD before this commit 645f3686 + CLAUDE.md edit)
Not green locally: 136/144. The 8 failures are environmental (root user, USER unset, python 3.13 _winapi, no httpx for some, read-only-cache tests as root). Re-run on origin/v3 base: agent_ctl_connection_id_test, why_pending_test, wsl_bridge_test and 4 pytest cases (cli_help_top, tc124, tc022, tc026) fail identically; the two test_station_e2e cases fail on `import _winapi` (python 3.13), code untouched by this task.
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

136/144 passed, 8 failed
```
