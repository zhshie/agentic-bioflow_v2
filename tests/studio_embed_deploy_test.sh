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
if has "$exec_line" '--www-frame-origin="$${ABF_PUBLIC_URL}"' && ! has "$exec_line" '--www-frame-origin=${ABF_PUBLIC_URL}'; then ok "S4 the frame origin is read by the shell and quoted, not pasted in by systemd"; else bad "S4 quoted frame origin"; fi
if has "$exec_line" '--www-enable-origin-check=1'; then ok "S1 the unit sets --www-enable-origin-check=1"; else bad "S1 --www-enable-origin-check=1"; fi
if has "$exec_line" 'abf-rstudio will not start: ABF_PUBLIC_URL' && has "$exec_line" 'https://*' && has "$exec_line" 'exit 2'; then ok "S4 a missing or non-https ABF_PUBLIC_URL stops the unit with exit 2"; else bad "S4 ABF_PUBLIC_URL guard"; fi
if printf '%s\n' "$unit" | grep -E 'platform.s owner|owner of the platform' >/dev/null && printf '%s\n' "$unit" | grep -E 'Windows' >/dev/null; then ok "S2 the unit header says what access to this port means"; else bad "S2 unit header consequence"; fi
check "TC-029 EnvironmentFile=%h/.config/abf-platform/env" has "$code" 'EnvironmentFile=%h/.config/abf-platform/env'
check "TC-029 WantedBy=default.target" has "$code" 'WantedBy=default.target'
check "TC-029 Restart=on-failure" has "$code" 'Restart=on-failure'
# the option names that exist in the package's rserver binary (read from its strings); a misspelling fails here
for o in $(printf '%s\n' "$exec_line" | grep -oE -- '--[a-z][a-z-]+' | sort -u); do
  case "$o" in --www-address|--www-port|--www-frame-origin|--auth-none|--server-user|--server-daemonize|--server-data-dir|--server-pid-file|--secure-cookie-key-file|--database-config-file|--www-same-site|--auth-cookies-force-secure|--www-enable-origin-check) ;;
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
case "$port" in 8787|8788|8789) badport=1;; *) badport=0;; esac
if [ "$badport" -eq 0 ] && [ "$port" = 8790 ]; then ok "TC-032 the example port is 8790, not 8787-8789"; else bad "TC-032 example port" "$port"; fi
ops=$(tr -d '\r' < "$OPS"); tst=$(tr -d '\r' < "$TST"); plat=$(tr -d '\r' < "$PLAT")
rs=$(printf '%s\n' "$ops" | awk '/RStudio in the downstream page/{on=1} on' | head -n 60)
if has "$rs" "http://127.0.0.1:$port"; then ok "TC-032 OPERATIONS names the same address as the example"; else bad "TC-032 OPERATIONS address"; fi
if bash tests/hosted_deploy_test.sh 2>&1 | grep -E 'TC-01[56]' | grep FAIL >/dev/null; then bad "TC-032 hosted_deploy_test TC-015/016 on env.example"; else ok "TC-032 env.example still passes hosted_deploy_test TC-015/016"; fi


