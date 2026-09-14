#!/bin/bash
# The package build_package.sh assembles, described as an RO-Crate 1.1 itself
# (proposal R5), so an ELN or archive that already imports RO-Crate / .eln can
# bring the whole package in without a bespoke reader.
#
#   package_crate.py <project-dir> <submission-dir> <run-results-dir> [...]
#
# Not ro-crate-py (the `rocrate` library): not importable on this login node
# under `module load python/3.12.2` - `import rocrate` raises
# ModuleNotFoundError (checked 2026-09-14) - so this writes RO-Crate 1.1 JSON
# directly with the standard library instead of adding a dependency that is
# not on this cluster.
#
# What this writes, and what it never invents (docs/PRINCIPLES.md invariant
# 9): a root Dataset `./` naming every file build_package.sh actually put in
# submission/ - nothing here re-derives that list from a plan, it walks the
# directory. `license` and `author` are never set: neither can be read from
# any file this plugin controls, so both are simply absent and README.md says
# so, rather than a guessed value standing in for a fact nobody supplied.
#
# For each run whose results carry `pipeline_info/ro-crate-metadata.json` -
# nf-prov's own Workflow Run RO-Crate (PITFALLS 32) - that file is copied
# byte-for-byte into `runs/<run-name>/` and referenced from the root as a
# nested Dataset, `conformsTo` copied from the nested crate's own root entity.
# It is never rewritten: PITFALLS 32 measured that it carries this cluster's
# absolute paths, and README.md is told to warn about exactly that rather than
# have this script paper over it. A run with no such file is skipped without
# error - most runs will not have opted into nf-prov.
#
# <run-name> is the same name collect_provenance.py already uses for a run:
# the parent directory of the `results/` this was called with
# (`os.path.dirname(results)` in collect_provenance.py's own `collect()`), so
# a package and a provenance.json entry for the same run agree on its name.
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
import shutil
import sys
from datetime import datetime, timezone

CONTEXT = "https://w3id.org/ro/crate/1.1/context"
CRATE_1_1 = "https://w3id.org/ro/crate/1.1"

# Only extensions this package actually writes, or that a person is likely to
# drop into analysis/figures or analysis/scripts. Anything else is left
# without encodingFormat rather than guessed - "obvious" in the spec means
# obvious, not inferred from a byte sniff this script does not do.
ENCODING_FORMAT = {
    ".md": "text/markdown",
    ".qmd": "text/markdown",
    ".json": "application/json",
    ".bib": "application/x-bibtex",
    ".py": "text/x-python",
    ".r": "text/x-r",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".yml": "application/yaml",
    ".yaml": "application/yaml",
    ".html": "text/html",
}


def encoding_format(path):
    return ENCODING_FORMAT.get(os.path.splitext(path)[1].lower())


def file_entity(rel_path):
    e = {"@id": rel_path, "@type": "File", "name": os.path.basename(rel_path)}
    fmt = encoding_format(rel_path)
    if fmt:
        e["encodingFormat"] = fmt
    return e


def payload_files(submission_dir):
    """Every file already under submission/, relative-posix, sorted -
    excluding the crate's own metadata file and anything under runs/ (those
    are nested crates, handled separately so their File entities sit inside
    the nested Dataset rather than duplicated at the root)."""
    out = []
    for root, _dirs, files in os.walk(submission_dir):
        rel_root = os.path.relpath(root, submission_dir)
        for f in sorted(files):
            rel = f if rel_root == "." else os.path.join(rel_root, f)
            rel = rel.replace(os.sep, "/")
            if rel == "ro-crate-metadata.json":
                continue
            if rel.startswith("runs/"):
                continue
            out.append(rel)
    return sorted(out)


def nested_crate_root(crate):
    """The entity describing '@id': './' in a crate someone else wrote, or
    None. Read, never assumed - a crate that does not carry one leaves
    conformsTo out rather than inventing it."""
    for e in crate.get("@graph", []):
        if e.get("@id") == "./":
            return e
    return None


