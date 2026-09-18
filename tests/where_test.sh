#!/bin/bash
# T22: scripts/where.sh is purely read-only, so this test never checks that
# anything got created - only that the paths it reports are the right ones,
# under fake settings, with no real settings file and no network.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/where.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok \
           || { echo "FAIL: nothing matching '$2'"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" \
           && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }
t()      { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok \
           || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

# Every invocation below isolates HOME/XDG/LAB_* the same way
# tests/settings_test.sh's clean() does, so an ambient real deployment on the
# machine running this test can never leak into what should be a fixture.
clean() { # clean <env assignments...> -- <args...>
    local envs=()
    while [ "$1" != -- ]; do envs+=("$1"); shift; done; shift
    env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
        -u AGENTIC_BIOFLOW_STATE_DIR -u AGENTIC_BIOFLOW_REPORTS_DIR \
        "${envs[@]}" "$@"
}

# ---------------------------------------------------------------------------
# reach: none/ssh candidate - no LAB_RUNS_DIR at all, nothing on disk.
HOME1="$TMP/home1"; mkdir -p "$HOME1"
out=$(clean HOME="$HOME1" XDG_CONFIG_HOME="$HOME1/.config" -- bash "$S")
has "reach: ssh candidate names the XDG default"   "$HOME1/.config/agentic-bioflow/env.yaml" "$out"
has "reach: none uses the same file as ssh"        "reach: none" "$out"
has "reach: local has no candidate with no LAB_RUNS_DIR" "no candidate here" "$out"
has "a missing settings file is marked missing"    "[missing]" "$out"
has "and 'in use' says none was found"             "in use: none found" "$out"
has "the token is reported not found"              "not found" "$out"
has "the reports queue is reported missing"        "[missing]" "$out"

# ---------------------------------------------------------------------------
# reach: local - LAB_RUNS_DIR set and the file actually exists there.
RUNS="$TMP/site_runs"; mkdir -p "$RUNS/_personal"
printf 'seqera_user: alice\nlocal_root: %s/local\nreach: local\n' "$TMP" \
    > "$RUNS/_personal/env.yaml"
chmod 600 "$RUNS/_personal/env.yaml"
HOME2="$TMP/home2"; mkdir -p "$HOME2"
out=$(clean HOME="$HOME2" XDG_CONFIG_HOME="$HOME2/.config" LAB_RUNS_DIR="$RUNS" -- bash "$S")
has "reach: local candidate is under LAB_RUNS_DIR/_personal" \
    "$RUNS/_personal/env.yaml" "$out"
has "and it is marked exists"                      "[exists]" "$out"
has "'in use' names the file actually read"        "in use: $RUNS/_personal/env.yaml" "$out"
has "local_root is read from the settings file"    "$TMP/local" "$out"
hasnot "storage_root under reach:local is not deferred to the site" \
    "not checked from here" "$out"

# ---------------------------------------------------------------------------
# reach: ssh - storage_root is a site-side path and must NOT be existence
# checked from this machine (no ssh, no network - that is inspect_sides.sh's
# job, at the cost of the round trip this script deliberately avoids).
XDG3="$TMP/home3/.config"; mkdir -p "$XDG3/agentic-bioflow"
cat > "$XDG3/agentic-bioflow/env.yaml" <<YAML
reach: ssh
seqera_user: bob
storage_root: /nowhere/on/the/site
site_host: bob@example.org
ssh_control_path: ~/.ssh/cm-%r-%h-%p
YAML
chmod 600 "$XDG3/agentic-bioflow/env.yaml"
out=$(clean HOME="$TMP/home3" XDG_CONFIG_HOME="$XDG3" -- bash "$S")
has "reach: ssh reports storage_root's configured value"  "/nowhere/on/the/site" "$out"
has "...and says it is site-side, not checked from here"  "not checked from here - reach: ssh" "$out"
has "ssh control path section is populated under reach:ssh" "cm-%r-%h-%p" "$out"

XDG4="$TMP/home4/.config"; mkdir -p "$XDG4/agentic-bioflow"
printf 'reach: none\n' > "$XDG4/agentic-bioflow/env.yaml"; chmod 600 "$XDG4/agentic-bioflow/env.yaml"
out=$(clean HOME="$TMP/home4" XDG_CONFIG_HOME="$XDG4" -- bash "$S")
has "ssh control path section says n/a outside reach:ssh" "n/a - reach: none" "$out"

# ---------------------------------------------------------------------------
# LAB_SETTINGS_FILE wins outright and is shown as its own row.
EXPLICIT="$TMP/explicit/env.yaml"; mkdir -p "$TMP/explicit"
printf 'seqera_user: carol\n' > "$EXPLICIT"; chmod 600 "$EXPLICIT"
out=$(clean HOME="$TMP/home5" XDG_CONFIG_HOME="$TMP/home5/.config" \
      LAB_SETTINGS_FILE="$EXPLICIT" -- bash "$S")
has "an explicit LAB_SETTINGS_FILE gets its own row"  "LAB_SETTINGS_FILE overrides all three: $EXPLICIT" "$out"
has "...marked exists"                                "[exists]" "$out"
has "and 'in use' names it"                            "in use: $EXPLICIT" "$out"

# ---------------------------------------------------------------------------
# The token is never printed, only its state - same rule as settings.sh
# --summary and inspect_sides.sh.
SECRET='not-a-real-token-9Q7X'
printf '%s\n' "$SECRET" > "$RUNS/_personal/.seqera_token"
chmod 600 "$RUNS/_personal/.seqera_token"
out=$(clean HOME="$HOME2" XDG_CONFIG_HOME="$HOME2/.config" LAB_RUNS_DIR="$RUNS" -- bash "$S")
hasnot "the token's value is never printed"  "$SECRET" "$out"
has    "but its presence and mode are"       "present (mode 600)" "$out"

# ---------------------------------------------------------------------------
# The off-design reports queue comes from report.sh --queue-dir, the one
# place that formula lives - not a second copy here that could drift.
QDIR=$(clean HOME="$HOME2" XDG_CONFIG_HOME="$HOME2/.config" LAB_RUNS_DIR="$RUNS" -- \
       bash "$(dirname "$S")/report.sh" --queue-dir)
out=$(clean HOME="$HOME2" XDG_CONFIG_HOME="$HOME2/.config" LAB_RUNS_DIR="$RUNS" -- bash "$S")
has "the reports queue path matches report.sh's own reports_dir()" "$QDIR" "$out"

# ---------------------------------------------------------------------------
# State directory: intro marker dir and the (currently unwritten) Positron
# bridge convention path both live under the same state base.
STATE="$TMP/state"; mkdir -p "$STATE/intro-shown"
: > "$STATE/intro-shown/abc123"
: > "$STATE/intro-shown/def456"
out=$(clean HOME="$HOME2" XDG_CONFIG_HOME="$HOME2/.config" LAB_RUNS_DIR="$RUNS" \
      AGENTIC_BIOFLOW_STATE_DIR="$STATE" -- bash "$S")
has "intro marker dir is reported with its marker count"  "2 marker(s)" "$out"
has "and is marked exists"                                 "$STATE/intro-shown" "$out"
has "the positron bridge convention path is named"         "$STATE/positron-bridge" "$out"
has "...and honestly marked missing (nothing writes it yet)" "positron-bridge" "$out"

# ---------------------------------------------------------------------------
# --run-paths: the interface prepare_launch.sh (perf/latency, not on this
# branch) is documented in this file's own header to call.
out=$(clean HOME="$HOME2" XDG_CONFIG_HOME="$HOME2/.config" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --run-paths myproj myrun 2>&1); rc=$?
t "--run-paths exits clean"  "$rc"  "0"
has "--run-paths prints the site run dir"   "site_run_dir=$RUNS/alice/projects/myproj/runs/myrun" "$out"
has "--run-paths prints the local fetch dir" \
    "local_fetch_dir=$TMP/local/alice/projects/myproj/runs/myrun/results" "$out"

out=$(clean HOME="$HOME2" XDG_CONFIG_HOME="$HOME2/.config" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --run-paths myproj myrun --local-root "$TMP/override_root" 2>&1)
has "--local-root overrides the configured local_root outright" \
    "local_fetch_dir=$TMP/override_root/alice/projects/myproj/runs/myrun/results" "$out"

# Missing seqera_user: refused before printing either line, not a half-answer.
XDG6="$TMP/home6/.config"; mkdir -p "$XDG6/agentic-bioflow"
printf 'reach: local\n' > "$XDG6/agentic-bioflow/env.yaml"; chmod 600 "$XDG6/agentic-bioflow/env.yaml"
out=$(clean HOME="$TMP/home6" XDG_CONFIG_HOME="$XDG6" -- bash "$S" --run-paths p r 2>&1); rc=$?
t "--run-paths with no seqera_user is refused, not guessed"  "$rc"  "2"
hasnot "and prints no site_run_dir line at all"  "site_run_dir=" "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
