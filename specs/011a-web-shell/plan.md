# Plan 011a: the web shell — three panes, read-only

- **Slug**: 011a-web-shell. **Branch**: `feat/011a-web-shell`, base **v3**..
- **Tier**: B. The user sees something new, and the maintainer looks at the screenshots. No principle changes, and no deny is weakened. Per ADR 0010, this real page is the demo the maintainer asked for.
- **Created**: 2026-10-17 by the developer-agent from a Plan-agent draft. Facts are on origin/v3 43774c0; re-check the line numbers after #116.

## 給維護者
1. 登入網頁後看到三欄畫面：
   - 左邊是你的 run 清單。專案功能還沒做，頁面會照實寫出來。
   - 中間是選到的那個 run 的五階段板。
   - 右邊是你所有 run 的進度，照階段分組、用顏色加文字標狀態。
2. 右欄最上面一行「本月 SU — · 雲端 —」（B1）。
3. 整頁只能看，沒有會改東西的按鈕。每人只看到自己送出的 run；沒記錄送出者的舊 run 不顯示，只能在本機終端機查。

## Facts
- `platform/abf_platform/web.py` is the 009c app.
  - `create_app` is at :124. It has exactly five routes, at :310-312.
  - A successful login with no `next` gives a dead-end page, "已登入…請回到 AI…" (:234-236).
  - `next` is accepted only as `/c/<32 hex>` (:196, :207).
- The CSP is at `web.py:44-46`: `default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`.
  - There is no `script-src`.
  - `_page` writes one inline `<style>` (:98-103).
  - Every value is escaped through `_esc` (:94).
- The logged-in user comes from `store.web_session_user` and becomes `actions.Caller(user_id, name, lab)` (:301-302).
- The read actions are `list_runs`, `get_run`, `list_compute_envs`, `get_compute_env`, `list_agents` and `list_site_files` (`actions/__init__.py:56-84`). Each has a same-named MCP tool (`mcp_server.py:35-103`).
- A run view (`status._view`, `status.py:48-71`) has `id`, `name`, `status` (running / succeeded / failed / lost), the start and end times, and the task counts. `get_run` adds `failure_reason`.
- There are no stored projects, analyses, stages or costs.
- `ROADMAP.md:98` names the parity test as the check for its "owed parity" row. The test does not exist yet.
- `PLATFORM.md` :8, :372 and :424 say the only web pages are the login and the confirmation page.
- `tests/no_second_run_state_test.sh` forbids a second copy of run state.

## Design decisions (developer-agent)
1. **Rendering.**
   - The page is server-rendered HTML built from Python strings. It has no JavaScript, no build step and no template library.
   - Rendering lives in a new module, `abf_platform/web_board.py`, as pure functions from dicts to strings. `web.py` keeps routes and login.
   - The JS question is revisited at 014 (chat), not decided now.
2. **One new route, `GET /`.**
   - `?run=<id>` selects the run for the middle pane.
   - `?stage=launch|running|results|downstream|finished` picks the stage shown there. Any other value falls back to the run's own stage.
   - With no login, it answers 303 to `/login`.
   - A login with no `next` now goes to `/`. The default target is a constant, so there is no open redirect.
   - `<meta http-equiv="refresh" content="15">` is on `/` only.
3. **No new action and no new MCP tool.**
   - The left and right panes call `actions.list_runs(caller=Caller)`. The middle pane calls `actions.get_run(caller=Caller)`.
   - Both calls go through `run_in_threadpool`.
4. **The stage is a pure function of the run's status, never stored.**
   - `running`, `lost` and `failed` belong to `running`. `succeeded` belongs to `results`.
   - `launch`, `downstream` and `finished` show "—" until later slices bring their facts.
5. **Colour is never the only signal.** Each state gets a class plus a text label and a symbol:
   - running: blue, 執行中
   - succeeded: green, 成功
   - failed: red, 失敗
   - lost: amber, 失聯/暫停
   - Progress uses a native `<progress>` showing (succeeded + cached) / total. It has no `value` when the total is 0, and no `style=` attribute.
6. **Layout.**
   - A CSS grid with three columns, stacked below about 900 px.
   - Left: "我的 run" (newest first), and a note "專案與分析（011b）尚未開放". The bottom has the user name, 設定（尚未開放）, and logout.
   - Middle: with no run selected, "選一個 run". Otherwise, a five-stage strip with arrows, and the stage body (status, times, counts, and `failure_reason` when it failed). The other stages name the feature that provides them.
   - Right: "本月費用", then "NCHC SU —" and "雲端 —" on separate lines, then the five stage groups with counts.
   - Lists are capped at 100 rows, with "還有 N 筆" below the cap.
