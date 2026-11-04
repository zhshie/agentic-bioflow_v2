# Cloud-burn reports, 2026-11

One line per report: id, title, summary. Reports only; they change no repository file.

- [AR01](AR01.md) - adversarial review of `platform/abf_platform/actions/__init__.py`: 11 surviving findings, led by a month SU total that is definite while one of its runs is unknown.
- [AR02](AR02.md) - adversarial review of `platform/abf_platform/jobs.py` and `store.py`: 12 surviving findings, led by pruned refused launches freeing a run name and late answers applied to expired jobs.
- [AR03](AR03.md) - adversarial review of `compute_envs.py`, `validate.py` and `cloud_store.py`: 13 surviving findings, led by `snapshot()` crashing on a `sqlite3.Row` with a field equal to `config`.
