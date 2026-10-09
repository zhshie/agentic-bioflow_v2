# A self-hosted platform with a Tower-compatible API, reached through MCP tools, with its own chat

Supersedes ADR 0001 (2026-10-08).

We build and host our own platform for running Nextflow / nf-core pipelines: everything one lab
uses from Seqera Platform, a simplified two-role lab (ADR 0005), hosted by the maintainer for
other labs the way cloud.seqera.io is hosted. Every AI path goes through its MCP tools: the
platform's own chat on the web, which connects to the model the user chooses, calls them, and so
does any harness the user already has (Claude Desktop first; Claude Code, Codex and other MCP
clients too). The goal is the lowest learning cost for a lab in Taiwan.

Decided by the maintainer on 2026-10-08, in his words: 「完全仿照 Seqera MCP 的模式，自建平台，
功能延續 Seqera（一間實驗室用得到的全部＋簡化版多人），由我自己架雲端服務給大家用（像
cloud.seqera.io），對話不自己做——平台只開 MCP，使用者用自己的 harness 接。」
On 2026-10-09, reviewing this record, he added a chat of our own: 「也做聊天介面 可接模型」.
The chat is a client of the same MCP tools, so it carries no gate or rule of its own.

## How it is built

- **Run events come from Nextflow itself.** Nextflow's built-in `nf-tower` plugin (Apache-2.0)
  sends a run's events to whatever server `tower.endpoint` names
  (registry.nextflow.io/plugins/nf-tower). The platform implements the receiving end of that
  API, so neither Nextflow nor the pipelines change and there is no monitoring daemon of ours.
  What it stores is an index of those events; Nextflow's own records (trace, report, log) stay
  the truth, and the index can be rebuilt from them (constitution, principle 2; ROADMAP,
  "Principles waiting for a check").
- **The platform stores metadata only.** Sequencing data stays on the site; site credentials
  never reach the platform.
- **A station agent reaches the site.** A small program on the user's own machine (WSL) or the
  lab's always-on computer holds the SSH connection the user opened with their one-time code and
  connects outbound only to the platform to fetch work (launch, list files, read a log, run a
  downstream script) and report back. This is Seqera's Tower Agent pattern turned around: the
  gates, preflight, relay and cleanup rules this repository already has move into it.
- **Every AI path goes through the MCP tools.** Its tools follow Seqera MCP's published tool list
  (docs.seqera.io/platform-cloud/seqera-mcp/seqera-tools) plus what a lab here needs and Seqera
  does not offer: site file listing, samplesheet validation, an NCHC SU estimate, task logs,
  downstream analysis and the delivery package. Every write tool carries its own confirmation:
  it answers "needs confirmation", the harness shows that, the user says yes, and the call is
  repeated with the token. Judgment and procedure stay in skills; MCP tools only act.
- **The platform's own chat connects to a model the user chooses.** It is a page of the web
  (Stage 3) for a lab member with no AI tool of their own: the user picks the model and pays for
  it (their own API key, or a local model), and the chat reaches the platform only through the
  same MCP tools, so a confirmation looks the same in the chat as in any harness.

## Considered Options

- **Keep Seqera optional and add a local progress page (ADR 0001)**: rejected by the maintainer;
  a page on one person's machine cannot be shared by a lab or hosted for others.
- **Only MCP, no chat of our own (this record's first version, 2026-10-08)**: replaced on
  2026-10-09 by the maintainer; a member with no AI tool of their own must still be able to use
  the platform.
- **Write our own general-purpose harness**: rejected; harnesses are maintained by others. The
  platform's chat drives only the platform's own tools, and MCP lets any harness call them too.
- **Fork nf-tower Community Edition** (github.com/seqeralabs/nf-tower, MPL-2.0, Groovy and
  Angular, archived): rejected as a base, kept as a reference for the API's shape.
- **Organisations, workspaces, teams, SSO**: rejected; one lab with two roles (ADR 0005).
- **Studios**: rejected; the user's own IDE on the site does that job (Studios were refused on
  NCHC, `docs/SITE_ADAPTER.md`).

## Consequences

- Constitution 3.0.0 redefines principle 1 (build only what Seqera cannot or will not do here,
  reuse open source for the rest) and principle 2 (Nextflow's records are the truth; the
  platform keeps an index).
- ADR 0003 is revised: the host is any MCP client, the gates move into the platform's tool layer,
  and the Claude Code plugin becomes a thin shell.
- ADR 0001's Terms-of-Use reason still holds. Seqera's Terms forbid accessing its Services "for
  the purpose of developing a product or service that competes with a Seqera product or
  service", so development and testing never go through Seqera's Services, its MCP server or
  `tw`; features are compared against public documentation only. How those Terms read for this
  project is asked of a lawyer or Seqera before anyone is charged.
- ADR 0002 stands for the code; the revenue gains a hosted service, and the box moves later.
- Seqera Platform is the reference: features follow its public documentation, narrowed to what
  a lab here uses and carried by the nf-tower plugin and other open source.
