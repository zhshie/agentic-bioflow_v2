#!/usr/bin/env python3
"""Build an nf-core samplesheet from a directory of sequencing files.

Columns come from the caller (which reads them out of the pipeline's spec.yaml),
never from a pipeline definition stored next to this script. The retired
nextflow-development skill kept a full per-pipeline YAML here - genome options,
run command templates, outputs, troubleshooting - which duplicated almost all of
spec.yaml. Reintroducing that would give the engine a second source of truth for
every pipeline, so only the mechanical part was migrated: file discovery and
scored R1/R2 pairing.

Depends on the standard library only. The original required PyYAML, which is not
installed in any interpreter on this cluster (verified: system python3.13,
anaconda3, miniforge3) - so it raised ModuleNotFoundError on every invocation.

Usage:
    generate_samplesheet.py <input_dir> --columns sample,fastq_1,fastq_2,strandedness \\
        -o metadata/samplesheet.csv [--defaults strandedness=auto] [--single-end]

Exit codes: 0 ok, 1 nothing found / validation failed, 2 bad usage.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.file_discovery import discover_files          # noqa: E402
from utils.sample_inference import match_read_pairs      # noqa: E402


def build_rows(input_dir, columns, defaults, single_end):
    """Return (rows, warnings). One row per sample, keyed by the requested columns."""
    # Already recursive, and follows symlinks by default - which matters here,
    # because rawdata/ in a task dir is normally a symlink to the user's originals.
    files = discover_files(input_dir, file_type="fastq")
    if not files:
        return [], [f"no sequencing files found under {input_dir}"]

    pairs = match_read_pairs(files)
    rows, warnings, unpaired = [], [], []

    for key in sorted(pairs):
        p = pairs[key]
        sample = p["info"].get("sample") or key

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

        values = {
            "sample": sample,
            "fastq_1": os.path.abspath(p["r1"]),
            "fastq_2": os.path.abspath(p["r2"]) if p["r2"] and not single_end else "",
        }
        values.update(defaults)
        rows.append({c: values.get(c, defaults.get(c, "")) for c in columns})

    if unpaired:
        warnings.append(
            "no second read file found for: " + ", ".join(sorted(unpaired)) + ". "
            "These were NOT written. Ask the user whether this library is "
            "single-end (re-run with --single-end) or whether the mate files are "
            "named non-standardly - do not infer it from the filenames."
        )

    return rows, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", help="directory holding the FASTQ files (searched recursively)")
    ap.add_argument("--columns", required=True,
                    help="comma-separated column names, in order, from the pipeline's spec.yaml")
    ap.add_argument("-o", "--output", help="write here instead of stdout")
    ap.add_argument("--defaults", default="",
                    help="comma-separated key=value fills for columns that cannot be "
                         "inferred, e.g. strandedness=auto")
    ap.add_argument("--single-end", action="store_true",
                    help="the user has stated this library is single-end; leave "
                         "fastq_2 empty. Without this flag, samples with no second "
                         "read file are refused rather than guessed at.")
    ap.add_argument("--delimiter", default=",", help="output delimiter (default ,)")
    args = ap.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"ERROR: not a directory: {args.input_dir}", file=sys.stderr)
        return 2

    columns = [c.strip() for c in args.columns.split(",") if c.strip()]
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

    rows, warnings = build_rows(args.input_dir, columns, defaults, args.single_end)

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    if not rows:
        print("ERROR: no samples could be built - nothing written", file=sys.stderr)
        return 1

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
    paired = sum(1 for r in rows if r.get("fastq_2"))
    print(f"wrote {len(rows)} samples ({paired} paired, {len(rows) - paired} single) -> {where}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
