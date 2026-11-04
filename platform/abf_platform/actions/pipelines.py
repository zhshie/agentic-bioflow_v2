# Nothing existing: Seqera and nf-core keep no per-person, versioned store of canvas graphs; the owner rule (what is not yours answers like what does not exist) is this platform's own, as for datasets.
"""Composed pipelines (spec 017b): a graph of nf-core modules kept per owner, with numbered versions that are only ever added.
Every function takes the platform path first and `caller=` (None = the terminal, which sees everything). What belongs to somebody
else answers like what does not exist. This saves a description in the platform's own database and turns it into text; it starts
nothing and touches no site. The three tables are made the first time they are used and are not part of `store.STATE_SCHEMA`, so a
reader must make them itself before it looks (`_table`)."""
import hashlib
import json
import re
import sqlite3
import struct
import time
import zlib

from .. import compose, module_sources, pipeline_launch, store
from .. import validate as checks

_NAME = re.compile(r"^[a-z][a-z0-9-]{0,39}\Z")

_TABLES = """
CREATE TABLE IF NOT EXISTS pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (owner_user_id, name)
);
CREATE TABLE IF NOT EXISTS pipeline_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL REFERENCES pipelines(id),
    version INTEGER NOT NULL,
    graph_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (pipeline_id, version)
);
CREATE TRIGGER IF NOT EXISTS pipeline_versions_no_update BEFORE UPDATE ON pipeline_versions
    BEGIN SELECT RAISE(ABORT, 'pipeline versions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS pipeline_versions_no_delete BEFORE DELETE ON pipeline_versions
    BEGIN SELECT RAISE(ABORT, 'pipeline versions are append-only'); END;
"""
_TABLES += """CREATE TABLE IF NOT EXISTS pipeline_validations (
    pipeline_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    graph_sha256 TEXT NOT NULL,
    %s TEXT NOT NULL,
    result_json TEXT NOT NULL,
    validated_at REAL NOT NULL,
    PRIMARY KEY (pipeline_id, version)
);
""" % checks.SHA_FIELD

_SAVE_FAILED = "存檔沒有成功，什麼都沒有寫入；請稍後再試一次 (the save did not work and nothing was written; try again in a moment)"


def _no(message, **more):
    out = {"ok": False, "message": message}
    out.update(more)
    return out


def _not_found(pipeline_id):
    return "找不到這個組合 (pipeline not found): %s" % (pipeline_id,)


def _table(con):
    con.executescript(_TABLES)
    con.commit()


def _owner(caller):
    return caller.user_id if caller is not None else None


def _mine(con, pipeline_id, caller):
    """The pipeline row if it exists and is the caller's (the terminal sees all), else None."""
    if isinstance(pipeline_id, bool) or not isinstance(pipeline_id, int):
        return None
    sql, args = "SELECT * FROM pipelines WHERE id = ?", [pipeline_id]
    if caller is not None:
        sql, args = sql + " AND owner_user_id = ?", args + [caller.user_id]
    return con.execute(sql, args).fetchone()


def _latest(con, pipeline_id):
    return con.execute("SELECT * FROM pipeline_versions WHERE pipeline_id = ? ORDER BY version DESC LIMIT 1", (pipeline_id,)).fetchone()


def _summary(pipeline, version):
    return {"id": pipeline["id"], "name": pipeline["name"], "version": version["version"], "created_at": version["created_at"]}


