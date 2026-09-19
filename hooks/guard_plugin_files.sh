#!/bin/bash
# PreToolUse/Write|Edit|MultiEdit|NotebookEdit and PreToolUse on every shell
# tool (Bash, PowerShell, and anything shell-named - hooks.json): an
# installed plugin copy is not edited in place.
#
# 2.8's off-design procedure (skills/operational/SKILL.md, "Off-design: when
# nothing here covers it") tells the model it may "try to fix this step" when
# something is not designed for. Left unbounded, "fix" can mean editing the
# plugin's own installed files under ${CLAUDE_PLUGIN_ROOT} - a copy nobody
# else's session reads, silently discarded the next time the plugin is
# installed or updated, and never seen by whoever could actually change the
# plugin. A gap the model "fixed" this way looks solved and never gets
# reported, which is worse than the gap on its own. This hook makes that
# specific edit refuse instead, on every account - see below for why no
# identity check is needed.
#
# No identity check: the maintainer's own edits belong in a REPO CHECKOUT,
# never in a copy the plugin marketplace/install machinery placed under
# CLAUDE_PLUGIN_ROOT. A checkout is a different path, so it is never caught by
# the comparison below - nothing here has to ask who is running.
#
# Fail closed when `jq` itself is missing (PITFALLS 28), the same way as
# confirm_cleanup.sh, confirm_launch.sh and confirm_walkthrough.sh beside it -
# and for the identical reason: with no jq, every `jq -r` below would silently
# read back "", every path/command would look unrelated to the plugin root,
# and this guard would vanish with nothing printed at exactly the moment a
# gate was needed. Exit 2, not the `deny` JSON deny() builds: deny() is
# itself a `jq -n` call, so leaning on jq to report jq's own absence fails the
# same way it is trying to fix.
#
# Deliberately NOT sourcing scripts/utils/portable.sh, matching its two
# siblings: a gate that silently vanishes because a helper failed to load is
# worse than a gate that was never written. The few lines this needs (a
# physical-path resolve, an existing-parent walk) are inlined below instead.
#
# The Bash half is BEST EFFORT ONLY and does not claim to be complete. It
# looks for the plugin root's path together with a write-shaped verb in the
# same command string - it cannot parse shell, so it can both miss a real
# write (hidden behind a variable, an alias, a wrapper script) and flag a
# command that never touches the root at all (the root path appears only in
# an unrelated argument or a comment). Treat it as a speed bump, not a
# sandbox: the Write/Edit/MultiEdit/NotebookEdit half above is the real gate,
# because those tools always carry a structured path.
#
# T2: "flag a command that never touches the root" was not hypothetical -
# `grep -n foo $CLAUDE_PLUGIN_ROOT/hooks/x.sh > /tmp/scratch/out` is a
# read-only search whose output happens to go to scratch space, and it was
# denied outright, because the old check asked only "does the root appear
# anywhere on this line" and "does a bare '>' appear anywhere on this line" -
# two questions with no requirement that the '>' be writing to the root
# rather than merely coexisting with a mention of it. The Bash branch below
# now asks a narrower question for a redirect - does ITS OWN target resolve
# under the root - and a segment-scoped one for a write verb, so a
# read reported through a redirect elsewhere, or a write verb in an unrelated
# ';'-joined command, no longer trips this guard.
set -uo pipefail

# `command -v jq` only proves a FILE exists. A jq that cannot run - wrong
# architecture, a missing shared library, a Windows jq.exe a Git Bash PATH
# finds but cannot execute - passes that check and then fails every parse
# below, which is the exact silent-gate failure this guard exists to stop.
# So ask jq to do its job on the smallest possible input, same as its three
# siblings - but only once there is a plugin root to guard at all (below).
#
# Without jq this used to refuse EVERY call (issue #15): on a Windows machine
# with no jq, a bare `ls` was blocked, the session moved to PowerShell, and
# no guard fired at all from then on. What this hook protects is the
# installed plugin's own directory, and a call that never names that
# directory cannot write into it - so the no-jq path looks for the root in
# the raw bytes and refuses only when it is there. Scoped, not silent.
jq_works() { printf '{}' | jq -e . >/dev/null 2>&1; }
refuse_without_jq() {
    cat >&2 <<'EOF'
BLOCKED: jq is missing or cannot run here, so hooks/guard_plugin_files.sh cannot read
exactly what this call targets - and this call names the installed plugin's own
directory, which is the one thing this hook exists to protect. Calls that do not
name it are let through; this one is not. (confirm_cleanup.sh, confirm_launch.sh
and confirm_walkthrough.sh scope themselves the same way.)

Install it yourself (this hook will not attempt to), then retry:
  macOS:       brew install jq
  Debian/WSL:  sudo apt install jq
  Windows:     winget install jqlang.jq
EOF
    exit 2
}

