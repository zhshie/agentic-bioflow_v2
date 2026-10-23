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

**Who:** graduate students or research assistants operate it, one person per account, and each
person sees only their own runs. The PI view (the PI pays and sees the lab) is postponed with the
two roles (ADR 0009; ADR 0005 postponed). The first labs are university agriculture, plant-pathology and microbiology labs,
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
| 1 | **Station agent** (feature 007) | Slice 1 is a station agent + compute environments (Seqera model, all types; NCHC first): connection, environments, read-only jobs (`docs/PLATFORM.md` sections 6 to 8). Slice 2 (007b) launches through the agent, under constitution 4.0.0, behind the user's confirmation. 007b is built and waits for its manual acceptance on the real cluster (TC-047 to TC-050 in `docs/TESTING.md`). Seqera's Tower Agent pattern turned around: a small program on the user's machine (WSL) or the lab's always-on computer holds the SSH connection the user opened with their one-time code and connects outbound only to the platform for work. This repository's gates, preflight, relay and cleanup rules move into it | The agent runs on the maintainer's laptop; the platform's "list rawdata" and "launch ampliseq" both succeed through it; a gate refuses `rm results`; NCHC has answered M6 |
| 2 | **Platform core** (features 008–010) | 008: Tower-compatible receiver for the `nf-tower` plugin's events, kept as a rebuildable index. 009: the action layer (one function per action, called by the MCP tools, the web pages and the chat), the MCP server's write tools following Seqera MCP's tools plus `list_site_files`, `validate_samplesheet`, `estimate_su`, `read_task_log`, `run_downstream`, `build_package`; every write action's gate answered on a human channel (elicitation form or a confirmation page); OAuth 2.1 / personal-access-token authorization and the identity each token carries; the server's `instructions` and one prompt per skill mirroring `skills/`; the Skills over MCP endpoint; `skills/` copied into the package; the relay sending events to a public address. 010: postponed (ADR 0009), the two-role lab waits until roles return | A student in Claude Desktop runs a 16S analysis end to end from conversation, the student sees it on the web, and nothing goes through Seqera |
| 3 | **Web** (features 011–014, 016) | The web is three panes (ADR 0009): a left pane for projects and analyses, the working pane, and a right pane. 011: the web shell with the right pane (progress of all analyses), projects and analyses, run detail and the failure sentence (011a–e), matching the actions one to one (parity test). 012: settings and guided setup, the launch stage, uploads through the station agent (012a–d); cost shown per compute environment (NCHC SU and cloud money apart), a cloud cap per person per month (the number is set when an account opens), and no NCHC SU cap in dev mode; matching the actions one to one (parity test). 013: results, and the finished page with the delivery package (013a–b), matching the actions one to one (parity test). 014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009. 016: Studios (RStudio, Jupyter), on the person's own computer by default and embedded in the working pane (ADR 0008, ADR 0009) | A person with no AI tool completes setup → launch → running → results → downstream (in a Studio) → finished from the web alone; Two members of the trial lab use it for two weeks with fewer than 10 new PITFALLS; the hosted service goes live (charging waits on the open questions below) |
| 4 | **Cloud compute** | Merged into Stage 1 as far as modelling goes (merged into Stage 1: the 14 compute environment types are created there, `docs/SEQERA_PARITY.md` section F); what stays here is connecting a cloud type, which needs a real account. The station agent also runs on a VM the lab rents; Nextflow's AWS Batch executor; an estimate and cap before anything is billed; TWCC first | A lab with no NCHC account completes the same 16S |
| 5 | **Model-neutral shipping** | Gates verified from Codex and other MCP clients; the local-model evaluation below (feature `001-local-model-eval`, when the evaluation Mac arrives); the box of ADR 0002 | The evaluation passes on the shipping host |

Dropped on 2026-10-08: the old "local page to see progress and results" (replaced by the web of
Stage 3) and the old "Codex adapter" stage (any MCP client is a host, ADR 0003).

