# One lab, two roles: PI and member

The platform (ADR 0004) is shared by the people of one lab, and has two roles. A **member** runs
their own analyses and sees their own runs. A **PI** sees every run in the lab, who ran it, how
much it cost in NCHC SU and which failed, and spends nothing by default. Each person uses their
own NCHC account and their own credential, held by their own station agent, never by the
platform and never by another member. The platform stores metadata only (ADR 0004).

Why: Seqera reaches the same view only through organisations, workspaces, teams and several
roles, and its free tier stops at three members and three concurrent runs (seqera.io/pricing).
A lab here needs "who ran what, for how much" on one page, not an access-control system. Per-person
credentials are required anyway: NCHC's login uses a per-person one-time code
(`docs/LAB_AGENTS.md`, §1), and "accounts are never shared" was already agreed
(`docs/ROADMAP.md`, "Principles waiting for a check").

## Considered Options

- **Seqera's model (organisation → workspace → team, several roles, SSO)**: rejected as more to
  learn than a lab needs.
- **One shared lab account**: rejected; one code-holder becomes everyone's bottleneck, and no one
  can tell whose run is whose.
- **Single user only**: rejected by the maintainer, who asked for a simplified multi-user lab.

## Consequences

- Enforcing the roles is a principle waiting for its check (ROADMAP, Stage 2).
- The hosted service serves many labs, but nothing sits above a lab: no lab sees another's runs,
  and there is no organisation that groups labs.
