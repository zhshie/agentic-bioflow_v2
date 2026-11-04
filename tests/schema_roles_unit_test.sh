#!/bin/bash
# Unit tests for every public name in scripts/utils/schema_roles.py: the one place that
# decides which samplesheet column is the sample name and which are R1 / R2.
#
# Nothing existing: tests/generate_samplesheet_test.sh and tests/prepare_launch_test.sh only reach this
# module through the samplesheet CLI, on whole-tool inputs; no test called its functions one by one with a
# table of inputs and expected answers, so a change to one branch (the bare-string `meta`, the
# subset-of-columns rule, the --roles checks) could pass them. This file is new and self-contained.
#
# Pure: no network, no settings file, no site. The cases are a Python table run by `python3 -I`, which
# imports the module by path. Schemas are small inline ones; three real nf-core schemas from
# tests/fixtures/schema_input/ are sanity rows. Output: one ok/FAIL line per case, verdict in the exit code.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 is required"; exit 1; }
[ -f "$ROOT/scripts/utils/schema_roles.py" ] || { echo "FAIL: $ROOT/scripts/utils/schema_roles.py not found"; exit 1; }

python3 -I - "$ROOT" <<'PY'
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "scripts", "utils"))
import schema_roles as sr  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "schema_input")
TOOL = os.path.join(ROOT, "scripts", "utils", "schema_roles.py")
TMP = tempfile.mkdtemp(prefix="schema_roles_unit.")

fails = 0
total = 0


def report(label, good, detail=""):
    global fails, total
    total += 1
    print(f"{label:<76} ", end="")
    if good:
        print("ok")
    else:
        fails += 1
        print(f"FAIL: {detail}")


def eq(label, got, want):
    report(label, got == want, f"got {got!r}, wanted {want!r}")


def has(label, text, *needles):
    miss = [n for n in needles if n not in text]
    report(label, not miss, f"{miss!r} not in {text!r}")


def lacks(label, text, *needles):
    bad = [n for n in needles if n in text]
    report(label, not bad, f"unexpected {bad!r} in {text!r}")


def raises(label, fn, *needles):
    try:
        fn()
    except ValueError as e:
        miss = [n for n in needles if n not in str(e)]
        report(label, not miss, f"ValueError text {str(e)!r} lacks {miss!r}")
    except BaseException as e:  # noqa: BLE001 - any other type is itself the failure
        report(label, False, f"raised {type(e).__name__}, wanted ValueError: {e}")
    else:
        report(label, False, "did not raise")


def write(name, text):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def sheet(**props):
    """The usual array-of-rows schema, properties in the order given."""
    return {"items": {"properties": props}}


FQ_PAT = r"^\S+\.f(ast)?q\.gz$"
SAMPLE = {"type": "string", "meta": ["id"], "pattern": r"^\S+$"}
FQ = {"type": "string", "format": "file-path", "exists": True, "pattern": FQ_PAT}
FQ_OPT = {"anyOf": [{"type": "string", "format": "file-path", "pattern": FQ_PAT},
                    {"type": "string", "maxLength": 0}]}
BAM_OR_FQ = {"anyOf": [{"type": "string", "pattern": FQ_PAT}, {"type": "string", "pattern": r"^\S+\.bam$"}]}
FASTA = {"type": "string", "format": "file-path", "pattern": r"^\S+\.fa(sta)?(\.gz)?$"}
PLAIN = {"type": "string", "enum": ["a", "b"]}
R = sr.Roles
ND = sr.NeedsDecision

# ---------------------------------------------------------------- schema_properties
print("# schema_properties")
P = {"x": {"type": "string"}}
eq("schema_properties: items.properties", sr.schema_properties({"items": {"properties": P}}), P)
eq("schema_properties: top-level properties", sr.schema_properties({"properties": P}), P)
eq("schema_properties: items wins over top-level when both exist",
   sr.schema_properties({"items": {"properties": P}, "properties": {"y": {}}}), P)
eq("schema_properties: items without properties falls back to top-level",
   sr.schema_properties({"items": {"type": "object"}, "properties": P}), P)
eq("schema_properties: items.properties not a dict falls back to top-level",
   sr.schema_properties({"items": {"properties": ["x"]}, "properties": P}), P)
eq("schema_properties: items not a dict falls back to top-level",
   sr.schema_properties({"items": [1, 2], "properties": P}), P)
eq("schema_properties: neither -> {}", sr.schema_properties({"type": "array"}), {})
eq("schema_properties: empty schema -> {}", sr.schema_properties({}), {})
eq("schema_properties: top-level properties not a dict -> {}", sr.schema_properties({"properties": "x"}), {})
eq("schema_properties: both present but not dicts -> {}",
   sr.schema_properties({"items": {"properties": 1}, "properties": None}), {})
