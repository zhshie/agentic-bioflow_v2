#!/bin/bash
# Invariant 5 (constitution II.5): judgment, procedure and site operations live
# in docs/ and scripts/, readable and runnable by a person or another model.
# With hooks/ and .claude-plugin/ removed, the system still works from docs/
# and scripts/: degraded (no safety net, no per-command opening), not
# equivalent, but usable.
#
# This builds that world and uses it: a copy of the tree WITHOUT hooks/,
# .claude-plugin/, .claude/ and .git, run with an empty environment (no
# CLAUDE_PLUGIN_ROOT, a throwaway HOME, no settings file). In it:
#
#   1. Every script parses (bash -n / py_compile): nothing sources a removed file.
#   2. Static: no shipped script runs or sources anything under hooks/ or reads
#      .claude-plugin/ as a REQUIREMENT (scripts/report.sh reads plugin.json for
#      the repository name and must degrade to a clear message, case 6).
#   3. The key scripts answer their help / dry paths: intro.sh, on_site.sh (dry
#      run), settings.sh, the samplesheet generator's usage, report.sh.
#   4. report.sh without plugin.json says what is missing and keeps the report
#      queued: degraded, never silent.
#   5. Every scripts/<file> that commands/, skills/ and docs/ cite resolves in
#      the copy, so a person following the docs reaches a real file.
#
# What this does NOT prove: that a person can finish a real run with it. That is
# a person's check, and the constitution says "degraded, not equivalent" for that reason.
#
# WORKS_WITHOUT_HOST_SRC points at the tree to copy; the self-tests use it to
# prove the static scan goes red when a script depends on a hook.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$HERE/$(basename "${BASH_SOURCE[0]}")"
SRC="${WORKS_WITHOUT_HOST_SRC:-$(cd "$HERE/.." && pwd)}"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
t() { printf '%-66s ' "$1"; if [ "$2" = ok ]; then echo ok; else echo "FAIL: $2"; fails=$((fails + 1)); fi; }

command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 not found"; exit 1; }

COPY="$TMP/copy"; mkdir -p "$COPY"
# Only what a person or another model would use without the host.
( cd "$SRC" && tar -c scripts docs commands skills README.md CLAUDE.md 2>/dev/null ) | tar -x -C "$COPY"
[ ! -e "$COPY/hooks" ] && [ ! -e "$COPY/.claude-plugin" ] || { echo "FAIL: the copy still has hooks/ or .claude-plugin/"; exit 1; }
[ -d "$COPY/scripts" ] && [ -d "$COPY/docs" ] || { echo "FAIL: the copy lacks scripts/ or docs/"; exit 1; }

# A bare environment: nothing the host would have provided.
E() { env -i PATH="$PATH" HOME="$TMP/home" LANG=C.UTF-8 "$@"; }
mkdir -p "$TMP/home"
cd "$COPY" || exit 1

