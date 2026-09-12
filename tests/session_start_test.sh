#!/bin/bash
# Regression tests for hooks/session_start.sh.
#
# The hook's whole value is that it speaks exactly when there is something to
# say and is silent otherwise, so both halves are tested. A start-of-session
# check that talks on every conversation is one people disable.
#
# `tw` is stubbed through TW_BIN, and the settings file through
# LAB_SETTINGS_FILE - both seams the scripts already had.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
H="$ROOT/hooks/session_start.sh"
TMP=$(mktemp -d)
trap 'chmod -R u+w "$TMP" 2>/dev/null; command rm -rf "$TMP"' EXIT
fails=0

printf 'workspace_id: 12345\ntw_bin: %s/tw\n' "$TMP" > "$TMP/env.yaml"
printf 'not-a-real-token\n' > "$TMP/.seqera_token"
chmod 600 "$TMP/env.yaml" "$TMP/.seqera_token"

cat > "$TMP/tw" <<'STUB'
#!/bin/bash
cat <<'OUT'
  Pipeline runs at [Lab / site] workspace:

     ID            | Status    | Project Name        | Run Name        | Username | Submit Date
    ---------------+-----------+---------------------+-----------------+----------+------------
     aliveRUN123   | RUNNING   | nf-core/rnaseq      | nightly-run     | someone  | today
     queuedSUB456  | SUBMITTED | nf-core/ampliseq    | waiting-run     | someone  | today
     doneOK789     | SUCCEEDED | nf-core/funcscan    | finished-run    | someone  | today
OUT
STUB
chmod +x "$TMP/tw"

# A second stub for the workspace with nothing in it. The hook's other job -
# saying where the settings live - has to survive a quiet workspace, which is
# the ordinary case.
cat > "$TMP/tw_idle" <<'STUB'
#!/bin/bash
cat <<'OUT'
  Pipeline runs at [Lab / site] workspace:

     ID            | Status    | Project Name        | Run Name        | Username | Submit Date
    ---------------+-----------+---------------------+-----------------+----------+------------
OUT
STUB
chmod +x "$TMP/tw_idle"

run() { # run <reason> <settings-file> [tw-stub]
  printf '{"session_start_reason":"%s"}' "$1" \
    | LAB_SETTINGS_FILE="$2" TW_BIN="${3:-$TMP/tw}" TOWER_WORKSPACE_ID=12345 \
      SEQERA_TOKEN_FILE="$TMP/.seqera_token" bash "$H"
}

check() { # check <label> <haystack> <needle> <present|absent>
  printf '%-52s ' "$1"
  if grep -qF -- "$3" <<<"$2"; then got=present; else got=absent; fi
  if [ "$got" = "$4" ]; then echo "ok ($got)"; else
    echo "FAIL: expected $3 $4, got $got"; fails=$((fails+1))
  fi
}

OUT=$(run startup "$TMP/env.yaml")
check "reports a RUNNING run"          "$OUT" "aliveRUN123"  present
check "reports a SUBMITTED run"        "$OUT" "queuedSUB456" present
check "stays quiet about finished runs" "$OUT" "doneOK789"   absent
check "declares itself a SessionStart"  "$OUT" "SessionStart" present

OUT=$(run compact "$TMP/env.yaml")
check "silent on a compaction"          "${OUT:-<empty>}" "aliveRUN123" absent

OUT=$(run startup "$TMP/no_such_settings.yaml")
check "silent where no deployment exists" "${OUT:-<empty>}" "aliveRUN123" absent

# --- where the settings actually are -----------------------------------------
# Nothing that reads the settings file ever named it, so the only way back to it
# was to search the filesystem - which a member did. The hook is the one place
# guaranteed to run on a machine that has one, so it says the path once.
#
# Once, though: only on a real startup. A resume is the same conversation
# continuing and has already been told.
OUT=$(run startup "$TMP/env.yaml")
check "a startup names where the settings live" "$OUT" "$TMP/env.yaml" present

OUT=$(run startup "$TMP/env.yaml" "$TMP/tw_idle")
check "and says so even with nothing in flight" "${OUT:-<empty>}" "$TMP/env.yaml" present
check "without inventing runs to report"        "${OUT:-<empty>}" "Still in flight" absent

OUT=$(run resume "$TMP/env.yaml")
check "a resume still reports the runs"         "$OUT" "aliveRUN123" present
check "but does not repeat the path"            "$OUT" "$TMP/env.yaml" absent

