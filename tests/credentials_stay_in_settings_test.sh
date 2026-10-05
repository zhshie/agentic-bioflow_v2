#!/bin/bash
# Safety Net, fourth rule (constitution): credentials and personal details live
# only in the deployment's own settings area, readable by the owner only; never
# printed, never in git, never in a params file, and never carried over from
# another member's copy.
#
# The rule has five parts. Most are held by tests that already exist; this file
# holds the parts nothing held, and says where the others are so the whole rule
# has one place to look.
#
#   owner-only      tests/settings_test.sh (the settings file is created mode
#                   600, a filesystem that cannot hold 600 is refused, a token
#                   the whole machine can read is called out),
#                   tests/windows_privacy_test.sh (the ACL, where mode lies).
#   never printed   tests/settings_test.sh, tests/inspect_sides_test.sh,
#                   tests/status_test.sh, tests/windows_privacy_test.sh: each
#                   plants a fixture token and greps the output for it. HERE:
#                   no script echoes, prints or traces a token variable (static).
#   never in git    HERE: no tracked file holds a token-shaped value or has a
#                   credential's name, and .gitignore names the credential files
#                   so `git add .` in a checkout that holds a deployment skips them.
#   never in params HERE: the walkthrough hook refuses a params file that carries
#                   a credential, even after the walkthrough was waved through.
#   not carried     tests/confirm_launch_test.sh (changing agent_connection to
#                   another identity asks first) and tests/init_workspace_test.sh
#                   (_personal/ is mode 700, per person). NOT enforced as a
#                   check: a settings file copied in from another member's
#                   account is not detected as such. docs/SETTINGS.md says one
#                   root belongs to one person; nothing measures it.
#
# This is a net, not a proof: a pattern list finds the shapes it knows. It is
# narrow on purpose, because a scanner that cries wolf gets its allow-list
# grown until it finds nothing.
#
# CRED_ROOT points the static scans at a scratch tree; --static-only skips the
# hook cases. The self-tests use both to prove each scan can go red.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$HERE/$(basename "${BASH_SOURCE[0]}")"
DEFAULT_ROOT="$(cd "$HERE/.." && pwd)"
ROOT="${CRED_ROOT:-$DEFAULT_ROOT}"
STATIC_ONLY=0; [ "${1:-}" = "--static-only" ] && STATIC_ONLY=1
fails=0
fail() { echo "$1"; fails=$((fails + 1)); }

# Files to scan: what git tracks when there is a repository, else every file
# under the tree (a scratch copy of the suite has no .git).
list_files() {
    local out=""
    if [ -d "$ROOT/.git" ] || [ -f "$ROOT/.git" ]; then out=$(git -C "$ROOT" ls-files 2>/dev/null); fi
    if [ -n "$out" ]; then
        printf '%s\n' "$out"
    else
        ( cd "$ROOT" && find . -type f -not -path './.git/*' -not -path '*/node_modules/*' | sed 's|^\./||' )
    fi
}
FILES=$(list_files)
[ -n "$FILES" ] || { echo "FAIL: found no files to scan under $ROOT"; exit 1; }

