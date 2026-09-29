# Implementation Plan: 本地模型評測（第 1.5 階段）

**Branch**: `001-local-model-eval` | **Date**: 2026-09-29 | **Spec**: `specs/001-local-model-eval/spec.md`

**Input**: `spec.md`, the approved `test-case.md` (48 cases, approved 2026-09-29), `research.md`,
`.specify/memory/constitution.md` 1.0.0, `docs/ROADMAP.md` (stage 1.5), `docs/POSITIONING.md`.

## 給維護者：複雜度與風險摘要（人工關卡 2）

**做法一句話**：題目放在 repo 的 `evals/local-model/`；每一次作答交給 Claude Code 內建的 `claude plugin eval` 執行（它會完整載入 plugin、每次隔離）；外面包一支我們自己寫的 Python 程式負責「一次跑一回、錯 3 次就停、判對錯、出結果表」。

**複雜度**：中。新程式約 6 支 Python（一支主程式、五類各一支判分），全部只用 Python 內建功能、不裝新套件。不動 plugin 現有的指令、skill、安全網。

**分四段做，每段結束全部測試綠燈才進下一段**：
1. 判分器：五類題目怎麼判對錯（用假答案測，不需要任何模型）。
2. 主程式：開始前檢查、迴圈、提早停止、分類、結果表（用假的「模型」測，不需要 Mac）。
3. 真題目與正確答案：寫五道題；Claude 起草的正確答案**要你逐題確認**（第三次請你看東西，預計 5 份）。
4. 在你的 Mac 上實測：這一段**要你操作**——開 Ollama／llama.cpp、下一個指令、跑一晚。

**風險（由高到低）**：
1. **Claude Code 可能不肯把請求轉給本地模型**：官方不支援這種用法，`claude plugin eval` 是否會把「改接本地模型」的設定傳進去也沒寫明。第 4 段第一件事就是用 1 次作答驗證；不行就改走備案——自己用 `claude -p` 跑迴圈，多寫約 1 支程式。
2. **Ollama 的已知錯誤**（Qwen3.6 工具呼叫偶爾讓 Ollama 回錯）：這正是 US3 要兩個引擎都測的原因；會被歸類成「引擎失敗」，不會誤算成模型答錯。
3. **Ollama 超過上下文長度時會默默截斷而不報錯**：會把「讀不完」誤判成「答錯」。對策：明確設定上下文長度，並用每次作答回報的 token 數推斷是否撞到上限。要在 Mac 上實測才知道準不準。
4. **一晚跑不完**：5 題 × 20 次 × 每次數分鐘，一個組合約 5–8 小時（推論，未實測）。錯 3 次就停會省時間；真的超時就分兩晚，不改題目。
5. **統計題需要 Mac 上有 R 與 DESeq2／phyloseq**：開始前的檢查會列出缺什麼，不會跑到一半才失敗。

**沒有違反憲法的地方**（逐條見下方 Constitution Check）。

## Summary

Measure whether ~30B local models can do this plugin's work, per the approved test cases.
Five fixed tasks (one per category) live in `evals/local-model/` in `claude plugin eval`'s own
case format. A stdlib-only Python driver (`scripts/eval/run_eval.py`) runs each task one trial at a
time through `claude plugin eval --runs 1 --ablation none --keep-temp --json`, classifies every
trial into the seven outcomes of FR-011, stops a task at its 3rd failure (FR-006) or the whole run
at 5 consecutive engine failures (TC-012), scores the model's own output files with per-category
scorers, and writes raw trial records outside the repository plus a scorecard. Candidates
(model × engine, or Claude as control) are JSON files; switching is configuration, not code.

## Technical Context

**Language/Version**: Python 3 (stdlib only; resolved through `scripts/require_python.sh` like
every other Python script here) + bash for tests.

**Primary Dependencies**: Claude Code ≥ 2.1.281 with `claude plugin eval` (verified present on the
dev machine, `claude plugin eval --help`); on the evaluation Mac: Ollama and llama.cpp
(`llama-server --jinja`, mainline build), R with DESeq2 and phyloseq for task ④; `curl` for
`scripts/cite.sh` (task ⑤ scoring).

**Storage**: files. Task set and references in the repo; trial records and scorecards under
`$ABF_EVAL_RESULTS` (default `$HOME/abf-eval-results`), never in the repo.

**Testing**: `tests/eval_*_test.sh`, repo style (ok/FAIL per case, exit code), driving the Python
with fixtures and a fake runner (`ABF_EVAL_RUNNER`) so no model, engine or network is needed.
Run in WSL/Linux via `tests/run_all.sh`; CI unchanged.

