#!/bin/bash
# An nf-core process asks for the box its label names, not the box its data
# needs: process_high is 8 cpu / 53 GB, and a 6.5 Mb bacterial assembly does not
# need it. On this site a partition is a fixed-size box (PITFALLS 6), so that
# request queues behind everyone else's big jobs - and it cannot be resized in
# place, because `scontrol update` is refused outright here (PITFALLS 6c). The
# only route is: write a config that overrides that one process, cancel, and
# relaunch onto the cache. A human did that by hand twice in one session.
#
# The failures this pins down, all of them made by hand at 2am:
#
#   - relaunching without ever showing the plan. The numbers are a judgement
#     call and a low one is an OOM, not a slow job, so --confirm is the same
#     gate the launch hook asks 確認執行 for: without it nothing may be called.
#   - `tw runs cancel` on a run that is already CANCELLED, which is an error.
#     Two of the three real bacass runs were in exactly that state.
#   - relaunching without --config, which relaunches the same oversized request
#     and looks like it worked.
#   - naming a box the numbers do not actually land in. The box table lives in
#     configs/sites/nchc.config and is read back through scripts/utils/boxes.sh;
#     a second copy in this script is the thing that goes stale.
#
# `tw` is stubbed through TW_BIN, the way tests/agent_ctl_connection_id_test.sh
# stubs it: a fake that logs its argv and prints controllable output. Nothing
# here may reach the live workspace - the whole point of the script is that it
# cancels real runs.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
R="$ROOT/scripts/relaunch_with_override.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

ok()  { printf '%-58s ok\n' "$1"; }
bad() { printf '%-58s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
t()   { grep -qF -- "$2" <<<"$3" && ok "$1" || bad "$1" "lacks '$2'"; }
tn()  { grep -qF -- "$2" <<<"$3" && bad "$1" "has '$2'" || ok "$1"; }

# A stub tw that records what it was asked and answers the way the real one
# does: `runs view` prints a Status field, `runs relaunch` prints the new run
# and its watch URL. $TW_STATUS is what the case under test wants the run to be.
cat > "$TMP/tw" <<'STUB'
#!/bin/bash
echo "$*" >> "$TWLOG"
case "$*" in
  *"runs view"*)
      echo "  General"
      echo "  ---------------+------------------------------"
      echo "   ID            | 312SbdATPc2grr"
      echo "   Status        | ${TW_STATUS:-RUNNING}"
      echo "   Pipeline      | nf-core/bacass" ;;
  *"runs cancel"*)
      echo "  Workflow '312SbdATPc2grr' cancelled" ;;
  *"runs relaunch"*)
      echo "  Workflow 5newRunIdAAAAAA submitted at [lab / taiwania3] workspace."
      echo "  https://cloud.seqera.io/orgs/lab/workspaces/taiwania3/watch/5newRunIdAAAAAA" ;;
esac
STUB
chmod +x "$TMP/tw"

# A run area with a settings file, a fake token beside it, and nothing else.
area() {
    local d="$TMP/$1"; mkdir -p "$d/_personal"
    echo "not-a-real-token" > "$d/_personal/.seqera_token"
    printf 'workspace_id: 12345\n' > "$d/_personal/env.yaml"
    printf '%s' "$d"
}

run() { # run <area> <status> <args...>
    local d="$1" st="$2"; shift 2
    : > "$TMP/tw.log"
    ( export LAB_RUNS_DIR="$d" LAB_SETTINGS_FILE="$d/_personal/env.yaml" \
             TW_BIN="$TMP/tw" TWLOG="$TMP/tw.log" TW_STATUS="$st"
      bash "$R" "$@" 2>&1 )
}
twlog() { cat "$TMP/tw.log" 2>/dev/null; }

# The box these numbers land in, worked out the way every other consumer works
# it out - from the config, through boxes.sh. If this test typed 'ngs13G' by
# hand it would agree with a stale script forever.
. "$ROOT/scripts/utils/boxes.sh"
expect_box() { # expect_box <cpus> <memgb>
    local q c m h
    while IFS=$'\t' read -r q c m h; do
        if [ "$c" -ge "$1" ] && [ "$m" -ge "$2" ]; then printf '%s' "$q"; return 0; fi
    done < <(nchc_boxes)
    return 1
}

