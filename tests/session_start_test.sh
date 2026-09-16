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

# R5 (2.9): the stub now answers `-o json runs list` the way tw 0.40.0
# actually does, measured on the login node against a real workspace -
# `{"workflows":[{"workflow":{"id":..., "status":..., "projectName":...,
# "runName":..., ...}}]}`. session_start.sh no longer parses the human table
# at all, so a table-shaped stub would no longer exercise the code path this
# file tests - it is JSON, not a fallback for one.
cat > "$TMP/tw" <<'STUB'
#!/bin/bash
cat <<'OUT'
{
  "workspaceRef": "[Lab / site]",
  "workflows": [
    {"workflow": {"id": "aliveRUN123",  "status": "RUNNING",   "projectName": "nf-core/rnaseq",   "runName": "nightly-run"}},
    {"workflow": {"id": "queuedSUB456", "status": "SUBMITTED", "projectName": "nf-core/ampliseq", "runName": "waiting-run"}},
    {"workflow": {"id": "doneOK789",    "status": "SUCCEEDED", "projectName": "nf-core/funcscan",  "runName": "finished-run"}}
  ]
}
OUT
STUB
chmod +x "$TMP/tw"

# A second stub for the workspace with nothing in it. The hook's other job -
# saying where the settings live - has to survive a quiet workspace, which is
# the ordinary case.
cat > "$TMP/tw_idle" <<'STUB'
#!/bin/bash
cat <<'OUT'
{"workspaceRef": "[Lab / site]", "workflows": []}
OUT
STUB
chmod +x "$TMP/tw_idle"

# R5 mutation-proof: the same three runs, but with every object's keys in a
# DIFFERENT order and the array itself in a different order too. The old
# `awk -F'|'` read status/id/project/name by COLUMN POSITION, so a reordered
# table would have silently attributed the wrong field to the wrong run - a
# column reorder was exactly the failure mode a human-table parser could not
# see coming. JSON has no column order at all (jq selects by key name), so
# this stub is not "the same test as tw twice" - it is the case that would
# have broken the old parser and cannot break this one.
cat > "$TMP/tw_reordered" <<'STUB'
#!/bin/bash
cat <<'OUT'
{
  "workflows": [
    {"workflow": {"runName": "finished-run", "status": "SUCCEEDED", "id": "doneOK789", "projectName": "nf-core/funcscan"}},
    {"workflow": {"projectName": "nf-core/ampliseq", "id": "queuedSUB456", "runName": "waiting-run", "status": "SUBMITTED"}},
    {"workflow": {"status": "RUNNING", "runName": "nightly-run", "projectName": "nf-core/rnaseq", "id": "aliveRUN123"}}
  ],
  "workspaceRef": "[Lab / site]"
}
OUT
STUB
chmod +x "$TMP/tw_reordered"

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

OUT=$(run startup "$TMP/env.yaml" "$TMP/tw_reordered")
check "R5: a key/array reorder still reports the RUNNING run"   "$OUT" "aliveRUN123"  present
check "R5: and the SUBMITTED run"                                "$OUT" "queuedSUB456" present
check "R5: still says nothing about the SUCCEEDED one"           "$OUT" "doneOK789"    absent
check "R5: and gets that run's own project name right"           "$OUT" "nf-core/rnaseq" present

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

# A machine with no deployment hears nothing at all. (For a while this printed
# the plugin overview; that moved to hooks/plugin_intro.sh, which shows it when
# the plugin is actually used, not in every conversation.)
OUT=$(run startup "$TMP/no_such_settings.yaml" "$TMP/tw_idle")
check "no deployment: completely silent" "${OUT:-<empty>}" "SessionStart" absent
check "no deployment path is invented"   "${OUT:-<empty>}" "Deployment settings" absent

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
check "and told the bridge was measured too"         "$out" "PITFALLS 16g"    present
check "and told the reason that still holds"         "$out" "python3"         present
check "and told the move"                            "$out" "WSL"             present
check "and no longer told the site is unreachable"   "$out" "cannot reach the cluster" absent
check "and told the project does not have to move"   "$out" "does not have to move" present
# 2.13 (D2): the fix used to be "open a WSL shell and move the window there" -
# exactly the instruction plan section D2 retires. It's WSL that's missing,
# not a different window to run Claude Code in.
check "no longer prescribes opening a WSL shell to move into" "$out" "Open a WSL shell" absent
check "names the install command instead"                     "$out" "wsl --install"    present
# PITFALLS 25: deleted once already by an earlier release and had to be
# restored (D2's own instruction) - pinned explicitly so a future edit that
# drops it again turns this line red rather than merely losing the sentence.
check "the PITFALLS 25 fact is still present"                  "$out" "PITFALLS 25"      present
check "and its 'not found does not mean not set up' line survives" \
      "$out" "does not mean 'not set up'" present
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
# 2.13 (D2 + C1 together): once detect_conditions.sh actually measures a WSL
# bridge, the Condition line it feeds into this hook's output changes from
# `unsupported-msys-no-wsl` to `supported` and stops appearing at all (the
# hook only speaks about the condition when status != supported) - and
# regardless of which of those two a given machine lands on, this hook's own
# static SHELLWARN text must never say "Start Claude Code from a WSL shell"
# again, because that phrase is exactly what 2.13 retires (see D2 above).
SSHF_MSYS="$TMP/env_ssh_msys.yaml"
printf 'workspace_id: 12345\ntw_bin: %s/tw_idle\nreach: ssh\n' "$TMP" > "$SSHF_MSYS"
chmod 600 "$SSHF_MSYS"