7. **CSP gets stricter.**
   - `style-src` changes from `'unsafe-inline'` to the sha256 of the one constant stylesheet.
   - Everything else is unchanged.
8. **Maintainer decision (2026-10-17): a run with no recorded submitter is hidden on the web.**
   - The web always passes a `Caller`, never `None`, and relies on the #116 filters.
   - Another person's run and a missing run give the same 404 page.
9. **Parity test, new: `platform/tests/test_web_parity.py`.**
   - Tables:
     - `WEB_ROUTES`: route to the actions it calls.
     - `MCP_TOOLS`: read from the server.
     - `OWED`: actions with an MCP tool but no web route. Each names the slice that clears it: `list_compute_envs`, `get_compute_env` and `list_agents` (012a), `list_site_files` (012d), `launch` and `cancel` (terminal only, with request forms on `/c/`).
     - `INTERNAL`: helpers.
   - It asserts:
     - The public callables of `actions` are exactly the union of the tables.
     - Every web-called action has a same-named MCP tool.
     - Every OWED entry really has no route (the list only shrinks).
     - An AST scan shows `web.py` and `web_board.py` call `actions` only through `WEB_ROUTES` names, and import none of `confirm`, `jobs`, `compute_envs`, `agents` or `status`.
10. **Docs in the same PR.**
    - `docs/PLATFORM.md` :8, :372 and :424 (the route list becomes six), and the CSP line.
    - CHANGELOG.
    - The `web.py` module docstring.

## Tests (red first; the verifier writes the cases)
- TC-H01 login required: no cookie gives 303 to `/login`. A valid cookie gives 200 and the three panes.
- TC-H02 login redirect: a login lands on `/`. `next=/c/<hex>` is still honoured. `//evil` is ignored.
- TC-H03 own runs only: with two users, the other user's run names appear nowhere in the HTML, not even in counts.
- TC-H04 hidden submitter: a run with no `launches` row, or with a NULL user, is shown to neither user. It stays visible with `caller=None`.
- TC-H05 not mine looks missing: another user's run and a missing id give the same 404 page.
- TC-H06 stage grouping: grouped as in decision 4. `stage_of` is a pure table test.
- TC-H07 nothing stored: there is no stored stage, and `no_second_run_state_test.sh` stays green.
- TC-H08 states readable without colour: text labels are present, and the `<progress>` values are correct (no value when the total is 0).
- TC-H09 cost line: two lines with "—", no number and no link.
- TC-H10 `?stage=` input: only the five names are accepted, anything else falls back, and the arrows stop at both ends.
- TC-H11 read-only:
  - No form except logout, which carries CSRF.
  - `POST /` gives 405.
  - Exactly six routes (009c TC-G04 rewritten from five to six).
  - A GET writes nothing (the db file hashes do not change).
- TC-H12 escaping: markup in a run name or in `failure_reason` is escaped, and ids in `href` are quoted.
- TC-H13 CSP: no `script-src`, no `'unsafe-inline'`, a style hash that matches the stylesheet. No `<script>`, `style=` or `on*=` in the HTML, and no external host.
- TC-H14 refresh: the meta refresh is on `/` only.
- TC-H15 Bearer: a Bearer header on `/` gives the login redirect.
- TC-H16 parity: the parity test passes, and both failure modes are shown red.
- TC-H17 caller always passed: an AST check that every read call in the web module passes a `caller=` that is not None.
- TC-H18 empty states: no runs, or an empty or missing `index.db`, gives a page and never a 500.
- TC-H19 long lists: 250 runs gives 100 shown plus "還有 150 筆".
- Visual check (Tier B): the verifier starts `abf-platform web` on loopback with seeded e2e runs, and attaches screenshots of `/`, a succeeded run and a failed run.
- Pins to rewrite, each with old, new and reason in the ledger:
  - TC-G04 (five routes).
  - The login dead-end page text.
  - The CSP string, if it is pinned.
  - The `PLATFORM.md` wording pins.

