#!/bin/bash
# Constitution 6.0.0: three agreed rules joined (the run index, every write tool, a
# credential that arrives inside received data), each with the check that holds it.
# This test keeps the three rules honest: the files and tests they name exist, the
# write-tool list matches the tools the platform registers, and the roadmap and
# PRINCIPLES.md say what 6.0.0 says. Test cases: specs/constitution-6/test-case.md
# (TC-039 to TC-050).
#
# CONSTITUTION_FILE and MCP_SERVER_FILE point the check at scratch copies; the
# self-test at the bottom uses that to prove a new write tool turns it red.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
C="${CONSTITUTION_FILE:-.specify/memory/constitution.md}"
MCP="${MCP_SERVER_FILE:-platform/abf_platform/mcp_server.py}"
RM=docs/ROADMAP.md
PR=docs/PRINCIPLES.md
PT=platform/tests
fails=0
ok() { printf '%-92s ok\n' "$1"; }
bad() { printf '%-92s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
flat() { tr -d '\r' | tr '\n' ' ' | tr -s ' '; }
inn() { if printf '%s\n' "$2" | flat | grep -F -- "$3" >/dev/null; then ok "$1"; else bad "$1" "no '$3'"; fi; }
nin() { if printf '%s\n' "$2" | flat | grep -F -- "$3" >/dev/null; then bad "$1" "found '$3'"; else ok "$1"; fi; }

[ -r "$C" ] || { echo "FAIL: cannot read $C"; exit 1; }
[ -r "$MCP" ] || { echo "FAIL: cannot read $MCP"; exit 1; }

# The three rules, cut out of the constitution as one flattened text each.
RULE1=$(awk '/^- \*\*2\.\*\*/{f=1} f&&/^- \*\*3\.\*\*/{f=0} f' "$C" | flat)
SN=$(awk '/^## Safety Net/{f=1;next} /^## /{f=0} f' "$C")
RULE2=$(printf '%s\n' "$SN" | awk '/^- Every write tool of the platform/{f=1;print;next} f&&/^- /{f=0} f' | flat)
RULE3=$(printf '%s\n' "$SN" | awk '/^- The platform never stores a credential/{f=1;print;next} f&&/^- /{f=0} f' | flat)
[ -n "$RULE1" ] || bad "rule 1 (principle I.2) can be found"
[ -n "$RULE2" ] || bad "rule 2 (Safety Net write tools) can be found"
[ -n "$RULE3" ] || bad "rule 3 (Safety Net received credential) can be found"

# (a) each rule names its check files and each exists
check_files() { # <label> <rule text> <file>...
  local label=$1 rule=$2; shift 2
  local f
  for f in "$@"; do
    case "$rule" in *"$f"*) ;; *) bad "TC-039..041 $label names $f"; continue ;; esac
    if [ -f "$PT/$f" ]; then ok "TC-039..041 $label names $f and it exists"; else bad "TC-039..041 $label: $PT/$f does not exist"; fi
  done
}
check_files "rule 1" "$RULE1" test_nextflow_e2e.py
check_files "rule 2" "$RULE2" test_actions_layer.py test_human_channel.py test_resume_entrypoints.py test_keep_submissions.py
check_files "rule 3" "$RULE3" test_secrets.py test_nextflow_e2e.py test_human_channel.py

# (b) each named test prefix is defined in its file
defined() { # <rule text> <file> <prefix>...
  local rule=$1 file=$2; shift 2
  local p
  for p in "$@"; do
    case "$rule" in *"$p"*) ;; *) bad "TC-042..044 the rule names $p"; continue ;; esac
    if grep -qE "^[[:space:]]*(async )?def ${p}" "$PT/$file" 2>/dev/null; then ok "TC-042..044 $file defines $p"; else bad "TC-042..044 $file defines no 'def $p'"; fi
  done
}
defined "$RULE1" test_nextflow_e2e.py test_tc030_rebuild_gives_back_every_field test_tc031_nextflows_records_win_over_a_damaged_index
defined "$RULE2" test_actions_layer.py test_tcb04_ test_tcb08_
defined "$RULE2" test_human_channel.py test_tch09_ test_tca14_
defined "$RULE2" test_resume_entrypoints.py test_tc142_ test_tc144_
defined "$RULE2" test_keep_submissions.py test_tc034_ test_tc037_ test_tc038_
defined "$RULE3" test_secrets.py test_tc040_ test_tc042_ test_tc_i03_
defined "$RULE3" test_nextflow_e2e.py test_tc041_
defined "$RULE3" test_human_channel.py test_tcf10_f11_

