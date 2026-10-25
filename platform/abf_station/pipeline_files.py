# Nothing existing: git and the GitHub CLI are not installed on every agent machine, and nothing else reads just these four kinds of public file with a host allow-list and no credential; so this is a small urllib reader.
"""The pipeline_files job (feature release-lookup-job): read-only, public files only.

The agent is the one process on the user's side that can reach the internet, so it fetches for the platform, which never
connects out. It reads four kinds of public GitHub file and nothing else: `nextflow_schema.json` and `assets/schema_input.json`
of one pipeline at one pinned revision, the list of `docs/images` and one diagram from it, and the list of release tags.
Only three hosts are asked, over https, with GET, with no credential of any kind, and a redirect is never followed. The agent does
not parse what it reads (the platform does, in schema.py); it checks size and shape, and answers with its own short wording,
never with GitHub's headers or error pages. Nothing is written on this machine.

`OPEN(url, headers, timeout, limit) -> (status, headers, body)` is the only place that connects; the tests replace it. It
returns at most `limit + 1` bytes, so that a body longer than `limit` can be told from one that is exactly `limit` long.
"""
import base64
import json
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from abf_platform import releases

from . import __version__, launch, rules

ARGS = {"repo", "revision", "parts"}
PARTS = ("schema", "schema_input", "diagram", "image", "tags")
HOSTS = ("github.com", "raw.githubusercontent.com", "api.github.com")
REQUEST_SECONDS = 10.0
TOTAL_SECONDS = 45.0
SCHEMA_LIMIT = 1000000
LISTING_LIMIT = 1000000
IMAGE_LIMIT = 2000000
TAGS_LIMIT = 4000000
TAGS_TEXT_LIMIT = 1000000
MESSAGE_LIMIT = 300
_IMAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}\.(png|svg)\Z")
_TAG_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,200}\Z")
_SHA = re.compile(r"^[0-9a-f]{40}\Z")
_HEX4 = re.compile(r"^[0-9a-fA-F]{4}\Z")
_PNG = b"\x89PNG\r\n\x1a\n"
_ADVERT = "application/x-git-upload-pack-advertisement"

CLOCK = time.monotonic       # replaced in tests


