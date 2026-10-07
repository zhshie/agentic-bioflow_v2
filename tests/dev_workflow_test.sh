#!/bin/bash
# The constitution's Development Workflow (2.1.0) names gates that live in files,
# not in anyone's memory: test cases written by the independent reviewer before
# any code (.specify/templates/test-case*.md + .claude/skills/test-cases +
# .claude/agents/verifier.md CONTRACT mode), an executor that cannot stop before
# the suite is green (.claude/agents/executor.md), and acceptance by the same
# read-only reviewer. This checks the shape that makes each gate a gate - not
# the prose:
#   - both templates exist and carry the three case types and the draft status;
#   - the skill never lets the code's author write the cases or approve for him;
#   - the reviewer cannot write: no Edit/Write/NotebookEdit in its tools line;
#   - the executor has a Stop gate and cannot dispatch other agents.
# A reviewer that can edit the code it grades is the self-review the constitution
# forbids; a template that drops 不在範圍 quietly drops the out-of-scope checks.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fails=0

has() { printf '%-70s ' "$1"; if [ -r "$2" ] && grep -qF -- "$3" "$2"; then echo ok; else echo "FAIL: $2 lacks '$3'"; fails=$((fails+1)); fi; }
lacks() { printf '%-70s ' "$1"; if [ -r "$2" ] && ! grep -qE -- "$3" "$2"; then echo ok; else echo "FAIL: $2 matches '$3' (or is missing)"; fails=$((fails+1)); fi; }

TC="$ROOT/.specify/templates/test-case-template.md"
OV="$ROOT/.specify/templates/test-case-overview-template.md"
SK="$ROOT/.claude/skills/test-cases/SKILL.md"
VF="$ROOT/.claude/agents/verifier.md"
CO="$ROOT/.specify/memory/constitution.md"

for type in 功能 例外 不在範圍; do
  has "test-case template names type $type" "$TC" "$type"
  has "overview template counts type $type" "$OV" "$type"
done
has "test-case template: 驗證方式 column"           "$TC" "驗證方式"
has "overview template starts as draft"             "$OV" "狀態：草稿"
has "overview template: approval record section"    "$OV" "## 核可紀錄"

has "skill: author never writes the cases"         "$SK" "Let the author of the code write or edit the test cases"
has "skill: never approves without his words"       "$SK" "Set \`已核可\` without his explicit words"
has "skill: reads the constitution"                 "$SK" "constitution.md"

VTOOLS=$(sed -n '/^---$/,/^---$/p' "$VF" 2>/dev/null | grep '^tools:')
printf '%-70s ' "verifier: has a tools line"
[ -n "$VTOOLS" ] && echo ok || { echo "FAIL: no tools: line in frontmatter"; fails=$((fails+1)); }
printf '%-70s ' "verifier: tools grant no write"
if [ -n "$VTOOLS" ] && ! grep -qE 'Edit|Write|NotebookEdit|\*' <<<"$VTOOLS"; then echo ok; else echo "FAIL: $VTOOLS"; fails=$((fails+1)); fi
has "verifier: defaults to UNVERIFIED, not PASS"    "$VF" "Default to UNVERIFIED, never to PASS"
has "verifier: refuses unconfirmed test cases"      "$VF" "says neither \`合約已確認\` nor \`已核可\`"
has "verifier: checks for weakened tests"           "$VF" "Weakened tests"

EX="$ROOT/.claude/agents/executor.md"
EFM=$(sed -n '/^---$/,/^---$/p' "$EX" 2>/dev/null)
printf '%-70s ' "executor: has a Stop gate in frontmatter"
if grep -q '^  Stop:' <<<"$EFM" && grep -q 'exit 2' <<<"$EFM"; then echo ok; else echo "FAIL: no Stop hook that blocks"; fails=$((fails+1)); fi
printf '%-70s ' "executor: cannot dispatch agents"
ETOOLS=$(grep '^tools:' <<<"$EFM")
if [ -n "$ETOOLS" ] && ! grep -qE 'Agent|Task|\*' <<<"$ETOOLS"; then echo ok; else echo "FAIL: $ETOOLS"; fails=$((fails+1)); fi
has "executor: never weakens a test"                "$EX" "Never weaken a test to make it pass"

has "constitution: test cases before code"          "$CO" "Test cases before code"
has "constitution: independent acceptance"          "$CO" "Independent acceptance"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
