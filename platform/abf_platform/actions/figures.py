# Nothing existing: Seqera's platform and Tower Agent keep no figure a user's own model made, and no gallery that is only the owner's until the owner says yes.
"""publish_figure (slice 1): a run's private figure gallery, filled only by a person's yes.

The user's own LLM proposes figures (an image, the code that drew it, its parameters, a caption). `request_publish_figure` checks every
one of them, writes nothing, and asks the person through the confirmation channels (`_ask` of the action layer: the client's form, the
page /c/<rid>, or the person's own reply in the chat). Only when the person said yes does `write_confirmed` (passed to confirm.approve
by the action layer) write the files, in the same transaction that flips the request to confirmed. No job is queued, no site is reached.

Storage (no table): <figures_root>/<user id>/<run id>/<name>, <name>.code.txt, <name>.params.txt and index.json
  {"version": 1, "figures": {"<name>": {"size", "type", "caption", "code_file", "params_file", "created", "packed": false,
                                         "packed_at": null, "request_id"}}}
Files are 0600 and folders 0700; every file is written to a temporary name and moved into place, index.json last. Uploaded content is never
executed or parsed as HTML: an image is only ever loaded by an <img>, and code, params and caption are plain text.
"""
import base64
import binascii
import hashlib
import json
import os
import re
import secrets
import time
import unicodedata

from .. import common, confirm, jobs, status, store

MAX_FIGURES_PER_CALL = 10
MAX_PER_RUN = 30
MAX_BUNDLE_BYTES = 5 * 1024 * 1024
MAX_PENDING_BYTES = 20 * 1024 * 1024        # the images one person may have waiting for a yes at the same time (the rows hold them until then)
MAX_CAPTION_CHARS = 200
MAX_CODE_BYTES = 100 * 1024
MAX_PARAMS_BYTES = 10 * 1024
CODE_PREVIEW_LINES = 20

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_TYPES = {".png": "png", ".svg": "svg", ".jpg": "jpg", ".jpeg": "jpg"}
_RESERVED = ("index.json",)
_RESERVED_SUFFIXES = (".code.txt", ".params.txt")
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_SVG_BANNED = ("<script", "<foreignobject", "<!doctype", "<!entity", "javascript:", "<iframe", "<embed", "<object")
_SVG_EVENT = re.compile(r"[\s\"'/]on[a-z]+\s*=")
_SVG_EXTERNAL = re.compile(r"(?:href|src)\s*=\s*[\"']?\s*(?:https?:)?//|url\(\s*[\"']?\s*(?:https?:)?//")
NOT_YOURS = "找不到這個 run (run not found)"      # the same words for a run that is not yours and one that is not there

SIZE_MESSAGE = "這次送入的圖合計超過 5 MB 上限（目前 %s MB），請分次或縮小圖檔 (the figures together exceed the 5 MB limit; send fewer per call or smaller files)"
PENDING_MESSAGE = ("等待確認的圖合計已達每人 20 MB 上限（目前 %s MB，這次 %s MB）；請先到確認頁處理、或等 10 分鐘逾時之後再送 "
                   "(the figures waiting for a yes are over the limit of 20 MB per person; answer or wait for the open requests to expire, then send again)")
FULL_MESSAGE = "這個分析的圖庫已滿（最多 %d 張）；請改用既有的檔名覆蓋，或請本人先到網頁刪除不要的圖 (the gallery of this run is full: at most %d figures; reuse a name to replace one)"


class FigureRefused(Exception):
    """One figure, or the whole list, cannot be accepted; the message says which and what to do."""


def _mb(n):
    return "%.1f" % (n / (1024 * 1024))


# ---- checks (before any request exists, and again when the person says yes) -----------------------------------------------------

