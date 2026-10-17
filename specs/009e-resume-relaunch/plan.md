# Plan 009e: resume or relaunch a failed or cancelled run

- **Slug**: 009e-resume-relaunch. **Branch**: `feat/009e-resume-relaunch`, base **v3** (after 116b).
- **Tier**: B (user-visible: two new MCP tools, two terminal commands, a bundle with new keys). I checked whether it is C. It is not, because no deny is weakened: every attempt still needs a person's yes on TERMINAL, ELICITED or PAGE, there is still one submission file (`abf_station/launch.py`), and the gate code is untouched. One narrow relaxation is named in the Constitution Check. If the cold reviewer reads it as loosening Safety Net, escalate to C and let the maintainer merge.
- **Created**: by the Plan agent, read-only, on `origin/v3` (fetched). Line numbers below are from that fetch. Re-check them when the branch is cut.
- **Source note**: the 009 draft (`G:\我的雲端硬碟\謝馬爾\memory\handoff\2026-10-16-spec-009-draft.md`) gives 009e as "resume vs rerun from scratch, both go through the 009c confirmation, depends on 009c, B". This plan follows that. The draft's own line, "the CLI has no resume/retry/relaunch" (TC-061), is a pin this PR rewrites.

## 給維護者
1. 失敗或被取消的 run，本人可以選「續跑」（沿用同一個資料夾，Nextflow 接著上次做，算同一個分析的第 N+1 次）或「原樣重跑」（全新的資料夾，樣本與參數一模一樣）；要換樣本或參數，就是新的分析，不在這裡做。
2. 每一次續跑或重跑都跟第一次送出一樣，要本人在終端機、表單或確認頁按「是」；AI 不能代按，也沒有新的確認管道。
3. 只有那個 run 的主人能續跑或重跑，別人看到的是「找不到」；樣本裡的上傳路徑會重新檢查一次，捷徑被改指別處就不送出。

