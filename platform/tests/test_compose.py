# Nothing existing: nf-core has no library that turns a canvas graph into a pipeline project, and the golden files here are written by hand from the rules of spec 017b.
"""017b: the pure half of composed pipelines - `compose.normalize` (shape of a graph) and `compose.render` (the text of a Nextflow
project). Test cases are named in the comments (TC-001 ...), see specs/017b-compose/test-case.md. No database, no network."""
import copy
import json

import re
import socket
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
FIXTURES = HERE / "fixtures" / "compose"
MODULE = PLATFORM / "abf_platform" / "compose.py"
SHA = "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"


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


def qc_graph():
    return json.loads((FIXTURES / "fastqc_multiqc" / "graph.json").read_text(encoding="utf-8"))


def norm(graph, data=None):
    canonical, problems = compose().normalize(graph, data)
    assert problems == [] and canonical is not None, problems
    return canonical


def refused(graph, data=None):
    canonical, problems = compose().normalize(graph, data)
    assert canonical is None and problems, "the graph was accepted"
    return "\n".join(problems)


def fixture(name):
    d = FIXTURES / name
    files = {f: (d / f).read_text(encoding="utf-8") for f in ("main.nf", "modules.json", "nextflow.config")}
    m = re.search(r"\(pipeline (\S+) v(\d+)\)", files["main.nf"].splitlines()[1])
    return json.loads((d / "graph.json").read_text(encoding="utf-8")), files, m.group(1), int(m.group(2))


def rendered(graph, name="demo-qc", version=1):
    return compose().render(norm(graph), name, version)


TWINS = {"nodes": [node("s1", "samtools_sort"), node("s2", "samtools_sort"), node("report", "multiqc")],
         "edges": [edge("s1", "bam", "report"), edge("s2", "bam", "report")]}


# ---- US1: normalize -----------------------------------------------------------------------------------------------------

def test_tc001_the_two_node_graph_is_accepted():
    c = norm(qc_graph())
    assert len(c["nodes"]) == 2 and len(c["edges"]) == 1
    assert c["edges"][0] == {"from": {"node": "qc", "output": "zip"}, "to": {"node": "report", "input": 0}}


def test_module_names_are_stored_canonically():
    # TC-002, TC-003
    assert norm({"nodes": [node("a", "FASTQC")]})["nodes"][0]["module"] == "fastqc"
    assert norm({"nodes": [node("a", "strdust")]})["nodes"][0]["module"] == "STRdust"


def test_missing_sha_is_filled_from_the_snapshot():
    # TC-004, TC-005, TC-008
    c = norm({"nodes": [node("a", "fastqc")]})
    assert c["nodes"][0]["sha"] == SHA and c["nodes"][0]["params"] == {}
    norm({"nodes": [node("a", "fastqc", sha=SHA)]})


def test_wrong_sha_is_refused():
    # TC-012
    text = refused({"nodes": [node("a", "fastqc", sha="0" * 40)]})
    assert "sha" in text and "a" in text


def test_order_does_not_matter_and_the_standard_form_is_sorted():
    # TC-006, TC-007
    one = {"nodes": [node("b", "fastqc", params={"ext.prefix": "p", "ext.args": "x"}), node("a", "multiqc"), node("c", "multiqc")],
           "edges": [edge("b", "zip", "c"), edge("b", "html", "a")]}
    two = copy.deepcopy(one)
    two["nodes"].reverse()
    two["edges"].reverse()
    two["nodes"][2]["params"] = {"ext.args": "x", "ext.prefix": "p"}
    c1, c2 = norm(one), norm(two)
    assert c1 == c2 and compose().graph_json(c1) == compose().graph_json(c2)
    assert [n["id"] for n in c1["nodes"]] == ["a", "b", "c"]
    assert [(e["from"]["output"], e["to"]["node"]) for e in c1["edges"]] == [("html", "a"), ("zip", "c")]
    assert list(c1["nodes"][1]["params"]) == ["ext.args", "ext.prefix"]


