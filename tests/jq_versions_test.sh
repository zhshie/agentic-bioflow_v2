#!/bin/bash
# #95: the hooks' one-call jq fast path must compile and give the same answer on jq
# 1.6 (Ubuntu 22.04 / WSL default) as on 1.7.x / 1.8.x. On 1.6 `contains("\u0000")`
# is true for every string (C-string compare), so the NUL guard made the program
# print nothing and every call fell back to one jq per field. The guard is
# `test("\u0000")`.
#
# This test takes the program text out of each of the four hooks (not a copy of it)
# and runs it under every jq version it can find: ABF_JQ16 / ABF_JQ17 / ABF_JQ18,
# /usr/bin/jq, /usr/local/bin/jq and the first jq on PATH, each labelled with its
# real --version. A version that is not found prints SKIP, never PASS; if no version
# ran at all the test FAILS.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0
ok()   { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; fails=$((fails+1)); }
skip() { echo "SKIP: $1"; }

HOOKS="confirm_cleanup confirm_launch confirm_walkthrough guard_plugin_files"

# --- the program text each hook really carries --------------------------------
extract() { # extract <hook> : print the fast-path jq program of hooks/<hook>.sh
  local line n
  n=$(grep -cF "jq -js '" "$ROOT/hooks/$1.sh")
  [ "$n" = 1 ] || return 1
  line=$(grep -F "jq -js '" "$ROOT/hooks/$1.sh")
  line=${line#*"jq -js '"}
  printf '%s' "${line%%"' <<<"*}"
}
for h in $HOOKS; do
  if p=$(extract "$h") && [ -n "$p" ]; then printf '%s' "$p" > "$TMP/prog.$h"; ok "extracted the fast-path program from hooks/$h.sh"
  else bad "could not extract exactly one fast-path program from hooks/$h.sh"; : > "$TMP/prog.$h"; fi
done

# Static: the parts every hook shares must be identical text in all four, and the
# 1.6-unsafe form must be gone.
HEAD_='if length == 1 then (.[0] | ['
GUARD='if all(.[]; type == "string") and (any(.[]; contains("\u001f") or test("\u0000")) | not) then'
TAIL_='(map(sub("\\n+\\z"; "") + "\u001f") | join("")) else empty end) else empty end'
for part in HEAD_ GUARD TAIL_; do
  want=${!part}; same=1
  for h in $HOOKS; do grep -qF -- "$want" "$TMP/prog.$h" || same=0; done
  if [ "$same" = 1 ]; then ok "all four hooks carry the identical $part text"
  else bad "the four hooks do not all carry the identical $part text: $want"; fi
done
for h in $HOOKS; do
  if grep -qF 'contains("\u0000")' "$TMP/prog.$h"; then bad "hooks/$h.sh still uses contains(\"\\u0000\") (true for every string on jq 1.6)"
  else ok "hooks/$h.sh has no contains(\"\\u0000\")"; fi
done

# --- versions ------------------------------------------------------------------
LABELS=(); BINS=()
consider() { # consider <path>
  local c="$1" v l
  [ -n "$c" ] && [ -x "$c" ] || return 0
  v=$("$c" --version 2>/dev/null) || return 0
  case "$v" in jq-1.6|jq-1.7*|jq-1.8*) ;; *) return 0 ;; esac
  for l in ${LABELS[@]+"${LABELS[@]}"}; do [ "$l" = "$v" ] && return 0; done
  LABELS+=("$v"); BINS+=("$c")
}
consider "${ABF_JQ16:-}"; consider /usr/bin/jq
consider "${ABF_JQ17:-}"; consider /usr/local/bin/jq
consider "${ABF_JQ18:-}"; consider "$(command -v jq 2>/dev/null)"
if [ -n "${ABF_JQ16:-}" ] && [ "$("$ABF_JQ16" --version 2>/dev/null)" != "jq-1.6" ]; then
  bad "ABF_JQ16=$ABF_JQ16 is set but is not a working jq 1.6 (got: $("$ABF_JQ16" --version 2>&1 | head -n1))"
else
  case " ${LABELS[*]:-} " in *" jq-1.6 "*) ;; *) skip "jq 1.6 not found; the 1.6 half did not run" ;; esac
fi
if [ "${#LABELS[@]}" -eq 0 ]; then
  bad "no usable jq (1.6, 1.7.x or 1.8.x) found: nothing ran"; echo "$fails failed"; exit 1
fi

