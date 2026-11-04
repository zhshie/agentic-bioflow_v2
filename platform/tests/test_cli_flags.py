# Nothing existing: test_cli_contract.py pins the command line without flags; the root flags --version, --json and --debug are new (cli-json-debug-version).
"""The root flags of abf-platform: --version, --json, --debug (specs/cli-json-debug-version/test-case.md).

Flags sit before the command (`abf-platform --json ce show x`). Every case runs in process through abf_platform.cli.main on a
database under tmp_path, the way test_cli_contract.py does, and reuses its MATRIX of every command."""
import ast
import json
import re
import sqlite3
from pathlib import Path

import pytest

from abf_platform import cli, cliout, store
from helpers import REPO_ROOT
from test_cli_contract import (  # noqa: F401  (home is a fixture)
    CE_CREATE, MATRIX, RUNTIME, USER_BOB, call, fill, home, make_launch_dirs, no_leak, prepare)
from test_cli_usage_doc import _launch_commands

PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
LAUNCH = sorted(_launch_commands())
REFUSED = {"serve", "web", "mcp", "user passwd"} | set(LAUNCH)
JSON_DATA = {"ce show", "dataset show"}
CASES = [p for p in MATRIX if MATRIX[p]["happy"] and p not in REFUSED]
RUNTIME_CASES = [(p.values[0], p.values[1], p.id) for p in RUNTIME]
TOKEN = re.compile(r"abf_\S+")


def plugin_version():
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]


def err_object(err):
    obj = json.loads(err)          # exactly one object, nothing else on stderr
    assert set(obj) == {"ok", "command", "error"} and obj["ok"] is False, obj
    assert set(obj["error"]) == {"what", "why", "next"}, obj
    for k, v in obj["error"].items():
        assert isinstance(v, str) and v.strip(), (k, obj)
    return obj


def fresh(home, monkeypatch, tag):
    """A database of its own for one run, so the same command can be run twice from the same starting point."""
    d = home / ("db_" + tag)
    monkeypatch.setenv("ABF_PLATFORM_DB", str(d / "data" / "index.db"))
    return d


def run_case(home, monkeypatch, capsys, path, kind, flags, tag):
    """(rc, stdout, stderr) of the happy or fail case of a command with the given root flags, in a database of its own.
    Random tokens and the database folder are hidden so two runs can be compared."""
    d = fresh(home, monkeypatch, tag)
    make_launch_dirs(home)
    steps, argv = MATRIX[path][kind]
    prepare(steps, capsys)
    rc, out, err = call(list(flags) + fill(argv, capsys), capsys)
    return rc, TOKEN.sub("abf_T", out.replace(str(d), "<DB>")), TOKEN.sub("abf_T", err.replace(str(d), "<DB>"))


# ---- --version ------------------------------------------------------------------------------------------------

def test_version_prints_plugin_json_version(home, capsys):
    # TC-001, TC-002
    rc, out, err = call(["--version"], capsys)
    assert rc == 0 and err == "", (rc, out, err)
    assert out == "abf-platform %s\n" % plugin_version()
    assert "0.1.0" not in out


@pytest.mark.parametrize("argv", [["--json", "--version"], ["--version", "--json"]])
def test_version_json(argv, home, capsys):
    # TC-003, TC-004
    rc, out, err = call(argv, capsys)
    assert rc == 0 and err == "", (rc, out, err)
    obj = json.loads(out)
    assert obj["ok"] is True and obj["data"]["version"] == plugin_version() and obj["command"] == "version", obj


