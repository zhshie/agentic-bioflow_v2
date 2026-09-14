#!/bin/bash
# What a run can prove about itself, gathered by shape rather than by name.
#
#   collect_provenance.py [--json] <results-dir> [<results-dir> ...]
#
# Not nf-prov: wrroc coverage on this cluster is unmeasured (plan M1), so this
# still reconstructs from run output files - preferring `tw runs view` below
# for anything Platform can answer directly instead of a file-based guess.
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
#
# Everything above is a reconstruction, and a reconstruction is a copy of
# something Platform already holds (docs/PRINCIPLES.md, invariant 2). When a
# Seqera run id is known - `--run-id`, plus `--workspace` (or the settings
# file's `workspace_id`) - the command line, launch-time params and resolved
# Nextflow config are asked of Platform itself via `tw runs view --command
# --params --config` instead, and every field answered that way is marked
# `"platform"` in `sources`. A run id with no usable `tw` or workspace, or a
# call that fails outright, falls back to what these files can still prove:
# the launch-time params this run already recorded on disk, and the same
# command reconstruction methods_text.py performs and already labels as not
# reproducible. Neither is invented - a field neither side can supply is left
# out and a note says so (invariant 9). Tool versions are never asked of
# Platform: they live only in the versions YAML pipeline_info/ carries.
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
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

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
NOT_CITED = {"python", "python3", "r", "r-base", "sed", "awk", "perl", "bash",
             "pandas", "numpy", "yaml", "nextflow", "gawk", "grep", "coreutils"}

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


def find_tw_bin():
    """Where every other script here finds `tw`: TW_BIN, then the settings
    file's `tw_bin`, then PATH - the same order preflight.sh and task_health.sh
    use. This only ever reads a run that already finished; nothing here can
    launch one."""
    tw = os.environ.get("TW_BIN")
    if tw:
        return tw
    settings_sh = os.path.join(HERE, "settings.sh")
    if os.path.isfile(settings_sh):
        try:
            out = subprocess.run([settings_sh, "tw_bin"],
                                  capture_output=True, text=True, timeout=10)
            val = out.stdout.strip()
            if val:
                return val
        except (OSError, subprocess.TimeoutExpired):
            pass
    return shutil.which("tw")


def find_workspace():
    """The deployment's `workspace_id`, for a caller that gave a run id but no
    `--workspace`. Best effort - a settings file that cannot be found or read
    just means the Platform lookup gets skipped below, not an error here."""
    settings_sh = os.path.join(HERE, "settings.sh")
    if not os.path.isfile(settings_sh):
        return None
    try:
        out = subprocess.run([settings_sh, "workspace_id"],
                              capture_output=True, text=True, timeout=10)
        val = out.stdout.strip()
        return val or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def ambient_token_env():
    """The environment `tw` should see: TOWER_ACCESS_TOKEN if already
    exported, else the token file every other script here falls back to
    (settings.sh's own `token_file()`, which task_health.sh already uses this
    same way). Best effort throughout - a failure here just means the `tw`
    call below fails too, and that is reported as a gap, never papered over.
    """
    env = dict(os.environ)
    if env.get("TOWER_ACCESS_TOKEN"):
        return env
    settings_sh = os.path.join(HERE, "settings.sh")
    if not os.path.isfile(settings_sh):
        return env
    try:
        out = subprocess.run(
            ["bash", "-c", '. "$1" >/dev/null 2>&1; token_file',
             "--", settings_sh],
            capture_output=True, text=True, timeout=10)
        token_path = out.stdout.strip()
        if token_path and os.path.isfile(token_path):
            with open(token_path, encoding="utf-8") as fh:
                tok = fh.read().strip()
            if tok:
                env["TOWER_ACCESS_TOKEN"] = tok
    except (OSError, subprocess.TimeoutExpired):
        pass
    return env


