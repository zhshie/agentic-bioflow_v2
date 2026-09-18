#!/bin/bash
# Not GitHub CLI's own issue templates: `gh issue create --template` still
# needs a human at a keyboard picking a template and typing free text, which
# is exactly what a headless "something off-design happened" moment does not
# have. This script produces a machine-filled report from a fixed field
# whitelist and lets `gh` do only the actual sending.
#
# Part of PRINCIPLES.md's boundary procedure (plan "一、邊界程序"): when a
# command file or SKILL.md hits something it was not designed for, it tells
# the user, records the event here, attempts a fix inside the safety net, and
# offers to send the queue as a GitHub issue at the end. This script owns
# steps 2 and 4 (record, send); the procedure text itself lives once in
# skills/operational/SKILL.md.
#
# Privacy is a field whitelist, not redaction: every field is either an enum
# or matches ^[a-z0-9._-]{1,40}$, so a path, a hostname or an email cannot be
# accepted in the first place - there is nothing to scrub afterward. A
# hostname like `t3.nchc.org.tw` still matches that regex (lowercase letters,
# digits and dots), so the two CLI-supplied fields (--step, --script) get one
# more check on top: reject two-or-more dots, `@`, or `/`. That check is not
# applied to the auto-filled fields (plugin_version is legitimately `2.7.2`).
#
#   report.sh add --category <env|egress|scheduler|pipeline|data|request|host> \
#                  --command <setup|launch|runs|downstream|finish|none> \
#                  --step <slug> [--script <name>] [--exit <int>] \
#                  [--outcome resolved|workaround|unresolved]
#   report.sh list
#   report.sh send [--yes] [--dry-run]
#   report.sh --dir
#
# `--dir` prints where the queue lives and nothing else - the one place that
# computes this (reports_dir(), below) rather than a second copy of the same
# fallback chain elsewhere. hooks/session_start.sh used to reimplement it as
# `$(dirname "$SETTINGS_FILE")/reports`, which agreed with this script only
# when a settings file was actually found; before setup has ever run,
# reports_dir() falls back to the XDG state default, session_start.sh's copy
# did not know about that fallback, and a report queued before setup existed
# was never in the directory the hook went looking in - queued forever,
# reminded never. Calling this instead of re-deriving the path is what keeps
# the two in agreement by construction rather than by two edits staying in
# sync.
#
# `add` never queues a partially-valid report: every field is checked before
# anything is written, and any failure exits 2 with nothing on disk.
#
# `send` always shows every field of every queued report first and stops
# without --yes - there is no way to make this script send silently. With
# --yes it checks identity (`gh api user`, clocked so a hung network does not
# hang the whole flow): the maintainer's own login never sends, everyone else
# either gets a deduped comment/new issue through `gh`, or - no `gh`, not
# logged in, or the identity check timed out - a prefilled issue URL and the
# queue stays local. --dry-run (or REPORT_DRY_RUN=1) prints the `gh` commands
# instead of running them, which is how tests exercise this without ever
# filing a real issue.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
# shellcheck source=scripts/settings.sh
. "$HERE/settings.sh"

REPO="zhshie/agentic-bioflow_v2"

usage() {
    cat >&2 <<'U'
usage:
  report.sh add --category <env|egress|scheduler|pipeline|data|request|host> \
                 --command <setup|launch|runs|downstream|finish|none> \
                 --step <slug> [--script <name>] [--exit <int>] \
                 [--outcome resolved|workaround|unresolved]
  report.sh list
  report.sh send [--yes] [--dry-run]
  report.sh --dir
U
}

# --- sha256, without touching scripts/utils/portable.sh -----------------
# portable.sh has no sha256 helper and this file may not add one, so the
# handful of lines a fallback needs are inlined here instead: sha256sum on
# Linux, shasum -a 256 on macOS. If neither exists the signature simply
# cannot be computed and `add` fails loudly rather than queuing an
# unsigned report.
sha256_hex() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    else
        echo "neither sha256sum nor shasum is on PATH - cannot sign a report" >&2
        return 1
    fi
}

# --- field validation -----------------------------------------------------
is_enum() {
    local v="$1"; shift
    local x
    for x in "$@"; do [ "$v" = "$x" ] && return 0; done
    return 1
}

