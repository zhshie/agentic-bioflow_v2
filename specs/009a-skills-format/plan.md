# Plan 009a: the five command files become Agent Skills (move only, content unchanged)

- **Slug**: 009a-skills-format
- **Branch**: `feat/009a-skills-format`, base **`v3`** (never `main`: `main` is the v2 line, ADR 0006)
- **Created**: 2026-10-15 by the developer-agent; queued in the maintainer-authorized dev loop (2026-10-14), restarted after his 2026-10-16 instruction 整理一下後再開始.
- **Umbrella**: GitHub issue #93, step 3. Decision record: `docs/adr/0006-four-entries-one-action-layer.md` (merged to main 2026-10-15 and brought into v3).
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
- 34 test files reference `commands/` (33 under `tests/`, 1 under `platform/tests/`). `tests/run_all.sh` discovers tests by glob, no fixed count.
- `tests/lib/` exists (`nojq_path.sh`, `nowsl_path.sh`, `site_terms.sh`).
- `tests/skill_portability_test.sh` checks only `skills/operational/SKILL.md` and pins the heading `## On a host without these hooks` and the tier `H3`.
- `tests/works_without_host_test.sh:90` greps `commands skills docs …`; `:94` requires `commands/setup.md commands/launch.md commands/runs.md`; the reduced tree is built with `tar -c scripts docs commands skills README.md CLAUDE.md`.
- `tests/no_hardcoded_paths.sh:35` scans `$ROOT/commands` among others.
- `tests/skill_names_command_file_test.sh:26-27` pins `commands/<command>.md` and `${CLAUDE_PLUGIN_ROOT}/commands/<command>.md` inside `skills/operational/SKILL.md`; `:36` requires `commands/$c.md`.
- No hook reads `commands/` by path. `hooks/hooks.json` has no reference.
- Docs with current-layout `commands/` paths: `CLAUDE.md:26,113-114,163`, `docs/TESTING.md:136,161,177,193`, `docs/PRINCIPLES.md:151,181,267`, `docs/SETTINGS.md:127,292`, `docs/SITE_ADAPTER.md:87`, `docs/DOWNSTREAM.md:3`, `docs/FINISH.md:3`, `docs/LAB_AGENTS.md:223`. `docs/PITFALLS.md` and `specs/*` are history and stay. `.specify/memory/constitution.md:209` is NOT edited.

## Design decisions (developer-agent)

1. Target: `skills/{setup,launch,runs,downstream,finish}/SKILL.md`. Frontmatter = `name: <dir>` + existing `description` verbatim + existing `argument-hint` / `model` kept. Body byte-for-byte. `git diff -M` shows five renames ≥ 95% similar.
2. `commands/` deleted in the same PR (no duplicate slash commands).
3. New `tests/lib/flow_skills.sh`: `FLOW_SKILLS="setup launch runs downstream finish"`, `flow_skill_file <name>`, `flow_skill_files`. Tests that read `commands/*.md` source it; comment/echo-only mentions get text updates only.
4. `skills/operational/SKILL.md`: only path pointers change. Heading `## On a host without these hooks` and H1–H3 stay (step 7).
5. `tests/skill_portability_test.sh` widened to all six SKILL.md (name `^[a-z0-9-]+$`, description ≤ 1024 chars, frontmatter `key: value`, every `${CLAUDE_PLUGIN_ROOT}` paragraph also says "otherwise"); operational-only assertions stay scoped.
6. New `tests/flow_skills_layout_test.sh`: (a) five SKILL.md exist, non-empty; (b) `name:` = dir; (c) `description:` present; (d) no `commands/`; (e) operational names the five new paths; (f) stale-path guard over `tests/`, `docs/` (except PITFALLS), `CLAUDE.md`, `README.md`, `hooks/`, `skills/`. Red before, green after.
7. `claude plugin validate .` passes; output in the ledger.
8. `platform/tests/test_scope.py:65` keeps `commands/` in its regex; note in ledger.
9. `marketplace.json`: "Five commands:" → "Five skills (slash commands in Claude Code):".
10. CHANGELOG.md Unreleased: "commands/*.md moved to skills/<name>/SKILL.md (Agent Skills format); invocation names unchanged."

## Changes, in order (red first)

1. Write the new test + helper; run → FAIL (ledger).
2. `git mv` the five; add `name:`; record `git diff -M --stat`.
3. operational path pointers.
4. Tests that read the files (locate by content; line numbers from main 2026-10-15): column_output_relay_rule, commands_resolve_their_own_paths, commands_scope_tw_to_the_workspace, command_layer_is_record_neutral, command_layer_is_site_neutral (fixture strings stay), egress_allow_test, launch_provenance_test, no_hardcoded_paths, no_per_pipeline_config, no_second_run_state_test (fixtures stay), off_design_single_path, package_gaps_test, principle_9_test, runs_report_format_test, setup_doc_test, skill_names_command_file_test, skill_requires_intro_test, works_without_host_test (+ tar list), skill_portability_test, scripts_name_their_alternative (drop `*commands/*`). Leave `confirm_launch_test.sh:74` (gate fixture).
5. Comment/echo-only test text.
6. Docs → new paths; `CLAUDE.md:26` layout line names the five flow skills.
7. marketplace description; CHANGELOG line.
8. `claude plugin validate .`; WSL `bash tests/run_all.sh` green; ledger.

## Not in this PR

No change to skill instructions, `hooks/`, `scripts/`, `platform/`, `.github/`, plugin.json version, constitution. No Codex/Desktop packaging, no `.mcp.json`, no INSTALL.md, no H1–H3 rewording (step 7). No tw-era retirement (step 6).

## Constitution Check

II.5 (4.1.0): judgment lives in `skills/`, `docs/`, `scripts/` — this PR makes it literal; `tests/works_without_host_test.sh` still packs `skills/`. Safety Net untouched.
