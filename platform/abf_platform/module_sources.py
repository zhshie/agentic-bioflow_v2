# Nothing existing: nf-core/modules keeps the module scripts only inside its git repository, and Nextflow does not fetch a local script's includes; the platform needs the exact files of the pinned commit without going to the network.
"""The files of every nf-core module, as one committed gzip file (spec 017d), made from the same nf-core/modules commit as the catalogue.

A composed pipeline's `main.nf` includes './modules/nf-core/<path>/main', so those files must exist in the project folder of the run.
The platform takes them from here when it builds a launch, so building a launch needs no network and the site only writes files.
Per module the file keeps `main.nf` and the text files of `templates/` and `resources/`; `meta.yml`, `environment.yml` and `tests/` are
not kept. A module the project cannot carry (a `bin/` folder, a binary file, an odd file name, a cluster path in a file, a file over
200,000 characters) is kept as {"files": {}, "unsupported": <the reason>}. Only the standard library; nothing here opens a connection:
`snapshot` reads a folder that was cloned beforehand.
"""
import functools
import gzip
import io
import json
import re
import sys
from pathlib import Path

from . import catalogue

SOURCE = "nf-core/modules"
DEFAULT_PATH = Path(__file__).parent / "data" / "nf-core-module-sources.json.gz"
MAX_FILE = 200000
_FILE = re.compile(r"^(main\.nf|templates/[A-Za-z0-9_.-]+|resources/[A-Za-z0-9_.-]+)\Z")
_KEEP = ("templates", "resources")


def _gzip(data):
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as g:
        g.write(data)
    return buf.getvalue()


def _module(folder):
    """{"files": {...}, "unsupported": reason or None} of one module folder (the one that holds main.nf)."""
    if (folder / "bin").exists():
        return {"files": {}, "unsupported": "需要 bin/ 目錄，目前無法帶到站台 (the module has a bin/ folder, which the project cannot carry yet)"}
    wanted = [folder / "main.nf"]
    for sub in _KEEP:
        d = folder / sub
        if d.is_dir():
            wanted += sorted(p for p in d.rglob("*") if p.is_file())
    files = {}
    for p in wanted:
        rel = p.relative_to(folder).as_posix()
        if not _FILE.match(rel):
            return {"files": {}, "unsupported": "檔名 %s 的形狀不能帶到站台 (the file name %s has a shape the project cannot carry)" % (rel, rel)}
        raw = p.read_bytes()
        try:
            if b"\x00" in raw:
                raise ValueError
            text = raw.decode("utf-8")
        except ValueError:
            return {"files": {}, "unsupported": "%s 是二進位檔，目前無法帶到站台 (%s is a binary file)" % (rel, rel)}
        if len(text) > MAX_FILE:
            return {"files": {}, "unsupported": "%s 超過 %d 個字元 (%s is longer than %d characters)" % (rel, MAX_FILE, rel, MAX_FILE)}
        if catalogue._CLUSTER_PATH.search(text):
            return {"files": {}, "unsupported": "%s 含有叢集路徑，改了就不再是上游原檔 (%s holds a cluster path; changing it would no longer be the upstream file)" % (rel, rel)}
        files[rel] = text
    return {"files": files, "unsupported": None}


def build_snapshot(root, sha):
    """The snapshot dict of a checkout's modules/nf-core folder (`root`)."""
    root = Path(root)
    modules = {}
    for main in sorted(root.glob("**/main.nf")):
        rel = main.parent.relative_to(root).as_posix()
        if "/tests/" in "/" + rel + "/":
            continue
        modules[rel] = _module(main.parent)
    return {"source": SOURCE, "sha": sha, "modules": modules}


def dumps(snapshot):
    """The bytes of the committed file: sorted keys, no ASCII escapes, gzip with mtime 0, so one sha always gives the same bytes."""
    return _gzip(json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _read(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError("模組檔案資料不存在：%s (the module files data is missing)" % path.name)
    return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))


@functools.lru_cache(maxsize=None)
def _default():
    return _read(DEFAULT_PATH)


def load(path=None, data=None):
    """The module files data (the committed one when no path is given). Its sha must be the catalogue's sha (`data`, the catalogue of
    now when none is given): the two files are of one nf-core/modules commit or the project would not match the graph."""
    sources = _default() if path is None else _read(path)
    want = (catalogue.load() if data is None else data).get("sha")
    if sources.get("sha") != want:
        raise ValueError("模組檔案資料的 sha（%s）不是目錄的 sha（%s） (the module files data is of another nf-core/modules commit than the catalogue)"
                         % (sources.get("sha"), want))
    return sources


def files_for(paths, sources=None):
    """{"modules/nf-core/<path>/<file>": text} for these module paths. ValueError naming the module that is missing or unsupported."""
    sources = load() if sources is None else sources
    out = {}
    for path in sorted(set(paths)):
        m = (sources.get("modules") or {}).get(path)
        if m is None:
            raise ValueError("模組 %s 沒有檔案資料；換成別的模組 (no files for module %s; use another module)" % (path, path))
        if m.get("unsupported"):
            raise ValueError("模組 %s 不能帶到站台：%s；換成別的模組 (module %s cannot be carried; use another module)"
                             % (path, m["unsupported"], path))
        for rel, text in m["files"].items():
            out["modules/nf-core/%s/%s" % (path, rel)] = text
    return out


def _snapshot_command(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="python -m abf_platform.module_sources snapshot")
    ap.add_argument("--modules", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    root = Path(args.modules) / "modules" / "nf-core"
    Path(args.out).write_bytes(dumps(build_snapshot(root, args.sha)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        sys.exit(_snapshot_command(sys.argv[2:]))
    print("usage: python -m abf_platform.module_sources snapshot --modules <checkout> --sha <sha> --out <file>")
    sys.exit(2)
