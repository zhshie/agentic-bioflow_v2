# Plan 015: Jev triage for FAILED runs, moved onto the v3 line

- **Slug**: 015-jev-triage (was `009-jev-triage`, drafted on the laptop 2026-10-16, branch `origin/009-jev-triage`, commits 921ff16 + 8cc308f)
- **Branch**: `feat/015-jev-triage`, base **`v3`**, started only after 009a is merged into `v3` (it edits the runs skill that 009a moves).
- **Tier**: A (only adds a spec: an opt-in, off-by-default step); the maintainer asked to see nothing extra beyond the replay report, which he runs himself.

## 給維護者

1. 內容就是你 10-16 在筆電核可的「Jev 失敗分診」：只做除錯、預設關、自備金鑰、外送揭露、42 題題庫、≥90% 才寫建議開啟。一個字都沒改你的決定。
2. 改的只有位置：你 10-16 選「放 v3」，所以做在 `v3`、改的是 009a 搬家後的 `skills/runs/SKILL.md`，不再發 2.18。
3. 編號從 009 改成 015：roadmap 的 009 是「動作層」，兩個 009 會混淆。

## Carry over (do not rewrite)

The spec folder was carried over from the draft branch and renamed to this slug; spec.md, plan.md, tasks.md, labels.json (42 items, maintainer-approved 2026-10-16: do not edit a label) are kept, test-case*.md are replaced by the verifier contract.

## Edits to the carried-over documents (developer-agent decisions)

1. Every path uses the new slug; the old command file reference became `skills/runs/SKILL.md` (FR-001, plan Project Structure, tasks T008, test-case FAILED-flow definition).
2. FR-011 / T013: no `.claude-plugin/plugin.json` bump (v3 stays `3.0.0-dev`); instead one line in `CHANGELOG.md` under the 3.0.0-dev section.
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


---

# Carried-over technical plan (originally 009-jev-triage)

# Implementation Plan: Jev triage for FAILED runs

**Branch**: `feat/015-jev-triage` (was `009-jev-triage`) | **Date**: 2026-10-16 | **Spec**: `specs/015-jev-triage/spec.md`

## Summary

One new script, `scripts/jev.sh`, is the only place that talks to Jev. `skills/runs/SKILL.md` calls it once in the FAILED flow, after the egress, 137 and no-log rules and before the free-form "Anything else" branch. Off by default; fail-open with a printed line; offline tests through `JEV_DRY_RUN` fixtures.

## Technical Context

- **Language**: bash (same as the rest of `scripts/`), `curl` + `jq`.
- **API**: `POST ${JEV_ENDPOINT:-https://api.typesafe.ai/v1/systemone}`, `Authorization: Bearer <key>`, body `{"model":"jev-latest","state":{...},"questions":{"category":{"type":"choice","instructions":...,"criteria":{<8 keys>: <one-line description>}}}}`. Response `answers.category.{choice,probabilities,confidence}`〔docs.typesafe.ai/api〕.
- **State sent**: `{"exit_code": <n>, "err_tail": <last 200 lines of .command.err, valid UTF-8>}`. Nothing else.
- **Timeout**: `curl --max-time 10`; 429/529 → backoff 1 s, 3 s (2 retries); anything else non-2xx → fail-open.
- **Settings** (read the way `scripts/settings.sh` reads its other keys):
  - `jev.enabled` (default `false`)
  - `jev.daily_cap` (default `500`)
  - `jev.min_confidence` (default `0.80`)
  - key: `TYPESAFE_API_KEY` env first; else a file next to the settings file, `.typesafe_key`, by the same path rule as `token_file()` (`scripts/settings.sh:401-404`). Add a `jev_key_file()` beside `token_file()`; never echo it.
- **Daily counter**: `${XDG_STATE_HOME:-$HOME/.local/state}/agentic-bioflow/jev-count-<YYYY-MM-DD>`; one integer; old days' files removed on write. Not run state.
- **First-use notice**: marker file in the same state dir; printed once per machine.
- **Dry run**: `JEV_DRY_RUN=<dir>` → no network; response read from `<dir>/<sha256 of err_tail>.json` if present, else `<dir>/default.json`; special fixture names `__timeout__`, `__500__`, `__429_then_ok__` simulate failures.

### Output contract of `scripts/jev.sh triage --err <file> --exit <code>`

Always exit 0. Line 1 machine-readable, line 2 for the person:

```
JEV status=<ok|disabled|no_key|failed|capped|empty> category=<key|-> confidence=<0.00|-> sent_chars=<n>
<one zh-TW/English sentence: e.g. "Jev 判斷：container（信心 0.93）" / "Jev 未回應，改用原流程（原因：timeout）">
```

`disabled` prints nothing on line 2 (so the off path adds no visible text).

### Confidence threshold

`jev.min_confidence` (default `0.80`); the replay report recommends the final value. Below it, or `unknown`, → original flow.

## Constitution Check

- **I-1**: header `# Nothing existing: no maintained tool classifies a Nextflow task's stderr into fix routes; this is the thin client for one API call.` — `tests/scripts_name_their_alternative.sh`.
- **I-2**: counter and marker are not run state — `tests/no_second_run_state_test.sh` must stay green; add the paths to its allow-list with a reason only if the scan hits.
- **II-3**: no personal/cluster paths; endpoint overridable.
- **II-5**: invocation is a script call written in `skills/runs/SKILL.md`, not prose asking the host LLM to call an API.
- **VI-13**: every failure path prints a line; never silently permissive.
- **Safety Net, credentials rule**: key only in env or settings area; extend `tests/credentials_stay_in_settings_test.sh` (static "never printed" scan covers `TYPESAFE_API_KEY`; `.gitignore` names `.typesafe_key`).
- **Users decide**: Jev changes no ⏸ step; `skills/runs/SKILL.md` says so in the new step.
- **Architecture (ADR 0006)**: Jev is one step inside the runs skill, backed by one script. When step 6 of issue #93 rewrites the runs skill to call platform actions, the Jev step stays a script call in the skill; it is not an MCP tool and not part of the action layer (it changes no state and needs no gate).
- No amendment needed (no explainability clause exists).

## Project Structure

```
specs/015-jev-triage/      spec.md  plan.md  tasks.md  labels.json  test-case*.md  replay-report.md (later)
scripts/jev.sh             new
scripts/settings.sh        + jev_key_file(), jev.* keys
scripts/dev/jev_replay.sh  new, manual acceptance (real key), not in run_all
skills/runs/SKILL.md           FAILED: new step + 7 short category routes (memory route = existing "Out of memory")
skills/operational/SKILL.md  check order line
docs/adr/0007-jev-optional-triage.md   new
docs/POSITIONING.md        line 91
docs/SETTINGS.md           Jev section (keys, what is sent, cap, endpoint, off switch)
docs/TESTING.md            manual half: on/off failed-run walkthrough
docs/PITFALLS.md           entry if anything surprising is measured
.gitignore                 .typesafe_key
CHANGELOG.md (one line; plugin.json unchanged)
tests/jev_test.sh          new (fixtures)
tests/fixtures/jev/        new
tests/credentials_stay_in_settings_test.sh  extended
tests/run_all.sh           picks up jev_test.sh (count comment is no longer hard-coded since #88)
```

## Complexity Tracking

None. One script, one call site.
