# 網頁修改後續跑 progress ledger

> Executor: stamp 20261029-1405-L33. One line per task; tests first (RED commit 7a03539), then the code.

- [x] Tests: `platform/tests/test_web_resume_edit.py` (new, 34 tests; TC numbers in the comments). RED commit first.
- [x] `web_board.py`: only the new strings (`RESUME_EDIT`, merged into `STRINGS`), `Acts.edit_link`, and its two call sites (the menu beside Resume for a run with a failure record; the failure notice when its first action is Resume). `STYLE` and CSP untouched.
- [x] `web_launch.py`: new functions only (`typed_like`, `wrong_type`, `resume_changes`, `two_columns`, `resume_params_block`, `render_resume_edit`); `groups_block` and every existing function are unchanged byte for byte.
- [x] `web.py`: `GET /act/resume/edit`; `POST /act/resume` reads `p.<name>` and `extra_config` only when one is present (a form without them takes the old path, same 303 / 409); the confirmation page lists the changes (read from the lines the action layer's own screen wrote, no change to `confirm.py`).
- [x] `docs/TESTING.md`: new manual section.

Existing tests changed (each only adds; nothing deleted, skipped or loosened):

| file | what was added | why |
|---|---|---|
| `test_cleanup_offer.py` `ROUTES` | `/act/resume/edit` | the route list is pinned; there is one new route (TC-082) |
| `test_confirm_page.py` (routes of the web app) | `("/act/resume/edit", ("GET", "HEAD"))` | same |
| `test_dataset_cli.py` (routes read from the source of `web.py`) | `"/act/resume/edit"` | same |
| `test_owner_binding.py` `test_tc068` | `/act/resume/edit` in the set of paths | same; it logs nobody in |
| `test_web_board.py` routes list | `("/act/resume/edit", ("GET", "HEAD"))` | same |
| `test_web_board.py` `test_tcs36_cards_are_read_only` | a third allowed shape of link in the middle and right columns: `/act/resume/edit?run=…` | the new link "修改後續跑" is a plain link that only reads |

Plan versus rules, found while doing it:

- TC-040 asks the web code to use the station's `MAX_EXTRA_CONFIG`. `test_cleanup_offer::test_platform_and_launch_sources_…` forbids the word `station` in any `abf_platform` source line, so `web.py` uses `abf_launch.build.CONFIG_LIMIT` (the platform's own number, 20000, equal to the station's); the new test asserts the two are equal.
- The station's check on the extra settings accepts only resource lines and `//` comments; a `#` line is refused by the action layer and comes back on the form as the 400 sentence. The tests use `//`.
- `WSL constitution_scope_test.sh` red is the environment (ruling 5): worktree made with Windows git; CI decides.

Found by the first full run (two more pinned tests):

| file | what changed | why |
|---|---|---|
| `test_estimate_su.py` `test_tc030_no_su_route_on_the_web` | the search for a route whose path holds `su` or `estimate` skips `/act/resume/edit` | the path (fixed by the plan) holds the letters `su` in "resume"; the test is about SU, and the new page has nothing to do with it. One path is excluded, the check stays for every other route. |
| `test_resume_scope.py` `test_tc146_…` | none | it passes by naming: `web.py` has no new name with resume/relaunch in it (`edit_reads`, `edit_page`, `edit_get`, `edit_post`; the helpers in `web_launch.py` are `edit_changes`, `edit_params_block`, `edit_page_html`) |

| `test_clean_page.py` `BASE_BOARD` (`failed-zh`, `failed-en`) | the two pinned digests of the board of a failed run were replaced by the digests of the board now | the failed run's menu and notice now carry the link "修改後續跑" (TC-001, TC-002); this is the one pinned page that holds a failed run with no clean-up request. The `succeeded` and `running` digests are unchanged, which shows the page is otherwise the same bytes. This is a changed value, not an added one: it cannot be an addition. |

Note on the full run: a first-pass failure re-runs the shard under a longer temporary path (`….retry`), and `test_aws_ce.py::test_a_missing_credential_file_says_where_to_put_it` then fails on the path length; it passes alone and in a normal pass. It is not related to this task.

Merge of origin/v3 (ruling 6, 11-03): conflicts in `docs/TESTING.md` (both sections kept), `test_cleanup_offer.py`, `test_dataset_cli.py`, `test_owner_binding.py` (v3 side taken, `/act/resume/edit` added again), `test_clean_page.py` (v3 side taken, failed-zh / failed-en digests recomputed). `test_web_resume_edit.py::test_tc079` pin moved to v3's STYLE hash (`web_board.STYLE` is byte-identical to v3: no diff against origin/v3).
Full run after the merge found two more pinned tests: `test_k8s_launch.py::test_the_user_visible_actions_are_those_of_the_base` (web route count 28 -> 29 and its digest: the one new route `/act/resume/edit`) and `test_web_wording_sweep.py` (`tables()` lists `web_board.RESUME_EDIT`, count 7 -> 8, so our wording is checked for banned words too).
Also `test_web_settings_ce_mobile.py::test_ce08_no_new_strings`: the pinned hash of `web_board.STRINGS` re-pinned (the new resume-edit strings are merged into it; `web_settings` hash unchanged).