def test_limits_nodes_edges_and_size():
    # TC-010, TC-027, TC-028, TC-029
    norm({"nodes": [node("n%03d" % i, "fastqc") for i in range(200)]})
    assert "200" in refused({"nodes": [node("n%03d" % i, "fastqc") for i in range(201)]})
    nodes = [node("f%02d" % i, "fastqc") for i in range(40)] + [node("m%02d" % i, "multiqc") for i in range(40)]
    edges = [edge("f%02d" % i, out, "m%02d" % j) for i in range(40) for j in range(40) for out in ("html", "zip")][:1001]
    norm({"nodes": nodes, "edges": edges[:1000]})
    c, problems = compose().normalize({"nodes": nodes, "edges": edges})
    assert c is None and len(problems) == 1 and "1001" in problems[0]
    big = {k: "x" * 1000 for k in ["ext.args", "ext.prefix"] + ["ext.args%d" % i for i in range(2, 10)]}
    nodes = [node("n%02d" % i, "fastqc", params=dict(big)) for i in range(30)]
    c, problems = compose().normalize({"nodes": nodes})
    assert c is None and len(problems) == 1 and "256" in problems[0]


def test_param_keys_and_values_are_restricted():
    # TC-009, TC-011, TC-030 .. TC-035
    keys = ["ext.args", "ext.prefix"] + ["ext.args%d" % i for i in range(2, 10)]
    norm({"nodes": [node("qc", "fastqc", params={k: "v" for k in keys})]})
    norm({"nodes": [node("qc", "fastqc", params={"ext.args": "x" * 1000})]})
    for key in ("publishDir", "ext.args1", "ext.args10", "cpus"):
        text = refused({"nodes": [node("qc", "fastqc", params={key: "v"})]})
        assert "qc" in text and key in text
    for bad in ("a\nb", "a\x07b", "a\tb", "a\x00b", 5, True, ["x"], "x" * 1001):
        text = refused({"nodes": [node("qc", "fastqc", params={"ext.args": bad})]})
        assert "qc" in text and "ext.args" in text, repr(bad)


def test_unknown_module_is_refused_and_names_it():
    # TC-013, TC-122
    for name in ("fastqcc", "bam_sort_stats_samtools"):
        text = refused({"nodes": [node("a", name)]})
        assert name in text and "search" in text


def test_edge_to_a_missing_output_channel_lists_the_real_ones():
    # TC-014, TC-123
    g = qc_graph()
    g["edges"][0]["from"]["output"] = "zipp"
    text = refused(g)
    assert "qc.zipp" in text and "html" in text and "zip" in text
    g["edges"][0]["from"]["output"] = "versions"
    text = refused(g)
    assert "html" in text and "zip" in text


def test_an_output_channel_that_is_not_an_identifier_cannot_be_wired():
    # TC-015
    data = copy.deepcopy(catalogue().load())
    data["modules"] = data["modules"] + [{"name": "odd", "path": "odd", "description": "", "keywords": [], "tools": [],
                                          "inputs": [{"channel": 0, "name": "x", "type": "file", "pattern": None}],
                                          "outputs": [{"channel": "my-out", "name": "y", "type": "file", "pattern": None}]}]
    text = refused({"nodes": [node("a", "odd"), node("b", "multiqc")], "edges": [edge("a", "my-out", "b")]}, data)
    assert "這個輸出通道名不能接線" in text and "my-out" in text


def test_edge_to_a_missing_input_channel_is_refused():
    # TC-016, TC-017
    g = qc_graph()
    g["edges"][0]["to"]["input"] = 5
    assert "5" in refused(g)
    g["edges"][0]["to"]["input"] = "0"
    refused(g)


def test_edge_to_a_missing_node_is_refused():
    # TC-018, TC-019
    g = qc_graph()
    g["edges"][0]["to"]["node"] = "nope"
    assert "nope" in refused(g)
    g = qc_graph()
    g["edges"][0]["from"]["node"] = "nope"
    assert "nope" in refused(g)


def test_duplicate_edge_is_refused():
    # TC-020
    g = qc_graph()
    g["edges"].append(copy.deepcopy(g["edges"][0]))
    refused(g)