def check_name(name):
    """The type of a figure file name ('png', 'svg' or 'jpg'), or FigureRefused."""
    if not isinstance(name, str) or not name:
        raise FigureRefused("檔名是空的或不是文字 (the file name is empty or not text)")
    if not _NAME.fullmatch(name) or ".." in name:
        raise FigureRefused("檔名「%s」不合規定：只能用英數字、點、底線與連字號，開頭須是英數字，最長 80 字元，不可有空白、斜線或「..」 "
                            "(the file name is not allowed: letters, digits, dot, underscore and hyphen only, at most 80 characters)" % name[:80])
    low = name.lower()
    if low in _RESERVED or low.endswith(_RESERVED_SUFFIXES):
        raise FigureRefused("檔名「%s」是平台保留的名稱 (that file name is reserved)" % name)
    ext = os.path.splitext(low)[1]
    if ext not in _TYPES:
        raise FigureRefused("檔名「%s」的副檔名不收：只收 png、svg、jpg、jpeg (only png, svg, jpg and jpeg files are accepted)" % name)
    return _TYPES[ext]


def _text_problem(value, label, limit, unit):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise FigureRefused("%s 必須是文字 (%s must be text)" % (label, label))
    if chr(0) in value:
        raise FigureRefused("%s 含有 NUL 字元，不是純文字 (%s contains a NUL character)" % (label, label))
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise FigureRefused("%s 含有不成對的代理字元，不是正確的文字 (%s contains a lone surrogate, which is not valid text)" % (label, label))
    if label == "caption" and any(unicodedata.category(ch) in ("Cc", "Zl", "Zp") for ch in value):
        raise FigureRefused("caption 不可含換行或控制字元（說明只能是單行文字）(the caption must be one line of text: no line break or control character)")
    size = len(value) if unit == "chars" else len(encoded)
    if size > limit:
        raise FigureRefused("%s 超過上限（%d %s）(%s is over the limit of %d %s)" % (
            label, limit, "字元" if unit == "chars" else "位元組", label, limit, "characters" if unit == "chars" else "bytes"))
    return value


def check_content(name, kind, data):
    """The bytes must be what the extension says; an SVG must hold nothing the deny list names. Refuses, never rewrites."""
    if kind == "png" and not data.startswith(_PNG):
        raise FigureRefused("「%s」的內容不是 PNG 圖檔（檔頭與副檔名不符）(the content is not a PNG file)" % name)
    if kind == "jpg" and not data.startswith(_JPEG):
        raise FigureRefused("「%s」的內容不是 JPEG 圖檔（檔頭與副檔名不符）(the content is not a JPEG file)" % name)
    if kind == "svg":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise FigureRefused("「%s」不是 UTF-8 的 SVG 文字 (the SVG is not valid UTF-8)" % name)
        low = text.lower()
        for bad in _SVG_BANNED:
            if bad in low:
                raise FigureRefused("「%s」含有不收的 SVG 內容「%s」（腳本、外部實體等會被拒絕，平台不改寫）(the SVG holds content that is refused: %s)" % (name, bad, bad))
        if _SVG_EVENT.search(low):
            raise FigureRefused("「%s」含有事件屬性（如 onload=），SVG 被拒絕 (the SVG holds an event attribute)" % name)
        if _SVG_EXTERNAL.search(low):
            raise FigureRefused("「%s」指向外部網址的資源，SVG 被拒絕 (the SVG points at an external address)" % name)


