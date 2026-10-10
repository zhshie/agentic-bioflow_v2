#!/bin/bash
# Nothing existing: Claude Code permission rules match a command by its prefix or pattern; none splits a shell line into its commands, reads which arguments name rawdata/results/analysis, or warns on an argument still holding a variable.
#
# PreToolUse/Bash: the deletion guard.
#
#   deny  - rawdata/ results/ analysis/ and .nextflow/plugins/
#   warn  - anything touching sequencing-file extensions, and deleting work/,
#           .nextflow cache, or post-run leftovers (null/, offline_data/,
#           .sendmail_tmp.html) - all recreatable, but need an explicit "確認刪除"
#
# Two fixes over the previous version:
#
# 1. It matched the literal strings "rawdata"/"results" anywhere in the command.
#    /agentic-bioflow:end assigns RESULTS="$RUN_DIR/results" and then writes rm -rf "$RESULTS"
#    - the hook only ever sees the unexpanded "$RESULTS", which does not contain
#      lowercase "results", so the deny never fired on the one command most likely
#      to be issued. Conversely `rm -rf "$RUN_DIR/work" && ls "$RUN_DIR/results"`
#      was denied because "results" appeared somewhere in the line.
#    Now: the command is split into segments, only destructive segments are
#    examined, and only their arguments (not flags, not other commands) are
#    tested. Arguments that still contain a shell variable cannot be resolved
#    here, so they fall through to an explicit "expand it and show me" warning.
#
# 2. .nextflow/plugins/ - the one genuinely unrecoverable target, since compute
#    nodes cannot re-download it - had no rule at all. It appeared only inside the
#    text of a warning. Text is not a rule.
#
# Fail closed when `jq` itself is missing (PITFALLS 28), deliberately. Before
# this check existed, no `jq` meant `echo "$INPUT" | jq -r '.tool_input.command
# // ""'` below silently returned "", the very next line's `[ -n "$CMD" ] ||
# exit 0` fired, and the deletion guard vanished with nothing printed - on a
# freshly installed WSL Ubuntu, or macOS before 15. Exit 2 rather than the
# `deny` JSON this file's own deny() builds: deny() is itself a `jq -n` call,
# so leaning on jq to report jq's own absence would fail the same way.
#
# R2 (2.9): deleting work/ or .nextflow/cache/ needs the user's EXPLICIT
# confirmation (PRINCIPLES.md, the safety net) - previously enforced only by
# warn()'s additionalContext, i.e. prose the model was trusted to honour. That
# branch now returns hookSpecificOutput.permissionDecision: "ask" as well
# (ask(), beside warn()/deny() below), so Claude Code itself pauses rather
# than the model merely being told to. The four hard refusals just below
# (rawdata/, results/, analysis/, .nextflow/plugins/) already use deny() and
# are unchanged - this is additive, not a relaxation of anything that already
# blocked outright.
#
# Sent together with the existing additionalContext text - belt and braces -
# for the same reason confirm_launch.sh does it (see that file): `ask`'s
# behaviour under `bypassPermissions`/`acceptEdits` is UNDOCUMENTED
# (~/.claude/plans/curious-doodling-lightning.md, appendix 2).
#
# This is defence in depth, not a sandbox. The real floor is: originals stay
# read-only, linked not moved, and the execution zone is separate.
# Every symlink in a path resolved, deliberately inlined rather than sourced
# from scripts/utils/portable.sh. A gate that quietly vanishes when a helper is
# missing is worse than a gate that was never written, and this one decides
# whether `rm -rf <link>/*` is about to empty the lab's shared image library.
#
# The GNU spelling first, then a shell walk. `readlink -f` was absent from
# macOS until 12.3; there this returned nothing, and a rule that judges by the
# destination fell back to judging the link's own name, which says nothing.
# Returning the input unchanged would be worse than returning nothing.
resolve_link() {
    readlink -f "$1" 2>/dev/null && return 0   # GNU-ok: the walk below is the fallback
    local p="$1" n=0 b d
    while [ -L "$p" ] && [ "$n" -lt 40 ]; do
        b=$(readlink "$p") || return 1
        case "$b" in /*) p="$b" ;; *) p="$(dirname "$p")/$b" ;; esac
        n=$((n + 1))
    done
    d=$(cd "$(dirname "$p")" 2>/dev/null && pwd -P) || return 1
    printf '%s/%s\n' "${d%/}" "$(basename "$p")"
}

# T1 (2.15, Fixes #15): the same two blind spots confirm_launch.sh documents
# at length - see that file's header for the full reasoning, the GitHub
# report and why unbounded fail-closed became the thing pushing a member
# around this plugin's safety net rather than through it. Short version for
# this file:
#
#   1. jq missing/broken used to refuse every Bash command outright. It now
#      scans the RAW bytes with nothing but a shell `case` for anything that
#      could plausibly be a delete - a bare `case`, not jq or even grep -E,
#      because either could be the very thing also missing. A command that
#      cannot plausibly delete anything is let through unchanged; only a
#      match still blocks, naming the install fix.
#   2. hooks.json's matcher now reaches non-Bash execution tools too. This
#      file already only ever looked at `tool_input.command`; it now also
#      tries the other spellings a non-Bash tool might use for the same
#      idea, and falls back to the same raw-text scan (jq works here; the
#      TOOL's shape is what defeated it) when none of them holds anything.
#
# Shell separators AND the JSON punctuation around them folded to spaces -
# this runs against either a shell command line or a raw, still-quoted JSON
# payload, and a bare `tr -s ';&|()<>'` leaves `"rm` as one token (the
# opening quote glued to the word) that no `*' rm '*` pattern could ever
# match. Folding quotes, braces, brackets, commas, colons and `=` too turns
# either shape into the same flat token soup.
LOOKS_SHAPED_SEP=$'\t\n\r;&|()<>"\'{}[],:='
looks_delete_shaped() {
    local text
    # jq-broken-cleanup: in raw JSON a line break is the two characters `\n`,
    # which glued the next line's verb to an `n` (`\nrm`): the escapes for line
    # breaks and tabs are separators too. If sed or tr cannot run, nothing here
    # can be ruled out.
    text=$(printf '%s' "$1" | sed 's/\\[ntr]/ /g' | tr -s "$LOOKS_SHAPED_SEP" ' ')
    if [ -z "$text" ]; then [ -n "$1" ] && return 0; return 1; fi
    looks_delete_text "$text" && return 0
    # #66: the shell drops a backslash outside quotes, so `r\m`, `\rm` and
    # `--remo\ve-files` are the words they spell without it (in raw JSON the
    # backslash is written twice). The text as written is judged above and stays
    # judged; this is an added copy with every backslash dropped.
    if [[ $1 == *\\* ]]; then
        # Same treatment of the line-break escapes as above - or `hi\nr\\m` would
        # lose its `r` to a `\n` that is not one - but an escaped backslash (`\\`)
        # is taken out first, since `\\rm` is a backslash and `rm`, not a `\r`.
        local EB=$'\001'
        text=$(printf '%s' "$1" | sed "s/\\\\\\\\/$EB/g; s/\\\\[ntr]/ /g" | tr -d "\\\\$EB" | tr -s "$LOOKS_SHAPED_SEP" ' ')
        [ -n "$text" ] && looks_delete_text "$text" && return 0
        # ...and plain, for text that is a command line rather than JSON (there
        # `\rm` is a backslash and `rm`, and no `\r` is a line break).
        text=$(printf '%s' "$1" | tr -d '\\' | tr -s "$LOOKS_SHAPED_SEP" ' ')
        [ -n "$text" ] && looks_delete_text "$text" && return 0
    fi
    return 1
}
looks_delete_text() { # looks_delete_text <flattened text>
    local text="$1"
    case " $text " in
        *' rm '*|*' rmdir '*|*' shred '*|*' mv '*|*'-delete'*|*'--delete'*|*' find '*|*' rsync '*|*'Remove-Item'*|*'rmtree'*)
            return 0 ;;
        # jq-broken-cleanup: the other verbs and shapes the full check knows
        *' unlink '*|*' truncate '*|*' rclone '*|*'--remove-files'*|*' nextflow clean '*|*' nextflow '*' clean '*|*' git '*' clean '*)
            return 0 ;;
        *'rmSync'*|*'unlinkSync'*|*'rmdirSync'*|*'rm_rf'*|*'remove_tree'*|*'os.remove'*|*'os.unlink'*|*'FileUtils.rm'*)
            return 0 ;;
    esac
    return 1
}

# Invariant 13: with jq missing, unable to run, or answering wrongly, the raw text
# is all there is. A command that could be a delete is refused, naming the fix;
# anything else is let through, as before. Exit 2 rather than a JSON verdict:
# building that JSON is itself a jq call.
jq_refuse() { # jq_refuse <what is wrong with jq>
    if looks_delete_shaped "$INPUT"; then
        printf 'BLOCKED: %s, so hooks/confirm_cleanup.sh cannot read\n' "$1" >&2
        cat >&2 <<'EOF'
what this command would delete precisely - and the raw text of this one matches
a deletion-shaped pattern (rm / rmdir / shred / mv / find ... -delete /
rsync ... --delete), so it is refused rather than guessed at. A command that
matches none of those patterns is let through unchanged - this is narrower
than before, not a blanket refusal, though it still cannot see a delete hidden
behind a variable or an alias the way the real check can. confirm_launch.sh
and confirm_walkthrough.sh apply the same scoped rule.

Install jq to get the full check back (this hook will not attempt to), then retry:
  macOS:       brew install jq
  Debian/WSL:  sudo apt install jq
  Windows:     winget install jqlang.jq
EOF
        exit 2
    fi
    exit 0
}

# `command -v jq` would only prove a FILE exists. A jq that cannot run -
# wrong architecture, a missing shared library, or a Windows jq.exe that
# Git Bash finds but cannot execute - passes that check and then fails
# every parse below, which is the exact silent-gate failure this guard
# exists to stop. So ask jq to do its job on the smallest possible input.
# Feature 005 (#48), Constitution 2.0.0: silent in a session that is not using
# this plugin. Asked first, before the jq probe, so that session pays for one
# read of stdin and some string matching and nothing else (#34). See
# hooks/in_use.sh for what "in use" means and why unsure counts as in use. A
# hook directory that cannot supply in_use.sh answers "in use": the gate below
# then runs exactly as it did before this existed.
# Stdin without starting `cat` (#34: every process is expensive under Git Bash). Not `read -d ''`:
# that reads a pipe one byte at a time (a second per 300 KB) and stops at a NUL.
INPUT=$(</dev/stdin)   # no `cat` process; drops NULs and trailing newlines exactly as $(cat) does
HD="${0%/*}"; [ "$HD" = "$0" ] && HD=.
{ . "$HD/in_use.sh"; } 2>/dev/null || abf_in_use() { return 0; }
abf_in_use "$INPUT" "$INPUT" || exit 0

# One jq call reads what this hook needs, and when it works it stands in for the
# "can jq run at all" probe (#34). It is trusted only when it produced exactly one
# record, both fields plain strings, no separator inside them; anything else
# (not JSON, no jq, an object-valued field, two JSON values) goes the way this
# file always went: the probe, then one jq per field.
# jq-broken-cleanup: "produced something" was not enough - a jq that prints `{}`
# or a line of text for everything was read as an answer. The call now also
# prints a token jq has to compute, and is trusted only when the token, the
# two fields, their separators and nothing else came back.
JQ_FAST=0
JQ_OUT=$(jq -js 'if length == 1 then (.[0] | [(.tool_name // ""), (.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // "")] | if all(.[]; type == "string") and (any(.[]; contains("\u001f") or contains("\u0000")) | not) then ("abf-" + "jq-ok\u001f") + (map(sub("\\n+\\z"; "") + "\u001f") | join("")) else empty end) else empty end' <<<"$INPUT" 2>/dev/null) \
  && [ -n "$JQ_OUT" ] && JQ_FAST=1

if [ "$JQ_FAST" = 1 ]; then
    # The fields come as one string, each followed by the separator. They are read out in order:
    # pattern removal (`#*x`, `%%x*`, `##*x`) and ${x//p/} are quadratic in bash on a long string, and a
    # large Write or here-doc then outlasts the hook's timeout (#34); `read` is linear. Trailing
    # newlines were trimmed by jq, as $(jq) did per field.
    JQ_TOKEN=""; JQ_REST=""; JQ_SHAPE=0
    {
        IFS= read -r -d $'\037' JQ_TOKEN && IFS= read -r -d $'\037' TOOL \
          && IFS= read -r -d $'\037' CMD && JQ_SHAPE=1
        IFS= read -r -d '' JQ_REST
    } <<<"$JQ_OUT"
    [ "$JQ_SHAPE" = 1 ] && [ "$JQ_TOKEN" = abf-jq-ok ] && [ "$JQ_REST" = $'\n' ] || JQ_FAST=0
    JQ_OUT=""; JQ_REST=""
fi
if [ "$JQ_FAST" = 0 ]; then
    # `command -v jq` would only prove a file exists, and `jq -e .`'s exit status
    # only that it exited: jq has to read a known field out of a known input.
    # A Windows jq.exe may end the line with CR: allowed.
    JQ_PROBE=$(jq -e .abf -r <<<'{"abf":"jq-ok"}' 2>/dev/null)
    [ "${JQ_PROBE%$'\r'}" = jq-ok ] || jq_refuse "jq is missing, cannot run here, or does not compute correctly"
    TOOL=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // ""' 2>/dev/null)
fi
# jq-broken-cleanup: no command read from a Bash input that plainly carries one
# means jq's answer cannot be trusted (it failed on that field, or answered
# emptily). Another tool's shape is the unreadable-input case below.
RE_RAW_CMD='"(command|script|cmd|commandLine|powershell|input)"[[:space:]]*:[[:space:]]*"[^"]'
if [ -z "$CMD" ] && { [ "$TOOL" = Bash ] || [ -z "$TOOL" ]; } && [[ $INPUT =~ $RE_RAW_CMD ]]; then
    jq_refuse "jq runs here but read no command from an input that has one"
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
        # jq-broken-cleanup: printed only when it is the answer asked for; a jq
        # that prints `{}` (no decision: the call proceeds) gets the fixed ask.
        printf '%s\n' "$o"
    else
        printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"GATE: this hook could not build its own message (jq failed), so it cannot rule this call out. Show the user the full command and confirm it by hand before it runs.","additionalContext":"GATE: the hook could not build its message; treat this call as gated and confirm it with the user."}}'
    fi
}

# T1, part 2: jq is fine, but no field this file knows to check carried a
# command. For Bash that never happens in practice; for anything else the
# tool's own shape is what this file cannot parse - not that there is
# nothing here worth judging. Scoped exactly like the no-jq path above,
# except the message names the tool rather than the missing binary.
if [ "$TOOL" != "Bash" ] && [ -z "$CMD" ]; then
    if looks_delete_shaped "$INPUT"; then
        abf_emit ask "Unreadable tool input from '${TOOL:-<unnamed>}' that looks deletion-shaped." "GATE: this call came from a tool ('${TOOL:-<unnamed>}') whose input this hook does not parse - checked tool_input.command/script/cmd/commandLine/powershell/input, all empty - and the raw payload matches a deletion-shaped pattern. Confirm with the user, by hand, that this does not touch rawdata/, results/, analysis/ or .nextflow/plugins/ before it runs."
    fi
    exit 0
fi
[ -n "$CMD" ] || exit 0

# Drop here-doc bodies: a document containing a path example is not a command
# operating on that path, but the per-line segment scan below could not tell the
# difference. If awk is missing this yields nothing and CMD is left as-is.
# No `<<` means no here-doc, and the stripper then prints every line unchanged,
# so the process is not started for it (#34).
if [[ $CMD == *'<<'* ]]; then
    STRIPPED=$(awk -f "$HD/strip_heredocs.awk" <<<"$CMD" 2>/dev/null)
    [ -n "$STRIPPED" ] && CMD="$STRIPPED"
fi

deny() {
    abf_emit deny "$1" -
    exit 0
}
warn() {
    abf_emit - - "$1"
    exit 0
}
# R2: same message as warn(), but also asks Claude Code itself to pause for
# the user's explicit confirmation (permissionDecision: "ask") instead of
# relying on the model alone to honour additionalContext's prose. Reserved for
# the one branch PRINCIPLES.md actually names as needing explicit
# confirmation - deleting work/ or .nextflow/cache/ - not every warn() below.
ask() {
    abf_emit ask "$1" "$1"
    exit 0
}

# #29: what the command runs is decided by hooks/split_segments.awk, shared
# with hooks/launch_trigger.sh so the two gates cannot disagree. It yields one
# simple command per line - including the contents of $(...), backticks,
# `bash -c '...'`, `ssh host '...'`, `perl -e 'system("...")'`,
# `python3 -c "os.system('...')"` and anything piped into a shell - as
#     <segment as written>\037<segment with quoted text removed>
# The first copy keeps quotes because a target is often quoted
# (`rm -rf "…/results"` passed silently when quoted text was deleted); the
# second drops them because a verb inside a quoted regex is not a verb
# (`grep -n 'A\|rm ' file` was once denied). History: PITFALLS 37.
#
# If awk cannot run, fall back to a plain split and keep going: noisier, but
# still a gate, never an absent one.
US=$'\037'
SEGMENTS=$(awk -f "$HD/split_segments.awk" <<<"$CMD" 2>/dev/null)
if [ -z "$SEGMENTS" ]; then
    SEGMENTS=$(printf '%s\n' "$CMD" | sed -E 's/(\|\||&&|[;&|])/\n/g' | while IFS= read -r l; do printf '%s%s%s\n' "$l" "$US" "$l"; done)
fi
# #66: outside quotes the shell drops a backslash before a letter, so `r\m`,
# `t\ar --remo\ve-files` and `nextflow cl\ean` run what they spell without it.
# Every segment that holds a backslash is judged a second time with all its
# backslashes dropped - an added copy (all three columns), since on Windows a
# backslash is a path separator and the segment as written must still be judged.
# Done before the large-input filter below, so that sees the copy too; and only
# when there is a backslash, so a command without one costs no extra process.
# (The same idea as hooks/launch_trigger.sh, gates-audit2-low.)
if [[ $SEGMENTS == *\\* ]]; then
    # A word that is a Windows drive path (`C:\lab\x`, quoted or not) or a UNC path
    # keeps its backslashes: there they are separators, and `C:labx` is not a path
    # anyone meant (it made a PowerShell `Move-Item` of two such paths ask).
    SEGSB=$(awk -F"$US" -v OFS="$US" '
        function drop(s,   o, w) {
            o = ""
            while (match(s, /[^ \t]+/)) {
                w = substr(s, RSTART, RLENGTH)
                if (w !~ /^["\047]?([A-Za-z]:\\|\\\\[A-Za-z0-9_.$-])/) gsub(/\\/, "", w)
                o = o substr(s, 1, RSTART - 1) w
                s = substr(s, RSTART + RLENGTH)
            }
            return o s
        }
        { print }
        index($0, "\\") { n = $0; $1 = drop($1); $2 = drop($2); $3 = drop($3); if ($0 != n) { $4 = "copy"; print } }' \
        <<<"$SEGMENTS" 2>/dev/null) \
      && [ -n "$SEGSB" ] && SEGMENTS=$SEGSB
    SEGSB=""
fi

# The command word of a segment, lowercased: past sudo/env/command/exec/nohup/
# nice/timeout and their options, VAR=value assignments, a leading backslash
# (`\rm` skips an alias) and a directory (`/bin/rm`). Only the command word
# counts - `grep -rn del results/` names `del`, and must not read as a delete.
cmdword() {
    local W i=0 n w
    read -r -a W <<<"$1"
    n=${#W[@]}
    while [ "$i" -lt "$n" ]; do
        w=${W[$i]}
        case "$w" in
            sudo|env|command|builtin|exec|nohup|time|nice|stdbuf) i=$((i+1)) ;;
            timeout) i=$((i+2)) ;;
            -u|-g|-n|-C|-p) i=$((i+2)) ;;
            -*) i=$((i+1)) ;;
            [A-Za-z_]*=*) i=$((i+1)) ;;
            *) break ;;
        esac
    done
    w=${W[$i]:-}
    w=${w#\\}
    w=${w##*/}
    printf '%s' "$w" | tr 'A-Z' 'a-z'
}

