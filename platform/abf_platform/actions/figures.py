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
import contextlib
import hashlib
import json
import os
import re
import secrets
import time
import unicodedata

try:
    import fcntl
except ImportError:      # not a Unix: the platform runs on Linux; there is no cross-process lock to take elsewhere
    fcntl = None

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


_UNSEEN = ("Cc", "Cf", "Cs", "Zl", "Zp")          # control, format (bidi, zero width), surrogate, line and paragraph separators
# Default_Ignorable_Code_Point characters that are not category Cf (those are refused outright) and still draw nothing, plus the blank braille cell
# U+2800 (category So): Hangul fillers U+115F U+1160 U+3164 U+FFA0, Khmer inherent vowels U+17B4 U+17B5, U+034F, Mongolian free variation selectors
# U+180B-180D U+180F, variation selectors U+FE00-FE0F and U+E0100-E01EF. A person sees nothing where they are, so they count as blank (ruling N7).
_FILLER = "͏ᅟᅠ឴឵᠋-᠍᠏⠀ㅤ︀-️ﾠ\U000e0100-\U000e01ef"
_BLANK = r"(?:[^\S\r\n]|[" + _FILLER + r"])"
_LONG_SPACE = re.compile(_BLANK + "{9,}")
_BLANK_LINE = re.compile(_BLANK + "*")
MAX_BLANK_LINES = 2


def _safe(value, limit=80):
    """A piece of what the caller sent, fit to be echoed in a refusal: no control, format or surrogate character, at most `limit` characters (ruling N2)."""
    return "".join(ch for ch in str(value) if unicodedata.category(ch) not in _UNSEEN)[:limit]


def _lone_surrogate(value):
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return True
    return False


def _squeeze(text):
    """For display only (ruling N1): a run of more than 8 blank characters is shown as 8, so padding cannot push a forged line to the start of a
    visual line; more than MAX_BLANK_LINES blank lines in a row (a line of spaces or filler counts as blank) are shown as 2 (rulings N1, N7, N8).
    What is stored is never passed through here."""
    out, blanks = [], 0
    for line in _LONG_SPACE.sub(" " * 8, text).split("\n"):
        if _BLANK_LINE.fullmatch(line):
            blanks += 1
            if blanks > MAX_BLANK_LINES:
                continue
            line = ""
        else:
            blanks = 0
        out.append(line)
    return "\n".join(out)


# ---- checks (before any request exists, and again when the person says yes) -----------------------------------------------------

