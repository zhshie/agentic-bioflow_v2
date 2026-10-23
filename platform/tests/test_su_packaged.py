# Nothing existing: tests that the SU rates file is found from the wheel's own plugin folder and from a checkout; the lookup rule is ours.
"""su-followups: abf_platform.su reads su_rates.json from abf_station/plugin/configs/sites after `pip install`, else from the repo.

Test cases TC-SF-01 ... TC-SF-06 are named in the comments (the verifier's list for the su-followups task)."""
import json
import os
import shutil
import subprocess
import sys
import zipfile

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from test_station_packaging import _build, _copy_repo

REPO_RATES = REPO_ROOT / "configs" / "sites" / "su_rates.json"


@pytest.fixture(scope="module")
def wheel_dir(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sf")
    done = _build(_copy_repo(tmp), tmp / "wheels")
    if done.returncode != 0:
        pytest.fail("pip wheel failed:\n" + (done.stdout + done.stderr)[-1500:])
    unpacked = tmp / "unpacked"
    with zipfile.ZipFile(next((tmp / "wheels").glob("*.whl"))) as z:
        z.extractall(unpacked)
    return unpacked


def _isolated(wheel, code, cwd):
    """Run code in `python -I` that sees only the unpacked wheel."""
    return subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, %r); %s" % (str(wheel), code)],
                          capture_output=True, text=True, cwd=str(cwd), env={**os.environ})


def test_rates_found_from_the_packaged_plugin(tmp_path, wheel_dir):
    # TC-SF-01, TC-SF-02, TC-SF-03
    want = json.loads(REPO_RATES.read_text(encoding="utf-8"))["sites"]["nano4"]
    code = ("from abf_platform import su; import json; r = su.load_rates(); "
            "t = [{'cpus': 2, 'realtime': 1800000, 'queue': 'ngs92G'}, {'cpus': 1, 'realtime': 3600000, 'queue': 'ngs92G'}]; "
            "print(json.dumps({'path': str(su.RATES_PATH), 'nano4': r and r['sites']['nano4'], 'su': su.su_of_tasks(t, 'nano4', r)}))")
    done = _isolated(wheel_dir, code, tmp_path)
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout.strip().splitlines()[-1])
    assert got["nano4"] is not None and got["nano4"]["twd_per_su"] == want["twd_per_su"]
    path = got["path"].replace("\\", "/")
    assert path.endswith("abf_station/plugin/configs/sites/su_rates.json") and path.startswith(str(wheel_dir).replace("\\", "/"))
    s = got["su"]
    assert s["su"] == pytest.approx(2.0) and s["twd_nstc"] == pytest.approx(0.2) and s["twd_academic"] == pytest.approx(0.4)
    assert s["twd"]["industry"] == pytest.approx(0.74) and s["unknown_reasons"] == []


def test_packaged_copy_beats_the_repo_path(tmp_path, wheel_dir):
    # TC-SF-04: a different file at the repo path (two levels above su.py) must lose to the packaged one
    w = tmp_path / "w"
    shutil.copytree(wheel_dir, w)
    fake = tmp_path / "configs" / "sites"
    fake.mkdir(parents=True)
    data = json.loads(REPO_RATES.read_text(encoding="utf-8"))
    data["sites"]["nano4"]["twd_per_su"]["nstc"] = 999
    (fake / "su_rates.json").write_text(json.dumps(data), encoding="utf-8")
    done = _isolated(w, "from abf_platform import su; print(su.load_rates()['sites']['nano4']['twd_per_su']['nstc'])", tmp_path)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() != "999"


def test_checkout_still_uses_repo_configs():
    # TC-SF-05
    from abf_platform import su
    assert not (PLATFORM_DIR / "abf_station" / "plugin").exists()
    assert su.RATES_PATH == REPO_RATES
    rates = su.load_rates()
    assert rates is not None and {"taiwania3", "nchc", "nano4"} <= set(rates["sites"])


def test_no_rates_anywhere_is_unknown_without_a_path(tmp_path, wheel_dir):
    # TC-SF-06: no plugin configs in the wheel and no file at the repo path (nothing named configs/ above the unpacked wheel)
    root = tmp_path / "deep" / "er"
    root.mkdir(parents=True)
    w = root / "w"
    shutil.copytree(wheel_dir, w)
    shutil.rmtree(w / "abf_station" / "plugin" / "configs")
    code = ("from abf_platform import su; r = su.load_rates(); o = su.su_of_tasks([], 'nano4', r); "
            "import json; print(json.dumps({'r': r, 'o': o}))")
    done = _isolated(w, code, tmp_path)
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout.strip().splitlines()[-1])
    assert got["r"] is None and got["o"]["su"] is None
    assert "費率檔讀不到 (the rates file cannot be read)" in got["o"]["unknown_reasons"]
    for text in got["o"]["unknown_reasons"]:
        assert "/" not in text and "\\" not in text and "su_rates.json" not in text and str(tmp_path) not in text
