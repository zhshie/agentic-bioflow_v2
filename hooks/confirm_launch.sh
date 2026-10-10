#!/bin/bash
# Nothing existing: Claude Code permission rules and Seqera Platform do not stop a launch typed in the shell and report the preconditions that would ruin it while the command is still on screen.
#
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
    local text
    # jq-broken-later-line: in raw JSON a line break is the two characters `\n`,
    # which glued the next line's first word to an `n` (`ntw`): the escapes for
    # line breaks and tabs are separators too. If sed or tr cannot run, nothing
    # here can be ruled out.
    text=$(printf '%s' "$1" | sed 's/\\[ntr]/ /g' | tr -s "$LOOKS_SHAPED_SEP" ' ')
    if [ -z "$text" ]; then [ -n "$1" ] && return 0; return 1; fi
    text=" $text "
    case "$text" in
        *' tw launch '*|*' tw runs relaunch '*|*' sbatch '*|*' nextflow run '*|*' ssh '*|*' scp '*|*' rsync '*|*' sftp '*)
            return 0 ;;
        # launch-shapes-unconfirmed: the other ways to start a run. A path ending
        # in /launch (the Platform API's endpoint) cannot be told GET from POST
        # here, so it counts.
        *' kuberun '*|*' nf-core launch '*|*' pipelines launch '*|*' actions trigger '*|*' seqerakit '*'.yml'*|*' seqerakit '*'.yaml'*|*' seqerakit - '*|*'/launch '*|*'/launch?'*)
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
# Stdin without starting `cat` (#34: every process is expensive under Git Bash). Not `read -d ''`:
# that reads a pipe one byte at a time (a second per 300 KB) and stops at a NUL.
INPUT=$(</dev/stdin)   # no `cat` process; drops NULs and trailing newlines exactly as $(cat) does
HD="${0%/*}"; [ "$HD" = "$0" ] && HD=.
{ . "$HD/in_use.sh"; } 2>/dev/null || abf_in_use() { return 0; }
abf_in_use "$INPUT" "$INPUT" || exit 0

# One jq call reads what this hook needs, and it stands in for the "can jq run at
# all" probe (#34). Only when it fails does the probe run, which tells "jq cannot
# run" (the refusal below) from "this input is not JSON" (TOOL and CMD stay empty,
# as they always did). The command is read Bash-first, then the other spellings a
# non-Bash execution tool might use for the same idea; a tool this list does not
# cover yet is exactly the case handled below.
#
# The fast path is taken only when that one call saw exactly ONE JSON document whose
# fields are plain strings with no separator inside them (-s, so a second document
# can never be silently dropped). Anything else (not JSON,
# no jq, a field that is an object, two JSON values on stdin) goes the way this
# file always went: the probe, then one jq per field.
#
# jq-broken-gates: the fast path is trusted only when every field came with its
# separator. The fields are read out in order: pattern removal (`#*x`, `%%x*`,
# `##*x`) and ${x//p/} are quadratic in bash on a long string, and a large Write
# or here-doc then outlasts the hook's timeout (#34); `read` is linear. Trailing
# newlines were trimmed by jq, as $(jq) did per field. A jq that exits 0 with
# `{}` or a line of text has not read this input: it goes to the probe below,
# which asks jq for a known answer - `jq -e .` alone passed such a jq.
abf_jq_works() { # a trailing CR is jq.exe on Windows
    local o
    o=$(jq -c .a <<<'{"a":[1]}' 2>/dev/null) || return 1
    [ "${o%$'\r'}" = '[1]' ]
}
JQ_FAST=0
if JQ_OUT=$(jq -js 'if length == 1 then (.[0] | [(.tool_name // ""), (.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // "")] | if all(.[]; type == "string") and (any(.[]; contains("\u001f") or contains("\u0000")) | not) then (map(sub("\\n+\\z"; "") + "\u001f") | join("")) else empty end) else empty end' <<<"$INPUT" 2>/dev/null) \
   && [ -n "$JQ_OUT" ]; then
    {
        IFS= read -r -d $'\037' TOOL &&
        IFS= read -r -d $'\037' CMD
    } <<<"$JQ_OUT" && JQ_FAST=1
