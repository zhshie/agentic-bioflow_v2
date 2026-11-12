# Nothing existing: the finished stage of a succeeded run (DESIGN.md v2 screen 10, spec finished-stage): provenance and the delivery package list.
"""The finished stage, as a pure function from the answers of the actions to a string.

No database, no file and no network is touched here: `web.py` reads `launch_prefill` and `run_outputs(enqueue=False)` for the logged-in
caller and hands the answers in. Every word of this stage is in the two tables below (zh and en, same keys). Each state is a symbol plus
words; the colour only helps. Nothing here downloads, writes or asks the site for anything: the download block only makes links to the existing `/run/file`.
"""
import html

STRINGS = {
    "zh": {
        "prov": "來源紀錄", "pipeline": "管線", "revision": "版本", "params": "已變更的參數", "ce": "運算環境", "launched": "送出時間",
        "finished": "完成時間", "by": "送出者", "sheet": "樣本表", "later": "之後開放",
        "defaults": "全部採預設值", "gone": "內容已不保留", "gone_note": "該次送出的內容已不保留。",
        "foreign": "此分析並非經由平台送出，無來源紀錄。",
        "pack": "交付包", "report": "報告", "tables": "結果表格", "multiqc": "MultiQC 報告", "figures": "圖", "methods": "方法段落（含版本）",
        "in_folder": "在輸出資料夾", "no_files": "無檔案", "no_multiqc": "該次未產生", "unread": "尚未讀取輸出", "see_outputs": "查看輸出",
        "download": "下載交付包", "dl_head": "下載結果檔", "dl_big": "大於 25 MB", "dl_more": "其餘檔案請至「%s」。",
        "g_title": "圖庫", "g_empty": "圖庫為空。可請自己的 LLM 以 MCP 工具 publish_figure 提出圖，經本人在確認頁按「送出」後存入。",
        "g_broken": "圖庫暫時無法讀取。請稍後再試；若持續發生，請回報給平台管理者。",
        "g_more": "僅顯示開頭的 200 行或 20 KB；其餘請下載全文。", "g_dl_code": "下載程式碼全文", "g_dl_params": "下載參數全文",
        "g_pending": "有存入圖庫的申請待您在確認頁按「送出」。", "g_pending_link": "前往確認頁",
        "g_label": "使用者與 LLM 產生", "g_packed": "已打包", "g_unpacked": "未打包", "g_download": "下載",
        "g_code": "檢視程式碼與參數", "g_code_h": "程式碼", "g_params_h": "參數", "g_pick": "選取 %s",
        "g_pack_btn": "打包所選的圖", "g_pack_note": "交付包將以本次勾選的圖為準；未勾選的圖會移出交付包。",
        "g_del_btn": "刪除 %s", "g_del_note": "刪除後無法復原，圖會一併移出交付包。",
        "f_none": "無", "f_unpacked": "%d 張在圖庫，尚未打包", "f_packed": "已打包 %d 張",
        "gr_pack": "無法打包", "gr_delete": "無法刪除", "gr_unknown": "圖庫裡沒有「%s」。", "gr_bad": "選取的圖名不合規定。",
        "gr_many": "一次最多選取 30 張。", "gr_none": "未變更任何內容。",
        "gr_fail": "未能寫入圖庫，內容沒有變更。請稍後再試，或回報給平台管理者。", "gr_back": "回到完成頁",
    },
    "en": {
        "prov": "Provenance", "pipeline": "Pipeline", "revision": "Revision", "params": "Changed parameters", "ce": "Compute environment",
        "launched": "Launched", "finished": "Finished", "by": "Launched by", "sheet": "Samplesheet", "later": "Coming later",
        "defaults": "All parameters use their defaults", "gone": "Content no longer kept",
        "gone_note": "The content of this launch is no longer kept.",
        "foreign": "Not launched from the platform; there is no provenance record.",
        "pack": "Delivery package", "report": "Report", "tables": "Tables", "multiqc": "MultiQC report", "figures": "Figures",
        "methods": "Methods with versions",
        "in_folder": "In the output folder", "no_files": "No files", "no_multiqc": "Not produced this time", "unread": "Outputs not read yet",
        "see_outputs": "View outputs", "download": "Download delivery package",
        "dl_head": "Download result files", "dl_big": "Over 25 MB", "dl_more": "Other files: see %s.",
        "g_title": "Figure gallery", "g_empty": "The gallery is empty. Ask your own LLM to propose figures with the MCP tool publish_figure; "
                   "they are stored after you press Send on the confirmation page.",
        "g_broken": "The gallery cannot be read right now. Try again later; if it continues, tell the platform administrator.",
        "g_more": "Only the first part is shown (up to 200 lines or 20 KB); download the full text for the rest.",
        "g_dl_code": "Download the full code", "g_dl_params": "Download the full parameters",
        "g_pending": "A request to add figures to the gallery waits for you to press Send on the confirmation page.",
        "g_pending_link": "Open the confirmation page",
        "g_label": "Made by the user and an LLM", "g_packed": "Packed", "g_unpacked": "Not packed", "g_download": "Download",
        "g_code": "View code and parameters", "g_code_h": "Code", "g_params_h": "Parameters", "g_pick": "Select %s",
        "g_pack_btn": "Pack the selected figures",
        "g_pack_note": "The delivery package will hold exactly the figures ticked now; figures not ticked are removed from it.",
        "g_del_btn": "Delete %s", "g_del_note": "This cannot be undone, and the figure is removed from the delivery package too.",
        "f_none": "None", "f_unpacked": "%d in the gallery, not packed yet", "f_packed": "%d packed",
        "gr_pack": "Cannot pack", "gr_delete": "Cannot delete", "gr_unknown": "The gallery has no figure \"%s\".",
        "gr_bad": "A selected figure name is not valid.", "gr_many": "At most 30 figures can be selected at a time.", "gr_none": "Nothing was changed.",
        "gr_fail": "The gallery could not be written and nothing was changed. Try again later or tell the platform administrator.",
        "gr_back": "Back to the finished page",
    },
}


