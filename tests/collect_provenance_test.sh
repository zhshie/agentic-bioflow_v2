#!/bin/bash
# Tests for scripts/collect_provenance.py.
#
# The thing worth testing here is not that it reads a file - it is that it
# reads files whose names nobody agreed on. Measured across three real runs on
# one cluster, the versions file is called software_versions.yml,
# nf_core_<pipeline>_software_mqc_versions.yml, or collated_versions.yml; the
# quality report sits at the top of the tree in one and under the aligner's
# name in another. A lookup table would have been wrong twice and would go
# wrong again on the next template.
#
# The other one is the retry. A run that failed and resumed leaves the first
# attempt's report and a 154-byte trace beside the real ones. Sorted
# alphabetically the corpse comes first, and nothing about the output would
# look wrong.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/collect_provenance.py"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

ok() { printf '%-62s ok\n' "$1"; }
no() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
has() { grep -qF -- "$2" <<<"$1"; }

# A run, built to order: <dir> <versions-filename> <qc-subpath>
mkrun() {
  local d="$1" vname="$2" qc="$3"
  mkdir -p "$d/results/pipeline_info" "$d/results/$(dirname "$qc")"
  cat > "$d/results/pipeline_info/$vname" <<YML
FASTQC:
  fastqc: 0.12.1
DADA2_DENOISING:
  R: 4.5.2
  dada2: 1.38.0
Workflow:
  nf-core/ampliseq: v2.18.0
  Nextflow: 25.10.4
YML
  echo '{"input":"samplesheet.csv","outdir":"results"}' \
      > "$d/results/pipeline_info/params_2026-09-04_11-35-50.json"
  : > "$d/results/pipeline_info/execution_report_2026-09-04_11-35-35.html"
  touch "$d/results/$qc"
  echo "# why these values" > "$d/params.yaml"
}

# --- the three names, one per run --------------------------------------------
for pair in "a:software_versions.yml" \
            "b:nf_core_ampliseq_software_mqc_versions.yml" \
            "c:collated_versions.yml"; do
  name="${pair%%:*}" vfile="${pair#*:}"
  mkrun "$TMP/$name" "$vfile" "multiqc/multiqc_report.html"
  out=$("$S" "$TMP/$name/results" 2>&1)
  if has "$out" "nf-core/ampliseq" && has "$out" "dada2 1.38.0"; then
    ok "versions file named $vfile is found"
  else no "versions file named $vfile is found" "<<$out>>"; fi
done

# --- the quality report, wherever it landed ----------------------------------
mkrun "$TMP/nested" "software_versions.yml" "multiqc/star_salmon/multiqc_report.html"
out=$("$S" "$TMP/nested/results" 2>&1)
has "$out" "star_salmon/multiqc_report.html" \
  && ok "a quality report nested under a tool name is still found" \
  || no "a quality report nested under a tool name is still found" "<<$out>>"

# --- the retry ---------------------------------------------------------------
# The older attempt is made newer-looking by name and older by mtime, which is
# the trap: sorted by name it wins, and it is the one that did not finish.
R="$TMP/retried/results/pipeline_info"
mkrun "$TMP/retried" "software_versions.yml" "multiqc/multiqc_report.html"
: > "$R/execution_trace_2026-09-04_11-25-59.txt"   # the aborted attempt
touch -d "2020-01-01" "$R/execution_trace_2026-09-04_11-25-59.txt"
: > "$R/execution_trace_2026-09-04_11-35-35.txt"   # the real one
out=$("$S" "$TMP/retried/results" 2>&1)
if has "$out" "execution_trace_2026-09-04_11-35-35.txt" && has "$out" "was retried"; then
  ok "a retried run uses the newest attempt and says so"
else no "a retried run uses the newest attempt and says so" "<<$out>>"; fi

# The note is not decoration: silence here reads as "there was one attempt".
out2=$("$S" "$TMP/a/results" 2>&1)
has "$out2" "was retried" \
  && no "a run that was not retried says nothing about retries" "<<$out2>>" \
  || ok "a run that was not retried says nothing about retries"

