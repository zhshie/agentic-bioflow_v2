#!/usr/bin/env python3
# Nothing existing: no tool checks our own downstream catalogue for schema errors and for reviews older than 12 months.
"""Check platform/abf_platform/data/downstream-methods.json.

Exit 0: the schema is fine and no entry has aged. Exit 1: some entry's effective grade is lower than its declared grade (not reviewed for
more than 365 days); each is printed with its id, review date and age. Exit 2: the schema is broken; every violation is printed.
Standard library only; nothing is written, nothing is fetched.
  --path FILE        catalogue to read (default: the packaged one)
  --today YYYY-MM-DD the date to count from (default: today)
"""
import argparse
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "platform" / "abf_platform" / "downstream_catalog.py"


def _module():
    spec = importlib.util.spec_from_file_location("downstream_catalog", CATALOG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check the downstream method catalogue.")
    ap.add_argument("--path")
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    dc = _module()
    path = Path(a.path) if a.path else dc.DEFAULT_PATH
    try:
        today = date.fromisoformat(a.today) if a.today else date.today()
    except ValueError:
        print("--today must be written YYYY-MM-DD")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print("cannot read %s as JSON: %s" % (path.name, err))
        return 2
    problems = dc.validate(data)
    if problems:
        print("schema violations (%d):" % len(problems))
        for p in problems:
            print("  " + p)
        return 2
    aged = []
    for e in data["entries"]:
        eff = dc.effective_grade(e, today)
        if eff != e["grade"]:
            aged.append("  %s: reviewed %s, %d days ago, %s -> %s" % (e["id"], e["reviewed"], dc.age_days(e, today), e["grade"], eff))
    if aged:
        print("entries past 12 months since review (%d):" % len(aged))
        print("\n".join(aged))
        return 1
    print("ok: %d entries, none past 12 months" % len(data["entries"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
