# Nothing existing: searched the copy command of gcloud with a dash for standard input, the google-cloud-storage package and Nextflow's gs:// support; the packages are barred by TC-083/114/085 (neither the platform nor this agent may import a Google library), so a gcloud started with a fixed argument list reads the bytes from its standard input and this file only checks and counts.
"""put_upload: write one uploaded file into the person's own cloud prefix, on behalf of the platform.

The job holds references only (environment, owner, file name, size, destination). Every one of them is judged again here, because
this is the process that holds the key: the destination must be exactly gs://<bucket of the workDir>/uploads/<owner>/<name>, the file
must be a plain file of that size inside <ABF_STATION_UPLOADS>/<owner>/, and only then is the copy command of gcloud (reading its standard input) started and fed the
file in blocks of one mebibyte. Nothing is kept, logged or written to a local file. The key file is only looked for (never read);
gcloud reads it from the path in its environment. When the copy has ended the size of the cloud object is asked for, and only when it
equals the size of the staged file is that one staged file removed.
"""
import os
import re
import shutil
import stat as stat_mod

from abf_platform import cloud_store

from . import aws_preflight, gcb_preflight, rules, site

ARGS = {"ce", "owner", "name", "size", "dest"}
UPLOADS_ENV = "ABF_STATION_UPLOADS"         # this agent's own setting: the folder the platform writes uploads to
TIMEOUT_ENV = "ABF_STATION_PUT_TIMEOUT"     # seconds the copy may take; for tests, else TIMEOUT_SECONDS
TIMEOUT_SECONDS = 3600
DESCRIBE_SECONDS = 60
CHUNK = 1024 * 1024
DETAIL_LIMIT = 300
# these four are looked up at run time so that a test can put a fake in their place
OPEN, FSTAT, READ, UNLINK = os.open, os.fstat, os.read, os.unlink
_LOCAL_PATH = re.compile(r"(?<![\w:/.])/[^\s'\"]+")
_PLAIN_NUMBER = re.compile(r"[0-9]+")
_CHECK = "；已中止，bucket 上可能需要檢查 %s"


def _no(text):
    raise rules.Refusal(text)


def _fail(message, received):
    return "error", {"ok": False, "message": message, "bytes": received}


def _seconds():
    try:
        value = int(os.environ.get(TIMEOUT_ENV, ""))
    except ValueError:
        return TIMEOUT_SECONDS
    return value if value > 0 else TIMEOUT_SECONDS


def _cleaned(text):
    """The first 300 characters of what gcloud said, with key blocks, long tokens and local paths replaced by [hidden]."""
    return gcb_preflight._scrub(_LOCAL_PATH.sub("[hidden]", str(text))).strip()[:DETAIL_LIMIT]


class _Sink:
    """What cloud_store.stream_into writes into: the standard input of the gcloud program."""

    def __init__(self, fed, seconds, program="gcloud"):
        self.fed, self.seconds, self.reason, self.program = fed, seconds, None, program

    def write(self, data):
        self.fed.write(data)

    def close(self):
        self.fed.close_stdin()
        try:
            rc, out = self.fed.wait(self.seconds)
        except TimeoutError:
            self.reason = "%s 逾時（超過 %d 秒） (%s did not finish in time)" % (self.program, self.seconds, self.program)
            raise
        if rc != 0:
            self.reason = "%s 沒有成功（回傳碼 %s）：%s" % (self.program, rc, _cleaned(out))
            raise RuntimeError("the copy did not succeed")

    def abort(self):
        self.fed.kill()


def _area(owner):
    """The real path of the owner's folder inside the upload folder, else a Refusal."""
    given = os.environ.get(UPLOADS_ENV)
    if not given or not os.path.isabs(given) or not os.path.isdir(given):
        _no("這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS），請管理者設定 (this agent has no upload folder set)")
    root = os.path.realpath(given)
    area = os.path.realpath(os.path.join(root, owner))
    if os.path.dirname(area) != root:
        _no("你的上傳資料夾不在上傳區裡 (your upload folder is not inside the upload area)")
    return area


