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

---

# REDO per web design v1 (2026-10-18 night) — SUPERSEDES the layout sections above

kind: ui + backend. The maintainer approved web design v1 (UI/UX session; his words: 「確保目前這個介面跑得動整趟分析流程後，就把這第一版送回主開發session」). Authority for every screen is now `DESIGN.md` and `PRODUCT.md` at the repo root (added in this branch) and the reference demo `specs/011a-web-shell/design-v1-demo.html`. Everything above about layout B (L1–L9, B1–B6, C1–C6) is superseded where it conflicts with DESIGN.md; the backend of this PR (routes, owner rule, parity tables, caps, 404 rule, symbols, read-only, CSP) STAYS.

## G0 First step
`git merge origin/v3` (plain merge, never rebase or force). Expect conflicts in docs/PLATFORM.md, platform/tests/test_confirm_page.py, test_review_fixes_2.py and others: keep both sides (v3 has since gained keep-submissions/forget, 009e resume/relaunch, OPERATIONS/MIGRATION/INSTALL docs, 013a). Commit the merge on its own.

## Scope of 011a (the frame only; later slices are 011b–e, 012a–d, 013a/b, 014, 016)
G1 Top bar: as DESIGN.md (product name, the cost readout linking to the cost page — the cost page itself is 012d, so the link target shows "之後開放"/coming later), user name, 中｜EN.
G2 Left pane: project tree as DESIGN.md. Projects are not stored on the platform yet — show the user's runs under one honest heading and unbuilt items in grey "之後開放", exactly as DESIGN.md specifies for the not-yet state.
G3 Right pane: progress column as DESIGN.md (the Progress｜Chat toggle shows Chat greyed "之後開放" — chat is 014).
G4 「現在」home page with the notification component (running / needs attention cards from list_runs) as DESIGN.md.
G5 Five-stage strip with done/current/later states styled as DESIGN.md (colours, dashed later).
G6 Settings page shell (keys only; every unbuilt item greyed), login page restyled to DESIGN.md, ≤900px stacking, `?lang=en` (links keep lang).
G7 Times shown in Asia/Taipei in a human format (DESIGN.md), never raw ISO.
G8 Still read-only in 011a: no write action from the web in this slice (launch/upload/resume pages are 012/011b+). Zero JS unless DESIGN.md marks a JS spot inside this slice's screens — then stop and list it in the ledger, do not add JS here.
G9 Tests: keep every backend test green; update old layout-markup tests to DESIGN.md structure, each changed assertion listed in the ledger (old/new/reason), none deleted without replacement. Pin: no `style=` attribute, no `<script`, no external URL; every link on every 011a page resolves (no dead link); `?lang=en` has no Chinese UI string from the table.
G10 Manual: Playwright screenshots, desktop width and phone width, zh and en, of 「現在」, a selected failed run, the empty state, settings, login — attach to the PR.
G11 Run `/impeccable critique`-equivalent self-check is NOT the executor's job; the developer-agent does it on the screenshots.

## 專長守則（ui）

# 專長守則：ui（改畫面的任務）

### executor

- 先讀專案根目錄的 `PRODUCT.md`（給誰用、要解決什麼）與 `DESIGN.md`（版面線框、tokens、每個畫面與狀態、維護者的原話例子）。讀不到就 BLOCKED，不自己發明設計。
- 只准用 `DESIGN.md` 定義的 tokens（色彩、字型、字級、間距、圓角）與版面。不新增任何視覺決策：不自創顏色、字型、間距數值，不順手「美化」。
- `DESIGN.md` 沒決定的事，一律寫進報告的「卡住的原因／要問的問題」，不猜。
- `DESIGN.md` 列出的每個畫面、每個狀態都必須做出來，包含空狀態、載入中、錯誤、失敗。少一個就不算完成。
- 遵守計畫寫明的前端限制（例如 CSP、禁用 inline style、不載外部資源、只在允許處使用 JS）。限制與設計衝突時停下來問，不自行取捨。
- 狀態絕不只靠顏色：一律「符號＋文字＋顏色」三者並用。
- 手機寬度可用（不橫向捲動、點擊目標夠大），鍵盤操作時焦點外框可見。
- 介面文字用使用者視角的白話，不露出內部術語、錯誤代碼或程式名詞；錯誤訊息說發生什麼事與下一步。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- `DESIGN.md` 的每個畫面、每個狀態都至少對應 1 個 TC（含空、載入、錯誤、失敗）。
- 維護者的原話例子逐字對應到 TC。
- 計畫列的前端限制各對應 TC（例如頁面不得含 inline style、不得請求外部網址、CSP 標頭存在）。
- 狀態表達 TC：每個狀態輸出的 HTML 同時含符號、文字，不得只靠 class 顏色。

