#!/bin/bash
# Suggest a smaller box for a process that never needed the one it got.
#
#   tune_resources.sh [--json] [--trace <file>] <run-id>
#   tune_resources.sh --config --samples <n> --input-size <size> <run-id>
#
# Seqera Platform already has a resource optimiser, and this deployment must
# keep it off (`tw launch --disable-optimization`, docs/PITFALLS.md 9): it
# right-sizes from run history, which is exactly wrong on a site where the
# acceptable sizes are a handful of fixed boxes rather than a range - a
# "helpfully" reduced request lands below a box's floor and never schedules
# (docs/PITFALLS.md 6). So the one thing that WOULD make an over-allocated
# process cheaper here - noticing it peaked at 6 GB inside a 33 GB box - is the
# one thing nothing does. Platform's optimiser does not know the boxes exist;
# this is the tool that does, and it exists only because that gap is real, not
# because Seqera's own tool was worth rebuilding (PRINCIPLES.md, invariant 1).
#
# Reads what Platform measured for a run - `tw runs view ... metrics`, or with
# --trace, a pipeline's own `pipeline_info/execution_trace_*.txt` (a TSV
# despite the extension) - and for each process works out the smallest box
# that still covers peak RSS x 1.5. Only a process at least one full TIER
# oversized is reported with a move; a 10% overshoot is noise that trains a
# reader to stop looking, so it is shown as unchanged instead. Nothing here
# decides on its own: this only ever reads Platform and the filesystem, never
# cancels, relaunches, or launches anything.
#
# The box table always comes from configs/sites/nchc.config, through
# scripts/utils/boxes.sh. A box name typed into this script would be the copy
# that goes stale the day a partition changes.
#
#   --json               emit the same table as JSON, one object per process
#   --trace <file>        read peak_rss/peak_vmem from an execution trace
#                          instead of asking Platform; asks Platform nothing
#   --config              print a tuned config for every oversized process,
#                          instead of the table
#   --samples <n>          required with --config: how many samples this was
#   --input-size <size>    required with --config: roughly how much input data
#
# A tuned config with no record of what it was tuned against is a trap - the
# same numbers on ten times the data are an OOM (docs/PITFALLS.md 6d) - so
# --config refuses to print one without both of the above. Saving the result
# to `<run area>/tuned/<pipeline>@<revision>.config` is the caller's job: this
# script does not touch the run area, so that offer stays behind a person's
# confirmation (PRINCIPLES.md, the safety net).
#
# Environment (all optional; each overrides the deployment setting):
#   TW_BIN, TOWER_WORKSPACE_ID, TOWER_ACCESS_TOKEN, SEQERA_TOKEN_FILE,
#   NCHC_SITE_CONFIG
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/settings.sh"
# The box table, from the config that is its only copy - never retyped here.
. "$HERE/utils/boxes.sh"

usage() {
    # Lifted out of the header above rather than restated, so the two cannot
    # disagree - matched on text, not a line number, which silently starts
    # printing the wrong comment the day a line is inserted above it.
    grep -m1 -o 'tune_resources\.sh \[--json\].*' "${BASH_SOURCE[0]}" \
        | sed 's/^/usage: /'
    echo "       tune_resources.sh --config --samples <n> --input-size <size> <run-id>"
    echo "  --json                emit the table as JSON"
    echo "  --trace <file>        read an execution_trace_*.txt instead of asking Platform"
    echo "  --config              print a tuned config for the oversized processes"
    echo "  --samples <n>         required with --config"
    echo "  --input-size <size>   required with --config"
}

# --- GB, from whatever unit Platform or the trace happens to be using -------
to_gb() {
    local s="${1:-}" num unit
    s="${s//[[:space:]]/}"
    [ -n "$s" ] || { echo 0; return 0; }
    num=$(sed -E 's/^([0-9]*\.?[0-9]+).*/\1/' <<<"$s")
    [ -n "$num" ] || { echo 0; return 0; }
    unit=$(sed -E 's/^[0-9]*\.?[0-9]+//' <<<"$s" | tr '[:lower:]' '[:upper:]')
    case "$unit" in
        TB|T) awk -v n="$num" 'BEGIN{printf "%.4f", n*1024}' ;;
        MB|M) awk -v n="$num" 'BEGIN{printf "%.4f", n/1024}' ;;
        KB|K) awk -v n="$num" 'BEGIN{printf "%.6f", n/1048576}' ;;
        *)    awk -v n="$num" 'BEGIN{printf "%.4f", n}' ;;   # bare number or GB/G
    esac
}
fmt_gb() { awk -v g="${1:-0}" 'BEGIN{ if (g==int(g)) printf "%d GB", g; else printf "%.1f GB", g }'; }

