# Plan: dev-profiles-hook (A tier, base v3)

## Why
On 2026-10-18 the maintainer rejected the 011a web layout wholesale. Root cause: plans described function only, never what screens look like, and the verifier only graded function. Decision (maintainer, 2026-10-18): keep ONE executor and ONE verifier (no frontend/backend split); the developer-agent copies a per-kind specialty brief (profile, e.g. ui, backend) verbatim into the plan under a heading that starts with `## 專長守則`. The agents must treat that section as binding. This change only makes the workflow stricter (A tier). It is project-agnostic: new projects copy these two agent files.

## Changes
1. `.claude/agents/executor.md`: add a section `## Specialty brief in the plan` (place it after 'How to work'). Text, in English like the rest of the file: if the plan contains a section whose heading starts with `## 專長守則`, its rules bind this task on top of everything else in this file; if the brief and the plan disagree, or the brief needs a decision the plan or the project's DESIGN.md does not make (for UI work: any colour, font, spacing or layout not stated), stop with BLOCKED or list it under 卡住的原因／要問的問題 — never guess. In the report format, add a line `專長守則：照做／無（計畫沒附）／偏離（原因）` before 範圍外的改動.
2. `.claude/agents/verifier.md`: add a section `## Specialty brief in the plan` (place it before 'You must not'). CONTRACT: every executor and verifier rule in the brief that applies to this task maps to at least one TC. ACCEPTANCE: run the checks the brief names (they are read-only, e.g. a design detector on a rendered HTML file); a breach of a rule the brief marks binding is a FAIL; findings the brief routes to a person go under 需要人看的事. In the ACCEPTANCE report format, add a line `專長守則檢查：……（計畫沒附就寫「無」）` after 與 main 比較的退步. The verifier's tools line must stay without any write tool.
3. `tests/dev_workflow_test.sh`: add checks using the existing `has` helper: executor.md contains `## Specialty brief in the plan` and `專長守則`; verifier.md contains `## Specialty brief in the plan` and `專長守則檢查`. Keep every existing check unchanged; the existing 'verifier: tools grant no write' check must still pass.
4. `docs/PITFALLS.md`: append one short entry in the file's existing style: 011a layout rejected because the plan had no design spec; fix = design gate in the developer-agent (PRODUCT.md / DESIGN.md) + `## 專長守則` copied into the plan, which executor and verifier treat as binding (this PR).

## Out of scope
No change to the agents' tools, models, Stop hook or worktree rules; no other files; no change to the constitution, spec templates, CI or plugin.json.

## Done when
`bash tests/dev_workflow_test.sh` passes with the new checks, and the full suite `tests/run_all.sh` is green (WSL).

## Maintainer's words (verbatim, for the test cases)
- 「版面我完全不滿意，請你直接參考 Seqera 以及 Galaxy 的網頁」
- 「但以後developer會開發各種不同的專案，不限於agentic-bioflow」