eq("schema_properties: keeps declared order",
   list(sr.schema_properties(sheet(b={}, a={}, c={}))), ["b", "a", "c"])

# ---------------------------------------------------------------- is_fastq_column
print("# is_fastq_column")
FQ_ONLY = [
    ("plain fastq.gz pattern", {"pattern": FQ_PAT}),
    ("uncompressed-only pattern", {"pattern": r"^\S+\.f(ast)?q$"}),
    ("unanchored fq.gz pattern (search, not match)", {"pattern": r"fq\.gz$"}),
    ("accepts only .fastq.gz", {"pattern": r"\.fastq\.gz$"}),
    ("accepts only .fastq", {"pattern": r"\.fastq$"}),
    ("accepts only .fq", {"pattern": r"\.fq$"}),
    ("anyOf fastq + empty-string branch (nf-core optional column)", FQ_OPT),
    ("oneOf with fastq branch", {"oneOf": [{"pattern": FQ_PAT}]}),
    ("allOf with fastq branch", {"allOf": [{"pattern": FQ_PAT}]}),
    ("nested anyOf inside anyOf", {"anyOf": [{"anyOf": [{"pattern": FQ_PAT}]}, {"maxLength": 0}]}),
    ("top-level pattern plus anyOf branch, both fastq", {"pattern": FQ_PAT, "anyOf": [{"pattern": r"fq\.gz$"}]}),
]
for name, prop in FQ_ONLY:
    eq(f"is_fastq_column: {name} -> True", sr.is_fastq_column(prop), True)
NOT_FQ = [
    ("no pattern at all", {"type": "string", "format": "file-path"}),
    ("empty dict", {}),
    ("None", None),
    ("a string, not a dict", "^\\S+\\.fastq\\.gz$"),
    ("a list", [{"pattern": FQ_PAT}]),
    ("catch-all ^\\S+$ accepts .txt", {"pattern": r"^\S+$"}),
    ("pattern accepts only .txt", {"pattern": r"^\S+\.txt$"}),
    ("fasta pattern", FASTA),
    ("fastq + bam in one pattern", {"pattern": r"^\S+\.(bam|f(ast)?q\.gz)$"}),
    ("anyOf fastq branch + bam branch", BAM_OR_FQ),
    ("anyOf fastq branch + catch-all branch", {"anyOf": [{"pattern": FQ_PAT}, {"pattern": r"^\S+$"}]}),
    ("invalid regex", {"pattern": "(["}),
    ("fastq branch + invalid-regex branch", {"anyOf": [{"pattern": FQ_PAT}, {"pattern": "(["}]}),
    ("pattern is not a string", {"pattern": 5}),
    ("anyOf is not iterable-of-dicts (None)", {"anyOf": None}),
    ("only a maxLength branch", {"anyOf": [{"maxLength": 0}]}),
    ("format file-path alone does not count", {"format": "file-path", "exists": True}),
    ("fq.gz or .txt", {"pattern": r"fq\.gz$|\.txt$"}),
    ("fq.gz or .bam", {"pattern": r"fq\.gz$|\.bam$"}),
    ("fq.gz or .fasta", {"pattern": r"fq\.gz$|\.fasta$"}),
    ("fq.gz or .fa.gz", {"pattern": r"fq\.gz$|\.fa\.gz$"}),
    ("fq.gz or .fasta.gz", {"pattern": r"fq\.gz$|\.fasta\.gz$"}),
    ("fasta pattern in a deeper branch", {"anyOf": [{"pattern": FQ_PAT}, {"allOf": [{"pattern": r"^\S+\.fa$"}]}]}),
]
for name, prop in NOT_FQ:
    eq(f"is_fastq_column: {name} -> False", sr.is_fastq_column(prop), False)

# ---------------------------------------------------------------- is_mixed_reads_column
print("# is_mixed_reads_column")
MIXED = [
    ("fastq branch + bam branch", BAM_OR_FQ),
    ("fastq branch + catch-all branch", {"anyOf": [{"pattern": FQ_PAT}, {"pattern": r"^\S+$"}]}),
    ("oneOf form", {"oneOf": [{"pattern": FQ_PAT}, {"pattern": r"^\S+\.bam$"}]}),
    ("one pattern accepting fastq and bam", {"pattern": FQ_PAT, "anyOf": [{"pattern": r"^\S+\.bam$"}]}),
]
for name, prop in MIXED:
    eq(f"is_mixed_reads_column: {name} -> True", sr.is_mixed_reads_column(prop), True)
