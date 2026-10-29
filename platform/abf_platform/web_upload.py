# Nothing existing: the two pages of the web upload (the form GET /upload and the progress of one batch GET /upload/{batch}); the frame, the escaping and the one stylesheet are web_board's, the words are ours.
"""The upload pages (web-upload-page), as pure functions from dicts to strings.

No database, file or network is touched here: `web.py` reads through the actions with the logged-in caller and hands the answers in. The pages have no
script, no `style=` attribute and no external address; they use only the classes of web_board's one stylesheet (DESIGN.md tokens). Every state of a
file is a symbol, a word and a class together, never a colour alone. Words come from the one table STRINGS (zh and en, same keys). A command for a file
over the limit is the text cloud_store gives; the platform never runs it.
"""
from . import cloud_store, compute_envs, web_board
from .web_board import esc

STRINGS = {
    "zh": {
        "title": "上傳資料",
        "intro": "選擇運算環境，填資料集名稱與版本，再選 FASTQ 檔。按「上傳」後，檔案會送進你自己的雲端資料夾；全部送完會自動登記成資料集，"
                 "之後在送出分析頁的第 4 步就能選。",
        "limit": "每檔上限 2 GB；更大的檔請改用指令上傳（見表單下方）。",
        "l_ce": "運算環境", "l_name": "資料集名稱", "l_version": "版本", "l_fastq": "FASTQ 檔", "l_sheet": "樣本表（選填）",
        "h_name": "英數字與 . _ -，最長 64 個字元。",
        "h_sheet": "沒有選樣本表時，會依檔名把 R1／R2 配成對，自動產生。",
        "go": "上傳",
        "none": "沒有可用的運算環境。請先到設定頁建立並檢查運算環境。", "go_settings": "前往設定頁",
        "sh_title": "樣本表", "sh_label": "上傳樣本表（CSV 或 TSV）",
        "sh_hint": "每列一個樣本。檔案內的路徑寫站台上的位置，平台不會檢查。僅收 .csv 或 .tsv，一次一個檔，上限 1 MB。",
        "sh_go": "上傳樣本表", "sh_saved": "✓ 已上傳樣本表 sheets/%s，可於「送出新分析」第 4 步選擇。", "sh_launch": "前往送出新分析",
        "su_big": "樣本表大於 1 MB，沒有收下。", "su_ext": "樣本表只收 .csv 或 .tsv 檔，沒有收下。",
        "su_utf8": "樣本表無法以 UTF-8 讀取，沒有收下。請存成 UTF-8 編碼後再上傳。",
        "su_ragged": "樣本表每一列的欄數必須相同，沒有收下。", "su_header": "樣本表至少要有一列標題加一列資料列，沒有收下。",
        "su_none": "請選擇一個樣本表檔。", "su_many": "一次只收一個樣本表檔，沒有收下任何檔案。",
        "cmds": "大檔指令", "cmds_note": "在你的電腦上執行；每個環境一行。",
        "e_required": "此欄為必填。", "e_invalid": "只能用英數字與 . _ -，長度 1 到 64。",
        "e_no_files": "請選擇至少一個 FASTQ 檔。",
        "e_env": "找不到可用的雲端運算環境，請重新選擇。",
        "e_registered": "此名稱與版本已登記，請換一個版本。",
        "e_bad_name": "這些檔名不能使用：%s。檔名不可含 / \\ 或 ..，不可含控制字元，也不可以 . 開頭。",
        "e_dup": "同一批裡有重複的檔名：%s。",
        "e_empty": "這些檔案是空的，沒有內容可以上傳：%s。",
        "e_too_big": "檔案 %s 大於每檔上限 2 GB，沒有收下，也沒有排入上傳。請改用下面的指令。",
        "e_in_use": "此檔名正在上傳或已使用，請改檔名。",
        "e_sheet_big": "樣本表太大，上限 1 MiB。沒有收下任何檔案。",
        "e_unpaired": "這些檔案配不成對（R1／R2）：請補齊另一半，或附上樣本表。",
        "e_sheet": "樣本表有問題：%s",
        "e_refused": "目前不能排入上傳：%s",
        "e_disk": "伺服器暫時無法收下檔案，沒有排入任何上傳。請稍後再試。",
        "e_request": "請求的格式不正確，沒有收下任何檔案。請回到上傳頁重新操作。",
        "e_many": "一次最多 100 個檔案，沒有收下任何檔案。",
        "e_nothing": "沒有收下任何檔案，也沒有排入任何上傳。",
        "p_title": "上傳進度", "p_of": "資料集 %s，版本 %s，環境 %s", "th_file": "檔名", "th_size": "大小", "th_state": "狀態",
        "s_queued": "排隊中", "s_sending": "傳送中", "s_done": "完成", "s_failed": "失敗",
        "p_timeout": "上傳逾時，沒有在時限內完成。", "p_no_reason": "上傳沒有成功。",
        "p_running": "正在上傳。本頁每 15 秒自動更新；全部傳完後會自動登記成資料集。",
        "p_failed": "有檔案沒有傳成功，資料集沒有登記。",
        "p_again": "重新上傳",
        "p_registered": "已登記資料集 %s（版本 %s）。", "p_go_launch": "已登記，前往送出",
        "p_reg_failed": "所有檔案都已傳完，但資料集登記失敗：%s", "p_keep": "檔案仍在你的雲端資料夾，可換一個版本重新上傳。", "p_places": "檔案在雲端的位置",
        "p_superseded": "這一批已被新的上傳取代。",
    },
    "en": {
        "title": "Upload data",
        "intro": "Choose a compute environment, name the dataset and its version, then choose the FASTQ files. After you press Upload the files go to your "
                 "own cloud folder; when all of them are there the dataset is registered, and you can choose it at step 4 of the launch page.",
        "limit": "Each file may be up to 2 GB; for larger files use the command below the form.",
        "l_ce": "Compute environment", "l_name": "Dataset name", "l_version": "Version", "l_fastq": "FASTQ files", "l_sheet": "Samplesheet (optional)",
        "h_name": "Letters, digits and . _ - ; up to 64 characters.",
        "h_sheet": "Without a samplesheet, the R1/R2 files are paired by name and one is made for you.",
        "go": "Upload",
        "none": "No compute environment is ready. Create and check one on the Settings page first.",
        "go_settings": "Go to the settings page",
        "sh_title": "Samplesheet", "sh_label": "Upload a samplesheet (CSV or TSV)",
        "sh_hint": "One row for each sample. The paths inside name files on the site, which the platform does not check. Only .csv or .tsv, one file at a time, up to 1 MB.",
        "sh_go": "Upload samplesheet", "sh_saved": "✓ Samplesheet sheets/%s uploaded. Choose it at step 4 of the launch page.",
        "sh_launch": "Go to the launch page",
        "su_big": "The samplesheet is larger than 1 MB. It was not taken.", "su_ext": "Only .csv or .tsv samplesheets are taken. It was not taken.",
        "su_utf8": "The samplesheet cannot be read as UTF-8. It was not taken. Save it as UTF-8 and upload it again.",
        "su_ragged": "Every row of the samplesheet must have the same number of columns. It was not taken.",
        "su_header": "The samplesheet needs a header row and at least one data row. It was not taken.",
        "su_none": "Choose one samplesheet file.", "su_many": "Only one samplesheet file at a time. No file was taken.",
        "cmds": "Commands for large files", "cmds_note": "Run on your computer; one line for each environment.",
        "e_required": "This field is required.", "e_invalid": "Use letters, digits and . _ - only, 1 to 64 characters.",
        "e_no_files": "Choose at least one FASTQ file.",
        "e_env": "That compute environment is not available. Choose another.",
        "e_registered": "This name and version are already registered. Use another version.",
        "e_bad_name": "These file names cannot be used: %s. A name may not contain / \\ or .., control characters, or begin with a dot.",
        "e_dup": "The same file name is in this upload more than once: %s.",
        "e_empty": "These files are empty, so there is nothing to upload: %s.",
        "e_too_big": "The file %s is larger than the 2 GB limit for one file. It was not taken and nothing was queued. Use the command below.",
        "e_in_use": "This file name is in use by another upload; rename the file.",
        "e_sheet_big": "The samplesheet is too large; the limit is 1 MiB. No file was taken.",
        "e_unpaired": "These files could not be paired (R1/R2): add the missing mate, or attach a samplesheet.",
        "e_sheet": "The samplesheet has a problem: %s",
        "e_refused": "The upload cannot be queued now: %s",
        "e_disk": "The server could not take the files just now. Nothing was queued. Try again later.",
        "e_request": "The request was not in the expected form. No file was taken. Go back to the upload page and try again.",
        "e_many": "At most 100 files at a time. No file was taken.",
        "e_nothing": "No file was taken and nothing was queued.",
        "p_title": "Upload progress", "p_of": "Dataset %s, version %s, environment %s", "th_file": "File", "th_size": "Size", "th_state": "Status",
        "s_queued": "Queued", "s_sending": "Sending", "s_done": "Done", "s_failed": "Failed",
        "p_timeout": "The upload timed out; it did not finish in time.", "p_no_reason": "The upload did not succeed.",
        "p_running": "Uploading. This page reloads every 15 seconds; when every file is there the dataset is registered automatically.",
        "p_failed": "A file did not upload, so the dataset was not registered.",
        "p_again": "Upload again",
        "p_registered": "Registered dataset %s (version %s).", "p_go_launch": "Registered, go to launch",
        "p_reg_failed": "Every file is uploaded, but registering the dataset failed: %s",
        "p_keep": "The files are still in your cloud folder. You can upload again under another version.", "p_places": "Where the files are in the cloud",
        "p_superseded": "A newer upload replaced this batch.",
    },
}
SYMBOL = {"queued": "○", "sending": "◐", "done": "✓", "failed": "✕"}
CLASS = {"queued": "chip state-unknown", "sending": "chip state-running", "done": "chip state-succeeded", "failed": "chip state-failed"}


