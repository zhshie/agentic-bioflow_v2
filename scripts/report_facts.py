#!/bin/bash
# The facts of a project's runs as an editable report.md, filled only from files.
#
#   report_facts.py --provenance <provenance.json> --methods <methods.md> --out <file>
#
# Not Jinja2 or Quarto templating: both would add a dependency to fill five
# short sections from two files that already exist, and this must run on a
# machine that has only a bare python3 (standard library only, like
# collect_provenance.py).
#
# Nothing here is composed from memory or by a model (constitution 9): every
# value is read from provenance.json (scripts/collect_provenance.py) or copied
# verbatim from methods.md (scripts/methods_text.py), and a value those files
# do not carry is written as "not recorded", never guessed. The Interpretation
# section is left empty on purpose; it is for the person to write.
#
# It reads what build_package.sh already produced and does not re-run either
# script. The output is deterministic - no timestamps, no host names, run order
# as in provenance.json - so two builds of the same project are byte-identical,
# which is how build_package.sh tells an edited report.md from an untouched one.
''''true
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
if [ -f "$HERE/require_python.sh" ]; then
    . "$HERE/require_python.sh"
    require_python || exit 1
fi
exec python3 "$0" "$@"
'''

import argparse
import json
import os
import sys

NR = "not recorded"


def pipeline_and_version(run):
    wf = run.get("workflow")
    if not isinstance(wf, dict):
        return NR, NR
    for name, version in wf.items():
        if str(name).lower() == "nextflow":
            continue
        return str(name), (str(version) if version not in (None, "") else NR)
    return NR, NR


def text(value):
    if value is None or value == "" or isinstance(value, (dict, list)):
        return NR
    return str(value)


def run_name(run):
    d = run.get("run_dir")
    if not d:
        return NR
    return os.path.basename(str(d).rstrip("/\\")) or NR


def input_name(run):
    pv = run.get("params_values")
    if not isinstance(pv, dict) or not isinstance(pv.get("input"), str) or not pv["input"]:
        return NR
    return os.path.basename(pv["input"].replace("\\", "/").rstrip("/")) or NR


def find_multiqc(run):
    """An existing report file, or None. A recorded path that is gone is not
    replaced by a search: the record is what it is."""
    if "quality_report" in run:
        q = run.get("quality_report")
        return q if isinstance(q, str) and os.path.isfile(q) else None
    results = run.get("results")
    if not isinstance(results, str) or not os.path.isdir(results):
        return None
    for root, dirs, files in os.walk(results):
        dirs[:] = sorted(d for d in dirs if d not in ("work", ".nextflow"))
        if "multiqc_report.html" in files:
            return os.path.join(root, "multiqc_report.html")
    return None


def main(argv=None):
    p = argparse.ArgumentParser(prog="report_facts.py")
    p.add_argument("--provenance", required=True)
    p.add_argument("--methods", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)

    with open(a.provenance, encoding="utf-8") as fh:
        runs = json.load(fh).get("runs") or []
    try:
        with open(a.methods, encoding="utf-8") as fh:
            methods = fh.read()
    except OSError:
        methods = NR + "\n"
    base = os.path.dirname(os.path.abspath(a.out))

    L = ["## Runs", ""]
    for run in runs:
        pipe, ver = pipeline_and_version(run)
        L += ["### %s" % run_name(run), "",
              "- pipeline: %s" % pipe,
              "- version: %s" % ver,
              "- run name: %s" % run_name(run),
              "- run id: %s" % text(run.get("platform_run_id")),
              "- start: %s" % text(run.get("start")),
              "- end: %s" % text(run.get("end")),
              "- status: %s" % text(run.get("status")), ""]
    L += ["## Inputs", ""]
    for run in runs:
        L.append("- %s: samplesheet %s" % (run_name(run), input_name(run)))
    L += ["", "## Methods", "", methods.rstrip("\n"), "", "## Quality control", ""]
    for run in runs:
        q = find_multiqc(run)
        if q:
            rel = os.path.relpath(q, base).replace(os.sep, "/")
            tail = " (outside this package)" if rel.startswith("../") else ""
            L.append("- %s: [MultiQC report](%s)%s" % (run_name(run), rel, tail))
        else:
            L.append("- %s: MultiQC report not found" % run_name(run))
    L += ["", "## Interpretation", "",
          "This section is empty on purpose: write your own reading of the results here.", ""]
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