def _build_figures(figures):
    """The list of figure dicts of the bundle, in the order given; FigureRefused naming the figure that does not pass."""
    if not isinstance(figures, list) or not figures:
        raise FigureRefused("figures 必須是 1 至 %d 張圖的清單 (figures must be a list of 1 to %d figures)" % (MAX_FIGURES_PER_CALL, MAX_FIGURES_PER_CALL))
    if len(figures) > MAX_FIGURES_PER_CALL:
        raise FigureRefused("一次最多送 %d 張圖（這次 %d 張），請分次送 (at most %d figures per call; send fewer)" % (MAX_FIGURES_PER_CALL, len(figures), MAX_FIGURES_PER_CALL))
    estimate = sum(len(f["content_base64"]) for f in figures if isinstance(f, dict) and isinstance(f.get("content_base64"), str))
    if estimate > MAX_BUNDLE_BYTES:
        raise FigureRefused(SIZE_MESSAGE % _mb(estimate))
    out, seen = [], set()
    for i, f in enumerate(figures, 1):
        label = "第 %d 張" % i
        try:
            if not isinstance(f, dict):
                raise FigureRefused("每張圖要是含 filename 與 content_base64 的物件 (each figure must be an object with filename and content_base64)")
            name = f.get("filename")
            label = "第 %d 張「%s」" % (i, name if isinstance(name, str) else "")
            kind = check_name(name)
            if name.lower() in seen:
                raise FigureRefused("同一批內有重複的檔名 (the same file name twice in one call)")
            seen.add(name.lower())
            b64 = f.get("content_base64")
            if not isinstance(b64, str) or not b64:
                raise FigureRefused("content_base64 是空的或不是文字 (content_base64 is empty or not text)")
            try:
                data = base64.b64decode(b64, validate=True)
            except (binascii.Error, ValueError):
                raise FigureRefused("content_base64 不是正確的 base64 (content_base64 is not valid base64)")
            if not data:
                raise FigureRefused("圖檔內容是空的 (the figure is empty)")
            check_content(name, kind, data)
            caption = _text_problem(f.get("caption"), "caption", MAX_CAPTION_CHARS, "chars")
            code = _text_problem(f.get("code"), "code", MAX_CODE_BYTES, "bytes")
            params = _text_problem(f.get("params"), "params", MAX_PARAMS_BYTES, "bytes")
        except FigureRefused as e:
            raise FigureRefused("%s未送出：%s" % (label, e))
        out.append({"name": name, "type": kind, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "caption": caption,
                    "code": code, "params": params, "content_base64": b64})
    return out


# ---- the gallery on disk --------------------------------------------------------------------------------------------------------

def _user_key(user_id):
    return str(int(user_id)) if user_id is not None else "local"


def run_folder(platform_path, user_id, run_id):
    """<figures_root>/<user>/<run id>, checked to lie inside figures_root; FigureRefused when the run id cannot be a folder name."""
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id) or ".." in run_id:
        raise FigureRefused(NOT_YOURS)
    root = os.path.realpath(str(store.figures_root(platform_path)))
    path = os.path.realpath(os.path.join(root, _user_key(user_id), run_id))
    if not path.startswith(root + os.sep):
        raise FigureRefused(NOT_YOURS)
    return path


def read_index(folder):
    """(figures dict, problem): the index of a gallery; a missing one is an empty gallery, a damaged one too, with the problem said."""
    path = os.path.join(folder, "index.json")
    try:
        with open(path, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
        figures = data["figures"]
        if data.get("version") != 1 or not isinstance(figures, dict) or not all(isinstance(v, dict) for v in figures.values()):
            raise ValueError("shape")
        return figures, None
    except FileNotFoundError:
        return {}, None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}, "圖庫的索引檔損毀，已當作空的圖庫；請聯絡平台管理者 (the gallery index is damaged and is read as an empty gallery; tell the platform administrator)"


def _owned_run(index_path, platform_path, run_id, caller):
    """The run's view when it is the caller's own (any state), else None: the check read_run_file makes."""
    from . import platform_path_for
    view = status.get_run(index_path, run_id, status.now()) if isinstance(run_id, str) and index_path is not None else None
    plat = platform_path_for(index_path, platform_path)
    if view is None or (caller is not None and view["name"] not in jobs.owned_run_names(plat, caller.user_id)):
        return None
    return view


