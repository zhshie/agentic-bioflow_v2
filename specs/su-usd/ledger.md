# su-usd progress ledger

- [x] su_rates.json: su_plan_type, usd_twd. su.usd_of / su.usd_rate (platform/abf_platform/su.py).
- [x] actions: get_run su.usd_approx; my_usage su.usd_approx, su.usd_rate_as_of, each line usd_approx. MCP descriptions one sentence added.
- [x] web_board.su_text (shared wording) + run page cost card; web_cost card, rows, footnote.
- [x] docs/PLATFORM.md paragraph, docs/TESTING.md section "SU 約 US$".
- [x] platform/tests/test_su_usd.py (RED commit first, then GREEN).

## Existing assertions rewritten (kind: new expected string / key added / sentence added)

| file | before | after | why |
|---|---|---|---|
| test_web_cost.py test_co02 | SU card `"12.30"` | `"12.30 SU（約 US$0.03）"` | new display |
| test_web_cost.py test_ruling12 | SU card `"4.00"` | `"4.00 SU（約 US$0.01）"` | new display |
| test_web_cost.py test_co11 | SU card `"2.00"` | `"2.00 SU（約 US$0.01 以下）"` | new display |
| test_web_cost.py test_co11 | `su` keys {total, unknown_reasons, site} | plus usd_approx, usd_rate_as_of | key added |
| test_web_cost.py test_co11 | line keys (7) | plus usd_approx | key added |
| test_web_cost.py test_co06 | row `"5.10 SU"` | `"5.10 SU（約 US$0.01）"` | new display |
| test_web_cost.py test_where_and_amount_per_row | row `"5.10 SU"` | `"5.10 SU（約 US$0.01）"` | new display |
| test_web_cost.py test_no_other_currency... | forbidden word list had `匯率` | `匯率` kept in the list unchanged (fix round); the one footnote sentence `SU 換美元依 <as_of> 匯率約略換算，不是帳單。` (and its English twin) is cut out of the page text first, then every forbidden word is checked | footnote exempted by removing that exact sentence, no word loosened |
| test_su_in_get_run.py SU_KEYS | five keys | plus usd_approx | key added |
| test_actions_layer.py BASELINE | get_run and my_usage descriptions | one sentence about usd_approx appended, old text whole | sentence added |

No `SU —` assertion was touched (test_web_running, test_web_results_outputs, test_web_board, masthead lines in test_web_cost).

## Fix round 2 (TC-077)

- [x] TC-077 test strengthened (test_su_usd.py test_tc077_other_user_sees_not_found): bob opening ann's run now must give status 404, the exact same page text as bob opening a run id that does not exist, and no ann SU or US$. Code was already right; only the test was weak.
