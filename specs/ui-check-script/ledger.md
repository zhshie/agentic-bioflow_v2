# Ledger: ui-check-script (C8)

## Red run (tests/ui_check_script_test.sh before scripts/dev/ui_check.py and the .gitignore line existed)

```
FAIL --help exits 0 (got 2)
FAIL --help lists --base-url
FAIL --help lists --out
FAIL --help lists --pages
FAIL --help lists --start
FAIL .gitignore has ui-check-*/
ok   unknown option exits 2
ok   missing --base-url/--start exits 2
ok   unknown page name exits 2
FAIL no playwright exits 3 (got 2)
FAIL line names playwright
ui_check_script_test: FAIL
```
(The three "unknown option / missing / unknown page exits 2" lines were green only because a missing file also exits 2.)

## Real run

pending
