#!/bin/bash
# scripts/dev/ui_check.py, static checks only (CI has no Playwright and no Chromium):
#   --help exits 0 and lists the four options; .gitignore keeps screenshots out;
#   a bad argument exits 2; without playwright the script says so on one line and exits 3
#   (it must not pretend to pass). The real run is by hand, see the header of the script.
cd "$(dirname "$0")/.." || exit 1
S=scripts/dev/ui_check.py
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }

out=$(python3 "$S" --help 2>&1); rc=$?
[ "$rc" = 0 ] && ok "--help exits 0" || bad "--help exits 0 (got $rc)"
for o in --base-url --out --pages --start; do
  case "$out" in *"$o"*) ok "--help lists $o" ;; *) bad "--help lists $o" ;; esac
done

grep -qxF 'ui-check-*/' .gitignore && ok ".gitignore has ui-check-*/" || bad ".gitignore has ui-check-*/"

python3 "$S" --no-such-option >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && ok "unknown option exits 2" || bad "unknown option exits 2 (got $rc)"
python3 "$S" >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && ok "missing --base-url/--start exits 2" || bad "missing --base-url/--start exits 2 (got $rc)"
python3 "$S" --base-url http://127.0.0.1:1 --pages nope >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && ok "unknown page name exits 2" || bad "unknown page name exits 2 (got $rc)"

# no playwright: mask it even where it is installed
mask=$(mktemp -d); printf 'raise ImportError("masked by test")\n' >"$mask/playwright.py"
out=$(PYTHONPATH="$mask" python3 "$S" --base-url http://127.0.0.1:1 --pages board 2>&1); rc=$?
rm -rf "$mask"
[ "$rc" = 3 ] && ok "no playwright exits 3" || bad "no playwright exits 3 (got $rc)"
[ "$(printf '%s\n' "$out" | wc -l)" = 1 ] && case "$out" in *playwright*) ok "one explicit line" ;; *) bad "line names playwright" ;; esac || bad "exactly one line on no playwright: $out"

[ "$fail" = 0 ] && echo "ui_check_script_test: PASS" || echo "ui_check_script_test: FAIL"
exit $fail
