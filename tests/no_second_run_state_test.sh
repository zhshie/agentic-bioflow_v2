#!/bin/bash
# Invariant 2 (constitution I.2): the execution backend is the single source of
# truth for run state. No file in this repository MAY keep a second copy of a
# run's state, and there MUST be no submission script of our own, no state
# machine, and no monitoring daemon. Where the backend is Seqera, the command
# layer follows Seqera's nouns.
#
# This is a static scan, which is crude but catches what actually happens: a
# helpful script that "just remembers" the last status, or one that "just
# submits" a job because sbatch is right there. Four scans:
#
#   1. SUBMISSION  no script runs sbatch/qsub/bsub/srun, `nextflow run`, or
#                  `tw launch`. Launching is Platform's, behind the launch gate;
#                  scripts only prepare for it and look at its result.
#   2. DAEMON      nohup/setsid/disown/cron/inotify/`while true` appear only in
#                  the allow-list below, each entry with the reason it is not a
#                  monitoring daemon.
#   3. RUN STATE   no script creates a database or a status/state file for runs.
#   4. NOUNS       every `tw <noun>` the command layer uses is one of Seqera's
#                  own nouns (compute-envs, pipelines, datasets, launch, runs...).
#
# What it cannot see: a script that keeps run state in a file under a name
# nobody thought to list in scan 3. That is why the allow-lists are short and
# every entry carries its reason, and why a reviewer reading a diff to scripts/
# is still the last line. It is a net, not a proof.
#
# NO_RUN_STATE_ROOT points the scan at a scratch tree; the self-tests at the
# bottom use it to prove each scan can go red.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "$HERE/.." && pwd)"
ROOT="${NO_RUN_STATE_ROOT:-$DEFAULT_ROOT}"

# DAEMON allow-list: "<file>|<why it is not a monitoring daemon>"
DAEMON_ALLOW="
scripts/agent_ctl.sh|starts Seqera's own Tower Agent on the login node (the outputs reader); it carries Platform's traffic and keeps no run state of ours
scripts/egress_ctl.sh|starts the login-node outbound channel (CONNECT proxy); it relays connections and keeps no run state
scripts/on_site.sh|a bounded wait for a free session slot; it exits at its own budget and holds no state about any run
"

# Seqera CLI nouns (tw --help). The command layer may use these and no others.
TW_NOUNS=" actions collaborators compute-envs credentials data-links datasets info labels launch members organizations participants pipelines runs secrets studios teams workspaces "

fails=0
fail() { echo "$1"; fails=$((fails + 1)); }

