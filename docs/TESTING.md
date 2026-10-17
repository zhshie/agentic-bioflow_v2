# Testing a release

Two halves, and the split matters more than either half: one is machine-checked
and cheap, the other needs a human in a live Claude Code session and is the only
place several classes of defect can show up at all.

## Half 1 — what the machine checks

```bash
bash tests/run_all.sh
```

About 100 seconds, one verdict and a non-zero exit if anything fails.
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
The machine part is `tests/platform_test.sh` (run by `run_all.sh`). These seven checks need a person, or a git diff. Write the answers in the release notes.

1. *An AI client reads the runs (TC-023).* Follow `docs/PLATFORM.md` section 4 to add the MCP server to Claude Code, then to Claude Desktop. Have at least one run recorded, then ask "what is the state of my latest runs?". The AI must call `list_runs` and its answer must match what `abf-platform` holds (compare with the run name, state and task numbers Nextflow printed). No tool call, or numbers that differ, is a failure.
2. *The document is enough (TC-050).* Give `docs/PLATFORM.md` and nothing else to someone who has not used the platform. Without help they must manage: start the receiver, issue a token, point a Nextflow run at it, connect Claude Code and Claude Desktop, and rebuild the index. Record each place they got stuck. The document must also say what exposing it to the network risks, and that the default locations can be changed.
3. *The whole suite is green where it matters (TC-052).* In WSL (Windows) run `cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<path to the repo> && bash tests/run_all.sh'`, or `bash tests/run_all.sh` in Linux. The output must show `platform_test.sh` ran and passed, and no line `E2E SKIPPED`. Then read the CI result of the pull request: the same, `platform_test.sh` passed, nothing skipped. (`conditions_matrix_test.sh` fails in WSL for a reason that predates this feature; compare with `main`.)
4. *A real pipeline from the internet (TC-053).* In WSL, with the receiver and a token as in `docs/PLATFORM.md`, run `nextflow run nextflow-io/hello -with-tower http://127.0.0.1:8787` once so that it succeeds, and once made to fail (for example by stopping the run with Ctrl-C part way, or by pointing it at an input that does not exist). `list_runs` and `get_run` must show the same state and the same task numbers as Nextflow printed. This is the one check that uses a pipeline fetched from the internet; the automated tests use only the local fixtures.
5. *The constitution was not touched (TC-063).* `git diff main...HEAD -- .specify/memory/constitution.md` is empty, and its version line still reads 3.0.0. In `docs/ROADMAP.md`, the row "The platform's run index is never a second truth" is still in the table "Principles waiting for a check", with only a note added that the check exists (`platform/tests/test_nextflow_e2e.py`, `test_tc030_rebuild_gives_back_every_field`) and the amendment is next. It must not have moved into the constitution.
6. *The plugin was not touched (TC-064).* `git diff main...HEAD --stat -- hooks/ scripts/ skills/ .claude-plugin/` lists nothing.
7. *The existing checks were not touched (TC-073).* `git diff main...HEAD --stat -- tests/no_hardcoded_paths.sh tests/scripts_name_their_alternative.sh tests/no_second_run_state_test.sh tests/run_all.sh` lists nothing. `bash tests/run_all.sh --list` includes `platform_test.sh`, and those three checks pass as before.

**When a release adds or changes the station agent or the compute environments (`platform/abf_station/`, `docs/PLATFORM.md` sections 6 to 8; feature 007).**
The machine part is `tests/platform_test.sh` (run by `run_all.sh`): it starts a real platform process and a real agent process against a fake site. These eight cases need a person or a git diff. Write the answers in the release notes.

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

   Then list the same `results` folder again with `list_site_files`: nothing may have changed. (`rm` is not a job kind, and no job kind writes.)