# #35: where a relative target really is. The hook input carries the session's
# working folder ("cwd"); a `cd` earlier in the same command moves it. Both are
# followed in-shell, no process. A cd that cannot be resolved (a variable, ~, -,
# no argument) makes later relative targets unknown, as they were before. A cd
# inside a subshell is treated as lasting for the rest of the command, which can
# only judge more targets, never fewer.
# norm_path <path> -> REPLY: `.` and `..` folded, no trailing slash.
norm_path() {
    local p="$1" pre="" seg res="" parts=() out=()
    case "$p" in
        /*) pre=/; p="${p#/}" ;;
        [A-Za-z]:/*) pre="${p:0:3}"; p="${p:3}" ;;
    esac
    # #62: split without a here-string (a pipe per call, per target)
    local IFS=/
    set -f; parts=($p); set +f
    unset IFS
    for seg in ${parts[@]+"${parts[@]}"}; do
        case "$seg" in
            ''|.) ;;
            ..) [ "${#out[@]}" -gt 0 ] && unset 'out[${#out[@]}-1]' ;;
            *) out+=("$seg") ;;
        esac
    done
    for seg in ${out[@]+"${out[@]}"}; do res="${res:+$res/}$seg"; done
    REPLY="$pre$res"
    [ -n "$REPLY" ] || REPLY=.
}
VCWD=""
RE_CWD='"cwd"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
if [[ $INPUT =~ $RE_CWD ]]; then
    VCWD="${BASH_REMATCH[1]}"; VCWD="${VCWD//\\\\//}"; VCWD="${VCWD//\\//}"
    case "$VCWD" in /*|[A-Za-z]:/*) norm_path "$VCWD"; VCWD="$REPLY" ;; *) VCWD="" ;; esac
fi
# #76, #75: the folder the shell is in is not always the one this gate tracked. VCWD is
# the trunk - what main's own cd / pushd leaves, exactly as before. CANDS holds the other
# folders the shell may be in: a dropped-backslash copy of a cd (`cd res\ults` enters
# results/) and PowerShell's location cmdlets can only ADD to it, never remove from it.
# Every relative target is judged against the trunk and every candidate; each finding only
# ever adds, so the strictest verdict wins. Only main's cd / pushd to a target replaces
# the set: an absolute one clears it, a relative one is followed from every candidate.
CANDS=()
PRE_VCWD=""; PRE_CANDS=()
# dir_rank <folder> -> DR: 2 protected (deny), 1 guarded (ask), 0 neither.
dir_rank() {
    DR=0
    if [[ $1 =~ $RE_PROTECTED ]] || [[ $1 =~ $RE_PLUGINS ]]; then DR=2
    elif [[ $1 =~ $RE_ANY_GUARDED ]]; then DR=1; fi
}
# cd_resolve <base folder> <target> -> REPLY: where a `cd` to <target> lands, the target
# read as written (a backslash as a separator); "" when it cannot be known.
cd_resolve() {
    case "$2" in
        /*|[A-Za-z]:*) norm_path "${2//\\//}" ;;
        *) if [ -n "$1" ]; then join_path "$1" "${2//\\//}"; else REPLY=""; fi ;;
    esac
}
# join_path <normalised folder> <relative word> -> REPLY: the same as norm_path "$1/$2",
# without its cost when the word has no `.`, `..`, `//` or trailing `/` to fold (a
# candidate is always a normalised folder, so the join is already normal).
join_path() {
    case "$1" in */|'') norm_path "$1/$2"; return ;; esac
    case "$2" in
        ''|.|..|./*|../*|*/.|*/..|*/./*|*/../*|*//*|*/) norm_path "$1/$2" ;;
        *) REPLY="$1/$2" ;;
    esac
}
# cand_add <folder>: one more folder the shell may be in (not the trunk, not twice).
cand_add() {
    local c
    [ -n "$1" ] || return 0
    [ "${#1}" -le 1024 ] || return 0
    [ "$1" = "$VCWD" ] && return 0
    for c in ${CANDS[@]+"${CANDS[@]}"}; do [ "$c" = "$1" ] && return 0; done
    CANDS+=("$1"); CANDS_DIRTY=1
}
# cand_add_from_pre <target>: the folder a cd to <target> reaches from the trunk and the
# candidates as they stood before the segment being read.
cand_add_from_pre() {
    local c
    cand_ok "$1" || return 0
    case "$1" in
        ''|-|'~'*|*'$'*|*'`'*) return 0 ;;
        /*|[A-Za-z]:*) cd_resolve "" "$1"; cand_add "$REPLY"; return 0 ;;
    esac
    [ -n "$PRE_VCWD" ] && { cd_resolve "$PRE_VCWD" "$1"; cand_add "$REPLY"; }
    for c in ${PRE_CANDS[@]+"${PRE_CANDS[@]}"}; do cd_resolve "$c" "$1"; cand_add "$REPLY"; done
}
# cand_cap: at most 8 candidates. Over that the harmless ones go first (then the merely
# guarded, newest kept); a protected-looking folder is the last to go, and the trunk is
# not in the set at all, so what main judges is always judged.
cand_cap() {
    [ "${#CANDS[@]}" -gt 8 ] || return 0
    local keep=() pass i n=${#CANDS[@]}
    for pass in 2 1 0; do
        for ((i = n - 1; i >= 0; i--)); do
            [ "${#keep[@]}" -lt 8 ] || break
            dir_rank "${CANDS[$i]}"
            [ "$DR" = "$pass" ] && keep+=("${CANDS[$i]}")
        done
    done
    CANDS=("${keep[@]}"); CANDS_DIRTY=1
}
# Deferred candidate checks. The segment loop judges every word against the trunk
# (VCWD) exactly as main does, at main's cost. The extra checks the candidate folders
# (CANDS) imply are only RECORDED there (defer_rec) and run after the loop (defer_run),
# while time remains: they can only add findings, so stopping them early leaves main's
# verdict plus whatever stricter hits were already found - never an `ask` for running
# out of time. A record holds the version of the candidate list it was made under,
# the kind (w word, f find, d delete / mv source), the word and up to three flags.
# Hard budgets: candidate work only ever ADDS strictness, so it is skipped, never waited
# for, once SECONDS (the time since the hook started) reaches CAND_BUDGET, and for any
# word or folder longer than 1024 characters. Skipping leaves main's verdict. The
# environment variable can only lower the budget (the tests use 0).
CAND_BUDGET=8
case "${ABF_CLEANUP_CAND_BUDGET_S:-}" in
    ''|*[!0-9]*) ;;
    *) [ "$ABF_CLEANUP_CAND_BUDGET_S" -lt "$CAND_BUDGET" ] && CAND_BUDGET=$ABF_CLEANUP_CAND_BUDGET_S ;;
esac
# cand_ok <word or folder>: may candidate work be done for it now?
cand_ok() { [ "$SECONDS" -lt "$CAND_BUDGET" ] && [ "${#1}" -le 1024 ]; }
DEFER=(); SNAP=(); CANDS_VER=0; CANDS_DIRTY=1
SEP1=$'\001'; SEP2=$'\002'
defer_rec() { # defer_rec <kind> <word> [flag1 flag2 flag3]
    [ "${#CANDS[@]}" -gt 0 ] || return 0
    cand_ok "$2" || return 0
    if [ -n "$CANDS_DIRTY" ]; then
        local s="" c
        for c in "${CANDS[@]}"; do s="$s$c$SEP1"; done
        CANDS_VER=$((CANDS_VER + 1)); SNAP[$CANDS_VER]=$s; CANDS_DIRTY=
    fi
    DEFER+=("$CANDS_VER$SEP2$1$SEP2$2$SEP2${3:-}$SEP2${4:-}$SEP2${5:-}")
}
# judge_y <resolved word> <mode>: what judge_word does for one resolved spelling.
judge_y() {
    local Y=$1 M=${2:-}
    case "$M" in
        move)
            [ "$CASE_FOLD" = 1 ] && shopt -s nocasematch
            [[ $Y =~ $RE_PROTECTED ]] && HIT_MV_SOURCE="${HIT_MV_SOURCE}${Y} "
            shopt -u nocasematch ;;
        *)
            judge_delete_target "$Y"
            [ "$M" = rec ] && holds_protected "$Y" \
                && HIT_PROTECTED="${HIT_PROTECTED}${Y} (it holds rawdata/, results/ or analysis/) "
            shopt -s nocasematch
            [[ $Y =~ $RE_SEQEXT ]] && HIT_SEQFILE="${HIT_SEQFILE}${Y} "
            shopt -u nocasematch ;;
    esac
}
defer_run() {
    local rec ver kind w f1 f2 f3 c Y CL=() RL=$DEFER_DEADLINE
    [ "$CAND_BUDGET" -lt "$RL" ] && RL=$CAND_BUDGET
    for rec in ${DEFER[@]+"${DEFER[@]}"}; do
        [ "$SECONDS" -ge "$RL" ] && break
        IFS=$SEP2 read -r ver kind w f1 f2 f3 <<<"$rec"
        case "$w" in /*|[A-Za-z]:*|'~'*|*'$'*|*'`'*) continue ;; esac
        IFS=$SEP1 read -r -a CL <<<"${SNAP[$ver]}"
        for c in ${CL[@]+"${CL[@]}"}; do
            [ "$SECONDS" -ge "$RL" ] && break 2
            join_path "$c" "$w"; Y=$REPLY
            [ "${#Y}" -le 1024 ] || continue
            case "$kind" in
                w) judge_y "$Y" "$f1" ;;
                f) if holds_protected "$Y"; then
                       if [ "$f1" = 0 ] || [ "$f2" = 1 ]; then
                           HIT_PROTECTED="${HIT_PROTECTED}${Y} (find deletes inside the rawdata/, results/ or analysis/ it holds) "
                       else
                           UNRESOLVED="${UNRESOLVED}(find from ${Y}, which holds rawdata/, results/ or analysis/: check that its filter keeps out of them) "
                       fi
                   fi ;;
                d) [ "$f1" = 1 ] && [[ $Y =~ $RE_PROTECTED ]] && HIT_MV_SOURCE="${HIT_MV_SOURCE}${Y} "
                   [ "$f2" = 1 ] && judge_delete_target "$Y"
                   [ "$f3" = 1 ] && holds_protected "$Y" && HIT_PROTECTED="${HIT_PROTECTED}${Y} (it holds rawdata/, results/ or analysis/) " ;;
            esac
        done
    done
}
# #35: is the segment before this one a lister of an explicit path, so a
# `Move-Item` fed from it has a known source? (Pipeline-fed Move-Item.)
LISTER_OK=0

UNRESOLVED=""
HIT_OVERWRITE=""
HIT_SHARED=""
HIT_PROTECTED=""
HIT_PLUGINS=""
HIT_WORK=""
HIT_SEQFILE=""
HIT_LEFTOVER=""
HIT_ROOT=""
HIT_CODE=""
HIT_GLOB=""
HIT_MV_SOURCE=""
HIT_CASE=""
HIT_PERM=""

# #29, round 3: everything below runs inside this shell - `[[ =~ ]]`, `case`
# and parameter expansion - with no `echo | grep` per segment or per target.
# Each of those started two processes, and Git Bash on Windows starts a
# process slowly: a 120-line script took this hook ~50 s, past its timeout,
# at which point Claude Code cancels the hook and RUNS THE COMMAND. The
# only process left per target is resolve_link, and only for a path that
# exists on this machine.
RE_DELVERB='(^|[[:space:]])([^[:space:]]*/)?\\?(rm|rmdir|unlink|shred)([[:space:]]|$)'
# find/rsync/mv are recognised anywhere in the segment, like rm, because a
# wrapper can come first (`srun find … -delete`, `ionice rsync --delete`).
# Round 3 matched them only as the command word and let those through,
# which main had denied (#29, round 4).
RE_FIND_DEL='(^|[[:space:]])([^[:space:]]*/)?\\?find[[:space:]](.*[[:space:]])?(-delete([[:space:]]|$)|-exec(dir)?[[:space:]]+([^[:space:]]*/)?(rm|rmdir|unlink|shred)([[:space:]]|$))'
RE_RSYNC_DEL='(^|[[:space:]])([^[:space:]]*/)?\\?rsync[[:space:]](.*[[:space:]])?--delete'
RE_MV='(^|[[:space:]])([^[:space:]]*/)?\\?mv([[:space:]]|$)'
RE_RSYNC_RSF='(^|[[:space:]])([^[:space:]]*/)?\\?rsync[[:space:]](.*[[:space:]])?--remove-source-files'
# sn1-delete-shapes: also any `.rm(` / `.rmdir(` / `.unlink(` call (node's
# require('fs').rmSync(, fs.promises.rm(, python's pathlib .unlink()), the node
# *Sync forms, Ruby's File/Dir.delete( and FileUtils.rm*/remove* - the last also
# without parentheses, which Ruby allows.
RE_CODE_DEL='(shutil\.rmtree|os\.(remove|unlink|rmdir|removedirs)|(^|[^[:alnum:]_.])(unlink|rmtree|remove_tree|rm_rf|rm_r|remove_dir|remove_entry(_secure)?)|\.(rm|rmdir|unlink|rmSync|rmdirSync|unlinkSync|removeSync|emptyDirSync|rm_rf|rm_r|rm_f)|(File|Dir)\.(delete|unlink|rmdir)|file\.remove|fs\.(rm|rmSync|unlinkSync|rmdirSync)|::Delete)[[:space:]]*\(|FileUtils\.(rm|rm_r|rm_rf|rm_f|rmtree|rmdir|remove[a-z_]*)([^[:alnum:]_]|$)'
RE_DEVNULL='[0-9]*>&?[[:space:]]*/dev/null'
RE_TRUNC='>[[:space:]]*/'
RE_OVERWRITE='(^|/)(rawdata|results)(/|$)'
RE_PLUGINS='(^|/)\.nextflow/plugins(/|$)'
RE_SHARED='(^|/)_references(/|$)|(^|/)[._]?(lab_)?singularity(_cache|_library)?(/|$)'
RE_PROTECTED='(^|/)(rawdata|results|analysis)(/|$)'
RE_ANY_GUARDED='(^|/)(rawdata|results|analysis|_references|work)(/|$)|(^|/)\.nextflow/(plugins|cache)(/|$)'
RE_WORK='^work(/|$)|.+/work(/|$)|(^|/)\.nextflow/(cache|tmp)(/|$)'
RE_LEFTOVER='(^|/)(null|offline_data)(/|$)|(^|/)\.sendmail_tmp\.html$'
RE_SEQEXT='\.(fastq|fq|fasta|fa|fna|bam|cram)(\.gz)?$'
RE_RAW='(^|/)(rawdata|raw_data)(/|$)'
# SN2: Nextflow's own delete of a run's work/ directories.
RE_NFCLEAN='(^|[[:space:]])([^[:space:]]*/)?\\?nextflow(\.exe)?[[:space:]](.*[[:space:]])?clean([[:space:]]|$)'
# sn1-delete-shapes: commands that delete as a side effect of something else -
# archive and remove the originals, a sync tool's delete/move/sync, a link or a
# mode laid over a folder, a redirect that only truncates.
RE_TAR_RM='(^|[[:space:]])([^[:space:]]*/)?\\?(g|bsd)?tar(\.exe)?[[:space:]](.*[[:space:]])?--rem[a-z-]*([[:space:]]|$)'
RE_ZIP_MV='(^|[[:space:]])([^[:space:]]*/)?\\?zip(\.exe)?[[:space:]](.*[[:space:]])?(-[A-Za-z0-9@$]*m[A-Za-z0-9@$]*|--move)([[:space:]]|$)'
RE_RCLONE='(^|[[:space:]])([^[:space:]]*/)?\\?rclone(\.exe)?[[:space:]](.*[[:space:]])?(purge|delete|deletefile|rmdir|rmdirs|move|moveto|sync)([[:space:]]|$)'
RE_LN_F='(^|[[:space:]])([^[:space:]]*/)?\\?ln(\.exe)?[[:space:]](.*[[:space:]])?(-[A-Za-z]*f[A-Za-z]*|--force)([[:space:]]|$)'
RE_INSTALL_D='(^|[[:space:]])([^[:space:]]*/)?\\?install(\.exe)?[[:space:]](.*[[:space:]])?(-[A-Za-z0-9]*d[A-Za-z0-9]*|--directory)([[:space:]]|$)'
RE_PURE_TRUNC='^[[:space:]]*((:|true|false|printf|echo[[:space:]]+-n|cat[[:space:]]+/dev/null)[[:space:]]*)?[0-9]*>([^>&]|$)'
RE_RECURSIVE='(^|[[:space:]])(-[A-Za-z]*[rR][A-Za-z]*|--recursive|/[sS])([[:space:]]|$)'
RE_SEQPAT='\.(fastq|fq|fasta|fa|fna|bam|cram)([^[:alnum:]]|$)'
# A folder the deployment's layout (docs/SETTINGS.md) fills with protected ones:
# a member's area under lab_runs/, projects[/<p>] (rawdata/), runs[/<r>] (results/).
RE_HOLDER='(^|/)(lab_runs(/[^/_.][^/]*)?|projects(/[^/]+)?|runs(/[^/]+)?)$'
RE_GUARDED_LEAF='^(rawdata|results|analysis|_references|work|plugins|cache|[._]?(lab_)?singularity(_cache|_library)?)$'
RE_WINPATH='^([A-Za-z]:/|/mnt/[A-Za-z]/|/cygdrive/[A-Za-z]/)'
# Windows and macOS file systems ignore case: there RESULTS is results/.
case "${OSTYPE:-}" in msys*|cygwin*|darwin*) CASE_FOLD=1 ;; *) CASE_FOLD=0 ;; esac