# Base shape every non-enum field must have. Deliberately permissive on dot
# count - the auto-filled plugin_version ("2.7.2") must pass this on its own.
is_slug() {
    local v="$1"
    [ -n "$v" ] || return 1
    [ "${#v}" -le 40 ] || return 1
    case "$v" in
        *[!a-z0-9._-]*) return 1 ;;
    esac
    return 0
}

# --step and --script are the two fields a caller writes by hand, so a path
# or a hostname is one typo away from landing in them. On top of is_slug:
# reject `@` or `/` (belt and braces - the character class above already
# excludes both) and reject two or more dots, which is what actually catches
# a dotted hostname that otherwise satisfies the base regex.
is_user_slug() {
    local v="$1" dots
    is_slug "$v" || return 1
    case "$v" in *@*|*/*) return 1 ;; esac
    dots=$(printf '%s' "$v" | tr -cd '.' | wc -c)
    [ "$dots" -le 1 ]
}

is_exit_code() {
    case "$1" in ''|*[!0-9]*) return 1 ;; esac
    [ "$1" -ge 0 ] && [ "$1" -le 255 ]
}

CATEGORY_ENUM="env egress scheduler pipeline data request host"
COMMAND_ENUM="setup launch runs downstream finish none"
OUTCOME_ENUM="resolved workaround unresolved"

# --- where the queue lives --------------------------------------------------
# AGENTIC_BIOFLOW_REPORTS_DIR overrides everything (tests use this so no run
# ever touches a real settings file or a real $HOME). Otherwise: beside the
# settings file when one was found, or the XDG state default - setup may not
# have run yet, which is exactly when something off-design is most likely.
reports_dir() {
    if [ -n "${AGENTIC_BIOFLOW_REPORTS_DIR:-}" ]; then
        printf '%s\n' "$AGENTIC_BIOFLOW_REPORTS_DIR"
        return 0
    fi
    if [ "$SETTINGS_FOUND" = 1 ]; then
        printf '%s\n' "$(dirname "$SETTINGS_FILE")/reports"
        return 0
    fi
    printf '%s\n' "${XDG_STATE_HOME:-${HOME:-}/.local/state}/agentic-bioflow/reports"
}

# --- auto-filled fields ----------------------------------------------------
version_extract() {
    local f="$1" v
    [ -r "$f" ] || { printf 'unknown\n'; return 0; }
    v=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$f" | head -1)
    printf '%s\n' "${v:-unknown}"
}

# Cell, tier and interface all come from detect_conditions.sh, which takes the
# interface from status.sh --interface - one reading of this machine, not a
# copy per script. If it fails, the field is `unknown` rather than blocking a
# report.
cond_get() {
    local key="$1" dc="$HERE/detect_conditions.sh" v
    if [ -r "$dc" ]; then
        v=$(bash "$dc" --get "$key" 2>/dev/null)
        [ -n "$v" ] && { printf '%s\n' "$v"; return 0; }
    fi
    printf 'unknown\n'
}

# --- add --------------------------------------------------------------------
add_report() {
    local category="" command="" step="" script="" exitc="" outcome=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --category) category="${2:-}"; shift 2 ;;
            --command)  command="${2:-}"; shift 2 ;;
            --step)     step="${2:-}"; shift 2 ;;
            --script)   script="${2:-}"; shift 2 ;;
            --exit)     exitc="${2:-}"; shift 2 ;;
            --outcome)  outcome="${2:-}"; shift 2 ;;
            *) echo "add: unknown argument '$1'" >&2; usage; return 2 ;;
        esac
    done

    is_enum "$category" $CATEGORY_ENUM || {
        echo "add: --category must be one of: $CATEGORY_ENUM" >&2; return 2; }
    is_enum "$command" $COMMAND_ENUM || {
        echo "add: --command must be one of: $COMMAND_ENUM" >&2; return 2; }
    is_user_slug "$step" || {
        echo "add: --step must match ^[a-z0-9._-]{1,40}\$, at most one dot, no path or hostname shape" >&2; return 2; }
    if [ -n "$script" ]; then
        is_user_slug "$script" || {
            echo "add: --script must match ^[a-z0-9._-]{1,40}\$, at most one dot, no path or hostname shape" >&2; return 2; }
    fi
    if [ -n "$exitc" ]; then
        is_exit_code "$exitc" || {
            echo "add: --exit must be an integer 0-255" >&2; return 2; }
    fi
    if [ -n "$outcome" ]; then
        is_enum "$outcome" $OUTCOME_ENUM || {
            echo "add: --outcome must be one of: $OUTCOME_ENUM" >&2; return 2; }
    fi

    local plugin_version os_v reach_v cell_v tier_v iface_v sig dir file
    plugin_version="$(version_extract "$ROOT/.claude-plugin/plugin.json")"
    os_v="$(plat_kind)"
    reach_v="$(setting reach local)"
    cell_v="$(cond_get cell)"
    tier_v="$(cond_get tier)"
    iface_v="$(cond_get interface)"

    sig="$(printf '%s' "${category}|${command}|${step}|${script}|${exitc}" | sha256_hex)" || return 2
    sig="${sig:0:12}"

    dir="$(reports_dir)"
    mkdir -p "$dir" || { echo "add: cannot create $dir" >&2; return 2; }
    chmod 700 "$dir" 2>/dev/null || true

    file="$dir/$(date +%s)-$$-${sig}.report"
    {
        printf 'category: %s\n'       "$category"
        printf 'command: %s\n'        "$command"
        printf 'step: %s\n'           "$step"
        printf 'script: %s\n'         "$script"
        printf 'exit: %s\n'           "$exitc"
        printf 'outcome: %s\n'        "$outcome"
        printf 'plugin_version: %s\n' "$plugin_version"
        printf 'os: %s\n'             "$os_v"
        printf 'reach: %s\n'          "$reach_v"
        printf 'cell: %s\n'           "$cell_v"
        printf 'tier: %s\n'           "$tier_v"
        printf 'interface: %s\n'      "$iface_v"
        printf 'signature: %s\n'      "$sig"
    } > "$file" || { echo "add: cannot write $file" >&2; return 2; }
    chmod 600 "$file"

    # Printed so the next steps of the procedure reach context even when
    # skills/operational/SKILL.md was never loaded this turn (plan, section
    # 七 - the "保留一項原本為拆分設計的保險").
    cat <<EOF
Recorded (queued, not sent) - category=$category command=$command step=$step signature=$sig
  $file

Next (skills/operational/SKILL.md, "Off-design: when nothing here covers it"):
  3. Attempt a fix inside the safety net. Submitting a run and any
     destructive delete still need the user's explicit confirmation. Do not
     edit this plugin's own files - that is what hooks/guard_plugin_files.sh
     is for.
  4. When this task is finished, run 'scripts/report.sh send' - it shows
     every field of everything queued and sends nothing without --yes.
EOF
}

# --- list ---------------------------------------------------------------
queued_files() {
    local dir="$1" f
    [ -d "$dir" ] || return 0
    find "$dir" -maxdepth 1 -type f -name '*.report' 2>/dev/null | sort
}

print_report() {
    local f="$1"
    echo "--- $(basename "$f") ---"
    cat "$f"
}

list_reports() {
    local dir files
    dir="$(reports_dir)"
    files="$(queued_files "$dir")"
    if [ -z "$files" ]; then
        echo "No reports queued."
        return 0
    fi
    local f
    while IFS= read -r f; do
        print_report "$f"
        echo
    done <<<"$files"
}

# --- send -----------------------------------------------------------------
field() { sed -n "s/^$1: //p" "$2" | head -1; }

report_title() {
    printf 'off-design: %s/%s/%s' \
        "$(field category "$1")" "$(field command "$1")" "$(field step "$1")"
}

report_body() {
    local f="$1"
    printf 'category: %s\ncommand: %s\nstep: %s\nscript: %s\nexit: %s\noutcome: %s\nplugin_version: %s\nos: %s\nreach: %s\ncell: %s\ntier: %s\ninterface: %s\nsignature: %s\n' \
        "$(field category "$f")" "$(field command "$f")" "$(field step "$f")" \
        "$(field script "$f")" "$(field exit "$f")" "$(field outcome "$f")" \
        "$(field plugin_version "$f")" "$(field os "$f")" "$(field reach "$f")" \
        "$(field cell "$f")" "$(field tier "$f")" "$(field interface "$f")" \
        "$(field signature "$f")"
}

# Pure-bash percent-encoding. Every field here is ASCII by construction (the
# same whitelist add() enforces), so this never has to think about UTF-8.
urlencode() {
    local s="$1" out="" i c
    for (( i = 0; i < ${#s}; i++ )); do
        c="${s:i:1}"
        case "$c" in
            [a-zA-Z0-9.~_-]) out+="$c" ;;
            $'\n') out+='%0A' ;;
            *) printf -v c '%%%02X' "'$c"; out+="$c" ;;
        esac
    done
    printf '%s' "$out"
}

gh_fallback_urls() {
    echo "gh is not available, not logged in, or did not answer in time."
    echo "Reports stay queued locally; here is a prefilled link for each:"
    local f title body
    for f in "$@"; do
        title="$(report_title "$f")"
        body="$(report_body "$f")"
        printf 'https://github.com/%s/issues/new?title=%s&body=%s&labels=off-design\n' \
            "$REPO" "$(urlencode "$title")" "$(urlencode "$body")"
    done
}

send_one() {
    local f="$1" dry="$2" sig title body num
    sig="$(field signature "$f")"
    title="$(report_title "$f")"
    body="$(report_body "$f")"

    if [ "$dry" = 1 ]; then
        echo "would run: gh issue list --repo $REPO --label off-design --state open --search \"$sig in:body\" --json number --jq '.[0].number // empty'"
        echo "would run (if found):     gh issue comment <number> --repo $REPO --body '<report fields, signature $sig>'"
        echo "would run (if not found): gh issue create --repo $REPO --title \"$title\" --label off-design --body '<report fields, signature $sig>'"
        return 0
    fi

    num="$(gh issue list --repo "$REPO" --label off-design --state open \
              --search "$sig in:body" --json number --jq '.[0].number // empty' 2>/dev/null)"
    if [ -n "$num" ]; then
        if gh issue comment "$num" --repo "$REPO" --body "$body" >/dev/null 2>&1; then
            echo "commented on existing issue #$num (signature $sig)"
            rm -f "$f"
        else
            echo "failed to comment on issue #$num - report kept queued"
        fi
    else
        if gh issue create --repo "$REPO" --title "$title" --label off-design --body "$body" >/dev/null 2>&1; then
            echo "filed a new off-design issue (signature $sig)"
            rm -f "$f"
        else
            echo "failed to create an issue - report kept queued"
        fi
    fi
}

send_reports() {
    local yes=0 dry=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --yes)      yes=1; shift ;;
            --dry-run)  dry=1; shift ;;
            *) echo "send: unknown argument '$1'" >&2; usage; return 2 ;;
        esac
    done
    [ "${REPORT_DRY_RUN:-0}" = 1 ] && dry=1

    local dir files
    dir="$(reports_dir)"
    files="$(queued_files "$dir")"
    if [ -z "$files" ]; then
        echo "No reports queued."
        return 0
    fi

    echo "Queued reports (every field that would be sent):"
    local f
    while IFS= read -r f; do
        print_report "$f"
        echo
    done <<<"$files"

    if [ "$yes" != 1 ]; then
        echo "Nothing sent - re-run with --yes to send these to https://github.com/$REPO (label off-design)."
        return 0
    fi

    # Not `mapfile`: bash 4+ only, and macOS still ships bash 3.2
    # (tests/portable_userland.sh, tests/bsd_userland_test.sh).
    local FILE_ARR=()
    while IFS= read -r f; do
        [ -n "$f" ] && FILE_ARR+=("$f")
    done <<<"$files"

    if ! command -v gh >/dev/null 2>&1; then
        gh_fallback_urls "${FILE_ARR[@]}"
        return 0
    fi

    local login rc
    login="$(clocked 3 gh api user --jq .login 2>/dev/null)"; rc=$?
    if [ "$rc" != 0 ] || [ -z "$login" ]; then
        gh_fallback_urls "${FILE_ARR[@]}"
        return 0
    fi
    if [ "$login" = zhshie ]; then
        echo "Maintainer identity detected (gh api user -> zhshie)."
        echo "design this into the plugin instead - not sent, queue kept."
        return 0
    fi

    for f in "${FILE_ARR[@]}"; do
        send_one "$f" "$dry"
    done
}

# --- dispatch ---------------------------------------------------------------
case "${1:-}" in
    add)   shift; add_report "$@"; exit $? ;;
    list)  shift; list_reports "$@"; exit $? ;;
    send)  shift; send_reports "$@"; exit $? ;;
    --dir) reports_dir; exit 0 ;;
    *) usage; exit 2 ;;
esac
