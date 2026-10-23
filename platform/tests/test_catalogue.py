# Nothing existing: the snapshot is nf-core's own module metadata, flattened; the repository has no module catalogue.
"""Tests for platform/abf_platform/catalogue.py (spec 017a; TC ids in comments)."""
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PLATFORM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_DIR.parent
PKG = PLATFORM_DIR / "abf_platform"
sys.path.insert(0, str(PLATFORM_DIR))

from abf_platform import catalogue  # noqa: E402

# cluster-looking prefixes are built from pieces so this file itself holds no such path (TC-072)
HOME = "/ho" + "me/"
SCRATCH = "/scra" + "tch/"
LUSTRE = "/lus" + "tre/"

FASTQC = ("fastqc", {
    "name": "fastqc", "description": "Run FastQC on sequenced reads\n",
    "keywords": ["quality control", "qc"],
    "tools": [{"fastqc": {"description": "FastQC gives general quality metrics.", "homepage": "https://www.bioinformatics.babraham.ac.uk/projects/fastqc/", "licence": ["GPL-2.0-only"]}}],
    "input": [[{"meta": {"type": "map", "description": "Groovy Map"}}, {"reads": {"type": "file", "description": "FastQ files"}}]],
    "output": {"html": [[{"meta": {"type": "map"}}, {"*.html": {"type": "file", "pattern": "*_{fastqc.html}"}}]],
               "zip": [[{"meta": {"type": "map"}}, {"*.zip": {"type": "file", "pattern": "*_{fastqc.zip}"}}]],
               "versions_fastqc": [[{"${task.process}": {"type": "string"}}]]},
    "topics": {"versions": [[{"${task.process}": {"type": "string"}}]]}})
SAMTOOLS_SORT = ("samtools/sort", {
    "name": "samtools_sort", "description": "Sort SAM/BAM/CRAM file",
    "keywords": ["sort", "bam"],
    "tools": [{"samtools": {"homepage": "http://www.htslib.org/", "licence": "MIT"}}],
    "input": [{"meta": {"type": "map"}}, {"bam": {"type": "file", "pattern": "*.{bam,cram,sam}"}}],
    "output": [{"meta": {"type": "map"}}, {"bam": {"type": "file", "pattern": "*.{bam}"}}, {"versions": {"type": "file", "pattern": "versions.yml"}}]})
BROKEN = ("broken/one", {"description": "no name here"})

GOLDEN = {"source": "nf-core/modules", "sha": "abc123", "count": 2,
 "modules": [
  {"name": "fastqc", "path": "fastqc", "description": "Run FastQC on sequenced reads", "keywords": ["quality control", "qc"],
   "tools": [{"name": "fastqc", "homepage": "https://www.bioinformatics.babraham.ac.uk/projects/fastqc/", "licence": ["GPL-2.0-only"]}],
   "inputs": [{"channel": 0, "name": "meta", "type": "map", "pattern": None, "optional": False}, {"channel": 0, "name": "reads", "type": "file", "pattern": None, "optional": False}],
   "outputs": [{"channel": "html", "name": "meta", "type": "map", "pattern": None}, {"channel": "html", "name": "*.html", "type": "file", "pattern": "*_{fastqc.html}"},
               {"channel": "zip", "name": "meta", "type": "map", "pattern": None}, {"channel": "zip", "name": "*.zip", "type": "file", "pattern": "*_{fastqc.zip}"}]},
  {"name": "samtools_sort", "path": "samtools/sort", "description": "Sort SAM/BAM/CRAM file", "keywords": ["sort", "bam"],
   "tools": [{"name": "samtools", "homepage": "http://www.htslib.org/", "licence": ["MIT"]}],
   "inputs": [{"channel": 0, "name": "meta", "type": "map", "pattern": None, "optional": False}, {"channel": 1, "name": "bam", "type": "file", "pattern": "*.{bam,cram,sam}", "optional": False}],
   "outputs": [{"channel": "meta", "name": "meta", "type": "map", "pattern": None}, {"channel": "bam", "name": "bam", "type": "file", "pattern": "*.{bam}"}]}],
 "errors": [{"path": "bad/yaml", "reason": "while parsing a block mapping"}, {"path": "broken/one", "reason": "meta.yml has no name"}]}