# non-comment lines of the shipped scripts, as file:line:text
code_lines() {
    local f
    for f in "$ROOT"/scripts/*.sh "$ROOT"/scripts/*.py "$ROOT"/scripts/utils/*.sh "$ROOT"/scripts/utils/*.py; do
        [ -f "$f" ] || continue
        grep -nE '.' "$f" | grep -vE '^[0-9]+:[[:space:]]*(#|//)' | sed "s|^|${f#"$ROOT"/}:|"
    done
}
CODE=$(code_lines)

# 1. SUBMISSION -------------------------------------------------------------
CMDS='(sbatch|qsub|bsub|srun|nextflow[[:space:]]+run|tw[[:space:]]+launch)([[:space:]]|$)'
PFX='^[^:]+:[0-9]+:'
sub_hits=$(grep -E "${PFX}[[:space:]]*${CMDS}|${PFX}.*([;&|(\`]|[\$][(]|then|do|else)[[:space:]]*${CMDS}|${PFX}.*[\"']?[\$]?[{]?TW[}]?[\"']?[[:space:]]+launch([[:space:]]|$)|${PFX}.*[[(][\"'](sbatch|qsub|srun)[\"']" <<<"$CODE")
# The same commands inside a quoted string: `ssh "$HOST" 'sbatch job.sh'`,
# subprocess.run("sbatch job.sh", shell=True). A quote straight before the word
# means the string BEGINS with the command; prose that merely mentions it does not.
qs_hits=$(grep -E "${PFX}.*[\"'][[:space:]]*(sbatch|qsub|bsub|srun|nextflow[[:space:]]+run|tw[[:space:]]+launch)([[:space:]\"']|\$)" <<<"$CODE")
# SUBMIT allow-list: "<file>|<why it is not submitting>". Stale entries fail.
SUBMIT_ALLOW="
scripts/collect_provenance.py|writes the reproduction command line into the provenance record as text; never runs it
scripts/methods_text.py|writes the reproduction command line into the methods text as text; never runs it
"
if [ -n "$qs_hits" ]; then
    kept=""
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        grep -q "^${line%%:*}|" <<<"$SUBMIT_ALLOW" || kept="$kept$line"$'
'
    done <<<"$qs_hits"
    if [ -z "${NO_RUN_STATE_ROOT:-}" ]; then
        while IFS='|' read -r file _; do
            [ -n "$file" ] || continue
            grep -q "^$file:" <<<"$qs_hits" || fail "STALE  $file no longer needs its SUBMIT allow-list entry; remove it from tests/no_second_run_state_test.sh"
        done <<<"$SUBMIT_ALLOW"
    fi
    qs_hits="${kept%$'
'}"
fi
[ -z "$qs_hits" ] || sub_hits="$sub_hits"$'
'"$qs_hits"
[ -z "$sub_hits" ] || { printf '%s\n' "$sub_hits" | cut -c1-160; fail "SUBMISSION  a script submits a job itself; submission is Platform's (I.2)"; }

# 2. DAEMON -----------------------------------------------------------------
dm_hits=$(grep -E '(^|[^[:alnum:]_])(nohup|setsid|disown|crontab|systemd-run|inotifywait|launchctl)([^[:alnum:]_]|$)|while[[:space:]]+(true|:)([[:space:];]|$)|(while|until)[[:space:]][^#]*sleep|(^|[;&|[:space:]])until[[:space:]][^#]*;[[:space:]]*do([[:space:]]|$)|^[^:]+:[0-9]+:[[:space:]]*until[[:space:]]' <<<"$CODE")
while IFS= read -r line; do
    [ -n "$line" ] || continue
    file="${line%%:*}"
    if ! grep -q "^$file|" <<<"$DAEMON_ALLOW"; then
        echo "$line" | cut -c1-160
        fail "DAEMON  $file starts something that keeps running, or polls in a loop; only the allow-listed channels may (I.2)"
    fi
done <<<"$dm_hits"
# An allow-list entry that no longer matches anything is stale: remove it.
while IFS='|' read -r file _; do
    [ -n "$file" ] || continue
    [ -f "$ROOT/$file" ] || { [ -n "${NO_RUN_STATE_ROOT:-}" ] || fail "STALE  allow-listed $file does not exist"; continue; }
    grep -q "^$file:" <<<"$dm_hits" || [ -n "${NO_RUN_STATE_ROOT:-}" ] || fail "STALE  $file no longer needs its DAEMON allow-list entry; remove it from tests/no_second_run_state_test.sh"
done <<<"$DAEMON_ALLOW"

# 3. RUN STATE --------------------------------------------------------------
st_hits=$(grep -iE 'snapshot|sqlite|[.]db["'"'"' ]|run_?state|runs?_(db|cache|index)|status_cache|state[.](json|yaml|txt)|status[.](json|yaml|txt)|runs[.](json|yaml|csv)' <<<"$CODE")
# Run lists cached to a file: `tw runs list > f`, `| tee f`. Reading one into a
# variable, or discarding it (>/dev/null, 2>&1), is not caching.
CODE_NOREDIR=$(sed -E 's#[0-9]>>?&?[^[:space:]]*##g; s#>>?[[:space:]]*/dev/null##g' <<<"$CODE")
cache_hits=$(grep -E 'runs[[:space:]]+(list|view|dump)[^;&]*(>|[|][[:space:]]*tee)' <<<"$CODE_NOREDIR")
[ -z "$cache_hits" ] || st_hits="$st_hits"$'
'"$cache_hits"
[ -z "$st_hits" ] || { printf '%s\n' "$st_hits" | cut -c1-160; fail "RUN STATE  a script keeps its own copy of run state; ask the backend each time (I.2)"; }

# 4. NOUNS ------------------------------------------------------------------
bad_nouns=""
while IFS= read -r noun; do
    [ -n "$noun" ] || continue
    case "$TW_NOUNS" in *" $noun "*) ;; *) bad_nouns="$bad_nouns $noun" ;; esac
done < <(grep -rhoE '(^|[^[:alnum:]_/.-])tw[[:space:]]+[a-z][a-z-]+' "$ROOT/commands" "$ROOT/skills" 2>/dev/null \
         | sed -E 's/^.*tw[[:space:]]+//' | sort -u)
