# gallery-followups ledger

Status: BLOCKED (one existing test outside the named list fails).

## Existing tests rewritten (only the named assertion)
- test_web_figures.py::test_nothing_in_package_until_pack_pressed: `'checked' not in g` became `ticked(g) == ["a.png", "b.svg"]` (decision: packed figures are pre-ticked).
- test_replace_needs_click.py (publish annotations test, line 348): destructive_hint False -> True.
- test_chat_tools.py: REQUESTS constant, test_gallery_tools_are_excluded_from_the_browser_chat, the tc020 relay-argument list, test_tc052 loop (gallery tools answer with `url`).
- test_chat_confirm.py::test_tcm_53: sha256/length pin of the prompt replaced by pack_figures / delete_figure / 不能在聊天 checks; comment at line 327.
- test_chat_tools.py test_tc001_tc034 passes through the REQUESTS constant.

## Blocking
- test_head_nodefail.py::test_tc048_get_run_stays_a_query_that_needs_no_yes (last assertion): `chat_tools.REQUEST_TOOLS == {"launch", ..., "forget"}`. It is not in the plan's list (the list names tc046, which passes unchanged). Not edited.

## Local results (WSL)
test_chat*.py, test_web_figures.py, test_web_wording_sweep.py, test_gallery_change*.py, test_replace_needs_click.py, test_head_nodefail.py, tests/mcp: 432 passed, 17 xfailed, 1 failed (tc048 above).
