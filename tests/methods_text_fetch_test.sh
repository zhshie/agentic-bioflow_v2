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
printf 'data: |
  <p>Local template ${tool_citations}</p>
' > "$TMP/assets/nf-core/demo/assets/methods_description_template.yml"
out=$(HOME="$TMP/home" "$S" --assets "$TMP/assets" --cache-dir "$TMP/cache2" --fetcher "$FAKE" "$TMP/r1/results" 2>&1)
if grep -qF "10.1000/local" <<<"$out" && [ "$(calls)" = 0 ]; then
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
mkrun r7c "nf-core/demo: 9876543210fedcba9876543210fedcba98765432"
: > "$LOG"
out=$(run r7c)
[ "$(awk '{print $2}' "$LOG" | sort -u | wc -l | tr -d ' ')" = 1 ] \
  && ok "a missing SHA is reported, not retried as another revision" \
  || no "a missing SHA is reported, not retried as another revision" "log=$(cat "$LOG")"

# --- 8. a name that is not owner/repo ---------------------------------------
mkrun r8 "git.example.org/lab/pipeline: v1.0"
: > "$LOG"
out=$(run r8); rc=$?
if [ "$rc" = 0 ] && [ "$(calls)" = 0 ] && grep -qF "CITATION NEEDED: dada2" <<<"$out" \
   && grep -qiE "owner/repo|not a GitHub" <<<"$out"; then
  ok "a pipeline that is not owner/repo is not fetched, and says why"
else no "a pipeline that is not owner/repo is not fetched, and says why" "rc=$rc calls=$(calls) <<$out>>"; fi

mkrun r8b "nf-core/..: v1.0"
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

# --- 11. build_package.sh puts the cache under the deployment's root --------
BP="$(cd "$(dirname "$S")" && pwd)/build_package.sh"
mkdir -p "$TMP/root/config" "$TMP/proj/runs/demo_20260101" "$TMP/proj/analysis/figures"
: > "$TMP/root/config/env.yaml"
printf -- '- **richness**
  id: richness
  question: Does treatment change richness?
  status: accepted
' > "$TMP/proj/analysis/analysis.md"
cp -r "$TMP/r1/results" "$TMP/proj/runs/demo_20260101/results"
cp "$TMP/r1/params.yaml" "$TMP/proj/runs/demo_20260101/params.yaml"
out=$(HOME="$TMP/home" LAB_SETTINGS_FILE="$TMP/root/config/env.yaml" ABF_PIPELINE_FETCHER="$FAKE"       "$BP" "$TMP/proj" 2>&1)
if [ -s "$TMP/root/cache/pipeline_files/nf-core/demo/v1.2.3/CITATIONS.md" ]    && grep -qF "Tools used within the workflow:" "$TMP/proj/submission/methods.md" 2>/dev/null; then
  ok "build_package.sh keeps the cache under <root>/cache/pipeline_files"
else no "build_package.sh keeps the cache under <root>/cache/pipeline_files" "<<$out>> $(find "$TMP/root" 2>&1)"; fi

# =============================================================================
# Acceptance round 2: validation before caching, branch revisions, each guard,
# the real curl path, and the no-root limit.
# =============================================================================
reset() { rm -rf "$TMP/cache"; : > "$LOG"; rm -f "$FX/OFFLINE"; }

# --- 12. a body that is not a CITATIONS.md is never cached (captive portal) --
mkdir -p "$FX/nf-core/demo/v7.7.7/assets"
echo '<html><body>Please log in to the network</body></html>' > "$FX/nf-core/demo/v7.7.7/CITATIONS.md"
cp "$FX/nf-core/demo/v1.2.3/assets/methods_description_template.yml" "$FX/nf-core/demo/v7.7.7/assets/"
mkrun r12 "nf-core/demo: v7.7.7"
reset
out=$(run r12)
if grep -qF "CITATION NEEDED: dada2" <<<"$out" \
   && grep -qE "no CITATIONS.md for nf-core/demo: .*not a CITATIONS.md" <<<"$out" \
   && grep -qF "github.com/nf-core/demo@v7.7.7" <<<"$out" \
   && [ ! -e "$TMP/cache/nf-core/demo/v7.7.7/CITATIONS.md" ] \
   && ! grep -qE "citations .github.com" <<<"$out"; then
  ok "an HTML 200 is not cached, is named as not a CITATIONS.md, is not a Source"
