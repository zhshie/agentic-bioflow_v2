# 網頁上傳資料頁（雲端環境） progress ledger

- [x] RED: `platform/tests/test_web_upload.py` TC-001..TC-070 first (59 red before any code, commit 72e1b3a); the rest of the file (progress page, entry points, layers, out of scope, constitution checks) was added with the code.
- [x] GREEN: `platform/abf_platform/uploads_web.py` (streaming multipart receive, per-file limit, staging folder, `discard`/`sweep`), `platform/abf_platform/actions/uploads.py` (judging, queueing, reading, registering), `platform/abf_platform/web_upload.py` (the two pages), routes `GET /upload`, `POST /upload`, `GET /upload/{batch}` in `web.py`, `actions/__init__.py` (`start_upload_batch`, `upload_batch_status`, forwarding only), `actions/datasets.py` (`check_samplesheet`; `register_dataset` shares it, same answers), `jobs.py` (`upload_jobs`, read only), `web_board.py` (left-column link, step-4 link, `g_go_upload` strings).
- [x] docs: `DESIGN.md` (two sentences of ruling 9), `docs/OPERATIONS.md` point 6, `docs/PLATFORM.md` (the "Uploading to AWS" paragraph), `docs/TESTING.md` (new manual section, TC-104).

## Where a batch is kept (TC-116)

`<uploads>/<user>/.batches/<batch>.json` (mode 0600, written to a temporary file in the same folder and renamed). It is not in the database: no table, no column, no migration (`_migrate` list and the table hash are unchanged). Staged copies: `<uploads>/<user>/.incoming-<batch>/` while the form is received, then moved to `<uploads>/<user>/<file name>`; the agent on the platform host deletes them after the size check. A registered batch also leaves `<uploads>/<user>/datasets/<name>/<version>.csv` (see "Decisions" below).

## Existing assertions that changed (TC-114, TC-115, TC-117)

Every change only adds an item or states the new truth the plan names; nothing was deleted, skipped or loosened.

