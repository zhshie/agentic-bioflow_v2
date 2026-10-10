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
has "version is 3.0.0 (2.0.0 made this change; 2.0.1, 2.1.0 and 3.0.0 came after)" "$C" '**Version**: 3.0.0'
has "the 2.0.0 amendment entry is still there"        "$C" '### 2.0.0 (2026-10-02)'
has "Last Amended is the day of the latest amendment" "$C" '**Last Amended**: 2026-10-08'
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
echo "== 3.0.0 amendment (platform direction): TC-002, TC-019, TC-040..TC-044, TC-047 =="
# TC-002: the 3.0.0 amendment record, and the three before it still there.
AM3=$(awk '/^### 3\.0\.0 \(2026-10-08\)/{f=1;next} /^##+ /{f=0} f' "$C")
am3_has() { if printf '%s\n' "$AM3" | tr '\n' ' ' | tr -s ' ' | grep -qF -- "$2"; then ok "$1"; else bad "$1" "no '$2' in the 3.0.0 amendment record"; fi; }
has "TC-002: the 3.0.0 (2026-10-08) amendment heading exists"          "$C" '### 3.0.0 (2026-10-08)'
has "TC-002: 2.0.0 amendment still there"                              "$C" '### 2.0.0 (2026-10-02)'
has "TC-002: 2.0.1 amendment still there"                              "$C" '### 2.0.1 (2026-10-05)'
has "TC-002: 2.1.0 amendment still there"                              "$C" '### 2.1.0 (2026-10-07)'
am3_has "TC-002: rationale quotes the maintainer's decision"           'the maintainer changed the project'
am3_has "TC-002: rationale cites ADR 0004"                             'docs/adr/0004'
am3_has "TC-002: rationale cites ADR 0005"                             'docs/adr/0005'
am3_has "TC-002: impact on existing deployments is stated"             'Impact on existing deployments.** None'
am3_has "TC-002: version is MAJOR"                                     '**Version.** MAJOR'
am3_has "TC-002: approval is the maintainer's"                         '**Approval.** The maintainer'

# TC-019: PRINCIPLES.md invariants 1 and 2 follow 3.0.0 and keep the scope pointer.
PA=$(awk '/^## A\. /{f=1;next} /^## /{f=0} f' docs/PRINCIPLES.md | tr '\n' ' ' | tr -s ' ')
pa_has() { if printf '%s\n' "$PA" | grep -qF -- "$2"; then ok "$1"; else bad "$1" "no '$2' in PRINCIPLES.md section A"; fi; }
pa_has "TC-019: invariant 1 restated: build only what Seqera cannot or will not do here" 'Build only what Seqera cannot or will not do here'
pa_has "TC-019: invariant 1 cites constitution 3.0.0"                  'constitution 3.0.0'
pa_has "TC-019: invariant 2 restated: Nextflow's own records are the truth" "Nextflow's own records are the truth about a run"
has "TC-019: PRINCIPLES.md still has 'in use'"                         docs/PRINCIPLES.md 'in use'
has "TC-019: PRINCIPLES.md still has 'Constitution 2.0.0'"             docs/PRINCIPLES.md 'Constitution 2.0.0'

