# 設定頁第一刀：使用前檢查＋運算環境＋憑證（唯讀） progress ledger

- [x] 設定頁第一刀 done: `platform/abf_platform/web_settings.py` (new) draws the middle column; `web.py` `settings` handler reads `list_compute_envs`, `list_agents`, `list_my_tokens` and calls `web_settings.render`; new read action `actions.list_my_tokens`. Tests: `platform/tests/test_web_settings.py` (RED commit first, then GREEN).

## 裁決 3 (parallel lanes)
Chose **(b)**: `web_board.py` is untouched. `web_settings.render` calls `web_board._frame` directly; `web_board.render_settings` / `_settings_page` / `SETTINGS` stay (the three lower sections reuse `SETTINGS[3:]` and its string keys). `web.py`: one import (`web_settings`) and the inside of the `settings` handler only.

## 裁決 6 (CSS)
No CSS added. The page reuses existing classes (`.tbl` already wraps with `overflow-wrap:anywhere`, `.chip` + `.state-succeeded|failed` for the status colour, `.muted`, `.off`, `.badge`). There is no `static/*.css` in this repo (the one stylesheet is `web_board.STYLE`, unchanged), so the CSP hash is unchanged.

## 裁決 8: compute env status -> display (from `compute_envs.py:39`: creating, available, invalid, unsupported, disabled)
| status | table | checklist item 3 |
|---|---|---|
| available | ✓ 可用 | ✓ if its agent is online, else ✗ 站台代理離線。 |
| invalid | ✗ 無法使用 + message | ✗ 主要運算環境無法使用：message |
| unsupported | ✗ 無法使用 + message | same |
| disabled | ✗ 無法使用 + message | same |
| creating | — 未檢查 | ✗ 主要運算環境無法使用：message |
| any other value | — 未檢查 (never ✓) | ✗ (only `available` passes) |
"Primary" for item 3 = the environment flagged primary; if none is flagged, the first one (list order).

## 裁決 4: edits to existing assertions (file, old -> new, why)
1. `platform/tests/test_web_board.py` `test_tcs39_s40_s41_s42_settings` (h2 list, ~line 951): 6 headings -> 7 headings with `使用前檢查` first. Named by the plan. The other two named assertions (`之後開放` >= 6, no `<a` in the middle column) still hold, so they were NOT changed. No form/input/select/textarea/button assertion and no banned-word assertion was loosened.
2. NOT named by the plan, needed by it: `platform/tests/test_web_board.py` `test_tn10_n13_n17_n19_n20_nothing_beyond_the_plan` (~line 1221) banned `<table` on every page. The plan requires two tables on `/settings`. Now `<table` is allowed on `/settings` only; `<textarea`, `<select`, `<iframe`, radio and checkbox are still banned everywhere, and `<table` is still banned on every other URL. **Needs the developer-agent's / verifier's sign-off.**
3. NOT named by the plan: parity tables in `platform/tests/test_web_parity.py`. `list_my_tokens` added to `WEB_ONLY` (web page only, no MCP tool, so no pinned tool list or tool count changed anywhere). The settings page must read the agents, so `list_agents` moved from `OWED` to `WEB_ROUTES` (the list only shrinks, as its comment demands): `test_tcs06` (`{"get_compute_env","list_site_files"} <= OWED`), `test_tcs07` (literal OWED set, now without `list_agents`), `test_tch16h` (its example of an owed name was `list_agents`, now `get_compute_env`; same guard strength). **Needs sign-off.**
4. `platform/tests/test_web_actions.py`: tc060 loop now also covers `web_settings.py` (stricter only).

## Tool list / count pins
No change: `list_my_tokens` has no MCP tool (the plan: "only when parity requires"; WEB_ONLY satisfies parity).

## Migration
Not needed: no table or column added (`list_my_tokens` reads `store.list_pats`).

## More edits to existing assertions (found by the full suite)
5. NOT named by the plan: `platform/tests/test_pat.py::test_tca11_no_tool_route_or_action_creates_or_revokes_users_or_pats` (line ~287) forbids any name in `actions` that matches `user|pat|token`. The plan fixes the new read's name as `list_my_tokens` (ruling 2), so it now exempts exactly that one name (`and n != "list_my_tokens"`). The MCP-tool check and the route check next to it are unchanged, so no create/revoke action can hide behind the exemption except by that exact name. **Needs sign-off.**
