# Testing a release

Two halves, and the split matters more than either half: one is machine-checked
and cheap, the other needs a human in a live Claude Code session and is the only
place several classes of defect can show up at all.

## Half 1 — what the machine checks

```bash
bash tests/run_all.sh
```

40 files, about 80 seconds, one verdict and a non-zero exit if anything fails.
Failing output is printed at the end; full logs land in a temp directory the
banner names. `--only <substring>` narrows it, `--verbose` streams each file's
own output, `--timeout <secs>` changes the per-test limit (default 300, only
there to catch a hang).

Nothing in it touches the network, the cluster, or a real settings file — the
tests that exercise ssh run under `ON_SITE_DRY_RUN`. So it is safe to run any
time, on any machine, including a laptop with no cluster access.

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

`run_all.sh` cannot see a user interface, cannot judge whether guidance reads
well, and — the important one — **cannot tell whether the hooks are loaded**.
Hooks are read at Claude Code startup. Every test here can be green while the
running session still has the previous version's hooks in memory, which is the
one failure that looks exactly like success.

After deploying, **restart Claude Code**, then walk this list. It takes a few
minutes and is the whole point of having a human in the loop.

| # | Check | What wrong looks like |
|---|---|---|
| 1 | A new session opens with **no** overview; the first `/agentic-bioflow:` command (or a request that loads the plugin) shows it once; a second command in the same session does not | Overview at session start → the old hook is still loaded. Nothing on first use → `systemMessage` is not rendered for UserPromptSubmit/PostToolUse on this surface. Shown every time → the per-session marker is not being written |
| 2 | Type one command, e.g. `/agentic-bioflow:setup` | No opening five-part block → the per-command intro is not firing |
| 3 | Ask for something destructive that should be confirmed | It proceeds without a confirmation → a gate is missing or its hook did not load |
| 4 | Finish a reply inside a command flow | No "下一步" line → the Stop hook is not loaded. Too many nags → it is scoped wrongly |
| 5 | `bash scripts/status.sh` against the real cluster | Every dry-run test passes with a stubbed site; this is the only check against the real one |
| 6 | Whatever this release specifically changed | — |

Record the answers in the release's own notes. A check nobody wrote down is a
check that gets re-argued three sessions later.

## When something is red

Fix the code, not the test — unless the test encodes a rule that changed, in
which case change the rule's statement in `docs/PRINCIPLES.md` first and the
test second, so the reason survives.

New assertions get a mutation test: remove the thing being checked and confirm
the test turns red. An assertion that has never failed has never been shown to
assert anything.
