# Nothing existing: nothing else in this package writes files on a user's own computer or builds R code; fetch-records brings Nextflow's logs to the platform for the index, not result tables to a person.
"""The commands that run on a user's own computer: `studio-connect` stores the platform's address and the user's own token, and `fetch-results` pulls the
small result tables of one run into a folder on this computer and prints the R code that loads them in RStudio.

Everything comes through `studio_remote` (the MCP tools run_outputs and read_run_file, and list_compute_envs for a hint); the platform decides
what a person may see, and which folders of the site may be read, so nothing of that is judged here. The commands read the platform and write
only to the folder the user chose; they start no program, run no R, and open no database of the platform."""
import asyncio
import os
import re
import sys
import time
from pathlib import Path

from . import cliout, studio_remote
from .jobs import RUN_FILE_MAX_BYTES

POLL_SECONDS = 2.0            # a tool that answers `loading` is asked again after this many seconds
DEADLINE_SECONDS = 120.0      # how long one listing, or one file, may stay `loading`
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_FILES = 200               # files fetched in one run of the command
MAX_DEPTH = 3                 # levels of the results tree that are listed, the first included
TABLE_SUFFIXES = (".tsv", ".csv", ".txt", ".md", ".json")
HTML_SUFFIXES = (".html", ".htm")
LIST_LIMIT = 50               # lines of one kind that are printed one by one

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
        "why_control": "含有控制字元",
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
        "why_control": "has a control character",
    },
}


def _t(key, **kw):
    return STRINGS[studio_remote.lang()][key].format(**kw)


def _say(text):
    cliout.say(text)


def _bad(text):
    cliout.err(text)


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


def r_snippet(files, folder):
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
    lines, used = [_t("paste")], set()
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
    if re.search(r"[\x00-\x1f\x7f]", rel):
        return _t("why_control")
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return _t("why_dots")
    if any(p.startswith(".") for p in parts):
        return _t("why_hidden")
    return None


def _target(base, rel):
    """The place `rel` is written to, or _Refused: inside `base` once resolved, and no link on the way (a link is never followed)."""
    cur = base
    for part in rel.split("/"):
        cur = cur / part
        if cur.is_symlink():
            raise _Refused(_t("why_symlink"))
    target = base.joinpath(*rel.split("/"))
    resolved = target.resolve()
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

    def skip(self, rel, why, problem=False):
        self.skipped.append(rel)
        if len(self.skipped) <= LIST_LIMIT:
            _say(_t("skip", rel=rel, why=why))
        self.problem = self.problem or problem

    def fail(self, rel, reason):
        self.failed.append(rel)
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
    for line in await studio_remote.site_link_lines(session, compute_env):
        _bad(line)


async def _list(session, run_id, report, candidates, path, depth, answer, compute_env):
    """List one level of the results and everything below it down to MAX_DEPTH; fills `candidates` with (path, size) of what is to be read."""
    prefix = path + "/" if path else ""
    for row in answer.get("files") or []:
        name = str(row.get("name"))
        kind = row.get("type")
        if kind == "dir":
            enter = row.get("enter")
            if not enter:
                report.skip(prefix + name, _t("why_nopath"), problem=True)
            elif depth + 1 > MAX_DEPTH:
                report.incomplete = True
                report.skip(enter, _t("why_deep", limit=MAX_DEPTH), problem=True)
            else:
                sub = await _ask(session, "run_outputs", {"run_id": run_id, "path": enter})
                if sub.get("found") is not False and sub.get("state") == "ready":
                    await _list(session, run_id, report, candidates, enter, depth + 1, sub, compute_env)
                else:
                    report.incomplete = report.problem = True
                    _bad(_t("fail_list", rel=enter, reason=_why(sub)))
            continue
        shown = row.get("download") or prefix + name
        ext = Path(name).suffix.lower()
        size = row.get("size")
        if kind != "file":
            report.skip(shown, _t("why_other"))
        elif ext in HTML_SUFFIXES:
            report.skip(shown, _t("why_html"))
        elif ext not in TABLE_SUFFIXES:
            report.skip(shown, _t("why_ext", ext=ext or "-"))
        elif row.get("too_large") or (isinstance(size, int) and size > RUN_FILE_MAX_BYTES):
            report.skip(shown, _t("why_big", size=size, limit=RUN_FILE_MAX_BYTES), problem=True)
        elif not row.get("download"):
            report.skip(shown, _t("why_nopath"), problem=True)
        elif _unsafe(row["download"]):
            report.skip(shown, _t("why_path", why=_unsafe(row["download"])), problem=True)
        elif len(candidates) >= MAX_FILES:
            report.incomplete = True
            report.hidden["limit"] = report.hidden.get("limit", 0) + 1
            report.problem = True
        else:
            candidates.append((row["download"], size if isinstance(size, int) else 0))


