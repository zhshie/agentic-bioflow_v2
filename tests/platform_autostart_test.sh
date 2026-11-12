#!/bin/bash
# platform-autostart: deploy/wsl/ - a supervisor script for the desktop (WSL) platform and a
# Windows logon-task installer. Test cases: specs/platform-autostart/test-case.md (TC ids in the
# labels). The supervisor cases run it against fake processes in a temporary folder with HOME and
# the state folder pointed there; nothing touches the real platform, the real home, or Windows.
# This file only ever signals processes it started itself: each one carries the environment
# marker ABFT_CASE=<its own case folder>, and a signal is sent to a pid only after that marker is
# read back from /proc/<pid>/environ. No name pattern is ever used to find a process to signal.
# The Windows task is never registered or removed here: the installer is only run without
# -Apply/-Remove, and only when powershell.exe is reachable (TC-004).
# Manual cases (TC-013, 014, 015, 034, 047, 055, 077, 114) live in docs/TESTING.md.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
W=deploy/wsl
SUP="$ROOT/$W/abf-supervise.sh"
INS="$ROOT/$W/install-autostart.ps1"
EX="$ROOT/$W/processes.example"
OPS=docs/OPERATIONS.md
JOBS=${PA_JOBS:-6}
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/abfpa.XXXXXX") || exit 1
mkdir -p "$TMPROOT/res" "$TMPROOT/msgs"

ok() { printf '%-96s ok\n' "$1"; }
bad() { printf '%-96s FAIL%s\n' "$1" "${2:+: $2}"; }
skip() { printf '%-96s skip%s\n' "$1" "${2:+: $2}"; }

# ------------------------------------------------------------------ process helpers
# every process a case starts carries ABFT_CASE=<case folder>; that is how we find our own.
carries() { grep -qazxF "ABFT_CASE=$1" "/proc/$2/environ" 2>/dev/null; }
procs_of() { # pids carrying the marker of case folder $1 (one grep over /proc, no per-process forks)
    grep -lazxF "ABFT_CASE=$1" /proc/[0-9]*/environ 2>/dev/null | sed -E 's|/proc/([0-9]+)/environ|\1|' | grep -vx "$$" || true
}
sweep() { # kill -9 every process of case folder $1 (found by the marker, never by name)
    local p; for p in $(procs_of "$1"); do kill -9 "$p" 2>/dev/null; done; return 0
}
count_procs() { procs_of "$1" | grep -c . || true; }
skill() { # skill SIG pid : only if the pid is one of this case's own
    if carries "$C" "$2"; then kill "$1" "$2" 2>/dev/null; else echo "refusing to signal $2: not ours" >&2; return 1; fi
}
cleanup() { local d; for d in "$TMPROOT"/c_*; do [ -d "$d" ] && sweep "$d"; done; chmod -R u+rwx "$TMPROOT" 2>/dev/null; rm -rf "$TMPROOT"; }
trap cleanup EXIT

wait_for() { local n=$(( $1 * 10 )); shift; while [ "$n" -gt 0 ]; do "$@" && return 0; sleep 0.1; n=$((n-1)); done; return 1; }
gone() { [ ! -d "/proc/$1" ] || grep -q '^State:[[:space:]]*Z' "/proc/$1/status" 2>/dev/null; }
alive() { ! gone "$1"; }

new_case() { # new_case <id>: a clean sandbox in $C; sets C ST LIST SE
    C="$TMPROOT/c_$1"; mkdir -p "$C/home" "$C/bin" "$C/pids" "$C/tmp"
    ST="$C/state"; LIST="$C/list"
    SE=(env "ABFT_CASE=$C" "HOME=$C/home" "TMPDIR=$C/tmp" "ABF_SUPERVISE_STATE=$ST"
        ABF_SUPERVISE_BASE=0.2 ABF_SUPERVISE_MAX=1.6 ABF_SUPERVISE_STABLE=1 ABF_SUPERVISE_WAIT=2 ABF_SUPERVISE_TICK=0.3)
    SUP_PID=""
}
mkfake() { # name [sleep]: records each start's pid, then sleeps (same pid)
    printf '#!/bin/sh\necho $$ >> "%s/pids/%s"\nexec sleep %s\n' "$C" "$1" "${2:-600}" > "$C/bin/$1"; chmod +x "$C/bin/$1"
}
mkexit() { # name secs rc: records its pid, runs secs, exits rc
    printf '#!/bin/sh\necho $$ >> "%s/pids/%s"\nsleep %s\nexit %s\n' "$C" "$1" "$2" "$3" > "$C/bin/$1"; chmod +x "$C/bin/$1"
}
wl() { : > "$LIST"; local l; for l in "$@"; do printf '%s\n' "$l" >> "$LIST"; done; chmod 600 "$LIST"; }
starts() { [ -f "$C/pids/$1" ] && wc -l < "$C/pids/$1" | tr -d ' ' || echo 0; }
curpid() { tail -n1 "$C/pids/$1" 2>/dev/null; }
up() { local p; p=$(curpid "$1"); [ -n "$p" ] && alive "$p"; }
all_up() { local n; for n in "$@"; do up "$n" || return 1; done; }
starts_ge() { [ "$(starts "$1")" -ge "$2" ]; }
start_sup() { set -m; "${SE[@]}" bash "$SUP" "$@" >"$C/sup.out" 2>&1 </dev/null & SUP_PID=$!; set +m; }
sup_down() { gone "$SUP_PID"; }
stop_sup() { # TERM it, wait for it, keep its exit code in SUP_RC
    [ -n "$SUP_PID" ] || return 0
    skill -TERM "$SUP_PID"; wait_for 20 sup_down; wait "$SUP_PID" 2>/dev/null; SUP_RC=$?
}
runsup() { OUT=$(timeout 30 "${SE[@]}" bash "$SUP" "$@" 2>&1); RC=$?; }
slog() { cat "$ST/supervise.log" 2>/dev/null; }
intervals() { slog | grep " $1 " | grep -oE '下次間隔 [0-9.]+' | awk '{print $2}'; }
save_msg() { printf '%s\n' "$2" > "$TMPROOT/msgs/$1"; }
sentinel_list() { # a list whose only process would write a sentinel file if it were ever started
    printf '#!/bin/sh\ntouch "%s/sentinel"\nexec sleep 600\n' "$C" > "$C/bin/sen"; chmod +x "$C/bin/sen"
}

# fragments, so the file never holds a token-shaped string
TOKV="abf""_$(printf 'q%.0s' $(seq 1 30))"
BEARV="Bear""er $(printf 'z%.0s' $(seq 1 24))"
PEMV="-----BEG""IN PRIV""ATE KEY-----"
CANARY="CANARY_$RANDOM$RANDOM$RANDOM"

