# Nothing existing: no syrupy in the test venv (constraints.txt has it not, tests/platform_test.sh installs mcp pytest httpx only), so the committed-snapshot compare is this small helper.
"""Command tree and --help text of abf-platform pinned by text files committed in tests/__golden__/.

The compare is the default and the only thing a plain run does. A file is written only when
ABF_UPDATE_GOLDEN=1 is set, and even then the test that wrote it still fails, so that a person
reads the diff and runs it again. Never regenerate all files in one go without reading each diff."""
import argparse
import difflib
import os
import re
from pathlib import Path

import pytest

from abf_platform import cli

GOLDEN_DIR = Path(__file__).resolve().parent / "__golden__"

# Every snapshot name the tests refer to (TC-016 checks each has a file).
TREE_NAME = "cli_tree"
HELP_NAMES = {  # name -> the argv before --help
    "cli_help_top": [],
    "cli_help_user_add": ["user", "add"],
    "cli_help_ce_create": ["ce", "create"],
}
JSON_NAMES = ("cli_json_ce_show", "cli_json_dataset_show")
GOLDEN_NAMES = (TREE_NAME,) + tuple(HELP_NAMES) + JSON_NAMES


def _lf(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def assert_golden(name, text, golden_dir=None):
    """Compare text with <golden_dir>/<name>.txt; fail with a unified diff. Never writes unless ABF_UPDATE_GOLDEN=1 (and then still fails)."""
    path = Path(golden_dir or GOLDEN_DIR) / (name + ".txt")
    text = _lf(text)
    update = os.environ.get("ABF_UPDATE_GOLDEN") == "1"
    if not path.is_file():
        if update:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            raise AssertionError("snapshot %s did not exist; wrote it (ABF_UPDATE_GOLDEN=1). Read it, then run again without the variable" % path.name)
        raise AssertionError("snapshot %s is missing (it is never created by a plain run); generate it with ABF_UPDATE_GOLDEN=1, read it, commit it" % path.name)
    with open(path, encoding="utf-8", newline="") as f:
        old = _lf(f.read())
    if old == text:
        return
    diff = "".join(difflib.unified_diff(old.splitlines(True), text.splitlines(True), "committed/" + path.name, "actual/" + path.name))
    if update:
        path.write_text(text, encoding="utf-8", newline="\n")
        raise AssertionError("snapshot %s changed and was rewritten (ABF_UPDATE_GOLDEN=1). Read this diff, then run again:\n%s" % (path.name, diff))
    raise AssertionError("output differs from the committed snapshot %s:\n%s" % (path.name, diff))


# ---- command tree ----------------------------------------------------------------------------

def _subparsers_of(parser):
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            return a
    return None


def walk_leaves(parser, path=()):
    """Yield (path, leaf parser, help text the parent shows for it) for every command that runs something."""
    sub = _subparsers_of(parser)
    if sub is None:
        yield path, parser
        return
    for name, child in sub.choices.items():
        yield from walk_leaves(child, path + (name,))


def _help_of_command(root, path):
    parser = root
    text = ""
    for name in path:
        sub = _subparsers_of(parser)
        text = next((a.help for a in sub._choices_actions if a.dest == name), None) or ""
        parser = sub.choices[name]
    return text


def tree_text(parser=None):
    root = parser or cli.build_parser()
    lines = []
    for path, leaf in walk_leaves(root):
        opts, req, defaults, helps = [], [], [], []
        for a in leaf._actions:
            if isinstance(a, argparse._HelpAction):
                continue
            label = ",".join(a.option_strings) if a.option_strings else a.dest
            opts.append(label)
            req.append("yes" if (a.required if a.option_strings else a.nargs not in ("?", "*")) else "no")
            defaults.append(repr(None if a.default is argparse.SUPPRESS else a.default))
            helps.append("%s: %s" % (label, a.help or ""))
        text = " ".join((_help_of_command(root, path) + " // " + (leaf.description or "")).split())
        lines.append("｜".join([" ".join(path), ",".join(opts), ",".join(req), ",".join(defaults),
                               " ## ".join([text] + helps)]))
    return "\n".join(sorted(lines)) + "\n"


def help_text(argv, capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "100")
    with pytest.raises(SystemExit) as e:
        cli.main(list(argv) + ["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    return re.sub(r"^optional arguments:", "options:", _lf(out), flags=re.M)


# ---- tests -----------------------------------------------------------------------------------

def test_snapshot_missing_fails(tmp_path, monkeypatch):
    # TC-013
    monkeypatch.delenv("ABF_UPDATE_GOLDEN", raising=False)
    g = tmp_path / "g"
    g.mkdir()
    with pytest.raises(AssertionError, match="missing"):                      # (a) no file: fail
        assert_golden("nope", "x\n", golden_dir=g)
    assert list(g.iterdir()) == []                                           # (c) nothing written
    (g / "has.txt").write_text("one\ntwo\n", encoding="utf-8", newline="\n")
    with pytest.raises(AssertionError) as e:                                 # (b) other content: fail with a diff
        assert_golden("has", "one\nTHREE\n", golden_dir=g)
    assert "-two" in str(e.value) and "+THREE" in str(e.value)
    assert (g / "has.txt").read_text(encoding="utf-8") == "one\ntwo\n"       # (c) untouched
    assert_golden("has", "one\r\ntwo\r\n", golden_dir=g)                      # CRLF is normalised, same content passes
    monkeypatch.setenv("ABF_UPDATE_GOLDEN", "1")
    with pytest.raises(AssertionError, match="rewritten"):                    # (d) written, and still a failure
        assert_golden("has", "one\nTHREE\n", golden_dir=g)
    assert (g / "has.txt").read_text(encoding="utf-8") == "one\nTHREE\n"
    assert_golden("has", "one\nTHREE\n", golden_dir=g)                        # second run (same text) passes


def test_command_tree_snapshot():
    # TC-014
    assert_golden(TREE_NAME, tree_text())


@pytest.mark.parametrize("name", sorted(HELP_NAMES))
def test_help_snapshots(name, capsys, monkeypatch):
    # TC-015
    assert_golden(name, help_text(HELP_NAMES[name], capsys, monkeypatch))


def test_snapshots_are_committed():
    # TC-016
    files = sorted(p for p in GOLDEN_DIR.iterdir() if p.is_file()) if GOLDEN_DIR.is_dir() else []
    assert files, "no snapshot files in %s" % GOLDEN_DIR
    for p in files:
        raw = p.read_bytes()
        assert raw, "%s is empty" % p.name
        raw.decode("utf-8")
        assert b"\r" not in raw, "%s has CR characters (LF only)" % p.name
    names = {p.stem for p in files}
    assert set(GOLDEN_NAMES) <= names, "missing snapshot files: %s" % sorted(set(GOLDEN_NAMES) - names)
    assert len([n for n in names if n.startswith("cli_help_")]) >= 3
    assert len([n for n in names if n.startswith("cli_json_")]) >= 2
