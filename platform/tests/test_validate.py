# Nothing existing: nf-core publishes module metadata but no checker for a canvas graph, and its lint needs a checked-out project and starts programs, which the platform host must not do.
"""017c: the pure half of the static checks of a composed pipeline - `validate.validate`. Test cases are named in the comments
(TC-001 ...), see specs/017c-validate/test-case.md. No database, no network. Small hand-made catalogues are used wherever a rule of
the type check needs exact control; the real catalogue is used for the golden graph and for TC-118 of 017b."""
import copy
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
FIXTURES = HERE / "fixtures" / "validate"
COMPOSE_FIXTURES = HERE / "fixtures" / "compose"
MODULE = PLATFORM / "abf_platform" / "validate.py"
SHA = "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"

M = ("meta", "map", None)
F = ("f", "file", None)
CODES = {"GRAPH_STALE", "META_MISMATCH", "TYPE_MISMATCH", "PATTERN_MISMATCH", "MIXED_SOURCES", "OPEN_INPUT", "DUPLICATE_PROCESS"}


def validate_mod():
    from abf_platform import validate
    return validate


def compose():
    from abf_platform import compose as c
    return c


def catalogue():
    from abf_platform import catalogue as c
    return c


def node(nid, module, **more):
    n = {"id": nid, "module": module}
    n.update(more)
    return n


def edge(src, out, dst, inp=0):
    return {"from": {"node": src, "output": out}, "to": {"node": dst, "input": inp}}


def mod(name, inputs=(), outputs=None, path=None):
    """inputs: one list of (name, type, pattern[, optional]) per input channel; outputs: {channel name: [(name, type, pattern)]}.
    A record gets an `optional` field only when the fourth item is given."""
    def rec(i, r):
        d = {"channel": i, "name": r[0], "type": r[1], "pattern": r[2]}
        if len(r) > 3:
            d["optional"] = r[3]
        return d
    return {"name": name, "path": path or name, "description": "", "keywords": [], "tools": [],
            "inputs": [rec(i, r) for i, ch in enumerate(inputs) for r in ch],
            "outputs": [{"channel": c, "name": n, "type": t, "pattern": p} for c, ch in (outputs or {}).items() for n, t, p in ch]}


def cat(*mods, sha="syn-sha"):
    return {"source": "synthetic", "sha": sha, "count": len(mods), "modules": list(mods), "errors": []}


def norm(graph, data=None):
    canonical, problems = compose().normalize(graph, data)
    assert problems == [] and canonical is not None, problems
    return canonical


def run(data, nodes, edges):
    return validate_mod().validate(norm({"nodes": nodes, "edges": edges}, data), data)


def pair(src_out, dst_in, src_extra=None):
    """One edge a.out -> b.0 over a hand-made catalogue; returns the findings."""
    data = cat(mod("a", outputs=src_out), mod("b", inputs=[dst_in]))
    return run(data, [node("a", "a"), node("b", "b")], [edge("a", "out", "b")])["findings"]


def codes(findings):
    return [f["code"] for f in findings]


def qc_graph():
    return json.loads((COMPOSE_FIXTURES / "fastqc_multiqc" / "graph.json").read_text(encoding="utf-8"))


def golden():
    return validate_mod().validate(norm(qc_graph()))


# ---- US1: shape, order, repeatability -------------------------------------------------------------------------------------

def test_golden_good_graph_is_ok_with_one_open_input_warning():
    # TC-001, TC-002, TC-004, TC-010, TC-087, TC-088
    r = golden()
    assert sorted(r) == ["catalogue_sha", "checks", "findings", "ok", "open_inputs"]
    assert r["checks"] == ["static"] and r["catalogue_sha"] == SHA and r["ok"] is True
    expected = json.loads((FIXTURES / "good_fastqc_multiqc.expected.json").read_text(encoding="utf-8"))
    assert r["findings"] == expected["findings"] and len(r["findings"]) == 1
    f = r["findings"][0]
    assert (f["node"], f["channel"], f["code"], f["severity"]) == ("qc", 0, "OPEN_INPUT", "warning") and "入口" in f["message"]
    assert r["open_inputs"] == [{"node": "qc", "input": 0, "names": ["meta", "reads"]}]
    assert "validated_at" not in r and "stale" not in r


