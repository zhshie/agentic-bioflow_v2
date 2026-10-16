# Plan: constitution 4.1.0 — `skills/` is a home of judgment; ADR 0006; the roadmap for v3

Branch `amend-4.1.0-skills-home`, base `main`. Tier C: the maintainer approves and merges
(Governance). Written by the developer-agent on 2026-10-15. The decision itself is
`docs/adr/0006-four-entries-one-action-layer.md`, already on this branch; this plan lists the
edits that carry it into the constitution, the roadmap and the documents that quote them.

## 給維護者

1. 這支 PR 只動文件和測試裡的「釘字」（測試用來確認文件沒被偷改的固定句子）。plugin 的行為、hooks、scripts 一個字都不動；2.17.0 的使用者完全不受影響。
2. 憲法只做**小修**（4.1.0）：第 II.5 條原本說「判斷與流程住在 `docs/` 與 `scripts/`」，加上 `skills/`。為什麼只小修：憲法只收「已經有檢查」的規則，v3 那四條新原則（四個入口到同一個動作、閘門住在動作層、平台工具算在使用中、網頁與工具一一對應）還沒有檢查，先排進 roadmap 的「等檢查的原則」，等 009 做出檢查再隨它大修（號碼到時候依 Governance 決定）。
3. ADR 0006 是整個 v3 方向的紀錄（四層架構、人才能按 yes、平台要有公開網址、hook 與閘門對照表、v2／v3 分線）。你核的是它。

## 維護者的例子（原文，2026-10-15）

- 「只加 MCP 網址就能用」
- 「平台純粹靠GUI介面也要能使用」
- 「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」
- 網頁範圍：接受「setup→launch→runs→看報告→打包；畫圖走聊天」
- CI：「好，加 v3 分支觸發」

## What changes

### 1. Constitution (`.specify/memory/constitution.md`)

**Principle II.5, new text** (only the first sentence changes; the check is unchanged):

> - **5.** Judgment, procedure and site operations live in `skills/`, `docs/` and `scripts/`,
>   readable and runnable by a person or another model. Whatever AI host runs the tool, its own
>   capabilities (hooks, skills, commands or their equivalents) MUST be used fully.

(Only `skills/` is added to the list; the rest of the sentence keeps today's meaning. The verifier
noted that an earlier draft narrowed "site operations" to `scripts/` alone; that is withdrawn.)
>   *Check:* `tests/works_without_host_test.sh`: with `hooks/` and `.claude-plugin/` removed, the
>   system still works from `skills/`, `docs/` and `scripts/`: degraded, not equivalent, but usable.

**New amendment record**, appended after 4.0.0's and before `## Governance`, in the shape of the
3.0.0 record (Rationale / What changes / Impact on existing deployments / Version / Approval):

- Heading: `### 4.1.0 (2026-10-15): skills are a home of judgment; the platform has four entries`
- Rationale: quotes the maintainer's five decisions above; names `docs/adr/0006`.
- What changes: principle II.5 names `skills/` (its check already packs `skills/`); nothing
  else. The four v3 principles wait in `docs/ROADMAP.md` ("Principles waiting for a check") and
  join by the MAJOR amendment that ships with feature 009 (no number is promised: the next MAJOR
  after 4.1.0 is 5.0.0, and ROADMAP already names the run-index amendment as a candidate for it).
  The Safety Net is unchanged, word for word. The record must not contain the words `run index`
  (an existing test greps the whole constitution for them).
- Impact on existing deployments: None. No hook, script, command or skill changes.
- Version: MINOR, under Governance: a principle is expanded, none is removed or redefined.
- Approval: the maintainer approves and merges the pull request.

**Version line** (last line of the file): `**Version**: 4.1.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-15`

### 2. `docs/ROADMAP.md`

- Stage 2 row, 009 cell: becomes `009: the action layer (one function per action, called by the
  MCP tools, the web pages and the chat), the MCP server's write tools following Seqera MCP's
  tools plus `list_site_files`, `validate_samplesheet`, `estimate_su`, `read_task_log`,
  `run_downstream`, `build_package`; every write action's gate answered on a human channel
  (elicitation form or a confirmation page); OAuth 2.1 / personal-access-token authorization and
  the identity each token carries; the server's `instructions` and one prompt per skill mirroring
  `skills/`; the Skills over MCP endpoint; `skills/` copied into the package; the relay sending
  events to a public address`. The rest of the row stays. The done-when stays.
