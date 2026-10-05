#!/bin/bash
# Invariant 1 (docs/PRINCIPLES.md, constitution I.1): before adding anything,
# say out loud what Seqera, nf-core or any other maintained tool already does
# the job. That was a spoken check, easy to skip under a deadline - this makes
# it mechanical.
#
# Every file under scripts/ (and scripts/utils/) and under hooks/ must carry,
# in its first 40 lines, a line of the form
#
#   # Not <tool>: <reason>
#   # Nothing existing: <why>
#
# and the FIRST such line is the file's declared answer. Two things are
# judged, not just that the line exists:
#
#   1. "Not <X>:" - X must be something OUTSIDE this repository (a maintained
#      tool, a platform feature, a library). A header that says "not our other
#      script" or "not a second copy of ourselves" is a design note, not an
#      answer to "what does somebody else already maintain" - it passed this
#      check for a year (audit 2026-09-29, issue #30). X is rejected when it
#      names a file or path of this repo, or opens with one of the in-repo
#      phrases in IN_REPO_PHRASES. The honest way to say "no external tool does
#      this" is the second form, "Nothing existing: <why>", whose reason is
#      the whole content.
#   2. The reason after the colon must be at least 15 characters.
#
# "Not <tool>" needs a capital N - lowercase "not" appears all over these
# headers in ordinary prose ("does not", "is not") and would make the check
# fire on sentences that were never meant as this line. Python files use the
# same '#' comment - not a docstring, which a later comment-only diff check
# cannot tell apart from code. awk files use '#' too.
#
# TEMPORARY ALLOW-LIST (bug: constitution-checks, item 1). The files named in
# TEMP_ALLOW are judged and REPORTED as PENDING, but do not fail the run,
# because another agent is editing them concurrently and a header edit here
# would collide with that work. Each entry names who applies the fix. An entry
# whose file is now clean FAILS the run ("remove it"), so the list can only
# shrink. SCRIPTS_NAME_ALT_NO_ALLOWLIST=1 ignores the list and shows the true
# red state.
#
# ROOT is parameterised via SCRIPTS_NAME_ALT_ROOT so a mutation test can point
# this at a scratch copy of the tree instead of the real one. The self-tests at
# the bottom do exactly that.
set -uo pipefail
DEFAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${SCRIPTS_NAME_ALT_ROOT:-$DEFAULT_ROOT}"

[ -d "$ROOT/scripts" ] || { echo "FAIL: no scripts/ under $ROOT"; exit 1; }

PATTERN='^#[[:space:]]*(Not[[:space:]]+.+:|Nothing existing:)'

# Openers that name an in-repo concept rather than an external tool. Matched
# case-insensitively against X (the text between "Not" and the first colon).
IN_REPO_PHRASES='^(a|an|the)[[:space:]]+(hook|gate|second|new|copy of|shell function|real .*implementation)|^(writing|rewriting|duplicating)[[:space:]]|^(this|our)[[:space:]]+(repo|plugin|own)|^"?(a|an)[[:space:]]+second'

# Temporary allow-list: "<path-under-root>|<who applies the fix, and when>".
TEMP_ALLOW="
scripts/detect_conditions.sh|another agent is editing this file; the maintainer applies the header line after merging (bug constitution-checks, item 1)
scripts/methods_text.py|another agent is editing this file; the maintainer applies the header line after merging (bug constitution-checks, item 1)
hooks/confirm_cleanup.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/confirm_launch.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/confirm_walkthrough.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/guard_plugin_files.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/in_use.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/launch_trigger.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/next_step.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/plugin_intro.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/session_start.sh|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/split_segments.awk|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
hooks/strip_heredocs.awk|hooks/ is being edited by another agent; headers are added after that merges (bug constitution-checks, item 1)
"
[ "${SCRIPTS_NAME_ALT_NO_ALLOWLIST:-0}" = 1 ] && TEMP_ALLOW=""
# A scratch root (mutation test) never uses the real repo's allow-list.
[ -n "${SCRIPTS_NAME_ALT_ROOT:-}" ] && [ "$ROOT" != "$DEFAULT_ROOT" ] && TEMP_ALLOW="${SCRIPTS_NAME_ALT_TEST_ALLOW:-}"