NOT_MIXED = [
    ("fastq only", FQ),
    ("fastq + empty-string branch (no other pattern)", FQ_OPT),
    ("catch-all sample-name pattern (no fastq-only branch)", SAMPLE),
    ("bam only", {"pattern": r"^\S+\.bam$"}),
    ("no pattern", {"type": "string"}),
    ("None", None),
    ("empty dict", {}),
    ("invalid regex only", {"pattern": "(["}),
    ("two fastq-only branches", {"anyOf": [{"pattern": FQ_PAT}, {"pattern": r"fq\.gz$"}]}),
]
for name, prop in NOT_MIXED:
    eq(f"is_mixed_reads_column: {name} -> False", sr.is_mixed_reads_column(prop), False)

# ---------------------------------------------------------------- infer_roles
print("# infer_roles")
PAIRED = sheet(sample=SAMPLE, fastq_1=FQ, fastq_2=FQ_OPT, strandedness=PLAIN)
ALL = ["sample", "fastq_1", "fastq_2", "strandedness"]
eq("infer_roles: paired schema, all columns",
   sr.infer_roles(PAIRED, ALL), R("sample", "fastq_1", "fastq_2"))
eq("infer_roles: result is a Roles tuple with the three named fields",
   sr.infer_roles(PAIRED, ALL)._fields, ("sample", "read1", "read2"))
eq("infer_roles: single-end (only fastq_1 requested; schema has two) -> read2 None",
   sr.infer_roles(PAIRED, ["sample", "fastq_1"]), R("sample", "fastq_1", None))
eq("infer_roles: single-end schema (one fastq column)",
   sr.infer_roles(sheet(sample=SAMPLE, reads=FQ), ["sample", "reads"]), R("sample", "reads", None))
eq("infer_roles: the requested fastq_2 alone is read1 (schema has two, so it is not ambiguous)",
   sr.infer_roles(PAIRED, ["sample", "fastq_2"]), R("sample", "fastq_2", None))
eq("infer_roles: schema order decides R1/R2, not --columns order",
   sr.infer_roles(PAIRED, ["fastq_2", "strandedness", "fastq_1", "sample"]), R("sample", "fastq_1", "fastq_2"))
eq("infer_roles: sample column can be anywhere in --columns",
   sr.infer_roles(PAIRED, ["fastq_1", "fastq_2", "sample"]), R("sample", "fastq_1", "fastq_2"))
eq("infer_roles: a schema whose properties are top-level (no items)",
   sr.infer_roles({"properties": PAIRED["items"]["properties"]}, ALL), R("sample", "fastq_1", "fastq_2"))
eq("infer_roles: a requested column the schema does not have is ignored",
   sr.infer_roles(PAIRED, ["sample", "fastq_1", "ghost"]), R("sample", "fastq_1", None))
eq("infer_roles: column names are not remembered (odd names work)",
   sr.infer_roles(sheet(zz=dict(SAMPLE), aa=FQ, bb=FQ), ["zz", "aa", "bb"]), R("zz", "aa", "bb"))

for tag, meta, want in [
    ("list [id]", ["id"], True),
    ("list [sample]", ["sample"], True),
    ("bare string id", "id", True),
    ("bare string sample", "sample", True),
    ("list with id second", ["single_end", "id"], True),
    ("list with a non-string first", [1, "id"], True),
    ("list of other keys", ["single_end"], False),
    ("only non-strings", [1, None], False),
    ("a dict is not a meta list", {"id": 1}, False),
    ("case matters (ID)", "ID", False),
    ("exact match, not prefix (samples)", ["samples"], False),
    ("empty list", [], False),
    ("empty string", "", False),
]:
    sch = sheet(name={"type": "string", "meta": meta}, fastq_1=FQ)
    res = sr.infer_roles(sch, ["name", "fastq_1"])
    if want:
        eq(f"infer_roles: meta {tag} marks the sample column", res, R("name", "fastq_1", None))
    else:
        eq(f"infer_roles: meta {tag} does not mark it", res, ND("sample", ["name"], res.why if isinstance(res, ND) else ""))

# the sample role
sch = sheet(sample=SAMPLE, fastq_1=FQ)
r = sr.infer_roles(sch, ["fastq_1"])
eq("infer_roles: sample column not requested -> NeedsDecision(sample)", (type(r), r.role), (ND, "sample"))
eq("infer_roles: ... candidates are the requested non-file columns (none)", r.candidates, [])

sch = sheet(sample=dict(SAMPLE), sample_name={"type": "string", "meta": ["sample"]}, fastq_1=FQ)
r = sr.infer_roles(sch, ["sample_name", "sample", "fastq_1"])
eq("infer_roles: two sample-marked columns -> NeedsDecision(sample)", (type(r), r.role), (ND, "sample"))
eq("infer_roles: ... candidates are the marked ones, in --columns order", r.candidates, ["sample_name", "sample"])
has("infer_roles: ... why counts them", r.why, "2 requested columns are marked as the sample name")