def check_name(name):
    """The type of a figure file name ('png', 'svg' or 'jpg'), or FigureRefused."""
    if not isinstance(name, str) or not name:
        raise FigureRefused("檔名是空的或不是文字 (the file name is empty or not text)")
    if not _NAME.fullmatch(name) or ".." in name:
        raise FigureRefused("檔名「%s」不合規定：只能用英數字、點、底線與連字號，開頭須是英數字，最長 80 字元，不可有空白、斜線或「..」 "
                            "(the file name is not allowed: letters, digits, dot, underscore and hyphen only, at most 80 characters)" % _safe(name))
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
    if label == "caption" and any(unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp") for ch in value):
        raise FigureRefused("caption 不可含換行、控制字元或不可見的格式字元（說明只能是單行文字）(the caption must be one line of text: no line break, control or invisible format character)")
    if label != "caption" and any(unicodedata.category(ch) in ("Cn", "Co") for ch in value):
        raise FigureRefused("%s 含有未指派或私用區的字元（看不見的填充）(%s contains an unassigned or private-use character)" % (label, label))
    if label != "caption" and any((unicodedata.category(ch) == "Cc" and ch not in "\n\t") or unicodedata.category(ch) in ("Cf", "Zl", "Zp") for ch in value.replace("\r\n", "\n")):       # a Windows file ends its lines with CR LF; a CR on its own moves the cursor and is refused
        raise FigureRefused("%s 含有控制字元或不可見的格式字元（只有換行與 Tab 可以）(%s contains a control or invisible format character; only a line break and a tab are allowed)" % (label, label))
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
            label = "第 %d 張「%s」" % (i, _safe(name) if isinstance(name, str) else "")
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
    return _squeeze("\n".join(lines).rstrip() + "\n")


def screen_for_page(bundle, replaces, lang):
    """The screen text of a stored request in `lang`, for the confirmation page (a gallery_change request, which has an `action`, has its own)."""
    if bundle.get("action") in ("pack", "delete"):
        return gallery_screen(bundle, lang)
    return _screen(bundle["run_name"], bundle["figures"], set(replaces or ()), lang)


def _identity(entry):
    """Which figure an index entry is: the request that wrote it (its creation time for an entry that has none)."""
    return entry.get("request_id") or entry.get("created") or ""


def _own_request(platform_path, request_id, caller_id, kind="publish_figure"):
    """The stored bundle of the caller's own publish_figure request, else None: somebody else's request is not read at all (ruling N6)."""
    if not isinstance(request_id, str) or not request_id or len(request_id) > 64:
        return None
    con = store.open_readonly(platform_path)
    if con is None:
        return None
    try:
        row = con.execute("SELECT bundle_json FROM confirmations WHERE id = ? AND kind = ? AND caller_user_id IS ? "
                          "AND bundle_json IS NOT NULL AND channel IS NOT 'TERMINAL'", (request_id, kind, caller_id)).fetchone()
    finally:
        con.close()
    try:
        bundle = json.loads(row["bundle_json"]) if row is not None else None
    except (TypeError, ValueError):
        return None
    return bundle if isinstance(bundle, dict) else None


async def request_publish_figure(platform_path, *, run_id, figures, caller=None, person=None, clock=time.time, remote=False, index_path=None,
                                 request_id=None, user_confirmed=False):
    """Propose figures for the gallery of the caller's own run. Writes nothing: a pending request (kind publish_figure) is made for the
    whole list, and the person is asked. Returns {state: pending|ok|refused, request_id, url, count, reason?, message}. Anything wrong with
    the run, a name or the content refuses the whole call before a request exists."""
    from . import _ask, _caller_id, platform_path_for
    plat = platform_path_for(index_path, platform_path)

    def refused(reason):
        return {"ok": False, "sent": False, "state": "refused", "request_id": None, "url": None, "count": 0, "reason": reason, "message": reason}
    if (isinstance(run_id, str) and _lone_surrogate(run_id)) or (isinstance(figures, list) and any(
            isinstance(f, dict) and isinstance(f.get("filename"), str) and _lone_surrogate(f["filename"]) for f in figures)):
        return refused("run 編號或檔名含有不成對的代理字元，不是正確的文字，未送出 (the run id or a file name contains a lone surrogate, which is not valid text; nothing was sent)")
    view = _owned_run(index_path, platform_path, run_id, caller)
    if view is None:
        return refused("找不到 run「%s」。請用 list_runs 查自己的 run 編號後再送 (run not found: %s; use list_runs to see your own run ids)" % (_safe(run_id), _safe(run_id)))
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
        ids = {n: _identity(existing[n]) for n in replaces}
        stored = _own_request(plat, request_id, _caller_id(caller)) if isinstance(request_id, str) and user_confirmed is True else None
        if stored:
            replaces = stored.get("replaces", replaces)          # a repeated call that carries the yes: what the screen said, not what the gallery says now (it changed by that very yes)
            ids = stored.get("replaces_ids")
        bundle = {"run_name": view["name"], "run_id": run_id, "figures": built, "replaces": replaces}
        if ids is not None:
            bundle["replaces_ids"] = ids          # which figure each name was when the screen was made (ruling N4)
        size = len(json.dumps(bundle).encode())
        if size > MAX_BUNDLE_BYTES:
            raise FigureRefused(SIZE_MESSAGE % _mb(size))
        if not (isinstance(request_id, str) and user_confirmed is True):        # a call that only relays a yes makes no new request
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


class GalleryBusy(OSError):
    """The gallery lock could not be taken. An OSError, so the confirmed write ends in slice 1's write-failed path."""


BUSY_MESSAGE = "圖庫目前無法變更，請稍後再試。沒有變更任何內容 (The gallery cannot be changed right now, please try again later. Nothing was changed.)"


@contextlib.contextmanager
def gallery_lock(folder):
    """One lock for each gallery folder, held from the read of index.json to its replace (ruling G1): pack, delete and the confirmed write all
    read the index and replace it whole, so two of them at once lose an update. It is a flock on the folder itself, taken on a handle of its own
    each time, so it holds between processes and between the web server's workers alike; there is no lock file, because a gallery folder holds
    only its figures and index.json. A folder that is not there is not locked: there is no index to lose. A lock that cannot be taken raises GalleryBusy."""
    key = os.path.realpath(folder)
    fd = None
    if fcntl is not None and os.path.isdir(key):
        try:
            fd = os.open(key, os.O_RDONLY)
            fcntl.flock(fd, fcntl.LOCK_EX)
        except OSError as e:        # never go on without the lock (ruling K3): the operation is refused and changes nothing
            if fd is not None:
                os.close(fd)
            raise GalleryBusy(e.errno or 0, "the gallery lock could not be taken") from None
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)        # closing releases the flock


def _stage(folder, final_name, data, tag):
    temp = os.path.join(folder, ".tmp-%s-%s" % (tag, secrets.token_hex(4)))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
    except BaseException:       # a write that fails half way leaves no temporary file (ruling G4)
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    return temp, os.path.join(folder, final_name)


INCONSISTENT_MESSAGE = ("寫入失敗，而且舊檔也沒能全部還原：這個圖庫可能處於不一致的狀態，請回報給平台管理者 (the write failed and the old files "
                        "could not all be put back: the gallery may be inconsistent; tell the platform administrator)")


