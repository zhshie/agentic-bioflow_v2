# The framework is open source under Apache-2.0; revenue comes from the box and the service

The framework in this repository is released under Apache-2.0, and so are the evaluation tasks
used to measure whether a model can drive it. What is sold is a pre-installed machine running a
local model (the Brain) plus onboarding and support; tuned model settings and per-customer
configuration stay private.

Why: a Claude Code plugin installs as plain-text files on the user's machine, so closing the
source would hide nothing technically. Transparency and reproducibility are the Product's own
selling points, and everything it builds on is permissively licensed (Nextflow Apache-2.0,
nf-core MIT) as are most competitors (Galaxy, Terra, Biomni). The evaluation tasks are published
because they are what lets a buyer trust the claim that a local model can do the job. Apache-2.0
over MIT for its explicit patent grant.

## Considered Options

- **Closed source** — rejected: unenforceable in practice for plain-text plugin files, and at odds
  with the positioning.
- **AGPL** — not chosen: stronger copyleft buys little when the revenue is not the code.
