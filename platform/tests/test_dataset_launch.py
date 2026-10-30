# Nothing existing: giving `dataset` (and `dataset_version`) to the launch action and the MCP launch tool is this platform's own rule (spec dataset-cli-launch); no library maps a lab's dataset names onto its confirmation flow.
"""dataset-cli-launch, the launch half: request_launch and the MCP `launch` tool take the name of a dataset of the caller's instead of a
samplesheet, and then go the very same way as samplesheet_text. Test cases (TC-0xx) are those of the test cases of the task.
Everything runs in process on databases under tmp_path: no network, no program is started, no file is read."""
import ast
import asyncio
import json
import os
import re
import sqlite3
from pathlib import Path

import pytest

from helpers import tool_json
from human_harness import World, form_answer
from owner_harness import Duo, sql_rows
from test_cloud_upload import A, make_env
from test_cloud_wire import Wire
from test_cloud_wire import PIPE, SHEET  # noqa: F401
from test_gcb_ce import ip  # noqa: F401
from test_gcb_launch import box  # noqa: F401

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "abf_platform"
UNIQUE = "zq7xk-ds"
NOT_BOTH = "未送出：dataset 與 samplesheet／samplesheet_text 只能給一個 (give dataset, or a samplesheet, not both)"


def _actions():
    from abf_platform import actions
    return actions


def _ds():
    from abf_platform.actions import datasets
    return datasets


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def csv_of(cells):
    return "sample,fastq_1\n" + "".join("s%02d,%s\n" % (i, c) for i, c in enumerate(cells, 1))


def cells_of(d, who, stem="x"):
    area = os.path.realpath(d.area(who))
    return ["%s/%s_s%d.fastq.gz" % (area, stem, i) for i in (1, 2)]


def register(d, who, name="proj", version="v1", stem="x"):
    cells = cells_of(d, who, stem)
    text = csv_of(cells)
    got = _ds().register_dataset(d.state, name=name, version=version, samplesheet=text, files=[{"path": c} for c in cells], caller=who)
    assert got["ok"], got
    return text


def counts(d):
    return tuple(len(sql_rows(d.state, "SELECT * FROM %s" % t)) for t in ("confirmations", "jobs", "launches"))


def ask(d, who, run="run-d", **kw):
    kw.setdefault("ce_name", "lab-a")
    return asyncio.run(_actions().request_launch(d.state, pipeline="nf-core/ampliseq", revision="2.18.0", run_name=run,
                                                 params={"depth": 3}, caller=who, **kw))


def bundle_of(d, out):
    row = sql_rows(d.state, "SELECT bundle_json FROM confirmations WHERE id = ?", (out["id"],))[0]
    return json.loads(row["bundle_json"])


def test_a_dataset_goes_the_way_of_its_samplesheet_text(d):
    # TC-030, TC-031, TC-032, TC-033, TC-061, TC-063
    text1 = register(d, d.a, version="v1", stem="one")
    text2 = register(d, d.a, version="v2", stem="two")
    out = ask(d, d.a, dataset="proj")
    assert out["state"] == "pending" and counts(d)[0] == 1
    same = ask(d, d.a, run="run-t", samplesheet_text=text2)
    a, b = bundle_of(d, out), bundle_of(d, same)
    assert json.dumps(a, sort_keys=True).replace("run-d", "RUN") == json.dumps(b, sort_keys=True).replace("run-t", "RUN")
    assert "dataset" not in a and "dataset_version" not in a
    older = ask(d, d.a, run="run-v1", dataset="proj", dataset_version="v1")
    other = ask(d, d.a, run="run-v1t", samplesheet_text=text1)
    x, y = bundle_of(d, older), bundle_of(d, other)
    assert json.dumps(x, sort_keys=True).replace("run-v1", "RUN") == json.dumps(y, sort_keys=True).replace("run-v1t", "RUN")
    assert x["samplesheet"] != a["samplesheet"]
    register(d, d.a, name=UNIQUE, stem="uniq")
    named = ask(d, d.a, run="run-u", dataset=UNIQUE)
    row = sql_rows(d.state, "SELECT * FROM confirmations WHERE id = ?", (named["id"],))[0]
    assert UNIQUE not in named["summary"] and UNIQUE not in row["screen_text"] and UNIQUE not in row["bundle_json"]


