#!/bin/bash
# D4: scripts/status.sh is the "where you are" card - four sections, ending in
# one concrete next step (U3 in the plan this implements). It is not allowed
# to re-implement any check preflight.sh, settings.sh or inspect_sides.sh
# already do, so this test fakes those three and checks status.sh only
# formats and decides - it never computes a fact those scripts did not hand it.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t() { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }

# A faked deployment: real settings.sh, real portable.sh, but inspect_sides.sh
# and preflight.sh replaced with stubs this test controls - no ssh, no
# network, no real site, and the exact facts under test.
FAKE="$TMP/fake_scripts"; mkdir -p "$FAKE/utils"
cp "$ROOT"/scripts/*.sh "$FAKE"/ 2>/dev/null
cp "$ROOT"/scripts/utils/*.sh "$FAKE/utils/" 2>/dev/null
ST="$FAKE/status.sh"

cat > "$FAKE/inspect_sides.sh" <<'EOF'
#!/bin/bash
cat <<'SIDES'
reach=ssh
site.reachable=yes
site.settings=yes
site.token=yes
site.skeleton=yes
site.tw=yes
site.java=yes
site.jar=no
site.runs=4
local.settings=yes
local.token=yes
local.skeleton=no
local.tw=yes
SIDES
EOF
chmod +x "$FAKE/inspect_sides.sh"

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

SETTINGS_FILE_PATH="$TMP/env.yaml"
cat > "$SETTINGS_FILE_PATH" <<YAML
reach: ssh
site_host: me@example.org
workspace_id: 999
YAML
chmod 600 "$SETTINGS_FILE_PATH"
SECRET='not-a-real-token-9Q7X'
printf '%s\n' "$SECRET" > "$TMP/.seqera_token"; chmod 600 "$TMP/.seqera_token"

run() { echo 0 > "$PF_RC_FILE"; LAB_SETTINGS_FILE="$SETTINGS_FILE_PATH" "$@" bash "$ST" 2>&1; }
run_pf_fail() { echo 1 > "$PF_RC_FILE"; LAB_SETTINGS_FILE="$SETTINGS_FILE_PATH" "$@" bash "$ST" 2>&1; }

out=$(run)

# --- structure: four sections, in order -------------------------------------
printf '%-64s ' "has all four sections, in order"
order=$(grep -n '^== ' <<<"$out" | sed 's/.*== \(.*\) ==/\1/')
want=$'Your environment\nBoth sides\nSetup progress\nNext step'
[ "$order" = "$want" ] && echo ok || { echo "FAIL: got:"; echo "$order"; fails=$((fails+1)); }

# --- section 1: this machine -------------------------------------------------
has "names the reach it read from settings"     "Reach: ssh"    "$out"
has "picks up CLAUDE_CODE_ENTRYPOINT"           "vscode"        "$(run CLAUDE_CODE_ENTRYPOINT=vscode)"
# "unknown" is only the right answer when nothing else says otherwise, so the
# editor's own variables are cleared here too - see the surface section below.
unset_entrypoint_run() { echo 0 > "$PF_RC_FILE"; env -u CLAUDE_CODE_ENTRYPOINT -u TERM_PROGRAM -u VSCODE_GIT_ASKPASS_MAIN LAB_SETTINGS_FILE="$SETTINGS_FILE_PATH" bash "$ST" 2>&1; }
has "says 'unknown' when the entrypoint is unset" "unknown"     "$(unset_entrypoint_run)"

# --- section 2: both sides, straight from inspect_sides.sh ------------------
has "site row carries what inspect_sides.sh reported"   "runs=4"        "$out"
has "site row shows jar=no exactly as inspect_sides.sh said" "jar=no"   "$out"
has "local row is present too"                          "local "        "$out"

# --- section 3: setup progress, straight from preflight + settings ----------
has "shows preflight's own OK line verbatim"            "compute-env"   "$out"
has "names the settings file's location"                "$SETTINGS_FILE_PATH" "$out"
has "says the token is present, not its value"          "present (mode 600)" "$out"
hasnot "never prints the token's value"                 "$SECRET"       "$out"

fail_out=$(run_pf_fail)
has "when preflight FAILs, the FAIL line surfaces"      "FAIL"          "$fail_out"
has "and names what failed"                             "agent"         "$fail_out"

# --- section 4: next step, one concrete sentence -----------------------------
has "next step points at :launch when everything is ready" ":launch"   "$out"
hasnot "does not suggest :setup when everything is ready"  "Run :setup" "$out"
has "next step names :setup when preflight FAILs"          ":setup"    "$fail_out"
has "and names the failing check, not just 'something failed'" "agent" "$fail_out"

# No settings file at all - the very first run, before setup has done anything.
NOFILE="$TMP/never.yaml"
out_none=$(echo 0 > "$PF_RC_FILE"; LAB_SETTINGS_FILE="$NOFILE" bash "$ST" 2>&1)
has "with no settings file, next step is to run setup" ":setup" "$out_none"

# --- the line budget ----------------------------------------------------------
printf '%-64s ' "stays under ~30 lines"
n=$(wc -l <<<"$out")
[ "$n" -le 30 ] && echo ok || { echo "FAIL: $n lines"; fails=$((fails+1)); }

echo

# The surface line must not trust CLAUDE_CODE_ENTRYPOINT alone: measured on
# this machine, one VS Code session reported claude-vscode and a later one
# reported cli. A report field that names the wrong surface sends the
# maintainer looking at the wrong platform.
echo "== which surface the user is on =="
surface_line() { echo 0 > "$PF_RC_FILE"; env "$@" LAB_SETTINGS_FILE="$SETTINGS_FILE_PATH" bash "$ST" 2>/dev/null | sed -n 2p; }

line=$(surface_line -u TERM_PROGRAM -u VSCODE_GIT_ASKPASS_MAIN CLAUDE_CODE_ENTRYPOINT=cli)
case "$line" in
    *"VS Code"*) echo "FAIL: a plain terminal claimed VS Code: $line"; fails=$((fails+1)) ;;
    *cli*)       echo "ok: a plain terminal is reported as a plain terminal" ;;
    *)           echo "FAIL: surface line missing: $line"; fails=$((fails+1)) ;;
esac

line=$(surface_line -u VSCODE_GIT_ASKPASS_MAIN TERM_PROGRAM=vscode CLAUDE_CODE_ENTRYPOINT=cli)
case "$line" in
    *"VS Code"*) echo "ok: a cli entrypoint inside VS Code is reported as such" ;;
    *)           echo "FAIL: VS Code not detected from the editor's own variables: $line"; fails=$((fails+1)) ;;
esac

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
