origin/v3 sha: 62c91293de611d265d8fbf3d0a128bea849be98c

# UI2: ui_check.py with axe-core, 6 pages × 1440/390 × zh/en

- **Task:** cloud-burn tasks.json UI2 (shard C, kind ui-report).
- **Run:** `scripts/dev/ui_check.py --start --pages board,launch,settings,results,usage,upload` against a throwaway platform. Its data folder was under /tmp, with HOME and XDG_DATA_HOME pointed at a scratch folder. No real site, agent or cloud account was contacted.
- **Environment:**
  - Python 3.13, Playwright 1.64.1, axe-playwright-python 0.1.8 and `abf-platform` installed from the origin/v3 checkout into a venv under /tmp.
  - `python -m playwright install chromium` failed: the download of Chrome for Testing 156 was blocked (`Download failure, code=1`).
  - A scratch copy of the script (not committed) changed one line, `scripts/dev/ui_check.py:123`, to `p.chromium.launch(executable_path=os.environ['CHROME_PATH'], args=['--no-sandbox'])`. CHROME_PATH is Chrome for Testing 153.0.8010.12.
- **Extra probe:** a second scratch script (same seeding, by importing `start_platform`) dumped the full axe JSON for every page. It also checked horizontal overflow (`scrollWidth` against the viewport, plus any element outside the viewport that is not clipped) and listed interactive targets under 24 px. All 24 screenshots were read by eye.
- **Screenshots:** they stay in the VM at `/tmp/cb/ui2/out/` (24 PNGs plus summary.md).

## Result of the script

| page | widths × langs | HTTP | critical | serious | moderate | minor |
|---|---|---|---|---|---|---|
| board (`/`) | 4 | 200 | 1 each (meta-refresh) | 0 | 1 (landmark-unique) | 0 |
| launch | 4 | 200 | 0 | 0 | 1 (landmark-unique) | 0 |
| settings | 4 | 200 | 0 | 0 | 1 (landmark-unique) | 0 |
| results (`/?run=ui-demo-run&stage=results`) | 4 | 200 | 1 each (meta-refresh) | 0 | 1 (landmark-unique) | 0 |
| usage | 4 | 200 | 0 | 0 | 1 (landmark-unique) | 0 |
| upload | 4 | 200 | 0 | 0 | 1 (landmark-unique) | 0 |

- **Serious/critical in total:** 8 instances of one rule, `meta-refresh` (critical): board and results × 1440/390 × zh/en.
- **Page width:** no page overflows horizontally at 390 or 1440 (`scrollWidth == clientWidth` everywhere).
- **Login page:** `/login` at 390 zh is clean under axe.
- **Script exit code:** with no output piped, the script exits 1 here because of the 8 critical violations.

The seeded run has no reachable agent (`agent-t` is offline). This is the state that brings out F2 and F6 below.

---

## Findings

### F1 (P2 risk): critical axe `meta-refresh` on board and results, all widths and languages

- **Where:** board 1440/390 zh/en and results 1440/390 zh/en. Selector `meta[http-equiv="refresh"]`, for example `<meta http-equiv="refresh" content="15;url=/?run=ui-demo-run&stage=results&tab=outputs&lang=en">`.
- **Rule broken:**
  - WCAG 2.2.1 Timing Adjustable (level A). axe reports "`<meta>` tag forces timed refresh of page (less than 20 hours)".
  - DESIGN.md:93 *requires* the "15-second refresh", so this is a conflict between DESIGN.md and accessibility, not a deviation from DESIGN.md.
- **Evidence:**
  - `platform/abf_platform/web_board.py:24`: `REFRESH_SECONDS = 15`.
  - `web_board.py:822-825` writes the meta tag whenever `refresh=True`. `_frame` (`web_board.py:846-851`) only forwards the caller's flag; `render_board` sets `refresh=not flash` (`web_board.py:872`), so every board page without a flash refreshes, including the empty page of a person with no analysis. (Corrected by critic; see below.)
  - `web_board.py:864-868`: a *succeeded* run on the Outputs tab still refreshes every 15 s. This happens even after the listing has failed ("Could not read", see F2), when nothing on the page can change by itself.
- **Side effects:**
  - Each reload resets scroll position and focus, which matters to keyboard and screen-reader users.
  - Once the right column's input "問這個分析…" (DESIGN.md:37) is enabled, a reload will throw away half-typed text.
