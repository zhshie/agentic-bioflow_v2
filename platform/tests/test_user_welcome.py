# Nothing existing: no mail or letter tool is wanted; these tests drive our own `abf-platform user welcome` against throwaway databases in tmp_path.
"""abf-platform user welcome: the letter with name, lab and cloud cap filled in. Test cases TC-001 ... TC-067 are named in the
comments (the verifier's list of this task). No network, no mail, no real data."""
import os
import re
import sqlite3
import subprocess
import sys

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT, pkg_env, run_cli

URL = "https://abf.example.org"
CLI_SRC = (PLATFORM_DIR / "abf_platform" / "cli.py").read_text(encoding="utf-8")
DOC = (REPO_ROOT / "docs" / "ONBOARDING.md").read_text(encoding="utf-8")


def _env(tmp_path):
    return pkg_env(ABF_PLATFORM_DB=tmp_path / "data" / "index.db")


def _add(env, name, lab="lab-x", cap=None):
    # set-up through the store (same file the command line reads); the command line's own `user add` is tested in TC-058/TC-059
    from abf_platform import store
    tokens = os.path.join(os.path.dirname(env["ABF_PLATFORM_DB"]), "tokens.db")
    os.makedirs(os.path.dirname(tokens), exist_ok=True)
    uid = store.create_user(tokens, name, lab)
    if cap is not None:
        store.set_cloud_cap(tokens, uid, float(cap))


def _welcome(env, name, *extra, url=URL):
    args = ["user", "welcome", name] + (["--platform-url", url] if url is not None else []) + list(extra)
    return run_cli(args, env=env)


def _letter(tmp_path, cap=20, name="alice", lab="lab-x", *extra):
    env = _env(tmp_path)
    _add(env, name, lab, cap)
    r = _welcome(env, name, *extra)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _tokens_db(tmp_path):
    return tmp_path / "data" / "tokens.db"


def _dump(tmp_path, tables=("users", "tokens", "cloud_caps")):
    con = sqlite3.connect(str(_tokens_db(tmp_path)))
    try:
        return {t: con.execute("SELECT * FROM %s ORDER BY 1" % t).fetchall() for t in tables}
    finally:
        con.close()


def _schema(tmp_path):
    con = sqlite3.connect(str(_tokens_db(tmp_path)))
    try:
        return con.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()
    finally:
        con.close()


# ---- US1 -------------------------------------------------------------------------------------------------------------

def test_the_letter_has_name_lab_and_address(tmp_path):
    # TC-001, TC-002, TC-003
    out = _letter(tmp_path)
    assert "alice" in out and "lab-x" in out and URL in out
    for p in ("<name>", "<lab>", "<platform-URL>"):
        assert p not in out
    assert "<operator>" in out


def test_operator_signs_the_letter(tmp_path):
    # TC-004, TC-005
    out = _letter(tmp_path, 20, "alice", "lab-x", "--operator", "Marvin")
    assert out.rstrip().endswith("Marvin") and "<operator>" not in out


def test_cap_in_dollars(tmp_path):
    # TC-006, TC-007, TC-008
    out = _letter(tmp_path)
    assert "US$20.00" in out and "cannot change" in out
    for bad in ("NT$", "台幣", "匯率", "TWD"):
        assert bad not in out


def test_cap_has_two_decimals(tmp_path):
    # TC-009
    assert "US$12.50" in _letter(tmp_path, 12.5)


def test_the_maintainers_manual_check(tmp_path):
    # TC-010
    out = _letter(tmp_path, 5, "test-colleague", "some-lab", "--operator", "Marvin")
    assert "test-colleague" in out and "US$5.00" in out and out.rstrip().endswith("Marvin")


def test_only_the_named_person(tmp_path):
    # TC-011
    env = _env(tmp_path)
    _add(env, "alice", "lab-x", 20)
    _add(env, "bob", "lab-y", 7)
    out = _welcome(env, "alice").stdout
    assert "lab-x" in out and "US$20.00" in out
    assert "bob" not in out and "lab-y" not in out and "US$7.00" not in out


# ---- US2 -------------------------------------------------------------------------------------------------------------

