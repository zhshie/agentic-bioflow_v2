# Nothing existing: pip-audit only scans the pins, and no other test reads the certifi line or the empty ignore list; this guard is ours.
"""certifi must be pinned at or above the PYSEC-2026-4320 fix; the audit ignore list stays empty."""
import re
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent
FIXED = (2026, 10, 18)


def _version_tuple(text):
    return tuple(int(p) for p in text.strip().split("."))


def _certifi_versions():
    out = []
    for line in (PLATFORM_DIR / "constraints.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^certifi(?:==|>=)([0-9][0-9.]*)\s*(?:#.*)?$", line.strip())
        if m:
            out.append(m.group(1))
    return out


def test_constraints_pins_certifi_at_or_above_fix():
    # TC-001, TC-002, TC-004
    found = _certifi_versions()
    assert len(found) == 1, found
    assert _version_tuple(found[0]) >= FIXED, found[0]


def test_certifi_version_parser_compares_numerically():
    # TC-003
    assert _version_tuple("2026.7.22") < _version_tuple("2026.10.18")
    assert "2026.7.22" > "2026.10.18"  # the string order is the wrong way round


def test_pip_audit_ignore_stays_empty():
    # TC-005
    lines = (PLATFORM_DIR / "pip-audit-ignore.txt").read_text(encoding="utf-8").splitlines()
    assert [l for l in lines if l.strip() and not l.strip().startswith("#")] == []