class _Network(Exception):
    """A connection-level failure (or the whole budget used up): the job ends at once."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None            # a redirect is an answer to report, not a way to another host


def allowed(url):
    """True only for an https address on one of the three hosts, with no user, no password and no port."""
    if not isinstance(url, str) or not url or url != url.strip():
        return False
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError:
        return False
    if parts.scheme != "https" or "@" in parts.netloc or port is not None or parts.username or parts.password:
        return False
    return isinstance(host, str) and host.lower() in HOSTS and parts.netloc.lower() == host.lower()


def _fetch_once(url, headers, timeout, limit):
    """The real connection. Redirects are not followed; an HTTP error status is an answer, not an exception."""
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    go = opener.open
    try:
        reply = go(request, timeout=timeout)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), b""
    except urllib.error.URLError as e:
        raise OSError("could not connect") from e
    try:
        return reply.status, dict(reply.headers.items()), reply.read(limit + 1)
    except Exception as e:      # a cut connection or a bad chunk reads as a network failure
        raise OSError("connection broke") from e
    finally:
        reply.close()


OPEN = _fetch_once


def _network_result():
    return "error", {"ok": False, "error": "network",
                     "message": "代理連不到 GitHub，請檢查這台機器的網路 (the agent could not reach GitHub; check this machine's network)"}


# ---- what is asked for ----------------------------------------------------------------------------------------

def _problem(args):
    """None when the arguments are good, else a short reason. Judged here again whatever the platform judged."""
    repo, revision, parts = args.get("repo"), args.get("revision"), args.get("parts")
    if not isinstance(repo, str) or "/" not in repo:
        return "the repo must be owner/name (repo 要寫 owner/name)"
    try:
        releases.repo_of(repo)
    except ValueError:
        return "the repo is not a plain owner/name (repo 名稱不合格)"
    if any(set(seg) <= {"."} for seg in repo.split("/")):
        return "the repo is not a plain owner/name (repo 名稱不合格)"
    if not isinstance(parts, list) or not parts:
        return "parts must be a list that is not empty (parts 要是非空的清單)"
    if any(not isinstance(p, str) or p not in PARTS for p in parts):
        return "parts names something this agent does not read (不支援的項目)"
    if len(set(parts)) != len(parts):
        return "parts names one thing twice (項目重複)"
    if set(parts) == {"tags"}:
        if revision is not None:
            return "the release tags need no revision (查 tag 清單不給版本)"
    elif not isinstance(revision, str) or launch.REVISION.match(revision) is None:
        return "the revision must be an exact tag or a 40-character commit, never a branch (版本要寫死成精確 tag 或 commit，不收分支名)"
    return None


# ---- one request ---------------------------------------------------------------------------------------------

class _Fetcher:
    def __init__(self):
        self.started = CLOCK()

    def get(self, url, accept, limit):
        """(status, lower-cased headers, body). Raises _Network when the connection fails or the whole budget is gone."""
        if not allowed(url):
            raise rules.Refusal("this address is not one the agent may ask (不在允許的主機)")
        if CLOCK() - self.started > TOTAL_SECONDS:
            raise _Network()
        headers = {"User-Agent": "abf-station/" + __version__, "Accept": accept}
        try:
            status, got, body = OPEN(url, headers, REQUEST_SECONDS, limit)
        except OSError:
            raise _Network() from None
        lowered = {str(k).lower(): str(v) for k, v in (got or {}).items()}
        return status, lowered, body


def _words(status):
    return {
        "not_found": "GitHub 上沒有這個檔案 (not found on GitHub)",
        "too_large": "檔案太大，沒有讀 (the file is too large, so it was not read)",
        "bad_response": "GitHub 回的內容不能用 (GitHub gave an answer that cannot be used)",
        "rate_limited": "GitHub 暫時限制了請求 (GitHub is limiting requests for now)",
    }[status]


def _fail(status):
    return {"status": status, "message": _words(status)[:MESSAGE_LIMIT]}


def _judge(status, headers):
    """The part status for an answer that is not a plain 200, or None for 200."""
    if status == 200:
        return None
    if status == 404:
        return "not_found"
    if status == 429 or (status == 403 and headers.get("x-ratelimit-remaining", "").strip() == "0"):
        return "rate_limited"
    return "bad_response"


def _text_part(fetcher, url, limit):
    status, headers, body = fetcher.get(url, "*/*", limit)
    bad = _judge(status, headers)
    if bad:
        return _fail(bad)
    if len(body) > limit:
        return _fail("too_large")
    try:
        return {"status": "ok", "text": body.decode("utf-8")}
    except UnicodeDecodeError:
        return _fail("bad_response")


# ---- the diagram -----------------------------------------------------------------------------------------------

def _candidates(entries):
    """The images of the folder listing that may be a pipeline diagram, best first."""
    found = []
    for e in entries:
        name = e.get("name") if isinstance(e, dict) else None
        if not isinstance(name, str) or e.get("type") != "file" or _IMAGE_NAME.match(name) is None:
            continue
        low = name.lower()
        if "metro" not in low and "workflow" not in low:
            continue
        size = e.get("size")
        size = size if isinstance(size, int) and not isinstance(size, bool) else None
        found.append((("metro" not in low), (not name.endswith(".png")), len(name), name, size))
    found.sort(key=lambda c: c[:4])
    return found


def _listing(fetcher, repo, revision):
    """(entries, None) or (None, the part that stands for the failure)."""
    url = "https://api.github.com/repos/%s/contents/docs/images?ref=%s" % (repo, revision)
    status, headers, body = fetcher.get(url, "application/vnd.github+json", LISTING_LIMIT)
    bad = _judge(status, headers)
    if bad == "not_found":
        return None, {"status": "none"}
    if bad:
        return None, _fail(bad)
    if len(body) > LISTING_LIMIT:
        return None, _fail("too_large")
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        return None, _fail("bad_response")
    if not isinstance(data, list):
        return None, _fail("bad_response")
    return data, None


def _pick(entries):
    """The diagram part: the first candidate that is not too large, 'too_large' if all are, 'none' if there is no candidate."""
    found = _candidates(entries)
    if not found:
        return {"status": "none"}, None
    for _, _, _, name, size in found:
        if size is None or size <= IMAGE_LIMIT:
            kind = "image/png" if name.endswith(".png") else "image/svg+xml"
            return {"status": "ok", "name": name, "type": kind, "size": size}, name
    return _fail("too_large"), None


def _image(fetcher, repo, revision, diagram):
    """The image part for the diagram that was picked."""
    url = "https://raw.githubusercontent.com/%s/%s/docs/images/%s" % (repo, revision, diagram["name"])
    status, headers, body = fetcher.get(url, "*/*", IMAGE_LIMIT)
    bad = _judge(status, headers)
    if bad:
        return _fail(bad)
    if len(body) > IMAGE_LIMIT:
        return _fail("too_large")
    if diagram["type"] == "image/png":
        if not body.startswith(_PNG):
            return _fail("bad_response")
    else:
        try:
            head = body.decode("utf-8")[:4096]
        except UnicodeDecodeError:
            return _fail("bad_response")
        if "<svg" not in head:
            return _fail("bad_response")
    return {"status": "ok", "name": diagram["name"], "type": diagram["type"], "size": len(body),
            "data_b64": base64.b64encode(body).decode("ascii")}


# ---- the release tags ------------------------------------------------------------------------------------------

def _tags_text(body):
    """`git ls-remote --tags --refs` text from the advertisement of git's smart HTTP protocol, or None when it is malformed."""
    pos, lines, flushed, first = 0, [], False, True
    while pos < len(body):
        head = body[pos:pos + 4]
        try:
            head_text = head.decode("ascii")
        except UnicodeDecodeError:
            return None
        if _HEX4.match(head_text) is None:
            return None
        size = int(head_text, 16)
        if size == 0:
            pos += 4
            flushed = True
            continue
        if size < 4 or pos + size > len(body):
            return None
        flushed = False
        line = body[pos + 4:pos + size]
        pos += size
        if first:
            first = False
            if not line.startswith(b"# service=git-upload-pack"):
                return None
            continue
        line = line.split(b"\0", 1)[0].rstrip(b"\n")
        try:
            sha, ref = line.decode("utf-8").split(" ", 1)
        except (UnicodeDecodeError, ValueError):
            continue
        if _SHA.match(sha) is None or not ref.startswith("refs/tags/") or ref.endswith("^{}"):
            continue
        if _TAG_NAME.match(ref[len("refs/tags/"):]) is None:
            continue
        lines.append("%s\t%s\n" % (sha, ref))
    if first or not flushed:
        return None
    return "".join(lines)


