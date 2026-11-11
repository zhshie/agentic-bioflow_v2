#!/bin/bash
# Constitution 8.0.0 (dev-mode-launch): a yes given in advance through the person's own SU
# budget (BUDGET), and three changes to the Development Workflow (real-site acceptance after
# the merge, the ruling agent, automatic merging of a protected path after the adversarial
# review). This is a document check: it holds the words that make each limit a limit, so that
# a later edit cannot quietly widen the budget, drop a "never", or put words in the
# maintainer's mouth. Test cases: specs/dev-mode-launch/test-case.md (TC-077 to TC-096) and
# .specify/amendments/8.0.0-budget-and-workflow/plan.md (part B).
#
# What the code does is tested where it runs: platform/tests/test_budget_launch.py.
# CONSTITUTION_FILE points the check at a scratch copy; the self-tests at the bottom use that
# to prove the check can go red.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT" || exit 1
C="${CONSTITUTION_FILE:-.specify/memory/constitution.md}"
CLI=platform/abf_platform/cli.py
PT=platform/tests/test_budget_launch.py
fails=0
ok() { printf '%-96s ok\n' "$1"; }
bad() { printf '%-96s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }
flat() { tr -d '\r' | tr '\n' ' ' | tr -s ' '; }
inn() { if printf '%s\n' "$2" | grep -F -- "$3" >/dev/null; then ok "$1"; else bad "$1" "no '$3'"; fi; }
nin() { if printf '%s\n' "$2" | grep -F -- "$3" >/dev/null; then bad "$1" "found '$3'"; else ok "$1"; fi; }

[ -r "$C" ] || { echo "FAIL: cannot read $C"; exit 1; }

VERSION=8.0.0
DAY=2026-11-11          # the day the amendment was drafted; a literal, so the check does not go red tomorrow

echo "== the version line and the 8.0.0 entry (TC-079) =="
LAST=$(grep -v '^[[:space:]]*$' "$C" | tr -d '\r' | tail -1)
if [ "$LAST" = "**Version**: $VERSION | **Ratified**: 2026-09-28 | **Last Amended**: $DAY" ]; then ok "TC-079 the last line is exactly the $VERSION version line, Last Amended $DAY"
else bad "TC-079 the last line is exactly the $VERSION version line, Last Amended $DAY" "got: $LAST"; fi
HEADS=$(grep -cE '^### 8\.0\.0 \(' "$C")
if [ "$HEADS" = 1 ]; then ok "TC-079 exactly one '### 8.0.0 (' heading"; else bad "TC-079 exactly one '### 8.0.0 (' heading" "found $HEADS"; fi
HDAY=$(grep -E '^### 8\.0\.0 \(' "$C" | head -1 | sed -E 's/^### 8\.0\.0 \(([0-9]{4}-[0-9]{2}-[0-9]{2})\): .*/\1/')
LDAY=$(printf '%s\n' "$LAST" | sed -E 's/.*\*\*Last Amended\*\*: //')
if [ -n "$HDAY" ] && [ "$HDAY" = "$LDAY" ] && [ "$HDAY" = "$DAY" ]; then ok "TC-079 the heading's date and the version line's date are the same string"
else bad "TC-079 the heading's date and the version line's date are the same string" "heading '$HDAY', version line '$LDAY'"; fi
l7=$(grep -n '^### 7\.0\.0 ' "$C" | head -1 | cut -d: -f1); l8=$(grep -n '^### 8\.0\.0 ' "$C" | head -1 | cut -d: -f1); lg=$(grep -n '^## Governance' "$C" | head -1 | cut -d: -f1)
if [ -n "$l7" ] && [ -n "$l8" ] && [ -n "$lg" ] && [ "$l7" -lt "$l8" ] && [ "$l8" -lt "$lg" ]; then ok "TC-079 order: 7.0.0 < 8.0.0 < Governance"; else bad "TC-079 order: 7.0.0 < 8.0.0 < Governance"; fi
ENTRY=$(awk '/^### 8\.0\.0 /{f=1} /^## Governance/{f=0} f' "$C" | tr -d '\r')
E=$(printf '%s\n' "$ENTRY" | flat)
ORDER=$(printf '%s' "$E" | grep -o '\*\*\(Rationale\|What changes\|Sync Impact Report\|Impact on existing deployments\|Version\|Approval\)\.\*\*' | tr '\n' ' ')
if [ "$ORDER" = '**Rationale.** **What changes.** **Sync Impact Report.** **Impact on existing deployments.** **Version.** **Approval.** ' ]; then ok "TC-079 six sections, once each, in order"
else bad "TC-079 six sections, once each, in order" "got: $ORDER"; fi
inn "TC-079 the amendment is MAJOR" "$E" '**Version.** MAJOR'

echo "== Approval is PENDING and nobody is quoted as agreeing (TC-077) =="
APPROVAL=$(printf '%s\n' "$ENTRY" | awk '/^\*\*Approval\.\*\*/{f=1} f' | grep -v '^[[:space:]]*$')
WANT='**Approval.** PENDING: 維護者尚未對修正案全文表示同意。合併前必須由維護者親口同意後補上其原話。'
if [ "$APPROVAL" = "$WANT" ]; then ok "TC-077 the Approval field is exactly the PENDING sentence and nothing else"
else bad "TC-077 the Approval field is exactly the PENDING sentence and nothing else" "got: $(printf '%s' "$APPROVAL" | head -c 300)"; fi
nin "TC-077 the entry does not quote 「同意，但4)按照1)」" "$E" '按照1)'
nin "TC-077 the entry does not say the maintainer approved it" "$E" 'approved the full text'
nin "TC-077 ...in either wording" "$E" 'approved this change in his own words'

echo "== what the entry must say, with its 'never' (TC-080) =="
WC=$(printf '%s\n' "$ENTRY" | awk '/^\*\*What changes\.\*\*/{f=1} /^\*\*Sync Impact Report\.\*\*/{f=0} f' | flat)
inn "TC-080 off until the person turns it on"                    "$WC" 'off until the person turns it on'
inn "TC-080 the person's own settings page"                      "$WC" 'settings page'
inn "TC-080 only the person sets or raises the limits"           "$WC" 'Only the person can set or raise the limits'
inn "TC-080 no tool, token, chat model or settings file can"     "$WC" 'no tool, token, chat model or settings file can'
inn "TC-080 over a limit goes back to the four channels"         "$WC" 'goes back to the four channels'
inn "TC-080 a send a cloud provider bills is never on the budget" "$WC" 'A send that a cloud provider bills is never on the budget'
inn "TC-080 forget is never on the budget"                       "$WC" '`forget` is never on the budget'
inn "TC-080 clearing a work directory is never on the budget"    "$WC" 'the clearing of a work directory is never on the budget'
inn "TC-080 honest limit: weaker than a yes for each send"       "$WC" 'weaker than a yes for each send'
inn "TC-080 honest limit: the estimate can be wrong"             "$WC" 'the estimate can be wrong'
inn "TC-080 an automatic resume counts toward the budget"        "$WC" 'automatic resume'
inn "TC-080 cancel is no longer asked for once both limits are set" "$WC" 'a cancel'
inn "TC-080 its relation to 5.0.0"                               "$WC" '5.0.0'
inn "TC-080 its relation to 7.0.0"                               "$WC" '7.0.0'
inn "TC-080 a hosted deployment never takes it"                  "$WC" 'hosted'
inn "the rest of the Safety Net is not loosened by it"           "$WC" 'No other Safety Net rule changes'

echo "== principle I.2 and the Safety Net carry the budget rule =="
I2=$(awk '/^- \*\*2\.\*\*/{f=1} f&&/^- \*\*3\.\*\*/{f=0} f' "$C" | flat)
SN=$(awk '/^## Safety Net/{f=1;next} /^## /{f=0} f' "$C" | tr -d '\r')
LRULE=$(printf '%s\n' "$SN" | awk '/^- A launch command is shown in full/{f=1;print;next} f&&/^- /{f=0} f' | flat)
WRULE=$(printf '%s\n' "$SN" | awk '/^- Every write tool of the platform/{f=1;print;next} f&&/^- /{f=0} f' | flat)
inn "I.2 names BUDGET"                                            "$I2" 'BUDGET'
inn "I.2: off until the person turns it on"                       "$I2" 'off until the person turns it on'
inn "I.2: two limits, set on the person's own settings page"      "$I2" 'settings page'
inn "I.2: a single-send limit"                                    "$I2" 'single-send limit'
inn "I.2: a monthly limit"                                        "$I2" 'monthly limit'
inn "I.2: both set and above zero"                                "$I2" 'both are set and above zero'
inn "I.2: anything else goes back to the four channels"           "$I2" 'goes back to the four channels'
inn "I.2: never on the budget (cloud, forget, work directory)"    "$I2" 'never on the budget'
inn "I.2: only the person can set or raise the limits"            "$I2" 'Only the person can set or raise the limits'
inn "I.2: it is weaker than a yes for each send"                  "$I2" 'weaker than a yes for each send'
inn "I.2 keeps: the four are the only channels a person operates" "$I2" 'The four are the only ones; a pending request, a token, or any answer the model itself can give is none of them.'
inn "the launch rule keeps its first sentence"                    "$LRULE" 'A launch command is shown in full and waits for explicit confirmation before it runs'
inn "the launch rule names the one exception"                     "$LRULE" 'BUDGET'
inn "the launch rule: the hook has no such exception"             "$LRULE" '`hooks/confirm_launch.sh` has no such exception'
inn "the write-tool rule names BUDGET"                            "$WRULE" 'BUDGET'
inn "the write-tool rule: never forget, a work directory or a cloud bill" "$WRULE" 'it never covers `forget`, the clearing of a work directory, or a send that a cloud provider bills'
inn "the write-tool rule: a caller cannot hand it in"             "$WRULE" 'never accepted from a caller'
inn "TC-081 the '(today ...)' list is unchanged, word for word"   "$WRULE" '(today `launch`, `launch_pipeline`, `cancel`, `resume`, `relaunch` and `forget`)'
inn "TC-082 the Check line names the new test file"               "$WRULE" '`platform/tests/test_budget_launch.py` (`test_bg_*`)'
if [ -f "$PT" ] && [ "$(grep -cE '^(async )?def test_bg_' "$PT")" -ge 1 ]; then ok "TC-082 $PT exists and defines test_bg_ tests"; else bad "TC-082 $PT exists and defines test_bg_ tests"; fi

echo "== the rest of the Safety Net is word for word what it was =="
SNF=$(printf '%s\n' "$SN" | flat)
inn "never delete a user's source data"       "$SNF" "- Never delete a user's source data: \`rawdata/\`, \`results/\`, \`analysis/\`, a run area's \`_references/\`, or a shared image cache. Never delete \`.nextflow/plugins/\`."
inn "deleting work/ needs the user's confirmation" "$SNF" "- Deleting \`work/\` or \`.nextflow/cache/\` requires the user's explicit confirmation (\`hooks/confirm_cleanup.sh\`)."
inn "credentials live only in the settings area" "$SNF" "- Credentials and personal details live only in the deployment's own settings area, readable by the owner only; never printed, never in git, never in a params file."
inn "the platform never stores a received credential" "$SNF" '- The platform never stores a credential that reaches it inside what it receives (a run'"'"'s config, command line, environment or secret parameters, or an OAuth exchange): none is written to its database or its data folder.'
inn "only a MAJOR amendment changes the rules" "$SNF" 'MUST NOT be relaxed by any feature spec or plan, and change only by a MAJOR amendment of this constitution.'

echo "== TC-081: the entries 2.0.0 to 7.0.0 are untouched =="
# The amendment records before 8.0.0 are pinned by a SHA-256 fingerprint (text from '## Amendments' up to the
# 8.0.0 heading, carriage returns removed), so the check works in a shallow clone with no base ref.
PINNED_OLD_ENTRIES_SHA256=6874bc14cc16ef85c5e6a4bd61029315f86397fb767fdbc8518575d85f730765
sha256_stdin() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then shasum -a 256 | cut -d' ' -f1
  elif command -v python3 >/dev/null 2>&1; then python3 -c 'import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
  else return 127
  fi
}
if OLDFP=$(awk '/^## Amendments/{f=1} /^### 8\.0\.0 /{f=0} /^## Governance/{f=0} f' "$C" | tr -d '\r' | sha256_stdin) && [ -n "$OLDFP" ]; then
  if [ "$OLDFP" = "$PINNED_OLD_ENTRIES_SHA256" ]; then ok "TC-081 the amendment records 2.0.0 to 7.0.0 match their fingerprint"
  else bad "TC-081 the amendment records 2.0.0 to 7.0.0 match their fingerprint" "current $OLDFP"; fi