def _e(text):
    return html.escape(str(text), quote=True)


def _later(t):
    return '<span class="later">%s</span>' % _e(t["later"])


def _gap(text):
    return '<span class="muted">— %s</span>' % _e(text)


def _value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _provenance(t, run, prov, user_name, board):
    when_end = board._time(run.get("ended_at"))
    if not prov.get("found"):
        return '<p>%s</p>' % _gap(t["foreign"])
    launched = board.taipei_time(prov.get("launched_at")) or "—"
    note = ""
    if prov.get("kept"):
        params = prov.get("params") or {}
        lines = ("".join('<code>%s</code>' % _e("%s: %s" % (k, _value(v))) for k, v in params.items())) if params else _gap(t["defaults"])
        cells = [(t["pipeline"], _e(prov.get("pipeline") or "—")), (t["revision"], _e(prov.get("revision") or "—")),
                 (t["params"], lines), (t["ce"], _e(prov.get("ce_name") or "—"))]
    else:
        note = '<p class="muted" role="status"><span>—</span> %s</p>' % _e(t["gone_note"])
        cells = [(t[k], _gap(t["gone"])) for k in ("pipeline", "revision", "params", "ce")]
    rows = cells + [(t["launched"], _e(launched)), (t["finished"], _e(when_end)),
            (t["by"], _e(user_name)), (t["sheet"], _later(t))]
    return note + '<dl class="prov">%s</dl>' % "".join("<dt>%s</dt><dd>%s</dd>" % (_e(k), v) for k, v in rows)


def _state(ok, text):
    if ok:
        return '<span class="state-succeeded"><span class="sym">✓</span> %s</span>' % _e(text)
    return '<span class="muted"><span>—</span> %s</span>' % _e(text)


def _figures_row(t, gallery):
    """The `Figures` row of the package: nothing in the gallery, figures in it but none packed, or those that are packed (by name)."""
    figs = gallery["figures"]
    if not figs:
        return _state(False, t["f_none"])
    packed = [f for f in figs if f.get("packed")]
    if not packed:
        return _state(False, t["f_unpacked"] % len(figs))
    return _state(True, t["f_packed"] % len(packed)) + " " + " ".join("<code>%s</code>" % _e(f["name"]) for f in sorted(packed, key=lambda f: f["name"]))


def _package(t, lang, run, outputs, board, gallery=None):
    out = outputs or {}
    ready = out.get("found") is not False and out.get("state") == "ready"
    files = out.get("files") or []
    link = '<a href="%s">%s</a>' % (board._url(lang, run["id"], "results", tab="outputs"), _e(t["see_outputs"]))
    unread = '%s %s' % (_state(False, t["unread"]), link)
    if ready:
        tables = _state(True, t["in_folder"]) if files else _state(False, t["no_files"])
        has_qc = any(f.get("name") == "multiqc" and f.get("type") == "dir" for f in files)
        qc = _state(True, t["in_folder"]) if has_qc else _state(False, t["no_multiqc"])
    else:
        tables = qc = unread
    soon = _later(t)
    figures = _figures_row(t, gallery) if isinstance(gallery, dict) and gallery.get("found") else soon
    items = [(t["report"], soon), (t["tables"], tables), (t["multiqc"], qc), (t["figures"], figures), (t["methods"], soon), (t["sheet"], soon)]
    lis = "".join('<li><span>%s</span> %s</li>' % (_e(k), v) for k, v in items)
    return '<ul class="pack">%s</ul><p class="off">%s %s</p>' % (lis, _e(t["download"]), soon)