fi
if [ "$JQ_FAST" = 0 ] && ! abf_jq_works; then
    RAW=$INPUT
    # Independent acceptance of 002: hooks.json now also routes Write/Edit/
    # MultiEdit/NotebookEdit calls here, and their raw payload is the FILE
    # CONTENT, not a command - a README that says ` rsync ` is not a transfer.
    # Without jq all that can still be read is the file's name: egress_allow.tsv
    # asks (a hand-built JSON, there being no jq to build it), anything else
    # passes untouched.
    NJ_RE_TOOL='"tool_name"[[:space:]]*:[[:space:]]*"([A-Za-z]*)"'
    NJ_TOOL=""
    [[ $RAW =~ $NJ_RE_TOOL ]] && NJ_TOOL="${BASH_REMATCH[1]}"
    case "$NJ_TOOL" in
        Write|Edit|MultiEdit|NotebookEdit)
            NJ_RE_FP='"(file_path|notebook_path)"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
            NJ_FP=""
            if [[ $RAW =~ $NJ_RE_FP ]]; then NJ_FP="${BASH_REMATCH[2]}"; fi
            NJ_FP="${NJ_FP//\\\\//}"; NJ_FP="${NJ_FP//\\//}"
            if [ "${NJ_FP##*/}" = egress_allow.tsv ]; then
                printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Direct change to egress_allow.tsv (jq is missing, so this hook can only read the file name). This moves a security boundary on a shared login node.","additionalContext":"GATE: this writes this deployment'"'"'s own relay allowlist file (egress_allow.tsv) directly, around scripts/egress_allow.sh and its checks. That moves a security boundary on the site'"'"'s SHARED login node. Show the user exactly which domain is being added or removed and why, and wait for their explicit yes. Prefer scripts/egress_allow.sh add/remove."}}'
            fi
            exit 0 ;;
    esac
    if looks_launch_shaped "$RAW"; then
        cat >&2 <<'EOF'
BLOCKED: jq is missing or cannot run here, so hooks/confirm_launch.sh cannot read what
this command is precisely - and the raw text of this one matches a launch- or
site-transport-shaped pattern (tw launch / tw runs relaunch / tw actions trigger
/ sbatch / nextflow run|kuberun / nf-core launch / seqerakit <file>.yml / an API
path ending in /launch / ssh / scp / rsync / sftp), so it is refused rather than guessed at. A
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

if [ "$JQ_FAST" = 0 ]; then
    # (The fast path's fields were read out above.)
    TOOL=$(jq -r '.tool_name // ""' <<<"$INPUT" 2>/dev/null)
    CMD=$(jq -r '.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // ""' <<<"$INPUT" 2>/dev/null)
fi

