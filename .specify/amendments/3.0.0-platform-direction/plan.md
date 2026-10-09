# Plan: Stage 0 — record the platform direction (constitution 3.0.0)

Branch `docs/stage0-platform-direction`. Tier: the constitution amendment is the maintainer's
to merge (C); the rest of the docs ride in the same PR, which is opened and not merged.

## The maintainer's decision, in his words (2026-10-08)

> 完全仿照 Seqera MCP 的模式，自建平台，功能延續 Seqera（一間實驗室用得到的全部＋簡化版多人），
> 由我自己架雲端服務給大家用（像 cloud.seqera.io），對話不自己做——平台只開 MCP，使用者用自己的
> harness（Claude Desktop 等）接。目標：簡化、適合台灣使用者、學習成本最低。

Also decided 10-07: confirmation stays a step-by-step text exchange (no confirmation card); the
Claude Code plugin stays and becomes a thin shell; the local-model box moves later; cloud compute
is paid from the user's own cloud account; one trial lab with an NCHC account, within three months.

Examples he gave of what the result must make true (quoted for the reviewer):
- 「平台只開 MCP，使用者用自己的 harness 接」 → no conversation UI of our own is planned anywhere. *(Superseded 2026-10-09: the platform gets its own chat; see the Revision section.)*
- 「簡化版多人：PI／成員兩角色」 → no organisation / workspace / team layer is planned.
- 「開發與測試全程不經 Seqera 的服務／MCP／tw」 → every document that plans new work says so.
- 「平台不持有國網憑證；只存 metadata」 → the platform design never stores a site credential.

## What changes, file by file

All of this is documentation; no script, hook, command or skill changes behaviour.

