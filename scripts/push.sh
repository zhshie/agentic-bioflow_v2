#!/bin/bash
# Put local data where the compute nodes can read it. The mirror image of
# fetch.sh, and the half that was missing: launch.md asserted "the reads are on
# the site", which is no help at all to someone whose own raw data has only
# ever existed on their laptop - the ordinary case, not the exotic one.
#
#   push.sh [--dry-run] <local-path> <site-path>
#
# <site-path> is the exact destination. A directory's *contents* land in it; a
# file lands as it. Prints the site path to write into the samplesheet.
#
# Deliberately no size limit, unlike fetch.sh. Raw reads are legitimately tens
# of gigabytes and moving them is the entire point, so the size is reported and
# the transfer resumes rather than being refused. Home connections are far
# slower up than down: say what is about to happen before starting it.
#
#   PUSH_DRY_RUN=1     report both ends and the size; move nothing
#   PUSH_RSYNC_BIN     override rsync (tests)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

REACH="$(setting reach local)"
HOST="$(setting site_host)"
CP="$(setting ssh_control_path "$HOME/.ssh/cm-%r-%h-%p")"
RSYNC="${PUSH_RSYNC_BIN:-rsync}"
SSH="${ON_SITE_SSH_BIN:-ssh}"
DRY="${PUSH_DRY_RUN:-}"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }
human() {
  local b="$1"
  if   [ "$b" -ge 1000000000 ]; then printf '%s GB' $((b/1000000000))
  elif [ "$b" -ge 1000000 ];    then printf '%s MB' $((b/1000000))
  else                               printf '%s KB' $((b/1000))
  fi
}

[ "${1:-}" = --dry-run ] && { DRY=1; shift; }
SRC="${1:-}"; DST="${2:-}"
[ -n "$SRC" ] && [ -n "$DST" ] \
  || die 2 "usage: push.sh [--dry-run] <local-path> <site-path>"
[ -e "$SRC" ] || die 2 "'$SRC' does not exist on this machine." \
                       "push.sh moves data from here to the site; fetch.sh is the other direction."

case "$REACH" in
  local)
    # The deployment already runs on the site, so this path is a site path.
    # Copying 40 GB from one directory to another on the same filesystem to
    # satisfy an abstraction would be worse than saying so.
    printf '%s\n' "$SRC"; exit 0 ;;
  none)
    die 2 "reach is 'none': this site's storage is object storage." \
          "Uploading needs cloud credentials and a client this deployment has" \
          "never run against - see PRINCIPLES.md invariant 8. Register the data" \
          "through Platform's own storage instead." ;;
  ssh) [ -n "$HOST" ] || die 2 "reach is 'ssh' but 'site_host' is not set - see docs/SETTINGS.md." ;;
  *) die 2 "unknown reach value '$REACH' - must be none, local or ssh." ;;
esac

bytes=$(du -sb "$SRC" 2>/dev/null | cut -f1); bytes="${bytes:-0}"

if [ -n "$DRY" ]; then
  printf '%s\t->\tssh %s:%s\t(%s)\n' "$SRC" "$HOST" "$DST" "$(human "$bytes")"
  exit 0
fi

# One round trip, not two: rsync makes the destination itself on the far side
# rather than this asking the site to mkdir first. --partial so a dropped
# connection resumes instead of restarting - which on an upload of this size is
# the difference between an interruption and a lost afternoon.
if [ -d "$SRC" ]; then
  mkdir_at="$DST"; from="$SRC/"; to="$HOST:$DST/"
else
  mkdir_at="$(dirname "$DST")"; from="$SRC"; to="$HOST:$DST"
fi
"$RSYNC" -a --partial -e "$SSH -o ControlPath=$CP" \
  --rsync-path="mkdir -p $(printf '%q' "$mkdir_at") && rsync" \
  "$from" "$to" \
  || die 2 "the transfer of '$SRC' failed. Nothing was left half-written that" \
           "a re-run will not resume (--partial)."
printf '%s\n' "$DST"