def collect_runs(project_dir, results_dirs, submission_dir):
    """For every results dir that carries nf-prov's crate, copy it verbatim
    into submission/runs/<name>/ and return what the root crate needs to know
    about it. A results dir with no such file contributes nothing and is not
    an error - most runs will not have nf-prov enabled."""
    runs = []
    for results_dir in results_dirs:
        src = os.path.join(results_dir, "pipeline_info", "ro-crate-metadata.json")
        if not os.path.isfile(src):
            continue
        run_name = os.path.basename(os.path.dirname(os.path.abspath(results_dir)))
        dest_dir = os.path.join(submission_dir, "runs", run_name)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "ro-crate-metadata.json")
        shutil.copyfile(src, dest)  # bytes only - never rewritten (PITFALLS 32)
        with open(dest, "r", encoding="utf-8") as fh:
            nested = json.load(fh)
        root = nested_crate_root(nested)
        runs.append({
            "name": run_name,
            "rel": "runs/%s/ro-crate-metadata.json" % run_name,
            "conforms_to": root.get("conformsTo") if root else None,
        })
    return sorted(runs, key=lambda r: r["name"])


def build_crate(project_name, submission_dir, runs):
    files = payload_files(submission_dir)
    has_part = [{"@id": f} for f in files]

    graph = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": CRATE_1_1},
            "about": {"@id": "./"},
        },
    ]

    for f in files:
        graph.append(file_entity(f))

    for r in runs:
        has_part.append({"@id": "runs/%s/" % r["name"]})
        ds = {
            "@id": "runs/%s/" % r["name"],
            "@type": "Dataset",
            "hasPart": [{"@id": r["rel"]}],
        }
        if r["conforms_to"] is not None:
            ds["conformsTo"] = r["conforms_to"]
        graph.append(ds)
        graph.append(file_entity(r["rel"]))

    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": project_name,
        "description": "An analysis package assembled by agentic-bioflow.",
        "datePublished": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hasPart": has_part,
    }
    # license is never set here - nothing on disk says what it is
    # (docs/PRINCIPLES.md invariant 9). Insert it after datePublished so the
    # descriptor entity stays first and the root Dataset stays second, which
    # is the order most RO-Crate readers expect but nothing here depends on.
    graph.insert(1, root)

    return {"@context": CONTEXT, "@graph": graph}


def append_readme(readme_path, runs_copied):
    lines = [
        "",
        "## RO-Crate packaging",
        "",
        "This package is itself an RO-Crate (`ro-crate-metadata.json` at its",
        "root), so an ELN or archive that already imports RO-Crate / `.eln`",
        "can bring the whole package in directly.",
        "",
        "- No license is declared - `license` is absent from",
        "  `ro-crate-metadata.json`. Add one only if this project's authors",
        "  choose one; nothing on disk told this build what it should be.",
    ]
    if runs_copied:
        lines += [
            "- `runs/*/ro-crate-metadata.json` is nf-prov's own crate for that",
            "  run, copied unchanged. It records this cluster's absolute file",
            "  paths - decide whether that is acceptable before sending this",
            "  package outside the lab.",
        ]
    with open(readme_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project_dir")
    p.add_argument("submission_dir")
    p.add_argument("results_dirs", nargs="+")
    args = p.parse_args(argv)

    project_dir = os.path.abspath(args.project_dir)
    submission_dir = os.path.abspath(args.submission_dir)
    if not os.path.isdir(submission_dir):
        print("no submission directory at %s" % submission_dir, file=sys.stderr)
        return 2

    runs = collect_runs(project_dir, args.results_dirs, submission_dir)
    crate = build_crate(os.path.basename(project_dir), submission_dir, runs)

    out_path = os.path.join(submission_dir, "ro-crate-metadata.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(crate, fh, indent=2, sort_keys=False)
        fh.write("\n")

    readme_path = os.path.join(submission_dir, "README.md")
    if os.path.isfile(readme_path):
        append_readme(readme_path, runs_copied=bool(runs))

    print("wrote     submission/ro-crate-metadata.json (%d run crate(s) nested)" % len(runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