def _restore(folder, path, old):
    """Put one file back to the bytes it had (`old` None: it was not there): through a temporary name and a replace, like every write here."""
    if old is None:
        if os.path.exists(path):
            os.unlink(path)
        return
    temp, final = _stage(folder, os.path.basename(path), old, "undo")
    try:
        os.replace(temp, final)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    _chmod(final, 0o600)


def _sweep_tmp(folder):
    """Remove the .tmp-* files a killed write left in the gallery folder. Called with the gallery lock held, before a write: no other writer is
    staging then, because every writer stages inside the lock (ruling N3)."""
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for leaf in names:
        if leaf.startswith(".tmp-"):
            try:
                os.unlink(os.path.join(folder, leaf))
            except OSError:
                pass


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
    for sub in (os.path.dirname(folder), folder):
        os.makedirs(sub, mode=0o700, exist_ok=True)
        _chmod(sub, 0o700)
    with gallery_lock(folder):
        _commit(folder, built, bundle, rid, now)


def _commit(folder, built, bundle, rid, now):
    """The part of write_confirmed that reads and replaces index.json; it runs with the gallery lock held."""
    _sweep_tmp(folder)
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
    ids = bundle.get("replaces_ids")
    if ids is not None and any(ids.get(n) != _identity(existing[n]) for n in replacing):
        raise jobs.JobRefused("要取代的圖在申請送出後已被換過，與確認畫面上寫的不是同一張，沒有寫入任何圖，請重新提出 "
                              "(a figure this request would replace is no longer the one the screen showed; nothing was written)")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    staged, replaced, backups, touched = [], [], {}, []
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
            touched.append(final)
            _chmod(final, 0o600)
            replaced.append(temp)
        for path in stale:
            try:
                os.unlink(path)
                touched.append(path)
            except OSError:
                pass
    except BaseException:
        for temp, _ in staged:
            if temp not in replaced:
                try:
                    os.unlink(temp)
                except OSError:
                    pass
        stuck = False
        for path in touched:       # every file the write changed goes back to the bytes it had (or is removed when it was not there)
            try:
                _restore(folder, path, backups.get(path))
            except OSError:
                stuck = True
        if stuck:       # the old bytes could not all be put back: never say that nothing was stored (ruling N3)
            raise jobs.JobRefused(INCONSISTENT_MESSAGE) from None
        raise


# ---- the gallery page: read, pack and delete (mcp-publish-figure-gallery, slice 2) ---------------------------------------------------
# Web only, owner only. Nothing here is an MCP tool: the person's own press of a button on the finished page (login cookie, CSRF token and same
# origin checked by the route) is the confirmation. Only <figures_root>/<user>/<run id>/ is ever written; no job is queued, no site is reached.

MIME = {"png": "image/png", "svg": "image/svg+xml", "jpg": "image/jpeg"}
NAME_LIMIT = 80
NAMES_LIMIT = 100


def _refused(reason, message, found=True, **more):
    return dict(more, ok=False, found=found, reason=reason, message=message)


def _own_folder(index_path, platform_path, run_id, caller):
    """(folder, plat) of the caller's own run, or (None, plat) when it is not theirs or not there: one answer for both."""
    from . import platform_path_for
    plat = platform_path_for(index_path, platform_path)
    if caller is None or _owned_run(index_path, platform_path, run_id, caller) is None:
        return None, plat
    try:
        return run_folder(plat, caller.user_id, run_id), plat
    except FigureRefused:
        return None, plat


def _write_index(folder, figures):
    """index.json replaced whole through a temporary name (readers see the old file or the new one); OSError when the disk says no, and then
    the old file stays and no temporary file is left."""
    data = json.dumps({"version": 1, "figures": figures}, indent=1, sort_keys=True).encode("utf-8")
    temp, final = _stage(folder, "index.json", data, "idx")
    try:
        os.replace(temp, final)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    _chmod(final, 0o600)


def _text_of(folder, entry, key):
    """The stored text of a figure's code or parameters, or None when it has none (or the file is gone)."""
    name = entry.get(key)
    if not isinstance(name, str) or not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    try:
        with open(os.path.join(folder, name), "rb") as f:
            return f.read().decode("utf-8", "replace")
    except OSError:
        return None


def pending_request(platform_path, user_id, run_id, clock=time.time):
    """The id of the caller's own publish_figure request for this run that still waits for a yes, else None. Reads only."""
    con = store.open_readonly(platform_path)
    if con is None:
        return None
    try:
        rows = con.execute("SELECT id, bundle_json FROM confirmations WHERE kind = 'publish_figure' AND state = 'pending' AND caller_user_id IS ? "
                           "AND expires_at > ? AND bundle_json IS NOT NULL AND forgotten_at IS NULL ORDER BY created_at DESC",
                           (user_id, clock())).fetchall()
    except Exception:
        return None
    finally:
        con.close()
    for r in rows:
        try:
            if json.loads(r["bundle_json"]).get("run_id") == run_id:
                return r["id"]
        except (TypeError, ValueError, AttributeError):
            continue
    return None


