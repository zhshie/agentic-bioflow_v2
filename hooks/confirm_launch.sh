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
# Feature 005 (#48, Constitution 2.0.0): two changes, from one incident. A
# subagent doing a small analysis with neither nf-core nor this plugin ran a
# read-only `wsl.exe -e ssh -o BatchMode=yes ...` query and was stopped here
# for a code it could not have cost.
#   1. Scope. Everything in this file now happens only when the plugin is in
#      use: the first lines below read stdin and ask hooks/in_use.sh, before
#      the jq probe and before anything is split, and exit silently when the
#      answer is no (the constitution's Safety Net applies to a session in use).
#      That covers the launch ask, the identity and resident-process asks and
#      D3 alike. Unsure counts as in use.
#   2. Detection. D3 no longer asks for ssh run through WSL (command word wsl
#      or wsl.exe) or with -o BatchMode=yes: neither can cost a one-time code.
#      Everything else D3 asked about, it still asks about.
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
        *'agent_ctl.sh start '*|*'agent_ctl.sh stop '*|*'agent_ctl.sh restart '*|*'egress_ctl.sh start '*|*'egress_ctl.sh stop '*|*'egress_ctl.sh restart '*|*'egress_allow.sh add '*|*'egress_allow.sh remove '*|*'--set agent_connection '*)
            return 0 ;;
    esac
    return 1
}

# Feature 005 (#48), Constitution 2.0.0: this plugin is silent in a session that
# is not using it. Asked FIRST, before the jq probe and before anything is
# split or parsed, so that session pays for one read of stdin and some string
# matching - no process beyond `cat` (#34). hooks/in_use.sh has the definition
# of "in use" and the rule that unsure counts as in use. A hook directory
# without in_use.sh, or one that cannot be sourced, answers "in use": the gate
# below then runs exactly as it did before this existed.
INPUT=$(cat)
HD="${0%/*}"; [ "$HD" = "$0" ] && HD=.
{ . "$HD/in_use.sh"; } 2>/dev/null || abf_in_use() { return 0; }
abf_in_use "$INPUT" "$INPUT" || exit 0

if ! printf '{}' | jq -e . >/dev/null 2>&1; then
    RAW=$INPUT
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
    # #29: an MCP server's tool starts a run through its own API, with no
    # command line to read - Seqera's MCP can launch (docs/LAB_AGENTS.md).
    # hooks.json routes only Seqera/Tower MCP tools here, and they are judged
    # by NAME: their payloads are JSON parameters, and scanning those for the
    # word "ssh" would pause every harmless query.
    case "$TOOL" in
        mcp__*)
            if grep -qiE '(^|_)(re)?launch|submit|run_(workflow|pipeline)|start_run' <<<"${TOOL#mcp__}"; then
                ask "GATE: '$TOOL' is an MCP tool that starts a pipeline run. Show the user the full call - pipeline, revision, parameters, compute environment - and wait for their explicit confirmation before it runs, exactly as for a tw launch." \
                    "MCP launch-type tool '$TOOL':