def test_no_cap_set_is_said_honestly(tmp_path):
    # TC-012 ... TC-017
    env = _env(tmp_path)
    _add(env, "carol", "x")
    r = _welcome(env, "carol")
    assert r.returncode == 0
    o = r.stdout
    assert "not set" in o and "cannot send runs to the cloud" in o
    assert "None" not in o and "US$0" not in o
    assert "NCHC runs are not affected" in o


def test_cap_zero_differs_from_not_set(tmp_path):
    # TC-018, TC-019, TC-020
    env = _env(tmp_path)
    _add(env, "carol", "x")
    _add(env, "bob", "x", 0)
    zero = _welcome(env, "bob").stdout.replace("bob", "NAME")
    none = _welcome(env, "carol").stdout.replace("carol", "NAME")
    assert "US$0.00" in zero and "cannot send runs to the cloud" in zero
    assert zero != none


# ---- US3 -------------------------------------------------------------------------------------------------------------

def test_the_letter_is_self_contained(tmp_path):
    # TC-021, TC-022, TC-023, TC-024, TC-067
    out = _letter(tmp_path)
    for k in ("temporary", "PAT", "password", "NCHC", "separately", "must change", "docs/INSTALL.md", "docs/ONBOARDING.md",
              "<your NSTC project>"):
        assert k in out, k
    for n in (2, 4, 5):
        assert re.search(r"(§|section )%d" % n, out)
    assert re.search(r"INSTALL\.md \(section 5\)", out) and re.search(r"ONBOARDING\.md \(section 2", out)


def test_cloud_users_are_not_asked_to_run_the_agent(tmp_path):
    # TC-025: the letter never mentions the station agent command at all
    out = _letter(tmp_path)
    assert "abf-station" not in out


def _template():
    m = re.search(r"## 3\. The welcome message.*?```text\n(.*?)\n```", DOC, re.S)
    return m.group(1)


def test_the_letter_is_the_document_template(tmp_path):
    # TC-026
    out = _letter(tmp_path)
    t = _template().replace("<platform-URL>", URL).replace("<name>", "alice").replace("<lab>", "lab-x")
    cap_line = re.search(r"(?m)^Cloud cap:.*$", t).group(0)
    t = t.replace(cap_line, "Cloud cap: your monthly cloud spending cap is US$20.00. It is set by me; you cannot change it. "
                            "Ask me if you need more.")
    assert out.rstrip("\n") == t


def test_no_secrets_in_the_letter(tmp_path):
    # TC-027, TC-028
    for sub, cap in (("a", 20), ("b", None)):
        out = _letter(tmp_path / sub, cap)
        assert not re.search(r"abf_pat_[A-Za-z0-9]{8,}", out)
        assert not re.search(r"mst1\d{5}", out) and not re.search(r"u9\d{7}", out)
        assert not re.search(r"(?<![A-Za-z0-9_-])(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{16}(?![A-Za-z0-9_-])", out)


def test_nothing_issued_or_changed(tmp_path):
    # TC-029, TC-047
    env = _env(tmp_path)
    _add(env, "alice", "lab-x", 20)
    before = _dump(tmp_path)
    assert _welcome(env, "alice").returncode == 0
    assert _dump(tmp_path) == before


def test_english_only(tmp_path):
    # TC-030
    assert not re.search(r"[一-鿿]", _letter(tmp_path))


# ---- US4 -------------------------------------------------------------------------------------------------------------

def test_unknown_person(tmp_path):
    # TC-031, TC-032, TC-033
    env = _env(tmp_path)
    _add(env, "alice")
    r = _welcome(env, "ghost")
    assert r.returncode != 0 and r.stdout == ""
    assert "沒有這個使用者" in r.stderr and "abf-platform user add" in r.stderr
    from abf_platform import store
    assert store.user_id_of(_tokens_db(tmp_path), "ghost") is None


def test_disabled_person(tmp_path):
    # TC-034
    env = _env(tmp_path)
    _add(env, "alice")
    con = sqlite3.connect(str(_tokens_db(tmp_path)))
    con.execute("UPDATE users SET disabled_at = 1 WHERE name = 'alice'")
    con.commit()
    con.close()
    r = _welcome(env, "alice")
    assert r.returncode != 0 and r.stdout == "" and "沒有這個使用者" in r.stderr and "abf-platform user add" in r.stderr