# TC-040..TC-044: the Safety Net is the same words as on main. Compared as a whole
# against main, so no rule, no scope word, and no new paragraph can slip in.
sn_has "TC-040: never delete rawdata/ results/ analysis/"              'Never delete a user'"'"'s source data: `rawdata/`, `results/`, `analysis/`'
sn_has "TC-040: ...nor _references/ or the shared image cache"         "a run area's"
sn_has "TC-040: ...nor .nextflow/plugins/"                             'Never delete `.nextflow/plugins/`.'
sn_has "TC-041: work/ and cache deletion needs confirmation"           'Deleting `work/` or `.nextflow/cache/` requires the user'"'"'s explicit confirmation'
sn_has "TC-041: ...via hooks/confirm_cleanup.sh"                       '`hooks/confirm_cleanup.sh`'
sn_has "TC-042: a launch is shown in full and waits for confirmation"  'A launch command is shown in full and waits for explicit confirmation before it runs'
sn_has "TC-042: ...via hooks/confirm_launch.sh"                        '`hooks/confirm_launch.sh`'
sn_has "TC-043: credentials live only in the deployment's settings area" 'Credentials and personal details live only in the deployment'"'"'s own settings area'
sn_has "TC-043: ...Check: credentials_stay_in_settings_test.sh"        '`tests/credentials_stay_in_settings_test.sh`'
sn_has "TC-043: ...Check: windows_privacy_test.sh"                     '`tests/windows_privacy_test.sh`'
sn_has "TC-043: ...Check: inspect_sides_test.sh"                       '`tests/inspect_sides_test.sh`'
sn_has "TC-044: scope is still in use / unsure / silent / in_use.sh"   'The definition lives in `hooks/in_use.sh`.'
sn_has "TC-044: the three Check files are still named"                 '`tests/in_use_test.sh`, `tests/in_use_speed_test.sh`, `tests/constitution_scope_test.sh`'
sn_has "TC-044: only a MAJOR amendment changes the rules"              'change only by a MAJOR amendment of this constitution.'
if git rev-parse --verify -q main >/dev/null 2>&1 && git show main:.specify/memory/constitution.md >/dev/null 2>&1; then
  MAIN_SN=$(git show main:.specify/memory/constitution.md | awk '/^## Safety Net/{f=1;next} /^## /{f=0} f')
  if [ -n "$MAIN_SN" ] && [ "$MAIN_SN" = "$SN" ]; then
    ok "TC-040..TC-044: Safety Net section identical to main's, word for word"
  else
    bad "TC-040..TC-044: Safety Net section identical to main's" "$(diff <(printf '%s\n' "$MAIN_SN") <(printf '%s\n' "$SN") | head -5)"
  fi
else
  echo "note: git or the 'main' ref is unavailable; TC-040..TC-044 whole-section comparison skipped (fixed-string checks above still ran)"
fi