def create_pipeline(platform_path, *, name, graph, caller=None, clock=time.time):
    """Keep a new composed pipeline: `name` (small letters, digits and -, 1 to 40) and its first graph as version 1. A graph with a
    problem writes nothing. A name the owner already has is refused; save a new version with `update_pipeline`."""
    if not isinstance(name, str) or not _NAME.match(name):
        return _no("名稱只能用小寫英文、數字與 -，以小寫英文開頭，長度 1 到 40 "
                   "(the name may use lowercase letters, digits and - only, must start with a letter, 1 to 40 long)")
    canonical, problems = compose.normalize(graph)
    if problems:
        return _no(problems[0], problems=problems)
    text = compose.graph_json(canonical)
    now = clock()
    owner = _owner(caller)
    con = store.connect_state(platform_path)
    try:
        _table(con)
        con.execute("BEGIN IMMEDIATE")
        if con.execute("SELECT 1 FROM pipelines WHERE owner_user_id IS ? AND name = ?", (owner, name)).fetchone():
            con.rollback()
            return _no("你已經有一個叫 %s 的組合；用 update 存新版本 (a pipeline named %s already exists; save a new version instead)"
                       % (name, name))
        cur = con.execute("INSERT INTO pipelines (owner_user_id, name, created_at) VALUES (?, ?, ?)", (owner, name, now))
        pid = cur.lastrowid
        con.execute("INSERT INTO pipeline_versions (pipeline_id, version, graph_json, created_at) VALUES (?, 1, ?, ?)", (pid, text, now))
        con.commit()
    except sqlite3.Error:
        con.rollback()
        return _no(_SAVE_FAILED)
    finally:
        con.close()
    return {"ok": True, "pipeline": {"id": pid, "name": name, "version": 1, "created_at": now}}


def update_pipeline(platform_path, pipeline_id, *, graph, caller=None, clock=time.time):
    """Add a version to the caller's pipeline. Versions are only added: the same graph as the newest version adds nothing and
    answers `unchanged`. A pipeline of somebody else answers like one that does not exist."""
    con = store.connect_state(platform_path)
    try:
        _table(con)
        row = _mine(con, pipeline_id, caller)
        if row is None:
            return _no(_not_found(pipeline_id))
        canonical, problems = compose.normalize(graph)
        if problems:
            return _no(problems[0], problems=problems)
        text = compose.graph_json(canonical)
        now = clock()
        con.execute("BEGIN IMMEDIATE")
        newest = _latest(con, row["id"])
        if newest["graph_json"] == text:
            con.rollback()
            return {"ok": True, "unchanged": True, "pipeline": _summary(row, newest)}
        number = newest["version"] + 1
        con.execute("INSERT INTO pipeline_versions (pipeline_id, version, graph_json, created_at) VALUES (?, ?, ?, ?)",
                    (row["id"], number, text, now))
        con.commit()
    except sqlite3.Error:
        con.rollback()
        return _no(_SAVE_FAILED)
    finally:
        con.close()
    return {"ok": True, "pipeline": {"id": row["id"], "name": row["name"], "version": number, "created_at": now}}


def list_pipelines(platform_path, *, caller=None):
    """The caller's own pipelines (the terminal sees all): id, name, newest version, number of nodes, created_at, updated_at."""
    con = store.connect_state(platform_path)
    try:
        _table(con)
        sql, args = "SELECT * FROM pipelines", []
        if caller is not None:
            sql, args = sql + " WHERE owner_user_id = ?", [caller.user_id]
        out = []
        for row in con.execute(sql + " ORDER BY name, id", args).fetchall():
            newest = _latest(con, row["id"])
            out.append({"id": row["id"], "name": row["name"], "version": newest["version"],
                        "n_nodes": len(json.loads(newest["graph_json"])["nodes"]),
                        "created_at": row["created_at"], "updated_at": newest["created_at"]})
    finally:
        con.close()
    return {"ok": True, "pipelines": out}


