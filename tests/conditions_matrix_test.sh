#!/bin/bash
# scripts/detect_conditions.sh: local measurement only, never touches the
# network, decides which cell of the condition matrix this run is in.
#
# This exercises every cell the decision tree can reach (docs/CONDITIONS.md
# names the same set - see the cross-reference block at the end), each one
# positive and negative, plus the raw fields it composes them from. A fake
# `uname` on PATH stands in for the OS; a temp settings file reached through
# LAB_SETTINGS_FILE (scripts/settings.sh's own knob) stands in for `reach`;
# AGENTIC_BIOFLOW_HOST_HOOKS/AGENTIC_BIOFLOW_ATTENDED stand in for a runtime
# that is not this interactive Claude Code session.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
D="$ROOT/scripts/detect_conditions.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()      { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }

# --- a fake uname on PATH, like tests/install_deps_test.sh's Z1 block --------
UB="$TMP/bin"; mkdir -p "$UB"
mkuname() { # mkuname <uname -s answer>
  cat > "$UB/uname" <<EOF
#!/bin/bash
case "\$1" in
  -s) echo "$1" ;;
  *)  echo unknown ;;
esac
EOF
  chmod +x "$UB/uname"
}
mkuname Linux
BASEPATH="$UB:/usr/bin:/bin"

# GNU env requires every -u before the first NAME=VALUE, or it starts reading
# arguments as the command instead. Keeping the unset list in one array, always
# passed first, is what keeps every call below from tripping over that.
UNSETS=(-u CLAUDE_PLUGIN_ROOT -u CLAUDECODE -u AGENTIC_BIOFLOW_HOST_HOOKS \
        -u AGENTIC_BIOFLOW_ATTENDED -u CLAUDE_CODE_ENTRYPOINT -u TERM_PROGRAM \
        -u VSCODE_GIT_ASKPASS_MAIN)

# A settings file, minted per test, so `reach` is whatever the test wants.
# Everything else about the deployment is irrelevant here.
settings_with_reach() { # settings_with_reach <reach-or-empty-for-no-file>
  local f="$TMP/env_$RANDOM$RANDOM.yaml"
  if [ -n "$1" ]; then
    printf 'reach: %s\nworkspace_id: 1\n' "$1" > "$f"
  fi
  printf '%s\n' "$f"
}

# run <PATH-value> [env assignments...] -- <args to detect_conditions.sh>
# Always starts from a clean slate (no host-hooks/attended leaking from this
# very session, since this test itself runs under Claude Code) and a fixed
# HOME/SHELL unless overridden.
run() {
  local pathval="$1"; shift
  local envs=() args=() seen_dd=0
  for a in "$@"; do
    if [ "$a" = -- ]; then seen_dd=1; continue; fi
    if [ "$seen_dd" = 0 ]; then envs+=("$a"); else args+=("$a"); fi
  done
  env -i "${UNSETS[@]}" PATH="$pathval" HOME="$TMP" SHELL=/bin/bash \
      "${envs[@]}" bash "$D" "${args[@]}"
}
getval() { # getval <key> [env assignments...]
  local key="$1"; shift
  run "$BASEPATH" "$@" -- --get "$key"
}

echo "== basic fields =="
NOFILE=$(settings_with_reach "")
LOCALF=$(settings_with_reach local)
SSHF=$(settings_with_reach ssh)
NONEF=$(settings_with_reach none)

mkuname Linux
t "os=linux from a Linux uname"   "$(getval os LAB_SETTINGS_FILE="$LOCALF")" "linux"
mkuname Darwin
t "os=macos from a Darwin uname"  "$(getval os LAB_SETTINGS_FILE="$LOCALF")" "macos"
mkuname MINGW64_NT
t "os=msys from an MSYS uname"    "$(getval os LAB_SETTINGS_FILE="$LOCALF")" "msys"
mkuname Plan9
t "os=other for anything else"    "$(getval os LAB_SETTINGS_FILE="$LOCALF")" "other"
mkuname Linux

t "shell reads basename of \$SHELL"      "$(getval shell SHELL=/usr/bin/zsh LAB_SETTINGS_FILE="$LOCALF")" "zsh"
# bash itself repopulates $SHELL at startup when it finds the variable simply
# UNSET (measured: `env -i bash -c 'echo $SHELL'` prints /bin/bash even with a
# fully cleared environment), so the only way to hand the script a genuinely
# empty SHELL is to set it to the empty string rather than unset it.
t "shell falls back to unknown"          "$(getval shell SHELL= LAB_SETTINGS_FILE="$LOCALF")" "unknown"