ITEMS = [SAMTOOLS_SORT, BROKEN, FASTQC, ("bad/yaml", "while parsing a block mapping")]


def snap():
    return catalogue.build_snapshot(ITEMS, "abc123")


def fake(name, path=None, keywords=(), description=""):
    return {"name": name, "path": path or name, "description": description, "keywords": list(keywords),
            "tools": [], "inputs": [], "outputs": []}


def data_of(*mods):
    return {"source": "nf-core/modules", "sha": "s", "count": len(mods), "modules": list(mods), "errors": []}


# ---- US1: flatten / snapshot ----------------------------------------------------------

def test_snapshot_of_three_fixtures_equals_the_golden():
    # TC-001
    assert snap() == GOLDEN


def test_modules_sorted_by_name_then_path():
    # TC-002
    items = [("z/y", {"name": "zed"}), ("b/x", {"name": "same"}), ("a/x", {"name": "same"})]
    got = catalogue.build_snapshot(items, "s")
    assert [(m["name"], m["path"]) for m in got["modules"]] == [("same", "a/x"), ("same", "b/x"), ("zed", "z/y")]


def test_key_order_and_no_generated_at():
    # TC-003
    s = snap()
    assert list(s) == ["source", "sha", "count", "modules", "errors"]
    for m in s["modules"]:
        assert list(m) == ["name", "path", "description", "keywords", "tools", "inputs", "outputs"]
    assert "generated_at" not in catalogue.dumps(s)


def test_description_whitespace_is_squeezed():
    # TC-004
    assert catalogue.flatten("a", {"name": "a", "description": "  a\n b\t c "})["description"] == "a b c"
    assert catalogue.flatten("a", {"name": "a"})["description"] == ""


def test_keywords_keep_only_strings():
    # TC-005
    assert catalogue.flatten("a", {"name": "a", "keywords": ["a", 3, None, "b"]})["keywords"] == ["a", "b"]
    assert catalogue.flatten("a", {"name": "a"})["keywords"] == []


def test_tools_shape_and_licence():
    # TC-006
    meta = {"name": "a", "tools": [{"x": {"homepage": "h", "licence": "MIT"}}, {"y": {"description": "d"}}]}
    got = catalogue.flatten("a", meta)["tools"]
    assert got == [{"name": "x", "homepage": "h", "licence": ["MIT"]}, {"name": "y", "homepage": None, "licence": []}]


def test_inputs_new_format_channels():
    # TC-007
    meta = {"name": "a", "input": [[{"meta": {"type": "map"}}, {"reads": {"type": "file"}}], [{"index": {"type": "file"}}]]}
    got = catalogue.flatten("a", meta)["inputs"]
    assert [(i["channel"], i["name"]) for i in got] == [(0, "meta"), (0, "reads"), (1, "index")]
    assert all(set(i) == {"channel", "name", "type", "pattern", "optional"} for i in got)


def test_inputs_old_format_channels():
    # TC-008
    got = catalogue.flatten(*SAMTOOLS_SORT)["inputs"]
    assert [(i["channel"], i["name"]) for i in got] == [(0, "meta"), (1, "bam")]
    assert got[1]["pattern"] == "*.{bam,cram,sam}"


def test_outputs_new_format():
    # TC-009
    got = catalogue.flatten(*FASTQC)["outputs"]
    assert [(o["channel"], o["name"]) for o in got] == [("html", "meta"), ("html", "*.html"), ("zip", "meta"), ("zip", "*.zip")]
    assert got[1]["pattern"] == "*_{fastqc.html}"


def test_outputs_old_format():
    # TC-010
    got = catalogue.flatten(*SAMTOOLS_SORT)["outputs"]
    assert [o["channel"] for o in got] == ["meta", "bam"]


def test_versions_channels_are_skipped_in_both_formats():
    # TC-011, TC-012
    new = {"name": "a", "output": {"versions_x": [[{"v": {}}]], "versions": [[{"v": {}}]], "out": [[{"f": {"type": "file"}}]]}}
    assert [o["channel"] for o in catalogue.flatten("a", new)["outputs"]] == ["out"]
    old = {"name": "a", "output": [{"versions": {"type": "file"}}, {"versions_x": {"type": "file"}}, {"bam": {"type": "file"}}]}
    assert [o["channel"] for o in catalogue.flatten("a", old)["outputs"]] == ["bam"]