def gallery_view(index_path, platform_path, run_id, *, caller, clock=time.time):
    """Read only: what the finished page shows of the gallery of the caller's own run:
    {found, figures: [{name, size, type, caption, created, packed, code, params}] newest first, error?, pending: request id or None}."""
    folder, plat = _own_folder(index_path, platform_path, run_id, caller)
    if folder is None:
        return {"found": False, "message": NOT_YOURS}
    figures, problem = read_index(folder)
    rows = []
    for name, v in figures.items():
        rows.append({"name": name, "size": v.get("size"), "type": v.get("type"), "caption": v.get("caption") or "", "created": v.get("created") or "",
                     "packed": v.get("packed") is True, "code": _text_of(folder, v, "code_file"), "params": _text_of(folder, v, "params_file")})
    rows.sort(key=lambda r: r["name"])
    rows.sort(key=lambda r: r["created"], reverse=True)
    out = {"found": True, "figures": rows, "pending": pending_request(plat, caller.user_id, run_id, clock)}
    if problem:
        out["error"] = problem
    return out


PARTS = {"code": ("code_file", ".code.txt"), "params": ("params_file", ".params.txt")}


def read_figure(index_path, platform_path, run_id, name, *, caller, part=None):
    """The bytes of one figure of the caller's own run: {found: True, name, type, mime, data}. Only a name that index.json holds is read (the
    name is compared with the index, never joined into a path by what the caller wrote); a run that is not the caller's, a name that is not
    there and a file that is gone all give {found: False}. With part="code" or "params" (ruling G5) the answer is the stored text of that part as
    plain text ({found, name: "<name>.code.txt", type: "text", mime, data}); a figure without that part, and any other part, give {found: False}."""
    folder, _ = _own_folder(index_path, platform_path, run_id, caller)
    if folder is None or not isinstance(name, str):
        return {"found": False, "message": NOT_YOURS}
    figures, _problem = read_index(folder)
    if name not in figures:
        return {"found": False, "message": NOT_YOURS}
    if part:
        if part not in PARTS:
            return {"found": False, "message": NOT_YOURS}
        key, suffix = PARTS[part]
        entry = figures[name]
        if entry.get(key) != name + suffix:      # the stored name is derived, never taken from the index as a path
            return {"found": False, "message": NOT_YOURS}
        try:
            check_name(name)
            path = os.path.join(folder, name + suffix)
            if os.path.realpath(path) != os.path.join(os.path.realpath(folder), name + suffix):
                raise FigureRefused("path")
            with open(path, "rb") as f:
                data = f.read()
        except (FigureRefused, OSError):
            return {"found": False, "message": NOT_YOURS}
        return {"found": True, "name": name + suffix, "type": "text", "mime": "text/plain; charset=utf-8", "data": data}
    try:
        kind = check_name(name)
        path = os.path.join(folder, name)
        if os.path.realpath(path) != os.path.join(os.path.realpath(folder), name):
            raise FigureRefused("path")
        with open(path, "rb") as f:
            data = f.read()
    except (FigureRefused, OSError):
        return {"found": False, "message": NOT_YOURS}
    return {"found": True, "name": name, "type": kind, "mime": MIME[kind], "data": data}


def _clean_names(names):
    """(distinct names in the order given, None, None), or (None, reason, the offending name) when the list is not one."""
    if isinstance(names, (str, bytes)) or not isinstance(names, (list, tuple, set, frozenset)):
        return None, "bad_name", ""
    if len(names) > NAMES_LIMIT:        # before anything is looked at one by one (the same ceiling as the page's form fields)
        return None, "too_many", ""
    out, seen = [], set()
    for n in names:
        if not isinstance(n, str) or not n or len(n) > NAME_LIMIT or any(ord(c) < 32 or ord(c) == 127 for c in n):
            return None, "bad_name", _safe(n) if isinstance(n, str) else ""
        if n not in seen:
            seen.add(n)
            out.append(n)
    if len(out) > MAX_PER_RUN:
        return None, "too_many", ""
    return out, None, None


def pack_figures(*a, **k):
    """_pack_figures, except that a gallery lock that cannot be taken is refused with reason busy and nothing is changed (ruling K3)."""
    try:
        return _pack_figures(*a, **k)
    except GalleryBusy:
        return _refused("busy", BUSY_MESSAGE)


