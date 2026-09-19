#!/bin/bash
# PreToolUse/Bash: the execution gate for v2.
#
# v1 gated `nextflow run` and consulted a .cli_task.json phase machine to decide
# whether to prompt. v2 has no state machine - Seqera Platform is the only
# source of truth for run state - so this gate does two things instead:
#
#   1. Requires an explicit confirmation before anything that can start a run.
#   2. Reports the preconditions that silently ruin a launch here, while the
#      command is still on screen, rather than 20 minutes into a stalled run.
#
# It never denies a launch it can actually see. It DOES refuse - the one
# exception to the line above - when `jq` itself is missing, deliberately
# fail-closed (PITFALLS 28). Before this check existed, no `jq` meant every
# `jq -r` below silently produced an empty string: CMD came back "", every
# judgement after it went the harmless way, and the whole gate vanished with
# nothing printed. A freshly installed WSL Ubuntu has no `jq`, and neither did
# macOS before 15, so this was not a corner case.
#
# R2 (2.9): a launch-shaped command now ALSO returns
# hookSpecificOutput.permissionDecision: "ask", with permissionDecisionReason
# carrying the full command plus any unmet preconditions - so Claude Code
# itself pauses for the user's explicit confirmation, rather than the model
# merely being asked (in prose, in additionalContext) to wait for one. This is
# still never a denial: "ask" only pauses, which is exactly what the safety
# net has always required here, so no existing "allow" path becomes "deny".
#
# Both the structural `ask` and the prose `additionalContext` are sent
# together - belt and braces - because `ask`'s behaviour under
# `bypassPermissions` and `acceptEdits` is UNDOCUMENTED. Confirmed against
# Claude Code's own docs while planning 2.9
# (~/.claude/plans/curious-doodling-lightning.md, appendix 2, "兩項文件沒回答，
# 要實測": `ask` in bypassPermissions/acceptEdits has no documented behaviour).
# If Claude Code ever treats "ask" as "allow" in one of those modes, the prose
# gate is what is left standing - it is not a fallback added out of caution,
# it is the only thing this file can still prove works there.
#
# D3 (2.13): this file also asks - the same way, through the same `ask()`
# below - when the command is NOT a launch but reaches the site directly over
# ssh/scp/rsync/sftp on MSYS, bypassing scripts/on_site.sh. That branch lives
# here rather than as a fifth PreToolUse hook so it costs nothing beyond a
# `uname -s` on every OTHER platform and every non-transport command on this
# one - a second hook process would add its own startup latency to every
# single Bash call this plugin's users make, launch-shaped or not.
#
# T1 (2.15, Fixes #15): two more ways this gate used to go blind, found from
# the same GitHub issue - a Windows member gave up on this plugin's safety
# net entirely and started typing commands in a plain PowerShell window
# instead, which has none of it. Both were the SAME shape as PITFALLS 28: a
# precondition this file could not verify was treated as "block everything",
# rather than "block what this cannot rule out" - and unbounded fail-closed
# is what sent that member around the net rather than through it.
#
#   1. jq missing/broken used to refuse every single Bash command, forever,
#      with no way to keep working while waiting for an install. It now asks
#      a much smaller question with nothing but a shell `case` (no jq, no
#      grep -E - one more binary that could be the very thing missing on a
#      machine that has none) against the RAW bytes this hook received: does
#      the text contain anything that reads like `tw launch` / `tw runs
#      relaunch` / `sbatch` / `nextflow run`, or a direct ssh/scp/rsync/sftp
#      call. A command that could not plausibly be one of those is let
#      through exactly as it would be with jq present and nothing matching -
#      silently, not a single line of noise - and only a genuine match still
#      blocks, with the fix (install jq) named in the message.
#   2. hooks.json's matcher used to be "Bash" only. It now covers other
#      execution-shaped tool names too (a PowerShell-flavoured MCP tool among
#      them) - which does nothing by itself unless this file can also read
#      what such a tool was asked to run. `tool_input.command` is a Bash-ism;
#      other tools spell the same idea `script`, `cmd`, `commandLine`,
#      `input` or `powershell`, so those are tried too before giving up. When
#      none of them holds anything, that is not "nothing to check" - it is
#      "this file does not know how to read this tool's shape" - and the
#      same scoped text scan from (1) runs against the raw payload rather
#      than silently waving the call through.
#
# Neither of these is a new kind of leniency: a command this file COULD read
# is judged exactly as precisely as before, by is_launch_command() and D3's
# transport check further down. Only the two "I cannot tell" cases changed,
# from total refusal to a scoped one.
# Shell separators AND the JSON punctuation around them folded to spaces -
# this runs against either a shell command line or a raw, still-quoted JSON
# payload (the whole hook input, when even .tool_name cannot be trusted), and
# a bare `tr -s ';&|()<>'` leaves `"tw launch` as one token (the opening
# quote glued to the word) which no `*' tw launch '*` pattern below can ever
# match. Folding quotes, braces, brackets, commas, colons and `=` too turns
# either shape into the same flat token soup.
LOOKS_SHAPED_SEP=$'\t\n\r;&|()<>"\'{}[],:='
looks_launch_shaped() {
    local text=" $(printf '%s' "$1" | tr -s "$LOOKS_SHAPED_SEP" ' ') "
    case "$text" in
        *' tw launch '*|*' tw runs relaunch '*|*' sbatch '*|*' nextflow run '*|*' ssh '*|*' scp '*|*' rsync '*|*' sftp '*)
            return 0 ;;
        # Identity and shared-process changes (the gate after the jq parse
        # below). Without jq the value being replaced cannot be compared, so
        # any change to these keys counts.
        *'agent_ctl.sh start '*|*'agent_ctl.sh stop '*|*'agent_ctl.sh restart '*|*'egress_ctl.sh start '*|*'egress_ctl.sh stop '*|*'egress_ctl.sh restart '*|*'--set agent_connection '*)
            return 0 ;;
    esac
    return 1
}

