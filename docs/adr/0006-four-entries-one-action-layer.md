# Four entries, one action layer: how the plugin, the harnesses, the web and the chat reach the platform

Amends ADR 0003 and ADR 0004 (2026-10-15). Decided by the maintainer on 2026-10-15; the
development lead wrote it, a cold reviewer (a fresh model session with no prior context) read it
against the constitution and the repository, and the fifteen findings of that review shaped the
second version.

## The problem this record answers

ADR 0004 says the platform is reached through MCP and that the Claude Code plugin becomes a thin
shell (ADR 0003). Neither record says *how* the plugin is wired to the platform: the five
command files (`commands/setup|launch|runs|downstream|finish.md`, about 2,200 lines) still call
`tw` and `scripts/`, nothing in `commands/`, `skills/` or `hooks/` names `abf-platform` or its MCP
server, and the MCP server has six read-only tools. The part of the plugin that guides a person
(judgment and procedure) exists only in Claude Code's own `commands/` format and in hooks, so a
user on Claude Desktop or Codex has none of it. And the records were silent on four things a
hosted platform cannot do without: who the caller is, where the platform runs, how a person (not
a model) says yes, and what someone with no AI tool at all can do.

On 2026-10-15 the maintainer settled the direction, in his words:

- Install cost: 「只加 MCP 網址就能用」 — a user adds one MCP URL to the harness they already
  have; nothing else is required.
- First harnesses that must work, tested by a person: Claude Desktop, Claude Code, Codex.
  Others (Gemini CLI, Cursor, Copilot, OpenCode…) can install it in theory and are not tested
  one by one.
- The five command files become skills in the Agent Skills format.
- 「平台純粹靠GUI介面也要能使用」 — the platform's web pages are a complete entry for a person
  with no AI tool.
- 「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」 —
  the platform's own chat is a full entry too, not a later extra.
- v2 is frozen as the version proven on Claude Code with Seqera Platform and the Positron
  bridge; the platform generation is v3.

## Decision

### Four entries, one action layer

```
A. any MCP client     Claude Desktop / Claude Code / Codex / Gemini CLI / …   one MCP URL (required) + an optional harness kit
B. the platform's web pages (click only, no AI)                               browser login
C. the platform's own chat (a built-in MCP client; the user picks the model)  browser login
D. a person in a shell (`abf-platform`, `scripts/`)                           principle II.5's fallback
        │
        ▼
the platform's MCP server (`abf-platform mcp --http`, OAuth 2.1 or a personal access token)
  instructions = the routing table (generated from `skills/operational`): always present, nothing to click   (channel 0)
  prompts      = one prompt per skill, the full flow text                                                      (channel 1)
  skills       = the same `skills/` folder served through Skills over MCP, once clients read it               (channel 2)
  tools        = the entry to actions
        │
        ▼
the action layer, `platform/abf_platform/actions/`: one function per action; the MCP tools, the
web routes and the chat call these functions and nothing else. The gate of a write action lives
here, and its "yes" comes from a human channel (next section).
        │
        ▼
`skills/<name>/SKILL.md` (Agent Skills format): the single source of guidance. Copied into the
`abf-platform` package at build time; a test keeps the copy equal to the repository.
```

**Why an action layer.** Gates in a hook protect only the host that runs the hook (ADR 0003).
Gates in an MCP tool protect every MCP client but not a web page. Gates in the function that
both the tool and the page call protect every entry once, and the parity test (every action has a
tool and a route; `mcp_server` and the web import only `actions`) keeps a later tool or page from
reaching around them.

**Why skills, and why three channels.** The Agent Skills format (agentskills.io: a folder with a
`SKILL.md` carrying `name` and `description`) is read by Claude Code, Claude, ChatGPT and Codex,
Gemini CLI, Cursor, GitHub Copilot, VS Code, OpenCode, Goose, Hermes, OpenClaw and others, so one
folder is the guidance for every harness. Because the maintainer wants a user to add only a URL,
the guidance must also arrive *through* the URL: the server's `instructions` string (which every
MCP client loads at connection and which `platform/abf_platform/mcp_server.py` already sets)
carries the routing table of `skills/operational/SKILL.md`, so "I want to run RNA-seq" is routed
without anyone picking anything; each skill is also exposed as an MCP prompt for the full flow
text (Claude Code lists prompts as `/server:prompt` commands; how Claude Desktop shows them is not
documented and is the first thing `docs/TESTING.md` checks); and the official Skills over MCP
extension (SEP-2640, Final) serves the same folder to clients that implement it (today ChatGPT
in part, none of the three target harnesses). A harness kit that installs the skills locally is
an improvement, never a requirement.