# Nothing to guard when this session has no plugin root at all - a repo
# checkout run directly, or a harness that never set the variable. Checked
# BEFORE the jq probe, deliberately: requiring jq just to conclude "there is
# nothing to check here" would fail closed for a reason that has nothing to
# do with what this hook actually protects.
ROOT_RAW="${CLAUDE_PLUGIN_ROOT:-}"
[ -n "$ROOT_RAW" ] || exit 0

# Resolve the root PHYSICALLY: a symlinked install (or a symlinked ancestor
# of one) must not let a write through just because the string on disk
# differs from ${CLAUDE_PLUGIN_ROOT}. If the root itself cannot be resolved -
# stale variable, deleted directory - there is nothing real to guard either.
ROOT="$(cd -P -- "$ROOT_RAW" 2>/dev/null && pwd -P)" || exit 0
[ -n "$ROOT" ] || exit 0

# Every spelling a command can use for the root, not only the two above. The
# Windows verification run (2.15.0) deleted a file under the root with
# `Remove-Item ~/agentic-bioflow_v2/hooks/...`: the hook ran, found neither
# literal spelling, and allowed it - and `$HOME/...`, `cd <root> && rm x` and
# `$CLAUDE_PLUGIN_ROOT/...` slipped through the same way on Linux. An
# installed root lives under ~/.claude/plugins/cache, so `~` is the spelling
# a model reaches for first. Windows adds drive forms (C:\ C:/ /c/ /mnt/c/)
# and compares case-insensitively, as its filesystem does.
root_spellings() {
    local p base rest d h hp
    printf '%s\n' "$ROOT_RAW" "$ROOT" '$CLAUDE_PLUGIN_ROOT' '${CLAUDE_PLUGIN_ROOT}' \
        '$env:CLAUDE_PLUGIN_ROOT' '%CLAUDE_PLUGIN_ROOT%'
    h="${HOME:-}"; hp=""
    [ -n "$h" ] && hp=$(cd -P -- "$h" 2>/dev/null && pwd -P)
    for p in "$ROOT_RAW" "$ROOT"; do
        for base in "$h" "$hp"; do
            [ -n "$base" ] || continue
            case "$p" in "$base"/*)
                rest="${p#"$base"/}"
                printf '%s\n' "~/$rest" "\$HOME/$rest" "\${HOME}/$rest" \
                    "\$env:USERPROFILE/$rest" "%USERPROFILE%/$rest" ;;
            esac
        done
        case "$p" in
            /[a-zA-Z]/*)
                d="${p:1:1}"; rest="${p:3}"
                printf '%s\n' "$d:/$rest" "/mnt/$d/$rest" "/cygdrive/$d/$rest" ;;
            [a-zA-Z]:[\\/]*)
                d="${p:0:1}"; rest="${p:3}"; rest="${rest//\\//}"
                printf '%s\n' "$d:/$rest" "/$d/$rest" "/mnt/$d/$rest" ;;
        esac
    done
}
SPELLINGS=$(root_spellings | while IFS= read -r s; do
    [ -n "$s" ] || continue
    printf '%s\n' "$s"
    case "$s" in */*)
        b="${s//\//\\}"
        # both as a shell sees it and as it sits JSON-escaped in raw input
        printf '%s\n' "$b" "${b//\\/\\\\}" ;;
    esac
