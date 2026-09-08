# The partition box table, read from the one place it is written down.
#
# `configs/sites/nchc.config` holds NCHC_BOXES because Nextflow has to read the
# boxes at launch time from a file it already parses. Every other consumer -
# the drift check, why_pending.sh - therefore has to read them back OUT of that
# file rather than keeping its own copy, or the copy is what goes stale the day
# NCHC changes a partition. That is the exact failure the drift check exists to
# catch, so a second transcription inside the checker would be self-defeating.
#
# Source this and call:
#
#   nchc_boxes [config]   ->  queue<TAB>cpus<TAB>mem<TAB>maxHours, smallest first
#
# The config path is resolved from this file's own location, so a caller in any
# directory gets the right table; pass an argument (or set NCHC_SITE_CONFIG) to
# point at another site's file.
#
# Parsing is per-line and keyed on field NAMES, not on field order. The version
# this replaces ran three independent `grep -oP` passes and pasted the columns
# back together, which silently mis-pairs every row if one entry ever wraps, is
# commented out, or lists its fields in a different order - and pastes an
# off-by-one table that looks entirely plausible.

_nchc_boxes_default_config() {
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    printf '%s\n' "$here/../../configs/sites/nchc.config"
}

nchc_boxes() {
    local config="${1:-${NCHC_SITE_CONFIG:-$(_nchc_boxes_default_config)}}"
    if [ ! -r "$config" ]; then
        echo "boxes.sh: cannot read site config: $config" >&2
        return 2
    fi

    # A literal single quote, so the regexes below can be written unquoted
    # (bash treats a quoted =~ pattern as a plain string, not a regex).
    local SQ="'"
    local line in_list=0 n=0 q c m h

    while IFS= read -r line; do
        # Ignore anything after a // comment: the surrounding file documents the
        # table in prose that mentions the same field names.
        line="${line%%//*}"

        if [ "$in_list" = 0 ]; then
            [[ $line =~ NCHC_BOXES[[:space:]]*=[[:space:]]*\[ ]] && in_list=1
            continue
        fi
        # The list ends at a ] that opens the line; a row's own trailing ], does not.
        [[ $line =~ ^[[:space:]]*\] ]] && break

        [[ $line =~ queue:[[:space:]]*${SQ}([^${SQ}]+)${SQ} ]] || continue
        q="${BASH_REMATCH[1]}"
        [[ $line =~ cpus:[[:space:]]*([0-9]+) ]] || continue
        c="${BASH_REMATCH[1]}"
        [[ $line =~ mem:[[:space:]]*([0-9]+) ]] || continue
        m="${BASH_REMATCH[1]}"
        # maxHours is the only optional field; 0 already means "unlimited" in the
        # config, so it is also the safe reading of an absent one.
        if [[ $line =~ maxHours:[[:space:]]*([0-9]+) ]]; then h="${BASH_REMATCH[1]}"; else h=0; fi

        printf '%s\t%s\t%s\t%s\n' "$q" "$c" "$m" "$h"
        n=$((n + 1))
    done < "$config"

    if [ "$n" = 0 ]; then
        echo "boxes.sh: no boxes found in $config - has NCHC_BOXES been renamed?" >&2
        return 1
    fi
}
