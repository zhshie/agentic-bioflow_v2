#!/bin/bash
# cloud-burn T3: scripts/utils/file_discovery.py keeps exactly what has a caller.
# discover_files (used by generate_samplesheet.py) and count_files_by_type are
# tested here; find_index_file and detect_input_type had no caller anywhere and
# are gone, which the last two cases hold.
#
# Nothing existing: no test named this module before; generate_samplesheet_test.sh
# reaches discover_files only indirectly and never count_files_by_type.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
UTILS="$ROOT/scripts/utils"

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t() { printf '%-76s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

# py <code> -> stdout of python3 with scripts/utils importable as a flat module
py() { PYTHONPATH="$UTILS" python3 -c "$1" 2>&1; }

D="$TMP/data"
mkdir -p "$D/a/deep" "$D/b" "$TMP/empty"
: > "$D/a/s1_R1.fastq.gz"; : > "$D/a/s1_R2.fq.gz"
printf 'ACGT' > "$D/a/deep/s2.FASTQ"
: > "$D/b/s3.fq"
: > "$D/b/x.bam"; : > "$D/b/y.bam"; : > "$D/b/z.cram"
: > "$D/b/notes.txt"; : > "$D/b/x.bam.bai"

# --- discover_files
t "discover fastq: all four spellings, recursive, sorted by full path" \
  "$(py "import file_discovery as f; print(','.join(x.name for x in f.discover_files('$D','fastq')))")" \
  "s2.FASTQ,s1_R1.fastq.gz,s1_R2.fq.gz,s3.fq"
t "discover default type is fastq" \
  "$(py "import file_discovery as f; print(len(f.discover_files('$D')))")" "4"
t "discover bam ignores .bai index and other files" \
  "$(py "import file_discovery as f; print(','.join(x.name for x in f.discover_files('$D','bam')))")" "x.bam,y.bam"
t "discover cram" \
  "$(py "import file_discovery as f; print(','.join(x.name for x in f.discover_files('$D','cram')))")" "z.cram"
t "FileInfo: stem strips the matched extension, case kept" \
  "$(py "import file_discovery as f; r=f.discover_files('$D','fastq'); print(r[0].stem, r[1].stem, r[2].stem, r[0].extension, r[1].extension)")" \
  "s2 s1_R1 s1_R2 .fastq .fastq.gz"
t "FileInfo: size and file_type" \
  "$(py "import file_discovery as f; r=f.discover_files('$D','fastq'); print(r[0].size, r[0].file_type)")" "4 fastq"
t "discover: symlink to an already-seen file is not listed twice" \
  "$(ln -s "$D/a/s1_R1.fastq.gz" "$D/b/link.fastq.gz"; py "import file_discovery as f; print(len(f.discover_files('$D','fastq')))")" "4"
t "discover: follow_symlinks=False does not descend into a linked directory" \
  "$(mkdir -p "$TMP/ext"; : > "$TMP/ext/e.fastq"; ln -s "$TMP/ext" "$D/extlink"
     py "import file_discovery as f; print(len(f.discover_files('$D','fastq',follow_symlinks=False)), len(f.discover_files('$D','fastq',follow_symlinks=True)))")" \
  "4 5"
t "discover: empty directory gives an empty list" \
  "$(py "import file_discovery as f; print(f.discover_files('$TMP/empty'))")" "[]"
t "discover: unknown type raises ValueError naming the type" \
  "$(py "import file_discovery as f
try: f.discover_files('$D','vcf')
except ValueError as e: print('ValueError', 'vcf' in str(e))")" "ValueError True"
t "discover: not a directory raises ValueError" \
  "$(py "import file_discovery as f
try: f.discover_files('$D/b/x.bam')
except ValueError as e: print('ValueError')")" "ValueError"

# --- count_files_by_type
rm -f "$D/b/link.fastq.gz" "$D/extlink"
t "count: one entry per supported type" \
  "$(py "import file_discovery as f; print(f.count_files_by_type('$D'))")" \
  "{'fastq': 4, 'bam': 2, 'cram': 1}"
t "count: empty directory is all zeros" \
  "$(py "import file_discovery as f; print(f.count_files_by_type('$TMP/empty'))")" \
  "{'fastq': 0, 'bam': 0, 'cram': 0}"
t "count: a missing directory is zeros, not an exception" \
  "$(py "import file_discovery as f; print(f.count_files_by_type('$TMP/nope'))")" \
  "{'fastq': 0, 'bam': 0, 'cram': 0}"

# --- dead code stays gone
t "find_index_file is not defined (no caller)" \
  "$(py "import file_discovery as f; print(hasattr(f,'find_index_file'))")" "False"
t "detect_input_type is not defined (no caller)" \
  "$(py "import file_discovery as f; print(hasattr(f,'detect_input_type'))")" "False"

[ "$fails" -eq 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
