# Nothing existing: no test covered the downstream method catalogue (spec downstream-method-catalog); these are its data, query and check-script tests.
"""downstream-method-catalog: the packaged JSON, effective grade, list_downstream and scripts/check_downstream_catalog.py.
Test cases TC-D*, TC-Q*, TC-S*, TC-N* are named in the comments (the task's test case file).
Counts that depend on today's date use an injected `today`; the packaged file is reviewed 2026-11-07."""
import ast
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "abf_platform"
REPO = HERE.parents[1]
DATA = PKG / "data" / "downstream-methods.json"
SCRIPT = REPO / "scripts" / "check_downstream_catalog.py"
TODAY = date(2026, 11, 17)
KEYS = ["id", "pipeline", "pipeline_version", "method", "link", "doi", "grade", "version_pin", "license", "inputs",
        "non_interactive_plot", "singularity", "reviewed", "notes"]


def dc():
    from abf_platform import downstream_catalog
    return downstream_catalog


def raw():
    return json.loads(DATA.read_text(encoding="utf-8"))


def entries():
    return raw()["entries"]


def by_id():
    return {e["id"]: e for e in entries()}


def mk(id, grade="A", reviewed="2026-01-01", method=None, pipeline="demo", **over):
    e = {"id": id, "pipeline": pipeline, "pipeline_version": "1.0", "method": method or id, "link": "https://example.org/" + id,
         "doi": "10.1/x", "grade": grade, "version_pin": "1.0", "license": "MIT", "inputs": [{"pipeline_output": "a.tsv", "role": "table"}],
         "non_interactive_plot": True, "singularity": "untested", "reviewed": reviewed, "notes": ""}
    e.update(over)
    return e


def write(tmp_path, es, name="cat.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"schema": 1, "entries": es}), encoding="utf-8")
    return p


def run_script(*args, cwd=None):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT)] + list(args), capture_output=True, text=True, cwd=str(cwd) if cwd else None)
    return r.returncode, r.stdout + r.stderr