def test_a_dataset_given_with_a_samplesheet_is_refused_and_changes_nothing(d):
    # TC-034, TC-035, TC-036, TC-037, TC-050
    text = register(d, d.a)
    before = counts(d)
    for kw in ({"samplesheet": "/some/sheet.csv"}, {"samplesheet_text": text}):
        out = ask(d, d.a, dataset="proj", **kw)
        assert out["ok"] is False and out["sent"] is False and out["message"] == NOT_BOTH
        assert counts(d) == before
    out = ask(d, d.a)                                             # nothing at all: the words of today
    assert out["message"] == "未送出：samplesheet 與 samplesheet_text 只能給一個 (give exactly one of samplesheet and samplesheet_text)"


def test_a_dataset_name_or_version_that_cannot_be_used_is_refused_without_an_error(d):
    # TC-038, TC-039, TC-040, TC-041, TC-042
    register(d, d.a)
    before = counts(d)
    out = ask(d, d.a, dataset_version="v1")
    assert out["sent"] is False and "dataset_version needs dataset" in out["message"]
    for kw in ({"dataset": ""}, {"dataset": 7}, {"dataset": "proj", "dataset_version": ""}, {"dataset": "proj", "dataset_version": 7}):
        out = ask(d, d.a, **kw)
        assert out["ok"] is False and out["sent"] is False and out["message"].startswith("未送出："), kw
    assert counts(d) == before


def test_what_is_not_found_and_what_is_not_yours_say_the_same(d):
    # TC-043, TC-044, TC-091
    register(d, d.b, name="bobset")
    out = ask(d, d.a, dataset="bobset")
    none = ask(d, d.a, dataset="nosuchset")
    assert "dataset not found" in none["message"] and none["sent"] is False
    assert out["message"].replace("bobset", "<n>") == none["message"].replace("nosuchset", "<n>")
    for text in (out["message"], none["message"]):
        assert "Traceback" not in text and "SELECT" not in text and str(d.state.parent) not in text


@pytest.fixture
def wire(ip, box, monkeypatch):
    return Wire(ip, box, monkeypatch)


def test_a_cloud_dataset_goes_to_google_batch_with_its_places_and_cost_line(wire):
    w = wire
    # TC-045, TC-046, TC-047
    uid = w.alice
    w.env(uid)
    w.cap(uid, 20.00)
    alice = w.caller(uid, "alice")
    places = [A + "a.fastq.gz", A + "b.fastq.gz"]
    text = "sample,fastq_1,strandedness\ns1,%s,auto\ns2,%s,auto\n" % tuple(places)
    got = _ds().register_dataset(w.plat, name="proj", version="v1", samplesheet=text, files=[{"path": p} for p in places],
                                 caller=alice, destination="gcb1")
    assert got["ok"], got
    before = w.counts()
    out = asyncio.run(_actions().request_launch(w.plat, pipeline=PIPE, revision="3.14.0", run_name="run-c", ce_name="gcb1",
                                                params={"genome": "GRCh38"}, caller=alice, dataset="proj"))
    assert out["state"] == "pending" and w.counts()[0] == before[0] + 1
    row = sql_rows(w.plat, "SELECT bundle_json FROM confirmations WHERE id = ?", (out["id"],))[0]
    sheet = json.loads(row["bundle_json"])["samplesheet"]
    assert sorted(r[1] for r in sheet[1:]) == sorted(places)
    same = w.launch(alice, run="run-t", samplesheet_text=text)
    assert same["state"] == "pending" and "費用預估" in out["summary"]
    assert out["summary"].split("\n")[2] == same["summary"].split("\n")[2]


def test_a_cloud_dataset_is_refused_on_a_slurm_environment(d):
    # TC-048, TC-049
    make_env(d, "gcb1", "lab-bucket", d.a)
    places = [A + "a.fastq.gz", A + "b.fastq.gz"]
    assert _ds().register_dataset(d.state, name="proj", version="v1", samplesheet=csv_of(places), files=[{"path": p} for p in places],
                                  caller=d.a, destination="gcb1")["ok"]
    before = counts(d)
    out = ask(d, d.a, dataset="proj")
    same = ask(d, d.a, run="run-t", samplesheet_text=csv_of(places))
    assert out["sent"] is False and out["message"].startswith("未送出：") and out["message"] == same["message"]
    assert counts(d) == before


