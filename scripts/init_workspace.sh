#!/bin/bash
# T11: give the run area a designed shape.
#
# Nothing existing: no tool builds this lab's specific project/run/analysis/
# package directory shape - before this script it accreted by hand, which is
# the exact mess measured just below.
#
# Measured, not guessed: a real run area was two things at once - probe
# directories from setup rehearsals (_boxtest, _coldstart, _coldstart2,
# _coldstart_s4, _net_probe, _relay_probe, _coscientist_eval, _exttest) sitting
# beside real analyses with no boundary between them, and a second run area
# elsewhere shaped differently again (rawdata/ results/ _work/ at the top,
# instead of per-member). Nothing had ever decided the shape; it accreted.
#
# This script is the shape, made real. It creates either side - never both in
# one call, because they are two different machines - and it is deliberately
# dumb about *how* the site is reached: reach (none/local/ssh, contract 6 in
# docs/SITE_ADAPTER.md) is a command-layer decision, not this script's. Run it
# where you want the directories to appear: directly for reach:local or the
# local side, through scripts/on_site.sh --script for reach:ssh's site side.
#
#   init_workspace.sh site  [--user <u>] [--project <p>] [--run <name>]
#   init_workspace.sh local --user <u> [--project <p>] [--run <name>] [--root <path>]
#
#   --plan   print `would-create: <path>`, one line per directory this call
#            would make that does not already exist, then exit 0 having
#            created NOTHING. Drives the same DIRS list the real run builds -
#            see the loop that appends to it below - so the plan can never
#            drift from what actually gets made. D3, docs/SETTINGS.md.
#
# A **project** is the unit everything is collected under: the raw data that
# feeds it, every run made from that data, the analysis written on those runs,
# and the package built from the analysis. Runs used to sit directly under a
# member and analysis directly under a run, which made two things awkward that
# turn out to be the normal case - one batch of reads feeding several runs, and
# one write-up drawing on several runs. Naming the project once puts all four
# in one place and gives the walkthrough gate a subject it can resolve on the
# filesystem rather than parse out of a path.
#
#   --user   the Seqera username (Username column of `tw runs list`). The site
#            is one shared Unix account, so this is what tells members' runs
#            apart - not $USER, which is the same for everyone. May not start
#            with '_': that prefix is reserved for the shared areas below.
#
#            Required on the local side, which has no shared area to fall
#            back to. Optional on the site side, because setup asks for it in
#            a later step than "where the work will live": call this once
#            without --user to lay down _personal/, _references/,
#            _singularity_cache/ and _system/ (nothing about them needs
#            to know who the member is), and again with --user once Seqera
#            has answered, to add that member's rawdata/ and runs/. Both
#            calls are idempotent, so doing it in two passes costs nothing.
#   --project  the project this work belongs to. Optional here for the same
#            reason --user is: setup lays the skeleton down before anyone has
#            named a project, and `launch` asks for one before it starts a run.
#   --run    also scaffold one run's own subdirectories
#            (projects/<project>/runs/<pipeline>_<label>_<YYYYMMDD>/...).
#            Needs --project: a run belongs to one.
#   --root   local side only. Overrides the `local_root` setting for this one
#            call; falls back to it otherwise, and to $HOME/agentic-bioflow
#            when neither is set. docs/SETTINGS.md.
#
# Idempotent: every directory is made with `mkdir -p`, which by construction
# never touches anything already inside an existing one - the same guarantee
# `hooks/confirm_cleanup.sh` polices from the other direction. Run this twice
# and the second run changes nothing.
#
# Where each directory's one home is, and why they are not all on both sides:
#
#   rawdata/     both. The site's is where the compute nodes read from and is
#                the real one; the local copy is the staging area push.sh
#                sends from, which is what inbox/ used to be. Same name on
#                both sides now, so the two ends of a transfer read alike.
#   runs/        both, same names. results/ locally is a read-only replica
#                fetch.sh can re-pull at any time.
#   analysis/    local only. Interactive editing happens where the IDE is, and
#                one home beats two that drift.
#   submission/  local only, and deliberately NOT under analysis/. Deleting or
#                moving anything under analysis/ is a hard deny in
#                hooks/confirm_cleanup.sh, and a built package has to be
#                throwable-away and rebuildable. analysis/ is source;
#                submission/ is what was built from it.
#
# The names below - rawdata, results, analysis, _references and
# _singularity_cache - are not this script's invention. Each has to satisfy two
# readers at once, and PITFALLS 17 is what happens when only one is consulted:
#
#   the hook that refuses to delete it   hooks/confirm_cleanup.sh
#   the thing that writes into it        configs/sites/nchc.config
#
# The image cache was `lab_singularity_library` here because that was once the
# hook's only literal pattern, and a name the hook did not know would have been
# an unguarded directory. PITFALLS 17 fixed the hook to match the shape - all
# of `lab_singularity_library`, `_singularity_cache`, `.singularity_cache` and
# a bare `singularity` - which retired that constraint without retiring the
# name it had forced. So the skeleton went on creating a directory that was
# guarded, agreed with the comment above it, and that nothing would ever write
# an image into: nchc.config puts them in `_singularity_cache`. That is the
# same silent divergence PITFALLS 17 is about, one file over, and it survived
# the fix because the justification for the wrong name outlived its reason.
# The name below is now the one the config resolves to, and
# tests/init_workspace_test.sh checks it against that file rather than against
# this comment.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }

SIDE="${1:-}"
case "$SIDE" in
    site|local) shift ;;
    *) die 2 "usage: init_workspace.sh site|local --user <seqera_user> [--run <name>] [--root <path>]" ;;
esac

USER_NAME="" PROJECT="" RUN_NAME="" ROOT_ARG="" PLAN=0
while [ $# -gt 0 ]; do
    case "$1" in
        --user)    USER_NAME="${2:?--user needs a value}"; shift 2 ;;
        --project) PROJECT="${2:?--project needs a value}"; shift 2 ;;
        --run)     RUN_NAME="${2:?--run needs a value}"; shift 2 ;;
        --root)    ROOT_ARG="${2:?--root needs a value}"; shift 2 ;;
        --plan)    PLAN=1; shift ;;
        *) die 2 "unknown option '$1'" ;;
    esac
done

if [ "$SIDE" = local ]; then
    [ -n "$USER_NAME" ] || die 2 "--user is required on the local side." \
        "There is no shared area here to fall back to - everything local is" \
        "under one member's own name. See docs/SETTINGS.md (seqera_user)."
fi
[ -n "$PROJECT" ] && [ -z "$USER_NAME" ] \
    && die 2 "--project needs --user - a project belongs to one member."
[ -n "$RUN_NAME" ] && [ -z "$PROJECT" ] \
    && die 2 "--run needs --project - a run belongs to one project." \
             "Ask which project this run is part of, or start a new one, before" \
             "launching it. See commands/launch.md."
if [ -n "$USER_NAME" ]; then
    case "$USER_NAME" in
        */*|.|..) die 2 "--user '$USER_NAME' must be a bare name, not a path." ;;
        _*) die 2 "--user '$USER_NAME' starts with '_'." \
                 "That prefix is reserved for the shared areas this script also" \
                 "creates (_personal, _references, _system) and would collide with one." ;;
    esac
fi
for pair in "project:$PROJECT" "run:$RUN_NAME"; do
    what="${pair%%:*}" val="${pair#*:}"
    [ -n "$val" ] || continue
    case "$val" in
        */*|.|..) die 2 "--$what '$val' must be a bare directory name, not a path." ;;
    esac
done

# mkdir -p is the whole idempotency and non-destructive guarantee: it creates
# what is missing and leaves what already exists - files inside included -
# completely alone.
make() { mkdir -p "$1" || die 1 "could not create '$1'"; }