# Fail-CLOSED output (invariant 13, SN3). Every verdict below is built by jq from
# strings that can be as large as the command itself, and `jq --arg` puts them in
# argv, which the OS limits (about 32 KB on Windows, 128 KiB on Linux). A jq that
# fails there prints nothing and the hook used to exit 0 = the call PROCEEDS. So:
# (1) what is displayed is bounded, with a marker saying what was left out (the
# verdict was already reached on the whole text), and (2) if jq still cannot
# build the output, a fixed minimal ask is printed instead of nothing.
abf_cap() { # abf_cap <text> -> ABF_CAP, at most ~6000 characters
    ABF_CAP=$1
    if [ "${#1}" -gt 6000 ]; then
        ABF_CAP="${1:0:3000}

[... $(( ${#1} - 6000 )) characters left out of this display; the whole command was checked ...]

${1: -3000}"
    fi
}
abf_emit() { # abf_emit <ask|deny|-> <permissionDecisionReason or -> <additionalContext or ->
    local o r c
    abf_cap "$2"; r=$ABF_CAP; abf_cap "$3"; c=$ABF_CAP
    if o=$(jq -n --arg d "$1" --arg r "$r" --arg c "$c" \
        '{hookSpecificOutput: ({hookEventName: "PreToolUse"}
            + (if $d != "-" then {permissionDecision: $d} else {} end)
            + (if $r != "-" then {permissionDecisionReason: $r} else {} end)
            + (if $c != "-" then {additionalContext: $c} else {} end))}' 2>/dev/null) \
       && [[ $o == '{'*'"hookSpecificOutput"'*'"hookEventName"'*'"PreToolUse"'* ]] \
       && { [ "$1" = - ] || [[ $o == *'"permissionDecision"'*'"'"$1"'"'* ]]; } \
       && { [ "$3" = - ] || [[ $o == *'"additionalContext"'* ]]; }; then
        # gate-emit-empty-object: printed only when it is the answer asked for; a
        # jq that builds `{}` (no decision: the call proceeds) gets the fixed ask.
        printf '%s\n' "$o"
    else
        printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"GATE: this hook could not build its own message (jq failed), so it cannot rule this call out. Show the user the full command and confirm it by hand before it runs.","additionalContext":"GATE: the hook could not build its message; treat this call as gated and confirm it with the user."}}'
    fi
}

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
if ! . "$HD/launch_trigger.sh" 2>/dev/null \
   || ! declare -F is_launch_command >/dev/null 2>&1; then
    abf_emit - - "GATE NOT WORKING: hooks/launch_trigger.sh could not be loaded, so this command was NOT checked and no other command will be either.

Reinstall or repair the plugin. Until then the launch gate is absent: treat anything that can start a run - tw launch, tw runs relaunch, sbatch, nextflow run - as ungated, and confirm it with the user by hand."
    exit 0
fi

# The one JSON builder this file has for a structural pause: R2's launch ask
# below and D3's transport ask further down both end here, rather than each
# carrying its own `jq -n` call that could drift out of sync with the other.
ask() { # ask <additionalContext message> <permissionDecisionReason>
    abf_emit ask "$2" "$1"
    exit 0
}

# #45: a Write/Edit-type tool changing this deployment's own relay allowlist file
# (egress_allow.tsv) directly, around scripts/egress_allow.sh and its checks.
# Only the file name is read; no other Write is this hook's business (a launch
# word in a document being written is not a launch).
case "$TOOL" in
    Write|Edit|MultiEdit|NotebookEdit)
        EA_FP=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' <<<"$INPUT" 2>/dev/null)
        EA_FP="${EA_FP//\\//}"
        if [ "${EA_FP##*/}" = egress_allow.tsv ]; then
            ask "GATE: this writes this deployment's own relay allowlist file (egress_allow.tsv) directly, around scripts/egress_allow.sh and its checks (a specific domain only, no shared or wildcard names, a recorded reason, the 100-entry limit). That moves a security boundary on the site's SHARED login node: a domain added here is carried by the relay the next time it is started or restarted. Show the user exactly which domain is being added or removed and why, and wait for their explicit yes. Prefer scripts/egress_allow.sh add/remove, which checks the name." \
                "$TOOL of $EA_FP

Direct change to egress_allow.tsv.
This moves a security boundary on a shared login node."
        fi
        exit 0 ;;
esac

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
# In-shell, not grep (#34). grep reads one line at a time and [[:space:]] in
# [[ =~ ]] also matches a newline, so a command with newlines is asked of grep.
# #62: the cheap substring test first; the regex reads the whole command.
RESIDENT_HIT=0
case "$CMD" in *agent_ctl*|*egress_ctl*) [[ $CMD =~ $RESIDENT_RE ]] && RESIDENT_HIT=1 ;; esac
if [ "$RESIDENT_HIT" = 1 ] && { [[ $CMD != *$'\n'* ]] || grep -qE "$RESIDENT_RE" <<<"$CMD" 2>/dev/null; }; then
    # A relay (re)start is the moment this deployment's extra domains take
    # effect - however they got into the file, egress_allow.sh or an editor.
    # So the ask shows exactly what will be carried; approving a restart must
    # never mean approving a list nobody was shown (002 acceptance, H2).
    RELAY_LIST=""
    RELAY_START_RE='egress_ctl\.sh["'\'']?[[:space:]]+["'\'']?(start|restart)([^[:alnum:]_-]|$)'
    if [[ $CMD =~ $RELAY_START_RE ]] && { [[ $CMD != *$'\n'* ]] || grep -qE "$RELAY_START_RE" <<<"$CMD" 2>/dev/null; }; then
        RELAY_ERRF=$(mktemp 2>/dev/null) || RELAY_ERRF=/dev/null
        RELAY_DOMS=$(bash "$HD/../scripts/egress_allow.sh" domains 2>"$RELAY_ERRF")
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
        # #45: an environment prefix on a direct start (`NF_RELAY_EXTRA_DOMAINS=x
        # bash scripts/egress_ctl.sh start`, `env ...`, `export ...;`) hands the
        # relay a list the file does not hold, so the summary above would be
        # untrue. Through scripts/on_site.sh the variable is always replaced by the
        # file's list, so only a direct start is named.
        if [[ $CMD == *NF_RELAY_EXTRA_DOMAINS=* ]] && [[ $CMD != *on_site.sh* ]]; then
            # A regex, not ${CMD#*...}: bash tries every prefix for that, quadratic
            # on a long command (#62).
            RELAY_OVR=""; RELAY_OVR_RE='NF_RELAY_EXTRA_DOMAINS=([^[:space:];&|]*)'
            [[ $CMD =~ $RELAY_OVR_RE ]] && RELAY_OVR="${BASH_REMATCH[1]}"
            RELAY_LIST="${RELAY_LIST}
THIS COMMAND ALSO SETS NF_RELAY_EXTRA_DOMAINS=${RELAY_OVR}, which overrides this deployment's list: the relay would carry THAT list, not the one shown above. Show the user the domains it names."
        fi
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
#
# #45: the name can be written so that it never appears as written - a glob
# (`egress_allo?.sh`, `egress_allow.*`), a backslash, a quote splice, or a
# variable set earlier in the same command. The pre-test therefore reads the
# command the way a shell would (no quotes, no backslashes) and also fires on a
# glob or a `$` beside an `add`/`remove` word; the per-segment test then decides
# what is really being run. The file the script keeps (egress_allow.tsv) is
# guarded the same way: a redirect, an editor, tee, cp, sed -i and the like ask.
# #62: ${x//p/} costs a pass over the rest of the string per match, so a big
# command full of quotes (a python here-doc) is handed to one `tr` instead.
EA_N=""
[ "${#CMD}" -gt 16384 ] && EA_N=$(tr -d '\\"'"'" <<<"$CMD" 2>/dev/null)
[ -n "$EA_N" ] || { EA_N="${CMD//\\/}"; EA_N="${EA_N//\"/}"; EA_N="${EA_N//\'/}"; }
EA_PRE=0
case "$EA_N" in *egress_*|*.tsv*) EA_PRE=1 ;; esac
if [ "$EA_PRE" = 0 ] && [[ $EA_N == *[\*\?\[\$]* ]] && [[ $EA_N =~ (^|[[:space:]])(add|remove)([[:space:]]|$) ]]; then EA_PRE=1; fi
if [ "$EA_PRE" = 1 ]; then
    EA_NB=$(awk -f "$HD/strip_heredocs.awk" <<<"$CMD" 2>/dev/null)
    [ -n "$EA_NB" ] || EA_NB="$CMD"
    EA_US=$'\037'
    EA_SEGS=$(awk -f "$HD/split_segments.awk" <<<"$EA_NB" 2>/dev/null)
    # #62: is_launch_command (below) reads these same segments of this same
    # command; it takes them from here instead of running both awk passes again.
    [ -n "$EA_SEGS" ] && { ABF_SPLIT_FOR="$CMD"; ABF_SPLIT_SEGS="$EA_SEGS"; ABF_SPLIT_STRIPPED="$EA_NB"; }
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
    EA_WR_RE='>>?[[:space:]]*([^[:space:]<>;&|]+)'
    EA_INPLACE_RE='(^|[[:space:]])(-[A-Za-z]*i[A-Za-z]*|--in-place[^[:space:]]*)([[:space:]]|$)'
    EA_VARS=""
    # ea_names <word> <file name>: does the word name that file, literally or as
    # a glob (`egress_allo?.sh`)? The path in front of the name does not matter.
    #
    # Independent acceptance of 002: a glob that merely COULD match the name
    # (`*.tsv`, `results/*/*.tsv`) is not naming it - `cp results/*.tsv /tmp/`
    # asked every time. A glob names the file only when its own text carries
    # the name (an obfuscation such as `egress_allo?.tsv` or `egr*ow.tsv` keeps
    # a piece of it: egr / ess / allow) or when its folder is the one the file
    # lives in (this deployment's config folder; for the script, the plugin's
    # scripts folder). The literal name always counts, in any folder.
    EA_CWD=""
    EA_CFG_DIRS=""
    EA_SCR_DIRS=""
    if declare -F _abf_find_deployment >/dev/null 2>&1 && _abf_find_deployment 2>/dev/null; then
        EA_CFG_DIRS="${_ABF_SETTINGS%/*}"$'\n'"${_ABF_ROOT}/config"
        if declare -F _abf_canon >/dev/null 2>&1; then
            _abf_canon "${_ABF_SETTINGS%/*}" 2>/dev/null && EA_CFG_DIRS="${EA_CFG_DIRS}"$'\n'"$REPLY"
        fi
    fi
    EA_PLUGIN_DIR="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
    EA_SCR_DIRS="${EA_PLUGIN_DIR}/scripts"
    [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && EA_SCR_DIRS="${EA_SCR_DIRS}"$'\n'"${CLAUDE_PLUGIN_ROOT%/}/scripts"
    EA_RE_CWD='"cwd"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
    if [[ $INPUT =~ $EA_RE_CWD ]]; then EA_CWD="${BASH_REMATCH[1]//\\\\//}"; EA_CWD="${EA_CWD//\\//}"; EA_CWD="${EA_CWD%/}"; fi
    # ea_in_dir <folder part of a word> <newline list of folders>
    ea_in_dir() {
        local d="$1" t
        d="${d//\\//}"
        case "$d" in
            '~'|'~/'*) d="${HOME:-}${d#\~}" ;;
        esac
        d="${d//\$\{HOME\}/${HOME:-}}"; d="${d//\$HOME/${HOME:-}}"
        case "$d" in
            /*|[A-Za-z]:*) ;;
            *) [ -n "$EA_CWD" ] || return 1
               d="$EA_CWD${d:+/$d}" ;;
        esac
        while [[ $d == *//* ]]; do d="${d//\/\//\/}"; done
        while [[ $d == */./* ]]; do d="${d//\/.\//\/}"; done
        d="${d%/.}"; d="${d%/}"
        while IFS= read -r t; do
            [ -n "$t" ] || continue
            t="${t%/}"
            # shellcheck disable=SC2053  # the word's folder may itself be a glob
            [[ $t == $d ]] && return 0
        done <<<"$2"
        return 1
    }
    ea_names() { # ea_names <word> <file name>
        local b="${1##*/}" lit d=""
        [[ $b == "$2" ]] && return 0
        [[ $b == *[\*\?\[]* ]] || return 1
        # shellcheck disable=SC2053
        [[ $2 == $b ]] || return 1
        lit="${b//[\*\?\[\]]/}"
        case "$lit" in *egr*|*ess*|*allow*|*gress*) return 0 ;; esac
        case "$1" in */*) d="${1%/*}"; [ -n "$d" ] || d=/ ;; esac
        case "$2" in
            *.tsv) ea_in_dir "$d" "$EA_CFG_DIRS" ;;
            *)     ea_in_dir "$d" "$EA_SCR_DIRS" ;;
        esac
    }
    # ea_tsv_scan <text>: sets EA_TSV=1 when a word names the allowlist file,
    # and EA_DEST=1 when one of those words could be WRITTEN (a redirect, an
    # operand that is not a copy's source). `cp egress_allow.tsv /tmp/bk` only
    # reads it; `mv` removes it, so it is not a plain source.
    ea_tsv_scan() {
        local -a W; local i n w w2 last=-1 tflag=0 cpmode=0
        read -r -a W <<<"$1"
        n=${#W[@]}
        case "$EA_CWB" in cp|scp|rsync|install) cpmode=1 ;; esac
        for ((i = 1; i < n; i++)); do
            w="${W[$i]}"
            case "$w" in
                -t|-t*|--target-directory|--target-directory=*) tflag=1 ;;
                -*|[0-9]*[\<\>]*|[\<\>]*) ;;
                *) last=$i ;;
            esac
        done
        for ((i = 0; i < n; i++)); do
            w2="${W[$i]}"
            if [[ $w2 =~ ^[0-9]*[\<\>]+(.*)$ ]]; then
                w2="${BASH_REMATCH[1]}"
                ea_names "${w2##*=}" egress_allow.tsv && { EA_TSV=1; EA_DEST=1; }
                continue
            fi
            w2="${w2##*=}"
            if ea_names "$w2" egress_allow.tsv; then
                EA_TSV=1
                if [ "$cpmode" = 0 ]; then EA_DEST=1
                elif [ "$tflag" = 0 ] && [ "$i" = "$last" ]; then EA_DEST=1; fi
            fi
        done
    }
    # #62: which segments the checks below can act on at all. A word names the
    # file or the script only if it holds a piece of their names (egr, ess,
    # allow - ea_names), a variable (`$a.sh`, `$HOME/...`), or is a glob whose
    # folder is the config or scripts folder: then the word holds a `/`, or the
    # session is in that folder (EA_GLOB_HERE). Assignments are kept for the
    # variables they set. Everything else is skipped before the word loops,
    # which cost a lot per segment on Git Bash, and for a big command (a python
    # here-doc is thousands of segments) one awk pass drops those segments
    # before the shell reads them; if awk cannot run, every segment is read.
    EA_GLOB_HERE=0
    { ea_in_dir "" "$EA_CFG_DIRS" || ea_in_dir "" "$EA_SCR_DIRS"; } && EA_GLOB_HERE=1
    if [ "${#EA_SEGS}" -gt 16384 ]; then
        EA_CAND=$(awk -F"$EA_US" -v here="$EA_GLOB_HERE" '{
            p = $1; gsub(/["\047]/, "", p); ps = p; gsub(/\\/, "/", ps); gsub(/\\/, "", p)
            if (p ~ /egr|ess|allow|\$/ || p ~ /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*$/ \
                || (p ~ /[*?[]/ && (here == 1 || index(ps, "/")))) print }' <<<"$EA_SEGS" 2>/dev/null) && EA_SEGS=$EA_CAND
    fi
    EA_SEG=""; EA_V=""; EA_CW=""
    while IFS="$EA_US" read -r EA_SEG EA_V EA_CW; do
        [ -n "$EA_SEG" ] || continue
        EA_PLAIN="${EA_SEG//[\"\']/}"
        # Two readings of a backslash: an ESCAPE (`egr\ess_allow.tsv` - dropped,
        # which is what a shell does) and a Windows path SEPARATOR
        # (`C:\cfg\egress_allow.tsv`, `.\egress_allow.tsv` - read as `/`).
        # The file's name is looked for in both; the script's is judged on the
        # first only, as before.
        EA_PLAIN_S="${EA_PLAIN//\\//}"; EA_PLAIN="${EA_PLAIN//\\/}"
        # `a=egress_allow` on its own is remembered and read into later segments.
        if [[ $EA_PLAIN =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=([^[:space:]]*)[[:space:]]*$ ]]; then
            EA_VARS="${EA_VARS}${BASH_REMATCH[1]}=${BASH_REMATCH[2]}"$'\n'
            continue
        fi
        if [ -n "$EA_VARS" ] && [[ $EA_PLAIN == *'$'* ]]; then
            while IFS='=' read -r EA_VN EA_VV; do
                [ -n "$EA_VN" ] || continue
                EA_PLAIN="${EA_PLAIN//\$\{$EA_VN\}/$EA_VV}"; EA_PLAIN="${EA_PLAIN//\$$EA_VN/$EA_VV}"
                EA_PLAIN_S="${EA_PLAIN_S//\$\{$EA_VN\}/$EA_VV}"; EA_PLAIN_S="${EA_PLAIN_S//\$$EA_VN/$EA_VV}"
            done <<<"$EA_VARS"
        fi
        case "$EA_PLAIN" in
            *egr*|*ess*|*allow*|*'$'*) ;;
            *[\*\?\[]*)
                case "$EA_PLAIN_S" in
                    */*) ;;
                    *) [ "$EA_GLOB_HERE" = 1 ] || continue ;;
                esac ;;
            *) continue ;;
        esac
        EA_CWB="${EA_CW##*/}"
        EA_SUB=""
        if [ "$EA_CWB" = git ]; then
            read -r _ EA_SUB _ <<<"$EA_PLAIN"
        fi

        # --- direct writes to the file the script keeps (#45) -----------------
        # (a redirect glued to its target - `>>cfg/x`, `2>cfg/x` - and a dd-style
        # of=cfg/x are read inside ea_tsv_scan; both readings of a backslash.)
        EA_TSV=0; EA_DEST=0
        ea_tsv_scan "$EA_PLAIN"
        ea_tsv_scan "$EA_PLAIN_S"
        if [ "$EA_TSV" = 1 ]; then
            EA_WRITES=0
            if [[ $EA_V == *'>'* ]]; then
                for EA_T in "$EA_PLAIN" "$EA_PLAIN_S"; do
                    while [[ $EA_T =~ $EA_WR_RE ]]; do
                        ea_names "${BASH_REMATCH[1]}" egress_allow.tsv && EA_WRITES=1
                        EA_T="${EA_T#*"${BASH_REMATCH[0]}"}"
                    done
                done
            fi
            if [ "$EA_WRITES" = 0 ]; then
                case "$EA_CWB" in
                    cat|less|more|head|tail|grep|egrep|fgrep|rg|ag|wc|ls|ll|dir|stat|file|diff|cmp|sort|uniq|cut|column|tr|nl|od|xxd|hexdump|md5sum|sha1sum|sha256sum|cksum|du|realpath|readlink|basename|dirname|test|'['|echo|printf|bat|jq|tac|rev|paste|join|comm|fold|strings|shellcheck) ;;
                    get-content|gc|type|select-string|sls|test-path|get-item|gi|get-childitem|gci|get-filehash|measure-object|resolve-path|get-itemproperty) ;;
                    cp|scp|rsync|install) [ "$EA_DEST" = 1 ] && EA_WRITES=1 ;;
                    sed|awk|gawk|perl|ruby) [[ $EA_PLAIN =~ $EA_INPLACE_RE ]] && EA_WRITES=1 ;;
                    git) case "$EA_SUB" in diff|log|show|blame|status|ls-files|grep|cat-file|annotate|whatchanged) ;; *) EA_WRITES=1 ;; esac ;;
                    *) EA_WRITES=1 ;;
                esac
            fi
            if [ "$EA_WRITES" = 1 ]; then
                ask "GATE: this writes this deployment's own relay allowlist file (egress_allow.tsv) directly, around scripts/egress_allow.sh and its checks (a specific domain only, no shared or wildcard names, a recorded reason, the 100-entry limit). That moves a security boundary on the site's SHARED login node: a domain added here is carried by the relay the next time it is started or restarted. Show the user exactly which domain is being added or removed and why, and wait for their explicit yes. Prefer scripts/egress_allow.sh add/remove, which checks the name." \
                    "$CMD

