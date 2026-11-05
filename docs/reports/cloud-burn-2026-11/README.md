# Cloud-burn 2026-11 reports

- MU01 - Mutation run: platform/abf_platform/common.py - 38 hand-made mutants, 13 killed, 25 survived (24 real, 1 equivalent); parse_iso_epoch, extract_error, run_failure_reason and token parsing are barely pinned by tests.
- MU02 - Mutation run: platform/abf_platform/validate.py - 48 hand-made mutants, 42 killed, 6 survived (5 real, 1 equivalent); gaps are mostly in extension-pattern comparison (multi-dot, case, hyphen).
- MU03 - Mutation run: platform/abf_platform/compute_envs.py - 101 hand-made mutants, 54 killed, 47 survived (44 real, 3 equivalent); Slurm limits, cloud workDir shapes and storage bookkeeping are unasserted.
- AR06 - Adversarial review of platform/abf_station/launch.py - 14 surviving findings; the top one is that a samplesheet cell outside the path-column heuristic (file:// URI, ../ path) passes both read-root locks and every cloud checker.
# Cloud-burn reports, 2026-11

One line per report: id, title, summary. Reports only; they change no repository file.

- [AR01](AR01.md) - adversarial review of `platform/abf_platform/actions/__init__.py`: 11 surviving findings, led by a month SU total that is definite while one of its runs is unknown.
- [AR02](AR02.md) - adversarial review of `platform/abf_platform/jobs.py` and `store.py`: 12 surviving findings, led by pruned refused launches freeing a run name and late answers applied to expired jobs.
- [AR03](AR03.md) - adversarial review of `compute_envs.py`, `validate.py` and `cloud_store.py`: 13 surviving findings, led by `snapshot()` crashing on a `sqlite3.Row` with a field equal to `config`.
One line per report: id, title, summary.

- AR04 - Adversarial review of oauth.py, http_auth.py, agents.py, receiver.py: 12 surviving findings, led by an unauthenticated way to fill the OAuth pending-consent table, an unbounded rate-cap address table, and a run-name forgery by a general run token.
- AR05 - Adversarial review of confirm.py, mcp_server.py, guidance.py, elicit.py: 11 surviving findings, led by two P1s (a cancel job that misses its deadline stays queued forever; an owner cannot cancel their own run seven days after hand-over).
- AR07 - Adversarial review of abf_station handlers.py, rules.py, fetch.py: 17 surviving findings, led by fetch never returning the trace of a platform-launched run and a late site inventory discarding a passing preflight.
- AR08 - Adversarial review of cloud_cost.py, su.py, web_cost.py: the SU card and cloud cap miscount (default_site pricing, partial sums, in-flight runs at $0, unpriceable tasks dropping a run), 13 surviving findings.
- AR09 - Adversarial review of web.py and web_board.py: exponent-form numbers sent as text, lost-run Resume offers the action layer refuses, SVG served without a sandbox CSP, shared login bucket behind a proxy, 15 surviving findings.
- AR10 - Adversarial review of web_settings.py, web_launch.py, web_upload.py, uploads_web.py, actions/uploads.py: same-name uploads overwrite registered dataset objects, resume-edit refuses its own untouched box, unregistered batches after job prune, 15 surviving findings.
- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
