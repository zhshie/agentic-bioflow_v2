#!/bin/bash
# Nothing existing: Claude Code has no first-use overview for a plugin; a hook on the user's first prompt or skill load is the only place to show one once per session.
#
# UserPromptSubmit + PostToolUse(Skill): show the overview the first time this
# plugin is actually used in a session, not at every session start.
#
# Feature 005 (#48): that same moment also writes the in-use marker
# ($STATE/in-use/<session id>) which every other hook reads through
# hooks/in_use.sh - the plugin is silent in a session until the session has
# reached for it, is inside the deployment, or runs one of its scripts. This
# hook is the one thing that is NOT gated by that: it is what turns it on.
#
# It used to be a SessionStart hook, which meant every conversation in every
# project opened with it - including the many that have nothing to do with
# pipelines. The overview is worth reading exactly once, at the moment the user
# reaches for the plugin. Two events are that moment, and both are measured,
# not assumed (2026-09-13):
#   - the user types a command: UserPromptSubmit's `prompt` is the raw text,
#     e.g. "/agentic-bioflow:runs check something".
#   - the model loads one of the plugin's skills for a natural-language
#     request: the Skill tool's input is {"skill": "agentic-bioflow:<name>"}.
#     PostToolUse, not PreToolUse, so a refused or failed load shows nothing.
# A typed command may go on to load the skill as well; the once-per-session
# marker makes the second event a no-op.
#
# Not a gate. It fails open everywhere and always exits 0: a missing jq, an
# unwritable state directory or a broken intro.sh costs the user the overview,
# never their prompt.
#
# T3 (2.16): typing the plugin's own name was the only door in. "I want to run
# the RNA-seq samples and submit them" never contains the string
# "agentic-bioflow", so it never reached the model with a hint to load the
# operational skill - the natural-language path this plugin's own skill
# description exists to cover (skills/operational/SKILL.md: "I want to run
# RNA-seq" should work identically to a typed command) had nothing in the
# hook layer backing it up. This adds a second door, scoped narrowly on
# purpose: a prompt has to name BOTH a pipeline topic AND something the user
# wants done about it before this says anything, so a pure knowledge question
# ("what is RNA-seq") is left alone - the model can and should answer that
# without loading an operational skill first.
#
# T3, second half: a missing/broken jq used to mean this file went silent in
# the one place a member most needed to know it - the safety-net hooks
# (confirm_launch.sh, confirm_cleanup.sh, confirm_walkthrough.sh) all run in a
# reduced, text-only mode without it (see their own "T1" sections), and
# nothing told anyone that was happening. A degraded safety net that says
# nothing about being degraded is the shape PITFALLS 28 already fixed once for
# the gates themselves; this closes the same hole for the one hook that could
# have SAID so instead of just going quiet. The warning is built with plain
# `printf`, not `jq -n`, for the same reason the gates' own no-jq messages are
# - leaning on jq to report jq's own absence fails the same way it is trying
# to fix.
set -uo pipefail
exec 2>/dev/null

# intro-marker-timeout: hooks.json gives this hook a timeout, and a hook past it
# is killed. The in-use marker (below) is what turns every other hook on for
# this session, so it is decided and written FIRST, from the raw input with
# bash alone, before any program is started: before this, a busy machine could
# kill the hook while `cat`, `tr` or `jq` were still running, and the session
# then counted as not in use - the whole safety net silent. Stdin is read
# without `cat` (#34).
INPUT=$(</dev/stdin)
HD="${0%/*}"; [ "$HD" = "$0" ] && HD=.

# The literal door: a typed `/agentic-bioflow:...` command or a Skill load
# naming this plugin. Checked on the raw text so it works with or without jq
# - EVENT below still does the precise version once jq is confirmed working.
case "$INPUT" in *agentic-bioflow:*) IS_LITERAL=1 ;; *) IS_LITERAL=0 ;; esac

# The natural-language door (T3). Scoped to UserPromptSubmit only - a
# PostToolUse Skill call is either the literal door above (this plugin's own
# skill) or none of this hook's business, never a prompt to pattern-match.
IS_UPS=0
re_ups='"hook_event_name"[[:space:]]*:[[:space:]]*"UserPromptSubmit"'
[[ $INPUT =~ $re_ups ]] && IS_UPS=1
# A Skill load whose own `skill` field names this plugin (not its arguments).
IS_SKILL=0
re_skill='"skill"[[:space:]]*:[[:space:]]*"agentic-bioflow:'
[[ $INPUT =~ $re_skill ]] && IS_SKILL=1

