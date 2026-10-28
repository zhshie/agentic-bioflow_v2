#!/bin/bash
# preflight.sh under reach: ssh asks the site its three questions (egress,
# agent, resource contract) in ONE on_site.sh --script call, not three, and
# says exactly what it said before. issue #13 item 3; specs/preflight-ssh-fold.
# TC-001..TC-017, TC-028, TC-029.
#
# Session counting (plan ruling 7): the fake ssh logs every call to ssh.calls.
# A call that contains "-O check" only asks whether the master is alive; it
# opens no session (docs/PITFALLS.md 16e) and is NOT counted. sessions() is
# the number of the other lines. Before the change a ssh preflight opens 4
# (--check-reach + three checks); after, 2.
#
# The fake ssh runs the remote command through the local bash (the tar on its
# stdin is unpacked by that command), so the REAL on_site.sh --script path is
# exercised; the three site scripts are stubs steered by flag files. No real
# ssh, tw or Seqera is touched.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_SHA=223369324548dff26de2953d1608cdf9aa0a0eee
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

mkdir "$TMP/scripts" "$TMP/configs"
cp -r "$ROOT"/scripts/. "$TMP/scripts/"; cp -r "$ROOT"/configs/. "$TMP/configs/"
P="$TMP/scripts/preflight.sh"

