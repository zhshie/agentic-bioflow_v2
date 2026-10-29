# Nothing existing: pairing FASTQ names into a samplesheet, the 2 GB web limit and the Datasets table are this platform's own rules (spec 012c, ADR 0009 point 5, ADR 0010); no library knows them, and this reads and writes no file content.
"""Datasets (spec 012c): pair FASTQ names into a samplesheet, say whether the web may take an upload, and keep a Dataset - a name, a
version, a samplesheet and the places of its files. The platform records names and places only; it never reads, copies or
stores a file (the bytes go straight to the person's own folder on the cluster, ADR 0010 - or, for a cloud destination, into the
person's own prefix of the lab's bucket, written by the agent on the platform host and never by this module).

A Dataset describes inputs. It has no status and no run: it starts nothing and is not a second copy of any run's state.
Every function takes the platform path first and `caller=` (None = the terminal, which sees everything). Over HTTP a person
reaches only the files below their own upload folder and only their own datasets; what belongs to somebody else answers like
what does not exist."""
import csv
import io
import json
import os
import re
import time

from abf_launch import build

from .. import cloud_store, compute_envs, store

WEB_UPLOAD_LIMIT = 2_000_000_000        # bytes, per file, decimal: what the browser reports for one file
SAMPLESHEET_LIMIT = 1_048_576           # 1 MiB
_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}\Z")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_EXT = re.compile(r"\.(fastq|fq)(\.gz)?$", re.I)
_TAG = re.compile(r"^(?P<stem>.+)_(?P<tag>[RI][0-9])(?P<end>_001)?$")
_NUM = re.compile(r"^(?P<stem>.+)_(?P<tag>[12])$")
_LANE = re.compile(r"_S[0-9]+(_L[0-9]{3})?$")

_TABLE = """CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    samplesheet_csv TEXT NOT NULL,
    files_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (owner_user_id, name, version)
)"""


def _no(message, **more):
    out = {"ok": False, "message": message}
    out.update(more)
    return out


# ---- pairing ---------------------------------------------------------------------------------------------------------------

def _classify(file):
    """(entry, None) for a file that can be a mate, else (None, reason). Nothing is guessed: no tag, a tag that is not R1/R2 (I1, I2,
    R3 ...) or a name that is not FASTQ is a reason, not a pair."""
    if not isinstance(file, str) or not file:
        return None, "不是檔名 (not a file name)"
    folder, base = os.path.split(file)
    ext = _EXT.search(base)
    if not ext:
        return None, "不是 FASTQ 檔（.fastq／.fq／.fastq.gz／.fq.gz） (not a FASTQ file)"
    stem = base[:ext.start()]
    kind = ext.group(0).lower()
    m = _TAG.match(stem)
    if m:
        tag, style, stem = m.group("tag"), ("R-tag", bool(m.group("end"))), m.group("stem")
        if tag not in ("R1", "R2"):
            return None, "%s 不是 R1／R2，不能配對 (%s is not R1 or R2, so it is not paired)" % (tag, tag)
        mate = int(tag[1])
    else:
        m = _NUM.match(stem)
        if not m:
            return None, "名稱裡沒有 R1／R2 或 _1／_2 標記 (no R1/R2 or _1/_2 tag in the name)"
        mate, style, stem = int(m.group("tag")), ("number", False), m.group("stem")
    return {"file": file, "folder": folder, "stem": stem, "mate": mate, "style": style, "kind": kind}, None