4. *Both suites are green where it matters (TC-081).* In WSL run `bash tests/run_all.sh` (`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<path to the repo> && bash tests/run_all.sh'` from Git Bash); the output must show `platform_test.sh` passed and no `E2E SKIPPED`. Then read the CI result of the pull request: the same, nothing skipped.
5. *The constitution was not touched (TC-088).* `git diff main...HEAD -- .specify/memory/constitution.md` is empty and its version line still reads 3.0.0. In `docs/ROADMAP.md` the rows of "Principles waiting for a check" are all still in that table (a note that a check exists is the most that may be added).
6. *The existing checks and the plugin were not touched (TC-093).* `git diff main...HEAD --stat -- tests/no_hardcoded_paths.sh tests/scripts_name_their_alternative.sh tests/no_second_run_state_test.sh tests/command_layer_is_site_neutral.sh tests/credentials_stay_in_settings_test.sh tests/run_all.sh hooks/ scripts/ skills/ .claude-plugin/` lists nothing, and `bash tests/run_all.sh --list` includes `platform_test.sh`.
7. *No 008 assertion was weakened (TC-094).* `git diff main...HEAD -- platform/tests/test_mcp.py platform/tests/test_scope.py platform/tests/test_receiver.py platform/tests/test_cli.py platform/tests/test_secrets.py platform/tests/test_status.py platform/tests/test_common.py platform/tests/test_nextflow_e2e.py platform/tests/test_wrapper.py platform/tests/conftest.py platform/tests/helpers.py platform/tests/e2e_harness.py`: only the named changes appear. The tool count of the two MCP tests goes from two to six, every tool still read-only and no input field named like a command; the header check of `test_scope.py` also covers `abf_station/`. Any removed, loosened or re-valued assertion is a failure.
8. *The plan answers the constitution (TC-095).* Read `specs/007-station-agent/plan.md`, "Constitution Check": it must answer principle 1 (the alternatives), principle 2 (why the poll loop and the job table are neither a monitoring daemon nor a state machine), principle 3, section II-4 (why modelling thirteen types is allowed), principle V (WSL and Git Bash), principle VI, the Safety Net scope (the agent is a path that passes no hook; its allow-list and the tests guard it) and where credentials live.

Record the answers in the release's own notes. A check nobody wrote down is a
check that gets re-argued three sessions later.

**When a release adds or changes launch, cancel or the way back (`platform/abf_launch/`, `platform/abf_station/launch.py`, `scripts/nf_relay.py`, the forward options of `scripts/on_site.sh`, `docs/PLATFORM.md` section 9; feature 007b).**
The machine part is `tests/platform_test.sh`. These cases need the real cluster or a person with `git diff`; do them in WSL on the maintainer's laptop, with the shared connection opened by hand as usual.

1. *Acceptance: ampliseq runs to the end (TC-047).* Start the platform and the agent (section 6). Run `abf-platform launch` with `nf-core/ampliseq`, `2.18.0`, the 10 fastq files of `microbiome_test`, primers 27F/1492R, PacBio, SILVA 138.2 (the settings of the 2026-09-20 run). Check the screen lists every item, compare its parameters with that run's `params.yaml` (only `outdir` may differ), answer y. Run `abf-platform launches` while it queues (it must say `已送出，尚未收到 Nextflow 事件`), then watch `get_run` at three different moments (the done, running and failed counts per process change). At the end the run is succeeded, its task total equals the rows of `trace.txt` on the site, `results/` is in the run folder, the folder is mode 700, and `grep -r` for the run's token finds it only in `tower.token` (not in `.nextflow.log`, not in the Slurm output).
2. *Cancel a small run (TC-048).* Launch a small run with tasks that take a few minutes. Record `squeue -u <you>`. Run `abf-platform cancel <run>`, answer y; every 30 seconds look at `squeue` and `get_run` until it settles. The head job and its tasks leave `squeue`; your other jobs and everybody else's stay; `get_run` shows Nextflow's end (failed, with its reason), not success; `abf-platform launches` lists "取消請求已於 T 送出"; the run folder and the records are still there. Note any task that stays and check that the output told you to look. The run's token stops working once its `complete` has arrived. Open the run's `.nextflow.log`: it must hold no `Report file already exists` and no `Timeline file already exists` (abort-report-overwrite, TC-012). For a small run that finishes normally, `results/pipeline_info/` must still hold the execution report and the timeline, as many as before (TC-014).
3. *The way back on the real site (TC-049).* Open the forward (a launch does it; or `scripts/on_site.sh --forward <platform port>`). On the login node `ss -ltn` shows the forward bound to `127.0.0.1` only. From a compute node (a short job you approve) run `curl -x http://<login node>:<relay port> http://127.0.0.1:<forward port>/user-info`: 401 with an `X-ABF-Platform` header. Try another port and `/agent/poll`: the relay refuses (see its log, `DENY`). Try `<login node>:<forward port>` directly: it fails. Run `abf-station unforward --deployment <root>` and repeat: it fails. Start a launch against a relay process started before this feature: the launch refuses and says `請重啟 relay`; restart it and it passes.
4. *Seqera comparison (TC-050).* While the run of step 1 is going, compare `get_run` with what Seqera showed for the 2026-09-20 run (process names, how the counts grow). Write down in plain words what is missing compared with Seqera and check `docs/SEQERA_PARITY.md` section L says the same (the list of every task, CPU and memory, logs and reports, a queued state).
5. *The tests cannot be talked out of it (TC-053).* In `platform/abf_station/launch.py` temporarily remove the lines of `verify_confirmation` that compare the hashes; run `test_unconfirmed_launch_is_refused` and the tests of TC-007, TC-008, TC-009 in `platform/tests/test_station_launch.py`: all four go red. Restore the file and they go green. Put the steps and results in the acceptance report.
6. *Existing assertions were only narrowed (TC-060).* `git diff main...HEAD -- platform/tests tests` shows, among the existing tests, changes only in `test_station_envs.py` (the two subcommand/help assertions), `test_station_platform.py` (the job kinds and the one table name that may contain "run"), `test_station_static.py` (the launch module may hold the submitting words) and `tests/no_second_run_state_test.sh` (LAUNCH_ALLOW and its self-test); no assertion is deleted, weakened or turned into a skip.
7. *Nothing else was touched (TC-076).* `git diff main...HEAD --stat -- hooks skills .claude-plugin .github scripts tests` lists no change under `hooks/`, `skills/`, `.claude-plugin/`, `.github/`; under `scripts/` only `on_site.sh` (the three forward options) and `nf_relay.py` (the loopback rule); under `tests/` only `no_second_run_state_test.sh` and `platform_test.sh` (the second pinned Nextflow).
8. *The relay question and the constitution (TC-077).* `git diff main...HEAD -- .specify/memory/constitution.md` is empty. The pull request description asks the maintainer, as a separate question, whether the relay may reach one loopback destination, and attaches the comparison with main (the 30-request golden file `platform/tests/fixtures/relay_golden.json`).

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

