# Nothing existing: no library packs a composed pipeline into the platform's deterministic zip; this tests that action.
"""export_pipeline (017b action): one version of a pipeline plus its nf-core module files as a zip, in bytes. Test cases TC-001 ... in
specs/pipeline-export-zip/test-case.md."""
import copy
import io
import json
import logging
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from human_harness import World
from owner_harness import Duo, sql_rows

HERE = Path(__file__).resolve().parent
PLATFORM = HERE.parent
GRAPH = json.loads((HERE / "fixtures" / "compose" / "fastqc_multiqc" / "graph.json").read_text(encoding="utf-8"))
ONE = {"nodes": [{"id": "only", "module": "fastqc"}]}
BAD = {"nodes": [{"id": "qc", "module": "fastqc"}, {"id": "s", "module": "samtools_sort"}],
       "edges": [{"from": {"node": "qc", "output": "html"}, "to": {"node": "s", "input": 2}}]}   # a wrong-channel edge: META_MISMATCH, an error


@pytest.fixture
def d(tmp_path, monkeypatch):
    return Duo(World(tmp_path, monkeypatch))


def pl():
    from abf_platform.actions import pipelines
    return pipelines


def make(d, name="qc-demo", graph=None):
    out = pl().create_pipeline(d.state, name=name, graph=graph or GRAPH, caller=d.a)
    assert out["ok"], out
    return out["pipeline"]["id"]


def export(d, pid, version=None, caller=None, **kw):
    return pl().export_pipeline(d.state, pid, version, caller=caller or d.a, **kw)


def opened(out):
    return zipfile.ZipFile(io.BytesIO(out["zip"]))


def sources_for():
    from abf_platform import module_sources
    return copy.deepcopy(module_sources.load())


def tables(d):
    return {r["name"]: sql_rows(d.state, "SELECT COUNT(*) AS n FROM %s" % r["name"])[0]["n"]
            for r in sql_rows(d.state, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}


def contents(d):
    """Every row of every table, in a fixed order (TC-022: not only the counts)."""
    out = {}
    for r in sql_rows(d.state, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
        rows = sql_rows(d.state, "SELECT * FROM %s" % r["name"])
        out[r["name"]] = sorted(json.dumps(dict(x), sort_keys=True, default=str) for x in rows)
    return out


def schema(d):
    return [tuple(r) for r in sql_rows(d.state, "SELECT name, sql FROM sqlite_master ORDER BY name")]


def broken(src, path, how):
    src["modules"] = dict(src["modules"])
    if how == "missing":
        del src["modules"][path]
    else:
        src["modules"][path] = dict(src["modules"][path], unsupported="uses a feature the platform cannot carry")
    return src


def big(src, extra_files=0, extra_bytes=0):
    src["modules"] = dict(src["modules"])
    m = dict(src["modules"]["fastqc"])
    files = dict(m["files"])
    for i in range(extra_files):
        files["f%d.txt" % i] = "x"
    if extra_bytes:
        files["big.txt"] = "x" * extra_bytes
    src["modules"]["fastqc"] = dict(m, files=files)
    return src


def test_export_has_the_project_and_both_modules(d):
    # TC-001, TC-002, TC-003, TC-004, TC-006, TC-007, TC-009
    pid = make(d)
    out = export(d, pid)
    assert out["ok"] is True and out["filename"] == "qc-demo-v1.zip" and isinstance(out["zip"], bytes)
    z = opened(out)
    names = z.namelist()
    for need in ("main.nf", "nextflow.config", "modules.json"):
        assert need in names
    assert any(n.startswith("modules/nf-core/fastqc/") and n.endswith("main.nf") for n in names)
    assert any(n.startswith("modules/nf-core/multiqc/") and n.endswith("main.nf") for n in names)
    rendered = pl().render_pipeline(d.state, pid, caller=d.a)
    for k, text in rendered["files"].items():
        assert z.read(k).decode("utf-8") == text
    assert out["files"] == sorted(names) == names
    assert out["open_inputs"] == rendered["open_inputs"]
    extra = [n for n in names if n not in rendered["files"] and not n.startswith("modules/")]
    assert len(extra) == 1
    note = z.read(extra[0]).decode("utf-8")
    assert len(note.splitlines()) <= 10
    for item in rendered["open_inputs"]:
        for n in item["names"]:
            assert n in note


def test_every_module_file_of_files_for_is_in_the_zip(d):
    # TC-005
    from abf_platform import module_sources
    pid = make(d)
    src = sources_for()
    z = opened(export(d, pid, sources=src))
    for k, text in module_sources.files_for(["fastqc", "multiqc"], src).items():
        assert z.read(k).decode("utf-8") == text


def test_stub_run_of_the_unpacked_zip(d, tmp_path, e2e_cfg):
    # TC-008
    dest = tmp_path / "unpacked"
    opened(export(d, make(d))).extractall(dest)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("NXF_", "TOWER_", "ABF_"))}
    env.update({"NXF_HOME": e2e_cfg["home"], "NXF_VER": e2e_cfg["ver"], "NXF_OFFLINE": "true",
                "NXF_ANSI_LOG": "false", "NXF_DISABLE_CHECK_LATEST": "true"})
    r = subprocess.run([e2e_cfg["launcher"], "run", ".", "-stub-run"], cwd=str(dest), env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]


