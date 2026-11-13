# Nothing existing: nothing else in this package writes files on a user's own computer or builds R code; fetch-records brings Nextflow's logs to the platform for the index, not result tables to a person.
"""The commands that run on a user's own computer: `studio-connect` stores the platform's address and the user's own token, `fetch-results` pulls the
small result tables of one run into a folder on this computer and prints the R code that loads them in RStudio, and `publish-figure` proposes a figure
drawn there to the gallery of the run (the person, not this command, says yes, at the link the platform gives).

Everything comes through `studio_remote` (the MCP tools run_outputs and read_run_file, list_compute_envs for a hint, and publish_figure); the platform decides
what a person may see, and which folders of the site may be read, so nothing of that is judged here. The commands read the platform and write
only to the folder the user chose; they start no program, run no R, and open no database of the platform."""
import asyncio
import base64
import os
import re
import stat
import sys
import time
import unicodedata
from pathlib import Path

from . import cliout, studio_remote
from .actions.figures import MAX_BUNDLE_BYTES, MAX_CAPTION_CHARS, MAX_CODE_BYTES, MAX_PARAMS_BYTES
from .jobs import RUN_FILE_MAX_BYTES

POLL_SECONDS = 2.0            # a tool that answers `loading` is asked again after this many seconds
DEADLINE_SECONDS = 120.0      # how long one listing, or one file, may stay `loading`
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_FILES = 200               # files fetched in one run of the command
MAX_DEPTH = 3                 # levels of the results tree that are listed, the first included
MAX_DIRS = 100                # folders listed in one run of the command (one call of run_outputs each, whatever the platform lists)
MAX_PAGES = 200               # pages read of one file (a page is up to 200,000 characters, so a file of 25 MB is at most 131)
MAX_NAME_BYTES = 255          # the longest part of a path that is written
COMMAND_DEADLINE_SECONDS = 900.0   # the whole command, listing and reading, whatever each single wait allows
TABLE_SUFFIXES = (".tsv", ".csv", ".txt", ".md", ".json")
HTML_SUFFIXES = (".html", ".htm")
LIST_LIMIT = 50               # lines of one kind that are printed one by one
PUBLISH_DEADLINE_SECONDS = 120.0   # the whole of publish-figure, whatever the connection allows each try