def _why(answer):
    """What to say when a tool did not give what was asked: its reason or message, or that the deadline passed."""
    if isinstance(answer, dict) and answer.get("state") == "timeout":
        return _t("fail_wait", seconds=DEADLINE_SECONDS)
    return _reason_of(answer, studio_remote.tr("tool_error"))


def _reason_of(answer, default):
    reason = answer.get("reason") or answer.get("message") if isinstance(answer, dict) else None
    return reason if isinstance(reason, str) and reason else default


async def _read(session, run_id, rel):
    """Read one file page by page. Returns ("ok", bytes), ("binary", None), ("big", size) or ("fail", answer); the pieces are joined only when the
    last one has come, so nothing short of the whole file is ever written."""
    pieces, offset, total, more = [], 0, 0, True
    while more:
        answer = await _ask(session, "read_run_file", {"run_id": run_id, "path": rel, "offset": offset})
        state = answer.get("state")
        if answer.get("found") is False or state not in ("ready", "too_large"):
            return "fail", answer
        if state == "too_large":
            return "big", answer.get("size")
        if answer.get("kind") != "text":
            return "binary", None
        text, nxt = answer.get("text"), answer.get("next_offset")
        total += len(text) if isinstance(text, str) else 0
        if not isinstance(text, str) or total > RUN_FILE_MAX_BYTES or (nxt is not None and (not isinstance(nxt, int) or nxt <= offset)):
            return "fail", {"reason": studio_remote.tr("bad_answer")}
        pieces.append(text)
        more, offset = nxt is not None, nxt
    return "ok", "".join(pieces).encode("utf-8")


def _folder_of(args):
    if args.dir:
        return Path(args.dir).expanduser().absolute()
    name = re.sub(r"[^A-Za-z0-9._-]", "_", args.run).lstrip(".")[:100] or "run"
    return Path.home() / "abf-results" / name


async def _fetch(args):
    run_id, folder = args.run, _folder_of(args)
    report, candidates = _Report(), []
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
        _say(_t("folder_line", path=folder))
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
                report.skip(rel, _t("why_binary"))
            elif kind == "big":
                report.skip(rel, _t("why_big", size=data, limit=RUN_FILE_MAX_BYTES), problem=True)
            elif kind == "fail":
                if studio_remote.is_site_closed(data):
                    await _site_closed(session, report, data, compute_env)
                    report.problem = True
                    report.pending = [r for r, _ in candidates[index:]]
                    break
                report.fail(rel, _why(data))
            else:
                try:
                    over = _write(target, data)
                except OSError as e:
                    report.fail(rel, _t("fail_write", why=e.strerror or "?"))
                    continue
                total += len(data)
                report.got.append(rel)
                _say(_t("got_over" if over else "got", rel=rel, size=len(data)))
    return _finish(report, folder)


def _finish(report, folder):
    if report.hidden.get("limit"):
        _say(_t("more", n=report.hidden["limit"]))
    if len(report.skipped) > LIST_LIMIT:
        _say(_t("more", n=len(report.skipped) - LIST_LIMIT))
    if report.pending:
        names = "、".join(report.pending[:LIST_LIMIT]) if studio_remote.lang() == "zh" else ", ".join(report.pending[:LIST_LIMIT])
        _bad(_t("pending", names=names))
    line = _t("summary", got=len(report.got), skipped=len(report.skipped))
    if report.failed:
        line += _t("summary_fail", failed=len(report.failed))
    _say(line + _t("summary_tail", path=folder))
    if report.incomplete:
        _say(_t("incomplete"))
    if report.failed or report.pending:
        _bad(_t("fail_end"))
    code = r_snippet(report.got, folder)
    if code:
        _say(code)
    cliout.set_data({"folder": str(folder), "fetched": report.got, "skipped": report.skipped, "failed": report.failed})
    return 1 if (report.problem or report.failed or report.incomplete) else 0


def cmd_fetch_results(args):
    try:
        return asyncio.run(_fetch(args))
    except studio_remote.StudioError as e:
        return _fail(e)


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
    _say(studio_remote.tr("server_line", server=server))
    _say(studio_remote.tr("saved", path=path))
    if replaced:
        _say(studio_remote.tr("overwritten"))
    if not studio_remote.permission_bits_trusted():
        _say(studio_remote.tr("cloud_note"))
    cliout.set_data({"server": server, "settings_file": str(path), "replaced": replaced})
    return 0


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
    f.set_defaults(func=cmd_fetch_results)
    _no_unknown_options(f)