# --- it can say what it takes ------------------------------------------------
# The usage line is lifted out of the header comment; when that was done by line
# number it printed the blank comment next to it and said nothing at all.
out=$(bash "$R" -h 2>&1)
t "-h names the arguments"  "<run-id> <process> <cpus> <mem-gb>"  "$out"
out=$(bash "$R" 2>&1); rc=$?
[ "$rc" != 0 ] && ok "no arguments: exits non-zero" \
                || bad "no arguments: exits non-zero" "rc=0"

A="$(area plan)"

# --- the plan, with no --confirm ---------------------------------------------
# Step one of the manual procedure this replaces is judgement, and it stays
# with the human: the script's job is to lay the change out and stop.
out=$(run "$A" RUNNING 312SbdATPc2grr FLYE 2 13); rc=$?
[ "$rc" != 0 ] && ok "no --confirm: exits non-zero" \
                || bad "no --confirm: exits non-zero" "rc=0"
[ -z "$(twlog)" ] && ok "no --confirm: tw was never called" \
                  || bad "no --confirm: tw was never called" "log: $(twlog)"

t "config selects the process by name"   "withName: 'FLYE'"  "$out"
t "config sets the cpus asked for"       "cpus"              "$out"
t "config sets the memory asked for"     "13.GB"             "$out"
printf '%-58s ' "config sets cpus = 2, escalating"
grep -qE 'cpus[[:space:]]*=[[:space:]]*\{[[:space:]]*2[[:space:]]*\*[[:space:]]*task\.attempt' <<<"$out" \
    && echo ok || { echo "FAIL: no escalating 'cpus = { 2 * task.attempt }'"; fails=$((fails+1)); }

# --- it says which box the numbers land in -----------------------------------
box="$(expect_box 2 13)"
if [ -n "$box" ]; then
    t "names the box these numbers land in"  "$box"  "$out"
else
    bad "names the box these numbers land in" "boxes.sh returned no table"
fi

t "the config records which box, in its own comment" "// lands in $box" "$out"
tn "the box note is not garbled together"            "GB)$box"          "$out"

# --- the override must not switch off the site's one recovery ----------------
# These four assertions exist because the first version of this script got the
# direction backwards. It wrote `memory = 13.GB`, a fixed number, which REPLACES
# the `{ 12.GB * task.attempt }` closure nf-core's own base.config supplies - so
# an override quietly disabled the automatic retry-at-double, and then warned
# the user that retries do not escalate. The warning was true only because the
# script had just made it true. PITFALLS 6d has the measurement.
t  "the override escalates rather than pinning"  "* task.attempt }"  "$out"
tn "no fixed memory that would kill escalation"  "memory = 13.GB"    "$out"
t  "says a low guess recovers by itself once"    "retried at double" "$out"
t  "and that it only happens once"               "maxRetries is 1"   "$out"

# --- both fallbacks fire when the site config cannot be read -----------------
# Silence here would be the bad outcome twice over: an unchecked box name, and
# a promise about retries that nothing verified.
G="$(area noconfig)"
out=$( export LAB_RUNS_DIR="$G" LAB_SETTINGS_FILE="$G/_personal/env.yaml" \
              TW_BIN="$TMP/tw" TWLOG="$TMP/tw.log" \
              NCHC_SITE_CONFIG="$TMP/there-is-no-such-config"
       bash "$R" --dry-run 312SbdATPc2grr FLYE 2 13 2>&1 )
t "no site config: says the box is unknown"     "UNKNOWN"          "$out"
t "no site config: does not promise a retry"    "was not checked"  "$out"

# --- the plan is written where it can be found later -------------------------
# Not /tmp: someone has to be able to see next week what was changed and why.
cfg=$(find "$A" -name '*.config' -type f 2>/dev/null | head -1)
[ -n "$cfg" ] && ok "the config is written into the run area" \
              || bad "the config is written into the run area" "no .config under $A"
if [ -n "$cfg" ]; then
    t "the written file is the printed plan"  "withName: 'FLYE'"  "$(cat "$cfg")"
