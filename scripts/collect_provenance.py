#!/bin/bash
# What a run can prove about itself, gathered by shape rather than by name.
#
#   collect_provenance.py [--json] <results-dir> [<results-dir> ...]
#
# One project's write-up commonly draws on several runs, so this takes several
# and reports them as a list. Every field is read from the run's own output;
# nothing here remembers what any pipeline is supposed to write.
#
# The names are not stable, which is the whole reason this is not a lookup.
# Measured across three real runs on one cluster:
#
#   software_versions.yml                          one pipeline
#   nf_core_<pipeline>_software_mqc_versions.yml   another, newer template
#   collated_versions.yml                          a third, which emits both
#
# and the quality report is nested under an aligner's name in one of them and
# at the top in another, with its data directory called multiqc_data in one
# and multiqc_report_data in the other. So: find files by what they contain,
# not by where they should be.
#
# Retried runs are the other trap. A run that failed and resumed leaves the
# first attempt's report and a 154-byte trace lying beside the real ones, all
# timestamped in the filename. Taking the first match sorts them alphabetically
# and picks the corpse. Take the newest, always, and say how many were passed
# over so a reader can tell a retry happened at all.
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
import re
import sys

# Language runtimes and shell utilities. These are excluded from "tools that
# need citing" - not because they do not matter but because no pipeline's
# citation file lists them and no journal expects sed in a reference list.
#
# Is this the per-pipeline table this project killed in v1? No, and the
# difference is testable: that table listed what one pipeline produces, so it
# went stale on the next upstream release and left an uncatalogued pipeline
# unusable. This lists language runtimes, which are the same everywhere and
# belong to no pipeline. tests/collect_provenance_test.sh asserts that nothing
# here is a pipeline tool.
NOT_CITED = {"python", "r", "sed", "awk", "perl", "bash", "pandas", "numpy",
             "yaml", "nextflow", "gawk", "grep", "coreutils"}

TIMESTAMPED = re.compile(r"^(execution_report|execution_trace|execution_timeline"
                         r"|params|pipeline_dag)_(.+?)\.(html|txt|json)$")


def newest(paths):
    """The newest of a timestamped set, and how many were passed over.

    By mtime rather than by parsing the stamp out of the name: the format is
    the pipeline's to choose and has already been seen to differ, while the
    filesystem's answer is the same everywhere.
    """
    if not paths:
        return None, 0
    ranked = sorted(paths, key=lambda p: os.path.getmtime(p), reverse=True)
    return ranked[0], len(ranked) - 1


def read_yaml_ish(path):
    """Two-level `key:` / `  sub: value` YAML, which is all these files are.

    Deliberately not a YAML parser: the dependency is not installed on the
    machines this has to run on, and the shape here is fixed and trivial.
    Anything it cannot read is reported as unreadable rather than guessed at.
    """
    out, section = {}, None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if not line[0].isspace():
                    section = line.split(":", 1)[0].strip()
                    out.setdefault(section, {})
                elif section is not None and ":" in line:
                    k, _, v = line.strip().partition(":")
                    out[section][k.strip()] = v.strip().strip("'\"")
    except OSError as exc:
        return {}, str(exc)
    return out, None


def find_versions(pipeline_info):
    """The versions file, whatever this pipeline's template chose to call it.

    Three names measured, and rather than list them, take any .yml in
    pipeline_info whose top level looks like process names carrying tool
    versions. A fourth name costs nothing.
    """
    best, best_n = None, -1
    for name in sorted(os.listdir(pipeline_info)):
        if not name.endswith((".yml", ".yaml")):
            continue
        parsed, err = read_yaml_ish(os.path.join(pipeline_info, name))
        if err:
            continue
        n = sum(1 for v in parsed.values() if isinstance(v, dict) and v)
        if n > best_n:
            best, best_n = os.path.join(pipeline_info, name), n
    return best


def tools_from_versions(parsed):
    """tool -> version, flattened, with the Workflow block pulled out.

    The Workflow block is the pipeline and Nextflow themselves; every other
    block is one process and the tools it ran.
    """
    tools, workflow = {}, {}
    for section, entries in parsed.items():
        if not isinstance(entries, dict):
            continue
        target = workflow if section.lower() == "workflow" else tools
        for tool, version in entries.items():
            target.setdefault(tool, version)
    return tools, workflow


def find_quality_report(results):
    """The rendered quality report and its data directory, wherever they landed.

    Located by name-shape within the tree rather than at a fixed path: one
    pipeline puts it at the top, another nests it under the aligner it used,
    and the data directory beside it is called multiqc_data in one and
    multiqc_report_data in the other.
    """
    report, citations = None, None
    for root, dirs, files in os.walk(results):
        dirs[:] = [d for d in dirs if d not in ("work", ".nextflow")]
        for name in files:
            full = os.path.join(root, name)
            if name.endswith("_report.html") and report is None:
                report = full
            elif name.endswith("_citations.txt") and citations is None:
                citations = full
    return report, citations


