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
