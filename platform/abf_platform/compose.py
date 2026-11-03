# Nothing existing: nf-core has no library that turns a canvas graph into a pipeline project; nf-core/tools installs modules into a checkout, which the platform host must not run.
"""Composed pipelines (spec 017b): a graph of nf-core modules, checked (`normalize`) and turned into the text of a Nextflow project
(`render`). Both are pure functions: they read the module catalogue they are given, return strings and nothing else - no database, no
network, no file written, no program started. The same canonical graph, name and version always give the same text.

A graph is {"nodes": [{id, module, sha?, params?}], "edges": [{from: {node, output}, to: {node, input}}]}. A node is one module of the
catalogue; an edge joins an output channel of one node to an input channel number of another. Types are not compared here."""
import heapq
import json
import re
import unicodedata

from . import catalogue

MAX_NODES = 200
MAX_EDGES = 1000
MAX_BYTES = 256 * 1024
MAX_VALUE = 1000
REPO_URL = "https://github.com/nf-core/modules.git"

_ID = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")
_NAME = re.compile(r"^[a-z][a-z0-9-]{0,39}\Z")
_KEY = re.compile(r"^ext\.(args[2-9]?|prefix)\Z")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
_TOP = ("nodes", "edges")
_TOO_BIG = "圖太大，上限 256 KiB；請拆小 (the graph is too large; the limit is 256 KiB, make it smaller)"


def graph_json(canonical):
    """The one text a canonical graph is kept as."""
    return json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def process_name(module):
    """The Nextflow process name of a catalogue record: its path with / turned into _, in capitals. The path, not the name: 18 names do
    not match their path (STRdust lives in strdust)."""
    return module["path"].replace("/", "_").upper()


def _bad_value(value):
    """(Chinese, English) reason a parameter value cannot go into a config file, or None."""
    if not isinstance(value, str):
        return "值必須是字串", "the value must be a string"
    if len(value) > MAX_VALUE:
        return "值最長 %d 個字元" % MAX_VALUE, "the value may be at most %d characters" % MAX_VALUE
    if any(unicodedata.category(c) in ("Cc", "Zl", "Zp") for c in value):
        return "值不能含換行或其他控制字元", "the value may not hold a line break or other control character"
    return None


def _check_params(node_id, params, problems):
    if not isinstance(params, dict):
        problems.append("節點 %s 的 params 必須是物件 (params of node %s must be an object)" % (node_id, node_id))
        return
    for key in params:
        if not isinstance(key, str) or not _KEY.match(key):
            problems.append("節點 %s 的參數 %s 不能用；只收 ext.args、ext.args2 到 ext.args9、ext.prefix "
                            "(node %s: parameter %s is not accepted; only ext.args, ext.args2 to ext.args9 and ext.prefix are)"
                            % (node_id, key, node_id, key))
            continue
        why = _bad_value(params[key])
        if why:
            problems.append("節點 %s 的參數 %s：%s (node %s, parameter %s: %s)" % (node_id, key, why[0], node_id, key, why[1]))


def _outputs(record):
    seen = []
    for o in record.get("outputs", []):
        if o["channel"] not in seen:
            seen.append(o["channel"])
    return seen


def _inputs(record):
    """{channel number: [input names]} in the catalogue's order."""
    out = {}
    for i in record.get("inputs", []):
        out.setdefault(i["channel"], []).append(i["name"])
    return out