@pytest.mark.parametrize("content", [None, "{}", "not json"], ids=["no file", "no version key", "not json"])
def test_version_missing_plugin_json_is_a_three_part_error(content, home, capsys, monkeypatch):
    # TC-005, TC-006, TC-007, TC-058
    target = home / "gone" / "plugin.json"
    if content is not None:
        target.parent.mkdir()
        target.write_text(content, encoding="utf-8")
    monkeypatch.setattr(cliout, "PLUGIN_JSON", target)
    rc, out, err = call(["--version"], capsys)
    assert rc == 1 and out == "", (rc, out, err)
    assert err.startswith("rejected:") and re.search("[一-鿿]", err) and "0.1.0" not in err, err
    rc, out, err = call(["--json", "--version"], capsys)
    assert rc == 1 and out == "", (rc, out, err)
    obj = err_object(err)
    assert "找不到產品版本" in obj["error"]["what"] and "plugin.json" in obj["error"]["why"] and "PYTHONPATH=platform" in obj["error"]["next"]
    assert "0.1.0" not in err


# ---- --json: success --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", CASES)
def test_json_success_envelope_has_stable_keys(path, home, capsys, monkeypatch):
    # TC-008, TC-009, TC-010, TC-017
    d = fresh(home, monkeypatch, "j")
    make_launch_dirs(home)
    steps, argv = MATRIX[path]["happy"]
    prepare(steps, capsys)
    rc, out, err = call(["--json"] + fill(argv, capsys), capsys)
    assert rc == 0 and err == "", (rc, out, err)
    assert out.count("\n") == 1, out                      # one object, one line
    obj = json.loads(out)
    assert set(obj) == {"ok", "command", "data", "output"} and obj["ok"] is True and isinstance(obj["output"], list), obj
    assert obj["command"] == path
    if path not in JSON_DATA:
        assert obj["data"] == {}, obj
    assert str(d) not in err


def test_json_command_path_is_space_separated(home, capsys):
    # TC-010
    prepare([["agent-token", "new", "a1"], CE_CREATE], capsys)
    rc, out, err = call(["--json", "ce", "show", "s1"], capsys)
    assert rc == 0 and json.loads(out)["command"] == "ce show"


def test_json_data_of_ce_show_and_dataset_show_equals_plain_output(home, capsys):
    # TC-011, TC-012
    make_launch_dirs(home)
    prepare([["agent-token", "new", "a1"], CE_CREATE,
             ["dataset", "register", "--name", "p", "--version", "v1", "--samplesheet", "s.csv", "--file", "a_R1.fq.gz"]], capsys)
    for argv in (["ce", "show", "s1"], ["dataset", "show", "p"]):
        rc, plain, err = call(argv, capsys)
        assert rc == 0, err
        rc, out, err = call(["--json"] + argv, capsys)
        assert rc == 0 and err == "", err
        assert json.loads(out)["data"] == json.loads(plain)


@pytest.mark.parametrize("path", CASES)
def test_json_output_lines_equal_plain_stdout(path, home, capsys, monkeypatch):
    # TC-013, TC-014: wrapping eats no word; the three secret-printing commands keep the secret in `output` only
    rc, plain, perr = run_case(home, monkeypatch, capsys, path, "happy", [], "plain")
    rc2, out, err = run_case(home, monkeypatch, capsys, path, "happy", ["--json"], "json")
    assert rc == rc2 == 0 and perr == err == "", (perr, err)
    obj = json.loads(out)
    assert "\n".join(obj["output"]) + ("\n" if obj["output"] else "") == plain
    if path in ("token new", "pat new", "agent-token new"):
        assert out.count("abf_T") == 1, out               # the secret is in the object once, as in the plain output
        assert plain.count("abf_T") == 1


# ---- --json: failure --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path,case,ident", RUNTIME_CASES, ids=[c[2] for c in RUNTIME_CASES])
def test_json_error_is_what_why_next(path, case, ident, home, capsys):
    # TC-018, TC-019, TC-020, TC-021, TC-025
    make_launch_dirs(home)
    steps, argv = case if case is not None else MATRIX[path]["fail"]
    prepare(steps, capsys)
    prc, pout, perr = call(argv, capsys)
    prepare([], capsys)
    rc, out, err = call(["--json"] + argv, capsys)
    assert rc == prc == 1 and out == "", (rc, out, err)
    obj = err_object(err)
    assert obj["command"] == path
    assert not obj["error"]["what"].startswith("rejected:"), obj
    no_leak(out + err, home)