def pair_fastq(files):
    """Pair R1 with R2 by name. Returns {pairs: [{sample, fastq_1, fastq_2}], unpaired: [{file, reason}], csv}. Tags _R1_001/_R2_001,
    _R1/_R2 and _1/_2; a pair needs the same folder, the same stem, the same tag style and the same extension. The sample is the stem
    without a trailing _S<n>(_L<nnn>), so two lanes of one sample are two rows with one sample name. When it is not certain
    (a mate is missing, two files fit one mate, the styles differ) every file concerned goes to `unpaired` with its reason."""
    unpaired, groups = [], {}
    for file in files:
        entry, reason = _classify(file)
        if entry is None:
            unpaired.append({"file": file, "reason": reason})
            continue
        groups.setdefault((entry["folder"], entry["stem"]), {1: [], 2: []})[entry["mate"]].append(entry)
    pairs = []
    for (folder, stem), mates in groups.items():
        one, two = mates[1], mates[2]
        if len(one) == 1 and len(two) == 1 and one[0]["style"] == two[0]["style"] and one[0]["kind"] == two[0]["kind"]:
            sample = _LANE.sub("", stem) or stem
            pairs.append({"sample": sample, "fastq_1": one[0]["file"], "fastq_2": two[0]["file"]})
            continue
        if len(one) > 1 or len(two) > 1:
            reason = "同一個 mate 有不只一個候選檔，不猜 (more than one file fits the same mate; not guessing)"
        elif not one or not two:
            reason = "找不到另一半 (R1 or R2 is missing)"
        else:
            reason = "R1 與 R2 的標記風格或副檔名不一致，不猜 (the tag style or the extension of R1 and R2 differ; not guessing)"
        for entry in one + two:
            unpaired.append({"file": entry["file"], "reason": reason})
    order = {f: i for i, f in enumerate(files) if isinstance(f, str)}
    unpaired.sort(key=lambda u: order.get(u["file"], len(order)))
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("sample", "fastq_1", "fastq_2"))
    for p in pairs:
        writer.writerow((p["sample"], p["fastq_1"], p["fastq_2"]))
    return {"pairs": pairs, "unpaired": unpaired, "csv": out.getvalue()}


# ---- a cloud destination ---------------------------------------------------------------------------------------------------

def _cloud_target(platform_path, caller, destination):
    """((environment, prefix), None) for the Google Batch environment named `destination` that the caller may use, else (None, message).
    An environment that is somebody else's answers like one that does not exist. The environment need not be available: this only
    records a place."""
    owner = caller.user_id if caller is not None else None
    ce = compute_envs.get(platform_path, destination, owner=owner) if isinstance(destination, str) else None
    if ce is None:
        return None, "找不到計算環境：%s (compute environment not found: %s)" % (destination, destination)
    try:
        prefix = cloud_store.upload_prefix(ce, caller.name if caller is not None else None, cloud_store.workdir_scheme(ce))
    except cloud_store.CloudPathError as e:
        return None, str(e)
    return (ce, prefix), None


def _scheme(target):
    """'gs', 's3' or 'az': read from the prefix of the target."""
    return target[1].partition("://")[0]


def _wrong_scheme(target):
    head = _scheme(target) + "://"
    return "只收 %s 開頭的位置；一份資料集的檔案要全是同一種 (only %s locations are taken, and a dataset holds one kind only)" % (head, head)


def _cloud_place(url, target):
    """None when `url` lies in the caller's own prefix of the environment's bucket, else a plain message that names only that prefix."""
    ce, prefix = target
    try:
        bucket, _ = {"s3": cloud_store.parse_s3, "az": cloud_store.parse_az}.get(_scheme(target), cloud_store.parse_gs)(url)
    except cloud_store.CloudPathError as e:
        return str(e)
    if bucket != cloud_store.workdir_bucket(ce):
        return ("bucket 必須就是這個計算環境 workDir 所在的 bucket：%s (the bucket must be the one of the environment's workDir)"
                % cloud_store.workdir_bucket(ce))
    if not cloud_store.inside_prefix(url, prefix, _scheme(target)):
        return "位置必須在你自己的前綴裡：%s (locations must lie inside your own prefix)" % prefix
    return None


# ---- the caller's own folder ---------------------------------------------------------------------------------------------

def _within(platform_path, caller, name):
    """(real path, None) for a file inside the caller's own upload folder (a relative name means that folder), else (None, message).
    The message names the caller's folder and nothing else. The terminal (caller None) is not confined."""
    if not isinstance(name, str) or not name or chr(0) in name:
        return None, "檔名不正確 (not a usable file name)"
    if caller is None:
        return name, None
    from . import caller_area
    try:
        area = caller_area(platform_path, caller)
    except build.Refusal as e:
        return None, str(e)
    real = os.path.realpath(name if os.path.isabs(name) else os.path.join(area, name))
    if real == area or not real.startswith(area + os.sep):
        return None, "檔案必須在你自己的上傳資料夾裡：%s (files must lie inside your own uploads folder)" % area
    return real, None