echo "== 1. everything parses without the host's files =="
bad=""
for f in scripts/*.sh scripts/utils/*.sh; do bash -n "$f" 2>/dev/null || bad="$bad $f"; done
for f in scripts/*.py scripts/utils/*.py; do python3 -m py_compile "$f" 2>/dev/null || bad="$bad $f"; done
t "all scripts parse in the reduced tree" "$([ -z "$bad" ] && echo ok || echo "$bad")"

echo "== 2. no script depends on hooks/ or .claude-plugin/ =="
# Only lines that EXECUTE or LOAD something count: a command word (source, ., bash,
# sh, python, exec) followed by a path under hooks/ or .claude-plugin/, or a path
# built from a variable. Prose in a comment, docstring or echo that merely names
# a hook is documentation, not a dependency. plugin.json is the one sanctioned
# read (report.sh, case 4).
dep=$(for f in scripts/*.sh scripts/*.py scripts/utils/*.sh scripts/utils/*.py; do
        grep -nE '.' "$f" | grep -vE '^[0-9]+:[[:space:]]*(#|//)'           | grep -E '(^[0-9]+:[[:space:]]*|[;&|(`]|[$][(]|then|do|else)[[:space:]]*(source|[.]|bash|sh|python3?|exec|env|cat|node)[[:space:]]+[^#]*(hooks/|[.]claude-plugin)|[$][{(]?[A-Za-z_]+[})]?/+(hooks|[.]claude-plugin)/'           | sed "s|^|$f:|"
      done | grep -vE 'plugin[.]json' )
t "no script runs, sources or requires a file under hooks/" "$([ -z "$dep" ] && echo ok || echo "$dep" | head -3)"
# Sections 3 and 4 run the scripts; a mutated tree under self-test skips them.
if [ -z "${WORKS_WITHOUT_HOST_SRC:-}" ]; then
echo "== 3. the key scripts answer without the host =="
out=$(E bash scripts/intro.sh --list 2>&1); rc=$?
t "intro.sh --list names the commands" "$([ "$rc" = 0 ] && grep -qx launch <<<"$out" && echo ok || echo "rc=$rc <<$out>>")"
out=$(E bash scripts/intro.sh 2>&1); rc=$?
t "intro.sh prints the overview" "$([ "$rc" = 0 ] && [ -n "$out" ] && echo ok || echo "rc=$rc")"
printf 'reach: local\n' > "$TMP/env.yaml"
out=$(E LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_DRY_RUN=1 bash scripts/on_site.sh true 2>&1); rc=$?
t "on_site.sh dry run says where and what it would run" "$([ "$rc" = 0 ] && grep -q 'local' <<<"$out" && echo ok || echo "rc=$rc <<$out>>")"
out=$(E LAB_SETTINGS_FILE="$TMP/none.yaml" bash scripts/settings.sh some_key fallback 2>&1); rc=$?
t "settings.sh answers a default with no settings file" "$([ "$rc" = 0 ] && [ "$out" = fallback ] && echo ok || echo "rc=$rc <<$out>>")"
out=$(E python3 scripts/generate_samplesheet.py 2>&1); rc=$?
t "the samplesheet generator prints usage (exit 2), not a traceback" "$([ "$rc" = 2 ] && grep -q '^usage:' <<<"$out" && echo ok || echo "rc=$rc <<$(head -2 <<<"$out")>>")"
out=$(E bash scripts/check_resource_contract.sh --help 2>&1); rc=$?
t "check_resource_contract.sh runs (any exit, never a missing-file error)" "$(grep -qE 'No such file|not found: .*hooks' <<<"$out" && echo "<<$out>>" || echo ok)"

echo "== 4. report.sh degrades loudly without plugin.json =="
out=$(E AGENTIC_BIOFLOW_REPORTS_DIR="$TMP/q" bash scripts/report.sh add --category env --command none --step probe 2>&1); rc=$?
t "report.sh add still queues a report" "$([ "$rc" = 0 ] && [ "$(find "$TMP/q" -name '*.report' 2>/dev/null | wc -l)" -ge 1 ] && echo ok || echo "rc=$rc <<$out>>")"
out=$(E AGENTIC_BIOFLOW_REPORTS_DIR="$TMP/q" bash scripts/report.sh send 2>&1)
t "report.sh send names what is missing instead of failing silently" "$(grep -q 'No repository to send to' <<<"$out" && grep -q 'REPORT_REPO' <<<"$out" && echo ok || echo "<<$out>>")"

fi

echo "== 5. the docs point at files that exist =="
# A doc that says a script is gone is not a dangling pointer.
missing=$(grep -rhE '`scripts/[A-Za-z0-9_./-]+[.](sh|py)`' commands skills docs README.md CLAUDE.md 2>/dev/null           | grep -viE '(are|is|was|were) (now )?(gone|removed|deleted)|no longer|used to|removed'           | grep -oE '`scripts/[A-Za-z0-9_./-]+[.](sh|py)`' | tr -d '`' | sort -u           | while read -r p; do [ -e "$p" ] || echo "$p"; done)
t "every scripts/<file> cited by commands/, skills/, docs/ exists" "$([ -z "$missing" ] && echo ok || echo "$missing" | head -5 | tr '\n' ' ')"
for need in docs/PITFALLS.md docs/SITE_ADAPTER.md docs/SETTINGS.md skills/operational/SKILL.md commands/setup.md commands/launch.md commands/runs.md; do
    t "the reduced tree still has $need" "$([ -s "$need" ] && echo ok || echo "missing or empty")"
done

# Self-tests: each shape of dependency, and one shape that is only prose, run
# against a mutated copy of the real tree. Skipped inside the nested run.
if [ -z "${WORKS_WITHOUT_HOST_SRC:-}" ]; then
    selffails=0
    mutate() { # mutate <want-rc> <label> <file> <line to append> [sed expr applied to the file instead]
        local S="$TMP/mut"; rm -rf "$S"; mkdir -p "$S"
        ( cd "$SRC" && tar -c scripts docs commands skills README.md CLAUDE.md 2>/dev/null ) | tar -x -C "$S"
        printf '%s
' "$4" >> "$S/$3"
        WORKS_WITHOUT_HOST_SRC="$S" bash "$SELF" >/dev/null 2>&1; local rc=$?
        [ "$rc" = "$1" ] || { echo "SELFTEST FAIL: $2 (rc $rc, wanted $1)"; selffails=$((selffails + 1)); }
    }
    mutate 0 "the untouched tree passes"                 scripts/intro.sh '# nothing added'
    mutate 0 "a comment naming a hook is only prose"     scripts/intro.sh '# see hooks/plugin_intro.sh for the card'
    mutate 1 "sourcing a hook fails"                     scripts/intro.sh '. "$(dirname "$0")/../hooks/in_use.sh"'
    mutate 1 "running a hook with bash fails"            scripts/settings.sh 'bash "$ROOT/hooks/in_use.sh"'
    mutate 1 "reading .claude-plugin as a requirement fails" scripts/settings.sh 'cat "$ROOT/.claude-plugin/marketplace.json"'
    mutate 1 "a script that does not parse fails"        scripts/intro.sh 'if then fi ('
    mutate 1 "a doc citing a script that is not there fails" docs/SETTINGS.md 'Run `scripts/no_such_script.sh` first.'
    [ "$selffails" -gt 0 ] && fails=$((fails + selffails))
fi

echo
if [ "$fails" -gt 0 ]; then echo "FAIL: $fails check(s) failed - the system does not work from docs/ and scripts/ alone"; exit 1; fi
echo "OK: with hooks/ and .claude-plugin/ removed, docs/ and scripts/ still work (degraded, not equivalent)"