WSLBIN="$TMP/wslbin"; mkdir -p "$WSLBIN"
cat > "$WSLBIN/wsl.exe" <<'EOF'
#!/bin/bash
if [ "$1" = -e ]; then shift; "$@"; exit $?; fi
exit 1
EOF
chmod +x "$WSLBIN/wsl.exe"

msys_bridge_run() { # msys_bridge_run <reason> <settings-file>
  printf '{"session_start_reason":"%s"}' "$1" \
    | env PATH="$UB:$WSLBIN:$PATH" LAB_SETTINGS_FILE="$2" TW_BIN="$TMP/tw_idle" \
          TOWER_WORKSPACE_ID=12345 SEQERA_TOKEN_FILE="$TMP/.seqera_token" bash "$H"
}

out=$(msys_bridge_run startup "$SSHF_MSYS")
check "bridge available: no Condition line at all (falls through to supported)" "$out" "Condition:" absent
check "bridge available: never says to start Claude Code from a WSL shell"      "$out" "Start Claude Code from a WSL shell" absent
check "bridge available: still told this is Git Bash (MSYS), via SHELLWARN"     "$out" "Git Bash (MSYS)" present
check "bridge available: PITFALLS 25 fact is still there too"                   "$out" "PITFALLS 25" present

out=$(msys_run startup "$SSHF_MSYS")
check "no bridge + reach=ssh: Condition line names unsupported-msys-no-wsl"    "$out" "unsupported-msys-no-wsl" present
check "no bridge + reach=ssh: still never says to start Claude Code elsewhere" "$out" "Start Claude Code from a WSL shell" absent
check "no bridge + reach=ssh: PITFALLS 25 fact is still there"                 "$out" "PITFALLS 25" present

echo

# ---------------------------------------------------------------------------
# The overview is not shown at session start (it moved to plugin_intro.sh).
# Proven against a STUB scripts/intro.sh printing one marker, in a small copy
# of the plugin root with the real session_start.sh and settings.sh - so this
# fails if anything here starts calling intro.sh again, whatever its wording.
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

for case in "startup $TMP/env.yaml" "startup $TMP/no_such_settings.yaml" "resume $TMP/env.yaml"; do
  set -- $case
  OUT=$(u1_run "$1" "$2")
  check "no overview at session start ($1, $(basename "$2"))" "${OUT:-<empty>}" "STUB-OVERVIEW-MARKER" absent
  check "and no systemMessage at all ($1, $(basename "$2"))"   "${OUT:-<empty>}" "systemMessage" absent
done
OUT=$(u1_run startup "$TMP/env.yaml")
check "runs are still reported" "$OUT" "aliveRUN123" present

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

# --- 2.8: the condition cell and unsent reports ------------------------------
# Only a cell that is not `supported` is worth a line; the ordinary case stays
# as quiet as before. Unsent off-design reports are counted on every start,
# resume included, because a compaction may have carried the first reminder
# away. The hook only reads the queue - it never writes it.
printf 'workspace_id: 12345\ntw_bin: %s/tw_idle\nreach: none\n' "$TMP" > "$TMP/c_none.yaml"
chmod 600 "$TMP/c_none.yaml"
OUT=$(run startup "$TMP/c_none.yaml" "$TMP/tw_idle")
check "2.8: an unsupported cell is named"             "${OUT:-<empty>}" "unsupported-cloud-ce" present
OUT=$(run startup "$TMP/env.yaml" "$TMP/tw_idle")
check "2.8: a supported cell says nothing about it"   "${OUT:-<empty>}" "Condition:" absent

mkdir -p "$TMP/reports"
: > "$TMP/reports/1-1-aaaaaaaaaaaa.report"; : > "$TMP/reports/2-2-bbbbbbbbbbbb.report"
OUT=$(run startup "$TMP/env.yaml" "$TMP/tw_idle")
check "2.8: unsent reports are counted"               "${OUT:-<empty>}" "2 off-design report(s) not sent" present
OUT=$(run resume "$TMP/env.yaml" "$TMP/tw_idle")
check "2.8: and again on resume"                      "${OUT:-<empty>}" "2 off-design report(s) not sent" present
before=$(ls "$TMP/reports" | wc -l)
run startup "$TMP/env.yaml" "$TMP/tw_idle" >/dev/null
after=$(ls "$TMP/reports" | wc -l)
check "2.8: the queue is only read"                   "$before=$after" "2=2" present
command rm -rf "$TMP/reports"
OUT=$(run resume "$TMP/env.yaml" "$TMP/tw_idle")
check "2.8: no queue, no line"                        "${OUT:-<empty>}" "not sent" absent

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
