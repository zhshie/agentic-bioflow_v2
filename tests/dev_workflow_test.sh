#!/bin/bash
# The constitution's Development Workflow names two gates that live in files,
# not in anyone's memory: test cases the maintainer approves before any plan
# (.specify/templates/test-case*.md + .claude/skills/test-cases), and acceptance
# by a separate read-only reviewer (.claude/agents/verifier.md). This checks the
# shape that makes each gate a gate - not the prose:
#   - both templates exist and carry the three case types and the draft status;
#   - the skill can never be read as permission to approve on its own;
#   - the reviewer cannot write: no Edit/Write/NotebookEdit in its tools line.
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

has "skill: stops before /speckit-plan"             "$SK" "Do not run \`/speckit-plan\`"
has "skill: never approves without his words"       "$SK" "Set \`已核可\` without his explicit words"
has "skill: reads the constitution"                 "$SK" "constitution.md"

VTOOLS=$(sed -n '/^---$/,/^---$/p' "$VF" 2>/dev/null | grep '^tools:')
printf '%-70s ' "verifier: has a tools line"
[ -n "$VTOOLS" ] && echo ok || { echo "FAIL: no tools: line in frontmatter"; fails=$((fails+1)); }
printf '%-70s ' "verifier: tools grant no write"
if [ -n "$VTOOLS" ] && ! grep -qE 'Edit|Write|NotebookEdit|\*' <<<"$VTOOLS"; then echo ok; else echo "FAIL: $VTOOLS"; fails=$((fails+1)); fi
has "verifier: defaults to UNVERIFIED, not PASS"    "$VF" "Default to UNVERIFIED, never to PASS"
has "verifier: refuses unapproved test cases"       "$VF" "已核可"

has "constitution: test cases before design"        "$CO" "test-case.md"
has "constitution: independent acceptance"          "$CO" "Independent acceptance"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