DIRS=()

if [ "$SIDE" = site ]; then
    BASE="${LAB_RUNS_DIR:-$(setting storage_root)}"
    [ -n "$BASE" ] || die 2 "no run area known." \
        "Set LAB_RUNS_DIR, or 'storage_root' in the deployment settings - this is" \
        "step 1 of setup and everything else derives from it. See docs/SETTINGS.md."
    BASE="${BASE%/}"

    # The image cache has three readers, not two, and the third one wins.
    # nchc.config falls back to "$LAB_RUNS_DIR/_singularity_cache" only when
    # NXF_SINGULARITY_CACHEDIR is unset - and ce_apply.sh sets it, from the
    # `singularity_cache` setting, on every deployment that has one. Creating
    # the fallback name regardless is how this directory came to be empty in
    # the first place (PITFALLS 17, then 19): a name that satisfies the guard
    # and the comment, and that nothing ever writes an image into. So resolve
    # it the way the run itself will, and build that. It is often outside the
    # run area, which is why the tree below prints it as an absolute path.
    CACHE="$(setting singularity_cache "$BASE/_singularity_cache")"
    DIRS+=(
        "$BASE/_personal"
        "$BASE/_references"
        "$CACHE"
        "$BASE/_system/agent"
        "$BASE/_system/relay"
        "$BASE/_system/coldstart"
    )
    if [ -n "$USER_NAME" ]; then
        DIRS+=("$BASE/$USER_NAME/projects")
    fi
    if [ -n "$PROJECT" ]; then
        PROJ_DIR="$BASE/$USER_NAME/projects/$PROJECT"
        DIRS+=("$PROJ_DIR/rawdata" "$PROJ_DIR/runs")
    fi
    if [ -n "$RUN_NAME" ]; then
        RUN_DIR="$PROJ_DIR/runs/$RUN_NAME"
        DIRS+=("$RUN_DIR/logs" "$RUN_DIR/results" "$RUN_DIR/work")
    fi
else
    # local_root (docs/SETTINGS.md): the same key scripts/inspect_sides.sh
    # reads, so "where this builds" and "where inspect_sides.sh looks" cannot
    # drift apart. --root still wins outright, for a one-off call that should
    # not need a settings edit.
    BASE="${ROOT_ARG:-$(setting local_root "$HOME/agentic-bioflow")}"
    BASE="${BASE%/}"

    # T21/T29: local_root and portable_root are allowed to be synced folders -
    # warn, do not refuse. Skipped under --plan: a plan is read-only
    # reconnaissance, and printing a stderr caution about a directory nothing
    # is about to touch yet would fire on every dry run of a path someone is
    # still deciding on.
    if [ "$PLAN" != 1 ]; then
        cloud_sync_caution "$BASE" local_root
        [ -z "$PORTABLE_ROOT" ] || cloud_sync_caution "$PORTABLE_ROOT" portable_root
    fi

    # T29: no unconditional "$BASE/$USER_NAME/projects" placeholder any more.
    # Under the new layout (below) there is no fixed per-user directory to
    # lay down ahead of time - making one without a project name would BE the
    # old, <seqera_user>-layered shape by accident, for a member who may never
    # end up using it. With a project name, local_project_base()/
    # local_analysis_base() (scripts/settings.sh) decide old vs new layout,
    # and where analysis/submission actually live, in the one place
    # scripts/where.sh also reads them from - so the two can never disagree.
    if [ -n "$PROJECT" ]; then
        PROJ_DIR="$(local_project_base "$BASE" "$USER_NAME" "$PROJECT")"
        ANALYSIS_DIR="$(local_analysis_base "$BASE" "$USER_NAME" "$PROJECT")"
        DIRS+=("$PROJ_DIR/rawdata" "$PROJ_DIR/runs"
               "$ANALYSIS_DIR/analysis" "$ANALYSIS_DIR/submission")
    fi
    if [ -n "$RUN_NAME" ]; then
        DIRS+=("$PROJ_DIR/runs/$RUN_NAME/results")
    fi
