#!/bin/bash
# A job that says `Reason=Resources` will start eventually, and the natural
# reaction - "wait longer" - is the expensive one. On this site every ngs
# partition is the same 46-node pool (PITFALLS 6b), so the thing that makes a
# job start sooner is asking for a smaller box, not a quieter queue. The
# operator cannot make that trade without seeing what the boxes are, so
# why_pending.sh has to lay the ladder out next to the request.
#
# The two failures this pins down:
#   - a "waiting" reason that prints no ladder, leaving the only lever invisible
#   - a ladder printed under a QOSMin* reason, which is actively wrong: that job
#     is stranded below the floor and shrinking it strands it harder.
#
# `scontrol` is stubbed through WHY_PENDING_SCONTROL_BIN so this runs anywhere,
# including on a node whose controller is down.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
W="$ROOT/scripts/why_pending.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()  { printf '%-58s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2'"; fails=$((fails+1)); }; }
tn() { printf '%-58s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: has '$2'"; fails=$((fails+1)); } || echo ok; }

# One stub serves every case: it answers `ping` UP always, and prints whatever
# job block the current case wrote to $TMP/job.
cat > "$TMP/scontrol" <<'STUB'
#!/bin/bash
case "$1 ${2:-}" in
  "ping "*)   echo "Slurmctld(primary) at lgn304 is UP"; exit 0 ;;
  "show job") [ -s "$TMP_JOB" ] && cat "$TMP_JOB" || exit 1 ;;
esac
STUB
chmod +x "$TMP/scontrol"

mkjob() { # mkjob <reason> <reqtres> <partition>
    cat > "$TMP/job" <<EOF
JobId=1234567 JobName=nf-STAR_ALIGN_sample1 UserId=someone(12345)
   JobState=PENDING Reason=$1 Dependency=(null)
   Partition=$3 TimeLimit=04:00:00 SubmitTime=2026-09-08T10:00:00
   ReqTRES=$2
EOF
}
ask() { TMP_JOB="$TMP/job" WHY_PENDING_SCONTROL_BIN="$TMP/scontrol" bash "$W" "$@" 2>&1; }

# --- a job that WILL start gets the ladder -----------------------------------
mkjob Resources 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(ask 1234567); rc=$?
printf '%-58s ' "Resources: exits 0"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc=$rc"; fails=$((fails+1)); }
t "Resources: still says it is waiting"        "waiting"                 "$out"
t "Resources: shows the request itself"        "cpu=8,mem=53G"           "$out"
t "Resources: names the box it lands in"       "ngs53G"                  "$out"
t "Resources: offers the box below it"         "ngs26G"                  "$out"
t "Resources: offers the whole ladder down"    "ngs13G"                  "$out"
t "Resources: and the smallest box"            "ngs7G"                   "$out"
tn "Resources: does not offer a bigger box"    "ngs92G"                  "$out"
t "Resources: says one node holds several"     "per node"                "$out"
t "Resources: refuses to pick a number"        "cannot know"             "$out"
t "Resources: names where the override lives"  "relaunch_with_override.sh" "$out"

# Priority is the same class of answer - the job starts, it is just queued.
mkjob Priority 'cpu=4,mem=26G,node=1,billing=4' ngs26G
out=$(ask 1234567)
t "Priority: gets a ladder too"                "ngs13G"                  "$out"
t "Priority: anchored on its own box"          "ngs26G"                  "$out"
tn "Priority: does not offer its own peers up" "ngs53G"                  "$out"

# The smallest box has nothing below it, and saying so beats an empty heading.
mkjob Resources 'cpu=1,mem=7G,node=1,billing=1' ngs7G
out=$(ask 1234567)
t "smallest box: says there is nothing smaller" "smallest"               "$out"

# --- a job that will NEVER start must not get one ----------------------------
# This is the whole point of the split. Shrinking a QOSMin* job makes it worse.
mkjob QOSMinCpuNotSatisfied 'cpu=1,mem=4G,node=1,billing=1' ngs13G
out=$(ask 1234567)
t "QOSMin: still says NEVER"                   "NEVER"                   "$out"
tn "QOSMin: no ladder"                         "smaller"                 "$out"
tn "QOSMin: no override pointer"               "relaunch_with_override.sh" "$out"

# --- a reason this adapter has no rule for must still say something ----------
# Measured against the live queue (2026-09-09): of 353 jobs pending across the
# cluster, 102 sat on Dependency or QOSGrpCpuLimit - reasons the case list did
# not cover, where the fallback branch printed an empty string. The job's
# fields scrolled past with no verdict under them, which reads exactly like a
# job that was examined and found fine.
mkjob Dependency 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(ask 1234567)
t  "an unruled reason still gets a verdict line" "->"                      "$out"
t  "waiting on another job says so"              "another job"             "$out"

mkjob DependencyNeverSatisfied 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(ask 1234567)
t  "a dependency that cannot be met is NEVER"    "NEVER"                   "$out"

# The account's own aggregate cap - what a pipeline fanning out 50 tasks hits,
# and the one waiting reason where the binding limit is other people's jobs.
mkjob QOSGrpCpuLimit 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(ask 1234567)
t  "a group cap is named as an account-wide one" "account"                 "$out"
t  "a group cap gets the ladder"                 "ngs26G"                  "$out"

# Whatever the reason turns out to be, the raw string has to reach the reader:
# a reason nobody has written a rule for is the one they most need to see.
mkjob SomeReasonNobodyHasSeenYet 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(ask 1234567)
t  "an unheard-of reason is quoted back"     "SomeReasonNobodyHasSeenYet"  "$out"
t  "and says plainly that there is no rule"      "no rule"                 "$out"

