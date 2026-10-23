# Nothing existing: tests that the wheel carries scripts/ and configs/ for abf-station and that the default plugin root finds them; the rules are ours.
"""abf-station finds its own scripts after `pip install` (task station-packaged-scripts).

Test cases are named in the comments (TC-SP-01 ...), see specs/station-packaged-scripts/test-case.md.
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT

sys.path.insert(0, str(PLATFORM_DIR))
SCRIPTS = REPO_ROOT / "scripts"
CONFIGS = REPO_ROOT / "configs"
SKIP = ("__pycache__",)


def _files(root):
    return {str(p.relative_to(root)).replace("\\", "/"): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and not any(s in p.parts for s in SKIP) and p.suffix != ".pyc"}


def _copy_repo(tmp_path, scripts=True, configs=True):
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "skills", root / "skills")
    if scripts:
        shutil.copytree(SCRIPTS, root / "scripts", ignore=shutil.ignore_patterns(*SKIP, "*.pyc"))
    if configs:
        shutil.copytree(CONFIGS, root / "configs")
    shutil.copytree(PLATFORM_DIR, root / "platform",
                    ignore=shutil.ignore_patterns("tests", "__pycache__", "build", "*.egg-info", "skills", "plugin"))
    return root


def _build(root, out):
    cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(out), str(root / "platform")]
    try:
        import setuptools
        if int(setuptools.__version__.split(".")[0]) >= 61:
            cmd.insert(5, "--no-build-isolation")
    except ImportError:
        pass
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="module")
def wheel_dir(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sp")
    root = _copy_repo(tmp)
    done = _build(root, tmp / "wheels")
    if done.returncode != 0:
        pytest.fail("pip wheel failed:\n" + (done.stdout + done.stderr)[-1500:])
    unpacked = tmp / "unpacked"
    with zipfile.ZipFile(next((tmp / "wheels").glob("*.whl"))) as z:
        z.extractall(unpacked)
    return unpacked


def _tree(wheel_dir, sub):
    return _files(wheel_dir / "abf_station" / "plugin" / sub)


def test_sp01_wheel_ships_the_scripts_folder(wheel_dir):
    # TC-SP-01
    got = _tree(wheel_dir, "scripts")
    for name in ("on_site.sh", "settings.sh", "egress_allow.sh"):
        assert got[name] == (SCRIPTS / name).read_bytes()


def test_sp02_the_whole_scripts_folder_is_there(wheel_dir):
    # TC-SP-02
    assert _tree(wheel_dir, "scripts") == _files(SCRIPTS)


def test_sp03_configs_sites_is_there(wheel_dir):
    # TC-SP-03
    got = _tree(wheel_dir, "configs/sites")
    assert got == _files(CONFIGS / "sites") and "su_rates.json" in got and "nchc.config" in got


def _fake_pkg(tmp_path, monkeypatch, packaged):
    from abf_station import site
    pkg = tmp_path / "abf_station"
    pkg.mkdir()
    if packaged:
        (pkg / "plugin" / "scripts").mkdir(parents=True)
        (pkg / "plugin" / "scripts" / "on_site.sh").write_text("#!/bin/bash\n")
    monkeypatch.setattr(site, "__file__", str(pkg / "site.py"))
    return site, pkg


def test_sp04_default_plugin_root_prefers_the_packaged_copy(tmp_path, monkeypatch):
    # TC-SP-04
    site, pkg = _fake_pkg(tmp_path, monkeypatch, True)
    assert site.default_plugin_root() == pkg / "plugin"


def test_sp05_checkout_falls_back_to_repo_root():
    # TC-SP-05
    from abf_station import site
    root = site.default_plugin_root()
    assert root == Path(site.__file__).resolve().parents[2]
    assert site.on_site_script(root).is_file()


def _deployment(tmp_path):
    dep = tmp_path / "dep"
    (dep / "config").mkdir(parents=True)
    (dep / "config" / "env.yaml").write_text("reach: local\nstorage_root: %s\n" % (tmp_path / "st"))
    return dep


def _no_other_problems(cli, monkeypatch):
    monkeypatch.setattr(cli, "windows_problem", lambda: None)
    monkeypatch.setattr(cli, "url_problem", lambda u: None)
    monkeypatch.setattr(cli, "token_problem", lambda t: None)


def test_sp06_explicit_plugin_root_still_wins(tmp_path, monkeypatch, capsys):
    # TC-SP-06
    from abf_station import cli
    _fake_pkg(tmp_path, monkeypatch, True)
    other = tmp_path / "other"
    other.mkdir()
    dep = _deployment(tmp_path)
    _no_other_problems(cli, monkeypatch)
    rc = cli.cmd_run(argparse.Namespace(plugin_root=str(other), deployment=str(dep), platform="http://127.0.0.1:1",
                                        token_file="x", name=None))
    out = capsys.readouterr().out
    assert rc == cli.EXIT_REFUSED and str(other.resolve() / "scripts" / "on_site.sh") in out
    rc = cli.cmd_unforward(argparse.Namespace(plugin_root=str(other), deployment=str(dep)))
    assert rc == cli.EXIT_REFUSED and str(other.resolve() / "scripts" / "on_site.sh") in capsys.readouterr().out


def test_sp07_wheel_only_environment_passes_the_deployment_check(tmp_path, wheel_dir):
    # TC-SP-07, TC-SP-10
    dep = _deployment(tmp_path)
    code = ("import os, sys; sys.path.insert(0, os.environ['WH']); from abf_station import cli, site; "
            "r = site.default_plugin_root(); print(r); print(cli.deployment_problem(sys.argv[1], r))")
    done = subprocess.run([sys.executable, "-I", "-c", code, str(dep)], capture_output=True, text=True,
                          cwd=str(tmp_path), env={**os.environ, "WH": str(wheel_dir)})
    lines = done.stdout.strip().splitlines()
    assert done.returncode == 0, done.stderr
    assert Path(lines[0]) == wheel_dir / "abf_station" / "plugin" and lines[1] == "None"


def _plugin_copy(tmp_path, wheel_dir):
    dest = tmp_path / "plugin_copy"
    shutil.copytree(wheel_dir / "abf_station" / "plugin", dest)
    for p in (dest / "scripts").rglob("*"):
        if p.is_file():
            p.chmod(0o644)                    # no executable bit anywhere
    return dest


def test_sp08_site_calls_the_packaged_script_without_an_executable_bit(tmp_path, wheel_dir, monkeypatch):
    # TC-SP-08
    from abf_station.site import Site
    plugin = _plugin_copy(tmp_path, wheel_dir)
    dep = _deployment(tmp_path)
    monkeypatch.setenv("ON_SITE_DRY_RUN", "1")
    res = Site(plugin, dep / "config" / "env.yaml", log=lambda *_: None).call(["echo hi"])
    assert res.rc == 0 and b"local" in res.out, (res.rc, res.out, res.err)


def test_sp09_the_ssh_bundle_command_works_on_the_packaged_root(wheel_dir):
    # TC-SP-09
    plugin = wheel_dir / "abf_station" / "plugin"
    made = subprocess.run(["tar", "-cz", "-C", str(plugin), "scripts", "configs"], capture_output=True)
    assert made.returncode == 0
    listing = subprocess.run(["tar", "-tz"], input=made.stdout, capture_output=True, text=True).stdout
    assert "scripts/on_site.sh" in listing and "configs/sites/su_rates.json" in listing


def _refusal(tmp_path, monkeypatch, capsys, func):
    from abf_station import cli
    _fake_pkg(tmp_path, monkeypatch, False)
    monkeypatch.setattr(cli.site, "default_plugin_root", lambda: tmp_path / "nowhere")
    _no_other_problems(cli, monkeypatch)
    tok = tmp_path / "tok"
    tok.write_text("SECRET_TOKEN_CANARY\n")
    dep = _deployment(tmp_path)
    ns = argparse.Namespace(plugin_root=None, deployment=str(dep), platform="http://127.0.0.1:1", token_file=str(tok), name=None)
    rc = getattr(cli, func)(ns)
    cap = capsys.readouterr()
    return rc, cap.out + cap.err


@pytest.mark.parametrize("func", ["cmd_run", "cmd_unforward"])
def test_sp11_missing_script_is_explained(tmp_path, monkeypatch, capsys, func):
    # TC-SP-11, TC-SP-12, TC-SP-13
    from abf_station import cli
    rc, out = _refusal(tmp_path, monkeypatch, capsys, func)
    assert rc == cli.EXIT_REFUSED
    assert str(tmp_path / "nowhere" / "scripts" / "on_site.sh") in out and "--plugin-root" in out
    assert "not in this install" in out or "安裝版" in out
    assert "Traceback" not in out and "SECRET_TOKEN_CANARY" not in out


@pytest.mark.parametrize("missing", ["scripts", "configs"])
def test_sp14_a_build_without_its_source_fails(tmp_path, missing):
    # TC-SP-14, TC-SP-15
    root = _copy_repo(tmp_path, scripts=missing != "scripts", configs=missing != "configs")
    done = _build(root, tmp_path / "wheels")
    assert done.returncode != 0 and missing in done.stdout + done.stderr
    assert not list((tmp_path / "wheels").glob("*.whl"))


def test_sp16_the_copy_is_gitignored_and_untracked():
    # TC-SP-16
    assert "platform/abf_station/plugin/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "platform/abf_station/plugin"], capture_output=True, text=True).stdout
    assert out.strip() == ""


def test_sp24_parser_keeps_plugin_root_option():
    # TC-SP-24
    from abf_station import cli
    p = cli.build_parser()
    for sub in (["run", "--platform", "http://x", "--token-file", "t", "--deployment", "d", "--plugin-root", "P"],
                ["unforward", "--deployment", "d", "--plugin-root", "P"]):
        assert p.parse_args(sub).plugin_root == "P"
    assert p.parse_args(["unforward", "--deployment", "d"]).plugin_root is None


def test_sp27_packaged_on_site_finds_its_neighbours_from_any_folder(tmp_path, wheel_dir):
    # TC-SP-27
    plugin = _plugin_copy(tmp_path, wheel_dir)
    dep = _deployment(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = {**os.environ, "ON_SITE_DRY_RUN": "1", "LAB_SETTINGS_FILE": str(dep / "config" / "env.yaml")}
    done = subprocess.run(["bash", str(plugin / "scripts" / "on_site.sh"), "echo hi"], cwd=str(elsewhere), env=env,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