- **Reproduction:** `ui_check.py --start` as above. Any page of a selected run shows it.
- **Proposed fix (keeps DESIGN.md:93 for live runs):** emit the refresh only while something can change, meaning run status `running` or an outputs listing in state `loading`. A terminal run (succeeded/failed) with a settled listing would get no meta refresh. Removing the refresh entirely, or replacing it with JS polling (DESIGN.md:93 allows JS only where marked), is the maintainer's call.
- **Proposed RED test:** `test_web_board_no_meta_refresh_for_settled_terminal_run`.
- **HOT:** yes (`web_board.py`; the rule itself is in `DESIGN.md`).
- **Suggested tier:** the conditional refresh is B (local lane). Changing the DESIGN.md:93 constraint is A (maintainer).

### F2 (P2 risk): agent-offline reason shown as mixed-language raw text (zh) or a generic line (en): results Outputs and Settings

- **Where:**
  - results (and board) 1440/390. Selector `main.main p.ostat.state-failed + dl` ("原因 / Reason") in the Outputs tab.
    - zh shows `原因 agent agent-t is offline (代理離線); nothing was queued。`
    - en shows `Reason That cannot be done right now.`
  - settings 1440/390, "使用前檢查 / Before you start", item 3.
    - zh shows `主要運算環境無法使用：沒有代理在線，尚未預檢 (no agent online, not checked yet): agent agent-t is offline (代理離線); nothing was queued`
    - en shows `The primary compute environment is unavailable: That cannot be done right now`, with a capital T in mid-sentence and no full stop.
- **Rules broken:**
  - DESIGN.md:84: every Chinese sentence in formal written Chinese, with an equivalent formal English sentence.
  - DESIGN.md:93: the language is chosen by `?lang` and every screen exists in English. Here the zh page shows English, and the en page loses the actual cause.
  - DESIGN.md:52: "No chatty sentences". "That cannot be done right now." says nothing about what is wrong.
- **Evidence:**
  - `web_board.py:933-948`: `plain_reason` expects `中文 (English)` with the English half in a final parenthesis (`LATIN_PAREN = r"\(([^()]*)\)\s*$"`, `web_board.py:929`).
  - `platform/abf_platform/jobs.py:147` raises `"agent %s is offline (代理離線); nothing was queued"`: English first, Chinese in a parenthesis that is *not* at the end.
    - zh page: no final parenthesis, so the whole English text is kept and `。` is appended.
    - en page: the body contains CJK, so `r_generic` replaces it (`web_board.py:131`).
  - Settings path: `web_settings.py:149` builds `ce_down + _message(...)`, and `_message` (`web_settings.py:125-127`) runs `plain_reason` and then strips the closing full stop, which is why the en line ends without one. (Added by critic.)
  - `compute_envs.py:860` builds `"沒有代理在線，尚未預檢 (no agent online, not checked yet): %s" % e`. The raw `e` follows the parenthesis, so the same failure happens.
  - The page already has the right words: `f_e_agent_offline` at `web_board.py:84` (zh) and `web_board.py:147` (en). `jobs.py:477` already classifies this case as code `agent_offline`. The Outputs view at `web_board.py:686` still renders the raw message through `plain_reason`.
- **Reproduction:** `--start` seeds a CE whose agent `agent-t` never connects. Open the results stage, or `/settings`, in either language.
- **Proposed fix:**
  - The Outputs view and the settings preflight line pick their text by code (`agent_offline` → `f_e_agent_offline`) instead of parsing the message.
  - Make `jobs.py:147` and `compute_envs.py:860` follow the `中文 (English)` convention, with the parenthesis last.
- **Proposed RED tests:**
  - `test_results_outputs_agent_offline_reason_is_single_language` (zh text has no Latin words except names; en text names the agent).
  - `test_settings_preflight_no_agent_reason_is_single_language`.
- **HOT:** yes (`jobs.py`, `web_board.py`). `compute_envs.py` is not HOT.
- **Suggested tier:** B.

### F3 (P2 risk): usage page card uses banned words 「這個」 and a bare "run" in Chinese; the English starts in lower case