def _pack_figures(index_path, platform_path, run_id, names, *, caller, clock=time.time, _folder=None, _locked=False):
    """Put exactly the named figures into the delivery package: they get packed=true and packed_at, every other figure of the run is set back to
    packed=false (the package is the selection of this press; none at all is allowed and empties it). All or nothing: a name that is not in
    the gallery, too many names or an unreadable index refuse the whole call and index.json is not touched. {ok, found, count, names} or
    {ok: False, found, reason, message}; reason is not_found, bad_name, too_many, unknown_name, unreadable (index.json is damaged; checked before the names) or write_failed.
    `_folder` (the confirmed write of gallery_change, which has checked the owner itself) is the gallery folder to use instead of looking the run up, and
    `_locked` says that caller holds the gallery lock already (its check and this write are one hold), so it is not taken again."""
    folder = _folder if _folder is not None else _own_folder(index_path, platform_path, run_id, caller)[0]
    if folder is None:
        return _refused("not_found", NOT_YOURS, found=False)
    chosen, reason, bad = _clean_names(names)
    if chosen is None:
        if reason == "too_many":
            return _refused(reason, "一次最多選 %d 張圖，沒有變更任何內容 (at most %d figures at a time; nothing was changed)" % (MAX_PER_RUN, MAX_PER_RUN))
        return _refused(reason, "圖名不合規定，沒有變更任何內容 (a figure name is not valid; nothing was changed)", name=bad)
    with (contextlib.nullcontext() if _locked else gallery_lock(folder)):
        _sweep_tmp(folder)
        figures, problem = read_index(folder)
        if problem:     # the damage is said before any name is looked at (ruling G2)
            return _refused("unreadable", problem)
        for n in chosen:
            if n not in figures:
                return _refused("unknown_name", "圖庫裡沒有「%s」，沒有變更任何內容 (the gallery has no figure \"%s\"; nothing was changed)" % (n, n), name=n)
        if not figures:
            return {"ok": True, "found": True, "count": 0, "names": []}
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(clock()))
        updated = {k: dict(v, packed=k in chosen, packed_at=stamp if k in chosen else None) for k, v in figures.items()}
        try:
            _write_index(folder, updated)
        except OSError:
            return _refused("write_failed", "未能打包，圖庫沒有變更；請稍後再試，或回報給平台管理者 (could not pack; the gallery is unchanged. Try again later or tell the administrator)")
    return {"ok": True, "found": True, "count": len(chosen), "names": chosen}


def delete_figure(*a, **k):
    """_delete_figure, with the same refusal when the gallery lock cannot be taken (ruling K3)."""
    try:
        return _delete_figure(*a, **k)
    except GalleryBusy:
        return _refused("busy", BUSY_MESSAGE)


def _delete_figure(index_path, platform_path, run_id, name, *, caller, _folder=None, _locked=False):
    """Remove one figure of the caller's own run: its image, its code and its parameters, and its entry in index.json (so it leaves the package
    too). {ok, found, name} or {ok: False, found, reason, message}. The index is written first, so a file that cannot be removed afterwards is
    only a leftover (the files go inside the lock) that nothing lists. Only files inside the run's own gallery folder are ever removed.
    `_folder` and `_locked` are as for _pack_figures."""
    folder = _folder if _folder is not None else _own_folder(index_path, platform_path, run_id, caller)[0]
    if folder is None:
        return _refused("not_found", NOT_YOURS, found=False)
    chosen, reason, bad = _clean_names([name])
    if chosen is None:
        return _refused("bad_name", "圖名不合規定，沒有刪除任何內容 (a figure name is not valid; nothing was deleted)", name=bad)
    with (contextlib.nullcontext() if _locked else gallery_lock(folder)):
        _sweep_tmp(folder)
        figures, problem = read_index(folder)
        if problem:
            return _refused("unreadable", problem)
        if name not in figures:
            return _refused("unknown_name", "圖庫裡沒有「%s」，沒有刪除任何內容 (the gallery has no figure \"%s\"; nothing was deleted)" % (name, name), name=name)
        rest = {k: v for k, v in figures.items() if k != name}
        try:
            _write_index(folder, rest)
        except OSError:
            return _refused("write_failed", "未能刪除，圖庫沒有變更；請稍後再試，或回報給平台管理者 (could not delete; the gallery is unchanged. Try again later or tell the administrator)")
        for leaf in (name, name + ".code.txt", name + ".params.txt"):       # still inside the lock (ruling K2): a same-named figure written next cannot lose its file
            try:
                os.unlink(os.path.join(folder, leaf))
            except OSError:
                pass
    return {"ok": True, "found": True, "name": name}


# ---- pack and delete through the confirmation channel (mcp-gallery-actions, slice 3) ----------------------------------------------------------
# The user's own LLM may ask to pack or delete figures of its owner's gallery; the person's yes (kind gallery_change, which queues no job) is what
# changes it. The request holds the names and what would happen, and the gallery as it was when the person was asked (every figure's name,
# created time, the request that stored it, and whether it is packed). At the yes the gallery is read again under its lock; if it is not as it was
# shown, nothing is written. The write itself is slice 2's pack_figures / delete_figure, called inside that same hold of the lock.

CHANGED_MESSAGE = ("圖庫已變動，這次確認沒有變更任何內容，請重新提出 (the gallery has changed; this confirmation changed nothing, please propose again)")
UNREADABLE_MESSAGE = "圖庫目前暫時無法讀取，沒有變更任何內容，請聯絡平台管理者 (the gallery cannot be read right now; nothing was changed, tell the platform administrator)"
GONE_MESSAGE = "找不到這個分析的圖庫，沒有變更任何內容，請確認分析後重新提出 (the gallery of this run was not found; nothing was changed, check the run and propose again)"
ONE_AT_A_TIME = "一次只能刪除一張圖，請分開提出 (delete one figure at a time; propose each separately)"
NO_CHANGE = "沒有需要變更：圖庫已是這個狀態，沒有建立任何申請 (nothing to change: the gallery is already like that, so no request was made)"


