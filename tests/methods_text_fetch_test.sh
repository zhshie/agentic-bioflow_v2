#!/bin/bash
# Tests for the fetch half of scripts/methods_text.py (issue #4).
#
# This plugin runs pipelines through Seqera Platform, so the machine that runs
# `finish` never did a local `nextflow pull`: ~/.nextflow/assets/<pipeline> is
# empty on the first finish, and every tool used to come out as
# [CITATION NEEDED] for a reason that had nothing to do with the tool. The fix
# fetches CITATIONS.md and assets/methods_description_template.yml from the
# pipeline's repository at the run's own pinned revision, into a cache the
# deployment owns.
#
# No network here. Every fetch goes through a fake fetcher (--fetcher), which
# serves files from a fixture tree, logs each call, and fails on request:
#   exit 0   content on stdout
#   exit 44  not found (HTTP 404)
#   other    unreachable, reason on stderr
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/methods_text.py"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-66s ok\n' "$1"; }
no() { printf '%-66s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

FX="$TMP/fx"; LOG="$TMP/fetch.log"; : > "$LOG"
cat > "$TMP/fake_fetcher.sh" <<EOF
#!/bin/bash
echo "\$1 \$2 \$3" >> "$LOG"
[ -e "$FX/OFFLINE" ] && { echo "could not resolve host: raw.githubusercontent.com" >&2; exit 7; }
f="$FX/\$1/\$2/\$3"
[ -f "\$f" ] && { cat "\$f"; exit 0; }
exit 44
EOF
chmod +x "$TMP/fake_fetcher.sh"
FAKE="$TMP/fake_fetcher.sh"

put() {   # put <owner/repo> <rev>   (serves both files)
  mkdir -p "$FX/$1/$2/assets"
  cat > "$FX/$1/$2/CITATIONS.md" <<'MD'
# nf-core/demo: Citations
- [FastQC](https://example.org/fastqc)
  > Andrews S. FastQC. doi: 10.1000/fastqc.
- [DADA2](https://example.org/dada2)
  > Callahan BJ et al. DADA2. doi: 10.1038/nmeth.3869.
MD
  cat > "$FX/$1/$2/assets/methods_description_template.yml" <<'YML'
id: "demo-methods"
data: |
  <h4>Methods</h4>
  <p>Data was processed using nf-core/demo v${workflow.manifest.version}.</p>
  <p>${tool_citations}</p>
YML
}

mkrun() {   # mkrun <dir> <"name: rev" line, or "" for none>
  local d="$TMP/$1"
  mkdir -p "$d/results/pipeline_info" "$d/results/multiqc"
  {
    printf 'FASTQC:\n  fastqc: 0.12.1\nDADA2_DENOISING:\n  dada2: 1.38.0\nWorkflow:\n'
    [ -n "$2" ] && printf '  %s\n' "$2"
    printf '  Nextflow: 25.10.4\n'
  } > "$d/results/pipeline_info/software_versions.yml"
  : > "$d/results/pipeline_info/execution_report_2026-01-01_00-00-00.html"
  echo '{}' > "$d/results/pipeline_info/params_2026-01-01_00-00-00.json"
  touch "$d/results/multiqc/multiqc_report.html"
  echo "# because" > "$d/params.yaml"
}
calls() { wc -l < "$LOG" | tr -d ' '; }
run() {   # run <rundir> [extra args]  (assets dir is always empty)
  local r="$1"; shift
  HOME="$TMP/home" "$S" --assets "$TMP/nowhere" --cache-dir "$TMP/cache" --fetcher "$FAKE" "$@" "$TMP/$r/results" 2>&1
}
mkdir -p "$TMP/home"

# --- 1. success: nothing local, fetched at the run's own revision -----------
put nf-core/demo v1.2.3
mkrun r1 "nf-core/demo: v1.2.3"
out=$(run r1)
if grep -qF "Tools used within the workflow:" <<<"$out" && grep -qF "DADA2" <<<"$out" \
   && ! grep -qF "CITATION NEEDED: dada2" <<<"$out"; then
  ok "nothing local: citations are fetched and the slot is filled"
else no "nothing local: citations are fetched and the slot is filled" "<<$out>>"; fi
grep -qF "nf-core/demo v1.2.3" <<<"$out" \
  && ok "the template is fetched too and its wording is used" \
  || no "the template is fetched too and its wording is used" "<<$out>>"

# The output names where the citations came from.
grep -qE "citations \`?github.com/nf-core/demo@v1.2.3" <<<"$out" \
  && ok "the software list names the repository and revision it fetched" \
  || no "the software list names the repository and revision it fetched" "<<$out>>"

# --- 2. cache: written under --cache-dir, never under ~/.nextflow ------------
[ -s "$TMP/cache/nf-core/demo/v1.2.3/CITATIONS.md" ] \
  && ok "the file is kept in the deployment's cache, keyed by revision" \
  || no "the file is kept in the deployment's cache, keyed by revision" "$(find "$TMP/cache" 2>&1)"
[ ! -e "$TMP/home/.nextflow" ] \
  && ok "nothing is written under ~/.nextflow" \
  || no "nothing is written under ~/.nextflow" "$(find "$TMP/home")"

# --- 3. second run uses the cache and does not fetch again -------------------
before=$(calls)
out=$(run r1)
after=$(calls)
if [ "$before" = "$after" ] && grep -qF "Tools used within the workflow:" <<<"$out"; then
  ok "a second run reads the cache and does not fetch again"
else no "a second run reads the cache and does not fetch again" "calls $before -> $after <<$out>>"; fi

# --- 4. local ~/.nextflow/assets wins and nothing is fetched -----------------
: > "$LOG"
mkdir -p "$TMP/assets/nf-core/demo/assets"
cat > "$TMP/assets/nf-core/demo/CITATIONS.md" <<'MD'
- [FastQC](https://example.org/fastqc)
  > Local copy. doi: 10.1000/local.
MD
out=$(HOME="$TMP/home" "$S" --assets "$TMP/assets" --cache-dir "$TMP/cache2" --fetcher "$FAKE" "$TMP/r1/results" 2>&1)
if grep -qF "Local copy" <<<"$out" && [ "$(calls)" = 0 ]; then
  ok "a local pipeline copy is read first and nothing is fetched for it"
else no "a local pipeline copy is read first and nothing is fetched for it" "calls=$(calls) <<$out>>"; fi

# --- 5. 404: visible, honest reason, the build does not break ----------------
mkrun r5 "nf-core/demo: v9.9.9"
out=$(run r5); rc=$?
if [ "$rc" = 0 ] && grep -qF "CITATION NEEDED: dada2" <<<"$out" \
   && grep -qF "no CITATIONS.md for nf-core/demo" <<<"$out" \
   && grep -qiE "not found.*v9\.9\.9|v9\.9\.9.*not found" <<<"$out" \
   && ! grep -qF "under $TMP/nowhere" <<<"$out"; then
  ok "404: CITATION NEEDED plus a comment that says the revision was not found"
else no "404: CITATION NEEDED plus a comment that says the revision was not found" "rc=$rc <<$out>>"; fi
[ ! -e "$TMP/cache/nf-core/demo/v9.9.9" ] \
  && ok "a failed fetch leaves nothing in the cache" \
  || no "a failed fetch leaves nothing in the cache" "$(find "$TMP/cache")"

# --- 6. offline: the real reason is shown ------------------------------------
touch "$FX/OFFLINE"
mkrun r6 "nf-core/demo: v4.5.6"
out=$(run r6); rc=$?
if [ "$rc" = 0 ] && grep -qF "CITATION NEEDED: dada2" <<<"$out" \
   && grep -qF "could not resolve host" <<<"$out" \
   && grep -qiE "network|unreachable|could not be fetched" <<<"$out"; then
  ok "offline: CITATION NEEDED plus the network failure as the reason"
else no "offline: CITATION NEEDED plus the network failure as the reason" "rc=$rc <<$out>>"; fi
rm -f "$FX/OFFLINE"

# --- 7. tag vs commit SHA ----------------------------------------------------
SHA=0123456789abcdef0123456789abcdef01234567
put nf-core/demo "$SHA"
mkrun r7 "nf-core/demo: $SHA"
: > "$LOG"
out=$(run r7)
if grep -qF "Tools used within the workflow:" <<<"$out" \
   && [ "$(sort -u "$LOG" | awk '{print $2}' | sort -u)" = "$SHA" ]; then
  ok "a commit SHA is used exactly as given, never rewritten"
else no "a commit SHA is used exactly as given, never rewritten" "log=$(cat "$LOG") <<$out>>"; fi

# A tag the versions file records without its leading v, published with one.
mkrun r7b "nf-core/demo: 1.2.3"
rm -rf "$TMP/cache"; : > "$LOG"
out=$(run r7b)
if grep -qF "Tools used within the workflow:" <<<"$out" && grep -q " v1.2.3 " "$LOG"; then
  ok "a tag recorded without its v is retried with it, and the match is cited"
else no "a tag recorded without its v is retried with it, and the match is cited" "log=$(cat "$LOG") <<$out>>"; fi

# A SHA that does not exist is not retried under other names.
mkrun r7c "nf-core/demo: fedcba9876543210fedcba9876543210fedcba98"
: > "$LOG"
out=$(run r7c)
[ "$(awk '{print $2}' "$LOG" | sort -u | wc -l | tr -d ' ')" = 1 ] \
  && ok "a missing SHA is reported, not retried as another revision" \
  || no "a missing SHA is reported, not retried as another revision" "log=$(cat "$LOG")"

# --- 8. a name that is not owner/repo ---------------------------------------
mkrun r8 "https://example.org/some/where: v1.0"
: > "$LOG"
out=$(run r8); rc=$?
if [ "$rc" = 0 ] && [ "$(calls)" = 0 ] && grep -qF "CITATION NEEDED: dada2" <<<"$out" \
   && grep -qiE "owner/repo|not a GitHub" <<<"$out"; then
  ok "a pipeline that is not owner/repo is not fetched, and says why"
else no "a pipeline that is not owner/repo is not fetched, and says why" "rc=$rc calls=$(calls) <<$out>>"; fi

mkrun r8b "../evil/..: v1.0"
: > "$LOG"
out=$(run r8b)
[ "$(calls)" = 0 ] && [ ! -e "$TMP/evil" ] \
  && ok "a name with .. is refused, nothing is fetched or written outside the cache" \
  || no "a name with .. is refused, nothing is fetched or written outside the cache" "calls=$(calls)"

# --- 9. no revision recorded -------------------------------------------------
mkrun r9 "nf-core/demo:"
: > "$LOG"
out=$(run r9); rc=$?
if [ "$rc" = 0 ] && [ "$(calls)" = 0 ] && grep -qF "CITATION NEEDED: dada2" <<<"$out" \
   && grep -qiE "no revision" <<<"$out"; then
  ok "no recorded revision: nothing is guessed, the reason says so"
else no "no recorded revision: nothing is guessed, the reason says so" "rc=$rc calls=$(calls) <<$out>>"; fi

# --- 10. the template is not fetched when the report already rendered it -----
cat > "$TMP/r10_report.html" <<'H'
<h4>Methods</h4><p>Data was processed using nf-core/demo v1.2.3.</p><p></p><h4>References</h4>
H
mkrun r10 "nf-core/demo: v1.2.3"
cp "$TMP/r10_report.html" "$TMP/r10/results/multiqc/multiqc_report.html"
rm -rf "$TMP/cache"; : > "$LOG"
out=$(run r10)
if grep -qF "CITATIONS.md" "$LOG" && ! grep -qF "methods_description_template" "$LOG"; then
  ok "the template is only fetched when no rendered report has the paragraph"
else no "the template is only fetched when no rendered report has the paragraph" "log=$(cat "$LOG")"; fi

echo
[ "$fails" = 0 ] && echo "OK: methods_text.py fetch" || { echo "$fails failed"; exit 1; }