# =================================================================== static cases
static_cases() {
    local ps; ps=$(tr -d '\r' < "$INS" 2>/dev/null)
    local sh; sh=$(cat "$SUP" 2>/dev/null)
    # TC-002
    if printf '%s\n' "$ps" | grep -q "abf-platform-autostart" && printf '%s\n' "$ps" | grep -q -- '-AtLogOn' \
       && ! printf '%s\n' "$ps" | grep -qE -- '-(AtStartup|Daily|Weekly|Once|Monthly)'; then ok "TC-002 task abf-platform-autostart, trigger = user logon only"; else bad "TC-002 task name and logon trigger"; fi
    if printf '%s\n' "$ps" | grep -E -- 'New-ScheduledTaskTrigger' | grep -q -- '-User'; then ok "TC-002 the trigger is limited to the current user"; else bad "TC-002 trigger limited to the current user"; fi
    # TC-003
    if printf '%s\n' "$ps" | grep -q "'wsl.exe'" && printf '%s\n' "$ps" | grep -qE -- '-d \$Distro -u \$User --exec \$Script' \
       && ! printf '%s\n' "$ps" | grep -qE 'bash -c|sudo|[[:space:]]-e[[:space:]]'; then ok "TC-003 action = wsl.exe -d <distro> -u <user> --exec <script>, no bash -c, no sudo, no -e"; else bad "TC-003 action string"; fi
    # TC-005: every mutating cmdlet sits in the function that only a switch reaches
    local mut=0 badpos=0 ln fn
    while IFS=: read -r ln _; do
        mut=$((mut+1))
        fn=$(printf '%s\n' "$ps" | head -n "$ln" | grep -E '^function ' | tail -n1 | awk '{print $2}')
        case $fn in Invoke-Apply|Invoke-Remove) ;; *) badpos=$((badpos+1)) ;; esac
    done < <(printf '%s\n' "$ps" | grep -nE '(Register|Unregister|Set|Enable|Disable|Remove)-ScheduledTask|schtasks')
    local callbad=0
    while IFS=: read -r ln txt; do
        case $txt in function*) continue ;; esac
        if printf '%s\n' "$ps" | sed -n "$((ln>1?ln-1:1)),${ln}p" | grep -qE 'if \(\$Apply|if \(\$Remove|elseif \(\$Apply|elseif \(\$Remove'; then :; else callbad=$((callbad+1)); fi
    done < <(printf '%s\n' "$ps" | grep -nE 'Invoke-(Apply|Remove)')
    if [ "$mut" -ge 2 ] && [ "$badpos" -eq 0 ] && [ "$callbad" -eq 0 ]; then ok "TC-005 register/unregister only inside the -Apply / -Remove functions, reached only by their switches"; else bad "TC-005 guarded mutation" "mut=$mut badpos=$badpos callbad=$callbad"; fi
    if printf '%s\n' "$ps" | grep -qE '^\s*else\s*\{?\s*$|\} *else *\{' && printf '%s\n' "$ps" | grep -q 'Show-Plan'; then ok "TC-005 the default branch only prints (Show-Plan)"; else bad "TC-005 default branch prints"; fi
    # TC-006
    if printf '%s\n' "$ps" | grep -q '\[switch\]\$Apply' && printf '%s\n' "$ps" | grep -q '\[switch\]\$Remove' \
       && printf '%s\n' "$ps" | grep -qE 'Register-ScheduledTask.*-Force' \
       && printf '%s\n' "$ps" | grep -E 'Unregister-ScheduledTask' | grep -q -- '-TaskName \$TaskName'; then ok "TC-006 -Apply (replaces if it exists) and -Remove (this task name only) exist"; else bad "TC-006 -Apply/-Remove"; fi
    # TC-007 (static; the live -Remove is not run, it would delete the real task if it were registered)
    if printf '%s\n' "$ps" | grep -q '本來就沒有這個工作'; then ok "TC-007 -Remove says 本來就沒有這個工作 when there is none"; else bad "TC-007 remove of a missing task"; fi
    if printf '%s\n' "$ps" | grep -A6 -- '本來就沒有這個工作' | grep -q 'exit 0'; then ok "TC-007 and ends with exit 0"; else bad "TC-007 exit 0 after the missing-task message"; fi
    # TC-008
    if ! printf '%s\n' "$ps" | grep -qE 'RunAs|RunLevel Highest|Start-Process' && printf '%s\n' "$ps" | grep -q -- '-RunLevel Limited' \
       && printf '%s\n' "$ps" | grep -qE 'UnauthorizedAccessException|0x80070005' && printf '%s\n' "$ps" | grep -q '權限不足'; then ok "TC-008 no elevation, runs Limited, a 權限不足 branch stops and says so"; else bad "TC-008 no elevation"; fi
    # TC-009
    local m9=""
    for w in '-RestartInterval (New-TimeSpan -Minutes 1)' '-RestartCount 999' '-ExecutionTimeLimit ([TimeSpan]::Zero)' '-AllowStartIfOnBatteries' '-DontStopIfGoingOnBatteries' '-MultipleInstances IgnoreNew' '-Hidden'; do
        printf '%s\n' "$ps" | grep -qF -- "$w" || m9="$m9 [$w]"
    done
    if [ -z "$m9" ]; then ok "TC-009 retry every minute, no time limit, battery ok, one instance, hidden"; else bad "TC-009 task settings" "missing:$m9"; fi
    # TC-010
    if [ -s "$INS" ] && { [ "$(head -c3 "$INS" | od -An -tx1 | tr -d ' ')" = "efbbbf" ] || ! LC_ALL=C grep -q '[^[:print:][:space:]]' "$INS"; }; then ok "TC-010 install-autostart.ps1 has a UTF-8 BOM or is pure ASCII"; else bad "TC-010 BOM or ASCII"; fi
    # TC-011
    if git rev-parse --git-dir >/dev/null 2>&1; then
        if git ls-files -s "$W/abf-supervise.sh" | grep -q '^100755'; then ok "TC-011 abf-supervise.sh is mode 100755 in the index"; else bad "TC-011 index mode 100755"; fi
    else skip "TC-011 index mode" "no git"; fi
    if [ "$(head -n1 "$SUP")" = '#!/usr/bin/env bash' ] && ! grep -q $'\r' "$SUP"; then ok "TC-011 bash shebang on line 1, no CR in the file"; else bad "TC-011 shebang and line endings"; fi
    # TC-012 (setsid): the script does not use it, so there is nothing to check for
    if [ -s "$SUP" ] && ! grep -vE '^[[:space:]]*#' "$SUP" | grep -qw setsid; then ok "TC-012 the script does not use setsid (nothing to check for)"; else bad "TC-012 setsid use needs its own check"; fi
    # TC-027 / TC-093: defaults written in the header
    local hd; hd=$(sed -n '1,45p' "$SUP")
    local d=""
    printf '%s\n' "$hd" | grep -qE 'ABF_SUPERVISE_BASE[[:space:]].*[[:space:]]2([[:space:]]|$)' || d="$d base"
    printf '%s\n' "$hd" | grep -qE 'ABF_SUPERVISE_MAX[[:space:]].*[[:space:]]60([[:space:]]|$)' || d="$d max"
    printf '%s\n' "$hd" | grep -qE 'ABF_SUPERVISE_STABLE[[:space:]].*[[:space:]]30([[:space:]]|$)' || d="$d stable"
    printf '%s\n' "$hd" | grep -qE 'ABF_SUPERVISE_WAIT[[:space:]].*[[:space:]]10([[:space:]]|$)' || d="$d wait"
    printf '%s\n' "$hd" | grep -qE 'ABF_SUPERVISE_LOGMAX[[:space:]].*10485760' || d="$d logmax"
    if [ -z "$d" ]; then ok "TC-027 header documents the defaults 2 / 60 / 30 / 10 and TC-093 10485760 bytes"; else bad "TC-027 header defaults" "missing:$d"; fi
    # TC-074: nothing that dumps the environment
    if [ -s "$SUP" ] && ! grep -vE '^[[:space:]]*#' "$SUP" | grep -qE '(^|[;&|(`[:space:]])(env|printenv|export[[:space:]]+-p|declare[[:space:]]+-p|set[[:space:]]+-o[[:space:]]+xtrace)([[:space:]]|$)|set[[:space:]]+-[a-z]*x|^[[:space:]]*set[[:space:]]*$|^[[:space:]]*export[[:space:]]*$'; then ok "TC-074 the script never dumps or traces the environment"; else bad "TC-074 environment dump"; fi
    # TC-110 / TC-115 / TC-116 / TC-121: what the three files must not contain
    local f n
    for f in "$SUP" "$INS" "$EX"; do
        n=$(basename "$f")
        if [ -s "$f" ] && ! grep -qiE 'sudo|/etc/wsl\.conf|systemctl|systemd=true|>[[:space:]]*/etc/' "$f"; then ok "TC-110 $n: no sudo, wsl.conf, systemctl, systemd=true, /etc write"; else bad "TC-110 $n"; fi
        if [ -s "$f" ] && ! grep -qiE 'tailscale|funnel' "$f"; then ok "TC-115 $n: no tailscale or funnel"; else bad "TC-115 $n"; fi
        if [ -s "$f" ] && ! grep -qiE '(^|[^a-z])ssh([^a-z]|$)|on_site\.sh' "$f"; then ok "TC-116 $n: no ssh, no on_site.sh"; else bad "TC-116 $n"; fi
    done
    if [ -s "$SUP" ] && ! grep -vE '^[[:space:]]*#' "$SUP" | grep -qE '(^|[^a-z-])(tw|nextflow)([[:space:]]|$)|abf-platform[[:space:]]+[a-z]|trace|\.db|\.sqlite'; then ok "TC-121 the script calls no tw, nextflow or platform command and reads no trace or database"; else bad "TC-121 no run state"; fi
    # TC-120
    local l1 l2
    l1=$(sed -n '1,40p' "$SUP" | grep -E '^#[[:space:]]*Not[[:space:]]+.+:' | head -n1)
    l2=$(sed -n '1,40p' "$INS" | grep -E '^#[[:space:]]*Not[[:space:]]+.+:' | head -n1)
    local r1=${l1#*:} r2=${l2#*:}
    if [ "${#r1}" -ge 15 ] && printf '%s' "$l1" | grep -qi 'systemd' && [ "${#r2}" -ge 15 ] && ! printf '%s\n%s\n' "$l1" "$l2" | grep -qE '\.(sh|ps1)'; then ok "TC-120 both scripts open with a '# Not <tool>: <reason>' line (systemd; an external task tool)"; else bad "TC-120 Not line" "$l1 / $l2"; fi
    # TC-060 / TC-061: the example file
    local ex; ex=$(cat "$EX" 2>/dev/null)
    local shapes='abf_[A-Za-z0-9]{20,}|Bearer |-----BEGIN|eyJ[A-Za-z0-9_-]{10,}[.][A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}'
    local nonc; nonc=$(printf '%s\n' "$ex" | grep -vE '^[[:space:]]*(#|$)')
    local badtok
    badtok=$(printf '%s\n' "$nonc" | tr ' ' '\n' | grep '/' | grep -vE '^<|^http://127\.0\.0\.1:8787$' || true)
    if [ -n "$ex" ] && ! printf '%s\n' "$ex" | grep -qE "$shapes" && ! printf '%s\n' "$ex" | grep -qE '/(home|Users|mnt)/|[A-Za-z]:\\' && [ -z "$badtok" ]; then ok "TC-060 processes.example: no token shape, no personal path, only <placeholders>"; else bad "TC-060 example has secrets or real paths" "$badtok"; fi
    local cnt names dupes
    cnt=$(printf '%s\n' "$nonc" | grep -c .)
    names=$(printf '%s\n' "$nonc" | awk '{print $1}')
    dupes=$(printf '%s\n' "$names" | sort | uniq -d)
    local shape_ok=1
    printf '%s\n' "$nonc" | grep -qE '^[a-z0-9-]+[[:space:]]+[^[:space:]]*abf-platform serve$' || shape_ok=0
    printf '%s\n' "$nonc" | grep -qE 'abf-platform web --public-url <[^>]+>$' || shape_ok=0
    printf '%s\n' "$nonc" | grep -qE 'abf-platform mcp --http --public-url <[^>]+>$' || shape_ok=0
    [ "$(printf '%s\n' "$nonc" | grep -cE 'abf-station run --platform http://127\.0\.0\.1:8787 --token-file <[^>]+> --deployment <[^>]+> --plugin-root <[^>]+>$')" -eq 3 ] || shape_ok=0
    printf '%s\n' "$names" | grep -qvE '^[a-z0-9-]+$' && shape_ok=0
    if [ "$cnt" -eq 6 ] && [ -z "$dupes" ] && [ "$shape_ok" -eq 1 ]; then ok "TC-061 six lines: serve, web, mcp and three stations, unique names, token only as --token-file"; else bad "TC-061 example lines" "count=$cnt dupes=$dupes shape=$shape_ok"; fi
    # TC-113: no real list in the repo
    if ! git ls-files 2>/dev/null | grep -qE '(^|/)processes$' && [ ! -e "$ROOT/$W/processes" ]; then ok "TC-113 only processes.example is in the repo, no real list named processes"; else bad "TC-113 a real list is in the repo"; fi
    if ! grep -nE 'psrun .*-(Apply|Remove)' "$HERE/platform_autostart_test.sh" | grep -v 'grep' >/dev/null; then ok "TC-113 this test never runs the installer with -Apply or -Remove"; else bad "TC-113 installer run with -Apply/-Remove"; fi
}

