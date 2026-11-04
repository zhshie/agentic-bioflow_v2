# cb-UI1 ledger

## RED (tests/ui_check_script_test.sh on unchanged scripts/dev/ui_check.py)
```
ok   --help exits 0
ok   --help lists --base-url
ok   --help lists --out
ok   --help lists --pages
ok   --help lists --start
FAIL --help lists --chromium-path
ok   .gitignore has ui-check-*/
ok   unknown option exits 2
ok   missing --base-url/--start exits 2
ok   unknown page name exits 2
ok   no playwright exits 3
ok   one explicit line
FAIL --chromium-path reaches launch as executable_path (got <no launch>)
FAIL launch failure with the flag still exits 3 (got 2)
FAIL $CHROME_PATH is the default (got <none>)
FAIL --chromium-path beats $CHROME_PATH (got <no launch>)
ok   empty $CHROME_PATH counts as unset
ok   no flag, no env: launch() unchanged, exit 3
FAIL missing chromium path exits 3 (got 2)
FAIL missing path: one line, launch not called: usage: ui_check.py [-h] [--base-url BASE_URL] [--out OUT] [--pages PAGES]
                   [--start] [--user USER] [--password-env PASSWORD_ENV]
                   [--run RUN]
ui_check.py: error: unrecognized arguments: --chromium-path /nonexistent/chrome
ui_check_script_test: FAIL
```

## GREEN (after the change)
```
ok   --help exits 0
ok   --help lists --base-url
ok   --help lists --out
ok   --help lists --pages
ok   --help lists --start
ok   --help lists --chromium-path
ok   .gitignore has ui-check-*/
ok   unknown option exits 2
ok   missing --base-url/--start exits 2
ok   unknown page name exits 2
ok   no playwright exits 3
ok   one explicit line
ok   --chromium-path reaches launch as executable_path
ok   launch failure with the flag still exits 3
ok   $CHROME_PATH is the default
ok   --chromium-path beats $CHROME_PATH
ok   empty $CHROME_PATH counts as unset
ok   no flag, no env: launch() unchanged, exit 3
ok   missing chromium path exits 3
ok   missing path: one line naming it, launch not called
ui_check_script_test: PASS
```

## Full suite (tests/run_all.sh at 38791130, NOT green locally)
Failures are environmental (VM runs as root with USER unset, no rsync/tw, read-only-cache tests cannot fail as root); none touch ui_check. agent_ctl_connection_id and why_pending pass with USER=root; ui_check_script_test passes.
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

135/144 passed, 9 failed
```