def test_topics_are_not_read():
    # TC-013
    assert "topics" not in json.dumps(catalogue.flatten(*FASTQC))


def test_missing_type_and_pattern_are_null():
    # TC-014
    meta = {"name": "a", "input": [{"x": {"description": "d"}}], "output": [{"y": {}}]}
    f = catalogue.flatten("a", meta)
    assert f["inputs"][0]["type"] is None and f["inputs"][0]["pattern"] is None
    assert f["outputs"][0]["type"] is None and f["outputs"][0]["pattern"] is None
    assert "null" in json.dumps(f)


def test_cluster_like_paths_are_masked():
    # TC-015
    f = catalogue.flatten("a", {"name": "a", "description": "see " + HOME + "alice/x"})
    assert "<path>/x" in f["description"]
    assert (HOME + "alice/") not in f["description"]


def test_cluster_like_paths_are_masked_in_every_string_field():
    # TC-016
    meta = {"name": "a", "keywords": [SCRATCH + "bob/y"],
            "tools": [{"t": {"homepage": LUSTRE + "carol/z"}}],
            "input": [{"i": {"pattern": HOME + "dave/q"}}]}
    f = catalogue.flatten("a", meta)
    assert f["keywords"] == ["<path>/y"]
    assert f["tools"][0]["homepage"] == "<path>/z"
    assert f["inputs"][0]["pattern"] == "<path>/q"


def test_odd_shapes_are_skipped_not_fatal():
    # TC-017
    s = catalogue.build_snapshot([("m", {"name": "m", "tools": None, "input": [None, 3, {"a": None}]})], "s")
    assert s["count"] == 1 and s["errors"] == []
    assert s["modules"][0]["inputs"] == [] and s["modules"][0]["tools"] == []


def test_missing_or_null_sections_are_empty_lists():
    # TC-018
    for meta in ({"name": "a"}, {"name": "a", "tools": None, "input": None, "output": None}):
        f = catalogue.flatten("a", meta)
        assert f["tools"] == [] and f["inputs"] == [] and f["outputs"] == []


def test_no_name_is_rejected():
    # TC-019
    for meta in ({"description": "x"}, {"name": ""}, {"name": 123}):
        with pytest.raises(ValueError, match="meta.yml has no name"):
            catalogue.flatten("p", meta)
    s = catalogue.build_snapshot([("p1", {}), ("p2", {"name": ""}), ("p3", {"name": 123})], "s")
    assert s["modules"] == []
    assert s["errors"] == [{"path": p, "reason": "meta.yml has no name"} for p in ("p1", "p2", "p3")]


def test_string_meta_becomes_the_error_reason():
    # TC-020
    s = catalogue.build_snapshot([("bad/yaml", "while parsing a block mapping"), ("ok", {"name": "ok"})], "s")
    assert s["errors"] == [{"path": "bad/yaml", "reason": "while parsing a block mapping"}]
    assert s["count"] == 1


def test_non_mapping_meta_is_an_error():
    # TC-021
    s = catalogue.build_snapshot([("a", None), ("b", 3), ("c", ["x"])], "s")
    assert s["errors"] == [{"path": p, "reason": "meta.yml is not a mapping"} for p in "abc"]


def test_any_exception_in_flatten_is_recorded(monkeypatch):
    # TC-022
    real = catalogue.flatten

    def boom(path, meta):
        if path == "bad":
            raise RuntimeError("boom")
        return real(path, meta)

    monkeypatch.setattr(catalogue, "flatten", boom)
    s = catalogue.build_snapshot([("a", {"name": "a"}), ("bad", {"name": "b"}), ("c", {"name": "c"})], "s")
    assert [m["name"] for m in s["modules"]] == ["a", "c"]
    assert s["errors"] == [{"path": "bad", "reason": "boom"}]


def test_dumps_is_stable_and_ends_with_one_newline():
    # TC-023
    a, b = catalogue.dumps(snap()), catalogue.dumps(snap())
    assert a == b
    assert a.endswith("}\n") and not a.endswith("\n\n")
    assert "generated_at" not in a


