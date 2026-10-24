#!/bin/bash
# Tests for the compute-environment (CE) check in scripts/prepare_launch.sh
# (issue #8, specs/launchpad-ce-routing): a registered launchpad entry is bound
# to one CE; the summary must say which, and ask the user when it is not the
# deployment's compute_env. Fully offline: a fake `tw` answers from canned files.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-72s ok\n' "$1"; }
no() { printf '%-72s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
has() { grep -qF -- "$2" <<<"$1"; }
cnt() { grep -cE -- "$2" <<<"$1" || true; }
chk() { if "${@:2}"; then ok "$1"; else no "$1" "assertion false"; fi; }

SDIR="$TMP/scripts"; mkdir -p "$SDIR/utils"
cp "$ROOT/scripts/prepare_launch.sh" "$ROOT/scripts/settings.sh" "$SDIR/"
cp "$ROOT/scripts/utils/portable.sh" "$ROOT/scripts/utils/schema_roles.py" "$SDIR/utils/"
printf '#!/bin/bash\necho "OK   fake preflight"\nexit 0\n' > "$SDIR/preflight.sh"; chmod +x "$SDIR/preflight.sh"
FIX="$TMP/fixture"; mkdir -p "$FIX"

# The fake tw: canned answers from $CASE/, every call logged. Never a real tw.
FAKE="$TMP/faketw"
cat > "$FAKE" <<'SH'
#!/bin/bash
echo "$*" >> "$CASE/calls.log"
if [[ " $* " == *" -o json "* && " $* " == *" list "* ]]; then cat "$CASE/list.json"; exit 0; fi
if [[ " $* " == *" view "* ]]; then
    if [ -r "$CASE/view.json" ]; then cat "$CASE/view.json"; exit 0; fi
    exit 1
fi
if [[ " $* " == *" list "* ]]; then cat "$CASE/text.txt"; exit 0; fi
exit 1
SH
chmod +x "$FAKE"

TEXT='NAME                 REPOSITORY                           REVISION
nf-core-rnaseq-3140  https://github.com/nf-core/rnaseq    3.14.0'

# ent <name> <repo> <rev|-> <ce|-> [launch]  -> one JSON entry.
# rev "-" = no revision fields at all; "launch" = CE only under launch.computeEnv.
ent() {
    local n="$1" r="$2" rev="$3" ce="$4" where="${5:-top}" j l=""
    j="\"name\":\"$n\",\"repository\":\"https://github.com/$r\""
    [ "$rev" != "-" ] && j="$j,\"revision\":\"$rev\""
    [ "$rev" != "-" ] && l="\"revision\":\"$rev\""
    if [ "$ce" != "-" ]; then
        if [ "$where" = launch ]; then l="${l}${l:+,}\"computeEnv\":{\"name\":\"$ce\"}"
        else j="$j,\"computeEnv\":{\"name\":\"$ce\"}"; fi
    fi
    [ -n "$l" ] && j="$j,\"launch\":{$l}"
    echo "{$j}"
}
list() { local IFS=,; echo "{\"pipelines\":[$*]}"; }

# run <case> <list-json> [view-json|-] [compute_env|-]  -> sets $out $calls
run() {
    local c="$TMP/case-$1"; rm -rf "$c"; mkdir -p "$c"
    printf '%s\n' "$2" > "$c/list.json"
    printf '%s\n' "${TEXT_OVERRIDE:-$TEXT}" > "$c/text.txt"
    [ "${3:--}" != "-" ] && printf '%s\n' "$3" > "$c/view.json"
    printf 'workspace_id: ws1\n' > "$c/env.yaml"
    [ "${4-agentic-bioflow-v2test}" != "-" ] && printf 'compute_env: %s\n' "${4-agentic-bioflow-v2test}" >> "$c/env.yaml"
    out=$(CASE="$c" LAB_SETTINGS_FILE="$c/env.yaml" TW_BIN="${TWB:-$FAKE}" TOWER_ACCESS_TOKEN=SECRET-TOKEN-xyz \
          bash "$SDIR/prepare_launch.sh" --repo nf-core/rnaseq --revision 3.14.0 --fixture-dir "$FIX" 2>&1)
    calls=$(cat "$c/calls.log" 2>/dev/null || true)
    LASTCASE="$c"
}
bline() { grep -m1 '^bound to:' <<<"$out" || true; }
quiet() { [ -z "$(grep -E '^(DECIDE|WARNING):' <<<"$out" | grep -E 'bound to|bound compute|registered entry is bound')" ]; }
decide_both() { [ -n "$(grep '^DECIDE:' <<<"$out" | grep -F -- '--compute-env' | grep -F "$1" | grep -F "$2")" ]; }
TCNAT=nchc-taiwania3; MINE=agentic-bioflow-v2test

# --- mismatch (TC-001..005, 025..027)
run t1 "$(list "$(ent nf-core-rnaseq-3140 nf-core/rnaseq 3.14.0 $TCNAT)")"
chk "TC-001 bound to line names the CE"         has "$(bline)" "$TCNAT"
chk "TC-002 DECIDE names both CEs + --compute-env" decide_both $TCNAT $MINE
chk "TC-002 says do NOT launch by short name"   has "$out" "do NOT launch it by short name"
chk "TC-003 registered line unchanged"          has "$out" "registered: yes, at 3.14.0"
chk "TC-004 no BLOCKING about bound to"         test -z "$(grep '^BLOCKING:.*bound to' <<<"$out")"
chk "TC-005 bound to right after registered"    test "$(grep -A1 '^registered:' <<<"$out" | sed -n 2p | cut -c1-9)" = "bound to:"
chk "TC-026 only list/view calls"               test -z "$(grep -E 'add|update|delete|launch' <<<"$calls")"
chk "TC-025 json list has workspace"            has "$calls" "-o json pipelines list --workspace ws1"
chk "TC-027 token not echoed"                   test -z "$(grep -F SECRET-TOKEN-xyz <<<"$out$calls")"
chk "TC-027 no traceback"                       test -z "$(grep -F Traceback <<<"$out")"

# --- match (TC-006, 007)
run t2 "$(list "$(ent nf-core-rnaseq-3140 nf-core/rnaseq 3.14.0 $MINE)")"
chk "TC-006 names CE"                           has "$(bline)" "bound to: $MINE"
chk "TC-006 matches wording"                    has "$(bline)" "matches this deployment's compute_env"
chk "TC-007 quiet on match"                     quiet

# --- view fallback (TC-008, 009, 011, 025)
L="$(list "$(ent nf-core-rnaseq-3140 nf-core/rnaseq 3.14.0 -)")"
run t8 "$L" '{"pipeline":{"launch":{"computeEnv":{"name":"nchc-taiwania3"}}}}'
chk "TC-008 view fallback names CE"             has "$(bline)" "$TCNAT"
chk "TC-008 view fallback DECIDE"               decide_both $TCNAT $MINE
chk "TC-025 view has -n and workspace"          has "$calls" "view -n nf-core-rnaseq-3140 --workspace ws1"
run t9 "$L" "{\"pipeline\":{\"launch\":{\"computeEnv\":{\"name\":\"$MINE\"}}}}"
chk "TC-009 view fallback match"                has "$(bline)" "matches this deployment's compute_env"
chk "TC-009 quiet"                              quiet
run t11 "$L" '{"pipeline":{"computeEnv":{"name":"nchc-taiwania3"}}}'
chk "TC-011 view top-level computeEnv"          has "$(bline)" "$TCNAT"
chk "TC-011 DECIDE"                             decide_both $TCNAT $MINE

# --- launch.computeEnv in the list itself (TC-010)
run t10 "$(list "$(ent nf-core-rnaseq-3140 nf-core/rnaseq 3.14.0 $TCNAT launch)")"
chk "TC-010 launch.computeEnv read"             has "$(bline)" "$TCNAT"
chk "TC-010 DECIDE"                             decide_both $TCNAT $MINE
chk "TC-010 no view call"                       test -z "$(grep view <<<"$calls")"

# --- SEQERA_COMPUTE_ENV wins (TC-012)
run t12 "$(list "$(ent nf-core-rnaseq-3140 nf-core/rnaseq 3.14.0 $TCNAT)")"
out=$(CASE="$LASTCASE" LAB_SETTINGS_FILE="$LASTCASE/env.yaml" TW_BIN="$FAKE" TOWER_ACCESS_TOKEN=x SEQERA_COMPUTE_ENV=$TCNAT \
      bash "$SDIR/prepare_launch.sh" --repo nf-core/rnaseq --revision 3.14.0 --fixture-dir "$FIX" 2>&1)
chk "TC-012 SEQERA_COMPUTE_ENV wins"            has "$(bline)" "matches this deployment's compute_env"
chk "TC-012 quiet"                              quiet

# --- several entries (TC-013..017)
run t13 "$(list "$(ent nf-core-rnaseq-3140 nf-core/rnaseq 3.14.0 $MINE)" "$(ent nf-core-ampliseq-2180 nf-core/ampliseq 2.18.0 $TCNAT)")"
chk "TC-013 other repo ignored"                 test -z "$(bline | grep $TCNAT)"
chk "TC-013 quiet"                              quiet
run t14 "$(list "$(ent a nf-core/rnaseq 3.14.0 $TCNAT)" "$(ent b nf-core/rnaseq 3.10.0 $MINE)")"
chk "TC-014 wanted revision wrong -> DECIDE"    decide_both $TCNAT $MINE
run t15 "$(list "$(ent a nf-core/rnaseq 3.14.0 $MINE)" "$(ent b nf-core/rnaseq 3.10.0 $TCNAT)")"
chk "TC-015 wanted revision right -> match"     has "$(bline)" "matches this deployment's compute_env"
chk "TC-015 quiet"                              quiet
run t16 "$(list "$(ent a nf-core/rnaseq - $MINE)" "$(ent b nf-core/rnaseq - $TCNAT)")"
chk "TC-016 no revision field -> DECIDE"        decide_both $TCNAT $MINE
chk "TC-016 does not claim matches"             test -z "$(bline | grep -F matches)"
many=(); for i in 1 2 3 4 5 6 7; do many+=("$(ent e$i nf-core/rnaseq 3.14.0 -)"); done
run t17 "$(list "${many[@]}")"
chk "TC-017 view called at most 5 times"        test "$(grep -c ' view ' <<<"$calls")" -le 5
chk "TC-017 unknown"                            has "$(bline)" "bound to: unknown"

# --- unknown / unset (TC-018..022)
run t18 "$L"
chk "TC-018 unknown"                            has "$(bline)" "bound to: unknown"
chk "TC-018 never claims match"                 test -z "$(grep -F "matches this deployment's" <<<"$out")"
chk "TC-019 exactly one bound-to warning"       test "$(cnt "$(grep '^WARNING:' <<<"$out")" 'bound to')" = 1
chk "TC-019 wording"                            has "$out" "treat it as NOT matching until checked"
run t20 'this is not json {'
chk "TC-020 unknown on bad json"                has "$(bline)" "bound to: unknown"
chk "TC-020 one warning"                        test "$(cnt "$(grep '^WARNING:' <<<"$out")" 'bound to')" = 1
chk "TC-020 no traceback"                       test -z "$(grep -F Traceback <<<"$out")"
chk "TC-020 registered line same"               has "$out" "registered: yes, at 3.14.0"
run t21 "$(list "$(ent nf-core-rnaseq-3140 nf-core/rnaseq 3.14.0 $TCNAT)")" - -
chk "TC-021 no compute_env text"                has "$(bline)" "no compute_env in the deployment settings, nothing to compare"
chk "TC-021 names CE"                           has "$(bline)" "$TCNAT"
chk "TC-022 fixed warning"                      has "$out" "WARNING: no compute_env is configured, so the bound compute environment cannot be checked."

# --- unchanged behaviour (TC-023, 024)
TEXT_OVERRIDE='NAME  REPOSITORY  REVISION
other  https://github.com/nf-core/ampliseq  2.18.0'
run t23 "$(list)"; unset TEXT_OVERRIDE
chk "TC-023 not registered"                     has "$out" "registered: no -"
chk "TC-023 old decide kept"                    has "$out" "DECIDE: register the pipeline before launch"
chk "TC-023 no bound to noise"                  quiet
TWB=/does/not/exist; run t24 "$L"; unset TWB
chk "TC-024 registered unknown"                 has "$out" "registered: unknown"
chk "TC-024 one old warning"                    test "$(cnt "$out" '^WARNING:.*could not check whether the pipeline is already registered')" = 1
chk "TC-024 no bound to warning"                quiet

# --- skill text (TC-028, 029)
S="$ROOT/skills/launch/SKILL.md"
s3=$(awk '/^3\. \*\*Register it/{f=1;next} /^4\. \*\*/{f=0} f' "$S")
s7=$(awk '/^7\. \*\*Show the complete/{f=1;next} /^8\. \*\*/{f=0} f' "$S")
chk "TC-028 step 3 mentions bound to"           has "$s3" "bound to"
chk "TC-029 step 7 explicit --compute-env"      has "$s7" '--compute-env "$(scripts/settings.sh compute_env)"'

echo; [ "$fails" = 0 ] && echo "all ok" || echo "$fails FAIL"
exit $((fails>0))
