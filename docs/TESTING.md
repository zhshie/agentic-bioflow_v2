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

Record the answers in the release's own notes. A check nobody wrote down is a
check that gets re-argued three sessions later.

## Half 3 — procedures the constitution cites

Two of the constitution's rules cannot be checked by a machine, because what
they ask is whether a person got stuck and whether a claim rests on evidence.
Each has a procedure here, and the constitution's *Check:* line names it. A
procedure is done when its record is written down in the release notes; "I
looked and it seemed fine" is not a record.

`tests/constitution_checks_exist_test.sh` holds the pointers: it fails if the
constitution cites a Procedure whose heading is not in this file.

### Procedure P1: onboarding without the maintainer (Constitution III.7)

When: every release that touches `commands/setup.md`, `commands/launch.md`,
`skills/`, or anything a first-time user is shown. Once a quarter otherwise.

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

## When something is red

Fix the code, not the test — unless the test encodes a rule that changed, in
which case change the rule's statement in `docs/PRINCIPLES.md` first and the
test second, so the reason survives.

New assertions get a mutation test: remove the thing being checked and confirm
the test turns red. An assertion that has never failed has never been shown to
assert anything.