# One delete target judged against every rule that depends on where it is. Called
# for the word as written, for the word with backslashes read as escapes, and for
# the word resolved against the working folder (#35).
judge_delete_target() {
        local A="$1" An GL NM RP FOLD=$CASE_FOLD CI=0
            # sn1-delete-shapes: a never-delete name in other letter case
            # (RESULTS). Where the file system ignores case (Git Bash, Cygwin,
            # macOS, or a Windows-shaped path from anywhere) it is the same
            # folder: refused like the exact name. Elsewhere it is a different
            # folder that is the same one on such a system: ask. The other
            # rules below (work/, leftovers, globs) keep comparing exactly.
            [[ $A =~ $RE_WINPATH ]] && FOLD=1
            if ! [[ $A =~ $RE_PROTECTED ]] && ! [[ $A =~ $RE_SHARED ]] && ! [[ $A =~ $RE_PLUGINS ]]; then
                shopt -s nocasematch
                [[ $A =~ $RE_PLUGINS ]] && CI=1 && [ "$FOLD" = 1 ] && HIT_PLUGINS="${HIT_PLUGINS}${A} "
                [[ $A =~ $RE_SHARED ]] && CI=1 && [ "$FOLD" = 1 ] && HIT_SHARED="${HIT_SHARED}${A} "
                [[ $A =~ $RE_PROTECTED ]] && CI=1 && [ "$FOLD" = 1 ] && HIT_PROTECTED="${HIT_PROTECTED}${A} "
                shopt -u nocasematch
                [ "$CI" = 1 ] && [ "$FOLD" = 0 ] && HIT_CASE="${HIT_CASE}${A} "
            fi
            [[ $A =~ $RE_PLUGINS ]] && HIT_PLUGINS="${HIT_PLUGINS}${A} "
            # Shared across the whole lab: reference genomes and taxonomy
            # databases (_references/) and the read-only image library. One
            # person deleting these costs everyone else the re-download - tens
            # of GB and hours - and nothing in the deleter's own run tells them
            # that happened. Scale is what makes this a deny rather than a warn.
            # The image library is matched under every spelling it has had
            # here (PITFALLS 17): `_singularity_cache` (nchc.config default),
            # `.singularity_cache` (NXF_SINGULARITY_CACHEDIR here), and
            # `lab_singularity_library`.
            [[ $A =~ $RE_SHARED ]] && HIT_SHARED="${HIT_SHARED}${A} "
            # A name-based rule cannot see the real danger here: a task dir's
            # references/ is a SYMLINK into the shared library, so its own path
            # says nothing about where it points. `rm -rf <link>` only removes
            # the link and is harmless, but `rm -rf <link>/*` deletes the lab's
            # copy. Resolve the path and judge by the destination - only when
            # something is there to resolve, since resolving costs a process.
            # #62: and only when a component of the path (from / for a relative
            # one) is a symbolic link here - resolving costs a program, which per
            # target made `rm -f` of 500 names take a minute on Git Bash.
            if { [ -e "$A" ] || [ -L "$A" ] || [ -e "${A%/*}" ]; } && has_link "$A"; then
                RP=$(resolve_link "$A" 2>/dev/null || true)
                if [ -n "$RP" ] && [ "$RP" != "$A" ] && [[ $RP =~ $RE_SHARED ]]; then
                    HIT_SHARED="${HIT_SHARED}${A} -> ${RP} "
                fi
            fi
            [[ $A =~ $RE_PROTECTED ]] && HIT_PROTECTED="${HIT_PROTECTED}${A} "
            # A glob whose last part could match a protected name (`…/res*`,
            # `…/*`) may take it with it; the shell decides, not us.
            case "$A" in *'*'*|*'?'*|*'['*)
                GL=${A%/}; GL=${GL##*/}
                for NM in rawdata results analysis _references; do
                    case "$NM" in $GL) HIT_GLOB="${HIT_GLOB}${A} "; break ;; esac
                done ;;
            esac
            # "work" must be a component *inside* a path, not the leading one:
            # many clusters put the execution zone under /work/$USER (or
            # /scratch, /data...), so '(^|/)work(/|$)' matched every path in
            # the run dir and the scratch warning fired on everything.
            [[ $A =~ $RE_WORK ]] && HIT_WORK="${HIT_WORK}${A} "
            # A bare filesystem root is never a cleanup target. Cover the common
            # big-storage roots across clusters (not just NCHC's /work), and the
            # execution-zone root itself ($LAB_RUNS_DIR) - deleting that
            # wholesale would wipe every task, not one.
            An="${A%/}"; [ -n "$An" ] || An="/"
            case "$An" in
                ""|"/"|/work|/home|/staging|/scratch|/data|/project|/projects|/work/"$USER"|/scratch/"$USER"|/data/"$USER")
                    HIT_ROOT="${HIT_ROOT}${A} " ;;
            esac
            [ -n "${LAB_RUNS_DIR:-}" ] && [ "$An" = "${LAB_RUNS_DIR%/}" ] && HIT_ROOT="${HIT_ROOT}${A} "
            # Post-/end leftovers: regenerable on the login node, no bearing on
            # results/. "null/" only exists when a launch lost its --outdir, so
            # nf-core wrote pipeline_info under the literal string "null".
            if [ "$A" != /dev/null ] && [[ $A =~ $RE_LEFTOVER ]]; then
                HIT_LEFTOVER="${HIT_LEFTOVER}${A} "
            fi
}

