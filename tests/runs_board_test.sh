#!/bin/bash
# T24: `/runs` with nothing named becomes a work board
# (scripts/runs_board.sh), whose own site-side check
# (scripts/runs_board_site_probe.sh) must cost exactly ONE on_site.sh round
# trip no matter how many runs are on the board - PITFALLS.md 16e's session
# cap. This fakes `tw` and `ssh` so it runs with no real workspace, no
# network and no site (same shape as tests/task_health_test.sh).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOARD="$ROOT/scripts/runs_board.sh"
PROBE="$ROOT/scripts/runs_board_site_probe.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()    { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
settings 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' \
         'seqera_user: alice' "tw_bin: $TMP/tw" 'ssh_max_parallel: 4' 'language: en'
: > "$TMP/.seqera_token"

# --- the tw stub: two shapes the board asks for -----------------------------
#   tw -o json runs list --workspace <ws>          -> $RUNS_LIST_FILE
#   tw runs view -i <id> --workspace <ws> --params  -> $PARAMS_DIR/<id>.txt
#   tw -o json runs view -i <id> --workspace <ws> tasks -> $TASKS_DIR/<id>.txt
mkdir -p "$TMP/params" "$TMP/tasks"
cat > "$TMP/tw" <<'EOF'
#!/bin/bash
args="$*"
case "$args" in
    *"runs list"*)
        cat "$RUNS_LIST_FILE" ;;
    *"tasks")
        id=""; prev=""
        for a in "$@"; do [ "$prev" = "-i" ] && id="$a"; prev="$a"; done
        f="$TASKS_DIR/$id.txt"
        [ -r "$f" ] && cat "$f" || echo '[]'
        ;;
    *"--params"*)
        id=""; prev=""
        for a in "$@"; do [ "$prev" = "-i" ] && id="$a"; prev="$a"; done
        f="$PARAMS_DIR/$id.txt"
        [ -r "$f" ] && cat "$f"
        ;;
    *) exit 1 ;;
esac
EOF
chmod +x "$TMP/tw"

# Two active runs for alice, one succeeded (must be excluded), one active run
# belonging to bob on the same shared workspace (must also be excluded).
cat > "$TMP/runs_2.json" <<'EOF'
{"workflows":[
  {"workflow":{"id":"r-alpha","runName":"tiny_hedgehog","projectName":"nf-core/rnaseq","status":"RUNNING","userName":"alice","submit":0}},
  {"workflow":{"id":"r-beta","runName":"cool_darwin","projectName":"nf-core/ampliseq","status":"SUBMITTED","userName":"alice","submit":0}},
  {"workflow":{"id":"r-gamma","runName":"old_one","projectName":"nf-core/rnaseq","status":"SUCCEEDED","userName":"alice","submit":0}},
  {"workflow":{"id":"r-delta","runName":"bobs_run","projectName":"nf-core/sarek","status":"RUNNING","userName":"bob","submit":0}}
]}
EOF

cat > "$TMP/params/r-alpha.txt" <<'EOF'
outdir: /lab/alice/projects/proj_a/runs/rnaseq_x_20260101/results
input: https://tower.example/datasets/1/n/proj_a_sheet
EOF
cat > "$TMP/params/r-beta.txt" <<'EOF'
outdir: /lab/alice/projects/proj_b/runs/ampliseq_y_20260102/results
input: https://tower.example/datasets/2/n/proj_b_sheet
EOF

echo '[]' > "$TMP/tasks/r-alpha.txt"
echo '[]' > "$TMP/tasks/r-beta.txt"

# ssh stub for on_site.sh's ssh mode - not used when --no-site-check is
# given, and counted (below) when it is.
CALL_LOG="$TMP/ssh_calls.log"
: > "$CALL_LOG"
cat > "$TMP/ssh" <<EOF
#!/bin/bash
echo "call" >> "$CALL_LOG"
if [[ "\$*" == *"-O check"* ]]; then exit 0; fi
echo "nothing pending for alice"
exit 0
EOF
chmod +x "$TMP/ssh"

run_board() {
    : > "$CALL_LOG"
    LAB_SETTINGS_FILE="$TMP/env.yaml" RUNS_LIST_FILE="$TMP/runs_2.json" \
    PARAMS_DIR="$TMP/params" TASKS_DIR="$TMP/tasks" \
    ON_SITE_SSH_BIN="$TMP/ssh" \
    bash "$BOARD" "$@" 2>&1
}

echo "== the board itself =="
out=$(run_board --no-site-check)

has "shows alice's RUNNING run, by name"            "tiny_hedgehog" "$out"
hasnot "never prints the run's raw Platform id"     "r-alpha" "$out"
has "shows alice's SUBMITTED run"                   "cool_darwin" "$out"
hasnot "excludes the SUCCEEDED run"                 "old_one" "$out"
hasnot "excludes another member's run"              "bobs_run" "$out"
has "shows the pipeline name"                       "nf-core/rnaseq" "$out"
has "shows the project, read from the run's outdir" "proj_a" "$out"
has "shows the second run's project too"            "proj_b" "$out"

printf '%-64s ' "assigns exactly two codes, r1 and r2"
codes=$(grep -oE '^r[0-9]+' <<<"$out" | sort -u)
[ "$codes" = "$(printf 'r1\nr2')" ] && echo ok || { echo "FAIL: got '$codes'"; fails=$((fails+1)); }