## Not in this PR
- Stored projects and analyses (011b).
- Run detail, logs, the failure sentence, and resume/restart (011c, 011e).
- Cost numbers (011d).
- Settings, launch form, uploads, results, Studios and chat (012–014, 016).
- `get_board` or any new MCP tool, any JavaScript, any live push.
- Ownership code (#116) and roles (010).

## Constitution Check
- I.2: GET reads only, no way to say yes, and nothing stored about stages.
- ADR 0009 point 7 and #116: the web always passes the logged-in caller.
- ADR 0010: no script, no external resource, and a stricter CSP.
- Safety Net: no hook or deny is changed.
- Governance: tier B, no amendment.

## Contract-review rulings (2026-10-18, developer-agent)
1. **Parity tables (replaces decision 9's table list).** Every public name in `actions` is in exactly one table.
   - `WEB_ROUTES`: read actions a web route calls. Rule: each one has a same-named MCP tool. Contents: `list_runs`, `get_run`.
   - `WEB_ONLY`: the PAGE confirmation channel, which is web-only by design because the MCP side uses the form channel. Contents: `describe_request`, `approve`, `platform_path_for`. A one-line reason is kept next to each entry. The same-name rule does not apply here.
   - `OWED`: actions with an MCP tool but no web route yet. Exactly six names: `list_compute_envs`, `get_compute_env`, `list_agents`, `list_site_files`, `launch`, `cancel`. The test pins the set, so adding a name means changing the test and this plan.
   - `INTERNAL`: helpers, classes and constants that no route or tool exposes by name. Contents: `request_launch`, `request_cancel`, `find_approved`, `void_request`, `person_at`, `caller_area`, `confined_samplesheet`, `read_confined_samplesheet`, `Caller`, `NotApproved`, `PAGE`, `ELICITED`, `TERMINAL`, `DEFAULT_WEB_BASE`, and any other non-callable constant.
   - Assertions:
     - (a) The union of the four tables equals the public names of `actions`.
     - (b) Every `WEB_ROUTES` name has a same-named MCP tool.
     - (c) No `OWED` name is called by a web route.
     - (d) The AST scan of `web.py` and `web_board.py` uses only names from `WEB_ROUTES`, `WEB_ONLY` and `INTERNAL`.
   - The two red demos for TC-H16: a new public function in no table, and an `OWED` name called by a web route.
2. **Arrows.** They are links to the previous and next stage. `launch` has no previous stage and `finished` has no next one.
3. **Placeholder stages.** Each shows "—" and the feature id that will provide it: launch → 012b, downstream → 016, finished → 013b.
4. **Caps.** Every list (the left list and each right-hand group) is capped at 100 rows, with "還有 N 筆" below. A group header shows the full total.
5. **The 404 page.** It never echoes the requested id. Another user's run and a missing id get byte-identical pages.
6. **Symbols.** running ▶, succeeded ✓, failed ✗, lost ⏸. The tests check the text and the class. The screenshot shows the symbols.
7. **Manual steps.** Add `docs/TESTING.md` steps for the visual check and the ledger review.

## Ruling after acceptance round 2 (2026-10-18, developer-agent): option B
- The cost line is labelled `SU —` and `雲端 —`, not `NCHC SU`. Code stays site-neutral (tc069/tc070 unchanged). The site's name will come from the compute environment's own name once 011d shows real costs.
- Remove the `test_launch_static.py` exemption and restore tc069/tc070 exactly.
- Strengthen `test_tch21_stage_strip_and_bodies` to assert the end time and each task-count number shown in the middle pane, as TC-H21c says.
- The contract amendment for TC-H09b ("SU —" instead of "NCHC SU —") is made by the verifier in contract mode, not by the executor.

## Layout redo: option B "Galaxy three-column workbench" (maintainer chose B, 2026-10-18)
The maintainer rejected the round-2 layout. The backend of this PR (routes, owner rule, parity tables, caps, 404, symbols, cost labels) STAYS; only the page layout and its stylesheet are redone in `web_board.py` (and the shared style if it lives in `web.py`). Visual reference, committed next to this plan: `specs/011a-web-shell/layoutB-reference.html` (zero JS, one stylesheet, no inline style — its CSS is the starting point for STYLE). `design-brief-v3.md` describes the full product; everything in it beyond the list below is LATER slices (011b–e, 012, 013, 014), not this PR.

L1. Top bar: thin dark strip; left `agentic-bioflow`, right the user's name and a `中｜EN` switch.
L2. Left column 232px: project tree (project → analyses). Projects are not stored yet (Facts), so the tree shows the runs under one honest heading as today, and unbuilt items as grey text `之後開放`. Bottom left: 設定 (grey, 之後開放) and 登出.
L3. Middle column: analysis name + status badge; five-stage strip with classes `is-done` / `is-current` / `is-later` (dashed); one stage content card (progress + 7 task-count cells); `← 上一階段` / `下一階段 →` links (ruling 2 still holds).
L4. Right column 272px: one line `本月 SU — · 雲端 —` (ruling option B labels), then history items grouped by stage, each item a whole block with a status background (number + name / symbol status · key fact); the selected run has a focus outline; failed runs are grouped under 執行中 (maintainer OK 10-18).
L5. Status always = symbol + text + colour (ruling 6).
L6. Zero JS, one stylesheet, no `style=` attribute, no external URL; CSP unchanged except that the single stylesheet's sha256 changes. Below 900px the columns stack: middle, right, left.
L7. Language: every UI string comes from one table with `zh` and `en`; `?lang=en` selects English, default Chinese; the switch is two plain links that keep the current path and selection. No JS, no cookie. Run names and data are never translated.
L8. Tests: keep every existing test green except those that pin the old layout's markup — update those to the new structure and list each changed assertion in the ledger (no assertion may be deleted without a replacement). New: column widths/classes present; stage classes; the 900px media query exists; `?lang=en` renders the English strings and no Chinese UI string from the table; no `style=`, no `<script`, no `http` URL in any page.
L9. Manual: re-take the screenshots (wide and <900px, zh and en) into the PR for the maintainer.

### Rulings after layout-B contract round (2026-10-18, developer-agent)
- B1 Cost line: L4 wins (the maintainer chose layout B, which shows it this way). One line `本月 SU — · 雲端 —`, no "本月費用" heading, no line count pinned. This supersedes 給維護者 point 2, decision 6's two-line wording and the old TC-H09 wording. 給維護者 point 2 now reads: 右欄最上面一行「本月 SU — · 雲端 —」。
- B2 Stage classes: the run's own stage is `is-current`; stages before it `is-done`; stages after it `is-later`. A `?stage=` selection does not change classes; the selected cell gets `aria-current="step"` and a focus outline instead. A succeeded run's own stage is results.
- B3 History item: number = the run's sequence number among this user's runs ordered by start time, oldest = 1 (newest first in the list, like the reference). Key fact: running → `done/total` tasks; failed → first line of `failure_reason`, cut to 80 characters; succeeded → end time; lost → `—`.
- B4 Unbuilt items: the single grey text `之後開放` everywhere (left tree items, 設定). This supersedes decision 6's "專案與分析（011b）尚未開放" and "設定（尚未開放）" wording.
- B5 Right-pane groups: follow the reference — 執行中 (running, failed), 結果 (succeeded, lost), and one grey block `之後開放` standing for 送出, 下游, 完成. This supersedes decision 6's five groups.
- B6 Language: every link the board pages generate keeps `lang=en` when the page was rendered in English. Only the board pages (and the board's own 404) are translated in 011a; the login and confirmation pages stay Chinese (later slice).

### Rulings after layout-B contract round 2 (2026-10-18, developer-agent)
- C1 lost goes in 執行中 (reference file, decision 4, TC-H06 and B2 agree). B5 is corrected: 執行中 = running, failed, lost; 結果 = succeeded; plus the grey 之後開放 block.
- C2 Wording authority: where 給維護者, decision 6 or the Tests section still carry the old cost/unbuilt/group wording, B1, B4, B5 and C1 win. (給維護者 point 2 has been rewritten.)
- C3 Routes: "exactly six routes" now means the route set of v3 as merged (including 009i's OAuth/consent routes) plus `GET /`. TC-H11 pins that union.
- C4 Failed key fact: the right pane calls `get_run` (with `caller=`) for each failed item shown (at most 100, the cap); `failure_reason` missing or empty -> `原因未記錄` / `reason not recorded`.
- C5 done = succeeded + cached (same as decision 5's progress bar). End time uses the same formatter as the middle pane.
- C6 The seven task-count cells, in this order, zh / en: 成功 succeeded, 快取 cached, 失敗 failed, 中止 aborted, 執行中 running, 等待 pending, 已送出 submitted (receiver.COUNT_FIELDS). Tests may pin label-number pairs.
