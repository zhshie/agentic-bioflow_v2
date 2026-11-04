# Cloud session probe (cloud/probe-169e66)

## 1. Tools available
- Core: Bash, Read, Write, Edit, Glob, Grep
- Agent (subagents: claude, general-purpose, Explore, Plan, claude-code-guide, statusline-setup, executor, verifier)
- Workflow (present, only usable on explicit user opt-in to multi-agent orchestration)
- WebFetch / WebSearch (deferred; load via ToolSearch)
- Artifact, Skill, ToolSearch, AskUserQuestion, Task* tools, Cron*, Monitor, SendMessage, ListAgents
- MCP: Claude_Code_Remote (repos, sessions, triggers), Claude_Docs, Gmail, Google Drive/Calendar, Slack, Notion, Canva, PubMed, bioRxiv, Consensus, Agentic-bioflow (connects intermittently)
- bio-research plugin MCP servers: several fail with proxy 403

## 2. Model
Configured: claude-sonnet-5-5 (serving model may differ).

## 3. Repo / branch
- origin: https://github.com/zhshie/agentic-bioflow_v2 (fetch/push)
- branch at probe time: cloud/probe-169e66 (created from main @ 66fbc94)

## 4. gh
`gh auth status`: Failed to log in to github.com using token (GH_TOKEN) - token invalid.
GraphQL is blocked in this environment (REST only). Git push works via the session git proxy.

## 5. Parallel subagents
Hard maximum unknown. Tool guidance says independent agents can be launched in one message; Workflow default guideline is under 10 agents. Not tested.