def _open(area, name, size):
    """(file descriptor, its fstat, path) of the plain file of exactly `size` bytes; never through a link. Else a Refusal."""
    path = os.path.join(area, name)
    if not hasattr(os, "O_NOFOLLOW"):
        try:
            if stat_mod.S_ISLNK(os.lstat(path).st_mode):
                _no("這是捷徑，不是一般檔案 (this is a link, not a plain file)")
        except OSError:
            pass
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        fd = OPEN(path, flags)
    except OSError:
        _no("找不到要上傳的檔案，請重新上傳 (the file is not in your upload folder; upload it again)")
    try:
        info = FSTAT(fd)
        if not stat_mod.S_ISREG(info.st_mode):
            _no("這不是一般檔案 (this is not a plain file)")
        if os.path.dirname(os.path.realpath(path)) != area:
            _no("這個檔案不在你的上傳資料夾裡 (the file is not inside your upload folder)")
        if info.st_size != size:
            _no("檔案和排隊時不一樣了，請重新上傳 (the file differs from when it was queued; upload it again)")
    except BaseException:
        os.close(fd)
        raise
    return fd, info, path


def _cloud_size(ce, dest, env):
    """The size the cloud object has, or None when it could not be asked or the answer is not a plain number."""
    argv = ["gcloud", "storage", "objects", "describe", dest, "--project", ce["project"], "--format=value(size)"]
    try:
        rc, out = site.run_fixed(argv, env, DESCRIBE_SECONDS)
    except TimeoutError:
        return None
    text = str(out).strip()
    if rc != 0 or not _PLAIN_NUMBER.fullmatch(text):
        return None
    return int(text)


def _remove(path, info):
    """Remove the staged file when the name still leads to the very file that was copied; True when it is gone."""
    try:
        now = os.lstat(path)
        if stat_mod.S_ISLNK(now.st_mode) or (now.st_dev, now.st_ino) != (info.st_dev, info.st_ino):
            return False
        UNLINK(path)
    except OSError:
        return False
    return True


def run_put(job, ctx):
    """(state, result) of one put_upload job. A reference that does not check out is a Refusal; nothing is started then."""
    args = job.get("args")
    if not isinstance(args, dict) or set(args) != ARGS:
        _no("這張上傳工作缺少需要的欄位 (the upload job lacks a field it needs)")
    given = args["ce"]
    platform = given.get("platform") if isinstance(given, dict) else None
    if platform == aws_preflight.TYPE:
        ce, scheme = aws_preflight.clean_environment(given), "s3"
        view = {"platform": aws_preflight.TYPE, "config": {"workDir": ce["workDir"]}}
    elif platform == gcb_preflight.TYPE:
        ce, scheme = gcb_preflight.clean_environment(given), "gs"
        view = {"platform": gcb_preflight.TYPE, "config": {"workDir": ce["workDir"]}}
    else:
        _no("這種計算環境不能放雲端資料 (this kind of environment cannot hold cloud data)")
    owner, name, dest, size = args["owner"], args["name"], args["dest"], args["size"]
    try:
        expected = cloud_store.object_url(view, owner, name, scheme)
        prefix = cloud_store.upload_prefix(view, owner, scheme)
    except cloud_store.CloudPathError:
        raise rules.Refusal("使用者名或檔名不能用 (the user name or the file name cannot be used)") from None
    if not (isinstance(dest, str) and dest == expected and cloud_store.inside_prefix(dest, prefix, scheme)):
        _no("目的地不在你自己的上傳前綴裡 (the destination is not inside your own upload prefix)")
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= cloud_store.UPLOAD_LIMIT:
        _no("檔案大小要在 1 位元組到 2 GB 之間 (the file size must be between 1 byte and 2 GB)")
    fd, info, path = _open(_area(owner), name, size)
    try:
        if scheme == "s3":
            return _transfer_aws(ctx, ce, dest, size, fd, info, path)
        return _transfer(ctx, ce, dest, size, fd, info, path)
    finally:
        os.close(fd)


