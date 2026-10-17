# Plan W0: ROADMAP and sibling docs follow ADR 0009 (web as three panes)

- **Slug**: w0-adr0009-followthrough
- **Branch**: `docs/w0-adr0009-followthrough`, base **`v3`** (after #114, ADR 0009)
- **Created**: 2026-10-17 by the developer-agent; slicing in the workspace file `memory/handoff/2026-10-17-web-slicing.md`
- **Tier**: C (direction text pinned by tests; ADR 0009 says rewording ROADMAP is a separate change the maintainer approves). The maintainer merges.

## 給維護者
1. 這次只改文件：把開發路線圖（ROADMAP）和幾份說明改成跟你 10-17 定的三欄網頁一致——不再有獨立「儀表板頁」、兩種角色延後、Studios 和「專案／分析」各自成為一個功能。
2. 沒有改任何程式、憲法或安全關卡。
3. 被測試釘住的舊句子，每一句改了什麼、為什麼，都記在進度帳本。

## Facts (origin/v3 after #114)
- `docs/ROADMAP.md:27` "Who: the PI pays and sees the whole lab"; `:46` Stage 2 row incl. "010: the two-role lab" and done-when "the PI sees it on the web"; `:47` Stage 3 row (011 dashboard and run detail, 012 launch form/datasets/SU estimate with a cap, 013 reports and package, 014 chat) and its done-when; `:96` waiting-list row "PI and member roles are enforced … 2". (Re-verify line numbers after #114.)
- `docs/POSITIONING.md:18`, `:31`: Data Explorer / Studios "not done"; dashboard / PI-member wording.
- `docs/adr/0004-self-hosted-platform-mcp-first.md:59`: "Studios: rejected" (pinned at `tests/platform_direction_docs_test.sh:175`).
- `tests/platform_direction_docs_test.sh`: `:274` (role row), `:471-472` (010 and Stage 2 done-when), `:474-476` (011/012/013 wording), `:478-479` (Stage 3 done-when, "no figures from web pages"); `:188-189`, `:344` (ADR 0005 PI text; SEQERA_PARITY counts A16 B11 C1 D5 E9 F13 G2 H7 I3 J9 K7) must stay; `:392-400` (014 chat) must stay.
- ADR 0009 (merged in #114): three panes; Project = the project folder; analysis = one thing from picking a pipeline to downloading results, resume/relaunch = attempt N; board stops only at the launch confirmation and "do downstream?"; no Data Explorer, no Dashboard page; uploads via the station agent (≤ ~2 GB from the web); cost per compute environment (NCHC SU and cloud money apart); cloud cap per person per month, number set when an account opens; dev mode no NCHC SU cap; all nf-core pipelines, 16S verified and prefilled; Studios (RStudio, Jupyter) in v3.0.0, default on the person's own computer, embedded; no roles, each person sees only their own runs (ADR 0005 two roles postponed); v3.0.0 includes the website.

## Design decisions (developer-agent)
1. Keep stage numbers and feature numbers 011–014 where ADR 0009 does not contradict them; add rows, do not renumber.
2. Stage 3 row: 011 = web shell, right pane (progress of all analyses), projects and analyses, run detail and failure sentence (011a–e); 012 = settings and guided setup, launch stage, uploads (012a–d); 013 = results and finished/package (013a–b); 014 = chat, unchanged. Studios gets its own feature number **016** (015 is Jev). Stage 3 done-when: a person with no AI completes setup → launch → running → results → downstream (in a Studio) → finished from the web alone.
3. 010 (two-role lab) becomes "postponed (ADR 0009)"; Stage 2 done-when "the student sees it on the web". `:27` "Who" paragraph: one person per account, sees only their own runs; the PI view is postponed with roles.
4. "SU estimate with a cap" (012) is reworded: cost shown per compute environment; cloud cap per person per month (number set when an account opens); no NCHC SU cap in dev mode.
5. Waiting list: the role row is re-staged "postponed (ADR 0009)"; add one row "owed parity — every action has an MCP tool and a web route; the owed list only shrinks" (its check arrives with 011a's parity test).
6. ADR 0004: add one line under the Studios item: "Superseded for Studios by ADR 0008 and ADR 0009." The pinned sentence stays.
7. POSITIONING `:18`, `:31`: Studios is in v3.0.0; Data Explorer and a dashboard page are not built (the right pane replaces the dashboard); roles postponed.
8. Record the maintainer's open questions in ROADMAP's open list (not decided here): account creation for the hosted service; whether runs without a recorded person are shown; whether uploads/downloads may pass through the hosted platform; whether each resume/relaunch needs the confirmation page; Studios on NCHC (a second submission path, needs a constitution amendment); cloud account and monthly cap number.
9. Do not touch the constitution, hooks, `PLATFORM.md`, SEQERA_PARITY's counts or Done ticks, or any code.

## Changes, in order (red first)
1. Red: extend `tests/platform_direction_docs_test.sh` with cases expecting the new wording (Stage 2/3 rows and done-whens, 010 postponed, no "dashboard page" in ROADMAP, Studios = 016, owed-parity row, ADR 0004 pointer line while `Studios**: rejected` still present, POSITIONING no longer lists Studios as not done, SEQERA_PARITY counts unchanged). Run → red; record in the ledger.
2. Rewrite only the pins named under Facts that the new wording breaks (`:274`, `:471-472`, `:474-476`, `:478-479`); for each: old expectation, new expectation, reason in the ledger. No other assertion is deleted or loosened.
3. Edit `docs/ROADMAP.md`, `docs/POSITIONING.md`, `docs/adr/0004-…md` (one line).
4. `bash tests/run_all.sh` green (WSL).

## Not in this PR
- Any code, the constitution, `PLATFORM.md`, the parity test itself (011a), SEQERA_PARITY ticks, any decision on the open questions.

## Constitution Check
- No principle or Safety Net text changes. Docs-only; pinned wording changed with the maintainer's merge (tier C).
