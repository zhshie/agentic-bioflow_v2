# Nothing existing: nf-core publishes module metadata but no checker for a canvas graph; the nf-core command line tools need a checked-out project and start programs, which the platform host must not do.
"""Static checks of a composed pipeline (spec 017c): does each edge join channels that fit, is every input wired, do two nodes
end up with one process name, and does the graph still fit the catalogue of today. A pure function of a canonical graph and a
catalogue: no database, no network, no file, no program started. The same graph and catalogue always give the same list.

A finding is {node, channel, code, severity, message}. `ok` is True when no finding is an error. Warnings are only shown."""
import re

from . import catalogue, compose

CHECKS = ["static"]
SHA_FIELD = "catalogue_sha"        # the key of a result, and the name of the column that keeps it
_CLASS = {"map": "meta", "file": "path", "directory": "path", "string": "val", "boolean": "val", "integer": "val", "float": "val"}
_PLAIN = re.compile(r"^[A-Za-z0-9._-]+$")


def _kind(record):
    return _CLASS.get(record.get("type"), "any")


def _channel(records):
    """(has_meta, set of classes) of the records of one channel, in the catalogue's order."""
    kinds = [_kind(r) for r in records]
    has_meta = bool(kinds) and kinds[0] == "meta"
    return has_meta, set(kinds[1:] if has_meta else kinds)


def _records(record, side, channel):
    return [r for r in record.get(side, []) if r["channel"] == channel]


def _disjoint(a, b):
    """Both sets have something and share nothing, with no 'any' to bridge them."""
    return bool(a) and bool(b) and not (a & b) and "any" not in a and "any" not in b


def _type_mismatch(a, b):
    return bool(a) != bool(b) or _disjoint(a, b)


def _classes(classes):
    return "+".join(sorted(classes)) or "none"


def _expand(pattern):
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    out = []
    for part in m.group(1).split(","):
        out += _expand(pattern[:m.start()] + part + pattern[m.end():])
    return out


def _extensions(pattern):
    """Set of final extensions a file pattern names, or None when it cannot be read as plain extensions."""
    found = set()
    for text in _expand(pattern):
        text = text.lstrip("*._")
        if not text or not _PLAIN.match(text):
            return None
        found.add(text.rsplit(".", 1)[-1].lower())
    return found


def _lone_pattern(records):
    """The pattern of the one file-class record of a channel; None when there are several or none, or it has no pattern."""
    files = [r for r in records if _kind(r) == "path"]
    if len(files) != 1 or not files[0].get("pattern"):
        return None
    return files[0]["pattern"]


def _finding(node, channel, code, severity, message):
    return {"node": node, "channel": channel, "code": code, "severity": severity, "message": message}


def _order_key(f):
    ch = f["channel"]
    ck = (0, 0, "") if ch is None else (1, ch, "") if isinstance(ch, int) else (2, 0, str(ch))
    return (0 if f["severity"] == "error" else 1, f["node"] or "", ck, f["code"], f["message"])


def _side(has_meta):
    if has_meta:
        return "是 [meta, ...] 的 tuple", "is a [meta, ...] tuple"
    return "是沒有 meta 的單一值", "is a single value with no meta"


def _edge_findings(e, records):
    src, out, dst, inp = e["from"]["node"], e["from"]["output"], e["to"]["node"], e["to"]["input"]
    s, d = "%s.%s" % (src, out), "%s.%d" % (dst, inp)
    outs = _records(records[src], "outputs", out)
    ins = _records(records[dst], "inputs", inp)
    (ma, ca), (mb, cb) = _channel(outs), _channel(ins)
    found = []
    if ma != mb:
        za, ea = _side(ma)
        zb, eb = _side(mb)
        found.append(_finding(dst, inp, "META_MISMATCH", "error",
                              "邊 %s → %s：輸出%s，輸入%s，兩端的 meta 對不上；中間需要一個轉換節點，或改接別的通道 "
                              "(edge %s -> %s: the output %s but the input %s, so the meta does not match; "
                              "add a conversion node or wire another channel)" % (s, d, za, zb, s, d, ea, eb)))
    elif _type_mismatch(ca, cb):
        found.append(_finding(dst, inp, "TYPE_MISMATCH", "error",
                              "邊 %s → %s：輸出的類型是 %s，輸入的類型是 %s，型別對不上；改接別的通道，或中間加一個轉換節點 "
                              "(edge %s -> %s: the output carries %s but the input expects %s, so the types do not match; "
                              "wire another channel or add a conversion node)"
                              % (s, d, _classes(ca), _classes(cb), s, d, _classes(ca), _classes(cb))))
    pa, pb = _lone_pattern(outs), _lone_pattern(ins)
    if pa and pb:
        xa, xb = _extensions(pa), _extensions(pb)
        if xa and xb and not (xa & xb):
            found.append(_finding(dst, inp, "PATTERN_MISMATCH", "warning",
                                  "邊 %s → %s：輸出的檔名樣式 %s 與輸入的 %s 沒有共同的副檔名，可能接錯了；確認這兩個通道是否該相接 "
                                  "(edge %s -> %s: the output file pattern %s and the input pattern %s share no extension, "
                                  "so the edge may be wrong; check that these two channels belong together)" % (s, d, pa, pb, s, d, pa, pb)))
    return found


