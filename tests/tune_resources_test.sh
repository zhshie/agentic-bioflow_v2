#!/bin/bash
# Platform HAS a resource optimiser and this deployment must keep it switched
# off (`--disable-optimization`, docs/PITFALLS.md 9): it right-sizes from run
# history, and a helpfully reduced request lands below a fixed box's floor and
# then never schedules at all. So the one thing that would make an
# over-allocated process cheaper here - noticing that it peaked at 6 GB inside a
# 53 GB box - is the one thing nothing does. That gap is what
# scripts/tune_resources.sh fills, and it is only safe to fill if it obeys the
# same box table as everything else.
#
# The failures this pins down, each of them one someone would make by hand:
#
#   - suggesting a size that is not a box. A number between two boxes is not a
#     smaller request, it is a request that never starts (PITFALLS 6). The box
#     table therefore has to come out of configs/sites/nchc.config through
#     scripts/utils/boxes.sh; a literal 'ngs13G' anywhere in the script is the
#     copy that goes stale, so this test greps for one.
#   - suggesting a change that is not worth making. A process 10% oversized
#     still sits in the same box, and a report full of those trains a reader to
#     skip the one row that matters.
#   - reading the peak and the allocation the wrong way round, which turns
#     "6 GB used of 33" into "33 used of 6" and proposes an OOM.
#   - parsing the on-disk trace by column POSITION. It is a TSV whose field
#     order is Nextflow's business, not ours - the fixture below deliberately
#     puts peak_vmem before peak_rss.
#   - saving a tuned config with no record of what it was tuned against. The
#     same numbers on ten times the data are an OOM, so --config refuses to
#     write one without the sample count and the input size.
#
# `tw` is stubbed through TW_BIN, the way tests/relaunch_override_test.sh and
# tests/agent_ctl_connection_id_test.sh stub it. Nothing here may reach the live
# workspace: this script reads a real run's metrics, and the run ids that would
# work are real ones.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S="$ROOT/scripts/tune_resources.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

ok()  { printf '%-62s ok\n' "$1"; }
bad() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
t()   { grep -qF -- "$2" <<<"$3" && ok "$1" || bad "$1" "lacks '$2'"; }
tn()  { grep -qF -- "$2" <<<"$3" && bad "$1" "has '$2'" || ok "$1"; }
tre() { grep -qE -- "$2" <<<"$3" && ok "$1" || bad "$1" "no match /$2/"; }

# --- what the boxes actually are, read the way every other consumer reads them.
# If this test typed a queue name by hand it would agree with a stale script
# forever, which is the failure the script itself is being tested for.
. "$ROOT/scripts/utils/boxes.sh"
box_at() {   # box_at <gb> -> idx<TAB>queue<TAB>cpus<TAB>mem   (smallest box that fits)
    local i=0 q c m h
    while IFS=$'\t' read -r q c m h; do
        if awk -v a="$m" -v b="$1" 'BEGIN{exit !(a>=b)}'; then
            printf '%s\t%s\t%s\t%s' "$i" "$q" "$c" "$m"; return 0
        fi
        i=$((i+1))
    done < <(nchc_boxes)
    return 1
}
IFS=$'\t' read -r QI QQ QC QM < <(box_at 9)     # QUALIMAP:  6 GB peak x 1.5
IFS=$'\t' read -r AI AQ AC AM < <(box_at 33)    # QUALIMAP:  33 GB allocated
IFS=$'\t' read -r PI PQ PC PM < <(box_at 29)    # PICARD:    19 GB peak x 1.5
TIERS=$((AI - QI))
[ -n "$QQ" ] && [ -n "$AQ" ] || { echo "boxes.sh gave no table - nothing below can be checked"; exit 1; }

# --- a stub tw --------------------------------------------------------------
# It logs its argv and answers `runs view ... metrics` the way the real one
# does: per process, peak RSS, peak virtual memory, and the percentage of the
# allocation Platform says was used.
cat > "$TMP/tw" <<'STUB'
#!/bin/bash
echo "$*" >> "$TWLOG"
case "$*" in
  *metrics*)
      echo "  Memory"
      echo "  process                | peak RSS | peak VMEM | % allocated"
      echo "  -----------------------+----------+-----------+------------"
      echo "  PICARD_MARKDUPLICATES  |     19GB |      34GB |         54%"
      echo "  QUALIMAP_RNASEQ        |      6GB |      33GB |         16%"
      echo "  STAR_ALIGN             |     30GB |      34GB |         88%" ;;
  *"runs view"*)
      echo "   Status        | SUCCEEDED" ;;
esac
STUB
chmod +x "$TMP/tw"

area() {
    local d="$TMP/$1"; mkdir -p "$d/_personal"
    echo "not-a-real-token" > "$d/_personal/.seqera_token"
    printf 'workspace_id: 12345\n' > "$d/_personal/env.yaml"
    printf '%s' "$d"
}
A="$(area run)"
run() {
    : > "$TMP/tw.log"
    ( export LAB_RUNS_DIR="$A" LAB_SETTINGS_FILE="$A/_personal/env.yaml" \
             TW_BIN="$TMP/tw" TWLOG="$TMP/tw.log"
      bash "$S" "$@" 2>&1 )
}
twlog() { cat "$TMP/tw.log" 2>/dev/null; }