### The "yes" must come from a person

ADR 0004 said a write tool "answers needs confirmation, the user says yes, and the call is
repeated with the token". That round trip is executed by the model: it receives "needs
confirmation", can decide the user agreed, and repeat the call. `docs/PLATFORM.md` ("The limits
of the confirmation") already concedes the same about the terminal prompt. So the token is the
record of a confirmation, not the confirmation. Every write action binds its gate to a channel a
person operates:

1. A client that supports MCP elicitation gets a form-mode yes/no (Claude Code does, with both
   form and URL modes; Codex is reported to, and is tested before it is relied on).
2. Any other client gets a confirmation URL: the tool's answer names a page on the platform, the
   person opens it in a browser they are logged into, approves there, and the repeated call
   succeeds. The confirmation dialog of the web pages is the same page.
3. The Claude Code kit adds a permission `ask` rule for the platform's write tools as a second
   layer; it is not the gate.

The check that lets this join the constitution (the MAJOR amendment that ships with feature 009; its number is whatever MAJOR is next when it lands) is "an
unconfirmed launch is refused through the MCP tool *and* through the web route", not a test of the
action function alone.

**Landed (spec 009c, 2026-10-17).** The amendment is constitution 5.0.0. The three channels above
are three objects of the action layer (`TERMINAL`, `ELICITED`, `PAGE`); the MCP tools `launch` and
`cancel` write a pending request and ask the person, and a pending request is no confirmation (the
queue requires `state = confirmed`). The page is `abf-platform web`, a program of its own, not part of
the MCP server's bearer check. Its login is a name and a **web password** that only
`abf-platform user passwd` can set, typed at a real terminal and kept as a scrypt hash: a first
version that logged in with the personal access token was refused at review, because an AI that holds
the token could then log in and press for the person. The honest boundary is in the constitution and in
`docs/PLATFORM.md`: an AI that can run commands on the person's own machine can do what the person
can; the gate stops the AI clients that reach the platform only over MCP.

### Where the platform runs, and who is calling

"One URL" and the maintainer's definition of v3.0.0 (a student in Claude Desktop runs a 16S
analysis from conversation) both require a platform at a public HTTPS address: Claude Desktop's
connectors are account-level and do not reach a loopback port. So feature 009 includes MCP
authorization (OAuth 2.1, with a personal access token for clients without OAuth, as Seqera MCP
does) and the identity each token carries: user, lab, agent and compute environments (the roles of
feature 010).

Today "the platform and the agent must be on the same machine" (`docs/PLATFORM.md`) because the
reverse SSH forward ends at the agent's loopback. That is a limit of slice 007b, not the design:
ADR 0004 already has the station agent connect outbound to the platform. In the hosted topology
the login node's relay sends Nextflow's events to the platform's public HTTPS address directly and
the reverse forward goes away; the agent stays on the user's machine or the lab's always-on
computer and fetches work from the platform. No new daemon appears (principle 2): the relay
already exists and only its destination changes. The first test on the three harnesses uses the
maintainer's always-on desktop behind a TLS tunnel, not `127.0.0.1`.

### Hooks and the gates they carry

Removing a gate hook changes the Safety Net, so it is the maintainer's and MAJOR (Governance);
it is not a technical choice of the development lead. The map:

| hook | the Safety Net rule it carries | what replaces it, with its test | when |
|---|---|---|---|
| `hooks/confirm_launch.sh` | a launch is shown in full and waits for explicit confirmation | the action layer's launch gate with a human channel; the check above | the MAJOR amendment with feature 009 |
| `hooks/confirm_cleanup.sh` | deleting `work/` or `.nextflow/cache/` needs confirmation | nothing: deleting is a shell act that no MCP tool sees | kept for good |
| `hooks/confirm_walkthrough.sh` (G7) | credentials never printed, never in a params file | the action layer's credential rule and `tests/credentials_stay_in_settings_test.sh` | that MAJOR amendment or later, each in its own MAJOR pull request |
| `hooks/guard_plugin_files.sh` | the installed plugin copy is not edited | nothing on the platform side; a Claude Code matter | kept |

The intro and next-step hooks (`plugin_intro.sh`, `next_step.sh`, `session_start.sh`) are Claude
Code conveniences and stay in the Claude Code kit.

