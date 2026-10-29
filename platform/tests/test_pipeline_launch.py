# Nothing existing: tests of sending a saved, checked composed pipeline through the platform's own confirmation page (spec 017d); no tool joins a canvas graph to a person's yes.
"""017d: `abf_platform.pipeline_launch` (the project of a composed pipeline) and `actions.request_pipeline_launch` (the way to the
confirmation page). Test cases are named in the comments (TC-001 ...), see specs/017d-launch-composed/test-case.md."""
import asyncio
import copy
import csv
import difflib
import io
import json
import re
import sqlite3
import time
from pathlib import Path

import pytest

from human_harness import World
from owner_harness import Duo, sql_rows

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
FIX = HERE / "fixtures" / "pipeline_launch"
COMPOSE_FIX = HERE / "fixtures" / "compose"
SHA = "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"
BAD = {"nodes": [{"id": "qc", "module": "fastqc"}, {"id": "s", "module": "samtools_sort"}],
       "edges": [{"from": {"node": "qc", "output": "html"}, "to": {"node": "s", "input": 2}}]}


def read(path):
    return Path(path).read_text(encoding="utf-8")


def pl():
    from abf_platform import pipeline_launch
    return pipeline_launch


def pipes():
    from abf_platform.actions import pipelines
    return pipelines


def qc_graph():
    return json.loads(read(FIX / "fastqc_multiqc" / "graph.json"))


def canonical_of(graph, data=None):
    from abf_platform import compose
    canonical, problems = compose.normalize(graph, data)
    assert not problems, problems
    return canonical


def qc_project(header=("sample", "reads")):
    return pl().build_project(canonical_of(qc_graph()), "demo-qc", 1, list(header))


# ---- synthetic catalogue and module files (the unit tests do not depend on the real modules) ---------------------------------

def mod(name, inputs, path=None):
    return {"name": name, "path": path or name, "description": "", "keywords": [], "tools": [],
            "inputs": [{"channel": c, "name": n, "type": t, "pattern": None, "optional": o} for c, n, t, o in inputs],
            "outputs": [{"channel": "out", "name": "result", "type": "file", "pattern": None}]}


def catalogue_of(*mods):
    return {"source": "nf-core/modules", "sha": SHA, "count": len(mods), "modules": list(mods), "errors": []}


def sources_of(*mods, main=None, extra=None):
    out = {}
    for m in mods:
        files = {"main.nf": (main or {}).get(m["path"], "process %s {\n}\n" % m["path"].upper())}
        files.update((extra or {}).get(m["path"], {}))
        out[m["path"]] = {"files": files, "unsupported": None}
    return {"source": "nf-core/modules", "sha": SHA, "modules": out}


META_READS = [(0, "meta", "map", False), (0, "reads", "file", False)]


def build(mods, nodes=None, header=("sample", "reads"), sources=None, edges=None):
    data = catalogue_of(*mods)
    graph = {"nodes": nodes or [{"id": "a", "module": mods[0]["name"]}], "edges": edges or []}
    return pl().build_project(canonical_of(graph, data), "demo", 1, list(header), data=data, sources=sources or sources_of(*mods))


def line_of(project, var="ch_a_in0"):
    return next(ln for ln in project["project"]["main.nf"].splitlines() if ln.startswith("    %s = " % var))


def refused_build(mods, match=None, **kw):
    with pytest.raises(pl().ProjectError) as e:
        build(mods, **kw)
    if match:
        assert re.search(match, str(e.value)), str(e.value)
    return e.value


# ---- US4: the project (build_project) -----------------------------------------------------------------------------------------

def test_golden_project_matches_the_hand_derived_files():
    # TC-032, TC-057 (modules.json as the compose step wrote it), TC-153 (the fixtures are there)
    got = qc_project()
    names = read(FIX / "fastqc_multiqc" / "files.txt").split()
    assert sorted(got["project"]) == sorted(names)
    assert got["project"]["main.nf"] == read(FIX / "fastqc_multiqc" / "main.nf")
    assert got["project"]["nextflow.config"] == read(FIX / "fastqc_multiqc" / "nextflow.config")
    assert got["project"]["modules.json"] == read(COMPOSE_FIX / "fastqc_multiqc" / "modules.json")
    from abf_platform import module_sources
    mods = module_sources.load()["modules"]
    for name in ("fastqc", "multiqc"):
        assert got["project"]["modules/nf-core/%s/main.nf" % name] == mods[name]["files"]["main.nf"]
    for need in ("graph.json", "samplesheet.csv", "main.nf", "nextflow.config", "files.txt"):
        assert (FIX / "fastqc_multiqc" / need).is_file()
    for need in ("catalogue.json", "sources.json", "graph_bin.json", "graph_list.json", "missing_column.csv"):
        assert (FIX / "unsupported" / need).is_file()


def test_project_is_deterministic_and_its_hash_is_the_canonical_json_hash():
    # TC-033
    import hashlib
    from abf_platform import common
    a, b = qc_project(), qc_project()
    assert a == b
    assert a["project_sha256"] == hashlib.sha256(common.canonical_json(a["project"])).hexdigest()


def test_main_differs_from_the_compose_golden_in_two_places_only():
    # TC-034, TC-035
    old = read(COMPOSE_FIX / "fastqc_multiqc" / "main.nf").splitlines()
    new = qc_project()["project"]["main.nf"].splitlines()
    diff = [ln for ln in difflib.ndiff(old, new) if ln[:2] in ("- ", "+ ")]
    assert [ln[2:] for ln in diff if ln[0] == "-"] == ["    ch_qc_in0 = Channel.empty()  // OPEN INPUT: qc input 0 (meta, reads)"]
    assert [ln[2:] for ln in diff if ln[0] == "+"] == [
        "    ch_rows = Channel.fromPath(params.input).splitCsv(header: true)",
        "    ch_qc_in0 = ch_rows.map { row -> [ [id: row.sample], file(row.reads, checkIfExists: true) ] }"]
    assert new[new.index("workflow {") + 1] == "    ch_rows = Channel.fromPath(params.input).splitCsv(header: true)"


