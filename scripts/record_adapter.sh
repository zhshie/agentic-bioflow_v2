#!/bin/bash
# The record adapter: where a run's record goes, if anywhere.
#
# Not a real ELN implementation written speculatively: only `none` is real
# until a lab actually picks a record system - see the contract note below.
#
# Mirrors on_site.sh's shape for a different question. The command layer never
# names a record system - it asks this adapter to resolve, attach or look up a
# reference, and the adapter answers. Full contract in docs/RECORD_ADAPTER.md;
# tests/command_layer_is_record_neutral.sh enforces that commands/*.md and
# skills/operational/SKILL.md never name one either.
#
#   record_adapter.sh resolve <ref>
#   record_adapter.sh attach <ref> <path>
#   record_adapter.sh lookup-by-checksum <sha256>
#
# Every reply is one `key=value` line, the convention the rest of this repo
# already uses for a script another script (or model) has to parse
# (scripts/inspect_sides.sh, on_site.sh's ON_SITE_DRY_RUN line).
#
# Only `none` exists. docs/RECORD_ADAPTER.md explains why an ELN implementation
# is not written speculatively - the same reason docs/SITE_ADAPTER.md gives for
# not writing a second site adapter before there is a real second site
# (PRINCIPLES.md: measure or read the source before claiming; one real
# implementation is what validates a contract, a second one guessed in advance
# is not). `none` does nothing and keeps no state: no file in this repo
# records run state (PRINCIPLES.md, invariant 2), and a record adapter that
# cached what it resolved would be exactly that file.
#
# Which adapter is configured is read the same way every other per-deployment
# value is - scripts/settings.sh's `record_adapter` key - by running
# settings.sh as its own CLI rather than sourcing it, so this script keeps its
# one dependency optional and stays runnable standalone by a person or another
# model even where settings.sh cannot be reached (PRINCIPLES.md, invariant 5).
# $RECORD_ADAPTER, default `none`, is the fallback: it wins whenever settings.sh
# has no actual value to give - no settings file, no key in it, or the script
# missing entirely - never when a settings file explicitly names an adapter.
#
# No network, ever - `none` has nothing to reach, and any future adapter
# reaches its own service directly rather than through this script's reach.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }

# No default passed to settings.sh: an empty answer has to mean "nothing
# configured" so it can fall through to $RECORD_ADAPTER, not "none" baked in
# here and settings.sh never gets the chance to be overridden by the caller.
ADAPTER="$("$HERE/settings.sh" record_adapter 2>/dev/null)" || ADAPTER=""
[ -n "$ADAPTER" ] || ADAPTER="${RECORD_ADAPTER:-none}"

OP="${1:-}"
REF=""
ATTACH_PATH=""
CHECKSUM=""

case "$OP" in
  resolve)
    REF="${2:-}"
    [ -n "$REF" ] || die 2 "usage: record_adapter.sh resolve <ref>"
    ;;
  attach)
    REF="${2:-}"; ATTACH_PATH="${3:-}"
    [ -n "$REF" ] && [ -n "$ATTACH_PATH" ] \
      || die 2 "usage: record_adapter.sh attach <ref> <path>"
    ;;
  lookup-by-checksum)
    CHECKSUM="${2:-}"
    [ -n "$CHECKSUM" ] || die 2 "usage: record_adapter.sh lookup-by-checksum <sha256>"
    ;;
  *)
    die 2 "usage: record_adapter.sh <resolve|attach|lookup-by-checksum> ..."
    ;;
esac

case "$ADAPTER" in
  none)
    case "$OP" in
      resolve)             echo "record=none" ;;
      # Does nothing: the artefact stays exactly where it already was. This
      # line is the whole of "attach" for this adapter - there is nowhere
      # else to put it and nothing to write down (see comment above).
      attach)               echo "kept=$ATTACH_PATH" ;;
      lookup-by-checksum)   echo "found=no" ;;
    esac
    exit 0
    ;;
  *)
    die 2 "adapter $ADAPTER is not implemented." \
          "Only 'none' exists - see docs/RECORD_ADAPTER.md."
    ;;
esac
