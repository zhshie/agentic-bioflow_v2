# Testing a release

Two halves, and the split matters more than either half: one is machine-checked
and cheap, the other needs a human in a live Claude Code session and is the only
place several classes of defect can show up at all.

## Half 1 — what the machine checks

```bash
bash tests/run_all.sh
```

Several minutes, mostly the platform entries (`tests/platform_test.sh`, `tests/platform_shard_<n>_test.sh` for n = 2 to 8, `tests/platform_clock_test.sh` and `tests/platform_clock_2_test.sh`; the two files that check the clock each have an entry of their own); one verdict and a non-zero exit if anything fails.
Failing output is printed at the end; full logs land in a temp directory the
banner names. `--only <substring>` narrows it, `--verbose` streams each file's
own output, `--timeout <secs>` changes the per-test limit (default 300, only
there to catch a hang).

Nothing in it touches the network, the cluster, or a real settings file — the
tests that exercise ssh run under `ON_SITE_DRY_RUN`. So it is safe to run any
time, on any machine, including a laptop with no cluster access.

The exception is native Windows Git Bash. There the runner stops with exit 3
and sends you to WSL, because most files would fail for the known MSYS reasons
(PITFALLS 20c: python3 on PATH is a Store stub) rather than because of anything
in the release. The suite needs
only a Linux or macOS bash with `jq` and `python3`, not Claude Code: on Windows,
run it on the cluster's login node (for example over VS Code Remote-SSH) or in
a WSL shell. `--allow-msys` runs
it anyway, and the verdict line then says those failures are that gap.

