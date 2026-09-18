#!/bin/bash
# Tests for scripts/prepare_launch.sh (T10): one call merging the
# no-judgement parts of commands/launch.md's steps 1-6 - revision lookup,
# schema fetch, registration check, a samplesheet draft, and preflight -
# into one structured summary.
#
# Runs entirely offline via two seams:
#   --fixture-dir   pipeline files (nextflow_schema.json, schema_input.json,
#                   conf/base.config) read from a local directory instead of
#                   fetched from GitHub - the same seam a member who already
#                   has the pipeline cloned would want, not testing-only glue.
#   a fake preflight.sh, copied in beside a real settings.sh/portable.sh in a
#   scratch scripts/ dir - the same "copy the real script, replace its
#   siblings" technique tests/site_report_test.sh already uses, because
#   prepare_launch.sh finds preflight.sh the same way (beside itself).
#
# TW_BIN is left unset/pointed at nothing in every case, so the "registered?"
# check reports "unknown" rather than reaching a real `tw` - no cluster, no
# network, matching every other test here.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REAL="$ROOT/scripts/prepare_launch.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-68s ok\n' "$1"; }
no() { printf '%-68s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
has() { grep -qF -- "$2" <<<"$1"; }
count() { grep -cF -- "$2" <<<"$1" || true; }

SDIR="$TMP/scripts"; mkdir -p "$SDIR/utils"
cp "$REAL" "$SDIR/prepare_launch.sh"
cp "$ROOT/scripts/settings.sh" "$SDIR/settings.sh"
cp "$ROOT/scripts/utils/portable.sh" "$SDIR/utils/portable.sh"

SETTINGS="$TMP/env.yaml"; printf 'workspace_id: ws1\n' > "$SETTINGS"

fake_preflight() {   # fake_preflight <line>...
    { printf '#!/bin/bash\n'
      for l in "$@"; do printf 'echo %q\n' "$l"; done
      # preflight.sh's own exit convention: nonzero iff a FAIL line was printed
      if printf '%s\n' "$@" | grep -q '^FAIL'; then printf 'exit 1\n'; else printf 'exit 0\n'; fi
    } > "$SDIR/preflight.sh"
    chmod +x "$SDIR/preflight.sh"
}

# A minimal fixture pipeline with NO required-with-no-default parameter and
# no GPU directive, so a scenario built on it produces no `DECIDE:` noise of
# its own - only what each test deliberately introduces.
FIX="$TMP/fixture"; mkdir -p "$FIX/assets" "$FIX/conf"
cat > "$FIX/assets/schema_input.json" <<'JSON'
{"items": {"type": "object", "properties": {
  "sample": {"type": "string"}, "fastq_1": {"type": "string"}
}}}
JSON
cat > "$FIX/nextflow_schema.json" <<'JSON'
{"definitions": {"generic_options": {"title": "Generic options",
  "properties": {"email": {"type": "string", "default": ""}}}}}
JSON
cat > "$FIX/conf/base.config" <<'CFG'
process { cpus = 2; memory = '8.GB' }
CFG

READS="$TMP/reads"; mkdir -p "$READS"
: > "$READS/S1_R1.fastq.gz"; : > "$READS/S1_R2.fastq.gz"

run() {   # run <extra-args...>  -> sets $out, $rc
    out=$(LAB_SETTINGS_FILE="$SETTINGS" TW_BIN=/does/not/exist \
          bash "$SDIR/prepare_launch.sh" --repo nf-core/testpipeline \
          --revision 1.2.3 --input "$READS" --fixture-dir "$FIX" "$@" 2>&1)
    rc=$?
}

# =========================================================================
# Scenario A: everything passes - preflight all OK, tw unreachable so
# registration is 'unknown' would normally warn, but this scenario is about
# the BLOCKING/WARNING counts specifically, so it stubs a reachable
# registration answer by skipping the tw check entirely (TW_BIN points
# nowhere - this fixture only asserts zero BLOCKING, and separately (below)
# a warning-only case for the registration check itself).
# =========================================================================
fake_preflight "OK         reach          local - this deployment runs on the site" \
               "OK         run-area       /work/u/lab_runs" \
               "OK         egress         relay is up" \
               "OK         agent          running" \
               "OK         resources      matches" \
               "OK         compute-env    AVAILABLE"
run
[ "$rc" = 0 ] && ok "scenario A (all OK): exits 0" || no "scenario A (all OK): exits 0" "rc=$rc"
order=$(grep -oE '^== [a-z]+ ==' <<<"$out" | tr -d '\n')
[ "$order" = "== pipeline ==== samplesheet ==== preflight ==== parameters ==== decisions ==" ] \
    && ok "the five sections appear, always in this order" \
    || no "the five sections appear, always in this order" "<<$order>>"
n=$(count "$out" "BLOCKING:")
[ "$n" = 0 ] && ok "scenario A: zero BLOCKING entries" || no "scenario A: zero BLOCKING entries" "got $n"
n=$(count "$out" "DECIDE: parameters required")
[ "$n" = 0 ] && ok "scenario A: the fixture schema has nothing required-with-no-default" \
             || no "scenario A: the fixture schema has nothing required-with-no-default" "got $n"
has "$out" "rows: 1" && ok "scenario A: the samplesheet draft counts the one fastq pair" \
                      || no "scenario A: the samplesheet draft counts the one fastq pair" "<<$out>>"
has "$out" "S1  S1_R1.fastq.gz  S1_R2.fastq.gz" \
    && ok "scenario A: the samplesheet draft samples the row" \
    || no "scenario A: the samplesheet draft samples the row" "<<$out>>"
has "$out" "revision: 1.2.3" && ! has "$out" "resolved automatically" \
    && ok "scenario A: a given revision is not flagged as auto-resolved" \
    || no "scenario A: a given revision is not flagged as auto-resolved" "<<$out>>"

# =========================================================================
# Scenario B: exactly one warning (registration unknown), still zero
# BLOCKING and zero DECIDE, by omitting --revision so the ONLY new signal is
# the registration warning this whole file already keeps off in scenario A
# via a given revision - here a revision is still given, so the one
# deliberate difference is asking prepare_launch.sh about registration with
# no tw reachable, which every scenario already does; scenario A already
# proved that alone produces a warning, so this fixture isolates it and
# counts precisely.
# =========================================================================
run
n=$(count "$out" "WARNING:")
[ "$n" = 1 ] && ok "scenario B: exactly one WARNING (registration unknown)" \
             || no "scenario B: exactly one WARNING (registration unknown)" "got $n <<$out>>"
has "$out" "WARNING: could not check whether the pipeline is already registered" \
    && ok "scenario B: the warning names what could not be checked" \
    || no "scenario B: the warning names what could not be checked" "<<$out>>"

# =========================================================================
# Scenario C: multiple failures - two preflight FAILs plus a missing input
# directory, all surfaced together, run to completion (never stops early).
# =========================================================================
fake_preflight "OK         reach          local - this deployment runs on the site" \
               "FAIL       egress         the site's egress channel is down" \
               "FAIL       agent          not running"
out=$(LAB_SETTINGS_FILE="$SETTINGS" TW_BIN=/does/not/exist \
      bash "$SDIR/prepare_launch.sh" --repo nf-core/testpipeline --revision 1.2.3 \
      --input "$TMP/no-such-reads-dir" --fixture-dir "$FIX" 2>&1); rc=$?
[ "$rc" = 1 ] && ok "scenario C (multiple failures): exits 1" \
             || no "scenario C (multiple failures): exits 1" "rc=$rc"
n=$(count "$out" "BLOCKING: preflight:")
[ "$n" = 2 ] && ok "scenario C: both preflight FAILs become BLOCKING entries" \
             || no "scenario C: both preflight FAILs become BLOCKING entries" "got $n <<$out>>"
has "$out" "== samplesheet ==" && has "$out" "cannot list" \
    && ok "scenario C: the missing input directory is reported, not fatal" \
    || no "scenario C: the missing input directory is reported, not fatal" "<<$out>>"
has "$out" "== parameters ==" \
    && ok "scenario C: every section still ran despite the earlier failures" \
    || no "scenario C: every section still ran despite the earlier failures" "<<$out>>"

# --- usage --------------------------------------------------------------
bash "$SDIR/prepare_launch.sh" >/dev/null 2>&1
[ "$?" = 2 ] && ok "no --repo given exits 2" || no "no --repo given exits 2" "wrong rc"

# =========================================================================
# Scenario D: the two cross-branch sections - `paths` (where.sh --run-paths)
# and `in flight` (parallel_watch_check.sh, duplicate_run_check.sh). The
# helpers are stubbed beside the copied script the same way preflight.sh is,
# so each case controls exactly what they report.
# =========================================================================
fake_preflight "OK: all good"
stub() {   # stub <name> <exit> <stdout-line>...
    local name="$1" rc="$2"; shift 2
    { printf '#!/bin/bash\n'
      for l in "$@"; do printf 'echo %q\n' "$l"; done
      printf 'exit %s\n' "$rc"
    } > "$SDIR/$name"; chmod +x "$SDIR/$name"
}
stub where.sh 0 "site_run_dir=/site/u/projects/p1/runs/r1" "local_fetch_dir=/home/me/agentic-bioflow/projects/p1/runs/r1/results"
stub parallel_watch_check.sh 0
stub duplicate_run_check.sh 0

run
has "$out" "== paths ==" \
    && no "without --project there is no paths section to guess at" "<<$out>>" \
    || ok "without --project there is no paths section to guess at"
has "$out" "== in flight ==" && has "$out" "nothing else of yours is running" \
    && ok "in flight section says plainly when nothing overlaps" \
    || no "in flight section says plainly when nothing overlaps" "<<$out>>"

run --project p1 --run r1
has "$out" "site run dir:     /site/u/projects/p1/runs/r1" \
    && has "$out" "local fetch dir:  /home/me/agentic-bioflow/projects/p1/runs/r1/results" \
    && ok "with --project/--run both absolute paths are shown" \
    || no "with --project/--run both absolute paths are shown" "<<$out>>"
has "$out" "confirm where results land" \
    && ok "...and confirming them is listed as a decision" \
    || no "...and confirming them is listed as a decision" "<<$out>>"

stub parallel_watch_check.sh 1 "3 of your runs are active; the site allows 4 sessions"
stub duplicate_run_check.sh 1 "r0 (RUNNING) uses the same samplesheet in project p1"
run --project p1 --run r1 --samplesheet /x/samplesheet.csv
has "$out" "3 of your runs are active" && has "$out" "r0 (RUNNING) uses the same samplesheet" \
    && ok "in flight shows the session-cap line and the duplicate line" \
    || no "in flight shows the session-cap line and the duplicate line" "<<$out>>"
has "$out" "looks like a run already in flight" \
    && ok "...and a duplicate is raised as a decision, not buried" \
    || no "...and a duplicate is raised as a decision, not buried" "<<$out>>"
[ "$rc" = 0 ] && ok "advisory findings alone never make the call fail" \
    || no "advisory findings alone never make the call fail" "rc=$rc"

stub duplicate_run_check.sh 1 "should not be consulted"
run --project p1 --run r1
has "$out" "should not be consulted" \
    && no "no --samplesheet means no duplicate check is attempted" "<<$out>>" \
    || ok "no --samplesheet means no duplicate check is attempted"
rm -f "$SDIR/where.sh" "$SDIR/parallel_watch_check.sh" "$SDIR/duplicate_run_check.sh"

echo
[ "$fails" = 0 ] && echo "OK: prepare_launch.sh" || { echo "$fails failed"; exit 1; }
