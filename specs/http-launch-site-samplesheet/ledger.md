# http-launch-site-samplesheet: progress ledger

- [x] US1 site files from Claude (TC-001..010): `abf_launch/build.py::_confine` (a path cell is judged as a path in `params` is: in `uploads_root` it must be a file inside the caller's own folder, else the read roots decide, already checked by `bundle.inputs_from_environment`; the `area_refusal` wording is unchanged), `abf_platform/actions/__init__.py::request_launch`, tests `platform/tests/test_http_site_samplesheet.py`.
- [x] US2 shapes that stay refused (TC-011..024, CS-03): same file; the folder itself as a cell is refused (ruling 3), a cell that is only a `..` or irregular spelling of an upload path is refused.
- [x] US3 `samplesheet_text` (TC-025..036): `actions._samplesheet_text_problem` (exactly one of the two, a non-empty `str`, at most 1 MiB of UTF-8, no NUL), `actions.request_launch` passes `samplesheet_raw=text.encode("utf-8")` to `build.prepare_launch`; `mcp_server.launch_tool` has `samplesheet: str | None = None` and `samplesheet_text: str | None = None`. `confined_samplesheet` and `read_confined_samplesheet` keep their names and use. The web form (`POST /launch`) gets no `samplesheet_text` (ruling 6).
- [x] US4/US5 rules not loosened, human gate, other person (TC-037..053): the existing files run unchanged (`test_owner_gaps.py`, `test_station_owner.py`, `test_owner_binding.py` except the one pin below) plus the new file.
- [x] US6 docs and pins (TC-054..057): `docs/PLATFORM.md` (the confirmation page paragraph, the "Files" bullet of 116, the "Paths in `params`" bullet of 116b, one sentence on the residual risk in the honest boundary); no table or column changed, so no migration (TC-057 pins the schema hash).
- [x] Out of scope kept (TC-058..062): no upload tool, no queued job before the yes, no folder made on the site.

## Rewritten pins (maintainer ruling 2026-10-23)

| Test | Old | New | Why |
|---|---|---|---|
| TC-049: `test_owner_binding.py::test_tc049_a_cell_inside_the_read_roots_but_outside_my_folder_passes` (was `test_tc049_a_cell_inside_the_read_roots_but_outside_my_folder_is_refused`) | an HTTP launch whose samplesheet cells lie in the read roots but outside the caller's folder is refused, and the refusal names the caller's folder; nothing is queued | the same launch passes to a pending request (ok, state pending, not sent) | the maintainer allowed on 2026-10-23: over HTTP a samplesheet cell may name a file in the environment's read roots; only a cell that lies in `uploads_root` must be the caller's own. A remote site has no per-person folder, so the environment owner's read roots are the limit |
| TC-LS-52: `test_station_launch.py::test_tc_ls_52_the_launch_tool_and_the_tool_list_are_those_of_the_base` | the `launch` tool's properties are `pipeline, revision, run_name, samplesheet, ce_name, params, path_columns` and `samplesheet` is required | the same plus `samplesheet_text`; required are `pipeline, revision, run_name` only; `samplesheet` and `samplesheet_text` default to none; the tool list is still the same twelve | the maintainer's ruling of 2026-10-23 adds `samplesheet_text`; exactly one of the two is given, so neither can be required by the schema (the action refuses none or both) |

## Support changes that are not pins

- `platform/tests/owner_harness.py::Duo.launch` gained `text=` and `nosheet=` (a launch by `samplesheet_text`, and a launch with no samplesheet argument at all); no existing assertion changed and the default path is as before (plan ruling 1).

## Notes

- Test environment of this run: no Java on the WSL machine, so the end-to-end tests that need Nextflow are skipped as `tests/platform_test.sh` says; the Python tests ran in a venv built from `platform/constraints.txt`.
