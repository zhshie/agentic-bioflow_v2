#!/bin/bash
# Not CI-enforced lint (ruff/vulture wired into .github/): this runs the four
# cleanup tools once, by hand, over the code a person reads, and writes one
# Markdown report. It never edits a file and adds no CI job.
#
# Why: the cloud sweep (docs/reports/sweep-2026-11.md) found dead code,
# duplicated helpers and unused names with a hand-made AST scan. This script
# lets anyone repeat that sweep with off-the-shelf tools and compare.
#
# 參數來源：sweep-2026-11 報告
#   - 範圍 scripts/ platform/abf_platform platform/abf_launch platform/abf_station
#     (the report's scope minus hooks/docs/.github); excludes tests, build,
#     .venv, node_modules.
#   - vulture whitelist = the report's section 5 false positives: decorator-
#     registered tools (launch_tool, cancel_tool), framework overrides
#     (get_client, load_*, redirect_request).
#   - The report named vulture for dead code and pip-audit is the dependency
#     check; jscpd and ruff F401/F841 are the duplicate / unused-name checks
#     for sections 4 and 5. The report fixes no other flags, so the rest are
#     each tool's defaults.
#
# Usage: bash scripts/sweep.sh [--out <file>]
#   default report: ${TMPDIR:-/tmp}/sweep-<date>.md ; the path is printed last.
# Exit: 0 = ran (findings or not), 2 = bad arguments.
# A missing tool gives a "skipped: <tool> not installed (install: ...)" line.
# pip-audit needs PyPI; unreachable gives "skipped: network".
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
usage() { echo "usage: bash scripts/sweep.sh [--out <file>]" >&2; exit 2; }

OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) [ $# -ge 2 ] && [ -n "$2" ] || usage; OUT="$2"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$OUT" ] || OUT="${TMPDIR:-/tmp}/sweep-$(date +%Y-%m-%d).md"
OUT="${OUT%/}"
mkdir -p "$(dirname "$OUT")" 2>/dev/null || { echo "cannot create $(dirname "$OUT")" >&2; exit 2; }

cd "$ROOT" || exit 2
SCOPE=(scripts platform/abf_platform platform/abf_launch platform/abf_station)
EXCL_NAMES="tests,build,.venv,node_modules"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

: >"$OUT"
{
  echo "# Sweep report $(date +%Y-%m-%d)"
  echo
  echo "- Scope: ${SCOPE[*]} (excluding $EXCL_NAMES). Read-only; no file was changed."
  echo "- Parameters from the sweep-2026-11 report."
  echo
} >>"$OUT"

# section <tool> <title> <install hint> <command text> <count mode> <cmd...>
# count modes: lines:<ERE> counts output lines matching; json: pip-audit;
# raw: count not attempted.
section() {
  local tool="$1" title="$2" hint="$3" shown="$4" mode="$5"; shift 5
  { echo "## $title ($tool)"; echo; } >>"$OUT"
  if ! command -v "$tool" >/dev/null 2>&1; then
    { echo "skipped: $tool not installed (install: $hint)"; echo; } >>"$OUT"
    return
  fi
  local raw="$WORK/$tool.out" rc
  "$@" >"$raw" 2>&1 </dev/null; rc=$?
  # strip terminal colour codes so counting and the pasted lines are plain text
  sed -e $'s/\x1b\\[[0-9;]*m//g' "$raw" >"$raw.plain" && mv "$raw.plain" "$raw"
  if [ "$tool" = pip-audit ] && grep -q -i -E 'connection|resolve|timed out|max retries|proxy|network' "$raw" \
     && ! grep -q '"dependencies"' "$raw"; then
    { echo "skipped: network"; echo; } >>"$OUT"
    return
  fi
  local n
  case "$mode" in
    lines:*) n=$(grep -c -E "${mode#lines:}" "$raw") ;;
    json)    # one "name version id" line per vulnerability replaces the raw JSON
             n=$(python3 - "$raw" <<'PY' 2>/dev/null
import json, sys
t = open(sys.argv[1]).read()
d = json.loads(t[t.index("{"):])
rows = [f'{x["name"]} {x["version"]} {v.get("id","?")}'
        for x in d.get("dependencies", []) for v in x.get("vulns", [])]
open(sys.argv[1], "w").write("\n".join(rows) + ("\n" if rows else ""))
print(len(rows))
PY
) || n="未計" ;;
    *) n="未計" ;;
  esac
  {
    echo "Command: \`$shown\`"
    echo
    echo "發現數: $n"
    echo
    echo "前 50 條 / first 50 lines of output (tool exit code $rc):"
    echo
    echo '```'
    head -50 "$raw"
    echo '```'
    echo
  } >>"$OUT"
}

IGN="launch_tool,cancel_tool,get_client,load_*,redirect_request"
section vulture "Dead code" "pip install vulture" \
  "vulture ${SCOPE[*]} --exclude $EXCL_NAMES --ignore-names $IGN" \
  'lines:^[^ ].*:[0-9]+: unused ' \
  vulture "${SCOPE[@]}" --exclude "$EXCL_NAMES" --ignore-names "$IGN"

section jscpd "Duplicated code" "npm i -g jscpd" \
  "jscpd ${SCOPE[*]} --ignore **/tests/**,**/build/**,**/.venv/**,**/node_modules/** --reporters console" \
  'lines:Clone found' \
  jscpd "${SCOPE[@]}" --ignore "**/tests/**,**/build/**,**/.venv/**,**/node_modules/**" --reporters console

section ruff "Unused imports and variables" "pip install ruff" \
  "ruff check --select F401,F841 --output-format concise --no-cache --exclude tests,build,.venv,node_modules ${SCOPE[*]}" \
  'lines:: F(401|841) ' \
  ruff check --select F401,F841 --output-format concise --no-cache \
    --exclude tests --exclude build --exclude .venv --exclude node_modules "${SCOPE[@]}"

section pip-audit "Dependency vulnerabilities" "pip install pip-audit" \
  "pip-audit --format json --progress-spinner off -r platform/constraints.txt" \
  json \
  pip-audit --format json --progress-spinner off -r platform/constraints.txt

echo "$OUT"
exit 0