sch = sheet(id={"type": "string"}, fastq_1=FQ, fastq_2=FQ, strandedness=PLAIN, assembly=FASTA,
            bam={"type": "string", "exists": True})
r = sr.infer_roles(sch, ["fastq_1", "id", "strandedness", "assembly", "fastq_2", "bam", "ghost"])
eq("infer_roles: no sample marker -> NeedsDecision(sample)", (type(r), r.role), (ND, "sample"))
eq("infer_roles: ... candidates are non-file columns only (unknown ones included), --columns order",
   r.candidates, ["id", "strandedness", "ghost"])
has("infer_roles: ... why says nothing is marked", r.why, "no requested column is marked as the sample name")
r = sr.infer_roles(sheet(), [])
eq("infer_roles: empty schema and no columns -> NeedsDecision(sample, [])", r, ND("sample", [], r.why))
r = sr.infer_roles({"items": {"type": "object"}}, ["a", "b"])
eq("infer_roles: schema without properties -> candidates are all requested columns", (r.role, r.candidates), ("sample", ["a", "b"]))

# the reads role
sch = sheet(sample=SAMPLE, strandedness=PLAIN, notes=PLAIN)
r = sr.infer_roles(sch, ["strandedness", "sample", "notes"])
eq("infer_roles: no fastq column -> NeedsDecision(reads)", (type(r), r.role), (ND, "reads"))
eq("infer_roles: ... candidates are the requested columns minus the sample, in --columns order",
   r.candidates, ["strandedness", "notes"])
has("infer_roles: ... why", r.why, "no requested column accepts FASTQ file names")

sch = sheet(sample=SAMPLE, a=FQ, b=FQ, c=FQ)
r = sr.infer_roles(sch, ["sample", "a", "b", "c"])
eq("infer_roles: three fastq columns -> NeedsDecision(reads)", (type(r), r.role, r.candidates), (ND, "reads", ["a", "b", "c"]))
has("infer_roles: ... why counts the columns", r.why, "3 columns that accept FASTQ files")
r = sr.infer_roles(sch, ["c", "sample", "a"])
eq("infer_roles: asking for a subset of >2 fastq columns does not resolve it",
   (type(r), r.role, r.candidates), (ND, "reads", ["a", "c"]))
r = sr.infer_roles(sch, ["sample"])
eq("infer_roles: >2 fastq in schema, none requested -> candidates fall back to all of them",
   (type(r), r.role, r.candidates), (ND, "reads", ["a", "b", "c"]))
eq("infer_roles: two fastq columns in the schema are not ambiguous",
   sr.infer_roles(sheet(sample=SAMPLE, a=FQ, b=FQ), ["sample", "a", "b"]), R("sample", "a", "b"))

sch = sheet(sample=SAMPLE, reads_x=BAM_OR_FQ, fastq_1=FQ)
r = sr.infer_roles(sch, ["fastq_1", "sample", "reads_x"])
eq("infer_roles: a mixed fastq/bam column -> NeedsDecision(reads)", (type(r), r.role), (ND, "reads"))
eq("infer_roles: ... candidates in schema order", r.candidates, ["reads_x", "fastq_1"])
has("infer_roles: ... why names the mixed column", r.why, "column(s) reads_x accept FASTQ files and other files too")
r = sr.infer_roles(sch, ["sample", "fastq_1"])
eq("infer_roles: mixed column in the schema but not requested still stops",
   (type(r), r.role), (ND, "reads"))
eq("infer_roles: ... candidates are the requested ones among them", r.candidates, ["fastq_1"])
r = sr.infer_roles(sch, ["sample"])
eq("infer_roles: ... none requested -> candidates fall back to all fastq-only + mixed columns",
   r.candidates, ["fastq_1", "reads_x"])
r = sr.infer_roles(sch, ["sample", "reads_x"])
eq("infer_roles: only the mixed column requested -> it is the only candidate", r.candidates, ["reads_x"])
r = sr.infer_roles(sheet(sample=SAMPLE, a=BAM_OR_FQ, b=BAM_OR_FQ), ["sample", "a", "b"])
has("infer_roles: two mixed columns are both named", r.why, "a, b accept FASTQ files")
r = sr.infer_roles(sheet(sample=SAMPLE, generic={"type": "string", "pattern": r"^\S+$"}, a=FQ),
                   ["sample", "generic", "a"])
eq("infer_roles: a catch-all pattern column is not 'mixed' (no fastq-only branch)", r, R("sample", "a", None))