def test_a_changed_line_shape_is_an_error(monkeypatch):
    # TC-036
    from abf_platform import compose
    real = compose.render

    def changed(*a, **k):
        out = real(*a, **k)
        out["files"]["main.nf"] = out["files"]["main.nf"].replace("Channel.empty()  // OPEN INPUT", "Channel.of()  // OPEN INPUT")
        return out

    monkeypatch.setattr(compose, "render", changed)
    with pytest.raises(pl().ProjectError):
        qc_project()


def test_a_graph_with_every_input_wired_has_no_sample_binding():
    # TC-037
    src, sink = mod("src", []), mod("sink", [(0, "y", "file", False)])
    nodes = [{"id": "a", "module": "sink"}, {"id": "b", "module": "src"}]
    edges = [{"from": {"node": "b", "output": "out"}, "to": {"node": "a", "input": 0}}]
    got = build([src, sink], nodes=nodes, edges=edges, header=["tag"])
    assert "ch_rows" not in got["project"]["main.nf"] and "row." not in got["project"]["main.nf"] and got["columns"] == []


@pytest.mark.parametrize("typ,name,element,columns", [
    ("string", "tag", "row.tag", ["tag"]),
    ("integer", "depth", "(row.depth as Integer)", ["depth"]),
    ("float", "rate", "(row.rate as Double)", ["rate"]),
    ("boolean", "flag", "row.flag.toBoolean()", ["flag"]),
    ("file", "reads", "file(row.reads, checkIfExists: true)", ["reads"]),
    ("directory", "indir", "file(row.indir, checkIfExists: true)", ["indir"]),
])
def test_each_record_type_has_one_fixed_form(typ, name, element, columns):
    # TC-038, TC-039, TC-040, TC-041, TC-042, TC-043 (one non-meta record, no meta: the bare value)
    m = mod("one", [(0, name, typ, False)])
    got = build([m], header=[name])
    assert line_of(got) == "    ch_a_in0 = ch_rows.map { row -> %s }" % element
    assert got["columns"] == columns
    assert got["path_columns"] == ([name] if typ in ("file", "directory") else [])


def test_meta_comes_first_and_several_records_are_bracketed():
    # TC-044
    got = build([mod("two", [(0, "meta", "map", False), (0, "x", "string", False), (0, "y", "integer", False)])], header=["sample", "x", "y"])
    assert line_of(got) == "    ch_a_in0 = ch_rows.map { row -> [ [id: row.sample], row.x, (row.y as Integer) ] }"
    got = build([mod("pair", [(0, "x", "string", False), (0, "y", "file", False)])], header=["x", "y"])
    assert line_of(got) == "    ch_a_in0 = ch_rows.map { row -> [ row.x, file(row.y, checkIfExists: true) ] }"


@pytest.mark.parametrize("record", [(0, "items", "list", False), (0, "items", None, False), (0, "items", "tuple", False)])
def test_unsupported_input_type_names_node_input_and_record(record):
    # TC-045, TC-046
    err = refused_build([mod("listy", [(0, "meta", "map", False), record])], nodes=[{"id": "n1", "module": "listy"}], header=["sample", "items"])
    text = str(err)
    assert "n1" in text and re.search(r"輸入 0|input 0", text) and "items" in text and re.search(r"[一-鿿]", text)


def test_the_unsupported_fixture_graph_is_refused_by_name():
    # TC-045 (fixture), TC-060 (the bin/ module), TC-167 (the same, one level up)
    data = json.loads(read(FIX / "unsupported" / "catalogue.json"))
    sources = json.loads(read(FIX / "unsupported" / "sources.json"))
    for graph, word in (("graph_list.json", "items"), ("graph_bin.json", "binmod")):
        canonical = canonical_of(json.loads(read(FIX / "unsupported" / graph)), data)
        with pytest.raises(pl().ProjectError) as e:
            pl().build_project(canonical, "demo", 1, ["sample", "reads"], data=data, sources=sources)
        assert word in str(e.value)
        if word == "binmod":
            assert "bin/" in str(e.value) and re.search(r"換成|use another", str(e.value))


def test_missing_required_column_is_named_in_plain_words():
    # TC-047, TC-048
    err = refused_build([mod("plain", META_READS)], header=["sample"])
    assert "樣本表需要這些欄" in str(err) and "sample" in str(err) and "reads" in str(err) and "缺" in str(err)
    fixture = read(FIX / "unsupported" / "missing_column.csv").splitlines()[0].split(",")
    err = refused_build([mod("plain", META_READS)], header=["reads"])
    assert "缺" in str(err) and "sample" in str(err)
    err = refused_build([mod("plain", META_READS)], header=fixture)
    assert "reads" in str(err)


def test_missing_optional_column_becomes_an_empty_list():
    # TC-049
    got = build([mod("opt", META_READS + [(0, "extra", "file", True)])], header=["sample", "reads"])
    assert line_of(got) == "    ch_a_in0 = ch_rows.map { row -> [ [id: row.sample], file(row.reads, checkIfExists: true), [] ] }"
    assert got["columns"][:2] == ["sample", "reads"]
    got = build([mod("opt1", [(0, "extra", "file", True)])], header=["other"])
    assert line_of(got) == "    ch_a_in0 = ch_rows.map { row -> [] }"


