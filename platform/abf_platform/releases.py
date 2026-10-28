# Nothing existing: nf-core's CLI and the plugin's prepare_launch.sh each look up tags on their own; the platform has no function to reuse, so the pick logic lives here.
"""Pick the newest launchable release from a list of tag names (release-tag-pick).

Pure string and JSON-file work. The caller passes `fetch(repo) -> list of tag names`; this module opens no
connection and starts no program. 這個模組只做字串與 JSON 檔運算，不連網、不啟動程式。
"""
import json
import os
import re
import time

_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_TAG = re.compile(r"^v?[0-9]+(\.[0-9]+){1,3}\Z")


def repo_of(pipeline):
    """'ampliseq' -> 'nf-core/ampliseq'; 'owner/name' unchanged; anything else raises ValueError."""
    p = pipeline
    if isinstance(p, str) and p and "/" not in p:
        p = "nf-core/" + p
    ok = isinstance(p, str) and _REPO.match(p) is not None
    if ok and any(seg in (".", "..") for seg in p.split("/")):
        ok = False
    if not ok:
        raise ValueError("pipeline 名稱不合格（要寫 owner/name，例如 nf-core/ampliseq）"
                         " / invalid pipeline name %r, expected owner/name" % (pipeline,))
    return p


def usable(tag):
    """True when the tag is a plain numeric version that the launch revision check accepts."""
    return isinstance(tag, str) and _TAG.match(tag) is not None


def _key(tag):
    return tuple(int(x) for x in tag.lstrip("v").split("."))


def pick_latest(tags):
    """The newest usable tag as its original string, or None."""
    if not isinstance(tags, (list, tuple)):
        return None
    best = None
    for t in tags:
        if not usable(t):
            continue
        if best is None:
            best = t
            continue
        a, b = _key(t), _key(best)
        # same version: prefer the one without the leading v
        if a > b or (a == b and best.startswith("v") and not t.startswith("v")):
            best = t
    return best


def usable_sorted(tags):
    """Every usable tag from the list, newest first, as the original strings (guided-launch-2d: the version list of the launch page). Of two
    spellings of one version the one without the leading v comes first, as in pick_latest, so the first item is always pick_latest's answer."""
    if not isinstance(tags, (list, tuple)):
        return []
    return sorted((t for t in tags if usable(t)), key=lambda t: (_key(t), not t.startswith("v")), reverse=True)


def parse_ls_remote(text):
    """Tag names from `git ls-remote --tags --refs` output; bad lines are skipped."""
    out = []
    if not isinstance(text, str):
        return out
    prefix = "refs/tags/"
    for line in text.splitlines():
        if "\t" not in line:
            continue
        ref = line.split("\t", 1)[1].strip()
        if ref.startswith(prefix) and len(ref) > len(prefix):
            out.append(ref[len(prefix):])
    return out


def _read_cache(path):
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _entry(data, repo):
    e = data.get(repo)
    if (isinstance(e, dict) and isinstance(e.get("revision"), str)
            and isinstance(e.get("checked_at"), (int, float)) and not isinstance(e.get("checked_at"), bool)):
        return e
    return None


def _listed(entry):
    """The version list of a cache entry; an entry from before the list was kept holds only its newest version."""
    listed = entry.get("releases")
    if isinstance(listed, list) and listed and all(isinstance(x, str) for x in listed):
        return list(listed)
    return [entry["revision"]]


def _write_cache(path, data):
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def _result(pipeline, revision, source, checked_at, why, releases=None):
    return {"pipeline": pipeline, "revision": revision, "source": source, "checked_at": checked_at, "why": why, "releases": releases or []}


def lookup(pipeline, fetch, *, cache_path=None, clock=time.time, ttl=86400.0):
    """The newest usable release for a pipeline, with a cache. Always returns a dict, never raises."""
    try:
        repo = repo_of(pipeline)
    except ValueError as e:
        return _result(pipeline if isinstance(pipeline, str) else None, None, "none", None, str(e))
    now = clock()
    data = _read_cache(cache_path)
    old = _entry(data, repo)
    if old is not None and 0 <= now - old["checked_at"] < ttl:
        return _result(repo, old["revision"], "cache", old["checked_at"], None, _listed(old))
    why = None
    try:
        tags = fetch(repo)
        rev = pick_latest(tags)
        listed = usable_sorted(tags)
        if rev is None:
            why = "沒有可用的 release tag / no usable release tag for %s" % repo
    except Exception as e:  # any failure of the caller's source counts as a failed lookup
        rev = None
        listed = []
        why = "查詢最新版失敗 / lookup failed: %s: %s" % (type(e).__name__, e)
    if rev is not None:
        if cache_path is not None:
            data[repo] = {"revision": rev, "checked_at": now, "releases": listed}
            _write_cache(cache_path, data)
        return _result(repo, rev, "fetched", now, None, listed)
    if old is not None:
        return _result(repo, old["revision"], "stale-cache", old["checked_at"], why, _listed(old))
    return _result(repo, None, "none", None, why)
