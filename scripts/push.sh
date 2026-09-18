#!/bin/bash
# Put local data where the compute nodes can read it. The mirror image of
# fetch.sh, and the half that was missing: launch.md asserted "the reads are on
# the site", which is no help at all to someone whose own raw data has only
# ever existed on their laptop - the ordinary case, not the exotic one.
#
# Not a bare rsync/scp: reports both ends and the size before moving anything,
# since a home connection is far slower up than down - see below.
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
# With no rsync on PATH - the ordinary state of Git Bash/MSYS, which this
# plugin otherwise supports as a first-class shell - this falls back to tar
# piped over the same ssh connection instead of hard-failing with no path
# forward (issue #6). No incremental resume like rsync's --partial; a dropped
# transfer starts over.
#
#   PUSH_DRY_RUN=1     report both ends and the size; move nothing
#   PUSH_RSYNC_BIN     override rsync (tests; also how a caller can force
#                      the tar|ssh fallback by pointing it at nothing)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

REACH="$(setting reach local)"
HOST="$(setting site_host)"
RSYNC="${PUSH_RSYNC_BIN:-rsync}"
SSH="${ON_SITE_SSH_BIN:-ssh}"

# The MSYS+WSL bridge, derived once in scripts/settings.sh and used here the
# same way scripts/on_site.sh uses it (PITFALLS 16b/16g). Unlike fetch.sh, nothing above this line asks the site anything first, so
# there is no earlier on_site.sh call to refuse on a missing bridge -
# without this a laptop push under MSYS would go straight to rsync building
# `-e` from Git Bash's own ssh (16b), and rsync's own connection failure
# would be the first thing heard about it.
#
# With $SSH possibly the shim, the `-e "$SSH -o ControlPath=$CP"` string below
# is split by rsync itself, and the shim's own arguments then cross wsl.exe a
# second time - whether that second hop's quoting survives is unmeasured on a
# real machine (risk R1); tests/wsl_bridge_test.sh pins the literal argv a
# fake wsl.exe receives from exactly this shape of `-e` string.
BRIDGE="$(bridge_kind)"
if [ -z "${ON_SITE_SSH_BIN:-}" ] && [ "$REACH" = ssh ] && [ "$BRIDGE" = wsl ]; then
  SSH="$(site_ssh_bin wsl)"
fi
CP="$(setting ssh_control_path "$(site_control_path_default "$BRIDGE")")"

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

bytes=$(dir_bytes "$SRC")   # GNU byte mode is not portable; see scripts/utils/portable.sh

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

if command -v "$RSYNC" >/dev/null 2>&1; then
  "$RSYNC" -a --partial -e "$SSH -o ControlPath=$CP" \
    --rsync-path="mkdir -p $(printf '%q' "$mkdir_at") && rsync" \
    "$from" "$to" \
    || die 2 "the transfer of '$SRC' failed. Nothing was left half-written that" \
             "a re-run will not resume (--partial)."
else
  # Git Bash ships no rsync by default (issue #6) - fall back to tar over the
  # same ssh connection already established for site-reach. Unlike the
  # rsync path above, a plain destination-file push (the "else" branch of the
  # $SRC directory check) can ask for a rename - $SRC's basename landing as
  # $DST's own name - which rsync gets for free from an explicit target path
  # and tar has to be told about after extracting.
  if [ -d "$SRC" ]; then
    tar czf - -C "$SRC" . \
      | "$SSH" -o ControlPath="$CP" "$HOST" \
          "mkdir -p $(printf '%q' "$mkdir_at") && tar xzf - -C $(printf '%q' "$mkdir_at")" \
      || die 2 "the transfer of '$SRC' failed. tar|ssh has no incremental" \
               "resume like rsync's --partial; a re-run starts over."
  else
    srcbase="$(basename "$SRC")"
    remote_cmd="mkdir -p $(printf '%q' "$mkdir_at") && tar xzf - -C $(printf '%q' "$mkdir_at")"
    [ "$srcbase" = "$(basename "$DST")" ] \
      || remote_cmd="$remote_cmd && mv -f -- $(printf '%q' "$mkdir_at/$srcbase") $(printf '%q' "$DST")"
    tar czf - -C "$(dirname "$SRC")" "$srcbase" \
      | "$SSH" -o ControlPath="$CP" "$HOST" "$remote_cmd" \
      || die 2 "the transfer of '$SRC' failed. tar|ssh has no incremental" \
               "resume like rsync's --partial; a re-run starts over."
  fi
fi
printf '%s\n' "$DST"
