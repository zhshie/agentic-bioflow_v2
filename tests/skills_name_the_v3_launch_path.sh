#!/bin/bash
# plugin-launch-v2-only (M1-09): the launch and setup skills, ce_apply.sh and
# MIGRATION.md must say that the `tw` (Seqera) flow is v2 only and that v3 starts
# analyses with `abf-platform launch` or the MCP `launch` tool.
# Covers TC-001..TC-023 of specs/plugin-launch-v2-only/test-case.md.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
fail() { echo "FAIL: $*"; fails=$((fails+1)); }

for n in launch setup; do
    f="$ROOT/skills/$n/SKILL.md"
    rel="skills/$n/SKILL.md"
    if [ ! -r "$f" ]; then fail "$rel unreadable"; continue; fi
    hdr=$(grep -n '^## Before anything else' "$f" | head -1 | cut -d: -f1)
    [ -n "$hdr" ] || { fail "$rel: no '## Before anything else' heading"; continue; }
    # fork section: text after the frontmatter, before the first '## ' heading
    sec=$(awk -v h="$hdr" 'NR<h' "$f" | awk 'BEGIN{c=0} /^---$/{c++; next} c>=2')
    printf '%s' "$sec" | grep -F 'abf-platform launch' >/dev/null || fail "$rel: fork section lacks 'abf-platform launch'"
    printf '%s' "$sec" | grep -F 'MCP' >/dev/null || fail "$rel: fork section lacks MCP"
    printf '%s' "$sec" | grep -F 'launch' >/dev/null || fail "$rel: fork section lacks MCP launch"
    printf '%s' "$sec" | grep -F 'v2' >/dev/null || fail "$rel: fork section lacks v2"
    printf '%s' "$sec" | grep -F 'tw' >/dev/null || fail "$rel: fork section lacks tw"
    printf '%s' "$sec" | grep -F 'docs/PLATFORM.md' >/dev/null || fail "$rel: fork section lacks docs/PLATFORM.md"
    a=$(printf '%s\n' "$sec" | grep -nF 'abf-platform launch' | head -1 | cut -d: -f1)
    t=$(printf '%s\n' "$sec" | grep -n '`tw`' | head -1 | cut -d: -f1)
    if [ -n "$a" ] && [ -n "$t" ] && [ "$a" -gt "$t" ]; then fail "$rel: tw appears before abf-platform launch"; fi
    if printf '%s' "$sec" | grep -oE '20[0-9]{2}' | grep -vx 2027 >/dev/null; then fail "$rel: fork section names a year other than 2027"; fi
done
[ -f "$ROOT/docs/PLATFORM.md" ] || fail "docs/PLATFORM.md missing"

# ce_apply.sh: leading comment block
f="$ROOT/scripts/ce_apply.sh"
if [ ! -r "$f" ]; then fail "scripts/ce_apply.sh unreadable"; else
    [ "$(head -1 "$f")" = '#!/bin/bash' ] || fail "ce_apply.sh line 1 changed"
    top=$(awk 'NR>1 && /^#/{print; next} NR>1{exit}' "$f")
    if ! { printf '%s\n' "$top" | grep -F 'abf-platform launch' >/dev/null && printf '%s\n' "$top" | grep -F 'v2' >/dev/null; }; then
        fail "ce_apply.sh top comment lacks v2 / abf-platform launch"
    fi
    bash -n "$f" || fail "ce_apply.sh syntax error"
fi

# MIGRATION.md: the new section
f="$ROOT/docs/MIGRATION.md"
if [ ! -r "$f" ]; then fail "docs/MIGRATION.md unreadable"; else
    sec=$(awk '/^## /{p=($0 ~ /tw/ && $0 ~ /v3/ && $0 ~ /v2/)} p' "$f")
    if [ -z "$sec" ]; then fail "MIGRATION.md: no section heading naming the v2 tw flow and v3"; else
        printf '%s' "$sec" | grep -F 'abf-platform launch' >/dev/null || fail "MIGRATION.md section lacks 'abf-platform launch'"
        printf '%s' "$sec" | grep -F 'MCP' >/dev/null || fail "MIGRATION.md section lacks MCP launch"
        rows=$(printf '%s\n' "$sec" | grep -c '^|')
        [ "$rows" -ge 3 ] || fail "MIGRATION.md section has no table with a data row"
        printf '%s\n' "$sec" | grep '^|' | grep -F 'tw launch' | grep -F 'abf-platform launch' >/dev/null \
            || fail "MIGRATION.md table lacks the tw launch -> abf-platform launch row"
        if printf '%s\n' "$sec" | grep '^|' | tail -n +3 | awk -F'|' '{print $(NF-1)}' | grep -E '`tw |token|account' >/dev/null; then
            fail "MIGRATION.md v3 column mentions tw/token/account"
        fi
        if printf '%s' "$sec" | grep -oE '20[0-9]{2}' | grep -vx 2027 >/dev/null; then fail "MIGRATION.md section names a year other than 2027"; fi
    fi
fi

[ "$fails" = 0 ] && echo "OK: v3 launch path is named in launch, setup, ce_apply.sh and MIGRATION.md"
[ "$fails" = 0 ]
