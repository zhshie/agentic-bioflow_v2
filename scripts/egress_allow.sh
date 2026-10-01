#!/bin/bash
# Add, remove and list this deployment's own extra domains for the relay's
# outbound allowlist (scripts/nf_relay.py).
#
# Nothing existing: no maintained tool manages a per-deployment addition to
# this repo's own relay allowlist - the allowlist is this repo's, so the
# thing that extends it is too.
#
# Feature 002 (specs/002-relay-allowlist): the built-in allowlist lives in
# plugin code, which only the maintainer can change (hooks/guard_plugin_files.sh
# blocks everyone else) - so a new pipeline needing a new domain used to need
# the maintainer, violating constitution invariants 6/7 ("no configuration",
# "nobody should need the maintainer"). This script is the fix: a member's own
# addition, stored beside their settings, never inside this repo.
#
#   egress_allow.sh add <domain> --reason "<text>"   # validates, appends today's date
#   egress_allow.sh remove <domain>                  # deletes the line, if present
#   egress_allow.sh list                             # domain, date, reason ("來源不明" if missing)
#   egress_allow.sh domains                          # comma list, for on_site.sh to carry; warns on stderr
#
# Storage: <config dir>/egress_allow.tsv, one line per domain -
# `domain<TAB>YYYY-MM-DD<TAB>reason`. The config dir is wherever
# scripts/settings.sh's own token_file() puts the token - not a path this
# script invents, so it travels with the settings root and survives a plugin
# upgrade or reinstall (FR-001, SC-002) and is per deployment (FR-010), the
# same way the token already is (docs/SETTINGS.md).
#
# Validation (FR-004): normalised to lowercase, one trailing '.' stripped, then
# matched against ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$ - at
# least two labels, each 1-63 characters and not starting/ending with '-', a
# final label of letters only (2-63 chars). That last requirement is what
# rejects every IPv4 literal without a separate IP check: a dotted-quad's
# final label is digits, and digits never satisfy [a-z]{2,63}. A wildcard, an
# empty string, or a single-label name (a bare TLD) all fail the same regex
# for the same reason - there is no "at least one dot" case to special-case.
# --reason is required and must be non-empty after trimming (FR-005, TC-018).
# A duplicate add says so and does nothing (idempotent, not an error). At most
# 100 entries (plan.md risk 3: the list travels to the site as one environment
# variable) - refused, by name, past that.
#
# This script never restarts the relay (constitution invariant 2: no file
# here keeps a second copy of run state, and starting/stopping a resident
# process is hooks/confirm_launch.sh's job, not this script's) - it only ever
# says that restarting the outbound channel is the next step.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }

MAX_ENTRIES=100

# Same directory settings.sh's own token_file() resolves the token into -
# not re-derived here, so there is exactly one place that decides where a
# deployment's config/ lives (docs/SETTINGS.md, invariant 3: no path of our
# own baked in).
ALLOW_FILE="$(dirname "$(token_file)")/egress_allow.tsv"

# --- validation --------------------------------------------------------------

normalize_domain() {   # normalize_domain <raw> -> lowercase, no trailing dot
    local d
    d="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
    case "$d" in *.) d="${d%.}" ;; esac
    printf '%s\n' "$d"
}

domain_format_ok() {   # domain_format_ok <normalized> -> 0 if it may be added
    local d="$1"
    [ -n "$d" ] || return 1
    [[ "$d" =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$ ]]
}

# --- the file ------------------------------------------------------------

ensure_config_dir() { mkdir -p "$(dirname "$ALLOW_FILE")"; }

# The file is owner-only like the rest of config/ (docs/SETTINGS.md). Reusing
# file_privacy()/warn_unmeasured_privacy() from scripts/utils/portable.sh
# (already sourced via settings.sh) rather than inventing a second privacy
# check - measured, never assumed (constitution invariant 11).
secure_allow_file() {
    [ -e "$ALLOW_FILE" ] || return 0
    chmod 600 "$ALLOW_FILE" 2>/dev/null || true
    local priv state
    priv="$(file_privacy "$ALLOW_FILE")"
    state="${priv%% *}"
    case "$state" in
        private) ;;
        unknown) warn_unmeasured_privacy "$ALLOW_FILE" "${priv#* }" ;;
        *) echo "warning: $ALLOW_FILE is ${priv#* }." >&2 ;;
    esac
}

entry_exists() {   # entry_exists <normalized-domain> -> 0 if already listed
    [ -r "$ALLOW_FILE" ] || return 1
    awk -F'\t' -v want="$1" '$1==want{found=1} END{exit !found}' "$ALLOW_FILE"
}

count_entries() {
    [ -r "$ALLOW_FILE" ] || { printf '0\n'; return 0; }
    awk -F'\t' '$1!=""{c++} END{print c+0}' "$ALLOW_FILE"
}

# --- commands ------------------------------------------------------------

usage() { die 2 "usage: egress_allow.sh <add|remove|list|domains> ..."; }

