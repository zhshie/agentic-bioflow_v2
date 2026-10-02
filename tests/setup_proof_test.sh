#!/bin/bash
# Feature 004 (specs/004-onboarding-proof): a machine counts as set up only
# once it has proven the environment on public test data, and that proof is
# written only from a run Platform itself confirms. scripts/setup_proof.sh
# --record <run-id> asks Platform (`tw -o json runs list`), --check reads the
# record back. The record is per machine: it lives in
# config/machines/<machine>.yaml, never in the shared config/env.yaml.
# Fakes `tw`; no network, no site (same shape as tests/runs_board_test.sh).
# Covers TC-004..TC-009 and TC-011.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROOF="$ROOT/scripts/setup_proof.sh"
SETTINGS="$ROOT/scripts/settings.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()      { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }

# The fake tw answers `tw -o json runs list` from $RUNS_LIST_FILE, or fails
# when $TW_FAIL is set. Nothing else is ever asked of it.
cat > "$TMP/tw" <<'EOF'
#!/bin/bash
[ -n "${TW_FAIL:-}" ] && { echo "tw: simulated outage" >&2; exit 1; }
[ -n "${TW_WARN:-}" ] && echo "WARNING: a newer version of tw is available" >&2
case "$*" in
    *"runs list"*) cat "$RUNS_LIST_FILE"; if [ -n "${TW_FAIL_AFTER:-}" ]; then exit 1; fi ;;
    *) exit 1 ;;
esac
EOF
chmod +x "$TMP/tw"

HOMEDIR="$TMP/home"; mkdir -p "$HOMEDIR"
RROOT="$TMP/root"
clean() {
    env -u XDG_CONFIG_HOME -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
        -u AGENTIC_BIOFLOW_STATE_DIR -u AGENTIC_BIOFLOW_REPORTS_DIR -u TOWER_ACCESS_TOKEN \
        HOME="$HOMEDIR" XDG_CONFIG_HOME="$HOMEDIR/.config" "$@"
}
clean bash "$SETTINGS" --use "$RROOT" >/dev/null 2>&1
cat > "$RROOT/config/env.yaml" <<YAML
reach: ssh
site_host: me@example.org
seqera_user: alice
workspace_id: 999
compute_env: ce-a-person
storage_root: /nowhere/runs
agent_connection: conn-alice
tw_bin: $TMP/tw
YAML
chmod 600 "$RROOT/config/env.yaml"
: > "$RROOT/config/.seqera_token"

ENVYAML="$RROOT/config/env.yaml"
# This machine's own settings file, whatever machine_id() calls it here.
machfile() { clean bash -c ". '$SETTINGS' >/dev/null 2>&1; printf '%s\n' \"\$MACHINE_SETTINGS_FILE\""; }
MACH="$(machfile)"
t "fixture: this machine has a machines/ file path"  "$([ -n "$MACH" ] && echo yes || echo no)"  "yes"

NOW_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
runs() { # runs <id> <status> <project> <user> [submit, default now]
    printf '{"workflows":[{"workflow":{"id":"%s","runName":"x","projectName":"%s","status":"%s","userName":"%s","submit":"%s"}},{"workflow":{"id":"other-run","runName":"y","projectName":"nf-core/rnaseq","status":"SUCCEEDED","userName":"alice","submit":"%s"}}]}\n' "$1" "$3" "$2" "$4" "${5:-$NOW_ISO}" "$NOW_ISO" > "$TMP/runs.json"
}
rec()   { clean RUNS_LIST_FILE="$TMP/runs.json" bash "$PROOF" --record "$@" 2>&1; }
check() { clean bash "$PROOF" --check 2>&1; }
recorded() { # does the machines file / env.yaml mention proof_run
    [ -r "$1" ] || { echo 0; return; }
    grep -c '^[[:space:]]*proof_run[[:space:]]*:' "$1" || true
}

# --- nothing recorded yet ----------------------------------------------------
out=$(check); rc=$?
t "--check with no record: exits 1"  "$rc"  "1"
has "...says it is not proven"  "not proven" "$out"
has "...points at setup step 8"  "step 8" "$out"

# --- TC-005: not SUCCEEDED ---------------------------------------------------
for st in FAILED RUNNING CANCELLED; do
    runs run-ok "$st" nf-core/demo alice
    out=$(rec run-ok); rc=$?
    t "TC-005 $st: --record exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
    has "TC-005 $st: names the status"  "$st" "$out"
    t "TC-005 $st: nothing written to the machines file"  "$(recorded "$MACH")"  "0"
done

# --- TC-006: wrong pipeline --------------------------------------------------
runs run-ok SUCCEEDED nextflow-io/hello alice
out=$(rec run-ok); rc=$?
t "TC-006 hello run: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
has "TC-006 ...says nf-core/demo is what is wanted"  "nf-core/demo" "$out"
t "TC-006 ...nothing written"  "$(recorded "$MACH")"  "0"

# --- TC-007: someone else's run ---------------------------------------------
runs run-ok SUCCEEDED nf-core/demo bob
out=$(rec run-ok); rc=$?
t "TC-007 other user's run: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
has "TC-007 ...names the other submitter"  "bob" "$out"
t "TC-007 ...nothing written"  "$(recorded "$MACH")"  "0"

# --- TC-008: no such run -----------------------------------------------------
runs run-ok SUCCEEDED nf-core/demo alice
out=$(rec no-such-run); rc=$?
t "TC-008 unknown run id: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
has "TC-008 ...says it was not found"  "not found" "$out"
t "TC-008 ...nothing written"  "$(recorded "$MACH")"  "0"