def _words(lang):
    lang = web_board.pick_lang(lang)
    t = dict(web_board.STRINGS[lang])
    t.update(STRINGS[lang])
    return lang, t


def shown(text, cap=120):
    """A file name or a message as one line of plain printable text: a control character becomes ?."""
    text = "".join(c if c.isprintable() else "?" for c in str(text))
    return text[:cap] + ("…" if len(text) > cap else "")


def usable(envs):
    """The environments the person may send files to: set up, and of a type whose jobs include the upload (the table that the queue itself reads)."""
    return [e for e in envs if e.get("status") == compute_envs.AVAILABLE and "put_upload" in compute_envs.CLOUD_JOB_KINDS.get(e.get("platform"), ())]


def sheet_ready(envs):
    """Whether the person has a national-HPC (Slurm) environment that is set up and checked: only then the samplesheet form is drawn and taken."""
    return any(e.get("platform") == compute_envs.SUPPORTED and e.get("status") == compute_envs.AVAILABLE for e in envs)


def big_commands(envs, user_name):
    """[(environment name, one command line)] for each usable environment, the text cloud_store gives."""
    out = []
    for e in usable(envs):
        try:
            out.append((e["name"], cloud_store.big_file_command(e, user_name, cloud_store.workdir_scheme(e))))
        except cloud_store.CloudPathError:
            continue
    return out