**ACCEPTANCE（閱卷）必須檢查：**
- 把每個有改動的頁面渲染成 HTML 檔（用專案的 test client，或計畫指名的 fixture）。做不到就標 UNVERIFIED，並寫明需要什麼才能驗。
- 對渲染出的 HTML 跑 Impeccable 偵測器（唯讀）：`sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`。
- **FAIL**：違反 `DESIGN.md` 的 tokens／畫面／狀態；違反計畫寫明的前端限制；狀態只靠顏色；缺少 DESIGN.md 列出的畫面或狀態。
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型、AI 範本味等）與品味問題。這些不判 FAIL。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。

## 專長守則（backend）

# 專長守則：backend（動作層、資料、權限）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。

## Rulings after design-v1 contract round (developer-agent, 2026-10-18)
- R1 Cost readout (B-1): two plain-text lines in the top bar, `SU —` and `雲端 NT$ —` (en: `SU —`, `Cloud NT$ —`); no site name in code (option-B ruling, tc069/tc070 unchanged); no progress bar and no link in 011a (the cost page is 012d; no dead link). DESIGN.md's NCHC label and bar arrive with 012d.
- R2 Parity after merging v3 (B-2): every public action that an MCP tool calls and no web route calls goes in OWED; helpers no tool exposes by name (`forget_check`, `keep_screen`, and any `request_*` helper not itself a tool target) go in INTERNAL. Replace the "exactly six" pin with: OWED equals the set computed by that rule at this merge, written out literally in the test and the ledger, and it may only shrink. If #138 (read_task_log) lands first, it joins OWED by the same rule.
- R3 「現在」 notifications (B-3): read-only, from list_runs only. Card 「正在跑」 = running runs. Card 「需要注意」 = failed and lost runs, each a plain line with symbol, name and (failed) the first line of the failure reason; no buttons; each line links only to that run's own detail on the board (exists). Counts = the number of items in each card. No 「系統自動處理紀錄」 table and no 「待你決定」 count in 011a.
- R4 Settings (B-4): route `GET /settings`, read-only, zero JS; every section, including the model key, is grey 「之後開放」 (key entry needs browser storage/JS → 012a/014). Add `/settings` to the pinned route set.
- R5 Login and confirmation pages (B-5): login fields stay name + password (no PAT field, no "remember 12 h"; constitution 5.0.0). Login, `/c/…` and `/consent/…` use the new shared stylesheet but stay Chinese (B6 stands).
- R6 Right column (B-6): item line 2 = symbol + status + `done/total` (no "current step" in 011a); failed items keep the failure-reason key fact (C4). Groups: 執行中 (running, failed, lost) / 結果 (succeeded) / one grey 之後開放 block. Counter row shows only ▶ running, ! needs attention (failed + lost), ✓ succeeded; the other DESIGN.md states are not shown in 011a.
- R7 Non-blocking: tokens and font sizes from DESIGN.md (dark tokens copied from the demo's :root); time format `MM-DD HH:mm` Asia/Taipei; DESIGN screens 2 (first-use setup) and 11 (cost page) are out of scope; search box, ＋新專案, 上傳資料 are grey 「之後開放」 with no input. The superseded text earlier in this plan need not be deleted; this section and "REDO per web design v1" win.
