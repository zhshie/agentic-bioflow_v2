# platform-doc-storage

Source: issue #119 item 'What the platform stores' (ADR 0004 'metadata only' vs ADR 0009 / 009c / keep-submissions which keep bundles and screen text). Docs only, A tier.

1. Add a section to docs/PLATFORM.md: a table 'What the platform stores / where / how long' — one row per kind of data, from the code on v3 (store.py, confirm.py, jobs.py, oauth.py, http_auth.py, records.py, uploads; docs/OPERATIONS.md section 4 lists files): e.g. run index (rebuildable), confirmed submission bundles and screen text (until the owner forgets them: keep-submissions), job rows (pruned 7 days after the job ends), tokens/users/OAuth, web sessions, uploads, fetched records. Every 'how long' must come from code or existing docs; if the code has no rule, write 'no automatic deletion' — never invent a period.
2. A short 'first-use disclosure' paragraph: the sentence a person should be shown the first time (what is kept, that they can forget a submission with `abf-platform forget`). Mark that showing it in the web/clients is not built yet.
3. Fix the ask-rule sentences (around lines 411-422) so the Claude Code ask list names all five gated tools: launch, cancel, resume, relaunch, forget (matching extensions/claude-code-kit/settings.json).

Test (write first) tests/platform_storage_doc_test.sh: the new heading exists; each table row's 'where' file/table name exists in platform/ code; the ask list sentence names exactly the tools in extensions/claude-code-kit/settings.json's ask list.

Out of scope: code, CHANGELOG.md, other docs.

## Rulings after contract round 1 (developer-agent, 2026-10-18)
- P1 Item 3 becomes verify-only: line ~411 already names the five tools (d2ba5a7). The test pins that sentence to the settings.json ask list so it cannot drift again. Do NOT change lines ~417-422 (they are about the terminal commands `abf-platform launch|cancel`, not the kit's MCP ask list).
- P2 Also fix the two stale tool lists the verifier found: line ~6 ("Two more tools, `launch` and `cancel`") and the action list near line ~460 so they name the current write tools (launch, cancel, resume, relaunch, forget) consistently with line ~274 / ~466. The test checks these lists against mcp_server.py's write tools.
- P3 Heading: `## What the platform stores`; table columns What / Where / How long. Disclosure: one paragraph, at most 3 sentences.
