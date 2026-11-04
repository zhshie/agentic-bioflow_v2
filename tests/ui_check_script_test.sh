#!/bin/bash
# scripts/dev/ui_check.py, static checks only (CI has no Playwright and no Chromium):
#   --help exits 0 and lists the five options (--chromium-path included); .gitignore keeps screenshots out;
#   a bad argument exits 2; without playwright the script says so on one line and exits 3
#   (it must not pretend to pass). The real run is by hand, see the header of the script.
cd "$(dirname "$0")/.." || exit 1
S=scripts/dev/ui_check.py
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }

out=$(python3 "$S" --help 2>&1); rc=$?
[ "$rc" = 0 ] && ok "--help exits 0" || bad "--help exits 0 (got $rc)"
for o in --base-url --out --pages --start --chromium-path; do
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

# --chromium-path / $CHROME_PATH: a stub playwright records what launch() receives (no browser needed)
stub=$(mktemp -d); rec="$stub/launch.json"
mkdir -p "$stub/playwright" "$stub/axe_playwright_python"
: >"$stub/playwright/__init__.py"; : >"$stub/axe_playwright_python/__init__.py"
cat >"$stub/playwright/sync_api.py" <<'PY'
import json, os
class _Chromium:
    def launch(self, **kw):
        with open(os.environ["STUB_REC"], "w") as f:
            json.dump(kw, f)
        raise RuntimeError("stub: no browser")
class _P:
    chromium = _Chromium()
class sync_playwright:
    def __enter__(self): return _P()
    def __exit__(self, *a): return False
PY
printf 'class Axe:\n    pass\n' >"$stub/axe_playwright_python/sync_playwright.py"
fake="$stub/chrome"; : >"$fake"; chmod +x "$fake"
stubrun() {  # stubrun <CHROME_PATH or -> args...  (sets rc, out; $rec holds launch kwargs)
  local cp="$1"; shift; rm -f "$rec"
  if [ "$cp" = - ]; then
    out=$(env -u CHROME_PATH STUB_REC="$rec" PYTHONPATH="$stub" ABF_UI_PASSWORD=x python3 "$S" --base-url http://127.0.0.1:1 --pages board "$@" 2>&1); rc=$?
  else
    out=$(CHROME_PATH="$cp" STUB_REC="$rec" PYTHONPATH="$stub" ABF_UI_PASSWORD=x python3 "$S" --base-url http://127.0.0.1:1 --pages board "$@" 2>&1); rc=$?
  fi
}
exec_of() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("executable_path","<none>"))' "$rec" 2>/dev/null || echo "<no launch>"; }

stubrun - --chromium-path "$fake"
[ "$(exec_of)" = "$fake" ] && ok "--chromium-path reaches launch as executable_path" || bad "--chromium-path reaches launch as executable_path (got $(exec_of))"
[ "$rc" = 3 ] && ok "launch failure with the flag still exits 3" || bad "launch failure with the flag still exits 3 (got $rc)"

stubrun "$fake"
[ "$(exec_of)" = "$fake" ] && ok "\$CHROME_PATH is the default" || bad "\$CHROME_PATH is the default (got $(exec_of))"

stubrun /nonexistent/other-chrome --chromium-path "$fake"
[ "$(exec_of)" = "$fake" ] && ok "--chromium-path beats \$CHROME_PATH" || bad "--chromium-path beats \$CHROME_PATH (got $(exec_of))"

stubrun ""
[ "$(exec_of)" = "<none>" ] && ok "empty \$CHROME_PATH counts as unset" || bad "empty \$CHROME_PATH counts as unset (got $(exec_of))"
stubrun -
[ "$(exec_of)" = "<none>" ] && [ "$rc" = 3 ] && ok "no flag, no env: launch() unchanged, exit 3" || bad "no flag, no env: launch() unchanged, exit 3 (got $(exec_of), rc $rc)"

stubrun - --chromium-path /nonexistent/chrome
[ "$rc" = 3 ] && ok "missing chromium path exits 3" || bad "missing chromium path exits 3 (got $rc)"
[ ! -e "$rec" ] && [ "$(printf '%s\n' "$out" | wc -l)" = 1 ] && case "$out" in */nonexistent/chrome*) ok "missing path: one line naming it, launch not called" ;; *) bad "missing path line names the path: $out" ;; esac || bad "missing path: one line, launch not called: $out"
rm -rf "$stub"

[ "$fail" = 0 ] && echo "ui_check_script_test: PASS" || echo "ui_check_script_test: FAIL"
exit $fail
