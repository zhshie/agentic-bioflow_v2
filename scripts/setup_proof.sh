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

out=$("$TW" -o json runs list --workspace "$WS" 2>&1) \
    || refuse "could not confirm - Platform could not be asked ($out)"

row=$(jq -r --arg id "$RUN_ID" '
    [.workflows[] | select(.workflow.id == $id)] | first
    | if . == null then "NONE"
      else [.workflow.status, .workflow.projectName, (.workflow.userName // "")] | @tsv end' \
    <<<"$out" 2>/dev/null) \
    || refuse "could not confirm - Platform's answer was not readable"
[ -n "$row" ] || refuse "could not confirm - Platform's answer was not readable"
[ "$row" != NONE ] || refuse "run '$RUN_ID' not found in workspace $WS on Platform"

IFS=$'\t' read -r status project owner <<<"$row"

[ "$status" = SUCCEEDED ] \
    || refuse "run '$RUN_ID' has status $status, not SUCCEEDED"
case "$project" in
    nf-core/demo|*/nf-core/demo) ;;
    *) refuse "run '$RUN_ID' is '$project'; the proof has to be an nf-core/demo run" ;;
esac
if [ -n "$SEQERA_USER" ] && [ "$owner" != "$SEQERA_USER" ]; then
    refuse "run '$RUN_ID' was submitted by '$owner', not by '$SEQERA_USER'"
fi

rec="$RUN_ID $(date +%Y-%m-%d) nf-core/demo"
set_setting proof_run "$rec" || exit 1
echo "recorded: proven on this machine: $rec"