def test_channels_with_the_same_names_share_columns():
    # TC-050
    m1, m2 = mod("tool1", META_READS), mod("tool2", META_READS)
    got = build([m1, m2], nodes=[{"id": "a", "module": "tool1"}, {"id": "b", "module": "tool2"}], header=["sample", "reads"])
    assert line_of(got, "ch_a_in0") == line_of(got, "ch_b_in0").replace("ch_b_in0", "ch_a_in0")
    assert got["columns"] == ["sample", "reads"] and got["path_columns"] == ["reads"]


def test_same_name_different_type_is_refused():
    # TC-051
    m1, m2 = mod("tool1", META_READS), mod("tool2", [(0, "meta", "map", False), (0, "reads", "string", False)])
    refused_build([m1, m2], nodes=[{"id": "a", "module": "tool1"}, {"id": "b", "module": "tool2"}], match="reads")


@pytest.mark.parametrize("bad", ["a'b", "a b", "a$b", 'a"b', "1abc", "a-b", ""])
def test_unsafe_column_names_are_refused(bad):
    # TC-052
    refused_build([mod("unsafe", [(0, bad, "string", False)])], header=[bad])


def test_publish_block_is_appended_once_and_after_the_node_config():
    # TC-056
    config = qc_project()["project"]["nextflow.config"]
    assert config.count("// added by the platform at launch") == 1 and config.count("publishDir") == 1
    head, tail = config.split("// added by the platform at launch")
    assert "withName: 'FASTQC'" in head and "mode: 'copy'" in tail and "${params.outdir}" in tail and "toLowerCase()" in tail
    assert config.endswith("]\n") and "process.publishDir" in tail


def test_columns_and_path_columns_of_the_golden_graph():
    # TC-054
    got = qc_project()
    assert got["columns"] == ["sample", "reads"] and got["path_columns"] == ["reads"]


def _exact(total):
    """sources for one module whose main.nf makes the whole project exactly `total` bytes."""
    m = mod("big", META_READS)
    base = build([m], sources=sources_of(m, main={"big": ""}))
    used = sum(len(v.encode("utf-8")) for v in base["project"].values())
    return m, sources_of(m, main={"big": "x" * (total - used)})


def test_project_size_and_file_count_limits():
    # TC-058, TC-059
    limit = 2 * 1024 * 1024
    m, s = _exact(limit)
    got = build([m], sources=s)
    assert sum(len(v.encode("utf-8")) for v in got["project"].values()) == limit
    m, s = _exact(limit + 1)
    err = refused_build([m], sources=s)
    assert "2097152" in str(err) or "2 MiB" in str(err)
    m = mod("many", META_READS)
    many = {"templates/t%d.txt" % i: "x" for i in range(2000 - 4)}
    got = build([m], sources=sources_of(m, extra={"many": many}))
    assert len(got["project"]) == 2000
    many["templates/one-more.txt"] = "x"
    err = refused_build([m], sources=sources_of(m, extra={"many": many}))
    assert "2000" in str(err)


def test_a_module_that_includes_or_declares_a_workflow_is_refused():
    # TC-061, TC-062 (the real fastqc and multiqc are not caught: the golden test builds them)
    for text in ("include { X } from './other'\nprocess A {\n}\n", "workflow SUB {\n}\n"):
        m = mod("nest", META_READS)
        err = refused_build([m], sources=sources_of(m, main={"nest": text}))
        assert "nest" in str(err) and err.code == "UNSUPPORTED_MODULE" and "UNSUPPORTED_MODULE" in str(err)
    assert qc_project()["project"]["main.nf"]


def test_project_errors_say_what_happened_and_what_to_do_in_two_languages():
    # TC-063
    errors = []
    errors.append(refused_build([mod("plain", META_READS)], header=["sample"]))                       # TC-047
    errors.append(refused_build([mod("listy", [(0, "items", "list", False)])], header=["items"]))     # TC-045
    m1, m2 = mod("t1", META_READS), mod("t2", [(0, "meta", "map", False), (0, "reads", "string", False)])
    errors.append(refused_build([m1, m2], nodes=[{"id": "a", "module": "t1"}, {"id": "b", "module": "t2"}]))    # TC-051
    m, s = _exact(2 * 1024 * 1024 + 1)
    errors.append(refused_build([m], sources=s))                                                      # TC-058
    mm = mod("nest", META_READS)
    errors.append(refused_build([mm], sources=sources_of(mm, main={"nest": "workflow X {\n}\n"})))
    for e in errors:
        text = str(e)
        assert re.search(r"[一-鿿]", text) and re.search(r"\([A-Za-z]", text), text


def test_build_project_is_a_pure_function(monkeypatch):
    # TC-065
    import inspect
    text = inspect.getsource(pl().build_project)
    for word in ("store", "jobs", "confirm", "open(", "write", "socket"):
        assert word not in text, word
    import builtins

    def no_open(*a, **k):
        raise AssertionError("build_project opened a file")
    monkeypatch.setattr(builtins, "open", no_open)
    assert qc_project()["project"]["main.nf"]


# ---- the platform side: the way to the confirmation page ------------------------------------------------------------------------

@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def sheet(d, caller, n=2, header=("sample", "reads"), cells=None, samples=None):
    area = d.area(caller)
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(header)
    for i in range(1, n + 1):
        cell = cells[i - 1] if cells else "%s/rawdata/s%02d_R1.fastq.gz" % (area, i)
        wr.writerow([samples[i - 1] if samples else "s%02d" % i, cell])
    return buf.getvalue()


def make(d, caller=None, name="demo-qc", graph=None):
    caller = caller or d.a
    out = pipes().create_pipeline(d.state, name=name, graph=graph if graph is not None else qc_graph(), caller=caller)
    assert out["ok"], out
    return out["pipeline"]["id"]