# ---------- desktop trial (2026-11-13): the two cookie options, a private cookie key, USER set ----------
if has "$exec_line" '--www-same-site=none' && has "$exec_line" '--auth-cookies-force-secure=1'; then ok "TC-029 the unit sets --www-same-site=none and --auth-cookies-force-secure=1 (a cookie the framed page can keep)"; else bad "TC-029 same-site and force-secure options"; fi
if has "$exec_line" 'chmod 600' && has "$exec_line" 'cookie-key'; then ok "TC-029 the cookie key file is made mode 600"; else bad "TC-029 chmod 600 of the cookie key"; fi
if has "$exec_line" 'export USER=%u'; then ok "TC-029 USER is set for rserver (export USER=%u)"; else bad "TC-029 export USER=%u"; fi
if printf '%s\n' "$unit" | grep -iE 'not (been )?(verified|checked)|checked on the computer' >/dev/null; then bad "TC-029 the unit header still says the options are not verified"; else ok "TC-029 the unit header states what was verified"; fi
if has "$ops" 'allow' && hasre "$ops" 'local network' && has "$tst" 'local network' && has "$plat" 'local network'; then ok "TC-043 OPERATIONS, TESTING and PLATFORM tell the browser asks to allow local network access"; else bad "TC-043 local network permission in the docs"; fi
# ---------- adversarial review round (S2 S3): what the port means, and that the setting is for one user ----------
rs2=$(printf '%s\n' "$ops" | awk '/RStudio in the downstream page/{on=1} on' | head -n 60)
miss=""; for w in "platform's owner" 'signing key' 'agent token' 'Windows' 'compute allowance' 'only for a deployment with one user' 'every user' 'runs no script'; do has "$rs2" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "S2 S3 OPERATIONS step 12 names the consequences and the one-user rule"; else bad "S2 S3 OPERATIONS" "missing:$miss"; fi
miss=""; for w in "platform's owner" 'signing key' 'agent token' 'Windows' 'only for a deployment with one user' 'every user' 'runs no script'; do has "$plat" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "S2 S3 PLATFORM.md names the consequences and the one-user rule"; else bad "S2 S3 PLATFORM.md" "missing:$miss"; fi
if grep -E '^#.*(one user|single)' "$ENVEX" >/dev/null && grep -E '^#.*every user' "$ENVEX" >/dev/null; then ok "S3 env.example says the setting is for a deployment with one user"; else bad "S3 env.example one-user sentence"; fi

# ---------- TC-033 TC-034: what is under deploy/, and no RStudio file in the repository ----------
# (That the branch added exactly one file under deploy/ and changed none of the files the plan forbids was a comparison with its base; it was
#  made once at review and is recorded in specs/studio-embed/ledger.md, "Checks against the base". After the merge there is no base to compare.)
if [ -f "$HERE/../deploy/systemd/abf-rstudio.service.in" ]; then ok "TC-033 the unit template is under deploy/systemd/"; else bad "TC-033 the unit template is missing"; fi
if git -C "$HERE/.." rev-parse --git-dir >/dev/null 2>&1; then
  rfiles=$(git -C "$HERE/.." ls-files | grep -iE '\.deb$|rserver\.conf|rstudio.*\.(tar|zip|rpm)$|/rserver$' || true)
else
  rfiles=$(cd "$HERE/.." && find . -path ./.git -prune -o -type f -print | grep -iE '\.deb$|rserver\.conf|rstudio.*\.(tar|zip|rpm)$|/rserver$' || true)
fi
if [ -z "$rfiles" ]; then ok "TC-034 no RStudio file in the repository"; else bad "TC-034 RStudio files" "$rfiles"; fi

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
if printf '%s\n' "$plat" | grep -E 'ABF_STUDIO_URL' | grep 'frame-src' >/dev/null; then ok "TC-043 PLATFORM.md names the setting together with the frame-src of the downstream page"; else bad "TC-043 PLATFORM.md setting and frame-src"; fi
if has "$plat" 'so all carry the same headers'; then bad "TC-043 PLATFORM.md still says every page has the same headers"; else ok "TC-043 PLATFORM.md no longer says every page has the same headers"; fi
if grep -q 'never a frame' platform/abf_platform/web_downstream.py; then bad "TC-043 web_downstream.py still says never a frame"; else ok "TC-043 web_downstream.py header reworded"; fi
ts=$(printf '%s\n' "$tst" | awk '/^##+ /{on=($0 ~ /studio-embed/)} on')
miss=""; for w in 'TC-036' 'TC-037' 'TC-038' 'TC-039' 'TC-040' 'Chrome' 'Edge' 'Firefox' 'Plots' 'Console' 'new tab' 'abf-rstudio' 'ledger.md'; do has "$ts" "$w" || miss="$miss [$w]"; done
if [ -z "$miss" ]; then ok "TC-043 TESTING.md studio-embed section has the manual steps"; else bad "TC-043 TESTING.md section" "missing:$miss"; fi

echo
if [ "$fails" -eq 0 ]; then echo "studio_embed_deploy_test: all ok"; exit 0; else echo "studio_embed_deploy_test: $fails FAILED"; exit 1; fi
