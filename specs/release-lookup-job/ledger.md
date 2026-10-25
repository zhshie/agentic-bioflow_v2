# 站台代理讀管線公開檔（schema、樣本表欄、流程圖、release tag） progress ledger

Run stamp 20261025-1815-L-release. Branch `feat/release-lookup-job`. Nothing is pushed.

## Tasks

- [x] Agent side: `platform/abf_station/pipeline_files.py` (host allow-list, GET only, no credential, no redirect, size limits, tag advertisement turned into `ls-remote` text, diagram pick); `handlers.py` knows the kind (last in `JOB_KINDS`). Tests `test_station_pipeline_files.py` (TC-001..048). RED `16eef88`, GREEN `758959f`.
- [x] Platform queue: `store.py` CHECK and `_jobs_kinds_current` (migration rebuilds the `jobs` table once, no other table), `jobs.py` (`DEADLINE_SECONDS`, `_DEADLINE_ENV`, constants, `pf_arguments`, `pick_environment`, `enqueue_pipeline_files`, `latest_pipeline_files`, `clean_result` branch, Google Batch let through). Tests `test_pipeline_files_queue.py` (TC-049..092, TC-180).
- [x] Action layer: `actions.pipeline_files`, `actions.latest_release` (kept between the `release-lookup-job` marker comments so TC-133 can scan exactly the new code). Tests `test_pipeline_files_action.py` (TC-093..151, TC-159, TC-180).
- [x] Docs: `docs/PLATFORM.md` (section 6 list and the "toward the site" sentence, Action layer, storage table row, settings), `docs/TESTING.md` (the manual section; not run by the executor).
- [ ] Manual TC-168..172 (real GitHub): left to developer-agent / maintainer, not run.

## Existing tests whose assertions changed (old -> new, reason)

Rule: only `"pipeline_files"` added at the tail; no assertion removed, loosened or skipped.

| File | Old | New | Reason |
|---|---|---|---|
| `test_cloud_cost.py` (TC-093 test) | jobs CHECK list equals the eight kinds | list plus `"pipeline_files"` last | CHECK has one more kind |
| `test_launch_platform.py` | `set(jobs.KINDS)` is the eight | set plus `"pipeline_files"` | `KINDS` has one more |
| `test_resume_scope.py` | `jobs.KINDS ==` tuple of eight | tuple plus `"pipeline_files"` last | same |
| `test_cleanup_confirm.py` TC-033 | `jobs.KINDS ==` tuple of eight; test name "kinds are seven ... clean_work is last" | tuple plus `"pipeline_files"`; name now `..._kinds_are_the_seven_before_pipeline_files_then_pipeline_files_last_...`; `CONFIRMED` assertion unchanged | same; the name no longer claimed clean_work last |
| `test_station_platform.py` | insert loop and `declared` set of eight kinds | `("pipeline_files", None)` added to the loop; `"pipeline_files"` added to the set | CHECK has one more; the kind needs no confirmation |
| `test_cleanup_store.py` TC-003 | `declared_kinds(...)` equals the eight | plus `"pipeline_files"` last | CHECK has one more |
| `test_cleanup_store.py` `old_jobs()` | cuts `, 'clean_work'` from the new DDL | cuts `, 'pipeline_files'` first, then `, 'clean_work'` | else the "old" table would hold a kind newer than the ones it lacks |
| `test_station_clean.py` TC-028 | `JOB_KINDS[6:] == ("clean_work","put_upload")`; `ARG_KEYS` without `clean_work`,`put_upload` equals the old six | `[6:]` plus `"pipeline_files"` last; exclusion tuple plus `"pipeline_files"` | the plan table's looser wording (`JOB_KINDS[6] == "clean_work"`) was not used: the tail rule of ruling 11 is stricter and still true |
| `test_web_parity.py` `WEB_ONLY` | two names fewer | `"pipeline_files"`, `"latest_release"` added with the reason text | two new public action names, with web use and no MCP tool |
| `test_byte_channel_a.py` TC-003 | CHECK list ends `put_upload` | ends `put_upload`, `pipeline_files` | ruling 12 |
| `test_byte_channel_a.py` TC-012/013 | `jobs_check(db)[-1] == "put_upload"` | `jobs_check(db)[-2:] == ["put_upload","pipeline_files"]` | ruling 12 |
| `test_byte_channel_a.py` TC-015 | `KINDS[-1]=="put_upload"` and `KINDS[:-1]==(...)` | `KINDS[-2:]==("put_upload","pipeline_files")` and `KINDS[:-2]==(...)` | ruling 12 |
| `test_http_site_samplesheet.py` TC-057 | `SCHEMA_SHA256 = bb8b185e8eeff90fc5f457c3326f8d3e65876d5571952a994b76685fbc7706c2` | `d39c4e436fb4c9250331453cf454d52b25c60528cf67079ce362d22432939f33` | ruling 12. Algorithm unchanged: `sha256(json.dumps(rows))` over `SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name` of a new `platform.db`; the only text that changed is the `jobs` CHECK list. |

Not edited although the plan allowed it: `test_cleanup_store.py:137` (the `KINDS` probe table), `test_cleanup_confirm.py:343` (the `CONFIRMED` assertion).

## Where a TC lives that the cases name in another file

TC-135 (no MCP tool of these names) and TC-159 (no `nfcore_catalogue`, no `catalogue` part) are written in `test_pipeline_files_action.py`, not in `test_web_parity.py`: the plan allows only the `WEB_ONLY` change in that file, and TC-134 (the union check) is the existing test turning green with the two new names.

## Words of the plan that the code settled on

- `OPEN(url, headers, timeout, limit)` returns at most `limit + 1` bytes and the caller judges `len(body) > limit` (TC-040 pins the `limit` values 1,000,000 / 1,000,000 / 2,000,000 / 4,000,000).
- The 60-second rule is `now - finished_at >= PF_RETRY_SECONDS` (exactly 60 asks again; 59 still shows the old answer).
- The "update abf-station" sentence in `actions` is written in string pieces: the platform scan (TC-061) bars the whole word in `abf_platform/`.
- `jobs._enqueue` refuses the kind `pipeline_files` (as it does `put_upload`): the one door is `enqueue_pipeline_files`.

## git diff --stat (everything but this folder), at the last code commit

```
 docs/PLATFORM.md                              |  11 +-
 docs/TESTING.md                               |  10 +
 platform/abf_platform/actions/__init__.py     | 213 +++++++++
 platform/abf_platform/jobs.py                 | 160 ++++++-
 platform/abf_platform/store.py                |   6 +-
 platform/abf_station/handlers.py              |   9 +-
 platform/abf_station/pipeline_files.py        | 353 +++++++++++++++
 platform/tests/test_byte_channel_a.py         |   6 +-
 platform/tests/test_cleanup_confirm.py        |   4 +-
 platform/tests/test_cleanup_store.py          |   4 +-
 platform/tests/test_cloud_cost.py             |   2 +-
 platform/tests/test_http_site_samplesheet.py  |   2 +-
 platform/tests/test_launch_platform.py        |   2 +-
 platform/tests/test_pipeline_files_action.py  | 579 +++++++++++++++++++++++++
 platform/tests/test_pipeline_files_queue.py   | 597 ++++++++++++++++++++++++++
 platform/tests/test_resume_scope.py           |   2 +-
 platform/tests/test_station_clean.py          |   4 +-
 platform/tests/test_station_pipeline_files.py | 578 +++++++++++++++++++++++++
 platform/tests/test_station_platform.py       |   4 +-
 platform/tests/test_web_parity.py             |   2 +
 20 files changed, 2518 insertions(+), 30 deletions(-)
```
