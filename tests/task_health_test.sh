# The check missing from a status-only background watch: `tw runs view
# --status` reports RUNNING for the whole time one task sits unstarted.
# task_health.sh is the one-command combo (task table -> stuck pattern ->
# why_pending.sh) a Monitor loop can poll instead of only the aggregate
# status. This fakes both `tw` and `ssh` so it runs with no real workspace or
# site.
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/task_health.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
settings 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' "tw_bin: $TMP/tw"
: > "$TMP/.seqera_token"

printf '#!/bin/bash\ncat "$TW_FAKE_OUTPUT_FILE"\n' > "$TMP/tw"; chmod +x "$TMP/tw"

cat > "$TMP/tasks_running.txt" <<'EOF'
  Pipeline's run X tasks:

     task_id | process | tag | status
    ---------+---------+-----+-----------
     1       | A       | t   | COMPLETED
     2       | B       | t   | RUNNING
EOF

cat > "$TMP/tasks_stuck.txt" <<'EOF'
  Pipeline's run X tasks:

     task_id | process | tag | status
    ---------+---------+-----+-----------
     1       | A       | t   | COMPLETED
     2       | B       | t   | SUBMITTED
EOF

# why_pending's no-argument form lists every pending job on the account, and
# this account is shared by every lab member (measured: a second Seqera user is
# active in the same workspace). So the stub has to answer the question
# task_health actually asks - "is one of THESE jobs stuck" - and a job matching
# nothing in the run is the case that used to pass. Nextflow names a task's job
# nf-<process, ':' replaced by '_'>_<tag>; measured on this site, process
# NFCORE_AMPLISEQ:AMPLISEQ:BARRNAP became nf-NFCORE_AMPLISEQ_AMPLISEQ_BARRNAP__.
mkssh() { { echo '#!/bin/bash'; printf '%s\n' "$@"; echo 'exit 0'; } > "$TMP/ssh"; chmod +x "$TMP/ssh"; }
mkssh 'echo "2044345  Resources   nf-B_sample1"' \
      'echo "   -> waiting - the partition is full."'

run() {
  LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" TW_FAKE_OUTPUT_FILE="$1" \
  bash "$P" "${2:-run1}" 2>&1
}
t() { # t <label> <expect-rc> <expect-substring> <tasks-file>
  local label="$1" want_rc="$2" want="$3" tasks_file="$4"
  printf '%-58s ' "$label"
  local out rc; out=$(run "$tasks_file"); rc=$?
  if [ "$rc" != "$want_rc" ]; then echo "FAIL: rc $rc wanted $want_rc <<$out>>"; fails=$((fails+1)); return; fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then echo "FAIL: lacks '$want' <<$out>>"; fails=$((fails+1)); return; fi
  echo ok
}

t "a task actually running reads as OK"          0 "OK: 1 running" "$TMP/tasks_running.txt"
t "nothing running while one queues escalates"   0 "STUCK:"        "$TMP/tasks_stuck.txt"
t "the escalation carries why_pending's reason"  0 "partition is full" "$TMP/tasks_stuck.txt"
t "and names the job it is a reason about"       0 "2044345"           "$TMP/tasks_stuck.txt"

# U5: layer=<value> so runs.md's report format measures the layer instead of
# an LLM guessing it from the prose. A run's own job actually found stuck on
# the scheduler is layer=scheduler; an OK line reports nothing wrong, so it
# must carry no layer at all.
out=$(run "$TMP/tasks_stuck.txt")
printf '%-58s ' "this run's own stuck job is layer=scheduler"
grep -qF "layer=scheduler" <<<"$out" && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

out=$(run "$TMP/tasks_running.txt")
printf '%-58s ' "an OK line carries no layer at all"
grep -qF "layer=" <<<"$out" && { echo "FAIL: <<$out>>"; fails=$((fails+1)); } || echo ok

# The PITFALLS 18b case. A pending job on a shared account is not evidence
# about this run unless its name says so; reporting one anyway attributes
# another member's queue position to a run it has nothing to do with, and does
# it in the single line a background watch is built to trust.
mkssh 'echo "9999999  Resources   nf-SOMEONE_ELSES_PIPELINE_STEP"' \
      'echo "   -> waiting - the partition is full."'
printf '%-58s ' "another member's queued job is not this run's reason"
out=$(run "$TMP/tasks_stuck.txt")
if grep -qF "partition is full" <<<"$out"; then
  echo "FAIL: reported a foreign job's reason  <<$out>>"; fails=$((fails+1))
elif grep -qF "9999999" <<<"$out"; then
  echo "FAIL: named a foreign job  <<$out>>"; fails=$((fails+1))
elif ! grep -qF "STUCK" <<<"$out"; then
  echo "FAIL: stopped saying it is stuck  <<$out>>"; fails=$((fails+1))
else echo ok; fi

printf '%-58s ' "and says why it cannot attribute one"
if grep -qiE "shared|none of|no pending job" <<<"$out"; then echo ok
else echo "FAIL: <<$out>>"; fails=$((fails+1)); fi

# No evidence this run's job is on the scheduler at all is not a fact about
# the scheduler - it is a gap in what this side can observe (has it even been
# submitted?), which is the env layer (agent, settings, connectivity).
printf '%-58s ' "and that unattributed case is layer=env, not layer=scheduler"
if grep -qF "layer=env" <<<"$out" && ! grep -qF "layer=scheduler" <<<"$out"; then echo ok
else echo "FAIL: <<$out>>"; fails=$((fails+1)); fi

mkssh 'echo "2044345  Resources   nf-B_sample1"' \
      'echo "   -> waiting - the partition is full."'

printf '#!/bin/bash\nexit 3\n' > "$TMP/tw"; chmod +x "$TMP/tw"
printf '%-58s ' "a tw failure is reported, not swallowed"
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" bash "$P" run1 2>&1); rc=$?
if [ "$rc" = 2 ] && grep -qF "ERROR" <<<"$out"; then echo ok; else echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); fi
# This is a usage/settings error of the health check itself, documented in the
# script's own header as "nothing about the run" - it must not claim a layer.
printf '%-58s ' "and a tw failure carries no layer (it is not a run diagnosis)"
grep -qF "layer=" <<<"$out" && { echo "FAIL: <<$out>>"; fails=$((fails+1)); } || echo ok

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