# real schemas
for f, want in [("rnaseq-3.27.0.json", R("sample", "fastq_1", "fastq_2")),
                ("taxprofiler-2.0.1.json", R("sample", "fastq_1", "fastq_2"))]:
    sch = json.load(open(os.path.join(FX, f), encoding="utf-8"))
    eq(f"infer_roles: real schema {f}", sr.infer_roles(sch, list(sr.schema_properties(sch))), want)
sch = json.load(open(os.path.join(FX, "mag-5.5.0.json"), encoding="utf-8"))
r = sr.infer_roles(sch, list(sr.schema_properties(sch)))
eq("infer_roles: real schema mag-5.5.0.json (three fastq columns) needs a decision",
   (type(r), r.role, r.candidates), (ND, "reads", ["short_reads_1", "short_reads_2", "long_reads"]))

# ---------------------------------------------------------------- NeedsDecision.machine_line / explain
print("# NeedsDecision.machine_line, explain")
eq("machine_line: role and comma-joined candidates",
   ND("reads", ["a", "b", "c"], "why").machine_line(), "needs-decision: role=reads candidates=a,b,c")
eq("machine_line: sample role, one candidate", ND("sample", ["id"], "w").machine_line(),
   "needs-decision: role=sample candidates=id")
eq("machine_line: no candidates", ND("sample", [], "w").machine_line(), "needs-decision: role=sample candidates=")
e = sr.explain(ND("sample", ["x", "y"], "two are marked"))
has("explain: sample role says 'the sample name'", e, "cannot tell which column holds the sample name: two are marked.")
lacks("explain: sample role does not say R1 / R2", e, "R1 / R2")
has("explain: candidates joined with ', '", e, "(candidates: x, y)")
has("explain: tells the next step", e, "re-run with --roles sample=<col>,read1=<col>,read2=<col>")
e = sr.explain(ND("reads", ["a"], "none fit"))
has("explain: reads role says R1 / R2", e, "cannot tell which column holds R1 / R2 (the two read files): none fit.")
lacks("explain: reads role does not say 'the sample name'", e, "the sample name")
has("explain: empty candidate list reads 'none'", sr.explain(ND("reads", [], "w")), "(candidates: none)")
eq("explain: any role other than 'sample' is the reads wording",
   "R1 / R2" in sr.explain(ND("whatever", ["a"], "w")), True)

# ---------------------------------------------------------------- other_file_columns
print("# other_file_columns")
OF = sheet(sample=SAMPLE, fastq_1=FQ, fastq_2=FQ, long_reads={"type": "string", "pattern": FQ_PAT},
           assembly=FASTA, bam={"type": "string", "exists": True}, notexist={"type": "string", "exists": False},
           note=PLAIN, weird=True)
ROLES3 = R("sample", "fastq_1", "fastq_2")
cols = ["sample", "fastq_1", "fastq_2", "long_reads", "assembly", "bam", "notexist", "note", "weird", "ghost"]
eq("other_file_columns: file columns that are not sample/R1/R2, in --columns order",
   sr.other_file_columns(OF, cols, ROLES3), ["long_reads", "assembly", "bam"])
eq("other_file_columns: --columns order, not schema order",
   sr.other_file_columns(OF, ["bam", "assembly", "long_reads"], ROLES3), ["bam", "assembly", "long_reads"])
eq("other_file_columns: single-end roles (read2 None) leave the second fastq column as 'other'",
   sr.other_file_columns(OF, ["sample", "fastq_1", "fastq_2"], R("sample", "fastq_1", None)), ["fastq_2"])
eq("other_file_columns: only requested columns are considered",
   sr.other_file_columns(OF, ["sample", "fastq_1", "fastq_2"], ROLES3), [])
eq("other_file_columns: exists false and plain strings are not file columns",
   sr.other_file_columns(OF, ["notexist", "note"], ROLES3), [])
eq("other_file_columns: a column missing from the schema, or a non-dict property, is not a file column",
   sr.other_file_columns(OF, ["ghost", "weird"], ROLES3), [])
eq("other_file_columns: format file-path alone counts (fasta-like column)",
   sr.other_file_columns(sheet(s=SAMPLE, f={"format": "file-path"}), ["f"], R("s", "x", None)), ["f"])
eq("other_file_columns: a fastq-pattern column with no format counts",
   sr.other_file_columns(OF, ["long_reads"], ROLES3), ["long_reads"])
eq("other_file_columns: no columns -> []", sr.other_file_columns(OF, [], ROLES3), [])
eq("other_file_columns: a role column that is not first stays excluded (read2 given)",
   sr.other_file_columns(OF, ["fastq_2", "long_reads"], ROLES3), ["long_reads"])
