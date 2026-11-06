origin/v3 sha: 62c91293de611d265d8fbf3d0a128bea849be98c

# UI3: design report for backlog item settings-ce-table-mobile

Kind: ui-report (design only). Shard C, cloud-burn v2. No repository file was edited. Every `file:line` below refers to the sha above.
Inputs I read: `platform/abf_platform/web_settings.py`, `platform/abf_platform/web_board.py` (STYLE), `DESIGN.md`, `specs/settings-ce-table-mobile/{plan,ledger}.md`, `platform/tests/test_web_settings_ce_mobile.py`, `scripts/dev/ui_check.py`, `scripts/dev/check_settings_mobile.py`.

## TL;DR

1. **The backlog item has already landed on origin/v3.** The 390 px card layout the brief asks me to propose already exists:
   - `web_settings.py:178-180`: every `<td>` carries `data-label`.
   - `web_settings.py:287`: the table has `class="tbl ce"`.
   - `web_board.py:275-278`: one `@media (max-width:640px)` block.
   - Tests: `platform/tests/test_web_settings_ce_mobile.py`, 10 tests, all pass here.
   - Plan and ledger: `specs/settings-ce-table-mobile/`.

   I reproduced the page with `ui_check`. At 390 px, in zh and en, each environment is one card with a label on each field. No label or status word is cut mid-letter. `scrollWidth == clientWidth`.
2. **The same bug is still there at desktop and tablet widths, and it is worse than the original phone bug.** The card switch depends on the *viewport* width (640). The table's real width depends on the three-column grid (`web_board.py:192-193`, `:279`).
   - From 901 px to about 1313 px of viewport, the middle column is narrower than it is on a 390 px phone. At 901 px the table is 299 px wide (on a phone it is 308 px). Its six fixed columns are 50 px each.
   - Words are cut mid-letter: "Nam|e", "Av|ailable", "Unav|ailable", "N|ot ch|ecked", "Regi|stered", "站台|代理", "可|用".
   - A smaller band, 641 to about 721 px, cuts "Unavaila|ble".
   - 1024 px is iPad landscape and small laptops.
   - Neither manual check (`ui_check.py`, `check_settings_mobile.py`) looks at these widths: both use only 1440 and 390.
3. **Proposed follow-up: make the card switch follow the table's container instead of the viewport.** This means one CSS container query, one wrapper `<div>`, and the same five rules.
   - Tested in scratch by injecting it into the rendered page: no mid-letter breaks remain at any width from 320 to 1440 px, in zh or en. The one exception is the 40-character commit id, which cannot be wrapped any other way.
   - The 1440 px rendering stays pixel-identical.
   - This is HOT work (`web_board.py`, `web_settings.py`, `test_web_*`). It needs a maintainer ruling on changing the two existing CSS-shape assertions.

## 1. Reproduction

Environment:
- Cloud VM, Chrome for Testing at `$CHROME_PATH=/usr/bin/google-chrome`.
- `playwright` and `axe-playwright-python` from PyPI, in `/tmp/cb/ui3/venv`.
- The platform was pip-installed from the scratch worktree `/tmp/cb/ro-UI3`.
- The bundled Playwright Chromium is revision 1248. `/opt/pw-browsers` has 1243. Because of that mismatch, `ui_check.py` was run **unchanged** through a 10-line wrapper that only adds `executable_path=$CHROME_PATH, args=["--no-sandbox"]` to `chromium.launch` (`/tmp/cb/ui3/bin/run_ui_check.py`).

### 1a. ui_check (the project's own check)

```
python run_ui_check.py scripts/dev/ui_check.py --start --pages settings --out /tmp/cb/ui3/out
| page | width | lang | HTTP | critical | serious | moderate | minor |
| settings | 1440 | zh | 200 | 0 | 0 | 1 | 0 |
| settings | 1440 | en | 200 | 0 | 0 | 1 | 0 |
| settings | 390 | zh | 200 | 0 | 0 | 1 | 0 |
| settings | 390 | en | 200 | 0 | 0 | 1 | 0 |
Serious / critical violations: none
```
- The one moderate violation is `landmark-unique` on `.side` (the left rail). It has nothing to do with this item.
- Screenshot `settings-390-en.png`: one card for `lab-a`, with the labels Name / Platform / Status / Site agent / Registered pipelines / Last used. Nothing is cut. The original bug ("Nam/e", "Av/aila/ble", plan.md:17) does **not** reproduce on origin/v3.