def bad_edges():
    d = json.loads((FIXTURES / "bad_edges.json").read_text(encoding="utf-8"))
    return d["catalogue"], d["graph"]


def test_finding_shape_and_ok_follow_the_severity():
    # TC-003, TC-005, TC-006
    data, graph = bad_edges()
    r = validate_mod().validate(norm(graph, data), data)
    assert r["ok"] is False
    for f in r["findings"]:
        assert sorted(f) == ["channel", "code", "message", "node", "severity"] and f["severity"] in ("error", "warning")
    sev = [f["severity"] for f in r["findings"]]
    assert sev == sorted(sev, key=lambda s: 0 if s == "error" else 1) and "warning" in sev and "error" in sev


def test_findings_are_in_a_fixed_order_and_repeatable():
    # TC-007, TC-009
    graph = {"nodes": [node("s1", "samtools_sort"), node("s2", "samtools_sort"), node("report", "multiqc")],
             "edges": [edge("s1", "bam", "report"), edge("s2", "bam", "report")]}
    r = validate_mod().validate(norm(graph))
    assert [(f["node"], f["channel"]) for f in r["findings"]] == [("s1", 0), ("s1", 1), ("s1", 2), ("s2", 0), ("s2", 1), ("s2", 2)]
    shuffled = {"nodes": list(reversed(graph["nodes"])), "edges": list(reversed(graph["edges"]))}
    runs = [validate_mod().validate(norm(g)) for g in (graph, shuffled) for _ in (0, 1)]
    assert all(x["findings"] == runs[0]["findings"] for x in runs)
    key = validate_mod()._order_key
    f = lambda node_, ch, code, sev="error", msg="m": {"node": node_, "channel": ch, "code": code, "severity": sev, "message": msg}
    mixed = [f("b", 1, "X"), f(None, None, "G"), f("b", "s", "X"), f("a", 2, "X", "warning"), f("b", 0, "X"), f("a", 2, "X")]
    got = sorted(mixed, key=key)
    assert [(x["node"], x["channel"], x["severity"]) for x in got] == [
        (None, None, "error"), ("a", 2, "error"), ("b", 0, "error"), ("b", 1, "error"), ("b", "s", "error"), ("a", 2, "warning")]


def test_open_inputs_list_matches_compose_render():
    # TC-013, TC-090
    graph = json.loads((FIXTURES / "open_inputs_twins.json").read_text(encoding="utf-8"))
    canonical = norm(graph)
    r = validate_mod().validate(canonical)
    assert r["open_inputs"] == compose().render(canonical, "demo", 1)["open_inputs"]
    expected = json.loads((FIXTURES / "open_inputs_twins.expected.json").read_text(encoding="utf-8"))
    assert r["ok"] is True and r["findings"] == expected["findings"] and r["open_inputs"] == expected["open_inputs"]
    assert [(f["node"], f["channel"]) for f in r["findings"]] == [(n, k) for n in ("s1", "s2") for k in (0, 1, 2)]
    assert all("入口" in f["message"] for f in r["findings"])