t "reach comes from the settings file"        "$(getval reach LAB_SETTINGS_FILE="$SSHF")" "ssh"
t "reach=unset when there is no settings file" "$(getval reach LAB_SETTINGS_FILE="$NOFILE")" "unset"
t "reach=none is read straight from settings"  "$(getval reach LAB_SETTINGS_FILE="$NONEF")" "none"

echo
echo "== jq =="
NOJQ="$TMP/nojq"; mkdir -p "$NOJQ"
for tool in bash cat mkdir tr sed grep find date rm mktemp basename dirname printf head; do
  p=$(command -v "$tool" 2>/dev/null) && ln -sf "$p" "$NOJQ/$tool"
done
mkuname Linux; cp "$UB/uname" "$NOJQ/uname"; chmod +x "$NOJQ/uname"
HASJQ_PRESENT=1; command -v jq >/dev/null 2>&1 || HASJQ_PRESENT=0
if [ "$HASJQ_PRESENT" = 1 ]; then
  t "jq=yes when jq is on PATH" "$(getval jq LAB_SETTINGS_FILE="$LOCALF")" "yes"
else
  echo "skip: no real jq on this test machine to prove the positive case"
fi
t "jq=no with no jq on PATH" "$(run "$NOJQ" LAB_SETTINGS_FILE="$LOCALF" -- --get jq)" "no"

echo
echo "== hooks =="
t "hooks=yes via CLAUDE_PLUGIN_ROOT"         "$(getval hooks CLAUDE_PLUGIN_ROOT=/some/plugin LAB_SETTINGS_FILE="$LOCALF")" "yes"
t "hooks=yes via CLAUDECODE=1"               "$(getval hooks CLAUDECODE=1 LAB_SETTINGS_FILE="$LOCALF")" "yes"
t "hooks=unknown with neither set"           "$(getval hooks LAB_SETTINGS_FILE="$LOCALF")" "unknown"
t "AGENTIC_BIOFLOW_HOST_HOOKS=no overrides even CLAUDECODE=1" \
  "$(getval hooks CLAUDECODE=1 AGENTIC_BIOFLOW_HOST_HOOKS=no LAB_SETTINGS_FILE="$LOCALF")" "no"
t "AGENTIC_BIOFLOW_HOST_HOOKS=yes overrides with nothing else set" \
  "$(getval hooks AGENTIC_BIOFLOW_HOST_HOOKS=yes LAB_SETTINGS_FILE="$LOCALF")" "yes"

echo
echo "== attended =="
t "attended=yes from the env"     "$(getval attended AGENTIC_BIOFLOW_ATTENDED=yes LAB_SETTINGS_FILE="$LOCALF")" "yes"
t "attended=no from the env"      "$(getval attended AGENTIC_BIOFLOW_ATTENDED=no LAB_SETTINGS_FILE="$LOCALF")" "no"
t "attended=unknown otherwise"    "$(getval attended LAB_SETTINGS_FILE="$LOCALF")" "unknown"

echo
echo "== tier =="
t "tier=H3 when hooks=no regardless of attended" \
  "$(getval tier AGENTIC_BIOFLOW_HOST_HOOKS=no AGENTIC_BIOFLOW_ATTENDED=yes LAB_SETTINGS_FILE="$LOCALF")" "H3"
t "tier=H2 when hooks=yes and attended=no" \
  "$(getval tier AGENTIC_BIOFLOW_HOST_HOOKS=yes AGENTIC_BIOFLOW_ATTENDED=no LAB_SETTINGS_FILE="$LOCALF")" "H2"
t "tier=H1 when hooks=yes and attended=yes" \
  "$(getval tier AGENTIC_BIOFLOW_HOST_HOOKS=yes AGENTIC_BIOFLOW_ATTENDED=yes LAB_SETTINGS_FILE="$LOCALF")" "H1"
t "tier=H1 when hooks=unknown (attended irrelevant)" \
  "$(getval tier AGENTIC_BIOFLOW_ATTENDED=no LAB_SETTINGS_FILE="$LOCALF")" "H1"
