#!/bin/bash
# T27: "setup once is enough". :setup runs scripts/setup_verify.sh before
# treating a machine as needing repair or first-run at all, so a fully
# configured machine hears that in seconds rather than being walked into the
# repair flow's own checks. This fakes preflight.sh (no ssh, no network, no
# real site) the same way tests/status_test.sh already does, and asserts
# setup_verify.sh only formats and decides - never re-implements a check.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()      { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }

FAKE="$TMP/fake_scripts"; mkdir -p "$FAKE/utils"
cp "$ROOT"/scripts/*.sh "$FAKE"/ 2>/dev/null
cp "$ROOT"/scripts/utils/*.sh "$FAKE/utils/" 2>/dev/null
V="$FAKE/setup_verify.sh"

PF_RC_FILE="$TMP/pf_rc"
cat > "$FAKE/preflight.sh" <<EOF
#!/bin/bash
rc=\$(cat "$PF_RC_FILE" 2>/dev/null || echo 0)
if [ "\$rc" = 0 ]; then
  printf 'OK         reach          ssh me@example.org - the master connection is up\n'
  printf 'OK         compute-env    ce-a-person AVAILABLE\n'
else
  printf 'OK         reach          ssh me@example.org - the master connection is up\n'
  printf 'FAIL       agent          not running - Platform will show no outputs (fix it)\n'
fi
exit "\$rc"
EOF
chmod +x "$FAKE/preflight.sh"

clean() { # clean <env assignments...> -- <args...>
    local envs=()
    while [ "$1" != -- ]; do envs+=("$1"); shift; done; shift
    # XDG_CONFIG_HOME too: T30's root pointer lives under it, and a CI runner
    # sets it globally. Left in place, every fixture in this file shares ONE
    # pointer file whatever HOME it was given, so a root one case `--use`s
    # leaks into the next. It did, on GitHub Actions - and was invisible
    # locally, where the variable happened to be unset.
    env -u XDG_CONFIG_HOME -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
        -u AGENTIC_BIOFLOW_STATE_DIR -u AGENTIC_BIOFLOW_REPORTS_DIR \
        "${envs[@]}" "$@"
}

# ---------------------------------------------------------------------------
# No settings file anywhere: refused fast, and named as a first run - not
# sent through preflight (which, on a genuinely fresh machine, would throw on
# an empty compute-env name rather than reporting cleanly).
NOHOME="$TMP/no_settings_home"; mkdir -p "$NOHOME"
echo 0 > "$PF_RC_FILE"
out=$(clean HOME="$NOHOME" XDG_CONFIG_HOME="$NOHOME/.config" -- bash "$V" 2>&1); rc=$?
t "no settings file at all: exits non-zero"  "$rc"  "1"
has "...says this is a first run"  "first run" "$out"
hasnot "...never claims to be already set up"  "already set up" "$out"

# ---------------------------------------------------------------------------
# Settings exist, complete, and preflight is fully green: the fast path this
# card exists for. Under a second, and it must NOT walk into repair's own
# checks (this fake preflight.sh, called once, is the only check that ran).
FULLHOME="$TMP/full_home"; mkdir -p "$FULLHOME"
FULLROOT="$TMP/full_root"
clean HOME="$FULLHOME" -- bash "$(dirname "$V")/settings.sh" --use "$FULLROOT" >/dev/null 2>&1
cat > "$FULLROOT/config/env.yaml" <<'YAML'
reach: ssh
site_host: me@example.org
seqera_user: alice
workspace_id: 999
compute_env: ce-a-person
storage_root: /nowhere/runs
agent_connection: conn-alice
YAML
chmod 600 "$FULLROOT/config/env.yaml"

# Feature 004: green preflight is no longer enough. "Already set up" also needs
# this machine's own proof record (proof_run in config/machines/<machine>.yaml,
# written by scripts/setup_proof.sh --record from a run Platform confirmed).
# TC-002: no record -> exit 3, and never the "already set up" claim.
echo 0 > "$PF_RC_FILE"
out=$(clean HOME="$FULLHOME" XDG_CONFIG_HOME="$FULLHOME/.config" -- bash "$V" 2>&1); rc=$?
t "TC-002 preflight green but no proof record: exits 3"  "$rc"  "3"
hasnot "...never claims to be already set up"  "already set up" "$out"
has "...says the proof on public test data is missing"  "public test data" "$out"
has "...points at setup step 8"  "step 8" "$out"

# TC-003: another machine's proof does not count for this one.
mkdir -p "$FULLROOT/config/machines"
echo "proof_run: run-elsewhere 2026-10-01 nf-core/demo" > "$FULLROOT/config/machines/some-other-box-Linux.yaml"
out=$(clean HOME="$FULLHOME" XDG_CONFIG_HOME="$FULLHOME/.config" -- bash "$V" 2>&1); rc=$?
t "TC-003 only ANOTHER machine has a record: exits 3"  "$rc"  "3"
hasnot "...never claims to be already set up"  "already set up" "$out"

# A record in the shared env.yaml is not a per-machine proof either: it would
# travel with the root to a machine that never proved anything.
echo "proof_run: run-shared 2026-10-01 nf-core/demo" >> "$FULLROOT/config/env.yaml"
out=$(clean HOME="$FULLHOME" XDG_CONFIG_HOME="$FULLHOME/.config" -- bash "$V" 2>&1); rc=$?
t "proof_run in shared env.yaml only: still exits 3"  "$rc"  "3"
grep -v '^proof_run' "$FULLROOT/config/env.yaml" > "$FULLROOT/config/env.yaml.new" \
    && mv "$FULLROOT/config/env.yaml.new" "$FULLROOT/config/env.yaml" && chmod 600 "$FULLROOT/config/env.yaml"

# TC-001: this machine's own record.
MACHID=$(clean HOME="$FULLHOME" -- bash -c ". '$FAKE/settings.sh' >/dev/null 2>&1; machine_id")
echo "proof_run: run-mine 2026-10-02 nf-core/demo" > "$FULLROOT/config/machines/$MACHID.yaml"
out=$(clean HOME="$FULLHOME" XDG_CONFIG_HOME="$FULLHOME/.config" -- bash "$V" 2>&1); rc=$?
t "TC-001 settings complete + preflight green + proof: exits 0"  "$rc"  "0"
has "...says this machine is already set up"  "already set up" "$out"
has "...says setup does not need to run again"  "No need to run setup again" "$out"
has "...still shows preflight's own OK lines (not hidden)"  "compute-env" "$out"
has "...shows the proving run id"  "run-mine" "$out"
has "...shows the proving date"  "2026-10-02" "$out"

# ---------------------------------------------------------------------------
# Settings exist but preflight FAILs on something: falls through to repair,
# not the "already set up" fast path - and names what preflight found.
echo 1 > "$PF_RC_FILE"
out=$(clean HOME="$FULLHOME" XDG_CONFIG_HOME="$FULLHOME/.config" -- bash "$V" 2>&1); rc=$?
t "settings exist but preflight FAILs: exits non-zero"  "$rc"  "1"
hasnot "...never claims to be already set up"  "already set up" "$out"
has "...says it is continuing into repair"  "repair" "$out"
has "...surfaces preflight's own FAIL line"  "FAIL" "$out"
has "...names what specifically failed"  "agent" "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
