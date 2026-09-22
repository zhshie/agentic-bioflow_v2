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
    # XDG_CONFIG_HOME too: T30's root pointer lives under it, and a CI runner
    # sets it globally. Left in place, every fixture in this file shares ONE
    # pointer file whatever HOME it was given, so a root one case `--use`s
    # leaks into the next. It did, on GitHub Actions - and was invisible
    # locally, where the variable happened to be unset.
    env -u XDG_CONFIG_HOME -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
        -u AGENTIC_BIOFLOW_STATE_DIR -u AGENTIC_BIOFLOW_REPORTS_DIR \
        "${envs[@]}" "$@"
}

# T30: one root, named by a pointer under $HOME. This helper builds a fixture
# deployment the way a real one is built - `--use`, then the settings inside
# it - so the test can never assert a layout that setup would not produce.
SET="$(dirname "$S")/settings.sh"
mkroot() { # mkroot <home> <root>  (env.yaml on stdin)
    clean HOME="$1" -- bash "$SET" --use "$2" >/dev/null 2>&1
    cat > "$2/config/env.yaml"
    chmod 600 "$2/config/env.yaml"
}

# ---------------------------------------------------------------------------
# A machine that has never been pointed at a root.
HOME1="$TMP/home1"; mkdir -p "$HOME1"
out=$(clean HOME="$HOME1" -- bash "$S")
has "names the pointer file it looked for"   "$HOME1/.config/agentic-bioflow/root" "$out"
has "and says this machine has no root yet"  "no root on this machine yet" "$out"
has "the pointer is marked missing"          "[missing]" "$out"
has "and 'in use' says none"                 "in use: none" "$out"
has "the token is reported not found"        "not found" "$out"
has "the reports queue is reported missing"  "[missing]" "$out"

# ---------------------------------------------------------------------------
# reach: local. The root holds the settings; LAB_RUNS_DIR is the SITE's run
# area and nothing to do with where settings live any more - which is exactly
# the separation T30 introduced.
RUNS="$TMP/site_runs"; mkdir -p "$RUNS"
LOCAL="$TMP/local"
HOME2="$TMP/home2"; mkdir -p "$HOME2"
mkroot "$HOME2" "$LOCAL" <<YAML
seqera_user: alice
reach: local
storage_root: $RUNS
YAML
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- bash "$S")
has "the root is named"                            "root:    $LOCAL" "$out"
has "and it is marked exists"                      "[exists]" "$out"
has "'in use' names the file actually read"        "in use: $LOCAL/config/env.yaml" "$out"
has "this machine's own keys file is named too"    "config/machines/<this>" "$out"
hasnot "storage_root under reach:local is not deferred to the site" \
    "not checked from here" "$out"

# ---------------------------------------------------------------------------
# reach: ssh - storage_root is a site-side path and must NOT be existence
# checked from this machine (no ssh, no network - that is inspect_sides.sh's
# job, at the cost of the round trip this script deliberately avoids).
HOME3="$TMP/home3"; mkdir -p "$HOME3"
mkroot "$HOME3" "$TMP/root3" <<YAML
reach: ssh
seqera_user: bob
storage_root: /nowhere/on/the/site
site_host: bob@example.org
ssh_control_path: ~/.ssh/cm-%r-%h-%p
YAML
out=$(clean HOME="$HOME3" -- bash "$S")
has "reach: ssh reports storage_root's configured value"  "/nowhere/on/the/site" "$out"
has "...and says it is site-side, not checked from here"  "not checked from here - reach: ssh" "$out"
has "ssh control path section is populated under reach:ssh" "cm-%r-%h-%p" "$out"

HOME4="$TMP/home4"; mkdir -p "$HOME4"
mkroot "$HOME4" "$TMP/root4" <<YAML
reach: none
YAML
out=$(clean HOME="$HOME4" -- bash "$S")
has "ssh control path section says n/a outside reach:ssh" "n/a - reach: none" "$out"

