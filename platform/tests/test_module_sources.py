# Nothing existing: tests of the committed file of nf-core module scripts (spec 017d); no tool keeps these files per commit for an offline platform.
"""017d: `abf_platform.module_sources` - the module files a composed pipeline's project carries. Test cases are named in the comments
(TC-066 ...), see specs/017d-launch-composed/test-case.md."""
import gzip
import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
REPO = PLATFORM.parent
SHA = "5ed90b42e78410e7411e9c6bdfeff33226d6c58e"


def ms():
    from abf_platform import module_sources
    return module_sources


def make_checkout(tmp_path, extra=None):
    """A small fake nf-core/modules checkout: modules/nf-core/<path>/..."""
    root = tmp_path / "co" / "modules" / "nf-core"
    files = {
        "fastqc/main.nf": "process FASTQC {\n    script:\n    'fastqc'\n}\n",
        "fastqc/meta.yml": "name: fastqc\n",
        "fastqc/environment.yml": "name: x\n",
        "fastqc/tests/main.nf.test": "nextflow_process {}\n",
        "multiqc/main.nf": "process MULTIQC {\n}\n",
        "multiqc/templates/report.txt": "a template\n",
        "multiqc/resources/extra.cfg": "a resource\n",
        "multiqc/meta.yml": "name: multiqc\n",
        "samtools/sort/main.nf": "process SAMTOOLS_SORT {\n}\n",
    }
    files.update(extra or {})
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            p.write_bytes(text)
        else:
            p.write_text(text, encoding="utf-8", newline="\n")
    return tmp_path / "co"


def snap(tmp_path, extra=None, sha=SHA):
    out = tmp_path / "out.json.gz"
    rc = ms()._snapshot_command(["--modules", str(make_checkout(tmp_path, extra)), "--sha", sha, "--out", str(out)])
    assert rc == 0
    return json.loads(gzip.decompress(out.read_bytes()).decode("utf-8")), out


def test_snapshot_is_byte_identical_for_the_same_sha(tmp_path):
    # TC-066
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _, fa = snap(a)
    _, fb = snap(b)
    assert fa.read_bytes() == fb.read_bytes()


def test_snapshot_shape_sorted_keys_and_zero_mtime(tmp_path):
    # TC-067
    data, out = snap(tmp_path)
    assert sorted(data) == ["modules", "sha", "source"] and data["source"] == "nf-core/modules" and data["sha"] == SHA
    assert list(data["modules"]) == sorted(data["modules"])
    for m in data["modules"].values():
        assert sorted(m) == ["files", "unsupported"]
    raw = out.read_bytes()
    assert raw[:2] == b"\x1f\x8b" and raw[4:8] == b"\x00\x00\x00\x00"      # gzip header: the mtime field is 0
    text = gzip.decompress(raw).decode("utf-8")
    assert text == json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def test_snapshot_keeps_only_main_templates_and_resources(tmp_path):
    # TC-068
    data, _ = snap(tmp_path)
    assert sorted(data["modules"]) == ["fastqc", "multiqc", "samtools/sort"]
    assert sorted(data["modules"]["fastqc"]["files"]) == ["main.nf"]
    assert sorted(data["modules"]["multiqc"]["files"]) == ["main.nf", "resources/extra.cfg", "templates/report.txt"]
    assert all(m["unsupported"] is None for m in data["modules"].values())
    assert data["modules"]["multiqc"]["files"]["templates/report.txt"] == "a template\n"


@pytest.mark.parametrize("tc,extra", [
    ("TC-069 bin", {"tool/main.nf": "x\n", "tool/bin/run.sh": "#!/bin/sh\n"}),
    ("TC-070 nul", {"tool/main.nf": "x\n", "tool/resources/blob.dat": b"ab\x00cd"}),
    ("TC-070 utf8", {"tool/main.nf": "x\n", "tool/resources/blob.dat": b"\xff\xfe\xfa"}),
    ("TC-071 name", {"tool/main.nf": "x\n", "tool/resources/with space.txt": "a\n"}),
    ("TC-071 nested", {"tool/main.nf": "x\n", "tool/resources/deep/inner.txt": "a\n"}),
    ("TC-072 path", {"tool/main.nf": "x\n", "tool/templates/run.sh": "cd /home/alice/data/ && ls\n"}),
    ("TC-073 big", {"tool/main.nf": "y" * 200001}),
])
def test_snapshot_marks_unsupported_modules_with_a_reason(tmp_path, tc, extra):
    data, out = snap(tmp_path, extra)
    m = data["modules"]["tool"]
    assert isinstance(m["unsupported"], str) and len(m["unsupported"]) > 5, tc
    assert m["files"] == {}, tc      # the file is not kept, so nothing of it was changed or half-carried
    assert data["modules"]["fastqc"]["unsupported"] is None
    if tc.startswith("TC-072"):
        assert "/home/alice/" not in gzip.decompress(out.read_bytes()).decode("utf-8")


