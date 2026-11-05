# Cloud-burn reports, 2026-11

One line per report: id, title, summary.

- AR04 - Adversarial review of oauth.py, http_auth.py, agents.py, receiver.py: 12 surviving findings, led by an unauthenticated way to fill the OAuth pending-consent table, an unbounded rate-cap address table, and a run-name forgery by a general run token.
- AR05 - Adversarial review of confirm.py, mcp_server.py, guidance.py, elicit.py: 11 surviving findings, led by two P1s (a cancel job that misses its deadline stays queued forever; an owner cannot cancel their own run seven days after hand-over).
- AR07 - Adversarial review of abf_station handlers.py, rules.py, fetch.py: 17 surviving findings, led by fetch never returning the trace of a platform-launched run and a late site inventory discarding a passing preflight.
- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