# =================================================================== PowerShell (only when powershell.exe is reachable)
psrun() { timeout 90 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$INS")" "$@" 2>&1 | tr -d '\r'; }
psq() { timeout 90 powershell.exe -NoProfile -Command "if (Get-ScheduledTask -TaskName abf-platform-autostart -ErrorAction SilentlyContinue) { 'EXISTS' } else { 'ABSENT' }" 2>&1 | tr -d '\r'; }
ps_cases() {
    if ! command -v powershell.exe >/dev/null 2>&1; then
        skip "TC-003 live dry run" "略過：這裡沒有 powershell.exe"; skip "TC-004 no task is created without -Apply" "略過：這裡沒有 powershell.exe"; return
    fi
    local before after out
    before=$(psq)
    out=$(psrun -Distro Ubuntu -User tester -Script /opt/abf/abf-supervise.sh)
    after=$(psq)
    if printf '%s\n' "$out" | grep -qF 'wsl.exe -d Ubuntu -u tester --exec /opt/abf/abf-supervise.sh'; then ok "TC-003 live dry run prints wsl.exe -d Ubuntu -u tester --exec <script>"; else bad "TC-003 live dry run action" "$out"; fi
    if printf '%s\n' "$out" | grep -q 'abf-platform-autostart' && printf '%s\n' "$out" | grep -q 'no change made' && [ -n "$before" ] && [ "$before" = "$after" ]; then ok "TC-004 without -Apply it says what it would do, changes nothing (task query before = after: $after)"; else bad "TC-004 dry run" "before=$before after=$after"; fi
}

# =================================================================== supervisor cases (each in its own sandbox, run in parallel)
case_t001() { new_case t001; mkfake a; mkfake b; mkfake c; wl "a $C/bin/a" "b $C/bin/b" "c $C/bin/c"
    set -m; env -i "ABFT_CASE=$C" "HOME=$C/home" "ABF_SUPERVISE_STATE=$ST" "PATH=/usr/bin:/bin" bash "$SUP" --list "$LIST" >"$C/sup.out" 2>&1 </dev/null & SUP_PID=$!; set +m
    if wait_for 10 all_up a b c; then ok "TC-001 from a clean environment (env -i, no terminal) all three processes come up"; else bad "TC-001 clean-environment start" "$(cat "$C/sup.out")"; fi
    OUT=$(env -i "ABFT_CASE=$C" "HOME=$C/home" "ABF_SUPERVISE_STATE=$ST" "PATH=/usr/bin:/bin" bash "$SUP" --status 2>&1); RC=$?
    if [ "$RC" -eq 0 ] && [ "$(printf '%s\n' "$OUT" | grep -cE '^[abc]: 在跑')" -eq 3 ]; then ok "TC-001 --status shows all three 在跑"; else bad "TC-001 status" "$OUT"; fi
    stop_sup; sweep "$C"; }

case_t012() { new_case t012; mkfake a; wl "a $C/bin/a"; sentinel_list
    mkdir -p "$C/nofl"; local t; for t in bash cat sleep date stat mkdir chmod cp mv rm touch env dirname id; do p=$(command -v $t) && ln -sf "$p" "$C/nofl/$t"; done
    OUT=$(env -i "ABFT_CASE=$C" "HOME=$C/home" "ABF_SUPERVISE_STATE=$ST" "PATH=$C/nofl" "$(command -v bash)" "$SUP" --list "$LIST" 2>&1); RC=$?
    save_msg TC-012 "$OUT"
    if [ "$RC" -ne 0 ] && printf '%s\n' "$OUT" | grep -q 'flock' && printf '%s\n' "$OUT" | grep -q '安裝' && [ ! -e "$C/pids/a" ] && [ ! -d "$ST" ]; then ok "TC-012 without flock: says which tool and what to do, non-zero, starts nothing, no unlocked mode"; else bad "TC-012 missing flock" "rc=$RC $OUT"; fi; sweep "$C"; }

case_t020() { new_case t020; mkfake a; mkfake b; mkfake c; wl "a $C/bin/a" "b $C/bin/b" "c $C/bin/c"; start_sup --list "$LIST"
    wait_for 10 all_up a b c || bad "TC-020 setup: three up"
    local pa pb pc; pa=$(curpid a); pc=$(curpid c); pb=$(curpid b)
    skill -KILL "$pb"
    if wait_for 4 starts_ge b 2 && up b && [ "$(curpid b)" != "$pb" ]; then ok "TC-020 b killed with -9 is back within base + 2 s with a new pid"; else bad "TC-020 b did not come back" "$(slog | tail -n5)"; fi
    if [ "$(curpid a)" = "$pa" ] && [ "$(curpid c)" = "$pc" ] && [ "$(starts a)" -eq 1 ] && [ "$(starts c)" -eq 1 ]; then ok "TC-020 a and c kept their pids and were started once"; else bad "TC-020 neighbours disturbed"; fi
    # TC-041 on the same run
    runsup --status
    if printf '%s\n' "$OUT" | grep -E '^b: 在跑' | grep -q "行程編號 $(curpid b) .*重啟次數 1" && printf '%s\n' "$OUT" | grep -E '^a: ' | grep -q '重啟次數 0' && printf '%s\n' "$OUT" | grep -E '^c: ' | grep -q '重啟次數 0'; then ok "TC-041 --status: b has restart count 1 and its new pid; a and c still 0"; else bad "TC-041 status after a restart" "$OUT"; fi
    # TC-023 / TC-094 style: events for the restart
    if slog | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8} b 啟動' && slog | grep -qE ' b 結束碼 137' && slog | grep -qE ' b 重啟 #1' && slog | grep -qE ' b 下次間隔 0.2 秒'; then ok "TC-023 supervise.log has timed 啟動, 結束碼, 重啟, 下次間隔 lines naming the process"; else bad "TC-023 event lines" "$(slog)"; fi
    stop_sup; sweep "$C"; }

case_t021() { new_case t021; mkexit x 1 0; wl "x $C/bin/x"; start_sup --list "$LIST"
    if wait_for 10 starts_ge x 2; then ok "TC-021 a clean exit 0 is restarted too"; else bad "TC-021 exit 0 not restarted"; fi
    if slog | grep -qE ' x 結束碼 0'; then ok "TC-021 supervise.log records exit code 0"; else bad "TC-021 exit code logged"; fi
    stop_sup; sweep "$C"; }