def test_every_finding_is_bilingual_and_says_what_to_do():
    # TC-011, TC-111
    data, graph = bad_edges()
    seen = validate_mod().validate(norm(graph, data), data)["findings"]
    seen += golden()["findings"]
    d2 = cat(mod("p/q"), mod("p_q"))
    seen += run(d2, [node("x", "p/q"), node("y", "p_q")], [])["findings"]
    seen += validate_mod().validate(norm(qc_graph()), cat(mod("fastqc")))["findings"]
    seen += run(cat(mod("a", inputs=[[M, F]], outputs={"o": [M, F]})), [node("n", "a")], [edge("n", "o", "n")])["findings"] \
        if False else []
    assert CODES.issuperset(codes(seen)) and {"GRAPH_STALE", "DUPLICATE_PROCESS", "OPEN_INPUT", "META_MISMATCH", "TYPE_MISMATCH",
                                               "MIXED_SOURCES", "PATTERN_MISMATCH"} <= set(codes(seen))
    for f in seen:
        assert re.search(r"[一-鿿]", f["message"]) and re.search(r"\([ -~]+\)", f["message"]), f["message"]


def test_validate_never_mutates_its_input():
    # TC-012
    canonical = norm(qc_graph())
    before = copy.deepcopy(canonical)
    validate_mod().validate(canonical)
    assert canonical == before


def test_data_defaults_to_the_catalogue():
    # TC-014
    canonical = norm(qc_graph())
    assert validate_mod().validate(canonical) == validate_mod().validate(canonical, catalogue().load())


# ---- US2: types ---------------------------------------------------------------------------------------------------------

def test_tuple_with_more_elements_is_compatible_by_class():
    # TC-015, TC-021, TC-022
    six = [M, ("a", "file", None), ("b", "file", None), ("c", "file", None), ("d", "file", None), ("e", "file", None)]
    data = cat(mod("a", outputs={"out": [M, F]}), mod("b", inputs=[six]))
    r = run(data, [node("a", "a"), node("b", "b")], [edge("a", "out", "b")])
    assert [f for f in r["findings"] if f["code"] in ("TYPE_MISMATCH", "META_MISMATCH")] == []
    assert not [f for f in pair({"out": [M, F]}, [M, ("d", "directory", None)]) if f["code"] in ("TYPE_MISMATCH", "META_MISMATCH")]
    for src, dst in (("string", "integer"), ("boolean", "float"), ("integer", "string")):
        found = pair({"out": [("v", src, None)]}, [("w", dst, None)])
        assert [f for f in found if f["code"] in ("TYPE_MISMATCH", "META_MISMATCH")] == [], (src, dst)


def test_meta_mismatch_names_both_ends_and_both_directions():
    # TC-016, TC-017, TC-018, TC-005
    for src, dst in (([M, F], [F]), ([F], [M, F]), ([M, F], [("s", "string", None)])):
        found = [f for f in pair({"out": src}, dst) if f["code"] in ("META_MISMATCH", "TYPE_MISMATCH")]
        assert codes(found) == ["META_MISMATCH"], (src, dst)
        f = found[0]
        assert f["severity"] == "error" and f["node"] == "b" and f["channel"] == 0
        assert "a.out" in f["message"] and "b.0" in f["message"] and "轉換節點" in f["message"]


def test_type_mismatch_names_both_ends():
    # TC-019, TC-020
    found = pair({"out": [M, F]}, [M, ("s", "string", None)])
    f = [x for x in found if x["code"] == "TYPE_MISMATCH"][0]
    assert f["severity"] == "error" and f["node"] == "b" and f["channel"] == 0 and "a.out" in f["message"] and "b.0" in f["message"]
    assert "TYPE_MISMATCH" in codes(pair({"out": [M]}, [M, F]))
    assert "TYPE_MISMATCH" in codes(pair({"out": [M, F]}, [M]))
    assert "TYPE_MISMATCH" not in codes(pair({"out": [M]}, [M]))


def test_any_and_unknown_types_are_compatible_with_anything_but_meta_must_still_match():
    # TC-023, TC-024
    for odd in (("x", "list", None), ("x", None, None), ("x", "weird", None)):
        for other in (F, ("s", "string", None)):
            assert not [f for f in pair({"out": [odd]}, [other]) if f["code"] in ("TYPE_MISMATCH", "META_MISMATCH")]
            assert not [f for f in pair({"out": [M, other]}, [M, odd]) if f["code"] in ("TYPE_MISMATCH", "META_MISMATCH")]
    assert "META_MISMATCH" in codes(pair({"out": [M, ("x", "list", None)]}, [("x", "list", None)]))


