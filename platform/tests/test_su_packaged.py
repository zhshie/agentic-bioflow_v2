# Nothing existing: no tool builds a wheel and checks that the SU rates file travels in it and is found by a lone interpreter; the build step and the lookup order are this task's.
"""su-followups: the SU rates file (configs/sites/su_rates.json) is copied into the wheel as abf_platform/data/su_rates.json,
and abf_platform.su reads that copy first, the repository file second. Test cases are named in the comments (TC-001 ...),
see specs/su-followups/test-case.md."""
import ast
import json
import shutil
import subprocess
import sys
import zipfile

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT

PKG = PLATFORM_DIR / "abf_platform"
RATES = REPO_ROOT / "configs" / "sites" / "su_rates.json"
SKILLS = REPO_ROOT / "skills"


def _copy_repo(root):
    shutil.copytree(SKILLS, root / "skills")
    shutil.copytree(REPO_ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(REPO_ROOT / "configs", root / "configs")
    shutil.copytree(PLATFORM_DIR, root / "platform",
                    ignore=shutil.ignore_patterns("tests", "__pycache__", "build", "*.egg-info", "skills"))
    return root


def _pip_wheel(root, out):
    try:
        import setuptools
        modern = int(setuptools.__version__.split(".")[0]) >= 61
    except ImportError:
        modern = False
    cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(out), str(root / "platform")]
    if modern:
        cmd.insert(5, "--no-build-isolation")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="module")
def wheel_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("sucase")
    root = _copy_repo(base / "repo")
    done = _pip_wheel(root, base / "wheels")
    assert done.returncode == 0, "pip wheel failed:\n" + (done.stdout + done.stderr)[-1500:]
    unpacked = base / "unpacked" / "lib"
    with zipfile.ZipFile(next((base / "wheels").glob("*.whl"))) as z:
        z.extractall(unpacked)
    return unpacked


def _isolated(code, path_entries):
    """Run code in `python -I` with only these folders on sys.path (plus the interpreter's own)."""
    prog = "import sys\n" + "".join("sys.path.insert(0, %r)\n" % str(p) for p in path_entries) + code
    return subprocess.run([sys.executable, "-I", "-c", prog], capture_output=True, text=True, timeout=120)


def test_rates_found_in_the_wheel_data(wheel_dir):
    # TC-001, TC-002, TC-003, TC-004
    got = wheel_dir / "abf_platform" / "data" / "su_rates.json"
    assert got.is_file()
    assert got.read_bytes() == RATES.read_bytes()                                    # TC-001
    nf = wheel_dir / "abf_platform" / "data" / "nf-core-modules.json"
    assert nf.read_bytes() == (PKG / "data" / "nf-core-modules.json").read_bytes()   # TC-002
    # TC-003: nothing above the unpacked folder can supply a repository file
    assert not (wheel_dir.parent / "configs" / "sites" / "su_rates.json").exists()
    done = _isolated("from abf_platform import su\nrates = su.load_rates()\n"
                     "print(json.dumps({'path': str(su.RATES_PATH), 'rates': rates})) if (json := __import__('json')) else 0\n",
                     [wheel_dir])
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout.strip().splitlines()[-1])
    want = json.loads(RATES.read_text(encoding="utf-8"))
    assert out["rates"] is not None and "twd_per_su" in out["rates"]["sites"]["nano4"]
    assert out["rates"]["sites"]["nano4"] == want["sites"]["nano4"]
    assert out["path"] == str(got)                                                   # TC-004


def test_checkout_still_uses_repo_configs():
    # TC-005
    assert not (PKG / "data" / "su_rates.json").exists()
    done = _isolated("import json\nfrom abf_platform import su\nr = su.load_rates()\n"
                     "print(json.dumps({'path': str(su.RATES_PATH), 'twd': r['sites']['nano4']['twd_per_su']}))\n", [PLATFORM_DIR])
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["path"] == str(RATES) and out["twd"]