# #62: does any component of a path exist here as a symbolic link? A relative
# path is walked from this shell's folder ($PWD, which may itself pass through
# one). Builtins only: `[ -L ]` per component, no program.
has_link() { # has_link <path>
    local rest="$1" pre="" seg
    case "$rest" in
        /*) pre=/; rest=${rest#/} ;;
        [A-Za-z]:*) ;;
        *) rest="${PWD#/}/$rest"; pre=/ ;;
    esac
    while [ -n "$rest" ]; do
        seg=${rest%%/*}
        if [ "$seg" = "$rest" ]; then rest=""; else rest=${rest#*/}; fi
        [ -n "$seg" ] || continue
        pre=$pre$seg
        [ -L "$pre" ] && return 0
        pre=$pre/
    done
    return 1
}

# sn1-delete-shapes: SW holds a segment's words; REPLY = the index just past the
# first one whose name (quotes and directory dropped) matches the ERE $1.
past_word() { # past_word <ERE of command names>
    local i x
    for ((i = 0; i < ${#SW[@]}; i++)); do
        x=${SW[$i]//[\"\']/}; x=${x##*/}; x=${x#\\}   # backslash-delete-shapes: `\tar`
        if [[ $x =~ ^($1)$ ]]; then REPLY=$((i + 1)); return 0; fi
    done
    REPLY=${#SW[@]}
    return 1
}

# sn1-delete-shapes: does a folder hold protected folders, so that deleting it
# recursively deletes them too? By the deployment's layout (RE_HOLDER), or, for
# an absolute path that exists on this machine, by its own children. Builtins
# only: no process.
holds_protected() { # holds_protected <path>
    local p="${1%/}" c
    [ -n "$p" ] || return 1
    [[ $p =~ $RE_HOLDER ]] && return 0
    case "$p" in /*|[A-Za-z]:/*) ;; *) return 1 ;; esac
    [ -d "$p" ] || return 1
    for c in rawdata results analysis _references projects runs; do
        [ -e "$p/$c" ] && return 0
    done
    return 1
}

# sn1-delete-shapes: a brace word as bash expands it - `res{ults,}` is results and
# res, `{a,{b,c}}` nests, `{1..3}` and `{a..c}` are sequences. BRACE_OUT gets
# every word, at most 64; returns 1 when there would be more (the words are then
# unknown). The old flattening of `{`, `}` and `,` into `/` stays where it was.
brace_expand() {
    local todo=("$1") w i j d k s e c a pre post inner lo hi st n alts
    BRACE_OUT=()
    while [ "${#todo[@]}" -gt 0 ]; do
        w=${todo[${#todo[@]}-1]}; unset 'todo[${#todo[@]}-1]'
        s=-1
        for ((i = 0; i < ${#w}; i++)); do
            [ "${w:i:1}" = '{' ] || continue
            d=0; k=0
            for ((j = i; j < ${#w}; j++)); do
                case "${w:j:1}" in
                    '{') d=$((d + 1)) ;;
                    '}') d=$((d - 1)); [ "$d" = 0 ] && break ;;
                    ',') [ "$d" = 1 ] && k=1 ;;
                esac
            done
            [ "$d" = 0 ] || continue
            inner=${w:i+1:j-i-1}
            if [ "$k" = 1 ] || [[ $inner =~ ^(-?[0-9]+\.\.-?[0-9]+|[A-Za-z]\.\.[A-Za-z])(\.\.-?[0-9]+)?$ ]]; then
                s=$i; e=$j; break
            fi
        done
        if [ "$s" -lt 0 ]; then
            BRACE_OUT+=("$w"); [ "${#BRACE_OUT[@]}" -le 64 ] || return 1
            continue
        fi
        pre=${w:0:s}; post=${w:e+1}; inner=${w:s+1:e-s-1}; alts=()
        if [ "$k" = 1 ]; then
            d=0; a=""
            for ((j = 0; j < ${#inner}; j++)); do
                c=${inner:j:1}
                case "$c" in
                    '{') d=$((d + 1)) ;;
                    '}') d=$((d - 1)) ;;
                    ',') if [ "$d" = 0 ]; then alts+=("$a"); a=""; continue; fi ;;
                esac
                a+=$c
            done
            alts+=("$a")
        else
            lo=${inner%%..*}; hi=${inner#*..}; st=1
            case "$hi" in *..*) st=${hi#*..}; hi=${hi%%..*} ;; esac
            st=${st#-}; [ "$st" = 0 ] && st=1
            if [[ $lo =~ ^[A-Za-z]$ ]]; then
                printf -v lo '%d' "'$lo"; printf -v hi '%d' "'$hi"; n=char
            else
                n=num
            fi
            if [ "$lo" -le "$hi" ]; then
                for ((i = lo; i <= hi; i += st)); do
                    if [ "$n" = char ]; then printf -v a '%x' "$i"; printf -v a "\\x$a"; else a=$i; fi
                    alts+=("$a"); [ "${#alts[@]}" -le 64 ] || return 1
                done
            else
                for ((i = lo; i >= hi; i -= st)); do
                    if [ "$n" = char ]; then printf -v a '%x' "$i"; printf -v a "\\x$a"; else a=$i; fi
                    alts+=("$a"); [ "${#alts[@]}" -le 64 ] || return 1
                done
            fi
        fi
        for a in "${alts[@]}"; do todo+=("$pre$a$post"); done
        [ "${#todo[@]}" -le 64 ] || return 1
    done
    return 0
}

# sn1-delete-shapes: one target word as written: quote characters dropped,
# backslashes read both as Windows separators and as escapes, a brace word
# expanded, a relative path also resolved against the working folder. Each
# spelling is then judged as deleted (mode ""), deleted with all it holds
# ("rec"), or moved out ("move": only rawdata/, results/, analysis/, an ask).
judge_word() { # judge_word <word> [""|rec|move]
    local W=$1 M=${2:-} V E Y X=() SP=()
    case "$W" in ''|-*) return 0 ;; esac
    W=${W//\"/}; W=${W//\'/}
    SP=("${W//\\//}"); [ "${W//\\/}" != "${W//\\//}" ] && SP+=("${W//\\/}")
    for V in "${SP[@]}"; do
        [ -n "$V" ] || continue
        case "$V" in *'$'*|*'`'*) [ "$M" = move ] || UNRESOLVED="${UNRESOLVED}${V} " ;; esac
        BRACE_OUT=("$V")
        if [[ $V == *'{'*'}'* ]] && ! brace_expand "$V"; then
            UNRESOLVED="${UNRESOLVED}(${V}: a brace list too long to read) "; BRACE_OUT=("$V")
        fi
        for E in "${BRACE_OUT[@]}"; do
            X=("$E")
            if [ -n "$VCWD" ]; then
                case "$E" in /*|[A-Za-z]:*|'~'*|*'$'*|*'`'*) ;; *) norm_path "$VCWD/$E"; X+=("$REPLY") ;; esac
            fi
            for Y in "${X[@]}"; do judge_y "$Y" "$M"; done
            defer_rec w "$E" "$M"
        done
    done
}

# A dry run deletes nothing (#35) - but only the options of the command ITSELF
# say so. `nice -n 10 rsync --delete`, `srun -n 1 rsync ...`, `ssh -n h rsync`,
# `sudo -n`, `ionice -n 7`, `timeout -n 5` carry an n that belongs to the
# wrapper; read as rsync's -n it silenced a real delete. So: find the rsync
# word (or `git ... clean`) and look only at the option words after it.
# is_dry_run <quote-free segment>: 0 if it is a dry run of rsync / rclone /
# git clean / nextflow clean.
is_dry_run() {
    local W w b i=0 n seen=0
    # Split without a here-string: it costs a pipe per call, and this runs for
    # every segment (#62). Globbing is off so a `*` stays a word.
    set -f; W=($1); set +f
    n=${#W[@]}
    for ((i = 0; i < n; i++)); do
        w=${W[$i]}; w=${w#\\}; b=${w##*/}
        if [ "$seen" = 0 ]; then
            case "$b" in rsync|rsync.exe|rclone|rclone.exe) seen=1 ;; clean) seen=1 ;; esac
            continue
        fi
        case "$w" in
            --dry-run) return 0 ;;
            --*) ;;
            -[A-Za-z]*) [[ $w == -*n* ]] && return 0 ;;
        esac
    done
    return 1
}