def ask(d, caller, pid, **kw):
    from abf_platform import actions
    kw.setdefault("run_name", "run-one")
    if "samplesheet" not in kw:
        kw.setdefault("samplesheet_text", sheet(d, caller))
    kw.setdefault("ce_name", d.w.env_for(caller))
    return asyncio.run(actions.request_pipeline_launch(d.state, pipeline_id=pid, caller=caller, **kw))


def count(d, table, where=""):
    try:
        return sql_rows(d.state, "SELECT COUNT(*) AS n FROM %s %s" % (table, where))[0]["n"]
    except sqlite3.OperationalError:
        return 0


def counts(d):
    return (count(d, "jobs"), count(d, "confirmations"), count(d, "launches"))


def pending_bundle(d):
    return json.loads(sql_rows(d.state, "SELECT bundle_json FROM confirmations ORDER BY created_at DESC")[0]["bundle_json"])


def approve(d, out, caller=None):
    from abf_platform import actions
    return actions.approve(d.state, out["id"], confirmed_by=actions.PAGE, caller=caller or d.a)


def words(text, *names):
    for n in names:
        text = re.sub(re.escape(str(n)), "<n>", str(text))
    return text


def test_a_saved_graph_goes_to_the_confirmation_page_and_nothing_runs_until_the_yes(d):
    # TC-001, TC-002, TC-003, TC-004
    pid = make(d)
    out = ask(d, d.a, pid)
    assert out["ok"], out
    assert out["state"] == "pending" and "/c/%s" % out["id"] in out["confirmation_url"]
    assert count(d, "jobs", "WHERE kind = 'launch_nextflow'") == 0 and count(d, "confirmations") == 1
    rid, job_id = approve(d, out)
    jobs = sql_rows(d.state, "SELECT * FROM jobs WHERE kind = 'launch_nextflow'")
    assert len(jobs) == 1 and jobs[0]["id"] == job_id
    from abf_platform import common
    conf = sql_rows(d.state, "SELECT * FROM confirmations WHERE id = ?", (rid,))[0]
    assert json.loads(jobs[0]["args_json"])["bundle_sha256"] == conf["sha256"] == common.bundle_sha256(json.loads(conf["bundle_json"]))
    again = ask(d, d.a, pid)
    assert again["state"] == "queued" and again["job_id"] == job_id
    assert count(d, "jobs", "WHERE kind = 'launch_nextflow'") == 1 and count(d, "confirmations") == 1


def test_the_page_facts_show_the_composed_name_and_version(d):
    # TC-005, TC-007
    from abf_platform import actions
    pid = make(d)
    for i in (2, 3):
        g = copy.deepcopy(qc_graph())
        g["nodes"][0]["params"]["ext.args"] = "--quiet%s" % ("x" * i)
        assert pipes().update_pipeline(d.state, pid, graph=g, caller=d.a)["ok"]
    out = ask(d, d.a, pid)
    facts = actions.request_facts(d.state, out["id"])
    assert facts["pipeline"] == "abf-composed/demo-qc" and facts["revision"] == "0.3.0" and facts["what"] == "launch"
    first = ask(d, d.a, pid, version=1, run_name="run-two")
    assert actions.request_facts(d.state, first["id"])["revision"] == "0.1.0"


def test_the_open_requests_limit_is_shared_with_nf_core_launches(d):
    # TC-006
    from abf_platform import actions
    pid = make(d)
    for i in range(5):
        assert ask(d, d.a, pid, run_name="comp-%d" % i)["state"] == "pending"
    for i in range(5):
        out = asyncio.run(actions.request_launch(d.state, pipeline="nf-core/ampliseq", revision="2.18.0", run_name="nfc-%d" % i,
                                                 samplesheet_text="sample,fastq_1\ns1,%s/rawdata/s1.fq\n" % d.area(d.a),
                                                 ce_name="lab-a", caller=d.a))
        assert out["state"] == "pending", out
    over_c = ask(d, d.a, pid, run_name="comp-x")
    over_n = asyncio.run(actions.request_launch(d.state, pipeline="nf-core/ampliseq", revision="2.18.0", run_name="nfc-x",
                                                samplesheet_text="sample,fastq_1\ns1,%s/rawdata/s1.fq\n" % d.area(d.a),
                                                ce_name="lab-a", caller=d.a))
    assert over_c["ok"] is False and over_n["ok"] is False and over_c["message"] == over_n["message"]
    assert count(d, "confirmations", "WHERE state = 'pending'") == 10


def test_a_missing_version_lists_the_versions_there_are(d):
    # TC-008
    pid = make(d)
    g = copy.deepcopy(qc_graph())
    g["nodes"][0]["params"]["ext.args"] = "--other"
    assert pipes().update_pipeline(d.state, pid, graph=g, caller=d.a)["ok"]
    before = counts(d)
    out = ask(d, d.a, pid, version=9)
    assert out["ok"] is False and "1、2" in out["message"] and out["message"].startswith("未送出：")
    assert counts(d) == before


def test_the_samplesheet_input_rules_are_those_of_a_launch(d):
    # TC-009, TC-010, TC-011, TC-012, TC-013
    pid = make(d)
    both = ask(d, d.a, pid, samplesheet="x.csv", samplesheet_text=sheet(d, d.a))
    neither = ask(d, d.a, pid, samplesheet=None, samplesheet_text=None)
    assert both["message"].startswith("未送出：") and neither["message"].startswith("未送出：") and "samplesheet" in both["message"]
    elsewhere = ask(d, d.a, pid, samplesheet="/etc/hostname", samplesheet_text=None)
    assert elsewhere["ok"] is False and "上傳" in elsewhere["message"]
    for bad in ({"input": "x"}, {"outdir": "x"}):
        out = ask(d, d.a, pid, params=bad)
        assert out["ok"] is False and list(bad)[0] in out["message"]
    assert ask(d, d.a, pid, params=["x"])["message"].startswith("params 必須是名稱到值的對照")
    assert count(d, "confirmations") == 0
    first = ask(d, d.a, pid)
    approve(d, first)
    other = ask(d, d.a, pid, samplesheet_text=sheet(d, d.a, n=3))
    from abf_platform import jobs
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_run_name(d.state, "run-one", time.time, d.a.user_id)
    assert other["ok"] is False and str(e.value) in other["message"] and other["message"].startswith("未送出：")