# --- it can say what it takes ------------------------------------------------
out=$(bash "$S" -h 2>&1)
t  "-h names the arguments"          "tune_resources.sh"  "$out"
t  "-h names --json"                 "--json"             "$out"
out=$(bash "$S" 2>&1); rc=$?
[ "$rc" != 0 ] && ok "no arguments: exits non-zero" || bad "no arguments: exits non-zero" "rc=0"

# --- invariant 1 is answered in the file itself ------------------------------
# This is the one place in the repo that rebuilds something Seqera ships, so the
# reason has to be written down where the next person meets it.
src=$(cat "$S" 2>/dev/null)
t "the script says why it exists next to Platform's optimiser" "--disable-optimization" "$src"
t "and cites the pitfall that turns that optimiser off"        "PITFALLS"               "$src"

# --- no second copy of the box table -----------------------------------------
t  "reads the box table through boxes.sh"  "utils/boxes.sh"  "$src"
printf '%-62s ' "no box name is retyped in the script"
if grep -qE '\bngs[0-9]+G\b' <<<"$src"; then
    echo "FAIL: $(grep -oE '\bngs[0-9]+G\b' <<<"$src" | sort -u | tr '\n' ' ')"
    fails=$((fails+1))
else echo ok; fi

# --- the table ---------------------------------------------------------------
out=$(run 312SbdATPc2grr)
t "reports the over-allocated process"       "QUALIMAP_RNASEQ"  "$out"
t "names the box it should move to"          "$QQ"              "$out"
t "says how many tiers down that is"         "$TIERS tiers down" "$out"
t "prints what was allocated"                "33"               "$out"
t "prints the peak it actually reached"      "6"                "$out"
t "prints Platform's own percentage"         "16%"              "$out"

# --- only a full tier is worth reporting -------------------------------------
# PICARD peaked at 19 GB in a 34 GB allocation. 19 x 1.5 is 28.5, which lands in
# the same box, so there is nothing to move and nothing to say.
printf '%-62s ' "a process already in the right box gets no suggestion"
if grep -E '^\s*PICARD_MARKDUPLICATES' <<<"$out" | grep -q '→\|->'; then
    echo "FAIL: it proposed a move for a process that is already right-sized"
    fails=$((fails+1))
else echo ok; fi
[ "$PI" = "$AI" ] && ok "the fixture really does keep PICARD in its box" \
                  || bad "the fixture really does keep PICARD in its box" "idx $PI vs $AI"
t "but it is still shown, so the reader knows it was measured" "PICARD_MARKDUPLICATES" "$out"
t "and says so in a word"                                      "unchanged"             "$out"

# A process at 88% of its allocation is not over-allocated; proposing a smaller
# box for it is proposing an OOM.
printf '%-62s ' "a process near its ceiling is never sent down"
if grep -E '^\s*STAR_ALIGN' <<<"$out" | grep -q 'tiers\? down'; then
    echo "FAIL: it proposed shrinking a process running at 88%"; fails=$((fails+1))
else echo ok; fi

# --- how it talked to Platform ------------------------------------------------
log="$(twlog)"
t  "asks Platform for metrics"               "metrics"          "$log"
t  "scoped to the workspace"                 "-w 12345"         "$log"
t  "names the run"                           "312SbdATPc2grr"   "$log"
tn "the token is never an argument"          "not-a-real-token" "$log"
tn "it never cancels anything"               "runs cancel"      "$log"
tn "it never relaunches anything"            "runs relaunch"    "$log"
tn "it never launches anything"              "tw launch"        "$log"

# --- --json -------------------------------------------------------------------
out=$(run --json 312SbdATPc2grr)
tre "--json emits the process"          '"process"[[:space:]]*:[[:space:]]*"QUALIMAP_RNASEQ"' "$out"
tre "--json emits the suggested box"    "\"suggested_queue\"[[:space:]]*:[[:space:]]*\"$QQ\"" "$out"
tre "--json emits the tier distance"    "\"tiers\"[[:space:]]*:[[:space:]]*$TIERS"            "$out"
tre "--json marks the unchanged ones"   '"suggested"[[:space:]]*:[[:space:]]*false'           "$out"
printf '%-62s ' "--json is parseable JSON"
if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys; json.load(sys.stdin)' <<<"$out" >/dev/null 2>&1 \
        && echo ok || { echo "FAIL: python3 could not parse it"; fails=$((fails+1)); }
else echo "skipped (no python3)"; fi