- **Where:** usage 1440/390 zh, card "國網 SU（本月）". Selector `main.main .scard` (first card). It reads `這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區`. The en card reads `the run record does not keep each task's cpus, realtime and partition` (no capital, no full stop).
- **Rule broken:** DESIGN.md:88 bans 「這個」 and 「單獨出現的 run」, and requires the sweep of every page (DESIGN.md:90). DESIGN.md:86 rule (2) says to name the thing ("該次分析") instead of pointing at it.
- **Evidence:**
  - `platform/abf_platform/su.py:29-30` (`NOT_STORED`).
  - `test_web_wording_sweep.py` visits `/usage` (`platform/tests/test_web_wording_sweep.py:477-491`). It evidently never reaches this card, which appears only when a run has no per-task trace fields. The seeded `ui-demo-run` has none.
- **Reproduction:** `ui_check.py --start`, then `/usage`.
- **Proposed fix:** rewrite as written Chinese, for example 「該次分析的紀錄未保存各步驟的 cpus、realtime 與分區，無法計算 SU。」, with a matching formal English sentence starting with a capital letter. Field names can stay in `<code>`.
- **Proposed RED test:** `test_su_not_stored_message_passes_wording_rules`. Put it in a new non-HOT file, for example `platform/tests/test_su_wording.py`, importing `BANNED` from the sweep.
- **HOT:** no (`su.py`). The sweep test itself is HOT, so do not edit it.
- **Suggested tier:** B.

### F4 (P2 risk): Launch with no available compute environment: step 1 is "current" with no control to continue, and the reasons are hidden in collapsed "Later" steps

- **Where:** launch 1440/390 zh/en.
  - `details.gstep[data-step="1"][data-state="current"]` holds only `input[name=run_name]`. There is no button. Pressing Enter does nothing, because the form has more than one text field and no submit button. The URL stays `/launch`.
  - The blocking messages ("No compute environment is available. Set one up on the settings page first." and "No samplesheet has been uploaded…") sit inside `details.gstep[data-step="2"]` and `[data-step="4"]`. These are closed and labelled only "○ Later" / 「○ 之後」.
  - In the screenshots a newcomer sees six steps and an empty name box, with no sign that nothing can be sent.
- **Rule broken:**
  - DESIGN.md:60: "nothing that is not set up is offered, so there is no pre-check step".
  - DESIGN.md:62 and :64: with no environment or no samplesheet, show the sentence and a link to `/settings` or `/upload`. Both are rendered, but not visibly.
  - DESIGN.md word 1 (line 7): 「系統直接一個個引導使用者」, the system guides the person step by step.
- **Evidence:**
  - `web_board.py:1093-1098`: steps without data become `later` and the first waiting step becomes `current`. A step whose only content is a ✗ blocker is never marked `bad`, so `min(bad)` does not select it.
  - `web_board.py:1100-1106` opens only the `current` step.
  - Also, `input[name=pipeline]` in the closed step 3 is `required`. A submit would fail silently with Chrome's "invalid form control is not focusable".
- **Reproduction:** `--start` (CE `lab-a`, agent offline, so not `available`), then `/launch?lang=en`. Type a name and press Enter: nothing happens.
- **Proposed fix:** treat "no available CE" and "no samplesheet" as `bad` for steps 2 and 4, so the first blocker becomes the open, current step. Alternatively render those blocks with `keep_open=True` and the ✗ mark in the summary.
- **Proposed RED test:** `test_launch_no_available_ce_opens_step_2_with_settings_link`.
- **HOT:** yes (`web_board.py`, `web_launch.py`).
- **Suggested tier:** B.

### F5 (P3 cleanup): stage bar breaks a word and crowds the current stage at 390 (en)

- **Where:** board/results 390 en. Selector `ol.steps li a` ("Downstream"). The label wraps as `Downstre` / `am`. The current stage's 2 px focus outline (`ol.steps a[aria-current]`) touches the "Running" label, so they read as "Running Results". zh at 390 is fine.
- **Rule broken:** DESIGN.md:36 (five-stage bar, readable labels) and DESIGN.md:38 (≤900px single column, which must still work at phone width). DESIGN.md:93 says every screen exists in English.
- **Evidence:**
  - `web_board.py:208`: `.main{…overflow-wrap:anywhere}` is inherited by `.steps a`.
  - `web_board.py:212`: `.steps li{flex:1;min-width:0}` gives five equal cells of about 62 px (342 px content width minus four 8-px gaps; 70 px pitch). (Corrected by critic.)
  - `web_board.py:219`: `outline-offset:2px` pushes the outline into the 8 px gap.