def platform_fields(run_id, workspace, tw_bin, timeout=20):
    """command/params/config as Platform itself recorded for run_id - never a
    reconstruction. Read-only: only `runs view` is ever called, nothing here
    can start or change a run.

    Returns (fields, notes). `fields` holds only the keys actually answered,
    so a caller can tell "Platform said nothing" from "Platform was never
    asked" rather than trusting an empty string either way.
    """
    fields, notes = {}, []
    if not workspace:
        notes.append("run %s: no workspace id (pass --workspace, or set "
                     "workspace_id in the settings file) - Platform lookup "
                     "skipped" % run_id)
        return fields, notes
    if not tw_bin:
        notes.append("run %s: no usable tw (set tw_bin, TW_BIN, or install "
                     "it) - Platform lookup skipped" % run_id)
        return fields, notes

    env = ambient_token_env()
    for flag, key in (("--command", "command"),
                       ("--params", "params_effective"),
                       ("--config", "config")):
        try:
            out = subprocess.run(
                [tw_bin, "runs", "view", "-i", run_id,
                 "--workspace", workspace, flag],
                capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            notes.append("run %s: tw runs view %s timed out after %ds"
                         % (run_id, flag, timeout))
            continue
        except OSError as exc:
            notes.append("run %s: tw runs view %s failed to start (%s)"
                         % (run_id, flag, exc))
            continue
        if out.returncode != 0:
            detail = (out.stderr or out.stdout or "").strip().splitlines()
            detail = detail[-1] if detail else "exit %d" % out.returncode
            notes.append("run %s: tw runs view %s failed (%s)"
                         % (run_id, flag, detail))
            continue
        text = out.stdout.strip()
        if not text:
            notes.append("run %s: tw runs view %s returned nothing"
                         % (run_id, flag))
            continue
        fields[key] = text
    return fields, notes


def file_based_command(run):
    """The same reconstruction methods_text.py already performs and already
    labels as such: not the command Platform actually launched - that would
    point at an ephemeral URL and is not reproducible - so this is the file
    fallback when Platform cannot be asked, not a substitute for asking it.
    """
    wf = run.get("workflow") or {}
    pipeline = next((k for k in wf if "/" in k), None)
    if not pipeline:
        return None
    rev = wf.get(pipeline) or "<revision>"
    params_path = run.get("launch_params")
    pf = (os.path.relpath(params_path, run["run_dir"]) if params_path
          else "params.yaml")
    return "nextflow run %s -r %s -params-file %s" % (pipeline, rev, pf)


def wrroc_fields(results):
    """The Workflow Run RO-Crate nf-prov writes, if this run had it enabled.

    Read only two things from it - the crate's own path, for a reader to open,
    and what profiles it says it conforms to - never re-derived facts nf-prov
    already reports better. It carries no checksums or tool versions of its
    own (PITFALLS 32), so this adds nothing that would duplicate the fields
    already gathered above from the versions file.

    Returns (path, conforms_to, error). `path` is None when no crate exists at
    all - the ordinary case for a run launched without provenance. `error` is
    set, and conforms_to left None, when the file exists but is not valid
    JSON - invariant 9's "a gap is written into the output", never a crash.
    """
    path = os.path.join(results, "pipeline_info", "ro-crate-metadata.json")
    if not os.path.isfile(path):
        return None, None, None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return path, None, "ro-crate-metadata.json exists but is not valid JSON: %s" % exc

    graph = data.get("@graph") if isinstance(data, dict) else None
    if not isinstance(graph, list):
        graph = []
    by_id = {e["@id"]: e for e in graph if isinstance(e, dict) and "@id" in e}

    # The metadata descriptor names the root dataset via `about`; fall back to
    # the RO-Crate convention ("./") when the descriptor itself is missing or
    # malformed rather than giving up on the whole file for one odd entity.
    root_id = "./"
    descriptor = by_id.get("ro-crate-metadata.json")
    if isinstance(descriptor, dict):
        about = descriptor.get("about")
        if isinstance(about, dict) and about.get("@id"):
            root_id = about["@id"]

    root = by_id.get(root_id)
    raw = root.get("conformsTo") if isinstance(root, dict) else None
    if isinstance(raw, dict):
        raw = [raw]
    elif isinstance(raw, str):
        raw = [raw]
    conforms = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("@id"):
                conforms.append(item["@id"])
            elif isinstance(item, str):
                conforms.append(item)
    return path, conforms, None


def collect(results, run_id=None, workspace=None, tw_bin=None):
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

    crate_path, conforms, crate_err = wrroc_fields(results)
    if crate_path:
        run["wrroc_crate"] = crate_path
        if crate_err:
            run["notes"].append(crate_err)
        else:
            run["wrroc_conforms_to"] = conforms

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

    # A run id given on the command line means command, params and config can
    # come from Platform itself rather than being reconstructed (R4). No file
    # beside the run is consulted for the id: nothing writes one, and a file
    # recording a run's identity is the start of the parallel state invariant
    # 2 rules out.

    if run_id:
        run["platform_run_id"] = run_id
        tw = tw_bin or find_tw_bin()
        ws = workspace or find_workspace()
        fields, plat_notes = platform_fields(run_id, ws, tw)
        sources = {}

        if "command" in fields:
            run["command"] = fields["command"]
            sources["command"] = "platform"
        else:
            fb = file_based_command(run)
            if fb is not None:
                run["command"] = fb
                sources["command"] = "files"
                run["notes"].append(
                    "run %s: command not available from Platform - falling "
                    "back to a reconstruction from this run's own files, "
                    "which is not necessarily reproducible" % run_id)
            else:
                run["notes"].append(
                    "run %s: command not available from Platform, and this "
                    "run's own files do not have enough to reconstruct one "
                    "either" % run_id)

        if "params_effective" in fields:
            run["params_effective"] = fields["params_effective"]
            sources["params_effective"] = "platform"
        elif run.get("params_values") is not None:
            run["params_effective"] = json.dumps(run["params_values"],
                                                  sort_keys=True)
            sources["params_effective"] = "files"
            run["notes"].append(
                "run %s: params not available from Platform - falling back "
                "to this run's own recorded params file" % run_id)
        else:
            run["notes"].append(
                "run %s: params not available from Platform, and this run "
                "has no recorded params file to fall back to" % run_id)

        if "config" in fields:
            run["config"] = fields["config"]
            sources["config"] = "platform"
        else:
            run["notes"].append(
                "run %s: config not available from Platform, and this "
                "script has no file-based way to reconstruct the resolved "
                "Nextflow config - the gap is left in, not filled"
                % run_id)

        if sources:
            run["sources"] = sources
        run["notes"].extend(plat_notes)

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
                    "quality_report", "launch_params", "wrroc_crate"):
            if run.get(key):
                print("    %-24s %s" % (key, os.path.relpath(run[key], run["run_dir"])))
        dois = run.get("citation_dois") or []
        if dois:
            print("    %-24s %d" % ("dois recorded", len(dois)))
        conforms = run.get("wrroc_conforms_to")
        if conforms is not None:
            print("    %-24s %s" % ("wrroc_conforms_to",
                                     ", ".join(conforms) if conforms else "(none listed)"))
        sources = run.get("sources") or {}
        for key in ("command", "params_effective", "config"):
            if run.get(key):
                tag = " (%s)" % sources[key] if key in sources else ""
                print("    %-24s present%s" % (key, tag))
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
    p.add_argument("--run-id", dest="run_id", default=None,
                   help="the Seqera Platform run id for these results; "
                        "command/params/config are then read from `tw runs "
                        "view` instead of being reconstructed from files. "
                        "Applies to every results directory given, so pass "
                        "one at a time when it names only one run. With no "
                        "run id, nothing changes from today's behaviour")
    p.add_argument("--workspace", dest="workspace", default=None,
                   help="workspace id for --run-id (default: the settings "
                        "file's workspace_id)")
    args = p.parse_args(argv)

    for d in args.results:
        if not os.path.isdir(d):
            print("not a directory: %s" % d, file=sys.stderr)
            return 2

    runs = [collect(d, run_id=args.run_id, workspace=args.workspace)
            for d in args.results]
    if args.as_json:
        json.dump({"runs": runs}, sys.stdout, indent=1, sort_keys=True)
        print()
    else:
        render(runs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