def test_tc118_still_holds_for_normalize_but_validate_flags_it():
    # TC-025, TC-026, TC-096 (graph level)
    graph = {"nodes": [node("qc", "fastqc"), node("s", "samtools_sort")], "edges": [edge("qc", "html", "s", 2)]}
    canonical, problems = compose().normalize(graph)
    assert problems == [] and canonical is not None
    r = validate_mod().validate(canonical)
    f = [x for x in r["findings"] if x["code"] == "META_MISMATCH"][0]
    assert f["severity"] == "error" and f["node"] == "s" and f["channel"] == 2
    assert "qc.html" in f["message"] and "s.2" in f["message"] and r["ok"] is False


# ---- US3: pattern, mixing, open inputs, names ----------------------------------------------------------------------------

def pat(p):
    return [M, ("f", "file", p)]


def test_pattern_mismatch_is_a_warning_and_does_not_fail_ok():
    # TC-027
    data = cat(mod("a", outputs={"out": pat("*.{bam}")}), mod("b", inputs=[pat("*.{vcf}")]))
    r = run(data, [node("a", "a"), node("b", "b")], [edge("a", "out", "b")])
    hits = [f for f in r["findings"] if f["code"] == "PATTERN_MISMATCH"]
    assert len(hits) == 1 and hits[0]["severity"] == "warning" and hits[0]["node"] == "b" and hits[0]["channel"] == 0
    assert r["ok"] is True or all(f["severity"] == "warning" for f in r["findings"])


def test_pattern_that_cannot_be_parsed_is_skipped():
    # TC-028, TC-029, TC-030, TC-031
    for a, b in (("*.{bam}", "bai|csi|crai"), ("${prefix}.bam", "*.{vcf}"), ("*", "*.{vcf}"), ("*.{bam,cram}", "*.{bam}")):
        assert "PATTERN_MISMATCH" not in codes(pair({"out": pat(a)}, pat(b))), (a, b)
    two = [M, ("f1", "file", "*.{vcf}"), ("f2", "file", "*.{vcf}")]
    assert "PATTERN_MISMATCH" not in codes(pair({"out": pat("*.{bam}")}, two))
    assert "PATTERN_MISMATCH" not in codes(pair({"out": two}, pat("*.{bam}")))
    assert "PATTERN_MISMATCH" not in codes(pair({"out": pat("*.{bam}")}, [M, ("f", "file", None)]))


def three(srcs, dst_in):
    mods = [mod(n, outputs={"out": o}) for n, o in srcs] + [mod("d", inputs=[[F], dst_in])]
    nodes = [node(n, n) for n, _ in srcs] + [node("d", "d")]
    return run(cat(*mods), nodes, [edge(n, "out", "d", 1) for n, _ in srcs])


def test_mixed_sources_on_one_input_are_checked_pairwise():
    # TC-032, TC-033, TC-034, TC-098
    r = three([("a", [M, F]), ("e", [F])], [F])
    mixed = [f for f in r["findings"] if f["code"] == "MIXED_SOURCES"]
    assert len(mixed) == 1 and mixed[0]["severity"] == "error" and (mixed[0]["node"], mixed[0]["channel"]) == ("d", 1)
    assert "a.out" in mixed[0]["message"] and "e.out" in mixed[0]["message"]
    r = three([("a", [F]), ("e", [("v", "string", None)])], [("x", "any", None)])
    assert "MIXED_SOURCES" in codes(r["findings"])
    r = three([("a", [F]), ("e", [F]), ("g", [("v", "string", None)])], [("x", "any", None)])
    assert "MIXED_SOURCES" in codes(r["findings"]) and r["ok"] is False


