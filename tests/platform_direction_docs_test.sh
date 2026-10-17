#!/bin/bash
# Constitution 3.0.0 / ADR 0004 (platform direction): the documents say what the
# amendment says they say. Document checks only: fixed strings and sections, in
# the style of tests/constitution_scope_test.sh. Test cases are in
# .specify/amendments/3.0.0-platform-direction/test-case.md; every assertion
# carries its TC id.
#
# Text is flattened (newlines to spaces) before matching, because the documents
# wrap lines; a phrase is found wherever it wraps.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
fails=0

C=.specify/memory/constitution.md
ADR1=$(ls docs/adr/0001-*.md 2>/dev/null | head -1)
ADR3=docs/adr/0003-host-strategy.md
ADR4=docs/adr/0004-self-hosted-platform-mcp-first.md
ADR5=docs/adr/0005-single-lab-multiuser.md
RM=docs/ROADMAP.md
POS=docs/POSITIONING.md
PAR=docs/SEQERA_PARITY.md
LA=docs/LAB_AGENTS.md
PR=docs/PRINCIPLES.md

ok() { printf '%-86s ok\n' "$1"; }
bad() { printf '%-86s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
flat() { tr -d '\r' | tr '\n' ' ' | tr -s ' '; }
# has <label> <file> <fixed string>: in the flattened file
has() {
  if [ -f "$2" ] && flat < "$2" | grep -qF -- "$3"; then ok "$1"; else bad "$1" "no '$3' in $2"; fi
}
# hasnt <label> <file> <ERE>: absent from the flattened file (case-insensitive)
hasnt() {
  local hit
  hit=$(flat < "$2" 2>/dev/null | grep -oiE -- ".{0,40}($3).{0,40}" | head -2)
  if [ -z "$hit" ]; then ok "$1"; else bad "$1" "$2: $hit"; fi
}
# sec <file> <start ERE> <end ERE>: lines from the start line (excluded) up to the next end line
sec() { awk -v s="$2" -v e="$3" '$0 ~ s {f=1;next} f && $0 ~ e {f=0} f' "$1"; }
# in <label> <section text> <fixed string>
inn() {
  if printf '%s\n' "$2" | flat | grep -qF -- "$3"; then ok "$1"; else bad "$1" "no '$3' in the section"; fi
}
nin() {
  if printf '%s\n' "$2" | flat | grep -qiE -- "$3"; then bad "$1" "found /$3/ in the section"; else ok "$1"; fi
}

echo "== US1: the constitution (TC-001, TC-003..TC-009) =="
LAST=$(grep -v '^[[:space:]]*$' "$C" | tail -1)
if [ "$LAST" = '**Version**: 5.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-17' ]; then
  ok "TC-001: last line is exactly the 5.0.0 version line"
else bad "TC-001: last line is exactly the 5.0.0 version line" "got: $LAST"; fi

P1=$(awk '/^### I\. /{f=1} /^### II\. /{f=0} f' "$C")
inn "TC-003: principle I is titled Build Only What Seqera Cannot or Will Not Do Here" "$P1" '### I. Build Only What Seqera Cannot or Will Not Do Here'
inn "TC-003: I.1 still names what Seqera/nf-core/another maintained tool does"  "$P1" 'name what Seqera, nf-core, or another maintained tool already uses for the same job'
inn "TC-003: I.1 reuse the open-source piece"                                   "$P1" 'reuse the open-source piece'
inn "TC-003: I.1 or say why it does not serve a lab here"                       "$P1" 'say why it does not serve a lab here'
inn "TC-003: I.1 reasons: cannot reach the site"                                "$P1" 'it cannot reach the site'
inn "TC-003: I.1 reasons: needs Seqera's Services"                              "$P1" "it needs Seqera's Services"
inn "TC-003: I.1 reasons: licence"                                              "$P1" 'its licence forbids the use'
inn "TC-003: I.1 reasons: price"                                                "$P1" 'or its price does'
inn "TC-009: header form '# Not <tool>: <reason>' kept"                         "$P1" '`# Not <tool>: <reason>`'
inn "TC-009: header form '# Nothing existing: <why>' kept"                      "$P1" '`# Nothing existing: <why>`'
inn "TC-009: I.1 Check is tests/scripts_name_their_alternative.sh"              "$P1" '*Check:* `tests/scripts_name_their_alternative.sh`.'
[ -f tests/scripts_name_their_alternative.sh ] && ok "TC-009: that Check file exists" || bad "TC-009: that Check file exists"

inn "TC-004: I.2 Nextflow's own records (trace, report, log, nf-tower events) are the truth" "$P1" "Nextflow's own records (trace, report, log, and the events its \`nf-tower\` plugin emits) are the truth about a run"
inn "TC-004: ...Seqera Platform's display counts while the plugin uses it"        "$P1" 'While the plugin uses Seqera Platform, Platform shows them'
inn "TC-004: ...no second copy of a run's state in this repository"               "$P1" "No file in this repository MAY keep a second copy of a run's state"
inn "TC-004: ...no state machine and no monitoring daemon"                        "$P1" 'no state machine and no monitoring daemon beyond the channels its check allow-lists'
inn "TC-005: ...at most one submission path of our own"                            "$P1" 'There MAY be at most one submission path of our own'
inn "TC-005: ...it is the station agent's launch job, the way Seqera Platform does" "$P1" "the station agent's launch job, which hands the Nextflow head job to the site's own scheduler the way Seqera Platform does"
nin "TC-005: ...not 'exactly one'"                                                 "$P1" 'exactly one'
inn "TC-006: ...runs only after the user has seen the full launch command and confirmed it" "$P1" 'runs only after the user has seen the full launch command and confirmed it'
inn "TC-007: ...after the hand-off everything comes from Nextflow's records"       "$P1" "everything known about the run comes from Nextflow's records"
inn "TC-004: ...Seqera's nouns where the backend is Seqera"                       "$P1" "follows Seqera's nouns"
inn "TC-008: I.2 Check is tests/no_second_run_state_test.sh, covering scripts/ and platform/" "$P1" '*Check:* `tests/no_second_run_state_test.sh` (its submission scan covers `scripts/` and `platform/`).'
inn "TC-005: where Seqera's display and Nextflow's records disagree, Nextflow's win" "$P1" "where Platform's display and Nextflow's own records disagree, Nextflow's records win"
if grep -qi 'run index' "$C"; then bad "TC-006: the constitution does not contain 'run index'" "$(grep -ni 'run index' "$C" | head -2)"; else ok "TC-006: the constitution does not contain 'run index'"; fi
inn "TC-007: principle I rationale cites docs/adr/0004"                           "$P1" 'docs/adr/0004'
nin "TC-007: ...and no longer attributes it to docs/adr/0001"                     "$P1" 'docs/adr/0001'

AM3=$(sec "$C" '^### 3[.]0[.]0 [(]2026-10-08[)]' '^##+ ')
inn "TC-008: scope condition 3 names only Seqera or Tower MCP tools today"        "$AM3" 'Scope condition 3 names Seqera or Tower MCP tools only'
inn "TC-008: platform's own MCP tools: decided by the amendment that moves a gate" "$AM3" "whether a call to the platform's own MCP tools counts as in use is decided by the amendment that moves a gate there"
# "Gates in the tool layer" is not a rule here: outside the amendment record the
# constitution never says it (it is in the ROADMAP waiting list).
RULES=$(awk '/^## Core Principles/{f=1} /^## Development Workflow/{f=0} f' "$C")
nin "TC-008: 'tool layer' is not written into the principles or the Safety Net"   "$RULES" 'tool layer'
nin "TC-050: 'action layer' is not written into the principles or the Safety Net"  "$RULES" 'action layer'

# Issue #71: the TC-034 check must run, and must catch a removed term, in a
# checkout that has no 'main' ref (CI's shallow clone). These cases build scratch
# shallow clones of HEAD, overlay the working-tree CONTEXT.md and this script,
# and run this very script inside. DOC_TEST_INNER stops the inner run from
# building clones of its own.
if [ -z "${DOC_TEST_INNER:-}" ]; then
  SCR=$(mktemp -d) || exit 1
  trap 'rm -rf "$SCR"' EXIT
  T34='TC-034: every pinned CONTEXT.md term is still defined'
  P1="git show ma""in:"; P2="rev-parse --verify -q ma""in"; P3="skip""ped"
  SELFN=$(basename "${BASH_SOURCE[0]}")
  mkclone() { # mkclone <name> [withmain]
    local d="$SCR/$1"
    git clone -q --depth 1 --no-local "file://$ROOT" "$d" >/dev/null 2>&1 || return 1
    if [ "${2:-}" = withmain ]; then
      git -C "$d" show-ref --verify --quiet refs/heads/main || git -C "$d" branch main HEAD >/dev/null 2>&1
    else # scratch-clone-main: the clone inherits the source branch (main on push CI); detach and drop it
      git -C "$d" checkout -q --detach >/dev/null 2>&1
      if git -C "$d" show-ref --verify --quiet refs/heads/main; then git -C "$d" branch -q -D main >/dev/null 2>&1; fi
    fi
    cp "$ROOT/CONTEXT.md" "$d/CONTEXT.md"; cp "$HERE/$SELFN" "$d/tests/"
    echo "$d"
  }
  inner() { OUT=$(cd "$1" && DOC_TEST_INNER=1 "$BASH" "tests/$SELFN" 2>&1); RC=$?; }
  t34ok() { printf '%s\n' "$OUT" | grep -F "$T34" | grep ' ok$' >/dev/null; }

  echo "== issue #71: TC-034 runs and fails without a main ref =="
  for mode in nomain withmain; do
    D=$(mkclone "c-$mode" "$([ "$mode" = withmain ] && echo withmain)") || { bad "scratch clone ($mode)"; continue; }
    # scratch-clone-main TC-006: nomain clones are detached with no main; withmain clones have main
    if [ "$mode" = nomain ]; then
      if ! git -C "$D" show-ref --verify --quiet refs/heads/main && [ -z "$(git -C "$D" symbolic-ref -q HEAD 2>/dev/null)" ]; then ok "nomain clone: no main ref, detached (scratch-clone-main TC-006)"; else bad "nomain clone: no main ref, detached (scratch-clone-main TC-006)"; fi
    else
      if git -C "$D" show-ref --verify --quiet refs/heads/main; then ok "withmain clone has a main ref (scratch-clone-main TC-006)"; else bad "withmain clone has a main ref (scratch-clone-main TC-006)"; fi
    fi
    # TC-010: unchanged
    inner "$D"
    if [ "$RC" = 0 ] && t34ok; then ok "TC-010: unchanged, $mode: TC-034 runs and is ok"; else bad "TC-010: unchanged, $mode: TC-034 runs and is ok" "rc=$RC"; fi
    if printf '%s\n' "$OUT" | grep -i "$P3" >/dev/null; then bad "TC-010: $mode: no skip note in the output"; else ok "TC-010: $mode: no skip note in the output"; fi
    # TC-014: a new term may be added freely
    printf '\n**Zebra stripes**\nA term added for the test.\n' >> "$D/CONTEXT.md"
    inner "$D"
    if [ "$RC" = 0 ] && t34ok; then ok "TC-014: $mode: an added term still passes"; else bad "TC-014: $mode: an added term still passes" "rc=$RC"; fi
    cp "$ROOT/CONTEXT.md" "$D/CONTEXT.md"
    # TC-011 (no main) / TC-012 (main present): a removed term fails and is named
    sed -i 's/^\*\*Run index\*\* /Run index /' "$D/CONTEXT.md"
    inner "$D"
    lbl="TC-01$([ "$mode" = nomain ] && echo 1 || echo 2): $mode: removing 'Run index' fails TC-034 and names it"
    if [ "$RC" != 0 ] && printf '%s\n' "$OUT" | grep -F 'TC-034' | grep 'FAIL' | grep -F '[Run index]' >/dev/null; then ok "$lbl"; else bad "$lbl" "rc=$RC"; fi
  done
  # TC-015: this file has no comparison against main and no skip branch left
  SELF="$HERE/$SELFN"
  if grep -qF -e "$P1" -e "$P2" "$SELF"; then bad "TC-015: no comparison against the main ref left in this file"; else ok "TC-015: no comparison against the main ref left in this file"; fi
  if grep -v "^[[:space:]]*#" "$SELF" | grep -F "$P3" >/dev/null; then bad "TC-015: no skip branch left in this file"; else ok "TC-015: no skip branch left in this file"; fi
fi

echo
echo "== US2: ADRs (TC-011..TC-018, TC-037, TC-039) =="
[ -f "$ADR4" ] && ok "TC-011: $ADR4 exists" || bad "TC-011: $ADR4 exists"
has "TC-011: ADR 0004 supersedes ADR 0001"                       "$ADR4" 'Supersedes ADR 0001'
has "TC-011: self-hosted platform"                               "$ADR4" 'We build and host our own platform'
has "TC-011: Tower-compatible API"                               "$ADR4" 'Tower-compatible'
has "TC-011: ...so the nf-tower plugin reports straight to it"   "$ADR4" '`nf-tower` plugin (Apache-2.0)'
has "TC-011: ...via tower.endpoint"                              "$ADR4" '`tower.endpoint`'
has "TC-011: every AI path goes through the MCP tools"           "$ADR4" 'Every AI path goes through the MCP tools'
has "TC-011: ...the platform's own chat is one such client"      "$ADR4" "the platform's own chat on the web, which connects to the model the user chooses, calls them"
has "TC-011: the platform stores metadata only"                  "$ADR4" 'The platform stores metadata only'
has "TC-011: site credentials never reach the platform"          "$ADR4" 'site credentials never reach the platform'
has "TC-011: station agent connects outbound only"               "$ADR4" 'connects outbound only to the platform'

O4=$(sec "$ADR4" '^## Considered Options' '^## ')
inn "TC-012: rejected: our own general-purpose harness"           "$O4" 'Write our own general-purpose harness**: rejected; harnesses are maintained by others'
inn "TC-012: ...the platform's chat drives only its own tools"    "$O4" "The platform's chat drives only the platform's own tools"
nin "TC-012: 'harness or chat UI' is no longer listed as rejected" "$O4" 'harness or chat UI'
inn "TC-012: 'only MCP, no chat' is replaced on 2026-10-09"       "$O4" "Only MCP, no chat of our own (this record's first version, 2026-10-08)**: replaced on 2026-10-09"
nin "TC-012: ...and is not listed as rejected"                    "$(printf '%s\n' "$O4" | flat | grep -oE 'Only MCP, no chat.{0,200}' | sed -E 's/- \*\*.*//')" 'rejected'
inn "TC-012: rejected: fork of the archived nf-tower CE (MPL-2.0)" "$O4" 'Fork nf-tower Community Edition'
inn "TC-012: ...MPL-2.0 and archived"                             "$O4" 'MPL-2.0'
inn "TC-012: ...archived"                                         "$O4" 'archived'
inn "TC-012: rejected: organisations, workspaces, teams, SSO"     "$O4" 'Organisations, workspaces, teams, SSO**: rejected'
inn "TC-012: rejected: Studios"                                   "$O4" 'Studios**: rejected'

Q4=$(sec "$ADR4" '^## Consequences' '^## ')
inn "TC-013: consequences cite constitution 3.0.0"                "$Q4" 'Constitution 3.0.0'
inn "TC-013: ...ADR 0003 is revised"                              "$Q4" 'ADR 0003 is revised'
inn "TC-013: ...ADR 0001's Terms-of-Use reason still holds"       "$Q4" "ADR 0001's Terms-of-Use reason still holds"
inn "TC-013: ...ADR 0002 stands, revenue gains a hosted service"  "$Q4" 'ADR 0002 stands for the code; the revenue gains a hosted service'
inn "TC-013: ...Seqera Platform is the reference, narrowed to what a lab here uses" "$Q4" 'Seqera Platform is the reference: features follow its public documentation, narrowed to what a lab here uses'
if flat < "$ADR4" | grep -qiF "rebuilding part of a company"; then bad "TC-013: ADR 0004 has no 'rebuilding part of a company'"; else ok "TC-013: ADR 0004 has no 'rebuilding part of a company'"; fi
if flat < "$ADR4" | grep -qF "重做"; then bad "TC-013: ADR 0004 has no 重做"; else ok "TC-013: ADR 0004 has no 重做"; fi

[ -f "$ADR5" ] && ok "TC-014: $ADR5 exists" || bad "TC-014: $ADR5 exists"
has "TC-014: role member"                                         "$ADR5" 'A **member** runs their own analyses'
has "TC-014: role PI sees every run in the lab"                   "$ADR5" 'A **PI** sees every run in the lab'
has "TC-014: PI spends nothing by default"                        "$ADR5" 'spends nothing by default'
has "TC-014: each person uses their own NCHC account and credential" "$ADR5" 'Each person uses their own NCHC account and their own credential'
has "TC-014: ...held by their own station agent"                  "$ADR5" 'held by their own station agent'
has "TC-014: nothing sits above a lab"                            "$ADR5" 'nothing sits above a lab'
O5=$(sec "$ADR5" '^## Considered Options' '^## ')
inn "TC-014: no organisation / workspace / team / SSO (rejected)" "$O5" 'organisation → workspace → team'
inn "TC-014: ...SSO"                                              "$O5" 'SSO'
inn "TC-014: ...rejected"                                         "$O5" 'rejected as more to learn than a lab needs'

if [ -n "$ADR1" ]; then
  if head -5 "$ADR1" | flat | grep -qF 'Superseded by ADR 0004 (2026-10-08)'; then ok "TC-015: ADR 0001 opens with 'Superseded by ADR 0004 (2026-10-08)'"
  else bad "TC-015: ADR 0001 opens with 'Superseded by ADR 0004 (2026-10-08)'"; fi
  has "TC-018: ADR 0001 body kept: Terms of Use reason" "$ADR1" 'Terms of Use also forbid accessing its Services'
  has "TC-018: ADR 0001 body kept: the decision text"  "$ADR1" 'The Prototype uses Seqera Platform as its execution backend and interface'
else bad "TC-015: ADR 0001 file found"; fi

has "TC-016: host is any MCP client"                              "$ADR3" 'the host is whatever MCP client the user already has'
has "TC-016: Claude Desktop first"                                "$ADR3" 'Claude Desktop first'
has "TC-016: the platform's own chat is one more host"            "$ADR3" "The platform's own chat (ADR 0004, Stage 3) is one more host of the same tools"
has "TC-016: general-purpose harness of our own still rejected"   "$ADR3" 'Our own general-purpose harness**: rejected in ADR 0004'
has "TC-016: gates move into the platform's tool layer"           "$ADR3" "move into the platform's tool layer"
has "TC-016: a host without hooks still cannot skip them"         "$ADR3" 'a host without hooks still cannot skip them'
has "TC-016: the Claude Code plugin becomes a thin shell"         "$ADR3" 'becomes a thin shell'
has "TC-016: the Codex adapter stage is dropped"                  "$ADR3" '(the Codex adapter) is dropped'
has "TC-017: licence fact kept: LICENSE.md"                       "$ADR3" 'LICENSE.md'
has "TC-017: licence fact kept: no routing to non-Claude models"  "$ADR3" "doesn't support routing Claude Code to non-Claude models through any gateway"
has "TC-017: local-model fact kept: Ollama --oss"                 "$ADR3" '`--oss` (Ollama, LM Studio)'

# TC-037: the development rule, in the ADR.
has "TC-037: ADR 0004: development never goes through Seqera's Services, MCP server or tw" "$ADR4" "development and testing never go through Seqera's Services, its MCP server or \`tw\`"
# TC-039: no site credential on the platform: ADR 0004, ADR 0005, ROADMAP waiting list.
has "TC-039: ADR 0004: platform stores metadata only"             "$ADR4" 'The platform stores metadata only'
has "TC-039: ADR 0004: credentials stay with the station agent"   "$ADR4" 'holds the SSH connection the user opened'
has "TC-039: ADR 0005: platform stores metadata only"             "$ADR5" 'The platform stores metadata only'
has "TC-039: ADR 0005: credential held by the station agent, never by the platform" "$ADR5" 'never by the platform'
has "TC-039: ROADMAP waiting row: metadata only, never holds a site credential" "$RM" 'The platform stores metadata only and never holds a site credential'
hasnt "TC-039: no design text has the platform storing a NCHC password or key" "$ADR4" 'platform (stores|holds|keeps)[^.]{0,40}(password|passphrase|private key)'
hasnt "TC-039: ...ADR 0005"                                       "$ADR5" 'platform (stores|holds|keeps)[^.]{0,40}(password|passphrase|private key)'

echo
echo "== US3: other documents (TC-020..TC-029, TC-032..TC-034, TC-038, TC-059) =="
# TC-020: PRINCIPLES.md "Where each piece belongs"
WP=$(sec "$PR" '^## Where each piece belongs' '^## |^---$')
inn "TC-020: the platform is an MCP server because any harness must be able to call it" "$WP" 'The platform is an MCP server'
inn "TC-020: ...any harness"                                      "$WP" 'whatever harness the user brings'
inn "TC-020: judgment stays in skills, MCP tools only act"        "$WP" 'judgment and procedure stay in skills and `docs/`, MCP tools only act'
inn "TC-020: the 'a tool cannot carry judgment' reason is kept as the reason for the split" "$WP" 'cannot carry procedure or judgment'
if grep -rIl --include='*.md' -iE 'not an MCP server' . 2>/dev/null | grep -v -e '^./.git/' -e '^./.specify/amendments/' -e '^./docs/LAB_AGENTS.md$' | grep -q .; then
  bad "TC-020: no document states 'Not an MCP server' as a current rule (LAB_AGENTS history aside)" "$(grep -rIl --include='*.md' -iE 'not an MCP server' . | grep -v -e '^./.git/' -e '^./.specify/amendments/' -e '^./docs/LAB_AGENTS.md$' | head -3)"
else ok "TC-020: no document states 'Not an MCP server' as a current rule (LAB_AGENTS history aside)"; fi
hasnt "TC-020: PRINCIPLES.md 'Where each piece belongs' no longer says the plugin is not an MCP server" "$PR" 'this plugin is not, and does not wrap itself in, an MCP server'

# TC-021: LAB_AGENTS R7 and section 8; TC-033: H3 trigger paragraph kept.
R7=$(grep -F '| R7 |' "$LA")
if printf '%s' "$R7" | grep -qF 'Reversed by ADR 0004'; then ok "TC-021: R7 verdict is 'Reversed by ADR 0004'"; else bad "TC-021: R7 verdict is 'Reversed by ADR 0004'" "$R7"; fi
S8=$(sec "$LA" '^## 8[.] ' '^## ')
inn "TC-021: section 8 title says reversed by ADR 0004"           "$(grep -F '## 8. ' "$LA")" 'reversed by ADR 0004'
inn "TC-021: section 8 states the same conclusion (self-hosted platform, MCP the only AI entry)" "$S8" 'only AI entry point is an MCP server (ADR 0004)'
inn "TC-033: section 8 keeps the H3 trigger paragraph"            "$S8" 'the H3 case is the only host this repo now describes that cannot'
inn "TC-033: ...and marks the rest as history"                    "$S8" 'The rest of this section is kept as history'

# TC-022: ROADMAP stages 0-5, done-when, dropped line.
STG=$(sec "$RM" '^## Stages' '^## ')
inn "TC-022: stage table has a Done when column"                  "$STG" '| Done when |'
inn "TC-022: stage 0 is docs (direction recorded)"                "$STG" '| 0 | **Direction recorded**'
inn "TC-022: stage 1 is the station agent (feature 007)"          "$STG" '| 1 | **Station agent** (feature 007)'
inn "TC-022: stage 2 is platform core (008-010)"                  "$STG" '| 2 | **Platform core** (features 008–010)'
inn "TC-022: stage 3 is web (011-014)"                            "$STG" '| 3 | **Web** (features 011–014, 016)'
inn "TC-022: 014 is the platform's chat, user-chosen model, MCP tools only" "$STG" "014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009"
inn "TC-022: stage 4 is cloud compute"                            "$STG" '| 4 | **Cloud compute**'
inn "TC-022: stage 5 is model-neutral shipping"                   "$STG" '| 5 | **Model-neutral shipping**'
# every stage row has a non-empty last cell
for n in 0 1 2 3 4 5; do
  row=$(printf '%s\n' "$STG" | grep -E "^\| $n \|" | head -1)
  last=$(printf '%s' "$row" | awk -F'|' '{print $(NF-1)}' | tr -d ' ')
  [ -n "$last" ] && ok "TC-022: stage $n has a done-when" || bad "TC-022: stage $n has a done-when" "$row"
done
inn "TC-022: a 'Dropped' line names the old progress page and the Codex adapter" "$STG" 'Dropped on 2026-10-08: the old "local page to see progress and results"'
inn "TC-022: ...and the old Codex adapter stage"                  "$STG" 'the old "Codex adapter" stage'

# TC-023: waiting list, five new rows plus re-staged old ones.
WL=$(sec "$RM" '^## Principles waiting for a check' '^## ')
inn "TC-023: new row: run index rebuildable (stage 2)"            "$WL" "The platform's run index is never a second truth"
inn "TC-023: new row: metadata only, no site credential"          "$WL" 'The platform stores metadata only and never holds a site credential'
inn "TC-023: new row: write tools refuse without a confirmation step" "$WL" 'Every platform write tool (launch, delete, clear `work/`) refuses without the user'"'"'s confirmation step'
inn "TC-023: new row: PI and member roles enforced"               "$WL" 'PI and member roles are enforced'
inn "TC-023: row: gates live in the platform's action layer, a person answers on a human channel" "$WL" "Gates live in the platform's action layer, which the MCP tools and the web pages both call, and a person answers each gate on a human channel; the plugin's hooks become callers"
inn "TC-023: ...check: refused through the MCP tool and through the web route" "$WL" "An unconfirmed launch is refused through the MCP tool and through the web route"
nin "TC-023: ...the old 'platform's tool layer' gate row is gone" "$WL" "Gates live in the platform's tool layer"
inn "TC-024: new row: every entry reaches the same action"         "$WL" "Every entry (MCP client, web page, platform chat, shell) reaches the same action"
inn "TC-024: ...check: parity test, mcp_server and web import only actions" "$WL" 'A parity test: every action has an MCP tool and a web route, and `mcp_server` and the web import only `actions`'
inn "TC-024: new row: a call to the platform's own tools counts as in use" "$WL" "A call to the platform's own tools counts as a session in use"
inn "TC-024: ...check: scope test covers the platform's tools"     "$WL" "The Safety Net's scope test covers the platform's tools"
inn "TC-024: new row: web pages and tools match one to one"        "$WL" "The web pages and the tools match one to one"
inn "TC-023: ...with their stages: 2, 1–2, 1–2, 2, 1–2"          "$WL" '| 1–2 |'
cnt=$(printf '%s\n' "$WL" | grep -cE '^\| ' || true)
# header + separator + 5 new + 6 original + 1 split row = 13 or more
[ "${cnt:-0}" -ge 12 ] && ok "TC-023: waiting list has the 5 new rows on top of the 6 original (rows incl. header: $cnt)" || bad "TC-023: waiting list row count" "$cnt rows"
inn "TC-023: old row rewritten: host reaches launch/delete only through tools that carry their own gate" "$WL" 'A host reaches launch and delete only through tools that carry their own gate'
nin "TC-023: ...the old 'may query but never launch or delete' wording is gone" "$WL" 'may query but never'
cnt16=$(printf '%s\n' "$WL" | grep -cE '^[|]' || true)
[ "${cnt16:-0}" = 17 ] && ok "TC-025: waiting list has 17 table lines (15 rows + header + separator)" || bad "TC-025: waiting list has 17 table lines" "$cnt16 lines"
# old stage numbers are gone: nothing waits for a stage that no longer exists
if printf '%s\n' "$WL" | grep -qE '\| (6|7) \|[[:space:]]*$'; then bad "TC-023: no row waits for stage 6 or 7"; else ok "TC-023: no row waits for stage 6 or 7"; fi

OQ=$(sec "$RM" '^## Open questions' '^## ')
inn "TC-024: open questions gain NCHC M6"                         "$OQ" 'NCHC (M6'
inn "TC-024: ...may a login node keep a process running"          "$OQ" 'may a login node keep a process running'
inn "TC-024: ...automation on one person's account allowed?"      "$OQ" "automation on one person's account allowed"

has "TC-025: local-model evaluation kept, retitled under Stage 5" "$RM" '## Local-model evaluation (Stage 5)'
hasnt "TC-025: no 'stages 3 and 6' left"                           "$RM" 'stages 3 and 6'
hasnt "TC-025: no 'running on Codex' left"                         "$RM" 'running on Codex'
inn "TC-025: the evaluation body is still there (20 runs, 18 of 20)" "$(sec "$RM" '^## Local-model evaluation' '^## ')" 'Pass threshold: 18 of 20 runs'

# TC-026 / TC-027: POSITIONING
has "TC-026: one-line positioning is 台灣版 Seqera"                 "$POS" '> 台灣版 Seqera'
has "TC-026: one-liner: own chat, model you choose, plus your own AI via MCP" "$POS" '平台有自己的聊天介面，可接你選的模型；也可以用你已經在用的 AI（Claude Desktop 等）透過 MCP 接上'
has "TC-026: feature 2: four entries" "$POS" '平台有四個入口：你自己的 AI（接 MCP 網址）、平台網頁、平台自己的聊天介面、命令列'
hasnt "TC-026: the old 'MCP only' lead is gone" "$POS" '平台只開 MCP'
has "TC-029: feature 2: web pages need no model; chat is the model-using entry" "$POS" '沒有 AI 工具的成員直接用平台網頁點選，不需要任何模型；想用對話的，用平台自己的聊天介面，接自己選的模型（自己的 API key 或本地模型），它走的是同一組 MCP 工具（2026-10-09 加入，`docs/adr/0004`；2026-10-15 四個入口，`docs/adr/0006`）。'
hasnt "TC-029: the old 'chat interface on the web pages' wording is gone" "$POS" '沒有 AI 工具的成員，用平台網頁上的聊天介面'
has "TC-028: feature 2: the person presses yes, not the model" "$POS" '判斷留在 skill，工具只做動作，每個寫入動作都要你本人確認——按 yes 的是人，不是模型（`docs/adr/0006`）。'
hasnt "TC-028: the old gate sentence is gone" "$POS" '每個寫入動作都要你確認（`docs/adr/0003`）'
has "TC-026: feature 2: own API key or local model, same MCP tools" "$POS" '接自己選的模型（自己的 API key 或本地模型），它走的是同一組 MCP 工具'
hasnt "TC-026: POSITIONING no longer says the platform does not do its own chat" "$POS" '平台不自己做對話'
has "TC-027: competitor table: Seqera MCP, no confirmation mechanism in its docs" "$POS" '文件中查不到確認機制'
has "TC-027: competitor table: pynf-agent"                        "$POS" '**pynf-agent**'
has "TC-027: competitor table: Agent Skills standard"             "$POS" '**Agent Skills 標準**'
has "TC-027: competitor table: MCP Apps"                          "$POS" '**MCP Apps**'
has "TC-027: competitor table: MadCowork"                         "$POS" '**MadCowork**'
has "TC-027: MadCowork: only madcowork-module-spec found"         "$POS" 'madcowork-module-spec'
has "TC-027: MadCowork: product claims from word of mouth, no public source" "$POS" '產品說法依口述、無公開來源'
has "TC-027: a section 十個突破點 exists, marked 推論"              "$POS" '## 十個突破點（推論）'
has "TC-027: the Codex local-model line is a superseded past decision" "$POS" '已被取代的過去決定（2026-09-28）：「本地模型套 Claude Code 只做實驗；產品的本地模型跑在 Codex 上。」'

# TC-028: SEQERA_PARITY.md
has "TC-028: original count 84"                                   "$PAR" 'the original count was 84'
has "TC-028: 83 named items"                                      "$PAR" 'lists 83 named items'
has "TC-028: per-section counts A 16, B 11, C 1, D 5, E 9, F 13, G 2, H 7, I 3, J 9, K 7" "$PAR" 'A 16, B 11, C 1, D 5, E 9, F 13, G 2, H 7, I 3, J 9, K 7'
has "TC-028: one K item counted and never named"                  "$PAR" 'one item of section K was counted and never named'
has "TC-028: no item invented to fill the gap"                    "$PAR" 'No item is invented to fill the gap'
has "TC-028: source line: 2026-10-08, Seqera's public documentation, not through its services" "$PAR" "Compiled 2026-10-08 by the development lead from Seqera's public documentation only"
# The section headings carry the counts: they must match the sentence and sum to 83.
sum=0; heads=""
while IFS= read -r h; do
  letter=$(printf '%s' "$h" | sed -E 's/^## ([A-K])\..*/\1/')
  n=$(printf '%s' "$h" | sed -E 's/.*\(([0-9]+) (named )?items?[;)].*/\1/')
  heads="$heads $letter$n"; sum=$((sum+n))
done < <(grep -E '^## [A-K]\. ' "$PAR")
[ "$sum" = 83 ] && ok "TC-028: the section headings' counts sum to 83 ($heads )" || bad "TC-028: the section headings' counts sum to 83" "sum=$sum ($heads )"
[ "$(echo $heads)" = "A16 B11 C1 D5 E9 F13 G2 H7 I3 J9 K7" ] && ok "TC-028: ...and equal the sentence's per-section counts" || bad "TC-028: heading counts equal the sentence's" "$heads"
# ★ items: lines that name an item, not the legend line that defines the mark.
stars=$(grep -F '★' "$PAR" | grep -vF 'marked ★' | wc -l | tr -d ' ')
[ "$stars" = 4 ] && ok "TC-028: exactly 4 items marked ★ (legend excluded)" || bad "TC-028: exactly 4 items marked ★" "found $stars"
for item in 'Dashboard' 'Parameter form from the pipeline schema' 'Reports' 'two-role lab'; do
  if grep -F '★' "$PAR" | grep -vF 'marked ★' | grep -qF -- "$item"; then ok "TC-028: ★ item: $item"; else bad "TC-028: ★ item: $item"; fi
done

if grep -F 'Co-Scientist' "$PAR" | grep -F 'Build' | grep -qvF '★'; then ok "TC-028: Co-Scientist row gains Build and carries no ★"; else bad "TC-028: Co-Scientist row gains Build and carries no ★"; fi
has "TC-028: Co-Scientist Build is the platform's own chat (Stage 3, feature 014)" "$PAR" "Build: the platform's own chat with the model the user chooses (Stage 3, feature 014)"

# TC-029 / TC-034: CONTEXT.md
PLAT=$(awk 'index($0,"**Platform** ")==1{f=1;next} f&&/^$/{exit} f' CONTEXT.md)
inn "TC-029: Platform is reached through MCP tools from its own chat or the user's harness" "$PLAT" "reached through MCP tools from its own chat or from the user's harness"
for term in 'Platform' 'Station agent' 'Run index' 'MCP tool layer'; do
  if grep -qE "^\*\*$term\*\* " CONTEXT.md; then ok "TC-029: CONTEXT.md defines $term"; else bad "TC-029: CONTEXT.md defines $term"; fi
done
for term in 'Platform' 'Station agent' 'Run index' 'MCP tool layer'; do
  def=$(awk -v t="**$term** " 'index($0,t)==1{f=1;next} f&&/^$/{exit} f' CONTEXT.md | head -1)
  [ -n "$def" ] && ok "TC-029: $term has a one-sentence definition line" || bad "TC-029: $term has a definition"
done
# TC-034: every term CONTEXT.md defines today is still defined. The list is pinned
# here (the 15 bold terms on main when this check was written), not read from a
# git ref, so it runs in any checkout. New terms may be added freely; removing or
# renaming one means editing this list in the same PR, where the reviewer sees it.
PINNED_TERMS=('Prototype' 'Product' 'Execution backend' 'Brain' 'Muscle' 'Platform' 'Station agent' 'Run index' 'MCP tool layer' 'Buyer' 'Operator' 'Experiment spec' 'Deliverable' 'Reproducible' 'Data stays local')
missing=""
for t in "${PINNED_TERMS[@]}"; do
  grep -qF -- "**$t**" CONTEXT.md || missing="$missing [$t]"
done
if [ "${#PINNED_TERMS[@]}" != 15 ]; then bad "TC-034: the pinned term list has 15 terms" "${#PINNED_TERMS[@]}"; fi
[ -z "$missing" ] && ok "TC-034: every pinned CONTEXT.md term is still defined" || bad "TC-034: terms removed from CONTEXT.md" "$missing"

# TC-032: line A is new text in ROADMAP (not on main): present.
has "TC-032: ROADMAP line A sentence present"                     "$RM" 'Line A is unchanged: 2.17.0 goes to the trial lab first'
has "TC-032: ...installation steps shown to the maintainer"       "$RM" 'its installation steps are shown to the maintainer before they are sent'

# TC-038: ROADMAP names all three.
has "TC-038: ROADMAP: development and testing never go through Seqera's Services, its MCP server or tw" "$RM" "Development and testing never go through Seqera's Services, its MCP server or \`tw\`"

# TC-059: CLAUDE.md and README.md
has "TC-059: CLAUDE.md: 2.17.0 uses Platform as the backend, Nextflow's records underneath" CLAUDE.md "Platform is the execution backend 2.17.0 uses; the truth about a run underneath it is Nextflow's own records"
has "TC-059: CLAUDE.md points at constitution 5.0.0"                CLAUDE.md 'constitution 5.0.0'
has "TC-059: CLAUDE.md still has 'Constitution 2.0.0'"             CLAUDE.md 'Constitution 2.0.0'
has "TC-059: CLAUDE.md still has 'hooks/in_use.sh'"                CLAUDE.md 'hooks/in_use.sh'
has "TC-059: README.md: Platform's runs rest on Nextflow's own records" README.md "Nextflow's own records, the truth under constitution 5.0.0"
has "TC-059: README.md still has 'Constitution 2.0.0'"             README.md 'Constitution 2.0.0'

# TC-060: the platform's own chat (maintainer, 2026-10-09: 「也做聊天介面 可接模型」)
CHATC=$(sec "$C" '^### 3[.]0[.]0 [(]2026-10-08[)]' '^##+ ')
# (a) the chat is a Stage 3 web page (014 in ROADMAP), not a separate product
has "TC-060a: ADR 0004: the chat is a page of the web (Stage 3)"   "$ADR4" 'It is a page of the web (Stage 3)'
has "TC-060a: ROADMAP: 014 is the platform's chat inside Stage 3"  "$RM" '| 3 | **Web** (features 011–014, 016)'
has "TC-060a: ROADMAP positioning: the platform's own chat"        "$RM" "from the platform's own chat, with the model it chooses, or from the harness it already uses"
# (b) the user picks and pays for the model
has "TC-060b: ADR 0004: user picks the model and pays (API key or local model)" "$ADR4" 'the user picks the model and pays for it (their own API key, or a local model)'
has "TC-060b: ROADMAP: their own API key or a local model"         "$RM" 'their own API key or a local model'
# (c) only through the same MCP tools; no gate or rule of its own
has "TC-060c: ADR 0004: only the same MCP tools, confirmation looks the same" "$ADR4" 'the chat reaches the platform only through the same MCP tools, so a confirmation looks the same in the chat as in any harness'
has "TC-060c: ADR 0004: no gate or rule of its own"                "$ADR4" 'carries no gate or rule of its own'
has "TC-060c: ROADMAP: chat calls only the MCP tools of 009"       "$RM" 'calling only the MCP tools of 009'
# (d) no general-purpose harness of our own: still rejected in 0004 and 0003
inn "TC-060d: ADR 0004 still rejects a general-purpose harness"    "$O4" 'general-purpose harness**: rejected'
has "TC-060d: ADR 0003 still rejects it"                           "$ADR3" 'Our own general-purpose harness**: rejected in ADR 0004'
# (e) bring-your-own harness through MCP stays
has "TC-060e: ADR 0004: any harness the user already has calls the tools too" "$ADR4" 'so does any harness the user already has (Claude Desktop first; Claude Code, Codex and other MCP clients too)'
has "TC-060e: ADR 0003: Claude Desktop first is still a host"      "$ADR3" 'Claude Desktop first, then Claude Code, Codex and others'
# (f) the amendment record carries his words; Safety Net unchanged (TC-040..044, constitution_scope_test)
inn "TC-060f: constitution 3.0.0 record has 「也做聊天介面 可接模型」"  "$CHATC" '「也做聊天介面 可接模型」'
inn "TC-060f: ...and says it calls the same MCP tools"              "$CHATC" 'it calls the same MCP tools'
# (g) ADR 0004: no 重做 / rebuilding part of a company's product; Seqera Platform is the reference
if flat < "$ADR4" | grep -qF "重做"; then bad "TC-060g: ADR 0004 has no 重做"; else ok "TC-060g: ADR 0004 has no 重做"; fi
if flat < "$ADR4" | grep -qiF "rebuilding part of a company"; then bad "TC-060g: ADR 0004 has no 'rebuilding part of a company'"; else ok "TC-060g: ADR 0004 has no 'rebuilding part of a company'"; fi
has "TC-060g: ADR 0004: Seqera Platform is the reference"          "$ADR4" 'Seqera Platform is the reference'

# TC-038/TC-039 (continued): the other planning documents.
has "TC-039: ROADMAP positioning: each member uses their own credential on their own station agent" "$RM" 'student'"'"'s own credential'

# ---- Constitution 4.1.0 (skills/ is a home of judgment; ADR 0006) ----
# Test cases: .specify/amendments/4.1.0-skills-home/test-case.md
echo
echo "== 4.1.0: constitution II.5, the 4.1.0 record, ROADMAP, CONTEXT, ADR 0006 (TC-003..TC-049) =="
ADR6=docs/adr/0006-four-entries-one-action-layer.md
P2=$(awk '/^### II\. /{f=1} /^### III\. /{f=0} f' "$C")
inn "4.1.0 TC-003: II.5 names skills/, docs/ and scripts/ as the home of judgment" "$P2" '**5.** Judgment, procedure and site operations live in `skills/`, `docs/` and `scripts/`, readable and runnable by a person or another model.'
inn "4.1.0 TC-004: II.5 Check names the test and skills/ in the fallback"          "$P2" '*Check:* `tests/works_without_host_test.sh`: with `hooks/` and `.claude-plugin/` removed, the system still works from `skills/`, `docs/` and `scripts/`: degraded, not equivalent, but usable.'
inn "4.1.0 TC-005: II.5 second sentence unchanged"                                "$P2" 'Whatever AI host runs the tool, its own capabilities (hooks, skills, commands or their equivalents) MUST be used fully.'
if grep -qxF '### 4.1.0 (2026-10-15): skills are a home of judgment; the platform has four entries' "$C"; then ok "4.1.0 TC-006: the 4.1.0 heading is exact"; else bad "4.1.0 TC-006: the 4.1.0 heading is exact"; fi
l40=$(grep -nF '### 4.0.0 (2026-10-11)' "$C" | head -1 | cut -d: -f1); l41=$(grep -nxF '### 4.1.0 (2026-10-15): skills are a home of judgment; the platform has four entries' "$C" | head -1 | cut -d: -f1); lg=$(grep -n '^## Governance' "$C" | head -1 | cut -d: -f1)
if [ -n "$l40" ] && [ -n "$l41" ] && [ -n "$lg" ] && [ "$l40" -lt "$l41" ] && [ "$l41" -lt "$lg" ]; then ok "4.1.0 TC-006: 4.1.0 sits after 4.0.0 and before Governance"; else bad "4.1.0 TC-006: 4.1.0 sits after 4.0.0 and before Governance" "$l40/$l41/$lg"; fi
AM41=$(sec "$C" '^### 4[.]1[.]0 [(]2026-10-15[)]' '^##+ ')
prev=0; okorder=1
for h in '**Rationale.**' '**What changes.**' '**Impact on existing deployments.**' '**Version.**' '**Approval.**'; do
  n=$(printf '%s\n' "$AM41" | grep -nF -- "$h" | head -1 | cut -d: -f1)
  if [ -z "$n" ] || [ "$n" -le "$prev" ]; then okorder=0; fi; prev=${n:-0}
done
[ "$okorder" = 1 ] && ok "4.1.0 TC-007: the five parts of the 4.1.0 record, in order" || bad "4.1.0 TC-007: the five parts of the 4.1.0 record, in order"
inn "4.1.0 TC-008: Rationale quotes 「只加 MCP 網址就能用」"           "$AM41" '「只加 MCP 網址就能用」'
inn "4.1.0 TC-008: ...and cites docs/adr/0006"                        "$AM41" 'docs/adr/0006'
inn "4.1.0 TC-009: Rationale quotes 「平台純粹靠GUI介面也要能使用」"   "$AM41" '「平台純粹靠GUI介面也要能使用」'
inn "4.1.0 TC-010: Rationale quotes the chat sentence"                "$AM41" '「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」'
inn "4.1.0 TC-011: the web scope: setup → launch → runs → rendered reports → the package" "$AM41" 'setup → launch → runs → rendered reports → the package'
inn "4.1.0 TC-011: ...figures are made in the chat or in a harness"   "$AM41" 'figures'
inn "4.1.0 TC-011: ...v3 is built on the branch v3"                   "$AM41" '`v3`'
inn "4.1.0 TC-011: ...the CI trigger is configured on the v3 branch"  "$AM41" 'CI trigger'
inn "4.1.0 TC-012: What changes: II.5 names skills/ and its check already packs it" "$AM41" '`skills/`'
inn "4.1.0 TC-012: ...the new principles wait in ROADMAP 'Principles waiting for a check'" "$AM41" 'Principles waiting for a check'
inn "4.1.0 TC-012: ...they join by the MAJOR amendment that ships with feature 009" "$AM41" 'the MAJOR amendment that ships with feature 009'
inn "4.1.0 TC-012: ...the Safety Net is unchanged, word for word"     "$AM41" 'The Safety Net is unchanged, word for word.'
inn "4.1.0 TC-013: Impact: None, no hook, script, command or skill changes" "$AM41" '**Impact on existing deployments.** None. No hook, script, command or skill changes'
inn "4.1.0 TC-014: Version: MINOR, under Governance"                  "$AM41" '**Version.** MINOR, under Governance'
inn "4.1.0 TC-014: ...a principle is expanded, none removed or redefined" "$AM41" 'none is removed or redefined'
inn "4.1.0 TC-014: Approval: the maintainer approves and merges"      "$AM41" '**Approval.** The maintainer approves and merges the pull request'
nin "4.1.0 TC-015: the 4.1.0 record does not say 'run index'"         "$AM41" 'run index'
nin "4.1.0 TC-015: ...nor 'tool layer'"                               "$AM41" 'tool layer'
nin "4.1.0 TC-015: ...nor 'action layer'"                             "$AM41" 'action layer'
nin "4.1.0 TC-046: ...nor a promised MAJOR number 6.0.0"              "$AM41" '(^|[^0-9.])6\.0\.0'
nin "4.1.0 TC-046: ADR 0006 promises no MAJOR number 6.0.0"           "$(cat "$ADR6")" '(^|[^0-9.])6\.0\.0'

# ROADMAP: Stage 2 and 3 rows, v2/v3 paragraph (TC-016..TC-022)
R2=$(printf '%s\n' "$STG" | grep -E '^\| 2 \|' | head -1)
R3=$(printf '%s\n' "$STG" | grep -E '^\| 3 \|' | head -1)
inn "4.1.0 TC-016: 009: the action layer, one function per action"     "$R2" 'the action layer (one function per action, called by the MCP tools, the web pages and the chat)'
inn "4.1.0 TC-016: 009: following Seqera MCP's tools plus the extra ones" "$R2" "following Seqera MCP's tools plus \`list_site_files\`, \`validate_samplesheet\`, \`estimate_su\`, \`read_task_log\`, \`run_downstream\`, \`build_package\`"
inn "4.1.0 TC-016: 009: every write action's gate on a human channel"  "$R2" "every write action's gate answered on a human channel (elicitation form or a confirmation page)"
inn "4.1.0 TC-016: 009: OAuth 2.1 / personal access token and identity" "$R2" 'OAuth 2.1 / personal-access-token authorization and the identity each token carries'
inn "4.1.0 TC-016: 009: instructions and one prompt per skill"         "$R2" "the server's \`instructions\` and one prompt per skill mirroring \`skills/\`"
inn "4.1.0 TC-016: 009: Skills over MCP endpoint"                      "$R2" 'the Skills over MCP endpoint'
inn "4.1.0 TC-016: 009: skills/ copied into the package"               "$R2" '`skills/` copied into the package'
inn "4.1.0 TC-016: 009: the relay sending events to a public address"  "$R2" 'the relay sending events to a public address'
inn "4.1.0 TC-017: 008 is unchanged"                                   "$R2" "008: Tower-compatible receiver for the \`nf-tower\` plugin's events, kept as a rebuildable index."
inn "4.1.0 TC-017: 010 is postponed (ADR 0009)"                                   "$R2" '010: postponed (ADR 0009)'
inn "4.1.0 TC-017: Stage 2 done-when: the student sees it on the web"                     "$R2" 'A student in Claude Desktop runs a 16S analysis end to end from conversation, the student sees it on the web, and nothing goes through Seqera'
nin "4.1.0 TC-017: the old 'every write tool carries its own confirmation' is gone" "$R2" 'every write tool carries its own confirmation'
inn "4.1.0 TC-018: 011 matches the actions one to one"                 "$R3" '011a–e), matching the actions one to one (parity test)'
inn "4.1.0 TC-018: 012 matches the actions one to one"                 "$R3" '(012a–d); cost shown per compute environment (NCHC SU and cloud money apart), a cloud cap per person per month (the number is set when an account opens), and no NCHC SU cap in dev mode; matching the actions one to one (parity test)'
inn "4.1.0 TC-018: 013 matches the actions one to one"                 "$R3" 'the finished page with the delivery package (013a–b), matching the actions one to one (parity test)'
inn "4.1.0 TC-019: 014 is verbatim"                                    "$R3" "014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009"
inn "4.1.0 TC-020: Stage 3 done-when opens with a person with no AI tool" "$R3" "A person with no AI tool completes setup → launch → running → results → downstream (in a Studio) → finished from the web alone; Two members of the trial lab"
nin "4.1.0 TC-021: no Stage 3 sentence gives figures to the web pages"  "$R3" 'web pages? (make|draw|plot)'
inn "4.1.0 TC-022: the v2 and v3 paragraph, verbatim"                  "$STG" 'v2 and v3 (2026-10-15, ADR 0006): `main` is the v2 line until v3.0.0; v3 is built on the branch `v3`. v2 takes bug fixes and changes that make the Safety Net stricter, released as 2.17.x only when a fix affects a user. Line A is unchanged:'

# CONTEXT.md (TC-031..TC-033, TC-064)
MTL=$(awk 'index($0,"**MCP tool layer** ")==1{f=1;next} f&&/^$/{exit} f' CONTEXT.md)
nin "4.1.0 TC-031: MCP tool layer: the old 'each write tool carries its own gate' is gone" "$MTL" 'each write tool carries its own confirmation gate'
inn "4.1.0 TC-031: ...the gate of a write action lives in the action layer, answered by a person" "$MTL" 'the gate of a write action lives there, answered by a person on a human channel'
inn "4.1.0 TC-031: ...and Planned (Stage 2)."                          "$MTL" 'Planned (Stage 2).'
inn "4.1.0 TC-031: ...gains the ADR 0006 sentence"                     "$MTL" 'Since ADR 0006 the tools call the action layer; the gate of a write action lives there, answered by a person on a human channel.'
ACT=$(awk 'index($0,"**action layer** ")==1{f=1;print;next} f&&/^$/{exit} f' CONTEXT.md)
inn "4.1.0 TC-032: action layer (動作層) is defined"                    "$ACT" '**action layer** (動作層)'
inn "4.1.0 TC-032: ...one function per platform action"                "$ACT" 'one function per platform action'
inn "4.1.0 TC-032: ...called by the tools, pages and chat alike"       "$ACT" 'called by the MCP tools, the web pages and the chat alike'
inn "4.1.0 TC-032: ...the gate of a write action lives here"           "$ACT" 'the gate of a write action lives here'
inn "4.1.0 TC-032: ...Planned (Stage 2, feature 009)"                  "$ACT" 'Planned (Stage 2, feature 009)'
inn "4.1.0 TC-032: ..._Avoid_: API, backend"                           "$ACT" '_Avoid_: API, backend'
HUM=$(awk 'index($0,"**human channel** ")==1{f=1;print;next} f&&/^$/{exit} f' CONTEXT.md)
inn "4.1.0 TC-033: human channel (人通道) is defined"                   "$HUM" '**human channel** (人通道)'
inn "4.1.0 TC-033: ...the way a person, not the model, answers a gate" "$HUM" 'the way a person, not the model, answers a gate'
inn "4.1.0 TC-033: ...elicitation form or confirmation page"           "$HUM" 'an elicitation form in the harness, or a confirmation page on the platform'
inn "4.1.0 TC-033: ...the token is the record, not the answer"         "$HUM" 'The token is the record of that answer, not the answer.'
inn "4.1.0 TC-033: ...Planned (Stage 2)."                              "$HUM" 'Planned (Stage 2).'
inn "4.1.0 TC-033: ..._Avoid_: confirmation token (when the act is meant)" "$HUM" '_Avoid_: confirmation token (when the act is meant)'

# ADR 0006 (TC-035..TC-043), ADR 0003 and 0004 notes (TC-044, TC-045)
has "4.1.0 TC-035: ADR 0006 title"                                     "$ADR6" '# Four entries, one action layer'
has "4.1.0 TC-035: ...amends ADR 0003 and ADR 0004"                    "$ADR6" 'Amends ADR 0003 and ADR 0004 (2026-10-15)'
has "4.1.0 TC-036: ADR 0006 quotes 「只加 MCP 網址就能用」"              "$ADR6" 'Install cost: 「只加 MCP 網址就能用」 — a user adds one MCP URL to the harness they already have; nothing else is required.'
has "4.1.0 TC-037: ADR 0006 quotes the GUI sentence"                   "$ADR6" "「平台純粹靠GUI介面也要能使用」 — the platform's web pages are a complete entry for a person with no AI tool."
has "4.1.0 TC-038: ADR 0006 quotes the chat sentence"                  "$ADR6" "「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」 — the platform's own chat is a full entry too, not a later extra."
has "4.1.0 TC-039: ADR 0006 states the web scope"                      "$ADR6" "the web pages complete **setup → launch → runs → rendered reports → the package of the pipeline's outputs**; figures from scripts are made in the platform's chat or in a harness."
has "4.1.0 TC-040: ADR 0006: v3 on the long-lived branch v3"           "$ADR6" 'v3 is built on the long-lived branch `v3`'
has "4.1.0 TC-040: ...CI trigger configured on the v3 branch itself"   "$ADR6" "the CI trigger for \`v3\` is configured on the \`v3\` branch itself, not in this record's pull request"
has "4.1.0 TC-040: ...the maintainer approved the CI change"           "$ADR6" 'the maintainer approved the CI change on 2026-10-15'
has "4.1.0 TC-040: ...main stays the v2 line until v3.0.0"             "$ADR6" '`main` stays the v2 line until v3.0.0'
for h in '### Four entries, one action layer' '### The "yes" must come from a person' '### Where the platform runs, and who is calling' '### Hooks and the gates they carry' '### What the web pages must do without AI' '### v2 and v3' '### The constitution' '## Considered Options' '## Consequences'; do
  if grep -qxF -- "$h" "$ADR6"; then ok "4.1.0 TC-041: ADR 0006 has '$h'"; else bad "4.1.0 TC-041: ADR 0006 has '$h'"; fi
done
HK=$(sec "$ADR6" '^### Hooks and the gates they carry' '^### ')
inn "4.1.0 TC-042: confirm_launch.sh rides with the MAJOR amendment with feature 009" "$HK" '| `hooks/confirm_launch.sh` |'
inn "4.1.0 TC-042: ...confirm_cleanup.sh kept for good"                "$HK" 'kept for good'
inn "4.1.0 TC-042: ...confirm_walkthrough.sh (G7)"                     "$HK" '`hooks/confirm_walkthrough.sh` (G7)'
inn "4.1.0 TC-042: ...guard_plugin_files.sh kept"                      "$HK" '`hooks/guard_plugin_files.sh`'
inn "4.1.0 TC-042: removing a gate hook is the maintainer's and MAJOR" "$HK" "the maintainer's and MAJOR"
CON6=$(sec "$ADR6" '^### The constitution' '^## ')
inn "4.1.0 TC-043: ADR 0006 says 4.1.0 (MINOR), II.5 names skills/"    "$CON6" '4.1.0 (MINOR): principle II.5 names `skills/`'
inn "4.1.0 TC-043: ...the new principles wait in the ROADMAP"          "$CON6" 'Waiting for a check in `docs/ROADMAP.md`'
has "4.1.0 TC-044: ADR 0003 gains the ADR 0006 note"                   "$ADR3" "Amended 2026-10-15 by ADR 0006: gates live in the action layer the tools and the web pages call; a harness kit is not an adapter"
has "4.1.0 TC-045: ADR 0004 gains the ADR 0006 note"                   "$ADR4" "Amended 2026-10-15 by ADR 0006: the web pages are a non-AI entry to the same actions; the confirmation is a person's act on a human channel"

# Citing documents (TC-047, TC-049)
hasnt "4.1.0 TC-047: CLAUDE.md no longer says constitution 4.0.0"      CLAUDE.md 'constitution 4\.0\.0'
hasnt "4.1.0 TC-047: README.md no longer says constitution 4.0.0"      README.md 'constitution 4\.0\.0'
has "4.1.0 TC-049: PRINCIPLES.md point 5 names skills/, docs/ and scripts/" "$PR" 'Judgment, procedure and site operations live in `skills/`, `docs/` and `scripts/`, which a person or another model can read and run directly.'
hasnt "4.1.0 TC-049: ...the docs/-and-scripts/-only wording is gone"    "$PR" 'operations live in `docs/` and `scripts/`'


# ---- W0 (ADR 0009 follow-through): specs/w0-adr0009-followthrough/test-case.md ----
echo "== W0: ROADMAP, POSITIONING, ADR 0004 follow ADR 0009 =="
W2=$(printf '%s\n' "$STG" | grep -E '^\| 2 \|' | head -1)
W3=$(printf '%s\n' "$STG" | grep -E '^\| 3 \|' | head -1)
WWHO=$(awk '/^\*\*Who:\*\*/{f=1} f&&/^$/{exit} f' "$RM")
inn "W0 TC-001: 010 is postponed (ADR 0009)"                     "$W2" '010: postponed (ADR 0009)'
nin "W0 TC-001: ...no longer '010: the two-role lab'"            "$W2" '010: the two-role lab'
inn "W0 TC-002: Stage 2 done-when: the student sees it on the web" "$W2" 'the student sees it on the web'
nin "W0 TC-002: ...the PI no longer sees it on the web"          "$W2" 'the PI sees it on the web'
inn "W0 TC-002: ...16S end to end from conversation kept"        "$W2" 'A student in Claude Desktop runs a 16S analysis end to end from conversation'
inn "W0 TC-002: ...nothing goes through Seqera kept"             "$W2" 'and nothing goes through Seqera'
inn "W0 TC-003: Stage 2 heading unchanged"                       "$W2" '| 2 | **Platform core** (features 008–010)'
inn "W0 TC-003: 009 action layer kept"                           "$W2" 'the action layer (one function per action, called by the MCP tools, the web pages and the chat)'
nin "W0 TC-004: Who: the old PI-pays sentence is gone"           "$WWHO" 'the PI pays and sees the whole lab'
inn "W0 TC-005: Who: one person per account, only their own runs" "$WWHO" 'only their own runs'
inn "W0 TC-006: Who: PI view postponed with roles (ADR 0009)"    "$WWHO" 'postponed'
inn "W0 TC-006: ...names ADR 0009"                               "$WWHO" 'ADR 0009'
inn "W0 TC-007: Who: first labs kept"                            "$WWHO" 'starting with 16S amplicon and RNA-seq'
inn "W0 TC-007: Who: hospitals out of scope kept"                "$WWHO" 'Hospitals are out of scope'

inn "W0 TC-008: Stage 3 heading is features 011–014, 016"        "$STG" '| 3 | **Web** (features 011–014, 016)'
inn "W0 TC-009: 011 is the shell, right pane, projects, run detail, failure sentence (011a–e)" "$W3" '011a–e'
inn "W0 TC-009: ...right pane shows progress of all analyses"    "$W3" 'right pane'
nin "W0 TC-010: no 'dashboard page' in ROADMAP"                  "$(cat "$RM")" 'dashboard page'
nin "W0 TC-010: ...Stage 3 has no '011: dashboard and run detail'" "$W3" '011: dashboard and run detail'
inn "W0 TC-011: 012 is settings, launch stage, uploads (012a–d)" "$W3" '012a–d'
inn "W0 TC-012: cost per compute environment"                    "$W3" 'per compute environment'
inn "W0 TC-012: ...cloud cap per person per month"               "$W3" 'per person per month'
inn "W0 TC-013: ...no NCHC SU cap in dev mode"                   "$W3" 'no NCHC SU cap in dev mode'
nin "W0 TC-014: 'SU estimate with a cap' is gone"                "$W3" 'SU estimate with a cap'
inn "W0 TC-015: 013 is results and the package (013a–b)"         "$W3" '013a–b'
n_par=$(printf '%s\n' "$W3" | flat | grep -oF 'matching the actions one to one (parity test)' | wc -l | tr -d ' ')
[ "$n_par" = 3 ] && ok "W0 TC-016: parity sentence appears three times in Stage 3" || bad "W0 TC-016: parity sentence appears three times in Stage 3" "got $n_par"
inn "W0 TC-017: 014 verbatim"                                    "$W3" "014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009"
inn "W0 TC-018: Studios is feature 016, inside Stage 3"          "$W3" '016: Studios'
inn "W0 TC-019: Stage 3 done-when: setup → launch → running → results → downstream (in a Studio) → finished" "$W3" 'setup → launch → running → results → downstream (in a Studio) → finished'
inn "W0 TC-020: Stage 3 done-when second half kept verbatim"     "$W3" 'Two members of the trial lab use it for two weeks with fewer than 10 new PITFALLS; the hosted service goes live (charging waits on the open questions below)'
nin "W0 TC-021: no Stage 3 sentence gives figures to the web"    "$W3" 'web pages? (make|draw|plot)'
for n in 0 1 4 5; do
  if printf '%s\n' "$STG" | grep -qE "^\| $n \| \*\*"; then ok "W0 TC-022: stage $n row still present"; else bad "W0 TC-022: stage $n row still present"; fi
done

inn "W0 TC-023: role row is re-staged postponed (ADR 0009)"      "$WL" "Role tests against the platform's API | postponed (ADR 0009) |"
inn "W0 TC-024: new owed-parity row"                             "$WL" 'owed parity — every action has an MCP tool and a web route; the owed list only shrinks'
inn "W0 TC-025: ...its check arrives with 011a's parity test"    "$WL" '011a'
cntW=$(printf '%s\n' "$WL" | grep -cE '^[|]' || true)
[ "${cntW:-0}" = 17 ] && ok "W0 TC-026: waiting list has 17 table lines" || bad "W0 TC-026: waiting list has 17 table lines" "$cntW"
inn "W0 TC-027: other rows untouched (run index)"                "$WL" "The platform's run index is never a second truth"
inn "W0 TC-027: ...(model-neutral command layer)"                "$WL" "Model-neutral command layer: no command depends on one model's behaviour"

inn "W0 TC-028: ADR 0009 open-questions subsection"              "$(cat "$RM")" 'Open questions from ADR 0009 (answered before the slice that needs them)'
inn "W0 TC-028: ...original intro sentence unchanged"            "$OQ" 'Each must be answered before the hosted service charges anyone (Stage 3).'
inn "W0 TC-029: original four stay (military service)"           "$OQ" 'alternative military service'
inn "W0 TC-029: ...(Seqera terms)"                               "$OQ" 'not for developing a competing product'
inn "W0 TC-029: ...(NCHC M6)"                                    "$OQ" 'NCHC (M6'
inn "W0 TC-029: ...(TWCC)"                                       "$OQ" 'TWCC: how a lab without an NSTC project pays'
OQ9=$(sec "$RM" '^### Open questions from ADR 0009' '^##+ ')
inn "W0 TC-030: asks how a hosted account is created"            "$OQ9" 'is an account created'
inn "W0 TC-031: asks about runs with no recorded person"         "$OQ9" 'no recorded person'
inn "W0 TC-032: asks whether uploads/downloads pass through the hosted platform" "$OQ9" 'pass through the hosted platform'
inn "W0 TC-033: asks whether each resume/relaunch needs the confirmation page" "$OQ9" 'resume or relaunch'
inn "W0 TC-034: asks about Studios on NCHC, a second submission path"  "$OQ9" 'second submission path'
inn "W0 TC-034: ...needs a constitution amendment"               "$OQ9" 'constitution amendment'
inn "W0 TC-035: asks about the cloud account and the monthly cap number" "$OQ9" 'monthly cap'

inn "W0 TC-036: ADR 0004 points to ADR 0008 and 0009 for Studios" "$O4" 'Superseded for Studios by ADR 0008 and ADR 0009.'
inn "W0 TC-037: ADR 0004 pinned Studios sentence stays"          "$O4" "Studios**: rejected; the user's own IDE on the site does that job"
POS18=$(grep -F '1. **一間實驗室' "$POS")
nin "W0 TC-039: POSITIONING point 1 no longer lists Studios as not built" "$POS18" 'Fusion、Studios'
inn "W0 TC-040: ...Data Explorer still not built"                "$POS18" 'Data Explorer'
inn "W0 TC-040: ...no dashboard page; the right pane replaces it" "$POS18" '右欄'
nin "W0 TC-041: ...no longer simplified to PI／member roles"     "$POS18" '簡化成 PI／成員兩種角色'
inn "W0 TC-041: ...roles postponed, ADR 0009"                    "$POS18" 'adr/0009'
inn "W0 TC-042: breakthrough 1 keeps the measured NCHC refusal"  "$(cat "$POS")" 'Data Explorer／Studios 在國網實測被拒'
POS9=$(grep -E '^\| 9 \|' "$POS")
inn "W0 TC-043: breakthrough 9 is postponed"                     "$POS9" '延後'
inn "W0 TC-043: ...points to ADR 0009"                           "$POS9" 'adr/0009'
hasnt "W0 TC-059: 'owed parity' is not in the constitution"      "$C" 'owed parity'
echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