# --- Platform's own table: process | peak RSS | peak VMEM | % allocated ------
# Column POSITION, not name - `tw` prints a fixed shape here, unlike the trace
# file below, which names its own columns and is read that way on purpose.
parse_metrics_table() {
    awk -F'|' '
        {
            if (NF < 3) next
            for (i = 1; i <= 4; i++) { gsub(/^[ \t]+|[ \t]+$/, "", $i) }
            proc = $1
            if (proc == "" || tolower(proc) == "process" || proc ~ /^-+$/) next
            peak = $2; alloc = $3
            if (peak !~ /[0-9]/ || alloc !~ /[0-9]/) next
            # "-" rather than empty: bash read with IFS=dollar-tab still
            # collapses RUNS of tab, because tab counts as blank for that
            # purpose no matter what IFS is set to - unlike a real delimiter
            # such as a pipe, an empty field between two tabs silently
            # vanishes and shifts every field after it. Every writer of this
            # table follows the rule below; every reader undoes it.
            pct = (NF >= 4 && $4 != "") ? $4 : "-"
            print proc "\t" peak "\t" alloc "\t" pct
        }
    '
}

# --- the on-disk trace: a TSV despite the extension, columns keyed by NAME ---
# nf-core's own field order is not this script's business - the fixture this
# is tested against deliberately puts peak_vmem before peak_rss, and a reader
# keyed on position would silently swap the two.
parse_trace_tasks() {
    awk -F'\t' '
        NR == 1 {
            for (i = 1; i <= NF; i++) { h = $i; gsub(/^[ \t]+|[ \t]+$/, "", h); col[h] = i }
            next
        }
        {
            ni = col["name"]; vi = col["peak_vmem"]; ri = col["peak_rss"]
            if (ni == "" || vi == "" || ri == "") next
            name = $ni; vmem = $vi; rss = $ri
            gsub(/^[ \t]+|[ \t]+$/, "", vmem); gsub(/^[ \t]+|[ \t]+$/, "", rss)
            if (vmem == "" || rss == "" || vmem == "-" || rss == "-") next
            # A task tag carries the workflow path and the sample, neither of
            # which is what the box table is keyed on - fold every task of one
            # process to the bare process name, e.g.
            # "NFCORE_RNASEQ:RNASEQ:QUALIMAP_RNASEQ (SAMPLE_1)" -> "QUALIMAP_RNASEQ".
            n = name
            idx = 0
            for (i = length(n); i >= 1; i--) { if (substr(n, i, 1) == ":") { idx = i; break } }
            if (idx > 0) n = substr(n, idx + 1)
            sub(/[ \t]*\([^)]*\)[ \t]*$/, "", n)
            gsub(/^[ \t]+|[ \t]+$/, "", n)
            if (n == "") next
            print n "\t" vmem "\t" rss
        }
    ' "$1"
}

# Fold every task down to one row per process: the PEAK across its tasks, not
# whichever task happened to be read last.
trace_rows() {
    local file="$1" proc vmem rss
    # The fold used to run in bash with `local -A`, which needs bash 4; macOS
    # ships bash 3.2, so the whole tool died there at parse time. awk has had
    # associative arrays forever, and this keeps the conversion in bash where
    # to_gb lives.
    while IFS=$'\t' read -r proc vmem rss; do
        [ -n "$proc" ] || continue
        printf '%s\t%s\t%s\n' "$proc" "$(to_gb "$rss")" "$(to_gb "$vmem")"
    done < <(parse_trace_tasks "$file") \
    | awk -F'\t' '
        # Keep the string that was read, ordered by its numeric value: the
        # caller prints these, and "6.0" must not silently become "6".
        {
            r = $2 + 0; v = $3 + 0
            if (!($1 in nr) || r > nr[$1]) { nr[$1] = r; sr[$1] = $2 }
            if (!($1 in nv) || v > nv[$1]) { nv[$1] = v; sv[$1] = $3 }
        }
        END { for (k in sr) printf "%s\t%s\t%s\t-\n", k, sr[k], sv[k] }
      ' | sort
}

fetch_metrics() {
    local tw ws token_f token out rc
    tw="${TW_BIN:-$(setting tw_bin)}"; [ -n "$tw" ] || tw="$(command -v tw 2>/dev/null)"
    [ -n "$tw" ] && [ -x "$tw" ] || { echo "no usable tw: '$tw' (set tw_bin or TW_BIN)" >&2; return 1; }
    ws="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
    token_f="$(token_file)"
    if [ -n "${TOWER_ACCESS_TOKEN:-}" ]; then
        token="$TOWER_ACCESS_TOKEN"
    elif [ -r "$token_f" ]; then
        token="$(cat "$token_f")"
    else
        echo "no Seqera token: looked at $token_f" >&2; return 1
    fi
    # The token goes through the environment only, never on the command line,
    # where `ps` would show it to every other user on a shared login node.
    out=$(TOWER_ACCESS_TOKEN="$token" "$tw" runs view -i "$RUN" ${ws:+-w "$ws"} metrics 2>&1); rc=$?
    [ "$rc" -eq 0 ] || { printf '%s\n' "$out" >&2; return 1; }
    printf '%s\n' "$out"
}

