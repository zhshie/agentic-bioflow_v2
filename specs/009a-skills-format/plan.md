# Plan 009a: the five command files become Agent Skills (move only, content unchanged)

- **Slug**: 009a-skills-format
- **Branch**: `feat/009a-skills-format`, base **`v3`** (never `main`: `main` is the v2 line, ADR 0006)
- **Created**: 2026-10-15 by the developer-agent
- **Umbrella**: GitHub issue #93, step 3. Decision record: `docs/adr/0006-four-entries-one-action-layer.md` (on `main` once the 4.1.0 PR merges; also readable in the v3 branch after that merge is brought in).
- **Tier**: B for the merge decision (the maintainer wants to see the PR before it lands); the work itself is mechanical.

## 給維護者

1. 這一步只搬家、不改內容：五個指令檔 `commands/setup|launch|runs|downstream|finish.md` 各自搬成 `skills/<名字>/SKILL.md`，這是 Agent Skills 開放格式（一個資料夾＋一個 `SKILL.md`），Claude Code、Codex、Claude Desktop 之外的工具都讀得懂。
2. 在 Claude Code 裡你打 `/agentic-bioflow:launch` 的用法和看到的流程完全一樣；只是檔案換了位置。
3. 做在 `v3` 分支，`main`（v2，實驗室正在用的 2.17.0）一個字不動。
4. 不在這一步做的：skill 內文改成呼叫平台動作（那是第 6 步，每個 skill 一支 PR）、Codex／Desktop 安裝包（第 7 步）。

## 維護者的例子（原文，2026-10-15）

- 「指令檔改成 skill」
- 「只加 MCP 網址就能用」（這一步只是前置：先把引導文字放進跨工具都讀得到的格式）
- 「v2 凍結、v3 平台世代」→ 本 PR base 是 `v3`

## Facts (gathered 2026-10-15, read-only, from `main`)

- `commands/` has exactly five files (343–641 lines each); none has a `name:` key; `finish.md` has `model: sonnet`; four have `argument-hint`. Every body opens with the same "Paths below such as `scripts/...`" paragraph.
- `skills/` has only `operational/SKILL.md` (`name: agentic-bioflow-operational`). No name clash with the five.
- `.claude-plugin/plugin.json` and `marketplace.json` list no `commands`/`skills` paths (default discovery). `marketplace.json` description says "Five commands: …".
- 34 test files reference `commands/` (33 under `tests/`, 1 under `platform/tests/`); the ones that actually read the files (not comments) are listed under "Tests" below. `tests/run_all.sh` discovers tests by glob, no fixed count.
- `tests/lib/` exists (`nojq_path.sh`, `nowsl_path.sh`, `site_terms.sh`).
- `tests/skill_portability_test.sh` checks only `skills/operational/SKILL.md` and pins the heading `## On a host without these hooks` and the tier `H3`.
- `tests/works_without_host_test.sh:90` greps `commands skills docs …`; `:94` requires `commands/setup.md commands/launch.md commands/runs.md`; the reduced tree is built with `tar -c scripts docs commands skills README.md CLAUDE.md`.
- `tests/no_hardcoded_paths.sh:35` scans `$ROOT/commands` among others (a missing directory makes `grep -r` complain).
- `tests/skill_names_command_file_test.sh:26-27` pins the literal `commands/<command>.md` and `${CLAUDE_PLUGIN_ROOT}/commands/<command>.md` inside `skills/operational/SKILL.md`; `:36` requires `commands/$c.md` for the five names.
- No hook reads `commands/` by path (comments only). `hooks/hooks.json` has no reference.
- Docs that describe the *current* layout with `commands/` paths: `CLAUDE.md:26,113-114,163`, `docs/TESTING.md:136,161,177,193`, `docs/PRINCIPLES.md:151,181,267`, `docs/SETTINGS.md:127,292`, `docs/SITE_ADAPTER.md:87`, `docs/DOWNSTREAM.md:3`, `docs/FINISH.md:3`, `docs/LAB_AGENTS.md:223`. `docs/PITFALLS.md` (11 hits) and `specs/*` are history and stay as they are. `.specify/memory/constitution.md:209` mentions `commands/` in the manual-walkthrough rule: the constitution is NOT edited in this PR.

## Design decisions (developer-agent; the maintainer does not need to judge these)

