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

# `command -v jq` would only prove a FILE exists. A jq that cannot run -
# wrong architecture, a missing shared library, or a Windows jq.exe that
# Git Bash finds but cannot execute - passes that check and then fails
# every parse below, which is the exact silent-gate failure this guard
# exists to stop. So ask jq to do its job on the smallest possible input.
if ! printf '{}' | jq -e . >/dev/null 2>&1; then
    cat >&2 <<'EOF'
BLOCKED: jq is missing or cannot run here, so hooks/confirm_cleanup.sh cannot read
what this command would delete - and cannot tell `rm -rf results/` from `ls`.
Rather than silently stop checking (the old, dangerous behaviour), it refuses
every Bash command until jq exists. The same is true of confirm_launch.sh and
confirm_walkthrough.sh, which share this requirement.

Install it yourself (this hook will not attempt to), then retry:
  macOS:       brew install jq
  Debian/WSL:  sudo apt install jq
EOF
    exit 2
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -n "$CMD" ] || exit 0

# Drop here-doc bodies: a document containing a path example is not a command
# operating on that path, but the per-line segment scan below could not tell the
# difference. If awk is missing this yields nothing and CMD is left as-is.
STRIPPED=$(printf '%s\n' "$CMD" | awk -f "$(dirname "$0")/strip_heredocs.awk" 2>/dev/null)
[ -n "$STRIPPED" ] && CMD="$STRIPPED"

deny() {
    jq -n --arg m "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse",
        permissionDecision: "deny", permissionDecisionReason: $m}}'
    exit 0
}
warn() {
    jq -n --arg m "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $m}}'
    exit 0
}

# `ssh <host> '<payload>'` hides a delete from every check below: the payload is
# quoted, so the delete verb sits behind a quote rather than at a segment
# boundary, and the command word is `ssh`. The far-side shell runs it anyway.
# Scan the payload as its own segment - appended rather than substituted,
# because the wrapper's own arguments still deserve checking.
PAYLOAD=""
if echo "$CMD" | grep -qE '(^|[[:space:]])([^[:space:]]*/)?(ssh|on_site\.sh)[[:space:]]'; then
    PAYLOAD=$(echo "$CMD" | grep -oE "'[^']*'|\"[^\"]*\"" | sed -E "s/^['\"]//; s/['\"]$//")
fi