def _shaped(tmp_path, with_repo_file, data_text):
    """root/platform/abf_platform (a copy of the package) and, as asked, root/configs/sites/su_rates.json and the package's data/ copy."""
    root = tmp_path / "root"
    pkg = root / "platform" / "abf_platform"
    shutil.copytree(PKG, pkg, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "skills", "su_rates.json"))
    if with_repo_file is not None:
        (root / "configs" / "sites").mkdir(parents=True)
        (root / "configs" / "sites" / "su_rates.json").write_text(with_repo_file, encoding="utf-8")
    if data_text is not None:
        (pkg / "data").mkdir(exist_ok=True)
        (pkg / "data" / "su_rates.json").write_text(data_text, encoding="utf-8")
    return root, pkg


def test_data_copy_wins_over_the_repo_file(tmp_path):
    # TC-006
    root, pkg = _shaped(tmp_path, json.dumps({"default_site": "A"}), json.dumps({"default_site": "B"}))
    done = _isolated("import json\nfrom abf_platform import su\nprint(json.dumps({'p': str(su.RATES_PATH), 'r': su.load_rates()}))\n",
                     [root / "platform"])
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["p"] == str(pkg / "data" / "su_rates.json") and out["r"] == {"default_site": "B"}


def test_no_rates_file_anywhere_imports_and_reads_none(tmp_path):
    # TC-007
    deep = tmp_path / "a" / "b"
    pkg = deep / "abf_platform"
    shutil.copytree(PKG, pkg, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "skills", "su_rates.json"))
    done = _isolated("from abf_platform import su\nprint(repr(su.load_rates()))\n", [deep])
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines()[-1] == "None"


def test_load_rates_reads_only_rates_path(tmp_path):
    # TC-008
    root, _pkg = _shaped(tmp_path, json.dumps({"default_site": "A"}), json.dumps({"default_site": "B"}))
    done = _isolated("from abf_platform import su\nfrom pathlib import Path\n"
                     "su.RATES_PATH = Path(%r)\nprint(repr(su.load_rates()))\n" % str(tmp_path / "nowhere.json"), [root / "platform"])
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines()[-1] == "None"


def test_build_fails_without_the_rates_file(tmp_path):
    # TC-010, TC-011
    root = _copy_repo(tmp_path / "repo")
    (root / "configs" / "sites" / "su_rates.json").unlink()
    done = _pip_wheel(root, tmp_path / "wheels")
    text = done.stdout + done.stderr
    assert done.returncode != 0
    assert "su_rates.json" in text and "build from a checkout of the repository" in text
    assert not list((tmp_path / "wheels").glob("*.whl"))


def test_gitignore_and_tracking():
    # TC-012
    assert "platform/abf_platform/data/su_rates.json" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    tracked = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files"], capture_output=True, text=True).stdout.splitlines()
    assert [p for p in tracked if p.endswith("su_rates.json")] == ["configs/sites/su_rates.json"]
    assert "platform/abf_platform/data/nf-core-modules.json" in tracked


# ---- su.py never names the site side, not even in pieces --------------------------------------------------------

WORD = "station"


def _spells_word(source):
    """True when the text, any string constant, or the constants of one statement joined in order spell the word."""
    if WORD in source.lower():
        return True
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            pieces = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            if any(WORD in p.lower() for p in pieces) or WORD in "".join(pieces).lower():
                return True
    return False


def test_su_source_never_spells_the_site_side():
    # TC-013
    assert not _spells_word((PKG / "su.py").read_text(encoding="utf-8"))


def test_the_spelling_check_can_go_red():
    # TC-014
    for bad in ('x = "sta" "tion"', 'x = "sta" + "tion"', 'x = "".join(["sta", "tion"])', 'x = "stat" + "ion"'):
        assert _spells_word(bad), bad
    assert not _spells_word("x = 1 + 2\ny = 'rates'")