fi

# --- --dry-run touches nothing at all ----------------------------------------
B="$(area dry)"
out=$(run "$B" RUNNING --dry-run --confirm 312SbdATPc2grr FLYE 2 13)
[ -z "$(twlog)" ] && ok "--dry-run: executes no tw command" \
                  || bad "--dry-run: executes no tw command" "log: $(twlog)"
t "--dry-run: still shows the cancel it would run"    "runs cancel"    "$out"
t "--dry-run: still shows the relaunch it would run"  "runs relaunch"  "$out"
if [ -z "$(find "$B" -name '*.config' -type f 2>/dev/null)" ]; then
    ok "--dry-run: writes no file"
else
    bad "--dry-run: writes no file" "it wrote one anyway"
fi

# --- an already-cancelled run is not cancelled again --------------------------
# `tw runs cancel` on a CANCELLED run is an error, and two of the three real
# bacass runs were already cancelled by hand before anyone reached for this.
C="$(area cancelled)"
out=$(run "$C" CANCELLED --confirm 312SbdATPc2grr FLYE 2 13)
log="$(twlog)"
tn "CANCELLED: does not call cancel"  "runs cancel"    "$log"
t  "CANCELLED: still relaunches"      "runs relaunch"  "$log"
t  "CANCELLED: says why it skipped"   "CANCELLED"      "$out"

# --- a SUCCEEDED run is not cancelled either ---------------------------------
D="$(area done)"
out=$(run "$D" SUCCEEDED --confirm 312SbdATPc2grr FLYE 2 13)
log="$(twlog)"
tn "SUCCEEDED: does not call cancel"  "runs cancel"    "$log"
t  "SUCCEEDED: still relaunches"      "runs relaunch"  "$log"

# --- a live run is cancelled first, then relaunched --------------------------
E="$(area live)"
out=$(run "$E" RUNNING --confirm 312SbdATPc2grr FLYE 2 13)
log="$(twlog)"
t "RUNNING: cancels"      "runs cancel"    "$log"
t "RUNNING: relaunches"   "runs relaunch"  "$log"
c_at=$(grep -n 'runs cancel'   <<<"$log" | head -1 | cut -d: -f1)
r_at=$(grep -n 'runs relaunch' <<<"$log" | head -1 | cut -d: -f1)
if [ -n "$c_at" ] && [ -n "$r_at" ] && [ "$c_at" -lt "$r_at" ]; then
    ok "RUNNING: cancel comes before relaunch"
else
    bad "RUNNING: cancel comes before relaunch" "cancel@${c_at:-none} relaunch@${r_at:-none}"
fi

# A SUBMITTED run has not started but is queued under the old request, so it is
# live for this purpose and must be cancelled too.
F="$(area queued)"
out=$(run "$F" SUBMITTED --confirm 312SbdATPc2grr FLYE 2 13)
t "SUBMITTED: cancels too"  "runs cancel"  "$(twlog)"

# --- the relaunch carries the config, and the run and workspace --------------
# Without --config this relaunches the same oversized request and looks like it
# worked, which is the failure that costs another spell in the queue.
rl=$(grep 'runs relaunch' <<<"$log" | head -1)
t "relaunch carries --config"        "--config"          "$rl"
t "relaunch names the run"           "312SbdATPc2grr"    "$rl"
t "relaunch is scoped to the workspace" "-w 12345"       "$rl"
printf '%-58s ' "relaunch points --config at the written file"
cfgarg=$(sed -n 's/.*--config \([^ ]*\).*/\1/p' <<<"$rl")
if [ -n "$cfgarg" ] && [ -f "$cfgarg" ]; then echo ok
else echo "FAIL: --config '$cfgarg' is not a file"; fails=$((fails+1)); fi

# --- the token never appears on a command line -------------------------------
# `ps` is readable by every user on a shared login node.
tn "the token is never passed as an argument"  "not-a-real-token"  "$(twlog)"

# --- it reports where the new run went ---------------------------------------
t "prints the new run id"        "5newRunIdAAAAAA"          "$out"
t "prints the Platform URL"      "https://cloud.seqera.io"  "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