# (c) the write tools the constitution lists are exactly the ones the platform registers
registered=$(tr -d '\r' < "$MCP" | grep -oE 'server\.tool\(name="[a-z_]+", *annotations=_(WRITES|STOPS)' | sed -E 's/.*name="([a-z_]+)".*/\1/' | sort -u | tr '\n' ' ')
listed=$(printf '%s\n' "$RULE2" | sed -nE 's/.*\(today ([^)]*)\).*/\1/p' | grep -oE '`[a-z_]+`' | tr -d '`' | sort -u | tr '\n' ' ')
if [ -z "$registered" ]; then bad "TC-045 the registered write tools can be read from $MCP"
elif [ -z "$listed" ]; then bad "TC-045 the Safety Net write-tool rule lists its tools in '(today ...)'"
elif [ "$registered" = "$listed" ]; then ok "TC-045 the rule lists exactly the registered write tools: $listed"
else bad "TC-045 write tools: registered [$registered] but the constitution lists [$listed]"; fi

# (d) ROADMAP: two rows gone, two rows kept with their 6.0.0 notes
WL=$(awk '/^## Principles waiting for a check/{f=1;next} f&&/^## /{f=0} f' "$RM")
nin "TC-047 ROADMAP has no run-index row" "$WL" "The platform's run index is never a second truth"
nin "TC-047 ROADMAP has no gates row" "$WL" "Gates live in the platform's action layer"
inn "TC-048 credential row kept word for word" "$WL" "The platform stores metadata only and never holds a site credential; credentials stay on the user's station agent"
inn "TC-048 credential row carries the 6.0.0 note" "$WL" "*Note (6.0.0): the half 'a credential inside received data is never stored' joined the Safety Net; the API refusing a credential field still has no check.*"
inn "TC-048 write-tool row kept word for word" "$WL" 'Every platform write tool (launch, delete, clear `work/`) refuses without the user'"'"'s confirmation step'
inn "TC-048 write-tool row carries the 6.0.0 note" "$WL" '*6.0.0 moved launch, cancel, resume, relaunch and forget into the Safety Net; delete and clear `work/` join when they exist with their refusal tests.*'

# (e) PRINCIPLES.md: a 6.0.0 entry, and no rule still "waiting"
P=$(cat "$PR")
inn "TC-049 PRINCIPLES.md has a constitution 6.0.0 entry" "$P" "constitution 6.0.0"
inn "TC-049 ...naming the run-index tests" "$P" "test_tc030"
inn "TC-049 ...naming the write-tool tests" "$P" "test_actions_layer.py"
inn "TC-049 ...naming the credential tests" "$P" "test_secrets.py"
inn "TC-049 ...and what did not move: the parity test (011a)" "$P" "011a"
inn "TC-049 ...the scope test" "$P" "scope test"
inn "TC-049 ...hooks/confirm_launch.sh still stands alone" "$P" "confirm_launch.sh"
nin "TC-050 PRINCIPLES.md no longer says the run-index rule waits" "$P" "that rule waits for its check"

# Self-test (TC-046): a write tool the constitution does not list turns (c) red.
if [ -z "${CONSTITUTION_6_INNER:-}" ]; then
  tmp=$(mktemp -d) && trap 'rm -rf "$tmp"' EXIT
  cp "$MCP" "$tmp/mcp_server.py"
  printf '\n    @server.tool(name="purge", annotations=_STOPS,\n        description="x")\n    def purge(): pass\n' >> "$tmp/mcp_server.py"
  if out=$(CONSTITUTION_6_INNER=1 MCP_SERVER_FILE="$tmp/mcp_server.py" bash "$0" 2>&1); then
    bad "TC-046 self-test: an unlisted write tool turns the check red" "stayed green"
  elif printf '%s\n' "$out" | grep 'registered .*purge' >/dev/null; then
    ok "TC-046 self-test: an unlisted write tool turns the check red and is named"
  else bad "TC-046 self-test: red, but did not name the extra tool"; fi
fi

if [ "$fails" -gt 0 ]; then echo "$fails check(s) failed"; exit 1; fi
echo "all constitution 6.0.0 checks passed"