def test_address_is_required(tmp_path):
    # TC-035
    env = _env(tmp_path)
    _add(env, "alice")
    r = _welcome(env, "alice", url=None)
    assert r.returncode != 0 and "Hi alice" not in r.stdout


@pytest.mark.parametrize("bad", ["http://abf.example.org", "abf.example.org", "https://abf.example .org"])
def test_bad_address(tmp_path, bad):
    # TC-036, TC-037, TC-038
    env = _env(tmp_path)
    _add(env, "alice")
    r = _welcome(env, "alice", url=bad)
    assert r.returncode != 0 and "https" in r.stderr and r.stdout == ""


def test_http_on_this_machine_is_fine(tmp_path):
    # TC-039
    env = _env(tmp_path)
    _add(env, "alice")
    r = _welcome(env, "alice", url="http://localhost:8080")
    assert r.returncode == 0 and "http://localhost:8080" in r.stdout


def test_errors_are_plain(tmp_path):
    # TC-040
    env = _env(tmp_path)
    _add(env, "alice")
    existing = tmp_path / "exists.txt"
    existing.write_text("x")
    errs = [_welcome(env, "ghost"), _welcome(env, "alice", url="http://abf.example.org"),
            _welcome(env, "alice", "--out", str(existing)),
            _welcome(env, "alice", "--out", str(tmp_path / "nodir" / "x.txt"))]
    for r in errs:
        assert r.returncode != 0 and r.stderr.strip()
        for bad in ("Traceback", "sqlite", "SELECT", "tokens.db"):
            assert bad not in r.stderr, r.stderr


# ---- US5 -------------------------------------------------------------------------------------------------------------

def test_out_saves_the_letter(tmp_path):
    # TC-041, TC-042, TC-043
    env = _env(tmp_path)
    _add(env, "alice", "lab-x", 20)
    plain = _welcome(env, "alice").stdout
    out = tmp_path / "letter.txt"
    r = _welcome(env, "alice", "--out", str(out))
    assert r.returncode == 0
    assert out.read_bytes().decode("utf-8").rstrip("\n") == plain.rstrip("\n")
    assert len(r.stdout.strip().splitlines()) == 1 and str(out) in r.stdout
    if os.name == "posix":
        assert (out.stat().st_mode & 0o777) == 0o600


def test_out_never_overwrites(tmp_path):
    # TC-044
    env = _env(tmp_path)
    _add(env, "alice")
    out = tmp_path / "letter.txt"
    assert _welcome(env, "alice", "--out", str(out)).returncode == 0
    out.write_bytes(b"edited")
    r = _welcome(env, "alice", "--out", str(out))
    assert r.returncode != 0 and out.read_bytes() == b"edited"


def test_out_into_missing_folder(tmp_path):
    # TC-045
    env = _env(tmp_path)
    _add(env, "alice")
    r = _welcome(env, "alice", "--out", str(tmp_path / "nodir" / "x.txt"))
    assert r.returncode != 0 and r.stderr.strip() and not (tmp_path / "nodir").exists()


def test_bad_address_creates_no_file(tmp_path):
    # TC-046
    env = _env(tmp_path)
    _add(env, "alice")
    x = tmp_path / "x.txt"
    r = _welcome(env, "alice", "--out", str(x), url="http://abf.example.org")
    assert r.returncode != 0 and not x.exists()


# ---- US6 -------------------------------------------------------------------------------------------------------------

def test_schema_unchanged(tmp_path):
    # TC-048
    env = _env(tmp_path)
    _add(env, "alice")
    before = _schema(tmp_path)
    assert _welcome(env, "alice").returncode == 0
    assert _schema(tmp_path) == before


def test_no_network_no_mail(tmp_path):
    # TC-049
    env = _env(tmp_path)
    _add(env, "alice")
    code = ("import socket, smtplib, sys\n"
            "def boom(*a, **k): raise RuntimeError('network or mail used')\n"
            "socket.socket = boom\nsmtplib.SMTP = boom\nsmtplib.SMTP_SSL = boom\n"
            "from abf_platform.cli import main\n"
            "sys.exit(main(['user', 'welcome', 'alice', '--platform-url', %r]))\n" % URL)
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert "alice" in r.stdout


def _func_source(src, name):
    m = re.search(r"(?ms)^def %s\(.*?(?=^def |\Z)" % name, src)
    return m.group(0)


