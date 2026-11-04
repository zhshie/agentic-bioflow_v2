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
