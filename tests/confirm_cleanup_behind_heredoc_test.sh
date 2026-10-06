#!/bin/bash
# #62: the deletion guard judges a large command along a different path from a
# small one. Past a size threshold it first drops, in one awk pass, every segment
# none of its rules can act on (hooks/confirm_cleanup.sh, "large input"), so a
# 300 KB python here-doc no longer costs it a judgement per line. A rule that
# filter does not reach would pass silently only on large input - the very shape
# of the bug that made the filter necessary (a long here-doc, then the delete).
#
# So every case of tests/confirm_cleanup_test.sh runs again with its command
# placed after a here-doc large enough to take that path, and must get the same
# verdict. The here-doc's lines are full of delete-like letters (format,
# transform, remove_prefix) so a filter keyed on substrings would keep them all.
# A first check proves the here-doc is large enough: the filter is one more awk
# process, counted the way tests/gate_process_count_test.sh counts.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "python is required for this test"; exit 1; }
export MSYS2_ARG_CONV_EXCL='*'

PREFIX="$TMP/prefix.txt"
"$PY" - "$PREFIX" <<'PY'
import sys
body = "".join("v%d = transform(format(x%d, '.2f')).remove_prefix('r')\n" % (i, i) for i in range(600))
open(sys.argv[1], "w").write("python3 - <<'EOF'\n" + body + "EOF\n")
PY

# The prefix alone must take the large-input path: three awk runs (strip
# here-docs, split, filter) instead of two.
mkdir -p "$TMP/shims"
real=$(command -v awk)
printf '#!/bin/bash\necho awk >> "%s/awk.log"\nexec %s "$@"\n' "$TMP" "$real" > "$TMP/shims/awk"
chmod +x "$TMP/shims/awk"
: > "$TMP/awk.log"
"$PY" -c "import json,sys;print(json.dumps({'tool_input':{'command':open(sys.argv[1]).read()+'ls'}}))" "$PREFIX" \
  | PATH="$TMP/shims:$PATH" bash "$ROOT/hooks/confirm_cleanup.sh" >/dev/null 2>&1
n=$(awk 'END {print NR+0}' "$TMP/awk.log")
printf '%-70s ' "the prefix takes the large-input path (awk runs: $n, want 3)"
if [ "$n" = 3 ]; then echo ok; else echo "FAIL: the prefix is too small to test the filter"; exit 1; fi

echo "== every case of tests/confirm_cleanup_test.sh, behind a $(wc -c < "$PREFIX")-byte here-doc =="
out=$(CLEANUP_TEST_PREFIX_FILE="$PREFIX" bash "$HERE/confirm_cleanup_test.sh" 2>&1); rc=$?
grep -E 'FAIL' <<<"$out"
tail -1 <<<"$out"
exit $rc
