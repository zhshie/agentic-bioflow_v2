# The host is any MCP client; the gates move into the platform; the Claude Code plugin becomes a thin shell

Revised 2026-10-08 for ADR 0004. The first version (2026-09-28) kept Claude Code and added Codex
CLI as a second host through a thin adapter; that is replaced below. Its licence and local-model
findings still hold and are kept.

Under ADR 0004 the platform is reached through MCP, so the host is whatever MCP client the user
already has: Claude Desktop first, then Claude Code, Codex and others. No host gets an adapter of
its own. The gates (launch confirmation, cleanup confirmation, walkthrough, protected paths) move
into the platform's tool layer as each action becomes a platform tool, so a host without hooks
still cannot skip them: a write tool answers "needs confirmation", the host shows that, the user
says yes, and the call is repeated with the token. Until then the gates stay where they are, in
the Claude Code plugin's hooks; "gates live in the tool layer" is a principle waiting for its
check (`docs/ROADMAP.md`).

The existing Claude Code plugin stays, and becomes a thin shell: its skills (judgment and
procedure) and the intro / next-step hooks remain; once the platform's tools exist, its commands
call those tools instead of `tw`, and its gate hooks call the same gates the tools carry.

Why: MCP is the one interface every current harness speaks, so building for it replaces building
one adapter per host. Gates in a hook protect only the host that runs the hook; gates in the tool
protect every host.

## Findings kept from the first version

- Claude Code is "© Anthropic PBC. All rights reserved" under Anthropic's Commercial Terms
  (anthropics/claude-code LICENSE.md), so it cannot be pre-installed in a box we sell, and
  Anthropic states it "doesn't support routing Claude Code to non-Claude models through any
  gateway" (code.claude.com/docs/en/llm-gateway).
- Codex is Apache-2.0 and runs local models with `--oss` (Ollama, LM Studio). It does not support
  `permissionDecision: "ask"`, and its `transcript_path` may be null; neither matters once the
  confirmation lives in the tool rather than in a host hook.
- On any host other than Claude Code, Claude is reachable only with an API key billed per token:
  since 2026-02 Anthropic forbids using Free/Pro/Max subscription credentials in other tools.
- A local model is measured first through Claude Code + Ollama's Anthropic-compatible API because
  that needs no code change; which host ships it is decided at Stage 5, not here.

## Considered Options

- **Claude Code plus a Codex adapter (the first version)**: replaced; an adapter per host does
  not scale, and the platform needs to be callable from hosts we do not maintain.
- **Our own harness**: rejected in ADR 0004.
- **OpenCode, Goose as hosts with our hooks**: no longer the question; any of them is a host if
  it speaks MCP.

## Consequences

- The old roadmap's "second host" stage (the Codex adapter) is dropped.
- Safety-net tests move with the gates: they test the tool's refusal, which holds on every host.
- A host that cannot show a "needs confirmation" answer to the user cannot launch or delete.