# 1. TOKEN-SHAPED VALUES ----------------------------------------------------
# Specific shapes first (a JWT, GitHub, AWS and Slack tokens, a private key),
# then an assignment to a credential-named key of a long, opaque value.
SHAPES='eyJ[A-Za-z0-9_-]{10,}[.][A-Za-z0-9_-]{10,}[.][A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
ASSIGN='(token|secret|passw(or)?d|api_?key|access_?key)[A-Za-z_]*["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9+/_=-]{24,}'
SCANLIST=$(grep -vxF 'tests/credentials_stay_in_settings_test.sh' <<<"$FILES")
# Fixtures: a test that proves a token is never printed has to plant one. Each
# entry is "<file>|<why the value is not a credential>"; an entry whose file no
# longer has a hit is stale and fails, so the list cannot only grow.
FIXTURE_ALLOW="
tests/positron_run_test.sh|marked FAKE in the value itself; planted so the test can grep the output for it
tests/settings_test.sh|'not-a-real-token...'; planted so the test can grep --summary for it
tests/windows_privacy_test.sh|base64 of 'tid:12345 NOTAREALTOKEN'; planted so the test can grep the report for it
extensions/positron-bridge/test/bridge-core.test.js|a repeating a1b2c3d4e5f6 pattern for the bridge's own test
"
raw=$(cd "$ROOT" && {
          printf '%s\n' "$SCANLIST" | tr '\n' '\0' | xargs -0 grep -IHnE "$SHAPES" 2>/dev/null
          printf '%s\n' "$SCANLIST" | tr '\n' '\0' | xargs -0 grep -IHnEi "$ASSIGN" 2>/dev/null
      } | cut -c1-140)
hits=""
while IFS= read -r line; do
    [ -n "$line" ] || continue
    grep -qF "${line%%:*}|" <<<"$FIXTURE_ALLOW" || hits="$hits$line"$'\n'
done <<<"$raw"
if [ -z "${CRED_ROOT:-}" ]; then
    while IFS='|' read -r file _; do
        [ -n "$file" ] || continue
        grep -q "^$file:" <<<"$raw" || fail "STALE  $file no longer holds a fixture token; remove it from FIXTURE_ALLOW in tests/credentials_stay_in_settings_test.sh"
    done <<<"$FIXTURE_ALLOW"
fi
[ -z "$hits" ] || { printf '%s' "$hits"; fail "TOKEN  a tracked file holds a token-shaped value; credentials live in the deployment's settings area only"; }

# 2. CREDENTIAL FILES NOT IN GIT, AND IGNORED --------------------------------
named=$(grep -E '(^|/)([.]seqera_token|env[.]yaml|egress_allow[.]tsv|id_rsa[^/]*|id_ed25519[^/]*|[^/]*[.]pem)$' <<<"$FILES")
[ -z "$named" ] || { printf '%s\n' "$named"; fail "TRACKED  a credential or settings file is tracked; it belongs in the deployment's settings area"; }
for pat in '.seqera_token' 'env.yaml'; do
    grep -qxF "$pat" "$ROOT/.gitignore" 2>/dev/null \
        || fail "IGNORE  .gitignore does not list '$pat'; a checkout that holds a deployment would add it with 'git add .'"
done