def synthetic(tmp_path, sha, modules=None):
    p = tmp_path / "syn.json.gz"
    snap_ = {"source": "nf-core/modules", "sha": sha, "modules": modules or {"fastqc": {"files": {"main.nf": "x\n"}, "unsupported": None}}}
    p.write_bytes(ms().dumps(snap_))
    return p


def test_load_refuses_sources_of_another_sha(tmp_path):
    # TC-074
    with pytest.raises(ValueError):
        ms().load(synthetic(tmp_path, "0" * 40))
    assert ms().load(synthetic(tmp_path, SHA))["sha"] == SHA


def test_sources_sha_equals_the_catalogue_sha():
    # TC-075
    from abf_platform import catalogue
    assert ms().load()["sha"] == catalogue.load()["sha"] == SHA


def test_every_catalogue_module_has_files_or_a_named_reason():
    # TC-076
    from abf_platform import catalogue
    mods = ms().load()["modules"]
    missing = [m["path"] for m in catalogue.load()["modules"] if m["path"] not in mods]
    assert missing == []
    for path, m in mods.items():
        if m["unsupported"] is not None:
            assert isinstance(m["unsupported"], str) and m["unsupported"].strip(), path
        else:
            assert "main.nf" in m["files"], path


def test_fastqc_and_multiqc_are_present_and_supported():
    # TC-077
    mods = ms().load()["modules"]
    for name in ("fastqc", "multiqc"):
        assert mods[name]["unsupported"] is None and "main.nf" in mods[name]["files"]


def test_files_for_returns_project_paths():
    # TC-078
    src = {"modules": {"a": {"files": {"main.nf": "A\n", "templates/t.sh": "T\n"}, "unsupported": None},
                       "b/c": {"files": {"main.nf": "B\n"}, "unsupported": None}}}
    assert ms().files_for(["b/c", "a", "a"], src) == {"modules/nf-core/a/main.nf": "A\n", "modules/nf-core/a/templates/t.sh": "T\n",
                                                      "modules/nf-core/b/c/main.nf": "B\n"}


def test_files_for_names_the_missing_or_unsupported_module():
    # TC-079
    src = {"modules": {"bad": {"files": {}, "unsupported": "needs a bin folder"}, "ok": {"files": {"main.nf": "x"}, "unsupported": None}}}
    with pytest.raises(ValueError) as e:
        ms().files_for(["ok", "gone"], src)
    assert "gone" in str(e.value) and re.search(r"[一-鿿]", str(e.value)) and "(" in str(e.value)
    with pytest.raises(ValueError) as e:
        ms().files_for(["bad"], src)
    assert "bad" in str(e.value) and "needs a bin folder" in str(e.value)


def test_load_is_cached():
    # TC-080
    assert ms().load() is ms().load()


def test_the_data_file_is_small_and_the_ledger_records_it():
    # TC-081
    size = (PLATFORM / "abf_platform" / "data" / "nf-core-module-sources.json.gz").stat().st_size
    assert 0 < size <= 8 * 1024 * 1024
    ledger = (REPO / "specs" / "017d-launch-composed" / "ledger.md").read_text(encoding="utf-8")
    assert str(size) in ledger.replace(",", "") and "unsupported" in ledger


def test_module_sources_source_has_no_network_or_program_words():
    # TC-082
    text = (PLATFORM / "abf_platform" / "module_sources.py").read_text(encoding="utf-8")
    for word in ("urllib", "requests", "socket", "subprocess", "http.client", "nextflow run", "sbatch"):
        assert word not in text, word
    imports = set(re.findall(r"^(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
    assert imports <= {"functools", "gzip", "io", "json", "re", "sys", "pathlib", "argparse"}


def test_package_data_gets_exactly_one_more_glob():
    # TC-083
    text = (PLATFORM / "pyproject.toml").read_text(encoding="utf-8")
    assert 'package-data = {"abf_platform" = ["skills/*/SKILL.md", "data/*.json", "data/*.json.gz"]}' in text