def list_figures(index_path, platform_path, run_id, *, caller=None, packed_only=False):
    """Read only: the figures of the caller's own run, {found, figures: [{name, ...index fields}], error?}. A run that is not the caller's,
    or is not there, gives {found: False, message} in the same words. Nothing is written."""
    from . import platform_path_for
    plat = platform_path_for(index_path, platform_path)
    if _owned_run(index_path, platform_path, run_id, caller) is None:
        return {"found": False, "message": NOT_YOURS}
    try:
        figures, problem = read_index(run_folder(plat, caller.user_id if caller else None, run_id))
    except FigureRefused:
        return {"found": False, "message": NOT_YOURS}
    rows = [dict(v, name=k) for k, v in sorted(figures.items()) if not packed_only or v.get("packed") is True]
    out = {"found": True, "figures": rows}
    if problem:
        out["error"] = problem
    return out


# ---- the request ----------------------------------------------------------------------------------------------------------------

def _screen(run_name, figures, existing, lang="zh"):
    """The text the person reads before pressing Send, in Chinese (the stored screen) or in English (the page in English)."""
    en = lang == "en"
    lines = ["== Confirm adding figures ==" if en else "== 存入圖庫確認 (confirm adding figures) ==", ("Run: %s" if en else "分析：%s") % run_name,
             ("Figures: %d" if en else "圖片：%d 張") % len(figures), ""]
    for i, f in enumerate(figures, 1):
        lines.append("[%d] %s" % (i, f["name"]))
        lines.append(("Type: %s   Size: %d bytes" if en else "類型：%s　大小：%d 位元組") % (f["type"], f["size"]))
        lines.append(("SHA-256 (first 12): %s" if en else "SHA-256（前 12 碼）：%s") % f["sha256"][:12])
        if f["name"] in existing:
            lines.append("Replaces the figure of the same name" if en else "覆蓋既有同名圖 (replaces the figure of the same name)")
        lines.append(("Caption: %s" if en else "說明：%s") % (f["caption"] or "-"))
        code_lines = f["code"].splitlines()
        if code_lines:
            lines.append(("Code (%d lines, the first %d shown):" if en else "程式碼（共 %d 行，顯示前 %d 行）：") % (len(code_lines), CODE_PREVIEW_LINES))
            lines.extend("  " + ln for ln in code_lines[:CODE_PREVIEW_LINES])
        else:
            lines.append("Code: none" if en else "程式碼：無")
        if f["params"]:
            lines.append("Parameters:" if en else "參數：")
            lines.extend("  " + ln for ln in f["params"].splitlines())
        else:
            lines.append("Parameters: none" if en else "參數：無")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def screen_for_page(bundle, replaces, lang):
    """The screen text of a stored request in `lang`, for the confirmation page."""
    return _screen(bundle["run_name"], bundle["figures"], set(replaces or ()), lang)


