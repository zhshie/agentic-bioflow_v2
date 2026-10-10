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
if [ "$LAST" = '**Version**: 3.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-08' ]; then
  ok "TC-001: last line is exactly the 3.0.0 version line"
else bad "TC-001: last line is exactly the 3.0.0 version line" "got: $LAST"; fi

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
inn "TC-004: ...no submission script, state machine, or monitoring daemon"        "$P1" 'no submission script of our own, no state machine, and no monitoring daemon beyond the channels its check allow-lists'
inn "TC-004: ...Seqera's nouns where the backend is Seqera"                       "$P1" "follows Seqera's nouns"
inn "TC-004: I.2 Check is tests/no_second_run_state_test.sh"                      "$P1" '*Check:* `tests/no_second_run_state_test.sh`.'
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
    if [ "${2:-}" = withmain ]; then git -C "$d" branch main HEAD >/dev/null 2>&1; fi
    cp "$ROOT/CONTEXT.md" "$d/CONTEXT.md"; cp "$HERE/$SELFN" "$d/tests/"
    echo "$d"
  }
  inner() { OUT=$(cd "$1" && DOC_TEST_INNER=1 "$BASH" "tests/$SELFN" 2>&1); RC=$?; }
  t34ok() { printf '%s\n' "$OUT" | grep -F "$T34" | grep ' ok$' >/dev/null; }

  echo "== issue #71: TC-034 runs and fails without a main ref =="
  for mode in nomain withmain; do
    D=$(mkclone "c-$mode" "$([ "$mode" = withmain ] && echo withmain)") || { bad "scratch clone ($mode)"; continue; }
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
inn "TC-022: stage 3 is web (011-014)"                            "$STG" '| 3 | **Web** (features 011–014)'
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
inn "TC-023: new row: gates live in the platform's tool layer"    "$WL" "Gates live in the platform's tool layer"
inn "TC-023: ...with their stages: 2, 1–2, 1–2, 2, 1–2"          "$WL" '| 1–2 |'
cnt=$(printf '%s\n' "$WL" | grep -cE '^\| ' || true)
# header + separator + 5 new + 6 original + 1 split row = 13 or more
[ "${cnt:-0}" -ge 12 ] && ok "TC-023: waiting list has the 5 new rows on top of the 6 original (rows incl. header: $cnt)" || bad "TC-023: waiting list row count" "$cnt rows"
inn "TC-023: old row rewritten: host reaches launch/delete only through tools that carry their own gate" "$WL" 'A host reaches launch and delete only through tools that carry their own gate'
nin "TC-023: ...the old 'may query but never launch or delete' wording is gone" "$WL" 'may query but never'
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
has "TC-026: feature 2: MCP, your own AI or the platform's own chat" "$POS" '平台只開 MCP，對話用你自己的 AI，或平台自己的聊天介面'
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
if git rev-parse --verify -q main >/dev/null 2>&1 && git show main:CONTEXT.md >/dev/null 2>&1; then
  missing=""
  while IFS= read -r t; do
    grep -qF -- "**$t**" CONTEXT.md || missing="$missing [$t]"
  done < <(git show main:CONTEXT.md | grep -oE '^\*\*[^*]+\*\*' | sed -E 's/^\*\*(.*)\*\*$/\1/')
  [ -z "$missing" ] && ok "TC-034: every term CONTEXT.md had on main is still there" || bad "TC-034: terms removed from CONTEXT.md" "$missing"
else
  echo "note: git or the 'main' ref is unavailable; TC-034 comparison against main skipped"
fi

# TC-032: line A is new text in ROADMAP (not on main): present.
has "TC-032: ROADMAP line A sentence present"                     "$RM" 'Line A is unchanged: 2.17.0 goes to the trial lab first'
has "TC-032: ...installation steps shown to the maintainer"       "$RM" 'its installation steps are shown to the maintainer before they are sent'

# TC-038: ROADMAP names all three.
has "TC-038: ROADMAP: development and testing never go through Seqera's Services, its MCP server or tw" "$RM" "Development and testing never go through Seqera's Services, its MCP server or \`tw\`"

# TC-059: CLAUDE.md and README.md
has "TC-059: CLAUDE.md: 2.17.0 uses Platform as the backend, Nextflow's records underneath" CLAUDE.md "Platform is the execution backend 2.17.0 uses; the truth about a run underneath it is Nextflow's own records"
has "TC-059: CLAUDE.md points at constitution 3.0.0"                CLAUDE.md 'constitution 3.0.0'
has "TC-059: CLAUDE.md still has 'Constitution 2.0.0'"             CLAUDE.md 'Constitution 2.0.0'
has "TC-059: CLAUDE.md still has 'hooks/in_use.sh'"                CLAUDE.md 'hooks/in_use.sh'
has "TC-059: README.md: Platform's runs rest on Nextflow's own records" README.md "Nextflow's own records, the truth under constitution 3.0.0"
has "TC-059: README.md still has 'Constitution 2.0.0'"             README.md 'Constitution 2.0.0'

# TC-060: the platform's own chat (maintainer, 2026-10-09: 「也做聊天介面 可接模型」)
CHATC=$(sec "$C" '^### 3[.]0[.]0 [(]2026-10-08[)]' '^##+ ')
# (a) the chat is a Stage 3 web page (014 in ROADMAP), not a separate product
has "TC-060a: ADR 0004: the chat is a page of the web (Stage 3)"   "$ADR4" 'It is a page of the web (Stage 3)'
has "TC-060a: ROADMAP: 014 is the platform's chat inside Stage 3"  "$RM" '| 3 | **Web** (features 011–014)'
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

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