# --- the on-disk trace, which is the same measurement from the other side ----
# nf-core writes pipeline_info/execution_trace_*.txt - a TSV despite the
# extension. Field ORDER is Nextflow's business: this fixture puts peak_vmem
# before peak_rss on purpose, and two tasks of one process so the peak has to be
# the max rather than the last row read.
TR="$TMP/execution_trace_2026-09-08.txt"
printf 'task_id\thash\tname\tstatus\texit\tpeak_vmem\tpeak_rss\trealtime\n' > "$TR"
printf '1\taa/11\tNFCORE_RNASEQ:RNASEQ:QUALIMAP_RNASEQ (S1)\tCOMPLETED\t0\t33 GB\t5.2 GB\t1h\n' >> "$TR"
printf '2\tbb/22\tNFCORE_RNASEQ:RNASEQ:QUALIMAP_RNASEQ (S2)\tCOMPLETED\t0\t33 GB\t6 GB\t1h\n' >> "$TR"
printf '3\tcc/33\tPICARD_MARKDUPLICATES (S1)\tCOMPLETED\t0\t34 GB\t19 GB\t2h\n' >> "$TR"
printf '4\tdd/44\tSOMETHING_UNMEASURED (S1)\tCOMPLETED\t0\t-\t-\t1m\n' >> "$TR"

out=$(run --trace "$TR" 312SbdATPc2grr)
t  "the trace is read at all"                  "QUALIMAP_RNASEQ"   "$out"
t  "the trace suggestion matches the metrics"  "$QQ"               "$out"
t  "the process name loses its tag"            "QUALIMAP_RNASEQ "  "$out "
tn "and loses the workflow prefix"             "NFCORE_RNASEQ:"    "$out"
t  "the peak is the max across tasks, not the last" "6"            "$out"
tn "a task with no measurement is not invented"     "SOMETHING_UNMEASURED" "$out"
[ -z "$(twlog)" ] && ok "--trace asks Platform nothing" \
                  || bad "--trace asks Platform nothing" "log: $(twlog)"

# --- a config that does not say what it was tuned against is a trap ----------
out=$(run --config 312SbdATPc2grr); rc=$?
[ "$rc" != 0 ] && ok "--config without provenance: exits non-zero" \
               || bad "--config without provenance: exits non-zero" "rc=0"
t "--config without provenance says what is missing" "--samples"    "$out"
t "and names the other half too"                     "--input-size" "$out"

out=$(run --config --samples 6 --input-size 24GB 312SbdATPc2grr)
t "the config selects the process by name"    "withName: 'QUALIMAP_RNASEQ'"  "$out"
# Escalating, not fixed, and the negative assertions matter as much as the
# positive ones. A plain `memory = N.GB` here would override nf-core's own
# escalating label directive and switch off the automatic retry-at-double
# (PITFALLS 6d) - permanently, because this file is saved to be reused, so
# every future launch of the pipeline would lose the recovery. The first
# version of this suite specified fixed numbers; it was written before that
# behaviour was measured.
t  "the config escalates cpus on retry"        "cpus   = { $QC * task.attempt }"    "$out"
t  "and memory with it"                        "memory = { $QM.GB * task.attempt }" "$out"
tn "no fixed cpus that would kill escalation"  "cpus   = $QC"                       "$out"
tn "no fixed memory either"                    "memory = $QM.GB"                    "$out"
t "the config records the sample count"       "6 samples"                    "$out"
t "the config records the input size"         "24GB"                         "$out"
t "the config warns that more data is an OOM" "OOM"                          "$out"
t "the config names the run it came from"     "312SbdATPc2grr"               "$out"
printf '%-62s ' "the config carries no block for an unchanged process"
grep -q "withName: 'PICARD_MARKDUPLICATES'" <<<"$out" \
    && { echo "FAIL: it pinned a process it had nothing to say about"; fails=$((fails+1)); } \
    || echo ok

# --- nothing measurable, nothing said ----------------------------------------
# Silence would be the bad outcome: an empty table reads exactly like a run with
# no over-allocation in it, which is the same mistake as an empty `tw` listing
# read as an answer.
cat > "$TMP/tw-empty" <<'STUB'
#!/bin/bash
echo "$*" >> "$TWLOG"
echo "  Memory"
echo "  process | peak RSS | peak VMEM | % allocated"
STUB
chmod +x "$TMP/tw-empty"
out=$( export LAB_RUNS_DIR="$A" LAB_SETTINGS_FILE="$A/_personal/env.yaml" \
              TW_BIN="$TMP/tw-empty" TWLOG="$TMP/tw.log"
       bash "$S" 312SbdATPc2grr 2>&1 ); rc=$?
[ "$rc" != 0 ] && ok "no measurements: exits non-zero" || bad "no measurements: exits non-zero" "rc=0"
t "no measurements: says so rather than printing an empty table" "no per-process measurement" "$out"
t "no measurements: names the other place to look"              "execution_trace"            "$out"

# --- and if the box table itself cannot be read ------------------------------
out=$( export LAB_RUNS_DIR="$A" LAB_SETTINGS_FILE="$A/_personal/env.yaml" \
              TW_BIN="$TMP/tw" TWLOG="$TMP/tw.log" \
              NCHC_SITE_CONFIG="$TMP/there-is-no-such-config"
       bash "$S" 312SbdATPc2grr 2>&1 ); rc=$?
[ "$rc" != 0 ] && ok "no box table: exits non-zero" || bad "no box table: exits non-zero" "rc=0"
t "no box table: refuses to name a size" "box table" "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