### What the web pages must do without AI

`downstream` (agreeing an analysis plan, writing R or Python) and the methods text of `finish`
need a model's judgment; a click-only page cannot invent an analysis for an experiment, and a
canned analysis per pipeline is what principle 6 forbids. The maintainer accepted on 2026-10-15:
the web pages complete **setup → launch → runs → rendered reports → the package of the pipeline's
outputs**; figures from scripts are made in the platform's chat or in a harness. The Stage 3
done-when says so.

### v2 and v3

`main` stays the v2 line until v3.0.0. `.claude-plugin/marketplace.json` installs from `main`
(`"source": "."`) and the trial lab runs 2.17.0, so a `3.0.0-dev` on `main` would ship unfinished
work to them. v3 is built on the long-lived branch `v3` (the CI trigger for `v3` is configured on the `v3` branch itself, not in this record's pull request; the maintainer
approved the CI change on 2026-10-15). On the day of v3.0.0, `v3` merges into `main`,
`v2-maintenance` is cut from the last 2.17.x, and the marketplace description changes. Until
then v2 takes bug fixes and changes that make the Safety Net stricter, released as 2.17.x only
when a fix affects a user. The Positron bridge (`extensions/positron-bridge/`) is independent of
the harness and stays in both lines. Issues #7 and #8 (launch through `tw`) are closed at v3.0.0
as "not fixed in v2".

### The constitution

- Now, 4.1.0 (MINOR): principle II.5 names `skills/` beside `docs/` and `scripts/` as a home of
  judgment and procedure. Its check, `tests/works_without_host_test.sh`, already packs `skills/`.
- Waiting for a check in `docs/ROADMAP.md`, to join by the MAJOR amendment with feature 009: every entry
  reaches the same action; gates live in the action layer and a person says yes; the platform's
  own tools count as "in use"; the web pages and the tools match one to one.

## Considered Options

- **Require a skills pack on every harness**: rejected by the maintainer (「只加 MCP 網址就能用」);
  the platform's own chat and Claude Desktop have no skills install anyway.
- **One adapter per harness** (ADR 0003's first version): still rejected; a kit is a manifest that
  points at the one `skills/` folder and the one URL, not an adapter with logic.
- **Gates only in the MCP tools** (ADR 0003 revised, ADR 0004): rejected; a web page would not
  meet them. Gates live one layer down, in the actions both call.
- **The token round trip as the gate**: rejected; the model can complete it. A person completes
  an elicitation form or a confirmation page.
- **Two MAJOR amendments weeks apart** (redefine II.5 now, move the gates later): rejected; the
  constitution admits only rules with an existing check, so II.5 gets a wording change now and
  its redefinition rides with the gates in the MAJOR amendment with feature 009.
- **A second repository for v3**: rejected; `scripts/`, `docs/PITFALLS.md`, the constitution and
  the tests continue. A branch does the same without breaking history.
- **v3 on `main` with a `3.0.0-dev` version**: rejected; the marketplace installs `main`.
- **Click-only pages that also make figures**: rejected (principle 6); the chat does that.

## Consequences

- ADR 0003 is amended: "gates move into the platform's tool layer" reads "into the action layer
  that the tools and the web pages call"; "no host gets an adapter of its own" stands, and a
  harness kit is not an adapter.
- ADR 0004 is amended: "every AI path goes through the MCP tools" stands for AI paths; the web
  pages are a non-AI path to the same actions; the confirmation is a person's act on a human
  channel, of which the token is the record.
- `docs/LAB_AGENTS.md`'s host tiers (H1–H3) change axis in feature 009's follow-up: from "are the
  hooks loaded" to "does the entry carry the platform's gate". Until then, `docs/CONDITIONS.md`
  and `scripts/detect_conditions.sh` are unchanged and Codex remains read-only on v2.
- `docs/POSITIONING.md` point 2 ("平台只開 MCP") becomes four entries.
- Feature 009's scope: the action layer, the write tools, the human-channel confirmation,
  authorization and identity, `instructions` and prompts mirroring `skills/`, the Skills over MCP
  endpoint, the skills copied into the package, the parity and import tests, the relay sending
  events to a public address. Features 011–013: the web pages matching the actions one to one.
  Feature 014: the chat.
- The command files move to `skills/` on the `v3` branch (a move without content change, so
  that the content change per skill is planned, not discovered); `main` keeps `commands/`.
