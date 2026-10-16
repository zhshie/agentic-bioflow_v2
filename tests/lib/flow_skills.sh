#!/bin/bash
# Shared path helper for the five flow skills (setup launch runs downstream
# finish). They are Agent Skills: skills/<name>/SKILL.md. Tests that walk or
# name those files source this so the layout is spelled in one place.
# Needs $ROOT set by the caller (the repo or deployed root).
FLOW_SKILLS="setup launch runs downstream finish"

# flow_skill_file <name> -> path of that skill's SKILL.md
flow_skill_file() { printf '%s\n' "$ROOT/skills/$1/SKILL.md"; }

# flow_skill_files -> the five paths, one per line, in FLOW_SKILLS order
flow_skill_files() {
    local n
    for n in $FLOW_SKILLS; do flow_skill_file "$n"; done
}