def _incompatible(x, y):
    return x[0] != y[0] or _disjoint(x[1], y[1])


def _mixed(edges, records):
    feeds = {}
    for e in edges:
        feeds.setdefault((e["to"]["node"], e["to"]["input"]), []).append(e)
    found = []
    for (dst, inp), group in sorted(feeds.items()):
        sigs = [("%s.%s" % (e["from"]["node"], e["from"]["output"]),
                 _channel(_records(records[e["from"]["node"]], "outputs", e["from"]["output"]))) for e in group]
        pair = next(((x, y) for i, x in enumerate(sigs) for y in sigs[i + 1:] if _incompatible(x[1], y[1])), None)
        if pair:
            d = "%s.%d" % (dst, inp)
            found.append(_finding(dst, inp, "MIXED_SOURCES", "error",
                                  "輸入 %s 同時接了不相容的來源 %s 與 %s，混合後內容不一致；同一個輸入只接類型相同的來源，或拆成不同的輸入 "
                                  "(input %s receives the incompatible sources %s and %s, which cannot be mixed; "
                                  "wire only sources of the same kind to one input or use separate inputs)"
                                  % (d, pair[0][0], pair[1][0], d, pair[0][0], pair[1][0])))
    return found


def _required(records, node, channel):
    """True when a non-meta record of this input channel says `optional: false`. Meta records and records with no `optional` field
    do not make a channel required."""
    return any(r.get("optional") is False and r.get("type") != "map" for r in _records(records[node], "inputs", channel))


def _unwired(open_inputs, edges, records):
    fed = {e["to"]["node"] for e in edges}
    found = []
    for o in open_inputs:
        n, k, names = o["node"], o["input"], ", ".join(o["names"])
        if n in fed:
            msg = ("節點 %s 少了一個輸入：輸入 %d 沒有接線，輸入名：%s；確認它是否可以省略，不能省略就接上線 "
                   "(node %s is missing an input: input %d is not wired, names: %s; check whether it may be left out, otherwise wire it)"
                   % (n, k, names, n, k, names))
        else:
            msg = ("節點 %s 的輸入 %d 沒有接線，輸入名：%s；這個節點是入口，送出時要由樣本表或參數供應 "
                   "(input %d of node %s is not wired, names: %s; this node is an entry point, "
                   "so the sample sheet or parameters must supply it at launch)" % (n, k, names, k, n, names))
        severity = "error" if n in fed and _required(records, n, k) else "warning"
        found.append(_finding(n, k, "OPEN_INPUT", severity, msg))
    return found


def _same_names(canonical, records):
    """Nodes that would get one process name. Same rule as `compose.render`: the module's own name, or name_ID for a module used
    more than once."""
    per_module = {}
    for n in canonical["nodes"]:
        name = records[n["id"]]["name"]
        per_module[name] = per_module.get(name, 0) + 1
    calls = {}
    for n in sorted(canonical["nodes"], key=lambda n: n["id"]):
        rec = records[n["id"]]
        base = compose.process_name(rec)
        call = base if per_module[rec["name"]] == 1 else "%s_%s" % (base, n["id"].upper())
        calls.setdefault(call, []).append((n["id"], rec["path"]))
    found = []
    for call, who in sorted(calls.items()):
        if len({path for _, path in who}) > 1:
            ids = [i for i, _ in who]
            found.append(_finding(ids[0], None, "DUPLICATE_PROCESS", "error",
                                  "節點 %s 會產生同名的流程名 %s，執行時會互相覆蓋；把其中一個換成別的模組，或改節點 id "
                                  "(nodes %s would get the same process name %s, so they would overwrite each other; "
                                  "use a different module or rename a node id)" % ("、".join(ids), call, ", ".join(ids), call)))
    return found


def current_sha(data=None):
    """The sha of the module list a check is made against now."""
    return (catalogue.load() if data is None else data).get("sha")


def validate(canonical, data=None):
    """{"ok", "checks", "catalogue_sha", "findings", "open_inputs"} for a canonical graph (the output of `compose.normalize`).
    The graph is first checked against the catalogue of now; when it no longer fits, only that is reported."""
    data = catalogue.load() if data is None else data
    _, problems = compose.normalize(canonical, data)
    findings, opened = [], []
    if problems:
        findings = [_finding(None, None, "GRAPH_STALE", "error", p) for p in problems]
    else:
        records = {n["id"]: catalogue.describe(n["module"], data) for n in canonical["nodes"]}
        for e in canonical["edges"]:
            findings += _edge_findings(e, records)
        findings += _mixed(canonical["edges"], records)
        opened = compose.render(canonical, "check", 1, data)["open_inputs"]
        findings += _unwired(opened, canonical["edges"], records)
        findings += _same_names(canonical, records)
    findings.sort(key=_order_key)
    return {"ok": not any(f["severity"] == "error" for f in findings), "checks": list(CHECKS),
            SHA_FIELD: data.get("sha"), "findings": findings, "open_inputs": opened}