# --- nothing to read ---------------------------------------------------------
mkdir -p "$TMP/bare/results"
out=$("$S" "$TMP/bare/results" 2>&1)
has "$out" "nothing here can say what produced it" \
  && ok "a tree with no pipeline_info says so instead of crashing" \
  || no "a tree with no pipeline_info says so instead of crashing" "<<$out>>"

"$S" "$TMP/does-not-exist" >/dev/null 2>&1
[ "$?" = 2 ] && ok "a missing directory exits 2" || no "a missing directory exits 2" "wrong rc"

# --- several runs at once ----------------------------------------------------
out=$("$S" --json "$TMP/a/results" "$TMP/nested/results" 2>&1)
n=$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)["runs"]))' <<<"$out" 2>/dev/null)
[ "$n" = 2 ] && ok "several runs come back as a list - a project spans them" \
             || no "several runs come back as a list - a project spans them" "got $n"

# --- what counts as citable --------------------------------------------------
out=$("$S" --json "$TMP/a/results")
cit=$(python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)["runs"][0]["citable_tools"]))' <<<"$out")
[ "$cit" = "dada2,fastqc" ] \
  && ok "runtimes are excluded and real tools are kept" \
  || no "runtimes are excluded and real tools are kept" "got '$cit'"

# The exclusion list is the one thing here that looks like v1's per-pipeline
# table, so it is pinned against the list this project already uses to define
# what a pipeline tool IS - read from that file rather than retyped, because a
# copy is what goes stale. A pipeline tool appearing in NOT_CITED would mean a
# real citation silently vanishing from a manuscript.
printf '%-62s ' "no pipeline tool hides in the not-cited list"
TOOLS=$(sed -n "s/^ *TOOLS='\\(.*\\)'$/\\1/p" "$ROOT/tests/no_per_pipeline_config.sh" | head -1)
if [ -z "$TOOLS" ]; then
  echo "FAIL: could not read the tool list from no_per_pipeline_config.sh"; fails=$((fails+1))
else
  overlap=$(python3 - "$ROOT/scripts/collect_provenance.py" "$TOOLS" <<'PY'
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
block = re.search(r"NOT_CITED = \{(.*?)\}", src, re.S).group(1)
excluded = set(re.findall(r'"([^"]+)"', block))
tools = set(sys.argv[2].split("|"))
print(",".join(sorted(excluded & tools)))
PY
)
  if [ -z "$overlap" ]; then echo ok
  else echo "FAIL: these are pipeline tools and must not be excluded: $overlap"; fails=$((fails+1)); fi
fi

# --- R4: provenance from Platform, not reconstructed -------------------------
# A stub `tw` in place of the real binary - this test never touches the
# network or a real workspace. Args always end "... --workspace <ws> <flag>".
FAKE_TW_OK="$TMP/tw-ok"
cat > "$FAKE_TW_OK" <<'SH'
#!/bin/bash
case "$*" in
  *--command*) echo "nextflow run nf-core/ampliseq -r 2.18.0 -params-file remote.yaml" ;;
  *--params*)  echo '{"input":"platform-samplesheet.csv"}' ;;
  *--config*)  echo "process.executor = 'awsbatch'" ;;
  *) echo "unrecognised: $*" >&2; exit 2 ;;
esac
SH
chmod +x "$FAKE_TW_OK"

FAKE_TW_FAIL="$TMP/tw-fail"
cat > "$FAKE_TW_FAIL" <<'SH'
#!/bin/bash
echo "ERROR: run not found" >&2
exit 1
SH
chmod +x "$FAKE_TW_FAIL"

PYVAL() { python3 -c "$1" <<<"$2" 2>/dev/null; }

