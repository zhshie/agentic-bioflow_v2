# Seqera Platform becomes an optional execution backend, not something we rebuild

The Prototype uses Seqera Platform as its execution backend and interface. The Product must also
run without it, and we get there by driving open-source Nextflow directly — reading run state
from Nextflow's own records (trace, report, weblog events, lineage) and adding a small local page
to see progress and results — not by building our own copy of Seqera Platform.

Why: open-source Nextflow already supports SLURM and the major cloud batch executors, and
`nf-core pipelines launch` already generates a parameter form from a pipeline's schema, so most
of what our Operators need from Platform exists without it. Rebuilding Platform (organisations,
workspaces, roles, credentials store, run database) is one person redoing a company's product,
which principle 1 forbids. Seqera's Terms of Use also forbid accessing its Services "for the
purpose of developing a product or service that competes with a Seqera product or service", so
the work toward running without Seqera is developed and tested directly on HPC and cloud
machines, never through Seqera's Services.

## Considered Options

- **Stay a Seqera add-on forever** — rejected: Seqera's own AI (Co-Scientist) covers the same
  ground, its bring-your-own-model option is Enterprise-only and Claude-only, and the free tier is
  limited to non-commercial, non-production use.
- **Replace Seqera with our own platform** — rejected for the reasons above.
- **Plug our model into Co-Scientist** — rejected: Enterprise-only, supports only Claude via AWS
  Bedrock or the Anthropic API.

## Consequences

- Constitution principle 2 names "the execution backend", not Seqera Platform, as the single
  source of truth for run state.
- Seqera-licensed components are avoided on the path without Seqera: Fusion needs a Seqera
  license even outside Platform; the `seqera` executor targets Seqera's own compute.