# --- inputs ----------------------------------------------------------------------
# JSON fed to a hook: tool_name Bash; command = V; file_path p; content c;
# transcript_path t. The expected answer lists the fields in the order the hook emits.
US=$'\037'
mkjson() { # mkjson <json-escaped V> <out file>
  printf '{"tool_name":"Bash","tool_input":{"command":"%s","file_path":"p","content":"c"},"transcript_path":"t"}' "$1" > "$2"
}
expect() { # expect <hook> <stripped V> <out file>
  case "$1" in
    confirm_cleanup)     printf 'abf-jq-ok%sBash%s%s%s' "$US" "$US" "$2" "$US" > "$3" ;;
    confirm_launch)      printf 'Bash%s%s%s' "$US" "$2" "$US" > "$3" ;;
    confirm_walkthrough) printf 'Bash%s%s%sp%sc%st%s' "$US" "$2" "$US" "$US" "$US" "$US" > "$3" ;;
    guard_plugin_files)  printf 'Bash%sp%s%s%s' "$US" "$US" "$2" "$US" > "$3" ;;
  esac
}
# name | JSON-escaped value | stripped value (printf %b form)
CASES=(
  'none|ls -la|ls -la'
  'one|ls -la\n|ls -la'
  'many|ls -la\n\n\n|ls -la'
  'only|\n\n\n|'
  'interior|a\nb\n\nc\n|a\nb\n\nc'
  'crlf|a\r\n|a\r'
  'cr|a\r|a\r'
  'unicode|中文 😀 text\n\n|中文 😀 text'
)
# Inputs whose fast-path answer must be EMPTY (the hook then takes its slow path)
EMPTY_CASES=(
  'embedded-NUL|a\u0000b'
  'embedded-0x1f|a\u001fb'
  'NUL-and-0x1f|a\u0000b\u001fc'
  'NUL-only|\u0000'
  'NUL-plus-trailing-newline|a\u0000\n\n'
)

run_prog() { # run_prog <jq> <hook> <input> <out> : sets RC; stderr in <out>.err
  if command -v timeout >/dev/null 2>&1; then
    timeout 30 "$1" -js "$(cat "$TMP/prog.$2")" "$3" > "$4" 2> "$4.err"; RC=$?
  else
    "$1" -js "$(cat "$TMP/prog.$2")" "$3" > "$4" 2> "$4.err"; RC=$?
  fi
}
errtxt() { head -c 200 "$1.err" | tr '\n' ' '; }

# 1 MB body of x, and 20,000 JSON-escaped newlines
head -c 1000000 /dev/zero | tr '\0' x > "$TMP/big.body"
NLK=$(printf '\\n%.0s' $(seq 1 1000))
: > "$TMP/nl.json"
k=0; while [ $k -lt 20 ]; do printf '%s' "$NLK" >> "$TMP/nl.json"; k=$((k+1)); done
[ "$(wc -c < "$TMP/nl.json")" -eq 40000 ] || bad "test setup: nl.json is not 20,000 newline escapes"