# #62: a large input - a 300 KB python here-doc is 11,000 segments - took this
# loop 23-116 s on native Git Bash, past hooks.json's 30 s, and a hook cancelled
# there lets the call PROCEED. Bash on MSYS slows down per operation once it
# holds a few large strings (measured 18-30x), so no per-segment loop over such
# an input is cheap there. So a large segment list is first filtered by one awk
# pass: a segment is kept when its command word is one the loop handles
# (CW_HANDLED, including the ones that only carry state: cd, the PowerShell
# listers) or its quote-free text matches one of the loop's own trigger regexes
# (RE_TRIGGER, built from the same variables the rules use). Each run of dropped
# segments becomes one `__skipped__` line, which ends a lister pipeline as any
# other command does. A rule added below needs its trigger here too;
# tests/confirm_cleanup_behind_heredoc_test.sh runs every case of
# tests/confirm_cleanup_test.sh through this path to catch one that has not.
# Small inputs (under 8 KB of segments) skip the filter: it is one more process
# (gate_process_count), and their full judgement costs well under a second.
CW_HANDLED='^(__too_deep__|cd|pushd|set-location|sl|chdir|push-location|pop-location|rm|rmdir|unlink|shred|truncate|remove-item|ri|del|erase|rd|xargs|cmd|git|rename|move-item|rename-item|mi|move|rni|ren|nextflow|tar|gtar|bsdtar|zip|rclone|ln|install|[$`].*)$'
RE_TRIGGER="($RE_DELVERB)|($RE_FIND_DEL)|($RE_RSYNC_DEL)|($RE_MV)|($RE_RSYNC_RSF)|($RE_CODE_DEL)|($RE_TRUNC)|($RE_NFCLEAN)"
RE_TRIGGER="$RE_TRIGGER|($RE_TAR_RM)|($RE_ZIP_MV)|($RE_RCLONE)|($RE_LN_F)|($RE_INSTALL_D)|($RE_PURE_TRUNC)"
# The PowerShell listers and pipeline filters (LISTER_OK below) matter only to a
# Move-Item they feed, which is in CW_HANDLED: a run of them is held back and
# kept only when a kept segment follows it. Kept always, `sort` and `ls` made
# every line of a shell script of pipelines a kept segment.
CW_LISTER='^(get-childitem|gci|ls|dir|get-item|gi|where-object|where|\?|select-object|select|sort-object|sort|measure-object|measure)$'
if [ "${#SEGMENTS}" -gt 8192 ]; then
    FILTERED=$(ABF_TRIG="$RE_TRIGGER" ABF_CWRE="$CW_HANDLED" ABF_LIST="$CW_LISTER" awk -F "$US" '
        BEGIN { t = ENVIRON["ABF_TRIG"]; c = ENVIRON["ABF_CWRE"]; l = ENVIRON["ABF_LIST"]
                s = "(skipped)" FS "(skipped)" FS "__skipped__" }
        $3 == "" || $3 ~ c || $2 ~ t { printf "%s", b; b = ""; print; g = 0; next }
        $3 ~ l { b = b $0 "\n"; next }
        { b = "" }
        !g { print s; g = 1 }
        END { if (b != "" && !g) print s }' <<<"$SEGMENTS" 2>/dev/null) \
      && [ -n "$FILTERED" ] && SEGMENTS=$FILTERED
    FILTERED=""
fi

# #62: a deadline of the hook's own, well inside the 30 s hooks.json allows.
# Past it the loop stops and the guard asks, saying so (invariant 13), rather
# than being cut off with the call let through. ABF_CLEANUP_DEADLINE_S can only
# lower it (the tests use 0).
DEADLINE=20
case "${ABF_CLEANUP_DEADLINE_S:-}" in
    ''|*[!0-9]*) ;;
    *) [ "$ABF_CLEANUP_DEADLINE_S" -lt "$DEADLINE" ] && DEADLINE=$ABF_CLEANUP_DEADLINE_S ;;
esac
# The deferred candidate checks (defer_run) have a deadline of their own: they only add
# findings, so past it they stop and the verdict stands as it is. ABF_CLEANUP_DEFER_DEADLINE_S
# can only lower it (the tests use 0).
DEFER_DEADLINE=$DEADLINE
[ "$DEFER_DEADLINE" -le 15 ] || DEFER_DEADLINE=15
case "${ABF_CLEANUP_DEFER_DEADLINE_S:-}" in
    ''|*[!0-9]*) ;;
    *) [ "$ABF_CLEANUP_DEFER_DEADLINE_S" -lt "$DEFER_DEADLINE" ] && DEFER_DEADLINE=$ABF_CLEANUP_DEFER_DEADLINE_S ;;