def get_pipeline(platform_path, pipeline_id, version=None, *, caller=None):
    """One pipeline with the graph of a version (no version means the newest). What is not the caller's answers like what does not
    exist."""
    con = store.connect_state(platform_path)
    try:
        _table(con)
        row = _mine(con, pipeline_id, caller)
        if row is None:
            return {"ok": False, "found": False, "message": _not_found(pipeline_id)}
        numbers = [r["version"] for r in con.execute("SELECT version FROM pipeline_versions WHERE pipeline_id = ? ORDER BY version",
                                                     (row["id"],)).fetchall()]
        want = numbers[-1] if version is None else version
        if isinstance(want, bool) or want not in numbers:
            return {"ok": False, "found": False,
                    "message": "這個組合沒有版本 %s；已有的版本：%s (pipeline %s has no version %s; the versions are: %s)"
                               % (version, "、".join(map(str, numbers)), row["name"], version, ", ".join(map(str, numbers)))}
        picked = con.execute("SELECT * FROM pipeline_versions WHERE pipeline_id = ? AND version = ?", (row["id"], want)).fetchone()
    finally:
        con.close()
    return {"ok": True, "found": True, "id": row["id"], "name": row["name"], "version": want, "versions": numbers,
            "graph": json.loads(picked["graph_json"]), "created_at": row["created_at"]}


def render_pipeline(platform_path, pipeline_id, version=None, *, caller=None, data=None):
    """The text of the Nextflow project for one version: main.nf, modules.json and nextflow.config, as strings. Nothing is written
    and nothing is started."""
    got = get_pipeline(platform_path, pipeline_id, version, caller=caller)
    if not got["ok"]:
        return got
    try:
        out = compose.render(got["graph"], got["name"], got["version"], data)
    except ValueError:
        return _no("這個版本的圖現在轉不出專案檔；請存一個修正後的新版本 "
                   "(this version of the graph can no longer be turned into a project; save a corrected version)")
    return {"ok": True, "name": got["name"], "version": got["version"], "files": out["files"], "open_inputs": out["open_inputs"]}


def _pack(files):
    """A zip of {path: text} as bytes, the same bytes every time: entries sorted by path, time fixed at 1980-01-01, all deflated.
    Written here (struct and zlib) because this module keeps clear of the packaging libraries by its own test."""
    body, central = b"", b""
    for path in sorted(files):
        name = path.encode("utf-8")
        raw = files[path].encode("utf-8")
        packer = zlib.compressobj(9, zlib.DEFLATED, -15)
        data = packer.compress(raw) + packer.flush()
        flag = 0x0800 if len(name) != len(path) else 0
        head = struct.pack("<HHHHHIIIHH", 20, flag, 8, 0, 0x21, zlib.crc32(raw) & 0xFFFFFFFF, len(data), len(raw), len(name), 0)
        central += (b"PK\x01\x02" + struct.pack("<H", 20) + head + struct.pack("<HHHII", 0, 0, 0, 0o100644 << 16, len(body)) + name)
        body += b"PK\x03\x04" + head + name + data
    end = struct.pack("<HHHHIIH", 0, 0, len(files), len(files), len(central), len(body), 0)
    return body + central + b"PK\x05\x06" + end


def _readme(name, version, open_inputs):
    lines = ["%s v%d: a Nextflow project exported from Agentic-Bioflow. Unpack it and start it from this folder with the Nextflow tool." % (name, version)]
    if open_inputs:
        lines.append("Inputs left open, fill these in yourself:")
        for item in open_inputs:
            lines.append("- node %s input %s: %s" % (item["node"], item["input"], ", ".join(item["names"])))
    else:
        lines.append("No input is left open.")
    return "\n".join(lines) + "\n"


