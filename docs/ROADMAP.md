# Roadmap

Where the project is going, stage by stage. The constitution
(`.specify/memory/constitution.md`) holds only what is true at every stage; everything that
differs between stages lives here. Each stage's concrete work is opened as its own Spec Kit
feature. Terms are defined in `CONTEXT.md`. First decided 2026-09-28; replaced 2026-10-08 by the
platform direction (ADR 0004).

## Positioning

> 台灣版 Seqera: everything one lab uses from Seqera Platform, simpler, in Chinese, on an NCHC
> account or the lab's own cloud account, with no paywall on members or runs. The lab talks to
> it from the platform's own chat, with the model it chooses, or from the harness it already uses.

The Product is a hosted platform (ADR 0004) reached through MCP:

1. A student describes the experiment in the platform's chat or in their own harness (Claude
   Desktop first); either one calls the platform's MCP tools.
2. The platform sets up and launches the matching nf-core pipeline through a station agent that
   reaches the site with the student's own credential.
3. Statistics and figures are made with ordinary **Python or R scripts**, handed over so anyone
   can rerun them.
4. Figures, tables, and a methods text with citations are packaged in one step.

It stops at figures and methods. Interpreting the results stays with the researcher.

**Who:** the PI pays and sees the whole lab; graduate students or research assistants operate
it (ADR 0005). The first labs are university agriculture, plant-pathology and microbiology labs,
starting with 16S amplicon and RNA-seq. Hospitals are out of scope; human-subject data brings a
separate body of regulation.

**What is sold:** the hosted platform as a service, with onboarding and support. Compute runs on
the lab's NCHC account or the lab's own cloud account, paid by the lab. The framework is open
source (ADR 0002). A pre-installed box with a local model comes later (Stage 5).

## Stages

Each stage has a fixed done-when. One change is open at a time. Development and testing never go
through Seqera's Services, its MCP server or `tw`; features are compared against Seqera's public
documentation only (ADR 0004, `docs/SEQERA_PARITY.md`).

| # | Stage | What changes | Done when |
|---|---|---|---|
| 0 | **Direction recorded** | ADR 0004 and 0005, ADR 0003 revised, constitution 3.0.0, this file, `docs/POSITIONING.md`, `docs/SEQERA_PARITY.md` | The maintainer merges constitution 3.0.0 |
| 1 | **Station agent** (feature 007) | Seqera's Tower Agent pattern turned around: a small program on the user's machine (WSL) or the lab's always-on computer holds the SSH connection the user opened with their one-time code and connects outbound only to the platform for work. This repository's gates, preflight, relay and cleanup rules move into it | The agent runs on the maintainer's laptop; the platform's "list rawdata" and "launch ampliseq" both succeed through it; a gate refuses `rm results`; NCHC has answered M6 |
| 2 | **Platform core** (features 008–010) | 008: Tower-compatible receiver for the `nf-tower` plugin's events, kept as a rebuildable index. 009: the MCP server, following Seqera MCP's tools plus `list_site_files`, `validate_samplesheet`, `estimate_su`, `read_task_log`, `run_downstream`, `build_package`; every write tool carries its own confirmation. 010: the two-role lab | A student in Claude Desktop runs a 16S analysis end to end from conversation, the PI sees it on the web, and nothing goes through Seqera |
| 3 | **Web** (features 011–014) | 011: dashboard and run detail. 012: launch form from the pipeline schema, datasets, SU estimate with a cap. 013: rendered reports and the delivery package. 014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009 | Two members of the trial lab use it for two weeks with fewer than 10 new PITFALLS; the hosted service goes live (charging waits on the open questions below) |
| 4 | **Cloud compute** | The station agent also runs on a VM the lab rents; Nextflow's AWS Batch executor; an estimate and cap before anything is billed; TWCC first | A lab with no NCHC account completes the same 16S |
| 5 | **Model-neutral shipping** | Gates verified from Codex and other MCP clients; the local-model evaluation below (feature `001-local-model-eval`, when the evaluation Mac arrives); the box of ADR 0002 | The evaluation passes on the shipping host |

Dropped on 2026-10-08: the old "local page to see progress and results" (replaced by the web of
Stage 3) and the old "Codex adapter" stage (any MCP client is a host, ADR 0003).