# Quoted content is data, not commands. `grep -n 'A\|rm ' file` used to split on
# the `|` inside the regex, leaving a segment that began with the delete verb -
# so a read-only search was denied. This really happened while planning v2.1.
# Strip quoted strings before segmenting; the wrapper payload above was taken
# from the unstripped command precisely because there the quotes are a shell.
SEGSRC=$(echo "$CMD" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g")

# Split into segments so one command's arguments are not attributed to another.
SEGMENTS=$(printf '%s\n%s' "$SEGSRC" "$PAYLOAD" | sed -E 's/(\|\||&&|[;&|])/\n/g')

UNRESOLVED=""
HIT_OVERWRITE=""
HIT_SHARED=""
HIT_PROTECTED=""
HIT_PLUGINS=""
HIT_WORK=""
HIT_SEQFILE=""
HIT_LEFTOVER=""
HIT_ROOT=""

while IFS= read -r SEG; do
    [ -n "$SEG" ] || continue

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
    # Must be the command word, not those two letters anywhere in the line. The
    # glob this replaces matched the tail of "confirm " and of "Platform run",
    # so `echo confirm the results directory` was denied outright - and this
    # project's own prose mentions Seqera Platform constantly.
    echo "$SEG" | grep -qE '(^|[[:space:]]|[;&|(])(sudo[[:space:]]+)?(rm|rmdir)([[:space:]]|$)' \
        && DESTRUCTIVE=1
    echo "$SEG" | grep -qE '\bfind\b.*-delete|\brsync\b.*--delete|\bshred\b' && DESTRUCTIVE=1
    # "2>/dev/null" appears in nearly every snippet this plugin's own commands
    # tell the assistant to run, and the old pattern ('>[[:space:]]*/') matched
    # it - so read-only `du`/`ls`/`jq` lines were classified destructive. A guard
    # that cries wolf on `du -sh "$RESULTS" 2>/dev/null` teaches the reader to
    # ignore it. Drop /dev/null redirects before testing.
    # One stripped copy, used by both the truncation test and the argument list
    # below. It used to be produced inline here and thrown away, so the token
    # `2>/dev/null` survived into ARGS and matched the leftover rule's `null`
    # pattern - `rm -rf /tmp/x 2>/dev/null` was reported as an nf-core null/
    # directory. The exception for a bare `/dev/null` argument further down
    # never saw this form, because the redirection operator is glued to it.
    SEG_NR=$(echo "$SEG" | sed -E 's/[0-9]*>&?[[:space:]]*\/dev\/null//g')
    echo "$SEG_NR" | grep -qE '>[[:space:]]*/' && TRUNCATE=1
    if echo "$SEG" | grep -qE '(^|[[:space:]])mv([[:space:]]|$)'; then MOVE_ONLY=1; fi
    [ "$DESTRUCTIVE" = 1 ] || [ "$TRUNCATE" = 1 ] || [ "$MOVE_ONLY" = 1 ] || continue

    # Arguments only: drop the leading command word and anything that looks like a flag.
    ARGS=$(echo "$SEG_NR" \
        | sed -E 's/^[[:space:]]*(sudo[[:space:]]+)?[A-Za-z0-9_\/.-]+[[:space:]]*//' \
        | tr ' \t' '\n\n' \
        | grep -v '^-' | grep -v '^$')

    while IFS= read -r A; do
        [ -n "$A" ] || continue
        A=$(echo "$A" | sed -E 's/^["'"'"']//; s/["'"'"']$//')

        # Cannot resolve a target that still holds a variable or substitution.
        # Only worth saying for a delete: "$RUN_DIR/analysis/x.R" as the target
        # of a redirect is the ordinary way every task file gets written, and
        # warning on each one buries the warning that matters.
        case "$A" in
            *'$'*|*'`'*)
                [ "$DESTRUCTIVE" = 1 ] && UNRESOLVED="${UNRESOLVED}${A} "
                continue ;;
        esac

        if [ "$TRUNCATE" = 1 ] && [ "$DESTRUCTIVE" = 0 ]; then
            # Overwriting is worth a word only where the content is not ours to
            # replace: the user's originals and the pipeline's own output.
            # analysis/ is deliberately absent - that is where downstream code
            # and figures are supposed to be written.
            echo "$A" | grep -qE '(^|/)(rawdata|results)(/|$)' \
                && HIT_OVERWRITE="${HIT_OVERWRITE}${A} "
        fi

        if [ "$DESTRUCTIVE" = 1 ]; then
            echo "$A" | grep -qE '(^|/)\.nextflow/plugins(/|$)' && HIT_PLUGINS="${HIT_PLUGINS}${A} "
            # Shared across the whole lab: reference genomes and taxonomy
            # databases (_references/) and the read-only image library. One
            # person deleting these costs everyone else the re-download - tens
            # of GB and hours - and nothing in the deleter's own run tells them
            # that happened. Scale is what makes this a deny rather than a warn.
            #
            # The image library is matched under every spelling it has had here,
            # because this rule protected exactly one of them and it was the one
            # nobody used. configs/sites/nchc.config defaults the cache to
            # `_singularity_cache`; this deployment's NXF_SINGULARITY_CACHEDIR
            # points at `.singularity_cache`; the rule named
            # `lab_singularity_library`. So the directory actually holding the
            # images was deletable, while a principle in PRINCIPLES.md said it
            # was not. A safety net that guards a path nothing writes to is not
            # a safety net. PITFALLS 17.
            echo "$A" | grep -qE '(^|/)_references(/|$)|(^|/)[._]?(lab_)?singularity(_cache|_library)?(/|$)' \
                && HIT_SHARED="${HIT_SHARED}${A} "
            # A name-based rule cannot see the real danger here: a task dir's
            # references/ is a SYMLINK into the shared library, so its own path
            # says nothing about where it points. `rm -rf <link>` only removes
            # the link and is harmless, but `rm -rf <link>/*` deletes the lab's
            # copy. Resolve the path and judge by the destination.
            RP=$(resolve_link "$A" 2>/dev/null || true)
            if [ -n "$RP" ] && [ "$RP" != "$A" ]; then
                echo "$RP" | grep -qE '(^|/)_references(/|$)|(^|/)[._]?(lab_)?singularity(_cache|_library)?(/|$)' \
                    && HIT_SHARED="${HIT_SHARED}${A} -> ${RP} "
            fi
            echo "$A" | grep -qE '(^|/)(rawdata|results|analysis)(/|$)' && HIT_PROTECTED="${HIT_PROTECTED}${A} "
            # "work" must be a component *inside* a path, not the leading one:
            # many clusters put the execution zone under /work/$USER (or /scratch,
            # /data...), so the old '(^|/)work(/|$)' matched every single path in
            # the run dir and the scratch warning fired on everything - including
            # deletes it had no business commenting on, which buried the others.
            echo "$A" | grep -qE '^work(/|$)|.+/work(/|$)|(^|/)\.nextflow/(cache|tmp)(/|$)' \
                && HIT_WORK="${HIT_WORK}${A} "
            # A bare filesystem root is never a cleanup target. Cover the common
            # big-storage roots across clusters (not just NCHC's /work), and the
            # execution-zone root itself ($LAB_RUNS_DIR) - deleting that wholesale
            # would wipe every task, not one. Trailing slash normalized first.
            An="${A%/}"; [ -n "$An" ] || An="/"
            case "$An" in
                ""|"/"|/work|/home|/staging|/scratch|/data|/project|/projects|/work/"$USER"|/scratch/"$USER"|/data/"$USER")
                    HIT_ROOT="${HIT_ROOT}${A} " ;;
            esac
            [ -n "${LAB_RUNS_DIR:-}" ] && [ "$An" = "${LAB_RUNS_DIR%/}" ] && HIT_ROOT="${HIT_ROOT}${A} "
            # Post-/end leftovers: regenerable on the login node, no bearing on
            # results/. "null/" only exists when a launch lost its --outdir, so
            # nf-core wrote pipeline_info under the literal string "null".
            case "$A" in /dev/null) ;; *)
                echo "$A" | grep -qE '(^|/)(null|offline_data)(/|$)|(^|/)\.sendmail_tmp\.html$' \
                    && HIT_LEFTOVER="${HIT_LEFTOVER}${A} " ;;
            esac
        fi
        echo "$A" | grep -qiE '\.(fastq|fq|fasta|fa|fna|bam|cram)(\.gz)?$' && HIT_SEQFILE="${HIT_SEQFILE}${A} "
        echo "$A" | grep -qE '(^|/)(rawdata|raw_data)(/|$)' && HIT_SEQFILE="${HIT_SEQFILE}${A} "
    done <<< "$ARGS"
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
[ -n "$UNRESOLVED" ] && warn "CANNOT VERIFY: this destructive command's target is a shell variable, so the
guard cannot tell what it points at.

Unresolved: ${UNRESOLVED}

Expand it and check before running, e.g.:
  echo \"<the variable>\"
Confirm it is not rawdata/, results/, analysis/ or .nextflow/plugins/, and that
the user has said \"確認刪除\", then issue the command with the literal path."

[ -n "$HIT_OVERWRITE" ] && warn "About to write over a file under rawdata/ or results/ (${HIT_OVERWRITE}).

Neither is this plugin's to rewrite: rawdata/ is the user's original data and
results/ is what the pipeline produced. Check the path is what you meant. Files
generated by downstream analysis belong in analysis/."

[ -n "$HIT_SEQFILE" ] && warn "CAUTION: this command targets what looks like original sequencing data
(${HIT_SEQFILE}).

Never mv original data - moving it makes the task dir the only copy. Use symlink
or cp. Confirm the exact target with the user before proceeding."

[ -n "$HIT_WORK" ] && warn "About to delete Nextflow scratch (${HIT_WORK}).

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

Still confirm phase is 'completed' and that the user replied \"確認刪除\".
Note pipeline/ is NOT in this list: it is the only record of which source
revision actually ran, and compute nodes cannot re-clone it."

exit 0