- Stage 3 row: 011–013 gain `, matching the actions one to one (parity test)`; 014 keeps its
  sentence verbatim (TC-022 pins it). Done-when gains a first clause: `A lab member with no AI
  tool completes setup → launch → runs → rendered reports → the package from the web pages alone
  (figures from scripts are made in the platform's chat or in a harness); ` before `Two members
  of the trial lab…`. (The parenthesis carries the maintainer's "畫圖走聊天".)
- After the "Dropped on 2026-10-08" paragraph, a new paragraph: `v2 and v3 (2026-10-15, ADR 0006):
  \`main\` is the v2 line until v3.0.0; v3 is built on the branch \`v3\`. v2 takes bug fixes and
  changes that make the Safety Net stricter, released as 2.17.x only when a fix affects a user.`
  The Line A sentence stays.
- "Principles waiting for a check" table: the row `Gates live in the platform's tool layer, so
  whichever host calls a tool meets the same gate; the plugin's hooks become callers` becomes
  `Gates live in the platform's action layer, which the MCP tools and the web pages both call,
  and a person answers each gate on a human channel; the plugin's hooks become callers` with the
  check `An unconfirmed launch is refused through the MCP tool and through the web route`. Three
  new rows: `Every entry (MCP client, web page, platform chat, shell) reaches the same action` /
  `A parity test: every action has an MCP tool and a web route, and \`mcp_server\` and the web
  import only \`actions\`` / stage 2–3; `A call to the platform's own tools counts as a session
  in use` / `The Safety Net's scope test covers the platform's tools` / 2; `The web pages and
  the tools match one to one` / the same parity test / 3.

### 3. `docs/POSITIONING.md`, point 2

The bold lead `平台只開 MCP，對話用你自己的 AI，或平台自己的聊天介面。` becomes `平台有四個入口：你自己的
AI（接 MCP 網址）、平台網頁、平台自己的聊天介面、命令列。` The sentence `沒有 AI 工具的成員，用平台網頁上的聊天介面，接自己選的模型（自己的 API key 或本地模型），它走的是同一組 MCP 工具（2026-10-09 加入，`docs/adr/0004`）。`
becomes `沒有 AI 工具的成員直接用平台網頁點選，不需要任何模型；想用對話的，用平台自己的聊天介面，接自己選的模型（自己的 API key 或本地模型），它走的是同一組 MCP 工具（2026-10-09 加入，`docs/adr/0004`；2026-10-15 四個入口，`docs/adr/0006`）。`
(the pinned substring `接自己選的模型（自己的 API key 或本地模型），它走的是同一組 MCP 工具` survives verbatim). The sentence `判斷留在 skill，MCP 工具只做動作，每個寫入動作都要你確認（`docs/adr/0003`）。`
becomes `判斷留在 skill，工具只做動作，每個寫入動作都要你本人確認——按 yes 的是人，不是模型（`docs/adr/0006`）。`

### 4. `CONTEXT.md`

- The `**MCP tool layer**` entry gains one sentence: `Since ADR 0006 the tools call the action
  layer; the gate lives there.`
- Two new entries in the same section, same shape: `**action layer** (動作層): one function per
  platform action (launch, cancel, list files…), called by the MCP tools, the web pages and the
  chat alike; the gate of a write action lives here. Planned (Stage 2, feature 009). _Avoid_:
  API, backend` and `**human channel** (人通道): the way a person, not the model, answers a gate:
  an elicitation form in the harness, or a confirmation page on the platform. The token is the
  record of that answer, not the answer. Planned (Stage 2). _Avoid_: confirmation token (when the
  act is meant)`.

### 4b. `docs/PRINCIPLES.md`, point 5 (line 67)

The sentence `Judgment, procedure and site operations live in `docs/` and `scripts/`, which a
person or another model can read and run directly.` becomes `Judgment, procedure and site
operations live in `skills/`, `docs/` and `scripts/`, which a person or another model can read and
run directly.` Nothing else in the point changes (Governance: PRINCIPLES.md restates the
constitution and must not differ from it).

### 5. ADR 0003 and ADR 0004

Each gains one line under its title: `Amended 2026-10-15 by ADR 0006: <one clause>` — for 0003
"gates live in the action layer the tools and the web pages call; a harness kit is not an
adapter"; for 0004 "the web pages are a non-AI entry to the same actions; the confirmation is a
person's act on a human channel". No sentence of either record is changed (TC-011 and TC-016 pin
them).

### 6. Pins in tests and documents (Governance: same PR)

- `tests/constitution_scope_test.sh` lines 29 and 31: `**Version**: 4.1.0` with the label text
  updated to mention 4.1.0; `**Last Amended**: 2026-10-15`. The 2.0.0 entry assertion stays.