def test_dumps_keeps_unicode_indent_and_order():
    # TC-024
    s = catalogue.build_snapshot([("u", {"name": "u", "description": "中文 café"})], "s")
    text = catalogue.dumps(s)
    assert "中文 café" in text and "\\u" not in text
    assert text.split("\n")[1] == ' "source": "nf-core/modules",'
    assert text.index('"source"') < text.index('"sha"') < text.index('"count"') < text.index('"modules"')
    assert json.loads(text) == s


# ---- US2: load / search / describe ----------------------------------------------------

def test_load_with_path_is_not_cached(tmp_path):
    # TC-030
    p = tmp_path / "c.json"
    p.write_text(json.dumps(data_of(fake("one"))), encoding="utf-8")
    assert catalogue.load(p)["modules"][0]["name"] == "one"
    p.write_text(json.dumps(data_of(fake("two"))), encoding="utf-8")
    assert catalogue.load(p)["modules"][0]["name"] == "two"


def test_default_load_is_cached():
    # TC-031
    a = catalogue.load()
    assert isinstance(a, dict) and catalogue.load() is a


def test_missing_catalogue_file_does_not_raise(tmp_path):
    # TC-032, TC-033, TC-C08
    missing = tmp_path / "none.json"
    d = catalogue.load(missing)
    assert d["count"] == 0 and d["sha"] is None and d["modules"] == [] and d["source"] == "nf-core/modules"
    assert len(d["errors"]) == 1
    e = d["errors"][0]
    assert e["path"] == ""
    assert "模組目錄檔不存在：" in e["reason"] and str(missing) in e["reason"]
    assert "(the module catalogue file is missing)" in e["reason"]
    assert "Traceback" not in e["reason"]


def test_search_ranks_exact_name_first():
    # TC-034, TC-035
    assert catalogue.search("FastQC", GOLDEN)[0]["name"] == "fastqc"
    assert catalogue.search("bam", GOLDEN)[0]["name"] == "samtools_sort"


def test_search_score_order():
    # TC-036
    d = data_of(fake("zz", keywords=["abc"]), fake("d2", description="has abc here"), fake("xabcx"),
                fake("abcd"), fake("abc"), fake("aa", keywords=["abc"]), fake("d1", description="abc"))
    assert [m["name"] for m in catalogue.search("abc", d)] == ["abc", "abcd", "xabcx", "aa", "zz", "d1", "d2"]


def test_search_ignores_case_and_outer_space():
    # TC-037
    d = data_of(fake("m1", keywords=["Quality Control"]), fake("m2", description="Sort SAM files"))
    assert catalogue.search("  QUALITY  ", d)[0]["name"] == "m1"
    assert catalogue.search("sort sam", d)[0]["name"] == "m2"


def test_search_empty_query_is_empty_and_caps_at_50():
    # TC-038, TC-040
    assert catalogue.search("   ", GOLDEN) == [] and catalogue.search("", GOLDEN) == []
    d = data_of(*[fake("x%02d" % i) for i in range(60)])
    got = catalogue.search("x", d)
    assert [m["name"] for m in got] == ["x%02d" % i for i in range(50)]


def test_search_no_hit_is_empty():
    # TC-039
    assert catalogue.search("zzzznotamodule", GOLDEN) == []


def test_search_result_keys():
    # TC-041
    got = catalogue.search("fastqc", GOLDEN)
    assert all(set(g) == {"name", "path", "description"} for g in got)
    assert got[0] == {"name": "fastqc", "path": "fastqc", "description": "Run FastQC on sequenced reads"}


def test_describe_found_carries_sha_and_channels():
    # TC-042
    d = catalogue.describe("FASTQC", GOLDEN)
    assert d["found"] is True and d["sha"] == "abc123" and d["inputs"][1]["name"] == "reads"
    for k in ("name", "path", "description", "keywords", "tools", "inputs", "outputs"):
        assert k in d