Needs `abf-platform web` on loopback, a data folder with e2e runs of the four statuses (running, succeeded, failed, lost; `platform/tests/e2e_harness.py` or a copy of a real index), two users with web passwords (`abf-platform user passwd <name>`), and a run each launched by those users.

**Visual check (TC-V01 to TC-V05).**

1. Log in as the first user and open `/`. Take a screenshot (TC-V01). Pass: three columns; left "我的 run" newest first; right "本月費用" with "SU —" and "雲端 —" on two lines, then five groups.
2. Click a succeeded run and take a screenshot (TC-V02). Pass: the stage strip stands on results; status, times and a progress bar show.
3. Click a failed run and take a screenshot (TC-V03). Pass: the failed state and the failure reason in Nextflow's words.
4. Turn the screenshot of step 1 black and white (TC-V04). Pass: the four states still differ by symbol and text (▶ ✓ ✗ ⏸).
5. Make the window narrower than 900 px and take a screenshot (TC-V05). Pass: the panes stack and nothing is cut off.
6. Log in as the second user. Pass: none of the first user's runs appear, and opening `/?run=<their run id>` gives the same 404 page as a made-up id.

**Ledger review (TC-D01 to TC-D09, TC-N07, TC-K5).** Read `specs/011a-web-shell/ledger.md` and `git diff v3...HEAD`. Pass: every rewritten pin has an old value, a new value and a reason (TC-G04 six routes; the "已登入 … 請回到 AI" page replaced by the redirect to `/`; CSP and `PLATFORM.md` wording); no other test was deleted, skipped or loosened; `docs/PLATFORM.md` names six routes; the CHANGELOG has a 011a line; `web.py`'s header describes `GET /`; nothing under `hooks/`, `.claude/`, `actions/`, `jobs.py`, `mcp_server.py` or `store.py` changed.

## Owner binding (116): the reviewer checks the rewritten pins

This one is read, not run. Open `specs/116-owner-binding/ledger.md` next to the diff of `platform/tests/`. Pass: every existing test that was changed is listed there with the old expectation, the new one and the reason; no assertion was deleted, skipped or loosened (a changed expectation must say what the new rule makes true instead); and `git diff <base> -- platform/tests` shows no test removed. Then, with two real users, check once by hand that one cannot see the other's environment, agent, run or upload folder over MCP and over the page.

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

## When something is red

Fix the code, not the test — unless the test encodes a rule that changed, in
which case change the rule's statement in `docs/PRINCIPLES.md` first and the
test second, so the reason survives.

New assertions get a mutation test: remove the thing being checked and confirm
the test turns red. An assertion that has never failed has never been shown to
assert anything.
