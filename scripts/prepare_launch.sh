#!/bin/bash
# Nothing existing: no tool bundles "resolve this pipeline's revision, fetch
# its schema, check whether it is already registered, draft a samplesheet
# from a directory of reads, and check the site is ready" as one call - each
# half already exists somewhere in this plugin (nf-core's own CLI, this
# repo's preflight.sh) or has to read a pipeline's own repository, which no
# outside tool does on this plugin's behalf.
#
# The largest single change from GitHub issue #13's latency accounting:
# `commands/launch.md` steps 1-6 used to be a long, sequential chain of `tw`/
# schema/samplesheet/preflight calls, each one its own tool call and
# therefore its own full model round trip (20-40 of them across a whole
# launch walk). Everything in that chain that needs no judgement - looking
# up a revision, fetching a schema, checking registration, drafting a
# samplesheet, running preflight - runs here in one call instead. What is
# left in commands/launch.md is exactly the part that DOES need judgement:
# putting the results in front of the user and asking what they decide.
#
#   prepare_launch.sh --repo <owner/name> [--revision <rev>] [--input <dir>]
#                      [--workspace <ws>] [--fixture-dir <dir>]
#                      [--project <name>] [--run <run-dir-name>]
#                      [--samplesheet <path>]
#
# --project/--run/--samplesheet are optional because step 0 may run this
# before the user has named them. Given, they add two sections: `paths`
# (where the run lands on the site and where its results come back to on
# this machine, from scripts/where.sh --run-paths) and `in flight` (whether
# this project+samplesheet is already running, and whether this member is
# near the site's session cap). Both are advisory - they feed == decisions ==
# and never block on their own.
#
# --revision, if not given, is resolved to the newest tag on the pipeline's
# own repo (the same `git ls-remote --tags` nf-core's own CLI already uses,
# PITFALLS 29) - and flagged in the summary as something the user must
# confirm, never launched on silently: invariant 6's "any pipeline, no
# configuration" does not extend to "no confirmation either".
#
# --fixture-dir points at a local checkout (or a test fixture built to look
# like one) and, when given, every pipeline file below is read from under it
# instead of fetched from the network - `<dir>/nextflow_schema.json`,
# `<dir>/assets/schema_input.json`, `<dir>/conf/base.config`. This is not
# testing-only plumbing bolted on afterward: it is the same seam a member
# who already has the pipeline cloned locally would want, and it is what
# tests/prepare_launch_test.sh uses to run with no network at all.
#
# --- Never stops at the first problem ---------------------------------------
# Every check below runs regardless of what an earlier one found, and the
# summary's final `== decisions ==` section lists every blocking and every
# warning-level issue together, once, at the end - never one problem at a
# time across several turns. A launch walk that stops at the first FAIL and
# waits to be re-run is exactly the round-trip cost this file exists to cut.
#
# --- Adding a section ---------------------------------------------------------
# The summary is a flat, ordered list of `== <name> ==` sections, each built
# by a block below that calls add_section. A new section may append to
# $BLOCKING/$WARNINGS/$DECISIONS (newline-separated, one entry per line) and
# the final == decisions == rollup picks it up with no other change. `paths`
# and `in flight` are the two added this way (scripts/where.sh,
# scripts/duplicate_run_check.sh, scripts/parallel_watch_check.sh).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

REPO="" REVISION="" INPUT="" WORKSPACE="" FIXTURE="" PROJECT="" RUN="" SAMPLESHEET=""
while [ $# -gt 0 ]; do
    case "$1" in
        --repo)        REPO="${2:?usage: --repo <owner/name>}"; shift 2 ;;
        --revision)    REVISION="${2:?usage: --revision <rev>}"; shift 2 ;;
        --input)       INPUT="${2:?usage: --input <dir>}"; shift 2 ;;
        --workspace)   WORKSPACE="${2:?usage: --workspace <id>}"; shift 2 ;;
        --fixture-dir) FIXTURE="${2:?usage: --fixture-dir <dir>}"; shift 2 ;;
        --project)     PROJECT="${2:?usage: --project <name>}"; shift 2 ;;
        --run)         RUN="${2:?usage: --run <run-dir-name>}"; shift 2 ;;
        --samplesheet) SAMPLESHEET="${2:?usage: --samplesheet <path>}"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
