# Keep Claude Code, add Codex as the second host; a local model on Claude Code is for experiments only

The core (`scripts/`, `docs/`, the procedure in `commands/` and `skills/`) stays host-independent,
and each AI host gets a thin adapter: Claude Code today, Codex CLI next. Local models are first
measured through Claude Code + Ollama's Anthropic-compatible API because it needs no code change,
but the Product that ships a local model runs it on Codex.

Why: Claude Code is "© Anthropic PBC. All rights reserved" under Anthropic's Commercial Terms
(anthropics/claude-code LICENSE.md), so it cannot be pre-installed in a box we sell, and Anthropic
states it "doesn't support routing Claude Code to non-Claude models through any gateway"
(code.claude.com/docs/en/llm-gateway). Codex is Apache-2.0, runs local models with `--oss`
(Ollama, LM Studio), and its hook protocol (PreToolUse deny via `permissionDecision`, Stop,
UserPromptSubmit, SessionStart) is close to Claude Code's, so the safety net ports rather than
being rewritten. Only about 12% of the current plugin is Claude-Code-specific (mostly `hooks/`),
which is what principle 5 was designed for.

## Considered Options

- **Claude Code only** — rejected for the Product: licence and no official local-model support.
- **Move to OpenCode** — rejected: no blocking Stop hook and no UserPromptSubmit injection, so
  roughly the walkthrough and next-step gates would be lost and the rest rewritten in TypeScript.
- **Goose** — UserPromptSubmit is observe-only and there is no transcript path.

## Consequences

- Codex does not support `permissionDecision: "ask"`; a launch gate becomes "deny, then confirm
  in conversation". Codex's `transcript_path` may be null, so transcript-reading gates must fail
  closed (principle 13).
- Codex supports only the `responses` wire API, so it cannot use Claude directly. The roadmap's
  "port the host, keep the model Claude" stage becomes: safety-net tests are model-independent
  and must pass on both hosts; task tests use Claude Code as the control.
- On any host other than Claude Code, Claude is reachable only with an API key billed per token:
  since 2026-02 Anthropic forbids using Free/Pro/Max subscription credentials in other tools.