case_t022() { new_case t022; mkexit a 0 1; mkfake b; wl "a $C/bin/a" "b $C/bin/b"; start_sup --list "$LIST"
    wait_for 15 starts_ge a 4 || bad "TC-022 setup: a reached its long interval"
    local pb; pb=$(curpid b); skill -KILL "$pb"
    if wait_for 4 starts_ge b 2 && up b && [ "$(curpid b)" != "$pb" ]; then ok "TC-022 b comes back within base + 2 s while a sits in its long interval"; else bad "TC-022 b slowed by a"; fi
    stop_sup; sweep "$C"; }

case_t024() { new_case t024; mkexit q 0 1; wl "q $C/bin/q"; start_sup --list "$LIST"; sleep 6.2; local n; n=$(starts q)
    if [ "$n" -le 15 ] && [ "$n" -ge 3 ]; then ok "TC-024 an instantly failing process is started 3..15 times in 6 s (got $n), not hundreds"; else bad "TC-024 start count" "$n"; fi
    local iv; iv=$(intervals q | head -n4 | tr '\n' ' ')
    if [ "$iv" = "0.2 0.4 0.8 1.6 " ]; then ok "TC-024 intervals double: 0.2 0.4 0.8 1.6"; else bad "TC-024 intervals" "$iv"; fi
    local all prev=0 over=0 dec=0 v
    for v in $(intervals q); do
        awk -v a="$v" 'BEGIN{exit !(a>1.6)}' && over=$((over+1))
        awk -v a="$v" -v b="$prev" 'BEGIN{exit !(a<b)}' && dec=$((dec+1)); prev=$v
    done
    if [ "$over" -eq 0 ] && [ "$dec" -eq 0 ] && [ "$(intervals q | grep -c '^1.6$')" -ge 1 ]; then ok "TC-025 no interval above the ceiling 1.6, none decreasing, the ceiling is held"; else bad "TC-025 ceiling" "over=$over dec=$dec"; fi
    stop_sup; sweep "$C"; }

case_t026() { new_case t026
    printf '#!/bin/sh\necho $$ >> "%s/pids/r"\nn=$(wc -l < "%s/pids/r")\n[ "$n" = 4 ] && sleep 1.4\nexit 0\n' "$C" "$C" > "$C/bin/r"; chmod +x "$C/bin/r"
    wl "r $C/bin/r"; start_sup --list "$LIST"; wait_for 15 starts_ge r 6
    local iv; iv=$(intervals r | head -n5 | tr '\n' ' ')
    if [ "$iv" = "0.2 0.4 0.8 0.2 0.4 " ]; then ok "TC-026 after a run that lived past the stable time the interval starts over at 0.2"; else bad "TC-026 interval reset" "$iv"; fi
    stop_sup; sweep "$C"; }

case_t027() { new_case t027; mkexit q 0 1; wl "q $C/bin/q"
    SE+=(ABF_SUPERVISE_BASE= ABF_SUPERVISE_MAX= ABF_SUPERVISE_STABLE= ABF_SUPERVISE_WAIT=)
    start_sup --list "$LIST"; sleep 3.6
    local iv; iv=$(intervals q | head -n2 | tr '\n' ' ')
    if [ "$iv" = "2 4 " ]; then ok "TC-027 with no knobs the first intervals are 2 s and 4 s"; else bad "TC-027 default intervals" "$iv"; fi
    stop_sup; sweep "$C"; }

case_t028() { new_case t028; mkfake a; mkfake b; wl "a $C/bin/a" "b $C/bin/b"; start_sup --list "$LIST"; wait_for 10 all_up a b
    local pb; pb=$(curpid b); rm -f "$C/bin/a"; skill -KILL "$(curpid a)"
    if wait_for 6 bash -c "grep -q '無法啟動' '$ST/supervise.log'"; then ok "TC-028 a vanished binary: supervise.log says 無法啟動"; else bad "TC-028 no 無法啟動 line" "$(slog)"; fi
    sleep 1
    if slog | grep ' a 結束碼 127' >/dev/null && [ "$(intervals a | wc -l)" -ge 2 ] && alive "$SUP_PID"; then ok "TC-028 exit code 127 and the backoff go on; the supervisor stays up"; else bad "TC-028 retry" "$(slog | tail -n6)"; fi
    if [ "$(curpid b)" = "$pb" ] && up b; then ok "TC-028 b is not affected"; else bad "TC-028 b disturbed"; fi
    stop_sup; sweep "$C"; }

stop_case() { # <TC> <signal>
    new_case "t$1"; mkfake a; mkfake b; mkfake c; wl "a $C/bin/a" "b $C/bin/b" "c $C/bin/c"; start_sup --list "$LIST"; wait_for 10 all_up a b c
    local pa=$(curpid a) pb=$(curpid b) pc=$(curpid c)
    skill "-$2" "$SUP_PID"; wait_for 12 sup_down; wait "$SUP_PID" 2>/dev/null; SUP_RC=$?
    local n=$(( $(starts a) + $(starts b) + $(starts c) ))
    if [ -n "$pa" ] && [ "$SUP_RC" -eq 0 ] && gone "$pa" && gone "$pb" && gone "$pc"; then ok "TC-0$1 $2: all three children end, the supervisor exits 0"; else bad "TC-0$1 $2 stop" "rc=$SUP_RC"; fi
    sleep 0.5
    if [ "$n" -ge 3 ] && [ "$(( $(starts a) + $(starts b) + $(starts c) ))" -eq "$n" ] && [ "$(count_procs "$C")" -eq 0 ]; then ok "TC-0$1 nothing is restarted after the signal"; else bad "TC-0$1 restart after stop"; fi
    # the lock is released: another copy can start (TC-052)
    start_sup --list "$LIST"
    if wait_for 10 all_up a b c && [ "$(starts a)" -eq 2 ]; then ok "TC-052 after a normal stop another copy starts (the lock was released)"; else bad "TC-052 restart after stop"; fi
    stop_sup; sweep "$C"
}
case_t029() { stop_case 29 TERM; }
case_t030() { stop_case 30 INT; }

case_t031() { new_case t031; printf '#!/bin/sh\ntrap "" TERM\necho $$ >> "%s/pids/s"\nwhile :; do sleep 1; done\n' "$C" > "$C/bin/s"; chmod +x "$C/bin/s"
    SE+=(ABF_SUPERVISE_WAIT=1); wl "s $C/bin/s"; start_sup --list "$LIST"; wait_for 10 all_up s; local ps=$(curpid s)
    skill -TERM "$SUP_PID"; local t0=$SECONDS
    if wait_for 6 sup_down && [ $((SECONDS - t0)) -le 4 ] && gone "$ps"; then ok "TC-031 a child that ignores TERM is killed after the wait; the supervisor ends in wait + 3 s"; else bad "TC-031 SIGKILL after the wait"; fi
    wait "$SUP_PID" 2>/dev/null; sleep 0.5; [ "$(starts s)" -eq 1 ] && ok "TC-031 and it is not restarted" || bad "TC-031 restarted after stop"; sweep "$C"; }

case_t032() { new_case t032; printf '#!/bin/sh\necho $$ >> "%s/pids/g"\nsh -c "sleep 600; :" &\nsleep 600\n' "$C" > "$C/bin/g"; chmod +x "$C/bin/g"
    wl "g $C/bin/g"; start_sup --list "$LIST"; wait_for 10 up g; sleep 0.5
    local before; before=$(count_procs "$C")
    skill -TERM "$SUP_PID"; wait_for 12 sup_down; wait "$SUP_PID" 2>/dev/null; sleep 0.3
    if [ "$before" -ge 5 ] && [ "$(count_procs "$C")" -eq 0 ]; then ok "TC-032 no orphan is left: the child's own children are gone too (was $before processes)"; else bad "TC-032 orphans" "before=$before after=$(count_procs "$C")"; fi; sweep "$C"; }

case_t033() { new_case t033; mkexit q 0 1; SE+=(ABF_SUPERVISE_BASE=30); wl "q $C/bin/q"; start_sup --list "$LIST"; wait_for 5 bash -c "grep -q 下次間隔 '$ST/supervise.log'"
    local n=$(starts q) t0=$SECONDS; skill -TERM "$SUP_PID"
    if [ "$n" -ge 1 ] && wait_for 5 sup_down && [ $((SECONDS - t0)) -le 4 ] && [ "$(starts q)" -eq "$n" ]; then ok "TC-033 a TERM during a 30 s wait ends the supervisor quickly with no further start"; else bad "TC-033 stop during backoff"; fi
    wait "$SUP_PID" 2>/dev/null; sweep "$C"; }

case_t035() { new_case t035; local m="MARK$RANDOM"
    printf '#!/bin/sh\necho $$ >> "%s/pids/o"\necho OUT_%s\necho ERR_%s >&2\nexec sleep 600\n' "$C" "$m" "$m" > "$C/bin/o"; chmod +x "$C/bin/o"
    wl "o $C/bin/o"; start_sup --list "$LIST"; wait_for 10 up o; sleep 0.3
    if grep -q "OUT_$m" "$ST/log/o.log" && grep -q "ERR_$m" "$ST/log/o.log" && ! grep -q "$m" "$C/sup.out"; then ok "TC-035 a process's stdout and stderr go to log/<name>.log, not to the supervisor's terminal"; else bad "TC-035 process log"; fi
    stop_sup; sweep "$C"; }

