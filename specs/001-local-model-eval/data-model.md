# Data Model: 本地模型評測

Entities from `spec.md` §Key Entities, as files. All JSON (stdlib-parsable); the only YAML is
`case.yaml`, which `claude plugin eval` reads and the driver never parses.

## Task — `evals/local-model/cases/<id>/task.json`

| Field | Type | Rule |
|---|---|---|
| `id` | string | `t1-16s-setup` … `t5-methods`; equals the directory name |
| `category` | enum | `setup-16s`, `setup-rnaseq`, `diagnose`, `stats`, `methods` (FR-001) |
| `part` | enum | `setup` (①②) or `results` (③④⑤) — scorecard grouping (FR-012) |
| `answer_files` | string[] | files the model must write, e.g. `["samplesheet.csv","params.json"]` (FR-004) |
| `inputs` | object[] | `{name, url, sha256}`; `url` host must be in the public allowlist (FR-003) |
| `requires` | string[] | environment needs checked in preflight, e.g. `["R:DESeq2","R:phyloseq"]` |

## Reference — `cases/<id>/reference/`

- `answer.*`: same shape as the task's `answer_files`.
- `source.json`: `{origin: "official"|"drafted", evidence: <URL or file the official answer came
  from>, confirmed: "YYYY-MM-DD"|null}`. `drafted` with `confirmed: null` → task excluded (FR-017).
- For ③: `{cause_id, fix_actions: [...]}` using ids from `causes.json`.
- For ④: flat `{key: number}`; tolerance 1% relative is global, not per file.
- For ⑤: `{required_tools: [...]}`.

## Candidate — `evals/local-model/candidates/<name>.json`

| Field | Rule |
|---|---|
| `name` | unique; used in paths |
| `model`, `quant` | e.g. `qwen3.6:27b`, `Q4_K_M`; `null` quant for Claude |
| `engine` | `anthropic` \| `ollama` \| `llamacpp` |
| `base_url` | `null` for Claude; `http://127.0.0.1:<port>` otherwise (localhost only) |
| `context` | tokens configured on the engine (≥ 65536) |
| `mem_gb` | estimated resident size; preflight refuses if > RAM × 0.75 (TC-007) |

## Trial record — `$ABF_EVAL_RESULTS/<set-version>/<candidate>/<task>/trial-NN/record.json`

| Field | Rule |
|---|---|
| `outcome` | one of `pass`, `wrong`, `format`, `timeout`, `engine`, `context`, `forbidden` (FR-011) |
| `reason` | one sentence naming what was wrong (column, key, DOI, command…) |
| `task_set_version` | sha256; records of other versions are void (TC-027) |
| `model`, `model_version`, `engine`, `engine_version`, `claude_version` | FR-014 |
| `started`, `duration_s`, `input_tokens`, `output_tokens` | speed recorded only (TC-043) |
| `answer_sha256` | detects "20 identical outputs" (TC-015) |
| `transcript`, `answer_dir` | relative paths inside the trial dir |

State of a task within a run: `running` → `passed-threshold` (20 run, ≤2 non-pass) or
`failed-threshold` (3rd non-pass reached; remaining trials not run). Run-level: `aborted-engine`
after 5 consecutive `engine` outcomes.

## Scorecard — `$ABF_EVAL_RESULTS/<set-version>/scorecard.{md,json}`

Rows: task × candidate; columns: passes / trials, threshold met, outcome counts, median duration.
Derived only from records (TC-048). Flags: `control-failed` (Claude < 18/20, FR-016),
`identical-outputs`, `engine-only-one` (TC-037). Disclosure line per candidate (TC-033).
`--publish` writes the Markdown with `$HOME` and any absolute path removed (FR-015).
