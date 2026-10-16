# Plan 015: Jev triage for FAILED runs, moved onto the v3 line

- **Slug**: 015-jev-triage (was `009-jev-triage`, drafted on the laptop 2026-10-16, branch `origin/009-jev-triage`, commits 921ff16 + 8cc308f)
- **Branch**: `feat/015-jev-triage`, base **`v3`**, started only after 009a is merged into `v3` (it edits the runs skill that 009a moves).
- **Tier**: A (only adds a spec: an opt-in, off-by-default step); the maintainer asked to see nothing extra beyond the replay report, which he runs himself.

## 給維護者

1. 內容就是你 10-16 在筆電核可的「Jev 失敗分診」：只做除錯、預設關、自備金鑰、外送揭露、42 題題庫、≥90% 才寫建議開啟。一個字都沒改你的決定。
2. 改的只有位置：你 10-16 選「放 v3」，所以做在 `v3`、改的是 009a 搬家後的 `skills/runs/SKILL.md`，不再發 2.18。
3. 編號從 009 改成 015：roadmap 的 009 是「動作層」，兩個 009 會混淆。

## Carry over (do not rewrite)

`git checkout origin/009-jev-triage -- specs/009-jev-triage` then `git mv specs/009-jev-triage specs/015-jev-triage`. Keep spec.md, plan.md, tasks.md, labels.json (42 items, maintainer-approved 2026-10-16: do not edit a label), test-case*.md (draft; the verifier re-confirms the contract).

## Edits to the carried-over documents (developer-agent decisions)

1. Every path: `specs/009-jev-triage` -> `specs/015-jev-triage`; `commands/runs.md` -> `skills/runs/SKILL.md` (FR-001, plan Project Structure, tasks T008, test-case FAILED-flow definition).
2. FR-011 / T013: no `.claude-plugin/plugin.json` bump (v3 stays `3.0.0-dev`); instead one line in `CHANGELOG.md` under Unreleased.
3. ADR number stays `docs/adr/0007-jev-optional-triage.md` (0006 is taken by the four-entries ADR; 0007 is free).
4. Verifier blocker 1 (SC-002 read-size comparison): `scripts/dev/jev_replay.sh` also reports, per scored item, the characters the AI would read with Jev high-confidence (last 200 lines) vs without (whole `.command.err` in the fixture); the report table carries both columns and the total.
5. Verifier blocker 2 (disabled output): the machine line `JEV status=disabled ...` IS printed on stdout for the skill to parse, and the skill text never shows it to the user; SC-003 "byte-identical" applies to what the user sees (the skill's user-facing report), not to the script's stdout. Spec US2-1 is reworded to say exactly this.
6. Verifier blocker 3: `jev_replay.sh` runs under `JEV_DRY_RUN` too (fixtures per label id), so US4 scenario 3 (< 90% -> no "建議開啟") is tested offline in `tests/jev_test.sh`; the real-key run stays manual.
7. Open questions of the draft, decided: (a) no exit code (T11) -> `--exit none`, sent as `"exit_code": null`; (b) `docs/SETTINGS.md` gives the creation command `umask 077; printf '%s' "$KEY" > <settings dir>/.typesafe_key` and the test checks the file mode is 600 when the script creates nothing itself (the script refuses a group/world-readable key file with a printed line, fail-open); (c) `jev.min_confidence` is added to the spec as FR-012; (d) retries after 429 count once per triage call, not per HTTP request; (e) the Authorization header goes to curl through `--config -` on stdin (`header = "Authorization: Bearer ..."`), never on the command line.
8. Architecture note for the spec (ADR 0006): this is a step inside the runs skill backed by one script. When step 6 of issue #93 rewrites the runs skill to call platform actions, the Jev step stays a script call in the skill; it is not an MCP tool and not part of the action layer (it changes no state and needs no gate). Say so in plan.md Constitution Check.

## Order

Red first per tasks.md (T001-T014, paths updated). WSL `bash tests/run_all.sh` green; `claude plugin validate .`.

## Not in this PR

Everything in the spec's Out of Scope; the old branch `origin/009-jev-triage` is left as it is (deleting a branch asks the maintainer first).
