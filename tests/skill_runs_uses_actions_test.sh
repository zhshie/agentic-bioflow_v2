#!/bin/bash
# #93 item 6, skill-runs-actions: skills/runs/SKILL.md reads run state and asks
# for actions through the platform's MCP tools, not through Seqera's CLI.
# TC numbers refer to specs/skill-runs-actions/test-case.md.
#
# SKILL_FILE points the checks at another copy of the skill; the last section
# runs them against the tw-era copy in tests/fixtures/runs_skill/ and requires
# that they FAIL there (TC-014: a test that cannot go red proves nothing).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SK="${SKILL_FILE:-$ROOT/skills/runs/SKILL.md}"
SERVER="$ROOT/platform/abf_platform/mcp_server.py"
LEDGER="$ROOT/specs/skill-runs-actions/ledger.md"
fails=0
ok()   { printf 'ok    %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fails=$((fails+1)); }
chk()  { if [ "$2" = 0 ]; then ok "$1"; else bad "$1"; fi; }
section() { awk -v want="## $1" '$0==want{g=1;next} g&&/^## /{exit} g{print}' "$SK"; }
# one paragraph per line (blank-line separated), newlines inside folded to spaces
paras() { awk 'BEGIN{RS=""}{gsub(/\n/," "); print}' "$SK"; }
UNAVAIL='not available on v3 yet'

[ -r "$SK" ] || { echo "FAIL: cannot read $SK"; exit 1; }

# TC-001: no tw command anywhere (a sentence saying a step is not available on v3 yet may name it)
bad_tw=$(grep -nE '(^|[^A-Za-z0-9_./-])tw([^A-Za-z0-9_-]|$)' "$SK" | grep -vF "$UNAVAIL")
[ -z "$bad_tw" ]; chk "TC-001 no tw command in the skill" $?

# TC-002 to TC-007: each read of state names a platform tool
board=$(section 'The work board (`/runs` with nothing named)')
grep -qF '`list_runs`' <<<"$board"; chk "TC-002 the work board reads list_runs" $?
! grep -qE -- '--workspace|runs_board' <<<"$board"; chk "TC-002 the work board has no tw flags or board script" $?
grep -qF '`get_run`' "$SK"; chk "TC-003 get_run is named" $?
sub=$(section SUBMITTED)
grep -qE '`(list_runs|get_run)`' <<<"$sub"; chk "TC-004 SUBMITTED reads state through a platform tool" $?
grep -qF 'scripts/on_site.sh --script scripts/why_pending.sh' <<<"$sub"; chk "TC-004/043 SUBMITTED keeps why_pending.sh" $?
run=$(section RUNNING)
grep -qF '`get_run`' <<<"$run"; chk "TC-005 RUNNING reads per-task progress with get_run" $?
grep -qF 'scripts/on_site.sh --script scripts/why_pending.sh' <<<"$run"; chk "TC-043 RUNNING keeps why_pending.sh" $?
failed=$(section FAILED)
grep -q 'get_run' <<<"$failed" && grep -q 'failure_reason' <<<"$failed"; chk "TC-006 FAILED uses get_run and failure_reason" $?
grep -qF 'scripts/on_site.sh --script scripts/egress_ctl.sh denied' <<<"$failed"; chk "TC-043 FAILED keeps the egress question" $?
unk=$(section UNKNOWN)
grep -qE '`(list_runs|get_run)`' <<<"$unk"; chk "TC-007 UNKNOWN is about what the platform tools report" $?
grep -qiE 'verbatim|exactly what' <<<"$unk"; chk "TC-007 UNKNOWN still says the status word as reported" $?

# TC-008/009: params and measurements either use an existing tool or say plainly it is not there
params=$(awk '/^#### `params`/{p=1;next} /^#### |^### |^## /{p=0} p' "$SK")
grep -qF "$UNAVAIL" <<<"$params"; chk "TC-008 params lookup says it is not available on v3 yet" $?
meas=$(section "Reading a measurement")
grep -qF "$UNAVAIL" <<<"$meas"; chk "TC-009 measurements say it is not available on v3 yet" $?
grep -q 'execution_trace_' <<<"$meas" && grep -q '85%' <<<"$meas" && grep -q '30%' <<<"$meas"; chk "TC-009 trace path and the reading table stay" $?

# TC-010 / TC-011 / TC-042
before=$(section "Before anything else")
! grep -qE 'workspace|TOWER' <<<"$before"; chk "TC-010 the tw-only preamble (workspace, token) is gone" $?
grep -qF 'scripts/intro.sh runs' "$SK" && grep -qF 'scripts/intro.sh --end runs' "$SK"; chk "TC-010/042 intro and end calls stay" $?
! grep -qiE 'only source of truth' "$SK"; chk "TC-011 no Seqera-is-the-only-truth sentence" $?
grep -qiE 'scheduler is doing' "$SK" && grep -qiE 'refused to send' "$SK"; chk "TC-011 the two site-side questions stay" $?

# TC-012/013: tool names are real; arguments are the real ones
tools=$(grep -oE 'name="[a-z_]+"' "$SERVER" | sed 's/name="//;s/"//' | sort -u)
args="run_id run_name compute_env"
badnames=""
for t in $(grep -oE '`[a-z]+_[a-z_]+`' "$SK" | tr -d '`' | sort -u); do
    case "$t" in tool_bug|failure_reason|peak_rss|peak_vmem|ssh_max_parallel|cancel_requested_at) continue;; esac
    grep -qxF "$t" <<<"$tools" && continue
    grep -qwF "$t" <<<"$args" && continue
    badnames="$badnames $t"
