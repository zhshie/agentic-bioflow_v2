# Nothing existing: tests that su.py treats NaN and Infinity in the rates file as unusable (task cb-D1); the cases are ours.
"""su finite: json.load accepts the literals NaN and Infinity, so a rates file can carry them. su.py must treat such a value like a
missing one (None with a reason), never a NaN/inf SU or money value and never a 0 dollar value. Finite rates behave as before."""
import math

import pytest

from helpers import REPO_ROOT

H = 3600000
BAD = ["NaN", "Infinity", "-Infinity"]


def su_mod():
    from abf_platform import su
    return su


def rates_file(tmp_path, body):
    p = tmp_path / "rates.json"
    p.write_text(body, encoding="utf-8")
    return p


def tasks():
    return [{"name": "A", "queue": "p1", "cpus": 4, "realtime": 2 * H}]


def body(nstc="0.08", academic="0.24", factor="1.5", usd="32", site_per_su=None):
    site = '"partitions": {"p1": {"factor": %s}}' % factor
    if site_per_su is not None:
        site += ', "twd_per_su": %s' % site_per_su
    return ('{"nstc_twd_per_su": %s, "academic_twd_per_su": %s, "su_plan_type": "nstc", '
            '"usd_twd": {"rate": %s, "as_of": "2026-11-01"}, "sites": {"s": {%s}}}' % (nstc, academic, usd, site))


@pytest.mark.parametrize("v", [float("nan"), float("inf"), float("-inf")])
def test_number_rejects_non_finite(v):
    assert su_mod()._number(v) is False


@pytest.mark.parametrize("v", [0, 1, -3, 0.5, 1e300])
def test_number_keeps_finite(v):
    assert su_mod()._number(v) is True


@pytest.mark.parametrize("v", [True, False, "1", None, [1]])
def test_number_keeps_rejecting_non_numbers(v):
    assert su_mod()._number(v) is False


@pytest.mark.parametrize("lit", BAD)
def test_non_finite_money_rate_gives_none_not_nan(tmp_path, lit):
    su = su_mod()
    r = su.load_rates(rates_file(tmp_path, body(nstc=lit, academic=lit)))
    out = su.su_of_tasks(tasks(), "s", r)
    assert out["su"] == 12 and out["unknown_reasons"] == []
    assert out["twd_nstc"] is None and out["twd_academic"] is None


@pytest.mark.parametrize("lit", BAD)
def test_non_finite_site_price_gives_none(tmp_path, lit):
    su = su_mod()
    per_su = '{"nstc": %s, "academic": 0.24, "industry": %s}' % (lit, lit)
    r = su.load_rates(rates_file(tmp_path, body(site_per_su=per_su)))
    out = su.su_of_tasks(tasks(), "s", r)
    assert out["su"] == 12
    assert out["twd_nstc"] is None and out["twd"]["nstc"] is None and out["twd"]["industry"] is None
    assert out["twd_academic"] == pytest.approx(12 * 0.24)


@pytest.mark.parametrize("lit", BAD)
def test_non_finite_factor_is_unknown(tmp_path, lit):
    su = su_mod()
    r = su.load_rates(rates_file(tmp_path, body(factor=lit)))
    out = su.su_of_tasks(tasks(), "s", r)
    assert out["su"] is None and out["twd_nstc"] is None
    assert out["unknown_reasons"] and "p1" in out["unknown_reasons"][0]


@pytest.mark.parametrize("lit", [float("nan"), float("inf")])
@pytest.mark.parametrize("field", ["cpus", "realtime"])
def test_non_finite_task_value_is_unknown(tmp_path, lit, field):
    su = su_mod()
    r = su.load_rates(rates_file(tmp_path, body()))
    t = tasks()
    t[0][field] = lit
    out = su.su_of_tasks(t, "s", r)
    assert out["su"] is None
    assert out["unknown_reasons"]


@pytest.mark.parametrize("lit", BAD)
def test_non_finite_usd_rate_is_none(tmp_path, lit):
    su = su_mod()
    r = su.load_rates(rates_file(tmp_path, body(usd=lit)))
    assert su.usd_rate(r)[0] is None
    assert su.usd_of(10, "s", r) is None     # not 10 * price / inf == 0


@pytest.mark.parametrize("lit", BAD)
def test_non_finite_price_or_su_gives_no_dollars(tmp_path, lit):
    su = su_mod()
    r = su.load_rates(rates_file(tmp_path, body(nstc=lit)))
    assert su.usd_of(10, "s", r) is None
    good = su.load_rates(rates_file(tmp_path, body()))
    assert su.usd_of(float(lit), "s", good) is None


def test_finite_rates_unchanged(tmp_path):
    su = su_mod()
    r = su.load_rates(rates_file(tmp_path, body()))
    out = su.su_of_tasks(tasks(), "s", r)
    assert out["su"] == 12
    assert out["twd_nstc"] == pytest.approx(12 * 0.08) and out["twd_academic"] == pytest.approx(12 * 0.24)
    assert su.usd_rate(r) == (32, "2026-11-01")
    assert su.usd_of(10, "s", r) == pytest.approx(10 * 0.08 / 32)


def test_load_rates_default_is_still_the_su_file(monkeypatch, tmp_path):
    su = su_mod()
    real = su.load_rates()
    assert isinstance(real, dict) and "sites" in real and real == su.load_rates(REPO_ROOT / "configs" / "sites" / "su_rates.json")
    monkeypatch.setattr(su, "RATES_PATH", tmp_path / "missing.json")
    assert su.load_rates() is None
    assert su.load_rates(tmp_path / "also-missing.json") is None
    bad = rates_file(tmp_path, "[1, 2]")
    assert su.load_rates(bad) is None


def test_the_finite_check_is_the_one_in_cloud_cost():
    from abf_platform import cloud_cost
    su = su_mod()
    for v in (0, 1, -1.5, True, None, "x", math.nan, math.inf, -math.inf):
        assert su._number(v) == cloud_cost._number(v)


def test_importing_cloud_cost_first_still_works():
    import subprocess
    import sys
    from helpers import PLATFORM_DIR
    for first in ("cloud_cost", "su"):
        done = subprocess.run([sys.executable, "-c", "from abf_platform import %s, su, cloud_cost; su.load_rates(); su._number(1)" % first],
                              cwd=str(PLATFORM_DIR), capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr
