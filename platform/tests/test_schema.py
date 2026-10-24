# Nothing existing: prepare_launch.sh prints a text summary from inline shell Python and schema_roles.py only judges column roles; nf-core's CLI needs a full install.
"""Tests for abf_platform.schema (feature schema-reader). TC ids in comments."""
import hashlib
import json
import re
import sys

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, FIXTURES

sys.path.insert(0, str(PLATFORM_DIR))
from abf_platform import schema as S  # noqa: E402

REAL = FIXTURES / "schema" / "ampliseq-2.18.0.nextflow_schema.json"
OLD = FIXTURES / "schema" / "old-definitions.json"
SI = REPO_ROOT / "tests" / "fixtures" / "schema_input"
SRC = PLATFORM_DIR / "abf_platform" / "schema.py"
PARAM_KEYS = {"name", "types", "description", "help_text", "has_default", "default", "required", "hidden", "enum", "format", "pattern"}
GROUP_KEYS = {"id", "title", "description", "hidden_count", "params"}
COL_KEYS = {"name", "types", "required", "format", "pattern", "exists", "meta", "description"}
ROLE_KEYS = {"role", "read1", "read2", "sample_column"}


@pytest.fixture(scope="module")
def real():
    return json.loads(REAL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def groups(real):
    return S.parameter_groups(real)


def P(groups, gid, name):
    g = [g for g in groups if g["id"] == gid][0]
    return [p for p in g["params"] if p["name"] == name][0]


def grp(props=None, required=None, **kw):
    d = {"title": "T", "type": "object", "properties": props or {}}
    if required is not None:
        d["required"] = required
    d.update(kw)
    return d


def sch(defs, order=None, key="$defs", **top):
    s = {key: defs}
    s["allOf"] = [{"$ref": "#/%s/%s" % (key, i)} for i in (order if order is not None else defs)]
    s.update(top)
    return s


def ids(gs):
    return [g["id"] for g in gs]


def one(prop, **kw):
    return S.parameter_groups(sch({"g": grp({"p": prop}, **kw)}))[0]["params"][0]


# ---- US1 ----
def test_tc001_002_003_004(real, groups):
    assert len(groups) == 16  # TC-001
    assert groups[0]["id"] == "input_output_options"  # TC-002
    assert ids(groups).index("asv_post_processing") == 5  # TC-003
    order = [r["$ref"].split("/")[-1] for r in real["allOf"]]
    assert ids(groups) == order  # TC-004


def test_tc005_006_007_045(groups):
    assert sum(len(g["params"]) for g in groups) == 170  # TC-005
    assert sum(1 for g in groups for p in g["params"] if p["hidden"] is True) == 19  # TC-006
    json.dumps(groups)  # TC-007
    for g in groups:  # TC-045
        assert set(g) == GROUP_KEYS
        for p in g["params"]:
            assert set(p) == PARAM_KEYS


def test_tc008(groups):
    assert S.required_without_default(groups) == ["outdir"]  # TC-008


def test_tc009_to_015(groups):
    assert P(groups, "generic_options", "help")["types"] == ["boolean", "string"]  # TC-009
    o = P(groups, "input_output_options", "outdir")
    assert o["format"] == "directory-path" and o["required"] is True  # TC-010/011
    assert o["has_default"] is False and o["default"] is None  # TC-012
    d = P(groups, "asv_post_processing", "decontam_decontaminate_method")
    assert d["default"] == "auto" and d["enum"][0] == "auto" and d["has_default"] is True  # TC-013/14/15


def test_tc016_017():
    gs = S.parameter_groups(json.loads(OLD.read_text(encoding="utf-8")))
    assert len(gs) == 1 and len(gs[0]["params"]) == 3  # TC-016
    by = {p["name"]: p for p in gs[0]["params"]}  # TC-017
    assert by["outdir"]["required"] and not by["outdir"]["has_default"]
    assert by["mode"]["required"] and by["mode"]["default"] == "fast" and by["mode"]["has_default"]
    assert not by["verbose"]["required"] and by["verbose"]["default"] is False and by["verbose"]["has_default"]


def test_tc018():
    s = {"$defs": {"a": grp({"x": {"type": "string"}}, title="FROM DEFS")},
         "definitions": {"a": grp({"y": {"type": "string"}}, title="FROM DEFINITIONS")},
         "allOf": [{"$ref": "#/$defs/a"}]}
    gs = S.parameter_groups(s)
    assert ids(gs) == ["a"] and gs[0]["title"] == "FROM DEFS" and gs[0]["params"][0]["name"] == "x"


def test_tc019_020_021():
    defs = {"a": grp({"x": {}}), "b": grp({"y": {}})}
    s = sch(defs)
    s["allOf"].insert(0, {"$ref": "#/$defs/nope"})  # TC-019
    assert ids(S.parameter_groups(s)) == ["a", "b"]
    s = sch(defs)
    s["allOf"].insert(1, {"$ref": "https://example.org/x.json#/$defs/a"})  # TC-020
    assert ids(S.parameter_groups(s)) == ["a", "b"]
    s = sch(defs)
    s["allOf"] += ["x", 5, None]  # TC-021
    assert ids(S.parameter_groups(s)) == ["a", "b"]


def test_tc022_023():
    s = sch({"bad": "oops", "ok": grp({"x": {}})}, order=["ok"])  # TC-022
    assert ids(S.parameter_groups(s)) == ["ok"]
    s = {"$defs": {"bad": "oops", "ok": grp({"x": {}})}}
    assert ids(S.parameter_groups(s)) == ["ok"]
    s = sch({"g": grp({"x": "nope", "y": {}})})  # TC-023
    assert [p["name"] for p in S.parameter_groups(s)[0]["params"]] == ["y"]


def test_tc024_025_026_027():
    s = sch({"a": grp({"x": {}})}, properties={"top": {"type": "string"}})  # TC-024
    gs = S.parameter_groups(s)
    assert ids(gs) == ["a", ""] and gs[-1]["title"] == "Parameters" and gs[-1]["params"][0]["name"] == "top"
    gs = S.parameter_groups({"properties": {"top": {}}})  # TC-025
    assert len(gs) == 1 and gs[0]["id"] == "" and gs[0]["title"] == "Parameters"
    assert ids(S.parameter_groups(sch({"a": grp({"x": {}})}, properties={}))) == ["a"]  # TC-026
    assert S.parameter_groups({}) == []  # TC-027


def test_tc028_to_031():
    g = grp({"f": {"type": "boolean", "default": False}, "z": {"type": "integer", "default": 0},
             "e": {"type": "string", "default": ""}}, required=["f", "z", "e"])
    gs = S.parameter_groups(sch({"g": g}))
    f, z, e = gs[0]["params"]
    assert f["has_default"] is True and f["default"] is False  # TC-028
    assert z["has_default"] is True and z["default"] == 0 and z["default"] is not False  # TC-029
    assert e["has_default"] is True and e["default"] == ""  # TC-030
    assert S.required_without_default(gs) == []  # TC-031


def test_tc032():
    gs = S.parameter_groups(sch({"g": grp({"x": {}}, required=["ghost", "x"])}))
    assert [p["name"] for p in gs[0]["params"]] == ["x"]
    assert S.required_without_default(gs) == ["x"]


def test_tc033_034():
    defs = {"a": grp(), "b": grp(), "c": grp()}
    s = {"$defs": defs, "allOf": [{"$ref": "#/$defs/c"}]}
    assert ids(S.parameter_groups(s)) == ["c", "a", "b"]  # TC-033
    s = sch({"a": grp(), "b": grp()}, order=["b", "a"], key="definitions")  # TC-034
    assert ids(S.parameter_groups(s)) == ["b", "a"]


def test_tc035_to_039():
    assert one({"type": "string"})["types"] == ["string"]  # TC-035
    assert one({})["types"] == []  # TC-036
    assert one({"type": ["string", 5, None]})["types"] == ["string"]  # TC-037
    g = S.parameter_groups({"$defs": {"zz": {"properties": {}}}})[0]  # TC-038
    assert g["title"] == "zz"
    assert one({})["description"] == ""  # TC-039


def test_tc040_041():
    props = {"a": {"hidden": True}, "b": {"hidden": "true"}, "c": {"hidden": 1}, "d": {}}  # TC-040
    g = S.parameter_groups(sch({"g": grp(props)}))[0]
    assert [p["hidden"] for p in g["params"]] == [True, False, False, False]
    g = S.parameter_groups(sch({"g": grp({"a": {"hidden": True}, "b": {"hidden": True}, "c": {}})}))[0]
    assert g["hidden_count"] == 2  # TC-041


def test_tc042_043_044():
    ps = S.parameter_groups(sch({"g": grp({"a": {"enum": ["x", "y"]}, "b": {"enum": "xy"}, "c": {}})}))[0]["params"]
    assert ps[0]["enum"] == ["x", "y"] and ps[1]["enum"] is None and ps[2]["enum"] is None  # TC-042
    p = one({"format": 1, "pattern": 2, "help_text": 3})  # TC-043
    assert p["format"] is None and p["pattern"] is None and p["help_text"] is None
    p = one({"format": "f", "pattern": "^a$", "help_text": "line1\n**bold**"})
    assert p["format"] == "f" and p["pattern"] == "^a$" and p["help_text"] == "line1\n**bold**"
    p = one({})
    assert p["format"] is None and p["pattern"] is None and p["help_text"] is None
    s = sch({"A": grp({"x": {}}, required=["x"]), "B": grp({"x": {}})})  # TC-044
    gs = S.parameter_groups(s)
    assert gs[0]["params"][0]["required"] is True and gs[1]["params"][0]["required"] is False


def test_tc046():
    s = sch({"A": grp({"a1": {}, "a2": {}, "a3": {"default": 1}}, required=["a1", "a2", "a3"]),
             "B": grp({"b1": {}, "b2": {"default": "x"}}, required=["b1", "b2"])})
    assert S.required_without_default(S.parameter_groups(s)) == ["a1", "a2", "b1"]


def test_tc047_048():
    p = one({"anyOf": [{"type": "string"}, {"type": "integer"}]})  # TC-047
    assert p["types"] == []
    p = one({"type": "integer", "default": "abc"})  # TC-048
    assert p["default"] == "abc"
    p = one({"enum": ["a", "b"], "default": "zzz"})
    assert p["default"] == "zzz"


# ---- US2 ----
def si(name):
    return json.loads((SI / name).read_text(encoding="utf-8"))


def cols_by(name):
    return {c["name"]: c for c in S.samplesheet_columns(si(name))}


def test_tc049_050():
    files = sorted(SI.glob("*.json"))
    assert len(files) == 5
    for f in files:  # TC-049
        d = json.loads(f.read_text(encoding="utf-8"))
        want = list((d.get("items", {}).get("properties") or d.get("properties")).keys())
        assert [c["name"] for c in S.samplesheet_columns(d)] == want, f.name
    # TC-050 (contract): first three columns are fastq_1, control, fastq_2.
    assert [c["name"] for c in S.samplesheet_columns(si("ampliseq-2.18.0.json"))][:3] == ["fastq_1", "control", "fastq_2"]


def test_tc051_052_053():
    c = cols_by("rnaseq-3.27.0.json")
    req = {"sample", "fastq_1", "strandedness"}
    assert all(c[n]["required"] is True for n in req)  # 051
    assert all(v["required"] is False for n, v in c.items() if n not in req)  # 052
    b = cols_by("bacass-2.6.1.json")  # 053
    assert b["ID"]["required"] is True
    assert all(v["required"] is False for n, v in b.items() if n != "ID")


def test_tc054_to_058():
    c = cols_by("ampliseq-2.18.0.json")
    assert all(v["required"] is False for v in c.values())  # 054
    assert c["sampleID"]["meta"] == ["sample"]  # 055
    assert c["fastq_1"]["exists"] is True  # 056
    assert c["fastq_1"]["format"] == "file-path"  # 057
    assert c["run"]["types"] == ["string", "integer"]  # 058


def test_tc059_066_067():
    for f in sorted(SI.glob("*.json")):
        cs = S.samplesheet_columns(json.loads(f.read_text(encoding="utf-8")))
        json.dumps(cs)  # 066
        for c in cs:
            assert set(c) == COL_KEYS  # 059
            assert not (ROLE_KEYS & set(c))  # 067


def test_tc067_params(groups):
    for g in groups:
        assert not (ROLE_KEYS & set(g))
        for p in g["params"]:
            assert not (ROLE_KEYS & set(p))


def test_tc060_to_065():
    def col(extra):
        return S.samplesheet_columns({"items": {"properties": {"c": extra}}})[0]
    cs = S.samplesheet_columns({"items": {"properties": {"a": {"exists": True}, "b": {"exists": "true"},
                                                         "c": {"exists": 1}, "d": {}}}})
    assert [c["exists"] for c in cs] == [True, False, False, False]  # 060
    assert col({"meta": "id"})["meta"] == ["id"]  # 061
    assert col({"meta": ["id", 5]})["meta"] == ["id"]  # 062
    assert col({})["meta"] == []  # 063
    cs = S.samplesheet_columns({"properties": {"x": {}, "y": {}}})  # 064
    assert [c["name"] for c in cs] == ["x", "y"]
    cs = S.samplesheet_columns({"items": {"properties": {"i": {}}}, "properties": {"top": {}}})  # 065
    assert [c["name"] for c in cs] == ["i"]


def test_tc068():
    d = si("mag-5.5.0.json")
    c = cols_by("mag-5.5.0.json")
    req = set(d["items"]["required"])
    assert req == {"sample", "group"}
    assert {n for n, v in c.items() if v["required"]} == req
    assert c["short_reads_1"]["required"] is False


# ---- US3 ----
def test_tc069_075():
    text = REAL.read_text(encoding="utf-8")
    assert S.load(text) == json.loads(text)  # 069
    pad = '{"a": 1}'
    t = pad + " " * (2000000 - len(pad))
    assert len(t) == 2000000 and S.load(t) == {"a": 1}  # 075


def test_tc070_to_074():
    bad = {"long": '{"a":1}' + " " * 2000000, "notjson": "not json", "list": "[]", "null": "null"}
    assert len(bad["long"]) > 2000000
    msgs = {}
    for k, t in bad.items():
        with pytest.raises(ValueError) as e:
            S.load(t)
        msgs[k] = str(e.value)
    for m in msgs.values():  # 074
        assert re.search(r"[一-鿿]", m) and re.search(r"[A-Za-z]", m)
        assert "Traceback" not in m and "/home/" not in m and ".py" not in m
    assert len(set(msgs.values())) == 3  # one message per problem kind


def test_tc076():
    s = sch({"g": grp({"x": {}})})
    assert len(S.parameter_groups(s)[0]["params"]) == 1
    s["$defs"]["g"]["properties"]["y"] = {}
    assert len(S.parameter_groups(s)[0]["params"]) == 2
    d = {"items": {"properties": {"a": {}}}}
    assert len(S.samplesheet_columns(d)) == 1
    d["items"]["properties"]["b"] = {}
    assert len(S.samplesheet_columns(d)) == 2


def test_tc077_078():
    src = SRC.read_text(encoding="utf-8")
    for w in ["lru_cache", "open(", "write_text", "urllib", "socket", "subprocess", "threading",
              "station", "ssh", "sbatch", "nextflow run", "while True"]:
        assert w not in src, w


def test_tc079_080():
    assert hashlib.sha256(REAL.read_bytes()).hexdigest() == "0e8f195c88c1a1a07f610ebd74bd88bf6ef00d8f105dfe16e39989d429da516f"
    assert REAL.stat().st_size == 95707
    assert OLD.stat().st_size < 5000