def test_versions(d):
    # TC-010, TC-011
    pid = make(d)
    assert pl().update_pipeline(d.state, pid, graph=ONE, caller=d.a)["ok"]
    new, old = export(d, pid), export(d, pid, 1)
    assert new["filename"] == "qc-demo-v2.zip" and old["filename"] == "qc-demo-v1.zip"
    main = lambda v: pl().render_pipeline(d.state, pid, v, caller=d.a)["files"]["main.nf"]
    assert opened(new).read("main.nf").decode() == main(2)
    assert opened(old).read("main.nf").decode() == main(1)
    assert main(1) != main(2)


def test_deterministic_sorted_fixed_time(d, monkeypatch):
    # TC-012, TC-013
    import time
    pid = make(d)
    a = export(d, pid)
    t = time.time()
    monkeypatch.setattr(time, "time", lambda: t + 86400 * 400)
    b = export(d, pid)
    assert a["zip"] == b["zip"]
    infos = opened(a).infolist()
    assert [i.filename for i in infos] == sorted(i.filename for i in infos)
    assert {i.date_time for i in infos} == {(1980, 1, 1, 0, 0, 0)}
    assert len({i.compress_type for i in infos}) == 1
    assert opened(a).testzip() is None


def test_validation_rides_along_and_never_blocks(d):
    # TC-014, TC-015, TC-016
    pid = make(d)
    assert export(d, pid)["ok"] is True
    pl().validate_pipeline(d.state, pid, caller=d.a)
    assert export(d, pid)["validation"] == pl().get_validation(d.state, pid, caller=d.a)["validation"]
    bad = make(d, name="bad-one", graph=BAD)
    pl().validate_pipeline(d.state, bad, caller=d.a)
    kept = pl().get_validation(d.state, bad, caller=d.a)["validation"]
    assert kept is not None and kept["ok"] is False                                      # TC-016: the kept check really has errors
    assert [f for f in kept["findings"] if f["severity"] == "error"]
    got = export(d, bad)
    assert got["ok"] is True and isinstance(got["zip"], bytes) and got["validation"] == kept
    assert got["validation"]["ok"] is False and [f for f in got["validation"]["findings"] if f["severity"] == "error"]


def test_nothing_written_no_schema_change_no_rows(d, tmp_path, monkeypatch):
    # TC-017, TC-018, TC-052, TC-061
    pid = make(d)
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    listing = lambda: sorted(str(p) for p in Path(d.state).parent.rglob("*") if "-wal" not in p.name and "-shm" not in p.name)
    before, sch, rows = listing(), schema(d), tables(d)
    out = export(d, pid)
    bad = export(d, pid, 9)
    assert out["ok"] and not bad["ok"]
    assert listing() == before and list(work.iterdir()) == [] and schema(d) == sch and tables(d) == rows
    assert not [k for k in out if "token" in k or "share" in k or "url" in k]


def test_no_external_program_is_started(d, monkeypatch):
    # TC-053
    pid = make(d)

    def boom(*a, **k):
        raise AssertionError("an external program was started")
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(os, "system", boom)
    assert export(d, pid)["ok"] is True


def test_other_user_gets_not_found_and_changes_nothing(d):
    # TC-020, TC-021, TC-022, TC-060
    pid = make(d)
    pl().update_pipeline(d.state, pid, graph=ONE, caller=d.a)
    pl().validate_pipeline(d.state, pid, caller=d.a)
    rows, sch, full = tables(d), schema(d), contents(d)
    assert full["pipeline_validations"] and len(full["pipeline_versions"]) == 2          # TC-022: there is something to be left alone
    missing = pid + 1000
    seen = [export(d, pid, v, caller=d.b) for v in (None, 1, 2)] + [export(d, missing, v, caller=d.b) for v in (None, 1, 2)]
    for r in seen:
        assert r["ok"] is False and "zip" not in r and "message" in r
        assert "qc-demo" not in r["message"] and "fastqc" not in r["message"]
    assert len({r["message"].replace(str(missing), "#").replace(str(pid), "#") for r in seen}) == 1
    assert "找不到" in seen[0]["message"]
    assert tables(d) == rows and schema(d) == sch and contents(d) == full