- **Reproduction:** screenshot `results-390-en.png`, crop y=140..210.
- **Proposed fix:**
  - `.steps a{overflow-wrap:normal;hyphens:auto}`.
  - At ≤600px, either smaller labels (12px, DESIGN.md:42 allows 12) or `flex-wrap:wrap` on `.steps`.
  - `outline-offset:0` on the current stage.
- **Proposed RED test:** `test_web_style_steps_labels_not_wrapped_anywhere`, a string check on `STYLE`. The visual check stays with ui_check.
- **HOT:** yes (`web_board.py`).
- **Suggested tier:** B.

### F6 (P3 cleanup): usage table breaks words mid-word at 390

- **Where:** usage 390 en, `main.main table.tbl`. Header `Analysi` / `s`; name `ui-` / `demo-` / `run`; status `≈ Estimat` / `e · bill pending`. zh 390 wraps more gently but is just as cramped.
- **Rule broken:** DESIGN.md:38 (≤900px single column) and DESIGN.md:78 (per-analysis table on the Cost page).
- **Evidence:**
  - `web_board.py:251-252`: `.tbl{table-layout:fixed}` with `th,td{overflow-wrap:anywhere}`.
  - `web_cost.py:137` uses plain `tbl`.
  - The compute-environment table already has a card layout at ≤640px (`web_board.py:275`, visible on `settings-390-*`). The cost table does not.
- **Reproduction:** screenshot `usage-390-en.png`.
- **Proposed fix:** reuse the `.tbl.ce` stacked-card pattern at ≤640px for the cost table, adding a `cost` class.
- **Proposed RED test:** `test_cost_table_has_narrow_layout_class`.
- **HOT:** yes (`web_board.py`, `web_cost.py`).
- **Suggested tier:** B.

### F7 (P3 cleanup): stray column borders in the one-column layout (≤900px)

- **Where:** every page at 390.
  - `aside.rail` keeps `border-left`: a 1-px line at x=0 beside "本分析的對話 / This analysis".
  - `aside.side` keeps `border-right`: a 1-px line at x=389 along the whole left column.
  - Nothing separates the stacked middle, right and left sections except a background change.
  - Pixel check on `upload-390-zh.png`: (0,300) = #d6d3cc and (389,500) = #d6d3cc, the `--line` token.
- **Rule broken:** DESIGN.md:38 (≤900px one column, order middle → right → left). The borders belong to the three-column layout.
- **Evidence:** `web_board.py:194` (`.side{border-right…}`), `web_board.py:232` (`.rail{border-left…}`), and `web_board.py:279` (media query without border reset).
- **Proposed fix:** in the ≤900px block, `.side,.rail{border-left:0;border-right:0;border-top:1px solid var(--line)}`.
- **Proposed RED test:** `test_web_style_narrow_layout_resets_column_borders`.
- **HOT:** yes.
- **Suggested tier:** B.

### F8 (P3 cleanup): masthead cost line disappears at ≤900px and is shown in US$ while DESIGN.md says NT$

- **Where:** masthead `header .costs` on every page.
  - Present at 1440 (`SU — 雲端 US$ —` / `SU — Cloud US$ —`).
  - Hidden at 390.
- **Rule broken:**
  - DESIGN.md:34: the masthead right side holds the "cost line (NCHC SU, cloud NT$ used / cap; links to the cost page)", with no narrow-width exception at DESIGN.md:38.
  - The currency differs from DESIGN.md:34, but the usage page says cloud costs are "never converted to New Taiwan dollars", consistent with DESIGN.md:78. DESIGN.md:97 marks the cost line as not re-confirmed.
- **Evidence:** `web_board.py:279` (`.costs{display:none}` at ≤900px) and `web_board.py:408`.
- **Proposed fix:** a maintainer decision (keep it hidden on phones, or show a compact `SU · US$`), and a correction to DESIGN.md:34 for the currency.
- **Proposed RED test:** none until decided.
- **HOT:** yes (`web_board.py`, `DESIGN.md`).
- **Suggested tier:** A (design question).

### F9 (P3 cleanup): English wording drifts from the Chinese and from DESIGN.md

These are seen on screenshots of all pages, en, both widths.