esac
NSEG=0
TIMED_OUT=0
while IFS="$US" read -r SEG VSEG CW COPY; do
    # #66: a segment marked `copy` is the dropped-backslash copy of the one just
    # before it. It is judged, but it must never change what the segments after it
    # are judged against: the state the loop carries from one segment to the next
    # (VCWD, the folder a `cd` moved to; LISTER_OK, whether a lister named a known
    # path - the only two it writes besides the accumulated findings, which only
    # ever add) is put back as it stood when the copy started. Without this
    # `cd <run>/results\old` set the folder from the original and the copy then
    # moved it to `<run>/resultsold`, so a delete after it went unjudged.
    #
    # #76: a copy may only tighten the lister verdict: the copy of
    # `Get-ChildItem res\ults` reads the protected `results`, which clears LISTER_OK,
    # and it must stay cleared; a copy can never raise it. And the candidates a copy
    # adds (cand_add_from_pre) are read from the state before the segment it copies.
    if [ -n "${COPY_SAVED-}" ]; then
        VCWD=$COPY_VCWD
        if [ "$LISTER_OK" = 1 ] && [ "$COPY_LISTER" = 1 ]; then LISTER_OK=1; else LISTER_OK=0; fi
        COPY_SAVED=
    fi
    if [ -n "$COPY" ]; then
        COPY_VCWD=$VCWD; COPY_LISTER=$LISTER_OK; COPY_SAVED=1
    else
        PRE_VCWD=$VCWD; PRE_CANDS=(${CANDS[@]+"${CANDS[@]}"})
    fi
    [ -n "$SEG" ] || continue
    # #62: past the deadline, stop and ask (see DEADLINE above).
    if [ "$SECONDS" -ge "$DEADLINE" ]; then TIMED_OUT=1; break; fi
    NSEG=$((NSEG + 1))
    # A run of segments the large-input filter dropped: like any other command
    # word, it ends a lister pipeline.
    if [ "$CW" = __skipped__ ]; then LISTER_OK=0; continue; fi

    # Deleting and overwriting are different acts and must not share a verdict.
    # They used to: a redirect set the same DESTRUCTIVE flag as rm, so its target
    # was tested against the never-delete list. That made
    #   cat > /.../analysis/de_analysis.R <<'EOF'
    # a DENY - blocking the step where /agentic-bioflow:downstream writes the R
    # code it just generated, which is that command's entire purpose. Writing a
    # file into analysis/ is the normal case there, not an attack on it.
    DESTRUCTIVE=0   # a real delete
    TRUNCATE=0      # a redirect: creates or overwrites, never removes a tree
    MOVE_ONLY=0
    VARCMD=0        # the command word is a variable or substitution
    # The third column from split_segments.awk; computed here only on the
    # awk-less fallback. Quote CHARACTERS are dropped, not quoted text:
    # `"/bin/rm" -rf …` quotes the command word itself.
    [ -n "$CW" ] || CW=$(cmdword "$(printf '%s' "$SEG" | tr -d "\"'")")

    if [ "$CW" = "__too_deep__" ]; then
        UNRESOLVED="${UNRESOLVED}(a command nested too deeply to read) "
        continue
    fi

    # #35: follow `cd`, and remember whether this segment is a lister of an
    # explicit, unprotected path (for a pipeline-fed Move-Item two segments on).
    PREV_LISTER_OK=$LISTER_OK
    case "$CW" in
        cd|pushd)
            CDT=""; CDF=0
            read -r -a CDW <<<"${SEG//[\"\']/}"
            for CDX in ${CDW[@]+"${CDW[@]}"}; do
                if [ "$CDF" = 0 ]; then [ "$CDX" = "$CW" ] && CDF=1; continue; fi
                case "$CDX" in -*) continue ;; esac
                CDT="$CDX"; break
            done
            # #76: main's own cd / pushd is the only thing that replaces the set of
            # candidate folders (CANDS). The trunk (VCWD) moves exactly as it always did.
            # A dropped-backslash copy never moves the trunk (#74); it only ADDS the
            # folder the shell reaches when the backslash is dropped, from the
            # candidates as they were before the segment it copies.
            if [ -n "$COPY" ]; then
                cand_add_from_pre "$CDT"; cand_cap
            else
                case "$CDT" in
                    ''|-|'~'*|*'$'*|*'`'*) VCWD="" ;;
                    /*|[A-Za-z]:*) norm_path "${CDT//\\//}"; VCWD="$REPLY"; CANDS=(); CANDS_DIRTY=1 ;;
                    *)
                        if [ -n "$VCWD" ]; then norm_path "$VCWD/${CDT//\\//}"; VCWD="$REPLY"; fi
                        # a relative target is followed from every candidate
                        DC_OLD=(${CANDS[@]+"${CANDS[@]}"}); CANDS=(); CANDS_DIRTY=1
                        if cand_ok "$CDT"; then
                            for DC_C in ${DC_OLD[@]+"${DC_OLD[@]}"}; do
                                cd_resolve "$DC_C" "$CDT"; cand_add "$REPLY"
                            done
                        fi ;;
                esac
                cand_cap
            fi
            LISTER_OK=0
            continue ;;
        set-location|sl|chdir|push-location|pop-location)
            # #75: PowerShell's location cmdlets. Under Bash they are not built-ins and
            # under PowerShell they may fail, sit behind a condition or take a form this
            # gate cannot read, so they can only ADD the folder they name as a candidate;
            # they never remove one. Pop-Location, like popd, adds nothing. The segment
            # then goes on through the checks main runs on it.
            CDT=""; CDF=0; DC_TAKE=0; DC_SKIP=0
            if [ "$CW" != pop-location ]; then
                read -r -a CDW <<<"${SEG//[\"\']/}"
                shopt -s nocasematch
                for CDX in ${CDW[@]+"${CDW[@]}"}; do
                    if [ "$CDF" = 0 ]; then
                        DC_W=${CDX#\\}; DC_W=${DC_W##*/}
                        [[ $DC_W == "$CW" ]] && CDF=1
                        continue
                    fi
                    # -Path / -LiteralPath value (also -Path:value), else the first word
                    # that is not an option; -StackName takes a word of its own.
                    if [ "$DC_TAKE" = 1 ]; then CDT=$CDX; break; fi
                    if [ "$DC_SKIP" = 1 ]; then DC_SKIP=0; continue; fi
                    case "$CDX" in
                        -path|-literalpath|-lp|-pspath) DC_TAKE=1 ;;
                        -path:?*|-literalpath:?*|-lp:?*|-pspath:?*) CDT=${CDX#*:}; break ;;
                        -stackname) DC_SKIP=1 ;;
                        -*) ;;
                        *) CDT=$CDX; break ;;
                    esac
                done
                shopt -u nocasematch
                case "$CDT" in
                    ''|-|'~'*|*'$'*|*'`'*|*'*'*|*'?'*|*'['*|*'('*|*')'*|'@'*) ;;
                    *) cand_add_from_pre "$CDT"; cand_cap ;;
                esac
            fi
            LISTER_OK=0 ;;
        get-childitem|gci|ls|dir|get-item|gi)
            LISTER_OK=0; LARGS=0
            read -r -a LW <<<"${SEG//[\"\']/}"
            for ((li = 1; li < ${#LW[@]}; li++)); do
                LX=${LW[$li]}
                case "$LX" in -*|'') continue ;; esac
                LX=${LX//\\//}
                case "$LX" in
                    *'$'*|*'`'*|*'*'*|*'?'*|*'['*|..|*/..|*/../*|../*) LARGS=-99 ;;
                    *) [[ $LX =~ $RE_ANY_GUARDED ]] && LARGS=-99 || LARGS=$((LARGS + 1)) ;;
                esac
            done
            [ "$LARGS" -ge 1 ] && LISTER_OK=1 ;;
        where-object|where|'?'|select-object|select|sort-object|sort|measure-object|measure)
            LISTER_OK=$PREV_LISTER_OK ;;
        *) LISTER_OK=0 ;;
    esac

    # The delete verbs rm/rmdir/unlink/shred count as a whole word anywhere
    # outside quotes, because a wrapper can come first: `srun rm`, `singularity
    # exec x.sif rm`, `parallel rm ::: …`, `flock l rm`, `doas rm`. Round 2
    # accepted only the command word and let every one of those through,
    # which main had denied. (`\rm` and `/bin/rm` are covered by the optional
    # path and backslash.) Words that are ordinary elsewhere count only as the
    # command word: truncate, find/rsync/xargs with their delete forms, and
    # PowerShell/cmd's Remove-Item - plus ri/del/erase/rd, which exist only in
    # PowerShell and cmd, so under Bash `del results` in a python body is
    # python, not a delete.
    [[ $VSEG =~ $RE_DELVERB ]] && DESTRUCTIVE=1
    case "$CW" in
        rm|rmdir|unlink|shred|truncate|remove-item) DESTRUCTIVE=1 ;;
        ri|del|erase|rd) case "$TOOL" in ""|Bash) ;; *) DESTRUCTIVE=1 ;; esac ;;
        xargs)
            # `xargs rm` takes its targets from stdin, which this hook never sees.
            [ "$DESTRUCTIVE" = 1 ] && UNRESOLVED="${UNRESOLVED}(targets read by xargs from stdin) " ;;
        '$'*|'`'*) VARCMD=1 ;;
    esac
    # A delete written as code - a python/R/perl/node/.NET call. Judged on the
    # quote-free copy with its parenthesis, so searching for the name (grep
    # 'os.remove(') or quoting it in a message is not one.
    [[ $VSEG =~ $RE_CODE_DEL ]] && HIT_CODE="${HIT_CODE}${SEG} "
    # "2>/dev/null" appears in nearly every snippet this plugin's own commands
    # tell the assistant to run, and an early pattern ('>[[:space:]]*/')
    # matched it - so read-only `du`/`ls`/`jq` lines were classified
    # destructive. Drop /dev/null redirects before testing; one stripped copy
    # feeds both the truncation test and the target list, so `2>/dev/null` can
    # never reach the leftover rule's `null` pattern either. A `>` inside
    # quotes is text, not a redirect: judged on the quote-free copy.
    SEG_NR=$SEG; while [[ $SEG_NR =~ $RE_DEVNULL ]]; do SEG_NR=${SEG_NR/"${BASH_REMATCH[0]}"/}; done
    V_NR=$VSEG;  while [[ $V_NR =~ $RE_DEVNULL ]]; do V_NR=${V_NR/"${BASH_REMATCH[0]}"/}; done
    [[ $V_NR =~ $RE_TRUNC ]] && TRUNCATE=1
    [[ $VSEG =~ $RE_FIND_DEL ]] && DESTRUCTIVE=1
    # A dry run deletes nothing (#35): `--dry-run`, or an n among the short options.
    DRYRUN=0
    is_dry_run "$VSEG" && DRYRUN=1
    # SN2 (nextflow-clean-unconfirmed): `nextflow clean -f` deletes a run's task
    # directories under work/ - the same act as rm -rf work/, so the same ask.
    # Its other words are run names, not paths. Without -f (Nextflow refuses) or
    # with -n / -dry-run (is_dry_run reads the options after `clean`) it deletes
    # nothing. The subcommand is the first word after `nextflow` that is not a
    # global option or that option's value (`nextflow -log x.log clean -f`).
    if [ "$CW" = nextflow ] || [[ $VSEG =~ $RE_NFCLEAN ]]; then
        set -f; NFW=(${SEG//[\"\']/}); set +f
        NFI=0; NFS=""; NFF=0
        while [ "$NFI" -lt "${#NFW[@]}" ]; do
            NFX=${NFW[$NFI]}; NFX=${NFX##*/}; NFX=${NFX#\\}; NFI=$((NFI + 1))
            case "$NFX" in nextflow|nextflow.exe) break ;; esac
        done
        while [ "$NFI" -lt "${#NFW[@]}" ]; do
            NFX=${NFW[$NFI]}; NFI=$((NFI + 1))
            case "$NFX" in
                -log|-c|-C|-config|-syslog|-trace) NFI=$((NFI + 1)) ;;
                -*) ;;
                *) NFS=$NFX; break ;;
            esac
        done
        if [ "$NFS" = clean ]; then
            for ((; NFI < ${#NFW[@]}; NFI++)); do
                case "${NFW[$NFI]}" in -f|-force|--force) NFF=1 ;; esac
            done
            [ "$NFF" = 1 ] && [ "$DRYRUN" = 0 ] && HIT_WORK="${HIT_WORK}(nextflow clean -f: the run's task directories under work/) "
            continue
        fi
    fi
    # variable-nextflow-clean: a command word held in a variable (`N=nextflow;
    # $N clean -f`) whose subcommand is `clean` with -f may be that same delete.
    if [ "$VARCMD" = 1 ] && [ "$DRYRUN" = 0 ]; then
        set -f; NFW=(${SEG//[\"\']/}); set +f
        NFI=0; NFS=""; NFF=0
        while [ "$NFI" -lt "${#NFW[@]}" ]; do
            NFX=${NFW[$NFI]}; NFI=$((NFI + 1))
            case "$NFX" in '$'*|'`'*) break ;; esac
        done
        while [ "$NFI" -lt "${#NFW[@]}" ]; do
            NFX=${NFW[$NFI]}; NFI=$((NFI + 1))
            case "$NFX" in -*) ;; *) NFS=$NFX; break ;; esac
        done
        if [ "$NFS" = clean ]; then
            for ((; NFI < ${#NFW[@]}; NFI++)); do
                case "${NFW[$NFI]}" in -f|-force|--force) NFF=1 ;; esac
            done
            [ "$NFF" = 1 ] && HIT_WORK="${HIT_WORK}(unknown command '${CW}' clean -f: if it is nextflow, the run's task directories under work/) "
        fi
    fi
    [[ $VSEG =~ $RE_RSYNC_DEL ]] && [ "$DRYRUN" = 0 ] && DESTRUCTIVE=1
    # cmd /c rd|del|erase|rmdir ... under the Bash tool (#35): those verbs are
    # ordinary words in Bash, but after cmd's /c they are the command.
    if [ "$CW" = cmd ]; then
        CMDPLAIN=${SEG//\"/}; CMDPLAIN=${CMDPLAIN//\'/}
        [[ $CMDPLAIN =~ (^|[[:space:]])/[cCkK][[:space:]]+(rd|rmdir|del|erase|ri)([[:space:]]|$) ]] && DESTRUCTIVE=1
    fi
    # git clean -f removes untracked files; which ones depends on the repository,
    # which this hook cannot see (#35). A dry run (-n / --dry-run) removes none.
    if [ "$CW" = git ] && [ "$DRYRUN" = 0 ] \
       && [[ $VSEG =~ (^|[[:space:]])clean([[:space:]]|$) ]] \
       && [[ $VSEG =~ (^|[[:space:]])(-[A-Za-z]*f[A-Za-z]*|--force)([[:space:]]|$) ]]; then
        DESTRUCTIVE=1
        UNRESOLVED="${UNRESOLVED}(git clean: removes untracked files, which ones depends on the repository) "
    fi

    # sn1-delete-shapes: commands that delete as a side effect of something else.
    # Each is read for the words it really removes, which are judged as an rm
    # target would be (judge_word). Additive: the rules after this still run.
    SHAPE=""
    if [[ $VSEG =~ $RE_TAR_RM ]]; then SHAPE=tar
    elif [[ $VSEG =~ $RE_ZIP_MV ]]; then SHAPE=zip
    elif [[ $VSEG =~ $RE_RCLONE ]]; then SHAPE=rclone
    elif [[ $VSEG =~ $RE_LN_F ]]; then SHAPE=ln
    elif [[ $VSEG =~ $RE_INSTALL_D ]]; then SHAPE=install
    else
        # the command word itself quoted (`"tar" ...`): the quote-free copy lost it
        case "$CW" in tar|gtar|bsdtar|zip|rclone|ln|install) SEGQ=${SEG//[\"\']/} ;; esac
        case "$CW" in
            tar|gtar|bsdtar) [[ $SEGQ =~ $RE_TAR_RM ]] && SHAPE=tar ;;
            zip) [[ $SEGQ =~ $RE_ZIP_MV ]] && SHAPE=zip ;;
            rclone) [[ $SEGQ =~ $RE_RCLONE ]] && SHAPE=rclone ;;
            ln) [[ $SEGQ =~ $RE_LN_F ]] && SHAPE=ln ;;
            install) [[ $SEGQ =~ $RE_INSTALL_D ]] && SHAPE=install ;;
        esac
    fi
    [ -n "$SHAPE" ] && { set -f; SW=($SEG_NR); set +f; }
    case "$SHAPE" in
    tar)
        # tar --remove-files deletes every source once archived: not the archive
        # (-f/--file, or `f` in an old-style first word), not the -C folder or
        # another option's value. -T/--files-from: the sources are in a file.
        past_word 'g?tar|bsdtar|tar\.exe'; XI=$REPLY; XSKIP=0; XFIRST=1
        for ((; XI < ${#SW[@]}; XI++)); do
            X=${SW[$XI]}; XQ=${X//[\"\']/}
            if [ "$XSKIP" = 1 ]; then XSKIP=0; XFIRST=0; continue; fi
            case "$XQ" in
                -T|--files-from) UNRESOLVED="${UNRESOLVED}(tar --remove-files: the files listed in ${SW[$((XI + 1))]:-?}) "; XSKIP=1 ;;
                --files-from=*) UNRESOLVED="${UNRESOLVED}(tar --remove-files: the files listed in ${XQ#*=}) " ;;
                -f|--file|-C|--directory|-X|--exclude-from|-g|--listed-incremental|-b|--blocking-factor|-H|--format|-K|--starting-file|-L|--tape-length|-N|--newer|--after-date|-V|--label|--exclude|-I|--use-compress-program) XSKIP=1 ;;
                --*) ;;
                -?*) case "$XQ" in
                         *T) UNRESOLVED="${UNRESOLVED}(tar --remove-files: the files listed in ${SW[$((XI + 1))]:-?}) "; XSKIP=1 ;;
                         *[fCXgbHKLNVI]) XSKIP=1 ;;
                     esac ;;
                *) if [ "$XFIRST" = 1 ] && [[ $XQ =~ ^[A-Za-z]+$ ]]; then
                       [[ $XQ == *f* ]] && XSKIP=1
                   else
                       judge_word "$X" rec
                   fi ;;
            esac
            XFIRST=0
        done ;;
    zip)
        # zip -m deletes every name after the zip file once added; not -x/-i
        # patterns or another option's value. -@: the names come from stdin.
        past_word 'zip|zip\.exe'; XI=$REPLY; XSKIP=0; XF=0; XPAT=0
        for ((; XI < ${#SW[@]}; XI++)); do
            X=${SW[$XI]}; XQ=${X//[\"\']/}
            if [ "$XSKIP" = 1 ]; then XSKIP=0; continue; fi
            case "$XQ" in
                -x|-i|--exclude|--include) XPAT=1; continue ;;
                -@|--names-stdin) UNRESOLVED="${UNRESOLVED}(zip -m: the names it reads from stdin) "; continue ;;
                -b|-n|-t|-tt|-P|-Z|-s|-sp|-O|--temp-path|--suffixes|--from-date|--before-date|--password|--compression-method|--split-size|--output-file) XSKIP=1; continue ;;
                -?*) XPAT=0; continue ;;
            esac
            [ "$XPAT" = 1 ] && continue
            if [ "$XF" = 0 ]; then XF=1; continue; fi
            judge_word "$X" rec
        done ;;
    rclone)
        # purge/delete/deletefile/rmdir/rmdirs remove every path; sync deletes in
        # its destination what the source lacks; move/moveto empty their sources
        # (an mv source: ask, E9). A `remote:` prefix is judged with and without.
        if [ "$DRYRUN" = 0 ]; then
            past_word 'rclone|rclone\.exe'; XI=$REPLY; XV=""; XP=()
            for ((; XI < ${#SW[@]}; XI++)); do
                XQ=${SW[$XI]//[\"\']/}
                if [ -z "$XV" ]; then
                    case "$XQ" in purge|delete|deletefile|rmdir|rmdirs|move|moveto|sync) XV=$XQ ;; esac
                    continue
                fi
                case "$XQ" in -*) continue ;; esac
                XP+=("${SW[$XI]}")
            done
            for ((XI = 0; XI < ${#XP[@]}; XI++)); do
                case "$XV" in
                    sync) [ "$XI" = $((${#XP[@]} - 1)) ] || continue; XM=rec ;;
                    move|moveto) [ "$XI" -lt $((${#XP[@]} - 1)) ] || continue; XM=move ;;
                    *) XM=rec ;;
                esac
                XQ=${XP[$XI]//[\"\']/}
                if [[ $XQ =~ ^[A-Za-z0-9_.-]+: ]] && ! [[ $XQ =~ ^[A-Za-z]:[/\\] ]]; then
                    # a remote path is relative to the remote's root, not to
                    # the working folder (a drive letter is a local path)
                    XCWD=$VCWD; XCANDS=(${CANDS[@]+"${CANDS[@]}"}); VCWD=""; CANDS=(); CANDS_DIRTY=1
                    judge_word "$XQ" "$XM"; judge_word "${XQ#*:}" "$XM"
                    VCWD=$XCWD; CANDS=(${XCANDS[@]+"${XCANDS[@]}"}); CANDS_DIRTY=1
                else
                    judge_word "${XP[$XI]}" "$XM"
                fi
            done
        fi ;;
    ln)
        # ln -f replaces its link name, and with -n/-T even a link to a folder:
        # rawdata/ is often exactly that. Without -n/-T a folder is written INTO
        # (staging a link in rawdata/), which stays quiet. Judged only when the
        # link name IS a guarded folder.
        past_word 'ln|ln\.exe'; XI=$REPLY; XSKIP=0; XT=0; XN=0; XA=()
        for ((; XI < ${#SW[@]}; XI++)); do
            XQ=${SW[$XI]//[\"\']/}
            if [ "$XSKIP" = 1 ]; then XSKIP=0; continue; fi
            case "$XQ" in
                -t|--target-directory) XT=1; XSKIP=1 ;;
                --target-directory=*) XT=1 ;;
                -S|--suffix) XSKIP=1 ;;
                --no-dereference|--no-target-directory) XN=1 ;;
                --*) ;;
                -?*) case "$XQ" in *[nT]*) XN=1 ;; esac
                     case "$XQ" in *t) XT=1; XSKIP=1 ;; *t*) XT=1 ;; *S) XSKIP=1 ;; esac ;;
                *) XA+=("${SW[$XI]}") ;;
            esac
        done
        if [ "$XT" = 0 ] && [ "$XN" = 1 ] && [ "${#XA[@]}" -ge 1 ]; then
            if [ "${#XA[@]}" = 1 ]; then X=${XA[0]//[\"\']/}; X=${X%/}; X=${X##*/}; else X=${XA[${#XA[@]}-1]}; fi
            XQ=${X//[\"\']/}; XQ=${XQ//\\//}; XQ=${XQ%/}
            shopt -s nocasematch
            [[ ${XQ##*/} =~ $RE_GUARDED_LEAF ]] && XL=1 || XL=0
            shopt -u nocasematch
            [ "$XL" = 1 ] && judge_word "$XQ"
        fi ;;
    install)
        # install -d on an existing folder sets its mode/owner: nothing removed,
        # but -m 000 locks everyone out. Asked when it names a protected folder
        # itself and sets a mode, owner or group.
        past_word 'install|install\.exe'; XI=$REPLY; XSKIP=0; XM=0; XA=()
        for ((; XI < ${#SW[@]}; XI++)); do
            XQ=${SW[$XI]//[\"\']/}
            if [ "$XSKIP" = 1 ]; then XSKIP=0; continue; fi
            case "$XQ" in
                -m|-o|-g|--mode|--owner|--group) XM=1; XSKIP=1 ;;
                --mode=*|--owner=*|--group=*) XM=1 ;;
                -t|-S|--target-directory|--suffix) XSKIP=1 ;;
                --*) ;;
                -?*) case "$XQ" in *[mog]*) XM=1 ;; esac
                     case "$XQ" in *[mogtS]) XSKIP=1 ;; esac ;;
                *) XA+=("$XQ") ;;
            esac
        done
        if [ "$XM" = 1 ]; then
            for X in ${XA[@]+"${XA[@]}"}; do
                X=${X//\\//}; X=${X%/}
                shopt -s nocasematch
                if [[ ${X##*/} =~ $RE_GUARDED_LEAF ]] \
                   && { [[ $X =~ $RE_PROTECTED ]] || [[ $X =~ $RE_SHARED ]] || [[ $X =~ $RE_PLUGINS ]]; }; then
                    HIT_PERM="${HIT_PERM}${X} "
                fi
                shopt -u nocasematch
            done
        fi ;;
    esac

    # sn1-delete-shapes: a redirect with nothing written through it (`: > f`,
    # `> f`, `true > f`, `cat /dev/null > f`) is `truncate -s 0 f`, and is judged
    # the same way. `>>` appends, and anything else that writes stays an overwrite.
    if [[ $VSEG =~ $RE_PURE_TRUNC ]]; then
        set -f; SW=($SEG_NR); set +f
        XP=(); XO=""; XN=0
        for X in ${SW[@]+"${SW[@]}"}; do
            if [ "$XN" = 1 ]; then XP+=("$X"); XN=0; continue; fi
            case "$X" in
                '>>'*|[0-9]'>>'*|'&>>'*) ;;
                '>'|'>|'|[0-9]'>'|[0-9]'>|'|'&>') XN=1 ;;
                '>&'*|[0-9]'>&'*) ;;
                '>|'?*) XP+=("${X#>|}") ;;
                '>'?*) XP+=("${X#>}") ;;
                [0-9]'>|'?*) XP+=("${X#?>|}") ;;
                [0-9]'>'?*) XP+=("${X#?>}") ;;
                '&>'?*) XP+=("${X#&>}") ;;
                *) XO="$XO $X" ;;
            esac
        done
        case "${XO# }" in
            ''|:|true|false|'cat /dev/null'|'echo -n'|"echo -n ''"|'echo -n ""'|printf|"printf ''"|'printf ""')
                for X in ${XP[@]+"${XP[@]}"}; do judge_word "$X"; done ;;
        esac
    fi

    # sn1-delete-shapes: a find that deletes is judged by where it starts. From a
    # folder that holds protected ones it deletes inside them: refused when it has
    # no name/path/depth filter or one aimed at sequencing files, asked about
    # otherwise. A sequencing-file filter from a folder this guard cannot place
    # is asked about too (/tmp and $TMPDIR excepted, as before).
    if [ "$DESTRUCTIVE" = 1 ] && [[ $VSEG =~ $RE_FIND_DEL ]]; then
        set -f; SW=($SEG_NR); set +f
        past_word 'find|find\.exe'; XI=$REPLY; XR=(); XF=0; XS=0; XE=0; XPREV=""
        while [ "$XI" -lt "${#SW[@]}" ]; do
            case "${SW[$XI]}" in -H|-L|-P|-O*) XI=$((XI + 1)) ;; -D) XI=$((XI + 2)) ;; *) break ;; esac
        done
        while [ "$XI" -lt "${#SW[@]}" ]; do
            XQ=${SW[$XI]//[\"\']/}
            case "$XQ" in -*|'('|'!'|'\('|'\!'|,) break ;; esac
            XR+=("$XQ"); XI=$((XI + 1))
        done
        for ((; XI < ${#SW[@]}; XI++)); do
            XQ=${SW[$XI]//[\"\']/}
            if [ "$XE" = 1 ]; then case "$XQ" in ';'|'\;'|+) XE=0 ;; esac; continue; fi
            case "$XPREV" in
                -name|-iname|-path|-ipath|-wholename|-iwholename|-regex|-iregex|-lname|-ilname)
                    shopt -s nocasematch; [[ $XQ =~ $RE_SEQPAT ]] && XS=1; shopt -u nocasematch ;;
            esac
            case "$XQ" in
                -exec|-execdir|-ok|-okdir) XE=1 ;;
                -name|-iname|-path|-ipath|-wholename|-iwholename|-regex|-iregex|-lname|-ilname|-maxdepth|-prune) XF=1 ;;
            esac
            XPREV=$XQ
        done
        [ "${#XR[@]}" -gt 0 ] || XR=(.)
        for X in "${XR[@]}"; do
            X=${X//\\//}; XA=("$X")
            if [ -n "$VCWD" ]; then
                case "$X" in /*|[A-Za-z]:*|'~'*|*'$'*|*'`'*) ;; *) norm_path "$VCWD/$X"; XA+=("$REPLY") ;; esac
            fi
            defer_rec f "$X" "$XF" "$XS"
            XH=0; XW=0; XT=0
            for Y in "${XA[@]}"; do
                holds_protected "$Y" && XH=1
                [[ $Y =~ $RE_WORK ]] && XW=1
                case "$Y/" in /tmp/*|/var/tmp/*|"${TMPDIR:-/tmp}"/*) XT=1 ;; esac
            done
            if [ "$XH" = 1 ]; then
                if [ "$XF" = 0 ] || [ "$XS" = 1 ]; then
                    HIT_PROTECTED="${HIT_PROTECTED}${X} (find deletes inside the rawdata/, results/ or analysis/ it holds) "
                else
                    UNRESOLVED="${UNRESOLVED}(find from ${X}, which holds rawdata/, results/ or analysis/: check that its filter keeps out of them) "
                fi
            elif [ "$XS" = 1 ] && [ "$XW" = 0 ] && [ "$XT" = 0 ]; then
                UNRESOLVED="${UNRESOLVED}(find deletes every sequencing file under ${X}, and this guard cannot see whether rawdata/ is there) "
            fi
        done
    fi
    # a recursive rm / Remove-Item / rd of a folder that holds protected ones
    RMODE=""
    [ "$DESTRUCTIVE" = 1 ] && [[ $VSEG =~ $RE_RECURSIVE ]] && ! [[ $VSEG =~ $RE_FIND_DEL ]] && RMODE=rec

    # E9: what kind of move this is decides which arguments are SOURCES.
    #   mv   - every non-flag argument but the last (the last is written into)
    #   all  - every argument is a source: `mv -t DIR SRC…`, rename(1)
    #   ps   - PowerShell's Move-Item/Rename-Item: -Path/-LiteralPath values,
    #          else the first positional; -Destination is written into
    # A reader of text is not a mover: `grep -rn mv results` stays quiet.
    MOVE_KIND=""
    case "$CW" in
        grep|egrep|fgrep|rg|echo|printf|cat|less|more|head|tail|ls|wc) ;;
        move-item|rename-item) MOVE_KIND=ps ;;
        mi|move|rni|ren) case "$TOOL" in ""|Bash) ;; *) MOVE_KIND=ps ;; esac ;;
        rename) MOVE_KIND=all ;;
        *)
            if [[ $VSEG =~ $RE_MV ]]; then
                MOVE_KIND=mv
                [[ $VSEG =~ (^|[[:space:]])(-t|--target-directory)([[:space:]=]|$) ]] && MOVE_KIND=all
            fi
            # rsync --remove-source-files deletes each source once copied.
            [[ $VSEG =~ $RE_RSYNC_RSF ]] && [ "$DRYRUN" = 0 ] && MOVE_KIND=mv ;;
    esac
    [ -n "$MOVE_KIND" ] && MOVE_ONLY=1
    if [ "$MOVE_KIND" = ps ] && [ "$DESTRUCTIVE" = 0 ]; then
        read -r -a PSW <<<"$SEG_NR"
        PS_SRC=""; PS_POS=0; PS_PREV=""
        for ((pi = 1; pi < ${#PSW[@]}; pi++)); do
            # Lowercased in-shell, one character class per letter PowerShell
            # parameters use - no process per argument (Git Bash is slow to
            # start one, and bash 3.2 on the Mac has no ${var,,}).
            Pw=${PSW[$pi]}; Pl=$Pw
            for UC in A:a B:b C:c D:d E:e F:f G:g H:h I:i J:j K:k L:l M:m N:n O:o P:p Q:q R:r S:s T:t U:u V:v W:w X:x Y:y Z:z; do
                Pl=${Pl//${UC%:*}/${UC#*:}}
            done
            case "$PS_PREV" in
                -path|-literalpath|-lp|-pspath) PS_SRC="$PS_SRC $Pw"; PS_PREV=""; continue ;;
                -destination|-newname) PS_PREV=""; continue ;;
            esac
            case "$Pl" in -*) PS_PREV=$Pl; continue ;; esac
            PS_POS=$((PS_POS + 1))
            [ "$PS_POS" = 1 ] && PS_SRC="$PS_SRC $Pw"
        done
        if [ -z "${PS_SRC// /}" ] && [ "$PREV_LISTER_OK" != 1 ]; then
            UNRESOLVED="${UNRESOLVED}(${CW}: no source on the command line - it comes from a pipe) "
        fi
        for Pw in $PS_SRC; do
            Pw=${Pw//\"/}; Pw=${Pw//\'/}; Pw=${Pw//\\//}
            [[ $Pw =~ $RE_PROTECTED ]] && HIT_MV_SOURCE="${HIT_MV_SOURCE}${Pw} "
        done
        continue
    fi
    [ "$DESTRUCTIVE" = 1 ] || [ "$TRUNCATE" = 1 ] || [ "$MOVE_ONLY" = 1 ] || [ "$VARCMD" = 1 ] || continue

    # Targets: every word after the first that is not a flag. (No here-string:
    # see is_dry_run.)
    set -f; WORDS=($SEG_NR); set +f
    NARGS=0
    # E9 (2026-09-30, maintainer decision): mv's LAST non-flag argument is the
    # destination being written INTO - that is normal, not a removal, and
    # stays quiet. Only the sources (every argument before it) are judged
    # against rawdata/, results/ and analysis/, same as rm/find/rsync. Knowing
    # which one is last needs the total up front, filtered exactly like the
    # main loop below (flags dropped, quotes stripped, a wrapping verb like
    # `srun mv a b` not counted as a source itself) so the two counts agree.
    TOTAL_TARGETS=0
    if [ "$MOVE_ONLY" = 1 ] && [ "$DESTRUCTIVE" = 0 ]; then
        for ((ti = 1; ti < ${#WORDS[@]}; ti++)); do
            Tw=${WORDS[$ti]}
            case "$Tw" in -*|'') continue ;; esac
            Tw=${Tw//\"/}; Tw=${Tw//\'/}; Tw=${Tw//\\//}; Tw=${Tw//\{//}; Tw=${Tw//\}//}; Tw=${Tw//,//}
            [ -n "$Tw" ] || continue
            case "$Tw" in rm|rmdir|unlink|shred|truncate|mv|move-item) continue ;; esac
            TOTAL_TARGETS=$((TOTAL_TARGETS + 1))
        done
    fi
    LASTW=""
    for ((wi = 1; wi < ${#WORDS[@]}; wi++)); do
        # #62: the deadline holds inside one long command too.
        if [ "$SECONDS" -ge "$DEADLINE" ]; then TIMED_OUT=1; break 2; fi
        A=${WORDS[$wi]}
        PW=$LASTW; LASTW=$A
        # #35: the folder named by `mv -t DIR` / `--target-directory DIR` is where
        # the sources are written INTO, not one of them.
        if [ "$MOVE_KIND" = all ] && { [ "$PW" = -t ] || [ "$PW" = --target-directory ]; }; then continue; fi
        # #35: `{}` is xargs's / find's placeholder for a target this hook cannot
        # see (it used to be munged into `//` and read as the filesystem root).
        if [ "$A" = '{}' ]; then
            NARGS=$((NARGS + 1))
            [ "$DESTRUCTIVE" = 1 ] && UNRESOLVED="${UNRESOLVED}({} placeholder: the targets come from the command that feeds it) "
            continue
        fi
        case "$A" in -*|'') continue ;; esac
        # Every quote character goes, not just an outer pair - `'…/rawdata'/`,
        # `'…/'results` and `res"ults"` all name the directory. A Windows path
        # uses backslashes; a brace list names each member. A_ESC is the same
        # word with its backslashes read as escapes instead (`re\sults` is
        # `results`, #35): both readings are judged.
        A_ESC=${A//\"/}; A_ESC=${A_ESC//\'/}; A_ESC=${A_ESC//\\/}; A_ESC=${A_ESC//\{//}; A_ESC=${A_ESC//\}//}; A_ESC=${A_ESC//,//}
        A=${A//\"/}; A=${A//\'/}; A=${A//\\//}; A=${A//\{//}; A=${A//\}//}; A=${A//,//}
        [ -n "$A" ] || continue
        # #35: a relative target is judged where it really is.
        RES=""
        if [ -n "$VCWD" ]; then
            case "$A" in
                /*|[A-Za-z]:*|'~'*|*'$'*|*'`'*) ;;
                *) norm_path "$VCWD/$A"; RES="$REPLY" ;;
            esac
        fi
        case "$A" in rm|rmdir|unlink|shred|truncate|mv|move-item) continue ;; esac   # a wrapped verb
        NARGS=$((NARGS + 1))

        # E9: judge every mv SOURCE (every arg but the last) against the same
        # three protected directories rm/find/rsync already deny on. The
        # destination (NARGS == TOTAL_TARGETS, the last one counted above) is
        # excluded - see the comment above TOTAL_TARGETS.
        # A brace list expands to several arguments (`mv results{,.bak}`,
        # `mv {rawdata,old}`), the first of them a source, so a brace word
        # naming a protected directory is a source wherever it sits.
        if [ "$MOVE_ONLY" = 1 ] && [ "$DESTRUCTIVE" = 0 ] \
           && { [ "$NARGS" -lt "$TOTAL_TARGETS" ] || [ "$MOVE_KIND" = all ] \
                || [[ ${WORDS[$wi]} == *'{'*','*'}'* ]]; }; then
            [[ $A =~ $RE_PROTECTED ]] && HIT_MV_SOURCE="${HIT_MV_SOURCE}${A} "
            [ -n "$RES" ] && [[ $RES =~ $RE_PROTECTED ]] && HIT_MV_SOURCE="${HIT_MV_SOURCE}${RES} "
            defer_rec d "$A" 1 0 0
        fi

        # An unknown command word (`$(which rm)`, `$R`) is judged only when
        # its target is something this hook protects, and then it pauses.
        if [ "$VARCMD" = 1 ]; then
            [[ $A =~ $RE_ANY_GUARDED ]] && UNRESOLVED="${UNRESOLVED}(unknown command '${CW}') ${A} "
            continue
        fi

        # Cannot resolve a target that still holds a variable or substitution.
        # Only worth saying for a delete: "$RUN_DIR/analysis/x.R" as the target
        # of a redirect is the ordinary way every task file gets written. For a
        # delete it is still judged by its literal part - "$RUN_DIR/results"
        # names results/ whatever RUN_DIR holds - and, being unknown, it
        # pauses (ask) rather than only warning the model.
        case "$A" in
            *'$'*|*'`'*)
                [ "$DESTRUCTIVE" = 1 ] || continue
                UNRESOLVED="${UNRESOLVED}${A} " ;;
        esac

        if [ "$TRUNCATE" = 1 ] && [ "$DESTRUCTIVE" = 0 ]; then
            # Overwriting is worth a word only where the content is not ours to
            # replace: the user's originals and the pipeline's own output.
            # analysis/ is deliberately absent - that is where downstream code
            # and figures are supposed to be written.
            [[ $A =~ $RE_OVERWRITE ]] && HIT_OVERWRITE="${HIT_OVERWRITE}${A} "
        fi

        if [ "$DESTRUCTIVE" = 1 ]; then
            judge_delete_target "$A"
            # #35: the same word with its backslashes read as escapes (re\sults is
            # results), and the same word resolved against the working folder.
            [ "$A_ESC" != "$A" ] && judge_delete_target "$A_ESC"
            [ -n "$RES" ] && judge_delete_target "$RES"
            defer_rec d "$A" 0 1 0
            # sn1-delete-shapes: a brace word as bash expands it (`res{ults,}`),
            # beside the flattened form above; and a recursive delete of a folder
            # that holds protected ones.
            [[ ${WORDS[$wi]} == *'{'*'}'* ]] && judge_word "${WORDS[$wi]}" "$RMODE"
            if [ "$RMODE" = rec ]; then
                holds_protected "$A" && HIT_PROTECTED="${HIT_PROTECTED}${A} (it holds rawdata/, results/ or analysis/) "
                [ -n "$RES" ] && holds_protected "$RES" && HIT_PROTECTED="${HIT_PROTECTED}${RES} (it holds rawdata/, results/ or analysis/) "
                defer_rec d "$A" 0 0 1
            fi
        fi
        shopt -s nocasematch
        [[ $A =~ $RE_SEQEXT ]] && HIT_SEQFILE="${HIT_SEQFILE}${A} "
        shopt -u nocasematch
        [[ $A =~ $RE_RAW ]] && HIT_SEQFILE="${HIT_SEQFILE}${A} "
    done
    # A delete that names no target (`gci X | Remove-Item`) takes it from a pipe.
    # Only for the PowerShell verbs: `which rm` or `man rm` name no target either.
    if [ "$DESTRUCTIVE" = 1 ] && [ "$NARGS" = 0 ] && [[ $CW =~ ^(remove-item|ri|del|erase|rd)$ ]]; then
        UNRESOLVED="${UNRESOLVED}(${CW}: no target on the command line - it comes from a pipe) "
    fi
done <<< "$SEGMENTS"
[ "$TIMED_OUT" = 1 ] || defer_run

# ── deny ─────────────────────────────────────────────────────────────────────
[ -n "$HIT_ROOT" ] && deny "BLOCKED: that target is a filesystem root, not a cleanup target.

Target: ${HIT_ROOT}

Cleanup always names a specific task directory. If a variable expanded to empty
(\"\$RUN_DIR/work\" with RUN_DIR unset becomes \"/work\"), fix the variable - do
not run the command."

[ -n "$HIT_PLUGINS" ] && deny "BLOCKED: .nextflow/plugins/ must never be deleted.

Target: ${HIT_PLUGINS}

Compute nodes have no outbound network, so Nextflow cannot re-download its plugins
there. Deleting this directory breaks every future run on this cluster and cannot
be undone from inside a job. There is no situation where the assistant should
remove it."

[ -n "$HIT_SHARED" ] && deny "BLOCKED: that path is shared by the whole lab, not this task's to remove.

Target: ${HIT_SHARED}

_references/ holds reference genomes and taxonomy databases; the image library
holds the Singularity images every member's runs resolve against. Both were
fetched once on a login node so nobody else has to wait for them again -
deleting either makes every other member re-download tens of GB, and their runs
will not tell them why they suddenly got slow.

If the intent is to free space or replace a stale version, that is a decision for
whoever maintains the shared area. Show them the path and the size; do not remove
it here."

[ -n "$HIT_PROTECTED" ] && deny "BLOCKED: rawdata/ (the user's original sequencing data), results/ (pipeline
output) and analysis/ (downstream code and figures) are never deleted.

Target: ${HIT_PROTECTED}

Cleanup is limited to work/ and the Nextflow cache. If the user genuinely wants
one of these paths removed, show them the command and let them run it themselves."

# ── warn ─────────────────────────────────────────────────────────────────────
# #62: the loop stopped at its deadline; whatever it had not judged yet is unknown.
[ "$TIMED_OUT" = 1 ] && ask "CANNOT VERIFY: this guard could not finish checking this command in time.

It stopped after ${NSEG} of its parts at its own ${DEADLINE} s limit, rather than
being cut off by the hook timeout (which would let the command run unchecked).
Nothing it had already read was a refused delete, but the rest is unchecked.

Show the user the command, confirm it does not delete rawdata/, results/,
analysis/, _references/, the image library or .nextflow/plugins/, and that any
work/ or cache delete has their \"確認刪除\". A shorter command (the script in a
file, run by name) is checked in full."

# #29: these two pause (ask) rather than warn. A warning is prose the model
# reads and may proceed past; the maintainer decided 2026-09-29 that a delete
# whose target this hook cannot see is the user's to confirm.
[ -n "$HIT_CODE" ] && ask "CANNOT VERIFY: this deletes files from inside code (a python/R/node call), so the
guard cannot read which paths it removes.

Code: ${HIT_CODE}

Show the user exactly which paths this removes. It must not touch rawdata/,
results/, analysis/, _references/, the image library or .nextflow/plugins/, and
deleting work/ or the Nextflow cache still needs them to say \"確認刪除\"."

[ -n "$HIT_GLOB" ] && ask "CANNOT VERIFY: this delete uses a wildcard that could also match rawdata/,
results/, analysis/ or _references/.

Pattern: ${HIT_GLOB}

List what it matches first (ls with the same pattern), show the user, and name
the paths literally if any protected directory is among them."

# sn1-delete-shapes: on a case-sensitive file system, a protected name in other case.
[ -n "$HIT_CASE" ] && ask "CANNOT VERIFY: this deletes a folder named like a protected one in different
letter case (${HIT_CASE}).

On this machine's file system that is a different folder from rawdata/,
results/, analysis/, _references/ or .nextflow/plugins/; on Windows or macOS,
and on a Windows drive under WSL, it is the same one. Confirm with the user
which folder this is before running it."

# sn1-delete-shapes: install -d with a mode or owner, on a protected folder itself.
[ -n "$HIT_PERM" ] && ask "About to change the mode or owner of a protected folder (${HIT_PERM}) with install -d.

It removes nothing, but a mode such as 000 locks the pipeline and every other
member out of it. Confirm with the user that this is intended."

[ -n "$UNRESOLVED" ] && ask "CANNOT VERIFY: this destructive command's target is a shell variable, so the
guard cannot tell what it points at.

Unresolved: ${UNRESOLVED}

Expand it and check before running, e.g.:
  echo \"<the variable>\"
Confirm it is not rawdata/, results/, analysis/ or .nextflow/plugins/, and that
the user has said \"確認刪除\", then issue the command with the literal path."

[ -n "$HIT_MV_SOURCE" ] && ask "About to move rawdata/, results/ or analysis/ - or something inside one -
somewhere else.

Source: ${HIT_MV_SOURCE}

Moving it out is a different act from writing into it, and the safety net now
treats the two differently on purpose (#29e, maintainer decision 2026-09-30):
once it lands in a scratch area, a later cleanup of that area deletes it for
good, with nothing here left to say it used to be here. Moving something INTO
one of these directories is unaffected - that is writing, not removing.
Confirm with the user that this move is intended before running it."

# SN2 (nextflow-clean-unconfirmed): these two warnings used to come first and
# end the hook, so a work/ delete in the same command lost its ask. They are now
# notes: appended to the work/ ask when there is one, a warning on their own
# otherwise.
NOTES=""
[ -n "$HIT_OVERWRITE" ] && NOTES="About to write over a file under rawdata/ or results/ (${HIT_OVERWRITE}).

Neither is this plugin's to rewrite: rawdata/ is the user's original data and
results/ is what the pipeline produced. Check the path is what you meant. Files
generated by downstream analysis belong in analysis/."

[ -n "$HIT_SEQFILE" ] && NOTES="${NOTES:+$NOTES

}CAUTION: this command targets what looks like original sequencing data
(${HIT_SEQFILE}).

Never mv original data - moving it makes the task dir the only copy. Use symlink
or cp. Confirm the exact target with the user before proceeding."

[ -n "$HIT_WORK" ] && ask "About to delete Nextflow scratch (${HIT_WORK}).

Before running this, confirm all three:
  1. the output file list has been shown to the user
  2. they were told -resume will no longer work, and roughly how long a full
     rerun costs
  3. no other task dir is using this work/ as its -work-dir (a _v2 rerun points
     back at the original), which would silently break that run's resume
  4. the user replied \"確認刪除\"

Note: downstream analysis can still be re-run afterwards - it reads results/ and
the grouping columns in the samplesheet, not work/.${NOTES:+

Also:

$NOTES}"

[ -n "$NOTES" ] && warn "$NOTES"

[ -n "$HIT_LEFTOVER" ] && warn "Post-run leftover (${HIT_LEFTOVER}) - deletable once the run is completed.

  null/             a launch that lost its --outdir; nf-core wrote pipeline_info
                    under the literal string \"null\". Never holds real output.
  offline_data/     references/test data staged on the login node. Re-stageable;
                    results/ does not read from it after the run finishes.
  .sendmail_tmp.html  notification leftover, contains the user's e-mail address.

Still confirm the run has actually finished and that the user replied \"確認刪除\".
Note pipeline/ is NOT in this list: it is the only record of which source
revision actually ran, and compute nodes cannot re-clone it."

exit 0