def test_json_error_what_is_the_plain_sentence_without_rejected(home, capsys):
    # TC-020
    prepare([USER_BOB], capsys)
    _, _, perr = call(USER_BOB, capsys)
    _, _, err = call(["--json"] + USER_BOB, capsys)
    assert perr.startswith("rejected: ")
    assert err_object(err)["error"]["what"] == perr.strip()[len("rejected: "):]


def test_json_argparse_error_is_what_why_next(home, capsys):
    # TC-022, TC-023, TC-024, TC-025
    prc, pout, perr = call(["user", "add"], capsys)
    rc, out, err = call(["--json", "user", "add"], capsys)
    assert rc == prc == 2 and out == "", (rc, out, err)
    obj = err_object(err)
    assert obj["error"]["why"] == "命令列參數不符合這個指令的格式"
    assert obj["error"]["next"].startswith("用 abf-platform ") and obj["error"]["next"].endswith("--help 看正確用法")
    assert "required" in obj["error"]["what"]
    for w in ("Traceback", 'File "', "SELECT ", str(home)):
        assert w not in err


@pytest.mark.parametrize("argv,want", [(["--json", "serve"], "serve"), (["--json", "web"], "web"), (["--json", "mcp"], "mcp"),
                                       (["--json", "user", "passwd", "bob"], "user passwd"),
                                       (["--json", "user", "passwd", "bob", "--temporary"], "user passwd")])
def test_json_refused_for_long_running_and_secret_terminal_commands(argv, want, home, capsys, monkeypatch):
    # TC-026, TC-027, TC-028, TC-029, TC-030, TC-060
    import uvicorn
    from abf_platform import mcp_server

    def boom(*a, **k):
        raise AssertionError("a server was started")
    monkeypatch.setattr(uvicorn, "run", boom)
    monkeypatch.setattr(mcp_server, "run_stdio", boom)
    monkeypatch.setattr(mcp_server, "run_http", boom)
    prepare([USER_BOB], capsys)
    rc, out, err = call(argv, capsys)
    assert rc == 1 and out == "", (rc, out, err)
    obj = err_object(err)
    assert obj["command"] == want
    assert "temporary" not in out and "password" not in out.lower()


@pytest.mark.parametrize("name", LAUNCH)
def test_json_refused_for_launch_registered_commands(name, home, capsys, monkeypatch):
    # TC-031, TC-032, TC-062
    assert name in MATRIX, name
    d = fresh(home, monkeypatch, "l")
    make_launch_dirs(home)
    row = MATRIX[name]
    steps, argv = row["fail"] or row["happy"]
    prepare(steps, capsys)

    def table_rows():
        p = store.default_platform_path()
        if not Path(p).exists():
            return {}
        con = sqlite3.connect(str(p))
        try:
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {t: con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] for t in tables}
        finally:
            con.close()
    before = table_rows()
    rc, out, err = call(["--json"] + fill(argv, capsys), capsys)
    assert rc == 1 and out == "", (rc, out, err)
    obj = err_object(err)
    assert obj["error"] == {"what": "這個指令還不支援 --json", "why": "它的輸出由 abf_launch 自己的出口產生，尚未接上 JSON 外殼",
                            "next": "不加 --json 執行，或等後續版本"}, obj
    assert table_rows() == before


# ---- every _err call has a why and a next ------------------------------------------------------------------------

def test_every_err_call_has_why_and_next():
    # TC-045
    tree = ast.parse((Path(cli.__file__)).read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_err"]
    assert len(calls) >= 40, len(calls)
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords}
        for key in ("why", "next"):
            assert key in kw, "line %d: _err without %s=" % (c.lineno, key)
            v = kw[key]
            assert not (isinstance(v, ast.Constant) and not (isinstance(v.value, str) and v.value.strip())), "line %d: empty %s" % (c.lineno, key)


# ---- without flags nothing changes ---------------------------------------------------------------------------------

