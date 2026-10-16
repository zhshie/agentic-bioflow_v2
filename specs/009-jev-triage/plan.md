# Implementation Plan: Jev triage for FAILED runs

**Branch**: `009-jev-triage` | **Date**: 2026-10-16 | **Spec**: `specs/009-jev-triage/spec.md`

## Summary

One new script, `scripts/jev.sh`, is the only place that talks to Jev. `commands/runs.md` calls it once in the FAILED flow, after the egress, 137 and no-log rules and before the free-form "Anything else" branch. Off by default; fail-open with a printed line; offline tests through `JEV_DRY_RUN` fixtures.

## Technical Context

- **Language**: bash (same as the rest of `scripts/`), `curl` + `jq`.
- **API**: `POST ${JEV_ENDPOINT:-https://api.typesafe.ai/v1/systemone}`, `Authorization: Bearer <key>`, body `{"model":"jev-latest","state":{...},"questions":{"category":{"type":"choice","instructions":...,"criteria":{<8 keys>: <one-line description>}}}}`. Response `answers.category.{choice,probabilities,confidence}`〔docs.typesafe.ai/api〕.
- **State sent**: `{"exit_code": <n>, "err_tail": <last 200 lines of .command.err, valid UTF-8>}`. Nothing else.
- **Timeout**: `curl --max-time 10`; 429/529 → backoff 1 s, 3 s (2 retries); anything else non-2xx → fail-open.
- **Settings** (read the way `scripts/settings.sh` reads its other keys):
  - `jev.enabled` (default `false`)
  - `jev.daily_cap` (default `500`)
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
- **II-5**: invocation is a script call written in `commands/runs.md`, not prose asking the host LLM to call an API.
- **VI-13**: every failure path prints a line; never silently permissive.
- **Safety Net, credentials rule**: key only in env or settings area; extend `tests/credentials_stay_in_settings_test.sh` (static "never printed" scan covers `TYPESAFE_API_KEY`; `.gitignore` names `.typesafe_key`).
- **Users decide**: Jev changes no ⏸ step; `commands/runs.md` says so in the new step.
- No amendment needed (no explainability clause exists).

## Project Structure

```
specs/009-jev-triage/      spec.md  plan.md  tasks.md  labels.json  test-case*.md  replay-report.md (later)
scripts/jev.sh             new
scripts/settings.sh        + jev_key_file(), jev.* keys
scripts/dev/jev_replay.sh  new, manual acceptance (real key), not in run_all
commands/runs.md           FAILED: new step + 7 short category routes (memory route = existing "Out of memory")
skills/operational/SKILL.md  check order line
docs/adr/0007-jev-optional-triage.md   new
docs/POSITIONING.md        line 91
docs/SETTINGS.md           Jev section (keys, what is sent, cap, endpoint, off switch)
docs/TESTING.md            manual half: on/off failed-run walkthrough
docs/PITFALLS.md           entry if anything surprising is measured
.gitignore                 .typesafe_key
.claude-plugin/plugin.json minor bump
tests/jev_test.sh          new (fixtures)
tests/fixtures/jev/        new
tests/credentials_stay_in_settings_test.sh  extended
tests/run_all.sh           picks up jev_test.sh (count comment is no longer hard-coded since #88)
```

## Complexity Tracking

None. One script, one call site.
