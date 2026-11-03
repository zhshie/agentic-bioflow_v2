# Nothing existing: Seqera has no module catalogue; this is a thin door onto our own abf_platform.catalogue (spec canvas-mcp-read).
"""The module catalogue as actions (find_module, describe_module). Thin: the search and the description are
`abf_platform.catalogue`; this only gives the answer its shape. Not exported by `actions/__init__`, like `actions.pipelines`.
The catalogue is public data, so there is no caller and no owner filter. Nothing is written."""
from .. import catalogue

_HINT = "沒找到；換個關鍵字，或直接用工具名，例如 fastqc (nothing found; try another keyword or the tool's own name, for example fastqc)"


def find_module(q, *, data=None):
    """{sha, count, modules}; each module has name, path, description and the inputs and outputs of the same catalogue entry.
    No hit: count 0, modules [] and a one-line hint."""
    data = catalogue.load() if data is None else data
    by_name = {m["name"]: m for m in data.get("modules", [])}
    modules = []
    for hit in catalogue.search(q, data):
        full = by_name.get(hit["name"], {})
        modules.append(dict(hit, inputs=full.get("inputs", []), outputs=full.get("outputs", [])))
    out = {"sha": data.get("sha"), "count": len(modules), "modules": modules}
    if not modules:
        out["hint"] = _HINT
    return out


def describe_module(name, *, data=None):
    """The entry of one module (found true), or found false naming the input and pointing at find_module."""
    got = catalogue.describe(name, data)
    if got.get("found"):
        return got
    return {"found": False, "name": name,
            "message": "找不到模組 %s；用 find_module 找相近的名字 (no module named %s; use find_module to find a similar name)" % (name, name)}