# Issue #71: the pinned-fingerprint check must run and must catch a change in a
# checkout that has no 'main' ref (CI's shallow clone). These cases build a
# scratch shallow clone of HEAD, overlay the working-tree copies of the files
# under test, and run this very script inside it. DOC_TEST_INNER stops the inner
# run from building clones of its own.
if [ -z "${DOC_TEST_INNER:-}" ]; then
  SCR=$(mktemp -d) || exit 1
  trap 'rm -rf "$SCR"' EXIT
  FPL='Safety Net section matches the pinned fingerprint'
  P1="git show ma""in:"; P2="rev-parse --verify -q ma""in"; P3="skip""ped"
  mkclone() { # mkclone <name> [withmain]: shallow clone, working-tree files overlaid
    local d="$SCR/$1"
    git clone -q --depth 1 --no-local "file://$ROOT" "$d" >/dev/null 2>&1 || return 1
    if [ "${2:-}" = withmain ]; then git -C "$d" branch main HEAD >/dev/null 2>&1; fi
    cp "$ROOT/$C" "$d/$C"; cp "$ROOT/CONTEXT.md" "$d/CONTEXT.md"
    cp "$HERE/$(basename "${BASH_SOURCE[0]}")" "$d/tests/"
    echo "$d"
  }
  inner() { # inner <clone> [PATH]: run the script in the clone; output in $OUT, status in $RC
    OUT=$(cd "$1" && DOC_TEST_INNER=1 PATH="${2:-$PATH}" "$BASH" "tests/$(basename "${BASH_SOURCE[0]}")" 2>&1); RC=$?
  }
  addsn() { sed -i '/^## Safety Net/a\
\
An extra sentence that is not in the pinned section.' "$1/$C"; }

  echo "== issue #71: the check runs and fails without a main ref =="
  D=$(mkclone nomain) || { bad "scratch shallow clone"; D=; }
  if [ -n "$D" ]; then
    if git -C "$D" rev-parse --verify -q main >/dev/null 2>&1; then bad "scratch clone really has no main ref"; else ok "scratch clone really has no main ref"; fi
    # TC-002
    inner "$D"
    if [ "$RC" = 0 ] && printf '%s\n' "$OUT" | grep -F "$FPL" | grep ' ok$' >/dev/null; then ok "TC-002: unchanged, no main: the fingerprint line runs and is ok"; else bad "TC-002: unchanged, no main: the fingerprint line runs and is ok" "rc=$RC"; fi
    if printf '%s\n' "$OUT" | grep -i "$P3" >/dev/null; then bad "TC-002: no skip note in the output"; else ok "TC-002: no skip note in the output"; fi
    # TC-007: a change outside the Safety Net does not trip it
    printf '\n### 9.9.9 (2099-01-01)\n\nA test amendment outside the Safety Net.\n' >> "$D/$C"
    inner "$D"
    if printf '%s\n' "$OUT" | grep -F "$FPL" | grep ' ok$' >/dev/null; then ok "TC-007: a change outside the Safety Net keeps the fingerprint ok"; else bad "TC-007: a change outside the Safety Net keeps the fingerprint ok"; fi
    cp "$ROOT/$C" "$D/$C"
    # TC-003: a change inside the Safety Net, no main
    addsn "$D"
    inner "$D"
    if [ "$RC" != 0 ] && printf '%s\n' "$OUT" | grep -F "$FPL" | grep 'FAIL' >/dev/null; then ok "TC-003: Safety Net changed, no main: fails on the fingerprint"; else bad "TC-003: Safety Net changed, no main: fails on the fingerprint" "rc=$RC"; fi
    NEWFP=$(printf '%s\n' "$OUT" | grep -oE 'current fingerprint: [0-9a-f]{64}' | head -1 | awk '{print $3}')
    if [ -n "$NEWFP" ]; then ok "TC-003: the failure prints the current fingerprint"; else bad "TC-003: the failure prints the current fingerprint"; fi
    if printf '%s\n' "$OUT" | grep -F 'An extra sentence' >/dev/null; then ok "TC-003: the failure shows the start of the current section"; else bad "TC-003: the failure shows the start of the current section"; fi
    # TC-008: same change, and the pinned value updated in the same PR: ok
    if [ -n "$NEWFP" ]; then
      sed -i -E "s/^PINNED_SN_SHA256=.*/PINNED_SN_SHA256=$NEWFP/" "$D/tests/$(basename "${BASH_SOURCE[0]}")"
      inner "$D"
      if printf '%s\n' "$OUT" | grep -F "$FPL" | grep ' ok$' >/dev/null; then ok "TC-008: change plus updated fingerprint passes"; else bad "TC-008: change plus updated fingerprint passes"; fi
    else
      bad "TC-008: change plus updated fingerprint passes" "no current fingerprint to pin"
    fi
  fi
  # TC-004: with a main ref present, the same change still fails the same way
  D=$(mkclone withmain withmain) || { bad "scratch clone with main"; D=; }
  if [ -n "$D" ]; then
    addsn "$D"
    inner "$D"
    if [ "$RC" != 0 ] && printf '%s\n' "$OUT" | grep -F "$FPL" | grep 'FAIL' >/dev/null; then ok "TC-004: Safety Net changed, main present: fails on the fingerprint"; else bad "TC-004: Safety Net changed, main present: fails on the fingerprint" "rc=$RC"; fi
  fi
  # TC-006: no hash tool: FAIL
  D=$(mkclone nohash) || { bad "scratch clone for TC-006"; D=; }
  if [ -n "$D" ]; then
    BIN="$SCR/bin"; mkdir -p "$BIN"
    for t in awk gawk mawk tr grep egrep head tail sed ls dirname basename cat diff cut sort wc mkdir rm cp git printf sleep env; do
      p=$(command -v "$t" 2>/dev/null) && [ -x "$p" ] && ln -sf "$p" "$BIN/$t"
    done
    inner "$D" "$BIN"
    if [ "$RC" != 0 ] && printf '%s\n' "$OUT" | grep -i 'no SHA-256 tool' >/dev/null; then ok "TC-006: no hash tool on PATH: fails and says so"; else bad "TC-006: no hash tool on PATH: fails and says so" "rc=$RC"; fi
    if printf '%s\n' "$OUT" | grep -i "$P3" >/dev/null; then bad "TC-006: ...and is not a skip note"; else ok "TC-006: ...and is not a skip note"; fi
  fi
  # TC-009: this file has no comparison against main and no skip branch left
  SELF="$HERE/$(basename "${BASH_SOURCE[0]}")"
  if grep -qF -e "$P1" -e "$P2" "$SELF"; then bad "TC-009: no comparison against the main ref left in this file"; else ok "TC-009: no comparison against the main ref left in this file"; fi
  if grep -v "^[[:space:]]*#" "$SELF" | grep -F "$P3" >/dev/null; then bad "TC-009: no skip branch left in this file"; else ok "TC-009: no skip branch left in this file"; fi
fi

# TC-047: the earlier scope assertions above run unchanged; only the version
# and date lines moved. Nothing else to add beyond the amendment trail.

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