def test_describe_unknown_is_a_clean_not_found():
    # TC-043, TC-044, TC-045, TC-C08
    d = catalogue.describe("nope", GOLDEN)
    assert set(d) == {"found", "name", "message"} and d["found"] is False and d["name"] == "nope"
    assert d["message"] == "找不到模組 nope；用 search 找相近的名字 (no module named nope; use search to find a similar name)"
    assert "Traceback" not in d["message"]
    e = catalogue.describe("", GOLDEN)
    assert set(e) == {"found", "name", "message"} and e["found"] is False


# ---- US3: committed snapshot, packaging, command, docs --------------------------------

SNAPSHOT_FILE = PKG / "data" / "nf-core-modules.json"
PINNED = "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"


def test_committed_snapshot_is_the_pinned_upstream():
    # TC-050, TC-051, TC-052, TC-053, TC-054, TC-056
    d = catalogue.load()
    assert d["sha"] == PINNED
    assert d["count"] >= 1000 and d["count"] == len(d["modules"])
    f = catalogue.describe("fastqc")
    assert f["found"] is True and any(i["name"] == "reads" for i in f["inputs"])
    assert f["outputs"]
    assert SNAPSHOT_FILE.stat().st_size <= 8 * 1024 * 1024


def test_committed_snapshot_has_no_versions_channels():
    # TC-055
    for m in catalogue.load()["modules"]:
        assert not any(str(o["channel"]).startswith("versions") for o in m["outputs"]), m["name"]


def test_committed_snapshot_is_what_dumps_writes():
    # TC-057
    text = SNAPSHOT_FILE.read_text(encoding="utf-8")
    assert text == catalogue.dumps(catalogue.load())
    assert text.endswith("}\n") and not text.endswith("\n\n") and "generated_at" not in text


def test_committed_snapshot_order():
    # TC-058
    d = catalogue.load()
    keys = [(m["name"], m["path"]) for m in d["modules"]]
    assert keys == sorted(keys)
    assert [e["path"] for e in d["errors"]] == sorted(e["path"] for e in d["errors"])
    for m in d["modules"]:
        assert list(m) == ["name", "path", "description", "keywords", "tools", "inputs", "outputs"]


def test_catalogue_runs_without_pyyaml():
    # TC-059
    code = ("import sys, importlib\n"
            "sys.path.insert(0, %r)\n"
            "m = importlib.import_module('abf_platform.catalogue')\n"
            "m.load(); m.search('fastqc'); m.describe('fastqc')\n"
            "assert 'yaml' not in sys.modules\n" % str(PLATFORM_DIR))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_package_data_ships_the_snapshot():
    # TC-060, TC-061
    text = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert '"data/*.json"' in text
    assert not (PKG / "data" / "__init__.py").exists()
    assert SNAPSHOT_FILE.is_file()


def test_snapshot_command_without_pyyaml_exits_2(tmp_path):
    # TC-063
    code = ("import sys, runpy\n"
            "sys.modules['yaml'] = None\n"
            "sys.path.insert(0, %r)\n"
            "sys.argv = ['catalogue', 'snapshot', '--modules', %r, '--sha', 'x', '--out', %r]\n"
            "runpy.run_module('abf_platform.catalogue', run_name='__main__')\n"
            % (str(PLATFORM_DIR), str(tmp_path), str(tmp_path / "o.json")))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 2
    assert "需要 PyYAML：python3 -m pip install pyyaml (PyYAML is needed to read meta.yml)" in r.stdout + r.stderr
    assert "Traceback" not in r.stdout + r.stderr


def test_platform_doc_has_the_catalogue_section():
    # TC-064, TC-065, TC-066, TC-067
    text = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    a, b = text.find("## nf-core module catalogue"), text.find("## What the platform stores")
    assert 0 <= a < b
    sec = text[a:b]
    assert PINNED in sec and "nf-core-modules.json" in sec
    assert "python -m abf_platform.catalogue snapshot" in sec
    assert "PR" in sec and re.search(r"tier A|A-tier|A 級|A級", sec)
    # TC-OP40
    assert "optional" in sec and "optional: true" in sec and "false" in sec


# ---- US4: out of scope ----------------------------------------------------------------

def _src(name):
    return (PKG / name).read_text(encoding="utf-8")


