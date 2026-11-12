#!/bin/bash
# Tests for scripts/keepalive_log.sh (mcp-site-keepalive-disconnect-ux, TC-061..TC-070, TC-091, TC-096).
# Nothing existing: no test covers a script that only records `on_site.sh --check-master`; the log format is this task's.
K="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/keepalive_log.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
check() { printf '%-72s ' "$1"; if [ "$2" = 0 ]; then echo ok; else echo FAIL; fails=$((fails+1)); fi; }

# a fake on_site.sh: logs its arguments, answers the next code of its own folder's `codes` (one per line), 0 once the list is used up
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
# one call = one check = one line (lead ruling 2026-11-11: nothing stays resident)
go() { PATH="$TMP/bin:$PATH" ABF_KEEPALIVE_ON_SITE="$TMP/on_site.sh" ABF_KEEPALIVE_LOG="$LOG" "$@" bash "$K" 2>&1; }
once() { ABF_KEEPALIVE_ONCE=1 go env; }
calls() { local i; for i in $(seq "$1"); do go env; done; }

# TC-061, TC-063: one call, one line, open, rc 0, key=value with an ISO8601 time that has a zone
fresh 0; once >/dev/null
check "TC-061: one call writes exactly one line" "$([ "$(wc -l < "$LOG")" = 1 ]; echo $?)"
check "TC-061: line says master=open rc=0" "$(grep -q 'master=open rc=0' "$LOG"; echo $?)"
check "TC-063: ts= ISO8601 with a zone" "$(grep -Eq '^ts=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:?[0-9]{2}) ' "$LOG"; echo $?)"
check "TC-063: machine=<hostname>" "$(grep -q " machine=$(hostname) " "$LOG"; echo $?)"

# TC-062: closed
fresh 1; once >/dev/null
check "TC-062: rc 1 -> master=closed rc=1" "$(grep -q 'master=closed rc=1' "$LOG"; echo $?)"
check "TC-062: a first sight of closed has no event" "$(! grep -q 'event=' "$LOG"; echo $?)"

# TC-064: open on one call, closed on the next -> event=closed with lasted_min and last_open
fresh 0 1; calls 2 >/dev/null
check "TC-064: two calls, three lines" "$([ "$(wc -l < "$LOG")" = 3 ]; echo $?)"
check "TC-064: event=closed lasted_min= last_open=<ISO>" "$(grep -Eq 'event=closed lasted_min=[0-9]+ last_open=[0-9]{4}-[0-9]{2}-[0-9]{2}T' "$LOG"; echo $?)"
check "TC-064: last_open is the time of the open line" "$([ -n "$(sed -n 's/.* last_open=//p' "$LOG")" ] && [ "$(sed -n 's/.* last_open=//p' "$LOG")" = "$(sed -n '1s/^ts=\([^ ]*\) .*/\1/p' "$LOG")" ]; echo $?)"
# TC-064, TC-068: the minutes are counted from the log (the first open of this open stretch), not from memory
OLD=1767225600   # 2026-01-01T00:00:00Z
fresh 1
printf '%s\n' "ts=2025-12-31T00:00:00+00:00 machine=m master=closed rc=1" \
              "ts=2026-01-01T08:00:00+08:00 machine=m master=open rc=0" \
              "ts=2026-01-02T00:00:00+00:00 machine=m master=open rc=0" > "$LOG"
want=$(( ($(date +%s) - OLD) / 60 )); go env >/dev/null
got=$(sed -n 's/.*event=closed lasted_min=\([0-9]*\) .*/\1/p' "$LOG")
check "TC-064: lasted_min counts from the first open after the last closed" "$([ -n "$got" ] && [ "$got" -ge "$want" ] && [ "$got" -le $((want + 1)) ]; echo $?)"
check "TC-064: last_open is that first open, zone kept" "$(grep -q 'event=closed lasted_min=[0-9]* last_open=2026-01-01T08:00:00+08:00$' "$LOG"; echo $?)"
fresh 1 1; calls 2 >/dev/null
check "TC-064: closed seen again writes no event" "$([ "$(wc -l < "$LOG")" = 2 ] && ! grep -q 'event=' "$LOG"; echo $?)"

# TC-065: closed then open again -> event=reopened
fresh 0 1 0 0; calls 4 >/dev/null
check "TC-065: event=reopened after closed" "$(grep -q 'event=reopened' "$LOG"; echo $?)"
check "TC-065: reopened only once" "$([ "$(grep -c 'event=reopened' "$LOG")" = 1 ]; echo $?)"

# TC-066: more than 1 MB -> renamed to .1, new file goes on
fresh 0; head -c 1100000 /dev/zero | tr '\0' 'x' > "$LOG"
once >/dev/null
check "TC-066: old log became .1" "$([ -f "$LOG.1" ] && [ "$(wc -c < "$LOG.1")" -gt 1048576 ]; echo $?)"
check "TC-066: new log holds the new line only" "$([ "$(wc -l < "$LOG")" = 1 ] && grep -q 'master=open' "$LOG"; echo $?)"
# what was last seen survives the rename: open before it, closed after it
fresh 0 1; go env >/dev/null; { head -c 1100000 /dev/zero | tr '\0' 'x'; echo; } >> "$LOG"; go env >/dev/null
check "TC-066: open before the rename, closed after it -> event=closed" "$([ -f "$LOG.1" ] && grep -q 'event=closed lasted_min=' "$LOG"; echo $?)"

