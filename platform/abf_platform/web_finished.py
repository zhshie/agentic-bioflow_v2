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


def _package(t, lang, run, outputs, board):
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
    items = [(t["report"], soon), (t["tables"], tables), (t["multiqc"], qc), (t["figures"], soon), (t["methods"], soon), (t["sheet"], soon)]
    lis = "".join('<li><span>%s</span> %s</li>' % (_e(k), v) for k, v in items)
    return '<ul class="pack">%s</ul><p class="off">%s %s</p>' % (lis, _e(t["download"]), soon)


def _size(n, board):
    if not isinstance(n, int) or n < 0:
        return "—"
    return "%.1f KB" % (n / 1024) if n < 1048576 else board._mb(n)


def _downloads(t, lang, run, outputs, board):
    """Links to the existing `/run/file` for the top-level files (at most 20 items, the MultiQC report first); nothing when not ready."""
    out = outputs or {}
    if out.get("found") is False or out.get("state") != "ready":
        return ""
    files = out.get("files") or []
    items = []
    if any(f.get("name") == "multiqc" and f.get("type") == "dir" for f in files):
        items.append('<li><a href="%s">%s</a></li>' % (board._url(lang, run["id"], path="/run/file", sub="multiqc/multiqc_report.html"), _e(t["multiqc"])))
    for f in files:
        if f.get("type") != "file":
            continue
        if f.get("too_large"):
            items.append('<li>%s <span class="muted">%s</span></li>' % (_e(f.get("name")), _e(t["dl_big"])))
        elif f.get("download"):
            items.append('<li><a href="%s">%s</a> <span class="muted">%s</span></li>'
                         % (board._url(lang, run["id"], path="/run/file", sub=f["download"]), _e(f.get("name")), _e(_size(f.get("size"), board))))
    if not items:
        return ""
    more = ""
    if len(items) > 20:
        items = items[:20]
        see = '<a href="%s">%s</a>' % (board._url(lang, run["id"], "results", tab="outputs"), _e(t["see_outputs"]))
        more = '<p class="muted">%s</p>' % _e(t["dl_more"]).replace("%s", see)
    return '<p>%s</p><ul class="pack">%s</ul>%s' % (_e(t["dl_head"]), "".join(items), more)


def render_finished(lang, run, provenance, outputs, user_name):
    """The two sections of the finished stage of a succeeded run: provenance (from `launch_prefill`, `get_run`) and the delivery package
    list (from `run_outputs`). `provenance` None is read as a run with no launch record."""
    from . import web_board      # imported here: web_board imports this module, and only the formatting helpers are wanted from it
    t = STRINGS["en" if lang == "en" else "zh"]
    prov = provenance if isinstance(provenance, dict) else {"found": False}
    return ('<section class="card"><h2>%s</h2>%s</section><section class="card"><h2>%s</h2>%s</section>'
            % (_e(t["prov"]), _provenance(t, run, prov, user_name, web_board), _e(t["pack"]), _package(t, lang, run, outputs, web_board) + _downloads(t, lang, run, outputs, web_board)))
