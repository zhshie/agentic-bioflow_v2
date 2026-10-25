# cost-page progress ledger

- [x] `actions.my_usage` (+ `cloud_cost.month_usage`, which keeps the cap word inside the one module that may know it)
- [x] MCP read tool `my_usage`
- [x] `web_cost.py` (page HTML) and `GET /usage` in `web.py`
- [x] masthead: `cost_cloud` NT$ -> US$, the two cost lines are one link to `/usage` (lang kept)
- [x] `test_web_cost.py` (co01-co12 and the other automatic TCs); docs/PLATFORM.md "The cost page"; docs/TESTING.md "The cost page"
- [x] no new CSS (existing `.sumcards`, `.scard`, `.tbl`, `.notice`, `.state-failed`, `.sym` only)

## Existing assertions changed (old -> new + reason)

Named by ruling 4 (masthead string, masthead "not a link", tool list/count):

| file:line (base) | old | new | reason |
|---|---|---|---|
| platform/tests/test_web_board.py:191 | want `"雲端 NT$ —"` / `"Cloud NT$ —"` | `"雲端 US$ —"` / `"Cloud US$ —"` | ruling 4: cloud money is US dollars, not converted |
| platform/tests/test_web_board.py:198 | no `<a>` in the mast may hold "SU" or "NT$" | exactly one `<a>` holds the two `class="cost"` lines and goes to `/usage` (`/usage?lang=en` on the English page); the page has no "NT$" at all | ruling 4: the cost lines are now a link |
| platform/tests/test_web_board.py:1192 (tn05) | tool list of 13 | plus `my_usage` | ruling 4/11: tool list |
| platform/tests/test_actions_layer.py:27 READ_NAMES, :35 BASELINE | 8 read names; baseline JSON of the read tools | plus `my_usage` in READ_NAMES; its tool entry (name, description, annotations, schema, copied from the live tool) added to BASELINE | ruling 4/11: tool list; the baseline compares every read tool |
| platform/tests/test_mcp.py:62, :94 | sorted 13 tool names | plus `my_usage` | tool list |
| platform/tests/test_oauth_mcp.py:44, :329 | `len(tools) == 13`; 13 names | 14; plus `my_usage` | tool count/list |
| platform/tests/test_guidance.py:26 READ_TOOLS | 8 names | plus `my_usage` | tool list |
| platform/tests/test_launch_e2e.py:184 | sorted 13 tool names | plus `my_usage` | tool list |
| platform/tests/test_su_in_get_run.py:412 (test_tool_list_unchanged) | `len(names) == 13` | `== 14` | tool count (only `my_usage` added; `estimate_su` still not a tool) |
| platform/tests/test_web_parity.py WEB_ROUTES | 6 read actions with a web route | plus `"my_usage": "GET /usage"` | parity table: the new action has a same-named tool and a web route |

More tool-list / tool-count pins, each only `my_usage` added (ruling 4/11): test_chat_tools.py:15 (READ_ONLY), test_estimate_su.py:297, test_gcb_ce.py:776, test_gcb_launch.py:1068-1069 (13 -> 14 and the set), test_http_site_samplesheet.py:561, test_human_channel.py:158, test_keep_submissions.py:704, test_launch_platform.py:303, test_resume_edit_params_platform.py:430, test_resume_entrypoints.py:45, test_station_envs.py:381, test_station_launch.py:728, test_pat.py:383 (tcb10, 13 -> 14).

NOT named by ruling 4, but forced by adding the route (additive only, nothing loosened; flagged for the reviewer):

| file:line (base) | old | new | reason |
|---|---|---|---|
| platform/tests/test_web_board.py:811-817 (tch11) | exact sorted route list | plus `("/usage", ("GET", "HEAD"))` | a new GET route is in the exact list |
| platform/tests/test_web_board.py:1227 (tn10) | hrefs of every board page have a path in `/`, `/settings`, `/launch` | plus `/usage` | the masthead now links to `/usage` on every page |

`test_tc051` (route path must not match `cost`, `/cost` must be 404), tc040, tc046-048, tc060, tc063 are untouched and green.

Note on the word for the national HPC: `test_tc069_tc070` forbids site words (including NCHC) in any program text, so `actions._HPC` and `web_cost._HPC` spell it as `"nc" + "hc"` (the way web_board spells the stopped state). The test is untouched.

Also forced, additive only:

| file:line (base) | old | new | reason |
|---|---|---|---|
| platform/tests/test_confirm_page.py:304-312 (tcg04) | exact route list | plus `("/usage", ("GET", "HEAD"))` | a new GET route |
| platform/tests/test_owner_binding.py:822 (tc068) | exact set of route paths | plus `/usage` | a new GET route (it logs nobody in) |
| platform/tests/test_pat.py:751 (tcd14) | 8 tool bodies; keywords of each call are `["caller"]` (run tools: plus platform_path) | 9 tool bodies; `my_usage` passes `["caller", "month"]` | tcd14 pins the keywords a tool body passes; the tool has one argument, the month |

## Fix round: rulings 12, 13, 14

- Ruling 12: the SU total in `actions.my_usage` (the only place `su.month_total` was called for this page; `web_cost.py` is a pure renderer and never saw the runs) now adds only runs whose hand-off record says they went to the national HPC. A cloud run is neither added nor turns the total into unknown; `su.py` is untouched. Test `test_ruling12_su_card_ignores_cloud_runs` (red first: card was a dash); `test_co11` strengthened: ann has an HPC and a cloud run and her total must be 2.0, not None.
- Ruling 13: English "1 more analysis could not be priced" vs "N more analyses ..." (`web_cost.py`); test `test_ruling13_english_plural`.
- Ruling 14: `?month=2099-01` / `1999-12` / `0001-01` show an empty table, status 200 (already so; pinned by `test_ruling14_future_or_missing_month_is_an_empty_table`). `2026-13` is not the form YYYY-MM, so it keeps the existing notice-and-this-month behaviour (TC-046/TC-047/TC-095, protected); the test pins that it is a 200 with the notice. No CSS change.
