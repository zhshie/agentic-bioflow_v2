#!/bin/bash
# studio-embed: the files around the page that embeds RStudio - the systemd user-unit template that runs RStudio Server as the
# person (not root) on 127.0.0.1 only, the line in the env example, the docs - checked by shape. Nothing here starts RStudio, installs
# it or touches a unit; whether it really starts is the manual TC-036 to TC-040 of docs/TESTING.md, "studio-embed".
# The page and the command are checked by platform/tests/test_studio_embed.py.
# Test cases: specs/studio-embed/test-case.md (TC ids in the labels).
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
check() { local l="$1"; shift; if "$@"; then ok "$l"; else bad "$l"; fi; }

UNIT=deploy/systemd/abf-rstudio.service.in
ENVEX=deploy/env.example
OPS=docs/OPERATIONS.md
TST=docs/TESTING.md
PLAT=docs/PLATFORM.md
unit=$(tr -d '\r' < "$UNIT" 2>/dev/null || true)
code=$(printf '%s\n' "$unit" | grep -vE '^\s*#')      # the lines that are not comments

# ---------- TC-029: the unit ----------
check "TC-029 the unit template exists" test -f "$UNIT"
first=$(printf '%s\n' "$unit" | head -n1)
if hasre "$first" '^# Not '; then ok "TC-029 the first line says what it is not"; else bad "TC-029 first line starts '# Not '" "$first"; fi
exec_line=$(printf '%s\n' "$code" | grep -E '^ExecStart=' | head -n1)
miss=""
for w in 'rserver' '--www-address' '--www-port' '--www-frame-origin' '--auth-none'; do has "$exec_line" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-029 ExecStart runs rserver with the four options"; else bad "TC-029 ExecStart options" "missing:$miss"; fi
if has "$exec_line" '--www-frame-origin=${ABF_PUBLIC_URL}'; then ok "TC-029 the frame origin is \${ABF_PUBLIC_URL}"; else bad "TC-029 www-frame-origin value"; fi
check "TC-029 EnvironmentFile=%h/.config/abf-platform/env" has "$code" 'EnvironmentFile=%h/.config/abf-platform/env'
check "TC-029 WantedBy=default.target" has "$code" 'WantedBy=default.target'
check "TC-029 Restart=on-failure" has "$code" 'Restart=on-failure'
# the option names that exist in the package's rserver binary (read from its strings); a misspelling fails here
for o in $(printf '%s\n' "$exec_line" | grep -oE -- '--[a-z][a-z-]+' | sort -u); do
  case "$o" in --www-address|--www-port|--www-frame-origin|--auth-none|--server-user|--server-daemonize|--server-data-dir|--server-pid-file|--secure-cookie-key-file|--database-config-file|--www-same-site) ;;
    *) bad "TC-029 option $o is not one of the rserver options seen in the package";; esac
done

# ---------- TC-030: not root ----------
if printf '%s\n' "$unit" | grep -nE 'User=root|sudo|multi-user\.target|AmbientCapabilities|CapabilityBoundingSet|/etc/systemd/system|--server-user[ =]+root' >/dev/null; then bad "TC-030 the unit runs as root or asks for privilege"; else ok "TC-030 no root, no sudo, no system target, no capability"; fi
if has "$exec_line" '--server-user=%u'; then ok "TC-030 rserver runs as the person (%u)"; else bad "TC-030 --server-user=%u"; fi

# ---------- TC-031: loopback only ----------
addr=$(printf '%s\n' "$unit" | grep -oE -- '--www-address[= ][^ ]*' | tr -d "'\"")
if [ -n "$addr" ] && [ "$(printf '%s\n' "$addr" | sort -u)" = "--www-address=127.0.0.1" ]; then ok "TC-031 www-address is present and is 127.0.0.1"; else bad "TC-031 www-address" "$addr"; fi
if printf '%s\n' "$unit" | grep -nE '0\.0\.0\.0|\[::\]|::|www-socket' >/dev/null; then bad "TC-031 an outward bind or a socket in the unit"; else ok "TC-031 no 0.0.0.0, [::], ::, www-socket"; fi
if grep -qE '^# *ABF_STUDIO_URL=http://127\.0\.0\.1:[0-9]+$' "$ENVEX"; then ok "TC-031 env.example has the commented line with a loopback value"; else bad "TC-031 env.example line"; fi