# TC-067, TC-091: only on_site.sh --check-master; ssh never called; no ssh command in the script
fresh 0 0; calls 2 >/dev/null
check "TC-067: on_site.sh got only --check-master" "$([ "$(sort -u "$TMP/args.log")" = "--check-master" ]; echo $?)"
check "TC-067: one call asks once" "$([ "$(wc -l < "$TMP/args.log")" = 2 ]; echo $?)"
check "TC-067: the fake ssh was never called" "$([ ! -e "$TMP/ssh.called" ]; echo $?)"
check "TC-067: the script has no ssh command of its own" "$(! grep -Ev '^[[:space:]]*#' "$K" | grep -Eq '(^|[^A-Za-z_.-])ssh([[:space:]]|$)|ControlMaster|ControlPersist'; echo $?)"
check "TC-091: the script writes only its log (no sed -i / on_site.sh edit)" "$(! grep -Ev '^[[:space:]]*#' "$K" | grep -Eq 'sed -i|>>? *"?\$?\{?ON_SITE'; echo $?)"

# TC-068: no environment variable at all: a copy beside a fake on_site.sh, a scratch HOME; called twice, the second sees closed
R="$(cd "$(dirname "$K")/.." && pwd)"
mkdir -p "$TMP/s" "$TMP/home"; cp "$K" "$TMP/s/keepalive_log.sh"; cp "$TMP/on_site.sh" "$TMP/s/on_site.sh"; printf '0\n1\n' > "$TMP/s/codes"
bare() { env -u ABF_KEEPALIVE_LOG -u ABF_KEEPALIVE_ON_SITE -u ABF_KEEPALIVE_ONCE HOME="$TMP/home" PATH="$TMP/bin:$PATH" bash "$TMP/s/keepalive_log.sh" >/dev/null 2>&1; }
D="$TMP/home/.abf/keepalive.log"
bare
check "TC-068: default log is \$HOME/.abf/keepalive.log, one line a call" "$([ "$(wc -l < "$D" 2>/dev/null)" = 1 ] && grep -q 'master=open rc=0' "$D"; echo $?)"
bare
check "TC-068: the second call adds its line and the event line" "$([ "$(wc -l < "$D" 2>/dev/null)" = 3 ] && sed -n 2p "$D" | grep -q 'master=closed rc=1' && sed -n 3p "$D" | grep -q 'event=closed lasted_min=0 last_open='; echo $?)"
check "TC-068: ABF_KEEPALIVE_LOG overrides the default" "$(grep -q 'ABF_KEEPALIVE_LOG:-\$HOME/.abf/keepalive.log' "$K"; echo $?)"
check "TC-068: no while/until/loop/nohup/sleep anywhere in the script" "$(! grep -Eiq '(^|[^[:alnum:]_])(while|until|loop|nohup|sleep|setsid|disown)([^[:alnum:]_]|$)' "$K"; echo $?)"
check "TC-068: no interval or rounds knob is left" "$(! grep -Eq 'ABF_KEEPALIVE_(INTERVAL|ROUNDS)' "$K"; echo $?)"
check "TC-068: not in DAEMON_ALLOW" "$(! grep -q 'keepalive_log' "$R/tests/no_second_run_state_test.sh"; echo $?)"

# TC-069: the call ends by itself, nothing is left running, nothing starts it
fresh 0; s=$(date +%s); go env >/dev/null; rc=$?
check "TC-069: the call returns 0 at once" "$([ "$rc" = 0 ] && [ $(( $(date +%s) - s )) -lt 10 ]; echo $?)"
check "TC-069: nothing is put in the background" "$(! grep -Ev '^[[:space:]]*#' "$K" | grep -Eq '[^&>]&[[:space:]]*$|[^&>]&[[:space:]]+[^&>]'; echo $?)"
check "TC-069: nothing in platform code starts keepalive_log.sh" "$(! grep -rq 'keepalive_log' "$R/platform/abf_platform" "$R/platform/abf_station" --include=*.py; echo $?)"

# TC-070, TC-096: no OTP or credential handling, the log holds only the named fields
fresh 0 1 0; calls 3 >/dev/null
check "TC-070: only ts machine master rc event lasted_min last_open" "$(! sed -E 's/ts=[^ ]+//; s/machine=[^ ]+//; s/master=[a-z]+//; s/rc=[0-9]+//; s/event=[a-z]+//; s/lasted_min=[0-9]+//; s/last_open=[^ ]+//; s/[[:space:]]//g' "$LOG" | grep -q .; echo $?)"
check "TC-096: no token/password/OTP in the log" "$(! grep -Eqi 'token|password|otp|secret' "$LOG"; echo $?)"
check "TC-070: the script never asks for a code" "$(! grep -Ev '^[[:space:]]*#' "$K" | grep -Eqi 'read -|otp|password'; echo $?)"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
