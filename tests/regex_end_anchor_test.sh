#!/bin/bash
# Guard (correct 2026-11, class "regex-dollar-newline"): in Python, `$` also matches just
# before a trailing "\n", so a name check like re.compile(r"^[a-z0-9-]+$") accepts
# "name\n". Fixed by hand twice (98b4fa9 releases._REPO, 2026-10-25; c727ed4 seven name
# regexes, 2026-10-29), and the next contributor copies the nearest example, which may
# still be the old form. This scans platform/ and scripts/ (not tests) for
# re.compile/match/search/fullmatch with a literal that starts with ^ and ends with a bare
# $ and fails on any not listed in tests/regex_end_anchor_baseline.txt (a list that may only
# shrink). Set REGEX_SCAN_ROOT to scan another tree (e.g. an old checkout).
# Nothing existing: flake8/ruff have no rule for "$ before a newline in a validator".
ROOT="${REGEX_SCAN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="${REGEX_BASELINE:-$HERE/regex_end_anchor_baseline.txt}"
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "SKIP: no python"; exit 0; }
fails=0
ok() { printf '%-60s ok\n' "$1"; }
bad() { printf '%-60s FAIL%s\n' "$1" "${2:+: $2}"; fails=$((fails+1)); }

scan() { # <root>: prints "<file>\t<pattern>" per bare-$ validator
  "$PY" -I - "$1" <<'PYEOF'
import ast, sys, pathlib
root = pathlib.Path(sys.argv[1])
for top in ("platform", "scripts"):
    for p in sorted((root / top).rglob("*.py")):
        if "tests" in p.parts:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "re"
                    and n.func.attr in ("compile", "match", "search", "fullmatch") and n.args):
                a = n.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    v = a.value
                    if v.startswith("^") and v.endswith("$") and not v.endswith("\\$"):
                        print(f"{p.relative_to(root)}\t{v}")
PYEOF
}

new_ones() { # <root>: findings not in the baseline
  scan "$1" | sort -u | grep -vxFf <(grep -v '^#' "$BASE") 
}

# the scanner itself: bad and clean shapes in a scratch tree
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/platform" "$T/scripts"
printf 'import re\nA = re.compile(r"^[a-z]+$")\n' > "$T/platform/bad.py"
printf 'import re\nA = re.compile(r"^[a-z]+\\Z")\nB = re.compile(r"(?m)^x$")\nC = re.compile(r"^a\\$")\n' > "$T/platform/ok.py"
got="$(scan "$T")"
[ "$got" = "$(printf 'platform/bad.py\t^[a-z]+$')" ] && ok "scanner flags ^...\$ only" || bad "scanner" "$got"

# the real tree
hits="$(new_ones "$ROOT")"
if [ -z "$hits" ]; then ok "no new bare-\$ validator regex"; else
  bad "bare-\$ validator regex"
  printf '%s\n' "$hits" | while IFS=$'\t' read -r f pat; do
    echo "  $f: $pat"
    echo "    \$ also matches before a trailing newline, so \"name\\n\" passes. End the pattern with \\Z or use re.fullmatch (example: platform/abf_platform/compose.py _NAME). Do not add it to tests/regex_end_anchor_baseline.txt."
  done
fi
# the baseline may only shrink: every line must still exist
stale="$(grep -v '^#' "$BASE" | grep -vxFf <(scan "$ROOT" | sort -u))"
[ -z "$stale" ] && ok "baseline has no stale lines" || bad "stale baseline line (already fixed? delete it)" "$stale"
[ "$fails" -eq 0 ] && exit 0 || exit 1