### 1b. Existing tests

```
cd platform && python -m pytest -q -p no:cacheprovider tests/test_web_settings_ce_mobile.py
10 passed in 3.03s
```

### 1c. Width sweep with realistic data (`/tmp/cb/ui3/bin/probe.py`)

`ui_check --start` seeds only one environment with short values. To stress the layout, the probe renders `web_settings.render(...)` directly. `web_settings.py:2-6`: the module reads nothing itself, so this is the real page markup plus STYLE. It uses three environments:
- a primary Slurm one with a 30-character agent name and three registered pipelines (one revision is a 40-character commit id);
- an `invalid` cloud one with a long provider message;
- an unchecked one.

The page is loaded into Chrome at 18 widths. For every word in `table.ce`, the probe uses `Range.getClientRects()` and reports a **mid-letter** break: a line break that does not follow `-`, `/`, `.`, `_` or `:`.

| viewport | table layout | table width px | col width px | mid-letter breaks en / zh | examples |
|---|---|---|---|---|---|
| 320–600 | cards | 238–518 | – | 1 / 1 (the 40-char commit id only) | – |
| 640 | cards | 558 | – | 0 / 0 | – |
| **641** | table | 559 | 93 | **4 / 4** | `Unavaila|ble`, `nf-core/amplis|eq`, `上次使用時|間` |
| **700** | table | 618 | 103 | **3 / 2** | `Unavailabl|e` |
| 768–900 | table | 686–818 | 114–136 | 1 / 1 (commit id) | – |
| **901** | table | **299** | **50** | **28 / 24** | `Nam|e`, `Platf|orm`, `Av|ailable`, `Un|available`, `N|ot`, `ch|ecked`, `Regi|stered`, `站台|代理`, `可|用`, `無|法使用` |
| **1024** | table | 422 | 70 | **17 / 16** | `Register|ed`, `Availa|ble`, `Unav|ailable`, `chec|ked`, `已登記管|線`, `未檢|查` |
| **1100** | table | 498 | 83 | **12 / 10** | |
| **1200** | table | 598 | 100 | **3 / 2** | `Unavailabl|e` |
| **1201** | table | 527 | 88 | **7 / 6** | |
| 1314–1440 | table | 640–766 | 107–128 | 1 / 1 (commit id) | – |

`scrollWidth == clientWidth` at every width. There is no sideways scroll: the bug is readability, as in the original report.

Screenshots (scratch only, not committed):
- `/tmp/cb/ui3/probe-base/ce-901-en.png` (the table cut into 50 px columns) and `/tmp/cb/ui3/probe-base/ce-1024-en.png`.
- `/tmp/cb/ui3/probe-base/ce-390-zh.png` (the current, good card layout).

## 2. Design as built (what DESIGN.md and the plan decided)

- DESIGN.md has no section for responsive tables. It decides only these points:
  - the skeleton breakpoints (DESIGN.md:38: "≤1200px: 232 / fluid / 300. ≤900px: one column");
  - "Single stylesheet, no inline style" (DESIGN.md:93);
  - tokens only (DESIGN.md:40-42);
  - "Visual polish is postponed" (DESIGN.md:98).
- The card layout follows the plan, except the cell rule: plan.md:47 specified `td{display:grid;…}`, which was replaced by `display:flow-root` + a floated label after TC-008 failed (`specs/settings-ce-table-mobile/ledger.md:14`) (`specs/settings-ce-table-mobile/plan.md:41-53`, rulings A–D at :101-105, rulings 13/14 at :136-144):
  - Markup: `<table class="tbl ce">` (`web_settings.py:287`). `<td data-label="th_*">` uses the existing header strings, so no new string is added (`web_settings.py:178-180`).
  - CSS (`web_board.py:275-278`), with every selector scoped by `.tbl.ce` and placed inside `@media (max-width:640px)`:
    - the table and tbody become blocks, and thead is hidden;
    - each `tr` becomes a card: `--raised` background, 1px `--line` border, radius 6, padding 8/12, margin 0 0 12;
    - each `td` is `display:flow-root` with a 6rem left pad;
    - `td::before{content:attr(data-label);float:left;width:5.5rem;margin-left:-6rem;color:var(--muted);font-size:12px}`.
  - The base `.tbl` rules (`web_board.py:251-252`: `table-layout:fixed` and `overflow-wrap:anywhere`) are untouched. Those two rules are what cut the words whenever the table is narrow.