def normalize(graph, data=None):
    """(canonical, problems). Any problem means canonical is None. Each problem says in Chinese and in English what is wrong and what
    to do."""
    data = catalogue.load() if data is None else data
    problems = []
    if not isinstance(graph, dict):
        return None, ["圖必須是物件，含 nodes 與 edges (the graph must be an object with nodes and edges)"]
    for key in graph:
        if key not in _TOP:
            problems.append("圖的頂層不能有 %s；只收 nodes 與 edges (the graph may not hold %s at the top; only nodes and edges are accepted)"
                            % (key, key))
    try:
        size = len(graph_json(graph).encode("utf-8"))
    except (TypeError, ValueError):
        return None, problems + ["圖必須是 JSON 能表示的內容 (the graph must be plain JSON data)"]
    if size > MAX_BYTES:
        return None, problems + [_TOO_BIG]
    nodes, edges = graph.get("nodes"), graph.get("edges", [])
    if not isinstance(nodes, list):
        problems.append("nodes 必須是清單 (nodes must be a list)")
        nodes = []
    if not isinstance(edges, list):
        problems.append("edges 必須是清單 (edges must be a list)")
        edges = []
    if not nodes and not problems:
        problems.append("圖裡至少要有一個節點 (the graph needs at least one node)")
    if len(nodes) > MAX_NODES:
        problems.append("節點太多：%d 個，上限 %d；請拆成較小的圖 (too many nodes: %d, the limit is %d; split the graph)"
                        % (len(nodes), MAX_NODES, len(nodes), MAX_NODES))
    if len(edges) > MAX_EDGES:
        problems.append("邊太多：%d 條，上限 %d；請減少連線 (too many edges: %d, the limit is %d; remove some)"
                        % (len(edges), MAX_EDGES, len(edges), MAX_EDGES))
    if len(nodes) > MAX_NODES or len(edges) > MAX_EDGES:
        return None, problems

    snapshot_sha = data.get("sha")
    good = {}                               # id -> (canonical node, catalogue record)
    seen = set()
    for n in nodes:
        if not isinstance(n, dict):
            problems.append("每個節點都必須是物件 (every node must be an object)")
            continue
        nid = n.get("id")
        label = nid if isinstance(nid, str) else repr(nid)
        extra = [k for k in n if k not in ("id", "module", "sha", "params")]
        if extra:
            problems.append("節點 %s 有不認得的欄位：%s (node %s has fields that are not accepted: %s)"
                            % (label, "、".join(map(str, extra)), label, ", ".join(map(str, extra))))
        ok = not extra
        if not isinstance(nid, str) or not _ID.match(nid):
            problems.append("節點 id %s 不合法；用小寫英文開頭，只含小寫英數與底線，最長 32 字 "
                            "(node id %s is not valid; start with a lowercase letter, then lowercase letters, digits or _, at most 32)"
                            % (label, label))
            ok = False
        elif nid in seen:
            problems.append("節點 id %s 重複了，請改成不同的 id (node id %s is used twice; give each node its own id)" % (nid, nid))
            ok = False
        if isinstance(nid, str):
            seen.add(nid)
        module = n.get("module")
        found = catalogue.describe(module, data) if isinstance(module, str) else {"found": False}
        if not found.get("found"):
            problems.append("節點 %s 的模組 %s 不在目錄裡；用 search 找正確的名字 "
                            "(node %s: no module named %s in the catalogue; use search to find the name)"
                            % (label, module, label, module))
            ok = False
        sha = n.get("sha", snapshot_sha)
        if found.get("found") and sha != snapshot_sha:
            problems.append("節點 %s 的 sha 不是目前目錄快照的 sha %s；省略 sha 或改成它 "
                            "(node %s: the sha is not the catalogue snapshot's sha %s; leave it out or use that one)"
                            % (label, snapshot_sha, label, snapshot_sha))
            ok = False
        params = n.get("params", {})
        before = len(problems)
        _check_params(label, params, problems)
        if len(problems) > before:
            ok = False
        if ok:
            good[nid] = ({"id": nid, "module": found["name"], "sha": sha, "params": {k: params[k] for k in sorted(params)}}, found)

    seen_edges, kept = set(), []
    for e in edges:
        try:
            f, t = e["from"], e["to"]
            if set(e) != {"from", "to"} or set(f) != {"node", "output"} or set(t) != {"node", "input"}:
                raise KeyError
            src, out, dst, inp = f["node"], f["output"], t["node"], t["input"]
            if not all(isinstance(x, str) for x in (src, out, dst)):
                raise KeyError
        except (KeyError, TypeError):
            problems.append("每條邊要寫成 {from: {node, output}, to: {node, input}} "
                            "(every edge must look like {from: {node, output}, to: {node, input}})")
            continue
        label = "%s.%s" % (src, out)
        if isinstance(inp, bool) or not isinstance(inp, int):
            problems.append("邊 %s 的 to.input 必須是整數 (the to.input of edge %s must be a whole number)" % (label, label))
            continue
        key = (src, out, dst, inp)
        if key in seen_edges:
            problems.append("邊 %s 到 %s 的輸入 %s 重複了，請刪掉一條 (edge %s to input %s of %s appears twice; remove one)"
                            % (label, dst, inp, label, inp, dst))
            continue
        seen_edges.add(key)
        missing = [x for x in (src, dst) if x not in seen]
        for x in missing:
            problems.append("邊 %s 指向的節點 %s 不存在；改成圖裡有的節點 (edge %s refers to node %s, which is not in the graph)"
                            % (label, x, label, x))
        if missing:
            continue
        if src in good:
            record = good[src][1]
            outs = _outputs(record)
            if out not in outs:
                problems.append("邊 %s 沒有這個輸出通道，可選：%s (module %s has no output channel %s; choose one of: %s)"
                                % (label, "、".join(sorted(outs)), record["name"], out, ", ".join(sorted(outs))))
                continue
            if not _IDENT.match(out):
                problems.append("這個輸出通道名不能接線：%s (the output channel name %s cannot be wired)" % (out, out))
                continue
        if dst in good:
            record = good[dst][1]
            have = sorted(_inputs(record))
            if inp not in have:
                problems.append("邊 %s 接的輸入 %s 不存在，節點 %s 可選的輸入編號：%s "
                                "(module %s has no input channel %s; choose one of: %s)"
                                % (label, inp, dst, "、".join(map(str, have)), record["name"], inp, ", ".join(map(str, have))))
                continue
        kept.append({"from": {"node": src, "output": out}, "to": {"node": dst, "input": inp}})

    for e in kept:
        if e["from"]["node"] == e["to"]["node"]:
            problems.append("節點 %s 接到了自己；把線接到別的節點 (node %s is wired to itself; wire it to another node)"
                            % (e["from"]["node"], e["from"]["node"]))
    if not problems and _order(sorted(seen), kept) is None:
        problems.append("連線形成了環；流程不能繞回去，請刪掉回頭的那條線 "
                        "(the edges form a cycle; a pipeline cannot loop back, remove the edge that does)")
    if problems:
        return None, problems

    kept.sort(key=lambda e: (e["from"]["node"], e["from"]["output"], e["to"]["node"], e["to"]["input"]))
    canonical = {"nodes": [good[i][0] for i in sorted(good)], "edges": kept}
    if len(graph_json(canonical).encode("utf-8")) > MAX_BYTES:
        return None, [_TOO_BIG]
    return canonical, []