1. **Target layout**: `skills/setup/SKILL.md`, `skills/launch/SKILL.md`, `skills/runs/SKILL.md`, `skills/downstream/SKILL.md`, `skills/finish/SKILL.md`. Frontmatter = `name: <directory name>` + the existing `description` verbatim + the existing `argument-hint` / `model` keys kept as they are (Claude Code honours them in skills; other hosts ignore unknown keys). The body is byte-for-byte the old body. `git diff -M` on the PR must show five renames with similarity ≥ 95%.
2. **`commands/` is deleted** in the same PR. Keeping both would register two `/agentic-bioflow:launch` entries in Claude Code.
3. **One path helper, not 33 edits of the same string**: new `tests/lib/flow_skills.sh` exporting `FLOW_SKILLS="setup launch runs downstream finish"` and `flow_skill_file <name>` → `$ROOT/skills/<name>/SKILL.md`, plus `flow_skill_files` (the five paths in that order). Every test that iterated `commands/*.md` or named `commands/<name>.md` sources the helper. Tests that only mention `commands/` in comments or `echo` text get the text updated (so nobody greps a stale path later) but no logic change.
4. **`skills/operational/SKILL.md`** changes only its *path pointers*: `commands/<command>.md` → `skills/<command>/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/commands/<command>.md` → `${CLAUDE_PLUGIN_ROOT}/skills/<command>/SKILL.md`. Its heading `## On a host without these hooks` and the H1–H3 text stay (they are rewritten in step 7 together with `docs/LAB_AGENTS.md`; the umbrella plan's earlier note that 009a rewords them is superseded: 009a is content-neutral).
5. **`tests/skill_portability_test.sh`** is widened to run its frontmatter/shape checks over all six `skills/*/SKILL.md` (name matches `^[a-z0-9-]+$`, description ≤ 1024 chars, frontmatter lines are `key: value`, every `${CLAUDE_PLUGIN_ROOT}` paragraph also says "otherwise"). The two operational-only assertions (heading, H3, LAB_AGENTS) stay scoped to operational.
6. **New test `tests/flow_skills_layout_test.sh`**: (a) each of the five `skills/<name>/SKILL.md` exists and is non-empty; (b) frontmatter `name:` equals the directory name; (c) `description:` present; (d) `commands/` does not exist; (e) `skills/operational/SKILL.md` names each of the five by its new path; (f) no file under `tests/`, `docs/` (except `docs/PITFALLS.md`), `CLAUDE.md`, `README.md`, `hooks/`, `skills/` contains the literal `commands/` followed by one of the five names + `.md` (stale-path guard). Red before the move (a–e fail), green after.
7. **`claude plugin validate .`** must pass; the executor records the output in the ledger.
8. `platform/tests/test_scope.py:65` keeps `commands/` in its regex (harmless; it classifies paths, and removing it is not needed). Say so in the ledger.
9. `marketplace.json` description: "Five commands:" → "Five skills (slash commands in Claude Code):"; the rest of the sentence unchanged.
10. CHANGELOG.md (exists on `v3`) gets one line under Unreleased: "commands/*.md moved to skills/<name>/SKILL.md (Agent Skills format); invocation names unchanged."

## Changes, in order (red first)

1. Write `tests/flow_skills_layout_test.sh` and `tests/lib/flow_skills.sh`; run the new test → FAIL (record in ledger).
2. `git mv commands/<n>.md skills/<n>/SKILL.md` for the five; add `name: <n>` as the first frontmatter key; nothing else in the file changes. `git diff -M --stat` recorded in the ledger.
3. Update `skills/operational/SKILL.md` path pointers (decision 4).
4. Tests, logic lines (source the helper or change the path):
   `column_output_relay_rule.sh:22`, `commands_resolve_their_own_paths.sh:19`, `commands_scope_tw_to_the_workspace.sh:23`, `command_layer_is_record_neutral.sh:27-28,45`, `command_layer_is_site_neutral.sh:33,83,104` (and the synthetic fixture strings at 46-53 stay as they are: they are test inputs), `egress_allow_test.sh:192,198`, `launch_provenance_test.sh:14`, `no_hardcoded_paths.sh:35,59`, `no_per_pipeline_config.sh:42,83,86,89`, `no_second_run_state_test.sh:193,218` (the `commands/a.md` fixture strings at 250-251 stay), `off_design_single_path.sh:62,69-71,78-80`, `package_gaps_test.sh:350`, `principle_9_test.sh:36,38`, `runs_report_format_test.sh:18`, `setup_doc_test.sh:14`, `skill_names_command_file_test.sh:26,27,36`, `skill_requires_intro_test.sh:34`, `works_without_host_test.sh:90,94` and its `tar -c` list, `skill_portability_test.sh` (decision 5), `scripts_name_their_alternative.sh:83` (add `*skills/*` is already there; drop `*commands/*`). `confirm_launch_test.sh:74` is a shell-command fixture string (`grep … commands/*.md`) fed to the gate: leave it, it tests the gate, not the layout.
5. Tests, comment/echo-only lines: update the text in the files listed in the facts report (build_package_test, collect_provenance_test, confirm_walkthrough_test, on_site_*, positron_run_test, prepare_launch_test, settings_test, site_report_test, where_test, principle_12_test, site_scripts_via_on_site, intro_test is prose "five commands" — leave).
6. Docs with current-layout paths (facts list) → new paths. `docs/TESTING.md:136,161,177`: the `git diff -- … commands/ …` assertions become `skills/`. `docs/TESTING.md:193` names the five new paths. `CLAUDE.md:26` layout line: "`skills/` — the five flow skills (`setup`, `launch`, `runs`, `downstream`, `finish`, each a `SKILL.md` in Agent Skills format, exposed as slash commands in Claude Code) and `operational`".
7. `marketplace.json` description (decision 9); `CHANGELOG.md` line (decision 10).
8. `claude plugin validate .`; WSL full suite `bash tests/run_all.sh` green; ledger updated with the red/green evidence and the `git diff -M --stat`.

## Not in this PR (不在範圍)

- No change to any skill's instructions (judgment text), to `hooks/`, `scripts/`, `platform/`, `.github/`, `.claude-plugin/plugin.json` version, or the constitution.
- No Codex `plugin.json` / `mcp.json`, no `.mcp.json`, no `docs/INSTALL.md` (step 7).
- No rewording of `## On a host without these hooks` / H1–H3 (step 7).
- No retirement of `tw`-era tests or scripts (step 6; inventory below).

## Inventory for step 6 (recorded here so the second change is planned, not improvised)

- Scripts whose content calls `tw ` (20 of 50): agent_ctl.sh, ce_apply.sh, collect_provenance.py, duplicate_run_check.sh, init_workspace.sh, inspect_sides.sh, install_deps.sh, on_site.sh, parallel_watch_check.sh, preflight.sh, prepare_launch.sh, relaunch_with_override.sh, require_python.sh, runs_board.sh, runs_board_site_probe.sh, settings.sh, setup_proof.sh, status.sh, task_health.sh, tune_resources.sh. Step 6 assigns each to the skill that calls it (or to "shared") before any is retired; a script named by two skills is retired with the second.
- Tests that assert `tw`-era behaviour of the command layer: `commands_scope_tw_to_the_workspace.sh`, `no_second_run_state_test.sh` (the `tw <verb>` grep at :193), `launch_provenance_test.sh`, `prepare_launch_test.sh`, `egress_allow_test.sh:192-198`, `runs_report_format_test.sh`, `setup_doc_test.sh`. Each is retired or rewritten in the PR of the skill it pins, never earlier.

## Constitution Check

- II.5 (4.1.0 text): judgment lives in `skills/` and `docs/` — this PR is the move that makes it literally true. `tests/works_without_host_test.sh` still packs `skills/`.
- Safety Net: untouched (hooks unchanged; the launch gate reads the shell command, not the skill file).
- Principle 12 / site-neutral / record-neutral tests keep running over the same text at its new path.
- Governance "manual walkthrough before a release touching `commands/` or `skills/`": no release in this PR.


## Contract round 1 (verifier, 2026-10-16): decisions that override anything above

1. **Body rule**: the five bodies are unchanged **except path pointers**. Every `commands/<name>.md` (and `${CLAUDE_PLUGIN_ROOT}/commands/<name>.md`) inside the five SKILL.md bodies becomes `skills/<name>/SKILL.md` (e.g. `commands/launch.md:524` naming `commands/runs.md`). Nothing else in the bodies changes; the `git diff -M` similarity ≥ 95% still holds.
2. **scripts/ user-visible messages move too**: `scripts/init_workspace.sh:139`, `scripts/relaunch_with_override.sh:91`, `scripts/settings.sh:1005`, `scripts/setup_proof.sh:55`, `scripts/setup_verify.sh:53,61` (and any other echo/printf line in `scripts/` that names `commands/<name>.md`) are changed to the new paths (constitution III.7: a printed pointer must lead somewhere). Only those string literals change; no script logic. `scripts/` is therefore removed from "Not in this PR" for these lines. Comments in `scripts/*.sh` that mention `commands/` are updated too (text only). **`hooks/` is not touched** (protected path): the comment mentions at `hooks/plugin_intro.sh:277` and `hooks/confirm_walkthrough.sh:7` stay and are listed as exemptions in the ledger.
3. **Stale-path guard (f), exact scope**: pattern `commands/(setup|launch|runs|downstream|finish)\.md` and, in `tests/`, also `"\$ROOT/commands"` / `\$ROOT/commands\b`. Scans `tests/`, `docs/`, `scripts/`, `skills/`, `CLAUDE.md`, `README.md`. Exemptions, listed in the test itself with a one-line reason each: `docs/PITFALLS.md` and `docs/adr/` (history), `specs/` (not scanned), `hooks/` (not scanned; protected), fixture strings `tests/command_layer_is_site_neutral.sh` (the synthetic inputs, by content marker), `tests/no_second_run_state_test.sh` (the `commands/a.md` fixtures), `tests/confirm_launch_test.sh` (the gate fixture), and the guard test file itself.
4. **Add `tests/site_scripts_via_on_site.sh`** to the tests that read the files (:32 `"$ROOT/commands"`, :46, :59 messages). Every test that loops over the flow files and `continue`s on a missing file (`commands_resolve_their_own_paths.sh`, `commands_scope_tw_to_the_workspace.sh`, and any similar) must after the change assert it actually read 5 files (fail if fewer) — no silent green.
5. **docs/TESTING.md**: add a short section "When a release moves the flow files (commands → skills)" with the checks: `git diff -M --stat` shows five renames ≥ 95%; each `description:` identical to the old one; marketplace description; CHANGELOG line; PR base is `v3`; `main` untouched. The verifier judges those against this section.
