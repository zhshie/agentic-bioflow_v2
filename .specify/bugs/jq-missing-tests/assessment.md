# Assessment: jq-missing-tests (issue #70)

## Reported

Issue #70 (2026-10-07): on WSL Ubuntu without `jq`, `bash tests/run_all.sh` on 2.17.0 gave
71/93 (now 72/94 on main 7a64a31), 22 files red, with gate cases reading "expected ask/deny,
got pass/allow". The issue asked whether the hooks themselves fail open without jq.

## Diagnosis (developer-agent, 2026-10-10, WSL without jq, main 7a64a31)

The hooks do NOT fail open. Fed directly, each gate exits 2 (Claude Code blocks the call) with
"BLOCKED: jq is missing..." on stderr:

| Hook | Input | Result without jq |
|---|---|---|
| confirm_cleanup.sh | `rm -rf results` | exit 2, BLOCKED |
| confirm_cleanup.sh | `ssh u@host rm -rf /work/results` | exit 2, BLOCKED |
| confirm_cleanup.sh | `ls -la` | exit 0 (nothing to gate; by design, issue #15) |
| confirm_launch.sh | `tw launch nf-core/rnaseq` | exit 2 |
| confirm_launch.sh | `nextflow run nf-core/rnaseq -profile slurm` | exit 2 |
| confirm_launch.sh | `ssh u@host sbatch job.sh` | exit 2 |
| confirm_launch.sh | `ssh -o BatchMode=yes -F jump.cfg u@node01 squeue` | exit 2 |
| confirm_walkthrough.sh | Write of `tower_access_token: ...` to params.yaml | exit 2 |
| confirm_walkthrough.sh | `echo tower_access_token: ... >> params.yaml` | exit 2 |
| guard_plugin_files.sh | Edit / `sed -i` of a file under `$CLAUDE_PLUGIN_ROOT` | exit 2 |

The reds come from the tests, not the gates:

- The gate tests build their inputs and read the hook's JSON answer with jq. Without jq the hook
  takes its no-jq path (exit 2, no JSON), and the test records that as "pass", "allow" or
  "exit:2" against an expected "ask"/"deny". 192 + 132 + 28 launch cases, 152 + 88 + 4 cleanup
  cases, 54 + 2 walkthrough cases, and the guard cases are all this.
- Eight files already stop at the top with "jq is required for this test"; they are counted
  as failures with no explanation in the summary.
- The no-jq behaviour itself is already tested: confirm_cleanup, confirm_launch,
  confirm_walkthrough and guard_plugin_files hide jq with `tests/lib/nojq_path.sh` and expect
  exit 2. Those cases need the real jq to build their inputs, so they run in CI.

So the defect is in the test runner: a machine without jq gets 22 red files that read like a
broken Safety Net, when the suite simply cannot run there. That is the same shape as issue #1
(native Git Bash), which `run_all.sh` already answers with one message and exit 3.

## Severity

Low for users (the gates hold). Medium for the project: a false alarm about the Safety Net, and
a maintainer machine that cannot tell a real regression from a missing tool.

## The maintainer's example

None; he was not asked (A-tier). The issue text is the example: "a deployment whose shell lacks
jq has no Safety Net" must be shown false, and "a test that runs a gate with jq removed from
PATH" must exist.
