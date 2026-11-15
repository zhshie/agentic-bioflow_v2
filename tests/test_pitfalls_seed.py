"""Guards the three pitfalls 62-64 appended to docs/PITFALLS.md (task pitfalls-seed).

Standard library + pytest only; no network.
"""
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "PITFALLS.md"
HEAD_RE = re.compile(r"^\*\*(\d+[a-z0-9]*)\.( |\*\*)")
FIELDS = ["Symptom:", "Root cause:", "Check:", "Touches:"]
# sha256 of the first 2572 lines of docs/PITFALLS.md at origin/v3 aebb7a59
BASE_LINES = 2572
BASE_SHA = "4cd10ec26e3a231a5687660d3d89934fff35ba630492599009fd8274b438e729"


def _lines():
    return DOC.read_bytes().decode("utf-8").replace("\r\n", "\n").split("\n")


def _entries():
    out, cur = {}, None
    for ln in _lines():
        m = HEAD_RE.match(ln)
        if m:
            cur = m.group(1)
            out[cur] = [ln]
        elif ln.startswith("## "):
            cur = None
        elif cur:
            out[cur].append(ln)
    return out


def _entry(n):
    e = _entries().get(str(n))
    assert e is not None, f"entry {n} missing from docs/PITFALLS.md"
    while e and not e[-1].strip():
        e = e[:-1]
    return e


def _field(e, label):
    return [i for i, ln in enumerate(e) if ln.startswith(label)]


def test_t1_no_root_pitfalls_file():  # TC-001, TC-060
    assert DOC.is_file()
    assert not (ROOT / "PITFALLS.md").exists()
    for n in (62, 63, 64):
        _entry(n)


def test_t2_entries_62_to_64_have_four_fields():  # TC-004
    for n in (62, 63, 64):
        e = _entry(n)
        idx = []
        for f in FIELDS:
            hits = _field(e, f)
            assert len(hits) == 1, f"{n}: {f} count {len(hits)}"
            assert e[hits[0]][len(f):].strip(), f"{n}: {f} empty"
            idx.append(hits[0])
        assert idx == sorted(idx), f"{n}: out of order"
        assert idx[3] - idx[0] == 3, f"{n}: not consecutive"
        assert idx[3] == len(e) - 1, f"{n}: fields not at entry end"
        check = e[idx[2]][len("Check:"):].strip()
        assert check.startswith("none automated:") or re.search(r"`[^`]+`", check)


def _touches(n):
    e = _entry(n)
    t = e[_field(e, "Touches:")[0]][len("Touches:"):]
    return [x.strip() for x in t.split(",")], e


def test_t3_titles_and_touches_keywords():  # TC-010, 020, 022, 030, 031, 032
    t62, e62 = _touches(62)
    assert "run_all" in e62[0] and "Git Bash" in e62[0]
    for k in ("tests/run_all.sh", "Git Bash", "WSL", "MSYS", "--allow-msys"):
        assert k in t62, k
    body62 = "\n".join(e62[:-4])
    assert "16b" in body62 and "20c" in body62
    assert "`tests/run_all_test.sh`" in "\n".join(e62)

    t63, e63 = _touches(63)
    assert "wsl.exe" in e63[0] and "non-ASCII" in e63[0]
    for k in ("wsl.exe", "--cd", "Failed to translate", "non-ASCII", "tests/run_all.sh", "$HOME"):
        assert k in t63, k
    assert "16i" in "\n".join(e63[:3])
    assert "16i" in "\n".join(e63) and "none automated:" in "\n".join(e63[-4:])

    t64, e64 = _touches(64)
    assert "synced drive" in e64[0] or "two runs" in e64[0].lower()
    for k in ("tests/run_all.sh", "synced drive (e.g. Google Drive)", "worktree", "temporary copies"):
        assert k in t64, k
    body64 = "\n".join(e64[:-4])
    for m in re.finditer("Google Drive", body64):
        assert body64[max(0, m.start() - 6):m.start()] == "(e.g. ", "Google Drive must be marked e.g."
    for e in (e62, e63, e64):
        txt = "\n".join(e)
        assert "other_docs_untouched" not in txt and "test_tc047" not in txt


def test_t4_existing_format_test_still_passes():  # TC-005, TC-071
    bash = shutil.which("bash")
    assert bash, "bash not found: cannot run tests/pitfalls_format_test.sh (this must fail, not skip)"
    r = subprocess.run([bash, "tests/pitfalls_format_test.sh"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "entry count 100" in r.stdout


def test_t5_numbering_continues():  # TC-003, TC-006
    lines = _lines()
    assert len(lines) >= BASE_LINES
    head = "\n".join(lines[:BASE_LINES]) + "\n"
    assert hashlib.sha256(head.encode("utf-8")).hexdigest() == BASE_SHA
    assert DOC.read_bytes().endswith(b"\n")
    heads = [HEAD_RE.match(ln).group(1) for ln in lines if HEAD_RE.match(ln)]
    assert heads[-4:] == ["61", "62", "63", "64"], heads[-4:]
    assert len(heads) == 100
    assert not any(ln.startswith("## ") for ln in lines[BASE_LINES:])


def test_t6_evidence_paths_exist():  # TC-041
    for n in (62, 63, 64):
        txt = "\n".join(_entry(n))
        for p in re.findall(r"`([^`\n]+)`", txt):
            if "<" in p or " " in p:
                continue
            if "/" in p or p.endswith((".md", ".sh", ".py")):
                if p.startswith("-") or p.startswith("~") or p.startswith("/mnt"):
                    continue
                assert (ROOT / p).exists(), f"{n}: {p} does not exist"