V3_TEXT = {
    "user add": "rejected: a user named bob already exists (這個名字已存在)\n",
    "user cloud-cap": "rejected: the monthly cloud cap 'abc' is not allowed: it must be a number of US dollars from 0 to 1,000,000 "
                      "(每月雲端費用上限要是 0 到 1,000,000 之間的美元數字); the cap was not changed (上限沒有改)\n",
    "ce create": "rejected: headQueue is required for a Slurm environment (缺主控佇列 headQueue)\n",
    "ce show": "compute environment nada not found (找不到)\n",
    "web": "rejected: the confirmation page binds loopback only (127.0.0.1, ::1 or localhost), not 0.0.0.0, whatever --public-url says. "
           "It serves plain http and the login cookie must not cross a network in clear text: put a TLS proxy (for example Tailscale "
           "Funnel) on this machine in front of it and give the proxy's address as --public-url https://<address people open> "
           "(確認頁只綁本機位址；要給別人用，請在本機前面放 TLS 代理，並用 --public-url https://… 告訴大家網址)\n",
    "dataset show": "找不到資料集：nada (dataset not found: nada)\n",
    "agent-token new": "rejected: say whose agent this is with --user NAME (請用 --user 名字 指定這個代理是誰的)\n",
}


@pytest.mark.parametrize("path,case,ident", RUNTIME_CASES, ids=[c[2] for c in RUNTIME_CASES])
def test_plain_mode_err_text_unchanged(path, case, ident, home, capsys):
    # TC-044, TC-056
    make_launch_dirs(home)
    steps, argv = case if case is not None else MATRIX[path]["fail"]
    prepare(steps, capsys)
    rc, out, err = call(argv, capsys)
    assert rc == 1 and out == "", (rc, out, err)
    want = V3_TEXT["user cloud-cap"] if ident.startswith("user cloud-cap") else V3_TEXT[path]
    assert err == want


def test_without_flags_nothing_changes(home, capsys):
    # TC-043: the wording of the sentences is pinned above and in test_cli_contract.py; here the shape: no flag, no JSON, no debug line
    prepare([USER_BOB], capsys)
    rc, out, err = call(["user", "cloud-cap", "zed", "5"], capsys)
    assert rc == 1 and out == "" and err.startswith("rejected: ") and "debug:" not in err and not err.lstrip().startswith("{"), err
    rc, out, err = call([], capsys)
    assert rc == 2 and "required: command" in err and out == "", (rc, out, err)


# ---- --debug ---------------------------------------------------------------------------------------------------

DEBUG_CASES = [(p, k) for p in sorted(MATRIX) for k in ("happy", "fail") if MATRIX[p][k]]


@pytest.mark.parametrize("path,kind", DEBUG_CASES, ids=["%s %s" % c for c in DEBUG_CASES])
def test_debug_never_changes_stdout_or_exit(path, kind, home, capsys, monkeypatch):
    # TC-033, TC-034, TC-035, TC-036, TC-038, TC-042
    rc, out, err = run_case(home, monkeypatch, capsys, path, kind, [], "plain")
    drc, dout, derr = run_case(home, monkeypatch, capsys, path, kind, ["--debug"], "debug")
    assert (rc, out) == (drc, dout)
    assert not [l for l in err.splitlines() if l.startswith("debug:")]
    lines = derr.splitlines()
    dbg = [l for l in lines if l.startswith("debug: ")]
    assert dbg, derr
    assert [l for l in lines if not l.startswith("debug: ")] == err.splitlines()      # the only addition is debug lines
    if err == "":
        assert lines == dbg
    text = "\n".join(dbg)
    assert path in text and ("exit %d" % rc) in text and re.search(r"\d+ ms", text), text


