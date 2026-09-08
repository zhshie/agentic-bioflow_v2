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

# The silence on a machine with no deployment is deliberate and stays: an
# unrelated project or someone else's laptop owes the user no explanation.
OUT=$(run startup "$TMP/no_such_settings.yaml" "$TMP/tw_idle")
check "and no path where there is no settings file" "${OUT:-<empty>}" "SessionStart" absent

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