$INPUT"
            fi ;;
    esac
    # A Seqera/Tower tool that is not launch-named is a query. Any other MCP
    # tool reaching here is a shell-like one (hooks.json), judged below.
    case "$TOOL" in mcp__*[Ss]eqera*|mcp__*[Tt]ower*) exit 0 ;; esac
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
# ["']? after .sh: an installed plugin's scripts are naturally called through a
# quoted "${CLAUDE_PLUGIN_ROOT}/scripts/..." path, and the closing quote used to
# stand between the name and its verb, so nothing asked (independent
# acceptance of 002, H1 - the same gap as the allowlist gate below).
RESIDENT_RE='(^|[^[:alnum:]_])(agent_ctl|egress_ctl)\.sh["'\'']?[[:space:]]+["'\'']?(start|stop|restart)([^[:alnum:]_-]|$)'
if grep -qE "$RESIDENT_RE" <<<"$CMD" 2>/dev/null; then
    # A relay (re)start is the moment this deployment's extra domains take
    # effect - however they got into the file, egress_allow.sh or an editor.
    # So the ask shows exactly what will be carried; approving a restart must
    # never mean approving a list nobody was shown (002 acceptance, H2).
    RELAY_LIST=""
    if grep -qE 'egress_ctl\.sh["'\'']?[[:space:]]+["'\'']?(start|restart)([^[:alnum:]_-]|$)' <<<"$CMD" 2>/dev/null; then
        RELAY_ERRF=$(mktemp 2>/dev/null) || RELAY_ERRF=/dev/null
        RELAY_DOMS=$(bash "$(dirname "$0")/../scripts/egress_allow.sh" domains 2>"$RELAY_ERRF")
        RELAY_ERR=""
        if [ "$RELAY_ERRF" != /dev/null ]; then RELAY_ERR=$(tr '\n' ' ' < "$RELAY_ERRF"); rm -f -- "$RELAY_ERRF"; fi
        if [ -n "$RELAY_DOMS" ]; then
            RELAY_LIST="
This deployment's extra domains the relay will carry: ${RELAY_DOMS}"
        else
            RELAY_LIST="
This deployment adds no extra domains (built-in list only)."
        fi
        [ -n "$RELAY_ERR" ] && RELAY_LIST="${RELAY_LIST}
Not loaded: ${RELAY_ERR}"
    fi
    ask "GATE: this starts, stops or restarts a resident process (the Tower Agent or the egress relay) on the site's SHARED login node. Before running it, tell the user which process, under which identity (agent_connection / credential) and why, and wait for their explicit yes. For the relay, also show the user this deployment's extra domains listed below - starting it is when they take effect. Never start one under an agent_connection that is not this member's own - docs/SETTINGS.md: two members sharing one are refused permanently.${RELAY_LIST}" \
        "$CMD

Starts/stops a resident process on the shared login node.${RELAY_LIST}"
fi
# Feature 002: the per-deployment egress allowlist (scripts/egress_allow.sh).
# Adding or removing a domain changes what the shared login node's relay will
# carry for every compute job - a security boundary, so the user answers, not
# the model. `list` and `domains` only read and are not matched.
# Judged on the quote-free column of the shared splitter, so `echo "egress_allow.sh
# add x.org"` or a commit message that mentions it does not ask, while
# on_site.sh '...' (whose quoted payload the splitter re-emits as a command of
# its own) and path forms do. The cheap substring test first keeps every other
# command off this path entirely; matching is in-shell, no fork per segment.
if [[ $CMD == *egress_allow.sh* ]]; then
    EA_NB=$(printf '%s\n' "$CMD" | awk -f "$(dirname "$0")/strip_heredocs.awk" 2>/dev/null)
    [ -n "$EA_NB" ] || EA_NB="$CMD"
    EA_US=$(printf '\037')
    EA_SEGS=$(printf '%s\n' "$EA_NB" | awk -f "$(dirname "$0")/split_segments.awk" 2>/dev/null)
    if [ -z "$EA_SEGS" ]; then
        EA_SEGS=$(printf '%s\n' "$EA_NB" | sed -E 's/(\|\||&&|[;&|])/\n/g' \
                  | while IFS= read -r l; do printf '%s%s%s\n' "$l" "$EA_US" "$l"; done)
    fi
    # The quote-free column only decides that the script is really being run
    # (not named inside someone else's quotes). WHAT it is asked to do is read
    # from the as-written segment with quotes dropped, and anything but a plain
    # `list` or `domains` asks: matching `add|remove` on the quote-free column
    # let `"add"`, `remove "x.org"` and `$op` through, because that column
    # blanks every quoted word (developer review of S3).
    #
    # Independent acceptance of 002 (H1, M1) widened "really being run": a
    # QUOTED path - "${CLAUDE_PLUGIN_ROOT}/scripts/egress_allow.sh", the
    # natural form for an installed plugin - is blanked from the quote-free
    # column too. So a segment also counts as running it when its command word
    # is something that runs a script (a shell, source, a wrapper) and the
    # name appears in it once quotes are dropped. `echo "..."` / `git commit
    # -m "..."` still do not: their command word runs nothing. And every
    # mention of the name is read, not the first: `X="egress_allow.sh list"
    # bash .../egress_allow.sh add ...` must not borrow the harmless `list`.
    EA_RUN_RE='(^|[^[:alnum:]_])egress_allow\.sh([^[:alnum:]_.-]|$)'
    EA_REDIR_RE='^[[:space:]]*[0-9]*[<>]+[&]?[[:space:]]*[^[:space:]]+(.*)$'
    EA_REASON_RE='--reason[[:space:]=]+(.*)$'
    while IFS="$EA_US" read -r EA_SEG EA_V EA_CW; do
        EA_PLAIN="${EA_SEG//[\"\']/}"
        EA_RUN=0
        [[ $EA_V =~ $EA_RUN_RE ]] && EA_RUN=1
        if [ "$EA_RUN" = 0 ] && [[ $EA_PLAIN == *egress_allow.sh* ]]; then
            case "${EA_CW##*/}" in
                bash|sh|zsh|dash|ksh|source|.|exec|env|command|nohup|timeout|time|sudo|xargs|nice|egress_allow.sh) EA_RUN=1 ;;
            esac
        fi
        [ "$EA_RUN" = 1 ] || continue
        EA_REST="$EA_PLAIN" EA_OP="" EA_DOM="" EA_NEED=0
        while [[ $EA_REST == *egress_allow.sh* ]]; do
            EA_REST="${EA_REST#*egress_allow.sh}"
            EA_T="$EA_REST"
            while [[ $EA_T =~ $EA_REDIR_RE ]]; do EA_T="${BASH_REMATCH[1]}"; done
            read -r EA_O EA_D _ <<< "$EA_T"
            case "$EA_O" in
                list|domains) ;;
                *) EA_NEED=1; [ -n "$EA_OP" ] || { EA_OP="$EA_O"; EA_DOM="$EA_D"; } ;;
            esac
        done
        [ "$EA_NEED" = 1 ] || continue
        [ -n "$EA_OP" ] || EA_OP="(no operation)"
        [ -n "$EA_DOM" ] || EA_DOM="(not stated)"
        EA_WHY="(none given)"
        if [[ $EA_SEG =~ $EA_REASON_RE ]]; then EA_WHY="${BASH_REMATCH[1]}"; EA_WHY="${EA_WHY%%[;&|]*}"; fi
        ask "GATE: this runs egress_allow.sh ${EA_OP}, which can change this deployment's outbound allowlist (domain: ${EA_DOM}; reason: ${EA_WHY}). That moves a security boundary on the site's SHARED login node: the relay will (or will no longer) carry connections to that host for every compute job. Show the user the domain and the reason, confirm the host is really what the failed run needed, and wait for their explicit yes. Adding to the plugin's built-in list is the maintainer's change, not this one." \
                "$CMD