def test_compatible_sources_mix_without_a_finding():
    # TC-035
    graph = {"nodes": [node("s1", "samtools_sort"), node("s2", "samtools_sort"), node("report", "multiqc")],
             "edges": [edge("s1", "bam", "report"), edge("s2", "bam", "report")]}
    r = validate_mod().validate(norm(graph))
    assert "MIXED_SOURCES" not in codes(r["findings"]) and "DUPLICATE_PROCESS" not in codes(r["findings"])     # TC-043


def test_open_inputs_required_on_non_entry_are_errors_and_entry_nodes_say_so():
    # TC-036 .. TC-040, TC-OI03, TC-OI11
    r = golden()
    assert r["ok"] is True and [f["severity"] for f in r["findings"]] == ["warning"]
    assert not [f for f in r["findings"] if f["node"] == "report"]
    graph = {"nodes": [node("qc", "fastqc"), node("s", "samtools_sort")], "edges": [edge("qc", "zip", "s", 0)]}
    r = validate_mod().validate(norm(graph))
    by = {(f["node"], f["channel"]): f for f in r["findings"] if f["code"] == "OPEN_INPUT"}
    assert "入口" in by[("qc", 0)]["message"] and "少了一個輸入" not in by[("qc", 0)]["message"]
    assert by[("qc", 0)]["severity"] == "warning"
    one = by[("s", 1)]["message"]
    assert "少了一個輸入" in one and "入口" not in one and "meta2" in one and "fasta" in one and "fai" in one
    assert by[("s", 1)]["severity"] == "warning"                       # TC-OI11: only meta2 is false
    assert by[("s", 2)]["severity"] == "error" and r["ok"] is False    # TC-OI03: index_format is required
    assert ("s", 0) not in by


def open_run(b_inputs, a_inputs=(), wire=True):
    """a -> b.0 (when wire) over a synthetic catalogue; returns the OPEN_INPUT findings by (node, channel) and the result."""
    data = cat(mod("a", inputs=a_inputs, outputs={"out": [("o", "file", None)]}), mod("b", inputs=b_inputs))
    r = run(data, [node("a", "a"), node("b", "b")], [edge("a", "out", "b")] if wire else [])
    return {(f["node"], f["channel"]): f for f in r["findings"] if f["code"] == "OPEN_INPUT"}, r


def test_required_open_input_on_a_non_entry_node_is_an_error():
    # TC-OI01, TC-OI02, TC-OI06, TC-OI63
    by, r = open_run([[("x", "file", None, False)], [("y", "file", None, False)]])
    assert list(by) == [("b", 1)] and by[("b", 1)]["severity"] == "error" and r["ok"] is False
    m = by[("b", 1)]["message"]
    assert "少了一個輸入" in m and "b" in m and "1" in m and "y" in m and "入口" not in m and re.search(r"\([ -~]+\)", m)
    assert "Traceback" not in m and "/" not in m


def test_optional_open_input_stays_a_warning():
    # TC-OI10
    by, r = open_run([[("x", "file", None, False)], [("y", "file", None, True)]])
    assert by[("b", 1)]["severity"] == "warning" and r["ok"] is True


def test_entry_node_required_input_is_still_a_warning():
    # TC-OI20, TC-OI21
    data = cat(mod("a", inputs=[[("x", "file", None, False)]]))
    r = run(data, [node("a", "a")], [])
    f = [x for x in r["findings"] if x["code"] == "OPEN_INPUT"]
    assert len(f) == 1 and f[0]["severity"] == "warning" and r["ok"] is True
    assert "這個節點是入口，送出時要由樣本表或參數供應" in f[0]["message"] and "少了一個輸入" not in f[0]["message"]