def _size(n, board):
    if not isinstance(n, int) or n < 0:
        return "—"
    return "%.1f KB" % (n / 1024) if n < 1048576 else board._mb(n)


def _preview(lang, run, path):
    """` <a>Preview</a>` after the Download link of a file that has a preview by name (web-result-viewer), else nothing."""
    from . import web_preview      # a circular import (web_preview needs web_board), so here
    link = web_preview.preview_link(lang, run["id"], path)
    return " " + link if link else ""


def _downloads(t, lang, run, outputs, board):
    """Links to the existing `/run/file` for the top-level files (at most 20 items, the MultiQC report first); nothing when not ready."""
    out = outputs or {}
    if out.get("found") is False or out.get("state") != "ready":
        return ""
    files = out.get("files") or []
    items = []
    if any(f.get("name") == "multiqc" and f.get("type") == "dir" for f in files):
        items.append('<li><a href="%s">%s</a>%s</li>' % (board._url(lang, run["id"], path="/run/file", sub="multiqc/multiqc_report.html"), _e(t["multiqc"]),
                                                         _preview(lang, run, "multiqc/multiqc_report.html")))
    for f in files:
        if f.get("type") != "file":
            continue
        if f.get("too_large"):
            items.append('<li>%s <span class="muted">%s</span></li>' % (_e(f.get("name")), _e(t["dl_big"])))
        elif f.get("download"):
            items.append('<li><a href="%s">%s</a> <span class="muted">%s</span>%s</li>'
                         % (board._url(lang, run["id"], path="/run/file", sub=f["download"]), _e(f.get("name")), _e(_size(f.get("size"), board)),
                            _preview(lang, run, f["download"])))
    if not items:
        return ""
    more = ""
    if len(items) > 20:
        items = items[:20]
        see = '<a href="%s">%s</a>' % (board._url(lang, run["id"], "results", tab="outputs"), _e(t["see_outputs"]))
        more = '<p class="muted">%s</p>' % _e(t["dl_more"]).replace("%s", see)
    return '<p>%s</p><ul class="pack">%s</ul>%s' % (_e(t["dl_head"]), "".join(items), more)


def _hidden(**fields):
    return "".join('<input type="hidden" name="%s" value="%s">' % (k, _e(v)) for k, v in fields.items() if v is not None)


INLINE_LINES = 200
INLINE_BYTES = 20 * 1024


def _clip(text):
    """(the start of a stored text, whether there is more): at most INLINE_LINES lines or INLINE_BYTES bytes, whichever comes first, cut at a
    whole character; the full text is what `GET /run/figure?...&part=` serves (ruling G5)."""
    shown = "".join(text.splitlines(keepends=True)[:INLINE_LINES])
    if len(shown.encode("utf-8")) > INLINE_BYTES:
        shown = shown.encode("utf-8")[:INLINE_BYTES].decode("utf-8", "ignore")
    return shown, shown != text


def _figure(t, run, f, n):
    """One figure of the gallery: the picture (an <img> loaded from /run/figure), its words, its state, its tick box and its delete button.
    The button belongs to a delete form that sits outside the pack form (form=), so no form is inside another."""
    base = f["url"]      # `/run/figure?run=&name=`, made by the route that read the gallery (this module makes no address from a name)
    name = _e(f["name"])
    box = "pick-%d" % n
    size = f.get("size")
    size_text = "%.1f KB" % (size / 1024) if isinstance(size, int) and size >= 0 else "—"
    state = _state(True, t["g_packed"]) if f.get("packed") else _state(False, t["g_unpacked"])
    caption = "<p>%s</p>" % _e(f["caption"]) if f.get("caption") else ""
    parts = ""
    for key, head, link in (("code", "g_code_h", "g_dl_code"), ("params", "g_params_h", "g_dl_params")):
        if f.get(key):
            shown, cut = _clip(f[key])
            more = '<p class="muted">%s <a href="%s&amp;part=%s">%s</a></p>' % (_e(t["g_more"]), _e(base), key, _e(t[link])) if cut else ""
            parts += '<p class="muted">%s</p><pre>%s</pre>%s' % (_e(t[head]), _e(shown), more)
    details = "<details><summary>%s</summary>%s</details>" % (_e(t["g_code"]), parts) if parts else ""
    return ('<li><figure><img src="%s" alt="%s" width="240" loading="lazy"><figcaption>'
            '<p><code>%s</code> <span class="muted">%s</span></p>%s<p class="muted">%s</p><p>%s</p>'
            '<p><input type="checkbox" id="%s" name="fig" value="%s"> <label for="%s">%s</label></p>'
            '<p><a href="%s&amp;download=1">%s</a></p>%s'
            '<p class="muted">%s</p><p><button type="submit" form="del-%d">%s</button></p></figcaption></figure></li>'
            % (_e(base), _e(f["caption"] or f["name"]), name, _e(size_text), caption, _e(t["g_label"]), state, box, name, box,
               _e(t["g_pick"] % f["name"]), _e(base), _e(t["g_download"]), details, _e(t["g_del_note"]), n, _e(t["g_del_btn"] % f["name"])))


