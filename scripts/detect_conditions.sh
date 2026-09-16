#!/bin/bash
# T1 (plan section "一", trigger 1): "the environment isn't one this plugin was
# designed for" is decided by measurement, never by the model guessing. This is
# the measurement. It reads only this machine and the deployment's settings
# file (scripts/settings.sh) - it NEVER touches the network (no curl, wget,
# ssh, tw, gh; tests/conditions_matrix_test.sh greps the source for exactly
# those) and finishes well under a second, so it is cheap enough to run before
# every session and every command opens (docs/CONDITIONS.md is the matrix this
# implements; the H1/H2/H3 tiers are plan section A2).
#
# Not a second interface detector: the cli|vscode|desktop|web|unknown value
# comes from `status.sh --interface`, the exact same corroboration status.sh's
# own claude_surface() uses (CLAUDE_CODE_ENTRYPOINT alone lies - measured on
# this machine, see status.sh's own header comment). Two implementations of
# that check would drift the moment one of them learned something the other
# didn't.
#
#   detect_conditions.sh              all keys, one `key=value` per line
#   detect_conditions.sh --get <key>  just that value
#
# Exit 0 in both forms unless the usage itself is bad (unknown flag, --get with
# no key or an unknown key), which exits 2.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

usage() {
    echo "usage: detect_conditions.sh [--get <key>]" >&2
    echo "keys: os shell interface reach jq hooks attended tier cell status may_touch_site message" >&2
}

