#!/bin/bash
# Stage S1 (tasks.md T001, T002): scripts/egress_allow.sh - validation, add,
# remove, list, domains - against a temporary settings root.
#
# Nothing existing: no test in this repo already exercises a per-deployment
# addition to the relay's allowlist, so this is a new, self-contained file.
#
# Self-contained: builds its own LAB_SETTINGS_FILE fixture per case, the way
# tests/settings_test.sh does, rather than touching a real deployment.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SCRIPT="$ROOT/scripts/egress_allow.sh"

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()   { printf '%-72s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has() { printf '%-72s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: nothing matching '$2' in: $3"; fails=$((fails+1)); }; }
ok_rc()   { printf '%-72s ' "$1"; [ "$2" -eq 0 ] && echo ok || { echo "FAIL: exit $2, wanted 0. output: $3"; fails=$((fails+1)); }; }
fail_rc() { printf '%-72s ' "$1"; [ "$2" -ne 0 ] && echo ok || { echo "FAIL: exit 0 (should have refused). output: $3"; fails=$((fails+1)); }; }

newroot() {  # newroot -> prints a fresh LAB_SETTINGS_FILE path
    # mktemp -d directly, not a hand-rolled counter: a counter variable bumped
    # inside `$(newroot)` only ever changes the subshell command substitution
    # forks, never this script's own - every call would return the same
    # directory (measured: it did, three cases silently shared one root).
    local r; r="$(mktemp -d "$TMP/root.XXXXXX")"
    mkdir -p "$r/config"
    printf '%s\n' "$r/config/env.yaml"
}

# count <pattern> <file> -> exactly one line, the match count.
# Not `grep -c ... || echo 0`: grep -c already prints "0" and exits 1 when a
# readable file has no match, so that idiom double-prints "0\n0" in exactly
# the case it exists to handle.
count() {
    [ -r "$2" ] || { echo 0; return; }
    grep -Fc -- "$1" "$2" 2>/dev/null
}
# count_in <pattern> <text> -> same, against a string instead of a file.
count_in() {
    grep -Fc -- "$1" <<<"$2" 2>/dev/null
}

# call <settings-file> <egress_allow.sh args...> -> sets $OUT and $RC.
# Deliberately NOT wrapped in its own $(...): the exit code of the command it
# runs must land in the CALLER's shell, and `x=$(f)` with `$?` read inside f
# would only ever see the subshell that command substitution forks.
call() {
    local sf="$1"; shift
    OUT=$(LAB_SETTINGS_FILE="$sf" bash "$SCRIPT" "$@" 2>&1)
    RC=$?
}

# =============================================================================
# T001 [TC-005, TC-006, TC-018] validation
# =============================================================================

SF1="$(newroot)"

# TC-005: wildcard, IP literals, a single-label TLD, and empty are all refused.
for bad in '*' 'com' '0.0.0.0' '10.1.2.3' '::1' ''; do
    call "$SF1" add "$bad" --reason "should never be written"
    fail_rc "TC-005 add '$bad' is refused" "$RC" "$OUT"
done

# TC-005: two labels with an empty segment in between.
call "$SF1" add "a..b" --reason "should never be written"
fail_rc "TC-005 add 'a..b' is refused" "$RC" "$OUT"

# TC-005: a label over 63 characters.
LONGLABEL="$(printf 'a%.0s' $(seq 1 64))"
call "$SF1" add "${LONGLABEL}.org" --reason "should never be written"
fail_rc "TC-005 add a 64-char label is refused" "$RC" "$OUT"

# TC-005: a label may not start with a hyphen.
call "$SF1" add "-x.org" --reason "should never be written"
fail_rc "TC-005 add '-x.org' is refused" "$RC" "$OUT"

# TC-006: an ordinary subdomain is accepted, with a reason.
call "$SF1" add "download.example.org" --reason "nf-core pipeline needs it"
ok_rc "TC-006 add 'download.example.org' is accepted" "$RC" "$OUT"

# TC-006: mixed case and a trailing dot are normalised to lowercase, no dot.
call "$SF1" add "Example.ORG." --reason "normalisation check"
ok_rc "TC-006 add 'Example.ORG.' is accepted" "$RC" "$OUT"
CONF1="$(dirname "$SF1")"
TSV1="$CONF1/egress_allow.tsv"
STORED1="$(cat "$TSV1" 2>/dev/null)"
has "TC-006 stored lowercase, no trailing dot" "example.org" "$STORED1"
t "TC-006 the original mixed-case spelling is not stored" \
  "$(count 'Example.ORG' "$TSV1")" "0"

# TC-018: add without --reason refuses.
call "$SF1" add "noreason.example.org"
fail_rc "TC-018 add with no --reason refuses" "$RC" "$OUT"
t "TC-018 nothing was written for it" "$(count 'noreason.example.org' "$TSV1")" "0"

# TC-018: add with an empty --reason refuses.
call "$SF1" add "emptyreason.example.org" --reason ""
fail_rc "TC-018 add with an empty --reason refuses" "$RC" "$OUT"
t "TC-018 nothing was written for it either" "$(count 'emptyreason.example.org' "$TSV1")" "0"

# Developer review: a reason is one field of one line. A tab or newline in it
# would split the line and could plant a second entry that never went through
# `add`'s checks. It is stored with those characters turned into spaces.
before=$(awk 'END {print NR}' "$TSV1")
call "$SF1" add "inject.example.org" --reason $'first\nplanted.example.org\t2026-01-01\tx'
after=$(awk 'END {print NR}' "$TSV1")
t "reason with a newline: exactly one line written" "$((after - before))" "1"
t "reason with a newline: no line starts with the planted domain" \
  "$(awk -F'\t' '$1 == "planted.example.org"' "$TSV1" | awk 'END {print NR}')" "0"
t "reason with a tab: the line still has exactly three fields" \
  "$(awk -F'\t' '$1 == "inject.example.org" {print NF}' "$TSV1")" "3"
t "reason with a tab: domains does not list the planted one" \
  "$(call "$SF1" domains; count_in 'planted.example.org' "$OUT")" "0"

# T001: more than 100 entries refuses.
SF2="$(newroot)"
CONF2="$(dirname "$SF2")"
TSV2="$CONF2/egress_allow.tsv"
for i in $(seq 1 100); do
    printf 'd%d.example.org\t2026-01-01\tseed entry %d\n' "$i" "$i" >> "$TSV2"
done
call "$SF2" add "d101.example.org" --reason "the 101st entry"
fail_rc "T001 the 101st entry is refused" "$RC" "$OUT"
has "T001 the refusal names the limit" "100" "$OUT"
t "T001 the 101st domain was not written" "$(count 'd101.example.org' "$TSV2")" "0"

# =============================================================================
# T002 [TC-001, TC-014, TC-015, TC-017] add/list/remove/domains
# =============================================================================

SF3="$(newroot)"
CONF3="$(dirname "$SF3")"
TSV3="$CONF3/egress_allow.tsv"

# TC-001: add writes domain<TAB>date<TAB>reason to <root>/config/egress_allow.tsv
call "$SF3" add "rawdata.example.org" --reason "run 42 needed it"
ok_rc "TC-001 add succeeds" "$RC" "$OUT"
TODAY="$(date +%Y-%m-%d)"
EXPECT_LINE="$(printf 'rawdata.example.org\t%s\trun 42 needed it' "$TODAY")"
ACTUAL_LINE="$(grep -F 'rawdata.example.org' "$TSV3")"
t "TC-001 the stored line is domain<TAB>date<TAB>reason" "$ACTUAL_LINE" "$EXPECT_LINE"

# Duplicate add: says already present, does not error, does not duplicate the line.
call "$SF3" add "rawdata.example.org" --reason "a different reason"
ok_rc "T002 a duplicate add is not an error" "$RC" "$OUT"
has "T002 a duplicate add says already present" "already present" "$OUT"
t "T002 the line was not duplicated" "$(grep -c 'rawdata.example.org' "$TSV3")" "1"

# A second, real domain plus a hand-added line with no date or reason.
call "$SF3" add "second.example.org" --reason "another run"
printf 'manualdomain.org\n' >> "$TSV3"

# TC-014: list shows domain, date and reason for a normal entry.
call "$SF3" list
has "TC-014 list shows the domain" "rawdata.example.org" "$OUT"
has "TC-014 list shows the date" "$TODAY" "$OUT"
has "TC-014 list shows the reason" "run 42 needed it" "$OUT"

# TC-017: a hand-added line with no date/reason is flagged, not silently dropped.
EXPECT_UNKNOWN="$(printf 'manualdomain.org\t來源不明')"
has "TC-017 a hand-added entry is flagged 來源不明" "$EXPECT_UNKNOWN" "$OUT"

# TC-015: remove deletes the line.
call "$SF3" remove "second.example.org"
ok_rc "TC-015 remove succeeds" "$RC" "$OUT"
t "TC-015 the line is gone" "$(count 'second.example.org' "$TSV3")" "0"

# T002: domains prints the comma list.
call "$SF3" domains
has "T002 domains lists the first domain" "rawdata.example.org" "$OUT"
has "T002 domains lists the hand-added (valid-shaped) domain" "manualdomain.org" "$OUT"
t "T002 domains no longer lists the removed one" "$(count_in 'second.example.org' "$OUT")" "0"

# Independent acceptance of 002, M4: `list` showed hand-added entries the relay
# will never load (`domains` drops them) as if they were in force.
SF4="$(newroot)"; TSV4="$(dirname "$SF4")/egress_allow.tsv"
printf '*.wild.org\t2026-01-01\tr\ncom\nok.example.org\t2026-01-01\tr\nhand.example.org\r\n' > "$TSV4"
call "$SF4" list
has "list marks a wildcard line as not in force" "$(printf '*.wild.org\t格式不符，不會生效')" "$OUT"
has "list marks a bare TLD line as not in force" "$(printf 'com\t格式不符，不會生效')" "$OUT"
has "list still shows a valid line normally"     "$(printf 'ok.example.org\t2026-01-01\tr')" "$OUT"
DOMS4="$(LAB_SETTINGS_FILE="$SF4" bash "$SCRIPT" domains 2>/dev/null)"
t "a CRLF-ended hand line still loads (the CR is not part of the name)" \
  "$DOMS4" "ok.example.org,hand.example.org"

# TC-012 [FR-009]: the commands' "allow it" step names this mechanism, and no
# sentence tells anyone to edit plugin files to let a host through.
for f in commands/runs.md commands/launch.md; do
    has "TC-012 $f names egress_allow.sh add" 'scripts/egress_allow.sh add <host> --reason' "$(cat "$ROOT/$f")"
    t "TC-012 $f never says to edit the relay or its built-in list" \
      "$(grep -ciE '(edit|change|modify|add to)[^.]{0,40}(nf_relay|ALLOW_DOMAINS|plugin file)' "$ROOT/$f")" "0"
done
# TC-013 is checked by hand; the text it checks must at least exist.
has "TC-013 runs.md says the built-in list is the maintainer's change" "maintainer's change" "$(cat "$ROOT/commands/runs.md")"


# =============================================================================
# #45 what "a specific domain" means: public suffixes, wildcard-DNS services,
# names that resolve to loopback/internal addresses by their spelling, length,
# and control characters in a reason.
# =============================================================================
SF5="$(newroot)"; TSV5="$(dirname "$SF5")/egress_allow.tsv"
for bad in co.uk com.au org.tw github.io gitlab.io herokuapp.com nip.io sslip.io xip.io \
           127.0.0.1.nip.io foo.nip.io 10.0.0.5.example.com localhost.localdomain printer.local \
           db.internal nas.lan a.localhost; do
    call "$SF5" add "$bad" --reason "should never be written"
    fail_rc "#45 add '$bad' is refused" "$RC" "$OUT"
done
t "#45 none of them was written" "$( [ -r "$TSV5" ] && awk 'END {print NR+0}' "$TSV5" || echo 0)" "0"
has "#45 the refusal says why (a shared or wildcard name)" "shared" "$(call "$SF5" add co.uk --reason r; echo "$OUT")"
for good in bbc.co.uk user.github.io download.example.org mirror.lab.test.example.org; do
    call "$SF5" add "$good" --reason "an ordinary specific host"
    ok_rc "#45 control: add '$good' is accepted" "$RC" "$OUT"
done
# a name over 253 characters (the relay refuses it; bash used to accept it)
LONGNAME="$(for i in 1 2 3 4 5; do printf '%s.' "$(printf 'a%.0s' $(seq 1 55))"; done)org"
call "$SF5" add "$LONGNAME" --reason "too long"
fail_rc "#45 a name over 253 characters is refused" "$RC" "$OUT"
# --reason: every control character becomes a space (VT, FF, US, and the C1 NEL)
before=$(awk 'END {print NR+0}' "$TSV5")
call "$SF5" add "ctl.example.org" --reason "$(printf 'a\vb\fc\037d\302\205e')"
after=$(awk 'END {print NR+0}' "$TSV5")
t "#45 a reason with VT, FF, US and NEL: still one line" "$((after - before))" "1"
t "#45 ...and the stored reason holds none of them" \
  "$(awk -F'\t' '$1=="ctl.example.org"{print $3}' "$TSV5")" "a b c d e"
# the stderr note of `domains` does not carry the machine's own path
printf 'good.example.org\t2026-01-01\tr\n*bad\t2026-01-01\tr\n' > "$TSV5"
DOMERR="$(LAB_SETTINGS_FILE="$SF5" bash "$SCRIPT" domains 2>&1 >/dev/null)"
t "#45 the dropped-entry note does not carry the settings path" "$(count_in "$(dirname "$SF5")" "$DOMERR")" "0"
has "#45 ...but still names the dropped entry and the file" "egress_allow.tsv" "$DOMERR"
echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
