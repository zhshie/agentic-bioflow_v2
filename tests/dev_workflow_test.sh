#!/bin/bash
# The constitution's Development Workflow (2.1.0) names gates that live in files,
# not in anyone's memory: test cases written by the independent reviewer before
# any code (.specify/templates/test-case*.md + .claude/skills/test-cases +
# the generic verifier's CONTRACT mode), an executor that cannot stop before the
# suite is green (gate in the developer-agent's workspace since 6.0.1), and acceptance by the same
# read-only reviewer. This checks the shape that makes each gate a gate - not
# the prose:
#   - both templates exist and carry the three case types and the draft status;
#   - the skill never lets the code's author write the cases or approve for him;
#   - CLAUDE.md carries the facts the generic executor and verifier read first;
#   - no stale repo copy of either agent is left to shadow the generic one.
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

# Constitution 6.0.1: the executor and verifier are generic agents in the developer-agent's
# workspace, shared by every project; their shape (verifier has no write tool, executor cannot
# dispatch, the stop and write gates are registered) is checked there at every opening by
# memory/scripts/dev-machine-check.ps1, because those files are not in this repository. What this
# repository owes them is the facts section in CLAUDE.md, and no stale copy of its own.
CM="$ROOT/CLAUDE.md"
has "CLAUDE.md: facts section for the executor and verifier" "$CM" "## For the executor and verifier"
has "CLAUDE.md: facts name the rules document"      "$CM" ".specify/memory/constitution.md"
has "CLAUDE.md: facts name the full-suite command"  "$CM" "bash tests/run_all.sh"
has "CLAUDE.md: facts list files never edited"      "$CM" "Never edit during implementation"
has "CLAUDE.md: facts keep the calibration failures" "$CM" "Calibration failures"
for f in executor verifier; do
  printf '%-70s ' "no stale repo copy of .claude/agents/$f.md"
  if [ ! -e "$ROOT/.claude/agents/$f.md" ]; then echo ok; else echo "FAIL: generic agent lives in the workspace; a repo copy would shadow it"; fails=$((fails+1)); fi
done

has "constitution: test cases before code"          "$CO" "Test cases before code"
has "constitution: independent acceptance"          "$CO" "Independent acceptance"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