done
[ -z "$badnames" ]; chk "TC-012/013 every snake_case name in backticks is a v3 tool or argument:$badnames" $?
for n in list_runs get_run cancel resume relaunch; do grep -qxF "$n" <<<"$tools" || bad "setup: $n missing from mcp_server.py"; done
! grep -qE '`(list_pipelines|get_task|get_logs|download_log|runs_board)`' "$SK"; chk "TC-012 no invented tool names" $?

# TC-020/021/023: actions only ask; a person confirms
badp=$(paras | grep -E '`(cancel|resume|relaunch)`' | grep -vE '(person|user)[^.]{0,100}(yes|confirm|press|send)|(yes|confirm)[^.]{0,100}(person|user)' | cut -c1-60)
[ -z "$badp" ]; chk "TC-020 every paragraph naming cancel/resume/relaunch says the person confirms ($badp)" $?
grep -qF '`cancel`' "$SK"; chk "TC-020 cancel is named" $?
! grep -qiE "\b(I|AI|assistant) (will )?(confirm|say yes|answer the form|press)|confirm(ed|s)? (it )?myself" "$SK"; chk "TC-021 the AI is never the one who confirms" $?
bad23=$(grep -nE '`(resume|relaunch)`' "$SK" | grep -iE 'larger|bigger|smaller|more time|raise|memory|box size' | grep -viE 'cannot|not |never|same')
[ -z "$bad23" ]; chk "TC-023 resume/relaunch are not said to change resources" $?
# TC-023 (fix round): the same, but for the word "relaunch" with or without backticks (tables, bullets, "relaunching")
bad23b=$(grep -niE 'relaunch(ing|es|ed)?\b' "$SK" | grep -iE 'tier|larger|bigger|smaller|above|more time|raise|floor|box size|memory' | grep -viE 'cannot|not available|never|same|no smaller' | cut -c1-80)
[ -z "$bad23b" ]; chk "TC-023 no line (backticked or not) says a relaunch can change the box ($bad23b)" $?
# TC-023 (fix round 2): no line says relaunch/resume can correct, remove or change parameters/options
bad23c=$(grep -niE 'relaunch|resume' "$SK" | grep -iE 'param|option' | grep -iE 'correct|remov|chang|edit|fix|adjust' | grep -viE 'cannot|can.t|never|new `launch`' | cut -c1-80)
[ -z "$bad23c" ]; chk "TC-023 no line says relaunch/resume can change parameters ($bad23c)" $?
cancelled=$(section CANCELLED)
grep -qF '`resume`' <<<"$cancelled" && grep -qF '`relaunch`' <<<"$cancelled" && grep -qF 'new `launch`' <<<"$cancelled" && grep -qiE 'same folder' <<<"$cancelled"; chk "TC-022 CANCELLED keeps resume vs relaunch and the new launch" $?

# TC-030/031/032: steps that still need tw say so, and the ledger owes them
holes=$(paras | awk 'NR>1' | grep -E '(task_health|tune_resources|relaunch_with_override|runs_board|agent_ctl|ce_apply).sh' | grep -vF "$UNAVAIL" | grep -v 'line their output up' | cut -c1-60)
[ -z "$holes" ]; chk "TC-030 no script that calls tw is sent to the AI unmarked ($holes)" $?
# TC-030 (fix round): the paragraph check above is too coarse (a whole bullet list is one paragraph), so check bullet by bullet
holes_b=$(awk '/^[[:space:]]*- / || /^[[:space:]]*$/ { if (rec != "") print rec; rec = ""; if ($0 ~ /^[[:space:]]*$/) next } { rec = rec " " $0 } END { if (rec != "") print rec }' "$SK" \
    | grep -E '(task_health|tune_resources|relaunch_with_override|runs_board|agent_ctl|ce_apply)\.sh' | grep -vF "$UNAVAIL" | grep -v 'line their output up' | cut -c1-60)
