# Ledger: mcp-gallery-actions (gallery slice 3, risk L)

Executor record, written for the acceptance reviewer. TC numbers are those of `test-case.md`. The full-suite verdict is the CI of the pull request (the local machine is loaded); the local run is noted in section (g).

## (a) `git diff --stat 53f3faab HEAD` (from the merge of origin/v3 this branch started from, to the GREEN commit; this ledger is not in it)

```
 CHANGELOG.md                                       |   1 +
 docs/PLATFORM.md                                   |   6 +-
 docs/TESTING.md                                    |  10 +
 platform/abf_platform/actions/__init__.py          |  21 +-
 platform/abf_platform/actions/chat_tools.py        |   5 +-
 platform/abf_platform/actions/figures.py           | 244 ++++++++-
 platform/abf_platform/confirm.py                   |   6 +-
 platform/abf_platform/mcp_server.py                |  31 +-
 platform/abf_platform/store.py                     |   9 +-
 platform/abf_platform/web.py                       |  55 ++
 platform/tests/mcp/snapshots/tools.json            |  83 ++++
 platform/tests/mcp/test_mcp_contract_tools.py      |   2 +-
 platform/tests/mcp/test_mcp_contract_writes.py     |  11 +-
 platform/tests/test_actions_layer.py               |   7 +-
 platform/tests/test_aws_ce.py                      |   2 +-
 platform/tests/test_aws_launch.py                  |   4 +-
 platform/tests/test_azure_ce.py                    |   2 +-
 platform/tests/test_azure_launch.py                |   4 +-
 platform/tests/test_azure_upload.py                |   2 +-
 platform/tests/test_chat_confirm.py                |   4 +-
 platform/tests/test_chat_tools.py                  |   8 +
 platform/tests/test_cleanup_store.py               | 112 ++++-
 platform/tests/test_dataset_launch.py              |   4 +-
 platform/tests/test_estimate_su.py                 |   2 +-
 platform/tests/test_gallery_change.py              | 552 +++++++++++++++++++++
 platform/tests/test_gallery_change_confirm.py      | 404 +++++++++++++++
 platform/tests/test_gallery_change_page.py         | 179 +++++++
 platform/tests/test_gcb_ce.py                      |   2 +-
 platform/tests/test_gcb_launch.py                  |   4 +-
 platform/tests/test_http_site_samplesheet.py       |   2 +-
 platform/tests/test_human_channel.py               |   4 +-
 platform/tests/test_k8s_ce.py                      |   2 +-
 platform/tests/test_keep_submissions.py            |   8 +-
 platform/tests/test_launch_e2e.py                  |   4 +-
 platform/tests/test_launch_platform.py             |   6 +-
 platform/tests/test_launch_profiles.py             |   4 +-
 platform/tests/test_mcp.py                         |  10 +-
 platform/tests/test_mcp_canvas_read.py             |   2 +-
 platform/tests/test_mcp_launch_pipeline.py         |   8 +-
 platform/tests/test_mcp_run_file.py                |   2 +-
 platform/tests/test_mcp_server_doc.py              |   4 +-
 platform/tests/test_oauth_mcp.py                   |   6 +-
 platform/tests/test_owner_guard.py                 |   4 +-
 platform/tests/test_pat.py                         |   2 +-
 platform/tests/test_publish_figure_confirm.py      |   2 +-
 platform/tests/test_resume_edit_params_platform.py |   4 +-
 platform/tests/test_resume_entrypoints.py          |   4 +-
 platform/tests/test_station_envs.py                |   2 +-
 platform/tests/test_station_launch.py              |   2 +-
 platform/tests/test_su_in_get_run.py               |   2 +-
 platform/tests/test_su_usd.py                      |   4 +-
 platform/tests/test_web_board.py                   |   2 +-
 platform/tests/test_web_guided_launch_preview.py   |   2 +-
 platform/tests/test_web_parity.py                  |   2 +
 tests/platform_storage_doc_test.sh                 |   2 +-
 55 files changed, 1783 insertions(+), 89 deletions(-)
```