# "tw" followed by an ordinary English word is prose, not a command; the
# command layer writes `tw ...` in backticks or code blocks, and the nouns it
# uses are few. Report only words that look like a subcommand attempt and are
# not Seqera's: anything lowercase with a hyphen, or not in the prose list.
PROSE=" and the is as in on to of or a an with for it its at by be if so this that not no all any one only then than when which who will can may must does do has have are was were you your we our each per via from into out up "
real_bad=""
for n in $bad_nouns; do
    case "$PROSE" in *" $n "*) ;; *) real_bad="$real_bad $n" ;; esac
done
[ -z "$real_bad" ] || fail "NOUNS  the command layer uses 'tw <noun>' for:$real_bad - not a Seqera noun; follow Seqera's own (I.2)"

# ---------------------------------------------------------------------------
if [ "$fails" -gt 0 ]; then
    echo
    echo "FAIL: $fails problem(s) against invariant 2"
    exit 1
fi

# Self-tests --------------------------------------------------------------
if [ -z "${NO_RUN_STATE_ROOT:-}" ]; then
    S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
    selffails=0
    case_() { # case_ <label> <want-rc> <file under scratch> <line>
        rm -rf "$S/t"; mkdir -p "$S/t/scripts" "$S/t/commands" "$S/t/skills"
        printf '#!/bin/bash\n%s\n' "$4" > "$S/t/$3"
        NO_RUN_STATE_ROOT="$S/t" bash "${BASH_SOURCE[0]}" >/dev/null 2>&1; rc=$?
        [ "$rc" = "$2" ] || { echo "SELFTEST FAIL: $1 (rc $rc, wanted $2)"; selffails=$((selffails + 1)); }
    }
    case_ "a clean script passes"                 0 scripts/a.sh 'echo hello'
    case_ "a quoted word is not a command"        0 scripts/a.sh 'echo "run sbatch yourself"'
    case_ "sbatch as a command fails"             1 scripts/a.sh 'sbatch job.sh'
    case_ "sbatch after && fails"                 1 scripts/a.sh 'cd x && sbatch job.sh'
    case_ "nextflow run fails"                    1 scripts/a.sh 'nextflow run nf-core/rnaseq'
    case_ "tw launch fails"                       1 scripts/a.sh 'tw launch nf-core/rnaseq'
    case_ "\"\$TW\" launch fails"                 1 scripts/a.sh '"$TW" launch x'
    case_ "a python sbatch call fails"            1 scripts/a.py 'subprocess.run(["sbatch", "job.sh"])'
    case_ "nohup fails outside the allow-list"    1 scripts/a.sh 'nohup ./watch.sh &'
    case_ "a polling loop fails"                  1 scripts/a.sh 'while true; do tw runs list; sleep 5; done'
    case_ "a run_state file fails"                1 scripts/a.sh 'echo "$st" > "$D/run_state.json"'
    case_ "a sqlite store fails"                  1 scripts/a.sh 'sqlite3 runs.db "create table r(id)"'
    case_ "sbatch inside single quotes (ssh) fails"   1 scripts/a.sh 'ssh "$HOST" '"'"'sbatch job.sh'"'"
    case_ "sbatch in a python string fails"       1 scripts/a.py 'subprocess.run("sbatch job.sh", shell=True)'
    case_ "nextflow run in a quoted string fails"  1 scripts/a.sh 'ssh "$HOST" "nextflow run nf-core/rnaseq"'
    case_ "an until/sleep polling loop fails"      1 scripts/a.sh 'until tw runs view x | grep -q OK; do sleep 30; done'
    case_ "a while/sleep polling loop fails"       1 scripts/a.sh 'while ! check_it; do sleep 5; done'
    case_ "tw runs list cached to a file fails"    1 scripts/a.sh 'tw runs list > runs_snapshot.txt'
    case_ "tw runs list piped to tee fails"        1 scripts/a.sh '"$TW" -o json runs list | tee "$D/r.json"'
    case_ "a runs snapshot file name fails"        1 scripts/a.sh 'echo "$out" > "$D/runs_snapshot.json"'
    case_ "tw runs list to /dev/null passes"       0 scripts/a.sh 'tw runs list >/dev/null 2>&1'
    case_ "tw runs list read into a variable passes" 0 scripts/a.sh 'out=$(tw runs list)'
    case_ "an invented tw noun fails"             1 commands/a.md 'Run `tw frobnicate -i 1` first.'
    case_ "a Seqera noun passes"                  0 commands/a.md 'Run `tw runs list` first.'
    [ "$selffails" -gt 0 ] && { echo "FAIL: $selffails self-test(s) failed"; exit 1; }
fi

echo "OK: no submission script, no daemon beyond the allow-listed channels, no run-state store, only Seqera's nouns"
