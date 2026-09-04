#!/bin/bash
# Bring a path on the site to somewhere it can be read.
#
#   fetch.sh [--max-mb N] [--dry-run] <site-path> [local-path]
#
# Prints the path to read. On a deployment that runs on the site that is the
# path it was given and nothing is copied - doubling 25 GB of results onto the
# same filesystem to satisfy an abstraction would be a poor trade.
#
# Reading a result is the thing this whole plugin exists to end with, so it is
# also where a laptop-driven deployment is most easily got wrong: `results/` is
# about 25 MB, and `work/` beside it is three orders of magnitude larger. A
# laptop asked to pull that over a home connection gives no sign of what it is
# doing for the first hour. So the site is asked how big the path is before
# anything moves, at the cost of one round trip.
#
#   FETCH_DRY_RUN=1     print what would be transferred; move nothing
#   FETCH_ROOT          where fetched copies are staged
#   FETCH_RSYNC_BIN     override rsync (tests)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

REACH="$(setting reach local)"
HOST="$(setting site_host)"
CP="$(setting ssh_control_path "$HOME/.ssh/cm-%r-%h-%p")"
RSYNC="${FETCH_RSYNC_BIN:-rsync}"
SSH="${ON_SITE_SSH_BIN:-ssh}"
STAGE="${FETCH_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/agentic-bioflow}"
MAX_MB=500
DRY="${FETCH_DRY_RUN:-}"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --max-mb) MAX_MB="${2:?--max-mb needs a number}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --) shift; break ;;
    -*) die 2 "unknown option '$1'" ;;
    *) break ;;
  esac
done
SRC="${1:?usage: fetch.sh [--max-mb N] [--dry-run] <site-path> [local-path]}"

case "$REACH" in
  local) printf '%s\n' "$SRC"; exit 0 ;;
  none)
    die 2 "reach is 'none': this site's results are in object storage." \
          "Reading them needs cloud credentials and a client this deployment" \
          "has never run against. Nothing here guesses at one - see" \
          "PRINCIPLES.md invariant 8." ;;
  ssh) [ -n "$HOST" ] || die 2 "reach is 'ssh' but 'site_host' is not set - see docs/SETTINGS.md." ;;
  *) die 2 "unknown reach value '$REACH' - must be none, local or ssh." ;;
esac

# The staging copy mirrors the site path, so two runs cannot land on each other
# and a second fetch of the same results updates in place rather than re-pulling.
DEST="${2:-$STAGE/${SRC#/}}"

bytes=$(bash "$HERE/on_site.sh" du -sb -- "$SRC" 2>/dev/null | tail -1 | cut -f1)
case "$bytes" in
  ''|*[!0-9]*) die 2 "the site could not size '$SRC'." \
                     "Either it does not exist there, or the site cannot be reached -" \
                     "'scripts/preflight.sh' says which." ;;
esac
mb=$(( bytes / 1000000 ))

if [ "$mb" -gt "$MAX_MB" ]; then
  die 2 "'$SRC' is ${mb} MB, over the ${MAX_MB} MB limit." \
        "" \
        "A results directory is usually tens of megabytes; a work directory is" \
        "hundreds of gigabytes and is meant to stay on the site. If this really" \
        "is what you want:" \
        "" \
        "    scripts/fetch.sh --max-mb ${mb} $SRC"
fi

if [ -n "$DRY" ]; then
  printf 'ssh %s\t%s\t%s (%s MB)\n' "$HOST" "$SRC" "$DEST" "$mb"
  exit 0
fi

mkdir -p "$(dirname "$DEST")" || die 2 "cannot create $(dirname "$DEST")"
"$RSYNC" -a -e "$SSH -o ControlPath=$CP" "$HOST:$SRC" "$(dirname "$DEST")/" \
  || die 2 "the transfer of '$SRC' failed."
printf '%s\n' "$DEST"