else no "an HTML 200 is not cached, is named as not a CITATIONS.md, is not a Source" "<<$out>> $(find "$TMP/cache" 2>&1)"; fi
out=$(HOME="$TMP/home" "$S" --assets "$TMP/nowhere" --cache-dir "$TMP/cache" --fetcher off "$TMP/r12/results" 2>&1)
if grep -qF "CITATION NEEDED: dada2" <<<"$out" && ! grep -qE "citations .github.com" <<<"$out"; then
  ok "...and a later run with fetching off finds nothing hidden in the cache"
else no "...and a later run with fetching off finds nothing hidden in the cache" "<<$out>>"; fi

# a template with no data: block is reported as such, not cached
mkdir -p "$FX/nf-core/demo/v7.7.8/assets"
cp "$FX/nf-core/demo/v1.2.3/CITATIONS.md" "$FX/nf-core/demo/v7.7.8/"
echo '<html>nope</html>' > "$FX/nf-core/demo/v7.7.8/assets/methods_description_template.yml"
mkrun r12b "nf-core/demo: v7.7.8"
reset
out=$(run r12b)
if grep -qE "no methods template for nf-core/demo: .*not a methods template" <<<"$out" \
   && [ ! -e "$TMP/cache/nf-core/demo/v7.7.8/assets/methods_description_template.yml" ]; then
  ok "a template without a data: block is named as not a template, not cached"
else no "a template without a data: block is named as not a template, not cached" "<<$out>>"; fi

# an empty body has its own reason
mkdir -p "$FX/nf-core/demo/v7.7.9"; : > "$FX/nf-core/demo/v7.7.9/CITATIONS.md"
mkrun r12c "nf-core/demo: v7.7.9"
reset
out=$(run r12c)
grep -qiE "no CITATIONS.md for nf-core/demo: .*empty" <<<"$out" \
  && ok "an empty body is reported as empty" \
  || no "an empty body is reported as empty" "<<$out>>"

# a poisoned cache (zero entries, from an older build) is not trusted
reset
mkdir -p "$TMP/cache/nf-core/demo/v1.2.3"
echo '<html>Please log in</html>' > "$TMP/cache/nf-core/demo/v1.2.3/CITATIONS.md"
out=$(HOME="$TMP/home" "$S" --assets "$TMP/nowhere" --cache-dir "$TMP/cache" --fetcher off "$TMP/r1/results" 2>&1)
if grep -qF "CITATION NEEDED: dada2" <<<"$out" && ! grep -qE "citations .github.com" <<<"$out" \
   && grep -qF "no CITATIONS.md for nf-core/demo" <<<"$out"; then
  ok "a cached file with no tool entries is not used, and is reported"
else no "a cached file with no tool entries is not used, and is reported" "<<$out>>"; fi
out=$(run r1)
grep -qF "Tools used within the workflow:" <<<"$out" \
  && ok "...and with fetching on it is replaced by a good copy" \
  || no "...and with fetching on it is replaced by a good copy" "<<$out>>"