def draft_samplesheet(platform_path, files, *, caller=None, destination=None):
    """Pair the named files into a samplesheet draft. Every name must lie in the caller's own folder. Writes nothing: the draft
    exists only in the answer, for the person to check before it is registered. With `destination` (the name of a Google Batch
    environment) a name is a gs:// location or a single file name, and must lie in the caller's own prefix of that bucket."""
    if not isinstance(files, list):
        return _no("files 必須是檔名清單 (files must be a list of names)")
    target = None
    if destination is not None:
        target, problem = _cloud_target(platform_path, caller, destination)
        if problem:
            return _no(problem)
    real = []
    for name in files:
        if target is not None:
            if not isinstance(name, str) or not name:
                return _no("檔名不正確 (not a usable file name)")
            try:
                if name.startswith(_scheme(target) + "://"):
                    path = name
                elif _SCHEME.match(name):
                    return _no(_wrong_scheme(target))
                else:
                    path = cloud_store.object_url(target[0], caller.name if caller is not None else None, name, _scheme(target))
            except cloud_store.CloudPathError as e:
                return _no(str(e))
            problem = _cloud_place(path, target)
            if problem:
                return _no(problem)
            real.append(path)
            continue
        path, problem = _within(platform_path, caller, name)
        if problem:
            return _no(problem)
        real.append(path)
    paired = pair_fastq(real)
    return {"ok": True, "csv": paired["csv"], "pairs": paired["pairs"], "unpaired": paired["unpaired"]}


# ---- the web limit -----------------------------------------------------------------------------------------------------------

def check_web_upload(platform_path, sizes, *, caller=None, destination=None):
    """Say whether the web may take these files: `sizes` is {name: bytes} as the browser reports it. The limit is per file. A file
    over it is not taken; the answer lists it and gives one command to run on the person's own computer, plus the other way
    (the file is already on the cluster: copy it into that same folder). With `destination` the same rule holds for a cloud bucket:
    the command is a copy into the caller's own prefix, and the other way is to put the files into that prefix."""
    if not isinstance(sizes, dict) or not all(isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) and v >= 0
                                              for k, v in sizes.items()):
        return _no("sizes 必須是 檔名 → 位元組數 (sizes must map a file name to a number of bytes)")
    target = None
    if destination is not None:
        target, problem = _cloud_target(platform_path, caller, destination)
        if problem:
            return _no(problem)
    over = [name for name, size in sizes.items() if size > WEB_UPLOAD_LIMIT]
    if not over:
        return {"ok": True, "accepted": list(sizes), "over": []}
    if target is not None:
        command = cloud_store.big_file_command(target[0], caller.name if caller is not None else None, _scheme(target))
        if _scheme(target) == "az":
            message = ("網頁一個檔案最多收 2 GB，這些檔案太大：%s。請在你自己的電腦上、用你自己的 Azure 登入，跑這一行指令上傳：%s ；平台不會代你上傳。"
                       "如果檔案已經在這個容器裡，就把它們放進同一個前綴：%s "
                       "(the web takes at most 2 GB per file; run the command on your own computer with your own Azure login; the platform does not upload it for you)"
                       ) % (", ".join(over), command, target[1])
            return _no(message, over=over, command=command, accepted=[n for n in sizes if n not in over])
        if _scheme(target) == "s3":
            message = ("網頁一個檔案最多收 2 GB，這些檔案太大：%s。請在你自己的電腦上、用你自己的 AWS 登入，跑這一行指令上傳：%s ；平台不會代你上傳。"
                       "如果檔案已經在這個 bucket 裡，就把它們放進同一個前綴：%s "
                       "(the web takes at most 2 GB per file; run the command on your own computer with your own AWS login; the platform does not upload it for you)"
                       ) % (", ".join(over), command, target[1])
            return _no(message, over=over, command=command, accepted=[n for n in sizes if n not in over])
        message = ("網頁一個檔案最多收 2 GB，這些檔案太大：%s。請在你的電腦上跑這一行指令上傳：%s 。"
                   "如果檔案已經在這個 bucket 裡，就把它們放進同一個前綴：%s "
                   "(the web takes at most 2 GB per file; run the command on your computer, or, if the files are already in this bucket, "
                   "put them into that same prefix)") % (", ".join(over), command, target[1])
        return _no(message, over=over, command=command, accepted=[n for n in sizes if n not in over])
    if caller is None:
        dest = "<你的上傳資料夾>/rawdata"
    else:
        from . import caller_area
        try:
            dest = caller_area(platform_path, caller) + "/rawdata"
        except build.Refusal as e:
            return _no(str(e))
    command = "bash scripts/push.sh <你電腦上的資料夾> %s" % dest
    message = ("網頁一個檔案最多收 2 GB，這些檔案太大：%s。請在你的電腦上跑這一行指令上傳：%s 。"
               "如果檔案已經在國網上，就把檔案複製進同一個資料夾：%s "
               "(the web takes at most 2 GB per file; run the command on your computer, or, if the files are already on the cluster, "
               "copy them into the same folder)") % (", ".join(over), command, dest)
    return _no(message, over=over, command=command, accepted=[n for n in sizes if n not in over])