async def request_publish_figure(platform_path, *, run_id, figures, caller=None, person=None, clock=time.time, remote=False, index_path=None,
                                 request_id=None, user_confirmed=False):
    """Propose figures for the gallery of the caller's own run. Writes nothing: a pending request (kind publish_figure) is made for the
    whole list, and the person is asked. Returns {state: pending|ok|refused, request_id, url, count, reason?, message}. Anything wrong with
    the run, a name or the content refuses the whole call before a request exists."""
    from . import _ask, _caller_id, platform_path_for
    plat = platform_path_for(index_path, platform_path)

    def refused(reason):
        return {"ok": False, "sent": False, "state": "refused", "request_id": None, "url": None, "count": 0, "reason": reason, "message": reason}
    view = _owned_run(index_path, platform_path, run_id, caller)
    if view is None:
        return refused("找不到 run「%s」。請用 list_runs 查自己的 run 編號後再送 (run not found: %s; use list_runs to see your own run ids)" % (str(run_id)[:80], str(run_id)[:80]))
    confirm.drop_figure_content(plat, _caller_id(caller), clock)       # the next request of the same person drops the bytes of what is over (void, expired)
    try:
        built = _build_figures(figures)
        folder = run_folder(plat, _caller_id(caller), run_id)
        existing, problem = read_index(folder)
        names = {f["name"] for f in built}
        lower = {k.lower(): k for k in existing}
        for n in names:
            if n.lower() in lower and lower[n.lower()] != n:
                raise FigureRefused("「%s」與圖庫裡的「%s」只差大小寫，請用相同的檔名 (the name differs from \"%s\" only in case)" % (n, lower[n.lower()], lower[n.lower()]))
        if len(set(existing) | names) > MAX_PER_RUN:
            raise FigureRefused(FULL_MESSAGE % (MAX_PER_RUN, MAX_PER_RUN))
        replaces = sorted(names & set(existing))
        stored = confirm.facts(plat, request_id) if isinstance(request_id, str) and user_confirmed else None
        if stored and stored.get("what") == "publish_figure":
            replaces = stored["replaces"]          # a repeated call that carries the yes: what the screen said, not what the gallery says now (it changed by that very yes)
        bundle = {"run_name": view["name"], "run_id": run_id, "figures": built, "replaces": replaces}
        size = len(json.dumps(bundle).encode())
        if size > MAX_BUNDLE_BYTES:
            raise FigureRefused(SIZE_MESSAGE % _mb(size))
        if not (isinstance(request_id, str) and user_confirmed):        # a call that only relays a yes makes no new request
            waiting = confirm.pending_figure_bytes(plat, _caller_id(caller), clock, except_sha=common.bundle_sha256(bundle))
            if waiting + size > MAX_PENDING_BYTES:
                raise FigureRefused(PENDING_MESSAGE % (_mb(waiting), _mb(size)))
    except FigureRefused as e:
        return refused(str(e))
    text = _screen(view["name"], built, existing)

    def done(rid):
        return {"ok": True, "sent": True, "state": "ok", "request_id": rid, "url": None, "count": len(built),
                "message": "已存入圖庫 %d 張 (added %d figures to the gallery)" % (len(built), len(built))}
    got = await _ask(plat, "publish_figure", None, bundle, text, "存入圖庫", caller, person, clock, remote, tool="publish_figure",
                     request_id=request_id, user_confirmed=user_confirmed, done=done)
    if got.get("state") == "ok":
        return got
    if got.get("state") == "pending":
        url = got["confirmation_url"]
        rid = got["id"]
        out = {"ok": True, "sent": False, "state": "pending", "request_id": rid, "url": url, "count": len(built), "summary": text,
               "message": "還沒存入 (nothing is written yet)。請本人打開這個網址、用自己的帳號登入、看過內容後按「送出」：%s ——按了之後圖才會寫入圖庫，"
                          "不必再呼叫一次。或者，把內容給本人看，本人在聊天裡親口回覆同意之後，用同樣的參數加上 request_id=%s 與 user_confirmed=true 再呼叫一次；"
                          "在本人回覆之前不可自己填 true。 (open the address, log in as yourself and press 送出; or, once the person has answered yes in the "
                          "chat, call publish_figure again with the same arguments plus request_id=%s and user_confirmed=true; never set it true before they answer)"
                          % (url, rid, rid)}
        if got.get("message", "").startswith("⚠"):
            out["message"] = got["message"].split("還沒送出")[0] + out["message"]
        if problem:
            out["warning"] = problem
        return out
    return refused(got.get("message") or "未送出 (not sent)")


# ---- the write (called by confirm.approve, after the person's yes) ----------------------------------------------------------------

def _chmod(path, mode):
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _stage(folder, final_name, data, tag):
    temp = os.path.join(folder, ".tmp-%s-%s" % (tag, secrets.token_hex(4)))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return temp, os.path.join(folder, final_name)


