# 結果頁點進資料夾、下載單一結果檔 progress ledger

> Executor: stamp 20261029-1525-L37. Branch feat/results-files. Process: RED commits then GREEN commits per group (agent, then platform and web).

## Tasks

- [x] **Agent** `read_run_file`: `platform/abf_station/readfile.py` (new), registered in `handlers.py` (JOB_KINDS, ARG_KEYS, one dispatch line, line-1 comment "ten"). Tests: `platform/tests/test_station_read_run_file.py` (TC-028..034, 038, 041, agent half of 015).
- [x] **Queue** `jobs.py`: kind, 60 s deadline (`ABF_PLATFORM_DEADLINE_READ_RUN_FILE`), constants (`RUN_FILE_MAX_BYTES` = 26,214,400, cache 600 s), `run_file_path_problem`, `enqueue_read_run_file` (refuses: bad path, not the caller's run, no folder on record, non-Slurm environment, offline agent), `latest_run_file`, `clean_result` branch (size and base64 length must agree, else `bad_answer`). `store.py`: CHECK list and `_jobs_kinds_current` gain the kind (older database is rebuilt, rows kept; no new function in the token section, ruling 7).
- [x] **Actions** `run_file` (new, never waits) and `run_outputs(subpath=...)` (adds `sub`, `bad_path`, `enter`, `download`, `too_large`, `max_bytes`, `top`).
- [x] **Web** `GET /run/file` (`web.py: run_file_get`), `web_board.py`: folder links, breadcrumbs, "下載" column, the two report cells, download pages, `download_headers`; STRINGS (zh and en). STYLE and CSP untouched.
- [x] **Docs** `docs/PLATFORM.md` ("下載結果檔"), `docs/TESTING.md` ("結果頁下載", includes the 390 px step).
- [x] **Tests (new)** `platform/tests/test_results_files.py` (TC-001..027, 034, 035, 037..044, doc checks for 036 and 045).

## Existing tests changed (only added to, or one literal brought up to date; none deleted, skipped or loosened)

| File | Change | Why |
|---|---|---|
| `test_byte_channel_a.py` | `jobs.KINDS[-2:]`/`[:-2]` to `[-3:]`/`[:-3]` with `read_run_file` last; the CHECK list gained `"read_run_file"`; the rebuilt-table tail check `[-3:]` | tenth kind |
| `test_byte_channel_b.py` | `handlers.JOB_KINDS[-3:]`/`[:-3]` | tenth kind |
| `test_cleanup_confirm.py` | `jobs.KINDS ==` tuple gained `"read_run_file"` | tenth kind |
| `test_launch_platform.py` | `set(jobs.KINDS) ==` gained `"read_run_file"` | tenth kind |
| `test_handlers_header.py` | `_kind_count() == 10` | tenth kind (line 1 of `handlers.py` now says "ten") |
| `test_web_parity.py` | `WEB_ONLY` gained `run_file` (no MCP tool) | TC-042 |
| `test_cleanup_offer.py`, `test_confirm_page.py`, `test_dataset_cli.py`, `test_owner_binding.py`, `test_web_board.py` | route lists gained `/run/file` (GET) | the one new route |
| `test_web_results_outputs.py::test_ro03_finished_listing_is_shown` | the name regex also reads a name inside a link; the "names are plain text, not links" check now covers files only (alpha, zeta), no longer the folder `dada2` | folder names are links by TC-001. The pinned grey "之後開放" assertions of `test_ro01_*` still hold (the cards stay grey while the first level is unknown, TC-026) |

`test_web_running.py` and the `test_aws_*`/`test_gcb_*` route files needed no change (they passed unchanged).

## Notes and questions

- **TC-016 vs TC-027.** TC-016 words the page "站台沒有這個檔案", TC-027 bans "這個" (DESIGN.md 用字). The page says "站台沒有此檔案。" (the ban wins; DESIGN.md is the maintainer's rule). Likewise "超" is banned in DESIGN.md but "超過 25 MB" is required by TC-004/014; only the word 超過 is used.
- **"三個值" of the job.** The job holds `ce` (the environment snapshot, which carries the name), `run` and `path`. For a resumed run (`<name>-aN`) the agent looks in `<workDir>/runs/<name>-aN` first and then in the folder of the run it continues.
- **Page of a run with no folder on record** is shown for a launch row whose folder is empty; a run with no launch row at all belongs to nobody and is the board's 404 (as on every page).
- **TC-043 "完整路徑".** The too-large page shows `<run folder>/results/<path>` built by the platform from its own launch record; the agent's path is not used.
- **STYLE / D13.** `web_board.STYLE` unchanged (sha256 pinned in the new test). No class was added: the crumb bar is `<nav class="ostat" data-part="crumbs">`.
- **Ruling 5.** `constitution_scope_test.sh` red in WSL is an environment matter; CI is the reference.