@pytest.mark.parametrize("how", ["missing", "unsupported"])
def test_module_missing_or_unsupported(d, how, tmp_path, monkeypatch):
    # TC-023, TC-024, TC-025, TC-026
    pid = make(d)
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    out = export(d, pid, sources=broken(sources_for(), "multiqc", how))
    assert out["ok"] is False and "zip" not in out and "multiqc" in out["message"]
    assert "換成別的模組" in out["message"]
    assert list(work.iterdir()) == []


def test_too_many_bytes_and_files(d, tmp_path, monkeypatch):
    # TC-027, TC-028, TC-034
    from abf_platform import pipeline_launch
    pid = make(d)
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    a = export(d, pid, sources=big(sources_for(), extra_bytes=pipeline_launch.MAX_BYTES + 1))
    b = export(d, pid, sources=big(sources_for(), extra_files=pipeline_launch.MAX_FILES + 1))
    for r in (a, b):
        assert r["ok"] is False and "zip" not in r and "減少節點" in r["message"]
    assert str(pipeline_launch.MAX_BYTES) in a["message"] and str(pipeline_launch.MAX_FILES) in b["message"]
    assert list(work.iterdir()) == []


def test_the_limits_are_the_launch_ones(d, monkeypatch):
    # TC-029
    from abf_platform import pipeline_launch
    pid = make(d)
    with monkeypatch.context() as m:
        m.setattr(pipeline_launch, "MAX_BYTES", 10)
        r = export(d, pid)
        assert r["ok"] is False and "10" in r["message"]
    with monkeypatch.context() as m:
        m.setattr(pipeline_launch, "MAX_FILES", 3)
        assert export(d, pid)["ok"] is False
    assert export(d, pid)["ok"] is True


PLANTED = "tok-9f3c1e7a52b84d06-NOT-A-REAL-PLANTED"


def test_no_such_version_and_all_failures_are_plain(d, caplog):
    # TC-030, TC-031, TC-032, TC-033
    from abf_platform import actions, pipeline_launch
    pid = make(d)
    caplog.set_level(logging.DEBUG)
    carrying = actions.Caller(d.a.user_id, d.a.name, PLANTED)           # TC-033: the caller carries a token value in the fields it has
    carrying_b = actions.Caller.connector(d.b.user_id, PLANTED, PLANTED, True)
    two = ("減少節點", "use fewer nodes")
    plan = [("no version", dict(version=5), ("沒有版本", "has no version", "已有的版本", "the versions are")),
            ("not found", dict(pid=pid + 99, caller=carrying_b), ("找不到", "not found")),
            ("module missing", dict(sources=broken(sources_for(), "fastqc", "missing")), ("換成別的模組", "use another module")),
            ("unsupported", dict(sources=broken(sources_for(), "fastqc", "unsupported")), ("換成別的模組", "use another module")),
            ("too big", dict(sources=big(sources_for(), extra_bytes=pipeline_launch.MAX_BYTES + 1)), two),
            ("too many files", dict(sources=big(sources_for(), extra_files=pipeline_launch.MAX_FILES + 1)), two)]
    fails = []
    for label, kw, halves in plan:
        kw = dict(kw)
        r = export(d, kw.pop("pid", pid), kw.pop("version", None), caller=kw.pop("caller", carrying), **kw)
        fails.append(r)
        assert r["ok"] is False and "zip" not in r and r["message"], label
        for need in halves:                                           # TC-031: what happened and what to do, in both languages
            assert need in r["message"], (label, need)
        zh, _, en = r["message"].partition(" (")
        assert len(zh.strip()) >= 4 and ")" in en and len(en) >= 12, label
    assert "1" in fails[0]["message"]
    ok = export(d, pid, caller=carrying)
    assert ok["ok"] is True
    for r in fails + [ok]:
        text = json.dumps({k: v for k, v in r.items() if k != "zip"}, ensure_ascii=False, default=str)
        for bad in ("Traceback", str(d.state), "SELECT ", "sqlite", "secret", "password", "token", PLANTED):
            assert bad not in text, bad
    for rec in caplog.records:
        low = rec.getMessage().lower()
        assert PLANTED.lower() not in low and "token" not in low and "password" not in low


def test_public_names_stay_out_of_the_other_exits():
    # TC-050, TC-051, TC-054
    for f in ("mcp_server.py", "web.py", "web_board.py", "actions/__init__.py", "store.py"):
        assert "export_pipeline" not in (PLATFORM / "abf_platform" / f).read_text(encoding="utf-8"), f
