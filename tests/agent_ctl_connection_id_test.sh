#!/bin/bash
# The agent's connection identifier has to be unique across everyone using the
# workspace, and a second agent on an identifier already in use is refused
# permanently rather than intermittently (PITFALLS 2b). The old form -
# ${USER}-$(hostname -s)-$(date +%Y%m%d) - had no ingredient that varies per
# person at this site: the account is shared, and under reach=ssh the hostname
# is the login node's for everybody. Only the date was left, so two setups on
# one day collided in silence.
#
# Seam: `start` assigns the identifier before it validates agent_java, so a run
# with no agent_java gets all the way through the assignment and then stops.
# That needs no Java, no jar, no agent and no network.
A="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/agent_ctl.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
BIN="$TMP/bin"; mkdir -p "$BIN"
fails=0

ok()   { printf '%-56s ok\n' "$1"; }
bad()  { printf '%-56s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

# A stub tw that records what it was asked and answers with one credential
# belonging to somebody else - the shape `tw -o json credentials list` really
# returns, keys.connectionId and all.
cat > "$BIN/tw" <<'EOF'
#!/bin/bash
echo "$*" >> "$TWLOG"
cat <<'JSON'
{"credentials":[{"provider":"tw-agent","name":"someone-else",
  "keys":{"discriminator":"tw-agent","connectionId":"someone-elses-agent"}}]}
JSON
EOF
chmod +x "$BIN/tw"

# A run area with a token and a workspace, and nothing else: no agent_java, so
# `start` stops right after the assignment.
area() {
  local d="$TMP/$1"; mkdir -p "$d/_personal"
  echo "not-a-real-token" > "$d/_personal/.seqera_token"
  echo "workspace_id: 12345" > "$d/env.yaml"
  printf '%s' "$d"
}

run_start() { # run_start <area> [TW_BIN override]
  ( export LAB_RUNS_DIR="$1" LAB_SETTINGS_FILE="$1/env.yaml" \
           TWLOG="$TMP/tw.log" PATH="$BIN:$PATH"
    [ -n "${2:-}" ] && export TW_BIN="$2"
    bash "$A" start 2>&1 )
}
assigned() { sed -n 's/^assigned connection id: //p' <<<"$1"; }

# --- it no longer reduces to user + host + date ------------------------------
out1=$(run_start "$(area one)")
id1=$(assigned "$out1")
stale="${USER}-$(hostname -s)-$(date +%Y%m%d)"
if [ -z "$id1" ]; then bad "start assigns an identifier" "nothing assigned <<$out1>>"
elif [ "$id1" = "$stale" ]; then bad "identifier is more than user+host+date" "got the old form: $id1"
else ok "identifier is more than user+host+date"; fi

# --- two setups on one day get different identifiers -------------------------
# This is the whole bug. Same account, same host, same calendar day, and the
# two must still differ.
out2=$(run_start "$(area two)")
id2=$(assigned "$out2")
if [ -n "$id1" ] && [ "$id1" != "$id2" ]; then ok "two setups on one day differ"
else bad "two setups on one day differ" "both got '$id1'"; fi

# --- the workspace is asked before the name is committed ---------------------
if grep -q 'credentials list' "$TMP/tw.log" 2>/dev/null; then
  ok "the workspace is asked whether it is free"
else
  bad "the workspace is asked whether it is free" "tw was never called for it"
fi

# --- it is recorded where it will be read ------------------------------------
# `start` runs on the site; with reach=ssh the settings file that drives the
# next start is on the user's machine, and the copy written here is not it.
if grep -qF -- "settings.sh --set agent_connection $id1" <<<"$out1"; then
  ok "says how to record it where settings are read"
else
  bad "says how to record it where settings are read" "no --set line <<$out1>>"
fi

# --- a site that cannot ask still gets a unique identifier -------------------
# No tw, no token or no route out is survivable: the random tag is what makes
# the identifier unique, and the query is what makes it checked.
out3=$(run_start "$(area three)" /nonexistent/tw)
id3=$(assigned "$out3")
if [ -n "$id3" ] && [ "$id3" != "$id1" ]; then ok "assigns even when it cannot ask"
else bad "assigns even when it cannot ask" "<<$out3>>"; fi
if grep -qi "could not ask" <<<"$out3"; then ok "and says the check did not run"
else bad "and says the check did not run" "silent about it <<$out3>>"; fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