# a local CITATIONS.md with zero entries is a visible gap too
mkdir -p "$TMP/badassets/nf-core/demo"
echo "nothing here" > "$TMP/badassets/nf-core/demo/CITATIONS.md"
out=$(HOME="$TMP/home" "$S" --assets "$TMP/badassets" --fetcher off "$TMP/r1/results" 2>&1)
if grep -qF "CITATION NEEDED: dada2" <<<"$out" && grep -qE "no CITATIONS.md for nf-core/demo: .*no tool entries" <<<"$out" \
   && ! grep -qF "citations \`nf-core/demo/CITATIONS.md" <<<"$out"; then
  ok "a local CITATIONS.md with no entries is a visible gap, not a Source"
else no "a local CITATIONS.md with no entries is a visible gap, not a Source" "<<$out>>"; fi

# --- 13. branch revisions are not cached as final ----------------------------
put nf-core/demo main
mkrun r13 "nf-core/demo: main"
reset
out=$(run r13); c1=$(calls)
out=$(run r13); c2=$(calls)
[ "$c2" -gt "$c1" ] && grep -qF "Tools used within the workflow:" <<<"$out" \
  && ok "a branch revision is fetched again every build" \
  || no "a branch revision is fetched again every build" "calls $c1 -> $c2"
touch "$FX/OFFLINE"
out=$(run r13)
if grep -qF "Tools used within the workflow:" <<<"$out" && grep -qiE "out of date|stale" <<<"$out"; then
  ok "offline, a branch falls back to the cached copy and says it may be stale"
else no "offline, a branch falls back to the cached copy and says it may be stale" "<<$out>>"; fi
rm -f "$FX/OFFLINE"
put nf-core/demo 3.15.0dev
mkrun r13b "nf-core/demo: 3.15.0dev"
reset; run r13b >/dev/null; c1=$(calls); run r13b >/dev/null
[ "$(calls)" -gt "$c1" ] && ok "a dev version is not treated as an immutable tag" \
  || no "a dev version is not treated as an immutable tag" "calls $c1 -> $(calls)"

# --- 14. each guard has a case that fails without it -------------------------
mkrun g1 "nf-core/demo: a/../b"
reset; out=$(run g1)
[ "$(calls)" = 0 ] && grep -qF "CITATION NEEDED: dada2" <<<"$out" && grep -qiE "not one GitHub can serve" <<<"$out" \
  && ok "guard: a revision with .. is refused (no traversal into the cache or URL)" \
  || no "guard: a revision with .. is refused" "calls=$(calls) <<$out>>"
[ ! -e "$TMP/cache/nf-core/demo/a" ] || no "guard: nothing written for a/../b" "$(find "$TMP/cache")"
mkrun g2 "nf-core/demo: v1.0;touch"
reset; out=$(run g2)
[ "$(calls)" = 0 ] && grep -qiE "not one GitHub can serve" <<<"$out" \
  && ok "guard: a revision with characters outside the allowed set is refused" \
  || no "guard: a revision with characters outside the allowed set is refused" "calls=$(calls) <<$out>>"
for bad in None null '~'; do
  mkrun g3 "nf-core/demo: $bad"
  reset; out=$(run g3)
  [ "$(calls)" = 0 ] && grep -qiE "no revision" <<<"$out" \
    && ok "guard: a recorded revision of '$bad' means no revision" \
    || no "guard: a recorded revision of '$bad' means no revision" "calls=$(calls) <<$out>>"
done
mkrun g4 "nf-core/demo: v6.6.6"
reset; out=$(run g4)
grep -qiE "not found in nf-core/demo at v6.6.6 or 6.6.6" <<<"$out" \
  && ok "guard: v1.2.3 is retried as 1.2.3 (the v is stripped)" \
  || no "guard: v1.2.3 is retried as 1.2.3 (the v is stripped)" "<<$out>> log=$(cat "$LOG")"
mkdir -p "$FX/nf-core/demo/6.6.6"; cp -r "$FX/nf-core/demo/v1.2.3/." "$FX/nf-core/demo/6.6.6/"
reset; out=$(run g4)
grep -qF "Tools used within the workflow:" <<<"$out" \
  && ok "guard: ...and the stripped twin is used when it exists" \
  || no "guard: ...and the stripped twin is used when it exists" "<<$out>>"
