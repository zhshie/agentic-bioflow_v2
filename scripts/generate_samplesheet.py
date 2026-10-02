#!/usr/bin/env python3
# Not each pipeline's own bin/fastq_dir_to_samplesheet.py: inconsistent and
# per-pipeline; this needed one discovery-and-pairing tool that works before
# a pipeline is even chosen.
"""Build an nf-core samplesheet from a directory of sequencing files.

Columns come from the caller (which reads them out of the pipeline's own
`assets/schema_input.json` at the pinned revision - see commands/launch.md),
never from a pipeline definition stored next to this script. The retired
nextflow-development skill kept a full per-pipeline YAML here (v1's spec.yaml) -
genome options, run command templates, outputs, troubleshooting - which
duplicated almost all of what the pipeline's own schema already says.
Reintroducing that would give the engine a second source of truth for every
pipeline, so only the mechanical part was migrated: file discovery and scored
R1/R2 pairing.

Which column holds the sample name and which hold R1 / R2 is not remembered
here either: it is read from the same schema (scripts/utils/schema_roles.py),
or named by the operator with --roles. When the schema does not give one
answer the tool stops with exit 3 and a `needs-decision:` line, writes nothing,
and the caller asks the operator. Other file columns (long reads, fasta, BAM...)
are left empty and named in one warning.

Depends on the standard library only. The original required PyYAML, which is not
installed in any interpreter on this cluster (verified: system python3.13,
anaconda3, miniforge3) - so it raised ModuleNotFoundError on every invocation.

Usage:
    generate_samplesheet.py <input_dir> --schema <schema_input.json> \\
        [--columns a,b,c] -o metadata/samplesheet.csv [--defaults k=v,...] \\
        [--roles sample=X,read1=Y,read2=Z] [--single-end]

Exit codes: 0 ok, 1 nothing found / validation failed, 2 bad usage (including
no schema and no --roles), 3 needs a decision from the operator.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.file_discovery import discover_files          # noqa: E402
from utils.sample_inference import match_read_pairs, SAMPLE_KEY  # noqa: E402
from utils import schema_roles                           # noqa: E402


def build_rows(input_dir, columns, defaults, single_end, roles):
    """Return (rows, warnings). One row per sample, keyed by the requested columns."""
    # Already recursive, and follows symlinks by default - which matters here,
    # because rawdata/ in a task dir is normally a symlink to the user's originals.
    files = discover_files(input_dir, file_type="fastq")
    if not files:
        return [], [f"no sequencing files found under {input_dir}"]

    pairs = match_read_pairs(files)
    rows, warnings, unpaired, two_for_one = [], [], [], []

    for key in sorted(pairs):
        p = pairs[key]
        sample = p["info"].get(SAMPLE_KEY) or key

        if p["r1"] is None:
            warnings.append(f"{sample}: found an R2 with no matching R1 - skipped")
            continue
        if p["r2"] is None and not single_end:
            # Do not decide this from filenames.
            #
            # The old behaviour was to warn "treated as single-end" and write the
            # row anyway. Anyone not watching stderr got a samplesheet that ran a
            # paired-end library as single-end: it completes, produces output, and
            # the output is wrong. Non-standard mate naming looks identical to a
            # genuinely single-end library from here.
            #
            # PIPELINE_FLOW.md Phase 1 step 9 already said single-end is not to be
            # auto-detected; this restores that.
            unpaired.append(sample)
            continue
        if p["r2"] is not None and roles.read2 is None and not single_end:
            # The schema has one reads column but this sample has two files.
            # Writing only R1 would quietly drop half the library.
            two_for_one.append(sample)
            continue

        values = {roles.sample: sample, roles.read1: os.path.abspath(p["r1"])}
        if roles.read2:
            values[roles.read2] = os.path.abspath(p["r2"]) if p["r2"] and not single_end else ""
        values.update(defaults)
        rows.append({c: values.get(c, defaults.get(c, "")) for c in columns})

    if unpaired:
        warnings.append(
            "no second read file found for: " + ", ".join(sorted(unpaired)) + ". "
            "These were NOT written. Ask the user whether this library is "
            "single-end (re-run with --single-end) or whether the mate files are "
            "named non-standardly - do not infer it from the filenames."
        )
    if two_for_one:
        warnings.append(
            "these samples have a second read file but the schema has only one reads "
            "column: " + ", ".join(sorted(two_for_one)) + ". They were NOT written. "
            "Ask the user how to represent them (name the columns with --roles, or "
            "re-run with --single-end if only the first file is wanted)."
        )

    return rows, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", help="directory holding the FASTQ files (searched recursively)")
    ap.add_argument("--schema",
                    help="the pipeline's own assets/schema_input.json (a path, or - for stdin): "
                         "says which column is the sample name and which are R1/R2, and "
                         "supplies the column order when --columns is not given")
    ap.add_argument("--columns",
                    help="comma-separated column names, in order, from the pipeline's own "
                         "schema (default with --schema: all of the schema's columns)")
    ap.add_argument("--roles",
                    help="the operator's choice, overriding the schema: "
                         "sample=<col>,read1=<col>[,read2=<col>]")
    ap.add_argument("-o", "--output", help="write here instead of stdout")
    ap.add_argument("--defaults", default="",
                    help="comma-separated key=value fills for columns that cannot be "
                         "inferred, e.g. strandedness=auto")
    ap.add_argument("--single-end", action="store_true",
                    help="the user has stated this library is single-end; leave the "
                         "second reads column empty. Without this flag, samples with no "
                         "second read file are refused rather than guessed at.")
    ap.add_argument("--delimiter", default=",", help="output delimiter (default ,)")
    args = ap.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"ERROR: not a directory: {args.input_dir}", file=sys.stderr)
        return 2

    schema = None
    if args.schema:
        try:
            schema = schema_roles.load_schema(args.schema)
        except ValueError as e:
            if not args.roles:
                print(f"ERROR: {e}. Without a schema, name the columns yourself: "
                      f"--roles sample=<col>,read1=<col>,read2=<col>", file=sys.stderr)
                return 2
            print(f"WARNING: {e} - going on with --roles alone", file=sys.stderr)

    if args.columns is not None:
        columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    elif schema is not None:
        columns = list(schema_roles.schema_properties(schema))
    else:
        print("ERROR: --columns is required unless --schema is given", file=sys.stderr)
        return 2
    if not columns:
        print("ERROR: --columns is empty", file=sys.stderr)
        return 2

    defaults = {}
    for item in filter(None, (d.strip() for d in args.defaults.split(","))):
        if "=" not in item:
            print(f"ERROR: --defaults entry is not key=value: {item}", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        defaults[k.strip()] = v.strip()

    # Roles: the operator's word first, then the schema. Never a remembered default.
    if args.roles:
        try:
            roles = schema_roles.parse_roles(args.roles, columns)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
    elif schema is not None:
        roles = schema_roles.infer_roles(schema, columns)
        if isinstance(roles, schema_roles.NeedsDecision):
            print(f"ERROR: {schema_roles.explain(roles)}", file=sys.stderr)
            print(roles.machine_line(), file=sys.stderr)
            return 3
    else:
        print("ERROR: no schema and no --roles: cannot tell which column holds the sample "
              "name or the reads. Pass --schema <the pipeline's schema_input.json>, or name "
              "them yourself with --roles sample=<col>,read1=<col>,read2=<col>",
              file=sys.stderr)
        return 2

    rows, warnings = build_rows(args.input_dir, columns, defaults, args.single_end, roles)

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    if not rows:
        print("ERROR: no samples could be built - nothing written", file=sys.stderr)
        return 1

    # File columns other than the short-read R1/R2 this tool fills (long reads,
    # fasta, BAM, a second FASTQ set...): left empty, named once, never guessed.
    if schema is not None:
        left = [c for c in schema_roles.other_file_columns(schema, columns, roles)
                if c not in defaults]
        if left:
            print("WARNING: this tool fills only the short-read R1/R2 columns; left empty "
                  "for the user to supply: " + ", ".join(left), file=sys.stderr)

    # Report columns that came out empty for every row: usually the spec asks for
    # something only the user knows (a condition, a batch), so the caller should
    # ask rather than ship a half-filled sheet.
    for c in columns:
        if all(not r[c] for r in rows):
            print(f"WARNING: column '{c}' is empty for every sample - "
                  f"fill it via --defaults or ask the user", file=sys.stderr)

    out = open(args.output, "w", newline="") if args.output else sys.stdout
    try:
        w = csv.DictWriter(out, fieldnames=columns, delimiter=args.delimiter,
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    finally:
        if args.output:
            out.close()

    where = args.output or "stdout"
    paired = sum(1 for r in rows if roles.read2 and r.get(roles.read2))
    print(f"wrote {len(rows)} samples ({paired} paired, {len(rows) - paired} single) -> {where}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