echo
echo "== --resolve turns a code back into a run id =="
r1=$(run_board --no-site-check --resolve r1)
r2=$(run_board --no-site-check --resolve r2)
t "r1 resolves to r-alpha" "$r1" "r-alpha"
t "r2 resolves to r-beta"  "$r2" "r-beta"

printf '%-64s ' "an unknown code resolves to nothing and fails"
LAB_SETTINGS_FILE="$TMP/env.yaml" RUNS_LIST_FILE="$TMP/runs_2.json" \
PARAMS_DIR="$TMP/params" TASKS_DIR="$TMP/tasks" \
bash "$BOARD" --no-site-check --resolve r99 >/dev/null 2>&1
rc=$?
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc $rc"; fails=$((fails+1)); }

echo
echo "== the site-side check costs exactly one round trip for both runs ====="
out=$(run_board)
calls=$(wc -l < "$CALL_LOG")
printf '%-64s ' "on_site.sh (ssh) is called exactly once for a 2-run board"
[ "$calls" -le 2 ] && echo "ok ($calls calls: one -O check, one session)" \
    || { echo "FAIL: $calls calls logged, expected at most 2 (one check + one session)"; fails=$((fails+1)); }

echo
echo "== the site probe script directly (unit-level) ========================"
run_probe() {
    : > "$CALL_LOG"
    PARAMS_DIR="$TMP/params" TASKS_DIR="$TMP/tasks" ON_SITE_SSH_BIN="$TMP/ssh" \
    LAB_SETTINGS_FILE="$TMP/env.yaml" RUNS_LIST_FILE="$TMP/runs_2.json" \
    bash "$PROBE" "$@" 2>&1
}

out=$(run_probe 1 r-alpha r-beta)
has "reports OK for a run with no pending tasks" "r-alpha OK" "$out"
has "reports OK for the second run too"          "r-beta OK" "$out"

printf '%-64s ' "one call to on_site.sh covers BOTH run ids"
calls=$(wc -l < "$CALL_LOG")
[ "$calls" -le 2 ] && echo "ok ($calls calls)" \
    || { echo "FAIL: $calls calls logged for 2 run ids - one round trip was supposed to cover all of them"; fails=$((fails+1)); }

# A run whose own task is queued with nothing running, and the site names
# exactly its process - task_health.sh's own attribution rule (PITFALLS 18b),
# reused here at board scale.
cat > "$TMP/tasks/r-alpha.txt" <<'EOF'
[{"taskId": 1, "process": "NFCORE_RNASEQ:RNASEQ:FASTQC", "tag": "s1", "status": "SUBMITTED"}]
EOF
cat > "$TMP/ssh" <<EOF
#!/bin/bash
echo "call" >> "$CALL_LOG"
if [[ "\$*" == *"-O check"* ]]; then exit 0; fi
echo "2044345  Resources   nf-NFCORE_RNASEQ_RNASEQ_FASTQC__s1"
echo "   -> waiting - the partition is full."
exit 0
EOF
chmod +x "$TMP/ssh"

out=$(run_probe 1 r-alpha r-beta)
has "flags the run whose own process the site names as stuck" "r-alpha STUCK" "$out"
has "still reports OK for the unaffected run"                  "r-beta OK" "$out"
has "carries why_pending's own reason"                          "partition is full" "$out"
has "carries layer=scheduler"                                   "layer=scheduler" "$out"

echo
echo "== a stuck run surfaces through the board itself, not just the probe =="
out=$(run_board)
has "board carries the stuck code, mapped from the id"  "r1 (r-alpha)" "$out"
has "board carries the reason too"                       "partition is full" "$out"
hasnot "board says nothing extra about the healthy run"  "r2 (r-beta)" "$out"

echo
echo "== guardrail 2: warns as the board's own count nears ssh_max_parallel =="
cat > "$TMP/runs_3.json" <<'EOF'
{"workflows":[
  {"workflow":{"id":"r-alpha","runName":"tiny_hedgehog","projectName":"nf-core/rnaseq","status":"RUNNING","userName":"alice","submit":0}},
  {"workflow":{"id":"r-beta","runName":"cool_darwin","projectName":"nf-core/ampliseq","status":"SUBMITTED","userName":"alice","submit":0}},
  {"workflow":{"id":"r-eps","runName":"third_run","projectName":"nf-core/sarek","status":"RUNNING","userName":"alice","submit":0}}
]}
EOF
cat > "$TMP/params/r-eps.txt" <<'EOF'
outdir: /lab/alice/projects/proj_c/runs/sarek_z_20260103/results
input: https://tower.example/datasets/3/n/proj_c_sheet
EOF
echo '[]' > "$TMP/tasks/r-eps.txt"

run_board3() {
    : > "$CALL_LOG"
    LAB_SETTINGS_FILE="$TMP/env.yaml" RUNS_LIST_FILE="$TMP/runs_3.json" \
    PARAMS_DIR="$TMP/params" TASKS_DIR="$TMP/tasks" \
    bash "$BOARD" --no-site-check "$@" 2>&1
}
out3=$(run_board3)
has "3 active runs against the default cap (4) triggers the warning" "ssh_max_parallel" "$out3"
has "names the configured max"                                        "4" "$out3"

out2=$(run_board --no-site-check)
hasnot "2 active runs does not trigger it" "ssh_max_parallel" "$out2"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
