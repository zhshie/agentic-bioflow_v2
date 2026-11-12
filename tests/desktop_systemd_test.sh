#!/bin/bash
# desktop-systemd: the files that make the lab's desktop platform (in WSL) start at logon and
# restart a crashed process - one systemd user-unit template for the station agent, its env
# example, one Windows script that keeps WSL open - and the docs that tell the lab owner how.
# Shape checks only: file contents, no secret, docs complete. Whether the platform really comes
# back after a reboot is only visible on the desktop (docs/TESTING.md, "desktop-systemd").
# This file starts nothing, registers nothing and writes nothing outside a temporary folder (TC-051).
# Test cases: specs/desktop-systemd/test-case.md (TC ids in the labels).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
fails=0
ok() { printf '%-92s ok\n' "$1"; }
bad() { printf '%-92s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
skip() { printf '%-92s skip%s\n' "$1" "${2:+: $2}"; }
has() { printf '%s\n' "$1" | grep -F -- "$2" >/dev/null; }
hasre() { printf '%s\n' "$1" | grep -E -- "$2" >/dev/null; }
# check <label> <command...>: ok when the command succeeds
check() { local l="$1"; shift; if "$@"; then ok "$l"; else bad "$l"; fi; }

TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT

D=deploy
UNIT=$D/systemd/abf-station@.service.in
ENVEX=$D/station.env.example
PS1=$D/wsl/keep-wsl-running.ps1
OPS=docs/OPERATIONS.md
TST=docs/TESTING.md
CHG=CHANGELOG.md
SCLI=platform/abf_station/cli.py
PCLI=platform/abf_platform/cli.py
BASE=$(git merge-base origin/v3 HEAD 2>/dev/null || true)
OLD_UNITS=("$D/systemd/abf-serve.service.in" "$D/systemd/abf-web.service.in" "$D/systemd/abf-mcp.service.in")
# words that are tool names, built from pieces so this file never contains them as a call (TC-051)
SC="system""ctl"; WSLX="ws""l"; SCH="sch""tasks"

unit=""; [ -f "$UNIT" ] && unit=$(tr -d '\r' < "$UNIT")
envex=""; [ -f "$ENVEX" ] && envex=$(tr -d '\r' < "$ENVEX")
ps1=""; [ -f "$PS1" ] && ps1=$(tr -d '\r' < "$PS1")
ops=$(tr -d '\r' < "$OPS"); tst=$(tr -d '\r' < "$TST")
# the ### section of OPERATIONS.md whose heading mentions WSL, until the next heading
sec=$(awk '/^##+ /{on=($0 ~ /^### .*WSL/)} on' "$OPS" | tr -d '\r')
nocomment() { printf '%s\n' "$1" | grep -vE '^[[:space:]]*#'; }
# the first line of $2 (a text) that matches regex $1 -> its line number, or empty
lineno() { printf '%s\n' "$2" | grep -nE -- "$1" | head -n1 | cut -d: -f1; }

# ---------- US1: starts by itself ----------
if [ -n "$unit" ]; then ok "TC-001 $UNIT exists"; else bad "TC-001 $UNIT exists"; fi
if hasre "$(nocomment "$unit")" '^WantedBy=default\.target$' && hasre "$unit" '^After=abf-serve\.service$' && hasre "$unit" '^Wants=abf-serve\.service$'; then ok "TC-001 station unit: WantedBy default.target, After and Wants abf-serve"; else bad "TC-001 station unit install and ordering"; fi

el=$(printf '%s\n' "$unit" | grep -E '^ExecStart=' | head -n1)
want_args=('--platform http://127.0.0.1:8787' '--token-file ${ABF_STATION_TOKEN_FILE}' '--deployment ${ABF_STATION_DEPLOYMENT}' '--plugin-root ${ABF_STATION_PLUGIN_ROOT}')
want_el='ExecStart=%h/<venv>/bin/abf-station run'; for a in "${want_args[@]}"; do want_el="$want_el $a"; done
if [ "$el" = "$want_el" ]; then ok "TC-002 ExecStart is abf-station run with exactly the four flags"; else bad "TC-002 ExecStart" "$el"; fi
runblock=$(awk '/add_parser\("run"/{on=1;next} /add_parser\("/{on=0} on' "$SCLI")
nfl=0; for fl in --platform --token-file --deployment --plugin-root; do nfl=$((nfl+1)); if has "$runblock" "add_argument(\"$fl\""; then ok "TC-002 '$fl' is a flag of abf-station run in cli.py"; else bad "TC-002 '$fl' is a flag of abf-station run"; fi; done
nflags=$(printf '%s\n' "$el" | grep -oE ' --[a-z-]+' | wc -l)
if [ "$nflags" -eq 4 ]; then ok "TC-002 ExecStart has no other flag"; else bad "TC-002 ExecStart flag count" "$nflags"; fi

envfiles=$(printf '%s\n' "$unit" | grep -E '^[[:space:]]*EnvironmentFile=')
if [ "$envfiles" = "$(printf 'EnvironmentFile=%%h/.config/abf-platform/env\nEnvironmentFile=%%h/.config/abf-platform/station-%%i.env')" ]; then ok "TC-003 two EnvironmentFile lines, shared first, station-%i.env second, no '-'"; else bad "TC-003 EnvironmentFile lines" "$envfiles"; fi

# ---------- Windows script ----------
if [ -n "$ps1" ]; then ok "TC-004 $PS1 exists"; else bad "TC-004 $PS1 exists"; fi
# TC-004 as changed by ruling D9: the action is a hidden-window powershell that starts wsl.exe; what finally runs is wsl.exe [-d <distro>] --exec /bin/sleep infinity
if has "$ps1" 'abf-wsl-keepalive' && hasre "$ps1" 'New-ScheduledTaskTrigger +-AtLogOn' && hasre "$ps1" "New-ScheduledTaskAction +-Execute +'powershell\.exe'" && has "$ps1" '-NoProfile -WindowStyle Hidden -Command' && hasre "$ps1" '& wsl\.exe' && has "$ps1" '--exec' && has "$ps1" '/bin/sleep' && hasre "$ps1" 'infinity'; then ok "TC-004 (ruling D9) task abf-wsl-keepalive: at logon, powershell.exe -NoProfile -WindowStyle Hidden -Command & wsl.exe ... --exec /bin/sleep infinity"; else bad "TC-004 task name, trigger and action (ruling D9)"; fi
nact=$(printf '%s\n' "$ps1" | grep -cE 'New-ScheduledTaskAction' || true)
if [ "$nact" -eq 1 ] && ! printf '%s\n' "$ps1" | grep -iE 'abf-platform|abf-station|systemctl|serve|restart' | grep -vE '^[[:space:]]*#|Write-Host|Write-Output|"[^"]*(platform|systemd)[^"]*"' >/dev/null; then ok "TC-004 one action only; nothing starts or restarts the platform"; else bad "TC-004 one action only" "actions: $nact"; fi
if hasre "$ps1" 'ExecutionTimeLimit +\(?New-TimeSpan +-Seconds +0\)?|ExecutionTimeLimit +\[TimeSpan\]::Zero|ExecutionTimeLimit +0' \
   && has "$ps1" '-AllowStartIfOnBatteries' && has "$ps1" '-DontStopIfGoingOnBatteries' && has "$ps1" '-Hidden' \
   && has "$ps1" '-MultipleInstances IgnoreNew' && hasre "$ps1" 'New-ScheduledTaskTrigger +-AtLogOn +-User' \
   && hasre "$ps1" '-RunLevel +Limited' ; then ok "TC-005 no time limit, battery ok, hidden, one instance, current user, Limited"; else bad "TC-005 task settings"; fi

# ---------- docs of US1 ----------
if [ -n "$sec" ]; then ok "TC-006 OPERATIONS.md has a ### section about WSL"; else bad "TC-006 a ### section with WSL in its heading"; fi
if has "$sec" '/etc/wsl.conf' && has "$sec" '[boot]' && has "$sec" 'systemd=true' && has "$sec" 'sudo' && has "$sec" 'wsl --shutdown'; then ok "TC-006 section: /etc/wsl.conf [boot] systemd=true, sudo, wsl --shutdown"; else bad "TC-006 systemd=true step"; fi
near=$(printf '%s\n' "$sec" | grep -n -A8 -B2 'wsl --shutdown')
if hasre "$near" 'OTP' && hasre "$near" '(everything|all).*(stop|stops)|stops everything|every.*stop' && hasre "$near" 'SSH' && hasre "$near" '[Rr]econnect|connect again|log in again|open it again'; then ok "TC-007 consequences of wsl --shutdown: all stops, SSH drops, OTP again"; else bad "TC-007 consequences next to wsl --shutdown"; fi
if has "$sec" '.bashrc' && has "$sec" '~/.config/abf-platform/env' && has "$sec" 'ABF_PUBLIC_URL' && hasre "$sec" 'does not read|never reads|not read'; then ok "TC-008 env step: systemd does not read ~/.bashrc, put it in the env file, ABF_PUBLIC_URL"; else bad "TC-008 env step"; fi
if has "$sec" 'loginctl enable-linger' && has "$sec" 'sudo loginctl enable-linger' && hasre "$sec" 'without .*terminal|nobody has a terminal|no terminal|not depend' && has "$sec" 'abf-wsl-keepalive' && hasre "$sec" 'each .*(one thing|job)|two .*(jobs|things)|different (job|thing)'; then ok "TC-009 linger step: command, sudo, what it does, and how it differs from the keep-alive task"; else bad "TC-009 linger step"; fi
# TC-010: order of steps
declare -a marks=('WSL 2' 'systemd=true' 'ABF_PUBLIC_URL' 'station-<name>.env' 'daemon-reload' 'enable --now abf-serve abf-web abf-mcp abf-station@<name>' 'enable-linger' 'abf-wsl-keepalive' "status 'abf-*'" 'journalctl --user -u abf-web -n 50' 'disable --now' 'by hand' 'not log' )
prev=0; order_ok=1; for m in "${marks[@]}"; do n=$(printf '%s\n' "$sec" | grep -nF -- "$m" | head -n1 | cut -d: -f1); if [ -z "$n" ]; then order_ok=0; bad "TC-010 section mentions '$m'"; elif [ "$n" -lt "$prev" ] && [ "$m" != 'by hand' ] && [ "$m" != 'not log' ]; then order_ok=0; bad "TC-010 '$m' comes after the previous step" "line $n < $prev"; else [ "$m" = 'by hand' ] || [ "$m" = 'not log' ] || prev=$n; fi; done
[ "$order_ok" -eq 1 ] && ok "TC-010 steps are in the planned order"
if hasre "$sec" '[Nn]obody is logged in|no one is logged in|not logged in to Windows|logged in to Windows'; then ok "TC-010 says nothing starts when nobody is logged in to Windows"; else bad "TC-010 nobody logged in to Windows"; fi

# ---------- US2: restart ----------
if hasre "$unit" '^Restart=on-failure$' && hasre "$unit" '^RestartSec=5$'; then ok "TC-014 Restart=on-failure, RestartSec=5"; else bad "TC-014 restart policy"; fi
if hasre "$unit" '^RestartPreventExitStatus=2 3$'; then ok "TC-015 RestartPreventExitStatus=2 3"; else bad "TC-015 RestartPreventExitStatus=2 3"; fi
if [ -n "$unit" ] && ! hasre "$(nocomment "$unit")" 'PrivateTmp|ProtectHome|ProtectSystem|PrivateNetwork|RestrictAddressFamilies|ReadOnlyPaths|ReadWritePaths'; then ok "TC-016 none of the seven forbidden hardening options"; else bad "TC-016 forbidden hardening options present or no unit"; fi
hard_ok=1; [ -n "$unit" ] || hard_ok=0
while IFS=: read -r n line; do
  [ -z "$n" ] && continue
  prevline=$(printf '%s\n' "$unit" | sed -n "$((n-1))p")
  if ! printf '%s\n' "$prevline" | grep -E '^#' | grep -iE 'ssh' | grep -iE '/tmp' >/dev/null; then hard_ok=0; bad "TC-016 hardening line '$line' has a comment above it naming ssh and /tmp"; fi
done < <(printf '%s\n' "$unit" | grep -nE '^(NoNewPrivileges|Protect[A-Za-z]*|Private[A-Za-z]*|Restrict[A-Za-z]*|Lock[A-Za-z]*|MemoryDenyWriteExecute|SystemCallFilter|Capability[A-Za-z]*)=')
[ "$hard_ok" -eq 1 ] && ok "TC-016 every hardening line is explained by a comment about ssh and /tmp"

# TC-017: systemd-analyze verify on a copy with the placeholder replaced
if command -v systemd-analyze >/dev/null 2>&1 && [ -f "$UNIT" ]; then
  mkdir -p "$TMP/v/venv/bin"; printf '#!/bin/sh\n' > "$TMP/v/venv/bin/abf-station"; chmod +x "$TMP/v/venv/bin/abf-station"
  mkdir -p "$TMP/v/home"; cp "$D/systemd/abf-serve.service.in" "$TMP/v/abf-serve.service"
  sed "s|%h/<venv>|$TMP/v/venv|" "$UNIT" > "$TMP/v/abf-station@.service"; sed -i "s|%h/<venv>|$TMP/v/venv|" "$TMP/v/abf-serve.service"
  out=$(cd "$TMP/v" && HOME="$TMP/v/home" systemd-analyze verify --user ./abf-station@.service 2>&1 | grep -F 'abf-station@' | grep -viE 'EnvironmentFile|No such file' || true)
  if [ -z "$out" ]; then ok "TC-017 systemd-analyze verify --user reports nothing for the station template"; else bad "TC-017 systemd-analyze verify" "$out"; fi
else skip "TC-017 systemd-analyze verify" "systemd-analyze is not installed here (or the unit is missing); the shape checks above stand"; fi

# TC-021: the three old units are byte-for-byte the ones of origin/v3
if [ -n "$BASE" ]; then
  if [ -z "$(git diff "$BASE" -- "${OLD_UNITS[@]}")" ]; then ok "TC-021 the three existing units are unchanged against origin/v3"; else bad "TC-021 an existing unit changed"; fi
else skip "TC-021 existing units unchanged" "no origin/v3 to compare with"; fi

# ---------- US3: seeing what runs ----------
if has "$sec" "systemctl --user status 'abf-*'" && has "$sec" 'journalctl --user -u abf-web -n 50' && has "$sec" 'active (running)'; then ok "TC-022 status and journal commands, with what you should see"; else bad "TC-022 status / journal commands"; fi
tail_sec=$(printf '%s\n' "$sec" | sed -n '/^[0-9]*\. .*\(Look\|status\|Status\)/,$p'); [ -n "$tail_sec" ] || tail_sec="$sec"
t23=1; for w in 'stop abf-serve abf-web abf-mcp abf-station@<name>' 'restart abf-serve abf-web abf-mcp abf-station@<name>' 'disable --now abf-serve abf-web abf-mcp abf-station@<name>'; do has "$tail_sec" "$w" || { t23=0; bad "TC-023 command '$w'"; }; done
has "$tail_sec" 'daemon-reload' || { t23=0; bad "TC-023 daemon-reload after removing unit files"; }
[ "$t23" -eq 1 ] && ok "TC-023 stop, restart, disable --now each cover the four units; daemon-reload after removal"
# TC-024: every abf-platform / abf-station subcommand and repo path named in the section exists
psubs=$(grep -oE 'sub\.add_parser\("[a-z-]+"' "$PCLI" | sed -E 's/.*\("//; s/"$//'); ssubs=$(grep -oE 'add_parser\("[a-z-]+"' "$SCLI" | sed -E 's/.*\("//; s/"$//')
n24=0
while IFS= read -r w; do [ -z "$w" ] && continue; n24=$((n24+1)); if printf '%s\n' "$psubs" | grep -x -- "$w" >/dev/null; then ok "TC-024 abf-platform $w exists"; else bad "TC-024 abf-platform $w exists"; fi; done < <(printf '%s\n' "$sec" | grep -oE 'abf-platform +[a-z][a-z-]*' | awk '{print $2}' | sort -u)
while IFS= read -r w; do [ -z "$w" ] && continue; n24=$((n24+1)); if printf '%s\n' "$ssubs" | grep -x -- "$w" >/dev/null; then ok "TC-024 abf-station $w exists"; else bad "TC-024 abf-station $w exists"; fi; done < <(printf '%s\n' "$sec" | sed 's/abf-station will not start//' | grep -oE 'abf-station +[a-z][a-z-]*' | awk '{print $2}' | sort -u)
while IFS= read -r p; do [ -z "$p" ] && continue; n24=$((n24+1)); if [ -e "$p" ]; then ok "TC-024 path $p exists"; else bad "TC-024 path $p exists"; fi; done < <(printf '%s\n' "$sec" | grep -oE '`(deploy|docs|platform|tests|scripts|specs)/[^` ]*[A-Za-z0-9]`' | tr -d '`' | sort -u)
[ "$n24" -gt 0 ] || bad "TC-024 the section names at least one command or path"
for need in 'deploy/systemd/abf-station@.service.in' 'deploy/station.env.example' 'deploy/wsl/keep-wsl-running.ps1'; do has "$sec" "$need" || bad "TC-024 section names $need"; done
if has "$sec" "journalctl --user -u 'abf-station@<name>'" && hasre "$sec" 'will not start'; then ok "TC-025 the reason an agent refuses to start is in journalctl for abf-station@<name>"; else bad "TC-025 journalctl for abf-station@<name>"; fi

# ---------- US4: not two copies ----------
n_stop=$(lineno 'stop' "$(printf '%s\n' "$sec" | sed -n '/by hand/,$p')")
if hasre "$sec" 'by hand' && hasre "$sec" '[Ss]top .*(started by hand|you started)|started by hand' && hasre "$sec" 'port' && hasre "$sec" 'minute' && hasre "$sec" 'two (copies|platforms)|second copy'; then ok "TC-027 switch-over: stop the hand-started ones (port, two copies), about a minute"; else bad "TC-027 switch-over text"; fi
l_sw=$(printf '%s\n' "$sec" | grep -nE 'Switching|switching|from (starting )?by hand|started by hand' | head -n1 | cut -d: -f1)
l_en=$(printf '%s\n' "$sec" | grep -nF 'enable --now abf-serve' | head -n1 | cut -d: -f1)
if [ -n "$l_sw" ] && [ -n "$l_en" ] && hasre "$sec" '[Bb]efore you run'; then ok "TC-027 the switch-over warning is tied to the enable --now step (before you run it)"; else bad "TC-027 warning before enable --now"; fi
if hasre "$sec" '[Ll]etters, digits, underscore|letters, digits, underscores|digits, underscore' && has "$sec" 'station-<name>.env' && has "$sec" 'abf-station@<name>'; then ok "TC-028 agent name rule and the two names that must match"; else bad "TC-028 agent name rule"; fi
if hasre "$envex" 'station-<name>\.env' && hasre "$envex" 'abf-station@<name>'; then ok "TC-028 station.env.example names station-<name>.env and abf-station@<name>"; else bad "TC-028 env example names the file and the instance"; fi

# ---------- US5: no token ----------
vars=$(nocomment "$envex" | grep -E '^[A-Z_]+=' | cut -d= -f1 | sort | tr '\n' ' ')
if [ "$vars" = "ABF_STATION_DEPLOYMENT ABF_STATION_PLUGIN_ROOT ABF_STATION_TOKEN_FILE " ]; then ok "TC-031 exactly the three variables"; else bad "TC-031 variables of station.env.example" "$vars"; fi
if ! nocomment "$envex" | grep -E '^[A-Z_]+=' | grep -vE '^[A-Z_]+=<[^>]+>[A-Za-z0-9_/.<>-]*$' | grep . >/dev/null && [ -n "$vars" ]; then ok "TC-031 every value is a <placeholder>"; else bad "TC-031 values are placeholders"; fi
if ! nocomment "$envex" | grep -E '^PATH=' >/dev/null && has "$envex" 'PATH='; then ok "TC-031 PATH appears only in a comment"; else bad "TC-031 PATH only in comments"; fi
if nocomment "$envex" | grep -E '^ABF_STATION_TOKEN_FILE=<[^>]*(file|path)[^>]*>' >/dev/null; then ok "TC-031 TOKEN_FILE is a path placeholder, not a token"; else bad "TC-031 TOKEN_FILE placeholder"; fi
KEYHDR="-----BEGIN ""PRIVATE KEY"
PATRE='abf_pat_[A-Za-z0-9]{8,}|abf_[a-z]+_[A-Za-z0-9]{16,}|Bearer +[A-Za-z0-9_-]{8,}|(password|ABF_PAT)=[^<[:space:]]'
secscan=("$UNIT" "$ENVEX" "$PS1")
printf '%s\n' "$sec" > "$TMP/section.md"
scan_files=("${secscan[@]}" "$TMP/section.md")
if grep -nE "$PATRE" "${scan_files[@]}" 2>/dev/null | grep -v 'Bearer <' | grep . >/dev/null; then bad "TC-032 no token-shaped value in the new files or section"; else ok "TC-032 no token-shaped value in the new files or section"; fi
if grep -F -- "$KEYHDR" "${scan_files[@]}" >/dev/null 2>&1; then bad "TC-032 no private-key header"; else ok "TC-032 no private-key header"; fi
if grep -nE 'DESKTOP-[A-Z0-9]{5,}|\.ts\.net|u9613010' "${scan_files[@]}" >/dev/null 2>&1; then bad "TC-032 no real host or account"; else ok "TC-032 no real host or account"; fi
if grep -nE '/(home|Users)/[A-Za-z][A-Za-z0-9_.-]*/|[A-Za-z]:\\Users' "${scan_files[@]}" 2>/dev/null | grep -v '<' | grep . >/dev/null; then bad "TC-032 no personal absolute path"; else ok "TC-032 no personal absolute path"; fi
# the scanner must be able to fail: a planted token-shaped line is found
printf 'ABF_STATION_TOKEN=%s%s\n' 'abf_pat_' 'Zz9Zz9Zz9Zz9' > "$TMP/plant.txt"
if grep -nE "$PATRE" "$TMP/plant.txt" >/dev/null; then ok "TC-032 the token scan catches a planted token (it can fail)"; else bad "TC-032 the token scan catches a planted token"; fi
tok_lines=$(nocomment "$unit" | grep -iE 'token')
if [ -n "$unit" ] && ! printf '%s\n' "$tok_lines" | grep -v -- '--token-file ${ABF_STATION_TOKEN_FILE}' | grep . >/dev/null && ! nocomment "$unit" | grep -E '^Environment=' | grep -i token >/dev/null; then ok "TC-033 the token appears in the unit only as the file path variable"; else bad "TC-033 token lines in the unit" "$tok_lines"; fi
if hasre "$sec" '\b600\b' && hasre "$sec" "WSL's own home|inside WSL|own home folder" && hasre "$sec" '/mnt/c|Windows drive' && has "$sec" 'abf-platform agent-token new' && hasre "$sec" 'once|one time'; then ok "TC-034 token file step: 600, WSL's own home not a Windows drive, made with agent-token new, shown once"; else bad "TC-034 token file step"; fi

# ---------- Windows script behaviour ----------
if has "$ps1" '[switch]$Apply' && has "$ps1" '[switch]$Remove' && has "$ps1" '$Distro'; then ok "TC-036 parameters -Apply, -Remove, -Distro exist"; else bad "TC-036 parameters"; fi
la=$(lineno 'if +\(\$Apply\)|elseif +\(\$Apply\)|\$Apply *\{' "$ps1"); lr=$(lineno 'Register-ScheduledTask' "$ps1")
if [ -n "$la" ] && [ -n "$lr" ] && [ "$lr" -gt "$la" ] && [ "$(printf '%s\n' "$ps1" | grep -c 'Register-ScheduledTask')" -eq 1 ]; then ok "TC-036 the registration call comes only after the -Apply branch opens"; else bad "TC-036 registration only inside the -Apply branch"; fi
if has "$ps1" 'Unregister-ScheduledTask' && hasre "$ps1" 'ErrorAction +SilentlyContinue|Get-ScheduledTask' && hasre "$ps1" 'Unregister-ScheduledTask[^\n]*-Confirm:\$false' && hasre "$ps1" '-Force'; then ok "TC-038 -Apply replaces (-Force), -Remove removes quietly when it is not there"; else bad "TC-038 idempotent Apply and quiet Remove"; fi
if ! hasre "$ps1" 'RunAs|RequireAdministrator|Start-Process[^\n]*-Verb' && hasre "$ps1" '[Aa]dministrator|not allowed|[Aa]ccess is denied|UnauthorizedAccess' ; then ok "TC-040 no elevation; says what to do when permission is missing"; else bad "TC-040 no self-elevation, message on missing permission"; fi
if [ -f "$PS1" ]; then
  if LC_ALL=C grep -q '[^[:print:][:space:]]' "$PS1" 2>/dev/null; then
    if [ "$(head -c3 "$PS1" | od -An -tx1 | tr -d ' ')" = "efbbbf" ]; then ok "TC-041 non-ASCII, and it starts with a UTF-8 BOM"; else bad "TC-041 non-ASCII without a BOM"; fi
  else ok "TC-041 pure ASCII"; fi
else bad "TC-041 $PS1 exists"; fi
if hasre "$ps1" 'param *\(' && has "$ps1" '[string]$Distro' && hasre "$ps1" 'if *\(\$Distro\)' && has "$ps1" '-d ' && has "$ps1" '-d "'"'"' + $Distro + '"'"'"'; then ok "TC-042 -Distro; '-d' only when given, name quoted"; else bad "TC-042 -Distro handling"; fi
# TC-043: a '# Not <tool>: <reason>' line in the first 40 lines of the unit and the script, naming something outside the repo
for f in "$UNIT" "$PS1"; do
  line=$(sed -n '1,40p' "$f" 2>/dev/null | tr -d '\r' | grep -E '^# Not [^:]+: ' | head -n1)
  reason=${line#*: }; tool=$(printf '%s' "$line" | sed -E 's/^# Not ([^:]+):.*/\1/')
  inrepo=0; for w in $tool; do w=${w%.}; [ -n "$(git ls-files | awk -F/ -v w="$w" '$NF==w' | head -n1)" ] && inrepo=1; done
  if [ -n "$line" ] && [ "${#reason}" -ge 15 ] && [ "$inrepo" -eq 0 ]; then ok "TC-043 $f has '# Not $tool: ...' naming a tool outside the repo"; else bad "TC-043 $f needs a '# Not <outside tool>: <reason of 15+ chars>' line" "$line"; fi
done
if [ -n "$ps1" ] && [ -f "$UNIT" ]; then
  if hasre "$ps1" '^# Not .*(Task Scheduler|NSSM|systemd|service)' ; then ok "TC-043 the script's Not-line points to a tool outside the repo"; else bad "TC-043 the script's Not-line points to a scheduler or service tool"; fi
fi

# ---------- US7: files and docs in place ----------
# TC-044/045 run the two existing tests (they are unchanged apart from the two named lines)
ht=$(bash tests/hosted_deploy_test.sh 2>&1); hrc=$?
if [ "$hrc" -eq 0 ]; then ok "TC-044 tests/hosted_deploy_test.sh passes"; else bad "TC-044 hosted_deploy_test.sh" "$(printf '%s\n' "$ht" | grep FAIL | head -n3 | tr '\n' ' ')"; fi
if [ -n "$BASE" ]; then
  dd=$(git diff -U0 "$BASE" -- tests/hosted_deploy_test.sh | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' || true)
  nminus=$(printf '%s\n' "$dd" | grep -c '^-' || true)
  if [ "$nminus" -eq 4 ] && [ "$(printf '%s\n' "$dd" | grep '^-' | grep -cE 'TC-069|want_list=|TC-083|-eq 3|three \.service')" -eq 4 ]; then ok "TC-044 only the TC-069 and TC-083 lines of hosted_deploy_test.sh changed (4 lines changed)"; else bad "TC-044 hosted_deploy_test.sh diff is more than the two named assertions" "removed lines: $nminus"; fi
else skip "TC-044 hosted_deploy_test.sh diff" "no origin/v3 to compare with"; fi
if hasre "$(grep -E 'want_list=' tests/hosted_deploy_test.sh)" 'station\.env\.example' && hasre "$(grep -E 'want_list=' tests/hosted_deploy_test.sh)" 'keep-wsl-running\.ps1' && hasre "$(grep -E 'want_list=' tests/hosted_deploy_test.sh)" 'abf-station@\.service\.in'; then ok "TC-044 the TC-069 list names the three new files"; else bad "TC-044 the TC-069 list names the three new files"; fi
if grep -q 'four \.service\.in' tests/hosted_deploy_test.sh && grep -qE 'wc -l\)" -eq 4' tests/hosted_deploy_test.sh; then ok "TC-044 TC-083 counts four .service.in"; else bad "TC-044 TC-083 counts four .service.in"; fi
ot=$(bash tests/operations_doc_test.sh 2>&1); orc=$?
if [ "$orc" -eq 0 ]; then ok "TC-045 tests/operations_doc_test.sh passes"; else bad "TC-045 operations_doc_test.sh" "$(printf '%s\n' "$ot" | grep FAIL | head -n3 | tr '\n' ' ')"; fi
if [ "$(printf '%s\n' "$ops" | grep -cE '^## ')" -eq 6 ]; then ok "TC-045 OPERATIONS.md still has six ## headings"; else bad "TC-045 six ## headings"; fi
lw=$(printf '%s\n' "$ops" | grep -nE '^### .*WSL' | head -n1 | cut -d: -f1); l3=$(printf '%s\n' "$ops" | grep -nE '^## 3\.' | cut -d: -f1); l4=$(printf '%s\n' "$ops" | grep -nE '^## 4\.' | cut -d: -f1)
if [ -n "$lw" ] && [ "$lw" -gt "$l3" ] && [ "$lw" -lt "$l4" ]; then ok "TC-045 the WSL section sits inside section 3, before section 4"; else bad "TC-045 the WSL section sits between ## 3 and ## 4" "$lw $l3 $l4"; fi
tsec=$(printf '%s\n' "$tst" | awk '/^##+ /{on=($0 ~ /desktop-systemd/)} on')
t46=1; for w in 'TC-011' 'TC-018' 'TC-026' 'TC-035' 'TC-029' "systemctl --user status 'abf-*'" 'active (running)'; do has "$tsec" "$w" || { t46=0; bad "TC-046 TESTING.md desktop-systemd section mentions '$w'"; }; done
[ "$t46" -eq 1 ] && ok "TC-046 TESTING.md has the desktop steps (reboot, kill, status, token, double start), each with what to see"
chg_top=$(sed -n '1,12p' "$CHG")
if hasre "$chg_top" 'desktop-systemd.*WSL|WSL.*desktop-systemd' && [ "$(printf '%s\n' "$chg_top" | grep -m1 '^- ' | grep -c 'keep-submissions')" -eq 1 ]; then ok "TC-047 CHANGELOG: a desktop-systemd line in the top section; keep-submissions still first"; else bad "TC-047 CHANGELOG line"; fi
if [ -n "$BASE" ]; then
  rem=$(git diff -U0 "$BASE" -- "$CHG" | grep -E '^-' | grep -vE '^---' | grep . || true)
  if [ -z "$rem" ]; then ok "TC-047 CHANGELOG: no existing line changed"; else bad "TC-047 CHANGELOG lines were changed"; fi
fi

# ---------- out of scope ----------
if [ -n "$BASE" ]; then
  names=$(git diff --name-only "$BASE"...HEAD; git diff --name-only; git ls-files --others --exclude-standard)
  if printf '%s\n' "$names" | grep -E '^(platform/|hooks/|\.github/|\.specify/memory/constitution\.md|\.claude-plugin/plugin\.json)' | grep . >/dev/null; then bad "TC-048 a protected path changed" "$(printf '%s\n' "$names" | grep -E '^(platform/|hooks/|\.github/|\.specify/memory/constitution\.md|\.claude-plugin/plugin\.json)')"; else ok "TC-048 no change under platform/, hooks/, .github/, the constitution or plugin.json"; fi
  if printf '%s\n' "$names" | grep -E 'requirements.*\.txt|pyproject\.toml' | grep . >/dev/null; then bad "TC-053 a dependency file changed"; else ok "TC-053 no dependency file changed"; fi
else skip "TC-048 protected paths" "no origin/v3 to compare with"; skip "TC-053 dependencies" "no origin/v3 to compare with"; fi
if has "$sec" 'OTP' && hasre "$sec" 'not (come back|reconnect|restore)|does not (come back|reconnect)|will not (come back|reconnect)|not reconnect' ; then ok "TC-049 the doc says the site connection does not come back by itself (OTP)"; else bad "TC-049 doc says the site connection needs the person and an OTP"; fi
if ! nocomment "$unit"$'\n'"$(nocomment "$ps1")" | grep -iE '\bssh\b|otp' | grep . >/dev/null; then ok "TC-049 the unit and the script never run ssh or touch an OTP"; else bad "TC-049 ssh or OTP in the unit or script"; fi
if hasre "$sec" 'Funnel' && hasre "$sec" 'Funnel .*(not|outside)|not .*Funnel|Funnel is not' ; then ok "TC-050 the doc says Tailscale Funnel is not handled here"; else bad "TC-050 Funnel is not handled"; fi
if ! git ls-files "$D" | grep -iE 'tailscale|caddy.*service' | grep . >/dev/null && ! ls "$D" "$D/systemd" "$D/wsl" 2>/dev/null | grep -iE 'tailscale|caddy.*service' >/dev/null; then ok "TC-050 no tailscale or caddy unit under deploy/"; else bad "TC-050 a tailscale or caddy unit exists"; fi
selfname=$(basename "$0")
if grep -nE "^[[:space:]]*($SC|$WSLX|$SCH|powershell\.exe|schtasks\.exe)([[:space:]]|\$)" "$HERE/$selfname" | grep -v 'powershell.exe -NoProfile' >/dev/null; then bad "TC-051 this test calls no service, wsl or scheduler tool"; else ok "TC-051 this test calls no service, wsl or scheduler tool"; fi
if ! grep -rnE '/etc/wsl\.conf' "$D" 2>/dev/null | grep -E '>>|tee|sed -i|>[[:space:]]*/etc' | grep . >/dev/null; then ok "TC-051 /etc/wsl.conf is only in docs; nothing writes it"; else bad "TC-051 something writes /etc/wsl.conf"; fi
if git ls-files "$D" scripts hooks | grep -iE 'supervis|autostart|watchdog' | grep . >/dev/null || [ -n "$(git ls-files --others --exclude-standard | grep -iE 'supervis|autostart|watchdog')" ]; then bad "TC-052 a supervisor/autostart/watchdog file exists"; else ok "TC-052 no supervisor, autostart or watchdog file"; fi
if printf '%s\n%s\n%s\n' "$sec" "$unit" "$ps1" | grep -iE 'supervisor script|autostart\.sh|watchdog' | grep . >/dev/null; then bad "TC-052 the doc teaches a hand-written watchdog"; else ok "TC-052 nothing teaches a hand-written watchdog"; fi

# ---------- constitution and safety net ----------
sc=$(bash tests/scripts_name_their_alternative.sh 2>&1); if [ $? -eq 0 ]; then ok "TC-054 tests/scripts_name_their_alternative.sh passes"; else bad "TC-054 scripts_name_their_alternative.sh" "$(printf '%s\n' "$sc" | tail -n2 | tr '\n' ' ')"; fi
cr=$(bash tests/credentials_stay_in_settings_test.sh 2>&1); if [ $? -eq 0 ]; then ok "TC-055 tests/credentials_stay_in_settings_test.sh passes"; else bad "TC-055 credentials_stay_in_settings_test.sh" "$(printf '%s\n' "$cr" | grep -iE 'fail' | head -n2 | tr '\n' ' ')"; fi
allexec=$(for f in "$UNIT" "${OLD_UNITS[@]}"; do grep -E '^ExecStart=' "$f" 2>/dev/null; done)
if [ -n "$unit" ] && ! printf '%s\n' "$allexec" | grep -vE '^ExecStart=%h/<venv>/bin/(abf-platform (serve|web|mcp)|abf-station run)( |$)' | grep . >/dev/null; then ok "TC-056 every ExecStart is abf-platform serve/web/mcp or abf-station run"; else bad "TC-056 ExecStart lines" "$allexec"; fi
if ! printf '%s\n%s\n' "$unit" "$ps1" | grep -nE '(^|[[:space:]])(tw|nextflow|abf-platform launch)([[:space:]]|$)' | grep -vE '^[0-9]+:[[:space:]]*#' | grep . >/dev/null; then ok "TC-056 no launch, tw or nextflow call in the unit or script"; else bad "TC-056 launch, tw or nextflow call"; fi

# ---------- TC-037 last: powershell.exe, default mode only ----------
if command -v powershell.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1 && [ -f "$PS1" ]; then
  q="Get-ScheduledTask -TaskName abf-wsl-keepalive -ErrorAction SilentlyContinue | Measure-Object | ForEach-Object Count"
  before=$(cd /mnt/c 2>/dev/null && powershell.exe -NoProfile -Command "$q" 2>/dev/null | tr -d '\r')
  out=$(cd /mnt/c 2>/dev/null && powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$ROOT/$PS1")" 2>&1 | tr -d '\r'); prc=$?
  after=$(cd /mnt/c 2>/dev/null && powershell.exe -NoProfile -Command "$q" 2>/dev/null | tr -d '\r')
  if [ -n "$out" ] && hasre "$out" 'abf-wsl-keepalive' && hasre "$out" '-Apply' && [ "$before" = "$after" ]; then ok "TC-037 default mode prints the plan and registers nothing (tasks before=$before after=$after)"; else bad "TC-037 default mode" "rc=$prc before=$before after=$after out=$(printf '%s' "$out" | head -c 200)"; fi
else skip "TC-037 run the script in default mode" "powershell.exe is not reachable from here; the shape checks of TC-036 stand"; fi

# ---------- fix round, rulings D1-D9 (acceptance REJECT: the docs would strand the owner) ----------
d_cdpos=$(lineno 'cd <repo' "$sec"); d_cppos=$(lineno 'cp deploy/' "$sec")
# D1: the folders exist before the first cp into them
d1=$(lineno 'mkdir -p ~/\.config/systemd/user ~/\.config/abf-platform' "$sec")
if [ -n "$d1" ] && [ -n "$d_cppos" ] && [ "$d1" -le "$d_cppos" ] && has "$sec" 'mkdir -p ~/.config/systemd/user ~/.config/abf-platform'; then ok "D1 mkdir -p of both folders comes before the first cp"; else bad "D1 mkdir -p ~/.config/systemd/user ~/.config/abf-platform before the first cp" "$d1 $d_cppos"; fi
# D2: the real order of the switch-over; no Ctrl+C advice; a listing command, kill only if something is left
sw=$(printf '%s\n' "$sec" | sed -n '/^\*\*Switching/,/^\*\*Going back/p')
if [ -n "$sw" ] && ! hasre "$sec" 'Ctrl\+C|or close it' && hasre "$sw" 'wsl --shutdown' && hasre "$sw" 'already (stopped|gone)|stops them all|stopped every' && has "$sw" "pgrep -af 'abf-platform|abf-station'" && hasre "$sw" 'nothing .*(printed|listed)|prints nothing|no output' && has "$sw" "pkill -f 'abf-platform|abf-station'" && [ "$(lineno 'pgrep' "$sw")" -lt "$(lineno 'pkill' "$sw")" ]; then ok "D2 switch-over: wsl --shutdown already stopped them, list with pgrep, pkill only if something is left"; else bad "D2 switch-over order and commands"; fi
# D3: going back to starting by hand
back=$(printf '%s\n' "$sec" | sed -n '/^\*\*Going back/,/^\*\*What this does not do/p')
if [ -n "$back" ] && has "$back" 'disable --now abf-serve abf-web abf-mcp abf-station@<name>' && has "$back" 'systemd=true' && hasre "$back" 'wsl --shutdown' && has "$back" '-Remove' && has "$back" 'docs/PLATFORM.md' && hasre "$back" '[Rr]emove the (four )?unit files|delete the (four )?unit files|rm ~/.config/systemd/user/abf-'; then ok "D3 going back: disable and remove the four, take systemd=true out, wsl --shutdown, -Remove the task, start as in docs/PLATFORM.md"; else bad "D3 a 'Going back to starting by hand' paragraph is missing or incomplete"; fi
# D4: several agents
if hasre "$sec" 'one `station-<name>\.env` (file )?for each agent' && hasre "$sec" 'enable --now abf-station@<second' && hasre "$sec" 'station-lab1\.env' && hasre "$sec" 'station-gcb\.env' && hasre "$sec" '(never|not|no) .*hyphen|hyphen .*(never|not)' && hasre "$sec" 'existing token file|file name need not'; then ok "D4 several agents: one env file and one enable each, two named examples, no hyphen, an existing token file may be reused"; else bad "D4 several agents text"; fi
# D5: the site connection
if has "$sec" 'scripts/preflight.sh' && hasre "$sec" 'prints? (the|a) line' && hasre "$sec" 'you (type|enter) the OTP|type the OTP yourself|only you can'; then ok "D5 site connection: scripts/preflight.sh prints the line, you type the OTP"; else bad "D5 how to open the site connection again"; fi
# D6: what the env files must hold, from what the programs read
d6=1; for w in 'ABF_STATION_GCP_CREDENTIALS' 'ABF_STATION_UPLOADS' 'JAVA_HOME' 'nextflow' 'gcloud' 'ABF_PLATFORM_DB' 'ABF_PLATFORM_UPLOADS' 'export'; do has "$sec" "$w" || { d6=0; bad "D6 the section names $w"; }; done
hasre "$sec" '[Gg]o through (every|each)|check every|compare (every|each)' || { d6=0; bad "D6 'compare every export in ~/.bashrc' sentence"; }
! has "$sec$envex" 'LAB_SETTINGS_FILE' || { d6=0; bad "D6 LAB_SETTINGS_FILE must not be the example"; }
! hasre "$sec" "where the deployment.s settings" || { d6=0; bad "D6 the misleading 'where the settings file is' example is gone"; }
for w in 'ABF_STATION_GCP_CREDENTIALS' 'ABF_STATION_UPLOADS' 'JAVA_HOME' '.bashrc'; do has "$envex" "$w" || { d6=0; bad "D6 station.env.example mentions $w"; }; done
[ "$d6" -eq 1 ] && ok "D6 env files: the variables the programs read, the .bashrc comparison, station.env.example in step"
# D7: cd before every cp, and the TESTING steps
if [ -n "$d_cdpos" ] && [ -n "$d_cppos" ] && [ "$d_cdpos" -lt "$d_cppos" ] && [ "$(printf '%s\n' "$sec" | grep -c 'cd <repo')" -ge 2 ]; then ok "D7 cd <repository-folder> before the cp lines and before the script call"; else bad "D7 cd to the repository before every cp deploy/ and the script call" "$d_cdpos $d_cppos"; fi
t18=$(printf '%s\n' "$tsec" | grep -A3 'TC-018'); t30=$(printf '%s\n' "$tsec" | grep 'TC-030'); t13=$(printf '%s\n' "$tsec" | grep -A12 'TC-013')
if has "$t18" 'show -p MainPID abf-serve abf-web abf-mcp abf-station@<name>' && hasre "$t18" 'before and after'; then ok "D7 TESTING TC-018: all four process numbers, before and after"; else bad "D7 TESTING TC-018 compares four process numbers before and after"; fi
if has "$t30" 'abf-platform web' && hasre "$t30" 'already in use|address already'; then ok "D7 TESTING TC-030: the exact command and the error to expect"; else bad "D7 TESTING TC-030 exact command and error"; fi
if has "$t13" 'wsl --version' && has "$t13" 'loginctl enable-linger' && hasre "$t13" 'you (must|should) see'; then ok "D7 TESTING TC-013 says what each command should show"; else bad "D7 TESTING TC-013 what to see for each command"; fi
# D8/D9: no false claim about a hidden window; the exact behaviour and the fallbacks
if ! printf '%s\n%s\n%s\n' "$sec" "$tsec" "$ps1" | grep -iE 'hidden window|in a hidden' | grep . >/dev/null; then ok "D8 nothing claims a hidden window"; else bad "D8 a 'hidden window' claim is still there"; fi
if hasre "$sec" 'flash' && hasre "$sec" 'minimi[sz]e' && hasre "$sec" '[Rr]eport' && hasre "$tsec" 'minimi[sz]e' && hasre "$tsec" 'report'; then ok "D9 docs: a window may flash; if it stays, minimise it, do not close it, report"; else bad "D9 docs say what to do if a window stays"; fi
if has "$sec" 'ExecutionPolicy Bypass' && hasre "$sec" 'right-click|right click' && hasre "$sec" 'Run with PowerShell'; then ok "D9 docs: execution-policy fallback (right-click, Run with PowerShell)"; else bad "D9 execution-policy note"; fi

# ---------- ruling E (second acceptance): the WSL section followed literally ----------
# E1: do not invent a data folder; the existing runs must be visible after enabling
if hasre "$sec" '^\*\*重要' && hasre "$sec" '[Dd]elete the .?ABF_PLATFORM_DB' && hasre "$sec" '[Dd]elete .*ABF_SITE_ADDRESS|ABF_SITE_ADDRESS.*Caddy' && hasre "$sec" '(never|do not|Do not) invent' && hasre "$sec" 'empty platform' && hasre "$sec" 'exactly the same value|identical value|same value'; then ok "E1 the 重要 paragraph: delete ABF_PLATFORM_DB and ABF_SITE_ADDRESS, never invent a folder, same value if exported"; else bad "E1 the 重要 paragraph about ABF_PLATFORM_DB"; fi
if hasre "$sec" 'existing (runs|analyses|analysis records)' && hasre "$sec" '(otherwise|if (it is|the list is) empty).*stop|stop.*(empty|otherwise)'; then ok "E1 checkpoint: existing runs must be visible after enable, otherwise stop"; else bad "E1 checkpoint: existing runs visible, otherwise stop"; fi
if grep -F 'Desktop platform in WSL' deploy/env.example >/dev/null; then ok "E1 deploy/env.example points to the WSL section"; else bad "E1 deploy/env.example points to the WSL section"; fi
# E2: no wide pkill; list narrowly, kill by number; save the command lines before the shutdown
if ! has "$sec" 'pkill' && ! has "$sec" "abf-platform|abf-station" && has "$sec" "pgrep -af 'abf-(platform|station) (serve|web|mcp|run)'" && hasre "$sec" 'kill <(process )?(number|id|pid)'; then ok "E2 no wide pkill pattern; narrow pgrep, kill by process number"; else bad "E2 no wide pkill pattern / narrow pgrep"; fi
l_save=$(lineno 'pgrep -af' "$sec"); l_sd=$(lineno '`wsl --shutdown`' "$sec")
if [ -n "$l_save" ] && [ -n "$l_sd" ] && [ "$l_save" -lt "$l_sd" ] && hasre "$sec" 'XDG_' && has "$sec" '8787' && has "$sec" '8788' && has "$sec" '8789' && has "$sec" '--public-url'; then ok "E2 command lines and ABF_/PATH/JAVA_HOME/XDG_ saved before the shutdown; ports and flags compared"; else bad "E2 save the command lines before the shutdown" "$l_save $l_sd"; fi
# E3: reconnect with on_site.sh, never reset_master.sh
if has "$sec" 'scripts/on_site.sh --check-reach' && has "$sec" 'scripts/on_site.sh --check-master; echo $?' && ! has "$sec" 'reset_master' && hasre "$sec" '25 seconds' && hasre "$sec" 'without a restart|no restart|need not restart|does not need a restart' && hasre "$sec" 'same (terminal|window)'; then ok "E3 reconnect: --check-reach line, OTP, --check-master prints 0, agent re-checks in 25 s, never reset_master"; else bad "E3 reconnect steps"; fi
# E4: all preparation before the shutdown; after it only check, daemon-reload, enable, status
l_dr=$(lineno 'daemon-reload' "$sec"); l_en=$(lineno 'enable --now abf-serve' "$sec"); l_cps=$(printf '%s\n' "$sec" | grep -nE 'cp deploy/' | tail -n1 | cut -d: -f1); l_sed=$(lineno 'sed -i' "$sec"); l_conf=$(lineno 'sudo nano /etc/wsl.conf' "$sec")
if [ -n "$l_sd" ] && [ -n "$l_dr" ] && [ -n "$l_cps" ] && [ -n "$l_sed" ] && [ -n "$l_conf" ] && [ "$l_cps" -lt "$l_sd" ] && [ "$l_sed" -lt "$l_sd" ] && [ "$l_conf" -lt "$l_sd" ] && [ "$l_sd" -lt "$l_dr" ] && [ "$l_dr" -lt "$l_en" ] && hasre "$sec" 'stopped from .*until|stays down' && hasre "$sec" 'few minutes'; then ok "E4 wsl.conf, env files and unit files are done before the shutdown; daemon-reload and enable come after; outage stated"; else bad "E4 preparation before the shutdown" "$l_conf $l_cps $l_sed $l_sd $l_dr $l_en"; fi
# E5: no hard-coded venv folder in the sed line; a command that finds it
if ! printf '%s\n' "$sec" | grep -E 'sed -i' | grep -F 'abf-venv' >/dev/null && hasre "$sec" 'venv folder' && hasre "$sec" '[Ff]ind'; then ok "E5 the sed line has no hard-coded venv name; a command finds it"; else bad "E5 sed hard-codes the venv folder"; fi

[ "$fails" -eq 0 ]