if ! printf '{}' | jq -e . >/dev/null 2>&1; then
    RAW=$(cat)
    if looks_launch_shaped "$RAW"; then
        cat >&2 <<'EOF'
BLOCKED: jq is missing or cannot run here, so hooks/confirm_launch.sh cannot read what
this command is precisely - and the raw text of this one matches a launch- or
site-transport-shaped pattern (tw launch / tw runs relaunch / sbatch / nextflow
run / ssh / scp / rsync / sftp), so it is refused rather than guessed at. A
command that matches none of those patterns is let through unchanged - this is
a narrower refusal than before, not a blanket one, but it still cannot see a
launch hidden behind a variable or an alias the way the real check can.
confirm_cleanup.sh and confirm_walkthrough.sh apply the same scoped rule.

Install jq to get the full check back (this hook will not attempt to), then retry:
  macOS:       brew install jq
  Debian/WSL:  sudo apt install jq
  Windows:     winget install jqlang.jq
EOF
        exit 2
    fi
    exit 0
fi

INPUT=$(cat)
TOOL=$(jq -r '.tool_name // ""' <<<"$INPUT" 2>/dev/null)
# Bash-first, then the other spellings a non-Bash execution tool might use
# for the same idea. A tool this list does not cover yet is exactly the case
# handled below, not a case this line needs to anticipate by name.
CMD=$(jq -r '.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // ""' <<<"$INPUT" 2>/dev/null)

# "Does this string start a run" is a judgement several hooks need to reach
# identically, so it lives in one sourced file instead of being restated here.
# Sourced relative to $0 the same way strip_heredocs.awk is, so a direct
# `bash hooks/confirm_launch.sh` from a test still finds it.
#
# It is loaded fail-CLOSED, unlike strip_heredocs.awk beside it. That awk fails
# safe by construction: if it dies, STRIPPED is empty, CMD keeps its original
# value, and the judgement below still happens. A missing launch_trigger.sh
# fails the other way - `is_launch_command` becomes command-not-found, 127 is
# non-zero, and `|| exit 0` waves through every command including a real launch.
# The gate would be gone with nothing on screen to say so, which is precisely
# the failure this file exists to prevent. So when the helper cannot be loaded,
# every command is treated as one that might start a run. That is noisy, and
# noisy is the correct behaviour for a safety net that has stopped being able
# to judge.
if ! . "$(dirname "$0")/launch_trigger.sh" 2>/dev/null \
   || ! declare -F is_launch_command >/dev/null 2>&1; then
    jq -n --arg m "GATE NOT WORKING: hooks/launch_trigger.sh could not be loaded, so this command was NOT checked and no other command will be either.

Reinstall or repair the plugin. Until then the launch gate is absent: treat anything that can start a run - tw launch, tw runs relaunch, sbatch, nextflow run - as ungated, and confirm it with the user by hand." \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $m}}'
    exit 0
fi

# The one JSON builder this file has for a structural pause: R2's launch ask
# below and D3's transport ask further down both end here, rather than each
# carrying its own `jq -n` call that could drift out of sync with the other.
ask() { # ask <additionalContext message> <permissionDecisionReason>
    jq -n --arg m "$1" --arg r "$2" \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $r, additionalContext: $m}}'
    exit 0
}

