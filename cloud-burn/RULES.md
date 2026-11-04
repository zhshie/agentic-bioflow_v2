# cloud-burn v2 rules (every cloud agent reads this first)

You run in an Anthropic cloud VM (Ubuntu, 4 vCPU, 16 GB). You cannot see the maintainer's
workspace. Everything you need is in this repository on branch `cloud/burn-v2`:
`cloud-burn/RULES.md` (this file), `cloud-burn/tasks.json`, `cloud-burn/*.sh`,
`.claude/workflows/cloud-burn.js`. The repo's own `CLAUDE.md` section "For the executor and
verifier" also applies; when it and this file disagree, the stricter one wins.

Base branch for every task branch: `origin/v3`. Never base work on `cloud/burn-v2`, and never
copy `cloud-burn/` or `.claude/workflows/` into a task branch.

## 1. GitHub from the VM

- The GitHub proxy rejects GraphQL. `gh pr ...` and `gh issue ...` FAIL (403). Use REST only:
  - list open PRs: `gh api 'repos/zhshie/agentic-bioflow_v2/pulls?state=open&per_page=100'`
  - PR files: `gh api 'repos/zhshie/agentic-bioflow_v2/pulls/<N>/files?per_page=100' --jq '.[].filename'`
  - create PR: `gh api -X POST repos/zhshie/agentic-bioflow_v2/pulls -f title=... -f head=<branch> -f base=v3 -F body=@body.md`
  - comment: `gh api -X POST repos/zhshie/agentic-bioflow_v2/issues/<N>/comments -F body=@c.md`
  - read comments: `gh api 'repos/zhshie/agentic-bioflow_v2/issues/<N>/comments?per_page=100'`
  - CI: `gh api repos/zhshie/agentic-bioflow_v2/commits/<sha>/check-runs --jq '.check_runs[]|[.name,.status,.conclusion]|@tsv'`
  The session's built-in GitHub tools may also work; REST is the fallback that always does.
- Push: `git push origin <branch>` (new branches only). The proxy refuses branch deletion and tags.

## 2. Never

- merge, enable auto-merge, approve, close PRs/issues, force-push, delete branches, push to
  `v3`/`main` or to any branch you did not create in this run;
- edit a FORBIDDEN or HOT path (§3), even "just one line";
- weaken a test, an assertion, a gate or a baseline (baselines may only shrink); add skip/xfail
  to hide a failure; delete an existing test;
- reach a real site, HPC, cloud account, `~/.config/agentic-bioflow` of a real deployment, or
  launch a pipeline; send anything outside GitHub;
- `git add -A` / `git add .` — always `git add <explicit paths>`, then `git status --porcelain`
  must show nothing unexpected (no egg-info, build/, venv, screenshots, `cloud-burn/`).
- A-tier work (direction change, release, spending money, HPC submission, constitution change,
  permissions/CI/settings change). If a task seems to need it: stop, report it as a FINDING.

## 3. FORBIDDEN and HOT paths (write = never; read = fine)

Run `bash cloud-burn/check_scope.sh <worktree> <allowed paths...>` before every commit; it
fails if the diff against `origin/v3` touches anything outside the allowed list or anything in
the lists below. The dynamic list comes from `bash cloud-burn/hot_scan.sh` (open PRs not made by
cloud-burn + branches pushed in the last 48 h) and from `HOT <path>` comments on the tracking
issue; refresh it at the start of every batch.

FORBIDDEN (always): `.specify/`, `.github/`, `hooks/`, `.claude-plugin/plugin.json`,
`extensions/claude-code-kit/settings.json`, `platform/abf_station/`, `docs/ROADMAP.md`,
any `spec.md` or `test-case*.md`, `tests/run_all.sh`, `pytest.ini`, `platform/pyproject.toml`,
`platform/setup.py`, `platform/tests/conftest.py`, `.claude/` (in task branches).

