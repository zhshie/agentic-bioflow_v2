#!/bin/bash
# Sibling of tests/command_layer_is_site_neutral.sh, for the record adapter
# instead of the site adapter (docs/RECORD_ADAPTER.md).
#
# The command layer asks only "where does this run's record go" - it may not
# name a record system by name, the same way it may not name a scheduler. A
# specific ELN baked into commands/*.md or skills/operational/SKILL.md is a
# command that only works for a lab that picked that one, and this plugin
# does not know, at the time these files are read, which one (if any) a given
# deployment picked (docs/RECORD_ADAPTER.md - only `none` is implemented).
#
# Root is parameterised via CMD_LAYER_ROOT so this file itself can be proven
# to catch a real regression without touching the real command files, which
# other agents own: point CMD_LAYER_ROOT at a temp copy with a name inserted,
# see it fail, remove the copy. tests/run_all.sh does not set it, so a normal
# run always checks the real repo.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CMD_LAYER_ROOT:-$(cd "$HERE/.." && pwd)}"

# Case-insensitive, word-bounded (PRINCIPLES.md, invariant 9 territory too:
# naming one specific tool here is the same regression this repo already
# guards against in tests/no_per_pipeline_config.sh, one layer over).
NAMES='eLabFTW|elabftw|RSpace|Benchling|LabArchives|SciNote|Labguru|Scispot|openBIS|Kadi4Mat|Chemotion|SampleDB'

TARGETS=()
[ -d "$ROOT/commands" ] && while IFS= read -r f; do TARGETS+=("$f"); done \
    < <(find "$ROOT/commands" -maxdepth 1 -name '*.md' 2>/dev/null | sort)
[ -f "$ROOT/skills/operational/SKILL.md" ] && TARGETS+=("$ROOT/skills/operational/SKILL.md")

if [ "${#TARGETS[@]}" -eq 0 ]; then
    echo "FAIL: no command files found under $ROOT - nothing was checked."
    exit 1
fi

hits=$(grep -nInE "\\b($NAMES)\\b" "${TARGETS[@]}" 2>/dev/null | sed "s|^$ROOT/||") || true

if [ -n "$hits" ]; then
    printf '%s\n' "$hits"
    echo
    echo "FAIL: the command layer names a record system. Move it behind"
    echo "scripts/record_adapter.sh - see docs/RECORD_ADAPTER.md."
    exit 1
fi
echo "OK: commands/ and skills/operational/SKILL.md name no record system"
