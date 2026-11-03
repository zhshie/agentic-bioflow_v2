# mcp-description-shorten ledger (task C6)

## Finding
`get_run` (683) and `run_outputs` (700) cannot be shortened here: `platform/tests/test_actions_layer.py`
(`test_tca10_...`, BASELINE) pins their descriptions byte for byte, and `test_su_usd.py` requires
`get_run` to start with the baseline text. Editing BASELINE would change another test's assertion, which
the task forbids. They stay in OVER_LIMIT at their current numbers. `launch` untouched.

## Red output (read_run_file and resume removed from OVER_LIMIT, before editing descriptions)
```
>               assert n <= LIMIT, "%s description is %d chars, over %d" % (t["name"], n, LIMIT)
E               AssertionError: read_run_file description is 1016 chars, over 600
E               assert 1016 <= 600
FAILED tests/mcp/test_mcp_contract_tools.py::test_descriptions_within_limit
1 failed, 10 passed in 1.23s
```
(With all four removed the first failure was `get_run description is 683 chars, over 600`.)

## Before / after (characters)
| tool | before | after |
|---|---|---|
| read_run_file | 1016 | 595 |
| resume | 807 | 600 |
| get_run | 683 | 683 (pinned by BASELINE) |
| run_outputs | 700 | 700 (pinned by BASELINE) |

## Full test run
Not recorded here: see the PR description for the state of the full run at the time of opening.