measure() {
    os="$(plat_kind)"

    shell="$(basename "${SHELL:-}" 2>/dev/null)"
    [ -n "$shell" ] || shell=unknown

    # The exact same cross-checked detection status.sh's own claude_surface()
    # uses, collapsed to this fixed vocabulary - see status.sh's --interface
    # fast path. Not reimplemented here on purpose.
    interface="$(bash "$HERE/status.sh" --interface 2>/dev/null)"
    [ -n "$interface" ] || interface=unknown

    # settings.sh's own convention (status.sh: REACH="$(setting reach local)")
    # defaults an absent key to "local" - but that default only makes sense
    # once a settings file exists at all. With none, "local" would claim a
    # reach this deployment was never actually configured with, so this reads
    # unset instead of quietly borrowing that default.
    if [ "$SETTINGS_FOUND" = 1 ]; then
        reach="$(setting reach local)"
    else
        reach=unset
    fi

    # `command -v jq` only proves a file exists (PITFALLS 28's own lesson, in
    # hooks/confirm_cleanup.sh and hooks/confirm_walkthrough.sh): a jq that
    # cannot actually run - wrong architecture, a missing shared library, a
    # Windows jq.exe found by a Linux-shaped PATH - would still pass that
    # check. Ask it to do its job on the smallest possible input instead.
    if printf '{}' | jq -e . >/dev/null 2>&1; then jq_present=yes; else jq_present=no; fi

    # hooks: yes when this is Claude Code running this plugin (CLAUDE_PLUGIN_ROOT
    # is set by the plugin loader; CLAUDECODE=1 is set by Claude Code itself).
    # Any other runtime cannot be measured from here - a lab agent integrating
    # this plugin (H2/H3, plan A2) is expected to say so with
    # AGENTIC_BIOFLOW_HOST_HOOKS, because nothing observable from inside a bare
    # shell distinguishes "no hooks" from "hooks, but this variable happens to
    # be unset".
    case "${AGENTIC_BIOFLOW_HOST_HOOKS:-}" in
        yes|no) hooks="$AGENTIC_BIOFLOW_HOST_HOOKS" ;;
        *)
            if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || [ "${CLAUDECODE:-}" = 1 ]; then
                hooks=yes
            else
                hooks=unknown
            fi
            ;;
    esac

    case "${AGENTIC_BIOFLOW_ATTENDED:-}" in
        yes|no) attended="$AGENTIC_BIOFLOW_ATTENDED" ;;
        *)      attended=unknown ;;
    esac

    # A2's tiers. Ambiguous cases (hooks=unknown) fall to H1 rather than H3:
    # this script only ever reports what it could measure, it does not enforce
    # anything. What is meant to enforce H2/H3 is a Seqera token scoped without
    # launch rights (plan A2), not this script's tier field - but no code here
    # provisions one and M5 has not confirmed a view-role token cannot launch,
    # so today this field is a report and nothing more (docs/LAB_AGENTS.md §3).
    if [ "$hooks" = no ]; then
        tier=H3
    elif [ "$hooks" = yes ] && [ "$attended" = no ]; then
        tier=H2
    else
        tier=H1
    fi

    # Fixed priority, exactly one cell wins: blocked beats unsupported beats
    # supported (plan section 二). Each branch below is one row of
    # docs/CONDITIONS.md's cell-code table; tests/conditions_matrix_test.sh
    # cross-references the two so neither can list a cell the other doesn't.
    if [ "$jq_present" = no ]; then
        cell=blocked-no-jq
        status=blocked
        message="jq is required here and was not found. Install it: macOS \`brew install jq\`; Debian/Ubuntu or WSL \`sudo apt install jq\`."
    elif [ "$tier" = H3 ] && { [ "$reach" = ssh ] || [ "$reach" = local ]; }; then
        cell=blocked-h3-site
        status=blocked
        message="no plugin hooks: Platform read-only only, see docs/LAB_AGENTS.md"
    elif [ "$os" = msys ] && [ "$reach" = ssh ]; then
        cell=unsupported-msys-native
        status=unsupported
        message="Native Windows Git Bash is recognised but not supported by this version: python3 here is a Microsoft Store stub (PITFALLS 20c), a default install carries no jq, and the test suite does not run here. Reaching the site through WSL's own ssh was measured to work (PITFALLS 16g); this version does not use it. Start Claude Code from a WSL shell, or run scripts/report.sh to let the maintainer know."
    elif [ "$reach" = none ]; then
        cell=unsupported-cloud-ce
        status=unsupported
        message="Seqera-managed cloud compute environment is recognised but not supported by this version. Run scripts/report.sh to let the maintainer know."
    else
        cell=supported
        status=supported
        message="This host and configuration are supported."
    fi

    # H3 never touches the site, full stop - independent of which cell won
    # above (an H3 host with no settings file at all lands on the `supported`
    # cell, since nothing else is wrong, but must still not be told it may
    # reach the cluster). Native Git Bash is the other case, and after 16g it
    # is here for a different reason than it used to be: not that it cannot
    # reach the site, but that this version does not carry the bridge that
    # would let it. Either way, it may not - so the answer stays no even where
    # its own cell above did not win (a different reach, say).
    if [ "$tier" = H3 ]; then
        may_touch_site=no
    elif [ "$os" = msys ] && [ "$reach" = ssh ]; then
        may_touch_site=no
    else
        may_touch_site=yes
    fi
}

print_all() {
    cat <<EOF
os=$os
shell=$shell
interface=$interface
reach=$reach
jq=$jq_present
hooks=$hooks
attended=$attended
tier=$tier
cell=$cell
status=$status
may_touch_site=$may_touch_site
message=$message
EOF
}

case "${1:-}" in
    "")
        measure
        print_all
        ;;
    --get)
        if [ $# -ne 2 ] || [ -z "${2:-}" ]; then
            usage; exit 2
        fi
        measure
        case "$2" in
            os)              printf '%s\n' "$os" ;;
            shell)           printf '%s\n' "$shell" ;;
            interface)       printf '%s\n' "$interface" ;;
            reach)           printf '%s\n' "$reach" ;;
            jq)              printf '%s\n' "$jq_present" ;;
            hooks)           printf '%s\n' "$hooks" ;;
            attended)        printf '%s\n' "$attended" ;;
            tier)            printf '%s\n' "$tier" ;;
            cell)            printf '%s\n' "$cell" ;;
            status)          printf '%s\n' "$status" ;;
            may_touch_site)  printf '%s\n' "$may_touch_site" ;;
            message)         printf '%s\n' "$message" ;;
            *) echo "unknown key: $2" >&2; usage; exit 2 ;;
        esac
        ;;
    *)
        usage; exit 2 ;;
esac
exit 0
