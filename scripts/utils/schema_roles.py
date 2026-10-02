#!/usr/bin/env python3
# Not andrewsgeller/nfcore_pipeline_samplesheet: it hard-codes three pipelines' columns and is unfinished; nf-schema's own `meta` tag and the file patterns in schema_input.json already say which column is which.
"""Work out which samplesheet column holds the sample name and which hold R1 / R2.

The answer comes from the pipeline's own `assets/schema_input.json` (or from
the operator), never from a column name this repo remembers - see
specs/003-samplesheet-roles/.

  sample column  the one requested column whose `meta` (a list or a bare
                 string) contains `id` or `sample`.
  FASTQ columns  requested columns whose `pattern` (also inside anyOf / oneOf /
                 allOf) accepts FASTQ file names and nothing else. `format:
                 file-path` alone does not count: fasta and BAM columns carry it
                 too. Schema order decides: first is R1, second is R2.

When the schema does not give exactly one answer the result is NeedsDecision:
the caller must ask the operator and come back with explicit roles.

CLI (used by scripts/prepare_launch.sh, so the rule lives in one place):

    schema_roles.py --schema <file|-> [--columns a,b,c] [--roles sample=X,read1=Y,read2=Z]

prints `sample=<col> read1=<col> [read2=<col>]` and exits 0; or prints
`needs-decision: role=<sample|reads> candidates=<a,b,c>` and exits 3; exit 2 on
bad input.

Standard library only.
"""

import argparse
import json
import re
import sys
from typing import List, NamedTuple, Optional, Union

# Names a pattern must accept (some of) and must reject (all of) to count as a
# FASTQ-only pattern. Not column names: these are file names.
_FASTQ_NAMES = ("reads.fastq.gz", "reads.fq.gz", "reads.fastq", "reads.fq")
_NOT_FASTQ_NAMES = ("reads.txt", "reads.bam", "reads.fasta", "reads.fa.gz", "reads.fasta.gz")
_SAMPLE_META = ("id", "sample")
_ROLE_KEYS = ("sample", "read1", "read2")


class Roles(NamedTuple):
    sample: str
    read1: str
    read2: Optional[str]      # None: the schema has a single reads column


class NeedsDecision(NamedTuple):
    role: str                 # "sample" or "reads"
    candidates: List[str]
    why: str

    def machine_line(self) -> str:
        return f"needs-decision: role={self.role} candidates={','.join(self.candidates)}"


def schema_properties(schema: dict) -> dict:
    """items.properties (the usual array-of-rows schema) or top-level properties."""
    items = schema.get("items")
    if isinstance(items, dict) and isinstance(items.get("properties"), dict):
        return items["properties"]
    props = schema.get("properties")
    return props if isinstance(props, dict) else {}


def _patterns(node) -> List[str]:
    out = []
    if isinstance(node, dict):
        if isinstance(node.get("pattern"), str):
            out.append(node["pattern"])
        for key in ("anyOf", "oneOf", "allOf"):
            for sub in node.get(key) or []:
                out.extend(_patterns(sub))
    return out


def _accepts_only_fastq(pattern: str) -> bool:
    try:
        rx = re.compile(pattern)
    except re.error:
        return False
    return (any(rx.search(n) for n in _FASTQ_NAMES)
            and not any(rx.search(n) for n in _NOT_FASTQ_NAMES))


def is_fastq_column(prop) -> bool:
    """FASTQ only when there is at least one pattern and EVERY pattern found
    accepts FASTQ and nothing else. A branch with no pattern (maxLength: 0, an
    empty string) is ignored; a branch that also accepts .bam disqualifies."""
    pats = _patterns(prop)
    return bool(pats) and all(_accepts_only_fastq(p) for p in pats)


def _is_file_column(prop) -> bool:
    if not isinstance(prop, dict):
        return False
    return is_fastq_column(prop) or prop.get("format") == "file-path" or bool(prop.get("exists"))


def _meta(prop) -> List[str]:
    m = prop.get("meta") if isinstance(prop, dict) else None
    if isinstance(m, str):
        return [m]
    return [x for x in m if isinstance(x, str)] if isinstance(m, list) else []