Line A is unchanged: 2.17.0 goes to the trial lab first, and its installation steps are shown to
the maintainer before they are sent.

History: on 2026-09-29 the maintainer moved "Seqera optional" ahead of the local-model experiment
(ADR 0001). That order is superseded by the stages above (ADR 0004).

## Local-model evaluation (Stage 5)

- A fixed, published task set covers 16S and RNA-seq on public test data.
- Score the model's own work, not Nextflow's: is the Experiment spec → samplesheet and parameters
  correct, and are the figures and methods traceable to their sources? "Pipeline completed" and
  "figures + methods" are scored separately.
- Run each task at least 20 times, because 5 runs cannot tell 60% from 95%. Claude runs the same
  set as the control.
- If a local model reaches only pipeline setup and not figures and methods, the Product's scope
  for local models stops there, and says so.
- Candidates and engines (from the 2026-09-28 sizing review, `docs/POSITIONING.md`):
  Qwen3.6-35B-A3B and Qwen3.6-27B at 4-bit, gpt-oss-20b as a floor; each on Ollama and on
  llama.cpp `--jinja`, so a broken engine is not mistaken for a weak model. Tasks: 16S and
  RNA-seq samplesheet + parameters from an Experiment spec; diagnosis from a seeded failure log
  (without launching anything); DESeq2 / phyloseq numbers against a reference; methods text
  whose every citation resolves. Context of at least 64k, preferably 128k.
- Pass threshold: 18 of 20 runs (90%) per task, decided by the maintainer on 2026-09-28.

## Principles waiting for a check

These are agreed but not yet in the constitution, because the constitution admits only rules a
test or tool already enforces. Each is added by amendment once its check exists.

| Principle | The check that has to exist first | Earliest stage |
|---|---|---|
| The platform's run index is never a second truth: it can be rebuilt from Nextflow's own records, and where they disagree the records win | A test that drops the index, rebuilds it from the records, and finds them equal | 2 |
| The platform stores metadata only and never holds a site credential; credentials stay on the user's station agent | A test that the platform's store and API refuse or never receive a credential field | 1–2 |
| Every platform write tool (launch, delete, clear `work/`) refuses without the user's confirmation step | A test per write tool: a call without the confirmation token is refused | 1–2 |
| Gates live in the platform's tool layer, so whichever host calls a tool meets the same gate; the plugin's hooks become callers | The Safety Net's tests run against the tools, not the hooks | 1–2 |
| PI and member roles are enforced: a member sees and runs their own work; a PI sees the lab and spends nothing by default; no lab sees another's | Role tests against the platform's API | 2 |
| No pipeline is set up before the Operator approves the Experiment spec | A gate refusing setup without an approved spec, plus its test | 2 |
| Every Operator uses their own credentials; accounts are never shared (Anthropic's consumer terms forbid sharing, and HPC 2FA is per person) | A check that refuses a station agent or settings root already bound to another identity | 1 |
| Model-neutral command layer: no command depends on one model's behaviour | The evaluation task set passing on a second model | 5 |
| A host reaches launch and delete only through tools that carry their own gate; a host that cannot show a confirmation cannot launch or delete | The tool-layer safety-net tests, run from more than one MCP client | 5 |
| Data stays local: nothing leaves except what the Operator was told leaves. While Claude is the model, logs, samplesheets and error messages go to Anthropic, and the Prototype says so | A disclosure shown at first use, plus its test | 1 |
| Any action that costs money needs the Operator's confirmation, and billable state is always visible and stoppable | A gate on billable cloud actions, plus its test | 4 |

## Open questions (not decisions)

Each must be answered before the hosted service charges anyone (Stage 3).

- Can a person on alternative military service register a business, issue invoices or take
  payment? Ask the service authority before any money changes hands.
- How do Seqera's Terms of Use ("not for developing a competing product") read for a platform
  built from public documentation only, never through Seqera's Services? Ask a lawyer or Seqera.
  Check whether nf-core has a trademark policy. The Product name cannot be "Nextflow <X>"
  (Nextflow trademark policy).
- NCHC (M6, `docs/LAB_AGENTS.md`): may a login node keep a process running, and is automation on
  one person's account allowed?
- TWCC: how a lab without an NSTC project pays, whether a VM can run Docker and reach the internet,
  and how long account approval takes.
