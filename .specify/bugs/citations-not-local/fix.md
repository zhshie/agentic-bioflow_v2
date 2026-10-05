# Fix: citations-not-local (#4)

- **Branch**: `fix/user-folder-audit2`
- **Changed**: `scripts/methods_text.py` (new `PipelineFiles`, `--cache-dir`, `--fetcher`), `scripts/build_package.sh` (passes `<root>/cache/pipeline_files`), `commands/finish.md`, `docs/FINISH.md`, `docs/SETTINGS.md`, headers of `scripts/methods_text.py` and `scripts/detect_conditions.sh`, `tests/methods_text_fetch_test.sh` (new)
- **Constitution**: III.7 (a person can finish without the maintainer); V (write only where the deployment owns); I.1 (reuse `launch`'s own read from the pipeline's repository)

## What changed

- `CITATIONS.md` and `assets/methods_description_template.yml` are resolved in order: `~/.nextflow/assets` (read only), the deployment's cache, then a fetch from `raw.githubusercontent.com/<owner>/<repo>/<revision>/<path>`. Pipeline and revision come from the run's own versions file (`collect_provenance.py`'s workflow block); the user supplies nothing.
- The fetch is the same curl read `scripts/prepare_launch.sh` uses, so it takes the same `https_proxy` where finish runs behind the egress relay (`githubusercontent.com` is on the relay's allow-list already).
- The cache is `<root>/cache/pipeline_files/<owner>/<repo>/<revision>/<path>`, written atomically. Without a root, a fetched file is used once from a scratch directory that is removed at exit. Nothing is ever written under `~/.nextflow`.
- A commit SHA is used exactly as recorded. A tag recorded as `1.2.3` is retried as `v1.2.3` (and the reverse) only after a 404.
- The template is fetched only when the quality report did not already render the paragraph.
- Failures never stop the build: no revision, name not `owner/repo` (or containing `..`), 404, and network failure each leave `[CITATION NEEDED]` and a Notes line with the real reason. The old "under ~/.nextflow/assets" wording is gone; the note still starts "no CITATIONS.md for <pipeline>".
- The Software section's `Source:` line now names `github.com/<repo>@<revision> <file>` when the file was fetched.
- `--fetcher <cmd>` / `$ABF_PIPELINE_FETCHER` (`off` disables) replaces the network read; it is how tests run with no network. Four existing tests that build a package set it to `off`.
- Headers: both scripts now open with `# Nothing existing: <why>`; the earlier in-repo "Not ..." comparison is kept as prose under "Why it does not ...". Checked by running the `fix/constitution-checks` version of `tests/scripts_name_their_alternative.sh` against this tree: neither file is reported (the test itself is not copied here).

## Evidence

- `tests/methods_text_fetch_test.sh`: 15 cases, red on `d2afe16` (14 failed, `--cache-dir` unknown), green after. Cases: success, template fetched too, source named, cache written and nothing under `~/.nextflow`, second run makes no fetch call, local copy wins, 404, offline, SHA as given, tag with/without `v`, missing SHA not retried, non-`owner/repo`, `..` name, no revision, template skipped when the report rendered it, `build_package.sh` cache under the root.
- Full suite in WSL: see the PR report.
- Not tested (no network allowed): the real curl path against GitHub. It is the same command line shape as `prepare_launch.sh`'s; the first real `finish` is the check.
