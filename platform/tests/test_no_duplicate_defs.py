# Nothing existing: no check in this repo notices the same function copy-pasted into a second production file; this one ratchets it.
"""No new AST-identical, same-named def in two or more production files.

Production = abf_platform, abf_station, abf_launch and scripts/*.py. A def (function, async function, class or
method) counts as a copy when its name and its AST, docstrings stripped and line numbers ignored, equal another's in
a different file. Today's copies are listed in duplicate_defs_baseline.txt, which may only shrink.
"""
import ast
import copy
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINE = pathlib.Path(__file__).resolve().parent / "duplicate_defs_baseline.txt"
PRODUCTION_DIRS = ("platform/abf_platform", "platform/abf_station", "platform/abf_launch", "scripts")

# Names that every entry point or renderer has, so an identical body in two files is not a copy to share.
WHITELIST = {
    "main": "every command-line entry point is called main; identical one-line wrappers are the convention, not drift",
    "render": "each page or card module has its own render hook; an identical body is a coincidence of shape",
}

_DEF = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _strip_docstrings(tree):
    for n in ast.walk(tree):
        if isinstance(n, _DEF + (ast.Module,)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                n.body = n.body[1:] or [ast.Pass()]
    return tree


def find_duplicates(sources):
    """sources: {repo-relative path: source text}. Returns {(name, files tuple)} of identical same-named defs."""
    groups = defaultdict(set)
    for path, text in sources.items():
        tree = _strip_docstrings(copy.deepcopy(ast.parse(text)))
        for n in ast.walk(tree):
            if isinstance(n, _DEF) and n.name not in WHITELIST:
                groups[(n.name, ast.dump(n))].add(path)
    return {(name, tuple(sorted(files))) for (name, _), files in groups.items() if len(files) >= 2}


def production_sources():
    out = {}
    for d in PRODUCTION_DIRS:
        for p in sorted((ROOT / d).rglob("*.py")):
            if "__pycache__" not in p.parts:
                out[p.relative_to(ROOT).as_posix()] = p.read_text(encoding="utf-8")
    return out


def load_baseline():
    entries = set()
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name, *files = line.split()
            entries.add((name, tuple(sorted(files))))
    return entries


def _fmt(entry):
    return f"{entry[0]} {' '.join(entry[1])}"


def test_no_new_duplicate_defs_and_baseline_only_shrinks():
    current = find_duplicates(production_sources())
    baseline = load_baseline()
    new = sorted(c for c in current if not any(c[0] == b[0] and set(c[1]) <= set(b[1]) for b in baseline))
    stale = sorted(b for b in baseline if b not in current)
    msg = []
    if new:
        msg.append("new duplicate defs (share the function instead of copying it, or, if the name is a convention, "
                   "whitelist it with a reason):\n  " + "\n  ".join(_fmt(c) for c in new))
    if stale:
        shrunk = []
        for b in stale:
            now = [c for c in current if c[0] == b[0] and set(c[1]) <= set(b[1])]
            shrunk.append(f"{_fmt(b)}   -> " + (" | ".join(_fmt(c) for c in now) if now else "delete this line"))
        msg.append("baseline lines that no longer match (the baseline may only shrink; edit as shown):\n  " + "\n  ".join(shrunk))
    assert not msg, "\n".join(msg)


def test_baseline_names_are_not_whitelisted_and_files_exist():
    for name, files in load_baseline():
        assert name not in WHITELIST, f"{name} is whitelisted; drop it from the baseline"
        assert len(files) >= 2, f"{name}: a group needs two files"
        for f in files:
            assert (ROOT / f).is_file(), f"{name}: {f} does not exist"


def test_whitelist_entries_carry_a_reason():
    for name, why in WHITELIST.items():
        assert len(why.strip()) >= 15, f"whitelist entry {name} needs a written reason"


# ---- the detector itself, on synthetic sources ----

def test_identical_function_in_two_files_is_found():
    src = "def f(x):\n    return x + 1\n"
    assert find_duplicates({"a.py": src, "b.py": src}) == {("f", ("a.py", "b.py"))}


def test_docstring_and_formatting_do_not_hide_a_copy():
    a = 'def f(x):\n    """one"""\n    return x + 1\n'
    b = "def f(x):\n    '''two, much longer'''\n\n\n    return (x+1)\n"
    assert find_duplicates({"a.py": a, "b.py": b}) == {("f", ("a.py", "b.py"))}


def test_a_different_body_or_signature_or_name_is_not_a_copy():
    base = "def f(x):\n    return x + 1\n"
    assert find_duplicates({"a.py": base, "b.py": "def f(x):\n    return x + 2\n"}) == set()
    assert find_duplicates({"a.py": base, "b.py": "def f(x, y=0):\n    return x + 1\n"}) == set()
    assert find_duplicates({"a.py": base, "b.py": "def g(x):\n    return x + 1\n"}) == set()


def test_same_name_twice_in_one_file_is_not_a_group():
    src = "def f(x):\n    return x\n\nclass C:\n    def f(self, x):\n        return x\n\ndef g(x):\n    return x\n"
    assert find_duplicates({"a.py": src}) == set()
    twice = "def f(x):\n    return x\n\ndef h():\n    def f(x):\n        return x\n"
    assert find_duplicates({"a.py": twice}) == set()


def test_three_files_make_one_group():
    src = "def f():\n    return 1\n"
    assert find_duplicates({"a.py": src, "b.py": src, "c.py": src}) == {("f", ("a.py", "b.py", "c.py"))}


def test_classes_methods_async_and_decorators_count():
    cls = "class C:\n    x = 1\n"
    meth = "class A:\n    def go(self):\n        return 2\n"
    meth2 = "class B:\n    def go(self):\n        return 2\n"
    asy = "async def f():\n    return 1\n"
    assert find_duplicates({"a.py": cls, "b.py": cls}) == {("C", ("a.py", "b.py"))}
    assert find_duplicates({"a.py": meth, "b.py": meth2}) == {("go", ("a.py", "b.py"))}
    assert find_duplicates({"a.py": asy, "b.py": asy}) == {("f", ("a.py", "b.py"))}
    dec = "@staticmethod\ndef f():\n    return 1\n"
    plain = "def f():\n    return 1\n"
    assert find_duplicates({"a.py": dec, "b.py": plain}) == set()


def test_whitelisted_names_are_never_reported():
    for name in WHITELIST:
        src = f"def {name}():\n    return 0\n"
        assert find_duplicates({"a.py": src, "b.py": src}) == set()


def test_two_separate_groups_with_one_name_are_both_reported():
    one, two = "def f():\n    return 1\n", "def f():\n    return 2\n"
    assert find_duplicates({"a.py": one, "b.py": one, "c.py": two, "d.py": two}) == {
        ("f", ("a.py", "b.py")), ("f", ("c.py", "d.py"))}


def test_production_sources_covers_the_packages():
    files = production_sources()
    assert "platform/abf_platform/common.py" in files
    assert "platform/abf_station/rules.py" in files
    assert "platform/abf_launch/build.py" in files
    assert not any(p.startswith("platform/tests/") for p in files)
