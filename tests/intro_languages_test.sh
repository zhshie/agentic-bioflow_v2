#!/bin/bash
# Two language directories exist under scripts/intro/ because the plan
# ("語言" in the appendix) requires zh-TW and en to carry the same content, not
# a different message. This checks the structural half of that promise, which
# is the half a machine can actually verify: the same set of files exists in
# both directories, and every command file in both languages contains all five
# fixed section headings. It cannot check that the prose says the same thing -
# that is on whoever writes the text.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZH="$ROOT/scripts/intro/zh-TW"
EN="$ROOT/scripts/intro/en"
fails=0

t() { printf '%-62s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

echo "== both language directories exist =="
[ -d "$ZH" ]; t "scripts/intro/zh-TW exists" "$?" "0"
[ -d "$EN" ]; t "scripts/intro/en exists"    "$?" "0"
[ -d "$ZH" ] && [ -d "$EN" ] || { echo "cannot continue without both directories"; exit 1; }

echo "== exactly the same set of filenames in both languages =="
ZH_FILES="$(cd "$ZH" && ls -1 | sort)"
EN_FILES="$(cd "$EN" && ls -1 | sort)"
t "file lists are identical" "$ZH_FILES" "$EN_FILES"

while IFS= read -r f; do
    [ -n "$f" ] || continue
    printf '%-62s ' "$f present in both"
    if [ -r "$EN/$f" ]; then echo ok; else
        echo "FAIL: missing from en/"; fails=$((fails+1))
    fi
done <<< "$ZH_FILES"

echo "== overview.txt exists in both =="
[ -r "$ZH/overview.txt" ]; t "zh-TW/overview.txt readable" "$?" "0"
[ -r "$EN/overview.txt" ]; t "en/overview.txt readable"    "$?" "0"

echo "== every command file in both languages has all five headings =="
ZH_HEADINGS=("會做什麼" "你可以決定什麼" "不會做什麼" "結束時你會有什麼" "下一步")
EN_HEADINGS=("What it does" "What you decide" "What it will not do" "What you end up with" "Next step")

check_headings() { # check_headings <file> <label> <heading...>
    local file="$1" label="$2"; shift 2
    local text; text="$(cat "$file" 2>/dev/null)"
    local h missing=""
    for h in "$@"; do
        grep -qF -- "$h" <<<"$text" || missing="$missing[$h]"
    done
    printf '%-62s ' "$label"
    if [ -z "$missing" ]; then echo ok; else
        echo "FAIL: missing $missing"; fails=$((fails+1))
    fi
}

for c in setup launch runs downstream finish; do
    check_headings "$ZH/$c.txt" "zh-TW/$c.txt has all five zh-TW headings" "${ZH_HEADINGS[@]}"
    check_headings "$EN/$c.txt" "en/$c.txt has all five en headings"       "${EN_HEADINGS[@]}"
done

echo

# A site name in the introduction is a hardcoded cluster by another spelling:
# PRINCIPLES invariant 3 (anyone can install) and 4 (one cluster is not the
# world). tests/no_hardcoded_paths.sh checks paths and would not see this.
for f in "$ZH"/*.txt "$EN"/*.txt; do
    if grep -qiE 'NCHC|Taiwania' "$f" 2>/dev/null; then
        echo "FAIL: $(basename "$(dirname "$f")")/$(basename "$f") names one specific site"
        fails=$((fails + 1))
    else
        echo "ok: $(basename "$(dirname "$f")")/$(basename "$f") names no specific site"
    fi
done

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failures"; exit 1; }