# ---- US1 data ----
def test_dc01_schema_every_entry_has_all_keys_and_valid_values():
    # TC-D01
    d = raw()
    assert d["schema"] == 1
    ids = []
    for e in d["entries"]:
        assert sorted(e) == sorted(KEYS), e["id"]
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", e["id"])
        assert e["grade"] in ("A", "B", "C")
        date.fromisoformat(e["reviewed"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["reviewed"])
        assert e["singularity"] in ("ok", "untested", "unavailable")
        assert e["non_interactive_plot"] in (True, False, "needs_person", None)
        ids.append(e["id"])
    assert len(ids) == len(set(ids))
    dc().load()      # the loader accepts the packaged file


def test_dc02_nineteen_entries_exact_ids():
    # TC-D02 TC-N09 TC-N10
    want = {"ampliseq-summary-report", "ampliseq-ancombc", "ampliseq-phyloseq", "ampliseq-mia-miaviz-oma", "ampliseq-ancom-bc",
            "ampliseq-aldex2", "ampliseq-microeco", "ampliseq-maaslin2", "ampliseq-vegan",
            "rnaseq-differentialabundance", "rnaseq-deseq2", "rnaseq-edger", "rnaseq-limma", "rnaseq-clusterprofiler", "rnaseq-fgsea",
            "rnaseq-tximport", "rnaseq-pcaexplorer", "rnaseq-isee", "rnaseq-debrowser"}
    assert set(by_id()) == want and len(entries()) == 19
    assert {e["pipeline"] for e in entries()} == {"ampliseq", "rnaseq"}
    assert "tximeta" not in DATA.read_text(encoding="utf-8").lower()


def test_dc03_ampliseq_grades_follow_the_ruling():
    # TC-D03
    amp = {e["id"]: e for e in entries() if e["pipeline"] == "ampliseq"}
    assert {i for i, e in amp.items() if e["grade"] == "A"} == {"ampliseq-summary-report", "ampliseq-ancombc", "ampliseq-phyloseq",
                                                                 "ampliseq-mia-miaviz-oma", "ampliseq-ancom-bc", "ampliseq-aldex2"}
    assert {i for i, e in amp.items() if e["grade"] == "B"} == {"ampliseq-microeco", "ampliseq-maaslin2", "ampliseq-vegan"}
    assert all(e["pipeline_version"] == "3.1.0" for e in amp.values())


def test_dc04_rnaseq_grades():
    # TC-D04
    rna = {e["id"]: e for e in entries() if e["pipeline"] == "rnaseq"}
    assert {i for i, e in rna.items() if e["grade"] == "B"} == {"rnaseq-debrowser"}
    assert {i for i, e in rna.items() if e["grade"] == "A"} == set(rna) - {"rnaseq-debrowser"} and len(rna) == 10


def test_dc05_needs_person_exactly_three():
    # TC-D05 TC-D13
    es = by_id()
    assert {i for i, e in es.items() if e["non_interactive_plot"] == "needs_person"} == {"rnaseq-pcaexplorer", "rnaseq-isee", "rnaseq-debrowser"}
    for i in ("ampliseq-summary-report", "rnaseq-differentialabundance", "rnaseq-deseq2", "rnaseq-edger", "rnaseq-limma",
              "rnaseq-clusterprofiler", "rnaseq-fgsea", "rnaseq-tximport"):
        assert es[i]["non_interactive_plot"] is True, i
    assert es["ampliseq-ancombc"]["non_interactive_plot"] is False


def test_dc06_differentialabundance_untested_on_nano4():
    # TC-D06 TC-D07 TC-N08
    e = by_id()["rnaseq-differentialabundance"]
    assert e["singularity"] == "untested" and "待實測" in e["notes"] and "nano4" in e["notes"] and "docker" in e["notes"]
    assert all(x["singularity"] == "untested" for x in entries())


def test_dc08_null_fields_carry_a_cha_bu_dao_note():
    # TC-D08 TC-D10 TC-D11
    for e in entries():
        if any(e[k] is None for k in ("doi", "license", "version_pin", "pipeline_version")):
            assert "查不到" in e["notes"], e["id"]
    for e in entries():
        if e["pipeline"] == "rnaseq":
            assert e["pipeline_version"] is None and "pipeline_version" in e["notes"] and "查不到" in e["notes"], e["id"]
    d = by_id()["rnaseq-debrowser"]
    assert d["grade"] == "B" and d["version_pin"] is None and "查不到" in d["notes"]


def test_dc09_null_without_note_is_rejected(tmp_path):
    # TC-D09
    p = write(tmp_path, [mk("lic-null", license=None)])
    with pytest.raises(ValueError) as ex:
        dc().load(p)
    assert "lic-null" in str(ex.value) and "license" in str(ex.value)
    dc().load(write(tmp_path, [mk("lic-null", license=None, notes="license 查不到")], "ok.json"))


def test_dc12_null_plot_flag_needs_pending_note():
    # TC-D12
    es = by_id()
    for i in ("phyloseq", "mia-miaviz-oma", "ancom-bc", "aldex2", "microeco", "maaslin2", "vegan"):
        e = es["ampliseq-" + i]
        assert e["non_interactive_plot"] is None and "待驗證" in e["notes"], i


def test_dc14_clusterprofiler_fgsea_inputs_empty_with_original_text():
    # TC-D14 TC-D15
    es = by_id()
    for i in ("rnaseq-clusterprofiler", "rnaseq-fgsea"):
        assert es[i]["inputs"] == [] and "待驗證" in es[i]["notes"] and "differential results table from a prior DESeq2/edgeR/limma step" in es[i]["notes"]
    for e in entries():
        if e["inputs"] == []:
            assert "待驗證" in e["notes"], e["id"]
        for x in e["inputs"]:
            assert isinstance(x["pipeline_output"], str) and x["pipeline_output"] and isinstance(x["role"], str) and x["role"]


def test_dc16_input_contracts():
    # TC-D16
    es = by_id()
    out = lambda i: [x["pipeline_output"] for x in es[i]["inputs"]]
    assert "summary_report/summary_report.html" in out("ampliseq-summary-report")
    assert "star_salmon/salmon.merged.gene_counts_length_scaled.tsv" in out("rnaseq-differentialabundance")
    assert "star_salmon/<SAMPLE>/quant.sf" in out("rnaseq-tximport")


def test_dc18_grade_a_without_link_is_rejected(tmp_path):
    # TC-D18
    with pytest.raises(ValueError) as ex:
        dc().load(write(tmp_path, [mk("no-link", link="")]))
    assert "no-link" in str(ex.value)


def test_dc10_packaged_data_file_is_covered_by_package_data():
    # TC-D19
    text = (REPO / "platform" / "pyproject.toml").read_text(encoding="utf-8")
    globs = re.search(r'package-data\s*=\s*\{[^}]*\[([^\]]*)\]', text).group(1)
    pats = re.findall(r'"([^"]+)"', globs)
    assert any(fnmatch.fnmatch("data/downstream-methods.json", p) for p in pats)


@pytest.mark.parametrize("path", [PKG / "downstream_catalog.py", PKG / "actions" / "downstream.py", SCRIPT])
def test_dc20_only_stdlib_imports(path):
    # TC-D20 TC-S13
    std = set(sys.stdlib_module_names)
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [] if node.level else [(node.module or "").split(".")[0]]
        else:
            continue
        for m in mods:
            assert m in std, "%s imports %s" % (path.name, m)
            assert m not in ("socket", "urllib", "http", "requests", "yaml")


def test_dc20_default_path_is_the_packaged_file():
    # TC-D20
    assert dc().DEFAULT_PATH == DATA


# ---- US2 query ----
def test_q01_ampliseq_default_listing():
    # TC-Q01 TC-Q03
    r = dc().list_downstream("ampliseq", today=TODAY)
    assert set(r) == {"pipeline", "methods", "count", "note"} and r["count"] == 9 == len(r["methods"])
    assert [m["grade"] for m in r["methods"]] == ["A"] * 6 + ["B"] * 3
    for m in r["methods"]:
        assert sorted(m) == sorted(["id", "method", "link", "grade", "declared_grade", "downgraded", "version_pin", "license", "doi", "inputs",
                                    "non_interactive_plot", "singularity", "reviewed", "notes"])


def test_q02_rnaseq_default_listing():
    # TC-Q02 TC-Q14
    r = dc().list_downstream("rnaseq", today=TODAY)
    assert r["count"] == 10 and [m["grade"] for m in r["methods"]] == ["A"] * 9 + ["B"]
    assert r["methods"][-1]["method"] == "DEBrowser"
    got = {m["id"]: m["non_interactive_plot"] for m in r["methods"]}
    assert [got[i] for i in ("rnaseq-pcaexplorer", "rnaseq-isee", "rnaseq-debrowser")] == ["needs_person"] * 3


def test_q04_boundary_365_days_stays():
    # TC-Q04
    e = mk("x", "A", "2026-01-01")
    assert dc().effective_grade(e, date(2026, 12, 31)) == "A"
    assert dc().effective_grade(e, date(2027, 1, 1)) == "A"
    assert dc().effective_grade(e, date(2027, 1, 2)) == "B"


def test_q05_downgrade_one_level():
    # TC-Q05
    t = date(2027, 1, 2)
    assert [dc().effective_grade(mk("x", g, "2026-01-01"), t) for g in "ABC"] == ["B", "C", "C"]


def test_q05_listing_keeps_declared_grade_and_flags(tmp_path):
    # TC-Q05 TC-Q06 TC-Q07 TC-Q09
    p = write(tmp_path, [mk("a", "A"), mk("b", "B", "2026-12-01"), mk("c", "C", "2026-12-01"), mk("old-b", "B", "2026-01-01"), mk("old-a", "A", "2026-01-01")])
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    r = dc().list_downstream("demo", today=date(2027, 1, 2), path=p)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before
    ids = [m["id"] for m in r["methods"]]
    assert sorted(ids) == ["b", "old-a"]
    old_a = next(m for m in r["methods"] if m["id"] == "old-a")
    assert (old_a["grade"], old_a["declared_grade"], old_a["downgraded"]) == ("B", "A", True)


def test_q08_order_a_before_b_alphabetical_and_stable(tmp_path):
    # TC-Q08
    p = write(tmp_path, [mk("g", "B", "2026-12-01", method="gamma"), mk("b", "A", "2026-12-01", method="beta"),
                         mk("a", "B", "2026-12-01", method="alpha"), mk("d", "A", "2026-12-01", method="delta")])
    r1 = dc().list_downstream("demo", today=TODAY, path=p)
    assert [m["method"] for m in r1["methods"]] == ["beta", "delta", "alpha", "gamma"]
    assert r1 == dc().list_downstream("demo", today=TODAY, path=p)


def test_q10_today_defaults_to_date_today(tmp_path):
    # TC-Q10
    p = write(tmp_path, [mk("a", "A", "2026-12-01")])
    assert dc().list_downstream("demo", path=p) == dc().list_downstream("demo", today=date.today(), path=p)


def test_q11_unknown_pipeline_is_empty_not_error():
    # TC-Q11 TC-Q12 TC-N09
    want = {"pipeline": "scrnaseq", "methods": [], "count": 0, "note": "no certified downstream methods for this pipeline"}
    assert dc().list_downstream("scrnaseq", today=TODAY) == want
    assert dc().list_downstream("ampliseqq", today=TODAY)["methods"] == []
    assert dc().list_downstream("atacseq", today=TODAY)["count"] == 0


def test_q13_empty_pipeline_raises():
    # TC-Q13
    for bad in ("", "  "):
        with pytest.raises(ValueError):
            dc().list_downstream(bad)


def test_q15_after_twelve_months_the_real_file_downgrades():
    # TC-Q15
    r = dc().list_downstream("ampliseq", today=date(2027, 11, 9))
    assert r["count"] == 6 and all(m["grade"] == "B" and m["declared_grade"] == "A" and m["downgraded"] for m in r["methods"])


def test_q16_query_is_read_only():
    # TC-Q16
    before = hashlib.sha256(DATA.read_bytes()).hexdigest()
    names = sorted(p.name for p in DATA.parent.iterdir())
    dc().list_downstream("ampliseq", today=TODAY)
    assert hashlib.sha256(DATA.read_bytes()).hexdigest() == before and sorted(p.name for p in DATA.parent.iterdir()) == names


def test_n04_signature_has_no_include_c():
    # TC-N04
    import inspect
    assert list(inspect.signature(dc().list_downstream).parameters) == ["pipeline", "today", "path"]


# ---- US4 script ----
def test_s01_fresh_catalogue_exits_zero(tmp_path):
    # TC-S01 TC-S03
    assert run_script("--today", "2026-11-17", cwd=tmp_path)[0] == 0
    assert run_script("--today", "2027-11-07", cwd=tmp_path)[0] == 0


def test_s02_expired_entry_exits_one(tmp_path):
    # TC-S02 TC-S14
    p = write(tmp_path, [mk("old-one", "A", "2026-01-01"), mk("fresh-one", "A", "2027-01-01")])
    code, out = run_script("--path", str(p), "--today", "2027-01-15")
    assert code == 1 and "old-one" in out and "2026-01-01" in out and "379" in out and "fresh-one" not in out


def test_s04_real_file_366_days(tmp_path):
    # TC-S04
    code, out = run_script("--today", "2027-11-08", cwd=tmp_path)
    assert code == 1 and "366" in out and "2026-11-07" in out
    for i in by_id():
        assert i in out


def _bad(tmp_path, mutate):
    e = mk("bad-one")
    mutate(e)
    return write(tmp_path, [e])


@pytest.mark.parametrize("mutate,word", [
    (lambda e: e.pop("license"), "license"),                                          # TC-S05
    (lambda e: e.update(grade="D"), "grade"),                                          # TC-S06
    (lambda e: e.update(reviewed="11/07/2026"), "reviewed"),                           # TC-S07
    (lambda e: e.update(doi=None), "doi"),                                             # TC-S08
    (lambda e: e.update(non_interactive_plot=None), "non_interactive_plot"),           # TC-S10
    (lambda e: e.update(link=""), "link"),                                             # TC-S11
])
def test_s05_schema_violations_exit_two(tmp_path, mutate, word):
    # TC-S05 TC-S06 TC-S07 TC-S08 TC-S10 TC-S11
    code, out = run_script("--path", str(_bad(tmp_path, mutate)), "--today", "2026-11-17")
    assert code == 2 and "bad-one" in out and word in out


def test_s09_duplicate_ids(tmp_path):
    # TC-S09
    code, out = run_script("--path", str(write(tmp_path, [mk("dup"), mk("dup")])), "--today", "2026-11-17")
    assert code == 2 and "dup" in out


def test_s12_all_violations_listed(tmp_path):
    # TC-S12
    e = mk("two-bad", grade="D")
    del e["license"]
    code, out = run_script("--path", str(write(tmp_path, [e])), "--today", "2026-11-17")
    assert code == 2 and "license" in out and "grade" in out


def test_s13_script_writes_nothing(tmp_path):
    # TC-S13
    p = write(tmp_path, [mk("a", "A", "2026-12-01")])
    before = (sorted(x.name for x in tmp_path.iterdir()), p.read_bytes())
    run_script("--path", str(p), "--today", "2026-12-02", cwd=tmp_path)
    assert (sorted(x.name for x in tmp_path.iterdir()), p.read_bytes()) == before