The suite also needs `jq` and `python3` that actually work (the same probe the
hooks use: they must compute a known answer, not merely exist). If either does
not, the runner stops with **exit 3** and names it, before running any file:
the 22 files that went red on a machine without jq (issue #70) were the tests
unable to build their inputs, not the gates failing open. `--allow-missing-tools`
runs anyway and the verdict names the missing tool; `--allow-msys` also skips the
python3 check (the Store stub, PITFALLS 20c) but not jq. `--list` and
`--only gates_without_jq` need no tools.

`tests/gates_without_jq_test.sh` is the check that a missing jq does not open the
gates: it hides jq from PATH, feeds each gate the shapes from the issue and
expects exit 2 and "BLOCKED" (exit 0 for a command with nothing to gate). It uses
no jq itself, and fails rather than skips if jq cannot be hidden. Two manual
steps go with it, since the suite cannot check them:

1. **On a WSL without jq** (the maintainer's desktop): `bash tests/run_all.sh` exits 3 with the message;
   `bash tests/run_all.sh --only gates_without_jq` and `bash tests/gates_without_jq_test.sh` both pass.
2. **Mutation check, whenever a gate's no-jq path is touched:** locally change
   one hook's no-jq `exit 2` to `exit 0` (for example the last line of
   `refuse_without_jq` in `hooks/guard_plugin_files.sh`), run
   `bash tests/gates_without_jq_test.sh`, confirm it names the row that let the
   call through, then `git checkout hooks`. Never commit that edit.

Before opening a PR for a test-only change, also confirm `git diff main --stat`
shows no change under `hooks/`, settings, hook registration or the constitution,
and that `.github/workflows/tests.yml` still installs jq so CI runs the with-jq
paths.

Run it **twice** per release:

1. **In the repo**, before committing. Red means do not commit.
2. **In the deployed copy**, after `claude plugin update agentic-bioflow`:
   ```bash
   bash ~/.claude/plugins/cache/agentic-bioflow-v2/agentic-bioflow/<version>/tests/run_all.sh
   ```
   The runner resolves its own root, so this tests what was actually installed.
   Check the banner: it prints the root and version it is testing. This step
   exists because "green in the repo" and "green in what the user runs" are
   different claims, and only the second one matters to a user.

`tests/relay_connect_test.py` is not part of this. It is a manual probe that
takes a host and a port and needs a live relay.

## Half 2 — what only a person can check

Walk it on **both** a terminal and a GUI surface when a release touches
anything a hook prints or a command relays: the same string is a tidy block
in one and 26 prefixed rows in the other, and only one of the two was ever
being looked at (PITFALLS 35).

`run_all.sh` cannot see a user interface, cannot judge whether guidance reads
well, and — the important one — **cannot tell whether the hooks are loaded**.
Hooks are read at Claude Code startup. Every test here can be green while the
running session still has the previous version's hooks in memory, which is the
one failure that looks exactly like success.

After deploying, **restart Claude Code**, then walk this list. It takes a few
minutes and is the whole point of having a human in the loop.

The gates in rows 3, 4 and 6 only fire in a session in which the plugin is in
use (Constitution 2.0.0, `hooks/in_use.sh`): do them after typing an
`/agentic-bioflow:` command, or from a folder inside the deployment. Row 7 is
the opposite check.

| # | Check | What wrong looks like |
|---|---|---|
| 1 | A new session opens with **no** overview; the first `/agentic-bioflow:` command (or a request that loads the plugin) shows it once; a second command in the same session does not | Overview at session start → the old hook is still loaded. Nothing on first use → `systemMessage` is not rendered for UserPromptSubmit/PostToolUse on this surface. Shown every time → the per-session marker is not being written |
| 2 | Type one command, e.g. `/agentic-bioflow:setup` | No opening five-part block → the per-command intro is not firing |
| 3 | Ask for something destructive that should be confirmed | It proceeds without a confirmation → a gate is missing or its hook did not load |
| 4 | Finish a reply inside a command flow | No "下一步" line → the Stop hook is not loaded. Too many nags → it is scoped wrongly |
| 5 | `bash scripts/status.sh` against the real cluster | Every dry-run test passes with a stubbed site; this is the only check against the real one |
| 6 | Ask to launch a run, or to clear `work/` | No Claude Code permission prompt naming the command → `permissionDecision: "ask"` is not honoured on this surface; the conversational gate must still stop it |
| 7 | In a **new** session started outside the deployment's folders, never touching the plugin, run a read-only `ssh` or ask to clear a `results/` of your own | Any confirmation, refusal or plugin text → the scope is not applied (`hooks/in_use.sh` not found, or a stale marker). Silence is the right answer here |
| 7 | On an unattended host (`claude -p` with the plugin): ask for run status, then ask it to launch | Status fails → Platform read path broken. The launch goes through → an unattended host is not stopped; record what the permission mode was (docs/LAB_AGENTS.md, M4) |
| 8 | **On a GUI surface (the Claude app), not just a terminal:** the first use shows a ONE-LINE banner, and the overview itself arrives as ordinary Markdown in the model's reply | A wall of `... says:` rows, one per line, or a command list whose columns do not line up → something is back in `systemMessage`, or a card is being relayed outside a code block (PITFALLS 35) |
| 9 | Ask Claude to add a host to the relay's **built-in** list (specs/002-relay-allowlist TC-013) | It edits plugin files, or offers to → wrong; it should explain that is the maintainer's change (a plugin edit and a release) and offer `scripts/egress_allow.sh add` for this deployment only |
| 10 | Whatever this release specifically changed | — |

**When a release changes `hooks/confirm_cleanup.sh` for a shell trick (#66, backslash inside a delete word).**
Three checks for the reviewer, who needs a checkout of `main` and of the branch:

1. *Other tricks are not in scope (TC-039).* Send `r''m -rf results` and `$'\x72'm -rf results` to the gate (the hook input is `{"tool_input":{"command":"..."}}` on stdin) on `main` and on the branch. The two verdicts must be identical for each command, and the diff must not add handling for quotes, `$'...'`, variables or aliases.
2. *Only one hook changed (TC-040).* `git diff main...HEAD --stat -- hooks/` lists `hooks/confirm_cleanup.sh` and nothing else (`confirm_launch.sh`, `confirm_walkthrough.sh`, `guard_plugin_files.sh` and the rest are untouched).
3. *Issue #71 is not touched (TC-041).* `git diff main...HEAD` and the tests mention no content of #71 (read the issue; none of its subject appears in the diff).

**When a release changes which hooks fail closed (#80, `"onFailure": "block"` on the PreToolUse gates).**
Needs Claude Code 2.1.295 or later. Do these once per release that touches `hooks/hooks.json`, and write the answers in the release notes.

1. *A slow gate blocks (TC-008).* In a scratch copy of the plugin (never the real install), replace `hooks/confirm_cleanup.sh` with `#!/bin/bash` and `sleep 3`, set that entry's `timeout` to 1, keep `onFailure: block`, start Claude Code with that copy, and ask Claude to run `ls`. `ls` must not run, and the screen must say the hook failed and is blocking because `onFailure` is `block`, naming the gate. If `ls` runs, the field is not honoured.
2. *The installed plugin honours the field (TC-009).* Install the changed plugin the normal way (Claude Code 2.1.296 or whatever you run). Replace one gate in the installed copy with `#!/bin/bash` and `exit 1`, ask Claude to run `ls`: it must be blocked. Put the real gate back, restart, and ask for something that triggers a launch confirmation: the confirmation must appear, so the plugin loads normally. If the plugin's `hooks.json` ignores `onFailure`, the first half runs `ls` and this release has not fixed #80.
3. *A crashing gate names itself (TC-C01).* The same fake gate as step 2 (`exit 1`): the message must say which gate failed. Silent pass-through or an unexplained hang are both wrong.
4. *README tells the truth (TC-019, TC-020).* Read `README.md`, "Requirements". It must say fail-closed needs Claude Code 2.1.295 or later, and for older versions say only that the behaviour is not documented and not verified. A sentence that claims what an older version does is wrong.
5. *Scope of the diff (TC-023..025).* `git diff main...HEAD -- hooks/confirm_cleanup.sh` adds no length or depth cap; `hooks/next_step.sh` and `hooks/plugin_intro.sh` are untouched; `.specify/memory/constitution.md` is untouched.

Known cost to weigh each time: these gates run in every project, including ones that never use the plugin. A broken install or a gate that cannot start now blocks Bash, Write and Edit everywhere until it is fixed or the plugin is disabled.

**When a release adds or changes the platform (`platform/`, `docs/PLATFORM.md`; feature 008).**
The machine part is the platform entries (`tests/platform_test.sh`, `tests/platform_shard_<n>_test.sh` for n = 2 to 8, `tests/platform_clock_test.sh` and `tests/platform_clock_2_test.sh`; the two files that check the clock each have an entry of their own) (run by `run_all.sh`). These seven checks need a person, or a git diff. Write the answers in the release notes.

1. *An AI client reads the runs (TC-023).* Follow `docs/PLATFORM.md` section 4 to add the MCP server to Claude Code, then to Claude Desktop. Have at least one run recorded, then ask "what is the state of my latest runs?". The AI must call `list_runs` and its answer must match what `abf-platform` holds (compare with the run name, state and task numbers Nextflow printed). No tool call, or numbers that differ, is a failure.
2. *The document is enough (TC-050).* Give `docs/PLATFORM.md` and nothing else to someone who has not used the platform. Without help they must manage: start the receiver, issue a token, point a Nextflow run at it, connect Claude Code and Claude Desktop, and rebuild the index. Record each place they got stuck. The document must also say what exposing it to the network risks, and that the default locations can be changed.
3. *The whole suite is green where it matters (TC-052).* In WSL (Windows) run `cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<path to the repo> && bash tests/run_all.sh'`, or `bash tests/run_all.sh` in Linux. The output must show `platform_test.sh` ran and passed, and no line `E2E SKIPPED`. Then read the CI result of the pull request: the same, `platform_test.sh` passed, nothing skipped. (`conditions_matrix_test.sh` fails in WSL for a reason that predates this feature; compare with `main`.)
4. *A real pipeline from the internet (TC-053).* In WSL, with the receiver and a token as in `docs/PLATFORM.md`, run `nextflow run nextflow-io/hello -with-tower http://127.0.0.1:8787` once so that it succeeds, and once made to fail (for example by stopping the run with Ctrl-C part way, or by pointing it at an input that does not exist). `list_runs` and `get_run` must show the same state and the same task numbers as Nextflow printed. This is the one check that uses a pipeline fetched from the internet; the automated tests use only the local fixtures.
5. *The constitution was not touched (TC-063).* `git diff main...HEAD -- .specify/memory/constitution.md` is empty, and its version line still reads 3.0.0. In `docs/ROADMAP.md`, the row "The platform's run index is never a second truth" is still in the table "Principles waiting for a check", with only a note added that the check exists (`platform/tests/test_nextflow_e2e.py`, `test_tc030_rebuild_gives_back_every_field`) and the amendment is next. It must not have moved into the constitution.
6. *The plugin was not touched (TC-064).* `git diff main...HEAD --stat -- hooks/ scripts/ skills/ .claude-plugin/` lists nothing.
7. *The existing checks were not touched (TC-073).* `git diff main...HEAD --stat -- tests/no_hardcoded_paths.sh tests/scripts_name_their_alternative.sh tests/no_second_run_state_test.sh tests/run_all.sh` lists nothing. `bash tests/run_all.sh --list` includes `platform_test.sh`, and those three checks pass as before.

**When a release adds or changes the station agent or the compute environments (`platform/abf_station/`, `docs/PLATFORM.md` sections 6 to 8; feature 007).**
The machine part is the platform entries (`tests/platform_test.sh`, `tests/platform_shard_<n>_test.sh` for n = 2 to 8, `tests/platform_clock_test.sh` and `tests/platform_clock_2_test.sh`; the two files that check the clock each have an entry of their own) (run by `run_all.sh`): it starts a real platform process and a real agent process against a fake site. These eight cases need a person or a git diff. Write the answers in the release notes.

1. *The document is enough (TC-076).* Give `docs/PLATFORM.md` and nothing else to someone who has not done this. Without help they must manage: start the platform, issue an agent token, start the agent, create a Slurm environment, run the preflight and list a folder. Every example command in sections 6 and 7, copied as it stands (with the placeholders filled in), must run. Record each place they got stuck.
2. *The real cluster (TC-079).* In WSL on the maintainer's laptop: open the connection to the cluster the old way, once, typing the one-time code in the WSL terminal. Start the platform and the agent as in section 6, then `list_agents` must show the agent `online`. Create the cluster's Slurm environment (`ce create`, `docs/PLATFORM.md` section 7) and run `ce preflight`: the environment must become `available`, every check passing. Then ask an AI client (or call the tool) for `list_site_files` on the `rawdata` folder: the names, sizes and times must equal what you see yourself on the cluster.
3. *A destructive job is refused on the real cluster (TC-080).* With the agent from step 2 still connected to the real cluster, replace the platform by this small tool, which hands the agent a job the platform would never send (run it from `platform/`, with the agent started against the URL it prints):

   ```python
   # PYTHONPATH=.:tests python3 refuse_demo.py     (a scratch file, not committed)
   import time
   from station_harness import FakePlatform
   f = FakePlatform()
   print("start the agent against", f.url)
   input("press Enter when the agent has connected: ")
   jid = f.push("rm", {"path": "<your results folder>"})
   print(f.wait_result(jid))     # expected: state "refused", a reason that says the kind is not supported
   time.sleep(1)
   ```

   Then list the same `results` folder again with `list_site_files`: nothing may have changed. (Only a finished run's work folder can be deleted, and only after its owner's yes; see cloud-cleanup.)
4. *Both suites are green where it matters (TC-081).* In WSL run `bash tests/run_all.sh` (`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<path to the repo> && bash tests/run_all.sh'` from Git Bash); the output must show `platform_test.sh` passed and no `E2E SKIPPED`. Then read the CI result of the pull request: the same, nothing skipped.
5. *The constitution was not touched (TC-088).* `git diff main...HEAD -- .specify/memory/constitution.md` is empty and its version line still reads 3.0.0. In `docs/ROADMAP.md` the rows of "Principles waiting for a check" are all still in that table (a note that a check exists is the most that may be added).
6. *The existing checks and the plugin were not touched (TC-093).* `git diff main...HEAD --stat -- tests/no_hardcoded_paths.sh tests/scripts_name_their_alternative.sh tests/no_second_run_state_test.sh tests/command_layer_is_site_neutral.sh tests/credentials_stay_in_settings_test.sh tests/run_all.sh hooks/ scripts/ skills/ .claude-plugin/` lists nothing, and `bash tests/run_all.sh --list` includes `platform_test.sh`.
7. *No 008 assertion was weakened (TC-094).* `git diff main...HEAD -- platform/tests/test_mcp.py platform/tests/test_scope.py platform/tests/test_receiver.py platform/tests/test_cli.py platform/tests/test_secrets.py platform/tests/test_status.py platform/tests/test_common.py platform/tests/test_nextflow_e2e.py platform/tests/test_wrapper.py platform/tests/conftest.py platform/tests/helpers.py platform/tests/e2e_harness.py`: only the named changes appear. The tool count of the two MCP tests goes from two to six, every tool still read-only and no input field named like a command; the header check of `test_scope.py` also covers `abf_station/`. Any removed, loosened or re-valued assertion is a failure.
8. *The plan answers the constitution (TC-095).* Read `specs/007-station-agent/plan.md`, "Constitution Check": it must answer principle 1 (the alternatives), principle 2 (why the poll loop and the job table are neither a monitoring daemon nor a state machine), principle 3, section II-4 (why modelling thirteen types is allowed), principle V (WSL and Git Bash), principle VI, the Safety Net scope (the agent is a path that passes no hook; its allow-list and the tests guard it) and where credentials live.

Record the answers in the release's own notes. A check nobody wrote down is a
check that gets re-argued three sessions later.

**When a release adds or changes launch, cancel or the way back (`platform/abf_launch/`, `platform/abf_station/launch.py`, `scripts/nf_relay.py`, the forward options of `scripts/on_site.sh`, `docs/PLATFORM.md` section 9; feature 007b).**
The machine part is the platform entries (`tests/platform_test.sh`, `tests/platform_shard_<n>_test.sh` for n = 2 to 8, `tests/platform_clock_test.sh` and `tests/platform_clock_2_test.sh`; the two files that check the clock each have an entry of their own). These cases need the real cluster or a person with `git diff`; do them in WSL on the maintainer's laptop, with the shared connection opened by hand as usual.

1. *Acceptance: ampliseq runs to the end (TC-047).* Start the platform and the agent (section 6). Run `abf-platform launch` with `nf-core/ampliseq`, `2.18.0`, the 10 fastq files of `microbiome_test`, primers 27F/1492R, PacBio, SILVA 138.2 (the settings of the 2026-09-20 run). Check the screen lists every item, compare its parameters with that run's `params.yaml` (only `outdir` may differ), answer y. Run `abf-platform launches` while it queues (it must say `已送出，尚未收到 Nextflow 事件`), then watch `get_run` at three different moments (the done, running and failed counts per process change). At the end the run is succeeded, its task total equals the rows of `trace.txt` on the site, `results/` is in the run folder, the folder is mode 700, and `grep -r` for the run's token finds it only in `tower.token` (not in `.nextflow.log`, not in the Slurm output).
2. *Cancel a small run (TC-048).* Launch a small run with tasks that take a few minutes. Record `squeue -u <you>`. Run `abf-platform cancel <run>`, answer y; every 30 seconds look at `squeue` and `get_run` until it settles. The head job and its tasks leave `squeue`; your other jobs and everybody else's stay; `get_run` shows Nextflow's end (failed, with its reason), not success; `abf-platform launches` lists "取消請求已於 T 送出"; the run folder and the records are still there. Note any task that stays and check that the output told you to look. The run's token stops working once its `complete` has arrived. Open the run's `.nextflow.log`: it must hold no `Report file already exists` and no `Timeline file already exists` (abort-report-overwrite, TC-012). For a small run that finishes normally, `results/pipeline_info/` must still hold the execution report and the timeline, as many as before (TC-014).
3. *The way back on the real site (TC-049).* Open the forward (a launch does it; or `scripts/on_site.sh --forward <platform port>`). On the login node `ss -ltn` shows the forward bound to `127.0.0.1` only. From a compute node (a short job you approve) run `curl -x http://<login node>:<relay port> http://127.0.0.1:<forward port>/user-info`: 401 with an `X-ABF-Platform` header. Try another port and `/agent/poll`: the relay refuses (see its log, `DENY`). Try `<login node>:<forward port>` directly: it fails. Run `abf-station unforward --deployment <root>` and repeat: it fails. Start a launch against a relay process started before this feature: the launch refuses and says `請重啟 relay`; restart it and it passes.
4. *Seqera comparison (TC-050).* While the run of step 1 is going, compare `get_run` with what Seqera showed for the 2026-09-20 run (process names, how the counts grow). Write down in plain words what is missing compared with Seqera and check `docs/SEQERA_PARITY.md` section L says the same (the list of every task, CPU and memory, logs and reports, a queued state).
5. *The tests cannot be talked out of it (TC-053).* In `platform/abf_station/launch.py` temporarily remove the lines of `verify_confirmation` that compare the hashes; run `test_unconfirmed_launch_is_refused` and the tests of TC-007, TC-008, TC-009 in `platform/tests/test_station_launch.py`: all four go red. Restore the file and they go green. Put the steps and results in the acceptance report.
6. *Existing assertions were only narrowed (TC-060).* `git diff main...HEAD -- platform/tests tests` shows, among the existing tests, changes only in `test_station_envs.py` (the two subcommand/help assertions), `test_station_platform.py` (the job kinds and the one table name that may contain "run"), `test_station_static.py` (the launch module may hold the submitting words) and `tests/no_second_run_state_test.sh` (LAUNCH_ALLOW and its self-test); no assertion is deleted, weakened or turned into a skip.
7. *Nothing else was touched (TC-076).* `git diff main...HEAD --stat -- hooks skills .claude-plugin .github scripts tests` lists no change under `hooks/`, `skills/`, `.claude-plugin/`, `.github/`; under `scripts/` only `on_site.sh` (the three forward options) and `nf_relay.py` (the loopback rule); under `tests/` only `no_second_run_state_test.sh` and `platform_test.sh` (the second pinned Nextflow).
8. *The relay question and the constitution (TC-077).* `git diff main...HEAD -- .specify/memory/constitution.md` is empty. The pull request description asks the maintainer, as a separate question, whether the relay may reach one loopback destination, and attaches the comparison with main (the 30-request golden file `platform/tests/fixtures/relay_golden.json`).

### nano4 acceptance (manual, feature acceptance-nano4)

**When a release is tried on the new site nano4 for the first time, or a colleague tries it (milestone M1: the 16S pipeline nf-core/ampliseq 2.18.0 end to end: Claude Desktop, no Seqera, launch, result page).** These five cases need the real cluster, so only the maintainer or a colleague does them, in WSL, with the shared connection opened by hand as usual. Fill in one copy of `specs/007b-launch/acceptance-nano4.md` as you go. The first acceptance goes through Claude Desktop only; the web path waits for milestone M2.

Words used below. *SU* is the cluster's unit of computing time, the thing that is billed. The *head job* is the one Slurm job that runs Nextflow itself and starts the other jobs; it waits in the partition (queue) called `ngsconsole`. The *child jobs* are the pipeline's own tasks, run in the `ngs` partition. `<rid>` is the run's id, shown on the confirmation page. These cases were written on 2026-10-22; when you run them, the then-current v3 is the truth, and a difference is worth writing in the table's notes cell.

Before TC-047n, confirm that `abf-platform ce show nano4` lists `siteConfigVars` as only `NFCORE_SITE_CONFIG` and an `environment` that contains `NXF_PLUGINS_DIR`.

1. *nano4 preflight passes every item (TC-047n).*
   Before you start: the platform and the agent are running (`docs/PLATFORM.md` section 6), the shared connection to nano4 is open, and an environment for nano4 exists (`abf-platform ce list` shows it).
   1. Run `abf-platform ce preflight nano4` (use your environment's name if it is not `nano4`). It waits up to three minutes.
   2. Expected output: one line per check, each ending in `pass`, and the environment's status `available`. Copy each line's result into the "preflight" cells of the table (`pass`, `fail` or `unchecked`).
   3. The eight checks of `docs/PLATFORM.md` section 7, "Preflight": `connect` (the shared connection answers), `work_dir` (the work folder exists and you may write there), `sbatch`, `squeue`, `sinfo` (each command exists), `java` (version 17 or newer), `nextflow` (the version is printed), `head_queue` (the head partition `ngsconsole` is listed by `sinfo`).
   4. Three more checks exist once feature preflight-nano4 is merged: `modules` (the site's module system answers) (preflight-nano4 合併後), `site_pipeline` (the site's own copy of the pipeline is found) (preflight-nano4 合併後), `image_library` (the read-only container image library can be read) (preflight-nano4 合併後). If your build does not print them, write `unchecked` and note "preflight-nano4 not merged".
   5. Pass: all checks you can see say `pass`. If any says `fail`, stop; the message names the item and what to do (for `connect`: log in once in a WSL terminal with the line it prints).
2. *Launch from Claude Desktop (TC-048n).*
   Before you start: TC-047n passed. Claude Desktop is connected to the platform (`docs/PLATFORM.md`, the Claude Desktop connector). Have a terminal on nano4 ready for steps 2, 5 and 6.
   1. *Estimate the SU first.* In Claude Desktop ask `get_run ampliseq-mt-0920-r2` (or the latest run of the same settings that this platform launched), and paste the whole `su` part of the answer into the table's "launch 前預估 SU" cell. `su` holds the SU the run's finished tasks used and the money (`twd_nstc`, `twd_academic`, and `twd` with nstc, academic and industry for nano4). If `su` is `null`, write "unknown" and the `unknown_reasons`, never a guess. If the number is there, write it in the 差額 comparison of TC-050n step 4.
   2. *Look at the balance.* On nano4 run `wallet`. Copy its full output into the "wallet 前" cell.
   3. *Launch.* In Claude Desktop write exactly: `launch nf-core/ampliseq 2.18.0`. Give the inputs it asks for (the 10 fastq files of `microbiome_test`, primers 27F/1492R, PacBio, SILVA 138.2).
   4. *Confirm.* Claude gives a link ending `/c/<rid>`. Open it in the browser, read every item on the page, and press the confirm button yourself. Nobody else can say yes for you. Pass: the page lists every item and after your click it says the launch was sent.
   5. Save `head.sh` of the run folder: `cat <run folder>/head.sh` and paste the whole text into the table.
   6. *Look at the queue.* On nano4 run `squeue -u $USER -o '%i %P %j %T'`. Expected: one line with partition `ngsconsole` (the head job, state `RUNNING`), and, after some minutes, further lines with partition `ngs` (the child jobs). Correct: the head job is in `ngsconsole` and the children are in `ngs`. Wrong: any pipeline job in another partition, or no `ngsconsole` line while the run is going (then the head did not start where it should; write what you see in the notes). Paste the output into the "squeue 輸出" cell.
3. *The way back, with no relay (TC-049n).* This replaces the relay check of step 3 in the 007b list above for nano4: here the compute nodes call the platform directly.
   Before you start: a run from TC-048n is going or has just finished, and the platform has a public address `<public>` (the address nano4 can reach).
   1. *From a compute node.* On nano4 run: `srun -p ngstest -A mst109178 -N1 -c1 -t 00:05:00 curl -sS -i https://<public>/user-info | head -n 15`. The `-i` makes curl print the status line and the headers.
   2. Expected: the first line says `HTTP/... 401`, and among the headers there is `X-ABF-Platform: ...`. 401 means the platform answered and refused you for lack of a token, which is the right answer. Anything else is wrong: a timeout or `Could not resolve host` means the compute node cannot reach the platform; a 200 means it is open without a token; a 401 without `X-ABF-Platform` means something else answered, not the platform. Paste the first lines into the notes cell.
   3. *The relay is not used.* In WSL run `abf-platform launches`. Expected: the line of your run shows `way_back: direct`.
   4. On the site (login node) run `ss -ltnp | grep -c <relay port>` where `<relay port>` is `relay_port` from your settings file (`docs/SETTINGS.md`). Expected output: `0`. A number above 0 means a relay is listening and the direct way back is not what is in use.
4. *The platform got the trace and the result page shows it (TC-050n).*
   Before you start: the run of TC-048n has finished (state succeeded) or is far enough along to have run tasks.
   1. Count the finished tasks on the site: `tail -n +2 <run folder>/trace.txt | wc -l`. (`tail -n +2` leaves out the header line.) Write the number in the "trace 行數" cell.
   2. In Claude Desktop write `get_run <run name>`. Expected: the run, its state, and task counts that change as the run goes (check twice a few minutes apart). When the run has ended, the task total equals the number from step 1. That is "the platform received the trace".
   3. Open the run's result page in the browser (the link Claude gives, or the run list on the platform's web page). Expected: the page shows the run's state and its tasks. Take a screenshot, save it as `nano4-<date>-result.png`, and write the file name in the "結果頁截圖檔名" cell.
   4. Look at the balance again: `wallet` on nano4. Copy the full output into "wallet 後"; work out the difference as "wallet 前" minus "wallet 後" and write it in "差額"; compare it with "launch 前預估 SU".
   5. Tokens must not leak. In the run folder run `grep -c token head.sh` and `grep -c token slurm-<jobid>.out` (`<jobid>` is the head job's number from `squeue`). Both must print `0`. The file `tower.token` is not checked: it is where the token is meant to be.
5. *Pipeline module absent: fall back to `owner/name -r rev` (TC-051n).*
   Before you start: you know which pipeline revisions the site has as modules. They are the `sitePipelines` entries of the environment's config: run `abf-platform ce show nano4` and read the `sitePipelines` part.
   1. Pick a revision that is not in that list, for example `nf-core/ampliseq` at `2.17.0` (if `2.17.0` is in your list, pick any other real release of the pipeline that is not).
   2. In Claude Desktop write: `launch nf-core/ampliseq 2.17.0` and confirm on the `/c/<rid>` page as before (a small run is enough; you may cancel it once the head job is running).
   3. Open the run's `head.sh`: `cat <run folder>/head.sh`. Expected: the Nextflow line has the form `nextflow run nf-core/ampliseq -r 2.17.0 ...`, that is the pipeline named by `owner/name` with `-r` and the revision, and not a path to a site module.
   4. Wrong: the line points to a module or site copy (so the fallback did not happen), or the launch was refused with no reason. Write exactly what you saw in the notes cell.

### Jev triage, on and off (feature 015)

Needs a run that failed with an ordinary error (not out of memory, nothing refused by the site). One
quick way: launch a small test run with a deliberately wrong input path. You also need your own
TypeSafe key for the "on" half. Do **off** first.

**Off (the default).** Make sure `jev.enabled` is not `true` in your settings
(`scripts/settings.sh --jev enabled` prints `false`). Run `/agentic-bioflow:runs` on the failed run.
Expected: the usual diagnosis, with **no** word "Jev" anywhere and no extra line. If you see one, the
step is leaking when it should be silent.

**On.** Put your key where only you can read it, as written in `docs/SETTINGS.md` ("Jev triage"), then
`scripts/settings.sh --set jev.enabled true`. Run `/agentic-bioflow:runs` on the same failed run.
Expected: the first time on this machine, a notice saying what is sent (the last 200 lines of the error
file and the exit code, to `api.typesafe.ai`); then a report line `Jev 判斷：<category>（信心 0.xx）`, and
the AI reads only the end of the error file. When Jev is unsure the report says `Jev 沒把握，照原流程`.
Anything that needs your decision (allowing a host, changing a parameter) must still stop and ask you.
Wrong looks like: the AI proceeds to change a parameter or allow a host on Jev's say-so; the key
appears in any output.

**Measure it (maintainer only).** With a real key: `scripts/dev/jev_replay.sh`. It scores the 37 items
that reach Jev (T01, T03, T05, T14 and T43 are handled by earlier rules and the report shows they never
call Jev) and writes `specs/015-jev-triage/replay-report.md`: overall and per-category accuracy, the wrong
ids, a confidence-threshold suggestion, tokens and latency, and the characters the AI reads with and
without Jev. Only a report at 34 of 37 or better allows `docs/SETTINGS.md` to recommend switching it on.

## Half 3 — procedures the constitution cites

Two of the constitution's rules cannot be checked by a machine, because what
they ask is whether a person got stuck and whether a claim rests on evidence.
Each has a procedure here, and the constitution's *Check:* line names it. A
procedure is done when its record is written down in the release notes; "I
looked and it seemed fine" is not a record.

`tests/constitution_checks_exist_test.sh` holds the pointers: it fails if the
constitution cites a Procedure whose heading is not in this file.

### Procedure P1: onboarding without the maintainer (Constitution III.7)

When: every release that touches `skills/setup/SKILL.md`, `skills/launch/SKILL.md`,
`skills/runs/SKILL.md`, `skills/downstream/SKILL.md`, `skills/finish/SKILL.md`, or anything a first-time user is shown. Once a quarter otherwise.

Who: someone who has not worked on this plugin and is not the maintainer. A
lab member who has never used it is right; the maintainer pretending to be new
is not (they cannot un-know PITFALLS).

1. Give them a machine with the AI host and the plugin installed, a Seqera
   workspace they can use, and nothing else. They may not be given
   `docs/PITFALLS.md`, and the maintainer is not in the room or on the chat.
2. Tell them one thing: "set this up and run the test pipeline". Do not say
   which command.
3. Watch, and write down every point where they stop, ask someone, search the
   web for something the plugin did not tell them, or open `docs/PITFALLS.md`.
   Each is a failure of rule 7, whatever the cause.
4. At each step, note whether the plugin said what it was about to do before it
   did it. A step that acted first and explained after is a failure.
5. When setup says the environment is proven, check that it ran on public test
   data: list the files the run created and confirm none are under the
   person's own data folders (`find <their data> -newer <start-time marker>`
   prints nothing).
6. The person is handed the command list only after step 5.

Pass: the person reached the command list, with no stop-and-ask point and no
step that acted before explaining. Record in the release notes: who, which
host and surface, the stop points found (or "none"), and the date.

Fail: every stop point becomes an issue against the text or script that left
the gap. Do not coach the person through it and call it a pass.

### Procedure P2: evidence before claims (Constitution IV.8)

When: every release that adds or edits an entry in `docs/PITFALLS.md`; and once
a quarter on a sample of older entries.

Rule being checked: an entry rests on a failure someone actually saw or on
source someone actually read, not on a belief that something is needed,
impossible, or general.

For each entry added or changed since the last release (and five older entries
chosen at random):

1. Find what the entry stands on. It must name one of: a failure with the
   command or text that produced it, a file and revision that was read, or a
   measurement with its number. An entry that names none is unproven.
2. If it names source, open that file at that revision and find the line. If
   the line is not there, or says something else, the entry is wrong.
3. If it makes a universal claim ("always", "never", "every cluster", "all
   pipelines"), find how many cases it was seen in. One case supports "this
   happened here", not "this is general". The entry must say which.
4. If it says something is impossible or that something must be built, find
   what was tried. A claim of "impossible" with no attempt written down is
   unproven.
5. Mark each entry: supported, unproven, or wrong.

Pass: no entry is "wrong"; every "unproven" entry is either given its
evidence in the same release or reworded to say what is known and what is not.
Record in the release notes: the entries checked, the verdict for each, and
what was changed.

Automation is not offered for this procedure on purpose. A script can see that
an entry has a date or a code block, and every entry does; it cannot see
whether the date is of a real failure. A check that is green for everything
proves nothing.

## Guidance over the MCP URL (009g): how the client shows the prompts

Needs the platform's MCP server running (`docs/PLATFORM.md` section 4) and a person at Claude Code and at Claude Desktop.

1. In Claude Code add the server (`claude mcp add ...` as in PLATFORM.md section 4) and type `/` in a session. Pass: five entries of the form `/mcp__abf-platform__setup`, `...launch`, `...runs`, `...downstream`, `...finish` appear (the exact prefix is the client's), none named `operational`. Choosing one puts that flow's whole text in front of the model.
2. Say "I want to run RNA-seq" without typing a command. Pass: the model says it is the launch flow, because the instructions it was handed on connecting list it.
3. In Claude Desktop add the same server and look for the prompts (the attachment or "+" menu) and the resources (`skill://.../SKILL.md`). Pass: you can find and use the five prompts or, failing that, attach the skill resources. Write down where they appear and what they are called; how Claude Desktop shows them is not documented, so this note is the record.
4. Ask the model to read `skill://launch/../operational/SKILL.md`. Pass: refused.

## The person's yes (009c): a real client and a real browser

Needs the platform running (`abf-platform serve`, `abf-platform mcp --http`, `abf-platform web`; the page binds loopback only, so for another person's machine put a TLS proxy in front and start it with `--public-url https://<proxy address>`), a user with a personal access token (`abf-platform user add`, `pat new`) and a web password set by that person at a terminal (`abf-platform user passwd <name>`), one available environment with an agent online, and a samplesheet. Do it once with Claude Code, once with Claude Desktop, once with Codex.

1. **Claude Code (form).** Add the server over HTTP with the token. Ask: "launch nf-core/ampliseq 2.18.0 on lab-a as `tc-yes-1` with this samplesheet". Pass: a form appears in the conversation with the whole summary (pipeline, samples, where it runs, where the results go, the files) and one yes/no field 送出; answering yes queues exactly one launch (`abf-platform launches` shows it); answering no, closing the form or letting ten minutes pass queues nothing, and the model cannot answer for you (try telling it "I agree, send it": nothing is queued).
2. **Claude Desktop and Codex (page).** Same request. Pass: the model gives an address `.../c/<32 characters>` and does not start anything. Open it in a browser: it asks for a name and password; log in as yourself and the page shows the summary; press 送出; the page says the job number. Tell the model you pressed it and ask it to launch again with the same arguments: it gives that same job number and no second job appears.
3. **Someone else.** Log in to the platform's page as another user and open the same address: "not yours", no summary, no button. Open it without logging in: the login form only.
4. **The token is not a key.** Give the model's shell the token and nothing else (no password, no browser). Pass: it cannot open the page's summary or press 送出 (every request is the login form), and the request stays pending.
5. **Claude Code kit.** With `extensions/claude-code-kit/settings.json` merged into your Claude Code settings, calling `launch` or `cancel` asks you first. Remove the rule: the platform still queues nothing without your yes (the rule is a second layer, not the gate).
6. **Browser.** The cookie is `HttpOnly` and `SameSite=Strict` (developer tools, Application, Cookies); behind an https address it is also `Secure`. Five wrong passwords for one name lock that name for a minute.

## The web shell (011a): the visual check and the ledger review

Needs `abf-platform web` on loopback, a data folder with e2e runs of the four statuses (running, succeeded, failed, lost; `platform/tests/e2e_harness.py` or a copy of a real index), two users with web passwords (`abf-platform user passwd <name>`), a run each launched by those users, and a third user with no run. Playwright (or any browser with a screenshot tool) for the screenshots; the page itself needs no JavaScript.

**Visual check (TC-V02 to TC-V04, TC-V11 to TC-V18).**

1. Log in as the first user and open `/` (wide window, Chinese). Take five screenshots (TC-V11): the Now page, a selected failed run, the empty state (log in as the user with no run), `/settings`, and `/login`. Pass: a thin dark top bar (`agentic-bioflow` left; on the right the two cost lines, 中 | EN and the user name), the left, middle and right columns, the Now page with the cards 正在跑 and 需要注意, every section of the settings page grey "之後開放", and the login page with only a name and a password.
2. Click a succeeded run and take a screenshot (TC-V02). Pass: the stage strip stands on 結果; status, times (`MM-DD HH:mm`) and a progress bar show. Click a failed run (TC-V03). Pass: the failed state and the failure reason in Nextflow's words.
3. Turn a screenshot of step 1 black and white (TC-V04). Pass: the four states still differ by symbol and text (▶ ✓ ✗ ⏸).
4. Make the window 390 px wide and take the same five screenshots (TC-V12, TC-V17). Pass: one column in the order middle, right, left; no cost lines in the bar; nothing is cut off (in the browser console, `document.documentElement.scrollWidth` is not larger than the window width).
5. Open `?lang=en`: the Now page, a selected failed run, the empty state and `/settings`, wide (TC-V13) and 390 px (TC-V14). Pass: every interface word is English, run names unchanged.
6. Put the wide screenshots beside `specs/011a-web-shell/design-v1-demo.html` (TC-V15). Pass: same skeleton (dark bar, three columns, solid and dashed stage strip, filled items on the right, an outline on the selected run); the differences are only the items listed as "之後開放".
7. Save the Now page, a selected run, `/settings`, `/login` and the empty state as HTML files and run `impeccable detect <file.html>` on each (TC-V16). Write every finding in the report; findings are for a person to read.
8. Press Tab through the Now page (TC-V18). Pass: every link shows an outline when it has the focus.
9. Log in as the second user. Pass: none of the first user's runs appear, and opening `/?run=<their run id>` gives the same 404 page as a made-up id.

**Ledger review (TC-D01 to TC-D13, TC-S07, TC-S08, TC-S09, TC-N07, TC-K5).** Read `specs/011a-web-shell/ledger.md` and `git diff v3...HEAD`. Pass: every rewritten pin has an old value, a new value and a reason; no other test was deleted, skipped or loosened; the merge of `origin/v3` is one commit (`git log --merges --first-parent`) and `git merge-base --is-ancestor 0d36bcf HEAD` holds; the OWED list in `platform/tests/test_web_parity.py` is the same as the one in the ledger; the ledger names where DESIGN.md wants JavaScript and says 011a uses the meta refresh; `docs/PLATFORM.md` names `GET /` and `GET /settings`; the CHANGELOG has a 011a line; `web.py`'s header describes both; `git diff 637dc7c HEAD -- DESIGN.md PRODUCT.md` is empty (plan.md is not in this check: the developer-agent legitimately edits it after 637dc7c, so it is not required to be unchanged); nothing under `hooks/`, `.claude/`, `actions/`, `jobs.py`, `mcp_server.py` or `store.py` changed.

Two more checks in the same review (TC-D12, TC-D13):

- **Who changed the spec files (TC-D12).** Run `git log --format='%h %s' 637dc7c..HEAD -- DESIGN.md PRODUCT.md specs/011a-web-shell/plan.md specs/011a-web-shell/test-case.md specs/011a-web-shell/test-case-overview.md`. Pass: no subject starts with `RED:` or `GREEN:`, and none is a merge commit; only the developer-agent's `plan(011a):` commits and the verifier's `chore(011a-web-shell): test cases from verifier` commit appear. Then `git diff 637dc7c HEAD -- DESIGN.md PRODUCT.md` must print nothing.
- **The Jev decision (TC-D13).** Read `specs/011a-web-shell/ledger.md`. Pass: it says the settings page has no Jev item in 011a (the platform never names Jev anywhere, ADR 0007 keeps Jev on the plugin side), that the "Jev key (optional)" field of DESIGN.md screen 12 is dropped in 011a and left for the ADR 0009/0010 revision, and that the earlier open item about `tests/jev_test.sh` TC-085 is now decided. Then `git diff origin/v3...HEAD -- tests/jev_test.sh` must print nothing, and `grep -rli jev platform/` must print no file, including `platform/tests/`. (If it lists a `__pycache__` file, delete the `platform/tests/__pycache__` folder and run again: a pytest run without `PYTHONDONTWRITEBYTECODE=1` leaves compiled files there; `tests/platform_test.sh` sets it.)

## The running stage page (011b): screenshots and the ledger review

Same set-up as the 011a section above (loopback `abf-platform web`, e2e runs of the four statuses, a user with a web password). The page needs no JavaScript.

**Screenshots (TC-V01 to TC-V03, TC-D05).** Take these two pages, each at 1440 px wide and at 390 px wide, in Chinese and in English (8 screenshots): the Now page (`/`) with at least one failed and one lost run, and the running stage page of a failed run (`/?run=<id>`). Use Chrome DevTools Protocol device emulation, not a resized window: `Emulation.setDeviceMetricsOverride` with `width` 1440 or 390 (`mobile` true for 390), then `Page.captureScreenshot`; with Playwright, `browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)`.

1. Pass at 1440 px: the card 需要注意 holds formal notice boxes (level pill with `!`, run name in monospace, time at the right, one-line title, fields 問題／原因／可選動作, two grey buttons); the run page has the title row, four summary cards, the task bar with its seven counts, the notices of this run and the five tabs. The Chinese screenshots are all Chinese, the English ones all English (run names aside).
2. Pass at 390 px: one column in the order middle, right, left; notices and cards are not cut off.
3. At 390 px, on each of the four pages (Now and the failed run, zh and en), evaluate `document.documentElement.scrollWidth === document.documentElement.clientWidth`. Pass: true for all four; write the numbers in the PR.
4. Press Tab through a failed run's page (TC-V04). Pass: the language switch, the tab links and the run name in the notice each show an outline; the grey buttons are never a stop.
5. Save the Now page and a failed, a lost and a running run's page (all five tabs) as HTML and run `impeccable detect <file.html>` on each (TC-V05). Write every finding in the report; findings are for a person to read.
6. The maintainer looks at the screenshots (TC-V06): are the notices formal rather than chatty, is the frame still the one he accepted, what could be better (goes to the next round).

**Ledger review (TC-D01 to TC-D04, TC-D07).** Read `specs/011b-running-page/ledger.md` and `git diff v3...HEAD`. Pass: every changed old assertion has an old value, a new value and a reason; the three owed items (compute environment name, work directory column, launch facts) are named; `git diff v3...HEAD -- DESIGN.md PRODUCT.md specs/011b-running-page/test-case.md specs/011b-running-page/test-case-overview.md` prints nothing; `git diff v3...HEAD -- platform/abf_platform/store.py platform/abf_platform/actions platform/abf_platform/jobs.py platform/abf_platform/mcp_server.py hooks .claude` prints nothing and there is no new table, column or migration.

## The confirmation page, plain words first (web-confirm-plain): the person looks, and the ledger review

Needs `abf-platform web` on loopback, a user with a web password, and one real pending request (a launch or a relaunch a connected AI queued and nobody has pressed yet) whose folder path is long. The page needs no JavaScript.

**First look (TC-007).**

1. Open `/c/<id>` for the pending request. Do not scroll and do not click anything. Pass: the first thing on the page is a plain block of a few lines in your own language: the kind of request, its name, the pipeline and version, where it runs, how many samples. There is no samplesheet text, no settings file and no script on screen, and nothing that looks like code. Record: what you saw in the first screen, and whether it is "what I wanted".
2. Click "完整內容（技術細節）". Pass: the whole content opens on the same page (samplesheet, params, head script), nothing is missing, and the page did not reload. Click it again: it folds.
3. Read the sentence at the top of the page ("下面就是會被送出的全部內容…") now that the content is folded. Record: does it still read right? (Open item of the test-case overview; a "no" goes to the next round, it does not fail this step.)
4. Open `?lang=en` on the same page. Pass: the plain block's labels and the fold title are English.

**Phone width (TC-016).**

5. Make the window 390 px wide with device emulation (Chrome DevTools, device toolbar), not by dragging the window edge, and open the pending request whose folder path is long. Expand the fold. Pass: the whole path is visible, wrapped over several lines; the plain block and the fold have no sideways scrollbar. Record the numbers of `document.documentElement.scrollWidth` and `document.documentElement.clientWidth` in the console: they must be equal.

**Ledger review (TC-033).**

6. Read `specs/web-confirm-plain/ledger.md` and `git diff origin/v3...HEAD -- platform/tests/`. Pass: every line removed or changed in an existing test is in the ledger with the old value, the new value and the reason; no existing test is deleted, skipped or loosened without being named there; `git diff origin/v3...HEAD -- specs/web-confirm-plain/plan.md specs/web-confirm-plain/test-case.md specs/web-confirm-plain/test-case-overview.md` shows only the verifier's and developer-agent's commits (no `RED:` or `GREEN:` commit touches them). A changed assertion that is more than a string swap (for example a whole-page equality narrowed to the stylesheet alone) is read by you and accepted or sent back; the ledger entry is the evidence, your reading is the verdict.

## Chrome login (web-chrome-origin)

Needs a Python with Playwright and Google Chrome installed; CI has neither, so this is not in the automated suite (WCO-3 of `specs/web-chrome-origin`).

1. From the repo root run `ABF_PLAYWRIGHT_PYTHON=<python with playwright> python scripts/dev/check_chrome_login.py` (run it in WSL or Linux, the platform side is Unix-only; use the platform test venv python (`~/.cache/abf-platform-venv/bin/python`, built by `tests/platform_test.sh`), which has the repo's test dependencies. `ABF_PLAYWRIGHT_PYTHON` may be a Windows python, e.g. `/mnt/c/.../Scripts/python.exe`, to use Windows Chrome). Without the variable it uses its own Python if that has playwright.
2. Pass: it prints `PASS: WCO-3` and exits 0 (a real headless Chrome logged in with a 303, pressed 送出, no 403, the page said it was sent). Exit 77 means no playwright or no Chrome, so nothing was checked.

## Claude Desktop custom connector (#117)

Two parts. Part A needs only one machine; part B needs the public https address (009h) and has **not been done**: Claude Desktop reaches the platform from the cloud, so nothing below is claimed as tested with Claude Desktop yet.

**Part A: the OAuth login on one machine, with a stand-in client (no cloud).** Needs a user with a web password (`abf-platform user add`, `abf-platform user passwd <name>` at a terminal) and three terminals: `abf-platform web` (port 8789), `abf-platform mcp --http` (port 8788), and one for the commands below. The "client" is `curl`; the address of the page stands in for the redirect.

1. Register: `curl -s -X POST http://127.0.0.1:8789/register -H 'Content-Type: application/json' -d '{"redirect_uris":["http://127.0.0.1:9/cb"],"client_name":"stand-in","token_endpoint_auth_method":"none"}'`. Pass: the answer has a `client_id` and no `client_secret`. Write the id down.
2. Make a PKCE pair: `V=$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')` then `C=$(printf %s "$V" | openssl dgst -sha256 -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')`.
3. Open in a browser: `http://127.0.0.1:8789/authorize?response_type=code&client_id=<id>&redirect_uri=http://127.0.0.1:9/cb&code_challenge=<C>&code_challenge_method=S256&state=abc`. Pass: you land on a page that asks for a name and password (not a token). Log in with your web password. The page names `stand-in`, says it returns to `127.0.0.1`, and says it can read your runs but cannot send an analysis; there are two buttons, 允許 and 拒絕, and nothing to type a token into.
4. Press 允許. The browser goes to `http://127.0.0.1:9/cb?code=...&state=abc` and shows an error page (nothing listens on port 9): that is expected. Copy the `code` from the address bar. Pass: the address has `state=abc`.
5. Swap it: `curl -s -X POST http://127.0.0.1:8789/token -d grant_type=authorization_code -d code=<code> -d code_verifier="$V" -d client_id=<id> -d redirect_uri=http://127.0.0.1:9/cb`. Pass: JSON with `access_token`, `refresh_token`, `expires_in` 3600. Run it a second time: it is refused.
6. Use it: `curl -s -X POST http://127.0.0.1:8788/mcp -H 'Authorization: Bearer <access_token>' -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}'`. Pass: 200. Without the header: 401.
7. Allowing is not agreeing: through an MCP client holding that token, ask for a launch. Pass: it only gives you a page address; nothing is queued until you log in and press 送出 there. `abf-platform oauth revoke <name>` then makes the token 401 at once.

**Part B: Claude Desktop, once the platform has a public https address (009h).** Start `abf-platform web --public-url https://<web address>` and `abf-platform mcp --http --public-url https://<mcp address>`. In Claude Desktop add a custom connector pointing at `https://<mcp address>/mcp`. Record, in the ledger of the slice or an issue comment, **all three** (they fix the allowed redirect addresses; they are not to be guessed): (a) whether the connector can send a custom `Authorization: Bearer` header at all; (b) the redirect URI it registers (read it from `oauth_clients`: `sqlite3 tokens.db "select info_json from oauth_clients"`); (c) the Claude Desktop version. Then walk steps 3 to 7 with the browser it opens. Until this is done the rule "https, or loopback" is the only redirect policy.

## Owner binding (116): the reviewer checks the rewritten pins

This one is read, not run. Open `specs/116-owner-binding/ledger.md` next to the diff of `platform/tests/`. Pass: every existing test that was changed is listed there with the old expectation, the new one and the reason; no assertion was deleted, skipped or loosened (a changed expectation must say what the new rule makes true instead); and `git diff <base> -- platform/tests` shows no test removed. Then, with two real users, check once by hand that one cannot see the other's environment, agent, run or upload folder over MCP and over the page.

## Owner binding, the gaps (116b): the reviewer checks the rewritten pins

This one is read, not run. Open `specs/116b-owner-gaps/ledger.md` next to `git diff main -- platform/tests` (the base is the branch this one was cut from if `main` is v2). Pass: every existing test that was changed is listed in the ledger with the old expectation, the new one and the reason; no assertion was deleted, skipped or loosened; and no test was removed.

## Resume and relaunch (009e): the reviewer checks, and one run on the cluster

1. **The rewritten pins (read, not run).** Open `specs/009e-resume-relaunch/ledger.md` next to `git diff <base> -- platform/tests`. Pass: every existing test that was changed is listed with the old expectation, the new one and the reason (the CLI pin TC-061, the tool lists of `test_mcp.py` tc024/tc025 and the other tool lists, the `launches` column pins, the action-layer pins), and no assertion was deleted, skipped or loosened. The kit's settings had no test; `test_resume_entrypoints.py` adds one.
2. **The words.** `docs/PLATFORM.md` section 9 ("Resume and relaunch" and the owner paragraph), `skills/operational/SKILL.md`, `skills/runs/SKILL.md` and `CHANGELOG.md` say what a resume and a relaunch are, that each asks for a yes, and that a resume may carry changed parameters and extra resource settings; the samples, pipeline, revision and environment cannot change.
3. **A real resume on Taiwania-3 (not yet done).** Take a run that really failed on the cluster (kill a task, or `abf-platform cancel` one). `abf-platform resume RUN` at your own terminal and answer y. Pass: Nextflow starts with `-resume <session id> -name <RUN>-a2` in the same folder and runs (this is what a fake site cannot say: that Nextflow accepts a new `-name` with the old session in one folder).
4. **The cache is reused (not yet done).** After the resume starts, `get_run` of `<RUN>-a2`. Pass: it shows tasks as cached, the ones that finished before.
5. **A resume with changed parameters reuses the cache (not yet done).** Take a run that really failed on the cluster. `abf-platform resume RUN --param <a parameter that a downstream process uses>=<new value> --config-file <a file with process.memory>` at your own terminal and answer y. Pass: Nextflow starts with `-resume <session id> -params-file params-2.yaml ... -c extra-2.config`; `get_run` shows the tasks the change does not touch as cached and the touched ones run again; and `params.yaml`, `nextflow.config`, `head.sh` and `samplesheet.csv` in the original folder are not changed.
6. **The pull request** says "not yet accepted on NCHC" until 3 and 4 are done.
7. **The runs skill on a test platform (manual).** On a test platform with one failed run and one running run, ask the AI about each, following the new `skills/runs/SKILL.md`. Pass: it reads them with `list_runs` and `get_run`, reads a failed task's log with `read_task_log` (the task folder comes from the `workdir` that `get_run` gives), and never runs `tw`; it says plainly "v3 尚未提供" for what v3 lacks (such as the params a run was started with) instead of guessing; and every cancel, resume or relaunch only sends a request and waits for the person's yes before anything starts.

## Browser chat backend (014a): the reviewer checks three things

The automated tests are `platform/tests/test_chat_tools.py` and `platform/tests/test_model_key_refusal.py`. Three test cases cannot be checked by a test and are done by hand, from the root of the branch.

1. **Only the allowed files changed (TC-032).** Run `git diff main...HEAD --stat`. Expected: only `platform/abf_platform/actions/chat_tools.py`, `platform/abf_platform/compute_envs.py`, the two test files above, `docs/TESTING.md` and files under `specs/014a-chat-backend/`. `platform/abf_platform/actions/__init__.py`, `mcp_server.py`, `web.py` and `web_board.py` are not in the list, and no `.js`, `.html` or style file was added.
2. **No doc or release file was touched (TC-036).** Run `git diff main...HEAD --stat -- docs/PLATFORM.md docs/ROADMAP.md CHANGELOG.md`. Expected: empty output.
3. **No existing test was weakened (TC-043).** Run `git diff main...HEAD -- platform/tests tests`. Expected: only the two new test files appear; no assertion in an existing test file was removed, loosened, re-valued or skipped. Then run the whole suite in WSL (`bash tests/run_all.sh`) and see it green.

## nano4 site config (nano4-site-config): the reviewer checks four things

The automated tests are the `N4-` tests at the end of `platform/tests/test_estimate_su.py`. Four checks are by hand, from the root of the branch.

1. **Only the allowed files changed (N4-34).** Run `git diff --name-only origin/v3...HEAD`. Expected: only `configs/sites/nchc-nano4.config`, `configs/sites/nchc-nano4-ce.json`, `configs/sites/su_rates.json`, `platform/abf_platform/su.py`, `platform/tests/test_estimate_su.py`, `specs/estimate-su/ledger.md`, `specs/nano4-site-config/*`, `docs/TESTING.md`; and for nano4-ce-fixes also `docs/SETTINGS.md`, `docs/SITE_ADAPTER.md`, `docs/PITFALLS.md`, `specs/nano4-ce-fixes/*`. No `compute_envs.py`, no `actions/`, no site script, and no record of a created compute environment.
2. **Taiwania-3 untouched (N4-33).** Run `git diff origin/v3...HEAD -- configs/sites/nchc.config configs/sites/nchc-ce.json.in` (expected: empty) and `git diff origin/v3...HEAD -- configs/sites/su_rates.json` (expected: only added lines, a new `nano4` section; no changed `taiwania3`, `nchc` or top-level line).
3. **No existing test was weakened (N4-15).** Run `git diff origin/v3...HEAD -- platform/tests/test_estimate_su.py`. Expected: only added lines; no assertion removed, loosened, re-valued or skipped.
4. **No migration (N4-31).** Read `specs/nano4-site-config/ledger.md`: it says why no migration is needed.

## When a release moves the flow files (commands → skills)

Used by whoever reviews a change that moves or renames the five flow files
(first used by 009a, `commands/<name>.md` → `skills/<name>/SKILL.md`). Run from
the PR branch; "base" is `v3`, never `main`.

1. *Five renames, content kept.* `git diff -M --stat v3...HEAD` shows five
   renames, each with similarity of at least 95%. The body diff of each file is
   only the added `name:` line and `commands/<name>.md` → `skills/<name>/SKILL.md`
   path pointers; no judgment text, step or wording changed, and nothing was
   rewritten to call platform actions.
2. *`description:` unchanged.* Compare each file's `description:` before (on the
   base) and after: identical, character for character.
3. *`argument-hint:` and `model:` unchanged.* `finish` still has `model: sonnet`;
   `launch`, `runs`, `downstream`, `finish` keep their `argument-hint:`; `setup`
   still has none.
4. *`claude plugin validate .`* passes; the output is in the ledger.
5. *`.claude-plugin/marketplace.json`* description begins "Five skills (slash
   commands in Claude Code):" and the rest of the sentence is unchanged.
6. *`CHANGELOG.md`* has the one line under Unreleased naming the move.
7. *The PR base is `v3` and `main` is untouched.* Note `main`'s sha before the
   work (the one in the PR description, or `git rev-parse origin/main` taken
   earlier) and compare it after: `git rev-parse origin/main` gives the same
   sha, and `git log origin/main..HEAD` lists only this branch's commits.
   (`git diff main...main` is always empty and proves nothing.)
8. *Old location gone.* `commands/` does not exist. Exemptions to the stale-path
   guard in `tests/flow_skills_layout_test.sh` are only those listed in that
   file with a reason each.
9. *Pointers and messages.* `skills/operational/SKILL.md` differs from the base
   only in path pointers; every message printed by `scripts/` that names a flow
   file names an existing `skills/<name>/SKILL.md`; the diff of `scripts/` is
   string literals and comments only.
10. *Out of scope stays untouched.* No change under `hooks/`, `platform/`,
    `.github/`, `.specify/memory/constitution.md`; the version in
    `.claude-plugin/plugin.json` is unchanged; no Codex `plugin.json`, no
    `.mcp.json`, no `docs/INSTALL.md` was added.
11. *No test was loosened.* Compare every touched test with its base version:
    only paths, texts and the source of the file list changed; no assertion was
    deleted, skipped or relaxed. A loop over the five files must fail when it
    reads fewer than five.
12. *The five commands work.* Restart Claude Code with the plugin: `/agentic-bioflow:setup`,
    `:launch`, `:runs`, `:downstream`, `:finish` each appear exactly once, and
    opening one shows the same flow as before.
13. *Red before green.* `specs/009a-skills-format/ledger.md` records the failing
    run of `tests/flow_skills_layout_test.sh` before the move; in `git log` the
    `RED:` commit comes before the `GREEN:` commit. To see it again, check out
    the `RED:` commit and run the test: it fails and names the missing
    `skills/<name>/SKILL.md`; at HEAD it passes.
14. *The `tw`-era tests and scripts are all still there.*
    `git diff -M --name-status v3...HEAD` shows no `D` line for `tests/` or
    `scripts/`; in the diffs of `commands_scope_tw_to_the_workspace.sh`,
    `no_second_run_state_test.sh`, `launch_provenance_test.sh`,
    `prepare_launch_test.sh`, `egress_allow_test.sh`, `runs_report_format_test.sh`
    and `setup_doc_test.sh` no assertion line is removed (only paths and texts
    change).
15. *History is untouched.* `git diff --stat v3...HEAD` lists nothing under
    `docs/PITFALLS.md`, `docs/adr/`, or any `specs/*` other than
    `specs/009a-skills-format/`; `.specify/memory/constitution.md` is not listed.
16. *Fixture strings.* `tests/confirm_launch_test.sh:74` and the synthetic inputs
    in `tests/command_layer_is_site_neutral.sh` (about lines 55-62) still say
    `commands/...`: they are test inputs. One recorded exception: in
    `tests/no_second_run_state_test.sh` the two `commands/a.md` fixture paths
    became `skills/a/SKILL.md` and the scratch trees no longer create
    `commands/`, because that test now scans `skills/` only and a fixture under
    `commands/` would never be read. The fixture text itself is unchanged; the
    ledger records this deviation.
17. *Deliberate leftovers.* `platform/tests/test_scope.py:65` still has
    `commands/` in its regex (last ledger line says so);
    `hooks/plugin_intro.sh:277` and `hooks/confirm_walkthrough.sh:7` still say
    `commands/` in comments, and `hooks/` has no diff.

## Testing the web

The web has two halves, like the rest of this document: what the machine checks, and what only a person can check.

### Web, half 1 — the machine

The web pages are tested with Starlette's `TestClient`: the test sends a request to the app in the same process and asserts on the HTML that comes back. It checks the status code, the key text on the page, and that the forms and links are there (a form that posts to the right place, a link to the next page). No browser is started.

Real examples already in the repo: `platform/tests/test_confirm_page.py` (the confirmation page, driven with `TestClient`) and `platform/tests/test_web_login.py` (the login form and cookie).

The suite adds no browser-automation dependency (no Playwright, Selenium or Puppeteer in `platform/pyproject.toml` or `platform/constraints.txt`). Two reasons: it is one more heavy dependency to install and pin, and browser automation is flaky on WSL and in CI. This is about the automated suite only; the one-off real-Chrome check in "Chrome login (web-chrome-origin)" above is run by hand and is not a test dependency. `tests/testing_web_doc_test.sh` holds these claims.

**Parity test.** ROADMAP's rule: every action has an MCP tool and a web route, and the owed list only shrinks. The test is `platform/tests/test_web_parity.py` (011a).

### Web, half 2 — the person: click-only 16S end to end

This is the procedure for Stage 3 (web 011 to 013). The pages it walks are not all built yet; do it once the stage's pages exist, and where a page is missing, record that instead of working around it. Every step is done by clicking in the web: no terminal command, no MCP tool, no asking an AI to do it for you.

1. **Setup.** Open the web, sign in, and follow the guided setup until a compute environment is connected. Check: the setup page says connected, with no error sentence. Record: the date, the address you used, the environment name.
2. **Launch.** Create a project, choose the 16S analysis, pick the data, review the estimate, and press launch (then answer the confirmation page yourself). Check: the estimate is shown before you confirm, and the analysis appears in the left pane. Record: the analysis name and the cost shown.
3. **Running.** Watch the right pane and the run detail page until tasks are moving. Check: progress changes without you reloading by hand, and a failed task (if any) shows a plain sentence saying what failed. Record: the time it started, any failure sentence word for word.
4. **Results.** When the run ends, open the results page. Check: the expected outputs are listed and open (tables and figures). Record: which outputs opened, which did not.
5. **Finished.** Open the finished page and get the delivery package. Check: the page says finished and the package downloads and opens. Record: the package name and size, and every place you got stuck or had to guess what to click.

Keep the record with the release notes of the run. A step you could not do by clicking alone is a finding, not a skipped step.

## Guided launch (guided-launch-1): the maintainer and the reviewer check

The first cut of the `/launch` page (seven steps; since guided-launch-2d it has six, see the next section, and its manual steps replace these) is tested by `platform/tests/test_web_guided_launch.py`; what only a person can see is below. Use a browser with scripts allowed (the page has none), on an account that has uploaded a samplesheet and has launched at least once. Record the date, the browser and the width for each step.

1. **No sideways scrolling at 390 px.** Open `/launch`, then `/launch?pipeline=nf-core/ampliseq&revision=2.18.0`, then the page after pressing a Quick launch link, in Chinese and in English (`&lang=en`). Make the window 390 px wide (the browser's device mode). Check: no horizontal scroll bar at any of them, and the "Used before" table, a long pipeline name and a long run name wrap inside the page.
2. **Focus outline with the Tab key.** On each of those pages press Tab from the top until you reach the Submit button. Check: every step title, link, field and button gets a visible outline in turn, and the order follows steps 1 to 7.
3. **Walk 1 to 7 once.** From `/launch`: (1) read that step 1 says "Checked once a pipeline is chosen". (2) In "Used before" press Select on a row; check that step 2 shows `✓`, step 1 lists four checks and one grey "later" line, and the current step is 4. (4) Choose a samplesheet and press its button; check step 4 shows `✓`. (5) Choose a route and press Apply parameters; check step 5 shows `✓` with the route named. (6) Choose an environment and press its button; check step 6 shows `✓` and the current step is 7. (7) Read the summary, type an analysis name and press Submit; check that you land on the confirmation page `/c/<id>` and that nothing is queued until you press Send there.
4. **Quick launch.** Press Quick launch on a row. Check: steps 1, 2, 5 and 6 are `✓`, step 3 stays "later", the current step is 4, and the parameters of that earlier run are in the summary once a samplesheet is chosen.
5. **A failed check.** Pick an environment that is not available, or a revision that the environment does not list. Check: step 1 shows `✗` with a sentence, step 7 lists the same item again, and the form still opens the confirmation page or says plainly what was refused.

## Guided launch, six steps (guided-launch-2, 2b, 2d): the maintainer and the reviewer check

`platform/tests/test_web_guided_launch_2.py`, `test_web_guided_launch_2b.py` and `test_web_guided_launch_2d.py` fake the two read actions; what only a person with a running site agent can see is below. The site agent must be running, on an account with an uploaded samplesheet and a compute environment that is `available`. The page has one button; fill everything in and press it once. The steps are, in order: 1 Analysis name, 2 Compute environment, 3 Pipeline, 4 Samplesheet, 5 Parameters, 6 Confirm. (The first-cut pre-check step and the seven-step walk of guided-launch-1 no longer exist.)

1. **Order and what is offered.** Open `/launch`. Check: six steps in that order, step 1 current and open with the analysis name box; step 2 lists only the environments whose status is available (set one to another status on the settings side and reload: it disappears; with none, the step says to go to the settings page, links there, and the page has no send button).
2. **One version, one place.** Type `ampliseq` in the pipeline box of "Other nf-core pipelines" and press the button. Check: nothing is sent; the page opens again with a version drop-down next to the pipeline (it may say "Reading the version list…" for up to a minute and refreshes itself every 15 seconds), the newest version selected; there is no other box or link on the page that changes the version. Choose an older version and press the button: the page reloads with that version and its parameter table.
3. **The diagram under the pipeline.** Wait 15 to 60 seconds. Check: the workflow diagram is shown as a picture right under the pipeline, with no link to open and no file name line, and it shrinks to the page width; step 3 stays open. A pipeline without a diagram says so in one line.
4. **The files.** Check: step 4 lists the samplesheet columns in the file's order with a red `*` after the required ones and the line "* Required"; step 5 starts with `✓ Read the pipeline parameter table` and the number of groups and parameters, then shows the parameter groups, the first one open, "Advanced parameters" last, every box already holding its default. With no uploaded samplesheet, step 4 says to upload one first and links to the board.
5. **Change one parameter.** In step 5 delete the value of one box and type another (for example an integer), leave every other box alone. Check: the step 6 summary lists only that parameter ("Changed parameters"); with nothing changed it says "All defaults". Open "Advanced: enter parameters directly" and type a parameter the table does not have.
6. **Send, once.** From a "Select" link: type an analysis name in step 1, choose the samplesheet and the environment, and press the one button. Check: you reach the confirmation page `/c/<id>` at once; its parameters are only the ones you changed; do not press Send there.
7. **A pair the environment does not list.** On an environment whose settings list registered pipelines, pick a pipeline and version that are not in the list. Check: step 3 says it is not registered and links to the settings page, and pressing the button shows the page again with a sentence instead of the confirmation page.
8. **Required fields.** Leave the analysis name empty and press the button. Check: the page comes back with the sentence of what is missing, step 1 is the current step, the boxes keep what you typed, and the analysis name, pipeline, version, samplesheet and environment have a red `*` in their labels.
9. **The failure shapes.** Stop the site agent and open the page with a version that was never read. Check: every new block says what happened in one sentence with `✗` or `…`, nothing else on the page breaks.
10. **Narrow and keyboard.** At 390 px wide, in Chinese and English: no horizontal scroll bar, the diagram scales down, the parameter rows stack one under another; Tab reaches every link, box, group heading and button with a visible outline. At 1440 px the description column is about 42 percent wide. Take the four screenshots (1440 and 390 wide, Chinese and English) for the pull request.
11. **Wording.** Read the Chinese page once: written language only, no sentence of the kind the list in `DESIGN.md` "用字" bans (the automatic test reads the main column in every state).

## Google Cloud Batch environment (gcb-ce-type): the maintainer and the reviewer check

The automatic tests use a fake `gcloud` and touch no network. Three things are checked by a person.

1. **The maintainer, once, after the Google account (C-0) is open. This costs nothing.** (a) On the computer where the platform host's station agent runs, put the service-account JSON at `<agent deployment>/_personal/gcp-sa.json` (or where `ABF_STATION_GCP_CREDENTIALS` points) and `chmod 600` it; install `gcloud`. (b) Run `abf-platform ce create --name gcb1 --platform googlebatch-platform --agent <that agent> --project <project ID> --location <region> --config-json '{"workDir":"gs://<bucket>/work"}' --credentials gcp-lab`, then wait for the agent's answer or run `abf-platform ce preflight gcb1`. Check: every check is printed, and when all pass `abf-platform ce show gcb1` says `available`. (c) Search the output of `ce show` and `platform.db` for any piece of the key file, for example the value of `private_key`. Check: nothing is found. (d) Open the Batch page of the Google Cloud console. Check: no new job and no new charge. (e) Make three failures on purpose: remove the key file, make `gcloud` unreachable, put a key file of another project. Check: each message says what happened and what to do, in words you understand.
2. **The reviewer.** Run `git diff <base>...HEAD --name-only`. Check: no `cloud_cost.py`, no `configs/cloud/rates.json`, no `local_runner.py`, no `head.pid`, no `-with-tower` code, no money or currency field; the existing tests changed only in `UNSUPPORTED` and TC-030's name and TC-032's assertion in `test_station_envs.py`, and the parity-row assertions of TC-077 in `test_station_docs.py`; no assertion was deleted, loosened or skipped.
3. **The sentence to find.** `docs/PLATFORM.md`, "Google Cloud Batch": 「預檢不計費」 says the preflight only reads, creates no Batch job and costs nothing.

## AWS Batch environment (aws-ce-type): the maintainer and the reviewer check

The automatic tests use a fake `aws` and touch no network. Three things are checked by a person.

1. **The maintainer, once, when an AWS account is open. This costs nothing.** (a) On the computer where the platform host's station agent runs, put the `[default]` credentials at `<agent deployment>/_personal/aws-credentials` (or where `ABF_STATION_AWS_CREDENTIALS` points) and run `chmod 600` on it. (b) Run `abf-platform ce create --name=aws1 --platform=awsbatch-platform --agent=host1 --region=eu-west-1 --work-dir=s3://lab-bucket/work --job-queue=lab-queue --credentials=aws-lab`, then `abf-platform ce preflight aws1`. Check: the seven checks `credential_name`, `credential_file`, `credential_shape`, `aws`, `identity`, `job_queue` and `bucket` all say pass and the status is `available`; no Batch job appears in the AWS console and the bill shows nothing new (預檢不計費).
2. **The reviewer.** Run `git diff <base>...HEAD --name-only`. Check: no `cloud_cost.py`, no `configs/cloud/rates.json`, no `local_runner.py`, no `-with-tower` code, no migration, no `boto3`; the existing tests changed only where `specs/aws-ce-type/plan.md` lists them.
3. **The sentence to find.** `docs/PLATFORM.md`, "AWS Batch": 「預檢不計費」 says the preflight only reads, creates no Batch job and costs nothing.

## Launching on Google Batch (gcb-launch): the maintainer and the reviewer check

The automatic tests use fakes for the program runner, the detached start and the signal; they start nothing and touch no network. The steps below start a real Nextflow head process and **cost a very small amount of money**: set the budget and alert of the Google Cloud project first.

1. **The platform host (WSL).** Check: `java -version` says 17 or newer, `nextflow -version` and `gcloud --version` answer, `storage_root` is set in `config/env.yaml`, and the key file is where `ABF_STATION_GCP_CREDENTIALS` points, mode 600.
2. **Send the smallest run.** Put two or three tiny files in the bucket of `workDir` with `gcloud storage cp`, then `abf-launch ... --ce gcb1` with `gs://` paths in the samplesheet. Check: the first paragraph of the screen says 由 Google 向實驗室的 Google Cloud 帳號收費; nothing starts until you answer y.
3. **After y.** Check: `已啟動：主控程序編號（pid）...`; `ls <storage_root>/_gcb_runs/<run>` shows `head.pid` and `head.out`; the Batch page of the Google Cloud Console shows a job; the platform's run page shows progress (`-with-tower` works); when it ends, `gs://.../runs/<run>/results` has the output.
4. **Cancel one.** Send another run and cancel it with `abf-launch cancel <run>` after answering y. Check: the Batch job is cancelled or deleted (this checks that SIGTERM makes Nextflow cancel its Batch jobs). If it is not cleaned up, write it in `specs/gcb-launch/ledger.md` and tell the developer-agent; do **not** add a `gcloud batch jobs delete` by hand into the code.
5. **Search for the key.** In `platform.db`, `abf-platform ce show gcb1`, the launch screen, the logs and `head.sh`, search for any piece of the key file and for its path. Check: nothing is found.
6. **Two facts to write down in `specs/gcb-launch/ledger.md`.** Whether `process.resourceLabels` shows up as labels on the Batch job, and whether a short `network` / `subnetwork` name (if you set one) was accepted.

**The reviewer.** Run `git diff --name-only <base>...HEAD` and compare with the list under "Scope: files" in `specs/gcb-launch/plan.md`: nothing else is changed; `records.py`, `web*.py`, `agent.py` and the `hello` facts are untouched; no Slurm test file is touched. Of the C-1 tests (`test_gcb_ce.py`) only five places changed: the job kinds that are refused, the first line and name of the "never auto picked" test, the two patterns dropped from the "later slices" test, the documentation strings, and the one job kind that `test_refusals_are_plain_words` probes (`launch_nextflow` is allowed now, so it asks `list_site_files`, which is still refused; the plan's list did not name this one, see the ledger).

## Cloud cost (cloud-cost): the maintainer and the reviewer check

The automatic tests use a made-up price list and databases in a temporary folder; they touch no network. The steps below run a real Google Batch job and **cost a very small amount of money**: set the budget and the alert of the Google Cloud project first (the budget is Google's own reminder, not the platform's cap; see `docs/CLOUD.md`).

1. **Set a small cap.** `abf-platform user add <name> --lab <lab> --cloud-cap-usd 5` (or `abf-platform user cloud-cap <name> 5` for an account that exists). Check: the command prints the cap; a wrong value (`-1`, `abc`, `nan`, `1e9`) is refused in words and leaves the cap as it was.
2. **Run the smallest analysis on `gcb1`** the way the gcb-launch section says, then open `index.db` and look at `task_usage`. Check: `machine_type`, `price_model` and `cloud_zone` are filled. If they are NULL, Nextflow's `google-batch` executor did not send them: stop and tell the developer-agent; do not change the code to guess.
3. **Compare with the bill (postponed to `cloud-rates-fill`).** The shipped price list is empty on purpose, so every estimate is unknown now; write "not done: no prices yet" in the ledger, do not pretend. Once prices exist:  Work out the run with `cloud_cost.run_tasks_cost` (it gives the US dollars, or `None` with the reasons) and compare it with the Compute Engine cost of the same hours in the Google Cloud Console. Check: write the difference in `specs/cloud-cost/ledger.md`. It should be a little under the bill (start-up time and disks are not counted); if it is far off, tell the developer-agent; do not change a price by hand.
4. **Make the cap bite.** Set the cap below "used + estimate" (for example 0; with the empty price list only 0 or "already used up" can bite) and call `cloud_cost.cap_problem` for the same environment and pipeline. Check: the answer is a plain refusal with the cap, the used amount, what is left and the estimate in `US$` with two decimals. (Launching from the web or the AI now makes the same call before it creates anything; see "Cloud cost wiring" below and `docs/CLOUD.md`.)

**The reviewer.** Run `git diff --name-only origin/v3...HEAD`: only the files under "Scope: files" in `specs/cloud-cost/plan.md`; none of `abf_launch/build.py`, `abf_station/launch.py`, `actions/__init__.py`, `pipeline_launch.py`, `pyproject.toml`, `setup.py`, `su.py`, `records.py`, `jobs.py`, `compute_envs.py`. In `test_gcb_ce.py` one assertion changed (`cloud_cost.py` may exist now) and in `test_web_actions.py` one line (the new table `tokens.cloud_caps`) plus its comment; nothing else was loosened, deleted or skipped. If `platform/abf_platform/data/cloud_rates.json` has entries, open up to three `source` addresses at random and compare the number on the page with the file; mark an address that does not open as unverified.

## Cloud cost wiring (cloud-cost-wire): the maintainer and the reviewer check

The cap is looked at before a launch to Google Batch from the web or the AI creates anything, and the launch screen has a cost line. Steps 1 to 4 cost nothing: they stop before the confirmation or only read the screen. **Do not press 送出 in steps 1 to 3.** The shipped price list is empty, so every estimate reads "無法預估" now.

1. **A cap of 0.** `abf-platform user cloud-cap <name> 0`, then launch on `gcb1` as that account from the web or the AI. Check: the answer is a plain refusal that starts with 未送出 and names the cap, the amount used and what is left in `US$`; `jobs` and `confirmations` have no new row.
2. **No cap at all.** Do the same with an account that has no cap. Check: refused, and the sentence mentions `cloud-cap`.
3. **Room left.** Launch as an account with a cap above its use. Check: the line after the cost sentence reads 費用預估：無法預估（…） with a reason (the price list is empty); do not press 送出.
4. **Slurm.** Launch on nano4 (Slurm). Check: the screen is the same as before this task.
5. **(After `cloud-rates-fill` has put real prices in.)** Send a pipeline for the second time. Check: the cost line reads 費用預估：約 US$… with the run it is based on.

**The reviewer.** Run `git diff --name-only origin/v3...HEAD`: only the files under "Scope: files" in `specs/cloud-cost-wire/plan.md` and `specs/cloud-cost-wire/`; none of `abf_launch/cli.py`, `store.py`, `receiver.py`, `jobs.py`, `confirm.py`, `web.py`, `mcp_server.py`, `cloud_rates.json`. `git diff origin/v3...HEAD -- platform/abf_platform/cloud_cost.py` must not touch `cap_problem`, `NO_CAP` or `_money`. The terminal command `abf-launch` and a local stdio client have no account, so they are not checked against a cap (a known gap, see `docs/CLOUD.md`). In `test_gcb_launch.py` only the sentence of the first-paragraph test changed.

## Datasets in a cloud bucket (cloud-upload): the maintainer and the reviewer check

This task delivers the platform half only: a Dataset can be registered at `gs://` places, other people's places are refused, and a file over 2 GB gets a one-line command. **The end-to-end check (really sending a file into the bucket from the web or the AI) has to wait for a web or AI entry; for now only registering and refusing can be checked.** The automatic tests use fakes and touch no network. The steps below use `abf-platform dataset` on the platform host, with a Google Batch environment `gcb1` (workDir `gs://<bucket>/work`) that you own and a user name `<you>`.

1. **Register a cloud Dataset.** Run `abf-platform dataset register --destination gcb1 --user <you> ...` with two `--file` places `gs://<bucket>/uploads/<you>/a_R1.fastq.gz` and `.../a_R2.fastq.gz` and a samplesheet that names exactly those two. Check: the answer says `ok`, and `abf-platform dataset show` shows the same two `gs://` places and nothing else per file.
2. **Somebody else's prefix.** Register a file at `gs://<bucket>/uploads/<another user>/a_R1.fastq.gz`. Check: it is refused, the sentence names only your own prefix `gs://<bucket>/uploads/<you>/`, and nothing is stored.
3. **Another bucket.** Register a file in a bucket that is not the one of `workDir`. Check: it is refused and the sentence says the bucket must be the one of the environment's workDir.
4. **Over 2 GB.** There is no command for the size check, so read the line in `docs/OPERATIONS.md` ("Datasets in the lab's bucket", point 2). Check: it starts with `gcloud storage cp ` and ends at your prefix `.../uploads/<you>/rawdata/`, the same as `cloud_store.big_file_command` builds, and the limit it names is 2 GB (2000000000 bytes, decimal).
5. **Nothing else changed.** Without `destination` every call answers as before. Search the platform database, the logs and your terminal output for any piece of the key file (for example `private_key`). Check: nothing is found.

**The reviewer.** Run `git diff --name-only <base>...HEAD`. Check: only `platform/abf_platform/actions/datasets.py`, `platform/abf_platform/cloud_store.py`, `platform/tests/test_cloud_upload.py`, `platform/tests/test_gcb_ce.py`, `docs/TESTING.md` and `specs/cloud-upload/*`; `actions/__init__.py`, `pipeline_launch.py`, `abf_launch/build.py`, `cli.py`, `store.py`, `deploy/`, `pyproject.toml` and `constraints.txt` are identical to the base.

Then check the existing tests with `git diff <base>...HEAD -- platform/tests/`. Check: `test_datasets.py`, `test_gcb_launch.py`, `test_station_envs.py`, `test_guidance.py`, `test_scope.py` and `test_actions_layer.py` have no difference. `test_gcb_ce.py` is the one allowed exception, and only in one place: the regex in `test_nothing_of_the_later_slices_exists` loses `storage cp`; everything else in that file is unchanged, and no assertion is deleted, loosened or skipped.

Last, look for split strings: run `grep -nE '"[^"]*" *\+ *"' platform/tests/test_cloud_upload.py` and read each hit. Check: no path or forbidden word is cut in two and joined again to dodge a scan (for example `/home` split); a path that is needed is made with `tmp_path`; the scans in `test_scope.py` and `test_datasets.py` still pass. A plain join that is not a dodge is fine.

## Launching a composed pipeline (017d): the maintainer runs one on nano4, the reviewer checks the diff

The automatic tests use a fake site and no real Nextflow (the CI has none), so what Nextflow does with the project is checked once by a person. The run costs a few core-hours on nano4.

1. **Save and check.** Save the fastqc to multiqc graph as a composed pipeline (`actions.pipelines`), check it, and have two small FASTQ files ready under the storage root. Make a samplesheet with the columns `sample,reads` (one file per row).
2. **Send it.** Call `request_pipeline_launch` for the saved pipeline (the terminal or a script; there is no tool yet). Check: the answer names a page `/c/<id>`; nothing is queued; the page shows the whole `main.nf`, the project's `nextflow.config` and the list of the other files with their hashes; the last line of `head.sh` starts `<run folder>/pipeline/main.nf`. Press 送出 as yourself.
3. **On the site.** Check: `<run folder>/pipeline/` holds `main.nf`, `nextflow.config`, `modules.json` and `modules/nf-core/fastqc/main.nf` and `modules/nf-core/multiqc/main.nf`; the Slurm job runs; the run page shows progress (`-with-tower`).
4. **What Nextflow did with it.** Check: the settings of the project's `nextflow.config` were read (`ext.args = '--quiet'` shows in the `.command.sh` of a FASTQC task), `<run folder>/results/fastqc` and `results/multiqc` hold the outputs (the `publishDir` block works), and the containers were pulled online by nano4 itself. Write what you saw in `specs/017d-launch-composed/ledger.md`; if the project's config was not read, tell the developer-agent (the head script then needs a change, not a workaround by hand).
5. **A refused case.** Send the same pipeline with a samplesheet that has no `reads` column. Check: the refusal starts 未送出 and says which columns are needed. Then resume the failed or finished run. Check: the refusal says a composed run cannot be resumed yet.
6. **The reviewer.** Run `git diff --name-only <base>...HEAD` and compare with "Scope: files" of `specs/017d-launch-composed/plan.md`; `store.py`, `jobs.py`, `confirm.py`, `compose.py`, `catalogue.py`, `validate.py`, `actions/pipelines.py`, `mcp_server.py` and `web.py` are untouched; the existing tests changed only as the ledger says; the non-composed bundle, head script and screen are byte for byte what they were.

## Hosted deploy (hosted-deploy): the maintainer and the reviewer check

The automatic test, `tests/hosted_deploy_test.sh`, reads the files in `deploy/` and runs the backup script on a fake data folder; it starts no service and touches no network. The steps below start real services and are yours to run; nothing in the task ran them. Replace `<funnel-address>` with the address Funnel prints.

1. **The always-on desktop (WSL).** Copy `deploy/systemd/abf-*.service.in` to `~/.config/systemd/user/` and drop the `.in` (for example `abf-serve.service`), replace `<venv>` as `docs/OPERATIONS.md` section 3 says, copy `deploy/env.example` to `~/.config/abf-platform/env` (mode 600) and fill it in, then `systemctl --user daemon-reload` and `systemctl --user enable --now abf-serve abf-mcp abf-web`. Check: `systemctl --user status abf-serve abf-mcp abf-web` shows `active (running)` for all three.
2. **Caddy and Funnel.** Set `ABF_SITE_ADDRESS=http://127.0.0.1:8080` in the env file, start `caddy run --config deploy/Caddyfile.template --envfile ~/.config/abf-platform/env`, then `tailscale funnel --bg 8080`. Check: from a phone on mobile data, `https://<funnel-address>/` shows the login page, and `curl -i https://<funnel-address>/user-info` answers 401 with an `X-ABF-Platform` header.
3. **Claude Desktop.** Point the connector at `https://<funnel-address>/mcp` and go through the OAuth login and the consent page. Check: the connector lists the platform's tools. Write the result where "Claude Desktop custom connector (#117)" asks for it.
4. **A crash.** Find the process of one service (`systemctl --user show -p MainPID abf-web`) and kill it. Check: within 5 seconds `systemctl --user status abf-web` shows it running again with a new process number.
5. **Backup and restore.** Run `deploy/backup.sh ~/backups`. Stop the three services, copy the files of the newest `abf-backup-...` folder into an empty folder, and run `ABF_PLATFORM_DB=<that folder>/index.db abf-platform pat list`. Check: the tokens you issued are listed (never their values).
6. **A rented server.** On the VPS use the same files with `ABF_SITE_ADDRESS=<your-domain>` and follow "Hosting one lab" in `docs/OPERATIONS.md`. Check: Caddy gets the certificate by itself and `curl -i https://<your-domain>/user-info` answers 401 with `X-ABF-Platform`.

**The reviewer.** Run `git diff --name-only <base>...HEAD`: only `deploy/`, `tests/hosted_deploy_test.sh`, the three docs and `specs/hosted-deploy/` appear; nothing under `platform/abf_platform/`, `platform/abf_station/` or `platform/abf_launch/`; no existing test file is changed.

## The cost page (cost-page): the maintainer and the reviewer check three things

The automatic tests (`platform/tests/test_web_cost.py`) check the numbers and the markup. What a person sees on a small screen and with the keyboard is checked once by hand. Start `abf-platform web`, log in as a person who has some runs, and open `/usage`.

1. **A 390 px screen (TC-065).** Make the browser window 390 px wide (the developer tools' phone mode). Open `/usage` and `/usage?lang=en`, once with runs, once with more than 50 runs in the month (the page lists 50), once with none. Check: no horizontal scroll bar on the page, the four cards stack, the table text can be read.
2. **The keyboard (TC-066).** Press Tab from the top of `/usage`. Check: each link it stops on (the masthead cost link, the language links, the previous and next month links, the analysis names in the table) shows a visible focus outline.
3. **Both languages (TC-067).** Look at the whole of `/usage` and then of `/usage?lang=en`. Check: both are complete, the layout is the same, and the English page has no Chinese word except the language switch and your own run names; the month notice (`/usage?month=abc`) is also in English.

**The reviewer.** Read the section "The cost page" of `docs/PLATFORM.md` (TC-069): it says where the SU, cloud used, cap, remaining and the per-analysis usage come from. Run `git diff --name-only <base>...HEAD`: `web.py` and `web_board.py` appear, and the diff of `web_board.py` is only the masthead and the two cost strings; `test_tc051` is unchanged.

## 設定頁（settings-page）: the maintainer and the reviewer check

Automatic tests: `platform/tests/test_web_settings.py`. These steps are what no script can see. Open `/settings` logged in, once in Chinese and once with `?lang=en`.

1. **390 px**: narrow the window (or the browser's phone view) to 390 px. The page must not scroll sideways; the two tables wrap their text instead of being cut off.
2. **Tab**: press Tab through the page. Every thing that takes focus (the logout button, the language links) shows a visible outline. The middle column has nothing to focus, by design: it is read-only.
3. **Read both languages**: every status shows a symbol, a word and a colour (✓ / ✗ / —). No Chinese on the English page, no error code, no internal name. Each ✗ in 使用前檢查 says what is missing.
4. **Nothing to press**: no button, box or link in the middle column; the only form on the page is the logout one.

## SU 約 US$ (su-usd): the maintainer checks three things by hand

The automatic tests (`platform/tests/test_su_usd.py`) check the numbers and the markup. Start `abf-platform web`, log in as a person who has finished national HPC runs, and open `/usage` and one run's page (`/?run=<id>`).

1. **A 390 px screen (TC-063).** Make the browser window 390 px wide. Open `/usage` and the run page. Check: no horizontal scroll bar, and `51.50 SU（約 US$0.16）` style text can be read whole in its cell or card.
2. **Both languages (TC-064).** Open the same pages with `?lang=en`. Check: Chinese shows `（約 US$…）`, English shows `(≈ US$…)`, and the English page has no Chinese word except the language switch and your own names.
3. **The date under the cards (TC-065).** Read the sentence after the cost note on `/usage`. Check: the date in it is the same as `usd_twd.as_of` in `configs/sites/su_rates.json`.

## A temporary password, then your own (web-change-password): the maintainer and the reviewer check

Automatic tests: `platform/tests/test_web_welcome.py`. These steps need a real browser and the platform host's terminal. Use a test user, never a real colleague's name.

1. On the platform host's terminal run `abf-platform user passwd <name> --temporary` and write down the 16-character password it prints once. It works for 72 hours.
2. In a browser open the login page, log in as `<name>` with that password. Pass: you land on `/welcome` ("設定你自己的密碼 (set your own password)"), not on the board.
3. Type `/` in the address bar. Pass: you are brought back to `/welcome`; no run, no cost, no 送出 button is shown anywhere.
4. On `/welcome` fill the three boxes (the temporary password, a new password of 8 or more characters, the same new password again) and press 設定密碼. Pass: you go straight to the board without logging in again. Try once with two different new passwords first: the page says so and nothing changes.
5. Press 登出, then log in with the new password. Pass: it works and you land on the board. Log in with the old temporary password. Pass: it is refused.

## Finished stage (finished-stage): the maintainer and the reviewer check

The automatic tests are in `platform/tests/test_web_finished.py`. The steps below need a browser and a succeeded run that was launched from the platform.

1. **Open it by clicking.** From the run list click the run, then "完成" in the stage strip. Check: the page shows "來源紀錄" and "交付包" with no extra download step or input.
2. **390 px.** Narrow the browser to 390 px wide (developer tools, device mode) and open the stage of a run with a long parameter value. Check: there is no horizontal scroll bar and the long value wraps inside its column.
3. **Tab key.** On the finished stage press Tab repeatedly. Check: every link (stage strip, "查看輸出", previous stage) shows a visible focus outline in turn; the grey "之後開放" lines are never focused.

## Analysis state squares (status-squares-3): the maintainer and the reviewer check

The automatic tests are in `platform/tests/test_web_status_squares_3.py`. The steps below need a browser and four analyses: one running, one succeeded, one failed and one that lost contact with the platform.

1. **Screenshots.** Take `/` and the failed analysis page at 1440 px and at 390 px, each in 中文 and in English (4 sets). Check: every analysis state is a small coloured square followed by a word (執行中 / 完成 / 失敗, or Running / Done / Failed); there is no ▶ ✓ ✗ on any of them; the lost analysis shows 失敗 / Failed. Show the pictures to the maintainer; he must say "好" before the merge.
2. **Black and white.** Turn the pictures grey (or the screen's colour filter on). Check: the three states can still be told apart by the word alone.
3. **390 px.** In developer tools (device mode, 390 px wide) open `/` and each of the four analyses, in both languages, and run `document.documentElement.scrollWidth === document.documentElement.clientWidth` in the console. Check: it is `true` (no horizontal scroll bar); no square or word is cut off or overlaps. Write the numbers in the PR.
4. **Tab key.** Press Tab repeatedly on the failed analysis page. Check: each link and button shows a visible focus outline in turn.
5. **Detector.** Save the rendered HTML of `/` and of the failed analysis page to files and run `sh .claude/skills/impeccable/scripts/impeccable detect <file.html>` on each. Check: it runs; copy its findings into the review (contrast and fonts are for a person to judge, not a failure).

## release-lookup-job：真的連 GitHub 讀一次 (release-lookup-job: read GitHub for real, once)

The automatic tests never reach the internet (a guard fails any test that tries). This is the one time a person checks it for real: the maintainer or developer-agent does it, on a machine with a network. It only sends read requests for public files. Nothing is written and no credential is sent.

1. **Start the platform and an agent** as in sections 1 and 6 of `docs/PLATFORM.md`, and add a compute environment that names that agent (it does not need to be checked first: this job never touches the site).
2. **Pipeline files.** In one line of Python call `actions.pipeline_files(<path of platform.db>, "nf-core/ampliseq", "2.18.0")` and call it again every 5 seconds until `state` is no longer `loading` (about a minute at most: the agent asks for work every 25 seconds). Check: `state` is `ready`; `schema.groups` has 16 groups holding 170 parameters in all; `schema.required_without_default == ["outdir"]`; the first column of `schema_input.columns` is `sampleID`; `diagram.name == "ampliseq_workflow.png"` and `diagram.size == 753702`. Then call it with `parts=("image",)`. Check: `len(base64.b64decode(image["data_b64"])) == 753702` and the bytes begin with the PNG signature `\x89PNG`.
3. **Newest release.** Call `actions.latest_release(<path>, "nf-core/ampliseq")` the same way. Check: it ends as the newest plain numbered tag (on 2026-10-25 that was `3.0.0`; go by GitHub on the day), `source` is `fetched`, and `release-tags.json` has appeared beside `platform.db`. Call it again at once. Check: `source` is `cache` and the `jobs` table has no new `pipeline_files` row.
4. **No network.** Switch the agent machine's network off (or stop its access to the internet) and call `actions.pipeline_files(<path>, "nf-core/rnaseq", "3.27.0")`, a pair not asked before. Check: within about a minute `state` is `error`, `error` is `network`, and `reason` is a plain sentence that tells you to check the machine's network.
5. **Write down** the output of each step in `specs/release-lookup-job/ledger.md`.

## Cleaning a finished run's work folder (cloud-cleanup): the maintainer checks five things

The machine part is `platform/tests/test_cleanup_offer.py` (a fake site, a fake bucket, the real agents). Only you can do the following, each on **your own test run**, and each by the **product itself** (the confirmation page): do not use an AI session to run a delete command on the cluster or in the bucket.

1. *nano4: the notice, the page, the button.* Run something very small on nano4 (for example `ampliseq-d5` with the smallest samplesheet) until it succeeds. The board's right column shows the notice "可以清掉中間檔"; open it (`/c/<id>`). The screen has the three sentences (the folder that will be deleted for good, results and raw data untouched, the run cannot be resumed). **Do not press yet.** After a while list `<run folder>/work` with `list_site_files`: it is still there. Then press 確認刪除: only `work` is gone, `results/` is complete.
2. *nano4: is `work` where the formula says?* Open the head of the Nextflow log (or `.nextflow.log`) of that run and read `work-dir`. It must be `<run folder>/work`. If it is not, **stop and report**: the site's settings or the `nextflowConfig` changed `workDir`, and the formula has to change.
3. *Google Batch (your own account).* The same run on Google Batch. Before you press, put two objects beside it by hand: `<workDir>/runs/<run>/work2/x` and `<workDir>/runs/<run>/work-keep`. After 確認刪除 the prefix `<workDir>/runs/<run>/work/` is gone and the two others are still there (this is the first real test of how `gcloud storage rm --recursive` treats the trailing slash; cloud-cleanup-d trusted the documentation only). Write down whether the bucket has soft delete or object versioning and whether the deleted objects can still be listed, put the answer into `specs/cloud-cleanup-d/ledger.md`, and check that the fourth sentence of the screen says the same.
4. *nano4: a resumed attempt.* Make a run fail, resume it (`-a2`) and let it succeed. The notice is on the `-a2` run. Press 確認刪除: the `work` folder of the **first** run's folder is gone and the rest of that folder is still there.
5. *A request that lapsed is not offered again.* In your own test database move one request's `expires_at` into the past. The confirmation page says 已逾時（7 天）, the board has no notice for it, and no new request for that run appears later.

Then keep the screenshots (the confirmation page with the text of `clean_screen`, and the board card, in Chinese and in English) for the daily list; the maintainer answers 好 or 不好.

## Offering a clean-up for an old run (cloud-cleanup-backfill): the maintainer checks it on nano4

The machine part is `platform/tests/test_cleanup_backfill.py`. The command only asks; the owner of the run still presses the button. Do not use an AI session to delete anything.

1. Find a run that succeeded **before** the clean-up offer existed (the board shows it as finished, and its owner has no "可以清掉中間檔" notice).
2. On the platform host run `abf-platform runs offer-cleanup <run>` without any other flag. It must print `<run>: 會提出申請 (would offer)` and the owner's board must show nothing new. The last line starts with `預覽：`.
3. Run the same line with `--apply`. It prints `已提出申請，請 <owner> 登入網頁在確認頁按送出`.
4. Sign in on the web as the owner: the right column "待處理" has the notice and the confirmation page shows the clean-up request.
5. **Do not press.** List `<run folder>/work` on nano4 (`list_site_files`): it is still there.

Write 好 or 不好 for the daily list.

## nfcore-catalogue：真的讀一次 nf-co.re (read nf-co.re for real, once)

The automatic tests never reach the internet. This is the one time a person checks it for real: the maintainer or developer-agent does it after the merge, on a machine with a network. It only sends one read request for a public file.

1. **Start the platform and an agent** and add a compute environment that names that agent (same as step 1 of the release-lookup-job section).
2. **The list.** In one line of Python call `actions.nfcore_catalogue(<path of platform.db>)` and call it again every 5 seconds until `state` is no longer `loading` (about a minute at most). Check: `state` is `ready` and `count` is at least 150 (159 on 2026-10-26); the entry with `name` `ampliseq` has `repo` `nf-core/ampliseq`, `archived` `False` and `latest` the newest plain numbered tag (on 2026-10-26 that was `3.0.0`; go by nf-co.re on the day); `exoseq` has `archived` `True`; `abotyper` has `latest` `None` (it only has `dev`); the list is sorted by `name`; no new file appeared beside `platform.db`.
3. **Reuse.** Call it again at once. Check: the same `checked_at` and no new `pipeline_files` row in the `jobs` table (the agent prints one line per job, not per request, so the jobs table is the check).
4. **No network.** Switch the agent machine's network off, delete that job row (or wait 24 hours) and call it again. Check: within about a minute `state` is `error`, `error` is `network`, and `reason` names nf-co.re and says to check the network.
5. **Write down** the output of each step in `specs/nfcore-catalogue/ledger.md`.

## Owner binding follow-up (owner-binding)

For the administrator of a platform that has two users, alice and bob, and an old agent token that names no user. This is a data move: nothing in the schema changed.

1. **Find what has no owner.** Run `abf-platform ce list` and `abf-platform launches`. Note every agent or environment whose owner reads `(none: local only)`.
2. **Reissue the old tokens.** For each agent whose old token names no user: check that its hello is now refused (403), then `abf-platform agent-token revoke <name>` and `abf-platform agent-token new <name> --user <U>`; put the new token in the agent's token file and restart the agent. Check: the new token's hello is accepted and the agent keeps its owner.
3. **Give the environments their owners.** `abf-platform ce update <env> --owner <U>` for each environment that has none; this claims its unowned agent too. Restarting the platform does the same for an agent whose environments all belong to one user.
4. **Check the walls.** With alice's personal access token call `list_agents` and `get_compute_env`: only her own show. With bob's token ask `get_compute_env` for alice's environment and for a name that does not exist: the two answers are the same words ("not found").

## Azure Batch environment (azure-ce-type): the maintainer and the reviewer check

The automatic tests use a fake `az` runner and a fake `which`; they call no network and no real Azure. The steps below read a real Azure account once. 預檢不計費 (the preflight costs nothing): it creates no pool and no job, so the Azure bill must show no new item afterwards.

1. **TC-089: the maintainer prepares by hand, once.** Create a Batch account, a storage account, a blob container and one pool (the pool must already exist). Install the Azure CLI on the platform host. Put `[default]` with `batch_account_key` and `storage_account_key` in `<agent deployment>/_personal/azure-credentials` (mode 600), or point `ABF_STATION_AZURE_CREDENTIALS` at it.
2. **TC-089: create the environment.** `abf-platform ce create --name az1 --platform azbatch-platform --agent <agent> --credentials azure-lab --location <region> --batch-account <name> --storage-account <name> --work-dir az://<container>/work --pool <pool>`. Check: every check is shown; when all pass, `ce show az1` says `available`; neither `ce show` nor `platform.db` holds any piece of a key; the Azure bill shows no new item.
3. **TC-090: the key-only call.** Check that `az batch pool show` really works with only the key variables and without `az batch account login`. If it does not, the `pool` check fails: report it to the developer-agent, do not change the check by hand.
4. **TC-131: the reviewer, scope.** Run `git diff --name-only` against the base: only the files in the plan's file list, the existing tests that the rulings list, and the tests recorded in the ledger. No web file, nothing in `abf_launch/`, no `gcb_preflight.py`, `aws_preflight.py`, `launch.py`, `cloud_store.py` or `clean.py`.
5. **TC-132: the reviewer, existing assertions.** Run `git diff` on each existing test file: the only changes are Azure added to a set, a count or a document line, Azure moved out of the unsupported list, `eleven` turned `ten`, and `azbatch-platform` swapped for a type that is still unsupported. No assertion is deleted or loosened, and nothing about AWS, Google or Slurm changed.

## Launching on Azure Batch (azure-launch): the maintainer and the reviewer check

The automatic tests use fakes for the program runner, the detached start and the signal; they start nothing and touch no network. The steps below start a real Nextflow head process and 會花錢、需維護者同意: set a budget and an alert in the Azure account first, and do not run them without the maintainer's yes.

1. **The platform host (WSL).** Check: `java -version` says 17 or newer, `nextflow -version` and `az --version` answer, `storage_root` is set in `config/env.yaml`, and the credential file is where `ABF_STATION_AZURE_CREDENTIALS` points, mode 600.
2. **The pool, on the Azure Portal.** Check: the pool is `dockerCompatible`, its task slots equal the cores of the node, the storage account is in the region of the Batch account, and every process has a `container`. If Nextflow stops at once with a pool setting error or cannot find a container, stop and report it to the developer-agent: do not add any setting by hand.
3. **Send the smallest run.** Put two or three tiny files in the container of `workDir` (with the az CLI), then `abf-launch ... --ce az1` with `az://` paths in the samplesheet. Check: the first paragraph of the screen says 由 Azure 向實驗室的 Azure 帳號收費; nothing starts until you answer y. Also check that the head process passes Azure authentication; if it reports an authentication failure (Nextflow did not read the key variables), write it in `specs/azure-launch/ledger.md` (the ledger) and tell the developer-agent: do not change how the credentials are passed by hand.
4. **After y.** Check: `已啟動：主控程序編號（pid）...`; `ls <storage_root>/_azure_runs/<run>` shows `head.pid` and `head.out`; the Azure Portal shows Batch jobs; when it ends, `az://<container>/runs/<run>/results` has the output.
5. **Cancel one.** Send another run and cancel it with `abf-launch cancel <run>` after answering y. Check: whether the Batch jobs stop by themselves after the SIGTERM. If they do not, write it in `specs/azure-launch/ledger.md` (the ledger) and tell the developer-agent; do **not** add an `az batch job terminate` by hand into the code.
6. **Search for the keys.** In `platform.db`, `abf-platform ce show az1`, the launch screen, the logs, `head.sh` and the Azure config file, search for any piece of the two keys and for the path of the credential file. Check: nothing is found.
7. **Four facts to write down in the ledger.** Whether `az batch pool show` works with the key variables alone, whether a pool whose task slots differ from its cores is accepted, what the Portal shows after a cancel, and whether `process.resourceLimits = [cpus: N]` in the Azure config is accepted by `azurebatch` (no unknown-setting error).

**The reviewer.** Run `git diff --name-only <base>...HEAD` and compare with the plan's file list: `azure_preflight.py`, `clean.py`, `put_upload.py`, `site.py`, `agent.py`, `cloud_cost.py`, `web*.py` and `abf_platform/cli.py` are untouched; no migration; no assertion was deleted, loosened or skipped.

## Kubernetes environment (k8s-ce): the maintainer and the reviewer check

The automatic tests use a fake `kubectl` runner and a fake `which`; they call no network and no real cluster. The steps below read a real cluster once. 預檢不計費 (the preflight costs nothing): it creates, changes and deletes nothing on the cluster. Four facts are unverified until this is done; if one turns out different, write it in `specs/k8s-ce/ledger.md` and report it to the developer-agent (回報), and do not change a check by hand.

1. **TC-166: the maintainer prepares by hand, once.** Have a cluster with a namespace, a claim that is `Bound` with `ReadWriteMany`, and (optionally) a service account. Install `kubectl` on the platform host. Put the kubeconfig in `<agent deployment>/_personal/kubeconfig` (mode 600), or point `ABF_STATION_KUBECONFIG` at it.
2. **TC-166: create the environment.** `abf-platform ce create --name k1 --platform k8s-platform --agent <agent> --credentials k8s-lab --context <context> --namespace <ns> --storage-claim <claim> --work-dir /workspace/work`. Check: all seven checks are shown; when all pass, `ce show k1` says `available`; neither `ce show` nor `platform.db` holds any piece of the kubeconfig.
3. **TC-156 (first fact): `config get-contexts` offline.** Check that `kubectl config get-contexts -o name` answers with no network. If it does not, the `context` check fails: report it.
4. **TC-157 (second fact): the shape of `accessModes`.** Check that `kubectl get pvc <claim> -o jsonpath={.spec.accessModes[*]}` prints the modes separated by spaces, and that `.status.phase` prints `Bound`.
5. **TC-158 (third fact): `KUBECACHEDIR`.** Check that `kubectl` with an empty `KUBECACHEDIR` still works and writes only into that folder, which the agent removes afterwards.
6. **TC-045 and TC-166 (fourth fact): least privilege.** Use a kubeconfig whose user may only `get` claims and service accounts, and check that the preflight still passes. Also check what the ledger says about the lines `client-certificate-data:` and `client-key-data:` pasted into a text field: the platform's existing rules may not catch them (recorded, no rule added).
7. **TC-143: the reviewer, scope.** Run `git diff --name-only <base>...HEAD` and compare with the plan's file list: no web file, nothing in `abf_launch/`, no `gcb_preflight.py`, `aws_preflight.py`, `azure_preflight.py`, `launch.py`, `cloud_store.py` or `clean.py`; no migration.
8. **TC-156: the reviewer, existing assertions.** Run `git diff` on each existing test file: the only changes are Kubernetes added to `CHECK_ONLY_TYPES` and `CHECKABLE`, Kubernetes moved out of the unsupported list (ten turned nine), and the document sentence. No assertion is deleted or loosened.

## When something is red

Fix the code, not the test — unless the test encodes a rule that changed, in
which case change the rule's statement in `docs/PRINCIPLES.md` first and the
test second, so the reason survives.

New assertions get a mutation test: remove the thing being checked and confirm
the test turns red. An assertion that has never failed has never been shown to
assert anything.

## Launching on AWS Batch (aws-launch): the maintainer and the reviewer check

The automatic tests use fakes for the program runner, the aws runner, the detached start and the signal; they start nothing and touch no network. The steps below start a real Nextflow head process and **cost a small amount of money** once the real trial run is approved: do not start them before the maintainer says go.

1. **The platform host (WSL), once.** Check: `java -version` says 17 or newer, `nextflow -version` and `aws --version` answer, `storage_root` is set in `config/env.yaml`, the credential file is where `ABF_STATION_AWS_CREDENTIALS` points (mode 600), and a budget alert is set in AWS Budgets.
2. **The compute image.** Check that the AMI of the compute environment behind the job queue has the aws CLI.
3. **Send the smallest run.** Put two or three tiny files in the bucket of `workDir` with the aws CLI, then `abf-launch ... --ce aws1` with `s3://` paths in the samplesheet. Check: the first paragraph of the screen says 由 AWS 向實驗室的 AWS 帳號收費; nothing starts until you answer y.
4. **Check that the credentials work.** If Nextflow does not honour `AWS_SHARED_CREDENTIALS_FILE`, the run fails at once: report it, do not work around it by putting a key in a file.
5. **After the run starts.** Check: the run folder under `<storage_root>/_aws_runs/` has `head.pid`, a Batch job appears in the AWS Console, and results arrive under `<workDir>/runs/<run>/results`.
6. **Cancel.** Cancel a second small run; check on the Batch page that every job ended (whether one SIGTERM stops them is what this step finds out), and search the run folder, `head.out` and the database for the key id and the credential path: neither must be found.
7. **`process.resourceLimits`.** Launch with `maxvCpus` set and check that Nextflow accepts the line in `aws.config`.

**The reviewer.** Run `git diff --name-only` against the base: no `cloud_cost.py`, no `local_runner.py`, no migration, no `boto3`; the existing tests changed only where `specs/aws-launch/plan.md` lists them.

## Uploading to AWS Batch (aws-upload): the maintainer checks by hand

The automatic tests use fakes for the `aws` program and never touch the network. A real upload writes to a real S3 bucket and **costs a small amount of money**: do not start it before the maintainer says go, and only with an AWS Budgets alarm set.

1. **Environment.** An available AWS Batch environment (`aws1`), the credential file at `ABF_STATION_AWS_CREDENTIALS` (mode 600), and `aws --version` answering on the platform host.
2. **File.** Stage one small file (about 10 MB) in your uploads folder and queue the upload for `aws1`.
3. **Expected.** The object appears at `s3://<workDir bucket>/uploads/<you>/<name>` with the same size, the answer says the staged copy was removed, and no key id or credential path appears in the answer or in the agent log.
4. **Over the limit.** Try a file over 2 GB: the answer gives the `aws s3 cp ... --recursive` line and nothing is uploaded.

## Uploading to Azure Batch (azure-upload): the maintainer checks by hand

The automatic tests use fakes for the `az` program and never touch the network. A real upload writes to a real Blob container and **會花一點錢、先設好成本警示** (an Azure Cost Management budget alert); do not start it before the maintainer says go.

1. **Environment.** An available Azure Batch environment (`azure1`), the credential file at `ABF_STATION_AZURE_CREDENTIALS` (mode 600), and `az --version` answering on the platform host.
2. **File.** Stage one small file (about 10 MB) in your uploads folder and queue the upload for `azure1`.
3. **Expected.** The blob appears at `az://<container of the workDir>/uploads/<you>/<name>`; check its size with `az storage blob show --account-name <account> --container-name <container> --name uploads/<you>/<name> --query properties.contentLength --output tsv --auth-mode key`, which equals the file; the answer says the staged copy was removed, and no key or credential path appears in the answer or in the agent log.
4. **Over the limit.** Try a file over 2 GB: the answer gives the `az storage blob upload-batch` line and nothing is uploaded.

## Cleaning an AWS Batch work folder (aws-clean): the maintainer checks by hand

The automatic tests use fakes for the `aws` program and never touch the network. A real clean deletes real objects from a real S3 bucket: do not start it before the maintainer says go, and only on a test bucket and a prefix that holds nothing you need. The real output format of `aws s3 ls --recursive` and `aws s3 rm --recursive` has not been seen by the tests (UNVERIFIED), so this step is also where it is checked.

1. **Environment.** An available AWS Batch environment (`aws1`), the credential file at `ABF_STATION_AWS_CREDENTIALS` (mode 600), a finished run `r1` whose head process is gone, and a test prefix `s3://<test bucket>/runs/r1/work/` holding a few small files, plus a neighbour such as `runs/r1/work2/` and `runs/r1/results/`.
2. **Ask and answer.** Open the clean request, read the screen (it names the prefix with a trailing slash, says results are untouched, shows no amount of money) and confirm.
3. **Expected.** Only the objects under `runs/r1/work/` are gone; `work2/` and `results/` are still there; the answer says 已刪除 and `work_cleaned_at` is recorded. List the prefix with the aws CLI yourself to see the real line format, and tell the developer if a line does not look like `date time size key`.
4. **Run it again.** The prefix is empty: the answer says there was nothing to delete and nothing is removed.
5. **Versioning.** If the test bucket has versioning on, check in the console that old versions are still there after the clean (the documents say they are, and they are still billed).

## Cleaning an Azure Batch work folder (azure-clean): the maintainer checks by hand

The automatic tests use fakes for the `az` program and never touch the network. A real clean deletes real blobs from a real storage account: do not start it before the maintainer says go, and only in a 測試用 container and a prefix that holds nothing you need. The real output of `az storage blob list --query "[].name" --output tsv` and of `az storage blob delete-batch` has not been seen by the tests (UNVERIFIED), so this step is also where it is checked.

1. **Environment.** An available Azure Batch environment (`az1`), the credential file at `ABF_STATION_AZURE_CREDENTIALS` (mode 600), a finished run `r1` whose head process is gone, and a test prefix `az://<test container>/<sub>/runs/r1/work/` holding a few small blobs, plus a neighbour such as `runs/r1/work2/` and `runs/r1/results/`.
2. **Ask and answer.** Open the clean request, read the screen (it names the prefix with a trailing slash, says results are untouched, mentions 軟刪除 and version control, shows no amount of money) and confirm.
3. **Expected.** Only the blobs under `runs/r1/work/` are gone; `work2/` and `results/` are still there; the answer says 已刪除 and `work_cleaned_at` is recorded. List the prefix with the az CLI yourself (`az storage blob list --container-name <c> --prefix <sub>/runs/r1/work/ --num-results "*" --query "[].name" --output tsv --auth-mode key`) to see the real line format, and tell the developer if a line is not a plain blob name. Check that `--num-results "*"` returned every blob and not the first 5000 only.
4. **Run it again.** The prefix is empty: the answer says there was nothing to delete and nothing is removed.
5. **Soft delete and versions.** If the storage account has blob soft delete or versioning on, check in the portal that deleted blobs and old versions are still there after the clean (the documents say they are).
6. **Wildcard.** Check that `delete-batch --pattern "<prefix>*"` really matches across `/` on your account (blobs two folders deep must go), and that it did not touch `work2/`.