| File:line (after) | Old | New | Why |
|---|---|---|---|
| test_dataset_cli.py:183 | route list ends `"/settings", "/usage", "/welcome"` | adds `"/upload", "/upload/{batch}"` | pinned route list (ruling 17 / scope) |
| test_cleanup_offer.py:821 | `ROUTES` without upload | adds `'/upload', '/upload/{batch}'` | pinned route list |
| test_confirm_page.py:312-319 | route list without upload; `/upload` in the must-be-404 loop | list adds `/upload` GET+POST and `/upload/{batch}`; `/upload` leaves the 404 loop; new assert: without a login `/upload` answers like `/launch` (303 /login) | ruling 17 |
| test_web_board.py:316-322 (`test_tcs21_s22_left_grey_and_settings`) | `"↑ 上傳資料"` in the grey list | removed from the grey list; new asserts that it is `<a class="nv" href="/upload">` (zh) and `href="/upload?lang=en"` (en); the other grey items and the settings link unchanged | ruling 13, TC-112 |
| test_web_board.py:824 (`test_tch11_read_only`) | route list without upload | adds the three upload routes | pinned route list |
| test_web_board.py:1189-1195 (`test_tn04_other_paths_stay_missing`) | `/upload` in the must-be-404 loop | removed; new assert as in test_confirm_page | ruling 17 |
| test_web_board.py:1240 (`test_tn10...`) | board links may go to `/ /settings /launch /usage` | adds `/upload` | the left column now links to it |
| test_owner_binding.py:824 | route set without upload | adds `"/upload", "/upload/{batch}"` | pinned route set |
| test_web_actions.py:504-506 (`test_tc051_tc056...`) | regex `upload\|cost\|...`; `/upload` in the must-be-404 tuple | `upload\|` removed from the regex and `/upload` from the tuple; new line: the routes with `upload` are exactly `/upload` and `/upload/{batch}` | ruling 17 (the tuple part is a consequence the plan did not spell out) |
| test_web_parity.py:35-36 | `WEB_ONLY` without the two upload actions | adds `start_upload_batch`, `upload_batch_status` | parity table (TC-108) |
| test_aws_upload.py:665 | datasets functions: six names | seven (adds `check_samplesheet`) | ruling 13, TC-110 |
| test_aws_upload.py:733-734 | callers of `enqueue_put_upload` collected as file names, `== ["jobs.py"]` | collected as paths relative to `abf_platform`, `== ["actions/uploads.py", "jobs.py"]` | ruling 13, TC-109 (the collection had to give paths to be able to say the list the plan names) |
| test_aws_upload.py:751-752 | PLATFORM.md holds `網頁入口尚未接上` | holds `網頁上傳頁（/upload）會把檔案暫存於平台主機後排入此工作` and no longer the old sentence; the `s3://`, `版本控管`, `仍` checks on that paragraph unchanged | ruling 13, TC-103 |
| test_datasets.py:441 (`test_tc063...`) | six names | seven | TC-110 (the plan names `:441`) |
| test_cloud_upload.py:611 (`test_no_public_function_was_added_to_datasets`) | six names | seven | the same list lives here too; not named in the plan, found by the run |
| test_aws_ce.py:812, test_aws_launch.py:1137, test_gcb_ce.py:779, test_gcb_launch.py:1071 | `... and not r.path.startswith("/upload")` | `... and r.path not in {"/upload", "/upload/{batch}"}` (the exact two routes of this task, no prefix) | ruling 25 item 1 |
| test_web_guided_launch_2d.py:361 (`test_tc020...`) | step-4 link goes to `/` and `/?lang=en` | goes to `/upload` and `/upload?lang=en` | ruling 25 item 2 |
| test_clean_page.py:166-168 and helper `old_upload_item` | helper put the grey item back before hashing the board | helper removed; `BASE_BOARD` holds the six new digests (b900748476502f3d, 870addd406492402, f5866fcf5bb0a339, 918ba6c8db56e423, f5b7e52afdb2ec69, 9c1d9195eacfbe23) | ruling 25 item 3 |
| test_owner_guard.py:149 | `NO_TOOL` without the upload actions | adds `start_upload_batch`, `upload_batch_status` | ruling 25 item 4 (kept) |
| test_cloud_upload_docs.py:42 | OPERATIONS point 6 holds `Not built yet` and `nothing in the web or the AI calls it` | holds `The web page /upload sends files up to 2 GB into the bucket` and no `Not built yet` | ruling 13, TC-102 |
| test_guidance.py:460 (`test_tc707_the_mcp_pin_is_unchanged`) | `dependencies = ["mcp>=2.3,<3"]` | `dependencies = ["mcp>=2.3,<3", "python-multipart"]` | ruling 24 / TC-105 adds the one dependency line; the mcp pin and the constraints.txt check are unchanged. Not named in the plan, found by the full run; flagged for the reviewer. |
| test_azure_upload.py:857 | Azure section of PLATFORM.md holds `網頁入口尚未接上` | holds `網頁上傳頁（/upload）會把檔案暫存於平台主機後排入此工作` and no longer `網頁入口尚未接上` (the other checks on that section unchanged); PLATFORM.md's Azure paragraph reworded to match | merge with v3 after #259/#262: the upload page is not tied to a cloud type, so the Azure sentence became false and contradicted test_aws_upload.py:751 |
| the pinned route lists in test_dataset_cli.py:183, test_cleanup_offer.py:821, test_confirm_page.py:312-319, test_web_board.py:824, test_owner_binding.py:824 | each lists the three upload routes (and, from v3, no pipeline-registration routes) | each lists both: the three upload routes and `/settings/pipelines`, `/settings/pipelines/confirm` | merge with v3 after #259/#262: recomputed from the merged `web.py`; no assertion of either side dropped |
| test_owner_guard.py:149 and test_web_parity.py:35 | `NO_TOOL` / `WEB_ONLY` list the two upload actions | list the two upload actions and the three site-pipeline actions v3 added | merge with v3 after #259/#262 |
| test_azure_launch.py:1122 (`test_tool_list_is_still_twelve_and_no_new_web_route`) | no route path matches `azure\|batch` | no such route except the exact two `/upload`, `/upload/{batch}` | merge with v3 after #259/#262: same exemption as the four sibling tests above (ruling 25 item 1); the test came in with v3 |
| test_azure_upload.py:759 (`test_no_migration_and_the_datasets_surface_did_not_grow`) | datasets functions: six names | seven (adds `check_samplesheet`) | merge with v3 after #259/#262: the same list as test_aws_upload.py:665 and the others above; this test came in with v3 |

Not changed although the plan lists them: `test_temp_password.py:290` (the loop over all routes already holds for the new routes: a temporary login gets 303 /welcome on `/upload` GET and POST and on `/upload/{batch}`), `test_aws_upload.py:660` (no table, no migration), `test_datasets.py:470` (`test_tc064`, untouched and green).

## Decisions and open points

- **Step 4 of the launch page lists files of the person's upload folder, not datasets.** The plan and TC-083 say a registered dataset is a choice at step 4. The web launch page never read the datasets table (only the AI `launch` tool takes `dataset`). To make TC-083 true without touching `web.py`/`web_board.py` beyond the plan, registering a batch also writes the registered samplesheet (cloud places in the cells) to `<uploads>/<user>/datasets/<name>/<version>.csv`; `list_samplesheets` then offers it as `datasets/<name>/<version>.csv`. If the maintainer wants a real dataset chooser in step 4, that is a separate task.
- **`platform/pyproject.toml`**: the one line `"python-multipart"` was applied by the developer-agent (c2152b4); TC-105 is done.
- TC-129 (tools): the second half now reads the real registration source `chat_tools.tool_specs(...)` (chat_tools has no `TOOLS` list) and asserts no tool name holds `upload`. TC-101 now has an automatic test (`test_tc101_design_md_upload_data_paragraph`).
- The 404 for a path such as `/upload/..%2F..%2Fetc` is the framework's own 404 (no route matches once `%2F` is decoded); a missing batch and somebody else's batch answer with the board's 404 page, byte for byte the same.
- The pages use `LAUNCH_HEADERS` (the same content-security-policy as `/launch`, TC-016); `_HEADERS` and both constants are unchanged.
- Rule 18 (taking a failed batch's names back) is decided per file: a name is free when its batch failed and the job for that very file is over; a file of a failed batch that is still queued or being sent keeps its name.
