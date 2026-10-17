# 116: each caller sees and uses only their own compute envs, agents, runs and files progress ledger

Branch `feat/116-owner-binding`. Tests were written first (commit `RED:`), then the code (commit `GREEN:`). The cases are `test-case.md`; the new tests are `platform/tests/test_owner_binding.py` (helpers: `platform/tests/owner_harness.py`).

## Tasks

- [x] D1 owner columns: `compute_envs.owner_user_id`, `agents.owner_user_id`, `launches.user_id` (INTEGER NULL, added in place, last); `user_id` copied from the confirmation's `caller_user_id` inside `enqueue_confirmed`, same transaction (`store.py`, `jobs.py`).
- [x] D2 one rule: a caller sees only its own rows; another's or nobody's answers like a missing one (`compute_envs.get/list_all(owner=)`, `agents.list_agents(owner=)`, `actions/__init__.py`).
- [x] D3 runs: the newest `launches` row of a name decides (`jobs.owned_run_names`, `status.list_runs(names=)`, `actions.list_runs/get_run`).
- [x] D4 launch and listing: `primary_environment`/`prepare_launch` choose among the caller's own; `jobs._target` and `enqueue_confirmed` refuse when the confirmation's caller is not the owner of the environment and of its agent; `ce create|update` refuse an agent with a different owner; `set_primary` is per owner.
- [x] D5 agents: `agent-token new --user`, `create_token` allows `user_id` for an agent token, `lookup_token` returns `user_id`, `agents.register(owner_user_id=)` fills an empty owner and refuses another (403 on hello, poll, result); `ce create --owner` (default: the only user, required with two or more), `ce update --owner` (fix round: it also hands the environment's agent to the new owner when the old owner had it, `compute_envs._hand_agent_along`; refused while another environment of the old owner uses that agent).
- [x] D6 cancel: `prepare_cancel(owner=)` and the queue's cancel branch check that the confirmation's caller launched the run; the 009c `launched_by` check is untouched; the terminal cancel names no account.
- [x] D7 terminal launch: `abf-platform launch --user NAME` (required once a user exists, unknown name refused before the question, no user: NULL); `_require_human` / `terminal_problem` untouched.
- [x] D8 path cells: `build.prepare_launch(area=)` checks every path cell with links followed against `actions.caller_area()` (the samplesheet's own area), on top of the environment's roots; terminal and stdio pass no area.
- [x] D9 `list_site_files`: a path inside `uploads_root` is allowed for a caller only inside its own folder.
- [x] D10 migration: `store.assign_orphans` (one user adopts; two or more adopt nothing; none: nothing; `owners_assigned` mark), run at `serve`, `mcp`, `web`, `ce` (in `cli.main`) and `launch`; `ce list` and `launches` print the owner; `rebuild` does not call it.
- [x] Docs: `docs/PLATFORM.md` "Whose it is (spec 116)", `CHANGELOG.md`, `docs/TESTING.md` "Owner binding (116)" (the manual step of TC-074).

## Test cases

| TC | test | code |
|---|---|---|
| 001-013 | `test_owner_binding.py` tc001 to tc013 | `actions/__init__.py` (`list_*`, `get_*`), `compute_envs.get/list_all`, `agents.list_agents`, `jobs.owned_run_names`, `status.list_runs` |
| 014-023 | tc014 to tc023 | `build.prepare_launch`, `jobs._target`, `jobs.enqueue_confirmed`, `jobs.enqueue_listing`, `compute_envs.set_primary` |
| 024-027 | tc024 to tc027 | `build.prepare_cancel`, `jobs.enqueue_confirmed` (cancel branch) |
| 028-030 | tc028 to tc030 | `store.create_token/lookup_token`, `agents.register`, `agents.make_routes` |
| 031-036 | tc031 to tc036 (TC-035 also: two added tests, the agent goes with the environment and is then usable by the new owner; refused while the old owner's other environment uses it) | `compute_envs.create/update`, `cli.py` (`--owner`, `ce list`) |
| 037 | tc037 | unchanged page rule (`web.view_of`) |
| 038-040 | tc038 to tc040 | `jobs.enqueue_confirmed`, `confirm.approve` |
| 041-047 | tc041 to tc047 | `abf_launch/cli.py` (`_account`, `cmd_launch`, `cmd_launches`) |
| 048 | tc048 | `docs/PLATFORM.md`, `CHANGELOG.md` |
| 049-053 | tc049 to tc053 | `build._check_area`, `actions.caller_area`, `abf_station/launch.py::path_cells` |
| 054 | existing agent re-check tests, unchanged (`test_station_launch.py`, `test_launch_bundle.py`) | `abf_station/launch.py` (the re-check is the same function; only a helper was split out of `_check_samplesheet`) |
| 055-058 | tc055 to tc058 | `actions._uploads_problem` |
| 059-068 | tc059 to tc068 | `store.assign_orphans`, `store._add_owner_columns`, `cli.adopt_orphans` |
| 069 | `test_human_channel.py::test_tch09_*`, `test_confirm_page.py` (unchanged) | |
| 070 | `test_pat.py` tce04, `test_human_channel.py` tcf09 (unchanged) | |
| 071 | `test_human_channel.py` tcf07/tcf08 (unchanged), `test_receiver*.py` | |
| 072 | `test_station_envs.py::test_tc086_*`, `test_human_channel.py::test_tcf10_f11_*` (the allow-list of identity names gains `owner_user_id`; `EXEMPT` is unchanged) | |
| 073 | `tests/no_second_run_state_test.sh` (unchanged) | |
| 074 | this file, section below; `docs/TESTING.md` | |

Limits worth knowing:

- TC-008 and TC-011 name "the web" as a third door. The page (`web.py`) has five routes and none lists runs or environments, so there is nothing for it to show or hide; the tests assert that those addresses are 404 for a logged-in user and that another user's request page stays "not yours". No list page was added (out of scope).
- Open question 1 of the overview (no user at all): `ce create` without `--owner` makes an environment with no owner. Question 4 (agent with no owner): `ce create|update` accept it; the queue refuses a caller on an agent whose owner is not that caller, empty included. Question 5: `--user` on `agent-token new` is optional; a token without a user neither takes nor refuses an owner. Question 2: old runs of two or more users stay terminal-only; no command assigns them.

## Pins that were rewritten (nothing deleted, skipped or loosened)

Each line: test, old expectation, new expectation, reason.

- `test_pat.py::test_tcd10_the_terminal_passes_caller_none_and_the_row_is_null`: old, both `actions.launch` and `actions.cancel` in `abf_launch/cli.py` pass `caller=None`; new, `cancel` still passes `None` and `launch` passes the variable `caller` (the account named with `--user`, `None` when the platform has no user); the second half (a terminal launch without a caller leaves `caller_user_id` NULL) is unchanged. Reason: D7.
- `test_pat.py::test_tcd14_tool_bodies_stay_one_call_with_caller_and_read_the_http_auth_context`: old, every tool passes only `caller=`; new, `list_runs` and `get_run` also pass `platform_path=platform_path`, and all other checks (one return statement, `_caller(ctx)`, no branch) stay. Reason: D3, a run is its launcher's and the record is in platform.db, whose path the server is built with.
- `test_pat.py::test_tcf03_f04_the_users_table_has_no_role_and_both_labs_see_the_same`: old, two users of two labs get the same four answers and see two environments; new, the users table assertion is unchanged, each user sees only their own environment (`lab-a` / `lab-b`), the runs without a launch record are visible to neither, and the other lab's environment is "not found". Reason: D2, D3 and TC-013 (no sharing, not even inside a lab). The function name is kept.
- `test_pat.py::test_tcb08_b09_a_valid_pat_gives_the_six_tools_and_the_stdio_answers`: assertions unchanged (HTTP answers equal stdio answers); setup change: the three runs get hand-off rows naming alice, because a run without one is hidden over HTTP.
- `test_pat.py::test_tcd08`, `test_tcd09`, `test_tcd11`: assertions unchanged; setup change: the environment, its agent and the launch row of the fixture are given to the caller's id (`test_launch_platform.own_all`), because a caller may use only what is theirs.
- `test_pat.py::test_tcd01_read_actions_take_caller_by_keyword_and_ignore_it`: not changed and still green (the platform it uses has no data); its second half ("ignore it") is no longer the rule, and the new rule is covered by `test_owner_binding.py` tc001 to tc012.
- `test_launch_platform.py::test_tc055_launches_holds_the_facts_of_the_handover_and_no_state`: old column set had 10 names; new adds `user_id` (the name check for state words below it is unchanged). Reason: D1.
- `test_launch_platform.py::test_tc051_a_platform_db_made_by_007_is_upgraded_and_keeps_every_row`: old, the upgraded `compute_envs` rows equal the old rows; new, the old columns equal the old rows and the new `owner_user_id` is NULL. Reason: D1, the column is added last.
- `test_station_envs.py::banned_schema_words` (used by `test_tc086_*` and `test_human_channel.py::test_tcf10_f11_*`): the allow-list of identity names gains `owner_user_id`. `EXEMPT` (the session and password exception) is unchanged, so no new exception to the ban on session, cookie and password names.
- `test_mcp.py::test_tc025_streamable_http_gives_the_same_answers_on_loopback`: assertions unchanged; setup change as `test_tcb08`.
- `test_human_channel.py::test_tca02_a06_*`: assertions unchanged (the page's summary and bundle hash are the terminal's); setup change: the terminal run names the account (`--user ann`) and reads the samplesheet that the page's caller sent (its paths are in her folder), so the two bundles are the same content.
- `test_review_fixes.py::put_sheet` and `test_f2_stdio_keeps_reading_any_path_and_the_root_is_a_setting`: assertions unchanged; setup change: the sheet copied into a caller's folder has its paths moved under that folder, and the environment is given the moved upload root as a read root.
- `human_harness.World`: the environment can read the upload folder; the first user to exist adopts the setup (`store.assign_orphans`, what the migration does); `in_area` moves the paths of the sheet under the caller's folder and launches on an environment the caller owns (`env_for`: `lab-a` for its owner, an own one made on first use for any other user). `make_ce` and `helpers.own_runs` are new optional setup. Setup changes only.
- Unchanged and green: `tce04`/`tcf09` (signatures of `launch` and `cancel`), the three channel singletons, the receiver tests, the agent re-check tests, `test_tch09_*`.
