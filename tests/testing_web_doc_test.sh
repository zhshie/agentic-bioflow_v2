#!/bin/bash
# The web test strategy in docs/TESTING.md (issue #119 item 8) must stay honest:
# the section exists, it names TestClient and the click-only procedure, every
# platform/tests file it points at exists, and the platform declares no
# browser-automation dependency. TESTING_FILE, PYPROJECT_FILE and CONSTRAINTS_FILE
# point the check at scratch copies (how the self-tests below go red).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TESTING="${TESTING_FILE:-$ROOT/docs/TESTING.md}"
PYPROJECT="${PYPROJECT_FILE:-$ROOT/platform/pyproject.toml}"
CONSTRAINTS="${CONSTRAINTS_FILE:-$ROOT/platform/constraints.txt}"
fail=0
bad() { echo "FAIL: $*"; fail=1; }

[ -r "$TESTING" ] || { echo "FAIL: cannot read $TESTING"; exit 1; }

# TC-001: exactly one heading
n=$(grep -c '^## Testing the web[[:space:]]*$' "$TESTING")
[ "$n" -eq 1 ] || bad "TC-001: expected exactly one '## Testing the web' heading, found $n"

# the section: heading up to the next '## ' heading
section=$(awk '/^## Testing the web[[:space:]]*$/{f=1;next} f&&/^## /{exit} f' "$TESTING")

# TC-002, TC-013
grep -q 'TestClient' <<<"$section" || bad "TC-002: 'TestClient' missing from the Testing the web section"
grep -q 'click-only' <<<"$section" || bad "TC-013: 'click-only' missing from the Testing the web section"

# TC-005: no browser-automation package declared
for f in "$PYPROJECT" "$CONSTRAINTS"; do
  [ -r "$f" ] || { bad "TC-005: cannot read $f"; continue; }
  for pkg in playwright selenium puppeteer; do
    grep -qi "$pkg" "$f" && bad "TC-005: $pkg appears in $f"
  done
done

# TC-006: every named platform/tests file exists, at least one named
files=$(grep -oE 'platform/tests/[A-Za-z0-9_./-]+\.py' <<<"$section" | sort -u)
[ -n "$files" ] || bad "TC-006: the section names no platform/tests/...py file"
for p in $files; do
  [ -f "$ROOT/$p" ] || bad "TC-006: $p is named in the section but does not exist"
done

[ "$fail" -eq 0 ] || exit 1

# Self-tests: the rules can go red (TC-010, TC-011, TC-012).
if [ -z "${TESTING_WEB_NO_SELFTEST:-}" ]; then
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  run() { TESTING_WEB_NO_SELFTEST=1 "$@" bash "$HERE/testing_web_doc_test.sh" 2>&1; }
  st() { # name expected-text, env...
    local name="$1" want="$2"; shift 2
    local out; out=$(run env "$@") && { echo "FAIL: self-test $name stayed green"; exit 1; }
    grep -q "$want" <<<"$out" || { echo "FAIL: self-test $name did not name '$want'"; exit 1; }
  }
  sed 's#platform/tests/test_web_login.py#platform/tests/nope_does_not_exist.py#' "$TESTING" > "$tmp/a.md"
  st TC-010 nope_does_not_exist TESTING_FILE="$tmp/a.md"
  { cat "$PYPROJECT"; echo 'playwright'; } > "$tmp/p.toml"
  st TC-011 playwright PYPROJECT_FILE="$tmp/p.toml"
  sed 's/click-only/clickonly/g' "$TESTING" > "$tmp/b.md"
  st TC-012a click-only TESTING_FILE="$tmp/b.md"
  sed 's/TestClient/TC/g' "$TESTING" > "$tmp/c.md"
  st TC-012b TestClient TESTING_FILE="$tmp/c.md"
  sed 's/^## Testing the web/## Something else/' "$TESTING" > "$tmp/d.md"
  st TC-012c "Testing the web" TESTING_FILE="$tmp/d.md"
fi
echo "PASS: testing_web_doc_test"