def _snapshot(figures):
    """The gallery as the person is asked about it: each figure's name, when it was stored, the request that stored it and whether it is packed.
    A same-named replacement has another created time or request id, so it counts as a change; packed_at is left out (packing the same set again is no change)."""
    return [[k, v.get("created") or "", v.get("request_id") or "", v.get("packed") is True] for k, v in sorted(figures.items())]


def _pack_effect(figures, chosen):
    now = sorted(k for k, v in figures.items() if v.get("packed") is True)
    keep = sorted(n for n in chosen if n in now)
    return {"add": sorted(n for n in chosen if n not in now), "remove": [k for k in now if k not in chosen], "keep_packed": keep,
            "keep_unpacked": sorted(k for k in figures if k not in chosen and k not in now), "result": sorted(chosen)}


def _delete_effect(figures, name):
    entry = figures[name]
    files = [name] + [name + suffix for key, suffix in (("code_file", ".code.txt"), ("params_file", ".params.txt")) if entry.get(key) == name + suffix]
    return {"name": name, "in_package": entry.get("packed") is True, "files": files}


def _effect_of(bundle, figures):
    if bundle["action"] == "pack":
        return _pack_effect(figures, bundle["names"])
    return _delete_effect(figures, bundle["name"])


def _join(names, en):
    return (", " if en else "、").join(names)


def gallery_screen(bundle, lang="zh"):
    """The text the person reads before the yes for a gallery_change request, in Chinese (the stored screen) or in English (the page in English).
    The same names, in the same lines, on every channel."""
    en = lang == "en"
    e = bundle["effect"]
    if bundle["action"] == "pack":
        add, rem, keep, still, result = e["add"], e["remove"], e["keep_packed"], e["keep_unpacked"], e["result"]
        if en:
            out = ["== Confirm the delivery package ==", "Run: %s" % bundle["run_name"], "Added to the package: %s" % (_join(add, True) or "none")]
            tail = (" (stays in the gallery and can be packed again later)" if len(rem) == 1 else " (they stay in the gallery and can be packed again later)") if rem else ""
            out += ["Removed from the package: %s%s" % (_join(rem, True) or "none", tail),
                    "Unchanged, in the package: %s" % (_join(keep, True) or "none"), "Unchanged, not in the package: %s" % (_join(still, True) or "none"),
                    "The package will hold %d figure%s%s" % (len(result), "" if len(result) == 1 else "s", ": " + _join(result, True) if result else "")]
            if not result and rem:
                out.append("Note: The delivery package will be emptied. The figures now in it (%s) will leave the package and stay in the gallery." % _join(rem, True))
            return "\n".join(out) + "\n"
        out = ["== 打包確認 (confirm the delivery package) ==", "分析：%s" % bundle["run_name"], "加入交付包：%s" % (_join(add, False) or "無"),
               "移出交付包：%s%s" % (_join(rem, False) or "無", "（仍留在圖庫，之後可以再打包）" if rem else ""),
               "不變（已在交付包內）：%s" % (_join(keep, False) or "無"), "不變（未打包）：%s" % (_join(still, False) or "無"),
               "打包後交付包：%d 張%s" % (len(result), "（%s）" % _join(result, False) if result else "")]
        if not result and rem:
            out.append("注意：交付包將被清空，目前包內的 %s 都會移出，但仍留在圖庫，之後可以再打包。" % _join(rem, False))
        return "\n".join(out) + "\n"
    name, files = e["name"], e["files"]
    if en:
        listed = [f for f in files if f != name]
        what = "Will delete %s" % name
        if len(listed) == 2:
            what += ", its code file %s and its parameter file %s" % (listed[0], listed[1])
        elif listed:
            what += " and its %s %s" % ("code file" if listed[0].endswith(".code.txt") else "parameter file", listed[0])
        else:
            what = "Will delete the figure file %s" % name
        return "\n".join(["== Confirm deleting a figure ==", "Run: %s" % bundle["run_name"], "Figure to delete: %s" % name, what,
                          ("%s is currently in the delivery package and will be removed from it too" if e["in_package"] else "%s is not in the delivery package") % name,
                          "After this the gallery no longer has %s." % name]) + "\n"
    parts = ["圖檔 %s" % name] + [("程式碼檔 %s" if f.endswith(".code.txt") else "參數檔 %s") % f for f in files if f != name]
    return "\n".join(["== 刪除確認 (confirm deleting a figure) ==", "分析：%s" % bundle["run_name"], "要刪除：%s" % name, "會一併刪除：%s" % "、".join(parts),
                      "目前在交付包內：%s" % ("是（刪除後會一併移出交付包）" if e["in_package"] else "否"), "刪除後圖庫裡不再有 %s。" % name]) + "\n"


