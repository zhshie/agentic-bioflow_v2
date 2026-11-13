# Nothing existing: no test checks that the platform tests themselves leave the maintainer's real ~/.abf/studio.json alone (the bug: a blanket monkeypatch.undo() in test_studio_remote dropped the home patch, then save_config wrote a dummy token there).
"""Bug test-home-leak. The tests must never write to the real home. Three checks:
(a) after a test calls monkeypatch.undo(), the studio config path still does not resolve under the real home;
(b) no test function reaches save_config / write_config / studio-connect after a bare monkeypatch.undo() in the same function;
(c) the session-level fingerprint of the real studio.json notices a change (and never reads the file)."""
import ast
import os
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
REAL_HOME = Path(os.path.expanduser("~")).resolve()       # captured at import, before any test patches Path.home
WRITERS = {"save_config", "write_config"}


def _under(p, root):
    try:
        Path(p).resolve().relative_to(root)
        return True
    except ValueError:
        return False


def test_undo_does_not_expose_the_real_home(monkeypatch):
    # TC-HOME-1: a test's own monkeypatch.undo() must not let config_path() fall back to the real home.
    from abf_platform import studio_remote
    monkeypatch.undo()
    assert not _under(studio_remote.config_path(), REAL_HOME), studio_remote.config_path()


def _undo_then_write(tree):
    found = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        undo_lines = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == "undo" and isinstance(n.func.value, ast.Name) and n.func.value.id == "monkeypatch"]
        if not undo_lines:
            continue
        first = min(undo_lines)
        for n in ast.walk(fn):
            if getattr(n, "lineno", 0) <= first:
                continue
            if isinstance(n, ast.Call):
                name = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
                if name in WRITERS:
                    found.append((fn.name, n.lineno, name))
            elif isinstance(n, ast.Constant) and n.value == "studio-connect":
                found.append((fn.name, n.lineno, "studio-connect"))
    return found


def test_static_no_blanket_undo_then_config_write():
    # TC-HOME-2: simple and honest: it looks only for a bare monkeypatch.undo() followed, in the same function, by a call to
    # save_config/write_config or the text "studio-connect". It does not follow helpers that call those.
    bad = []
    for f in sorted(TESTS.glob("test_*.py")):
        if f.name == Path(__file__).name:
            continue
        bad += [(f.name,) + hit for hit in _undo_then_write(ast.parse(f.read_text(encoding="utf-8")))]
    assert not bad, bad


def test_the_checker_itself_catches_the_pattern():
    # TC-HOME-3: the static check is not vacuous.
    src = "def test_x(monkeypatch):\n    monkeypatch.undo()\n    write_config(1, 2)\n"
    assert _undo_then_write(ast.parse(src)) == [("test_x", 3, "write_config")]


def test_fingerprint_sees_a_change_and_never_reads_content(tmp_path):
    # TC-HOME-4: the session-level fingerprint (size + mtime only) differs after a write and for a created file.
    import conftest
    p = tmp_path / "studio.json"
    absent = conftest.studio_fingerprint(p)
    p.write_text("a")
    one = conftest.studio_fingerprint(p)
    os.utime(p, ns=(1, 1))
    two = conftest.studio_fingerprint(p)
    assert absent is None and one != absent and two != one
    assert "a" not in repr(one)