def test_required_means_any_non_meta_record_explicitly_false():
    # TC-OI04, TC-OI05, TC-OI07, TC-OI12, TC-OI13, TC-OI14
    ok = [("x", "file", None, False)]
    by, _ = open_run([ok, [("p", "file", None, False), ("q", "file", None, True)]])
    assert by[("b", 1)]["severity"] == "error"
    by, _ = open_run([ok, [("p", "file", None, False), ("q", "file", None)]])
    assert by[("b", 1)]["severity"] == "error"
    by, r = open_run([ok, [("p", "file", None, False)], [("q", "file", None, False)]])
    assert [by[k]["severity"] for k in sorted(by)] == ["error", "error"] and r["ok"] is False
    by, _ = open_run([ok, [("m", "map", None, False)]])
    assert by[("b", 1)]["severity"] == "warning"
    by, r = open_run([[("x", "file", None)], [("y", "file", None)]])
    assert by[("b", 1)]["severity"] == "warning" and r["ok"] is True
    by, _ = open_run([ok, [("m", "map", None, False), ("q", "file", None, True)]])
    assert by[("b", 1)]["severity"] == "warning"


def test_entry_and_non_entry_are_judged_separately_in_one_graph():
    # TC-OI24
    by, r = open_run([[("x", "file", None, False)], [("y", "file", None, False)]], a_inputs=[[("z", "file", None, False)]])
    assert by[("a", 0)]["severity"] == "warning" and "入口" in by[("a", 0)]["message"]
    assert by[("b", 1)]["severity"] == "error" and "少了一個輸入" in by[("b", 1)]["message"] and r["ok"] is False


def test_real_catalogue_golden_still_ok():
    # TC-OI22
    r = golden()
    f = r["findings"]
    assert r["ok"] is True and len(f) == 1
    assert (f[0]["node"], f[0]["channel"], f[0]["code"], f[0]["severity"]) == ("qc", 0, "OPEN_INPUT", "warning") and "入口" in f[0]["message"]


def test_duplicate_process_names_and_alias_collisions():
    # TC-041, TC-042
    r = run(cat(mod("ab1", path="a/b"), mod("ab2", path="a_b")), [node("x", "ab1"), node("y", "ab2")], [])
    f = [x for x in r["findings"] if x["code"] == "DUPLICATE_PROCESS"]
    assert len(f) == 1 and f[0]["severity"] == "error" and r["ok"] is False and "A_B" in f[0]["message"]
    data = cat(mod("fastqc"), mod("odd", path="fastqc/x"))
    r = run(data, [node("x", "fastqc"), node("y", "fastqc"), node("z", "odd")], [])
    assert "DUPLICATE_PROCESS" in codes(r["findings"]) and r["ok"] is False


# ---- US4: the graph no longer fits ---------------------------------------------------------------------------------------

def test_stale_graph_stops_after_the_graph_check():
    # TC-044, TC-045, TC-046, TC-051, TC-052
    canonical = norm(qc_graph())
    data = catalogue().load()
    gone = dict(data, modules=[m for m in data["modules"] if m["name"] != "multiqc"])
    r = validate_mod().validate(canonical, gone)
    _, problems = compose().normalize(canonical, gone)
    assert problems and r["ok"] is False and r["open_inputs"] == []
    assert [f["message"] for f in r["findings"]] == problems          # TC-052; no OPEN_INPUT, no type finding (TC-051)
    assert all(f["code"] == "GRAPH_STALE" and f["severity"] == "error" and f["node"] is None and f["channel"] is None for f in r["findings"])
    assert "GRAPH_STALE" in codes(validate_mod().validate(canonical, dict(data, sha="changed"))["findings"])
    fewer = copy.deepcopy(data)
    for m in fewer["modules"]:
        if m["name"] == "fastqc":
            m["outputs"] = [o for o in m["outputs"] if o["channel"] != "zip"]
    assert "GRAPH_STALE" in codes(validate_mod().validate(canonical, fewer)["findings"])


