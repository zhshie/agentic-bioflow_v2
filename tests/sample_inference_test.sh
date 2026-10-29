#!/bin/bash
# Sample-name inference and R1/R2 pairing from filenames
# (specs/sample-inference-mate-token-pairing, TC-001..TC-019).
#
# Nothing existing: tests/generate_samplesheet_test.sh only uses the `_R1_001` form of filename (mkpairs); no test checked
# `_R1.fastq.gz`, `_1.fastq.gz`, or sample names that contain digits, so this is a new file.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fails=0

t() { printf '%-72s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

# py <names...> : prints one line per key "key|sample|r1base|r2base" sorted; None when absent.
py() {
    python3 - "$ROOT/scripts" "$@" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1])
from utils.sample_inference import match_read_pairs, SAMPLE_KEY
files = ["/d/" + n for n in sys.argv[2:]]
b = lambda p: os.path.basename(p) if p else "None"
pairs = match_read_pairs(files)
for k in sorted(pairs):
    v = pairs[k]
    print("%s|%s|%s|%s" % (k, v["info"][SAMPLE_KEY], b(v["r1"]), b(v["r2"])))
PY
}
# count lines
n() { printf '%s\n' "$1" | grep -c . ; }

r=$(py S1_R1.fastq.gz S1_R2.fastq.gz)
t "TC-001 S1_R1/S1_R2 one pair" "$r" "S1|S1|S1_R1.fastq.gz|S1_R2.fastq.gz"
r=$(py S1_1.fastq.gz S1_2.fastq.gz)
t "TC-002 S1_1/S1_2 one pair" "$r" "S1|S1|S1_1.fastq.gz|S1_2.fastq.gz"
r=$(py x.R1.fastq.gz x.R2.fastq.gz)
t "TC-003 x.R1/x.R2 one pair" "$r" "x|x|x.R1.fastq.gz|x.R2.fastq.gz"

r=$(py Patient_1_Tumor_R1.fastq.gz Patient_1_Tumor_R2.fastq.gz Patient_2_Tumor_R1.fastq.gz Patient_2_Tumor_R2.fastq.gz)
t "TC-004 two patients kept apart (R1/R2)" "$r" "Patient_1_Tumor|Patient_1_Tumor|Patient_1_Tumor_R1.fastq.gz|Patient_1_Tumor_R2.fastq.gz
Patient_2_Tumor|Patient_2_Tumor|Patient_2_Tumor_R1.fastq.gz|Patient_2_Tumor_R2.fastq.gz"
r=$(py Patient_1_Tumor_1.fastq.gz Patient_1_Tumor_2.fastq.gz)
t "TC-005 Patient_1_Tumor_1/_2 one pair, _2 is R2" "$r" "Patient_1_Tumor|Patient_1_Tumor|Patient_1_Tumor_1.fastq.gz|Patient_1_Tumor_2.fastq.gz"
r=$(py Patient_1_Tumor_1.fastq.gz Patient_1_Tumor_2.fastq.gz Patient_2_Tumor_1.fastq.gz Patient_2_Tumor_2.fastq.gz)
t "TC-006 two patients kept apart (_1/_2)" "$r" "Patient_1_Tumor|Patient_1_Tumor|Patient_1_Tumor_1.fastq.gz|Patient_1_Tumor_2.fastq.gz
Patient_2_Tumor|Patient_2_Tumor|Patient_2_Tumor_1.fastq.gz|Patient_2_Tumor_2.fastq.gz"
r=$(py A_2_x_1.fastq.gz A_2_x_2.fastq.gz)
t "TC-007 A_2_x_1/_2 one pair" "$r" "A_2_x|A_2_x|A_2_x_1.fastq.gz|A_2_x_2.fastq.gz"
r=$(py Sample_1_S1_L001_R1_001.fastq.gz Sample_1_S1_L001_R2_001.fastq.gz Sample_2_S2_L001_R1_001.fastq.gz Sample_2_S2_L001_R2_001.fastq.gz)
t "TC-008 Illumina names with digits not collapsed" "$r" "Sample_1_S1|Sample_1_S1|Sample_1_S1_L001_R1_001.fastq.gz|Sample_1_S1_L001_R2_001.fastq.gz
Sample_2_S2|Sample_2_S2|Sample_2_S2_L001_R1_001.fastq.gz|Sample_2_S2_L001_R2_001.fastq.gz"

# TC-009: every input file appears exactly once in the output
cnt() { py "$@" | awk -F'|' '{ for(i=3;i<=4;i++) if($i!="None") c++ } END{print c+0}'; }
t "TC-009 no file lost (patients R)" "$(cnt Patient_1_Tumor_R1.fastq.gz Patient_1_Tumor_R2.fastq.gz Patient_2_Tumor_R1.fastq.gz Patient_2_Tumor_R2.fastq.gz)" 4
t "TC-009 no file lost (patients _1/_2)" "$(cnt Patient_1_Tumor_1.fastq.gz Patient_1_Tumor_2.fastq.gz Patient_2_Tumor_1.fastq.gz Patient_2_Tumor_2.fastq.gz)" 4
t "TC-009 no file lost (illumina digits)" "$(cnt Sample_1_S1_L001_R1_001.fastq.gz Sample_1_S1_L001_R2_001.fastq.gz Sample_2_S2_L001_R1_001.fastq.gz Sample_2_S2_L001_R2_001.fastq.gz)" 4

# Controls: already worked before the fix
r=$(py S1_R1_001.fastq.gz S1_R2_001.fastq.gz)
t "TC-010 _R1_001 pair" "$r" "S1|S1|S1_R1_001.fastq.gz|S1_R2_001.fastq.gz"
r=$(py S1_L002_R1_001.fastq.gz S1_L002_R2_001.fastq.gz)
t "TC-011 lane key" "$r" "S1_L002|S1|S1_L002_R1_001.fastq.gz|S1_L002_R2_001.fastq.gz"
r=$(py S1_L001_R1_001.fastq.gz S1_L001_R2_001.fastq.gz S1_L002_R1_001.fastq.gz S1_L002_R2_001.fastq.gz)
t "TC-012 multi-lane not merged" "$r" "S1|S1|S1_L001_R1_001.fastq.gz|S1_L001_R2_001.fastq.gz
S1_L002|S1|S1_L002_R1_001.fastq.gz|S1_L002_R2_001.fastq.gz"
r=$(py S1_S1_L001_R1_001.fastq.gz S1_S1_L001_R2_001.fastq.gz)
t "TC-013 S1_S1 lane name" "$r" "S1_S1|S1_S1|S1_S1_L001_R1_001.fastq.gz|S1_S1_L001_R2_001.fastq.gz"

# Safety net
r=$(py S1_R2.fastq.gz)
t "TC-016 lone R2 keeps r1 None" "$r" "S1|S1|None|S1_R2.fastq.gz"

# Not in scope
r=$(py S1_R1.fastq.gz S1_R1.fq.gz)
t "TC-018 duplicate R1 overwrite unchanged" "$r" "S1|S1|S1_R1.fq.gz|None"
r=$(py S1-R1.fastq.gz S1-R2.fastq.gz)
t "TC-019 hyphen marker not newly paired" "$(grep -c -v 'None' <<<"$r")" 0

# TC-020: header
t "TC-020 Nothing existing header" "$(head -40 "${BASH_SOURCE[0]}" | grep -cE '^# Nothing existing: .{15,}')" 1

[ "$fails" -eq 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
