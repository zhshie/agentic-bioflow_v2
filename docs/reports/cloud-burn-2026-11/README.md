# Cloud-burn reports, 2026-11

One line per report: id, title, summary. Reports only; they change no repository file.

- [AR01](AR01.md) - adversarial review of `platform/abf_platform/actions/__init__.py`: 11 surviving findings, led by a month SU total that is definite while one of its runs is unknown.
- [AR02](AR02.md) - adversarial review of `platform/abf_platform/jobs.py` and `store.py`: 12 surviving findings, led by pruned refused launches freeing a run name and late answers applied to expired jobs.
- [AR03](AR03.md) - adversarial review of `compute_envs.py`, `validate.py` and `cloud_store.py`: 13 surviving findings, led by `snapshot()` crashing on a `sqlite3.Row` with a field equal to `config`.
- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