eq("other_file_columns: top-level properties schema works",
   sr.other_file_columns({"properties": {"a": FQ, "b": FQ}}, ["a", "b"], R("s", "a", None)), ["b"])

# ---------------------------------------------------------------- parse_roles
print("# parse_roles")
C = ["sample", "fastq_1", "fastq_2", "extra"]
eq("parse_roles: sample, read1, read2", sr.parse_roles("sample=sample,read1=fastq_1,read2=fastq_2", C),
   R("sample", "fastq_1", "fastq_2"))
eq("parse_roles: read2 is optional", sr.parse_roles("sample=sample,read1=fastq_1", C), R("sample", "fastq_1", None))
eq("parse_roles: key order does not matter", sr.parse_roles("read2=fastq_2,read1=fastq_1,sample=sample", C),
   R("sample", "fastq_1", "fastq_2"))
eq("parse_roles: whitespace around keys, values and commas is trimmed",
   sr.parse_roles("  sample = extra ,  read1=fastq_1 , read2 =fastq_2 ", C), R("extra", "fastq_1", "fastq_2"))
eq("parse_roles: empty items (trailing / doubled comma) are ignored",
   sr.parse_roles(",sample=sample,,read1=fastq_1,", C), R("sample", "fastq_1", None))
eq("parse_roles: any requested column can take any role",
   sr.parse_roles("sample=fastq_2,read1=extra,read2=sample", C), R("fastq_2", "extra", "sample"))
eq("parse_roles: result is a Roles tuple", type(sr.parse_roles("sample=sample,read1=fastq_1", C)), R)
raises("parse_roles: an item without '=' is refused",
       lambda: sr.parse_roles("sample=sample,read1", C), "--roles entry is not role=column: read1")
raises("parse_roles: an unknown role is refused",
       lambda: sr.parse_roles("sample=sample,read1=fastq_1,read3=extra", C), "unknown role 'read3'", "sample, read1, read2")
raises("parse_roles: role names are case sensitive",
       lambda: sr.parse_roles("Sample=sample,read1=fastq_1", C), "unknown role 'Sample'")
raises("parse_roles: the same role twice is refused",
       lambda: sr.parse_roles("sample=sample,read1=fastq_1,read1=fastq_2", C), "read1 given more than once")
raises("parse_roles: sample twice is refused",
       lambda: sr.parse_roles("sample=sample,sample=extra,read1=fastq_1", C), "sample given more than once")
raises("parse_roles: a role with an empty column is refused",
       lambda: sr.parse_roles("sample=sample,read1=", C), "role read1 has no column", "read1=<column>")
raises("parse_roles: a role with a blank column is refused",
       lambda: sr.parse_roles("sample=  ,read1=fastq_1", C), "role sample has no column")
raises("parse_roles: sample missing", lambda: sr.parse_roles("read1=fastq_1", C), "missing sample")
raises("parse_roles: read1 missing", lambda: sr.parse_roles("sample=sample,read2=fastq_2", C), "missing read1")
raises("parse_roles: an empty spec is refused (sample is reported first)",
       lambda: sr.parse_roles("", C), "at least sample= and read1=", "missing sample")
raises("parse_roles: only commas is the same as empty", lambda: sr.parse_roles(" , ,", C), "missing sample")
raises("parse_roles: a column that was not requested is refused, naming it and the requested ones",
       lambda: sr.parse_roles("sample=sample,read1=nope", C), "read1=nope", "'nope' is not in the requested columns",
       "sample, fastq_1, fastq_2, extra")
raises("parse_roles: read2 naming an unrequested column is refused too",
       lambda: sr.parse_roles("sample=sample,read1=fastq_1,read2=nope", C), "read2=nope")
raises("parse_roles: one column for two roles is refused, naming both roles",
       lambda: sr.parse_roles("sample=sample,read1=sample", C), "column 'sample' for both sample and read1",
       "each role needs its own column")
raises("parse_roles: R2 on R1's column is refused (the old silent overwrite)",
       lambda: sr.parse_roles("sample=sample,read1=fastq_1,read2=fastq_1", C), "column 'fastq_1' for both read1 and read2")
raises("parse_roles: a value containing '=' keeps the rest and then fails the column check",
       lambda: sr.parse_roles("sample=a=b,read1=fastq_1", C), "'a=b' is not in the requested columns")
raises("parse_roles: the not-requested check comes before the same-column check",
       lambda: sr.parse_roles("sample=zzz,read1=zzz", C), "'zzz' is not in the requested columns")
raises("parse_roles: the missing-role check comes before the not-requested check",
       lambda: sr.parse_roles("sample=zzz", C), "missing read1")
eq("parse_roles: columns need not include unused ones", sr.parse_roles("sample=a,read1=b", ["a", "b"]), R("a", "b", None))