# ---------------------------------------------------------------------------
# LAB_SETTINGS_FILE wins outright and is shown as its own row.
EXPLICIT="$TMP/explicit/env.yaml"; mkdir -p "$TMP/explicit"
printf 'seqera_user: carol\n' > "$EXPLICIT"; chmod 600 "$EXPLICIT"
out=$(clean HOME="$TMP/home5" \
      LAB_SETTINGS_FILE="$EXPLICIT" -- bash "$S")
has "an explicit LAB_SETTINGS_FILE gets its own row"  "LAB_SETTINGS_FILE overrides the pointer: $EXPLICIT" "$out"
has "...marked exists"                                "[exists]" "$out"
has "and 'in use' names it"                            "in use: $EXPLICIT" "$out"

# ---------------------------------------------------------------------------
# The token is never printed, only its state - same rule as settings.sh
# --summary and inspect_sides.sh.
SECRET='not-a-real-token-9Q7X'
printf '%s\n' "$SECRET" > "$LOCAL/config/.seqera_token"
chmod 600 "$LOCAL/config/.seqera_token"
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- bash "$S")
hasnot "the token's value is never printed"  "$SECRET" "$out"
has    "but its presence and mode are"       "present (mode 600)" "$out"

# ---------------------------------------------------------------------------
# The off-design reports queue comes from report.sh --dir, the one
# place that formula lives - not a second copy here that could drift.
QDIR=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
       bash "$(dirname "$S")/report.sh" --dir)
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- bash "$S")
has "the reports queue path matches report.sh's own reports_dir()" "$QDIR" "$out"

# ---------------------------------------------------------------------------
# State directory: intro marker dir and the (currently unwritten) Positron
# bridge convention path both live under the same state base.
STATE="$TMP/state"; mkdir -p "$STATE/intro-shown"
: > "$STATE/intro-shown/abc123"
: > "$STATE/intro-shown/def456"
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" \
      AGENTIC_BIOFLOW_STATE_DIR="$STATE" -- bash "$S")
has "intro marker dir is reported with its marker count"  "2 marker(s)" "$out"
has "and is marked exists"                                 "$STATE/intro-shown" "$out"
has "the positron bridge convention path is named"         "$STATE/positron-bridge" "$out"
has "...and honestly marked missing (nothing writes it yet)" "positron-bridge" "$out"

# ---------------------------------------------------------------------------
# --run-paths: the interface prepare_launch.sh (perf/latency, not on this
# branch) is documented in this file's own header to call.
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --run-paths myproj myrun 2>&1); rc=$?
t "--run-paths exits clean"  "$rc"  "0"
has "--run-paths prints the site run dir"   "site_run_dir=$RUNS/alice/projects/myproj/runs/myrun" "$out"
# T29: no pre-existing old-layout directory for this project on disk, so
# local_fetch_dir resolves to the NEW layout - no <seqera_user> layer.
has "--run-paths prints the local fetch dir" \
    "local_fetch_dir=$TMP/local/projects/myproj/runs/myrun/results" "$out"

out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --run-paths myproj myrun --local-root "$TMP/override_root" 2>&1)
has "--local-root overrides the configured local_root outright" \
    "local_fetch_dir=$TMP/override_root/projects/myproj/runs/myrun/results" "$out"

# A project that already lives at the OLD, <user>-layered path keeps
# resolving there - the same per-project detection init_workspace.sh uses
# (scripts/settings.sh: local_layout_is_old()), never a machine-wide switch.
mkdir -p "$TMP/local/alice/projects/legacy/rawdata"
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --run-paths legacy myrun 2>&1)
has "a pre-existing old-layout project keeps resolving under the user layer" \
    "local_fetch_dir=$TMP/local/alice/projects/legacy/runs/myrun/results" "$out"

# Missing seqera_user: refused before printing either line, not a half-answer.
HOME6="$TMP/home6"; mkdir -p "$HOME6"
mkroot "$HOME6" "$TMP/root6" <<YAML
reach: local
YAML
out=$(clean HOME="$HOME6" -- bash "$S" --run-paths p r 2>&1); rc=$?
t "--run-paths with no seqera_user is refused, not guessed"  "$rc"  "2"
hasnot "and prints no site_run_dir line at all"  "site_run_dir=" "$out"

