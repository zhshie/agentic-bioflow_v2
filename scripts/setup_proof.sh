#!/bin/bash
# Feature 004 (specs/004-onboarding-proof): "this machine has proven the
# environment on public test data", recorded per machine and written ONLY from
# what Platform itself says about a run - never from what anyone typed or
# remembered (constitution IV, evidence before claims).
#
#   setup_proof.sh --check
#       exit 0 and `proven on this machine: <record>` if this machine has a
#       record; exit 1 and say how to get one (commands/setup.md step 8) if not.
#   setup_proof.sh --record <run-id>
#       asks Platform (`tw -o json runs list`, the same call and token loading
#       as scripts/runs_board.sh) about that run. It is recorded only if the
#       run is SUCCEEDED, is nf-core/demo, and was submitted by seqera_user.
#       Every refusal names its reason and writes nothing. If Platform cannot
#       be asked, or answers something unreadable, that is a refusal too: an
#       unconfirmed run is never counted as proof (FR-004).
#
# The record is `proof_run: <run-id> <YYYY-MM-DD> nf-core/demo`, a machine key
# (scripts/settings.sh MACHINE_KEYS), so it lands in
# config/machines/<machine>.yaml and never travels with the root.
#
# Not `tw runs view`: its output carries no project name. `runs list`
# does (.workflows[].workflow.{id,projectName,status,userName}, measured live,
# see runs_board.sh).
#
# Exit codes: 0 ok, 1 refused / not proven, 2 usage or missing setting.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

usage() {
    echo "usage: setup_proof.sh --check | --record <run-id>" >&2
    exit 2
}

MODE=""; RUN_ID=""
case "${1:-}" in
    --check)  [ $# -eq 1 ] || usage; MODE=check ;;
    --record) [ $# -eq 2 ] && [ -n "${2:-}" ] || usage; MODE=record; RUN_ID="$2" ;;
    *) usage ;;
esac

if [ "$MODE" = check ]; then
    # The machine file only, not setting(): setting() falls back to the shared
    # env.yaml for a machine key, and a proof_run that landed there (hand edit,
    # an older copy) would travel with the root and vouch for a machine that
    # proved nothing.
    rec=""
    [ -n "$MACHINE_SETTINGS_FILE" ] && rec="$(_read_key "$MACHINE_SETTINGS_FILE" proof_run)"
    if [ -n "$rec" ]; then
        echo "proven on this machine: $rec"
        exit 0
    fi
    echo "not proven: this machine has not yet run nf-core/demo successfully on public test data."
    echo "Do commands/setup.md step 8, then record the run with: scripts/setup_proof.sh --record <run-id>"
    exit 1
fi

TW="$(setting tw_bin tw)"
WS="$(setting workspace_id --required)" || exit 2
SEQERA_USER="$(setting seqera_user)"

TOKEN_FILE="${SEQERA_TOKEN_FILE:-$(dirname "$SETTINGS_FILE")/.seqera_token}"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
    export TOWER_ACCESS_TOKEN
fi

refuse() { echo "not recorded: $*" >&2; exit 1; }

# stdout only: a CLI notice on stderr (an update banner) must not spoil an
# otherwise good answer, and tw's own exit code must be zero too.
ERRF="$(mktemp)"; trap 'rm -f "$ERRF"' EXIT
out=$("$TW" -o json runs list --workspace "$WS" 2>"$ERRF") \
    || refuse "could not confirm - Platform could not be asked ($(head -3 "$ERRF"))"
command -v jq >/dev/null 2>&1 || refuse "could not confirm - jq is not installed here"

# One field per jq call: `IFS=<tab> read` collapses an empty field and shifts
# the rest (a null status was reported as "has status nf-core/demo").
field() {
    jq -r --arg id "$RUN_ID" --arg f "$1" '
        [.workflows[] | select(.workflow.id == $id)] | first
        | if . == null then "__NO_SUCH_RUN__" else (.workflow[$f] // "" | tostring) end' \
        <<<"$out" 2>/dev/null
}
status="$(field status)"   || refuse "could not confirm - Platform's answer was not readable"
[ "$status" != __NO_SUCH_RUN__ ] || refuse "run '$RUN_ID' not found in workspace $WS on Platform"
project="$(field projectName)"
owner="$(field userName)"
submit="$(field submit)"

[ "$status" = SUCCEEDED ] \
    || refuse "run '$RUN_ID' has status '${status:-unknown}', not SUCCEEDED"
# nf-core/demo itself, by name or by its GitHub address - not a fork or a
# look-alike path that merely ends in it.
case "$project" in
    nf-core/demo|https://github.com/nf-core/demo|https://github.com/nf-core/demo.git) ;;
    *) refuse "run '$RUN_ID' is '$project'; the proof has to be an nf-core/demo run" ;;
esac
if [ -n "$SEQERA_USER" ] && [ "$owner" != "$SEQERA_USER" ]; then
    refuse "run '$RUN_ID' was submitted by '$owner', not by '$SEQERA_USER'"
fi

# Proof of THIS machine, now: a recent run, not one already proving another
# machine of this root (acceptance of 004, MED-1).
age_days=$(jq -rn --arg s "$submit" '
    ($s | sub("\\.[0-9]+Z$"; "Z") | try fromdateiso8601 catch null) as $t
    | if $t == null then "" else ((now - $t) / 86400 | floor) end' 2>/dev/null)
[ -n "$age_days" ] || refuse "could not confirm when run '$RUN_ID' was submitted ('$submit')"
[ "$age_days" -le 7 ] \
    || refuse "run '$RUN_ID' was submitted $age_days days ago - older than 7 days; run step 8 again on this machine"
MDIR="$(dirname "${MACHINE_SETTINGS_FILE:-/nonexistent/x}")"
for f in "$MDIR"/*.yaml; do
    [ -r "$f" ] && [ "$f" != "$MACHINE_SETTINGS_FILE" ] || continue
    if [ "$(_read_key "$f" proof_run | cut -d' ' -f1)" = "$RUN_ID" ]; then
        refuse "run '$RUN_ID' already proves another machine ($(basename "$f" .yaml)); run step 8 on this one"
    fi
done

rec="$RUN_ID $(printf '%s' "$submit" | cut -c1-10) nf-core/demo"
set_setting proof_run "$rec" || exit 1
echo "recorded: proven on this machine: $rec"
