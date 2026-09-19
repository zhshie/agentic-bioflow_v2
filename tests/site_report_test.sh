#!/bin/bash
# Tests for scripts/site_report.sh (T9): one call bundling agent/resources/
# provenance/inventory, in place of the two or three separate `on_site.sh`
# round trips `commands/downstream.md` used to make back-to-back.
#
# site_report.sh finds its four dependencies beside itself
# (`$(dirname "${BASH_SOURCE[0]}")`), which is also exactly how it runs once
# shipped by `on_site.sh --script` (the whole `scripts/` tree lands in one
# extracted directory on the far end). So this test copies site_report.sh
# into its own scratch `scripts/` directory alongside FAKE
# agent_ctl.sh/check_resource_contract.sh/collect_provenance.py/
# inventory_outputs.py - real stand-ins for real scripts, not a mock of an
# interface this file invents. It never touches this repo's real ones and
# never reaches a real site.
set -uo pipefail
REAL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site_report.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-68s ok\n' "$1"; }
no() { printf '%-68s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
has() { grep -qF -- "$2" <<<"$1"; }

SDIR="$TMP/scripts"; mkdir -p "$SDIR"
cp "$REAL" "$SDIR/site_report.sh"

# fake_agent <rc> <output-line> - agent_ctl.sh online <id>
fake_agent() {
    printf '#!/bin/bash\n[ "$1" = online ] || exit 2\necho "%s"\nexit %s\n' "$2" "$1" > "$SDIR/agent_ctl.sh"
    chmod +x "$SDIR/agent_ctl.sh"
}
fake_resources() {
    printf '#!/bin/bash\necho "%s"\nexit %s\n' "$2" "$1" > "$SDIR/check_resource_contract.sh"
    chmod +x "$SDIR/check_resource_contract.sh"
}
fake_provenance() {
    printf '#!/bin/bash\necho "provenance-called: $*"\nexit 0\n' > "$SDIR/collect_provenance.py"
    chmod +x "$SDIR/collect_provenance.py"
}
fake_inventory() {
    printf '#!/bin/bash\necho "inventory-called: $*"\nexit 0\n' > "$SDIR/inventory_outputs.py"
    chmod +x "$SDIR/inventory_outputs.py"
}
fake_agent 0 "ONLINE - Platform lists 2 report(s)"
fake_resources 0 "OK - every box matches"
fake_provenance
fake_inventory

RESULTS="$TMP/results"; mkdir -p "$RESULTS"

# --- the happy path: all four sections, in order, exit 0 -------------------
out=$("$SDIR/site_report.sh" "$RESULTS" --run-id run123 2>&1); rc=$?
[ "$rc" = 0 ] && ok "everything healthy: exits 0" || no "everything healthy: exits 0" "rc=$rc"
order=$(grep -oE '^== [a-z]+ ==' <<<"$out" | tr -d '\n')
[ "$order" = "== agent ==== resources ==== provenance ==== inventory ==" ] \
    && ok "the four sections appear, always in the same order" \
    || no "the four sections appear, always in the same order" "<<$order>>"
has "$out" "ONLINE - Platform lists 2 report(s)" \
    && ok "the agent section carries agent_ctl.sh's own output" \
    || no "the agent section carries agent_ctl.sh's own output" "<<$out>>"
has "$out" "OK - every box matches" \
    && ok "the resources section carries check_resource_contract.sh's own output" \
    || no "the resources section carries check_resource_contract.sh's own output" "<<$out>>"
has "$out" "provenance-called: --brief --run-id run123 $RESULTS" \
    && ok "provenance is called with --brief and the given run id" \
    || no "provenance is called with --brief and the given run id" "<<$out>>"
has "$out" "inventory-called: $RESULTS" \
    && ok "inventory is called against the results directory" \
    || no "inventory is called against the results directory" "<<$out>>"

# --- no --run-id: agent is skipped, provenance runs without one ------------
out=$("$SDIR/site_report.sh" "$RESULTS" 2>&1); rc=$?
[ "$rc" = 0 ] && ok "no --run-id: still exits 0" || no "no --run-id: still exits 0" "rc=$rc"
has "$out" "skipped - no --run-id given" \
    && ok "no --run-id: the agent section says why it was skipped" \
    || no "no --run-id: the agent section says why it was skipped" "<<$out>>"
has "$out" "provenance-called: --brief $RESULTS" \
    && ok "no --run-id: provenance still runs, just without --run-id" \
    || no "no --run-id: provenance still runs, just without --run-id" "<<$out>>"

# --- the agent being offline is blocking ------------------------------------
fake_agent 1 "OFFLINE - Platform cannot reach this cluster"
out=$("$SDIR/site_report.sh" "$RESULTS" --run-id run123 2>&1); rc=$?
[ "$rc" = 1 ] && ok "an offline agent makes the whole call exit 1" \
             || no "an offline agent makes the whole call exit 1" "rc=$rc"
has "$out" "== resources ==" && has "$out" "== inventory ==" \
    && ok "...but every other section still ran (no early exit)" \
    || no "...but every other section still ran (no early exit)" "<<$out>>"
fake_agent 0 "ONLINE - Platform lists 2 report(s)"

# --- resource-contract drift is blocking too --------------------------------
fake_resources 1 "DRIFT: ngs53g config=8cpu/53G live=8cpu/48G"
out=$("$SDIR/site_report.sh" "$RESULTS" --run-id run123 2>&1); rc=$?
[ "$rc" = 1 ] && ok "resource-contract drift makes the whole call exit 1" \
             || no "resource-contract drift makes the whole call exit 1" "rc=$rc"
has "$out" "== provenance ==" && has "$out" "== inventory =="  \
    && ok "...and every other section still ran" \
    || no "...and every other section still ran" "<<$out>>"
fake_resources 0 "OK - every box matches"

# --- provenance/inventory are informational: never affect the exit code ----
printf '#!/bin/bash\necho "no versions file"\nexit 2\n' > "$SDIR/collect_provenance.py"
chmod +x "$SDIR/collect_provenance.py"
out=$("$SDIR/site_report.sh" "$RESULTS" --run-id run123 2>&1); rc=$?
[ "$rc" = 0 ] && ok "a non-zero exit from provenance does not fail the call" \
             || no "a non-zero exit from provenance does not fail the call" "rc=$rc"
fake_provenance

# --- a results directory that does not exist here: skip, do not crash ------
out=$("$SDIR/site_report.sh" "$TMP/no-such-results" --run-id run123 2>&1); rc=$?
[ "$rc" = 0 ] && ok "a missing results directory: still exits 0" \
             || no "a missing results directory: still exits 0" "rc=$rc"
has "$out" "does not exist here" \
    && ok "a missing results directory: provenance/inventory say so and skip" \
    || no "a missing results directory: provenance/inventory say so and skip" "<<$out>>"

# --- usage ------------------------------------------------------------------
"$SDIR/site_report.sh" >/dev/null 2>&1
[ "$?" = 2 ] && ok "no results directory given at all exits 2" \
             || no "no results directory given at all exits 2" "wrong rc"

"$SDIR/site_report.sh" "$RESULTS" --unknown-flag >/dev/null 2>&1
[ "$?" = 2 ] && ok "an unrecognised option exits 2" \
             || no "an unrecognised option exits 2" "wrong rc"

echo
[ "$fails" = 0 ] && echo "OK: site_report.sh" || { echo "$fails failed"; exit 1; }