1. **`docs/adr/0004-self-hosted-platform-mcp-first.md`** (new). Supersedes 0001. Decision: a
   self-hosted platform that implements a Tower-compatible API, so Nextflow's built-in nf-tower
   plugin (`tower.endpoint`, Apache-2.0) sends run events to it with no change to Nextflow and no
   monitoring daemon of ours; MCP is the only AI entry point; the platform stores metadata only;
   site credentials stay with a station agent on the user's side that connects outbound only.
   Considered and rejected: our own harness / chat UI *(superseded 2026-10-09: only a general-purpose harness stays rejected)*; forking the archived nf-tower CE
   (MPL-2.0, Groovy/Angular); organisation / workspace layers; Studios (the user's own IDE
   instead). Consequences: constitution 3.0.0; ADR 0003 revised; the 0001 Terms-of-Use reason
   still holds (development never goes through Seqera's Services); ADR 0002's revenue line gains
   a hosted service, the box moves later. *(Superseded 2026-10-09: the cost sentence is removed; Seqera is named as the reference.)* Names the cost honestly: one person rebuilding part
   of a company's product, bought with time and narrowed to what a Taiwanese lab uses.
2. **`docs/adr/0005-single-lab-multiuser.md`** (new). Labs are separate on the hosted service (nothing above a lab), two roles (PI sees
   everything in the lab and spends nothing by default; member runs their own work), each person
   with their own NCHC credential on their own station agent; no org / workspace / team / SSO.
3. **`docs/adr/0001`**: a status line at the top, "Superseded by ADR 0004 (2026-10-08)"; body
   kept as history.
4. **`docs/adr/0003`**: host = any MCP client (Claude Desktop first; Claude Code, Codex, others);
   gates move into the platform's tool layer, so a host without hooks still cannot skip them; the
   Claude Code plugin becomes a thin shell (skills + intro/next-step hooks; its gates call the
   platform's tools once they exist); the separate "Codex adapter" stage is dropped. Licence and
   local-model facts kept.
5. **Constitution 2.1.0 → 3.0.0** (MAJOR: principles I.1 and I.2 are redefined).
   - **I title and I.1**: "Build only what Seqera cannot or will not do here". The change MUST
     still name what Seqera, nf-core or another maintained tool does for the same job, and then
     either reuse the open-source piece or say why it does not serve a lab here (cannot reach the
     site, needs Seqera's Services, licence, price). Script header forms and the Check unchanged.
   - **I.2**: Nextflow's own records (trace, report, log, the events its nf-tower plugin emits)
     are the truth about a run; Seqera Platform's, while the plugin still uses it. Nothing in this
     repository keeps a second copy; no submission script of our own, no state machine, no
     monitoring daemon beyond allow-listed channels; Seqera's nouns where the backend is Seqera.
     The platform's run index (rebuildable, records win) is *not* written in as a rule yet: it
     goes to ROADMAP "Principles waiting for a check" until its rebuild test exists (Stage 2).
     Check unchanged: `tests/no_second_run_state_test.sh`.
   - I.2 also says: where Seqera's display and Nextflow's own records disagree, Nextflow's
     records win.
   - **Safety Net: unchanged, word for word** (scope and four rules). "Gates live in the
     platform's tool layer" has no check yet, so it goes to ROADMAP "Principles waiting for a
     check" (Stage 1–2), not into the constitution. The amendment record says so, and says that
     scope condition 3 names only Seqera / Tower MCP tools today; whether a call to the platform's
     own MCP tools counts as "in use" is decided by the amendment that moves a gate there.
   - **Amendment record 3.0.0 (2026-10-08)**: rationale (his decision, ADR 0004/0005), what
     changes, impact on existing deployments (none: no hook, script or command changes), version,
     approval (maintainer merges). Footer: `**Version**: 3.0.0 | **Ratified**: 2026-09-28 |
     **Last Amended**: 2026-10-08`.
   - Principle 2's rationale sentence citing ADR 0001 now cites 0004.
6. **`docs/PRINCIPLES.md`**: invariants 1 and 2 (section A) restated to match 3.0.0 (reasoning,
   not new rules); "Where each piece belongs": the four "not an MCP server" reasons replaced by
   "the platform is an MCP server, because any harness must be able to call it; judgment stays in
   skills, MCP tools only act" — the old reason that a tool cannot carry judgment is kept, as the
   reason for that split.
7. **`docs/LAB_AGENTS.md`**: R7 verdict → "Reversed by ADR 0004"; §8 rewritten the same way;
   the H3 trigger paragraph kept as history.
8. **`docs/ROADMAP.md`**: Positioning / "What is sold" rewritten for the platform (hosted service
   first, box later); the 2026-09-29 "Order changed" note kept as history but marked superseded
   by the 2026-10-08 order and pointing at ADR 0004; the six existing waiting rows re-staged to
   the new numbering, and "any AI host without the safety net may query but never launch or
   delete" rewritten so it does not contradict gates in the tool layer (a host reaches launch and
   delete only through tools that carry their own gate); stages replaced by 0–5 from the handoff (0 docs; 1 station agent,
   feature 007; 2 platform core 008–010; 3 web 011–013; 4 cloud compute; 5 model-neutral
   shipping), each with its done-when; "dropped" line (old local progress page, old Codex
   adapter); line A (2.17.0 to the trial lab) unchanged; local-model evaluation section kept under
   Stage 5; waiting list gains: platform index rebuildable (Stage 2), platform stores metadata
   only and never a site credential (1–2), platform write tools refuse without a confirmation
   step (1–2), PI / member roles enforced (2); open questions gain: NCHC M6 (may a login node
   keep a process running; is automation on a shared account allowed).
9. **`docs/POSITIONING.md`**: one-line positioning → 台灣版 Seqera; core features rewritten
   around platform + MCP + bring-your-own harness; competitor table gains Seqera MCP (no
   confirmation mechanism in its docs), pynf-agent, Agent Skills standard, MCP Apps, MadCowork
   (marked: only `madcowork-module-spec` found; product claims from word of mouth, no public
   source); a section "十個突破點" from the direction plan, marked 推論 where it is.
   Also: the "宿主與本地模型" section's "產品的本地模型跑在 Codex 上" becomes past decision
   superseded by revised ADR 0003 (any MCP client; local model at Stage 5).
10. **`docs/SEQERA_PARITY.md`** (new): the 84-item table as a checklist, with the four items the
    new direction turns into "Build". Source line: compiled 2026-10-08 from Seqera's public
    documentation by the development lead (the maintainer's direction plan, outside this repo).
12. **`CLAUDE.md`, `README.md`**: one sentence each, so neither restates principles 1 / 2 in the
    old form. CLAUDE.md:10 and README.md:57 say what 2.17.0 does (Seqera Platform is the backend
    it uses, Nextflow's own records the truth underneath) and point at constitution 3.0.0. No
    other rewrite.

Every document that plans new work (ADR 0004, ROADMAP) names all three: development and testing
never go through Seqera's Services, its MCP server, or `tw` (his example, verbatim scope).
ADR 0002 itself is not edited; ADR 0004's Consequences may mention it.
Manual TCs (consistency read) are judged by the reviewer's reading at acceptance; no new
Procedure in `docs/TESTING.md`.
11. **`CONTEXT.md`**: terms Platform, Station agent, Run index, MCP tool layer.

## Tests (executor's part)

The suite checks the constitution's text in places. Expected to go red and be fixed:
- `tests/constitution_scope_test.sh`: version line 2.1.0 → 3.0.0, Last Amended 2026-10-08.
- `tests/no_second_run_state_test.sh`, `tests/scripts_name_their_alternative.sh`: header comments
  quote the old wording of I.2 / I.1; reword to 3.0.0. Behaviour unchanged.
- Whatever else the reviewer's test cases require (e.g. ADR 0001 marked superseded, 0004/0005
  exist, no document left saying "Not an MCP server" as a current rule).
- `tests/constitution_checks_exist_test.sh` must still count 14 rules.

## Done when

- `bash tests/run_all.sh` green in WSL.
- The reviewer's acceptance passes, including a consistency read across constitution, ADRs,
  ROADMAP, POSITIONING, PRINCIPLES, LAB_AGENTS, CLAUDE.md, README.md (this is what
  `/speckit-analyze` would check; there is no spec/tasks pair for an amendment).
- PR opened, not merged.

## Out of scope

Any code for the platform, the station agent or the MCP server; changing any hook, script,
command or skill; README / CLAUDE.md rewrites (they describe 2.17.0, which is still what ships);
ADR 0002 itself; a release. (CLAUDE.md / README.md: only the one sentence each in item 12.)

## Revision 2026-10-09: the maintainer's review of PR #72

His answers, in his words: 「1. 保留 2. 不要特別寫到重做 只說參考 3. 也做聊天介面 可接模型 同意merge」.

1. ROADMAP "Line A is unchanged…" sentence: kept as written (it is new text, not a copy of main;
   TC-032's "same as main" premise is replaced by "the sentence is present").
2. ADR 0004 Consequences: the sentence about one person rebuilding part of a company's product
   is removed; it now says Seqera Platform is the reference, narrowed to what a lab here uses.
3. The platform gets its own chat (web, Stage 3, feature 014) that connects to the model the
   user chooses (their own API key or a local model) and reaches the platform only through the
   same MCP tools; bring-your-own harness through MCP stays. Edited: ADR 0004 (title, intro,
   his 10-09 words, a "How it is built" bullet, Considered Options: "only MCP, no chat" replaced;
   "general-purpose harness of our own" still rejected), ADR 0003 (the chat is one more host),
   ROADMAP (Positioning, flow step 1, Stage 3 = 011–014), POSITIONING (one-liner, feature 2),
   CONTEXT (Platform), SEQERA_PARITY (Co-Scientist row gains Build, not ★: the ★ count stays 4),
   constitution amendment record rationale (one sentence). Safety Net and principles unchanged.

Tests to change: TC-012 (rejected options), TC-013 (cost sentence gone, "reference" present),
TC-026 (one-liner/feature 2 wording), TC-032 (premise), TC-035 (no longer "no chat anywhere":
the chat is planned, calls only the MCP tools, and no general-purpose harness is planned), plus
a new TC for the chat's three properties (own page in Stage 3, user-chosen model paid by the user,
only through the MCP tools) in ADR 0004 and ROADMAP.