def test_the_two_requests_share_one_back_half_and_the_signatures_are_those_named():
    # TC-014, TC-016
    import inspect
    from abf_platform import actions
    assert "_finish_launch(" in inspect.getsource(actions.request_launch) and "_finish_launch(" in inspect.getsource(actions.request_pipeline_launch)
    for fn in (actions.request_launch, actions.request_pipeline_launch):
        assert "_ask(" not in inspect.getsource(fn) and "find_approved" not in inspect.getsource(fn)
    old = list(inspect.signature(actions.request_launch).parameters)
    assert old == ["platform_path", "pipeline", "revision", "run_name", "samplesheet", "samplesheet_text", "ce_name", "params", "path_columns", "dataset", "dataset_version",
                   "caller", "person", "clock", "remote"]
    new = list(inspect.signature(actions.request_pipeline_launch).parameters)
    assert new == ["platform_path", "pipeline_id", "version", "run_name", "samplesheet", "samplesheet_text", "ce_name", "params", "caller",
                   "person", "clock", "remote", "data"]
    assert inspect.iscoroutinefunction(actions.request_pipeline_launch)
    from abf_platform import confirm
    assert "request_pipeline_launch" not in repr(getattr(confirm, "REQUEST_TOOLS", ""))


# ---- US2: the gate ---------------------------------------------------------------------------------------------------------------

def test_a_graph_with_an_error_finding_is_refused_with_the_findings_in_plain_words(d):
    # TC-017, TC-018, TC-024
    from abf_platform import validate
    pid = make(d, graph=BAD)
    errors = [f["message"] for f in validate.validate(canonical_of(BAD))["findings"] if f["severity"] == "error"]
    assert errors
    before, v_before = counts(d), count(d, "pipeline_validations")
    out = ask(d, d.a, pid)
    assert out["ok"] is False and out["sent"] is False
    assert errors[0] in out["message"] and "存成新版本" in out["message"]
    assert counts(d) == before and count(d, "pipeline_validations") == v_before


def test_at_most_five_findings_are_listed_and_the_rest_counted(d, monkeypatch):
    # TC-019
    from abf_platform import validate
    pid = make(d)
    fake = {"ok": False, "checks": ["static"], "catalogue_sha": SHA, "open_inputs": [],
            "findings": [{"node": None, "channel": None, "code": "X", "severity": "error", "message": "problem number %d" % i} for i in range(8)]}
    monkeypatch.setattr(validate, "validate", lambda canonical, data=None: fake)
    out = ask(d, d.a, pid)
    assert out["ok"] is False
    shown = re.findall(r"problem number \d", out["message"])
    assert shown == ["problem number %d" % i for i in range(5)] and "另有 3 條" in out["message"]


def test_a_graph_with_only_warnings_goes_through_and_the_gate_asks_nothing_stored(d):
    # TC-020, TC-023, TC-024, TC-025
    pid = make(d)
    assert count(d, "pipeline_validations") == 0
    out = ask(d, d.a, pid)
    assert out["state"] == "pending" and count(d, "pipeline_validations") == 0


def test_the_gate_recomputes_and_does_not_trust_a_stored_result(d):
    # TC-021, TC-022
    from abf_platform import catalogue
    pid = make(d)
    assert pipes().validate_pipeline(d.state, pid, caller=d.a)["validation"]["ok"] is True
    stale = dict(catalogue.load(), sha="f" * 40)
    out = ask(d, d.a, pid, data=stale)
    assert out["ok"] is False and out["sent"] is False and count(d, "confirmations") == 0
    # the other way round: a stored error, a graph that has none now
    pid2 = make(d, name="other-qc")
    assert pipes().validate_pipeline(d.state, pid2, caller=d.a, data=stale)["validation"]["ok"] is False
    assert ask(d, d.a, pid2, run_name="run-two")["state"] == "pending"


# ---- US3: whose it is ----------------------------------------------------------------------------------------------------------------

def test_somebody_elses_pipeline_answers_like_a_missing_one(d):
    # TC-026, TC-027, TC-028, TC-030
    a_id = make(d, d.a)
    before = counts(d)
    theirs = ask(d, d.b, a_id)
    missing = ask(d, d.b, 9999)
    assert theirs["ok"] is False and words(theirs["message"], a_id) == words(missing["message"], 9999)
    assert "找不到這個組合" in missing["message"]
    assert counts(d) == before
    assert ask(d, d.a, a_id)["state"] == "pending"
    assert ask(d, d.a, 9999)["message"].count("找不到這個組合") == 1


def test_an_environment_of_somebody_else_is_refused_as_in_a_launch(d):
    # TC-029
    from abf_platform import actions
    b_id = make(d, d.b, name="bobs-qc")
    mine = d.w.env_for(d.b)
    assert mine != "lab-a"
    out = ask(d, d.b, b_id, ce_name="lab-a")
    nf = asyncio.run(actions.request_launch(d.state, pipeline="nf-core/ampliseq", revision="2.18.0", run_name="run-one",
                                            samplesheet_text="sample,fastq_1\ns1,%s/rawdata/s1.fq\n" % d.area(d.b), ce_name="lab-a", caller=d.b))
    assert out["ok"] is False and nf["ok"] is False and out["message"] == nf["message"]


