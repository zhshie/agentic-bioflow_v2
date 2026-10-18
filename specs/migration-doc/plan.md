# migration-doc: docs/MIGRATION.md

Source: issue #119 item 'v2 -> v3 migration'. Docs only, A tier. Runs after ops-doc in the same lane only to keep docs PRs small; files are separate.

## Goal
A new `docs/MIGRATION.md` for a v2 user moving to v3. Rule from the issue: keep the settings file; add the platform URL and a personal access token (PAT); Seqera fields become optional.

## Content
1. Who this is for and what changes (v2 = plugin + Seqera Platform; v3 = plugin talking to the self-hosted abf platform over MCP; read docs/adr/0001, 0004, 0006 and docs/SETTINGS.md).
2. Step by step: keep `settings` file as is; add the platform URL and PAT - use the exact key names the v3 code reads (grep `scripts/settings.sh`, `docs/SETTINGS.md`, `platform/` for the real names; if no key exists yet for the platform URL/PAT on the plugin side, say so in 'Not built yet' instead of inventing one); how to get a PAT (`abf-platform pat new`).
3. What happens to Seqera fields (optional; what still uses them, from the code).
4. Existing runs and project folders: what carries over (read docs/PLATFORM.md, `rebuild.py`).
5. Going back to v2.
6. Not built yet.

## Test (write first)
`tests/migration_doc_test.sh`, same style as other docs tests:
- file exists with the six headings;
- every settings key the doc names in backticks in section 2/3 appears in `docs/SETTINGS.md` or `scripts/settings.sh` (so it cannot invent keys);
- every `abf-platform <subcommand>` named exists in `platform/abf_platform/cli.py`.

## Out of scope
No code. Do not edit CHANGELOG.md, docs/PLATFORM.md, ROADMAP.md, SETTINGS.md.