# T1, part 2: jq is fine, but this call's own tool ('$TOOL') did not carry
# its command under any field name this file knows to check. For Bash that
# never happens in practice; for anything else it means the tool's shape is
# one this file cannot parse - not that there is nothing here worth judging.
# jq DOES work in this branch, so this gets the real `ask()` (a structural
# pause), not the bare exit-2 the no-jq path above is limited to.
if [ "$TOOL" != "Bash" ] && [ -z "$CMD" ]; then
    if looks_launch_shaped "$INPUT"; then
        ask "GATE: this call came from a tool ('${TOOL:-<unnamed>}') whose input this hook does not parse - checked tool_input.command/script/cmd/commandLine/powershell/input, all empty - and the raw payload matches a launch- or site-transport-shaped pattern. Show the user the full call and wait for explicit confirmation before it runs; this hook cannot verify it the way it verifies a Bash launch." \
            "Unreadable tool input from '${TOOL:-<unnamed>}' that looks launch-shaped:

$INPUT"
    fi
    exit 0
fi

# Who the site thinks you are, and what runs on its shared login node.
#
# 2.15.0 Windows verification: `tw launch` failed with "No Tower Agent is
# online". The model then set agent_connection to a different credential's
# connection id - one belonging to a shared lab credential, not this member's -
# and started an agent under it on the login node, and asked nobody.
# docs/SETTINGS.md already said agent_connection "must be unique" and that two
# members sharing one are refused permanently; prose in a doc did not stop it.
# A structural ask does: the harness stops and the user answers, not the model.
#
# Settings: asked only when an identity key already has a value and the
# command would change it. First-time setup fills them from empty many times
# and should not ask each time; a change to an existing identity is the thing
# to catch. A value this cannot read back from the command also asks.
IDENTITY_KEYS='agent_connection|seqera_user|workspace_id|compute_env|site_host|slurm_account|storage_root'
RESIDENT_RE='(^|[^[:alnum:]_])(agent_ctl|egress_ctl)\.sh[[:space:]]+(start|stop|restart)([^[:alnum:]_-]|$)'
if grep -qE "$RESIDENT_RE" <<<"$CMD" 2>/dev/null; then
    ask "GATE: this starts, stops or restarts a resident process (the Tower Agent or the egress relay) on the site's SHARED login node. Before running it, tell the user which process, under which identity (agent_connection / credential) and why, and wait for their explicit yes. Never start one under an agent_connection that is not this member's own - docs/SETTINGS.md: two members sharing one are refused permanently." \
        "$CMD

Starts/stops a resident process on the shared login node."
fi
ID_HITS=$(grep -oE "(settings\.sh[[:space:]]+--set|set_setting)[[:space:]]+($IDENTITY_KEYS)[[:space:]]+[^;&|]*" <<<"$CMD" 2>/dev/null)
if [ -n "$ID_HITS" ]; then
    HERE_S="$(cd "$(dirname "$0")/.." && pwd)/scripts/settings.sh"
    while IFS= read -r hit; do
        [ -n "$hit" ] || continue
        key=$(sed -E "s/^(settings\.sh[[:space:]]+--set|set_setting)[[:space:]]+([a-z_]+).*/\2/" <<<"$hit")
        new=$(sed -E "s/^(settings\.sh[[:space:]]+--set|set_setting)[[:space:]]+[a-z_]+[[:space:]]+//; s/[[:space:]]+$//; s/^[\"']//; s/[\"']$//" <<<"$hit")
        old=$(bash "$HERE_S" "$key" "" 2>/dev/null </dev/null)
        [ -z "$old" ] && continue
        [ "$new" = "$old" ] && continue
        ask "GATE: this changes '$key', which decides whose identity or resources the site uses, from an existing value to a different one. Show the user the old value, the new value and where the new one came from (whose credential / compute environment it is), and wait for their explicit yes. Never adopt a value that belongs to another member or to a shared lab credential - for agent_connection, docs/SETTINGS.md: two members sharing one are refused permanently." \
            "$CMD

Changes $key:
  from: $old
  to:   $new"
    done <<<"$ID_HITS"
fi