# ---------------------------------------------------------------------------
# T29: --project-paths - the interface commands/downstream.md and
# commands/finish.md are told to call instead of constructing a path
# themselves, now that the shape branches three ways (old layout, new
# layout, portable-redirected analysis/submission).
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --project-paths ppstudy 2>&1); rc=$?
t "--project-paths exits clean"  "$rc"  "0"
has "...prints rawdata_dir under the new (unlayered) local layout" \
    "rawdata_dir=$TMP/local/projects/ppstudy/rawdata" "$out"
has "...prints runs_dir the same way"  "runs_dir=$TMP/local/projects/ppstudy/runs" "$out"
has "...prints analysis_dir alongside rawdata/runs (no portable folder adopted)" \
    "analysis_dir=$TMP/local/projects/ppstudy/analysis" "$out"
has "...prints submission_dir the same way" \
    "submission_dir=$TMP/local/projects/ppstudy/submission" "$out"

# A pre-existing old-layout project resolves ALL FOUR paths under the user
# layer, consistently - never a mix of old rawdata/runs with a new-layout
# analysis/submission for the same project.
mkdir -p "$TMP/local/alice/projects/ppstudy_old/rawdata"
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --project-paths ppstudy_old 2>&1)
has "old-layout project: rawdata_dir under the user layer" \
    "rawdata_dir=$TMP/local/alice/projects/ppstudy_old/rawdata" "$out"
has "old-layout project: analysis_dir ALSO under the user layer, consistently" \
    "analysis_dir=$TMP/local/alice/projects/ppstudy_old/analysis" "$out"

# T30 removed the redirect this block used to assert. analysis/ and
# submission/ used to move into a separate portable folder while rawdata/ and
# runs/ stayed behind in another root, and the two had to be kept in step by
# hand. There is one root now, so all four are siblings under it - which is
# the property worth pinning, because a future change that reintroduced a
# second root would break exactly this.
out=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --project-paths ppstudy_together 2>&1)
for d in rawdata runs analysis submission; do
  has "all four project dirs are siblings in one root: $d" \
      "${d}_dir=$LOCAL/projects/ppstudy_together/$d" "$out"
done

# Missing seqera_user: refused before printing anything, not a half-answer.
out=$(clean HOME="$HOME6" -- bash "$S" --project-paths p 2>&1); rc=$?
t "--project-paths with no seqera_user is refused, not guessed"  "$rc"  "2"
hasnot "and prints no rawdata_dir line at all"  "rawdata_dir=" "$out"

# ---------------------------------------------------------------------------
# T29: THE assertion this card asks for by name - the analysis path has ONE
# source. scripts/init_workspace.sh actually builds a project (new layout,
# no portable folder) and scripts/where.sh --project-paths is asked where
# that same project's analysis/ is - they must agree exactly, because both
# call the very same scripts/settings.sh function (local_analysis_base())
# rather than each computing their own formula.
SRC_LOCAL="$TMP/single_source_root"
SRC_RUNS="$TMP/single_source_site_runs"
built_out=$(LAB_RUNS_DIR="$SRC_RUNS" bash "$(dirname "$S")/init_workspace.sh" \
      local --root "$SRC_LOCAL" --user alice --project single_source_study 2>&1)
printf '%-64s ' "init_workspace.sh actually built analysis/ where it says it did"
[ -d "$SRC_LOCAL/projects/single_source_study/analysis" ] && echo ok \
  || { echo "FAIL: not built - <<$built_out>>"; fails=$((fails+1)); }

queried=$(clean HOME="$HOME2" LAB_RUNS_DIR="$RUNS" -- \
      bash "$S" --project-paths single_source_study --local-root "$SRC_LOCAL" 2>&1 \
      | sed -n 's/^analysis_dir=//p')
t "where.sh --project-paths names the EXACT directory init_workspace.sh built" \
  "$queried"  "$SRC_LOCAL/projects/single_source_study/analysis"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
