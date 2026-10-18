# Nothing existing: pairing FASTQ names into a samplesheet, the 2 GB web limit and the Datasets table are this platform's own rules (spec 012c, ADR 0009 point 5, ADR 0010); no library knows them, and this reads and writes no file content.
"""Datasets (spec 012c): pair FASTQ names into a samplesheet, say whether the web may take an upload, and keep a Dataset - a name, a
version, a samplesheet and the places of its files. The platform records names and places only; it never reads, copies or
stores a file (the bytes go straight to the person's own folder on the cluster, ADR 0010).

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

from .. import compute_envs, store

WEB_UPLOAD_LIMIT = 2_000_000_000        # bytes, per file, decimal: what the browser reports for one file
SAMPLESHEET_LIMIT = 1_048_576           # 1 MiB
_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
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


def draft_samplesheet(platform_path, files, *, caller=None):
    """Pair the named files into a samplesheet draft. Every name must lie in the caller's own folder. Writes nothing: the draft
    exists only in the answer, for the person to check before it is registered."""
    if not isinstance(files, list):
        return _no("files 必須是檔名清單 (files must be a list of names)")
    real = []
    for name in files:
        path, problem = _within(platform_path, caller, name)
        if problem:
            return _no(problem)
        real.append(path)
    paired = pair_fastq(real)
    return {"ok": True, "csv": paired["csv"], "pairs": paired["pairs"], "unpaired": paired["unpaired"]}


# ---- the web limit -----------------------------------------------------------------------------------------------------------

def check_web_upload(platform_path, sizes, *, caller=None):
    """Say whether the web may take these files: `sizes` is {name: bytes} as the browser reports it. The limit is per file. A file
    over it is not taken; the answer lists it and gives one command to run on the person's own computer, plus the other way
    (the file is already on the cluster: copy it into that same folder)."""
    if not isinstance(sizes, dict) or not all(isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) and v >= 0
                                              for k, v in sizes.items()):
        return _no("sizes 必須是 檔名 → 位元組數 (sizes must map a file name to a number of bytes)")
    over = [name for name, size in sizes.items() if size > WEB_UPLOAD_LIMIT]
    if not over:
        return {"ok": True, "accepted": list(sizes), "over": []}
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


def register_dataset(platform_path, *, name, version, samplesheet, files, caller=None, clock=time.time):
    """Keep a Dataset: `name` and `version` (letters, digits . _ -, 1 to 64), the samplesheet text and `files` = [{path, size_bytes?}].
    Every file must lie in the caller's own folder and every path in the samplesheet must be one of those files. No file is
    read, no URL and nothing that looks like a credential is kept, and a (owner, name, version) that exists is never changed. This saves
    a description only; nothing is started."""
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
    kept, known = [], set()
    for item in files:
        item = {"path": item} if isinstance(item, str) else item
        if not isinstance(item, dict) or "path" not in item:
            return _no("每個檔案都要有 path (every file needs a path)")
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
            if _SCHEME.match(cell.strip()):
                return _no("樣本表含網址，不收；檔案要放進你的上傳資料夾 (the samplesheet holds a URL; put the files in your uploads folder)")
            if compute_envs.looks_like_credential(cell):
                return _no("樣本表含像憑證的值，不收 (the samplesheet holds something that looks like a credential)")
    for row in rows:
        for column in ("fastq_1", "fastq_2"):
            if column in header and header.index(column) < len(row) and row[header.index(column)].strip():
                path, problem = _within(platform_path, caller, row[header.index(column)].strip())
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
