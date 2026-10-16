#!/bin/bash
# Proposal R10 (docs/LAB_AGENTS.md section A3, row R10): the skill text has to
# be portable, saying plainly what degrades when a runtime reads it with no
# plugin hooks loaded - tying back to the H1/H2/H3 tiers docs/LAB_AGENTS.md
# section 3 defines. This file checks the shape of that, not the prose: the
# frontmatter still parses as the minimal thing it has always been, the
# section exists exactly once, it names the tier and the document that
# defines it, and every `${CLAUDE_PLUGIN_ROOT}` mention still carries its
# "otherwise" alternative in the same paragraph - the SKILL.md convention this
# section has to keep, not invent (skills/operational/SKILL.md:16-17 already
# does this once).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SKILL="$ROOT/skills/operational/SKILL.md"
HEADING='## On a host without these hooks'
fails=0

t()  { printf '%-70s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2'"; fails=$((fails+1)); }; }
eq() { printf '%-70s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

shape_checks() {  # shape_checks <path to a SKILL.md> <label>
# --- frontmatter: a valid YAML block between the first two '---' lines,
# carrying at least `name` and `description`. Not a real YAML parser - this
# repo's own rule for its settings file (scripts/settings.sh) applies here
# too: `key: value`, one per line, is all frontmatter this simple is allowed
# to be, and a real parser is not a dependency this test may add.
FRONT="$HERE/.skill_frontmatter.$$"
awk '
    NR==1 { if ($0 != "---") { print "BADSTART"; exit 1 } next }
    /^---$/ { exit 0 }
    { print }
' "$1" > "$FRONT" 2>/dev/null
front_ok=1
[ -s "$FRONT" ] || front_ok=0

printf '%-70s ' "$2: frontmatter block is present and non-empty"
[ "$front_ok" = 1 ] && echo ok || { echo "FAIL"; fails=$((fails+1)); }

bad_lines=0
while IFS= read -r line; do
    [ -n "$line" ] || continue
    case "$line" in
        [a-zA-Z_]*:*) ;;                  # key: value
        *) bad_lines=$((bad_lines+1)) ;;
    esac
done < "$FRONT"
printf '%-70s ' "$2: every frontmatter line is a plain 'key: value'"
[ "$bad_lines" = 0 ] && echo ok || { echo "FAIL: $bad_lines line(s) do not parse as key: value"; fails=$((fails+1)); }

name_val=$(sed -n 's/^name:[[:space:]]*//p' "$FRONT" | head -1)
desc_val=$(sed -n 's/^description:[[:space:]]*//p' "$FRONT" | head -1)
rm -f "$FRONT"

printf '%-70s ' "$2: frontmatter has a 'name' key"
[ -n "$name_val" ] && echo ok || { echo "FAIL: no name: line"; fails=$((fails+1)); }
printf '%-70s ' "$2: name matches ^[a-z0-9-]+\$"
[[ "$name_val" =~ ^[a-z0-9-]+$ ]] && echo ok || { echo "FAIL: '$name_val'"; fails=$((fails+1)); }

printf '%-70s ' "$2: frontmatter has a 'description' key"
[ -n "$desc_val" ] && echo ok || { echo "FAIL: no description: line"; fails=$((fails+1)); }
printf '%-70s ' "$2: description is non-empty and <= 1024 chars"
[ -n "$desc_val" ] && [ "${#desc_val}" -le 1024 ] && echo ok \
    || { echo "FAIL: length ${#desc_val}"; fails=$((fails+1)); }

# --- every ${CLAUDE_PLUGIN_ROOT} mention carries its "otherwise" in the same
# paragraph. Same paragraph-grouping trick tests/off_design_single_path.sh
# uses (awk RS='', portable - no GNU-only paragraph flag).
bad=$(awk -v RS='' '
    /\$\{CLAUDE_PLUGIN_ROOT\}/ {
        if ($0 !~ /otherwise/) {
            print "----- paragraph with no otherwise -----"
            print $0
        }
    }
' "$1")
printf '%-70s ' "$2: every \${CLAUDE_PLUGIN_ROOT} mention has 'otherwise' in the same paragraph"
if [ -z "$bad" ]; then
    echo ok
else
    echo "FAIL"
    printf '%s\n' "$bad"
    fails=$((fails+1))
fi

# --- positive control: at least one ${CLAUDE_PLUGIN_ROOT} mention exists, so
# the check above is not vacuously passing on an empty file.
printf '%-70s ' "$2: SKILL.md mentions \${CLAUDE_PLUGIN_ROOT} at least once"
grep -qF '${CLAUDE_PLUGIN_ROOT}' "$1" && echo ok || { echo "FAIL"; fails=$((fails+1)); }

}

printf '%-70s ' "SKILL.md exists"
[ -r "$SKILL" ] && echo ok || { echo "FAIL: $SKILL not found"; echo; echo "1 failed"; exit 1; }

# TC-027: the shape checks run over all six skills (the five flow skills moved
# from commands/ in 009a, plus operational).
. "$HERE/lib/flow_skills.sh"
read_n=0
for n in $FLOW_SKILLS; do
    f="$(flow_skill_file "$n")"
    [ -r "$f" ] && read_n=$((read_n+1))
    [ -r "$f" ] && shape_checks "$f" "$n" || { printf '%-70s FAIL: %s not found
' "$n: SKILL.md exists" "$f"; fails=$((fails+1)); }
done
printf '%-70s ' "all five flow skills were read"
[ "$read_n" = 5 ] && echo ok || { echo "FAIL: read $read_n of 5"; fails=$((fails+1)); }
shape_checks "$SKILL" operational

# TC-028/TC-040: from here on, operational only (heading, H3, LAB_AGENTS).
# --- the section: exactly one occurrence, exact heading text -----------------
count=$(grep -Fxc "$HEADING" "$SKILL")
eq "the heading appears exactly once, verbatim" "$count" "1"

# --- the section's own body mentions H3 and docs/LAB_AGENTS.md ---------------
# Sliced from the heading to the next '## ' heading (or EOF) so this checks
# the section's own text, not some other part of the file that happens to
# mention the same words.
SECTION="$HERE/.skill_section.$$"
awk -v h="$HEADING" '
    $0 == h { grabbing=1; print; next }
    grabbing && /^## / { exit }
    grabbing { print }
' "$SKILL" > "$SECTION"

printf '%-70s ' "the section is non-empty"
[ -s "$SECTION" ] && echo ok || { echo "FAIL"; fails=$((fails+1)); }
t "the section names tier H3"                 "H3"                  "$(cat "$SECTION")"
t "the section points at docs/LAB_AGENTS.md"  "docs/LAB_AGENTS.md"  "$(cat "$SECTION")"
rm -f "$SECTION"


echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
