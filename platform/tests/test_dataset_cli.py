# Nothing existing: the `abf-platform dataset` command group is this platform's own front door to its Datasets table (spec dataset-cli-launch); no library registers a lab's samplesheets, and the owner rule and exit codes are ours.
"""dataset-cli-launch, the terminal half: `abf-platform dataset register|list|show`. Test cases (TC-0xx) are those of
the test cases of the task. Everything runs in process on databases under tmp_path: no network, no program is started,
and no file named by --file is opened."""
import ast
import json
import os
import re
import sqlite3
from pathlib import Path

import pytest

from human_harness import PASSWORD, World
from owner_harness import Duo, sql_rows
from test_cloud_upload import A, B, make_env

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "abf_platform"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def sheet_file(tmp, cells, name="s.csv"):
    p = Path(tmp) / name
    p.write_text("sample,fastq_1,fastq_2\ns1,%s,%s\n" % (cells[0], cells[1]), encoding="utf-8")
    return p


def register(ip, tmp, *extra, name="proj", version="v1", sheet=None, files=("a_R1.fastq.gz", "a_R2.fastq.gz")):
    sheet = sheet or sheet_file(tmp, files)
    argv = ["dataset", "register", "--name", name, "--version", version, "--samplesheet", str(sheet)]
    for f in files:
        argv += ["--file", f]
    return ip.run(*argv, *extra)


def datasets_in(ip):
    try:
        return sql_rows(ip.state_db, "SELECT * FROM datasets ORDER BY id")
    except sqlite3.OperationalError:
        return []


def clean(out, tmp):
    # TC-091: no stack, no SQL, no internal path, no secret (the web password the users of the Duo really hold) in what the person is told
    assert "Traceback" not in out and "SELECT" not in out and "sqlite" not in out.lower() and PASSWORD not in out
    assert str(tmp) not in out


def test_register_list_and_show_without_users(w, tmp_path):
    # TC-001, TC-002, TC-003, TC-004, TC-020
    ip = w.ip
    rc, out = register(ip, tmp_path)
    assert rc == 0 and "已登記資料集 proj 版本 v1（2 個檔案）(registered)" in out, out
    rc, out = ip.run("dataset", "list")
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert rc == 0 and len(lines) == 1 and "proj" in lines[0] and "v1" in lines[0] and " 2 " in lines[0] + " ", out
    rc, out = ip.run("dataset", "show", "proj")
    got = json.loads(out)
    assert rc == 0 and "s1,a_R1.fastq.gz,a_R2.fastq.gz" in got["samplesheet"]
    assert [f["path"] for f in got["files"]] == ["a_R1.fastq.gz", "a_R2.fastq.gz"]
    assert out.strip() == json.dumps(got, indent=2, sort_keys=True, ensure_ascii=False)
    assert register(ip, tmp_path, version="v2")[0] == 0
    rc, out = ip.run("dataset", "show", "proj", "--version", "v1")
    assert rc == 0 and json.loads(out)["version"] == "v1"
    assert json.loads(ip.run("dataset", "show", "proj")[1])["version"] == "v2"
    rc, out = ip.run("dataset", "show", "nosuchset")
    assert rc == 1 and "找不到資料集" in out


def test_a_second_registration_of_the_same_name_and_version_is_refused(w, tmp_path):
    # TC-005, TC-091
    assert register(w.ip, tmp_path)[0] == 0
    rc, out = register(w.ip, tmp_path)
    assert rc == 1 and "已存在" in out and len(datasets_in(w.ip)) == 1
    clean(out, tmp_path)


def test_with_users_the_terminal_must_name_one(d, tmp_path):
    # TC-006, TC-007, TC-008, TC-009
    from abf_launch import cli as launch_cli
    ip = d.w.ip
    said = launch_cli._account(None)[1]
    assert said
    for argv in (("dataset", "list"), ("dataset", "show", "proj")):
        rc, out = ip.run(*argv)
        assert rc == 1 and said in out, out
    rc, out = register(ip, tmp_path)
    assert rc == 1 and said in out and datasets_in(ip) == []
    rc, out = register(ip, tmp_path, "--user", "nobody")
    assert rc == 1 and "沒有這個帳號：nobody" in out and datasets_in(ip) == []


def test_a_cloud_dataset_is_registered_for_the_named_user_and_only_below_their_prefix(d, tmp_path):
    # TC-010, TC-011, TC-012, TC-013, TC-091
    ip = d.w.ip
    make_env(d, "gcb1", "lab-bucket", d.a)
    mine = [A + "a_R1.fastq.gz", A + "a_R2.fastq.gz"]
    rc, out = register(ip, tmp_path, "--user", "alice", "--destination", "gcb1", files=mine, sheet=sheet_file(tmp_path, mine))
    assert rc == 0, out
    rc, out = ip.run("dataset", "list", "--user", "alice")
    assert rc == 0 and "proj" in out
    assert [r["owner_user_id"] for r in datasets_in(ip)] == [d.a.user_id]
    theirs = [B + "a_R1.fastq.gz", B + "a_R2.fastq.gz"]
    rc, out = register(ip, tmp_path, "--user", "alice", "--destination", "gcb1", name="other", files=theirs,
                       sheet=sheet_file(tmp_path, theirs, "t.csv"))
    assert rc == 1 and "alice" in out and "bob" not in out and len(datasets_in(ip)) == 1
    clean(out, tmp_path)