| Selector | English text | Chinese text / DESIGN.md says | Source |
|---|---|---|---|
| `aside.side h2` | "My runs" | 「我的分析」; DESIGN.md:35 calls them analyses | `web_board.py:91` |
| `aside.rail` header | "This analysis" | 「本分析的對話」 (`web_board.py:42`); DESIGN.md:37 requires the conversation header | `web_board.py:97` |
| upload `main.main p` | "There is no cloud compute environment you can use." | DESIGN.md:86 rule (1): state the state, not what the person can or cannot do; zh 「尚無可用的雲端運算環境。」 is right | `web_upload.py:67` |
| launch `main.main > p.muted` | "Pressing **Submit** … only the **Send** button there …" | DESIGN.md:86 rule (3), one verb for one act; zh uses 送出 twice | `web_board.py:986` |

- **Proposed fix:**
  - "My analyses".
  - "This analysis: conversation".
  - "No cloud compute environment is available."
  - "Submit" in both places.
- **Proposed RED test:** `test_en_strings_match_design_terms` (non-HOT file).
- **HOT:** yes.
- **Suggested tier:** B.

### Moderate (not serious or critical, listed for completeness)

`landmark-unique` on every page. The selectors are `aside.side` and `aside.rail`, two complementary landmarks without labels. On board and results there is also `nav.views` (`web_board.py:798`). Sources are `web_board.py:459` and `web_board.py:798`.
- **Fix:** give each its own `aria-label`.
- **HOT:** yes.
- **Severity:** P3.

---

## Refuted

- **"Links with empty text on /launch at 390" (probe output):** these are the links inside closed `<details>` blocks ("Go to the settings page", the pipeline tabs, "Go to upload data"). `innerText` is empty only because they are collapsed. They have text, and axe `link-name` did not fire. The real issue is that they are hidden; that is F4.
- **"board and results screenshots are identical":** this is by design. `/` opens the most recent analysis (DESIGN.md:35), and the only seeded analysis is a succeeded run, which opens at its results stage.
- **Small touch targets (中/EN 29×20 and 35×20 px; "Read again" 16 px tall):** under 24 px, but axe's `target-size` check did not report them, probably because of the spacing exemption. This is not a demonstrated WCAG 2.5.8 failure, so it is not reported as a finding.
- **Horizontal overflow at 390:** none on any page (`scrollWidth == 390`). The breaks above are wrapping problems, not overflow.
- **zh refresh URL lacks `lang=zh`:** zh is the default language (`pick_lang`), so the refresh stays in Chinese.

## Not done

- **Chromium:** Playwright's own Chromium could not be downloaded. The run used Chrome for Testing 153 at `$CHROME_PATH`, and the one-line launch patch lives only in `/tmp/cb/ui2/ui_check_scratch.py`.
- **Untested states:** running and failed run states, Downstream/Finished, confirmation pages and dark mode. The `--start` seed has only one succeeded run, and the script takes light-scheme screenshots only.

---

## Corrections by critic

Checked against origin/v3 `62c91293de611d265d8fbf3d0a128bea849be98c` in a read-only worktree, plus the PNGs and summary.md in `/tmp/cb/ui2/out/`.

**Verified (22 claims):**
- `scripts/dev/ui_check.py:123` is `browser = p.chromium.launch()`. Exit code 1 for any serious or critical violation is documented at `ui_check.py:18`.
- `ui_check.py:31-33`: `upload` is not in `DEFAULT_PAGES`, so passing `--pages ...,upload` was needed.
- summary.md has 24 rows, all HTTP 200, and exactly 8 critical `meta-refresh` entries (board and results × 2 widths × 2 languages). There are no serious entries.
- `web_board.py:24` (`REFRESH_SECONDS = 15`), `:822-825` (meta tag) and `:864-868` (the succeeded/outputs refresh URL) are as cited.
- `web_board.py:929` (`LATIN_PAREN`) and `:933-948` (`plain_reason`): traced by hand. zh keeps the whole English text and appends `。`. en drops a body that has CJK and falls back to `r_generic` (`:131`).
- `jobs.py:147` (the offline message), `jobs.py:477` (the `agent_offline` code), `compute_envs.py:860` and `web_board.py:84/147` (`f_e_agent_offline`) are as cited.
- `su.py:29-30` (`NOT_STORED` with 這個 and run). `DESIGN.md:88` bans 「這個」 and 「單獨出現的 run」.
- `test_web_wording_sweep.py:477-491` visits `/usage` with seeds that have per-task fields.
- CSS lines in `web_board.py` are as cited: `:194` `.side` border-right, `:208` `overflow-wrap:anywhere`, `:212` `.steps li`, `:219` `outline-offset:2px`, `:232` `.rail` border-left, `:251-252` `.tbl`, `:275` `.tbl.ce` card layout at ≤640px, and `:279` (≤900px block with no border reset, and `.costs{display:none}`).
- `web_cost.py:137` uses a plain `tbl`. `web_upload.py:67` and `web_board.py:986/955` (the en and zh intro text) are as cited. `web_board.py:91` is "My runs" and `:97` is "This analysis".
- `web_board.py:1093-1098` (step states) and `:1135` (`input name="pipeline" … required`). Step 6 has a submit button only when `envs` is non-empty (`:1177`), and `envs` holds only *available* environments (docstring `:1069-1070`).
- F7 pixel check: (0,300) and (389,500) on `upload-390-zh.png` are both rgb(214,211,204) = #d6d3cc.
- Screenshots: `results-390-en.png` shows "Downstre/am", the outline touching "Running", and the 1-px column lines. `usage-390-zh.png` shows the 這個 run card and the cramped table. `launch-390-en.png` shows step 1 current with no button and steps 2 to 6 "Later".

