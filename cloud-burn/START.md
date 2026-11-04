# cloud-burn v2 — how to start a shard

Three shards run as three separate cloud sessions (each VM has 4 vCPU, so one session runs only
about 2 workflow agents at a time; parallel sessions are how we get throughput):

| shard | what | default models |
|---|---|---|
| A | code PRs (tests, C-tier cleanups) — needs full-suite runs | executor Sonnet, checker Opus |
| B | Opus adversarial module reviews + design/coverage reports | Opus |
| C | mutation testing, UI/a11y screenshots, QA walk, spec-vs-code reconciliation | Sonnet / Opus |

## Launch (pick one)

From a local checkout (the cloud clones the CURRENT branch from GitHub):

```bash
git fetch origin && git switch cloud/burn-v2
claude --cloud "$(sed -n '/^=== PROMPT ===/,$p' cloud-burn/START.md | tail -n +2 | sed 's/__SHARD__/A/g')"
# repeat with B and C
```

Into an already-open cloud session: `claude -p "<the prompt with __SHARD__ replaced>" --cloud <session-id>`.
From claude.ai/code: open the repo, paste the prompt (step 0 checks the branch out itself).

Stop everything: comment `STOP` on issue #317 (or `SHARD B STOP` for one shard), as the repo owner.

=== PROMPT ===
You are the cloud-burn v2 orchestrator for SHARD __SHARD__ of zhshie/agentic-bioflow_v2. Work until 2026-11-05 07:00 UTC (15:00 Taipei) or until a stop condition; the maintainer is not watching live.

0. Setup (once): `git fetch origin && git switch cloud/burn-v2 || git switch -c cloud/burn-v2 origin/cloud/burn-v2`; `HOME_DIR=$(pwd)`. Read `cloud-burn/RULES.md` completely and `cloud-burn/tasks.json`. Remember: `gh pr`/`gh issue` do not work here (GraphQL blocked) — use the REST forms in RULES §1. Never commit to cloud/burn-v2 itself.
1. Tool check: if you have the Workflow tool, you will run `.claude/workflows/cloud-burn.js` (use a workflow; start it from that script path) once per batch. If you do NOT have it, use the fallback in step 5. Post one comment on issue #317: `__SHARD__ start | utc=<date -u> | workflow=<yes/no> | model=<your model>`.
2. Loop:
   a. `date -u`. At or after 2026-11-05T07:00Z: go to step 4. `SHARD=__SHARD__ bash cloud-burn/signal.sh`: STOP → step 4; PAUSE → wait 30 min (a background `sleep 1800` then re-check), repeat.
   b. Repair first: list your open cloud-burn PRs (REST, head ref contains `/cb-` or `cb-reports-__SHARD__`). For each with a comment starting `VERIFIER: FAIL` that you have not answered, or with a failing check run: fix it on the same branch, same files (max two attempts per PR; RULES §5 flow, run_all green), push, comment what changed. Two consecutive PRs you cannot fix → step 4.
   c. Pick the next batch for shard __SHARD__ from tasks.json (`shard` == __SHARD__, ascending `order`), skipping ids already reported on #317 by any shard and ids whose branch exists on origin. Batch size: A = 4 code tasks; B = 3 tasks; C = 3 tasks. If shard A has ≥ 10 open cloud-burn code PRs without a `VERIFIER:` comment, do not take new code tasks: take report tasks (shard B/C or pool) instead. When the shard's list is empty, generate tasks from `pool` (ids continue the series, e.g. AR15, MU09, SR01) — the pool never runs dry; you may take another shard's pool.
   d. Run the workflow with args `{home: "<HOME_DIR>", shard: "__SHARD__", batchNo: <n starting at 1>, batch: [<the task objects verbatim>], issue: 317, reportDir: "docs/reports/cloud-burn-2026-11", utcStart: "<date -u>"}`. Wait for it to finish (it runs in the background; do not start a second batch in this session meanwhile).
   e. For every result with `prPayload`: open the PR yourself via `gh api -X POST repos/zhshie/agentic-bioflow_v2/pulls` (title/head/base/body from the payload). Then post one progress line per result on #317 in the RULES §4 format, plus `__SHARD__ batch <n> done | <counts> | utc=<date -u>`.
   f. If two results in a row are BLOCKED or CHECK-FAIL for environment reasons (missing tool, no network), post the reason and switch this shard to report tasks only.
   g. Back to a.
3. Never: merge, approve, enable auto-merge, close, force-push, delete branches, touch FORBIDDEN/HOT paths, weaken tests, reach any real site/HPC/cloud account, change CI/settings/permissions. If unsure whether something crosses a line, skip it and say why on #317.
4. Final: post on #317 `__SHARD__ FINAL` with one line per task (id, PR/branch, status, CI, verifier verdict if any), what was left undone and why. Then stop.
5. Fallback without the Workflow tool: do the same per batch with the Agent tool — read `.claude/workflows/cloud-burn.js` and use its prompts verbatim for each stage (gate → executor → checker → one fix round → lander for code; three lens reviewers → refuter for `review`; mutation agent for `mutation`; draft → critic for the rest; then one scribe per batch). Run at most two subagents at a time; give executors and mutation agents the model named in the task (default sonnet) and reviewers/checkers opus.