**Target Platform**: macOS on Apple Silicon (the maintainer's M5 Pro 48 GB) for real runs;
Linux/WSL for development and CI.

**Project Type**: CLI evaluation harness inside the existing plugin repository.

**Performance Goals**: one candidate completes the task set (with early stop) within 10 hours
unattended (SC-002). Speed is recorded, never gated (TC-043).

**Constraints**: no network egress of task content during local-model runs (FR-010); nothing can
launch or delete (FR-008); no new third-party Python packages; BSD userland compatible
(`tests/portable_userland.sh`).

**Scale/Scope**: 5 tasks × ≤20 trials × ~7 candidates (3 models × 2 engines + Claude) ≈ ≤700
trials total.

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1 design. Result: PASS, no violations.*

| Principle | How this plan complies | Proven by |
|---|---|---|
| 1 Build only what nobody maintains | Execution is `claude plugin eval` (Anthropic's); DOI resolution reuses `scripts/cite.sh`; forbidden-action detection reuses `hooks/confirm_launch.sh` and `hooks/confirm_cleanup.sh` as the oracle instead of a second regex. Only early stop, classification and numeric/structural scoring are ours — plugin eval has no script grader and no early stop (research.md). Every new script carries its `# Not <tool>:` header | TC-047, `tests/scripts_name_their_alternative.sh` |
| 2 No second copy of run state | Not touched: trial records describe evaluation runs, not pipeline runs; no pipeline is run | TC-042 |
| 3 No personal paths | Results root from `$ABF_EVAL_RESULTS`/`$HOME`; candidate files hold URLs, not paths | TC-046 |
| 4 Site-neutral command layer | No change to `commands/`; the harness never names a scheduler or site | `tests/command_layer_is_site_neutral.sh` unchanged |
| 5 Portable substance | Plain Python + JSON; runnable by a person without Claude Code except for the trial runner itself | — |
| 6 Any pipeline, no configuration | References come from each pipeline's own test profile/samplesheet; no per-pipeline config added to the plugin | `tests/no_per_pipeline_config.sh` unchanged |
| 7 Nobody needs the maintainer | Preflight says exactly what is missing before starting (FR-009) | TC-007–009 |
| 8 Measure before claiming | Four claims in research.md are marked "to verify" and are stage 4's first step | quickstart.md §Smoke |
| 9 Numbers point at files | Every scorecard number is computed from trial records and links back to them | TC-038, TC-048 |
| 10 Off-design takes one path | Unclassifiable trial outcome → recorded as such and the run continues; never improvised | TC-010 |
| 11 User's folder/shell | Results root is wherever the maintainer points it; scripts locate themselves via `__file__` | `tests/path_shapes_test.sh` |
| 12–13 Nothing goes quiet | Plugin failing to load stops the run loudly (TC-005); engine failures are named (TC-011/012) | TC-005, TC-011, TC-012 |
| Safety Net | Triple barrier: each trial runs with a temp HOME holding no site settings, token or ssh key; the plugin's hooks stay loaded (`ask` becomes a denial in headless mode — to verify, research.md item 2); plugin eval's OS sandbox limits network. Any attempt is classified as forbidden | TC-044, TC-045, TC-042 |

Development Workflow compliance: spec → clarify → test cases approved 2026-09-29 → this plan. The
plan cites `test-case.md` below for every stage.

## Design

### Task set (`evals/local-model/`)

One directory per task, in `claude plugin eval`'s format plus our sidecars:

```text
evals/local-model/
├── README.md                 # how to rerun (US4), public
├── causes.json               # fixed cause list + fix-action list for task ③
├── cases/
│   ├── t1-16s-setup/         # ① ampliseq samplesheet + params from an Experiment spec
│   ├── t2-rnaseq-setup/      # ② rnaseq, same
│   ├── t3-diagnose/          # ③ seeded failure log → cause id + fix actions
│   ├── t4-stats/             # ④ DESeq2 / phyloseq numbers from a public count table
│   └── t5-methods/           # ⑤ methods text; every citation must resolve
│       ├── case.yaml         # plugin eval case: prompt, max_turns, timeout_seconds
│       ├── task.json         # category, answer files expected, inputs (public URLs + sha256)
│       └── reference/
│           ├── answer.*      # the reference answer
│           └── source.json   # origin: official|drafted, confirmed: date (FR-017)
└── candidates/
    ├── claude.json           # control
    ├── qwen36-35b-a3b.ollama.json, .llamacpp.json
    ├── qwen36-27b.ollama.json, .llamacpp.json
    └── gpt-oss-20b.ollama.json, .llamacpp.json
```

`evals/` ships with the plugin; it is inert (no hook, command or skill reads it). Task-set version
= sha256 over every file under `cases/` and `causes.json` (FR-002, TC-027).

### Driver (`scripts/eval/run_eval.py`)

```text
run_eval.py --candidate <file> [--task <id>...] [--results <dir>] [--trials 20]
run_eval.py --scorecard [--results <dir>]          # rebuild from records only
run_eval.py --publish <out.md> [--results <dir>]   # summary safe to commit (FR-015)
```

1. **Preflight** (FR-009; TC-005, 007–009, 028, 029): candidate memory estimate vs machine RAM ×
   0.75; engine reachable and its version (Ollama `/api/version`, llama.cpp `/props`); each input
   downloaded to cache and checksum-matched, host in the public allowlist; each reference
   `official` or `drafted`+`confirmed`; R packages for task ④; plugin loads (one dry trial's
   `system/init` lists the plugin and no `plugin_errors`). Any failure → stop before trial 1, name it.
2. **Trial loop** (FR-006; TC-001–003, 012): per task, trial i = one runner call. Stop the task at
   the 3rd non-pass; stop everything at 5 consecutive engine failures with an engine message.
3. **Classify** each trial (FR-011; TC-010–014, 044, 045) in this order: engine failure (API
   connection/5xx in result) → timeout → context (input tokens ≥ 98% of candidate context) →
   forbidden (any Bash tool call in the transcript that `hooks/confirm_launch.sh` or
   `hooks/confirm_cleanup.sh` would gate) → format (answer files missing/unparseable/cause not in
   list) → scorer verdict pass/wrong.
4. **Record** (FR-014, FR-015; TC-038, 039): `$ABF_EVAL_RESULTS/<task-set-version>/<candidate>/<task>/trial-NN/`
   holding the kept transcript, answer files, `record.json` (outcome, reason, model+version,
   engine+version, date, duration, tokens, answer sha256).
5. **Scorecard** (FR-012, FR-013, FR-016; TC-015, 026, 031–037, 043, 048): Markdown + JSON built
   only from records of the current task-set version; setup (①②) and figures/methods (④⑤, with ③
   reported alongside) shown separately; engines side by side; tasks where Claude < 18/20 flagged
   and excluded; disclosure line per candidate (Claude: sent to Anthropic; local: stayed on this
   machine); "20 identical outputs" note.

The runner is `claude plugin eval` by default and is replaceable through `ABF_EVAL_RUNNER` (a
command that takes the same arguments and writes the same JSON) — the fake runner in tests, and the
`claude -p` fallback if research.md item 1 fails.

### Scorers (`scripts/eval/score_*.py`, pure functions: answer dir + reference dir → verdict + reason)

| Task | Pass when | Wrong reason names |
|---|---|---|
| ①② setup | samplesheet columns equal the reference set, rows equal as a set; every reference param present with equal value | the column / row / param |
| ③ diagnose | `cause_id` equals reference; required `fix_actions` ⊆ answer's | chosen vs expected |
| ④ stats | every reference number within 1% relative (absolute 1e-9 when the reference is 0) | the key, both values, the gap |
| ⑤ methods | ≥1 DOI; every DOI resolves via `scripts/cite.sh`; every reference-required tool cited | the unresolved DOI / missing tool |

DOI resolution happens after the trial, outside its sandbox, and sends only DOIs (FR-010 unaffected).

### Local-only traffic (FR-010; TC-034)

Local candidates set `ANTHROPIC_BASE_URL` to `127.0.0.1`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`,
and a sandbox network allowlist of localhost only. The automated test asserts the environment a
local candidate produces; confirming no packets leave is a stage-4 check on the Mac
(quickstart.md), recorded in the scorecard.

## Implementation stages (each ends with `tests/run_all.sh` green in WSL)

| Stage | Delivers | Test cases proven |
|---|---|---|
| S1 Scorers + task-set skeleton | `scripts/eval/score_*.py`, `causes.json`, `task.json`/`source.json` formats, fixture answers | TC-016–025, 027–030 |
| S2 Driver on a fake runner | `run_eval.py` preflight, loop, early stop, classify, record, scorecard, publish | TC-001–015, 026, 031–040, 042–048 |
| S3 Real tasks + references | five cases; official references fetched; drafted references **confirmed by the maintainer** | TC-016, 029, 030 on real files |
| S4 On the Mac | smoke (research.md items 1–3), Claude control, then candidates overnight | TC-041 (manual), real-world confirmation of TC-004, 034 |

After S4: `verifier` agent judges all 48 cases against the diff; manual walkthrough (TC-041) is
the maintainer's.

## Project Structure

### Documentation (this feature)

```text
specs/001-local-model-eval/
├── spec.md, test-case.md, test-case-overview.md (approved)
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/            # CLI + file formats
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
evals/local-model/        # task set, references, candidates (public)
scripts/eval/
├── run_eval.py           # driver
├── classify.py           # FR-011 order
├── scorecard.py
└── score_setup.py, score_diagnose.py, score_stats.py, score_methods.py
tests/
├── eval_scorers_test.sh
├── eval_driver_test.sh
└── fixtures/eval/        # fake runner, canned transcripts, fixture answers
```

**Structure Decision**: harness under `scripts/eval/` so the existing script checks (principle 1
header, portability) apply to it; task data under `evals/` because that is `claude plugin eval`'s
default location.

## Complexity Tracking

No constitution violations to justify.