def test_no_sending_imports():
    # TC-050
    welcome_src = (PLATFORM_DIR / "abf_platform" / "welcome.py").read_text(encoding="utf-8")
    body = welcome_src + _func_source(CLI_SRC, "cmd_user_welcome")
    for bad in ("smtplib", "urllib", "http.client", "subprocess", "socket"):
        assert bad not in body, bad


def test_no_files_added(tmp_path):
    # TC-051
    env = _env(tmp_path)
    _add(env, "alice")

    def names():
        return sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    before = names()
    assert _welcome(env, "alice").returncode == 0
    assert _welcome(env, "ghost").returncode != 0
    assert names() == before


def test_one_action_one_function():
    # TC-052
    assert sorted(re.findall(r'usub\.add_parser\("([^"]+)"', CLI_SRC)) == ["add", "cloud-cap", "passwd", "welcome"]
    welcome_src = (PLATFORM_DIR / "abf_platform" / "welcome.py").read_text(encoding="utf-8")
    assert "def welcome_text(" in welcome_src and "welcome.welcome_text(" in _func_source(CLI_SRC, "cmd_user_welcome")
    assert "Your account on the platform is ready" in welcome_src and "Your account on the platform" not in CLI_SRC


# ---- US7 -------------------------------------------------------------------------------------------------------------

def test_help_text():
    # TC-053, TC-054
    r = run_cli(["user", "welcome", "--help"])
    assert r.returncode == 0
    h = " ".join(r.stdout.split())
    for k in ("--platform-url", "--operator", "--out", "prints only", "sends nothing"):
        assert k in h, k


def test_docstring_lists_welcome():
    # TC-055
    assert "welcome" in CLI_SRC.splitlines()[1]


def test_the_doc_points_at_the_command():
    # TC-056, TC-057
    sec2 = DOC.split("## 2.")[1].split("\n## 3.")[0]
    sec3 = DOC.split("## 3.")[1].split("\n## 4.")[0]
    for s in (sec2, sec3):
        assert re.search(r"abf-platform user welcome <name> --platform-url", s)
    assert len(re.findall(r"(?m)^## ", DOC)) == 5
    assert len(re.findall(r"(?m)^```text$", sec3)) == 1
    for p in ("<platform-URL>", "<name>", "<lab>", "<operator>"):
        assert p in sec3


def test_user_add_output_unchanged(tmp_path):
    # TC-058, TC-059
    env = _env(tmp_path)
    r = run_cli(["user", "add", "alice", "--lab", "lab-x", "--cloud-cap-usd", "20"], env=env)
    assert "added user alice (lab lab-x)" in r.stdout
    assert "issue a token with: abf-platform pat new --user alice" in r.stdout
    assert "Hi alice" not in r.stdout and "Your account on the platform is ready" not in r.stdout
    assert "welcome" not in r.stdout.lower()


def test_cloud_cap_message_unchanged(tmp_path):
    # TC-060
    env = _env(tmp_path)
    _add(env, "alice")
    r = run_cli(["user", "cloud-cap", "alice", "30"], env=env)
    assert "monthly cloud cap of alice is now US$30.00 (每月雲端費用上限)" in r.stdout


def test_only_scoped_files_changed():
    # TC-063: only where origin/v3 is this branch's real base (a few commits behind HEAD); elsewhere the verifier reads the diff
    def git(*a):
        return subprocess.run(["git"] + list(a), cwd=str(REPO_ROOT), capture_output=True, text=True)
    base = git("merge-base", "origin/v3", "HEAD")
    if base.returncode != 0 or not base.stdout.strip():
        pytest.skip("no origin/v3")
    count = git("rev-list", "--count", base.stdout.strip() + "..HEAD")
    if count.returncode != 0 or int(count.stdout.strip() or 99) > 15:
        pytest.skip("origin/v3 is not this branch's base")
    r = git("diff", "--name-only", base.stdout.strip() + "..HEAD")
    allowed = {"platform/tests/test_user_welcome.py", "platform/abf_platform/cli.py", "platform/abf_platform/welcome.py",
               "docs/ONBOARDING.md"}
    extra = [f for f in r.stdout.split() if f not in allowed and not f.startswith("specs/account-welcome-cli/")]
    assert extra == [], extra
