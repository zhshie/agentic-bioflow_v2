#!/bin/bash
# UserPromptSubmit + PostToolUse(Skill): show the overview the first time this
# plugin is actually used in a session, not at every session start.
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

INPUT=$(cat)

# Shell separators AND the JSON punctuation around them folded to spaces, the
# same trick hooks/confirm_launch.sh uses and for the same reason: this has to
# work on the raw, still-quoted JSON payload without jq (jq may be exactly
# what is missing), and a bare `tr -s ';&|()<>'` leaves `"agentic-bioflow`
# glued to its opening quote, which no substring check could reliably bound.
FOLD_SEP=$'\t\n\r;&|()<>"\'{}[],:='
NORM=" $(printf '%s' "$INPUT" | tr -s "$FOLD_SEP" ' ') "

# The literal door: a typed `/agentic-bioflow:...` command or a Skill load
# naming this plugin. Checked on the raw text so it works with or without jq
# - EVENT below still does the precise version once jq is confirmed working.
case "$INPUT" in *agentic-bioflow:*) IS_LITERAL=1 ;; *) IS_LITERAL=0 ;; esac

# The natural-language door (T3). Scoped to UserPromptSubmit only - a
# PostToolUse Skill call is either the literal door above (this plugin's own
# skill) or none of this hook's business, never a prompt to pattern-match.
IS_UPS=0
case "$NORM" in *' hook_event_name UserPromptSubmit '*) IS_UPS=1 ;; esac

# Kept close to skills/operational/SKILL.md's own trigger vocabulary
# (RNA-seq, amplicon/16S, metagenomics, variant calling, differential
# expression, nf-core, Nextflow, Seqera, FASTQ, a samplesheet, GEO/SRA) so the
# two do not silently drift into naming different things - PITFALLS 19's
# lesson, that a justification naming another file's behaviour needs
# SOMETHING pinning them together: tests/plugin_intro_test.sh asserts a
# handful of these words also appear in that file's own description.
has_topic() {
    case "$1" in
        *RNA-seq*|*RNAseq*|*'RNA seq'*|*FASTQ*|*fastq*|*nf-core*|*[Nn]extflow*|*samplesheet*|*Seqera*|*16S*|*ampliseq*|*amplicon*|*metagenom*|*[Ww][Gg][Ss]*|*'variant calling'*|*'differential expression'*|*GEO*|*SRA*)
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

# The session id names a file, so it is reduced to characters that cannot
# climb out of the state directory. Extracted with sed rather than jq - this
# has to work in the no-jq branch just below, and a single extraction here
# serves both branches instead of two copies drifting apart. The first-line
# trim is a bash parameter expansion, not `head -1`: this runs before jq's
# availability is even known, and a degraded machine's PATH is exactly the
# place to avoid reaching for one more external binary than the job needs.
SID_RAW=$(printf '%s' "$INPUT" | sed -nE 's/.*"session_id"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/p')
SID_RAW="${SID_RAW%%$'\n'*}"
SID=$(printf '%s' "$SID_RAW" | tr -cd 'A-Za-z0-9_-')
STATE="${AGENTIC_BIOFLOW_STATE_DIR:-${XDG_STATE_HOME:-${HOME:-}/.local/state}/agentic-bioflow}"
MARKS="$STATE/intro-shown"
[ -n "$SID" ] && [ -e "$MARKS/$SID" ] && exit 0

# T3: jq missing/broken is now visible instead of silent - see the file
# header. A SEPARATE marker from $MARKS: that one means "the overview or the
# nudge was shown", this one means "jq was found broken", and the two answer
# different questions - jq being reinstalled mid-session should not be
# blocked from ever showing the real overview by a marker written while it
# was still broken.
JQMARKS="$STATE/jq-warn-shown"
if ! command -v jq >/dev/null 2>&1 || ! printf '{}' | jq -e . >/dev/null 2>&1; then
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

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$IS_LITERAL" = 1 ]; then
    EVENT=$(jq -r '
        if .tool_name == "Skill" then
            (if ((.tool_input.skill // "") | startswith("agentic-bioflow:")) then "PostToolUse" else "" end)
        elif ((.prompt // "") | test("^\\s*/agentic-bioflow:")) then "UserPromptSubmit"
        else "" end' <<<"$INPUT") || exit 0
    [ -n "$EVENT" ] || exit 0

    INTRO="$(bash "$ROOT/scripts/intro.sh")" || exit 0
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
    BANNER="$(bash "$ROOT/scripts/intro.sh" --banner 2>/dev/null)"
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
    NUDGE="$(bash "$ROOT/scripts/intro.sh" --nudge)" || exit 0
    [ -n "$NUDGE" ] || exit 0
    jq -n --arg m "$NUDGE" \
      '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $m}}' || exit 0
fi

# Marked only after something went out, so a failure above leaves the next
# use free to try again. Markers are a few bytes each; a month is long past
# any session anyone resumes.
if [ -n "$SID" ] && mkdir -p "$MARKS"; then
    : > "$MARKS/$SID"
    find "$MARKS" -type f -mtime +30 -exec rm -f {} + 2>/dev/null
fi
exit 0