def _check_asked(name):
    """check_name, with the next step said: a name that cannot be a figure of this gallery is refused before any request."""
    try:
        check_name(name)
    except FigureRefused as e:
        raise FigureRefused("%s；請修正後重新提出 (fix the name and propose again)" % e)


async def _request_change(action, platform_path, *, run_id, arg, caller, person, clock, remote, index_path, request_id, user_confirmed):
    """The one request function behind both tools. Writes nothing: a pending request (kind gallery_change) is made for the change and the person is
    asked. {state: pending|ok|refused|unchanged, request_id, url, summary, message}. A run that is not the caller's and one that is not there answer alike;
    a name that is not valid or not in the gallery refuses the whole call before a request exists; a change that would change nothing makes no request."""
    from . import _ask, _caller_id, platform_path_for
    plat = platform_path_for(index_path, platform_path)
    tool = "pack_figures" if action == "pack" else "delete_figure"

    def refused(reason):
        return {"ok": False, "sent": False, "state": "refused", "request_id": None, "url": None, "reason": reason, "message": reason}
    if (isinstance(run_id, str) and _lone_surrogate(run_id)) or (isinstance(arg, str) and _lone_surrogate(arg)) or (
            isinstance(arg, (list, tuple)) and any(isinstance(n, str) and _lone_surrogate(n) for n in arg)):
        return refused("run 編號或圖名含有不成對的代理字元，不是正確的文字，未送出 (the run id or a figure name contains a lone surrogate, which is not valid text; nothing was sent)")
    view = _owned_run(index_path, platform_path, run_id, caller)
    if view is None:
        return refused("找不到 run「%s」。請用 list_runs 查自己的 run 編號後再送 (run not found: %s; use list_runs to see your own run ids)" % (_safe(run_id), _safe(run_id)))
    try:
        if action == "pack":
            names, reason, bad = _clean_names(arg)
            if names is None:
                raise FigureRefused("一次最多選 %d 張圖，請分次提出 (at most %d figures at a time; propose again with fewer)" % (MAX_PER_RUN, MAX_PER_RUN) if reason == "too_many" else
                                    "圖名不合規定：names 必須是圖名的清單，每個名稱只能用英數字、點、底線與連字號，請修正後重新提出 (a figure name is not valid: names must be a list of figure names; fix and propose again)")
            for n in names:
                _check_asked(n)
            key = "names"
            asked = sorted(names)
        else:
            if isinstance(arg, (list, tuple, set, frozenset)) or (isinstance(arg, str) and re.search(r"[\s,;]", arg.strip())):
                raise FigureRefused(ONE_AT_A_TIME)
            if _clean_names([arg])[0] is None:
                raise FigureRefused("圖名不合規定：name 必須是一個圖名，請修正後重新提出 (a figure name is not valid: name must be one figure name; fix and propose again)")
            _check_asked(arg)
            key, asked = "name", arg
        folder = run_folder(plat, _caller_id(caller), run_id)
        figures, problem = read_index(folder)
        if problem:
            raise FigureRefused(UNREADABLE_MESSAGE)
        stored = _own_request(plat, request_id, _caller_id(caller), "gallery_change") if isinstance(request_id, str) and user_confirmed is True else None
        if stored and stored.get("action") == action and stored.get("run_id") == run_id and stored.get(key) == asked:
            bundle = {k: stored[k] for k in ("action", "run_id", "run_name", key, "effect", "snapshot")}      # a call that carries the yes: what the screen said, not what the gallery says now
        else:
            for n in (asked if action == "pack" else [asked]):
                if n not in figures:
                    raise FigureRefused("圖庫裡沒有「%s」，沒有變更任何內容；請確認圖名後重新提出 (the gallery has no figure \"%s\"; nothing was changed, check the name and propose again)" % (n, n))
            bundle = {"action": action, "run_id": run_id, "run_name": view["name"], key: asked, "snapshot": _snapshot(figures)}
            bundle["effect"] = _effect_of(bundle, figures)
            if action == "pack" and not bundle["effect"]["add"] and not bundle["effect"]["remove"]:
                return {"ok": True, "sent": False, "state": "unchanged", "request_id": None, "url": None, "message": NO_CHANGE}
    except FigureRefused as e:
        return refused(str(e))
    text = gallery_screen(bundle, "zh")

    def done(rid):
        e = bundle["effect"]
        msg = ("已打包：交付包現有 %d 張 (the delivery package now holds %d figures)" % (len(e["result"]), len(e["result"])) if action == "pack" else
               "已刪除 %s (deleted %s)" % (e["name"], e["name"]))
        return {"ok": True, "sent": True, "state": "ok", "request_id": rid, "url": None, "message": msg}
    got = await _ask(plat, "gallery_change", None, bundle, text, "打包" if action == "pack" else "刪除", caller, person, clock, remote, tool=tool,
                     request_id=request_id, user_confirmed=user_confirmed, done=done)
    if got.get("state") == "ok":
        return got
    if got.get("state") == "pending":
        url, rid = got["confirmation_url"], got["id"]
        out = {"ok": True, "sent": False, "state": "pending", "request_id": rid, "url": url, "summary": text,
               "message": "還沒變更 (nothing is changed yet)。請本人打開這個網址、用自己的帳號登入、看過內容後按送出：%s ——按了之後才會變更圖庫，不必再呼叫一次。"
                          "或者，把內容給本人看，本人在聊天裡親口回覆同意之後，用同樣的參數加上 request_id=%s 與 user_confirmed=true 再呼叫 %s 一次；"
                          "在本人回覆之前不可自己填 true。 (open the address, log in as yourself and press the button; or, once the person has answered yes in the "
                          "chat, call %s again with the same arguments plus request_id=%s and user_confirmed=true; never set it true before they answer)"
                          % (url, rid, tool, tool, rid)}
        if action == "delete":      # a deletion is confirmed on the confirmation page or in the form, never by a relayed yes: say only that
            out["message"] = ("尚未變更 (nothing is changed yet)。刪除無法復原，須由本人在確認頁按下確認：請本人打開確認頁網址、用自己的帳號登入、看過內容後按下確認：%s "
                              "——按下之後才會刪除，不必再呼叫一次；在聊天裡回答確認不算數。 (a deletion cannot be undone, so only the person can confirm it: open the "
                              "address, log in as yourself and press confirm; no second call is needed, and a yes in the chat does not count)" % url)
        if got.get("message", "").startswith("⚠"):
            out["message"] = got["message"].split("還沒送出")[0] + out["message"]
        return out
    out = refused(got.get("message") or "未送出 (not sent)")
    if got.get("confirmation_url"):      # the refused relay of a deletion names the page of that very request
        out["url"] = got["confirmation_url"]
    return out