def infer_roles(schema: dict, columns: List[str]) -> Union[Roles, NeedsDecision]:
    props = schema_properties(schema)
    wanted = [c for c in columns]

    sample_cols = [c for c in wanted if any(m in _SAMPLE_META for m in _meta(props.get(c)))]
    if len(sample_cols) != 1:
        non_file = [c for c in wanted if not _is_file_column(props.get(c))]
        if sample_cols:
            return NeedsDecision("sample", sample_cols,
                                 f"{len(sample_cols)} requested columns are marked as the sample name")
        return NeedsDecision("sample", non_file,
                             "no requested column is marked as the sample name in the schema")

    # Schema order, not --columns order: the schema is what says "first is R1".
    # Ambiguity is judged on the WHOLE schema: asking for a subset does not tell
    # us which two of several FASTQ columns are R1/R2 (a subset used to put R2
    # into long_reads with exit 0).
    all_fastq = [c for c in props if is_fastq_column(props[c])]
    fastq = [c for c in all_fastq if c in wanted]
    if len(all_fastq) > 2:
        return NeedsDecision("reads", fastq or all_fastq,
                             f"the schema has {len(all_fastq)} columns that accept FASTQ files, "
                             f"so which two are R1/R2 cannot be told from it")
    if len(fastq) == 1:
        return Roles(sample_cols[0], fastq[0], None)
    if len(fastq) == 2:
        return Roles(sample_cols[0], fastq[0], fastq[1])
    if len(fastq) == 0:
        rest = [c for c in wanted if c != sample_cols[0]]
        return NeedsDecision("reads", rest, "no requested column accepts FASTQ file names")
    return NeedsDecision("reads", fastq,
                         f"{len(fastq)} requested columns accept FASTQ file names")


def other_file_columns(schema: dict, columns: List[str], roles: Roles) -> List[str]:
    """Requested file columns (long reads, fasta, BAM, a second FASTQ set...) that
    are not the sample / R1 / R2 roles. The tool leaves these empty."""
    props = schema_properties(schema)
    taken = {roles.sample, roles.read1, roles.read2}
    return [c for c in columns if c not in taken and _is_file_column(props.get(c))]


def parse_roles(spec: str, columns: List[str]) -> Roles:
    """`sample=X,read1=Y,read2=Z` (read2 optional) -> Roles. ValueError when it is
    malformed or names a column that was not requested."""
    given = {}
    for item in filter(None, (s.strip() for s in spec.split(","))):
        if "=" not in item:
            raise ValueError(f"--roles entry is not role=column: {item}")
        k, v = (x.strip() for x in item.split("=", 1))
        if k not in _ROLE_KEYS:
            raise ValueError(f"--roles has an unknown role '{k}' (use sample, read1, read2)")
        if k in given:
            raise ValueError(f"--roles: {k} given more than once; each role is named once")
        if not v:
            raise ValueError(f"--roles: role {k} has no column (write {k}=<column>)")
        given[k] = v
    for need in ("sample", "read1"):
        if need not in given:
            raise ValueError(f"--roles must name at least sample= and read1= (missing {need})")
    for k, v in given.items():
        if v not in columns:
            raise ValueError(f"--roles {k}={v}: '{v}' is not in the requested columns "
                             f"({', '.join(columns)}); the role names a column that is not in --columns")
    # One column, one role: two roles on the same column wrote a wrong sheet
    # with exit 0 - R2 overwrote R1 and the summary still said "paired"
    # (developer review of 003 S1).
    seen = {}
    for k, v in given.items():
        if v in seen:
            raise ValueError(f"--roles names column '{v}' for both {seen[v]} and {k}; "
                             f"each role needs its own column - re-run with --roles "
                             f"sample=<col>,read1=<col>,read2=<col>")
        seen[v] = k
    return Roles(given["sample"], given["read1"], given.get("read2"))


def explain(nd: NeedsDecision) -> str:
    what = "the sample name" if nd.role == "sample" else "R1 / R2 (the two read files)"
    return (f"cannot tell which column holds {what}: {nd.why}. Ask the user which is which "
            f"(candidates: {', '.join(nd.candidates) or 'none'}), then re-run with "
            f"--roles sample=<col>,read1=<col>,read2=<col>")


def load_schema(path: str) -> dict:
    """Read a schema from a file or '-' (stdin). ValueError on any failure."""
    try:
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        data = json.loads(text)
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot read schema {path}: {e}")
    if not isinstance(data, dict):
        raise ValueError(f"schema {path} is not a JSON object")
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Infer samplesheet column roles from a schema_input.json")
    ap.add_argument("--schema", required=True, help="schema_input.json path, or - for stdin")
    ap.add_argument("--columns", help="comma-separated requested columns (default: all schema columns)")
    ap.add_argument("--roles", help="operator's roles; skips inference")
    args = ap.parse_args(argv)
    try:
        schema = load_schema(args.schema)
        columns = ([c.strip() for c in args.columns.split(",") if c.strip()] if args.columns
                   else list(schema_properties(schema)))
        res = parse_roles(args.roles, columns) if args.roles else infer_roles(schema, columns)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if isinstance(res, NeedsDecision):
        print(f"ERROR: {explain(res)}", file=sys.stderr)
        print(res.machine_line())
        return 3
    print(" ".join(f"{k}={v}" for k, v in zip(_ROLE_KEYS, res) if v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
