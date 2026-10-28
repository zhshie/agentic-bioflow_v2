# guided-launch-2b progress ledger

Branch `feat/guided-launch-2` (the PR #240 branch, the correction round goes on the same branch).

## Done

- [x] One form, one button: steps 2, 4, 5, 6, 7 are fields of one `<form method="post" action="/launch">`; the four small forms are gone (`web_board.render_launch`).
- [x] Load or send with the same button: hidden `shown_pipeline`, `shown_revision`, `shown_params_from` (and `src`); a pair/earlier-analysis change is a 303 to `GET /launch` (no `p.*`, no `params`), a blank pipeline or revision is a 400 (rulings 9, 15; `web.launch_post`). GET shows "已載入 ... 的參數表，請檢查後再按送出。" and reads `run_name`.
- [x] Parameter boxes hold the default (or the earlier analysis's value); no radio, no `route` (ignored); advanced box in a closed `<details class="padv">`, open when it has text (ruling 14).
- [x] Only changed parameters are sent (`web_launch.changed_fields`), the step 7 summary lists the same ("全部使用預設值" when none).
- [x] Red `*` (`<span class="req" title="必填">*</span>`): pipeline, version, samplesheet, environment, analysis name, required parameters, required samplesheet columns; legend "* 必填"; samplesheet table has two columns.
- [x] Diagram size B / KB / MB (`web_launch.size_text`); description column 42 percent (`<colgroup>` classes `cname cdesc ctype cdef cval`, 20/42/9/12/17).
- [x] Written wording (ruling 1 table, below) and the guard test; `DESIGN.md` section "用字".
- [x] Docs: `docs/TESTING.md` "Guided launch, second cut", `docs/PLATFORM.md` "The guided launch page".

## Wording: old to new (ruling 1 table, used word for word)

The 28 rows of the ruling-1 table were applied as written. Strings the table does not list that contained a banned word or a spoken phrase, rewritten in the same tone:

| old | new |
|---|---|
| 站台已登記這個管線與版本。 | 站台已登記此管線與版本。 |
| 站台尚未登記這個管線與版本。 | 站台尚未登記此管線與版本。 |
| （這個環境不需登記） | （此環境不需登記） |
| 管線必填，只能寫 nf-core 的名稱，例如 ampliseq。 | 管線為必填，只能填寫 nf-core 的名稱，例如 ampliseq。 |
| 版本必填，而且要寫死（例如 2.18.0），不能留空。 | 版本為必填，請填寫確切版本號（例如 2.18.0），不可留空。 |
| run 名稱必填。 | 分析名稱為必填。 |
| 樣本表必須從你上傳的檔案裡選。 | 樣本表必須從已上傳的檔案中選擇。 |
| 運算環境必須是你自己的環境。 | 運算環境必須是您名下可用的環境。 |
| 參數「%s」看不懂；每行寫成「名稱: 值」。 | 參數「%s」無法辨識；每行須寫成「名稱: 值」。 |
| 參數 %s 不行：只能是文字、數字或 true/false。 | 參數 %s 不符規定：只能是文字、數字或 true/false。 |
| 參數 %s 寫了兩次。 | 參數 %s 重複出現。 |
| 沒有送出，請修正後再按一次。 | 尚未送出，請修正後再按一次。 |
| 填好之後按「下一步」，會先帶你到確認頁；在確認頁按「送出」才會真的排進佇列。（頁面最上方 launch_intro，後被 g_intro 取代） | 填寫完成後按「送出」，將先前往確認頁；於確認頁按「送出」才會排入佇列。 |
| 參數（選填，一行一個「名稱: 值」）（文字框標籤） | 其他參數（選填），放在「進階：直接輸入參數（一行一個「名稱: 值」）」區塊內 |
| 下一步，到確認頁（`l_submit`，已不顯示） | 送出（前往確認頁） |
| 預設值（不帶參數）（第 7 步摘要） | 全部使用預設值 |
| 沿用 %s / 預設值 / 自己調整（第 5 步摘要） | 沿用 %s（其餘兩個隨三條路線一起拿掉） |

English text is the equivalent formal sentence (no Chinese): "Previously used pipelines", "Other nf-core pipelines", "Re-run with the same settings", "Apply this version", "Submit (go to the confirmation page)", "All defaults", "The parameter table of %s version %s is loaded; check it, then press Submit.", and so on.

Not touched (out of scope, ruling 12, backlog item `web-wording-sweep`): the left column ("我的 run", "還沒有 run。"), the header, the other screens, `r_form`, `r_none`, `r_generic` (shared with other pages), and the sentences the action layer sends back (`actions/`).

## Existing assertions changed (ruling 3): old to new, reason

`test_web_guided_launch.py`
- gl01: `選好管線後檢查` / `選好管線與版本後顯示` to `選定管線後檢查` / `選定管線與版本後顯示`. Old string (ruling 1).
- gl02: `⚡` in the used row to `沿用設定重新分析`. The label changed (ruling 1).
- gl02b: the pair boxes sit in a `method="get"` form to they sit in the one post form; `搜尋全部 nf-core 之後開放` to `搜尋全部 nf-core（尚未開放）`. Four small forms gone, ruling 1.
- gl04: `這個環境不需登記` to `此環境不需登記`. Old string.
- gl06: `已用這個 run 的內容預填` to `已帶入該次分析的設定`. Old string.
- gl07: three radio inputs to no `name="route"` and the first option `不沿用`; `route=defaults&params_from=run-a` box empty to the same box as without `route` (ruling 4: `route` is ignored); `這個分析的參數不能沿用。` to `此分析的參數無法沿用。` (and English); step 7 hidden values `nf-core/ampliseq`, `samples.csv` to the step 2 box value and the selected option of step 4. The hidden fields of step 7 are gone with the one form.
- gl08: the post form is inside step 7 to it wraps the steps (checked on the whole page). Same reason.
- gl08b: `action="/launch"` inside step 7 html to on the page. Same reason.
- gl09: `value="nf-core/ampliseq"` in step 7 to in step 2. Same reason.
- gl10: `你還沒有上傳樣本表` to `尚未上傳樣本表`; `之後開放` to `尚未開放`. Old strings.
- gl11: English `Used before` / `New pipeline` / `Quick launch` and the three circled numbers to the new English tab and link names and no `route`. Old strings, no radios.
- gl12b: allowed field names: `route` removed, `shown_pipeline`, `shown_revision`, `shown_params_from` added. The interface of the one form.

`test_web_guided_launch_2.py`
- g01: `讀取中頁面會自動更新，請等讀完再填參數。` and `選好版本後檢查` to the ruling-1 sentences.
- g02: `之後開放` after the nf-core search, `使用這一版`, `目前連不到 GitHub，這是 %s 查到的。` to the ruling-1 sentences.
- g03: `753702` to `736 KB` (ruling 1, KB); `這條管線沒有提供流程圖。` and `選好管線與版本後顯示` to the new sentences.
- g05: samplesheet table with three columns and `✓` / `—` to two columns and a red star after the required name (the 「必填」 column); `預覽與欄位角色 之後開放` to `預覽與欄位角色（尚未開放）`.
- g06: three radios to none; `<form` before the groups to the reuse select before the groups (the form is outside the step now); `placeholder` default to `value` default; `進階（管線預設隱藏的參數）` to `進階參數（管線預設隱藏）`; the `必填` span to the red star span.
- g07: a filled `p.*` in the address is in its box and in the summary, not in the box `params` (the boxes no longer merge into the text on a GET); `route=defaults` / `route=custom` no longer change anything (ruling 4); the integer is checked in the summary.
- g08: `Use this version`, the English advanced title and `>Required<` to the new English sentences and `title="Required"`.
- g11: the first-cell regex of the samplesheet table accepts the star span.

Helper changes, not assertions: `form_values` (`test_web_actions.py`) and the direct post in `test_http_site_samplesheet.py` carry `shown_pipeline` and `shown_revision` equal to the pair, as the page they stand for would.

## Tool search record (ruling 13, copied word for word from the plan)

developer-agent 已搜過：搜過 sysprog21/zhtw-mcp（依教育部標準檢查台灣用詞與標點，例如「軟件」應作「軟體」）、huacnlee/AutoCorrect（中英文之間的空格與標點）、mileschou/traditional-chinese-lint（錯字對照表）。三者都不判斷口語或書面語氣，所以不採用；改用 DESIGN.md「用字」節的禁用詞表加自動測試（參考 Qwen Code check-i18n 的禁用子字串作法）。

## Things the plan did not decide (for the developer-agent)

- The launch form now returns every box of the table (about 170 fields for ampliseq). `web.body_of` allows 50 fields and 16 KB, which would have turned every send into an error. A new `launch_body` (limit 256 KB, 1000 fields) is used by `launch_post` only; it sits beside `launch_post`, but `web.py` was limited to the three functions, so this is a small step outside the plan. The other forms keep the old limits.
- Styles are in `web_board.STYLE` (there is no `static/` folder): five column-width rules added, `.padv` shares the `.pgroup` rules, `.req` is unchanged. No new colour. `.gsteps` still has `max-width:640px`, so the 42 percent description column is 42 percent of 640 px; widening the container is a design decision left to the maintainer's screenshots (TC-133).
- Overview question 1 (which tab after a load): the hidden field `src` carries the tab and the 303 brings it back, so the page stays on the tab the person was on. Question 2: on a refused send the boxes keep what was sent. Question 3: the "loaded" line shows on every GET that has a pipeline, a revision and a read parameter table (not only after a redirect).

`test_web_actions.py`
- tc026/tc028 (quick launch, content not kept): `沒有保留` to `未保存`. Old string (ruling 1: 該次分析的設定未保存，請自行填寫。).

`test_clean_page.py`: `BASE_CONFIRM`, `BASE_EXPIRED`, `BASE_POST`, `BASE_BOARD` and `BASE_STYLE` pinned again, as guided-launch-2 did. The one stylesheet changed (column-width rules and the advanced box added, the radio rows removed), so every page's hash changes; no page text changed.

`test_cleanup_offer.py`: the route list gets `/launch/diagram` (the route guided-launch-2 added; the test arrived with the merge of origin/v3 and had not been told).

## Fix round (verifier: TC-093)

- Added `test_h11_used_tab_empty_sentence` in `test_web_guided_launch_2b.py`: with no usage records the used tab shows 「尚無使用紀錄。」 (and not the old 「還沒有用過的管線。」); English shows "No usage history.". No product code changed; the behavior was already right.

## 2c (small fixes after the screenshots of c794c84; plan `guided-launch-2c`)

What changed
- Red star on the name line: new `web_launch.lbl(t, text)` writes `<span class="lbl">name <span class="req" title="必填">*</span></span>`; the pipeline, version, samplesheet, environment and analysis-name labels use it (`web_board.render_launch`). `.req` is now `font-size:inherit` (colour unchanged).
- The parameter table has four columns (name, description, type, value): the default column, the `cdef` col and the string `g2_th_default` (zh and en) are gone. Widths 22 / 50 / 10 / 18. The default only shows as the value of the box.
- Desktop width: `.gsteps` has no `max-width`; `.lform input,select,textarea` have `max-width:640px`. The mobile rules are untouched.
- Refused send (400): no product change was needed; `launch_post` already passes every `p.*` box back (`guide["cells"]`) and `launch_page` shows them, a cleared box stays empty, and the advanced box keeps its text. J05 pins this; J03 and J06 also passed before the change.
- Tests J01-J06 added in `test_web_guided_launch_2b.py` (J01, J02, J04 were red first, commit `RED:`).

Existing assertions changed (old to new, reason)
- `test_web_guided_launch_2b.py::test_h12_columns`: five columns `[:5]`, widths 20/42/9/12/17 to four columns `[:4]`, widths 22/50/10/18 (allowed: the five-column colgroup and the 42 percent column).
- `test_web_guided_launch_2b.py::test_h09_stars`: five regexes `<label>NAME STAR<input|select` to `<label><span class="lbl">NAME STAR</span><input|select`. Not on the plan's list of allowed assertions: the star moved into the new inline element (plan step 1), so the same five labels are checked, with the same star, in the new shape; nothing is weaker.
- `test_clean_page.py`: all page hashes and `BASE_STYLE` pinned a third time (only the stylesheet differs).

Green run record
- Focused: test_web_guided_launch*.py and test_web_actions.py green after the change; `test_clean_page.py` 28 passed after the repin.
- Full suite at 996a03c from WSL: `bash tests/run_all.sh --timeout 900`: 127/127 passed, all green (platform shards: 1285 + pytest tests, shard 2 alone ran 1121 passed in 361 s). With the default 300 s limit platform_shard_2_test.sh timed out on this machine (361 s alone, no failing test); with the limit raised it passes. Running pytest inside the worktree leaves `__pycache__` folders under `platform/`, and `jev_test.sh` TC-085 (grep -rli jev platform) then fails on a `.pyc`; they were cleared before the green run.

### 2c fix round (verifier FAIL on J04)

- `.lform{...}` itself still had `max-width:640px`, and `.gsteps` sits inside the form, so the step area stayed 640 px wide. Removed it from `.lform` (web_board.py); the single-line controls keep their own `max-width:640px`. The only other `max-width:640px` in the style sheet is `.narrow` (the login-type pages, not /launch); the only wrapper of the steps is the form, so nothing else caps the launch page.
- `test_j04_style` also asserts that `.lform{` has no max-width (red first: commit `RED: .lform must not cap the width`).
- `test_clean_page.py`: page hashes and `BASE_STYLE` pinned a fourth time (only the style sheet changed).
- Green run: see the last line of this ledger.
- Full suite at a6aa830 from WSL, __pycache__ cleared first: `bash tests/run_all.sh --timeout 900`: 127/127 passed, all green.

### 2c fix round 2 (phone widths, 390 px screenshot)

- Under `@media (max-width:600px)` the table stayed `display:table`, so the desktop column widths still shaped the stacked cells (about 69 px each). The block now also has `.ptbl,.ptbl tbody{display:block}` and `.ptbl td{width:auto}`; the desktop percentages stay outside it. Placed after `.ptbl thead{display:none}` so the string the older test `test_h12_columns` looks for is unchanged.
- Samplesheet column table (step 4, `.scols`): it has no phone stacking rule (it stays an ordinary two-column table, no `display:block`, no widths of its own), so it does not have this problem; not changed.
- `test_j07_phone_cells_full_width` added (red first, commit `RED: phone cells must span the row`).
- `test_clean_page.py`: hashes and `BASE_STYLE` pinned a fifth time (only the style sheet changed).
- Full suite at 55a618e from WSL, __pycache__ cleared first: `bash tests/run_all.sh --timeout 900`: 127/127 passed, all green.

## 2d (guided-launch-2d: six steps, only set-up environments, one version drop-down, the diagram under the pipeline, no pre-check step; plan `specs/guided-launch-2d/plan.md`, contract `specs/guided-launch-2d/test-case.md`)

What changed
- Order: 1 analysis name, 2 compute environment, 3 pipeline (with version and diagram), 4 samplesheet, 5 parameters, 6 confirm. The pre-check step is gone; `launch_checks` and `step1_note` are deleted. The parameter-table read (`✓ ... N groups, M parameters` / `…` / `✗` / `○`) is now the first line of step 5 (`web_launch.params_status`).
- Environments: `launch_choices` (web.py) keeps only `status == "available"`; the page and `POST /launch` both use that list. None available: step 2 says 「尚無可用的運算環境，請先至設定頁完成設定。」 with a link to `/settings`, no send button, POST is 400 (`e_ce`).
- Registration: `web_board.is_unregistered(env, pipeline, revision)`; a non-empty `sitePipelines` list that lacks the pair gives the sentence (ruling 4) with a link to `/settings` under the pipeline, and `POST` is 400 (`e_reg`, step 3). Missing, empty or odd lists: no check.
- Samplesheet: none uploaded gives 「尚無已上傳的樣本表，請先上傳。」 and a link; the button stays; POST stays 400 (`e_sheet`).
- Version in one place: on the "Other nf-core pipelines" tab only the pipeline box is typed; with a pipeline in the address the page asks `latest_release` (also when a version is given) and shows a `<select name="revision">`, newest first, the newest selected (the page reads the files at that version); a version from the address that is not in the list stays, selected. Loading: 「正在讀取版本清單…」 plus the 15 s refresh; error with no version: a ✗ line, no drop-down, POST 400 (`e_revision`). The "Used before" rows carry the version only as a hidden field. The "套用此版本" link and the "最新版本" line are gone.
- `POST /launch`: a pipeline that differs from `shown_pipeline` on the new tab with a blank version is a 303 reload (ruling 5), the redirect drops the old version so the new pipeline starts at its newest; same pipeline with a blank version is still 400 `e_revision`. Error steps renumbered (name 1, environment 2, pipeline/version/registration 3, samplesheet 4, parameters 5, refusal by `request_launch` 6).
- Diagram: `<img class="gdia" src="/launch/diagram?..." alt="...">` under the pipeline (CSS `.gdia{display:block;max-width:100%;height:auto}`, replaces `.dlink`); step 3 is `open` whenever the picture is shown (ruling 6). Reading: 「正在讀取流程圖…」; none: 「此管線未提供流程圖。」. The link, the file-name/size line, `g2_dia_file`, `g2_dia_open`, `g2_dia_wait`, `g2_latest`, `g2_use_ver`, `g_ver_hint` and `web_launch.size_text` (now unused) are deleted.
- CSP: `LAUNCH_HEADERS` in web.py = the base policy with `img-src 'self'` inserted after `default-src 'none';`, used only by `launch_page` (GET /launch and the 400 answer of POST). Nothing else changed.
- `actions.latest_release` (only inside `# ---- release-lookup-job`) returns `releases` (every usable tag, newest first; `revision` is the first; `[]` while loading or on error); `releases.lookup` keeps the list in the cache entry and reads an older entry as `[revision]`. New `releases.usable_sorted`.
- Docs: DESIGN.md (launch stage list, six steps), docs/PLATFORM.md (guided launch section, `latest_release`, `img-src`), docs/TESTING.md (Guided launch manual steps rewritten for six steps).
- Tests: new `platform/tests/test_web_guided_launch_2d.py` (88 tests, comments name the TC numbers; RED commit `dc0ceff`).

Upload link (TC-020, ruling 3)
- The page has no upload address of its own (the side column's 「上傳資料」 is grey text), so the sentence of step 4 links to the board: `/` (`/?lang=en` in English). If an upload page appears later, only `render_launch` (the `g_go_board` link) changes.

Existing assertions changed (old to new, reason; all of the kinds the plan allows)
- `test_web_guided_launch.py::ready`: now also sets `lab-a` to `available` for `ann` (the rig starts it as `invalid`; only available environments are offered). Harness, no assertion changed.
- `test_gl01_seven_numbered_steps` (renamed `test_gl01_six_numbered_steps`): steps `[1..7]` to `[1..6]`, titles 7 to 6, current step `[2]` to `[1]`, the hints 「選定管線後檢查」 and 「選定管線與版本後顯示」 removed (seven-step numbering).
- `test_gl01b_one_current_step_and_symbols`: checked states `(2 done, 4 current, 5 later)` to `(3 done, 1 current, 4 later)` (numbering and the name first).
- `test_gl02b_no_used_pipeline_opens_the_new_tab`: step 2 to 3; the required `revision` text box to "no revision control until a pipeline is typed" (version text box gone).
- `test_gl03_select_marks_step2_done_and_runs_prechecks` (renamed `..._step3_done`): step 2 to 3, current `[4]` to `[1]`, the five pre-check rows removed and replaced by "no pre-check wording" plus the read line in step 5 (pre-check rows).
- `test_gl04_registered_check`: the `✓/✗/—` row 「管線已登記」 to the S2 sentence under the pipeline, absent when the pair is listed or the environment lists nothing (pre-check row).
- `test_gl05_site_connection_check`: rows 「站台連線」「版本已指定」「有可用樣本表」 to: an available environment is offered, an invalid one is not (S1 shown), the samplesheet sentence S3 (pre-check rows; 「版本已指定」 removed by the maintainer).
- `test_gl06_quick_launch_prefills_and_goes_to_first_open_step`: states `(1,2,5,6)` to `(2,3,5)`, current `[4]` to `[1]` (three places), summary step 7 to 6.
- `test_gl07_param_routes`: pair in step 2 to step 3 (numbering).
- `test_gl08_post_unchanged`: summary step 7 to 6, name box in step 1 instead of 7 (numbering).
- `test_gl08b_a_failed_check_does_not_stop_the_page_only_the_action_decides` (renamed `..._an_unregistered_pair_is_refused_by_the_page`): old: the page lists the failed check in step 7 and the action decides; new: the page refuses an unregistered pair itself, 400 at step 3 (plan 作法 2: 「POST 回 400」).
- `test_gl09_post_error_rerenders_at_the_failing_step`: current `[7]` to `[1]` for the missing name; the sheet/params case now gives a name (else step 1 wins) and a case with the name missing too was added; summary step 7 to 6, pair step 2 to 3.
- `test_gl10_no_samplesheet_notice`: two old sentences to S3; environment in step 2 instead of 6; `lab-a` set available first.
- `test_gl11_english`: seven English titles to six.
- `test_web_guided_launch_2.py`: `row()` reads the line in step 5 (was `<li class="chk` of step 1); `test_g01_*` (refresh note, error rows, no revision) step 1 to 5, the 「前置檢查未通過」 clause of step 7 removed; `test_g02_latest_called_once_for_the_caller` (the version is now read, so `fk.pf == []` is dropped and the version select is checked), `test_g02_latest_ready_and_link` (line and link to the selected drop-down item), `test_g02_stale_cache`, `test_g02_latest_loading_and_error` (step 2 to 3; 「… 讀取中」 to 「… 正在讀取版本清單…」), `test_g02_not_for_the_used_tab_or_with_a_revision` (the list is asked also with a version on the new tab; never on the used tab); `test_g03_link_with_name_and_size` (link and file/size line to the picture), `test_g03_none_loading_failed` (later to done, the reading sentence), `test_g03_image_loading_and_failed` (「圖檔讀取中」 to S5), `test_g03_not_chosen` (hint gone, nothing shown), `test_g03_calls` (`fk.lr == []` to one call); `test_g07_get_merges`, `test_g07_typed_from_the_schema` (summary step 7 to 6); `test_g08_english_every_state` (2 asserts: version line/link to select, link to picture); `test_g09_limits` (the /launch CSP now has `img-src 'self'`, exact string); `test_g10_one_get_shows_everything` (lr 0 to 1, read line in step 5, picture instead of link).
- `test_web_guided_launch_2b.py`: `test_h01_one_submit_button` (version text box to select), `test_h01_kept_links` (step 2 to 3, no 套用此版本 link, picture), `test_h01_no_sheet_no_env_keep_the_button` (env set available; with no environment there is no button, the old test expected the button to stay: TC-013), `test_h08_prefill_cells_and_unknown`, `test_h06_all_defaults_send_no_params` (step 7 to 6), `test_h09_stars` (version label on a select, no hint line, environment step 2, name step 1), `test_h10_size` (6 cases: the file name/size line is gone, so no size is written) and `test_h10_english` (alt text instead of 「(736 KB)」), `test_h11_old_strings_are_gone` (six-step intro, hints removed, S1/S3 sentences, old strings list extended), `test_h11_no_banned_word_without_env` (S1 full sentence), `test_scope_page_limits` (the only image is the diagram, our own address; read line in step 5, pipeline in step 3). Import of `set_env` added.
- `test_web_actions.py::test_tc020_the_form_has_the_fields`: `lab-a` set available; six steps (was seven); revision is a select (was a required text box; the address carries pipeline and version).
- `test_releases.py`: `KEYS` gets `releases`; the three cache-entry equalities get `releases` (list in the entry). `test_pipeline_files_action.py`: `LR_KEYS` gets `releases`; the cache-entry equality of TC-140 gets `releases`.
- `test_clean_page.py`: page hashes and `BASE_STYLE` pinned a sixth time (only the style sheet changed: `.dlink` to `.gdia`).
- Not changed: `test_cleanup_offer.py` route list (`/launch/diagram` was added in guided-launch-2).
- Known flake, not from this change: `test_web_guided_launch_2b.py::test_j02_four_columns` asserts `"cdef" not in page`, and a random CSRF token can contain those four letters (it failed once in one of my runs and passed on the next).