async def request_pack_figures(platform_path, *, run_id, names, caller=None, person=None, clock=time.time, remote=False, index_path=None,
                               request_id=None, user_confirmed=False):
    """Propose that the delivery package of the caller's own run is exactly the figures `names` (none at all empties it). Nothing is changed until a person's yes."""
    return await _request_change("pack", platform_path, run_id=run_id, arg=names, caller=caller, person=person, clock=clock, remote=remote,
                                 index_path=index_path, request_id=request_id, user_confirmed=user_confirmed)


async def request_delete_figure(platform_path, *, run_id, name, caller=None, person=None, clock=time.time, remote=False, index_path=None,
                                request_id=None, user_confirmed=False):
    """Propose that one figure of the caller's own run is deleted with its code and parameters. Nothing is changed until a person's yes."""
    return await _request_change("delete", platform_path, run_id=run_id, arg=name, caller=caller, person=person, clock=clock, remote=remote,
                                 index_path=index_path, request_id=request_id, user_confirmed=user_confirmed)


def write_gallery_change(platform_path, caller_user_id, bundle, rid, now):
    """The write of a confirmed gallery_change request (called by confirm.approve after the person's yes). The owner is checked again, then, in ONE hold
    of the gallery lock, the gallery is read again and compared with what the person was shown; only when it is the same is slice 2's pack_figures or
    delete_figure called. Anything else is jobs.JobRefused with the reason (the request is void and nothing changed)."""
    try:
        action, run_id, run_name, shown = bundle["action"], bundle["run_id"], bundle["run_name"], json.loads(json.dumps(bundle["snapshot"]))
        if action not in ("pack", "delete"):
            raise KeyError(action)
        if caller_user_id is not None and run_name not in jobs.owned_run_names(platform_path, caller_user_id):
            raise FigureRefused(NOT_YOURS)
        folder = run_folder(platform_path, caller_user_id, run_id)
    except FigureRefused:
        raise jobs.JobRefused(GONE_MESSAGE)
    except (KeyError, TypeError, ValueError):
        raise jobs.JobRefused("申請的內容不完整，沒有變更任何內容，請重新提出 (the request is incomplete; nothing was changed, propose again)")
    if not os.path.isdir(folder):
        raise jobs.JobRefused(GONE_MESSAGE)
    try:
        with gallery_lock(folder):
            figures, problem = read_index(folder)
            if problem:
                raise jobs.JobRefused(UNREADABLE_MESSAGE)
            try:
                same = _snapshot(figures) == shown and _effect_of(bundle, figures) == json.loads(json.dumps(bundle["effect"]))
            except (KeyError, TypeError, ValueError):
                same = False
            if not same:
                raise jobs.JobRefused(CHANGED_MESSAGE)
            if action == "pack":
                got = pack_figures(None, platform_path, run_id, bundle["names"], caller=None, clock=lambda: now, _folder=folder, _locked=True)
            else:
                got = delete_figure(None, platform_path, run_id, bundle["name"], caller=None, _folder=folder, _locked=True)
    except GalleryBusy:
        raise jobs.JobRefused(BUSY_MESSAGE)
    if not got.get("ok"):
        raise jobs.JobRefused(got.get("message") or CHANGED_MESSAGE)