## Facts (verify on v3)
- **The yes is bound to a hash of the bundle.**
- `platform/abf_platform/confirm.py:38-49` `_confirm` writes the confirmation (hash = `common.bundle_sha256(bundle)`) and the job in one transaction.
- `confirm.py:67-93` `create_pending` and `confirm.py:105-155` `approve` do the same for a pending request.
- `jobs._check_confirmation` (`jobs.py:193-213`) refuses unless the bundle hash equals the confirmed hash.
- `confirm.py:26` `JOB_KIND = {"launch": "launch_nextflow", "cancel": "cancel_run"}`.
- The `confirmations.kind` column has `CHECK (kind IN ('launch','cancel'))` (`store.py:151` and `store.py:301`). A third kind would mean a table rebuild.
- **The action layer.**
- `platform/abf_platform/actions/__init__.py:143` `launch(state_path, ce_name, bundle, *, confirmed_by, ...)` is generic: it queues "exactly `bundle`".
- `_require_human` (`:138-140`) accepts only the three `_Channel` singletons (`:36-38`).
- `request_launch` (`:273-299`) and `request_cancel` (`:302-314`) both end in `_ask` (`:190-229`). `_ask` does the form (ELICITED), else the page (PAGE) and never answers for the person.
- `find_approved(..., include_spent=True)` (`confirm.py:158-176`) makes a repeated tool call return the existing job.
- `_no`/`_queued` (`:175-181`) are the answer shapes.
- **Ownership (116).**
- `jobs.owned_run_names` (`jobs.py:216-229`): a run is the caller's when the newest `launches` row of its name has that `user_id`.
- `jobs.enqueue_confirmed` (`jobs.py:309-339`) copies `caller_user_id` into `launches.user_id` and checks the environment and its agent against the caller.
- Its cancel branch drops a launch row owned by somebody else (`:333-337`).
- `jobs.name_problem` returns `NAME_TAKEN` to an HTTP caller whose name is held by another user (`:256-275`).
- `build.prepare_cancel` (`abf_launch/build.py:249-276`) filters by owner: another user's run is "not launched from this platform", the same as a missing one.
- `request_cancel` adds `confirm.launched_by` (`confirm.py:179-191`).
- **116b upload re-check.**
- `build._confine` (`build.py:214-246`) records `bundle["upload_paths"] = {"area", "paths":[{where, given, real}]}` for an HTTP caller. The approved hash covers it.
- `prepare_launch` sets it only when `area is not None` (`build.py:166-167`).
- The agent strips `upload_paths` before comparing the bundle (`abf_station/launch.py:617`), then runs `_check_upload_paths` (`:573-597`, `:620-621`). That check only ever refuses.
- **The agent's launch.**
- `run_launch` (`abf_station/launch.py:600-670`) verifies the confirmation (`:444-465`) and rebuilds the bundle from its own facts. It writes the five files with `mkdir folder && tar -x` and refuses an existing folder with "專屬資料夾已存在，不覆蓋" (`:648-652`). It then runs `sbatch folder/head.sh` once (`:659`).
- The head script is built in `_head_script` (`:333-368`). Its last line is `exec nextflow run <pipeline> -r <rev> -name <run> -params-file params.yaml -c nextflow.config -with-tower <endpoint>`; there is no `-resume` anywhere.
- `grep -i "resume\|relaunch" platform` outside `tests/` finds nothing. The only hit in the repo is `"resume": false` in the Tower payload fixtures.
- `render_bundle` (`:371-405`) derives `run_folder = <workDir>/runs/<run_name>`.
- **The hand-off record.**
- The `launches` columns (`store.py:205`) are `id, run_name, slurm_job_id, run_folder, ce, agent, confirmed_at, submitted_at, cancel_requested_at`, plus `user_id` from 116.
- It is documented as "a record of what was done, never a status" (`docs/PLATFORM.md`, `launches` paragraph).
- A cancel writes only `cancel_requested_at` (`jobs.py:477-480`): "the platform never writes cancelled as a state".
- A cancelled run reaches `get_run` as failed, with Nextflow's reason.
- **Retention.**
- `jobs.py:25` and `:100`: finished jobs are deleted 7 days after `finished_at`.
- `confirm.create_pending` clears the content of old requests after 7 days (`confirm.py:25,74-76`).
- So a launch job's `args_json` (the full bundle) lives about 7 days after it finishes.
- **Run identity.** The receiver keys a run by `common.run_id(session_id, run_name)` (`receiver.py:132-144`), and a run token is bound to one run name (`PLATFORM.md`, "Nextflow needs a token…"). Nextflow itself refuses to reuse a `-name`. So an attempt needs a new run name even though the session is the same.
- **Decisions already made.**
- ADR 0009 lines 44-46: a resume or relaunch with the same inputs is attempt 2, 3… of the same analysis; changing the samples or parameters starts a new analysis. Lines 53-56: the failure view shows the two buttons "resume" and "start over".
- ADR 0010 "Decided", line 101: every resume or relaunch needs a person's confirmation.
- ROADMAP line 128: "yes, every time".
- **Guards that exist.**
- `tests/no_second_run_state_test.sh:57-61` allows one submission file (`abf_station/launch.py`) with the test `test_unconfirmed_launch_is_refused`. Scan 3 (`:89-97`) greps `scripts/` for state files and databases.
- 009c pins: exactly the existing tool set (`test_mcp.py` tc024), the three channel singletons, and the CLI shape (TC-061 "no resume/retry/relaunch/yes/force" in `test_launch_platform.py`).