STRINGS = {
    "zh": {
        "folder_line": "結果資料夾：{path}",
        "got": "已取得 {rel}（{size} 位元組）",
        "got_over": "已取得 {rel}（{size} 位元組），已覆蓋原有的檔案。",
        "skip": "略過 {rel}：{why}",
        "why_ext": "不是文字表格或報告（副檔名 {ext}），不經網路傳送",
        "why_html": "網頁報告不經網路傳送，須用瀏覽器登入平台下載",
        "why_binary": "平台回報為二進位檔，不經網路傳送",
        "why_big": "檔案為 {size} 位元組，大於單檔上限 {limit} 位元組，未下載",
        "why_path": "路徑不安全（{why}），未下載",
        "why_nopath": "平台沒有提供可讀取的路徑，未下載",
        "why_other": "不是一般檔案",
        "why_total": "已達總量上限 {limit} 位元組，未下載",
        "why_deep": "資料夾位於第 {limit} 層以下，未列出",
        "fail": "未取得 {rel}：{reason}",
        "fail_wait": "未在 {seconds} 秒的期限內取得",
        "fail_list": "無法列出資料夾 {rel}：{reason}",
        "fail_write": "無法寫入本機檔案：{why}",
        "fail_end": "部分檔案未取得。請依上列原因處理後，再執行一次。",
        "pending": "尚未取得：{names}",
        "more": "另有 {n} 個同類項目未逐一列出。",
        "incomplete": "結果並非全部取得：有檔案或資料夾因個數、層數或總量的上限而未取。請到站台的結果資料夾取用其餘檔案。",
        "summary": "取到 {got} 個、略過 {skipped} 個",
        "summary_fail": "、未取得 {failed} 個",
        "summary_tail": "；資料夾 {path}",
        "paste": "將下列程式碼貼入 RStudio 的 Console：",
        "rest": "其餘檔案見資料夾",
        "site_reply": "站台回覆：{reason}",
        "why_symlink": "目的位置是符號連結",
        "why_outside": "目的位置在資料夾之外",
        "why_empty": "空白",
        "why_abs": "絕對路徑或含反斜線",
        "why_dots": "含有 .. 或空的部分",
        "why_hidden": "含有以點開頭的部分",
        "why_control": "含有控制字元或無法編碼的字元",
        "why_long": "有一段名稱的長度大於 {limit} 位元組",
        "why_local": "這台電腦無法使用該名稱",
        "why_mismatch": "要寫入的名稱與它所在的資料夾和名稱不一致",
        "why_badrow": "列表中的這一項格式不正確",
        "why_dup": "在列表中出現不只一次，只取一次",
        "why_dup_case": "與 {other} 只差大小寫，這台電腦可能視為同一個檔案，未下載",
        "fail_pages": "讀了 {limit} 頁仍未讀完",
        "fail_total": "整個指令已達 {seconds} 秒的總期限而停止",
        "dirs_limit": "另有 {n} 個資料夾因已列出 {limit} 個的上限而未列出。",
        "pub_figure": "圖：{name}（{size} 位元組）",
        "pub_pending": "尚未存入；請本人在瀏覽器開啟下列連結並按送出：",
        "pub_bundle_note": "圖存入後會在私有圖庫，只有本人看得到，不會加入交付包；要不要打包，由本人在網頁勾選。",
        "pub_saved": "已存入私有圖庫：{name}（{size} 位元組）。這張圖不會加入交付包；要不要打包，由本人在網頁勾選。",
        "pub_refused": "未送出：{reason}",
        "pub_no_file": "無法讀取 {what} {path}（{why}）。請確認路徑正確且為一般檔案。",
        "pub_why_missing": "找不到或沒有讀取權限",
        "pub_why_not_file": "不是一般檔案",
        "pub_why_utf8": "不是 UTF-8 文字",
        "pub_why_nul": "含有 NUL 字元，不是純文字",
        "pub_what_figure": "圖檔",
        "pub_what_code": "code 檔案",
        "pub_what_params": "params 檔案",
        "pub_too_big": "{what} {path} 大於上限 {limit} 位元組，未送出。",
        "pub_too_big_figure": "圖檔 {path} 大於單次送出的合計上限 {limit} 位元組，未送出。請縮小圖檔後再試。",
        "pub_caption_long": "caption 大於上限 {limit} 字元，未送出。請縮短說明後再試。",
        "pub_caption_line": "caption 不可含換行或控制字元，只能是單行文字，未送出。",
        "pub_bad_text": "{what} 含有無法編碼為 UTF-8 的字元，未送出。",
        "pub_bad_name": "圖檔的檔名含有無法編碼為 UTF-8 的字元，未送出。請改用一般的檔名。",
        "pub_deadline": "整個指令已達 {seconds} 秒的總期限而停止，圖尚未送出或結果不明。請稍後再試。",
    },
    "en": {
        "folder_line": "Results folder: {path}",
        "got": "Fetched {rel} ({size} bytes)",
        "got_over": "Fetched {rel} ({size} bytes); the earlier file was overwritten.",
        "skip": "Skipped {rel}: {why}",
        "why_ext": "not a text table or report (extension {ext}); it is not sent over the network",
        "why_html": "a web report is not sent over the network; log in to the platform with a browser to download it",
        "why_binary": "the platform says it is a binary file; it is not sent over the network",
        "why_big": "the file is {size} bytes, above the limit of {limit} bytes for one file; not downloaded",
        "why_path": "the path is not safe ({why}); not downloaded",
        "why_nopath": "the platform gave no path that can be read; not downloaded",
        "why_other": "not a regular file",
        "why_total": "the total limit of {limit} bytes was reached; not downloaded",
        "why_deep": "the folder is below level {limit}; not listed",
        "fail": "Not fetched {rel}: {reason}",
        "fail_wait": "not obtained within the {seconds} second limit",
        "fail_list": "The folder {rel} could not be listed: {reason}",
        "fail_write": "The local file could not be written: {why}",
        "fail_end": "Some files were not fetched. Deal with the reasons above, then run it again.",
        "pending": "Not fetched yet: {names}",
        "more": "{n} more items of the same kind are not listed one by one.",
        "incomplete": "The result is not all fetched: some files or folders were left out by the limit on files, levels or total size. Get the rest from the results folder on the site.",
        "summary": "Fetched {got}, skipped {skipped}",
        "summary_fail": ", not fetched {failed}",
        "summary_tail": "; folder {path}",
        "paste": "Paste the code below into the RStudio Console:",
        "rest": "The other files are in the folder",
        "site_reply": "The site answered: {reason}",
        "why_symlink": "the target is a symbolic link",
        "why_outside": "the target is outside the folder",
        "why_empty": "empty",
        "why_abs": "absolute or has a backslash",
        "why_dots": "has .. or an empty part",
        "why_hidden": "has a part that starts with a dot",
        "why_control": "has a control character or a character that cannot be encoded",
        "why_long": "a part of the name is longer than {limit} bytes",
        "why_local": "this computer cannot use that name",
        "why_mismatch": "the name to write is not the folder it is in plus its name",
        "why_badrow": "this entry of the listing is not in the right shape",
        "why_dup": "it is listed more than once; it is fetched once",
        "why_dup_case": "it differs from {other} only in case, which this computer may take for the same file; not downloaded",
        "fail_pages": "not read to the end within {limit} pages",
        "fail_total": "the whole command was stopped at its total limit of {seconds} seconds",
        "dirs_limit": "{n} more folders are not listed because of the limit of {limit} folders listed.",
        "pub_figure": "Figure: {name} ({size} bytes)",
        "pub_pending": "Not saved yet: the person must open the link below in a browser and press Send:",
        "pub_bundle_note": "Once saved the figure is in the private gallery that only the person sees, and it will not be added to the delivery bundle; the person ticks it on the web page if it is to go in.",
        "pub_saved": "Saved in the private gallery: {name} ({size} bytes). The figure will not be added to the delivery bundle; the person ticks it on the web page if it is to go in.",
        "pub_refused": "Not sent: {reason}",
        "pub_no_file": "The {what} {path} cannot be read ({why}). Make sure the path is right and is a regular file.",
        "pub_why_missing": "not found, or no permission to read it",
        "pub_why_not_file": "not a regular file",
        "pub_why_utf8": "not UTF-8 text",
        "pub_why_nul": "has a NUL character, so it is not plain text",
        "pub_what_figure": "figure file",
        "pub_what_code": "code file",
        "pub_what_params": "params file",
        "pub_too_big": "The {what} {path} is over the limit of {limit} bytes; nothing was sent.",
        "pub_too_big_figure": "The figure file {path} is over the limit of {limit} bytes for one send; nothing was sent. Make the file smaller and try again.",
        "pub_caption_long": "The caption is over the limit of {limit} characters; nothing was sent. Shorten it and try again.",
        "pub_caption_line": "The caption must be one line of text with no line break or control character; nothing was sent.",
        "pub_bad_text": "The {what} has a character that cannot be encoded as UTF-8; nothing was sent.",
        "pub_bad_name": "The file name of the figure has a character that cannot be encoded as UTF-8; nothing was sent. Use a plain file name.",
        "pub_deadline": "The whole command was stopped at its total limit of {seconds} seconds; the figure was not sent or the outcome is not known. Try again later.",
    },
}