HOT (the maintainer's local lanes, 2026-11-04): `platform/abf_platform/web*.py`,
`jobs.py`, `store.py`, `mcp_server.py`, `cli.py`, `cliout.py`, `confirm.py`, `failures.py`,
`guidance.py`, `pipeline_lint.py`, `actions/` (all of it); `platform/abf_launch/`;
`platform/tests/*_harness.py`, `platform/tests/__golden__/`, `platform/tests/mcp/`,
`platform/tests/fake_slurm.py`, `tests/smoke/`; tests `test_web_*`, `test_results_*`,
`test_pipeline_lint.py`, `test_station_lint.py`, `test_launch_profiles.py`, `test_head_nodefail.py`,
`test_station_head_state.py`, `test_cli_*`, `test_fake_slurm_shim.py`, `test_su_job_states.py`,
`test_actions_layer.py`, `test_mcp*.py`; `tests/constitution_scope_test.sh`,
`tests/platform_direction_docs_test.sh`, `tests/pitfalls_format_test.sh`;
`docs/PLATFORM.md`, `docs/TESTING.md`, `docs/PITFALLS.md`, `PRODUCT.md`, `DESIGN.md`, `CONTEXT.md`.

Reports, reviews and mutation runs may READ HOT and FORBIDDEN files freely; they write only
their returned markdown.

## 4. Control protocol (tracking issue #317)

Read the newest comments by the repository owner (`zhshie`) before every task:
`STOP` = finish nothing new, post the final report, end. `PAUSE` = check every 30 min until
`RESUME`. `SKIP <id>` = drop that task. `HOT <path>` = add to HOT. `SHARD <X> STOP` = only
shard X stops. Verdicts on PRs come from the local verifier as a PR comment starting
`VERIFIER: PASS` or `VERIFIER: FAIL: <reason>`; on FAIL fix it on the same branch, same files,
max two attempts, before starting new work. `bash cloud-burn/signal.sh` prints the current signal.

Progress line on #317 after each task: `<shard> <id> | PR #N or branch | DONE/BLOCKED/SKIPPED-* | CI | one sentence`.

## 5. Code task flow (executor)

1. `git fetch origin`; `git worktree add /tmp/cb/<id> -b <branch> origin/v3`. If `<branch>` already
   exists on origin: SKIPPED-EXISTS.
2. Write `specs/cb-<id>/plan.md` (goal; source = "cloud-burn tasks.json <id>"; files; approach;
   RED tests; done criteria; environment facts; not doing).
3. RED first: write the test, run it, see it fail, save the output in `specs/cb-<id>/ledger.md`,
   commit "RED: ...". Pure test additions (code already right): mutation proof instead — break the
   function temporarily, show the new test fails, restore; both outputs in the ledger; never commit
   the mutant. If a new test fails on unchanged code and the task is not about that bug: do not fix,
   do not weaken; move that case out and record a FINDING.
4. Implement only inside the allowed files. 5. `bash cloud-burn/check_scope.sh /tmp/cb/<id> <files...> specs/cb-<id>/`.
6. Full suite: `cd /tmp/cb/<id> && bash tests/run_all.sh` — one run per checkout at a time; at most
   two full suites at once per VM. Paste the last 20 lines + HEAD sha into the ledger. If a tool is
   missing and the suite cannot be green, say so ("not green locally: missing X") — never claim green.
7. Commit with explicit paths. Hand back; the lander pushes and opens the PR.

PR title `[cloud-burn <id>] <summary>`; body: before/after one line each, files changed, RED
evidence, run_all result, risk, "Merged only by the local developer-agent after VERIFIER: PASS and
green CI", link to #317, last line `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## 6. Report kinds (review / mutation / reconcile / report / ui-report)

Output = one markdown document returned to the workflow; the batch scribe commits all of a
batch's reports to `docs/reports/cloud-burn-2026-11/<id>.md` on branch `docs/cb-reports-<shard>-<n>`
and opens one PR. Every claim cites `file:line` at `origin/v3` sha (write the sha at the top).
Every finding has: severity (P1 bug / P2 risk / P3 cleanup), evidence, a reproduction or the
reason none is possible, proposed fix, proposed RED test name, HOT? yes/no, suggested tier.
Findings that did not survive the refutation round are listed at the end under "Refuted"
with the reason — never silently dropped.
