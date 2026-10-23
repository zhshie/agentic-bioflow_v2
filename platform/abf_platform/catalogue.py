# Nothing existing: the snapshot is nf-core's own module metadata, flattened; the repository has no module catalogue.
"""The list of nf-core modules, as one committed JSON file, with load, search and describe.

The file is made from `modules/nf-core/**/meta.yml` of one pinned nf-core/modules commit. Nothing
here edits the modules; it only reads and flattens them. Only the standard library is needed at
run time; PyYAML is imported inside the snapshot command alone.
"""
import functools
import json
import re
import sys
from pathlib import Path

SOURCE = "nf-core/modules"
DEFAULT_PATH = Path(__file__).parent / "data" / "nf-core-modules.json"
_CLUSTER_PATH = re.compile(r"(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/")


def _mask(value):
    if isinstance(value, str):
        return _CLUSTER_PATH.sub("<path>/", value)
    return value


def _single(item):
    """(key, value) of a one-key mapping whose value is a mapping, else None."""
    if isinstance(item, dict) and len(item) == 1:
        key, val = next(iter(item.items()))
        if isinstance(val, dict):
            return key, val
    return None


def _entry(channel, key, val):
    return {"channel": _mask(channel), "name": _mask(str(key)), "type": _mask(val.get("type")),
            "pattern": _mask(val.get("pattern"))}


def _tools(meta):
    out = []
    raw = meta.get("tools")
    for item in raw if isinstance(raw, list) else []:
        one = _single(item)
        if one is None:
            continue
        key, val = one
        lic = val.get("licence")
        if isinstance(lic, str):
            lic = [lic]
        elif isinstance(lic, list):
            lic = [x for x in lic if isinstance(x, str)]
        else:
            lic = []
        out.append({"name": _mask(str(key)), "homepage": _mask(val.get("homepage")), "licence": [_mask(x) for x in lic]})
    return out


def _inputs(meta):
    out = []
    raw = meta.get("input")
    for i, item in enumerate(raw if isinstance(raw, list) else []):
        for sub in item if isinstance(item, list) else [item]:
            one = _single(sub)
            if one:
                out.append(_entry(i, *one))
    return out


def _outputs(meta):
    out = []
    raw = meta.get("output")
    if isinstance(raw, dict):
        for channel, tuples in raw.items():
            if str(channel).startswith("versions"):
                continue
            for tup in tuples if isinstance(tuples, list) else []:
                for sub in tup if isinstance(tup, list) else [tup]:
                    one = _single(sub)
                    if one:
                        out.append(_entry(channel, *one))
    elif isinstance(raw, list):
        for item in raw:
            one = _single(item)
            if one and not str(one[0]).startswith("versions"):
                out.append(_entry(one[0], *one))
    return out


def flatten(path, meta):
    name = meta.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("meta.yml has no name")
    desc = meta.get("description")
    keywords = meta.get("keywords")
    return {
        "name": _mask(name),
        "path": _mask(path),
        "description": _mask(" ".join(desc.split())) if isinstance(desc, str) else "",
        "keywords": [_mask(k) for k in keywords if isinstance(k, str)] if isinstance(keywords, list) else [],
        "tools": _tools(meta),
        "inputs": _inputs(meta),
        "outputs": _outputs(meta),
    }


def build_snapshot(items, sha):
    modules, errors = [], []
    for path, meta in items:
        if isinstance(meta, dict):
            try:
                modules.append(flatten(path, meta))
            except Exception as e:  # any bad module is recorded, never fatal
                errors.append({"path": path, "reason": str(e)})
        else:
            errors.append({"path": path, "reason": meta if isinstance(meta, str) else "meta.yml is not a mapping"})
    modules.sort(key=lambda m: (m["name"], m["path"]))
    errors.sort(key=lambda e: e["path"])
    return {"source": SOURCE, "sha": sha, "count": len(modules), "modules": modules, "errors": errors}


def dumps(snapshot):
    return json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n"


def _load_file(path):
    path = Path(path)
    if not path.is_file():
        return {"source": SOURCE, "sha": None, "count": 0, "modules": [],
                "errors": [{"path": "", "reason": "模組目錄檔不存在：%s (the module catalogue file is missing)" % path}]}
    return json.loads(path.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def _load_default():
    return _load_file(DEFAULT_PATH)


def load(path=None):
    return _load_default() if path is None else _load_file(path)


def search(q, data=None):
    data = load() if data is None else data
    q = (q or "").strip().lower()
    if not q:
        return []
    hits = []
    for m in data.get("modules", []):
        name = m["name"].lower()
        if name == q:
            score = 0
        elif name.startswith(q):
            score = 1
        elif q in name:
            score = 2
        elif any(q in k.lower() for k in m.get("keywords", [])):
            score = 3
        elif q in m.get("description", "").lower():
            score = 4
        else:
            continue
        hits.append((score, m["name"], m))
    hits.sort(key=lambda h: (h[0], h[1]))
    return [{"name": m["name"], "path": m["path"], "description": m["description"]} for _, _, m in hits[:50]]


def describe(name, data=None):
    data = load() if data is None else data
    want = (name or "").lower()
    if want:
        for m in data.get("modules", []):
            if m["name"].lower() == want:
                return {"found": True, "sha": data.get("sha"), **m}
    return {"found": False, "name": name,
            "message": "找不到模組 %s；用 search 找相近的名字 (no module named %s; use search to find a similar name)" % (name, name)}


def _snapshot_command(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="python -m abf_platform.catalogue snapshot")
    ap.add_argument("--modules", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        import yaml
    except ImportError:
        print("需要 PyYAML：python3 -m pip install pyyaml (PyYAML is needed to read meta.yml)")
        return 2
    root = Path(args.modules) / "modules" / "nf-core"
    items = []
    for f in sorted(root.glob("**/meta.yml")):
        rel = f.parent.relative_to(root).as_posix()
        try:
            meta = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            meta = (str(e).strip().splitlines() or ["meta.yml could not be read"])[0]
        items.append((rel, meta))
    Path(args.out).write_text(dumps(build_snapshot(items, args.sha)), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        sys.exit(_snapshot_command(sys.argv[2:]))
    print("usage: python -m abf_platform.catalogue snapshot --modules <checkout> --sha <sha> --out <file>")
    sys.exit(2)
