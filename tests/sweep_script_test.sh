#!/bin/bash
# scripts/sweep.sh: one-shot dead-code / duplicate / unused / audit report.
# CI has none of the four real tools, so every case here uses fake ones: four
# tiny scripts in a temp folder that print fixed output, put first on PATH.
#
# Cases: (1) all four sections present with the right finding counts,
# (2) a missing tool gives a "skipped:" line and still exit 0, (3) no --out
# leaves the repo's git status unchanged, (4) a bad argument exits 2,
# (5) pip-audit that cannot reach the network gives "skipped: network".
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SWEEP="$ROOT/scripts/sweep.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fails=0
ok()   { echo "ok   $1"; }
fail() { echo "FAIL $1"; fails=$((fails+1)); }

FAKE="$T/fake"; mkdir -p "$FAKE"
mk() { printf '#!/bin/bash\n%s\n' "$2" >"$FAKE/$1"; chmod +x "$FAKE/$1"; }
mk vulture 'echo "scripts/a.py:3: unused function '"'f'"' (60% confidence)"
echo "platform/abf_platform/b.py:9: unused variable '"'x'"' (60% confidence)"
echo "platform/abf_station/c.py:1: unused import '"'os'"' (90% confidence)"
exit 3'
mk ruff 'echo "scripts/a.py:1:8: F401 [*] `os` imported but unused"
echo "scripts/a.py:5:5: F841 Local variable `y` is assigned to but never used"
echo "Found 2 errors."
exit 1'
mk jscpd 'echo "Clone found (python):"
echo " - scripts/a.py [1:1 - 9:2]"
echo "   scripts/b.py [1:1 - 9:2]"
echo "Clone found (python):"
echo " - scripts/c.py [1:1 - 9:2]"
echo "   scripts/d.py [1:1 - 9:2]"
exit 0'
mk pip-audit 'echo "{\"dependencies\":[{\"name\":\"a\",\"version\":\"1\",\"vulns\":[{\"id\":\"PYSEC-1\"},{\"id\":\"PYSEC-2\"}]},{\"name\":\"b\",\"version\":\"2\",\"vulns\":[]}]}"
exit 1'

# (1) four sections, right counts
out="$T/r1.md"
PATH="$FAKE:$PATH" bash "$SWEEP" --out "$out" >"$T/o1" 2>&1; rc=$?
[ "$rc" = 0 ] && ok "1a exit 0 with findings" || fail "1a exit $rc"
for tool in vulture jscpd ruff pip-audit; do
  grep -q "^## .*$tool" "$out" 2>/dev/null && ok "1b section $tool" || fail "1b section $tool missing"
done
# count printed in the section whose heading mentions $1, in report $2
secn() { awk -v t="$1" '/^## /{on=index($0,t)>0} on&&/^發現數:/{print $2; exit}' "$2"; }
[ "$(secn vulture "$out")" = 3 ] && ok "1c vulture=3" || fail "1c vulture count"
[ "$(secn jscpd "$out")" = 2 ] && ok "1d jscpd=2" || fail "1d jscpd count"
[ "$(secn ruff "$out")" = 2 ] && ok "1e ruff=2" || fail "1e ruff count"
[ "$(secn pip-audit "$out")" = 2 ] && ok "1f pip-audit=2" || fail "1f pip-audit count"
grep -q -- '--select F401,F841' "$out" && ok "1g ruff command text recorded" || fail "1g ruff command text"
[ "$(cat "$T/o1" | tail -1)" = "$out" ] && ok "1h prints report path" || fail "1h path not printed"

# (2) a missing tool: isolated PATH holding only basics + three fakes
BIN="$T/bin"; mkdir -p "$BIN"
for c in bash sh env grep sed awk head tail cat date mkdir mktemp rm wc sort tr dirname basename cut python3 timeout git ls; do
  p="$(command -v "$c" 2>/dev/null)" && ln -sf "$p" "$BIN/$c"
done
for f in vulture ruff pip-audit; do ln -sf "$FAKE/$f" "$BIN/$f"; done   # no jscpd
out2="$T/r2.md"
PATH="$BIN" bash "$SWEEP" --out "$out2" >/dev/null 2>&1; rc=$?
[ "$rc" = 0 ] && ok "2a exit 0 with tool missing" || fail "2a exit $rc"
grep -q '^skipped: jscpd not installed (install: ' "$out2" && ok "2b skipped line" || fail "2b skipped line"
[ "$(secn vulture "$out2")" = 3 ] && ok "2c other tools still ran" || fail "2c other tools did not run"

# (3) no --out: nothing new in the repo
before="$(cd "$ROOT" && git status --porcelain)"
TMPDIR="$T" PATH="$FAKE:$PATH" bash "$SWEEP" >"$T/o3" 2>&1; rc=$?
after="$(cd "$ROOT" && git status --porcelain)"
[ "$rc" = 0 ] && [ "$before" = "$after" ] && ok "3a git status unchanged" || fail "3a repo changed or rc=$rc"
p="$(tail -1 "$T/o3")"
case "$p" in "$T"/sweep-*.md) [ -f "$p" ] && ok "3b default under \$TMPDIR" || fail "3b file missing";; *) fail "3b default path '$p'";; esac

# (4) bad arguments
bash "$SWEEP" --bogus >/dev/null 2>&1; [ $? = 2 ] && ok "4a unknown flag exit 2" || fail "4a"
bash "$SWEEP" --out >/dev/null 2>&1;   [ $? = 2 ] && ok "4b --out without value exit 2" || fail "4b"
bash "$SWEEP" extra >/dev/null 2>&1;   [ $? = 2 ] && ok "4c stray positional exit 2" || fail "4c"

# (5) pip-audit cannot reach PyPI
mk pip-audit 'echo "Failed to establish a new connection: Max retries exceeded" >&2; exit 1'
out5="$T/r5.md"
PATH="$FAKE:$PATH" bash "$SWEEP" --out "$out5" >/dev/null 2>&1; rc=$?
[ "$rc" = 0 ] && grep -q '^skipped: network' "$out5" && ok "5 network skip" || fail "5 network skip (rc=$rc)"

[ "$fails" = 0 ] && { echo "all ok"; exit 0; }
echo "$fails failed"; exit 1