# --- TC-009: Platform cannot be asked / answers garbage ----------------------
out=$(clean TW_FAIL=1 RUNS_LIST_FILE="$TMP/runs.json" bash "$PROOF" --record run-ok 2>&1); rc=$?
t "TC-009 tw fails: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
has "TC-009 ...says it could not confirm"  "could not confirm" "$out"
t "TC-009 ...nothing written"  "$(recorded "$MACH")"  "0"
echo 'this is not json' > "$TMP/garbage.json"
out=$(clean RUNS_LIST_FILE="$TMP/garbage.json" bash "$PROOF" --record run-ok 2>&1); rc=$?
t "TC-009 garbage JSON: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
has "TC-009 ...says it could not confirm"  "could not confirm" "$out"
t "TC-009 ...nothing written"  "$(recorded "$MACH")"  "0"
t "TC-009 after all refusals --check still exits 1"  "$(check >/dev/null; echo $?)"  "1"

# --- acceptance MED-1: an old run, or one already proving another machine ----
runs run-old SUCCEEDED nf-core/demo alice 2020-01-01T00:00:00Z
out=$(rec run-old); rc=$?
t "old run (2020): exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
has "...says the run is older than 7 days"  "older than 7 days" "$out"
t "...nothing written"  "$(recorded "$MACH")"  "0"
OTHER="$(dirname "$MACH")/some-other-box-Linux.yaml"
mkdir -p "$(dirname "$MACH")"; echo "proof_run: run-taken 2026-01-01 nf-core/demo" > "$OTHER"
runs run-taken SUCCEEDED nf-core/demo alice
out=$(rec run-taken); rc=$?
t "run already proving another machine: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
has "...names the other machine"  "some-other-box-Linux" "$out"
t "...nothing written"  "$(recorded "$MACH")"  "0"
rm -f "$OTHER"

# --- acceptance LOW: look-alike pipelines are not nf-core/demo ---------------
for proj in nf-core/demo-fork evil/nf-core/demo https://gitlab.com/evil/nf-core/demo; do
    runs run-ok SUCCEEDED "$proj" alice
    out=$(rec run-ok); rc=$?
    t "look-alike '$proj': exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
    t "look-alike '$proj': nothing written"  "$(recorded "$MACH")"  "0"
done

# --- acceptance LOW: tw exits 1 even though it printed valid JSON ------------
runs run-ok SUCCEEDED nf-core/demo alice
out=$(clean TW_FAIL_AFTER=1 RUNS_LIST_FILE="$TMP/runs.json" bash "$PROOF" --record run-ok 2>&1); rc=$?
t "tw exit 1 with valid JSON: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
t "...nothing written"  "$(recorded "$MACH")"  "0"

# --- acceptance LOW: a null field must not shift the others ------------------
printf '{"workflows":[{"workflow":{"id":"run-null","runName":"x","projectName":"nf-core/demo","status":null,"userName":"alice","submit":"%s"}}]}
' "$NOW_ISO" > "$TMP/runs.json"
out=$(rec run-null); rc=$?
t "null status: exits non-zero"  "$([ "$rc" != 0 ] && echo yes)"  "yes"
hasnot "...does not report the project as the status"  "has status nf-core/demo" "$out"

# --- TC-004: the qualifying run ---------------------------------------------
runs run-ok SUCCEEDED nf-core/demo alice
out=$(rec run-ok); rc=$?
t "TC-004 qualifying run: exits 0"  "$rc"  "0"
has "TC-004 ...prints the run id"  "run-ok" "$out"
has "TC-004 ...prints the run's own date"  "$(date -u +%Y-%m-%d)" "$out"
t "TC-004 record is in the machines file"  "$(recorded "$MACH")"  "1"
t "TC-004 record is NOT in env.yaml"  "$(recorded "$ENVYAML")"  "0"
out=$(check); rc=$?
t "TC-004 --check now exits 0"  "$rc"  "0"
has "TC-004 ...--check says proven on this machine"  "proven on this machine" "$out"
has "TC-004 ...--check shows the run id"  "run-ok" "$out"

# A URL-form project name (a run launched from a git URL) still qualifies.
runs run-url SUCCEEDED https://github.com/nf-core/demo alice
out=$(rec run-url); rc=$?
t "URL-form projectName ending /nf-core/demo: exits 0"  "$rc"  "0"
t "...still exactly one proof_run line (rewritten in place)"  "$(recorded "$MACH")"  "1"
has "...the newer run id replaced the old one"  "run-url" "$(check)"

# A CLI warning on stderr does not spoil an otherwise good answer.
runs run-warn SUCCEEDED nf-core/demo alice
out=$(clean TW_WARN=1 RUNS_LIST_FILE="$TMP/runs.json" bash "$PROOF" --record run-warn 2>&1); rc=$?
t "tw warning on stderr + good JSON: exits 0"  "$rc"  "0"
runs run-git SUCCEEDED https://github.com/nf-core/demo.git alice
out=$(rec run-git); rc=$?
t "projectName https://github.com/nf-core/demo.git: exits 0"  "$rc"  "0"

# --- TC-011: usage errors ----------------------------------------------------
for args in "" "--bogus" "--record"; do
    out=$(clean bash "$PROOF" $args 2>&1); rc=$?
    t "TC-011 args '$args': exits 2"  "$rc"  "2"
    has "TC-011 args '$args': prints usage"  "usage" "$out"
done

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
