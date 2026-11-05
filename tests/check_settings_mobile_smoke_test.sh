#!/bin/bash
# scripts/dev/check_settings_mobile.py, smoke only (CI has neither Playwright nor Chrome, so the real browser run is by hand):
#   it compiles and imports without side effects; its header says what it is for, how to run it and that it is a one-off;
#   without playwright it skips LOUDLY - exit 77 and a line that names playwright as the reason - and never exits 0.
# Playwright is masked even where it is installed, so this file means the same everywhere.
cd "$(dirname "$0")/.." || exit 1
ROOT=$(pwd)
S=scripts/dev/check_settings_mobile.py
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }

work=$(mktemp -d) || exit 1
trap 'rm -rf "$work"' EXIT
mkdir "$work/mask" "$work/cwd"
# find_spec("playwright") returns None when sys.modules["playwright"] is None
printf 'import sys\nsys.modules["playwright"] = None\n' >"$work/mask/sitecustomize.py"

python3 -m py_compile "$S" 2>/dev/null && ok "compiles" || bad "compiles"
rm -rf scripts/dev/__pycache__ 2>/dev/null

out=$(cd "$work/cwd" && PYTHONPATH="$work/mask" python3 -c '
import importlib.util, sys
spec = importlib.util.spec_from_file_location("check_settings_mobile", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert callable(m.main) and "sync_playwright" in m.DRIVER
print("imported")' "$ROOT/$S" 2>&1); rc=$?
[ "$rc" = 0 ] && [ "$out" = imported ] && ok "imports without running anything" || bad "imports without running anything (rc=$rc: $out)"

head -n 20 "$S" >"$work/head.txt"
for k in 'Purpose' 'How to run' 'One-off'; do
  grep -q "$k" "$work/head.txt" && ok "header has: $k" || bad "header has: $k"
done

for args in "" "--help"; do
  out=$(cd "$work/cwd" && env -u ABF_PLAYWRIGHT_PYTHON PYTHONPATH="$work/mask" python3 "$ROOT/$S" $args 2>&1); rc=$?
  label="no playwright${args:+ ($args)}"
  [ "$rc" = 77 ] && ok "$label exits 77 (skip)" || bad "$label exits 77 (got $rc)"
  case "$out" in *Traceback*) bad "$label: no traceback" ;; *) ok "$label: no traceback" ;; esac
  case "$out" in *playwright*) ok "$label: names playwright as the reason" ;; *) bad "$label: names playwright as the reason: $out" ;; esac
  [ -z "$(ls -A "$work/cwd")" ] && ok "$label: wrote nothing" || bad "$label: wrote nothing ($(ls -A "$work/cwd"))"
done

[ "$fail" = 0 ] && echo "check_settings_mobile_smoke_test: PASS" || echo "check_settings_mobile_smoke_test: FAIL"
exit $fail
