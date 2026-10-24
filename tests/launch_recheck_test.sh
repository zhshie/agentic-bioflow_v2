#!/bin/bash
# launch_recheck.sh runs just before `tw launch` and must notice that a daemon
# died after step 0 (issue #7). Fake agent/egress scripts stand in for the site.
# TC-001..TC-020, TC-023..TC-026, TC-032, TC-033 (T1-T9 in the plan).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

mkdir "$TMP/scripts"; cp "$ROOT"/scripts/* "$TMP/scripts/" 2>/dev/null
P="$TMP/scripts/launch_recheck.sh"
cat > "$TMP/scripts/agent_ctl.sh" <<STUB
#!/bin/bash
echo "\$*" >> "$TMP/agent.calls"
if [ -e "$TMP/agent.up" ]; then echo "running pid=1 connection=c on h since t"; exit 0; fi
echo "not running"; exit 1
STUB
cat > "$TMP/scripts/egress_ctl.sh" <<STUB
#!/bin/bash
if [ -e "$TMP/egress.up" ]; then echo "up"; [ -e "$TMP/egress.warn" ] && echo "WARNING: started elsewhere"; exit 0; fi
echo "down"; exit 1
STUB
cat > "$TMP/scripts/check_resource_contract.sh" <<STUB
#!/bin/bash
echo x >> "$TMP/contract.called"; exit 0
STUB
printf '#!/bin/bash\necho x >> "%s/tw.called"\nexit 99\n' "$TMP" > "$TMP/tw"
chmod +x "$TMP"/tw "$TMP"/scripts/*.sh

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
mkssh()    { printf '#!/bin/bash\nexit %s\n' "$1" > "$TMP/ssh"; chmod +x "$TMP/ssh"; }
run() {
  LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" TW_BIN="$TMP/tw" bash "$P" 2>&1
}
has()    { printf '%-62s ' "$1"; grep -qE "$2" <<<"$3" && echo ok || { echo "FAIL: no line matching /$2/"; fails=$((fails+1)); }; }
hasnot() { printf '%-62s ' "$1"; grep -qE "$2" <<<"$3" && { echo "FAIL: unexpected /$2/"; fails=$((fails+1)); } || echo ok; }
code()   { printf '%-62s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: exit $2, wanted $3"; fails=$((fails+1)); }; }
up()   { : > "$TMP/$1.up"; }
down() { rm -f "$TMP/$1.up"; }

mkssh 0
settings 'reach: local' 'storage_root: /work/runs' 'workspace_id: 1' 'compute_env: ce'

# T1 / TC-003..005: agent dead
down agent; up egress; out=$(run); rc=$?
code   "T1 agent dead: exit 1"                       $rc 1
has    "T1 FAIL agent with the restart command"      '^FAIL +agent.*agent_ctl\.sh.*start' "$out"
has    "T1 egress still reported"                    '^OK +egress' "$out"

# T2 / TC-001,002
up agent; up egress; out=$(run); rc=$?
code   "T2 both up: exit 0"                          $rc 0
has    "T2 OK agent"                                 '^OK +agent' "$out"
has    "T2 OK egress"                                '^OK +egress' "$out"
hasnot "T2 no FAIL"                                  '^FAIL' "$out"

# T5 / TC-006,007
down egress; up agent; out=$(run); rc=$?
code   "T5 egress dead: exit 1"                      $rc 1
has    "T5 FAIL egress"                              '^FAIL +egress' "$out"
has    "T5 OK agent (independent)"                   '^OK +agent' "$out"

# TC-008: egress WARNING
up egress; up agent; : > "$TMP/egress.warn"; out=$(run); rc=$?; rm -f "$TMP/egress.warn"
code   "TC-008 WARNING: exit 1"                      $rc 1
has    "TC-008 FAIL egress-host"                     '^FAIL +egress-host' "$out"

# T6 / TC-009,010: no cache between two calls
up agent; up egress; run >/dev/null; rc=$?
code   "T6 first call: exit 0"                       $rc 0
down agent; out=$(run); rc=$?
code   "T6 second call after agent died: exit 1"     $rc 1
has    "T6 FAIL agent"                               '^FAIL +agent' "$out"

# T3 / TC-011..013: dead ssh master
settings 'reach: ssh' 'site_host: me@example.org' 'storage_root: /work/runs' 'workspace_id: 1' 'compute_env: ce'
mkssh 255; up agent; up egress; out=$(run); rc=$?
code   "T3 dead master: exit 1"                      $rc 1
has    "T3 FAIL reach"                               '^FAIL +reach' "$out"
has    "T3 names the host"                           'me@example\.org' "$out"
has    "TC-013 prints the line to paste"             'ControlMaster=auto' "$out"
hasnot "T3 does not go on to ask the site"           '(^| )(agent|egress)' "$out"

# T4 / TC-014,015
settings 'reach: none' 'storage_root: s3://b/runs' 'workspace_id: 1' 'compute_env: ce'
out=$(run); rc=$?
code   "T4 none: exit 0"                             $rc 0
has    "T4 OK reach none"                            '^OK +reach .*none' "$out"
hasnot "T4 no agent/egress"                          '(^| )(agent|egress)' "$out"

# T9 / TC-016..019: never tw, only `status`, no step-0 checks
[ -e "$TMP/tw.called" ] && { echo "FAIL: tw was called"; fails=$((fails+1)); } || echo "T9 tw never called                                            ok"
if [ -e "$TMP/agent.calls" ]; then
  bad=$(grep -vxE 'status' "$TMP/agent.calls" | head -1)
  [ -z "$bad" ] && echo "TC-017/018 agent only asked 'status'                          ok" || { echo "FAIL: agent_ctl called with '$bad'"; fails=$((fails+1)); }
else echo "FAIL: agent_ctl never called"; fails=$((fails+1)); fi
[ -e "$TMP/contract.called" ] && { echo "FAIL: resource contract was checked"; fails=$((fails+1)); } || echo "TC-019 no resource contract check                             ok"

# TC-020: no sleep / retry loops
printf '%-62s ' "TC-020 no sleep or retry loop"
grep -qE '(^|[^a-z_])(sleep|while|until)[ ;]' "$P" && { echo "FAIL"; fails=$((fails+1)); } || echo ok

# T7 / TC-023..026: step 8 of the skill
SK="$ROOT/skills/launch/SKILL.md"
s8=$(awk '/^8\. \*\*Launch/{f=1} /^9\. \*\*Watch/{f=0} f' "$SK")
has "T7 step 8 runs launch_recheck.sh"               'scripts/launch_recheck\.sh' "$s8"
has "T7 step 8 gives the restart path"               'agent_ctl\.sh start' "$s8"
has "T7 step 8 says what to do on FAIL"              'FAIL' "$s8"
printf '%-62s ' "T7 recheck comes before the first tw launch"
a=${s8%%launch_recheck.sh*}; b=${s8%%tw launch*}
if [[ "$s8" != *launch_recheck.sh* ]]; then echo "FAIL: absent"; fails=$((fails+1))
elif [[ "$s8" != *"tw launch"* ]] || [ ${#a} -lt ${#b} ]; then echo ok
else echo "FAIL: order"; fails=$((fails+1)); fi

# T8 / TC-032,033
head70=$(head -70 "$SK")
tail400=$(grep -A40 're-checks the two things that can die while you work' <<<"$head70" | tr '\n' ' ' | sed 's/.*re-checks the two things that can die while you work//' | cut -c1-400)
has "T8 gate sentence now says which reach it covers" 'reach' "$tail400"
n=$(grep -o 'launch_recheck\.sh' "$SK" | wc -l)
printf '%-62s ' "T8 launch_recheck.sh named at least twice"
[ "$n" -ge 2 ] && echo ok || { echo "FAIL: $n"; fails=$((fails+1)); }

[ $fails -eq 0 ] && echo "all ok" || { echo "$fails failure(s)"; exit 1; }