- Guarded by `test_web_settings_ce_mobile.py`:
  - ce01–ce03: class and labels;
  - ce04/ce05: one 640px `@media` block contains every `.tbl.ce` rule;
  - ce06: tokens only;
  - ce07: other tables untouched;
  - ce08: strings unchanged and cell not grid/flex;
  - ce09: no inline style.

## 3. Findings

### F1 (P2 risk): the card switch is keyed to the viewport, so the compute-environment table cuts words mid-letter from 901 to about 1313 px (and from 641 to about 721 px)

- **Evidence**:
  - The media query is `@media (max-width:640px){.tbl.ce…` (`web_board.py:275`).
  - The three-column grid is `272px | fluid | 320px` above 1200 (`web_board.py:192`) and `232 | fluid | 288` at ≤1200 (`:193`). It drops to one column only at ≤900 (`:279`).
  - So at 901 px the middle column takes 901 − 232 − 288 ≈ 381 px. After the `.main` padding (24, `:208`) and the card padding, the table gets 299 px, which is less than on a 390 px phone (308 px).
  - Base `.tbl{table-layout:fixed}` plus `overflow-wrap:anywhere` (`web_board.py:251-252`) splits that into six equal 50 px columns, and words break anywhere.
  - Numbers and examples: table in §1c, screenshots `/tmp/cb/ui3/probe-base/ce-901-en.png`, `/tmp/cb/ui3/probe-base/ce-1024-en.png`.
  - The maintainer's own complaint ("字被切成「Nam/e」「Av/aila/ble」", plan.md:20) applies word for word at 901 px ("Nam|e", "Av|ailable").
- **Reproduction**:
  - Open `/settings` with two or more environments at a 1024 × 768 viewport (iPad landscape) or 901 px.
  - Or run `PROPOSAL= python -I /tmp/cb/ui3/bin/probe.py <outdir>` and read `probe.json`: `en-901` gives `hard=28`, `en-1024` gives `hard=17`.
- **Proposed fix**: §4 (container query). It was tested in scratch with the same probe and `PROPOSAL=1`:
  - mid-letter breaks fall to 0 at 641/700/722/901/1024/1100/1180/1200/1201/1280/1314 in zh and en; only the unwrappable 40-character commit id remains, the same as today at 390;
  - the table layout is unchanged at 768–900 and ≥1315;
  - the element screenshots at 1440 en and 1440 zh are byte-identical to the current ones (`cmp`: same);
  - at 390, the cards look identical but the element screenshot is 12 px shorter, because the last card's bottom margin now ends inside the wrapper. Nothing else changes visually.
- **Proposed RED tests** (names):
  - `test_ce10_card_rule_follows_container_not_viewport`: STYLE contains `.cewrap{container-type:inline-size}` and `@container (max-width:640px){`, which holds every `.tbl.ce` rule. No `.tbl.ce` selector sits under any `@media`. Red today.
  - `test_ce11_ce_table_wrapped_in_container`: the settings middle column contains `<div class="cewrap"><table class="tbl ce">`. Red today.
  - `test_ce12_other_tables_not_wrapped`: `cewrap` appears only in `web_settings.py` (the same pattern as ce07). It passes today; it guards scope.
  - Browser check (manual, not CI, as ruling D allows): extend `scripts/dev/check_settings_mobile.py` from `((1440, False), (390, True))` (`:31`) to also take 1024 and 901, and add the Range mid-letter heuristic from plan.md:70. Screenshot names: `settings-ce-{901,1024}-{zh,en}.png`.
- **HOT?** Yes. The fix touches `web_board.py` and `web_settings.py` (HOT `web*.py`), plus `test_web_settings_ce_mobile.py`, `test_clean_page.py` and `test_web_settings_register.py` (the first and the third are `test_web_*`, HOT; `test_clean_page.py` is not on the HOT list). The new TC ids also go into `specs/…/test-case.md`, which is FORBIDDEN for cloud agents (see "Additions by critic").
- **Suggested tier**: B. It needs a maintainer ruling because ce04/ce05 (`test_web_settings_ce_mobile.py:62-77`) assert the *shape* `@media (max-width:640px){` and `css.count(MEDIA) == 1`. Those two assertions must be rewritten to the container form (same intent: every `.tbl.ce` rule inside one guarded block, none leaking to the base). The STYLE hashes must be re-pinned under the precedent of rulings 13/14 (plan.md:136-144).

