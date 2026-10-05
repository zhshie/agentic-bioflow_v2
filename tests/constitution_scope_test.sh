#!/bin/bash
# Feature 005 (#48): the constitution's Safety Net applies only to a session in
# which agentic-bioflow is in use, and every document that cites it says so the
# same way. This is a document check (TC-021, TC-022): the rule lives in
# .specify/memory/constitution.md, and a second statement of it elsewhere that
# reads differently is exactly what Governance forbids.
#
# The in-use definition itself is tested where it runs: tests/in_use_test.sh.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
fails=0

C=.specify/memory/constitution.md

ok() { printf '%-78s ok\n' "$1"; }
bad() { printf '%-78s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
has() { # has <label> <file> <fixed string>
  if grep -qF -- "$3" "$2" 2>/dev/null; then ok "$1"; else bad "$1" "no '$3' in $2"; fi
}
hasnt() { # hasnt <label> <file> <extended regex>
  local hit
  hit=$(grep -niE -- "$3" "$2" 2>/dev/null | head -3)
  if [ -z "$hit" ]; then ok "$1"; else bad "$1" "$2: $hit"; fi
}

echo "== TC-021: the constitution =="
has "version is 2.0.1 (PATCH on top of the 2.0.0 that made this change)" "$C" '**Version**: 2.0.1'
has "the 2.0.0 amendment entry is still there"        "$C" '### 2.0.0 (2026-10-02)'
has "Last Amended is the day of the latest amendment" "$C" '**Last Amended**: 2026-10-05'
has "Ratified date is untouched"               "$C" '**Ratified**: 2026-09-28'
# The Safety Net section opens with its scope. Read the section on its own so a
# mention elsewhere in the file cannot satisfy these.
SN=$(awk '/^## Safety Net/{f=1;next} /^## /{f=0} f' "$C")
sn_has() { # sn_has <label> <fixed string>
  if printf '%s\n' "$SN" | grep -qF -- "$2"; then ok "$1"; else bad "$1" "no '$2' in the Safety Net section"; fi
}
sn_has "Safety Net says it governs sessions in which the plugin is in use" 'in use'
sn_has "...condition 1: the session's own marker"                           'marker'
sn_has "...condition 2: the folder (deployment root or storage_root)"        'storage_root'
sn_has "...condition 3: the call itself (plugin script, tw, Seqera MCP)"     'Seqera'
sn_has "...unsure counts as in use"                                          'unsure'
sn_has "...and says what happens outside: the plugin stays silent"           'silent'
# The old wording said these rules hold everywhere, with no scope.
if printf '%s\n' "$SN" | grep -qF 'These rules are not subject to the principles above, MUST NOT be relaxed by any feature spec or'; then
  ok "the Safety Net still cannot be relaxed by a feature spec or plan"
else bad "the Safety Net still cannot be relaxed by a feature spec or plan"; fi
# An amendment record: rationale, impact on existing deployments, version.
AM=$(awk '/^## Amendment/{f=1;next} /^## /{f=0} f' "$C")
am_has() { if printf '%s\n' "$AM" | grep -qF -- "$2"; then ok "$1"; else bad "$1" "no '$2' in the Amendments section"; fi; }
am_has "amendment record exists and names 2.0.0"                    '2.0.0'
am_has "...names the issue (#48)"                                   '#48'
am_has "...names the 2026-10-02 subagent case"                      '2026-10-02'
am_has "...states the impact on existing deployments"               'existing deployments'
am_has "...says a session outside a deployment loses hook protection" 'no longer protected'
am_has "...records the maintainer's decision"                       'maintainer'

echo
echo "== TC-022: nothing else states the safety net as unconditional =="
has "PRINCIPLES.md says the safety net is scoped to in-use sessions"    docs/PRINCIPLES.md 'in use'
has "PRINCIPLES.md points at the constitution for the definition"       docs/PRINCIPLES.md 'Constitution 2.0.0'
has "CLAUDE.md says the hooks are silent unless the plugin is in use"   CLAUDE.md 'hooks/in_use.sh'
has "CLAUDE.md names the scope in its Safety Net pointer"               CLAUDE.md 'Constitution 2.0.0'
has "SITE_ADAPTER.md contract 6 says the direct-ssh reminder is scoped" docs/SITE_ADAPTER.md 'Constitution 2.0.0'
has "TESTING.md's manual walkthrough says to run it in a session in use" docs/TESTING.md 'Constitution 2.0.0'
has "README.md says the plugin is silent outside its own use"           README.md 'Constitution 2.0.0'
for h in confirm_launch confirm_cleanup confirm_walkthrough guard_plugin_files next_step session_start; do
  has "hooks/$h.sh header cites feature 005 and in_use.sh" "hooks/$h.sh" 'in_use.sh'
done
has "hooks/plugin_intro.sh header says it writes the marker" hooks/plugin_intro.sh 'in-use marker'
# Wording that would contradict the scope, anywhere a reader meets the net.
for f in CLAUDE.md README.md docs/PRINCIPLES.md docs/SITE_ADAPTER.md docs/TESTING.md docs/CONDITIONS.md; do
  hasnt "$f: no 'every session / all sessions / always on' wording" "$f" \
    'safety net[^.]*(in every (session|project|conversation)|in all sessions|always on|unconditional)|(every|all) (session|conversation)s?[^.]*safety net'
done

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
