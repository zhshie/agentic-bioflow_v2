#!/bin/bash
# Sourced by every hook (feature 005, #48): is agentic-bioflow IN USE for this
# call? The hooks exit 0 without a word when the answer is no, so a session that
# has nothing to do with this plugin never sees it - not a gate, not a reminder,
# not an overview. Constitution 2.0.0, Safety Net.
#
#   abf_in_use <raw hook input JSON> <command text>      0 = in use, 1 = not
#
# <command text> is whatever the caller has of the call's own text. The gates
# pass the raw input again: reading more than the command only ever makes the
# answer "in use", the safe direction. Stop and SessionStart pass "".
#
# In use means ANY of (docs/PRINCIPLES.md names them once more):
#   1. a Seqera / Tower MCP tool is being called (that matcher is the plugin's);
#   2. this session has a marker: hooks/plugin_intro.sh writes
#      $STATE/in-use/<session id> the first time the user reaches for the
#      plugin (a typed /agentic-bioflow: command, a plugin skill load, the
#      natural-language door). A subagent's calls carry its parent's session id,
#      so the marker covers them. A session whose overview was already shown
#      before this version has $STATE/intro-shown/<id> and counts the same;
#   3. the call itself names this plugin's root, one of its scripts as
#      scripts/<name>, `tw` as a word, or a path under the deployment root or
#      its storage_root;
#   4. the session's cwd is under the deployment root or its storage_root.
# And when this cannot tell - no session id, a state path that is not a readable
# directory - the answer is in use: one gate too many beats one missed.
#
# Fork-free on purpose (#34: every process is expensive under Git Bash, and this
# runs before the hook's own jq probe). Bash builtins and [[ =~ ]] only, nothing
# `set -e`-fragile, and nothing here changes the caller's shell options for
# longer than one call. Portable to bash 3.2.