cmd_add() {
    local raw="${1:-}" reason=""
    [ -n "$raw" ] || die 2 'usage: egress_allow.sh add <domain> --reason "<text>"'
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --reason)
                [ $# -ge 2 ] || die 2 'usage: egress_allow.sh add <domain> --reason "<text>"'
                reason="$2"; shift 2 ;;
            *) die 2 "unknown argument to 'add': $1" ;;
        esac
    done

    local domain; domain="$(normalize_domain "$raw")"
    domain_format_ok "$domain" || die 1 \
        "refusing '$raw': only accepts a specific domain name (subdomains are fine," \
        "e.g. download.example.org) - never a wildcard, an IP address, a single-label" \
        "top-level domain, or an empty string."

    # One reason is one field of one line: tabs, newlines and carriage
    # returns become spaces, or a reason could split the line and plant an
    # entry that never passed the checks above (developer review of 002).
    reason="${reason//$'\t'/ }"; reason="${reason//$'\n'/ }"; reason="${reason//$'\r'/ }"
    reason="$(printf '%s' "$reason" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -n "$reason" ] || die 1 \
        "a reason is required - name the run or need that made '$domain' necessary."

    ensure_config_dir
    if entry_exists "$domain"; then
        echo "$domain is already present in this deployment's extra allowlist."
        return 0
    fi

    local n; n="$(count_entries)"
    [ "$n" -lt "$MAX_ENTRIES" ] || die 1 \
        "refusing to add '$domain': this deployment's extra allowlist already has" \
        "$MAX_ENTRIES entries, the limit. Remove one first if this is still needed."

    printf '%s\t%s\t%s\n' "$domain" "$(date +%Y-%m-%d)" "$reason" >> "$ALLOW_FILE"
    secure_allow_file
    echo "added $domain (reason: $reason)."
    echo "next step: restart the outbound channel for it to take effect."
}

cmd_remove() {
    local raw="${1:-}"
    [ -n "$raw" ] || die 2 "usage: egress_allow.sh remove <domain>"
    local domain; domain="$(normalize_domain "$raw")"

    if ! entry_exists "$domain"; then
        echo "$domain is not in this deployment's extra allowlist."
        return 0
    fi

    local tmp; tmp="$(mktemp "${ALLOW_FILE}.XXXXXX")" || die 1 "could not create a temp file beside $ALLOW_FILE"
    awk -F'\t' -v want="$domain" '$1!=want' "$ALLOW_FILE" > "$tmp"
    mv "$tmp" "$ALLOW_FILE"
    secure_allow_file
    echo "removed $domain."
    echo "next step: restart the outbound channel for it to take effect."
}

# TC-007/017: a hand-edited line with no date or reason still counts (FR-002 -
# it is still a domain in the file, and the relay must still allow it) but is
# marked so, never silently treated as if someone had followed the normal path.
cmd_list() {
    if [ ! -r "$ALLOW_FILE" ]; then
        echo "(this deployment has no extra allowlist entries yet)"
        return 0
    fi
    local domain date_ reason
    while IFS=$'\t' read -r domain date_ reason || [ -n "$domain" ]; do
        [ -n "$domain" ] || continue
        if [ -z "$date_" ] || [ -z "$reason" ]; then
            printf '%s\t來源不明\n' "$domain"
        else
            printf '%s\t%s\t%s\n' "$domain" "$date_" "$reason"
        fi
    done < "$ALLOW_FILE"
}

# The comma list on_site.sh carries as NF_RELAY_EXTRA_DOMAINS (plan.md,
# Stage S2). Re-validates each stored domain rather than trusting the file
# blindly - a hand edit that broke the format is dropped and named on stderr,
# never silently passed through to the relay (constitution invariant 13).
cmd_domains() {
    [ -e "$ALLOW_FILE" ] || return 0
    # Present but unreadable is not "no list": say so and fail, so on_site.sh
    # carries the reason to the relay instead of an empty list that looks
    # exactly like a deployment that never added anything (TC-009).
    [ -r "$ALLOW_FILE" ] || die 1 "$ALLOW_FILE exists but cannot be read - check its permissions."
    local domain date_ reason out=""
    while IFS=$'\t' read -r domain date_ reason || [ -n "$domain" ]; do
        [ -n "$domain" ] || continue
        if ! domain_format_ok "$domain"; then
            echo "egress_allow: skipping '$domain' in $ALLOW_FILE - not a valid domain." >&2
            continue
        fi
        out="${out:+$out,}$domain"
    done < "$ALLOW_FILE"
    printf '%s\n' "$out"
}

OP="${1:-}"
[ -n "$OP" ] || usage
shift
case "$OP" in
    add)     cmd_add "$@" ;;
    remove)  cmd_remove "$@" ;;
    list)    [ $# -eq 0 ] || die 2 "usage: egress_allow.sh list"; cmd_list ;;
    domains) [ $# -eq 0 ] || die 2 "usage: egress_allow.sh domains"; cmd_domains ;;
    *)       usage ;;
esac