# The session id names a file, so it is reduced to characters that cannot
# climb out of the state directory. Extracted without jq - this has to work in
# the no-jq branch below, and a single extraction here serves both
# branches instead of two copies drifting apart; a degraded machine's PATH is
# exactly the place to avoid reaching for one more external binary than the
# job needs. Feature 005: the FIRST "session_id" in the input, by a bash regex - the same
# reading hooks/in_use.sh does, so the file written here is the file read there.
# (The sed that stood here took the LAST one, which is a nested copy when a
# tool's response carries its own session_id.)
SID_RAW=""
re_sid='"session_id"[[:space:]]*:[[:space:]]*"([^"]*)"'
if [[ $INPUT =~ $re_sid ]]; then SID_RAW="${BASH_REMATCH[1]}"; fi
SID="${SID_RAW//[^A-Za-z0-9_-]/}"
STATE="${AGENTIC_BIOFLOW_STATE_DIR:-${XDG_STATE_HOME:-${HOME:-}/.local/state}/agentic-bioflow}"
MARKS="$STATE/intro-shown"

# Feature 005 (#48), Constitution 2.0.0: this is the moment a session starts
# being "in use" - every other hook is silent until it has happened, or until
# the call itself or the session's folder says so (hooks/in_use.sh). The marker
# is a separate file from $MARKS above on purpose: that one means "the overview
# was shown" and is written only after something went out; this one means "the
# plugin was reached for" and is written as soon as that is known, so a failed
# intro.sh does not leave the safety net off. A subagent's calls carry its
# parent's session id, so one marker covers both. Fails open like everything
# here: an unwritable state directory costs the marker, never the prompt - and
# a state path that cannot be read or written is itself read as "in use" by
# in_use.sh once a deployment exists, so a failed write here does not turn the
# net off.
# intro-marker-timeout: no `mkdir` when the folder is there, and the sweep of
# month-old markers runs only when this session's marker is new, after it is
# written (a kill during the sweep costs nothing).
mark_in_use() {
    [ -n "$SID" ] || return 0
    [ -e "$STATE/in-use/$SID" ] && return 0
    [ -d "$STATE/in-use" ] || mkdir -p "$STATE/in-use" 2>/dev/null || return 0
    : > "$STATE/in-use/$SID" 2>/dev/null || return 0
    find "$STATE/in-use" -type f -mtime +30 -exec rm -f {} + 2>/dev/null
    return 0
}
# A prompt that names /agentic-bioflow: anywhere - mid-sentence, quoted, asked
# about - is reaching for the plugin as far as this can tell. The overview waits
# for the prompt to START with it (below); the marker does not: unsure is in use.
if [ "$IS_UPS" = 1 ] && [ "$IS_LITERAL" = 1 ]; then mark_in_use; fi   # with or without the slash (#53)
# A Skill load of this plugin's own skill: marked now; EVENT below still checks
# it precisely before anything is shown.
[ "$IS_SKILL" = 1 ] && mark_in_use

# Nothing else this hook does applies to a call that is neither door.
[ "$IS_LITERAL" = 1 ] || [ "$IS_UPS" = 1 ] || exit 0

# Shell separators AND the JSON punctuation around them folded to spaces, the
# same trick hooks/confirm_launch.sh uses and for the same reason: this has to
# work on the raw, still-quoted JSON payload without jq (jq may be exactly
# what is missing), and a bare `tr -s ';&|()<>'` leaves `"agentic-bioflow`
# glued to its opening quote, which no substring check could reliably bound.
# Folded in the shell for an ordinary prompt (no process before the
# natural-language door can mark); one `tr` for a long one, where the shell's
# replacements would be quadratic.
FOLD_SEP=$'\t\n\r;&|()<>"\'{}[],:='
FOLD_BR=$']\t\n\r;&|()<>"\'{}[,:='    # the same set, `]` first for a bracket expression
if [ "${#INPUT}" -le 8192 ]; then
    NORM=" ${INPUT//[$FOLD_BR]/ } "
    while [[ $NORM == *"  "* ]]; do NORM="${NORM//  / }"; done
else
    NORM=" $(printf '%s' "$INPUT" | tr -s "$FOLD_SEP" ' ') "
fi

