#!/bin/bash
# Nothing existing: Claude Code runs every installed plugin's hooks in every session and has no per-plugin switch for 'only when this plugin is in use', so each hook asks this check first.
#
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
# longer than one call. Portable to bash 3.2. The one exception is a text over
# 8 KB (a big here-doc or Write): one sed normalises it, because the builtin
# replacements are quadratic in bash and ran past the hooks' timeout (#62).

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

# ~ and $HOME / ${HOME} at the start of a path value, as a shell would read
# them. Result in REPLY.
_abf_home() {
    local v="$1" h="${HOME:-}"
    case "$v" in
        '~') v="$h" ;;
        '~/'*) v="$h/${v#\~/}" ;;
        '$HOME') v="$h" ;;
        '$HOME/'*) v="$h/${v#\$HOME/}" ;;
        '${HOME}') v="$h" ;;
        '${HOME}/'*) v="$h/${v#\$\{HOME\}/}" ;;
    esac
    REPLY="$v"
}

# The physical form of an existing directory (symlinks resolved), canonical.
# cd -P and $PWD are builtins, so this forks nothing; the caller's directory is
# put back. Fails (REPLY empty) for a path that is relative or not a directory.
_abf_phys() {
    REPLY=""
    case "$1" in /*) ;; *) return 1 ;; esac
    [ -d "$1" ] || return 1
    local old="$PWD" p
    # No way back to a caller's directory that no longer exists: do not move
    # (the hook would carry on elsewhere). Unresolved is the safe answer.
    [ -d "$old" ] || return 1
    cd -P -- "$1" 2>/dev/null || return 1
    p="$PWD"
    cd -- "$old" 2>/dev/null
    _abf_canon "$p"
    return 0
}

# The physical form of a path that may not exist yet (a file about to be
# written): the nearest existing ancestor, resolved, plus the rest.
_abf_phys_path() {
    local p="$1" rest="" n=0
    REPLY=""
    case "$p" in /*) ;; *) return 1 ;; esac
    while [ ! -d "$p" ] && [ "$n" -lt 40 ]; do
        rest="/${p##*/}$rest"; p="${p%/*}"; n=$((n+1))
        [ -n "$p" ] || p=/
    done
    _abf_phys "$p" || return 1
    REPLY="${REPLY%/}$rest"
    return 0
}

# Whether the in-use marker could be written under state dir $1: it exists and
# is a writable directory (and so is in-use/ when there), or the nearest
# existing ancestor is writable so it can be created.
_abf_state_ok() {
    local s="$1" d n=0
    if [ -e "$s" ]; then
        { [ -d "$s" ] && [ -w "$s" ] && [ -x "$s" ]; } || return 1
        if [ -e "$s/in-use" ]; then
            { [ -d "$s/in-use" ] && [ -w "$s/in-use" ] && [ -x "$s/in-use" ]; } || return 1
        fi
        return 0
    fi
    d="${s%/*}"
    while [ -n "$d" ] && [ ! -e "$d" ] && [ "$n" -lt 40 ]; do d="${d%/*}"; n=$((n+1)); done
    [ -n "$d" ] || d=/
    { [ -d "$d" ] && [ -w "$d" ] && [ -x "$d" ]; }
}

# True when text $1 contains path $2 as a whole path: what follows it is the end
# of the text, a slash, or a character that cannot continue a name (so /x/dep is
# found in "rm /x/dep/a" but not in "/x/dep-neighbour").
# One regex with the path quoted (literal): `${t#*"$p"}` made bash try every
# prefix of the text, quadratic - 36 s on a 300 KB here-doc that ends with a
# path under storage_root, past the hooks' timeout (#62).
_abf_has_path() {
    local re_after='($|[^A-Za-z0-9_.-])'
    [[ $1 == *"$2"* ]] || return 1
    [[ $1 =~ "$2"$re_after ]]
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

# The relative path from canonical directory $1 to canonical path $2 (`runs3`,
# `../runs3`, `home/runs3`), in REPLY. Case-insensitive like the rest
# (nocasematch is on inside abf_in_use).
_abf_rel() {
    local f="$1" up=""
    while [ -n "$f" ] && ! _abf_under "$2" "$f"; do
        f="${f%/*}"; up="$up../"
    done
    REPLY="${2:${#f}}"; REPLY="$up${REPLY#/}"; REPLY="${REPLY%/}"
}

# True when text $1 holds relative path $2 at the start of a word (after a
# blank, a quote, `=`, `:`, a separator, or `./`) as a whole path. A single
# name under 4 characters is ignored: short names prove nothing.
_abf_text_has_rel() {
    local r="$2" re_before='(^|[[:space:]=":;&|(])(\./)?' re_after='($|[^A-Za-z0-9_.-])'
    [ -n "$r" ] || return 1
    case "$r" in */*) ;; *) [ "${#r}" -ge 4 ] || return 1 ;; esac
    [[ $1 == *"$r"* ]] || return 1
    [[ $1 =~ $re_before"$r"$re_after ]]
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
    local d line pointer f
    if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
        _abf_home "$LAB_SETTINGS_FILE"; f="$REPLY"
        case "$f" in /*|[A-Za-z]:*) ;; *) f="${PWD:-.}/$f" ;; esac
        [ -r "$f" ] || return 1
        _ABF_SETTINGS="$f"
        d="${f%/*}"
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
    local re_tw='(^|[^[:alnum:]_.-])tw(\.exe)?([^[:alnum:]_.-]|$)'
    local re_tp='"transcript_path"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
    local re_fp='"(file_path|notebook_path)"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
    local fp=""
    local tool="" sid="" cwd="" state f n h=""

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

    # 3. the call's own text. The hook input also carries the session's cwd and
    # transcript path; those are not what the call names, and cwd has its own
    # test below (condition 2), so they are taken out of the text first. The
    # target of a file tool is kept aside to be compared by its physical path.
    if [[ $text =~ $re_fp ]]; then fp="${BASH_REMATCH[2]}"; fi
    if [[ $text =~ $re_cwd ]]; then text="${text/"${BASH_REMATCH[0]}"/}"; fi
    if [[ $text =~ $re_tp ]]; then text="${text/"${BASH_REMATCH[0]}"/}"; fi
    # The call's own text. JSON newlines and tabs are the two characters
    # (\n, \t) that glue a word to the one before it; backslashes become
    # slashes so a Windows path reads like any other. A JSON-escaped backslash
    # (two of them) goes first, or C:\\new would lose its n to the newline rule.
    # Quotes around a path part are not part of the path (#53): a JSON-escaped
    # double quote and a single quote are dropped, so "$HOME"/runs3 reads as
    # $HOME/runs3. This only widens what matches, the safe direction.
    # #62: ${x//p/} costs a pass over the rest of the text per match, so a big
    # text (a here-doc of thousands of lines: one `\n` each) is normalised the
    # same way by one sed; a text under 8 KB keeps the fork-free form. Under
    # MSYS/Cygwin that sed runs in C.UTF-8: in the plain C locale (what it gets
    # when LANG is unset, as under Claude Code on Windows) GNU sed there is
    # itself quadratic on one long line with many matches (measured: 50-120 s
    # at 300 KB, 0.1-0.4 s in C.UTF-8).
    local norm="" loc="${LC_ALL:-}"
    if [ "${#text}" -gt 8192 ]; then
        case "$OSTYPE" in msys*|cygwin*) loc=C.UTF-8 ;; esac
        norm=$(LC_ALL=$loc sed -e 's#\\\\#/#g' -e 's#\\[ntr]# #g' -e 's#\\"##g' \
               -e "s#'##g" -e 's#\\#/#g' -e 's#//*#/#g' <<<"$text" 2>/dev/null)
    fi
    if [ -n "$norm" ]; then
        text=$norm
    else
        text="${text//\\\\//}"
        text="${text//\\n/ }"; text="${text//\\t/ }"; text="${text//\\r/ }"
        text="${text//\\\"/}"; text="${text//\'/}"
        text="${text//\\//}"
        while [[ $text == *//* ]]; do text="${text//\/\///}"; done
    fi
    # ~ and $HOME spell the home directory; a path in the text may use either.
    if [ -n "${HOME:-}" ]; then
        _abf_canon "$HOME"; h="$REPLY"
        text="${text//\$\{HOME\}/$h}"; text="${text//\$HOME/$h}"
        text="${text// \~\// $h/}"
        # in-use-path-spellings: PowerShell's and cmd's names for the home
        # directory, and a `~/` that starts the text or follows `=`, `:` or a
        # quote (`x=~/runs3`, `--dir=~/runs3`, a command that starts with it).
        case "$text" in
            *USERPROFILE*|*'env:HOME'*)
                text="${text//\$\{env:USERPROFILE\}/$h}"; text="${text//\$env:USERPROFILE/$h}"
                text="${text//%USERPROFILE%/$h}"; text="${text//\$env:HOME/$h}" ;;
        esac
        case "$text" in
            '~/'*|*'=~/'*|*':~/'*|*'"~/'*)
                case "$text" in '~/'*) text="$h/${text#\~/}" ;; esac
                text="${text//=\~\//=$h/}"; text="${text//:\~\//:$h/}"; text="${text//\"\~\//\"$h/}" ;;
        esac
        # `~<this user>/` is the same home directory.
        local u="${USER:-${LOGNAME:-${USERNAME:-}}}"
        u="${u//[^A-Za-z0-9._-]/}"
        if [ -n "$u" ] && [[ $text == *"~$u/"* ]]; then text="${text//\~$u\//$h/}"; fi
    fi
    [[ $text =~ $re_tw ]] && return 0
    # Naming the plugin's install location without its resolved path: the
    # variable itself, or anything under ~/.claude/plugins. This is what
    # guard_plugin_files.sh exists to catch, so it cannot read as "not in use".
    [[ $text == *CLAUDE_PLUGIN_ROOT* || $text == */.claude/plugins/* ]] && return 0

    local roots="${CLAUDE_PLUGIN_ROOT:-}" here="${BASH_SOURCE[0]}" base
    here="${here%/*}"; [ "$here" = "${BASH_SOURCE[0]}" ] && here=.
    base="$here/.."
    case "$here" in /*/hooks|[A-Za-z]:*/hooks) roots="$roots"$'\n'"${here%/hooks}" ;; esac
    local r rc rp fpc="" fpp="" icwd=""
    # The session working inside the plugin itself: a bare `bash on_site.sh`
    # there names no root, but is the plugin's own script (acceptance round 2).
    if [[ $input =~ $re_cwd ]]; then _abf_canon "${BASH_REMATCH[1]}"; icwd="$REPLY"; fi
    if [ -n "$fp" ]; then
        _abf_canon "$fp"; fpc="$REPLY"
        _abf_phys_path "$fpc" && fpp="$REPLY"
    fi
    while IFS= read -r r; do
        [ -n "$r" ] || continue
        _abf_canon "$r"; rc="$REPLY"
        _abf_text_has "$text" "$rc" && return 0
        _abf_under "$icwd" "$rc" && return 0
        # a link in the root's path: the same place under its physical name, and
        # a write whose target resolves into it
        if _abf_phys "$rc"; then
            rp="$REPLY"
            _abf_text_has "$text" "$rp" && return 0
            _abf_under "$icwd" "$rp" && return 0
            _abf_under "$fpc" "$rp" && return 0
            _abf_under "$fpp" "$rp" && return 0
        fi
        _abf_under "$fpc" "$rc" && return 0
        _abf_under "$fpp" "$rc" && return 0
    done <<<"$roots"

    # The plugin's own scripts, by the name a relative call uses.
    if [[ $text == *scripts/* ]]; then
        for f in "$base"/scripts/*.sh "$base"/scripts/*.py "$base"/scripts/utils/*.sh "$base"/scripts/utils/*.py; do
            [ -e "$f" ] || continue
            n="${f#"$base"/}"
            [[ $text == *"$n"* ]] && return 0
        done
    fi

    # 4. the deployment: where the session is, and what the call names
    _abf_find_deployment || return 1
    # A deployment exists, so the plugin has been set up here. If this session's
    # marker could not be written (a state directory that is read-only, missing
    # and not creatable, or whose in-use/ is a file) then "no marker" proves
    # nothing: plugin_intro.sh may well have tried and failed. Unsure: in use.
    _abf_state_ok "$state" || return 0
    local sroot="" runs="" c b
    _abf_read_key "$_ABF_SETTINGS" storage_root
    if [ -n "$REPLY" ]; then _abf_home "$REPLY"; _abf_canon "$REPLY"; sroot="$REPLY"; fi
    if [ -n "${LAB_RUNS_DIR:-}" ]; then _abf_canon "$LAB_RUNS_DIR"; runs="$REPLY"; fi

    if [[ $input =~ $re_cwd ]]; then cwd="${BASH_REMATCH[1]}"; else cwd="${PWD:-}"; fi
    # a cwd that cannot be read is not evidence of anything: unsure, in use
    [ -n "$cwd" ] || return 0
    _abf_canon "$cwd"; cwd="$REPLY"

    # The bases as named, then as they are physically (a link on either side).
    local bases=() cwds=("$cwd")
    for b in "$_ABF_ROOT" "$sroot" "$runs"; do
        [ -n "$b" ] || continue
        bases+=("$b")
        if _abf_phys "$b"; then bases+=("$REPLY"); fi
    done
    if _abf_phys "$cwd"; then cwds+=("$REPLY"); fi
    for c in "${cwds[@]}"; do
        for b in "${bases[@]}"; do
            _abf_under "$c" "$b" && return 0
        done
    done
    # in-use-path-spellings: `$LAB_RUNS_DIR` names this deployment's run area -
    # the value this hook sees, or when it has none, the deployment's own
    # storage_root (settings.sh exports one as the other). Any other
    # `${LAB_RUNS_DIR...}` form (a default, a trim) names it as well.
    if [[ $text == *LAB_RUNS_DIR* ]]; then
        local lrd="${runs:-$sroot}"
        if [ -n "$lrd" ]; then
            text="${text//\$\{LAB_RUNS_DIR\}/$lrd}"; text="${text//\$LAB_RUNS_DIR/$lrd}"
            text="${text//\$env:LAB_RUNS_DIR/$lrd}"; text="${text//%LAB_RUNS_DIR%/$lrd}"
            [[ $text == *'${LAB_RUNS_DIR'* ]] && return 0
        fi
    fi
    for b in "${bases[@]}"; do
        _abf_text_has "$text" "$b" && return 0
    done
    # in-use-path-spellings: a relative path from the session's folder - one
    # above storage_root (`runs3/p/results`, `cd runs3/p`) or beside it
    # (`../runs3/p/results`). String work only, no process.
    for c in "${cwds[@]}"; do
        for b in "${bases[@]}"; do
            _abf_rel "$c" "$b"
            _abf_text_has_rel "$text" "$REPLY" && return 0
        done
    done
    # A `cd` with no destination (or to ~ / $HOME) starts a relative walk from
    # home, so `cd && cd runs3 && ...` names no root as written (#53). When a
    # root lives at or under home, such a walk may end in it: in use. Only a
    # question that matters for a command a gate would judge anyway.
    # `cd` as a word of its own (after a separator, a blank or a `~`), then
    # nothing, `~` or the home path, then a separator or the end. Two regexes,
    # not the global replacements this used to make: those were quadratic on a
    # big text (#62).
    if [ -n "$h" ] && [ "$h" != / ] && [[ $text == *cd* ]]; then
        local re_cd='(^|[[:space:];&|"()~])cd[[:space:]]*(~[[:space:]]*)?([;&|"()]|$)'
        local re_cdh='(^|[[:space:];&|"()~])cd[[:space:]]+' re_end='[[:space:]]*([;&|"()]|$)'
        if [[ $text =~ $re_cd ]] || [[ $text =~ $re_cdh"$h"$re_end ]]; then
            for b in "${bases[@]}"; do
                _abf_under "$b" "$h" && return 0
            done
        fi
    fi
    return 1
}
