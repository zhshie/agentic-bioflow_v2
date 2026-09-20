#!/bin/bash
# This release's requirement (docs/SETTINGS.md, the "any folder works" brief):
# a member can open Claude Code in whatever folder they already work in - a
# desktop folder, a cloud-drive sync folder, a Windows path reached from WSL -
# and none of it may matter, because nothing the plugin needs lives in the
# project folder. The one place location DOES matter is the settings file
# (scripts/settings.sh, docs/SETTINGS.md), and that is covered on its own in
# tests/settings_test.sh (B1/B2/B3).
#
# This file is the mechanical guarantee behind the word "whatever": a
# directory name with a space AND non-ASCII characters AND parentheses is not
# exotic - it is an ordinary folder name on a shared drive ("My Drive/實驗
# folder (1)" is exactly what Google Drive's desktop client and a lab member
# naming their own experiment produce together) - and every entry point that
# reads $XDG_CONFIG_HOME has to survive it: a stray unquoted variable, an `ls`
# whose glob trips on the parenthesis, a `sed` pattern anchored on ASCII, a
# `wc -c` that miscounts a multibyte character as several bytes and truncates
# something. Each of those has broken a real script before (PITFALLS), just
# never on a path shaped exactly like this one at once.
#
# Deliberately NOT one of the sync-folder names B3 refuses ("Google Drive",
# "OneDrive", ...): "My Drive" does not match any of those literal patterns,
# so this test exercises path-shape robustness only, without also tripping
# the synced-folder refusal that tests/settings_test.sh already covers on its
# own. If a maintainer later widens B3's patterns to also catch "My Drive",
# this file's env.yaml round trip will start failing loudly right here - which
# is the correct outcome, but fix this test by pointing XDG_CONFIG_HOME at a
# non-sync-shaped odd path instead of loosening the assertions.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
t()  { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
ok() { printf '%-64s ' "$1"; [ "$2" = 0 ] && echo ok || { echo "FAIL: exit $2 <<$3>>"; fails=$((fails+1)); }; }
has(){ printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: nothing matching '$2' <<$3>>"; fails=$((fails+1)); }; }

# The odd folder itself: a space, non-ASCII (Traditional Chinese, matching
# this lab's own default `language: zh-TW`), and parentheses - all at once,
# nested two levels deep the way a real sync client does it.
ODD="$TMP/My Drive/實驗 folder (1)"
mkdir -p "$ODD"
HOMEDIR="$TMP/home"; mkdir -p "$HOMEDIR"

run() {
    env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE -u XDG_CONFIG_HOME \
        HOME="$HOMEDIR" "$@" 2>&1
}

# T30: the odd path is now the ROOT itself, which is the harder case - a
# space, a bracket and a non-ASCII directory name in the one path every script
# derives every other path from.
run bash "$ROOT/scripts/settings.sh" --use "$ODD/abf" >/dev/null

# --- scripts/settings.sh: --set, a read-back, --summary ---------------------
out=$(run bash "$ROOT/scripts/settings.sh" --set workspace_id 424242); rc=$?
ok "settings.sh --set under the odd path exits 0" "$rc" "$out"

ENV_FILE="$ODD/abf/config/env.yaml"
printf '%-64s ' "...and the file actually landed under the odd path"
[ -r "$ENV_FILE" ] && echo ok || { echo "FAIL: no file at $ENV_FILE"; fails=$((fails+1)); }
printf '%-64s ' "...at mode 600, same as anywhere else"
[ "$(stat -c %a "$ENV_FILE" 2>/dev/null)" = 600 ] && echo ok \
    || { echo "FAIL: mode $(stat -c %a "$ENV_FILE" 2>/dev/null)"; fails=$((fails+1)); }

out=$(run bash "$ROOT/scripts/settings.sh" workspace_id)
t "a read-back finds the value again through the same odd path" "$out" "424242"

out=$(run bash "$ROOT/scripts/settings.sh" --summary); rc=$?
ok "settings.sh --summary under the odd path exits 0" "$rc" "$out"
has "...and names the odd path itself, not a mangled version of it" "$ODD" "$out"
has "...and shows the value written above" "424242" "$out"

# --- the other three entry points the brief names -------------------------
out=$(run bash "$ROOT/scripts/detect_conditions.sh"); rc=$?
ok "detect_conditions.sh under the odd path exits 0" "$rc" "$out"
has "...and still reports a reach, not a mangled/empty one" "reach=" "$out"

out=$(run bash "$ROOT/scripts/status.sh" --interface); rc=$?
ok "status.sh --interface under the odd path exits 0" "$rc" "$out"

out=$(run bash "$ROOT/scripts/intro.sh"); rc=$?
ok "intro.sh under the odd path exits 0" "$rc" "$out"
printf '%-64s ' "...and actually prints something, not an empty page"
[ -n "$out" ] && echo ok || { echo "FAIL: intro.sh printed nothing"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
