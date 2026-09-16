#!/bin/bash
# scripts/input_checksums.sh - proposal R4 (docs/LAB_AGENTS.md section A3):
# prefer an existing checksum over recomputing one, because the files this
# script hashes can run tens of gigabytes.
#
# The load-bearing property this file exists to prove is negative: a file
# --known already covers must NEVER be handed to a hashing tool. Case A
# proves it structurally rather than by inspection - a stub `sha256sum` that
# errors the moment it is actually invoked sits first on PATH throughout that
# case, so any regression that starts recomputing a known value turns into a
# hard failure (exit 2, no output written) rather than a value that merely
# looks right.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/input_checksums.sh"
BASH_BIN="$(command -v bash)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t()  { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2'"; echo "   <<$3>>"; fails=$((fails+1)); }; }
tn() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: has '$2'"; fails=$((fails+1)); } || echo ok; }
eq() { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

sha256_of() { python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$1"; }

echo "--- A: known values are reused, never recomputed; missing is exit 1 with everything else written; URL is not-local"
SDIR_A="$TMP/caseA"; mkdir -p "$SDIR_A/data"
printf 'R1 content\n' > "$SDIR_A/data/s1_R1.fastq.gz"
printf 'R2 content\n' > "$SDIR_A/data/s1_R2.fastq.gz"
R1_HEX=$(sha256_of "$SDIR_A/data/s1_R1.fastq.gz")
R2_HEX=$(sha256_of "$SDIR_A/data/s1_R2.fastq.gz")

cat > "$SDIR_A/samplesheet.csv" <<CSV
sample,fastq_1,fastq_2,strandedness
s1,data/s1_R1.fastq.gz,data/s1_R2.fastq.gz,auto
s2,data/s2_R1_missing.fastq.gz,,auto
s3,s3://a-bucket/s3_R1.fastq.gz,,auto
CSV

# R1 is matched by absolute path. R2 is DELIBERATELY given a wrong directory
# in --known (same basename, correct hash) so the run also exercises the
# basename fallback, not just the path match.
cat > "$SDIR_A/known.sha256" <<KNOWN
$R1_HEX  $SDIR_A/data/s1_R1.fastq.gz
$R2_HEX  /nowhere/not-the-real-dir/s1_R2.fastq.gz
KNOWN

STUBBIN="$TMP/failing_sha256sum"; mkdir -p "$STUBBIN"
cat > "$STUBBIN/sha256sum" <<'EOF'
#!/bin/bash
echo "sha256sum stub: called for $*  -  a known value was recomputed" >&2
exit 1
EOF
chmod +x "$STUBBIN/sha256sum"

OUT_A="$SDIR_A/checksums.sha256"
out=$(PATH="$STUBBIN:$PATH" "$BASH_BIN" "$SCRIPT" \
        --samplesheet "$SDIR_A/samplesheet.csv" --out "$OUT_A" \
        --known "$SDIR_A/known.sha256" 2>&1)
rc=$?

eq  "exits 1 (s2 missing) rather than 2 (stub never had to run)" "$rc" "1"
tn  "the failing stub was never actually invoked"          "a known value was recomputed" "$out"
t   "one sentence explains a missing input, at the end"     "missing" "$out"

[ -f "$OUT_A" ] || { echo "FAIL: $OUT_A was not written"; fails=$((fails+1)); }
sha_out=$(cat "$OUT_A" 2>/dev/null)
t "out file: s1 R1's known hash, reused verbatim"   "$R1_HEX  data/s1_R1.fastq.gz" "$sha_out"
t "out file: s1 R2's known hash, reused verbatim"   "$R2_HEX  data/s1_R2.fastq.gz" "$sha_out"
tn "out file: the missing s2 path is not in the checksum file" "s2_R1_missing" "$sha_out"
tn "out file: the not-local s3 URL is not in the checksum file" "s3_R1" "$sha_out"

src_out=$(cat "${OUT_A}.sources.tsv" 2>/dev/null)
t "sources.tsv: s1 R1 is source=known"    "$(printf 'data/s1_R1.fastq.gz\t%s\tknown' "$(stat -c %s "$SDIR_A/data/s1_R1.fastq.gz" 2>/dev/null || stat -f %z "$SDIR_A/data/s1_R1.fastq.gz")")" "$src_out"
t "sources.tsv: s1 R2 is source=known-by-name (a basename match is weaker)"   "$(printf 'data/s1_R2.fastq.gz\t%s\tknown-by-name' "$(stat -c %s "$SDIR_A/data/s1_R2.fastq.gz" 2>/dev/null || stat -f %z "$SDIR_A/data/s1_R2.fastq.gz")")" "$src_out"
t "sources.tsv: s2 is source=missing"     "$(printf 'data/s2_R1_missing.fastq.gz\t-\tmissing')" "$src_out"
t "sources.tsv: s3 is source=not-local"   "$(printf 's3://a-bucket/s3_R1.fastq.gz\t-\tnot-local')" "$src_out"
t "the basename-only match is flagged on stderr" "matched-by-name" "$out"
tn "sources.tsv: the path-matched s1 R1 is not marked by-name" "$(printf 'data/s1_R1.fastq.gz\t%s\tknown-by-name' "$(stat -c %s "$SDIR_A/data/s1_R1.fastq.gz" 2>/dev/null || stat -f %z "$SDIR_A/data/s1_R1.fastq.gz")")" "$src_out"

echo
echo "--- B: a value with no --known coverage is computed, and matches a precomputed hash"
SDIR_B="$TMP/caseB"; mkdir -p "$SDIR_B/data"
printf 'hello world, compute me\n' > "$SDIR_B/data/x_R1.fastq.gz"
EXPECT_B=$(sha256_of "$SDIR_B/data/x_R1.fastq.gz")
cat > "$SDIR_B/samplesheet.csv" <<CSV
sample,fastq_1
x,data/x_R1.fastq.gz
CSV
OUT_B="$SDIR_B/out.sha256"
outB=$("$BASH_BIN" "$SCRIPT" --samplesheet "$SDIR_B/samplesheet.csv" --out "$OUT_B" 2>&1)
rcB=$?
eq "case B exits 0" "$rcB" "0"
t  "case B: the computed hash matches an independent precomputed hash" \
   "$EXPECT_B  data/x_R1.fastq.gz" "$(cat "$OUT_B")"
t  "case B: sources.tsv marks it computed, not known" \
   "$(printf 'data/x_R1.fastq.gz\t')" "$(cat "${OUT_B}.sources.tsv")"
grep -q "computed$" "${OUT_B}.sources.tsv" \
  && { printf '%-64s ok\n' "case B: source column reads computed"; } \
  || { printf '%-64s FAIL\n' "case B: source column reads computed"; fails=$((fails+1)); }

echo
echo "--- C: the output verifies with sha256sum -c / shasum -c from the samplesheet's own directory"
if command -v sha256sum >/dev/null 2>&1; then
    verify=$(cd "$SDIR_B" && sha256sum -c "$(basename "$OUT_B")" 2>&1); vrc=$?
elif command -v shasum >/dev/null 2>&1; then
    verify=$(cd "$SDIR_B" && shasum -a 256 -c "$(basename "$OUT_B")" 2>&1); vrc=$?
else
    verify="(no sha256sum/shasum on this machine to verify with)"; vrc=0
fi
printf '%-64s ' "sha256sum -c / shasum -c from the sheet's directory succeeds"
[ "$vrc" = 0 ] && echo ok || { echo "FAIL: rc=$vrc <<$verify>>"; fails=$((fails+1)); }

echo
echo "--- D: --force behaviour"
SDIR_E="$TMP/caseE"; mkdir -p "$SDIR_E/data"
printf 'force test\n' > "$SDIR_E/data/f_R1.fastq.gz"
cat > "$SDIR_E/samplesheet.csv" <<CSV
sample,fastq_1
f,data/f_R1.fastq.gz
CSV
OUT_E="$SDIR_E/out.sha256"
"$BASH_BIN" "$SCRIPT" --samplesheet "$SDIR_E/samplesheet.csv" --out "$OUT_E" >/dev/null 2>&1
first_sum=$(cat "$OUT_E")

out2=$("$BASH_BIN" "$SCRIPT" --samplesheet "$SDIR_E/samplesheet.csv" --out "$OUT_E" 2>&1)
rc2=$?
eq "a second run without --force exits 2"  "$rc2" "2"
t  "...and explains why"                   "--force" "$out2"
second_sum=$(cat "$OUT_E")
eq "...and leaves the existing file untouched" "$first_sum" "$second_sum"

out3=$("$BASH_BIN" "$SCRIPT" --samplesheet "$SDIR_E/samplesheet.csv" --out "$OUT_E" --force 2>&1)
rc3=$?
eq "a run WITH --force succeeds"           "$rc3" "0"

echo
echo "--- E: bad usage exits 2, not a crash"
eq "no arguments at all"                "$("$BASH_BIN" "$SCRIPT" >/dev/null 2>&1; echo $?)" "2"
eq "missing --out"                      "$("$BASH_BIN" "$SCRIPT" --samplesheet "$SDIR_B/samplesheet.csv" >/dev/null 2>&1; echo $?)" "2"
eq "unreadable samplesheet"             "$("$BASH_BIN" "$SCRIPT" --samplesheet "$TMP/does-not-exist.csv" --out "$TMP/o1" >/dev/null 2>&1; echo $?)" "2"

echo
echo "--- F: the macOS fallback path - PATH carries shasum but not sha256sum"
FAKEBIN="$TMP/fakebin_macos"; mkdir -p "$FAKEBIN"
for tool in dirname basename awk python3 mv stat readlink tr mktemp; do
    real="$(command -v "$tool" 2>/dev/null)" || continue
    ln -sf "$real" "$FAKEBIN/$tool"
done
cat > "$FAKEBIN/shasum" <<'EOF'
#!/bin/bash
# Minimal `shasum -a 256 -- <path>` that computes a real digest, so this
# proves the fallback path produces a CORRECT value, not merely that it runs.
path=""
while [ $# -gt 0 ]; do
    case "$1" in
        -a) shift 2 ;;
        --) shift; path="$1"; shift ;;
        *)  path="$1"; shift ;;
    esac
done
python3 - "$path" <<'PY'
import hashlib, sys
h = hashlib.sha256()
with open(sys.argv[1], "rb") as f:
    for chunk in iter(lambda: f.read(65536), b""):
        h.update(chunk)
print(h.hexdigest() + "  " + sys.argv[1])
PY
EOF
chmod +x "$FAKEBIN/shasum"

printf '%-64s ' "fixture: sha256sum is genuinely absent from the fallback PATH"
[ -z "$(PATH="$FAKEBIN" sh -c 'command -v sha256sum' 2>/dev/null)" ] && echo ok \
  || { echo "FAIL: sha256sum is still reachable - test fixture is broken"; fails=$((fails+1)); }

SDIR_G="$TMP/caseG"; mkdir -p "$SDIR_G/data"
printf 'macos fallback content\n' > "$SDIR_G/data/m_R1.fastq.gz"
EXPECT_G=$(sha256_of "$SDIR_G/data/m_R1.fastq.gz")
cat > "$SDIR_G/samplesheet.csv" <<CSV
sample,fastq_1
m,data/m_R1.fastq.gz
CSV
OUT_G="$SDIR_G/out.sha256"
outG=$(PATH="$FAKEBIN" "$BASH_BIN" "$SCRIPT" \
         --samplesheet "$SDIR_G/samplesheet.csv" --out "$OUT_G" 2>&1)
rcG=$?
eq "macOS-fallback run exits 0"            "$rcG" "0"
t  "macOS-fallback: the hash is correct"   "$EXPECT_G  data/m_R1.fastq.gz" "$(cat "$OUT_G" 2>/dev/null)"

echo
echo "--- H: no working Python on this machine - the Windows case (PITFALLS 20c)"
# python3, python and py all shadowed by stubs that fail - the shape of a Git
# Bash PATH whose only "python" is the unusable Microsoft Store stub.
NOPY="$TMP/nopy_bin"; mkdir -p "$NOPY"
for name in python3 python py; do
    printf '#!/bin/bash\nexit 49\n' > "$NOPY/$name"
    chmod +x "$NOPY/$name"
done
SDIR_H="$TMP/caseH"; mkdir -p "$SDIR_H/data"
printf 'content\n' > "$SDIR_H/data/h_R1.fastq.gz"
printf 'sample,fastq_1\nh,data/h_R1.fastq.gz\n' > "$SDIR_H/samplesheet.csv"
outH=$(PATH="$NOPY:$PATH" "$BASH_BIN" "$SCRIPT" \
         --samplesheet "$SDIR_H/samplesheet.csv" --out "$SDIR_H/out.sha256" 2>&1)
rcH=$?
eq "no working python exits 2"                     "$rcH" "2"
t  "...and says no working Python on this machine" "no working Python on this machine" "$outH"
t  "...and names what was tried"                   "python3" "$outH"
tn "...and never blames the shell"                  "this shell is unsupported" "$outH"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