## Design decisions
1. **Two actions, not a `mode` on `request_launch`.** I chose `request_resume` and `request_relaunch`, with the signature of `request_cancel`:
 `request_resume(platform_path, *, run_name, caller=None, person=None, clock=time.time, remote=False)` and `request_relaunch(...)` the same.
 - **Why not a mode.** `request_launch` takes pipeline, revision, samplesheet, params. A `mode="resume"` would let someone pass new params together with a resume, which is the case the maintainer ruled out. With separate functions, the inputs cannot be expressed at all: the only argument is the run's name.
 - **Why not a third confirmation kind.** The two actions differ in preparation, screen and refusal words, so they stay apart. Both end in the existing `_ask` and the existing `confirm`/`jobs` path.
 - **No new write function and no new channel.** Both write `kind="launch"` and `job_kind="launch_nextflow"`, so the CHECK constraint, `JOB_KIND`, `CONFIRMED`, `_check_confirmation` and `verify_confirmation` are unchanged. The terminal calls the existing `actions.launch(..., confirmed_by=TERMINAL)` with the new bundle. What tells the three launches apart is the content of the bundle, which the hash covers (decision 3).
2. **Who may, and when.**
 - **Predecessor lookup.** `build.prepare_resume(state, run, owner)` and `build.prepare_relaunch(...)` look up the newest `launches` row of `run`. With a caller, a row owned by somebody else, by nobody, or missing gives one `build.Refusal`: `找不到這個 run (Run not found): <run>`. These are the words `get_run` uses (`actions:70-71`), so an outsider learns nothing, as 116 requires.
 - **Run state.** The run must have ended not-succeeded, read from the run index through `status.get_run` (Nextflow's own record). It is never stored.
   - Succeeded: "已成功，不需要續跑".
   - Still running or waiting: refused, "還在跑".
   - A cancelled run is a failed run to the index, so it passes.
   - Both actions are for the newest attempt of an analysis only. If a later attempt exists and is not refused, say which.
 - **Agent and environment.** The agent that submitted the predecessor and the environment must be the same. Changing the environment is changing the analysis.
 - **Owner for the chain.** All attempts of an analysis have the same owner. `enqueue_confirmed` refuses when `launches.user_id` of the parent differs from the confirmation's caller, with the same not-found words, so a confirmation made for one user's run cannot be turned onto another's.
 - **Terminal.** `abf-platform resume|relaunch RUN [--user NAME]` follows `launch` (`--user` required once any user exists, resolved by `_account`). It must be the owner of the predecessor, else the same refusal. With no users at all, owner NULL matches NULL.
3. **Bundle contents and hash (what binds a resume to its predecessor).**
 - **The source of a resume or relaunch** is the bundle of the launch job that created the folder, read from the `args_json` of the newest `launches` row of the same `run_folder` that is not a resume (a first launch or a relaunch). It is verbatim, so nothing is rebuilt from the person's words. If that job was pruned (decision 9) the answer is: 「太久了，這次送出的內容已經清掉，請當成新分析重新送出」.
 - **Relaunch bundle** = `build.prepare_launch`'s own output, rebuilt from the source's pipeline, revision, samplesheet, params and path_columns with a new auto run name. It carries a new `run_name`, `run_folder` and files, an area re-check (below), and one extra key: `"relaunch": {"of_run", "attempt", "of_sha256"}`.
   - `of_sha256` is the confirmation hash of the launch that created the predecessor's folder, kept in the audit columns.
   - The agent strips `relaunch` and `upload_paths` before comparing with its own rebuild, like `upload_paths` today (`launch.py:617`).
 - **Resume bundle**: `{"version", "agent", "ce", "run_name": <new name>, "run_folder": <the predecessor's folder, unchanged>, "files": {"head-N.sh": <text>}, "upload_paths"?, "resume": {"of_run", "of_slurm_job_id", "session_id", "attempt", "origin": <the source bundle verbatim>}}`.
   - It has no samplesheet or params of its own. They are `origin`'s, so they cannot change by construction.
   - `session_id` is the predecessor's Nextflow session id from the run index, which is Nextflow's own record.
   - `head-N.sh` is rendered by a new pure function in `abf_station/launch.py` (`render_resume`), sharing `_head_script`, which gains `resume_session=None`. The only difference from the first head script is `-resume <session id>` and the new `-name`, written as `head-N.sh` so the first `head.sh` is never overwritten.
 - **What the hash covers.** The whole bundle, so a resume of attempt 2 cannot be replayed as attempt 3 or as a relaunch, and the confirmation cannot be reused for a different predecessor (`of_slurm_job_id`, `session_id`, `attempt` are inside).
 - **Run names.** They are given by the platform, never typed: `<root>-a<N>` (a root name is cut to fit 64 characters). Both actions go through the existing `jobs.check_run_name` and `name_problem`.
 - **Screens** (`resume_screen` and `relaunch_screen` in `build.py`, same `as_text`):
   - The old run, the attempt number and the Slurm number.
   - "這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變" (a resume), or "這是原樣重跑：全新資料夾，樣本與參數不變" (a relaunch).
   - Pipeline, revision, sample count.
   - **The exact `nextflow run … -resume <id> -name … ` line** (constitution I.2: the full command is seen before the yes).
   - For a relaunch the same file blocks as a launch.
4. **116b `upload_paths` re-check.**
 - For an HTTP caller (area is not None) both actions re-run `_confine(state, bundle, caller_area(...), roots)` on the source's samplesheet and params.
 - For a resume the bundle is the origin plus `upload_paths` at top level, so the approved hash covers the real paths as of this request. If a link now leads outside the caller's folder the answer is the same refusal as a launch (`area_refusal`), before anything is asked.
 - The agent runs `_check_upload_paths(bundle["upload_paths"], ctx)` again at job time on both paths and refuses a swapped link, unchanged. The terminal and stdio (area=None) behave as today.
5. **MCP tools** (`mcp_server.py`, beside `cancel` at `:96`):
 - `resume(run_name)` and `relaunch(run_name)`. No other argument. Annotations: writing, not destructive.
 - Each calls `actions.request_resume` or `request_relaunch` with `caller=_caller(ctx)`, `person=actions.person_at(ctx)`.
 - The Claude Code kit's `extensions/claude-code-kit/settings.json` gains `ask` rules for `mcp__abf-platform__resume` and `mcp__abf-platform__relaunch`: a second layer, not the gate.
 - The tool descriptions and the `instructions` text say "does not start anything until the person says yes".
 - The routing table in `skills/operational/SKILL.md` and the `runs` skill get one line each. The generated text is not hand-edited.
6. **Terminal** (`abf_launch/cli.py`): `abf-platform resume RUN` and `abf-platform relaunch RUN`, beside `cancel`. Same shape as `cmd_launch`: `_account`, `build.prepare_*`, `terminal.terminal_problem()`, `terminal.ask(screen, question)`, then `actions.launch(state, ce, bundle, confirmed_by=actions.TERMINAL, caller=caller)`, then `_report_launch`. There is no `--yes` and no flag standing in for the keyboard. `abf-platform launches` prints `attempt N (resume|relaunch of <run>)`.
7. **Station-agent side** (`abf_station/launch.py`, the only file that submits):
 - `run_launch` branches on `"resume" in bundle` into `run_resume(job, ctx, preflight)`. The shared steps are factored out of `run_launch` and not copied: `verify_confirmation`, `own_facts`, the rebuild comparison (for a resume, of `origin` against the agent's own render), `_check_upload_paths`, the deadline guard, the `preflight` checks, the container-cache check and the forward channel.
 - **Then the folder rules**, in place of `mkdir` (so an existing folder is no longer a refusal, for a resume only):
   1. The folder is `bundle["run_folder"]`, must equal `origin["run_folder"]`, and must lie under `env["workDir"]/runs/` (`rules.path_problem` and `rules.inside`).
   2. One site call checks all of: the folder is a directory not reached through a link; the first line of `.nextflow/history` that has `session_id` agrees with `resume.session_id`; the sha256 of `samplesheet.csv`, `params.yaml`, `nextflow.config` and `head.sh` equal the hashes of `origin["files"]` (so the inputs are what was confirmed); `head-N.sh` does not exist; and `squeue -h -n nf-<of_run> -u <site_user>` is empty (the predecessor is not alive).
   3. Any mismatch is a `rules.Refusal` that names the folder and says nothing was changed.
 - It then writes `head-N.sh` and a new `tower.token` (mode 600; the token is for the new run name and the old run's token is already revoked) by `tar -x` into the existing folder, and calls `sbatch folder/head-N.sh` once. Results, `left_on_site` and the unknown-outcome words are the same as a launch.
 - A relaunch needs no new agent code except stripping `relaunch` from the compare; its folder is new and goes through the unchanged `mkdir` path.
 - **Which folder.** A resume runs in the predecessor's own `run_folder`, with its own `work/` and `.nextflow/` cache, so Nextflow's cache is found (`cd` into the folder; the head script does it at `:341`). A relaunch gets a new `<workDir>/runs/<new name>` and starts from nothing.
 - **Facts to confirm on a real run.** The assumption that `nextflow run … -resume <session id> -name <new name>` works with a fresh `-name` in the same cwd must be verified on the NCHC acceptance run, and it also decides whether `get_run` of the new run shows cached tasks (`PLATFORM.md` line 55). Until that is done the PR says "not yet accepted on NCHC".
8. **Attempt numbering: where it is stored, and why it is not a second run-state store.**
 - **Where.** Three nullable columns appended to `launches`, last: `parent_run TEXT`, `attempt INTEGER`, `attempt_kind TEXT CHECK (attempt_kind IN ('resume','relaunch'))`.
   - NULL means a first launch (attempt 1).
   - They are written in `enqueue_confirmed`, in the same transaction as the job, from the bundle's `resume` or `relaunch` block. It checks that the bundle's `attempt` equals 1 plus the highest attempt among the analysis's rows whose job was not refused, and that `parent_run` has a row owned by the caller. A race between two attempts makes the later one a `JobRefused` ("another attempt was started meanwhile").
   - The analysis's root is found by following `parent_run`. No `analysis` column.
   - `_LAUNCH_COLUMNS`, the in-place migration and the same-order pins (`test_launch_followup.py`, `test_launch_platform.py`) change together, as they did in 116.
 - **Why this is not a second run-state store.** These columns record a request and its lineage (what was asked, in what order), the same kind of fact as `cancel_requested_at`. Nothing says whether an attempt is running, succeeded or failed; that is always read from Nextflow's records through the index. The platform still never writes "resumed" or "failed" as a state.
 - **Checks.** `tests/no_second_run_state_test.sh` scans `scripts/` only for state files and databases, and its scan 1 reads `platform/` only for submission words. It needs no new entry. `LAUNCH_ALLOW` keeps its one file; `nextflow run`/`-resume` text lives only in `abf_station/launch.py`. The test named there, `test_unconfirmed_launch_is_refused`, gains a sibling, `test_unconfirmed_resume_is_refused`, in the same file; the allow-list line is unchanged and the script's self-test must stay green.
9. **Retention.** Resume and relaunch read the source bundle from the launch job's `args_json`, which is pruned 7 days after it finishes (`jobs.py:100`). Default in this PR: leave it at 7 days and, past that, answer "太久了…當成新分析". **Question for the maintainer, one question:** a failure noticed after a week is plausible on a shared cluster; should launch jobs be kept 30 days (a one-line exception in the prune; the paths stay in `platform.db` longer)? I recommend yes, but it changes how long sample paths are kept, so I will not do it without an answer.
10. **What the web will show later (not built here).** `launches` plus the index are enough for the stage board: attempt list per analysis (`parent_run`, `attempt`, `attempt_kind`, state read from the index), the failure sentence, and the two buttons that call `resume` and `relaunch`. A read action `list_attempts(run)` would return them. Adding it is 011's slice, so here the data and the terminal's `launches` line are all that exist. The confirmation page needs no change: it renders `describe()` and the stored summary text, and the PAGE channel's approve is generic.

## Tests (red first; the verifier writes the cases)
- **Gate (the same as a launch).**
- `actions.request_resume` and `request_relaunch` with no form and no caller answer "no one can say yes" and queue nothing.
- A decline voids the request. A pending request is not a confirmation: calling `jobs.enqueue_launch` with it is refused.
- With ELICITED a job exists and the answer is `_queued`. With no form (HTTP) the answer is `pending` plus `confirmation_url`, and PAGE approves it as the same user.
- A repeated call returns the job that exists and queues no second.
- Anything other than the three singletons as `confirmed_by` is refused before a database is opened.
- **Binding.**
- The hash covers `attempt`, `of_run`, `of_slurm_job_id`, `session_id` and `origin`. Changing any one after the yes makes `approve` or `enqueue` refuse ("內容與確認時不符").
- A yes for a resume is not usable as a relaunch (different content), and a yes for attempt 2 cannot make attempt 3.
- The agent refuses a resume bundle with a changed `origin`, a `resume` stripped, or a `run_folder` outside `workDir/runs/`.
- **Lineage.**
- Attempt numbers go 2, 3, 4 across a mix of resume and relaunch. A refused job does not use up a number.
- Two simultaneous attempts: the second is refused.
- `launches.parent_run`, `attempt` and `attempt_kind` are written in the same transaction as the job, and the old rows read back unchanged. A pre-009e `platform.db` upgrades in place and keeps the `launches` column order.
- **Ownership (116).**
- User A's failed run: A can resume and relaunch. B gets exactly the "Run not found" words of a missing run, for a run that is A's, nobody's or missing. List output never shows the existence of A's run to B.
- B's confirmation cannot be turned on A's run, at the queue (the parent's `user_id` check). A's yes is never reused for B.
- The terminal: `--user` is required once users exist, and a different user than the owner is refused with the same words.
- Stdio and the terminal with no users work on NULL-owner runs.
- **116b.** Over HTTP, a sample link swapped to point outside the caller's folder after the original launch is refused when asking (area refusal), before any question. A link swapped between the yes and the job is refused by the agent (`_check_upload_paths`). The re-recorded `upload_paths` is inside the approved hash.
- **State rules.** Succeeded, running and waiting runs are refused; a failed run and a cancelled-then-failed run pass. A run with no Slurm number is refused. A different agent or environment is refused. A pruned source job gives the "太久了" words.
- **Agent resume** (fake site).
- Right call order: the checks, then one tar with `head-N.sh` and `tower.token`, then one `sbatch`. There is no `mkdir`, no `rm`, no overwrite of `head.sh`.
- The head script contains `-resume <session id>` and the new `-name`. A first launch's head script is byte-identical to before (golden test).
- It refuses and changes nothing when: the history's session id differs, an input file's hash differs, `head-N.sh` exists, `squeue` shows the predecessor alive, or the folder is a link.
- The unknown-outcome words and `left_on_site` match a launch.
- `test_unconfirmed_resume_is_refused`: no valid confirmation gives no call on the site.
- **Relaunch.** The new folder, name and files differ from the predecessor's; the samplesheet and params are equal; `run_folder` exists nowhere; the first run's folder is untouched.
- **MCP and CLI.**
- The tool set is exactly the old one plus `resume` and `relaunch`, each with the single argument `run_name` (tc024 rewritten). No argument can say yes.
- `abf-platform resume|relaunch` need a real terminal (the existing pty-refusal test applies). There is no `--yes` or `--force`.
- `test_mcp.py` pins on `instructions`/prompts still pass and the generated text equals `skills/`.
- **Pins to rewrite, each with a ledger line (old expectation, new one, reason; nothing deleted or loosened):** `test_launch_platform.py` TC-061 (the CLI has no resume/relaunch → it has exactly these two, with no yes/force flags), `test_mcp.py` tc024 (tool count), `launches` column-order pins, `extensions/claude-code-kit` settings test (new ask rules).
- **Unchanged and green:** `tests/no_second_run_state_test.sh` (including its self-tests), the three-channel singleton tests, the receiver tests, the 116 and 116b suites.

## Not in this PR
- Any web page, the stage board, the buttons, `list_attempts` (011).
- Changing samples, parameters, revision, pipeline or environment on a resume or relaunch: that is a new analysis through `launch`.
- Automatic resume (the rule-based "exit 137 → larger box and resume" of ADR 0009) and the AI-assisted fix. A person still says yes to each.
- Resume for runs not launched by this platform, or without a Slurm number (use `launch`).
- Longer retention of launch jobs, unless the maintainer answers yes to decision 9.
- Any change to who may say yes, to the three channels, to `LAUNCH_ALLOW`'s single file, or to the cancel flow.
- Per-attempt tokens beyond the existing one-token-per-run-name rule.

## Constitution Check
- **I.2 (full command seen and confirmed before it runs):** the screen shows the exact `nextflow run … -resume … -name …` line and, for a relaunch, every file. The hash covers it. The agent re-renders and refuses any difference.
- **Invariant 2 (Nextflow's records are truth; no second run-state store; at most one submission path):** attempt numbers are lineage of requests, in the existing hand-off record. Session id comes from the index and `.nextflow/history`. Status is never stored. The single submission file is unchanged and its refusal test gains a resume sibling.
- **Safety Net / 009c gate:** no new channel, no weaker check. The `hooks/confirm_launch.sh` replacement (the action layer's human gate) is the same code path. The kit's `ask` rules are added for the two new tools as a second layer.
- **The one relaxation, named:** a resume writes into an existing run folder (a launch refuses an existing folder). It is narrow: only `head-N.sh` and `tower.token`; only after the session id, the input-file hashes and a dead predecessor are all checked on the site; never an overwrite of `head.sh` or the inputs; never deleting. If the reviewer calls it a Safety Net change, the tier becomes C.
- **116 / 116b:** owner-only, not-found words for everybody else, chain owner enforced at the queue, upload_paths re-recorded and re-checked.
- **Governance:** tier B. Update `docs/PLATFORM.md` (sections 9 and "Whose it is"), the `skills/` text, CHANGELOG, and the ledger for the rewritten pins. No amendment. A maintainer merge is not required unless the escalation above applies.

## Ruling (2026-10-18, developer-agent): the eight pins that resume and relaunch necessarily move
Approved. Edit each one separately with the Edit tool, not a bulk script. In the ledger's Rewritten pins table, record the old expectation, the new one and the reason. Each stays an exact set or exact value, with only the new names added.
1. `test_station_envs.py::test_tc071`: the tool list gains `resume` and `relaunch` (10 tools).
2. `test_station_envs.py::test_tc063`: the top-level subcommand set gains `resume` and `relaunch`.
3. `test_station_envs.py::test_tc084`: the `--help` subcommand string gains them, in registration order.
4. `test_pat.py::test_tcb10`: 8 tools becomes 10.
5. `test_pat.py::test_tcd10`: `cli.py` calls to `actions.launch`/`cancel` go from 2 to 3. All three still pass `confirmed_by=TERMINAL` and a non-None caller expression, as before.
6. `test_owner_binding.py::test_tc066`: revert the previous round's edit to the original `old_cols + ["user_id"]`. `old_cols` already contains the new columns, so the edit was wrong.
7. `test_confirm_page.py::test_tcg01`: allow exactly `resume`, `relaunch`, `request_resume` and `request_relaunch`. `retry` and anything else stay forbidden.
8. `test_station_platform.py::test_tc090`: the allow-list gains exactly `("launches","parent_run")`.

**Suite time.** If `platform_test.sh` still exceeds the 300 s per-test limit in `tests/run_all.sh`, rebalance its pytest shards so each shard stays under the limit. Do not raise the limit.