Egress allowlist ${EA_OP}: ${EA_DOM}
Reason: ${EA_WHY}
This moves a security boundary on a shared login node."
    done <<< "$EA_SEGS"
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
    # Reads the same segments the launch check does - here-doc bodies handled
    # by strip_heredocs.awk, then split_segments.awk (#29) - so a payload that
    # ssh/on_site.sh hands to a far shell is judged as a command, while
    # `grep -rn "ssh" docs/` is not (matched on the quote-free column).
    # In-shell matching only: a process per segment made this gate take ~27 s
    # on a 120-line script under Git Bash (#29, round 3).
    case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*)
        TCMD_NB=$(printf '%s\n' "$CMD" | awk -f "$(dirname "$0")/strip_heredocs.awk" 2>/dev/null)
        [ -n "$TCMD_NB" ] || TCMD_NB="$CMD"
        US=$(printf '\037')
        TSEGS=$(printf '%s\n' "$TCMD_NB" | awk -f "$(dirname "$0")/split_segments.awk" 2>/dev/null)
        if [ -z "$TSEGS" ]; then
            TSEGS=$(printf '%s\n' "$TCMD_NB" | sed -E 's/(\|\||&&|[;&|])/\n/g' \
                    | while IFS= read -r l; do printf '%s%s%s\n' "$l" "$US" "$l"; done)
        fi
        TRANSPORT_RE='(^|[[:space:]]|[;&|(])(sudo[[:space:]]+)?([^[:space:]]*/)?(ssh|scp|rsync|sftp)([[:space:]]|$)'
        ONSITE_RE='(^|[[:space:]]|[;&|(])([^[:space:]]*/)?on_site\.sh([[:space:]]|$)'
        # Feature 005 (#48), FR-006: two shapes of ssh that cannot cost a code.
        #   - run through WSL (command word wsl / wsl.exe): WSL's own ssh can
        #     share a connection that is already open (PITFALLS 16g), so no
        #     fresh login happens;
        #   - ssh/scp/sftp with -o BatchMode=yes among ITS OWN options: it never
        #     prompts, it fails instead.
        # Both are judged per segment, on that segment's own words, so
        # `echo wsl; ssh h ls` is still two segments and the ssh still asks.
        #
        # The BatchMode test reads the segment's words the way a shell would
        # (quotes honoured) and walks the options up to the destination, so:
        # an option after the destination belongs to the remote command, a
        # quoted one inside the remote command is not ssh's, `rsync -o` is
        # "owner" and not ssh's at all, and a jump host (-J, ProxyJump,
        # ProxyCommand) can still prompt on the far side. Any other BatchMode
        # value in the options, or anything this does not understand, is not
        # an exemption: when in doubt, ask.
        batchmode_exempt() { # batchmode_exempt <segment as written>; 0 = exempt
            local s="$1" i c cur="" q="" have=0 w kind="" arglet="" pend="" yes=0 bad=0 val
            local -a W=()
            for ((i = 0; i < ${#s}; i++)); do
                c="${s:i:1}"
                if [ -n "$q" ]; then
                    if [ "$c" = "$q" ]; then q=""; else cur="$cur$c"; fi
                else
                    case "$c" in
                        "'"|'"') q="$c"; have=1 ;;
                        [[:space:]]) if [ "$have" = 1 ]; then W+=("$cur"); cur=""; have=0; fi ;;
                        *) cur="$cur$c"; have=1 ;;
                    esac
                fi
            done
            [ "$have" = 1 ] && W+=("$cur")
            for w in "${W[@]}"; do
                if [ -z "$kind" ]; then
                    w="${w##*/}"
                    case "$w" in
                        ssh|ssh.exe) kind=ssh; arglet=BbcDEeFIiJLlmOopQRSWw ;;
                        scp|scp.exe) kind=scp; arglet=cFiJloPS ;;
                        sftp|sftp.exe) kind=sftp; arglet=BbcDFiJloPRSs ;;
                        rsync|rsync.exe) return 1 ;;
                    esac
                    continue
                fi
                if [ "$pend" = -o ]; then
                    pend=""; val="$w"
                elif [ -n "$pend" ]; then
                    [ "$pend" = -J ] && bad=1
                    pend=""; continue
                else
                    case "$w" in
                        --) break ;;
                        -o) pend=-o; continue ;;
                        -o?*) val="${w#-o}" ;;
                        -J|-J?*) bad=1; continue ;;
                        -?) if [[ $arglet == *"${w#-}"* ]]; then pend="$w"; fi; continue ;;
                        -*) c="${w:1:1}"
                            # a cluster or a flag with its argument glued on; an o or J
                            # anywhere in it is one this does not parse
                            case "${w:1}" in *[oJ]*) bad=1 ;; esac
                            continue ;;
                        *) break ;;   # the destination: ssh's own options end here
                    esac
                fi
                # val is one -o value
                case "$val" in
                    [Bb]atch[Mm]ode=[Yy][Ee][Ss]) yes=1 ;;
                    *[Bb]atch[Mm]ode*|*[Pp]roxy[Jj]ump*|*[Pp]roxy[Cc]ommand*) bad=1 ;;
                esac
            done
            [ "$yes" = 1 ] && [ "$bad" = 0 ]
        }
        TSEG=""; TV=""; TCW=""
        while IFS="$US" read -r TSEG TV TCW; do
            [[ $TV =~ $ONSITE_RE ]] && continue
            case "${TCW##*[/\\]}" in wsl|wsl.exe) continue ;; esac
            if [[ $TV =~ $TRANSPORT_RE ]]; then
                batchmode_exempt "$TSEG" && continue
                ask "GATE: this command reaches the site directly over ssh/scp/rsync/sftp, bypassing scripts/on_site.sh. In this shell (Git Bash/MSYS) a direct ssh connection cannot hold a multiplexed master - the control socket comes up but fd-passing to a real session fails (PITFALLS 16b) - so a call like this one falls back to a full login: a one-time code on the user's phone that this agent cannot read. scripts/on_site.sh is the only sanctioned route to the site from here (docs/SITE_ADAPTER.md contract 6); it also knows how to borrow WSL's own ssh for the multiplexed part (PITFALLS 16g), which this bare call does not. Show the user the command and route it through scripts/on_site.sh instead, or let them run it themselves." \
                    "$CMD

This shell's own ssh cannot multiplex (PITFALLS 16b): every direct call like this one costs a fresh one-time code on the user's phone, which this agent cannot read. scripts/on_site.sh is the only sanctioned route to the site from here (docs/SITE_ADAPTER.md contract 6)."
            fi
        done <<< "$TSEGS"
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