def write_confirmed(platform_path, caller_user_id, bundle, rid, now):
    """Write the figures of a confirmed request. Everything is checked once more (names, bytes, the number in the gallery); JobRefused when
    it no longer passes, any other error when the disk says no. On any failure nothing stays behind and every file that was touched,
    index.json included, has the bytes it had before. The names are matched without regard to case, and what would be replaced must be what the
    screen said (bundle["replaces"]); otherwise nothing is written."""
    try:
        folder = run_folder(platform_path, caller_user_id, bundle["run_id"])
        figures = bundle["figures"]
        built = []
        for f in figures:
            kind = check_name(f["name"])
            data = base64.b64decode(f["content_base64"], validate=True)
            if kind != f["type"] or hashlib.sha256(data).hexdigest() != f["sha256"]:
                raise FigureRefused("圖的內容與申請時不同")
            check_content(f["name"], kind, data)
            built.append((f, data))
    except (FigureRefused, KeyError, TypeError, ValueError, binascii.Error) as e:
        raise jobs.JobRefused("核准時重新檢查未通過，沒有寫入任何圖：%s (the check at the time of the yes failed; nothing was written)" % e)
    existing, problem = read_index(folder)
    if len(set(existing) | {f["name"] for f, _ in built}) > MAX_PER_RUN:
        raise jobs.JobRefused(FULL_MESSAGE % (MAX_PER_RUN, MAX_PER_RUN))
    lower = {k.lower(): k for k in existing}
    replacing = set()
    for f, _ in built:
        hit = lower.get(f["name"].lower())
        if hit is not None and hit != f["name"]:
            raise jobs.JobRefused("「%s」與圖庫裡的「%s」只差大小寫，沒有寫入任何圖，請用相同的檔名重新提出 (the name differs from \"%s\" only in case; nothing was written)" % (f["name"], hit, hit))
        if hit is not None:
            replacing.add(hit)
    if sorted(replacing) != sorted(bundle.get("replaces", [])):
        raise jobs.JobRefused("圖庫在申請送出後有變動，會被取代的圖與確認畫面上寫的不同，沒有寫入任何圖，請重新提出 "
                              "(the gallery changed after the request was made: what would be replaced is not what the screen said; nothing was written)")
    for sub in (os.path.dirname(folder), folder):
        os.makedirs(sub, mode=0o700, exist_ok=True)
        _chmod(sub, 0o700)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    staged, replaced, backups = [], [], {}
    index = {k: dict(v) for k, v in existing.items()}
    try:
        for f, data in built:
            name = f["name"]
            staged.append(_stage(folder, name, data, rid[:8]))
            entry = {"size": len(data), "type": f["type"], "caption": f["caption"], "code_file": None, "params_file": None, "created": stamp,
                     "packed": False, "packed_at": None, "request_id": rid}
            for field, key, suffix in (("code", "code_file", ".code.txt"), ("params", "params_file", ".params.txt")):
                if f[field]:
                    staged.append(_stage(folder, name + suffix, f[field].encode("utf-8"), rid[:8]))
                    entry[key] = name + suffix
            index[name] = entry
        staged.append(_stage(folder, "index.json", json.dumps({"version": 1, "figures": index}, indent=1, sort_keys=True).encode("utf-8"), rid[:8]))
        stale = []
        for f, _ in built:
            old = existing.get(f["name"], {})
            for key, suffix, field in (("code_file", ".code.txt", "code"), ("params_file", ".params.txt", "params")):
                if old.get(key) and not f[field]:
                    stale.append(os.path.join(folder, f["name"] + suffix))
        for path in [final for _, final in staged] + stale:        # what is there now, to put back if any step fails
            try:
                with open(path, "rb") as old_file:
                    backups[path] = old_file.read()
            except FileNotFoundError:
                backups[path] = None
        for temp, final in staged:
            os.replace(temp, final)
            _chmod(final, 0o600)
            replaced.append(temp)
        for path in stale:
            try:
                os.unlink(path)
            except OSError:
                pass
    except BaseException:
        for temp, _ in staged:
            if temp not in replaced:
                try:
                    os.unlink(temp)
                except OSError:
                    pass
        for path, old in backups.items():       # every file the write touched goes back to the bytes it had (or is removed when it was not there)
            try:
                if old is None:
                    if os.path.exists(path):
                        os.unlink(path)
                else:
                    with open(path, "wb") as restored:
                        restored.write(old)
                    _chmod(path, 0o600)
            except OSError:
                pass
        raise