t "tier=H1 when hooks=yes and attended=unknown" \
  "$(getval tier AGENTIC_BIOFLOW_HOST_HOOKS=yes LAB_SETTINGS_FILE="$LOCALF")" "H1"

echo
echo "== interface: reuses status.sh, not a second implementation =="
t "interface=vscode from claude-vscode entrypoint" \
  "$(getval interface CLAUDE_CODE_ENTRYPOINT=claude-vscode LAB_SETTINGS_FILE="$LOCALF")" "vscode"
t "interface=vscode when TERM_PROGRAM corroborates it, entrypoint or not" \
  "$(getval interface CLAUDE_CODE_ENTRYPOINT=cli TERM_PROGRAM=vscode LAB_SETTINGS_FILE="$LOCALF")" "vscode"
t "interface=cli for a plain cli entrypoint" \
  "$(getval interface CLAUDE_CODE_ENTRYPOINT=cli LAB_SETTINGS_FILE="$LOCALF")" "cli"
t "interface=unknown with nothing set" \
  "$(getval interface LAB_SETTINGS_FILE="$LOCALF")" "unknown"
# Cross-check against status.sh directly: both must agree, because
# detect_conditions.sh is required to call through to it, not reimplement it.
SI=$(env -i "${UNSETS[@]}" PATH="$BASEPATH" HOME="$TMP" CLAUDE_CODE_ENTRYPOINT=claude-vscode \
     LAB_SETTINGS_FILE="$LOCALF" bash "$ROOT/scripts/status.sh" --interface)
t "matches status.sh --interface exactly" \
  "$(getval interface CLAUDE_CODE_ENTRYPOINT=claude-vscode LAB_SETTINGS_FILE="$LOCALF")" "$SI"

echo
echo "== the full key order and set, on a plain --get-less run =="
mkuname Linux
FULL=$(run "$BASEPATH" LAB_SETTINGS_FILE="$LOCALF" --)
rc=$?
printf '%-64s ' "exit code is 0"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: $rc"; fails=$((fails+1)); }
WANT_KEYS=$'os\nshell\ninterface\nreach\njq\nhooks\nattended\ntier\ncell\nstatus\nmay_touch_site\nmessage'
GOT_KEYS=$(cut -d= -f1 <<<"$FULL")
t "exactly these keys, in this order" "$GOT_KEYS" "$WANT_KEYS"