else bad "TC-081 the amendment records 2.0.0 to 7.0.0 match their fingerprint" "no SHA-256 tool found"; fi

echo "== part B: the Development Workflow's last bullet =="
WF=$(awk '/^- \*\*One change at a time, on a branch\.\*\*/{f=1;print;next} f&&/^$/{f=0} f' "$C" | flat)
NB=$(awk '/^## Development Workflow/{f=1;next} /^## /{f=0} f&&/^- \*\*/' "$C" | wc -l | tr -d ' ')
if [ "$NB" = 8 ]; then ok "B: the Development Workflow still has eight rules"; else bad "B: the Development Workflow still has eight rules" "found $NB"; fi
inn "B: none of the three replaces the maintainer's yes"          "$WF" "none of them replaces the maintainer's yes"
inn "B1: acceptance on a real site MAY take place after the merge" "$WF" 'Acceptance on a real site (a run on a real cluster or in a real cloud account) MAY take place after the merge'
inn "B1: CI and the independent acceptance still come first"      "$WF" 'CI and the independent acceptance still come first'
inn "B1: the pull request lists what is still owed"               "$WF" 'lists each real-site check that is still owed'
inn "B1: not called done and not released while one is owed"      "$WF" 'is not called done and is not released while one is owed'
inn "B1: a failed real-site check reopens the change"             "$WF" 'a real-site check that fails reopens the change'
inn "B2: a ruling agent MAY rule on a failed task"                "$WF" 'a ruling agent MAY rule on it in place of the development lead'
inn "B2: it is neither the executor nor the reviewer of that task" "$WF" 'is neither the executor nor the reviewer of that task'
inn "B2: every ruling is written down with its reason"            "$WF" 'writes each ruling down with its reason'
inn "B2: it MUST NOT rule on the reserved matters"                "$WF" 'It MUST NOT rule on spending money, credentials or keys, permissions, this constitution, a release, or the protected hooks'
inn "B2: those go to the maintainer himself, always"              "$WF" 'those go to the maintainer himself, always'
inn "B3: a protected path MAY be merged automatically, only when" "$WF" 'MAY be merged automatically, without the development lead merging it by hand, only when'
inn "B3: the written record that the adversarial review passed"   "$WF" 'the written record that the adversarial review passed'
inn "B3: on the very commit that is merged"                       "$WF" 'on the very commit that is merged'
inn "B3: by a reviewer that is neither the author nor the first reviewer" "$WF" 'neither the author nor the first reviewer'
inn "B3: never an amendment, a release, a changed requirement or a loosening" "$WF" 'This never applies to an amendment of this constitution, a release, a modified or removed requirement, or anything that loosens the Safety Net'
inn "B3: a missing record or a doubt waits"                       "$WF" 'the change waits'
inn "B: the 6.2.0 sentence on the maintainer's yes is kept"       "$WF" "first need the maintainer's explicit yes, in his own words"
inn "B: the 6.2.0 sentence on the second review is kept"          "$WF" 'also carries a proof of what else it can affect and passes a second, adversarial review before it is merged.'