case_t040() { new_case t040; mkfake a; mkfake b; mkfake c; wl "a $C/bin/a" "b $C/bin/b" "c $C/bin/c"; start_sup --list "$LIST"; wait_for 10 all_up a b c
    runsup --status
    local okl=1 n; for n in a b c; do printf '%s\n' "$OUT" | grep -E "^$n: 在跑" | grep -qE "行程編號 $(curpid $n) .*上次啟動 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8}.*重啟次數 0" || okl=0; done
    if [ "$RC" -eq 0 ] && [ "$okl" -eq 1 ]; then ok "TC-040 --status: one line per name with 在跑, pid, last start, restart count 0; exit 0"; else bad "TC-040 status lines" "rc=$RC $OUT"; fi
    # TC-043: status does not start or write anything
    local snap1 snap2 ls1 ls2; snap1=$(find "$ST" | sort | tr '\n' ' '); ls1=$(slog | wc -l); local pa=$(curpid a) sa=$(starts a)
    local i; for i in 1 2 3 4 5; do runsup --status; done
    snap2=$(find "$ST" | sort | tr '\n' ' '); ls2=$(slog | wc -l)
    if [ -n "$pa" ] && [ "$snap1" = "$snap2" ] && [ "$ls1" = "$ls2" ] && [ "$(curpid a)" = "$pa" ] && [ "$(starts a)" = "$sa" ] && [ "$(count_procs "$C")" -le 12 ]; then ok "TC-043 five --status runs start nothing, add no file and no log line"; else bad "TC-043 status side effects"; fi
    # TC-050 / TC-051: a second copy, the same list and a different list
    local before=$(starts a)$(starts b)$(starts c)
    runsup --list "$LIST"; save_msg TC-050 "$OUT"
    if [ "$RC" -eq 0 ] && printf '%s\n' "$OUT" | grep -q '已經有一份' && [ "$(starts a)$(starts b)$(starts c)" = "$before" ] && [ "$(curpid a)" = "$pa" ]; then ok "TC-050 a second copy says one is already running, exits 0, starts nothing"; else bad "TC-050 second copy" "rc=$RC $OUT"; fi
    mkfake d; local l2="$C/list2"; printf 'd %s\n' "$C/bin/d" > "$l2"; chmod 600 "$l2"
    runsup --list "$l2"
    if [ "$RC" -eq 0 ] && [ ! -e "$C/pids/d" ]; then ok "TC-051 a second copy with a different list is stopped by the same lock"; else bad "TC-051 different list" "rc=$RC"; fi
    # TC-121: the state files hold nothing but names, pids, times, counts and exit codes
    local keys; keys=$(cat "$ST"/proc/* | cut -d= -f1 | sort -u | tr '\n' ' ')
    if [ "$keys" = "last_rc pid restarts running started " ]; then ok "TC-121 the state files hold only pid, times, counts, running flag and exit code"; else bad "TC-121 state file keys" "$keys"; fi
    stop_sup; sweep "$C"; }

case_t042() { new_case t042; mkexit z 0 1; mkfake b; SE+=(ABF_SUPERVISE_BASE=6 ABF_SUPERVISE_MAX=6); wl "z $C/bin/z" "b $C/bin/b"; start_sup --list "$LIST"
    wait_for 6 bash -c "grep -q ' z 下次間隔' '$ST/supervise.log'"; sleep 0.3; runsup --status
    if printf '%s\n' "$OUT" | grep -E '^z: ' | grep -q '沒在跑' && ! printf '%s\n' "$OUT" | grep -E '^z: ' | grep -qE '在跑 +行程編號 [0-9]' && printf '%s\n' "$OUT" | grep -E '^b: ' | grep -qE '^b: 在跑'; then ok "TC-042 a process waiting to restart shows 沒在跑 (not its old pid as running); the others are true"; else bad "TC-042 backoff state" "$OUT"; fi
    stop_sup; sweep "$C"; }

case_t044() { new_case t044; mkdir -p "$ST"; chmod 700 "$ST"; : > "$ST/supervise.lock"; sentinel_list
    runsup --status; save_msg TC-044 "$OUT"
    if [ "$RC" -eq 1 ] && printf '%s\n' "$OUT" | grep -q '看守腳本沒在跑' && printf '%s\n' "$OUT" | grep -q -- '--list' && [ ! -e "$C/sentinel" ]; then ok "TC-044 --status with no supervisor: says so, gives the next step, exit 1, starts nothing"; else bad "TC-044 not running" "rc=$RC $OUT"; fi
    new_case t045; mkfake a; mkfake b; wl "a $C/bin/a" "b $C/bin/b"; start_sup --list "$LIST"; wait_for 10 all_up a b
    kill -9 "$SUP_PID" 2>/dev/null; wait "$SUP_PID" 2>/dev/null; sweep "$C"; sleep 0.3
    runsup --status
    if [ "$RC" -eq 1 ] && printf '%s\n' "$OUT" | grep -q '看守腳本沒在跑' && ! printf '%s\n' "$OUT" | grep -qE '^[ab]: 在跑'; then ok "TC-045 after a kill -9 of the supervisor the leftover state files do not fake a 在跑"; else bad "TC-045 stale state" "rc=$RC $OUT"; fi
    new_case t046; runsup --status
    if [ "$RC" -eq 1 ] && printf '%s\n' "$OUT" | grep -q '沒在跑' && [ ! -e "$ST" ]; then ok "TC-046 on a fresh machine --status says not running and creates no folder"; else bad "TC-046 fresh machine" "rc=$RC"; fi; sweep "$C"; }

case_t053() { new_case t053; mkfake a; mkfake b; wl "a $C/bin/a" "b $C/bin/b"; start_sup --list "$LIST"; wait_for 10 all_up a b
    kill -9 "$SUP_PID" 2>/dev/null; wait "$SUP_PID" 2>/dev/null; sweep "$C"; sleep 0.3; rm -f "$C/pids/a" "$C/pids/b"
    start_sup --list "$LIST"
    if wait_for 10 all_up a b; then ok "TC-053 after a kill -9 of the first copy (and a clean-up) a new copy starts: no stale lock"; else bad "TC-053 stale lock" "$(cat "$C/sup.out")"; fi
    stop_sup; sweep "$C"
    new_case t054; mkfake a; mkfake b; wl "a $C/bin/a" "b $C/bin/b"
    set -m; "${SE[@]}" bash "$SUP" --list "$LIST" >"$C/o1" 2>&1 </dev/null & local p1=$!; "${SE[@]}" bash "$SUP" --list "$LIST" >"$C/o2" 2>&1 </dev/null & local p2=$!; set +m
    wait_for 10 all_up a b; sleep 1
    local gl=0; gone "$p1" && gl=$((gl+1)); gone "$p2" && gl=$((gl+1))
    if [ "$gl" -eq 1 ] && [ "$(starts a)" -eq 1 ] && [ "$(starts b)" -eq 1 ] && grep -qh '已經有一份' "$C/o1" "$C/o2"; then ok "TC-054 two started at once: exactly one runs the processes, the other says so"; else bad "TC-054 race" "gone=$gl a=$(starts a) b=$(starts b)"; fi
    skill -TERM "$p1"; skill -TERM "$p2"; wait "$p1" "$p2" 2>/dev/null; sweep "$C"; }

tok_case() { # <TC> <label> <the offending text> <where: line|comment>
    new_case "t$1"; sentinel_list
    if [ "$4" = comment ]; then printf '# note %s\nsen %s/bin/sen\n' "$3" "$C" > "$LIST"; else printf 'sen %s/bin/sen --opt %s\n' "$C" "$3" > "$LIST"; fi; chmod 600 "$LIST"
    runsup --list "$LIST"; local o1=$OUT r1=$RC; save_msg "TC-$1" "$o1"; runsup --list "$LIST" --check
    local lineno=1; [ "$4" = comment ] && lineno=1
    if [ "$r1" -eq 2 ] && printf '%s\n' "$o1" | grep -qE '第 [0-9]+ 行' && printf '%s\n' "$o1" | grep -q -- '--token-file' && [ ! -e "$C/sentinel" ] && [ ! -d "$ST" ] \
       && ! printf '%s\n%s\n' "$o1" "$OUT" | grep -qF -- "$3" && ! printf '%s\n%s\n' "$o1" "$OUT" | grep -qF -- "${3#*Bearer }"; then ok "TC-$1 $2: refused with exit 2, line number, --token-file advice, nothing started, the text not echoed"; else bad "TC-$1 $2" "rc=$r1 $o1"; fi
    if [ "$RC" -eq 2 ] && printf '%s\n' "$OUT" | grep -qE '第 [0-9]+ 行'; then ok "TC-067 $2: --check also flags it, exit 2, by line"; else bad "TC-067 $2 --check" "rc=$RC $OUT"; fi
    sweep "$C"
}
case_t063() { tok_case 063 "abf_ token" "$TOKV" line; }
case_t064() { tok_case 064 "Bearer" "$BEARV" line; }
case_t065() { tok_case 065 "key header" "$PEMV" line; }
case_t066() { tok_case 066 "token in a comment line" "$TOKV" comment; }

case_t068() { new_case t068; mkfake a; wl "a $C/bin/a --token-file /tmp/x/abf_token abf_platform abf-platform abf-station"
    runsup --list "$LIST" --check
    if [ "$RC" -eq 0 ]; then ok "TC-068 ordinary abf-platform / abf_token / abf_platform words are not taken for a token (--check)"; else bad "TC-068 false positive" "$OUT"; fi
    start_sup --list "$LIST"; if wait_for 10 up a; then ok "TC-068 and the list starts"; else bad "TC-068 start"; fi; stop_sup; sweep "$C"; }

case_t069() { new_case t069; sentinel_list; local m r=0 all=1 msg=""
    for m in 666 664 660 640 644; do
        printf 'sen %s/bin/sen\n' "$C" > "$LIST"; chmod $m "$LIST"; runsup --list "$LIST"; msg=$OUT
        printf '%s\n' "$OUT" | grep -qF "$LIST" && printf '%s\n' "$OUT" | grep -q "chmod 600 $LIST" && [ "$RC" -eq 2 ] && [ ! -e "$C/sentinel" ] && [ ! -d "$ST" ] || { all=0; msg="$m: rc=$RC $OUT"; }
    done
    save_msg TC-069 "$OUT"
    if [ "$all" -eq 1 ]; then ok "TC-069 modes 0666 0664 0660 0640 0644 are all refused: file named, chmod 600 given, exit 2, nothing started"; else bad "TC-069 wide modes" "$msg"; fi
    printf 'sen %s/bin/sen\n' "$C" > "$LIST"; local both=1
    for m in 600 400; do chmod $m "$LIST"; runsup --list "$LIST" --check; [ "$RC" -eq 0 ] || both=0; done
    if [ "$both" -eq 1 ]; then ok "TC-070 modes 0600 and 0400 are accepted by --check"; else bad "TC-070 good modes"; fi
    chmod 666 "$LIST"; runsup --list "$LIST" --check
    if [ "$RC" -eq 2 ] && printf '%s\n' "$OUT" | grep -q '權限' && [ ! -e "$C/sentinel" ]; then ok "TC-071 --check also refuses a list with a wide mode"; else bad "TC-071" "rc=$RC $OUT"; fi; sweep "$C"; }

case_t072() { local um
    for um in 022 000; do
        new_case "t072_$um"; printf '#!/bin/sh\necho $$ >> "%s/pids/w"\nhead -c 300 /dev/zero | tr "\\0" x\nexec sleep 600\n' "$C" > "$C/bin/w"; chmod +x "$C/bin/w"
        mkfake k; wl "w $C/bin/w" "k $C/bin/k"; SE+=(ABF_SUPERVISE_LOGMAX=100)
        ( umask $um; start_sup --list "$LIST"; echo "$SUP_PID" > "$C/suppid" ); SUP_PID=$(cat "$C/suppid")
        wait_for 10 all_up w k; skill -KILL "$(curpid w)"; wait_for 6 starts_ge w 2; sleep 0.8
        local bad_perm="" f
        while IFS= read -r f; do
            if [ -d "$f" ]; then [ "$(stat -c %a "$f")" = 700 ] || bad_perm="$bad_perm $f:$(stat -c %a "$f")"; else [ "$(stat -c %a "$f")" = 600 ] || bad_perm="$bad_perm $f:$(stat -c %a "$f")"; fi
        done < <(find "$ST")
        if [ -z "$bad_perm" ] && [ -f "$ST/log/w.log.1" ] && [ -f "$ST/supervise.lock" ]; then ok "TC-072 umask $um: folders 0700, every file (logs, rotated log, lock, state) 0600"; else bad "TC-072 umask $um" "$bad_perm"; fi
        stop_sup; sweep "$C"
    done; }

case_round() { new_case round; mkfake a; mkfake b; wl "a $C/bin/a" "b $C/bin/b"; sentinel_list
    SE+=("CANARY_SECRET=$CANARY" ABF_SUPERVISE_LOGMAX=400)
    printf 'x bad name %s\n' "$C" > "$C/badlist"; chmod 600 "$C/badlist"
    mkdir -p "$C/home/.config" "$C/tmp/keep"; echo keep > "$C/home/.config/keep.txt"
    snap() { find "$C/home" "$C/tmp" "$LIST" "$C/bin" -exec stat -c '%n %Y %s %a' {} + 2>/dev/null | sort; }
    local s1; s1=$(snap)
    runsup --check --list "$LIST"; local o_check=$OUT
    start_sup --list "$LIST"; wait_for 10 all_up a b
    skill -KILL "$(curpid b)"; wait_for 6 starts_ge b 2; sleep 0.8
    runsup --status; local o_status=$OUT
    runsup --list "$C/badlist"; local o_bad=$OUT
    stop_sup; sweep "$C"
    local s2; s2=$(snap)
    # TC-075
    if [ "$(starts a)" -ge 1 ] && [ "$s1" = "$s2" ] && [ -z "$(ls -A "$C/tmp" | grep -v '^keep$')" ]; then ok "TC-075 outside the state folder nothing is added, changed or removed (list hash and time unchanged, TMPDIR clean)"; else bad "TC-075 files outside the state folder" "$(diff <(printf '%s\n' "$s1") <(printf '%s\n' "$s2") | head -n5)"; fi
    # TC-073
    if [ "$(starts a)" -ge 1 ] && [ -d "$ST" ] && ! printf '%s\n%s\n%s\n%s\n' "$o_check" "$o_status" "$o_bad" "$(cat "$C/sup.out")" | grep -qF "$CANARY" && ! grep -rqF "$CANARY" "$ST"; then ok "TC-073 an environment variable of the caller appears in no output, no log, no state file"; else bad "TC-073 environment leak"; fi
    # TC-094
    if [ -s "$ST/supervise.log" ] && ! grep -qvE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} ' "$ST/supervise.log"; then ok "TC-094 every line of supervise.log starts with a date and time"; else bad "TC-094 untimed line" "$(grep -vE '^[0-9]{4}-[0-9]{2}-[0-9]{2} ' "$ST/supervise.log" | head -n2)"; fi
    if slog | grep -q ' a 已停止'; then ok "TC-094 the stop is logged too"; else bad "TC-094 stop line"; fi; }

case_t080() { new_case t080; printf '#!/bin/sh\nn=0\nfor x in "$@"; do printf "%%s\\n" "$x" >> "%s/args"; done\necho $$ >> "%s/pids/argt"\nexec sleep 600\n' "$C" "$C" > "$C/bin/argt"; chmod +x "$C/bin/argt"
    mkfake plain
    printf '# a comment\n\n   \n   argt %s/bin/argt '"'"'one two'"'"' three "four five"\n  plain %s/bin/plain\n' "$C" "$C" > "$LIST"; chmod 600 "$LIST"
    start_sup --list "$LIST"; wait_for 10 all_up argt plain; sleep 0.2
    if [ "$(tr '\n' '|' < "$C/args")" = "one two|three|four five|" ]; then ok "TC-080 comments, blank lines and indentation skipped; quotes and spaces in arguments kept as the shell reads them"; else bad "TC-080 arguments" "$(cat "$C/args" 2>/dev/null)"; fi
    stop_sup; sweep "$C"; }

case_t081() { new_case t081; sentinel_list; local n all=1 msg=""
    for n in Web my_proc a.b 中文 a/b; do
        printf '%s %s/bin/sen\n' "$n" "$C" > "$LIST"; chmod 600 "$LIST"
        runsup --list "$LIST" --check; local c1=$RC o1=$OUT; runsup --list "$LIST"
        [ "$c1" -eq 2 ] && [ "$RC" -eq 2 ] && printf '%s\n' "$o1" | grep -qE '第 1 行' && printf '%s\n' "$o1" | grep -q '不合法' && [ ! -e "$C/sentinel" ] || { all=0; msg="$n: $c1/$RC $o1"; }
    done
    if [ "$all" -eq 1 ]; then ok "TC-081 bad names (Web my_proc a.b 中文 a/b): refused by --check and by start, line number and reason given"; else bad "TC-081 names" "$msg"; fi; sweep "$C"; }

case_t082() { new_case t082; sentinel_list; printf 'sen %s/bin/sen\n# gap\nsen %s/bin/sen\n' "$C" "$C" > "$LIST"; chmod 600 "$LIST"
    runsup --list "$LIST" --check; local c1=$RC o1=$OUT; runsup --list "$LIST"; save_msg TC-082 "$OUT"
    if [ "$c1" -eq 2 ] && [ "$RC" -eq 2 ] && printf '%s\n' "$o1" | grep -q '第 1 行與第 3 行' && printf '%s\n' "$o1" | grep -q '「sen」' && [ ! -e "$C/sentinel" ]; then ok "TC-082 a repeated name: both line numbers and the name, exit 2, nothing started"; else bad "TC-082 duplicates" "$o1"; fi; sweep "$C"; }

case_t083() { new_case t083; printf 'lonely\n' > "$LIST"; chmod 600 "$LIST"; runsup --list "$LIST" --check
    if [ "$RC" -eq 2 ] && printf '%s\n' "$OUT" | grep -qE '第 1 行.*缺'; then ok "TC-083 a name with no command: exit 2, the line number, 缺"; else bad "TC-083" "$OUT"; fi
    # TC-084 / TC-086
    new_case t084; mkfake good; printf '#!/bin/sh\n' > "$C/bin/noexec"; chmod 644 "$C/bin/noexec"
    wl "good $C/bin/good" "gone $C/bin/not-here" "noex $C/bin/noexec"; runsup --list "$LIST" --check
    if [ "$RC" -eq 2 ] && printf '%s\n' "$OUT" | grep -qE '第 2 行.*找不到執行檔' && printf '%s\n' "$OUT" | grep -qE '第 3 行.*不可執行' && [ ! -e "$C/pids/good" ]; then ok "TC-084 --check names the missing and the non-executable program, per line, and starts nothing"; else bad "TC-084" "$OUT"; fi
    new_case t086; mkfake good; wl "Bad $C/bin/good" "good $C/bin/good" "good $C/bin/good" "zz $C/bin/not-here"; runsup --list "$LIST" --check
    if [ "$RC" -eq 2 ] && printf '%s\n' "$OUT" | grep -qE '第 1 行.*不合法' && printf '%s\n' "$OUT" | grep -qE '第 2 行與第 3 行' && printf '%s\n' "$OUT" | grep -qE '第 4 行.*找不到執行檔'; then ok "TC-086 three kinds of error in one list are all reported at once, each with its line"; else bad "TC-086" "$OUT"; fi
    new_case t085; mkfake a; sentinel_list; wl "a $C/bin/a" "sen $C/bin/sen"; runsup --list "$LIST" --check
    if [ "$RC" -eq 0 ] && printf '%s\n' "$OUT" | grep -q '清單沒問題' && [ ! -e "$C/sentinel" ] && [ ! -e "$C/pids/a" ] && [ ! -e "$ST" ]; then ok "TC-085 --check on a good list: exit 0, 清單沒問題, starts nothing, creates no state folder or lock"; else bad "TC-085" "rc=$RC $OUT"; fi; sweep "$C"; }

case_t087() { new_case t087; mkfake a; mkdir -p "$C/home/.config/abf-platform"; printf 'a %s/bin/a\n' "$C" > "$C/home/.config/abf-platform/processes"; chmod 600 "$C/home/.config/abf-platform/processes"
    start_sup; if wait_for 10 up a; then ok "TC-087 without --list the list at ~/.config/abf-platform/processes is read"; else bad "TC-087 default list" "$(cat "$C/sup.out")"; fi; stop_sup
    new_case t088; sentinel_list; runsup --list "$C/nope"; local r1=$RC o1=$OUT; save_msg TC-088 "$o1"; runsup; local r2=$RC o2=$OUT; runsup --check
    if [ "$r1" -eq 2 ] && [ "$r2" -eq 2 ] && [ "$RC" -eq 2 ] && printf '%s\n' "$o1" | grep -qF "$C/nope" && printf '%s\n' "$o1" | grep -q 'processes.example' && printf '%s\n' "$o2" | grep -q 'processes.example' && ! printf '%s\n' "$o1$o2" | grep -qE 'No such file|line [0-9]+:' && [ ! -d "$ST" ]; then ok "TC-088 a missing list (given or default): plain sentence, names the file and processes.example, exit 2"; else bad "TC-088" "$r1/$r2/$RC $o1 $o2"; fi
    new_case t089; printf '# only a comment\n\n' > "$LIST"; chmod 600 "$LIST"; runsup --list "$LIST"; local r3=$RC o3=$OUT; runsup --list "$LIST" --check
    if [ "$r3" -eq 2 ] && [ "$RC" -eq 2 ] && printf '%s\n' "$o3" | grep -q '沒有可看守的行程' && [ ! -d "$ST" ]; then ok "TC-089 an empty list is refused: 沒有可看守的行程, exit 2"; else bad "TC-089" "$o3"; fi; sweep "$C"; }

logsetup() { # <id> <contents of the log> : start with a log of $2 bytes of x already present
    new_case "$1"; mkfake a; wl "a $C/bin/a"; SE+=(ABF_SUPERVISE_LOGMAX=100); mkdir -p "$ST/log"; chmod 700 "$ST" "$ST/log"
}
case_t090() { logsetup t090; head -c 500 /dev/zero | tr '\0' N > "$ST/log/a.log"; start_sup --list "$LIST"; wait_for 10 up a
    if [ -f "$ST/log/a.log.1" ] && [ "$(stat -c %s "$ST/log/a.log.1")" -eq 500 ] && [ "$(stat -c %s "$ST/log/a.log")" -lt 100 ]; then ok "TC-090 an over-size log is moved to <name>.log.1 and <name>.log starts empty"; else bad "TC-090 rotation at start"; fi
    stop_sup
    # TC-091
    head -c 600 /dev/zero | tr '\0' M > "$ST/log/a.log"; echo OLD > "$ST/log/a.log.1"; start_sup --list "$LIST"; wait_for 10 up a
    if [ "$(stat -c %s "$ST/log/a.log.1")" -eq 600 ] && [ "$(ls "$ST/log" | grep -c '^a\.log')" -eq 2 ]; then ok "TC-091 a second rotation keeps one old file: the latest, the older dropped"; else bad "TC-091" "$(ls "$ST/log")"; fi
    stop_sup; sweep "$C"; }

case_t092() { new_case t092; printf '#!/bin/sh\necho $$ >> "%s/pids/spew"\nwhile :; do echo xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx; sleep 0.05; done\n' "$C" > "$C/bin/spew"; chmod +x "$C/bin/spew"
    wl "spew $C/bin/spew"; SE+=(ABF_SUPERVISE_LOGMAX=2000); start_sup --list "$LIST"; wait_for 10 up spew
    local maxsz=0 t sz; for t in $(seq 1 40); do sleep 0.1; sz=$(stat -c %s "$ST/log/spew.log" 2>/dev/null || echo 0); [ "$sz" -gt "$maxsz" ] && maxsz=$sz; done
    if [ "$maxsz" -le 5000 ] && [ -f "$ST/log/spew.log.1" ] && [ "$(ls "$ST/log" | grep -c '^spew\.log')" -eq 2 ] && [ "$(starts spew)" -eq 1 ]; then ok "TC-092 a log that grows while the process runs is rotated in place; one old file; the process is not restarted (max $maxsz bytes)"; else bad "TC-092 live rotation" "max=$maxsz starts=$(starts spew) $(ls "$ST/log")"; fi
    stop_sup; sweep "$C"; }

case_t093() { new_case t093; mkexit q 0 1; wl "q $C/bin/q"; SE+=(ABF_SUPERVISE_LOGMAX=400); start_sup --list "$LIST"; sleep 5
    if [ -f "$ST/supervise.log.1" ] && [ "$(ls "$ST" | grep -c '^supervise\.log')" -eq 2 ] && head -n1 "$ST/supervise.log" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8} ' && ! grep -qvE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8} ' "$ST/supervise.log"; then ok "TC-093 supervise.log is rotated too: one old file, the new one still starts with a timed line"; else bad "TC-093 supervise.log rotation" "$(ls "$ST")"; fi
    stop_sup; sweep "$C"; }

case_t125() { new_case t125; mkfake a; wl "a $C/bin/a"
    if [ "$(id -u)" -eq 0 ]; then skip "TC-125 unwritable state folder" "running as root, a read-only folder cannot be made"; return; fi
    mkdir -p "$C/ro"; chmod 500 "$C/ro"; SE+=("ABF_SUPERVISE_STATE=$C/ro/state"); runsup --list "$LIST"; save_msg TC-125 "$OUT"; chmod 700 "$C/ro"
    if [ "$RC" -eq 2 ] && printf '%s\n' "$OUT" | grep -qF "$C/ro/state" && printf '%s\n' "$OUT" | grep -q '寫不進' && [ ! -e "$C/pids/a" ]; then ok "TC-125 a state folder that cannot be written: says which, exit 2, no process runs without a record"; else bad "TC-125" "rc=$RC $OUT"; fi; sweep "$C"; }

# =================================================================== documents and repo-level cases
doc_cases() {
    local sec; sec=$(awk '/^##+ .*桌機（WSL）上自動啟動/{f=1;h=$1;next} f&&/^##+ /{ if (length($1)<=length(h)) exit } f' "$OPS" 2>/dev/null)
    if [ -n "$sec" ] && grep -qE '^##+ .*桌機（WSL）上自動啟動' "$OPS"; then ok "TC-096 docs/OPERATIONS.md has the section 桌機（WSL）上自動啟動"; else bad "TC-096 section missing"; fi
    local pos=0 prev=0 order_ok=1 w ln
    for w in '前提' '清單檔' '--check' '手動' '-Apply' '記錄' '停' '-Remove'; do
        ln=$(printf '%s\n' "$sec" | grep -n -- "$w" | head -n1 | cut -d: -f1); ln=${ln:-0}
        if [ "$ln" -eq 0 ] || [ "$ln" -lt "$prev" ]; then order_ok=0; fi; prev=$ln
    done
    if [ "$order_ok" -eq 1 ] && [ -n "$sec" ]; then ok "TC-096 it covers, in order: prerequisites, the list, --check, a manual run, registering, status and logs, stopping, removing"; else bad "TC-096 order of topics"; fi
    if printf '%s\n' "$sec" | grep -q 'OTP' && printf '%s\n' "$sec" | grep -q '重新連線' && printf '%s\n' "$sec" | grep -q '一分鐘' && printf '%s\n' "$sec" | grep -q '先停掉'; then ok "TC-097 it says the shared SSH connection (OTP) is not restored, and that switching needs the manual processes stopped first (about a minute off)"; else bad "TC-097 the two limits"; fi
    local sw="" f
    if printf '%s\n' "$sec" | grep -q 'SIGTERM' && printf '%s\n' "$sec" | grep -q 'kill -9' && printf '%s\n' "$sec" | grep -q 'Ctrl-C'; then :; else sw="$sw stop-advice"; fi
    for f in --list --check --status; do grep -qF -- "$f" "$SUP" || sw="$sw $f-missing-in-script"; printf '%s\n' "$sec" | grep -qF -- "$f" || sw="$sw $f-not-in-doc"; done
    for f in -Apply -Remove; do grep -qF -- "$f" "$INS" || sw="$sw $f-missing-in-ps1"; printf '%s\n' "$sec" | grep -qF -- "$f" || sw="$sw $f-not-in-doc"; done
    local p; while IFS= read -r p; do [ -z "$p" ] && continue; [ -e "$p" ] || sw="$sw nofile:$p"; done < <(printf '%s\n' "$sec" | grep -oE '`deploy/[^` ]+`' | tr -d '`')
    if [ -z "$sw" ]; then ok "TC-098 it tells how to stop (SIGTERM / Ctrl-C, not kill -9); every switch and file it names exists"; else bad "TC-098" "$sw"; fi
    if awk '/^## 3\.0\.0-dev/{f=1;next} /^## /{f=0} f' CHANGELOG.md | grep -E '^- ' | grep -q 'platform-autostart.*deploy/wsl/'; then ok "TC-099 CHANGELOG 3.0.0-dev has a line for platform-autostart and deploy/wsl/"; else bad "TC-099 changelog line"; fi
    if printf '%s\n' "$sec" | grep -q 'deploy/systemd/' && ! printf '%s\n' "$sec" | grep -qiE 'sudo|/etc/wsl\.conf|systemctl|systemd=true'; then ok "TC-110 the doc section points systemd hosts to deploy/systemd/ and names no sudo, wsl.conf or systemctl"; else bad "TC-110 doc section"; fi
    # manual cases are written down in docs/TESTING.md
    local t; t=$(awk '/^## .*platform-autostart/{f=1;next} /^## /{f=0} f' docs/TESTING.md)
    local mm=""; for w in TC-013 TC-014 TC-015 TC-034 TC-047 TC-055 TC-077 TC-114; do printf '%s\n' "$t" | grep -q "$w" || mm="$mm $w"; done
    if [ -z "$mm" ]; then ok "docs/TESTING.md has a platform-autostart section with the eight manual cases"; else bad "TESTING.md manual cases" "missing:$mm"; fi
}

git_cases() {
    if ! git rev-parse --verify -q origin/v3 >/dev/null || [ "$(git branch --show-current 2>/dev/null)" != "fable/platform-autostart" ]; then
        skip "TC-111 / TC-112 / TC-123 diff against origin/v3" "only checked on the feature branch with origin/v3 present"; return
    fi
    local names; names=$(git diff --name-only origin/v3...HEAD); [ -n "$names" ] || { bad "TC-111 nothing differs from origin/v3 yet"; return; }
    if [ -z "$(git diff --name-only origin/v3...HEAD -- deploy/systemd)" ]; then ok "TC-111 deploy/systemd/ is untouched"; else bad "TC-111 deploy/systemd changed"; fi
    local out; out=$(printf '%s\n' "$names" | grep -vE '^(deploy/wsl/|docs/OPERATIONS\.md$|docs/TESTING\.md$|CHANGELOG\.md$|specs/platform-autostart/|tests/platform_autostart_test\.sh$|tests/hosted_deploy_test\.sh$)' || true)
    if [ -z "$out" ]; then ok "TC-112 only the planned files changed (nothing in platform/, hooks/, .github/, the constitution, plugin.json)"; else bad "TC-112 unplanned files" "$out"; fi
    local d; d=$(git diff -U0 origin/v3...HEAD -- tests/hosted_deploy_test.sh | grep -E '^[-+][^-+]')
    if [ "$(printf '%s\n' "$d" | grep -c '^-')" -eq 1 ] && [ "$(printf '%s\n' "$d" | grep -c '^+')" -eq 1 ] && printf '%s\n' "$d" | grep '^+' | grep -q 'wsl/abf-supervise.sh'; then ok "TC-123 hosted_deploy_test.sh differs only by the TC-069 list line"; else bad "TC-123 hosted_deploy diff" "$d"; fi
}

nested_cases() { # TC-122 / 124 / 126: the neighbours that must stay green (the full suite runs them again)
    [ "${PA_NO_NEST:-0}" = 1 ] && { skip "TC-122 / TC-123 / TC-124 neighbours" "PA_NO_NEST=1"; return; }
    local t
    for t in credentials_stay_in_settings_test.sh:TC-122 hosted_deploy_test.sh:TC-123 portable_userland.sh:TC-124 no_hardcoded_paths.sh:TC-124 shell_helper_dupes_test.sh:TC-124 scripts_name_their_alternative.sh:TC-124 no_second_run_state_test.sh:TC-121 operations_doc_test.sh:TC-096; do
        if bash "$HERE/${t%%:*}" >"$TMPROOT/nest.out" 2>&1; then ok "${t##*:} ${t%%:*} stays green"; else bad "${t##*:} ${t%%:*}" "$(grep -E 'FAIL|STALE|NEW|TOKEN' "$TMPROOT/nest.out" | head -n3)"; fi
    done
    if bash "$HERE/run_all.sh" --list 2>/dev/null | grep -q 'platform_autostart_test.sh'; then ok "TC-126 run_all.sh lists platform_autostart_test.sh"; else bad "TC-126 run_all.sh --list"; fi
}

msg_cases() { # TC-095: every refusal message says what happened and a next step in plain words
    local t f m n all=1 why=""
    for t in TC-012 TC-044 TC-050 TC-063 TC-069 TC-082 TC-088 TC-125; do
        f="$TMPROOT/msgs/$t"; [ -f "$f" ] || { [ "$t" = TC-125 ] && [ "$(id -u)" -eq 0 ] && continue; all=0; why="$why $t:none"; continue; }
        m=$(cat "$f"); n=$(printf '%s\n' "$m" | grep -c .)
        if [ "$n" -gt 3 ] || printf '%s\n' "$m" | grep -qE 'No such file|command not found|syntax error|unbound variable|line [0-9]+:' || ! printf '%s\n' "$m" | grep -qE '請|用 |chmod|--status|--list'; then all=0; why="$why $t"; fi
    done
    if [ "$all" -eq 1 ]; then ok "TC-095 the refusals read as plain sentences with a next step, not raw shell errors"; else bad "TC-095 messages" "$why"; fi
}

# =================================================================== run
main_run() {
    static_cases
    ps_cases
    doc_cases
    git_cases
    local f
    for f in $(declare -F | awk '{print $3}' | grep -E '^case_' | sort); do
        while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 0.2; done
        ( $f ) >"$TMPROOT/res/$f" 2>/dev/null &
    done
    wait
    for f in "$TMPROOT"/res/case_*; do cat "$f"; done
    msg_cases
    nested_cases
}
main_run | tee "$TMPROOT/all.out"
nf=$(grep -cE '[[:space:]]FAIL(:|$)' "$TMPROOT/all.out" || true)
if [ "${nf:-0}" -gt 0 ]; then echo "$nf failed"; exit 1; fi
echo "all passed"