def _commands_block(t, envs, user_name):
    lines = big_commands(envs, user_name)
    if not lines:
        return ""
    items = "".join("<li><span class=\"muted\">%s</span> <code>%s</code></li>" % (esc(n), esc(c)) for n, c in lines)
    return '<section class="card sec"><h2>%s</h2><p class="muted">%s</p><ul>%s</ul></section>' % (esc(t["cmds"]), esc(t["cmds_note"]), items)


def _size_text(n):
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        return "—"
    value, unit = float(n), "B"
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1000 or unit == "GB":
            break
        value /= 1000
    return ("%d B" % n) if unit == "B" else ("%.1f %s" % (value, unit))


def _bad(text):
    return '<p class="bad">✕ %s</p>' % esc(text)


def _names(names):
    return ", ".join(shown(n, 80) for n in names)


def problem_html(t, lang, problem):
    """The lines that say what was wrong with a form that was sent (the dict the action answered, or {error: 'too_big', name} from the receiver)."""
    kind = (problem or {}).get("error")
    if not kind:
        return ""
    if kind == "fields":
        return ""      # said beside the box
    if kind == "too_big":
        names = problem.get("names") or [problem.get("name")]
        return _bad(t["e_too_big"] % _names(names))
    if kind in ("bad_name", "dup_in_batch", "empty_file"):
        return _bad(t[{"bad_name": "e_bad_name", "dup_in_batch": "e_dup", "empty_file": "e_empty"}[kind]] % _names(problem.get("names") or []))
    if kind == "in_use":
        return _bad(t["e_in_use"]) + '<p class="muted">%s</p>' % esc(_names(problem.get("names") or []))
    if kind == "unpaired":
        rows = "".join("<li><code>%s</code> <span class=\"muted\">%s</span></li>" % (esc(shown(u.get("file"), 80)), esc(web_board.plain_reason(u.get("reason"), lang)))
                       for u in problem.get("unpaired") or [])
        return _bad(t["e_unpaired"]) + "<ul>%s</ul>" % rows
    if kind == "sheet":
        return _bad(t["e_sheet"] % web_board.plain_reason(problem.get("message"), lang))
    if kind == "refused":
        return _bad(t["e_refused"] % web_board.plain_reason(problem.get("message"), lang))
    key = {"no_files": "e_no_files", "env": "e_env", "already_registered": "e_registered", "sheet_too_big": "e_sheet_big", "disk": "e_disk",
           "too_many": "e_many", "request": "e_request", "bad_request": "e_request"}.get(kind)
    return _bad(t[key] if key else t["e_nothing"])