# ---------- TC-032: one port, not the platform's own ----------
nports=$(printf '%s\n' "$code" | grep -oE 'ABF_STUDIO_[A-Z_]+' | sort -u | tr '\n' ' ')
if [ "$nports" = "ABF_STUDIO_URL " ]; then ok "TC-032 the port comes from ABF_STUDIO_URL only"; else bad "TC-032 setting names in the unit" "$nports"; fi
if printf '%s\n' "$code" | grep -E -- '--www-port[= ]+[0-9]' >/dev/null; then bad "TC-032 a literal port in the unit"; else ok "TC-032 no literal port in the unit"; fi
exline=$(grep -E '^# *ABF_STUDIO_URL=' "$ENVEX" | head -n1)
port=${exline##*:}
if [ -n "$port" ] && ! printf '%s\n' "$port" | grep -qE '^878[789]$' && [ "$port" = 8790 ]; then ok "TC-032 the example port is 8790, not 8787-8789"; else bad "TC-032 example port" "$port"; fi
ops=$(tr -d '\r' < "$OPS"); tst=$(tr -d '\r' < "$TST"); plat=$(tr -d '\r' < "$PLAT")
rs=$(printf '%s\n' "$ops" | awk '/RStudio in the downstream page/{on=1} on' | head -n 60)
if has "$rs" "http://127.0.0.1:$port"; then ok "TC-032 OPERATIONS names the same address as the example"; else bad "TC-032 OPERATIONS address"; fi
if bash tests/hosted_deploy_test.sh 2>&1 | grep -E 'TC-01[56]' | grep -q FAIL; then bad "TC-032 hosted_deploy_test TC-015/016 on env.example"; else ok "TC-032 env.example still passes hosted_deploy_test TC-015/016"; fi

# ---------- TC-033: the two tests that count files were rewritten, nothing else under deploy/ ----------
if git rev-parse --git-dir >/dev/null 2>&1; then
  base=$(git merge-base origin/v3 HEAD 2>/dev/null || true)
  if [ -n "$base" ]; then
    added=$(git diff --name-only --diff-filter=A "$base" -- deploy/ | tr '\n' ' ')
    if [ "$added" = "deploy/systemd/abf-rstudio.service.in " ]; then ok "TC-033 deploy/ gains exactly the one file"; else bad "TC-033 files added under deploy/" "$added"; fi
    # TC-034
    changed=$(git diff --name-only "$base")
    forbidden=$(printf '%s\n' "$changed" | grep -E '^(\.github/|hooks/|\.specify/memory/constitution\.md|\.claude-plugin/plugin\.json|platform/abf_platform/(confirm|store)\.py|platform/abf_station/|platform/pyproject\.toml|pyproject\.toml|requirements)' || true)
    if [ -z "$forbidden" ]; then ok "TC-034 none of the files the plan forbids is changed, no new dependency"; else bad "TC-034 forbidden files changed" "$forbidden"; fi
    rfiles=$(git ls-files | grep -iE '\.deb$|rserver\.conf|rstudio.*\.(tar|zip|rpm)$|/rserver$' || true)
    if [ -z "$rfiles" ]; then ok "TC-034 no RStudio file in the repository"; else bad "TC-034 RStudio files" "$rfiles"; fi
  else skip "TC-033 TC-034 diff checks" "no origin/v3 to compare with"; fi
else skip "TC-033 TC-034" "no git"; fi

# ---------- TC-035: OPERATIONS ----------
miss=""
for w in 'RStudio in the downstream page' 'AGPL' 'does not ship' 'systemctl --user enable --now abf-rstudio' 'systemctl --user status abf-rstudio' 'systemctl --user stop abf-rstudio' \
         'systemctl --user disable --now abf-rstudio' 'sudo systemctl disable --now rstudio-server' '127.0.0.1' 'ss -ltn' 'Posit' \
         '任何能登入這台電腦的人與這台電腦上的任何程式都連得到它，所以只適合個人電腦' '不得把這個埠對外公開'; do has "$rs" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-035 OPERATIONS has the RStudio step with install, enable, status, stop, remove, the warning"; else bad "TC-035 OPERATIONS step" "missing:$miss"; fi
if hasre "$rs" 'root' && hasre "$rs" 'before'; then ok "TC-035 it says the package starts a root service that must be disabled first"; else bad "TC-035 root service warning"; fi
if has "$ops" 'systemctl --user stop abf-serve abf-web abf-mcp abf-station@<name>' && has "$ops" 'systemctl --user disable --now abf-serve abf-web abf-mcp abf-station@<name>'; then ok "TC-035 the four-unit command lines are as they were"; else bad "TC-035 four-unit lines"; fi
cl=$(tr -d '\r' < CHANGELOG.md)
ks=$(printf '%s\n' "$cl" | grep -n -- '^- keep-submissions:' | head -n1 | cut -d: -f1); se=$(printf '%s\n' "$cl" | grep -n -- '^- studio-embed:' | head -n1 | cut -d: -f1)
if [ -n "$ks" ] && [ -n "$se" ] && [ "$se" -gt "$ks" ]; then ok "TC-035 CHANGELOG has a studio-embed bullet after keep-submissions"; else bad "TC-035 CHANGELOG order" "keep=$ks studio=$se"; fi

# ---------- TC-041: no secret ----------
pat='abf_pat_[A-Za-z0-9]{8,}|Bearer +[A-Za-z0-9_-]{8,}|(password|ABF_PAT|token|key)=[^<[:space:]]|sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{8,}|BEGIN [A-Z ]*PRIVATE KEY'
newlines=$(printf '%s\n' "$unit"; grep -E 'ABF_STUDIO_URL' "$ENVEX")
if printf '%s\n' "$newlines" | grep -nE "$pat" | grep -v 'Bearer <' >/dev/null; then bad "TC-041 a token, password or key shape in the unit or the env line"; else ok "TC-041 no token, password or key shape"; fi
if printf '%s\n' "$unit" | grep -nE -- '--auth-(pam|password|login|minimum)|/home/[A-Za-z]' >/dev/null; then bad "TC-041 an auth password option or a home path"; else ok "TC-041 no auth option but auth-none, no personal path"; fi

# ---------- TC-043: the documents say what the program does ----------
if printf '%s\n' "$plat" | grep -E 'ABF_STUDIO_URL' | grep -q 'frame-src'; then ok "TC-043 PLATFORM.md names the setting together with the frame-src of the downstream page"; else bad "TC-043 PLATFORM.md setting and frame-src"; fi
if has "$plat" 'so all carry the same headers'; then bad "TC-043 PLATFORM.md still says every page has the same headers"; else ok "TC-043 PLATFORM.md no longer says every page has the same headers"; fi
if grep -q 'never a frame' platform/abf_platform/web_downstream.py; then bad "TC-043 web_downstream.py still says never a frame"; else ok "TC-043 web_downstream.py header reworded"; fi
ts=$(printf '%s\n' "$tst" | awk '/^##+ /{on=($0 ~ /studio-embed/)} on')
miss=""; for w in 'TC-036' 'TC-037' 'TC-038' 'TC-039' 'TC-040' 'Chrome' 'Edge' 'Firefox' 'Plots' 'Console' 'new tab' 'abf-rstudio' 'ledger.md'; do has "$ts" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-043 TESTING.md studio-embed section has the manual steps"; else bad "TC-043 TESTING.md section" "missing:$miss"; fi

echo
if [ "$fails" -eq 0 ]; then echo "studio_embed_deploy_test: all ok"; exit 0; else echo "studio_embed_deploy_test: $fails FAILED"; exit 1; fi