def test_debug_lines_leak_nothing(home, capsys, monkeypatch):
    # TC-037, TC-039, TC-061
    monkeypatch.setenv("ABF_SECRET_ENV", "envvalue-12345")
    prepare([["agent-token", "new", "a1"], USER_BOB], capsys)
    rc, out, err = call(["--debug", "--json", "pat", "new", "--user", "bob", "--label", "SECRETLABEL"], capsys)
    assert rc == 0, err
    token = TOKEN.search(out).group(0).rstrip('",]')
    assert token.startswith("abf_") and token not in err
    assert "pat new" in err and "--label" in err and "--user" in err
    argv = ["--debug", "ce", "create", "--name", "SECRETNAME", "--description", "SECRETDESC", "--platform", "slurm-platform",
            "--agent", "a1", "--work-dir", "/SECRETDIR", "--head-queue", "q", "--compute-queue", "q"]
    rc, out, err = call(argv, capsys)
    assert rc == 0, err
    assert "ce create" in err and "--description" in err and "--work-dir" in err
    for w in ("SECRETLABEL", "SECRETNAME", "SECRETDESC", "SECRETDIR", "bob", "slurm-platform", "envvalue-12345", "Traceback", str(home)):
        assert w not in err, (w, err)


def test_debug_with_json_keeps_object_identical(home, capsys, monkeypatch):
    # TC-015, TC-016
    for path in ("ce list", "user add", "token new", "ce show"):
        row = MATRIX[path]
        outs = []
        for i, flags in enumerate((["--json"], ["--debug", "--json"], ["--json", "--debug"])):
            rc, out, err = run_case(home, monkeypatch, capsys, path, "happy", flags, "%s%d" % (path.replace(" ", ""), i))
            assert rc == 0
            outs.append((rc, out))
        # ce show carries creation times that may differ by a second between two databases
        norm = [(rc, re.sub(r"\d{9,}|\d{4}-\d\d-\d\dT[\d:.+Z-]+", "<T>", o)) for rc, o in outs]
        assert norm[0] == norm[1] == norm[2], (path, outs)


def test_unexpected_exception_shows_its_stack_only_with_debug(home, capsys, monkeypatch):
    # TC-040, TC-041
    def boom(args):
        raise RuntimeError("boom-42")
    monkeypatch.setattr(cli, "cmd_pat_list", boom)
    capsys.readouterr()
    with pytest.raises(RuntimeError):
        cli.main(["pat", "list"])
    plain = capsys.readouterr()
    with pytest.raises(RuntimeError):
        cli.main(["--debug", "pat", "list"])
    dbg = capsys.readouterr()
    assert "debug:" not in plain.err and plain.out == dbg.out == ""
    assert "boom-42" in dbg.err and "Traceback" in dbg.err
    assert all(l.startswith("debug: ") for l in dbg.err.splitlines() if l.strip())


# ---- flags only before the command -------------------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [["ce", "list", "--json"], ["ce", "list", "--debug"], ["agent-token", "list", "--json"]])
def test_flags_not_accepted_after_the_command(argv, home, capsys):
    # TC-054, TC-055
    rc, out, err = call(argv, capsys)
    assert rc == 2 and out == "", (rc, out, err)


def test_root_has_the_three_flags_and_leaves_have_only_the_dataset_version():
    # TC-046, TC-048, TC-059
    def parsers(p):
        yield p
        for a in p._actions:
            if isinstance(getattr(a, "choices", None), dict):
                for child in a.choices.values():
                    yield from parsers(child)
    root = cli.build_parser()
    assert {"--version", "--json", "--debug"} <= {o for a in root._actions for o in a.option_strings}
    leaves = [p for p in parsers(root) if p is not root]
    assert not {o for p in leaves for a in p._actions for o in a.option_strings} & {"--json", "--debug"}
    with_version = {p.prog for p in leaves for a in p._actions if "--version" in a.option_strings}
    assert with_version == {"abf-platform dataset register", "abf-platform dataset show"}, with_version


def test_docs_describe_the_flags():
    # TC-051
    text = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    head = text.index("Command-line flags")
    body = text[head:head + 4000]
    for word in ("--version", "--json", "--debug", "before the command", "what", "why", "next"):
        assert word in body, word