def is_sheet_problem(problem):
    return str((problem or {}).get("error") or "").startswith("sheetup_")


def _sheet_section(t, lang, token, problem):
    """The samplesheet form of a national-HPC environment: one file box, the refusal (if any) above the form."""
    star = '<span class="req" title="%s">*</span>' % esc(t["g2_req"])
    action = "/upload" + ("?lang=en" if lang == "en" else "")
    why = str((problem or {}).get("error") or "")[len("sheetup_"):] if is_sheet_problem(problem) else ""
    bad = _bad(t["su_" + why]) if ("su_" + why) in t else ""
    return ('<section class="card sec"><h2>%s</h2><p class="muted">%s</p>%s<form class="lform" method="post" action="%s" enctype="multipart/form-data">'
            '<input type="hidden" name="csrf" value="%s"><label><span class="lbl">%s %s</span><input type="file" name="sheet" accept=".csv,.tsv" required></label>'
            '<button type="submit">%s</button></form></section>'
            % (esc(t["sh_title"]), esc(t["sh_hint"]), bad, esc(action), esc(token), esc(t["sh_label"]), star, esc(t["sh_go"])))


def _saved_notice(t, lang, saved):
    if not saved:
        return ""
    return '<p class="ok">%s</p><p><a href="%s">%s</a></p>' % (esc(t["sh_saved"] % saved), web_board._url(lang, path="/launch"), esc(t["sh_launch"]))


def _field_error(t, problem, key):
    why = ((problem or {}).get("fields") or {}).get(key)
    return ' <span class="bad">✕ %s</span>' % esc(t["e_required" if why == "required" else "e_invalid"]) if why else ""


def render_form(name, csrf, runs, lang, envs, token, values=None, problem=None, saved=None):
    """GET /upload (and the answer to a POST that did not pass): the cloud form, the samplesheet form of a national-HPC environment, or one
    sentence and a link when no environment can take an upload. `saved` is the name a samplesheet was just kept under."""
    lang, t = _words(lang)
    values = values or {}
    ours = usable(envs)
    sheet = sheet_ready(envs)
    in_sheet = is_sheet_problem(problem)

    def middle(t_, lang_):
        head = '<main class="main" data-pane="middle"><h1>%s</h1>%s' % (esc(t["title"]), _saved_notice(t, lang, saved))
        if not ours:
            if sheet:
                return head + _sheet_section(t, lang, token, problem) + "</main>"
            return head + '<p>%s</p><p><a href="%s">%s</a></p></main>' % (esc(t["none"]), web_board._url(lang, path="/settings"), esc(t["go_settings"]))
        chosen = values.get("ce") if values.get("ce") in [e["name"] for e in ours] else ours[0]["name"]
        options = "".join('<option value="%s"%s>%s</option>' % (esc(e["name"]), " selected" if e["name"] == chosen else "", esc(e["name"])) for e in ours)
        star = '<span class="req" title="%s">*</span>' % esc(t["g2_req"])
        action = "/upload" + ("?lang=en" if lang == "en" else "")
        form = ('<form class="lform" method="post" action="%s" enctype="multipart/form-data"><input type="hidden" name="csrf" value="%s">'
                '<label><span class="lbl">%s %s</span><select name="ce" required>%s</select></label>'
                '<label><span class="lbl">%s %s</span><input name="name" value="%s" maxlength="64" required>%s<small>%s</small></label>'
                '<label><span class="lbl">%s %s</span><input name="version" value="%s" maxlength="64" required>%s</label>'
                '<label><span class="lbl">%s %s</span><input type="file" name="fastq" multiple required><small>%s</small></label>'
                '<label><span class="lbl">%s</span><input type="file" name="samplesheet"><small>%s</small></label>'
                '<button type="submit">%s</button></form>'
                % (esc(action), esc(token), esc(t["l_ce"]), star, options,
                   esc(t["l_name"]), star, esc(values.get("name", "")), _field_error(t, problem, "name"), esc(t["h_name"]),
                   esc(t["l_version"]), star, esc(values.get("version", "")), _field_error(t, problem, "version"),
                   esc(t["l_fastq"]), star, esc(t["limit"]),
                   esc(t["l_sheet"]), esc(t["h_sheet"]), esc(t["go"])))
        return (head + '<p class="muted">%s</p>%s<p class="muted">%s</p>%s%s%s%s</main>'
                % (esc(t["intro"]), "" if in_sheet else problem_html(t, lang, problem), esc(t["g_legend"]), form, _commands_block(t, envs, name),
                   _sheet_section(t, lang, token, problem) if sheet else "", ""))

    return web_board._frame(name, csrf, runs, lang, "upload", middle, lambda t_, lang_: web_board._right(t_, None), path="/upload")


