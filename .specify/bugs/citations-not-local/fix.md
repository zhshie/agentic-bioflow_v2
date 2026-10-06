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

## Round 2 (independent acceptance rejected the first fix)

Test first: RED commit, then the fix. The same acceptance also covered #25's test.

| Finding | Change |
|---|---|
| HIGH 1: an HTML 200 (captive portal) was cached for good and shown as the Source | Every file is checked before it is used or kept: CITATIONS.md must parse to at least one tool entry, the template must have its `data:` block, neither may be empty. A body that fails is not cached; the Notes say the file fetched from `github.com/<repo>@<rev>` "is not a CITATIONS.md (..., starts: '<html>...')". The same check runs on local and cached copies, so a zero-entry file (including one cached by the first version) is reported, never named as a Source, and a bad cached copy is fetched again. |
| HIGH 2: the #25 test was vacuous outside Git Bash | `tests/on_site_parallel_test.sh` now sets `ssh_control_path: ~/.ssh/cm-%r-%h-%p`, so the literal `~` reaches `CP` on Linux/WSL too. Verified red against a /tmp copy with `SLOTS_DIR="${CP}.slots"` restored (see suite notes in the report). |
| MED 3: branch revisions cached forever | Only a full SHA or a version tag (`3.14.0`, `v1.2.3`) is final in the cache. A branch, a `dev` version or anything else is fetched every build; if that fetch fails the cached copy is used with a Notes line that it may be out of date. |
| MED 4: guards with no failing test | Cases added for: `..` in a revision (`a/../b`), characters outside the allowed set, `None`/`null`/`~` as revision, `v1.2.3` retried as `1.2.3`, a SHA that 404s never retried as `v<sha>` (digit-leading SHA, so a rewrite would show), `..` as the repo part, empty body. Reviewer's mutation script `abf_accept_B/m.sh` re-run: see report. |
| MED 5: real curl path untested | `tests/methods_text_fetch_test.sh` puts a fake `curl` on PATH: 200 (URL checked), 404, another status, network failure with curl's message, and the HTML-200 case end to end (nothing cached). |
| LOW 6: no root means a refetch every run | Now also a Notes line ("not kept and will be fetched again on every build"), and listed here as a known limit. |
| LOW 7: HOME unset gave a slot dir under `/` | `scripts/on_site.sh` exits 2 with a message naming HOME and `ssh_control_path`; tested. |

Known limits: with no deployment root, or an unwritable cache, each build fetches again. A cached release-tag file is trusted forever; if a tag is ever force-moved upstream, delete `<root>/cache/pipeline_files`.
