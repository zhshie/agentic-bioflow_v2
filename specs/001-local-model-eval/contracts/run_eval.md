# Contract: `scripts/eval/run_eval.py`

## Invocation

```text
run_eval.py --candidate <candidate.json> [--task <id> ...] [--trials N] [--results DIR]
run_eval.py --scorecard [--results DIR]
run_eval.py --publish <out.md> [--results DIR]
```

- `--trials` default 20. `--results` default `$ABF_EVAL_RESULTS`, else `$HOME/abf-eval-results`.
- Exit codes: `0` finished (thresholds met or not — the scorecard says which); `2` preflight
  refused (nothing ran); `3` aborted after 5 consecutive engine failures; `1` internal error.
- Every refusal prints one line naming the missing thing and one line naming the fix.

## Runner seam

The driver calls, once per trial:

```text
$ABF_EVAL_RUNNER <plugin-root> --eval-dir evals --case <task-id> --runs 1 --ablation none \
    --keep-temp --json <out.json> --no-publish [--model <m>]
```

Default `ABF_EVAL_RUNNER` is `claude plugin eval`. The environment carries the candidate's
`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, and
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` for local candidates. A replacement runner (fake in
tests, `claude -p` fallback) must write `<out.json>` with, per run: `result` text, `is_error`,
`duration_ms`, `usage.input_tokens`, `usage.output_tokens`, the kept work directory, and the
transcript path. The driver reads only those fields.

## Answer formats the model is told to write (FR-004)

| Task | Files |
|---|---|
| ①② | `samplesheet.csv`, `params.json` |
| ③ | `diagnosis.json` = `{"cause_id": "<id from causes.json>", "fix_actions": ["<id>", ...]}` |
| ④ | `numbers.json` = `{"<key>": <number>, ...}` with the keys named in the prompt |
| ⑤ | `methods.md` with DOIs written as `doi:10.xxxx/...` |