check_version() { # check_version <jq> <label>
  local J="$1" label="$2" h c name val want ms t0 t1
  for h in $HOOKS; do
    for c in "${CASES[@]}"; do
      IFS='|' read -r name val want <<<"$c"
      mkjson "$val" "$TMP/in.json"
      expect "$h" "$(printf '%b' "$want")" "$TMP/exp"
      run_prog "$J" "$h" "$TMP/in.json" "$TMP/out"
      if [ "$RC" -eq 0 ] && [ -s "$TMP/out" ] && [ ! -s "$TMP/out.err" ] && cmp -s "$TMP/out" "$TMP/exp"; then
        ok "$label $h $name"
      else
        bad "$label $h $name (rc=$RC, $(wc -c < "$TMP/out") bytes out, stderr: $(errtxt "$TMP/out"))"
      fi
      cp "$TMP/out" "$TMP/res.$h.$name.$label"
    done
    for c in "${EMPTY_CASES[@]}"; do
      IFS='|' read -r name val <<<"$c"
      mkjson "$val" "$TMP/in.json"
      run_prog "$J" "$h" "$TMP/in.json" "$TMP/out"
      if [ "$RC" -eq 0 ] && [ ! -s "$TMP/out" ] && [ ! -s "$TMP/out.err" ]; then ok "$label $h $name -> empty (slow path)"
      else bad "$label $h $name should be empty with rc 0 (rc=$RC, $(wc -c < "$TMP/out") bytes out, stderr: $(errtxt "$TMP/out"))"; fi
      cp "$TMP/out" "$TMP/res.$h.$name.$label"
    done

    # mixed: a clean command with a NUL in file_path. confirm_walkthrough and
    # guard_plugin_files read file_path, so they must give empty; the other two do not.
    printf '{"tool_name":"Bash","tool_input":{"command":"ok\\n","file_path":"a\\u0000b","content":"c"},"transcript_path":"t"}' > "$TMP/in.json"
    run_prog "$J" "$h" "$TMP/in.json" "$TMP/out"
    case "$h" in
      confirm_walkthrough|guard_plugin_files)
        if [ "$RC" -eq 0 ] && [ ! -s "$TMP/out" ] && [ ! -s "$TMP/out.err" ]; then ok "$label $h NUL in a later field -> empty"
        else bad "$label $h NUL in a later field should be empty (rc=$RC, stderr: $(errtxt "$TMP/out"))"; fi ;;
      *)
        if [ "$RC" -eq 0 ] && [ -s "$TMP/out" ] && [ ! -s "$TMP/out.err" ]; then ok "$label $h NUL in an unread field -> still answers"
        else bad "$label $h NUL in an unread field should still answer (rc=$RC, stderr: $(errtxt "$TMP/out"))"; fi ;;
    esac
    # a non-string field (transcript_path: 5) -> empty on the hook that reads it
    printf '{"tool_name":"Bash","tool_input":{"command":"ok\\n","file_path":"p","content":"c"},"transcript_path":5}' > "$TMP/in.json"
    run_prog "$J" "$h" "$TMP/in.json" "$TMP/out"
    if [ "$h" = confirm_walkthrough ]; then
      if [ "$RC" -eq 0 ] && [ ! -s "$TMP/out" ] && [ ! -s "$TMP/out.err" ]; then ok "$label $h non-string field -> empty"
      else bad "$label $h non-string field should be empty (rc=$RC, stderr: $(errtxt "$TMP/out"))"; fi
    fi

    # 1 MB body ending in 20,000 newlines: same answer, and under 2 s
    { printf '{"tool_name":"Bash","tool_input":{"command":"'; cat "$TMP/big.body" "$TMP/nl.json"
      printf '","file_path":"p","content":"c"},"transcript_path":"t"}'; } > "$TMP/in.json"
    expect "$h" "$(cat "$TMP/big.body")" "$TMP/exp"
    t0=$(date +%s%N)
    run_prog "$J" "$h" "$TMP/in.json" "$TMP/out"
    t1=$(date +%s%N); ms=$(( (t1 - t0) / 1000000 ))
    if [ "$RC" -eq 0 ] && [ -s "$TMP/out" ] && [ ! -s "$TMP/out.err" ] && cmp -s "$TMP/out" "$TMP/exp"; then
      ok "$label $h 1 MB body + 20,000 trailing newlines: correct"
    else
      bad "$label $h 1 MB body + 20,000 trailing newlines: wrong (rc=$RC, $(wc -c < "$TMP/out") bytes out, stderr: $(errtxt "$TMP/out"))"
    fi
    if [ "$ms" -lt 2000 ]; then ok "$label $h big body took ${ms} ms (< 2000)"; else bad "$label $h big body took ${ms} ms (limit 2000)"; fi
  done
}

# --- run each version --------------------------------------------------------------
i=0
while [ "$i" -lt "${#LABELS[@]}" ]; do
  label="${LABELS[$i]}"; J="${BINS[$i]}"; i=$((i+1))
  echo "--- $label at $J"
  d="$TMP/shim-$label"; mkdir -p "$d"; ln -s "$J" "$d/jq" 2>/dev/null || cp "$J" "$d/jq"
  if [ "$("$d/jq" --version 2>/dev/null)" = "$label" ]; then ok "shim for $label reports $label"
  else bad "shim for $label reports '$("$d/jq" --version 2>&1)', not $label"; continue; fi
  check_version "$d/jq" "$label"
  out=$(PATH="$d:$PATH" bash "$HERE/gate_process_count_test.sh" 2>&1); rc=$?
  echo "$out" | tail -n 3
  if [ $rc -eq 0 ] && echo "$out" | grep -q 'all passed'; then ok "gate_process_count_test.sh under $label"
  else bad "gate_process_count_test.sh under $label (rc=$rc)"; fi
done

# --- versions agree --------------------------------------------------------------------
if [ "${#LABELS[@]}" -gt 1 ]; then
  for f in "$TMP"/res.*."${LABELS[0]}"; do
    base=${f%."${LABELS[0]}"}; k=1
    while [ "$k" -lt "${#LABELS[@]}" ]; do
      if cmp -s "$f" "$base.${LABELS[$k]}"; then ok "${LABELS[0]} and ${LABELS[$k]} agree on $(basename "$base")"
      else bad "${LABELS[0]} and ${LABELS[$k]} disagree on $(basename "$base")"; fi
      k=$((k+1))
    done
  done
fi

if [ "$fails" -eq 0 ]; then echo "all passed"; exit 0; fi
echo "$fails failed"; exit 1
