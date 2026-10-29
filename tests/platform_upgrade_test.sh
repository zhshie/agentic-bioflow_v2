#!/bin/bash
# deploy/platform-upgrade.sh (specs/upgrade-agents-reconnect-check): after the upgrade restarts the
# platform services, every agent that was online before must say hello again, or the script names it
# and exits non-zero. Every scenario runs in a temporary folder with fake pull / install / restart
# commands; nothing here reaches systemd, the network or a site.
# Test cases: specs/upgrade-agents-reconnect-check/test-case.md (TC ids in the labels).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
fails=0
ok() { printf '%-92s ok\n' "$1"; }
bad() { printf '%-92s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
skip() { printf '%-92s skip%s\n' "$1" "${2:+: $2}"; }
check() { # <label> <command...>: ok when the command succeeds
  local label=$1; shift
  if "$@"; then ok "$label"; else bad "$label"; fi
}

UP=$ROOT/deploy/platform-upgrade.sh
OPS=docs/OPERATIONS.md

# a python that can import the platform (needs starlette)
TPY=""
for c in "${ABF_PLATFORM_VENV:-}/bin/python" "${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform-venv/bin/python" python3.13 python3.12 python3.11 python3.10 python3; do
  [ "$c" = "/bin/python" ] && continue
  if command -v "$c" >/dev/null 2>&1 && PYTHONPATH="$ROOT/platform" "$c" -c 'import sys, starlette; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then TPY=$c; break; fi
done
if [ -z "$TPY" ]; then skip "platform_upgrade_test" "no Python >= 3.10 with starlette on this machine"; exit 0; fi
TPY=$(command -v "$TPY")
export PYTHONPATH="$ROOT/platform${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1

TMP=$(mktemp -d "${TMPDIR:-/tmp}/abf-upgrade-test.XXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT

# helper: add / reconnect agents in a platform.db with the platform's own functions
cat > "$TMP/h.py" <<'PY'
import sys, time
from abf_platform import agents, store
cmd, state = sys.argv[1], sys.argv[2]
if cmd == "init":
    store.init_state(state)
elif cmd == "add":      # add <state> <name> [age_seconds] [owner]
    age = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    owner = int(sys.argv[5]) if len(sys.argv) > 5 else None
    store.init_state(state)
    agents.register(state, sys.argv[3], "1", clock=lambda: time.time() - age, owner_user_id=owner)
elif cmd == "reconnect":   # reconnect <state> <name>... ; a refused agent is not written (403)
    for n in sys.argv[3:]:
        try:
            agents.register(state, n, "1")
        except agents.OwnerMismatch:
            pass
elif cmd == "dump":
    import sqlite3
    c = sqlite3.connect(state)
    for r in c.execute("SELECT name, last_seen_at, owner_user_id FROM agents ORDER BY name"):
        print(r)
PY
H() { "$TPY" "$TMP/h.py" "$@"; }

new_case() { # <name> -> sets D (data folder), ST, TK, env defaults
  D=$TMP/$1; mkdir -p "$D/bin"; ST=$D/platform.db; TK=$D/tokens.db
  echo "SECRET_TOKEN_VALUE" > "$TK"
  MARK=$D/marks; : > "$MARK"
}
# run the script; sets RC and OUT. Extra env via the caller's `env` words in "$@" before the script args.
run_up() { # [VAR=val ...] -- [script args]
  local envs=() ; while [ $# -gt 0 ] && [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  OUT=$(env ABF_PLATFORM_STATE="$ST" ABF_PLATFORM_TOKENS="$TK" ABF_UPGRADE_PYTHON="$TPY" \
        ABF_UPGRADE_PULL_CMD="true" ABF_UPGRADE_INSTALL_CMD="true" ABF_UPGRADE_POLL_SECONDS=1 \
        "${envs[@]}" bash "$UP" "$@" 2>&1); RC=$?
}
reconn() { printf '"%s" "%s" reconnect "%s" %s' "$TPY" "$TMP/h.py" "$ST" "$*"; }
has() { printf '%s' "$OUT" | grep -qF -- "$1"; }

if [ ! -f "$UP" ]; then
  bad "TC-U8 deploy/platform-upgrade.sh exists" "missing"
fi

# ---- TC-U1 ----
new_case u1; H add "$ST" alpha; H add "$ST" beta
run_up "ABF_UPGRADE_RESTART_CMD=$(reconn alpha beta)" --
if [ $RC -eq 0 ] && has "2 agents reconnected"; then ok "TC-U1 both agents reconnect: rc 0, '2 agents reconnected'"; else bad "TC-U1" "rc=$RC $OUT"; fi
U1_OUT=$OUT

# ---- TC-U2 / TC-U9 / TC-U16 / TC-U32 / TC-U31 / TC-U35 ----
new_case u2; H add "$ST" alpha; H add "$ST" beta
mkdir -p "$D/fake"; for f in curl wget mail sendmail git; do printf '#!/bin/sh\necho "$0" >> "%s/called"\n' "$D" > "$D/fake/$f"; chmod +x "$D/fake/$f"; done
t0=$SECONDS
run_up "ABF_UPGRADE_RESTART_CMD=$(reconn alpha)" ABF_UPGRADE_WAIT_SECONDS=3 "PATH=$D/fake:$PATH" --
el=$((SECONDS-t0)); U2_OUT=$OUT; U2_RC=$RC
line=$(printf '%s\n' "$OUT" | grep -F '沒有重新連上' | head -n1)
if [ $RC -eq 1 ] && printf '%s' "$line" | grep -q beta && ! printf '%s' "$line" | grep -q alpha && [ $el -le 15 ]; then ok "TC-U2 only beta named (alpha reconnected), rc 1, ${el}s"; else bad "TC-U2" "rc=$RC el=$el out=$OUT"; fi
if ! printf '%s' "$OUT" | grep -q SECRET_TOKEN_VALUE; then ok "TC-U9 output has no token value"; else bad "TC-U9 token leaked"; fi
if has "這些代理人重啟後沒有重新連上" && has "abf-platform agent-token" && has "docs/TESTING.md" && has "日誌" && ! has "Traceback" && ! has "SELECT"; then ok "TC-U16 plain-language message with next steps"; else bad "TC-U16" "$OUT"; fi
# TC-H1 / TC-H2 / TC-H4: the section named in the hint exists as a "## " heading in docs/TESTING.md
sec=$(printf '%s\n' "$OUT" | grep -F '沒有重新連上' | head -n1 | sed -n 's/.*docs\/TESTING\.md 的「\([^」]*\)」一節.*/\1/p')
if [ -n "$sec" ] && grep -E '^## ' docs/TESTING.md | grep -qF -- "$sec" && has "docs/TESTING.md 的「Owner binding follow-up」一節第 2 步" && ! has "403 一節"; then ok "TC-H1/H2/H4 hint names a TESTING.md section that exists ($sec)"; else bad "TC-H1/H2/H4 hint section" "sec='$sec'"; fi
if [ ! -s "$D/called" ]; then ok "TC-U32 no curl/wget/mail called; TC-U31 no git called"; else bad "TC-U32/U31 fake tool called" "$(cat "$D/called")"; fi

# ---- TC-U3: 403 (owner mismatch) ----
new_case u3; H add "$ST" alpha; H add "$ST" beta 0 1
run_up "ABF_UPGRADE_RESTART_CMD=$(reconn alpha beta)" ABF_UPGRADE_WAIT_SECONDS=3 --
if [ $RC -eq 1 ] && has beta && ! has alpha; then ok "TC-U3 refused (403) beta named, alpha not, rc 1"; else bad "TC-U3" "rc=$RC $OUT"; fi
U3_OUT=$OUT; U3_RC=$RC

# ---- TC-U4: offline before the restart is not expected ----
new_case u4; H add "$ST" alpha; H add "$ST" gamma 1000
run_up "ABF_UPGRADE_RESTART_CMD=$(reconn alpha)" ABF_UPGRADE_WAIT_SECONDS=3 --
if [ $RC -eq 0 ] && ! has gamma; then ok "TC-U4 agent offline before restart is not a failure"; else bad "TC-U4" "rc=$RC $OUT"; fi

# ---- TC-U5: nobody ----
new_case u5; H init "$ST"
run_up ABF_UPGRADE_RESTART_CMD=true --
if [ $RC -eq 0 ] && has "沒有在線代理人可檢查"; then ok "TC-U5 no online agents: rc 0 with a note"; else bad "TC-U5" "rc=$RC $OUT"; fi

# ---- TC-U6: restart fails -> no waiting ----
new_case u6; H add "$ST" alpha
t0=$SECONDS
run_up ABF_UPGRADE_RESTART_CMD=false ABF_UPGRADE_WAIT_SECONDS=60 --
el=$((SECONDS-t0)); U6_OUT=$OUT; U6_RC=$RC
if [ $RC -ne 0 ] && [ $el -le 3 ]; then ok "TC-U6 restart failure: rc $RC in ${el}s, no waiting"; else bad "TC-U6" "rc=$RC el=$el"; fi

# ---- TC-U7: bounded wait ----
new_case u7; H add "$ST" alpha
t0=$SECONDS
run_up ABF_UPGRADE_RESTART_CMD=true ABF_UPGRADE_WAIT_SECONDS=2 --
el=$((SECONDS-t0))
if [ $RC -eq 1 ] && [ $el -le 6 ]; then ok "TC-U7 wait is bounded (${el}s), rc 1"; else bad "TC-U7" "rc=$RC el=$el"; fi

# ---- TC-U18: --wait N ----
new_case u18; H add "$ST" alpha
t0=$SECONDS
run_up ABF_UPGRADE_RESTART_CMD=true -- --wait 2
el=$((SECONDS-t0))
if [ $RC -eq 1 ] && [ $el -le 6 ]; then ok "TC-U18 --wait 2 ends in ${el}s, rc 1"; else bad "TC-U18" "rc=$RC el=$el"; fi

# ---- TC-U10: registered just before, same second ----
new_case u10; H add "$ST" beta
run_up ABF_UPGRADE_RESTART_CMD=true ABF_UPGRADE_WAIT_SECONDS=3 --
if [ $RC -eq 1 ] && has beta; then ok "TC-U10 a contact from before the restart is not a reconnect"; else bad "TC-U10" "rc=$RC $OUT"; fi

# ---- TC-U11 / TC-U12 / TC-U13 ----
new_case u11; H add "$ST" alpha
run_up ABF_UPGRADE_PULL_CMD=false "ABF_UPGRADE_INSTALL_CMD=touch $D/installed" "ABF_UPGRADE_RESTART_CMD=touch $D/restarted" --
U11_OUT=$OUT; U11_RC=$RC
if [ $RC -ne 0 ] && [ ! -e "$D/installed" ] && [ ! -e "$D/restarted" ]; then ok "TC-U11 pull failure stops before install and restart"; else bad "TC-U11" "rc=$RC"; fi
new_case u12; H add "$ST" alpha
run_up ABF_UPGRADE_INSTALL_CMD=false "ABF_UPGRADE_RESTART_CMD=touch $D/restarted" --
U12_OUT=$OUT; U12_RC=$RC
if [ $RC -ne 0 ] && [ ! -e "$D/restarted" ]; then ok "TC-U12 install failure stops before restart"; else bad "TC-U12" "rc=$RC"; fi
new_case u13; H add "$ST" alpha
run_up "ABF_UPGRADE_PULL_CMD=echo pull >> $D/order" "ABF_UPGRADE_INSTALL_CMD=echo install >> $D/order" "ABF_UPGRADE_RESTART_CMD=echo restart >> $D/order; $(reconn alpha)" --
if [ $RC -eq 0 ] && [ "$(cat "$D/order" 2>/dev/null | tr '\n' ' ')" = "pull install restart " ]; then ok "TC-U13 pull, install, restart once each in that order"; else bad "TC-U13" "rc=$RC $(cat "$D/order" 2>/dev/null | tr '\n' ' ')"; fi

# ---- TC-U15: reconnect arrives late ----
new_case u15; H add "$ST" alpha
run_up "ABF_UPGRADE_RESTART_CMD=( sleep 2; $(reconn alpha) ) &" ABF_UPGRADE_POLL_SECONDS=1 ABF_UPGRADE_WAIT_SECONDS=10 --
if [ $RC -eq 0 ] && has "1 agents reconnected"; then ok "TC-U15 waits for a late reconnect"; else bad "TC-U15" "rc=$RC $OUT"; fi

# ---- TC-U17: unknown option ----
new_case u17
run_up "ABF_UPGRADE_RESTART_CMD=touch $D/restarted" -- --bogus
U17_OUT=$OUT; U17_RC=$RC
if [ $RC -eq 2 ] && [ ! -e "$D/restarted" ] && has "--wait"; then ok "TC-U17 unknown option: rc 2, usage shown, nothing done"; else bad "TC-U17" "rc=$RC $OUT"; fi

# ---- TC-U19: ABF_PLATFORM_DB only ----
D=$TMP/u19; mkdir -p "$D/d"; ST=$D/d/platform.db; H add "$ST" alpha; H add "$ST" beta
OUT=$(env -u ABF_PLATFORM_STATE -u ABF_PLATFORM_TOKENS ABF_PLATFORM_DB="$D/d/index.db" ABF_UPGRADE_PYTHON="$TPY" ABF_UPGRADE_PULL_CMD=true ABF_UPGRADE_INSTALL_CMD=true ABF_UPGRADE_POLL_SECONDS=1 ABF_UPGRADE_RESTART_CMD="$(reconn alpha beta)" bash "$UP" 2>&1); RC=$?
if [ $RC -eq 0 ] && has "2 agents reconnected"; then ok "TC-U19 data folder found through ABF_PLATFORM_DB"; else bad "TC-U19" "rc=$RC $OUT"; fi
# ---- TC-U20: XDG_DATA_HOME only ----
D=$TMP/u20; mkdir -p "$D/x/abf-platform"; ST=$D/x/abf-platform/platform.db; H add "$ST" alpha; H add "$ST" beta
OUT=$(env -u ABF_PLATFORM_STATE -u ABF_PLATFORM_TOKENS -u ABF_PLATFORM_DB XDG_DATA_HOME="$D/x" ABF_UPGRADE_PYTHON="$TPY" ABF_UPGRADE_PULL_CMD=true ABF_UPGRADE_INSTALL_CMD=true ABF_UPGRADE_POLL_SECONDS=1 ABF_UPGRADE_RESTART_CMD="$(reconn alpha beta)" bash "$UP" 2>&1); RC=$?
if [ $RC -eq 0 ] && has "2 agents reconnected"; then ok "TC-U20 data folder found through XDG_DATA_HOME"; else bad "TC-U20" "rc=$RC $OUT"; fi

# ---- TC-U21: backup reminder ----
if printf '%s' "$U1_OUT" | grep -qiE 'backup|備份'; then ok "TC-U21 output reminds to back up"; else bad "TC-U21" "$U1_OUT"; fi

# ---- TC-U22 / TC-U29: read-only, no repair, no site ----
new_case u22; H add "$ST" alpha; H add "$ST" beta 0 1
before=$(H dump "$ST"); hb=$(cksum < "$TK")
mkdir -p "$D/fake"; for f in abf-platform scancel ssh; do printf '#!/bin/sh\necho "$0" >> "%s/called"\n' "$D" > "$D/fake/$f"; chmod +x "$D/fake/$f"; done
run_up ABF_UPGRADE_RESTART_CMD=true ABF_UPGRADE_WAIT_SECONDS=2 "PATH=$D/fake:$PATH" --
after=$(H dump "$ST"); ha=$(cksum < "$TK")
if [ "$before" = "$after" ] && [ "$hb" = "$ha" ] && [ $RC -eq 1 ]; then ok "TC-U22 agents table and tokens.db unchanged"; else bad "TC-U22" "rc=$RC"; fi
if [ ! -s "$D/called" ]; then ok "TC-U29 no abf-platform / scancel / ssh called (nothing repaired)"; else bad "TC-U29" "$(cat "$D/called")"; fi

# ---- static checks on the code (comments stripped) ----
if [ -f "$UP" ]; then CODE=$(grep -vE '^[[:space:]]*#' "$UP"); else CODE=""; fi
if [ -x "$UP" ] && [ "$(head -n1 "$UP" 2>/dev/null)" = '#!/usr/bin/env bash' ] && bash -n "$UP" 2>/dev/null && grep -q "^set -euo pipe""fail" "$UP" \
   && ! printf '%s\n' "$CODE" | grep -E '(^|[^A-Za-z])(curl|wget|scp|rsync|ssh|scancel)([^A-Za-z]|$)|(^|[^A-Za-z])rm |DELETE|UPDATE|INSERT' >/dev/null; then
  ok "TC-U8 executable, env-bash shebang, bash -n, strict-mode line, read-only vocabulary"
else bad "TC-U8 static checks"; fi
if printf '%s\n' "$CODE" | grep -q 'git pull' && printf '%s\n' "$CODE" | grep -qF 'pip install ./platform' && printf '%s\n' "$CODE" | grep -qF 'systemctl --user restart abf-serve abf-mcp abf-web' \
   && grep -qF 'git pull' "$OPS" && grep -qF 'pip install ./platform' "$OPS" && grep -qF 'systemctl --user restart abf-serve abf-mcp abf-web' "$OPS"; then ok "TC-U14 default commands are the ones in OPERATIONS.md"; else bad "TC-U14"; fi
if printf '%s\n' "$CODE" | grep -q 'list_agents' && ! printf '%s\n' "$CODE" | grep -qE 'SELECT|sqlite3'; then ok "TC-U23 reads agents through list_agents, no SQL of its own"; else bad "TC-U23"; fi
if ! printf '%s\n' "$CODE" | grep -qE 'git (reset|checkout|revert|stash)'; then ok "TC-U31 code has no git reset/checkout/revert/stash"; else bad "TC-U31 code"; fi
# TC-U33: backup.sh is never called, no backup folder appears
if ! printf '%s\n' "$CODE" | grep -qF 'backup.sh' && [ ! -e "$TMP/u1/abf-backup" ]; then ok "TC-U33 backup.sh is not called"; else bad "TC-U33"; fi
# TC-U34: found through BASH_SOURCE, run from elsewhere
new_case u34; H add "$ST" alpha; H add "$ST" beta; mkdir -p "$D/elsewhere"
OUT=$(cd "$D/elsewhere" && env ABF_PLATFORM_STATE="$ST" ABF_PLATFORM_TOKENS="$TK" ABF_UPGRADE_PYTHON="$TPY" ABF_UPGRADE_PULL_CMD=true ABF_UPGRADE_INSTALL_CMD=true ABF_UPGRADE_POLL_SECONDS=1 ABF_UPGRADE_RESTART_CMD="$(reconn alpha beta)" bash "$UP" 2>&1); RC=$?
if [ $RC -eq 0 ] && has "2 agents reconnected" && grep -q 'BASH_SOURCE' "$UP" && ! printf '%s\n' "$CODE" | grep -qE '(^|[^A-Za-z_])(pwd|\$PWD)'; then ok "TC-U34 works from any folder, located by BASH_SOURCE"; else bad "TC-U34" "rc=$RC $OUT"; fi

# ---- TC-U35: no silent failures ----
silent=""
for pair in "U2:$U2_RC:$U2_OUT" "U3:$U3_RC:$U3_OUT" "U6:$U6_RC:$U6_OUT" "U11:$U11_RC:$U11_OUT" "U12:$U12_RC:$U12_OUT" "U17:$U17_RC:$U17_OUT"; do
  n=${pair%%:*}; rest=${pair#*:}; rc=${rest%%:*}; o=${rest#*:}
  { [ "$rc" -ne 0 ] && [ -n "$o" ]; } || silent="$silent $n"
done
if [ -z "$silent" ]; then ok "TC-U35 every failure exits non-zero with a sentence"; else bad "TC-U35" "silent:$silent"; fi

# ---- docs and the neighbours ----
up_sec=$(awk '/^\*\*Upgrade\.\*\*/{on=1} on&&/^### /{exit} on{print}' "$OPS")
if printf '%s\n' "$up_sec" | grep -qF 'cd ~/<clone> && git pull' && printf '%s\n' "$up_sec" | grep -qF '~/$VENV/bin/pip install ./platform' \
   && printf '%s\n' "$up_sec" | grep -qF 'systemctl --user restart abf-serve abf-mcp abf-web' && printf '%s\n' "$up_sec" | grep -qF 'deploy/platform-upgrade.sh' \
   && [ "$(printf '%s\n' "$up_sec" | grep -nE 'git pull|pip install|systemctl' | cut -d: -f2 | cut -c1-3 | tr '\n' ' ')" != "" ]; then
  ok "TC-U24 Upgrade section keeps its three lines and points at the script"
else bad "TC-U24 OPERATIONS.md Upgrade section"; fi
if bash tests/hosted_deploy_test.sh >"$TMP/hd.out" 2>&1; then ok "TC-U24/U25/U30 hosted_deploy_test.sh is green"; else bad "TC-U25 hosted_deploy_test.sh" "$(grep FAIL "$TMP/hd.out" | head -3)"; fi

if mb=$(git merge-base origin/v3 HEAD 2>/dev/null) && git cat-file -e "$mb:tests/hosted_deploy_test.sh" 2>/dev/null; then
  d=$(git diff -U0 "$mb" -- tests/hosted_deploy_test.sh | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)')
  if [ "$(printf '%s\n' "$d" | grep -c '^-')" -eq 1 ] && [ "$(printf '%s\n' "$d" | grep -c '^+')" -eq 1 ] && printf '%s\n' "$d" | grep '^+' | grep -qF '$D/platform-upgrade.sh'; then ok "TC-U26 hosted_deploy_test.sh differs only by the want_list entry"; else bad "TC-U26" "$d"; fi
  ch=$(git diff --name-only "$mb" -- platform deploy/backup.sh deploy/systemd)
  if [ -z "$ch" ]; then ok "TC-U28 platform/, backup.sh and deploy/systemd untouched"; else bad "TC-U28" "$ch"; fi
else skip "TC-U26 / TC-U28" "no origin/v3"; fi

echo
[ "$fails" -eq 0 ] && echo "all platform_upgrade tests passed" || echo "$fails FAILED"
exit $((fails>0))