# 3. NO SCRIPT PRINTS A TOKEN -----------------------------------------------
# A command that prints (echo, printf, cat of a variable) or traces (set -x,
# bash -x) while a token variable is in scope. Reading a token INTO a variable
# is the point of the settings area and is fine.
code=$(cd "$ROOT" && grep -HnE '.' scripts/*.sh scripts/*.py scripts/utils/*.sh hooks/*.sh 2>/dev/null \
       | grep -vE '^[^:]+:[0-9]+:[[:space:]]*(#|//)')
TOKVAR='(^|[^\\])[$][{]?(TOWER_ACCESS_TOKEN|SEQERA_TOKEN|TOKEN|_env_token|token|tok)[}]?([^A-Za-z0-9_]|$)'
printing=$(grep -E "(echo|printf|print\(|cat <<)[^|>]*${TOKVAR}" <<<"$code" | grep -vE '>[[:space:]]*"?[$][{]?[A-Za-z_]*[Tt]oken[A-Za-z_]*[}]?"?[[:space:]]*$' | cut -c1-160)
[ -z "$printing" ] || { printf '%s\n' "$printing"; fail "PRINT  a script prints a token variable; the token is never printed"; }
tracing=$(grep -E '(^|[^[:alnum:]_])(set|bash|sh)[[:space:]]+-[euopxv]*x[euopxv]*([[:space:]]|$)' <<<"$code" | cut -c1-160)
[ -z "$tracing" ] || { printf '%s\n' "$tracing"; fail "TRACE  a script turns on shell tracing, which prints every expanded token"; }

[ "$STATIC_ONLY" = 1 ] && { [ "$fails" -gt 0 ] && exit 1; exit 0; }

# 4. NEVER IN A PARAMS FILE --------------------------------------------------
# hooks/confirm_walkthrough.sh sees every write to a params file (Write, Edit,
# a here-doc). A credential in one is carried into the run's record, the
# provenance and every package built from it, so the write is refused whether
# or not the walkthrough happened, and the user's 略過導覽 does not lift it.
H="$ROOT/hooks/confirm_walkthrough.sh"
if [ -x "$H" ] || [ -f "$H" ]; then
    command -v jq >/dev/null 2>&1 || { echo "FAIL: jq not found; cannot run the params-file cases"; exit 1; }
    TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
    python3 - "$TMP/escape.jsonl" "$TMP/empty.jsonl" <<'PY'
import json, sys
for path, turns in ((sys.argv[1], ["略過導覽"]), (sys.argv[2], [])):
    with open(path, "w") as f:
        for t in turns:
            f.write(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": t}]}}) + "\n")
PY
    verdict() { # verdict <tool-json> <transcript> -> allow | deny
        local out
        out=$(python3 -c '
import json,sys
d=json.loads(sys.argv[1]); d["transcript_path"]=sys.argv[2]; print(json.dumps(d))' "$1" "$2" | bash "$H" 2>/dev/null)
        if grep -q '"permissionDecision": *"deny"' <<<"$out"; then echo deny; else echo allow; fi
    }
    pw() { python3 -c '
import json,sys
print(json.dumps({"tool_name":"Write","tool_input":{"file_path":"/r/params.yaml","content":sys.argv[1]}}))' "$1"; }
    ed() { python3 -c '
import json,sys
print(json.dumps({"tool_name":"Edit","tool_input":{"file_path":"/r/params.yaml","old_string":"x: 1","new_string":sys.argv[1]}}))' "$1"; }
    hd() { python3 -c '
import json,sys
print(json.dumps({"tool_name":"Bash","tool_input":{"command":"cat > params.yaml <<EOF\n"+sys.argv[1]+"\nEOF"}}))' "$1"; }
    case_() { # case_ <label> <want> <tool-json>
        local got; got=$(verdict "$3" "$TMP/escape.jsonl")
        [ "$got" = "$2" ] || fail "PARAMS  $1: got $got, wanted $2"
    }
    # Every case runs with 略過導覽 said, so the walkthrough gate itself is
    # standing down: only the credential rule can be what answers.
    case_ "ordinary parameters pass"                    allow "$(pw $'outdir: /w/projects/p/runs/r1/results\ninput: s.csv\nskip_trimming: true')"
    case_ "a prose comment about tokens passes"         allow "$(pw $'# no token here, the settings area has it\noutdir: /w/projects/p/runs/r1/results')"
    case_ "a parameter that merely contains 'token' passes" allow "$(pw $'tokenizer: models/bpe/tokenizer.model\nmax_tokens: 512')"
    case_ "a token key with a long value is refused"   deny  "$(pw $'outdir: /w/projects/p/runs/r1/results\ntower_access_token: Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MA')"
    case_ "a password key is refused"                   deny  "$(pw $'outdir: /w/projects/p/runs/r1/results\ndb_password: hunter2hunter2')"
    case_ "an api_key is refused"                       deny  "$(pw $'outdir: /w/projects/p/runs/r1/results\napi_key: abcd1234efgh5678')"
    case_ "a JWT-shaped value under any key is refused" deny  "$(pw $'outdir: /w/projects/p/runs/r1/results\nnote: eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjEyMzQ1fQ.c2lnbmF0dXJlMTIzNDU')"
    case_ "an Edit that adds a token is refused"        deny  "$(ed $'tower_access_token: Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MA')"
    case_ "a here-doc that writes a token is refused"   deny  "$(hd $'outdir: /w/projects/p/runs/r1/results\nsecret: Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MA')"
fi

# ---------------------------------------------------------------------------
if [ "$fails" -gt 0 ]; then
    echo
    echo "FAIL: $fails problem(s) against the credentials rule"
    exit 1
fi

# Self-tests for the static scans: each shape on a scratch tree.
if [ -z "${CRED_ROOT:-}" ]; then
    S=$(mktemp -d)
    selffails=0
    scratch() { # scratch <want-rc> <label> <file> <content> [gitignore content]
        rm -rf "$S/t"; mkdir -p "$S/t/scripts" "$S/t/hooks" "$S/t/docs"
        printf '%s\n' "${5:-.seqera_token
env.yaml}" > "$S/t/.gitignore"
        mkdir -p "$S/t/$(dirname "$3")"; printf '%s\n' "$4" > "$S/t/$3"
        CRED_ROOT="$S/t" bash "$SELF" --static-only >/dev/null 2>&1; local rc=$?
        [ "$rc" = "$1" ] || { echo "SELFTEST FAIL: $2 (rc $rc, wanted $1)"; selffails=$((selffails + 1)); }
    }
    scratch 0 "a clean tree passes"                          docs/a.md 'nothing here'
    scratch 0 "a fixture-length fake token passes"           docs/a.md 'token: not-a-real-token-9Q7X'
    scratch 0 "a variable assignment is not a value"         scripts/a.sh 'TOKEN_FILE="${SEQERA_TOKEN_FILE:-$HOME/.seqera_token}"'
    scratch 0 "reading a token into a variable passes"       scripts/a.sh 'TOWER_ACCESS_TOKEN="$(cat "$f")"'
    scratch 1 "a JWT in a doc fails"                         docs/a.md 'eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjEyMzQ1fQ.c2lnbmF0dXJlMTIzNDU'
    scratch 1 "a GitHub token fails"                         docs/a.md 'ghp_abcdefghijklmnopqrstuvwxyz0123456789'
    scratch 1 "a private key header fails"                   docs/a.md '-----BEGIN OPENSSH PRIVATE KEY-----'
    scratch 1 "token: <long opaque value> fails"             docs/a.md 'seqera_token: Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MA'
    scratch 0 "an allow-listed test fixture passes"           tests/settings_test.sh 'SECRET=token_x_Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MA'
    scratch 1 "the same value in another test file fails"    tests/other_test.sh 'SECRET=token_x_Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MA'
    scratch 0 "an escaped \$VAR in a message is not a read"   scripts/a.sh 'echo "checked \$TOWER_ACCESS_TOKEN"'
    scratch 0 "fish's set -gx is not tracing"                scripts/a.sh 'printf "set -gx %s %s\n" "$n" "$v"'
    scratch 1 "a tracked .seqera_token fails"               config/.seqera_token 'x'
    scratch 1 "a tracked env.yaml fails"                     config/env.yaml 'workspace_id: 1'
    scratch 1 "a .gitignore without .seqera_token fails"     docs/a.md 'x' 'env.yaml'
    scratch 1 "a .gitignore without env.yaml fails"          docs/a.md 'x' '.seqera_token'
    scratch 1 "echoing the token fails"                      scripts/a.sh 'echo "token is $TOWER_ACCESS_TOKEN"'
    scratch 1 "printf of the token fails"                    scripts/a.sh 'printf "%s\n" "${TOKEN}"'
    scratch 1 "set -x fails"                                 scripts/a.sh 'set -x'
    scratch 1 "bash -x fails"                                hooks/a.sh 'bash -x ./run.sh'
    rm -rf "$S"
    [ "$selffails" -gt 0 ] && { echo "FAIL: $selffails self-test(s) failed"; exit 1; }
fi

echo "OK: no token-shaped value or credential file in the tree, .gitignore covers them, no script prints a token, no params file may carry one"