# --- smallest box whose mem covers a request, from the table loaded below ---
box_index_for_gb() {
    local gb="$1" i
    for (( i = 0; i < ${#BQ[@]}; i++ )); do
        if awk -v a="${BM[$i]}" -v b="$gb" 'BEGIN{exit !(a>=b)}'; then
            echo "$i"; return 0
        fi
    done
    echo $(( ${#BQ[@]} - 1 ))
}

# ============================================================================
JSON=0; CONFIG=0; TRACE=""; SAMPLES=""; INPUT_SIZE=""; RUN=""
while [ $# -gt 0 ]; do
    case "$1" in
        --json)        JSON=1; shift ;;
        --config)      CONFIG=1; shift ;;
        --trace)       TRACE="${2:?--trace needs a file}"; shift 2 ;;
        --samples)     SAMPLES="${2:?--samples needs a number}"; shift 2 ;;
        --input-size)  INPUT_SIZE="${2:?--input-size needs a size}"; shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        --) shift; break ;;
        -*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
        *)  RUN="$1"; shift ;;
    esac
done
[ -n "$RUN" ] || { usage >&2; exit 2; }

if [ "$CONFIG" = 1 ]; then
    missing=()
    [ -n "$SAMPLES" ]    || missing+=("--samples <n>")
    [ -n "$INPUT_SIZE" ] || missing+=("--input-size <size>")
    if [ "${#missing[@]}" -gt 0 ]; then
        echo "A tuned config with no record of what it was tuned against is a trap:" >&2
        echo "the same sizing on ten times the data is an OOM (docs/PITFALLS.md 6d)." >&2
        echo "Missing: ${missing[*]}" >&2
        exit 1
    fi
fi

# --- the measurement --------------------------------------------------------
if [ -n "$TRACE" ]; then
    [ -r "$TRACE" ] || { echo "cannot read trace file: $TRACE" >&2; exit 1; }
    RAW_ROWS="$(trace_rows "$TRACE")"
else
    RAW="$(fetch_metrics)" || exit 1
    RAW_ROWS="$(parse_metrics_table <<<"$RAW")"
fi

if [ -z "$RAW_ROWS" ]; then
    if [ -n "$TRACE" ]; then
        echo "no per-process measurement in $TRACE." >&2
    else
        echo "no per-process measurement came back for this run." >&2
        echo "Check for pipeline_info/execution_trace_*.txt in the run's outdir and" >&2
        echo "pass it with --trace instead - it carries the same peak_rss/peak_vmem" >&2
        echo "per task, from the filesystem side rather than Platform's." >&2
    fi
    exit 1
fi

# --- the box table -----------------------------------------------------------
SITE_CONFIG="${NCHC_SITE_CONFIG:-$ROOT/configs/sites/nchc.config}"
declare -a BQ=() BC=() BM=() BH=()
_bi=0
while IFS=$'\t' read -r q c m h; do
    BQ[_bi]="$q"; BC[_bi]="$c"; BM[_bi]="$m"; BH[_bi]="$h"; _bi=$((_bi + 1))
done < <(nchc_boxes "$SITE_CONFIG" 2>/dev/null)
if [ "$_bi" -eq 0 ]; then
    echo "cannot size a single suggestion: the box table in $SITE_CONFIG could not" >&2
    echo "be read (scripts/utils/boxes.sh is the only place NCHC_BOXES is parsed)." >&2
    exit 1
fi

