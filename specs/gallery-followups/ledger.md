# gallery-followups ledger

Status: done. Lead ruling 2026-11-13 allowed the tc048 rewrite below.

## Existing tests rewritten (only the named assertion)
- test_web_figures.py::test_nothing_in_package_until_pack_pressed: `'checked' not in g` became `ticked(g) == ["a.png", "b.svg"]` (decision: packed figures are pre-ticked).
- test_replace_needs_click.py (publish annotations test, line 348): destructive_hint False -> True.
- test_chat_tools.py: REQUESTS constant, test_gallery_tools_are_excluded_from_the_browser_chat, the tc020 relay-argument list, test_tc052 loop (gallery tools answer with `url`).
- test_chat_confirm.py::test_tcm_53: sha256/length pin of the prompt replaced by pack_figures / delete_figure / 不能在聊天 checks; comment at line 327.
- test_chat_tools.py test_tc001_tc034 passes through the REQUESTS constant.

## Local results (WSL)
test_chat*.py, test_web_figures.py, test_web_wording_sweep.py, test_gallery_change*.py, test_replace_needs_click.py, test_head_nodefail.py, tests/mcp: 433 passed, 17 xfailed, 0 failed (WSL). tests/run_all.sh not run locally; CI is the judge.

## Ruling and the tc048 rewrite
The plan named test_tc046 by mistake; the lead ruled (2026-11-13) that test_head_nodefail.py::test_tc048_get_run_stays_a_query_that_needs_no_yes may be rewritten, only the one assertion on `chat_tools.REQUEST_TOOLS`.
- Old: `chat_tools.REQUEST_TOOLS == {"launch", "launch_pipeline", "cancel", "resume", "relaunch", "forget"}`
- New: the same set plus `"pack_figures", "delete_figure"`.
- Reason: both tools are now request tools of the browser chat.

## Not observed
The RED of the publish_figure annotation change (commit 3495ae19) was committed without seeing it fail; only its GREEN was run.

## git diff --stat origin/v3...HEAD