def _transfer(ctx, ce, dest, size, fd, info, path):
    cred = gcb_preflight.credentials_path(ctx.settings_file)
    try:
        has_key = stat_mod.S_ISREG(os.stat(str(cred)).st_mode)
    except OSError:
        has_key = False
    if not has_key:
        return _fail("找不到金鑰檔（路徑不顯示內容），請管理者檢查 ABF_STATION_GCP_CREDENTIALS (the key file is missing)", 0)
    if shutil.which("gcloud") is None:
        return _fail("這台電腦沒裝 gcloud，請管理者安裝 (gcloud is not installed on this host)", 0)
    env = gcb_preflight._gcloud_env(cred)
    try:
        fed = site.start_fed(["gcloud", "storage", "cp", "-", dest, "--project", ce["project"]], env)
    except OSError:
        return _fail("沒能啟動 gcloud，請管理者檢查安裝 (gcloud could not be started)", 0)
    sink = _Sink(fed, _seconds())
    answer = cloud_store.stream_into(iter(lambda: READ(fd, CHUNK), b""), sink, declared_size=size, limit=cloud_store.UPLOAD_LIMIT)
    received = answer["received"]
    if not answer["ok"]:
        return _fail((sink.reason or answer["message"]) + _CHECK % dest, received)
    cloud = _cloud_size(ce, dest, env)
    if cloud is None:
        return "done", {"ok": True, "bytes": received, "path": dest,
                        "message": "已上傳 %s（%d 位元組），但沒能核對雲端大小；暫存檔保留" % (dest, received)}
    if not cloud == info.st_size == received:
        return _fail("雲端物件大小與本機不符，暫存檔保留，請重新上傳", received)
    tail = "平台主機上的暫存檔已刪除" if _remove(path, info) else "暫存檔沒刪掉，請管理者清理"
    return "done", {"ok": True, "bytes": received, "path": dest, "message": "已上傳 %s（%d 位元組）；%s" % (dest, received, tail)}


def _aws_cloud_size(ce, dest, env):
    """The size the S3 object has (head-object), or None when it could not be asked or the answer is not a plain number."""
    bucket, key = cloud_store.parse_s3(dest)
    argv = ["aws", "s3api", "head-object", "--bucket", bucket, "--key", key, "--query", "ContentLength", "--output", "text",
            "--region", ce["region"]]
    try:
        rc, out = site.run_fixed(argv, env, DESCRIBE_SECONDS)
    except (TimeoutError, OSError):
        return None
    text = str(out).strip()
    if rc != 0 or not _PLAIN_NUMBER.fullmatch(text):
        return None
    return int(text)


def _transfer_aws(ctx, ce, dest, size, fd, info, path):
    cred = aws_preflight.credentials_path(ctx.settings_file)
    try:
        has_key = stat_mod.S_ISREG(os.stat(str(cred)).st_mode)
    except OSError:
        has_key = False
    if not has_key:
        return _fail("找不到憑證檔 %s，請管理者檢查 ABF_STATION_AWS_CREDENTIALS (the credentials file is missing)" % cred, 0)
    env = aws_preflight._aws_env(cred, ce["region"])
    try:
        fed = site.start_fed(["aws", "s3", "cp", "-", dest, "--region", ce["region"]], env)
    except FileNotFoundError:
        return _fail("平台主機上找不到 aws 指令，請管理者安裝 AWS CLI (the aws command is not installed on this host)", 0)
    except OSError:
        return _fail("沒能啟動 aws，請管理者檢查安裝 (aws could not be started)", 0)
    sink = _Sink(fed, _seconds(), "aws")
    answer = cloud_store.stream_into(iter(lambda: READ(fd, CHUNK), b""), sink, declared_size=size, limit=cloud_store.UPLOAD_LIMIT)
    received = answer["received"]
    if not answer["ok"]:
        return _fail((sink.reason or answer["message"]) + _CHECK % dest, received)
    cloud = _aws_cloud_size(ce, dest, env)
    if cloud is None:
        return "done", {"ok": True, "bytes": received, "path": dest,
                        "message": "已上傳 %s（%d 位元組），但沒能核對雲端大小；暫存檔保留" % (dest, received)}
    if not cloud == info.st_size == received:
        return _fail("雲端物件大小與本機不符，暫存檔保留，請重新上傳", received)
    tail = "平台主機上的暫存檔已刪除" if _remove(path, info) else "暫存檔沒刪掉，請管理者清理"
    return "done", {"ok": True, "bytes": received, "path": dest, "message": "已上傳 %s（%d 位元組）；%s" % (dest, received, tail)}