[ -n "$REPO" ] || { echo "usage: prepare_launch.sh --repo <owner/name> [--revision <rev>] [--input <dir>] [--workspace <ws>] [--fixture-dir <dir>] [--project <name>] [--run <name>] [--samplesheet <path>]" >&2; exit 2; }

WORKSPACE="${WORKSPACE:-$(setting workspace_id)}"
TW="${TW_BIN:-$(setting tw_bin)}"; [ -n "$TW" ] || TW="$(command -v tw 2>/dev/null || true)"

BLOCKING=""; WARNINGS=""; DECISIONS=""
add_blocking()  { BLOCKING="${BLOCKING}${BLOCKING:+$'\n'}$1"; }
add_warning()   { WARNINGS="${WARNINGS}${WARNINGS:+$'\n'}$1"; }
add_decision()  { DECISIONS="${DECISIONS}${DECISIONS:+$'\n'}$1"; }

SECTIONS=""   # accumulates rendered "== name ==\n...\n" blocks, in order
add_section() {   # add_section <name> <<<"$body"
    local name="$1"; shift
    SECTIONS="${SECTIONS}== ${name} ==
$1
"
}

# fetch_pipeline_file <path-relative-to-repo-root> -> file content on stdout,
# nonzero on failure. Never caches anything (invariant 6): a fixture-dir read
# is a local checkout the caller already has, not a copy this plugin keeps.
fetch_pipeline_file() {
    local path="$1"
    if [ -n "$FIXTURE" ]; then
        [ -r "$FIXTURE/$path" ] && cat "$FIXTURE/$path" || return 1
        return 0
    fi
    command -v curl >/dev/null 2>&1 || return 1
    curl -fsSL "https://raw.githubusercontent.com/$REPO/$REVISION/$path" 2>/dev/null
}

# --- revision --------------------------------------------------------------
AUTO_REVISION=0
if [ -z "$REVISION" ]; then
    AUTO_REVISION=1
    if [ -n "$FIXTURE" ] && [ -r "$FIXTURE/.revision" ]; then
        REVISION="$(cat "$FIXTURE/.revision")"
    elif command -v git >/dev/null 2>&1; then
        # The newest tag, the same source nf-core's own CLI reads (PITFALLS
        # 29) - sorted by version, not by ref order, which git ls-remote does
        # not guarantee.
        REVISION="$(git ls-remote --tags --refs "https://github.com/$REPO.git" 2>/dev/null \
            | sed 's#.*refs/tags/##' | sort -V | tail -1)"
    fi
    [ -n "$REVISION" ] || REVISION="(could not be resolved)"
fi

# --- registered? -------------------------------------------------------------
REGISTERED="unknown (tw or a token is unavailable in this shell)"
if [ -x "$TW" ] && { [ -n "${TOWER_ACCESS_TOKEN:-}" ] || [ -r "$(token_file)" ]; }; then
    [ -n "${TOWER_ACCESS_TOKEN:-}" ] || TOWER_ACCESS_TOKEN="$(cat "$(token_file)" 2>/dev/null)"
    LIST=$(TOWER_ACCESS_TOKEN="$TOWER_ACCESS_TOKEN" "$TW" pipelines list \
             ${WORKSPACE:+--workspace "$WORKSPACE"} 2>/dev/null || true)
    if [ -n "$LIST" ]; then
        if grep -qF "$REPO" <<<"$LIST" && grep -qF "$REVISION" <<<"$LIST"; then
            REGISTERED="yes, at $REVISION"
        else
            REGISTERED="no - \`tw pipelines add\` will be needed before launch"
        fi
    fi