[ -z "$holes_b" ]; chk "TC-030 no bullet sends the AI to a tw script without saying it is unavailable ($holes_b)" $?
ids=$(grep -oE "$UNAVAIL \(owed: [a-z0-9-]+\)" "$SK" | sed 's/.*owed: //;s/)//' | sort -u)
[ -n "$ids" ]; chk "TC-031 at least one step is marked not available on v3 yet, with an owed id" $?
all_n=$(grep -o "$UNAVAIL" "$SK" | wc -l); tagged_n=$(grep -oE "$UNAVAIL \(owed: [a-z0-9-]+\)" "$SK" | wc -l)
[ "$all_n" = "$tagged_n" ]; chk "TC-031 every 'not available on v3 yet' carries an owed id" $?
if [ -r "$LEDGER" ]; then
    lids=$(grep -oE '^- owed: [a-z0-9-]+' "$LEDGER" | sed 's/- owed: //' | sort -u)
    [ "$ids" = "$lids" ]; chk "TC-032 skill and ledger owe the same things" $?
    grep -qE '^Retired assertions:' "$LEDGER"; chk "TC-051 ledger says what was retired (or none)" $?
else
    bad "TC-032 no ledger"
fi

# TC-040
fm=$(sed -n 1,5p "$SK")
[ "$fm" = "$(printf -- '---\nname: runs\ndescription: Check on, debug, or deliver a pipeline run\nargument-hint: [run id or name]\n---')" ]; chk "TC-040 frontmatter unchanged" $?

# ---- rulings S1 to S6 (TC-080 to TC-097) ----
# one "Mapping:" line directly under each of the six branch headings
maps() { section "$1" | grep -E '^Mapping:'; }
for h in SUBMITTED RUNNING FAILED SUCCEEDED CANCELLED UNKNOWN; do
    n=$(maps "$h" | wc -l); [ "$n" = 1 ]; chk "TC-085 $h has exactly one Mapping line" $?
done
m=$(maps SUBMITTED)
grep -qF '`list_runs`' <<<"$m" && grep -qF '已送出、還沒開始' <<<"$m" && grep -qiE 'again later|check again' <<<"$m"; chk "TC-080 SUBMITTED maps to not-in-list_runs-yet, says 已送出、還沒開始, checks later" $?
grep -qE '3 (checks|times)|three (checks|times)' <<<"$m" && grep -qiE 'tell the person|never wait forever' <<<"$m"; chk "TC-081 SUBMITTED checks at most 3 times, then tells the person" $?
grep -qF '`running`' <<<"$(maps RUNNING)"; chk "TC-082 RUNNING = running" $?
grep -qF '`failed`' <<<"$(maps FAILED)"; chk "TC-082 FAILED = failed" $?
grep -qF '`succeeded`' <<<"$(maps SUCCEEDED)"; chk "TC-082 SUCCEEDED = succeeded" $?
m=$(maps CANCELLED)
grep -qF '`failed`' <<<"$m" && grep -qiE 'cancel' <<<"$m" && grep -qiE 'Nextflow reports a cancelled run as failed' <<<"$m"; chk "TC-083 CANCELLED = failed with a cancel request sent" $?
m=$(maps UNKNOWN)
grep -qF '`lost`' <<<"$m" && grep -qiE 'three heartbeats' <<<"$m" && grep -qiE 'any other' <<<"$m"; chk "TC-084 UNKNOWN = lost (three heartbeats) or any other value" $?
! paras | grep -vE '^Mapping:' | grep -E '(list_runs|get_run|[Pp]latform)[^.]*report[a-z]* [^.]*(SUBMITTED|CANCELLED)' | grep . >/dev/null; chk "TC-086 no sentence says the platform reports SUBMITTED or CANCELLED" $?