# Kept close to skills/operational/SKILL.md's own trigger vocabulary
# (RNA-seq, amplicon/16S, metagenomics, variant calling, differential
# expression, nf-core, Nextflow, Seqera, FASTQ, a samplesheet, GEO/SRA) so the
# two do not silently drift into naming different things - PITFALLS 19's
# lesson, that a justification naming another file's behaviour needs
# SOMETHING pinning them together: tests/plugin_intro_test.sh asserts a
# handful of these words also appear in that file's own description.
#
# E10 (2026-09-30, maintainer decision): a Chinese request with action intent
# ("幫我分析這批定序資料") named no English topic word, so it never reached
# either door. Specialist Chinese terms only - 定序/測序/擴增子/轉錄體/轉錄組/
# 樣本表/總體基因體/宏基因組, plus their simplified forms where different -
# were added below, deliberately NOT generic words like 分析/流程/資料: the
# maintainer uses Chinese for unrelated work in the same shell, and a generic
# word would nudge on every one of those. has_action() already covers 分析
# and the rest of the verb side; only the topic side was missing.
has_topic() {
    case "$1" in
        *RNA-seq*|*RNAseq*|*'RNA seq'*|*FASTQ*|*fastq*|*nf-core*|*[Nn]extflow*|*samplesheet*|*Seqera*|*16S*|*ampliseq*|*amplicon*|*metagenom*|*[Ww][Gg][Ss]*|*'variant calling'*|*'differential expression'*|*GEO*|*SRA* | \
        *定序*|*測序*|*测序*|*擴增子*|*扩增子*|*轉錄體*|*转录体*|*轉錄組*|*转录组*|*樣本表*|*样本表*|*總體基因體*|*总体基因体*|*宏基因組*|*宏基因组*|*宏基因体*|*宏基因體*)
            return 0 ;;
    esac
    return 1
}

# English entries padded with spaces (word-boundary matching against $NORM,
# which is itself padded) - "run" alone would match inside "prune"; Chinese
# entries are left as bare substrings, which is the ordinary way to match
# words in a script with no spaces between them.
has_action() {
    case "$1" in
        *' run '*|*' launch '*|*'analy'*|*' submit '*|*'debug'*|*'troubleshoot'*|*'download'*'result'*|*'why'*'fail'*|*'check'*'run'*| \
        *跑*|*分析*|*送出*|*啟動*|*執行*|*下載結果*|*為什麼失敗*|*失敗*|*除錯*|*檢查*)
            return 0 ;;
    esac
    return 1
}

IS_NL=0
if [ "$IS_LITERAL" = 0 ] && [ "$IS_UPS" = 1 ] && has_topic "$NORM" && has_action "$NORM"; then
    IS_NL=1
fi

[ "$IS_LITERAL" = 1 ] || [ "$IS_NL" = 1 ] || exit 0

# The natural-language door is decided without jq, so it can mark now - before
# the once-per-session exit below, which must not skip it. The literal doors
# marked at the top.
[ "$IS_NL" = 1 ] && mark_in_use
[ -n "$SID" ] && [ -e "$MARKS/$SID" ] && exit 0

# T3: jq missing/broken is now visible instead of silent - see the file
# header. A SEPARATE marker from $MARKS: that one means "the overview or the
# nudge was shown", this one means "jq was found broken", and the two answer
# different questions - jq being reinstalled mid-session should not be
# blocked from ever showing the real overview by a marker written while it
# was still broken.
JQMARKS="$STATE/jq-warn-shown"
# jq-broken-gates: "cannot run" includes a jq that exits 0 with the wrong answer
# (`{}`, a line of text): it passed `jq -e .`, then its output went out as this
# hook's own. It has to compute a known answer (a trailing CR is jq.exe).
abf_jq_works() {
    local o
    o=$(jq -c .a <<<'{"a":[1]}' 2>/dev/null) || return 1
    [ "${o%$'\r'}" = '[1]' ]
}
if ! command -v jq >/dev/null 2>&1 || ! abf_jq_works; then
    # Without jq the literal door cannot be checked precisely (a mere mention
    # of /agentic-bioflow: mid-sentence matches the loose test). Marking is the
    # safe direction: one gate too many beats one missed.
    mark_in_use
    if [ -z "$SID" ] || [ ! -e "$JQMARKS/$SID" ]; then
        JQWARN='agentic-bioflow: jq is missing or cannot run here. The launch/cleanup/walkthrough safety-net hooks (confirm_launch.sh, confirm_cleanup.sh, confirm_walkthrough.sh) are running in a reduced, text-only mode until it is installed - they still catch a launch- or delete-shaped command, but cannot verify the fine detail the way they normally do. macOS: brew install jq / Debian+WSL: sudo apt install jq / Windows: winget install jqlang.jq'
        printf '{"systemMessage":"%s"}\n' "$JQWARN"
        if [ -n "$SID" ] && mkdir -p "$JQMARKS" 2>/dev/null; then
            : > "$JQMARKS/$SID" 2>/dev/null
            find "$JQMARKS" -type f -mtime +30 -exec rm -f {} + 2>/dev/null
        fi
    fi
    exit 0