def export_pipeline(platform_path, pipeline_id, version=None, *, caller=None, data=None, sources=None):
    """One version of the caller's pipeline (no version means the newest) as a zip: main.nf, modules.json, nextflow.config, a short
    README.txt and the nf-core module files it uses. Returns the bytes; nothing is written to disk and nothing is started. The kept
    check result, if any, rides along as `validation` and never blocks the export."""
    got = get_pipeline(platform_path, pipeline_id, version, caller=caller)
    if not got["ok"]:
        return _no(got["message"])
    rendered = render_pipeline(platform_path, pipeline_id, got["version"], caller=caller, data=data)
    if not rendered["ok"]:
        return rendered
    files = dict(rendered["files"])
    try:
        listed = json.loads(files["modules.json"])["repos"]
        paths = sorted({p for repo in listed.values() for p in repo["modules"]["nf-core"]})
        files.update(module_sources.files_for(paths, module_sources.load(data=data) if sources is None else sources))
    except (ValueError, KeyError) as e:
        why = str(e) if isinstance(e, ValueError) else "module list"
        return _no("這個版本用到的模組檔帶不進 zip：%s；請換成別的模組，或請平台維護者補上 "
                   "(a module file cannot be put in the zip: %s; use another module or ask the platform maintainer)" % (why, why))
    files["README.txt"] = _readme(got["name"], got["version"], rendered["open_inputs"])
    size = sum(len(text.encode("utf-8")) for text in files.values())
    if size > pipeline_launch.MAX_BYTES:
        return _no("專案檔全部共 %d 位元組，超過上限 %d；請減少節點 (the project files are %d bytes together, more than the limit of %d; "
                   "use fewer nodes)" % (size, pipeline_launch.MAX_BYTES, size, pipeline_launch.MAX_BYTES))
    if len(files) > pipeline_launch.MAX_FILES:
        return _no("專案有 %d 個檔案，超過上限 %d；請減少節點 (the project has %d files, more than the limit of %d; use fewer nodes)"
                   % (len(files), pipeline_launch.MAX_FILES, len(files), pipeline_launch.MAX_FILES))
    kept = get_validation(platform_path, pipeline_id, got["version"], caller=caller, data=data)
    return {"ok": True, "filename": "%s-v%d.zip" % (got["name"], got["version"]), "zip": _pack(files), "files": sorted(files),
            "open_inputs": rendered["open_inputs"], "validation": kept["validation"] if kept["ok"] else None}


def validate_pipeline(platform_path, pipeline_id, version=None, *, caller=None, data=None, clock=time.time):
    """Check one version of a pipeline (no version means the newest) and keep the result as the latest one of that version. The
    outer `ok` says the call worked; `validation.ok` says the graph has no error. Only the platform's own database is written."""
    got = get_pipeline(platform_path, pipeline_id, version, caller=caller)
    if not got["ok"]:
        return got
    result = checks.validate(got["graph"], data)
    now = clock()
    con = store.connect_state(platform_path)
    try:
        _table(con)
        con.execute("INSERT OR REPLACE INTO pipeline_validations (pipeline_id, version, graph_sha256, %s, result_json, "
                    "validated_at) VALUES (?, ?, ?, ?, ?, ?)" % checks.SHA_FIELD,
                    (got["id"], got["version"], hashlib.sha256(compose.graph_json(got["graph"]).encode("utf-8")).hexdigest(),
                     result[checks.SHA_FIELD] or "", json.dumps(result, sort_keys=True, ensure_ascii=False), now))
        con.commit()
    except sqlite3.Error:
        con.rollback()
        return _no("驗證結果沒有存成功；請稍後再試一次 (the check result was not saved; try again in a moment)")
    finally:
        con.close()
    return {"ok": True, "id": got["id"], "name": got["name"], "version": got["version"],
            "validation": dict(result, validated_at=now, stale=False)}


def get_validation(platform_path, pipeline_id, version=None, *, caller=None, data=None):
    """The kept result of the latest check of one version, or `validation: None` when it was never checked. `stale` is True when
    the module list of now is not the one the check was made against; nothing is checked again here."""
    got = get_pipeline(platform_path, pipeline_id, version, caller=caller)
    if not got["ok"]:
        return got
    con = store.connect_state(platform_path)
    try:
        _table(con)
        row = con.execute("SELECT * FROM pipeline_validations WHERE pipeline_id = ? AND version = ?",
                          (got["id"], got["version"])).fetchone()
    finally:
        con.close()
    out = {"ok": True, "id": got["id"], "name": got["name"], "version": got["version"], "validation": None}
    if row is not None:
        out["validation"] = dict(json.loads(row["result_json"]), validated_at=row["validated_at"],
                                 stale=checks.current_sha(data) != row[checks.SHA_FIELD])
    return out