# S2: resume = same folder, cache; relaunch = new folder, from the start (checked sentence by sentence)
sent() { paras | sed 's/\([.!?]\) /\1\n/g'; }
b88=$(sent | grep -E 'relaunch' | grep -vE 'resume' | grep -iE 'cache|same folder|where Nextflow stopped|takes up|picks up' | cut -c1-70)
[ -z "$b88" ]; chk "TC-088 no sentence gives relaunch the cache or the same folder ($b88)" $?
b88=$(sent | grep -E '`resume`' | grep -vE 'relaunch' | grep -iE 'new folder|from the start' | cut -c1-70)
[ -z "$b88" ]; chk "TC-088 no sentence gives resume a new folder or a restart ($b88)" $?
b88=$(paras | grep -E "relaunch" | grep -iE "not the run over again|not the whole run|without starting over|rather than starting over" | cut -c1-70)
[ -z "$b88" ]; chk "TC-088 no paragraph says a relaunch spares the run from starting over ($b88)" $?
run1=$(tr -s "[:space:]" " " <<<"$run")
grep -qE "[Aa] .resume. counts as reversible" <<<"$run1" && ! grep -qE "relaunch counts as reversible" <<<"$run1"; chk "TC-087 RUNNING: the cache sentence is about resume" $?

# S3 (retired by S7/S8, see the ledger): the "v3 尚未提供 task 的資料夾路徑" assertions (old TC-089, TC-091) are
# replaced by TC-100 to TC-106 and TC-110 below. TC-090 stays, reworded: the folder comes from get_run's workdir only.
! grep -qE '`(work_dir|path)`|work/[0-9a-f]{2}/' "$SK"; chk "TC-090 no invented work-folder field or hashed path" $?
grep -qF '`workdir`' <<<"$failed" && grep -q 'workdir' "$SERVER"; chk "TC-090 the only folder field named is get_run's workdir" $?

# ---- rulings S7 to S11 (TC-100 to TC-112) ----
! grep -qE '尚未提供 task 的資料夾路徑|task-folder-path|gives no work folder' "$SK"; chk "TC-100 the task-folder-path wording is gone" $?
nr=$(grep -n 'No refusal lines up' -A8 "$SK")
grep -qF 'workdir' <<<"$nr" && grep -qF 'get_run' <<<"$nr"; chk "TC-101 the .command.err step takes the folder from get_run's workdir" $?
jev=$(grep -n 'Jev triage, only if' -A4 "$SK")
grep -qF 'workdir' <<<"$jev" && grep -qiE 'first failing task' <<<"$jev" && grep -qE 'once per run, never per task' <<<"$jev"; chk "TC-102 Jev triage runs for the first failing task with a workdir, once per run" $?
! grep -qE 'only when the person has given the task folder' "$SK"; chk "TC-102 Jev no longer waits for the person to give the folder" $?
grep -qiE 'has no .?workdir.? for (that|a|the) task' <<<"$failed"; chk "TC-103 one plain sentence: ask the person only when get_run has no workdir" $?
! grep -E 'no .?workdir' "$SK" | grep "$UNAVAIL" >/dev/null; chk "TC-103 the no-workdir sentence does not say 'not available on v3 yet'" $?
grep -qF '`read_task_log`' <<<"$nr" && grep -qF '`run_name`' <<<"$nr" && grep -qF '`task`' <<<"$nr" && grep -qF '`which`' <<<"$nr"; chk "TC-104 the log is read with read_task_log(run_name, task, which)" $?
grep -qiE '`which`[^.]*`err`|`err`[^.]*first' <<<"$nr" && grep -qiE '`out`' <<<"$nr" && grep -qiE 'empty' <<<"$nr"; chk "TC-104 which = err first, out or log if err is empty" $?
! grep -q 'fetch.sh' <<<"$failed"; chk "TC-105 the FAILED section no longer reads the log with fetch.sh" $?
! grep -qE 'owed: log-download|Downloading the log through the platform' "$SK"; chk "TC-105 no log-download owed marker" $?
grep -qF 'scripts/fetch.sh' "$SK"; chk "TC-105 fetch.sh stays where results are delivered" $?
rf=$(grep -n 'read_task_log' -A12 "$SK" | grep -iE 'refus|no .?workdir|not launched|offline')
grep -qiE 'no .?workdir|no recorded' <<<"$rf" && grep -qiE 'not launched (from|by|through) this platform' <<<"$rf" && grep -qiE 'offline' <<<"$rf"; chk "TC-106 the three refusals of read_task_log each have a fall-back line" $?
! grep -n 'read_task_log' -A12 "$SK" | grep -iE 'refus|offline' | grep -E 'fetch.sh' >/dev/null; chk "TC-106 no fall-back sends the AI to fetch.sh" $?
# S9
grep -qF '`cancel_requested_at`' <<<"$cancelled" && grep -qF 'Asia/Taipei' <<<"$cancelled" && grep -qiE 'already (asked|requested)' <<<"$cancelled"; chk "TC-107 CANCELLED: cancel_requested_at, already asked for, time in Asia/Taipei" $?
grep -qF '`cancel_requested_at`' <<<"$(section CANCELLED | grep -E '^Mapping:')"; chk "TC-083/107 the CANCELLED mapping rests on cancel_requested_at" $?
tail_c=$(section CANCELLED | grep -F 'To stop a run that is still going')
grep -qE 'cancel_requested_at' <<<"$tail_c" && grep -qiE 'not offer|do not offer|no second|another' <<<"$tail_c" && grep -qiE 'person|user' <<<"$tail_c"; chk "TC-108 CANCELLED: no second cancel offered when cancel_requested_at is there; the person still confirms" $?
grep -qF 'cancel_requested_at' <<<"$run" && grep -qiE 'not offer|do not offer|another `cancel`' <<<"$run"; chk "TC-108 RUNNING: no second cancel offered when cancel_requested_at is there" $?
# S10
inp=$(awk '/^#### `input`/{p=1;next} /^#### |^### |^## /{p=0} p' "$SK" | tr -s '[:space:]' ' ')
grep -qE 'new `?launch`?' <<<"$inp" && grep -qiE 'not `?relaunch`?|`relaunch` is only' <<<"$inp"; chk "TC-109 input: a corrected samplesheet is a new launch, not relaunch" $?
! grep -niE 'samplesheet|sample sheet|input file' "$SK" | grep -iE 'relaunch|resume' | grep -viE 'new `?launch|not `?relaunch|cannot|never' | grep . >/dev/null; chk "TC-109 no line says a changed samplesheet or input is re-run by relaunch/resume" $?
# S11
if [ -r "$LEDGER" ]; then
    [ "$(grep -cE '^- owed: ' "$LEDGER")" = 6 ]; chk "TC-110 the ledger owes exactly 6 things" $?
    ! grep -qE '^- owed: (task-folder-path|log-download)' "$LEDGER"; chk "TC-110 task-folder-path and log-download are no longer owed" $?
    for id in task-health resize-relaunch run-params measurements tune-resources ce-apply; do
        grep -qE "^- owed: $id" "$LEDGER" && grep -qF "(owed: $id)" "$SK" || bad "TC-112 $id is owed in both the ledger and the skill"
    done
    grep -q 'Retired assertions' "$LEDGER" && grep -q 'TC-089' "$LEDGER" && grep -q 'TC-091' "$LEDGER"; chk "TC-111 the ledger accounts for the retired TC-089 and TC-091 assertions" $?