def test_cycles_and_self_loops_are_refused():
    # TC-021, TC-022
    refused({"nodes": [node("a", "fastqc")], "edges": [edge("a", "zip", "a")]})
    refused({"nodes": [node("a", "samtools_sort"), node("b", "samtools_sort")],
             "edges": [edge("a", "bam", "b"), edge("b", "bam", "a")]})


def test_ids_must_have_the_right_shape_and_be_unique():
    # TC-023, TC-024
    for bad in ("QC", "1qc", "_qc", "a" * 33):
        assert bad in refused({"nodes": [node(bad, "fastqc")]})
    assert "qc" in refused({"nodes": [node("qc", "fastqc"), node("qc", "multiqc")]})


def test_only_nodes_and_edges_at_the_top():
    # TC-025, TC-124, TC-026
    for key in ("inputs", "params"):
        g = qc_graph()
        g[key] = {}
        assert key in refused(g)
    refused({"nodes": []})


def test_problems_are_bilingual_and_say_what_to_do():
    # TC-036, TC-037
    cases = []
    g = qc_graph()
    g["edges"][0]["from"]["output"] = "zipp"
    cases.append(g)
    cases.append({"nodes": [node("a", "fastqc", sha="0" * 40)]})
    cases.append({"nodes": [node("a", "nonesuch")]})
    cases.append({"nodes": [node("QC", "fastqc")]})
    cases.append({"nodes": [node("a", "fastqc", params={"publishDir": "x"})]})
    cases.append({"nodes": [node("a", "fastqc", params={"ext.args": "a\nb"})]})
    cases.append(dict(qc_graph(), inputs={}))
    cases.append({"nodes": [node("a", "fastqc")], "edges": [edge("a", "zip", "a")]})
    cases.append({"nodes": [node("n%03d" % i, "fastqc") for i in range(201)]})
    cases.append({"nodes": []})
    for g in cases:
        for p in compose().normalize(g)[1]:
            assert re.search(r"[一-鿿]", p) and re.search(r"\([ -~]+\)\s*$", p), p
    c, problems = compose().normalize({"nodes": [node("a", "nonesuch"), node("a", "fastqc")]})
    assert c is None and len(problems) >= 2


def test_types_are_not_compared():
    # TC-118
    norm({"nodes": [node("qc", "fastqc"), node("s", "samtools_sort")], "edges": [edge("qc", "html", "s", 2)]})


# ---- US2: render --------------------------------------------------------------------------------------------------------

def test_fastqc_multiqc_renders_the_golden():
    # TC-038 .. TC-041, TC-077
    graph, files, name, version = fixture("fastqc_multiqc")
    out = compose().render(norm(graph), name, version)
    assert out["files"] == files
    assert out["open_inputs"] == [{"node": "qc", "input": 0, "names": ["meta", "reads"]}]
    assert files["main.nf"].startswith("#!/usr/bin/env nextflow\n// Generated by abf-platform compose (pipeline demo-qc v1); do not edit by hand.\n\n")
    assert files["main.nf"].endswith("}\n") and not files["main.nf"].endswith("\n\n")                  # TC-042
    assert "ch_report_in0" not in files["main.nf"] and all(o["node"] != "report" for o in out["open_inputs"])       # TC-061
    assert set(out["files"]) == {"main.nf", "modules.json", "nextflow.config"}                          # TC-074


def test_render_is_deterministic_and_order_independent():
    # TC-043
    a = qc_graph()
    b = copy.deepcopy(a)
    b["nodes"].reverse()
    b["nodes"][1]["params"] = dict(reversed(list(b["nodes"][1]["params"].items())))
    first, second = rendered(a), rendered(b)
    assert first == second == rendered(b)


def test_the_version_goes_into_the_header_and_the_manifest_only():
    # TC-044, TC-068
    one, three = rendered(qc_graph(), version=1), rendered(qc_graph(), version=3)
    assert one["files"]["modules.json"] == three["files"]["modules.json"]
    assert "v3" in three["files"]["main.nf"] and "v1" in one["files"]["main.nf"]
    assert "version = '0.3.0'" in three["files"]["nextflow.config"] and "pipeline demo-qc v3" in three["files"]["nextflow.config"]
    assert "name = 'demo-qc'" in three["files"]["nextflow.config"]