### F2 (P3 cleanup): the manual UI checks cover only 1440 and 390, so the three-column band is never looked at

- **Evidence**:
  - `scripts/dev/ui_check.py:34` has `WIDTHS = {1440: 900, 390: 844}`.
  - `scripts/dev/check_settings_mobile.py:31` checks only 1440 and 390.
  - The docs prescribe the same two widths: `docs/TESTING.md:374`, :962-966.
  - F1 shipped through all of these checks.
- **Reproduction**: run either script. Both pass while 901–1313 px is broken (§1a vs §1c).
- **Proposed fix**: add a third width, 1024 (×768), to `ui_check.WIDTHS`. This makes 6 screenshots per page; update the docstring "4 per page" at `ui_check.py:12` and `docs/TESTING.md`. Optionally add 901 to `check_settings_mobile.py`. `tests/ui_check_script_test.sh` has no width or count assertion (grep: no `390`, `1440` or `4 per`), so it is unaffected.
- **Proposed RED test**: `ui_check_script_test.sh: widths include a three-column tablet width (1024)` (static grep on `WIDTHS`).
- **HOT?** No for `scripts/dev/ui_check.py`. Yes for the `docs/TESTING.md` wording.
- **Suggested tier**: C for the script and B for the TESTING.md paragraph.

### F3 (P3 cleanup): a 40-character commit-id revision is wrapped mid-id at every width up to about 1440

- **Evidence**:
  - The "Registered pipelines" cell prints `pipeline revision` verbatim (`web_settings.py:176`).
  - A revision may be a 40-character commit id (`pf_e_revision`, `web_settings.py:46,89`).
  - It has no break opportunity, so `overflow-wrap:anywhere` splits it (`0123456789abcdef01234567|89abcdef01234567` at 390; still split at 1440).
- **Reproduction**: §1c, every row; the probe's third pipeline.
- **Proposed fix**: none needed for this item. This is expected and the plan accepts it (plan.md:70 "長字串…不算失敗"). If wanted later: show the first 12 characters with the full id in `title` (that changes the cell contents, so it belongs to a separate item).
- **Proposed RED test**: `test_ce13_commit_revision_shown_short` (only if that item is taken).
- **HOT?** Yes (`web_settings.py`).
- **Suggested tier**: C (cosmetic).

### F4 (P3 cleanup, documentation drift): DESIGN.md column widths do not match STYLE

- **Evidence**: DESIGN.md:37 says the right column is "360px" and DESIGN.md:38 says "≤1200px: 232 / fluid / 300". STYLE has `272px minmax(0,1fr) 320px` (`web_board.py:192`) and `232px minmax(0,1fr) 288px` (`:193`). F1's measured widths follow STYLE.
- **Reproduction**: read the two lines.
- **Proposed fix**: the maintainer decides which one is right. DESIGN.md is HOT, so this report does not touch it.
- **Proposed RED test**: none. This is a doc-only finding; the test (if any) would be a skeleton-width snapshot, and that is out of scope.
- **HOT?** Yes.
- **Suggested tier**: B (design document).

## 4. Proposed change list for a follow-up (`settings-ce-table-container`), design only

| # | File (HOT) | Change |
|---|---|---|
| 1 | `platform/abf_platform/web_settings.py` `_compute` (:287) | `'<div class="cewrap"><table class="tbl ce">…</table></div>'`: one wrapper. No string, attribute or `<td>` change. `_env_block` stays below it, untouched. |
| 2 | `platform/abf_platform/web_board.py` STYLE (:275) | Replace `@media (max-width:640px){` with `.cewrap{container-type:inline-size}@container (max-width:640px){`. The five inner rules on four source lines (:275-278) stay **byte-for-byte the same**. No new colour, token, px value or JS. |
| 3 | `platform/tests/test_web_settings_ce_mobile.py` | Add ce10–ce12 (F1). Rewrite the `MEDIA` constant (:12) and ce05's `count == 1` to the `@container` opener. The intent ("every `.tbl.ce` rule in one guarded block, none in the base") is kept; this needs a ruling. |
| 4 | `platform/tests/test_clean_page.py:158-163` (the five page-hash constants and `BASE_STYLE`; asserted at :468), `platform/tests/test_web_settings_register.py:18` (asserted at :859) | Re-pin the STYLE and page hashes, with the ledger proof that only STYLE changed (rulings 13/14). |
| 5 | `scripts/dev/check_settings_mobile.py` (+ `docs/TESTING.md` §settings-ce-table-mobile) | Also check 901 and 1024 and report mid-letter breaks (F2). |

