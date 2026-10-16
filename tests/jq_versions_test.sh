#!/bin/bash
# #95: the hooks' one-call jq fast path must compile on jq 1.6 (Ubuntu 22.04 / WSL
# default) as well as 1.7. The 1.7-only `sub("\n+\z"; "")` made it fail on 1.6, so
# every call fell back to one jq per field. This test runs the process-count test
# and the trailing-newline equivalence cases under each jq version it can find.
#   ABF_JQ16 / ABF_JQ17 name a binary; otherwise /usr/bin/jq and /usr/local/bin/jq.
# A version that cannot be found (or is not that version) prints SKIP, never PASS.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0
ok()   { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; fails=$((fails+1)); }
skip() { echo "SKIP: $1"; }

find_jq() { # find_jq <override> <default> <version-prefix>
  local c
  for c in "$1" "$2"; do
    [ -n "$c" ] && [ -x "$c" ] || continue
    case "$("$c" --version 2>/dev/null)" in "jq-$3"*) echo "$c"; return 0 ;; esac
  done
  return 1
}
JQ16=$(find_jq "${ABF_JQ16:-}" /usr/bin/jq 1.6) || JQ16=""
JQ17=$(find_jq "${ABF_JQ17:-}" /usr/local/bin/jq 1.7) || JQ17=""
[ -n "$JQ17" ] || JQ17=$(find_jq "" "$(command -v jq 2>/dev/null)" 1.7) || JQ17=""

# --- the program text the four hooks really carry ----------------------------
DEF='def t: if endswith("\n") then .[:-1] | t else . end;'
for h in confirm_cleanup confirm_launch confirm_walkthrough guard_plugin_files; do
  if grep -qF "$DEF" "$ROOT/hooks/$h.sh" && grep -qF 'map(t + "\u001f")' "$ROOT/hooks/$h.sh" \
     && ! grep -qF 'sub("\\n+\\z"' "$ROOT/hooks/$h.sh"; then
    ok "hooks/$h.sh carries the regex-free strip"
  else
    bad "hooks/$h.sh does not carry the regex-free strip (def t / map(t + ...))"
  fi
done
OLD='[.] | map(sub("\\n+\\z"; "") + "\u001f") | join("")'
NEW="$DEF [.] | map(t + \"\u001f\") | join(\"\")"

# --- inputs (TC-007..TC-015) --------------------------------------------------
IN="$TMP/in"; mkdir -p "$IN"
printf 'ls -la' > "$IN/none"
printf 'ls -la\n' > "$IN/one"
printf 'ls -la\n\n\n' > "$IN/many"
printf '\n\n\n' > "$IN/only"
printf 'a\nb\n\nc\n' > "$IN/interior"
printf 'a\r\n' > "$IN/crlf"
printf 'a\r' > "$IN/cr"
printf '中文 😀 text\n\n' > "$IN/unicode"
{ head -c 100000 /dev/zero | tr '\0' x; printf '\n'; } > "$IN/big"
{ printf 'body'; yes '' | head -n 5000; } > "$IN/nl5000"

run_equiv() { # run_equiv <jq> <label> : new program on every input; compare with old on 1.7
  local J="$1" label="$2" f n
  command -v timeout >/dev/null 2>&1 && local TO="timeout 60" || local TO=""
  for f in "$IN"/*; do
    n=$(basename "$f")
    "$J" -Rs . "$f" > "$TMP/$n.json"
    $TO "$J" -j "$NEW" "$TMP/$n.json" > "$TMP/$n.new.$label" 2>/dev/null
    if [ -n "$JQ17" ]; then
      [ -f "$TMP/$n.old" ] || "$JQ17" -j "$OLD" "$TMP/$n.json" > "$TMP/$n.old" 2>/dev/null
      if cmp -s "$TMP/$n.new.$label" "$TMP/$n.old"; then ok "equiv $n on $label"; else bad "equiv $n on $label differs from old program"; fi
    else
      [ -s "$TMP/$n.new.$label" ] && ok "equiv $n on $label (no 1.7 reference)" || bad "equiv $n on $label produced nothing"
    fi
  done
}

run_version() { # run_version <jq-or-empty> <label>
  local J="$1" label="$2" d out
  if [ -z "$J" ]; then skip "jq $label not found (or not that version); this half did not run"; return; fi
  d="$TMP/shim-$label"; mkdir -p "$d"; ln -s "$J" "$d/jq"
  echo "--- jq $label: $("$J" --version) at $J"
  out=$(PATH="$d:$PATH" bash "$HERE/gate_process_count_test.sh" 2>&1); rc=$?
  echo "$out" | tail -n 4
  if [ $rc -eq 0 ] && echo "$out" | grep -q 'all passed'; then ok "gate_process_count_test.sh under jq $label"; else bad "gate_process_count_test.sh under jq $label"; fi
  run_equiv "$J" "$label"
}

run_version "$JQ16" 1.6
run_version "$JQ17" 1.7

if [ -n "$JQ16" ] && [ -n "$JQ17" ]; then
  for f in "$IN"/*; do n=$(basename "$f")
    cmp -s "$TMP/$n.new.1.6" "$TMP/$n.new.1.7" && ok "1.6 and 1.7 agree on $n" || bad "1.6 and 1.7 disagree on $n"
  done
fi

[ "$fails" -eq 0 ] && { echo "all passed"; exit 0; }
echo "$fails failed"; exit 1