fi

# D3: the plan is read off this exact list, before anything runs make() on
# it. One source for "what would be built" and "what gets built" - a second,
# hand-maintained list here is exactly how the two would drift.
if [ "$PLAN" = 1 ]; then
    for d in "${DIRS[@]}"; do
        [ -e "$d" ] || echo "would-create: $d"
    done
    exit 0
fi

for d in "${DIRS[@]}"; do make "$d"; done

# _personal/ holds env.yaml and the Seqera token once setup writes them - both
# mode 600, per person. The directory itself is tightened here so nothing
# else on a shared account can even list what is in it before those files
# exist. Idempotent: chmod on an already-700 directory changes nothing.
[ "$SIDE" = site ] && chmod 700 "$BASE/_personal" 2>/dev/null

# --- the tree it made --------------------------------------------------------
# Fixed, not scanned: $BASE is the run area, and on a real deployment it holds
# every other member's rawdata and every past run - `find`-ing it recursively
# would print all of that, not "the tree this call made", and would do it
# every single time this idempotent script is re-run. Print only the shape
# this call is responsible for.
echo "$BASE"
if [ "$SIDE" = site ]; then
    echo "├── _personal/"
    echo "├── _references/"
    case "$CACHE" in
        "$BASE"/*) echo "├── ${CACHE#$BASE/}/" ;;
        # Outside the run area: printing a bare basename here would draw it as
        # though it lived under $BASE, which is the misreading that matters.
        *)         echo "├── (images: $CACHE/)" ;;
    esac
    if [ -n "$USER_NAME" ]; then
        echo "├── _system/"
        echo "│   ├── agent/"
        echo "│   ├── relay/"
        echo "│   └── coldstart/"
        echo "└── $USER_NAME/"
        echo "    └── projects/"
        if [ -n "$PROJECT" ]; then
            echo "        └── $PROJECT/"
            echo "            ├── rawdata/"
            echo "            └── runs/"
            if [ -n "$RUN_NAME" ]; then
                echo "                └── $RUN_NAME/"
                echo "                    ├── logs/"
                echo "                    ├── results/"
                echo "                    └── work/"
            fi
        fi
    else
        echo "└── _system/"
        echo "    ├── agent/"
        echo "    ├── relay/"
        echo "    └── coldstart/"
    fi
else
    # T29: printed as real absolute paths rather than a fixed nested diagram -
    # old layout, new layout and a portable folder redirecting analysis/
    # submission elsewhere are three different shapes, and drawing all of
    # them as one indented tree would misrepresent whichever one this call
    # did not build.
    if [ -n "$PROJECT" ]; then
        echo "$PROJ_DIR"
        echo "├── rawdata/      (staging; push.sh sends this up)"
        if [ "$ANALYSIS_DIR" = "$PROJ_DIR" ]; then
            echo "├── runs/"
            if [ -n "$RUN_NAME" ]; then
                echo "│   └── $RUN_NAME/"
                echo "│       └── results/"
            fi
            echo "├── analysis/     (source: analysis.md, scripts, figures)"
            echo "└── submission/   (built package; safe to throw away)"
        else
            echo "└── runs/"
            if [ -n "$RUN_NAME" ]; then
                echo "    └── $RUN_NAME/"
                echo "        └── results/"
            fi
            echo
            echo "analysis/ and submission/ live in the portable folder instead (T23):"
            echo "$ANALYSIS_DIR"
            echo "├── analysis/     (source: analysis.md, scripts, figures)"
            echo "└── submission/   (built package; safe to throw away)"
        fi
    else
        echo "$BASE"
        echo "(no --project given yet - nothing built on the local side until there is one)"
    fi
fi
