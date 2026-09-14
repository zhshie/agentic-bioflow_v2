#!/bin/bash
# D4: the "where you are" card. One screen, four sections, ending in exactly
# one concrete next step - U3 in the plan this implements.
#
# Not `tw info`: it reports Platform-side connectivity only, never this site's
# own setup progress - this formats preflight.sh/settings.sh/inspect_sides.sh
# instead of reimplementing any of their checks (below).
#
# It calls scripts/preflight.sh, scripts/settings.sh --summary and
# scripts/inspect_sides.sh (D1) for the facts and formats them; it does not
# re-implement any check any of those three already does. Keep this file
# about formatting and the next-step decision only.
#
#   status.sh
#
# Token state is never printed, only present/absent - inspect_sides.sh and
# settings.sh --summary already keep that rule; this just carries it through.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

# Whether TERM_PROGRAM/VSCODE_GIT_ASKPASS_MAIN corroborate VS Code - the one
# check both claude_surface() (below, human-readable) and claude_interface_kind()
# (the raw cli|vscode|desktop|web|unknown category scripts/detect_conditions.sh
# reads via `status.sh --interface`) rest on. Factored out once so the two
# read this machine the same way and cannot drift apart.
_in_vscode() {
    [ "${TERM_PROGRAM:-}" = vscode ] || [ -n "${VSCODE_GIT_ASKPASS_MAIN:-}" ]
}

# CLAUDE_CODE_ENTRYPOINT alone answers the wrong question. Measured on this
# machine: the same VS Code session reported `claude-vscode` once and `cli`
# later, because the value describes how this Bash subprocess was started, not
# which surface the person is looking at. So corroborate it with the editor's
# own variables before claiming anything.
claude_surface() {
    case "${CLAUDE_CODE_ENTRYPOINT:-}" in
        claude-vscode) printf 'vscode\n'; return 0 ;;
    esac
    if _in_vscode; then
        printf '%s (inside VS Code)\n' "${CLAUDE_CODE_ENTRYPOINT:-cli}"
        return 0
    fi
    printf '%s\n' "${CLAUDE_CODE_ENTRYPOINT:-unknown}"
}

# The same detection, collapsed to the fixed vocabulary
# scripts/detect_conditions.sh prints: cli|vscode|desktop|web|unknown. Only
# `claude-vscode` (corroborated or not) and `cli` are MEASURED; `claude-desktop`
# and `claude-web` follow the one naming convention actually observed
# (`claude-<surface>`) and are INFERRED, never measured - docs/CONDITIONS.md
# marks this whole dimension as inferred, not measured, for that reason.
claude_interface_kind() {
    if [ "${CLAUDE_CODE_ENTRYPOINT:-}" = claude-vscode ] || _in_vscode; then
        printf 'vscode\n'; return 0
    fi
    case "${CLAUDE_CODE_ENTRYPOINT:-}" in
        cli)                    printf 'cli\n' ;;
        claude-desktop|desktop) printf 'desktop\n' ;;
        claude-web|web)         printf 'web\n' ;;
        *)                      printf 'unknown\n' ;;
    esac
}

# `status.sh --interface`: the raw category alone - no settings lookups beyond
# what is already sourced, no inspect_sides.sh, no preflight.sh, no network.
# This is the fast path scripts/detect_conditions.sh calls, so nothing above
# this line may do anything slower than reading an env var, and nothing below
# it runs when this flag is given.
if [ "${1:-}" = "--interface" ]; then
    claude_interface_kind
    exit 0
fi

REACH="$(setting reach local)"

echo "== Your environment =="
echo "OS: $(plat_kind)   Shell: $(basename "${SHELL:-unknown}")   Reach: $REACH   Claude: $(claude_surface)"
echo

echo "== Both sides =="
SIDES=$(bash "$HERE/inspect_sides.sh" 2>/dev/null)
sv() { sed -n "s/^$1=//p" <<<"$SIDES" | head -1; }
printf 'site   settings=%-7s token=%-7s skeleton=%-7s tw=%-7s java=%-7s jar=%-7s runs=%s\n' \
    "$(sv site.settings)" "$(sv site.token)" "$(sv site.skeleton)" \
    "$(sv site.tw)" "$(sv site.java)" "$(sv site.jar)" "$(sv site.runs)"
printf 'local  settings=%-7s token=%-7s skeleton=%-7s tw=%-7s\n' \
    "$(sv local.settings)" "$(sv local.token)" "$(sv local.skeleton)" "$(sv local.tw)"
echo

echo "== Setup progress =="
PF=$(bash "$HERE/preflight.sh" 2>&1); PF_RC=$?
printf '%s\n' "$PF"
# The two lines from --summary that say where things live and whether the
# token exists - the rest of that report is settings values already visible
# above via inspect_sides.sh, and repeating them here is exactly the
# re-implementation this script is told not to do.
SUMMARY=$(bash "$HERE/settings.sh" --summary 2>&1)
grep -E '^[[:space:]]*(settings file|token)[[:space:]]' <<<"$SUMMARY" | sed 's/^/  /'
echo

echo "== Next step =="
if [ "$SETTINGS_FOUND" != 1 ]; then
    echo "No settings file yet. Run :setup to create one."
elif [ "$PF_RC" != 0 ]; then
    first_fail=$(grep '^FAIL' <<<"$PF" | head -1 | awk '{print $2}')
    echo "Not ready yet - preflight FAILs on '${first_fail:-a check}'. Run :setup to fix it."
else
    echo "Everything preflight checks is ready. Run :launch to start a pipeline,"
    echo "or :runs to check on one already going."
fi
