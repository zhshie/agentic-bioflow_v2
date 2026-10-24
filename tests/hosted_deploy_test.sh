#!/bin/bash
# deploy/ (specs/hosted-deploy): the files that put one lab's platform on one host - three
# systemd user units, one Caddyfile template, one backup script, one env example - and the
# docs that tell the operator how to use them. Static checks, plus the backup script run
# against a fake data folder in a temporary directory. Nothing here starts a service, reaches
# the network or needs Caddy, systemd or Docker (TC-072).
# Test cases: specs/hosted-deploy/test-case.md (TC ids in the labels).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
fails=0
ok() { printf '%-92s ok\n' "$1"; }
bad() { printf '%-92s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
skip() { printf '%-92s skip%s\n' "$1" "${2:+: $2}"; }

D=deploy
UNITS=("$D/systemd/abf-serve.service.in" "$D/systemd/abf-mcp.service.in" "$D/systemd/abf-web.service.in")
CADDY=$D/Caddyfile.template
BACKUP=$D/backup.sh
ENVEX=$D/env.example
OPS=docs/OPERATIONS.md
INST=docs/INSTALL.md
CLI=platform/abf_platform/cli.py
# words that are tool names, built from pieces so this file never contains them as a call (TC-072)
TS="tail""scale"; SC="system""ctl"; CU="cu""rl"

# ---------- US1: units ----------
all_files=1
for f in "${UNITS[@]}" "$CADDY" "$BACKUP" "$ENVEX"; do [ -s "$f" ] || { all_files=0; bad "TC-001 $f exists and is not empty"; }; done
[ "$all_files" -eq 1 ] && ok "TC-001 the six deploy files exist and are not empty"
if [ -x "$BACKUP" ] && [ "$(head -n1 "$BACKUP" 2>/dev/null)" = '#!/usr/bin/env bash' ]; then ok "TC-002 backup.sh is executable and starts with the env-bash shebang"; else bad "TC-002 backup.sh executable + shebang"; fi

exec_line() { grep -E '^ExecStart=' "$1" 2>/dev/null | head -n1; }
for pair in "serve:abf-serve:8787" "mcp:abf-mcp:8788" "web:abf-web:8789"; do
  sub=${pair%%:*}; rest=${pair#*:}; unit=$D/systemd/${rest%%:*}.service.in; port=${rest##*:}
  el=$(exec_line "$unit")
  # TC-003 / TC-004: exactly its own subcommand, which exists in cli.py; <venv> placeholder
  nsub=$(printf '%s\n' "$el" | grep -oE ' (serve|mcp|web)( |$)' | wc -l)
  if printf '%s\n' "$el" | grep -qE "^ExecStart=%h/<venv>/bin/abf-platform $sub( |\$)" && [ "$nsub" -eq 1 ]; then ok "TC-003 $unit runs abf-platform $sub only"; else bad "TC-003 $unit runs abf-platform $sub only" "$el"; fi
  if grep -qE "sub\.add_parser\(\"$sub\"" "$CLI"; then ok "TC-004 '$sub' is a cli.py subcommand"; else bad "TC-004 '$sub' is a cli.py subcommand"; fi
  # TC-005 / TC-008: loopback host, the right port
  if printf '%s\n' "$el" | grep -qE -- "--host 127\.0\.0\.1( |\$)" && printf '%s\n' "$el" | grep -qE -- "--port $port( |\$)"; then ok "TC-005 $unit --host 127.0.0.1 --port $port"; else bad "TC-005 $unit --host 127.0.0.1 --port $port" "$el"; fi
  badhost=$(printf '%s\n' "$el" | grep -oE -- '--host +[^ ]+' | awk '{print $2}' | grep -vx '127.0.0.1' || true)
  if [ -z "$badhost" ]; then ok "TC-008 $unit has no non-loopback --host"; else bad "TC-008 $unit has no non-loopback --host" "$badhost"; fi
  # TC-006: the port is the default= of that subcommand in cli.py
  code_port=$(awk -v sub_="$sub" '
    $0 ~ "sub\\.add_parser\\(\"" sub_ "\"" {on=1; next}
    on && /sub\.add_parser\("/ {on=0}
    on && /add_argument\("--port"/ { if (match($0, /default=[0-9]+/)) { print substr($0, RSTART+8, RLENGTH-8); exit } }' "$CLI")
  if [ "$code_port" = "$port" ]; then ok "TC-006 $sub default port in cli.py is $port"; else bad "TC-006 $sub default port in cli.py is $port" "cli.py says '$code_port'"; fi
  # TC-010..014
  if grep -qx 'Restart=on-failure' "$unit" 2>/dev/null && grep -qx 'RestartSec=5' "$unit"; then ok "TC-010 $unit restarts on failure after 5 s"; else bad "TC-010 $unit restart"; fi
  if grep -qx 'EnvironmentFile=%h/.config/abf-platform/env' "$unit" 2>/dev/null; then ok "TC-011 $unit reads the env file"; else bad "TC-011 $unit EnvironmentFile"; fi
  if grep -qx 'WantedBy=default.target' "$unit" 2>/dev/null; then ok "TC-012 $unit is a user unit (default.target)"; else bad "TC-012 $unit WantedBy"; fi
  if grep -qx 'NoNewPrivileges=true' "$unit" 2>/dev/null && grep -qx 'PrivateTmp=true' "$unit"; then ok "TC-013 $unit NoNewPrivileges + PrivateTmp"; else bad "TC-013 $unit hardening"; fi
  if [ -f "$unit" ] && ! grep -qE 'ProtectHome|ProtectSystem' "$unit"; then ok "TC-014 $unit has no ProtectHome/ProtectSystem"; else bad "TC-014 $unit has no ProtectHome/ProtectSystem"; fi
done
for u in abf-mcp abf-web; do
  if exec_line "$D/systemd/$u.service.in" | grep -qF -- '--public-url ${ABF_PUBLIC_URL}'; then ok "TC-009 $u passes --public-url \${ABF_PUBLIC_URL}"; else bad "TC-009 $u passes --public-url"; fi
done
if exec_line "$D/systemd/abf-mcp.service.in" | grep -qE 'abf-platform mcp --http( |$)'; then ok "TC-003 mcp unit uses --http"; else bad "TC-003 mcp unit uses --http"; fi
# TC-007: nothing binds outward
if [ -f "$CADDY" ] && ! grep -nE '0\.0\.0\.0|\[::\]|--host +::' "${UNITS[@]}" "$CADDY" "$ENVEX" >/dev/null 2>&1; then ok "TC-007 no outward bind in units, Caddyfile, env example"; else bad "TC-007 no outward bind in units, Caddyfile, env example"; fi

# ---------- env example ----------
if grep -qx 'ABF_PUBLIC_URL=https://<your-domain>' "$ENVEX" 2>/dev/null && grep -qx 'ABF_PLATFORM_DB=<data-folder>/index.db' "$ENVEX" && grep -qx 'ABF_SITE_ADDRESS=<your-domain>' "$ENVEX"; then ok "TC-015 env.example has the three placeholder lines"; else bad "TC-015 env.example three lines"; fi
if grep -qF '~/.config/abf-platform/env' "$ENVEX" 2>/dev/null && grep -qE '600' "$ENVEX"; then ok "TC-015 env.example says where to copy it and mode 600"; else bad "TC-015 env.example copy + 600 note"; fi
badv=$(grep -vE '^\s*(#|$)' "$ENVEX" 2>/dev/null | awk '{v=substr($0, index($0,"=")+1); if (v=="" || v ~ /^<[^>]*>/ || v ~ /^https:\/\/<[^>]*>/ || v ~ /^127\.0\.0\.1/ || v ~ /^http:\/\/127\.0\.0\.1/) next; print}')
long=$(grep -vE '^\s*#' "$ENVEX" 2>/dev/null | grep -E '=[A-Za-z0-9_+/.-]{20,}' || true)
if [ -f "$ENVEX" ] && [ -z "$badv" ] && [ -z "$long" ]; then ok "TC-016 every env.example value is a placeholder"; else bad "TC-016 env.example values" "$badv $long"; fi
if grep -qE 'pat new' "$ENVEX" 2>/dev/null && grep -qiE 'once' "$ENVEX"; then ok "TC-017 env.example says a token is shown once and kept out of files"; else bad "TC-017 env.example token note"; fi
if [ -f "$ENVEX" ] && ! grep -qE 'ABF_PAT' "$ENVEX"; then ok "TC-017 env.example has no ABF_PAT variable"; else bad "TC-017 env.example has no ABF_PAT variable"; fi

# ---------- US2: Caddyfile ----------
# routes: "<path pattern>\t<port>" in file order; the bare catch-all is "*"
routes=$(awk '
  /^[ \t]*@[A-Za-z0-9_-]+[ \t]+path[ \t]/ { n=$1; sub(/^@/,"",n); $1=""; $2=""; paths[n]=$0; next }
  /^[ \t]*handle[ \t]+@[A-Za-z0-9_-]+[ \t]*\{/ { n=$2; sub(/^@/,"",n); cur=n; next }
  /^[ \t]*handle[ \t]*\{/ { cur="*"; next }
  /^[[:space:]]*reverse_proxy[[:space:]]/ { t=$2; sub(/^.*:/,"",t);
      if (cur=="*") print "*\t" t;
      else { m=split(paths[cur], a, /[ \t]+/); for (i=1;i<=m;i++) if (a[i]!="") print a[i] "\t" t }
      next }' "$CADDY" 2>/dev/null)
port_of() { printf '%s\n' "$routes" | awk -F'\t' -v p="$1" '$1==p {print $2; exit}'; }
want() { # <TC> <port> <paths...>
  local tc=$1 port=$2; shift 2; local p
  for p in "$@"; do
    if [ "$(port_of "$p")" = "$port" ]; then ok "$tc $p -> 127.0.0.1:$port"; else bad "$tc $p -> 127.0.0.1:$port" "got '$(port_of "$p")'"; fi
  done
}
want TC-018 8787 '/trace/*' '/user-info'
want TC-019 8787 '/agent/hello' '/agent/poll' '/agent/result/*'
want TC-020 8788 '/mcp*' '/.well-known/oauth-protected-resource*'
want TC-021 8789 '/.well-known/oauth-authorization-server' '/register' '/authorize' '/token' '/revoke' '/consent/*'
last=$(printf '%s\n' "$routes" | tail -n1)
lasth=$(grep -E '^[[:space:]]*handle[[:space:]]' "$CADDY" 2>/dev/null | tail -n1)
if [ "$last" = "$(printf '*\t8789')" ] && printf '%s\n' "$lasth" | grep -qE '^[[:space:]]*handle[[:space:]]*\{'; then ok "TC-022 the last handle is the bare catch-all to 8789"; else bad "TC-022 last handle is the catch-all to 8789" "$lasth"; fi
if [ -f "$CADDY" ] && ! grep -qE '/\.well-known/\*' "$CADDY"; then ok "TC-023 no /.well-known/* wildcard"; else bad "TC-023 no /.well-known/* wildcard"; fi
# TC-024: every prefix has a source in the platform code
src_ok() { # literal in the code, or the SDK function that makes it
  local p=${1%\*}
  grep -qF -- "\"$p" platform/abf_platform/*.py && return 0
  case "$1" in
    /authorize|/token|/revoke|/register) grep -q 'create_auth_routes(' platform/abf_platform/web.py ;;
    '/.well-known/oauth-protected-resource*') grep -q 'create_protected_resource_routes(' platform/abf_platform/http_auth.py ;;
    *) return 1 ;;
  esac
}
while IFS=$'\t' read -r p port; do
  { [ -z "$p" ] || [ "$p" = "*" ]; } && continue
  if src_ok "$p"; then ok "TC-024 $p has a source in platform/abf_platform"; else bad "TC-024 $p has a source in platform/abf_platform"; fi
done <<< "$routes"
# TC-025: every route in the code lands on the right backend (first matching rule wins)
backend_for() { local c=$1 p port; while IFS=$'\t' read -r p port; do [ -z "$p" ] && continue; if [ "$p" = "*" ] || [[ $c == $p ]]; then echo "$port"; return; fi; done <<< "$routes"; }
chk_routes() { # <file> <port>
  local f=$1 want=$2 r c
  for r in $(grep -oE 'Route\("[^"]+"' "$f" | sed -E 's/Route\("//; s/"$//' | sort -u); do
    c=$(printf '%s' "$r" | sed -E 's/\{[a-z]+\}/x/g')
    if [ "$(backend_for "$c")" = "$want" ]; then ok "TC-025 $(basename "$f") $r -> $want"; else bad "TC-025 $(basename "$f") $r -> $want" "got '$(backend_for "$c")'"; fi
  done
}
chk_routes platform/abf_platform/receiver.py 8787
chk_routes platform/abf_platform/agents.py 8787
chk_routes platform/abf_platform/web.py 8789
for c in /mcp /.well-known/oauth-protected-resource/mcp; do if [ "$(backend_for "$c")" = 8788 ]; then ok "TC-025 $c -> 8788"; else bad "TC-025 $c -> 8788"; fi; done
# TC-026
targets=$(grep -E '^[[:space:]]*reverse_proxy[[:space:]]' "$CADDY" 2>/dev/null | awk '{print $2}')
if [ -n "$targets" ] && ! printf '%s\n' "$targets" | grep -vqE '^127\.0\.0\.1:(8787|8788|8789)$'; then ok "TC-026 every reverse_proxy target is loopback 8787/8788/8789"; else bad "TC-026 reverse_proxy targets" "$targets"; fi
# TC-027 / 028
if grep -vE '^\s*(#|$)' "$CADDY" 2>/dev/null | head -n1 | grep -qF '{$ABF_SITE_ADDRESS}'; then ok "TC-027 site address is {\$ABF_SITE_ADDRESS}"; else bad "TC-027 site address is {\$ABF_SITE_ADDRESS}"; fi
if [ -f "$CADDY" ] && ! grep -vE '^\s*#' "$CADDY" | grep -qE '\.ts\.net|[A-Za-z0-9-]+\.(com|org|net|io|tw)\b'; then ok "TC-027 no hard-coded domain in the Caddyfile"; else bad "TC-027 no hard-coded domain in the Caddyfile"; fi
if [ -f "$CADDY" ] && ! grep -vE '^\s*#' "$CADDY" | grep -qE 'tls[[:space:]]+internal|auto_https[[:space:]]+off'; then ok "TC-028 nothing that turns certificates off"; else bad "TC-028 nothing that turns certificates off"; fi
# TC-029: no prefix twice with different backends; no broad rule ahead of a narrower one it would eat
dupe=$(printf '%s\n' "$routes" | awk -F'\t' 'seen[$1] && seen[$1]!=$2 {print $1} {seen[$1]=$2}')
if [ -n "$routes" ] && [ -z "$dupe" ]; then ok "TC-029 no prefix is routed to two backends"; else bad "TC-029 prefix routed twice" "$dupe"; fi
shadow=""; i=0; declare -a P Q
while IFS=$'\t' read -r p port; do [ -z "$p" ] && continue; P[i]=$p; Q[i]=$port; i=$((i+1)); done <<< "$routes"
for ((a=0; a<i; a++)); do for ((b=a+1; b<i; b++)); do
  [ "${P[a]}" = "*" ] && continue
  c=$(printf '%s' "${P[b]}" | sed 's/\*$/x/')
  if [ "${P[b]}" != "*" ] && [[ $c == ${P[a]} ]] && [ "${Q[a]}" != "${Q[b]}" ]; then shadow="$shadow ${P[a]}>${P[b]}"; fi
done; done
if [ "$i" -gt 0 ] && [ -z "$shadow" ]; then ok "TC-029 no broad rule eats a narrower one"; else bad "TC-029 shadowed rules" "$shadow"; fi
# TC-030 / 031
if [ -f "$CADDY" ] && ! grep -vE '^\s*#' "$CADDY" | grep -qE '^[[:space:]]*log\b'; then ok "TC-030 no log directive"; else bad "TC-030 no log directive"; fi
n=$(find "$D" -iname '*caddyfile*' 2>/dev/null | wc -l); if [ "$n" -eq 1 ]; then ok "TC-031 exactly one Caddyfile in deploy/"; else bad "TC-031 exactly one Caddyfile in deploy/" "$n"; fi

# ---------- US3: backup script ----------
if bash -n "$BACKUP" 2>/dev/null && grep -q '^set -euo pipefail' "$BACKUP"; then ok "TC-032 backup.sh parses and has set -euo pipefail"; else bad "TC-032 backup.sh syntax + set -euo pipefail"; fi
miss=""; for w in tokens.db platform.db web_signing.key uploads records; do grep -qF "$w" "$BACKUP" 2>/dev/null || miss="$miss $w"; done
if [ -z "$miss" ]; then ok "TC-033 backup.sh names the five things it backs up"; else bad "TC-033 backup.sh names" "missing:$miss"; fi
if grep -qE '\.backup' "$BACKUP" 2>/dev/null && ! grep -vE '^\s*#' "$BACKUP" | grep -E '(^|[ ;|&])cp[ ]' | grep -qE 'tokens|platform\.db|\$state[^_]'; then ok "TC-033 databases are copied with .backup, not cp"; else bad "TC-033 databases copied with .backup, not cp"; fi
if [ -f "$BACKUP" ] && ! grep -vE '^\s*#' "$BACKUP" | grep -qF 'index.db'; then ok "TC-037 backup.sh does not copy index.db"; else bad "TC-037 backup.sh does not copy index.db"; fi
if [ -f "$BACKUP" ] && ! grep -qE 'curl|wget|scp|rsync|ssh|rm ' "$BACKUP"; then ok "TC-071 backup.sh has no network tool and no rm"; else bad "TC-071 backup.sh has no network tool and no rm"; fi

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
PYBIN=python3; python3 -c 'import sqlite3' >/dev/null 2>&1 || PYBIN=python
SECRET="canary-$$-$RANDOM-secret-text"
mkdb() { "$PYBIN" - "$1" "$2" <<'PY'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1]); c.execute("create table t(v text)"); c.execute("insert into t values (?)", (sys.argv[2],)); c.commit(); c.close()
PY
}
dbval() { "$PYBIN" -c 'import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute("select v from t").fetchone()[0])' "$1"; }
fake() { # <dir> [leave-out words...]: a data folder
  local d=$1; shift; mkdir -p "$d"
  case " $* " in *" tokens "*) ;; *) mkdb "$d/tokens.db" "$SECRET-tokens" ;; esac
  case " $* " in *" platform "*) ;; *) mkdb "$d/platform.db" "$SECRET-platform" ;; esac
  case " $* " in *" key "*) ;; *) printf '%s' "$SECRET-key" > "$d/web_signing.key" ;; esac
  mkdir -p "$d/uploads/alice" "$d/records/run1"; echo up > "$d/uploads/alice/s.csv"; echo rec > "$d/records/run1/r.txt"
  case " $* " in *" index "*) mkdb "$d/index.db" "idx" ;; esac
}
run() { # <out-file> <env assignments...> -- <args...>
  local o=$1; shift; local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  ( cd "$TMP" && env -u ABF_PLATFORM_DB -u XDG_DATA_HOME -u ABF_PLATFORM_TOKENS -u ABF_PLATFORM_STATE -u ABF_PLATFORM_UPLOADS "${envs[@]}" bash "$ROOT/$BACKUP" "$@" ) >"$o" 2>&1
}
newest() { ls -d "$1"/abf-backup-* 2>/dev/null | tail -n1; }

if [ -f "$BACKUP" ]; then
# TC-034 / 036 / 037 / 078 / 079 (success)
fake "$TMP/d1" index
run "$TMP/o1" "ABF_PLATFORM_DB=$TMP/d1/index.db" -- "$TMP/out1"; rc=$?
B=$(newest "$TMP/out1")
if [ "$rc" -eq 0 ] && [ -n "$B" ] && [ -f "$B/tokens.db" ] && [ -f "$B/platform.db" ] && [ -f "$B/web_signing.key" ] && [ -f "$B/uploads/alice/s.csv" ] && [ -f "$B/records/run1/r.txt" ]; then ok "TC-034 backup of a full folder succeeds with all five"; else bad "TC-034 full backup" "rc=$rc dir=$B $(cat "$TMP/o1")"; fi
case "$(basename "${B:-x}")" in abf-backup-*) ok "TC-034 folder is named abf-backup-<UTC time>";; *) bad "TC-034 folder name";; esac
if [ "$(dbval "$B/tokens.db" 2>/dev/null)" = "$SECRET-tokens" ] && [ "$(dbval "$B/platform.db" 2>/dev/null)" = "$SECRET-platform" ]; then ok "TC-036 both database copies open and match"; else bad "TC-036 database copies match"; fi
if [ ! -e "$B/index.db" ]; then ok "TC-037 index.db was not copied"; else bad "TC-037 index.db was not copied"; fi
if grep -qF "$SECRET" "$TMP/o1"; then bad "TC-078 output has no secret text (success)"; else ok "TC-078 output has no secret text (success)"; fi
probe="$TMP/probe"; : > "$probe"; chmod 600 "$probe"
if [ "$(stat -c %a "$probe" 2>/dev/null)" = 600 ]; then
  perm_bad=$(find "$B" -type d ! -perm 700; find "$B" -type f ! -perm 600)
  if [ -z "$perm_bad" ]; then ok "TC-079 backup folders are 700 and files 600"; else bad "TC-079 permissions" "$perm_bad"; fi
else skip "TC-079 backup permissions" "this filesystem has no POSIX modes"; fi

# TC-035: no web_signing.key
fake "$TMP/d2" key
run "$TMP/o2" "ABF_PLATFORM_DB=$TMP/d2/index.db" -- "$TMP/out2"; rc=$?
B2=$(newest "$TMP/out2")
if [ "$rc" -eq 0 ] && [ -n "$B2" ] && [ ! -e "$B2/web_signing.key" ] && grep -qi 'signing' "$TMP/o2" && [ "$(wc -l < "$TMP/o2")" -le 2 ]; then ok "TC-035 no signing key: still succeeds, one plain line"; else bad "TC-035 no signing key" "rc=$rc: $(cat "$TMP/o2")"; fi
# TC-038 / 039 / 078 (failure)
fake "$TMP/d3" tokens
run "$TMP/o3" "ABF_PLATFORM_DB=$TMP/d3/index.db" -- "$TMP/out3"; rc=$?
if [ "$rc" -ne 0 ] && grep -q 'tokens.db' "$TMP/o3"; then ok "TC-038 missing tokens.db: non-zero and says tokens.db"; else bad "TC-038 missing tokens.db" "rc=$rc $(cat "$TMP/o3")"; fi
if grep -qF "$SECRET" "$TMP/o3"; then bad "TC-078 output has no secret text (failure)"; else ok "TC-078 output has no secret text (failure)"; fi
fake "$TMP/d4" platform
run "$TMP/o4" "ABF_PLATFORM_DB=$TMP/d4/index.db" -- "$TMP/out4"; rc=$?
if [ "$rc" -ne 0 ] && grep -q 'platform.db' "$TMP/o4"; then ok "TC-039 missing platform.db: non-zero and says platform.db"; else bad "TC-039 missing platform.db" "rc=$rc $(cat "$TMP/o4")"; fi
# TC-040: no destination
run "$TMP/o5" "ABF_PLATFORM_DB=$TMP/d1/index.db" -- ; rc=$?
if [ "$rc" -ne 0 ] && grep -qiE 'destination|folder' "$TMP/o5" && [ ! -d "$TMP/out5" ]; then ok "TC-040 no destination: non-zero, says what to give"; else bad "TC-040 no destination" "rc=$rc $(cat "$TMP/o5")"; fi
# TC-041: XDG_DATA_HOME
fake "$TMP/xdg/abf-platform"
run "$TMP/o6" "XDG_DATA_HOME=$TMP/xdg" -- "$TMP/out6"; rc=$?
B6=$(newest "$TMP/out6")
if [ "$rc" -eq 0 ] && [ -n "$B6" ] && [ "$(dbval "$B6/tokens.db")" = "$SECRET-tokens" ]; then ok "TC-041 XDG_DATA_HOME folder is found"; else bad "TC-041 XDG_DATA_HOME" "rc=$rc $(cat "$TMP/o6")"; fi
# TC-042: overrides
fake "$TMP/d7"; rm -f "$TMP/d7/tokens.db" "$TMP/d7/platform.db"; rm -rf "$TMP/d7/uploads"
mkdir -p "$TMP/elsewhere/up/bob"; echo ov > "$TMP/elsewhere/up/bob/o.csv"
mkdb "$TMP/elsewhere/t.db" "override-tokens"; mkdb "$TMP/elsewhere/p.db" "override-state"
run "$TMP/o7" "ABF_PLATFORM_DB=$TMP/d7/index.db" "ABF_PLATFORM_TOKENS=$TMP/elsewhere/t.db" "ABF_PLATFORM_STATE=$TMP/elsewhere/p.db" "ABF_PLATFORM_UPLOADS=$TMP/elsewhere/up" -- "$TMP/out7"; rc=$?
B7=$(newest "$TMP/out7")
if [ "$rc" -eq 0 ] && [ "$(dbval "$B7/tokens.db" 2>/dev/null)" = override-tokens ] && [ "$(dbval "$B7/platform.db" 2>/dev/null)" = override-state ] && [ -f "$B7/uploads/bob/o.csv" ]; then ok "TC-042 the three override variables are used"; else bad "TC-042 override variables" "rc=$rc $(cat "$TMP/o7")"; fi
else
  bad "TC-034..042,078,079 backup.sh runs" "deploy/backup.sh does not exist"
fi

# ---------- US4: docs ----------
sect() { # <file> <regex of the ## heading>: the text of that section
  awk -v pat="$2" '/^## /{on=($0 ~ pat)} on' "$1"; }
sub3() { # <file> <regex of a ## or ### heading>: until the next heading of two or more hashes
  awk -v pat="$2" '/^##+ /{on=($0 ~ pat)} on' "$1"; }
ops=$(tr -d '\r' < "$OPS"); inst=$(tr -d '\r' < "$INST")
host=$(sub3 "$OPS" '^### Hosting one lab')
s2=$(sect "$OPS" '^## 2[.]'); s3=$(sect "$OPS" '^## 3[.]'); s4=$(sect "$OPS" '^## 4[.]'); s5=$(sect "$OPS" '^## 5[.]'); s6=$(sect "$OPS" 'Not built yet')
has() { printf '%s\n' "$1" | grep -qF -- "$2"; }
# TC-043
n=$(printf '%s\n' "$ops" | grep -cF -- '--envfile')
if has "$ops" 'caddy run --config deploy/Caddyfile.template' && [ "$n" -ge 2 ] && has "$ops" 'ABF_SITE_ADDRESS=http://127.0.0.1:8080'; then ok "TC-043 both step lists feed ABF_SITE_ADDRESS to Caddy with --envfile"; else bad "TC-043 --envfile step in both lists" "envfile mentions: $n"; fi
# TC-044
if printf '%s\n' "$ops" | grep -qE '^### Hosting one lab'; then ok "TC-044 '### Hosting one lab' exists"; else bad "TC-044 '### Hosting one lab' exists"; fi
first=$(printf '%s\n' "$host" | sed -n 2,4p | tr '\n' ' ')
if has "$first" '託管一間實驗室'; then ok "TC-044 the section opens with 託管一間實驗室"; else bad "TC-044 section opens with 託管一間實驗室"; fi
if has "$s5" '### Hosting one lab' && has "$s5" '### Public URL'; then ok "TC-044 sits in section 5 beside Public URL"; else bad "TC-044 sits in section 5"; fi
# TC-045
miss=""; for w in 'deploy/systemd' 'deploy/Caddyfile.template' 'deploy/backup.sh' 'loginctl enable-linger' "$TS funnel" '<your-domain>'; do has "$ops" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-045 OPERATIONS names the deploy files, enable-linger, funnel, <your-domain>"; else bad "TC-045 OPERATIONS keywords" "missing:$miss"; fi
# TC-046
if has "$s2" "$TS funnel --bg 8080" && has "$s2" 'deploy/Caddyfile.template' && has "$s2" '8443' && has "$s2" '10000' && has "$s2" 'VPS'; then ok "TC-046 section 2: both front ends, funnel command, port limits"; else bad "TC-046 section 2"; fi
# TC-047 / 048
miss=""; for w in 'deploy/systemd/' '~/.config/systemd/user/' "$SC --user daemon-reload" 'enable --now' 'loginctl enable-linger'; do has "$s3" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-047 section 3: units dir and install steps"; else bad "TC-047 section 3" "missing:$miss"; fi
if has "$s3" 'Bearer tokens never go into a unit file'; then ok "TC-048 'tokens never go into a unit file' is kept"; else bad "TC-048 token sentence kept"; fi
# TC-049
if has "$s4" 'deploy/backup.sh' && printf '%s\n' "$s4" | grep -qiE 'restor' && printf '%s\n' "$s4" | grep -qiE 'stop .*three'; then ok "TC-049 section 4: backup.sh usage and restore"; else bad "TC-049 section 4"; fi
# TC-050
if has "$s6" 'Service-manager unit files'; then bad "TC-050 Not built yet: unit-files line removed"; else ok "TC-050 Not built yet: unit-files line removed"; fi
if has "$s6" 'Tailscale Funnel and proxy configuration'; then bad "TC-050 Not built yet: Funnel line removed"; else ok "TC-050 Not built yet: Funnel line removed"; fi
# TC-051..054
miss=""; for w in 'one lab' 'Python 3.10' '80' '443' 'systemd' 'enable-linger'; do has "$host" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-051 Hosting section: one lab per host, VPS needs, dedicated user + linger"; else bad "TC-051 Hosting section" "missing:$miss"; fi
if has "$host" "$CU -i https://<your-domain>/user-info" && has "$host" '401' && has "$host" 'X-ABF-Platform'; then ok "TC-052 Hosting section ends in the /user-info check"; else bad "TC-052 /user-info check"; fi
if printf '%s\n' "$host" | grep -qiE 'cron|timer'; then ok "TC-053 backup schedule example"; else bad "TC-053 backup schedule example"; fi
if printf '%s\n' "$host" | grep -qiE 'upgrad'; then ok "TC-054 upgrade steps"; else bad "TC-054 upgrade steps"; fi
# TC-056
oth=$(printf '%s\n%s\n' "$s2" "$host" | grep -oE 'https?://[^ )`"]+' | grep -vE '^https?://(<[a-z-]+>|127\.0\.0\.1|localhost)' || true)
if [ -z "$oth" ]; then ok "TC-056 new doc text uses only the placeholder hosts"; else bad "TC-056 placeholders only" "$oth"; fi
# TC-059: INSTALL got only a short pointer
if git rev-parse --verify -q origin/v3 >/dev/null 2>&1; then
  add=$(git diff origin/v3 -- "$INST" | grep -E '^\+[^+]' | sed 's/^+//')
  nadd=$(printf '%s\n' "$add" | grep -c . || true)
  snake=$(printf '%s\n' "$add" | grep -oE '`[^`]*`' | grep -E '[a-z]+_[a-z_]+' || true)
  if printf '%s\n' "$add" | grep -q 'Hosting one lab' && ! printf '%s\n' "$add" | grep -qE '^##' && [ "$nadd" -le 6 ] && [ -z "$snake" ]; then ok "TC-059 INSTALL.md: a short pointer, no new ##, no snake_case terms"; else bad "TC-059 INSTALL.md pointer" "added $nadd lines $snake"; fi
  if [ "$(printf '%s\n' "$inst" | grep -cE '^## ')" -eq 6 ]; then ok "TC-059 INSTALL.md still has six ## headings"; else bad "TC-059 INSTALL.md six headings"; fi
else skip "TC-059 INSTALL.md diff" "no origin/v3"; fi
# TC-062
while IFS= read -r p; do [ -z "$p" ] && continue; if [ -e "$p" ]; then ok "TC-062 doc path $p exists"; else bad "TC-062 doc path $p exists"; fi; done < <(printf '%s\n%s\n' "$ops" "$inst" | grep -oE '`(deploy/[^` ]+|tests/hosted_deploy_test\.sh)`' | tr -d '`' | sed 's/[.,;:]*$//' | sort -u)
# TC-064: docs/TESTING.md has the hosted-deploy steps
tst=$(sub3 docs/TESTING.md '^## .*[Hh]osted-deploy')
miss=""; for w in "$SC --user" 'http://127.0.0.1:8080' "$TS funnel --bg 8080" "$CU -i" 'X-ABF-Platform' '/mcp' 'deploy/backup.sh' 'pat list' 'ABF_SITE_ADDRESS=<your-domain>'; do has "$tst" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-064 TESTING.md has the hosted-deploy steps"; else bad "TC-064 TESTING.md hosted-deploy" "missing:$miss"; fi

# ---------- US5 / constitution ----------
if git rev-parse --verify -q origin/v3 >/dev/null 2>&1; then
  names=$(git diff --name-only origin/v3...HEAD)
  hit=$(printf '%s\n' "$names" | grep -E '^(platform/abf_platform/|platform/abf_station/|platform/abf_launch/|platform/pyproject\.toml|docs/ROADMAP\.md|\.github/|\.claude-plugin/plugin\.json|\.specify/memory/constitution\.md)|(^|/)spec\.md$' || true)
  if [ -z "$hit" ]; then ok "TC-066 no program code, gate file or spec touched (also TC-080: no schema change)"; else bad "TC-066 gate files touched" "$hit"; fi
  # the contract files arrive with the branch's own first commits; they must not change after that
  base_tc=$(git log --format=%H -n1 -- specs/hosted-deploy/test-case.md)
  if [ -n "$base_tc" ] && git diff --quiet "$base_tc" HEAD -- specs/hosted-deploy/test-case.md specs/hosted-deploy/test-case-overview.md; then ok "TC-066 the test case files are unchanged since they were written"; else bad "TC-066 test case files changed"; fi
else skip "TC-066 no-code-touched" "no git or no origin/v3"; fi
extra=$(find "$D" -type f 2>/dev/null | sort | tr '\n' ' ')
want_list="$(printf '%s\n' $D/Caddyfile.template $D/backup.sh $D/env.example $D/systemd/abf-mcp.service.in $D/systemd/abf-serve.service.in $D/systemd/abf-web.service.in | sort | tr '\n' ' ')"
if [ "$extra" = "$want_list" ]; then ok "TC-069 deploy/ holds exactly the six planned files"; else bad "TC-069 deploy/ contents" "$extra"; fi
# TC-083: no tracked *.service / *.timer; deploy/systemd holds exactly three *.service.in
if git rev-parse --git-dir >/dev/null 2>&1; then
  if git ls-files | grep -E '\.(service|timer)$' >/dev/null; then bad "TC-083 a tracked *.service or *.timer exists"; else
    sd=$(git ls-files "$D/systemd" | tr '\n' ' ')
    [ "$(git ls-files "$D/systemd" | wc -l)" -eq 3 ] && [ -z "$(git ls-files "$D/systemd" | grep -v '\.service\.in$')" ] && ok "TC-083 units ship as three .service.in templates" || bad "TC-083 deploy/systemd contents" "$sd"
  fi
else skip "TC-083 templates" "no git"; fi
# TC-084: 127.0.0.1:8080 only on comment lines of env.example
if grep -F 'http://127.0.0.1:8080' "$ENVEX" | grep -vE '^[[:space:]]*#' >/dev/null; then bad "TC-084 8080 appears on a non-comment line"; else ok "TC-084 8080 only in comments"; fi
# TC-085: no uploads/ or records/ -> rc 0, one skip line each, nothing empty backed up
fake "$TMP/d8" index; rm -rf "$TMP/d8/uploads" "$TMP/d8/records"
run "$TMP/o8" "ABF_PLATFORM_DB=$TMP/d8/index.db" -- "$TMP/out8"; rc=$?
B8=$(newest "$TMP/out8")
if [ "$rc" -eq 0 ] && [ -f "$B8/tokens.db" ] && [ -f "$B8/platform.db" ] && [ ! -e "$B8/uploads" ] && [ ! -e "$B8/records" ] && grep -q uploads "$TMP/o8" && grep -q records "$TMP/o8"; then ok "TC-085 missing uploads/records is a skip, not an error"; else bad "TC-085 missing uploads/records" "rc=$rc $(cat "$TMP/o8")"; fi
# TC-086: install step says copy abf-*.service.in and drop the .in
if grep -q 'abf-\$u.service.in' "$OPS" && grep -qiE 'drop the `?\.in`?' "$OPS"; then ok "TC-086 OPERATIONS install step copies .service.in and drops .in"; else bad "TC-086 install step"; fi
# TC-072: this file starts nothing (no tool name in command position)
if grep -nE '^[[:space:]]*(docker|caddy|systemctl|tailscale|curl|wget)([[:space:]]|$)' "$HERE/hosted_deploy_test.sh" >/dev/null; then bad "TC-072 this test calls no service tool"; else ok "TC-072 this test calls no service tool"; fi
# TC-073: systemd-analyze is never relied on
if command -v systemd-analyze >/dev/null 2>&1; then ok "TC-073 systemd-analyze present but not relied on"; else skip "TC-073 systemd-analyze" "not installed; not needed"; fi
# TC-075 .. 077: no secret, no real host, no personal path
KEYHDR="-----BEGIN ""PRIVATE KEY"
scan=("$D" "$OPS" "$INST")
if grep -rnE 'abf_pat_[A-Za-z0-9]{8,}|Bearer +[A-Za-z0-9_-]{8,}|(password|ABF_PAT)=[^<[:space:]]' "${scan[@]}" 2>/dev/null | grep -v 'Bearer <' >/dev/null; then bad "TC-075 no token, password or key in deploy/ or the two docs"; else ok "TC-075 no token or password in deploy/ or the two docs"; fi
if grep -rqF -- "$KEYHDR" "${scan[@]}" 2>/dev/null; then bad "TC-075 no private-key header"; else ok "TC-075 no private-key header"; fi
if grep -rnE 'DESKTOP-7J5L5BJ|\.ts\.net|u9613010' "${scan[@]}" >/dev/null 2>&1; then bad "TC-076 no real host or account"; else ok "TC-076 no real host or account"; fi
if grep -rnE '/(home|Users)/[A-Za-z][A-Za-z0-9_.-]*/|[A-Za-z]:\\Users' "${scan[@]}" 2>/dev/null | grep -v '<' >/dev/null; then bad "TC-077 no personal absolute path"; else ok "TC-077 no personal absolute path"; fi

[ "$fails" -eq 0 ]