def test_process_name_comes_from_the_path_not_the_name():
    # TC-045, TC-046, TC-064, TC-077
    graph, files, name, version = fixture("old_format_module")
    out = compose().render(norm(graph), name, version)
    assert out["files"] == files
    text = out["files"]["main.nf"]
    assert "include { STRDUST } from './modules/nf-core/strdust/main'" in text and "STRDUST(" in text and "STRdust" not in text
    assert "include { CUSTOM_CLUSTERMETRICS } from './modules/nf-core/custom/clustermetrics/main'" in text
    assert set(json.loads(out["files"]["modules.json"])["repos"]["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]) == \
        {"strdust", "custom/clustermetrics"}


def test_a_module_used_once_has_no_alias():
    # TC-047, TC-051
    text = rendered({"nodes": [node("s", "samtools_sort")]})["files"]["main.nf"]
    assert "include { SAMTOOLS_SORT } from './modules/nf-core/samtools/sort/main'" in text and " as " not in text


def test_every_catalogue_module_has_a_valid_process_name():
    # TC-048
    names = [compose().process_name(m) for m in catalogue().load()["modules"]]
    assert len(names) == 2116
    bad = [n for n in names if not re.match(r"^[A-Z][A-Z0-9_]*$", n)]
    assert bad == []
    dup = sorted({n for n in names if names.count(n) > 1})
    assert dup == [], "two modules would get one process name: %s" % dup


def test_includes_are_sorted_by_process_name():
    # TC-049
    g = {"nodes": [node("a", "multiqc"), node("b", "fastqc")]}
    lines = [l for l in rendered(g)["files"]["main.nf"].splitlines() if l.startswith("include")]
    assert [l.split()[2] for l in lines] == ["FASTQC", "MULTIQC"]


def test_fan_in_uses_mix_and_twins_get_aliases():
    # TC-050, TC-052, TC-056, TC-058 .. TC-060, TC-063, TC-065, TC-070, TC-077, TC-078
    graph, files, name, version = fixture("fan_in_and_twins")
    out = compose().render(norm(graph), name, version)
    assert out["files"] == files
    text = files["main.nf"]
    assert "include { SAMTOOLS_SORT as SAMTOOLS_SORT_S1 } from './modules/nf-core/samtools/sort/main'" in text
    assert "include { SAMTOOLS_SORT as SAMTOOLS_SORT_S2 }" in text and "include { SAMTOOLS_SORT }" not in text
    assert "include { MULTIQC } from" in text
    assert "MULTIQC(SAMTOOLS_SORT_S1.out.bam.mix(SAMTOOLS_SORT_S2.out.bam))" in text
    assert text.index("SAMTOOLS_SORT_S1(") < text.index("SAMTOOLS_SORT_S2(") < text.index("MULTIQC(")
    assert "ch_s1_in1 = Channel.empty()  // OPEN INPUT: s1 input 1 (meta2, fasta, fai)" in text
    assert text.index("ch_s2_in2 =") < text.index("SAMTOOLS_SORT_S1(")
    assert [(o["node"], o["input"]) for o in out["open_inputs"]] == [(n, i) for n in ("s1", "s2") for i in (0, 1, 2)]
    assert out["open_inputs"][1]["names"] == ["meta2", "fasta", "fai"]
    modules = json.loads(files["modules.json"])["repos"]["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]
    assert list(modules).count("samtools/sort") == 1
    cfg = files["nextflow.config"]
    assert cfg.index("'SAMTOOLS_SORT_S1'") < cfg.index("'SAMTOOLS_SORT_S2'") and "MULTIQC" not in cfg
    assert cfg.index("ext.args") < cfg.index("ext.prefix")
    assert "\\'x\\' \\$TMPDIR" in cfg                                                                  # TC-078


def test_three_sources_chain_the_mix_in_order():
    # TC-053, TC-054
    g = {"nodes": [node("s3", "samtools_sort"), node("s1", "samtools_sort"), node("s2", "samtools_sort"), node("r", "multiqc")],
         "edges": [edge("s3", "bam", "r"), edge("s1", "bam", "r"), edge("s2", "bam", "r")]}
    text = rendered(g)["files"]["main.nf"]
    call = next(l for l in text.splitlines() if l.strip().startswith("MULTIQC("))
    assert call.index("_S1.out.bam") < call.index("_S2.out.bam") < call.index("_S3.out.bam")
    assert call.count(".mix(") == 2


def test_nodes_are_called_after_their_sources():
    # TC-055
    g = {"nodes": [node("zz", "fastqc"), node("aa", "multiqc")], "edges": [edge("zz", "zip", "aa")]}
    text = rendered(g)["files"]["main.nf"]
    assert text.index("FASTQC(") < text.index("MULTIQC(")


def test_argument_count_is_the_number_of_input_channels():
    # TC-057
    g = {"nodes": [node("a", "fastqc"), node("b", "samtools_sort"), node("c", "strdust"), node("d", "multiqc")]}
    text = rendered(g)["files"]["main.nf"]

    def args(name):
        line = next(l for l in text.splitlines() if l.strip().startswith(name + "("))
        return len(line.split("(", 1)[1].rstrip(")").split(", "))
    assert (args("FASTQC"), args("SAMTOOLS_SORT"), args("STRDUST"), args("MULTIQC")) == (1, 3, 4, 1)


def test_an_open_input_is_not_an_error():
    # TC-062
    out = rendered(qc_graph())
    assert out["open_inputs"] and set(out["files"]) == {"main.nf", "modules.json", "nextflow.config"}


def test_modules_json_matches_nf_core_shape():
    # TC-063, TC-066, TC-067
    out = rendered(TWINS, "twin", 1)["files"]["modules.json"]
    data = json.loads(out)
    assert sorted(data) == ["homePage", "name", "repos"] and data["homePage"] == ""
    mods = data["repos"]["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]
    assert sorted(mods) == ["multiqc", "samtools/sort"]
    for entry in mods.values():
        assert sorted(entry) == ["branch", "git_sha", "installed_by"]
        assert entry["branch"] == "master" and entry["git_sha"] == SHA and entry["installed_by"] == ["modules"]
    assert out == json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False) + "\n"


def test_no_params_means_no_process_block():
    # TC-069
    cfg = rendered({"nodes": [node("a", "fastqc")]})["files"]["nextflow.config"]
    assert "manifest {" in cfg and "process {" not in cfg


def test_param_strings_are_escaped_in_the_config():
    # TC-071, TC-072
    value = "a'b$c\\d"
    cfg = rendered({"nodes": [node("a", "fastqc", params={"ext.args": value})]})["files"]["nextflow.config"]
    line = next(l for l in cfg.splitlines() if "ext.args" in l)
    assert line.strip() == "ext.args = 'a\\'b\\$c\\\\d'"
    body = line.split(" = ", 1)[1]
    assert body[0] == "'" and body[-1] == "'"
    i = 1
    while i < len(body) - 1:                                  # walk the string: every quote and dollar inside must be escaped
        ch = body[i]
        if ch == "\\":
            i += 2
            continue
        assert ch not in "'$", body
        i += 1
    assert i == len(body) - 1                                  # the last quote closes the string, it is not an escaped one


def test_render_refuses_a_control_character_even_if_normalize_was_skipped():
    # TC-073
    bad = {"nodes": [{"id": "a", "module": "fastqc", "sha": SHA, "params": {"ext.args": "x\ny"}}], "edges": []}
    with pytest.raises(ValueError):
        compose().render(bad, "demo-qc", 1)


def test_render_makes_no_file_and_no_connection(tmp_path, monkeypatch):
    # TC-075
    monkeypatch.chdir(tmp_path)

    def no_network(*a, **k):
        raise AssertionError("render tried to use the network")
    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    rendered(qc_graph())
    assert list(tmp_path.iterdir()) == []


def test_compose_module_is_pure():
    # TC-076, TC-119, TC-126
    s = MODULE.read_text(encoding="utf-8")
    for word in ("import store", "sqlite3", "urllib", "requests", "socket", "subprocess", "open(", "zipfile", "tarfile", "shutil",
                 "os.system", "sbatch", "srun", "qsub", "confirm", "jobs", "queue"):
        assert word not in s, word


def test_the_output_only_names_modules_it_does_not_copy_them():
    # TC-125
    for text in rendered(qc_graph())["files"].values():
        assert not re.search(r"^\s*process\s+\w+\s*\{", text, re.M)
    assert "script:" not in rendered(qc_graph())["files"]["main.nf"]


def test_no_hard_coded_cluster_paths_in_the_fixtures():
    # TC-135 (the fixtures are checked again by test_scope.py)
    for f in FIXTURES.rglob("*"):
        if f.is_file():
            assert not re.search(r"(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/", f.read_text(encoding="utf-8")), f


def test_the_fixture_answers_are_not_just_the_program_output():
    # TC-077: the three folders exist with all four files, and the answer of the first one is the text of the plan
    for d in ("fastqc_multiqc", "fan_in_and_twins", "old_format_module"):
        assert sorted(p.name for p in (FIXTURES / d).iterdir()) == ["graph.json", "main.nf", "modules.json", "nextflow.config"]


# ---- regex-dollar-newline: name checks end with \Z, a trailing newline is not part of a name ------------------------------

def _hand_canonical(output="html"):
    return {"nodes": [node("qc", "fastqc"), node("report", "multiqc")], "edges": [edge("qc", output, "report")]}


def test_regex_dollar_newline_tc001_pipeline_name_with_newline_is_refused():
    # regex-dollar-newline TC-001
    canonical = norm(qc_graph())
    with pytest.raises(ValueError):
        compose().render(canonical, "abc\n", 1)


def test_regex_dollar_newline_tc002_node_id_with_newline_is_refused():
    # regex-dollar-newline TC-002
    assert "a\n" in refused({"nodes": [node("a\n", "fastqc")]})


def test_regex_dollar_newline_tc003_param_key_with_newline_is_refused():
    # regex-dollar-newline TC-003
    g = {"nodes": [node("qc", "fastqc", params={"ext.args\n": "-q"})]}
    canonical, problems = compose().normalize(g)
    if canonical is None:
        assert problems
        return
    with pytest.raises(ValueError):
        compose().render(canonical, "demo-qc", 1)


def test_regex_dollar_newline_tc004_output_name_with_newline_is_refused():
    # regex-dollar-newline TC-004
    with pytest.raises(ValueError):
        compose().render(_hand_canonical("x\n"), "demo-qc", 1)


def test_regex_dollar_newline_tc005_legal_pipeline_names_are_rendered():
    # regex-dollar-newline TC-005
    canonical = norm(qc_graph())
    for name in ("a", "a" + "b" * 39):
        assert compose().render(canonical, name, 1)["files"]["main.nf"]


def test_regex_dollar_newline_tc006_legal_node_ids_are_accepted():
    # regex-dollar-newline TC-006
    for nid in ("a", "a" + "b1_" * 10 + "c"):
        assert len(nid) <= 32
        norm({"nodes": [node(nid, "fastqc")]})
    assert len("a" + "b1_" * 10 + "c") == 32


def test_regex_dollar_newline_tc007_legal_param_keys_are_accepted():
    # regex-dollar-newline TC-007
    for key in ("ext.args", "ext.prefix"):
        norm({"nodes": [node("qc", "fastqc", params={key: "-q"})]})


def test_regex_dollar_newline_tc008_legal_output_names_pass_the_ident_check():
    # regex-dollar-newline TC-008 (the channel is not in the catalogue, so the later step may refuse it, but not with the ident message)
    for out in ("x", "out_1"):
        try:
            compose().render(_hand_canonical(out), "demo-qc", 1)
        except ValueError as e:
            raise AssertionError("legal output name %r refused: %s" % (out, e))


def test_regex_dollar_newline_tc050_old_refused_shapes_stay_refused():
    # regex-dollar-newline TC-050
    canonical = norm(qc_graph())
    for bad in ("a" * 41, "ABC"):
        with pytest.raises(ValueError):
            compose().render(canonical, bad, 1)
    assert "a" * 33 in refused({"nodes": [node("a" * 33, "fastqc")]})