if ! is_launch_command "$CMD"; then
    # D3 (2.13): a command that reaches the site directly - ssh/scp/rsync/sftp,
    # not routed through scripts/on_site.sh - asks instead of running silently,
    # but ONLY on MSYS (Git Bash). Everywhere else this plugin already runs,
    # the local ssh binary holds a multiplexed master fine (this deployment's
    # own login-node and macOS sessions do it every day); asking there would
    # be noise with nothing wrong to report. MSYS is different and measured,
    # not assumed: this shell's own ssh cannot carry a session over its master
    # (PITFALLS 16b - the control socket comes up, fd-passing does not), so
    # every direct call like this one falls back to a fresh login, and a fresh
    # login here means a one-time code on the user's phone that this agent
    # cannot read. scripts/on_site.sh is the only sanctioned route to the site
    # from any shell (docs/SITE_ADAPTER.md contract 6) - on MSYS specifically
    # it is also the only one that can borrow WSL's ssh for the multiplexed
    # part (PITFALLS 16g), which a bare `ssh` typed here does not do.
    #
    # Reuses is_launch_command's own here-doc stripper and its
    # LAUNCH_NESTED_SHELL_RE (already sourced above, not restated): a payload
    # ssh/on_site.sh hands to a far shell is not quoted DATA the way a string
    # inside `grep "ssh"` is, so the same exception that protects launch
    # detection from `bash -c "tw launch ..."` also keeps this branch from
    # missing `ssh host '...'` while still ignoring `grep -rn "ssh" docs/`.
    case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*)
        TCMD_NB=$(printf '%s\n' "$CMD" | awk -f "$(dirname "$0")/strip_heredocs.awk" 2>/dev/null)
        [ -n "$TCMD_NB" ] || TCMD_NB="$CMD"
        if grep -qE "$LAUNCH_NESTED_SHELL_RE" <<<"$TCMD_NB"; then
            TCMD_NQ="$TCMD_NB"
        else
            TCMD_NQ=$(sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g" <<<"$TCMD_NB")
        fi
        TRANSPORT_RE='(^|[[:space:]]|[;&|(])(sudo[[:space:]]+)?([^[:space:]]*/)?(ssh|scp|rsync|sftp)([[:space:]]|$)'
        ONSITE_RE='(^|[[:space:]]|[;&|(])([^[:space:]]*/)?on_site\.sh([[:space:]]|$)'
        TSEG=""
        while IFS= read -r TSEG; do
            echo "$TSEG" | grep -qE "$ONSITE_RE" && continue
            if echo "$TSEG" | grep -qE "$TRANSPORT_RE"; then
                ask "GATE: this command reaches the site directly over ssh/scp/rsync/sftp, bypassing scripts/on_site.sh. In this shell (Git Bash/MSYS) a direct ssh connection cannot hold a multiplexed master - the control socket comes up but fd-passing to a real session fails (PITFALLS 16b) - so a call like this one falls back to a full login: a one-time code on the user's phone that this agent cannot read. scripts/on_site.sh is the only sanctioned route to the site from here (docs/SITE_ADAPTER.md contract 6); it also knows how to borrow WSL's own ssh for the multiplexed part (PITFALLS 16g), which this bare call does not. Show the user the command and route it through scripts/on_site.sh instead, or let them run it themselves." \
                    "$CMD

This shell's own ssh cannot multiplex (PITFALLS 16b): every direct call like this one costs a fresh one-time code on the user's phone, which this agent cannot read. scripts/on_site.sh is the only sanctioned route to the site from here (docs/SITE_ADAPTER.md contract 6)."
            fi
        done <<< "$(echo "$TCMD_NQ" | sed -E 's/(\|\||&&|[;&|])/\n/g')"
        ;;
    esac
    exit 0
fi

WARN=""
add() { WARN="${WARN}
  - $1"; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"

# Z2: whether an unset LAB_RUNS_DIR is a FAULT depends on `reach`. v2.6 settled
# that under `ssh`/`none` this variable must NOT be set in the user's own
# shell - the site is a different machine entirely - so under those two
# reaches this warning used to fire on every single launch command,
# unconditionally, reporting as broken a thing that was working exactly as
# designed. A warning that always fires teaches the reader to skip the whole
# section (the same argument every other message in this file already makes).
#
# Reading `reach` means reading the settings file, which is settings.sh's job
# alone - PITFALLS already recorded that a second copy of that search logic
# drifts out of sync (on_site.sh once carried a hand-written list of another
# script's dependencies, twice gone stale). The "no helper" rule beside this
# file's siblings (confirm_cleanup.sh, confirm_walkthrough.sh) exists to stop
# a gate vanishing SILENTLY the moment a sourced file goes missing. Invoking
# settings.sh as a SUBPROCESS rather than sourcing it sidesteps that risk a
# different way: if the call fails for any reason at all - settings.sh
# missing, its own portable.sh missing, no settings file anywhere - the
# command substitution below comes back empty and REACH falls back to
# "local", which is exactly TODAY'S unconditional behaviour and the same
# default settings.sh/on_site.sh already use for this same key. So the worst
# this lookup can do is leave the gate exactly as noisy as it already is; it
# can never make it vanish the way a bare `. helper.sh || true` would. That is
# why this one line is a subprocess call rather than the `.` this repo
# forbids for its two stricter siblings.
#
# Under ssh/none the fix is silence, not a substitute check: on_site.sh can
# answer this, but only at the cost of a round trip that runs up to 31s
# without an already-shared connection (measured) against this hook's own
# 10s timeout - and a PreToolUse hook that times out does not block, it lets
# the tool call through with NOTHING shown, on no predictable schedule. A
# launch command that reliably prints nothing extra is a better outcome than
# one that unpredictably times out trying to be helpful. :launch's own
# background watcher and :runs already cover this once the run actually
# starts.
REACH="$(bash "$HERE/scripts/settings.sh" reach local 2>/dev/null)"
[ -n "$REACH" ] || REACH=local

# Preconditions. Each of these has cost a real run.
#
# Hooks do not always run under a login shell, so an unset LAB_RUNS_DIR means
# "cannot check" - reporting that as "not running" would train the user to
# ignore this section.
if [ -z "${LAB_RUNS_DIR:-}" ]; then
    case "$REACH" in
        ssh|none) ;;   # expected here (v2.6) - not a fault, see above
        *) add "LAB_RUNS_DIR is not set in this shell, so the site's readiness could not be checked" ;;
    esac
