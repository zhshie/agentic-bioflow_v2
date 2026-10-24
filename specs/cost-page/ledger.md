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
| platform/tests/test_web_parity.py WEB_ROUTES | 6 read actions with a web route | plus `"my_usage": "GET /usage"` | parity table: the new action has a same-named tool and a web route |

NOT named by ruling 4, but forced by adding the route (additive only, nothing loosened; flagged for the reviewer):

| file:line (base) | old | new | reason |
|---|---|---|---|
| platform/tests/test_web_board.py:811-817 (tch11) | exact sorted route list | plus `("/usage", ("GET", "HEAD"))` | a new GET route is in the exact list |
| platform/tests/test_web_board.py:1227 (tn10) | hrefs of every board page have a path in `/`, `/settings`, `/launch` | plus `/usage` | the masthead now links to `/usage` on every page |

`test_tc051` (route path must not match `cost`, `/cost` must be 404), tc040, tc046-048, tc060, tc063 are untouched and green.