def _t(key, **kw):
    return STRINGS[studio_remote.lang()][key].format(**{k: studio_remote.clean_text(v) if isinstance(v, str) else v for k, v in kw.items()})


def _bad(text):
    cliout.err(text)


_R_ONLY = False       # `fetch-results --r`: standard output holds the R code and nothing else (the line of the downstream page feeds it to R's parse())


def _progress(text):
    """A line that tells how the command is doing: standard output as always, standard error under --r."""
    if _R_ONLY:
        print(text, file=sys.stderr, flush=True)
    else:
        cliout.say(text)


def _fail(e):
    what, nxt = e.parts()
    cliout.err(e.text, what, nxt)
    return e.code


# ---- the R code -----------------------------------------------------------------------------------------------------------------------------

def _r_text(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _r_name(rel, used):
    stem = re.sub(r"[^A-Za-z0-9_]", "_", Path(rel.replace("\\", "/")).stem) or "table"
    if not stem[0].isalpha():
        stem = "t_" + stem
    name, n = stem, 2
    while name in used:
        name, n = "%s_%d" % (stem, n), n + 1
    used.add(name)
    return name


def r_snippet(files, folder, header=True):
    """The lines to paste in the RStudio Console to read the tables in `files` (paths relative to `folder`): one line for each ASV or counts table, or
    for the first five tables when there is none of those. Pure: no R is run and nothing is looked up. Empty when no file is a table."""
    def suffix(f):
        return Path(f.replace("\\", "/")).suffix.lower()
    tables = [f for f in files if suffix(f) in (".tsv", ".csv")]
    asv = [f for f in tables if suffix(f) == ".tsv" and re.search(r"asv|feature-table|abundance", f.rsplit("/", 1)[-1].lower())]
    counts = [f for f in tables if "counts" in f.rsplit("/", 1)[-1].lower()]
    chosen = list(dict.fromkeys(asv + counts))
    more = False
    if not chosen:
        chosen, more = tables[:5], len(tables) > 5
    if not chosen:
        return ""
    base = _r_text(str(folder).replace("\\", "/"))
    lines, used = ([_t("paste")] if header else []), set()
    for f in chosen:
        fn = "read.csv" if suffix(f) == ".csv" else "read.delim"
        lines.append('%s <- %s(file.path("%s", "%s"), check.names = FALSE, row.names = 1)' % (_r_name(f, used), fn, base, _r_text(f)))
    if more:
        lines.append("# " + _t("rest"))
    return "\n".join(lines)


# ---- fetch-results --------------------------------------------------------------------------------------------------------------------------

class _Refused(Exception):
    """A path that must not be written; the message is the reason in words."""


def _unsafe(rel):
    """The reason a path the platform gave is not a plain relative path inside the results, or None. The platform checks this too; it is checked again
    here because the next step is writing a file on this computer."""
    if not isinstance(rel, str) or not rel:
        return _t("why_empty")
    if rel.startswith("/") or "\\" in rel or re.match(r"^[A-Za-z]:", rel):
        return _t("why_abs")
    if re.search(r"[\x00-\x1f\x7f-\x9f]", rel):
        return _t("why_control")
    try:
        encoded = rel.encode("utf-8")
    except UnicodeEncodeError:
        return _t("why_control")
    if any(len(p) > MAX_NAME_BYTES for p in encoded.split(b"/")):
        return _t("why_long", limit=MAX_NAME_BYTES)
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return _t("why_dots")
    if any(p.startswith(".") for p in parts):
        return _t("why_hidden")
    return None


def _target(base, rel):
    """The place `rel` is written to, or _Refused: inside `base` once resolved, and no link on the way (a link is never followed)."""
    try:
        cur = base
        for part in rel.split("/"):
            cur = cur / part
            if cur.is_symlink():
                raise _Refused(_t("why_symlink"))
        target = base.joinpath(*rel.split("/"))
        resolved = target.resolve()
    except (OSError, ValueError):
        raise _Refused(_t("why_local")) from None
    if resolved != base and base not in resolved.parents:
        raise _Refused(_t("why_outside"))
    return target


def _write(target, data):
    """Write `data` to `target` through a temporary file next to it and one replace; returns whether a file was replaced."""
    existed = target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(".abf-%s.%s.tmp" % (target.name, os.urandom(4).hex()))
    try:
        with open(tmp, "xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return existed


async def _ask(session, name, args):
    """One tool call, asked again every POLL_SECONDS while it says `loading`, until DEADLINE_SECONDS; the last answer, or {state: timeout}."""
    end = time.monotonic() + DEADLINE_SECONDS
    answer = await session.call_tool(name, args)
    while isinstance(answer, dict) and answer.get("found") is not False and answer.get("state") == "loading":
        if time.monotonic() >= end:
            return {"found": True, "state": "timeout"}
        await asyncio.sleep(POLL_SECONDS)
        answer = await session.call_tool(name, args)
    return answer


class _Report:
    def __init__(self):
        self.got, self.skipped, self.failed, self.pending = [], [], [], []
        self.incomplete = False        # something was left out that is not a deliberate skip
        self.problem = False           # the exit code is 1
        self.site_closed = False
        self.hidden = {}
        self.dirs = 0                  # folders listed so far, the first level excluded
        self.listed = {}               # lower case path -> the path as it was listed

    def skip(self, rel, why, problem=False):
        self.skipped.append(studio_remote.clean_text(rel))
        if len(self.skipped) <= LIST_LIMIT:
            _progress(_t("skip", rel=rel, why=why))
        self.problem = self.problem or problem

    def fail(self, rel, reason):
        self.failed.append(studio_remote.clean_text(rel))
        _bad(_t("fail", rel=rel, reason=reason))
        self.problem = True


async def _site_closed(session, report, answer, compute_env):
    """Tell that the platform is reachable and the link to the site is not open; once, with what the platform knows of that link."""
    if report.site_closed:
        return
    report.site_closed = True
    _bad(studio_remote.tr("site_closed"))
    reason = answer.get("reason") or answer.get("message")
    if isinstance(reason, str) and reason:
        _bad(_t("site_reply", reason=reason))
    for line in await studio_remote.site_state_lines(session, compute_env):
        _bad(line)


async def _list(session, run_id, report, candidates, path, depth, answer, compute_env):
    """List one level of the results and everything below it down to MAX_DEPTH; fills `candidates` with (path, size) of what is to be read."""
    prefix = path + "/" if path else ""
    rows = answer.get("files")
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        report.incomplete = report.problem = True
        _bad(_t("fail_list", rel=path or ".", reason=studio_remote.tr("bad_answer")))
        return
    for row in rows:
        name = row.get("name") if isinstance(row, dict) else None
        if not isinstance(name, str) or not name:
            report.incomplete = True
            report.skip(prefix + "?", _t("why_badrow"), problem=True)
            continue
        kind = row.get("type")
        if kind == "dir":
            enter = row.get("enter")
            if not isinstance(enter, str) or not enter:
                report.skip(prefix + name, _t("why_nopath"), problem=True)
            elif depth + 1 > MAX_DEPTH:
                report.incomplete = True
                report.skip(enter, _t("why_deep", limit=MAX_DEPTH), problem=True)
            elif report.dirs >= MAX_DIRS:
                report.incomplete = report.problem = True
                report.hidden["dirs"] = report.hidden.get("dirs", 0) + 1
            else:
                report.dirs += 1
                sub = await _ask(session, "run_outputs", {"run_id": run_id, "path": enter})
                if sub.get("found") is not False and sub.get("state") == "ready":
                    await _list(session, run_id, report, candidates, enter, depth + 1, sub, compute_env)
                else:
                    report.incomplete = report.problem = True
                    _bad(_t("fail_list", rel=enter, reason=_why(sub)))
            continue
        download = row.get("download")
        shown = download if isinstance(download, str) and download else prefix + name
        ext = Path(name).suffix.lower()
        size = row.get("size")
        size = max(size, 0) if isinstance(size, int) and not isinstance(size, bool) else 0
        if kind != "file":
            report.skip(shown, _t("why_other"))
        elif ext in HTML_SUFFIXES:
            report.skip(shown, _t("why_html"))
        elif ext not in TABLE_SUFFIXES:
            report.skip(shown, _t("why_ext", ext=ext or "-"))
        elif row.get("too_large") or size > RUN_FILE_MAX_BYTES:
            report.skip(shown, _t("why_big", size=size, limit=RUN_FILE_MAX_BYTES), problem=True)
        elif not isinstance(download, str) or not download:
            report.skip(shown, _t("why_nopath"), problem=True)
        elif _unsafe(download) or _unsafe(name) or "/" in name:
            report.skip(shown, _t("why_path", why=_unsafe(download) or _unsafe(name) or _t("why_abs")), problem=True)
        elif download != prefix + name:
            report.skip(shown, _t("why_mismatch"), problem=True)
        elif download in report.listed.values():
            report.skip(shown, _t("why_dup"))
        elif download.lower() in report.listed:
            report.skip(shown, _t("why_dup_case", other=report.listed[download.lower()]), problem=True)
        elif len(candidates) >= MAX_FILES:
            report.incomplete = True
            report.hidden["limit"] = report.hidden.get("limit", 0) + 1
            report.problem = True
        else:
            report.listed[download.lower()] = download
            candidates.append((download, size))


def _why(answer):
    """What to say when a tool did not give what was asked: its reason or message, or that the deadline passed."""
    if isinstance(answer, dict) and answer.get("state") == "timeout":
        return _t("fail_wait", seconds=DEADLINE_SECONDS)
    return _reason_of(answer, studio_remote.tr("tool_error"))


def _reason_of(answer, default):
    reason = answer.get("reason") or answer.get("message") if isinstance(answer, dict) else None
    return studio_remote.clean_text(reason) if isinstance(reason, str) and reason else default


async def _read(session, run_id, rel):
    """Read one file page by page. Returns ("ok", bytes), ("binary", None), ("big", size) or ("fail", answer); the pieces are joined only when the
    last one has come, so nothing short of the whole file is ever written. The limit of one file counts UTF-8 bytes; a page is at most MAX_PAGES."""
    pieces, offset, total, pages, more = [], 0, 0, 0, True
    while more:
        if pages >= MAX_PAGES:
            return "fail", {"reason": _t("fail_pages", limit=MAX_PAGES)}
        pages += 1
        answer = await _ask(session, "read_run_file", {"run_id": run_id, "path": rel, "offset": offset})
        state = answer.get("state")
        if answer.get("found") is False or state not in ("ready", "too_large"):
            return "fail", answer
        if state == "too_large":
            return "big", answer.get("size")
        if answer.get("kind") != "text":
            return "binary", None
        text, nxt = answer.get("text"), answer.get("next_offset")
        try:
            piece = text.encode("utf-8") if isinstance(text, str) else None
        except UnicodeEncodeError:
            piece = None
        if piece is None or (nxt is not None and (not isinstance(nxt, int) or isinstance(nxt, bool) or nxt <= offset or not piece)):
            return "fail", {"reason": studio_remote.tr("bad_answer")}
        total += len(piece)
        if total > RUN_FILE_MAX_BYTES:
            return "big", total
        pieces.append(piece)
        more, offset = nxt is not None, nxt
    return "ok", b"".join(pieces)


def _folder_of(args):
    if args.dir:
        return Path(args.dir).expanduser().absolute()
    name = re.sub(r"[^A-Za-z0-9._-]", "_", args.run).lstrip(".")[:100] or "run"
    return Path.home() / "abf-results" / name


async def _fetch(args):
    """The command inside one deadline for the whole of it (COMMAND_DEADLINE_SECONDS); what was written before the deadline stays, and the rest is
    listed as not fetched."""
    folder = _folder_of(args)
    report, candidates = _Report(), []
    try:
        code = await asyncio.wait_for(_work(args, folder, report, candidates), COMMAND_DEADLINE_SECONDS)
    except asyncio.TimeoutError:
        done = set(report.got) | set(report.failed) | set(report.skipped)
        report.pending = [r for r, _ in candidates if r not in done]
        report.problem = report.incomplete = True
        _bad(_t("fail_total", seconds=COMMAND_DEADLINE_SECONDS))
        return _finish(report, folder)
    return code


async def _work(args, folder, report, candidates):
    run_id = args.run
    async with studio_remote.open_session() as session:
        root = await _ask(session, "run_outputs", {"run_id": run_id})
        if root.get("found") is False:
            _bad(_reason_of(root, ""))
            return 1
        state = root.get("state")
        compute_env = root.get("compute_env")
        if state != "ready":
            if studio_remote.is_site_closed(root):
                await _site_closed(session, report, root, compute_env)
            elif state == "timeout":
                _bad(_t("fail_list", rel=".", reason=_why(root)))
            else:
                _bad(_why(root))
            return 1
        _progress(_t("folder_line", path=folder))
        await _list(session, run_id, report, candidates, "", 1, root, compute_env)
        base, total = folder.resolve(), 0
        for index, (rel, size) in enumerate(candidates):
            if total + size > MAX_TOTAL_BYTES:
                report.problem = report.incomplete = True
                report.pending = [r for r, _ in candidates[index:]]
                break
            try:
                target = _target(base, rel)
            except _Refused as e:
                report.skip(rel, _t("why_path", why=e), problem=True)
                continue
            kind, data = await _read(session, run_id, rel)
            if kind == "binary":
                report.skip(rel, _t("why_binary"), problem=True)
            elif kind == "big":
                report.skip(rel, _t("why_big", size=data, limit=RUN_FILE_MAX_BYTES), problem=True)
            elif kind == "fail":
                if studio_remote.is_site_closed(data):
                    await _site_closed(session, report, data, compute_env)
                    report.problem = True
                    report.pending = [r for r, _ in candidates[index:]]
                    break
                report.fail(rel, _why(data))
            elif total + len(data) > MAX_TOTAL_BYTES:
                report.problem = report.incomplete = True
                report.pending = [r for r, _ in candidates[index:]]
                break
            else:
                try:
                    over = _write(target, data)
                except OSError as e:
                    report.fail(rel, _t("fail_write", why=e.strerror or "?"))
                    continue
                total += len(data)
                report.got.append(rel)
                _progress(_t("got_over" if over else "got", rel=rel, size=len(data)))
    return _finish(report, folder)


def _finish(report, folder):
    if report.hidden.get("limit"):
        _progress(_t("more", n=report.hidden["limit"]))
    if report.hidden.get("dirs"):
        _progress(_t("dirs_limit", n=report.hidden["dirs"], limit=MAX_DIRS))
    if len(report.skipped) > LIST_LIMIT:
        _progress(_t("more", n=len(report.skipped) - LIST_LIMIT))
    if report.pending:
        names = "、".join(report.pending[:LIST_LIMIT]) if studio_remote.lang() == "zh" else ", ".join(report.pending[:LIST_LIMIT])
        _bad(_t("pending", names=names))
    line = _t("summary", got=len(report.got), skipped=len(report.skipped))
    if report.failed:
        line += _t("summary_fail", failed=len(report.failed))
    _progress(line + _t("summary_tail", path=folder))
    if report.incomplete:
        _progress(_t("incomplete"))
    if report.failed or report.pending:
        _bad(_t("fail_end"))
    code = r_snippet(report.got, folder, header=not _R_ONLY)
    if code:
        cliout.say(code)
    cliout.set_data({"folder": str(folder), "fetched": report.got, "skipped": report.skipped, "failed": report.failed})
    return 1 if (report.problem or report.failed or report.incomplete) else 0


def cmd_fetch_results(args):
    global _R_ONLY
    _R_ONLY = bool(getattr(args, "r", False))
    try:
        return asyncio.run(_fetch(args))
    except studio_remote.StudioError as e:
        return _fail(e)
    finally:
        _R_ONLY = False


# ---- studio-connect -------------------------------------------------------------------------------------------------------------------------

async def _check(server, token):
    async with studio_remote.open_session({"server": server, "token": token}) as session:
        await session.tool_names()


def cmd_studio_connect(args):
    try:
        server = studio_remote.check_server(args.server)
        token = studio_remote.check_token(sys.stdin.readline() if args.token_stdin else studio_remote.ask_token())
        if not args.no_check:
            asyncio.run(_check(server, token))
        path, replaced = studio_remote.save_config(server, token)
    except studio_remote.StudioError as e:
        return _fail(e)
    cliout.say(studio_remote.tr("server_line", server=server))
    cliout.say(studio_remote.tr("saved", path=path))
    if replaced:
        cliout.say(studio_remote.tr("overwritten"))
    if not studio_remote.permission_bits_trusted():
        cliout.say(studio_remote.tr("cloud_note"))
    cliout.set_data({"server": server, "settings_file": str(path), "replaced": replaced})
    return 0


# ---- publish-figure ---------------------------------------------------------------------------------------------------------------------------

class _Local(Exception):
    """Something on this computer that stops the figure before anything is sent; the message is the sentence to show."""


def _read_local(path, limit, what, too_big):
    """The bytes of a regular file of at most `limit` bytes (never more than limit + 1 read), or _Local saying which file and why."""
    shown = studio_remote.clean_text(str(path))
    try:
        st = os.stat(path)
        if not stat.S_ISREG(st.st_mode):
            raise _Local(_t("pub_no_file", what=_t(what), path=shown, why=_t("pub_why_not_file")))
        if st.st_size > limit:
            raise _Local(_t(too_big, what=_t(what), path=shown, limit=limit))
        with open(path, "rb") as f:
            data = f.read(limit + 1)
    except OSError:
        raise _Local(_t("pub_no_file", what=_t(what), path=shown, why=_t("pub_why_missing"))) from None
    if len(data) > limit:
        raise _Local(_t(too_big, what=_t(what), path=shown, limit=limit))
    return data


def _read_text(path, limit, what):
    """The UTF-8 text of a code or params file (strict: a file that is not UTF-8 is refused, and so is one with a NUL); the limit counts bytes."""
    data = _read_local(path, limit, what, "pub_too_big")
    shown = studio_remote.clean_text(str(path))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise _Local(_t("pub_no_file", what=_t(what), path=shown, why=_t("pub_why_utf8"))) from None
    if chr(0) in text:
        raise _Local(_t("pub_no_file", what=_t(what), path=shown, why=_t("pub_why_nul")))
    return text


def _caption_problem(caption):
    """The reason a caption cannot be sent, or None: one line of at most MAX_CAPTION_CHARS characters that can be encoded as UTF-8."""
    try:
        caption.encode("utf-8")
    except UnicodeEncodeError:
        return _t("pub_bad_text", what="caption")
    if any(unicodedata.category(ch) in ("Cc", "Zl", "Zp") for ch in caption):
        return _t("pub_caption_line")
    if len(caption) > MAX_CAPTION_CHARS:
        return _t("pub_caption_long", limit=MAX_CAPTION_CHARS)
    return None


def _figure_item(args):
    """(the one figure of the call, the bytes of the image), or _Local. Only what can be told here is checked, with the limits of the platform's own
    gallery module; the file name, the type and the content are judged by the platform, whose reason is shown as it is."""
    name = Path(args.figure).name
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        raise _Local(_t("pub_bad_name")) from None
    data = _read_local(args.figure, MAX_BUNDLE_BYTES, "pub_what_figure", "pub_too_big_figure")
    encoded = base64.b64encode(data).decode("ascii")
    if len(encoded) > MAX_BUNDLE_BYTES:
        raise _Local(_t("pub_too_big_figure", what="", path=studio_remote.clean_text(str(args.figure)), limit=MAX_BUNDLE_BYTES))
    item = {"filename": name, "content_base64": encoded}
    if args.code:
        item["code"] = _read_text(args.code, MAX_CODE_BYTES, "pub_what_code")
    if args.params:
        item["params"] = _read_text(args.params, MAX_PARAMS_BYTES, "pub_what_params")
    if args.caption is not None:
        problem = _caption_problem(args.caption)
        if problem:
            raise _Local(problem)
        item["caption"] = args.caption
    return item, len(data)


async def _publish(run_id, item, size):
    """One call of publish_figure, once: no wait, no second call, nothing sent that stands for the person's yes. The platform answers `pending` with the
    link where the person says yes (printed as given, never opened), `refused` with a reason, or (when the platform's own form was answered) `ok`."""
    async def go():
        async with studio_remote.open_session() as session:
            return await session.call_tool("publish_figure", {"run_id": run_id, "figures": [item]})
    try:
        answer = await asyncio.wait_for(go(), PUBLISH_DEADLINE_SECONDS)
    except asyncio.TimeoutError:
        _bad(_t("pub_deadline", seconds=PUBLISH_DEADLINE_SECONDS))
        return 1
    answer = answer if isinstance(answer, dict) else {}
    state, url, reason = answer.get("state"), answer.get("url"), answer.get("reason")
    name = item["filename"]
    if state == "pending" and isinstance(url, str) and url.strip():
        cliout.say(_t("pub_figure", name=name, size=size))
        cliout.say(_t("pub_pending"))
        cliout.say(studio_remote.clean_text(url.strip()))
        cliout.say(_t("pub_bundle_note"))
        cliout.set_data({"state": "pending", "figure": name, "size": size, "confirmation_url": url.strip()})
        return 0
    if state == "ok":
        cliout.say(_t("pub_saved", name=name, size=size))
        cliout.set_data({"state": "ok", "figure": name, "size": size})
        return 0
    if state == "refused" and isinstance(reason, str) and reason.strip():
        _bad(_t("pub_refused", reason=reason))
        return 1
    _bad(studio_remote.tr("bad_answer"))
    return 1


def cmd_publish_figure(args):
    try:
        item, size = _figure_item(args)
    except _Local as e:
        _bad(str(e))
        return 1
    try:
        return asyncio.run(_publish(args.run, item, size))
    except studio_remote.StudioError as e:
        return _fail(e)


# ---- the command line -----------------------------------------------------------------------------------------------------------------------

def _no_unknown_options(parser):
    """An option the command does not have (the token on the command line, say) is refused by name only: argparse would print the whole argument,
    and a value that follows such an option can be a secret."""
    original = parser.parse_known_args

    def parse_known_args(args=None, namespace=None):
        ns, extras = original(args, namespace)
        if extras:
            names = sorted({a.split("=", 1)[0] for a in extras if a.startswith("-")})
            parser.error("unrecognized options: %s (the token is never taken from the command line)" % (", ".join(names) or "none"))
        return ns, extras
    parser.parse_known_args = parse_known_args


def add_commands(sub):
    s = sub.add_parser("studio-connect", allow_abbrev=False,
                       help="store the platform's address and your own token on this computer (run once)",
                       description="Keep the platform's public address and your own personal token in a settings file on this computer, so that "
                                   "fetch-results can read the result tables of your runs. The token is issued by the platform administrator "
                                   "with `abf-platform pat new --user <name>`; it is asked at a hidden prompt (or read from standard input "
                                   "with --token-stdin) and is never printed.")
    s.add_argument("--server", required=True, help="the platform's public address: https://host, no path (http only for this computer itself)")
    s.add_argument("--token-stdin", action="store_true", help="read the token from standard input instead of asking at a hidden prompt")
    s.add_argument("--no-check", action="store_true", help="store without first connecting to the platform to check the token (for when this computer is offline)")
    s.set_defaults(func=cmd_studio_connect)
    _no_unknown_options(s)

    f = sub.add_parser("fetch-results", allow_abbrev=False,
                       help="pull the small result tables of one run to this computer and print the R code that loads them (read only)",
                       description="Read the small result tables (.tsv .csv .txt .md .json, at most 25 MB each) of one run through the platform "
                                   "into a folder on this computer and print the R code that loads them in RStudio. It is not fetch-records, "
                                   "which reads Nextflow's own logs back to the platform for the index. Web reports and binary files are not "
                                   "fetched. Exit code: 0 all well, 1 something was not fetched, 2 not set up (run studio-connect), 3 no connection.")
    f.add_argument("run", help="the run id")
    f.add_argument("--dir", help="the folder on this computer to put the files in (default: ~/abf-results/<run>)")
    f.add_argument("--r", action="store_true", help="print only the R code on standard output (progress and messages go to standard error), for the line of the downstream page")
    f.set_defaults(func=cmd_fetch_results)
    _no_unknown_options(f)

    p = sub.add_parser("publish-figure", allow_abbrev=False,
                       help="propose one figure drawn on this computer to the gallery of a run; you press the button at the link it prints",
                       description="Propose one figure (a PNG, SVG or JPEG file, with the code and the parameters that made it when you give them) to the "
                                   "gallery of one of your runs. Nothing is stored by this command: the platform gives a link, you open it in a browser, "
                                   "look at what is asked and press the button; until then the gallery is unchanged. A stored figure is private to you "
                                   "and is not added to the delivery bundle. Exit code: 0 the link was printed, 1 the figure was not sent, "
                                   "2 not set up (run studio-connect), 3 no connection.")
    p.add_argument("run", help="the run id")
    p.add_argument("figure", help="the image file on this computer")
    p.add_argument("--code", help="a text file with the code that drew the figure (UTF-8)")
    p.add_argument("--params", help="a text file with the parameters of that code (UTF-8)")
    p.add_argument("--caption", help="one line of text under the figure")
    p.set_defaults(func=cmd_publish_figure)
    _no_unknown_options(p)