fi

PIPELINE_BODY="repo: $REPO
revision: $REVISION$([ "$AUTO_REVISION" = 1 ] && echo ' (no revision given - resolved automatically, newest tag)')
registered: $REGISTERED"
add_section pipeline "$PIPELINE_BODY"

# --- paths -------------------------------------------------------------------
# Both absolute paths, said before anything is launched, so the user can
# change where results land now rather than find out afterwards. Asked of
# where.sh, which builds them with the same functions init_workspace.sh uses,
# so this can never name a directory the run will not actually use.
if [ -n "$PROJECT" ] && [ -n "$RUN" ]; then
    RP_OUT="$(bash "$HERE/where.sh" --run-paths "$PROJECT" "$RUN" 2>&1)"
    if [ $? -eq 0 ]; then
        add_section paths "site run dir:     $(sed -n 's/^site_run_dir=//p' <<<"$RP_OUT")
local fetch dir:  $(sed -n 's/^local_fetch_dir=//p' <<<"$RP_OUT")"
        add_decision "confirm where results land (== paths ==), or name another local folder for this run"
    else
        add_section paths "could not work out the paths: $RP_OUT"
        add_warning "paths unknown - where.sh --run-paths failed"
    fi
fi
[ "$AUTO_REVISION" = 1 ] && [ "$REVISION" != "(could not be resolved)" ] && \
    add_decision "confirm the resolved revision ($REVISION) - it was not given, only picked as the newest tag"
[ "$REVISION" = "(could not be resolved)" ] && \
    add_blocking "no revision was given and none could be resolved automatically - ask the user to pin one"
case "$REGISTERED" in
    no\ -*) add_decision "register the pipeline before launch: \`tw pipelines add\`" ;;
    unknown*) add_warning "could not check whether the pipeline is already registered - $REGISTERED" ;;
esac

# --- samplesheet draft -------------------------------------------------------
SCHEMA_INPUT="$(fetch_pipeline_file assets/schema_input.json || true)"
COLUMNS=""
# pick_python(), not `command -v python3`: on Windows `python3` is the
# Microsoft Store alias, which PATH finds and which then runs nothing
# (PITFALLS 20c). With the old test both this section and == parameters ==
# came out silently empty there, and the model went on to read this script's
# source to work out what it should have said (2.15.0 Windows verification).
PY="$(pick_python)" || PY=""
[ -n "$PY" ] || add_warning "no working Python interpreter (tried: $PICK_PYTHON_CANDIDATES) - samplesheet columns and parameter groups could not be read"
if [ -n "$SCHEMA_INPUT" ] && [ -n "$PY" ]; then
    COLUMNS="$("$PY" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
props = (d.get("items") or {}).get("properties") or d.get("properties") or {}
print(",".join(props.keys()))
' <<<"$SCHEMA_INPUT" 2>/dev/null)"
fi

SS_BODY=""
if [ -z "$INPUT" ]; then
    SS_BODY="skipped - no --input directory given"
    add_decision "no input directory given - a samplesheet still needs one before launch"
elif [ ! -d "$INPUT" ]; then
    SS_BODY="cannot list $INPUT from here - if this is a site path under reach:ssh,
