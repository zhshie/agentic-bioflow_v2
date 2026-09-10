#!/bin/bash
# Invariant 9: every verifiable claim points at the file that produced it.
#
# The other invariants are about what this project asserts about itself, and a
# later run catches a mistake. This one is about what it writes on someone
# else's behalf: a wrong line in a methods section goes out under a
# researcher's name, and nothing catches it afterwards.
#
# So this is a structural check on the three tools that write such lines. It
# does not re-test their behaviour - each has its own suite - it asserts that
# the machinery for admitting ignorance is still present in each of them. A
# refactor that removed the gap markers would leave every one of those suites
# green, because they test what happens when a source IS found.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
need() { # need <file> <pattern> <what it protects>
  printf '%-62s ' "$3"
  if grep -qE -- "$2" "$ROOT/$1"; then echo ok
  else echo "FAIL: $1 no longer contains /$2/"; fails=$((fails+1)); fi
}

need scripts/cite.sh          'CITATION NEEDED' \
     "an unresolved citation stays visible in the bibliography"
need scripts/cite.sh          'Accept: application/x-bibtex' \
     "citations are fetched, not composed"
need scripts/methods_text.py  'CITATION NEEDED' \
     "an unmatched tool stays visible in the methods"
need scripts/methods_text.py  'closest in CITATIONS.md' \
     "a near miss is offered as a candidate, not resolved"
need scripts/build_package.sh 'no figure file starting with' \
     "a planned figure that was never made is called out"
need scripts/build_package.sh 'no plan entry claims it' \
     "a figure nobody planned is called out"
need scripts/build_package.sh 'trace to a file or to a script' \
     "the results prose is told where its numbers must come from"
need commands/downstream.md   'from the data' \
     "a figure is described from the data, never from the picture"
need commands/finish.md       'never from memory' \
     "the citation rule is stated where the work is done"

# The one that is easiest to lose by accident: the manuscript must not gain
# executable chunks, because rendering it then needs a language runtime the
# renderer's machine may not have.
printf '%-62s ' "the assembled manuscript stays free of code chunks"
if grep -qF '```{' "$ROOT/scripts/build_package.sh"; then
  echo "FAIL: build_package.sh emits a code chunk"; fails=$((fails+1))
else echo ok; fi

echo
[ "$fails" = 0 ] && echo "OK: invariant 9 is still enforced where it is written" \
  || { echo "$fails failed"; exit 1; }