def test_the_mcp_launch_tool_asks_a_person_and_a_yes_makes_one_job(d):
    # TC-051, TC-052, TC-053, TC-059, TC-060
    register(d, d.a, version="v1", stem="one")
    text2 = register(d, d.a, version="v2", stem="two")
    out = d.launch(d.a, nosheet=True, raw_args={"dataset": "proj", "dataset_version": "v1"})
    assert out["state"] == "pending" and out["confirmation_url"] and d.w.jobs() == []
    assert "one_s1" in out["summary"] or "one_s1" in json.dumps(bundle_of(d, out))
    sent = d.sent(d.a, run="run-s", nosheet=True, raw_args={"dataset": "proj"})
    assert len(d.w.jobs("launch_nextflow")) == 1
    twin = d.sent(d.a, run="run-t", text=text2)
    assert len(d.w.jobs("launch_nextflow")) == 2 and set(sent) == set(twin)
    # the form of the two rows: same columns, and in every column the same kind of value (set or empty, same type); the columns that
    # differ by nature (the run's own name, row id, clock) are left out of the value comparison, and the run name is blanked in the rest
    rows = sql_rows(d.state, "SELECT * FROM launches ORDER BY id")
    assert len(rows) == 2 and sorted(dict(rows[0])) == sorted(dict(rows[1]))
    own = {"id", "run_name", "confirmed_at", "job_id"}

    def shape(r, run):
        return {k: (type(v).__name__, str(v).replace(run, "RUN")) for k, v in dict(r).items() if k not in own}
    assert shape(rows[0], "run-s") == shape(rows[1], "run-t")
    assert {k: type(v).__name__ for k, v in dict(rows[0]).items()} == {k: type(v).__name__ for k, v in dict(rows[1]).items()}


def test_the_launch_tool_has_two_more_properties_and_the_tools_are_the_same(d):
    # TC-054, TC-055, TC-056, TC-057, TC-058
    tools, _ = d.w.mcp([])
    launch = [t for t in tools if t.name == "launch"][0]
    props = set(launch.input_schema["properties"])
    today = {"pipeline", "revision", "run_name", "samplesheet", "samplesheet_text", "ce_name", "params", "path_columns"}
    assert props == today | {"dataset", "dataset_version"}
    assert launch.input_schema["required"] == ["pipeline", "revision", "run_name"]
    assert not [p for p in props if re.search(r"confirm|approve|yes|send|force|skip|accept|送出|void", p)]
    assert "Or name a dataset of yours (dataset, optionally dataset_version): its samplesheet is used." in launch.description
    assert sorted(t.name for t in tools) == ["cancel", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation", "launch", "list_agents", "list_compute_envs",
                                              "list_pipelines", "list_runs", "list_site_files", "list_used_pipelines", "my_usage", "read_run_file", "read_task_log", "relaunch",
                                              "resume", "run_outputs"]


def test_the_terminal_without_users_registers_and_stdio_launches(w, tmp_path):
    # TC-062
    sheet = tmp_path / "s.csv"
    cells = [str(w.uploads / "a_R1.fastq.gz"), str(w.uploads / "a_R2.fastq.gz")]      # inside the environment's read roots
    sheet.write_text(csv_of(cells), encoding="utf-8")
    argv = ["dataset", "register", "--name", "proj", "--version", "v1", "--samplesheet", str(sheet)]
    rc, out = w.ip.run(*argv, "--file", cells[0], "--file", cells[1])
    assert rc == 0, out
    args = w.choices(dataset="proj")
    del args["samplesheet"]
    out = tool_json(w.mcp([("launch", args)], caller=None, raw=True, answer=form_answer())[1][0])      # stdio: the form of the client is the person
    assert out.get("sent") is True and len(w.jobs("launch_nextflow")) == 1, out


def test_only_the_launch_action_calls_get_dataset_and_the_tool_only_passes_two_names():
    # TC-082, TC-083, TC-084, TC-085, TC-065, TC-064
    text = (PKG / "actions" / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    inside = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "request_launch":
            inside = sum(1 for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr == "get_dataset")
    assert inside == 1 and text.count("get_dataset") == 1
    for word in ("register_dataset", "list_datasets", "draft_samplesheet", "check_web_upload", "pair_fastq", "actions.datasets"):
        assert word not in text
    for f in ("mcp_server.py", "web.py", "web_board.py", "store.py"):
        src = (PKG / f).read_text(encoding="utf-8") if (PKG / f).exists() else ""
        for word in ("register_dataset", "list_datasets", "get_dataset", "draft_samplesheet", "check_web_upload", "pair_fastq", "actions.datasets"):
            assert word not in src, (f, word)
    assert not re.search(r"import\s+datasets|from\s+\S*datasets\s+import", (PKG / "mcp_server.py").read_text(encoding="utf-8"))
    con = sqlite3.connect(":memory:")
    con.execute(_ds()._TABLE)
    assert [r[1] for r in con.execute("PRAGMA table_info(datasets)")] == ["id", "owner_user_id", "name", "version", "samplesheet_csv",
                                                                         "files_json", "created_at"]