# U1 changed this one: a machine with no deployment used to hear NOTHING at
# all, because there was nothing to say. Now there is always the intro - a
# first-time user, with nothing set up yet, is exactly who needs it - so
# SessionStart output now appears here too. What must still be absent is
# anything implying a deployment exists: no invented settings path, no run
# report.
OUT=$(run startup "$TMP/no_such_settings.yaml" "$TMP/tw_idle")
check "U1: the intro appears even with no deployment at all" "${OUT:-<empty>}" "SessionStart" present
check "but no deployment path is invented"          "${OUT:-<empty>}" "Deployment settings" absent
check "and no run report is invented"               "${OUT:-<empty>}" "Still in flight" absent

echo

# ---------------------------------------------------------------------------
# The wrong shell, said once per conversation.
#
# The hook's rule is silence where no deployment exists - correct everywhere
# except here, because under Git Bash there may well BE a deployment, in a home
# directory this shell cannot open. That is the one case where silence is the
# wrong answer, and it was the case a member actually hit: the same "no
# settings file" every session, with nothing to distinguish it from a machine
# that had never run setup.
UB="$TMP/msysbin"; mkdir -p "$UB"
printf '#!/bin/sh\necho MINGW64_NT-10.0-22631\n' > "$UB/uname"; chmod +x "$UB/uname"

msys_run() { # msys_run <reason> <settings-file>
  printf '{"session_start_reason":"%s"}' "$1" \
    | env PATH="$UB:$PATH" LAB_SETTINGS_FILE="$2" TW_BIN="$TMP/tw_idle" \
          TOWER_WORKSPACE_ID=12345 SEQERA_TOKEN_FILE="$TMP/.seqera_token" bash "$H"
}

out=$(msys_run startup "$TMP/does-not-exist.yaml"); rc=$?
check "with no settings file, MSYS is still told"     "$out" "Git Bash (MSYS)" present
check "and told what it costs, measured"             "$out" "PITFALLS 16b"    present
check "and told the move"                            "$out" "WSL"             present
printf '%-52s ' "and the hook still exits 0"
[ "$rc" = 0 ] && echo "ok" || { echo "FAIL: rc $rc"; fails=$((fails+1)); }

out=$(msys_run resume "$TMP/does-not-exist.yaml")
check "a resume is told too - a compaction loses it"  "$out" "Git Bash (MSYS)" present

out=$(msys_run startup "$TMP/env.yaml")
check "a working deployment is told as well"          "$out" "Git Bash (MSYS)" present
check "and still gets its settings path"              "$out" "Deployment settings" present

# The negative that keeps it from becoming noise everywhere else.
out=$(run startup "$TMP/does-not-exist.yaml")
check "on Linux with no settings, still silent"       "$out" "Git Bash"        absent
out=$(run startup "$TMP/env.yaml" "$TMP/tw_idle")
check "and a Linux deployment hears nothing of it"    "$out" "Git Bash"        absent

echo

# ---------------------------------------------------------------------------
# U1: scripts/intro.sh's output must land in BOTH systemMessage (shown to the
# user directly) and additionalContext (given to the model), on every
# startup/resume, with or without a settings file - and NOT on compaction.
#
# scripts/intro.sh belongs to a sibling track and may still be edited after
# this file is written, so this does not depend on its actual wording - only
# on the WIRING. The seam: a small copy of the plugin root with the real
# hooks/session_start.sh and scripts/settings.sh(+utils/portable.sh), and a
# STUB scripts/intro.sh that prints one unmistakable marker.
UROOT="$TMP/u1plugin"
mkdir -p "$UROOT/hooks" "$UROOT/scripts/utils"
cp "$ROOT/hooks/session_start.sh" "$UROOT/hooks/"
cp "$ROOT/scripts/settings.sh" "$UROOT/scripts/"
cp "$ROOT/scripts/utils/portable.sh" "$UROOT/scripts/utils/"
cat > "$UROOT/scripts/intro.sh" <<'EOF'
#!/bin/bash
[ $# -eq 0 ] || exit 2
echo "STUB-OVERVIEW-MARKER: what this plugin is, five commands, next step"
EOF
chmod +x "$UROOT/scripts/intro.sh" "$UROOT/hooks/session_start.sh"

u1_run() { # u1_run <reason> <settings-file> [tw-stub]
  printf '{"session_start_reason":"%s"}' "$1" \
    | LAB_SETTINGS_FILE="$2" TW_BIN="${3:-$TMP/tw}" TOWER_WORKSPACE_ID=12345 \
      SEQERA_TOKEN_FILE="$TMP/.seqera_token" bash "$UROOT/hooks/session_start.sh"
}

json_field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(sys.argv[1],'') if len(sys.argv)==2 else d.get(sys.argv[1],{}).get(sys.argv[2],''))" "$@"; }