# --- the ladder is about ngs boxes, so it may only answer for ngs jobs -------
# Same shape as PITFALLS 18b: the answer has a subject, and nobody checked it.
# Run against a real ct224 job on the live queue, the ladder announced which
# ngs box it "lands in" and offered six more below - confident advice about a
# partition family this job is not in and whose hardware it does not share.
mkjob Resources 'cpu=112,mem=324800M,node=2,billing=112' ct224
out=$(ask 1234567)
tn "a non-ngs job is offered no box at all"      "lands in"                "$out"
t  "and is told the table does not cover it"     "box table"               "$out"

# A request no box can hold used to fall back to the largest box and present it
# as the one the job "lands in" - which is false, and is the one case where a
# wrong box number costs a whole queue wait to find out.
mkjob Resources 'cpu=112,mem=350G,node=1,billing=112' ngs372G
out=$(ask 1234567)
tn "a request no box fits is not said to land"   "lands in"                "$out"
t  "it is told that nothing here holds it"       "no box"                  "$out"

# --- the pre-existing exit codes are load-bearing and must not shift ---------
out=$(WHY_PENDING_SCONTROL_BIN="$TMP/nowhere/scontrol" bash "$W" 2>&1); rc=$?
printf '%-58s ' "no scontrol still exits 2"
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc=$rc out=<<$out>>"; fails=$((fails+1)); }

rm -f "$TMP/job"; : > "$TMP/job"
out=$(ask 9999999); rc=$?
printf '%-58s ' "unknown job still exits 1"
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc=$rc out=<<$out>>"; fails=$((fails+1)); }

cat > "$TMP/downctl" <<'STUB'
#!/bin/bash
echo "Slurmctld(primary) at lgn304 is DOWN"; exit 0
STUB
chmod +x "$TMP/downctl"
out=$(WHY_PENDING_SCONTROL_BIN="$TMP/downctl" bash "$W" 2>&1); rc=$?
printf '%-58s ' "a down controller still exits 3"
[ "$rc" = 3 ] && echo ok || { echo "FAIL: rc=$rc out=<<$out>>"; fails=$((fails+1)); }

# --- U5: layer= so the command layer measures instead of guesses ------------
# The five-layer taxonomy (docs in the 2.7 plan appendix) puts "will not
# schedule, resource shape" in the scheduler layer - every Reason this adapter
# explains is exactly that, so every verdict line gets layer=scheduler,
# regardless of which case in explain() produced it. Added to the line, not
# reshaping it: the existing human text above must still match unchanged.
mkjob Resources 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(ask 1234567)
t "Resources: verdict line still reads as before" "-> waiting - the partition is full." "$out"
t "Resources: and now carries layer=scheduler"    "layer=scheduler"                     "$out"

mkjob QOSMinCpuNotSatisfied 'cpu=1,mem=4G,node=1,billing=1' ngs13G
out=$(ask 1234567)
t "QOSMin: also carries layer=scheduler"           "layer=scheduler"                    "$out"

mkjob SomeReasonNobodyHasSeenYet 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(ask 1234567)
t "an unheard-of reason still carries layer=scheduler" "layer=scheduler"                "$out"

# The no-argument, whole-queue form prints its own verdict line per job - a
# separate print site in the script, so it needs its own check.
cat > "$TMP/squeue" <<'STUB'
#!/bin/bash
echo "1234567 Resources nf-STAR_ALIGN_sample1"
STUB
chmod +x "$TMP/squeue"
mkjob Resources 'cpu=8,mem=53G,node=1,billing=8' ngs53G
out=$(TMP_JOB="$TMP/job" WHY_PENDING_SCONTROL_BIN="$TMP/scontrol" \
      WHY_PENDING_SQUEUE_BIN="$TMP/squeue" bash "$W" 2>&1)
t "the whole-queue form also tags layer=scheduler"  "layer=scheduler"                    "$out"

# A site this adapter does not know is an environment/tooling mismatch, not a
# fact about any run's scheduling - layer=env, not layer=scheduler.
out=$(WHY_PENDING_SCONTROL_BIN="$TMP/nowhere/scontrol" bash "$W" 2>&1)
t "no scontrol at all is layer=env, not a scheduler verdict" "layer=env"                 "$out"

# The controller itself being unreachable is still a fact about the
# scheduler - a site whose slurmctld is down cannot schedule anything, which
# is exactly what the scheduler layer means here.
out=$(WHY_PENDING_SCONTROL_BIN="$TMP/downctl" bash "$W" 2>&1)
t "a down controller is layer=scheduler"            "layer=scheduler"                    "$out"

echo
# --- the box table has exactly one source of truth ---------------------------
# The numbers above are only correct because they came out of the config. A
# second copy of them anywhere is the drift this repo already checks for.
out=$(bash -c ". $ROOT/scripts/utils/boxes.sh; nchc_boxes" 2>&1)
printf '%-58s ' "boxes.sh emits the ladder smallest first"
[ "$(head -1 <<<"$out" | cut -f1)" = ngs7G ] && [ "$(tail -1 <<<"$out" | cut -f1)" = ngs372G ] \
    && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }
printf '%-58s ' "boxes.sh emits queue/cpus/mem/maxHours"
[ "$(head -1 <<<"$out")" = "$(printf 'ngs7G\t1\t7\t48')" ] \
    && echo ok || { echo "FAIL: <<$(head -1 <<<"$out")>>"; fails=$((fails+1)); }
printf '%-58s ' "why_pending.sh retypes no box numbers"
grep -qE "ngs(7|13|26|53|92|186|372)G" "$ROOT/scripts/why_pending.sh" \
    && { echo "FAIL: box names are hardcoded in the script"; fails=$((fails+1)); } || echo ok

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