v2 and v3 (2026-10-15, ADR 0006): `main` is the v2 line until v3.0.0; v3 is built on the branch `v3`.
v2 takes bug fixes and changes that make the Safety Net stricter, released as 2.17.x only when a
fix affects a user.

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
| The platform stores metadata only and never holds a site credential; credentials stay on the user's station agent | A test that the platform's store and API refuse or never receive a credential field. *Note (6.0.0): the half 'a credential inside received data is never stored' joined the Safety Net; the API refusing a credential field still has no check.* | 1–2 |
| Every platform write tool (launch, delete, clear `work/`) refuses without the user's confirmation step | A test per write tool: a call without a person's answer on a human channel is refused; the confirmation token is only the record of that answer (ADR 0006). *Note: 4.0.0 binds the launch path to this check; 007b builds it for launch and cancel (the tests of TC-001 to TC-011 and TC-040 to TC-043). It is not moved into the constitution here.* *6.0.0 moved launch, cancel, resume, relaunch and forget into the Safety Net; delete and clear `work/` join when they exist with their refusal tests.* | 1–2 |
| Every entry (MCP client, web page, platform chat, shell) reaches the same action | A parity test: every action has an MCP tool and a web route, and `mcp_server` and the web import only `actions` | 2–3 |
| A call to the platform's own tools counts as a session in use | The Safety Net's scope test covers the platform's tools | 2 |
| The web pages and the tools match one to one | The same parity test | 3 |
| PI and member roles are enforced: a member sees and runs their own work; a PI sees the lab and spends nothing by default; no lab sees another's | Role tests against the platform's API | postponed (ADR 0009) |
| owed parity — every action has an MCP tool and a web route; the owed list only shrinks | The parity test (arrives with 011a) lists each action still owed a tool or a route and fails if that list grows | 3 |
| No pipeline is set up before the Operator approves the Experiment spec | A gate refusing setup without an approved spec, plus its test | 2 |
| Every Operator uses their own credentials; accounts are never shared (Anthropic's consumer terms forbid sharing, and HPC 2FA is per person) | A check that refuses a station agent or settings root already bound to another identity | 1 |
| Model-neutral command layer: no command depends on one model's behaviour | The evaluation task set passing on a second model | 5 |
| A host reaches launch and delete only through tools that carry their own gate; a host that cannot show a confirmation cannot launch or delete | The tool-layer safety-net tests, run from more than one MCP client | 5 |
| Data stays local: nothing leaves except what the Operator was told leaves. While Claude is the model, logs, samplesheets and error messages go to Anthropic, and the Prototype says so | A disclosure shown at first use, plus its test | 1 |
| Any action that costs money needs the Operator's confirmation, and billable state is always visible and stoppable | A gate on billable cloud actions, plus its test | 4 |
| A run lost with its site is resumed once without a new confirmation: only resume, only after a lost status, at most once per analysis, citing the original confirmation (ADR 0011) | Tests that the automatic resume fires for a lost run once, never for a failed or cancelled run, never as relaunch, and that the job cites the original confirmation | 2 |
| Keystrokes the platform relays to a web terminal (passphrase, OTP) are never stored, logged or echoed; the AI reads the terminal and never types into it (ADR 0011) | Tests that relayed input reaches neither the database, the data folder nor a log, and that no AI-facing tool can write to a terminal | 2 |

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

### Open questions from ADR 0009 (answered before the slice that needs them)

Asked by ADR 0009. The maintainer answered five of them on 2026-10-17, recorded in ADR 0010 ("Decided").

- How is an account created on the hosted service, and by whom? Answered: the operator creates it at a terminal; no self sign-up in v3.0.0.
- Are runs with no recorded person (started outside the platform) shown, and to whom? Answered: a terminal launch names the account; a run with no recorded person is hidden on the web and seen only on the local command line.
- May uploads and downloads pass through the hosted platform, or only through the station agent? Answered: loopback on the agent's machine, otherwise relayed through the platform with nothing written to disk (ADR 0010).
- Does each resume or relaunch need the confirmation page again? Answered: yes, every time.
- Studios on NCHC would be a second submission path and needs a constitution amendment: may it be built? Answered: not in v3.0.0.
- Which cloud account is used, and what number is the monthly cap per person? Partly answered: the cap is set when an account opens, and the page shows "—" until then; the cloud account is still open.