# ---- registering and reading Datasets ---------------------------------------------------------------------------------------

def _table(con):
    con.execute(_TABLE)
    con.commit()


def _cells(text):
    """(header, rows) of a samplesheet, or (None, message)."""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error:
        return None, "樣本表不是正確的 CSV (the samplesheet is not valid CSV)"
    if not rows:
        return None, "樣本表是空的 (the samplesheet is empty)"
    return [h.strip() for h in rows[0]], rows[1:]


def register_dataset(platform_path, *, name, version, samplesheet, files, caller=None, clock=time.time, destination=None):
    """Keep a Dataset: `name` and `version` (letters, digits . _ -, 1 to 64), the samplesheet text and `files` = [{path, size_bytes?}].
    Every file must lie in the caller's own folder and every path in the samplesheet must be one of those files. No file is
    read, no URL and nothing that looks like a credential is kept, and a (owner, name, version) that exists is never changed. This saves
    a description only; nothing is started. With `destination` (the name of a Google Batch environment) every file is a gs:// location
    in the caller's own prefix of that bucket, none is a local path, and the samplesheet may name only those locations."""
    for label, value in (("名稱 name", name), ("版本 version", version)):
        if not isinstance(value, str) or not _NAME.match(value) or compute_envs.looks_like_credential(value):
            return _no("%s 只能用英數字、. _ -，長度 1 到 64，且不能像憑證 (%s may use letters, digits, . _ - only, 1 to 64 long, and must not look like a credential)"
                       % (label, label.split()[1]))
    if not isinstance(samplesheet, str):
        return _no("樣本表必須是文字 (the samplesheet must be text)")
    if len(samplesheet.encode("utf-8")) > SAMPLESHEET_LIMIT:
        return _no("樣本表太大，上限 1 MiB (the samplesheet is too large; the limit is 1 MiB)")
    if not isinstance(files, list) or not files:
        return _no("files 必須是檔案清單 [{path, size_bytes?}] (files must be a non-empty list)")
    target = None
    if destination is not None:
        target, problem = _cloud_target(platform_path, caller, destination)
        if problem:
            return _no(problem)
    kept, known = [], set()
    for item in files:
        item = {"path": item} if isinstance(item, str) else item
        if not isinstance(item, dict) or "path" not in item:
            return _no("每個檔案都要有 path (every file needs a path)")
        if target is not None:
            path = item["path"]
            if not isinstance(path, str) or not path:
                return _no("檔名不正確 (not a usable file name)")
            if compute_envs.looks_like_credential(path):
                return _no("檔案路徑含像憑證的值，不收 (a file path holds something that looks like a credential)")
            if not path.startswith(_scheme(target) + "://"):
                if _SCHEME.match(path):
                    return _no(_wrong_scheme(target))
                return _no("一份資料集不能同時混本機路徑與雲端位置；選了雲端目的地，檔案都要是 %s:// 位置 "
                           "(a dataset cannot mix local paths and cloud locations)" % _scheme(target))
            problem = _cloud_place(path, target)
        else:
            path, problem = _within(platform_path, caller, item["path"])
        if problem:
            return _no(problem)
        if compute_envs.looks_like_credential(path):
            return _no("檔案路徑含像憑證的值，不收 (a file path holds something that looks like a credential)")
        entry = {"path": path}
        if item.get("size_bytes") is not None:
            size = item["size_bytes"]
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                return _no("size_bytes 必須是 0 以上的整數 (size_bytes must be a whole number, 0 or more)")
            entry["size_bytes"] = size
        kept.append(entry)
        known.add(path)
    header, rows = _cells(samplesheet)
    if header is None:
        return _no(rows)
    missing = [c for c in ("sample", "fastq_1") if c not in header]
    if missing:
        return _no("樣本表缺少 %s 欄 (the samplesheet needs the column %s)" % (", ".join(missing), ", ".join(missing)))
    for row in rows:
        for cell in row:
            if target is not None and cell.strip().startswith(_scheme(target) + "://"):
                if cell.strip() not in known:
                    return _no("樣本表裡有檔案不在登記的檔案內 (the samplesheet names a file that is not among the registered files)")
                continue
            if _SCHEME.match(cell.strip()):
                return _no("樣本表含網址，不收；檔案要放進你的上傳資料夾 (the samplesheet holds a URL; put the files in your uploads folder)")
            if compute_envs.looks_like_credential(cell):
                return _no("樣本表含像憑證的值，不收 (the samplesheet holds something that looks like a credential)")
    for row in rows:
        for column in ("fastq_1", "fastq_2"):
            if column in header and header.index(column) < len(row) and row[header.index(column)].strip():
                cell = row[header.index(column)].strip()
                if target is not None:
                    path, problem = cell, None
                else:
                    path, problem = _within(platform_path, caller, cell)
                if problem or path not in known:
                    return _no("樣本表裡有檔案不在登記的檔案內 (the samplesheet names a file that is not among the registered files)")
    now = clock()
    con = store.connect_state(platform_path)
    try:
        _table(con)
        con.execute("BEGIN IMMEDIATE")
        owner = caller.user_id if caller is not None else None
        if con.execute("SELECT 1 FROM datasets WHERE owner_user_id IS ? AND name = ? AND version = ?", (owner, name, version)).fetchone():
            con.rollback()
            return _no("資料集 %s 版本 %s 已存在，版本不能改；請用新的版本名 (dataset %s version %s already exists; a version never changes)"
                       % (name, version, name, version))
        con.execute("INSERT INTO datasets (owner_user_id, name, version, samplesheet_csv, files_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (owner, name, version, samplesheet, json.dumps(kept), now))
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return {"ok": True, "dataset": {"name": name, "version": version, "n_files": len(kept), "created_at": now}}


def _rows(platform_path, caller, where="", args=()):
    con = store.connect_state(platform_path)
    try:
        _table(con)
        sql = "SELECT * FROM datasets WHERE 1 = 1"
        mine = []
        if caller is not None:
            sql += " AND owner_user_id = ?"
            mine.append(caller.user_id)
        return con.execute(sql + where, mine + list(args)).fetchall()
    finally:
        con.close()


def list_datasets(platform_path, *, caller=None):
    """The caller's own datasets (the terminal sees all): name, version, number of files, created_at."""
    rows = _rows(platform_path, caller, " ORDER BY name, created_at, id")
    return {"ok": True, "datasets": [{"name": r["name"], "version": r["version"], "n_files": len(json.loads(r["files_json"])),
                                      "created_at": r["created_at"]} for r in rows]}


def get_dataset(platform_path, name, version=None, *, caller=None):
    """One dataset with its samplesheet and file places; no version means the newest. What is not the caller's answers like what
    does not exist."""
    where, args = " AND name = ?", [name]
    if version is not None:
        where, args = where + " AND version = ?", args + [version]
    rows = _rows(platform_path, caller, where + " ORDER BY created_at DESC, id DESC LIMIT 1", args)
    if not rows:
        what = "%s 版本 %s" % (name, version) if version is not None else name
        return {"ok": False, "found": False, "name": name,
                "message": "找不到資料集：%s (dataset not found: %s)" % (what, what)}
    r = rows[0]
    files = json.loads(r["files_json"])
    return {"ok": True, "found": True, "name": r["name"], "version": r["version"], "samplesheet": r["samplesheet_csv"],
            "files": files, "n_files": len(files), "created_at": r["created_at"]}