list it with \`scripts/on_site.sh ls $INPUT\` and draft the samplesheet from
what that returns"
    add_warning "samplesheet draft skipped - $INPUT is not readable from here"
else
    # A minimal, honest draft: pair *_R1*/*_R2* fastq files by the sample
    # name left after stripping the R1/R2 token - the same shape
    # bin/fastq_dir_to_samplesheet.py and generate_samplesheet.py already
    # use, not a second, competing convention. Anything the filenames
    # cannot tell you (patient, lane, condition) is explicitly NOT guessed
    # here - launch.md step 4 already says to ask the user for those.
    ROWS="$(find "$INPUT" -maxdepth 1 -type f \( -iname '*_R1*.f*q.gz' -o -iname '*_R1*.f*q' \) 2>/dev/null | sort)"
    N=0; SAMPLE_LINES=""
    while IFS= read -r r1; do
        [ -n "$r1" ] || continue
        N=$((N + 1))
        base="$(basename "$r1")"
        sample="$(sed -E 's/_R1.*$//' <<<"$base")"
        r2="$(sed -E 's/_R1/_R2/' <<<"$r1")"
        [ -f "$r2" ] || r2="(no R2 found)"
        if [ "$N" -le 3 ]; then
            SAMPLE_LINES="${SAMPLE_LINES}${SAMPLE_LINES:+$'\n'}  $sample  $(basename "$r1")  $(basename "$r2")"
        fi
    done <<<"$ROWS"
    if [ "$N" = 0 ]; then
        SS_BODY="input: $INPUT
rows: 0 - no *_R1*.f*q.gz files found; this directory may hold something
other than paired-end reads, or use a different naming convention"
        add_warning "no fastq pairs found under $INPUT by the *_R1*/*_R2* convention"
    else
        SS_BODY="input: $INPUT
columns (assets/schema_input.json${FIXTURE:+, from fixture}): ${COLUMNS:-unknown - schema_input.json not read}
rows: $N
$SAMPLE_LINES$([ "$N" -gt 3 ] && echo "
  ... and $((N - 3)) more")"
    fi
fi
add_section samplesheet "$SS_BODY"

# --- in flight ---------------------------------------------------------------
# One member often runs several analyses at once from one conversation. Two
# ways that goes wrong are cheap to catch here: relaunching something that
# is already running, and opening more watches than the site's session cap
# allows (PITFALLS 16e - past it, calls hang instead of failing). Both
# helpers are advisory: exit 1 means "say this", never "stop".
IF_BODY=""
ME="$(setting seqera_user)"
PW_OUT="$(bash "$HERE/parallel_watch_check.sh" ${WORKSPACE:+--workspace "$WORKSPACE"} ${ME:+--user "$ME"} 2>/dev/null)"
[ $? -eq 1 ] && { IF_BODY="$PW_OUT"; add_decision "$PW_OUT"; }
if [ -n "$PROJECT" ] && [ -n "$SAMPLESHEET" ]; then
    DUP_OUT="$(bash "$HERE/duplicate_run_check.sh" --project "$PROJECT" --samplesheet "$SAMPLESHEET" \
               ${WORKSPACE:+--workspace "$WORKSPACE"} ${ME:+--user "$ME"} 2>/dev/null)"
    if [ $? -eq 1 ]; then
        IF_BODY="${IF_BODY}${IF_BODY:+$'\n'}$DUP_OUT"
        add_decision "this looks like a run already in flight - see == in flight == before launching again"
    fi
fi
add_section "in flight" "${IF_BODY:-nothing else of yours is running with this project and samplesheet}"

# --- preflight ---------------------------------------------------------------
PF_OUT=""
if [ -x "$HERE/preflight.sh" ]; then
    PF_OUT="$(bash "$HERE/preflight.sh" 2>&1)"
    PF_RC=$?
else
    PF_OUT="preflight.sh not found beside this script"
    PF_RC=2
fi
add_section preflight "$PF_OUT"
while IFS= read -r line; do
    case "$line" in
        FAIL*) add_blocking "preflight: $(sed -E 's/^FAIL[[:space:]]+//' <<<"$line")" ;;
    esac
done <<<"$PF_OUT"

# --- parameters needing a user decision --------------------------------------
# The source URL is printed even when --fixture-dir was used (it is simply
# labelled as such) - not decoration: commands/launch.md tells the caller to
# show this whole summary to the user as its own text, and
# hooks/confirm_walkthrough.sh's G2 gate looks for exactly this URL in an
# assistant text block as its evidence that the schema was read before
# params.yaml gets written (docs/PITFALLS.md 18/33 - the same "evidence has
# to reach the transcript" rule step 2's diagram is built around). Printing
# the literal URL here is what lets a caller who displays this summary
# verbatim satisfy that gate without a second, separate fetch.
SCHEMA_URL="https://raw.githubusercontent.com/$REPO/$REVISION/nextflow_schema.json"
SCHEMA="$(fetch_pipeline_file nextflow_schema.json || true)"
PARAM_BODY="source: ${FIXTURE:+(from --fixture-dir; the real URL would be) }$SCHEMA_URL"
if [ -n "$SCHEMA" ] && [ -n "$PY" ]; then
    PARAM_BODY="$PARAM_BODY
$("$PY" -c '
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    print("nextflow_schema.json did not parse as JSON")
    sys.exit(0)
groups = d.get("definitions") or d.get("$defs") or {}
required_no_default = []
lines = []
for gname, g in groups.items():
    props = g.get("properties") or {}
    req = set(g.get("required") or [])
    lines.append("%s (%d parameters)" % (g.get("title", gname), len(props)))
    for pname, p in props.items():
        if pname in req and "default" not in p:
            required_no_default.append(pname)
print("groups:")
for l in lines:
    print("  " + l)
print("required with no default: " + (", ".join(required_no_default) if required_no_default else "(none)"))
' <<<"$SCHEMA" 2>/dev/null)"
    REQ_LIST="$(sed -n 's/^required with no default: //p' <<<"$PARAM_BODY")"
    if [ -n "$REQ_LIST" ] && [ "$REQ_LIST" != "(none)" ]; then
        add_decision "parameters required with no default: $REQ_LIST"
    fi
else
    PARAM_BODY="$PARAM_BODY
nextflow_schema.json could not be read${FIXTURE:+ from $FIXTURE} - route ③ (go through the schema) cannot be offered until it is"
    add_warning "nextflow_schema.json unavailable - parameter groups not listed"
fi

BASE_CONFIG="$(fetch_pipeline_file conf/base.config || true)"
if [ -n "$BASE_CONFIG" ]; then
    if grep -qE 'accelerator' <<<"$BASE_CONFIG"; then
        PARAM_BODY="$PARAM_BODY
conf/base.config: names an 'accelerator' (GPU) directive - the GPU path is
not yet verified anywhere here; needs an explicit decision from the user"
        add_decision "conf/base.config requests a GPU (accelerator) - not yet verified on this deployment; confirm with the user before launching"
    else
        PARAM_BODY="$PARAM_BODY
conf/base.config: no accelerator/GPU directive found"
    fi
fi
add_section parameters "$PARAM_BODY"

# --- decisions (the rollup every other section fed) --------------------------
DEC_BODY=""
if [ -n "$BLOCKING" ]; then
    while IFS= read -r l; do DEC_BODY="${DEC_BODY}${DEC_BODY:+$'\n'}BLOCKING: $l"; done <<<"$BLOCKING"
fi
if [ -n "$WARNINGS" ]; then
    while IFS= read -r l; do DEC_BODY="${DEC_BODY}${DEC_BODY:+$'\n'}WARNING: $l"; done <<<"$WARNINGS"
fi
if [ -n "$DECISIONS" ]; then
    while IFS= read -r l; do DEC_BODY="${DEC_BODY}${DEC_BODY:+$'\n'}DECIDE: $l"; done <<<"$DECISIONS"
fi
[ -n "$DEC_BODY" ] || DEC_BODY="(nothing blocking, no warnings, nothing left for the user to decide from this call alone - project/parameter-route choices from launch.md's own steps still apply)"
add_section decisions "$DEC_BODY"

printf '%s' "$SECTIONS"

# Exit 1 only when something here is genuinely blocking (docs/PRINCIPLES.md
# invariant 10's "one path, not an improvised one": a caller that ignores
# this and launches anyway is a choice the command layer can still make, but
# the summary itself has to say plainly that it found a reason not to).
[ -z "$BLOCKING" ]