# ---------------------------------------------------------------- load_schema
print("# load_schema")
good = write("good.json", json.dumps({"items": {"properties": {"a": {}}}}))
eq("load_schema: a file holding an object", sr.load_schema(good), {"items": {"properties": {"a": {}}}})
raises("load_schema: a missing file -> ValueError naming the path",
       lambda: sr.load_schema(os.path.join(TMP, "absent.json")), "cannot read schema", "absent.json")
raises("load_schema: a directory -> ValueError", lambda: sr.load_schema(TMP), "cannot read schema")
raises("load_schema: invalid JSON -> ValueError", lambda: sr.load_schema(write("bad.json", "{not json")), "cannot read schema")
raises("load_schema: an empty file -> ValueError", lambda: sr.load_schema(write("empty.json", "")), "cannot read schema")
bad_utf8 = os.path.join(TMP, "latin.json")
with open(bad_utf8, "wb") as f:
    f.write(b'{"a": "\xff\xfe"}')
raises("load_schema: bytes that are not UTF-8 -> ValueError", lambda: sr.load_schema(bad_utf8), "cannot read schema")
raises("load_schema: a JSON array is not a schema",
       lambda: sr.load_schema(write("list.json", "[1, 2]")), "is not a JSON object", "list.json")
raises("load_schema: JSON null is not a schema", lambda: sr.load_schema(write("null.json", "null")), "is not a JSON object")
raises("load_schema: a JSON string is not a schema", lambda: sr.load_schema(write("str.json", '"x"')), "is not a JSON object")
eq("load_schema: unicode content survives",
   sr.load_schema(write("uni.json", json.dumps({"t": "樣本"}, ensure_ascii=False))), {"t": "樣本"})
real_stdin = sys.stdin
try:
    sys.stdin = io.StringIO('{"properties": {"s": {}}}')
    got = sr.load_schema("-")
finally:
    sys.stdin = real_stdin
eq("load_schema: '-' reads stdin", got, {"properties": {"s": {}}})
try:
    sys.stdin = io.StringIO("[]")
    raises("load_schema: '-' with a non-object -> ValueError naming '-'", lambda: sr.load_schema("-"), "schema - is not a JSON object")
finally:
    sys.stdin = real_stdin

# ---------------------------------------------------------------- main (CLI)
print("# main / CLI")
PAIRED_F = write("paired.json", json.dumps(PAIRED))
THREE_F = write("three.json", json.dumps(sheet(sample=SAMPLE, a=FQ, b=FQ, c=FQ)))
NOSAMPLE_F = write("nosample.json", json.dumps(sheet(id={"type": "string"}, fastq_1=FQ)))