def test_somebody_elses_yes_does_not_count(d):
    # TC-031, TC-172 (the model cannot give the yes either)
    from abf_platform import actions, confirm, jobs
    out = ask(d, d.a, make(d))
    with pytest.raises((confirm.NotApproved, jobs.JobRefused)):
        approve(d, out, caller=d.b)
    with pytest.raises((confirm.NotApproved, jobs.JobRefused)):
        actions.approve(d.state, out["id"], confirmed_by=actions.PAGE, caller=None)
    for fake in ("PAGE", "TERMINAL", object(), actions.TERMINAL):
        with pytest.raises(jobs.JobRefused):
            actions.approve(d.state, out["id"], confirmed_by=fake, caller=d.a)
    assert count(d, "jobs", "WHERE kind = 'launch_nextflow'") == 0


# ---- the bundle ------------------------------------------------------------------------------------------------------------------------

def test_the_bundle_of_a_composed_launch(d):
    # TC-089, TC-090, TC-105, TC-171
    import hashlib
    from abf_platform import common
    out = ask(d, d.a, make(d))
    b = pending_bundle(d)
    assert set(b) == {"version", "agent", "ce", "run_name", "run_folder", "pipeline", "revision", "samplesheet", "params", "path_columns",
                      "account", "tower", "files", "pipeline_source", "project", "upload_paths"}
    assert b["pipeline"] == "abf-composed/demo-qc" and b["revision"] == "0.1.0"
    assert sorted(b["pipeline_source"]) == ["kind", "pipeline_id", "project_sha256", "version"] and b["pipeline_source"]["kind"] == "composed"
    assert b["pipeline_source"]["project_sha256"] == hashlib.sha256(common.canonical_json(b["project"])).hexdigest()
    assert not [k for k in b if "tar" in k] and all(isinstance(v, str) for v in b["project"].values())
    changed = copy.deepcopy(b)
    changed["project"]["modules/nf-core/fastqc/main.nf"] += " "
    assert common.bundle_sha256(changed) != common.bundle_sha256(b) and out["ok"]


def test_a_non_composed_bundle_is_byte_identical_to_before():
    # TC-136: the value is what the base branch computes for these inputs (taken from a run of that branch, not from this code)
    from abf_platform import common
    from test_launch_bundle import render
    assert common.bundle_sha256(render()) == "1d240f37a88d46df49139f42d35dd4e30537fe375919c50f53466686f19606b3"


def test_user_text_never_reaches_groovy_and_a_cell_is_one_value(d):
    # TC-053, TC-169
    out = ask(d, d.a, make(d), samplesheet_text=sheet(d, d.a, samples=["x'; evil()", "y\"; evil()"]))
    assert out["state"] == "pending"
    project = pending_bundle(d)["project"]
    assert "evil" not in json.dumps(project)
    two = ask(d, d.a, make(d, name="two-qc"), run_name="run-two",
              samplesheet_text=sheet(d, d.a, cells=["%s/rawdata/a.fq %s/rawdata/b.fq" % (d.area(d.a), d.area(d.a)), "%s/rawdata/c.fq" % d.area(d.a)]))
    assert two["ok"] is False or two["state"] == "pending"
    main = json.loads(sql_rows(d.state, "SELECT bundle_json FROM confirmations ORDER BY created_at DESC")[0]["bundle_json"])["project"]["main.nf"]
    assert not re.findall(r"\.split\(|tokenize|\.toList|\.collect", main)


def test_a_path_outside_the_read_roots_is_refused_as_in_a_launch(d):
    # TC-055
    pid = make(d)
    out = ask(d, d.a, pid, samplesheet_text=sheet(d, d.a, cells=["/etc/passwd", "%s/rawdata/ok.fq" % d.area(d.a)]))
    assert out["ok"] is False and "路徑" in out["message"] and count(d, "confirmations") == 0


def test_a_project_error_is_said_as_not_sent_and_writes_nothing(d):
    # TC-064
    pid = make(d)
    before = counts(d)
    out = ask(d, d.a, pid, samplesheet_text=sheet(d, d.a, header=("sample", "files")))
    assert out["ok"] is False and out["message"].startswith("未送出：") and "樣本表需要這些欄" in out["message"]
    assert counts(d) == before


# ---- build.py ------------------------------------------------------------------------------------------------------------------------

def run_without_sockets(coro):
    """Run a coroutine with socket.socket turned into a trap (the event loop's own pair of sockets is made before the trap is set)."""
    import socket

    async def go():
        real = socket.socket

        def no_socket(*a, **k):
            raise AssertionError("a socket was opened")
        socket.socket = no_socket
        try:
            return await coro
        finally:
            socket.socket = real
    return asyncio.run(go())


def test_the_reserved_owner_cannot_be_launched_as_an_nf_core_pipeline(d):
    # TC-125, TC-126, TC-127, TC-128, TC-140 (no socket)
    from abf_launch import build
    from abf_platform import actions

    before = counts(d)
    out = run_without_sockets(actions.request_launch(d.state, pipeline="abf-composed/x", revision="0.1.0", run_name="run-one",
                                             samplesheet_text="sample,fastq_1\ns1,%s/rawdata/s1.fq\n" % d.area(d.a), ce_name="lab-a", caller=d.a))
    assert out["ok"] is False and "組合流程只能從畫布送出（畫布送出介面尚未開放）" in out["message"] and "launch_pipeline" not in out["message"]
    assert re.search(r"\(.*canvas|canvas.*\)", out["message"], re.I) or "canvas" in out["message"].lower()
    assert counts(d) == before
    with pytest.raises(build.Refusal):
        build.prepare_launch(d.state, ce="lab-a", pipeline="abf-composed/x", revision="0.1.0", run_name="run-one",
                             samplesheet_raw=b"sample,fastq_1\ns1,%s/rawdata/s1.fq\n" % str(d.area(d.a)).encode(), owner=d.a.user_id)
    # building a composed launch to the page opens no socket either
    pid = make(d)
    again = run_without_sockets(actions.request_pipeline_launch(d.state, pipeline_id=pid, run_name="run-one", samplesheet_text=sheet(d, d.a),
                                                               ce_name="lab-a", caller=d.a))
    assert again["state"] == "pending"