def _file_row(t, f):
    state = f.get("state") if f.get("state") in SYMBOL else "failed"
    chip = '<span class="%s">%s %s</span>' % (CLASS[state], SYMBOL[state], esc(t["s_" + state]))
    note = ""
    if state == "failed":
        if f.get("message"):
            note = '<br><small>%s</small>' % esc(shown(f["message"], 400))
        elif f.get("expired"):
            note = '<br><small>%s</small>' % esc(t["p_timeout"])
        else:
            note = '<br><small>%s</small>' % esc(t["p_no_reason"])
    return "<tr><td>%s</td><td>%s</td><td>%s%s</td></tr>" % (esc(shown(f.get("name"), 200)), esc(_size_text(f.get("size"))), chip, note)


def render_progress(name, csrf, runs, lang, view):
    """GET /upload/{batch}: one row per file (name, size, symbol + word), and one of four endings: still going, failed, registered, registered refused."""
    lang, t = _words(lang)
    files = view["files"]
    status = view["status"]
    moving = any(f.get("state") in ("queued", "sending") for f in files)

    def middle(t_, lang_):
        head = '<main class="main" data-pane="middle"><h1>%s</h1><p class="muted">%s</p>' % (
            esc(t["p_title"]), esc(t["p_of"] % (view["name"], view["version"], view["ce"])))
        table = ('<table class="tbl"><thead><tr><th>%s</th><th>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table>'
                 % (esc(t["th_file"]), esc(t["th_size"]), esc(t["th_state"]), "".join(_file_row(t, f) for f in files)))
        again = '<p><a href="%s">%s</a></p>' % (web_board._url(lang, path="/upload"), esc(t["p_again"]))
        if status == "registered":
            tail = ('<p class="ok">✓ %s</p><p><a href="%s">%s</a></p>'
                    % (esc(t["p_registered"] % (view["name"], view["version"])), web_board._url(lang, path="/launch"), esc(t["p_go_launch"])))
        elif status == "register_failed":
            places = "".join("<li><code>%s</code></li>" % esc(shown(p, 400)) for p in view.get("places") or [])
            tail = (_bad(t["p_reg_failed"] % web_board.plain_reason(view.get("message"), lang)) + '<p>%s</p><p class="muted">%s</p><ul>%s</ul>%s'
                    % (esc(t["p_keep"]), esc(t["p_places"]), places, again))
        elif status == "failed":
            tail = _bad(t["p_failed"]) + again
        else:
            tail = '<p class="muted">%s</p>' % esc(t["p_running"])
        if view.get("superseded"):
            tail += '<p class="muted">%s</p>' % esc(t["p_superseded"])
        return head + table + tail + "</main>"

    return web_board._frame(name, csrf, runs, lang, "upload", middle, lambda t_, lang_: web_board._right(t_, None), path="/upload/" + view["batch"],
                            refresh=moving)
