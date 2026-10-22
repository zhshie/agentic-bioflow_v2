#!/bin/bash
# t3-scripts-tagged: TC-001..TC-009.
# The four Taiwania-3-only scripts must carry the exact tag line inside their
# opening comment block, so nobody uses them on nano4 by mistake.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${T3_TAG_ROOT:-$(cd "$HERE/.." && pwd)}"
TAG='# Taiwania-3 only (v2); nano4 uses $NFCORE_SITE_CONFIG — see docs/SITE_ADAPTER.md'
FILES="scripts/utils/boxes.sh scripts/check_resource_contract.sh scripts/tune_resources.sh scripts/why_pending.sh"
fail=0
for f in $FILES; do
  p="$ROOT/$f"
  if [ ! -f "$p" ]; then echo "FAIL $f: missing file"; fail=1; continue; fi
  n=$(grep -cxF -- "$TAG" "$p")
  if [ "$n" -ne 1 ]; then echo "FAIL $f: tag line found $n times (want exactly 1)"; fail=1; continue; fi
  # TC-005: tag inside the leading contiguous '#' block
  ok=0
  while IFS= read -r line; do
    case "$line" in
      "#"*) [ "$line" = "$TAG" ] && { ok=1; break; } ;;
      *) break ;;
    esac
  done < "$p"
  if [ "$ok" -ne 1 ]; then echo "FAIL $f: tag not within the opening comment block"; fail=1; continue; fi
  # TC-006: shebang
  first=$(head -n1 "$p")
  case "$f" in
    scripts/utils/boxes.sh)
      case "$first" in "#!"*) echo "FAIL $f: unexpected shebang"; fail=1; continue ;; esac ;;
    *)
      if [ "$first" != "#!/bin/bash" ]; then echo "FAIL $f: line 1 is not #!/bin/bash"; fail=1; continue; fi ;;
  esac
  echo "ok   $f"
done
[ "$fail" -eq 0 ] && echo "PASS: all four T3 scripts tagged" || echo "FAILED"
exit "$fail"