Why a container query and not another `@media` range:
- The table's available width is set by the grid, not the viewport. A container query states that directly, and it keeps working if the 232/288/272/320 column widths change (F4).
- The threshold of 640 container px means:
  - viewport ≤ about 722 in the one-column layout;
  - viewport 901 to 1314 in the three-column layout (at 1314 the container is exactly 640 px, so `max-width:640px` still matches; critic re-ran the probe: `en-1314`/`zh-1314` render as cards with `PROPOSAL=1`).
  - Phones (≤ 640 viewport) get cards exactly as today.
- The alternative, `@media (max-width:640px),(min-width:901px) and (max-width:1313px)`, needs no wrapper. But it hard-codes the grid arithmetic and adds new breakpoints, which plan.md:93 "不加…新斷點" forbids for that lane.

Risk:
- Container queries need Chrome/Edge 105+, Safari 16+ and Firefox 110+. In an older browser the table simply stays a table (today's desktop behaviour), including on phones.
- If phone fallback on such browsers matters, keep the existing `@media (max-width:640px)` block as well. That duplicates four rules and breaks ce05's single-block assertion. My recommendation is to accept the modern-browser floor: the platform already depends on CSS grid and `minmax`. That choice is the maintainer's.

## 5. Not done / limits

- No repository file was written. The worktree `/tmp/cb/ro-UI3` was used read-only (pytest ran with `-p no:cacheprovider`).
- The proposal (§4) was checked only by injecting it into rendered HTML in scratch, not as a code change. Full `run_all.sh` was not run, because nothing changed.
- Seeding three environments through the real database was skipped. The probe uses `web_settings.render` with dict environments, which is the same input `web.py` hands it (`web_settings.py:4`). The `ui_check --start` run (§1a) covers the real server path with one environment.
- The git history of this checkout is shallow, so I could not find the PR number that landed settings-ce-table-mobile.

## Refuted

- "The 390 px bug still reproduces on origin/v3": refuted. `ui_check` at 390 in zh and en and the probe at 320–640 show cards with full labels and no mid-letter break other than the commit id. The 10 tests pass.
- "The card layout causes sideways scroll at 390": refuted. `scrollWidth == clientWidth` at every width tested (320–1440, zh and en).
- "The `landmark-unique` axe violation comes from the new table": refuted. It targets `.side` (the left rail), not `table.ce`.

## Corrections by critic

Critic re-checked against origin/v3 `62c91293de611d265d8fbf3d0a128bea849be98c` (worktree `/tmp/cb/ro-UI3`, clean). Wrong or imprecise claims, fixed in place above:

- ~~`scripts/dev/ui_check.py:32` has `WIDTHS`~~ → it is `:34` (`:32` is `DEFAULT_PAGES`).
- ~~docstring "4 per page" at `ui_check.py:11`~~ → `:12`.
- ~~`test_clean_page.py:157-162`~~ → the hash constants are `:158-163` (`:157` is a comment; `BASE_STYLE` is `:163`, asserted at `:468`).
- ~~"(the first is `test_web_*`, HOT)"~~ → `test_web_settings_register.py` is `test_web_*` too, so two of the three test files are HOT.
- ~~"The card layout follows the plan"~~ (unqualified) → the `td` rule deviates from plan.md:47 (`display:grid`); the as-built `display:flow-root` + float came from the TC-008 fix recorded at `ledger.md:14`, and the second `test_ce08_…` now forbids grid/flex on the cell.
- ~~"the same four rules"~~ → `web_board.py:275-278` holds five rules (`.tbl.ce,.tbl.ce tbody`, `thead`, `tr`, `td`, `td::before`) on four source lines.
- ~~"901 to about 1313"~~ for the container-query band → 901 to 1314 inclusive (container = 640 px at 1314). The base-layout table row "1314–1440: 1/1" is correct.

Claims verified as correct (critic re-ran or re-read): sha line; `web_settings.py:2-6`, `:46`, `:89`, `:176`, `:178-180`, `:287` (inside `_compute`, def at `:282`); `web_board.py:192`, `:193`, `:208`, `:251-252`, `:275-278`, `:279`; DESIGN.md:37, :38, :40-42, :93, :98; plan.md:17, :20, :70, :93, :101-105, :136-144; `test_web_settings_ce_mobile.py:12` (`MEDIA`), ce04/ce05 at `:63-77`, `css.count(MEDIA) == 1` at `:77`; 10 tests collected and passing (`10 passed in 2.46s` in `/tmp/cb/ui3/venv`); `check_settings_mobile.py:31`; `docs/TESTING.md:962-968`; `test_web_settings_register.py:18`; `tests/ui_check_script_test.sh` has no `390`/`1440`/`WIDTHS`/`4 per` match; `/tmp/cb/ui3/out/summary.md` matches §1a. The §1c probe was re-run independently (base and `PROPOSAL=1`, outputs in the critic's scratchpad): every table width, column width and hard-break count in the §1c table reproduces exactly (e.g. en-901 = 299 px / 50 px / 28, zh-901 = 24, en-1024 = 17, zh-1024 = 16, en-1201 = 7, zh-1201 = 6); `scrollWidth == clientWidth` everywhere; with the proposal, every width from 641 to 1314 renders as cards with 0 hard breaks except the 40-char commit id; `ce-1440-{en,zh}.png` are byte-identical base vs proposal; `ce-390-en.png` is 308×835 vs 308×823 (12 px shorter), as stated. Screenshot `ce-901-en.png` visually confirms "Nam|e", "Av|ail|ab|le", "Un|av|ail|ab|le", "N|ot ch|ec|ke|d".

Note on the probe heuristic: it counts a break *before* `-` as hard (e.g. `googlebatch|-platform` at 641/1180), and long tokens like `nf-core/amplis|eq`; the counts therefore include some breaks inside long identifiers, not only labels and status words. The conclusion does not change: the header labels and status words alone break at 901–1201.

## Additions by critic

- **Brief coverage.** The brief asks for (a) a `ui_check` reproduction, (b) a reading of `web_settings.py` and DESIGN.md, (c) a card layout under ~640 px with a CSS/HTML change list and RED test names, (d) no edit to `web*.py`. (a), (b), (d) are covered. For (c) the report correctly finds the ≤640 px card layout already merged on origin/v3, documents it as built (§2), and redirects the change list and RED tests to the residual defect (F1, §4). Nothing in the brief is left unanswered.
- **TC ids and FORBIDDEN paths.** Every existing ce test carries a `# TC-0xx` comment tied to `specs/settings-ce-table-mobile/test-case.md`. Any ce10–ce12 RED test needs new TC entries there, and `test-case*.md` is FORBIDDEN for cloud agents (RULES §3). The follow-up therefore goes through the verifier's CONTRACT mode (test-cases skill) before code, in addition to the maintainer ruling on ce04/ce05 already named in F1. Add to §4 row 3: "TC entries in `specs/<follow-up>/test-case.md` written by the verifier, not by an executor".
- **Same pattern elsewhere (unverified, P3).** The launch parameter table uses a viewport-keyed card rule too: `@media (max-width:600px){.ptbl …}` at `web_board.py:273-274` (rendered by `web_launch.py:335`, `:409`). It has per-column percentage widths (`web_board.py:270`) so it may behave differently, and the critic did not probe it; if the maintainer takes the container-query route, `.ptbl` is the obvious second candidate, and the 600 vs 640 thresholds are an existing inconsistency the follow-up could settle. Proposed check (not a RED test yet): run the §1c probe against `/launch` at 901/1024. HOT? yes (`web_board.py`). Tier: C to investigate.
- **Data realism of F1.** The 50 px columns at 901 px are set by `table-layout:fixed` and the grid, not by the seeded data, so the header labels ("Nam|e", "Platf|orm", "Regi|stered") break even with the single short environment that `ui_check --start` seeds; F1 does not depend on the probe's long values. Critic verified this with the probe re-run on one short environment (`lab-a`, `slurm-platform`, `agent-1`, as `ui_check --start` seeds): en-901 cuts `Nam|e`, `Platf|orm`, `Statu|s`, `Regi|stered`, `pipel|ines`, `Av|ailable`; en-1024 cuts `Register|ed`, `pipeline|s`, `Availa|ble`; zh-901 cuts `站台|代理`, `已登|記管線`, `上次|使用時間`, `可|用`; 390 has none. So `/settings` with its default seed is already broken at 1024 px; adding 1024 to `ui_check.WIDTHS` (F2) would have caught it.
