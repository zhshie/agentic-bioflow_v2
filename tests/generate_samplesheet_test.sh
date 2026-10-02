#!/bin/bash
# Feature 003, Stage S1 (tasks.md T002): the samplesheet tool takes its column
# roles (sample name, R1, R2) from the pipeline's own schema_input.json, or from
# the operator, and never from names it remembers. Covers TC-001..TC-013,
# TC-017, TC-018, TC-019 of specs/003-samplesheet-roles/test-case.md.
#
# Nothing existing: no test in this repo exercised the samplesheet tool at all
# before this feature (it had none), so this is a new, self-contained file.
#
# The schemas are the five real nf-core ones under tests/fixtures/schema_input/
# (pinned tags, see the README there). Synthetic schemas are used only for the
# shapes no real pipeline has on purpose (no id column, two id columns, ...).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TOOL="$ROOT/scripts/generate_samplesheet.py"
ROLES="$ROOT/scripts/utils/schema_roles.py"
FX="$HERE/fixtures/schema_input"
GOLD="$HERE/fixtures/samplesheet_golden"

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
n=0

t()   { printf '%-76s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has() { printf '%-76s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: nothing matching '$2' in: $3"; fails=$((fails+1)); }; }
lacks() { printf '%-76s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: unexpected '$2' in: $3"; fails=$((fails+1)); } || echo ok; }
ok_rc()   { printf '%-76s ' "$1"; [ "$2" -eq 0 ] && echo ok || { echo "FAIL: exit $2, wanted 0. stderr: $3"; fails=$((fails+1)); }; }

# run <args...> -> sets RC, ERR (stderr), OUT (stdout). Not wrapped in $(...)
# so the exit code lands in this shell.
run() {
    python3 "$TOOL" "$@" >"$TMP/stdout" 2>"$TMP/stderr"
    RC=$?
    OUT=$(cat "$TMP/stdout"); ERR=$(cat "$TMP/stderr")
}
# mktemp -u, not a counter: `o=$(newout)` runs in a subshell, so a counter bumped
# inside it never advances here and every case would share one file name.
newout() { mktemp -u "$TMP/out.XXXXXX.csv"; }

# A stop must: exit non-zero, write nothing, and say what to do next (TC-017).
stopped() {  # stopped <label> <outfile>
    printf '%-76s ' "$1: stops, writes nothing, says what to do"
    local bad=""
    [ "$RC" -ne 0 ] || bad="$bad exit-0"
    [ ! -e "$2" ] || bad="$bad file-written"
    [ -z "$OUT" ] || bad="$bad stdout-not-empty"
    grep -qE -- '--roles|--schema|--single-end' <<<"$ERR" || bad="$bad no-next-step"
    [ -n "$bad" ] && { echo "FAIL:$bad (rc=$RC) stderr: $ERR"; fails=$((fails+1)); } || echo ok
}

mkpairs() {  # mkpairs <dir> <prefix...> : paired Illumina-style files
    local d="$1"; shift
    mkdir -p "$d"
    for s in "$@"; do
        printf 'x\n' > "$d/${s}_R1_001.fastq.gz"
        printf 'x\n' > "$d/${s}_R2_001.fastq.gz"
    done
}

PAIRS="$TMP/pairs"; mkpairs "$PAIRS" S1 S2 S3

# ---------------------------------------------------------------- TC-001
# Golden captured from the tool BEFORE feature 003 (tasks.md T001). Paths are
# made machine-independent by replacing this run's temp dir with <TMP>.
# The golden's layout: <run dir>/reads/ holds the input, <run dir>/out.csv the output.
goldrun() {  # goldrun <tool args...> -> sets GR; input is built under $GR/reads
    GR=$(mktemp -d "$TMP/gr.XXXXXX")
    mkpairs "$GR/reads" S1 S2 S3; printf 'x\n' > "$GR/reads/S4_R2_001.fastq.gz"
    run "$GR/reads" "$@" --columns sample,fastq_1,fastq_2,strandedness,seq_platform,seq_center \
        --defaults strandedness=auto -o "$GR/out.csv"
}
goldrun --schema "$FX/rnaseq-3.27.0.json"
ok_rc "TC-001 rnaseq via --schema exits 0" "$RC" "$ERR"
t "TC-001 CSV is byte-identical to the pre-change golden" \
  "$(sed "s#$GR#<TMP>#g" "$GR/out.csv" | cksum)" "$(cksum < "$GOLD/rnaseq.csv")"
t "TC-001 warnings + summary are byte-identical to the pre-change golden" \
  "$(sed "s#$GR#<TMP>#g" "$TMP/stderr" | cksum)" "$(cksum < "$GOLD/rnaseq.stderr")"
goldrun --roles sample=sample,read1=fastq_1,read2=fastq_2
t "TC-001 same output when the operator names the same roles" \
  "$(sed "s#$GR#<TMP>#g" "$GR/out.csv" | cksum)" "$(cksum < "$GOLD/rnaseq.csv")"
t "TC-001 same warnings when the operator names the same roles" \
  "$(sed "s#$GR#<TMP>#g" "$TMP/stderr" | cksum)" "$(cksum < "$GOLD/rnaseq.stderr")"

# ---------------------------------------------------------------- TC-002
o=$(newout)
run "$PAIRS" --schema "$FX/ampliseq-2.18.0.json" --columns sampleID,forwardReads,reverseReads -o "$o"
ok_rc "TC-002 ampliseq (one column set) exits 0" "$RC" "$ERR"
t "TC-002 header is the requested columns" "$(sed -n 1p "$o")" "sampleID,forwardReads,reverseReads"
t "TC-002 sample name lands in sampleID" "$(sed -n 2p "$o" | cut -d, -f1)" "S1"
t "TC-002 R1 lands in forwardReads" "$(sed -n 2p "$o" | cut -d, -f2 | xargs basename)" "S1_R1_001.fastq.gz"
t "TC-002 R2 lands in reverseReads" "$(sed -n 2p "$o" | cut -d, -f3 | xargs basename)" "S1_R2_001.fastq.gz"
lacks "TC-002 no empty-column warning" "is empty for every sample" "$ERR"

# ---------------------------------------------------------------- TC-003
o=$(newout)
run "$PAIRS" --schema "$FX/taxprofiler-2.0.1.json" \
  --columns sample,run_accession,instrument_platform,fastq_1,fastq_2,fasta \
  --defaults run_accession=r1,instrument_platform=ILLUMINA -o "$o"
ok_rc "TC-003 taxprofiler (has a fasta column) exits 0" "$RC" "$ERR"
t "TC-003 R1 filled" "$(sed -n 2p "$o" | cut -d, -f4 | xargs basename)" "S1_R1_001.fastq.gz"
t "TC-003 R2 filled" "$(sed -n 2p "$o" | cut -d, -f5 | xargs basename)" "S1_R2_001.fastq.gz"
t "TC-003 fasta is not treated as a FASTQ column (left empty)" "$(sed -n 2p "$o" | cut -d, -f6)" ""
has "TC-003 fasta is named as needing the operator" "fasta" "$ERR"

# ---------------------------------------------------------------- TC-004..006
o=$(newout)
run "$PAIRS" --schema "$FX/ampliseq-2.18.0.json" \
  --columns sampleID,forwardReads,reverseReads,sample,fastq_1,fastq_2,run,control,quant_reading -o "$o"
t "TC-004 ampliseq with both column sets: exit 3" "$RC" "3"
t "TC-004 machine line lists the 4 candidates in schema order" \
  "$(grep '^needs-decision:' <<<"$ERR")" "needs-decision: role=reads candidates=forwardReads,reverseReads,fastq_1,fastq_2"
stopped "TC-004" "$o"

o=$(newout)
run "$PAIRS" --schema "$FX/mag-5.5.0.json" \
  --columns sample,run,group,short_reads_1,short_reads_2,short_reads_platform,long_reads,long_reads_platform -o "$o"
t "TC-005 mag: exit 3" "$RC" "3"
t "TC-005 machine line lists the 3 candidates" \
  "$(grep '^needs-decision:' <<<"$ERR")" "needs-decision: role=reads candidates=short_reads_1,short_reads_2,long_reads"
stopped "TC-005" "$o"

o=$(newout)
run "$PAIRS" --schema "$FX/bacass-2.6.1.json" --columns ID,R1,R2,LongFastQ,Fast5,GenomeSize -o "$o"
t "TC-006 bacass (rule inside anyOf): exit 3" "$RC" "3"
t "TC-006 machine line lists the 3 candidates (Fast5 is not one)" \
  "$(grep '^needs-decision:' <<<"$ERR")" "needs-decision: role=reads candidates=R1,R2,LongFastQ"
stopped "TC-006" "$o"

o=$(newout)
run "$PAIRS" --schema "$FX/bacass-2.6.1.json" --columns ID,R1,R2 -o "$o"
ok_rc "TC-006b bacass with only ID,R1,R2 is inferable (anyOf pattern read)" "$RC" "$ERR"
t "TC-006b ID gets the sample name" "$(sed -n 2p "$o" | cut -d, -f1)" "S1"
t "TC-006b R2 column gets the R2 file" "$(sed -n 2p "$o" | cut -d, -f3 | xargs basename)" "S1_R2_001.fastq.gz"

# ---------------------------------------------------------------- TC-007 / TC-008
cat > "$TMP/no_id.json" <<'EOF'
{"type":"array","items":{"type":"object","properties":{
 "name":{"type":"string"},
 "label":{"type":"string"},
 "r1":{"type":"string","pattern":"^\\S+\\.fastq\\.gz$"},
 "r2":{"type":"string","pattern":"^\\S+\\.fastq\\.gz$"}}}}
EOF
o=$(newout)
run "$PAIRS" --schema "$TMP/no_id.json" --columns name,label,r1,r2 -o "$o"
t "TC-007 no column marked as the sample name: exit 3" "$RC" "3"
t "TC-007 machine line offers the non-file columns" \
  "$(grep '^needs-decision:' <<<"$ERR")" "needs-decision: role=sample candidates=name,label"
stopped "TC-007" "$o"

cat > "$TMP/two_id.json" <<'EOF'
{"type":"array","items":{"type":"object","properties":{
 "a":{"type":"string","meta":["id"]},
 "b":{"type":"string","meta":"sample"},
 "r1":{"type":"string","pattern":"^\\S+\\.fastq\\.gz$"},
 "r2":{"type":"string","pattern":"^\\S+\\.fastq\\.gz$"}}}}
EOF
o=$(newout)
run "$PAIRS" --schema "$TMP/two_id.json" --columns a,b,r1,r2 -o "$o"
t "TC-008 two columns marked as the sample name: exit 3" "$RC" "3"
t "TC-008 machine line lists exactly those two" \
  "$(grep '^needs-decision:' <<<"$ERR")" "needs-decision: role=sample candidates=a,b"
stopped "TC-008" "$o"

# meta may be a bare string as well as a list; format: file-path alone is not FASTQ
cat > "$TMP/shapes.json" <<'EOF'
{"type":"array","items":{"type":"object","properties":{
 "who":{"type":"string","meta":"id"},
 "reads_a":{"type":"string","pattern":"^\\S+\\.fq\\.gz$"},
 "reads_b":{"type":"string","anyOf":[{"pattern":"^\\S+\\.fq\\.gz$"},{"maxLength":0}]},
 "table":{"type":"string","format":"file-path"}}}}
EOF
o=$(newout)
run "$PAIRS" --schema "$TMP/shapes.json" --columns who,reads_a,reads_b,table -o "$o"
ok_rc "TC-002b meta as a string, pattern in anyOf, bare file-path column" "$RC" "$ERR"
t "TC-002b sample in the string-meta column" "$(sed -n 2p "$o" | cut -d, -f1)" "S1"
t "TC-002b a file-path column with no FASTQ pattern is not a read column" "$(sed -n 2p "$o" | cut -d, -f4)" ""
has "TC-002b ...and is named as needing the operator" "table" "$ERR"

# ---------------------------------------------------------------- TC-009 / TC-010 / TC-011
o=$(newout)
run "$PAIRS" --schema "$FX/mag-5.5.0.json" --roles sample=sample,read1=short_reads_1,read2=short_reads_2 \
  --columns sample,run,group,short_reads_1,short_reads_2,short_reads_platform,long_reads \
  --defaults run=1,group=g,short_reads_platform=ILLUMINA -o "$o"
ok_rc "TC-009 mag with the operator's roles exits 0" "$RC" "$ERR"
t "TC-009 sample" "$(sed -n 2p "$o" | cut -d, -f1)" "S1"
t "TC-009 short_reads_1 gets R1" "$(sed -n 2p "$o" | cut -d, -f4 | xargs basename)" "S1_R1_001.fastq.gz"
t "TC-009 short_reads_2 gets R2" "$(sed -n 2p "$o" | cut -d, -f5 | xargs basename)" "S1_R2_001.fastq.gz"
t "TC-009 long_reads stays empty" "$(sed -n 2p "$o" | cut -d, -f7)" ""
has "TC-009 long_reads is named as needing the operator" "long_reads" "$ERR"

o=$(newout)
run "$PAIRS" --roles sample=sample,read1=nosuchcol,read2=fastq_2 --columns sample,fastq_1,fastq_2 -o "$o"
t "TC-010 role naming a column that is not requested: exit 2" "$RC" "2"
has "TC-010 message names the bad column" "nosuchcol" "$ERR"
has "TC-010 message says it is not among the requested columns" "not in" "$ERR"
stopped "TC-010" "$o"

o=$(newout)
run "$PAIRS" --columns sample,fastq_1,fastq_2 -o "$o"
t "TC-011 no schema, no roles, rnaseq-looking names: exit 2" "$RC" "2"
has "TC-011 asks for a schema or roles" "--schema" "$ERR"
stopped "TC-011" "$o"

# ---------------------------------------------------------------- TC-012
cat > "$TMP/single.json" <<'EOF'
{"type":"array","items":{"type":"object","properties":{
 "id":{"type":"string","meta":["id"]},
 "reads":{"type":"string","pattern":"^\\S+\\.fastq\\.gz$"}}}}
EOF
SE="$TMP/se"; mkdir -p "$SE"; printf 'x\n' > "$SE/A_R1_001.fastq.gz"; printf 'x\n' > "$SE/B_R1_001.fastq.gz"
o=$(newout)
run "$SE" --schema "$TMP/single.json" --columns id,reads -o "$o"
t "TC-012 one reads column, files unpaired, not declared single-end: exit 1" "$RC" "1"
has "TC-012 asks whether the library is single-end" "--single-end" "$ERR"
t "TC-012 nothing written" "$([ -e "$o" ] && echo yes || echo no)" "no"
o=$(newout)
run "$SE" --schema "$TMP/single.json" --columns id,reads --single-end -o "$o"
ok_rc "TC-012 with --single-end it is written" "$RC" "$ERR"
t "TC-012 sample in id" "$(sed -n 2p "$o" | cut -d, -f1)" "A"
t "TC-012 read in the single reads column" "$(sed -n 2p "$o" | cut -d, -f2 | xargs basename)" "A_R1_001.fastq.gz"

# ---------------------------------------------------------------- TC-013
o=$(newout)
run "$PAIRS" --schema "$FX/rnaseq-3.27.0.json" --columns sample,fastq_1,fastq_2,strandedness,genome_bam,transcriptome_bam \
  --defaults strandedness=auto -o "$o"
ok_rc "TC-013 other file columns requested: still exits 0" "$RC" "$ERR"
t "TC-013 genome_bam left empty" "$(sed -n 2p "$o" | cut -d, -f5)" ""
t "TC-013 transcriptome_bam left empty" "$(sed -n 2p "$o" | cut -d, -f6)" ""
has "TC-013 genome_bam named" "genome_bam" "$ERR"
has "TC-013 transcriptome_bam named" "transcriptome_bam" "$ERR"
t "TC-013 named in ONE warning" "$(grep -c 'transcriptome_bam' <<<"$(grep -v 'is empty for every sample' <<<"$ERR")")" "1"

# --schema alone: columns default to the schema's own order
o=$(newout)
run "$PAIRS" --schema "$FX/rnaseq-3.27.0.json" -o "$o"
ok_rc "TC-002c --schema without --columns exits 0" "$RC" "$ERR"
t "TC-002c header starts with the schema's own column order" "$(sed -n 1p "$o" | cut -d, -f1-4)" "sample,fastq_1,fastq_2,strandedness"

# ---------------------------------------------------------------- TC-019
CT="$TMP/cond"; mkpairs "$CT" ctrl_A treat_B
cat > "$TMP/cond.json" <<'EOF'
{"type":"array","items":{"type":"object","properties":{
 "sample":{"type":"string","meta":["id"]},
 "condition":{"type":"string","meta":["condition"]},
 "fastq_1":{"type":"string","pattern":"^\\S+\\.fastq\\.gz$"},
 "fastq_2":{"type":"string","pattern":"^\\S+\\.fastq\\.gz$"}}}}
EOF
o=$(newout)
run "$CT" --schema "$TMP/cond.json" -o "$o"
ok_rc "TC-019 files named ctrl_/treat_: exits 0" "$RC" "$ERR"
t "TC-019 condition column is empty for ctrl_A" "$(sed -n 2p "$o" | cut -d, -f2)" ""
t "TC-019 condition column is empty for treat_B" "$(sed -n 3p "$o" | cut -d, -f2)" ""
has "TC-019 the empty condition column is flagged" "column 'condition' is empty" "$ERR"

# ---------------------------------------------------------------- schema_roles.py CLI
out=$(python3 "$ROLES" --schema "$FX/ampliseq-2.18.0.json" --columns sampleID,forwardReads,reverseReads 2>&1); rc=$?
t "roles CLI: inferable schema exits 0" "$rc" "0"
t "roles CLI: prints the three roles" "$out" "sample=sampleID read1=forwardReads read2=reverseReads"
out=$(python3 "$ROLES" --schema "$FX/mag-5.5.0.json" --columns sample,short_reads_1,short_reads_2,long_reads 2>&1); rc=$?
t "roles CLI: ambiguous schema exits 3" "$rc" "3"
has "roles CLI: prints the needs-decision line" "needs-decision: role=reads candidates=short_reads_1,short_reads_2,long_reads" "$out"
out=$(python3 "$ROLES" --schema - --columns sampleID,forwardReads,reverseReads < "$FX/ampliseq-2.18.0.json" 2>&1)
t "roles CLI: schema on stdin" "$out" "sample=sampleID read1=forwardReads read2=reverseReads"

# ---------------------------------------------------------------- TC-018
out=$(bash "$HERE/scripts_name_their_alternative.sh" 2>&1); rc=$?
t "TC-018 every script still names the tool it is not (incl. schema_roles.py)" "$rc" "0"
for f in "$TOOL" "$ROLES"; do
    printf '%-76s ' "TC-018 $(basename "$f") names its alternative in the first 40 lines"
    if [ -f "$f" ] && sed -n '1,40p' "$f" | grep -qE '^#[[:space:]]*(Not[[:space:]]+.+:|Nothing existing:)'; then echo ok
    else echo "FAIL: missing or no header line"; fails=$((fails+1)); fi
done

echo
if [ "$fails" -eq 0 ]; then echo "all passed"; else echo "$fails failed"; exit 1; fi
