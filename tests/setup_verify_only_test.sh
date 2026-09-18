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
    env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
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
FULLHOME="$TMP/full_home"; mkdir -p "$FULLHOME/.config/agentic-bioflow"
cat > "$FULLHOME/.config/agentic-bioflow/env.yaml" <<'YAML'
reach: ssh
site_host: me@example.org
seqera_user: alice
workspace_id: 999
compute_env: ce-a-person
storage_root: /nowhere/runs
agent_connection: conn-alice
YAML
chmod 600 "$FULLHOME/.config/agentic-bioflow/env.yaml"

echo 0 > "$PF_RC_FILE"
out=$(clean HOME="$FULLHOME" XDG_CONFIG_HOME="$FULLHOME/.config" -- bash "$V" 2>&1); rc=$?
t "settings complete + preflight green: exits 0"  "$rc"  "0"
has "...says this machine is already set up"  "already set up" "$out"
has "...says setup does not need to run again"  "No need to run setup again" "$out"
has "...still shows preflight's own OK lines (not hidden)"  "compute-env" "$out"

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
