# Research: 008-run-receiver (2026-10-11)

Constitution principle 1 asks what already exists for the same job, and whether it is reused.

| Item | Finding | Decision | Source |
|---|---|---|---|
| Tower trace API | Five trace endpoints: `POST /trace/create`, `PUT /trace/{id}/begin`, `/progress`, `/heartbeat` and `/complete`, plus an optional `?workspaceId=`. The token comes from `tower.accessToken` or `TOWER_ACCESS_TOKEN`; a JWT or personal access token is sent as Bearer, anything else as Basic `@token:`. `TowerFactory` only rejects an endpoint ending in `/`, and there is no service-info check. `create` doubles as the auth check, and its response must carry `workflowId`. | Write our own thin receiver. The plugin source is the specification. | https://raw.githubusercontent.com/nextflow-io/nextflow/master/plugins/nf-tower/src/main/io/seqera/tower/plugin/TowerClient.groovy , TowerObserver.groovy |
| seqeralabs/nf-tower (CE) | Archived 2025-01-30. MPL-2.0. A full Java backend plus web app that needs SMTP, Docker and a database. | Not used: heavy, unmaintained, and a second language stack. | https://github.com/seqeralabs/nf-tower |
| AugustDev/nf-shard | MIT. Next.js/TypeScript with Postgres and Prisma. Accepts any non-empty token. Last push 2024-09. | Reference only, for payload handling. Not used because it has no auth, is stale, and is TypeScript with Postgres. | https://github.com/AugustDev/nf-shard |
| MCP SDK | Python `mcp` 2.3.0 (Python 3.10+, MIT), supports Streamable HTTP and stdio. TS SDK v2 is also stable. Standalone FastMCP is at 4.1.0. | Official Python `mcp` 2.x. One language across the receiver, the MCP server and the future station agent. | https://pypi.org/pypi/mcp/json |
| Elicitation (human confirmation) | Client support is inconsistent: Claude Code yes, Claude Desktop unconfirmed, Cursor buggy. | Not relied on. Write tools (a later feature) confirm on the platform's own page. | https://modelcontextprotocol.io/specification/draft/client/elicitation |
| Tool annotations | `readOnlyHint` and `destructiveHint` are hints only. | Set them anyway. | MCP spec |
| Existing MCP for Nextflow | Seqera MCP is hosted only, with no repository. wjlim/nf-core_mcp is a community TypeScript server whose licence is unconfirmed. | Neither is used. Seqera's tool list serves as a design reference only, read from public documentation. | https://docs.seqera.io/platform-cloud/seqera-mcp/ |

Not yet extracted, for the executor to read from the pinned Nextflow version's source before coding:

- the exact `TraceRecord` and `progress` field lists;
- the heartbeat interval;
- the literal `Authorization` header.
