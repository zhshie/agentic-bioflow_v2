#!/bin/bash
# harness-kits: copy-to-use MCP connection kits for Claude Code and Codex.
#   TC-001 claude-code-kit/mcp.json; TC-002 codex-kit/config.toml; TC-003 no literal token / real host;
#   TC-004 no root .mcp.json/plugin.json/mcp.json; TC-005 INSTALL s4; TC-006 INSTALL names kit, s6 trimmed;
#   TC-007 negative self-check; TC-008 file names; TC-010 claude mcp add line kept;
#   TC-011 s2 alternative; TC-012 s2 401; TC-013 s4 steps; TC-015 s6 one bullet.
# Overrides: KIT_DIR (dir holding claude-code-kit/ and codex-kit/), INSTALL_DOC, ROOT_DIR.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"

run_checks() {
    local KIT="$1" DOC="$2" ROOT="$3" fails=0
    local CC="$KIT/claude-code-kit/mcp.json" CX="$KIT/codex-kit/config.toml"
    ok()   { printf '%-70s ok\n' "$1"; }
    fail() { printf '%-70s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

    # TC-001
    if jq -e . "$CC" >/dev/null 2>&1; then
        s='.mcpServers["abf-platform"]'
        [ "$(jq -r "$s.type" "$CC")" = "http" ] && ok "TC-001 type http" || fail "TC-001 type" "not http"
        u=$(jq -r "$s.url" "$CC")
        [[ "$u" == *'${ABF_PLATFORM_URL}'* && "$u" == */mcp ]] && ok "TC-001 url" || fail "TC-001 url" "got '$u'"
        [ "$(jq -r "$s.headers.Authorization" "$CC")" = 'Bearer ${ABF_PAT}' ] && ok "TC-001 Authorization header" || fail "TC-001 header" "not Bearer \${ABF_PAT}"
    else fail "TC-001 mcp.json parses" "missing or invalid JSON: $CC"; fi

    # TC-002
    if [ -r "$CX" ]; then
        grep -qE '^\[mcp_servers\.abf-platform\]' "$CX" && ok "TC-002 section" || fail "TC-002 section" "no [mcp_servers.abf-platform]"
        grep -qE '^url *= *"[^"]*/mcp"' "$CX" && ok "TC-002 url ends /mcp" || fail "TC-002 url" "no url ending /mcp"
        grep -qE '^bearer_token_env_var *= *"ABF_PAT"' "$CX" && ok "TC-002 env var" || fail "TC-002 env var" "no bearer_token_env_var = \"ABF_PAT\""
        grep -qE '^ *bearer_token *=' "$CX" && fail "TC-002 no bearer_token" "literal bearer_token line" || ok "TC-002 no bearer_token ="
        grep -qE '^ *(http_headers|\[mcp_servers\.[^]]*\.http_headers)' "$CX" && fail "TC-002 no http_headers" "http_headers present" || ok "TC-002 no http_headers"
    else fail "TC-002 config.toml" "missing: $CX"; fi

    # TC-003
    for f in "$CC" "$CX"; do
        [ -r "$f" ] || continue
        if grep -qE 'abf_pat_[A-Za-z0-9]{8,}' "$f"; then fail "TC-003 no token in $(basename "$f")" "PAT-looking value"; else ok "TC-003 no token in $(basename "$f")"; fi
        bad=0
        while IFS= read -r h; do
            [ -z "$h" ] && continue
            case "$h" in '${ABF_PLATFORM_URL}'|*.example|*.example/*) ;; *) bad=1; fail "TC-003 host in $(basename "$f")" "real host '$h'";; esac
        done < <(grep -oE 'https?://[^"/ ]+|"\$\{ABF_PLATFORM_URL\}' "$f" | sed -E 's#^https?://##; s#^"##')
        [ "$bad" -eq 0 ] && ok "TC-003 hosts placeholder in $(basename "$f")"
    done

    # TC-004
    for n in .mcp.json plugin.json mcp.json; do
        [ -e "$ROOT/$n" ] && fail "TC-004 no root $n" "$n exists at repo root" || ok "TC-004 no root $n"
    done

    # TC-008
    [ -e "$KIT/claude-code-kit/.mcp.json" ] && fail "TC-008 no dotted kit file" ".mcp.json in claude-code-kit" || ok "TC-008 no dotted kit file"

    # INSTALL.md
    if [ ! -r "$DOC" ]; then fail "INSTALL.md" "missing $DOC"; return $fails; fi
    s2=$(awk '/^## 2\./{f=1;next} /^## 3\./{f=0} f' "$DOC")
    s4=$(awk '/^## 4\./{f=1;next} /^## 5\./{f=0} f' "$DOC")
    s6=$(awk '/^## 6\./{f=1;next} f' "$DOC")
    # TC-005
    grep -qF 'Not built yet' <<<"$s4" && fail "TC-005 s4 not 'Not built yet'" "still says it" || ok "TC-005 s4 not 'Not built yet'"
    grep -qF 'extensions/codex-kit/config.toml' <<<"$s4" && ok "TC-005 s4 names codex kit" || fail "TC-005 s4" "no extensions/codex-kit/config.toml"
    grep -qF 'bearer_token_env_var' <<<"$s4" && ok "TC-005 s4 names bearer_token_env_var" || fail "TC-005 s4" "no bearer_token_env_var"
    # TC-006
    grep -qF 'extensions/claude-code-kit/mcp.json' "$DOC" && ok "TC-006 names claude-code kit" || fail "TC-006" "no extensions/claude-code-kit/mcp.json"
    grep -qiE 'codex kit' <<<"$s6" && fail "TC-006 s6 no Codex kit" "still listed" || ok "TC-006 s6 no Codex kit"
    grep -qiE 'connector kit' <<<"$s6" && fail "TC-006 s6 no Desktop kit" "still listed" || ok "TC-006 s6 no Desktop kit"
    # TC-010
    grep -qxF 'claude mcp add --transport http abf-platform <platform-URL>/mcp --header "Authorization: Bearer <PAT>"' "$DOC" && ok "TC-010 claude mcp add line" || fail "TC-010" "line missing"
    # TC-011
    for w in .mcp.json ABF_PLATFORM_URL ABF_PAT; do
        grep -qF "$w" <<<"$s2" && ok "TC-011 s2 names $w" || fail "TC-011 s2" "no $w"
    done
    # TC-012
    grep -qF 401 <<<"$s2" && ok "TC-012 s2 mentions 401" || fail "TC-012" "no 401 in s2"
    # TC-013
    grep -qF '~/.codex/config.toml' <<<"$s4" && ok "TC-013 s4 names ~/.codex/config.toml" || fail "TC-013" "no ~/.codex/config.toml"
    grep -qF 'export ABF_PAT=' <<<"$s4" && ok "TC-013 s4 export ABF_PAT=" || fail "TC-013" "no export ABF_PAT="
    # TC-015
    nb=$(grep -cE '^- ' <<<"$s6")
    [ "$nb" -eq 1 ] && grep -qF .mcp.json <<<"$s6" && ok "TC-015 s6 one bullet about .mcp.json" || fail "TC-015" "s6 has $nb bullets or no .mcp.json"
    # TC-023 (doc)
    grep -qE 'abf_pat_[A-Za-z0-9]{8,}' "$DOC" && fail "TC-023 no token in doc" "PAT-looking value" || ok "TC-023 no token in doc"
    return $fails
}

KIT="${KIT_DIR:-$REPO/extensions}"
DOC="${INSTALL_DOC:-$REPO/docs/INSTALL.md}"
ROOT="${ROOT_DIR:-$REPO}"
run_checks "$KIT" "$DOC" "$ROOT"; rc=$?
total=$rc

# TC-007 negative self-check: a doctored copy must fail.
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/kit" "$T/root"
cp -r "$KIT/claude-code-kit" "$KIT/codex-kit" "$T/kit/" 2>/dev/null
for f in "$T/kit/claude-code-kit/mcp.json" "$T/kit/codex-kit/config.toml"; do
    [ -f "$f" ] && echo '# abf_pat_abcdefgh12' >> "$f"
done
: > "$T/root/.mcp.json"
out=$(run_checks "$T/kit" "$DOC" "$T/root" 2>&1); drc=$?
if [ "$drc" -gt 0 ] && grep -q 'FAIL: .*PAT-looking' <<<"$out" && grep -q 'TC-004 no root .mcp.json.*FAIL' <<<"$out"; then
    printf '%-70s ok\n' "TC-007 doctored copy is rejected"
else
    printf '%-70s FAIL: %s\n' "TC-007 doctored copy" "checks did not catch the doctored copy"; total=$((total+1))
fi

[ "$total" -eq 0 ] && { echo "all ok"; exit 0; }
echo "FAILED: $total"; exit 1