fi

# S13/S14/S15 (2026-10-19): never tell the AI to read `.exitcode` as a file; the over-allocated row proposes, not shrinks
! grep -qF '.exitcode' "$SK"; chk "TC-120 SKILL.md has no instruction to read .exitcode as a file" $?
grep -F 'badly over-allocated' "$SK" | grep 'new `launch`' >/dev/null; chk "TC-121 the over-allocated row says a smaller box is a new launch the person confirms" $?
! grep -qF 'abf-platform launches' "$LEDGER"; chk "TC-122 the ledger no longer mentions abf-platform launches" $?

# S5: one manual step in docs/TESTING.md under the 009e section
step=$(awk '/^## Resume and relaunch \(009e\)/{g=1;next} g&&/^## /{exit} g' "$ROOT/docs/TESTING.md" | grep -E 'skills/runs/SKILL.md' | grep -E 'list_runs' | grep -E 'get_run' | grep -E '\btw\b' | grep -iE 'yes')
[ -n "$step" ]; chk "TC-093 TESTING.md 009e has the runs-skill walkthrough step" $?
# TC-094: the manual step follows S7/S8 (failed task's log via read_task_log; the task folder is no longer a "v3 lacks" example)
grep -q 'read_task_log' <<<"$step" && ! grep -qiE "task.s folder path" <<<"$step"; chk "TC-094 TESTING.md step names read_task_log and no longer lists the task folder as missing" $?
# TC-097 (TESTING.md numstat against origin/v3) removed 2026-10-23: a one-off contract check from #136 that fails on v3 itself once merged.

# TC-014: the same checks must fail on the tw-era skill
if [ -z "${ABF_RUNS_INNER:-}" ]; then
    out=$(ABF_RUNS_INNER=1 SKILL_FILE="$HERE/fixtures/runs_skill/SKILL.tw-era.md" bash "$0" 2>&1); rc=$?
    [ "$rc" != 0 ] && grep -q 'FAIL  TC-001' <<<"$out"; chk "TC-014 the checks fail on the tw-era skill" $?
fi
[ "$fails" = 0 ] && echo "OK" && exit 0
echo "$fails failed"; exit 1