Nothing under `.github/`, `hooks/`, `.specify/memory/constitution.md`, `.claude-plugin/plugin.json`, `platform/abf_station/`, `platform/abf_platform/jobs.py` or the CSS was touched. There is no new route (the route set of `web.py` is the one of slice 2) and no new dependency.

## (b) `confirm.py` and `store.py`: which lines changed and why

`platform/abf_platform/confirm.py` (`git diff -U0`: three hunks, 6 lines):

| line | change | why |
|---|---|---|
| 31 | `NO_JOB_KINDS = ("publish_figure",)` became `("publish_figure", "gallery_change")` | the one existing line that changed: the new kind queues no job, so `approve()` takes its writer branch. The contract (TC-086) names this value. |
| 130-131 (new) | `_without_content`: `if "figures" not in bundle: return dict(bundle)` | `approve()` rewrites the bundle through this helper after the writer ran; without the guard a gallery_change bundle would gain an empty `figures` key. A publish_figure bundle always has `figures`, so its path is unchanged. |
| 420-421 (new) | `facts()`: a branch `if row["kind"] == "gallery_change": return dict(bundle, what="gallery_change")` | the confirmation page and the repeated chat call read the stored request through `facts`; without a branch the kind would fall to the launch default (`bundle["pipeline"]`, KeyError, so None). |

Existing lines of `confirm.py` that changed: exactly one, line 31. Nothing in `approve`, `create_pending`, `describe`, `find_approved`, `find_attempt`, `find_cancel`, `forget_content`, `drop_figure_content` or `pending_figure_bytes` was edited.

`platform/abf_platform/store.py` (three hunks, 5 insertions and 4 deletions, all of them the new kind):

| line | change | why |
|---|---|---|
| 216-218 | the comment above `_CONFIRMATIONS_TABLE` names `gallery_change` | words only |
| 222 | `CHECK (kind IN (..., 'publish_figure'))` became `(..., 'publish_figure', 'gallery_change')` | the table a new database gets, and the one the migration builds |
| 608 | `_confirmations_current` also requires `'gallery_change'` in the table text | a database made by slice 1 is no longer "current", so `_migrate_confirmation_kinds` rebuilds it. The migration function itself is not edited: it copies by the column names both tables have, in one transaction, rolls back on any failure and checks `PRAGMA foreign_key_check`. |

The schema-diff guard `test_no_schema_change` (`test_mcp_launch_pipeline.py`) allows exactly these lines and no other: its list `PUBLISH_FIGURE_STORE_LINES` only gained the five new or changed lines, nothing was removed from it.

## (c) The migration, real output

