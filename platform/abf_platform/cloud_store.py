# Nothing existing: searched google-cloud-storage, gcloud and Nextflow's gs:// support; each one opens a connection or starts a program inside the platform process, which principle 2 and TC-061/071 bar, so this module only judges locations and counts bytes, and the real write is done by an injected sink.
"""Cloud locations for Datasets (cloud-upload): how a gs:// location is read, whose prefix it lies in, and a streaming core.

Nothing here opens a file, a connection or a program. A location is text; a sink is whatever the caller hands in (the agent on the
platform host will be the real one, in a later task). No credential is taken, kept or returned: the only words that leave this module
are plain sentences about a location, never the location text a person typed."""
import re

from . import compute_envs

_BUCKET = re.compile(r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$")
_OBJECT_BYTES = 1024
_NAME_CHARS = 255
# Bytes, per file, decimal: the same number as WEB_UPLOAD_LIMIT in actions/datasets.py. Kept twice because datasets.py imports abf_launch.build
# and the queue should not pull that in for one number; a test makes sure the two are equal.
UPLOAD_LIMIT = 2_000_000_000


class CloudPathError(ValueError):
    """A location that cannot be used; the message is a plain sentence that says what to do."""


def _control(text):
    return any(ord(c) < 32 or ord(c) == 127 for c in text)


def parse_gs(url):
    """(bucket, object_name) of a gs://<bucket>/<object> location, or CloudPathError. No URL decoding: %2e%2e stays as written."""
    if not isinstance(url, str) or not url:
        raise CloudPathError("位置必須是文字 (a location must be text)")
    if _control(url):
        raise CloudPathError("位置裡有不能用的控制字元 (the location holds a control character)")
    if not url.startswith("gs://"):
        raise CloudPathError("只收 gs:// 開頭的位置 (only gs:// locations are taken)")
    bucket, _, name = url[5:].partition("/")
    if not _BUCKET.match(bucket):
        raise CloudPathError("bucket 名稱不正確：要 3 到 63 個字元，小寫英數與 - _ .，頭尾是英數 "
                             "(the bucket name must be 3 to 63 characters, lower-case letters, digits and - _ ., starting and ending with a letter or digit)")
    if not name:
        raise CloudPathError("位置後面要有檔案或資料夾名 (the location needs a name after the bucket)")
    if name.startswith("/"):
        raise CloudPathError("bucket 後面不能直接接 / (the name after the bucket must not begin with /)")
    if ".." in name.split("/"):
        raise CloudPathError("位置不能含 .. (the location must not contain ..)")
    if len(name.encode("utf-8")) > _OBJECT_BYTES:
        raise CloudPathError("位置太長，名稱最多 1024 位元組 (the location is too long; the name is at most 1024 bytes)")
    return bucket, name


def workdir_bucket(ce):
    """The bucket of a Google Batch environment's workDir, or CloudPathError. A workDir with no folder part still has its bucket."""
    if not isinstance(ce, dict) or ce.get("platform") != compute_envs.GOOGLE_BATCH:
        raise CloudPathError("這個計算環境不能放雲端資料，只有 Google Batch 環境可以 (only a Google Batch environment can hold cloud data)")
    config = ce.get("config")
    work = config.get("workDir") if isinstance(config, dict) else None
    if not isinstance(work, str) or not work.startswith("gs://"):
        raise CloudPathError("這個計算環境沒有 gs:// 的 workDir，不能放雲端資料 (this environment has no gs:// workDir)")
    bucket = work[5:].partition("/")[0]
    if not _BUCKET.match(bucket):
        raise CloudPathError("這個計算環境的 workDir 不是正確的 bucket 位置 (the workDir of this environment is not a usable bucket location)")
    return bucket


def _single(text, what, limit):
    if not isinstance(text, str) or not 1 <= len(text) <= limit or _control(text) or "/" in text or "\\" in text or text in (".", ".."):
        raise CloudPathError("%s 不能當成單層名稱 (%s is not a usable single name)" % (what, what))
    return text


def upload_prefix(ce, owner_name):
    """gs://<bucket>/uploads/<owner>/ ; without an owner (the terminal) gs://<bucket>/uploads/."""
    bucket = workdir_bucket(ce)
    if owner_name is None:
        return "gs://%s/uploads/" % bucket
    return "gs://%s/uploads/%s/" % (bucket, _single(owner_name, "使用者名 name", _NAME_CHARS))


def object_url(ce, owner_name, filename):
    """The location of a single-level file name inside the owner's prefix."""
    return upload_prefix(ce, owner_name) + _single(filename, "檔名 file name", _NAME_CHARS)


def inside_prefix(url, prefix):
    """True when url lies in prefix: the same bucket, a name that begins with the prefix and has at least one more character."""
    try:
        bucket, name = parse_gs(url)
        pbucket, pname = parse_gs(prefix)
    except CloudPathError:
        return False
    if not pname.endswith("/"):
        pname += "/"
    return bucket == pbucket and name.startswith(pname) and len(name) > len(pname)


def big_file_command(ce, owner_name):
    """One line to run on the person's own computer for files over the web limit; only the bucket prefix is in it."""
    # this phrase may appear only in this file (test_cloud_upload checks it); the file starts no program, the line is only text
    return "gcloud storage cp <你電腦上的資料夾>/* %srawdata/" % upload_prefix(ce, owner_name)


# ---- streaming -------------------------------------------------------------------------------------------------------------

def _fail(message, received):
    return {"ok": False, "message": message, "received": received}


def _abort(sink):
    try:
        sink.abort()
    except Exception:
        pass


def stream_into(chunks, sink, *, declared_size, limit):
    """Hand chunks of bytes one by one to sink.write and keep nothing. Stops at the first byte over `declared_size` or `limit`
    (the next chunk is not read) and calls sink.abort(); a total that differs from `declared_size`, or any error on either side,
    also aborts. Exact agreement calls sink.close(). The answer is {ok, received} or {ok: False, message, received}; the text of an
    error is never repeated."""
    if isinstance(declared_size, bool) or not isinstance(declared_size, int) or declared_size < 0:
        return _fail("宣告的大小必須是 0 以上的整數 (the declared size must be a whole number, 0 or more)", 0)
    if declared_size > limit:
        return _fail("檔案超過上限，這裡不收，請改用指令上傳 (the file is over the limit and is not taken here; use the command instead)", 0)
    received = 0
    try:
        for chunk in chunks:
            if received + len(chunk) > declared_size or received + len(chunk) > limit:
                _abort(sink)
                return _fail("收到的資料比宣告的多，已停止 (more data arrived than was declared; stopped)", received)
            sink.write(chunk)
            received += len(chunk)
        if received != declared_size:
            _abort(sink)
            return _fail("收到的資料比宣告的短，已中止 (less data arrived than was declared; stopped)", received)
        sink.close()
    except Exception:
        _abort(sink)
        return _fail("傳輸中斷 (the transfer was interrupted)", received)
    return {"ok": True, "received": received}