fi

# No subshell for this: intro.sh finds its own root from its own path.
ROOT="$HD/.."
# intro-marker-timeout: the language is asked of settings.sh once here and
# handed to both intro.sh calls below, rather than each of them asking it
# again (a bash process apiece). Empty means no setting: zh-TW, intro.sh's own
# default.
INTRO_LANG=$(bash "$ROOT/scripts/settings.sh" language 2>/dev/null)
[ -n "$INTRO_LANG" ] || INTRO_LANG=zh-TW

if [ "$IS_LITERAL" = 1 ]; then
    EVENT=$(jq -r '
        if .tool_name == "Skill" then
            (if ((.tool_input.skill // "") | startswith("agentic-bioflow:")) then "PostToolUse" else "" end)
        elif ((.prompt // "") | test("^\\s*/agentic-bioflow:")) then "UserPromptSubmit"
        else "" end' <<<"$INPUT") || exit 0
    [ -n "$EVENT" ] || exit 0
    mark_in_use

    INTRO="$(bash "$ROOT/scripts/intro.sh" --lang "$INTRO_LANG")" || exit 0
    [ -n "$INTRO" ] || exit 0

    # Claude Code caps hook output at 10,000 characters and swaps anything
    # longer for a file preview; trimming here keeps it readable.
    [ "${#INTRO}" -gt 9000 ] && INTRO="${INTRO:0:9000}

[truncated - run scripts/intro.sh for the full text]"

    # PITFALLS 35: `systemMessage` is chrome, not a canvas. A GUI surface
    # (the Claude app; measured 2026-09-20 with this same overview) renders
    # it ONE PROMPT-PREFIXED ROW PER LINE - "PostToolUse:Skill says: " in
    # front of all 26 of them, blank lines included - and collapses the runs
    # of spaces the old card used to align its command list and its flow
    # diagram. The same string is a tidy block in a terminal, which is why
    # this was written that way and why nobody saw it until the plugin was
    # opened somewhere else.
    #
    # So the card travels as additionalContext and the MODEL prints it, as
    # ordinary Markdown, the way it prints everything else it says: one
    # renderer, already correct on every surface, instead of this hook
    # guessing which one it is talking to. The user still gets an immediate
    # signal that something loaded - the one-line banner below, short enough
    # that the per-row rendering has nothing to do to it.
    #
    # What this gives up, stated plainly: the overview is no longer
    # GUARANTEED by the hook - a model that ignores the instruction below
    # shows the user nothing but the banner. That is the same bet
    # every commands/*.md file's "Before anything else" section already
    # makes, and tests/plugin_intro_test.sh now pins the instruction's
    # presence rather than the old guarantee.
    BANNER="$(bash "$ROOT/scripts/intro.sh" --lang "$INTRO_LANG" --banner 2>/dev/null)"
    [ -n "$BANNER" ] || BANNER="agentic-bioflow"
    BANNER="${BANNER%%$'\n'*}"

    SHOW='Print the overview below to the user as the FIRST thing in your reply, verbatim, before anything else and before any tool call. It is already Markdown - keep it as Markdown, do not wrap it in a code block, do not summarise it, and do not re-order it.'

    jq -n --arg b "$BANNER" --arg s "$SHOW" --arg m "$INTRO" --arg e "$EVENT" \
      '{systemMessage: $b,
        hookSpecificOutput: {hookEventName: $e, additionalContext: ($s + "\n\n" + $m)}}' || exit 0
elif [ "$IS_NL" = 1 ]; then
    # T3's short door: additionalContext only, for the model - not
    # systemMessage. The full overview is a banner worth the user's attention
    # once; a routing hint fired on ordinary conversational text is not, and
    # showing it every time would teach the user to ignore this hook the same
    # way a gate that cries wolf teaches people to click through it.
    NUDGE="$(bash "$ROOT/scripts/intro.sh" --lang "$INTRO_LANG" --nudge)" || exit 0
    [ -n "$NUDGE" ] || exit 0
    jq -n --arg m "$NUDGE" \
      '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $m}}' || exit 0
fi

# Marked only after something went out, so a failure above leaves the next
# use free to try again. Markers are a few bytes each; a month is long past
# any session anyone resumes.
if [ -n "$SID" ] && { [ -d "$MARKS" ] || mkdir -p "$MARKS"; }; then
    : > "$MARKS/$SID"
    find "$MARKS" -type f -mtime +30 -exec rm -f {} + 2>/dev/null
fi
exit 0