Databases built by the test helpers (`test_cleanup_store.py`: `_publish_era` for slice 1's shape, `make_old` for the oldest) and opened with `store.connect_state`, in WSL:

```
== slice-1 database (kind publish_figure known, gallery_change not)
row counts before: {'confirmations': 1, 'jobs': 0, 'launches': 0}
row counts after:  {'confirmations': 1, 'jobs': 0, 'launches': 0}
confirmations rows identical (old columns): True
PRAGMA foreign_key_check: []  foreign_keys: 1
sqlite_master entries that differ: ['confirmations']
confirmations CHECK before: ["kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel', 'clean_work', 'publish_figure')),"]
confirmations CHECK after:  ["kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel', 'clean_work', 'publish_figure', 'gallery_change')),"]
jobs table text identical: True
second open: sqlite_master identical: True  counts identical: True
== oldest database (kinds launch, cancel only)
row counts before: {'confirmations': 3, 'jobs': 4, 'launches': 2}
row counts after:  {'confirmations': 3, 'jobs': 4, 'launches': 2}
confirmations rows identical (old columns): True
PRAGMA foreign_key_check: []  foreign_keys: 1
sqlite_master entries that differ: ['agents', 'compute_envs', 'confirmations', 'jobs', 'launches', 'launches_run_name', 'meta']
confirmations CHECK after:  ["kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel', 'clean_work', 'publish_figure', 'gallery_change')),"]
jobs rebuilt too (older than clean_work): kinds now ['preflight', 'list_site_files', 'launch_nextflow', 'cancel_run', 'fetch_run_records', 'read_task_log', 'clean_work', 'put_upload', 'pipeline_files', 'read_run_file', 'lint_pipeline']
second open: sqlite_master identical: True  counts identical: True
```

For the slice-1 database `sqlite_master` differs in `confirmations` only, and its `CHECK` text differs by `, 'gallery_change'` only (asserted by `test_a_slice_one_database_is_rebuilt_to_take_gallery_change_and_its_row_is_untouched`: TC-075, TC-082, TC-083). For the oldest database the other entries differ because that file only held the three tables that older versions rebuild (the same as before this feature). The `jobs` table text of the slice-1 database is identical (TC-082). A second open changes nothing (TC-077). A failure in the copy rolls back (TC-078) and a dangling job link stops it (TC-079); the existing concurrent-open and read-only tests (TC-080, TC-081) pass unchanged.

## (d) Every place that reads or writes `confirmations.kind`, and whether `gallery_change` touches it

Found with `grep -n "kind"` over `platform/abf_platform`; `test_every_place_that_reads_or_writes_the_kind_is_in_the_ledger` checks that the files `confirm.py`, `store.py`, `jobs.py`, `actions/__init__.py`, `actions/figures.py` and `web.py` that the search finds are in this list.

| place | what it does with the kind | affected by `gallery_change` |
|---|---|---|
| `store.py` `_CONFIRMATIONS_TABLE`, `_confirmations_current`, `_migrate_confirmation_kinds` | the CHECK and its rebuild | yes, on purpose: the kind is let in (section b) |
| `confirm.py` `_confirm` (INSERT of a terminal confirmation) | writes `launch` or `cancel` | no |
| `confirm.py` `create_pending` (reuse lookup `kind = ?`, the open-request count `kind <> 'clean_work'`, the INSERT) | generic over the kind | yes, as intended: `gallery_change` shares the 10-request limit with every kind except `clean_work`, and is reused by sha256 within its kind (TC-042, TC-043) |
| `confirm.py` `drop_figure_content`, `pending_figure_bytes` | `kind = 'publish_figure'` only | no: a gallery_change bundle holds no image bytes |
| `confirm.py` `_changed` (CHAT: kind and hash must match) | compares the row's kind with the kind asked now | yes, as intended: a pack request cannot carry a delete's yes, nor a publish_figure's (TC-035) |
| `confirm.py` `approve` (`row["kind"] in NO_JOB_KINDS`, then `JOB_KIND[row["kind"]]`) | the no-job branch and the job branch | yes: the kind is in `NO_JOB_KINDS`, so it never reaches `JOB_KIND`, which is unchanged and has no `gallery_change` (TC-082) |
| `confirm.py` `find_approved` (`c.kind = ?`, joined to `jobs`) | launch and cancel by their kind | no: a gallery_change has no job row and nothing asks for that kind |
| `confirm.py` `find_attempt` (`'launch'`), `find_cancel` (`'cancel'`), `launched_by` (through `launches`), `open_clean_requests` (`'clean_work'`) | one fixed kind each | no |
| `confirm.py` `describe` | returns `kind` as it is | yes, harmlessly: the page and the action layer's `approve` read it |
| `confirm.py` `facts` | a branch for each kind, then the launch default | yes: a new branch (section b), so the kind never falls to the launch default |
| `confirm.py` `forget_content` | finds rows by the run name in the bundle (`_named`), generic over the kind | yes, as intended: gallery_change rows of the run are cleared and the pending ones voided; the gallery files stay (TC-088) |
| `jobs.py` `_check_confirmation`, `claim` (`conf["kind"] != CONFIRMED[...]`), `launch_confirmation` (`kind = 'launch'`) | the three job kinds that write on the site | no: a gallery_change is never the confirmation of a job (`CONFIRMED` is unchanged) |
| `actions/__init__.py` `_ask` (passes `kind`), `_writer_for(kind)` (new), `approve` (reads the kind through `describe` to pick the writer) | the writer by kind at the three call sites (CHAT, ELICITED, PAGE) | yes: `gallery_change` gets `write_gallery_change`; every other kind keeps what it had (`write_confirmed` for publish_figure) |
| `actions/figures.py` `pending_request` (`kind = 'publish_figure'`) | the "waiting" line on the gallery | no |
| `web.py` `state_page`, `confirm_post`, `plain_block` (`req["kind"]`) | the confirmation page and its POST | yes: a branch for the new kind comes first (`change_page`, `chg`); the lines of the other kinds are unchanged. `plain_block` is not used for the new kind. |
| `web_finished.py`, `web_board.py`, `cli.py`, `receiver.py` | do not read a confirmation kind | no |

## (e) The other kinds are as they were

The existing tests of launch, cancel, resume, relaunch, clean_work, forget and publish_figure are the ones that were there (`test_launch_*`, `test_resume_*`, `test_cleanup_confirm.py`, `test_cleanup_offer.py`, `test_keep_submissions.py`, `test_chat_confirm.py`, `test_human_channel.py`, `test_publish_figure.py`, `test_publish_figure_confirm.py`, `test_web_figures.py`, `test_pending_confirm_restart.py`). They were not edited except where listed below, and they pass (section g).

### Existing test files touched, and how

- Only the number or the name list of a pinned tool list, by adding `pack_figures` and `delete_figure` (or 23 became 25): `test_aws_ce`, `test_aws_launch`, `test_azure_ce`, `test_azure_launch`, `test_azure_upload`, `test_chat_confirm`, `test_dataset_launch`, `test_estimate_su`, `test_gcb_ce`, `test_gcb_launch`, `test_http_site_samplesheet`, `test_human_channel`, `test_k8s_ce`, `test_keep_submissions`, `test_launch_e2e`, `test_launch_platform`, `test_launch_profiles`, `test_mcp`, `test_mcp_canvas_read`, `test_mcp_launch_pipeline` (also the five store lines of the schema guard), `test_mcp_run_file`, `test_mcp_server_doc`, `test_oauth_mcp`, `test_owner_guard` (also `TOOL_ACTION`: the two tools map to `request_pack_figures` and `request_delete_figure`), `test_pat`, `test_resume_edit_params_platform`, `test_resume_entrypoints`, `test_station_envs`, `test_station_launch`, `test_su_in_get_run`, `test_su_usd`, `test_web_board`, `test_web_guided_launch_preview`, `mcp/test_mcp_contract_tools.py` (`EXPECTED_TOOLS`), `mcp/snapshots/tools.json` (regenerated: 83 lines added, none removed, TC-093), `mcp/test_mcp_contract_writes.py` (`WRITE_TOOLS`, the call arguments, the error inputs, and two more write points in `FORBIDDEN`).
- `test_chat_tools.py`: one new test and one constant (`CHAT_EXCLUDED`, ruling R1); nothing else.
- `test_cleanup_store.py`: the two kind lists of the fresh-database test gained `gallery_change`; new tests appended (TC-073 to TC-083, TC-087, TC-111).
- `test_web_parity.py`: `WEB_ONLY` gained `request_pack_figures` and `request_delete_figure` with reasons; `OWED` is unchanged.
- `test_actions_layer.py`: `WRITE_NAMES` gained the two names; **ruling R2** loosened `test_gallery_page_actions_exist_in_the_action_layer_and_are_not_tools` as the plan says: it no longer asserts that `pack_figures` and `delete_figure` are not tools (they are, through the confirmation channel); `read_figure` is still asserted not to be one, and the count is 25. `test_web_figures.py` was not edited: its `not hasattr(actions, "pack_figures")` still holds because the request functions are named `request_pack_figures` and `request_delete_figure`.
- `test_publish_figure_confirm.py` and `tests/platform_storage_doc_test.sh`: the phrase "Twenty-three tools" became "Twenty-five tools" (the document sentence that went stale, TC-096). `test_publish_figure.py`, `test_publish_figure_confirm.py`: `NO_JOB_KINDS == ("publish_figure",)` became `("publish_figure", "gallery_change")` (TC-086); the migration test there removes `gallery_change` as well as `publish_figure` to build its "older" table.
- Pins that the first CI run found and that the contract's list did not name, each synced by adding the new kind or name only: `test_chat_confirm` (schema hash after `.replace(", 'gallery_change'", "")`, and the relay arguments of the two tools), `test_http_site_samplesheet`, `test_k8s_launch` (schema digest; the action-layer function list gained the two request functions), `test_web_nano4_path` (schema digest), `test_cloud_cost`, `test_keep_submissions` and `test_resume_scope` (the CHECK text), `test_guidance` (tool list), `test_web_downstream` (action names), `test_publish_figure_confirm::test_page_headers_and_css_are_unchanged` (see below).
- `test_mcp.py` `test_tc024`: the rule "no tool name matches delete|clean|write|confirm|approve" now excepts `delete_figure` by name (the maintainer's 2026-11-12 ruling; the tool asks a person first). This is a loosening that ruling R2 does not name; it is one name.
- `test_publish_figure_confirm.py::test_page_headers_and_css_are_unchanged` was already red on `origin/v3` (CI run 43318718142): it expected `origin/v3`'s routes plus the three gallery routes, but `origin/v3` has had those three since slice 2 merged, so they were counted twice. It now counts them once (`[r for r in routes(old) if r not in gallery_routes] + gallery_routes`), and still fails for any other added or removed route.
- No assertion was deleted, skipped or loosened beyond R2.

### Choices to look at

- `delete_figure` is annotated with its own constant `_DELETES` (destructive, not idempotent), not `_STOPS`: `tests/platform_storage_doc_test.sh` finds "write tools" by the annotation names `_WRITES|_STOPS`, and would then demand that `delete_figure` appears in the permission-ask paragraphs of PLATFORM.md. `publish_figure` (`_PUBLISH`) already stays out of those paragraphs. The annotation values are those of `_STOPS`.
- The confirmed write holds the gallery lock for the re-check and calls slice 2's `pack_figures` or `delete_figure`, which would take the same lock (a second flock on the same folder from the same process waits for ever). So the two cores got two optional keywords, `_folder` (the confirmed write has already checked the owner and found the folder, and has no index path to look the run up again) and `_locked` (the caller holds the lock: it is not taken again). The web routes call them as before. TC-059 and TC-060 to TC-062 test this.
- A request with no effect answers `state: "unchanged"` and makes no row (R7). The check at the yes compares the whole list of figures (name, created, request id, packed), so an unrelated new figure also refuses (P5), and a replacement with the same name does (R5).
- The writer is chosen by kind at the two call sites of `_ask` and, for the page's `approve`, by the kind that `describe` returns for the request id.

## (f) Manual cases not done by the executor

TC-113, TC-114 and TC-115 need a running platform, an MCP client and the maintainer's eye. The steps are in `docs/TESTING.md`, section "mcp-gallery-actions (slice 3)". Nothing of their output is pasted here yet.

## (g) Test runs

- New in this slice (`test_gallery_change.py`, `test_gallery_change_confirm.py`, `test_gallery_change_page.py`, the new tests of `test_cleanup_store.py`): all pass in WSL.
- Local full platform run (`python3 -m pytest tests`, WSL, serial, 20 minutes) before the last fixes: 3643 passed, 15 failed, 24 errors; the failures and errors are in the packaging/wheel tests (`test_station_packaging`, `test_su_packaged`, `test_guidance` wheel copy, two of `test_station_envs`, `test_cli` tc035) and in the Nextflow end-to-end tests (`test_nextflow_e2e`, `test_launch_nextflow`, `test_launch_e2e` tc034), which need a wheel build and a Nextflow install that this WSL does not have. The verdict that counts is the CI of the pull request.