done | sort -u)
case "$ROOT_RAW$ROOT" in [a-zA-Z]:*|/[a-zA-Z]/*) shopt -s nocasematch ;; esac
case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) shopt -s nocasematch ;; esac

root_in() { # root_in <text> - any spelling of the root, as a literal substring
    local s
    while IFS= read -r s; do
        [[ -n "$s" && "$1" == *"$s"* ]] && return 0
    done <<<"$SPELLINGS"
    return 1
}

INPUT=$(cat)
if ! jq_works; then
    root_in "$INPUT" && refuse_without_jq
    exit 0
fi
TOOL=$(jq -r '.tool_name // ""' <<<"$INPUT" 2>/dev/null)

deny() {
    jq -n --arg m "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse",
        permissionDecision: "deny", permissionDecisionReason: $m}}'
    exit 0
}

REASON_TAIL="If this is a real gap in the plugin, follow the off-design procedure in
\`skills/operational/SKILL.md\` (section \"Off-design: when nothing here
covers it\") and report it there - do not edit the installed copy to work
around it. Maintainers change the plugin in their own repo checkout, never in
an installed copy."

# Walk up to the nearest EXISTING parent, physically resolved. Write/Edit
# target a file that may not exist yet (Write creates it), so resolving the
# file itself would fail every time for the one tool this exists to catch.
# Bounded for free: dirname strictly shortens an absolute path until it hits
# "/", and a relative path bottoms out at "." - the current directory, which
# always exists - so this always terminates.
resolve_existing_parent() {
    local d="$1"
    while [ -n "$d" ] && [ "$d" != "/" ] && [ ! -d "$d" ]; do
        d=$(dirname -- "$d")
    done
    [ -d "$d" ] || d="/"
    (cd -P -- "$d" 2>/dev/null && pwd -P)
}

case "$TOOL" in
Write | Edit | MultiEdit | NotebookEdit)
    # notebook_path for NotebookEdit, file_path for the other three - the
    # same fallback confirm_walkthrough.sh uses beside this file.
    FILE=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' <<<"$INPUT" 2>/dev/null)
    [ -n "$FILE" ] || exit 0

    DIR=$(dirname -- "$FILE")
    RDIR=$(resolve_existing_parent "$DIR")
    [ -n "$RDIR" ] || exit 0

    case "$RDIR" in
    "$ROOT" | "$ROOT"/*)
        deny "BLOCKED: this path resolves inside the installed plugin (\$CLAUDE_PLUGIN_ROOT), which
is not edited in place. A plugin install is a deployed copy, not a checkout -
edits made here are overwritten by the next install or update and are never
seen by anyone else who has this plugin installed.

Target: ${FILE}
Resolves under: ${RDIR}

${REASON_TAIL}"
        ;;
    esac
    exit 0
    ;;
Bash | *[Ss]hell* | *[Pp]wsh* | *[Tt]erminal* | *[Cc]md* | *[Ee]xec*)
    # Any shell tool, not only Bash (issue #15): once Bash was blocked,
    # PowerShell was the natural fallback and this guard never saw it. The
    # same input fields the three confirm_* hooks try, in the same order.
    CMD=$(jq -r '.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // ""' <<<"$INPUT" 2>/dev/null)
    if [ -z "$CMD" ]; then
        [ "$TOOL" = Bash ] && exit 0
        # A shell tool whose input shape this hook does not know. Judge the
        # raw payload instead - but only refuse when it names the root AND
        # carries a write verb; naming the plugin to read it stays allowed.
        root_in "$INPUT" || exit 0
        if grep -qiE '(sed[[:space:]]+-i|tee|cp|mv|rm|rmdir|chmod|chown|patch|ln|truncate|install|set-content|add-content|out-file|remove-item|copy-item|move-item|new-item|rename-item|del|erase|copy|move|ren)([^a-z-]|$)|>' <<<"$INPUT"; then
            deny "BLOCKED: this call came from a shell tool ('${TOOL:-<unnamed>}') whose input this hook cannot read, and its raw text names the installed plugin's location next to something write-shaped. The installed plugin is not edited in place.

${REASON_TAIL}"
        fi
        exit 0
    fi

    # Any spelling of the root (SPELLINGS, above), as a literal substring - a
    # path is not a regex, and one that happens to contain '.', '+', '['
    # must not be read as one.
    root_in "$CMD" || exit 0

    # T2: "the plugin root is mentioned somewhere" and "this command writes
    # into it" are different claims, and the old check conflated them -
    # `grep -n foo $ROOT/hooks/x.sh > /tmp/scratch/out` names the root only
    # as what it READS, and was denied anyway because a bare '>' also
    # appeared on the same line. A redirect writes exactly one place: the
    # token right after '>'/'>>', never wherever else the root happened to
    # be named. So the root check below is bound to that token alone, not to
    # the command as a whole - measured against the report, this is the
    # fix.
    #
    # A write VERB (cp, mv, rm, ...) does not offer one fixed argument
    # position the way a redirect does - `cp SRC DEST` and `rm A B C` both
    # take the root in different slots depending on intent - so those stay
    # bound to their own SEGMENT rather than one argument: still narrower
    # than the old whole-line check (a command word doubled up with the root
    # by a completely unrelated ';'-joined command is worth splitting apart),
    # without inventing a per-verb argument model this guard does not have.
    CMD_NR=$(sed -E 's/[0-9]*>&?[[:space:]]*\/dev\/null//g' <<<"$CMD")
    SEGMENTS=$(printf '%s\n' "$CMD_NR" | sed -E 's/(\|\||&&|[;&|])/\n/g')

    WRITE_RE='(^|[[:space:]]|[;&|(])(sudo[[:space:]]+)?(sed[[:space:]]+-i|tee|cp|mv|rm|rmdir|chmod|chown|patch|ln|truncate|install)([[:space:]]|$)'
    # PowerShell and cmd.exe spell the same writes differently, and
    # PowerShell does not care about case. Matched on their own, -i.
    PS_WRITE_RE='(^|[[:space:]]|[;&|(])(set-content|add-content|out-file|remove-item|copy-item|move-item|new-item|rename-item|del|erase|copy|move|ren)([[:space:]]|$)'

    # `cd <root> && rm hooks/x.sh` names the root only in the cd, and the
    # write that follows uses a relative path. Once a segment moves INTO the
    # root, every later segment is treated as running there.
    CD_RE='^[[:space:]]*(cd|pushd|set-location|push-location|sl)([[:space:]]|$)'

    HITVERB=0
    INROOT=0
    while IFS= read -r SEG; do
        [ -n "$SEG" ] || continue

        if grep -qiE "$CD_RE" <<<"$SEG" 2>/dev/null; then
            root_in "$SEG" && INROOT=1
            continue
        fi

        # A write verb owns its whole segment; the root has to appear
        # SOMEWHERE in that same segment, not merely on the same line -
        # unless an earlier segment already cd'd into it.
        if { grep -qE "$WRITE_RE" <<<"$SEG" || grep -qiE "$PS_WRITE_RE" <<<"$SEG"; } 2>/dev/null \
            && { [ "$INROOT" = 1 ] || root_in "$SEG"; }; then
            HITVERB=1
        fi

        # A redirect owns only its own target. Take the LAST '>'/'>>' on the
        # segment (a `cmd 2>&1 >file`-shaped line still has one real stdout
        # destination, the rightmost one) and the single token that follows
        # it, and judge the root against that token alone.
        if grep -qE '>[[:space:]]*' <<<"$SEG" 2>/dev/null; then
            RTARGET=$(printf '%s\n' "$SEG" \
                | grep -oE '>>?[[:space:]]*[^[:space:];&|]+' | tail -1 \
                | sed -E 's/^>>?[[:space:]]*//')
            [ -n "$RTARGET" ] && root_in "$RTARGET" && HITVERB=1
            # After a cd into the root, a relative target lands inside it; an
            # absolute one (a scratchpad, /tmp) still does not.
            if [ "$INROOT" = 1 ] && [ -n "$RTARGET" ]; then
                case "$RTARGET" in
                    /*|~*|\$*|[a-zA-Z]:*|%*) ;;
                    *) HITVERB=1 ;;
                esac
            fi
        fi
    done <<< "$SEGMENTS"

    if [ "$HITVERB" = 1 ]; then
        deny "BLOCKED: this command names the installed plugin's location and also looks like
a write into it. The installed plugin is not edited in place - see the header
of hooks/guard_plugin_files.sh for what this half of the guard can and
cannot catch; it is best-effort pattern matching, not a sandbox.

Command: ${CMD}

${REASON_TAIL}"
    fi
    exit 0
    ;;
*)
    exit 0
    ;;
esac