def _gallery(t, lang, run, gallery):
    """The private gallery of the run: a line when a request waits, then either the empty line or every figure with the pack form. No script,
    no polling: the page changes when the person presses a button."""
    note = ""
    if gallery.get("pending"):
        note = ('<p role="status"><span class="sym">…</span> %s <a href="/c/%s">%s</a></p>'
                % (_e(t["g_pending"]), _e(gallery["pending"]), _e(t["g_pending_link"])))
    figs = gallery.get("figures") or []
    if gallery.get("error"):      # a damaged index.json is said so; it is not an empty gallery (ruling G2), and no path is shown
        body = '<p class="bad state-failed" role="status"><span class="sym">✗</span> %s</p>' % _e(t["g_broken"])
    elif not figs:
        body = '<p class="muted" role="status"><span>—</span> %s</p>' % _e(t["g_empty"])
    else:
        token = gallery.get("csrf") or {}
        en = _hidden(lang="en") if lang == "en" else ""
        pack = ('<form method="post" action="/run/figures/pack">%s%s%s<ul class="pack">%s</ul><p class="muted">%s</p>'
                '<p><button type="submit">%s</button></p></form>'
                % (_hidden(csrf=token.get("pack")), _hidden(run=run["id"]), en, "".join(_figure(t, run, f, i) for i, f in enumerate(figs)),
                   _e(t["g_pack_note"]), _e(t["g_pack_btn"])))
        dels = "".join('<form id="del-%d" method="post" action="/run/figure/delete">%s%s%s%s</form>'
                       % (i, _hidden(csrf=token.get("delete")), _hidden(run=run["id"]), _hidden(name=f["name"]), en) for i, f in enumerate(figs))
        body = pack + dels
    return '<section class="card"><h2>%s</h2>%s%s</section>' % (_e(t["g_title"]), note, body)


def refusal_page(lang, answer):
    """(title, body) of the page for a pack or a delete that was refused or failed: a symbol, what happened, that nothing changed, the way back."""
    t = STRINGS["en" if lang == "en" else "zh"]
    title = t["gr_delete"] if answer.get("verb") == "delete" else t["gr_pack"]
    reason = answer.get("reason")
    if reason == "unknown_name":
        line = (t["gr_unknown"] % answer.get("name", "")) + " " + t["gr_none"]
    elif reason == "bad_name":
        line = t["gr_bad"] + " " + t["gr_none"]
    elif reason == "too_many":
        line = t["gr_many"] + " " + t["gr_none"]
    elif reason == "unreadable":
        line = t["g_broken"] + " " + t["gr_none"]
    else:
        line = t["gr_fail"]
    back = answer.get("back", "/")
    return title, ('<p class="bad state-failed"><span class="sym">✗</span> %s</p><p><a href="%s">%s</a></p>'
                   % (_e(line), _e(back), _e(t["gr_back"])))


def render_finished(lang, run, provenance, outputs, user_name, gallery=None):
    """The two sections of the finished stage of a succeeded run: provenance (from `launch_prefill`, `get_run`) and the delivery package
    list (from `run_outputs`). `provenance` None is read as a run with no launch record."""
    from . import web_board      # imported here: web_board imports this module, and only the formatting helpers are wanted from it
    t = STRINGS["en" if lang == "en" else "zh"]
    prov = provenance if isinstance(provenance, dict) else {"found": False}
    shown = _gallery(t, lang, run, gallery) if isinstance(gallery, dict) and gallery.get("found") else ""
    return ('<section class="card"><h2>%s</h2>%s</section><section class="card"><h2>%s</h2>%s</section>%s'
            % (_e(t["prov"]), _provenance(t, run, prov, user_name, web_board), _e(t["pack"]),
               _package(t, lang, run, outputs, web_board, gallery) + _downloads(t, lang, run, outputs, web_board), shown))