def test_a_prefilled_composed_name_is_refused_when_sent_as_nf_core(d):
    # TC-126
    from abf_platform import actions
    out = ask(d, d.a, make(d))
    rid, job_id = approve(d, out)
    sql = sql_rows(d.state, "SELECT run_name FROM launches")
    assert sql and sql[0]["run_name"] == "run-one"
    fill = actions.launch_prefill(d.state, "run-one", caller=d.a)
    if fill.get("kept"):
        assert fill["pipeline"].startswith("abf-composed/")
        again = asyncio.run(actions.request_launch(d.state, pipeline=fill["pipeline"], revision=fill["revision"], run_name="run-three",
                                                   samplesheet_text="sample,fastq_1\ns1,%s/rawdata/s1.fq\n" % d.area(d.a), ce_name="lab-a",
                                                   caller=d.a))
        assert again["ok"] is False and "組合流程只能從畫布送出" in again["message"]


@pytest.fixture
def rig(tmp_path, monkeypatch):
    from resume_harness import Rig
    return Rig(tmp_path, monkeypatch)


def _composed_failed_run(rig, run="run-c"):
    from abf_launch import build
    from abf_platform import actions
    pid = pipes().create_pipeline(rig.state, name="demo-qc", graph=qc_graph(), caller=None)["pipeline"]["id"]
    ce, bundle = pl().prepare(rig.state, pipeline_id=pid, version=None, run_name=run, samplesheet_raw=sheet_for_rig(rig).encode("utf-8"),
                              ce="lab-a", params=None, caller=None, area=None)
    _, job_id = actions.launch(rig.state, ce, bundle, confirmed_by=actions.TERMINAL, caller=None)
    rig.hand_over(job_id, run)
    rig.set_run(run, "failed")
    return bundle


def sheet_for_rig(rig):
    return "sample,reads\ns1,/data/storage/rawdata/s1.fq\ns2,/data/storage/rawdata/s2.fq\n"


def test_resume_and_relaunch_of_a_composed_run_are_refused_in_plain_words(rig):
    # TC-129, TC-130
    from abf_launch import build
    _composed_failed_run(rig)
    said = "自訂組合的 run 目前不能續跑或原樣重跑；請回到組合頁，用同一個版本重新送出（會再問一次確認）(a run of a composed pipeline cannot be resumed or relaunched yet; send the same version again from the pipeline page, which asks for a new yes)"
    for verb in ("resume", "relaunch"):
        with pytest.raises(build.Refusal) as e:
            rig.prepare(verb, "run-c")
        assert str(e.value) == said


def test_the_screens_of_a_composed_launch(rig):
    # TC-131, TC-132, TC-133, TC-134, TC-174
    from abf_launch import build
    bundle = _composed_failed_run(rig)
    text = build.as_text(build.launch_screen(bundle, "lab-a"))
    project = bundle["project"]
    assert "abf-composed/demo-qc" in text and "0.1.0" in text and bundle["pipeline_source"]["project_sha256"] in text
    assert [ln for ln in text.splitlines() if "專案檔" in ln and str(len(project)) in ln]
    assert text.index("0.1.0") < text.index(bundle["pipeline_source"]["project_sha256"])
    for name in ("main.nf", "nextflow.config"):
        for ln in project[name].splitlines():
            if ln.strip():
                assert ln in text, (name, ln)
    import hashlib
    for key in sorted(project):
        if key.startswith("modules/"):
            body = project[key]
            assert key in text and str(len(body.encode("utf-8"))) in text and hashlib.sha256(body.encode("utf-8")).hexdigest()[:12] in text
            assert body.splitlines()[0] not in text.replace(key, "")
    assert "nf-core/modules" in text and "原檔" in text and SHA in text
    assert "pipeline/main.nf" in text and "exec nextflow run" in text
    hostile = copy.deepcopy(bundle)
    hostile["project"]["main.nf"] += "\x1b[31mred\x1b[0m\x07\n"
    shown = "\n".join(build.launch_screen(hostile, "lab-a"))
    assert "\x1b" not in shown and "\x07" not in shown and "\\x1b" in shown


def test_the_screen_of_an_nf_core_launch_is_unchanged(rig):
    # TC-135
    from abf_launch import build, terminal
    import io as _io, csv as _csv
    bundle = rig.first(run="run-n", finish=False)
    got = build.launch_screen(bundle, "lab-a")
    ce = bundle["ce"]
    want = [terminal.PREFIX + "== 送出確認：下面就是會被送出的全部內容 =="]
    for label, value in (("管線", bundle["pipeline"]), ("版本", bundle["revision"]), ("環境", "lab-a"), ("代理", bundle["agent"]),
                         ("run 名稱", bundle["run_name"]), ("專屬資料夾", bundle["run_folder"]), ("計費帳號", bundle["account"]),
                         ("主控佇列", ce["headQueue"]), ("主控送出選項", ce["headJobOptions"] or "(無)")):
        want.append(terminal.pair(label, value))
    rows = bundle["samplesheet"]
    want.append(terminal.PREFIX + "== samplesheet.csv（%d 列資料）==" % (len(rows) - 1))
    for row in rows:
        buf = _io.StringIO()
        _csv.writer(buf, lineterminator="").writerow(row)
        want.append(terminal.PREFIX + terminal.esc(buf.getvalue()))
    for name in ("params.yaml", "nextflow.config", "head.sh"):
        want += terminal.block(name, bundle["files"][name])
    assert got == want


