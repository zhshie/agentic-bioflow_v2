#!/bin/bash
# 009a: the five flow files live as Agent Skills (skills/<name>/SKILL.md) and
# nothing still points at commands/.
#   TC-001 (a) five SKILL.md exist, non-empty     TC-002 (b) name == dir name
#   TC-003 (c) description present                TC-004 (d) commands/ is gone
#   TC-016 (e) operational names the five by new path
#   TC-008/018/019/020/021/029/034 (f) stale-path guard
#   TC-023 helper tests/lib/flow_skills.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fails=0
ok()   { printf '%-70s ok\n' "$1"; }
bad()  { printf '%-70s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

# --- TC-023 helper
# shellcheck source=lib/flow_skills.sh
. "$HERE/lib/flow_skills.sh"
t="helper: FLOW_SKILLS lists the five in order"
[ "$FLOW_SKILLS" = "setup launch runs downstream finish" ] && ok "$t" || bad "$t" "got '$FLOW_SKILLS'"
t="helper: flow_skill_file launch"
[ "$(flow_skill_file launch)" = "$ROOT/skills/launch/SKILL.md" ] && ok "$t" || bad "$t" "$(flow_skill_file launch)"
t="helper: flow_skill_files returns five paths in order"
exp=""; for n in setup launch runs downstream finish; do exp="$exp$ROOT/skills/$n/SKILL.md"$'\n'; done
[ "$(flow_skill_files)" = "${exp%$'\n'}" ] && ok "$t" || bad "$t" "unexpected list"

# --- (a)(b)(c)
for n in $FLOW_SKILLS; do
    f="$(flow_skill_file "$n")"
    t="$n: skills/$n/SKILL.md exists and is non-empty"
    if [ -s "$f" ]; then ok "$t"; else bad "$t" "missing or empty"; continue; fi
    fm="$(awk 'NR==1&&$0!="---"{exit} NR>1&&$0=="---"{exit} NR>1{print}' "$f")"
    t="$n: frontmatter name equals directory name"
    [ "$(printf '%s\n' "$fm" | sed -n 's/^name:[[:space:]]*//p' | head -1)" = "$n" ] && ok "$t" || bad "$t" "name: mismatch"
    t="$n: frontmatter has description"
    printf '%s\n' "$fm" | grep -q '^description:[[:space:]]*[^[:space:]]' && ok "$t" || bad "$t" "no description"
done

# --- (d)
t="commands/ does not exist (two entries would register)"
[ ! -e "$ROOT/commands" ] && ok "$t" || bad "$t" "commands/ still there"

# --- (e)
OP="$ROOT/skills/operational/SKILL.md"
for n in $FLOW_SKILLS; do
    t="operational names skills/$n/SKILL.md"
    grep -qF "skills/$n/SKILL.md" "$OP" 2>/dev/null && ok "$t" || bad "$t" "not named"
done

# --- (f) stale-path guard.
# Scans tests/ docs/ scripts/ skills/ CLAUDE.md README.md. hooks/ and specs/
# are not scanned (hooks protected; specs are history).
# Exemptions (one reason each):
#   docs/PITFALLS.md                      history
#   docs/adr/*                            history
#   tests/command_layer_is_site_neutral.sh synthetic fixture inputs
#   tests/no_second_run_state_test.sh     commands/a.md fixtures
#   tests/confirm_launch_test.sh          gate fixture (a shell command text)
#   tests/flow_skills_layout_test.sh      this file spells the pattern
PAT='commands/(setup|launch|runs|downstream|finish)\.md'
PAT_ROOT='\$ROOT/commands([^[:alnum:]_]|$)'
exempt() {
    case "$1" in
        docs/PITFALLS.md|docs/adr/*|tests/command_layer_is_site_neutral.sh|\
tests/no_second_run_state_test.sh|tests/confirm_launch_test.sh|tests/flow_skills_layout_test.sh) return 0;;
    esac
    return 1
}
stale=""
while IFS= read -r rel; do
    exempt "$rel" && continue
    [ -f "$ROOT/$rel" ] || continue
    if grep -qE "$PAT" "$ROOT/$rel"; then stale="$stale $rel"; continue; fi
    case "$rel" in tests/*) grep -qE "$PAT_ROOT" "$ROOT/$rel" && stale="$stale $rel";; esac
done < <(cd "$ROOT" && { find tests docs scripts skills -type f 2>/dev/null; ls CLAUDE.md README.md 2>/dev/null; } | sort)
t="no stale commands/<name>.md pointer outside the exemptions"
[ -z "$stale" ] && ok "$t" || bad "$t" "in:$stale"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