def dois_from_citations(path):
    """The DOIs a quality report recorded, in file order.

    These cover only the tools that report parsed - never the whole run - so
    they are a floor, not the answer. Whatever they miss has to come from the
    pipeline's own citation file, and whatever both miss has to be visible in
    the manuscript rather than dropped.
    """
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^\s*(10\.\d{4,9}/\S+?)\s*(#\s*(.*))?$", line.rstrip())
                if m:
                    out.append({"doi": m.group(1), "tool": (m.group(3) or "").strip()})
    except OSError:
        pass
    return out


def collect(results):
    """Everything one run can prove about itself."""
    results = os.path.abspath(results)
    run = {"results": results, "run_dir": os.path.dirname(results),
           "notes": []}

    info = None
    for cand in (os.path.join(results, "pipeline_info"),):
        if os.path.isdir(cand):
            info = cand
    if info is None:
        for root, dirs, _ in os.walk(results):
            dirs[:] = [d for d in dirs if d not in ("work", ".nextflow")]
            if "pipeline_info" in dirs:
                info = os.path.join(root, "pipeline_info")
                break
    if info is None:
        run["notes"].append("no pipeline_info/ anywhere under this tree - "
                            "nothing here can say what produced it")
        return run
    run["pipeline_info"] = info

    grouped = {}
    for name in os.listdir(info):
        m = TIMESTAMPED.match(name)
        if m:
            grouped.setdefault(m.group(1), []).append(os.path.join(info, name))

    for kind, paths in sorted(grouped.items()):
        pick, skipped = newest(paths)
        run[kind] = pick
        if skipped:
            run["notes"].append(
                "%d older %s file(s) beside the one used - this run was retried, "
                "and the older ones describe an attempt that did not finish"
                % (skipped, kind))

    vfile = find_versions(info)
    if vfile:
        parsed, err = read_yaml_ish(vfile)
        run["versions_file"] = vfile
        if err:
            run["notes"].append("versions file unreadable: %s" % err)
        else:
            tools, workflow = tools_from_versions(parsed)
            run["tools"] = tools
            run["workflow"] = workflow
            run["citable_tools"] = sorted(t for t in tools if t.lower() not in NOT_CITED)
    else:
        run["notes"].append("no versions file in pipeline_info/ - the tool "
                            "versions this run used are not recoverable from it")

    if run.get("params"):
        try:
            with open(run["params"], encoding="utf-8") as fh:
                run["params_values"] = json.load(fh)
        except (OSError, ValueError) as exc:
            run["notes"].append("params file unreadable: %s" % exc)

    report, citations = find_quality_report(results)
    if report:
        run["quality_report"] = report
    if citations:
        run["citation_dois"] = dois_from_citations(citations)

    # The rationale the person wrote when they launched it. This is the only
    # place on the whole tree that says WHY a parameter has the value it has,
    # and a methods section assembled without it can say what was run and never
    # why - which is the half a reader actually needs.
    for name in ("params.yaml", "params.yml"):
        cand = os.path.join(run["run_dir"], name)
        if os.path.isfile(cand):
            run["launch_params"] = cand
            break
    if "launch_params" not in run:
        run["notes"].append("no hand-written params.yaml beside results/ - the "
                            "reasoning behind the parameter choices is not on disk")
    return run


def render(runs):
    for run in runs:
        print(run["results"])
        wf = run.get("workflow") or {}
        for k, v in sorted(wf.items()):
            print("    %-24s %s" % (k, v))
        tools = run.get("tools") or {}
        citable = run.get("citable_tools") or []
        if tools:
            print("    %-24s %d (%d citable)" % ("tools", len(tools), len(citable)))
            print("        " + ", ".join("%s %s" % (t, tools[t]) for t in citable))
        for key in ("execution_report", "execution_trace", "params",
                    "quality_report", "launch_params"):
            if run.get(key):
                print("    %-24s %s" % (key, os.path.relpath(run[key], run["run_dir"])))
        dois = run.get("citation_dois") or []
        if dois:
            print("    %-24s %d" % ("dois recorded", len(dois)))
        for note in run["notes"]:
            print("    ! " + note)
        print()


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="collect_provenance.py",
        description="What one project's runs can prove about themselves.")
    p.add_argument("results", nargs="+", help="one or more results directories")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="emit the same report machine-readably")
    args = p.parse_args(argv)

    for d in args.results:
        if not os.path.isdir(d):
            print("not a directory: %s" % d, file=sys.stderr)
            return 2

    runs = [collect(d) for d in args.results]
    if args.as_json:
        json.dump({"runs": runs}, sys.stdout, indent=1, sort_keys=True)
        print()
    else:
        render(runs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