# A path in one spelling: backslashes to slashes, doubled slashes collapsed,
# C:\x and /mnt/c/x and /cygdrive/c/x all to /c/x, no trailing slash. Result in
# REPLY. Case is NOT folded here; abf_in_use turns on nocasematch for the
# comparisons (a case-insensitive match on Linux only widens "in use").
_abf_canon() {
    local p="$1" re_drive='^([A-Za-z]):(/.*)?$' re_mnt='^/(mnt|cygdrive)/([A-Za-z])(/.*)?$'
    p="${p//\\//}"
    while [[ $p == *//* ]]; do p="${p//\/\///}"; done
    if [[ $p =~ $re_drive ]]; then
        p="/${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
    elif [[ $p =~ $re_mnt ]]; then
        p="/${BASH_REMATCH[2]}${BASH_REMATCH[3]}"
    fi
    REPLY="${p%/}"
}

# True when canonical path $1 is, or is under, canonical path $2.
_abf_under() {
    [ -n "$2" ] || return 1
    [[ "$1/" == "$2"/* ]]
}

# True when text $1 contains path $2 as a whole path: what follows it is the end
# of the text, a slash, or a character that cannot continue a name (so /x/dep is
# found in "rm /x/dep/a" but not in "/x/dep-neighbour").
_abf_has_path() {
    local t="$1" p="$2" rest
    while [[ $t == *"$p"* ]]; do
        rest="${t#*"$p"}"
        case "$rest" in
            ''|/*|[!A-Za-z0-9_.-]*) return 0 ;;
        esac
        t="$rest"
    done
    return 1
}

# True when the (lightly normalised) text $1 contains canonical path $2 in any
# spelling a command might use. Short paths prove nothing, so a path under
# four characters is ignored rather than matching half the world.
_abf_text_has() {
    local t="$1" p="$2" d rest re='^/([A-Za-z])(/.*)?$'
    [ "${#p}" -ge 4 ] || return 1
    _abf_has_path "$t" "$p" && return 0
    if [[ $p =~ $re ]]; then
        d="${BASH_REMATCH[1]}"; rest="${BASH_REMATCH[2]}"
        _abf_has_path "$t" "$d:$rest" && return 0
        _abf_has_path "$t" "/mnt/$d$rest" && return 0
        _abf_has_path "$t" "/cygdrive/$d$rest" && return 0
    fi
    return 1
}

# _abf_read_key <file> <key>  ->  REPLY (empty when absent). The same reading
# scripts/settings.sh does: `key: value`, cut at the first `#`.
_abf_read_key() {
    REPLY=""
    [ -r "$1" ] || return 0
    local line re="^[[:space:]]*$2[[:space:]]*:[[:space:]]*(.*)\$"
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ $line =~ $re ]]; then
            line="${BASH_REMATCH[1]}"
            line="${line%%#*}"
            line="${line%"${line##*[![:space:]]}"}"
            case "$line" in
                \"*\") line="${line#\"}"; line="${line%\"}" ;;
                \'*\') line="${line#\'}"; line="${line%\'}" ;;
            esac
            REPLY="$line"
            return 0
        fi
    done < "$1"
    return 0
}

# Where the deployment is, the way scripts/settings.sh finds it: LAB_SETTINGS_FILE
# wins outright, otherwise the one-line root pointer. Sets _ABF_SETTINGS and
# _ABF_ROOT (canonical). Returns 1 when there is no deployment on this machine
# - no settings file named, or one that is not there - which is an answer, not
# a failure to answer.
_abf_find_deployment() {
    _ABF_SETTINGS=""; _ABF_ROOT=""
    local d line pointer
    if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
        [ -r "$LAB_SETTINGS_FILE" ] || return 1
        _ABF_SETTINGS="$LAB_SETTINGS_FILE"
        d="${LAB_SETTINGS_FILE%/*}"
        [ "$d" = "$LAB_SETTINGS_FILE" ] && d=.
        case "$d" in */config) d="${d%/*}" ;; esac
        _abf_canon "$d"; _ABF_ROOT="$REPLY"
        return 0
    fi
    pointer="${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/root"
    [ -r "$pointer" ] || return 1
    IFS= read -r line < "$pointer" || [ -n "$line" ]
    line="${line//$'\r'/}"
    [ -n "$line" ] || return 1
    _abf_canon "$line"; _ABF_ROOT="$REPLY"
    [ -n "$_ABF_ROOT" ] || return 1
    _ABF_SETTINGS="$line/config/env.yaml"
    return 0
}

abf_in_use() {
    local _ncm=0 _rc
    shopt -q nocasematch && _ncm=1
    shopt -s nocasematch
    _abf_in_use_inner "${1:-}" "${2:-}"
    _rc=$?
    [ "$_ncm" = 1 ] || shopt -u nocasematch
    return "$_rc"
}

_abf_in_use_inner() {
    local input="$1" text="$2"
    local re_tool='"tool_name"[[:space:]]*:[[:space:]]*"([^"]*)"'
    local re_sid='"session_id"[[:space:]]*:[[:space:]]*"([^"]*)"'
    local re_cwd='"cwd"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
    local re_mcp='^mcp__.*([Ss]eqera|[Tt]ower)'
    local re_tw='(^|[^[:alnum:]_.-])tw([^[:alnum:]_.-]|$)'
    local tool="" sid="" cwd="" state f n

    # 1. a Seqera / Tower MCP tool
    if [[ $input =~ $re_tool ]]; then tool="${BASH_REMATCH[1]}"; fi
    [[ $tool =~ $re_mcp ]] && return 0

    # 2. the session: no id means this cannot tell, so in use
    if [[ $input =~ $re_sid ]]; then sid="${BASH_REMATCH[1]}"; fi
    sid="${sid//[^A-Za-z0-9_-]/}"
    [ -n "$sid" ] || return 0

    state="${AGENTIC_BIOFLOW_STATE_DIR:-${XDG_STATE_HOME:-${HOME:-}/.local/state}/agentic-bioflow}"
    if [ -e "$state" ]; then
        { [ -d "$state" ] && [ -r "$state" ] && [ -x "$state" ]; } || return 0
        [ -e "$state/in-use/$sid" ] && return 0
        [ -e "$state/intro-shown/$sid" ] && return 0
    fi

    # 3. the call's own text. JSON newlines and tabs are the two characters
    # (\n, \t) that glue a word to the one before it; backslashes become
    # slashes so a Windows path reads like any other. A JSON-escaped backslash
    # (two of them) goes first, or C:\\new would lose its n to the newline rule.
    text="${text//\\\\//}"
    text="${text//\\n/ }"; text="${text//\\t/ }"; text="${text//\\r/ }"
    text="${text//\\//}"
    while [[ $text == *//* ]]; do text="${text//\/\///}"; done
    [[ $text =~ $re_tw ]] && return 0
    # Naming the plugin's install location without its resolved path: the
    # variable itself, or anything under ~/.claude/plugins. This is what
    # guard_plugin_files.sh exists to catch, so it cannot read as "not in use".
    [[ $text == *CLAUDE_PLUGIN_ROOT* || $text == */.claude/plugins/* ]] && return 0

    local roots="${CLAUDE_PLUGIN_ROOT:-}" here="${BASH_SOURCE[0]}" base
    here="${here%/*}"; [ "$here" = "${BASH_SOURCE[0]}" ] && here=.
    base="$here/.."
    case "$here" in /*/hooks|[A-Za-z]:*/hooks) roots="$roots"$'\n'"${here%/hooks}" ;; esac
    local r
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        _abf_canon "$r"
        _abf_text_has "$text" "$REPLY" && return 0
    done <<<"$roots"

    # The plugin's own scripts, by the name a relative call uses.
    if [[ $text == *scripts/* ]]; then
        for f in "$base"/scripts/*.sh "$base"/scripts/*.py "$base"/scripts/utils/*.sh; do
            [ -e "$f" ] || continue
            n="${f#"$base"/}"
            [[ $text == *"$n"* ]] && return 0
        done
    fi

    # 4. the deployment: where the session is, and what the call names
    _abf_find_deployment || return 1
    local sroot=""
    _abf_read_key "$_ABF_SETTINGS" storage_root
    if [ -n "$REPLY" ]; then _abf_canon "$REPLY"; sroot="$REPLY"; fi
    local runs=""
    if [ -n "${LAB_RUNS_DIR:-}" ]; then _abf_canon "$LAB_RUNS_DIR"; runs="$REPLY"; fi

    if [[ $input =~ $re_cwd ]]; then cwd="${BASH_REMATCH[1]}"; else cwd="${PWD:-}"; fi
    if [ -n "$cwd" ]; then
        _abf_canon "$cwd"; cwd="$REPLY"
        _abf_under "$cwd" "$_ABF_ROOT" && return 0
        _abf_under "$cwd" "$sroot" && return 0
        _abf_under "$cwd" "$runs" && return 0
    else
        # a cwd that cannot be read is not evidence of anything else
        return 0
    fi
    _abf_text_has "$text" "$_ABF_ROOT" && return 0
    _abf_text_has "$text" "$sroot" && return 0
    _abf_text_has "$text" "$runs" && return 0
    return 1
}