mkrun g5 "nf-core/demo: 0123456789abcdef0123456789abcdef01234999"
reset; out=$(run g5)
[ "$(awk '{print $2}' "$LOG" | sort -u)" = "0123456789abcdef0123456789abcdef01234999" ] \
  && ok "guard: a SHA that 404s is never retried as v<sha>" \
  || no "guard: a SHA that 404s is never retried as v<sha>" "log=$(cat "$LOG")"

# --- 15. the real curl path, with a fake curl on PATH ------------------------
FB="$TMP/fakebin"; mkdir -p "$FB"; CURLLOG="$TMP/curl.log"
cat > "$FB/curl" <<EOF
#!/bin/bash
echo "\$*" >> "$CURLLOG"
case "\${FAKE_CURL:-ok}" in
  ok)   printf '%s\n200' "\$(cat "$FX/nf-core/demo/v1.2.3/CITATIONS.md")" ;;
  404)  printf '\n404' ;;
  html) printf '<html>Please log in</html>\n200' ;;
  503)  printf 'busy\n503' ;;
  net)  echo "curl: (6) Could not resolve host: raw.githubusercontent.com" >&2; exit 6 ;;
esac
EOF
chmod +x "$FB/curl"
PYDIR="$(cd "$(dirname "$S")" && pwd)"
cf() { FAKE_CURL="$1" PATH="$FB:$PATH" python3 -c "
import sys; sys.path.insert(0, '$PYDIR'); import methods_text as m
t, r = m.curl_fetcher('nf-core/demo', 'v1.2.3', 'CITATIONS.md'); print(repr((t is not None, r)))"; }
[ "$(cf ok)" = "(True, None)" ] && grep -qF "https://raw.githubusercontent.com/nf-core/demo/v1.2.3/CITATIONS.md" "$CURLLOG" \
  && ok "curl_fetcher: 200 returns the body from the raw.githubusercontent.com URL" \
  || no "curl_fetcher: 200 returns the body" "$(cf ok) $(cat "$CURLLOG")"
[ "$(cf 404)" = "(False, 'not found')" ] && ok "curl_fetcher: 404 is 'not found'" || no "curl_fetcher: 404" "$(cf 404)"
cf 503 | grep -q "HTTP 503" && ok "curl_fetcher: another status is named" || no "curl_fetcher: 503" "$(cf 503)"
cf net | grep -q "Could not resolve host" && ok "curl_fetcher: a network failure carries curl's message" || no "curl_fetcher: net" "$(cf net)"
reset
out=$(FAKE_CURL=html HOME="$TMP/home" PATH="$FB:$PATH" "$S" --assets "$TMP/nowhere" --cache-dir "$TMP/cache" "$TMP/r12/results" 2>&1)
if grep -qF "CITATION NEEDED: dada2" <<<"$out" && grep -qF "not a CITATIONS.md" <<<"$out" && [ ! -e "$TMP/cache/nf-core/demo" ]; then
  ok "end to end with curl answering an HTML 200: visible, nothing cached"
else no "end to end with curl answering an HTML 200" "<<$out>> $(find "$TMP/cache" 2>&1)"; fi

# --- 16. no cache dir: it works, and says it will fetch again ----------------
out=$(HOME="$TMP/home" "$S" --assets "$TMP/nowhere" --fetcher "$FAKE" "$TMP/r1/results" 2>&1)
if grep -qF "Tools used within the workflow:" <<<"$out" && grep -qiE "fetched again|not kept" <<<"$out"; then
  ok "with no cache dir the file is used once and the notes say it is not kept"
else no "with no cache dir the file is used once and the notes say it is not kept" "<<$out>>"; fi

echo
[ "$fails" = 0 ] && echo "OK: methods_text.py fetch" || { echo "$fails failed"; exit 1; }
