# Jev (TypeSafe) as an optional, off-by-default triage step for FAILED runs

Decided by the maintainer on 2026-10-16 (feature 015, `specs/015-jev-triage/`). It changes one line of
`docs/POSITIONING.md`, which until now rejected Jev outright.

## The problem this record answers

`docs/POSITIONING.md` listed Jev (TypeSafe System One) among the things not to build on: it is a paid
cloud API at `api.typesafe.ai`, no self-hosted version could be found, and "does not retain data" is
offered to enterprise customers only. That conflicts with "data does not leave the lab" and with
"depend on nobody else's service" 〔docs.typesafe.ai/api, docs.typesafe.ai/legal〕.

Meanwhile one step of the runs flow is the slowest and most reading-heavy part of debugging. When a
run fails and the site refused nothing and the task did not die with exit 137, the AI reads the whole
`.command.err` of the failing task and guesses. A classifier that returns one of a few categories from
the last lines of that file is a small, well-defined job, and the cost of it being wrong is a wasted
read, not a wrong action.

## What the maintainer said (2026-10-16, after reading the evaluation)

- 「只要有價值就設計，若有風險未來考慮變成本地端」 - design it if it has value; if the risk bites, move it
  to a local service later.
- 「使用者自備」 - the user brings their own key.
- 「一致率 ≥ 90%」 - agreement of at least 90% with the approved labels before it is called recommended.
- 「只做除錯」 - debugging only, not the other places it could have been used.
- 「題庫我核可了」 - the 42-item question bank is approved.

## Decision

1. Jev is an **optional** step in the runs skill's FAILED flow, **off by default** (`jev.enabled`), and
   the user supplies their own key (`TYPESAFE_API_KEY`, or a mode-600 `.typesafe_key` beside the
   settings file). Nothing in the repository holds a key or turns it on.
2. The first use on a machine **says what is sent** (the last 200 lines of the failing task's
   `.command.err` plus its exit code, to `api.typesafe.ai`; it may contain paths and sample names;
   retention is not guaranteed for non-enterprise keys) and how to turn it off. Only those two fields
   are ever sent.
3. It **fails open and says so**: off, no key, over the daily cap (default 500), timeout, bad answer or
   a missing tool each print one sentence and the flow continues as before. There is no fallback to
   another model.
4. It **only points**. A category leads to a page of the runs skill; every step that needs the user's
   consent still stops for it. It changes no state, so it is not part of the action layer of ADR 0006:
   it stays a script call (`scripts/jev.sh`) inside the skill, not an MCP tool.
5. The service URL is `JEV_ENDPOINT`, so a local, compatible service can replace it later without code
   changes - the maintainer's "move it to a local service" route.
6. It is called "recommended" only after the maintainer runs `scripts/dev/jev_replay.sh` with a real
   key and the 37 scorable items agree at least 90% (34 of 37).

## Consequences

- A deployment that never sets `jev.enabled` behaves exactly as before; what the user sees is unchanged.
- The risk accepted is outbound error text for users who opt in, disclosed before the first send.
- The question bank is 39 synthetic and 3 PITFALLS-derived items; real cluster samples will be added to
  `specs/015-jev-triage/labels.json` when available.
- Reversing this is deleting `scripts/jev.sh`, the step in `skills/runs/SKILL.md` and its categories.