**Corrected:**
1. F1 said that `web_board.py:846-851` "passes it for every board frame". That is imprecise: `_frame` only forwards its `refresh` argument. The callers decide:
   - board: `refresh=not flash` (`:872`);
   - launch: only while loading (`:1198`, `web_launch.py:457`);
   - upload: only while moving (`web_upload.py:309`);
   - always: the file page (`:1235`) and `:1259`.

   The conclusion (every board and results page refreshes) still holds. The text has been fixed in place.
2. F5 said there were "five equal 70-px cells". At 390 the cells are about 62 px wide (70 px is the pitch including the gap). Fixed in place.
3. F2 evidence was incomplete for the settings line: the missing full stop comes from `web_settings.py:127` (`.rstrip("。.")`). Added in place.

No claim was struck outright.

## Added by critic

### F10 (P3 cleanup): Settings "Before you start" item 2 reads as two run-on fragments (en and zh)

- **Where:** settings 1440/390, selector `#setup ol li:nth-child(2)`. The en text is "Access token — **Check with the command** Create one in a terminal with abf-platform token new." The chip text names no command, and the note that follows has no separator.
- **Rule broken:** DESIGN.md:52 (no chatty or empty sentences) and DESIGN.md:86 rule (1) (say what the state is).
- **Evidence:** `web_settings.py:62` (`check_cmd` "Check with the command", `token_hint`) and `:24` (zh 「請以指令確認」). `web_settings.py:152` puts `check_cmd` as the chip text and `token_hint` as the note. `:157` joins them with a single space.
- **Reproduction:** `/settings?lang=en`, as in `settings-1440-en.png`.
- **Proposed fix:** a chip with a state ("Not checked" / 「未確認」) and a note that names the command once.
- **Proposed RED test:** `test_settings_token_step_names_state_and_command`.
- **HOT:** yes (`web_settings.py` matches `web*.py`).
- **Suggested tier:** B.

### F11 (P3 cleanup, design question): right column "This analysis / —" on pages that are not an analysis

- **Where:** launch, settings, usage and upload at both widths and in both languages, selector `aside.rail`. At 390 it sits between the main column and the left column as an empty block that holds only "—".
- **Evidence:** `web_board.py:815` (`_right(t, None)`), passed by `web_settings.py:348` and `web_board.py:1259`.
- **Rule:** DESIGN.md:37 defines the right column only as *this analysis's* conversation and says nothing for pages without one. This is not a clear break, so it is listed for the maintainer.
- **Proposed RED test:** none until decided.
- **HOT:** yes.
- **Suggested tier:** A (design question).

### Note: DESIGN.md contradicts itself on 這個

DESIGN.md:37 spells the right-column header 「這個分析的對話」, while DESIGN.md:88 bans 「這個」. The code correctly uses 「本分析的對話」 (`web_board.py:42`). DESIGN.md:37 should be aligned, which is A tier because DESIGN.md is the maintainer's.

### Coverage

The report covers the whole brief:
- every page × width × language;
- the one serious/critical rule, in all 8 instances;
- layout breaks with page, width, language, selector and DESIGN.md rule;
- the Chromium fallback;
- screenshots kept in the VM.

Dark mode and running or failed states were not exercised, as the report already says under "Not done".