def cli(*args, stdin=None):
    p = subprocess.run([sys.executable, "-I", TOOL, *args], input=stdin, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


rc, out, err = cli("--schema", PAIRED_F)
eq("main: paired schema -> exit 0", rc, 0)
eq("main: ... stdout is 'sample=.. read1=.. read2=..'", out, "sample=sample read1=fastq_1 read2=fastq_2\n")
eq("main: ... stderr is empty", err, "")
rc, out, err = cli("--schema", PAIRED_F, "--columns", "sample,fastq_1")
eq("main: single-end request -> no read2 field", (rc, out), (0, "sample=sample read1=fastq_1\n"))
rc, out, err = cli("--schema", PAIRED_F, "--columns", " fastq_2 , sample,, fastq_1 ")
eq("main: --columns tolerates spaces and empty items, schema order decides R1/R2",
   (rc, out), (0, "sample=sample read1=fastq_1 read2=fastq_2\n"))
rc, out, err = cli("--schema", PAIRED_F, "--columns", "")
eq("main: an empty --columns means every schema column", (rc, out), (0, "sample=sample read1=fastq_1 read2=fastq_2\n"))
rc, out, err = cli("--schema", PAIRED_F, "--columns", "sample,fastq_1,fastq_2,strandedness")
eq("main: non-role columns requested are not printed", out, "sample=sample read1=fastq_1 read2=fastq_2\n")
rc, out, err = cli("--schema", THREE_F)
eq("main: ambiguous reads -> exit 3", rc, 3)
eq("main: ... stdout is exactly the machine line", out, "needs-decision: role=reads candidates=a,b,c\n")
has("main: ... stderr starts with ERROR: and tells the next step", err, "ERROR: cannot tell which column holds R1 / R2",
    "--roles sample=<col>,read1=<col>,read2=<col>")
rc, out, err = cli("--schema", NOSAMPLE_F)
eq("main: no sample column -> exit 3 with the sample role", (rc, out), (3, "needs-decision: role=sample candidates=id\n"))
rc, out, err = cli("--schema", THREE_F, "--roles", "sample=sample,read1=a,read2=c")
eq("main: --roles skips inference (ambiguous schema, exit 0)", (rc, out), (0, "sample=sample read1=a read2=c\n"))
rc, out, err = cli("--schema", THREE_F, "--roles", "sample=sample,read1=b")
eq("main: --roles without read2 prints two fields", (rc, out), (0, "sample=sample read1=b\n"))
rc, out, err = cli("--schema", THREE_F, "--roles", "sample=sample,read1=a", "--columns", "sample,a")
eq("main: --roles are checked against --columns (ok)", (rc, out), (0, "sample=sample read1=a\n"))
rc, out, err = cli("--schema", THREE_F, "--roles", "sample=sample,read1=b", "--columns", "sample,a")
eq("main: --roles naming a column outside --columns -> exit 2", rc, 2)
eq("main: ... nothing on stdout", out, "")
has("main: ... stderr is 'ERROR: ' + the reason", err, "ERROR: --roles read1=b: 'b' is not in the requested columns")
rc, out, err = cli("--schema", THREE_F, "--roles", "sample=sample")
eq("main: --roles missing read1 -> exit 2", (rc, out), (2, ""))
rc, out, err = cli("--schema", THREE_F, "--roles", "sample=a,read1=a")
eq("main: --roles one column twice -> exit 2, no sheet", (rc, out), (2, ""))
rc, out, err = cli("--schema", PAIRED_F, "--roles", "")
eq("main: an empty --roles falls back to inference", (rc, out), (0, "sample=sample read1=fastq_1 read2=fastq_2\n"))
rc, out, err = cli("--schema", os.path.join(TMP, "absent.json"))
eq("main: missing schema file -> exit 2, nothing on stdout", (rc, out), (2, ""))
has("main: ... stderr names the file", err, "ERROR: cannot read schema", "absent.json")
rc, out, err = cli("--schema", write("arr.json", "[]"))
eq("main: schema that is not an object -> exit 2", (rc, out), (2, ""))
rc, out, err = cli()
eq("main: no --schema -> argparse exit 2", rc, 2)
has("main: ... usage on stderr", err, "--schema")
rc, out, err = cli("--schema", "-", stdin=json.dumps(PAIRED))
eq("main: --schema - reads stdin", (rc, out), (0, "sample=sample read1=fastq_1 read2=fastq_2\n"))
rc, out, err = cli("--schema", "-", stdin="not json")
eq("main: --schema - with bad JSON -> exit 2", (rc, out), (2, ""))
rc, out, err = cli("--schema", PAIRED_F, "--columns", ",")
eq("main: --columns of only commas -> no columns -> needs a decision (exit 3)",
   (rc, out), (3, "needs-decision: role=sample candidates=\n"))
rc, out, err = cli("--schema", os.path.join(FX, "rnaseq-3.27.0.json"))
eq("main: real schema rnaseq-3.27.0", (rc, out), (0, "sample=sample read1=fastq_1 read2=fastq_2\n"))
rc, out, err = cli("--schema", os.path.join(FX, "ampliseq-2.18.0.json"))
eq("main: real schema ampliseq-2.18.0 (four fastq columns) -> exit 3", rc, 3)
has("main: ... machine line lists them in schema order", out,
    "needs-decision: role=reads candidates=forwardReads,reverseReads,fastq_1,fastq_2")
rc, out, err = cli("--schema", PAIRED_F, "--roles", "sample=sample,read1=fastq_1,read2=fastq_2", "--columns",
                   "sample,fastq_1,fastq_2")
eq("main: --roles and --columns together", (rc, out), (0, "sample=sample read1=fastq_1 read2=fastq_2\n"))

# main() in-process: returns the code instead of exiting
real_out, real_err = sys.stdout, sys.stderr
try:
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    code = sr.main(["--schema", PAIRED_F])
    cap_out, cap_err = sys.stdout.getvalue(), sys.stderr.getvalue()
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    code3 = sr.main(["--schema", THREE_F])
    cap3_out = sys.stdout.getvalue()
finally:
    sys.stdout, sys.stderr = real_out, real_err
eq("main(argv): returns 0 and prints the roles line", (code, cap_out, cap_err), (0, "sample=sample read1=fastq_1 read2=fastq_2\n", ""))
eq("main(argv): returns 3 on a needs-decision", (code3, cap3_out), (3, "needs-decision: role=reads candidates=a,b,c\n"))

print()
print(f"{total - fails}/{total} cases ok")
sys.exit(1 if fails else 0)
PY
rc=$?
if [ "$rc" -eq 0 ]; then echo "schema_roles unit tests: all passed"; else echo "schema_roles unit tests: FAILED"; fi
exit "$rc"
