#!/bin/bash
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
    local text=" $(printf '%s' "$1" | tr -s "$LOOKS_SHAPED_SEP" ' ') "
    case "$text" in
        *' rm '*|*' rmdir '*|*' shred '*|*' mv '*|*'-delete'*|*'--delete'*|*' find '*|*' rsync '*|*'Remove-Item'*|*'rmtree'*)
            return 0 ;;
    esac
    return 1
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
JQ_FAST=0
JQ_OUT=$(jq -js 'if length == 1 then (.[0] | [(.tool_name // ""), (.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // "")] | if all(.[]; type == "string") and (any(.[]; contains("\u001f") or contains("\u0000")) | not) then (map(sub("\\n+\\z"; "") + "\u001f") | join("")) else empty end) else empty end' <<<"$INPUT" 2>/dev/null) \
  && [ -n "$JQ_OUT" ] && JQ_FAST=1
if [ "$JQ_FAST" = 0 ] && ! printf '{}' | jq -e . >/dev/null 2>&1; then
    RAW=$INPUT
    if looks_delete_shaped "$RAW"; then
        cat >&2 <<'EOF'
BLOCKED: jq is missing or cannot run here, so hooks/confirm_cleanup.sh cannot read
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
fi

if [ "$JQ_FAST" = 1 ]; then
    # The fields come as one string, each followed by the separator. They are read out in order:
    # pattern removal (`#*x`, `%%x*`, `##*x`) and ${x//p/} are quadratic in bash on a long string, and a
    # large Write or here-doc then outlasts the hook's timeout (#34); `read` is linear. Trailing
    # newlines were trimmed by jq, as $(jq) did per field.
    {
        IFS= read -r -d $'\037' TOOL
        IFS= read -r -d $'\037' CMD
    } <<<"$JQ_OUT"
else
    TOOL=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // .tool_input.script // .tool_input.cmd // .tool_input.commandLine // .tool_input.powershell // .tool_input.input // ""' 2>/dev/null)
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
       && [[ $o == '{'* ]]; then
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
    IFS=/ read -r -a parts <<<"$p"
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
RE_FIND_DEL='(^|[[:space:]])([^[:space:]]*/)?find[[:space:]](.*[[:space:]])?(-delete([[:space:]]|$)|-exec(dir)?[[:space:]]+([^[:space:]]*/)?(rm|rmdir|unlink|shred)([[:space:]]|$))'
RE_RSYNC_DEL='(^|[[:space:]])([^[:space:]]*/)?rsync[[:space:]](.*[[:space:]])?--delete'
RE_MV='(^|[[:space:]])([^[:space:]]*/)?\\?mv([[:space:]]|$)'
RE_RSYNC_RSF='(^|[[:space:]])([^[:space:]]*/)?rsync[[:space:]](.*[[:space:]])?--remove-source-files'
RE_CODE_DEL='(shutil\.rmtree|os\.(remove|unlink|rmdir|removedirs)|(^|[^[:alnum:]_.])(unlink|rmtree|remove_tree)|file\.remove|fs\.(rm|rmSync|unlinkSync|rmdirSync)|::Delete)[[:space:]]*\('
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

# One delete target judged against every rule that depends on where it is. Called
# for the word as written, for the word with backslashes read as escapes, and for
# the word resolved against the working folder (#35).
judge_delete_target() {
        local A="$1" An GL NM RP
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
            if [ -e "$A" ] || [ -L "$A" ] || [ -e "${A%/*}" ]; then
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

# A dry run deletes nothing (#35) - but only the options of the command ITSELF
# say so. `nice -n 10 rsync --delete`, `srun -n 1 rsync ...`, `ssh -n h rsync`,
# `sudo -n`, `ionice -n 7`, `timeout -n 5` carry an n that belongs to the
# wrapper; read as rsync's -n it silenced a real delete. So: find the rsync
# word (or `git ... clean`) and look only at the option words after it.
# is_dry_run <quote-free segment>: 0 if it is a dry run of rsync / git clean.
is_dry_run() {
    local W w b i=0 n seen=0
    read -r -a W <<<"$1"
    n=${#W[@]}
    for ((i = 0; i < n; i++)); do
        w=${W[$i]}; w=${w#\\}; b=${w##*/}
        if [ "$seen" = 0 ]; then
            case "$b" in rsync|rsync.exe) seen=1 ;; clean) seen=1 ;; esac
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

while IFS="$US" read -r SEG VSEG CW; do
    [ -n "$SEG" ] || continue

    # #62: a segment that cannot be one of the things judged below is dropped here,
    # before ~25 regex tests and a dozen assignments cost it ~10 ms each on Git Bash
    # (a 300 KB python here-doc is thousands of segments, and a hook that runs past
    # its timeout is cancelled and the call PROCEEDS). It can only be skipped when
    # its command word is none of the ones handled below AND none of the stems
    # every later rule needs - a delete verb, find/rsync/mv, a redirect, a
    # delete-shaped call - appears anywhere in the quote-free text. Stems are
    # deliberately loose (`rm` also matches `format`): looser only means "judged
    # as before". The one piece of state a skipped segment must still update is
    # LISTER_OK, which any other command word resets.
    if [ -n "$CW" ]; then
        case "$CW" in
            __too_deep__|cd|pushd|get-childitem|gci|ls|dir|get-item|gi|where-object|where|'?'|select-object|select|sort-object|sort|measure-object|measure) ;;
            rm|rmdir|unlink|shred|truncate|remove-item|ri|del|erase|rd|xargs|cmd|git|rename|move-item|rename-item|mi|move|rni|ren|'$'*|'`'*) ;;
            *)
                case "$VSEG" in
                    *rm*|*unlink*|*shred*|*remove*|*Delete*|*find*|*rsync*|*mv*|*'>'*) ;;
                    *) LISTER_OK=0; continue ;;
                esac ;;
        esac
    fi

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
            case "$CDT" in
                ''|-|'~'*|*'$'*|*'`'*) VCWD="" ;;
                /*|[A-Za-z]:*) norm_path "${CDT//\\//}"; VCWD="$REPLY" ;;
                *) if [ -n "$VCWD" ]; then norm_path "$VCWD/${CDT//\\//}"; VCWD="$REPLY"; fi ;;
            esac
            LISTER_OK=0
            continue ;;
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

    # Targets: every word after the first that is not a flag.
    read -r -a WORDS <<<"$SEG_NR"
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

[ -n "$HIT_OVERWRITE" ] && warn "About to write over a file under rawdata/ or results/ (${HIT_OVERWRITE}).

Neither is this plugin's to rewrite: rawdata/ is the user's original data and
results/ is what the pipeline produced. Check the path is what you meant. Files
generated by downstream analysis belong in analysis/."

[ -n "$HIT_SEQFILE" ] && warn "CAUTION: this command targets what looks like original sequencing data
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
the grouping columns in the samplesheet, not work/."

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