def _tags(fetcher, repo):
    url = "https://github.com/%s.git/info/refs?service=git-upload-pack" % repo
    status, headers, body = fetcher.get(url, "*/*", TAGS_LIMIT)
    bad = _judge(status, headers)
    if bad:
        return _fail(bad)
    if len(body) > TAGS_LIMIT:
        return _fail("too_large")
    if headers.get("content-type", "").split(";")[0].strip().lower() != _ADVERT:
        return _fail("bad_response")
    text = _tags_text(body)
    if text is None:
        return _fail("bad_response")
    if len(text) > TAGS_TEXT_LIMIT:
        return _fail("too_large")
    return {"status": "ok", "text": text}


# ---- the job ---------------------------------------------------------------------------------------------------

def run_fetch(job, ctx):
    """(state, result) for one pipeline_files job: done with the parts asked for, or error/network when GitHub cannot be reached."""
    args = job.get("args") if isinstance(job, dict) else None
    problem = _problem(args if isinstance(args, dict) else {})
    if problem:
        raise rules.Refusal(problem)
    repo, revision = args["repo"], args["revision"]
    wanted = [p for p in PARTS if p in args["parts"]]
    fetcher = _Fetcher()
    parts, picked = {}, None
    try:
        for name in wanted:
            if name in ("schema", "schema_input"):
                path = "nextflow_schema.json" if name == "schema" else "assets/schema_input.json"
                parts[name] = _text_part(fetcher, "https://raw.githubusercontent.com/%s/%s/%s" % (repo, revision, path), SCHEMA_LIMIT)
            elif name in ("diagram", "image"):
                if "diagram" not in parts:      # one listing serves both: the image needs it to know which file to ask for
                    entries, failure = _listing(fetcher, repo, revision)
                    parts["diagram"], picked = (failure, None) if failure else _pick(entries)
                if name == "image":
                    diagram = parts["diagram"]
                    if picked is not None:
                        parts["image"] = _image(fetcher, repo, revision, diagram)
                    elif diagram["status"] == "none":
                        parts["image"] = _fail("not_found")
                    else:
                        parts["image"] = dict(diagram)
            else:
                parts[name] = _tags(fetcher, repo)
    except _Network:
        return _network_result()
    kept = {n: parts[n] for n in wanted + (["diagram"] if "image" in wanted else []) if n in parts}
    ordered = {n: kept[n] for n in PARTS if n in kept}
    return "done", {"ok": True, "repo": repo, "revision": revision, "parts": ordered,
                    "message": "read %d part(s) from GitHub (已從 GitHub 讀取)" % len(ordered)}
