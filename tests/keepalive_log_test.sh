#!/bin/bash
# Tests for scripts/keepalive_log.sh (mcp-site-keepalive-disconnect-ux, TC-061..TC-070, TC-091, TC-096).
# Nothing existing: no test covers a loop that only records `on_site.sh --check-master`; the log format is this task's.
K="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/keepalive_log.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
check() { printf '%-64s ' "$1"; if [ "$2" = 0 ]; then echo ok; else echo FAIL; fails=$((fails+1)); fi; }

# a fake on_site.sh: logs its arguments, answers the next code of $TMP/codes (one per line), 0 once the list is used up
cat > "$TMP/on_site.sh" <<'FAKE'
#!/bin/bash
D="$(dirname "${BASH_SOURCE[0]}")"
echo "$*" >> "$D/args.log"
n=$(( $(cat "$D/n" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$D/n"
c=$(sed -n "${n}p" "$D/codes" 2>/dev/null); exit "${c:-0}"
FAKE
chmod +x "$TMP/on_site.sh"
# a fake ssh that must never be called
mkdir -p "$TMP/bin"; printf '#!/bin/bash\necho called >> "%s/ssh.called"\nexit 0\n' "$TMP" > "$TMP/bin/ssh"; chmod +x "$TMP/bin/ssh"

LOG="$TMP/k.log"
fresh() { rm -f "$LOG" "$LOG.1" "$TMP/n" "$TMP/args.log"; printf '%s\n' "$@" > "$TMP/codes"; }
go() { PATH="$TMP/bin:$PATH" ABF_KEEPALIVE_ON_SITE="$TMP/on_site.sh" ABF_KEEPALIVE_LOG="$LOG" ABF_KEEPALIVE_INTERVAL=0 "$@" bash "$K" 2>&1; }
once() { ABF_KEEPALIVE_ONCE=1 go env; }
rounds() { ABF_KEEPALIVE_ROUNDS="$1" go env; }

# TC-061, TC-063: one run, one line, open, rc 0, key=value with an ISO8601 time that has a zone
fresh 0; once >/dev/null
check "TC-061: ONCE writes exactly one line" "$([ "$(wc -l < "$LOG")" = 1 ]; echo $?)"
check "TC-061: line says master=open rc=0" "$(grep -q 'master=open rc=0' "$LOG"; echo $?)"
check "TC-063: ts= ISO8601 with a zone" "$(grep -Eq '^ts=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:?[0-9]{2}) ' "$LOG"; echo $?)"
check "TC-063: machine=<hostname>" "$(grep -q " machine=$(hostname) " "$LOG"; echo $?)"

# TC-062: closed
fresh 1; once >/dev/null
check "TC-062: rc 1 -> master=closed rc=1" "$(grep -q 'master=closed rc=1' "$LOG"; echo $?)"
check "TC-062: a first sight of closed has no event" "$(! grep -q 'event=' "$LOG"; echo $?)"

# TC-064: open then closed -> event=closed with lasted_min and last_open
fresh 0 1; rounds 2 >/dev/null
check "TC-064: two rounds, three lines" "$([ "$(wc -l < "$LOG")" = 3 ]; echo $?)"
check "TC-064: event=closed lasted_min= last_open=<ISO>" "$(grep -Eq 'event=closed lasted_min=[0-9]+ last_open=[0-9]{4}-[0-9]{2}-[0-9]{2}T' "$LOG"; echo $?)"

# TC-065: closed then open again -> event=reopened
fresh 0 1 0; rounds 3 >/dev/null
check "TC-065: event=reopened after closed" "$(grep -q 'event=reopened' "$LOG"; echo $?)"
check "TC-065: reopened only once" "$([ "$(grep -c 'event=reopened' "$LOG")" = 1 ]; echo $?)"

# TC-066: more than 1 MB -> renamed to .1, new file goes on
fresh 0; head -c 1100000 /dev/zero | tr '\0' 'x' > "$LOG"
once >/dev/null
check "TC-066: old log became .1" "$([ -f "$LOG.1" ] && [ "$(wc -c < "$LOG.1")" -gt 1048576 ]; echo $?)"
check "TC-066: new log holds the new line only" "$([ "$(wc -l < "$LOG")" = 1 ] && grep -q 'master=open' "$LOG"; echo $?)"

# TC-067, TC-091: only on_site.sh --check-master; ssh never called; no ssh command in the script
fresh 0 0; rounds 2 >/dev/null
check "TC-067: on_site.sh got only --check-master" "$([ "$(sort -u "$TMP/args.log")" = "--check-master" ]; echo $?)"
check "TC-067: the fake ssh was never called" "$([ ! -e "$TMP/ssh.called" ]; echo $?)"
check "TC-067: the script has no ssh command of its own" "$(! grep -Ev '^[[:space:]]*#' "$K" | grep -Eq '(^|[^A-Za-z_.-])ssh([[:space:]]|$)|ControlMaster|ControlPersist'; echo $?)"
check "TC-091: the script writes only its log (no sed -i / on_site.sh edit)" "$(! grep -Ev '^[[:space:]]*#' "$K" | grep -Eq 'sed -i|>>? *"?\$?\{?ON_SITE'; echo $?)"

# TC-068: defaults
check "TC-068: default interval 600 and ABF_KEEPALIVE_INTERVAL override" "$(grep -q 'ABF_KEEPALIVE_INTERVAL:-600' "$K"; echo $?)"
check "TC-068: default log is \$HOME/.abf/keepalive.log" "$(grep -q 'ABF_KEEPALIVE_LOG:-\$HOME/.abf/keepalive.log' "$K"; echo $?)"
fresh 0; s=$(date +%s); ABF_KEEPALIVE_INTERVAL=30 ABF_KEEPALIVE_ONCE=1 PATH="$TMP/bin:$PATH" ABF_KEEPALIVE_ON_SITE="$TMP/on_site.sh" ABF_KEEPALIVE_LOG="$LOG" bash "$K" >/dev/null 2>&1
check "TC-068: ONCE does not sleep" "$([ $(( $(date +%s) - s )) -lt 10 ]; echo $?)"

# TC-069: kill stops it
fresh 0; PATH="$TMP/bin:$PATH" ABF_KEEPALIVE_ON_SITE="$TMP/on_site.sh" ABF_KEEPALIVE_LOG="$LOG" ABF_KEEPALIVE_INTERVAL=30 bash "$K" >/dev/null 2>&1 &
pid=$!; sleep 1; kill "$pid" 2>/dev/null; sleep 1
check "TC-069: kill stops the loop" "$(! kill -0 "$pid" 2>/dev/null; echo $?)"
for f in platform/abf_platform platform/abf_station; do :; done
R="$(cd "$(dirname "$K")/.." && pwd)"
check "TC-069: nothing in platform code starts keepalive_log.sh" "$(! grep -rq 'keepalive_log' "$R/platform/abf_platform" "$R/platform/abf_station" --include=*.py; echo $?)"

# TC-070, TC-096: no OTP or credential handling, the log holds only the named fields
fresh 0 1 0; rounds 3 >/dev/null
check "TC-070: only ts machine master rc event lasted_min last_open" "$(! sed -E 's/ts=[^ ]+//; s/machine=[^ ]+//; s/master=[a-z]+//; s/rc=[0-9]+//; s/event=[a-z]+//; s/lasted_min=[0-9]+//; s/last_open=[^ ]+//; s/[[:space:]]//g' "$LOG" | grep -q .; echo $?)"
check "TC-096: no token/password/OTP in the log" "$(! grep -Eqi 'token|password|otp|secret' "$LOG"; echo $?)"
check "TC-070: the script never asks for a code" "$(! grep -Ev '^[[:space:]]*#' "$K" | grep -Eqi 'read -|otp|password'; echo $?)"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