missing=0
short=0
inrepo=0
count=0
pending=0
stale=0

# Basenames of every file this repo ships: a "Not <that file>" is in-repo.
REPO_NAMES=$(find "$ROOT/scripts" "$ROOT/hooks" "$ROOT/tests" "$ROOT/commands" "$ROOT/skills" "$ROOT/docs" \
                  -type f 2>/dev/null | sed 's|.*/||' | grep -E '[.](sh|py|awk|md)$' | sort -u)

allow_reason() { printf '%s\n' "$TEMP_ALLOW" | awk -F'|' -v f="$1" '$1==f {print $2; exit}'; }

# judge_file <file> -> prints one problem line on stdout, nothing when clean
judge_file() {
    local f="$1" rel hit ln text x reason base
    rel="${f#"$ROOT"/}"
    hit=$(sed -n '1,40p' "$f" | grep -nE "$PATTERN" | head -1)
    if [ -z "$hit" ]; then
        echo "MISSING  $rel: no '# Not <tool>: ...' or '# Nothing existing: ...' line in the first 40 lines"
        return
    fi
    ln="${hit%%:*}"
    text="${hit#*:}"                       # strip "N:" (the grep line-number prefix)
    reason="${text#*:}"                    # strip "# Not <tool>:" / "# Nothing existing:"
    reason="$(printf '%s' "$reason" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    if [ "${#reason}" -lt 15 ]; then
        echo "SHORT    $rel:$ln reason is only ${#reason} chars: '${reason}'"
        return
    fi
    case "$text" in
        *Nothing\ existing:*) return ;;    # the explicit, reasoned form
    esac
    x="$(printf '%s' "$text" | sed -E -e 's/^#[[:space:]]*Not[[:space:]]+//' -e 's/:.*$//')"
    # (a) names a file or path of this repo
    case "$x" in
        *scripts/*|*hooks/*|*tests/*|*commands/*|*skills/*|*docs/*)
            echo "IN-REPO  $rel:$ln 'Not $x' names a path in this repo; name what is maintained OUTSIDE it, or write '# Nothing existing: <why>'"
            return ;;
    esac
    # one awk pass: split X into words, look each up in the set of repo names
    base=$(printf '%s\n' "$x" | awk -v names="$REPO_NAMES" '
        BEGIN { n = split(names, a, "\n"); for (i = 1; i <= n; i++) set[a[i]] = 1 }
        { m = split($0, w, /[^A-Za-z0-9_.-]+/)
          for (i = 1; i <= m; i++) { t = w[i]; sub(/[.]+$/, "", t); if (t in set) { print t; exit } } }')
    if [ -n "$base" ]; then
        echo "IN-REPO  $rel:$ln 'Not $x' names $base, a file of this repo; name what is maintained OUTSIDE it, or write '# Nothing existing: <why>'"
        return
    fi
    # (b) opens with an in-repo concept
    if printf '%s' "$x" | grep -qiE "$IN_REPO_PHRASES"; then
        echo "IN-REPO  $rel:$ln 'Not $x' names a concept of this repo, not a maintained tool; name the external tool, or write '# Nothing existing: <why>'"
        return
    fi
}

files=$(
    {
        find "$ROOT/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \)
        find "$ROOT/scripts/utils" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) 2>/dev/null
        find "$ROOT/hooks" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.awk' \) 2>/dev/null
    } | sort
)

while IFS= read -r f; do
    [ -n "$f" ] || continue
    count=$((count + 1))
    rel="${f#"$ROOT"/}"
    problem=$(judge_file "$f")
    why=$(allow_reason "$rel")
    if [ -n "$problem" ]; then
        if [ -n "$why" ]; then
            echo "PENDING  ${problem#* }   [temporary allow-list: $why]"
            pending=$((pending + 1))
        else
            echo "$problem"
            case "$problem" in
                MISSING*) missing=$((missing + 1)) ;;
                SHORT*)   short=$((short + 1)) ;;
                *)        inrepo=$((inrepo + 1)) ;;
            esac
        fi
    elif [ -n "$why" ]; then
        echo "STALE    $rel is clean now: remove it from TEMP_ALLOW in tests/scripts_name_their_alternative.sh"
        stale=$((stale + 1))
    fi
done <<< "$files"

echo
if [ "$missing" -gt 0 ] || [ "$short" -gt 0 ] || [ "$inrepo" -gt 0 ] || [ "$stale" -gt 0 ]; then
    echo "FAIL: $missing missing, $short too-short reason, $inrepo naming an in-repo alternative, $stale stale allow-list entries (of $count files checked)"
    [ "$pending" -gt 0 ] && echo "      ($pending more are on the temporary allow-list)"
    exit 1
fi

# ---------------------------------------------------------------------------
# Self-tests (mutation): the rule must turn red on the shapes it exists for.
# Skipped when this run is itself a self-test.
if [ -z "${SCRIPTS_NAME_ALT_ROOT:-}" ]; then
    SELF="${BASH_SOURCE[0]}"
    S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
    selffails=0
    mk() { # mk <relative path> <header line>
        mkdir -p "$S/$(dirname "$1")"
        printf '#!/bin/bash\n%s\n# reason continues here for the check.\n' "$2" > "$S/$1"
    }
    expect() { # expect <label> <want-rc> <path> <header>
        rm -rf "$S/scripts" "$S/hooks"; mkdir -p "$S/scripts"
        mk scripts/settings.sh "# Not tmux: a real external tool, with a long enough reason."
        mk "$3" "$4"
        out=$(SCRIPTS_NAME_ALT_ROOT="$S" bash "$SELF" 2>&1); rc=$?
        if [ "$rc" != "$2" ]; then
            echo "SELFTEST FAIL: $1 (rc $rc, wanted $2)"; printf '%s\n' "$out" | tail -4
            selffails=$((selffails + 1))
        fi
    }
    expect "external tool passes"                     0 scripts/a.sh "# Not tmux: it dies with its server and this must survive."
    expect "Nothing existing passes"                  0 scripts/a.sh "# Nothing existing: no maintained tool does exactly this job."
    expect "Not <our own script> fails"               1 scripts/a.sh "# Not settings.sh: a second reader of the file would duplicate it."
    expect "Not scripts/<path> fails"                 1 scripts/a.sh "# Not scripts/preflight.sh alone: it answers a different question."
    expect "Not a hook fails"                         1 scripts/a.sh "# Not a hook: nothing a hook exports survives to the next call."
    expect "Not a second ... fails"                   1 scripts/a.sh "# Not a second interface detector: the value is already computed."
    expect "hooks/ is scanned: no header fails"       1 hooks/h.sh   "# just prose, no answer to the question here at all."
    expect "hooks/ is scanned: external tool passes"  0 hooks/h.sh   "# Not a bare jq filter: it must also run when jq is missing."
    expect "too-short reason fails"                   1 scripts/a.sh "# Not tmux: short"
    # A waived file must never produce an unqualified OK (the false green this
    # check was filed against): the last line says PARTIAL and names the files.
    rm -rf "$S/scripts" "$S/hooks"; mkdir -p "$S/scripts" "$S/hooks"
    mk scripts/settings.sh "# Not tmux: a real external tool, with a long enough reason."
    printf '#!/bin/bash
echo no header
' > "$S/hooks/waived.sh"
    out=$(SCRIPTS_NAME_ALT_ROOT="$S" SCRIPTS_NAME_ALT_TEST_ALLOW='hooks/waived.sh|test' bash "$SELF" 2>&1); rc=$?
    [ "$rc" = 0 ] || { echo "SELFTEST FAIL: a waived file alone must not fail (rc $rc)"; selffails=$((selffails + 1)); }
    tail -1 <<<"$out" | grep -q '^PARTIAL' || { echo "SELFTEST FAIL: last line with a waived file must start with PARTIAL"; selffails=$((selffails + 1)); }
    tail -1 <<<"$out" | grep -q 'hooks/waived.sh' || { echo "SELFTEST FAIL: last line must name the waived file"; selffails=$((selffails + 1)); }
    grep -q '^OK' <<<"$out" && { echo "SELFTEST FAIL: an unqualified OK with a waived file"; selffails=$((selffails + 1)); }
    [ "$selffails" -gt 0 ] && { echo "FAIL: $selffails self-test(s) failed"; exit 1; }
fi

echo "OK: all $count scripts and hooks name an alternative outside this repo ($pending on the temporary allow-list)"