def test_a_samplesheet_that_cannot_be_used_registers_nothing(w, tmp_path):
    # TC-014, TC-015, TC-016, TC-017, TC-091
    bad = {"missing.csv": None, "big.csv": b"a" * (1024 * 1024 + 1), "nul.csv": b"a,b\n\x00\n", "latin.csv": b"sample,\xff\xfe\n"}
    for name, content in bad.items():
        p = tmp_path / name
        if content is not None:
            p.write_bytes(content)
        rc, out = register(w.ip, tmp_path, sheet=p)
        assert rc == 1 and out.strip(), (name, out)
        clean(out, tmp_path)
        assert datasets_in(w.ip) == [], name


def test_one_user_cannot_list_or_show_the_dataset_of_another(d, tmp_path):
    # TC-018, TC-019, TC-091
    from abf_platform.actions import datasets
    ip = d.w.ip
    for who, name in ((d.a, "aliceset"), (d.b, "bobset")):
        area = os.path.realpath(d.area(who))
        cells = ["%s/x_R1.fastq.gz" % area, "%s/x_R2.fastq.gz" % area]
        text = "sample,fastq_1,fastq_2\ns1,%s,%s\n" % tuple(cells)
        assert datasets.register_dataset(d.state, name=name, version="v1", samplesheet=text, files=[{"path": c} for c in cells], caller=who)["ok"]
    rc, out = ip.run("dataset", "list", "--user", "alice")
    assert rc == 0 and "aliceset" in out and "bobset" not in out
    rc, other = ip.run("dataset", "show", "bobset", "--user", "alice")
    rc2, none = ip.run("dataset", "show", "nosuchset", "--user", "alice")
    assert rc == rc2 == 1 and other.replace("bobset", "<n>") == none.replace("nosuchset", "<n>")
    clean(other, tmp_path)


def test_register_needs_a_file_and_never_opens_one(w, tmp_path):
    # TC-021, TC-022
    s = sheet_file(tmp_path, ("a", "b"))
    rc, out = w.ip.run("dataset", "register", "--name", "proj", "--version", "v1", "--samplesheet", str(s))
    assert rc == 2 and datasets_in(w.ip) == []
    ghost = str(tmp_path / "no" / "such" / "file.fastq.gz")
    rc, out = register(w.ip, tmp_path, files=(ghost, ghost + "2"), sheet=sheet_file(tmp_path, (ghost, ghost + "2"), "g.csv"))
    assert rc == 0 and len(datasets_in(w.ip)) == 1, out


def _walk(parser, seen, path=()):
    for act in parser._actions:
        for opt in getattr(act, "option_strings", []):
            seen.setdefault(path, set()).add(opt.lstrip("-"))
        ch = getattr(act, "choices", None)
        if isinstance(ch, dict):
            seen.setdefault(path, set()).update(ch)
            for name, sub in ch.items():
                _walk(sub, seen, path + (name,))


def test_the_group_adds_only_its_three_commands_and_options_and_no_other_door(w):
    # TC-023, TC-024, TC-025, TC-026
    from abf_platform import cli
    seen = {}
    _walk(cli.build_parser(), seen)
    assert {"register", "list", "show"} == seen[("dataset",)] - {"h", "help"}
    mine = set().union(*(v for k, v in seen.items() if k[:1] == ("dataset",))) - {"register", "list", "show", "h", "help"}
    assert mine <= {"name", "version", "samplesheet", "file", "user", "destination"}
    assert not mine & {"retry", "confirm", "yes", "y", "force", "assume-yes", "no-confirm"}
    assert cli.ADOPTING == ("serve", "web", "mcp", "ce")
    assert not [o for o in seen[("launch",)] if "dataset" in o]
    routes = sorted(set(re.findall(r'Route\("([^"]*)"', (PKG / "web.py").read_text(encoding="utf-8"))))
    assert routes == ["/", "/.well-known/oauth-authorization-server", "/act/{verb}", "/c/{rid}", "/consent/{rid}", "/launch", "/launch/diagram", "/login", "/logout", "/settings", "/usage", "/welcome"]


def test_every_dataset_command_is_handled_by_one_action_function_and_by_nothing_else():
    # TC-090: both sides listed. The terminal's side is read from the parser (which handler each sub-command really runs) and from the
    # source of that handler; the action layer's side is read from the module. A handler that did its own work would not match.
    from abf_platform import cli
    from abf_platform.actions import datasets
    pairs = {"register": ("cmd_dataset_register", "register_dataset", ["--name", "n", "--version", "v", "--samplesheet", "s.csv", "--file", "f"]),
             "list": ("cmd_dataset_list", "list_datasets", []),
             "show": ("cmd_dataset_show", "get_dataset", ["n"])}
    parser = cli.build_parser()
    for sub, (handler, action, rest) in pairs.items():
        assert getattr(cli, handler) is parser.parse_args(["dataset", sub] + rest).func, sub
        assert callable(getattr(datasets, action)), action
    src = (PKG / "cli.py").read_text(encoding="utf-8")
    funcs = {n.name: n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    for sub, (handler, action, _) in pairs.items():
        calls = [n for n in ast.walk(funcs[handler]) if isinstance(n, ast.Call)]
        via = [c for c in calls if isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) and c.func.value.id == "datasets"]
        assert [c.func.attr for c in via] == [action], (sub, [c.func.attr for c in via])
        names = {n.id for n in ast.walk(funcs[handler]) if isinstance(n, ast.Name)}
        assert not names & {"sqlite3", "sql_rows", "json_loads", "csv"}, (handler, names)
        assert "execute" not in {n.attr for n in ast.walk(funcs[handler]) if isinstance(n, ast.Attribute)}, handler
    # the MCP side: the `launch` tool hands `dataset` on to the one launch action and does nothing else with it
    mcp = ast.parse((PKG / "mcp_server.py").read_text(encoding="utf-8"))
    passed = [kw.arg for n in ast.walk(mcp) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "request_launch"
              for kw in n.keywords]
    assert "dataset" in passed and "dataset_version" in passed, passed