echo
echo "== timing: well under 1s, purely local =="
START=$(date +%s%N 2>/dev/null || date +%s)
run "$BASEPATH" LAB_SETTINGS_FILE="$LOCALF" -- >/dev/null 2>&1
END=$(date +%s%N 2>/dev/null || date +%s)
if [[ "$START" == *N* || ${#START} -lt 15 ]]; then
  # nanosecond date unavailable on this date(1) (e.g. a BSD one); skip rather
  # than fake precision.
  echo "skip: nanosecond timing unavailable on this date(1)"
else
  MS=$(( (END - START) / 1000000 ))
  printf '%-64s ' "finished in well under 1000ms"
  [ "$MS" -lt 900 ] && echo "ok (${MS}ms)" || { echo "FAIL: ${MS}ms"; fails=$((fails+1)); }
fi

echo
echo "== bad usage =="
printf '%-64s ' "unknown flag exits 2"
run "$BASEPATH" LAB_SETTINGS_FILE="$LOCALF" -- --bogus >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc=$rc"; fails=$((fails+1)); }
printf '%-64s ' "--get with no key exits 2"
run "$BASEPATH" LAB_SETTINGS_FILE="$LOCALF" -- --get >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc=$rc"; fails=$((fails+1)); }
printf '%-64s ' "--get with an unknown key exits 2"
run "$BASEPATH" LAB_SETTINGS_FILE="$LOCALF" -- --get bogus >/dev/null 2>&1; rc=$?
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc=$rc"; fails=$((fails+1)); }
printf '%-64s ' "ordinary usage exits 0 even when the cell is blocked"
run "$NOJQ" LAB_SETTINGS_FILE="$LOCALF" -- >/dev/null 2>&1; rc=$?
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc=$rc"; fails=$((fails+1)); }

echo
echo "== no network, ever =="
# All five legitimately appear as PROSE (this very header explains what the
# script never does) and ssh/tw/gh additionally appear as bare comparison
# values ("$reach" = ssh) - so this checks INVOCATION shape, not mere presence:
# the word sitting right after a command-starting shell operator (start of
# line, ; & | ( or a backtick/$( ) with nothing but whitespace between, which
# is how a real `curl ...`, `ssh $host ...`, `tw launch ...` or `gh api ...`
# call would appear and how prose or a bare-word comparison never does.
printf '%-64s ' "curl/wget/ssh/tw/gh never appear in invocation position"
if grep -nE '(^|[;&|(`]|\$\()[[:space:]]*(curl|wget|ssh|tw|gh)([[:space:]]|$)' "$D"; then
  echo "FAIL: a network-shaped command invocation appears above"; fails=$((fails+1))
else
  echo ok
fi

# ---------------------------------------------------------------------------
# The five decision cells: every one of blocked-no-jq, unsupported-msys-native,
# blocked-h3-site, unsupported-cloud-ce and supported, positive and negative,
# plus the priority order when more than one condition applies at once.
# ---------------------------------------------------------------------------
echo
echo "== cell: blocked-no-jq =="
OUT=$(run "$NOJQ" LAB_SETTINGS_FILE="$LOCALF" --)
has "cell is blocked-no-jq"        "cell=blocked-no-jq"   "$OUT"
has "status is blocked"            "status=blocked"       "$OUT"
# may_touch_site's spec is literally "no for H3, and no when os=msys under
# reach ssh" - two structural triggers, neither of which is "jq is missing".
# A missing jq blocks everything this session does (PITFALLS 28) but says
# nothing about whether the HOST is structurally allowed near the site, which
# is the narrower question this field answers.
has "may_touch_site is still yes (jq is not one of its two triggers)" "may_touch_site=yes" "$OUT"
has "message names the mac fix"    "brew install jq"      "$OUT"
has "message names the WSL/Linux fix" "sudo apt install jq" "$OUT"

echo
echo "== cell: unsupported-msys-native =="
mkuname MINGW64_NT
OUT=$(run "$BASEPATH" LAB_SETTINGS_FILE="$SSHF" --)
has "cell is unsupported-msys-native" "cell=unsupported-msys-native" "$OUT"
has "status is unsupported"           "status=unsupported"           "$OUT"
has "message points at WSL"           "WSL"                          "$OUT"
has "and names the report path"       "report.sh"                    "$OUT"
has "and it still may not touch the site" "may_touch_site=no"        "$OUT"
printf '%-64s ' "and does not repeat the retracted 16b conclusion"
grep -q 'cannot hold the shared ssh connection' <<<"$OUT" \
  && { echo "FAIL: repeats it"; fails=$((fails+1)); } || echo ok

OUT=$(run "$BASEPATH" LAB_SETTINGS_FILE="$LOCALF" --)
printf '%-64s ' "negative: msys + reach=local is NOT this cell"
grep -q 'cell=unsupported-msys-native' <<<"$OUT" && { echo "FAIL: wrongly flagged"; fails=$((fails+1)); } || echo ok
mkuname Linux
OUT=$(run "$BASEPATH" LAB_SETTINGS_FILE="$SSHF" --)
printf '%-64s ' "negative: linux + reach=ssh is NOT this cell"
grep -q 'cell=unsupported-msys-native' <<<"$OUT" && { echo "FAIL: wrongly flagged"; fails=$((fails+1)); } || echo ok

echo
echo "== cell: blocked-h3-site =="
h3() { # h3 <settings-file>
  env -i -u CLAUDE_PLUGIN_ROOT -u CLAUDECODE -u AGENTIC_BIOFLOW_ATTENDED \
      -u CLAUDE_CODE_ENTRYPOINT -u TERM_PROGRAM -u VSCODE_GIT_ASKPASS_MAIN \
      PATH="$BASEPATH" HOME="$TMP" SHELL=/bin/bash \
      AGENTIC_BIOFLOW_HOST_HOOKS=no LAB_SETTINGS_FILE="$1" bash "$D"
}
OUT=$(h3 "$SSHF")
has "H3 + reach=ssh is blocked-h3-site"  "cell=blocked-h3-site" "$OUT"
has "status is blocked"                   "status=blocked"       "$OUT"
has "message names the no-hooks reason"   "no plugin hooks" "$OUT"
has "message points at docs/LAB_AGENTS.md" "docs/LAB_AGENTS.md" "$OUT"
has "may_touch_site is no"                "may_touch_site=no"    "$OUT"

OUT=$(h3 "$LOCALF")
has "H3 + reach=local is also blocked-h3-site" "cell=blocked-h3-site" "$OUT"

OUT=$(h3 "$NONEF")
printf '%-64s ' "negative: H3 + reach=none is NOT blocked-h3-site (falls to unsupported)"
grep -q 'cell=blocked-h3-site' <<<"$OUT" && { echo "FAIL"; fails=$((fails+1)); } || echo ok
has "and lands on unsupported-cloud-ce instead" "cell=unsupported-cloud-ce" "$OUT"
has "but may_touch_site stays no for H3 regardless" "may_touch_site=no" "$OUT"

OUT=$(h3 "$NOFILE")
printf '%-64s ' "negative: H3 + no settings file (reach=unset) is NOT blocked-h3-site"
grep -q 'cell=blocked-h3-site' <<<"$OUT" && { echo "FAIL"; fails=$((fails+1)); } || echo ok
has "may_touch_site is still no (tier alone decides this field)" "may_touch_site=no" "$OUT"

echo
echo "== cell: unsupported-cloud-ce =="
OUT=$(run "$BASEPATH" LAB_SETTINGS_FILE="$NONEF" --)
has "cell is unsupported-cloud-ce"  "cell=unsupported-cloud-ce" "$OUT"
has "status is unsupported"         "status=unsupported"        "$OUT"
has "message tells the user to report it" "scripts/report.sh"   "$OUT"
has "may_touch_site is yes (not H3, not msys+ssh)" "may_touch_site=yes" "$OUT"

echo
echo "== cell: supported =="
OUT=$(run "$BASEPATH" LAB_SETTINGS_FILE="$LOCALF" --)
has "cell is supported"    "cell=supported"    "$OUT"
has "status is supported"  "status=supported"  "$OUT"
has "may_touch_site is yes" "may_touch_site=yes" "$OUT"

echo
echo "== priority: blocked beats unsupported beats supported =="
# no-jq wins over msys native
mkuname MINGW64_NT
OUT=$(run "$NOJQ" LAB_SETTINGS_FILE="$SSHF" --)
has "no-jq beats msys-native when both apply" "cell=blocked-no-jq" "$OUT"

# no-jq wins over H3+ssh
OUT=$(env -i -u CLAUDE_PLUGIN_ROOT -u CLAUDECODE -u AGENTIC_BIOFLOW_ATTENDED \
      -u CLAUDE_CODE_ENTRYPOINT -u TERM_PROGRAM -u VSCODE_GIT_ASKPASS_MAIN \
      PATH="$NOJQ" HOME="$TMP" SHELL=/bin/bash \
      AGENTIC_BIOFLOW_HOST_HOOKS=no LAB_SETTINGS_FILE="$SSHF" bash "$D")
has "no-jq beats H3-site when both apply" "cell=blocked-no-jq" "$OUT"

# H3+ssh wins over msys native: blocked beats unsupported
mkuname MINGW64_NT
OUT=$(h3 "$SSHF")
has "H3-site beats msys-native when both apply" "cell=blocked-h3-site" "$OUT"
mkuname Linux

echo
echo "== docs/CONDITIONS.md cross-reference =="
DOC="$ROOT/docs/CONDITIONS.md"
printf '%-64s ' "docs/CONDITIONS.md exists"
[ -r "$DOC" ] && echo ok || { echo "FAIL: missing $DOC"; fails=$((fails+1)); exit 1; }

SCRIPT_CELLS=$(grep -oE 'cell=[a-z0-9._-]+' "$D" | cut -d= -f2 | sort -u)
DOC_CELLS=$(grep -oE '`[a-z0-9._-]+`' "$DOC" | tr -d '`' \
  | grep -E '^(blocked|unsupported|supported)(-[a-z0-9._-]+)*$' | sort -u)

printf '%-64s ' "every cell code detect_conditions.sh can print is documented"
missing=$(comm -23 <(echo "$SCRIPT_CELLS") <(echo "$DOC_CELLS"))
[ -z "$missing" ] && echo ok || { echo "FAIL: undocumented cells:"; echo "$missing"; fails=$((fails+1)); }

printf '%-64s ' "docs/CONDITIONS.md names no cell the script cannot print"
extra=$(comm -13 <(echo "$SCRIPT_CELLS") <(echo "$DOC_CELLS"))
[ -z "$extra" ] && echo ok || { echo "FAIL: extra cells in docs:"; echo "$extra"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
