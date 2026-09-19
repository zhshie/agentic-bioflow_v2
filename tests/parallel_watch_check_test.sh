#!/bin/bash
# Guardrail 2 (T26): scripts/parallel_watch_check.sh warns before one more
# background watch would push this member's own in-flight run count close
# to ssh_max_parallel (PITFALLS.md 16e's session cap). Fakes `tw` so this
# runs with no real workspace and no network.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$ROOT/scripts/parallel_watch_check.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

has() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }

cat > "$TMP/tw" <<'EOF'
#!/bin/bash
case "$*" in
    *"runs list"*) cat "$RUNS_LIST_FILE" ;;
    *) exit 1 ;;
esac
EOF
chmod +x "$TMP/tw"
: > "$TMP/.seqera_token"

mk_runs() { # mk_runs <n active for alice>
    local n="$1" i out="$TMP/runs.json"
    printf '{"workflows":[' > "$out"
    for ((i=0; i<n; i++)); do
        [ "$i" -gt 0 ] && printf ',' >> "$out"
        printf '{"workflow":{"id":"r%d","runName":"run%d","projectName":"p","status":"RUNNING","userName":"alice"}}' "$i" "$i" >> "$out"
    done
    printf ']}' >> "$out"
}

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }

run() {
    LAB_SETTINGS_FILE="$TMP/env.yaml" RUNS_LIST_FILE="$TMP/runs.json" bash "$P" 2>&1
}

echo "== default cap (4): headroom below it is silent =="
settings 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' 'seqera_user: alice' "tw_bin: $TMP/tw" 'language: en'
mk_runs 2
out=$(run); rc=$?
printf '%-64s ' "2 active runs: exit 0"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-64s ' "2 active runs: prints nothing"
[ -z "$out" ] && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

echo
echo "== default cap (4): 3 active runs is 'one more push' - warns =="
mk_runs 3
out=$(run); rc=$?
printf '%-64s ' "exit 1 (a warning was printed)"
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
has "names the count"       "3" "$out"
has "names the configured max" "4" "$out"

echo
echo "== a lower configured max warns sooner =="
settings 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' 'seqera_user: alice' "tw_bin: $TMP/tw" 'ssh_max_parallel: 2' 'language: en'
mk_runs 1
out=$(run); rc=$?
printf '%-64s ' "1 active run against a cap of 2: exit 1"
[ "$rc" = 1 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
has "names the lower max" "2" "$out"

echo
echo "== bilingual output =="
settings 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' 'seqera_user: alice' "tw_bin: $TMP/tw" 'language: zh-TW'
mk_runs 3
out=$(run)
has "reads in zh-TW" "接近這個部署的" "$out"

echo
echo "== another member's runs are not counted against this one's headroom =="
printf '{"workflows":[{"workflow":{"id":"rb","runName":"bobs","projectName":"p","status":"RUNNING","userName":"bob"}}]}' > "$TMP/runs.json"
settings 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1' 'seqera_user: alice' "tw_bin: $TMP/tw" 'language: en'
out=$(run); rc=$?
printf '%-64s ' "exit 0 - bob's runs are not alice's headroom problem"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
