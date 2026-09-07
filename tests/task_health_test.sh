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

printf '#!/bin/bash\necho "2044345  Resources   nf-TEST_JOB_"\necho "   -> waiting - the partition is full."\nexit 0\n' \
  > "$TMP/ssh"; chmod +x "$TMP/ssh"

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

printf '#!/bin/bash\nexit 3\n' > "$TMP/tw"; chmod +x "$TMP/tw"
printf '%-58s ' "a tw failure is reported, not swallowed"
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" bash "$P" run1 2>&1); rc=$?
if [ "$rc" = 2 ] && grep -qF "ERROR" <<<"$out"; then echo ok; else echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
