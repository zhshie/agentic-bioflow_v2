#!/bin/bash
# PreToolUse/Write|Edit|MultiEdit|NotebookEdit and PreToolUse/Bash: an
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
check_jq() {
    if ! printf '{}' | jq -e . >/dev/null 2>&1; then
        cat >&2 <<'EOF'
BLOCKED: jq is missing or cannot run here, so hooks/guard_plugin_files.sh cannot read
what this action targets - and cannot tell an edit to the installed plugin
from an ordinary project edit. Rather than silently stop checking (the old,
dangerous behaviour this repo has already been bitten by once - PITFALLS 28),
it refuses every gated action until jq exists. The same is true of
confirm_cleanup.sh, confirm_launch.sh and confirm_walkthrough.sh, which share
this requirement.

Install it yourself (this hook will not attempt to), then retry:
  macOS:       brew install jq
  Debian/WSL:  sudo apt install jq
  Windows:     winget install jqlang.jq
EOF
        exit 2
    fi
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

check_jq

INPUT=$(cat)
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
Bash)
    CMD=$(jq -r '.tool_input.command // ""' <<<"$INPUT" 2>/dev/null)
    [ -n "$CMD" ] || exit 0

    # The root's path, either spelling: the literal (possibly still an
    # unexpanded env-var reference the shell would resolve at run time) and
    # the physical one resolved above. Fixed-string match - a path is not a
    # regex, and one that happens to contain '.', '+', '[' must not be read
    # as one.
    HITROOT=0
    if grep -qF -- "$ROOT_RAW" <<<"$CMD" 2>/dev/null; then HITROOT=1; fi
    if [ "$ROOT" != "$ROOT_RAW" ] && grep -qF -- "$ROOT" <<<"$CMD" 2>/dev/null; then HITROOT=1; fi
    [ "$HITROOT" = 1 ] || exit 0

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

    root_in() { # root_in <text> - either spelling of the root, fixed-string
        grep -qF -- "$ROOT_RAW" <<<"$1" 2>/dev/null && return 0
        [ "$ROOT" != "$ROOT_RAW" ] && grep -qF -- "$ROOT" <<<"$1" 2>/dev/null && return 0
        return 1
    }

    HITVERB=0
    while IFS= read -r SEG; do
        [ -n "$SEG" ] || continue

        # A write verb owns its whole segment; the root has to appear
        # SOMEWHERE in that same segment, not merely on the same line.
        if grep -qE "$WRITE_RE" <<<"$SEG" 2>/dev/null && root_in "$SEG"; then
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
