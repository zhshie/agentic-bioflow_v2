#!/bin/bash
# Ratchet: the same shell function name defined in more than one script under
# scripts/**/*.sh. Each script is meant to run standalone (one script, one job),
# so some small helpers (die, usage, say) are copied on purpose; but every copy
# is a place a fix has to be made twice, and a new copy of a name that already
# exists elsewhere is usually a helper that should have been sourced from
# scripts/utils/ instead.
#
# tests/shell_helper_dupes_baseline.txt holds today's set, one "<name><TAB><file>"
# line per definition of a name that is defined in two or more files. The test:
#   - fails on a (name, file) pair that is duplicated now and not in the baseline
#     (a new duplicate, or a new copy of an old one);
#   - fails on a baseline line that is no longer a duplicate (the baseline may only
#     shrink: delete the line so the gain is kept).
# It never fails because the baseline is long. To pay one down, source one copy
# from scripts/utils/ and delete its lines here. `bash tests/shell_helper_dupes_test.sh
# --print` prints today's set in the baseline's format.
#
# A function is a line that starts (after indentation) with `name()` or
# `function name`. A name defined twice inside ONE file is not counted: that is
# a redefinition, not a duplicate across scripts. Static, bash 3.2 safe (no
# arrays, no mapfile), no network, no site.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
BASELINE="${SHELL_HELPER_DUPES_BASELINE:-$HERE/shell_helper_dupes_baseline.txt}"
fails=0
TMP="$(mktemp -d "${TMPDIR:-/tmp}/shdupes.XXXXXX")" || exit 1
trap 'rm -rf "$TMP"' EXIT

ok()   { printf 'ok    %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; fails=$((fails+1)); }

# dupes <root> -> "<name>\t<file>" for every definition of a name found in 2+ files,
# sorted, files relative to <root>.
dupes() {
    ( cd "$1" || exit 1
      find scripts -name '*.sh' 2>/dev/null | LC_ALL=C sort | while IFS= read -r f; do
          sed -nE \
              -e 's/^[[:space:]]*function[[:space:]]+([A-Za-z_][A-Za-z0-9_:.-]*).*/\1/p' \
              -e 's/^[[:space:]]*([A-Za-z_][A-Za-z0-9_:.-]*)[[:space:]]*\(\)[[:space:]]*(\{.*)?$/\1/p' \
              "$f" | LC_ALL=C sort -u | while IFS= read -r n; do
                  printf '%s\t%s\n' "$n" "$f"
              done
      done > "$TMP/all.$$"
      cut -f1 "$TMP/all.$$" | LC_ALL=C sort | uniq -d > "$TMP/names.$$"
      while IFS= read -r n; do
          [ -n "$n" ] || continue
          awk -F'\t' -v n="$n" '$1 == n' "$TMP/all.$$"
      done < "$TMP/names.$$" | LC_ALL=C sort
    )
}

# compare <current> <baseline> -> prints problems, returns the count via stdout lines
compare() {
    LC_ALL=C sort -u "$2" | grep -vE '^[[:space:]]*(#|$)' > "$TMP/base.$$" || true
    LC_ALL=C sort -u "$1" > "$TMP/cur.$$"
    LC_ALL=C comm -13 "$TMP/base.$$" "$TMP/cur.$$" | while IFS=$'\t' read -r n f; do
        echo "NEW   $n in $f is a duplicate of a helper already defined in another script"
    done
    LC_ALL=C comm -23 "$TMP/base.$$" "$TMP/cur.$$" | while IFS=$'\t' read -r n f; do
        echo "STALE $n in $f is no longer a duplicate: delete its line from the baseline"
    done
}

if [ "${1:-}" = "--print" ]; then   # prints today's set in baseline format
    dupes "$ROOT"; exit 0
fi

# --- the real tree ---------------------------------------------------------
if [ ! -f "$BASELINE" ]; then
    fail "baseline missing: $BASELINE (generate it from the current tree)"
else
    dupes "$ROOT" > "$TMP/real.cur"
    problems=$(compare "$TMP/real.cur" "$BASELINE")
    if [ -z "$problems" ]; then
        ok "scripts/**/*.sh: no helper duplicate beyond the baseline ($(wc -l < "$TMP/real.cur" | tr -d ' ') definitions of $(cut -f1 "$TMP/real.cur" | LC_ALL=C sort -u | wc -l | tr -d ' ') names)"
    else
        fail "scripts/**/*.sh helper duplicates differ from the baseline"
        echo "$problems" | sed 's/^/      /'
    fi
fi

# --- the detector itself, on a fixture (so a broken scanner cannot go green) -
FX="$TMP/fx"; mkdir -p "$FX/scripts/utils"
printf 'die() { echo x; exit 1; }\nonly_a() { :; }\n' > "$FX/scripts/a.sh"
printf 'function die {\n  :\n}\n  helper_b ()\n{\n:\n}\n' > "$FX/scripts/b.sh"
printf 'die(){ :; }\nhelper_b() { :; }\nrepeat() { :; }\nrepeat() { :; }\n' > "$FX/scripts/utils/c.sh"
printf '# die() { not code }\nx=$(die)\n' > "$FX/scripts/d.sh"
dupes "$FX" > "$TMP/fx.cur"
want=$(printf 'die\tscripts/a.sh\ndie\tscripts/b.sh\ndie\tscripts/utils/c.sh\nhelper_b\tscripts/b.sh\nhelper_b\tscripts/utils/c.sh\n')
if [ "$(cat "$TMP/fx.cur")" = "$want" ]; then ok "detector: finds name() / function name / one-line forms, ignores comments, calls and same-file redefinition"
else fail "detector: fixture result wrong"; sed 's/^/      /' "$TMP/fx.cur"; fi

: > "$TMP/empty.base"
if [ -n "$(compare "$TMP/fx.cur" "$TMP/empty.base")" ]; then ok "ratchet: a duplicate absent from the baseline is reported"
else fail "ratchet: a new duplicate was NOT reported"; fi

cp "$TMP/fx.cur" "$TMP/full.base"
if [ -z "$(compare "$TMP/fx.cur" "$TMP/full.base")" ]; then ok "ratchet: a duplicate listed in the baseline passes"
else fail "ratchet: a baselined duplicate was reported"; fi

grep -v 'scripts/b.sh' "$TMP/fx.cur" > "$TMP/third.base"
third=$(compare "$TMP/fx.cur" "$TMP/third.base")
if grep -q '^NEW   die in scripts/b.sh' <<< "$third"; then ok "ratchet: a new copy of an already-duplicated name is reported"
else fail "ratchet: a new copy of an old duplicate was NOT reported"; fi

{ cat "$TMP/fx.cur"; printf 'gone\tscripts/a.sh\n'; } > "$TMP/stale.base"
stale=$(compare "$TMP/fx.cur" "$TMP/stale.base")
if grep -q '^STALE gone' <<< "$stale"; then ok "ratchet: a baseline line that is no longer a duplicate is reported (baseline only shrinks)"
else fail "ratchet: a stale baseline line was NOT reported"; fi

if [ "$fails" -eq 0 ]; then echo "all passed"; exit 0; fi
echo "$fails failed"; exit 1