Direct change to egress_allow.tsv.
This moves a security boundary on a shared login node."
            fi
        fi

        # --- the script itself ------------------------------------------------
        case "$EA_CWB" in
            cat|less|more|head|tail|grep|egrep|fgrep|rg|ag|wc|ls|ll|dir|stat|file|diff|cmp|shellcheck|bat|git) continue ;;
        esac
        # `bash -n` parses and runs nothing.
        [[ $EA_PLAIN =~ (^|[[:space:]])(bash|sh|zsh|dash|ksh)[[:space:]]+(-[A-Za-z]+[[:space:]]+)*-[A-Za-z]*n[A-Za-z]*[[:space:]] ]] && continue
        # Spellings that name the script without containing its name: a glob
        # (`egress_allo?.sh`) or a variable that is not set here (`$a.sh`)
        # followed by add/remove. Read as the name, when what runs it is a
        # runner (or is itself that word).
        EA_NORM=""; EA_MOD=0
        set -f
        for EA_W in $EA_PLAIN; do
            EA_B="${EA_W##*/}"
            if [[ $EA_B == *[\*\?\[]* ]] && ea_names "$EA_W" egress_allow.sh; then
                EA_W="${EA_W%"$EA_B"}egress_allow.sh"; EA_MOD=1
            fi
            EA_NORM="$EA_NORM $EA_W"
        done
        set +f
        # A variable-named script is read as ours only when something says it
        # may be: the command text says egress, or the word's folder is the
        # plugin's own (`scripts/$a.sh`, `$CLAUDE_PLUGIN_ROOT/...`). Without
        # that, `bash $HOME/bin/todo.sh add milk` is somebody else's script.
        if [[ $EA_NORM =~ (^|[[:space:]])([^[:space:]]*\$[^[:space:]]*)[[:space:]]+(add|remove)([[:space:]]|$) ]]; then
            EA_VW="${BASH_REMATCH[2]}"
            EA_VHINT=0
            [[ $EA_N == *egress* ]] && EA_VHINT=1
            case "$EA_VW" in
                *CLAUDE_PLUGIN_ROOT*|*/plugins/*|*agentic-bioflow*|scripts/*|*/scripts/*) EA_VHINT=1 ;;
            esac
            if [ "$EA_VHINT" = 1 ]; then
                EA_NORM="${EA_NORM/"$EA_VW"/egress_allow.sh}"; EA_MOD=1
            fi
        fi
        EA_RUN=0
        [[ $EA_V =~ $EA_RUN_RE ]] && EA_RUN=1
        if [ "$EA_RUN" = 0 ] && [ "$EA_MOD" = 1 ]; then
            case "$EA_CWB" in
                bash|sh|zsh|dash|ksh|source|.|exec|env|command|nohup|timeout|time|sudo|xargs|nice) EA_RUN=1 ;;
                *) ea_names "$EA_CW" egress_allow.sh && EA_RUN=1 ;;
            esac
            [ "$EA_RUN" = 1 ] && EA_PLAIN="$EA_NORM"
        fi
        if [ "$EA_RUN" = 0 ] && [[ $EA_PLAIN == *egress_allow.sh* ]]; then
            case "$EA_CWB" in
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
                # Sourcing it with no operation runs nothing worth asking about.
                '') case "$EA_CWB" in source|.) ;; *) EA_NEED=1 ;; esac ;;
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
# The cheap substring test first: the pattern needs one of these two words (#34).
ID_HITS=""
case "$CMD" in
    *settings.sh*|*set_setting*)
        ID_HITS=$(grep -oE "(settings\.sh[[:space:]]+--set|set_setting)[[:space:]]+($IDENTITY_KEYS)[[:space:]]+[^;&|]*" <<<"$CMD" 2>/dev/null) ;;
esac
if [ -n "$ID_HITS" ]; then
    HERE_S="$(cd "$HD/.." && pwd)/scripts/settings.sh"
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
    #
    # #34: D3 can only ever speak about a transport word, and `uname` is a
    # process, so it is asked only when such a word could be in the segments.
    # The segments are built from the command's own characters, in order, with
    # quoted text and line continuations taken OUT (`s"x"sh` reads as ssh), so a
    # word can only be there if its letters occur in the raw command in order.
    # That test is a glob, no process, and can only say "maybe", never "no" wrongly.
    # A glob with several stars is not linear on a long string, so a long command
    # skips the shortcut and simply asks (8 KB: measured under 40 ms; at 130 KB it does not finish).
    D3_UNAME=""
    if [ "${#CMD}" -ge 8192 ]; then
        D3_UNAME=$(uname -s 2>/dev/null)
    else
        case "$CMD" in
            *s*s*h*|*s*c*p*|*r*s*y*n*c*|*s*f*t*p*) D3_UNAME=$(uname -s 2>/dev/null) ;;
        esac
    fi
    case "$D3_UNAME" in
    MINGW*|MSYS*|CYGWIN*)
        US=$'\037'
        if [ -n "${ABF_SPLIT_SEGS-}" ] && [ "${ABF_SPLIT_FOR-}" = "$CMD" ]; then
            # is_launch_command just split exactly this command the same way
            TSEGS=$ABF_SPLIT_SEGS
        else
            TCMD_NB=$CMD
            [[ $CMD == *'<<'* ]] && TCMD_NB=$(awk -f "$HD/strip_heredocs.awk" <<<"$CMD" 2>/dev/null)
            [ -n "$TCMD_NB" ] || TCMD_NB="$CMD"
            TSEGS=$(awk -f "$HD/split_segments.awk" <<<"$TCMD_NB" 2>/dev/null)
        fi
        if [ -z "$TSEGS" ]; then
            TSEGS=$(printf '%s\n' "$TCMD_NB" | sed -E 's/(\|\||&&|[;&|])/\n/g' \
                    | while IFS= read -r l; do printf '%s%s%s\n' "$l" "$US" "$l"; done)
        fi
        # #62: a big command is first cut down by one awk pass to the segments
        # whose quote-free text holds a transport word - the loop's own first test
        # below - so the shell does not walk thousands of here-doc lines. If awk
        # cannot run, every segment goes through the loop.
        if [ "${#TSEGS}" -gt 16384 ]; then
            TCAND=$(awk -F"$US" 'index($2, "ssh") || index($2, "scp") || index($2, "rsync") || index($2, "sftp")' <<<"$TSEGS" 2>/dev/null) \
                && TSEGS=$TCAND
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
        # Known blind spot (#53): a ProxyJump or ProxyCommand set in ~/.ssh/config
        # (or a file named with -F, which IS refused above) cannot be seen from
        # here, and a jump host can still ask for a one-time code even with
        # BatchMode=yes - so the exemption can be wrong for such a host.
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
            for w in ${W[@]+"${W[@]}"}; do
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
                    [ "$pend" = -F ] && bad=1   # #53: a named config can hold a ProxyJump
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
                            case "${w:1}" in *[oJF]*) bad=1 ;; esac
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
            # #62: only a segment that names a transport word can be asked about.
            case "$TV" in *ssh*|*scp*|*rsync*|*sftp*) ;; *) continue ;; esac
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

HERE="$(cd "$HD/.." && pwd)"

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

# In-shell (#34); a newline counts as a line start, as it did for grep.
# Blanks are spelled out because [[:space:]] would also match across a newline.
RE_TW_LAUNCH=$'(^|/|\n)tw[ \t\r\v\f]+launch'
RE_TW_RELAUNCH=$'(^|/|\n)tw[ \t\r\v\f]+runs[ \t\r\v\f]+relaunch'
if [[ $CMD != *--disable-optimization* && $CMD == *launch* && $CMD =~ $RE_TW_LAUNCH ]]; then
    add "no --disable-optimization: Platform right-sizes from run history, which fights a site whose accepted sizes are fixed - a helpfully reduced request can land below what the site will take"
fi

# The same check cannot be made of a relaunch: `tw runs relaunch` has no
# --disable-optimization flag at all (`tw runs relaunch --help`), because it
# reuses whatever the original launch stored. Saying nothing would read as
# "checked, and fine", and warning that the flag is absent would send the user
# to a flag that does not exist - so state which of the two it is. It is not a
# precondition the user can meet, so it does not go in the WARN list.
NOTE=""
if [[ $CMD == *relaunch* && $CMD =~ $RE_TW_RELAUNCH ]]; then
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
