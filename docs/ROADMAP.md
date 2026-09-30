# Roadmap

Where the Prototype is going, stage by stage. The constitution
(`.specify/memory/constitution.md`) holds only what is true at every stage; everything that
differs between stages lives here. Each stage's concrete work is opened as its own Spec Kit
feature. Terms are defined in `CONTEXT.md`. Decided 2026-09-28.

## Positioning

> No HPC? Use an NCHC account or rent a cloud machine. Students describe the goal of their
> experiment in conversation and go from raw data to publishable figures, tables and text. The
> AI can be your own, and the data never leaves the lab.

The Product is conversation-first, not a click-through GUI. Its core chain:

1. Draw the lab's experiment design out through conversation into an approved **Experiment spec**.
2. Set up the matching nf-core pipeline from it.
3. Run statistics and plot figures with ordinary **Python or R scripts**, following the
   Operator's goal and preferred style. The scripts are handed over, so anyone can rerun them.
4. Package figures, tables, and a methods text with citations in one step.

It stops at figures and methods. Interpreting the results stays with the researcher.

**Who:** the PI pays, and graduate students or research assistants operate it. The first labs
are university agriculture, plant-pathology and microbiology labs, starting with 16S amplicon and
RNA-seq. Hospitals are out of scope; human-subject data brings a separate body of regulation.

**What is sold:** a pre-installed Brain (local model, conversation, plotting, packaging) plus
onboarding and support. Pipelines run on the Muscle, which is an HPC account or a rented cloud
machine. The framework is open source (ADR 0002).

## Stages

Each stage changes exactly one thing, so a failure points at one cause. Engineering that is known
to be doable comes first. Research with an unknown outcome (the local model) comes after it, and
also waits for the evaluation Mac, which arrives in mid-October 2026.

| # | Stage | What changes | Done when |
|---|---|---|---|
| 1 | **Prototype** (now) | — Claude Code + Seqera Platform + NCHC HPC. Before moving on, the plugin is audited against the constitution and every violation found is fixed | Spec Kit adoption finished; constitution audit findings fixed; first feature through the full flow |
| 2 | **Seqera optional** | Drive open-source Nextflow directly on HPC; read run state from Nextflow's own records; ship a local page to see progress and results (ADR 0001) | A 16S and an RNA-seq run complete on NCHC with no Seqera account |
| 3 | **Local-model experiment** | Nothing ships. Run the evaluation below through Claude Code + Ollama (and llama.cpp) on a 48 GB Mac — no code change needed. Specified and planned as feature `001-local-model-eval`; implementation starts when the Mac arrives | The evaluation says whether a ~30B model is enough, which sets the Brain's hardware and price |
| 4 | **Second host** | Keep Claude Code; add a Codex CLI adapter over the same host-independent core (ADR 0003). Codex cannot use Claude directly, so the safety-net tests are model-independent and must pass on both hosts; task tests keep Claude Code as the control | Safety-net tests green on both hosts |
| 5 | **Cloud** | The Muscle can be one SSH-reachable Linux VM with Docker. The Operator creates it at first; automation comes later. TWCC is tried first, with GCP's Taiwan region as fallback | The same runs complete on a rented VM |
| 6 | **Local model** | Ship a local open-weight model (Apache/MIT first, e.g. Qwen3.6) on the Brain, running on Codex — not on Claude Code, which cannot be redistributed | Evaluation below passes on the shipping host |

Order changed 2026-09-29 by the maintainer: "Seqera optional" moved ahead of the local-model
experiment, because the evaluation Mac arrives only in mid-October and the Seqera work needs no new
hardware. Development toward stage 2 and beyond never goes through Seqera's Services (ADR 0001).

## Local-model evaluation (stages 3 and 6)

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
test or tool already enforces. Each is added by a MINOR amendment once its check exists.

| Principle | The check that has to exist first | Earliest stage |
|---|---|---|
| No pipeline is set up before the Operator approves the Experiment spec | A gate (hook or equivalent) refusing setup without an approved spec, plus its test | 1–4 |
| Every Operator uses their own credentials; accounts are never shared (Anthropic's consumer terms forbid sharing, and HPC 2FA is per person) | A check that refuses a settings root already bound to another identity | 4 |
| Model-neutral command layer: no command depends on one model's behaviour | The evaluation task set passing on a second model | 3–6 |
| Any AI host without the safety net may query but never launch or delete | Safety-net tests that run against every supported host | 4 |
| Data stays local: nothing leaves except what the Operator was told leaves. While Claude is the model, logs, samplesheets and error messages go to Anthropic, and the Prototype says so | A disclosure shown at first use, plus its test | 1 |
| Any action that costs money needs the Operator's confirmation, and billable state is always visible and stoppable | A gate on billable cloud actions, plus its test | 5 |

## Open questions (not decisions)

- Can a person on alternative military service register a business, issue invoices or take
  payment? Ask the service authority before any money changes hands.
- Before charging anyone, ask Seqera (or a lawyer) how its Terms of Use apply; check whether
  nf-core has a trademark policy. The Product name cannot be "Nextflow <X>" (Nextflow trademark
  policy).
- TWCC: how a lab without an NSTC project pays, whether a VM can run Docker and reach the internet,
  and how long account approval takes.
