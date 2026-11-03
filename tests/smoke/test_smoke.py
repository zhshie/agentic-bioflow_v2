"""Read-only post-deploy smoke probes (smoke-suite-b).

The functions decorated with @smoke are the real probes: they run only when
SMOKE_BASE_URL is set.  The other tests prove the probes against a throw-away
fake site on 127.0.0.1 and never leave the machine.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from smoke_support import (
    MARKERS_OPT, CheckFailed, CheckSkipped, FakeSite, base_url, check_404_headers,
    check_home, check_mcp_resource_metadata, check_mcp_unauthenticated,
    check_oauth_metadata, check_security_headers, check_web_alive, run_all_checks,
    run_check, smoke,
)

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- real probes
@smoke
def test_home_redirects_to_login_then_200():
    run_check(check_home, base_url())


@smoke
def test_login_page_alive():
    run_check(check_web_alive, base_url())


@smoke
def test_oauth_metadata_json():
    run_check(check_oauth_metadata, base_url())


@smoke
def test_mcp_unauthenticated_is_401_with_bearer():
    run_check(check_mcp_unauthenticated, base_url())


@smoke
def test_mcp_resource_metadata():
    run_check(check_mcp_resource_metadata, base_url())


@smoke
def test_security_headers_present():
    run_check(check_security_headers, base_url())


@smoke
def test_404_carries_csp():
    run_check(check_404_headers, base_url())


# ------------------------------------------------- the probes against a fake site
def _ok(check, **opts):
    with FakeSite(**opts) as site:
        check(site.base)


def _fails(check, **opts):
    with FakeSite(**opts) as site:
        with pytest.raises(CheckFailed) as exc:
            check(site.base)
    return str(exc.value)


# TC-004
@pytest.mark.parametrize("home", ["login", "welcome", "ok"])
def test_tc004_home_three_shapes(home):
    _ok(check_home, home=home)


# TC-004
def test_tc004_home_does_not_follow_and_rejects_other_location():
    _fails(check_home, home="elsewhere")
    with FakeSite(home="login") as site:
        check_home(site.base)
        assert [p for m, p, h in site.requests if m == "GET"][0] == "/"


# TC-005
def test_tc005_web_and_oauth_alive_only_known_paths():
    with FakeSite() as site:
        check_web_alive(site.base)
        check_oauth_metadata(site.base)
        paths = {p for _m, p, _h in site.requests}
    assert paths == {"/login", "/.well-known/oauth-authorization-server"}


# TC-005
def test_tc005_failure_names_item_and_status_without_body():
    msg = _fails(check_web_alive, login_status=503, secrets=True)
    assert "503" in msg and "/login" in msg
    assert "SECRET123" not in msg
    msg = _fails(check_oauth_metadata, oauth_status=500)
    assert "500" in msg


# TC-006
def test_tc006_mcp_unauthenticated_request_shape():
    with FakeSite() as site:
        check_mcp_unauthenticated(site.base)
        posts = [r for r in site.requests if r[0] == "POST"]
    assert len(posts) == 1
    _method, path, headers = posts[0]
    assert path == "/mcp"
    assert "authorization" not in {k.lower() for k in headers}
    assert site.post_bodies == [b"{}"]


# TC-007
def test_tc007_resource_metadata_present():
    _ok(check_mcp_resource_metadata, resource_meta=True)


# TC-007
def test_tc007_resource_metadata_absent_is_skip_not_fail():
    with FakeSite(resource_meta=False) as site:
        with pytest.raises(CheckSkipped) as exc:
            check_mcp_resource_metadata(site.base)
    assert "public-url" in str(exc.value)
    with FakeSite(resource_meta=False) as site:
        failures = run_all_checks(site.base)
    assert failures == []


# TC-008
def test_tc008_headers_ok():
    _ok(check_security_headers)


# TC-008
@pytest.mark.parametrize("drop", ["csp", "xfo", "nosniff", "nostore", "csp_weak"])
def test_tc008_each_header_is_required(drop):
    assert _fails(check_security_headers, drop=drop)


# TC-009
def test_tc009_404_with_csp_ok_and_failures():
    _ok(check_404_headers)
    _fails(check_404_headers, not_found_status=200)
    _fails(check_404_headers, drop="csp")


# TC-010
def test_tc010_lowercase_header_names():
    with FakeSite(lower=True) as site:
        assert run_all_checks(site.base) == []


# TC-011
def test_tc011_bad_sites_fail_the_right_check():
    msg = _fails(check_security_headers, drop="csp")
    assert "content-security-policy" in msg.lower()
    msg = _fails(check_mcp_unauthenticated, mcp_status=200)
    assert "401" in msg and "200" in msg
    msg = _fails(check_home, home="500")
    assert "500" in msg


# TC-012
def test_tc012_only_get_and_one_unauthenticated_post(monkeypatch):
    monkeypatch.setenv("SMOKE_TOKEN", "TOKEN456")
    with FakeSite() as site:
        assert run_all_checks(site.base) == []
        reqs = list(site.requests)
    methods = [m for m, _p, _h in reqs]
    assert set(methods) <= {"GET", "POST"}
    assert [p for m, p, _h in reqs if m == "POST"] == ["/mcp"]
    assert methods.count("POST") == 1
    for _m, _p, headers in reqs:
        assert "authorization" not in {k.lower() for k in headers}
        assert "TOKEN456" not in " ".join(headers.values())


# ----------------------------------------------------------- child-run helpers
def _child(site_base, extra_env=None):
    env = dict(os.environ)
    env["SMOKE_BASE_URL"] = site_base
    env.update(extra_env or {})
    cmd = [sys.executable, "-m", "pytest", "-o", MARKERS_OPT, "-m", "smoke",
           "tests/smoke", "-rs", "-p", "no:cacheprovider"]
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


# TC-013
def test_tc013_output_has_no_secrets():
    with FakeSite(drop="csp", secrets=True) as site:
        proc = _child(site.base + "/?k=QUERY789", {"SMOKE_TOKEN": "TOKEN456"})
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "failed" in out
    for secret in ("SECRET123", "QUERY789", "TOKEN456"):
        assert secret not in out


# TC-013 (green counterpart: the marker-selected probes pass against the fake site)
def test_tc013_green_child_run_passes():
    with FakeSite(secrets=True) as site:
        proc = _child(site.base)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out[-600:]
    assert "passed" in out
    assert "SECRET123" not in out


# TC-018 (the other static scans are the tests/*.sh files themselves)
def test_tc018_smoke_sh_parses():
    proc = subprocess.run(["bash", "-n", str(ROOT / "scripts" / "smoke.sh")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