# 1. A working tw: all three fields come back and are tagged 'platform'.
out=$(TW_BIN="$FAKE_TW_OK" "$S" --json --run-id run123 --workspace ws1 "$TMP/a/results" 2>&1)
cmd_src=$(PYVAL 'import json,sys; print(json.load(sys.stdin)["runs"][0]["sources"]["command"])' "$out")
par_src=$(PYVAL 'import json,sys; print(json.load(sys.stdin)["runs"][0]["sources"]["params_effective"])' "$out")
cfg_src=$(PYVAL 'import json,sys; print(json.load(sys.stdin)["runs"][0]["sources"]["config"])' "$out")
cfg_val=$(PYVAL 'import json,sys; print(json.load(sys.stdin)["runs"][0]["config"])' "$out")
if [ "$cmd_src" = platform ] && [ "$par_src" = platform ] && [ "$cfg_src" = platform ] \
   && has "$cfg_val" "awsbatch"; then
  ok "a working tw sources command/params/config from Platform"
else
  no "a working tw sources command/params/config from Platform" "<<$out>>"
fi

# 2. tw fails outright: command and params fall back to file-based values and
#    say 'files'; config has no file-based equivalent, so it is left out and a
#    note records the gap instead of inventing one (invariant 9).
out=$(TW_BIN="$FAKE_TW_FAIL" "$S" --json --run-id run123 --workspace ws1 "$TMP/a/results" 2>&1)
cmd_src=$(PYVAL 'import json,sys; print(json.load(sys.stdin)["runs"][0]["sources"]["command"])' "$out")
par_src=$(PYVAL 'import json,sys; print(json.load(sys.stdin)["runs"][0]["sources"]["params_effective"])' "$out")
has_cfg=$(PYVAL 'import json,sys; print("config" in json.load(sys.stdin)["runs"][0])' "$out")
has_cfg_src=$(PYVAL 'import json,sys; print("config" in json.load(sys.stdin)["runs"][0].get("sources",{}))' "$out")
if [ "$cmd_src" = files ] && [ "$par_src" = files ] \
   && [ "$has_cfg" = False ] && [ "$has_cfg_src" = False ] \
   && has "$out" "config not available from Platform"; then
  ok "a failing tw falls back to file-based command/params and leaves config out with a note"
else
  no "a failing tw falls back to file-based command/params and leaves config out with a note" "<<$out>>"
fi

# 3. No --run-id at all: today's behaviour is unchanged, and nothing is
#    fabricated about Platform - no 'sources' key appears at all.
out=$("$S" --json "$TMP/a/results" 2>&1)
has_sources=$(PYVAL 'import json,sys; print("sources" in json.load(sys.stdin)["runs"][0])' "$out")
has_run_id=$(PYVAL 'import json,sys; print("platform_run_id" in json.load(sys.stdin)["runs"][0])' "$out")
if [ "$has_sources" = False ] && [ "$has_run_id" = False ]; then
  ok "no --run-id means no Platform fields and no fabricated 'sources' key"
else
  no "no --run-id means no Platform fields and no fabricated 'sources' key" "<<$out>>"
fi

# 4. A run id given but no workspace anywhere (LAB_SETTINGS_FILE pointed at
#    nothing, so settings.sh's own workspace_id resolves to nothing too): the
#    gap is named, and Platform is never even asked - checked by NOT setting
#    TW_BIN, so a real tw on this machine's PATH would prove the point moot.
out=$(LAB_SETTINGS_FILE="$TMP/no-such-settings.yaml" "$S" --json --run-id run999 \
      "$TMP/a/results" 2>&1)
has "$out" "no workspace id" \
  && ok "a run id with no workspace anywhere records why Platform was not asked" \
  || no "a run id with no workspace anywhere records why Platform was not asked" "<<$out>>"

# 5. The command tw returns is the literal text tw printed, not reformatted -
#    mutation coverage for the platform-branch assignment itself, distinct
#    from the source tag checked in case 1.
out=$(TW_BIN="$FAKE_TW_OK" "$S" --json --run-id run123 --workspace ws1 "$TMP/a/results" 2>&1)
has "$out" "nextflow run nf-core/ampliseq -r 2.18.0 -params-file remote.yaml" \
  && ok "the command field carries tw's own text verbatim" \
  || no "the command field carries tw's own text verbatim" "<<$out>>"

echo
[ "$fails" = 0 ] && echo "OK: collect_provenance.py" || { echo "$fails failed"; exit 1; }
