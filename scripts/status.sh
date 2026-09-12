#!/bin/bash
# D4: the "where you are" card. One screen, four sections, ending in exactly
# one concrete next step - U3 in the plan this implements.
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

REACH="$(setting reach local)"

echo "== Your environment =="
# CLAUDE_CODE_ENTRYPOINT alone answers the wrong question. Measured on this
# machine: the same VS Code session reported `claude-vscode` once and `cli`
# later, because the value describes how this Bash subprocess was started, not
# which surface the person is looking at. So corroborate it with the editor's
# own variables before claiming anything.
claude_surface() {
    case "${CLAUDE_CODE_ENTRYPOINT:-}" in
        claude-vscode) printf 'vscode\n'; return 0 ;;
    esac
    if [ "${TERM_PROGRAM:-}" = vscode ] || [ -n "${VSCODE_GIT_ASKPASS_MAIN:-}" ]; then
        printf '%s (inside VS Code)\n' "${CLAUDE_CODE_ENTRYPOINT:-cli}"
        return 0
    fi
    printf '%s\n' "${CLAUDE_CODE_ENTRYPOINT:-unknown}"
}

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