else
    bash "$HERE/scripts/egress_ctl.sh" status >/dev/null 2>&1 \
      || add "the site's egress channel is DOWN - container pulls and reference downloads will fail (scripts/egress_ctl.sh start)"

    bash "$HERE/scripts/agent_ctl.sh" status >/dev/null 2>&1 \
      || add "Tower Agent is NOT running - the run may still execute, but Platform will show no outputs (scripts/agent_ctl.sh start)"
fi

# Where a site's egress channel is tied to a specific host, a channel that came
# up elsewhere is useless: the head job reaches back by the address baked into
# the compute environment. The adapter reports this as a WARNING.
if [ -n "${LAB_RUNS_DIR:-}" ] && bash "$HERE/scripts/egress_ctl.sh" status 2>/dev/null | grep -q WARNING; then
    add "the egress channel is up somewhere other than where the compute environment expects it - see scripts/egress_ctl.sh env"
fi

if grep -qE '(^|/)tw[[:space:]]+launch' <<<"$CMD" && ! grep -q -- '--disable-optimization' <<<"$CMD"; then
    add "no --disable-optimization: Platform right-sizes from run history, which fights a site whose accepted sizes are fixed - a helpfully reduced request can land below what the site will take"
fi

# The same check cannot be made of a relaunch: `tw runs relaunch` has no
# --disable-optimization flag at all (`tw runs relaunch --help`), because it
# reuses whatever the original launch stored. Saying nothing would read as
# "checked, and fine", and warning that the flag is absent would send the user
# to a flag that does not exist - so state which of the two it is. It is not a
# precondition the user can meet, so it does not go in the WARN list.
NOTE=""
if grep -qE '(^|/)tw[[:space:]]+runs[[:space:]]+relaunch' <<<"$CMD"; then
    NOTE="This is a relaunch, so the --disable-optimization question cannot be answered from the command line: the flag does not exist on \`tw runs relaunch\`, and the setting is inherited from the original launch. Check it in the Platform launch form before confirming."
fi

MSG="GATE: this command can start a pipeline run. Show the user the complete command (every parameter, one per line) and wait for an explicit \"確認執行\" before proceeding."
[ -n "$NOTE" ] && MSG="${MSG}

${NOTE}"
[ -n "$WARN" ] && MSG="${MSG}

Preconditions that are not met:${WARN}

Report these to the user with the command; do not silently launch past them."

# R2: what Claude Code shows the user directly when it asks - the exact
# command plus whatever preconditions are unmet, so the ask prompt alone is
# enough to decide on without needing to scroll up to additionalContext.
REASON="$CMD"
[ -n "$NOTE" ] && REASON="${REASON}

${NOTE}"
[ -n "$WARN" ] && REASON="${REASON}

Preconditions that are not met:${WARN}"

ask "$MSG" "$REASON"