# ---- what did not change ---------------------------------------------------------------------------------------------------------------

def test_no_table_or_column_changed(d):
    # TC-137, TC-165
    from abf_platform import store
    cols = [c["name"] for c in sql_rows(d.state, "PRAGMA table_info(launches)")]
    assert cols == ["id", "run_name", "slurm_job_id", "run_folder", "ce", "agent", "confirmed_at", "submitted_at", "cancel_requested_at",
                    "job_id", "user_id", "parent_run", "attempt", "attempt_kind", "work_cleaned_at"]
    for word in ("project", "pipeline_source", "composed", "abf-composed"):
        assert word not in store.STATE_SCHEMA
    make(d)
    assert {r["name"] for r in sql_rows(d.state, "SELECT name FROM sqlite_master WHERE type = 'table'")} >= {"pipelines", "pipeline_versions"}


def test_error_messages_hide_internals_and_secrets(d):
    # TC-141, TC-142
    pid = make(d)
    bad = make(d, name="bad-qc", graph=BAD)
    texts = [ask(d, d.a, pid, version=9)["message"], ask(d, d.a, 4242)["message"],
             ask(d, d.a, pid, samplesheet_text=sheet(d, d.a, header=("sample", "x")))["message"], ask(d, d.a, bad)["message"]]
    for t in texts:
        assert not re.search(r"Traceback|SELECT |INSERT |platform\.db|sqlite|/home/|/work/", t), t
        assert re.search(r"[一-鿿]", t)
    ok = ask(d, d.a, pid)
    row = sql_rows(d.state, "SELECT bundle_json, screen_text FROM confirmations")[0]
    stored = row["bundle_json"] + row["screen_text"]
    from human_harness import PASSWORD
    for secret in (PASSWORD, "tower.token'"):
        assert secret not in stored and secret not in ok["message"] and secret not in ok["summary"]
    head = json.loads(row["bundle_json"])["files"]["head.sh"]
    assert 'export TOWER_ACCESS_TOKEN="$(cat tower.token)"' in head      # the token is read from the file, never written into a script


def test_a_validation_does_not_send_anything(d):
    # TC-166
    pid = make(d)
    assert pipes().validate_pipeline(d.state, pid, caller=d.a)["validation"]["ok"] is True
    assert count(d, "jobs", "WHERE kind = 'launch_nextflow'") == 0 and count(d, "confirmations") == 0


def test_a_list_input_and_a_bin_or_nested_module_are_refused_before_the_page(d, monkeypatch):
    # TC-167, TC-168
    from abf_platform import catalogue, module_sources
    data = catalogue.load()
    listed = next(m for m in data["modules"] if any(i["type"] == "list" and i["channel"] == 0 for i in m["inputs"])
                  and module_sources.load()["modules"][m["path"]]["unsupported"] is None)
    pid = make(d, graph={"nodes": [{"id": "x", "module": listed["name"]}]})
    out = ask(d, d.a, pid)
    assert out["ok"] is False and "x" in out["message"] and "list" in out["message"] and count(d, "confirmations") == 0
    real = module_sources.load()
    fake = copy.deepcopy(real)
    fake["modules"]["fastqc"] = {"files": {}, "unsupported": "需要 bin/ 目錄，目前無法帶到站台 (needs a bin/ folder)"}
    monkeypatch.setattr(module_sources, "load", lambda *a, **k: fake)
    out = ask(d, d.a, make(d, name="qc-one"), run_name="run-bin")
    assert out["ok"] is False and "fastqc" in out["message"] and "bin/" in out["message"]
    fake["modules"]["fastqc"] = {"files": {"main.nf": "include { A } from './x'\nprocess FASTQC {\n}\n"}, "unsupported": None}
    out = ask(d, d.a, make(d, name="qc-two"), run_name="run-inc")
    assert out["ok"] is False and "fastqc" in out["message"] and "UNSUPPORTED_MODULE" in out["message"]
    assert count(d, "confirmations") == 0 and count(d, "jobs", "WHERE kind = 'launch_nextflow'") == 0


# ---- the source of it all ----------------------------------------------------------------------------------------------------------------

def test_the_sources_hold_no_program_or_run_words():
    # TC-143, TC-144
    for f in ("abf_platform/pipeline_launch.py", "abf_platform/module_sources.py", "abf_launch/build.py"):
        text = read(PLATFORM / f)
        for word in ("subprocess", "sbatch", "nextflow run", "os.system", "Popen"):
            assert word not in text, (f, word)
    actions = read(PLATFORM / "abf_platform" / "actions" / "__init__.py")
    for word in ("compose", "composed", "abf-composed"):
        assert word not in actions, word
    assert "pipeline_launch.prepare(" in actions and re.search(r"from \.\. import [^\n]*pipeline_launch|from \.\.pipeline_launch import", actions)
    for f in ("abf_station/launch.py", "abf_launch/build.py", "abf_platform/pipeline_launch.py"):
        assert "composed" in read(PLATFORM / f)


def test_no_new_public_name_in_the_tool_or_web_layers():
    # TC-161: the outer names stay for 017e
    for f in ("mcp_server.py", "web.py", "web_board.py"):
        text = read(PLATFORM / "abf_platform" / f)
        # launch-pipeline-mcp (017e): the tool name launch_pipeline now belongs in mcp_server.py; every other name stays out
        if f == "mcp_server.py":
            text = text.replace("request_pipeline_launch", "").replace("launch_pipeline", "")
        assert "pipeline_launch" not in text and "launch_pipeline" not in text, f
    assert "pipeline_launch" not in read(PLATFORM / "abf_station" / "handlers.py")
