#!/bin/bash
# Tests for scripts/cite.sh.
#
# These run offline. The cache is the seam: a DOI already in it is never
# fetched, and $CITE_CURL points the fetch at a stub for everything else. That
# is not only convenience - the failure path is the one that matters here, and
# a test that needs the network to exercise it would be skipped exactly when
# it was needed.
#
# What is being defended: a reference nobody can resolve must stay VISIBLE.
# A methods section that silently drops a citation looks complete, and the
# work it under-cites belongs to someone.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/cite.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-62s ok\n' "$1"; }
no() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

CACHE="$TMP/cache"; mkdir -p "$CACHE"
cat > "$CACHE/10.1234_known.bib" <<'B'
@article{Someone_2020, title={A known thing}, DOI={10.1234/known}, year={2020} }
B

# A stub that answers the way a resolver does when it has never heard of the
# DOI: prose, and a 200. This is the case that must not be cached or cited.
cat > "$TMP/prose_curl" <<'B'
#!/bin/bash
echo "<html>Resource not found</html>"
B
chmod +x "$TMP/prose_curl"

run() { CITE_CURL="$1" bash "$S" --cache "$CACHE" "${@:2}" 2>"$TMP/err"; }

out=$(run false 10.1234/known); rc=$?
[ "$rc" = 0 ] && grep -qF "Someone_2020" <<<"$out" \
  && ok "a cached DOI needs no network" \
  || no "a cached DOI needs no network" "rc=$rc <<$out>>"

out=$(run false 10.5555/unknown); rc=$?
if [ "$rc" = 3 ] && grep -qF "CITATION NEEDED" <<<"$out"; then
  ok "an unresolvable DOI is marked in the output, not dropped"
else no "an unresolvable DOI is marked in the output, not dropped" "rc=$rc <<$out>>"; fi

# The sigil check. A resolver's error page is a 200 with prose in it, and
# caching that would put an HTML fragment in a bibliography.
out=$(run "$TMP/prose_curl" 10.7777/prose); rc=$?
if [ "$rc" = 3 ] && [ ! -s "$CACHE/10.7777_prose.bib" ]; then
  ok "an error page is neither cited nor cached"
else no "an error page is neither cited nor cached" "rc=$rc, cache=$(ls "$CACHE")"; fi

# ...and the other half of that check, which is the one that broke: the real
# service answers with a leading space before the @. An anchored match on '@'
# rejected every genuine reply, and every DOI came back CITATION NEEDED. A
# fixture without the space would never have shown it.
cat > "$TMP/spaced_curl" <<'B'
#!/bin/bash
printf ' @article{Spaced_2021, title={Leading space}, DOI={10.8888/spaced}, year={2021} }\n'
B
chmod +x "$TMP/spaced_curl"
out=$(run "$TMP/spaced_curl" 10.8888/spaced); rc=$?
[ "$rc" = 0 ] && grep -qF "Spaced_2021" <<<"$out" \
  && ok "a reply with leading whitespace is still an entry" \
  || no "a reply with leading whitespace is still an entry" "rc=$rc <<$out>>"

# @file: the shape a quality report writes its citation list in, so that list
# can be piped straight in and the tool name survives into the marker.
cat > "$TMP/citations.txt" <<'B'
10.1234/known                                      # MultiQC
10.5555/unknown                                    # somethingelse
B
out=$(run false "@$TMP/citations.txt"); rc=$?
if grep -qF "Someone_2020" <<<"$out" && grep -qF "CITATION NEEDED: somethingelse" <<<"$out"; then
  ok "@file keeps the tool name so the gap says which tool"
else no "@file keeps the tool name so the gap says which tool" "<<$out>>"; fi

out=$(run false 10.1234/known 10.1234/known)
[ "$(grep -c "Someone_2020" <<<"$out")" = 1 ] \
  && ok "the same DOI twice is one entry" \
  || no "the same DOI twice is one entry" "<<$out>>"

run false --out "$TMP/refs.bib" 10.1234/known >/dev/null
grep -qF "Someone_2020" "$TMP/refs.bib" 2>/dev/null \
  && ok "--out writes the file" || no "--out writes the file" "no file"

bash "$S" --cache "$CACHE" >/dev/null 2>&1
[ "$?" = 2 ] && ok "no arguments exits 2" || no "no arguments exits 2" "wrong rc"

echo
[ "$fails" = 0 ] && echo "OK: cite.sh" || { echo "$fails failed"; exit 1; }