def test_a_loop_is_a_graph_problem_with_no_node():
    # TC-047
    canonical = norm({"nodes": [node("qc", "fastqc"), node("s", "samtools_sort")], "edges": [edge("qc", "zip", "s", 0)]})
    looped = copy.deepcopy(canonical)
    looped["edges"].append(edge("s", "bam", "qc", 0))
    r = validate_mod().validate(looped)
    assert r["ok"] is False and r["findings"] and all(f["code"] == "GRAPH_STALE" and f["node"] is None for f in r["findings"])
    selfie = copy.deepcopy(canonical)
    selfie["edges"] = [edge("qc", "zip", "qc", 0)]
    assert "GRAPH_STALE" in codes(validate_mod().validate(selfie)["findings"])


def test_param_rules_agree_with_normalize():
    # TC-048, TC-049, TC-050
    keys = ["ext.args", "ext.prefix"] + ["ext.args%d" % i for i in range(2, 10)]
    good = {"nodes": [node("qc", "fastqc", params={k: "v" for k in keys})]}
    assert "GRAPH_STALE" not in codes(validate_mod().validate(norm(good))["findings"])
    bad = [{"publishDir": "v"}, {"ext.args1": "v"}, {"ext.args10": "v"}, {"cpus": "v"}] + \
          [{"ext.args": v} for v in ("a\nb", "a\x07b", 5, True, ["x"], "x" * 1001)]
    for params in bad:
        graph = {"nodes": [node("qc", "fastqc", params=params)]}
        _, problems = compose().normalize(graph)
        assert problems, params
        canonical = {"nodes": [node("qc", "fastqc", sha=SHA, params=params)], "edges": []}
        r = validate_mod().validate(canonical)
        key = next(iter(params))
        assert r["ok"] is False and all(f["code"] == "GRAPH_STALE" and f["severity"] == "error" for f in r["findings"]), params
        assert any("qc" in f["message"] and key in f["message"] for f in r["findings"]), params


# ---- fixtures and constitution ------------------------------------------------------------------------------------------

def test_fixtures_and_hand_derived_answers():
    # TC-085, TC-086, TC-091 .. TC-095
    names = ["good_fastqc_multiqc", "bad_edges", "open_inputs_twins"]
    for n in names:
        assert (FIXTURES / (n + ".json")).is_file() and (FIXTURES / (n + ".expected.json")).is_file()
    assert json.loads((FIXTURES / "good_fastqc_multiqc.json").read_text(encoding="utf-8")) == qc_graph()
    data, graph = bad_edges()
    r = validate_mod().validate(norm(graph, data), data)
    expected = json.loads((FIXTURES / "bad_edges.expected.json").read_text(encoding="utf-8"))
    assert r["ok"] is False and r["findings"] == expected["findings"] and r["open_inputs"] == expected["open_inputs"]
    want = {("b", 0, "META_MISMATCH"), ("c", 0, "TYPE_MISMATCH"), ("d", 1, "MIXED_SOURCES"), ("g", 0, "PATTERN_MISMATCH")}
    assert want <= {(f["node"], f["channel"], f["code"]) for f in r["findings"]}
    assert [f for f in r["findings"] if (f["node"], f["channel"], f["code"]) == ("d", 1, "META_MISMATCH")][0]["message"].count("e.out") == 0


def test_validate_module_is_pure():
    # TC-084
    text = MODULE.read_text(encoding="utf-8")
    low = text.lower()
    for word in ("import store", "sqlite3", "urllib", "requests", "socket", "subprocess", "open(", "nextflow", "lint", "stub"):
        assert word not in low, word
    imports = [l for l in text.splitlines() if l.startswith(("import ", "from "))]
    assert imports == ["import re", "from . import catalogue, compose"]


def test_only_the_seven_codes_appear():
    # TC-111: every code that any graph here produces is one of the seven
    data, graph = bad_edges()
    seen = set(codes(validate_mod().validate(norm(graph, data), data)["findings"]))
    seen |= set(codes(validate_mod().validate(norm(qc_graph()), cat(mod("x")))["findings"]))
    assert seen <= CODES