- `tests/platform_direction_docs_test.sh`: TC-001 last line becomes the 4.1.0 line; TC-059
  `constitution 4.1.0` for CLAUDE.md and `the truth under constitution 4.1.0` for README.md;
  TC-023 expects the new "action layer" row text; a new assertion in TC-023 for each of the three
  new rows; TC-008's `nin "$RULES" 'tool layer'` stays and a sibling `nin "$RULES" 'action layer'`
  is added (the principles and the Safety Net still do not carry it); TC-026 (line 286) `has …
  '平台只開 MCP，對話用你自己的 AI，或平台自己的聊天介面'` becomes `has … '平台有四個入口：你自己的 AI（接 MCP 網址）、平台網頁、平台自己的聊天介面、命令列'`
  plus a sibling `hasnt "TC-026: the old 'MCP only' lead is gone" "$POS" '平台只開 MCP'`; the
  other TC-026 lines stay (their substrings survive).
- `CLAUDE.md` line 11 and `README.md` lines 56 and 58: `4.0.0` → `4.1.0`.
- `tests/works_without_host_test.sh` line 94: unchanged in this PR (`commands/*.md` still exist
  on `main`); the `v3` branch changes it when the files move.

### 7. Not in this PR

- No change to `commands/`, `skills/`, `hooks/`, `scripts/`, `platform/`, `.github/`. The
  maintainer's "好，加 v3 分支觸發" is delivered on the `v3` branch itself (its `tests.yml` lists
  `[main, v3]`; a push trigger is read from the branch being pushed, so `main`'s file need not
  change). ADR 0006 says so; this PR does not touch `.github/`.
- No change to `docs/LAB_AGENTS.md`, `docs/CONDITIONS.md`, `scripts/detect_conditions.sh` (ADR
  0006, Consequences: they change with feature 009's follow-up).
- No CHANGELOG (it starts on `v3`).

### 8. Fix round after `/code-review` (2026-10-15, developer-agent; two contradictions, one readability item)

- `docs/ROADMAP.md`, "Principles waiting for a check", the row `Every platform write tool (launch, delete,
  clear \`work/\`) refuses without the user's confirmation step`: its check `A test per write tool: a call
  without the confirmation token is refused.` becomes `A test per write tool: a call without a person's
  answer on a human channel is refused; the confirmation token is only the record of that answer (ADR 0006).`
  The *Note* sentence that follows stays verbatim. (Reason: the row beneath it says a token is not the
  confirmation; the two rows contradicted each other.)
- `CONTEXT.md`, `**MCP tool layer**` entry: `the tools only act, and each write tool carries its own
  confirmation gate. Planned (Stage 2). Since ADR 0006 the tools call the action layer; the gate lives there.`
  becomes `the tools only act. Planned (Stage 2). Since ADR 0006 the tools call the action layer; the gate of
  a write action lives there, answered by a person on a human channel.` (Reason: one entry said the gate is
  both in the tool and in the action layer.) TC-031's pinned sentence changes accordingly: the test asserts the
  new sentence and `nin` the old `each write tool carries its own confirmation gate`; `test-case.md` TC-031
  is updated with a one-line note "amended 2026-10-15 after /code-review".
- `tests/platform_direction_docs_test.sh`: every `ok`/`bad`/`has`/`inn`/`nin` label inside the 4.1.0 block
  is prefixed `4.1.0 ` (e.g. `4.1.0 TC-025: …`) so a failure line is not confused with the earlier
  amendment's TC-003…TC-029 labels in the same file. No assertion changes.

Rejected findings (recorded so they are not re-raised): ADR 0003/0004 bodies stay as written (an ADR is
amended by a note, not rewritten); MINOR is the conservative bump class; the `v3` CI trigger is on the `v3`
branch (pending push); the 16-row count is a pin like the version line and is updated by each amendment;
ADR context facts are dated statements; the confirmation page is listed in the 009 row.

## Red first

The verifier's test cases pin the new sentences; before the edits, `tests/platform_direction_docs_test.sh`
and `tests/constitution_scope_test.sh` fail on the version line and the new rows; after, the whole
suite is green in WSL (`bash tests/run_all.sh`).

## Test-case conventions for this amendment

Checks that compare the branch with `main` (Safety Net byte-identical, only three hunks in the
constitution, earlier records untouched) are marked 手動 and are run by the verifier in ACCEPTANCE
mode with the evidence in its report; they are not added to `docs/TESTING.md`, which is for
release walkthroughs on a site.

## Constitution Check

- Governance: rationale, impact assessment, version bump and every citing document in one PR — yes.
- 2.0.1: every rule names a check that exists — II.5 keeps `tests/works_without_host_test.sh`.
- Safety Net: unchanged, word for word.
- Principle 2: untouched.