def _order(ids, edges):
    """Ids in an order where every source comes before its users; among those ready, the smallest id first. None when there is a cycle."""
    after = {i: set() for i in ids}
    waiting = {i: 0 for i in ids}
    for e in edges:
        a, b = e["from"]["node"], e["to"]["node"]
        if b not in after[a]:
            after[a].add(b)
            waiting[b] += 1
    ready = [i for i in ids if waiting[i] == 0]
    heapq.heapify(ready)
    out = []
    while ready:
        i = heapq.heappop(ready)
        out.append(i)
        for b in after[i]:
            waiting[b] -= 1
            if waiting[b] == 0:
                heapq.heappush(ready, b)
    return out if len(out) == len(ids) else None


def _quote(value):
    """A Groovy single-quoted string: backslash, quote and dollar are escaped. A value that is not a plain one-line string is refused."""
    why = _bad_value(value)
    if why:
        raise ValueError("%s (%s)" % why)
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$") + "'"


def render(canonical, name, version, data=None):
    """{"files": {"main.nf", "modules.json", "nextflow.config"}, "open_inputs": [...]}. `canonical` comes from `normalize`; a graph that
    does not fit the catalogue, or a parameter that is not a one-line string, is a ValueError (the checks run twice on purpose: the
    config file is run as a program)."""
    data = catalogue.load() if data is None else data
    if not isinstance(name, str) or not _NAME.match(name):
        raise ValueError("名稱不合法 (the pipeline name is not valid)")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("版本必須是 1 以上的整數 (the version must be a whole number, 1 or more)")
    nodes = {}
    for n in canonical["nodes"]:
        record = catalogue.describe(n["module"], data)
        if not record.get("found") or not _ID.match(n["id"]):
            raise ValueError("節點 %s 不在目錄裡 (node %s is not in the catalogue)" % (n["id"], n["id"]))
        for key, value in n.get("params", {}).items():
            if not _KEY.match(key):
                raise ValueError("參數 %s 不能用 (parameter %s is not accepted)" % (key, key))
            _quote(value)
        nodes[n["id"]] = (n, record)
    edges = sorted(canonical["edges"], key=lambda e: (e["from"]["node"], e["from"]["output"], e["to"]["node"], e["to"]["input"]))
    for e in edges:
        if e["from"]["node"] not in nodes or e["to"]["node"] not in nodes or not _IDENT.match(e["from"]["output"]):
            raise ValueError("邊指向不存在的節點或不能接線的通道 (an edge points at a missing node or a channel that cannot be wired)")
    order = _order(sorted(nodes), edges)
    if order is None:
        raise ValueError("連線形成了環 (the edges form a cycle)")

    per_module = {}
    for n, record in nodes.values():
        per_module[record["name"]] = per_module.get(record["name"], 0) + 1
    call = {}                               # id -> the name the workflow calls
    for nid, (n, record) in nodes.items():
        base = process_name(record)
        call[nid] = base if per_module[record["name"]] == 1 else "%s_%s" % (base, nid.upper())
    includes = sorted({(call[nid], process_name(record), record["path"]) for nid, (n, record) in nodes.items()})

    lines = ["#!/usr/bin/env nextflow",
             "// Generated by abf-platform compose (pipeline %s v%d); do not edit by hand." % (name, version), ""]
    for alias, base, path in includes:
        what = base if alias == base else "%s as %s" % (base, alias)
        lines.append("include { %s } from './modules/nf-core/%s/main'" % (what, path))
    lines += ["", "workflow {"]

    feeds = {}
    for e in edges:
        feeds.setdefault((e["to"]["node"], e["to"]["input"]), []).append("%s.out.%s" % (call[e["from"]["node"]], e["from"]["output"]))
    opened, calls, open_inputs = [], [], []
    for nid in order:
        n, record = nodes[nid]
        args = []
        for channel, names in sorted(_inputs(record).items()):
            sources = feeds.get((nid, channel))
            if sources:
                args.append(sources[0] + "".join(".mix(%s)" % s for s in sources[1:]))
            else:
                var = "ch_%s_in%d" % (nid, channel)
                args.append(var)
                opened.append((nid, channel, "    %s = Channel.empty()  // OPEN INPUT: %s input %d (%s)" % (var, nid, channel, ", ".join(names))))
                open_inputs.append({"node": nid, "input": channel, "names": list(names)})
        calls.append("    %s(%s)" % (call[nid], ", ".join(args)))
    opened.sort(key=lambda o: (o[0], o[1]))
    open_inputs.sort(key=lambda o: (o["node"], o["input"]))
    lines += [o[2] for o in opened] + calls + ["}"]
    main_nf = "\n".join(lines) + "\n"

    modules = {}
    for n, record in nodes.values():
        modules.setdefault(record["path"], {"branch": "master", "git_sha": n["sha"], "installed_by": ["modules"]})
    modules_json = json.dumps({"name": name, "homePage": "", "repos": {REPO_URL: {"modules": {"nf-core": modules}}}},
                              indent=4, sort_keys=True, ensure_ascii=False) + "\n"

    config = ["// Generated by abf-platform compose (pipeline %s v%d); do not edit by hand." % (name, version),
              "manifest {", "    name = %s" % _quote(name), "    version = '0.%d.0'" % version, "}"]
    tuned = [nid for nid in sorted(nodes) if nodes[nid][0].get("params")]
    if tuned:
        config += ["", "process {"]
        for nid in tuned:
            config.append("    withName: '%s' {" % call[nid])
            params = nodes[nid][0]["params"]
            config += ["        %s = %s" % (k, _quote(params[k])) for k in sorted(params)]
            config.append("    }")
        config.append("}")
    return {"files": {"main.nf": main_nf, "modules.json": modules_json, "nextflow.config": "\n".join(config) + "\n"},
            "open_inputs": open_inputs}