if [ -z "${CONSTITUTION_FILE:-}" ]; then
  echo "== documents and code (TC-084, TC-086, TC-090) =="
  n=0
  while IFS= read -r w; do
    [ -z "$w" ] && continue
    n=$((n+1))
    if grep -E "assub\.add_parser\(\"$w\"" "$CLI" >/dev/null; then ok "TC-084 'abf-platform auto-send $w' is a real subcommand"; else bad "TC-084 'abf-platform auto-send $w' is a real subcommand" "no such parser in $CLI"; fi
  done < <(cat docs/*.md CHANGELOG.md skills/*/SKILL.md 2>/dev/null | tr -d '\r' | grep -oE 'abf-platform +auto-send +[a-z][a-z-]*' | awk '{print $3}' | sort -u)
  if [ "$n" -gt 0 ]; then ok "TC-084 the documents name 'abf-platform auto-send'"; else bad "TC-084 the documents name 'abf-platform auto-send'"; fi
  if grep -E 'sub\.add_parser\("auto-send"' "$CLI" >/dev/null; then ok "TC-084 'auto-send' is a real top-level subcommand"; else bad "TC-084 'auto-send' is a real top-level subcommand"; fi
  WRITERS=$(grep -oE 'assub\.add_parser\("[a-z-]+"' "$CLI" | sed -E 's/.*\("//; s/"$//' | sort -u | tr '\n' ' ')
  if [ "$WRITERS" = 'list ' ]; then ok "TC-094 'auto-send' has only 'list': no command sets a limit"; else bad "TC-094 'auto-send' has only 'list': no command sets a limit" "found: $WRITERS"; fi
  if grep -rIl 'ABF_HOSTED' deploy/env.example >/dev/null 2>&1; then bad "TC-086 deploy/env.example does not carry ABF_HOSTED"; else ok "TC-086 deploy/env.example does not carry ABF_HOSTED"; fi
  UNITS=$(grep -rIl 'ABF_HOSTED' deploy/systemd 2>/dev/null)
  if [ -z "$UNITS" ]; then ok "TC-086 no unit file carries ABF_HOSTED yet (the hosted package is not merged): nothing to check"
  elif grep -rIh 'ABF_HOSTED' deploy/systemd | grep -v 'ABF_HOSTED=1' >/dev/null; then bad "TC-086 a unit file that carries ABF_HOSTED sets it to 1"
  else ok "TC-086 a unit file that carries ABF_HOSTED sets it to 1"; fi
  if grep -rIn 'auto_resume' platform/abf_platform platform/abf_station >/dev/null 2>&1; then bad "TC-090 no automatic resume in this slice"; else ok "TC-090 no automatic resume in this slice"; fi
  inn "docs/PLATFORM.md tells a reader about the budget yes" "$(flat < docs/PLATFORM.md)" 'BUDGET'
  inn "docs/PRINCIPLES.md records constitution 8.0.0"        "$(flat < docs/PRINCIPLES.md)" 'constitution 8.0.0'
  [ -f .specify/amendments/8.0.0-budget-and-workflow/plan.md ] && ok "the amendment's record folder exists" || bad "the amendment's record folder exists"

  # Self-tests: the check must go red on the shapes it exists for.
  S=$(mktemp -d) && trap 'rm -rf "$S"' EXIT
  red() { # red <label> <sed program>
    sed -E "$2" "$C" > "$S/c.md"
    if cmp -s "$C" "$S/c.md"; then bad "self-test: $1" "the edit changed nothing"; return; fi
    if CONSTITUTION_FILE="$S/c.md" bash "${BASH_SOURCE[0]}" >/dev/null 2>&1; then bad "self-test: $1" "stayed green"; else ok "self-test: $1 turns the check red"; fi
  }
  red "an Approval that quotes an agreement" 's/^\*\*Approval\.\*\* PENDING: .*/**Approval.** The maintainer approved the full text (「好」)./'
  red "a 'never' dropped from the write-tool rule" 's/it never covers `forget`, /it covers `forget`, /'
  red "the ruling agent allowed to rule on a release" 's/permissions, this constitution, a release, or the$/permissions, this constitution, or the/'
  red "an older amendment record edited" 's/^(### 7\.0\.0 \(2026-11-05\): a fourth)/\1 and fifth/'
fi

echo
if [ "$fails" -gt 0 ]; then echo "$fails check(s) failed"; exit 1; fi
echo "all constitution 8.0.0 checks passed"