# --- one row per process: measured, and what it should move to --------------
# A process is only ever sent DOWN, and only when the box that covers peak x
# 1.5 is a full tier below the box its allocation rounds to - a 10% overshoot
# stays in the same box and is reported as unchanged, not as a move. A process
# already near its own ceiling is never sent down even if the arithmetic
# above would agree, on the same reasoning runs.md gives an OOM'd task: a
# request that is too small is not a slow run, it is a second failure.
ROWS_TSV="$(mktemp)"; trap 'rm -f "$ROWS_TSV"' EXIT
NEAR_CEILING_PCT=85
while IFS=$'\t' read -r proc peak_raw alloc_raw pct_raw; do
    [ -n "$proc" ] || continue
    peak_gb="$(to_gb "$peak_raw")"
    alloc_gb="$(to_gb "$alloc_raw")"
    pct=""
    [ -n "$pct_raw" ] && [ "$pct_raw" != "-" ] && pct="${pct_raw%\%}"

    cur_idx="$(box_index_for_gb "$alloc_gb")"
    target_gb="$(awk -v p="$peak_gb" 'BEGIN{printf "%.4f", p*1.5}')"
    tgt_idx="$(box_index_for_gb "$target_gb")"
    tiers=$(( cur_idx - tgt_idx ))
    [ "$tiers" -ge 0 ] || tiers=0

    suggested=0; queue=""; cpus=""; mem=""
    if [ "$tiers" -ge 1 ]; then
        near_ceiling=0
        if [ -n "$pct" ] && awk -v p="$pct" -v c="$NEAR_CEILING_PCT" 'BEGIN{exit !(p+0>=c)}'; then
            near_ceiling=1
        fi
        if [ "$near_ceiling" = 0 ]; then
            suggested=1
            queue="${BQ[$tgt_idx]}"; cpus="${BC[$tgt_idx]}"; mem="${BM[$tgt_idx]}"
        fi
    fi
    # "-" for anything that can legitimately be empty - see the note in
    # parse_metrics_table above about why a truly empty field cannot survive
    # a tab-delimited `read`.
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$proc" "$alloc_gb" "$peak_gb" "${pct:--}" "$suggested" "${queue:--}" \
        "$tiers" "${cpus:--}" "${mem:--}" \
        >> "$ROWS_TSV"
done <<<"$RAW_ROWS"

# --- render -------------------------------------------------------------------
render_table() {
    printf '%-24s %10s %10s %7s   %s\n' "process" "allocated" "peak" "used" "suggestion"
    while IFS=$'\t' read -r proc alloc peak pct suggested queue tiers cpus mem; do
        pct_disp="-"; [ -n "$pct" ] && [ "$pct" != "-" ] && pct_disp="${pct}%"
        if [ "$suggested" = 1 ]; then
            word="tier"; [ "$tiers" != 1 ] && word="tiers"
            sug="→ ${queue}  (${tiers} ${word} down)"
        else
            sug="unchanged"
        fi
        printf '%-24s %10s %10s %7s   %s\n' \
            "$proc" "$(fmt_gb "$alloc")" "$(fmt_gb "$peak")" "$pct_disp" "$sug"
    done < "$ROWS_TSV"
}

render_json() {
    python3 - "$ROWS_TSV" <<'PY'
import sys, json
rows = []
with open(sys.argv[1]) as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = (line.split("\t") + [""] * 9)[:9]
        proc, alloc, peak, pct, suggested, queue, tiers, cpus, mem = parts
        val = lambda s: (None if s in ("", "-") else s)
        pct, queue = val(pct), val(queue)
        rows.append({
            "process": proc,
            "allocated_gb": float(alloc) if alloc else None,
            "peak_gb": float(peak) if peak else None,
            "pct_allocated": float(pct) if pct else None,
            "suggested": suggested == "1",
            "suggested_queue": queue,
            "tiers": int(tiers) if tiers else 0,
        })
print(json.dumps(rows, indent=2))
PY
}

render_config() {
    local any=0
    cat <<EOF
// Tuned config for run $RUN, written $(date '+%Y-%m-%d %H:%M:%S %z')
// by scripts/tune_resources.sh --config.
//
// Tuned against $SAMPLES samples, ~$INPUT_SIZE input. The same sizing on
// materially more data than that is an OOM (docs/PITFALLS.md 6d) - re-tune
// with this script rather than reusing this file on a larger batch than the
// one named above.
EOF
    while IFS=$'\t' read -r proc alloc peak pct suggested queue tiers cpus mem; do
        [ "$suggested" = 1 ] || continue
        any=1
        pct_note="${pct}% used"; [ "$pct" = "-" ] && pct_note="no % figure from this source"
        cat <<EOF

// $proc peaked at $(fmt_gb "$peak") inside a $(fmt_gb "$alloc") box ($pct_note)
// - $tiers tier(s) smaller ($queue) still covers peak x 1.5.
//
// Written as closures on task.attempt, matching what this block replaces. A
// fixed number here would override nf-core's own escalating label directive
// and switch off the automatic retry-at-double (PITFALLS 6d), and it would do
// so PERMANENTLY: this file is saved to be reused, so every future launch of
// this pipeline would lose the recovery, not just one run.
//
// The 1.5x headroom is measured against the data named above and does not
// travel. Re-tune when the data changes; until then the retry is what covers
// the gap if it changed more than expected.
process {
    withName: '$proc' {
        cpus   = { $cpus * task.attempt }
        memory = { ${mem}.GB * task.attempt }
    }
}
EOF
    done < "$ROWS_TSV"
    if [ "$any" = 0 ]; then
        echo
        echo "// Nothing here is a full tier oversized against $SAMPLES samples /"
        echo "// $INPUT_SIZE input - no override needed."
    fi
}

if [ "$CONFIG" = 1 ]; then
    render_config
elif [ "$JSON" = 1 ]; then
    render_json
else
    render_table
fi