OUT=$(u1_run startup "$TMP/env.yaml")
printf '%-52s ' "U1: intro marker lands in additionalContext"
ctx=$(echo "$OUT" | json_field hookSpecificOutput additionalContext)
echo "$ctx" | grep -qF "STUB-OVERVIEW-MARKER" && echo ok || { echo "FAIL: <<$ctx>>"; fails=$((fails+1)); }

printf '%-52s ' "U1: intro marker ALSO lands in systemMessage"
sysmsg=$(echo "$OUT" | json_field systemMessage)
echo "$sysmsg" | grep -qF "STUB-OVERVIEW-MARKER" && echo ok || { echo "FAIL: <<$sysmsg>>"; fails=$((fails+1)); }

printf '%-52s ' "U1: run info is still in additionalContext alongside it"
echo "$ctx" | grep -qF "aliveRUN123" && echo ok || { echo "FAIL: <<$ctx>>"; fails=$((fails+1)); }

OUT=$(u1_run startup "$TMP/no_such_settings.yaml")
printf '%-52s ' "U1: intro appears even with NO settings file (first-time user)"
sysmsg=$(echo "$OUT" | json_field systemMessage)
echo "$sysmsg" | grep -qF "STUB-OVERVIEW-MARKER" && echo ok || { echo "FAIL: <<$sysmsg>>"; fails=$((fails+1)); }

OUT=$(u1_run startup "$TMP/no_such_settings.yaml" "$TMP/tw_idle")
printf '%-52s ' "U1: (recheck) intro appears with no settings, idle tw"
sysmsg=$(echo "$OUT" | json_field systemMessage)
echo "$sysmsg" | grep -qF "STUB-OVERVIEW-MARKER" && echo ok || { echo "FAIL: <<$sysmsg>>"; fails=$((fails+1)); }

OUT=$(u1_run compact "$TMP/env.yaml")
check "U1: still silent on compaction, even with the intro wired in" "${OUT:-<empty>}" "STUB-OVERVIEW-MARKER" absent

echo

# ---------------------------------------------------------------------------
# Z3: the outputs-reader check only means something under reach: local. Reuse
# the u1plugin seam (real session_start.sh + settings.sh, stub intro.sh) so
# the assertions below are about THIS hook's gating logic, not about whatever
# scripts/agent_ctl.sh happens to do when LAB_RUNS_DIR is unset (it always
# fails in that case, which is exactly what makes this a useful seam: under
# reach: local the failure must still be reported, and under ssh/none it must
# not, even though agent_ctl.sh fails identically both times).
z3settings() { # z3settings <file> <reach-value-or-empty>
    { printf 'workspace_id: 12345\ntw_bin: %s/tw\n' "$TMP"
      [ -n "$2" ] && printf 'reach: %s\n' "$2"; } > "$1"
}
z3settings "$TMP/z3_ssh.yaml"   ssh
z3settings "$TMP/z3_none.yaml"  none
z3settings "$TMP/z3_local.yaml" local

z3_run() { # z3_run <settings-file>
  printf '{"session_start_reason":"startup"}' \
    | env -u LAB_RUNS_DIR LAB_SETTINGS_FILE="$1" TW_BIN="$TMP/tw" TOWER_WORKSPACE_ID=12345 \
          SEQERA_TOKEN_FILE="$TMP/.seqera_token" bash "$UROOT/hooks/session_start.sh"
}

OUT=$(z3_run "$TMP/z3_ssh.yaml")
check "Z3: reach ssh - outputs-reader check not even attempted"  "${OUT:-<empty>}" "outputs reader is not running" absent

OUT=$(z3_run "$TMP/z3_none.yaml")
check "Z3: reach none - same"                                    "${OUT:-<empty>}" "outputs reader is not running" absent

OUT=$(z3_run "$TMP/z3_local.yaml")
check "Z3: reach local - warning UNCHANGED (agent_ctl.sh really is unreachable here)" \
      "${OUT:-<empty>}" "outputs reader is not running" present

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