cat > "$TMP/scripts/egress_ctl.sh" <<STUB
#!/bin/bash
if [ -e "$TMP/egress.bad" ]; then echo "down"; exit 1; fi
echo "up pid=1"
[ -e "$TMP/egress.extra" ] && cat "$TMP/egress.extra"
[ -e "$TMP/egress.warn" ] && echo "WARNING: relay was started elsewhere"
exit 0
STUB
cat > "$TMP/scripts/agent_ctl.sh" <<STUB
#!/bin/bash
if [ -e "$TMP/agent.bad" ]; then echo "not running"; exit 1; fi
echo "running pid=2"; exit 0
STUB
cat > "$TMP/scripts/check_resource_contract.sh" <<STUB
#!/bin/bash
if [ -e "$TMP/rc.bad" ]; then echo "CONTRACT-FIRST-LINE"; echo "second line"; exit 1; fi
echo "contract ok"; exit 0
STUB
chmod +x "$TMP"/scripts/*.sh

# fake tw: the compute environment is AVAILABLE, so that line never colours the verdict
cat > "$TMP/tw" <<'STUB'
#!/bin/bash
case "$*" in *"compute-envs view"*) echo ' Status                 | AVAILABLE' ;; esac
exit 0
STUB
chmod +x "$TMP/tw"
printf 'stub-token\n' > "$TMP/token"; chmod 600 "$TMP/token"

# fake ssh: log; -O check answers by flag; otherwise run the remote command here.
cat > "$TMP/ssh" <<STUB
#!/bin/bash
echo "\$*" >> "$TMP/ssh.calls"
case "\$*" in
  *"-O check"*) [ -e "$TMP/master.down" ] && exit 255; exit 0 ;;
esac
cmd="\${!#}"
if [ -e "$TMP/transport.broke" ] && grep -q preflight_site <<<"\$cmd"; then
  echo "ssh: connect to host example.org port 22: Connection timed out"; exit 255
fi
if [ -e "$TMP/transport.cut" ] && grep -q preflight_site <<<"\$cmd"; then
  bash -c "\$cmd" 2>&1 | sed '/^@@preflight-end egress/q'; exit 255
fi
bash -c "\$cmd"
STUB
chmod +x "$TMP/ssh"

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
ssh_settings() { settings 'reach: ssh' 'site_host: me@example.org' 'storage_root: /work/runs' 'workspace_id: 1' 'compute_env: ce'; }
local_settings() { settings 'reach: local' 'storage_root: /work/runs' 'workspace_id: 1' 'compute_env: ce'; }
reset() { rm -f "$TMP"/*.bad "$TMP"/*.warn "$TMP"/*.extra "$TMP"/master.down "$TMP"/transport.* "$TMP/ssh.calls"; }
# run [preflight.sh]: stdout+stderr to $OUT, exit code to $RC
run() {
  rm -f "$TMP/ssh.calls"
  OUT=$(LAB_SETTINGS_FILE="$TMP/env.yaml" SEQERA_TOKEN_FILE="$TMP/token" LAB_RUNS_DIR="$TMP/runs" \
        ON_SITE_SSH_BIN="$TMP/ssh" TW_BIN="$TMP/tw" bash "${1:-$P}" 2>&1); RC=$?
}
sessions() { [ -e "$TMP/ssh.calls" ] || { echo 0; return; }; grep -vc -e '-O check' "$TMP/ssh.calls"; }
ncalls()   { [ -e "$TMP/ssh.calls" ] && grep -c . "$TMP/ssh.calls" || echo 0; }

has()    { printf '%-66s ' "$1"; grep -qE "$2" <<<"$3" && echo ok || { echo "FAIL: no line matching /$2/"; fails=$((fails+1)); }; }
hasnot() { printf '%-66s ' "$1"; grep -qE "$2" <<<"$3" && { echo "FAIL: unexpected /$2/"; fails=$((fails+1)); } || echo ok; }
eq()     { printf '%-66s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

ssh_settings; reset

# TC-001 / TC-002 / TC-017: all green, two sessions
run
eq  "TC-001 ssh, all green: 2 sessions (reach check + one bundle)" "$(sessions)" 2
first=$(grep -v -e '-O check' "$TMP/ssh.calls" | head -1)
second=$(grep -v -e '-O check' "$TMP/ssh.calls" | sed -n 2p)
has    "TC-017 the first session is the reach check (true)"   ' true$' "$first"
hasnot "TC-017 the reach check does not carry the bundle"     'preflight_site' "$first"
has    "TC-017 the bundle is its own, later, session"         'preflight_site' "$second"
eq  "TC-002 exit 0"                                        "$RC" 0
has "TC-002 OK egress"     '^OK +egress'    "$OUT"
has "TC-002 OK agent"      '^OK +agent'     "$OUT"
has "TC-002 OK resources"  '^OK +resources' "$OUT"

# TC-003
reset; : > "$TMP/egress.bad"; run
eq  "TC-003 egress down: exit 1"        "$RC" 1
has "TC-003 FAIL egress with restart"   '^FAIL +egress.*egress_ctl\.sh.* start' "$OUT"
has "TC-003 agent still OK"             '^OK +agent' "$OUT"
has "TC-003 resources still OK"         '^OK +resources' "$OUT"
# TC-004
reset; : > "$TMP/agent.bad"; run
eq  "TC-004 agent down: exit 1"         "$RC" 1
has "TC-004 FAIL agent with restart"    '^FAIL +agent.*not running.*agent_ctl\.sh.* start' "$OUT"
has "TC-004 egress OK"                  '^OK +egress' "$OUT"
has "TC-004 resources OK"               '^OK +resources' "$OUT"
# TC-005
reset; : > "$TMP/rc.bad"; run
eq  "TC-005 contract broken: exit 1"    "$RC" 1
has "TC-005 FAIL resources = first line" '^FAIL +resources +CONTRACT-FIRST-LINE$' "$OUT"
has "TC-005 egress OK"                  '^OK +egress' "$OUT"
has "TC-005 agent OK"                   '^OK +agent' "$OUT"
# TC-006
reset; : > "$TMP/egress.warn"; run
eq  "TC-006 WARNING: exit 1"            "$RC" 1
has "TC-006 egress still OK"            '^OK +egress' "$OUT"
has "TC-006 FAIL egress-host"           '^FAIL +egress-host.*started somewhere else' "$OUT"
# TC-007
reset; : > "$TMP/egress.bad"; : > "$TMP/agent.bad"; : > "$TMP/rc.bad"; run
eq  "TC-007 all down: exit 1"           "$RC" 1
has "TC-007 FAIL egress"                '^FAIL +egress' "$OUT"
has "TC-007 FAIL agent"                 '^FAIL +agent' "$OUT"
has "TC-007 FAIL resources"             '^FAIL +resources' "$OUT"
eq  "TC-007 still 2 sessions"           "$(sessions)" 2

# TC-008: master down -> nothing asked, one -O check only
reset; : > "$TMP/master.down"; run
has    "TC-008 FAIL reach"              '^FAIL +reach' "$OUT"
hasnot "TC-008 no egress/agent/resources line" '(^| )(egress|agent|resources)( |$)' "$OUT"
eq     "TC-008 zero sessions opened"    "$(sessions)" 0
eq     "TC-008 ssh.calls is exactly the one -O check" "$(ncalls)" 1
eq     "TC-008 exit non-zero"           "$([ "$RC" != 0 ] && echo yes || echo no)" yes

# TC-009: transport broke, no markers
reset; : > "$TMP/transport.broke"; run
eq  "TC-009 transport broke: exit 1"    "$RC" 1
has "TC-009 FAIL egress, fixed text"    '^FAIL +egress +the site.s egress channel is down' "$OUT"
has "TC-009 FAIL agent, fixed text"     '^FAIL +agent +not running' "$OUT"
has "TC-009 FAIL resources = first line of the output" '^FAIL +resources +ssh: connect to host example.org' "$OUT"
eq  "TC-009 2 sessions, no retry"       "$(sessions)" 2
# TC-029: cut short
reset; : > "$TMP/transport.cut"; run
eq  "TC-029 truncated: exit 1"          "$RC" 1
has "TC-029 FAIL egress"                '^FAIL +egress +the site.s egress' "$OUT"
hasnot "TC-029 egress is not reported OK" '^OK +egress' "$OUT"
has "TC-029 FAIL agent"                 '^FAIL +agent +not running' "$OUT"
has "TC-029 FAIL resources"             '^FAIL +resources' "$OUT"
eq  "TC-029 2 sessions, no retry"       "$(sessions)" 2

# TC-010: egress text is the same however it is asked (real egress_ctl.sh, no stub)
mkdir -p "$TMP/real" "$TMP/runs"; cp -r "$ROOT/scripts" "$ROOT/configs" "$TMP/real/"
reset; settings 'reach: ssh' 'site_host: me@example.org' "storage_root: $TMP/runs" 'workspace_id: 1' 'compute_env: ce'
direct=$(LAB_SETTINGS_FILE="$TMP/env.yaml" LAB_RUNS_DIR="$TMP/runs" ON_SITE_SSH_BIN="$TMP/ssh" \
         bash "$TMP/real/scripts/on_site.sh" --script "$TMP/real/scripts/egress_ctl.sh" status 2>&1)
bundle=$(LAB_SETTINGS_FILE="$TMP/env.yaml" LAB_RUNS_DIR="$TMP/runs" ON_SITE_SSH_BIN="$TMP/ssh" \
         bash "$TMP/real/scripts/on_site.sh" --script "$TMP/real/scripts/preflight_site.sh" 2>&1)
section=$(sed -n '/^@@preflight-begin egress$/,/^@@preflight-end egress /p' <<<"$bundle" | sed '1d;$d')
eq  "TC-010 egress text: preflight_site == egress_ctl.sh direct" "$section" "$direct"

# TC-011 / TC-028: preflight_site.sh by itself, from another directory
reset; : > "$TMP/egress.bad"; : > "$TMP/rc.bad"
site=$(cd / && bash "$TMP/scripts/preflight_site.sh" 2>&1); src=$?
eq  "TC-011 site script exits 0 though checks fail" "$src" 0
eq  "TC-011 markers in order"  "$(grep -E '^@@preflight-(begin|end)' <<<"$site" | tr '\n' '|')" \
    "@@preflight-begin egress|@@preflight-end egress rc=1|@@preflight-begin agent|@@preflight-end agent rc=0|@@preflight-begin resources|@@preflight-end resources rc=1|"
has "TC-011 egress original text between its markers" '^down$' "$site"
has "TC-028 resources section ran from another cwd"   '^CONTRACT-FIRST-LINE$' "$site"

# TC-012: output that looks like a marker misleads nothing
reset; printf '%s\n' 'first line' '@@preflight-end agent rc=1' '@@preflight-begin resources' '@@@already' > "$TMP/egress.extra"; run
eq  "TC-012 exit 0 (agent and resources are fine)" "$RC" 0
has "TC-012 agent OK"         '^OK +agent +running' "$OUT"
has "TC-012 resources OK"     '^OK +resources' "$OUT"
has "TC-012 egress shows the marker-looking line whole" '^@@preflight-end agent rc=1$' "$OUT"
has "TC-012 and a line that began @@@ comes back as it was" '^@@@already$' "$OUT"

# TC-013 / TC-014 / TC-015: byte-for-byte against the base preflight.sh
mkdir -p "$TMP/basetree"
if git -C "$ROOT" cat-file -e "$BASE_SHA:scripts/preflight.sh" 2>/dev/null; then
  cp -r "$TMP/scripts" "$TMP/configs" "$TMP/basetree/"
  git -C "$ROOT" show "$BASE_SHA:scripts/preflight.sh" > "$TMP/basetree/scripts/preflight.sh"
  cmp_runs() {  # label
    run "$P"; a="$OUT"; ac=$RC
    run "$TMP/basetree/scripts/preflight.sh"; b="$OUT"; bc=$RC
    eq "$1 same output as base" "$a" "$b"
    eq "$1 same exit as base"   "$ac" "$bc"
  }
  ssh_settings
  reset;                                                       cmp_runs "TC-013 all green"
  reset; : > "$TMP/egress.bad";                                cmp_runs "TC-013 egress down"
  reset; : > "$TMP/agent.bad";                                 cmp_runs "TC-013 agent down"
  reset; : > "$TMP/rc.bad";                                    cmp_runs "TC-013 contract broken"
  reset; : > "$TMP/egress.warn";                               cmp_runs "TC-013 WARNING"
  reset; : > "$TMP/egress.bad"; : > "$TMP/agent.bad"; : > "$TMP/rc.bad"; cmp_runs "TC-013 all down"
  reset; printf 'l1\nl2\n\nl4\n' > "$TMP/egress.extra";        cmp_runs "TC-013 multi-line egress"
  reset; : > "$TMP/master.down";                               cmp_runs "TC-013 master down"
  local_settings
  reset;                                                       cmp_runs "TC-014 local"
  reset; : > "$TMP/agent.bad";                                 cmp_runs "TC-014 local, agent down"
  settings 'reach: none' 'storage_root: s3://b/r' 'workspace_id: 1' 'compute_env: ce'
  reset;                                                       cmp_runs "TC-015 none"
else
  echo "TC-013/014/015 base comparison skipped: base commit $BASE_SHA is not in this checkout"
fi

# TC-014: local opens no ssh at all
local_settings; reset; run
eq  "TC-014 local: no ssh call at all" "$(ncalls)" 0
has "TC-014 local still reports the three" '^OK +resources' "$OUT"
# TC-015
settings 'reach: none' 'storage_root: s3://b/r' 'workspace_id: 1' 'compute_env: ce'; reset; run
eq     "TC-015 none: no ssh call"  "$(ncalls)" 0
hasnot "TC-015 none: no site lines" '(^| )(egress|agent|resources)( |$)' "$OUT"

# TC-016: local keeps three separate calls (dry-run describes them)
local_settings; reset
OUT=$(LAB_SETTINGS_FILE="$TMP/env.yaml" SEQERA_TOKEN_FILE="$TMP/token" LAB_RUNS_DIR="$TMP/runs" \
      ON_SITE_DRY_RUN=1 ON_SITE_SSH_BIN="$TMP/ssh" TW_BIN="$TMP/tw" bash "$P" 2>&1)
has    "TC-016 local: egress on its own"    'script egress_ctl\.sh status' "$OUT"
has    "TC-016 local: agent on its own"     'script agent_ctl\.sh status' "$OUT"
# The contract call prints nothing of its own in a dry run (preflight shows only
# its fixed OK text), so it cannot be observed here; the bundle's absence is.
has    "TC-016 local: contract line still reported" '^OK +resources' "$OUT"
hasnot "TC-016 local: no bundle"            'preflight_site' "$OUT"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