def test_no_tool_route_or_action_mentions_the_catalogue():
    # TC-070, TC-071
    for f in ["mcp_server.py", "web.py", "web_board.py"] + ["actions/" + p.name for p in (PKG / "actions").glob("*.py")]:
        assert "catalogue" not in _src(f).lower(), f


def test_catalogue_source_stays_in_scope():
    # TC-072, TC-073, TC-074
    text = _src("catalogue.py")
    assert "subworkflows" not in text and "subprocess" not in text and "os.system" not in text
    assert "sqlite3" not in text and "abf_platform.store" not in text
    import inspect
    assert list(inspect.signature(catalogue.load).parameters) == ["path"]
    assert list(inspect.signature(catalogue.search).parameters) == ["q", "data"]
    assert list(inspect.signature(catalogue.describe).parameters) == ["name", "data"]


def test_yaml_is_not_a_dependency():
    # TC-075
    for f in ("pyproject.toml", "constraints.txt"):
        assert "yaml" not in (PLATFORM_DIR / f).read_text(encoding="utf-8").lower(), f


# ---- catalogue-optional -----------------------------------------------------------------

def _opt(meta):
    return [i["optional"] for i in catalogue.flatten("a", meta)["inputs"]]


def test_flatten_keeps_optional_true():
    # TC-OP01
    meta = {"name": "a", "input": [[{"meta": {"type": "map"}}, {"x": {"type": "file", "optional": True}}]]}
    assert catalogue.flatten("a", meta)["inputs"][1]["optional"] is True


def test_flatten_defaults_optional_false():
    # TC-OP02, TC-OP05
    for item in (FASTQC, SAMTOOLS_SORT):
        got = catalogue.flatten(*item)["inputs"]
        assert got and all(i["optional"] is False for i in got)


def test_old_format_optional():
    # TC-OP03
    meta = {"name": "a", "input": [{"a": {"type": "file"}}, {"b": {"type": "file", "optional": True}}]}
    assert _opt(meta) == [False, True]


def test_optional_is_per_record():
    # TC-OP04
    meta = {"name": "a", "input": [{"a": {"type": "file"}}, {"b": {"optional": True}}, {"c": {"type": "file"}}]}
    assert _opt(meta) == [False, True, False]


def test_other_input_fields_unchanged():
    # TC-OP06
    got = catalogue.flatten(*FASTQC)["inputs"]
    assert (got[1]["channel"], got[1]["name"], got[1]["type"], got[1]["pattern"]) == (0, "reads", "file", None)


def test_outputs_never_get_optional():
    # TC-OP08
    new = {"name": "a", "output": {"o": [[{"x": {"type": "file", "optional": True}}]]}}
    old = {"name": "a", "output": [{"x": {"type": "file", "optional": True}}]}
    for meta in (new, old):
        outs = catalogue.flatten("a", meta)["outputs"]
        assert outs and all(set(o) == {"channel", "name", "type", "pattern"} for o in outs)


def test_empty_input_record_is_not_optional():
    # TC-OP12
    f = catalogue.flatten("a", {"name": "a", "input": [{"x": {}}]})
    assert f["inputs"][0]["type"] is None and f["inputs"][0]["optional"] is False


def test_snapshot_has_optional_on_every_input_record():
    # TC-OP20
    n = 0
    for m in catalogue.load()["modules"]:
        for i in m["inputs"]:
            n += 1
            assert isinstance(i.get("optional"), bool), (m["name"], i)
    assert n > 0


def test_snapshot_marks_known_optional_input():
    # TC-OP21: modules/nf-core/deeptools/bamcoverage/meta.yml at 5ed90b42 marks `blacklist` optional: true
    d = catalogue.describe("deeptools_bamcoverage")
    by = {i["name"]: i["optional"] for i in d["inputs"]}
    assert by["blacklist"] is True and by["input"] is False


def test_describe_inputs_carry_optional():
    # TC-OP22
    assert all(isinstance(i["optional"], bool) for i in catalogue.describe("fastqc")["inputs"])


def test_snapshot_count_and_outputs_unchanged():
    # TC-OP23, TC-OP29
    d = catalogue.load()
    assert d["count"] == 2116 and d["errors"] == []
    for m in d["modules"]:
        for o in m["outputs"]:
            assert set(o) == {"channel", "name", "type", "pattern"}
